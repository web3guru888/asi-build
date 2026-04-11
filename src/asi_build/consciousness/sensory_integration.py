"""
Sensory Integration System

This module integrates sensory inputs from different modalities into
unified conscious perceptual experiences, handling cross-modal binding,
sensory fusion, and perceptual coherence.

Key components:
- Multi-modal sensory processing
- Cross-modal binding and synchronization
- Sensory fusion and integration
- Perceptual coherence maintenance
- Sensory attention allocation
- Perceptual consciousness emergence
"""

import math
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState


class SensoryModality(Enum):
    """Different sensory modalities"""

    VISUAL = "visual"
    AUDITORY = "auditory"
    TACTILE = "tactile"
    PROPRIOCEPTIVE = "proprioceptive"
    TEMPORAL = "temporal"
    COGNITIVE = "cognitive"
    SEMANTIC = "semantic"


@dataclass
class SensoryInput:
    """Represents input from a sensory modality"""

    input_id: str
    modality: SensoryModality
    data: Dict[str, Any]
    intensity: float
    timestamp: float
    spatial_location: Optional[Tuple[float, float, float]] = None
    confidence: float = 1.0
    processed: bool = False

    def get_feature_vector(self) -> np.ndarray:
        """Extract feature vector from sensory data"""
        features = []

        # Extract numerical features
        for key, value in self.data.items():
            if isinstance(value, (int, float)):
                features.append(value)
            elif isinstance(value, bool):
                features.append(1.0 if value else 0.0)

        # Add intensity and confidence
        features.extend([self.intensity, self.confidence])

        # Pad or truncate to standard size
        target_size = 16
        if len(features) < target_size:
            features.extend([0.0] * (target_size - len(features)))
        else:
            features = features[:target_size]

        return np.array(features)


@dataclass
class PerceptualBinding:
    """Represents binding between sensory inputs"""

    binding_id: str
    bound_inputs: Set[str]
    binding_strength: float
    binding_type: str  # 'spatial', 'temporal', 'semantic', 'causal'
    coherence_score: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class IntegratedPercept:
    """Represents a unified perceptual experience"""

    percept_id: str
    contributing_inputs: Set[str]
    dominant_modality: SensoryModality
    integrated_features: np.ndarray
    confidence: float
    coherence: float
    consciousness_level: float
    spatial_extent: Optional[Dict[str, float]] = None


class SensoryIntegration(BaseConsciousness):
    """
    Sensory Integration System

    Integrates sensory inputs from multiple modalities into unified
    conscious perceptual experiences with cross-modal binding.
    """

    def _initialize(self):
        """Initialize the SensoryIntegration consciousness model (called by BaseConsciousness)."""
        pass  # All initialization is done in __init__ after super().__init__()

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("SensoryIntegration", config)

        # Sensory input management
        self.sensory_inputs: Dict[str, SensoryInput] = {}
        self.inputs_by_modality: Dict[SensoryModality, Set[str]] = defaultdict(set)
        self.input_buffer: deque = deque(maxlen=200)

        # Perceptual binding
        self.perceptual_bindings: Dict[str, PerceptualBinding] = {}
        self.binding_history: deque = deque(maxlen=100)

        # Integrated percepts
        self.integrated_percepts: Dict[str, IntegratedPercept] = {}
        self.conscious_percepts: Set[str] = set()

        # Integration parameters
        self.binding_threshold = self.config.get("binding_threshold", 0.6)
        self.temporal_binding_window = self.config.get("temporal_window", 0.5)  # 500ms
        self.spatial_binding_radius = self.config.get("spatial_radius", 0.2)
        self.consciousness_threshold = self.config.get("consciousness_threshold", 0.7)

        # Attention and salience
        self.modality_attention: Dict[SensoryModality, float] = defaultdict(lambda: 1.0)
        self.spatial_attention_map = np.zeros((20, 20, 10))  # 3D attention map

        # Cross-modal learning
        self.cross_modal_associations: Dict[Tuple[SensoryModality, SensoryModality], float] = (
            defaultdict(float)
        )
        self.association_learning_rate = 0.1

        # Statistics
        self.total_inputs_processed = 0
        self.bindings_formed = 0
        self.conscious_percepts_formed = 0

        # Threading
        self.integration_lock = threading.Lock()

    def process_sensory_input(
        self,
        modality: SensoryModality,
        data: Dict[str, Any],
        intensity: float = 0.5,
        spatial_location: Optional[Tuple[float, float, float]] = None,
    ) -> SensoryInput:
        """Process new sensory input"""
        input_id = f"sensory_input_{self.total_inputs_processed:06d}"
        self.total_inputs_processed += 1

        sensory_input = SensoryInput(
            input_id=input_id,
            modality=modality,
            data=data,
            intensity=intensity,
            timestamp=time.time(),
            spatial_location=spatial_location,
            confidence=self._calculate_input_confidence(modality, data),
        )

        with self.integration_lock:
            self.sensory_inputs[input_id] = sensory_input
            self.inputs_by_modality[modality].add(input_id)
            self.input_buffer.append(input_id)

            # Attempt cross-modal binding
            self._attempt_cross_modal_binding(sensory_input)

            # Update spatial attention if location provided
            if spatial_location:
                self._update_spatial_attention(spatial_location, intensity)

        self.logger.debug(f"Processed {modality.value} input: {input_id}")
        return sensory_input

    def _calculate_input_confidence(self, modality: SensoryModality, data: Dict[str, Any]) -> float:
        """Calculate confidence level for sensory input"""
        base_confidence = 0.8

        # Modality-specific confidence adjustments
        modality_reliability = {
            SensoryModality.VISUAL: 0.9,
            SensoryModality.AUDITORY: 0.8,
            SensoryModality.TACTILE: 0.85,
            SensoryModality.PROPRIOCEPTIVE: 0.9,
            SensoryModality.TEMPORAL: 0.7,
            SensoryModality.COGNITIVE: 0.6,
            SensoryModality.SEMANTIC: 0.7,
        }

        base_confidence *= modality_reliability.get(modality, 0.7)

        # Data quality indicators
        if "noise_level" in data:
            noise_penalty = data["noise_level"] * 0.3
            base_confidence *= 1.0 - noise_penalty

        if "clarity" in data:
            base_confidence *= 0.5 + data["clarity"] * 0.5

        return max(0.1, min(1.0, base_confidence))

    def _attempt_cross_modal_binding(self, new_input: SensoryInput) -> None:
        """Attempt to bind new input with existing inputs"""
        current_time = time.time()

        # Find recent inputs from other modalities
        candidate_inputs = []
        for input_id in list(self.input_buffer)[-20:]:  # Last 20 inputs
            if input_id in self.sensory_inputs:
                candidate = self.sensory_inputs[input_id]

                # Skip same modality and old inputs
                if (
                    candidate.modality != new_input.modality
                    and current_time - candidate.timestamp <= self.temporal_binding_window
                ):
                    candidate_inputs.append(candidate)

        # Attempt binding with each candidate
        for candidate in candidate_inputs:
            binding_strength = self._calculate_binding_strength(new_input, candidate)

            if binding_strength > self.binding_threshold:
                self._create_perceptual_binding(
                    [new_input.input_id, candidate.input_id], binding_strength
                )

    def _calculate_binding_strength(self, input1: SensoryInput, input2: SensoryInput) -> float:
        """Calculate binding strength between two sensory inputs"""
        strength = 0.0

        # Temporal synchrony
        time_diff = abs(input1.timestamp - input2.timestamp)
        temporal_sync = max(0.0, 1.0 - time_diff / self.temporal_binding_window)
        strength += temporal_sync * 0.3

        # Spatial proximity (if both have spatial locations)
        if input1.spatial_location and input2.spatial_location:
            spatial_distance = math.sqrt(
                sum((a - b) ** 2 for a, b in zip(input1.spatial_location, input2.spatial_location))
            )
            spatial_proximity = max(0.0, 1.0 - spatial_distance / self.spatial_binding_radius)
            strength += spatial_proximity * 0.3

        # Feature similarity
        feature_similarity = self._calculate_feature_similarity(input1, input2)
        strength += feature_similarity * 0.2

        # Cross-modal association strength (learned)
        modality_pair = (input1.modality, input2.modality)
        reverse_pair = (input2.modality, input1.modality)
        association_strength = max(
            self.cross_modal_associations[modality_pair],
            self.cross_modal_associations[reverse_pair],
        )
        strength += association_strength * 0.2

        return min(1.0, strength)

    def _calculate_feature_similarity(self, input1: SensoryInput, input2: SensoryInput) -> float:
        """Calculate feature similarity between inputs"""
        try:
            features1 = input1.get_feature_vector()
            features2 = input2.get_feature_vector()

            # Normalize features
            norm1 = np.linalg.norm(features1)
            norm2 = np.linalg.norm(features2)

            if norm1 > 0 and norm2 > 0:
                normalized1 = features1 / norm1
                normalized2 = features2 / norm2

                # Cosine similarity
                similarity = np.dot(normalized1, normalized2)
                return max(0.0, similarity)

        except Exception as e:
            self.logger.debug(f"Feature similarity calculation failed: {e}")

        return 0.0

    def _create_perceptual_binding(
        self, input_ids: List[str], strength: float
    ) -> PerceptualBinding:
        """Create a new perceptual binding"""
        binding_id = f"binding_{self.bindings_formed:06d}"
        self.bindings_formed += 1

        # Determine binding type
        inputs = [self.sensory_inputs[iid] for iid in input_ids if iid in self.sensory_inputs]
        binding_type = self._determine_binding_type(inputs)

        # Calculate coherence
        coherence_score = self._calculate_binding_coherence(inputs)

        binding = PerceptualBinding(
            binding_id=binding_id,
            bound_inputs=set(input_ids),
            binding_strength=strength,
            binding_type=binding_type,
            coherence_score=coherence_score,
        )

        self.perceptual_bindings[binding_id] = binding
        self.binding_history.append(binding_id)

        # Update cross-modal associations (learning)
        if len(inputs) >= 2:
            for i, input1 in enumerate(inputs):
                for input2 in inputs[i + 1 :]:
                    modality_pair = (input1.modality, input2.modality)
                    current_association = self.cross_modal_associations[modality_pair]
                    self.cross_modal_associations[modality_pair] = (
                        current_association
                        + self.association_learning_rate * (strength - current_association)
                    )

        # Attempt to create integrated percept
        self._attempt_percept_integration(binding)

        self.logger.debug(f"Created perceptual binding: {binding_id} ({binding_type})")
        return binding

    def _determine_binding_type(self, inputs: List[SensoryInput]) -> str:
        """Determine the type of binding based on input characteristics"""
        # Temporal binding if inputs are temporally close
        if len(inputs) >= 2:
            time_diffs = [
                abs(inputs[i].timestamp - inputs[i + 1].timestamp) for i in range(len(inputs) - 1)
            ]
            if max(time_diffs) < 0.1:  # 100ms
                return "temporal"

        # Spatial binding if inputs have similar spatial locations
        spatial_inputs = [inp for inp in inputs if inp.spatial_location]
        if len(spatial_inputs) >= 2:
            distances = []
            for i, inp1 in enumerate(spatial_inputs):
                for inp2 in spatial_inputs[i + 1 :]:
                    distance = math.sqrt(
                        sum(
                            (a - b) ** 2
                            for a, b in zip(inp1.spatial_location, inp2.spatial_location)
                        )
                    )
                    distances.append(distance)

            if distances and max(distances) < self.spatial_binding_radius:
                return "spatial"

        # Semantic binding if inputs share semantic features
        semantic_overlap = self._check_semantic_overlap(inputs)
        if semantic_overlap > 0.5:
            return "semantic"

        # Default to causal binding
        return "causal"

    def _check_semantic_overlap(self, inputs: List[SensoryInput]) -> float:
        """Check semantic overlap between inputs"""
        if len(inputs) < 2:
            return 0.0

        # Simple semantic overlap based on common data keys
        all_keys = [set(inp.data.keys()) for inp in inputs]
        if len(all_keys) >= 2:
            intersection = set.intersection(*all_keys)
            union = set.union(*all_keys)

            if union:
                return len(intersection) / len(union)

        return 0.0

    def _calculate_binding_coherence(self, inputs: List[SensoryInput]) -> float:
        """Calculate coherence of a binding"""
        if not inputs:
            return 0.0

        coherence_factors = []

        # Temporal coherence
        timestamps = [inp.timestamp for inp in inputs]
        if len(timestamps) > 1:
            time_variance = np.var(timestamps)
            temporal_coherence = 1.0 / (1.0 + time_variance * 10)  # Scale variance
            coherence_factors.append(temporal_coherence)

        # Intensity coherence
        intensities = [inp.intensity for inp in inputs]
        if len(intensities) > 1:
            intensity_variance = np.var(intensities)
            intensity_coherence = 1.0 / (1.0 + intensity_variance)
            coherence_factors.append(intensity_coherence)

        # Confidence coherence
        confidences = [inp.confidence for inp in inputs]
        avg_confidence = np.mean(confidences)
        coherence_factors.append(avg_confidence)

        return np.mean(coherence_factors) if coherence_factors else 0.0

    def _attempt_percept_integration(self, binding: PerceptualBinding) -> None:
        """Attempt to create integrated percept from binding"""
        if binding.binding_strength < 0.7:
            return  # Not strong enough for integration

        inputs = [
            self.sensory_inputs[iid] for iid in binding.bound_inputs if iid in self.sensory_inputs
        ]

        if not inputs:
            return

        # Create integrated percept
        percept = self._create_integrated_percept(inputs, binding)

        # Check if percept reaches consciousness threshold
        if percept.consciousness_level > self.consciousness_threshold:
            self.conscious_percepts.add(percept.percept_id)
            self.conscious_percepts_formed += 1

            # Emit consciousness event
            self._emit_conscious_percept_event(percept)

    def _create_integrated_percept(
        self, inputs: List[SensoryInput], binding: PerceptualBinding
    ) -> IntegratedPercept:
        """Create an integrated percept from multiple inputs"""
        percept_id = f"percept_{len(self.integrated_percepts):06d}"

        # Determine dominant modality (highest intensity)
        dominant_input = max(inputs, key=lambda inp: inp.intensity)
        dominant_modality = dominant_input.modality

        # Integrate features
        feature_vectors = [inp.get_feature_vector() for inp in inputs]
        integrated_features = np.mean(feature_vectors, axis=0)

        # Calculate confidence and coherence
        confidences = [inp.confidence for inp in inputs]
        avg_confidence = np.mean(confidences)

        coherence = binding.coherence_score

        # Calculate consciousness level
        consciousness_level = self._calculate_consciousness_level(inputs, binding, coherence)

        # Calculate spatial extent if spatial inputs present
        spatial_extent = self._calculate_spatial_extent(inputs)

        percept = IntegratedPercept(
            percept_id=percept_id,
            contributing_inputs=set(inp.input_id for inp in inputs),
            dominant_modality=dominant_modality,
            integrated_features=integrated_features,
            confidence=avg_confidence,
            coherence=coherence,
            consciousness_level=consciousness_level,
            spatial_extent=spatial_extent,
        )

        self.integrated_percepts[percept_id] = percept
        return percept

    def _calculate_consciousness_level(
        self, inputs: List[SensoryInput], binding: PerceptualBinding, coherence: float
    ) -> float:
        """Calculate consciousness level of integrated percept"""
        factors = []

        # Binding strength contribution
        factors.append(binding.binding_strength * 0.3)

        # Coherence contribution
        factors.append(coherence * 0.3)

        # Multi-modal integration bonus
        modalities = set(inp.modality for inp in inputs)
        modality_bonus = min(0.3, len(modalities) * 0.1)
        factors.append(modality_bonus)

        # Attention weighting
        attention_weights = [self.modality_attention[inp.modality] for inp in inputs]
        avg_attention = np.mean(attention_weights)
        factors.append(avg_attention * 0.1)

        return sum(factors)

    def _calculate_spatial_extent(self, inputs: List[SensoryInput]) -> Optional[Dict[str, float]]:
        """Calculate spatial extent of integrated percept"""
        spatial_inputs = [inp for inp in inputs if inp.spatial_location]

        if not spatial_inputs:
            return None

        locations = np.array([inp.spatial_location for inp in spatial_inputs])

        return {
            "center": tuple(np.mean(locations, axis=0)),
            "extent": tuple(np.max(locations, axis=0) - np.min(locations, axis=0)),
            "volume": np.prod(np.max(locations, axis=0) - np.min(locations, axis=0)),
        }

    def _emit_conscious_percept_event(self, percept: IntegratedPercept) -> None:
        """Emit event for conscious percept formation"""
        consciousness_event = ConsciousnessEvent(
            event_id=f"conscious_percept_{percept.percept_id}",
            timestamp=time.time(),
            event_type="conscious_percept_formed",
            data={
                "percept_id": percept.percept_id,
                "dominant_modality": percept.dominant_modality.value,
                "contributing_modalities": [
                    self.sensory_inputs[iid].modality.value
                    for iid in percept.contributing_inputs
                    if iid in self.sensory_inputs
                ],
                "consciousness_level": percept.consciousness_level,
                "coherence": percept.coherence,
                "confidence": percept.confidence,
                "spatial_extent": percept.spatial_extent,
            },
            priority=9,
            source_module="sensory_integration",
            confidence=percept.consciousness_level,
        )

        self.emit_event(consciousness_event)

    def _update_spatial_attention(
        self, location: Tuple[float, float, float], intensity: float
    ) -> None:
        """Update spatial attention map"""
        x, y, z = location

        # Convert to map coordinates
        map_x = int(np.clip(x * 20, 0, 19))
        map_y = int(np.clip(y * 20, 0, 19))
        map_z = int(np.clip(z * 10, 0, 9))

        # Add attention with Gaussian spread
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                for dz in range(-1, 2):
                    nx, ny, nz = map_x + dx, map_y + dy, map_z + dz
                    if 0 <= nx < 20 and 0 <= ny < 20 and 0 <= nz < 10:
                        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
                        attention_value = intensity * math.exp(-(distance**2) / 2.0)
                        self.spatial_attention_map[nx, ny, nz] += attention_value

    def set_modality_attention(self, modality: SensoryModality, attention_level: float) -> None:
        """Set attention level for a specific modality"""
        self.modality_attention[modality] = max(0.0, min(2.0, attention_level))

    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "sensory_input":
            modality_str = event.data.get("modality", "cognitive")
            data = event.data.get("data", {})
            intensity = event.data.get("intensity", 0.5)
            spatial_location = event.data.get("spatial_location")

            try:
                modality = SensoryModality(modality_str)
                sensory_input = self.process_sensory_input(
                    modality, data, intensity, spatial_location
                )

                return ConsciousnessEvent(
                    event_id=f"sensory_processed_{sensory_input.input_id}",
                    timestamp=time.time(),
                    event_type="sensory_input_processed",
                    data={
                        "input_id": sensory_input.input_id,
                        "modality": modality.value,
                        "confidence": sensory_input.confidence,
                    },
                    source_module="sensory_integration",
                )
            except ValueError:
                self.logger.error(f"Invalid sensory modality: {modality_str}")

        elif event.event_type == "attention_modulation":
            modality_str = event.data.get("modality")
            attention_level = event.data.get("attention_level", 1.0)

            try:
                modality = SensoryModality(modality_str)
                self.set_modality_attention(modality, attention_level)
            except ValueError:
                self.logger.error(f"Invalid modality for attention: {modality_str}")

        return None

    def update(self) -> None:
        """Update the Sensory Integration system"""
        current_time = time.time()

        # Decay spatial attention map
        self.spatial_attention_map *= 0.95

        # Clean up old inputs
        old_input_ids = [
            iid
            for iid, inp in self.sensory_inputs.items()
            if current_time - inp.timestamp > 300  # 5 minutes
        ]

        for input_id in old_input_ids:
            if input_id in self.sensory_inputs:
                modality = self.sensory_inputs[input_id].modality
                self.inputs_by_modality[modality].discard(input_id)
                del self.sensory_inputs[input_id]

        # Clean up old bindings
        old_binding_ids = [
            bid
            for bid, binding in self.perceptual_bindings.items()
            if current_time - binding.timestamp > 600  # 10 minutes
        ]

        for binding_id in old_binding_ids:
            del self.perceptual_bindings[binding_id]

        # Update consciousness metrics
        if self.integrated_percepts:
            conscious_ratio = len(self.conscious_percepts) / len(self.integrated_percepts)
            self.metrics.awareness_level = conscious_ratio

        if self.sensory_inputs:
            modalities_active = len(set(inp.modality for inp in self.sensory_inputs.values()))
            max_modalities = len(SensoryModality)
            self.metrics.integration_level = modalities_active / max_modalities

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Sensory Integration system"""
        modality_counts = {}
        for modality in SensoryModality:
            modality_counts[modality.value] = len(self.inputs_by_modality[modality])

        return {
            "total_sensory_inputs": len(self.sensory_inputs),
            "inputs_by_modality": modality_counts,
            "perceptual_bindings": len(self.perceptual_bindings),
            "integrated_percepts": len(self.integrated_percepts),
            "conscious_percepts": len(self.conscious_percepts),
            "modality_attention": {mod.value: att for mod, att in self.modality_attention.items()},
            "cross_modal_associations": len(self.cross_modal_associations),
            "total_inputs_processed": self.total_inputs_processed,
            "bindings_formed": self.bindings_formed,
            "conscious_percepts_formed": self.conscious_percepts_formed,
            "spatial_attention_peak": float(np.max(self.spatial_attention_map)),
        }
