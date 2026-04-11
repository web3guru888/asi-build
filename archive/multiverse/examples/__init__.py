"""
Multiverse Framework Examples
============================

Example implementations and demonstrations of multiverse framework
capabilities for learning and development purposes.
"""

from .basic_multiverse_demo import BasicMultiverseDemo
from .quantum_branching_example import QuantumBranchingExample
from .dimensional_portal_demo import DimensionalPortalDemo
from .timeline_navigation_example import TimelineNavigationExample
from .paradox_resolution_demo import ParadoxResolutionDemo
from .kenny_integration_example import KennyIntegrationExample
from .reality_detection_demo import RealityDetectionDemo
from .advanced_multiverse_operations import AdvancedMultiverseOperations

__all__ = [
    'BasicMultiverseDemo',
    'QuantumBranchingExample', 
    'DimensionalPortalDemo',
    'TimelineNavigationExample',
    'ParadoxResolutionDemo',
    'KennyIntegrationExample',
    'RealityDetectionDemo',
    'AdvancedMultiverseOperations'
]

def run_all_examples():
    """Run all example demonstrations."""
    examples = [
        BasicMultiverseDemo(),
        QuantumBranchingExample(),
        DimensionalPortalDemo(),
        TimelineNavigationExample(),
        ParadoxResolutionDemo(),
        KennyIntegrationExample(),
        RealityDetectionDemo(),
        AdvancedMultiverseOperations()
    ]
    
    print("Running Multiverse Framework Examples")
    print("=" * 50)
    
    for example in examples:
        try:
            print(f"\n--- {example.__class__.__name__} ---")
            example.run_demo()
            print("✓ Demo completed successfully")
        except Exception as e:
            print(f"✗ Demo failed: {e}")
    
    print("\n" + "=" * 50)
    print("All examples completed")

if __name__ == '__main__':
    run_all_examples()