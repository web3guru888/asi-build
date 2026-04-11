"""API components for the Kenny Vector Database system."""

try:
    from .unified_client import UnifiedVectorDB
except (ImportError, ModuleNotFoundError, SyntaxError):
    UnifiedVectorDB = None
try:
    from .indexing import IndexingAPI
except (ImportError, ModuleNotFoundError, SyntaxError):
    IndexingAPI = None
try:
    from .retrieval import RetrievalAPI
except (ImportError, ModuleNotFoundError, SyntaxError):
    RetrievalAPI = None

__all__ = [
    "UnifiedVectorDB",
    "IndexingAPI", 
    "RetrievalAPI"
]