"""
Tests for asi_build.bio_inspired module.

The bio_inspired top-level __init__.py and several sub-__init__.py files
import from modules that don't exist (genetic_algorithms, genetic_programming,
evolutionary_strategies, allostasis_controller, stress_response, energy_balance,
biological_efficiency, power_management, thermal_dynamics, and many more).

Strategy: mock all missing modules in sys.modules BEFORE importing, then test
the individual files that DO exist and have real code.
"""

import sys
import types
import pytest
import asyncio
import time
import numpy as np

# ---------------------------------------------------------------------------
# Mock all missing bio_inspired submodules BEFORE any bio_inspired import
# ---------------------------------------------------------------------------

_MISSING = [
    # evolutionary submodules
    "asi_build.bio_inspired.evolutionary.genetic_algorithms",
    "asi_build.bio_inspired.evolutionary.genetic_programming",
    "asi_build.bio_inspired.evolutionary.evolutionary_strategies",
    # homeostatic submodules
    "asi_build.bio_inspired.homeostatic.allostasis_controller",
    "asi_build.bio_inspired.homeostatic.stress_response",
    "asi_build.bio_inspired.homeostatic.energy_balance",
    # energy_efficiency submodules
    "asi_build.bio_inspired.energy_efficiency.biological_efficiency",
    "asi_build.bio_inspired.energy_efficiency.power_management",
    "asi_build.bio_inspired.energy_efficiency.thermal_dynamics",
    # learning_rules submodules
    "asi_build.bio_inspired.learning_rules.stdp_learning",
    "asi_build.bio_inspired.learning_rules.bcm_learning",
    "asi_build.bio_inspired.learning_rules.hebbian_learning",
    "asi_build.bio_inspired.learning_rules.homeostatic_plasticity",
    "asi_build.bio_inspired.learning_rules.metaplasticity",
    # top-level missing packages
    "asi_build.bio_inspired.developmental",
    "asi_build.bio_inspired.neuromodulation",
    "asi_build.bio_inspired.sleep_wake",
    "asi_build.bio_inspired.emotional",
    "asi_build.bio_inspired.embodied",
    "asi_build.bio_inspired.neuroplasticity",
    "asi_build.bio_inspired.hierarchical_memory",
]


class _AutoModule(types.ModuleType):
    """Module that returns a dummy class for any missing attribute."""
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return type(name, (), {"__init__": lambda self, *a, **kw: None})


for _mod_name in _MISSING:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _AutoModule(_mod_name)


# ---------------------------------------------------------------------------
# NOW we can safely import the real modules
# ---------------------------------------------------------------------------

from asi_build.bio_inspired.core import (
    BioCognitiveArchitecture,
    BiologicalMetrics,
    CognitiveState,
    BioCognitiveModule,
)
from asi_build.bio_inspired.neuromorphic.neuromorphic_processor import (
    NeuromorphicProcessor,
    NeuromorphicChip,
    NeuromorphicEvent,
    EventDrivenProcessor,
    LoadBalancer,
    ThermalModel,
    ProcessingMode,
)
from asi_build.bio_inspired.neuromorphic.spiking_networks import (
    SpikingNeuralNetwork,
    SpikeEvent,
)
from asi_build.bio_inspired.evolutionary.evolutionary_optimizer import (
    EvolutionaryOptimizer,
    Individual,
    Population,
    BiologicalFitnessFunction,
    MultiObjectiveOptimizer,
    OptimizationMethod,
    FitnessFunction,
)
from asi_build.bio_inspired.homeostatic.homeostatic_regulator import (
    HomeostaticRegulator,
    HomeostaticVariable,
    RegulationMode,
)
from asi_build.bio_inspired.energy_efficiency.energy_metrics import (
    EnergyCalculator,
    EnergyMetrics,
    MetabolicCost,
    EnergyType,
)


# ===== helpers =====

def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ===================================================================
# BiologicalMetrics
# ===================================================================

class TestBiologicalMetrics:

    def test_defaults(self):
        m = BiologicalMetrics()
        assert m.energy_efficiency == 0.0
        assert m.spike_rate == 0.0
        assert m.neurotransmitter_levels == {}

    def test_to_dict(self):
        m = BiologicalMetrics(energy_efficiency=0.5, spike_rate=10.0)
        d = m.to_dict()
        assert d["energy_efficiency"] == 0.5
        assert d["spike_rate"] == 10.0
        assert "neurotransmitter_levels" in d

    def test_custom_neurotransmitters(self):
        m = BiologicalMetrics(neurotransmitter_levels={"dopamine": 0.3})
        assert m.neurotransmitter_levels["dopamine"] == 0.3


# ===================================================================
# CognitiveState enum
# ===================================================================

class TestCognitiveState:

    def test_values(self):
        assert CognitiveState.AWAKE_ACTIVE.value == "awake_active"
        assert CognitiveState.REM_SLEEP.value == "rem_sleep"

    def test_all_members(self):
        assert len(CognitiveState) == 8


# ===================================================================
# BioCognitiveArchitecture
# ===================================================================

class TestBioCognitiveArchitecture:

    def test_default_init(self):
        arch = BioCognitiveArchitecture()
        assert arch.state == CognitiveState.AWAKE_ACTIVE
        assert arch.generation == 0
        assert arch.running is False
        assert len(arch.modules) == 0

    def test_custom_config(self):
        cfg = {"sleep_wake": {"sleep_threshold": 0.9, "wake_threshold": 0.1, "consolidation_strength": 0.5},
               "evolutionary": {"mutation_rate": 0.05, "crossover_rate": 0.8, "population_size": 100, "selection_pressure": 0.2},
               "energy_efficiency": {"spike_cost": 0.001, "metabolic_cost_weight": 0.2, "target_efficiency": 0.8}}
        arch = BioCognitiveArchitecture(config=cfg)
        assert arch.config["sleep_wake"]["sleep_threshold"] == 0.9

    def test_default_config_keys(self):
        arch = BioCognitiveArchitecture()
        expected = {"neuromorphic", "evolutionary", "homeostatic", "developmental",
                    "neuromodulation", "sleep_wake", "emotional", "embodied",
                    "neuroplasticity", "energy_efficiency"}
        assert expected == set(arch.config.keys())

    def test_register_unregister_module(self):
        arch = BioCognitiveArchitecture()
        # Create a dummy concrete module
        class DummyModule(BioCognitiveModule):
            async def process(self, inputs): return {}
            def get_biological_metrics(self): return BiologicalMetrics()
            def update_parameters(self, sig): pass

        mod = DummyModule("test_mod")
        arch.register_module(mod)
        assert "test_mod" in arch.modules
        arch.unregister_module("test_mod")
        assert "test_mod" not in arch.modules

    def test_unregister_missing(self):
        arch = BioCognitiveArchitecture()
        arch.unregister_module("nonexistent")  # should not raise

    def test_circadian_clock(self):
        arch = BioCognitiveArchitecture()
        arch._update_circadian_clock()
        assert 0.0 <= arch.circadian_clock <= 1.0

    def test_sleep_pressure_increases(self):
        arch = BioCognitiveArchitecture()
        arch.sleep_pressure = 0.0
        arch.state = CognitiveState.AWAKE_ACTIVE
        arch._update_circadian_clock()
        assert arch.sleep_pressure > 0.0

    def test_consolidation_strength_by_state(self):
        arch = BioCognitiveArchitecture()
        arch.state = CognitiveState.NREM_SLEEP
        assert arch._calculate_consolidation_strength() == 0.9
        arch.state = CognitiveState.AWAKE_ACTIVE
        assert arch._calculate_consolidation_strength() == 0.2

    def test_attention_focus_awake(self):
        arch = BioCognitiveArchitecture()
        arch.state = CognitiveState.AWAKE_ACTIVE
        arch.global_metrics.neurotransmitter_levels = {"norepinephrine": 0.5}
        focus = arch._calculate_attention_focus()
        assert focus > 0.0

    def test_evolve_system(self):
        arch = BioCognitiveArchitecture()
        for i in range(15):
            arch.evolve_system(0.6)
        assert arch.generation == 15
        assert len(arch.fitness_history) == 15

    def test_adaptive_config_explore(self):
        arch = BioCognitiveArchitecture()
        original_rate = arch.config["evolutionary"]["mutation_rate"]
        arch._adaptive_configuration_update(0.9)  # high fitness → explore
        assert arch.config["evolutionary"]["mutation_rate"] > original_rate

    def test_adaptive_config_exploit(self):
        arch = BioCognitiveArchitecture()
        original_rate = arch.config["evolutionary"]["mutation_rate"]
        arch._adaptive_configuration_update(0.3)  # low fitness → exploit
        assert arch.config["evolutionary"]["mutation_rate"] < original_rate

    def test_get_system_status(self):
        arch = BioCognitiveArchitecture()
        status = arch.get_system_status()
        assert status["state"] == "awake_active"
        assert status["generation"] == 0
        assert status["running"] is False

    def test_save_load_state(self, tmp_path):
        arch = BioCognitiveArchitecture()
        arch.generation = 42
        arch.fitness_history = [0.5, 0.6]
        fp = str(tmp_path / "state.pkl")
        arch.save_state(fp)

        arch2 = BioCognitiveArchitecture()
        arch2.load_state(fp)
        assert arch2.generation == 42
        assert arch2.fitness_history == [0.5, 0.6]

    def test_integrate_outputs(self):
        arch = BioCognitiveArchitecture()
        module_outputs = {
            "mod1": {"perception": {"score": 0.8}, "cognition": {"val": 1}},
            "mod2": {"emotion": {"happy": 0.5}},
        }
        integrated = arch._integrate_outputs(module_outputs)
        assert "mod1" in integrated["perception"]
        assert "mod2" in integrated["emotion"]

    def test_evaluate_performance(self):
        arch = BioCognitiveArchitecture()
        result = {
            "metrics": {"energy_efficiency": 0.5, "homeostatic_balance": 0.5,
                        "plasticity_index": 0.5},
            "processing_time": 0.1,
        }
        fitness = arch._evaluate_performance(result)
        assert 0.0 <= fitness <= 1.0

    def test_update_global_metrics_no_modules(self):
        arch = BioCognitiveArchitecture()
        arch._update_global_metrics()  # should not raise

    def test_efficiency_metrics(self):
        arch = BioCognitiveArchitecture()
        arch.global_metrics.spike_rate = 100.0
        arch._calculate_efficiency_metrics(0.01)
        assert 0.0 < arch.global_metrics.energy_efficiency <= 1.0


# ===================================================================
# LoadBalancer
# ===================================================================

class TestLoadBalancer:

    def test_least_loaded(self):
        lb = LoadBalancer(["c0", "c1", "c2"])
        assert lb.get_least_loaded_chip() in ["c0", "c1", "c2"]

    def test_load_tracking(self):
        lb = LoadBalancer(["c0", "c1"])
        lb.update_load("c0", 10)
        assert lb.get_least_loaded_chip() == "c1"

    def test_reset_counters(self):
        lb = LoadBalancer(["c0", "c1"])
        lb.update_load("c0", 100)
        lb.reset_counters()
        assert lb.get_least_loaded_chip() in ["c0", "c1"]


# ===================================================================
# ThermalModel
# ===================================================================

class TestThermalModel:

    def test_default_temperature(self):
        tm = ThermalModel()
        assert tm.get_temperature() == 25.0

    def test_heating(self):
        tm = ThermalModel(ambient_temp=25.0)
        tm.update(1.0, 10.0)  # 1W for 10s
        assert tm.get_temperature() > 25.0

    def test_get_state(self):
        tm = ThermalModel()
        s = tm.get_state()
        assert "temperature" in s or "current_temp" in s or len(s) > 0


# ===================================================================
# NeuromorphicEvent
# ===================================================================

class TestNeuromorphicEvent:

    def test_creation(self):
        evt = NeuromorphicEvent("spike", 1, 2, 0.5, {"strength": 1.0})
        assert evt.event_type == "spike"
        assert evt.source_id == 1

    def test_comparison(self):
        e1 = NeuromorphicEvent("a", 0, 0, 0, None, priority=1)
        e2 = NeuromorphicEvent("b", 0, 0, 0, None, priority=5)
        assert e1 < e2


# ===================================================================
# NeuromorphicChip
# ===================================================================

class TestNeuromorphicChip:

    def test_init(self):
        chip = NeuromorphicChip("test_chip", num_cores=4)
        assert len(chip.cores) == 4
        assert chip.total_neurons == 4 * 1024
        assert chip.total_synapses == chip.total_neurons * 64

    def test_routing_table(self):
        chip = NeuromorphicChip("c", num_cores=3)
        assert "c_core_0" in chip.inter_core_network
        # core_0 should connect to core_1
        assert "c_core_1" in chip.inter_core_network["c_core_0"]

    def test_metrics(self):
        chip = NeuromorphicChip("c", num_cores=2)
        m = chip.get_chip_metrics()
        assert m["chip_id"] == "c"
        assert m["num_cores"] == 2
        assert "energy_efficiency" in m


# ===================================================================
# EventDrivenProcessor
# ===================================================================

class TestEventDrivenProcessor:

    def test_register_handler(self):
        proc = EventDrivenProcessor("p1")
        proc.register_event_handler("spike", lambda e: None)
        assert "spike" in proc.event_handlers

    def test_energy_cost(self):
        proc = EventDrivenProcessor("p1")
        evt = NeuromorphicEvent("spike", 0, 0, 0, "hello")
        cost = proc._calculate_energy_cost(evt, 0.001)
        assert cost > 0.0


# ===================================================================
# NeuromorphicProcessor (full system)
# The constructor calls asyncio.create_task() which needs a running loop.
# We patch _start_processing_tasks to avoid that requirement.
# ===================================================================

class TestNeuromorphicProcessor:

    @pytest.fixture(autouse=True)
    def _patch_async_startup(self, monkeypatch):
        monkeypatch.setattr(NeuromorphicProcessor, "_start_processing_tasks", lambda self: None)

    def test_init_defaults(self):
        proc = NeuromorphicProcessor()
        assert len(proc.chips) == 4
        assert proc.processing_mode == ProcessingMode.EVENT_DRIVEN

    def test_custom_config(self):
        proc = NeuromorphicProcessor(num_chips=2, cores_per_chip=4)
        assert len(proc.chips) == 2
        for chip in proc.chips.values():
            assert chip.num_cores == 4

    def test_default_config_keys(self):
        proc = NeuromorphicProcessor()
        cfg = proc._get_default_config()
        assert "neurons_per_core" in cfg
        assert "power_budget" in cfg

    def test_biological_metrics(self):
        proc = NeuromorphicProcessor()
        m = proc.get_biological_metrics()
        assert isinstance(m, BiologicalMetrics)

    def test_update_parameters(self):
        proc = NeuromorphicProcessor()
        proc.update_parameters(0.5)  # should not raise

    def test_processor_status(self):
        proc = NeuromorphicProcessor()
        status = proc.get_processor_status()
        assert "processing_mode" in status or isinstance(status, dict)

    def test_event_handlers_registered(self):
        proc = NeuromorphicProcessor()
        # Verify handlers were registered in all cores
        for chip in proc.chips.values():
            for core in chip.cores.values():
                assert "spike" in core.event_handlers


# ===================================================================
# Individual & Population (evolutionary)
# ===================================================================

class TestIndividual:

    def test_creation(self):
        ind = Individual(genome=[1, 2, 3], fitness=0.5)
        assert ind.genome == [1, 2, 3]
        assert ind.fitness == 0.5

    def test_copy(self):
        ind = Individual(genome=[1, 2, 3], fitness=0.8)
        c = ind.copy()
        assert c.genome == ind.genome
        assert c is not ind


class TestPopulation:

    def test_init_empty(self):
        pop = Population(size=50)
        assert pop.size == 50

    def test_add_individual(self):
        pop = Population(size=10)
        ind = Individual(genome=[1], fitness=0.5)
        pop.add_individual(ind)
        assert len(pop.individuals) >= 1

    def test_best_individuals(self):
        pop = Population(size=5, individuals=[
            Individual(genome=[i], fitness=float(i) / 10) for i in range(5)
        ])
        best = pop.get_best_individuals(2)
        assert len(best) == 2
        assert best[0].fitness >= best[1].fitness

    def test_worst_individuals(self):
        pop = Population(size=5, individuals=[
            Individual(genome=[i], fitness=float(i) / 10) for i in range(5)
        ])
        worst = pop.get_worst_individuals(2)
        assert len(worst) == 2
        assert worst[0].fitness <= worst[1].fitness

    def test_diversity(self):
        pop = Population(size=3, individuals=[
            Individual(genome=[float(i)], fitness=0.0) for i in range(3)
        ])
        d = pop.calculate_diversity()
        assert isinstance(d, float)

    def test_statistics(self):
        pop = Population(size=3, individuals=[
            Individual(genome=[1], fitness=0.3),
            Individual(genome=[2], fitness=0.6),
            Individual(genome=[3], fitness=0.9),
        ])
        pop.update_statistics()
        # update_statistics should run without error


# ===================================================================
# BiologicalFitnessFunction
# ===================================================================

class TestBiologicalFitnessFunction:

    def test_default_objectives(self):
        ff = BiologicalFitnessFunction()
        objs = ff.get_objectives()
        assert isinstance(objs, list)
        assert len(objs) > 0

    def test_evaluate(self):
        ff = BiologicalFitnessFunction()
        ind = Individual(genome=[0.5] * 10, fitness=0.0)
        score = _run(ff.evaluate(ind))
        assert isinstance(score, float)

    def test_custom_objectives(self):
        ff = BiologicalFitnessFunction(objectives=["energy_efficiency", "robustness"])
        assert "energy_efficiency" in ff.get_objectives()


# ===================================================================
# EvolutionaryOptimizer
# ===================================================================

class TestEvolutionaryOptimizer:

    def test_init(self):
        opt = EvolutionaryOptimizer()
        assert opt.name == "EvolutionaryOptimizer"

    def test_custom_params(self):
        opt = EvolutionaryOptimizer(
            population_size=50,
            optimization_method=OptimizationMethod.GENETIC_ALGORITHM,
        )
        assert opt.population.size == 50

    def test_biological_metrics(self):
        opt = EvolutionaryOptimizer()
        m = opt.get_biological_metrics()
        assert isinstance(m, BiologicalMetrics)

    def test_update_parameters(self):
        opt = EvolutionaryOptimizer(population_size=20)
        opt.update_parameters(0.5)

    def test_create_random_individual(self):
        opt = EvolutionaryOptimizer(population_size=10)
        ind = opt._create_random_individual("test_target")
        assert isinstance(ind, Individual)
        assert ind.genome is not None

    def test_crossover(self):
        opt = EvolutionaryOptimizer()
        p1 = Individual(genome=[float(i) for i in range(10)], fitness=0.5)
        p2 = Individual(genome=[float(i + 10) for i in range(10)], fitness=0.6)
        c1, c2 = opt._crossover(p1, p2)
        assert len(c1.genome) == 10
        assert len(c2.genome) == 10

    def test_mutate(self):
        opt = EvolutionaryOptimizer()
        ind = Individual(genome=[0.5] * 10, fitness=0.5)
        opt._mutate(ind)
        # mutation may or may not change values — just check no crash

    def test_tournament_selection(self):
        opt = EvolutionaryOptimizer(population_size=20)
        # Initialize population (async)
        _run(opt._initialize_population("target"))
        for ind in opt.population.individuals:
            ind.fitness = np.random.random()
        selected = opt._tournament_selection()
        assert len(selected) > 0

    def test_save_load_state(self, tmp_path):
        opt = EvolutionaryOptimizer(population_size=10)
        _run(opt._initialize_population("target"))
        fp = str(tmp_path / "evo_state.pkl")
        opt.save_evolution_state(fp)

        opt2 = EvolutionaryOptimizer(population_size=10)
        opt2.load_evolution_state(fp)
        assert opt2.generation_count == opt.generation_count


# ===================================================================
# HomeostaticVariable
# ===================================================================

class TestHomeostaticVariable:

    def test_creation(self):
        v = HomeostaticVariable(name="energy", current_value=0.7, setpoint=0.7, tolerance=0.1)
        assert v.name == "energy"
        assert v.calculate_error() == pytest.approx(0.0)

    def test_error_positive(self):
        v = HomeostaticVariable(name="x", current_value=0.3, setpoint=0.7, tolerance=0.1)
        assert v.calculate_error() == pytest.approx(0.4)

    def test_pid_terms(self):
        v = HomeostaticVariable(name="x", current_value=0.5, setpoint=0.7, tolerance=0.1)
        v.update_pid_terms(0.2, 0.1)
        assert v.integral_error == pytest.approx(0.02)
        assert len(v.error_history) == 1

    def test_error_history_bounded(self):
        v = HomeostaticVariable(name="x", current_value=0.5, setpoint=0.7, tolerance=0.1)
        for i in range(150):
            v.update_pid_terms(0.1, 0.1)
        assert len(v.error_history) == 100  # capped


# ===================================================================
# HomeostaticRegulator
# ===================================================================

class TestHomeostaticRegulator:

    def test_init(self):
        reg = HomeostaticRegulator()
        assert reg.regulation_mode == RegulationMode.ADAPTIVE
        assert len(reg.variables) == 4  # 4 default variables

    def test_default_variables(self):
        reg = HomeostaticRegulator()
        assert "energy_level" in reg.variables
        assert "arousal_level" in reg.variables
        assert "attention_focus" in reg.variables
        assert "emotional_valence" in reg.variables

    def test_add_remove_variable(self):
        reg = HomeostaticRegulator()
        new_var = HomeostaticVariable(name="custom", current_value=0.5, setpoint=0.5, tolerance=0.1)
        reg.add_variable(new_var)
        assert "custom" in reg.variables
        reg.remove_variable("custom")
        assert "custom" not in reg.variables

    def test_set_setpoint(self):
        reg = HomeostaticRegulator()
        reg.set_setpoint("energy_level", 0.8)
        assert reg.variables["energy_level"].setpoint == 0.8

    def test_set_setpoint_clamp(self):
        reg = HomeostaticRegulator()
        reg.set_setpoint("energy_level", 5.0)  # above max
        assert reg.variables["energy_level"].setpoint == 1.0

    def test_pid_control(self):
        reg = HomeostaticRegulator()
        var = reg.variables["energy_level"]
        output = reg._pid_control(var, 0.1)
        assert isinstance(output, float)

    def test_adaptive_control(self):
        reg = HomeostaticRegulator()
        var = reg.variables["energy_level"]
        output = reg._adaptive_control(var, 0.1)
        assert isinstance(output, float)

    def test_emergency_control_large_error(self):
        reg = HomeostaticRegulator()
        var = reg.variables["energy_level"]
        output = reg._emergency_control(var, 0.5)  # large error
        assert abs(output) > abs(reg._adaptive_control(var, 0.5))

    def test_system_stability(self):
        reg = HomeostaticRegulator()
        reg._update_system_stability()
        assert 0.0 <= reg.system_stability <= 1.0

    def test_overall_balance(self):
        reg = HomeostaticRegulator()
        balance = reg._calculate_overall_balance()
        assert 0.0 <= balance <= 1.0

    def test_process_async(self):
        reg = HomeostaticRegulator()
        result = _run(reg.process({"current_values": {"energy_level": 0.5}}))
        assert "regulation_outputs" in result
        assert "system_stability" in result

    def test_emergency_conditions(self):
        reg = HomeostaticRegulator()
        # Push energy_level to extreme
        reg.variables["energy_level"].current_value = 0.01
        actions = reg._check_emergency_conditions()
        assert any("critical_low" in a for a in actions)

    def test_biological_metrics(self):
        reg = HomeostaticRegulator()
        m = reg.get_biological_metrics()
        assert isinstance(m, BiologicalMetrics)
        assert m.homeostatic_balance >= 0.0

    def test_update_parameters_poor(self):
        reg = HomeostaticRegulator()
        old_kp = reg.kp
        reg.update_parameters(0.1)  # poor performance
        assert reg.kp >= old_kp  # should increase

    def test_regulation_history(self):
        reg = HomeostaticRegulator()
        _run(reg.process({"current_values": {"energy_level": 0.3}}))
        history = reg.get_regulation_history("energy_level")
        assert len(history) > 0

    def test_reset_regulation_state(self):
        reg = HomeostaticRegulator()
        _run(reg.process({"current_values": {"energy_level": 0.3}}))
        reg.reset_regulation_state()
        assert reg.system_stability == 1.0
        assert reg.total_regulation_effort == 0.0

    def test_variable_states(self):
        reg = HomeostaticRegulator()
        states = reg._get_variable_states()
        assert len(states) == 4
        assert "current_value" in states["energy_level"]


# ===================================================================
# EnergyCalculator
# ===================================================================

class TestEnergyCalculator:

    def test_init(self):
        ec = EnergyCalculator()
        assert ec.brain_power == 20.0
        assert ec.energy_per_spike > 0

    def test_spike_energy(self):
        ec = EnergyCalculator()
        e = ec.calculate_spike_energy(1000)
        assert e > 0

    def test_synaptic_energy(self):
        ec = EnergyCalculator()
        e = ec.calculate_synaptic_energy(1000, 1.0)
        assert e > 0

    def test_neuronal_energy(self):
        ec = EnergyCalculator()
        e = ec.calculate_neuronal_energy(100, 1.0)
        assert e > 0

    def test_plasticity_energy(self):
        ec = EnergyCalculator()
        e = ec.calculate_plasticity_energy(10)
        assert e > 0

    def test_total_energy_breakdown(self):
        ec = EnergyCalculator()
        bd = ec.calculate_total_energy(100, 1000, 50, 5, 0.001)
        assert "spike_energy" in bd
        assert "total_energy" in bd
        assert bd["total_energy"] > 0

    def test_efficiency_ratio_zero_ops(self):
        ec = EnergyCalculator()
        assert ec.calculate_efficiency_ratio(1.0, 0) == 0.0

    def test_efficiency_ratio(self):
        ec = EnergyCalculator()
        ratio = ec.calculate_efficiency_ratio(1e-10, 1000)
        assert ratio > 0

    def test_biological_efficiency(self):
        ec = EnergyCalculator()
        be = ec.biological_efficiency
        assert "spikes_per_joule" in be
        assert be["spikes_per_joule"] > 0


# ===================================================================
# MetabolicCost
# ===================================================================

class TestMetabolicCost:

    def test_defaults(self):
        mc = MetabolicCost()
        assert mc.spike_cost > 0

    def test_total_cost(self):
        mc = MetabolicCost()
        cost = mc.total_cost(num_spikes=100, num_synapses=500, num_neurons=50,
                            plasticity_events=5, memory_operations=10, dt=0.001)
        assert cost > 0


# ===================================================================
# EnergyType enum
# ===================================================================

class TestEnergyType:

    def test_values(self):
        assert EnergyType.COMPUTATIONAL.value == "computational"
        assert len(EnergyType) == 5


# ===================================================================
# SpikingNeuralNetwork (if importable, basic checks)
# ===================================================================

class TestSpikingNeuralNetwork:

    def test_creation(self):
        snn = SpikingNeuralNetwork(num_neurons=100)
        assert snn is not None
        assert snn.num_neurons == 100

    def test_custom_params(self):
        snn = SpikingNeuralNetwork(
            num_neurons=50,
            connection_probability=0.2,
            excitatory_ratio=0.7,
        )
        assert snn.connection_probability == 0.2
        assert snn.excitatory_ratio == 0.7

    def test_initial_state(self):
        snn = SpikingNeuralNetwork(num_neurons=20)
        assert snn.total_spikes == 0
        assert snn.current_time == 0.0


# ===================================================================
# MultiObjectiveOptimizer
# ===================================================================

class TestMultiObjectiveOptimizer:

    def test_init(self):
        moo = MultiObjectiveOptimizer(population_size=20)
        assert moo is not None
        assert moo.optimization_method == OptimizationMethod.MULTI_OBJECTIVE

    def test_dominates_with_fitness_components(self):
        moo = MultiObjectiveOptimizer(population_size=10)
        ind1 = Individual(genome=[], fitness=0.0,
                          metadata={"fitness_components": {"a": 0.8, "b": 0.9}})
        ind2 = Individual(genome=[], fitness=0.0,
                          metadata={"fitness_components": {"a": 0.7, "b": 0.8}})
        assert moo._dominates_multi_objective(ind1, ind2)

    def test_dominates_no_components_fallback(self):
        """Without fitness_components, falls back to simple fitness comparison."""
        moo = MultiObjectiveOptimizer(population_size=10)
        ind1 = Individual(genome=[], fitness=0.9)
        ind2 = Individual(genome=[], fitness=0.3)
        assert moo._dominates_multi_objective(ind1, ind2)

    def test_non_dominated_sorting(self):
        moo = MultiObjectiveOptimizer(population_size=10)
        individuals = [
            Individual(genome=[1], fitness=0.0,
                       metadata={"fitness_components": {"a": 0.9, "b": 0.9}}),
            Individual(genome=[2], fitness=0.0,
                       metadata={"fitness_components": {"a": 0.1, "b": 0.1}}),
            Individual(genome=[3], fitness=0.0,
                       metadata={"fitness_components": {"a": 0.5, "b": 0.5}}),
        ]
        fronts = moo._non_dominated_sorting(individuals)
        assert len(fronts) >= 1
        # ind with (0.9, 0.9) dominates all others → should be in front 0
        front0_genomes = [ind.genome for ind in fronts[0]]
        assert [1] in front0_genomes
