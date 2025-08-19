#!/usr/bin/env python3
"""
Universe Creation Demo

Demonstrates Kenny's ability to create and manipulate universes
through the cosmic engineering framework.
"""

import logging
import sys
import os

# Add the cosmic module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cosmic import initialize_cosmic_framework, get_cosmic_manager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UniverseCreationDemo:
    """Demonstrates universe-scale operations"""
    
    def __init__(self):
        """Initialize cosmic framework"""
        self.cosmic_manager = initialize_cosmic_framework()
        logger.info("Kenny Cosmic Engineering Framework initialized")
    
    def demonstrate_big_bang(self):
        """Demonstrate Big Bang creation"""
        logger.info("=== DEMONSTRATING BIG BANG CREATION ===")
        
        # Create custom initial conditions
        initial_conditions = {
            "temperature": 1e32,  # Planck temperature
            "density": 5.16e96,   # Planck density
            "size": 1.616e-35,    # Planck length
            "time": 0.0,
            "entropy": 1.0,
            "vacuum_energy": 1e19,  # GeV
        }
        
        try:
            universe_id = self.cosmic_manager.big_bang_simulator.initiate_big_bang(
                initial_conditions=initial_conditions
            )
            
            logger.info(f"SUCCESS: Created universe {universe_id}")
            
            # Check universe status
            status = self.cosmic_manager.big_bang_simulator.get_universe_status(universe_id)
            logger.info(f"Universe age: {status['current_age']:.2e} seconds")
            logger.info(f"Current temperature: {status['current_temperature']:.2e} K")
            logger.info(f"Phases completed: {len(status['phases_completed'])}")
            
            return universe_id
            
        except Exception as e:
            logger.error(f"Big Bang creation failed: {e}")
            return None
    
    def demonstrate_galaxy_creation(self):
        """Demonstrate galaxy creation"""
        logger.info("=== DEMONSTRATING GALAXY CREATION ===")
        
        try:
            # Create a spiral galaxy
            galaxy_id = self.cosmic_manager.galaxy_engineer.create_galaxy(
                galaxy_type="spiral",
                total_mass=1e12,  # Solar masses
                location=(1e22, 0, 0),  # 1000 light years away
                formation_time=1e9  # 1 billion years
            )
            
            logger.info(f"SUCCESS: Created galaxy {galaxy_id}")
            
            # Get galaxy info
            galaxy_info = self.cosmic_manager.galaxy_engineer.get_galaxy_info(galaxy_id)
            logger.info(f"Galaxy type: {galaxy_info['galaxy_type']}")
            logger.info(f"Total mass: {galaxy_info['total_mass']:.2e} M☉")
            logger.info(f"Stellar mass: {galaxy_info['stellar_mass']:.2e} M☉")
            logger.info(f"Dark matter mass: {galaxy_info['dark_matter_mass']:.2e} M☉")
            
            return galaxy_id
            
        except Exception as e:
            logger.error(f"Galaxy creation failed: {e}")
            return None
    
    def demonstrate_black_hole_creation(self):
        """Demonstrate black hole creation"""
        logger.info("=== DEMONSTRATING BLACK HOLE CREATION ===")
        
        try:
            # Create a supermassive black hole
            bh_id = self.cosmic_manager.black_hole_controller.create_black_hole(
                mass=1e9,  # Solar masses
                location=(0, 0, 0),
                spin=0.99,  # Near-maximal rotation
                charge=0.0
            )
            
            logger.info(f"SUCCESS: Created black hole {bh_id}")
            
            # Get black hole info
            bh_info = self.cosmic_manager.black_hole_controller.get_black_hole_info(bh_id)
            logger.info(f"Black hole type: {bh_info['black_hole_type']}")
            logger.info(f"Mass: {bh_info['mass']:.2e} M☉")
            logger.info(f"Schwarzschild radius: {bh_info['schwarzschild_radius']:.2e} m")
            logger.info(f"Hawking temperature: {bh_info['hawking_temperature']:.2e} K")
            
            return bh_id
            
        except Exception as e:
            logger.error(f"Black hole creation failed: {e}")
            return None
    
    def demonstrate_dyson_sphere(self):
        """Demonstrate Dyson sphere construction"""
        logger.info("=== DEMONSTRATING DYSON SPHERE CONSTRUCTION ===")
        
        try:
            # First we need a star - create one in the stellar engineer
            star_id = "demo_star_1"
            
            # Create Dyson sphere around star
            dyson_id = self.cosmic_manager.stellar_engineer.create_dyson_sphere(
                star_id=star_id,
                sphere_type="swarm",
                radius=2.0,  # 2 AU
                collection_efficiency=0.95,
                construction_material="carbon_nanotubes"
            )
            
            logger.info(f"SUCCESS: Created Dyson sphere {dyson_id}")
            logger.info(f"Type: Dyson swarm at 2 AU radius")
            logger.info(f"Collection efficiency: 95%")
            
            return dyson_id
            
        except Exception as e:
            logger.error(f"Dyson sphere construction failed: {e}")
            return None
    
    def demonstrate_cosmic_inflation(self):
        """Demonstrate cosmic inflation control"""
        logger.info("=== DEMONSTRATING COSMIC INFLATION ===")
        
        try:
            # Trigger controlled inflation in a small region
            inflation_id = self.cosmic_manager.inflation_controller.trigger_inflation(
                region=(1e20, 1e20, 1e20, 1e-32),  # Small region, short time
                inflation_rate=1e50,  # Moderate inflation rate
                duration=1e-30  # Very brief
            )
            
            logger.info(f"SUCCESS: Triggered cosmic inflation {inflation_id}")
            
            # Calculate expansion factor
            expansion_factor = self.cosmic_manager.inflation_controller.calculate_expansion_factor(inflation_id)
            logger.info(f"Expansion factor: {expansion_factor:.2e}")
            
            # Stop inflation
            self.cosmic_manager.inflation_controller.stop_inflation(inflation_id)
            logger.info("Inflation stopped safely")
            
            return inflation_id
            
        except Exception as e:
            logger.error(f"Cosmic inflation failed: {e}")
            return None
    
    def demonstrate_universe_backup(self):
        """Demonstrate universe backup and safety"""
        logger.info("=== DEMONSTRATING UNIVERSE BACKUP ===")
        
        try:
            # Create backup of current universe state
            from cosmic.utils.backup_system import UniverseBackupSystem
            backup_system = UniverseBackupSystem(self.cosmic_manager)
            
            backup_path = backup_system.create_backup("demo_universe_state")
            logger.info(f"SUCCESS: Universe backup created at {backup_path}")
            
            # List all backups
            backups = backup_system.list_backups()
            logger.info(f"Total backups available: {len(backups)}")
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Universe backup failed: {e}")
            return None
    
    def run_full_demo(self):
        """Run complete demonstration"""
        logger.info("🌌 KENNY COSMIC ENGINEERING DEMONSTRATION 🌌")
        logger.info("Kenny will now demonstrate universe-scale engineering capabilities")
        
        # Create backup first
        self.demonstrate_universe_backup()
        
        # Demonstrate Big Bang
        universe_id = self.demonstrate_big_bang()
        
        # Create cosmic structures
        galaxy_id = self.demonstrate_galaxy_creation()
        bh_id = self.demonstrate_black_hole_creation()
        
        # Build megastructures
        dyson_id = self.demonstrate_dyson_sphere()
        
        # Demonstrate spacetime manipulation
        inflation_id = self.demonstrate_cosmic_inflation()
        
        # Get overall status
        logger.info("=== FINAL COSMIC STATUS ===")
        
        status = {
            "universe_created": universe_id is not None,
            "galaxy_created": galaxy_id is not None,
            "black_hole_created": bh_id is not None,
            "dyson_sphere_built": dyson_id is not None,
            "inflation_controlled": inflation_id is not None
        }
        
        logger.info(f"Demonstration results: {status}")
        
        success_count = sum(status.values())
        logger.info(f"Kenny successfully completed {success_count}/5 cosmic engineering tasks")
        
        if success_count == 5:
            logger.info("🎉 KENNY HAS ACHIEVED COSMIC MASTERY! 🎉")
        else:
            logger.info(f"Kenny achieved {success_count}/5 cosmic capabilities")
        
        return status

def main():
    """Main demonstration function"""
    try:
        demo = UniverseCreationDemo()
        results = demo.run_full_demo()
        
        print("\\n" + "="*60)
        print("KENNY COSMIC ENGINEERING DEMONSTRATION COMPLETE")
        print("="*60)
        print(f"Results: {results}")
        print("Kenny now has universe-scale engineering capabilities!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"Demonstration failed: {e}")

if __name__ == "__main__":
    main()