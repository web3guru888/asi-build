"""
Causality Loop Manager

Advanced system for managing probability fields within causal loops,
handling temporal paradoxes, and maintaining causal consistency
while manipulating cause-effect relationships.
"""

import numpy as np
import logging
import math
import time
from typing import Dict, List, Tuple, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict, deque
import networkx as nx
from concurrent.futures import ThreadPoolExecutor
import asyncio


class CausalityType(Enum):
    """Types of causal relationships."""
    DIRECT_CAUSE = "direct_cause"
    INDIRECT_CAUSE = "indirect_cause"
    TEMPORAL_LOOP = "temporal_loop"
    FEEDBACK_LOOP = "feedback_loop"
    PARADOX_LOOP = "paradox_loop"
    BOOTSTRAP_PARADOX = "bootstrap_paradox"
    GRANDFATHER_PARADOX = "grandfather_paradox"
    CAUSAL_CHAIN = "causal_chain"


class ParadoxResolution(Enum):
    """Methods for resolving temporal paradoxes."""
    NOVIKOV_CONSISTENCY = "novikov_consistency"
    MANY_WORLDS = "many_worlds"
    TIMELINE_REPAIR = "timeline_repair"
    PROBABILITY_DAMPENING = "probability_dampening"
    CAUSAL_ISOLATION = "causal_isolation"
    QUANTUM_SUPERPOSITION = "quantum_superposition"


@dataclass
class CausalEvent:
    """Represents an event in a causal network."""
    event_id: str
    event_description: str
    probability: float
    timestamp: float
    causal_strength: float
    causes: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    temporal_displacement: float = 0.0
    paradox_risk: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalLoop:
    """Represents a causal loop structure."""
    loop_id: str
    loop_type: CausalityType
    events: List[str]
    loop_strength: float
    temporal_span: float
    paradox_level: float
    resolution_method: Optional[ParadoxResolution]
    stability: float
    creation_time: float
    last_validated: float


@dataclass
class ParadoxAnalysis:
    """Analysis result for temporal paradoxes."""
    paradox_id: str
    paradox_type: str
    severity: float
    affected_events: List[str]
    resolution_options: List[ParadoxResolution]
    recommended_action: str
    consistency_violation: float
    temporal_impact: float


class CausalityLoopManager:
    """
    Advanced causality loop and temporal paradox management system.
    
    This system manages probability fields within causal loops,
    prevents temporal paradoxes, and maintains causal consistency
    while allowing controlled manipulation of cause-effect relationships.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Core system state
        self.causal_events: Dict[str, CausalEvent] = {}
        self.causal_loops: Dict[str, CausalLoop] = {}
        self.causal_graph: nx.DiGraph = nx.DiGraph()
        self.paradox_registry: Dict[str, ParadoxAnalysis] = {}
        
        # Threading and synchronization
        self.system_lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Causal parameters
        self.max_loop_depth = 50
        self.paradox_threshold = 0.8
        self.consistency_tolerance = 0.05
        self.temporal_resolution = 1e-9  # Nanosecond precision
        
        # Physics constants for causality
        self.LIGHT_SPEED = 299792458  # m/s
        self.PLANCK_TIME = 5.391247e-44  # seconds
        self.CAUSALITY_VIOLATION_ENERGY = 1e20  # Joules
        
        # Paradox detection thresholds
        self.grandfather_paradox_threshold = 0.95
        self.bootstrap_paradox_threshold = 0.85
        self.consistency_violation_threshold = 0.9
        
        # Resolution strategies
        self.default_resolution = ParadoxResolution.NOVIKOV_CONSISTENCY
        self.resolution_priorities = {
            ParadoxResolution.NOVIKOV_CONSISTENCY: 1.0,
            ParadoxResolution.MANY_WORLDS: 0.8,
            ParadoxResolution.TIMELINE_REPAIR: 0.6,
            ParadoxResolution.PROBABILITY_DAMPENING: 0.4,
            ParadoxResolution.CAUSAL_ISOLATION: 0.2
        }
        
        self.logger.info("CausalityLoopManager initialized")
    
    def register_causal_event(
        self,
        event_description: str,
        probability: float,
        timestamp: Optional[float] = None,
        causal_strength: float = 1.0,
        temporal_displacement: float = 0.0
    ) -> str:
        """
        Register a new causal event in the system.
        
        Args:
            event_description: Description of the event
            probability: Probability of the event occurring
            timestamp: When the event occurs (None for current time)
            causal_strength: Strength of causal influence
            temporal_displacement: Time displacement (for time travel)
            
        Returns:
            Event ID string
        """
        with self.system_lock:
            event_id = f"ce_{int(time.time() * 1000000000)}"
            
            if timestamp is None:
                timestamp = time.time()
            
            # Validate probability
            probability = max(0.0, min(1.0, probability))
            
            # Calculate initial paradox risk
            paradox_risk = self._calculate_initial_paradox_risk(
                timestamp, temporal_displacement, causal_strength
            )
            
            event = CausalEvent(
                event_id=event_id,
                event_description=event_description,
                probability=probability,
                timestamp=timestamp,
                causal_strength=causal_strength,
                temporal_displacement=temporal_displacement,
                paradox_risk=paradox_risk
            )
            
            self.causal_events[event_id] = event
            self.causal_graph.add_node(event_id, **event.__dict__)
            
            self.logger.info(f"Registered causal event {event_id}: {event_description}")
            return event_id
    
    def create_causal_link(
        self,
        cause_event_id: str,
        effect_event_id: str,
        causal_strength: float = 1.0,
        temporal_delay: float = 0.0
    ) -> bool:
        """
        Create a causal link between two events.
        
        Args:
            cause_event_id: ID of the causing event
            effect_event_id: ID of the effect event
            causal_strength: Strength of the causal link (0-1)
            temporal_delay: Time delay between cause and effect
            
        Returns:
            True if link created successfully
        """
        with self.system_lock:
            if (cause_event_id not in self.causal_events or 
                effect_event_id not in self.causal_events):
                return False
            
            cause_event = self.causal_events[cause_event_id]
            effect_event = self.causal_events[effect_event_id]
            
            # Check for causality violations
            if self._would_violate_causality(cause_event, effect_event, temporal_delay):
                self.logger.warning(f"Causal link would violate causality: {cause_event_id} -> {effect_event_id}")
                return False
            
            # Add causal relationship
            if effect_event_id not in cause_event.effects:
                cause_event.effects.append(effect_event_id)
            if cause_event_id not in effect_event.causes:
                effect_event.causes.append(cause_event_id)
            
            # Add edge to causal graph
            self.causal_graph.add_edge(
                cause_event_id, 
                effect_event_id,
                causal_strength=causal_strength,
                temporal_delay=temporal_delay
            )
            
            # Check for loops
            self._detect_and_register_loops()
            
            # Update paradox risks
            self._update_paradox_risks([cause_event_id, effect_event_id])
            
            self.logger.info(f"Created causal link: {cause_event_id} -> {effect_event_id}")
            return True
    
    def detect_causal_loops(self) -> List[str]:
        """
        Detect all causal loops in the current system.
        
        Returns:
            List of loop IDs
        """
        with self.system_lock:
            detected_loops = []
            
            try:
                # Find strongly connected components (cycles)
                cycles = list(nx.simple_cycles(self.causal_graph))
                
                for cycle in cycles:
                    if len(cycle) > 1:  # Exclude self-loops for now
                        loop_id = self._register_causal_loop(cycle)
                        if loop_id:
                            detected_loops.append(loop_id)
                
            except nx.NetworkXError as e:
                self.logger.error(f"Error detecting causal loops: {e}")
            
            self.logger.info(f"Detected {len(detected_loops)} causal loops")
            return detected_loops
    
    def analyze_temporal_paradox(self, loop_id: str) -> ParadoxAnalysis:
        """
        Analyze a causal loop for temporal paradoxes.
        
        Args:
            loop_id: ID of the causal loop to analyze
            
        Returns:
            ParadoxAnalysis with detailed analysis
        """
        if loop_id not in self.causal_loops:
            raise ValueError(f"Loop {loop_id} not found")
        
        loop = self.causal_loops[loop_id]
        paradox_id = f"paradox_{loop_id}_{int(time.time() * 1000000)}"
        
        # Analyze paradox type and severity
        paradox_type, severity = self._classify_paradox(loop)
        
        # Determine affected events
        affected_events = self._find_affected_events(loop)
        
        # Calculate consistency violation
        consistency_violation = self._calculate_consistency_violation(loop)
        
        # Calculate temporal impact
        temporal_impact = self._calculate_temporal_impact(loop)
        
        # Determine resolution options
        resolution_options = self._determine_resolution_options(paradox_type, severity)
        
        # Recommend action
        recommended_action = self._recommend_paradox_resolution(
            paradox_type, severity, resolution_options
        )
        
        analysis = ParadoxAnalysis(
            paradox_id=paradox_id,
            paradox_type=paradox_type,
            severity=severity,
            affected_events=affected_events,
            resolution_options=resolution_options,
            recommended_action=recommended_action,
            consistency_violation=consistency_violation,
            temporal_impact=temporal_impact
        )
        
        self.paradox_registry[paradox_id] = analysis
        
        self.logger.info(f"Analyzed paradox {paradox_id}: type={paradox_type}, severity={severity:.3f}")
        return analysis
    
    def resolve_paradox(
        self,
        paradox_id: str,
        resolution_method: ParadoxResolution = None
    ) -> bool:
        """
        Resolve a temporal paradox using specified method.
        
        Args:
            paradox_id: ID of the paradox to resolve
            resolution_method: Method to use for resolution
            
        Returns:
            True if paradox resolved successfully
        """
        if paradox_id not in self.paradox_registry:
            return False
        
        analysis = self.paradox_registry[paradox_id]
        
        if resolution_method is None:
            resolution_method = ParadoxResolution(analysis.recommended_action)
        
        with self.system_lock:
            success = False
            
            if resolution_method == ParadoxResolution.NOVIKOV_CONSISTENCY:
                success = self._apply_novikov_consistency(analysis)
            
            elif resolution_method == ParadoxResolution.MANY_WORLDS:
                success = self._apply_many_worlds_resolution(analysis)
            
            elif resolution_method == ParadoxResolution.TIMELINE_REPAIR:
                success = self._apply_timeline_repair(analysis)
            
            elif resolution_method == ParadoxResolution.PROBABILITY_DAMPENING:
                success = self._apply_probability_dampening(analysis)
            
            elif resolution_method == ParadoxResolution.CAUSAL_ISOLATION:
                success = self._apply_causal_isolation(analysis)
            
            elif resolution_method == ParadoxResolution.QUANTUM_SUPERPOSITION:
                success = self._apply_quantum_superposition(analysis)
            
            if success:
                self.logger.info(f"Resolved paradox {paradox_id} using {resolution_method.value}")
            else:
                self.logger.error(f"Failed to resolve paradox {paradox_id}")
            
            return success
    
    def manipulate_causal_probability(
        self,
        event_id: str,
        target_probability: float,
        causal_propagation: bool = True
    ) -> bool:
        """
        Manipulate the probability of a causal event with loop-aware propagation.
        
        Args:
            event_id: ID of the event to manipulate
            target_probability: Desired probability
            causal_propagation: Whether to propagate through causal links
            
        Returns:
            True if manipulation successful
        """
        with self.system_lock:
            if event_id not in self.causal_events:
                return False
            
            event = self.causal_events[event_id]
            original_probability = event.probability
            
            # Validate target probability
            target_probability = max(0.0, min(1.0, target_probability))
            
            # Check for paradox creation
            if self._would_create_paradox(event_id, target_probability):
                self.logger.warning(f"Probability manipulation would create paradox for event {event_id}")
                
                # Try to resolve with dampening
                dampening_factor = self._calculate_paradox_dampening(event_id, target_probability)
                target_probability = original_probability + (target_probability - original_probability) * dampening_factor
            
            # Apply probability change
            event.probability = target_probability
            
            # Update causal graph
            self.causal_graph.nodes[event_id]['probability'] = target_probability
            
            # Propagate through causal network if requested
            if causal_propagation:
                self._propagate_probability_change(event_id, original_probability, target_probability)
            
            # Re-validate loops and paradoxes
            self._validate_causal_consistency()
            
            self.logger.info(f"Manipulated probability for event {event_id}: {original_probability:.4f} -> {target_probability:.4f}")
            return True
    
    def stabilize_causal_loops(self) -> Dict[str, float]:
        """
        Stabilize all detected causal loops to prevent paradoxes.
        
        Returns:
            Dictionary mapping loop IDs to stability scores
        """
        stability_scores = {}
        
        with self.system_lock:
            for loop_id, loop in self.causal_loops.items():
                original_stability = loop.stability
                
                # Apply stabilization techniques
                new_stability = self._apply_loop_stabilization(loop)
                
                loop.stability = new_stability
                stability_scores[loop_id] = new_stability
                
                self.logger.info(f"Stabilized loop {loop_id}: {original_stability:.3f} -> {new_stability:.3f}")
        
        return stability_scores
    
    def get_causal_analysis(self, event_id: str) -> Dict[str, Any]:
        """Get comprehensive causal analysis for an event."""
        if event_id not in self.causal_events:
            return {}
        
        event = self.causal_events[event_id]
        
        # Calculate causal influence
        influence_score = self._calculate_causal_influence(event_id)
        
        # Find causal chains
        causal_chains = self._find_causal_chains(event_id)
        
        # Calculate loop membership
        loop_memberships = [
            loop_id for loop_id, loop in self.causal_loops.items()
            if event_id in loop.events
        ]
        
        return {
            'event_id': event_id,
            'description': event.event_description,
            'probability': event.probability,
            'causal_strength': event.causal_strength,
            'temporal_displacement': event.temporal_displacement,
            'paradox_risk': event.paradox_risk,
            'direct_causes': len(event.causes),
            'direct_effects': len(event.effects),
            'causal_influence_score': influence_score,
            'causal_chains': len(causal_chains),
            'loop_memberships': loop_memberships,
            'timestamp': event.timestamp
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive causality system status."""
        total_events = len(self.causal_events)
        total_loops = len(self.causal_loops)
        total_paradoxes = len(self.paradox_registry)
        
        # Calculate system stability
        if total_loops > 0:
            avg_loop_stability = sum(loop.stability for loop in self.causal_loops.values()) / total_loops
        else:
            avg_loop_stability = 1.0
        
        # Calculate paradox severity distribution
        severity_levels = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for analysis in self.paradox_registry.values():
            if analysis.severity < 0.3:
                severity_levels["low"] += 1
            elif analysis.severity < 0.6:
                severity_levels["medium"] += 1
            elif analysis.severity < 0.9:
                severity_levels["high"] += 1
            else:
                severity_levels["critical"] += 1
        
        # Calculate graph properties
        graph_density = nx.density(self.causal_graph) if total_events > 1 else 0
        
        return {
            'total_causal_events': total_events,
            'total_causal_links': self.causal_graph.number_of_edges(),
            'total_causal_loops': total_loops,
            'total_paradoxes': total_paradoxes,
            'average_loop_stability': avg_loop_stability,
            'graph_density': graph_density,
            'paradox_severity_distribution': severity_levels,
            'system_consistency': self._calculate_system_consistency(),
            'temporal_violations': self._count_temporal_violations(),
            'max_loop_depth': self.max_loop_depth,
            'paradox_threshold': self.paradox_threshold
        }
    
    # Private helper methods
    
    def _calculate_initial_paradox_risk(
        self,
        timestamp: float,
        temporal_displacement: float,
        causal_strength: float
    ) -> float:
        """Calculate initial paradox risk for an event."""
        base_risk = 0.1
        
        # Increase risk for temporal displacement
        temporal_risk = min(0.5, abs(temporal_displacement) * 0.01)
        
        # Increase risk for high causal strength
        strength_risk = causal_strength * 0.1
        
        # Increase risk for events in the past
        current_time = time.time()
        if timestamp < current_time:
            time_risk = min(0.3, (current_time - timestamp) * 0.001)
        else:
            time_risk = 0.0
        
        total_risk = base_risk + temporal_risk + strength_risk + time_risk
        return min(1.0, total_risk)
    
    def _would_violate_causality(
        self,
        cause_event: CausalEvent,
        effect_event: CausalEvent,
        temporal_delay: float
    ) -> bool:
        """Check if a causal link would violate causality."""
        # Basic temporal ordering check
        if cause_event.timestamp + temporal_delay > effect_event.timestamp:
            return True
        
        # Check for faster-than-light information transfer
        if temporal_delay < self.PLANCK_TIME:
            return True
        
        # Check for existing reverse causality
        if self.causal_graph.has_edge(effect_event.event_id, cause_event.event_id):
            return True
        
        return False
    
    def _detect_and_register_loops(self) -> None:
        """Detect and register new causal loops."""
        try:
            cycles = list(nx.simple_cycles(self.causal_graph))
            
            for cycle in cycles:
                if len(cycle) > 1:
                    # Check if this loop is already registered
                    cycle_signature = tuple(sorted(cycle))
                    existing_loop = None
                    
                    for loop in self.causal_loops.values():
                        if tuple(sorted(loop.events)) == cycle_signature:
                            existing_loop = loop
                            break
                    
                    if not existing_loop:
                        self._register_causal_loop(cycle)
                        
        except nx.NetworkXError:
            pass  # Graph might be empty or have issues
    
    def _register_causal_loop(self, cycle: List[str]) -> Optional[str]:
        """Register a new causal loop."""
        loop_id = f"loop_{int(time.time() * 1000000)}"
        
        # Classify loop type
        loop_type = self._classify_loop_type(cycle)
        
        # Calculate loop properties
        loop_strength = self._calculate_loop_strength(cycle)
        temporal_span = self._calculate_temporal_span(cycle)
        paradox_level = self._calculate_loop_paradox_level(cycle)
        
        loop = CausalLoop(
            loop_id=loop_id,
            loop_type=loop_type,
            events=cycle,
            loop_strength=loop_strength,
            temporal_span=temporal_span,
            paradox_level=paradox_level,
            resolution_method=None,
            stability=1.0 - paradox_level,
            creation_time=time.time(),
            last_validated=time.time()
        )
        
        self.causal_loops[loop_id] = loop
        
        self.logger.info(f"Registered causal loop {loop_id} with {len(cycle)} events")
        return loop_id
    
    def _classify_loop_type(self, cycle: List[str]) -> CausalityType:
        """Classify the type of a causal loop."""
        if len(cycle) == 2:
            return CausalityType.FEEDBACK_LOOP
        
        # Check for temporal displacement
        has_temporal_displacement = any(
            self.causal_events[event_id].temporal_displacement != 0
            for event_id in cycle
        )
        
        if has_temporal_displacement:
            # Check for grandfather paradox patterns
            if self._has_grandfather_paradox_pattern(cycle):
                return CausalityType.GRANDFATHER_PARADOX
            
            # Check for bootstrap paradox patterns
            if self._has_bootstrap_paradox_pattern(cycle):
                return CausalityType.BOOTSTRAP_PARADOX
            
            return CausalityType.TEMPORAL_LOOP
        
        return CausalityType.CAUSAL_CHAIN
    
    def _calculate_loop_strength(self, cycle: List[str]) -> float:
        """Calculate the strength of a causal loop."""
        total_strength = 1.0
        
        for i in range(len(cycle)):
            current_event = cycle[i]
            next_event = cycle[(i + 1) % len(cycle)]
            
            if self.causal_graph.has_edge(current_event, next_event):
                edge_data = self.causal_graph[current_event][next_event]
                causal_strength = edge_data.get('causal_strength', 1.0)
                total_strength *= causal_strength
        
        return total_strength
    
    def _calculate_temporal_span(self, cycle: List[str]) -> float:
        """Calculate the temporal span of a causal loop."""
        timestamps = [self.causal_events[event_id].timestamp for event_id in cycle]
        return max(timestamps) - min(timestamps)
    
    def _calculate_loop_paradox_level(self, cycle: List[str]) -> float:
        """Calculate paradox level for a causal loop."""
        base_paradox = 0.0
        
        # Check for temporal violations
        for event_id in cycle:
            event = self.causal_events[event_id]
            base_paradox += event.paradox_risk
        
        # Normalize by cycle length
        base_paradox /= len(cycle)
        
        # Increase for certain loop types
        loop_type = self._classify_loop_type(cycle)
        if loop_type == CausalityType.GRANDFATHER_PARADOX:
            base_paradox *= 1.5
        elif loop_type == CausalityType.BOOTSTRAP_PARADOX:
            base_paradox *= 1.3
        elif loop_type == CausalityType.TEMPORAL_LOOP:
            base_paradox *= 1.2
        
        return min(1.0, base_paradox)
    
    def _classify_paradox(self, loop: CausalLoop) -> Tuple[str, float]:
        """Classify a paradox and calculate its severity."""
        if loop.loop_type == CausalityType.GRANDFATHER_PARADOX:
            severity = min(1.0, loop.paradox_level * 1.2)
            return "grandfather_paradox", severity
        
        elif loop.loop_type == CausalityType.BOOTSTRAP_PARADOX:
            severity = min(1.0, loop.paradox_level * 1.1)
            return "bootstrap_paradox", severity
        
        elif loop.loop_type == CausalityType.TEMPORAL_LOOP:
            severity = loop.paradox_level
            return "temporal_loop", severity
        
        else:
            severity = loop.paradox_level * 0.8
            return "causal_inconsistency", severity
    
    def _find_affected_events(self, loop: CausalLoop) -> List[str]:
        """Find all events affected by a causal loop."""
        affected = set(loop.events)
        
        # Add events that are causally connected to loop events
        for event_id in loop.events:
            event = self.causal_events[event_id]
            affected.update(event.causes)
            affected.update(event.effects)
        
        return list(affected)
    
    def _calculate_consistency_violation(self, loop: CausalLoop) -> float:
        """Calculate consistency violation level for a loop."""
        violation = 0.0
        
        for i in range(len(loop.events)):
            current_event_id = loop.events[i]
            next_event_id = loop.events[(i + 1) % len(loop.events)]
            
            current_event = self.causal_events[current_event_id]
            next_event = self.causal_events[next_event_id]
            
            # Check temporal consistency
            if current_event.timestamp >= next_event.timestamp:
                violation += 0.2
            
            # Check probability consistency
            prob_diff = abs(current_event.probability - next_event.probability)
            if prob_diff > 0.5:
                violation += prob_diff * 0.1
        
        return min(1.0, violation)
    
    def _calculate_temporal_impact(self, loop: CausalLoop) -> float:
        """Calculate temporal impact of a causal loop."""
        impact = 0.0
        
        # Impact increases with temporal span
        if loop.temporal_span > 0:
            impact += min(0.5, loop.temporal_span / 86400)  # Normalize by day
        
        # Impact increases with number of events
        impact += min(0.3, len(loop.events) / 10)
        
        # Impact increases with paradox level
        impact += loop.paradox_level * 0.2
        
        return min(1.0, impact)
    
    def _determine_resolution_options(
        self,
        paradox_type: str,
        severity: float
    ) -> List[ParadoxResolution]:
        """Determine possible resolution options for a paradox."""
        options = []
        
        if severity < 0.3:
            options.append(ParadoxResolution.PROBABILITY_DAMPENING)
        
        if severity < 0.6:
            options.extend([
                ParadoxResolution.NOVIKOV_CONSISTENCY,
                ParadoxResolution.TIMELINE_REPAIR
            ])
        
        if severity < 0.9:
            options.extend([
                ParadoxResolution.MANY_WORLDS,
                ParadoxResolution.CAUSAL_ISOLATION
            ])
        
        if severity >= 0.9:
            options.append(ParadoxResolution.QUANTUM_SUPERPOSITION)
        
        return options
    
    def _recommend_paradox_resolution(
        self,
        paradox_type: str,
        severity: float,
        options: List[ParadoxResolution]
    ) -> str:
        """Recommend the best resolution method."""
        if not options:
            return ParadoxResolution.NOVIKOV_CONSISTENCY.value
        
        # Choose based on severity and type
        if severity < 0.5:
            return ParadoxResolution.PROBABILITY_DAMPENING.value
        elif severity < 0.8:
            return ParadoxResolution.NOVIKOV_CONSISTENCY.value
        else:
            return ParadoxResolution.MANY_WORLDS.value
    
    def _apply_novikov_consistency(self, analysis: ParadoxAnalysis) -> bool:
        """Apply Novikov self-consistency principle."""
        # Adjust probabilities to maintain consistency
        for event_id in analysis.affected_events:
            if event_id in self.causal_events:
                event = self.causal_events[event_id]
                # Reduce probability of paradox-causing changes
                consistency_factor = 1.0 - analysis.consistency_violation
                event.probability *= consistency_factor
                event.paradox_risk *= 0.5
        
        return True
    
    def _apply_many_worlds_resolution(self, analysis: ParadoxAnalysis) -> bool:
        """Apply many-worlds interpretation to resolve paradox."""
        # Create alternate timeline probability distributions
        for event_id in analysis.affected_events:
            if event_id in self.causal_events:
                event = self.causal_events[event_id]
                # Split probability across multiple worlds
                event.probability *= 0.5  # This world
                event.metadata['alternate_probability'] = event.probability  # Other world
                event.paradox_risk = 0.0  # Resolved in multiverse
        
        return True
    
    def _apply_timeline_repair(self, analysis: ParadoxAnalysis) -> bool:
        """Apply timeline repair to fix paradox."""
        # Identify and repair causal inconsistencies
        for event_id in analysis.affected_events:
            if event_id in self.causal_events:
                event = self.causal_events[event_id]
                # Repair temporal ordering
                if event.temporal_displacement != 0:
                    event.temporal_displacement *= 0.1  # Reduce displacement
                event.paradox_risk *= 0.3
        
        return True
    
    def _apply_probability_dampening(self, analysis: ParadoxAnalysis) -> bool:
        """Apply probability dampening to reduce paradox."""
        dampening_factor = 1.0 - analysis.severity * 0.5
        
        for event_id in analysis.affected_events:
            if event_id in self.causal_events:
                event = self.causal_events[event_id]
                # Dampen extreme probabilities
                if event.probability > 0.8:
                    event.probability = 0.8 * dampening_factor + event.probability * (1 - dampening_factor)
                elif event.probability < 0.2:
                    event.probability = 0.2 * dampening_factor + event.probability * (1 - dampening_factor)
                
                event.paradox_risk *= dampening_factor
        
        return True
    
    def _apply_causal_isolation(self, analysis: ParadoxAnalysis) -> bool:
        """Apply causal isolation to contain paradox."""
        # Isolate paradox-causing events
        for event_id in analysis.affected_events:
            if event_id in self.causal_events:
                event = self.causal_events[event_id]
                # Reduce causal strength
                event.causal_strength *= 0.5
                # Remove some causal links
                if len(event.effects) > 1:
                    event.effects = event.effects[:len(event.effects)//2]
        
        return True
    
    def _apply_quantum_superposition(self, analysis: ParadoxAnalysis) -> bool:
        """Apply quantum superposition to resolve paradox."""
        # Put paradox-causing events in superposition
        for event_id in analysis.affected_events:
            if event_id in self.causal_events:
                event = self.causal_events[event_id]
                # Create superposition state
                event.metadata['superposition_amplitudes'] = [
                    complex(math.sqrt(event.probability), 0),
                    complex(math.sqrt(1 - event.probability), 0)
                ]
                event.paradox_risk = 0.0  # Resolved in superposition
        
        return True
    
    def _would_create_paradox(self, event_id: str, new_probability: float) -> bool:
        """Check if changing an event's probability would create a paradox."""
        if event_id not in self.causal_events:
            return False
        
        event = self.causal_events[event_id]
        probability_change = abs(new_probability - event.probability)
        
        # Large probability changes in temporal loops are risky
        if event.temporal_displacement != 0 and probability_change > 0.5:
            return True
        
        # Check if event is in a high-risk loop
        for loop in self.causal_loops.values():
            if event_id in loop.events and loop.paradox_level > self.paradox_threshold:
                return True
        
        return False
    
    def _calculate_paradox_dampening(self, event_id: str, target_probability: float) -> float:
        """Calculate dampening factor to prevent paradox creation."""
        if event_id not in self.causal_events:
            return 1.0
        
        event = self.causal_events[event_id]
        base_dampening = 1.0
        
        # Reduce dampening for events in paradoxical loops
        for loop in self.causal_loops.values():
            if event_id in loop.events:
                base_dampening *= (1.0 - loop.paradox_level * 0.5)
        
        # Reduce dampening for large probability changes
        probability_change = abs(target_probability - event.probability)
        if probability_change > 0.3:
            base_dampening *= 0.5
        
        return max(0.1, base_dampening)
    
    def _propagate_probability_change(
        self,
        event_id: str,
        old_probability: float,
        new_probability: float
    ) -> None:
        """Propagate probability changes through causal network."""
        change_ratio = new_probability / old_probability if old_probability > 0 else 1.0
        visited = set()
        
        def propagate_recursive(current_id: str, depth: int, propagation_strength: float):
            if depth > 5 or current_id in visited or propagation_strength < 0.01:
                return
            
            visited.add(current_id)
            
            if current_id in self.causal_events:
                event = self.causal_events[current_id]
                
                # Propagate to effects
                for effect_id in event.effects:
                    if effect_id in self.causal_events:
                        effect_event = self.causal_events[effect_id]
                        
                        # Calculate propagated change
                        if self.causal_graph.has_edge(current_id, effect_id):
                            edge_data = self.causal_graph[current_id][effect_id]
                            causal_strength = edge_data.get('causal_strength', 1.0)
                            
                            propagated_change = (change_ratio - 1.0) * causal_strength * propagation_strength
                            new_effect_probability = effect_event.probability * (1.0 + propagated_change * 0.1)
                            new_effect_probability = max(0.0, min(1.0, new_effect_probability))
                            
                            effect_event.probability = new_effect_probability
                            
                            # Continue propagation with reduced strength
                            propagate_recursive(effect_id, depth + 1, propagation_strength * 0.7)
        
        propagate_recursive(event_id, 0, 1.0)
    
    def _validate_causal_consistency(self) -> None:
        """Validate consistency of the entire causal system."""
        # Re-detect loops
        self.detect_causal_loops()
        
        # Update paradox risks
        for event_id in self.causal_events:
            self._update_paradox_risks([event_id])
    
    def _update_paradox_risks(self, event_ids: List[str]) -> None:
        """Update paradox risks for specified events."""
        for event_id in event_ids:
            if event_id in self.causal_events:
                event = self.causal_events[event_id]
                
                # Recalculate paradox risk based on current state
                base_risk = self._calculate_initial_paradox_risk(
                    event.timestamp, event.temporal_displacement, event.causal_strength
                )
                
                # Add risk from loop membership
                loop_risk = 0.0
                for loop in self.causal_loops.values():
                    if event_id in loop.events:
                        loop_risk = max(loop_risk, loop.paradox_level)
                
                event.paradox_risk = min(1.0, base_risk + loop_risk * 0.5)
    
    def _apply_loop_stabilization(self, loop: CausalLoop) -> float:
        """Apply stabilization techniques to a causal loop."""
        original_stability = loop.stability
        
        # Reduce extreme probabilities in loop events
        for event_id in loop.events:
            if event_id in self.causal_events:
                event = self.causal_events[event_id]
                
                if event.probability > 0.9:
                    event.probability = 0.9
                elif event.probability < 0.1:
                    event.probability = 0.1
        
        # Reduce causal strengths if too high
        for i in range(len(loop.events)):
            current_event = loop.events[i]
            next_event = loop.events[(i + 1) % len(loop.events)]
            
            if self.causal_graph.has_edge(current_event, next_event):
                edge_data = self.causal_graph[current_event][next_event]
                if edge_data.get('causal_strength', 1.0) > 0.8:
                    edge_data['causal_strength'] = 0.8
        
        # Recalculate stability
        new_paradox_level = self._calculate_loop_paradox_level(loop.events)
        new_stability = 1.0 - new_paradox_level
        
        return max(original_stability, new_stability)
    
    def _calculate_causal_influence(self, event_id: str) -> float:
        """Calculate the causal influence score of an event."""
        if event_id not in self.causal_events:
            return 0.0
        
        event = self.causal_events[event_id]
        
        # Base influence from direct connections
        direct_influence = len(event.effects) * 0.1 + len(event.causes) * 0.05
        
        # Influence from causal strength
        strength_influence = event.causal_strength * 0.2
        
        # Influence from probability
        probability_influence = event.probability * 0.1
        
        # Influence from loop membership
        loop_influence = 0.0
        for loop in self.causal_loops.values():
            if event_id in loop.events:
                loop_influence += loop.loop_strength * 0.1
        
        total_influence = direct_influence + strength_influence + probability_influence + loop_influence
        return min(1.0, total_influence)
    
    def _find_causal_chains(self, event_id: str) -> List[List[str]]:
        """Find all causal chains involving an event."""
        chains = []
        
        if event_id not in self.causal_events:
            return chains
        
        # Find chains starting from this event
        def find_chains_recursive(current_id: str, current_chain: List[str], max_depth: int = 5):
            if len(current_chain) > max_depth:
                return
            
            if current_id in self.causal_events:
                event = self.causal_events[current_id]
                
                for effect_id in event.effects:
                    if effect_id not in current_chain:  # Avoid cycles in chain finding
                        new_chain = current_chain + [effect_id]
                        chains.append(new_chain)
                        find_chains_recursive(effect_id, new_chain, max_depth)
        
        find_chains_recursive(event_id, [event_id])
        return chains
    
    def _has_grandfather_paradox_pattern(self, cycle: List[str]) -> bool:
        """Check if a cycle has grandfather paradox patterns."""
        # Look for events that could prevent their own causes
        for event_id in cycle:
            event = self.causal_events[event_id]
            
            # Check if this event affects its own past
            if event.temporal_displacement < 0:  # Goes back in time
                for cause_id in event.causes:
                    if cause_id in cycle:
                        cause_event = self.causal_events[cause_id]
                        if cause_event.timestamp > event.timestamp + event.temporal_displacement:
                            return True
        
        return False
    
    def _has_bootstrap_paradox_pattern(self, cycle: List[str]) -> bool:
        """Check if a cycle has bootstrap paradox patterns."""
        # Look for information/objects that create themselves
        for event_id in cycle:
            event = self.causal_events[event_id]
            
            # Check if this event is its own ultimate cause
            if event.temporal_displacement != 0:
                # Trace the causal chain
                visited = set()
                current = event_id
                
                while current not in visited and current in self.causal_events:
                    visited.add(current)
                    current_event = self.causal_events[current]
                    
                    # If we find a cause that is the original event, it's a bootstrap paradox
                    for cause_id in current_event.causes:
                        if cause_id == event_id:
                            return True
                        current = cause_id
                        break
                    else:
                        break
        
        return False
    
    def _calculate_system_consistency(self) -> float:
        """Calculate overall system consistency."""
        if not self.causal_events:
            return 1.0
        
        total_consistency = 0.0
        total_events = len(self.causal_events)
        
        for event in self.causal_events.values():
            event_consistency = 1.0 - event.paradox_risk
            total_consistency += event_consistency
        
        return total_consistency / total_events
    
    def _count_temporal_violations(self) -> int:
        """Count the number of temporal causality violations."""
        violations = 0
        
        for edge in self.causal_graph.edges(data=True):
            cause_id, effect_id, edge_data = edge
            
            if cause_id in self.causal_events and effect_id in self.causal_events:
                cause_event = self.causal_events[cause_id]
                effect_event = self.causal_events[effect_id]
                
                temporal_delay = edge_data.get('temporal_delay', 0.0)
                
                # Check if cause happens after effect
                if cause_event.timestamp + temporal_delay > effect_event.timestamp:
                    violations += 1
        
        return violations