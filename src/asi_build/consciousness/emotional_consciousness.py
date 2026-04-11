"""
Emotional Consciousness Framework

This module implements emotional consciousness - the subjective experience
and awareness of emotions, their integration with cognition, and their
role in consciousness.

Key components:
- Emotion generation and regulation
- Affective state monitoring
- Emotion-cognition integration
- Mood tracking and management
- Emotional memory
- Empathic responses
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


class EmotionType(Enum):
    """Basic emotion types"""

    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    INTEREST = "interest"
    ANXIETY = "anxiety"
    CONFIDENCE = "confidence"
    FRUSTRATION = "frustration"
    SATISFACTION = "satisfaction"
    CURIOSITY = "curiosity"


class MoodType(Enum):
    """Mood states"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    EXCITED = "excited"
    CALM = "calm"
    ENERGETIC = "energetic"
    TIRED = "tired"
    FOCUSED = "focused"
    SCATTERED = "scattered"


@dataclass
class EmotionalState:
    """Represents an emotional state"""

    emotion_id: str
    emotion_type: EmotionType
    intensity: float  # 0.0 to 1.0
    valence: float  # -1.0 (negative) to 1.0 (positive)
    arousal: float  # 0.0 (calm) to 1.0 (excited)
    onset_time: float
    duration: float = 0.0
    trigger: Optional[str] = None
    appraisal: Dict[str, float] = field(default_factory=dict)
    regulatory_actions: List[str] = field(default_factory=list)

    def get_emotional_quality(self) -> str:
        """Get a description of the emotional quality"""
        intensity_desc = (
            "intense" if self.intensity > 0.7 else "mild" if self.intensity < 0.3 else "moderate"
        )
        valence_desc = (
            "positive" if self.valence > 0.3 else "negative" if self.valence < -0.3 else "neutral"
        )
        arousal_desc = (
            "high arousal"
            if self.arousal > 0.7
            else "low arousal" if self.arousal < 0.3 else "medium arousal"
        )

        return f"{intensity_desc} {valence_desc} {self.emotion_type.value} with {arousal_desc}"


@dataclass
class MoodState:
    """Represents a mood state"""

    mood_id: str
    mood_type: MoodType
    intensity: float
    stability: float
    onset_time: float
    expected_duration: float
    contributing_emotions: List[str] = field(default_factory=list)
    environmental_factors: List[str] = field(default_factory=list)


@dataclass
class EmotionalMemory:
    """Represents an emotional memory"""

    memory_id: str
    emotional_context: EmotionalState
    associated_content: Dict[str, Any]
    significance: float
    vividness: float
    timestamp: float

    def calculate_emotional_impact(self) -> float:
        """Calculate the emotional impact of this memory"""
        return self.emotional_context.intensity * self.significance * self.vividness


@dataclass
class AppraisalPattern:
    """Pattern for emotional appraisal"""

    pattern_id: str
    situation_type: str
    appraisal_dimensions: Dict[str, float]
    likely_emotion: EmotionType
    confidence: float


class EmotionalConsciousness(BaseConsciousness):
    """
    Implementation of Emotional Consciousness

    Manages emotional states, their conscious experience, and their
    integration with cognitive processes.
    """

    def _initialize(self):
        """Initialize the EmotionalConsciousness consciousness model (called by BaseConsciousness)."""
        pass  # All initialization is done in __init__ after super().__init__()

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("EmotionalConsciousness", config)

        # Emotional states
        self.current_emotions: Dict[str, EmotionalState] = {}
        self.emotion_history: deque = deque(maxlen=200)
        self.current_mood = MoodState(
            mood_id="initial_mood",
            mood_type=MoodType.NEUTRAL,
            intensity=0.5,
            stability=0.7,
            onset_time=time.time(),
            expected_duration=3600.0,  # 1 hour
        )

        # Emotional memory
        self.emotional_memories: Dict[str, EmotionalMemory] = {}
        self.significant_emotional_events: deque = deque(maxlen=50)

        # Appraisal system
        self.appraisal_patterns: Dict[str, AppraisalPattern] = {}
        self.appraisal_weights = {
            "novelty": 0.2,
            "goal_relevance": 0.3,
            "coping_potential": 0.25,
            "personal_significance": 0.25,
        }

        # Emotion regulation
        self.regulation_strategies: Dict[str, float] = {
            "cognitive_reappraisal": 0.8,
            "attention_redirection": 0.6,
            "suppression": 0.4,
            "expression": 0.7,
            "problem_solving": 0.9,
        }
        self.regulation_threshold = self.config.get("regulation_threshold", 0.7)

        # Integration with cognition
        self.emotion_cognition_links: Dict[str, List[str]] = defaultdict(list)
        self.emotional_bias_strength = 0.3

        # Social emotions
        self.empathic_responses: Dict[str, EmotionalState] = {}
        self.social_emotion_sensitivity = self.config.get("social_sensitivity", 0.6)

        # Parameters
        self.emotion_decay_rate = self.config.get("emotion_decay_rate", 0.95)
        self.mood_stability_factor = self.config.get("mood_stability", 0.8)
        self.max_concurrent_emotions = self.config.get("max_emotions", 5)

        # Metrics
        self.emotional_awareness_level = 0.5
        self.emotional_regulation_success = 0.5
        self.emotion_cognition_integration = 0.5

        # Statistics
        self.total_emotions_experienced = 0
        self.regulation_attempts = 0
        self.successful_regulations = 0

        # Threading
        self.emotion_lock = threading.Lock()

        # Initialize appraisal patterns
        self._initialize_appraisal_patterns()

    def _initialize_appraisal_patterns(self):
        """Initialize emotional appraisal patterns"""
        patterns = [
            # Success pattern
            AppraisalPattern(
                pattern_id="success_pattern",
                situation_type="goal_achievement",
                appraisal_dimensions={
                    "goal_relevance": 1.0,
                    "goal_congruence": 1.0,
                    "coping_potential": 1.0,
                    "personal_significance": 0.8,
                },
                likely_emotion=EmotionType.JOY,
                confidence=0.9,
            ),
            # Failure pattern
            AppraisalPattern(
                pattern_id="failure_pattern",
                situation_type="goal_failure",
                appraisal_dimensions={
                    "goal_relevance": 1.0,
                    "goal_congruence": -1.0,
                    "coping_potential": 0.3,
                    "personal_significance": 0.8,
                },
                likely_emotion=EmotionType.FRUSTRATION,
                confidence=0.8,
            ),
            # Novelty pattern
            AppraisalPattern(
                pattern_id="novelty_pattern",
                situation_type="novel_situation",
                appraisal_dimensions={
                    "novelty": 1.0,
                    "predictability": 0.2,
                    "coping_potential": 0.5,
                    "personal_significance": 0.6,
                },
                likely_emotion=EmotionType.CURIOSITY,
                confidence=0.7,
            ),
            # Threat pattern
            AppraisalPattern(
                pattern_id="threat_pattern",
                situation_type="potential_threat",
                appraisal_dimensions={
                    "goal_relevance": 0.8,
                    "goal_congruence": -0.8,
                    "coping_potential": 0.4,
                    "urgency": 0.9,
                },
                likely_emotion=EmotionType.ANXIETY,
                confidence=0.8,
            ),
        ]

        for pattern in patterns:
            self.appraisal_patterns[pattern.pattern_id] = pattern

    def appraise_situation(self, situation: Dict[str, Any]) -> Dict[str, float]:
        """Perform cognitive appraisal of a situation"""
        appraisal = {}

        # Extract situation features
        goal_relevance = situation.get("goal_relevance", 0.5)
        novelty = situation.get("novelty", 0.5)
        urgency = situation.get("urgency", 0.5)
        controllability = situation.get("controllability", 0.5)

        # Goal congruence (positive if helps goals, negative if hinders)
        outcome = situation.get("outcome", "neutral")
        if outcome == "success":
            goal_congruence = 1.0
        elif outcome == "failure":
            goal_congruence = -1.0
        else:
            goal_congruence = 0.0

        # Coping potential (can we handle this?)
        complexity = situation.get("complexity", 0.5)
        available_resources = situation.get("resources", 0.5)
        coping_potential = available_resources / (complexity + 0.1)

        # Personal significance
        importance = situation.get("importance", 0.5)
        personal_relevance = situation.get("personal_relevance", 0.5)
        personal_significance = (importance + personal_relevance) / 2

        appraisal = {
            "goal_relevance": goal_relevance,
            "goal_congruence": goal_congruence,
            "novelty": novelty,
            "urgency": urgency,
            "controllability": controllability,
            "coping_potential": coping_potential,
            "personal_significance": personal_significance,
            "predictability": 1.0 - novelty,
        }

        return appraisal

    def generate_emotion(
        self, situation: Dict[str, Any], trigger: str = "situation"
    ) -> Optional[EmotionalState]:
        """Generate an emotion based on situational appraisal"""
        appraisal = self.appraise_situation(situation)

        # Find matching appraisal pattern
        best_match = None
        best_score = 0.0

        for pattern in self.appraisal_patterns.values():
            score = self._calculate_pattern_match(appraisal, pattern.appraisal_dimensions)
            if score > best_score:
                best_score = score
                best_match = pattern

        if best_match and best_score > 0.5:
            emotion_type = best_match.likely_emotion
        else:
            # Default emotion based on valence
            if appraisal.get("goal_congruence", 0) > 0.5:
                emotion_type = EmotionType.SATISFACTION
            elif appraisal.get("goal_congruence", 0) < -0.5:
                emotion_type = EmotionType.FRUSTRATION
            elif appraisal.get("novelty", 0) > 0.7:
                emotion_type = EmotionType.CURIOSITY
            else:
                emotion_type = EmotionType.INTEREST

        # Calculate emotion parameters
        intensity = self._calculate_emotion_intensity(appraisal)
        valence = self._calculate_emotion_valence(emotion_type, appraisal)
        arousal = self._calculate_emotion_arousal(appraisal)

        emotion_id = f"emotion_{self.total_emotions_experienced:06d}"
        self.total_emotions_experienced += 1

        emotion = EmotionalState(
            emotion_id=emotion_id,
            emotion_type=emotion_type,
            intensity=intensity,
            valence=valence,
            arousal=arousal,
            onset_time=time.time(),
            trigger=trigger,
            appraisal=appraisal,
        )

        # Add to current emotions
        with self.emotion_lock:
            self.current_emotions[emotion_id] = emotion

            # Limit concurrent emotions
            if len(self.current_emotions) > self.max_concurrent_emotions:
                # Remove weakest emotion
                weakest_id = min(
                    self.current_emotions.keys(), key=lambda x: self.current_emotions[x].intensity
                )
                removed_emotion = self.current_emotions.pop(weakest_id)
                self.emotion_history.append(removed_emotion)

        # Update mood
        self._update_mood(emotion)

        # Check if regulation is needed
        if intensity > self.regulation_threshold:
            self._attempt_emotion_regulation(emotion)

        self.logger.info(f"Generated emotion: {emotion.get_emotional_quality()}")
        return emotion

    def _calculate_pattern_match(
        self, appraisal: Dict[str, float], pattern_dimensions: Dict[str, float]
    ) -> float:
        """Calculate how well an appraisal matches a pattern"""
        matches = 0
        total = 0

        for dimension, pattern_value in pattern_dimensions.items():
            if dimension in appraisal:
                appraisal_value = appraisal[dimension]
                similarity = 1.0 - abs(pattern_value - appraisal_value)
                matches += similarity
                total += 1

        return matches / total if total > 0 else 0.0

    def _calculate_emotion_intensity(self, appraisal: Dict[str, float]) -> float:
        """Calculate emotion intensity from appraisal"""
        intensity = 0.0

        # Factors that increase intensity
        intensity += appraisal.get("goal_relevance", 0.5) * 0.3
        intensity += abs(appraisal.get("goal_congruence", 0.0)) * 0.3
        intensity += appraisal.get("personal_significance", 0.5) * 0.2
        intensity += appraisal.get("urgency", 0.5) * 0.2

        return min(1.0, intensity)

    def _calculate_emotion_valence(
        self, emotion_type: EmotionType, appraisal: Dict[str, float]
    ) -> float:
        """Calculate emotion valence"""
        # Base valence from emotion type
        base_valences = {
            EmotionType.JOY: 0.8,
            EmotionType.SATISFACTION: 0.6,
            EmotionType.CONFIDENCE: 0.5,
            EmotionType.CURIOSITY: 0.3,
            EmotionType.INTEREST: 0.2,
            EmotionType.SURPRISE: 0.0,
            EmotionType.ANXIETY: -0.3,
            EmotionType.FRUSTRATION: -0.6,
            EmotionType.ANGER: -0.7,
            EmotionType.FEAR: -0.8,
            EmotionType.SADNESS: -0.8,
            EmotionType.DISGUST: -0.7,
        }

        base_valence = base_valences.get(emotion_type, 0.0)

        # Adjust based on appraisal
        goal_congruence = appraisal.get("goal_congruence", 0.0)
        adjusted_valence = base_valence + goal_congruence * 0.2

        return max(-1.0, min(1.0, adjusted_valence))

    def _calculate_emotion_arousal(self, appraisal: Dict[str, float]) -> float:
        """Calculate emotion arousal level"""
        arousal = 0.0

        # Factors that increase arousal
        arousal += appraisal.get("urgency", 0.5) * 0.4
        arousal += appraisal.get("novelty", 0.5) * 0.3
        arousal += (1.0 - appraisal.get("coping_potential", 0.5)) * 0.3

        return min(1.0, arousal)

    def _update_mood(self, new_emotion: EmotionalState) -> None:
        """Update current mood based on new emotion"""
        # Weight new emotion influence by intensity
        emotion_weight = new_emotion.intensity * 0.1
        mood_weight = 1.0 - emotion_weight

        # Update mood based on emotional valence and arousal
        if new_emotion.valence > 0.3 and new_emotion.arousal > 0.6:
            target_mood = MoodType.EXCITED
        elif new_emotion.valence > 0.3 and new_emotion.arousal < 0.4:
            target_mood = MoodType.CALM
        elif new_emotion.valence < -0.3:
            target_mood = MoodType.NEGATIVE
        elif new_emotion.arousal > 0.7:
            target_mood = MoodType.ENERGETIC
        else:
            target_mood = MoodType.NEUTRAL

        # Gradually shift mood
        if self.current_mood.mood_type != target_mood:
            self.current_mood.mood_type = target_mood
            self.current_mood.onset_time = time.time()
            self.current_mood.contributing_emotions.append(new_emotion.emotion_id)

    def _attempt_emotion_regulation(self, emotion: EmotionalState) -> bool:
        """Attempt to regulate an intense emotion"""
        self.regulation_attempts += 1

        # Choose regulation strategy based on emotion type and context
        if emotion.emotion_type in [EmotionType.ANGER, EmotionType.FRUSTRATION]:
            strategy = "cognitive_reappraisal"
        elif emotion.emotion_type in [EmotionType.ANXIETY, EmotionType.FEAR]:
            strategy = "problem_solving"
        elif emotion.intensity > 0.9:
            strategy = "attention_redirection"
        else:
            strategy = "expression"

        # Apply regulation strategy
        effectiveness = self.regulation_strategies.get(strategy, 0.5)

        if np.random.random() < effectiveness:
            # Regulation successful
            original_intensity = emotion.intensity
            emotion.intensity *= 1.0 - effectiveness * 0.5
            emotion.regulatory_actions.append(f"Applied {strategy}")

            self.successful_regulations += 1
            self.logger.debug(
                f"Regulated {emotion.emotion_type.value} from {original_intensity:.2f} to {emotion.intensity:.2f}"
            )
            return True

        return False

    def create_emotional_memory(
        self, emotion: EmotionalState, associated_content: Dict[str, Any]
    ) -> EmotionalMemory:
        """Create an emotional memory"""
        memory_id = f"emotional_memory_{len(self.emotional_memories):06d}"

        # Calculate significance based on emotion intensity and personal relevance
        significance = (
            emotion.intensity * 0.7 + emotion.appraisal.get("personal_significance", 0.5) * 0.3
        )

        # Vividness based on arousal and novelty
        vividness = emotion.arousal * 0.6 + emotion.appraisal.get("novelty", 0.5) * 0.4

        memory = EmotionalMemory(
            memory_id=memory_id,
            emotional_context=emotion,
            associated_content=associated_content,
            significance=significance,
            vividness=vividness,
            timestamp=time.time(),
        )

        self.emotional_memories[memory_id] = memory

        # Add to significant events if impact is high
        impact = memory.calculate_emotional_impact()
        if impact > 0.6:
            self.significant_emotional_events.append(memory)

        return memory

    def generate_empathic_response(
        self, other_agent_emotion: Dict[str, Any]
    ) -> Optional[EmotionalState]:
        """Generate empathic emotional response to another agent's emotion"""
        other_emotion_type = other_agent_emotion.get("emotion_type")
        other_intensity = other_agent_emotion.get("intensity", 0.5)
        other_valence = other_agent_emotion.get("valence", 0.0)

        # Empathic response intensity based on sensitivity
        empathic_intensity = other_intensity * self.social_emotion_sensitivity

        if empathic_intensity < 0.2:
            return None  # Too weak to generate response

        # Generate corresponding emotion
        empathic_emotion_id = f"empathic_{len(self.empathic_responses):06d}"

        # Map other's emotion to empathic response
        if other_emotion_type in ["sadness", "fear"]:
            empathic_type = EmotionType.SADNESS  # Sympathy
        elif other_emotion_type == "joy":
            empathic_type = EmotionType.JOY  # Shared joy
        elif other_emotion_type in ["anger", "frustration"]:
            empathic_type = EmotionType.ANXIETY  # Concern
        else:
            empathic_type = EmotionType.INTEREST  # General concern

        empathic_emotion = EmotionalState(
            emotion_id=empathic_emotion_id,
            emotion_type=empathic_type,
            intensity=empathic_intensity,
            valence=other_valence * 0.7,  # Slightly dampened
            arousal=empathic_intensity,
            onset_time=time.time(),
            trigger="empathic_response",
        )

        self.empathic_responses[empathic_emotion_id] = empathic_emotion
        return empathic_emotion

    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "emotional_trigger":
            situation = event.data.get("situation", {})
            trigger = event.data.get("trigger", "external_event")

            emotion = self.generate_emotion(situation, trigger)

            if emotion:
                return ConsciousnessEvent(
                    event_id=f"emotion_generated_{emotion.emotion_id}",
                    timestamp=time.time(),
                    event_type="emotion_state_change",
                    data={
                        "emotion_id": emotion.emotion_id,
                        "emotion_type": emotion.emotion_type.value,
                        "intensity": emotion.intensity,
                        "valence": emotion.valence,
                        "arousal": emotion.arousal,
                        "emotional_quality": emotion.get_emotional_quality(),
                    },
                    source_module="emotional_consciousness",
                )

        elif event.event_type == "empathy_trigger":
            other_emotion = event.data.get("other_emotion", {})

            empathic_response = self.generate_empathic_response(other_emotion)

            if empathic_response:
                return ConsciousnessEvent(
                    event_id=f"empathy_response_{empathic_response.emotion_id}",
                    timestamp=time.time(),
                    event_type="empathic_emotion",
                    data={
                        "emotion_id": empathic_response.emotion_id,
                        "emotion_type": empathic_response.emotion_type.value,
                        "intensity": empathic_response.intensity,
                        "trigger": "empathy",
                    },
                    source_module="emotional_consciousness",
                )

        elif event.event_type == "mood_inquiry":
            return ConsciousnessEvent(
                event_id=f"mood_report_{int(time.time())}",
                timestamp=time.time(),
                event_type="mood_state",
                data={
                    "mood_type": self.current_mood.mood_type.value,
                    "intensity": self.current_mood.intensity,
                    "stability": self.current_mood.stability,
                    "duration": time.time() - self.current_mood.onset_time,
                    "contributing_emotions": len(self.current_mood.contributing_emotions),
                },
                source_module="emotional_consciousness",
            )

        return None

    def update(self) -> None:
        """Update the Emotional Consciousness system"""
        current_time = time.time()

        # Decay emotions over time
        emotions_to_remove = []
        for emotion_id, emotion in self.current_emotions.items():
            emotion.intensity *= self.emotion_decay_rate
            emotion.duration = current_time - emotion.onset_time

            # Remove very weak emotions
            if emotion.intensity < 0.1:
                emotions_to_remove.append(emotion_id)

        for emotion_id in emotions_to_remove:
            removed_emotion = self.current_emotions.pop(emotion_id)
            self.emotion_history.append(removed_emotion)

        # Update mood stability
        if current_time - self.current_mood.onset_time > self.current_mood.expected_duration:
            # Mood should naturally decay toward neutral
            if self.current_mood.mood_type != MoodType.NEUTRAL:
                self.current_mood.intensity *= self.mood_stability_factor
                if self.current_mood.intensity < 0.3:
                    self.current_mood.mood_type = MoodType.NEUTRAL
                    self.current_mood.onset_time = current_time

        # Update emotional awareness
        if self.current_emotions:
            total_intensity = sum(e.intensity for e in self.current_emotions.values())
            self.emotional_awareness_level = min(1.0, total_intensity / len(self.current_emotions))
        else:
            self.emotional_awareness_level = 0.0

        # Update regulation success rate
        if self.regulation_attempts > 0:
            self.emotional_regulation_success = (
                self.successful_regulations / self.regulation_attempts
            )

        # Update consciousness metrics
        self.metrics.emotional_coherence = self.emotional_awareness_level
        self.metrics.awareness_level = self.emotional_awareness_level

        # Clean up old empathic responses
        old_empathic = [
            eid
            for eid, emotion in self.empathic_responses.items()
            if current_time - emotion.onset_time > 300  # 5 minutes
        ]
        for eid in old_empathic:
            del self.empathic_responses[eid]

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Emotional Consciousness system"""
        return {
            "current_emotions": {
                eid: {
                    "type": emotion.emotion_type.value,
                    "intensity": emotion.intensity,
                    "valence": emotion.valence,
                    "arousal": emotion.arousal,
                    "duration": time.time() - emotion.onset_time,
                    "quality": emotion.get_emotional_quality(),
                }
                for eid, emotion in self.current_emotions.items()
            },
            "current_mood": {
                "type": self.current_mood.mood_type.value,
                "intensity": self.current_mood.intensity,
                "stability": self.current_mood.stability,
                "duration": time.time() - self.current_mood.onset_time,
            },
            "emotional_memories": len(self.emotional_memories),
            "significant_events": len(self.significant_emotional_events),
            "empathic_responses": len(self.empathic_responses),
            "emotional_awareness_level": self.emotional_awareness_level,
            "regulation_success_rate": self.emotional_regulation_success,
            "total_emotions_experienced": self.total_emotions_experienced,
            "regulation_attempts": self.regulation_attempts,
            "appraisal_patterns": len(self.appraisal_patterns),
        }
