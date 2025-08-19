"""
Quantum Branching Engine
=======================

Simulates quantum branching events that create parallel universes based on
quantum measurement, decoherence, and many-worlds interpretation.
"""

import numpy as np
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import random
from concurrent.futures import ThreadPoolExecutor
import math

from ..core.base_multiverse import MultiverseComponent
from ..core.quantum_state import QuantumState, QuantumStateType
from ..core.config_manager import get_global_config


class BranchingTrigger(Enum):
    """Types of events that can trigger quantum branching."""
    QUANTUM_MEASUREMENT = "quantum_measurement"
    DECOHERENCE_EVENT = "decoherence_event"
    ENTANGLEMENT_COLLAPSE = "entanglement_collapse"
    CONSCIOUSNESS_OBSERVATION = "consciousness_observation"
    CRITICAL_DECISION_POINT = "critical_decision_point"
    UNCERTAINTY_RESOLUTION = "uncertainty_resolution"
    WAVE_FUNCTION_COLLAPSE = "wave_function_collapse"
    SPONTANEOUS_SYMMETRY_BREAKING = "spontaneous_symmetry_breaking"


@dataclass
class BranchingEvent:
    """Represents a quantum branching event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trigger: BranchingTrigger = BranchingTrigger.QUANTUM_MEASUREMENT
    source_universe_id: str = ""
    branch_universe_ids: List[str] = field(default_factory=list)
    probability_amplitudes: List[complex] = field(default_factory=list)
    branching_probability: float = 0.0
    quantum_coherence: float = 1.0
    decoherence_rate: float = 0.001
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_branch_probabilities(self) -> List[float]:
        """Calculate normalized probabilities for each branch."""
        if not self.probability_amplitudes:
            return []
        
        probabilities = [abs(amp)**2 for amp in self.probability_amplitudes]
        total_prob = sum(probabilities)
        
        if total_prob > 0:
            return [p / total_prob for p in probabilities]
        else:
            return [1.0 / len(probabilities)] * len(probabilities)


class QuantumBranchingEngine(MultiverseComponent):
    """
    Engine for simulating quantum branching events that create parallel universes.
    
    Based on the many-worlds interpretation of quantum mechanics, this engine
    simulates how quantum measurements and decoherence events create universe
    branches with different outcomes.
    """
    
    def __init__(self, multiverse_manager=None):
        """Initialize the quantum branching engine."""
        super().__init__("QuantumBranchingEngine")
        
        self.multiverse_manager = multiverse_manager
        self.config = get_global_config()
        
        # Branching state
        self.active_branches: Dict[str, BranchingEvent] = {}
        self.branching_history: List[BranchingEvent] = []
        self.branching_lock = threading.RLock()
        
        # Quantum simulation parameters
        self.base_branching_probability = 0.1
        self.consciousness_amplification_factor = 2.0
        self.decoherence_threshold = 0.5
        self.max_simultaneous_branches = 50
        
        # Monitoring and statistics
        self.total_branches_created = 0
        self.average_branching_rate = 0.0
        self.last_branching_time = time.time()
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(
            max_workers=self.config.performance.max_worker_threads,
            thread_name_prefix="QuantumBranching"
        )
        
        # Event handlers
        self.branching_event_handlers: List[Callable[[BranchingEvent], None]] = []
        
        self.logger.info("QuantumBranchingEngine initialized")
    
    def on_start(self):
        """Start the quantum branching engine."""
        self.logger.info("Quantum branching engine started")
        self.update_property("status", "active")
    
    def on_stop(self):
        """Stop the quantum branching engine."""
        self.executor.shutdown(wait=True)
        self.logger.info("Quantum branching engine stopped")
        self.update_property("status", "inactive")
    
    def add_branching_event_handler(self, handler: Callable[[BranchingEvent], None]):
        """Add a handler for branching events."""
        with self.branching_lock:
            self.branching_event_handlers.append(handler)
            self.logger.debug("Added branching event handler: %s", handler.__name__)
    
    def simulate_quantum_measurement_branching(self, 
                                             source_universe_id: str,
                                             quantum_state: QuantumState,
                                             observable: np.ndarray,
                                             consciousness_factor: float = 1.0) -> Optional[BranchingEvent]:
        """
        Simulate universe branching due to quantum measurement.
        
        Args:
            source_universe_id: ID of the universe where measurement occurs
            quantum_state: Quantum state being measured
            observable: Observable operator
            consciousness_factor: Factor representing consciousness involvement
            
        Returns:
            BranchingEvent if branching occurs, None otherwise
        """
        try:
            self.track_operation("quantum_measurement_branching")
            
            # Calculate eigenvalues and eigenvectors
            eigenvalues, eigenvectors = np.linalg.eigh(observable)
            
            # Calculate probability amplitudes
            rho = quantum_state.density_matrix
            probability_amplitudes = []
            
            for i, eigenval in enumerate(eigenvalues):
                eigenvec = eigenvectors[:, i]
                projector = np.outer(eigenvec, eigenvec.conj())
                amplitude = np.sqrt(np.real(np.trace(rho @ projector)))
                probability_amplitudes.append(complex(amplitude))
            
            # Calculate branching probability
            branching_prob = self._calculate_branching_probability(
                quantum_state, consciousness_factor
            )
            
            # Determine if branching occurs
            if random.random() < branching_prob:
                return self._create_measurement_branches(
                    source_universe_id,
                    quantum_state,
                    eigenvalues,
                    eigenvectors,
                    probability_amplitudes,
                    consciousness_factor
                )
            
            return None
            
        except Exception as e:
            self.logger.error("Error in quantum measurement branching: %s", e)
            self.track_error(e, "quantum_measurement_branching")
            return None
    
    def simulate_decoherence_branching(self, 
                                     source_universe_id: str,
                                     quantum_state: QuantumState,
                                     environment_interaction_strength: float = 1.0) -> Optional[BranchingEvent]:
        """
        Simulate universe branching due to quantum decoherence.
        
        Args:
            source_universe_id: ID of source universe
            quantum_state: Quantum state undergoing decoherence
            environment_interaction_strength: Strength of environmental interaction
            
        Returns:
            BranchingEvent if branching occurs, None otherwise
        """
        try:
            self.track_operation("decoherence_branching")
            
            # Calculate decoherence rate
            decoherence_rate = (
                quantum_state.decoherence_rate * 
                environment_interaction_strength *
                self.config.quantum.decoherence_rate
            )
            
            # Check if decoherence is strong enough to cause branching
            if decoherence_rate > self.decoherence_threshold:
                return self._create_decoherence_branches(
                    source_universe_id,
                    quantum_state,
                    decoherence_rate,
                    environment_interaction_strength
                )
            
            return None
            
        except Exception as e:
            self.logger.error("Error in decoherence branching: %s", e)
            self.track_error(e, "decoherence_branching")
            return None
    
    def simulate_consciousness_branching(self, 
                                       source_universe_id: str,
                                       decision_complexity: float,
                                       consciousness_level: float = 1.0) -> Optional[BranchingEvent]:
        """
        Simulate universe branching due to consciousness observation/decision.
        
        Args:
            source_universe_id: ID of source universe
            decision_complexity: Complexity of the decision/observation
            consciousness_level: Level of consciousness involved
            
        Returns:
            BranchingEvent if branching occurs, None otherwise
        """
        try:
            self.track_operation("consciousness_branching")
            
            # Calculate consciousness-induced branching probability
            branching_prob = (
                decision_complexity * 
                consciousness_level * 
                self.consciousness_amplification_factor *
                self.base_branching_probability
            )
            
            if random.random() < branching_prob:
                return self._create_consciousness_branches(
                    source_universe_id,
                    decision_complexity,
                    consciousness_level
                )
            
            return None
            
        except Exception as e:
            self.logger.error("Error in consciousness branching: %s", e)
            self.track_error(e, "consciousness_branching")
            return None
    
    def _calculate_branching_probability(self, 
                                       quantum_state: QuantumState,
                                       consciousness_factor: float) -> float:
        """Calculate probability of universe branching."""
        # Base probability from quantum coherence
        base_prob = (1.0 - quantum_state.calculate_purity()) * self.base_branching_probability
        
        # Amplify with consciousness factor
        consciousness_amplified = base_prob * (1.0 + consciousness_factor * 
                                              self.consciousness_amplification_factor)
        
        # Consider quantum entanglement
        entanglement_factor = 1.0 + 0.5 * len(quantum_state.entanglement_partners)
        
        # Final probability
        final_prob = consciousness_amplified * entanglement_factor
        
        return min(1.0, max(0.0, final_prob))
    
    def _create_measurement_branches(self, 
                                   source_universe_id: str,
                                   quantum_state: QuantumState,
                                   eigenvalues: np.ndarray,
                                   eigenvectors: np.ndarray,
                                   probability_amplitudes: List[complex],
                                   consciousness_factor: float) -> BranchingEvent:
        """Create universe branches for quantum measurement."""
        with self.branching_lock:
            # Create branching event
            branching_event = BranchingEvent(
                trigger=BranchingTrigger.QUANTUM_MEASUREMENT,
                source_universe_id=source_universe_id,
                probability_amplitudes=probability_amplitudes.copy(),
                branching_probability=self._calculate_branching_probability(
                    quantum_state, consciousness_factor
                ),
                quantum_coherence=quantum_state.calculate_purity(),
                metadata={
                    'eigenvalues': eigenvalues.tolist(),
                    'consciousness_factor': consciousness_factor,
                    'quantum_state_id': quantum_state.state_id,
                    'measurement_type': 'observable_measurement'
                }
            )
            
            # Create branch universes through multiverse manager
            if self.multiverse_manager:
                for i, (eigenval, amplitude) in enumerate(zip(eigenvalues, probability_amplitudes)):
                    if abs(amplitude)**2 > 1e-10:  # Only create branches with non-negligible probability
                        branch_id = self.multiverse_manager.branch_universe(
                            source_universe_id,
                            quantum_deviation=abs(amplitude)**2
                        )
                        if branch_id:
                            branching_event.branch_universe_ids.append(branch_id)
            
            # Store and process event
            self._process_branching_event(branching_event)
            
            return branching_event
    
    def _create_decoherence_branches(self, 
                                   source_universe_id: str,
                                   quantum_state: QuantumState,
                                   decoherence_rate: float,
                                   environment_strength: float) -> BranchingEvent:
        """Create universe branches for decoherence events."""
        with self.branching_lock:
            # Generate random basis states for decoherence
            num_branches = min(4, quantum_state.dimension)  # Limit decoherence branches
            probability_amplitudes = []
            
            for i in range(num_branches):
                # Random amplitudes with decreasing probability
                amplitude = complex(
                    random.gauss(0, 1/math.sqrt(i+1)),
                    random.gauss(0, 1/math.sqrt(i+1))
                )
                probability_amplitudes.append(amplitude)
            
            # Normalize amplitudes
            total_prob = sum(abs(amp)**2 for amp in probability_amplitudes)
            if total_prob > 0:
                probability_amplitudes = [amp / math.sqrt(total_prob) 
                                        for amp in probability_amplitudes]
            
            # Create branching event
            branching_event = BranchingEvent(
                trigger=BranchingTrigger.DECOHERENCE_EVENT,
                source_universe_id=source_universe_id,
                probability_amplitudes=probability_amplitudes,
                branching_probability=min(decoherence_rate, 1.0),
                quantum_coherence=1.0 - decoherence_rate,
                decoherence_rate=decoherence_rate,
                metadata={
                    'environment_strength': environment_strength,
                    'quantum_state_id': quantum_state.state_id,
                    'decoherence_type': 'environmental_interaction'
                }
            )
            
            # Create branch universes
            if self.multiverse_manager:
                for i, amplitude in enumerate(probability_amplitudes):
                    if abs(amplitude)**2 > 1e-10:
                        branch_id = self.multiverse_manager.branch_universe(
                            source_universe_id,
                            quantum_deviation=decoherence_rate * abs(amplitude)**2
                        )
                        if branch_id:
                            branching_event.branch_universe_ids.append(branch_id)
            
            self._process_branching_event(branching_event)
            
            return branching_event
    
    def _create_consciousness_branches(self, 
                                     source_universe_id: str,
                                     decision_complexity: float,
                                     consciousness_level: float) -> BranchingEvent:
        """Create universe branches for consciousness-induced events."""
        with self.branching_lock:
            # Number of branches based on decision complexity
            num_branches = max(2, min(8, int(decision_complexity * 4)))
            
            # Generate probability amplitudes for different outcomes
            probability_amplitudes = []
            for i in range(num_branches):
                # Use decision complexity to weight probabilities
                weight = 1.0 / (i + 1)  # Decreasing probability for alternatives
                amplitude = complex(
                    math.sqrt(weight * consciousness_level),
                    0.0  # Real amplitudes for consciousness decisions
                )
                probability_amplitudes.append(amplitude)
            
            # Normalize amplitudes
            total_prob = sum(abs(amp)**2 for amp in probability_amplitudes)
            if total_prob > 0:
                probability_amplitudes = [amp / math.sqrt(total_prob) 
                                        for amp in probability_amplitudes]
            
            # Create branching event
            branching_event = BranchingEvent(
                trigger=BranchingTrigger.CONSCIOUSNESS_OBSERVATION,
                source_universe_id=source_universe_id,
                probability_amplitudes=probability_amplitudes,
                branching_probability=decision_complexity * consciousness_level,
                quantum_coherence=consciousness_level,
                metadata={
                    'decision_complexity': decision_complexity,
                    'consciousness_level': consciousness_level,
                    'branching_type': 'consciousness_decision'
                }
            )
            
            # Create branch universes
            if self.multiverse_manager:
                for i, amplitude in enumerate(probability_amplitudes):
                    if abs(amplitude)**2 > 1e-10:
                        branch_id = self.multiverse_manager.branch_universe(
                            source_universe_id,
                            quantum_deviation=decision_complexity * abs(amplitude)**2
                        )
                        if branch_id:
                            branching_event.branch_universe_ids.append(branch_id)
            
            self._process_branching_event(branching_event)
            
            return branching_event
    
    def _process_branching_event(self, branching_event: BranchingEvent):
        """Process and store a branching event."""
        # Add to active branches
        self.active_branches[branching_event.event_id] = branching_event
        
        # Add to history
        self.branching_history.append(branching_event)
        
        # Update statistics
        self.total_branches_created += len(branching_event.branch_universe_ids)
        current_time = time.time()
        time_delta = current_time - self.last_branching_time
        self.average_branching_rate = (
            0.9 * self.average_branching_rate + 
            0.1 * (1.0 / max(time_delta, 0.001))
        )
        self.last_branching_time = current_time
        
        # Notify event handlers
        for handler in self.branching_event_handlers:
            try:
                self.executor.submit(handler, branching_event)
            except Exception as e:
                self.logger.error("Error in branching event handler: %s", e)
        
        # Emit multiverse event
        self.emit_event("quantum_branching_occurred", {
            'event_id': branching_event.event_id,
            'trigger': branching_event.trigger.value,
            'source_universe': branching_event.source_universe_id,
            'branch_count': len(branching_event.branch_universe_ids),
            'total_probability': sum(abs(amp)**2 for amp in branching_event.probability_amplitudes)
        })
        
        self.logger.info("Quantum branching event processed: %s (%s) -> %d branches",
                        branching_event.event_id,
                        branching_event.trigger.value,
                        len(branching_event.branch_universe_ids))
    
    def get_active_branching_events(self) -> Dict[str, BranchingEvent]:
        """Get all currently active branching events."""
        with self.branching_lock:
            return self.active_branches.copy()
    
    def get_branching_history(self, limit: Optional[int] = None) -> List[BranchingEvent]:
        """Get branching event history."""
        with self.branching_lock:
            history = self.branching_history.copy()
            if limit:
                return history[-limit:]
            return history
    
    def get_branching_statistics(self) -> Dict[str, Any]:
        """Get comprehensive branching statistics."""
        with self.branching_lock:
            trigger_counts = {}
            total_probability = 0.0
            
            for event in self.branching_history:
                trigger = event.trigger.value
                trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
                total_probability += sum(abs(amp)**2 for amp in event.probability_amplitudes)
            
            return {
                'total_branching_events': len(self.branching_history),
                'total_branches_created': self.total_branches_created,
                'active_events': len(self.active_branches),
                'average_branching_rate': self.average_branching_rate,
                'trigger_distribution': trigger_counts,
                'total_probability_processed': total_probability,
                'last_branching_time': self.last_branching_time
            }
    
    def simulate_spontaneous_branching(self, universe_id: str) -> Optional[BranchingEvent]:
        """
        Simulate spontaneous quantum branching due to vacuum fluctuations.
        
        Args:
            universe_id: Universe where spontaneous branching occurs
            
        Returns:
            BranchingEvent if branching occurs, None otherwise
        """
        try:
            # Very low probability for spontaneous branching
            if random.random() < 0.001:  # 0.1% chance
                # Create minimal branching event
                probability_amplitudes = [
                    complex(0.7071, 0),  # Main universe continues
                    complex(0.7071, 0)   # Alternative outcome
                ]
                
                branching_event = BranchingEvent(
                    trigger=BranchingTrigger.SPONTANEOUS_SYMMETRY_BREAKING,
                    source_universe_id=universe_id,
                    probability_amplitudes=probability_amplitudes,
                    branching_probability=0.001,
                    quantum_coherence=0.99,
                    metadata={
                        'branching_type': 'spontaneous_vacuum_fluctuation',
                        'energy_scale': 'planck_scale'
                    }
                )
                
                # Create single branch
                if self.multiverse_manager:
                    branch_id = self.multiverse_manager.branch_universe(
                        universe_id, quantum_deviation=0.001
                    )
                    if branch_id:
                        branching_event.branch_universe_ids.append(branch_id)
                
                self._process_branching_event(branching_event)
                return branching_event
            
            return None
            
        except Exception as e:
            self.logger.error("Error in spontaneous branching: %s", e)
            self.track_error(e, "spontaneous_branching")
            return None
    
    def cleanup_completed_events(self, age_threshold: float = 3600.0):
        """
        Clean up completed branching events older than threshold.
        
        Args:
            age_threshold: Age threshold in seconds (default: 1 hour)
        """
        current_time = time.time()
        
        with self.branching_lock:
            events_to_remove = []
            
            for event_id, event in self.active_branches.items():
                if current_time - event.timestamp > age_threshold:
                    events_to_remove.append(event_id)
            
            for event_id in events_to_remove:
                del self.active_branches[event_id]
            
            if events_to_remove:
                self.logger.info("Cleaned up %d completed branching events", 
                               len(events_to_remove))
    
    def on_health_check(self) -> Optional[Dict[str, Any]]:
        """Health check for quantum branching engine."""
        return {
            'active_events': len(self.active_branches),
            'total_events': len(self.branching_history),
            'branching_rate': self.average_branching_rate,
            'total_branches': self.total_branches_created,
            'last_branching_ago': time.time() - self.last_branching_time
        }