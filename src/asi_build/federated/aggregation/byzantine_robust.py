"""
Byzantine-Robust Aggregation for Federated Learning

Implementation of aggregation methods that are robust against
Byzantine (malicious) clients and various attack scenarios.
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from ..core.exceptions import AggregationError, SecurityError
from .base_aggregator import BaseAggregator


class ByzantineRobustAggregator(BaseAggregator):
    """
    Byzantine-robust aggregator using multiple defense mechanisms.

    Implements various robust aggregation methods to defend against
    malicious clients in federated learning.
    """

    def __init__(self, aggregator_id: str = "byzantine_robust", config: Dict[str, Any] = None):
        super().__init__(aggregator_id, config)

        # Byzantine defense parameters
        self.defense_method = self.config.get("defense_method", "krum")
        self.num_byzantine = self.config.get("num_byzantine", 1)
        self.trimmed_mean_ratio = self.config.get("trimmed_mean_ratio", 0.1)
        self.median_threshold = self.config.get("median_threshold", 2.0)
        self.clustering_eps = self.config.get("clustering_eps", 0.5)
        self.clustering_min_samples = self.config.get("clustering_min_samples", 2)

        # Detection parameters
        self.enable_anomaly_detection = self.config.get("enable_anomaly_detection", True)
        self.anomaly_threshold = self.config.get("anomaly_threshold", 2.5)

        # Defense statistics
        self.byzantine_detections = []
        self.defense_history = []

        self.logger.info(
            f"Byzantine-robust aggregator initialized with method: {self.defense_method}"
        )

    def aggregate(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate client updates with Byzantine robustness."""
        start_time = time.time()

        # Validate updates
        self.validate_updates(client_updates)

        # Extract client information
        client_weights_list = [update["weights"] for update in client_updates]
        data_sizes = [update["data_size"] for update in client_updates]
        client_ids = [update["client_id"] for update in client_updates]

        self.logger.info(f"Byzantine-robust aggregation for {len(client_updates)} clients")

        try:
            # Detect potential Byzantine clients
            if self.enable_anomaly_detection:
                byzantine_scores = self._detect_byzantine_clients(client_weights_list, client_ids)
            else:
                byzantine_scores = [0.0] * len(client_updates)

            # Apply Byzantine-robust aggregation
            if self.defense_method == "krum":
                aggregated_weights, defense_info = self._krum_aggregation(
                    client_weights_list, data_sizes, client_ids
                )
            elif self.defense_method == "multi_krum":
                aggregated_weights, defense_info = self._multi_krum_aggregation(
                    client_weights_list, data_sizes, client_ids
                )
            elif self.defense_method == "trimmed_mean":
                aggregated_weights, defense_info = self._trimmed_mean_aggregation(
                    client_weights_list, data_sizes
                )
            elif self.defense_method == "median":
                aggregated_weights, defense_info = self._coordinate_wise_median(
                    client_weights_list, data_sizes
                )
            elif self.defense_method == "clustering":
                aggregated_weights, defense_info = self._clustering_based_aggregation(
                    client_weights_list, data_sizes, client_ids
                )
            elif self.defense_method == "faba":
                aggregated_weights, defense_info = self._faba_aggregation(
                    client_weights_list, data_sizes, client_ids
                )
            else:
                raise ValueError(f"Unknown defense method: {self.defense_method}")

            # Apply additional security measures
            aggregated_weights = self.clip_weights(aggregated_weights)
            aggregated_weights = self.add_noise(aggregated_weights)

            aggregation_time = time.time() - start_time

            # Compile results
            result = {
                "aggregated_weights": aggregated_weights,
                "num_clients": len(client_updates),
                "aggregation_time": aggregation_time,
                "aggregation_method": f"byzantine_robust_{self.defense_method}",
                "byzantine_scores": byzantine_scores,
                "defense_info": defense_info,
                "metadata": {
                    "defense_method": self.defense_method,
                    "num_byzantine_expected": self.num_byzantine,
                    "anomaly_detection_enabled": self.enable_anomaly_detection,
                    "total_samples": sum(data_sizes),
                },
            }

            # Record defense statistics
            self._record_defense_statistics(result, client_ids, byzantine_scores)
            self.record_aggregation(result)

            self.logger.info(f"Byzantine-robust aggregation completed in {aggregation_time:.3f}s")
            return result

        except Exception as e:
            self.logger.error(f"Byzantine-robust aggregation failed: {str(e)}")
            raise AggregationError(
                f"Byzantine-robust aggregation failed: {str(e)}",
                aggregator_type=self.aggregator_id,
                client_count=len(client_updates),
            )

    def _detect_byzantine_clients(
        self, client_weights_list: List[List[np.ndarray]], client_ids: List[str]
    ) -> List[float]:
        """Detect potential Byzantine clients using statistical analysis."""
        byzantine_scores = []

        # Flatten all client weights for analysis
        flattened_weights = []
        for weights in client_weights_list:
            flat_weight = np.concatenate([w.flatten() for w in weights])
            flattened_weights.append(flat_weight)

        flattened_weights = np.array(flattened_weights)

        # Compute statistics for anomaly detection
        for i, client_weights in enumerate(flattened_weights):
            # Method 1: Distance from median
            median_weights = np.median(flattened_weights, axis=0)
            distance_from_median = np.linalg.norm(client_weights - median_weights)

            # Method 2: Z-score based detection
            mean_weights = np.mean(flattened_weights, axis=0)
            std_weights = np.std(flattened_weights, axis=0)

            # Avoid division by zero
            std_weights = np.where(std_weights == 0, 1e-8, std_weights)
            z_scores = np.abs((client_weights - mean_weights) / std_weights)
            max_z_score = np.max(z_scores)

            # Method 3: Mahalanobis distance (simplified)
            try:
                cov_matrix = np.cov(flattened_weights.T)
                if np.linalg.det(cov_matrix) != 0:
                    inv_cov = np.linalg.inv(cov_matrix)
                    diff = client_weights - mean_weights
                    mahalanobis_dist = np.sqrt(diff.T @ inv_cov @ diff)
                else:
                    mahalanobis_dist = distance_from_median
            except:
                mahalanobis_dist = distance_from_median

            # Combine scores
            byzantine_score = (
                0.4 * distance_from_median + 0.3 * max_z_score + 0.3 * mahalanobis_dist
            )

            byzantine_scores.append(float(byzantine_score))

        # Normalize scores
        if byzantine_scores:
            max_score = max(byzantine_scores)
            if max_score > 0:
                byzantine_scores = [score / max_score for score in byzantine_scores]

        # Log potential Byzantine clients
        for i, (client_id, score) in enumerate(zip(client_ids, byzantine_scores)):
            if score > self.anomaly_threshold:
                self.logger.warning(
                    f"Potential Byzantine client detected: {client_id} (score: {score:.3f})"
                )

        return byzantine_scores

    def _krum_aggregation(
        self,
        client_weights_list: List[List[np.ndarray]],
        data_sizes: List[int],
        client_ids: List[str],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """Krum aggregation method."""
        n = len(client_weights_list)
        f = self.num_byzantine

        if n <= 2 * f:
            raise SecurityError(
                f"Insufficient honest clients for Krum. Need > 2f={2*f}, got {n}",
                security_level="byzantine_robust",
                threat_type="insufficient_honest_clients",
            )

        # Compute pairwise distances
        distances = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                dist = self._compute_weight_distance(client_weights_list[i], client_weights_list[j])
                distances[i, j] = dist
                distances[j, i] = dist

        # Compute Krum scores
        krum_scores = []
        for i in range(n):
            # Sum of distances to n-f-1 closest clients
            sorted_distances = np.sort(distances[i])
            score = np.sum(sorted_distances[1 : n - f])  # Exclude self (distance 0)
            krum_scores.append(score)

        # Select client with minimum Krum score
        selected_idx = np.argmin(krum_scores)
        selected_weights = client_weights_list[selected_idx]

        defense_info = {
            "method": "krum",
            "selected_client": client_ids[selected_idx],
            "selected_client_idx": selected_idx,
            "krum_scores": krum_scores,
            "num_byzantine_expected": f,
            "distance_matrix_shape": distances.shape,
        }

        return [w.copy() for w in selected_weights], defense_info

    def _multi_krum_aggregation(
        self,
        client_weights_list: List[List[np.ndarray]],
        data_sizes: List[int],
        client_ids: List[str],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """Multi-Krum aggregation method."""
        n = len(client_weights_list)
        f = self.num_byzantine
        m = max(1, n - f - 2)  # Number of clients to select

        if n <= 2 * f:
            raise SecurityError(
                f"Insufficient honest clients for Multi-Krum. Need > 2f={2*f}, got {n}",
                security_level="byzantine_robust",
            )

        # Compute pairwise distances
        distances = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                dist = self._compute_weight_distance(client_weights_list[i], client_weights_list[j])
                distances[i, j] = dist
                distances[j, i] = dist

        # Compute Krum scores
        krum_scores = []
        for i in range(n):
            sorted_distances = np.sort(distances[i])
            score = np.sum(sorted_distances[1 : n - f])
            krum_scores.append(score)

        # Select top m clients with lowest Krum scores
        selected_indices = np.argsort(krum_scores)[:m]
        selected_weights = [client_weights_list[i] for i in selected_indices]
        selected_data_sizes = [data_sizes[i] for i in selected_indices]

        # Compute weighted average of selected clients
        aggregation_weights = []
        total_samples = sum(selected_data_sizes)
        for size in selected_data_sizes:
            aggregation_weights.append(
                size / total_samples if total_samples > 0 else 1.0 / len(selected_weights)
            )

        aggregated_weights = self.weighted_average(selected_weights, aggregation_weights)

        defense_info = {
            "method": "multi_krum",
            "selected_clients": [client_ids[i] for i in selected_indices],
            "selected_indices": selected_indices.tolist(),
            "num_selected": m,
            "krum_scores": krum_scores,
            "aggregation_weights": aggregation_weights,
        }

        return aggregated_weights, defense_info

    def _trimmed_mean_aggregation(
        self, client_weights_list: List[List[np.ndarray]], data_sizes: List[int]
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """Trimmed mean aggregation method."""
        n = len(client_weights_list)
        trim_count = max(1, int(n * self.trimmed_mean_ratio))

        aggregated_weights = []
        num_layers = len(client_weights_list[0])

        for layer_idx in range(num_layers):
            layer_weights = [weights[layer_idx] for weights in client_weights_list]

            # Apply trimmed mean coordinate-wise
            layer_shape = layer_weights[0].shape
            flat_weights = np.array([w.flatten() for w in layer_weights])

            trimmed_layer = np.zeros_like(flat_weights[0])

            for coord_idx in range(flat_weights.shape[1]):
                coord_values = flat_weights[:, coord_idx]
                coord_values_sorted = np.sort(coord_values)

                # Remove extreme values
                trimmed_values = (
                    coord_values_sorted[trim_count:-trim_count]
                    if trim_count > 0
                    else coord_values_sorted
                )
                trimmed_layer[coord_idx] = np.mean(trimmed_values)

            aggregated_weights.append(trimmed_layer.reshape(layer_shape))

        defense_info = {
            "method": "trimmed_mean",
            "trim_ratio": self.trimmed_mean_ratio,
            "trim_count": trim_count,
            "remaining_clients": n - 2 * trim_count,
        }

        return aggregated_weights, defense_info

    def _coordinate_wise_median(
        self, client_weights_list: List[List[np.ndarray]], data_sizes: List[int]
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """Coordinate-wise median aggregation."""
        aggregated_weights = []
        num_layers = len(client_weights_list[0])

        for layer_idx in range(num_layers):
            layer_weights = [weights[layer_idx] for weights in client_weights_list]

            # Stack weights and compute median
            stacked_weights = np.stack(layer_weights, axis=0)
            median_weights = np.median(stacked_weights, axis=0)

            aggregated_weights.append(median_weights)

        defense_info = {"method": "coordinate_wise_median", "num_clients": len(client_weights_list)}

        return aggregated_weights, defense_info

    def _clustering_based_aggregation(
        self,
        client_weights_list: List[List[np.ndarray]],
        data_sizes: List[int],
        client_ids: List[str],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """Clustering-based robust aggregation."""
        # Flatten weights for clustering
        flattened_weights = []
        for weights in client_weights_list:
            flat_weight = np.concatenate([w.flatten() for w in weights])
            flattened_weights.append(flat_weight)

        flattened_weights = np.array(flattened_weights)

        # Standardize features for clustering
        scaler = StandardScaler()
        normalized_weights = scaler.fit_transform(flattened_weights)

        # Apply DBSCAN clustering
        clustering = DBSCAN(eps=self.clustering_eps, min_samples=self.clustering_min_samples).fit(
            normalized_weights
        )

        labels = clustering.labels_
        unique_labels = set(labels)

        # Find the largest cluster (assumed to be honest clients)
        largest_cluster_label = -1
        largest_cluster_size = 0

        for label in unique_labels:
            if label != -1:  # -1 is noise/outliers
                cluster_size = np.sum(labels == label)
                if cluster_size > largest_cluster_size:
                    largest_cluster_size = cluster_size
                    largest_cluster_label = label

        # Aggregate weights from the largest cluster
        if largest_cluster_label != -1:
            cluster_indices = np.where(labels == largest_cluster_label)[0]
            cluster_weights = [client_weights_list[i] for i in cluster_indices]
            cluster_data_sizes = [data_sizes[i] for i in cluster_indices]

            # Compute weighted average
            if sum(cluster_data_sizes) > 0:
                aggregation_weights = [
                    size / sum(cluster_data_sizes) for size in cluster_data_sizes
                ]
            else:
                aggregation_weights = [1.0 / len(cluster_weights)] * len(cluster_weights)

            aggregated_weights = self.weighted_average(cluster_weights, aggregation_weights)

            selected_clients = [client_ids[i] for i in cluster_indices]
        else:
            # Fallback to regular averaging if no good cluster found
            aggregation_weights = self.compute_client_weights(
                [{"data_size": size} for size in data_sizes]
            )
            aggregated_weights = self.weighted_average(client_weights_list, aggregation_weights)
            selected_clients = client_ids

        defense_info = {
            "method": "clustering",
            "num_clusters": len(unique_labels) - (1 if -1 in unique_labels else 0),
            "largest_cluster_size": largest_cluster_size,
            "selected_clients": selected_clients,
            "outliers": [client_ids[i] for i, label in enumerate(labels) if label == -1],
            "clustering_labels": labels.tolist(),
        }

        return aggregated_weights, defense_info

    def _faba_aggregation(
        self,
        client_weights_list: List[List[np.ndarray]],
        data_sizes: List[int],
        client_ids: List[str],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """FedAvg with Byzantine-resilient aggregation (FABA)."""
        # Compute initial aggregate using FedAvg
        aggregation_weights = self.compute_client_weights(
            [{"data_size": size} for size in data_sizes]
        )
        initial_aggregate = self.weighted_average(client_weights_list, aggregation_weights)

        # Compute distances from initial aggregate
        distances = []
        for weights in client_weights_list:
            dist = self._compute_weight_distance(weights, initial_aggregate)
            distances.append(dist)

        # Remove clients that are too far from the aggregate
        median_distance = np.median(distances)
        mad = np.median(np.abs(np.array(distances) - median_distance))  # Median Absolute Deviation
        threshold = median_distance + self.median_threshold * mad

        # Select clients within threshold
        selected_indices = [i for i, dist in enumerate(distances) if dist <= threshold]

        if len(selected_indices) < len(client_weights_list) // 2:
            # Too many clients removed, fallback to less aggressive filtering
            selected_indices = list(range(len(client_weights_list)))

        # Re-aggregate with selected clients
        selected_weights = [client_weights_list[i] for i in selected_indices]
        selected_data_sizes = [data_sizes[i] for i in selected_indices]

        if sum(selected_data_sizes) > 0:
            final_aggregation_weights = [
                size / sum(selected_data_sizes) for size in selected_data_sizes
            ]
        else:
            final_aggregation_weights = [1.0 / len(selected_weights)] * len(selected_weights)

        aggregated_weights = self.weighted_average(selected_weights, final_aggregation_weights)

        defense_info = {
            "method": "faba",
            "initial_clients": len(client_weights_list),
            "selected_clients": len(selected_indices),
            "removed_clients": [
                client_ids[i] for i in range(len(client_ids)) if i not in selected_indices
            ],
            "median_distance": median_distance,
            "mad": mad,
            "threshold": threshold,
            "distances": distances,
        }

        return aggregated_weights, defense_info

    def _compute_weight_distance(
        self, weights1: List[np.ndarray], weights2: List[np.ndarray]
    ) -> float:
        """Compute L2 distance between two weight vectors."""
        total_distance = 0.0

        for w1, w2 in zip(weights1, weights2):
            layer_distance = np.linalg.norm(w1 - w2)
            total_distance += layer_distance**2

        return math.sqrt(total_distance)

    def _record_defense_statistics(
        self, result: Dict[str, Any], client_ids: List[str], byzantine_scores: List[float]
    ):
        """Record Byzantine defense statistics."""
        defense_record = {
            "timestamp": time.time(),
            "method": self.defense_method,
            "num_clients": len(client_ids),
            "byzantine_scores": byzantine_scores,
            "defense_info": result["defense_info"],
            "high_risk_clients": [
                client_ids[i]
                for i, score in enumerate(byzantine_scores)
                if score > self.anomaly_threshold
            ],
        }

        self.defense_history.append(defense_record)

        # Keep only recent history
        max_history = self.config.get("max_defense_history", 100)
        if len(self.defense_history) > max_history:
            self.defense_history = self.defense_history[-max_history:]

    def get_byzantine_defense_stats(self) -> Dict[str, Any]:
        """Get Byzantine defense statistics."""
        base_stats = self.get_aggregation_stats()

        defense_stats = {
            "defense_method": self.defense_method,
            "num_byzantine_expected": self.num_byzantine,
            "anomaly_detection_enabled": self.enable_anomaly_detection,
            "total_defense_rounds": len(self.defense_history),
            "avg_byzantine_score": (
                np.mean([np.mean(record["byzantine_scores"]) for record in self.defense_history])
                if self.defense_history
                else 0.0
            ),
            "high_risk_detections": sum(
                [len(record["high_risk_clients"]) for record in self.defense_history]
            ),
        }

        base_stats.update(defense_stats)
        return base_stats
