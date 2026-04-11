"""
Higher-Order Thought (HOT) Theory Implementation
===============================================

Implementation of David Rosenthal's Higher-Order Thought Theory for measuring
consciousness through hierarchical metacognitive representations.

Key concepts:
- First-Order States: Basic mental states (perceptions, thoughts)
- Higher-Order Thoughts: Thoughts about first-order mental states
- Consciousness Threshold: When HOTs represent first-order states
- Introspective Consciousness: Awareness of one's own mental states
- Transitivity: HOTs can be directed at other HOTs

Based on Rosenthal's HOT theory of consciousness.
"""

import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import networkx as nx
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.decomposition import PCA


@dataclass(eq=False)
class MentalState:
    """Representation of a mental state at any order.

    Note: eq=False because ``content`` is a torch.Tensor — element-wise
    comparison cannot be reduced to a single bool, which breaks ``in``
    checks and ``==`` when used in lists.  Identity comparison (``is``)
    is the correct semantics for MentalState objects.
    """

    content: torch.Tensor
    order: int  # 0 = sensory, 1 = first-order thought, 2+ = higher-order thoughts
    confidence: float
    temporal_persistence: float
    referential_target: Optional["MentalState"] = None


@dataclass
class HOTStructure:
    """Complete Higher-Order Thought structure."""

    first_order_states: List[MentalState]
    higher_order_thoughts: List[MentalState]
    consciousness_candidates: List[MentalState]
    max_order: int
    introspective_depth: int
    transitivity_chains: List[List[MentalState]]


@dataclass
class ConsciousnessMetrics:
    """HOT-based consciousness measurements."""

    hot_complexity: float
    introspective_depth: float
    transitivity_score: float
    metacognitive_richness: float
    consciousness_candidates_ratio: float
    hierarchical_integration: float


class HOTTheoryImplementation:
    """
    Higher-Order Thought Theory implementation for consciousness assessment.

    Measures consciousness through hierarchical metacognitive thought structures
    and higher-order representations of mental states.
    """

    def __init__(self, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        """
        Initialize HOT Theory implementation.

        Args:
            device: Computing device for tensor operations
        """
        self.device = device
        self.logger = logging.getLogger(__name__)

        # HOT parameters
        self.max_order = 4  # Maximum order of thoughts to consider
        self.consciousness_threshold = 0.6  # Threshold for consciousness attribution
        self.temporal_window = 10  # Number of timesteps to maintain state history
        self.content_dimensions = 128  # Dimensionality of mental state content

        # Initialize HOT neural networks
        self._initialize_hot_networks()

        # Mental state history
        self.state_history: deque = deque(maxlen=self.temporal_window)

    def _initialize_hot_networks(self):
        """Initialize Higher-Order Thought neural networks."""
        # First-order thought generator
        self.first_order_generator = nn.Sequential(
            nn.Linear(512, 256),  # Input will be adapted dynamically
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, self.content_dimensions),
            nn.Tanh(),
        ).to(self.device)

        # Higher-order thought generators (one for each order)
        self.higher_order_generators = nn.ModuleList()
        for order in range(2, self.max_order + 1):
            generator = nn.Sequential(
                nn.Linear(self.content_dimensions * order, 256),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.Linear(128, self.content_dimensions),
                nn.Tanh(),
            )
            self.higher_order_generators.append(generator)

        # Consciousness attribution network
        self.consciousness_attributor = nn.Sequential(
            nn.Linear(self.content_dimensions * 2, 128),  # State + HOT
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        ).to(self.device)

        # Introspective monitoring network
        self.introspective_monitor = nn.Sequential(
            nn.Linear(self.content_dimensions, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 3),  # [confidence, persistence, order_prediction]
            nn.Sigmoid(),
        ).to(self.device)

        # Referential targeting network
        self.referential_targeter = nn.Sequential(
            nn.Linear(self.content_dimensions * 2, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        ).to(self.device)

        self.logger.info("Higher-Order Thought Theory networks initialized")

    def assess_higher_order_thoughts(
        self, neural_activations: torch.Tensor, behavioral_data: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Assess higher-order thought complexity and consciousness.

        Args:
            neural_activations: Neural network activations [batch, time, neurons]
            behavioral_data: Optional behavioral and response data

        Returns:
            Higher-order thought complexity score (0-1)
        """
        self.logger.info("Assessing Higher-Order Thought complexity")

        try:
            # Ensure proper tensor format
            if neural_activations.dim() == 2:
                neural_activations = neural_activations.unsqueeze(0)

            activations = neural_activations.to(self.device)

            # Adapt network input size if needed
            input_size = activations.shape[-1]
            self._adapt_network_sizes(input_size)

            # Process temporal sequence
            hot_structures = []
            consciousness_metrics_sequence = []

            for t in range(activations.shape[1]):
                timestep_activations = activations[:, t, :]  # [batch, neurons]

                # Generate HOT structure for this timestep
                hot_structure = self._generate_hot_structure(timestep_activations, behavioral_data)
                hot_structures.append(hot_structure)

                # Measure consciousness metrics
                metrics = self._compute_consciousness_metrics(hot_structure)
                consciousness_metrics_sequence.append(metrics)

                # Update state history
                self.state_history.append(hot_structure)

            # Aggregate HOT complexity across time
            complexity_scores = [m.hot_complexity for m in consciousness_metrics_sequence]
            overall_complexity = np.mean(complexity_scores) if complexity_scores else 0.0

            # Additional temporal integration
            temporal_integration = self._compute_temporal_hot_integration(hot_structures)

            # Final complexity score
            final_complexity = 0.7 * overall_complexity + 0.3 * temporal_integration

            self.logger.info(f"HOT complexity score: {final_complexity:.3f}")
            return float(final_complexity)

        except Exception as e:
            self.logger.error(f"Higher-order thought assessment failed: {e}")
            return 0.0

    def _adapt_network_sizes(self, input_size: int):
        """Adapt network input sizes to match neural activations."""
        if hasattr(self.first_order_generator[0], "in_features"):
            if self.first_order_generator[0].in_features != input_size:
                self.first_order_generator[0] = nn.Linear(input_size, 256).to(self.device)
                nn.init.xavier_uniform_(self.first_order_generator[0].weight)

    def _generate_hot_structure(
        self, activations: torch.Tensor, behavioral_data: Optional[Dict[str, Any]] = None
    ) -> HOTStructure:
        """
        Generate complete Higher-Order Thought structure from activations.

        Args:
            activations: Neural activations [batch, neurons]
            behavioral_data: Optional behavioral context

        Returns:
            Complete HOT structure
        """
        batch_size = activations.shape[0]

        # 1. Generate first-order thoughts from neural activations
        first_order_content = self.first_order_generator(activations)  # [batch, content_dims]

        # Create first-order mental states
        first_order_states = []
        for b in range(batch_size):
            fo_content = first_order_content[b]
            introspective_outputs = self.introspective_monitor(fo_content)

            confidence = introspective_outputs[0].item()
            persistence = introspective_outputs[1].item()

            first_order_state = MentalState(
                content=fo_content,
                order=1,
                confidence=confidence,
                temporal_persistence=persistence,
                referential_target=None,
            )
            first_order_states.append(first_order_state)

        # 2. Generate higher-order thoughts
        higher_order_thoughts = []
        current_states = first_order_states.copy()
        max_achieved_order = 1

        for order in range(2, self.max_order + 1):
            if not current_states:
                break

            next_order_states = []
            generator_idx = order - 2  # Index into higher_order_generators

            if generator_idx >= len(self.higher_order_generators):
                break

            generator = self.higher_order_generators[generator_idx]

            # Generate higher-order thoughts about current states
            for i, target_state in enumerate(current_states):
                # Create input for HOT generation
                if order == 2:
                    hot_input = torch.cat(
                        [
                            target_state.content,
                            target_state.content,  # Self-reference for second-order
                        ],
                        dim=0,
                    )
                else:
                    # For higher orders, combine with previous HOT
                    if higher_order_thoughts:
                        recent_hot = higher_order_thoughts[-1].content
                        hot_input = torch.cat(
                            [target_state.content, recent_hot]
                            + [target_state.content] * (order - 2),
                            dim=0,
                        )
                    else:
                        continue

                # Ensure input size matches generator expectations
                expected_size = self.content_dimensions * order
                if len(hot_input) != expected_size:
                    hot_input = hot_input[:expected_size]
                    if len(hot_input) < expected_size:
                        hot_input = F.pad(hot_input, (0, expected_size - len(hot_input)))

                # Generate higher-order thought
                try:
                    hot_content = generator(hot_input.unsqueeze(0)).squeeze(0)

                    # Introspective monitoring
                    introspective_outputs = self.introspective_monitor(hot_content)

                    confidence = introspective_outputs[0].item()
                    persistence = introspective_outputs[1].item()

                    # Check if this HOT is strong enough
                    if confidence > 0.3:
                        hot_state = MentalState(
                            content=hot_content,
                            order=order,
                            confidence=confidence,
                            temporal_persistence=persistence,
                            referential_target=target_state,
                        )
                        next_order_states.append(hot_state)
                        higher_order_thoughts.append(hot_state)
                        max_achieved_order = order

                except Exception as e:
                    self.logger.warning(f"HOT generation failed for order {order}: {e}")
                    continue

            current_states = next_order_states

        # 3. Identify consciousness candidates
        consciousness_candidates = self._identify_consciousness_candidates(
            first_order_states, higher_order_thoughts
        )

        # 4. Analyze transitivity chains
        transitivity_chains = self._analyze_transitivity_chains(higher_order_thoughts)

        # 5. Compute introspective depth
        introspective_depth = self._compute_introspective_depth(higher_order_thoughts)

        return HOTStructure(
            first_order_states=first_order_states,
            higher_order_thoughts=higher_order_thoughts,
            consciousness_candidates=consciousness_candidates,
            max_order=max_achieved_order,
            introspective_depth=introspective_depth,
            transitivity_chains=transitivity_chains,
        )

    def _identify_consciousness_candidates(
        self, first_order_states: List[MentalState], higher_order_thoughts: List[MentalState]
    ) -> List[MentalState]:
        """
        Identify which mental states qualify as conscious according to HOT theory.

        Args:
            first_order_states: List of first-order mental states
            higher_order_thoughts: List of higher-order thoughts

        Returns:
            List of states that qualify as conscious
        """
        consciousness_candidates = []

        # A state is conscious if there's a HOT directed at it with sufficient strength
        for fo_state in first_order_states:
            directed_hots = [
                hot for hot in higher_order_thoughts if hot.referential_target == fo_state
            ]

            if directed_hots:
                # Find strongest HOT directed at this state
                strongest_hot = max(directed_hots, key=lambda h: h.confidence)

                # Check consciousness threshold
                consciousness_score = self._compute_consciousness_attribution(
                    fo_state, strongest_hot
                )

                if consciousness_score > self.consciousness_threshold:
                    consciousness_candidates.append(fo_state)

        return consciousness_candidates

    def _compute_consciousness_attribution(
        self, target_state: MentalState, hot_state: MentalState
    ) -> float:
        """
        Compute consciousness attribution score for a state-HOT pair.

        Args:
            target_state: The mental state potentially conscious
            hot_state: The higher-order thought about the state

        Returns:
            Consciousness attribution score (0-1)
        """
        try:
            # Combine target and HOT representations
            combined_input = torch.cat([target_state.content, hot_state.content], dim=0)

            # Predict consciousness attribution
            consciousness_score = (
                self.consciousness_attributor(combined_input.unsqueeze(0)).squeeze(0).item()
            )

            # Weight by HOT confidence and target persistence
            weighted_score = (
                consciousness_score * hot_state.confidence * target_state.temporal_persistence
            )

            return weighted_score

        except Exception as e:
            self.logger.warning(f"Consciousness attribution computation failed: {e}")
            return 0.0

    def _analyze_transitivity_chains(
        self, higher_order_thoughts: List[MentalState]
    ) -> List[List[MentalState]]:
        """
        Analyze transitivity chains in higher-order thoughts.

        Transitivity occurs when HOTs are directed at other HOTs.
        """
        chains = []

        # Build referential graph
        hot_graph = nx.DiGraph()

        for hot in higher_order_thoughts:
            hot_graph.add_node(id(hot), state=hot)

            if hot.referential_target and hot.referential_target in higher_order_thoughts:
                hot_graph.add_edge(id(hot.referential_target), id(hot))

        # Find chains (paths in the graph)
        try:
            for node in hot_graph.nodes():
                # Find all paths starting from this node
                for target in hot_graph.nodes():
                    if node != target:
                        try:
                            paths = list(nx.all_simple_paths(hot_graph, node, target))
                            for path in paths:
                                if len(path) > 2:  # At least 3 nodes for meaningful chain
                                    chain_states = [
                                        hot_graph.nodes[node_id]["state"] for node_id in path
                                    ]
                                    chains.append(chain_states)
                        except nx.NetworkXNoPath:
                            continue

        except Exception as e:
            self.logger.warning(f"Transitivity chain analysis failed: {e}")

        return chains

    def _compute_introspective_depth(self, higher_order_thoughts: List[MentalState]) -> int:
        """Compute the depth of introspective access."""
        if not higher_order_thoughts:
            return 0

        # Find the deepest introspective chain
        max_depth = 0

        def find_depth(state: MentalState, current_depth: int = 0) -> int:
            if state.referential_target is None:
                return current_depth

            # Check if target is also a HOT (introspective access)
            if state.referential_target.order > 1:
                return find_depth(state.referential_target, current_depth + 1)
            else:
                return current_depth

        for hot in higher_order_thoughts:
            depth = find_depth(hot)
            max_depth = max(max_depth, depth)

        return max_depth

    def _compute_consciousness_metrics(self, hot_structure: HOTStructure) -> ConsciousnessMetrics:
        """
        Compute comprehensive consciousness metrics from HOT structure.

        Args:
            hot_structure: Complete HOT structure

        Returns:
            Consciousness metrics based on HOT theory
        """
        # 1. HOT Complexity
        hot_complexity = self._compute_hot_complexity(hot_structure)

        # 2. Introspective Depth
        introspective_depth_norm = hot_structure.introspective_depth / self.max_order

        # 3. Transitivity Score
        transitivity_score = self._compute_transitivity_score(hot_structure.transitivity_chains)

        # 4. Metacognitive Richness
        metacognitive_richness = self._compute_metacognitive_richness(hot_structure)

        # 5. Consciousness Candidates Ratio
        if hot_structure.first_order_states:
            consciousness_ratio = len(hot_structure.consciousness_candidates) / len(
                hot_structure.first_order_states
            )
        else:
            consciousness_ratio = 0.0

        # 6. Hierarchical Integration
        hierarchical_integration = self._compute_hierarchical_integration(hot_structure)

        return ConsciousnessMetrics(
            hot_complexity=hot_complexity,
            introspective_depth=introspective_depth_norm,
            transitivity_score=transitivity_score,
            metacognitive_richness=metacognitive_richness,
            consciousness_candidates_ratio=consciousness_ratio,
            hierarchical_integration=hierarchical_integration,
        )

    def _compute_hot_complexity(self, hot_structure: HOTStructure) -> float:
        """Compute overall complexity of HOT structure."""
        complexity_factors = []

        # Number of higher-order thoughts
        hot_count_factor = min(len(hot_structure.higher_order_thoughts) / 10.0, 1.0)
        complexity_factors.append(hot_count_factor)

        # Order diversity
        if hot_structure.higher_order_thoughts:
            orders = [hot.order for hot in hot_structure.higher_order_thoughts]
            order_diversity = len(set(orders)) / self.max_order
            complexity_factors.append(order_diversity)
        else:
            complexity_factors.append(0.0)

        # Confidence distribution
        if hot_structure.higher_order_thoughts:
            confidences = [hot.confidence for hot in hot_structure.higher_order_thoughts]
            confidence_mean = np.mean(confidences)
            confidence_std = np.std(confidences)
            confidence_complexity = confidence_mean * (1.0 + confidence_std)
            complexity_factors.append(min(confidence_complexity, 1.0))
        else:
            complexity_factors.append(0.0)

        # Referential complexity
        referential_density = self._compute_referential_density(hot_structure)
        complexity_factors.append(referential_density)

        # Weighted average
        weights = [0.3, 0.25, 0.25, 0.2]
        total_complexity = sum(w * f for w, f in zip(weights, complexity_factors))

        return total_complexity

    def _compute_referential_density(self, hot_structure: HOTStructure) -> float:
        """Compute density of referential relationships."""
        all_states = hot_structure.first_order_states + hot_structure.higher_order_thoughts

        if len(all_states) < 2:
            return 0.0

        # Count referential relationships
        referential_links = 0
        for hot in hot_structure.higher_order_thoughts:
            if hot.referential_target is not None:
                referential_links += 1

        # Maximum possible links
        max_links = len(hot_structure.higher_order_thoughts)

        if max_links > 0:
            density = referential_links / max_links
        else:
            density = 0.0

        return density

    def _compute_transitivity_score(self, transitivity_chains: List[List[MentalState]]) -> float:
        """Compute transitivity score from chains."""
        if not transitivity_chains:
            return 0.0

        # Score based on number and length of chains
        chain_scores = []

        for chain in transitivity_chains:
            # Longer chains indicate deeper transitivity
            length_score = min(len(chain) / self.max_order, 1.0)

            # Confidence along the chain
            confidences = [state.confidence for state in chain]
            confidence_score = np.mean(confidences)

            chain_score = 0.6 * length_score + 0.4 * confidence_score
            chain_scores.append(chain_score)

        # Average chain quality
        transitivity_score = np.mean(chain_scores)

        return transitivity_score

    def _compute_metacognitive_richness(self, hot_structure: HOTStructure) -> float:
        """Compute richness of metacognitive representations."""
        if not hot_structure.higher_order_thoughts:
            return 0.0

        # Representational diversity
        hot_contents = torch.stack([hot.content for hot in hot_structure.higher_order_thoughts])

        try:
            # Use PCA to measure representational dimensionality
            pca = PCA(n_components=min(len(hot_structure.higher_order_thoughts), 10))
            pca.fit(hot_contents.detach().cpu().numpy())

            # Explained variance as richness measure
            explained_variance_ratio = np.sum(pca.explained_variance_ratio_)
            dimensionality_richness = min(explained_variance_ratio, 1.0)

        except Exception as e:
            self.logger.warning(f"PCA analysis failed: {e}")
            # Fallback: use variance across dimensions
            dimensionality_richness = torch.mean(torch.var(hot_contents, dim=0)).item()
            dimensionality_richness = min(dimensionality_richness, 1.0)

        # Metacognitive sophistication (higher orders = more sophisticated)
        order_sophistication = hot_structure.max_order / self.max_order

        # Confidence calibration
        confidences = [hot.confidence for hot in hot_structure.higher_order_thoughts]
        confidence_calibration = 1.0 - np.std(confidences)  # More consistent = better calibrated

        # Combined richness
        metacognitive_richness = (
            0.5 * dimensionality_richness
            + 0.3 * order_sophistication
            + 0.2 * confidence_calibration
        )

        return metacognitive_richness

    def _compute_hierarchical_integration(self, hot_structure: HOTStructure) -> float:
        """Compute integration across hierarchical levels."""
        if hot_structure.max_order <= 1:
            return 0.0

        # Measure integration between adjacent orders
        integration_scores = []

        for order in range(1, hot_structure.max_order):
            current_order_states = [
                state
                for state in hot_structure.first_order_states + hot_structure.higher_order_thoughts
                if state.order == order
            ]
            next_order_states = [
                state for state in hot_structure.higher_order_thoughts if state.order == order + 1
            ]

            if current_order_states and next_order_states:
                # Measure representational similarity between orders
                current_contents = torch.stack([state.content for state in current_order_states])
                next_contents = torch.stack([state.content for state in next_order_states])

                # Average content similarity
                current_mean = torch.mean(current_contents, dim=0)
                next_mean = torch.mean(next_contents, dim=0)

                similarity = F.cosine_similarity(
                    current_mean.unsqueeze(0), next_mean.unsqueeze(0), dim=1
                ).item()

                integration_scores.append(max(0.0, (similarity + 1.0) / 2.0))

        if integration_scores:
            return np.mean(integration_scores)
        else:
            return 0.0

    def _compute_temporal_hot_integration(self, hot_structures: List[HOTStructure]) -> float:
        """Compute integration of HOT structures across time."""
        if len(hot_structures) < 2:
            return 0.0

        temporal_consistencies = []

        for i in range(len(hot_structures) - 1):
            current_structure = hot_structures[i]
            next_structure = hot_structures[i + 1]

            # Compare consciousness candidates consistency
            current_conscious = len(current_structure.consciousness_candidates)
            next_conscious = len(next_structure.consciousness_candidates)

            if current_conscious + next_conscious > 0:
                consciousness_consistency = (
                    2
                    * min(current_conscious, next_conscious)
                    / (current_conscious + next_conscious)
                )
            else:
                consciousness_consistency = 1.0

            # Compare HOT complexity consistency
            current_complexity = self._compute_hot_complexity(current_structure)
            next_complexity = self._compute_hot_complexity(next_structure)

            complexity_consistency = 1.0 - abs(current_complexity - next_complexity)

            # Combined temporal consistency
            temporal_consistency = 0.6 * consciousness_consistency + 0.4 * complexity_consistency
            temporal_consistencies.append(temporal_consistency)

        return np.mean(temporal_consistencies) if temporal_consistencies else 0.0

    def analyze_hot_dynamics(self, activations_sequence: List[torch.Tensor]) -> Dict[str, float]:
        """
        Analyze Higher-Order Thought dynamics over time.

        Args:
            activations_sequence: Sequence of neural activations

        Returns:
            Dictionary with HOT dynamics analysis
        """
        hot_complexities = []
        consciousness_ratios = []
        introspective_depths = []

        for activations in activations_sequence:
            complexity = self.assess_higher_order_thoughts(activations)
            hot_complexities.append(complexity)

            # Extract additional metrics from latest structure
            if self.state_history:
                latest_structure = self.state_history[-1]

                if latest_structure.first_order_states:
                    ratio = len(latest_structure.consciousness_candidates) / len(
                        latest_structure.first_order_states
                    )
                    consciousness_ratios.append(ratio)

                introspective_depths.append(latest_structure.introspective_depth)

        complexity_array = np.array(hot_complexities)

        dynamics = {
            "mean_hot_complexity": float(np.mean(complexity_array)),
            "complexity_stability": float(1.0 / (1.0 + np.std(complexity_array))),
            "complexity_trend": (
                float(np.polyfit(range(len(hot_complexities)), hot_complexities, 1)[0])
                if len(hot_complexities) > 1
                else 0.0
            ),
        }

        if consciousness_ratios:
            dynamics["mean_consciousness_ratio"] = float(np.mean(consciousness_ratios))
            dynamics["consciousness_consistency"] = float(1.0 - np.std(consciousness_ratios))

        if introspective_depths:
            dynamics["mean_introspective_depth"] = float(np.mean(introspective_depths))
            dynamics["depth_progression"] = (
                float(np.mean(np.diff(introspective_depths)))
                if len(introspective_depths) > 1
                else 0.0
            )

        return dynamics
