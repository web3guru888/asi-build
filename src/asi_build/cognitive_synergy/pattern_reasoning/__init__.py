"""
Pattern Mining ↔ Reasoning Integration Module
=============================================

Implements bidirectional information flow between pattern mining and reasoning
processes, enabling emergent cognitive capabilities through their synergy.
"""

try:
    from .pattern_mining_engine import PatternMiningEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    PatternMiningEngine = None
try:
    from .reasoning_engine import ReasoningEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    ReasoningEngine = None
try:
    from .pattern_reasoning_synergy import PatternReasoningSynergy
except (ImportError, ModuleNotFoundError, SyntaxError):
    PatternReasoningSynergy = None

__all__ = ["PatternMiningEngine", "ReasoningEngine", "PatternReasoningSynergy"]
