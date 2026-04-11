"""
Emotion Transmitter

This module handles the encoding and transmission of emotional states
through telepathic channels, simulating empathic connections between minds.
"""

import numpy as np
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class EmotionType(Enum):
    """Basic emotion types"""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    LOVE = "love"
    EXCITEMENT = "excitement"
    CALM = "calm"
    ANXIETY = "anxiety"
    CONTENTMENT = "contentment"
    FRUSTRATION = "frustration"

class EmotionIntensity(Enum):
    """Emotion intensity levels"""
    SUBTLE = "subtle"
    MILD = "mild"
    MODERATE = "moderate"
    STRONG = "strong"
    INTENSE = "intense"
    OVERWHELMING = "overwhelming"

@dataclass
class EmotionalState:
    """Represents an emotional state"""
    emotion_id: str
    primary_emotion: EmotionType
    intensity: EmotionIntensity
    emotion_vector: np.ndarray  # Multi-dimensional emotion representation
    arousal_level: float  # 0.0 to 1.0
    valence: float  # -1.0 (negative) to 1.0 (positive)
    dominance: float  # 0.0 (submissive) to 1.0 (dominant)
    duration: float  # seconds
    source_id: str
    timestamp: datetime
    physiological_markers: Dict[str, float]
    neural_signature: np.ndarray

class EmotionTransmitter:
    """
    Advanced Emotion Transmission System
    
    Encodes and transmits emotional states through telepathic channels:
    - Multi-dimensional emotion encoding
    - Physiological emotion mapping
    - Neural emotion signatures
    - Empathic resonance modeling
    - Emotional contagion simulation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        
        # Emotion processing
        self.emotion_encoder = self._initialize_emotion_encoder()
        self.physiological_mapper = self._initialize_physiological_mapper()
        self.neural_correlator = self._initialize_neural_correlator()
        
        # Transmission systems
        self.empathic_resonator = self._initialize_empathic_resonator()
        self.emotion_amplifier = self._initialize_emotion_amplifier()
        
        # Emotion database
        self.emotion_history = []
        self.transmission_log = []
        
        # Performance metrics
        self.transmission_success_rate = 0.89
        self.emotion_fidelity = 0.91
        self.empathic_resonance = 0.85
        
        logger.info("EmotionTransmitter initialized")
    
    def _default_config(self) -> Dict:
        """Default configuration for emotion transmitter"""
        return {
            "emotion_dimensions": 64,
            "transmission_frequency": 6.0,  # Hz (Theta waves for emotions)
            "empathic_coupling_strength": 0.8,
            "emotion_decay_rate": 0.9,
            "resonance_threshold": 0.6,
            "physiological_weighting": 0.4,
            "neural_weighting": 0.6,
            "enable_emotion_amplification": True,
            "enable_contagion_modeling": True,
            "enable_empathic_mirroring": True,
            "max_transmission_distance": 1000.0,  # meters
            "emotion_bandwidth": 20.0,  # Hz
            "emotional_interference_filtering": True
        }
    
    async def encode_emotional_state(self, emotional_state: Dict,
                                   source_neural_signature: np.ndarray) -> EmotionalState:
        """
        Encode emotional state for telepathic transmission
        
        Args:
            emotional_state: Raw emotional state data
            source_neural_signature: Neural signature of the source
            
        Returns:
            EmotionalState: Encoded emotional state
        """
        # Extract primary emotion and intensity
        primary_emotion = await self._identify_primary_emotion(emotional_state)
        intensity = await self._assess_emotion_intensity(emotional_state)
        
        # Create multi-dimensional emotion vector
        emotion_vector = await self._create_emotion_vector(emotional_state)
        
        # Calculate dimensional attributes
        arousal_level = await self._calculate_arousal(emotional_state)
        valence = await self._calculate_valence(emotional_state)
        dominance = await self._calculate_dominance(emotional_state)
        
        # Extract physiological markers
        physiological_markers = await self._extract_physiological_markers(emotional_state)
        
        # Generate neural signature for emotion
        neural_signature = await self._generate_emotion_neural_signature(
            emotion_vector, source_neural_signature
        )
        
        # Create emotional state object
        emotion_id = f"emo_{int(time.time())}_{hash(str(emotional_state)) % 10000}"
        
        encoded_emotion = EmotionalState(
            emotion_id=emotion_id,
            primary_emotion=primary_emotion,
            intensity=intensity,
            emotion_vector=emotion_vector,
            arousal_level=arousal_level,
            valence=valence,
            dominance=dominance,
            duration=emotional_state.get("duration", 5.0),
            source_id=emotional_state.get("source_id", "unknown"),
            timestamp=datetime.now(),
            physiological_markers=physiological_markers,
            neural_signature=neural_signature
        )
        
        # Store in emotion history
        self.emotion_history.append(encoded_emotion)
        
        logger.info(f"Emotion encoded: {emotion_id}, type: {primary_emotion.value}, "
                   f"intensity: {intensity.value}, valence: {valence:.3f}")
        
        return encoded_emotion
    
    async def transmit_emotion(self, emotional_state: EmotionalState,
                             target_participants: List[str],
                             transmission_method: str = "empathic_resonance") -> Dict:
        """
        Transmit emotional state to target participants
        
        Args:
            emotional_state: Encoded emotional state
            target_participants: List of target participant IDs
            transmission_method: Method of emotional transmission
            
        Returns:
            Dict: Transmission results
        """
        transmission_id = f"tx_{emotional_state.emotion_id}_{int(time.time())}"
        
        # Prepare emotion for transmission
        transmission_signal = await self._prepare_emotion_transmission(
            emotional_state, transmission_method
        )
        
        # Apply empathic resonance
        if self.config["enable_empathic_mirroring"]:
            resonance_enhanced = await self._apply_empathic_resonance(
                transmission_signal, emotional_state
            )
        else:
            resonance_enhanced = transmission_signal
        
        # Transmit to each target
        transmission_results = []
        for target_id in target_participants:
            result = await self._transmit_to_target(
                resonance_enhanced, emotional_state, target_id
            )
            transmission_results.append(result)
        
        # Calculate overall transmission metrics
        success_count = sum(1 for r in transmission_results if r["success"])
        average_fidelity = np.mean([r["fidelity"] for r in transmission_results])
        average_resonance = np.mean([r["empathic_resonance"] for r in transmission_results])
        
        # Log transmission
        transmission_log = {
            "transmission_id": transmission_id,
            "emotion_id": emotional_state.emotion_id,
            "emotion_type": emotional_state.primary_emotion.value,
            "targets_count": len(target_participants),
            "successful_transmissions": success_count,
            "average_fidelity": average_fidelity,
            "average_resonance": average_resonance,
            "transmission_method": transmission_method,
            "timestamp": datetime.now(),
            "results": transmission_results
        }
        
        self.transmission_log.append(transmission_log)
        
        # Update performance metrics
        self._update_transmission_metrics(transmission_log)
        
        logger.info(f"Emotion transmitted: {transmission_id}, "
                   f"success_rate: {success_count}/{len(target_participants)}")
        
        return transmission_log
    
    async def create_empathic_bond(self, participant_a: str, participant_b: str) -> str:
        """
        Create empathic bond between two participants
        
        Args:
            participant_a: First participant ID
            participant_b: Second participant ID
            
        Returns:
            str: Empathic bond ID
        """
        bond_id = f"bond_{participant_a}_{participant_b}_{int(time.time())}"
        
        # Initialize empathic connection
        empathic_bond = {
            "bond_id": bond_id,
            "participant_a": participant_a,
            "participant_b": participant_b,
            "bond_strength": 0.0,
            "synchronization_level": 0.0,
            "created_time": datetime.now(),
            "last_sync": None,
            "emotion_exchanges": 0,
            "resonance_history": []
        }
        
        # Establish initial connection
        initial_strength = await self._establish_empathic_connection(
            participant_a, participant_b
        )
        empathic_bond["bond_strength"] = initial_strength
        
        logger.info(f"Empathic bond created: {bond_id}, strength: {initial_strength:.3f}")
        return bond_id
    
    async def enhance_emotional_transmission(self, emotional_state: EmotionalState,
                                           enhancement_factor: float = 1.5) -> EmotionalState:
        """
        Enhance emotional transmission strength and clarity
        
        Args:
            emotional_state: Original emotional state
            enhancement_factor: Enhancement multiplier
            
        Returns:
            EmotionalState: Enhanced emotional state
        """
        # Amplify emotion vector
        enhanced_vector = emotional_state.emotion_vector * enhancement_factor
        
        # Increase arousal and maintain valence
        enhanced_arousal = min(1.0, emotional_state.arousal_level * enhancement_factor)
        
        # Enhance neural signature
        enhanced_neural = emotional_state.neural_signature * np.sqrt(enhancement_factor)
        
        # Create enhanced emotional state
        enhanced_emotion = EmotionalState(
            emotion_id=f"enhanced_{emotional_state.emotion_id}",
            primary_emotion=emotional_state.primary_emotion,
            intensity=self._amplify_intensity(emotional_state.intensity, enhancement_factor),
            emotion_vector=enhanced_vector,
            arousal_level=enhanced_arousal,
            valence=emotional_state.valence,
            dominance=emotional_state.dominance,
            duration=emotional_state.duration,
            source_id=emotional_state.source_id,
            timestamp=datetime.now(),
            physiological_markers=emotional_state.physiological_markers,
            neural_signature=enhanced_neural
        )
        
        return enhanced_emotion
    
    async def measure_empathic_resonance(self, participant_a: str, 
                                       participant_b: str) -> float:
        """
        Measure empathic resonance between two participants
        
        Args:
            participant_a: First participant ID
            participant_b: Second participant ID
            
        Returns:
            float: Empathic resonance level (0.0 to 1.0)
        """
        # Get recent emotional states for both participants
        emotions_a = await self._get_recent_emotions(participant_a)
        emotions_b = await self._get_recent_emotions(participant_b)
        
        if not emotions_a or not emotions_b:
            return 0.0
        
        # Calculate emotional synchronization
        synchronization = await self._calculate_emotional_synchronization(
            emotions_a, emotions_b
        )
        
        # Calculate valence correlation
        valence_correlation = await self._calculate_valence_correlation(
            emotions_a, emotions_b
        )
        
        # Calculate arousal correlation
        arousal_correlation = await self._calculate_arousal_correlation(
            emotions_a, emotions_b
        )
        
        # Combined empathic resonance
        resonance = (synchronization + valence_correlation + arousal_correlation) / 3
        
        return min(1.0, max(0.0, resonance))
    
    # Private methods
    
    async def _identify_primary_emotion(self, emotional_state: Dict) -> EmotionType:
        """Identify primary emotion from emotional state data"""
        
        # Extract emotion indicators
        if "emotion" in emotional_state:
            emotion_name = emotional_state["emotion"].lower()
            
            # Map to emotion types
            emotion_mapping = {
                "happy": EmotionType.JOY,
                "joy": EmotionType.JOY,
                "sad": EmotionType.SADNESS,
                "sadness": EmotionType.SADNESS,
                "angry": EmotionType.ANGER,
                "anger": EmotionType.ANGER,
                "afraid": EmotionType.FEAR,
                "fear": EmotionType.FEAR,
                "surprised": EmotionType.SURPRISE,
                "surprise": EmotionType.SURPRISE,
                "disgusted": EmotionType.DISGUST,
                "disgust": EmotionType.DISGUST,
                "love": EmotionType.LOVE,
                "excited": EmotionType.EXCITEMENT,
                "calm": EmotionType.CALM,
                "anxious": EmotionType.ANXIETY,
                "content": EmotionType.CONTENTMENT,
                "frustrated": EmotionType.FRUSTRATION
            }
            
            return emotion_mapping.get(emotion_name, EmotionType.CONTENTMENT)
        
        # Default fallback
        return EmotionType.CONTENTMENT
    
    async def _assess_emotion_intensity(self, emotional_state: Dict) -> EmotionIntensity:
        """Assess intensity of emotional state"""
        
        intensity_value = emotional_state.get("intensity", 0.5)
        
        if intensity_value < 0.1:
            return EmotionIntensity.SUBTLE
        elif intensity_value < 0.3:
            return EmotionIntensity.MILD
        elif intensity_value < 0.5:
            return EmotionIntensity.MODERATE
        elif intensity_value < 0.7:
            return EmotionIntensity.STRONG
        elif intensity_value < 0.9:
            return EmotionIntensity.INTENSE
        else:
            return EmotionIntensity.OVERWHELMING
    
    async def _create_emotion_vector(self, emotional_state: Dict) -> np.ndarray:
        """Create multi-dimensional emotion vector"""
        
        dimensions = self.config["emotion_dimensions"]
        emotion_vector = np.zeros(dimensions)
        
        # Map emotional components to vector dimensions
        if "emotions" in emotional_state:
            emotions = emotional_state["emotions"]
            for i, (emotion, value) in enumerate(emotions.items()):
                if i < dimensions:
                    emotion_vector[i] = value
        else:
            # Create default vector based on primary emotion
            primary_emotion = await self._identify_primary_emotion(emotional_state)
            intensity = await self._assess_emotion_intensity(emotional_state)
            
            # Encode primary emotion in vector
            emotion_indices = {
                EmotionType.JOY: 0,
                EmotionType.SADNESS: 8,
                EmotionType.ANGER: 16,
                EmotionType.FEAR: 24,
                EmotionType.SURPRISE: 32,
                EmotionType.LOVE: 40,
                EmotionType.CALM: 48,
                EmotionType.EXCITEMENT: 56
            }
            
            base_index = emotion_indices.get(primary_emotion, 0)
            intensity_multiplier = self._intensity_to_value(intensity)
            
            # Fill emotion vector
            for i in range(8):  # 8 dimensions per emotion
                if base_index + i < dimensions:
                    emotion_vector[base_index + i] = intensity_multiplier * np.random.uniform(0.5, 1.0)
        
        # Normalize vector
        norm = np.linalg.norm(emotion_vector)
        if norm > 0:
            emotion_vector = emotion_vector / norm
        
        return emotion_vector
    
    async def _calculate_arousal(self, emotional_state: Dict) -> float:
        """Calculate arousal level"""
        
        if "arousal" in emotional_state:
            return float(emotional_state["arousal"])
        
        # Estimate arousal from emotion type
        primary_emotion = await self._identify_primary_emotion(emotional_state)
        intensity = await self._assess_emotion_intensity(emotional_state)
        
        emotion_arousal_map = {
            EmotionType.JOY: 0.7,
            EmotionType.EXCITEMENT: 0.9,
            EmotionType.ANGER: 0.8,
            EmotionType.FEAR: 0.8,
            EmotionType.SURPRISE: 0.7,
            EmotionType.SADNESS: 0.3,
            EmotionType.CALM: 0.2,
            EmotionType.CONTENTMENT: 0.4
        }
        
        base_arousal = emotion_arousal_map.get(primary_emotion, 0.5)
        intensity_modifier = self._intensity_to_value(intensity)
        
        return min(1.0, base_arousal * intensity_modifier)
    
    async def _calculate_valence(self, emotional_state: Dict) -> float:
        """Calculate emotional valence (-1 to 1)"""
        
        if "valence" in emotional_state:
            return float(emotional_state["valence"])
        
        # Estimate valence from emotion type
        primary_emotion = await self._identify_primary_emotion(emotional_state)
        
        emotion_valence_map = {
            EmotionType.JOY: 0.8,
            EmotionType.LOVE: 0.9,
            EmotionType.EXCITEMENT: 0.7,
            EmotionType.CONTENTMENT: 0.6,
            EmotionType.CALM: 0.5,
            EmotionType.SURPRISE: 0.1,
            EmotionType.SADNESS: -0.7,
            EmotionType.ANGER: -0.6,
            EmotionType.FEAR: -0.8,
            EmotionType.DISGUST: -0.8,
            EmotionType.ANXIETY: -0.5,
            EmotionType.FRUSTRATION: -0.4
        }
        
        return emotion_valence_map.get(primary_emotion, 0.0)
    
    async def _calculate_dominance(self, emotional_state: Dict) -> float:
        """Calculate emotional dominance"""
        
        if "dominance" in emotional_state:
            return float(emotional_state["dominance"])
        
        # Estimate dominance from emotion type
        primary_emotion = await self._identify_primary_emotion(emotional_state)
        
        emotion_dominance_map = {
            EmotionType.ANGER: 0.8,
            EmotionType.EXCITEMENT: 0.7,
            EmotionType.JOY: 0.6,
            EmotionType.LOVE: 0.5,
            EmotionType.SURPRISE: 0.3,
            EmotionType.FEAR: 0.2,
            EmotionType.SADNESS: 0.2,
            EmotionType.ANXIETY: 0.1,
            EmotionType.CALM: 0.5,
            EmotionType.CONTENTMENT: 0.4
        }
        
        return emotion_dominance_map.get(primary_emotion, 0.5)
    
    def _intensity_to_value(self, intensity: EmotionIntensity) -> float:
        """Convert intensity enum to numeric value"""
        intensity_values = {
            EmotionIntensity.SUBTLE: 0.1,
            EmotionIntensity.MILD: 0.3,
            EmotionIntensity.MODERATE: 0.5,
            EmotionIntensity.STRONG: 0.7,
            EmotionIntensity.INTENSE: 0.9,
            EmotionIntensity.OVERWHELMING: 1.0
        }
        return intensity_values.get(intensity, 0.5)
    
    def _amplify_intensity(self, intensity: EmotionIntensity, factor: float) -> EmotionIntensity:
        """Amplify emotion intensity"""
        current_value = self._intensity_to_value(intensity)
        amplified_value = min(1.0, current_value * factor)
        
        if amplified_value >= 1.0:
            return EmotionIntensity.OVERWHELMING
        elif amplified_value >= 0.9:
            return EmotionIntensity.INTENSE
        elif amplified_value >= 0.7:
            return EmotionIntensity.STRONG
        elif amplified_value >= 0.5:
            return EmotionIntensity.MODERATE
        elif amplified_value >= 0.3:
            return EmotionIntensity.MILD
        else:
            return EmotionIntensity.SUBTLE
    
    # Initialization methods
    
    def _initialize_emotion_encoder(self) -> Dict:
        """Initialize emotion encoding system"""
        return {
            "emotion_mappings": {},
            "intensity_scalers": {},
            "vector_generators": {}
        }
    
    def _initialize_physiological_mapper(self) -> Dict:
        """Initialize physiological emotion mapping"""
        return {
            "heart_rate_correlations": {},
            "skin_conductance_maps": {},
            "facial_expression_encoders": {}
        }
    
    def _initialize_neural_correlator(self) -> Dict:
        """Initialize neural emotion correlation"""
        return {
            "neural_emotion_patterns": {},
            "brainwave_correlations": {},
            "connectivity_maps": {}
        }
    
    def _initialize_empathic_resonator(self) -> Dict:
        """Initialize empathic resonance system"""
        return {
            "resonance_calculators": {},
            "synchronization_detectors": {},
            "mirroring_systems": {}
        }
    
    def _initialize_emotion_amplifier(self) -> Dict:
        """Initialize emotion amplification system"""
        return {
            "amplification_filters": {},
            "intensity_enhancers": {},
            "resonance_boosters": {}
        }
    
    def get_transmitter_stats(self) -> Dict:
        """Get comprehensive transmitter statistics"""
        return {
            "emotions_encoded": len(self.emotion_history),
            "transmissions_completed": len(self.transmission_log),
            "transmission_success_rate": self.transmission_success_rate,
            "emotion_fidelity": self.emotion_fidelity,
            "empathic_resonance": self.empathic_resonance,
            "config": self.config
        }
    
    # Stub implementations for complex methods
    
    async def _extract_physiological_markers(self, emotional_state: Dict) -> Dict[str, float]:
        """Extract physiological emotion markers"""
        return {
            "heart_rate": 75.0,
            "skin_conductance": 0.5,
            "facial_tension": 0.3,
            "breathing_rate": 16.0
        }
    
    async def _generate_emotion_neural_signature(self, emotion_vector: np.ndarray, 
                                               neural_signature: np.ndarray) -> np.ndarray:
        """Generate neural signature for emotion"""
        # Combine emotion vector with neural signature
        combined = emotion_vector[:len(neural_signature)] * neural_signature
        return combined / np.linalg.norm(combined)
    
    async def _prepare_emotion_transmission(self, emotion: EmotionalState, method: str) -> np.ndarray:
        """Prepare emotion for transmission"""
        return emotion.emotion_vector
    
    async def _apply_empathic_resonance(self, signal: np.ndarray, emotion: EmotionalState) -> np.ndarray:
        """Apply empathic resonance enhancement"""
        resonance_factor = self.config["empathic_coupling_strength"]
        return signal * (1.0 + resonance_factor)
    
    async def _transmit_to_target(self, signal: np.ndarray, emotion: EmotionalState, target_id: str) -> Dict:
        """Transmit emotion to specific target"""
        return {
            "target_id": target_id,
            "success": True,
            "fidelity": np.random.uniform(0.8, 0.95),
            "empathic_resonance": np.random.uniform(0.7, 0.9),
            "transmission_time": time.time()
        }
    
    async def _establish_empathic_connection(self, participant_a: str, participant_b: str) -> float:
        """Establish empathic connection between participants"""
        return np.random.uniform(0.6, 0.9)
    
    def _update_transmission_metrics(self, transmission_log: Dict):
        """Update transmission performance metrics"""
        success_rate = transmission_log["successful_transmissions"] / transmission_log["targets_count"]
        fidelity = transmission_log["average_fidelity"]
        resonance = transmission_log["average_resonance"]
        
        # Update running averages
        self.transmission_success_rate = (self.transmission_success_rate * 0.9 + success_rate * 0.1)
        self.emotion_fidelity = (self.emotion_fidelity * 0.9 + fidelity * 0.1)
        self.empathic_resonance = (self.empathic_resonance * 0.9 + resonance * 0.1)
    
    async def _get_recent_emotions(self, participant_id: str) -> List[EmotionalState]:
        """Get recent emotions for participant"""
        return [e for e in self.emotion_history[-10:] if e.source_id == participant_id]
    
    async def _calculate_emotional_synchronization(self, emotions_a: List[EmotionalState], 
                                                 emotions_b: List[EmotionalState]) -> float:
        """Calculate emotional synchronization between participants"""
        return np.random.uniform(0.6, 0.9)  # Stub
    
    async def _calculate_valence_correlation(self, emotions_a: List[EmotionalState], 
                                          emotions_b: List[EmotionalState]) -> float:
        """Calculate valence correlation between participants"""
        return np.random.uniform(0.5, 0.8)  # Stub
    
    async def _calculate_arousal_correlation(self, emotions_a: List[EmotionalState], 
                                          emotions_b: List[EmotionalState]) -> float:
        """Calculate arousal correlation between participants"""
        return np.random.uniform(0.5, 0.8)  # Stub