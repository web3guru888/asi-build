"""
Timeline Tracker
===============

Tracks and monitors parallel timelines across multiple universes,
detecting changes, branches, and convergence points in temporal flow.
"""

import numpy as np
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict, deque
import bisect

from ..core.base_multiverse import MultiverseComponent
from ..core.config_manager import get_global_config


class TimelineState(Enum):
    """States of timeline progression."""
    STABLE = "stable"
    BRANCHING = "branching"
    CONVERGING = "converging"
    DIVERGING = "diverging"
    ANOMALOUS = "anomalous"
    COLLAPSED = "collapsed"
    SPLITTING = "splitting"
    MERGING = "merging"


class EventType(Enum):
    """Types of timeline events."""
    CREATION = "creation"
    DESTRUCTION = "destruction"
    MEASUREMENT = "measurement"
    INTERACTION = "interaction"
    DECISION = "decision"
    OBSERVATION = "observation"
    QUANTUM_JUMP = "quantum_jump"
    CAUSAL_INFLUENCE = "causal_influence"


@dataclass
class TimelineEvent:
    """Represents an event in a timeline."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    universe_id: str = ""
    timeline_id: str = ""
    event_type: EventType = EventType.OBSERVATION
    timestamp: float = 0.0
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    description: str = ""
    probability: float = 1.0
    causal_influence: float = 0.0
    quantum_signature: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize quantum signature if not provided."""
        if self.quantum_signature is None:
            # Generate simple quantum signature
            self.quantum_signature = np.random.random(8) * self.probability


@dataclass
class Timeline:
    """Represents a timeline in a universe."""
    timeline_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    universe_id: str = ""
    parent_timeline_id: Optional[str] = None
    child_timeline_ids: List[str] = field(default_factory=list)
    state: TimelineState = TimelineState.STABLE
    start_time: float = 0.0
    current_time: float = 0.0
    end_time: Optional[float] = None
    events: List[TimelineEvent] = field(default_factory=list)
    branch_probability: float = 1.0
    convergence_probability: float = 0.0
    temporal_flow_rate: float = 1.0
    causal_weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_event(self, event: TimelineEvent):
        """Add an event to the timeline."""
        event.timeline_id = self.timeline_id
        
        # Insert event in chronological order
        insert_index = bisect.bisect_left(
            [e.timestamp for e in self.events], 
            event.timestamp
        )
        self.events.insert(insert_index, event)
        
        # Update current time if this is the latest event
        if event.timestamp > self.current_time:
            self.current_time = event.timestamp
    
    def get_events_in_range(self, start_time: float, end_time: float) -> List[TimelineEvent]:
        """Get events within a time range."""
        return [
            event for event in self.events
            if start_time <= event.timestamp <= end_time
        ]
    
    def calculate_timeline_entropy(self) -> float:
        """Calculate entropy of the timeline based on events."""
        if not self.events:
            return 0.0
        
        # Group events by type
        event_counts = defaultdict(int)
        for event in self.events:
            event_counts[event.event_type] += 1
        
        # Calculate Shannon entropy
        total_events = len(self.events)
        entropy = 0.0
        for count in event_counts.values():
            probability = count / total_events
            if probability > 0:
                entropy -= probability * np.log2(probability)
        
        return entropy
    
    def get_causal_influence_distribution(self) -> np.ndarray:
        """Get distribution of causal influences over time."""
        if not self.events:
            return np.array([])
        
        influences = [event.causal_influence for event in self.events]
        return np.array(influences)


class TimelineTracker(MultiverseComponent):
    """
    Tracks and monitors timeline evolution across multiple universes.
    
    Maintains comprehensive records of timeline states, events, branches,
    and convergence points to enable temporal navigation and analysis.
    """
    
    def __init__(self, multiverse_manager=None):
        """Initialize the timeline tracker."""
        super().__init__("TimelineTracker")
        
        self.multiverse_manager = multiverse_manager
        self.config = get_global_config()
        
        # Timeline storage
        self.timelines: Dict[str, Timeline] = {}
        self.universe_timelines: Dict[str, List[str]] = defaultdict(list)
        self.timeline_lock = threading.RLock()
        
        # Event tracking
        self.recent_events: deque = deque(maxlen=10000)  # Last 10k events
        self.event_index: Dict[str, TimelineEvent] = {}
        
        # Timeline analysis
        self.timeline_states: Dict[str, TimelineState] = {}
        self.branch_points: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        self.convergence_points: Dict[str, List[Tuple[float, List[str]]]] = defaultdict(list)
        
        # Monitoring parameters
        self.monitoring_interval = 1.0  # seconds
        self.max_timeline_age = 86400.0  # 24 hours
        self.event_correlation_window = 10.0  # seconds
        
        # Statistics
        self.total_events_tracked = 0
        self.total_timelines_created = 0
        self.active_timelines_count = 0
        
        self.logger.info("TimelineTracker initialized")
    
    def on_start(self):
        """Start timeline tracking."""
        self.logger.info("Timeline tracking started")
        self.update_property("status", "tracking")
        
        # Start monitoring thread
        self._start_monitoring_thread()
    
    def on_stop(self):
        """Stop timeline tracking."""
        self.logger.info("Timeline tracking stopped")
        self.update_property("status", "stopped")
    
    def _start_monitoring_thread(self):
        """Start timeline monitoring in background thread."""
        def monitor_timelines():
            while self.is_running:
                try:
                    self._update_timeline_states()
                    self._detect_temporal_anomalies()
                    self._cleanup_old_timelines()
                    time.sleep(self.monitoring_interval)
                except Exception as e:
                    self.logger.error("Error in timeline monitoring: %s", e)
                    time.sleep(1.0)
        
        monitor_thread = threading.Thread(
            target=monitor_timelines,
            daemon=True,
            name="TimelineMonitor"
        )
        monitor_thread.start()
    
    def create_timeline(self, universe_id: str, 
                       parent_timeline_id: Optional[str] = None,
                       start_time: Optional[float] = None) -> str:
        """
        Create a new timeline for a universe.
        
        Args:
            universe_id: ID of the universe
            parent_timeline_id: ID of parent timeline (for branches)
            start_time: Starting time (defaults to current time)
            
        Returns:
            Timeline ID
        """
        with self.timeline_lock:
            timeline = Timeline(
                universe_id=universe_id,
                parent_timeline_id=parent_timeline_id,
                start_time=start_time or time.time(),
                current_time=start_time or time.time()
            )
            
            # Add metadata
            timeline.metadata.update({
                'created_at': time.time(),
                'creation_source': 'timeline_tracker',
                'universe_id': universe_id
            })
            
            # Register timeline
            self.timelines[timeline.timeline_id] = timeline
            self.universe_timelines[universe_id].append(timeline.timeline_id)
            self.timeline_states[timeline.timeline_id] = TimelineState.STABLE
            
            # Update parent timeline if branching
            if parent_timeline_id and parent_timeline_id in self.timelines:
                parent = self.timelines[parent_timeline_id]
                parent.child_timeline_ids.append(timeline.timeline_id)
                parent.state = TimelineState.BRANCHING
                
                # Record branch point
                self.branch_points[parent_timeline_id].append(
                    (timeline.start_time, timeline.timeline_id)
                )
            
            self.total_timelines_created += 1
            self.active_timelines_count += 1
            
            self.emit_event("timeline_created", {
                'timeline_id': timeline.timeline_id,
                'universe_id': universe_id,
                'parent_timeline_id': parent_timeline_id
            })
            
            self.logger.info("Timeline created: %s for universe %s", 
                           timeline.timeline_id, universe_id)
            
            return timeline.timeline_id
    
    def add_timeline_event(self, timeline_id: str, event: TimelineEvent) -> bool:
        """
        Add an event to a timeline.
        
        Args:
            timeline_id: ID of the timeline
            event: Timeline event to add
            
        Returns:
            True if successful, False otherwise
        """
        with self.timeline_lock:
            timeline = self.timelines.get(timeline_id)
            if not timeline:
                self.logger.error("Timeline not found: %s", timeline_id)
                return False
            
            # Set timeline and universe IDs
            event.timeline_id = timeline_id
            event.universe_id = timeline.universe_id
            
            # Add to timeline
            timeline.add_event(event)
            
            # Add to global tracking
            self.recent_events.append(event)
            self.event_index[event.event_id] = event
            self.total_events_tracked += 1
            
            # Analyze event impact
            self._analyze_event_impact(timeline, event)
            
            self.emit_event("timeline_event_added", {
                'timeline_id': timeline_id,
                'event_id': event.event_id,
                'event_type': event.event_type.value
            })
            
            self.track_operation("add_timeline_event")
            return True
    
    def _analyze_event_impact(self, timeline: Timeline, event: TimelineEvent):
        """Analyze the impact of an event on timeline state."""
        # Check for high causal influence events
        if event.causal_influence > 0.8:
            timeline.state = TimelineState.ANOMALOUS
            self.timeline_states[timeline.timeline_id] = TimelineState.ANOMALOUS
        
        # Check for quantum events that might cause branching
        if (event.event_type in [EventType.QUANTUM_JUMP, EventType.MEASUREMENT] and
            event.probability < 0.7):
            timeline.branch_probability *= event.probability
            
            if timeline.branch_probability < 0.5:
                timeline.state = TimelineState.BRANCHING
                self.timeline_states[timeline.timeline_id] = TimelineState.BRANCHING
        
        # Update temporal flow rate based on event density
        recent_events = timeline.get_events_in_range(
            event.timestamp - self.event_correlation_window,
            event.timestamp
        )
        
        if len(recent_events) > 10:  # High event density
            timeline.temporal_flow_rate *= 0.95  # Slow down time
        elif len(recent_events) < 2:  # Low event density
            timeline.temporal_flow_rate *= 1.05  # Speed up time
        
        # Clamp temporal flow rate
        timeline.temporal_flow_rate = max(0.1, min(10.0, timeline.temporal_flow_rate))
    
    def get_timeline(self, timeline_id: str) -> Optional[Timeline]:
        """Get a timeline by ID."""
        with self.timeline_lock:
            return self.timelines.get(timeline_id)
    
    def get_universe_timelines(self, universe_id: str) -> List[Timeline]:
        """Get all timelines for a universe."""
        with self.timeline_lock:
            timeline_ids = self.universe_timelines.get(universe_id, [])
            return [self.timelines[tid] for tid in timeline_ids if tid in self.timelines]
    
    def get_active_timelines(self) -> List[Timeline]:
        """Get all currently active timelines."""
        with self.timeline_lock:
            return [
                timeline for timeline in self.timelines.values()
                if timeline.state not in [TimelineState.COLLAPSED]
            ]
    
    def detect_timeline_branches(self, timeline_id: str, 
                                time_window: float = 60.0) -> List[Tuple[float, str]]:
        """
        Detect recent timeline branches from a given timeline.
        
        Args:
            timeline_id: ID of the timeline to check
            time_window: Time window to check for branches (seconds)
            
        Returns:
            List of (branch_time, branch_timeline_id) tuples
        """
        with self.timeline_lock:
            timeline = self.timelines.get(timeline_id)
            if not timeline:
                return []
            
            current_time = time.time()
            recent_branches = []
            
            for branch_time, branch_id in self.branch_points[timeline_id]:
                if current_time - branch_time <= time_window:
                    recent_branches.append((branch_time, branch_id))
            
            return recent_branches
    
    def detect_timeline_convergence(self, universe_id: str) -> List[Tuple[float, List[str]]]:
        """
        Detect timeline convergence points in a universe.
        
        Args:
            universe_id: ID of the universe
            
        Returns:
            List of (convergence_time, [timeline_ids]) tuples
        """
        with self.timeline_lock:
            universe_timelines = self.get_universe_timelines(universe_id)
            convergence_points = []
            
            # Look for timelines with similar event patterns
            for i, timeline1 in enumerate(universe_timelines):
                for timeline2 in universe_timelines[i+1:]:
                    convergence_score = self._calculate_timeline_similarity(
                        timeline1, timeline2
                    )
                    
                    if convergence_score > 0.8:  # High similarity threshold
                        convergence_time = max(timeline1.current_time, timeline2.current_time)
                        convergence_points.append((
                            convergence_time,
                            [timeline1.timeline_id, timeline2.timeline_id]
                        ))
            
            return convergence_points
    
    def _calculate_timeline_similarity(self, timeline1: Timeline, timeline2: Timeline) -> float:
        """Calculate similarity between two timelines."""
        # Compare event sequences
        events1 = timeline1.events[-10:]  # Last 10 events
        events2 = timeline2.events[-10:]  # Last 10 events
        
        if not events1 or not events2:
            return 0.0
        
        # Compare event types and timing
        similarity_score = 0.0
        matches = 0
        
        for e1 in events1:
            for e2 in events2:
                # Time similarity
                time_diff = abs(e1.timestamp - e2.timestamp)
                time_similarity = max(0, 1.0 - time_diff / 60.0)  # 60 second window
                
                # Type similarity
                type_similarity = 1.0 if e1.event_type == e2.event_type else 0.0
                
                # Probability similarity
                prob_similarity = 1.0 - abs(e1.probability - e2.probability)
                
                event_similarity = (time_similarity + type_similarity + prob_similarity) / 3.0
                similarity_score += event_similarity
                matches += 1
        
        if matches > 0:
            return similarity_score / matches
        return 0.0
    
    def _update_timeline_states(self):
        """Update states of all timelines."""
        with self.timeline_lock:
            for timeline_id, timeline in self.timelines.items():
                old_state = timeline.state
                new_state = self._calculate_timeline_state(timeline)
                
                if new_state != old_state:
                    timeline.state = new_state
                    self.timeline_states[timeline_id] = new_state
                    
                    self.emit_event("timeline_state_changed", {
                        'timeline_id': timeline_id,
                        'old_state': old_state.value,
                        'new_state': new_state.value
                    })
    
    def _calculate_timeline_state(self, timeline: Timeline) -> TimelineState:
        """Calculate the current state of a timeline."""
        current_time = time.time()
        
        # Check if timeline is too old
        if timeline.end_time and current_time > timeline.end_time:
            return TimelineState.COLLAPSED
        
        # Check branch probability
        if timeline.branch_probability < 0.3:
            return TimelineState.BRANCHING
        
        # Check for child timelines (indicates recent branching)
        if timeline.child_timeline_ids:
            latest_branch_time = 0
            for child_id in timeline.child_timeline_ids:
                child = self.timelines.get(child_id)
                if child:
                    latest_branch_time = max(latest_branch_time, child.start_time)
            
            if current_time - latest_branch_time < 300:  # 5 minutes
                return TimelineState.SPLITTING
        
        # Check event density for anomalies
        recent_events = timeline.get_events_in_range(
            current_time - 60, current_time  # Last minute
        )
        
        if len(recent_events) > 50:  # Very high event density
            return TimelineState.ANOMALOUS
        
        # Check convergence probability
        if timeline.convergence_probability > 0.7:
            return TimelineState.CONVERGING
        
        return TimelineState.STABLE
    
    def _detect_temporal_anomalies(self):
        """Detect temporal anomalies across all timelines."""
        with self.timeline_lock:
            anomalies = []
            
            for timeline in self.timelines.values():
                # Check for temporal flow rate anomalies
                if timeline.temporal_flow_rate < 0.5 or timeline.temporal_flow_rate > 2.0:
                    anomalies.append({
                        'type': 'temporal_flow_anomaly',
                        'timeline_id': timeline.timeline_id,
                        'flow_rate': timeline.temporal_flow_rate
                    })
                
                # Check for causal weight anomalies
                if timeline.causal_weight > 10.0:
                    anomalies.append({
                        'type': 'causal_weight_anomaly',
                        'timeline_id': timeline.timeline_id,
                        'causal_weight': timeline.causal_weight
                    })
                
                # Check for event clustering anomalies
                entropy = timeline.calculate_timeline_entropy()
                if entropy > 5.0:  # High entropy indicates chaotic events
                    anomalies.append({
                        'type': 'event_entropy_anomaly',
                        'timeline_id': timeline.timeline_id,
                        'entropy': entropy
                    })
            
            if anomalies:
                self.emit_event("temporal_anomalies_detected", {
                    'anomaly_count': len(anomalies),
                    'anomalies': anomalies
                })
    
    def _cleanup_old_timelines(self):
        """Clean up old and collapsed timelines."""
        current_time = time.time()
        
        with self.timeline_lock:
            timelines_to_remove = []
            
            for timeline_id, timeline in self.timelines.items():
                # Remove very old timelines
                if (current_time - timeline.start_time > self.max_timeline_age and
                    timeline.state == TimelineState.COLLAPSED):
                    timelines_to_remove.append(timeline_id)
            
            for timeline_id in timelines_to_remove:
                self._remove_timeline(timeline_id)
    
    def _remove_timeline(self, timeline_id: str):
        """Remove a timeline and clean up references."""
        timeline = self.timelines.get(timeline_id)
        if not timeline:
            return
        
        # Remove from universe timelines
        if timeline.universe_id in self.universe_timelines:
            try:
                self.universe_timelines[timeline.universe_id].remove(timeline_id)
            except ValueError:
                pass
        
        # Clean up parent references
        if timeline.parent_timeline_id:
            parent = self.timelines.get(timeline.parent_timeline_id)
            if parent and timeline_id in parent.child_timeline_ids:
                parent.child_timeline_ids.remove(timeline_id)
        
        # Remove timeline
        del self.timelines[timeline_id]
        if timeline_id in self.timeline_states:
            del self.timeline_states[timeline_id]
        if timeline_id in self.branch_points:
            del self.branch_points[timeline_id]
        
        self.active_timelines_count -= 1
        
        self.logger.debug("Timeline removed: %s", timeline_id)
    
    def get_timeline_statistics(self) -> Dict[str, Any]:
        """Get comprehensive timeline statistics."""
        with self.timeline_lock:
            state_counts = defaultdict(int)
            total_events = 0
            total_entropy = 0.0
            
            for timeline in self.timelines.values():
                state_counts[timeline.state.value] += 1
                total_events += len(timeline.events)
                total_entropy += timeline.calculate_timeline_entropy()
            
            avg_entropy = total_entropy / len(self.timelines) if self.timelines else 0.0
            
            return {
                'total_timelines': len(self.timelines),
                'active_timelines': self.active_timelines_count,
                'total_events_tracked': self.total_events_tracked,
                'timeline_states': dict(state_counts),
                'average_entropy': avg_entropy,
                'total_branch_points': sum(len(branches) for branches in self.branch_points.values()),
                'recent_events_count': len(self.recent_events)
            }
    
    def on_health_check(self) -> Optional[Dict[str, Any]]:
        """Health check for timeline tracker."""
        return {
            'active_timelines': len(self.timelines),
            'recent_events': len(self.recent_events),
            'total_events': self.total_events_tracked,
            'tracking_active': self.is_running
        }