"""
Basic Multiverse Demo
====================

Demonstrates fundamental multiverse operations including universe creation,
branching, navigation, and basic quantum operations.
"""

import time
import logging
from typing import Dict, Any

from ..core.multiverse_manager import MultiverseManager
from ..core.config_manager import MultiverseConfig
from ..quantum.quantum_branching_engine import QuantumBranchingEngine
from ..dimensional.dimensional_portal_generator import DimensionalPortalGenerator
from ..analysis.alternate_reality_detector import AlternateRealityDetector


class BasicMultiverseDemo:
    """
    Basic demonstration of multiverse framework capabilities.
    
    Shows fundamental operations like universe creation, branching,
    portal generation, and reality detection.
    """
    
    def __init__(self):
        """Initialize the demo."""
        self.logger = logging.getLogger("multiverse.demo.basic")
        self.setup_logging()
        
        # Core components
        self.config = MultiverseConfig()
        self.multiverse_manager = None
        self.quantum_engine = None
        self.portal_generator = None
        self.reality_detector = None
    
    def setup_logging(self):
        """Setup logging for the demo."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def run_demo(self):
        """Run the complete basic multiverse demonstration."""
        print("🌌 Basic Multiverse Framework Demo")
        print("=" * 50)
        
        try:
            # Initialize components
            self._initialize_components()
            
            # Demonstrate core operations
            self._demo_universe_operations()
            self._demo_quantum_branching()
            self._demo_dimensional_portals()
            self._demo_reality_detection()
            self._demo_multiverse_statistics()
            
            print("\n✨ Demo completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Demo failed: {e}")
            raise
        finally:
            self._cleanup()
    
    def _initialize_components(self):
        """Initialize multiverse components."""
        print("\n🔧 Initializing multiverse components...")
        
        # Initialize multiverse manager
        self.multiverse_manager = MultiverseManager(self.config)
        print("✓ Multiverse manager initialized")
        
        # Initialize quantum branching engine
        self.quantum_engine = QuantumBranchingEngine(self.multiverse_manager)
        self.quantum_engine.start()
        print("✓ Quantum branching engine started")
        
        # Initialize portal generator
        self.portal_generator = DimensionalPortalGenerator(self.multiverse_manager)
        self.portal_generator.start()
        print("✓ Dimensional portal generator started")
        
        # Initialize reality detector
        self.reality_detector = AlternateRealityDetector(self.multiverse_manager)
        self.reality_detector.start()
        print("✓ Alternate reality detector started")
        
        time.sleep(2)  # Allow initialization to complete
    
    def _demo_universe_operations(self):
        """Demonstrate basic universe operations."""
        print("\n🌍 Demonstrating universe operations...")
        
        # List initial universes
        universes = self.multiverse_manager.list_universes()
        print(f"Initial universes: {len(universes)}")
        
        # Create additional universes by branching
        primary_universe_id = None
        for universe_id, info in universes.items():
            if info.get('is_primary', False):
                primary_universe_id = universe_id
                break
        
        if primary_universe_id:
            print(f"Primary universe: {primary_universe_id}")
            
            # Create branches
            branch1_id = self.multiverse_manager.branch_universe(
                primary_universe_id, quantum_deviation=0.1
            )
            branch2_id = self.multiverse_manager.branch_universe(
                primary_universe_id, quantum_deviation=0.2
            )
            
            print(f"Created branch 1: {branch1_id}")
            print(f"Created branch 2: {branch2_id}")
            
            # Switch between universes
            if branch1_id:
                success = self.multiverse_manager.switch_universe(branch1_id)
                print(f"Switched to branch 1: {'✓' if success else '✗'}")
                
                # Switch back
                success = self.multiverse_manager.switch_universe(primary_universe_id)
                print(f"Switched back to primary: {'✓' if success else '✗'}")
        
        # Show final universe count
        universes = self.multiverse_manager.list_universes()
        print(f"Final universes: {len(universes)}")
    
    def _demo_quantum_branching(self):
        """Demonstrate quantum branching operations."""
        print("\n⚛️ Demonstrating quantum branching...")
        
        # Get primary universe
        universes = self.multiverse_manager.list_universes()
        primary_universe_id = None
        for universe_id, info in universes.items():
            if info.get('is_primary', False):
                primary_universe_id = universe_id
                break
        
        if primary_universe_id:
            # Simulate quantum measurement branching
            universe = self.multiverse_manager.get_universe(primary_universe_id)
            if universe and universe.quantum_state:
                
                # Create observable for measurement
                import numpy as np
                observable = np.array([[1, 0], [0, -1]])  # Pauli-Z
                
                # Simulate quantum measurement branching
                branching_event = self.quantum_engine.simulate_quantum_measurement_branching(
                    primary_universe_id,
                    universe.quantum_state,
                    observable,
                    consciousness_factor=1.0
                )
                
                if branching_event:
                    print(f"Quantum branching event: {branching_event.event_id}")
                    print(f"Created {len(branching_event.branch_universe_ids)} branches")
                    print(f"Branching probability: {branching_event.branching_probability:.3f}")
                else:
                    print("No quantum branching occurred")
                
                # Simulate decoherence branching
                decoherence_event = self.quantum_engine.simulate_decoherence_branching(
                    primary_universe_id,
                    universe.quantum_state,
                    environment_interaction_strength=0.8
                )
                
                if decoherence_event:
                    print(f"Decoherence event: {decoherence_event.event_id}")
                    print(f"Created {len(decoherence_event.branch_universe_ids)} branches")
                else:
                    print("No decoherence branching occurred")
    
    def _demo_dimensional_portals(self):
        """Demonstrate dimensional portal operations."""
        print("\n🌀 Demonstrating dimensional portals...")
        
        # Get available universes
        universes = list(self.multiverse_manager.list_universes().keys())
        
        if len(universes) >= 2:
            origin_universe = universes[0]
            destination_universe = universes[1]
            
            # Generate portal
            portal_id = self.portal_generator.generate_portal(
                origin_universe,
                destination_universe,
                origin_position=(0, 0, 0),
                destination_position=(10, 10, 10),
                aperture_radius=2.0,
                lifetime=300.0  # 5 minutes
            )
            
            if portal_id:
                print(f"Portal generated: {portal_id}")
                
                # Get portal status
                status = self.portal_generator.get_portal_status(portal_id)
                if status:
                    print(f"Portal state: {status['state']}")
                    print(f"Stability rating: {status['stability_rating']:.3f}")
                    print(f"Energy level: {status['energy_level']:.3f}")
                    print(f"Operational: {status['operational']}")
                
                # Activate portal
                success = self.portal_generator.activate_portal(portal_id)
                print(f"Portal activation: {'✓' if success else '✗'}")
                
                # Simulate transit
                if success:
                    transit_success = self.portal_generator.simulate_transit(
                        portal_id, mass=70.0  # 70kg human
                    )
                    print(f"Transit simulation: {'✓' if transit_success else '✗'}")
                
                # Close portal
                self.portal_generator.close_portal(portal_id)
                print("Portal closed")
            else:
                print("Portal generation failed")
        else:
            print("Insufficient universes for portal demo")
    
    def _demo_reality_detection(self):
        """Demonstrate reality detection and analysis."""
        print("\n🔍 Demonstrating reality detection...")
        
        # Allow detector to scan
        time.sleep(5)
        
        # Get universes for analysis
        universes = self.multiverse_manager.list_universes()
        
        analyzed_count = 0
        for universe_id in universes.keys():
            # Generate reality signature
            signature = self.reality_detector.generate_reality_signature(universe_id)
            
            if signature:
                print(f"Reality signature for {universe_id[:8]}...")
                print(f"  Classification: {signature.reality_classification.value}")
                print(f"  Similarity to baseline: {signature.similarity_score:.3f}")
                print(f"  Stability index: {signature.stability_index:.3f}")
                analyzed_count += 1
            
            if analyzed_count >= 3:  # Limit output
                break
        
        # Get detector statistics
        stats = self.reality_detector.get_detector_statistics()
        print(f"\nReality detector statistics:")
        print(f"  Total signatures: {stats['total_signatures']}")
        print(f"  Alternate realities: {stats['alternate_realities_detected']}")
        print(f"  Anomaly count: {stats['anomaly_count']}")
    
    def _demo_multiverse_statistics(self):
        """Show comprehensive multiverse statistics."""
        print("\n📊 Multiverse statistics...")
        
        # Multiverse manager stats
        mv_stats = self.multiverse_manager.get_multiverse_statistics()
        print(f"Multiverse Manager:")
        print(f"  Total universes: {mv_stats['total_universes']}")
        print(f"  Active universe: {mv_stats['active_universe']}")
        print(f"  Average entropy: {mv_stats['average_entropy']:.3f}")
        print(f"  Universe states: {mv_stats['universe_states']}")
        
        # Quantum engine stats
        qe_stats = self.quantum_engine.get_branching_statistics()
        print(f"\nQuantum Branching Engine:")
        print(f"  Branching events: {qe_stats['total_branching_events']}")
        print(f"  Branches created: {qe_stats['total_branches_created']}")
        print(f"  Average rate: {qe_stats['average_branching_rate']:.3f}/s")
        
        # Portal generator stats
        pg_stats = self.portal_generator.get_generator_statistics()
        print(f"\nPortal Generator:")
        print(f"  Portals created: {pg_stats['total_portals_created']}")
        print(f"  Active portals: {pg_stats['active_portals']}")
        print(f"  Successful transits: {pg_stats['successful_transits']}")
        print(f"  Energy available: {pg_stats['total_energy_available']:.2e} J")
        
        # Reality detector stats
        rd_stats = self.reality_detector.get_detector_statistics()
        print(f"\nReality Detector:")
        print(f"  Signatures generated: {rd_stats['total_signatures']}")
        print(f"  Reality classifications: {rd_stats['reality_classifications']}")
        print(f"  Baseline established: {rd_stats['baseline_established']}")
    
    def _cleanup(self):
        """Cleanup demo components."""
        print("\n🧹 Cleaning up...")
        
        try:
            if self.reality_detector and self.reality_detector.is_running:
                self.reality_detector.stop()
            
            if self.portal_generator and self.portal_generator.is_running:
                self.portal_generator.stop()
            
            if self.quantum_engine and self.quantum_engine.is_running:
                self.quantum_engine.stop()
            
            if self.multiverse_manager:
                self.multiverse_manager.shutdown()
            
            print("✓ Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


if __name__ == "__main__":
    demo = BasicMultiverseDemo()
    demo.run_demo()