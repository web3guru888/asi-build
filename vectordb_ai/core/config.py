"""
Configuration management for Kenny Vector Database System

This module handles configuration for all vector database integrations,
embedding models, and search parameters.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class DatabaseConfig:
    """Base configuration for database connections."""
    host: str = "localhost"
    port: int = 8080
    api_key: Optional[str] = None
    environment: str = "production"
    timeout: int = 30
    max_retries: int = 3
    
@dataclass 
class PineconeConfig(DatabaseConfig):
    """Pinecone-specific configuration."""
    environment: str = "us-east1-aws"
    index_name: str = "kenny-vectors"
    dimension: int = 1536
    metric: str = "cosine"
    replicas: int = 1
    shards: int = 1
    
@dataclass
class WeaviateConfig(DatabaseConfig):
    """Weaviate-specific configuration."""
    port: int = 8080
    grpc_port: int = 50051
    scheme: str = "http"
    auth_client_secret: Optional[str] = None
    startup_period: int = 5
    
@dataclass
class QdrantConfig(DatabaseConfig):
    """Qdrant-specific configuration."""
    port: int = 6333
    grpc_port: int = 6334
    prefer_grpc: bool = False
    https: bool = False
    collection_name: str = "kenny-collection"
    vector_size: int = 1536
    distance: str = "Cosine"
    
@dataclass
class EmbeddingConfig:
    """Configuration for embedding models."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    model_type: str = "sentence_transformers"  # huggingface, openai, cohere
    api_key: Optional[str] = None
    batch_size: int = 32
    max_length: int = 512
    normalize_embeddings: bool = True
    cache_embeddings: bool = True
    cache_dir: str = "./embeddings_cache"
    
@dataclass
class SearchConfig:
    """Configuration for search operations."""
    top_k: int = 10
    score_threshold: float = 0.7
    rerank: bool = True
    rerank_top_k: int = 100
    enable_filters: bool = True
    enable_hybrid_search: bool = True
    alpha: float = 0.5  # Hybrid search weight
    
class VectorDBConfig:
    """Main configuration manager for Kenny Vector Database."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
        """
        self.config_path = config_path
        self._config = self._load_config()
        
        # Initialize sub-configurations
        self.pinecone = self._init_pinecone_config()
        self.weaviate = self._init_weaviate_config() 
        self.qdrant = self._init_qdrant_config()
        self.embedding = self._init_embedding_config()
        self.search = self._init_search_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment variables."""
        config = {}
        
        # Load from file if provided
        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)
                    
        # Override with environment variables
        env_config = self._load_from_env()
        config.update(env_config)
        
        return config
        
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # Pinecone
        if os.getenv('PINECONE_API_KEY'):
            env_config.setdefault('pinecone', {})['api_key'] = os.getenv('PINECONE_API_KEY')
        if os.getenv('PINECONE_ENVIRONMENT'):
            env_config.setdefault('pinecone', {})['environment'] = os.getenv('PINECONE_ENVIRONMENT')
        if os.getenv('PINECONE_INDEX_NAME'):
            env_config.setdefault('pinecone', {})['index_name'] = os.getenv('PINECONE_INDEX_NAME')
            
        # Weaviate
        if os.getenv('WEAVIATE_HOST'):
            env_config.setdefault('weaviate', {})['host'] = os.getenv('WEAVIATE_HOST')
        if os.getenv('WEAVIATE_API_KEY'):
            env_config.setdefault('weaviate', {})['api_key'] = os.getenv('WEAVIATE_API_KEY')
            
        # Qdrant
        if os.getenv('QDRANT_HOST'):
            env_config.setdefault('qdrant', {})['host'] = os.getenv('QDRANT_HOST')
        if os.getenv('QDRANT_API_KEY'):
            env_config.setdefault('qdrant', {})['api_key'] = os.getenv('QDRANT_API_KEY')
        if os.getenv('QDRANT_COLLECTION_NAME'):
            env_config.setdefault('qdrant', {})['collection_name'] = os.getenv('QDRANT_COLLECTION_NAME')
            
        # Embedding
        if os.getenv('OPENAI_API_KEY'):
            env_config.setdefault('embedding', {})['api_key'] = os.getenv('OPENAI_API_KEY')
        if os.getenv('EMBEDDING_MODEL'):
            env_config.setdefault('embedding', {})['model_name'] = os.getenv('EMBEDDING_MODEL')
            
        return env_config
        
    def _init_pinecone_config(self) -> PineconeConfig:
        """Initialize Pinecone configuration."""
        pinecone_config = self._config.get('pinecone', {})
        return PineconeConfig(**pinecone_config)
        
    def _init_weaviate_config(self) -> WeaviateConfig:
        """Initialize Weaviate configuration."""
        weaviate_config = self._config.get('weaviate', {})
        return WeaviateConfig(**weaviate_config)
        
    def _init_qdrant_config(self) -> QdrantConfig:
        """Initialize Qdrant configuration."""
        qdrant_config = self._config.get('qdrant', {})
        return QdrantConfig(**qdrant_config)
        
    def _init_embedding_config(self) -> EmbeddingConfig:
        """Initialize embedding configuration."""
        embedding_config = self._config.get('embedding', {})
        return EmbeddingConfig(**embedding_config)
        
    def _init_search_config(self) -> SearchConfig:
        """Initialize search configuration."""
        search_config = self._config.get('search', {})
        return SearchConfig(**search_config)
        
    def get_database_config(self, database_type: str) -> Union[PineconeConfig, WeaviateConfig, QdrantConfig]:
        """Get configuration for specific database type."""
        database_type = database_type.lower()
        
        if database_type == "pinecone":
            return self.pinecone
        elif database_type == "weaviate":
            return self.weaviate
        elif database_type == "qdrant":
            return self.qdrant
        else:
            raise ValueError(f"Unsupported database type: {database_type}")
            
    def save_config(self, output_path: str):
        """Save current configuration to file."""
        config_dict = {
            'pinecone': asdict(self.pinecone),
            'weaviate': asdict(self.weaviate),
            'qdrant': asdict(self.qdrant),
            'embedding': asdict(self.embedding),
            'search': asdict(self.search)
        }
        
        with open(output_path, 'w') as f:
            if output_path.endswith('.yaml') or output_path.endswith('.yml'):
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            else:
                json.dump(config_dict, f, indent=2)
                
    def update_config(self, database_type: str, **kwargs):
        """Update configuration for specific database type."""
        database_type = database_type.lower()
        
        if database_type == "pinecone":
            for key, value in kwargs.items():
                setattr(self.pinecone, key, value)
        elif database_type == "weaviate":
            for key, value in kwargs.items():
                setattr(self.weaviate, key, value)
        elif database_type == "qdrant":
            for key, value in kwargs.items():
                setattr(self.qdrant, key, value)
        elif database_type == "embedding":
            for key, value in kwargs.items():
                setattr(self.embedding, key, value)
        elif database_type == "search":
            for key, value in kwargs.items():
                setattr(self.search, key, value)
        else:
            raise ValueError(f"Unsupported config type: {database_type}")
            
    def validate_config(self) -> bool:
        """Validate configuration settings."""
        try:
            # Validate Pinecone config
            if self.pinecone.api_key:
                assert isinstance(self.pinecone.dimension, int) and self.pinecone.dimension > 0
                assert self.pinecone.metric in ["cosine", "euclidean", "dotproduct"]
                
            # Validate embedding config
            assert isinstance(self.embedding.batch_size, int) and self.embedding.batch_size > 0
            assert isinstance(self.embedding.max_length, int) and self.embedding.max_length > 0
            
            # Validate search config
            assert isinstance(self.search.top_k, int) and self.search.top_k > 0
            assert 0 <= self.search.score_threshold <= 1
            assert 0 <= self.search.alpha <= 1
            
            return True
            
        except AssertionError:
            return False
            
    @classmethod
    def create_default_config(cls, output_path: str):
        """Create a default configuration file."""
        default_config = cls()
        default_config.save_config(output_path)
        return default_config