"""
Paradox Resolution Engine
========================

Advanced engine for detecting, analyzing, and resolving paradoxes
across the multiverse framework to maintain causal consistency.
"""

import numpy as np
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict
import math

from ..core.base_multiverse import MultiverseComponent
from ..core.config_manager import get_global_config


class ParadoxType(Enum):
    """Types of paradoxes that can occur in the multiverse."""
    GRANDFATHER = "grandfather"
    BOOTSTRAP = "bootstrap"
    CAUSAL_LOOP = "causal_loop"
    INFORMATION = "information"
    ONTOLOGICAL = "ontological"
    TEMPORAL_DISPLACEMENT = "temporal_displacement"
    QUANTUM_ENTANGLEMENT = "quantum_entanglement"
    CONSCIOUSNESS_SPLIT = "consciousness_split"
    REALITY_CONVERGENCE = "reality_convergence"
    DIMENSIONAL_BREACH = "dimensional_breach"
    TIMELINE_COLLAPSE = "timeline_collapse"


class ParadoxSeverity(Enum):
    """Severity levels of paradoxes."""
    MINOR = 1
    MODERATE = 2
    SEVERE = 3
    CRITICAL = 4
    CATASTROPHIC = 5


class ResolutionStrategy(Enum):
    """Strategies for resolving paradoxes."""
    TIMELINE_SPLIT = "timeline_split"
    QUANTUM_SUPERPOSITION = "quantum_superposition"
    CAUSAL_ISOLATION = "causal_isolation"
    REALITY_ANCHOR = "reality_anchor"
    TEMPORAL_CORRECTION = "temporal_correction"
    DIMENSIONAL_QUARANTINE = "dimensional_quarantine"
    CONSCIOUSNESS_PARTITION = "consciousness_partition"
    INFORMATION_ERASURE = "information_erasure"
    UNIVERSE_TERMINATION = "universe_termination"
    OBSERVER_RELOCATION = "observer_relocation"


@dataclass
class ParadoxEvent:
    """Represents a detected paradox event."""
    paradox_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    paradox_type: ParadoxType = ParadoxType.CAUSAL_LOOP
    severity: ParadoxSeverity = ParadoxSeverity.MODERATE
    detection_time: float = field(default_factory=time.time)
    
    # Location and context
    universe_id: str = ""
    timeline_id: Optional[str] = None
    dimensional_coordinates: Optional[Any] = None
    
    # Paradox details
    description: str = ""
    causal_chain: List[str] = field(default_factory=list)
    affected_entities: List[str] = field(default_factory=list)
    temporal_range: Tuple[float, float] = (0.0, 0.0)
    
    # Resolution tracking
    resolution_strategy: Optional[ResolutionStrategy] = None
    resolution_status: str = "unresolved"
    resolution_time: Optional[float] = None
    resolution_success: Optional[bool] = None
    
    # Analysis data
    causality_violation_score: float = 0.0
    temporal_consistency_score: float = 1.0
    reality_stability_impact: float = 0.0
    
    # Metadata
    detected_by: str = "paradox_resolution_engine"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_priority_score(self) -> float:
        """Calculate priority score for resolution."""
        severity_weight = self.severity.value * 0.3
        violation_weight = self.causality_violation_score * 0.4
        stability_weight = self.reality_stability_impact * 0.3
        
        return severity_weight + violation_weight + stability_weight
    
    def get_affected_scope(self) -> Dict[str, int]:
        """Get scope of paradox effects."""
        return {
            'universes': 1 if self.universe_id else 0,
            'timelines': 1 if self.timeline_id else 0,
            'entities': len(self.affected_entities),
            'temporal_span': self.temporal_range[1] - self.temporal_range[0]
        }


class ParadoxResolutionEngine(MultiverseComponent):
    """
    Engine for detecting and resolving paradoxes in the multiverse.
    
    Monitors for paradoxical situations, analyzes their impact,
    and implements appropriate resolution strategies to maintain
    causal consistency and reality stability.
    """
    
    def __init__(self, multiverse_manager=None):
        """Initialize the paradox resolution engine."""
        super().__init__("ParadoxResolutionEngine")
        
        self.multiverse_manager = multiverse_manager
        self.config = get_global_config()
        
        # Paradox tracking
        self.detected_paradoxes: Dict[str, ParadoxEvent] = {}
        self.resolved_paradoxes: List[ParadoxEvent] = []
        self.paradox_lock = threading.RLock()
        
        # Detection parameters
        self.detection_sensitivity = 0.8  # 0-1 scale
        self.causality_threshold = 0.3
        self.temporal_consistency_threshold = 0.7
        self.auto_resolution_threshold = 0.9
        
        # Resolution strategies ranking
        self.strategy_preferences = {
            ParadoxType.GRANDFATHER: [
                ResolutionStrategy.TIMELINE_SPLIT,
                ResolutionStrategy.QUANTUM_SUPERPOSITION,
                ResolutionStrategy.TEMPORAL_CORRECTION
            ],
            ParadoxType.BOOTSTRAP: [
                ResolutionStrategy.CAUSAL_ISOLATION,
                ResolutionStrategy.INFORMATION_ERASURE,
                ResolutionStrategy.TIMELINE_SPLIT
            ],
            ParadoxType.CAUSAL_LOOP: [
                ResolutionStrategy.TEMPORAL_CORRECTION,
                ResolutionStrategy.CAUSAL_ISOLATION,
                ResolutionStrategy.TIMELINE_SPLIT
            ],
            ParadoxType.QUANTUM_ENTANGLEMENT: [
                ResolutionStrategy.QUANTUM_SUPERPOSITION,
                ResolutionStrategy.DIMENSIONAL_QUARANTINE,
                ResolutionStrategy.REALITY_ANCHOR
            ]
        }
        
        # Monitoring
        self.monitoring_interval = 5.0  # seconds
        self.resolution_timeout = 300.0  # 5 minutes
        
        # Statistics
        self.total_paradoxes_detected = 0
        self.total_paradoxes_resolved = 0
        self.resolution_success_rate = 0.0
        self.critical_paradox_count = 0
        
        self.logger.info("ParadoxResolutionEngine initialized")
    
    def on_start(self):
        """Start paradox resolution."""
        self.logger.info("Paradox resolution started")
        self.update_property("status", "monitoring")
        
        # Start monitoring thread
        self._start_monitoring_thread()
    
    def on_stop(self):
        """Stop paradox resolution."""
        self.logger.info("Paradox resolution stopped")
        self.update_property("status", "stopped")
    
    def _start_monitoring_thread(self):
        """Start paradox monitoring thread."""
        def monitor_paradoxes():
            while self.is_running:
                try:
                    self._scan_for_paradoxes()
                    self._process_detected_paradoxes()
                    self._check_resolution_timeouts()
                    time.sleep(self.monitoring_interval)
                except Exception as e:
                    self.logger.error("Error in paradox monitoring: %s", e)
                    time.sleep(1.0)
        
        monitor_thread = threading.Thread(
            target=monitor_paradoxes,
            daemon=True,
            name="ParadoxMonitor"
        )
        monitor_thread.start()
    
    def detect_paradox(self, paradox_type: ParadoxType,
                      universe_id: str,
                      description: str,
                      severity: ParadoxSeverity = ParadoxSeverity.MODERATE,
                      **kwargs) -> str:
        """
        Manually report a detected paradox.
        
        Args:
            paradox_type: Type of paradox
            universe_id: Affected universe
            description: Paradox description
            severity: Paradox severity
            **kwargs: Additional paradox properties
            
        Returns:
            Paradox ID
        """
        try:
            self.track_operation("detect_paradox")
            
            paradox = ParadoxEvent(
                paradox_type=paradox_type,
                universe_id=universe_id,
                description=description,
                severity=severity
            )
            
            # Apply additional properties
            for key, value in kwargs.items():
                if hasattr(paradox, key):
                    setattr(paradox, key, value)
            
            # Analyze paradox
            self._analyze_paradox(paradox)
            
            # Store paradox
            with self.paradox_lock:
                self.detected_paradoxes[paradox.paradox_id] = paradox
                self.total_paradoxes_detected += 1
                
                if severity == ParadoxSeverity.CRITICAL:
                    self.critical_paradox_count += 1
            
            self.emit_event("paradox_detected", {
                'paradox_id': paradox.paradox_id,
                'paradox_type': paradox_type.value,
                'severity': severity.value,
                'universe_id': universe_id
            })
            
            self.logger.warning("Paradox detected: %s (%s) in universe %s",
                              paradox.paradox_id, paradox_type.value, universe_id)
            
            # Auto-resolve if appropriate
            if self._should_auto_resolve(paradox):
                self.resolve_paradox(paradox.paradox_id)
            
            return paradox.paradox_id
            
        except Exception as e:
            self.logger.error("Error detecting paradox: %s", e)
            self.track_error(e, "detect_paradox")
            return ""
    
    def _analyze_paradox(self, paradox: ParadoxEvent):
        """Analyze a paradox to determine its properties and impact."""
        # Calculate causality violation score
        paradox.causality_violation_score = self._calculate_causality_violation(paradox)
        
        # Calculate temporal consistency score
        paradox.temporal_consistency_score = self._calculate_temporal_consistency(paradox)
        
        # Calculate reality stability impact
        paradox.reality_stability_impact = self._calculate_stability_impact(paradox)
        
        # Adjust severity based on analysis
        if paradox.causality_violation_score > 0.8:
            paradox.severity = max(paradox.severity, ParadoxSeverity.SEVERE)
        
        if paradox.reality_stability_impact > 0.9:
            paradox.severity = ParadoxSeverity.CATASTROPHIC
    
    def _calculate_causality_violation(self, paradox: ParadoxEvent) -> float:
        """Calculate the degree of causality violation."""
        # Base violation score based on type
        type_scores = {
            ParadoxType.GRANDFATHER: 0.9,
            ParadoxType.BOOTSTRAP: 0.7,
            ParadoxType.CAUSAL_LOOP: 0.8,
            ParadoxType.INFORMATION: 0.6,
            ParadoxType.ONTOLOGICAL: 0.8,
            ParadoxType.TEMPORAL_DISPLACEMENT: 0.5,
            ParadoxType.QUANTUM_ENTANGLEMENT: 0.4,
            ParadoxType.CONSCIOUSNESS_SPLIT: 0.6,
            ParadoxType.REALITY_CONVERGENCE: 0.5,
            ParadoxType.DIMENSIONAL_BREACH: 0.7,
            ParadoxType.TIMELINE_COLLAPSE: 1.0
        }
        
        base_score = type_scores.get(paradox.paradox_type, 0.5)
        
        # Adjust based on affected entities
        entity_factor = min(1.0, len(paradox.affected_entities) / 10.0)
        
        # Adjust based on temporal range
        temporal_span = paradox.temporal_range[1] - paradox.temporal_range[0]
        temporal_factor = min(1.0, temporal_span / 86400.0)  # Scale by day
        
        return min(1.0, base_score * (1.0 + entity_factor * 0.3 + temporal_factor * 0.2))
    
    def _calculate_temporal_consistency(self, paradox: ParadoxEvent) -> float:
        """Calculate temporal consistency score."""
        # Higher violations lead to lower consistency
        violation_penalty = paradox.causality_violation_score * 0.5
        
        # Check for causal chain integrity
        chain_consistency = 1.0
        if len(paradox.causal_chain) > 1:
            # Simplified consistency check
            chain_consistency = max(0.0, 1.0 - len(paradox.causal_chain) * 0.1)
        
        return max(0.0, chain_consistency - violation_penalty)
    
    def _calculate_stability_impact(self, paradox: ParadoxEvent) -> float:
        """Calculate impact on reality stability."""
        # Base impact from severity
        severity_impact = paradox.severity.value * 0.2
        
        # Impact from causality violation
        causality_impact = paradox.causality_violation_score * 0.4
        
        # Impact from temporal inconsistency
        temporal_impact = (1.0 - paradox.temporal_consistency_score) * 0.3
        
        # Impact from scope
        scope = paradox.get_affected_scope()
        scope_impact = min(1.0, scope['entities'] / 100.0) * 0.1
        
        return min(1.0, severity_impact + causality_impact + temporal_impact + scope_impact)
    
    def _should_auto_resolve(self, paradox: ParadoxEvent) -> bool:
        """Determine if paradox should be auto-resolved."""
        priority_score = paradox.calculate_priority_score()
        
        return (priority_score >= self.auto_resolution_threshold or
                paradox.severity in [ParadoxSeverity.CRITICAL, ParadoxSeverity.CATASTROPHIC])
    
    def resolve_paradox(self, paradox_id: str, 
                       strategy: Optional[ResolutionStrategy] = None) -> bool:
        """
        Resolve a detected paradox.
        
        Args:
            paradox_id: ID of paradox to resolve
            strategy: Specific resolution strategy (optional)
            
        Returns:
            True if resolution successful, False otherwise
        """
        try:
            self.track_operation("resolve_paradox")
            
            with self.paradox_lock:
                paradox = self.detected_paradoxes.get(paradox_id)
                if not paradox:
                    self.logger.error("Paradox not found: %s", paradox_id)
                    return False
                
                if paradox.resolution_status != "unresolved":
                    self.logger.warning("Paradox already being resolved: %s", paradox_id)
                    return False
                
                paradox.resolution_status = "resolving"
            
            # Select resolution strategy
            if not strategy:
                strategy = self._select_resolution_strategy(paradox)
            
            if not strategy:
                self.logger.error("No suitable resolution strategy for paradox %s", paradox_id)
                return False
            
            paradox.resolution_strategy = strategy
            
            # Execute resolution
            success = self._execute_resolution(paradox, strategy)
            
            # Update paradox status
            paradox.resolution_time = time.time()
            paradox.resolution_success = success
            
            if success:
                paradox.resolution_status = "resolved"
                with self.paradox_lock:
                    # Move to resolved list
                    del self.detected_paradoxes[paradox_id]
                    self.resolved_paradoxes.append(paradox)
                    self.total_paradoxes_resolved += 1
                
                self.emit_event("paradox_resolved", {
                    'paradox_id': paradox_id,
                    'strategy': strategy.value,
                    'resolution_time': paradox.resolution_time
                })
                
                self.logger.info("Paradox resolved: %s using %s", 
                               paradox_id, strategy.value)
            else:
                paradox.resolution_status = "failed"
                
                self.emit_event("paradox_resolution_failed", {
                    'paradox_id': paradox_id,
                    'strategy': strategy.value
                })
                
                self.logger.error("Failed to resolve paradox: %s", paradox_id)
            
            # Update success rate
            self._update_success_rate()
            
            return success
            
        except Exception as e:
            self.logger.error("Error resolving paradox %s: %s", paradox_id, e)
            self.track_error(e, "resolve_paradox")
            return False
    
    def _select_resolution_strategy(self, paradox: ParadoxEvent) -> Optional[ResolutionStrategy]:
        """Select the best resolution strategy for a paradox."""
        # Get preferred strategies for this paradox type
        preferred_strategies = self.strategy_preferences.get(
            paradox.paradox_type, 
            [ResolutionStrategy.TIMELINE_SPLIT]
        )
        
        # Score strategies based on paradox characteristics
        strategy_scores = {}
        
        for strategy in preferred_strategies:
            score = self._score_resolution_strategy(paradox, strategy)
            strategy_scores[strategy] = score
        
        # Select highest scoring strategy
        if strategy_scores:
            best_strategy = max(strategy_scores, key=strategy_scores.get)
            return best_strategy
        
        return None
    
    def _score_resolution_strategy(self, paradox: ParadoxEvent, 
                                  strategy: ResolutionStrategy) -> float:
        """Score a resolution strategy for a specific paradox."""
        base_score = 0.5
        
        # Type-specific scoring
        if paradox.paradox_type == ParadoxType.GRANDFATHER:
            if strategy == ResolutionStrategy.TIMELINE_SPLIT:
                base_score = 0.9
            elif strategy == ResolutionStrategy.QUANTUM_SUPERPOSITION:
                base_score = 0.8
        elif paradox.paradox_type == ParadoxType.BOOTSTRAP:
            if strategy == ResolutionStrategy.CAUSAL_ISOLATION:
                base_score = 0.9
            elif strategy == ResolutionStrategy.INFORMATION_ERASURE:
                base_score = 0.8
        elif paradox.paradox_type == ParadoxType.CAUSAL_LOOP:
            if strategy == ResolutionStrategy.TEMPORAL_CORRECTION:
                base_score = 0.9
        
        # Severity adjustments
        if paradox.severity == ParadoxSeverity.CATASTROPHIC:
            if strategy == ResolutionStrategy.UNIVERSE_TERMINATION:
                base_score += 0.3
        
        # Stability impact adjustments
        if paradox.reality_stability_impact > 0.8:
            if strategy in [ResolutionStrategy.REALITY_ANCHOR, 
                          ResolutionStrategy.DIMENSIONAL_QUARANTINE]:
                base_score += 0.2
        
        return min(1.0, base_score)
    
    def _execute_resolution(self, paradox: ParadoxEvent, 
                           strategy: ResolutionStrategy) -> bool:
        """Execute a specific resolution strategy."""
        try:
            if strategy == ResolutionStrategy.TIMELINE_SPLIT:
                return self._execute_timeline_split(paradox)
            elif strategy == ResolutionStrategy.QUANTUM_SUPERPOSITION:
                return self._execute_quantum_superposition(paradox)
            elif strategy == ResolutionStrategy.CAUSAL_ISOLATION:
                return self._execute_causal_isolation(paradox)
            elif strategy == ResolutionStrategy.REALITY_ANCHOR:
                return self._execute_reality_anchor(paradox)
            elif strategy == ResolutionStrategy.TEMPORAL_CORRECTION:
                return self._execute_temporal_correction(paradox)
            elif strategy == ResolutionStrategy.DIMENSIONAL_QUARANTINE:
                return self._execute_dimensional_quarantine(paradox)
            elif strategy == ResolutionStrategy.INFORMATION_ERASURE:
                return self._execute_information_erasure(paradox)
            elif strategy == ResolutionStrategy.UNIVERSE_TERMINATION:
                return self._execute_universe_termination(paradox)
            else:
                self.logger.warning("Unknown resolution strategy: %s", strategy)
                return False
                
        except Exception as e:
            self.logger.error("Error executing resolution strategy %s: %s", strategy, e)
            return False
    
    def _execute_timeline_split(self, paradox: ParadoxEvent) -> bool:
        """Execute timeline split resolution."""
        if not self.multiverse_manager:
            return False
        
        # Create new timeline branch to resolve paradox
        new_universe_id = self.multiverse_manager.branch_universe(
            paradox.universe_id,
            quantum_deviation=0.5
        )
        
        if new_universe_id:
            paradox.metadata['resolution_details'] = {
                'new_universe_id': new_universe_id,
                'original_universe_id': paradox.universe_id
            }
            return True
        
        return False
    
    def _execute_quantum_superposition(self, paradox: ParadoxEvent) -> bool:
        """Execute quantum superposition resolution."""
        # Create quantum superposition state to allow multiple outcomes
        if not self.multiverse_manager:
            return False
        
        universe = self.multiverse_manager.get_universe(paradox.universe_id)
        if universe and universe.quantum_state:
            # Create superposition of the quantum state
            superposition_state = universe.quantum_state.create_superposition()
            universe.quantum_state = superposition_state
            
            paradox.metadata['resolution_details'] = {
                'superposition_created': True,
                'original_purity': universe.quantum_state.calculate_purity()
            }
            return True
        
        return False
    
    def _execute_causal_isolation(self, paradox: ParadoxEvent) -> bool:
        """Execute causal isolation resolution."""
        # Isolate the causal chain to prevent paradox propagation
        paradox.metadata['resolution_details'] = {
            'isolated_entities': paradox.affected_entities.copy(),
            'isolation_strength': 0.9
        }
        
        # In a full implementation, this would actually isolate the entities
        return True
    
    def _execute_reality_anchor(self, paradox: ParadoxEvent) -> bool:
        """Execute reality anchor resolution."""
        # Deploy reality anchor to stabilize the affected region
        paradox.metadata['resolution_details'] = {
            'anchor_deployed': True,
            'anchor_strength': 1.0,
            'stabilization_radius': 50.0
        }
        
        # In a full implementation, this would deploy actual reality anchors
        return True
    
    def _execute_temporal_correction(self, paradox: ParadoxEvent) -> bool:
        """Execute temporal correction resolution."""
        # Correct temporal inconsistencies
        paradox.metadata['resolution_details'] = {
            'temporal_adjustment': True,
            'correction_magnitude': paradox.causality_violation_score,
            'timeline_stability_restored': True
        }
        
        return True
    
    def _execute_dimensional_quarantine(self, paradox: ParadoxEvent) -> bool:
        """Execute dimensional quarantine resolution."""
        # Quarantine the affected dimensional region
        paradox.metadata['resolution_details'] = {
            'quarantine_established': True,
            'quarantine_boundary': 'dimensional_barrier',
            'containment_strength': 0.95
        }
        
        return True
    
    def _execute_information_erasure(self, paradox: ParadoxEvent) -> bool:
        """Execute information erasure resolution."""
        # Erase paradoxical information from the timeline
        paradox.metadata['resolution_details'] = {
            'information_erased': True,
            'erasure_scope': 'causal_chain',
            'memory_adjustment': True
        }
        
        return True
    
    def _execute_universe_termination(self, paradox: ParadoxEvent) -> bool:
        """Execute universe termination resolution (last resort)."""
        if not self.multiverse_manager:
            return False
        
        # This is a catastrophic resolution - only for universe-ending paradoxes
        if paradox.severity != ParadoxSeverity.CATASTROPHIC:
            return False
        
        # In a full implementation, this would terminate the universe
        paradox.metadata['resolution_details'] = {
            'universe_terminated': True,
            'termination_reason': 'catastrophic_paradox',
            'backup_created': True
        }
        
        return True
    
    def _scan_for_paradoxes(self):
        """Scan for potential paradoxes in the multiverse."""
        if not self.multiverse_manager:
            return
        
        universes = self.multiverse_manager.list_universes()
        
        for universe_id, universe_info in universes.items():
            # Check for timeline inconsistencies
            self._check_timeline_paradoxes(universe_id)
            
            # Check for causality violations
            self._check_causality_paradoxes(universe_id)
            
            # Check for quantum paradoxes
            self._check_quantum_paradoxes(universe_id)
    
    def _check_timeline_paradoxes(self, universe_id: str):
        """Check for timeline-related paradoxes."""
        # Simplified paradox detection
        # In full implementation, would analyze timeline events
        pass
    
    def _check_causality_paradoxes(self, universe_id: str):
        """Check for causality violations."""
        # Simplified causality checking
        # In full implementation, would analyze causal chains
        pass
    
    def _check_quantum_paradoxes(self, universe_id: str):
        """Check for quantum-related paradoxes."""
        # Simplified quantum paradox detection
        # In full implementation, would analyze quantum states
        pass
    
    def _process_detected_paradoxes(self):
        """Process all detected paradoxes."""
        with self.paradox_lock:
            unresolved_paradoxes = list(self.detected_paradoxes.values())
        
        # Sort by priority
        unresolved_paradoxes.sort(
            key=lambda p: p.calculate_priority_score(), 
            reverse=True
        )
        
        # Process high-priority paradoxes
        for paradox in unresolved_paradoxes[:5]:  # Limit concurrent resolutions
            if paradox.resolution_status == "unresolved":
                if self._should_auto_resolve(paradox):
                    self.resolve_paradox(paradox.paradox_id)
    
    def _check_resolution_timeouts(self):
        """Check for resolution timeouts."""
        current_time = time.time()
        
        with self.paradox_lock:
            for paradox in self.detected_paradoxes.values():
                if (paradox.resolution_status == "resolving" and
                    current_time - paradox.detection_time > self.resolution_timeout):
                    
                    paradox.resolution_status = "timeout"
                    
                    self.emit_event("paradox_resolution_timeout", {
                        'paradox_id': paradox.paradox_id,
                        'timeout_duration': self.resolution_timeout
                    })
                    
                    self.logger.warning("Paradox resolution timeout: %s", paradox.paradox_id)
    
    def _update_success_rate(self):
        """Update resolution success rate."""
        if self.total_paradoxes_detected > 0:
            self.resolution_success_rate = (
                self.total_paradoxes_resolved / self.total_paradoxes_detected
            )
    
    def get_paradox_statistics(self) -> Dict[str, Any]:
        """Get comprehensive paradox statistics."""
        with self.paradox_lock:
            active_paradoxes = len(self.detected_paradoxes)
            
            paradox_types = defaultdict(int)
            severity_distribution = defaultdict(int)
            
            for paradox in self.detected_paradoxes.values():
                paradox_types[paradox.paradox_type.value] += 1
                severity_distribution[paradox.severity.value] += 1
            
            return {
                'total_paradoxes_detected': self.total_paradoxes_detected,
                'total_paradoxes_resolved': self.total_paradoxes_resolved,
                'active_paradoxes': active_paradoxes,
                'critical_paradox_count': self.critical_paradox_count,
                'resolution_success_rate': self.resolution_success_rate,
                'paradox_types': dict(paradox_types),
                'severity_distribution': dict(severity_distribution),
                'detection_sensitivity': self.detection_sensitivity,
                'auto_resolution_threshold': self.auto_resolution_threshold,
                'engine_status': self.get_property('status', 'unknown')
            }
    
    def on_health_check(self) -> Optional[Dict[str, Any]]:
        """Health check for paradox resolution engine."""
        with self.paradox_lock:
            return {
                'active_paradoxes': len(self.detected_paradoxes),
                'resolved_paradoxes': self.total_paradoxes_resolved,
                'critical_paradoxes': self.critical_paradox_count,
                'success_rate': self.resolution_success_rate,
                'engine_active': self.is_running
            }