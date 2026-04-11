"""
Base aggregator class for federated learning

Abstract base class for all aggregation algorithms.
"""

import abc
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import tensorflow as tf

from ..core.exceptions import AggregationError


class BaseAggregator(abc.ABC):
    """Abstract base class for federated learning aggregators."""

    def __init__(self, aggregator_id: str, config: Dict[str, Any] = None):
        self.aggregator_id = aggregator_id
        self.config = config or {}
        self.logger = logging.getLogger(f"Aggregator-{aggregator_id}")

        # Aggregation statistics
        self.aggregation_history = []
        self.total_aggregations = 0
        self.total_clients_aggregated = 0
        self.aggregation_times = []

        # Configuration parameters
        self.min_clients = self.config.get("min_clients", 2)
        self.weight_by_samples = self.config.get("weight_by_samples", True)
        self.clip_norm = self.config.get("clip_norm", None)
        self.noise_multiplier = self.config.get("noise_multiplier", 0.0)

    @abc.abstractmethod
    def aggregate(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate client updates into a global model update.

        Args:
            client_updates: List of client updates containing weights and metadata

        Returns:
            Dictionary containing aggregated weights and aggregation metadata
        """
        pass

    def validate_updates(self, client_updates: List[Dict[str, Any]]) -> bool:
        """Validate client updates before aggregation."""
        if len(client_updates) < self.min_clients:
            raise AggregationError(
                f"Insufficient client updates. Need at least {self.min_clients}, got {len(client_updates)}",
                aggregator_type=self.aggregator_id,
                client_count=len(client_updates),
            )

        # Check that all updates have required fields
        required_fields = ["client_id", "weights", "data_size"]
        for i, update in enumerate(client_updates):
            for field in required_fields:
                if field not in update:
                    raise AggregationError(
                        f"Client update {i} missing required field: {field}",
                        aggregator_type=self.aggregator_id,
                    )

        # Check weight compatibility
        if len(client_updates) > 0:
            reference_shapes = [w.shape for w in client_updates[0]["weights"]]
            for i, update in enumerate(client_updates[1:], 1):
                update_shapes = [w.shape for w in update["weights"]]
                if update_shapes != reference_shapes:
                    raise AggregationError(
                        f"Weight shape mismatch in client update {i}",
                        aggregator_type=self.aggregator_id,
                    )

        return True

    def clip_weights(self, weights: List[np.ndarray]) -> List[np.ndarray]:
        """Apply gradient clipping if configured."""
        if self.clip_norm is None:
            return weights

        clipped_weights = []
        for weight in weights:
            norm = np.linalg.norm(weight)
            if norm > self.clip_norm:
                clipped_weights.append(weight * (self.clip_norm / norm))
            else:
                clipped_weights.append(weight)

        return clipped_weights

    def add_noise(self, weights: List[np.ndarray]) -> List[np.ndarray]:
        """Add differential privacy noise if configured."""
        if self.noise_multiplier <= 0:
            return weights

        noisy_weights = []
        for weight in weights:
            noise = np.random.normal(0, self.noise_multiplier, weight.shape)
            noisy_weights.append(weight + noise)

        return noisy_weights

    def compute_client_weights(self, client_updates: List[Dict[str, Any]]) -> List[float]:
        """Compute aggregation weights for clients."""
        if not self.weight_by_samples:
            # Equal weighting
            return [1.0 / len(client_updates)] * len(client_updates)

        # Weight by number of samples
        total_samples = sum(update["data_size"] for update in client_updates)
        if total_samples == 0:
            return [1.0 / len(client_updates)] * len(client_updates)

        weights = [update["data_size"] / total_samples for update in client_updates]
        return weights

    def weighted_average(
        self, weights_list: List[List[np.ndarray]], client_weights: List[float]
    ) -> List[np.ndarray]:
        """Compute weighted average of model weights."""
        if not weights_list:
            raise AggregationError("No weights to aggregate", aggregator_type=self.aggregator_id)

        # Initialize aggregated weights
        aggregated_weights = []
        num_layers = len(weights_list[0])

        for layer_idx in range(num_layers):
            # Get weights for this layer from all clients
            layer_weights = [weights[layer_idx] for weights in weights_list]

            # Compute weighted average
            weighted_sum = np.zeros_like(layer_weights[0])
            for weight, client_weight in zip(layer_weights, client_weights):
                weighted_sum += weight * client_weight

            aggregated_weights.append(weighted_sum)

        return aggregated_weights

    def record_aggregation(self, aggregation_result: Dict[str, Any]) -> None:
        """Record aggregation statistics."""
        self.total_aggregations += 1
        self.total_clients_aggregated += aggregation_result.get("num_clients", 0)

        if "aggregation_time" in aggregation_result:
            self.aggregation_times.append(aggregation_result["aggregation_time"])

        self.aggregation_history.append(
            {
                "aggregation_id": self.total_aggregations,
                "timestamp": time.time(),
                "num_clients": aggregation_result.get("num_clients", 0),
                "aggregation_time": aggregation_result.get("aggregation_time", 0),
                "metadata": aggregation_result.get("metadata", {}),
            }
        )

        # Keep only recent history
        max_history = self.config.get("max_history", 1000)
        if len(self.aggregation_history) > max_history:
            self.aggregation_history = self.aggregation_history[-max_history:]

    def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get aggregation statistics."""
        return {
            "aggregator_id": self.aggregator_id,
            "total_aggregations": self.total_aggregations,
            "total_clients_aggregated": self.total_clients_aggregated,
            "avg_aggregation_time": (
                np.mean(self.aggregation_times) if self.aggregation_times else 0
            ),
            "avg_clients_per_round": (
                self.total_clients_aggregated / self.total_aggregations
                if self.total_aggregations > 0
                else 0
            ),
            "config": self.config,
        }

    def reset_stats(self) -> None:
        """Reset aggregation statistics."""
        self.aggregation_history.clear()
        self.total_aggregations = 0
        self.total_clients_aggregated = 0
        self.aggregation_times.clear()
        self.logger.info("Aggregation statistics reset")
