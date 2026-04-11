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

from .core.bridge import NLLogicBridge
from .core.architecture import BridgeArchitecture
from .parsers.semantic_parser import SemanticParser
from .parsers.pln_extractor import PLNExtractor
from .generators.explanation_generator import ExplanationGenerator
from .generators.nl_generator import NLGenerator
from .knowledge.commonsense import CommonsenseReasoner
from .knowledge.graph_builder import KnowledgeGraphBuilder
from .interfaces.query_interface import QueryInterface
from .models.transformer_models import TransformerModels

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
    "TransformerModels"
]