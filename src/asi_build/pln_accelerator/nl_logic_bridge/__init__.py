"""
Natural Language ↔ Logic Bridge for Ben Goertzel's Symbolic-Neural AGI Vision

This system provides a comprehensive bridge between natural language and formal
logical representations, enabling seamless translation between human communication
and symbolic AI reasoning systems.

Core Components:
- PLN rule extraction from natural language
- Logic-to-explanation generation
- Commonsense reasoning integration
- Semantic parsing with compositional semantics
- Natural language generation from logical forms
- Ambiguity resolution and context handling
- Multi-lingual support
- Interactive query interfaces
- Knowledge graph construction
- Real-time symbolic-natural language translation

Author: Kenny (with Ben Goertzel's AGI vision)
Version: 1.0.0
"""

try:
    from .core.bridge import NLLogicBridge
except (ImportError, ModuleNotFoundError, SyntaxError):
    NLLogicBridge = None
try:
    from .core.architecture import BridgeArchitecture
except (ImportError, ModuleNotFoundError, SyntaxError):
    BridgeArchitecture = None
try:
    from .parsers.semantic_parser import SemanticParser
except (ImportError, ModuleNotFoundError, SyntaxError):
    SemanticParser = None
try:
    from .parsers.pln_extractor import PLNExtractor
except (ImportError, ModuleNotFoundError, SyntaxError):
    PLNExtractor = None
try:
    from .generators.explanation_generator import ExplanationGenerator
except (ImportError, ModuleNotFoundError, SyntaxError):
    ExplanationGenerator = None
try:
    from .generators.nl_generator import NLGenerator
except (ImportError, ModuleNotFoundError, SyntaxError):
    NLGenerator = None
try:
    from .knowledge.commonsense import CommonsenseReasoner
except (ImportError, ModuleNotFoundError, SyntaxError):
    CommonsenseReasoner = None
try:
    from .knowledge.graph_builder import KnowledgeGraphBuilder
except (ImportError, ModuleNotFoundError, SyntaxError):
    KnowledgeGraphBuilder = None
try:
    from .interfaces.query_interface import QueryInterface
except (ImportError, ModuleNotFoundError, SyntaxError):
    QueryInterface = None
try:
    from .models.transformer_models import TransformerModels
except (ImportError, ModuleNotFoundError, SyntaxError):
    TransformerModels = None

__version__ = "1.0.0"
__author__ = "Kenny"
__description__ = "Natural Language ↔ Logic Bridge for Symbolic-Neural AGI"

__all__ = [
    "NLLogicBridge",
    "BridgeArchitecture",
    "SemanticParser",
    "PLNExtractor",
    "ExplanationGenerator",
    "NLGenerator",
    "CommonsenseReasoner",
    "KnowledgeGraphBuilder",
    "QueryInterface",
    "TransformerModels",
]
