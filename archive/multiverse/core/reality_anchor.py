"""
Reality Anchor System
====================

Provides stability anchors for maintaining coherent reality states across
parallel universes and preventing catastrophic reality collapse.
"""

import numpy as np
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
import math

from .base_multiverse import MultiverseComponent
from .config_manager import get_global_config


class AnchorType(Enum):
    """Types of reality anchors."""
    FUNDAMENTAL = "fundamental"
    CAUSAL = "causal"
    QUANTUM = "quantum"
    TEMPORAL = "temporal"
    CONSCIOUSNESS = "consciousness"
    PHYSICAL = "physical"
    INFORMATIONAL = "informational"
    EMERGENCY = "emergency"


class AnchorState(Enum):
    """States of reality anchors."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    STABILIZING = "stabilizing"
    WEAKENING = "weakening"
    CRITICAL = "critical"
    FAILED = "failed"
    DORMANT = "dormant"


@dataclass
class RealityAnchor:
    """Represents a reality stabilization anchor."""
    anchor_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    anchor_type: AnchorType = AnchorType.FUNDAMENTAL
    state: AnchorState = AnchorState.INITIALIZING
    
    # Spatial properties
    position: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    influence_radius: float = 10.0  # meters
    dimensional_depth: int = 3
    
    # Stability properties
    anchor_strength: float = 1.0  # 0-1 scale
    stability_field: float = 1.0
    coherence_factor: float = 1.0
    resonance_frequency: float = 1.0  # Hz
    
    # Energy properties
    energy_requirement: float = 1e12  # Joules
    current_energy: float = 0.0
    energy_efficiency: float = 0.9
    maintenance_energy_rate: float = 1e9  # J/s
    
    # Temporal properties
    creation_time: float = field(default_factory=time.time)
    last_maintenance: float = field(default_factory=time.time)
    degradation_rate: float = 0.001  # per second
    expected_lifetime: float = 86400.0  # 24 hours
    
    # Operational properties
    universe_id: Optional[str] = None
    protected_entities: List[str] = field(default_factory=list)
    anchor_network_id: Optional[str] = None
    backup_anchors: List[str] = field(default_factory=list)
    
    # Metadata
    created_by: str = "reality_anchor_system"
    purpose: str = "reality_stabilization"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize anchor with derived properties."""
        if isinstance(self.position, list):
            self.position = np.array(self.position)
        
        # Ensure position is 3D
        if self.position.size < 3:
            self.position = np.pad(self.position, (0, 3 - self.position.size))
    
    def calculate_influence_at_point(self, point: np.ndarray) -> float:
        """Calculate anchor influence at a specific point."""
        if isinstance(point, list):
            point = np.array(point)
        
        distance = np.linalg.norm(point - self.position)
        
        if distance > self.influence_radius:
            return 0.0
        
        # Gaussian influence falloff
        influence = math.exp(-0.5 * (distance / (self.influence_radius / 3))**2)
        
        # Scale by anchor strength and state
        state_multipliers = {
            AnchorState.ACTIVE: 1.0,
            AnchorState.STABILIZING: 0.8,
            AnchorState.WEAKENING: 0.5,
            AnchorState.CRITICAL: 0.2,
            AnchorState.FAILED: 0.0,
            AnchorState.DORMANT: 0.1,
            AnchorState.INITIALIZING: 0.3
        }
        
        state_multiplier = state_multipliers.get(self.state, 0.5)
        
        return influence * self.anchor_strength * state_multiplier
    
    def is_operational(self) -> bool:
        """Check if anchor is operational."""
        return (self.state in [AnchorState.ACTIVE, AnchorState.STABILIZING] and
                self.current_energy >= self.energy_requirement * 0.5 and
                self.anchor_strength > 0.3)
    
    def get_remaining_lifetime(self) -> float:
        """Get estimated remaining lifetime in seconds."""
        current_time = time.time()
        age = current_time - self.creation_time
        
        # Calculate degradation effect
        degraded_lifetime = self.expected_lifetime * (1.0 - self.degradation_rate * age)
        
        return max(0.0, degraded_lifetime - age)
    
    def needs_maintenance(self) -> bool:
        """Check if anchor needs maintenance."""
        current_time = time.time()
        time_since_maintenance = current_time - self.last_maintenance
        
        return (time_since_maintenance > 3600.0 or  # 1 hour
                self.anchor_strength < 0.7 or
                self.current_energy < self.energy_requirement * 0.6)
    
    def create_variant(self) -> 'RealityAnchor':
        """Create a variant anchor with slight modifications."""
        variant = RealityAnchor(
            anchor_type=self.anchor_type,
            position=self.position + np.random.normal(0, 1, 3),
            influence_radius=self.influence_radius * np.random.uniform(0.8, 1.2),
            anchor_strength=self.anchor_strength * np.random.uniform(0.9, 1.1),
            resonance_frequency=self.resonance_frequency * np.random.uniform(0.95, 1.05),
            universe_id=self.universe_id
        )
        
        # Add to backup list
        self.backup_anchors.append(variant.anchor_id)
        variant.metadata['parent_anchor'] = self.anchor_id
        
        return variant


class RealityStabilizer(MultiverseComponent):
    """
    Reality stabilization system using anchor networks.
    
    Manages reality anchors that maintain universe stability and prevent
    catastrophic reality collapse through distributed stabilization fields.
    """
    
    def __init__(self, multiverse_manager=None):
        """Initialize the reality stabilizer."""
        super().__init__("RealityStabilizer")
        
        self.multiverse_manager = multiverse_manager
        self.config = get_global_config()
        
        # Anchor management
        self.active_anchors: Dict[str, RealityAnchor] = {}
        self.universe_anchors: Dict[str, List[str]] = {}
        self.anchor_networks: Dict[str, List[str]] = {}
        self.anchor_lock = threading.RLock()
        
        # Stabilization parameters
        self.min_anchors_per_universe = 3
        self.max_anchors_per_universe = 10
        self.anchor_separation_distance = 50.0  # meters
        self.stability_threshold = 0.8
        self.emergency_anchor_threshold = 0.5
        
        # Energy management
        self.total_energy_pool = 1e15  # Joules
        self.energy_regeneration_rate = 1e12  # J/s
        self.energy_distribution_interval = 10.0  # seconds
        
        # Monitoring
        self.stability_check_interval = 5.0  # seconds
        self.maintenance_interval = 60.0  # seconds
        
        # Statistics
        self.total_anchors_deployed = 0
        self.stability_incidents = 0
        self.emergency_deployments = 0
        self.total_energy_consumed = 0.0
        
        self.logger.info("RealityStabilizer initialized")
    
    def on_start(self):
        """Start reality stabilization."""
        self.logger.info("Reality stabilization started")
        self.update_property("status", "stabilizing")
        
        # Deploy initial anchors
        self._deploy_initial_anchors()
        
        # Start monitoring threads
        self._start_monitoring_threads()
    
    def on_stop(self):
        """Stop reality stabilization."""
        # Gracefully shutdown anchors
        with self.anchor_lock:
            for anchor in self.active_anchors.values():
                self._deactivate_anchor(anchor)
        
        self.logger.info("Reality stabilization stopped")
        self.update_property("status", "stopped")
    
    def _deploy_initial_anchors(self):
        """Deploy initial anchors for existing universes."""
        if not self.multiverse_manager:
            return
        
        universes = self.multiverse_manager.list_universes()
        
        for universe_id in universes.keys():
            self.deploy_universe_anchors(universe_id)
    
    def _start_monitoring_threads(self):
        """Start stabilization monitoring threads."""
        def monitor_stability():
            while self.is_running:
                try:
                    self._check_universe_stability()
                    self._maintain_anchors()
                    time.sleep(self.stability_check_interval)
                except Exception as e:
                    self.logger.error("Error in stability monitoring: %s", e)
                    time.sleep(1.0)
        
        def manage_energy():
            while self.is_running:
                try:
                    self._regenerate_energy()
                    self._distribute_energy()
                    time.sleep(self.energy_distribution_interval)
                except Exception as e:
                    self.logger.error("Error in energy management: %s", e)
                    time.sleep(1.0)
        
        stability_monitor = threading.Thread(
            target=monitor_stability,
            daemon=True,
            name="StabilityMonitor"
        )
        stability_monitor.start()
        
        energy_manager = threading.Thread(
            target=manage_energy,
            daemon=True,
            name="EnergyManager"
        )
        energy_manager.start()
    
    def deploy_universe_anchors(self, universe_id: str) -> List[str]:
        """
        Deploy stabilization anchors for a universe.
        
        Args:
            universe_id: Universe to stabilize
            
        Returns:
            List of deployed anchor IDs
        """
        try:
            self.track_operation("deploy_universe_anchors")
            
            if not self.multiverse_manager:
                self.logger.error("No multiverse manager available")
                return []
            
            universe = self.multiverse_manager.get_universe(universe_id)
            if not universe:
                self.logger.error("Universe not found: %s", universe_id)
                return []
            
            # Calculate anchor positions
            anchor_positions = self._calculate_optimal_anchor_positions(universe)
            
            deployed_anchors = []
            
            with self.anchor_lock:
                for i, position in enumerate(anchor_positions):
                    anchor = self._create_anchor(
                        universe_id=universe_id,
                        position=position,
                        anchor_type=AnchorType.FUNDAMENTAL if i == 0 else AnchorType.PHYSICAL
                    )
                    
                    if anchor and self._deploy_anchor(anchor):
                        deployed_anchors.append(anchor.anchor_id)
                
                # Initialize universe anchor tracking
                if universe_id not in self.universe_anchors:
                    self.universe_anchors[universe_id] = []
                
                self.universe_anchors[universe_id].extend(deployed_anchors)
            
            # Create anchor network
            if len(deployed_anchors) > 1:
                network_id = f"network_{universe_id}"
                self.anchor_networks[network_id] = deployed_anchors.copy()
                
                # Update anchor network references
                for anchor_id in deployed_anchors:
                    anchor = self.active_anchors.get(anchor_id)
                    if anchor:
                        anchor.anchor_network_id = network_id
            
            self.emit_event("universe_anchors_deployed", {
                'universe_id': universe_id,
                'anchor_count': len(deployed_anchors),
                'anchor_ids': deployed_anchors
            })
            
            self.logger.info("Deployed %d anchors for universe %s", 
                           len(deployed_anchors), universe_id)
            
            return deployed_anchors
            
        except Exception as e:
            self.logger.error("Error deploying universe anchors: %s", e)
            self.track_error(e, "deploy_universe_anchors")
            return []
    
    def _calculate_optimal_anchor_positions(self, universe) -> List[np.ndarray]:
        """Calculate optimal positions for reality anchors."""
        # Start with universe center
        center = np.array([0.0, 0.0, 0.0])
        positions = [center]
        
        # Add positions in geometric pattern
        num_anchors = min(self.max_anchors_per_universe, 
                         max(self.min_anchors_per_universe, 
                             int(universe.entropy + 3)))
        
        if num_anchors > 1:
            # Distribute anchors in sphere around center
            for i in range(1, num_anchors):
                # Golden spiral distribution
                theta = i * 2.4  # Golden angle approximation
                phi = math.acos(1 - 2 * i / num_anchors)
                
                x = self.anchor_separation_distance * math.sin(phi) * math.cos(theta)
                y = self.anchor_separation_distance * math.sin(phi) * math.sin(theta)
                z = self.anchor_separation_distance * math.cos(phi)
                
                positions.append(np.array([x, y, z]))
        
        return positions
    
    def _create_anchor(self, universe_id: str, position: np.ndarray,
                      anchor_type: AnchorType = AnchorType.PHYSICAL) -> Optional[RealityAnchor]:
        """Create a new reality anchor."""
        anchor = RealityAnchor(
            anchor_type=anchor_type,
            position=position.copy(),
            universe_id=universe_id,
            influence_radius=self.anchor_separation_distance / 2,
            energy_requirement=1e12 * (1.5 if anchor_type == AnchorType.FUNDAMENTAL else 1.0)
        )
        
        # Set anchor properties based on type
        type_properties = {
            AnchorType.FUNDAMENTAL: {
                'anchor_strength': 1.0,
                'resonance_frequency': 1.0,
                'expected_lifetime': 86400.0 * 7  # 1 week
            },
            AnchorType.PHYSICAL: {
                'anchor_strength': 0.8,
                'resonance_frequency': 2.0,
                'expected_lifetime': 86400.0 * 3  # 3 days
            },
            AnchorType.QUANTUM: {
                'anchor_strength': 0.9,
                'resonance_frequency': 10.0,
                'expected_lifetime': 3600.0 * 12  # 12 hours
            },
            AnchorType.EMERGENCY: {
                'anchor_strength': 0.6,
                'resonance_frequency': 0.5,
                'expected_lifetime': 3600.0  # 1 hour
            }
        }
        
        properties = type_properties.get(anchor_type, {})
        for key, value in properties.items():
            setattr(anchor, key, value)
        
        return anchor
    
    def _deploy_anchor(self, anchor: RealityAnchor) -> bool:
        """Deploy and activate a reality anchor."""
        try:
            # Check energy availability
            if self.total_energy_pool < anchor.energy_requirement:
                self.logger.warning("Insufficient energy to deploy anchor")
                return False
            
            # Initialize anchor
            anchor.state = AnchorState.INITIALIZING
            
            # Charge anchor
            self.total_energy_pool -= anchor.energy_requirement
            anchor.current_energy = anchor.energy_requirement * anchor.energy_efficiency
            self.total_energy_consumed += anchor.energy_requirement
            
            # Activate anchor
            anchor.state = AnchorState.ACTIVE
            anchor.last_maintenance = time.time()
            
            # Register anchor
            self.active_anchors[anchor.anchor_id] = anchor
            self.total_anchors_deployed += 1
            
            self.emit_event("anchor_deployed", {
                'anchor_id': anchor.anchor_id,
                'anchor_type': anchor.anchor_type.value,
                'universe_id': anchor.universe_id,
                'position': anchor.position.tolist()
            })
            
            self.logger.debug("Anchor deployed: %s (%s)", 
                            anchor.anchor_id, anchor.anchor_type.value)
            
            return True
            
        except Exception as e:
            self.logger.error("Error deploying anchor: %s", e)
            return False
    
    def deploy_emergency_anchor(self, universe_id: str, 
                              position: Optional[np.ndarray] = None) -> Optional[str]:
        """
        Deploy emergency anchor for critical stability issues.
        
        Args:
            universe_id: Universe requiring emergency stabilization
            position: Specific position for anchor (optional)
            
        Returns:
            Anchor ID if successful, None otherwise
        """
        try:
            if position is None:
                # Use universe center as default
                position = np.array([0.0, 0.0, 0.0])
            
            # Create emergency anchor with reduced requirements
            anchor = self._create_anchor(
                universe_id=universe_id,
                position=position,
                anchor_type=AnchorType.EMERGENCY
            )
            
            if anchor:
                # Reduce energy requirement for emergency deployment
                anchor.energy_requirement *= 0.5
                
                if self._deploy_anchor(anchor):
                    # Add to universe anchors
                    with self.anchor_lock:
                        if universe_id not in self.universe_anchors:
                            self.universe_anchors[universe_id] = []
                        self.universe_anchors[universe_id].append(anchor.anchor_id)
                    
                    self.emergency_deployments += 1
                    
                    self.emit_event("emergency_anchor_deployed", {
                        'anchor_id': anchor.anchor_id,
                        'universe_id': universe_id,
                        'deployment_time': time.time()
                    })
                    
                    self.logger.warning("Emergency anchor deployed for universe %s", universe_id)
                    
                    return anchor.anchor_id
            
            return None
            
        except Exception as e:
            self.logger.error("Error deploying emergency anchor: %s", e)
            return None
    
    def _check_universe_stability(self):
        """Check stability of all universes."""
        if not self.multiverse_manager:
            return
        
        universes = self.multiverse_manager.list_universes()
        
        for universe_id, universe_info in universes.items():
            stability = self._calculate_universe_stability(universe_id)
            
            if stability < self.emergency_anchor_threshold:
                self.logger.critical("Critical stability in universe %s: %.2f", 
                                   universe_id, stability)
                
                # Deploy emergency anchor
                self.deploy_emergency_anchor(universe_id)
                self.stability_incidents += 1
                
            elif stability < self.stability_threshold:
                self.logger.warning("Low stability in universe %s: %.2f", 
                                  universe_id, stability)
                
                # Strengthen existing anchors
                self._strengthen_universe_anchors(universe_id)
    
    def _calculate_universe_stability(self, universe_id: str) -> float:
        """Calculate overall stability of a universe."""
        with self.anchor_lock:
            anchor_ids = self.universe_anchors.get(universe_id, [])
            
            if not anchor_ids:
                return 0.0  # No anchors = no stability
            
            total_influence = 0.0
            active_anchors = 0
            
            for anchor_id in anchor_ids:
                anchor = self.active_anchors.get(anchor_id)
                if anchor and anchor.is_operational():
                    # Calculate anchor contribution to universe stability
                    influence = anchor.calculate_influence_at_point(np.array([0.0, 0.0, 0.0]))
                    total_influence += influence * anchor.anchor_strength
                    active_anchors += 1
            
            if active_anchors == 0:
                return 0.0
            
            # Normalize by number of anchors and expected influence
            expected_influence = active_anchors * 0.8  # Expected average
            stability = min(1.0, total_influence / expected_influence)
            
            return stability
    
    def _strengthen_universe_anchors(self, universe_id: str):
        """Strengthen anchors in a universe with low stability."""
        with self.anchor_lock:
            anchor_ids = self.universe_anchors.get(universe_id, [])
            
            for anchor_id in anchor_ids:
                anchor = self.active_anchors.get(anchor_id)
                if anchor and anchor.is_operational():
                    # Boost anchor strength if energy available
                    if self.total_energy_pool > 1e11:
                        energy_boost = 1e11
                        self.total_energy_pool -= energy_boost
                        anchor.current_energy += energy_boost
                        anchor.anchor_strength = min(1.0, anchor.anchor_strength + 0.1)
                        
                        self.logger.debug("Strengthened anchor %s", anchor_id)
    
    def _maintain_anchors(self):
        """Perform maintenance on all anchors."""
        current_time = time.time()
        
        with self.anchor_lock:
            anchors_to_remove = []
            
            for anchor_id, anchor in self.active_anchors.items():
                # Check if anchor needs replacement
                if anchor.get_remaining_lifetime() <= 0:
                    anchors_to_remove.append(anchor_id)
                    continue
                
                # Perform maintenance if needed
                if anchor.needs_maintenance():
                    self._perform_anchor_maintenance(anchor)
                
                # Update anchor degradation
                time_since_creation = current_time - anchor.creation_time
                degradation = anchor.degradation_rate * time_since_creation
                anchor.anchor_strength = max(0.1, anchor.anchor_strength - degradation)
                
                # Update energy consumption
                energy_consumed = anchor.maintenance_energy_rate * self.stability_check_interval
                anchor.current_energy = max(0.0, anchor.current_energy - energy_consumed)
                
                # Update anchor state based on energy and strength
                if anchor.current_energy < anchor.energy_requirement * 0.3:
                    anchor.state = AnchorState.CRITICAL
                elif anchor.anchor_strength < 0.5:
                    anchor.state = AnchorState.WEAKENING
                elif anchor.current_energy < anchor.energy_requirement * 0.6:
                    anchor.state = AnchorState.STABILIZING
                else:
                    anchor.state = AnchorState.ACTIVE
            
            # Remove failed anchors
            for anchor_id in anchors_to_remove:
                self._remove_anchor(anchor_id)
    
    def _perform_anchor_maintenance(self, anchor: RealityAnchor):
        """Perform maintenance on a specific anchor."""
        maintenance_energy = anchor.energy_requirement * 0.2
        
        if self.total_energy_pool >= maintenance_energy:
            self.total_energy_pool -= maintenance_energy
            anchor.current_energy += maintenance_energy
            anchor.anchor_strength = min(1.0, anchor.anchor_strength + 0.05)
            anchor.last_maintenance = time.time()
            
            self.logger.debug("Maintenance performed on anchor %s", anchor.anchor_id)
    
    def _remove_anchor(self, anchor_id: str):
        """Remove a failed or expired anchor."""
        anchor = self.active_anchors.get(anchor_id)
        if not anchor:
            return
        
        # Remove from tracking
        del self.active_anchors[anchor_id]
        
        if anchor.universe_id in self.universe_anchors:
            try:
                self.universe_anchors[anchor.universe_id].remove(anchor_id)
            except ValueError:
                pass
        
        # Remove from networks
        for network_id, anchor_ids in list(self.anchor_networks.items()):
            if anchor_id in anchor_ids:
                anchor_ids.remove(anchor_id)
                if not anchor_ids:  # Empty network
                    del self.anchor_networks[network_id]
        
        self._deactivate_anchor(anchor)
        
        self.emit_event("anchor_removed", {
            'anchor_id': anchor_id,
            'universe_id': anchor.universe_id,
            'removal_time': time.time()
        })
        
        self.logger.info("Anchor removed: %s", anchor_id)
        
        # Deploy replacement if needed
        if anchor.universe_id and len(self.universe_anchors.get(anchor.universe_id, [])) < self.min_anchors_per_universe:
            self.deploy_emergency_anchor(anchor.universe_id)
    
    def _deactivate_anchor(self, anchor: RealityAnchor):
        """Deactivate an anchor and recover energy."""
        anchor.state = AnchorState.FAILED
        
        # Recover some energy
        recovered_energy = anchor.current_energy * 0.8
        self.total_energy_pool += recovered_energy
        anchor.current_energy = 0.0
    
    def _regenerate_energy(self):
        """Regenerate energy for anchor operations."""
        energy_gain = self.energy_regeneration_rate * self.energy_distribution_interval
        self.total_energy_pool += energy_gain
        
        # Cap at maximum
        max_capacity = 1e18
        self.total_energy_pool = min(max_capacity, self.total_energy_pool)
    
    def _distribute_energy(self):
        """Distribute energy to anchors that need it."""
        with self.anchor_lock:
            # Prioritize critical and fundamental anchors
            priority_anchors = []
            regular_anchors = []
            
            for anchor in self.active_anchors.values():
                if (anchor.state == AnchorState.CRITICAL or 
                    anchor.anchor_type == AnchorType.FUNDAMENTAL):
                    priority_anchors.append(anchor)
                else:
                    regular_anchors.append(anchor)
            
            # Distribute to priority anchors first
            available_energy = self.total_energy_pool * 0.1  # Use 10% for distribution
            
            for anchor in priority_anchors + regular_anchors:
                if available_energy <= 0:
                    break
                
                energy_deficit = max(0.0, anchor.energy_requirement - anchor.current_energy)
                if energy_deficit > 0:
                    allocation = min(available_energy, energy_deficit)
                    anchor.current_energy += allocation
                    available_energy -= allocation
                    self.total_energy_pool -= allocation
    
    def get_stabilizer_statistics(self) -> Dict[str, Any]:
        """Get comprehensive stabilizer statistics."""
        with self.anchor_lock:
            anchor_states = {}
            anchor_types = {}
            total_influence = 0.0
            
            for anchor in self.active_anchors.values():
                state = anchor.state.value
                anchor_type = anchor.anchor_type.value
                
                anchor_states[state] = anchor_states.get(state, 0) + 1
                anchor_types[anchor_type] = anchor_types.get(anchor_type, 0) + 1
                
                total_influence += anchor.anchor_strength
            
            return {
                'total_anchors_deployed': self.total_anchors_deployed,
                'active_anchors': len(self.active_anchors),
                'anchor_networks': len(self.anchor_networks),
                'universes_stabilized': len(self.universe_anchors),
                'stability_incidents': self.stability_incidents,
                'emergency_deployments': self.emergency_deployments,
                'total_energy_pool': self.total_energy_pool,
                'total_energy_consumed': self.total_energy_consumed,
                'total_influence': total_influence,
                'anchor_states': anchor_states,
                'anchor_types': anchor_types,
                'stabilizer_status': self.get_property('status', 'unknown')
            }
    
    def on_health_check(self) -> Optional[Dict[str, Any]]:
        """Health check for reality stabilizer."""
        with self.anchor_lock:
            operational_anchors = sum(1 for a in self.active_anchors.values() if a.is_operational())
            
            return {
                'active_anchors': len(self.active_anchors),
                'operational_anchors': operational_anchors,
                'universes_stabilized': len(self.universe_anchors),
                'energy_pool': self.total_energy_pool,
                'stabilizer_active': self.is_running
            }