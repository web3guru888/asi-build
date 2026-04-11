"""
Dimensional Portal Generator
===========================

Generates interdimensional portals for travel between parallel universes,
managing portal creation, stabilization, and energy requirements.
"""

import numpy as np
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import math
import cmath
from concurrent.futures import ThreadPoolExecutor

from ..core.base_multiverse import MultiverseComponent
from ..core.dimensional_coordinate import DimensionalCoordinate
from ..core.config_manager import get_global_config


class PortalType(Enum):
    """Types of dimensional portals."""
    POINT_TO_POINT = "point_to_point"
    BROADCAST = "broadcast"
    WORMHOLE = "wormhole"
    QUANTUM_TUNNEL = "quantum_tunnel"
    RIFT = "rift"
    BRIDGE = "bridge"
    GATEWAY = "gateway"
    EMERGENCY = "emergency"


class PortalState(Enum):
    """States of portal operation."""
    INITIALIZING = "initializing"
    CHARGING = "charging"
    STABLE = "stable"
    ACTIVE = "active"
    UNSTABLE = "unstable"
    COLLAPSING = "collapsing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class Portal:
    """Represents a dimensional portal."""
    portal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    portal_type: PortalType = PortalType.POINT_TO_POINT
    state: PortalState = PortalState.INITIALIZING
    
    # Spatial properties
    origin_coordinate: DimensionalCoordinate = field(default_factory=DimensionalCoordinate)
    destination_coordinate: DimensionalCoordinate = field(default_factory=DimensionalCoordinate)
    aperture_radius: float = 1.0  # meters
    
    # Energy properties
    energy_requirement: float = 1e15  # Joules (Planck scale)
    current_energy: float = 0.0
    energy_efficiency: float = 0.8
    
    # Stability properties
    stability_rating: float = 1.0  # 0-1 scale
    coherence_field_strength: float = 1.0
    dimensional_resonance: float = 1.0
    
    # Temporal properties
    creation_time: float = field(default_factory=time.time)
    activation_time: Optional[float] = None
    lifetime: float = 3600.0  # seconds (1 hour default)
    
    # Quantum properties
    quantum_entanglement_strength: float = 1.0
    wave_function_overlap: float = 0.5
    uncertainty_factor: float = 0.1
    
    # Operational properties
    max_throughput: float = 1000.0  # kg/s
    current_load: float = 0.0
    bidirectional: bool = True
    requires_maintenance: bool = False
    
    # Metadata
    created_by: str = "dimensional_portal_generator"
    purpose: str = "interdimensional_travel"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_dimensional_distance(self) -> float:
        """Calculate distance between origin and destination in dimensional space."""
        return self.origin_coordinate.distance_to(self.destination_coordinate)
    
    def calculate_energy_cost(self) -> float:
        """Calculate total energy cost for portal operation."""
        # Base energy from dimensional distance
        distance = self.calculate_dimensional_distance()
        distance_cost = distance * 1e12  # Energy scales with distance
        
        # Aperture cost (energy scales with area)
        aperture_cost = math.pi * self.aperture_radius**2 * 1e13
        
        # Stability cost (more stable = more energy)
        stability_cost = self.stability_rating * 1e14
        
        # Type modifier
        type_modifiers = {
            PortalType.POINT_TO_POINT: 1.0,
            PortalType.BROADCAST: 2.0,
            PortalType.WORMHOLE: 1.5,
            PortalType.QUANTUM_TUNNEL: 0.8,
            PortalType.RIFT: 0.6,
            PortalType.BRIDGE: 3.0,
            PortalType.GATEWAY: 4.0,
            PortalType.EMERGENCY: 0.5
        }
        
        modifier = type_modifiers.get(self.portal_type, 1.0)
        
        return (distance_cost + aperture_cost + stability_cost) * modifier
    
    def is_operational(self) -> bool:
        """Check if portal is operational."""
        return (self.state in [PortalState.STABLE, PortalState.ACTIVE] and
                self.current_energy >= self.energy_requirement * 0.8 and
                self.stability_rating > 0.5)
    
    def get_remaining_lifetime(self) -> float:
        """Get remaining portal lifetime in seconds."""
        if self.activation_time is None:
            return self.lifetime
        
        elapsed = time.time() - self.activation_time
        return max(0.0, self.lifetime - elapsed)
    
    def calculate_transit_probability(self, mass: float) -> float:
        """Calculate probability of successful transit for given mass."""
        # Base probability from stability
        base_prob = self.stability_rating
        
        # Load factor
        load_factor = min(1.0, self.current_load / self.max_throughput)
        load_penalty = 1.0 - 0.5 * load_factor
        
        # Mass factor (heavier objects harder to transport)
        mass_factor = math.exp(-mass / 1000.0)  # Exponential decay with mass
        
        # Energy factor
        energy_factor = min(1.0, self.current_energy / self.energy_requirement)
        
        # Quantum uncertainty
        uncertainty_penalty = 1.0 - self.uncertainty_factor
        
        total_probability = (base_prob * load_penalty * mass_factor * 
                           energy_factor * uncertainty_penalty)
        
        return max(0.0, min(1.0, total_probability))


class DimensionalPortalGenerator(MultiverseComponent):
    """
    Generator for dimensional portals enabling travel between universes.
    
    Creates, manages, and maintains portals with various types and properties
    for interdimensional navigation and transportation.
    """
    
    def __init__(self, multiverse_manager=None):
        """Initialize the dimensional portal generator."""
        super().__init__("DimensionalPortalGenerator")
        
        self.multiverse_manager = multiverse_manager
        self.config = get_global_config()
        
        # Portal management
        self.active_portals: Dict[str, Portal] = {}
        self.portal_history: List[Portal] = []
        self.portal_lock = threading.RLock()
        
        # Energy management
        self.total_energy_available = 1e18  # Joules
        self.energy_regeneration_rate = 1e15  # Joules/second
        self.energy_efficiency = 0.85
        
        # Generation parameters
        self.max_concurrent_portals = 10
        self.default_portal_lifetime = 3600.0  # 1 hour
        self.stability_threshold = 0.7
        self.energy_safety_margin = 0.2
        
        # Monitoring
        self.portal_monitor_interval = 5.0  # seconds
        self.energy_monitor_interval = 1.0  # seconds
        
        # Statistics
        self.total_portals_created = 0
        self.successful_transits = 0
        self.failed_transits = 0
        self.total_energy_consumed = 0.0
        
        # Thread pool for portal operations
        self.executor = ThreadPoolExecutor(
            max_workers=self.config.performance.max_worker_threads,
            thread_name_prefix="PortalGenerator"
        )
        
        self.logger.info("DimensionalPortalGenerator initialized")
    
    def on_start(self):
        """Start the portal generator."""
        self.logger.info("Dimensional portal generator started")
        self.update_property("status", "active")
        
        # Start monitoring threads
        self._start_monitoring_threads()
    
    def on_stop(self):
        """Stop the portal generator."""
        # Close all active portals
        with self.portal_lock:
            for portal in self.active_portals.values():
                self._close_portal(portal)
        
        self.executor.shutdown(wait=True)
        self.logger.info("Dimensional portal generator stopped")
        self.update_property("status", "stopped")
    
    def _start_monitoring_threads(self):
        """Start portal and energy monitoring threads."""
        def monitor_portals():
            while self.is_running:
                try:
                    self._update_portal_states()
                    self._maintain_portals()
                    time.sleep(self.portal_monitor_interval)
                except Exception as e:
                    self.logger.error("Error in portal monitoring: %s", e)
                    time.sleep(1.0)
        
        def monitor_energy():
            while self.is_running:
                try:
                    self._regenerate_energy()
                    self._balance_energy_distribution()
                    time.sleep(self.energy_monitor_interval)
                except Exception as e:
                    self.logger.error("Error in energy monitoring: %s", e)
                    time.sleep(1.0)
        
        portal_monitor = threading.Thread(
            target=monitor_portals,
            daemon=True,
            name="PortalMonitor"
        )
        portal_monitor.start()
        
        energy_monitor = threading.Thread(
            target=monitor_energy,
            daemon=True,
            name="EnergyMonitor"
        )
        energy_monitor.start()
    
    def generate_portal(self, 
                       origin_universe_id: str,
                       destination_universe_id: str,
                       origin_position: Optional[Tuple[float, float, float]] = None,
                       destination_position: Optional[Tuple[float, float, float]] = None,
                       portal_type: PortalType = PortalType.POINT_TO_POINT,
                       aperture_radius: float = 1.0,
                       lifetime: Optional[float] = None,
                       stability_requirement: float = 0.8,
                       **kwargs) -> Optional[str]:
        """
        Generate a new dimensional portal.
        
        Args:
            origin_universe_id: Source universe ID
            destination_universe_id: Destination universe ID
            origin_position: Position in origin universe (x, y, z)
            destination_position: Position in destination universe (x, y, z)
            portal_type: Type of portal to create
            aperture_radius: Portal aperture radius in meters
            lifetime: Portal lifetime in seconds
            stability_requirement: Minimum stability rating required
            **kwargs: Additional portal parameters
            
        Returns:
            Portal ID if successful, None otherwise
        """
        try:
            self.track_operation("generate_portal")
            
            # Check concurrent portal limit
            if len(self.active_portals) >= self.max_concurrent_portals:
                self.logger.warning("Maximum concurrent portals reached")
                return None
            
            # Create dimensional coordinates
            origin_coord = self._create_dimensional_coordinate(
                origin_universe_id, origin_position
            )
            dest_coord = self._create_dimensional_coordinate(
                destination_universe_id, destination_position
            )
            
            # Create portal
            portal = Portal(
                portal_type=portal_type,
                origin_coordinate=origin_coord,
                destination_coordinate=dest_coord,
                aperture_radius=aperture_radius,
                lifetime=lifetime or self.default_portal_lifetime,
                stability_rating=stability_requirement
            )
            
            # Apply additional parameters
            for key, value in kwargs.items():
                if hasattr(portal, key):
                    setattr(portal, key, value)
            
            # Calculate energy requirements
            portal.energy_requirement = portal.calculate_energy_cost()
            
            # Check energy availability
            if portal.energy_requirement > self.total_energy_available * (1 - self.energy_safety_margin):
                self.logger.error("Insufficient energy for portal generation")
                return None
            
            # Initialize portal
            if self._initialize_portal(portal):
                with self.portal_lock:
                    self.active_portals[portal.portal_id] = portal
                    self.portal_history.append(portal)
                    self.total_portals_created += 1
                
                self.emit_event("portal_generated", {
                    'portal_id': portal.portal_id,
                    'portal_type': portal_type.value,
                    'origin_universe': origin_universe_id,
                    'destination_universe': destination_universe_id
                })
                
                self.logger.info("Portal generated: %s (%s) %s -> %s",
                               portal.portal_id, portal_type.value,
                               origin_universe_id, destination_universe_id)
                
                return portal.portal_id
            
            return None
            
        except Exception as e:
            self.logger.error("Error generating portal: %s", e)
            self.track_error(e, "generate_portal")
            return None
    
    def _create_dimensional_coordinate(self, universe_id: str, 
                                     position: Optional[Tuple[float, float, float]]) -> DimensionalCoordinate:
        """Create dimensional coordinate for portal endpoint."""
        pos = position or (0.0, 0.0, 0.0)
        
        # Get universe dimension from multiverse manager
        dimension = 0
        if self.multiverse_manager:
            universe = self.multiverse_manager.get_universe(universe_id)
            if universe:
                dimension = universe.dimension.w  # Use w-coordinate as dimension
        
        return DimensionalCoordinate(
            x=pos[0], y=pos[1], z=pos[2], 
            t=time.time(), w=dimension,
            universe_id=universe_id
        )
    
    def _initialize_portal(self, portal: Portal) -> bool:
        """Initialize a portal through the generation sequence."""
        try:
            # Phase 1: Dimensional analysis
            portal.state = PortalState.INITIALIZING
            self._analyze_dimensional_compatibility(portal)
            
            # Phase 2: Energy charging
            portal.state = PortalState.CHARGING
            if not self._charge_portal(portal):
                return False
            
            # Phase 3: Quantum entanglement
            self._establish_quantum_entanglement(portal)
            
            # Phase 4: Stability verification
            if not self._verify_portal_stability(portal):
                return False
            
            # Phase 5: Activation
            portal.state = PortalState.STABLE
            portal.activation_time = time.time()
            
            return True
            
        except Exception as e:
            self.logger.error("Error initializing portal %s: %s", portal.portal_id, e)
            portal.state = PortalState.ERROR
            return False
    
    def _analyze_dimensional_compatibility(self, portal: Portal):
        """Analyze compatibility between dimensional coordinates."""
        distance = portal.calculate_dimensional_distance()
        
        # Check if dimensions are too far apart
        if distance > 100.0:  # Arbitrary maximum distance
            portal.stability_rating *= 0.8
            self.logger.warning("Large dimensional distance may affect stability")
        
        # Check for dimensional barriers
        barrier_strength = self._calculate_dimensional_barrier(portal)
        portal.stability_rating *= (1.0 - barrier_strength * 0.5)
        
        # Update energy requirement based on compatibility
        compatibility_factor = 1.0 + distance * 0.1 + barrier_strength
        portal.energy_requirement *= compatibility_factor
    
    def _calculate_dimensional_barrier(self, portal: Portal) -> float:
        """Calculate strength of dimensional barriers between coordinates."""
        # Simplified barrier calculation based on coordinate differences
        origin = portal.origin_coordinate
        dest = portal.destination_coordinate
        
        # Different universes have barriers
        universe_barrier = 0.5 if origin.universe_id != dest.universe_id else 0.0
        
        # Temporal barriers
        time_diff = abs(dest.t - origin.t)
        temporal_barrier = min(0.3, time_diff / 86400.0)  # Max 0.3 for 1 day difference
        
        # Dimensional barriers
        dim_diff = abs(dest.w - origin.w)
        dimensional_barrier = min(0.4, dim_diff * 0.1)
        
        return min(1.0, universe_barrier + temporal_barrier + dimensional_barrier)
    
    def _charge_portal(self, portal: Portal) -> bool:
        """Charge portal with required energy."""
        required_energy = portal.energy_requirement
        
        if self.total_energy_available < required_energy:
            self.logger.error("Insufficient energy to charge portal")
            return False
        
        # Simulate charging process
        charging_time = required_energy / (1e16)  # 1e16 J/s charging rate
        time.sleep(min(0.1, charging_time))  # Brief simulation delay
        
        # Transfer energy
        self.total_energy_available -= required_energy
        portal.current_energy = required_energy * portal.energy_efficiency
        self.total_energy_consumed += required_energy
        
        return True
    
    def _establish_quantum_entanglement(self, portal: Portal):
        """Establish quantum entanglement between portal endpoints."""
        # Calculate entanglement strength based on dimensional distance
        distance = portal.calculate_dimensional_distance()
        max_distance = 50.0  # Maximum effective distance
        
        entanglement_strength = max(0.1, 1.0 - distance / max_distance)
        portal.quantum_entanglement_strength = entanglement_strength
        
        # Calculate wave function overlap
        overlap = entanglement_strength * 0.8 + 0.1
        portal.wave_function_overlap = overlap
        
        # Update stability based on entanglement
        portal.stability_rating *= (0.5 + 0.5 * entanglement_strength)
    
    def _verify_portal_stability(self, portal: Portal) -> bool:
        """Verify portal meets stability requirements."""
        if portal.stability_rating < self.stability_threshold:
            self.logger.warning("Portal stability below threshold: %.2f < %.2f",
                              portal.stability_rating, self.stability_threshold)
            
            # Attempt stabilization
            if self._attempt_portal_stabilization(portal):
                return True
            else:
                portal.state = PortalState.UNSTABLE
                return False
        
        return True
    
    def _attempt_portal_stabilization(self, portal: Portal) -> bool:
        """Attempt to stabilize an unstable portal."""
        # Increase energy allocation
        additional_energy = portal.energy_requirement * 0.2
        
        if self.total_energy_available >= additional_energy:
            self.total_energy_available -= additional_energy
            portal.current_energy += additional_energy
            portal.stability_rating += 0.2
            
            self.logger.info("Portal stabilized with additional energy")
            return True
        
        return False
    
    def activate_portal(self, portal_id: str) -> bool:
        """
        Activate a portal for transit operations.
        
        Args:
            portal_id: Portal to activate
            
        Returns:
            True if successful, False otherwise
        """
        with self.portal_lock:
            portal = self.active_portals.get(portal_id)
            if not portal:
                self.logger.error("Portal not found: %s", portal_id)
                return False
            
            if portal.state != PortalState.STABLE:
                self.logger.error("Portal not stable, cannot activate: %s", portal_id)
                return False
            
            portal.state = PortalState.ACTIVE
            
            self.emit_event("portal_activated", {
                'portal_id': portal_id,
                'activation_time': time.time()
            })
            
            self.logger.info("Portal activated: %s", portal_id)
            return True
    
    def close_portal(self, portal_id: str) -> bool:
        """
        Close an active portal.
        
        Args:
            portal_id: Portal to close
            
        Returns:
            True if successful, False otherwise
        """
        with self.portal_lock:
            portal = self.active_portals.get(portal_id)
            if not portal:
                self.logger.error("Portal not found: %s", portal_id)
                return False
            
            self._close_portal(portal)
            del self.active_portals[portal_id]
            
            self.emit_event("portal_closed", {
                'portal_id': portal_id,
                'closure_time': time.time()
            })
            
            self.logger.info("Portal closed: %s", portal_id)
            return True
    
    def _close_portal(self, portal: Portal):
        """Internal portal closure logic."""
        portal.state = PortalState.COLLAPSING
        
        # Return unused energy
        unused_energy = portal.current_energy * 0.8  # 20% loss on closure
        self.total_energy_available += unused_energy
        
        portal.current_energy = 0.0
        portal.state = PortalState.CLOSED
    
    def simulate_transit(self, portal_id: str, mass: float, 
                        data_payload: Optional[Dict] = None) -> bool:
        """
        Simulate transit through a portal.
        
        Args:
            portal_id: Portal to use for transit
            mass: Mass of object/data transiting (kg)
            data_payload: Optional data payload
            
        Returns:
            True if transit successful, False otherwise
        """
        with self.portal_lock:
            portal = self.active_portals.get(portal_id)
            if not portal:
                self.logger.error("Portal not found: %s", portal_id)
                return False
            
            if not portal.is_operational():
                self.logger.error("Portal not operational: %s", portal_id)
                return False
            
            # Calculate transit probability
            transit_probability = portal.calculate_transit_probability(mass)
            
            # Check capacity
            if portal.current_load + mass > portal.max_throughput:
                self.logger.warning("Portal capacity exceeded")
                return False
            
            # Simulate transit
            if np.random.random() < transit_probability:
                # Successful transit
                portal.current_load += mass
                
                # Energy consumption for transit
                transit_energy = mass * 1e9  # 1 GJ per kg
                portal.current_energy -= transit_energy
                
                self.successful_transits += 1
                
                self.emit_event("transit_successful", {
                    'portal_id': portal_id,
                    'mass': mass,
                    'probability': transit_probability,
                    'data_payload': data_payload is not None
                })
                
                # Reduce load after brief delay (simulate transit time)
                def reduce_load():
                    time.sleep(0.1)  # Brief transit time
                    portal.current_load = max(0.0, portal.current_load - mass)
                
                self.executor.submit(reduce_load)
                
                return True
            else:
                # Failed transit
                self.failed_transits += 1
                
                self.emit_event("transit_failed", {
                    'portal_id': portal_id,
                    'mass': mass,
                    'probability': transit_probability
                })
                
                return False
    
    def _update_portal_states(self):
        """Update states of all active portals."""
        current_time = time.time()
        
        with self.portal_lock:
            portals_to_close = []
            
            for portal_id, portal in self.active_portals.items():
                # Check lifetime
                if portal.get_remaining_lifetime() <= 0:
                    portals_to_close.append(portal_id)
                    continue
                
                # Check energy levels
                if portal.current_energy < portal.energy_requirement * 0.3:
                    portal.state = PortalState.UNSTABLE
                
                # Check stability degradation
                age = current_time - portal.creation_time
                stability_decay = age / (24 * 3600)  # Decay over 24 hours
                portal.stability_rating *= (1.0 - stability_decay * 0.1)
                
                if portal.stability_rating < 0.3:
                    portals_to_close.append(portal_id)
            
            # Close expired/unstable portals
            for portal_id in portals_to_close:
                self.close_portal(portal_id)
    
    def _maintain_portals(self):
        """Perform maintenance on active portals."""
        with self.portal_lock:
            for portal in self.active_portals.values():
                if portal.requires_maintenance:
                    self._perform_portal_maintenance(portal)
    
    def _perform_portal_maintenance(self, portal: Portal):
        """Perform maintenance on a specific portal."""
        # Boost stability
        portal.stability_rating = min(1.0, portal.stability_rating + 0.1)
        
        # Refresh energy if available
        if self.total_energy_available > 1e14:
            energy_boost = min(1e14, portal.energy_requirement * 0.1)
            self.total_energy_available -= energy_boost
            portal.current_energy += energy_boost
        
        portal.requires_maintenance = False
        
        self.logger.debug("Maintenance performed on portal: %s", portal.portal_id)
    
    def _regenerate_energy(self):
        """Regenerate energy for portal operations."""
        energy_gain = self.energy_regeneration_rate * self.energy_monitor_interval
        self.total_energy_available += energy_gain
        
        # Cap at maximum capacity
        max_capacity = 1e20  # 100 EJ maximum
        self.total_energy_available = min(max_capacity, self.total_energy_available)
    
    def _balance_energy_distribution(self):
        """Balance energy distribution among active portals."""
        with self.portal_lock:
            if not self.active_portals:
                return
            
            # Calculate total energy deficit
            total_deficit = 0.0
            for portal in self.active_portals.values():
                deficit = max(0.0, portal.energy_requirement - portal.current_energy)
                total_deficit += deficit
            
            # Distribute available energy proportionally
            if total_deficit > 0 and self.total_energy_available > 1e15:
                available_for_distribution = min(1e15, self.total_energy_available * 0.1)
                
                for portal in self.active_portals.values():
                    deficit = max(0.0, portal.energy_requirement - portal.current_energy)
                    if deficit > 0:
                        allocation = (deficit / total_deficit) * available_for_distribution
                        portal.current_energy += allocation
                        self.total_energy_available -= allocation
    
    def get_portal_status(self, portal_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive status of a portal."""
        with self.portal_lock:
            portal = self.active_portals.get(portal_id)
            if not portal:
                return None
            
            return {
                'portal_id': portal.portal_id,
                'portal_type': portal.portal_type.value,
                'state': portal.state.value,
                'stability_rating': portal.stability_rating,
                'energy_level': portal.current_energy / portal.energy_requirement,
                'remaining_lifetime': portal.get_remaining_lifetime(),
                'operational': portal.is_operational(),
                'current_load': portal.current_load,
                'max_throughput': portal.max_throughput,
                'dimensional_distance': portal.calculate_dimensional_distance(),
                'origin_universe': portal.origin_coordinate.universe_id,
                'destination_universe': portal.destination_coordinate.universe_id
            }
    
    def list_active_portals(self) -> List[Dict[str, Any]]:
        """List all active portals with basic information."""
        with self.portal_lock:
            return [
                {
                    'portal_id': portal.portal_id,
                    'portal_type': portal.portal_type.value,
                    'state': portal.state.value,
                    'stability': portal.stability_rating,
                    'operational': portal.is_operational(),
                    'origin_universe': portal.origin_coordinate.universe_id,
                    'destination_universe': portal.destination_coordinate.universe_id
                }
                for portal in self.active_portals.values()
            ]
    
    def get_generator_statistics(self) -> Dict[str, Any]:
        """Get comprehensive generator statistics."""
        with self.portal_lock:
            operational_portals = sum(
                1 for p in self.active_portals.values() if p.is_operational()
            )
            
            total_energy_in_use = sum(
                p.current_energy for p in self.active_portals.values()
            )
            
            return {
                'total_portals_created': self.total_portals_created,
                'active_portals': len(self.active_portals),
                'operational_portals': operational_portals,
                'successful_transits': self.successful_transits,
                'failed_transits': self.failed_transits,
                'total_energy_available': self.total_energy_available,
                'total_energy_consumed': self.total_energy_consumed,
                'total_energy_in_use': total_energy_in_use,
                'energy_efficiency': (self.successful_transits / 
                                    max(1, self.successful_transits + self.failed_transits)),
                'generator_status': self.get_property('status', 'unknown')
            }
    
    def on_health_check(self) -> Optional[Dict[str, Any]]:
        """Health check for portal generator."""
        with self.portal_lock:
            return {
                'active_portals': len(self.active_portals),
                'operational_portals': sum(1 for p in self.active_portals.values() 
                                         if p.is_operational()),
                'energy_available': self.total_energy_available,
                'successful_transits': self.successful_transits,
                'generator_active': self.is_running
            }