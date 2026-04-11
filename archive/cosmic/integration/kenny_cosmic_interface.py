"""
Kenny Cosmic Interface - Main integration point with Kenny
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class KennyCosmicInterface:
    """Main interface between Kenny and cosmic engineering systems"""
    
    def __init__(self, cosmic_manager):
        self.cosmic_manager = cosmic_manager
        self.command_history = []
        
    def execute_cosmic_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute cosmic engineering command from Kenny"""
        logger.info(f"Kenny cosmic command: {command}")
        
        try:
            if command.startswith("create_galaxy"):
                result = self._handle_galaxy_command(command, parameters)
            elif command.startswith("create_black_hole"):
                result = self._handle_black_hole_command(command, parameters)
            elif command.startswith("create_dyson_sphere"):
                result = self._handle_stellar_command(command, parameters)
            elif command.startswith("trigger_big_bang"):
                result = self._handle_big_bang_command(command, parameters)
            elif command.startswith("manipulate_universe"):
                result = self._handle_universal_command(command, parameters)
            else:
                result = {"success": False, "error": f"Unknown command: {command}"}
                
            # Record command
            self.command_history.append({
                "command": command,
                "parameters": parameters,
                "result": result,
                "timestamp": logger.time.time()
            })
            
            return result
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            logger.error(f"Cosmic command failed: {e}")
            return error_result
            
    def _handle_galaxy_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle galaxy-related commands"""
        if "create" in command:
            galaxy_id = self.cosmic_manager.galaxy_engineer.create_galaxy(
                galaxy_type=params.get("type", "spiral"),
                total_mass=params.get("mass", 1e12),
                location=params.get("location", (0, 0, 0))
            )
            return {"success": True, "galaxy_id": galaxy_id}
        else:
            return {"success": False, "error": "Unknown galaxy command"}
            
    def _handle_black_hole_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle black hole commands"""
        if "create" in command:
            bh_id = self.cosmic_manager.black_hole_controller.create_black_hole(
                mass=params.get("mass", 10),
                location=params.get("location", (0, 0, 0)),
                spin=params.get("spin", 0.0)
            )
            return {"success": True, "black_hole_id": bh_id}
        else:
            return {"success": False, "error": "Unknown black hole command"}
            
    def _handle_stellar_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stellar engineering commands"""
        if "dyson_sphere" in command:
            # Find or create a star first
            star_id = params.get("star_id", "default_star")
            dyson_id = self.cosmic_manager.stellar_engineer.create_dyson_sphere(
                star_id=star_id,
                sphere_type=params.get("type", "swarm"),
                radius=params.get("radius", 1.0)
            )
            return {"success": True, "dyson_sphere_id": dyson_id}
        else:
            return {"success": False, "error": "Unknown stellar command"}
            
    def _handle_big_bang_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Big Bang commands"""
        universe_id = self.cosmic_manager.big_bang_simulator.initiate_big_bang(
            initial_conditions=params.get("initial_conditions")
        )
        return {"success": True, "universe_id": universe_id}
        
    def _handle_universal_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle universal manipulation commands"""
        if "expand" in command:
            success = self.cosmic_manager.expansion_controller.accelerate_expansion(
                acceleration_factor=params.get("factor", 1.1)
            )
            return {"success": success}
        elif "contract" in command:
            success = self.cosmic_manager.expansion_controller.reverse_expansion()
            return {"success": success}
        else:
            return {"success": False, "error": "Unknown universal command"}
            
    def get_cosmic_status(self) -> Dict[str, Any]:
        """Get overall cosmic engineering status"""
        return {
            "galaxy_engineering": self.cosmic_manager.galaxy_engineer.get_status(),
            "black_hole_engineering": self.cosmic_manager.black_hole_controller.get_status(),
            "stellar_engineering": self.cosmic_manager.stellar_engineer.get_status(),
            "cosmic_strings": len(self.cosmic_manager.cosmic_string_manipulator.cosmic_strings),
            "dark_energy_density": self.cosmic_manager.dark_energy_controller.get_density(),
            "inflation_rate": self.cosmic_manager.inflation_controller.get_current_rate(),
            "vacuum_energy": self.cosmic_manager.vacuum_manipulator.get_vacuum_energy(),
            "hubble_constant": self.cosmic_manager.expansion_controller.hubble_constant
        }