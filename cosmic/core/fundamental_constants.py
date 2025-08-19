"""
Fundamental Constants Manager

Manages and allows manipulation of fundamental physical constants
for universe-scale engineering operations.

WARNING: Modifying fundamental constants can have catastrophic consequences.
Use with extreme caution and proper safety protocols.
"""

import logging
import numpy as np
from typing import Dict, Optional, Any
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)

@dataclass
class ConstantState:
    """State of a fundamental constant"""
    name: str
    value: float
    units: str
    standard_value: float
    modification_factor: float
    last_modified: Optional[str] = None
    safety_locked: bool = False

class FundamentalConstants:
    """
    Manager for fundamental physical constants
    
    Allows controlled manipulation of the universe's fundamental constants
    while maintaining safety and monitoring capabilities.
    """
    
    def __init__(self):
        """Initialize with standard model values"""
        self.lock = threading.RLock()
        self.constants: Dict[str, ConstantState] = {}
        self.modification_history: list = []
        
        # Initialize with standard values
        self._initialize_constants()
        
        logger.info("Fundamental Constants Manager initialized")
    
    def _initialize_constants(self):
        """Initialize all fundamental constants to standard values"""
        standard_constants = {
            # Planck units and fundamental scales
            "planck_length": {
                "value": 1.616255e-35,
                "units": "m",
                "description": "Planck length"
            },
            "planck_time": {
                "value": 5.391247e-44,
                "units": "s", 
                "description": "Planck time"
            },
            "planck_mass": {
                "value": 2.176434e-8,
                "units": "kg",
                "description": "Planck mass"
            },
            "planck_energy": {
                "value": 1.956081e9,
                "units": "J",
                "description": "Planck energy"
            },
            "planck_temperature": {
                "value": 1.416784e32,
                "units": "K",
                "description": "Planck temperature"
            },
            
            # Fundamental interactions
            "speed_of_light": {
                "value": 299792458.0,
                "units": "m/s",
                "description": "Speed of light in vacuum"
            },
            "gravitational_constant": {
                "value": 6.67430e-11,
                "units": "m^3/kg/s^2",
                "description": "Gravitational constant"
            },
            "planck_constant": {
                "value": 6.62607015e-34,
                "units": "J*s",
                "description": "Planck constant"
            },
            "fine_structure_constant": {
                "value": 7.2973525693e-3,
                "units": "dimensionless",
                "description": "Fine structure constant"
            },
            "electric_charge": {
                "value": 1.602176634e-19,
                "units": "C",
                "description": "Elementary charge"
            },
            
            # Particle masses (in eV/c^2)
            "electron_mass": {
                "value": 0.51099895000e6,
                "units": "eV/c^2",
                "description": "Electron rest mass"
            },
            "proton_mass": {
                "value": 938.27208816e6,
                "units": "eV/c^2", 
                "description": "Proton rest mass"
            },
            "neutron_mass": {
                "value": 939.56542052e6,
                "units": "eV/c^2",
                "description": "Neutron rest mass"
            },
            "higgs_mass": {
                "value": 125.18e9,
                "units": "eV/c^2",
                "description": "Higgs boson mass"
            },
            
            # Cosmological parameters
            "hubble_constant": {
                "value": 67.4,
                "units": "km/s/Mpc",
                "description": "Hubble constant"
            },
            "dark_energy_density": {
                "value": 6.8e-27,
                "units": "kg/m^3",
                "description": "Dark energy density"
            },
            "dark_matter_density": {
                "value": 2.6e-27,
                "units": "kg/m^3",
                "description": "Dark matter density"
            },
            "baryon_density": {
                "value": 4.1e-28,
                "units": "kg/m^3",
                "description": "Baryon density"
            },
            "cmb_temperature": {
                "value": 2.7255,
                "units": "K",
                "description": "CMB temperature"
            },
            
            # Vacuum properties
            "vacuum_permeability": {
                "value": 1.25663706212e-6,
                "units": "H/m",
                "description": "Vacuum permeability"
            },
            "vacuum_permittivity": {
                "value": 8.8541878128e-12,
                "units": "F/m",
                "description": "Vacuum permittivity"
            },
            "vacuum_energy_density": {
                "value": 1e-15,  # Estimated, highly uncertain
                "units": "J/m^3",
                "description": "Vacuum energy density"
            },
            
            # Critical thresholds for cosmic engineering
            "false_vacuum_threshold": {
                "value": 1e16,
                "units": "GeV",
                "description": "False vacuum decay threshold"
            },
            "inflation_field_value": {
                "value": 1e16,
                "units": "GeV",
                "description": "Inflation field critical value"
            },
            "cosmic_string_tension": {
                "value": 1e-6,
                "units": "dimensionless",
                "description": "Cosmic string tension parameter"
            }
        }
        
        for name, props in standard_constants.items():
            self.constants[name] = ConstantState(
                name=name,
                value=props["value"],
                units=props["units"],
                standard_value=props["value"],
                modification_factor=1.0
            )
    
    def get_constant(self, name: str) -> float:
        """Get current value of a fundamental constant"""
        with self.lock:
            if name not in self.constants:
                raise ValueError(f"Unknown constant: {name}")
            
            return self.constants[name].value
    
    def set_constant(self, name: str, value: float, override_safety: bool = False) -> bool:
        """
        Set the value of a fundamental constant
        
        Args:
            name: Name of the constant
            value: New value
            override_safety: Whether to override safety locks
            
        Returns:
            True if successful, False if blocked by safety
        """
        with self.lock:
            if name not in self.constants:
                raise ValueError(f"Unknown constant: {name}")
            
            constant = self.constants[name]
            
            # Check safety lock
            if constant.safety_locked and not override_safety:
                logger.warning(f"Constant {name} is safety locked")
                return False
            
            # Check for dangerous modifications
            modification_factor = value / constant.standard_value
            
            if not override_safety:
                if modification_factor > 10 or modification_factor < 0.1:
                    logger.error(f"Dangerous modification to {name}: factor {modification_factor}")
                    return False
                
                # Special checks for critical constants
                if name == "speed_of_light" and modification_factor != 1.0:
                    logger.error("Modifying speed of light could break causality")
                    return False
                
                if name == "fine_structure_constant":
                    if modification_factor > 1.1 or modification_factor < 0.9:
                        logger.error("Large changes to fine structure constant could destroy atoms")
                        return False
            
            # Apply the change
            old_value = constant.value
            constant.value = value
            constant.modification_factor = modification_factor
            constant.last_modified = f"Modified from {old_value} to {value}"
            
            # Record in history
            self.modification_history.append({
                "constant": name,
                "old_value": old_value,
                "new_value": value,
                "factor": modification_factor,
                "timestamp": np.datetime64('now')
            })
            
            logger.info(f"Modified {name}: {old_value} -> {value} (factor: {modification_factor:.3f})")
            return True
    
    def modify_constant_by_factor(self, name: str, factor: float, override_safety: bool = False) -> bool:
        """
        Modify a constant by a multiplicative factor
        
        Args:
            name: Name of the constant
            factor: Multiplicative factor
            override_safety: Whether to override safety locks
            
        Returns:
            True if successful
        """
        with self.lock:
            if name not in self.constants:
                raise ValueError(f"Unknown constant: {name}")
            
            current_value = self.constants[name].value
            new_value = current_value * factor
            
            return self.set_constant(name, new_value, override_safety)
    
    def reset_constant(self, name: str) -> bool:
        """Reset a constant to its standard value"""
        with self.lock:
            if name not in self.constants:
                raise ValueError(f"Unknown constant: {name}")
            
            constant = self.constants[name]
            
            if constant.safety_locked:
                logger.warning(f"Cannot reset safety-locked constant {name}")
                return False
            
            old_value = constant.value
            constant.value = constant.standard_value
            constant.modification_factor = 1.0
            constant.last_modified = f"Reset from {old_value} to standard value"
            
            logger.info(f"Reset {name} to standard value: {constant.standard_value}")
            return True
    
    def reset_to_standard_model(self) -> bool:
        """Reset all constants to standard model values"""
        with self.lock:
            logger.warning("Resetting all constants to Standard Model values")
            
            reset_count = 0
            for name in self.constants.keys():
                if self.reset_constant(name):
                    reset_count += 1
            
            logger.info(f"Reset {reset_count} constants to standard values")
            return True
    
    def lock_constant(self, name: str) -> bool:
        """Lock a constant to prevent modifications"""
        with self.lock:
            if name not in self.constants:
                raise ValueError(f"Unknown constant: {name}")
            
            self.constants[name].safety_locked = True
            logger.info(f"Locked constant {name}")
            return True
    
    def unlock_constant(self, name: str) -> bool:
        """Unlock a constant to allow modifications"""
        with self.lock:
            if name not in self.constants:
                raise ValueError(f"Unknown constant: {name}")
            
            self.constants[name].safety_locked = False
            logger.info(f"Unlocked constant {name}")
            return True
    
    def get_all_constants(self) -> Dict[str, Dict[str, Any]]:
        """Get all constants and their current states"""
        with self.lock:
            result = {}
            for name, constant in self.constants.items():
                result[name] = {
                    "value": constant.value,
                    "units": constant.units,
                    "standard_value": constant.standard_value,
                    "modification_factor": constant.modification_factor,
                    "last_modified": constant.last_modified,
                    "safety_locked": constant.safety_locked
                }
            return result
    
    def get_modification_history(self) -> list:
        """Get history of all constant modifications"""
        with self.lock:
            return self.modification_history.copy()
    
    def calculate_planck_scale_ratio(self) -> float:
        """Calculate current Planck scale relative to standard"""
        with self.lock:
            current_planck_length = self.get_constant("planck_length")
            standard_planck_length = self.constants["planck_length"].standard_value
            return current_planck_length / standard_planck_length
    
    def calculate_coupling_strength(self, interaction: str) -> float:
        """Calculate coupling strength for fundamental interactions"""
        with self.lock:
            if interaction == "electromagnetic":
                return self.get_constant("fine_structure_constant")
            elif interaction == "gravitational":
                # Dimensionless gravitational coupling
                G = self.get_constant("gravitational_constant")
                c = self.get_constant("speed_of_light")
                hbar = self.get_constant("planck_constant") / (2 * np.pi)
                mp = self.get_constant("proton_mass") * 1.783e-36  # Convert to kg
                return G * mp**2 / (hbar * c)
            else:
                raise ValueError(f"Unknown interaction: {interaction}")
    
    def verify_universe_stability(self) -> Dict[str, bool]:
        """Check if current constants allow for stable universe"""
        with self.lock:
            stability_checks = {}
            
            # Check fine structure constant for atomic stability
            alpha = self.get_constant("fine_structure_constant")
            stability_checks["atoms_stable"] = 0.005 < alpha < 0.2
            
            # Check electron to proton mass ratio
            me = self.get_constant("electron_mass")
            mp = self.get_constant("proton_mass")
            stability_checks["chemistry_possible"] = 0.0001 < me/mp < 0.01
            
            # Check gravitational coupling
            gravity_coupling = self.calculate_coupling_strength("gravitational")
            stability_checks["gravity_balanced"] = 1e-40 < gravity_coupling < 1e-35
            
            # Check cosmological parameters
            H0 = self.get_constant("hubble_constant")
            stability_checks["expansion_reasonable"] = 50 < H0 < 100
            
            # Check vacuum stability
            vacuum_energy = self.get_constant("vacuum_energy_density")
            stability_checks["vacuum_stable"] = vacuum_energy < 1e10  # J/m^3
            
            return stability_checks
    
    # Convenience properties for commonly used constants
    @property
    def c(self) -> float:
        """Speed of light"""
        return self.get_constant("speed_of_light")
    
    @property
    def G(self) -> float:
        """Gravitational constant"""
        return self.get_constant("gravitational_constant")
    
    @property
    def h(self) -> float:
        """Planck constant"""
        return self.get_constant("planck_constant")
    
    @property
    def hbar(self) -> float:
        """Reduced Planck constant"""
        return self.get_constant("planck_constant") / (2 * np.pi)
    
    @property
    def alpha(self) -> float:
        """Fine structure constant"""
        return self.get_constant("fine_structure_constant")
    
    @property
    def hubble_constant(self) -> float:
        """Hubble constant"""
        return self.get_constant("hubble_constant")
    
    @property
    def baryon_density(self) -> float:
        """Baryon density"""
        return self.get_constant("baryon_density")
    
    @property
    def cmb_temperature(self) -> float:
        """CMB temperature"""
        return self.get_constant("cmb_temperature")