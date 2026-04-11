"""
Consciousness Evolution Trackers
================================

Tools for tracking the evolution of consciousness during training and development.
"""

try:
    from .consciousness_evolution import ConsciousnessEvolutionTracker, ConsciousnessSnapshot
except (ImportError, ModuleNotFoundError, SyntaxError):
    ConsciousnessEvolutionTracker = None
    ConsciousnessSnapshot = None

__all__ = ['ConsciousnessEvolutionTracker', 'ConsciousnessSnapshot']
