#!/usr/bin/env python3
"""
Simple test script for the Reality Manipulation Simulation Framework
"""

import sys
import os
import asyncio

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_individual_modules():
    """Test individual modules first"""
    print("Testing Reality Manipulation Framework (SIMULATION ONLY)")
    print("=" * 60)
    print("DISCLAIMER: All operations are simulated - no actual reality manipulation")
    print()
    
    # Test physics simulator
    try:
        from physics import PhysicsSimulator
        
        class MockEngine:
            pass
        
        physics = PhysicsSimulator(MockEngine())
        print("✓ Physics Simulator loaded successfully")
        
        # Test a simple operation
        result = await physics.modify_physics_law({
            "law": "gravity",
            "modification_type": "scaling", 
            "value": 1.1
        })
        print(f"  Physics test: Success={result[0]}, Impact={result[1]:.3f}")
        
    except Exception as e:
        print(f"✗ Physics Simulator failed: {e}")
    
    # Test probability manipulator
    try:
        from probability import ProbabilityManipulator
        
        probability = ProbabilityManipulator(MockEngine())
        print("✓ Probability Manipulator loaded successfully")
        
        # Test probability operation
        result = await probability.alter_probability({
            "target_event": "coin_flip",
            "new_probability": 0.7
        })
        print(f"  Probability test: Success={result[0]}, Impact={result[1]:.3f}")
        
    except Exception as e:
        print(f"✗ Probability Manipulator failed: {e}")
    
    # Test matter simulator
    try:
        from matter import MatterSimulator
        
        matter = MatterSimulator(MockEngine())
        print("✓ Matter Simulator loaded successfully")
        
        # Test matter generation
        result = await matter.generate_matter({
            "matter_type": "ordinary_matter",
            "mass": 1e-27,
            "composition": {"protons": 1, "electrons": 1}
        })
        print(f"  Matter test: Success={result[0]}, Impact={result[1]:.3f}")
        
    except Exception as e:
        print(f"✗ Matter Simulator failed: {e}")
    
    # Test spacetime warper
    try:
        from spacetime import SpacetimeWarper
        
        spacetime = SpacetimeWarper(MockEngine())
        print("✓ Spacetime Warper loaded successfully")
        
        # Test spacetime warping
        result = await spacetime.warp_spacetime({
            "warp_type": "gravitational_well",
            "coordinates": [0, 0, 0, 0],
            "intensity": 1.0,
            "radius": 1000
        })
        print(f"  Spacetime test: Success={result[0]}, Impact={result[1]:.3f}")
        
    except Exception as e:
        print(f"✗ Spacetime Warper failed: {e}")
    
    # Test omnipotence framework
    try:
        from omnipotence import OmnipotenceFramework
        
        omnipotence = OmnipotenceFramework(MockEngine())
        print("✓ Omnipotence Framework loaded successfully")
        
        # Test omnipotence activation
        result = await omnipotence.activate_omnipotence({
            "action_type": "reality_rewrite",
            "target_aspect": "omnipotence",
            "power_investment": 1.0
        })
        print(f"  Omnipotence test: Success={result[0]}, Power={result[1]:.3f}")
        
    except Exception as e:
        print(f"✗ Omnipotence Framework failed: {e}")
    
    print()
    print("Individual module testing completed")
    print("All modules are SIMULATION ONLY - no actual reality was affected")

if __name__ == "__main__":
    asyncio.run(test_individual_modules())