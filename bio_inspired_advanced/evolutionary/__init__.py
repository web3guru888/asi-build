"""
Evolutionary Algorithm Optimization Module

Implements biological evolution-inspired optimization techniques including
genetic algorithms, genetic programming, and evolutionary strategies for
adaptive optimization of cognitive architectures.
"""

from .genetic_algorithms import GeneticAlgorithm, Individual, Population
from .genetic_programming import GeneticProgramming, GPTree, GPNode
from .evolutionary_strategies import EvolutionaryStrategy, CMAEvolutionaryStrategy
from .evolutionary_optimizer import EvolutionaryOptimizer, MultiObjectiveOptimizer

__all__ = [
    "GeneticAlgorithm",
    "Individual", 
    "Population",
    "GeneticProgramming",
    "GPTree",
    "GPNode",
    "EvolutionaryStrategy",
    "CMAEvolutionaryStrategy",
    "EvolutionaryOptimizer",
    "MultiObjectiveOptimizer"
]