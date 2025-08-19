"""
Stellar Engineer - Main interface for stellar manipulation

Provides comprehensive stellar engineering capabilities including
Dyson spheres, star lifting, stellar mergers, and megastructures.
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

class StellarType(Enum):
    """Stellar classification types"""
    MAIN_SEQUENCE = "main_sequence"
    GIANT = "giant"
    SUPERGIANT = "supergiant"
    WHITE_DWARF = "white_dwarf"
    NEUTRON_STAR = "neutron_star"
    PULSAR = "pulsar"
    MAGNETAR = "magnetar"
    BROWN_DWARF = "brown_dwarf"
    PROTOSTAR = "protostar"
    ENGINEERED = "engineered"

class StellarState(Enum):
    """Stellar operational states"""
    STABLE = "stable"
    FORMING = "forming"
    EVOLVING = "evolving"
    ENGINEERED = "engineered"
    HARVESTED = "harvested"
    MERGING = "merging"
    EXPLODING = "exploding"
    COLLAPSED = "collapsed"

@dataclass
class StellarProperties:
    """Properties of a star"""
    star_id: str
    stellar_type: StellarType
    state: StellarState
    mass: float  # Solar masses
    radius: float  # Solar radii
    luminosity: float  # Solar luminosities
    temperature: float  # Kelvin
    metallicity: float  # Z/Z_sun
    age: float  # Years
    location: Tuple[float, float, float]  # Coordinates
    velocity: Tuple[float, float, float]  # km/s
    rotation_period: float  # Days
    magnetic_field: float  # Tesla
    stellar_wind_rate: float  # M☉/year
    nuclear_fuel_remaining: float  # Fraction (0-1)
    created_at: datetime
    last_modified: datetime
    engineered_features: List[str]
    megastructures: List[str]
    energy_output: float  # Watts
    stability_index: float

@dataclass
class DysonSphereParameters:
    """Parameters for Dyson sphere construction"""
    radius: float  # AU
    construction_material: str
    collection_efficiency: float
    energy_storage_capacity: float  # Joules
    construction_time: float  # Years
    maintenance_requirements: float
    swarm_vs_shell: str  # "swarm" or "shell"

class StellarEngineer:
    """
    Main stellar engineering interface
    
    Orchestrates all stellar-scale operations including megastructure
    construction, stellar manipulation, and energy harvesting.
    """
    
    def __init__(self, cosmic_manager):
        """Initialize stellar engineer"""
        self.cosmic_manager = cosmic_manager
        self.lock = threading.RLock()
        
        # Stellar object tracking
        self.stars: Dict[str, StellarProperties] = {}
        self.construction_projects: Dict[str, Dict[str, Any]] = {}
        self.manipulation_projects: Dict[str, Dict[str, Any]] = {}
        self.megastructures: Dict[str, Dict[str, Any]] = {}
        
        # Physical constants
        self.solar_mass = 1.989e30  # kg
        self.solar_radius = 6.96e8  # m
        self.solar_luminosity = 3.828e26  # W
        self.AU = 1.496e11  # m
        self.stefan_boltzmann = 5.67e-8  # W⋅m⁻²⋅K⁻⁴
        
        # Engineering limits
        self.max_dyson_sphere_radius = 10  # AU
        self.min_harvestable_star_mass = 0.1  # Solar masses
        self.max_star_lifting_rate = 0.01  # M☉/year
        
        # Initialize subsystems
        self._initialize_subsystems()
        
        logger.info("Stellar Engineer initialized")
    
    def _initialize_subsystems(self):
        """Initialize stellar engineering subsystems"""
        from .dyson_sphere_constructor import DysonSphereConstructor
        from .star_lifting_system import StarLiftingSystem
        from .stellar_merger_controller import StellarMergerController
        from .neutron_star_engineer import NeutronStarEngineer
        from .supernova_trigger import SupernovaTrigger
        
        self.dyson_constructor = DysonSphereConstructor(self)
        self.star_lifter = StarLiftingSystem(self)
        self.merger_controller = StellarMergerController(self)
        self.neutron_engineer = NeutronStarEngineer(self)
        self.supernova_trigger = SupernovaTrigger(self)
    
    def create_dyson_sphere(self,
                          star_id: str,
                          sphere_type: str = "swarm",
                          radius: float = 1.0,
                          collection_efficiency: float = 0.9,
                          construction_material: str = "carbon_nanotubes") -> str:
        """
        Create a Dyson sphere around a star
        
        Args:
            star_id: ID of target star
            sphere_type: Type of Dyson structure (swarm, shell, ring)
            radius: Radius in AU
            collection_efficiency: Energy collection efficiency (0-1)
            construction_material: Construction material
            
        Returns:
            Dyson sphere ID
        """
        with self.lock:
            if star_id not in self.stars:
                raise ValueError(f"Star {star_id} not found")
            
            star = self.stars[star_id]
            
            # Validate parameters
            if radius > self.max_dyson_sphere_radius:
                raise ValueError(f"Dyson sphere radius {radius} AU exceeds maximum {self.max_dyson_sphere_radius} AU")
            
            if not (0 < collection_efficiency <= 1):
                raise ValueError("Collection efficiency must be between 0 and 1")
            
            # Calculate construction requirements
            sphere_surface_area = 4 * np.pi * (radius * self.AU)**2
            material_mass = self._calculate_construction_mass(sphere_surface_area, construction_material)
            construction_time = self._calculate_construction_time(material_mass, sphere_type)
            
            # Calculate energy requirements
            energy_required = self.cosmic_manager.energy_manager.calculate_energy_requirements(
                "stellar_engineering", {
                    "project_type": "dyson_sphere",
                    "radius": radius,
                    "material_mass": material_mass,
                    "construction_time": construction_time
                }
            )
            
            # Check energy availability
            if not self.cosmic_manager.energy_manager.check_energy_availability(energy_required):
                raise RuntimeError(f"Insufficient energy for Dyson sphere construction: {energy_required:.2e} GeV required")
            
            # Generate Dyson sphere ID
            dyson_id = f"dyson_{uuid.uuid4().hex[:8]}"
            
            # Create Dyson sphere parameters
            dyson_params = DysonSphereParameters(
                radius=radius,
                construction_material=construction_material,
                collection_efficiency=collection_efficiency,
                energy_storage_capacity=star.luminosity * self.solar_luminosity * 3600 * 24 * 365,  # 1 year storage
                construction_time=construction_time,
                maintenance_requirements=0.01,  # 1% per year
                swarm_vs_shell=sphere_type
            )
            
            # Execute construction
            construction_success = self.dyson_constructor.construct_dyson_sphere(
                star_id, dyson_id, dyson_params
            )
            
            if construction_success:
                # Update star properties
                star.engineered_features.append(f"dyson_sphere_{dyson_id}")
                star.megastructures.append(dyson_id)
                star.state = StellarState.ENGINEERED
                star.last_modified = datetime.now()
                
                # Store megastructure
                self.megastructures[dyson_id] = {
                    "type": "dyson_sphere",
                    "star_id": star_id,
                    "parameters": asdict(dyson_params),
                    "construction_progress": 1.0,
                    "energy_collected_total": 0.0,
                    "created_at": datetime.now(),
                    "active": True
                }
                
                logger.info(f"Dyson sphere construction completed: {dyson_id}")
                logger.info(f"Star: {star_id}, Type: {sphere_type}, Radius: {radius} AU")
                logger.info(f"Collection efficiency: {collection_efficiency}, Material: {construction_material}")
                
                return dyson_id
            else:
                raise RuntimeError("Dyson sphere construction failed")
    
    def _calculate_construction_mass(self, surface_area: float, material: str) -> float:
        """Calculate mass of construction material needed"""
        # Material thickness and density
        material_properties = {
            "carbon_nanotubes": {"thickness": 1e-6, "density": 1300},  # m, kg/m³
            "graphene": {"thickness": 3.4e-10, "density": 2200},
            "steel": {"thickness": 1e-3, "density": 7850},
            "aluminum": {"thickness": 1e-3, "density": 2700},
            "metamaterials": {"thickness": 1e-7, "density": 500}
        }
        
        props = material_properties.get(material, material_properties["steel"])
        volume = surface_area * props["thickness"]
        mass = volume * props["density"]
        
        return mass
    
    def _calculate_construction_time(self, material_mass: float, sphere_type: str) -> float:
        """Calculate construction time in years"""
        # Construction rate depends on type
        construction_rates = {
            "swarm": 1e12,  # kg/year
            "shell": 1e10,  # kg/year (slower due to structural requirements)
            "ring": 1e11    # kg/year
        }
        
        rate = construction_rates.get(sphere_type, 1e10)
        construction_time = material_mass / rate
        
        return construction_time
    
    def perform_star_lifting(self,
                           star_id: str,
                           extraction_rate: float,
                           target_mass: float,
                           method: str = "magnetic_mirror") -> str:
        """
        Perform star lifting to extract stellar material
        
        Args:
            star_id: ID of target star
            extraction_rate: Material extraction rate (M☉/year)
            target_mass: Target mass to extract (M☉)
            method: Star lifting method
            
        Returns:
            Star lifting operation ID
        """
        with self.lock:
            if star_id not in self.stars:
                raise ValueError(f"Star {star_id} not found")
            
            star = self.stars[star_id]
            
            # Validate parameters
            if extraction_rate > self.max_star_lifting_rate:
                raise ValueError(f"Extraction rate {extraction_rate} M☉/year exceeds maximum")
            
            if target_mass >= star.mass:
                raise ValueError("Cannot extract more mass than star contains")
            
            # Calculate operation time
            operation_time = target_mass / extraction_rate
            
            # Generate operation ID
            lifting_id = f"lifting_{uuid.uuid4().hex[:8]}"
            
            # Execute star lifting
            lifting_success = self.star_lifter.begin_star_lifting(
                star_id, lifting_id, extraction_rate, target_mass, method
            )
            
            if lifting_success:
                # Update star properties
                star.engineered_features.append(f"star_lifting_{lifting_id}")
                star.state = StellarState.HARVESTED
                star.stellar_wind_rate += extraction_rate  # Increased mass loss
                star.last_modified = datetime.now()
                
                logger.info(f"Star lifting initiated: {lifting_id}")
                logger.info(f"Star: {star_id}, Method: {method}")
                logger.info(f"Extraction rate: {extraction_rate} M☉/year, Target: {target_mass} M☉")
                logger.info(f"Estimated completion: {operation_time:.2f} years")
                
                return lifting_id
            else:
                raise RuntimeError("Star lifting operation failed")
    
    def merge_stars(self,
                   star_ids: List[str],
                   merger_configuration: str = "head_on",
                   target_outcome: str = "main_sequence") -> str:
        """
        Merge multiple stars
        
        Args:
            star_ids: List of star IDs to merge
            merger_configuration: Merger configuration (head_on, spiral, gradual)
            target_outcome: Desired outcome type
            
        Returns:
            ID of merged star
        """
        with self.lock:
            if len(star_ids) < 2:
                raise ValueError("Need at least 2 stars to merge")
            
            # Validate all stars exist
            stars_to_merge = []
            for star_id in star_ids:
                if star_id not in self.stars:
                    raise ValueError(f"Star {star_id} not found")
                stars_to_merge.append(self.stars[star_id])
            
            # Execute merger
            merged_star_id = self.merger_controller.execute_stellar_merger(
                star_ids, merger_configuration, target_outcome
            )
            
            if merged_star_id:
                logger.info(f"Stellar merger completed: {star_ids} -> {merged_star_id}")
                return merged_star_id
            else:
                raise RuntimeError("Stellar merger failed")
    
    def trigger_supernova(self,
                         star_id: str,
                         supernova_type: str = "core_collapse",
                         energy_direction: Optional[Tuple[float, float, float]] = None) -> bool:
        """
        Trigger controlled supernova explosion
        
        Args:
            star_id: ID of target star
            supernova_type: Type of supernova (core_collapse, thermonuclear, pair_instability)
            energy_direction: Direction to focus explosion energy (optional)
            
        Returns:
            True if successful
        """
        with self.lock:
            if star_id not in self.stars:
                raise ValueError(f"Star {star_id} not found")
            
            star = self.stars[star_id]
            
            # Check if star is suitable for supernova
            if not self._can_supernova(star):
                raise ValueError(f"Star {star_id} cannot undergo supernova")
            
            # Calculate energy release
            explosion_energy = self._calculate_supernova_energy(star.mass, supernova_type)
            
            # Execute supernova trigger
            success = self.supernova_trigger.trigger_explosion(
                star_id, supernova_type, energy_direction, explosion_energy
            )
            
            if success:
                # Update star state
                star.state = StellarState.EXPLODING
                star.engineered_features.append(f"triggered_supernova_{supernova_type}")
                star.last_modified = datetime.now()
                
                logger.info(f"Supernova triggered for star {star_id}")
                logger.info(f"Type: {supernova_type}, Energy: {explosion_energy:.2e} J")
                
                return True
            else:
                logger.error(f"Failed to trigger supernova for star {star_id}")
                return False
    
    def _can_supernova(self, star: StellarProperties) -> bool:
        """Check if star can undergo supernova"""
        # Simplified criteria
        if star.stellar_type in [StellarType.SUPERGIANT, StellarType.GIANT]:
            return star.mass >= 8.0  # Solar masses
        elif star.stellar_type == StellarType.WHITE_DWARF:
            return star.mass >= 1.4  # Chandrasekhar limit
        else:
            return star.mass >= 20.0  # Very massive stars
    
    def _calculate_supernova_energy(self, mass: float, supernova_type: str) -> float:
        """Calculate supernova explosion energy"""
        c = 2.998e8  # m/s
        solar_mass = 1.989e30  # kg
        
        if supernova_type == "core_collapse":
            # Typical core-collapse SN: ~10^44 J
            return 1e44
        elif supernova_type == "thermonuclear":
            # Type Ia SN: ~10^44 J
            return 1e44
        elif supernova_type == "pair_instability":
            # Pair-instability SN: ~10^45 J
            mass_kg = mass * solar_mass
            return 0.1 * mass_kg * c**2  # 10% mass-energy conversion
        else:
            return 1e44  # Default
    
    def create_neutron_star(self,
                          location: Tuple[float, float, float],
                          mass: float = 1.4,
                          rotation_period: float = 0.001,
                          magnetic_field: float = 1e12) -> str:
        """
        Create an engineered neutron star
        
        Args:
            location: (x, y, z) coordinates
            mass: Mass in solar masses
            rotation_period: Rotation period in seconds
            magnetic_field: Magnetic field strength in Tesla
            
        Returns:
            Neutron star ID
        """
        with self.lock:
            # Generate neutron star ID
            ns_id = f"neutronstar_{uuid.uuid4().hex[:8]}"
            
            # Execute neutron star creation
            creation_success = self.neutron_engineer.create_neutron_star(
                ns_id, location, mass, rotation_period, magnetic_field
            )
            
            if creation_success:
                logger.info(f"Neutron star created: {ns_id}")
                logger.info(f"Mass: {mass} M☉, Period: {rotation_period}s, B-field: {magnetic_field:.2e} T")
                
                return ns_id
            else:
                raise RuntimeError("Neutron star creation failed")
    
    def harvest_stellar_energy(self,
                             star_id: str,
                             harvesting_method: str = "dyson_swarm",
                             efficiency: float = 0.8) -> float:
        """
        Harvest energy from a star
        
        Args:
            star_id: ID of star to harvest from
            harvesting_method: Energy harvesting method
            efficiency: Harvesting efficiency (0-1)
            
        Returns:
            Power harvested (Watts)
        """
        with self.lock:
            if star_id not in self.stars:
                raise ValueError(f"Star {star_id} not found")
            
            star = self.stars[star_id]
            
            # Calculate harvestable power
            stellar_power = star.luminosity * self.solar_luminosity
            harvested_power = stellar_power * efficiency
            
            # Update star energy output tracking
            star.energy_output = harvested_power
            star.last_modified = datetime.now()
            
            logger.info(f"Harvesting {harvested_power:.2e} W from star {star_id}")
            logger.info(f"Method: {harvesting_method}, Efficiency: {efficiency}")
            
            return harvested_power
    
    def get_star_info(self, star_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a star"""
        with self.lock:
            if star_id not in self.stars:
                return None
            
            return asdict(self.stars[star_id])
    
    def list_stars(self,
                  stellar_type: Optional[StellarType] = None,
                  state: Optional[StellarState] = None) -> List[str]:
        """List stars with optional filtering"""
        with self.lock:
            star_ids = []
            
            for star_id, star in self.stars.items():
                if stellar_type and star.stellar_type != stellar_type:
                    continue
                if state and star.state != state:
                    continue
                star_ids.append(star_id)
            
            return star_ids
    
    def list_megastructures(self, structure_type: Optional[str] = None) -> List[str]:
        """List megastructures with optional filtering"""
        with self.lock:
            structure_ids = []
            
            for structure_id, structure in self.megastructures.items():
                if structure_type and structure["type"] != structure_type:
                    continue
                structure_ids.append(structure_id)
            
            return structure_ids
    
    def emergency_shutdown(self):
        """Emergency shutdown of stellar engineering"""
        with self.lock:
            logger.critical("Stellar Engineer emergency shutdown")
            
            # Stop all construction projects
            for project in self.construction_projects.values():
                project["status"] = "aborted"
            
            # Stop all manipulation projects
            for project in self.manipulation_projects.values():
                project["status"] = "aborted"
            
            # Shutdown subsystems
            self.dyson_constructor.emergency_shutdown()
            self.star_lifter.emergency_shutdown()
            self.merger_controller.emergency_shutdown()
            self.neutron_engineer.emergency_shutdown()
            self.supernova_trigger.emergency_shutdown()
    
    def reset_to_baseline(self):
        """Reset stellar engineer to baseline state"""
        with self.lock:
            logger.info("Resetting Stellar Engineer to baseline")
            
            # Clear all projects
            self.construction_projects.clear()
            self.manipulation_projects.clear()
            
            # Reset subsystems
            self.dyson_constructor.reset_to_baseline()
            self.star_lifter.reset_to_baseline()
            self.merger_controller.reset_to_baseline()
            self.neutron_engineer.reset_to_baseline()
            self.supernova_trigger.reset_to_baseline()
            
            # Reset star engineered features
            for star in self.stars.values():
                star.engineered_features.clear()
                star.megastructures.clear()
                if star.state == StellarState.ENGINEERED:
                    star.state = StellarState.STABLE
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of stellar engineering"""
        with self.lock:
            return {
                "total_stars": len(self.stars),
                "stars_by_type": {
                    stype.value: len([s for s in self.stars.values() if s.stellar_type == stype])
                    for stype in StellarType
                },
                "stars_by_state": {
                    state.value: len([s for s in self.stars.values() if s.state == state])
                    for state in StellarState
                },
                "total_megastructures": len(self.megastructures),
                "megastructures_by_type": {
                    "dyson_sphere": len([m for m in self.megastructures.values() if m["type"] == "dyson_sphere"]),
                    "other": len([m for m in self.megastructures.values() if m["type"] != "dyson_sphere"])
                },
                "active_construction_projects": len([p for p in self.construction_projects.values() if p.get("status") == "active"]),
                "total_energy_harvested": sum(s.energy_output for s in self.stars.values()),
                "engineered_stars": len([s for s in self.stars.values() if s.engineered_features])
            }