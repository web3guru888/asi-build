"""
Qualia Processor

This module implements a system for representing and processing qualia - the
subjective, experiential qualities of conscious states (what it's like to
experience something).

Key components:
- Qualia representation structures
- Phenomenal binding mechanisms
- Subjective experience modeling
- Quality space mapping
- Experience comparison and similarity
- Phenomenal concepts
"""

import math
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
from scipy.spatial.distance import cosine, euclidean

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState


class QualiaType(Enum):
    """Types of qualia that can be experienced"""

    VISUAL = "visual"
    AUDITORY = "auditory"
    TACTILE = "tactile"
    EMOTIONAL = "emotional"
    COGNITIVE = "cognitive"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    AESTHETIC = "aesthetic"
    SEMANTIC = "semantic"
    INTENTIONAL = "intentional"


class QualiaIntensity(Enum):
    """Intensity levels of qualia"""

    SUBTLE = 0.2
    MILD = 0.4
    MODERATE = 0.6
    STRONG = 0.8
    INTENSE = 1.0


@dataclass
class QualiaVector:
    """Multi-dimensional representation of a quale"""

    dimensions: np.ndarray  # N-dimensional vector
    dimension_names: List[str]
    intensity: float
    clarity: float
    stability: float

    def similarity_to(self, other: "QualiaVector") -> float:
        """Calculate similarity to another qualia vector"""
        if len(self.dimensions) != len(other.dimensions):
            return 0.0
        return 1.0 - cosine(self.dimensions, other.dimensions)

    def distance_from(self, other: "QualiaVector") -> float:
        """Calculate distance from another qualia vector"""
        if len(self.dimensions) != len(other.dimensions):
            return float("inf")
        return euclidean(self.dimensions, other.dimensions)


@dataclass
class Quale:
    """Represents a single qualitative experience"""

    quale_id: str
    qualia_type: QualiaType
    vector: QualiaVector
    associated_content: Dict[str, Any]
    duration: float
    onset_time: float
    phenomenal_properties: Dict[str, float]
    binding_strength: float = 1.0
    access_consciousness: bool = True  # Whether it's accessible to cognitive processes

    def get_phenomenal_character(self) -> str:
        """Describe the phenomenal character of this quale"""
        properties_desc = []
        for prop, value in self.phenomenal_properties.items():
            if value > 0.5:
                properties_desc.append(f"{prop}({value:.2f})")

        return f"{self.qualia_type.value} quale with {', '.join(properties_desc)}"

    def is_similar_to(self, other: "Quale", threshold: float = 0.7) -> bool:
        """Check if this quale is similar to another"""
        return (
            self.qualia_type == other.qualia_type
            and self.vector.similarity_to(other.vector) > threshold
        )


@dataclass
class QualiaBinding:
    """Represents the binding of multiple qualia into unified experience"""

    binding_id: str
    bound_qualia: List[str]  # quale IDs
    binding_strength: float
    binding_type: str  # 'temporal', 'spatial', 'semantic', 'causal'
    unified_experience: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def get_binding_quality(self) -> float:
        """Calculate overall binding quality"""
        return self.binding_strength * len(self.bound_qualia) / 10.0


@dataclass
class PhenomenalConcept:
    """Represents a phenomenal concept - a concept involving qualia"""

    concept_id: str
    name: str
    prototype_qualia: List[QualiaVector]
    typical_properties: Dict[str, float]
    recognition_threshold: float = 0.6
    usage_count: int = 0

    def matches_experience(self, quale: Quale) -> bool:
        """Check if a quale matches this phenomenal concept"""
        for prototype in self.prototype_qualia:
            if quale.vector.similarity_to(prototype) > self.recognition_threshold:
                return True
        return False


class QualiaProcessor(BaseConsciousness):
    """
    Implementation of Qualia Processing System

    Processes and represents the qualitative, subjective aspects of experience.
    Creates structured representations of what experiences are like.
    """

    def _initialize(self):
        """Initialize the QualiaProcessor consciousness model (called by BaseConsciousness)."""
        pass  # All initialization is done in __init__ after super().__init__()

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("QualiaProcessor", config)

        # Core qualia structures
        self.active_qualia: Dict[str, Quale] = {}
        self.qualia_history: deque = deque(maxlen=1000)
        self.qualia_bindings: Dict[str, QualiaBinding] = {}
        self.phenomenal_concepts: Dict[str, PhenomenalConcept] = {}

        # Quality spaces for different types of qualia
        self.quality_spaces: Dict[QualiaType, np.ndarray] = {}
        self.quality_space_dimensions = self.config.get("quality_space_dims", 16)

        # Binding mechanisms
        self.binding_threshold = self.config.get("binding_threshold", 0.5)
        self.temporal_binding_window = self.config.get("temporal_window", 1.0)
        self.spatial_binding_radius = self.config.get("spatial_radius", 0.3)

        # Experience tracking
        self.current_unified_experience: Optional[str] = None
        self.experience_stream: deque = deque(maxlen=100)
        self.phenomenal_field: Dict[str, Quale] = {}  # Currently active phenomenal field

        # Subjective measures
        self.current_experiential_intensity = 0.0
        self.experiential_complexity = 0.0
        self.phenomenal_richness = 0.0

        # Learning and adaptation
        self.qualia_recognition_accuracy = 0.5
        self.concept_formation_threshold = self.config.get("concept_threshold", 3)

        # Statistics
        self.total_qualia_processed = 0
        self.binding_events = 0
        self.concept_formations = 0

        # Threading
        self.qualia_lock = threading.Lock()

        # Initialize quality spaces and concepts
        self._initialize_quality_spaces()
        self._initialize_phenomenal_concepts()

    def _initialize_quality_spaces(self):
        """Initialize quality spaces for different types of qualia"""
        # Each qualia type has its own dimensional space
        for qualia_type in QualiaType:
            # Create a structured quality space
            space_size = self.quality_space_dimensions
            quality_space = np.random.normal(0, 0.5, (space_size, space_size))
            self.quality_spaces[qualia_type] = quality_space

        self.logger.info(f"Initialized quality spaces for {len(QualiaType)} qualia types")

    def _initialize_phenomenal_concepts(self):
        """Initialize basic phenomenal concepts"""
        # Visual concepts
        red_prototype = QualiaVector(
            dimensions=np.array([0.8, 0.2, 0.1, 0.0, 0.9, 0.7, 0.3, 0.8] + [0.0] * 8),
            dimension_names=[
                "hue",
                "saturation",
                "brightness",
                "warmth",
                "vividness",
                "intensity",
                "purity",
                "arousal",
            ]
            + [f"dim_{i}" for i in range(8)],
            intensity=0.8,
            clarity=0.9,
            stability=0.8,
        )

        red_concept = PhenomenalConcept(
            concept_id="red_experience",
            name="Redness",
            prototype_qualia=[red_prototype],
            typical_properties={"warmth": 0.8, "vividness": 0.9, "arousal": 0.7},
        )
        self.phenomenal_concepts["red_experience"] = red_concept

        # Emotional concepts
        joy_prototype = QualiaVector(
            dimensions=np.array([0.9, 0.8, 0.2, 0.9, 0.7, 0.8, 0.1, 0.6] + [0.0] * 8),
            dimension_names=[
                "valence",
                "arousal",
                "tension",
                "energy",
                "lightness",
                "expansion",
                "warmth",
                "flow",
            ]
            + [f"dim_{i}" for i in range(8)],
            intensity=0.8,
            clarity=0.7,
            stability=0.6,
        )

        joy_concept = PhenomenalConcept(
            concept_id="joy_experience",
            name="Joy",
            prototype_qualia=[joy_prototype],
            typical_properties={"valence": 0.9, "energy": 0.8, "lightness": 0.7},
        )
        self.phenomenal_concepts["joy_experience"] = joy_concept

        # Cognitive concepts
        understanding_prototype = QualiaVector(
            dimensions=np.array([0.7, 0.6, 0.8, 0.5, 0.9, 0.4, 0.7, 0.8] + [0.0] * 8),
            dimension_names=[
                "clarity",
                "coherence",
                "insight",
                "confidence",
                "integration",
                "surprise",
                "satisfaction",
                "depth",
            ]
            + [f"dim_{i}" for i in range(8)],
            intensity=0.7,
            clarity=0.8,
            stability=0.9,
        )

        understanding_concept = PhenomenalConcept(
            concept_id="understanding_experience",
            name="Understanding",
            prototype_qualia=[understanding_prototype],
            typical_properties={"clarity": 0.8, "integration": 0.9, "satisfaction": 0.7},
        )
        self.phenomenal_concepts["understanding_experience"] = understanding_concept

        self.logger.info(f"Initialized {len(self.phenomenal_concepts)} phenomenal concepts")

    def create_quale(
        self,
        qualia_type: QualiaType,
        stimulus_data: Dict[str, Any],
        phenomenal_properties: Optional[Dict[str, float]] = None,
    ) -> Quale:
        """Create a new quale from stimulus data"""
        quale_id = f"quale_{self.total_qualia_processed:06d}"
        self.total_qualia_processed += 1

        # Generate qualia vector from stimulus
        vector = self._stimulus_to_qualia_vector(qualia_type, stimulus_data)

        # Set default phenomenal properties if not provided
        if phenomenal_properties is None:
            phenomenal_properties = self._infer_phenomenal_properties(qualia_type, stimulus_data)

        # Calculate duration and onset
        duration = stimulus_data.get("duration", 1.0)
        onset_time = time.time()

        # Determine access consciousness based on intensity and attention
        intensity = vector.intensity
        access_consciousness = intensity > 0.3  # Threshold for access

        quale = Quale(
            quale_id=quale_id,
            qualia_type=qualia_type,
            vector=vector,
            associated_content=stimulus_data.copy(),
            duration=duration,
            onset_time=onset_time,
            phenomenal_properties=phenomenal_properties,
            access_consciousness=access_consciousness,
        )

        # Add to active qualia
        with self.qualia_lock:
            self.active_qualia[quale_id] = quale
            self.phenomenal_field[quale_id] = quale

        # Attempt binding with other active qualia
        self._attempt_binding(quale)

        # Check for concept matching
        self._check_concept_matching(quale)

        self.logger.debug(f"Created {qualia_type.value} quale: {quale_id}")
        return quale

    def _stimulus_to_qualia_vector(
        self, qualia_type: QualiaType, stimulus_data: Dict[str, Any]
    ) -> QualiaVector:
        """Convert stimulus data to qualia vector"""
        # Get quality space for this type
        quality_space = self.quality_spaces[qualia_type]

        # Extract relevant features from stimulus
        features = self._extract_stimulus_features(stimulus_data, qualia_type)

        # Map features to quality space dimensions
        dimensions = np.zeros(self.quality_space_dimensions)

        for i, feature_value in enumerate(features[: self.quality_space_dimensions]):
            dimensions[i] = feature_value

        # Calculate intensity, clarity, stability
        intensity = stimulus_data.get("intensity", 0.5)
        clarity = stimulus_data.get("clarity", 0.7)
        stability = stimulus_data.get("stability", 0.6)

        # Generate dimension names
        dim_names = [f"{qualia_type.value}_dim_{i}" for i in range(self.quality_space_dimensions)]

        return QualiaVector(
            dimensions=dimensions,
            dimension_names=dim_names,
            intensity=intensity,
            clarity=clarity,
            stability=stability,
        )

    def _extract_stimulus_features(
        self, stimulus_data: Dict[str, Any], qualia_type: QualiaType
    ) -> List[float]:
        """Extract numerical features from stimulus data"""
        features = []

        if qualia_type == QualiaType.VISUAL:
            # Visual features
            features.extend(
                [
                    stimulus_data.get("brightness", 0.5),
                    stimulus_data.get("contrast", 0.5),
                    stimulus_data.get("saturation", 0.5),
                    stimulus_data.get("hue", 0.5),
                    stimulus_data.get("sharpness", 0.5),
                    stimulus_data.get("motion", 0.0),
                    stimulus_data.get("depth", 0.5),
                    stimulus_data.get("complexity", 0.5),
                ]
            )

        elif qualia_type == QualiaType.EMOTIONAL:
            # Emotional features
            features.extend(
                [
                    stimulus_data.get("valence", 0.5),
                    stimulus_data.get("arousal", 0.5),
                    stimulus_data.get("dominance", 0.5),
                    stimulus_data.get("intensity", 0.5),
                    stimulus_data.get("urgency", 0.0),
                    stimulus_data.get("familiarity", 0.5),
                    stimulus_data.get("predictability", 0.5),
                    stimulus_data.get("control", 0.5),
                ]
            )

        elif qualia_type == QualiaType.COGNITIVE:
            # Cognitive features
            features.extend(
                [
                    stimulus_data.get("complexity", 0.5),
                    stimulus_data.get("coherence", 0.5),
                    stimulus_data.get("novelty", 0.5),
                    stimulus_data.get("relevance", 0.5),
                    stimulus_data.get("confidence", 0.5),
                    stimulus_data.get("effort", 0.5),
                    stimulus_data.get("progress", 0.5),
                    stimulus_data.get("understanding", 0.5),
                ]
            )

        else:
            # Default features
            features.extend(
                [
                    stimulus_data.get("intensity", 0.5),
                    stimulus_data.get("quality", 0.5),
                    stimulus_data.get("duration", 0.5),
                    stimulus_data.get("location", 0.5),
                ]
            )

        # Pad or truncate to desired length
        while len(features) < self.quality_space_dimensions:
            features.append(0.0)

        return features[: self.quality_space_dimensions]

    def _infer_phenomenal_properties(
        self, qualia_type: QualiaType, stimulus_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Infer phenomenal properties from stimulus data"""
        properties = {}

        # Universal properties
        properties["vividness"] = stimulus_data.get("intensity", 0.5)
        properties["clarity"] = stimulus_data.get("clarity", 0.7)
        properties["richness"] = stimulus_data.get("complexity", 0.5)

        # Type-specific properties
        if qualia_type == QualiaType.VISUAL:
            properties["brightness"] = stimulus_data.get("brightness", 0.5)
            properties["colorfulness"] = stimulus_data.get("saturation", 0.5)
            properties["spatial_extent"] = stimulus_data.get("size", 0.5)

        elif qualia_type == QualiaType.EMOTIONAL:
            properties["pleasantness"] = stimulus_data.get("valence", 0.5)
            properties["energy"] = stimulus_data.get("arousal", 0.5)
            properties["warmth"] = max(0, properties["pleasantness"] - 0.2)

        elif qualia_type == QualiaType.COGNITIVE:
            properties["insight"] = stimulus_data.get("understanding", 0.5)
            properties["certainty"] = stimulus_data.get("confidence", 0.5)
            properties["flow"] = 1.0 - stimulus_data.get("effort", 0.5)

        return properties

    def _attempt_binding(self, new_quale: Quale) -> None:
        """Attempt to bind new quale with existing active qualia"""
        binding_candidates = []

        # Find binding candidates
        for quale_id, existing_quale in self.active_qualia.items():
            if quale_id != new_quale.quale_id:
                binding_strength = self._calculate_binding_strength(new_quale, existing_quale)

                if binding_strength > self.binding_threshold:
                    binding_candidates.append((quale_id, binding_strength))

        # Create bindings if candidates found
        if binding_candidates:
            # Sort by binding strength
            binding_candidates.sort(key=lambda x: x[1], reverse=True)

            # Create binding with strongest candidates
            bound_qualia = [new_quale.quale_id]
            total_strength = 0.0

            for candidate_id, strength in binding_candidates[:3]:  # Max 3 bindings
                bound_qualia.append(candidate_id)
                total_strength += strength

            if len(bound_qualia) > 1:
                binding_id = f"binding_{self.binding_events:06d}"
                self.binding_events += 1

                binding = QualiaBinding(
                    binding_id=binding_id,
                    bound_qualia=bound_qualia,
                    binding_strength=total_strength / len(bound_qualia),
                    binding_type=self._determine_binding_type(new_quale, bound_qualia),
                    unified_experience=self._generate_unified_experience_description(bound_qualia),
                )

                self.qualia_bindings[binding_id] = binding
                self.logger.debug(f"Created binding: {binding_id} with {len(bound_qualia)} qualia")

    def _calculate_binding_strength(self, quale1: Quale, quale2: Quale) -> float:
        """Calculate binding strength between two qualia"""
        strength = 0.0

        # Temporal proximity
        time_diff = abs(quale1.onset_time - quale2.onset_time)
        if time_diff <= self.temporal_binding_window:
            temporal_strength = 1.0 - (time_diff / self.temporal_binding_window)
            strength += temporal_strength * 0.3

        # Vector similarity
        vector_similarity = quale1.vector.similarity_to(quale2.vector)
        strength += vector_similarity * 0.3

        # Phenomenal property similarity
        property_similarity = self._calculate_property_similarity(
            quale1.phenomenal_properties, quale2.phenomenal_properties
        )
        strength += property_similarity * 0.2

        # Type compatibility
        if quale1.qualia_type == quale2.qualia_type:
            strength += 0.2

        return min(1.0, strength)

    def _calculate_property_similarity(
        self, props1: Dict[str, float], props2: Dict[str, float]
    ) -> float:
        """Calculate similarity between phenomenal properties"""
        common_props = set(props1.keys()) & set(props2.keys())

        if not common_props:
            return 0.0

        similarity_sum = 0.0
        for prop in common_props:
            diff = abs(props1[prop] - props2[prop])
            similarity_sum += 1.0 - diff

        return similarity_sum / len(common_props)

    def _determine_binding_type(self, new_quale: Quale, bound_qualia: List[str]) -> str:
        """Determine the type of binding"""
        # Simple heuristic based on timing and type
        time_diffs = []
        types = [new_quale.qualia_type]

        for quale_id in bound_qualia[1:]:  # Skip the new quale itself
            if quale_id in self.active_qualia:
                existing_quale = self.active_qualia[quale_id]
                time_diffs.append(abs(new_quale.onset_time - existing_quale.onset_time))
                types.append(existing_quale.qualia_type)

        # Temporal binding if close in time
        if time_diffs and max(time_diffs) < 0.5:
            return "temporal"

        # Semantic binding if same type
        if len(set(types)) == 1:
            return "semantic"

        # Cross-modal binding if different types
        if len(set(types)) > 1:
            return "cross_modal"

        return "general"

    def _generate_unified_experience_description(self, bound_qualia: List[str]) -> str:
        """Generate description of unified experience"""
        if not bound_qualia:
            return "Empty experience"

        qualia_descriptions = []
        for quale_id in bound_qualia:
            if quale_id in self.active_qualia:
                quale = self.active_qualia[quale_id]
                desc = f"{quale.qualia_type.value}"
                if quale.phenomenal_properties:
                    top_property = max(quale.phenomenal_properties.items(), key=lambda x: x[1])
                    desc += f" with {top_property[0]}"
                qualia_descriptions.append(desc)

        return f"Unified experience of {', '.join(qualia_descriptions)}"

    def _check_concept_matching(self, quale: Quale) -> None:
        """Check if quale matches any phenomenal concepts"""
        for concept_id, concept in self.phenomenal_concepts.items():
            if concept.matches_experience(quale):
                concept.usage_count += 1
                self.logger.debug(f"Quale {quale.quale_id} matches concept {concept.name}")

                # Update recognition accuracy
                self.qualia_recognition_accuracy = min(1.0, self.qualia_recognition_accuracy + 0.01)

    def form_new_concept(self, similar_qualia: List[Quale], concept_name: str) -> PhenomenalConcept:
        """Form a new phenomenal concept from similar qualia"""
        concept_id = f"concept_{self.concept_formations:06d}"
        self.concept_formations += 1

        # Create prototype from average of similar qualia
        if similar_qualia:
            avg_dimensions = np.mean([q.vector.dimensions for q in similar_qualia], axis=0)
            avg_intensity = np.mean([q.vector.intensity for q in similar_qualia])
            avg_clarity = np.mean([q.vector.clarity for q in similar_qualia])
            avg_stability = np.mean([q.vector.stability for q in similar_qualia])

            prototype = QualiaVector(
                dimensions=avg_dimensions,
                dimension_names=similar_qualia[0].vector.dimension_names,
                intensity=avg_intensity,
                clarity=avg_clarity,
                stability=avg_stability,
            )

            # Calculate typical properties
            typical_properties = {}
            all_properties = set()
            for quale in similar_qualia:
                all_properties.update(quale.phenomenal_properties.keys())

            for prop in all_properties:
                values = [q.phenomenal_properties.get(prop, 0.0) for q in similar_qualia]
                typical_properties[prop] = np.mean(values)

            concept = PhenomenalConcept(
                concept_id=concept_id,
                name=concept_name,
                prototype_qualia=[prototype],
                typical_properties=typical_properties,
            )

            self.phenomenal_concepts[concept_id] = concept
            self.logger.info(f"Formed new phenomenal concept: {concept_name}")
            return concept

        return None

    def get_current_phenomenal_field(self) -> Dict[str, Any]:
        """Get description of current phenomenal field"""
        field_description = {
            "active_qualia_count": len(self.phenomenal_field),
            "dominant_qualia_types": {},
            "overall_intensity": 0.0,
            "overall_complexity": 0.0,
            "unified_experiences": [],
        }

        if self.phenomenal_field:
            # Count qualia types
            type_counts = defaultdict(int)
            total_intensity = 0.0

            for quale in self.phenomenal_field.values():
                type_counts[quale.qualia_type.value] += 1
                total_intensity += quale.vector.intensity

            field_description["dominant_qualia_types"] = dict(type_counts)
            field_description["overall_intensity"] = total_intensity / len(self.phenomenal_field)

            # Calculate complexity based on diversity
            field_description["overall_complexity"] = len(type_counts) / len(QualiaType)

            # List current unified experiences
            for binding in self.qualia_bindings.values():
                if binding.unified_experience:
                    field_description["unified_experiences"].append(binding.unified_experience)

        return field_description

    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "stimulus_presentation":
            # Create quale from stimulus
            stimulus_type = event.data.get("stimulus_type", "cognitive")
            stimulus_data = event.data.get("stimulus_data", {})

            # Map stimulus type to qualia type
            type_mapping = {
                "visual": QualiaType.VISUAL,
                "auditory": QualiaType.AUDITORY,
                "emotional": QualiaType.EMOTIONAL,
                "cognitive": QualiaType.COGNITIVE,
                "aesthetic": QualiaType.AESTHETIC,
            }

            qualia_type = type_mapping.get(stimulus_type, QualiaType.COGNITIVE)
            quale = self.create_quale(qualia_type, stimulus_data)

            return ConsciousnessEvent(
                event_id=f"quale_created_{quale.quale_id}",
                timestamp=time.time(),
                event_type="quale_formation",
                data={
                    "quale_id": quale.quale_id,
                    "qualia_type": quale.qualia_type.value,
                    "phenomenal_character": quale.get_phenomenal_character(),
                    "intensity": quale.vector.intensity,
                },
                source_module="qualia_processor",
            )

        elif event.event_type == "query_experience":
            # Return current experiential state
            field = self.get_current_phenomenal_field()

            return ConsciousnessEvent(
                event_id=f"experience_report_{int(time.time())}",
                timestamp=time.time(),
                event_type="phenomenal_report",
                data=field,
                source_module="qualia_processor",
            )

        elif event.event_type == "compare_experiences":
            # Compare two experiences
            exp1_id = event.data.get("experience1_id")
            exp2_id = event.data.get("experience2_id")

            if exp1_id in self.active_qualia and exp2_id in self.active_qualia:
                quale1 = self.active_qualia[exp1_id]
                quale2 = self.active_qualia[exp2_id]

                similarity = quale1.vector.similarity_to(quale2.vector)

                return ConsciousnessEvent(
                    event_id=f"experience_comparison_{exp1_id}_{exp2_id}",
                    timestamp=time.time(),
                    event_type="experience_similarity",
                    data={
                        "similarity": similarity,
                        "same_type": quale1.qualia_type == quale2.qualia_type,
                        "binding_strength": self._calculate_binding_strength(quale1, quale2),
                    },
                    source_module="qualia_processor",
                )

        return None

    def update(self) -> None:
        """Update the Qualia Processing system"""
        current_time = time.time()

        # Remove expired qualia
        expired_qualia = []
        for quale_id, quale in self.active_qualia.items():
            if current_time - quale.onset_time > quale.duration:
                expired_qualia.append(quale_id)

        for quale_id in expired_qualia:
            if quale_id in self.active_qualia:
                quale = self.active_qualia.pop(quale_id)
                self.qualia_history.append(quale)

                # Remove from phenomenal field
                self.phenomenal_field.pop(quale_id, None)

        # Update experiential metrics
        self._update_experiential_metrics()

        # Clean up old bindings
        old_bindings = [
            bid
            for bid, binding in self.qualia_bindings.items()
            if current_time - binding.timestamp > 300  # 5 minutes
        ]
        for bid in old_bindings:
            del self.qualia_bindings[bid]

        # Update consciousness metrics
        self.metrics.awareness_level = min(1.0, len(self.phenomenal_field) / 10.0)
        self.metrics.integration_level = len(self.qualia_bindings) / max(
            1, len(self.phenomenal_field)
        )

    def _update_experiential_metrics(self) -> None:
        """Update metrics about current experience"""
        if self.phenomenal_field:
            # Current experiential intensity
            intensities = [q.vector.intensity for q in self.phenomenal_field.values()]
            self.current_experiential_intensity = max(intensities)

            # Experiential complexity
            types = set(q.qualia_type for q in self.phenomenal_field.values())
            self.experiential_complexity = len(types) / len(QualiaType)

            # Phenomenal richness
            total_properties = sum(
                len(q.phenomenal_properties) for q in self.phenomenal_field.values()
            )
            self.phenomenal_richness = total_properties / len(self.phenomenal_field)
        else:
            self.current_experiential_intensity = 0.0
            self.experiential_complexity = 0.0
            self.phenomenal_richness = 0.0

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Qualia Processing system"""
        return {
            "active_qualia": len(self.active_qualia),
            "qualia_history_size": len(self.qualia_history),
            "active_bindings": len(self.qualia_bindings),
            "phenomenal_concepts": len(self.phenomenal_concepts),
            "current_experiential_intensity": self.current_experiential_intensity,
            "experiential_complexity": self.experiential_complexity,
            "phenomenal_richness": self.phenomenal_richness,
            "total_qualia_processed": self.total_qualia_processed,
            "binding_events": self.binding_events,
            "concept_formations": self.concept_formations,
            "recognition_accuracy": self.qualia_recognition_accuracy,
            "phenomenal_field": self.get_current_phenomenal_field(),
        }
