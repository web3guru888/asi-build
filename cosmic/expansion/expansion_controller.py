"""
Expansion Controller - Controls universal expansion and contraction
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import threading

logger = logging.getLogger(__name__)

class ExpansionController:
    """Universal expansion and contraction control system"""
    
    def __init__(self, cosmic_manager):
        """Initialize expansion controller"""
        self.cosmic_manager = cosmic_manager
        self.lock = threading.RLock()
        
        # Current cosmological parameters
        self.hubble_constant = 67.4  # km/s/Mpc
        self.scale_factor = 1.0  # Present day = 1.0
        self.expansion_history: List[Dict[str, Any]] = []
        
        # Initialize subsystems
        from .hubble_parameter_manipulator import HubbleParameterManipulator
        from .scale_factor_controller import ScaleFactorController
        
        self.hubble_manipulator = HubbleParameterManipulator(self)
        self.scale_controller = ScaleFactorController(self)
        
        logger.info("Expansion Controller initialized")
    
    def accelerate_expansion(self, acceleration_factor: float = 1.1) -> bool:
        """Accelerate universal expansion"""
        with self.lock:
            logger.warning(f"Accelerating universal expansion by factor {acceleration_factor}")
            
            old_hubble = self.hubble_constant
            self.hubble_constant *= acceleration_factor
            
            # Record change
            self.expansion_history.append({
                "action": "accelerate",
                "old_hubble": old_hubble,
                "new_hubble": self.hubble_constant,
                "factor": acceleration_factor,
                "timestamp": np.datetime64('now')
            })
            
            logger.warning(f"Hubble constant changed: {old_hubble} -> {self.hubble_constant} km/s/Mpc")
            
            return True
    
    def decelerate_expansion(self, deceleration_factor: float = 0.9) -> bool:
        """Decelerate universal expansion"""
        with self.lock:
            logger.warning(f"Decelerating universal expansion by factor {deceleration_factor}")
            
            old_hubble = self.hubble_constant
            self.hubble_constant *= deceleration_factor
            
            # Record change
            self.expansion_history.append({
                "action": "decelerate",
                "old_hubble": old_hubble,
                "new_hubble": self.hubble_constant,
                "factor": deceleration_factor,
                "timestamp": np.datetime64('now')
            })
            
            logger.warning(f"Hubble constant changed: {old_hubble} -> {self.hubble_constant} km/s/Mpc")
            
            return True
    
    def reverse_expansion(self, contraction_rate: float = -50.0) -> bool:
        """Reverse expansion to cause universal contraction"""
        with self.lock:
            logger.critical("REVERSING UNIVERSAL EXPANSION")
            logger.critical("INITIATING BIG CRUNCH SCENARIO")
            
            old_hubble = self.hubble_constant
            self.hubble_constant = contraction_rate  # Negative Hubble parameter
            
            # Record change
            self.expansion_history.append({
                "action": "reverse",
                "old_hubble": old_hubble,
                "new_hubble": self.hubble_constant,
                "timestamp": np.datetime64('now')
            })
            
            logger.critical(f"Hubble constant set to {self.hubble_constant} km/s/Mpc")
            logger.critical("Universe now contracting - Big Crunch initiated")
            
            return True
    
    def set_expansion_rate(self, new_hubble_constant: float) -> bool:
        """Set specific expansion rate"""
        with self.lock:
            old_hubble = self.hubble_constant
            self.hubble_constant = new_hubble_constant
            
            # Record change
            self.expansion_history.append({
                "action": "set_rate",
                "old_hubble": old_hubble,
                "new_hubble": self.hubble_constant,
                "timestamp": np.datetime64('now')
            })
            
            logger.info(f"Expansion rate set to {self.hubble_constant} km/s/Mpc")
            
            return True
    
    def calculate_distance_redshift(self, redshift: float) -> float:
        """Calculate distance for given redshift"""
        # Simplified calculation assuming flat universe
        c = 299792.458  # km/s
        return (c * redshift) / self.hubble_constant  # Mpc
    
    def get_age_of_universe(self) -> float:
        """Calculate current age of universe"""
        # Simplified: Age ≈ 1/H0 for matter-dominated universe
        hubble_si = self.hubble_constant * 1000 / (3.086e22)  # Convert to SI
        age_seconds = 1.0 / hubble_si
        age_years = age_seconds / (365.25 * 24 * 3600)
        
        return age_years
    
    def emergency_shutdown(self):
        """Emergency shutdown"""
        with self.lock:
            logger.critical("Expansion Controller emergency shutdown")
            
            # Reset to standard cosmological parameters
            self.hubble_constant = 67.4  # Standard value
            self.scale_factor = 1.0
            
            self.hubble_manipulator.emergency_shutdown()
            self.scale_controller.emergency_shutdown()
    
    def reset_to_baseline(self):
        """Reset to baseline"""
        with self.lock:
            self.hubble_constant = 67.4
            self.scale_factor = 1.0
            self.expansion_history.clear()
            
            self.hubble_manipulator.reset_to_baseline()
            self.scale_controller.reset_to_baseline()