"""
PRIMUS Foundation - Core Theoretical Framework
==============================================

Implementation of Ben Goertzel's PRIMUS theory providing the foundational
principles for cognitive synergy in artificial general intelligence.

PRIMUS Principles:
- Pattern Recognition and Information Mining (PRIM)
- Understanding and Synthesis (US)
- Motivation and Goal-Oriented Behavior (MOT)
- Interaction and Communication (INT)
- Self-Organization and Adaptation (SOA)
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np


@dataclass
class PRIMUSState:
    """Represents the current state of the PRIMUS system"""

    pattern_space: Dict[str, Any] = field(default_factory=dict)
    understanding_level: float = 0.0
    motivation_vector: np.ndarray = field(default_factory=lambda: np.zeros(10))
    interaction_context: Dict[str, Any] = field(default_factory=dict)
    self_organization_metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class CognitivePrimitive:
    """Basic cognitive primitive in the PRIMUS framework"""

    name: str
    type: str  # 'pattern', 'concept', 'procedure', 'goal', etc.
    content: Any
    confidence: float = 1.0
    activation: float = 0.0
    connections: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PRIMUSFoundation:
    """
    Core implementation of PRIMUS theory for cognitive synergy.

    This class provides the fundamental mechanisms for:
    - Pattern recognition and information mining
    - Understanding and synthesis
    - Motivation and goal-oriented behavior
    - Interaction and communication
    - Self-organization and adaptation
    """

    def __init__(
        self,
        dimension: int = 512,
        learning_rate: float = 0.01,
        decay_rate: float = 0.99,
        synergy_threshold: float = 0.5,
    ):
        """
        Initialize PRIMUS foundation.

        Args:
            dimension: Dimensionality of cognitive representations
            learning_rate: Rate of adaptation and learning
            decay_rate: Memory decay rate
            synergy_threshold: Threshold for synergistic interactions
        """
        self.dimension = dimension
        self.learning_rate = learning_rate
        self.decay_rate = decay_rate
        self.synergy_threshold = synergy_threshold

        # Core PRIMUS components
        self.pattern_space = {}  # Pattern Recognition & Information Mining
        self.understanding_graph = nx.DiGraph()  # Understanding & Synthesis
        self.motivation_system = self._initialize_motivation_system()
        self.interaction_buffer = defaultdict(list)
        self.self_organization_state = {}

        # Cognitive primitives store
        self.primitives: Dict[str, CognitivePrimitive] = {}

        # State tracking
        self.current_state = PRIMUSState()
        self.state_history = []

        # Threading for continuous processes
        self._running = False
        self._threads = []

        # Logger
        self.logger = logging.getLogger(__name__)

    def _initialize_motivation_system(self) -> Dict[str, Any]:
        """Initialize the motivation system with core drives"""
        return {
            "curiosity": 0.8,
            "goal_achievement": 0.7,
            "pattern_completion": 0.6,
            "social_interaction": 0.5,
            "self_preservation": 0.9,
            "creativity": 0.6,
            "learning": 0.8,
            "efficiency": 0.5,
            "coherence": 0.7,
            "novelty_seeking": 0.6,
        }

    def start(self):
        """Start the PRIMUS system with continuous processing"""
        if self._running:
            return

        self._running = True

        # Start core processing threads
        self._threads = [
            threading.Thread(target=self._pattern_recognition_loop, daemon=True),
            threading.Thread(target=self._understanding_synthesis_loop, daemon=True),
            threading.Thread(target=self._motivation_update_loop, daemon=True),
            threading.Thread(target=self._self_organization_loop, daemon=True),
        ]

        for thread in self._threads:
            thread.start()

        self.logger.info("PRIMUS foundation started")

    def stop(self):
        """Stop the PRIMUS system"""
        self._running = False

        for thread in self._threads:
            if thread.is_alive():
                thread.join(timeout=1.0)

        self._threads.clear()
        self.logger.info("PRIMUS foundation stopped")

    def _pattern_recognition_loop(self):
        """Continuous pattern recognition and information mining"""
        while self._running:
            try:
                self._mine_patterns()
                self._update_pattern_space()
                time.sleep(0.1)  # 10Hz processing
            except Exception as e:
                self.logger.error(f"Pattern recognition error: {e}")

    def _understanding_synthesis_loop(self):
        """Continuous understanding and synthesis processing"""
        while self._running:
            try:
                self._synthesize_understanding()
                self._update_understanding_graph()
                time.sleep(0.2)  # 5Hz processing
            except Exception as e:
                self.logger.error(f"Understanding synthesis error: {e}")

    def _motivation_update_loop(self):
        """Continuous motivation system updates"""
        while self._running:
            try:
                self._update_motivations()
                self._generate_goals()
                time.sleep(0.5)  # 2Hz processing
            except Exception as e:
                self.logger.error(f"Motivation update error: {e}")

    def _self_organization_loop(self):
        """Continuous self-organization and adaptation"""
        while self._running:
            try:
                self._adapt_system()
                self._reorganize_structures()
                time.sleep(1.0)  # 1Hz processing
            except Exception as e:
                self.logger.error(f"Self-organization error: {e}")

    def add_primitive(self, primitive: CognitivePrimitive):
        """Add a cognitive primitive to the system"""
        self.primitives[primitive.name] = primitive

        # Update pattern space if it's a pattern
        if primitive.type == "pattern":
            self.pattern_space[primitive.name] = primitive.content

        # Add to understanding graph
        self.understanding_graph.add_node(primitive.name, **primitive.metadata)

        # Update connections
        for connection in primitive.connections:
            if connection in self.primitives:
                self.understanding_graph.add_edge(primitive.name, connection)

    def get_primitive(self, name: str) -> Optional[CognitivePrimitive]:
        """Retrieve a cognitive primitive by name"""
        return self.primitives.get(name)

    def compute_synergy(self, primitive1: str, primitive2: str) -> float:
        """
        Compute synergistic interaction between two primitives.

        Based on PRIMUS theory, synergy emerges from complementary
        cognitive processes working together.
        """
        p1 = self.primitives.get(primitive1)
        p2 = self.primitives.get(primitive2)

        if not p1 or not p2:
            return 0.0

        # Base synergy from activation correlation
        activation_synergy = np.corrcoef([p1.activation, p2.activation])[0, 1]
        if np.isnan(activation_synergy):
            activation_synergy = 0.0

        # Structural synergy from graph connectivity
        try:
            path_length = nx.shortest_path_length(self.understanding_graph, primitive1, primitive2)
            structural_synergy = 1.0 / (1.0 + path_length)
        except nx.NetworkXNoPath:
            structural_synergy = 0.0

        # Type compatibility synergy
        type_synergy = self._compute_type_synergy(p1.type, p2.type)

        # Content similarity synergy
        content_synergy = self._compute_content_synergy(p1.content, p2.content)

        # Weighted combination
        total_synergy = (
            0.3 * activation_synergy
            + 0.3 * structural_synergy
            + 0.2 * type_synergy
            + 0.2 * content_synergy
        )

        return max(0.0, min(1.0, total_synergy))

    def _compute_type_synergy(self, type1: str, type2: str) -> float:
        """Compute synergy based on primitive types"""
        synergy_matrix = {
            ("pattern", "concept"): 0.8,
            ("pattern", "procedure"): 0.6,
            ("concept", "goal"): 0.7,
            ("procedure", "goal"): 0.9,
            ("pattern", "pattern"): 0.5,
            ("concept", "concept"): 0.4,
            ("procedure", "procedure"): 0.3,
            ("goal", "goal"): 0.2,
        }

        return synergy_matrix.get((type1, type2), synergy_matrix.get((type2, type1), 0.1))

    def _compute_content_synergy(self, content1: Any, content2: Any) -> float:
        """Compute synergy based on content similarity"""
        try:
            # Convert to vectors if possible
            if hasattr(content1, "__array__") and hasattr(content2, "__array__"):
                c1 = np.array(content1).flatten()
                c2 = np.array(content2).flatten()

                # Ensure same length
                min_len = min(len(c1), len(c2))
                c1, c2 = c1[:min_len], c2[:min_len]

                if len(c1) > 0:
                    similarity = np.corrcoef(c1, c2)[0, 1]
                    return 0.0 if np.isnan(similarity) else abs(similarity)

            # String similarity
            if isinstance(content1, str) and isinstance(content2, str):
                common = set(content1.split()) & set(content2.split())
                total = set(content1.split()) | set(content2.split())
                return len(common) / len(total) if total else 0.0

            # Default case
            return 0.5 if content1 == content2 else 0.1

        except Exception:
            return 0.1

    def _mine_patterns(self):
        """Mine patterns from current system state"""
        # Extract patterns from primitive activations
        active_primitives = [
            name for name, prim in self.primitives.items() if prim.activation > 0.5
        ]

        if len(active_primitives) >= 2:
            # Find co-activation patterns
            for i, p1 in enumerate(active_primitives):
                for p2 in active_primitives[i + 1 :]:
                    synergy = self.compute_synergy(p1, p2)
                    if synergy > self.synergy_threshold:
                        pattern_name = f"synergy_{p1}_{p2}"
                        self.pattern_space[pattern_name] = {
                            "components": [p1, p2],
                            "synergy": synergy,
                            "timestamp": time.time(),
                        }

    def _update_pattern_space(self):
        """Update and maintain the pattern space"""
        current_time = time.time()

        # Decay old patterns
        to_remove = []
        for name, pattern in self.pattern_space.items():
            if "timestamp" in pattern:
                age = current_time - pattern["timestamp"]
                if age > 300:  # 5 minutes
                    to_remove.append(name)

        for name in to_remove:
            del self.pattern_space[name]

    def _synthesize_understanding(self):
        """Synthesize understanding from current patterns and primitives"""
        # Update understanding level based on pattern coherence
        coherence_scores = []

        for pattern in self.pattern_space.values():
            if isinstance(pattern, dict) and "synergy" in pattern:
                coherence_scores.append(pattern["synergy"])

        if coherence_scores:
            self.current_state.understanding_level = np.mean(coherence_scores)
        else:
            self.current_state.understanding_level *= self.decay_rate

    def _update_understanding_graph(self):
        """Update the understanding graph structure"""
        # Add edges for high-synergy primitive pairs
        for name, pattern in self.pattern_space.items():
            if (
                isinstance(pattern, dict)
                and "components" in pattern
                and "synergy" in pattern
                and pattern["synergy"] > self.synergy_threshold
            ):

                components = pattern["components"]
                if len(components) >= 2:
                    self.understanding_graph.add_edge(
                        components[0], components[1], weight=pattern["synergy"]
                    )

    def _update_motivations(self):
        """Update motivation system based on current state"""
        # Curiosity increases with new patterns
        new_patterns = sum(
            1
            for p in self.pattern_space.values()
            if isinstance(p, dict) and time.time() - p.get("timestamp", 0) < 10
        )

        self.motivation_system["curiosity"] = min(
            1.0, self.motivation_system["curiosity"] + 0.1 * new_patterns
        )

        # Learning motivation based on understanding level
        self.motivation_system["learning"] = 0.7 * self.motivation_system["learning"] + 0.3 * (
            1.0 - self.current_state.understanding_level
        )

        # Decay all motivations slightly
        for key in self.motivation_system:
            self.motivation_system[key] *= 0.999

    def _generate_goals(self):
        """Generate goals based on current motivations"""
        # Find highest motivation
        max_motivation = max(self.motivation_system.values())
        dominant_drive = max(self.motivation_system.items(), key=lambda x: x[1])[0]

        # Generate goal primitive if motivation is high enough
        if max_motivation > 0.7:
            goal_name = f"goal_{dominant_drive}_{int(time.time())}"
            goal_primitive = CognitivePrimitive(
                name=goal_name,
                type="goal",
                content={"drive": dominant_drive, "intensity": max_motivation},
                activation=max_motivation,
            )
            self.add_primitive(goal_primitive)

    def _adapt_system(self):
        """Adapt system parameters based on performance"""
        # Adapt synergy threshold based on pattern discovery rate
        pattern_rate = len(
            [
                p
                for p in self.pattern_space.values()
                if isinstance(p, dict) and time.time() - p.get("timestamp", 0) < 60
            ]
        )

        if pattern_rate > 10:  # Too many patterns
            self.synergy_threshold = min(1.0, self.synergy_threshold + 0.01)
        elif pattern_rate < 2:  # Too few patterns
            self.synergy_threshold = max(0.1, self.synergy_threshold - 0.01)

    def _reorganize_structures(self):
        """Reorganize internal structures for better efficiency"""
        # Prune low-activation primitives
        to_remove = []
        for name, prim in self.primitives.items():
            prim.activation *= self.decay_rate
            if prim.activation < 0.01:
                to_remove.append(name)

        for name in to_remove:
            del self.primitives[name]
            if self.understanding_graph.has_node(name):
                self.understanding_graph.remove_node(name)

    def get_system_state(self) -> PRIMUSState:
        """Get current system state"""
        self.current_state.pattern_space = dict(self.pattern_space)
        self.current_state.motivation_vector = np.array(list(self.motivation_system.values()))
        self.current_state.self_organization_metrics = {
            "primitives_count": len(self.primitives),
            "patterns_count": len(self.pattern_space),
            "graph_density": nx.density(self.understanding_graph),
            "synergy_threshold": self.synergy_threshold,
        }
        self.current_state.timestamp = time.time()

        return self.current_state

    def inject_stimulus(self, stimulus: Dict[str, Any]):
        """Inject external stimulus into the system"""
        stimulus_primitive = CognitivePrimitive(
            name=f"stimulus_{int(time.time() * 1000)}",
            type="stimulus",
            content=stimulus,
            activation=1.0,
            metadata={"external": True},
        )
        self.add_primitive(stimulus_primitive)

        # Boost related motivations
        if "type" in stimulus:
            if stimulus["type"] == "learning":
                self.motivation_system["learning"] = min(
                    1.0, self.motivation_system["learning"] + 0.2
                )
            elif stimulus["type"] == "social":
                self.motivation_system["social_interaction"] = min(
                    1.0, self.motivation_system["social_interaction"] + 0.2
                )

    def get_synergy_network(self) -> nx.Graph:
        """Get network representation of synergistic relationships"""
        synergy_graph = nx.Graph()

        primitive_names = list(self.primitives.keys())
        for i, p1 in enumerate(primitive_names):
            for p2 in primitive_names[i + 1 :]:
                synergy = self.compute_synergy(p1, p2)
                if synergy > self.synergy_threshold:
                    synergy_graph.add_edge(p1, p2, weight=synergy)

        return synergy_graph

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
