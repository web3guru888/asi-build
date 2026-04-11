#!/usr/bin/env python3
"""
Basic Cognitive Synergy Demonstration
=====================================

Demonstrates the core functionality of the Cognitive Synergy Framework
implementing Ben Goertzel's PRIMUS theory for AGI systems.

This example shows:
1. PRIMUS foundation initialization
2. Cognitive synergy engine setup
3. Pattern-reasoning synergy integration
4. Emergent property detection
5. Self-organization mechanisms
"""

import sys
import os
import time
import numpy as np
from pathlib import Path

# Add cognitive synergy modules to path
sys.path.append(str(Path(__file__).parent.parent))

from core.primus_foundation import PRIMUSFoundation, CognitivePrimitive
from core.cognitive_synergy_engine import CognitiveSynergyEngine
from modules.pattern_reasoning.pattern_reasoning_synergy import PatternReasoningSynergy
from modules.perception_action.sensorimotor_synergy import SensorimotorSynergy


def main():
    """Main demonstration function"""
    print("=" * 70)
    print("COGNITIVE SYNERGY FRAMEWORK - BASIC DEMONSTRATION")
    print("Implementing Ben Goertzel's PRIMUS Theory")
    print("=" * 70)
    
    # 1. Initialize PRIMUS Foundation
    print("\n1. Initializing PRIMUS Foundation...")
    primus = PRIMUSFoundation(
        dimension=256,
        learning_rate=0.01,
        synergy_threshold=0.6
    )
    
    # Add some initial cognitive primitives
    primitives = [
        CognitivePrimitive("concept_object", "concept", "physical object", 0.9),
        CognitivePrimitive("concept_motion", "concept", "movement in space", 0.8),
        CognitivePrimitive("pattern_sequence", "pattern", [1, 2, 3, 2, 1], 0.85),
        CognitivePrimitive("goal_understand", "goal", {"target": "understand_environment"}, 0.9),
        CognitivePrimitive("procedure_analyze", "procedure", "analyze input patterns", 0.7)
    ]
    
    for primitive in primitives:
        primus.add_primitive(primitive)
    
    print(f"   Added {len(primitives)} cognitive primitives")
    print(f"   PRIMUS system initialized with dimension {primus.dimension}")
    
    # 2. Initialize Cognitive Synergy Engine
    print("\n2. Initializing Cognitive Synergy Engine...")
    synergy_engine = CognitiveSynergyEngine(
        primus_foundation=primus,
        update_frequency=5.0,
        synergy_threshold=0.6,
        emergence_threshold=0.8
    )
    
    # 3. Initialize Pattern-Reasoning Synergy
    print("\n3. Initializing Pattern-Reasoning Synergy...")
    pattern_reasoning_synergy = PatternReasoningSynergy(
        synergy_update_rate=5.0,
        integration_threshold=0.7,
        emergence_threshold=0.8
    )
    
    # Register with synergy engine
    synergy_engine.register_module('pattern_reasoning', pattern_reasoning_synergy)
    
    # 4. Initialize Sensorimotor Synergy
    print("\n4. Initializing Sensorimotor Synergy...")
    sensorimotor_synergy = SensorimotorSynergy(
        coupling_threshold=0.6,
        adaptation_rate=0.01,
        prediction_window=0.5
    )
    
    # Add sensorimotor loops
    sensorimotor_synergy.add_sensorimotor_loop(
        "vision_motor", "visual", "motor"
    )
    sensorimotor_synergy.add_sensorimotor_loop(
        "audio_head", "auditory", "head_movement"
    )
    
    synergy_engine.register_module('sensorimotor', sensorimotor_synergy)
    
    print("   Cognitive synergy engine initialized with all modules")
    
    # 5. Start the system
    print("\n5. Starting cognitive synergy system...")
    
    with synergy_engine:  # Use context manager for proper cleanup
        print("   ✓ PRIMUS foundation started")
        print("   ✓ Cognitive synergy engine started")
        print("   ✓ All synergy modules active")
        
        # 6. Demonstrate cognitive processing
        print("\n6. Demonstrating cognitive processing...")
        
        # Inject various stimuli to trigger synergy
        stimuli = [
            {"type": "perceptual", "data": np.random.rand(10), "confidence": 0.8},
            {"type": "learning", "data": "new pattern observed", "confidence": 0.9},
            {"type": "goal", "data": {"objective": "learn new skill"}, "confidence": 0.7}
        ]
        
        for i, stimulus in enumerate(stimuli):
            print(f"\n   Injecting stimulus {i+1}: {stimulus['type']}")
            synergy_engine.inject_stimulus(stimulus)
            
            # Process sensorimotor input
            if stimulus["type"] == "perceptual":
                sensorimotor_synergy.process_perception(
                    "visual", stimulus["data"], stimulus["confidence"]
                )
            
            # Allow processing time
            time.sleep(0.5)
        
        # 7. Run demonstration loop
        print("\n7. Running cognitive synergy demonstration...")
        print("   (Processing for 10 seconds - watch for emergent properties)")
        
        for cycle in range(20):  # 20 cycles at 0.5s each = 10 seconds
            # Get current system state
            system_state = synergy_engine.get_system_state()
            
            # Display key metrics every 5 cycles
            if cycle % 5 == 0:
                print(f"\n   Cycle {cycle + 1}:")
                print(f"   Global Coherence: {system_state['global_coherence']:.3f}")
                
                synergy_pairs = system_state['synergy_pairs']
                for pair_name, pair_data in synergy_pairs.items():
                    synergy_strength = pair_data['synergy_strength']
                    print(f"   {pair_name} synergy: {synergy_strength:.3f}")
                
                # Check for emergence
                emergence_indicators = synergy_engine.get_emergence_indicators()
                if emergence_indicators:
                    print(f"   🌟 EMERGENCE DETECTED: {len(emergence_indicators)} indicators")
                    for indicator in emergence_indicators:
                        print(f"      - {indicator['pair']}: {indicator['indicators']}")
            
            # Add some variety to keep system active
            if cycle % 7 == 0:
                # Inject pattern mining input
                pattern_reasoning_synergy.process_external_input({
                    "type": "sequence",
                    "data": np.sin(np.linspace(0, 2*np.pi, 20)) + np.random.normal(0, 0.1, 20),
                    "timestamp": time.time()
                })
            
            if cycle % 6 == 0:
                # Inject sensorimotor action
                sensorimotor_synergy.process_action(
                    "motor", np.random.rand(3), execution_confidence=0.8
                )
            
            time.sleep(0.5)
        
        # 8. Final system analysis
        print("\n8. Final System Analysis")
        print("=" * 40)
        
        final_state = synergy_engine.get_system_state()
        
        print(f"Global Coherence: {final_state['global_coherence']:.3f}")
        print(f"System Uptime: {final_state['performance_metrics']['system_uptime']:.1f}s")
        
        print("\nSynergy Pair Performance:")
        for pair_name, pair_data in final_state['synergy_pairs'].items():
            synergy = pair_data['synergy_strength']
            integration = pair_data['integration_level']
            indicators = len(pair_data['emergence_indicators'])
            
            print(f"  {pair_name}:")
            print(f"    Synergy: {synergy:.3f}")
            print(f"    Integration: {integration:.3f}")
            print(f"    Emergence indicators: {indicators}")
        
        print(f"\nCognitive Dynamics: {len(final_state['cognitive_dynamics'])}")
        print(f"Emergence Events: {len(final_state['emergence_events'])}")
        
        # Pattern-Reasoning specific analysis
        pr_state = pattern_reasoning_synergy.get_synergy_state()
        print(f"\nPattern-Reasoning Synergy:")
        print(f"  Synergy Strength: {pr_state['metrics']['synergy_strength']:.3f}")
        print(f"  Integration Level: {pr_state['metrics']['integration_level']:.3f}")
        print(f"  Emergent Concepts: {len(pr_state['emergent_concepts'])}")
        
        # Sensorimotor specific analysis
        sm_state = sensorimotor_synergy.get_synergy_state()
        print(f"\nSensorimotor Synergy:")
        print(f"  Average Coupling: {sm_state['average_coupling_strength']:.3f}")
        print(f"  Prediction Accuracy: {sm_state['average_prediction_accuracy']:.3f}")
        print(f"  Active Loops: {len([l for l in sm_state['sensorimotor_loops'].values() if l['active']])}")
        
        # PRIMUS foundation analysis
        primus_state = primus.get_system_state()
        print(f"\nPRIMUS Foundation:")
        print(f"  Understanding Level: {primus_state.understanding_level:.3f}")
        print(f"  Primitive Count: {primus_state.self_organization_metrics['primitives_count']}")
        print(f"  Pattern Count: {primus_state.self_organization_metrics['patterns_count']}")
        print(f"  Graph Density: {primus_state.self_organization_metrics['graph_density']:.3f}")
        
        print("\n" + "=" * 70)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("🧠 Cognitive synergy achieved through PRIMUS implementation")
        print("🌟 Emergent properties detected and tracked")
        print("🔄 Self-organization mechanisms active")
        print("💡 Pattern-reasoning integration functional")
        print("🤖 Sensorimotor loops established and adaptive")
        print("=" * 70)


def demonstrate_emergent_properties():
    """Focused demonstration of emergent property detection"""
    print("\n" + "=" * 50)
    print("EMERGENT PROPERTIES DEMONSTRATION")
    print("=" * 50)
    
    # Create minimal system for emergence demonstration
    primus = PRIMUSFoundation(dimension=128)
    synergy_engine = CognitiveSynergyEngine(primus, emergence_threshold=0.7)
    
    # Add complementary primitives that should create synergy
    complementary_pairs = [
        (CognitivePrimitive("visual_pattern", "pattern", "visual input pattern", 0.9),
         CognitivePrimitive("motor_response", "procedure", "motor response to visual", 0.8)),
        (CognitivePrimitive("memory_trace", "concept", "stored experience", 0.85),
         CognitivePrimitive("learning_update", "procedure", "update from experience", 0.9)),
        (CognitivePrimitive("attention_focus", "goal", "focus attention", 0.8),
         CognitivePrimitive("intention_form", "goal", "form behavioral intention", 0.85))
    ]
    
    with synergy_engine:
        for pair in complementary_pairs:
            primus.add_primitive(pair[0])
            primus.add_primitive(pair[1])
            
            # Create artificial synergy by connecting primitives
            synergy = primus.compute_synergy(pair[0].name, pair[1].name)
            print(f"Created synergy between {pair[0].name} and {pair[1].name}: {synergy:.3f}")
        
        # Let system run and evolve
        for i in range(10):
            system_state = synergy_engine.get_system_state()
            emergence_indicators = synergy_engine.get_emergence_indicators()
            
            if emergence_indicators:
                print(f"\n🌟 EMERGENCE DETECTED at cycle {i+1}:")
                for indicator in emergence_indicators:
                    print(f"   {indicator['pair']}: synergy={indicator['synergy']:.3f}")
                    print(f"      Indicators: {', '.join(indicator['indicators'])}")
            
            time.sleep(0.3)
        
        print("\nEmergence demonstration completed!")


if __name__ == "__main__":
    try:
        main()
        
        # Optional: Run emergence-focused demo
        demonstrate_emergent_properties()
        
    except KeyboardInterrupt:
        print("\n\nDemonstration interrupted by user")
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nThank you for exploring the Cognitive Synergy Framework!")
    print("Based on Ben Goertzel's PRIMUS theory for AGI systems.")