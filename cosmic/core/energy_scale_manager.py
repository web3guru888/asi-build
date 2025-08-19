"""
Energy Scale Manager

Manages energy scales across the cosmic engineering framework,
from Planck scale to universal scale operations.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)

class EnergyScale(Enum):
    """Energy scale definitions"""
    PLANCK = 1.956e19  # GeV - Planck energy
    GUT = 1e16         # GeV - Grand Unified Theory scale
    ELECTROWEAK = 100  # GeV - Electroweak scale
    QCD = 0.2          # GeV - QCD scale
    NUCLEAR = 1e-3     # GeV - Nuclear scale
    ATOMIC = 1e-8      # GeV - Atomic scale
    MOLECULAR = 1e-12  # GeV - Molecular scale
    THERMAL = 1e-13    # GeV - Room temperature scale
    COSMIC_RAY = 1e11  # GeV - Ultra-high energy cosmic rays
    STELLAR = 1e-6     # GeV - Stellar energy per nucleon
    GALACTIC = 1e3     # GeV - Galactic magnetic field scale
    DARK_ENERGY = 1e-12 # GeV - Dark energy scale

@dataclass
class EnergyReservoir:
    """Represents an energy reservoir for cosmic operations"""
    reservoir_id: str
    energy_type: str
    total_energy: float  # GeV
    available_energy: float  # GeV
    extraction_rate: float  # GeV/s
    location: Tuple[float, float, float]
    efficiency: float = 1.0
    stability: float = 1.0

class EnergyScaleManager:
    """
    Manages energy scales and energy operations across cosmic engineering
    
    Handles energy extraction, conversion, and distribution for
    universe-scale engineering projects.
    """
    
    def __init__(self):
        """Initialize energy scale manager"""
        self.lock = threading.RLock()
        
        # Energy reservoirs and sources
        self.energy_reservoirs: Dict[str, EnergyReservoir] = {}
        self.energy_extraction_operations: Dict[str, Dict[str, Any]] = {}
        
        # Energy conversion efficiencies
        self.conversion_matrix = self._initialize_conversion_matrix()
        
        # Safety limits for energy operations
        self.safety_limits = {
            "max_extraction_rate": 1e20,  # GeV/s
            "max_single_operation": 1e25,  # GeV
            "vacuum_stability_threshold": 1e18,  # GeV/m^3
            "planck_density_limit": 5.16e96,  # kg/m^3
        }
        
        # Initialize default energy sources
        self._initialize_default_sources()
        
        logger.info("Energy Scale Manager initialized")
    
    def _initialize_conversion_matrix(self) -> Dict[str, Dict[str, float]]:
        """Initialize energy conversion efficiency matrix"""
        # Conversion efficiencies between different energy types
        conversions = {
            "mass_energy": {
                "kinetic": 1.0,      # E=mc^2 perfect conversion
                "potential": 0.9,    # Gravitational binding
                "thermal": 0.1,      # Thermodynamic limits
                "electromagnetic": 0.8,
                "nuclear": 0.007,    # Nuclear binding energy
                "dark_energy": 0.001 # Hypothetical conversion
            },
            "kinetic": {
                "mass_energy": 1.0,
                "potential": 0.95,
                "thermal": 0.4,
                "electromagnetic": 0.7,
                "nuclear": 0.001,
                "dark_energy": 0.0001
            },
            "potential": {
                "mass_energy": 0.9,
                "kinetic": 0.95,
                "thermal": 0.3,
                "electromagnetic": 0.6,
                "nuclear": 0.001,
                "dark_energy": 0.0001
            },
            "thermal": {
                "mass_energy": 0.1,
                "kinetic": 0.4,
                "potential": 0.3,
                "electromagnetic": 0.5,
                "nuclear": 0.0001,
                "dark_energy": 0.00001
            },
            "electromagnetic": {
                "mass_energy": 0.8,
                "kinetic": 0.7,
                "potential": 0.6,
                "thermal": 0.5,
                "nuclear": 0.01,
                "dark_energy": 0.001
            },
            "nuclear": {
                "mass_energy": 0.007,
                "kinetic": 0.001,
                "potential": 0.001,
                "thermal": 0.0001,
                "electromagnetic": 0.01,
                "dark_energy": 0.000001
            },
            "dark_energy": {
                "mass_energy": 0.001,
                "kinetic": 0.0001,
                "potential": 0.0001,
                "thermal": 0.00001,
                "electromagnetic": 0.001,
                "nuclear": 0.000001
            },
            "vacuum_energy": {
                "mass_energy": 0.01,
                "kinetic": 0.001,
                "potential": 0.001,
                "thermal": 0.0001,
                "electromagnetic": 0.01,
                "nuclear": 0.00001,
                "dark_energy": 0.1
            }
        }
        
        return conversions
    
    def _initialize_default_sources(self):
        """Initialize default energy sources for cosmic operations"""
        # Vacuum energy reservoir
        self.create_energy_reservoir(
            "vacuum_zero_point",
            "vacuum_energy", 
            1e50,  # Enormous but finite vacuum energy
            (0, 0, 0),
            extraction_rate=1e15
        )
        
        # Dark energy reservoir
        self.create_energy_reservoir(
            "dark_energy_field",
            "dark_energy",
            1e60,  # Dark energy dominates universe
            (0, 0, 0),
            extraction_rate=1e12
        )
        
        # Stellar fusion reservoir (representative)
        self.create_energy_reservoir(
            "stellar_fusion",
            "nuclear",
            1e35,  # Total stellar energy in observable universe
            (0, 0, 0),
            extraction_rate=1e10
        )
        
        # Gravitational potential reservoir
        self.create_energy_reservoir(
            "gravitational_binding",
            "potential",
            1e45,  # Gravitational binding energy
            (0, 0, 0),
            extraction_rate=1e13
        )
    
    def create_energy_reservoir(self,
                              reservoir_id: str,
                              energy_type: str,
                              total_energy: float,
                              location: Tuple[float, float, float],
                              extraction_rate: float,
                              efficiency: float = 1.0) -> bool:
        """
        Create a new energy reservoir
        
        Args:
            reservoir_id: Unique identifier
            energy_type: Type of energy (mass_energy, kinetic, etc.)
            total_energy: Total energy available (GeV)
            location: (x, y, z) coordinates
            extraction_rate: Maximum extraction rate (GeV/s)
            efficiency: Extraction efficiency (0-1)
            
        Returns:
            True if successful
        """
        with self.lock:
            if reservoir_id in self.energy_reservoirs:
                logger.warning(f"Energy reservoir {reservoir_id} already exists")
                return False
            
            reservoir = EnergyReservoir(
                reservoir_id=reservoir_id,
                energy_type=energy_type,
                total_energy=total_energy,
                available_energy=total_energy,
                extraction_rate=extraction_rate,
                location=location,
                efficiency=efficiency,
                stability=1.0
            )
            
            self.energy_reservoirs[reservoir_id] = reservoir
            
            logger.info(f"Created energy reservoir {reservoir_id}")
            logger.info(f"Type: {energy_type}, Energy: {total_energy:.2e} GeV")
            
            return True
    
    def extract_energy(self,
                      reservoir_id: str,
                      amount: float,
                      target_type: Optional[str] = None) -> Tuple[bool, float]:
        """
        Extract energy from a reservoir
        
        Args:
            reservoir_id: ID of reservoir to extract from
            amount: Amount of energy to extract (GeV)
            target_type: Convert to this energy type (optional)
            
        Returns:
            (success, actual_extracted_energy)
        """
        with self.lock:
            if reservoir_id not in self.energy_reservoirs:
                logger.error(f"Energy reservoir {reservoir_id} not found")
                return False, 0.0
            
            reservoir = self.energy_reservoirs[reservoir_id]
            
            # Check safety limits
            if amount > self.safety_limits["max_single_operation"]:
                logger.error(f"Energy extraction {amount:.2e} GeV exceeds safety limit")
                return False, 0.0
            
            # Check availability
            if amount > reservoir.available_energy:
                # Extract what's available
                amount = reservoir.available_energy
                logger.warning(f"Reduced extraction to available energy: {amount:.2e} GeV")
            
            # Apply efficiency
            extracted = amount * reservoir.efficiency
            
            # Apply conversion if requested
            if target_type and target_type != reservoir.energy_type:
                conversion_efficiency = self.get_conversion_efficiency(
                    reservoir.energy_type, target_type
                )
                extracted *= conversion_efficiency
                
                logger.info(f"Converting {reservoir.energy_type} -> {target_type}")
                logger.info(f"Conversion efficiency: {conversion_efficiency:.3f}")
            
            # Update reservoir
            reservoir.available_energy -= amount
            
            logger.info(f"Extracted {extracted:.2e} GeV from {reservoir_id}")
            logger.info(f"Remaining: {reservoir.available_energy:.2e} GeV")
            
            return True, extracted
    
    def get_conversion_efficiency(self, from_type: str, to_type: str) -> float:
        """Get conversion efficiency between energy types"""
        with self.lock:
            if from_type == to_type:
                return 1.0
            
            if from_type in self.conversion_matrix:
                if to_type in self.conversion_matrix[from_type]:
                    return self.conversion_matrix[from_type][to_type]
            
            # Default very low efficiency for unknown conversions
            logger.warning(f"Unknown conversion {from_type} -> {to_type}, using 0.001 efficiency")
            return 0.001
    
    def calculate_energy_requirements(self, operation_type: str, parameters: Dict[str, Any]) -> float:
        """
        Calculate energy requirements for cosmic operations
        
        Args:
            operation_type: Type of operation
            parameters: Operation parameters
            
        Returns:
            Required energy in GeV
        """
        with self.lock:
            if operation_type == "galaxy_creation":
                # Estimate energy for galaxy creation
                mass = parameters.get("mass", 1e12)  # Solar masses
                solar_mass_gev = 1.78e57  # GeV
                return mass * solar_mass_gev
            
            elif operation_type == "black_hole_creation":
                mass = parameters.get("mass", 10)  # Solar masses
                solar_mass_gev = 1.78e57  # GeV
                return mass * solar_mass_gev
            
            elif operation_type == "stellar_engineering":
                star_mass = parameters.get("star_mass", 1)  # Solar masses
                solar_mass_gev = 1.78e57  # GeV
                return 0.1 * star_mass * solar_mass_gev  # 10% of star mass
            
            elif operation_type == "cosmic_string_creation":
                length = parameters.get("length", 1e20)  # meters
                tension = parameters.get("tension", 1e-6)  # dimensionless
                string_energy_per_meter = 1e15  # GeV/m (rough estimate)
                return length * string_energy_per_meter * tension
            
            elif operation_type == "vacuum_manipulation":
                volume = parameters.get("volume", 1e30)  # m^3
                energy_density = parameters.get("energy_density", 1e10)  # GeV/m^3
                return volume * energy_density
            
            elif operation_type == "inflation_trigger":
                region_size = parameters.get("region_size", 1e20)  # meters
                inflation_energy = 1e16  # GeV (GUT scale)
                volume = (4/3) * np.pi * (region_size/2)**3
                planck_volumes = volume / (1.616e-35)**3
                return planck_volumes * inflation_energy
            
            elif operation_type == "big_bang_replication":
                # Enormous energy requirement
                return 1e70  # GeV
            
            else:
                logger.warning(f"Unknown operation type: {operation_type}")
                return 1e20  # Default large energy requirement
    
    def check_energy_availability(self, required_energy: float, energy_type: str = None) -> bool:
        """
        Check if enough energy is available for an operation
        
        Args:
            required_energy: Energy needed (GeV)
            energy_type: Preferred energy type (optional)
            
        Returns:
            True if energy is available
        """
        with self.lock:
            if energy_type:
                # Check specific energy type
                for reservoir in self.energy_reservoirs.values():
                    if reservoir.energy_type == energy_type:
                        if reservoir.available_energy >= required_energy:
                            return True
            
            # Check all reservoirs with conversion
            total_available = 0.0
            
            for reservoir in self.energy_reservoirs.values():
                available = reservoir.available_energy
                
                if energy_type and reservoir.energy_type != energy_type:
                    # Apply conversion efficiency
                    efficiency = self.get_conversion_efficiency(reservoir.energy_type, energy_type)
                    available *= efficiency
                
                total_available += available
                
                if total_available >= required_energy:
                    return True
            
            return False
    
    def allocate_energy_for_operation(self,
                                    operation_id: str,
                                    required_energy: float,
                                    preferred_type: str = None) -> Dict[str, float]:
        """
        Allocate energy from multiple reservoirs for an operation
        
        Args:
            operation_id: Unique operation identifier
            required_energy: Total energy needed (GeV)
            preferred_type: Preferred energy type
            
        Returns:
            Dictionary mapping reservoir_id to allocated energy
        """
        with self.lock:
            allocation = {}
            remaining_energy = required_energy
            
            # Sort reservoirs by preference
            reservoirs = list(self.energy_reservoirs.values())
            
            if preferred_type:
                # Prioritize reservoirs with preferred type
                reservoirs.sort(key=lambda r: (
                    r.energy_type != preferred_type,
                    -r.available_energy
                ))
            else:
                # Sort by available energy (descending)
                reservoirs.sort(key=lambda r: -r.available_energy)
            
            for reservoir in reservoirs:
                if remaining_energy <= 0:
                    break
                
                # Calculate how much we can extract from this reservoir
                available = reservoir.available_energy
                
                if preferred_type and reservoir.energy_type != preferred_type:
                    # Apply conversion efficiency
                    efficiency = self.get_conversion_efficiency(
                        reservoir.energy_type, preferred_type
                    )
                    effective_available = available * efficiency
                else:
                    effective_available = available
                
                # Take what we need or what's available
                to_allocate = min(remaining_energy, effective_available)
                
                if to_allocate > 0:
                    allocation[reservoir.reservoir_id] = to_allocate
                    remaining_energy -= to_allocate
            
            if remaining_energy > 0:
                logger.warning(f"Could not fully allocate energy for {operation_id}")
                logger.warning(f"Still need {remaining_energy:.2e} GeV")
            
            # Record allocation
            self.energy_extraction_operations[operation_id] = {
                "required_energy": required_energy,
                "allocation": allocation,
                "preferred_type": preferred_type,
                "timestamp": np.datetime64('now')
            }
            
            return allocation
    
    def execute_energy_extraction(self, operation_id: str) -> bool:
        """
        Execute the energy extraction for an allocated operation
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            True if successful
        """
        with self.lock:
            if operation_id not in self.energy_extraction_operations:
                logger.error(f"No energy allocation found for operation {operation_id}")
                return False
            
            operation = self.energy_extraction_operations[operation_id]
            allocation = operation["allocation"]
            preferred_type = operation["preferred_type"]
            
            total_extracted = 0.0
            
            for reservoir_id, allocated_energy in allocation.items():
                success, extracted = self.extract_energy(
                    reservoir_id, allocated_energy, preferred_type
                )
                
                if success:
                    total_extracted += extracted
                else:
                    logger.error(f"Failed to extract from reservoir {reservoir_id}")
                    return False
            
            logger.info(f"Operation {operation_id} extracted {total_extracted:.2e} GeV total")
            
            # Mark operation as completed
            operation["status"] = "completed"
            operation["total_extracted"] = total_extracted
            
            return True
    
    def get_energy_scale_for_operation(self, operation_type: str) -> EnergyScale:
        """Get appropriate energy scale for operation type"""
        scale_mapping = {
            "particle_physics": EnergyScale.ELECTROWEAK,
            "nuclear_physics": EnergyScale.QCD,
            "stellar_engineering": EnergyScale.STELLAR,
            "galactic_engineering": EnergyScale.GALACTIC,
            "cosmic_string": EnergyScale.GUT,
            "vacuum_manipulation": EnergyScale.PLANCK,
            "inflation": EnergyScale.GUT,
            "big_bang": EnergyScale.PLANCK
        }
        
        return scale_mapping.get(operation_type, EnergyScale.ELECTROWEAK)
    
    def get_total_available_energy(self, energy_type: str = None) -> float:
        """Get total available energy across all reservoirs"""
        with self.lock:
            total = 0.0
            
            for reservoir in self.energy_reservoirs.values():
                if energy_type is None or reservoir.energy_type == energy_type:
                    total += reservoir.available_energy
            
            return total
    
    def get_reservoir_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all energy reservoirs"""
        with self.lock:
            status = {}
            
            for reservoir_id, reservoir in self.energy_reservoirs.items():
                status[reservoir_id] = {
                    "energy_type": reservoir.energy_type,
                    "total_energy": reservoir.total_energy,
                    "available_energy": reservoir.available_energy,
                    "utilization": 1.0 - (reservoir.available_energy / reservoir.total_energy),
                    "extraction_rate": reservoir.extraction_rate,
                    "efficiency": reservoir.efficiency,
                    "stability": reservoir.stability,
                    "location": reservoir.location
                }
            
            return status
    
    def emergency_shutdown(self):
        """Emergency shutdown of energy operations"""
        with self.lock:
            logger.critical("Energy Scale Manager emergency shutdown")
            
            # Cancel all extraction operations
            for operation_id in list(self.energy_extraction_operations.keys()):
                operation = self.energy_extraction_operations[operation_id]
                operation["status"] = "aborted"
            
            logger.critical("All energy extraction operations aborted")
    
    def reset_to_baseline(self):
        """Reset energy manager to baseline state"""
        with self.lock:
            logger.info("Resetting Energy Scale Manager to baseline")
            
            # Clear all operations
            self.energy_extraction_operations.clear()
            
            # Reset all reservoirs to full capacity
            for reservoir in self.energy_reservoirs.values():
                reservoir.available_energy = reservoir.total_energy
                reservoir.stability = 1.0
            
            logger.info("Energy Scale Manager reset to baseline")