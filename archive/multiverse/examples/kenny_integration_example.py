"""
Kenny Integration Example
========================

Demonstrates how Kenny AI system integrates with the multiverse framework
for reality-aware automation and interdimensional task execution.
"""

import time
import logging
from typing import Dict, Any, List

from ..integration.kenny_multiverse_integration import KennyMultiverseIntegration
from ..core.multiverse_manager import MultiverseManager
from ..core.config_manager import MultiverseConfig


class MockKennyAgent:
    """Mock Kenny agent for demonstration purposes."""
    
    def __init__(self):
        """Initialize mock Kenny agent."""
        self.current_task = None
        self.task_history = []
        self.universe_context = {}
        
    def execute_task(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task (mock implementation)."""
        self.current_task = task_config
        
        # Simulate task execution
        time.sleep(0.1)
        
        result = {
            'status': 'completed',
            'task_type': task_config.get('type', 'unknown'),
            'result_data': f"Task executed in universe context",
            'execution_time': 0.1,
            'success': True
        }
        
        self.task_history.append(result)
        return result
    
    def on_universe_changed(self, old_universe: str, new_universe: str, context: Dict[str, Any]):
        """Handle universe change notification."""
        self.universe_context = context
        print(f"Kenny: Universe changed from {old_universe[:8]}... to {new_universe[:8]}...")
        print(f"  New reality stability: {context.get('reality_stability', 0):.3f}")
        print(f"  Quantum purity: {context.get('quantum_purity', 0):.3f}")


class KennyIntegrationExample:
    """
    Comprehensive example of Kenny's integration with the multiverse framework.
    
    Demonstrates reality-aware automation, quantum decision making,
    and interdimensional task execution capabilities.
    """
    
    def __init__(self):
        """Initialize the integration example."""
        self.logger = logging.getLogger("multiverse.example.kenny")
        self.setup_logging()
        
        # Components
        self.kenny_agent = MockKennyAgent()
        self.multiverse_manager = None
        self.kenny_integration = None
    
    def setup_logging(self):
        """Setup logging for the example."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def run_demo(self):
        """Run the complete Kenny integration demonstration."""
        print("🤖 Kenny Multiverse Integration Demo")
        print("=" * 50)
        
        try:
            # Initialize components
            self._initialize_components()
            
            # Demonstrate integration features
            self._demo_universe_awareness()
            self._demo_quantum_decision_making()
            self._demo_dimensional_task_execution()
            self._demo_reality_monitoring()
            self._demo_automatic_universe_switching()
            self._demo_integration_statistics()
            
            print("\n🌟 Kenny integration demo completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Demo failed: {e}")
            raise
        finally:
            self._cleanup()
    
    def _initialize_components(self):
        """Initialize multiverse and integration components."""
        print("\n🔧 Initializing Kenny multiverse integration...")
        
        # Initialize multiverse
        config = MultiverseConfig()
        self.multiverse_manager = MultiverseManager(config)
        print("✓ Multiverse manager initialized")
        
        # Create some universe branches for testing
        universes = self.multiverse_manager.list_universes()
        primary_universe_id = None
        for universe_id, info in universes.items():
            if info.get('is_primary', False):
                primary_universe_id = universe_id
                break
        
        if primary_universe_id:
            # Create test branches
            branch1 = self.multiverse_manager.branch_universe(primary_universe_id, 0.1)
            branch2 = self.multiverse_manager.branch_universe(primary_universe_id, 0.2)
            branch3 = self.multiverse_manager.branch_universe(primary_universe_id, 0.3)
            print(f"✓ Created test universe branches: {len([branch1, branch2, branch3])} branches")
        
        # Initialize Kenny integration
        self.kenny_integration = KennyMultiverseIntegration(self.kenny_agent)
        self.kenny_integration.start()
        print("✓ Kenny multiverse integration started")
        
        time.sleep(2)  # Allow initialization to complete
    
    def _demo_universe_awareness(self):
        """Demonstrate Kenny's universe awareness capabilities."""
        print("\n🌍 Demonstrating universe awareness...")
        
        # Show current universe context
        status = self.kenny_integration.get_integration_status()
        current_universe = status['kenny_multiverse_integration']['current_universe']
        reality_context = status['kenny_multiverse_integration']['reality_context']
        
        print(f"Kenny's current universe: {current_universe}")
        print(f"Reality context:")
        for key, value in reality_context.items():
            if key != 'last_updated':
                print(f"  {key}: {value}")
        
        # Show available universes
        universes = self.multiverse_manager.list_universes()
        print(f"\nAvailable universes: {len(universes)}")
        for i, (universe_id, info) in enumerate(universes.items()):
            if i < 5:  # Limit output
                print(f"  {universe_id[:12]}... - {info['state']} (prob: {info['probability']:.3f})")
    
    def _demo_quantum_decision_making(self):
        """Demonstrate quantum-enhanced decision making."""
        print("\n⚛️ Demonstrating quantum decision making...")
        
        # Create decision scenario
        decision_options = [
            {
                'action': 'click_button_A',
                'probability': 0.6,
                'expected_outcome': 'success',
                'risk_level': 0.2
            },
            {
                'action': 'click_button_B',
                'probability': 0.4,
                'expected_outcome': 'partial_success',
                'risk_level': 0.1
            },
            {
                'action': 'wait_and_observe',
                'probability': 0.8,
                'expected_outcome': 'gather_information',
                'risk_level': 0.05
            }
        ]
        
        context = {
            'task_type': 'ui_automation',
            'urgency': 'medium',
            'complexity': 'high'
        }
        
        print("Decision scenario: UI automation task with multiple options")
        for i, option in enumerate(decision_options):
            print(f"  Option {i+1}: {option['action']} (prob: {option['probability']})")
        
        # Make quantum decision
        decision = self.kenny_integration.make_quantum_decision(decision_options, context)
        
        print(f"\nQuantum decision result:")
        print(f"  Selected action: {decision.get('action', 'unknown')}")
        print(f"  Quantum score: {decision.get('quantum_score', 0):.3f}")
        print(f"  Confidence: {decision.get('confidence', 0):.3f}")
        
        # Show decision history
        stats = self.kenny_integration.get_integration_status()
        decisions_made = stats['kenny_multiverse_integration']['statistics']['quantum_decisions']
        print(f"  Total quantum decisions made: {decisions_made}")
    
    def _demo_dimensional_task_execution(self):
        """Demonstrate cross-dimensional task execution."""
        print("\n🌀 Demonstrating dimensional task execution...")
        
        # Get available universes
        universes = list(self.multiverse_manager.list_universes().keys())
        
        if len(universes) >= 2:
            # Create dimensional task
            task_config = {
                'type': 'screen_analysis',
                'action': 'analyze_ui_elements',
                'universes': universes[:3],  # Execute in first 3 universes
                'parameters': {
                    'region': {'x': 0, 'y': 0, 'width': 1920, 'height': 1080},
                    'analysis_depth': 'comprehensive'
                },
                'timeout': 60
            }
            
            print(f"Executing task across {len(task_config['universes'])} universes...")
            
            # Execute dimensional task
            task_id = self.kenny_integration.execute_dimensional_task(task_config)
            
            if task_id:
                print(f"Dimensional task started: {task_id}")
                
                # Wait for task completion
                print("Waiting for task completion...")
                time.sleep(3)
                
                # Check task status
                active_tasks = self.kenny_integration.active_dimensional_tasks
                if task_id in active_tasks:
                    task = active_tasks[task_id]
                    print(f"Task status: {task['status']}")
                    print(f"Results from {len(task['results'])} universes")
                    print(f"Errors in {len(task['errors'])} universes")
                else:
                    print("Task completed and cleaned up")
                
                # Show statistics
                stats = self.kenny_integration.get_integration_status()
                tasks_completed = stats['kenny_multiverse_integration']['statistics']['dimensional_tasks']
                print(f"Total dimensional tasks completed: {tasks_completed}")
            else:
                print("Failed to start dimensional task")
        else:
            print("Insufficient universes for dimensional task demo")
    
    def _demo_reality_monitoring(self):
        """Demonstrate reality monitoring and anomaly detection."""
        print("\n🔍 Demonstrating reality monitoring...")
        
        # Show current reality monitoring status
        status = self.kenny_integration.get_integration_status()
        monitoring_active = status['kenny_multiverse_integration']['monitoring_active']
        print(f"Reality monitoring active: {monitoring_active}")
        
        # Show reality statistics
        reality_context = status['kenny_multiverse_integration']['reality_context']
        if reality_context:
            stability = reality_context.get('reality_stability', 0)
            quantum_purity = reality_context.get('quantum_purity', 0)
            entropy = reality_context.get('entropy', 0)
            
            print(f"Current reality metrics:")
            print(f"  Stability: {stability:.3f}")
            print(f"  Quantum purity: {quantum_purity:.3f}")
            print(f"  Entropy: {entropy:.3f}")
            
            # Interpret stability
            if stability > 0.8:
                print("  Status: Reality is stable ✓")
            elif stability > 0.5:
                print("  Status: Reality showing minor fluctuations ⚠️")
            else:
                print("  Status: Reality unstable - monitoring closely ⚠️")
        
        # Show anomaly statistics
        anomalies = status['kenny_multiverse_integration']['statistics']['reality_anomalies']
        print(f"Reality anomalies detected: {anomalies}")
    
    def _demo_automatic_universe_switching(self):
        """Demonstrate automatic universe switching for stability."""
        print("\n🔄 Demonstrating automatic universe switching...")
        
        # Get available universes
        universes = list(self.multiverse_manager.list_universes().keys())
        current_universe = self.kenny_integration.current_universe_id
        
        print(f"Current universe: {current_universe}")
        print(f"Available universes: {len(universes)}")
        
        # Test manual universe switching
        if len(universes) > 1:
            # Find different universe
            target_universe = None
            for universe_id in universes:
                if universe_id != current_universe:
                    target_universe = universe_id
                    break
            
            if target_universe:
                print(f"Switching to universe: {target_universe[:12]}...")
                
                success = self.kenny_integration.switch_universe(target_universe, "demo_test")
                
                if success:
                    print("✓ Universe switch successful")
                    
                    # Show new context
                    time.sleep(1)
                    status = self.kenny_integration.get_integration_status()
                    new_universe = status['kenny_multiverse_integration']['current_universe']
                    print(f"New current universe: {new_universe}")
                    
                    # Switch back
                    print("Switching back to original universe...")
                    self.kenny_integration.switch_universe(current_universe, "demo_return")
                    print("✓ Returned to original universe")
                else:
                    print("✗ Universe switch failed")
        
        # Show switch statistics
        stats = self.kenny_integration.get_integration_status()
        switches = stats['kenny_multiverse_integration']['statistics']['universe_switches']
        print(f"Total universe switches: {switches}")
    
    def _demo_integration_statistics(self):
        """Show comprehensive integration statistics."""
        print("\n📊 Integration statistics...")
        
        # Get full integration status
        status = self.kenny_integration.get_integration_status()
        integration_data = status['kenny_multiverse_integration']
        
        print("Kenny Multiverse Integration Status:")
        print(f"  Current universe: {integration_data['current_universe']}")
        print(f"  Monitoring active: {integration_data['monitoring_active']}")
        print(f"  Auto-switch enabled: {integration_data['auto_switch_enabled']}")
        
        stats = integration_data['statistics']
        print(f"\nOperational Statistics:")
        print(f"  Universe switches: {stats['universe_switches']}")
        print(f"  Quantum decisions: {stats['quantum_decisions']}")
        print(f"  Dimensional tasks: {stats['dimensional_tasks']}")
        print(f"  Reality anomalies: {stats['reality_anomalies']}")
        
        config = integration_data['integration_config']
        print(f"\nConfiguration:")
        print(f"  Reality awareness: {config['reality_awareness']}")
        print(f"  Quantum decisions: {config['quantum_decisions']}")
        print(f"  Dimensional tasks: {config['dimensional_tasks']}")
        print(f"  Temporal navigation: {config['temporal_navigation']}")
        
        # Kenny agent statistics
        print(f"\nKenny Agent:")
        print(f"  Tasks executed: {len(self.kenny_agent.task_history)}")
        print(f"  Current task: {self.kenny_agent.current_task is not None}")
        print(f"  Universe context keys: {list(self.kenny_agent.universe_context.keys())}")
    
    def _cleanup(self):
        """Cleanup demo components."""
        print("\n🧹 Cleaning up integration demo...")
        
        try:
            if self.kenny_integration and self.kenny_integration.is_running:
                self.kenny_integration.stop()
            
            if self.multiverse_manager:
                self.multiverse_manager.shutdown()
            
            print("✓ Integration demo cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


if __name__ == "__main__":
    demo = KennyIntegrationExample()
    demo.run_demo()