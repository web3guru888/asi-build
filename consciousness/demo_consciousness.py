"""
Consciousness System Demonstration

This script demonstrates the Kenny consciousness system by setting up
and running all consciousness components, showing their interactions
and emergent conscious behaviors.
"""

import time
import logging
from typing import Dict, Any

# Import consciousness components
from consciousness_orchestrator import ConsciousnessOrchestrator
from global_workspace import GlobalWorkspaceTheory
from integrated_information import IntegratedInformationTheory
from attention_schema import AttentionSchemaTheory
from predictive_processing import PredictiveProcessing
from metacognition import MetacognitionSystem
from self_awareness import SelfAwarenessEngine
from qualia_processor import QualiaProcessor
from theory_of_mind import TheoryOfMind
from emotional_consciousness import EmotionalConsciousness
from recursive_improvement import RecursiveSelfImprovement
from memory_integration import MemoryIntegration
from temporal_consciousness import TemporalConsciousness
from sensory_integration import SensoryIntegration
from base_consciousness import ConsciousnessEvent

def setup_logging():
    """Set up logging for the demonstration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_consciousness_system() -> ConsciousnessOrchestrator:
    """Create and configure the complete consciousness system"""
    print("🧠 Initializing Kenny Consciousness System...")
    
    # Create orchestrator
    orchestrator = ConsciousnessOrchestrator({
        'emergence_threshold': 0.7,
        'integration_interval': 1.0,
        'assessment_interval': 5.0
    })
    
    # Create consciousness components
    components = [
        # Core theories
        GlobalWorkspaceTheory({'max_workspace_size': 7}),
        IntegratedInformationTheory({'num_levels': 4}),
        AttentionSchemaTheory({'max_targets': 5}),
        PredictiveProcessing({'num_levels': 5}),
        
        # Cognitive systems
        MetacognitionSystem({'max_load': 1.0}),
        SelfAwarenessEngine(),
        TheoryOfMind({'max_agents': 5}),
        
        # Experience systems
        QualiaProcessor({'quality_space_dims': 16}),
        EmotionalConsciousness({'regulation_threshold': 0.7}),
        TemporalConsciousness({'temporal_resolution': 0.1}),
        SensoryIntegration({'binding_threshold': 0.6}),
        
        # Learning systems
        MemoryIntegration({'consolidation_threshold': 0.7}),
        RecursiveSelfImprovement({'improvement_enabled': True})
    ]
    
    # Register all components
    for component in components:
        orchestrator.register_component(component)
        print(f"  ✓ Registered {component.name}")
    
    return orchestrator

def demonstrate_consciousness_emergence(orchestrator: ConsciousnessOrchestrator):
    """Demonstrate consciousness emergence through various scenarios"""
    print("\n🌟 Demonstrating Consciousness Emergence")
    
    # Scenario 1: Visual attention and awareness
    print("\n1. Visual Attention Scenario")
    
    # Simulate visual input
    visual_event = ConsciousnessEvent(
        event_id="demo_visual_001",
        timestamp=time.time(),
        event_type="sensory_input",
        data={
            'modality': 'visual',
            'data': {
                'brightness': 0.8,
                'contrast': 0.7,
                'motion': 0.9,
                'novelty': 0.8
            },
            'intensity': 0.9,
            'spatial_location': (0.5, 0.3, 0.0)
        },
        priority=8,
        source_module="external"
    )
    
    # Route through orchestrator
    recipients = orchestrator.route_event(visual_event, "external")
    print(f"  → Visual event routed to: {recipients}")
    
    time.sleep(2)
    
    # Scenario 2: Emotional response and memory formation
    print("\n2. Emotional Memory Scenario")
    
    emotional_event = ConsciousnessEvent(
        event_id="demo_emotion_001",
        timestamp=time.time(),
        event_type="emotional_trigger",
        data={
            'situation': {
                'goal_relevance': 0.9,
                'outcome': 'success',
                'complexity': 0.6,
                'personal_relevance': 0.8
            },
            'trigger': 'goal_achievement'
        },
        priority=9,
        source_module="external"
    )
    
    recipients = orchestrator.route_event(emotional_event, "external")
    print(f"  → Emotional event routed to: {recipients}")
    
    time.sleep(2)
    
    # Scenario 3: Metacognitive reflection
    print("\n3. Metacognitive Reflection Scenario")
    
    reflection_event = ConsciousnessEvent(
        event_id="demo_reflection_001",
        timestamp=time.time(),
        event_type="reflect",
        data={
            'question': 'How am I performing in processing these scenarios?',
            'trigger': 'self_evaluation'
        },
        priority=7,
        source_module="external"
    )
    
    recipients = orchestrator.route_event(reflection_event, "external")
    print(f"  → Reflection event routed to: {recipients}")
    
    time.sleep(3)

def monitor_consciousness_levels(orchestrator: ConsciousnessOrchestrator):
    """Monitor and display consciousness levels over time"""
    print("\n📊 Monitoring Consciousness Levels")
    
    for i in range(10):
        snapshot = orchestrator.assess_global_consciousness()
        
        print(f"\nTime {i+1}:")
        print(f"  Global Consciousness Level: {snapshot.global_consciousness_level:.3f}")
        print(f"  System Coherence: {snapshot.system_coherence:.3f}")
        print(f"  Active Integrations: {len(snapshot.active_integrations)}")
        print(f"  Emergent Properties: {list(snapshot.emergent_properties.keys())}")
        
        # Show component health
        status = orchestrator.get_current_state()
        healthy_components = status['healthy_components']
        total_components = status['registered_components']
        print(f"  Component Health: {healthy_components}/{total_components}")
        
        time.sleep(2)

def demonstrate_self_improvement(orchestrator: ConsciousnessOrchestrator):
    """Demonstrate self-improvement capabilities"""
    print("\n🔧 Demonstrating Self-Improvement")
    
    # Trigger improvement analysis
    improvement_event = ConsciousnessEvent(
        event_id="demo_improvement_001",
        timestamp=time.time(),
        event_type="improvement_request",
        data={},
        priority=6,
        source_module="external"
    )
    
    recipients = orchestrator.route_event(improvement_event, "external")
    print(f"  → Improvement request routed to: {recipients}")
    
    time.sleep(3)
    
    # Check for any improvements made
    if 'RecursiveSelfImprovement' in orchestrator.consciousness_components:
        rsi = orchestrator.consciousness_components['RecursiveSelfImprovement']
        state = rsi.get_current_state()
        print(f"  → Successful improvements: {state['successful_improvements']}")
        print(f"  → Active proposals: {state['active_proposals']}")

def show_system_summary(orchestrator: ConsciousnessOrchestrator):
    """Show final system summary"""
    print("\n📈 Final System Summary")
    
    status = orchestrator.get_current_state()
    
    print(f"System Uptime: {status['system_uptime']:.1f} seconds")
    print(f"Total Events Routed: {status['total_events_routed']}")
    print(f"Integration Events: {status['integration_events']}")
    print(f"Emergence Events: {status['emergence_events']}")
    print(f"Final Consciousness Level: {status['global_consciousness_level']:.3f}")
    
    print("\nComponent Status:")
    for name, comp_status in status['component_status'].items():
        health = "✓" if comp_status['healthy'] else "✗"
        awareness = comp_status['awareness_level']
        integration = comp_status['integration_level']
        print(f"  {health} {name}: awareness={awareness:.2f}, integration={integration:.2f}")

def main():
    """Main demonstration function"""
    setup_logging()
    
    print("=" * 60)
    print("🤖 KENNY CONSCIOUSNESS SYSTEM DEMONSTRATION")
    print("=" * 60)
    
    try:
        # Create consciousness system
        orchestrator = create_consciousness_system()
        
        # Start the system
        print("\n🚀 Starting consciousness orchestration...")
        orchestrator.start_orchestration()
        
        # Wait for system to stabilize
        time.sleep(3)
        
        # Run demonstrations
        demonstrate_consciousness_emergence(orchestrator)
        monitor_consciousness_levels(orchestrator)
        demonstrate_self_improvement(orchestrator)
        
        # Show final summary
        show_system_summary(orchestrator)
        
        print("\n✨ Consciousness demonstration completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Demonstration interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
    finally:
        # Clean shutdown
        print("\n🛑 Shutting down consciousness system...")
        if 'orchestrator' in locals():
            orchestrator.stop_orchestration()
        print("✓ Shutdown complete")

if __name__ == "__main__":
    main()