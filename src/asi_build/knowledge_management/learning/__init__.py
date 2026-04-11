"""
Learning Module - Contextual Knowledge Learning
==============================================

Adaptive learning system for knowledge processing optimization.
"""

try:
    from .contextual_learner import (
        AdaptationRule,
        ContextualLearner,
        LearningEvent,
        LearningPattern,
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    ContextualLearner = None
    LearningPattern = None
    LearningEvent = None
    AdaptationRule = None

__all__ = ["ContextualLearner", "LearningPattern", "LearningEvent", "AdaptationRule"]
