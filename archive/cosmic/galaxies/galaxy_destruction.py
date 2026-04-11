"""
Galaxy Destruction Engine

Implements various methods for galaxy destruction including
tidal disruption, black hole consumption, and supernova chains.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class DestructionMethod(Enum):
    """Galaxy destruction methods"""
    TIDAL_DISRUPTION = "tidal"
    BLACK_HOLE_CONSUMPTION = "black_hole"
    SUPERNOVA_CHAIN = "supernova"
    DARK_ENERGY_TEAR = "dark_energy"
    VACUUM_DECAY = "vacuum_decay"
    STELLAR_STRIPPING = "stellar_stripping"
    RAM_PRESSURE_STRIPPING = "ram_pressure"
    GRAVITATIONAL_HARASSMENT = "harassment"

@dataclass
class DestructionParameters:
    """Parameters for galaxy destruction"""
    method: DestructionMethod
    intensity: float  # 0.1 to 10.0 scale
    duration: float  # Years
    preservation_fraction: float  # 0.0 to 1.0
    energy_efficiency: float  # Energy conversion efficiency
    debris_distribution: str  # "concentrated", "dispersed", "expelled"
    target_components: List[str]  # ["stars", "gas", "dark_matter"]

@dataclass
class DestructionStage:
    """Stage in destruction process"""
    stage_name: str
    duration_fraction: float  # Fraction of total destruction time
    mass_destroyed_fraction: float  # Fraction of mass destroyed this stage
    energy_released: float  # Energy released (GeV)
    structural_changes: List[str]  # Description of changes

class GalaxyDestructionEngine:
    """
    Advanced galaxy destruction system
    
    Implements various methods for controlled and uncontrolled
    galaxy destruction with debris management.
    """
    
    def __init__(self, galaxy_engineer):
        """Initialize destruction engine"""
        self.galaxy_engineer = galaxy_engineer
        self.lock = threading.RLock()
        
        # Active destruction processes
        self.active_destructions: Dict[str, Dict[str, Any]] = {}
        
        # Destruction method configurations
        self.destruction_methods = self._initialize_destruction_methods()
        
        # Physical constants
        self.c = 2.998e8  # Speed of light (m/s)
        self.binding_energy_factor = 1e-5  # Gravitational binding energy factor
        
        logger.info("Galaxy Destruction Engine initialized")
    
    def _initialize_destruction_methods(self) -> Dict[DestructionMethod, Dict[str, Any]]:
        """Initialize destruction method configurations"""
        methods = {}
        
        # Tidal disruption
        methods[DestructionMethod.TIDAL_DISRUPTION] = {
            "efficiency": 0.3,
            "energy_requirement_factor": 0.5,
            "typical_duration": 1e8,  # Years
            "preservation_capability": 0.8,
            "debris_pattern": "tidal_streams",
            "stages": [
                DestructionStage("outer_stripping", 0.3, 0.2, 1e45, ["halo_disruption", "outer_star_loss"]),
                DestructionStage("disk_distortion", 0.4, 0.4, 2e45, ["spiral_arm_disruption", "bar_formation"]),
                DestructionStage("core_destruction", 0.2, 0.3, 1.5e45, ["nuclear_disruption", "stellar_dispersion"]),
                DestructionStage("remnant_dispersal", 0.1, 0.1, 5e44, ["final_disruption", "debris_expulsion"])
            ]
        }
        
        # Black hole consumption
        methods[DestructionMethod.BLACK_HOLE_CONSUMPTION] = {
            "efficiency": 0.1,  # Most mass goes to black hole
            "energy_requirement_factor": 0.2,
            "typical_duration": 1e7,  # Years
            "preservation_capability": 0.1,
            "debris_pattern": "accretion_disk",
            "stages": [
                DestructionStage("initial_accretion", 0.1, 0.1, 5e45, ["tidal_radius_expansion", "gas_inflow"]),
                DestructionStage("rapid_consumption", 0.7, 0.7, 3e46, ["stellar_disruption", "disk_formation"]),
                DestructionStage("cleanup_phase", 0.2, 0.2, 1e46, ["debris_accretion", "jet_expulsion"])
            ]
        }
        
        # Supernova chain reaction
        methods[DestructionMethod.SUPERNOVA_CHAIN] = {
            "efficiency": 0.8,
            "energy_requirement_factor": 1.0,
            "typical_duration": 1e6,  # Years
            "preservation_capability": 0.2,
            "debris_pattern": "explosive_shells",
            "stages": [
                DestructionStage("chain_initiation", 0.1, 0.1, 1e46, ["first_supernovae", "shock_propagation"]),
                DestructionStage("cascading_explosions", 0.6, 0.6, 5e46, ["chain_reaction", "stellar_destruction"]),
                DestructionStage("final_dispersal", 0.3, 0.3, 2e46, ["remnant_explosion", "gas_expulsion"])
            ]
        }
        
        # Dark energy manipulation
        methods[DestructionMethod.DARK_ENERGY_TEAR] = {
            "efficiency": 0.9,
            "energy_requirement_factor": 2.0,
            "typical_duration": 1e5,  # Years
            "preservation_capability": 0.05,
            "debris_pattern": "quantum_foam",
            "stages": [
                DestructionStage("spacetime_weakening", 0.2, 0.1, 1e47, ["metric_distortion", "gravitational_anomalies"]),
                DestructionStage("fabric_tearing", 0.5, 0.6, 5e47, ["spacetime_rupture", "matter_dissolution"]),
                DestructionStage("reality_collapse", 0.3, 0.3, 3e47, ["dimensional_collapse", "energy_dissipation"])
            ]
        }
        
        # Vacuum decay
        methods[DestructionMethod.VACUUM_DECAY] = {
            "efficiency": 1.0,  # Complete annihilation
            "energy_requirement_factor": 10.0,
            "typical_duration": 1e3,  # Years
            "preservation_capability": 0.0,
            "debris_pattern": "true_vacuum_bubble",
            "stages": [
                DestructionStage("false_vacuum_nucleation", 0.1, 0.0, 1e50, ["bubble_nucleation", "vacuum_transition"]),
                DestructionStage("bubble_expansion", 0.8, 0.9, 1e52, ["light_speed_expansion", "matter_annihilation"]),
                DestructionStage("true_vacuum_state", 0.1, 0.1, 1e51, ["vacuum_stabilization", "energy_release"])
            ]
        }
        
        return methods
    
    def destroy_galaxy(self,
                      galaxy_id: str,
                      method: str,
                      preservation_fraction: float = 0.0,
                      custom_params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute galaxy destruction
        
        Args:
            galaxy_id: ID of galaxy to destroy
            method: Destruction method
            preservation_fraction: Fraction of mass to preserve
            custom_params: Custom destruction parameters
            
        Returns:
            True if destruction initiated successfully
        """
        with self.lock:
            if galaxy_id not in self.galaxy_engineer.galaxies:
                logger.error(f"Galaxy {galaxy_id} not found")
                return False
            
            galaxy = self.galaxy_engineer.galaxies[galaxy_id]
            
            if galaxy.state.name == "DESTROYED":
                logger.warning(f"Galaxy {galaxy_id} already destroyed")
                return False
            
            # Convert method string to enum
            try:
                destruction_method = DestructionMethod(method)
            except ValueError:
                logger.error(f"Unknown destruction method: {method}")
                return False
            
            # Get method configuration
            method_config = self.destruction_methods[destruction_method]
            
            # Create destruction parameters
            destruction_params = self._create_destruction_parameters(
                destruction_method, galaxy, preservation_fraction, custom_params
            )
            
            # Calculate energy requirements
            energy_required = self._calculate_destruction_energy(
                galaxy, destruction_method, destruction_params
            )
            
            # Check energy availability
            if not self.galaxy_engineer.cosmic_manager.energy_manager.check_energy_availability(energy_required):
                logger.error(f"Insufficient energy for galaxy destruction: {energy_required:.2e} GeV required")
                return False
            
            # Initialize destruction state
            destruction_state = {
                "galaxy_id": galaxy_id,
                "method": destruction_method,
                "parameters": destruction_params,
                "stages": method_config["stages"].copy(),
                "current_stage": 0,
                "start_time": datetime.now(),
                "stage_start_time": datetime.now(),
                "total_progress": 0.0,
                "mass_destroyed": 0.0,
                "energy_released": 0.0,
                "status": "active",
                "debris_created": []
            }
            
            self.active_destructions[galaxy_id] = destruction_state
            
            # Update galaxy state
            galaxy.state = galaxy.state.__class__.DISRUPTING
            
            # Start destruction thread
            destruction_thread = threading.Thread(
                target=self._run_destruction_simulation,
                args=(galaxy_id,),
                daemon=True
            )
            destruction_thread.start()
            
            logger.info(f"Galaxy destruction initiated for {galaxy_id} using {method}")
            return True
    
    def _create_destruction_parameters(self,
                                     method: DestructionMethod,
                                     galaxy,
                                     preservation_fraction: float,
                                     custom_params: Optional[Dict[str, Any]]) -> DestructionParameters:
        """Create destruction parameters"""
        method_config = self.destruction_methods[method]
        
        params = DestructionParameters(
            method=method,
            intensity=1.0,  # Default intensity
            duration=method_config["typical_duration"],
            preservation_fraction=min(preservation_fraction, method_config["preservation_capability"]),
            energy_efficiency=method_config["efficiency"],
            debris_distribution=method_config["debris_pattern"],
            target_components=["stars", "gas", "dark_matter"]
        )
        
        # Apply custom parameters
        if custom_params:
            for key, value in custom_params.items():
                if hasattr(params, key):
                    setattr(params, key, value)
        
        return params
    
    def _calculate_destruction_energy(self,
                                    galaxy,
                                    method: DestructionMethod,
                                    params: DestructionParameters) -> float:
        """Calculate energy required for destruction"""
        # Base energy is gravitational binding energy
        G = 6.67430e-11  # Gravitational constant
        M = galaxy.total_mass * 1.989e30  # Convert to kg
        R = galaxy.diameter * 9.461e15 / 2  # Convert light-years to meters radius
        
        # Gravitational binding energy (simplified)
        binding_energy_joules = 3 * G * M**2 / (5 * R)
        
        # Convert to GeV
        binding_energy_gev = binding_energy_joules / 1.602e-10
        
        # Apply method-specific energy factor
        method_config = self.destruction_methods[method]
        energy_factor = method_config["energy_requirement_factor"]
        
        # Apply intensity factor
        intensity_factor = params.intensity ** 2
        
        # Apply efficiency factor (higher efficiency = less energy needed)
        efficiency_factor = 1.0 / params.energy_efficiency
        
        total_energy = binding_energy_gev * energy_factor * intensity_factor * efficiency_factor
        
        return total_energy
    
    def _run_destruction_simulation(self, galaxy_id: str):
        """Run the destruction simulation"""
        try:
            while True:
                with self.lock:
                    if galaxy_id not in self.active_destructions:
                        break
                    
                    destruction_state = self.active_destructions[galaxy_id]
                    
                    if destruction_state["status"] != "active":
                        break
                
                # Process current destruction stage
                self._process_destruction_stage(galaxy_id)
                
                # Update progress
                self._update_destruction_progress(galaxy_id)
                
                # Check if destruction is complete
                if self._is_destruction_complete(galaxy_id):
                    self._complete_destruction(galaxy_id)
                    break
                
                # Sleep for simulation timestep
                time.sleep(0.1)  # 100ms timestep
                
        except Exception as e:
            logger.error(f"Error in destruction simulation for {galaxy_id}: {e}")
            with self.lock:
                if galaxy_id in self.active_destructions:
                    self.active_destructions[galaxy_id]["status"] = "error"
    
    def _process_destruction_stage(self, galaxy_id: str):
        """Process current destruction stage"""
        with self.lock:
            destruction_state = self.active_destructions[galaxy_id]
            galaxy = self.galaxy_engineer.galaxies[galaxy_id]
            current_stage_idx = destruction_state["current_stage"]
            
            if current_stage_idx >= len(destruction_state["stages"]):
                return  # All stages complete
            
            stage = destruction_state["stages"][current_stage_idx]
            params = destruction_state["parameters"]
            
            # Calculate time elapsed in current stage
            now = datetime.now()
            stage_elapsed = (now - destruction_state["stage_start_time"]).total_seconds()
            stage_duration_seconds = stage.duration_fraction * params.duration * 365.25 * 24 * 3600
            
            # Scale time for simulation
            time_scale_factor = 1e-6  # 1 microsecond = 1 year
            scaled_stage_duration = stage_duration_seconds * time_scale_factor
            
            if stage_elapsed >= scaled_stage_duration:
                # Stage complete
                self._complete_destruction_stage(galaxy_id)
                return
            
            # Update destruction progress within stage
            stage_progress = stage_elapsed / scaled_stage_duration if scaled_stage_duration > 0 else 1.0
            
            # Calculate mass destruction for this timestep
            dt_fraction = 0.1 * time_scale_factor / (365.25 * 24 * 3600) / params.duration
            mass_destroyed_this_step = stage.mass_destroyed_fraction * galaxy.total_mass * dt_fraction
            
            # Apply destruction to galaxy components
            self._apply_mass_destruction(galaxy, mass_destroyed_this_step, params)
            
            # Update destruction state
            destruction_state["mass_destroyed"] += mass_destroyed_this_step
            destruction_state["energy_released"] += stage.energy_released * dt_fraction
            
            # Create debris if specified
            if stage_progress > 0.5 and galaxy_id not in [d["source_galaxy"] for d in destruction_state["debris_created"]]:
                debris = self._create_debris(galaxy, stage, params)
                destruction_state["debris_created"].append(debris)
    
    def _apply_mass_destruction(self, galaxy, mass_destroyed: float, params: DestructionParameters):
        """Apply mass destruction to galaxy components"""
        # Distribute destruction across components based on target_components
        if "stars" in params.target_components:
            stellar_destruction = mass_destroyed * 0.4
            galaxy.stellar_mass = max(0, galaxy.stellar_mass - stellar_destruction)
        
        if "gas" in params.target_components:
            gas_destruction = mass_destroyed * 0.3
            galaxy.gas_mass = max(0, galaxy.gas_mass - gas_destruction)
        
        if "dark_matter" in params.target_components:
            dm_destruction = mass_destroyed * 0.3
            galaxy.dark_matter_mass = max(0, galaxy.dark_matter_mass - dm_destruction)
        
        # Update total mass
        galaxy.total_mass = galaxy.stellar_mass + galaxy.gas_mass + galaxy.dark_matter_mass
        
        # Update other properties
        galaxy.star_formation_rate *= 0.99  # Gradual decline
        galaxy.stability_index *= 0.98  # Decreasing stability
    
    def _create_debris(self, galaxy, stage: DestructionStage, params: DestructionParameters) -> Dict[str, Any]:
        """Create debris from destruction process"""
        debris = {
            "source_galaxy": galaxy.galaxy_id,
            "debris_type": params.debris_distribution,
            "mass": galaxy.total_mass * params.preservation_fraction * 0.1,  # 10% of preserved mass
            "location": galaxy.location,
            "velocity": tuple(np.array(galaxy.velocity) + np.random.normal(0, 100, 3)),  # Add velocity scatter
            "created_at": datetime.now(),
            "stage": stage.stage_name
        }
        
        return debris
    
    def _complete_destruction_stage(self, galaxy_id: str):
        """Complete current destruction stage"""
        with self.lock:
            destruction_state = self.active_destructions[galaxy_id]
            current_stage_idx = destruction_state["current_stage"]
            
            stage = destruction_state["stages"][current_stage_idx]
            
            logger.info(f"Galaxy {galaxy_id} completed destruction stage: {stage.stage_name}")
            
            # Move to next stage
            destruction_state["current_stage"] += 1
            destruction_state["stage_start_time"] = datetime.now()
    
    def _update_destruction_progress(self, galaxy_id: str):
        """Update destruction progress"""
        with self.lock:
            destruction_state = self.active_destructions[galaxy_id]
            stages = destruction_state["stages"]
            
            completed_stages = destruction_state["current_stage"]
            
            if destruction_state["current_stage"] < len(stages):
                # Add partial progress for current stage
                current_stage = stages[destruction_state["current_stage"]]
                stage_elapsed = (datetime.now() - destruction_state["stage_start_time"]).total_seconds()
                
                params = destruction_state["parameters"]
                stage_duration_seconds = current_stage.duration_fraction * params.duration * 365.25 * 24 * 3600
                time_scale_factor = 1e-6
                scaled_duration = stage_duration_seconds * time_scale_factor
                
                stage_progress = min(1.0, stage_elapsed / scaled_duration) if scaled_duration > 0 else 1.0
                
                total_progress = (completed_stages + stage_progress) / len(stages)
            else:
                total_progress = 1.0
            
            destruction_state["total_progress"] = total_progress
    
    def _is_destruction_complete(self, galaxy_id: str) -> bool:
        """Check if destruction is complete"""
        with self.lock:
            destruction_state = self.active_destructions[galaxy_id]
            return destruction_state["total_progress"] >= 1.0
    
    def _complete_destruction(self, galaxy_id: str):
        """Complete galaxy destruction"""
        with self.lock:
            destruction_state = self.active_destructions[galaxy_id]
            galaxy = self.galaxy_engineer.galaxies[galaxy_id]
            params = destruction_state["parameters"]
            
            # Apply final destruction
            preserved_mass = galaxy.total_mass * params.preservation_fraction
            
            galaxy.stellar_mass = preserved_mass * 0.3
            galaxy.gas_mass = preserved_mass * 0.2
            galaxy.dark_matter_mass = preserved_mass * 0.5
            galaxy.total_mass = preserved_mass
            
            # Update galaxy state
            galaxy.state = galaxy.state.__class__.DESTROYED
            galaxy.star_formation_rate = 0.0
            galaxy.stability_index = 0.0
            
            # Mark destruction as complete
            destruction_state["status"] = "completed"
            destruction_state["completion_time"] = datetime.now()
            
            logger.info(f"Galaxy destruction completed for {galaxy_id}")
            logger.info(f"Preserved mass: {preserved_mass:.2e} M☉")
            logger.info(f"Debris created: {len(destruction_state['debris_created'])} objects")
    
    def get_destruction_status(self, galaxy_id: str) -> Optional[Dict[str, Any]]:
        """Get destruction status"""
        with self.lock:
            if galaxy_id not in self.active_destructions:
                return None
            
            destruction_state = self.active_destructions[galaxy_id]
            current_stage_idx = destruction_state["current_stage"]
            
            status = {
                "galaxy_id": galaxy_id,
                "method": destruction_state["method"].value,
                "status": destruction_state["status"],
                "total_progress": destruction_state["total_progress"],
                "current_stage_index": current_stage_idx,
                "current_stage_name": "",
                "mass_destroyed": destruction_state["mass_destroyed"],
                "energy_released": destruction_state["energy_released"],
                "debris_count": len(destruction_state["debris_created"]),
                "start_time": destruction_state["start_time"]
            }
            
            if current_stage_idx < len(destruction_state["stages"]):
                status["current_stage_name"] = destruction_state["stages"][current_stage_idx].stage_name
            
            return status
    
    def abort_destruction(self, galaxy_id: str) -> bool:
        """Abort galaxy destruction"""
        with self.lock:
            if galaxy_id not in self.active_destructions:
                return False
            
            destruction_state = self.active_destructions[galaxy_id]
            destruction_state["status"] = "aborted"
            
            # Update galaxy state
            galaxy = self.galaxy_engineer.galaxies[galaxy_id]
            galaxy.state = galaxy.state.__class__.STABLE
            
            logger.info(f"Galaxy destruction aborted for {galaxy_id}")
            return True
    
    def emergency_shutdown(self):
        """Emergency shutdown of destruction engine"""
        with self.lock:
            logger.critical("Galaxy Destruction Engine emergency shutdown")
            
            # Abort all active destructions
            for galaxy_id in list(self.active_destructions.keys()):
                self.abort_destruction(galaxy_id)
    
    def reset_to_baseline(self):
        """Reset destruction engine to baseline"""
        with self.lock:
            logger.info("Resetting Galaxy Destruction Engine to baseline")
            self.active_destructions.clear()