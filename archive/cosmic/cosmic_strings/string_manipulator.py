"""
Cosmic String Manipulator - Main interface for cosmic string operations
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import threading
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class CosmicStringManipulator:
    """Main cosmic string manipulation interface"""
    
    def __init__(self, cosmic_manager):
        """Initialize cosmic string manipulator"""
        self.cosmic_manager = cosmic_manager
        self.lock = threading.RLock()
        
        # String tracking
        self.cosmic_strings: Dict[str, Dict[str, Any]] = {}
        self.string_networks: Dict[str, List[str]] = {}
        
        # Initialize subsystems
        from .string_creation import CosmicStringCreator
        from .string_dynamics import CosmicStringDynamics
        from .string_collisions import CosmicStringCollisions
        
        self.creator = CosmicStringCreator(self)
        self.dynamics = CosmicStringDynamics(self)
        self.collisions = CosmicStringCollisions(self)
        
        logger.info("Cosmic String Manipulator initialized")
    
    def create_cosmic_string(self,
                           length: float,
                           tension: float,
                           start_point: Tuple[float, float, float],
                           end_point: Tuple[float, float, float],
                           string_type: str = "fundamental") -> str:
        """Create a cosmic string"""
        with self.lock:
            string_id = f"string_{uuid.uuid4().hex[:8]}"
            
            # Calculate energy requirements
            energy_required = self.cosmic_manager.energy_manager.calculate_energy_requirements(
                "cosmic_string_creation", {
                    "length": length,
                    "tension": tension,
                    "string_type": string_type
                }
            )
            
            # Check energy availability
            if not self.cosmic_manager.energy_manager.check_energy_availability(energy_required):
                raise RuntimeError(f"Insufficient energy for cosmic string creation")
            
            # Create string
            success = self.creator.create_string(string_id, length, tension, start_point, end_point, string_type)
            
            if success:
                string_properties = {
                    "string_id": string_id,
                    "length": length,
                    "tension": tension,
                    "start_point": start_point,
                    "end_point": end_point,
                    "string_type": string_type,
                    "created_at": datetime.now(),
                    "velocity": (0.0, 0.0, 0.0),
                    "oscillation_modes": [],
                    "energy_density": tension * length,
                    "active": True
                }
                
                self.cosmic_strings[string_id] = string_properties
                
                logger.info(f"Cosmic string created: {string_id}")
                logger.info(f"Length: {length:.2e} m, Tension: {tension:.2e}")
                
                return string_id
            else:
                raise RuntimeError("Cosmic string creation failed")
    
    def manipulate_string(self,
                         string_id: str,
                         manipulation_type: str,
                         parameters: Dict[str, Any]) -> bool:
        """Manipulate cosmic string properties"""
        with self.lock:
            if string_id not in self.cosmic_strings:
                logger.error(f"Cosmic string {string_id} not found")
                return False
            
            string = self.cosmic_strings[string_id]
            
            if manipulation_type == "oscillate":
                return self.dynamics.induce_oscillations(string_id, parameters)
            elif manipulation_type == "stretch":
                return self.dynamics.stretch_string(string_id, parameters)
            elif manipulation_type == "curve":
                return self.dynamics.curve_string(string_id, parameters)
            else:
                logger.error(f"Unknown manipulation type: {manipulation_type}")
                return False
    
    def orchestrate_collision(self,
                            string_ids: List[str],
                            collision_type: str = "intersection",
                            collision_energy: float = 1e15) -> str:
        """Orchestrate cosmic string collision"""
        with self.lock:
            collision_id = f"collision_{uuid.uuid4().hex[:8]}"
            
            success = self.collisions.execute_collision(
                string_ids, collision_id, collision_type, collision_energy
            )
            
            if success:
                logger.info(f"Cosmic string collision orchestrated: {collision_id}")
                return collision_id
            else:
                raise RuntimeError("Cosmic string collision failed")
    
    def get_string_density(self) -> float:
        """Get current cosmic string density"""
        with self.lock:
            if not self.cosmic_strings:
                return 0.0
            
            total_length = sum(s["length"] for s in self.cosmic_strings.values() if s["active"])
            # Simplified density calculation per cubic meter
            universe_volume = (4/3) * np.pi * (4.4e26)**3  # Observable universe
            
            return total_length / universe_volume
    
    def emergency_shutdown(self):
        """Emergency shutdown"""
        with self.lock:
            logger.critical("Cosmic String Manipulator emergency shutdown")
            self.creator.emergency_shutdown()
            self.dynamics.emergency_shutdown()
            self.collisions.emergency_shutdown()
    
    def reset_to_baseline(self):
        """Reset to baseline"""
        with self.lock:
            self.cosmic_strings.clear()
            self.string_networks.clear()
            self.creator.reset_to_baseline()
            self.dynamics.reset_to_baseline()
            self.collisions.reset_to_baseline()