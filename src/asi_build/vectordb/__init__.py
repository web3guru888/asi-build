"""
Kenny Vector Database - Advanced Vector Database Integration System

This module provides comprehensive vector database capabilities with support for:
- Pinecone (cloud-native vector database)
- Weaviate (open-source vector database)
- Qdrant (vector similarity search engine)
- Embedding generation pipeline
- Semantic search capabilities
- Unified indexing and retrieval APIs

Author: Kenny AGI System
Version: 1.0.0
"""

from .core.config import VectorDBConfig
from .core.embeddings import EmbeddingPipeline
from .core.search import SemanticSearchEngine
from .databases.pinecone_client import PineconeClient
from .databases.weaviate_client import WeaviateClient
from .databases.qdrant_client import QdrantClient
from .api.unified_client import UnifiedVectorDB
from .api.indexing import IndexingAPI
from .api.retrieval import RetrievalAPI

__version__ = "1.0.0"
__author__ = "Kenny AGI System"

__all__ = [
    "VectorDBConfig",
    "EmbeddingPipeline", 
    "SemanticSearchEngine",
    "PineconeClient",
    "WeaviateClient", 
    "QdrantClient",
    "UnifiedVectorDB",
    "IndexingAPI",
    "RetrievalAPI"
]

def get_version():
    """Return the version of the Kenny Vector Database system."""
    return __version__

def list_available_databases():
    """Return a list of supported vector databases."""
    return ["pinecone", "weaviate", "qdrant"]

def create_client(database_type: str, **config):
    """Factory method to create vector database clients."""
    database_type = database_type.lower()
    
    if database_type == "pinecone":
        return PineconeClient(**config)
    elif database_type == "weaviate":
        return WeaviateClient(**config)
    elif database_type == "qdrant":
        return QdrantClient(**config)
    elif database_type == "unified":
        return UnifiedVectorDB(**config)
    else:
        raise ValueError(f"Unsupported database type: {database_type}")