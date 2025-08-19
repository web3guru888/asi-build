"""
AGI Component Benchmark Suite

A comprehensive benchmark suite for measuring genuine AGI progress across
core cognitive capabilities, addressing Ben Goertzel's need for objective
AGI progress measurement.

This suite provides:
- Reasoning benchmarks (deductive, inductive, abductive, analogical)
- Learning benchmarks (one-shot, few-shot, continual, transfer)
- Memory benchmarks (episodic, semantic, procedural, working)
- Creativity benchmarks (novel problem solving, artistic generation)
- Consciousness benchmarks (self-awareness, metacognition, qualia)
- Symbolic AI specific benchmarks
- Neural-symbolic integration tests
- Real-world AGI challenges
- Progress tracking and analysis
"""

from .core import AGIBenchmarkSuite, BenchmarkRunner
from .config import BenchmarkConfig
from .reasoning import ReasoningBenchmarks
from .learning import LearningBenchmarks
from .memory import MemoryBenchmarks
from .creativity import CreativityBenchmarks
from .consciousness import ConsciousnessBenchmarks
from .symbolic import SymbolicAIBenchmarks
from .neural_symbolic import NeuralSymbolicBenchmarks
from .real_world import RealWorldAGIChallenges
from .tracking import ProgressTracker
from .analysis import BenchmarkAnalyzer

__version__ = "1.0.0"
__author__ = "Kenny AGI Reproducibility Platform"

__all__ = [
    "AGIBenchmarkSuite",
    "BenchmarkRunner", 
    "BenchmarkConfig",
    "ReasoningBenchmarks",
    "LearningBenchmarks",
    "MemoryBenchmarks",
    "CreativityBenchmarks",
    "ConsciousnessBenchmarks",
    "SymbolicAIBenchmarks",
    "NeuralSymbolicBenchmarks",
    "RealWorldAGIChallenges",
    "ProgressTracker",
    "BenchmarkAnalyzer"
]