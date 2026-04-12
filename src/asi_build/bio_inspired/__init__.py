"""
Bio-Inspired Cognitive Architecture for Kenny AGI

A comprehensive biological intelligence framework based on Ben Goertzel's research
into replicating biological intelligence principles in AGI systems.

This module implements:
- Neuromorphic computing with spiking neural networks
- Evolutionary optimization with genetic programming
- Homeostatic regulation with allostasis
- Developmental learning stages
- Neuromodulation systems
- Sleep/wake cycles and memory consolidation
- Emotional regulation and affective computing
- Embodied cognition with sensorimotor integration
- Neuroplasticity and synaptic pruning
- Hierarchical temporal memory
- Biologically plausible learning rules (STDP, BCM)
- Energy efficiency metrics
"""


def _safe_import(module_path, names):
    """Import names from a submodule, returning None for any that fail."""
    result = {}
    try:
        import importlib

        mod = importlib.import_module(module_path, package=__name__)
        for name in names:
            result[name] = getattr(mod, name, None)
    except (ImportError, ModuleNotFoundError, SyntaxError):
        for name in names:
            result[name] = None
    return result


_imports = {}
_imports.update(_safe_import(".core", ["BioCognitiveArchitecture"]))
_imports.update(_safe_import(".neuromorphic", ["SpikingNeuralNetwork", "NeuromorphicProcessor"]))
_imports.update(_safe_import(".evolutionary", ["EvolutionaryOptimizer", "GeneticProgramming"]))
_imports.update(_safe_import(".homeostatic", ["HomeostaticRegulator", "AllostasisController"]))
_imports.update(_safe_import(".developmental", ["DevelopmentalLearning", "CognitiveDevelopment"]))
_imports.update(
    _safe_import(".neuromodulation", ["NeuromodulationSystem", "NeurotransmitterManager"])
)
_imports.update(_safe_import(".sleep_wake", ["SleepWakeCycle", "MemoryConsolidation"]))
_imports.update(_safe_import(".emotional", ["EmotionalRegulation", "AffectiveComputing"]))
_imports.update(_safe_import(".embodied", ["EmbodiedCognition", "SensorimotorIntegration"]))
_imports.update(_safe_import(".neuroplasticity", ["NeuroplasticityManager", "SynapticPruning"]))
_imports.update(_safe_import(".hierarchical_memory", ["HierarchicalTemporalMemory", "HTMNetwork"]))
_imports.update(
    _safe_import(".learning_rules", ["STDPLearning", "BCMLearning", "BiologicalLearning"])
)
_imports.update(
    _safe_import(".energy_efficiency", ["EnergyMetrics", "BiologicalEfficiencyComparator"])
)
_imports.update(
    _safe_import(".kg_bridge", ["CognitiveStateKGBridge", "enable_kg_logging"])
)

# Promote to module namespace
globals().update(_imports)

__version__ = "1.0.0"
__author__ = "Kenny AGI Team"
__maturity__ = "beta"
__description__ = "Bio-Inspired Cognitive Architecture for Ben Goertzel's AGI Research"

__all__ = [
    "BioCognitiveArchitecture",
    "SpikingNeuralNetwork",
    "NeuromorphicProcessor",
    "EvolutionaryOptimizer",
    "GeneticProgramming",
    "HomeostaticRegulator",
    "AllostasisController",
    "DevelopmentalLearning",
    "CognitiveDevelopment",
    "NeuromodulationSystem",
    "NeurotransmitterManager",
    "SleepWakeCycle",
    "MemoryConsolidation",
    "EmotionalRegulation",
    "AffectiveComputing",
    "EmbodiedCognition",
    "SensorimotorIntegration",
    "NeuroplasticityManager",
    "SynapticPruning",
    "HierarchicalTemporalMemory",
    "HTMNetwork",
    "STDPLearning",
    "BCMLearning",
    "BiologicalLearning",
    "EnergyMetrics",
    "BiologicalEfficiencyComparator",
    "CognitiveStateKGBridge",
    "enable_kg_logging",
]
