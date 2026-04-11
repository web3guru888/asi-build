"""
Distributed Dataset Sharding System
Implements intelligent data distribution for federated learning
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import random
import time
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.utils.data as data
from sklearn.cluster import KMeans


@dataclass
class DataShard:
    """Represents a data shard"""

    shard_id: str
    node_id: str
    data_indices: List[int]
    label_distribution: Dict[str, int]
    size: int
    checksum: str
    created_at: float


@dataclass
class DatasetMetadata:
    """Metadata about the global dataset"""

    dataset_id: str
    total_samples: int
    num_classes: int
    feature_dim: int
    class_distribution: Dict[str, int]
    data_type: str
    sharding_strategy: str


class ShardingStrategy(ABC):
    """Abstract base class for data sharding strategies"""

    @abstractmethod
    def shard_data(
        self, dataset: data.Dataset, num_shards: int, node_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[DataShard]:
        """Shard dataset according to strategy"""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name"""
        pass


class IIDSharding(ShardingStrategy):
    """Independent and Identically Distributed sharding"""

    def shard_data(
        self, dataset: data.Dataset, num_shards: int, node_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[DataShard]:
        """Create IID shards"""

        total_size = len(dataset)
        indices = list(range(total_size))
        random.shuffle(indices)

        # Calculate shard sizes based on node capabilities
        shard_sizes = self._calculate_shard_sizes(num_shards, total_size, node_capabilities)

        shards = []
        start_idx = 0

        for i, shard_size in enumerate(shard_sizes):
            end_idx = min(start_idx + shard_size, total_size)
            shard_indices = indices[start_idx:end_idx]

            # Calculate label distribution for this shard
            label_dist = self._calculate_label_distribution(dataset, shard_indices)

            shard = DataShard(
                shard_id=f"iid_shard_{i}",
                node_id=f"node_{i}",
                data_indices=shard_indices,
                label_distribution=label_dist,
                size=len(shard_indices),
                checksum=self._calculate_checksum(shard_indices),
                created_at=time.time(),
            )

            shards.append(shard)
            start_idx = end_idx

        return shards

    def _calculate_shard_sizes(
        self, num_shards: int, total_size: int, node_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[int]:
        """Calculate shard sizes based on node capabilities"""

        if not node_capabilities:
            # Equal distribution
            base_size = total_size // num_shards
            remainder = total_size % num_shards

            sizes = [base_size] * num_shards
            for i in range(remainder):
                sizes[i] += 1

            return sizes

        # Weight by compute capability
        node_ids = list(node_capabilities.keys())[:num_shards]
        capabilities = [
            node_capabilities[node_id].get("compute_power", 1.0) for node_id in node_ids
        ]

        total_capability = sum(capabilities)
        sizes = []

        allocated = 0
        for i, capability in enumerate(capabilities):
            if i == len(capabilities) - 1:
                # Last shard gets remaining samples
                size = total_size - allocated
            else:
                size = int((capability / total_capability) * total_size)

            sizes.append(max(1, size))  # Ensure at least 1 sample
            allocated += sizes[-1]

        return sizes

    def _calculate_label_distribution(
        self, dataset: data.Dataset, indices: List[int]
    ) -> Dict[str, int]:
        """Calculate label distribution for a shard"""
        label_counts = defaultdict(int)

        for idx in indices:
            try:
                if hasattr(dataset, "targets"):
                    label = dataset.targets[idx]
                elif hasattr(dataset, "labels"):
                    label = dataset.labels[idx]
                else:
                    # Try to get label from dataset item
                    _, label = dataset[idx]

                if isinstance(label, torch.Tensor):
                    label = label.item()

                label_counts[str(label)] += 1

            except Exception as e:
                logging.warning(f"Could not extract label for index {idx}: {e}")

        return dict(label_counts)

    def _calculate_checksum(self, indices: List[int]) -> str:
        """Calculate checksum for shard indices"""
        indices_str = ",".join(map(str, sorted(indices)))
        return hashlib.sha256(indices_str.encode()).hexdigest()[:16]

    def get_strategy_name(self) -> str:
        return "iid"


class NonIIDSharding(ShardingStrategy):
    """Non-IID sharding with configurable heterogeneity"""

    def __init__(self, alpha: float = 0.5, min_samples_per_class: int = 10):
        self.alpha = alpha  # Dirichlet concentration parameter
        self.min_samples_per_class = min_samples_per_class

    def shard_data(
        self, dataset: data.Dataset, num_shards: int, node_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[DataShard]:
        """Create non-IID shards using Dirichlet distribution"""

        # Extract labels
        labels = self._extract_labels(dataset)
        unique_labels = sorted(set(labels))
        num_classes = len(unique_labels)

        # Group indices by class
        class_indices = defaultdict(list)
        for idx, label in enumerate(labels):
            class_indices[label].append(idx)

        # Generate Dirichlet distribution for each class
        class_distributions = {}
        for label in unique_labels:
            # Dirichlet parameter: higher alpha = more uniform distribution
            dirichlet_params = np.full(num_shards, self.alpha)
            distribution = np.random.dirichlet(dirichlet_params)
            class_distributions[label] = distribution

        # Allocate samples to shards
        shard_indices = [[] for _ in range(num_shards)]

        for label, indices in class_indices.items():
            distribution = class_distributions[label]
            num_samples = len(indices)

            # Calculate samples per shard for this class
            samples_per_shard = (distribution * num_samples).astype(int)

            # Handle rounding errors
            remainder = num_samples - samples_per_shard.sum()
            if remainder > 0:
                # Distribute remainder to shards with highest fractional parts
                fractional_parts = (distribution * num_samples) - samples_per_shard
                top_shards = np.argsort(fractional_parts)[-remainder:]
                samples_per_shard[top_shards] += 1

            # Shuffle indices for this class
            shuffled_indices = indices.copy()
            random.shuffle(shuffled_indices)

            # Distribute to shards
            start_idx = 0
            for shard_idx, num_samples in enumerate(samples_per_shard):
                end_idx = start_idx + num_samples
                shard_indices[shard_idx].extend(shuffled_indices[start_idx:end_idx])
                start_idx = end_idx

        # Create DataShard objects
        shards = []
        for i, indices in enumerate(shard_indices):
            if not indices:  # Skip empty shards
                continue

            label_dist = self._calculate_label_distribution_from_labels(
                [labels[idx] for idx in indices]
            )

            shard = DataShard(
                shard_id=f"noniid_shard_{i}",
                node_id=f"node_{i}",
                data_indices=indices,
                label_distribution=label_dist,
                size=len(indices),
                checksum=self._calculate_checksum(indices),
                created_at=time.time(),
            )

            shards.append(shard)

        return shards

    def _extract_labels(self, dataset: data.Dataset) -> List[Any]:
        """Extract labels from dataset"""
        labels = []

        if hasattr(dataset, "targets"):
            labels = dataset.targets
            if isinstance(labels, torch.Tensor):
                labels = labels.tolist()
        elif hasattr(dataset, "labels"):
            labels = dataset.labels
            if isinstance(labels, torch.Tensor):
                labels = labels.tolist()
        else:
            # Extract labels by iterating through dataset
            for i in range(len(dataset)):
                try:
                    _, label = dataset[i]
                    if isinstance(label, torch.Tensor):
                        label = label.item()
                    labels.append(label)
                except Exception as e:
                    logging.warning(f"Could not extract label for index {i}: {e}")
                    labels.append(0)  # Default label

        return labels

    def _calculate_label_distribution_from_labels(self, labels: List[Any]) -> Dict[str, int]:
        """Calculate label distribution from list of labels"""
        label_counts = Counter(str(label) for label in labels)
        return dict(label_counts)

    def _calculate_checksum(self, indices: List[int]) -> str:
        """Calculate checksum for shard indices"""
        indices_str = ",".join(map(str, sorted(indices)))
        return hashlib.sha256(indices_str.encode()).hexdigest()[:16]

    def get_strategy_name(self) -> str:
        return f"noniid_alpha_{self.alpha}"


class GeographicSharding(ShardingStrategy):
    """Geographic/location-based sharding"""

    def __init__(self, location_clusters: int = 5):
        self.location_clusters = location_clusters

    def shard_data(
        self, dataset: data.Dataset, num_shards: int, node_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[DataShard]:
        """Shard data based on geographic regions"""

        # Extract location information from node capabilities
        node_locations = {}
        for node_id, capabilities in node_capabilities.items():
            location = capabilities.get("location", {"lat": 0, "lon": 0})
            node_locations[node_id] = [location["lat"], location["lon"]]

        if not node_locations:
            # Fallback to IID if no location info
            iid_strategy = IIDSharding()
            return iid_strategy.shard_data(dataset, num_shards, node_capabilities)

        # Cluster nodes by location
        locations = list(node_locations.values())
        node_ids = list(node_locations.keys())

        if len(locations) <= self.location_clusters:
            clusters = list(range(len(locations)))
        else:
            kmeans = KMeans(n_clusters=self.location_clusters, random_state=42)
            clusters = kmeans.fit_predict(locations)

        # Group nodes by cluster
        cluster_nodes = defaultdict(list)
        for i, cluster in enumerate(clusters):
            if i < len(node_ids):
                cluster_nodes[cluster].append(node_ids[i])

        # Distribute data equally among clusters, then among nodes in cluster
        total_size = len(dataset)
        indices = list(range(total_size))
        random.shuffle(indices)

        shards = []
        start_idx = 0

        for cluster_id, cluster_node_list in cluster_nodes.items():
            # Calculate cluster size
            cluster_size = total_size // len(cluster_nodes)
            if cluster_id < total_size % len(cluster_nodes):
                cluster_size += 1

            end_idx = min(start_idx + cluster_size, total_size)
            cluster_indices = indices[start_idx:end_idx]

            # Further divide among nodes in cluster
            nodes_in_cluster = len(cluster_node_list)
            node_size = len(cluster_indices) // nodes_in_cluster
            remainder = len(cluster_indices) % nodes_in_cluster

            cluster_start = 0
            for i, node_id in enumerate(cluster_node_list):
                node_shard_size = node_size + (1 if i < remainder else 0)
                node_indices = cluster_indices[cluster_start : cluster_start + node_shard_size]

                if node_indices:
                    label_dist = self._calculate_label_distribution(dataset, node_indices)

                    shard = DataShard(
                        shard_id=f"geo_cluster_{cluster_id}_node_{i}",
                        node_id=node_id,
                        data_indices=node_indices,
                        label_distribution=label_dist,
                        size=len(node_indices),
                        checksum=self._calculate_checksum(node_indices),
                        created_at=time.time(),
                    )

                    shards.append(shard)

                cluster_start += node_shard_size

            start_idx = end_idx

        return shards

    def _calculate_label_distribution(
        self, dataset: data.Dataset, indices: List[int]
    ) -> Dict[str, int]:
        """Calculate label distribution for a shard"""
        label_counts = defaultdict(int)

        for idx in indices:
            try:
                if hasattr(dataset, "targets"):
                    label = dataset.targets[idx]
                elif hasattr(dataset, "labels"):
                    label = dataset.labels[idx]
                else:
                    _, label = dataset[idx]

                if isinstance(label, torch.Tensor):
                    label = label.item()

                label_counts[str(label)] += 1

            except Exception:
                pass

        return dict(label_counts)

    def _calculate_checksum(self, indices: List[int]) -> str:
        """Calculate checksum for shard indices"""
        indices_str = ",".join(map(str, sorted(indices)))
        return hashlib.sha256(indices_str.encode()).hexdigest()[:16]

    def get_strategy_name(self) -> str:
        return f"geographic_{self.location_clusters}_clusters"


class AdaptiveSharding(ShardingStrategy):
    """Adaptive sharding based on node performance and data characteristics"""

    def __init__(self, performance_weight: float = 0.4, diversity_weight: float = 0.6):
        self.performance_weight = performance_weight
        self.diversity_weight = diversity_weight

    def shard_data(
        self, dataset: data.Dataset, num_shards: int, node_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[DataShard]:
        """Adaptive sharding based on multiple factors"""

        # Extract dataset characteristics
        labels = self._extract_labels(dataset)
        unique_labels = sorted(set(labels))

        # Calculate node scores based on capabilities
        node_scores = self._calculate_node_scores(node_capabilities)

        # Create balanced shards considering both performance and data diversity
        shards = []

        # Group indices by class for controlled distribution
        class_indices = defaultdict(list)
        for idx, label in enumerate(labels):
            class_indices[label].append(idx)

        # Sort nodes by score (best nodes first)
        sorted_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)

        # Initialize shard containers
        shard_data = {node_id: [] for node_id, _ in sorted_nodes[:num_shards]}
        shard_class_counts = {node_id: defaultdict(int) for node_id, _ in sorted_nodes[:num_shards]}

        # Distribute each class across shards
        for label, indices in class_indices.items():
            shuffled_indices = indices.copy()
            random.shuffle(shuffled_indices)

            # Calculate target samples per shard for this class
            samples_per_class = len(indices)
            base_samples = samples_per_class // num_shards
            extra_samples = samples_per_class % num_shards

            idx_pointer = 0
            for i, (node_id, _) in enumerate(sorted_nodes[:num_shards]):
                target_samples = base_samples + (1 if i < extra_samples else 0)

                # Adjust based on node capability
                node_capability = node_scores[node_id]
                capability_multiplier = min(2.0, max(0.5, node_capability))
                adjusted_samples = int(target_samples * capability_multiplier)
                adjusted_samples = min(adjusted_samples, len(indices) - idx_pointer)

                if adjusted_samples > 0:
                    shard_indices = shuffled_indices[idx_pointer : idx_pointer + adjusted_samples]
                    shard_data[node_id].extend(shard_indices)
                    shard_class_counts[node_id][label] += len(shard_indices)
                    idx_pointer += adjusted_samples

            # Distribute any remaining samples
            while idx_pointer < len(shuffled_indices):
                # Find shard with least samples of this class
                min_node = min(
                    shard_class_counts.keys(), key=lambda n: shard_class_counts[n][label]
                )

                shard_data[min_node].append(shuffled_indices[idx_pointer])
                shard_class_counts[min_node][label] += 1
                idx_pointer += 1

        # Create DataShard objects
        for i, (node_id, node_indices) in enumerate(shard_data.items()):
            if node_indices:
                label_dist = {
                    str(label): count for label, count in shard_class_counts[node_id].items()
                }

                shard = DataShard(
                    shard_id=f"adaptive_shard_{i}",
                    node_id=node_id,
                    data_indices=node_indices,
                    label_distribution=label_dist,
                    size=len(node_indices),
                    checksum=self._calculate_checksum(node_indices),
                    created_at=time.time(),
                )

                shards.append(shard)

        return shards

    def _extract_labels(self, dataset: data.Dataset) -> List[Any]:
        """Extract labels from dataset"""
        labels = []

        if hasattr(dataset, "targets"):
            labels = dataset.targets
            if isinstance(labels, torch.Tensor):
                labels = labels.tolist()
        elif hasattr(dataset, "labels"):
            labels = dataset.labels
            if isinstance(labels, torch.Tensor):
                labels = labels.tolist()
        else:
            for i in range(min(len(dataset), 1000)):  # Sample for efficiency
                try:
                    _, label = dataset[i]
                    if isinstance(label, torch.Tensor):
                        label = label.item()
                    labels.append(label)
                except Exception:
                    labels.append(0)

        return labels

    def _calculate_node_scores(
        self, node_capabilities: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate composite scores for nodes"""
        if not node_capabilities:
            return {}

        scores = {}

        # Normalize capabilities
        compute_powers = [caps.get("compute_power", 1.0) for caps in node_capabilities.values()]
        bandwidth_values = [caps.get("bandwidth", 100.0) for caps in node_capabilities.values()]
        storage_values = [caps.get("storage_gb", 10.0) for caps in node_capabilities.values()]

        max_compute = max(compute_powers) if compute_powers else 1.0
        max_bandwidth = max(bandwidth_values) if bandwidth_values else 1.0
        max_storage = max(storage_values) if storage_values else 1.0

        for node_id, capabilities in node_capabilities.items():
            compute_score = capabilities.get("compute_power", 1.0) / max_compute
            bandwidth_score = capabilities.get("bandwidth", 100.0) / max_bandwidth
            storage_score = capabilities.get("storage_gb", 10.0) / max_storage

            # Weighted combination
            composite_score = 0.5 * compute_score + 0.3 * bandwidth_score + 0.2 * storage_score
            scores[node_id] = composite_score

        return scores

    def _calculate_checksum(self, indices: List[int]) -> str:
        """Calculate checksum for shard indices"""
        indices_str = ",".join(map(str, sorted(indices)))
        return hashlib.sha256(indices_str.encode()).hexdigest()[:16]

    def get_strategy_name(self) -> str:
        return f"adaptive_perf_{self.performance_weight}_div_{self.diversity_weight}"


class DistributedDatasetManager:
    """Main manager for distributed dataset sharding and coordination"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Sharding strategies
        self.strategies = {
            "iid": IIDSharding(),
            "noniid": NonIIDSharding(
                alpha=config.get("noniid_alpha", 0.5),
                min_samples_per_class=config.get("min_samples_per_class", 10),
            ),
            "geographic": GeographicSharding(location_clusters=config.get("location_clusters", 5)),
            "adaptive": AdaptiveSharding(
                performance_weight=config.get("performance_weight", 0.4),
                diversity_weight=config.get("diversity_weight", 0.6),
            ),
        }

        # Dataset management
        self.datasets: Dict[str, Any] = {}
        self.dataset_metadata: Dict[str, DatasetMetadata] = {}
        self.shards: Dict[str, List[DataShard]] = {}

        # Node management
        self.node_capabilities: Dict[str, Dict[str, Any]] = {}
        self.node_shard_assignments: Dict[str, List[str]] = {}  # node_id -> [shard_ids]

        self.logger = logging.getLogger(__name__)

    async def register_dataset(
        self, dataset: data.Dataset, dataset_id: str, data_type: str = "vision"
    ) -> DatasetMetadata:
        """Register a new dataset for distributed training"""

        self.logger.info(f"Registering dataset {dataset_id}")

        # Extract dataset metadata
        total_samples = len(dataset)

        # Determine number of classes and feature dimensions
        sample_data, sample_label = dataset[0]

        if isinstance(sample_data, torch.Tensor):
            if len(sample_data.shape) > 1:
                feature_dim = np.prod(sample_data.shape)
            else:
                feature_dim = sample_data.shape[0]
        else:
            feature_dim = -1  # Unknown

        # Extract class distribution
        class_distribution = self._calculate_global_class_distribution(dataset)
        num_classes = len(class_distribution)

        metadata = DatasetMetadata(
            dataset_id=dataset_id,
            total_samples=total_samples,
            num_classes=num_classes,
            feature_dim=feature_dim,
            class_distribution=class_distribution,
            data_type=data_type,
            sharding_strategy="",  # Will be set during sharding
        )

        self.datasets[dataset_id] = dataset
        self.dataset_metadata[dataset_id] = metadata

        self.logger.info(
            f"Registered dataset {dataset_id}: {total_samples} samples, {num_classes} classes"
        )

        return metadata

    async def shard_dataset(
        self, dataset_id: str, strategy: str, target_nodes: List[str]
    ) -> List[DataShard]:
        """Shard dataset using specified strategy"""

        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset {dataset_id} not registered")

        if strategy not in self.strategies:
            raise ValueError(f"Unknown sharding strategy: {strategy}")

        dataset = self.datasets[dataset_id]
        sharding_strategy = self.strategies[strategy]

        # Get node capabilities for target nodes
        node_caps = {node_id: self.node_capabilities.get(node_id, {}) for node_id in target_nodes}

        self.logger.info(
            f"Sharding dataset {dataset_id} using {strategy} strategy for {len(target_nodes)} nodes"
        )

        # Perform sharding
        start_time = time.time()
        shards = sharding_strategy.shard_data(dataset, len(target_nodes), node_caps)
        sharding_time = time.time() - start_time

        # Update metadata
        self.dataset_metadata[dataset_id].sharding_strategy = sharding_strategy.get_strategy_name()

        # Store shards
        self.shards[dataset_id] = shards

        # Update node assignments
        self.node_shard_assignments.clear()
        for shard in shards:
            if shard.node_id not in self.node_shard_assignments:
                self.node_shard_assignments[shard.node_id] = []
            self.node_shard_assignments[shard.node_id].append(shard.shard_id)

        self.logger.info(
            f"Sharding completed in {sharding_time:.2f}s: created {len(shards)} shards"
        )

        return shards

    def register_node(self, node_id: str, capabilities: Dict[str, Any]):
        """Register node capabilities"""
        self.node_capabilities[node_id] = capabilities
        self.logger.info(f"Registered node {node_id} with capabilities: {capabilities}")

    def get_node_shards(self, node_id: str, dataset_id: str) -> List[DataShard]:
        """Get shards assigned to a specific node"""
        if dataset_id not in self.shards:
            return []

        node_shards = []
        for shard in self.shards[dataset_id]:
            if shard.node_id == node_id:
                node_shards.append(shard)

        return node_shards

    def get_dataset_stats(self, dataset_id: str) -> Dict[str, Any]:
        """Get statistics about dataset sharding"""
        if dataset_id not in self.shards:
            return {}

        shards = self.shards[dataset_id]
        metadata = self.dataset_metadata[dataset_id]

        # Calculate shard statistics
        shard_sizes = [shard.size for shard in shards]
        total_sharded = sum(shard_sizes)

        # Label distribution analysis
        global_dist = metadata.class_distribution
        shard_distributions = []

        for shard in shards:
            # Normalize shard distribution for comparison
            shard_total = sum(shard.label_distribution.values())
            if shard_total > 0:
                normalized_dist = {
                    label: count / shard_total for label, count in shard.label_distribution.items()
                }
                shard_distributions.append(normalized_dist)

        # Calculate heterogeneity metrics
        heterogeneity = self._calculate_heterogeneity(shard_distributions, global_dist)

        return {
            "dataset_id": dataset_id,
            "total_samples": metadata.total_samples,
            "total_sharded_samples": total_sharded,
            "num_shards": len(shards),
            "avg_shard_size": np.mean(shard_sizes),
            "std_shard_size": np.std(shard_sizes),
            "min_shard_size": min(shard_sizes) if shard_sizes else 0,
            "max_shard_size": max(shard_sizes) if shard_sizes else 0,
            "sharding_strategy": metadata.sharding_strategy,
            "heterogeneity_score": heterogeneity,
            "coverage_ratio": total_sharded / metadata.total_samples,
        }

    def _calculate_global_class_distribution(self, dataset: data.Dataset) -> Dict[str, int]:
        """Calculate global class distribution"""
        class_counts = defaultdict(int)

        # Sample dataset to avoid processing entire dataset
        sample_size = min(len(dataset), 10000)
        indices = np.random.choice(len(dataset), sample_size, replace=False)

        for idx in indices:
            try:
                if hasattr(dataset, "targets"):
                    label = dataset.targets[idx]
                elif hasattr(dataset, "labels"):
                    label = dataset.labels[idx]
                else:
                    _, label = dataset[idx]

                if isinstance(label, torch.Tensor):
                    label = label.item()

                class_counts[str(label)] += 1

            except Exception as e:
                self.logger.warning(f"Could not extract label for index {idx}: {e}")

        # Scale up to full dataset
        scale_factor = len(dataset) / sample_size
        scaled_counts = {label: int(count * scale_factor) for label, count in class_counts.items()}

        return scaled_counts

    def _calculate_heterogeneity(
        self, shard_distributions: List[Dict[str, float]], global_distribution: Dict[str, int]
    ) -> float:
        """Calculate heterogeneity score using KL divergence"""
        if not shard_distributions:
            return 0.0

        # Normalize global distribution
        total_global = sum(global_distribution.values())
        global_probs = {label: count / total_global for label, count in global_distribution.items()}

        # Calculate average KL divergence
        kl_divergences = []

        for shard_dist in shard_distributions:
            kl_div = 0.0

            for label in global_probs:
                p_global = global_probs[label]
                p_shard = shard_dist.get(label, 1e-10)  # Small epsilon for numerical stability

                if p_global > 0 and p_shard > 0:
                    kl_div += p_shard * np.log(p_shard / p_global)

            kl_divergences.append(kl_div)

        return np.mean(kl_divergences) if kl_divergences else 0.0

    async def rebalance_shards(
        self, dataset_id: str, performance_metrics: Dict[str, Dict[str, float]]
    ) -> List[DataShard]:
        """Rebalance shards based on node performance"""

        if dataset_id not in self.shards:
            raise ValueError(f"Dataset {dataset_id} not found")

        current_shards = self.shards[dataset_id]

        # Analyze performance metrics
        slow_nodes = []
        fast_nodes = []

        for node_id, metrics in performance_metrics.items():
            training_time = metrics.get("avg_training_time", 0)
            accuracy = metrics.get("accuracy", 0)

            # Simple heuristic: slow if training time > 2x average or accuracy < 0.5
            avg_time = np.mean(
                [m.get("avg_training_time", 0) for m in performance_metrics.values()]
            )

            if training_time > 2 * avg_time or accuracy < 0.5:
                slow_nodes.append(node_id)
            elif training_time < 0.8 * avg_time and accuracy > 0.8:
                fast_nodes.append(node_id)

        if not slow_nodes or not fast_nodes:
            self.logger.info("No rebalancing needed")
            return current_shards

        self.logger.info(
            f"Rebalancing: moving load from {len(slow_nodes)} slow nodes to {len(fast_nodes)} fast nodes"
        )

        # Collect indices from slow nodes
        indices_to_redistribute = []
        for shard in current_shards:
            if shard.node_id in slow_nodes:
                indices_to_redistribute.extend(shard.data_indices)

        # Remove shards from slow nodes
        remaining_shards = [shard for shard in current_shards if shard.node_id not in slow_nodes]

        # Redistribute to fast nodes
        if indices_to_redistribute:
            random.shuffle(indices_to_redistribute)

            samples_per_fast_node = len(indices_to_redistribute) // len(fast_nodes)
            remainder = len(indices_to_redistribute) % len(fast_nodes)

            start_idx = 0
            for i, node_id in enumerate(fast_nodes):
                end_idx = start_idx + samples_per_fast_node + (1 if i < remainder else 0)
                node_indices = indices_to_redistribute[start_idx:end_idx]

                if node_indices:
                    # Create new shard
                    dataset = self.datasets[dataset_id]
                    label_dist = self._calculate_label_distribution_from_indices(
                        dataset, node_indices
                    )

                    new_shard = DataShard(
                        shard_id=f"rebalanced_{node_id}_{int(time.time())}",
                        node_id=node_id,
                        data_indices=node_indices,
                        label_distribution=label_dist,
                        size=len(node_indices),
                        checksum=self._calculate_checksum(node_indices),
                        created_at=time.time(),
                    )

                    remaining_shards.append(new_shard)

                start_idx = end_idx

        # Update stored shards
        self.shards[dataset_id] = remaining_shards

        # Update node assignments
        self._update_node_assignments(dataset_id)

        return remaining_shards

    def _calculate_label_distribution_from_indices(
        self, dataset: data.Dataset, indices: List[int]
    ) -> Dict[str, int]:
        """Calculate label distribution from indices"""
        label_counts = defaultdict(int)

        for idx in indices:
            try:
                if hasattr(dataset, "targets"):
                    label = dataset.targets[idx]
                elif hasattr(dataset, "labels"):
                    label = dataset.labels[idx]
                else:
                    _, label = dataset[idx]

                if isinstance(label, torch.Tensor):
                    label = label.item()

                label_counts[str(label)] += 1

            except Exception:
                pass

        return dict(label_counts)

    def _calculate_checksum(self, indices: List[int]) -> str:
        """Calculate checksum for indices"""
        indices_str = ",".join(map(str, sorted(indices)))
        return hashlib.sha256(indices_str.encode()).hexdigest()[:16]

    def _update_node_assignments(self, dataset_id: str):
        """Update node shard assignments"""
        self.node_shard_assignments.clear()

        if dataset_id in self.shards:
            for shard in self.shards[dataset_id]:
                if shard.node_id not in self.node_shard_assignments:
                    self.node_shard_assignments[shard.node_id] = []
                self.node_shard_assignments[shard.node_id].append(shard.shard_id)

    def export_sharding_config(self, dataset_id: str) -> Dict[str, Any]:
        """Export sharding configuration for persistence"""
        if dataset_id not in self.shards:
            return {}

        return {
            "dataset_metadata": asdict(self.dataset_metadata[dataset_id]),
            "shards": [asdict(shard) for shard in self.shards[dataset_id]],
            "node_assignments": self.node_shard_assignments.copy(),
            "export_timestamp": time.time(),
        }

    def import_sharding_config(self, dataset_id: str, config: Dict[str, Any]):
        """Import sharding configuration"""

        # Import metadata
        metadata_dict = config["dataset_metadata"]
        self.dataset_metadata[dataset_id] = DatasetMetadata(**metadata_dict)

        # Import shards
        shard_dicts = config["shards"]
        self.shards[dataset_id] = [DataShard(**shard_dict) for shard_dict in shard_dicts]

        # Import node assignments
        self.node_shard_assignments.update(config["node_assignments"])

        self.logger.info(f"Imported sharding configuration for dataset {dataset_id}")

    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        total_datasets = len(self.datasets)
        total_nodes = len(self.node_capabilities)
        total_shards = sum(len(shards) for shards in self.shards.values())

        # Calculate total samples across all datasets
        total_samples = sum(metadata.total_samples for metadata in self.dataset_metadata.values())

        return {
            "total_datasets": total_datasets,
            "total_nodes": total_nodes,
            "total_shards": total_shards,
            "total_samples": total_samples,
            "avg_shards_per_dataset": total_shards / max(1, total_datasets),
            "avg_shards_per_node": total_shards / max(1, total_nodes),
        }
