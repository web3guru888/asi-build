"""
Learning Benchmarks for AGI Component Benchmark Suite

Implements comprehensive learning capability tests including:
- One-shot learning (rapid adaptation from single examples)
- Few-shot learning (learning from minimal examples)
- Continual learning (learning without catastrophic forgetting)
- Transfer learning (knowledge transfer across domains)
"""

import random
import numpy as np
import time
from typing import Dict, List, Any, Tuple, Optional, Callable
from dataclasses import dataclass
import json
import copy

from .core import BaseBenchmark, AGISystem, BenchmarkResult


@dataclass
class LearningTask:
    """Represents a learning task"""
    task_id: str
    domain: str
    task_type: str  # classification, regression, sequence_modeling
    examples: List[Dict[str, Any]]
    test_examples: List[Dict[str, Any]]
    meta_info: Dict[str, Any]


@dataclass
class ContinualLearningSequence:
    """Represents a sequence of tasks for continual learning"""
    sequence_id: str
    tasks: List[LearningTask]
    evaluation_points: List[int]  # Which tasks to evaluate after each step


class LearningBenchmarks(BaseBenchmark):
    """Comprehensive learning benchmarks"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.one_shot_tasks = self._generate_one_shot_tasks()
        self.few_shot_tasks = self._generate_few_shot_tasks()
        self.continual_tasks = self._generate_continual_tasks()
        self.transfer_tasks = self._generate_transfer_tasks()
    
    def run_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run all learning tests"""
        results = []
        
        # One-shot learning tests
        if self.config.get("one_shot_learning", {}).get("enabled", True):
            results.extend(self._run_one_shot_tests(system))
        
        # Few-shot learning tests
        if self.config.get("few_shot_learning", {}).get("enabled", True):
            results.extend(self._run_few_shot_tests(system))
        
        # Continual learning tests
        if self.config.get("continual_learning", {}).get("enabled", True):
            results.extend(self._run_continual_tests(system))
        
        # Transfer learning tests
        if self.config.get("transfer_learning", {}).get("enabled", True):
            results.extend(self._run_transfer_tests(system))
        
        return results
    
    def _run_one_shot_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run one-shot learning tests"""
        results = []
        config = self.config.get("one_shot_learning", {})
        
        for domain in config.get("domains", ["visual"]):
            for complexity in config.get("complexity_levels", ["simple"]):
                tasks = [t for t in self.one_shot_tasks 
                        if t.domain == domain and t.meta_info.get("complexity") == complexity]
                
                if tasks:
                    result = self._run_single_test(
                        lambda sys: self._test_one_shot_learning(sys, tasks),
                        f"one_shot_{domain}_{complexity}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_few_shot_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run few-shot learning tests"""
        results = []
        config = self.config.get("few_shot_learning", {})
        
        for shot_count in config.get("shot_counts", [5]):
            for domain in config.get("domains", ["classification"]):
                tasks = [t for t in self.few_shot_tasks if t.domain == domain]
                
                if tasks:
                    result = self._run_single_test(
                        lambda sys: self._test_few_shot_learning(sys, tasks, shot_count),
                        f"few_shot_{domain}_{shot_count}shot",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_continual_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run continual learning tests"""
        results = []
        config = self.config.get("continual_learning", {})
        
        for task_sequence in config.get("task_sequences", ["permuted_mnist"]):
            for replay_mechanism in config.get("replay_mechanisms", ["none"]):
                sequences = [s for s in self.continual_tasks 
                           if s.sequence_id.startswith(task_sequence)]
                
                if sequences:
                    result = self._run_single_test(
                        lambda sys: self._test_continual_learning(sys, sequences[0], replay_mechanism),
                        f"continual_{task_sequence}_{replay_mechanism}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_transfer_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run transfer learning tests"""
        results = []
        config = self.config.get("transfer_learning", {})
        
        for source_domain in config.get("source_domains", ["vision"]):
            for target_domain in config.get("target_domains", ["language"]):
                if source_domain != target_domain:
                    task_pairs = [(s, t) for s in self.transfer_tasks 
                                 if s.domain == source_domain
                                 for t in self.transfer_tasks
                                 if t.domain == target_domain]
                    
                    if task_pairs:
                        result = self._run_single_test(
                            lambda sys: self._test_transfer_learning(sys, task_pairs[0]),
                            f"transfer_{source_domain}_to_{target_domain}",
                            system,
                            max_score=100.0
                        )
                        results.append(result)
        
        return results
    
    def _test_one_shot_learning(self, system: AGISystem, tasks: List[LearningTask]) -> Dict[str, Any]:
        """Test one-shot learning capability"""
        total_accuracy = 0
        total_tasks = len(tasks)
        details = {"tasks_tested": total_tasks, "individual_results": []}
        
        for task in tasks:
            if not task.examples:
                continue
            
            # Use only the first example for training
            training_example = task.examples[0]
            test_examples = task.test_examples
            
            learning_task = {
                "type": "one_shot_learning",
                "domain": task.domain,
                "task_type": task.task_type,
                "training_example": training_example,
                "test_examples": test_examples,
                "meta_info": task.meta_info
            }
            
            try:
                response = system.process_learning_task(learning_task)
                predictions = response.get("predictions", [])
                
                accuracy = self._calculate_accuracy(predictions, test_examples, task.task_type)
                total_accuracy += accuracy
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "domain": task.domain,
                    "task_type": task.task_type,
                    "accuracy": accuracy,
                    "num_test_examples": len(test_examples),
                    "predictions": predictions[:5]  # Store first 5 predictions for analysis
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
        
        average_accuracy = total_accuracy / total_tasks if total_tasks > 0 else 0
        details["average_accuracy"] = average_accuracy
        
        # Test generalization if enabled
        if self.config.get("one_shot_learning", {}).get("generalization_tests", False):
            generalization_score = self._test_generalization(system, tasks)
            details["generalization_score"] = generalization_score
            # Weight generalization in final score
            final_score = (average_accuracy * 0.7) + (generalization_score * 0.3)
        else:
            final_score = average_accuracy
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_few_shot_learning(self, system: AGISystem, tasks: List[LearningTask], 
                               shot_count: int) -> Dict[str, Any]:
        """Test few-shot learning capability"""
        total_accuracy = 0
        total_tasks = len(tasks)
        details = {"tasks_tested": total_tasks, "shot_count": shot_count, "individual_results": []}
        
        for task in tasks:
            if len(task.examples) < shot_count:
                continue
            
            # Use first shot_count examples for training
            training_examples = task.examples[:shot_count]
            test_examples = task.test_examples
            
            learning_task = {
                "type": "few_shot_learning",
                "domain": task.domain,
                "task_type": task.task_type,
                "training_examples": training_examples,
                "test_examples": test_examples,
                "shot_count": shot_count,
                "meta_info": task.meta_info
            }
            
            try:
                response = system.process_learning_task(learning_task)
                predictions = response.get("predictions", [])
                
                accuracy = self._calculate_accuracy(predictions, test_examples, task.task_type)
                total_accuracy += accuracy
                
                # Calculate learning efficiency (accuracy per example)
                efficiency = accuracy / shot_count if shot_count > 0 else 0
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "domain": task.domain,
                    "task_type": task.task_type,
                    "accuracy": accuracy,
                    "efficiency": efficiency,
                    "num_training_examples": shot_count,
                    "num_test_examples": len(test_examples)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
        
        average_accuracy = total_accuracy / total_tasks if total_tasks > 0 else 0
        details["average_accuracy"] = average_accuracy
        
        # Test meta-learning if enabled
        if self.config.get("few_shot_learning", {}).get("meta_learning", False):
            meta_learning_score = self._test_meta_learning(system, tasks, shot_count)
            details["meta_learning_score"] = meta_learning_score
            # Weight meta-learning in final score
            final_score = (average_accuracy * 0.8) + (meta_learning_score * 0.2)
        else:
            final_score = average_accuracy
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_continual_learning(self, system: AGISystem, task_sequence: ContinualLearningSequence,
                                replay_mechanism: str) -> Dict[str, Any]:
        """Test continual learning capability"""
        details = {
            "sequence_id": task_sequence.sequence_id,
            "num_tasks": len(task_sequence.tasks),
            "replay_mechanism": replay_mechanism,
            "task_results": [],
            "forgetting_analysis": {}
        }
        
        task_accuracies = []  # Track accuracy on each task over time
        
        for i, current_task in enumerate(task_sequence.tasks):
            learning_task = {
                "type": "continual_learning",
                "domain": current_task.domain,
                "task_type": current_task.task_type,
                "training_examples": current_task.examples,
                "test_examples": current_task.test_examples,
                "task_index": i,
                "replay_mechanism": replay_mechanism,
                "meta_info": current_task.meta_info
            }
            
            try:
                # Train on current task
                response = system.process_learning_task(learning_task)
                
                # Evaluate on current task
                current_predictions = response.get("predictions", [])
                current_accuracy = self._calculate_accuracy(
                    current_predictions, current_task.test_examples, current_task.task_type
                )
                
                # Evaluate on all previous tasks to measure forgetting
                previous_accuracies = []
                for j in range(i):
                    prev_task = task_sequence.tasks[j]
                    eval_task = {
                        "type": "continual_evaluation",
                        "domain": prev_task.domain,
                        "task_type": prev_task.task_type,
                        "test_examples": prev_task.test_examples,
                        "task_index": j
                    }
                    
                    eval_response = system.process_learning_task(eval_task)
                    prev_predictions = eval_response.get("predictions", [])
                    prev_accuracy = self._calculate_accuracy(
                        prev_predictions, prev_task.test_examples, prev_task.task_type
                    )
                    previous_accuracies.append(prev_accuracy)
                
                task_accuracies.append({
                    "task_index": i,
                    "current_accuracy": current_accuracy,
                    "previous_accuracies": previous_accuracies
                })
                
                details["task_results"].append({
                    "task_index": i,
                    "task_id": current_task.task_id,
                    "current_accuracy": current_accuracy,
                    "previous_accuracies": previous_accuracies,
                    "average_previous_accuracy": np.mean(previous_accuracies) if previous_accuracies else 0
                })
            
            except Exception as e:
                details["task_results"].append({
                    "task_index": i,
                    "task_id": current_task.task_id,
                    "error": str(e)
                })
        
        # Calculate continual learning metrics
        metrics = self._calculate_continual_metrics(task_accuracies)
        details["forgetting_analysis"] = metrics
        
        # Final score combines average accuracy and forgetting resistance
        if metrics.get("average_accuracy", 0) > 0:
            forgetting_penalty = max(0, metrics.get("average_forgetting", 0))
            final_score = metrics["average_accuracy"] * (1 - forgetting_penalty)
        else:
            final_score = 0
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_transfer_learning(self, system: AGISystem, task_pair: Tuple[LearningTask, LearningTask]) -> Dict[str, Any]:
        """Test transfer learning capability"""
        source_task, target_task = task_pair
        
        details = {
            "source_domain": source_task.domain,
            "target_domain": target_task.domain,
            "source_task_id": source_task.task_id,
            "target_task_id": target_task.task_id
        }
        
        try:
            # Phase 1: Train on source task
            source_learning_task = {
                "type": "transfer_source",
                "domain": source_task.domain,
                "task_type": source_task.task_type,
                "training_examples": source_task.examples,
                "test_examples": source_task.test_examples,
                "meta_info": source_task.meta_info
            }
            
            source_response = system.process_learning_task(source_learning_task)
            source_predictions = source_response.get("predictions", [])
            source_accuracy = self._calculate_accuracy(
                source_predictions, source_task.test_examples, source_task.task_type
            )
            
            # Phase 2: Adapt to target task (with limited data)
            # Use only 20% of target training data to test transfer
            target_train_size = max(1, len(target_task.examples) // 5)
            target_training_examples = target_task.examples[:target_train_size]
            
            target_learning_task = {
                "type": "transfer_target",
                "domain": target_task.domain,
                "task_type": target_task.task_type,
                "training_examples": target_training_examples,
                "test_examples": target_task.test_examples,
                "source_knowledge": source_response.get("learned_representation", {}),
                "meta_info": target_task.meta_info
            }
            
            target_response = system.process_learning_task(target_learning_task)
            target_predictions = target_response.get("predictions", [])
            target_accuracy = self._calculate_accuracy(
                target_predictions, target_task.test_examples, target_task.task_type
            )
            
            # Compare with baseline (learning target task from scratch)
            baseline_task = {
                "type": "baseline_learning",
                "domain": target_task.domain,
                "task_type": target_task.task_type,
                "training_examples": target_training_examples,
                "test_examples": target_task.test_examples,
                "meta_info": target_task.meta_info
            }
            
            baseline_response = system.process_learning_task(baseline_task)
            baseline_predictions = baseline_response.get("predictions", [])
            baseline_accuracy = self._calculate_accuracy(
                baseline_predictions, target_task.test_examples, target_task.task_type
            )
            
            # Calculate transfer efficiency
            transfer_gain = target_accuracy - baseline_accuracy
            transfer_efficiency = transfer_gain / baseline_accuracy if baseline_accuracy > 0 else 0
            
            details.update({
                "source_accuracy": source_accuracy,
                "target_accuracy": target_accuracy,
                "baseline_accuracy": baseline_accuracy,
                "transfer_gain": transfer_gain,
                "transfer_efficiency": transfer_efficiency,
                "target_train_size": target_train_size
            })
            
            # Score based on both target performance and transfer efficiency
            performance_score = target_accuracy
            efficiency_bonus = max(0, transfer_efficiency * 20)  # Bonus for positive transfer
            final_score = performance_score + efficiency_bonus
            
        except Exception as e:
            details["error"] = str(e)
            final_score = 0
        
        return {
            "score": min(100, final_score),  # Cap at 100
            "success": final_score > 0,
            "details": details
        }
    
    def _generate_one_shot_tasks(self) -> List[LearningTask]:
        """Generate one-shot learning tasks"""
        tasks = []
        
        # Visual classification tasks
        visual_tasks = [
            {
                "task_id": "visual_shape_classify_1",
                "domain": "visual",
                "task_type": "classification",
                "complexity": "simple",
                "examples": [{"input": [1, 0, 1, 0], "output": "square"}],
                "test_examples": [
                    {"input": [1, 0, 1, 0], "expected": "square"},
                    {"input": [1, 1, 1, 1], "expected": "square"},
                    {"input": [0, 1, 0, 1], "expected": "triangle"}
                ]
            },
            {
                "task_id": "visual_color_classify_1",
                "domain": "visual", 
                "task_type": "classification",
                "complexity": "simple",
                "examples": [{"input": [255, 0, 0], "output": "red"}],
                "test_examples": [
                    {"input": [255, 0, 0], "expected": "red"},
                    {"input": [250, 10, 5], "expected": "red"},
                    {"input": [0, 255, 0], "expected": "green"}
                ]
            }
        ]
        
        for task_data in visual_tasks:
            tasks.append(LearningTask(
                task_id=task_data["task_id"],
                domain=task_data["domain"],
                task_type=task_data["task_type"],
                examples=task_data["examples"],
                test_examples=task_data["test_examples"],
                meta_info={"complexity": task_data["complexity"]}
            ))
        
        # Linguistic tasks
        linguistic_tasks = [
            {
                "task_id": "linguistic_sentiment_1",
                "domain": "linguistic",
                "task_type": "classification",
                "complexity": "medium",
                "examples": [{"input": "I love this movie", "output": "positive"}],
                "test_examples": [
                    {"input": "I love this book", "expected": "positive"},
                    {"input": "I hate this song", "expected": "negative"},
                    {"input": "This is okay", "expected": "neutral"}
                ]
            }
        ]
        
        for task_data in linguistic_tasks:
            tasks.append(LearningTask(
                task_id=task_data["task_id"],
                domain=task_data["domain"],
                task_type=task_data["task_type"],
                examples=task_data["examples"],
                test_examples=task_data["test_examples"],
                meta_info={"complexity": task_data["complexity"]}
            ))
        
        return tasks
    
    def _generate_few_shot_tasks(self) -> List[LearningTask]:
        """Generate few-shot learning tasks"""
        tasks = []
        
        # Classification tasks
        classification_tasks = [
            {
                "task_id": "classification_animals",
                "domain": "classification",
                "examples": [
                    {"input": [1, 1, 0, 1], "output": "mammal"},
                    {"input": [1, 0, 1, 0], "output": "bird"},
                    {"input": [0, 0, 1, 1], "output": "fish"},
                    {"input": [1, 1, 0, 0], "output": "mammal"},
                    {"input": [1, 0, 1, 1], "output": "bird"}
                ],
                "test_examples": [
                    {"input": [1, 1, 0, 1], "expected": "mammal"},
                    {"input": [1, 0, 1, 0], "expected": "bird"},
                    {"input": [0, 0, 1, 1], "expected": "fish"}
                ]
            }
        ]
        
        for task_data in classification_tasks:
            tasks.append(LearningTask(
                task_id=task_data["task_id"],
                domain="classification",
                task_type="classification",
                examples=task_data["examples"],
                test_examples=task_data["test_examples"],
                meta_info={}
            ))
        
        # Regression tasks
        regression_tasks = [
            {
                "task_id": "regression_linear",
                "domain": "regression",
                "examples": [
                    {"input": [1], "output": [2]},
                    {"input": [2], "output": [4]},
                    {"input": [3], "output": [6]},
                    {"input": [4], "output": [8]},
                    {"input": [5], "output": [10]}
                ],
                "test_examples": [
                    {"input": [6], "expected": [12]},
                    {"input": [7], "expected": [14]},
                    {"input": [0], "expected": [0]}
                ]
            }
        ]
        
        for task_data in regression_tasks:
            tasks.append(LearningTask(
                task_id=task_data["task_id"],
                domain="regression",
                task_type="regression",
                examples=task_data["examples"],
                test_examples=task_data["test_examples"],
                meta_info={}
            ))
        
        return tasks
    
    def _generate_continual_tasks(self) -> List[ContinualLearningSequence]:
        """Generate continual learning task sequences"""
        sequences = []
        
        # Permuted MNIST-like sequence
        permuted_tasks = []
        for i in range(5):
            task = LearningTask(
                task_id=f"permuted_mnist_task_{i}",
                domain="vision",
                task_type="classification",
                examples=[
                    {"input": [random.random() for _ in range(10)], "output": random.randint(0, 9)}
                    for _ in range(20)
                ],
                test_examples=[
                    {"input": [random.random() for _ in range(10)], "expected": random.randint(0, 9)}
                    for _ in range(10)
                ],
                meta_info={"permutation_id": i}
            )
            permuted_tasks.append(task)
        
        sequences.append(ContinualLearningSequence(
            sequence_id="permuted_mnist_sequence",
            tasks=permuted_tasks,
            evaluation_points=list(range(5))
        ))
        
        return sequences
    
    def _generate_transfer_tasks(self) -> List[LearningTask]:
        """Generate transfer learning tasks"""
        tasks = []
        
        # Vision tasks
        vision_tasks = [
            {
                "task_id": "vision_shape_recognition",
                "domain": "vision",
                "examples": [
                    {"input": [1, 0, 1, 0], "output": "square"},
                    {"input": [1, 1, 0, 0], "output": "triangle"}
                ],
                "test_examples": [
                    {"input": [1, 0, 1, 0], "expected": "square"}
                ]
            }
        ]
        
        # Language tasks
        language_tasks = [
            {
                "task_id": "language_sentiment",
                "domain": "language",
                "examples": [
                    {"input": "good", "output": "positive"},
                    {"input": "bad", "output": "negative"}
                ],
                "test_examples": [
                    {"input": "excellent", "expected": "positive"}
                ]
            }
        ]
        
        all_task_data = vision_tasks + language_tasks
        
        for task_data in all_task_data:
            tasks.append(LearningTask(
                task_id=task_data["task_id"],
                domain=task_data["domain"],
                task_type="classification",
                examples=task_data["examples"],
                test_examples=task_data["test_examples"],
                meta_info={}
            ))
        
        return tasks
    
    def _calculate_accuracy(self, predictions: List[Any], test_examples: List[Dict[str, Any]], 
                           task_type: str) -> float:
        """Calculate accuracy for predictions"""
        if not predictions or not test_examples:
            return 0.0
        
        correct = 0
        total = min(len(predictions), len(test_examples))
        
        for i in range(total):
            pred = predictions[i]
            expected = test_examples[i].get("expected")
            
            if task_type == "classification":
                if pred == expected:
                    correct += 1
            elif task_type == "regression":
                # For regression, allow some tolerance
                if isinstance(pred, (list, tuple)) and isinstance(expected, (list, tuple)):
                    if len(pred) == len(expected):
                        mse = np.mean([(p - e) ** 2 for p, e in zip(pred, expected)])
                        if mse < 0.1:  # Threshold for "correct"
                            correct += 1
                elif isinstance(pred, (int, float)) and isinstance(expected, (int, float)):
                    if abs(pred - expected) < 0.1:
                        correct += 1
        
        return (correct / total) * 100 if total > 0 else 0
    
    def _test_generalization(self, system: AGISystem, tasks: List[LearningTask]) -> float:
        """Test generalization capability beyond training examples"""
        # This is a simplified generalization test
        # In practice, this would involve more sophisticated out-of-distribution testing
        generalization_scores = []
        
        for task in tasks:
            if task.examples and task.test_examples:
                # Create modified test examples that are slightly different
                modified_examples = self._create_modified_examples(task.test_examples)
                
                generalization_task = {
                    "type": "generalization_test",
                    "domain": task.domain,
                    "task_type": task.task_type,
                    "training_example": task.examples[0],
                    "test_examples": modified_examples,
                    "meta_info": task.meta_info
                }
                
                try:
                    response = system.process_learning_task(generalization_task)
                    predictions = response.get("predictions", [])
                    accuracy = self._calculate_accuracy(predictions, modified_examples, task.task_type)
                    generalization_scores.append(accuracy)
                except:
                    generalization_scores.append(0)
        
        return np.mean(generalization_scores) if generalization_scores else 0
    
    def _test_meta_learning(self, system: AGISystem, tasks: List[LearningTask], shot_count: int) -> float:
        """Test meta-learning capability (learning to learn)"""
        # Simplified meta-learning test
        # Measure improvement in learning speed across similar tasks
        
        if len(tasks) < 2:
            return 0
        
        learning_speeds = []
        
        for i, task in enumerate(tasks[:3]):  # Test on first 3 tasks
            meta_task = {
                "type": "meta_learning",
                "domain": task.domain,
                "task_type": task.task_type,
                "training_examples": task.examples[:shot_count],
                "test_examples": task.test_examples,
                "task_index": i,
                "previous_tasks": tasks[:i] if i > 0 else [],
                "meta_info": task.meta_info
            }
            
            try:
                start_time = time.time()
                response = system.process_learning_task(meta_task)
                learning_time = time.time() - start_time
                
                predictions = response.get("predictions", [])
                accuracy = self._calculate_accuracy(predictions, task.test_examples, task.task_type)
                
                # Learning speed = accuracy / time (higher is better)
                learning_speed = accuracy / max(learning_time, 0.001)
                learning_speeds.append(learning_speed)
            except:
                learning_speeds.append(0)
        
        # Meta-learning score is improvement in learning speed
        if len(learning_speeds) >= 2:
            improvement = (learning_speeds[-1] - learning_speeds[0]) / max(learning_speeds[0], 0.001)
            return max(0, improvement * 100)  # Convert to percentage
        
        return 0
    
    def _calculate_continual_metrics(self, task_accuracies: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate continual learning metrics"""
        if not task_accuracies:
            return {"average_accuracy": 0, "average_forgetting": 0, "backward_transfer": 0}
        
        # Average accuracy on all tasks
        all_accuracies = []
        for task_result in task_accuracies:
            all_accuracies.append(task_result["current_accuracy"])
            all_accuracies.extend(task_result["previous_accuracies"])
        
        average_accuracy = np.mean(all_accuracies) if all_accuracies else 0
        
        # Average forgetting (how much performance drops on previous tasks)
        forgetting_values = []
        for i, task_result in enumerate(task_accuracies[1:], 1):  # Skip first task
            if task_result["previous_accuracies"]:
                # Compare current performance on old tasks with when they were learned
                for j, prev_acc in enumerate(task_result["previous_accuracies"]):
                    original_acc = task_accuracies[j]["current_accuracy"]
                    forgetting = max(0, original_acc - prev_acc) / max(original_acc, 0.001)
                    forgetting_values.append(forgetting)
        
        average_forgetting = np.mean(forgetting_values) if forgetting_values else 0
        
        # Backward transfer (improvement on old tasks due to new learning)
        backward_transfer = 0  # Simplified - would need more complex analysis
        
        return {
            "average_accuracy": average_accuracy,
            "average_forgetting": average_forgetting,
            "backward_transfer": backward_transfer
        }
    
    def _create_modified_examples(self, examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create modified examples for generalization testing"""
        modified = []
        for example in examples:
            if "input" in example:
                # Add small noise to inputs
                if isinstance(example["input"], list):
                    noisy_input = [x + random.uniform(-0.1, 0.1) if isinstance(x, (int, float)) else x 
                                  for x in example["input"]]
                    modified.append({
                        "input": noisy_input,
                        "expected": example["expected"]
                    })
                else:
                    modified.append(example)
            else:
                modified.append(example)
        
        return modified