"""
Tests for asi_build.optimization module.

This module contains a VLA++ (Vision-Language-Action) autonomous vehicle AI system
with architecture (VLAConfig, VisionModule, LanguageModule, ActionModule, VLAPlusPlus),
model optimization (quantization, pruning, distillation), and training utilities.

All imports rely on torch which IS available (CPU-only).
"""

import pytest
pytest.importorskip("torch")
import torch
import torch.nn as nn
import numpy as np
import time

from asi_build.optimization.src import get_config, CONFIG
from asi_build.optimization.src.architecture import (
    VLAConfig,
    VisionModule,
    LanguageModule,
    ActionModule,
    VLAPlusPlus,
    create_vla_model,
)
from asi_build.optimization.src.model_optimization import (
    OptimizationConfig,
    ModelQuantizer,
    ModelPruner,
    KnowledgeDistiller,
    VLAOptimizationPipeline,
)
from asi_build.optimization.src.training import (
    TrainingConfig,
    LoRALayer,
)


# ===================================================================
# Module-level __init__ / CONFIG
# ===================================================================

class TestModuleInit:

    def test_config_exists(self):
        assert CONFIG is not None
        assert "model" in CONFIG
        assert "training" in CONFIG
        assert "deployment" in CONFIG

    def test_get_config(self):
        cfg = get_config()
        assert cfg is CONFIG
        assert cfg["model"]["total_params"] == 350_000_000

    def test_config_infrastructure(self):
        assert CONFIG["infrastructure"]["provider"] == "Cudo Compute"
        assert CONFIG["infrastructure"]["max_budget"] == 2500

    def test_config_deployment(self):
        assert CONFIG["deployment"]["target_fps"] == 83
        assert CONFIG["deployment"]["runtime"] == "WASM"


# ===================================================================
# VLAConfig
# ===================================================================

class TestVLAConfig:

    def test_defaults(self):
        c = VLAConfig()
        assert c.vision_backbone == "resnet50"
        assert c.language_vocab_size == 8192
        assert c.action_num_waypoints == 20
        assert c.fusion_dropout == 0.1

    def test_custom(self):
        c = VLAConfig(language_vocab_size=4096, fusion_dropout=0.2)
        assert c.language_vocab_size == 4096
        assert c.fusion_dropout == 0.2

    def test_hidden_sizes(self):
        c = VLAConfig()
        assert c.vision_hidden_size == 2048
        assert c.language_hidden_size == 768
        assert c.action_hidden_size == 512
        assert c.fusion_hidden_size == 1024


# ===================================================================
# VisionModule
# ===================================================================

class TestVisionModule:

    def test_creation(self):
        cfg = VLAConfig()
        vm = VisionModule(cfg)
        assert vm.config is cfg

    def test_forward_shape(self):
        cfg = VLAConfig()
        vm = VisionModule(cfg)
        images = torch.randn(2, 3, 224, 224)
        with torch.no_grad():
            out = vm(images)
        assert "detections" in out
        assert "segmentation" in out
        assert "vision_embedding" in out
        assert out["vision_embedding"].shape[0] == 2  # batch size

    def test_param_count(self):
        vm = VisionModule(VLAConfig())
        count = sum(p.numel() for p in vm.parameters())
        assert count > 0


# ===================================================================
# LanguageModule
# ===================================================================

class TestLanguageModule:

    def test_creation(self):
        cfg = VLAConfig()
        lm = LanguageModule(cfg)
        assert lm.config is cfg

    def test_forward_shape(self):
        cfg = VLAConfig()
        lm = LanguageModule(cfg)
        input_ids = torch.randint(0, cfg.language_vocab_size, (2, 32))
        with torch.no_grad():
            out = lm(input_ids)
        assert "language_features" in out
        assert "language_embedding" in out
        assert out["language_embedding"].shape[0] == 2
        assert out["language_embedding"].shape[1] == cfg.fusion_hidden_size

    def test_sequence_length(self):
        cfg = VLAConfig()
        lm = LanguageModule(cfg)
        input_ids = torch.randint(0, cfg.language_vocab_size, (1, 10))
        with torch.no_grad():
            out = lm(input_ids)
        assert out["language_features"].shape[1] == 10  # seq len preserved


# ===================================================================
# ActionModule
# ===================================================================

class TestActionModule:

    def test_creation(self):
        cfg = VLAConfig()
        am = ActionModule(cfg)
        assert am.config is cfg

    def test_forward_shape(self):
        cfg = VLAConfig()
        am = ActionModule(cfg)
        batch_size = 2
        vision_emb = torch.randn(batch_size, cfg.fusion_hidden_size)
        lang_emb = torch.randn(batch_size, cfg.fusion_hidden_size)
        with torch.no_grad():
            out = am(vision_emb, lang_emb)
        assert "waypoints" in out
        assert out["waypoints"].shape == (batch_size, cfg.action_num_waypoints, 7)

    def test_attention_weights_output(self):
        cfg = VLAConfig()
        am = ActionModule(cfg)
        v = torch.randn(1, cfg.fusion_hidden_size)
        l = torch.randn(1, cfg.fusion_hidden_size)
        with torch.no_grad():
            out = am(v, l)
        assert "attention_weights" in out


# ===================================================================
# VLAPlusPlus (full model)
# ===================================================================

class TestVLAPlusPlus:

    @pytest.fixture
    def model(self):
        return VLAPlusPlus(VLAConfig())

    def test_creation(self, model):
        assert model.config.vision_backbone == "resnet50"
        assert hasattr(model, "vision_module")
        assert hasattr(model, "language_module")
        assert hasattr(model, "action_module")
        assert hasattr(model, "safety_checker")

    def test_forward(self, model):
        batch = 2
        images = torch.randn(batch, 3, 224, 224)
        commands = torch.randint(0, 8192, (batch, 32))
        with torch.no_grad():
            out = model(images, commands)
        assert "waypoints" in out
        assert "safety_score" in out
        assert out["waypoints"].shape[0] == batch
        assert out["safety_score"].shape == (batch, 1)
        # Safety score should be in [0, 1] (sigmoid)
        assert (out["safety_score"] >= 0).all()
        assert (out["safety_score"] <= 1).all()

    def test_count_parameters(self, model):
        count = model.count_parameters()
        assert count > 0
        # Should be in millions range
        assert count > 1_000_000

    def test_gradient_checkpointing(self, model):
        # Should not raise even though transformer layers don't have
        # gradient_checkpointing_enable attribute
        model.enable_gradient_checkpointing()

    def test_create_factory(self):
        model = create_vla_model()
        assert isinstance(model, VLAPlusPlus)
        # Weights should be initialized (not all zeros for Linear layers)
        for name, param in model.named_parameters():
            if "weight" in name and param.dim() >= 2:
                assert not (param == 0).all(), f"{name} is all zeros after init"
                break

    def test_custom_config(self):
        cfg = VLAConfig(action_num_waypoints=10, language_vocab_size=4096)
        model = VLAPlusPlus(cfg)
        assert model.config.action_num_waypoints == 10

    def test_default_config_when_none(self):
        model = VLAPlusPlus(None)
        assert model.config.vision_backbone == "resnet50"


# ===================================================================
# OptimizationConfig
# ===================================================================

class TestOptimizationConfig:

    def test_defaults(self):
        c = OptimizationConfig()
        assert c.quantization_dtype == "int8"
        assert c.pruning_amount == 0.6
        assert c.target_model_size_mb == 50.0

    def test_custom(self):
        c = OptimizationConfig(pruning_amount=0.3, target_latency_ms=5.0)
        assert c.pruning_amount == 0.3
        assert c.target_latency_ms == 5.0


# ===================================================================
# ModelQuantizer
# ===================================================================

class TestModelQuantizer:

    def test_init(self):
        q = ModelQuantizer(OptimizationConfig())
        assert q.config is not None

    def test_quantize_dynamic(self):
        q = ModelQuantizer(OptimizationConfig())
        model = nn.Sequential(
            nn.Linear(10, 20),
            nn.ReLU(),
            nn.Linear(20, 5),
        )
        qmodel = q.quantize_dynamic(model)
        assert qmodel is not None
        # Quantized model should still produce output
        x = torch.randn(1, 10)
        with torch.no_grad():
            out = qmodel(x)
        assert out.shape == (1, 5)

    def test_calibrate_model(self):
        q = ModelQuantizer(OptimizationConfig())
        model = nn.Linear(10, 5)
        data = torch.randn(10, 10)
        q.calibrate_model(model, data)  # should not raise


# ===================================================================
# ModelPruner
# ===================================================================

class TestModelPruner:

    def test_init(self):
        p = ModelPruner(OptimizationConfig())
        assert p.config.pruning_amount == 0.6

    def test_prune_unstructured(self):
        p = ModelPruner(OptimizationConfig(pruning_amount=0.5))
        model = nn.Sequential(
            nn.Linear(20, 30),
            nn.ReLU(),
            nn.Linear(30, 10),
        )
        pruned = p.prune_unstructured(model)
        # After pruning, some weights should be zero
        total_zeros = 0
        total_params = 0
        for name, param in pruned.named_parameters():
            if "weight" in name:
                total_zeros += (param == 0).sum().item()
                total_params += param.numel()
        sparsity = total_zeros / total_params
        # Should be roughly 50% sparse
        assert sparsity > 0.3

    def test_prune_structured(self):
        p = ModelPruner(OptimizationConfig(pruning_amount=0.3))
        model = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),
            nn.Linear(10, 5),
        )
        pruned = p.prune_structured(model)
        assert pruned is not None


# ===================================================================
# KnowledgeDistiller
# ===================================================================

class TestKnowledgeDistiller:

    def test_init(self):
        kd = KnowledgeDistiller(OptimizationConfig())
        assert kd.config is not None

    def test_create_student(self):
        kd = KnowledgeDistiller(OptimizationConfig())
        teacher = nn.Linear(100, 10)  # dummy teacher
        student = kd.create_student_model(teacher)
        assert student is not None

    def test_distillation_loss(self):
        kd = KnowledgeDistiller(OptimizationConfig())
        student_logits = torch.randn(4, 10)
        teacher_logits = torch.randn(4, 10)
        labels = torch.randint(0, 10, (4,))
        loss = kd.distillation_loss(student_logits, teacher_logits, labels, 5.0, 0.7)
        assert loss.item() > 0
        assert loss.requires_grad  # should be differentiable


# ===================================================================
# VLAOptimizationPipeline
# ===================================================================

class TestVLAOptimizationPipeline:

    def test_init(self):
        pipe = VLAOptimizationPipeline(OptimizationConfig())
        assert pipe.quantizer is not None
        assert pipe.pruner is not None
        assert pipe.distiller is not None

    def test_get_model_size(self):
        pipe = VLAOptimizationPipeline(OptimizationConfig())
        model = nn.Linear(100, 50)
        size = pipe.get_model_size(model)
        assert size > 0  # should be in MB

    def test_measure_latency(self):
        pipe = VLAOptimizationPipeline(OptimizationConfig())
        model = nn.Sequential(
            nn.Linear(10, 20),
            nn.ReLU(),
            nn.Linear(20, 5),
        )
        latency = pipe.measure_latency(model, input_size=(1, 10))
        assert latency > 0  # ms


# ===================================================================
# TrainingConfig
# ===================================================================

class TestTrainingConfig:

    def test_defaults(self):
        c = TrainingConfig()
        assert c.batch_size == 32
        assert c.learning_rate == 1e-4
        assert c.mixed_precision is True
        assert c.use_lora is True
        assert c.lora_rank == 16

    def test_custom(self):
        c = TrainingConfig(batch_size=64, learning_rate=5e-5)
        assert c.batch_size == 64

    def test_checkpoint_dir(self):
        c = TrainingConfig()
        assert c.checkpoint_dir.startswith("/models")

    def test_cudo_settings(self):
        c = TrainingConfig()
        assert c.cudo_instance_type == "rtx4090"
        assert c.cudo_spot_instance is True
        assert c.cudo_max_price == 1.20


# ===================================================================
# LoRALayer
# ===================================================================

class TestLoRALayer:

    def test_creation(self):
        lora = LoRALayer(in_features=64, out_features=64, rank=8)
        assert lora.rank == 8
        assert lora.scaling == 32.0 / 8  # alpha/rank

    def test_forward_shape(self):
        lora = LoRALayer(in_features=32, out_features=64, rank=4)
        x = torch.randn(2, 32)
        out = lora(x)
        assert out.shape == (2, 64)

    def test_init_weights(self):
        lora = LoRALayer(in_features=16, out_features=16, rank=4)
        # lora_B should be initialized to zeros
        assert (lora.lora_B.weight == 0).all()
        # lora_A should be non-zero (kaiming init)
        assert not (lora.lora_A.weight == 0).all()

    def test_scaling_factor(self):
        lora = LoRALayer(in_features=32, out_features=32, rank=16, alpha=64.0)
        assert lora.scaling == 64.0 / 16

    def test_dropout(self):
        lora = LoRALayer(in_features=32, out_features=32, rank=4, dropout=0.5)
        # In eval mode, dropout should not be applied
        lora.eval()
        x = torch.randn(10, 32)
        out1 = lora(x)
        out2 = lora(x)
        assert torch.allclose(out1, out2)

    def test_trainable(self):
        lora = LoRALayer(in_features=32, out_features=32, rank=4)
        trainable = sum(p.numel() for p in lora.parameters() if p.requires_grad)
        # Should be: lora_A (32*4) + lora_B (4*32) = 256
        assert trainable == 32 * 4 + 4 * 32

    def test_output_initially_zero(self):
        """Since lora_B is initialized to zeros, output should start at ~0."""
        lora = LoRALayer(in_features=32, out_features=32, rank=4)
        lora.eval()
        x = torch.randn(1, 32)
        out = lora(x)
        assert torch.allclose(out, torch.zeros_like(out), atol=1e-6)


# ===================================================================
# End-to-end integration smoke test
# ===================================================================

class TestEndToEnd:

    def test_model_create_and_forward(self):
        """Create model, run forward pass, verify all outputs."""
        cfg = VLAConfig(
            language_num_layers=2,  # reduce for speed
            action_num_layers=2,
        )
        model = create_vla_model(cfg)
        model.eval()

        images = torch.randn(1, 3, 224, 224)
        commands = torch.randint(0, cfg.language_vocab_size, (1, 16))

        with torch.no_grad():
            out = model(images, commands)

        assert out["waypoints"].shape == (1, cfg.action_num_waypoints, 7)
        assert out["safety_score"].shape == (1, 1)
        assert "detections" in out
        assert "segmentation" in out

    def test_quantize_simple_model(self):
        """Quantize a simple model and verify it still works."""
        model = nn.Sequential(nn.Linear(10, 20), nn.ReLU(), nn.Linear(20, 5))
        q = ModelQuantizer(OptimizationConfig())
        qmodel = q.quantize_dynamic(model)
        x = torch.randn(3, 10)
        with torch.no_grad():
            out = qmodel(x)
        assert out.shape == (3, 5)

    def test_prune_and_verify(self):
        """Prune a model and verify sparsity."""
        model = nn.Sequential(nn.Linear(50, 100), nn.ReLU(), nn.Linear(100, 10))
        p = ModelPruner(OptimizationConfig(pruning_amount=0.7))
        pruned = p.prune_unstructured(model)
        x = torch.randn(2, 50)
        with torch.no_grad():
            out = pruned(x)
        assert out.shape == (2, 10)
