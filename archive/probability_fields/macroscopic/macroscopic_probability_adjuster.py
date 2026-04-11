"""
Macroscopic Probability Adjuster

Advanced system for manipulating probability distributions at macroscopic scales,
affecting real-world events, outcomes, and large-scale statistical patterns.
"""

import numpy as np
import logging
import math
import statistics
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum
import threading
import time
import random
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor
import asyncio


class EventType(Enum):
    """Types of macroscopic events that can be influenced."""
    RANDOM_EVENT = "random_event"
    DECISION_OUTCOME = "decision_outcome"
    STATISTICAL_TREND = "statistical_trend"
    MARKET_MOVEMENT = "market_movement"
    WEATHER_PATTERN = "weather_pattern"
    SOCIAL_BEHAVIOR = "social_behavior"
    TECHNOLOGICAL_DEVELOPMENT = "technological_development"
    BIOLOGICAL_PROCESS = "biological_process"


class AdjustmentMethod(Enum):
    """Methods for adjusting macroscopic probabilities."""
    BIAS_INJECTION = "bias_injection"
    TREND_AMPLIFICATION = "trend_amplification"
    VARIANCE_REDUCTION = "variance_reduction"
    CORRELATION_ENHANCEMENT = "correlation_enhancement"
    STATISTICAL_CONDITIONING = "statistical_conditioning"
    MONTE_CARLO_MODIFICATION = "monte_carlo_modification"
    BAYESIAN_UPDATE = "bayesian_update"
    REGRESSION_ADJUSTMENT = "regression_adjustment"


@dataclass
class MacroscopicEvent:
    """Represents a macroscopic event with probability characteristics."""
    event_id: str
    event_type: EventType
    description: str
    base_probability: float
    current_probability: float
    confidence_interval: Tuple[float, float]
    sample_size: int
    adjustment_history: List[Dict[str, Any]]
    creation_time: float
    last_modified: float
    metadata: Dict[str, Any]


@dataclass
class AdjustmentResult:
    """Result of a macroscopic probability adjustment."""
    adjustment_id: str
    event_id: str
    method: AdjustmentMethod
    original_probability: float
    target_probability: float
    achieved_probability: float
    confidence_score: float
    statistical_significance: float
    sample_size_change: int
    adjustment_strength: float
    side_effects: List[str]
    timestamp: float


class MacroscopicProbabilityAdjuster:
    """
    Advanced macroscopic probability manipulation system.
    
    This system manipulates probability distributions at large scales,
    affecting real-world events, statistical trends, and outcomes
    through various statistical and probabilistic techniques.
    """
    
    def __init__(self, max_adjustment_strength: float = 0.3):
        self.logger = logging.getLogger(__name__)
        self.max_adjustment_strength = max_adjustment_strength
        
        # System state
        self.active_events: Dict[str, MacroscopicEvent] = {}
        self.adjustment_history: List[AdjustmentResult] = []
        self.system_lock = threading.RLock()
        
        # Statistical tracking
        self.probability_distributions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.correlation_matrix: Dict[Tuple[str, str], float] = {}
        self.trend_analysis: Dict[str, List[float]] = defaultdict(list)
        
        # Adjustment parameters
        self.minimum_sample_size = 100
        self.maximum_sample_size = 1000000
        self.confidence_threshold = 0.95
        self.significance_level = 0.05
        self.adjustment_decay_rate = 0.01
        
        # Statistical constants
        self.NORMAL_APPROXIMATION_THRESHOLD = 30
        self.CHI_SQUARE_CRITICAL_VALUE = 3.841  # p=0.05, df=1
        self.T_DISTRIBUTION_CRITICAL = 1.96     # 95% confidence
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        self.logger.info("MacroscopicProbabilityAdjuster initialized")
    
    def register_event(
        self,
        event_type: EventType,
        description: str,
        base_probability: float,
        initial_sample_size: int = 1000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a new macroscopic event for probability manipulation.
        
        Args:
            event_type: Type of the event
            description: Human-readable description
            base_probability: Initial probability estimate
            initial_sample_size: Initial sample size for statistics
            metadata: Additional event metadata
            
        Returns:
            Event ID string
        """
        with self.system_lock:
            event_id = f"me_{event_type.value}_{int(time.time() * 1000000)}"
            
            # Validate probability
            probability = max(0.0, min(1.0, base_probability))
            
            # Calculate confidence interval
            confidence_interval = self._calculate_confidence_interval(
                probability, initial_sample_size
            )
            
            event = MacroscopicEvent(
                event_id=event_id,
                event_type=event_type,
                description=description,
                base_probability=probability,
                current_probability=probability,
                confidence_interval=confidence_interval,
                sample_size=initial_sample_size,
                adjustment_history=[],
                creation_time=time.time(),
                last_modified=time.time(),
                metadata=metadata or {}
            )
            
            self.active_events[event_id] = event
            
            # Initialize probability tracking
            self.probability_distributions[event_id].append(probability)
            
            self.logger.info(f"Registered event {event_id}: {description}")
            return event_id
    
    def adjust_event_probability(
        self,
        event_id: str,
        target_probability: float,
        method: AdjustmentMethod = AdjustmentMethod.BIAS_INJECTION,
        adjustment_strength: float = 0.1,
        duration: float = 3600.0
    ) -> AdjustmentResult:
        """
        Adjust the probability of a macroscopic event.
        
        Args:
            event_id: ID of the event to adjust
            target_probability: Desired probability value
            method: Method of adjustment
            adjustment_strength: Strength of the adjustment (0-1)
            duration: Duration of adjustment effect in seconds
            
        Returns:
            AdjustmentResult with operation details
        """
        with self.system_lock:
            if event_id not in self.active_events:
                raise ValueError(f"Event {event_id} not found")
            
            event = self.active_events[event_id]
            adjustment_id = f"adj_{int(time.time() * 1000000)}"
            
            # Validate parameters
            target_probability = max(0.0, min(1.0, target_probability))
            adjustment_strength = max(0.0, min(self.max_adjustment_strength, adjustment_strength))
            
            original_probability = event.current_probability
            
            # Perform adjustment based on method
            achieved_probability, confidence_score, significance = self._perform_adjustment(
                event, target_probability, method, adjustment_strength
            )
            
            # Calculate side effects
            side_effects = self._analyze_side_effects(
                event, original_probability, achieved_probability, adjustment_strength
            )
            
            # Update event
            event.current_probability = achieved_probability
            event.last_modified = time.time()
            
            # Update confidence interval
            event.confidence_interval = self._calculate_confidence_interval(
                achieved_probability, event.sample_size
            )
            
            # Track probability change
            self.probability_distributions[event_id].append(achieved_probability)
            
            # Record adjustment
            adjustment_record = {
                'adjustment_id': adjustment_id,
                'method': method.value,
                'target_probability': target_probability,
                'achieved_probability': achieved_probability,
                'adjustment_strength': adjustment_strength,
                'duration': duration,
                'timestamp': time.time()
            }
            event.adjustment_history.append(adjustment_record)
            
            # Create result
            result = AdjustmentResult(
                adjustment_id=adjustment_id,
                event_id=event_id,
                method=method,
                original_probability=original_probability,
                target_probability=target_probability,
                achieved_probability=achieved_probability,
                confidence_score=confidence_score,
                statistical_significance=significance,
                sample_size_change=0,
                adjustment_strength=adjustment_strength,
                side_effects=side_effects,
                timestamp=time.time()
            )
            
            self.adjustment_history.append(result)
            
            self.logger.info(
                f"Adjusted event {event_id}: {original_probability:.4f} -> {achieved_probability:.4f}"
            )
            
            return result
    
    def create_probability_trend(
        self,
        event_id: str,
        trend_function: Callable[[float], float],
        duration: float = 3600.0,
        sample_interval: float = 60.0
    ) -> str:
        """
        Create a time-based probability trend for an event.
        
        Args:
            event_id: ID of the event
            trend_function: Function defining probability over time
            duration: Total duration of the trend
            sample_interval: Interval between trend updates
            
        Returns:
            Trend ID string
        """
        if event_id not in self.active_events:
            raise ValueError(f"Event {event_id} not found")
        
        trend_id = f"trend_{event_id}_{int(time.time() * 1000000)}"
        
        # Schedule trend updates
        def apply_trend():
            start_time = time.time()
            step = 0
            
            while (time.time() - start_time) < duration:
                current_time = time.time() - start_time
                relative_time = current_time / duration
                
                # Calculate new probability from trend function
                new_probability = trend_function(relative_time)
                new_probability = max(0.0, min(1.0, new_probability))
                
                # Apply gradual adjustment
                self.adjust_event_probability(
                    event_id=event_id,
                    target_probability=new_probability,
                    method=AdjustmentMethod.TREND_AMPLIFICATION,
                    adjustment_strength=0.05
                )
                
                # Store trend data
                self.trend_analysis[trend_id].append(new_probability)
                
                step += 1
                time.sleep(sample_interval)
        
        # Start trend in background
        self.executor.submit(apply_trend)
        
        self.logger.info(f"Created probability trend {trend_id} for event {event_id}")
        return trend_id
    
    def correlate_events(
        self,
        event_id1: str,
        event_id2: str,
        correlation_strength: float = 0.5,
        correlation_type: str = "positive"
    ) -> bool:
        """
        Create correlation between two events' probabilities.
        
        Args:
            event_id1: First event ID
            event_id2: Second event ID
            correlation_strength: Strength of correlation (0-1)
            correlation_type: "positive" or "negative"
            
        Returns:
            True if correlation created successfully
        """
        with self.system_lock:
            if event_id1 not in self.active_events or event_id2 not in self.active_events:
                return False
            
            # Store correlation
            correlation_key = (event_id1, event_id2)
            correlation_value = correlation_strength if correlation_type == "positive" else -correlation_strength
            
            self.correlation_matrix[correlation_key] = correlation_value
            self.correlation_matrix[(event_id2, event_id1)] = correlation_value
            
            self.logger.info(f"Created {correlation_type} correlation between {event_id1} and {event_id2}")
            return True
    
    def apply_statistical_conditioning(
        self,
        event_id: str,
        conditioning_events: List[str],
        conditional_probabilities: Dict[str, float]
    ) -> bool:
        """
        Apply conditional probability adjustments based on other events.
        
        Args:
            event_id: Event to condition
            conditioning_events: List of conditioning event IDs
            conditional_probabilities: Mapping of conditions to probabilities
            
        Returns:
            True if conditioning applied successfully
        """
        if event_id not in self.active_events:
            return False
        
        event = self.active_events[event_id]
        
        # Calculate conditional probability
        # P(A|B) = P(A∩B) / P(B)
        conditional_prob = event.base_probability
        
        for cond_event_id in conditioning_events:
            if cond_event_id in self.active_events:
                cond_event = self.active_events[cond_event_id]
                cond_key = f"{cond_event_id}=true"
                
                if cond_key in conditional_probabilities:
                    # Apply Bayesian update
                    prior = conditional_prob
                    likelihood = conditional_probabilities[cond_key]
                    evidence = cond_event.current_probability
                    
                    if evidence > 0:
                        posterior = (likelihood * prior) / evidence
                        conditional_prob = max(0.0, min(1.0, posterior))
        
        # Apply the conditional probability
        self.adjust_event_probability(
            event_id=event_id,
            target_probability=conditional_prob,
            method=AdjustmentMethod.BAYESIAN_UPDATE,
            adjustment_strength=0.1
        )
        
        self.logger.info(f"Applied statistical conditioning to event {event_id}")
        return True
    
    def generate_statistical_field(
        self,
        center_coordinates: Tuple[float, float],
        field_radius: float,
        probability_gradient: Callable[[float], float],
        event_density: int = 100
    ) -> List[str]:
        """
        Generate a field of correlated probability events in a spatial region.
        
        Args:
            center_coordinates: (x, y) center of the field
            field_radius: Radius of the probability field
            probability_gradient: Function defining probability by distance
            event_density: Number of events to create in the field
            
        Returns:
            List of created event IDs
        """
        created_events = []
        center_x, center_y = center_coordinates
        
        for i in range(event_density):
            # Generate random position within field
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, field_radius)
            
            x = center_x + distance * math.cos(angle)
            y = center_y + distance * math.sin(angle)
            
            # Calculate probability based on distance
            normalized_distance = distance / field_radius
            probability = probability_gradient(normalized_distance)
            
            # Create event
            event_id = self.register_event(
                event_type=EventType.STATISTICAL_TREND,
                description=f"Field event at ({x:.2f}, {y:.2f})",
                base_probability=probability,
                metadata={
                    'coordinates': (x, y),
                    'distance_from_center': distance,
                    'field_id': f"field_{int(time.time())}"
                }
            )
            
            created_events.append(event_id)
        
        # Create correlations between nearby events
        self._create_spatial_correlations(created_events, field_radius)
        
        self.logger.info(f"Generated probability field with {len(created_events)} events")
        return created_events
    
    def analyze_event_statistics(self, event_id: str) -> Dict[str, Any]:
        """Analyze comprehensive statistics for an event."""
        if event_id not in self.active_events:
            return {}
        
        event = self.active_events[event_id]
        prob_history = list(self.probability_distributions[event_id])
        
        if len(prob_history) < 2:
            return {'error': 'Insufficient data for analysis'}
        
        # Calculate statistics
        mean_prob = statistics.mean(prob_history)
        median_prob = statistics.median(prob_history)
        std_dev = statistics.stdev(prob_history) if len(prob_history) > 1 else 0
        variance = statistics.variance(prob_history) if len(prob_history) > 1 else 0
        
        # Calculate trend
        trend_slope = self._calculate_trend_slope(prob_history)
        
        # Calculate stability
        stability = 1.0 - (std_dev / mean_prob) if mean_prob > 0 else 0
        
        # Calculate adjustment effectiveness
        effectiveness = self._calculate_adjustment_effectiveness(event)
        
        return {
            'event_id': event_id,
            'current_probability': event.current_probability,
            'base_probability': event.base_probability,
            'mean_probability': mean_prob,
            'median_probability': median_prob,
            'standard_deviation': std_dev,
            'variance': variance,
            'trend_slope': trend_slope,
            'stability_score': stability,
            'adjustment_effectiveness': effectiveness,
            'total_adjustments': len(event.adjustment_history),
            'sample_size': event.sample_size,
            'confidence_interval': event.confidence_interval,
            'data_points': len(prob_history)
        }
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        total_events = len(self.active_events)
        total_adjustments = len(self.adjustment_history)
        
        if total_events == 0:
            return {'error': 'No events registered'}
        
        # Calculate system-wide statistics
        all_probabilities = []
        for event in self.active_events.values():
            all_probabilities.append(event.current_probability)
        
        system_mean = statistics.mean(all_probabilities)
        system_std = statistics.stdev(all_probabilities) if len(all_probabilities) > 1 else 0
        
        # Calculate adjustment success rate
        successful_adjustments = sum(
            1 for adj in self.adjustment_history 
            if abs(adj.achieved_probability - adj.target_probability) < 0.05
        )
        success_rate = successful_adjustments / total_adjustments if total_adjustments > 0 else 0
        
        # Event type distribution
        event_type_counts = defaultdict(int)
        for event in self.active_events.values():
            event_type_counts[event.event_type.value] += 1
        
        return {
            'total_events': total_events,
            'total_adjustments': total_adjustments,
            'adjustment_success_rate': success_rate,
            'system_mean_probability': system_mean,
            'system_std_probability': system_std,
            'active_correlations': len(self.correlation_matrix),
            'active_trends': len(self.trend_analysis),
            'event_type_distribution': dict(event_type_counts),
            'max_adjustment_strength': self.max_adjustment_strength,
            'uptime': time.time()
        }
    
    # Private helper methods
    
    def _perform_adjustment(
        self,
        event: MacroscopicEvent,
        target_probability: float,
        method: AdjustmentMethod,
        strength: float
    ) -> Tuple[float, float, float]:
        """Perform the actual probability adjustment."""
        current = event.current_probability
        
        if method == AdjustmentMethod.BIAS_INJECTION:
            # Direct bias toward target
            adjustment = (target_probability - current) * strength
            new_probability = current + adjustment
            
        elif method == AdjustmentMethod.TREND_AMPLIFICATION:
            # Amplify existing trend toward target
            recent_trend = self._calculate_recent_trend(event.event_id)
            trend_factor = 1.0 + (strength * recent_trend)
            new_probability = current * trend_factor
            
        elif method == AdjustmentMethod.VARIANCE_REDUCTION:
            # Reduce variance, move toward mean
            mean_prob = statistics.mean(self.probability_distributions[event.event_id])
            adjustment = (mean_prob - current) * strength * 0.5
            new_probability = current + adjustment
            
        elif method == AdjustmentMethod.CORRELATION_ENHANCEMENT:
            # Adjust based on correlated events
            corr_adjustment = self._calculate_correlation_adjustment(event, strength)
            new_probability = current + corr_adjustment
            
        elif method == AdjustmentMethod.MONTE_CARLO_MODIFICATION:
            # Use Monte Carlo sampling for adjustment
            new_probability = self._monte_carlo_adjustment(current, target_probability, strength)
            
        elif method == AdjustmentMethod.BAYESIAN_UPDATE:
            # Bayesian probability update
            prior = current
            likelihood = target_probability
            evidence = 0.5  # Neutral evidence
            posterior = (likelihood * prior) / evidence if evidence > 0 else current
            new_probability = current + (posterior - current) * strength
            
        else:  # Default: STATISTICAL_CONDITIONING
            new_probability = current + (target_probability - current) * strength
        
        # Ensure probability bounds
        new_probability = max(0.0, min(1.0, new_probability))
        
        # Calculate confidence and significance
        confidence_score = self._calculate_adjustment_confidence(
            event, current, new_probability, strength
        )
        
        statistical_significance = self._calculate_statistical_significance(
            current, new_probability, event.sample_size
        )
        
        return new_probability, confidence_score, statistical_significance
    
    def _calculate_confidence_interval(
        self,
        probability: float,
        sample_size: int,
        confidence_level: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for probability estimate."""
        if sample_size < self.NORMAL_APPROXIMATION_THRESHOLD:
            # Use exact binomial confidence interval
            alpha = 1 - confidence_level
            z_score = 1.96  # 95% confidence
            
            margin_of_error = z_score * math.sqrt((probability * (1 - probability)) / sample_size)
            lower = max(0.0, probability - margin_of_error)
            upper = min(1.0, probability + margin_of_error)
            
        else:
            # Use normal approximation
            z_score = 1.96  # 95% confidence
            standard_error = math.sqrt((probability * (1 - probability)) / sample_size)
            margin_of_error = z_score * standard_error
            
            lower = max(0.0, probability - margin_of_error)
            upper = min(1.0, probability + margin_of_error)
        
        return (lower, upper)
    
    def _analyze_side_effects(
        self,
        event: MacroscopicEvent,
        original_prob: float,
        new_prob: float,
        strength: float
    ) -> List[str]:
        """Analyze potential side effects of probability adjustment."""
        side_effects = []
        
        probability_change = abs(new_prob - original_prob)
        
        if probability_change > 0.2:
            side_effects.append("Large probability shift detected")
        
        if strength > 0.15:
            side_effects.append("High adjustment strength applied")
        
        # Check for correlation effects
        event_correlations = [
            corr for (e1, e2), corr in self.correlation_matrix.items()
            if e1 == event.event_id or e2 == event.event_id
        ]
        
        if len(event_correlations) > 5:
            side_effects.append("Multiple correlation impacts")
        
        if any(abs(corr) > 0.8 for corr in event_correlations):
            side_effects.append("Strong correlation effects")
        
        # Check statistical significance
        if event.sample_size < self.minimum_sample_size:
            side_effects.append("Low sample size - reduced reliability")
        
        return side_effects
    
    def _calculate_trend_slope(self, probability_history: List[float]) -> float:
        """Calculate the slope of probability trend."""
        if len(probability_history) < 2:
            return 0.0
        
        n = len(probability_history)
        x_values = list(range(n))
        y_values = probability_history
        
        # Simple linear regression
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope
    
    def _calculate_recent_trend(self, event_id: str) -> float:
        """Calculate recent trend for an event."""
        if event_id not in self.probability_distributions:
            return 0.0
        
        recent_data = list(self.probability_distributions[event_id])[-10:]  # Last 10 points
        return self._calculate_trend_slope(recent_data)
    
    def _calculate_correlation_adjustment(self, event: MacroscopicEvent, strength: float) -> float:
        """Calculate adjustment based on correlated events."""
        total_adjustment = 0.0
        correlation_count = 0
        
        for (e1, e2), correlation in self.correlation_matrix.items():
            if e1 == event.event_id and e2 in self.active_events:
                correlated_event = self.active_events[e2]
                prob_diff = correlated_event.current_probability - correlated_event.base_probability
                adjustment = correlation * prob_diff * strength * 0.1
                total_adjustment += adjustment
                correlation_count += 1
        
        if correlation_count > 0:
            return total_adjustment / correlation_count
        
        return 0.0
    
    def _monte_carlo_adjustment(
        self,
        current_prob: float,
        target_prob: float,
        strength: float,
        num_samples: int = 1000
    ) -> float:
        """Perform Monte Carlo-based probability adjustment."""
        samples = []
        
        for _ in range(num_samples):
            # Generate random adjustment
            noise = random.gauss(0, 0.1 * strength)
            adjustment = (target_prob - current_prob) * strength + noise
            new_prob = max(0.0, min(1.0, current_prob + adjustment))
            samples.append(new_prob)
        
        # Return the mean of Monte Carlo samples
        return statistics.mean(samples)
    
    def _calculate_adjustment_confidence(
        self,
        event: MacroscopicEvent,
        old_prob: float,
        new_prob: float,
        strength: float
    ) -> float:
        """Calculate confidence in the adjustment."""
        base_confidence = 0.8
        
        # Reduce confidence for large changes
        change_penalty = min(0.3, abs(new_prob - old_prob) * 2)
        
        # Reduce confidence for high strength
        strength_penalty = min(0.2, strength * 0.5)
        
        # Increase confidence for larger sample sizes
        sample_bonus = min(0.2, math.log10(event.sample_size / self.minimum_sample_size) * 0.1)
        
        confidence = base_confidence - change_penalty - strength_penalty + sample_bonus
        return max(0.1, min(1.0, confidence))
    
    def _calculate_statistical_significance(
        self,
        old_prob: float,
        new_prob: float,
        sample_size: int
    ) -> float:
        """Calculate statistical significance of the change."""
        if sample_size < 2:
            return 0.0
        
        # Calculate z-score for proportion difference
        pooled_prob = (old_prob + new_prob) / 2
        standard_error = math.sqrt(pooled_prob * (1 - pooled_prob) * (2 / sample_size))
        
        if standard_error == 0:
            return 0.0
        
        z_score = abs(new_prob - old_prob) / standard_error
        
        # Convert z-score to p-value approximation
        significance = min(1.0, 2 * (1 - 0.5 * (1 + math.erf(z_score / math.sqrt(2)))))
        
        return significance
    
    def _create_spatial_correlations(self, event_ids: List[str], field_radius: float) -> None:
        """Create spatial correlations between events in a field."""
        for i, event_id1 in enumerate(event_ids):
            event1 = self.active_events[event_id1]
            coords1 = event1.metadata.get('coordinates', (0, 0))
            
            for j, event_id2 in enumerate(event_ids[i+1:], i+1):
                event2 = self.active_events[event_id2]
                coords2 = event2.metadata.get('coordinates', (0, 0))
                
                # Calculate distance
                distance = math.sqrt(
                    (coords1[0] - coords2[0])**2 + (coords1[1] - coords2[1])**2
                )
                
                # Create correlation based on inverse distance
                if distance < field_radius:
                    correlation_strength = max(0.1, 1.0 - (distance / field_radius))
                    self.correlate_events(event_id1, event_id2, correlation_strength)
    
    def _calculate_adjustment_effectiveness(self, event: MacroscopicEvent) -> float:
        """Calculate the effectiveness of past adjustments."""
        if not event.adjustment_history:
            return 0.0
        
        total_effectiveness = 0.0
        
        for adjustment in event.adjustment_history:
            target = adjustment['target_probability']
            achieved = adjustment['achieved_probability']
            
            # Calculate how close we got to the target
            if target != 0:
                effectiveness = 1.0 - abs(achieved - target) / max(target, 1 - target)
            else:
                effectiveness = 1.0 - abs(achieved - target)
            
            total_effectiveness += max(0.0, effectiveness)
        
        return total_effectiveness / len(event.adjustment_history)