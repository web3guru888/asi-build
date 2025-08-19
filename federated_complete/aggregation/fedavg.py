"""
FedAvg (Federated Averaging) Implementation

The classic federated learning algorithm that aggregates client model updates
by computing weighted averages based on the number of training samples.
"""

import time
from typing import Dict, Any, List, Optional
import numpy as np

from .base_aggregator import BaseAggregator
from ..core.exceptions import AggregationError


class FedAvgAggregator(BaseAggregator):
    """
    Federated Averaging (FedAvg) aggregator.
    
    Implements the classic FedAvg algorithm that computes weighted averages
    of client model updates, where weights are proportional to the number
    of training samples at each client.
    """
    
    def __init__(self, aggregator_id: str = "fedavg", config: Dict[str, Any] = None):
        super().__init__(aggregator_id, config)
        
        # FedAvg specific parameters
        self.momentum = self.config.get("momentum", 0.0)
        self.server_learning_rate = self.config.get("server_learning_rate", 1.0)
        self.adaptive_weighting = self.config.get("adaptive_weighting", False)
        self.min_weight_threshold = self.config.get("min_weight_threshold", 0.0)
        
        # Server-side optimization state
        self.server_momentum_buffer = None
        self.previous_global_weights = None
        
        self.logger.info(f"FedAvg aggregator initialized with momentum={self.momentum}")
    
    def aggregate(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate client updates using federated averaging.
        
        Args:
            client_updates: List of client updates containing weights and metadata
            
        Returns:
            Dictionary containing aggregated weights and metadata
        """
        start_time = time.time()
        
        # Validate client updates
        self.validate_updates(client_updates)
        
        # Extract client information
        client_weights_list = [update["weights"] for update in client_updates]
        data_sizes = [update["data_size"] for update in client_updates]
        client_ids = [update["client_id"] for update in client_updates]
        
        self.logger.info(f"Aggregating {len(client_updates)} client updates")
        
        try:
            # Compute client aggregation weights
            aggregation_weights = self._compute_aggregation_weights(
                client_updates, data_sizes
            )
            
            # Perform weighted averaging
            aggregated_weights = self._weighted_averaging(
                client_weights_list, aggregation_weights
            )
            
            # Apply server-side optimization if configured
            if self.momentum > 0 or self.server_learning_rate != 1.0:
                aggregated_weights = self._apply_server_optimization(aggregated_weights)
            
            # Apply gradient clipping and noise if configured
            aggregated_weights = self.clip_weights(aggregated_weights)
            aggregated_weights = self.add_noise(aggregated_weights)
            
            aggregation_time = time.time() - start_time
            
            # Compute aggregation statistics
            stats = self._compute_aggregation_statistics(
                client_updates, aggregation_weights, aggregation_time
            )
            
            # Create result
            result = {
                "aggregated_weights": aggregated_weights,
                "num_clients": len(client_updates),
                "aggregation_time": aggregation_time,
                "aggregation_method": "fedavg",
                "client_weights": aggregation_weights,
                "metadata": stats
            }
            
            # Record aggregation
            self.record_aggregation(result)
            
            # Store current weights for next iteration
            self.previous_global_weights = [w.copy() for w in aggregated_weights]
            
            self.logger.info(f"FedAvg aggregation completed in {aggregation_time:.3f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"FedAvg aggregation failed: {str(e)}")
            raise AggregationError(
                f"FedAvg aggregation failed: {str(e)}",
                aggregator_type=self.aggregator_id,
                client_count=len(client_updates)
            )
    
    def _compute_aggregation_weights(self, client_updates: List[Dict[str, Any]],
                                   data_sizes: List[int]) -> List[float]:
        """Compute weights for client aggregation."""
        if self.adaptive_weighting:
            return self._compute_adaptive_weights(client_updates)
        else:
            return self.compute_client_weights(client_updates)
    
    def _compute_adaptive_weights(self, client_updates: List[Dict[str, Any]]) -> List[float]:
        """Compute adaptive weights based on client performance."""
        data_sizes = [update["data_size"] for update in client_updates]
        
        # Base weights from data sizes
        total_samples = sum(data_sizes)
        if total_samples == 0:
            base_weights = [1.0 / len(client_updates)] * len(client_updates)
        else:
            base_weights = [size / total_samples for size in data_sizes]
        
        # Adjust weights based on client metrics if available
        adaptive_weights = []
        for i, update in enumerate(client_updates):
            weight = base_weights[i]
            
            # Consider client loss/accuracy for weighting
            metrics = update.get("metrics", {})
            if "loss" in metrics:
                # Lower loss -> higher weight (inverse relationship)
                loss = metrics["loss"]
                if loss > 0:
                    loss_factor = 1.0 / (1.0 + loss)
                    weight *= loss_factor
            
            if "accuracy" in metrics:
                # Higher accuracy -> higher weight
                accuracy = metrics["accuracy"]
                weight *= (1.0 + accuracy)
            
            # Apply minimum weight threshold
            weight = max(weight, self.min_weight_threshold)
            adaptive_weights.append(weight)
        
        # Normalize weights
        total_weight = sum(adaptive_weights)
        if total_weight > 0:
            adaptive_weights = [w / total_weight for w in adaptive_weights]
        else:
            adaptive_weights = [1.0 / len(client_updates)] * len(client_updates)
        
        return adaptive_weights
    
    def _weighted_averaging(self, client_weights_list: List[List[np.ndarray]],
                          aggregation_weights: List[float]) -> List[np.ndarray]:
        """Perform weighted averaging of client weights."""
        if not client_weights_list:
            raise AggregationError("No client weights to aggregate")
        
        # Initialize aggregated weights
        aggregated_weights = []
        num_layers = len(client_weights_list[0])
        
        for layer_idx in range(num_layers):
            # Get weights for this layer from all clients
            layer_weights = [weights[layer_idx] for weights in client_weights_list]
            
            # Compute weighted average
            weighted_sum = np.zeros_like(layer_weights[0])
            for weight, agg_weight in zip(layer_weights, aggregation_weights):
                weighted_sum += weight * agg_weight
            
            aggregated_weights.append(weighted_sum)
        
        return aggregated_weights
    
    def _apply_server_optimization(self, aggregated_weights: List[np.ndarray]) -> List[np.ndarray]:
        """Apply server-side optimization (momentum, learning rate)."""
        if self.previous_global_weights is None:
            # First iteration - no momentum to apply
            optimized_weights = []
            for weight in aggregated_weights:
                optimized_weights.append(weight * self.server_learning_rate)
            return optimized_weights
        
        optimized_weights = []
        
        # Initialize momentum buffer if needed
        if self.server_momentum_buffer is None:
            self.server_momentum_buffer = [
                np.zeros_like(weight) for weight in aggregated_weights
            ]
        
        for i, (new_weight, prev_weight) in enumerate(
            zip(aggregated_weights, self.previous_global_weights)
        ):
            # Compute weight update
            weight_update = new_weight - prev_weight
            
            # Apply momentum
            if self.momentum > 0:
                self.server_momentum_buffer[i] = (
                    self.momentum * self.server_momentum_buffer[i] + 
                    (1 - self.momentum) * weight_update
                )
                weight_update = self.server_momentum_buffer[i]
            
            # Apply server learning rate and compute new weights
            optimized_weight = prev_weight + self.server_learning_rate * weight_update
            optimized_weights.append(optimized_weight)
        
        return optimized_weights
    
    def _compute_aggregation_statistics(self, client_updates: List[Dict[str, Any]],
                                      aggregation_weights: List[float],
                                      aggregation_time: float) -> Dict[str, Any]:
        """Compute detailed aggregation statistics."""
        data_sizes = [update["data_size"] for update in client_updates]
        
        stats = {
            "total_samples": sum(data_sizes),
            "avg_samples_per_client": np.mean(data_sizes),
            "std_samples_per_client": np.std(data_sizes),
            "min_samples": min(data_sizes),
            "max_samples": max(data_sizes),
            "weight_distribution": {
                "mean": np.mean(aggregation_weights),
                "std": np.std(aggregation_weights),
                "min": min(aggregation_weights),
                "max": max(aggregation_weights)
            },
            "aggregation_time": aggregation_time,
            "clients_participated": len(client_updates)
        }
        
        # Add client metrics statistics if available
        client_losses = []
        client_accuracies = []
        
        for update in client_updates:
            metrics = update.get("metrics", {})
            if "loss" in metrics:
                client_losses.append(metrics["loss"])
            if "accuracy" in metrics:
                client_accuracies.append(metrics["accuracy"])
        
        if client_losses:
            stats["client_losses"] = {
                "mean": np.mean(client_losses),
                "std": np.std(client_losses),
                "min": min(client_losses),
                "max": max(client_losses)
            }
        
        if client_accuracies:
            stats["client_accuracies"] = {
                "mean": np.mean(client_accuracies),
                "std": np.std(client_accuracies),
                "min": min(client_accuracies),
                "max": max(client_accuracies)
            }
        
        # Configuration information
        stats["config"] = {
            "momentum": self.momentum,
            "server_learning_rate": self.server_learning_rate,
            "adaptive_weighting": self.adaptive_weighting,
            "weight_by_samples": self.weight_by_samples
        }
        
        return stats
    
    def get_fedavg_specific_stats(self) -> Dict[str, Any]:
        """Get FedAvg-specific statistics."""
        base_stats = self.get_aggregation_stats()
        
        fedavg_stats = {
            "algorithm": "FedAvg",
            "momentum": self.momentum,
            "server_learning_rate": self.server_learning_rate,
            "adaptive_weighting": self.adaptive_weighting,
            "has_momentum_buffer": self.server_momentum_buffer is not None,
            "has_previous_weights": self.previous_global_weights is not None
        }
        
        # Merge with base stats
        base_stats.update(fedavg_stats)
        return base_stats
    
    def reset_server_state(self):
        """Reset server-side optimization state."""
        self.server_momentum_buffer = None
        self.previous_global_weights = None
        self.logger.info("Server optimization state reset")