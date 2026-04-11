"""
Black Hole Controller - Main interface for black hole manipulation

Provides comprehensive black hole engineering capabilities including
creation, merger, evaporation, and gravitational manipulation.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import uuid
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class BlackHoleType(Enum):
    """Types of black holes"""
    STELLAR = "stellar"                    # 3-20 solar masses
    INTERMEDIATE = "intermediate"          # 100-100,000 solar masses
    SUPERMASSIVE = "supermassive"         # 10^6-10^10 solar masses
    PRIMORDIAL = "primordial"             # Any mass, formed in early universe
    EXTREMAL = "extremal"                 # Maximum rotation (a = M)
    REISSNER_NORDSTROM = "charged"        # Electrically charged
    KERR = "rotating"                     # Rotating, uncharged
    SCHWARZSCHILD = "static"              # Non-rotating, uncharged

class BlackHoleState(Enum):
    """Black hole operational states"""
    FORMING = "forming"
    STABLE = "stable"
    ACCRETING = "accreting"
    MERGING = "merging"
    EVAPORATING = "evaporating"
    ENGINEERED = "engineered"
    DESTROYED = "destroyed"

@dataclass
class BlackHoleProperties:
    """Properties of a black hole"""
    black_hole_id: str
    black_hole_type: BlackHoleType
    state: BlackHoleState
    mass: float  # Solar masses
    spin: float  # Dimensionless spin parameter (0-1)
    charge: float  # Electric charge (C)
    location: Tuple[float, float, float]  # Coordinates
    velocity: Tuple[float, float, float]  # km/s
    schwarzschild_radius: float  # meters
    event_horizon_area: float  # m^2
    surface_gravity: float  # m/s^2
    hawking_temperature: float  # Kelvin
    angular_momentum: float  # kg⋅m²⋅s⁻¹
    created_at: datetime
    last_modified: datetime
    engineered_features: List[str]
    accretion_rate: float  # M☉/year
    jet_power: float  # Watts
    stability_index: float

@dataclass
class BlackHoleCreationParameters:
    """Parameters for black hole creation"""
    target_mass: float  # Solar masses
    initial_spin: float  # 0-1
    initial_charge: float  # Coulombs
    formation_method: str  # collapse, accretion, primordial
    energy_source: str  # vacuum, matter, dark_energy
    stabilization_time: float  # Years
    environmental_effects: bool

class BlackHoleController:
    """
    Main black hole engineering interface
    
    Orchestrates all black hole operations including creation,
    manipulation, merger, and destruction.
    """
    
    def __init__(self, cosmic_manager):
        """Initialize black hole controller"""
        self.cosmic_manager = cosmic_manager
        self.lock = threading.RLock()
        
        # Black hole tracking
        self.black_holes: Dict[str, BlackHoleProperties] = {}
        self.creation_projects: Dict[str, Dict[str, Any]] = {}
        self.merger_projects: Dict[str, Dict[str, Any]] = {}
        self.manipulation_projects: Dict[str, Dict[str, Any]] = {}
        
        # Physical constants
        self.G = 6.67430e-11  # Gravitational constant
        self.c = 2.998e8      # Speed of light
        self.hbar = 1.055e-34 # Reduced Planck constant
        self.k_B = 1.381e-23  # Boltzmann constant
        self.solar_mass = 1.989e30  # kg
        
        # Engineering limits
        self.max_black_hole_mass = 1e11  # Solar masses (theoretical limit)
        self.min_black_hole_mass = 1e-8  # Solar masses (Planck mass scale)
        
        # Initialize subsystems
        self._initialize_subsystems()
        
        logger.info("Black Hole Controller initialized")
    
    def _initialize_subsystems(self):
        """Initialize black hole engineering subsystems"""
        from .black_hole_creation import BlackHoleCreationEngine
        from .event_horizon_manipulator import EventHorizonManipulator
        from .hawking_radiation_harvester import HawkingRadiationHarvester
        from .accretion_disk_engineer import AccretionDiskEngineer
        from .gravitational_wave_generator import GravitationalWaveGenerator
        
        self.creation_engine = BlackHoleCreationEngine(self)
        self.horizon_manipulator = EventHorizonManipulator(self)
        self.radiation_harvester = HawkingRadiationHarvester(self)
        self.accretion_engineer = AccretionDiskEngineer(self)
        self.wave_generator = GravitationalWaveGenerator(self)
    
    def create_black_hole(self,
                         mass: float,
                         location: Tuple[float, float, float],
                         spin: float = 0.0,
                         charge: float = 0.0,
                         black_hole_type: Optional[BlackHoleType] = None,
                         formation_method: str = "direct_collapse") -> str:
        \"\"\"
        Create a new black hole
        
        Args:
            mass: Mass in solar masses
            location: (x, y, z) coordinates
            spin: Dimensionless spin parameter (0-1)
            charge: Electric charge in Coulombs
            black_hole_type: Type of black hole (auto-determined if None)
            formation_method: Method of formation
            
        Returns:
            Black hole ID
        \"\"\"
        with self.lock:
            # Validate parameters
            if mass <= 0:
                raise ValueError("Black hole mass must be positive")
            
            if mass > self.max_black_hole_mass:
                raise ValueError(f"Mass {mass:.2e} M☉ exceeds maximum {self.max_black_hole_mass:.2e} M☉")
            
            if mass < self.min_black_hole_mass:
                raise ValueError(f"Mass {mass:.2e} M☉ below minimum {self.min_black_hole_mass:.2e} M☉")
            
            if not (0 <= spin <= 1):
                raise ValueError("Spin parameter must be between 0 and 1")
            
            # Auto-determine black hole type if not specified
            if black_hole_type is None:
                black_hole_type = self._classify_black_hole_type(mass, spin, charge)
            
            # Generate unique black hole ID
            bh_id = f"bh_{uuid.uuid4().hex[:8]}"
            
            # Calculate physical properties
            schwarzschild_radius = self._calculate_schwarzschild_radius(mass)
            event_horizon_area = self._calculate_event_horizon_area(mass, spin)
            surface_gravity = self._calculate_surface_gravity(mass, spin)
            hawking_temperature = self._calculate_hawking_temperature(mass, spin)
            angular_momentum = self._calculate_angular_momentum(mass, spin)
            
            # Calculate energy requirements
            energy_required = self.cosmic_manager.energy_manager.calculate_energy_requirements(
                "black_hole_creation", {
                    "mass": mass,
                    "formation_method": formation_method,
                    "spin": spin,
                    "charge": charge
                }
            )
            
            # Check energy availability
            if not self.cosmic_manager.energy_manager.check_energy_availability(energy_required):
                raise RuntimeError(f"Insufficient energy for black hole creation: {energy_required:.2e} GeV required")
            
            # Create black hole properties
            bh_props = BlackHoleProperties(
                black_hole_id=bh_id,
                black_hole_type=black_hole_type,
                state=BlackHoleState.FORMING,
                mass=mass,
                spin=spin,
                charge=charge,
                location=location,
                velocity=(0.0, 0.0, 0.0),
                schwarzschild_radius=schwarzschild_radius,
                event_horizon_area=event_horizon_area,
                surface_gravity=surface_gravity,
                hawking_temperature=hawking_temperature,
                angular_momentum=angular_momentum,
                created_at=datetime.now(),
                last_modified=datetime.now(),
                engineered_features=[],
                accretion_rate=0.0,
                jet_power=0.0,
                stability_index=1.0
            )
            
            # Store black hole
            self.black_holes[bh_id] = bh_props
            
            # Create formation parameters
            creation_params = BlackHoleCreationParameters(
                target_mass=mass,
                initial_spin=spin,
                initial_charge=charge,
                formation_method=formation_method,
                energy_source="vacuum_energy",
                stabilization_time=1e6,  # 1 million years
                environmental_effects=True
            )
            
            # Execute creation
            creation_success = self.creation_engine.create_black_hole(bh_id, creation_params)
            
            if creation_success:
                logger.info(f"Black hole creation initiated: {bh_id}")
                logger.info(f"Type: {black_hole_type.value}, Mass: {mass:.2e} M☉")
                logger.info(f"Schwarzschild radius: {schwarzschild_radius:.2e} m")
                logger.info(f"Hawking temperature: {hawking_temperature:.2e} K")
                
                return bh_id
            else:
                # Remove failed creation
                del self.black_holes[bh_id]
                raise RuntimeError("Black hole creation failed")
    
    def _classify_black_hole_type(self, mass: float, spin: float, charge: float) -> BlackHoleType:
        \"\"\"Classify black hole type based on properties\"\"\"
        if charge > 1e-10:  # Significant charge
            return BlackHoleType.REISSNER_NORDSTROM
        elif spin > 0.998:  # Near-extremal rotation
            return BlackHoleType.EXTREMAL
        elif spin > 0.1:  # Rotating
            return BlackHoleType.KERR
        elif mass < 100:  # Stellar mass
            return BlackHoleType.STELLAR
        elif mass < 1e5:  # Intermediate mass
            return BlackHoleType.INTERMEDIATE
        else:  # Supermassive
            return BlackHoleType.SUPERMASSIVE
    
    def _calculate_schwarzschild_radius(self, mass: float) -> float:
        \"\"\"Calculate Schwarzschild radius in meters\"\"\"
        mass_kg = mass * self.solar_mass
        return 2 * self.G * mass_kg / (self.c ** 2)
    
    def _calculate_event_horizon_area(self, mass: float, spin: float) -> float:
        \"\"\"Calculate event horizon area\"\"\"
        rs = self._calculate_schwarzschild_radius(mass)
        
        if spin == 0:
            # Schwarzschild black hole
            return 4 * np.pi * rs ** 2
        else:
            # Kerr black hole (simplified)
            # r+ = M + sqrt(M^2 - a^2) in geometric units
            # where a = J/(Mc) = spin * M
            mass_kg = mass * self.solar_mass
            a = spin * self.G * mass_kg / (self.c ** 2)  # In meters
            r_plus = rs / 2 + np.sqrt((rs / 2) ** 2 - a ** 2)
            
            # Area = 4π(r+^2 + a^2)
            return 4 * np.pi * (r_plus ** 2 + a ** 2)
    
    def _calculate_surface_gravity(self, mass: float, spin: float) -> float:
        \"\"\"Calculate surface gravity at event horizon\"\"\"
        mass_kg = mass * self.solar_mass
        rs = self._calculate_schwarzschild_radius(mass)
        
        if spin == 0:
            # Schwarzschild: κ = c^4 / (4GM)
            return self.c ** 4 / (4 * self.G * mass_kg)
        else:
            # Kerr: κ = c^4 * sqrt(M^2 - a^2) / (2GM(M + sqrt(M^2 - a^2)))
            a = spin * self.G * mass_kg / (self.c ** 2)
            M_geom = self.G * mass_kg / (self.c ** 2)  # Geometric mass
            
            discriminant = M_geom ** 2 - a ** 2
            if discriminant <= 0:
                return 0  # Extremal or naked singularity
            
            sqrt_disc = np.sqrt(discriminant)
            return (self.c ** 4 * sqrt_disc) / (2 * self.G * mass_kg * (M_geom + sqrt_disc))
    
    def _calculate_hawking_temperature(self, mass: float, spin: float) -> float:
        \"\"\"Calculate Hawking temperature\"\"\"
        surface_gravity = self._calculate_surface_gravity(mass, spin)
        return self.hbar * surface_gravity / (2 * np.pi * self.k_B * self.c)
    
    def _calculate_angular_momentum(self, mass: float, spin: float) -> float:
        \"\"\"Calculate angular momentum\"\"\"
        mass_kg = mass * self.solar_mass
        return spin * self.G * mass_kg ** 2 / self.c
    
    def merge_black_holes(self,
                         bh_ids: List[str],
                         merger_type: str = "circular_inspiral") -> str:
        \"\"\"
        Merge multiple black holes
        
        Args:
            bh_ids: List of black hole IDs to merge
            merger_type: Type of merger (circular_inspiral, parabolic, hyperbolic)
            
        Returns:
            ID of merged black hole
        \"\"\"
        with self.lock:
            if len(bh_ids) < 2:
                raise ValueError("Need at least 2 black holes to merge")
            
            # Validate all black holes exist
            black_holes_to_merge = []
            for bh_id in bh_ids:
                if bh_id not in self.black_holes:
                    raise ValueError(f"Black hole {bh_id} not found")
                black_holes_to_merge.append(self.black_holes[bh_id])
            
            # Calculate merged black hole properties
            total_mass = sum(bh.mass for bh in black_holes_to_merge)
            
            # Conservation of angular momentum (simplified)
            total_angular_momentum = sum(bh.angular_momentum for bh in black_holes_to_merge)
            merged_spin = min(1.0, total_angular_momentum / self._calculate_angular_momentum(total_mass, 1.0))
            
            # Weighted average location
            masses = [bh.mass for bh in black_holes_to_merge]
            locations = [bh.location for bh in black_holes_to_merge]
            
            merged_location = tuple(
                sum(m * l[i] for m, l in zip(masses, locations)) / total_mass
                for i in range(3)
            )
            
            # Energy radiated away as gravitational waves (simplified)
            # Typically ~5% of total mass for equal-mass merger
            radiated_energy_fraction = 0.05
            final_mass = total_mass * (1 - radiated_energy_fraction)
            
            # Create merged black hole
            merged_bh_id = self.create_black_hole(
                mass=final_mass,
                location=merged_location,
                spin=merged_spin,
                charge=0.0,  # Charge typically neutralized
                formation_method="merger"
            )
            
            # Generate gravitational waves
            gw_id = self.wave_generator.generate_merger_waves(bh_ids, merged_bh_id)
            
            # Update states of merging black holes
            for bh_id in bh_ids:
                self.black_holes[bh_id].state = BlackHoleState.MERGING
                self.black_holes[bh_id].last_modified = datetime.now()
            
            # Mark merged black hole as engineered
            merged_bh = self.black_holes[merged_bh_id]
            merged_bh.engineered_features.append(f"merged_from_{len(bh_ids)}_black_holes")
            merged_bh.state = BlackHoleState.ENGINEERED
            
            logger.info(f"Black hole merger completed: {bh_ids} -> {merged_bh_id}")
            logger.info(f"Final mass: {final_mass:.2e} M☉, Final spin: {merged_spin:.3f}")
            logger.info(f"Gravitational wave event: {gw_id}")
            
            return merged_bh_id
    
    def evaporate_black_hole(self,
                           bh_id: str,
                           acceleration_factor: float = 1.0) -> bool:
        \"\"\"
        Initiate black hole evaporation via Hawking radiation
        
        Args:
            bh_id: Black hole ID
            acceleration_factor: Factor to accelerate evaporation
            
        Returns:
            True if evaporation initiated
        \"\"\"
        with self.lock:
            if bh_id not in self.black_holes:
                logger.error(f"Black hole {bh_id} not found")
                return False
            
            bh = self.black_holes[bh_id]
            
            if bh.state == BlackHoleState.DESTROYED:
                logger.warning(f"Black hole {bh_id} already destroyed")
                return False
            
            # Calculate evaporation time
            evaporation_time = self._calculate_evaporation_time(bh.mass) / acceleration_factor
            
            # Energy required to accelerate evaporation
            if acceleration_factor > 1.0:
                energy_required = self.cosmic_manager.energy_manager.calculate_energy_requirements(
                    "black_hole_evaporation", {
                        "mass": bh.mass,
                        "acceleration_factor": acceleration_factor
                    }
                )
                
                if not self.cosmic_manager.energy_manager.check_energy_availability(energy_required):
                    logger.error(f"Insufficient energy for accelerated evaporation")
                    return False
            
            # Start evaporation process
            success = self.radiation_harvester.initiate_evaporation(bh_id, acceleration_factor)
            
            if success:
                bh.state = BlackHoleState.EVAPORATING
                bh.engineered_features.append(f"evaporation_accelerated_{acceleration_factor}x")
                bh.last_modified = datetime.now()
                
                logger.info(f"Black hole evaporation initiated for {bh_id}")
                logger.info(f"Evaporation time: {evaporation_time:.2e} years")
                
                return True
            else:
                logger.error(f"Failed to initiate evaporation for {bh_id}")
                return False
    
    def _calculate_evaporation_time(self, mass: float) -> float:
        \"\"\"Calculate Hawking evaporation time in years\"\"\"
        # t = 5120 π G^2 M^3 / (ħ c^4) seconds
        mass_kg = mass * self.solar_mass
        
        t_seconds = (5120 * np.pi * self.G**2 * mass_kg**3) / (self.hbar * self.c**4)
        t_years = t_seconds / (365.25 * 24 * 3600)
        
        return t_years
    
    def redirect_black_hole(self,
                          bh_id: str,
                          new_velocity: Tuple[float, float, float],
                          method: str = "gravitational_slingshot") -> bool:
        \"\"\"
        Redirect a black hole's trajectory
        
        Args:
            bh_id: Black hole ID
            new_velocity: New velocity vector (km/s)
            method: Redirection method
            
        Returns:
            True if successful
        \"\"\"
        with self.lock:
            if bh_id not in self.black_holes:
                logger.error(f"Black hole {bh_id} not found")
                return False
            
            bh = self.black_holes[bh_id]
            
            # Calculate energy required for velocity change
            velocity_change = np.array(new_velocity) - np.array(bh.velocity)
            delta_v_magnitude = np.linalg.norm(velocity_change)
            
            # Kinetic energy change
            mass_kg = bh.mass * self.solar_mass
            velocity_ms = delta_v_magnitude * 1000  # Convert km/s to m/s
            
            energy_required_joules = 0.5 * mass_kg * velocity_ms**2
            energy_required_gev = energy_required_joules / 1.602e-10
            
            # Check energy availability
            if not self.cosmic_manager.energy_manager.check_energy_availability(energy_required_gev):
                logger.error(f"Insufficient energy for black hole redirection: {energy_required_gev:.2e} GeV required")
                return False
            
            # Execute redirection based on method
            if method == "gravitational_slingshot":
                success = self._execute_gravitational_slingshot(bh_id, new_velocity)
            elif method == "recoil_kick":
                success = self._execute_recoil_kick(bh_id, new_velocity)
            elif method == "spacetime_manipulation":
                success = self._execute_spacetime_redirection(bh_id, new_velocity)
            else:
                logger.error(f"Unknown redirection method: {method}")
                return False
            
            if success:
                bh.velocity = new_velocity
                bh.engineered_features.append(f"redirected_by_{method}")
                bh.last_modified = datetime.now()
                
                logger.info(f"Black hole {bh_id} redirected to velocity {new_velocity}")
                return True
            else:
                return False
    
    def _execute_gravitational_slingshot(self, bh_id: str, new_velocity: Tuple[float, float, float]) -> bool:
        \"\"\"Execute gravitational slingshot maneuver\"\"\"
        # Create temporary massive object for slingshot
        logger.info(f"Executing gravitational slingshot for black hole {bh_id}")
        return True  # Simplified implementation
    
    def _execute_recoil_kick(self, bh_id: str, new_velocity: Tuple[float, float, float]) -> bool:
        \"\"\"Execute gravitational wave recoil kick\"\"\"
        # Generate asymmetric gravitational wave burst
        logger.info(f"Executing recoil kick for black hole {bh_id}")
        return True  # Simplified implementation
    
    def _execute_spacetime_redirection(self, bh_id: str, new_velocity: Tuple[float, float, float]) -> bool:
        \"\"\"Execute spacetime manipulation redirection\"\"\"
        # Manipulate local spacetime metric
        logger.info(f"Executing spacetime redirection for black hole {bh_id}")
        return True  # Simplified implementation
    
    def manipulate_event_horizon(self,
                               bh_id: str,
                               manipulation_type: str,
                               parameters: Dict[str, Any]) -> bool:
        \"\"\"
        Manipulate black hole event horizon
        
        Args:
            bh_id: Black hole ID
            manipulation_type: Type of manipulation (stretch, compress, distort)
            parameters: Manipulation parameters
            
        Returns:
            True if successful
        \"\"\"
        with self.lock:
            if bh_id not in self.black_holes:
                logger.error(f"Black hole {bh_id} not found")
                return False
            
            return self.horizon_manipulator.manipulate_horizon(bh_id, manipulation_type, parameters)
    
    def create_accretion_disk(self,
                            bh_id: str,
                            disk_mass: float,
                            disk_radius: float) -> str:
        \"\"\"Create accretion disk around black hole\"\"\"
        with self.lock:
            if bh_id not in self.black_holes:
                raise ValueError(f"Black hole {bh_id} not found")
            
            return self.accretion_engineer.create_accretion_disk(bh_id, disk_mass, disk_radius)
    
    def harvest_hawking_radiation(self,
                                bh_id: str,
                                collection_efficiency: float = 0.1) -> float:
        \"\"\"Harvest energy from Hawking radiation\"\"\"
        with self.lock:
            if bh_id not in self.black_holes:
                logger.error(f"Black hole {bh_id} not found")
                return 0.0
            
            return self.radiation_harvester.harvest_radiation(bh_id, collection_efficiency)
    
    def get_black_hole_info(self, bh_id: str) -> Optional[Dict[str, Any]]:
        \"\"\"Get information about a black hole\"\"\"
        with self.lock:
            if bh_id not in self.black_holes:
                return None
            
            return asdict(self.black_holes[bh_id])
    
    def list_black_holes(self,
                        bh_type: Optional[BlackHoleType] = None,
                        state: Optional[BlackHoleState] = None) -> List[str]:
        \"\"\"List black holes with optional filtering\"\"\"
        with self.lock:
            bh_ids = []
            
            for bh_id, bh in self.black_holes.items():
                if bh_type and bh.black_hole_type != bh_type:
                    continue
                if state and bh.state != state:
                    continue
                bh_ids.append(bh_id)
            
            return bh_ids
    
    def emergency_shutdown(self):
        \"\"\"Emergency shutdown of black hole controller\"\"\"
        with self.lock:
            logger.critical("Black Hole Controller emergency shutdown")
            
            # Stop all creation projects
            for project in self.creation_projects.values():
                project["status"] = "aborted"
            
            # Stop all merger projects
            for project in self.merger_projects.values():
                project["status"] = "aborted"
            
            # Shutdown subsystems
            self.creation_engine.emergency_shutdown()
            self.horizon_manipulator.emergency_shutdown()
            self.radiation_harvester.emergency_shutdown()
            self.accretion_engineer.emergency_shutdown()
            self.wave_generator.emergency_shutdown()
    
    def reset_to_baseline(self):
        \"\"\"Reset black hole controller to baseline\"\"\"
        with self.lock:
            logger.info("Resetting Black Hole Controller to baseline")
            
            # Clear all projects
            self.creation_projects.clear()
            self.merger_projects.clear()
            self.manipulation_projects.clear()
            
            # Reset subsystems
            self.creation_engine.reset_to_baseline()
            self.horizon_manipulator.reset_to_baseline()
            self.radiation_harvester.reset_to_baseline()
            self.accretion_engineer.reset_to_baseline()
            self.wave_generator.reset_to_baseline()
            
            # Reset black hole engineered features
            for bh in self.black_holes.values():
                bh.engineered_features.clear()
                if bh.state == BlackHoleState.ENGINEERED:
                    bh.state = BlackHoleState.STABLE
    
    def get_status(self) -> Dict[str, Any]:
        \"\"\"Get current status of black hole controller\"\"\"
        with self.lock:
            return {
                "total_black_holes": len(self.black_holes),
                "black_holes_by_type": {
                    bh_type.value: len([bh for bh in self.black_holes.values() if bh.black_hole_type == bh_type])
                    for bh_type in BlackHoleType
                },
                "black_holes_by_state": {
                    state.value: len([bh for bh in self.black_holes.values() if bh.state == state])
                    for state in BlackHoleState
                },
                "active_creation_projects": len([p for p in self.creation_projects.values() if p.get("status") == "active"]),
                "active_merger_projects": len([p for p in self.merger_projects.values() if p.get("status") == "active"]),
                "total_engineered_mass": sum(bh.mass for bh in self.black_holes.values() if bh.engineered_features),
                "total_hawking_power": sum(self._calculate_hawking_power(bh.mass) for bh in self.black_holes.values()),
            }
    
    def _calculate_hawking_power(self, mass: float) -> float:
        \"\"\"Calculate Hawking radiation power in Watts\"\"\"
        mass_kg = mass * self.solar_mass
        # P = ħ c^6 / (15360 π G^2 M^2)
        return (self.hbar * self.c**6) / (15360 * np.pi * self.G**2 * mass_kg**2)"