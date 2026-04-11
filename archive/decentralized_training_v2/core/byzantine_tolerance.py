"""
Byzantine Fault Tolerance for Malicious Nodes
Implements robust aggregation mechanisms to handle adversarial participants
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import numpy as np
import torch
import torch.nn as nn
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import json

class AttackType(Enum):
    """Types of Byzantine attacks"""
    HONEST = "honest"
    RANDOM = "random"
    SIGN_FLIP = "sign_flip"
    GAUSSIAN = "gaussian"
    LABEL_FLIP = "label_flip"
    BACKDOOR = "backdoor"
    SYBIL = "sybil"

@dataclass
class NodeBehavior:
    """Track node behavior for Byzantine detection"""
    node_id: str
    gradient_norms: List[float]
    submission_times: List[float]
    accuracy_contributions: List[float]
    similarity_scores: List[float]
    reputation_score: float
    trust_score: float
    detected_attacks: List[AttackType]
    last_evaluation: float

@dataclass
class AggregationResult:
    """Result of Byzantine-tolerant aggregation"""
    aggregated_gradients: Dict[str, torch.Tensor]
    honest_participants: List[str]
    suspected_byzantine: List[str]
    confidence_score: float
    aggregation_method: str
    detection_stats: Dict[str, Any]

class ByzantineDetector:
    """Detects Byzantine/malicious nodes based on behavior analysis"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Detection thresholds
        self.norm_deviation_threshold = config.get('norm_deviation_threshold', 3.0)
        self.similarity_threshold = config.get('similarity_threshold', 0.1)
        self.timing_correlation_threshold = config.get('timing_correlation_threshold', 0.8)
        self.reputation_decay_rate = config.get('reputation_decay_rate', 0.05)
        
        # History tracking
        self.node_behaviors: Dict[str, NodeBehavior] = {}
        self.global_gradient_history: List[Dict[str, torch.Tensor]] = []
        
        self.logger = logging.getLogger(__name__)
    
    def analyze_gradients(self, gradients: Dict[str, Dict[str, torch.Tensor]]) -> Dict[str, float]:
        """Analyze gradients for Byzantine behavior"""
        suspicion_scores = {}
        
        if len(gradients) < 3:
            # Not enough participants for meaningful analysis
            return {node_id: 0.0 for node_id in gradients.keys()}
        
        # Calculate gradient norms
        norms = {}
        for node_id, node_gradients in gradients.items():
            total_norm = 0.0
            for param_grad in node_gradients.values():
                total_norm += torch.norm(param_grad).item() ** 2
            norms[node_id] = total_norm ** 0.5
        
        # Detect norm-based anomalies
        norm_values = list(norms.values())
        median_norm = np.median(norm_values)
        mad = np.median(np.abs(np.array(norm_values) - median_norm))  # Median Absolute Deviation
        
        for node_id, norm in norms.items():
            # Z-score based on MAD (robust to outliers)
            if mad > 0:
                z_score = abs(norm - median_norm) / (1.4826 * mad)  # 1.4826 makes MAD consistent with std
                if z_score > self.norm_deviation_threshold:
                    suspicion_scores[node_id] = min(1.0, z_score / self.norm_deviation_threshold)
                else:
                    suspicion_scores[node_id] = 0.0
            else:
                suspicion_scores[node_id] = 0.0
        
        # Cosine similarity analysis
        self._analyze_gradient_similarity(gradients, suspicion_scores)
        
        # Update node behavior tracking
        self._update_node_behaviors(gradients, norms, suspicion_scores)
        
        return suspicion_scores
    
    def _analyze_gradient_similarity(self, gradients: Dict[str, Dict[str, torch.Tensor]], 
                                   suspicion_scores: Dict[str, float]):
        """Analyze gradient similarity patterns"""
        node_ids = list(gradients.keys())
        similarities = np.zeros((len(node_ids), len(node_ids)))
        
        # Calculate pairwise cosine similarities
        for i, node_i in enumerate(node_ids):
            for j, node_j in enumerate(node_ids):
                if i != j:
                    similarity = self._calculate_cosine_similarity(
                        gradients[node_i], gradients[node_j]
                    )
                    similarities[i][j] = similarity
        
        # Detect outliers using clustering
        try:
            # Use average similarity as feature for clustering
            avg_similarities = similarities.mean(axis=1)
            
            if len(avg_similarities) > 2:
                # Reshape for sklearn
                features = avg_similarities.reshape(-1, 1)
                scaler = StandardScaler()
                scaled_features = scaler.fit_transform(features)
                
                # DBSCAN clustering to find outliers
                clustering = DBSCAN(eps=0.5, min_samples=2)
                labels = clustering.fit_predict(scaled_features)
                
                # Nodes with label -1 are outliers
                for i, label in enumerate(labels):
                    if label == -1:
                        node_id = node_ids[i]
                        # Increase suspicion for isolated nodes
                        suspicion_scores[node_id] = max(
                            suspicion_scores.get(node_id, 0.0),
                            0.7
                        )
        
        except Exception as e:
            self.logger.warning(f"Similarity clustering failed: {e}")
    
    def _calculate_cosine_similarity(self, grad1: Dict[str, torch.Tensor], 
                                   grad2: Dict[str, torch.Tensor]) -> float:
        """Calculate cosine similarity between two gradient dictionaries"""
        dot_product = 0.0
        norm1 = 0.0
        norm2 = 0.0
        
        common_keys = set(grad1.keys()) & set(grad2.keys())
        
        for key in common_keys:
            g1_flat = grad1[key].flatten()
            g2_flat = grad2[key].flatten()
            
            dot_product += torch.dot(g1_flat, g2_flat).item()
            norm1 += torch.norm(g1_flat).item() ** 2
            norm2 += torch.norm(g2_flat).item() ** 2
        
        norm1 = norm1 ** 0.5
        norm2 = norm2 ** 0.5
        
        if norm1 * norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _update_node_behaviors(self, gradients: Dict[str, Dict[str, torch.Tensor]], 
                             norms: Dict[str, float], suspicion_scores: Dict[str, float]):
        """Update behavior tracking for nodes"""
        current_time = time.time()
        
        for node_id in gradients.keys():
            if node_id not in self.node_behaviors:
                self.node_behaviors[node_id] = NodeBehavior(
                    node_id=node_id,
                    gradient_norms=[],
                    submission_times=[],
                    accuracy_contributions=[],
                    similarity_scores=[],
                    reputation_score=0.5,
                    trust_score=0.5,
                    detected_attacks=[],
                    last_evaluation=current_time
                )
            
            behavior = self.node_behaviors[node_id]
            
            # Update gradient norms
            behavior.gradient_norms.append(norms[node_id])
            if len(behavior.gradient_norms) > 50:
                behavior.gradient_norms = behavior.gradient_norms[-50:]
            
            # Update submission times
            behavior.submission_times.append(current_time)
            if len(behavior.submission_times) > 50:
                behavior.submission_times = behavior.submission_times[-50:]
            
            # Update reputation based on suspicion
            suspicion = suspicion_scores.get(node_id, 0.0)
            if suspicion > 0.5:
                behavior.reputation_score = max(0.0, behavior.reputation_score - 0.1)
            else:
                behavior.reputation_score = min(1.0, behavior.reputation_score + 0.01)
            
            # Decay reputation over time
            time_since_eval = current_time - behavior.last_evaluation
            if time_since_eval > 3600:  # 1 hour
                behavior.reputation_score *= (1 - self.reputation_decay_rate)
                behavior.last_evaluation = current_time
    
    def get_trusted_nodes(self, node_ids: List[str], min_trust_score: float = 0.3) -> List[str]:
        """Get list of nodes above trust threshold"""
        trusted = []
        
        for node_id in node_ids:
            if node_id in self.node_behaviors:
                if self.node_behaviors[node_id].reputation_score >= min_trust_score:
                    trusted.append(node_id)
            else:
                # New nodes get benefit of the doubt
                trusted.append(node_id)
        
        return trusted
    
    def detect_coordinated_attacks(self, gradients: Dict[str, Dict[str, torch.Tensor]]) -> List[Set[str]]:
        """Detect coordinated attacks by groups of nodes"""
        if len(gradients) < 4:
            return []
        
        node_ids = list(gradients.keys())
        suspicious_groups = []
        
        # Look for groups with highly similar gradients (potential Sybil attack)
        similarity_matrix = np.zeros((len(node_ids), len(node_ids)))
        
        for i, node_i in enumerate(node_ids):
            for j, node_j in enumerate(node_ids):
                if i != j:
                    similarity = self._calculate_cosine_similarity(
                        gradients[node_i], gradients[node_j]
                    )
                    similarity_matrix[i][j] = similarity
        
        # Find highly similar groups
        for i in range(len(node_ids)):
            similar_nodes = {node_ids[i]}
            
            for j in range(len(node_ids)):
                if i != j and similarity_matrix[i][j] > 0.95:  # Very high similarity
                    similar_nodes.add(node_ids[j])
            
            if len(similar_nodes) >= 3:  # Group of 3+ similar nodes is suspicious
                suspicious_groups.append(similar_nodes)
        
        # Remove overlapping groups (keep largest)
        unique_groups = []
        for group in sorted(suspicious_groups, key=len, reverse=True):
            is_subset = False
            for existing_group in unique_groups:
                if group.issubset(existing_group):
                    is_subset = True
                    break
            
            if not is_subset:
                unique_groups.append(group)
        
        return unique_groups

class ByzantineTolerantAggregator:
    """Implements various Byzantine-tolerant aggregation algorithms"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.detector = ByzantineDetector(config.get('detection', {}))
        
        # Aggregation parameters
        self.aggregation_method = config.get('aggregation_method', 'krum')
        self.byzantine_ratio = config.get('byzantine_ratio', 0.3)
        
        self.logger = logging.getLogger(__name__)
    
    async def aggregate(self, gradients: Dict[str, Dict[str, torch.Tensor]]) -> AggregationResult:
        """Perform Byzantine-tolerant aggregation"""
        
        if not gradients:
            raise ValueError("No gradients to aggregate")
        
        # Detect suspicious nodes
        suspicion_scores = self.detector.analyze_gradients(gradients)
        
        # Detect coordinated attacks
        coordinated_groups = self.detector.detect_coordinated_attacks(gradients)
        
        # Select aggregation method
        if self.aggregation_method == 'krum':
            result = await self._multi_krum_aggregation(gradients, suspicion_scores)
        elif self.aggregation_method == 'trimmed_mean':
            result = await self._trimmed_mean_aggregation(gradients, suspicion_scores)
        elif self.aggregation_method == 'median':
            result = await self._coordinate_wise_median(gradients, suspicion_scores)
        elif self.aggregation_method == 'fltrust':
            result = await self._fltrust_aggregation(gradients, suspicion_scores)
        else:
            result = await self._weighted_aggregation(gradients, suspicion_scores)
        
        # Add coordinated attack detection results
        result.detection_stats['coordinated_groups'] = [list(group) for group in coordinated_groups]
        result.detection_stats['suspicion_scores'] = suspicion_scores
        
        return result
    
    async def _multi_krum_aggregation(self, gradients: Dict[str, Dict[str, torch.Tensor]], 
                                    suspicion_scores: Dict[str, float]) -> AggregationResult:
        """Multi-Krum aggregation algorithm"""
        
        node_ids = list(gradients.keys())
        n = len(node_ids)
        f = int(n * self.byzantine_ratio)  # Assumed number of Byzantine nodes
        m = n - f - 2  # Number of closest nodes to consider
        
        if m <= 0:
            # Fallback to simple averaging
            return await self._weighted_aggregation(gradients, suspicion_scores)
        
        # Calculate pairwise distances
        distances = {}
        
        for i, node_i in enumerate(node_ids):
            distances[node_i] = {}
            for j, node_j in enumerate(node_ids):
                if i != j:
                    dist = self._calculate_euclidean_distance(gradients[node_i], gradients[node_j])
                    distances[node_i][node_j] = dist
        
        # Calculate Krum scores
        krum_scores = {}
        
        for node_i in node_ids:
            # Find m closest nodes
            node_distances = [(node_j, dist) for node_j, dist in distances[node_i].items()]
            node_distances.sort(key=lambda x: x[1])
            closest_m = node_distances[:m]
            
            # Sum of distances to m closest nodes
            krum_scores[node_i] = sum(dist for _, dist in closest_m)
        
        # Select nodes with lowest Krum scores (most similar to others)
        sorted_nodes = sorted(krum_scores.items(), key=lambda x: x[1])
        selected_nodes = [node for node, _ in sorted_nodes[:n-f]]
        
        # Average selected gradients
        aggregated = self._average_gradients([gradients[node] for node in selected_nodes])
        
        byzantine_nodes = [node for node in node_ids if node not in selected_nodes]
        
        return AggregationResult(
            aggregated_gradients=aggregated,
            honest_participants=selected_nodes,
            suspected_byzantine=byzantine_nodes,
            confidence_score=1.0 - (len(byzantine_nodes) / n),
            aggregation_method='multi_krum',
            detection_stats={'krum_scores': krum_scores}
        )
    
    async def _trimmed_mean_aggregation(self, gradients: Dict[str, Dict[str, torch.Tensor]], 
                                      suspicion_scores: Dict[str, float]) -> AggregationResult:
        """Trimmed mean aggregation"""
        
        node_ids = list(gradients.keys())
        n = len(node_ids)
        f = int(n * self.byzantine_ratio)
        
        # Get all parameter names
        param_names = set()
        for node_grads in gradients.values():
            param_names.update(node_grads.keys())
        
        aggregated = {}
        
        for param_name in param_names:
            # Collect all values for this parameter
            param_gradients = []
            contributing_nodes = []
            
            for node_id in node_ids:
                if param_name in gradients[node_id]:
                    param_gradients.append(gradients[node_id][param_name])
                    contributing_nodes.append(node_id)
            
            if not param_gradients:
                continue
            
            # Stack gradients for trimmed mean calculation
            stacked = torch.stack(param_gradients, dim=0)
            
            # Calculate trimmed mean (remove top and bottom f values)
            if len(param_gradients) > 2 * f:
                sorted_grads, _ = torch.sort(stacked, dim=0)
                trimmed = sorted_grads[f:-f] if f > 0 else sorted_grads
                aggregated[param_name] = torch.mean(trimmed, dim=0)
            else:
                # Not enough gradients for trimming
                aggregated[param_name] = torch.mean(stacked, dim=0)
        
        # Identify suspected nodes based on suspicion scores
        threshold = 0.5
        suspected = [node for node, score in suspicion_scores.items() if score > threshold]
        honest = [node for node in node_ids if node not in suspected]
        
        return AggregationResult(
            aggregated_gradients=aggregated,
            honest_participants=honest,
            suspected_byzantine=suspected,
            confidence_score=1.0 - (len(suspected) / n),
            aggregation_method='trimmed_mean',
            detection_stats={'trim_ratio': f / n}
        )
    
    async def _coordinate_wise_median(self, gradients: Dict[str, Dict[str, torch.Tensor]], 
                                    suspicion_scores: Dict[str, float]) -> AggregationResult:
        """Coordinate-wise median aggregation"""
        
        node_ids = list(gradients.keys())
        param_names = set()
        for node_grads in gradients.values():
            param_names.update(node_grads.keys())
        
        aggregated = {}
        
        for param_name in param_names:
            param_gradients = []
            
            for node_id in node_ids:
                if param_name in gradients[node_id]:
                    param_gradients.append(gradients[node_id][param_name])
            
            if param_gradients:
                stacked = torch.stack(param_gradients, dim=0)
                aggregated[param_name] = torch.median(stacked, dim=0)[0]
        
        # All nodes contribute to median, but flag highly suspicious ones
        threshold = 0.7
        suspected = [node for node, score in suspicion_scores.items() if score > threshold]
        honest = [node for node in node_ids if node not in suspected]
        
        return AggregationResult(
            aggregated_gradients=aggregated,
            honest_participants=honest,
            suspected_byzantine=suspected,
            confidence_score=1.0 - (len(suspected) / len(node_ids)),
            aggregation_method='coordinate_median',
            detection_stats={'median_robust': True}
        )
    
    async def _fltrust_aggregation(self, gradients: Dict[str, Dict[str, torch.Tensor]], 
                                 suspicion_scores: Dict[str, float]) -> AggregationResult:
        """FLTrust aggregation with server-side validation"""
        
        # This would require a trusted server gradient for comparison
        # For now, implement a simplified version using trust scores
        
        node_ids = list(gradients.keys())
        
        # Get trusted nodes
        trusted_nodes = self.detector.get_trusted_nodes(node_ids, min_trust_score=0.4)
        
        if len(trusted_nodes) < 2:
            # Fallback to trimmed mean
            return await self._trimmed_mean_aggregation(gradients, suspicion_scores)
        
        # Calculate trust-weighted average
        aggregated = {}
        param_names = set()
        for node_grads in gradients.values():
            param_names.update(node_grads.keys())
        
        for param_name in param_names:
            weighted_sum = None
            total_weight = 0.0
            
            for node_id in trusted_nodes:
                if param_name in gradients[node_id]:
                    trust_score = self.detector.node_behaviors.get(node_id, 
                                 NodeBehavior(node_id, [], [], [], [], 0.5, 0.5, [], 0)).reputation_score
                    
                    if weighted_sum is None:
                        weighted_sum = gradients[node_id][param_name] * trust_score
                    else:
                        weighted_sum += gradients[node_id][param_name] * trust_score
                    
                    total_weight += trust_score
            
            if total_weight > 0:
                aggregated[param_name] = weighted_sum / total_weight
        
        suspected = [node for node in node_ids if node not in trusted_nodes]
        
        return AggregationResult(
            aggregated_gradients=aggregated,
            honest_participants=trusted_nodes,
            suspected_byzantine=suspected,
            confidence_score=len(trusted_nodes) / len(node_ids),
            aggregation_method='fltrust',
            detection_stats={'trusted_ratio': len(trusted_nodes) / len(node_ids)}
        )
    
    async def _weighted_aggregation(self, gradients: Dict[str, Dict[str, torch.Tensor]], 
                                  suspicion_scores: Dict[str, float]) -> AggregationResult:
        """Weighted aggregation based on trust scores"""
        
        node_ids = list(gradients.keys())
        
        # Calculate weights (inverse of suspicion)
        weights = {}
        for node_id in node_ids:
            suspicion = suspicion_scores.get(node_id, 0.0)
            weights[node_id] = max(0.1, 1.0 - suspicion)  # Minimum weight of 0.1
        
        # Weighted average
        aggregated = {}
        param_names = set()
        for node_grads in gradients.values():
            param_names.update(node_grads.keys())
        
        for param_name in param_names:
            weighted_sum = None
            total_weight = 0.0
            
            for node_id in node_ids:
                if param_name in gradients[node_id]:
                    weight = weights[node_id]
                    
                    if weighted_sum is None:
                        weighted_sum = gradients[node_id][param_name] * weight
                    else:
                        weighted_sum += gradients[node_id][param_name] * weight
                    
                    total_weight += weight
            
            if total_weight > 0:
                aggregated[param_name] = weighted_sum / total_weight
        
        # Flag highly suspicious nodes
        threshold = 0.6
        suspected = [node for node, score in suspicion_scores.items() if score > threshold]
        honest = [node for node in node_ids if node not in suspected]
        
        return AggregationResult(
            aggregated_gradients=aggregated,
            honest_participants=honest,
            suspected_byzantine=suspected,
            confidence_score=1.0 - (len(suspected) / len(node_ids)),
            aggregation_method='weighted',
            detection_stats={'weights': weights}
        )
    
    def _calculate_euclidean_distance(self, grad1: Dict[str, torch.Tensor], 
                                    grad2: Dict[str, torch.Tensor]) -> float:
        """Calculate Euclidean distance between gradient dictionaries"""
        distance = 0.0
        common_keys = set(grad1.keys()) & set(grad2.keys())
        
        for key in common_keys:
            diff = grad1[key] - grad2[key]
            distance += torch.norm(diff).item() ** 2
        
        return distance ** 0.5
    
    def _average_gradients(self, gradient_list: List[Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
        """Average a list of gradient dictionaries"""
        if not gradient_list:
            return {}
        
        # Get all parameter names
        all_params = set()
        for grads in gradient_list:
            all_params.update(grads.keys())
        
        averaged = {}
        
        for param_name in all_params:
            param_grads = [grads[param_name] for grads in gradient_list if param_name in grads]
            
            if param_grads:
                averaged[param_name] = torch.mean(torch.stack(param_grads), dim=0)
        
        return averaged
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get Byzantine detection statistics"""
        total_nodes = len(self.detector.node_behaviors)
        
        if total_nodes == 0:
            return {'total_nodes': 0}
        
        reputation_scores = [behavior.reputation_score 
                           for behavior in self.detector.node_behaviors.values()]
        
        trusted_nodes = sum(1 for score in reputation_scores if score >= 0.5)
        suspicious_nodes = sum(1 for score in reputation_scores if score < 0.3)
        
        return {
            'total_nodes': total_nodes,
            'trusted_nodes': trusted_nodes,
            'suspicious_nodes': suspicious_nodes,
            'average_reputation': np.mean(reputation_scores) if reputation_scores else 0.0,
            'aggregation_method': self.aggregation_method,
            'byzantine_ratio_assumption': self.byzantine_ratio
        }

class AdaptiveByzantineDefense:
    """Adaptive defense mechanism that evolves with attack patterns"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.aggregator = ByzantineTolerantAggregator(config)
        
        # Adaptive parameters
        self.attack_history: List[Tuple[float, AttackType, List[str]]] = []
        self.defense_effectiveness: Dict[str, float] = {
            'krum': 0.7,
            'trimmed_mean': 0.8,
            'median': 0.6,
            'fltrust': 0.9,
            'weighted': 0.5
        }
        
        # Learning parameters
        self.adaptation_rate = config.get('adaptation_rate', 0.1)
        self.min_samples_for_adaptation = config.get('min_samples', 10)
        
        self.logger = logging.getLogger(__name__)
    
    async def adaptive_aggregate(self, gradients: Dict[str, Dict[str, torch.Tensor]]) -> AggregationResult:
        """Perform adaptive Byzantine-tolerant aggregation"""
        
        # Analyze current threat level
        threat_level = self._assess_threat_level(gradients)
        
        # Adapt aggregation method based on threat and historical effectiveness
        optimal_method = self._select_optimal_method(threat_level)
        
        # Update aggregator method
        self.aggregator.aggregation_method = optimal_method
        
        # Perform aggregation
        result = await self.aggregator.aggregate(gradients)
        
        # Update defense effectiveness based on result
        self._update_effectiveness(optimal_method, result)
        
        # Record attack patterns if detected
        if result.suspected_byzantine:
            current_time = time.time()
            attack_type = self._classify_attack_type(gradients, result.suspected_byzantine)
            self.attack_history.append((current_time, attack_type, result.suspected_byzantine))
        
        result.aggregation_method = f"adaptive_{optimal_method}"
        
        return result
    
    def _assess_threat_level(self, gradients: Dict[str, Dict[str, torch.Tensor]]) -> float:
        """Assess current threat level based on gradient patterns"""
        
        if len(gradients) < 3:
            return 0.0
        
        # Calculate gradient diversity
        similarities = []
        node_ids = list(gradients.keys())
        
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                sim = self.aggregator.detector._calculate_cosine_similarity(
                    gradients[node_ids[i]], gradients[node_ids[j]]
                )
                similarities.append(sim)
        
        # High similarity might indicate coordinated attacks
        avg_similarity = np.mean(similarities)
        similarity_std = np.std(similarities)
        
        # High variance in gradient norms might indicate attacks
        norms = []
        for node_grads in gradients.values():
            total_norm = sum(torch.norm(grad).item() ** 2 for grad in node_grads.values()) ** 0.5
            norms.append(total_norm)
        
        norm_cv = np.std(norms) / (np.mean(norms) + 1e-7)  # Coefficient of variation
        
        # Combine metrics for threat assessment
        threat_score = 0.0
        
        if avg_similarity > 0.9:  # Suspiciously high similarity
            threat_score += 0.4
        
        if similarity_std < 0.05:  # Low diversity
            threat_score += 0.3
        
        if norm_cv > 2.0:  # High norm variance
            threat_score += 0.3
        
        return min(1.0, threat_score)
    
    def _select_optimal_method(self, threat_level: float) -> str:
        """Select optimal aggregation method based on threat level and effectiveness"""
        
        # Weight methods by effectiveness and suitability for current threat
        method_scores = {}
        
        for method, base_effectiveness in self.defense_effectiveness.items():
            # Adjust effectiveness based on threat level
            if threat_level > 0.7:  # High threat
                if method in ['fltrust', 'krum']:
                    adjusted_effectiveness = base_effectiveness * 1.2
                elif method == 'median':
                    adjusted_effectiveness = base_effectiveness * 1.1
                else:
                    adjusted_effectiveness = base_effectiveness * 0.9
            elif threat_level > 0.4:  # Medium threat
                if method in ['trimmed_mean', 'krum']:
                    adjusted_effectiveness = base_effectiveness * 1.1
                else:
                    adjusted_effectiveness = base_effectiveness
            else:  # Low threat
                if method == 'weighted':
                    adjusted_effectiveness = base_effectiveness * 1.2
                else:
                    adjusted_effectiveness = base_effectiveness
            
            method_scores[method] = adjusted_effectiveness
        
        # Select method with highest adjusted effectiveness
        optimal_method = max(method_scores, key=method_scores.get)
        
        self.logger.info(f"Selected {optimal_method} method (threat level: {threat_level:.2f})")
        
        return optimal_method
    
    def _update_effectiveness(self, method: str, result: AggregationResult):
        """Update method effectiveness based on aggregation result"""
        
        # Use confidence score as effectiveness measure
        current_effectiveness = self.defense_effectiveness.get(method, 0.5)
        new_effectiveness = result.confidence_score
        
        # Exponential moving average update
        updated_effectiveness = ((1 - self.adaptation_rate) * current_effectiveness + 
                               self.adaptation_rate * new_effectiveness)
        
        self.defense_effectiveness[method] = max(0.1, min(1.0, updated_effectiveness))
    
    def _classify_attack_type(self, gradients: Dict[str, Dict[str, torch.Tensor]], 
                            suspected_nodes: List[str]) -> AttackType:
        """Classify the type of attack based on patterns"""
        
        if len(suspected_nodes) >= len(gradients) * 0.3:
            return AttackType.SYBIL
        
        # Analyze gradient patterns of suspected nodes
        suspected_grads = [gradients[node] for node in suspected_nodes if node in gradients]
        
        if not suspected_grads:
            return AttackType.RANDOM
        
        # Check for sign flipping
        # This is a simplified heuristic - in practice, would need more sophisticated analysis
        
        return AttackType.GAUSSIAN  # Default classification
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get adaptation statistics"""
        recent_attacks = [attack for timestamp, attack, nodes in self.attack_history 
                         if time.time() - timestamp < 3600]  # Last hour
        
        attack_counts = {}
        for attack_type in AttackType:
            attack_counts[attack_type.value] = sum(1 for attack in recent_attacks if attack == attack_type)
        
        return {
            'defense_effectiveness': self.defense_effectiveness.copy(),
            'recent_attacks_count': len(recent_attacks),
            'attack_type_distribution': attack_counts,
            'total_attack_history': len(self.attack_history),
            'current_optimal_method': max(self.defense_effectiveness, 
                                        key=self.defense_effectiveness.get)
        }