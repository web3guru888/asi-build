"""
Federated Transfer Learning

Implementation of transfer learning in federated settings, including
domain adaptation, knowledge distillation, and cross-domain federation.
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


class TransferStrategy(ABC):
    """Abstract base class for transfer learning strategies."""

    @abstractmethod
    def adapt_model(
        self,
        source_weights: List[np.ndarray],
        target_data: tf.data.Dataset,
        adaptation_config: Dict[str, Any],
    ) -> List[np.ndarray]:
        """Adapt source model to target domain."""
        pass


class LayerFreezingStrategy(TransferStrategy):
    """Transfer learning through layer freezing."""

    def __init__(self, frozen_layers: List[int], fine_tune_epochs: int = 10):
        self.frozen_layers = frozen_layers
        self.fine_tune_epochs = fine_tune_epochs
        self.logger = logging.getLogger("LayerFreezing")

    def adapt_model(
        self,
        source_weights: List[np.ndarray],
        target_data: tf.data.Dataset,
        adaptation_config: Dict[str, Any],
    ) -> List[np.ndarray]:
        """Adapt model by freezing certain layers and fine-tuning others."""
        # This is a simplified version - in practice, you'd need the actual model
        adapted_weights = [w.copy() for w in source_weights]

        # In a real implementation, you would:
        # 1. Load the model with source weights
        # 2. Freeze specified layers
        # 3. Fine-tune unfrozen layers on target data
        # 4. Return the adapted weights

        self.logger.info(f"Layer freezing adaptation with {len(self.frozen_layers)} frozen layers")
        return adapted_weights


class DomainAdversarialStrategy(TransferStrategy):
    """Domain adversarial neural network strategy."""

    def __init__(self, domain_adaptation_weight: float = 1.0):
        self.domain_adaptation_weight = domain_adaptation_weight
        self.logger = logging.getLogger("DomainAdversarial")

    def adapt_model(
        self,
        source_weights: List[np.ndarray],
        target_data: tf.data.Dataset,
        adaptation_config: Dict[str, Any],
    ) -> List[np.ndarray]:
        """Adapt using domain adversarial training."""
        # Simplified implementation
        adapted_weights = [w.copy() for w in source_weights]

        # Domain adversarial adaptation would involve:
        # 1. Adding domain classifier
        # 2. Adversarial training between feature extractor and domain classifier
        # 3. Minimizing task loss while maximizing domain confusion

        self.logger.info("Domain adversarial adaptation")
        return adapted_weights


class KnowledgeDistillationStrategy(TransferStrategy):
    """Knowledge distillation for transfer learning."""

    def __init__(self, temperature: float = 3.0, alpha: float = 0.7):
        self.temperature = temperature
        self.alpha = alpha
        self.logger = logging.getLogger("KnowledgeDistillation")

    def adapt_model(
        self,
        source_weights: List[np.ndarray],
        target_data: tf.data.Dataset,
        adaptation_config: Dict[str, Any],
    ) -> List[np.ndarray]:
        """Adapt using knowledge distillation."""
        adapted_weights = [w.copy() for w in source_weights]

        # Knowledge distillation would involve:
        # 1. Using source model as teacher
        # 2. Training student model on soft targets from teacher
        # 3. Combining with hard targets from actual labels

        self.logger.info(f"Knowledge distillation with temperature={self.temperature}")
        return adapted_weights


class FedTransferAggregator(BaseAggregator):
    """Aggregator for federated transfer learning."""

    def __init__(self, aggregator_id: str = "fed_transfer", config: Dict[str, Any] = None):
        super().__init__(aggregator_id, config)

        # Transfer learning parameters
        self.domain_similarity_threshold = self.config.get("domain_similarity_threshold", 0.5)
        self.adaptation_weight = self.config.get("adaptation_weight", 0.3)
        self.enable_domain_clustering = self.config.get("enable_domain_clustering", True)

        # Domain information
        self.client_domains = {}
        self.domain_clusters = {}
        self.domain_similarities = {}

        self.logger.info("FedTransfer aggregator initialized")

    def register_client_domain(self, client_id: str, domain_info: Dict[str, Any]):
        """Register domain information for a client."""
        self.client_domains[client_id] = domain_info
        self.logger.info(
            f"Registered domain for client {client_id}: {domain_info.get('domain_name', 'unknown')}"
        )

    def aggregate(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate client updates with transfer learning considerations."""
        start_time = time.time()

        # Validate updates
        self.validate_updates(client_updates)

        # Extract client information
        client_weights_list = [update["weights"] for update in client_updates]
        data_sizes = [update["data_size"] for update in client_updates]
        client_ids = [update["client_id"] for update in client_updates]

        # Compute domain similarities
        domain_similarities = self._compute_domain_similarities(client_ids)

        # Perform domain-aware aggregation
        if self.enable_domain_clustering:
            aggregated_weights, domain_info = self._domain_aware_aggregation(
                client_weights_list, data_sizes, client_ids, domain_similarities
            )
        else:
            # Standard weighted aggregation
            aggregation_weights = self.compute_client_weights(client_updates)
            aggregated_weights = self.weighted_average(client_weights_list, aggregation_weights)
            domain_info = {"method": "standard_aggregation"}

        # Apply gradient clipping and noise
        aggregated_weights = self.clip_weights(aggregated_weights)
        aggregated_weights = self.add_noise(aggregated_weights)

        aggregation_time = time.time() - start_time

        result = {
            "aggregated_weights": aggregated_weights,
            "num_clients": len(client_updates),
            "aggregation_time": aggregation_time,
            "aggregation_method": "fed_transfer",
            "domain_similarities": domain_similarities,
            "domain_info": domain_info,
            "metadata": {
                "domain_clustering_enabled": self.enable_domain_clustering,
                "adaptation_weight": self.adaptation_weight,
                "total_samples": sum(data_sizes),
            },
        }

        self.record_aggregation(result)
        self.logger.info(f"FedTransfer aggregation completed in {aggregation_time:.3f}s")

        return result

    def _compute_domain_similarities(self, client_ids: List[str]) -> Dict[str, float]:
        """Compute similarities between client domains."""
        similarities = {}

        for i, client_id in enumerate(client_ids):
            if client_id not in self.client_domains:
                continue

            client_domain = self.client_domains[client_id]
            client_similarities = {}

            for j, other_client_id in enumerate(client_ids):
                if i != j and other_client_id in self.client_domains:
                    other_domain = self.client_domains[other_client_id]
                    similarity = self._compute_single_domain_similarity(client_domain, other_domain)
                    client_similarities[other_client_id] = similarity

            similarities[client_id] = client_similarities

        return similarities

    def _compute_single_domain_similarity(
        self, domain1: Dict[str, Any], domain2: Dict[str, Any]
    ) -> float:
        """Compute similarity between two domains."""
        # Simple domain similarity based on domain names
        if domain1.get("domain_name") == domain2.get("domain_name"):
            return 1.0

        # Compare domain features if available
        features1 = domain1.get("features", {})
        features2 = domain2.get("features", {})

        if features1 and features2:
            # Compute feature similarity (simplified)
            common_features = set(features1.keys()) & set(features2.keys())
            if common_features:
                similarities = []
                for feature in common_features:
                    val1 = features1[feature]
                    val2 = features2[feature]

                    if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                        # Numerical similarity
                        max_val = max(abs(val1), abs(val2))
                        if max_val > 0:
                            sim = 1.0 - abs(val1 - val2) / max_val
                        else:
                            sim = 1.0
                        similarities.append(sim)
                    elif val1 == val2:
                        similarities.append(1.0)
                    else:
                        similarities.append(0.0)

                return np.mean(similarities) if similarities else 0.0

        # Default similarity for unknown domains
        return 0.1

    def _domain_aware_aggregation(
        self,
        client_weights_list: List[List[np.ndarray]],
        data_sizes: List[int],
        client_ids: List[str],
        domain_similarities: Dict[str, Dict[str, float]],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """Perform domain-aware aggregation."""
        # Cluster clients by domain similarity
        domain_clusters = self._cluster_clients_by_domain(client_ids, domain_similarities)

        # Aggregate within each cluster
        cluster_aggregates = {}
        cluster_info = {}

        for cluster_id, cluster_clients in domain_clusters.items():
            cluster_indices = [client_ids.index(client_id) for client_id in cluster_clients]
            cluster_weights = [client_weights_list[i] for i in cluster_indices]
            cluster_data_sizes = [data_sizes[i] for i in cluster_indices]

            # Aggregate within cluster
            if sum(cluster_data_sizes) > 0:
                cluster_aggregation_weights = [
                    size / sum(cluster_data_sizes) for size in cluster_data_sizes
                ]
            else:
                cluster_aggregation_weights = [1.0 / len(cluster_weights)] * len(cluster_weights)

            cluster_aggregate = self.weighted_average(cluster_weights, cluster_aggregation_weights)
            cluster_aggregates[cluster_id] = cluster_aggregate

            cluster_info[cluster_id] = {
                "clients": cluster_clients,
                "total_samples": sum(cluster_data_sizes),
                "num_clients": len(cluster_clients),
            }

        # Aggregate across clusters
        if len(cluster_aggregates) == 1:
            # Single cluster - return cluster aggregate
            final_aggregate = list(cluster_aggregates.values())[0]
        else:
            # Multiple clusters - weighted aggregation
            cluster_weights = []
            cluster_aggregates_list = []

            for cluster_id, cluster_aggregate in cluster_aggregates.items():
                cluster_weight = cluster_info[cluster_id]["total_samples"]
                cluster_weights.append(cluster_weight)
                cluster_aggregates_list.append(cluster_aggregate)

            # Normalize cluster weights
            total_weight = sum(cluster_weights)
            if total_weight > 0:
                cluster_weights = [w / total_weight for w in cluster_weights]
            else:
                cluster_weights = [1.0 / len(cluster_weights)] * len(cluster_weights)

            final_aggregate = self.weighted_average(cluster_aggregates_list, cluster_weights)

        domain_info = {
            "method": "domain_aware_aggregation",
            "num_clusters": len(domain_clusters),
            "clusters": cluster_info,
            "cluster_weights": cluster_weights if len(cluster_aggregates) > 1 else [1.0],
        }

        return final_aggregate, domain_info

    def _cluster_clients_by_domain(
        self, client_ids: List[str], domain_similarities: Dict[str, Dict[str, float]]
    ) -> Dict[str, List[str]]:
        """Cluster clients based on domain similarity."""
        clusters = {}
        assigned_clients = set()
        cluster_id = 0

        for client_id in client_ids:
            if client_id in assigned_clients:
                continue

            # Start new cluster
            current_cluster = [client_id]
            assigned_clients.add(client_id)

            # Find similar clients
            if client_id in domain_similarities:
                for other_client_id, similarity in domain_similarities[client_id].items():
                    if (
                        other_client_id not in assigned_clients
                        and similarity >= self.domain_similarity_threshold
                    ):
                        current_cluster.append(other_client_id)
                        assigned_clients.add(other_client_id)

            clusters[f"cluster_{cluster_id}"] = current_cluster
            cluster_id += 1

        return clusters


class FederatedTransferLearning:
    """
    Main coordinator for federated transfer learning.

    Manages source-to-target domain adaptation in federated settings.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.transfer_strategy_name = config.get("transfer_strategy", "layer_freezing")
        self.source_domain = config.get("source_domain", "general")
        self.target_domains = config.get("target_domains", [])

        # Initialize transfer strategy
        self.transfer_strategy = self._create_transfer_strategy()

        # Initialize aggregator
        self.aggregator = FedTransferAggregator("transfer_aggregator", config.get("aggregator", {}))

        # Transfer learning state
        self.source_model_weights = None
        self.domain_adapted_models = {}
        self.transfer_history = []

        self.logger = logging.getLogger("FederatedTransferLearning")
        self.logger.info(
            f"Federated transfer learning initialized with strategy: {self.transfer_strategy_name}"
        )

    def _create_transfer_strategy(self) -> TransferStrategy:
        """Create the transfer learning strategy."""
        if self.transfer_strategy_name == "layer_freezing":
            frozen_layers = self.config.get("frozen_layers", [0, 1])
            fine_tune_epochs = self.config.get("fine_tune_epochs", 10)
            return LayerFreezingStrategy(frozen_layers, fine_tune_epochs)
        elif self.transfer_strategy_name == "domain_adversarial":
            adaptation_weight = self.config.get("domain_adaptation_weight", 1.0)
            return DomainAdversarialStrategy(adaptation_weight)
        elif self.transfer_strategy_name == "knowledge_distillation":
            temperature = self.config.get("temperature", 3.0)
            alpha = self.config.get("alpha", 0.7)
            return KnowledgeDistillationStrategy(temperature, alpha)
        else:
            raise ValueError(f"Unknown transfer strategy: {self.transfer_strategy_name}")

    def set_source_model(self, source_weights: List[np.ndarray]):
        """Set the source domain model weights."""
        self.source_model_weights = [w.copy() for w in source_weights]
        self.logger.info("Source model weights set")

    def register_client_domain(self, client_id: str, domain_info: Dict[str, Any]):
        """Register domain information for a client."""
        self.aggregator.register_client_domain(client_id, domain_info)

    def federated_transfer_round(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute one round of federated transfer learning."""
        round_start_time = time.time()

        # Aggregate client updates
        aggregation_result = self.aggregator.aggregate(client_updates)

        # Perform domain adaptation if source model is available
        adaptation_results = {}
        if self.source_model_weights:
            for update in client_updates:
                client_id = update["client_id"]
                client_data = update.get("client_data")

                if client_data:
                    adapted_weights = self.transfer_strategy.adapt_model(
                        self.source_model_weights,
                        client_data,
                        {"adaptation_config": self.config.get("adaptation", {})},
                    )

                    self.domain_adapted_models[client_id] = adapted_weights
                    adaptation_results[client_id] = {
                        "adapted": True,
                        "strategy": self.transfer_strategy_name,
                    }

        round_time = time.time() - round_start_time

        # Record transfer history
        transfer_record = {
            "timestamp": time.time(),
            "round_time": round_time,
            "aggregation_result": aggregation_result,
            "adaptation_results": adaptation_results,
            "num_clients": len(client_updates),
            "source_model_available": self.source_model_weights is not None,
        }

        self.transfer_history.append(transfer_record)

        self.logger.info(f"Federated transfer round completed in {round_time:.3f}s")

        return transfer_record

    def get_adapted_model_for_client(self, client_id: str) -> Optional[List[np.ndarray]]:
        """Get domain-adapted model for a specific client."""
        return self.domain_adapted_models.get(client_id)

    def get_transfer_summary(self) -> Dict[str, Any]:
        """Get summary of transfer learning progress."""
        return {
            "transfer_strategy": self.transfer_strategy_name,
            "source_domain": self.source_domain,
            "target_domains": self.target_domains,
            "total_rounds": len(self.transfer_history),
            "num_adapted_clients": len(self.domain_adapted_models),
            "source_model_available": self.source_model_weights is not None,
            "aggregator_stats": self.aggregator.get_aggregation_stats(),
        }


class FedTransferManager:
    """High-level manager for federated transfer learning scenarios."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.transfer_scenarios = {}
        self.logger = logging.getLogger("FedTransferManager")

    def create_transfer_scenario(
        self, scenario_id: str, scenario_config: Dict[str, Any]
    ) -> FederatedTransferLearning:
        """Create a new transfer learning scenario."""
        scenario = FederatedTransferLearning(scenario_config)
        self.transfer_scenarios[scenario_id] = scenario

        self.logger.info(f"Created transfer scenario: {scenario_id}")
        return scenario

    def get_scenario(self, scenario_id: str) -> Optional[FederatedTransferLearning]:
        """Get an existing transfer scenario."""
        return self.transfer_scenarios.get(scenario_id)

    def list_scenarios(self) -> List[str]:
        """List all available transfer scenarios."""
        return list(self.transfer_scenarios.keys())

    def get_global_transfer_summary(self) -> Dict[str, Any]:
        """Get summary across all transfer scenarios."""
        summaries = {}
        for scenario_id, scenario in self.transfer_scenarios.items():
            summaries[scenario_id] = scenario.get_transfer_summary()

        return {
            "num_scenarios": len(self.transfer_scenarios),
            "scenarios": summaries,
            "total_adapted_clients": sum(
                summary["num_adapted_clients"] for summary in summaries.values()
            ),
        }
