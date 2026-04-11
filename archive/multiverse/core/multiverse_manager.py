"""
Multiverse Manager
=================

Central orchestrator for all multiverse operations, managing parallel universes,
quantum states, and interdimensional coordination.
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import uuid

from .base_multiverse import BaseMultiverseComponent
from .config_manager import MultiverseConfig
from .event_system import MultiverseEventBus, MultiverseEvent
from .metrics_collector import MultiverseMetrics
from .quantum_state import QuantumState
from .reality_anchor import RealityAnchor
from .dimensional_coordinate import DimensionalCoordinate


class UniverseState(Enum):
    """States of parallel universes."""
    STABLE = "stable"
    UNSTABLE = "unstable"
    BRANCHING = "branching"
    CONVERGING = "converging"
    ISOLATED = "isolated"
    COLLAPSED = "collapsed"
    EMERGING = "emerging"


@dataclass
class Universe:
    """Represents a parallel universe."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dimension: DimensionalCoordinate = field(default_factory=DimensionalCoordinate)
    quantum_state: QuantumState = field(default_factory=QuantumState)
    reality_anchor: RealityAnchor = field(default_factory=RealityAnchor)
    state: UniverseState = UniverseState.STABLE
    probability: float = 1.0
    entropy: float = 0.0
    timestamp_created: float = field(default_factory=time.time)
    parent_universe: Optional[str] = None
    child_universes: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize universe with unique properties."""
        if not hasattr(self, '_initialized'):
            self.properties.update({
                'physics_constants': self._generate_physics_constants(),
                'natural_laws': self._generate_natural_laws(),
                'consciousness_level': np.random.uniform(0.1, 1.0),
                'technology_level': np.random.uniform(0.0, 2.0),
                'temporal_flow_rate': np.random.uniform(0.5, 2.0)
            })
            self._initialized = True
    
    def _generate_physics_constants(self) -> Dict[str, float]:
        """Generate unique physics constants for this universe."""
        base_constants = {
            'speed_of_light': 299792458,  # m/s
            'planck_constant': 6.62607015e-34,  # J⋅s
            'gravitational_constant': 6.67430e-11,  # m³⋅kg⁻¹⋅s⁻²
            'fine_structure_constant': 7.2973525693e-3,
            'cosmological_constant': 1.1056e-52  # m⁻²
        }
        
        # Add quantum variations
        variance = np.random.uniform(0.95, 1.05)
        return {k: v * variance for k, v in base_constants.items()}
    
    def _generate_natural_laws(self) -> Dict[str, Any]:
        """Generate natural laws for this universe."""
        return {
            'causality_strength': np.random.uniform(0.8, 1.0),
            'entropy_direction': np.random.choice([1, -1]),  # Forward or backward time
            'quantum_coherence': np.random.uniform(0.1, 1.0),
            'dimensional_stability': np.random.uniform(0.5, 1.0),
            'consciousness_emergence': np.random.uniform(0.0, 1.0)
        }


class MultiverseManager(BaseMultiverseComponent):
    """
    Central manager for multiverse operations.
    
    Manages parallel universes, quantum branching, timeline tracking,
    and interdimensional coordination.
    """
    
    def __init__(self, config: Optional[MultiverseConfig] = None):
        """Initialize the multiverse manager."""
        super().__init__()
        self.config = config or MultiverseConfig()
        self.event_bus = MultiverseEventBus()
        self.metrics = MultiverseMetrics()
        
        # Universe management
        self.universes: Dict[str, Universe] = {}
        self.active_universe_id: Optional[str] = None
        self.universe_lock = threading.RLock()
        
        # System state
        self.is_running = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_worker_threads)
        
        # Initialize primary universe
        self._initialize_primary_universe()
        
        # Start monitoring
        self.start_monitoring()
        
        self.logger.info("MultiverseManager initialized with %d universes", 
                        len(self.universes))
    
    def _initialize_primary_universe(self):
        """Initialize the primary universe (our reality)."""
        primary_universe = Universe(
            id="universe_alpha_primary",
            dimension=DimensionalCoordinate(x=0, y=0, z=0, t=0),
            state=UniverseState.STABLE,
            probability=1.0,
            properties={
                'is_primary': True,
                'kenny_origin': True,
                'reality_baseline': True
            }
        )
        
        with self.universe_lock:
            self.universes[primary_universe.id] = primary_universe
            self.active_universe_id = primary_universe.id
        
        self.event_bus.emit(MultiverseEvent(
            event_type="universe_created",
            data={"universe_id": primary_universe.id, "is_primary": True}
        ))
    
    def start_monitoring(self):
        """Start multiverse monitoring thread."""
        if not self.is_running:
            self.is_running = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="MultiverseMonitor"
            )
            self.monitoring_thread.start()
            self.logger.info("Multiverse monitoring started")
    
    def stop_monitoring(self):
        """Stop multiverse monitoring."""
        self.is_running = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
        self.logger.info("Multiverse monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop for multiverse stability."""
        while self.is_running:
            try:
                self._update_universe_states()
                self._monitor_quantum_fluctuations()
                self._check_temporal_stability()
                self._manage_universe_lifecycle()
                
                # Collect metrics
                self.metrics.record_universe_count(len(self.universes))
                self.metrics.record_active_universe(self.active_universe_id)
                
                time.sleep(self.config.monitoring_interval)
                
            except Exception as e:
                self.logger.error("Error in monitoring loop: %s", e)
                time.sleep(1.0)  # Brief pause before retry
    
    def _update_universe_states(self):
        """Update the state of all universes."""
        with self.universe_lock:
            for universe in self.universes.values():
                self._update_single_universe_state(universe)
    
    def _update_single_universe_state(self, universe: Universe):
        """Update state of a single universe."""
        # Calculate entropy change
        old_entropy = universe.entropy
        universe.entropy += np.random.normal(0, 0.01)
        
        # Update probability based on stability
        stability_factor = universe.properties.get('dimensional_stability', 1.0)
        universe.probability *= (0.999 + 0.001 * stability_factor)
        universe.probability = max(0.001, min(1.0, universe.probability))
        
        # Check for state transitions
        if universe.entropy > self.config.entropy_threshold:
            if universe.state == UniverseState.STABLE:
                universe.state = UniverseState.UNSTABLE
                self.event_bus.emit(MultiverseEvent(
                    event_type="universe_destabilized",
                    data={"universe_id": universe.id, "entropy": universe.entropy}
                ))
        
        # Check for universe branching conditions
        if (universe.probability > self.config.branching_threshold and 
            len(universe.child_universes) < self.config.max_child_universes):
            self._consider_universe_branching(universe)
    
    def _monitor_quantum_fluctuations(self):
        """Monitor quantum fluctuations across all universes."""
        total_quantum_energy = 0.0
        
        with self.universe_lock:
            for universe in self.universes.values():
                quantum_energy = universe.quantum_state.calculate_total_energy()
                total_quantum_energy += quantum_energy
                
                # Check for anomalous quantum activity
                if quantum_energy > self.config.quantum_anomaly_threshold:
                    self.event_bus.emit(MultiverseEvent(
                        event_type="quantum_anomaly_detected",
                        data={
                            "universe_id": universe.id,
                            "quantum_energy": quantum_energy
                        }
                    ))
        
        self.metrics.record_total_quantum_energy(total_quantum_energy)
    
    def _check_temporal_stability(self):
        """Check temporal stability across universes."""
        with self.universe_lock:
            for universe in self.universes.values():
                temporal_flow = universe.properties.get('temporal_flow_rate', 1.0)
                
                if abs(temporal_flow - 1.0) > self.config.temporal_deviation_threshold:
                    self.event_bus.emit(MultiverseEvent(
                        event_type="temporal_anomaly_detected",
                        data={
                            "universe_id": universe.id,
                            "temporal_flow_rate": temporal_flow
                        }
                    ))
    
    def _manage_universe_lifecycle(self):
        """Manage creation and destruction of universes."""
        with self.universe_lock:
            universes_to_remove = []
            
            for universe_id, universe in self.universes.items():
                # Check for universe collapse
                if (universe.probability < self.config.collapse_threshold and
                    not universe.properties.get('is_primary', False)):
                    universes_to_remove.append(universe_id)
            
            # Remove collapsed universes
            for universe_id in universes_to_remove:
                self._collapse_universe(universe_id)
    
    def _consider_universe_branching(self, universe: Universe):
        """Consider whether to branch a universe."""
        branching_probability = (
            universe.probability * 
            universe.properties.get('quantum_coherence', 0.5) *
            self.config.branching_probability_multiplier
        )
        
        if np.random.random() < branching_probability:
            self.branch_universe(universe.id)
    
    def branch_universe(self, parent_universe_id: str, 
                       quantum_deviation: float = 0.1) -> Optional[str]:
        """
        Create a new universe branch from an existing universe.
        
        Args:
            parent_universe_id: ID of parent universe
            quantum_deviation: Amount of quantum deviation for the branch
            
        Returns:
            ID of new universe branch or None if failed
        """
        with self.universe_lock:
            parent = self.universes.get(parent_universe_id)
            if not parent:
                self.logger.error("Parent universe %s not found", parent_universe_id)
                return None
            
            # Create new universe as branch
            branch_universe = Universe(
                dimension=parent.dimension.create_branch(quantum_deviation),
                quantum_state=parent.quantum_state.create_superposition(),
                reality_anchor=parent.reality_anchor.create_variant(),
                state=UniverseState.BRANCHING,
                probability=parent.probability * 0.5,  # Split probability
                parent_universe=parent_universe_id
            )
            
            # Add quantum variations
            branch_universe.properties = parent.properties.copy()
            for key, value in branch_universe.properties.items():
                if isinstance(value, (int, float)):
                    variance = np.random.normal(1.0, quantum_deviation)
                    branch_universe.properties[key] = value * variance
            
            # Update parent
            parent.child_universes.append(branch_universe.id)
            parent.probability *= 0.5  # Split probability
            
            # Register new universe
            self.universes[branch_universe.id] = branch_universe
            
            self.event_bus.emit(MultiverseEvent(
                event_type="universe_branched",
                data={
                    "parent_id": parent_universe_id,
                    "branch_id": branch_universe.id,
                    "quantum_deviation": quantum_deviation
                }
            ))
            
            self.logger.info("Universe branched: %s -> %s", 
                           parent_universe_id, branch_universe.id)
            return branch_universe.id
    
    def _collapse_universe(self, universe_id: str):
        """Collapse a universe that has become unstable."""
        universe = self.universes.get(universe_id)
        if not universe:
            return
        
        # Don't collapse primary universe
        if universe.properties.get('is_primary', False):
            self.logger.warning("Attempted to collapse primary universe")
            return
        
        # Remove from parent's children
        if universe.parent_universe:
            parent = self.universes.get(universe.parent_universe)
            if parent and universe_id in parent.child_universes:
                parent.child_universes.remove(universe_id)
        
        # Collapse all child universes first
        for child_id in universe.child_universes.copy():
            self._collapse_universe(child_id)
        
        # Remove universe
        del self.universes[universe_id]
        
        # Switch active universe if needed
        if self.active_universe_id == universe_id:
            self.active_universe_id = self._find_stable_universe()
        
        self.event_bus.emit(MultiverseEvent(
            event_type="universe_collapsed",
            data={"universe_id": universe_id}
        ))
        
        self.logger.info("Universe collapsed: %s", universe_id)
    
    def _find_stable_universe(self) -> Optional[str]:
        """Find the most stable universe to switch to."""
        stable_universes = [
            (uid, u) for uid, u in self.universes.items()
            if u.state in [UniverseState.STABLE, UniverseState.CONVERGING]
        ]
        
        if not stable_universes:
            return None
        
        # Return universe with highest probability
        return max(stable_universes, key=lambda x: x[1].probability)[0]
    
    def switch_universe(self, universe_id: str) -> bool:
        """
        Switch active universe context.
        
        Args:
            universe_id: ID of universe to switch to
            
        Returns:
            True if successful, False otherwise
        """
        with self.universe_lock:
            if universe_id not in self.universes:
                self.logger.error("Universe %s not found", universe_id)
                return False
            
            universe = self.universes[universe_id]
            if universe.state == UniverseState.COLLAPSED:
                self.logger.error("Cannot switch to collapsed universe %s", universe_id)
                return False
            
            old_universe_id = self.active_universe_id
            self.active_universe_id = universe_id
            
            self.event_bus.emit(MultiverseEvent(
                event_type="universe_switched",
                data={
                    "from_universe": old_universe_id,
                    "to_universe": universe_id
                }
            ))
            
            self.logger.info("Switched from universe %s to %s", 
                           old_universe_id, universe_id)
            return True
    
    def get_active_universe(self) -> Optional[Universe]:
        """Get the currently active universe."""
        with self.universe_lock:
            if self.active_universe_id:
                return self.universes.get(self.active_universe_id)
            return None
    
    def get_universe(self, universe_id: str) -> Optional[Universe]:
        """Get a specific universe by ID."""
        with self.universe_lock:
            return self.universes.get(universe_id)
    
    def list_universes(self) -> Dict[str, Dict[str, Any]]:
        """List all universes with their basic information."""
        with self.universe_lock:
            return {
                uid: {
                    'id': universe.id,
                    'state': universe.state.value,
                    'probability': universe.probability,
                    'entropy': universe.entropy,
                    'is_active': uid == self.active_universe_id,
                    'is_primary': universe.properties.get('is_primary', False),
                    'child_count': len(universe.child_universes),
                    'dimension': universe.dimension.to_dict()
                }
                for uid, universe in self.universes.items()
            }
    
    def get_multiverse_statistics(self) -> Dict[str, Any]:
        """Get comprehensive multiverse statistics."""
        with self.universe_lock:
            states = {}
            total_probability = 0.0
            total_entropy = 0.0
            
            for universe in self.universes.values():
                state = universe.state.value
                states[state] = states.get(state, 0) + 1
                total_probability += universe.probability
                total_entropy += universe.entropy
            
            return {
                'total_universes': len(self.universes),
                'active_universe': self.active_universe_id,
                'universe_states': states,
                'total_probability': total_probability,
                'average_entropy': total_entropy / len(self.universes) if self.universes else 0,
                'monitoring_active': self.is_running,
                'metrics': self.metrics.get_summary()
            }
    
    def create_universe_manually(self, config: Dict[str, Any]) -> str:
        """
        Manually create a new universe with specific configuration.
        
        Args:
            config: Configuration for the new universe
            
        Returns:
            ID of created universe
        """
        universe = Universe()
        
        # Apply configuration
        if 'dimension' in config:
            universe.dimension = DimensionalCoordinate(**config['dimension'])
        if 'properties' in config:
            universe.properties.update(config['properties'])
        if 'state' in config:
            universe.state = UniverseState(config['state'])
        
        with self.universe_lock:
            self.universes[universe.id] = universe
        
        self.event_bus.emit(MultiverseEvent(
            event_type="universe_created_manually",
            data={"universe_id": universe.id, "config": config}
        ))
        
        self.logger.info("Universe created manually: %s", universe.id)
        return universe.id
    
    def shutdown(self):
        """Shutdown the multiverse manager."""
        self.logger.info("Shutting down MultiverseManager")
        
        self.stop_monitoring()
        self.executor.shutdown(wait=True)
        
        # Emit shutdown event
        self.event_bus.emit(MultiverseEvent(
            event_type="multiverse_shutdown",
            data={"final_universe_count": len(self.universes)}
        ))
        
        self.logger.info("MultiverseManager shutdown complete")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()