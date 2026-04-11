"""
Galaxy Formation Engine

Handles the complex process of galaxy formation from initial
dark matter halos through star formation and structural evolution.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import threading
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class FormationStage:
    """Represents a stage in galaxy formation"""
    stage_name: str
    duration: float  # Years
    gas_fraction: float
    star_formation_rate: float
    stellar_mass_formed: float
    dark_matter_accretion: float
    feedback_strength: float
    completed: bool = False

class GalaxyFormationEngine:
    """
    Advanced galaxy formation simulation engine
    
    Simulates the formation process from initial dark matter collapse
    through hierarchical assembly and stellar population synthesis.
    """
    
    def __init__(self, galaxy_engineer):
        """Initialize formation engine"""
        self.galaxy_engineer = galaxy_engineer
        self.lock = threading.RLock()
        
        # Active formation simulations
        self.active_formations: Dict[str, Dict[str, Any]] = {}
        
        # Formation stage definitions
        self.formation_stages = self._define_formation_stages()
        
        # Physical parameters
        self.baryon_fraction = 0.15  # Cosmic baryon fraction
        self.cooling_efficiency = 0.1
        self.feedback_efficiency = 0.01
        
        logger.info("Galaxy Formation Engine initialized")
    
    def _define_formation_stages(self) -> Dict[str, List[FormationStage]]:
        """Define formation stages for different galaxy types"""
        stages = {}
        
        # Spiral galaxy formation stages
        stages["spiral"] = [
            FormationStage("dark_matter_collapse", 1e8, 0.8, 0.0, 0.0, 1.0, 0.0),
            FormationStage("gas_accretion", 2e8, 0.7, 0.1, 0.05, 0.8, 0.5),
            FormationStage("disk_formation", 3e8, 0.6, 0.5, 0.15, 0.6, 1.0),
            FormationStage("spiral_structure", 2e8, 0.5, 1.0, 0.25, 0.4, 1.2),
            FormationStage("steady_evolution", 4e8, 0.4, 0.8, 0.35, 0.2, 1.0),
            FormationStage("maturation", 0, 0.3, 0.3, 0.2, 0.1, 0.8)
        ]
        
        # Elliptical galaxy formation stages
        stages["elliptical"] = [
            FormationStage("dark_matter_collapse", 5e7, 0.8, 0.0, 0.0, 1.0, 0.0),
            FormationStage("rapid_star_formation", 1e8, 0.6, 5.0, 0.4, 0.5, 2.0),
            FormationStage("merger_activity", 2e8, 0.4, 2.0, 0.3, 0.8, 3.0),
            FormationStage("gas_expulsion", 1e8, 0.2, 0.5, 0.15, 0.2, 5.0),
            FormationStage("passive_evolution", 5e8, 0.1, 0.1, 0.1, 0.1, 1.0),
            FormationStage("maturation", 0, 0.05, 0.05, 0.05, 0.05, 0.5)
        ]
        
        # Dwarf galaxy formation stages
        stages["dwarf"] = [
            FormationStage("dark_matter_assembly", 2e8, 0.9, 0.0, 0.0, 1.0, 0.0),
            FormationStage("delayed_star_formation", 3e8, 0.8, 0.05, 0.1, 0.3, 2.0),
            FormationStage("episodic_bursts", 4e8, 0.7, 0.2, 0.2, 0.2, 3.0),
            FormationStage("continuous_formation", 3e8, 0.6, 0.1, 0.3, 0.1, 2.0),
            FormationStage("gradual_evolution", 0, 0.5, 0.05, 0.4, 0.05, 1.5)
        ]
        
        # Irregular galaxy formation stages
        stages["irregular"] = [
            FormationStage("chaotic_assembly", 3e8, 0.85, 0.0, 0.0, 1.2, 0.0),
            FormationStage("turbulent_star_formation", 4e8, 0.75, 0.3, 0.2, 0.8, 1.5),
            FormationStage("environmental_effects", 3e8, 0.65, 0.4, 0.25, 0.6, 2.0),
            FormationStage("ongoing_evolution", 0, 0.55, 0.2, 0.3, 0.4, 1.8)
        ]
        
        return stages
    
    def begin_formation(self, galaxy_id: str, formation_params) -> bool:
        """
        Begin galaxy formation process
        
        Args:
            galaxy_id: ID of galaxy to form
            formation_params: Formation parameters
            
        Returns:
            True if formation started successfully
        """
        with self.lock:
            if galaxy_id in self.active_formations:
                logger.warning(f"Formation already active for galaxy {galaxy_id}")
                return False
            
            galaxy = self.galaxy_engineer.galaxies[galaxy_id]
            
            # Get formation stages for galaxy type
            galaxy_type_str = galaxy.galaxy_type.value
            if galaxy_type_str not in self.formation_stages:
                galaxy_type_str = "spiral"  # Default
            
            stages = self.formation_stages[galaxy_type_str].copy()
            
            # Initialize formation state
            formation_state = {
                "galaxy_id": galaxy_id,
                "formation_params": formation_params,
                "stages": stages,
                "current_stage": 0,
                "start_time": datetime.now(),
                "stage_start_time": datetime.now(),
                "total_progress": 0.0,
                "current_gas_mass": formation_params.initial_gas_mass,
                "current_stellar_mass": 0.0,
                "current_dark_matter_mass": formation_params.dark_matter_halo_mass,
                "status": "active"
            }
            
            self.active_formations[galaxy_id] = formation_state
            
            # Start formation thread
            formation_thread = threading.Thread(
                target=self._run_formation_simulation,
                args=(galaxy_id,),
                daemon=True
            )
            formation_thread.start()
            
            logger.info(f"Galaxy formation started for {galaxy_id}")
            return True
    
    def _run_formation_simulation(self, galaxy_id: str):
        """Run the galaxy formation simulation"""
        try:
            with self.lock:
                formation_state = self.active_formations[galaxy_id]
                galaxy = self.galaxy_engineer.galaxies[galaxy_id]
            
            while formation_state["status"] == "active":
                # Process current stage
                self._process_formation_stage(galaxy_id)
                
                # Update progress
                self._update_formation_progress(galaxy_id)
                
                # Check if formation is complete
                if self._is_formation_complete(galaxy_id):
                    self._complete_formation(galaxy_id)
                    break
                
                # Sleep for simulation timestep
                time.sleep(0.1)  # 100ms timestep
                
        except Exception as e:
            logger.error(f"Error in formation simulation for {galaxy_id}: {e}")
            with self.lock:
                if galaxy_id in self.active_formations:
                    self.active_formations[galaxy_id]["status"] = "error"
    
    def _process_formation_stage(self, galaxy_id: str):
        """Process the current formation stage"""
        with self.lock:
            formation_state = self.active_formations[galaxy_id]
            galaxy = self.galaxy_engineer.galaxies[galaxy_id]
            current_stage_idx = formation_state["current_stage"]
            
            if current_stage_idx >= len(formation_state["stages"]):
                return  # All stages complete
            
            stage = formation_state["stages"][current_stage_idx]
            formation_params = formation_state["formation_params"]
            
            # Calculate time elapsed in current stage
            now = datetime.now()
            stage_elapsed = (now - formation_state["stage_start_time"]).total_seconds()
            stage_duration_seconds = stage.duration * 365.25 * 24 * 3600  # Convert years to seconds
            
            # For simulation, scale time dramatically
            time_scale_factor = 1e-6  # 1 microsecond = 1 year
            scaled_stage_duration = stage_duration_seconds * time_scale_factor
            
            if stage_elapsed >= scaled_stage_duration or stage.duration == 0:
                # Stage complete, move to next
                self._complete_current_stage(galaxy_id)
                return
            
            # Update galaxy properties based on current stage
            stage_progress = stage_elapsed / scaled_stage_duration if scaled_stage_duration > 0 else 1.0
            
            # Star formation
            if stage.star_formation_rate > 0:
                dt_years = 0.1 * time_scale_factor / (365.25 * 24 * 3600)  # Timestep in years
                stars_formed = stage.star_formation_rate * dt_years
                
                # Check gas availability
                if formation_state["current_gas_mass"] >= stars_formed:
                    formation_state["current_gas_mass"] -= stars_formed
                    formation_state["current_stellar_mass"] += stars_formed
                    
                    # Update galaxy properties
                    galaxy.stellar_mass = formation_state["current_stellar_mass"]
                    galaxy.gas_mass = formation_state["current_gas_mass"]
                    galaxy.star_formation_rate = stage.star_formation_rate
            
            # Dark matter accretion
            if stage.dark_matter_accretion > 0:
                dt_years = 0.1 * time_scale_factor / (365.25 * 24 * 3600)
                dm_accreted = stage.dark_matter_accretion * formation_params.dark_matter_halo_mass * 0.001 * dt_years
                formation_state["current_dark_matter_mass"] += dm_accreted
                galaxy.dark_matter_mass = formation_state["current_dark_matter_mass"]
            
            # Update total mass
            galaxy.total_mass = galaxy.stellar_mass + galaxy.gas_mass + galaxy.dark_matter_mass
            
            # Update age
            galaxy.age += 0.1 * time_scale_factor / (365.25 * 24 * 3600)  # Convert to years
    
    def _complete_current_stage(self, galaxy_id: str):
        """Complete the current formation stage and move to next"""
        with self.lock:
            formation_state = self.active_formations[galaxy_id]
            current_stage_idx = formation_state["current_stage"]
            
            if current_stage_idx < len(formation_state["stages"]):
                stage = formation_state["stages"][current_stage_idx]
                stage.completed = True
                
                logger.info(f"Galaxy {galaxy_id} completed formation stage: {stage.stage_name}")
                
                # Move to next stage
                formation_state["current_stage"] += 1
                formation_state["stage_start_time"] = datetime.now()
    
    def _update_formation_progress(self, galaxy_id: str):
        """Update overall formation progress"""
        with self.lock:
            formation_state = self.active_formations[galaxy_id]
            stages = formation_state["stages"]
            
            completed_stages = sum(1 for stage in stages if stage.completed)
            current_stage_idx = formation_state["current_stage"]
            
            if current_stage_idx < len(stages):
                # Add partial progress for current stage
                current_stage = stages[current_stage_idx]
                stage_elapsed = (datetime.now() - formation_state["stage_start_time"]).total_seconds()
                
                if current_stage.duration > 0:
                    time_scale_factor = 1e-6
                    stage_duration_seconds = current_stage.duration * 365.25 * 24 * 3600 * time_scale_factor
                    stage_progress = min(1.0, stage_elapsed / stage_duration_seconds)
                else:
                    stage_progress = 1.0
                
                total_progress = (completed_stages + stage_progress) / len(stages)
            else:
                total_progress = 1.0
            
            formation_state["total_progress"] = total_progress
            
            # Update project progress in galaxy engineer
            if galaxy_id in self.galaxy_engineer.formation_projects:
                self.galaxy_engineer.formation_projects[galaxy_id]["progress"] = total_progress
    
    def _is_formation_complete(self, galaxy_id: str) -> bool:
        """Check if galaxy formation is complete"""
        with self.lock:
            formation_state = self.active_formations[galaxy_id]
            return formation_state["total_progress"] >= 1.0
    
    def _complete_formation(self, galaxy_id: str):
        """Complete galaxy formation process"""
        with self.lock:
            formation_state = self.active_formations[galaxy_id]
            galaxy = self.galaxy_engineer.galaxies[galaxy_id]
            
            # Update galaxy state
            galaxy.state = galaxy.state.__class__.STABLE
            galaxy.stability_index = 0.9  # High stability after formation
            
            # Final property calculations
            galaxy.metallicity = self._calculate_final_metallicity(galaxy)
            galaxy.star_formation_rate = self._calculate_final_sfr(galaxy)
            
            # Mark formation as complete
            formation_state["status"] = "completed"
            formation_state["completion_time"] = datetime.now()
            
            # Update project status
            if galaxy_id in self.galaxy_engineer.formation_projects:
                project = self.galaxy_engineer.formation_projects[galaxy_id]
                project["status"] = "completed"
                project["progress"] = 1.0
                project["completion_time"] = datetime.now()
            
            logger.info(f"Galaxy formation completed for {galaxy_id}")
            logger.info(f"Final mass: {galaxy.total_mass:.2e} M☉")
            logger.info(f"Stellar mass: {galaxy.stellar_mass:.2e} M☉")
            logger.info(f"Formation time: {galaxy.age:.2e} years")
    
    def _calculate_final_metallicity(self, galaxy) -> float:
        """Calculate final metallicity based on star formation history"""
        # Simplified metallicity evolution
        # More massive galaxies retain more metals
        mass_factor = np.log10(galaxy.stellar_mass / 1e10)
        base_metallicity = 0.02  # Solar metallicity
        
        # Apply mass-metallicity relation
        metallicity = base_metallicity * (1 + 0.5 * mass_factor)
        
        return max(0.001, metallicity)  # Minimum metallicity
    
    def _calculate_final_sfr(self, galaxy) -> float:
        """Calculate final star formation rate"""
        # SFR depends on gas reservoir and galaxy type
        if galaxy.gas_mass <= 0:
            return 0.0
        
        # Kennicutt-Schmidt relation (simplified)
        gas_surface_density = galaxy.gas_mass / (np.pi * (galaxy.diameter / 2)**2)
        sfr = 2.5e-4 * (gas_surface_density / 10)**1.4  # M☉/yr
        
        return sfr
    
    def get_formation_status(self, galaxy_id: str) -> Optional[Dict[str, Any]]:
        """Get current formation status"""
        with self.lock:
            if galaxy_id not in self.active_formations:
                return None
            
            formation_state = self.active_formations[galaxy_id]
            current_stage_idx = formation_state["current_stage"]
            
            status = {
                "galaxy_id": galaxy_id,
                "status": formation_state["status"],
                "total_progress": formation_state["total_progress"],
                "current_stage_index": current_stage_idx,
                "current_stage_name": "",
                "stages_completed": sum(1 for stage in formation_state["stages"] if stage.completed),
                "total_stages": len(formation_state["stages"]),
                "start_time": formation_state["start_time"],
                "current_gas_mass": formation_state["current_gas_mass"],
                "current_stellar_mass": formation_state["current_stellar_mass"],
                "current_dark_matter_mass": formation_state["current_dark_matter_mass"]
            }
            
            if current_stage_idx < len(formation_state["stages"]):
                status["current_stage_name"] = formation_state["stages"][current_stage_idx].stage_name
            
            return status
    
    def abort_formation(self, galaxy_id: str) -> bool:
        """Abort galaxy formation process"""
        with self.lock:
            if galaxy_id not in self.active_formations:
                return False
            
            formation_state = self.active_formations[galaxy_id]
            formation_state["status"] = "aborted"
            
            # Update galaxy state
            galaxy = self.galaxy_engineer.galaxies[galaxy_id]
            galaxy.state = galaxy.state.__class__.DISRUPTING
            
            logger.info(f"Galaxy formation aborted for {galaxy_id}")
            return True
    
    def emergency_shutdown(self):
        """Emergency shutdown of formation engine"""
        with self.lock:
            logger.critical("Galaxy Formation Engine emergency shutdown")
            
            # Abort all active formations
            for galaxy_id in list(self.active_formations.keys()):
                self.abort_formation(galaxy_id)
    
    def reset_to_baseline(self):
        """Reset formation engine to baseline"""
        with self.lock:
            logger.info("Resetting Galaxy Formation Engine to baseline")
            
            # Clear all active formations
            self.active_formations.clear()