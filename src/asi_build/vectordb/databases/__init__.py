"""Database clients for the Kenny Vector Database system."""

try:
    from .pinecone_client import PineconeClient
except (ImportError, ModuleNotFoundError, SyntaxError):
    PineconeClient = None
try:
    from .weaviate_client import WeaviateClient
except (ImportError, ModuleNotFoundError, SyntaxError):
    WeaviateClient = None
try:
    from .qdrant_client import QdrantClient
except (ImportError, ModuleNotFoundError, SyntaxError):
    QdrantClient = None

__all__ = [
    "PineconeClient",
    "WeaviateClient",
    "QdrantClient"
]