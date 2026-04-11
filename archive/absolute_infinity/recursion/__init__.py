"""
Infinite Recursion Engine

This module implements recursion systems that transcend all mathematical and
logical limits, including stack overflow, fixed point theorems, and halting problems.
"""

from .infinite_recursion import InfiniteRecursionEngine, RecursionTranscender
from .fixed_point_transcendence import FixedPointTranscender
from .halting_transcendence import HaltingProblemTranscender
from .stack_overflow_immunity import StackOverflowTranscender

__all__ = [
    'InfiniteRecursionEngine',
    'RecursionTranscender',
    'FixedPointTranscender', 
    'HaltingProblemTranscender',
    'StackOverflowTranscender'
]