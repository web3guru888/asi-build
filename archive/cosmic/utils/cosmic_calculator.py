"""
Cosmic Calculator - Utility calculations for cosmic engineering
"""
import numpy as np
import logging

logger = logging.getLogger(__name__)

class CosmicCalculator:
    """Utility calculations for cosmic engineering operations"""
    
    def __init__(self):
        # Physical constants
        self.c = 2.998e8
        self.G = 6.674e-11
        self.hbar = 1.055e-34
        
    def schwarzschild_radius(self, mass_kg):
        """Calculate Schwarzschild radius"""
        return 2 * self.G * mass_kg / (self.c ** 2)
        
    def hawking_temperature(self, mass_kg):
        """Calculate Hawking temperature"""
        rs = self.schwarzschild_radius(mass_kg)
        return self.hbar * self.c**3 / (8 * np.pi * self.G * mass_kg * 1.381e-23)
        
    def binding_energy(self, mass_kg, radius_m):
        """Calculate gravitational binding energy"""
        return 3 * self.G * mass_kg**2 / (5 * radius_m)
        
    def escape_velocity(self, mass_kg, radius_m):
        """Calculate escape velocity"""
        return np.sqrt(2 * self.G * mass_kg / radius_m)
        
    def hubble_time(self, hubble_constant):
        """Calculate Hubble time"""
        h_si = hubble_constant * 1000 / 3.086e22
        return 1.0 / h_si
        
    def critical_density(self, hubble_constant):
        """Calculate critical density of universe"""
        h_si = hubble_constant * 1000 / 3.086e22
        return 3 * h_si**2 / (8 * np.pi * self.G)
        
    def comoving_distance(self, redshift, hubble_constant=67.4):
        """Calculate comoving distance for redshift"""
        return self.c * redshift / (hubble_constant * 1000 / 3.086e22)
        
    def luminosity_distance(self, redshift, hubble_constant=67.4):
        """Calculate luminosity distance"""
        return self.comoving_distance(redshift, hubble_constant) * (1 + redshift)