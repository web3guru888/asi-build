"""
Fortune Manipulator

Advanced system for manipulating luck, fortune, serendipity, and random
chance to bias probability outcomes in favor of desired results.
"""

import numpy as np
import logging
import math
import time
import random
from typing import Dict, List, Tuple, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor


class LuckType(Enum):
    """Types of luck that can be manipulated."""
    GOOD_FORTUNE = "good_fortune"
    BAD_LUCK = "bad_luck"
    SERENDIPITY = "serendipity"
    SYNCHRONICITY = "synchronicity"
    KARMIC_LUCK = "karmic_luck"
    RANDOM_CHANCE = "random_chance"
    PROBABILITY_BIAS = "probability_bias"
    FORTUNE_REVERSAL = "fortune_reversal"


class FortuneScope(Enum):
    """Scope of fortune manipulation."""
    PERSONAL = "personal"
    LOCAL = "local"
    REGIONAL = "regional"
    GLOBAL = "global"
    UNIVERSAL = "universal"
    DIMENSIONAL = "dimensional"


@dataclass
class LuckField:
    """Represents a field of luck manipulation."""
    field_id: str
    luck_type: LuckType
    target_entity: str
    field_strength: float
    field_radius: float
    center_coordinates: Tuple[float, float, float]
    bias_direction: float  # -1 (bad luck) to +1 (good luck)
    duration: float
    decay_rate: float
    creation_time: float
    expiration_time: float
    affected_events: Set[str] = field(default_factory=set)
    manipulation_count: int = 0
    cumulative_effect: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FortuneEvent:
    """Represents a fortunate or unfortunate event."""
    event_id: str
    event_description: str
    base_probability: float
    manipulated_probability: float
    luck_modifier: float
    fortune_score: float  # -1 (very unlucky) to +1 (very lucky)
    event_magnitude: float
    temporal_window: Tuple[float, float]
    luck_fields_affecting: List[str]
    serendipity_factor: float
    timestamp: float


@dataclass
class FortuneManipulationResult:
    """Result of a fortune manipulation operation."""
    manipulation_id: str
    field_id: str
    target_entity: str
    original_luck_level: float
    target_luck_level: float
    achieved_luck_level: float
    manipulation_strength: float
    duration: float
    affected_events: List[str]
    serendipity_generated: int
    probability_shifts: Dict[str, float]
    karmic_balance_impact: float
    success_confidence: float
    timestamp: float


class FortuneManipulator:
    """
    Advanced luck and fortune manipulation system.
    
    This system creates and manages fields of luck that bias random
    events and probability outcomes, generating serendipity, synchronicity,
    and favorable circumstances for targeted entities.
    """
    
    def __init__(self, enable_karmic_tracking: bool = True):
        self.logger = logging.getLogger(__name__)
        self.enable_karmic_tracking = enable_karmic_tracking
        
        # Core system state
        self.luck_fields: Dict[str, LuckField] = {}
        self.fortune_events: Dict[str, FortuneEvent] = {}
        self.manipulation_history: List[FortuneManipulationResult] = []
        
        # Threading and synchronization
        self.fortune_lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # System parameters
        self.max_field_strength = 1.0
        self.max_simultaneous_fields = 100
        self.serendipity_threshold = 0.7
        self.synchronicity_window = 300.0  # 5 minutes
        
        # Luck constants
        self.GOLDEN_RATIO = 1.618033988749
        self.LUCK_DECAY_RATE = 0.001
        self.PROBABILITY_SENSITIVITY = 0.1
        self.SERENDIPITY_MULTIPLIER = 1.5
        
        # Fortune tracking
        self.global_luck_level = 0.0
        self.karmic_balance = 0.0
        self.total_fortune_generated = 0.0
        self.active_serendipity_events = 0
        
        # Probability distributions for luck
        self.luck_distribution_cache: Dict[str, np.ndarray] = {}
        self.fortune_history: deque = deque(maxlen=10000)
        
        # Random number generator with luck bias
        self.fortune_rng = random.SystemRandom()
        
        self.logger.info("FortuneManipulator initialized with karmic tracking")
    
    def create_luck_field(
        self,
        target_entity: str,
        luck_type: LuckType,
        field_strength: float,
        field_radius: float = 100.0,
        coordinates: Optional[Tuple[float, float, float]] = None,
        duration: float = 3600.0
    ) -> str:
        """
        Create a field of luck around a target entity.
        
        Args:
            target_entity: Entity to center luck field on
            luck_type: Type of luck to generate
            field_strength: Strength of the luck field (0-1)
            field_radius: Radius of effect in meters
            coordinates: Center coordinates (x, y, z)
            duration: Duration of the field in seconds
            
        Returns:
            Luck field ID
        """
        with self.fortune_lock:
            if len(self.luck_fields) >= self.max_simultaneous_fields:
                self._cleanup_expired_fields()
                
                if len(self.luck_fields) >= self.max_simultaneous_fields:
                    raise ValueError("Maximum number of luck fields reached")
            
            field_id = f"lf_{luck_type.value}_{int(time.time() * 1000000)}"
            
            if coordinates is None:
                coordinates = (0.0, 0.0, 0.0)  # Default coordinates
            
            # Validate and normalize parameters
            field_strength = max(0.0, min(self.max_field_strength, field_strength))
            
            # Calculate bias direction
            bias_direction = self._calculate_bias_direction(luck_type, field_strength)
            
            # Calculate decay rate
            decay_rate = self.LUCK_DECAY_RATE * (1.0 + field_strength)
            
            field = LuckField(
                field_id=field_id,
                luck_type=luck_type,
                target_entity=target_entity,
                field_strength=field_strength,
                field_radius=field_radius,
                center_coordinates=coordinates,
                bias_direction=bias_direction,
                duration=duration,
                decay_rate=decay_rate,
                creation_time=time.time(),
                expiration_time=time.time() + duration
            )
            
            self.luck_fields[field_id] = field
            
            self.logger.info(f"Created luck field {field_id} for {target_entity}: {luck_type.value}")
            return field_id
    
    def manipulate_fortune(
        self,
        field_id: str,
        target_luck_level: float,
        manipulation_strength: float = 0.5,
        duration: float = 3600.0
    ) -> FortuneManipulationResult:
        """
        Manipulate fortune within a luck field.
        
        Args:
            field_id: ID of the luck field to manipulate
            target_luck_level: Desired luck level (-1 to +1)
            manipulation_strength: Strength of manipulation (0-1)
            duration: Duration of manipulation
            
        Returns:
            FortuneManipulationResult with operation details
        """
        with self.fortune_lock:
            if field_id not in self.luck_fields:
                raise ValueError(f"Luck field {field_id} not found")
            
            field = self.luck_fields[field_id]
            manipulation_id = f"fm_{int(time.time() * 1000000)}"
            
            # Calculate current luck level
            original_luck_level = self._calculate_current_luck_level(field)
            
            # Validate target luck level
            target_luck_level = max(-1.0, min(1.0, target_luck_level))
            manipulation_strength = max(0.0, min(1.0, manipulation_strength))
            
            # Calculate actual luck change
            luck_delta = target_luck_level - original_luck_level
            actual_delta = luck_delta * manipulation_strength * field.field_strength
            
            # Apply temporal factors
            time_factor = self._calculate_temporal_factor(field, duration)
            actual_delta *= time_factor
            
            achieved_luck_level = original_luck_level + actual_delta
            achieved_luck_level = max(-1.0, min(1.0, achieved_luck_level))
            
            # Update field bias
            field.bias_direction = achieved_luck_level
            field.manipulation_count += 1
            field.cumulative_effect += abs(actual_delta)
            
            # Generate fortune events
            affected_events = self._generate_fortune_events(
                field, original_luck_level, achieved_luck_level, duration
            )
            
            # Calculate serendipity
            serendipity_generated = self._calculate_serendipity_generation(
                field, luck_delta, manipulation_strength
            )
            
            # Calculate probability shifts
            probability_shifts = self._calculate_probability_shifts(
                field, achieved_luck_level, duration
            )
            
            # Calculate karmic impact
            karmic_impact = 0.0
            if self.enable_karmic_tracking:
                karmic_impact = self._calculate_karmic_impact(
                    luck_delta, manipulation_strength, field.luck_type
                )
                self.karmic_balance += karmic_impact
            
            # Update global luck level
            self._update_global_luck_level(actual_delta, field.field_strength)
            
            # Calculate success confidence
            success_confidence = self._calculate_manipulation_confidence(
                original_luck_level, target_luck_level, achieved_luck_level
            )
            
            # Create result
            result = FortuneManipulationResult(
                manipulation_id=manipulation_id,
                field_id=field_id,
                target_entity=field.target_entity,
                original_luck_level=original_luck_level,
                target_luck_level=target_luck_level,
                achieved_luck_level=achieved_luck_level,
                manipulation_strength=manipulation_strength,
                duration=duration,
                affected_events=[event.event_id for event in affected_events],
                serendipity_generated=serendipity_generated,
                probability_shifts=probability_shifts,
                karmic_balance_impact=karmic_impact,
                success_confidence=success_confidence,
                timestamp=time.time()
            )
            
            self.manipulation_history.append(result)
            
            # Record in fortune history
            self.fortune_history.append({
                'timestamp': time.time(),
                'luck_level': achieved_luck_level,
                'field_id': field_id,
                'manipulation_id': manipulation_id
            })
            
            self.logger.info(
                f"Manipulated fortune in field {field_id}: {original_luck_level:.3f} -> {achieved_luck_level:.3f}"
            )
            
            return result
    
    def generate_serendipity_event(
        self,
        target_entity: str,
        event_description: str,
        magnitude: float = 0.8,
        probability_boost: float = 0.3
    ) -> str:
        """
        Generate a serendipitous event for a target entity.
        
        Args:
            target_entity: Entity to benefit from serendipity
            event_description: Description of the serendipitous event
            magnitude: Magnitude of the serendipitous effect
            probability_boost: Boost to event probability
            
        Returns:
            Serendipity event ID
        """
        event_id = f"se_{int(time.time() * 1000000)}"
        
        # Calculate serendipity timing
        temporal_window = (
            time.time(),
            time.time() + self.synchronicity_window
        )
        
        # Create fortune event
        fortune_event = FortuneEvent(
            event_id=event_id,
            event_description=event_description,
            base_probability=0.1,  # Serendipity is naturally rare
            manipulated_probability=0.1 + probability_boost,
            luck_modifier=magnitude,
            fortune_score=magnitude,
            event_magnitude=magnitude,
            temporal_window=temporal_window,
            luck_fields_affecting=[],
            serendipity_factor=1.0,
            timestamp=time.time()
        )
        
        self.fortune_events[event_id] = fortune_event
        self.active_serendipity_events += 1
        
        # Create temporary luck field for serendipity
        luck_field_id = self.create_luck_field(
            target_entity=target_entity,
            luck_type=LuckType.SERENDIPITY,
            field_strength=magnitude,
            field_radius=50.0,
            duration=self.synchronicity_window
        )
        
        fortune_event.luck_fields_affecting.append(luck_field_id)
        
        self.logger.info(f"Generated serendipity event {event_id} for {target_entity}")
        return event_id
    
    def create_synchronicity_pattern(
        self,
        entities: List[str],
        pattern_type: str,
        strength: float = 0.6
    ) -> str:
        """
        Create a synchronicity pattern affecting multiple entities.
        
        Args:
            entities: List of entities to connect through synchronicity
            pattern_type: Type of synchronicity pattern
            strength: Strength of the synchronicity connection
            
        Returns:
            Synchronicity pattern ID
        """
        pattern_id = f"sync_{pattern_type}_{int(time.time() * 1000000)}"
        
        # Create interconnected luck fields
        field_ids = []
        for entity in entities:
            field_id = self.create_luck_field(
                target_entity=entity,
                luck_type=LuckType.SYNCHRONICITY,
                field_strength=strength,
                field_radius=200.0,
                duration=3600.0
            )
            field_ids.append(field_id)
        
        # Link the fields through metadata
        for field_id in field_ids:
            field = self.luck_fields[field_id]
            field.metadata['synchronicity_pattern'] = pattern_id
            field.metadata['connected_fields'] = [fid for fid in field_ids if fid != field_id]
        
        self.logger.info(f"Created synchronicity pattern {pattern_id} for {len(entities)} entities")
        return pattern_id
    
    def bias_random_events(
        self,
        event_types: List[str],
        bias_strength: float,
        target_entity: Optional[str] = None,
        duration: float = 3600.0
    ) -> Dict[str, float]:
        """
        Bias random events in favor of desired outcomes.
        
        Args:
            event_types: Types of events to bias
            bias_strength: Strength of bias (-1 to +1)
            target_entity: Specific entity to bias for (None for global)
            duration: Duration of bias effect
            
        Returns:
            Dictionary of event types and their bias adjustments
        """
        bias_adjustments = {}
        
        for event_type in event_types:
            # Create probability bias for this event type
            adjustment = self._calculate_event_bias_adjustment(
                event_type, bias_strength, duration
            )
            
            bias_adjustments[event_type] = adjustment
            
            # Create luck field if targeting specific entity
            if target_entity:
                field_id = self.create_luck_field(
                    target_entity=target_entity,
                    luck_type=LuckType.PROBABILITY_BIAS,
                    field_strength=abs(bias_strength),
                    duration=duration
                )
                
                # Configure field for event type bias
                field = self.luck_fields[field_id]
                field.metadata['biased_event_types'] = [event_type]
                field.metadata['bias_adjustment'] = adjustment
        
        self.logger.info(f"Biased {len(event_types)} event types with strength {bias_strength}")
        return bias_adjustments
    
    def reverse_fortune(
        self,
        target_entity: str,
        reversal_strength: float = 0.8,
        duration: float = 1800.0
    ) -> str:
        """
        Reverse the fortune of a target entity (good luck becomes bad, bad becomes good).
        
        Args:
            target_entity: Entity whose fortune to reverse
            reversal_strength: Strength of the reversal (0-1)
            duration: Duration of the reversal effect
            
        Returns:
            Fortune reversal ID
        """
        reversal_id = self.create_luck_field(
            target_entity=target_entity,
            luck_type=LuckType.FORTUNE_REVERSAL,
            field_strength=reversal_strength,
            duration=duration
        )
        
        # Configure reversal field
        field = self.luck_fields[reversal_id]
        field.metadata['reversal_active'] = True
        field.metadata['reversal_strength'] = reversal_strength
        
        # Apply immediate reversal to existing luck
        current_luck = self._calculate_current_luck_level(field)
        reversed_luck = -current_luck * reversal_strength
        
        self.manipulate_fortune(
            field_id=reversal_id,
            target_luck_level=reversed_luck,
            manipulation_strength=reversal_strength,
            duration=duration
        )
        
        self.logger.info(f"Reversed fortune for {target_entity} with strength {reversal_strength}")
        return reversal_id
    
    def analyze_luck_patterns(
        self,
        target_entity: str,
        analysis_period: float = 86400.0
    ) -> Dict[str, Any]:
        """
        Analyze luck patterns for a target entity.
        
        Args:
            target_entity: Entity to analyze
            analysis_period: Period to analyze in seconds
            
        Returns:
            Luck pattern analysis
        """
        # Collect relevant data
        relevant_events = []
        relevant_manipulations = []
        
        cutoff_time = time.time() - analysis_period
        
        for event in self.fortune_events.values():
            if (event.timestamp > cutoff_time and 
                target_entity in event.event_description):
                relevant_events.append(event)
        
        for manipulation in self.manipulation_history:
            if (manipulation.timestamp > cutoff_time and 
                manipulation.target_entity == target_entity):
                relevant_manipulations.append(manipulation)
        
        # Calculate statistics
        if relevant_events:
            avg_fortune_score = sum(event.fortune_score for event in relevant_events) / len(relevant_events)
            luck_variance = np.var([event.fortune_score for event in relevant_events])
            serendipity_count = sum(1 for event in relevant_events if event.serendipity_factor > 0.5)
        else:
            avg_fortune_score = 0.0
            luck_variance = 0.0
            serendipity_count = 0
        
        # Find patterns
        luck_trends = self._find_luck_trends(relevant_events)
        synchronicity_score = self._calculate_synchronicity_score(relevant_events)
        karmic_balance_impact = sum(manip.karmic_balance_impact for manip in relevant_manipulations)
        
        return {
            'target_entity': target_entity,
            'analysis_period': analysis_period,
            'total_events': len(relevant_events),
            'total_manipulations': len(relevant_manipulations),
            'average_fortune_score': avg_fortune_score,
            'luck_variance': luck_variance,
            'serendipity_events': serendipity_count,
            'synchronicity_score': synchronicity_score,
            'luck_trends': luck_trends,
            'karmic_balance_impact': karmic_balance_impact,
            'current_luck_level': self._get_entity_current_luck(target_entity)
        }
    
    def get_field_status(self, field_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive status of a luck field."""
        if field_id not in self.luck_fields:
            return None
        
        field = self.luck_fields[field_id]
        
        # Calculate field effectiveness
        effectiveness = self._calculate_field_effectiveness(field)
        
        # Calculate remaining duration
        remaining_duration = max(0, field.expiration_time - time.time())
        
        return {
            'field_id': field.field_id,
            'luck_type': field.luck_type.value,
            'target_entity': field.target_entity,
            'field_strength': field.field_strength,
            'field_radius': field.field_radius,
            'bias_direction': field.bias_direction,
            'remaining_duration': remaining_duration,
            'manipulation_count': field.manipulation_count,
            'cumulative_effect': field.cumulative_effect,
            'affected_events': len(field.affected_events),
            'field_effectiveness': effectiveness,
            'age': time.time() - field.creation_time
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive fortune manipulation system status."""
        total_fields = len(self.luck_fields)
        total_events = len(self.fortune_events)
        total_manipulations = len(self.manipulation_history)
        
        # Calculate field type distribution
        field_type_counts = defaultdict(int)
        for field in self.luck_fields.values():
            field_type_counts[field.luck_type.value] += 1
        
        # Calculate average luck level
        if self.fortune_history:
            recent_luck_levels = [entry['luck_level'] for entry in list(self.fortune_history)[-100:]]
            average_luck_level = sum(recent_luck_levels) / len(recent_luck_levels)
        else:
            average_luck_level = 0.0
        
        # Calculate system effectiveness
        if total_manipulations > 0:
            successful_manipulations = sum(
                1 for manip in self.manipulation_history
                if manip.success_confidence > 0.7
            )
            system_effectiveness = successful_manipulations / total_manipulations
        else:
            system_effectiveness = 0.0
        
        return {
            'total_luck_fields': total_fields,
            'total_fortune_events': total_events,
            'total_manipulations': total_manipulations,
            'active_serendipity_events': self.active_serendipity_events,
            'global_luck_level': self.global_luck_level,
            'karmic_balance': self.karmic_balance,
            'average_luck_level': average_luck_level,
            'system_effectiveness': system_effectiveness,
            'field_type_distribution': dict(field_type_counts),
            'total_fortune_generated': self.total_fortune_generated,
            'enable_karmic_tracking': self.enable_karmic_tracking,
            'uptime': time.time()
        }
    
    # Private helper methods
    
    def _calculate_bias_direction(self, luck_type: LuckType, strength: float) -> float:
        """Calculate bias direction based on luck type."""
        bias_map = {
            LuckType.GOOD_FORTUNE: 1.0,
            LuckType.BAD_LUCK: -1.0,
            LuckType.SERENDIPITY: 0.8,
            LuckType.SYNCHRONICITY: 0.5,
            LuckType.KARMIC_LUCK: 0.0,  # Neutral, depends on karma
            LuckType.RANDOM_CHANCE: 0.0,
            LuckType.PROBABILITY_BIAS: 0.6,
            LuckType.FORTUNE_REVERSAL: 0.0  # Will be set dynamically
        }
        
        base_bias = bias_map.get(luck_type, 0.0)
        return base_bias * strength
    
    def _calculate_current_luck_level(self, field: LuckField) -> float:
        """Calculate current luck level of a field."""
        # Start with bias direction
        luck_level = field.bias_direction
        
        # Apply decay over time
        age = time.time() - field.creation_time
        decay_factor = math.exp(-age * field.decay_rate)
        luck_level *= decay_factor
        
        # Apply field strength
        luck_level *= field.field_strength
        
        return max(-1.0, min(1.0, luck_level))
    
    def _calculate_temporal_factor(self, field: LuckField, duration: float) -> float:
        """Calculate temporal effectiveness factor."""
        # Effectiveness decreases over time
        age = time.time() - field.creation_time
        age_factor = math.exp(-age / field.duration * 0.5)
        
        # Duration factor
        duration_factor = min(1.0, duration / 3600.0)  # Normalize by hour
        
        return age_factor * duration_factor
    
    def _generate_fortune_events(
        self,
        field: LuckField,
        old_luck: float,
        new_luck: float,
        duration: float
    ) -> List[FortuneEvent]:
        """Generate fortune events based on luck manipulation."""
        events = []
        luck_change = abs(new_luck - old_luck)
        
        # Number of events proportional to luck change
        num_events = int(luck_change * 10 * field.field_strength)
        num_events = min(20, max(1, num_events))  # Limit event generation
        
        for i in range(num_events):
            event_id = f"fe_{field.field_id}_{i}_{int(time.time() * 1000000)}"
            
            # Generate event properties
            base_prob = 0.1 + self.fortune_rng.random() * 0.3
            manipulation_factor = new_luck * 0.2
            manipulated_prob = max(0.0, min(1.0, base_prob + manipulation_factor))
            
            fortune_score = new_luck * (0.5 + self.fortune_rng.random() * 0.5)
            magnitude = luck_change * field.field_strength
            
            event = FortuneEvent(
                event_id=event_id,
                event_description=f"Fortune event for {field.target_entity}",
                base_probability=base_prob,
                manipulated_probability=manipulated_prob,
                luck_modifier=manipulation_factor,
                fortune_score=fortune_score,
                event_magnitude=magnitude,
                temporal_window=(time.time(), time.time() + duration),
                luck_fields_affecting=[field.field_id],
                serendipity_factor=max(0, new_luck * 0.8),
                timestamp=time.time()
            )
            
            events.append(event)
            self.fortune_events[event_id] = event
            field.affected_events.add(event_id)
        
        return events
    
    def _calculate_serendipity_generation(
        self,
        field: LuckField,
        luck_delta: float,
        strength: float
    ) -> int:
        """Calculate how many serendipitous events to generate."""
        # Serendipity increases with positive luck changes
        if luck_delta > 0 and field.luck_type in [LuckType.GOOD_FORTUNE, LuckType.SERENDIPITY]:
            serendipity_factor = luck_delta * strength * self.SERENDIPITY_MULTIPLIER
            return int(serendipity_factor * 5)  # Up to 5 serendipitous events
        
        return 0
    
    def _calculate_probability_shifts(
        self,
        field: LuckField,
        luck_level: float,
        duration: float
    ) -> Dict[str, float]:
        """Calculate probability shifts for various event types."""
        shifts = {}
        
        # Base shift proportional to luck level
        base_shift = luck_level * self.PROBABILITY_SENSITIVITY
        
        # Different event types affected differently
        event_types = [
            'financial_gain', 'opportunity_discovery', 'relationship_success',
            'health_improvement', 'creative_inspiration', 'problem_resolution'
        ]
        
        for event_type in event_types:
            # Add some randomness and type-specific modifiers
            type_modifier = 0.8 + self.fortune_rng.random() * 0.4
            shift = base_shift * type_modifier * field.field_strength
            shifts[event_type] = shift
        
        return shifts
    
    def _calculate_karmic_impact(
        self,
        luck_delta: float,
        strength: float,
        luck_type: LuckType
    ) -> float:
        """Calculate karmic impact of luck manipulation."""
        base_impact = abs(luck_delta) * strength
        
        # Different luck types have different karmic costs
        karmic_multipliers = {
            LuckType.GOOD_FORTUNE: 1.0,
            LuckType.BAD_LUCK: -1.5,  # Creating bad luck has negative karma
            LuckType.SERENDIPITY: 0.5,
            LuckType.SYNCHRONICITY: 0.3,
            LuckType.KARMIC_LUCK: 0.0,  # Balances itself
            LuckType.RANDOM_CHANCE: 0.8,
            LuckType.PROBABILITY_BIAS: 1.2,
            LuckType.FORTUNE_REVERSAL: 0.1  # Minimal karmic impact
        }
        
        multiplier = karmic_multipliers.get(luck_type, 1.0)
        return base_impact * multiplier
    
    def _update_global_luck_level(self, delta: float, field_strength: float) -> None:
        """Update global luck level based on manipulation."""
        # Global luck influenced by all manipulations
        influence = delta * field_strength * 0.01  # Small global influence
        self.global_luck_level += influence
        
        # Keep global luck in reasonable bounds
        self.global_luck_level = max(-2.0, min(2.0, self.global_luck_level))
        
        # Natural decay toward neutral
        self.global_luck_level *= 0.999
    
    def _calculate_manipulation_confidence(
        self,
        original: float,
        target: float,
        achieved: float
    ) -> float:
        """Calculate confidence in manipulation success."""
        if target == original:
            return 1.0
        
        target_delta = abs(target - original)
        achieved_delta = abs(achieved - original)
        
        if target_delta == 0:
            return 1.0
        
        # Confidence based on how close we got to target
        confidence = min(1.0, achieved_delta / target_delta)
        
        # Reduce confidence if we overshot significantly
        if achieved_delta > target_delta * 1.2:
            confidence *= 0.8
        
        return confidence
    
    def _calculate_event_bias_adjustment(
        self,
        event_type: str,
        bias_strength: float,
        duration: float
    ) -> float:
        """Calculate bias adjustment for a specific event type."""
        # Base adjustment
        base_adjustment = bias_strength * self.PROBABILITY_SENSITIVITY
        
        # Duration factor
        duration_factor = min(1.0, duration / 3600.0)  # Normalize by hour
        
        # Event type specific factors
        event_factors = {
            'financial': 1.2,
            'social': 1.0,
            'health': 0.8,
            'creative': 1.1,
            'academic': 0.9,
            'romantic': 1.3
        }
        
        # Find matching factor
        factor = 1.0
        for key, value in event_factors.items():
            if key in event_type.lower():
                factor = value
                break
        
        adjustment = base_adjustment * duration_factor * factor
        return max(-0.5, min(0.5, adjustment))  # Limit adjustment range
    
    def _cleanup_expired_fields(self) -> None:
        """Clean up expired luck fields."""
        current_time = time.time()
        expired_fields = []
        
        for field_id, field in self.luck_fields.items():
            if current_time > field.expiration_time:
                expired_fields.append(field_id)
        
        for field_id in expired_fields:
            del self.luck_fields[field_id]
            self.logger.debug(f"Cleaned up expired luck field {field_id}")
    
    def _find_luck_trends(self, events: List[FortuneEvent]) -> Dict[str, Any]:
        """Find trends in luck patterns."""
        if len(events) < 3:
            return {'trend': 'insufficient_data'}
        
        # Sort events by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        # Calculate trend slope
        fortune_scores = [event.fortune_score for event in events]
        timestamps = [event.timestamp for event in events]
        
        # Simple linear regression for trend
        n = len(events)
        sum_x = sum(timestamps)
        sum_y = sum(fortune_scores)
        sum_xy = sum(x * y for x, y in zip(timestamps, fortune_scores))
        sum_x2 = sum(x * x for x in timestamps)
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator != 0:
            slope = (n * sum_xy - sum_x * sum_y) / denominator
        else:
            slope = 0.0
        
        # Classify trend
        if slope > 0.01:
            trend_type = 'improving'
        elif slope < -0.01:
            trend_type = 'declining'
        else:
            trend_type = 'stable'
        
        return {
            'trend': trend_type,
            'slope': slope,
            'confidence': min(1.0, abs(slope) * 100),
            'data_points': n
        }
    
    def _calculate_synchronicity_score(self, events: List[FortuneEvent]) -> float:
        """Calculate synchronicity score for events."""
        if len(events) < 2:
            return 0.0
        
        # Look for temporal clustering of events
        events.sort(key=lambda e: e.timestamp)
        
        synchronicity_score = 0.0
        for i in range(len(events) - 1):
            time_diff = events[i + 1].timestamp - events[i].timestamp
            
            # Events within synchronicity window contribute to score
            if time_diff <= self.synchronicity_window:
                # Closer events have higher synchronicity
                proximity_factor = 1.0 - (time_diff / self.synchronicity_window)
                fortune_correlation = abs(events[i].fortune_score * events[i + 1].fortune_score)
                synchronicity_score += proximity_factor * fortune_correlation
        
        # Normalize by number of possible pairs
        max_pairs = len(events) * (len(events) - 1) / 2
        if max_pairs > 0:
            synchronicity_score /= max_pairs
        
        return min(1.0, synchronicity_score)
    
    def _get_entity_current_luck(self, entity: str) -> float:
        """Get current luck level for an entity."""
        # Find all active fields affecting this entity
        affecting_fields = [
            field for field in self.luck_fields.values()
            if field.target_entity == entity and time.time() < field.expiration_time
        ]
        
        if not affecting_fields:
            return 0.0
        
        # Combine luck from all fields
        total_luck = 0.0
        total_weight = 0.0
        
        for field in affecting_fields:
            field_luck = self._calculate_current_luck_level(field)
            weight = field.field_strength
            
            total_luck += field_luck * weight
            total_weight += weight
        
        if total_weight > 0:
            return total_luck / total_weight
        else:
            return 0.0
    
    def _calculate_field_effectiveness(self, field: LuckField) -> float:
        """Calculate effectiveness of a luck field."""
        if field.manipulation_count == 0:
            return 0.5  # Neutral for unused fields
        
        # Effectiveness based on cumulative effect vs manipulation count
        efficiency = field.cumulative_effect / field.manipulation_count
        
        # Factor in field age and decay
        age = time.time() - field.creation_time
        age_factor = math.exp(-age * field.decay_rate)
        
        effectiveness = efficiency * field.field_strength * age_factor
        return min(1.0, effectiveness)