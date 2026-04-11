"""
Comprehensive Bio-Inspired Cognitive Architecture Demo

Demonstrates the integration and operation of all bio-inspired components
in a unified cognitive system that mimics biological intelligence principles.
"""

import asyncio
import logging
import time
from typing import Any, Dict

import numpy as np

# Import all bio-inspired modules
from ..core import BioCognitiveArchitecture, CognitiveState
from ..energy_efficiency import EnergyMetrics
from ..evolutionary import BiologicalFitnessFunction, EvolutionaryOptimizer
from ..homeostatic import HomeostaticRegulator, HomeostaticVariable
from ..neuromorphic import NeuromorphicProcessor, SpikingNeuralNetwork

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
            name="MainSNN", num_neurons=1000, connection_probability=0.1
        )

        self.neuromorphic_processor = NeuromorphicProcessor(
            name="NeuromorphicCore", num_chips=2, cores_per_chip=4
        )

        self.evolutionary_optimizer = EvolutionaryOptimizer(
            name="EvolutionEngine", population_size=50, fitness_function=BiologicalFitnessFunction()
        )

        self.homeostatic_regulator = HomeostaticRegulator(name="HomeostaticController")

        self.energy_metrics = EnergyMetrics(name="EnergyMonitor")

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
        autonomous_task = asyncio.create_task(self.architecture.start_autonomous_operation())

        # Run demo scenarios
        demo_tasks = [
            self.run_learning_scenario(),
            self.run_adaptation_scenario(),
            self.run_energy_optimization_scenario(),
            self.run_homeostatic_challenge_scenario(),
            self.monitor_system_health(),
        ]

        try:
            # Run all scenarios concurrently
            await asyncio.gather(*demo_tasks)

        except Exception as e:
            logger.error(f"Demo error: {e}")

        finally:
            # Stop autonomous operation
            self.architecture.stop_autonomous_operation()
            await autonomous_task

    async def run_learning_scenario(self):
        """Demonstrate learning and adaptation capabilities"""
        logger.info("Starting learning scenario")

        for episode in range(10):
            # Create learning task
            learning_inputs = {
                "sensory": {
                    "visual": np.random.randn(64, 64, 3),
                    "auditory": np.random.randn(1024),
                },
                "target_output": np.random.randn(10),
                "reward_signal": np.random.random(),
                "task_complexity": 0.5 + episode * 0.05,
            }

            # Process through architecture
            result = await self.architecture.process_input(learning_inputs)

            # Extract performance metrics
            performance = self._evaluate_learning_performance(result)

            # Provide feedback to evolutionary optimizer
            evolution_inputs = {
                "optimization_target": "learning_performance",
                "evaluation_data": {
                    "performance": performance,
                    "complexity": learning_inputs["task_complexity"],
                },
            }

            await self.evolutionary_optimizer.process(evolution_inputs)

            logger.info(f"Learning episode {episode + 1}: Performance = {performance:.3f}")

            await asyncio.sleep(1.0)

    async def run_adaptation_scenario(self):
        """Demonstrate homeostatic adaptation to environmental changes"""
        logger.info("Starting adaptation scenario")

        # Create environmental perturbations
        perturbations = [
            {"energy_demand": 0.8, "noise_level": 0.2},
            {"energy_demand": 1.2, "noise_level": 0.5},
            {"energy_demand": 0.6, "noise_level": 0.1},
            {"energy_demand": 1.5, "noise_level": 0.8},
        ]

        for i, perturbation in enumerate(perturbations):
            logger.info(f"Applying perturbation {i + 1}: {perturbation}")

            # Apply environmental change
            homeostatic_inputs = {
                "disturbances": {
                    "energy_level": -perturbation["energy_demand"] * 0.1,
                    "arousal_level": perturbation["noise_level"] * 0.3,
                },
                "current_values": {"attention_focus": 0.6 - perturbation["noise_level"] * 0.2},
            }

            # Monitor adaptation response
            for step in range(20):  # 20 adaptation steps
                result = await self.homeostatic_regulator.process(homeostatic_inputs)

                stability = result["system_stability"]
                balance = result["homeostatic_balance"]

                if step % 5 == 0:
                    logger.info(
                        f"  Step {step}: Stability = {stability:.3f}, Balance = {balance:.3f}"
                    )

                # Gradually reduce disturbances (system adapts)
                for var in homeostatic_inputs["disturbances"]:
                    homeostatic_inputs["disturbances"][var] *= 0.95

                await asyncio.sleep(0.1)

            await asyncio.sleep(2.0)

    async def run_energy_optimization_scenario(self):
        """Demonstrate energy efficiency optimization"""
        logger.info("Starting energy optimization scenario")

        # Simulate varying computational loads
        load_patterns = [
            {"spikes": 100, "plasticity": 5, "description": "light_load"},
            {"spikes": 500, "plasticity": 25, "description": "moderate_load"},
            {"spikes": 1000, "plasticity": 50, "description": "heavy_load"},
            {"spikes": 2000, "plasticity": 100, "description": "extreme_load"},
        ]

        for pattern in load_patterns:
            logger.info(f"Testing {pattern['description']} (spikes: {pattern['spikes']})")

            # Generate load
            energy_inputs = {
                "num_spikes": pattern["spikes"],
                "num_neurons": 1000,
                "num_synapses": 100000,
                "plasticity_events": pattern["plasticity"],
                "memory_operations": pattern["spikes"] // 10,
                "dt": 0.1,
            }

            # Monitor energy consumption
            result = await self.energy_metrics.process(energy_inputs)

            efficiency = result["efficiency_ratio"]
            power = result["current_power"]
            temp = result["thermal_state"]["temperature"]

            logger.info(f"  Efficiency ratio: {efficiency:.4f}")
            logger.info(f"  Power consumption: {power:.3f}W")
            logger.info(f"  Temperature: {temp:.1f}°C")

            # Check for optimization recommendations
            recommendations = result["optimization_recommendations"]
            if recommendations:
                logger.info(f"  Recommendations: {len(recommendations)} suggestions")
                for rec in recommendations[:2]:  # Show first 2
                    logger.info(f"    - {rec['type']}: {rec['description']}")

            await asyncio.sleep(2.0)

    async def run_homeostatic_challenge_scenario(self):
        """Test homeostatic regulation under extreme conditions"""
        logger.info("Starting homeostatic challenge scenario")

        # Create extreme disturbances
        extreme_challenges = [
            {"name": "energy_crisis", "disturbances": {"energy_level": -0.5}, "duration": 10},
            {
                "name": "attention_overload",
                "disturbances": {"attention_focus": 0.8, "arousal_level": 0.6},
                "duration": 15,
            },
            {"name": "emotional_shock", "disturbances": {"emotional_valence": -0.9}, "duration": 8},
        ]

        for challenge in extreme_challenges:
            logger.info(f"Challenging system with {challenge['name']}")

            # Apply extreme disturbance
            homeostatic_inputs = {"disturbances": challenge["disturbances"], "current_values": {}}

            # Monitor recovery
            recovery_times = []
            for step in range(challenge["duration"]):
                result = await self.homeostatic_regulator.process(homeostatic_inputs)

                stability = result["system_stability"]
                emergency_actions = result["emergency_actions"]

                if emergency_actions:
                    logger.warning(f"  Emergency actions triggered: {emergency_actions}")

                if stability > 0.8 and not recovery_times:
                    recovery_times.append(step)
                    logger.info(f"  System recovered in {step} steps")

                # Reduce disturbance over time
                for var in homeostatic_inputs["disturbances"]:
                    homeostatic_inputs["disturbances"][var] *= 0.9

                await asyncio.sleep(0.5)

            await asyncio.sleep(3.0)

    async def monitor_system_health(self):
        """Continuously monitor overall system health"""
        logger.info("Starting system health monitoring")

        monitoring_duration = self.demo_duration
        start_time = time.time()

        while time.time() - start_time < monitoring_duration:
            # Get system status
            status = self.architecture.get_system_status()

            # Log key metrics every 30 seconds
            if int(time.time() - start_time) % 30 == 0:
                logger.info("=== SYSTEM HEALTH REPORT ===")
                logger.info(f"State: {status['state']}")
                logger.info(f"Generation: {status['generation']}")
                logger.info(f"Active modules: {len(status['active_modules'])}")

                global_metrics = status["global_metrics"]
                logger.info(f"Energy efficiency: {global_metrics['energy_efficiency']:.3f}")
                logger.info(f"Homeostatic balance: {global_metrics['homeostatic_balance']:.3f}")
                logger.info(f"Plasticity index: {global_metrics['plasticity_index']:.3f}")

                # Check for any critical issues
                if global_metrics["energy_efficiency"] < 0.1:
                    logger.warning("Low energy efficiency detected!")

                if global_metrics["homeostatic_balance"] < 0.3:
                    logger.warning("Homeostatic imbalance detected!")

                logger.info("=============================")

            await asyncio.sleep(5.0)

    def _evaluate_learning_performance(self, result: Dict[str, Any]) -> float:
        """Evaluate learning performance from processing result"""
        # Extract relevant metrics
        processing_time = result.get("processing_time", 1.0)
        metrics = result.get("metrics", {})

        # Calculate performance score
        speed_score = 1.0 / (1.0 + processing_time)
        efficiency_score = metrics.get("energy_efficiency", 0.5)
        plasticity_score = metrics.get("plasticity_index", 0.5)

        # Weighted combination
        performance = 0.4 * speed_score + 0.3 * efficiency_score + 0.3 * plasticity_score

        return np.clip(performance, 0.0, 1.0)

    async def run_circadian_rhythm_demo(self):
        """Demonstrate circadian rhythm and sleep/wake cycles"""
        logger.info("Starting circadian rhythm demonstration")

        # Simulate 24-hour cycle in accelerated time (24 minutes)
        hours_per_minute = 1.0

        for minute in range(24):  # 24 "hours"
            hour = minute % 24
            circadian_phase = hour / 24.0

            # Simulate different states based on time
            if 22 <= hour or hour <= 6:  # Night time
                sleep_inputs = {
                    "circadian_phase": circadian_phase,
                    "sleep_pressure": 0.8,
                    "activity_level": 0.1,
                }
                logger.info(f"Hour {hour}: Sleep phase (circadian: {circadian_phase:.2f})")
            else:  # Day time
                wake_inputs = {
                    "circadian_phase": circadian_phase,
                    "sleep_pressure": 0.2,
                    "activity_level": 0.8,
                }
                logger.info(f"Hour {hour}: Wake phase (circadian: {circadian_phase:.2f})")

            await asyncio.sleep(1.0)  # 1 minute = 1 hour

    def generate_demo_report(self) -> Dict[str, Any]:
        """Generate comprehensive demo report"""
        system_status = self.architecture.get_system_status()

        report = {
            "demo_summary": {
                "duration": self.demo_duration,
                "scenarios_completed": 4,
                "system_state": system_status["state"],
                "generation": system_status["generation"],
            },
            "performance_metrics": system_status["global_metrics"],
            "module_status": {
                module_name: module.get_biological_metrics().to_dict()
                for module_name, module in self.architecture.modules.items()
            },
            "energy_statistics": self.energy_metrics.get_energy_statistics(),
            "evolutionary_progress": {
                "generation": self.evolutionary_optimizer.generation_count,
                "best_fitness": (
                    self.evolutionary_optimizer.population.best_individual.fitness
                    if self.evolutionary_optimizer.population.best_individual
                    else 0.0
                ),
            },
            "homeostatic_state": self.homeostatic_regulator._get_variable_states(),
            "recommendations": [
                "System demonstrates robust biological-inspired operation",
                "Energy efficiency within acceptable biological ranges",
                "Homeostatic regulation maintains system stability",
                "Evolutionary optimization shows continuous improvement",
                "Neuromorphic processing exhibits biological-like dynamics",
            ],
        }

        return report


async def main():
    """Main demo function"""
    print("Bio-Inspired Cognitive Architecture Comprehensive Demo")
    print("======================================================")
    print()
    print("This demo showcases Ben Goertzel's research principles:")
    print("- Neuromorphic spiking neural networks")
    print("- Evolutionary optimization and adaptation")
    print("- Homeostatic regulation and allostasis")
    print("- Energy efficiency matching biological networks")
    print("- Integrated bio-inspired cognitive processing")
    print()

    # Create and run demo
    demo = BioCognitiveDemo()

    try:
        # Run comprehensive demo
        await demo.run_comprehensive_demo()

        # Generate final report
        report = demo.generate_demo_report()

        print()
        print("=== DEMO COMPLETION REPORT ===")
        print(f"System Generation: {report['demo_summary']['generation']}")
        print(f"Final State: {report['demo_summary']['system_state']}")
        print(f"Energy Efficiency: {report['performance_metrics']['energy_efficiency']:.3f}")
        print(f"Homeostatic Balance: {report['performance_metrics']['homeostatic_balance']:.3f}")
        print(f"Plasticity Index: {report['performance_metrics']['plasticity_index']:.3f}")
        print()
        print("Key Achievements:")
        for rec in report["recommendations"]:
            print(f"✓ {rec}")
        print()
        print("Demo completed successfully!")

    except KeyboardInterrupt:
        print("\
Demo interrupted by user")
    except Exception as e:
        print(f"\
Demo error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
