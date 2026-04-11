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

from .core import BioCognitiveArchitecture
from .neuromorphic import SpikingNeuralNetwork, NeuromorphicProcessor
from .evolutionary import EvolutionaryOptimizer, GeneticProgramming
from .homeostatic import HomeostaticRegulator, AllostasisController
from .developmental import DevelopmentalLearning, CognitiveDevelopment
from .neuromodulation import NeuromodulationSystem, NeurotransmitterManager
from .sleep_wake import SleepWakeCycle, MemoryConsolidation
from .emotional import EmotionalRegulation, AffectiveComputing
from .embodied import EmbodiedCognition, SensorimotorIntegration
from .neuroplasticity import NeuroplasticityManager, SynapticPruning
from .hierarchical_memory import HierarchicalTemporalMemory, HTMNetwork
from .learning_rules import STDPLearning, BCMLearning, BiologicalLearning
from .energy_efficiency import EnergyMetrics, BiologicalEfficiencyComparator

__version__ = "1.0.0"
__author__ = "Kenny AGI Team"
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
    "BiologicalEfficiencyComparator"
]