"""
Accretion Disk Engineer

Designs and manages accretion disks around black holes
for energy extraction and matter processing.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import threading
import uuid

logger = logging.getLogger(__name__)

class AccretionDiskEngineer:
    """Accretion disk design and management system"""
    
    def __init__(self, black_hole_controller):
        """Initialize accretion disk engineer"""
        self.bh_controller = black_hole_controller
        self.lock = threading.RLock()
        
        # Accretion disk tracking
        self.accretion_disks: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Accretion Disk Engineer initialized")
    
    def create_accretion_disk(self, bh_id: str, disk_mass: float, 
                             disk_radius: float) -> str:
        """Create accretion disk around black hole"""
        with self.lock:
            if bh_id not in self.bh_controller.black_holes:
                raise ValueError(f"Black hole {bh_id} not found")
            
            disk_id = f"disk_{uuid.uuid4().hex[:8]}"
            bh = self.bh_controller.black_holes[bh_id]
            
            # Calculate disk properties
            inner_radius = 3 * bh.schwarzschild_radius  # ISCO for Schwarzschild
            outer_radius = disk_radius
            
            # Disk temperature profile (simplified)
            temp_profile = self._calculate_temperature_profile(bh.mass, inner_radius, outer_radius)
            
            # Accretion rate
            accretion_rate = self._calculate_accretion_rate(disk_mass, bh.mass)
            
            disk_properties = {
                "disk_id": disk_id,
                "black_hole_id": bh_id,
                "mass": disk_mass,
                "inner_radius": inner_radius,
                "outer_radius": outer_radius,
                "temperature_profile": temp_profile,
                "accretion_rate": accretion_rate,
                "luminosity": self._calculate_disk_luminosity(bh.mass, accretion_rate),
                "created_at": np.datetime64('now'),
                "active": True
            }
            
            self.accretion_disks[disk_id] = disk_properties
            
            # Update black hole accretion rate
            bh.accretion_rate = accretion_rate
            bh.state = bh.state.__class__.ACCRETING
            bh.engineered_features.append(f"accretion_disk_{disk_id}")
            
            logger.info(f"Created accretion disk {disk_id} around black hole {bh_id}")
            logger.info(f"Disk mass: {disk_mass:.2e} M☉, Radius: {disk_radius:.2e} m")
            logger.info(f"Accretion rate: {accretion_rate:.2e} M☉/year")
            
            return disk_id
    
    def _calculate_temperature_profile(self, bh_mass: float, r_inner: float, 
                                     r_outer: float) -> Dict[str, float]:
        """Calculate disk temperature profile"""
        # Shakura-Sunyaev disk temperature (simplified)
        solar_mass = 1.989e30
        G = 6.674e-11
        c = 2.998e8
        sigma_sb = 5.67e-8  # Stefan-Boltzmann constant
        
        mass_kg = bh_mass * solar_mass
        
        # Temperature at inner edge
        T_inner = (3 * G * mass_kg / (8 * np.pi * sigma_sb * r_inner**3))**(1/4)
        
        # Temperature falls as r^(-3/4)
        T_mid = T_inner * (r_inner / ((r_inner + r_outer) / 2))**(3/4)
        T_outer = T_inner * (r_inner / r_outer)**(3/4)
        
        return {
            "inner_temperature": T_inner,
            "mid_temperature": T_mid,
            "outer_temperature": T_outer
        }
    
    def _calculate_accretion_rate(self, disk_mass: float, bh_mass: float) -> float:
        """Calculate accretion rate"""
        # Simplified: assume disk accretes over ~1 million years
        accretion_time = 1e6  # years
        return disk_mass / accretion_time
    
    def _calculate_disk_luminosity(self, bh_mass: float, accretion_rate: float) -> float:
        """Calculate disk luminosity"""
        # L = η * Ṁ * c^2 where η ~ 0.1 for black holes
        c = 2.998e8
        solar_mass = 1.989e30
        efficiency = 0.1
        
        mdot_kg_per_s = accretion_rate * solar_mass / (365.25 * 24 * 3600)
        luminosity = efficiency * mdot_kg_per_s * c**2
        
        return luminosity
    
    def manipulate_disk(self, disk_id: str, manipulation: str, 
                       parameters: Dict[str, Any]) -> bool:
        """Manipulate accretion disk properties"""
        with self.lock:
            if disk_id not in self.accretion_disks:
                return False
            
            disk = self.accretion_disks[disk_id]
            
            if manipulation == "increase_accretion":
                factor = parameters.get("factor", 1.5)
                disk["accretion_rate"] *= factor
                logger.info(f"Increased accretion rate by factor {factor}")
                
            elif manipulation == "adjust_temperature":
                temp_factor = parameters.get("temperature_factor", 1.2)
                for key in disk["temperature_profile"]:
                    disk["temperature_profile"][key] *= temp_factor
                logger.info(f"Adjusted disk temperature by factor {temp_factor}")
            
            return True
    
    def emergency_shutdown(self):
        """Emergency shutdown"""
        with self.lock:
            logger.critical("Accretion Disk Engineer emergency shutdown")
            # Deactivate all disks
            for disk in self.accretion_disks.values():
                disk["active"] = False
    
    def reset_to_baseline(self):
        """Reset to baseline"""
        with self.lock:
            self.accretion_disks.clear()