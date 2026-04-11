"""
Alternate Reality Detector
=========================

Detects and analyzes alternate reality states across parallel universes,
identifying divergence points, reality signatures, and dimensional variations.
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
import hashlib
import json

from ..core.base_multiverse import MultiverseComponent
from ..core.config_manager import get_global_config


class RealityClassification(Enum):
    """Classifications of reality types."""
    BASELINE = "baseline"
    ALTERNATE = "alternate"
    DIVERGENT = "divergent"
    PARALLEL = "parallel"
    MIRROR = "mirror"
    QUANTUM_VARIANT = "quantum_variant"
    TEMPORAL_BRANCH = "temporal_branch"
    ARTIFICIAL = "artificial"
    UNSTABLE = "unstable"
    ANOMALOUS = "anomalous"


class DivergenceType(Enum):
    """Types of reality divergence."""
    QUANTUM_MEASUREMENT = "quantum_measurement"
    DECISION_POINT = "decision_point"
    CONSCIOUSNESS_CHOICE = "consciousness_choice"
    RANDOM_EVENT = "random_event"
    CAUSAL_INTERVENTION = "causal_intervention"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    DIMENSIONAL_SHIFT = "dimensional_shift"
    PHYSICS_VARIATION = "physics_variation"


@dataclass
class RealitySignature:
    """Signature representing a unique reality state."""
    signature_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    universe_id: str = ""
    timestamp: float = field(default_factory=time.time)
    
    # Physical properties
    physics_constants: Dict[str, float] = field(default_factory=dict)
    natural_laws: Dict[str, Any] = field(default_factory=dict)
    quantum_state_hash: str = ""
    
    # Observational properties
    major_events: List[str] = field(default_factory=list)
    entity_states: Dict[str, Any] = field(default_factory=dict)
    environmental_conditions: Dict[str, float] = field(default_factory=dict)
    
    # Analysis properties
    reality_classification: RealityClassification = RealityClassification.BASELINE
    divergence_type: Optional[DivergenceType] = None
    divergence_timestamp: Optional[float] = None
    parent_signature_id: Optional[str] = None
    similarity_score: float = 1.0
    stability_index: float = 1.0
    
    # Metadata
    detection_confidence: float = 1.0
    analysis_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_signature_hash(self) -> str:
        """Calculate unique hash for this reality signature."""
        signature_data = {
            'physics_constants': self.physics_constants,
            'natural_laws': self.natural_laws,
            'major_events': sorted(self.major_events),
            'entity_states': self.entity_states,
            'environmental_conditions': self.environmental_conditions
        }
        
        signature_str = json.dumps(signature_data, sort_keys=True)
        return hashlib.sha256(signature_str.encode()).hexdigest()
    
    def compare_with(self, other: 'RealitySignature') -> float:
        """Compare this signature with another and return similarity score."""
        similarity_components = []
        
        # Physics constants similarity
        physics_sim = self._compare_physics_constants(other)
        similarity_components.append(physics_sim * 0.3)
        
        # Natural laws similarity
        laws_sim = self._compare_natural_laws(other)
        similarity_components.append(laws_sim * 0.2)
        
        # Major events similarity
        events_sim = self._compare_major_events(other)
        similarity_components.append(events_sim * 0.3)
        
        # Entity states similarity
        entities_sim = self._compare_entity_states(other)
        similarity_components.append(entities_sim * 0.2)
        
        return sum(similarity_components)
    
    def _compare_physics_constants(self, other: 'RealitySignature') -> float:
        """Compare physics constants between signatures."""
        if not self.physics_constants or not other.physics_constants:
            return 0.5  # Neutral score if data missing
        
        common_constants = set(self.physics_constants.keys()) & set(other.physics_constants.keys())
        if not common_constants:
            return 0.0
        
        differences = []
        for constant in common_constants:
            val1 = self.physics_constants[constant]
            val2 = other.physics_constants[constant]
            
            if val1 != 0:
                relative_diff = abs(val1 - val2) / abs(val1)
                differences.append(min(1.0, relative_diff))
        
        avg_difference = sum(differences) / len(differences)
        return 1.0 - avg_difference
    
    def _compare_natural_laws(self, other: 'RealitySignature') -> float:
        """Compare natural laws between signatures."""
        if not self.natural_laws or not other.natural_laws:
            return 0.5
        
        common_laws = set(self.natural_laws.keys()) & set(other.natural_laws.keys())
        if not common_laws:
            return 0.0
        
        matches = 0
        for law in common_laws:
            if self.natural_laws[law] == other.natural_laws[law]:
                matches += 1
        
        return matches / len(common_laws)
    
    def _compare_major_events(self, other: 'RealitySignature') -> float:
        """Compare major events between signatures."""
        events1 = set(self.major_events)
        events2 = set(other.major_events)
        
        if not events1 and not events2:
            return 1.0
        
        intersection = events1 & events2
        union = events1 | events2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _compare_entity_states(self, other: 'RealitySignature') -> float:
        """Compare entity states between signatures."""
        if not self.entity_states or not other.entity_states:
            return 0.5
        
        common_entities = set(self.entity_states.keys()) & set(other.entity_states.keys())
        if not common_entities:
            return 0.0
        
        matches = 0
        for entity in common_entities:
            if self.entity_states[entity] == other.entity_states[entity]:
                matches += 1
        
        return matches / len(common_entities)


class AlternateRealityDetector(MultiverseComponent):
    """
    Detector for alternate reality states across the multiverse.
    
    Analyzes universe states, identifies reality variations, tracks divergence
    points, and maintains a comprehensive database of reality signatures.
    """
    
    def __init__(self, multiverse_manager=None):
        """Initialize the alternate reality detector."""
        super().__init__("AlternateRealityDetector")
        
        self.multiverse_manager = multiverse_manager
        self.config = get_global_config()
        
        # Reality signature storage
        self.reality_signatures: Dict[str, RealitySignature] = {}
        self.universe_signatures: Dict[str, List[str]] = defaultdict(list)
        self.signature_lock = threading.RLock()
        
        # Baseline reality tracking
        self.baseline_signature_id: Optional[str] = None
        self.baseline_universe_id: Optional[str] = None
        
        # Detection parameters
        self.similarity_threshold = 0.8
        self.divergence_threshold = 0.3
        self.scan_interval = 30.0  # seconds
        self.max_signatures_per_universe = 100
        
        # Analysis tracking
        self.divergence_points: List[Tuple[float, str, DivergenceType]] = []
        self.reality_clusters: Dict[str, List[str]] = {}
        self.anomaly_count = 0
        
        # Statistics
        self.total_signatures_generated = 0
        self.alternate_realities_detected = 0
        self.divergence_events_detected = 0
        
        self.logger.info("AlternateRealityDetector initialized")
    
    def on_start(self):
        """Start alternate reality detection."""
        self.logger.info("Alternate reality detection started")
        self.update_property("status", "detecting")
        
        # Establish baseline if not set
        if not self.baseline_signature_id:
            self._establish_baseline_reality()
        
        # Start scanning thread
        self._start_scanning_thread()
    
    def on_stop(self):
        """Stop alternate reality detection."""
        self.logger.info("Alternate reality detection stopped")
        self.update_property("status", "stopped")
    
    def _start_scanning_thread(self):
        """Start reality scanning thread."""
        def scan_realities():
            while self.is_running:
                try:
                    self._scan_all_universes()
                    self._analyze_reality_patterns()
                    time.sleep(self.scan_interval)
                except Exception as e:
                    self.logger.error("Error in reality scanning: %s", e)
                    time.sleep(5.0)
        
        scan_thread = threading.Thread(
            target=scan_realities,
            daemon=True,
            name="RealityScanner"
        )
        scan_thread.start()
    
    def _establish_baseline_reality(self):
        """Establish baseline reality signature from primary universe."""
        if not self.multiverse_manager:
            self.logger.warning("No multiverse manager available for baseline")
            return
        
        # Find primary universe
        universes = self.multiverse_manager.list_universes()
        primary_universe_id = None
        
        for universe_id, universe_info in universes.items():
            if universe_info.get('is_primary', False):
                primary_universe_id = universe_id
                break
        
        if primary_universe_id:
            signature = self.generate_reality_signature(primary_universe_id)
            if signature:
                signature.reality_classification = RealityClassification.BASELINE
                self.baseline_signature_id = signature.signature_id
                self.baseline_universe_id = primary_universe_id
                
                self.logger.info("Baseline reality established: %s", 
                               self.baseline_signature_id)
    
    def generate_reality_signature(self, universe_id: str) -> Optional[RealitySignature]:
        """
        Generate a reality signature for a universe.
        
        Args:
            universe_id: Universe to analyze
            
        Returns:
            RealitySignature if successful, None otherwise
        """
        try:
            self.track_operation("generate_reality_signature")
            
            if not self.multiverse_manager:
                self.logger.error("No multiverse manager available")
                return None
            
            universe = self.multiverse_manager.get_universe(universe_id)
            if not universe:
                self.logger.error("Universe not found: %s", universe_id)
                return None
            
            # Create signature
            signature = RealitySignature(
                universe_id=universe_id,
                physics_constants=universe.properties.get('physics_constants', {}),
                natural_laws=universe.properties.get('natural_laws', {}),
                quantum_state_hash=self._calculate_quantum_hash(universe)
            )
            
            # Extract major events (simplified)
            signature.major_events = self._extract_major_events(universe)
            
            # Extract entity states (simplified)
            signature.entity_states = self._extract_entity_states(universe)
            
            # Extract environmental conditions
            signature.environmental_conditions = self._extract_environmental_conditions(universe)
            
            # Calculate signature hash
            signature.quantum_state_hash = signature.calculate_signature_hash()
            
            # Classify reality
            self._classify_reality(signature)
            
            # Store signature
            with self.signature_lock:
                self.reality_signatures[signature.signature_id] = signature
                self.universe_signatures[universe_id].append(signature.signature_id)
                self.total_signatures_generated += 1
                
                # Limit signatures per universe
                if len(self.universe_signatures[universe_id]) > self.max_signatures_per_universe:
                    old_signature_id = self.universe_signatures[universe_id].pop(0)
                    if old_signature_id in self.reality_signatures:
                        del self.reality_signatures[old_signature_id]
            
            self.emit_event("reality_signature_generated", {
                'signature_id': signature.signature_id,
                'universe_id': universe_id,
                'classification': signature.reality_classification.value
            })
            
            self.logger.debug("Reality signature generated: %s for universe %s",
                            signature.signature_id, universe_id)
            
            return signature
            
        except Exception as e:
            self.logger.error("Error generating reality signature: %s", e)
            self.track_error(e, "generate_reality_signature")
            return None
    
    def _calculate_quantum_hash(self, universe) -> str:
        """Calculate hash representing quantum state of universe."""
        quantum_data = {
            'quantum_state_id': universe.quantum_state.state_id,
            'purity': universe.quantum_state.calculate_purity(),
            'entropy': universe.quantum_state.calculate_von_neumann_entropy(),
            'energy': universe.quantum_state.calculate_total_energy()
        }
        
        quantum_str = json.dumps(quantum_data, sort_keys=True)
        return hashlib.md5(quantum_str.encode()).hexdigest()
    
    def _extract_major_events(self, universe) -> List[str]:
        """Extract major events from universe (simplified implementation)."""
        # In a real implementation, this would analyze timeline events,
        # significant quantum measurements, consciousness decisions, etc.
        events = []
        
        # Add universe creation event
        events.append(f"universe_created_{universe.timestamp_created}")
        
        # Add branching events
        for child_id in universe.child_universes:
            events.append(f"universe_branched_{child_id}")
        
        # Add state transitions
        events.append(f"universe_state_{universe.state.value}")
        
        return events
    
    def _extract_entity_states(self, universe) -> Dict[str, Any]:
        """Extract entity states from universe (simplified implementation)."""
        # In a real implementation, this would track conscious entities,
        # their decisions, locations, states, etc.
        return {
            'universe_state': universe.state.value,
            'universe_probability': universe.probability,
            'universe_entropy': universe.entropy,
            'child_count': len(universe.child_universes),
            'parent_exists': universe.parent_universe is not None
        }
    
    def _extract_environmental_conditions(self, universe) -> Dict[str, float]:
        """Extract environmental conditions from universe."""
        conditions = {}
        
        # Physical conditions
        conditions['temperature'] = universe.properties.get('temperature', 273.15)
        conditions['pressure'] = universe.properties.get('pressure', 101325.0)
        conditions['energy_density'] = universe.properties.get('energy_density', 1.0)
        
        # Quantum conditions
        conditions['quantum_coherence'] = universe.properties.get('quantum_coherence', 0.5)
        conditions['dimensional_stability'] = universe.properties.get('dimensional_stability', 1.0)
        conditions['temporal_flow_rate'] = universe.properties.get('temporal_flow_rate', 1.0)
        
        return conditions
    
    def _classify_reality(self, signature: RealitySignature):
        """Classify reality type based on signature analysis."""
        if not self.baseline_signature_id:
            signature.reality_classification = RealityClassification.BASELINE
            return
        
        baseline = self.reality_signatures.get(self.baseline_signature_id)
        if not baseline:
            signature.reality_classification = RealityClassification.BASELINE
            return
        
        # Calculate similarity to baseline
        similarity = signature.compare_with(baseline)
        signature.similarity_score = similarity
        
        # Classify based on similarity
        if similarity > 0.95:
            signature.reality_classification = RealityClassification.BASELINE
        elif similarity > 0.8:
            signature.reality_classification = RealityClassification.PARALLEL
        elif similarity > 0.6:
            signature.reality_classification = RealityClassification.ALTERNATE
        elif similarity > 0.4:
            signature.reality_classification = RealityClassification.DIVERGENT
        elif similarity > 0.2:
            signature.reality_classification = RealityClassification.QUANTUM_VARIANT
        else:
            signature.reality_classification = RealityClassification.ANOMALOUS
            self.anomaly_count += 1
        
        # Detect divergence type
        if similarity < 0.8:
            signature.divergence_type = self._detect_divergence_type(signature, baseline)
            signature.divergence_timestamp = signature.timestamp
            self.divergence_events_detected += 1
        
        # Count alternate realities
        if signature.reality_classification != RealityClassification.BASELINE:
            self.alternate_realities_detected += 1
    
    def _detect_divergence_type(self, signature: RealitySignature, 
                               baseline: RealitySignature) -> DivergenceType:
        """Detect type of divergence from baseline."""
        # Physics constants changed significantly
        physics_sim = signature._compare_physics_constants(baseline)
        if physics_sim < 0.5:
            return DivergenceType.PHYSICS_VARIATION
        
        # Natural laws different
        laws_sim = signature._compare_natural_laws(baseline)
        if laws_sim < 0.5:
            return DivergenceType.DIMENSIONAL_SHIFT
        
        # Major events different
        events_sim = signature._compare_major_events(baseline)
        if events_sim < 0.5:
            return DivergenceType.DECISION_POINT
        
        # Entity states different
        entities_sim = signature._compare_entity_states(baseline)
        if entities_sim < 0.5:
            return DivergenceType.CONSCIOUSNESS_CHOICE
        
        # Default to quantum measurement if unclear
        return DivergenceType.QUANTUM_MEASUREMENT
    
    def _scan_all_universes(self):
        """Scan all active universes for reality signatures."""
        if not self.multiverse_manager:
            return
        
        universes = self.multiverse_manager.list_universes()
        
        for universe_id in universes.keys():
            try:
                signature = self.generate_reality_signature(universe_id)
                if signature:
                    self._detect_reality_changes(signature)
            except Exception as e:
                self.logger.error("Error scanning universe %s: %s", universe_id, e)
    
    def _detect_reality_changes(self, new_signature: RealitySignature):
        """Detect changes in reality for a universe."""
        universe_id = new_signature.universe_id
        
        with self.signature_lock:
            previous_signatures = self.universe_signatures.get(universe_id, [])
            
            if len(previous_signatures) > 1:
                # Compare with most recent signature
                prev_signature_id = previous_signatures[-2]
                prev_signature = self.reality_signatures.get(prev_signature_id)
                
                if prev_signature:
                    similarity = new_signature.compare_with(prev_signature)
                    
                    if similarity < self.similarity_threshold:
                        self._report_reality_change(prev_signature, new_signature, similarity)
    
    def _report_reality_change(self, old_signature: RealitySignature,
                              new_signature: RealitySignature, similarity: float):
        """Report detected reality change."""
        change_magnitude = 1.0 - similarity
        
        self.emit_event("reality_change_detected", {
            'universe_id': new_signature.universe_id,
            'old_signature_id': old_signature.signature_id,
            'new_signature_id': new_signature.signature_id,
            'similarity': similarity,
            'change_magnitude': change_magnitude,
            'old_classification': old_signature.reality_classification.value,
            'new_classification': new_signature.reality_classification.value
        })
        
        self.logger.info("Reality change detected in universe %s: %.2f similarity",
                        new_signature.universe_id, similarity)
    
    def _analyze_reality_patterns(self):
        """Analyze patterns in reality signatures."""
        with self.signature_lock:
            # Group similar realities
            self._cluster_similar_realities()
            
            # Detect convergence patterns
            self._detect_convergence_patterns()
            
            # Analyze divergence trends
            self._analyze_divergence_trends()
    
    def _cluster_similar_realities(self):
        """Cluster similar reality signatures."""
        signatures = list(self.reality_signatures.values())
        clusters = {}
        
        for signature in signatures:
            # Find most similar cluster
            best_cluster = None
            best_similarity = 0.0
            
            for cluster_id, cluster_signatures in clusters.items():
                for cluster_sig_id in cluster_signatures:
                    cluster_sig = self.reality_signatures.get(cluster_sig_id)
                    if cluster_sig:
                        similarity = signature.compare_with(cluster_sig)
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_cluster = cluster_id
            
            # Add to cluster or create new cluster
            if best_cluster and best_similarity > self.similarity_threshold:
                clusters[best_cluster].append(signature.signature_id)
            else:
                # Create new cluster
                new_cluster_id = f"cluster_{len(clusters)}"
                clusters[new_cluster_id] = [signature.signature_id]
        
        self.reality_clusters = clusters
    
    def _detect_convergence_patterns(self):
        """Detect patterns of reality convergence."""
        # Look for universes becoming more similar over time
        convergence_pairs = []
        
        with self.signature_lock:
            for universe_id, signature_ids in self.universe_signatures.items():
                if len(signature_ids) < 3:
                    continue
                
                # Compare recent signatures with others
                recent_sig_id = signature_ids[-1]
                recent_sig = self.reality_signatures.get(recent_sig_id)
                
                if recent_sig:
                    for other_universe_id, other_sig_ids in self.universe_signatures.items():
                        if universe_id == other_universe_id or not other_sig_ids:
                            continue
                        
                        other_recent_id = other_sig_ids[-1]
                        other_recent = self.reality_signatures.get(other_recent_id)
                        
                        if other_recent:
                            similarity = recent_sig.compare_with(other_recent)
                            if similarity > 0.9:  # High similarity indicates convergence
                                convergence_pairs.append((universe_id, other_universe_id, similarity))
        
        if convergence_pairs:
            self.emit_event("reality_convergence_detected", {
                'convergence_pairs': convergence_pairs,
                'detection_time': time.time()
            })
    
    def _analyze_divergence_trends(self):
        """Analyze trends in reality divergence."""
        divergence_rates = {}
        
        with self.signature_lock:
            for universe_id, signature_ids in self.universe_signatures.items():
                if len(signature_ids) < 2:
                    continue
                
                # Calculate divergence rate over time
                signatures = [self.reality_signatures[sid] for sid in signature_ids[-5:] 
                             if sid in self.reality_signatures]
                
                if len(signatures) >= 2:
                    divergence_rate = self._calculate_divergence_rate(signatures)
                    divergence_rates[universe_id] = divergence_rate
        
        # Report accelerating divergence
        for universe_id, rate in divergence_rates.items():
            if rate > 0.1:  # Threshold for concerning divergence rate
                self.emit_event("accelerating_divergence_detected", {
                    'universe_id': universe_id,
                    'divergence_rate': rate,
                    'detection_time': time.time()
                })
    
    def _calculate_divergence_rate(self, signatures: List[RealitySignature]) -> float:
        """Calculate rate of divergence from baseline over time."""
        if not self.baseline_signature_id or len(signatures) < 2:
            return 0.0
        
        baseline = self.reality_signatures.get(self.baseline_signature_id)
        if not baseline:
            return 0.0
        
        # Calculate similarities over time
        similarities = []
        times = []
        
        for signature in signatures:
            similarity = signature.compare_with(baseline)
            similarities.append(similarity)
            times.append(signature.timestamp)
        
        # Calculate rate of change (negative = diverging)
        if len(similarities) >= 2:
            time_diff = times[-1] - times[0]
            similarity_diff = similarities[-1] - similarities[0]
            
            if time_diff > 0:
                return -similarity_diff / time_diff  # Negative rate = diverging
        
        return 0.0
    
    def get_reality_analysis(self, universe_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive reality analysis for a universe."""
        with self.signature_lock:
            signature_ids = self.universe_signatures.get(universe_id, [])
            if not signature_ids:
                return None
            
            latest_signature_id = signature_ids[-1]
            latest_signature = self.reality_signatures.get(latest_signature_id)
            
            if not latest_signature:
                return None
            
            return {
                'universe_id': universe_id,
                'latest_signature_id': latest_signature_id,
                'reality_classification': latest_signature.reality_classification.value,
                'similarity_to_baseline': latest_signature.similarity_score,
                'stability_index': latest_signature.stability_index,
                'divergence_type': latest_signature.divergence_type.value if latest_signature.divergence_type else None,
                'signature_count': len(signature_ids),
                'analysis_timestamp': latest_signature.timestamp,
                'detection_confidence': latest_signature.detection_confidence
            }
    
    def find_similar_realities(self, signature_id: str, 
                              similarity_threshold: float = 0.8) -> List[Tuple[str, float]]:
        """Find realities similar to a given signature."""
        target_signature = self.reality_signatures.get(signature_id)
        if not target_signature:
            return []
        
        similar_realities = []
        
        with self.signature_lock:
            for other_id, other_signature in self.reality_signatures.items():
                if other_id == signature_id:
                    continue
                
                similarity = target_signature.compare_with(other_signature)
                if similarity >= similarity_threshold:
                    similar_realities.append((other_id, similarity))
        
        # Sort by similarity (highest first)
        similar_realities.sort(key=lambda x: x[1], reverse=True)
        
        return similar_realities
    
    def get_detector_statistics(self) -> Dict[str, Any]:
        """Get comprehensive detector statistics."""
        with self.signature_lock:
            classification_counts = defaultdict(int)
            
            for signature in self.reality_signatures.values():
                classification_counts[signature.reality_classification.value] += 1
            
            return {
                'total_signatures': self.total_signatures_generated,
                'active_signatures': len(self.reality_signatures),
                'alternate_realities_detected': self.alternate_realities_detected,
                'divergence_events': self.divergence_events_detected,
                'anomaly_count': self.anomaly_count,
                'reality_classifications': dict(classification_counts),
                'reality_clusters': len(self.reality_clusters),
                'baseline_established': self.baseline_signature_id is not None,
                'detector_status': self.get_property('status', 'unknown')
            }
    
    def on_health_check(self) -> Optional[Dict[str, Any]]:
        """Health check for alternate reality detector."""
        return {
            'active_signatures': len(self.reality_signatures),
            'universes_tracked': len(self.universe_signatures),
            'alternate_realities': self.alternate_realities_detected,
            'detector_active': self.is_running,
            'baseline_established': self.baseline_signature_id is not None
        }