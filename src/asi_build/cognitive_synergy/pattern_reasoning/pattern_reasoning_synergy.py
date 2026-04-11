"""
Pattern Mining ↔ Reasoning Synergy Module
=========================================

Implements bidirectional information flow and synergistic integration between
pattern mining and reasoning processes. This module enables emergent cognitive
capabilities through their dynamic interaction.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .pattern_mining_engine import Pattern, PatternMiningEngine
from .reasoning_engine import Hypothesis, Inference, KnowledgeItem, ReasoningEngine


@dataclass
class SynergyMetrics:
    """Metrics for pattern-reasoning synergy"""

    bidirectional_flow_rate: float = 0.0
    pattern_to_reasoning_transfer: float = 0.0
    reasoning_to_pattern_transfer: float = 0.0
    synergy_strength: float = 0.0
    emergence_indicators: List[str] = field(default_factory=list)
    integration_level: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class SynergyEvent:
    """Represents a synergistic event between pattern mining and reasoning"""

    event_type: str  # 'pattern_guides_reasoning', 'reasoning_guides_patterns', 'mutual_enhancement'
    pattern_content: Any = None
    reasoning_content: Any = None
    synergy_strength: float = 0.0
    emergence_level: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatternReasoningSynergy:
    """
    Orchestrates synergistic interaction between pattern mining and reasoning.

    Key synergy mechanisms:
    1. Pattern-Guided Reasoning: Patterns inform hypothesis formation and inference
    2. Reasoning-Guided Pattern Mining: Logical structure guides pattern search
    3. Bidirectional Validation: Cross-validation between pattern evidence and logical inference
    4. Emergent Abstraction: Novel concepts emerge from pattern-reasoning integration
    5. Dynamic Attention: Mutual attention guidance between systems
    """

    def __init__(
        self,
        pattern_engine: Optional[PatternMiningEngine] = None,
        reasoning_engine: Optional[ReasoningEngine] = None,
        synergy_update_rate: float = 5.0,  # Hz
        integration_threshold: float = 0.7,
        emergence_threshold: float = 0.8,
    ):
        """
        Initialize pattern-reasoning synergy.

        Args:
            pattern_engine: Pattern mining engine instance
            reasoning_engine: Reasoning engine instance
            synergy_update_rate: Rate of synergy updates (Hz)
            integration_threshold: Threshold for integration events
            emergence_threshold: Threshold for emergence detection
        """
        self.pattern_engine = pattern_engine or PatternMiningEngine()
        self.reasoning_engine = reasoning_engine or ReasoningEngine()
        self.synergy_update_rate = synergy_update_rate
        self.integration_threshold = integration_threshold
        self.emergence_threshold = emergence_threshold

        # Synergy state
        self.metrics = SynergyMetrics()
        self.synergy_events: deque = deque(maxlen=1000)

        # Bidirectional communication buffers
        self.pattern_to_reasoning_buffer: deque = deque(maxlen=100)
        self.reasoning_to_pattern_buffer: deque = deque(maxlen=100)

        # Integration mechanisms
        self.abstraction_engine = AbstractionEngine()
        self.attention_coordinator = AttentionCoordinator()
        self.validation_engine = CrossValidationEngine()

        # Emergence tracking
        self.emergent_concepts = {}
        self.emergence_history = deque(maxlen=500)

        # Control and monitoring
        self._running = False
        self._synergy_thread = None
        self._lock = threading.RLock()

        # Performance metrics
        self.performance_history = defaultdict(list)

        # Logger
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the synergy orchestration"""
        if self._running:
            return

        self._running = True

        # Start synergy coordination thread
        self._synergy_thread = threading.Thread(target=self._synergy_loop, daemon=True)
        self._synergy_thread.start()

        self.logger.info("Pattern-Reasoning synergy started")

    def stop(self):
        """Stop the synergy orchestration"""
        self._running = False

        if self._synergy_thread and self._synergy_thread.is_alive():
            self._synergy_thread.join(timeout=2.0)

        self.logger.info("Pattern-Reasoning synergy stopped")

    def _synergy_loop(self):
        """Main synergy coordination loop"""
        sleep_time = 1.0 / self.synergy_update_rate

        while self._running:
            try:
                loop_start = time.time()

                # Core synergy processes
                self._coordinate_bidirectional_flow()
                self._perform_cross_validation()
                self._detect_emergent_abstractions()
                self._coordinate_attention()
                self._update_synergy_metrics()

                # Performance tracking
                loop_time = time.time() - loop_start
                self.performance_history["synergy_loop_time"].append(loop_time)

                # Sleep for remaining time
                remaining_time = max(0, sleep_time - loop_time)
                time.sleep(remaining_time)

            except Exception as e:
                self.logger.error(f"Synergy loop error: {e}")
                time.sleep(sleep_time)

    def _coordinate_bidirectional_flow(self):
        """Coordinate bidirectional information flow"""
        with self._lock:
            # Pattern → Reasoning flow
            self._pattern_to_reasoning_flow()

            # Reasoning → Pattern flow
            self._reasoning_to_pattern_flow()

            # Update flow metrics
            self._update_flow_metrics()

    def _pattern_to_reasoning_flow(self):
        """Flow information from pattern mining to reasoning"""
        # Get recent high-quality patterns
        top_patterns = self.pattern_engine.get_top_patterns(20)

        for pattern in top_patterns:
            if pattern.confidence > 0.7:
                # Convert pattern to reasoning knowledge
                self._convert_pattern_to_knowledge(pattern)

                # Guide hypothesis formation
                if pattern.type == "causal":
                    self._pattern_guided_hypothesis_formation(pattern)

                # Update buffer
                self.pattern_to_reasoning_buffer.append(
                    {"pattern": pattern, "timestamp": time.time(), "transferred": True}
                )

    def _reasoning_to_pattern_flow(self):
        """Flow information from reasoning to pattern mining"""
        # Get recent high-confidence inferences and hypotheses
        reasoning_state = self.reasoning_engine.get_state()

        # Send high-confidence inferences as pattern constraints
        high_conf_inferences = [
            inf
            for inf in self.reasoning_engine.inferences.values()
            if inf.confidence > 0.8 and time.time() - getattr(inf, "timestamp", 0) < 60
        ]

        for inference in high_conf_inferences:
            self._reasoning_guided_pattern_search(inference)

        # Send validated hypotheses as pattern targets
        confirmed_hypotheses = [
            hyp for hyp in self.reasoning_engine.hypotheses.values() if hyp.confidence > 0.8
        ]

        for hypothesis in confirmed_hypotheses:
            self._hypothesis_guided_pattern_mining(hypothesis)

            # Update buffer
            self.reasoning_to_pattern_buffer.append(
                {"hypothesis": hypothesis, "timestamp": time.time(), "transferred": True}
            )

    def _convert_pattern_to_knowledge(self, pattern: Pattern):
        """Convert pattern to reasoning knowledge"""
        # Create knowledge item from pattern
        knowledge_content = self._pattern_to_knowledge_content(pattern)

        self.reasoning_engine.add_knowledge(
            content=knowledge_content,
            knowledge_type="pattern_derived",
            confidence=pattern.confidence,
            source="pattern_mining",
        )

    def _pattern_to_knowledge_content(self, pattern: Pattern) -> str:
        """Convert pattern content to knowledge representation"""
        if pattern.type == "sequence":
            return f"Sequential pattern: {pattern.content}"
        elif pattern.type == "temporal":
            return f"Temporal pattern: {pattern.content}"
        elif pattern.type == "causal":
            return f"Causal pattern: {pattern.content}"
        elif pattern.type == "spatial":
            return f"Spatial pattern observed"
        elif pattern.type == "structural":
            return f"Structural pattern: {pattern.content}"
        else:
            return f"Pattern of type {pattern.type}: {pattern.content}"

    def _pattern_guided_hypothesis_formation(self, pattern: Pattern):
        """Use pattern to guide hypothesis formation"""
        if pattern.type == "causal" and isinstance(pattern.content, dict):
            # Extract causal relationships for hypothesis
            cause_effect = pattern.content
            if "cause" in cause_effect and "effect" in cause_effect:
                hypothesis_text = f"If {cause_effect['cause']}, then {cause_effect['effect']}"

                # Generate hypothesis
                self.reasoning_engine.generate_hypothesis(
                    observations=[hypothesis_text],
                    reasoning_type=self.reasoning_engine.reasoning_rules.get("ABDUCTIVE", [None])[
                        0
                    ],
                )

    def _reasoning_guided_pattern_search(self, inference: Inference):
        """Use reasoning inference to guide pattern search"""
        # Extract key terms from inference conclusion
        conclusion_terms = inference.conclusion.lower().split()

        # Create search input for pattern mining
        search_input = {
            "type": "reasoning_guided",
            "data": conclusion_terms,
            "timestamp": time.time(),
            "priority": inference.confidence,
        }

        self.pattern_engine.process_input(search_input)

    def _hypothesis_guided_pattern_mining(self, hypothesis: Hypothesis):
        """Use hypothesis to guide pattern mining"""
        # Extract observable predictions from hypothesis
        if hypothesis.predictions:
            for prediction in hypothesis.predictions:
                prediction_input = {
                    "type": "hypothesis_test",
                    "data": prediction,
                    "timestamp": time.time(),
                    "priority": hypothesis.confidence,
                }
                self.pattern_engine.process_input(prediction_input)

    def _update_flow_metrics(self):
        """Update bidirectional flow metrics"""
        # Pattern to reasoning transfer rate
        recent_p2r = len(
            [
                item
                for item in self.pattern_to_reasoning_buffer
                if time.time() - item["timestamp"] < 10
            ]
        )
        self.metrics.pattern_to_reasoning_transfer = recent_p2r / 10.0

        # Reasoning to pattern transfer rate
        recent_r2p = len(
            [
                item
                for item in self.reasoning_to_pattern_buffer
                if time.time() - item["timestamp"] < 10
            ]
        )
        self.metrics.reasoning_to_pattern_transfer = recent_r2p / 10.0

        # Total bidirectional flow
        self.metrics.bidirectional_flow_rate = (
            self.metrics.pattern_to_reasoning_transfer + self.metrics.reasoning_to_pattern_transfer
        )

    def _perform_cross_validation(self):
        """Perform cross-validation between pattern evidence and reasoning"""
        validation_results = self.validation_engine.validate(
            self.pattern_engine.patterns,
            self.reasoning_engine.inferences,
            self.reasoning_engine.hypotheses,
        )

        # Process validation results
        for result in validation_results:
            if result["validation_strength"] > self.integration_threshold:
                # Create synergy event
                event = SynergyEvent(
                    event_type="cross_validation",
                    pattern_content=result.get("pattern"),
                    reasoning_content=result.get("reasoning_element"),
                    synergy_strength=result["validation_strength"],
                    metadata=result,
                )
                self.synergy_events.append(event)

    def _detect_emergent_abstractions(self):
        """Detect emergent abstractions from pattern-reasoning integration"""
        abstractions = self.abstraction_engine.detect_abstractions(
            patterns=self.pattern_engine.patterns,
            knowledge_base=self.reasoning_engine.knowledge_base,
            synergy_events=list(self.synergy_events)[-50:],  # Recent events
        )

        for abstraction in abstractions:
            if abstraction["emergence_level"] > self.emergence_threshold:
                # Register emergent concept
                concept_id = f"emergent_{int(time.time() * 1000)}"
                self.emergent_concepts[concept_id] = abstraction

                # Add to emergence history
                self.emergence_history.append(
                    {"concept_id": concept_id, "abstraction": abstraction, "timestamp": time.time()}
                )

                # Create emergence event
                event = SynergyEvent(
                    event_type="emergent_abstraction",
                    emergence_level=abstraction["emergence_level"],
                    synergy_strength=abstraction.get("synergy_strength", 0.8),
                    metadata=abstraction,
                )
                self.synergy_events.append(event)

                # Inject emergent concept back into both systems
                self._inject_emergent_concept(concept_id, abstraction)

    def _inject_emergent_concept(self, concept_id: str, abstraction: Dict[str, Any]):
        """Inject emergent concept back into both systems"""
        # Add to reasoning system
        self.reasoning_engine.add_knowledge(
            content=abstraction["description"],
            knowledge_type="emergent_concept",
            confidence=abstraction["emergence_level"],
            source="synergy_emergence",
        )

        # Add to pattern mining system
        pattern_input = {
            "type": "emergent_concept",
            "data": abstraction["features"],
            "timestamp": time.time(),
            "priority": abstraction["emergence_level"],
        }
        self.pattern_engine.process_input(pattern_input)

    def _coordinate_attention(self):
        """Coordinate attention between pattern mining and reasoning"""
        attention_coordination = self.attention_coordinator.coordinate(
            pattern_engine_state=self.pattern_engine.get_state(),
            reasoning_engine_state=self.reasoning_engine.get_state(),
            synergy_metrics=self.metrics,
        )

        # Apply attention guidance
        if attention_coordination["focus_on_patterns"]:
            focus_types = attention_coordination["pattern_focus_types"]
            self._boost_pattern_attention(focus_types)

        if attention_coordination["focus_on_reasoning"]:
            reasoning_types = attention_coordination["reasoning_focus_types"]
            self._boost_reasoning_attention(reasoning_types)

    def _boost_pattern_attention(self, focus_types: List[str]):
        """Boost attention on specific pattern types"""
        # Send feedback to pattern engine
        feedback = {
            "boost_types": focus_types,
            "attention_boost": 1.5,
            "source": "synergy_coordination",
        }
        self.pattern_engine.receive_reasoning_feedback(feedback)

    def _boost_reasoning_attention(self, reasoning_types: List[str]):
        """Boost attention on specific reasoning types"""
        # Increase priority for specific reasoning types in agenda
        for reasoning_type in reasoning_types:
            self.reasoning_engine.reasoning_agenda.append(
                {"type": "attention_boost", "reasoning_type": reasoning_type, "priority": 0.9}
            )

    def _update_synergy_metrics(self):
        """Update comprehensive synergy metrics"""
        # Calculate synergy strength from recent events
        recent_events = [e for e in self.synergy_events if time.time() - e.timestamp < 30]

        if recent_events:
            avg_synergy = np.mean([e.synergy_strength for e in recent_events])
            self.metrics.synergy_strength = 0.8 * self.metrics.synergy_strength + 0.2 * avg_synergy
        else:
            self.metrics.synergy_strength *= 0.95  # Gradual decay

        # Calculate integration level
        pattern_state = self.pattern_engine.get_state()
        reasoning_state = self.reasoning_engine.get_state()

        # Integration based on activation correlation
        pattern_activation = pattern_state.get("activation_level", 0)
        reasoning_activation = reasoning_state.get("activation_level", 0)

        activation_correlation = np.corrcoef([pattern_activation, reasoning_activation])[0, 1]
        if np.isnan(activation_correlation):
            activation_correlation = 0.0

        self.metrics.integration_level = (
            0.4 * abs(activation_correlation)
            + 0.3 * self.metrics.bidirectional_flow_rate / 2.0  # Normalize flow rate
            + 0.3 * self.metrics.synergy_strength
        )

        # Update emergence indicators
        self.metrics.emergence_indicators = []
        if self.metrics.synergy_strength > 0.8:
            self.metrics.emergence_indicators.append("high_synergy")
        if self.metrics.integration_level > 0.8:
            self.metrics.emergence_indicators.append("high_integration")
        if self.metrics.bidirectional_flow_rate > 1.5:
            self.metrics.emergence_indicators.append("strong_bidirectional_flow")
        if len(self.emergent_concepts) > 0:
            self.metrics.emergence_indicators.append("emergent_concepts_present")

        self.metrics.last_updated = time.time()

        # Track performance history
        self.performance_history["synergy_strength"].append(self.metrics.synergy_strength)
        self.performance_history["integration_level"].append(self.metrics.integration_level)
        self.performance_history["bidirectional_flow"].append(self.metrics.bidirectional_flow_rate)

    def process_external_input(self, input_data: Dict[str, Any]):
        """Process external input through both systems synergistically"""
        # Send to both engines
        self.pattern_engine.process_input(input_data)

        # Convert input to knowledge for reasoning
        if "data" in input_data:
            self.reasoning_engine.add_knowledge(
                content=input_data["data"],
                knowledge_type=input_data.get("type", "external_input"),
                confidence=input_data.get("confidence", 0.8),
                source="external_input",
            )

        # Create synergy event
        event = SynergyEvent(
            event_type="external_input_processing",
            synergy_strength=0.6,  # Moderate synergy for external input
            metadata=input_data,
        )
        self.synergy_events.append(event)

    def get_synergy_state(self) -> Dict[str, Any]:
        """Get comprehensive synergy state"""
        return {
            "metrics": {
                "synergy_strength": self.metrics.synergy_strength,
                "integration_level": self.metrics.integration_level,
                "bidirectional_flow_rate": self.metrics.bidirectional_flow_rate,
                "pattern_to_reasoning_transfer": self.metrics.pattern_to_reasoning_transfer,
                "reasoning_to_pattern_transfer": self.metrics.reasoning_to_pattern_transfer,
                "emergence_indicators": self.metrics.emergence_indicators,
            },
            "recent_events": [
                {
                    "type": e.event_type,
                    "synergy_strength": e.synergy_strength,
                    "emergence_level": e.emergence_level,
                    "timestamp": e.timestamp,
                }
                for e in list(self.synergy_events)[-10:]
            ],
            "emergent_concepts": {
                concept_id: {
                    "description": concept["description"],
                    "emergence_level": concept["emergence_level"],
                    "features": concept.get("features", []),
                }
                for concept_id, concept in list(self.emergent_concepts.items())[-5:]
            },
            "pattern_engine_state": self.pattern_engine.get_state(),
            "reasoning_engine_state": self.reasoning_engine.get_state(),
            "performance_summary": {
                "avg_synergy_strength": (
                    np.mean(self.performance_history["synergy_strength"][-100:])
                    if self.performance_history["synergy_strength"]
                    else 0.0
                ),
                "avg_integration_level": (
                    np.mean(self.performance_history["integration_level"][-100:])
                    if self.performance_history["integration_level"]
                    else 0.0
                ),
                "total_emergent_concepts": len(self.emergent_concepts),
            },
        }

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


class AbstractionEngine:
    """Engine for detecting emergent abstractions"""

    def detect_abstractions(
        self,
        patterns: Dict[str, Pattern],
        knowledge_base: Dict[str, KnowledgeItem],
        synergy_events: List[SynergyEvent],
    ) -> List[Dict[str, Any]]:
        """Detect emergent abstractions from pattern-reasoning integration"""
        abstractions = []

        # Look for pattern-knowledge convergence
        for pattern_id, pattern in patterns.items():
            for knowledge_id, knowledge in knowledge_base.items():
                convergence = self._compute_convergence(pattern, knowledge)

                if convergence > 0.7:  # Strong convergence
                    abstraction = {
                        "description": f"Emergent concept bridging pattern '{pattern.content}' "
                        f"and knowledge '{knowledge.content}'",
                        "emergence_level": convergence,
                        "features": [pattern.content, knowledge.content],
                        "synergy_strength": convergence,
                        "pattern_id": pattern_id,
                        "knowledge_id": knowledge_id,
                    }
                    abstractions.append(abstraction)

        return abstractions

    def _compute_convergence(self, pattern: Pattern, knowledge: KnowledgeItem) -> float:
        """Compute convergence between pattern and knowledge"""
        # Simple content similarity
        pattern_content = str(pattern.content).lower()
        knowledge_content = str(knowledge.content).lower()

        pattern_words = set(pattern_content.split())
        knowledge_words = set(knowledge_content.split())

        if pattern_words and knowledge_words:
            intersection = len(pattern_words & knowledge_words)
            union = len(pattern_words | knowledge_words)
            similarity = intersection / union

            # Weight by confidence
            weighted_similarity = similarity * pattern.confidence * knowledge.confidence
            return min(1.0, weighted_similarity)

        return 0.0


class AttentionCoordinator:
    """Coordinates attention between pattern mining and reasoning"""

    def coordinate(
        self,
        pattern_engine_state: Dict[str, Any],
        reasoning_engine_state: Dict[str, Any],
        synergy_metrics: SynergyMetrics,
    ) -> Dict[str, Any]:
        """Coordinate attention between systems"""
        coordination = {
            "focus_on_patterns": False,
            "focus_on_reasoning": False,
            "pattern_focus_types": [],
            "reasoning_focus_types": [],
        }

        # Analyze system states
        pattern_activation = pattern_engine_state.get("activation_level", 0)
        reasoning_activation = reasoning_engine_state.get("activation_level", 0)

        # Balance attention based on activation levels
        if pattern_activation > reasoning_activation * 1.5:
            coordination["focus_on_reasoning"] = True
            coordination["reasoning_focus_types"] = ["inductive", "analogical"]
        elif reasoning_activation > pattern_activation * 1.5:
            coordination["focus_on_patterns"] = True
            coordination["pattern_focus_types"] = ["causal", "temporal"]

        # Focus on areas showing high synergy
        if synergy_metrics.synergy_strength > 0.7:
            coordination["focus_on_patterns"] = True
            coordination["focus_on_reasoning"] = True
            coordination["pattern_focus_types"] = ["structural", "causal"]
            coordination["reasoning_focus_types"] = ["abductive", "causal"]

        return coordination


class CrossValidationEngine:
    """Engine for cross-validating patterns and reasoning"""

    def validate(
        self,
        patterns: Dict[str, Pattern],
        inferences: Dict[str, Inference],
        hypotheses: Dict[str, Hypothesis],
    ) -> List[Dict[str, Any]]:
        """Cross-validate patterns against reasoning elements"""
        validation_results = []

        # Validate patterns against inferences
        for pattern_id, pattern in patterns.items():
            for inference_id, inference in inferences.items():
                validation_strength = self._validate_pattern_inference(pattern, inference)

                if validation_strength > 0.6:
                    validation_results.append(
                        {
                            "type": "pattern_inference_validation",
                            "pattern": pattern,
                            "reasoning_element": inference,
                            "validation_strength": validation_strength,
                        }
                    )

        # Validate patterns against hypotheses
        for pattern_id, pattern in patterns.items():
            for hypothesis_id, hypothesis in hypotheses.items():
                validation_strength = self._validate_pattern_hypothesis(pattern, hypothesis)

                if validation_strength > 0.6:
                    validation_results.append(
                        {
                            "type": "pattern_hypothesis_validation",
                            "pattern": pattern,
                            "reasoning_element": hypothesis,
                            "validation_strength": validation_strength,
                        }
                    )

        return validation_results

    def _validate_pattern_inference(self, pattern: Pattern, inference: Inference) -> float:
        """Validate pattern against inference"""
        pattern_content = str(pattern.content).lower()
        inference_content = inference.conclusion.lower()

        pattern_words = set(pattern_content.split())
        inference_words = set(inference_content.split())

        if pattern_words and inference_words:
            intersection = len(pattern_words & inference_words)
            union = len(pattern_words | inference_words)
            content_similarity = intersection / union

            # Weight by confidence
            confidence_factor = (pattern.confidence + inference.confidence) / 2

            return content_similarity * confidence_factor

        return 0.0

    def _validate_pattern_hypothesis(self, pattern: Pattern, hypothesis: Hypothesis) -> float:
        """Validate pattern against hypothesis"""
        pattern_content = str(pattern.content).lower()
        hypothesis_content = hypothesis.content.lower()

        pattern_words = set(pattern_content.split())
        hypothesis_words = set(hypothesis_content.split())

        if pattern_words and hypothesis_words:
            intersection = len(pattern_words & hypothesis_words)
            union = len(pattern_words | hypothesis_words)
            content_similarity = intersection / union

            # Weight by confidence
            confidence_factor = (pattern.confidence + hypothesis.confidence) / 2

            return content_similarity * confidence_factor

        return 0.0
