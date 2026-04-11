"""
Core Bio-Inspired Cognitive Architecture

This module implements the main orchestrator for the bio-inspired cognitive architecture,
integrating all biological intelligence principles into a unified system.
"""

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CognitiveState(Enum):
    """Cognitive states of the bio-inspired system"""

    AWAKE_ACTIVE = "awake_active"
    AWAKE_RESTING = "awake_resting"
    NREM_SLEEP = "nrem_sleep"
    REM_SLEEP = "rem_sleep"
    LEARNING = "learning"
    CONSOLIDATING = "consolidating"
    DEVELOPING = "developing"
    ADAPTING = "adapting"


@dataclass
class BiologicalMetrics:
    """Biological plausibility metrics"""

    energy_efficiency: float = 0.0
    spike_rate: float = 0.0
    synaptic_strength: float = 0.0
    plasticity_index: float = 0.0
    homeostatic_balance: float = 0.0
    developmental_stage: float = 0.0
    emotional_valence: float = 0.0
    attention_focus: float = 0.0
    memory_consolidation: float = 0.0
    neurotransmitter_levels: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "energy_efficiency": self.energy_efficiency,
            "spike_rate": self.spike_rate,
            "synaptic_strength": self.synaptic_strength,
            "plasticity_index": self.plasticity_index,
            "homeostatic_balance": self.homeostatic_balance,
            "developmental_stage": self.developmental_stage,
            "emotional_valence": self.emotional_valence,
            "attention_focus": self.attention_focus,
            "memory_consolidation": self.memory_consolidation,
            "neurotransmitter_levels": self.neurotransmitter_levels,
        }


class BioCognitiveModule(ABC):
    """Base class for all bio-cognitive modules"""

    def __init__(self, name: str):
        self.name = name
        self.active = True
        self.metrics = BiologicalMetrics()
        self.lock = threading.Lock()

    @abstractmethod
    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process inputs through the biological module"""
        pass

    @abstractmethod
    def get_biological_metrics(self) -> BiologicalMetrics:
        """Get current biological metrics"""
        pass

    @abstractmethod
    def update_parameters(self, learning_signal: float):
        """Update module parameters based on learning signal"""
        pass


class BioCognitiveArchitecture:
    """
    Main Bio-Inspired Cognitive Architecture orchestrator

    Integrates all biological intelligence principles:
    - Neuromorphic computing with spiking neural networks
    - Evolutionary optimization
    - Homeostatic regulation
    - Developmental learning
    - Neuromodulation
    - Sleep/wake cycles
    - Emotional regulation
    - Embodied cognition
    - Neuroplasticity
    - Hierarchical temporal memory
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.modules: Dict[str, BioCognitiveModule] = {}
        self.state = CognitiveState.AWAKE_ACTIVE
        self.global_metrics = BiologicalMetrics()
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=8)

        # Initialize biological timing
        self.circadian_clock = 0.0
        self.circadian_period = 24.0 * 3600.0  # 24 hours in seconds
        self.sleep_pressure = 0.0
        self.wake_time = 0.0

        # Initialize evolutionary parameters
        self.generation = 0
        self.fitness_history = []

        # Initialize homeostatic variables
        self.homeostatic_targets = {"energy": 0.7, "arousal": 0.5, "valence": 0.0, "attention": 0.6}

        logger.info("Bio-Inspired Cognitive Architecture initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for the architecture"""
        return {
            "neuromorphic": {
                "num_neurons": 10000,
                "connection_probability": 0.1,
                "spike_threshold": -55.0,
                "refractory_period": 2.0,
            },
            "evolutionary": {
                "population_size": 100,
                "mutation_rate": 0.01,
                "crossover_rate": 0.8,
                "selection_pressure": 0.2,
            },
            "homeostatic": {
                "regulation_strength": 0.1,
                "adaptation_rate": 0.01,
                "setpoint_flexibility": 0.05,
            },
            "developmental": {
                "maturation_rate": 0.001,
                "pruning_threshold": 0.1,
                "growth_factor": 1.2,
            },
            "neuromodulation": {
                "dopamine_baseline": 0.3,
                "serotonin_baseline": 0.4,
                "norepinephrine_baseline": 0.2,
                "acetylcholine_baseline": 0.5,
            },
            "sleep_wake": {
                "sleep_threshold": 0.8,
                "wake_threshold": 0.2,
                "consolidation_strength": 0.6,
            },
            "emotional": {
                "emotion_decay": 0.95,
                "emotion_sensitivity": 0.3,
                "regulation_strength": 0.4,
            },
            "embodied": {
                "sensory_integration_window": 100,
                "motor_prediction_horizon": 50,
                "proprioception_weight": 0.3,
            },
            "neuroplasticity": {
                "stdp_window": 20.0,
                "ltp_threshold": 0.6,
                "ltd_threshold": 0.3,
                "metaplasticity_rate": 0.01,
            },
            "energy_efficiency": {
                "target_efficiency": 0.8,
                "metabolic_cost_weight": 0.2,
                "spike_cost": 0.001,
            },
        }

    def register_module(self, module: BioCognitiveModule):
        """Register a bio-cognitive module"""
        with threading.Lock():
            self.modules[module.name] = module
            logger.info(f"Registered module: {module.name}")

    def unregister_module(self, module_name: str):
        """Unregister a bio-cognitive module"""
        with threading.Lock():
            if module_name in self.modules:
                del self.modules[module_name]
                logger.info(f"Unregistered module: {module_name}")

    async def process_input(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process inputs through the entire bio-cognitive architecture"""
        start_time = time.time()

        # Update circadian clock
        self._update_circadian_clock()

        # Determine current cognitive state
        self._update_cognitive_state()

        # Process through all active modules
        module_outputs = {}
        tasks = []

        for name, module in self.modules.items():
            if module.active:
                task = asyncio.create_task(module.process(inputs))
                tasks.append((name, task))

        # Wait for all modules to complete
        for name, task in tasks:
            try:
                output = await task
                module_outputs[name] = output
            except Exception as e:
                logger.error(f"Error in module {name}: {e}")
                module_outputs[name] = {}

        # Integrate module outputs
        integrated_output = self._integrate_outputs(module_outputs)

        # Update global metrics
        self._update_global_metrics()

        # Calculate biological efficiency
        processing_time = time.time() - start_time
        self._calculate_efficiency_metrics(processing_time)

        return {
            "output": integrated_output,
            "metrics": self.global_metrics.to_dict(),
            "state": self.state.value,
            "processing_time": processing_time,
        }

    def _update_circadian_clock(self):
        """Update circadian rhythm clock"""
        current_time = time.time()
        self.circadian_clock = (current_time % self.circadian_period) / self.circadian_period

        # Update sleep pressure (builds during wake, decreases during sleep)
        if self.state in [CognitiveState.AWAKE_ACTIVE, CognitiveState.AWAKE_RESTING]:
            self.sleep_pressure = min(1.0, self.sleep_pressure + 0.0001)
        else:
            self.sleep_pressure = max(0.0, self.sleep_pressure - 0.001)

    def _update_cognitive_state(self):
        """Update cognitive state based on circadian rhythm and sleep pressure"""
        sleep_drive = self.sleep_pressure + 0.5 * np.sin(2 * np.pi * self.circadian_clock)

        if sleep_drive > self.config["sleep_wake"]["sleep_threshold"]:
            if np.random.random() < 0.8:  # 80% NREM, 20% REM
                self.state = CognitiveState.NREM_SLEEP
            else:
                self.state = CognitiveState.REM_SLEEP
        elif sleep_drive < self.config["sleep_wake"]["wake_threshold"]:
            self.state = CognitiveState.AWAKE_ACTIVE
        else:
            self.state = CognitiveState.AWAKE_RESTING

    def _integrate_outputs(self, module_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Integrate outputs from all modules"""
        integrated = {
            "perception": {},
            "cognition": {},
            "emotion": {},
            "memory": {},
            "action": {},
            "meta": {},
        }

        # Combine outputs from different modules
        for module_name, output in module_outputs.items():
            for category, data in output.items():
                if category in integrated:
                    integrated[category][module_name] = data

        # Apply cognitive state-dependent modulation
        self._apply_state_modulation(integrated)

        return integrated

    def _apply_state_modulation(self, integrated_output: Dict[str, Any]):
        """Apply cognitive state-dependent modulation to outputs"""
        modulation_factors = {
            CognitiveState.AWAKE_ACTIVE: {
                "attention": 1.0,
                "learning": 0.8,
                "memory_formation": 0.6,
                "consolidation": 0.2,
            },
            CognitiveState.AWAKE_RESTING: {
                "attention": 0.6,
                "learning": 0.4,
                "memory_formation": 0.3,
                "consolidation": 0.5,
            },
            CognitiveState.NREM_SLEEP: {
                "attention": 0.1,
                "learning": 0.1,
                "memory_formation": 0.1,
                "consolidation": 1.0,
            },
            CognitiveState.REM_SLEEP: {
                "attention": 0.2,
                "learning": 0.3,
                "memory_formation": 0.2,
                "consolidation": 0.8,
            },
        }

        factors = modulation_factors.get(
            self.state, modulation_factors[CognitiveState.AWAKE_ACTIVE]
        )

        # Apply modulation factors (simplified - would be more complex in practice)
        for category, data in integrated_output.items():
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        if "attention" in key.lower():
                            data[key] = value * factors["attention"]
                        elif "learning" in key.lower():
                            data[key] = value * factors["learning"]
                        elif "memory" in key.lower():
                            data[key] = value * factors["memory_formation"]
                        elif "consolidation" in key.lower():
                            data[key] = value * factors["consolidation"]

    def _update_global_metrics(self):
        """Update global biological metrics"""
        if not self.modules:
            return

        # Aggregate metrics from all modules
        total_energy = 0.0
        total_spikes = 0.0
        total_synaptic_strength = 0.0
        total_plasticity = 0.0
        num_modules = len(self.modules)

        neurotransmitter_totals = {
            "dopamine": 0.0,
            "serotonin": 0.0,
            "norepinephrine": 0.0,
            "acetylcholine": 0.0,
        }

        for module in self.modules.values():
            metrics = module.get_biological_metrics()
            total_energy += metrics.energy_efficiency
            total_spikes += metrics.spike_rate
            total_synaptic_strength += metrics.synaptic_strength
            total_plasticity += metrics.plasticity_index

            for nt, level in metrics.neurotransmitter_levels.items():
                if nt in neurotransmitter_totals:
                    neurotransmitter_totals[nt] += level

        # Calculate averages
        self.global_metrics.energy_efficiency = total_energy / num_modules
        self.global_metrics.spike_rate = total_spikes / num_modules
        self.global_metrics.synaptic_strength = total_synaptic_strength / num_modules
        self.global_metrics.plasticity_index = total_plasticity / num_modules

        # Average neurotransmitter levels
        for nt in neurotransmitter_totals:
            neurotransmitter_totals[nt] /= num_modules
        self.global_metrics.neurotransmitter_levels = neurotransmitter_totals

        # Calculate homeostatic balance
        self._calculate_homeostatic_balance()

        # Update other metrics
        self.global_metrics.memory_consolidation = self._calculate_consolidation_strength()
        self.global_metrics.attention_focus = self._calculate_attention_focus()

    def _calculate_homeostatic_balance(self):
        """Calculate overall homeostatic balance"""
        deviations = []

        current_values = {
            "energy": self.global_metrics.energy_efficiency,
            "arousal": self.global_metrics.neurotransmitter_levels.get("norepinephrine", 0.0),
            "valence": self.global_metrics.emotional_valence,
            "attention": self.global_metrics.attention_focus,
        }

        for param, target in self.homeostatic_targets.items():
            current = current_values.get(param, 0.0)
            deviation = abs(current - target) / (target + 1e-6)
            deviations.append(deviation)

        # Homeostatic balance is inverse of average deviation
        avg_deviation = np.mean(deviations)
        self.global_metrics.homeostatic_balance = max(0.0, 1.0 - avg_deviation)

    def _calculate_consolidation_strength(self) -> float:
        """Calculate memory consolidation strength based on state"""
        if self.state == CognitiveState.NREM_SLEEP:
            return 0.9
        elif self.state == CognitiveState.REM_SLEEP:
            return 0.7
        elif self.state == CognitiveState.AWAKE_RESTING:
            return 0.4
        else:
            return 0.2

    def _calculate_attention_focus(self) -> float:
        """Calculate attention focus based on state and arousal"""
        base_attention = {
            CognitiveState.AWAKE_ACTIVE: 0.8,
            CognitiveState.AWAKE_RESTING: 0.5,
            CognitiveState.NREM_SLEEP: 0.1,
            CognitiveState.REM_SLEEP: 0.3,
        }.get(self.state, 0.5)

        # Modulate by norepinephrine (arousal)
        arousal = self.global_metrics.neurotransmitter_levels.get("norepinephrine", 0.5)
        return base_attention * (0.5 + arousal)

    def _calculate_efficiency_metrics(self, processing_time: float):
        """Calculate energy efficiency metrics"""
        # Simplified biological efficiency calculation
        spike_cost = self.global_metrics.spike_rate * self.config["energy_efficiency"]["spike_cost"]
        metabolic_cost = processing_time * self.config["energy_efficiency"]["metabolic_cost_weight"]

        total_cost = spike_cost + metabolic_cost
        efficiency = 1.0 / (1.0 + total_cost)

        self.global_metrics.energy_efficiency = efficiency

    def evolve_system(self, fitness_score: float):
        """Evolve the system using evolutionary principles"""
        self.fitness_history.append(fitness_score)
        self.generation += 1

        if len(self.fitness_history) >= 10:  # Evolve every 10 generations
            avg_fitness = np.mean(self.fitness_history[-10:])

            # Apply evolutionary pressure to modules
            for module in self.modules.values():
                if hasattr(module, "evolve"):
                    module.evolve(avg_fitness)

            # Update configuration based on performance
            self._adaptive_configuration_update(avg_fitness)

    def _adaptive_configuration_update(self, fitness: float):
        """Adaptively update configuration based on fitness"""
        if fitness > 0.8:  # High performance - explore
            self.config["evolutionary"]["mutation_rate"] *= 1.1
        elif fitness < 0.5:  # Low performance - exploit
            self.config["evolutionary"]["mutation_rate"] *= 0.9

        # Clamp mutation rate
        self.config["evolutionary"]["mutation_rate"] = np.clip(
            self.config["evolutionary"]["mutation_rate"], 0.001, 0.1
        )

    async def start_autonomous_operation(self):
        """Start autonomous operation of the bio-cognitive architecture"""
        self.running = True
        logger.info("Starting autonomous bio-cognitive operation")

        while self.running:
            try:
                # Simulate autonomous cognition with random inputs
                autonomous_inputs = self._generate_autonomous_inputs()

                # Process autonomously
                result = await self.process_input(autonomous_inputs)

                # Self-evaluation and adaptation
                fitness = self._evaluate_performance(result)
                self.evolve_system(fitness)

                # Sleep briefly to allow other operations
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in autonomous operation: {e}")
                await asyncio.sleep(1.0)

    def _generate_autonomous_inputs(self) -> Dict[str, Any]:
        """Generate autonomous inputs for self-driven cognition"""
        return {
            "sensory": {
                "visual": np.random.randn(64, 64, 3),
                "auditory": np.random.randn(1024),
                "tactile": np.random.randn(100),
            },
            "internal": {
                "motivation": np.random.random(),
                "curiosity": np.random.random(),
                "energy_level": 0.5 + 0.5 * np.sin(self.circadian_clock * 2 * np.pi),
            },
            "context": {
                "time_of_day": self.circadian_clock,
                "sleep_pressure": self.sleep_pressure,
                "previous_state": self.state.value,
            },
        }

    def _evaluate_performance(self, result: Dict[str, Any]) -> float:
        """Evaluate system performance for evolutionary feedback"""
        metrics = result.get("metrics", {})

        # Multi-objective fitness function
        fitness_components = {
            "energy_efficiency": metrics.get("energy_efficiency", 0.0),
            "homeostatic_balance": metrics.get("homeostatic_balance", 0.0),
            "plasticity": metrics.get("plasticity_index", 0.0),
            "processing_speed": 1.0 / (result.get("processing_time", 1.0) + 1e-6),
        }

        # Weighted combination
        weights = [0.3, 0.3, 0.2, 0.2]
        fitness = sum(w * f for w, f in zip(weights, fitness_components.values()))

        return np.clip(fitness, 0.0, 1.0)

    def stop_autonomous_operation(self):
        """Stop autonomous operation"""
        self.running = False
        logger.info("Stopping autonomous bio-cognitive operation")

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "state": self.state.value,
            "circadian_phase": self.circadian_clock,
            "sleep_pressure": self.sleep_pressure,
            "generation": self.generation,
            "num_modules": len(self.modules),
            "active_modules": [name for name, module in self.modules.items() if module.active],
            "global_metrics": self.global_metrics.to_dict(),
            "fitness_history": self.fitness_history[-10:] if self.fitness_history else [],
            "running": self.running,
        }

    def save_state(self, filepath: str):
        """Save system state to file"""
        import pickle

        state_data = {
            "config": self.config,
            "state": self.state,
            "global_metrics": self.global_metrics,
            "circadian_clock": self.circadian_clock,
            "sleep_pressure": self.sleep_pressure,
            "generation": self.generation,
            "fitness_history": self.fitness_history,
            "homeostatic_targets": self.homeostatic_targets,
        }

        with open(filepath, "wb") as f:
            pickle.dump(state_data, f)

        logger.info(f"System state saved to {filepath}")

    def load_state(self, filepath: str):
        """Load system state from file"""
        import pickle

        with open(filepath, "rb") as f:
            state_data = pickle.load(f)

        self.config = state_data.get("config", self.config)
        self.state = state_data.get("state", self.state)
        self.global_metrics = state_data.get("global_metrics", self.global_metrics)
        self.circadian_clock = state_data.get("circadian_clock", 0.0)
        self.sleep_pressure = state_data.get("sleep_pressure", 0.0)
        self.generation = state_data.get("generation", 0)
        self.fitness_history = state_data.get("fitness_history", [])
        self.homeostatic_targets = state_data.get("homeostatic_targets", self.homeostatic_targets)

        logger.info(f"System state loaded from {filepath}")

    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=False)
