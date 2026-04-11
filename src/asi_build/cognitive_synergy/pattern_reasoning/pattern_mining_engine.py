"""
Pattern Mining Engine
====================

Advanced pattern mining system that discovers regularities, structures, and
emergent patterns from sensory input, memory, and cognitive activity.
Integrates with reasoning through bidirectional information flow.
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


@dataclass
class Pattern:
    """Represents a discovered pattern"""

    id: str
    type: str  # 'sequence', 'spatial', 'temporal', 'structural', 'causal'
    content: Any
    confidence: float
    support: int  # Number of instances supporting this pattern
    frequency: float
    complexity: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class PatternHierarchy:
    """Hierarchical pattern structure"""

    root_patterns: List[Pattern] = field(default_factory=list)
    sub_patterns: Dict[str, List[Pattern]] = field(default_factory=dict)
    super_patterns: Dict[str, List[Pattern]] = field(default_factory=dict)
    relationships: nx.DiGraph = field(default_factory=nx.DiGraph)


class PatternMiningEngine:
    """
    Advanced pattern mining engine for cognitive synergy.

    Discovers patterns at multiple levels:
    - Low-level sensory patterns
    - Mid-level conceptual patterns
    - High-level abstract patterns
    - Meta-patterns (patterns of patterns)
    """

    def __init__(
        self,
        max_patterns: int = 10000,
        min_support: int = 3,
        min_confidence: float = 0.6,
        complexity_penalty: float = 0.1,
    ):
        """
        Initialize pattern mining engine.

        Args:
            max_patterns: Maximum patterns to maintain
            min_support: Minimum support for pattern validity
            min_confidence: Minimum confidence for pattern validity
            complexity_penalty: Penalty for complex patterns (Occam's razor)
        """
        self.max_patterns = max_patterns
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.complexity_penalty = complexity_penalty

        # Pattern storage
        self.patterns: Dict[str, Pattern] = {}
        self.pattern_hierarchy = PatternHierarchy()

        # Input buffers for different data types
        self.sequence_buffer = deque(maxlen=1000)
        self.spatial_buffer = deque(maxlen=500)
        self.temporal_buffer = deque(maxlen=1000)
        self.causal_buffer = deque(maxlen=500)

        # Pattern mining algorithms
        self.clusterer = DBSCAN(eps=0.3, min_samples=3)
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=0.95)  # Keep 95% variance

        # Statistics and metrics
        self.mining_stats = {
            "patterns_discovered": 0,
            "patterns_validated": 0,
            "patterns_pruned": 0,
            "total_mining_time": 0.0,
        }

        # Reasoning integration
        self.reasoning_feedback = {}
        self.reasoning_requests = deque(maxlen=100)

        # State
        self.activation_level = 0.0
        self._last_mining_time = 0.0

        # Logger
        self.logger = logging.getLogger(__name__)

    def process_input(self, input_data: Dict[str, Any]):
        """Process input data for pattern mining"""
        input_type = input_data.get("type", "unknown")
        data = input_data.get("data")
        timestamp = input_data.get("timestamp", time.time())

        # Route data to appropriate buffer
        if input_type == "sequence":
            self.sequence_buffer.append((data, timestamp))
        elif input_type == "spatial":
            self.spatial_buffer.append((data, timestamp))
        elif input_type == "temporal":
            self.temporal_buffer.append((data, timestamp))
        elif input_type == "causal":
            self.causal_buffer.append((data, timestamp))
        else:
            # Default to sequence buffer
            self.sequence_buffer.append((data, timestamp))

        # Update activation
        self.activation_level = min(1.0, self.activation_level + 0.1)

    def mine_patterns(self) -> List[Pattern]:
        """Main pattern mining process"""
        start_time = time.time()
        discovered_patterns = []

        # Mine different types of patterns
        sequence_patterns = self._mine_sequence_patterns()
        spatial_patterns = self._mine_spatial_patterns()
        temporal_patterns = self._mine_temporal_patterns()
        structural_patterns = self._mine_structural_patterns()
        causal_patterns = self._mine_causal_patterns()

        discovered_patterns.extend(sequence_patterns)
        discovered_patterns.extend(spatial_patterns)
        discovered_patterns.extend(temporal_patterns)
        discovered_patterns.extend(structural_patterns)
        discovered_patterns.extend(causal_patterns)

        # Validate patterns
        valid_patterns = self._validate_patterns(discovered_patterns)

        # Update pattern store
        for pattern in valid_patterns:
            self.patterns[pattern.id] = pattern

        # Build pattern hierarchy
        self._build_pattern_hierarchy()

        # Prune old/weak patterns
        self._prune_patterns()

        # Update statistics
        mining_time = time.time() - start_time
        self.mining_stats["total_mining_time"] += mining_time
        self.mining_stats["patterns_discovered"] += len(discovered_patterns)
        self.mining_stats["patterns_validated"] += len(valid_patterns)
        self._last_mining_time = mining_time

        return valid_patterns

    def _mine_sequence_patterns(self) -> List[Pattern]:
        """Mine sequential patterns from sequence buffer"""
        if len(self.sequence_buffer) < 3:
            return []

        patterns = []
        sequences = [item[0] for item in self.sequence_buffer if item[0] is not None]

        # Convert sequences to numerical if possible
        numerical_sequences = []
        for seq in sequences:
            if isinstance(seq, (list, tuple, np.ndarray)):
                try:
                    num_seq = [float(x) for x in seq if isinstance(x, (int, float))]
                    if num_seq:
                        numerical_sequences.append(num_seq)
                except (ValueError, TypeError):
                    continue

        if not numerical_sequences:
            return patterns

        # Find common subsequences
        common_subsequences = self._find_common_subsequences(numerical_sequences)

        for i, subseq in enumerate(common_subsequences):
            pattern = Pattern(
                id=f"sequence_{int(time.time() * 1000)}_{i}",
                type="sequence",
                content=subseq["sequence"],
                confidence=subseq["confidence"],
                support=subseq["support"],
                frequency=subseq["frequency"],
                complexity=len(subseq["sequence"]) * self.complexity_penalty,
            )
            patterns.append(pattern)

        return patterns

    def _mine_spatial_patterns(self) -> List[Pattern]:
        """Mine spatial patterns from spatial buffer"""
        if len(self.spatial_buffer) < 3:
            return []

        patterns = []
        spatial_data = []

        # Extract spatial data
        for item in self.spatial_buffer:
            data = item[0]
            if isinstance(data, np.ndarray) and len(data.shape) >= 2:
                spatial_data.append(data.flatten())
            elif isinstance(data, (list, tuple)):
                try:
                    flat_data = np.array(data).flatten()
                    spatial_data.append(flat_data)
                except (ValueError, TypeError):
                    continue

        if not spatial_data or len(spatial_data) < 3:
            return patterns

        # Normalize data
        try:
            spatial_array = np.array([d for d in spatial_data if len(d) > 0])
            if spatial_array.size == 0:
                return patterns

            # Make all arrays same length by padding/truncating
            max_len = min(100, max(len(d) for d in spatial_data))  # Limit to prevent memory issues
            normalized_data = []

            for data in spatial_data:
                if len(data) >= max_len:
                    normalized_data.append(data[:max_len])
                else:
                    padded = np.pad(data, (0, max_len - len(data)), mode="constant")
                    normalized_data.append(padded)

            spatial_array = np.array(normalized_data)
            scaled_data = self.scaler.fit_transform(spatial_array)

            # Cluster spatial patterns
            clusters = self.clusterer.fit_predict(scaled_data)

            # Create patterns from clusters
            unique_clusters = set(clusters) - {-1}  # Exclude noise
            for cluster_id in unique_clusters:
                cluster_mask = clusters == cluster_id
                cluster_data = scaled_data[cluster_mask]

                if len(cluster_data) >= self.min_support:
                    # Compute cluster centroid as pattern
                    centroid = np.mean(cluster_data, axis=0)

                    pattern = Pattern(
                        id=f"spatial_{int(time.time() * 1000)}_{cluster_id}",
                        type="spatial",
                        content=centroid,
                        confidence=min(1.0, len(cluster_data) / len(spatial_data)),
                        support=len(cluster_data),
                        frequency=len(cluster_data) / len(spatial_data),
                        complexity=len(centroid) * self.complexity_penalty,
                    )
                    patterns.append(pattern)

        except Exception as e:
            self.logger.warning(f"Spatial pattern mining failed: {e}")

        return patterns

    def _mine_temporal_patterns(self) -> List[Pattern]:
        """Mine temporal patterns from temporal buffer"""
        if len(self.temporal_buffer) < 5:
            return []

        patterns = []
        temporal_data = [(item[0], item[1]) for item in self.temporal_buffer]

        # Sort by timestamp
        temporal_data.sort(key=lambda x: x[1])

        # Extract time series
        values = []
        timestamps = []

        for value, timestamp in temporal_data:
            if isinstance(value, (int, float)):
                values.append(float(value))
                timestamps.append(timestamp)
            elif isinstance(value, (list, tuple, np.ndarray)):
                try:
                    # Take mean for multi-dimensional data
                    mean_val = np.mean([float(x) for x in value if isinstance(x, (int, float))])
                    if not np.isnan(mean_val):
                        values.append(mean_val)
                        timestamps.append(timestamp)
                except (ValueError, TypeError):
                    continue

        if len(values) < 5:
            return patterns

        # Detect temporal patterns
        time_series = np.array(values)

        # Moving averages for trend detection
        if len(time_series) >= 5:
            trends = self._detect_trends(time_series)
            cycles = self._detect_cycles(time_series)

            # Create trend patterns
            for i, trend in enumerate(trends):
                pattern = Pattern(
                    id=f"temporal_trend_{int(time.time() * 1000)}_{i}",
                    type="temporal",
                    content={"type": "trend", "parameters": trend},
                    confidence=trend.get("confidence", 0.5),
                    support=trend.get("support", len(time_series)),
                    frequency=1.0,
                    complexity=1.0 * self.complexity_penalty,
                )
                patterns.append(pattern)

            # Create cycle patterns
            for i, cycle in enumerate(cycles):
                pattern = Pattern(
                    id=f"temporal_cycle_{int(time.time() * 1000)}_{i}",
                    type="temporal",
                    content={"type": "cycle", "parameters": cycle},
                    confidence=cycle.get("confidence", 0.5),
                    support=cycle.get("support", len(time_series)),
                    frequency=1.0,
                    complexity=2.0 * self.complexity_penalty,
                )
                patterns.append(pattern)

        return patterns

    def _mine_structural_patterns(self) -> List[Pattern]:
        """Mine structural patterns from relationships and hierarchies"""
        patterns = []

        # Analyze pattern hierarchy structure
        if self.pattern_hierarchy.relationships.number_of_nodes() > 3:
            # Find common structural motifs
            motifs = self._find_graph_motifs(self.pattern_hierarchy.relationships)

            for i, motif in enumerate(motifs):
                pattern = Pattern(
                    id=f"structural_{int(time.time() * 1000)}_{i}",
                    type="structural",
                    content=motif,
                    confidence=motif.get("confidence", 0.7),
                    support=motif.get("support", 1),
                    frequency=motif.get("frequency", 0.1),
                    complexity=motif.get("complexity", 3.0) * self.complexity_penalty,
                )
                patterns.append(pattern)

        return patterns

    def _mine_causal_patterns(self) -> List[Pattern]:
        """Mine causal patterns from causal buffer"""
        if len(self.causal_buffer) < 3:
            return []

        patterns = []
        causal_data = [item[0] for item in self.causal_buffer]

        # Look for cause-effect relationships
        causal_relationships = self._identify_causal_relationships(causal_data)

        for i, relationship in enumerate(causal_relationships):
            pattern = Pattern(
                id=f"causal_{int(time.time() * 1000)}_{i}",
                type="causal",
                content=relationship,
                confidence=relationship.get("confidence", 0.6),
                support=relationship.get("support", 1),
                frequency=relationship.get("frequency", 0.1),
                complexity=2.0 * self.complexity_penalty,
            )
            patterns.append(pattern)

        return patterns

    def _find_common_subsequences(self, sequences: List[List[float]]) -> List[Dict[str, Any]]:
        """Find common subsequences in numerical sequences"""
        common_subsequences = []

        if not sequences or len(sequences) < 2:
            return common_subsequences

        # Find subsequences of length 2-5
        for subseq_len in range(2, min(6, min(len(seq) for seq in sequences) + 1)):
            subsequence_counts = defaultdict(int)

            for seq in sequences:
                for i in range(len(seq) - subseq_len + 1):
                    subseq = tuple(seq[i : i + subseq_len])
                    subsequence_counts[subseq] += 1

            # Find frequent subsequences
            for subseq, count in subsequence_counts.items():
                if count >= self.min_support:
                    confidence = count / len(sequences)
                    if confidence >= self.min_confidence:
                        common_subsequences.append(
                            {
                                "sequence": list(subseq),
                                "support": count,
                                "confidence": confidence,
                                "frequency": count / sum(subsequence_counts.values()),
                            }
                        )

        return common_subsequences

    def _detect_trends(self, time_series: np.ndarray) -> List[Dict[str, Any]]:
        """Detect trend patterns in time series"""
        trends = []

        if len(time_series) < 5:
            return trends

        # Moving averages for different windows
        windows = [3, 5, 10]
        for window in windows:
            if len(time_series) >= window:
                moving_avg = np.convolve(time_series, np.ones(window) / window, mode="valid")

                # Detect trend direction
                diff = np.diff(moving_avg)

                # Count increasing vs decreasing segments
                increasing = np.sum(diff > 0)
                decreasing = np.sum(diff < 0)

                if increasing > decreasing * 1.5:
                    trends.append(
                        {
                            "type": "increasing",
                            "window": window,
                            "strength": increasing / len(diff),
                            "confidence": max(0.5, increasing / (increasing + decreasing)),
                            "support": len(moving_avg),
                        }
                    )
                elif decreasing > increasing * 1.5:
                    trends.append(
                        {
                            "type": "decreasing",
                            "window": window,
                            "strength": decreasing / len(diff),
                            "confidence": max(0.5, decreasing / (increasing + decreasing)),
                            "support": len(moving_avg),
                        }
                    )

        return trends

    def _detect_cycles(self, time_series: np.ndarray) -> List[Dict[str, Any]]:
        """Detect cyclical patterns in time series"""
        cycles = []

        if len(time_series) < 8:
            return cycles

        # Autocorrelation for cycle detection
        autocorr = np.correlate(time_series, time_series, mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]

        # Find peaks in autocorrelation (indicating periodicity)
        for i in range(2, min(len(autocorr), len(time_series) // 2)):
            if (
                i < len(autocorr) - 1
                and autocorr[i] > autocorr[i - 1]
                and autocorr[i] > autocorr[i + 1]
                and autocorr[i] > 0.3 * autocorr[0]
            ):  # Significant correlation

                cycles.append(
                    {
                        "period": i,
                        "strength": autocorr[i] / autocorr[0],
                        "confidence": min(1.0, autocorr[i] / autocorr[0]),
                        "support": len(time_series) // i,  # Number of complete cycles
                    }
                )

        return cycles

    def _find_graph_motifs(self, graph: nx.DiGraph) -> List[Dict[str, Any]]:
        """Find common structural motifs in graph"""
        motifs = []

        if graph.number_of_nodes() < 3:
            return motifs

        # Find triangles (3-node motifs)
        triangles = [
            triangle
            for triangle in nx.enumerate_all_cliques(graph.to_undirected())
            if len(triangle) == 3
        ]

        if len(triangles) >= 2:
            motifs.append(
                {
                    "type": "triangle",
                    "count": len(triangles),
                    "confidence": 0.7,
                    "support": len(triangles),
                    "frequency": len(triangles) / max(1, graph.number_of_nodes()),
                    "complexity": 3.0,
                }
            )

        # Find star patterns (hub nodes)
        degrees = dict(graph.degree())
        max_degree = max(degrees.values()) if degrees else 0

        if max_degree >= 3:
            hubs = [node for node, degree in degrees.items() if degree >= max_degree * 0.7]
            if hubs:
                motifs.append(
                    {
                        "type": "star",
                        "hubs": hubs,
                        "max_degree": max_degree,
                        "confidence": 0.8,
                        "support": len(hubs),
                        "frequency": len(hubs) / graph.number_of_nodes(),
                        "complexity": 2.0,
                    }
                )

        return motifs

    def _identify_causal_relationships(self, causal_data: List[Any]) -> List[Dict[str, Any]]:
        """Identify causal relationships in data"""
        relationships = []

        # Simple temporal causality detection
        for i in range(len(causal_data) - 1):
            cause = causal_data[i]
            effect = causal_data[i + 1]

            if isinstance(cause, dict) and isinstance(effect, dict):
                # Look for state changes that might indicate causality
                if "state" in cause and "state" in effect:
                    if cause["state"] != effect["state"]:
                        relationships.append(
                            {
                                "cause": cause,
                                "effect": effect,
                                "confidence": 0.6,
                                "support": 1,
                                "frequency": 1.0 / len(causal_data),
                                "type": "state_transition",
                            }
                        )

        return relationships

    def _validate_patterns(self, patterns: List[Pattern]) -> List[Pattern]:
        """Validate discovered patterns"""
        valid_patterns = []

        for pattern in patterns:
            # Check minimum support and confidence
            if pattern.support >= self.min_support and pattern.confidence >= self.min_confidence:

                # Check for duplicates
                is_duplicate = False
                for existing_id, existing_pattern in self.patterns.items():
                    if self._patterns_similar(pattern, existing_pattern):
                        is_duplicate = True
                        break

                if not is_duplicate:
                    valid_patterns.append(pattern)

        self.mining_stats["patterns_validated"] += len(valid_patterns)
        return valid_patterns

    def _patterns_similar(self, pattern1: Pattern, pattern2: Pattern) -> bool:
        """Check if two patterns are similar"""
        if pattern1.type != pattern2.type:
            return False

        # Content similarity check depends on pattern type
        if pattern1.type == "sequence":
            return self._sequence_similarity(pattern1.content, pattern2.content) > 0.8
        elif pattern1.type in ["spatial", "temporal"]:
            return self._numerical_similarity(pattern1.content, pattern2.content) > 0.8
        elif pattern1.type in ["structural", "causal"]:
            return self._structural_similarity(pattern1.content, pattern2.content) > 0.8

        return False

    def _sequence_similarity(self, seq1: List, seq2: List) -> float:
        """Compute similarity between sequences"""
        if not seq1 or not seq2:
            return 0.0

        # Simple Jaccard similarity
        set1, set2 = set(seq1), set(seq2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _numerical_similarity(self, data1: Any, data2: Any) -> float:
        """Compute similarity between numerical data"""
        try:
            arr1 = np.array(data1).flatten()
            arr2 = np.array(data2).flatten()

            if len(arr1) != len(arr2):
                return 0.0

            correlation = np.corrcoef(arr1, arr2)[0, 1]
            return abs(correlation) if not np.isnan(correlation) else 0.0

        except Exception:
            return 0.0

    def _structural_similarity(self, struct1: Any, struct2: Any) -> float:
        """Compute similarity between structural data"""
        if isinstance(struct1, dict) and isinstance(struct2, dict):
            common_keys = set(struct1.keys()) & set(struct2.keys())
            total_keys = set(struct1.keys()) | set(struct2.keys())

            return len(common_keys) / len(total_keys) if total_keys else 0.0

        return 0.0

    def _build_pattern_hierarchy(self):
        """Build hierarchical relationships between patterns"""
        # Clear existing hierarchy
        self.pattern_hierarchy.relationships.clear()

        # Add all patterns as nodes
        for pattern_id in self.patterns:
            self.pattern_hierarchy.relationships.add_node(pattern_id)

        # Find hierarchical relationships
        pattern_list = list(self.patterns.values())

        for i, pattern1 in enumerate(pattern_list):
            for pattern2 in pattern_list[i + 1 :]:
                # Check if one pattern is a sub-pattern of another
                relationship = self._compute_hierarchy_relationship(pattern1, pattern2)

                if relationship:
                    if relationship == "pattern1_sub":
                        self.pattern_hierarchy.relationships.add_edge(pattern2.id, pattern1.id)
                    elif relationship == "pattern2_sub":
                        self.pattern_hierarchy.relationships.add_edge(pattern1.id, pattern2.id)

    def _compute_hierarchy_relationship(
        self, pattern1: Pattern, pattern2: Pattern
    ) -> Optional[str]:
        """Compute hierarchical relationship between two patterns"""
        # Simple hierarchy based on complexity and support
        if pattern1.type == pattern2.type:
            if pattern1.complexity < pattern2.complexity and pattern1.support < pattern2.support:
                return "pattern1_sub"
            elif pattern2.complexity < pattern1.complexity and pattern2.support < pattern1.support:
                return "pattern2_sub"

        return None

    def _prune_patterns(self):
        """Prune old and weak patterns"""
        if len(self.patterns) <= self.max_patterns:
            return

        current_time = time.time()
        patterns_to_remove = []

        # Sort patterns by score (combination of confidence, support, and recency)
        pattern_scores = []

        for pattern_id, pattern in self.patterns.items():
            age = current_time - pattern.timestamp
            age_penalty = 1.0 / (1.0 + age / 3600)  # Decay over hours

            score = (pattern.confidence * pattern.support * age_penalty) - pattern.complexity
            pattern_scores.append((pattern_id, score))

        # Sort by score and remove lowest scoring patterns
        pattern_scores.sort(key=lambda x: x[1])

        num_to_remove = len(self.patterns) - self.max_patterns
        for i in range(num_to_remove):
            patterns_to_remove.append(pattern_scores[i][0])

        # Remove patterns
        for pattern_id in patterns_to_remove:
            del self.patterns[pattern_id]
            if self.pattern_hierarchy.relationships.has_node(pattern_id):
                self.pattern_hierarchy.relationships.remove_node(pattern_id)

        self.mining_stats["patterns_pruned"] += len(patterns_to_remove)

    def get_state(self) -> Dict[str, Any]:
        """Get current state of pattern mining engine"""
        return {
            "activation_level": self.activation_level,
            "num_patterns": len(self.patterns),
            "buffer_sizes": {
                "sequence": len(self.sequence_buffer),
                "spatial": len(self.spatial_buffer),
                "temporal": len(self.temporal_buffer),
                "causal": len(self.causal_buffer),
            },
            "mining_stats": self.mining_stats.copy(),
            "last_mining_time": self._last_mining_time,
            "hierarchy_stats": {
                "nodes": self.pattern_hierarchy.relationships.number_of_nodes(),
                "edges": self.pattern_hierarchy.relationships.number_of_edges(),
            },
        }

    def get_patterns_by_type(self, pattern_type: str) -> List[Pattern]:
        """Get patterns of a specific type"""
        return [p for p in self.patterns.values() if p.type == pattern_type]

    def get_top_patterns(self, n: int = 10) -> List[Pattern]:
        """Get top N patterns by score"""
        pattern_scores = []

        for pattern in self.patterns.values():
            score = pattern.confidence * pattern.support - pattern.complexity
            pattern_scores.append((pattern, score))

        pattern_scores.sort(key=lambda x: x[1], reverse=True)
        return [p[0] for p in pattern_scores[:n]]

    def receive_reasoning_feedback(self, feedback: Dict[str, Any]):
        """Receive feedback from reasoning engine"""
        self.reasoning_feedback.update(feedback)

        # Adjust mining based on feedback
        if "boost_types" in feedback:
            for pattern_type in feedback["boost_types"]:
                # Increase activation for specific pattern types
                relevant_patterns = self.get_patterns_by_type(pattern_type)
                for pattern in relevant_patterns:
                    pattern.confidence = min(1.0, pattern.confidence * 1.1)

    def send_patterns_to_reasoning(self, reasoning_engine) -> Dict[str, Any]:
        """Send patterns to reasoning engine"""
        top_patterns = self.get_top_patterns(20)

        return {
            "patterns": top_patterns,
            "pattern_hierarchy": self.pattern_hierarchy,
            "mining_confidence": self.activation_level,
            "timestamp": time.time(),
        }
