"""
Temporal Consciousness

This module implements temporal aspects of consciousness including
time perception, temporal binding, duration awareness, and the
subjective flow of time in conscious experience.

Key components:
- Time perception mechanisms
- Temporal binding across modalities
- Duration estimation and awareness
- Temporal attention and memory
- Present moment awareness
- Temporal integration of experience
"""

import math
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState


@dataclass
class TemporalEvent:
    """Represents an event in temporal consciousness"""

    event_id: str
    onset_time: float
    duration: float
    event_type: str
    content: Dict[str, Any]
    subjective_duration: float = 0.0
    temporal_salience: float = 0.5

    def get_offset_time(self) -> float:
        """Get the offset time of the event"""
        return self.onset_time + self.duration


@dataclass
class TemporalWindow:
    """Represents a window of temporal integration"""

    window_id: str
    start_time: float
    end_time: float
    contained_events: List[str] = field(default_factory=list)
    integration_strength: float = 0.0
    coherence_score: float = 0.0

    def get_duration(self) -> float:
        """Get the duration of the window"""
        return self.end_time - self.start_time


class TemporalConsciousness(BaseConsciousness):
    """
    Implementation of Temporal Consciousness

    Manages temporal aspects of conscious experience including
    time perception, temporal binding, and the subjective flow of time.
    """

    def _initialize(self):
        """Initialize the TemporalConsciousness consciousness model (called by BaseConsciousness)."""
        pass  # All initialization is done in __init__ after super().__init__()

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("TemporalConsciousness", config)

        # Temporal event tracking
        self.temporal_events: Dict[str, TemporalEvent] = {}
        self.event_timeline: deque = deque(maxlen=1000)

        # Temporal windows and binding
        self.temporal_windows: Dict[str, TemporalWindow] = {}
        self.active_temporal_bindings: Set[Tuple[str, str]] = set()

        # Time perception
        self.subjective_time_rate = 1.0
        self.temporal_resolution = self.config.get("temporal_resolution", 0.1)  # 100ms
        self.integration_window_size = self.config.get("integration_window", 3.0)  # 3 seconds

        # Present moment tracking
        self.present_moment_window = 0.5  # 500ms
        self.present_moment_events: List[str] = []

        # Duration estimation
        self.duration_estimates: Dict[str, float] = {}
        self.duration_estimation_accuracy = 0.7

        # Temporal attention
        self.temporal_attention_focus: Optional[float] = None
        self.attention_window_size = 1.0  # 1 second

        # Statistics
        self.total_temporal_events = 0
        self.temporal_bindings_formed = 0
        self.duration_estimations = 0

        # Threading
        self.temporal_lock = threading.Lock()

    def register_temporal_event(
        self, content: Dict[str, Any], event_type: str, duration: float = 0.1
    ) -> TemporalEvent:
        """Register a new temporal event"""
        event_id = f"temporal_event_{self.total_temporal_events:06d}"
        self.total_temporal_events += 1

        current_time = time.time()

        # Estimate subjective duration
        subjective_duration = self._estimate_subjective_duration(duration, content)

        # Calculate temporal salience
        temporal_salience = self._calculate_temporal_salience(content, event_type)

        temporal_event = TemporalEvent(
            event_id=event_id,
            onset_time=current_time,
            duration=duration,
            event_type=event_type,
            content=content,
            subjective_duration=subjective_duration,
            temporal_salience=temporal_salience,
        )

        with self.temporal_lock:
            self.temporal_events[event_id] = temporal_event
            self.event_timeline.append((current_time, event_id))

            # Update present moment
            self._update_present_moment(temporal_event)

            # Attempt temporal binding
            self._attempt_temporal_binding(temporal_event)

        self.logger.debug(f"Registered temporal event: {event_type} (duration: {duration:.3f}s)")
        return temporal_event

    def _estimate_subjective_duration(
        self, objective_duration: float, content: Dict[str, Any]
    ) -> float:
        """Estimate subjective duration of an event"""
        # Base subjective duration
        subjective_duration = objective_duration * self.subjective_time_rate

        # Modify based on content properties
        arousal = content.get("arousal", 0.5)
        attention = content.get("attention_level", 0.5)
        novelty = content.get("novelty", 0.5)

        # High arousal tends to make time feel slower
        arousal_factor = 1.0 + arousal * 0.3

        # High attention makes duration estimation more accurate
        attention_factor = 1.0 + (attention - 0.5) * 0.2

        # Novel events tend to feel longer
        novelty_factor = 1.0 + novelty * 0.2

        subjective_duration *= arousal_factor * attention_factor * novelty_factor

        return subjective_duration

    def _calculate_temporal_salience(self, content: Dict[str, Any], event_type: str) -> float:
        """Calculate temporal salience of an event"""
        salience = 0.5  # Base salience

        # Event type contributions
        salience_weights = {
            "sensory_change": 0.8,
            "action_onset": 0.7,
            "attention_shift": 0.6,
            "memory_retrieval": 0.4,
            "cognitive_event": 0.3,
        }

        salience = salience_weights.get(event_type, salience)

        # Content-based modifications
        if "intensity" in content:
            salience += content["intensity"] * 0.2

        if "urgency" in content:
            salience += content["urgency"] * 0.3

        return min(1.0, salience)

    def _update_present_moment(self, new_event: TemporalEvent) -> None:
        """Update present moment awareness"""
        current_time = time.time()

        # Remove events outside present moment window
        self.present_moment_events = [
            event_id
            for event_id in self.present_moment_events
            if (
                event_id in self.temporal_events
                and current_time - self.temporal_events[event_id].onset_time
                <= self.present_moment_window
            )
        ]

        # Add new event if it has sufficient salience
        if new_event.temporal_salience > 0.3:
            self.present_moment_events.append(new_event.event_id)

        # Limit present moment events
        if len(self.present_moment_events) > 5:
            # Keep most salient events
            self.present_moment_events.sort(
                key=lambda eid: (
                    self.temporal_events[eid].temporal_salience
                    if eid in self.temporal_events
                    else 0
                ),
                reverse=True,
            )
            self.present_moment_events = self.present_moment_events[:5]

    def _attempt_temporal_binding(self, new_event: TemporalEvent) -> None:
        """Attempt to bind new event with recent events"""
        current_time = time.time()
        binding_window = 2.0  # 2 seconds

        # Find recent events for potential binding
        recent_events = []
        for timestamp, event_id in reversed(self.event_timeline):
            if current_time - timestamp > binding_window:
                break
            if event_id != new_event.event_id and event_id in self.temporal_events:
                recent_events.append(self.temporal_events[event_id])

        # Attempt binding with each recent event
        for recent_event in recent_events:
            binding_strength = self._calculate_temporal_binding_strength(new_event, recent_event)

            if binding_strength > 0.5:
                binding = (recent_event.event_id, new_event.event_id)
                self.active_temporal_bindings.add(binding)
                self.temporal_bindings_formed += 1

                self.logger.debug(
                    f"Temporal binding formed: {recent_event.event_id} <-> {new_event.event_id}"
                )

    def _calculate_temporal_binding_strength(
        self, event1: TemporalEvent, event2: TemporalEvent
    ) -> float:
        """Calculate strength of temporal binding between two events"""
        # Temporal proximity
        time_diff = abs(event1.onset_time - event2.onset_time)
        temporal_proximity = max(0.0, 1.0 - time_diff / 2.0)  # 2 second window

        # Content similarity
        content_similarity = self._calculate_content_similarity(event1.content, event2.content)

        # Event type compatibility
        type_compatibility = 1.0 if event1.event_type == event2.event_type else 0.5

        # Salience product
        salience_factor = math.sqrt(event1.temporal_salience * event2.temporal_salience)

        binding_strength = (
            temporal_proximity * 0.4
            + content_similarity * 0.3
            + type_compatibility * 0.2
            + salience_factor * 0.1
        )

        return binding_strength

    def _calculate_content_similarity(
        self, content1: Dict[str, Any], content2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between event contents"""
        similarity = 0.0

        # Check for common keys
        common_keys = set(content1.keys()) & set(content2.keys())
        if not common_keys:
            return 0.0

        for key in common_keys:
            val1, val2 = content1[key], content2[key]

            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # Numerical similarity
                max_val = max(abs(val1), abs(val2), 1.0)
                similarity += 1.0 - abs(val1 - val2) / max_val
            elif isinstance(val1, str) and isinstance(val2, str):
                # String similarity (simple overlap)
                words1 = set(val1.lower().split())
                words2 = set(val2.lower().split())
                if words1 or words2:
                    overlap = len(words1 & words2)
                    total = len(words1 | words2)
                    similarity += overlap / total if total > 0 else 0.0
            elif val1 == val2:
                similarity += 1.0

        return similarity / len(common_keys) if common_keys else 0.0

    def create_temporal_window(self, start_time: float, duration: float) -> TemporalWindow:
        """Create a temporal integration window"""
        window_id = f"temporal_window_{len(self.temporal_windows):06d}"
        end_time = start_time + duration

        # Find events within this window
        contained_events = []
        for event_id, event in self.temporal_events.items():
            if (
                start_time <= event.onset_time <= end_time
                or start_time <= event.get_offset_time() <= end_time
                or (event.onset_time <= start_time and event.get_offset_time() >= end_time)
            ):
                contained_events.append(event_id)

        # Calculate integration strength
        integration_strength = self._calculate_window_integration_strength(contained_events)

        # Calculate coherence
        coherence_score = self._calculate_window_coherence(contained_events)

        window = TemporalWindow(
            window_id=window_id,
            start_time=start_time,
            end_time=end_time,
            contained_events=contained_events,
            integration_strength=integration_strength,
            coherence_score=coherence_score,
        )

        self.temporal_windows[window_id] = window
        return window

    def _calculate_window_integration_strength(self, event_ids: List[str]) -> float:
        """Calculate integration strength for events in a temporal window"""
        if len(event_ids) < 2:
            return 0.0

        # Count temporal bindings within the window
        window_bindings = 0
        total_possible_bindings = len(event_ids) * (len(event_ids) - 1) // 2

        for i, event_id1 in enumerate(event_ids):
            for event_id2 in event_ids[i + 1 :]:
                if (event_id1, event_id2) in self.active_temporal_bindings or (
                    event_id2,
                    event_id1,
                ) in self.active_temporal_bindings:
                    window_bindings += 1

        return window_bindings / total_possible_bindings if total_possible_bindings > 0 else 0.0

    def _calculate_window_coherence(self, event_ids: List[str]) -> float:
        """Calculate coherence score for events in a temporal window"""
        if not event_ids:
            return 0.0

        events = [self.temporal_events[eid] for eid in event_ids if eid in self.temporal_events]
        if len(events) < 2:
            return 1.0  # Single event is perfectly coherent

        # Calculate temporal spacing coherence
        onset_times = sorted([event.onset_time for event in events])
        intervals = [onset_times[i + 1] - onset_times[i] for i in range(len(onset_times) - 1)]

        if intervals:
            interval_variance = np.var(intervals)
            temporal_coherence = 1.0 / (1.0 + interval_variance)
        else:
            temporal_coherence = 1.0

        # Calculate content coherence
        content_similarities = []
        for i, event1 in enumerate(events):
            for event2 in events[i + 1 :]:
                similarity = self._calculate_content_similarity(event1.content, event2.content)
                content_similarities.append(similarity)

        content_coherence = np.mean(content_similarities) if content_similarities else 0.0

        return (temporal_coherence + content_coherence) / 2.0

    def estimate_duration(self, start_time: float, end_time: Optional[float] = None) -> float:
        """Estimate subjective duration of a time period"""
        if end_time is None:
            end_time = time.time()

        objective_duration = end_time - start_time
        self.duration_estimations += 1

        # Find events during this period
        period_events = []
        for event in self.temporal_events.values():
            if start_time <= event.onset_time <= end_time:
                period_events.append(event)

        # Base subjective duration
        subjective_duration = objective_duration * self.subjective_time_rate

        # Modify based on events in the period
        if period_events:
            # High salience events make time feel longer
            avg_salience = np.mean([event.temporal_salience for event in period_events])
            salience_factor = 1.0 + avg_salience * 0.2

            # Many events make time feel longer
            event_density = len(period_events) / max(0.1, objective_duration)
            density_factor = 1.0 + min(0.3, event_density * 0.1)

            subjective_duration *= salience_factor * density_factor

        # Store estimation
        estimation_id = f"duration_est_{self.duration_estimations}"
        self.duration_estimates[estimation_id] = subjective_duration

        return subjective_duration

    def focus_temporal_attention(
        self, target_time: float, window_size: Optional[float] = None
    ) -> None:
        """Focus temporal attention on a specific time period"""
        if window_size is None:
            window_size = self.attention_window_size

        self.temporal_attention_focus = target_time
        self.attention_window_size = window_size

        # Enhance salience of events within attention window
        for event in self.temporal_events.values():
            time_distance = abs(event.onset_time - target_time)
            if time_distance <= window_size / 2:
                # Enhance salience based on proximity to focus
                enhancement = 1.0 - (time_distance / (window_size / 2))
                event.temporal_salience = min(
                    1.0, event.temporal_salience * (1.0 + enhancement * 0.3)
                )

    def get_temporal_flow_state(self) -> Dict[str, Any]:
        """Get current temporal flow state"""
        current_time = time.time()

        # Recent event density
        recent_events = [
            event
            for event in self.temporal_events.values()
            if current_time - event.onset_time <= 10.0  # Last 10 seconds
        ]

        event_density = len(recent_events) / 10.0

        # Average temporal salience
        if recent_events:
            avg_salience = np.mean([event.temporal_salience for event in recent_events])
        else:
            avg_salience = 0.0

        # Present moment richness
        present_moment_richness = (
            len(self.present_moment_events) / 5.0
        )  # Normalized to max 5 events

        # Temporal binding activity
        recent_bindings = sum(
            1
            for binding in self.active_temporal_bindings
            if any(
                self.temporal_events.get(event_id, {}).get("onset_time", 0) > current_time - 5.0
                for event_id in binding
            )
        )

        return {
            "subjective_time_rate": self.subjective_time_rate,
            "event_density": event_density,
            "average_temporal_salience": avg_salience,
            "present_moment_richness": present_moment_richness,
            "active_temporal_bindings": len(self.active_temporal_bindings),
            "recent_binding_activity": recent_bindings,
            "temporal_attention_focus": self.temporal_attention_focus,
            "present_moment_events": len(self.present_moment_events),
        }

    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "temporal_event_registration":
            content = event.data.get("content", {})
            event_type = event.data.get("event_type", "cognitive_event")
            duration = event.data.get("duration", 0.1)

            temporal_event = self.register_temporal_event(content, event_type, duration)

            return ConsciousnessEvent(
                event_id=f"temporal_registered_{temporal_event.event_id}",
                timestamp=time.time(),
                event_type="temporal_event_registered",
                data={
                    "temporal_event_id": temporal_event.event_id,
                    "subjective_duration": temporal_event.subjective_duration,
                    "temporal_salience": temporal_event.temporal_salience,
                },
                source_module="temporal_consciousness",
            )

        elif event.event_type == "duration_estimation_request":
            start_time = event.data.get("start_time")
            end_time = event.data.get("end_time")

            if start_time:
                estimated_duration = self.estimate_duration(start_time, end_time)

                return ConsciousnessEvent(
                    event_id=f"duration_estimated_{int(time.time())}",
                    timestamp=time.time(),
                    event_type="duration_estimation",
                    data={
                        "start_time": start_time,
                        "end_time": end_time or time.time(),
                        "estimated_duration": estimated_duration,
                        "objective_duration": (end_time or time.time()) - start_time,
                    },
                    source_module="temporal_consciousness",
                )

        elif event.event_type == "temporal_attention_focus":
            target_time = event.data.get("target_time", time.time())
            window_size = event.data.get("window_size")

            self.focus_temporal_attention(target_time, window_size)

        return None

    def update(self) -> None:
        """Update the Temporal Consciousness system"""
        current_time = time.time()

        # Update subjective time rate based on recent activity
        self._update_subjective_time_rate()

        # Clean up old events
        old_events = [
            event_id
            for event_id, event in self.temporal_events.items()
            if current_time - event.get_offset_time() > 3600  # 1 hour
        ]

        for event_id in old_events:
            del self.temporal_events[event_id]

        # Clean up old temporal bindings
        valid_bindings = set()
        for binding in self.active_temporal_bindings:
            event1_id, event2_id = binding
            if event1_id in self.temporal_events and event2_id in self.temporal_events:
                valid_bindings.add(binding)

        self.active_temporal_bindings = valid_bindings

        # Update present moment
        self._update_present_moment_awareness()

        # Update consciousness metrics
        flow_state = self.get_temporal_flow_state()
        self.metrics.awareness_level = flow_state["present_moment_richness"]
        self.metrics.integration_level = min(1.0, len(self.active_temporal_bindings) / 10.0)

    def _update_subjective_time_rate(self) -> None:
        """Update subjective time rate based on recent activity"""
        current_time = time.time()

        # Get recent events (last 30 seconds)
        recent_events = [
            event
            for event in self.temporal_events.values()
            if current_time - event.onset_time <= 30.0
        ]

        if recent_events:
            # High activity makes time feel faster
            event_rate = len(recent_events) / 30.0
            activity_factor = 1.0 - min(0.2, event_rate * 0.05)

            # High salience makes time feel slower
            avg_salience = np.mean([event.temporal_salience for event in recent_events])
            salience_factor = 1.0 + avg_salience * 0.1

            # Update rate with exponential smoothing
            target_rate = activity_factor * salience_factor
            alpha = 0.1
            self.subjective_time_rate = (
                alpha * target_rate + (1 - alpha) * self.subjective_time_rate
            )
        else:
            # No activity - time rate approaches normal
            self.subjective_time_rate = 0.9 * self.subjective_time_rate + 0.1 * 1.0

    def _update_present_moment_awareness(self) -> None:
        """Update present moment awareness"""
        current_time = time.time()

        # Remove expired events from present moment
        self.present_moment_events = [
            event_id
            for event_id in self.present_moment_events
            if (
                event_id in self.temporal_events
                and current_time - self.temporal_events[event_id].onset_time
                <= self.present_moment_window
            )
        ]

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Temporal Consciousness system"""
        current_time = time.time()

        return {
            "total_temporal_events": len(self.temporal_events),
            "recent_events": len(
                [e for e in self.temporal_events.values() if current_time - e.onset_time <= 60.0]
            ),
            "present_moment_events": len(self.present_moment_events),
            "active_temporal_bindings": len(self.active_temporal_bindings),
            "temporal_windows": len(self.temporal_windows),
            "subjective_time_rate": self.subjective_time_rate,
            "temporal_attention_focus": self.temporal_attention_focus,
            "attention_window_size": self.attention_window_size,
            "total_events_registered": self.total_temporal_events,
            "temporal_bindings_formed": self.temporal_bindings_formed,
            "duration_estimations": self.duration_estimations,
            "temporal_flow_state": self.get_temporal_flow_state(),
        }
