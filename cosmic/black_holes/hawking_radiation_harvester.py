"""
Hawking Radiation Harvester

Harvests energy from black hole Hawking radiation and
manages controlled evaporation processes.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import threading

logger = logging.getLogger(__name__)

class HawkingRadiationHarvester:
    """Hawking radiation energy harvesting system"""
    
    def __init__(self, black_hole_controller):
        """Initialize radiation harvester"""
        self.bh_controller = black_hole_controller
        self.lock = threading.RLock()
        
        # Harvesting operations
        self.active_harvesting: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Hawking Radiation Harvester initialized")
    
    def harvest_radiation(self, bh_id: str, efficiency: float = 0.1) -> float:
        """Harvest energy from Hawking radiation"""
        with self.lock:
            if bh_id not in self.bh_controller.black_holes:
                return 0.0
            
            bh = self.bh_controller.black_holes[bh_id]
            
            # Calculate Hawking power
            hawking_power = self._calculate_hawking_power(bh.mass)
            
            # Apply collection efficiency
            harvested_power = hawking_power * efficiency
            
            logger.info(f"Harvesting {harvested_power:.2e} W from black hole {bh_id}")
            
            return harvested_power
    
    def initiate_evaporation(self, bh_id: str, acceleration_factor: float) -> bool:
        """Initiate controlled evaporation"""
        with self.lock:
            if bh_id not in self.bh_controller.black_holes:
                return False
            
            logger.info(f"Initiating evaporation for black hole {bh_id}")
            logger.info(f"Acceleration factor: {acceleration_factor}x")
            
            evaporation_state = {
                "bh_id": bh_id,
                "acceleration_factor": acceleration_factor,
                "start_time": np.datetime64('now'),
                "status": "active"
            }
            
            self.active_harvesting[bh_id] = evaporation_state
            
            return True
    
    def _calculate_hawking_power(self, mass: float) -> float:
        """Calculate Hawking radiation power"""
        # Constants
        hbar = 1.055e-34
        c = 2.998e8
        G = 6.674e-11
        solar_mass = 1.989e30
        
        mass_kg = mass * solar_mass
        
        # P = ħ c^6 / (15360 π G^2 M^2)
        power = (hbar * c**6) / (15360 * np.pi * G**2 * mass_kg**2)
        
        return power
    
    def emergency_shutdown(self):
        """Emergency shutdown"""
        with self.lock:
            logger.critical("Hawking Radiation Harvester emergency shutdown")
            self.active_harvesting.clear()
    
    def reset_to_baseline(self):
        """Reset to baseline"""
        with self.lock:
            self.active_harvesting.clear()