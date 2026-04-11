"""
Galaxy Engineer - Main interface for galaxy manipulation

Provides comprehensive galaxy engineering capabilities including
formation, destruction, merging, and structural modification.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class GalaxyType(Enum):
    """Galaxy classification types"""
    SPIRAL = "spiral"
    ELLIPTICAL = "elliptical"
    IRREGULAR = "irregular"
    DWARF = "dwarf"
    PECULIAR = "peculiar"
    ACTIVE = "active"  # AGN/Quasar
    STARBURST = "starburst"
    LENTICULAR = "lenticular"

class GalaxyState(Enum):
    """Galaxy operational states"""
    FORMING = "forming"
    STABLE = "stable"
    MERGING = "merging"
    DISRUPTING = "disrupting"
    DESTROYED = "destroyed"
    ENGINEERED = "engineered"

@dataclass
class GalaxyProperties:
    """Properties of a galaxy"""
    galaxy_id: str
    galaxy_type: GalaxyType
    state: GalaxyState
    total_mass: float  # Solar masses
    stellar_mass: float  # Solar masses
    dark_matter_mass: float  # Solar masses
    gas_mass: float  # Solar masses
    central_black_hole_mass: float  # Solar masses
    diameter: float  # Light years
    location: Tuple[float, float, float]  # Galactic coordinates
    velocity: Tuple[float, float, float]  # km/s
    metallicity: float  # Z/Z_sun
    star_formation_rate: float  # Solar masses/year
    age: float  # Years
    created_at: datetime
    engineered_features: List[str]
    stability_index: float

@dataclass
class GalaxyFormationParameters:
    """Parameters for galaxy formation"""
    initial_gas_mass: float  # Solar masses
    dark_matter_halo_mass: float  # Solar masses
    formation_redshift: float
    initial_angular_momentum: float
    collapse_time: float  # Years
    star_formation_efficiency: float
    feedback_strength: float
    environmental_density: float

class GalaxyEngineer:
    """
    Main galaxy engineering interface
    
    Orchestrates all galaxy-scale operations including formation,
    destruction, merging, and advanced structural modifications.
    """
    
    def __init__(self, cosmic_manager):
        """Initialize galaxy engineer"""
        self.cosmic_manager = cosmic_manager
        self.lock = threading.RLock()
        
        # Galaxy tracking
        self.galaxies: Dict[str, GalaxyProperties] = {}
        self.formation_projects: Dict[str, Dict[str, Any]] = {}
        self.destruction_projects: Dict[str, Dict[str, Any]] = {}
        self.merger_projects: Dict[str, Dict[str, Any]] = {}
        
        # Engineering capabilities
        self.max_galaxy_mass = 1e13  # Solar masses (largest observed)
        self.min_formation_time = 1e6  # Years
        self.max_formation_time = 1e10  # Years
        
        # Initialize subsystems
        self._initialize_subsystems()
        
        logger.info("Galaxy Engineer initialized")
    
    def _initialize_subsystems(self):
        """Initialize galaxy engineering subsystems"""
        from .galaxy_formation import GalaxyFormationEngine
        from .galaxy_destruction import GalaxyDestructionEngine
        from .galaxy_merger import GalaxyMergerEngine
        from .dark_matter_scaffolding import DarkMatterScaffolding
        from .stellar_nursery_manager import StellarNurseryManager
        
        self.formation_engine = GalaxyFormationEngine(self)
        self.destruction_engine = GalaxyDestructionEngine(self)
        self.merger_engine = GalaxyMergerEngine(self)
        self.dark_matter_scaffolding = DarkMatterScaffolding(self)
        self.stellar_nursery_manager = StellarNurseryManager(self)
    
    def create_galaxy(self,
                     galaxy_type: Union[str, GalaxyType],
                     total_mass: float,
                     location: Tuple[float, float, float],
                     formation_time: Optional[float] = None,
                     custom_parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new galaxy from scratch
        
        Args:
            galaxy_type: Type of galaxy to create
            total_mass: Total mass in solar masses
            location: (x, y, z) coordinates in meters
            formation_time: Time for formation in years (optional)
            custom_parameters: Custom formation parameters
            
        Returns:
            Galaxy ID
        """
        with self.lock:
            # Convert string to enum if needed
            if isinstance(galaxy_type, str):
                galaxy_type = GalaxyType(galaxy_type.lower())
            
            # Generate unique galaxy ID
            galaxy_id = f"galaxy_{uuid.uuid4().hex[:8]}"
            
            # Validate parameters
            if total_mass <= 0:
                raise ValueError("Galaxy mass must be positive")
            
            if total_mass > self.max_galaxy_mass:
                logger.warning(f"Galaxy mass {total_mass:.2e} exceeds typical maximum")
            
            # Set default formation time based on galaxy type
            if formation_time is None:
                formation_time = self._get_default_formation_time(galaxy_type, total_mass)
            
            # Calculate component masses
            stellar_mass, dark_matter_mass, gas_mass = self._calculate_component_masses(
                galaxy_type, total_mass
            )
            
            # Create formation parameters
            formation_params = self._create_formation_parameters(
                galaxy_type, total_mass, stellar_mass, dark_matter_mass, gas_mass, custom_parameters
            )
            
            # Calculate energy requirements
            energy_required = self.cosmic_manager.energy_manager.calculate_energy_requirements(
                "galaxy_creation", {
                    "mass": total_mass,
                    "formation_time": formation_time,
                    "galaxy_type": galaxy_type.value
                }
            )
            
            # Check energy availability
            if not self.cosmic_manager.energy_manager.check_energy_availability(energy_required):
                raise RuntimeError(f"Insufficient energy for galaxy creation: {energy_required:.2e} GeV required")
            
            # Allocate energy
            energy_allocation = self.cosmic_manager.energy_manager.allocate_energy_for_operation(
                f"galaxy_creation_{galaxy_id}", energy_required, "gravitational"
            )
            
            # Create galaxy properties
            galaxy_props = GalaxyProperties(
                galaxy_id=galaxy_id,
                galaxy_type=galaxy_type,
                state=GalaxyState.FORMING,
                total_mass=total_mass,
                stellar_mass=stellar_mass,
                dark_matter_mass=dark_matter_mass,
                gas_mass=gas_mass,
                central_black_hole_mass=self._calculate_central_bh_mass(stellar_mass),
                diameter=self._calculate_galaxy_diameter(galaxy_type, total_mass),
                location=location,
                velocity=(0.0, 0.0, 0.0),  # Initial velocity
                metallicity=0.02,  # Initial metallicity
                star_formation_rate=self._calculate_initial_sfr(galaxy_type, gas_mass),
                age=0.0,
                created_at=datetime.now(),
                engineered_features=[],
                stability_index=0.5  # Initial stability
            )
            
            # Store galaxy
            self.galaxies[galaxy_id] = galaxy_props
            
            # Create formation project
            formation_project = {
                "galaxy_id": galaxy_id,
                "formation_params": formation_params,
                "energy_allocation": energy_allocation,
                "start_time": datetime.now(),
                "estimated_completion": datetime.now(),  # Would calculate based on formation_time
                "status": "initializing",
                "progress": 0.0
            }
            
            self.formation_projects[galaxy_id] = formation_project
            
            # Execute energy extraction
            if not self.cosmic_manager.energy_manager.execute_energy_extraction(f"galaxy_creation_{galaxy_id}"):
                raise RuntimeError("Failed to extract required energy for galaxy creation")
            
            # Begin formation process
            self.formation_engine.begin_formation(galaxy_id, formation_params)
            
            logger.info(f"Galaxy creation initiated: {galaxy_id}")
            logger.info(f"Type: {galaxy_type.value}, Mass: {total_mass:.2e} M☉")
            logger.info(f"Location: {location}")
            
            return galaxy_id
    
    def _get_default_formation_time(self, galaxy_type: GalaxyType, mass: float) -> float:
        """Get default formation time based on galaxy type and mass"""
        base_times = {
            GalaxyType.DWARF: 5e8,      # 500 million years
            GalaxyType.SPIRAL: 1e9,     # 1 billion years
            GalaxyType.ELLIPTICAL: 2e9, # 2 billion years
            GalaxyType.IRREGULAR: 8e8,  # 800 million years
            GalaxyType.LENTICULAR: 1.5e9,
            GalaxyType.PECULIAR: 1.2e9,
            GalaxyType.ACTIVE: 1e9,
            GalaxyType.STARBURST: 5e8
        }
        
        base_time = base_times.get(galaxy_type, 1e9)
        
        # Scale with mass (more massive takes longer)
        mass_factor = (mass / 1e11) ** 0.3
        
        return base_time * mass_factor
    
    def _calculate_component_masses(self, galaxy_type: GalaxyType, total_mass: float) -> Tuple[float, float, float]:
        """Calculate stellar, dark matter, and gas masses"""
        # Typical mass fractions for different galaxy types
        mass_fractions = {
            GalaxyType.SPIRAL: {"stellar": 0.03, "dark_matter": 0.85, "gas": 0.12},
            GalaxyType.ELLIPTICAL: {"stellar": 0.05, "dark_matter": 0.90, "gas": 0.05},
            GalaxyType.DWARF: {"stellar": 0.01, "dark_matter": 0.95, "gas": 0.04},
            GalaxyType.IRREGULAR: {"stellar": 0.02, "dark_matter": 0.80, "gas": 0.18},
            GalaxyType.LENTICULAR: {"stellar": 0.04, "dark_matter": 0.88, "gas": 0.08},
            GalaxyType.PECULIAR: {"stellar": 0.025, "dark_matter": 0.87, "gas": 0.105},
            GalaxyType.ACTIVE: {"stellar": 0.04, "dark_matter": 0.85, "gas": 0.11},
            GalaxyType.STARBURST: {"stellar": 0.02, "dark_matter": 0.75, "gas": 0.23}
        }
        
        fractions = mass_fractions.get(galaxy_type, mass_fractions[GalaxyType.SPIRAL])
        
        stellar_mass = total_mass * fractions["stellar"]
        dark_matter_mass = total_mass * fractions["dark_matter"]
        gas_mass = total_mass * fractions["gas"]
        
        return stellar_mass, dark_matter_mass, gas_mass
    
    def _calculate_central_bh_mass(self, stellar_mass: float) -> float:
        """Calculate central black hole mass using M-sigma relation"""
        # M_bh ~ 0.002 * M_bulge (simplified)
        # For spiral galaxies, bulge is ~20% of stellar mass
        bulge_mass = stellar_mass * 0.2
        return bulge_mass * 0.002
    
    def _calculate_galaxy_diameter(self, galaxy_type: GalaxyType, total_mass: float) -> float:
        """Calculate galaxy diameter in light years"""
        # Empirical size-mass relations
        base_sizes = {  # Light years for 1e11 solar masses
            GalaxyType.SPIRAL: 100000,
            GalaxyType.ELLIPTICAL: 80000,
            GalaxyType.DWARF: 10000,
            GalaxyType.IRREGULAR: 60000,
            GalaxyType.LENTICULAR: 70000,
            GalaxyType.PECULIAR: 90000,
            GalaxyType.ACTIVE: 120000,
            GalaxyType.STARBURST: 40000
        }
        
        base_size = base_sizes.get(galaxy_type, 100000)
        
        # Scale with mass
        mass_factor = (total_mass / 1e11) ** 0.2
        
        return base_size * mass_factor
    
    def _calculate_initial_sfr(self, galaxy_type: GalaxyType, gas_mass: float) -> float:
        """Calculate initial star formation rate"""
        # SFR efficiency varies by galaxy type
        sfr_efficiencies = {
            GalaxyType.SPIRAL: 0.01,      # 1% per Gyr
            GalaxyType.ELLIPTICAL: 0.001, # 0.1% per Gyr
            GalaxyType.DWARF: 0.005,      # 0.5% per Gyr
            GalaxyType.IRREGULAR: 0.008,  # 0.8% per Gyr
            GalaxyType.LENTICULAR: 0.003,
            GalaxyType.PECULIAR: 0.015,
            GalaxyType.ACTIVE: 0.02,
            GalaxyType.STARBURST: 0.1     # 10% per Gyr
        }
        
        efficiency = sfr_efficiencies.get(galaxy_type, 0.01)
        
        # SFR = efficiency * gas_mass / (1 Gyr in years)
        return efficiency * gas_mass / 1e9
    
    def _create_formation_parameters(self,
                                   galaxy_type: GalaxyType,
                                   total_mass: float,
                                   stellar_mass: float,
                                   dark_matter_mass: float,
                                   gas_mass: float,
                                   custom_params: Optional[Dict[str, Any]]) -> GalaxyFormationParameters:
        """Create formation parameters for galaxy"""
        # Default parameters
        params = GalaxyFormationParameters(
            initial_gas_mass=gas_mass * 2,  # Start with more gas
            dark_matter_halo_mass=dark_matter_mass * 1.5,  # Larger initial halo
            formation_redshift=3.0,  # Typical formation redshift
            initial_angular_momentum=1e12,  # Typical angular momentum
            collapse_time=self._get_default_formation_time(galaxy_type, total_mass),
            star_formation_efficiency=self._get_sf_efficiency(galaxy_type),
            feedback_strength=self._get_feedback_strength(galaxy_type),
            environmental_density=1.0  # Average density
        )
        
        # Apply custom parameters if provided
        if custom_params:
            for key, value in custom_params.items():
                if hasattr(params, key):
                    setattr(params, key, value)
        
        return params
    
    def _get_sf_efficiency(self, galaxy_type: GalaxyType) -> float:
        """Get star formation efficiency for galaxy type"""
        efficiencies = {
            GalaxyType.SPIRAL: 0.02,
            GalaxyType.ELLIPTICAL: 0.05,  # Higher efficiency, faster consumption
            GalaxyType.DWARF: 0.01,
            GalaxyType.IRREGULAR: 0.015,
            GalaxyType.LENTICULAR: 0.03,
            GalaxyType.PECULIAR: 0.025,
            GalaxyType.ACTIVE: 0.04,
            GalaxyType.STARBURST: 0.1
        }
        
        return efficiencies.get(galaxy_type, 0.02)
    
    def _get_feedback_strength(self, galaxy_type: GalaxyType) -> float:
        """Get stellar feedback strength for galaxy type"""
        strengths = {
            GalaxyType.SPIRAL: 1.0,
            GalaxyType.ELLIPTICAL: 1.5,
            GalaxyType.DWARF: 2.0,  # Strong feedback in low-mass halos
            GalaxyType.IRREGULAR: 1.2,
            GalaxyType.LENTICULAR: 1.1,
            GalaxyType.PECULIAR: 1.3,
            GalaxyType.ACTIVE: 3.0,  # Very strong AGN feedback
            GalaxyType.STARBURST: 2.5
        }
        
        return strengths.get(galaxy_type, 1.0)
    
    def destroy_galaxy(self,
                      galaxy_id: str,
                      destruction_method: str = "tidal",
                      preservation_fraction: float = 0.0) -> bool:
        """
        Destroy an existing galaxy
        
        Args:
            galaxy_id: ID of galaxy to destroy
            destruction_method: Method of destruction (tidal, black_hole, supernova)
            preservation_fraction: Fraction of mass to preserve as debris
            
        Returns:
            True if successful
        """
        with self.lock:
            if galaxy_id not in self.galaxies:
                logger.error(f"Galaxy {galaxy_id} not found")
                return False
            
            galaxy = self.galaxies[galaxy_id]
            
            if galaxy.state == GalaxyState.DESTROYED:
                logger.warning(f"Galaxy {galaxy_id} already destroyed")
                return False
            
            # Calculate energy requirements for destruction
            energy_required = self.cosmic_manager.energy_manager.calculate_energy_requirements(
                "galaxy_destruction", {
                    "mass": galaxy.total_mass,
                    "method": destruction_method,
                    "preservation_fraction": preservation_fraction
                }
            )
            
            # Check energy availability
            if not self.cosmic_manager.energy_manager.check_energy_availability(energy_required):
                logger.error(f"Insufficient energy for galaxy destruction: {energy_required:.2e} GeV required")
                return False
            
            # Begin destruction process
            destruction_success = self.destruction_engine.destroy_galaxy(
                galaxy_id, destruction_method, preservation_fraction
            )
            
            if destruction_success:
                # Update galaxy state
                galaxy.state = GalaxyState.DESTROYED
                galaxy.engineered_features.append(f"destroyed_by_{destruction_method}")
                
                logger.info(f"Galaxy {galaxy_id} successfully destroyed using {destruction_method}")
                return True
            else:
                logger.error(f"Failed to destroy galaxy {galaxy_id}")
                return False
    
    def merge_galaxies(self,
                      galaxy_ids: List[str],
                      merger_type: str = "major",
                      final_galaxy_type: Optional[GalaxyType] = None) -> str:
        """
        Merge multiple galaxies into one
        
        Args:
            galaxy_ids: List of galaxy IDs to merge
            merger_type: Type of merger (major, minor, multiple)
            final_galaxy_type: Desired type of merged galaxy
            
        Returns:
            ID of merged galaxy
        """
        with self.lock:
            if len(galaxy_ids) < 2:
                raise ValueError("Need at least 2 galaxies to merge")
            
            # Validate all galaxies exist
            galaxies_to_merge = []
            for gid in galaxy_ids:
                if gid not in self.galaxies:
                    raise ValueError(f"Galaxy {gid} not found")
                galaxies_to_merge.append(self.galaxies[gid])
            
            # Calculate merged galaxy properties
            merged_galaxy_id = self.merger_engine.execute_merger(
                galaxy_ids, merger_type, final_galaxy_type
            )
            
            if merged_galaxy_id:
                logger.info(f"Successfully merged galaxies {galaxy_ids} into {merged_galaxy_id}")
                return merged_galaxy_id
            else:
                raise RuntimeError("Galaxy merger failed")
    
    def redirect_galaxy(self,
                       galaxy_id: str,
                       new_velocity: Tuple[float, float, float],
                       method: str = "gravitational_slingshot") -> bool:
        """
        Redirect a galaxy's trajectory
        
        Args:
            galaxy_id: ID of galaxy to redirect
            new_velocity: New velocity vector (km/s)
            method: Method for redirection
            
        Returns:
            True if successful
        """
        with self.lock:
            if galaxy_id not in self.galaxies:
                logger.error(f"Galaxy {galaxy_id} not found")
                return False
            
            galaxy = self.galaxies[galaxy_id]
            
            # Calculate energy required for velocity change
            velocity_change = np.array(new_velocity) - np.array(galaxy.velocity)
            delta_v_magnitude = np.linalg.norm(velocity_change)
            
            # Kinetic energy change
            # E = (1/2) * M * v^2, but for galaxy we use total mass
            mass_kg = galaxy.total_mass * 1.989e30  # Convert solar masses to kg
            velocity_ms = delta_v_magnitude * 1000   # Convert km/s to m/s
            
            energy_required_joules = 0.5 * mass_kg * velocity_ms**2
            energy_required_gev = energy_required_joules / 1.602e-10  # Convert to GeV
            
            # Check energy availability
            if not self.cosmic_manager.energy_manager.check_energy_availability(energy_required_gev):
                logger.error(f"Insufficient energy for galaxy redirection: {energy_required_gev:.2e} GeV required")
                return False
            
            # Execute redirection
            if method == "gravitational_slingshot":
                success = self._execute_gravitational_slingshot(galaxy_id, new_velocity)
            elif method == "direct_thrust":
                success = self._execute_direct_thrust(galaxy_id, new_velocity)
            elif method == "dark_energy_manipulation":
                success = self._execute_dark_energy_redirection(galaxy_id, new_velocity)
            else:
                logger.error(f"Unknown redirection method: {method}")
                return False
            
            if success:
                galaxy.velocity = new_velocity
                galaxy.engineered_features.append(f"redirected_by_{method}")
                logger.info(f"Galaxy {galaxy_id} successfully redirected to velocity {new_velocity}")
                return True
            else:
                return False
    
    def _execute_gravitational_slingshot(self, galaxy_id: str, new_velocity: Tuple[float, float, float]) -> bool:
        """Execute gravitational slingshot maneuver"""
        # Simplified implementation - in reality would involve complex orbital mechanics
        logger.info(f"Executing gravitational slingshot for galaxy {galaxy_id}")
        return True  # Assume success for now
    
    def _execute_direct_thrust(self, galaxy_id: str, new_velocity: Tuple[float, float, float]) -> bool:
        """Execute direct thrust maneuver"""
        logger.info(f"Executing direct thrust for galaxy {galaxy_id}")
        return True  # Assume success for now
    
    def _execute_dark_energy_redirection(self, galaxy_id: str, new_velocity: Tuple[float, float, float]) -> bool:
        """Execute dark energy manipulation for redirection"""
        logger.info(f"Executing dark energy redirection for galaxy {galaxy_id}")
        return True  # Assume success for now
    
    def get_galaxy_info(self, galaxy_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a galaxy"""
        with self.lock:
            if galaxy_id not in self.galaxies:
                return None
            
            return asdict(self.galaxies[galaxy_id])
    
    def list_galaxies(self, galaxy_type: Optional[GalaxyType] = None,
                     state: Optional[GalaxyState] = None) -> List[str]:
        """List galaxies with optional filtering"""
        with self.lock:
            galaxy_ids = []
            
            for gid, galaxy in self.galaxies.items():
                if galaxy_type and galaxy.galaxy_type != galaxy_type:
                    continue
                if state and galaxy.state != state:
                    continue
                galaxy_ids.append(gid)
            
            return galaxy_ids
    
    def get_formation_progress(self, galaxy_id: str) -> Optional[float]:
        """Get formation progress for a galaxy"""
        with self.lock:
            if galaxy_id in self.formation_projects:
                return self.formation_projects[galaxy_id]["progress"]
            return None
    
    def emergency_shutdown(self):
        """Emergency shutdown of galaxy engineering"""
        with self.lock:
            logger.critical("Galaxy Engineer emergency shutdown")
            
            # Stop all formation projects
            for project in self.formation_projects.values():
                project["status"] = "aborted"
            
            # Stop all destruction projects
            for project in self.destruction_projects.values():
                project["status"] = "aborted"
            
            # Stop all merger projects
            for project in self.merger_projects.values():
                project["status"] = "aborted"
            
            # Shutdown subsystems
            self.formation_engine.emergency_shutdown()
            self.destruction_engine.emergency_shutdown()
            self.merger_engine.emergency_shutdown()
            self.dark_matter_scaffolding.emergency_shutdown()
            self.stellar_nursery_manager.emergency_shutdown()
    
    def reset_to_baseline(self):
        """Reset galaxy engineer to baseline state"""
        with self.lock:
            logger.info("Resetting Galaxy Engineer to baseline")
            
            # Clear all projects
            self.formation_projects.clear()
            self.destruction_projects.clear()
            self.merger_projects.clear()
            
            # Reset subsystems
            self.formation_engine.reset_to_baseline()
            self.destruction_engine.reset_to_baseline()
            self.merger_engine.reset_to_baseline()
            self.dark_matter_scaffolding.reset_to_baseline()
            self.stellar_nursery_manager.reset_to_baseline()
            
            # Keep galaxies but reset their engineered features
            for galaxy in self.galaxies.values():
                galaxy.engineered_features.clear()
                if galaxy.state == GalaxyState.ENGINEERED:
                    galaxy.state = GalaxyState.STABLE
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of galaxy engineering"""
        with self.lock:
            return {
                "total_galaxies": len(self.galaxies),
                "galaxies_by_type": {
                    gtype.value: len([g for g in self.galaxies.values() if g.galaxy_type == gtype])
                    for gtype in GalaxyType
                },
                "galaxies_by_state": {
                    state.value: len([g for g in self.galaxies.values() if g.state == state])
                    for state in GalaxyState
                },
                "active_formation_projects": len([p for p in self.formation_projects.values() if p["status"] == "active"]),
                "active_destruction_projects": len([p for p in self.destruction_projects.values() if p["status"] == "active"]),
                "active_merger_projects": len([p for p in self.merger_projects.values() if p["status"] == "active"]),
                "total_engineered_mass": sum(g.total_mass for g in self.galaxies.values() if g.engineered_features),
            }