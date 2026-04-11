"""
Evolutionary Algorithm Optimization Module

Implements biological evolution-inspired optimization techniques including
genetic algorithms, genetic programming, and evolutionary strategies for
adaptive optimization of cognitive architectures.
"""

try:
    from .genetic_algorithms import GeneticAlgorithm, Individual, Population
except (ImportError, ModuleNotFoundError, SyntaxError):
    GeneticAlgorithm = None
    Individual = None
    Population = None
try:
    from .genetic_programming import GeneticProgramming, GPTree, GPNode
except (ImportError, ModuleNotFoundError, SyntaxError):
    GeneticProgramming = None
    GPTree = None
    GPNode = None
try:
    from .evolutionary_strategies import EvolutionaryStrategy, CMAEvolutionaryStrategy
except (ImportError, ModuleNotFoundError, SyntaxError):
    EvolutionaryStrategy = None
    CMAEvolutionaryStrategy = None
try:
    from .evolutionary_optimizer import EvolutionaryOptimizer, MultiObjectiveOptimizer
except (ImportError, ModuleNotFoundError, SyntaxError):
    EvolutionaryOptimizer = None
    MultiObjectiveOptimizer = None

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