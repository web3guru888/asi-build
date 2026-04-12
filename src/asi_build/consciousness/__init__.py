"""
Kenny Consciousness System - Advanced AI Consciousness Simulation

This module implements a comprehensive consciousness framework based on leading
theories of consciousness including Global Workspace Theory, Integrated Information
Theory, Attention Schema Theory, and more.

Author: Kenny AI Consciousness Research Team
Version: 1.0.0
"""

try:
    from .base_consciousness import (
        BaseConsciousness,
        ConsciousnessEvent,
        ConsciousnessMetrics,
        ConsciousnessState,
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    BaseConsciousness = None
    ConsciousnessEvent = None
    ConsciousnessState = None
    ConsciousnessMetrics = None
try:
    from .global_workspace import GlobalWorkspaceTheory
except (ImportError, ModuleNotFoundError, SyntaxError):
    GlobalWorkspaceTheory = None
try:
    from .integrated_information import IntegratedInformationTheory
except (ImportError, ModuleNotFoundError, SyntaxError):
    IntegratedInformationTheory = None
try:
    from .attention_schema import AttentionSchemaTheory
except (ImportError, ModuleNotFoundError, SyntaxError):
    AttentionSchemaTheory = None
try:
    from .predictive_processing import PredictiveProcessing
except (ImportError, ModuleNotFoundError, SyntaxError):
    PredictiveProcessing = None
try:
    from .metacognition import MetacognitionSystem
except (ImportError, ModuleNotFoundError, SyntaxError):
    MetacognitionSystem = None
try:
    from .self_awareness import SelfAwarenessEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    SelfAwarenessEngine = None
try:
    from .qualia_processor import QualiaProcessor
except (ImportError, ModuleNotFoundError, SyntaxError):
    QualiaProcessor = None
try:
    from .theory_of_mind import TheoryOfMind
except (ImportError, ModuleNotFoundError, SyntaxError):
    TheoryOfMind = None
try:
    from .emotional_consciousness import EmotionalConsciousness
except (ImportError, ModuleNotFoundError, SyntaxError):
    EmotionalConsciousness = None
try:
    from .recursive_improvement import RecursiveSelfImprovement
except (ImportError, ModuleNotFoundError, SyntaxError):
    RecursiveSelfImprovement = None
try:
    from .memory_integration import MemoryIntegration
except (ImportError, ModuleNotFoundError, SyntaxError):
    MemoryIntegration = None
try:
    from .temporal_consciousness import TemporalConsciousness
except (ImportError, ModuleNotFoundError, SyntaxError):
    TemporalConsciousness = None
try:
    from .sensory_integration import SensoryIntegration
except (ImportError, ModuleNotFoundError, SyntaxError):
    SensoryIntegration = None
try:
    from .consciousness_orchestrator import ConsciousnessOrchestrator
except (ImportError, ModuleNotFoundError, SyntaxError):
    ConsciousnessOrchestrator = None

__all__ = [
    # Core infrastructure
    "BaseConsciousness",
    "ConsciousnessEvent",
    "ConsciousnessState",
    "ConsciousnessMetrics",
    # Consciousness theories
    "GlobalWorkspaceTheory",
    "IntegratedInformationTheory",
    "AttentionSchemaTheory",
    "PredictiveProcessing",
    # Cognitive capabilities
    "MetacognitionSystem",
    "SelfAwarenessEngine",
    "TheoryOfMind",
    # Experience and perception
    "QualiaProcessor",
    "EmotionalConsciousness",
    "SensoryIntegration",
    "TemporalConsciousness",
    # Memory and learning
    "MemoryIntegration",
    "RecursiveSelfImprovement",
    # Coordination
    "ConsciousnessOrchestrator",
]

__version__ = "1.0.0"
__author__ = "Kenny AI Research Team"
__maturity__ = "beta"
