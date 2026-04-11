"""
ASI:BUILD Hybrid Reasoning Engine

Advanced reasoning system combining symbolic logic, neural networks,
and quantum-inspired processing for superhuman cognitive capabilities.

This module implements Dr. Ben Goertzel's vision of cognitive synergy
through integrated reasoning architectures.
"""

try:
    from .hybrid_reasoning import HybridReasoningEngine, ReasoningMode
except (ImportError, ModuleNotFoundError, SyntaxError):
    HybridReasoningEngine = None
    ReasoningMode = None
try:
    from .symbolic_processing import SymbolicProcessor, LogicalReasoner, PLNEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    SymbolicProcessor = None
    LogicalReasoner = None
    PLNEngine = None
try:
    from .neural_networks import NeuralProcessor, TransformerReasoner, MultimodalNetwork
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeuralProcessor = None
    TransformerReasoner = None
    MultimodalNetwork = None
try:
    from .quantum_reasoning import QuantumReasoningEngine, QuantumLogic
except (ImportError, ModuleNotFoundError, SyntaxError):
    QuantumReasoningEngine = None
    QuantumLogic = None
try:
    from .cognitive_architectures import CognitiveArchitecture, OpenCogIntegration
except (ImportError, ModuleNotFoundError, SyntaxError):
    CognitiveArchitecture = None
    OpenCogIntegration = None

__all__ = [
    "HybridReasoningEngine",
    "ReasoningMode",
    "SymbolicProcessor", 
    "LogicalReasoner",
    "PLNEngine",
    "NeuralProcessor",
    "TransformerReasoner",
    "MultimodalNetwork",
    "QuantumReasoningEngine",
    "QuantumLogic",
    "CognitiveArchitecture",
    "OpenCogIntegration"
]