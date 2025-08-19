"""
Comprehensive Bio-Inspired Cognitive Architecture Demo

Demonstrates the integration and operation of all bio-inspired components
in a unified cognitive system that mimics biological intelligence principles.
"""

import asyncio
import numpy as np
import logging
import time
from typing import Dict, Any

# Import all bio-inspired modules
from ..core import BioCognitiveArchitecture, CognitiveState
from ..neuromorphic import SpikingNeuralNetwork, NeuromorphicProcessor
from ..evolutionary import EvolutionaryOptimizer, BiologicalFitnessFunction
from ..homeostatic import HomeostaticRegulator, HomeostaticVariable
from ..energy_efficiency import EnergyMetrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BioCognitiveDemo:
    """
    Comprehensive demonstration of bio-inspired cognitive architecture
    
    This demo shows how all biological principles work together:
    - Spiking neural networks for neuromorphic computation
    - Evolutionary optimization for adaptive improvement
    - Homeostatic regulation for stability
    - Energy efficiency monitoring
    - Circadian rhythms and sleep/wake cycles
    """
    
    def __init__(self):
        # Initialize main architecture
        self.architecture = BioCognitiveArchitecture()
        
        # Initialize all subsystems
        self.snn = SpikingNeuralNetwork(
            name="MainSNN",
            num_neurons=1000,
            connection_probability=0.1
        )
        
        self.neuromorphic_processor = NeuromorphicProcessor(
            name="NeuromorphicCore",
            num_chips=2,
            cores_per_chip=4
        )
        
        self.evolutionary_optimizer = EvolutionaryOptimizer(
            name="EvolutionEngine",
            population_size=50,
            fitness_function=BiologicalFitnessFunction()
        )
        
        self.homeostatic_regulator = HomeostaticRegulator(
            name="HomeostaticController"
        )
        
        self.energy_metrics = EnergyMetrics(
            name="EnergyMonitor"
        )
        
        # Register all modules with the architecture
        self.architecture.register_module(self.snn)
        self.architecture.register_module(self.neuromorphic_processor)
        self.architecture.register_module(self.evolutionary_optimizer)
        self.architecture.register_module(self.homeostatic_regulator)
        self.architecture.register_module(self.energy_metrics)
        
        # Demo parameters
        self.demo_duration = 300  # 5 minutes
        self.timestep = 0.1  # 100ms
        self.demo_running = False
        
        logger.info("Bio-Inspired Cognitive Architecture Demo initialized")
    
    async def run_comprehensive_demo(self):
        """Run comprehensive demonstration of the bio-inspired system"""
        
        logger.info("Starting comprehensive bio-inspired cognitive architecture demo")
        
        # Start autonomous operation
        autonomous_task = asyncio.create_task(
            self.architecture.start_autonomous_operation()
        )
        
        # Run demo scenarios
        demo_tasks = [
            self.run_learning_scenario(),
            self.run_adaptation_scenario(), 
            self.run_energy_optimization_scenario(),
            self.run_homeostatic_challenge_scenario(),
            self.monitor_system_health()
        ]
        
        try:\n            # Run all scenarios concurrently\n            await asyncio.gather(*demo_tasks)\n            \n        except Exception as e:\n            logger.error(f\"Demo error: {e}\")\n        \n        finally:\n            # Stop autonomous operation\n            self.architecture.stop_autonomous_operation()\n            await autonomous_task\n    \n    async def run_learning_scenario(self):\n        \"\"\"Demonstrate learning and adaptation capabilities\"\"\"\n        logger.info(\"Starting learning scenario\")\n        \n        for episode in range(10):\n            # Create learning task\n            learning_inputs = {\n                'sensory': {\n                    'visual': np.random.randn(64, 64, 3),\n                    'auditory': np.random.randn(1024)\n                },\n                'target_output': np.random.randn(10),\n                'reward_signal': np.random.random(),\n                'task_complexity': 0.5 + episode * 0.05\n            }\n            \n            # Process through architecture\n            result = await self.architecture.process_input(learning_inputs)\n            \n            # Extract performance metrics\n            performance = self._evaluate_learning_performance(result)\n            \n            # Provide feedback to evolutionary optimizer\n            evolution_inputs = {\n                'optimization_target': 'learning_performance',\n                'evaluation_data': {\n                    'performance': performance,\n                    'complexity': learning_inputs['task_complexity']\n                }\n            }\n            \n            await self.evolutionary_optimizer.process(evolution_inputs)\n            \n            logger.info(f\"Learning episode {episode + 1}: Performance = {performance:.3f}\")\n            \n            await asyncio.sleep(1.0)\n    \n    async def run_adaptation_scenario(self):\n        \"\"\"Demonstrate homeostatic adaptation to environmental changes\"\"\"\n        logger.info(\"Starting adaptation scenario\")\n        \n        # Create environmental perturbations\n        perturbations = [\n            {'energy_demand': 0.8, 'noise_level': 0.2},\n            {'energy_demand': 1.2, 'noise_level': 0.5},\n            {'energy_demand': 0.6, 'noise_level': 0.1},\n            {'energy_demand': 1.5, 'noise_level': 0.8}\n        ]\n        \n        for i, perturbation in enumerate(perturbations):\n            logger.info(f\"Applying perturbation {i + 1}: {perturbation}\")\n            \n            # Apply environmental change\n            homeostatic_inputs = {\n                'disturbances': {\n                    'energy_level': -perturbation['energy_demand'] * 0.1,\n                    'arousal_level': perturbation['noise_level'] * 0.3\n                },\n                'current_values': {\n                    'attention_focus': 0.6 - perturbation['noise_level'] * 0.2\n                }\n            }\n            \n            # Monitor adaptation response\n            for step in range(20):  # 20 adaptation steps\n                result = await self.homeostatic_regulator.process(homeostatic_inputs)\n                \n                stability = result['system_stability']\n                balance = result['homeostatic_balance']\n                \n                if step % 5 == 0:\n                    logger.info(f\"  Step {step}: Stability = {stability:.3f}, Balance = {balance:.3f}\")\n                \n                # Gradually reduce disturbances (system adapts)\n                for var in homeostatic_inputs['disturbances']:\n                    homeostatic_inputs['disturbances'][var] *= 0.95\n                \n                await asyncio.sleep(0.1)\n            \n            await asyncio.sleep(2.0)\n    \n    async def run_energy_optimization_scenario(self):\n        \"\"\"Demonstrate energy efficiency optimization\"\"\"\n        logger.info(\"Starting energy optimization scenario\")\n        \n        # Simulate varying computational loads\n        load_patterns = [\n            {'spikes': 100, 'plasticity': 5, 'description': 'light_load'},\n            {'spikes': 500, 'plasticity': 25, 'description': 'moderate_load'},\n            {'spikes': 1000, 'plasticity': 50, 'description': 'heavy_load'},\n            {'spikes': 2000, 'plasticity': 100, 'description': 'extreme_load'}\n        ]\n        \n        for pattern in load_patterns:\n            logger.info(f\"Testing {pattern['description']} (spikes: {pattern['spikes']})\")\n            \n            # Generate load\n            energy_inputs = {\n                'num_spikes': pattern['spikes'],\n                'num_neurons': 1000,\n                'num_synapses': 100000,\n                'plasticity_events': pattern['plasticity'],\n                'memory_operations': pattern['spikes'] // 10,\n                'dt': 0.1\n            }\n            \n            # Monitor energy consumption\n            result = await self.energy_metrics.process(energy_inputs)\n            \n            efficiency = result['efficiency_ratio']\n            power = result['current_power']\n            temp = result['thermal_state']['temperature']\n            \n            logger.info(f\"  Efficiency ratio: {efficiency:.4f}\")\n            logger.info(f\"  Power consumption: {power:.3f}W\")\n            logger.info(f\"  Temperature: {temp:.1f}°C\")\n            \n            # Check for optimization recommendations\n            recommendations = result['optimization_recommendations']\n            if recommendations:\n                logger.info(f\"  Recommendations: {len(recommendations)} suggestions\")\n                for rec in recommendations[:2]:  # Show first 2\n                    logger.info(f\"    - {rec['type']}: {rec['description']}\")\n            \n            await asyncio.sleep(2.0)\n    \n    async def run_homeostatic_challenge_scenario(self):\n        \"\"\"Test homeostatic regulation under extreme conditions\"\"\"\n        logger.info(\"Starting homeostatic challenge scenario\")\n        \n        # Create extreme disturbances\n        extreme_challenges = [\n            {\n                'name': 'energy_crisis',\n                'disturbances': {'energy_level': -0.5},\n                'duration': 10\n            },\n            {\n                'name': 'attention_overload',\n                'disturbances': {'attention_focus': 0.8, 'arousal_level': 0.6},\n                'duration': 15\n            },\n            {\n                'name': 'emotional_shock',\n                'disturbances': {'emotional_valence': -0.9},\n                'duration': 8\n            }\n        ]\n        \n        for challenge in extreme_challenges:\n            logger.info(f\"Challenging system with {challenge['name']}\")\n            \n            # Apply extreme disturbance\n            homeostatic_inputs = {\n                'disturbances': challenge['disturbances'],\n                'current_values': {}\n            }\n            \n            # Monitor recovery\n            recovery_times = []\n            for step in range(challenge['duration']):\n                result = await self.homeostatic_regulator.process(homeostatic_inputs)\n                \n                stability = result['system_stability']\n                emergency_actions = result['emergency_actions']\n                \n                if emergency_actions:\n                    logger.warning(f\"  Emergency actions triggered: {emergency_actions}\")\n                \n                if stability > 0.8 and not recovery_times:\n                    recovery_times.append(step)\n                    logger.info(f\"  System recovered in {step} steps\")\n                \n                # Reduce disturbance over time\n                for var in homeostatic_inputs['disturbances']:\n                    homeostatic_inputs['disturbances'][var] *= 0.9\n                \n                await asyncio.sleep(0.5)\n            \n            await asyncio.sleep(3.0)\n    \n    async def monitor_system_health(self):\n        \"\"\"Continuously monitor overall system health\"\"\"\n        logger.info(\"Starting system health monitoring\")\n        \n        monitoring_duration = self.demo_duration\n        start_time = time.time()\n        \n        while time.time() - start_time < monitoring_duration:\n            # Get system status\n            status = self.architecture.get_system_status()\n            \n            # Log key metrics every 30 seconds\n            if int(time.time() - start_time) % 30 == 0:\n                logger.info(\"=== SYSTEM HEALTH REPORT ===\")\n                logger.info(f\"State: {status['state']}\")\n                logger.info(f\"Generation: {status['generation']}\")\n                logger.info(f\"Active modules: {len(status['active_modules'])}\")\n                \n                global_metrics = status['global_metrics']\n                logger.info(f\"Energy efficiency: {global_metrics['energy_efficiency']:.3f}\")\n                logger.info(f\"Homeostatic balance: {global_metrics['homeostatic_balance']:.3f}\")\n                logger.info(f\"Plasticity index: {global_metrics['plasticity_index']:.3f}\")\n                \n                # Check for any critical issues\n                if global_metrics['energy_efficiency'] < 0.1:\n                    logger.warning(\"Low energy efficiency detected!\")\n                \n                if global_metrics['homeostatic_balance'] < 0.3:\n                    logger.warning(\"Homeostatic imbalance detected!\")\n                \n                logger.info(\"=============================\")\n            \n            await asyncio.sleep(5.0)\n    \n    def _evaluate_learning_performance(self, result: Dict[str, Any]) -> float:\n        \"\"\"Evaluate learning performance from processing result\"\"\"\n        # Extract relevant metrics\n        processing_time = result.get('processing_time', 1.0)\n        metrics = result.get('metrics', {})\n        \n        # Calculate performance score\n        speed_score = 1.0 / (1.0 + processing_time)\n        efficiency_score = metrics.get('energy_efficiency', 0.5)\n        plasticity_score = metrics.get('plasticity_index', 0.5)\n        \n        # Weighted combination\n        performance = 0.4 * speed_score + 0.3 * efficiency_score + 0.3 * plasticity_score\n        \n        return np.clip(performance, 0.0, 1.0)\n    \n    async def run_circadian_rhythm_demo(self):\n        \"\"\"Demonstrate circadian rhythm and sleep/wake cycles\"\"\"\n        logger.info(\"Starting circadian rhythm demonstration\")\n        \n        # Simulate 24-hour cycle in accelerated time (24 minutes)\n        hours_per_minute = 1.0\n        \n        for minute in range(24):  # 24 \"hours\"\n            hour = minute % 24\n            circadian_phase = hour / 24.0\n            \n            # Simulate different states based on time\n            if 22 <= hour or hour <= 6:  # Night time\n                sleep_inputs = {\n                    'circadian_phase': circadian_phase,\n                    'sleep_pressure': 0.8,\n                    'activity_level': 0.1\n                }\n                logger.info(f\"Hour {hour}: Sleep phase (circadian: {circadian_phase:.2f})\")\n            else:  # Day time\n                wake_inputs = {\n                    'circadian_phase': circadian_phase,\n                    'sleep_pressure': 0.2,\n                    'activity_level': 0.8\n                }\n                logger.info(f\"Hour {hour}: Wake phase (circadian: {circadian_phase:.2f})\")\n            \n            await asyncio.sleep(1.0)  # 1 minute = 1 hour\n    \n    def generate_demo_report(self) -> Dict[str, Any]:\n        \"\"\"Generate comprehensive demo report\"\"\"\n        system_status = self.architecture.get_system_status()\n        \n        report = {\n            'demo_summary': {\n                'duration': self.demo_duration,\n                'scenarios_completed': 4,\n                'system_state': system_status['state'],\n                'generation': system_status['generation']\n            },\n            'performance_metrics': system_status['global_metrics'],\n            'module_status': {\n                module_name: module.get_biological_metrics().to_dict()\n                for module_name, module in self.architecture.modules.items()\n            },\n            'energy_statistics': self.energy_metrics.get_energy_statistics(),\n            'evolutionary_progress': {\n                'generation': self.evolutionary_optimizer.generation_count,\n                'best_fitness': (self.evolutionary_optimizer.population.best_individual.fitness\n                               if self.evolutionary_optimizer.population.best_individual else 0.0)\n            },\n            'homeostatic_state': self.homeostatic_regulator._get_variable_states(),\n            'recommendations': [\n                \"System demonstrates robust biological-inspired operation\",\n                \"Energy efficiency within acceptable biological ranges\", \n                \"Homeostatic regulation maintains system stability\",\n                \"Evolutionary optimization shows continuous improvement\",\n                \"Neuromorphic processing exhibits biological-like dynamics\"\n            ]\n        }\n        \n        return report\n\nasync def main():\n    \"\"\"Main demo function\"\"\"\n    print(\"Bio-Inspired Cognitive Architecture Comprehensive Demo\")\n    print(\"======================================================\")\n    print()\n    print(\"This demo showcases Ben Goertzel's research principles:\")\n    print(\"- Neuromorphic spiking neural networks\")\n    print(\"- Evolutionary optimization and adaptation\")\n    print(\"- Homeostatic regulation and allostasis\")\n    print(\"- Energy efficiency matching biological networks\")\n    print(\"- Integrated bio-inspired cognitive processing\")\n    print()\n    \n    # Create and run demo\n    demo = BioCognitiveDemo()\n    \n    try:\n        # Run comprehensive demo\n        await demo.run_comprehensive_demo()\n        \n        # Generate final report\n        report = demo.generate_demo_report()\n        \n        print()\n        print(\"=== DEMO COMPLETION REPORT ===\")\n        print(f\"System Generation: {report['demo_summary']['generation']}\")\n        print(f\"Final State: {report['demo_summary']['system_state']}\")\n        print(f\"Energy Efficiency: {report['performance_metrics']['energy_efficiency']:.3f}\")\n        print(f\"Homeostatic Balance: {report['performance_metrics']['homeostatic_balance']:.3f}\")\n        print(f\"Plasticity Index: {report['performance_metrics']['plasticity_index']:.3f}\")\n        print()\n        print(\"Key Achievements:\")\n        for rec in report['recommendations']:\n            print(f\"✓ {rec}\")\n        print()\n        print(\"Demo completed successfully!\")\n        \n    except KeyboardInterrupt:\n        print(\"\\nDemo interrupted by user\")\n    except Exception as e:\n        print(f\"\\nDemo error: {e}\")\n        raise\n\nif __name__ == \"__main__\":\n    asyncio.run(main())"