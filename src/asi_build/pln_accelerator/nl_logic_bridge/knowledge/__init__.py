"""
Knowledge systems and commonsense reasoning components.
"""

try:
    from .commonsense import CommonsenseReasoner
except (ImportError, ModuleNotFoundError, SyntaxError):
    CommonsenseReasoner = None
try:
    from .graph_builder import KnowledgeGraphBuilder
except (ImportError, ModuleNotFoundError, SyntaxError):
    KnowledgeGraphBuilder = None
try:
    from .conceptnet_integration import ConceptNetIntegration
except (ImportError, ModuleNotFoundError, SyntaxError):
    ConceptNetIntegration = None
try:
    from .cyc_integration import CycIntegration
except (ImportError, ModuleNotFoundError, SyntaxError):
    CycIntegration = None

__all__ = ["CommonsenseReasoner", "KnowledgeGraphBuilder", "ConceptNetIntegration", "CycIntegration"]