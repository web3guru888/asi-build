"""
Federated Meta-Learning

Implementation of federated meta-learning algorithms including FedMAML,
FedReptile, and other gradient-based meta-learning approaches.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import tensorflow as tf

from ..aggregation.base_aggregator import BaseAggregator
from ..core.base import FederatedClient, FederatedModel, FederatedServer
from ..core.exceptions import FederatedLearningError, ModelError


class MetaLearningStrategy(ABC):
    """Abstract base class for meta-learning strategies."""

    @abstractmethod
    def meta_update(
        self,
        global_weights: List[np.ndarray],
        client_gradients: List[List[np.ndarray]],
        meta_lr: float,
    ) -> List[np.ndarray]:
        """Perform meta-update given client gradients."""
        pass

    @abstractmethod
    def inner_loop_update(
        self,
        initial_weights: List[np.ndarray],
        task_data: tf.data.Dataset,
        inner_lr: float,
        inner_steps: int,
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """Perform inner loop adaptation and return final weights and gradients."""
        pass


class MAMLStrategy(MetaLearningStrategy):
    """Model-Agnostic Meta-Learning (MAML) strategy."""

    def __init__(self, first_order: bool = False):
        self.first_order = first_order
        self.logger = logging.getLogger("MAML")

    def meta_update(
        self,
        global_weights: List[np.ndarray],
        client_gradients: List[List[np.ndarray]],
        meta_lr: float,
    ) -> List[np.ndarray]:
        """MAML meta-update using aggregated gradients."""
        if not client_gradients:
            return global_weights

        # Average gradients across clients
        averaged_gradients = []
        num_layers = len(client_gradients[0])

        for layer_idx in range(num_layers):
            layer_gradients = [grad_list[layer_idx] for grad_list in client_gradients]
            avg_gradient = np.mean(layer_gradients, axis=0)
            averaged_gradients.append(avg_gradient)

        # Apply meta-update
        updated_weights = []
        for weight, gradient in zip(global_weights, averaged_gradients):
            updated_weight = weight - meta_lr * gradient
            updated_weights.append(updated_weight)

        return updated_weights

    def inner_loop_update(
        self,
        initial_weights: List[np.ndarray],
        task_data: tf.data.Dataset,
        inner_lr: float,
        inner_steps: int,
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """MAML inner loop adaptation."""
        # This is a simplified version - in practice, you'd need actual model and gradients
        current_weights = [w.copy() for w in initial_weights]

        # Simulate inner loop updates
        for step in range(inner_steps):
            # In real implementation:
            # 1. Forward pass with current weights
            # 2. Compute loss and gradients
            # 3. Update weights with inner_lr
            pass

        # Compute meta-gradients (difference between final and initial weights)
        meta_gradients = []
        for initial, final in zip(initial_weights, current_weights):
            meta_grad = (final - initial) / inner_lr  # Simplified
            meta_gradients.append(meta_grad)

        return current_weights, meta_gradients


class ReptileStrategy(MetaLearningStrategy):
    """Reptile meta-learning strategy."""

    def __init__(self):
        self.logger = logging.getLogger("Reptile")

    def meta_update(
        self,
        global_weights: List[np.ndarray],
        client_gradients: List[List[np.ndarray]],
        meta_lr: float,
    ) -> List[np.ndarray]:
        """Reptile meta-update using weight differences."""
        # Reptile uses weight differences rather than gradients
        # This implementation assumes client_gradients actually contains weight differences
        if not client_gradients:
            return global_weights

        # Average weight differences
        averaged_differences = []
        num_layers = len(client_gradients[0])

        for layer_idx in range(num_layers):
            layer_differences = [diff_list[layer_idx] for diff_list in client_gradients]
            avg_difference = np.mean(layer_differences, axis=0)
            averaged_differences.append(avg_difference)

        # Apply Reptile update
        updated_weights = []
        for weight, difference in zip(global_weights, averaged_differences):
            updated_weight = weight + meta_lr * difference
            updated_weights.append(updated_weight)

        return updated_weights

    def inner_loop_update(
        self,
        initial_weights: List[np.ndarray],
        task_data: tf.data.Dataset,
        inner_lr: float,
        inner_steps: int,
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """Reptile inner loop adaptation."""
        current_weights = [w.copy() for w in initial_weights]

        # Simulate SGD updates on task
        for step in range(inner_steps):
            # In real implementation: perform SGD steps
            pass

        # Compute weight differences for Reptile
        weight_differences = []
        for initial, final in zip(initial_weights, current_weights):
            difference = final - initial
            weight_differences.append(difference)

        return current_weights, weight_differences


class FOMAMLStrategy(MetaLearningStrategy):
    """First-Order MAML (FOMAML) strategy."""

    def __init__(self):
        self.logger = logging.getLogger("FOMAML")

    def meta_update(
        self,
        global_weights: List[np.ndarray],
        client_gradients: List[List[np.ndarray]],
        meta_lr: float,
    ) -> List[np.ndarray]:
        """FOMAML meta-update (same as MAML but with first-order gradients)."""
        if not client_gradients:
            return global_weights

        # Average first-order gradients
        averaged_gradients = []
        num_layers = len(client_gradients[0])

        for layer_idx in range(num_layers):
            layer_gradients = [grad_list[layer_idx] for grad_list in client_gradients]
            avg_gradient = np.mean(layer_gradients, axis=0)
            averaged_gradients.append(avg_gradient)

        # Apply meta-update
        updated_weights = []
        for weight, gradient in zip(global_weights, averaged_gradients):
            updated_weight = weight - meta_lr * gradient
            updated_weights.append(updated_weight)

        return updated_weights

    def inner_loop_update(
        self,
        initial_weights: List[np.ndarray],
        task_data: tf.data.Dataset,
        inner_lr: float,
        inner_steps: int,
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """FOMAML inner loop (ignores second-order gradients)."""
        current_weights = [w.copy() for w in initial_weights]

        # Final step gradients only (first-order approximation)
        final_gradients = []
        for weight in current_weights:
            # Simulate final gradient computation
            grad = np.random.normal(0, 0.01, weight.shape)  # Placeholder
            final_gradients.append(grad)

        return current_weights, final_gradients


class FedMAMLAggregator(BaseAggregator):
    """Aggregator for Federated MAML."""

    def __init__(self, aggregator_id: str = "fedmaml", config: Dict[str, Any] = None):
        super().__init__(aggregator_id, config)

        # Meta-learning parameters
        self.meta_lr = self.config.get("meta_lr", 0.01)
        self.inner_lr = self.config.get("inner_lr", 0.1)
        self.inner_steps = self.config.get("inner_steps", 5)
        self.strategy_type = self.config.get("strategy", "maml")

        # Initialize meta-learning strategy
        self.strategy = self._create_strategy()

        # Meta-learning state
        self.meta_learning_history = []

        self.logger.info(f"FedMAML aggregator initialized with strategy: {self.strategy_type}")

    def _create_strategy(self) -> MetaLearningStrategy:
        """Create the meta-learning strategy."""
        if self.strategy_type.lower() == "maml":
            return MAMLStrategy(first_order=False)
        elif self.strategy_type.lower() == "fomaml":
            return FOMAMLStrategy()
        elif self.strategy_type.lower() == "reptile":
            return ReptileStrategy()
        else:
            raise ValueError(f"Unknown meta-learning strategy: {self.strategy_type}")

    def aggregate(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate client updates using meta-learning."""
        start_time = time.time()

        # Validate updates
        self.validate_updates(client_updates)

        # Extract meta-learning specific information
        global_weights = client_updates[0].get("global_weights")
        if global_weights is None:
            raise FederatedLearningError("Global weights required for meta-learning")

        client_gradients = []
        client_adapted_weights = []
        meta_learning_metrics = []

        for update in client_updates:
            # Extract meta-gradients or weight differences
            meta_gradients = update.get("meta_gradients", [])
            adapted_weights = update.get("adapted_weights", [])
            metrics = update.get("meta_metrics", {})

            if meta_gradients:
                client_gradients.append(meta_gradients)
            if adapted_weights:
                client_adapted_weights.append(adapted_weights)

            meta_learning_metrics.append(metrics)

        # Perform meta-update
        if client_gradients:
            updated_global_weights = self.strategy.meta_update(
                global_weights, client_gradients, self.meta_lr
            )
        else:
            # Fallback to standard aggregation if no meta-gradients
            self.logger.warning("No meta-gradients found, falling back to standard aggregation")
            client_weights_list = [update["weights"] for update in client_updates]
            aggregation_weights = self.compute_client_weights(client_updates)
            updated_global_weights = self.weighted_average(client_weights_list, aggregation_weights)

        # Apply gradient clipping and noise
        updated_global_weights = self.clip_weights(updated_global_weights)
        updated_global_weights = self.add_noise(updated_global_weights)

        aggregation_time = time.time() - start_time

        # Compute meta-learning statistics
        meta_stats = self._compute_meta_learning_stats(
            client_updates, meta_learning_metrics, aggregation_time
        )

        result = {
            "aggregated_weights": updated_global_weights,
            "num_clients": len(client_updates),
            "aggregation_time": aggregation_time,
            "aggregation_method": f"federated_{self.strategy_type}",
            "meta_learning_stats": meta_stats,
            "metadata": {
                "meta_lr": self.meta_lr,
                "inner_lr": self.inner_lr,
                "inner_steps": self.inner_steps,
                "strategy": self.strategy_type,
            },
        }

        self.record_aggregation(result)
        self.meta_learning_history.append(meta_stats)

        self.logger.info(f"FedMAML aggregation completed in {aggregation_time:.3f}s")
        return result

    def _compute_meta_learning_stats(
        self,
        client_updates: List[Dict[str, Any]],
        meta_metrics: List[Dict[str, Any]],
        aggregation_time: float,
    ) -> Dict[str, Any]:
        """Compute meta-learning specific statistics."""
        stats = {
            "aggregation_time": aggregation_time,
            "num_clients": len(client_updates),
            "strategy": self.strategy_type,
        }

        # Aggregate client meta-learning metrics
        if meta_metrics:
            # Extract common metrics
            adaptation_losses = [
                m.get("adaptation_loss", 0) for m in meta_metrics if "adaptation_loss" in m
            ]
            inner_loop_steps = [
                m.get("inner_steps_taken", 0) for m in meta_metrics if "inner_steps_taken" in m
            ]
            task_similarities = [
                m.get("task_similarity", 0) for m in meta_metrics if "task_similarity" in m
            ]

            if adaptation_losses:
                stats["adaptation_loss"] = {
                    "mean": np.mean(adaptation_losses),
                    "std": np.std(adaptation_losses),
                    "min": min(adaptation_losses),
                    "max": max(adaptation_losses),
                }

            if inner_loop_steps:
                stats["inner_steps"] = {
                    "mean": np.mean(inner_loop_steps),
                    "std": np.std(inner_loop_steps),
                    "total": sum(inner_loop_steps),
                }

            if task_similarities:
                stats["task_similarity"] = {
                    "mean": np.mean(task_similarities),
                    "std": np.std(task_similarities),
                }

        return stats

    def get_meta_learning_summary(self) -> Dict[str, Any]:
        """Get summary of meta-learning progress."""
        base_stats = self.get_aggregation_stats()

        meta_summary = {
            "strategy": self.strategy_type,
            "meta_lr": self.meta_lr,
            "inner_lr": self.inner_lr,
            "inner_steps": self.inner_steps,
            "total_meta_rounds": len(self.meta_learning_history),
        }

        # Aggregate historical metrics
        if self.meta_learning_history:
            recent_history = self.meta_learning_history[-10:]  # Last 10 rounds

            # Average adaptation loss over recent rounds
            adaptation_losses = [
                h.get("adaptation_loss", {}).get("mean", 0)
                for h in recent_history
                if "adaptation_loss" in h
            ]

            if adaptation_losses:
                meta_summary["recent_adaptation_loss"] = {
                    "mean": np.mean(adaptation_losses),
                    "trend": (
                        "decreasing"
                        if len(adaptation_losses) > 1
                        and adaptation_losses[-1] < adaptation_losses[0]
                        else "stable"
                    ),
                }

        base_stats.update(meta_summary)
        return base_stats


class FedMAML:
    """Federated Model-Agnostic Meta-Learning (FedMAML) implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.aggregator = FedMAMLAggregator("fedmaml_main", config.get("aggregator", {}))

        # FedMAML specific parameters
        self.num_tasks_per_client = config.get("num_tasks_per_client", 5)
        self.support_shots = config.get("support_shots", 5)
        self.query_shots = config.get("query_shots", 15)

        # State
        self.global_model_weights = None
        self.round_number = 0
        self.training_history = []

        self.logger = logging.getLogger("FedMAML")
        self.logger.info("FedMAML initialized")

    def training_round(self, client_task_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute one round of FedMAML training."""
        round_start_time = time.time()

        # Add global weights to each update
        for update in client_task_updates:
            update["global_weights"] = self.global_model_weights

        # Aggregate using meta-learning
        aggregation_result = self.aggregator.aggregate(client_task_updates)

        # Update global model
        self.global_model_weights = aggregation_result["aggregated_weights"]

        round_time = time.time() - round_start_time
        self.round_number += 1

        # Compile round results
        round_result = {
            "round": self.round_number,
            "round_time": round_time,
            "aggregation_result": aggregation_result,
            "num_clients": len(client_task_updates),
            "timestamp": time.time(),
        }

        self.training_history.append(round_result)

        self.logger.info(f"FedMAML round {self.round_number} completed in {round_time:.3f}s")
        return round_result

    def get_global_model(self) -> Optional[List[np.ndarray]]:
        """Get current global model weights."""
        return self.global_model_weights

    def set_global_model(self, weights: List[np.ndarray]):
        """Set global model weights."""
        self.global_model_weights = [w.copy() for w in weights]

    def get_training_summary(self) -> Dict[str, Any]:
        """Get comprehensive training summary."""
        return {
            "algorithm": "FedMAML",
            "total_rounds": self.round_number,
            "num_tasks_per_client": self.num_tasks_per_client,
            "support_shots": self.support_shots,
            "query_shots": self.query_shots,
            "aggregator_summary": self.aggregator.get_meta_learning_summary(),
            "training_history_length": len(self.training_history),
        }


class FedReptile:
    """Federated Reptile meta-learning implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Use Reptile strategy
        reptile_config = config.copy()
        reptile_config["strategy"] = "reptile"

        self.aggregator = FedMAMLAggregator(
            "fedreptile_main", reptile_config.get("aggregator", reptile_config)
        )

        # Reptile specific parameters
        self.inner_batch_size = config.get("inner_batch_size", 10)
        self.inner_iterations = config.get("inner_iterations", 20)

        # State
        self.global_model_weights = None
        self.round_number = 0

        self.logger = logging.getLogger("FedReptile")
        self.logger.info("FedReptile initialized")

    def training_round(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute one round of FedReptile training."""
        round_start_time = time.time()

        # Add global weights to each update
        for update in client_updates:
            update["global_weights"] = self.global_model_weights

        # Aggregate using Reptile strategy
        aggregation_result = self.aggregator.aggregate(client_updates)

        # Update global model
        self.global_model_weights = aggregation_result["aggregated_weights"]

        round_time = time.time() - round_start_time
        self.round_number += 1

        round_result = {
            "round": self.round_number,
            "round_time": round_time,
            "aggregation_result": aggregation_result,
            "num_clients": len(client_updates),
        }

        self.logger.info(f"FedReptile round {self.round_number} completed in {round_time:.3f}s")
        return round_result

    def get_global_model(self) -> Optional[List[np.ndarray]]:
        """Get current global model weights."""
        return self.global_model_weights

    def set_global_model(self, weights: List[np.ndarray]):
        """Set global model weights."""
        self.global_model_weights = [w.copy() for w in weights]


class FederatedMetaLearning:
    """
    Main coordinator for federated meta-learning.

    Supports multiple meta-learning algorithms and task distributions.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.algorithm = config.get("algorithm", "fedmaml")

        # Initialize the appropriate meta-learning algorithm
        if self.algorithm.lower() == "fedmaml":
            self.meta_learner = FedMAML(config)
        elif self.algorithm.lower() == "fedreptile":
            self.meta_learner = FedReptile(config)
        else:
            raise ValueError(f"Unknown meta-learning algorithm: {self.algorithm}")

        # Task management
        self.task_distributions = {}
        self.client_task_assignments = {}

        self.logger = logging.getLogger("FederatedMetaLearning")
        self.logger.info(f"Federated meta-learning coordinator initialized with {self.algorithm}")

    def register_task_distribution(self, task_id: str, task_config: Dict[str, Any]):
        """Register a task distribution."""
        self.task_distributions[task_id] = task_config
        self.logger.info(f"Registered task distribution: {task_id}")

    def assign_tasks_to_client(self, client_id: str, task_ids: List[str]):
        """Assign tasks to a client."""
        self.client_task_assignments[client_id] = task_ids
        self.logger.info(f"Assigned {len(task_ids)} tasks to client {client_id}")

    def meta_training_round(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute one round of federated meta-learning."""
        return self.meta_learner.training_round(client_updates)

    def get_meta_model_for_task(self, task_id: str) -> Optional[List[np.ndarray]]:
        """Get meta-model that can be adapted for a specific task."""
        return self.meta_learner.get_global_model()

    def get_comprehensive_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of federated meta-learning."""
        return {
            "algorithm": self.algorithm,
            "num_task_distributions": len(self.task_distributions),
            "num_clients_with_tasks": len(self.client_task_assignments),
            "task_distributions": list(self.task_distributions.keys()),
            "meta_learner_summary": (
                self.meta_learner.get_training_summary()
                if hasattr(self.meta_learner, "get_training_summary")
                else {}
            ),
        }
