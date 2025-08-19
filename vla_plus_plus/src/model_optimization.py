#!/usr/bin/env python3
"""
Model Optimization Pipeline for VLA++
Implements quantization, pruning, and knowledge distillation
Reduces model from 217MB to <50MB for production deployment
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils import prune
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import time
import logging
from dataclasses import dataclass
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """Configuration for model optimization"""
    # Quantization settings
    quantization_backend: str = "qnnpack"  # For mobile/edge deployment
    quantization_dtype: str = "int8"  # int8 or fp16
    calibration_samples: int = 1000
    
    # Pruning settings
    pruning_amount: float = 0.6  # Remove 60% of weights
    pruning_type: str = "structured"  # structured or unstructured
    
    # Knowledge distillation settings
    teacher_temperature: float = 5.0
    student_temperature: float = 3.0
    distillation_alpha: float = 0.7
    
    # Target constraints
    target_model_size_mb: float = 50.0
    target_latency_ms: float = 10.0
    max_accuracy_loss: float = 0.01  # 1% max accuracy loss


class ModelQuantizer:
    """
    Quantization pipeline for VLA++ model
    Converts FP32 → FP16 → INT8 with minimal accuracy loss
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        torch.backends.quantized.engine = config.quantization_backend
        
    def calibrate_model(self, model: nn.Module, calibration_data: torch.Tensor) -> None:
        """
        Calibrate quantization parameters using representative data
        """
        model.eval()
        with torch.no_grad():
            for i in range(min(len(calibration_data), self.config.calibration_samples)):
                _ = model(calibration_data[i:i+1])
    
    def quantize_dynamic(self, model: nn.Module) -> nn.Module:
        """
        Dynamic quantization - quantizes weights, activations computed in FP32
        Best for models with varying input sizes
        """
        logger.info("Applying dynamic quantization...")
        
        # Identify layers to quantize
        quantized_model = torch.quantization.quantize_dynamic(
            model,
            qconfig_spec={
                nn.Linear: torch.quantization.default_dynamic_qconfig,
                nn.Conv2d: torch.quantization.default_dynamic_qconfig,
            },
            dtype=torch.qint8
        )
        
        return quantized_model
    
    def quantize_static(self, model: nn.Module, calibration_data: torch.Tensor) -> nn.Module:
        """
        Static quantization - quantizes both weights and activations
        Best for fixed input sizes and maximum performance
        """
        logger.info("Applying static quantization...")
        
        # Prepare model for quantization
        model.eval()
        model.qconfig = torch.quantization.get_default_qconfig(self.config.quantization_backend)
        model_prepared = torch.quantization.prepare(model)
        
        # Calibrate with representative data
        self.calibrate_model(model_prepared, calibration_data)
        
        # Convert to quantized model
        quantized_model = torch.quantization.convert(model_prepared)
        
        return quantized_model
    
    def quantize_qat(self, model: nn.Module, train_loader: Any) -> nn.Module:
        """
        Quantization-Aware Training - fine-tune with quantization
        Best accuracy but requires retraining
        """
        logger.info("Applying quantization-aware training...")
        
        model.train()
        model.qconfig = torch.quantization.get_default_qat_qconfig(self.config.quantization_backend)
        model_prepared = torch.quantization.prepare_qat(model)
        
        # Training loop (simplified)
        optimizer = torch.optim.AdamW(model_prepared.parameters(), lr=1e-4)
        
        for epoch in range(3):  # Quick fine-tuning
            for batch in train_loader:
                optimizer.zero_grad()
                output = model_prepared(batch['input'])
                loss = F.mse_loss(output, batch['target'])
                loss.backward()
                optimizer.step()
        
        # Convert to quantized model
        model_prepared.eval()
        quantized_model = torch.quantization.convert(model_prepared)
        
        return quantized_model


class ModelPruner:
    """
    Pruning pipeline for VLA++ model
    Removes redundant weights while maintaining performance
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        
    def prune_unstructured(self, model: nn.Module) -> nn.Module:
        """
        Unstructured pruning - removes individual weights
        Maximum compression but may not accelerate inference
        """
        logger.info(f"Applying unstructured pruning ({self.config.pruning_amount*100:.0f}%)...")
        
        parameters_to_prune = []
        for name, module in model.named_modules():
            if isinstance(module, (nn.Linear, nn.Conv2d)):
                parameters_to_prune.append((module, 'weight'))
        
        # Global magnitude pruning
        prune.global_unstructured(
            parameters_to_prune,
            pruning_method=prune.L1Unstructured,
            amount=self.config.pruning_amount,
        )
        
        # Remove pruning reparameterization
        for module, param_name in parameters_to_prune:
            prune.remove(module, param_name)
        
        return model
    
    def prune_structured(self, model: nn.Module) -> nn.Module:
        """
        Structured pruning - removes entire channels/filters
        Less compression but better acceleration
        """
        logger.info(f"Applying structured pruning ({self.config.pruning_amount*100:.0f}%)...")
        
        for name, module in model.named_modules():
            if isinstance(module, nn.Conv2d):
                # Prune output channels
                prune.ln_structured(
                    module, 
                    name='weight',
                    amount=self.config.pruning_amount,
                    n=2,  # L2 norm
                    dim=0  # Output channel dimension
                )
                prune.remove(module, 'weight')
                
            elif isinstance(module, nn.Linear):
                # Prune output features
                prune.ln_structured(
                    module,
                    name='weight',
                    amount=self.config.pruning_amount,
                    n=2,
                    dim=0
                )
                prune.remove(module, 'weight')
        
        return model
    
    def iterative_pruning(self, model: nn.Module, val_loader: Any) -> nn.Module:
        """
        Iterative magnitude pruning with fine-tuning
        Best balance of compression and accuracy
        """
        logger.info("Applying iterative pruning...")
        
        initial_accuracy = self.evaluate_model(model, val_loader)
        pruning_iterations = 5
        amount_per_iteration = 1 - (1 - self.config.pruning_amount) ** (1/pruning_iterations)
        
        for iteration in range(pruning_iterations):
            logger.info(f"Pruning iteration {iteration+1}/{pruning_iterations}")
            
            # Prune
            model = self.prune_unstructured(model)
            
            # Fine-tune
            self.fine_tune(model, val_loader, epochs=2)
            
            # Check accuracy
            current_accuracy = self.evaluate_model(model, val_loader)
            accuracy_loss = initial_accuracy - current_accuracy
            
            if accuracy_loss > self.config.max_accuracy_loss:
                logger.warning(f"Accuracy loss too high: {accuracy_loss:.3f}")
                break
        
        return model
    
    def evaluate_model(self, model: nn.Module, val_loader: Any) -> float:
        """Evaluate model accuracy (simplified)"""
        model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch in val_loader:
                outputs = model(batch['input'])
                predicted = torch.argmax(outputs, dim=1)
                correct += (predicted == batch['target']).sum().item()
                total += batch['target'].size(0)
        
        return correct / total if total > 0 else 0.0
    
    def fine_tune(self, model: nn.Module, train_loader: Any, epochs: int = 2):
        """Quick fine-tuning after pruning"""
        model.train()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5)
        
        for epoch in range(epochs):
            for batch in train_loader:
                optimizer.zero_grad()
                output = model(batch['input'])
                loss = F.cross_entropy(output, batch['target'])
                loss.backward()
                optimizer.step()


class KnowledgeDistiller:
    """
    Knowledge distillation for VLA++ model
    Transfers knowledge from large teacher to small student
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        
    def create_student_model(self, teacher_model: nn.Module) -> nn.Module:
        """
        Create smaller student model architecture
        50M params vs 350M params teacher
        """
        # This is a simplified example - actual implementation would
        # create a smaller version of the VLA++ architecture
        
        class StudentVLAModel(nn.Module):
            def __init__(self, teacher_dims):
                super().__init__()
                # Reduced dimensions (1/4 of teacher)
                self.vision_encoder = nn.Sequential(
                    nn.Conv2d(3, 32, 3, padding=1),
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                    nn.Conv2d(32, 64, 3, padding=1),
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                    nn.Flatten(),
                    nn.Linear(64 * 56 * 56, 256)
                )
                
                self.language_encoder = nn.Sequential(
                    nn.Linear(teacher_dims['vocab_size'], 128),
                    nn.ReLU(),
                    nn.Linear(128, 256)
                )
                
                self.action_decoder = nn.Sequential(
                    nn.Linear(512, 128),
                    nn.ReLU(),
                    nn.Linear(128, teacher_dims['action_dim'])
                )
            
            def forward(self, vision_input, language_input):
                vision_features = self.vision_encoder(vision_input)
                language_features = self.language_encoder(language_input)
                combined = torch.cat([vision_features, language_features], dim=-1)
                return self.action_decoder(combined)
        
        # Extract teacher dimensions
        teacher_dims = {
            'vocab_size': 8192,  # From teacher config
            'action_dim': 10
        }
        
        return StudentVLAModel(teacher_dims)
    
    def distillation_loss(
        self,
        student_logits: torch.Tensor,
        teacher_logits: torch.Tensor,
        labels: torch.Tensor,
        temperature: float,
        alpha: float
    ) -> torch.Tensor:
        """
        Combined distillation and student loss
        """
        # Distillation loss
        distillation_loss = F.kl_div(
            F.log_softmax(student_logits / temperature, dim=1),
            F.softmax(teacher_logits / temperature, dim=1),
            reduction='batchmean'
        ) * (temperature ** 2)
        
        # Student loss
        student_loss = F.cross_entropy(student_logits, labels)
        
        # Combined loss
        return alpha * distillation_loss + (1 - alpha) * student_loss
    
    def distill(
        self,
        teacher_model: nn.Module,
        student_model: nn.Module,
        train_loader: Any,
        epochs: int = 10
    ) -> nn.Module:
        """
        Perform knowledge distillation
        """
        logger.info("Starting knowledge distillation...")
        
        teacher_model.eval()
        student_model.train()
        
        optimizer = torch.optim.AdamW(student_model.parameters(), lr=1e-3)
        
        for epoch in range(epochs):
            total_loss = 0
            for batch in train_loader:
                # Get teacher predictions
                with torch.no_grad():
                    teacher_logits = teacher_model(
                        batch['vision_input'],
                        batch['language_input']
                    )
                
                # Get student predictions
                student_logits = student_model(
                    batch['vision_input'],
                    batch['language_input']
                )
                
                # Calculate loss
                loss = self.distillation_loss(
                    student_logits,
                    teacher_logits,
                    batch['labels'],
                    self.config.teacher_temperature,
                    self.config.distillation_alpha
                )
                
                # Optimize
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            logger.info(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(train_loader):.4f}")
        
        return student_model


class VLAOptimizationPipeline:
    """
    Complete optimization pipeline for VLA++ model
    Combines quantization, pruning, and distillation
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.quantizer = ModelQuantizer(config)
        self.pruner = ModelPruner(config)
        self.distiller = KnowledgeDistiller(config)
        
    def optimize_model(
        self,
        model: nn.Module,
        calibration_data: Optional[torch.Tensor] = None,
        train_loader: Optional[Any] = None,
        val_loader: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Full optimization pipeline
        """
        results = {
            "original_size_mb": self.get_model_size(model),
            "original_latency_ms": self.measure_latency(model),
            "optimization_steps": []
        }
        
        logger.info("="*60)
        logger.info("VLA++ MODEL OPTIMIZATION PIPELINE")
        logger.info("="*60)
        logger.info(f"Original model size: {results['original_size_mb']:.1f} MB")
        logger.info(f"Target size: {self.config.target_model_size_mb} MB")
        
        # Step 1: Knowledge Distillation
        logger.info("\n[1/3] Knowledge Distillation")
        student_model = self.distiller.create_student_model(model)
        if train_loader:
            student_model = self.distiller.distill(model, student_model, train_loader)
        
        student_size = self.get_model_size(student_model)
        logger.info(f"Student model size: {student_size:.1f} MB")
        results["optimization_steps"].append({
            "step": "distillation",
            "size_mb": student_size,
            "reduction": 1 - student_size/results["original_size_mb"]
        })
        
        # Step 2: Pruning
        logger.info("\n[2/3] Model Pruning")
        if self.config.pruning_type == "structured":
            pruned_model = self.pruner.prune_structured(student_model)
        else:
            pruned_model = self.pruner.prune_unstructured(student_model)
        
        pruned_size = self.get_model_size(pruned_model)
        logger.info(f"Pruned model size: {pruned_size:.1f} MB")
        results["optimization_steps"].append({
            "step": "pruning",
            "size_mb": pruned_size,
            "reduction": 1 - pruned_size/student_size
        })
        
        # Step 3: Quantization
        logger.info("\n[3/3] Quantization")
        if calibration_data is not None:
            quantized_model = self.quantizer.quantize_static(pruned_model, calibration_data)
        else:
            quantized_model = self.quantizer.quantize_dynamic(pruned_model)
        
        final_size = self.get_model_size(quantized_model)
        final_latency = self.measure_latency(quantized_model)
        
        logger.info(f"Quantized model size: {final_size:.1f} MB")
        results["optimization_steps"].append({
            "step": "quantization",
            "size_mb": final_size,
            "reduction": 1 - final_size/pruned_size
        })
        
        # Final results
        results["final_size_mb"] = final_size
        results["final_latency_ms"] = final_latency
        results["total_reduction"] = 1 - final_size/results["original_size_mb"]
        results["speedup"] = results["original_latency_ms"] / final_latency
        results["target_met"] = final_size <= self.config.target_model_size_mb
        
        self.print_optimization_summary(results)
        
        return results
    
    def get_model_size(self, model: nn.Module) -> float:
        """Get model size in MB"""
        param_size = 0
        buffer_size = 0
        
        for param in model.parameters():
            param_size += param.nelement() * param.element_size()
        
        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        
        size_mb = (param_size + buffer_size) / 1024 / 1024
        return size_mb
    
    def measure_latency(self, model: nn.Module, input_size: Tuple = (1, 3, 224, 224)) -> float:
        """Measure model inference latency"""
        model.eval()
        dummy_input = torch.randn(input_size)
        
        # Warmup
        for _ in range(10):
            with torch.no_grad():
                _ = model(dummy_input)
        
        # Measure
        times = []
        for _ in range(100):
            start = time.time()
            with torch.no_grad():
                _ = model(dummy_input)
            times.append((time.time() - start) * 1000)  # Convert to ms
        
        return np.median(times)
    
    def print_optimization_summary(self, results: Dict[str, Any]):
        """Print optimization results summary"""
        print("\n" + "="*60)
        print("OPTIMIZATION SUMMARY")
        print("="*60)
        
        print(f"\nModel Size Reduction:")
        print(f"  Original: {results['original_size_mb']:.1f} MB")
        print(f"  Optimized: {results['final_size_mb']:.1f} MB")
        print(f"  Reduction: {results['total_reduction']*100:.1f}%")
        print(f"  Target ({self.config.target_model_size_mb} MB): {'✅ MET' if results['target_met'] else '❌ NOT MET'}")
        
        print(f"\nLatency Improvement:")
        print(f"  Original: {results['original_latency_ms']:.1f} ms")
        print(f"  Optimized: {results['final_latency_ms']:.1f} ms")
        print(f"  Speedup: {results['speedup']:.1f}x")
        
        print(f"\nOptimization Breakdown:")
        for step in results["optimization_steps"]:
            print(f"  {step['step'].capitalize()}: {step['reduction']*100:.1f}% reduction")
        
        print("\n" + "="*60)
        if results['target_met']:
            print("✅ MODEL READY FOR PRODUCTION DEPLOYMENT")
        else:
            print("⚠️  FURTHER OPTIMIZATION NEEDED")
        print("="*60)


def test_optimization_pipeline():
    """Test the optimization pipeline"""
    
    # Create mock model
    class MockVLAModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(3, 64, 3)
            self.conv2 = nn.Conv2d(64, 128, 3)
            self.fc1 = nn.Linear(128 * 220 * 220, 512)
            self.fc2 = nn.Linear(512, 10)
            
        def forward(self, x):
            x = F.relu(self.conv1(x))
            x = F.relu(self.conv2(x))
            x = x.view(x.size(0), -1)
            x = F.relu(self.fc1(x))
            return self.fc2(x)
    
    # Initialize
    config = OptimizationConfig()
    pipeline = VLAOptimizationPipeline(config)
    model = MockVLAModel()
    
    # Create mock calibration data
    calibration_data = torch.randn(100, 3, 224, 224)
    
    # Run optimization
    results = pipeline.optimize_model(model, calibration_data)
    
    # Save results
    with open("optimization_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to optimization_results.json")


if __name__ == "__main__":
    test_optimization_pipeline()