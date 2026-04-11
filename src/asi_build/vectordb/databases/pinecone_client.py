"""
Pinecone vector database client for Kenny Vector Database System

This module provides comprehensive integration with Pinecone, including:
- Index management and configuration
- Vector operations (upsert, query, delete)
- Metadata filtering and search
- Batch operations and error handling
"""

import time
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
import numpy as np

try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

from ..core.config import PineconeConfig

logger = logging.getLogger(__name__)

@dataclass
class PineconeSearchResult:
    """Container for Pinecone search results."""
    id: str
    score: float
    metadata: Dict[str, Any]
    values: Optional[List[float]] = None

@dataclass
class PineconeStats:
    """Container for Pinecone index statistics."""
    vector_count: int
    index_fullness: float
    dimension: int
    index_size: int

class PineconeClient:
    """
    Pinecone vector database client for Kenny AGI system.
    
    Provides comprehensive vector database operations including indexing,
    searching, and management of vector embeddings with metadata.
    """
    
    def __init__(self, config: PineconeConfig):
        """
        Initialize Pinecone client.
        
        Args:
            config: Pinecone configuration object
        """
        if not PINECONE_AVAILABLE:
            raise ImportError("pinecone-client not available. Install with: pip install pinecone-client")
            
        self.config = config
        self._initialize_client()
        self._index = None
        
    def _initialize_client(self):
        """Initialize Pinecone client and connection."""
        if not self.config.api_key:
            raise ValueError("Pinecone API key is required")
            
        try:
            pinecone.init(
                api_key=self.config.api_key,
                environment=self.config.environment
            )
            logger.info(f"Initialized Pinecone client for environment: {self.config.environment}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {str(e)}")
            raise
            
    def create_index(self, 
                    index_name: Optional[str] = None,
                    dimension: Optional[int] = None,
                    metric: Optional[str] = None,
                    replicas: Optional[int] = None,
                    shards: Optional[int] = None,
                    metadata_config: Optional[Dict] = None) -> bool:
        """
        Create a new Pinecone index.
        
        Args:
            index_name: Name of the index (default from config)
            dimension: Vector dimension (default from config) 
            metric: Distance metric (default from config)
            replicas: Number of replicas (default from config)
            shards: Number of shards (default from config)
            metadata_config: Metadata configuration
            
        Returns:
            True if index created successfully
        """
        index_name = index_name or self.config.index_name
        dimension = dimension or self.config.dimension
        metric = metric or self.config.metric
        replicas = replicas or self.config.replicas
        shards = shards or self.config.shards
        
        try:
            # Check if index already exists
            if index_name in pinecone.list_indexes():
                logger.warning(f"Index '{index_name}' already exists")
                return True
                
            # Create index
            pinecone.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                replicas=replicas,
                shards=shards,
                metadata_config=metadata_config or {}
            )
            
            # Wait for index to be ready
            while index_name not in pinecone.list_indexes():
                time.sleep(1)
                
            logger.info(f"Created Pinecone index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index '{index_name}': {str(e)}")
            return False
            
    def delete_index(self, index_name: Optional[str] = None) -> bool:
        """
        Delete a Pinecone index.
        
        Args:
            index_name: Name of the index to delete
            
        Returns:
            True if index deleted successfully
        """
        index_name = index_name or self.config.index_name
        
        try:
            if index_name not in pinecone.list_indexes():
                logger.warning(f"Index '{index_name}' does not exist")
                return True
                
            pinecone.delete_index(index_name)
            logger.info(f"Deleted Pinecone index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete index '{index_name}': {str(e)}")
            return False
            
    def connect(self, index_name: Optional[str] = None) -> bool:
        """
        Connect to a Pinecone index.
        
        Args:
            index_name: Name of the index to connect to
            
        Returns:
            True if connection successful
        """
        index_name = index_name or self.config.index_name
        
        try:
            if index_name not in pinecone.list_indexes():
                logger.error(f"Index '{index_name}' does not exist")
                return False
                
            self._index = pinecone.Index(index_name)
            logger.info(f"Connected to Pinecone index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to index '{index_name}': {str(e)}")
            return False
            
    def disconnect(self):
        """Disconnect from the current index."""
        self._index = None
        logger.info("Disconnected from Pinecone index")
        
    def _ensure_connected(self):
        """Ensure connection to index exists."""
        if self._index is None:
            if not self.connect():
                raise RuntimeError("Not connected to any Pinecone index")
                
    def upsert_vectors(self, 
                      vectors: List[Tuple[str, List[float], Dict[str, Any]]],
                      namespace: str = "",
                      batch_size: int = 100) -> bool:
        """
        Upsert vectors to the index.
        
        Args:
            vectors: List of (id, vector, metadata) tuples
            namespace: Namespace for vectors
            batch_size: Batch size for upsert operations
            
        Returns:
            True if upsert successful
        """
        self._ensure_connected()
        
        try:
            # Process in batches
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                
                # Convert to Pinecone format
                upsert_data = []
                for vec_id, vector, metadata in batch:
                    upsert_data.append({
                        'id': vec_id,
                        'values': vector,
                        'metadata': metadata or {}
                    })
                    
                # Upsert batch
                self._index.upsert(
                    vectors=upsert_data,
                    namespace=namespace
                )
                
                logger.debug(f"Upserted batch {i//batch_size + 1}/{(len(vectors)-1)//batch_size + 1}")
                
            logger.info(f"Upserted {len(vectors)} vectors to Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {str(e)}")
            return False
            
    def upsert_single(self, 
                     vec_id: str,
                     vector: List[float],
                     metadata: Optional[Dict[str, Any]] = None,
                     namespace: str = "") -> bool:
        """
        Upsert a single vector.
        
        Args:
            vec_id: Vector ID
            vector: Vector values
            metadata: Vector metadata
            namespace: Namespace for vector
            
        Returns:
            True if upsert successful
        """
        return self.upsert_vectors([(vec_id, vector, metadata or {})], namespace)
        
    def query_vectors(self,
                     query_vector: List[float],
                     top_k: int = 10,
                     namespace: str = "",
                     filter_dict: Optional[Dict[str, Any]] = None,
                     include_values: bool = False,
                     include_metadata: bool = True) -> List[PineconeSearchResult]:
        """
        Query vectors from the index.
        
        Args:
            query_vector: Query vector
            top_k: Number of results to return
            namespace: Namespace to query
            filter_dict: Metadata filter
            include_values: Include vector values in results
            include_metadata: Include metadata in results
            
        Returns:
            List of search results
        """
        self._ensure_connected()
        
        try:
            response = self._index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter_dict,
                include_values=include_values,
                include_metadata=include_metadata
            )
            
            # Convert to search results
            results = []
            for match in response.matches:
                result = PineconeSearchResult(
                    id=match.id,
                    score=match.score,
                    metadata=match.metadata if include_metadata else {},
                    values=match.values if include_values else None
                )
                results.append(result)
                
            logger.debug(f"Query returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to query vectors: {str(e)}")
            return []
            
    def query_by_id(self,
                   vec_ids: List[str],
                   namespace: str = "",
                   include_values: bool = True,
                   include_metadata: bool = True) -> List[PineconeSearchResult]:
        """
        Fetch vectors by IDs.
        
        Args:
            vec_ids: List of vector IDs
            namespace: Namespace to query
            include_values: Include vector values
            include_metadata: Include metadata
            
        Returns:
            List of search results
        """
        self._ensure_connected()
        
        try:
            response = self._index.fetch(
                ids=vec_ids,
                namespace=namespace,
                include_values=include_values,
                include_metadata=include_metadata
            )
            
            # Convert to search results
            results = []
            for vec_id, vector_data in response.vectors.items():
                result = PineconeSearchResult(
                    id=vec_id,
                    score=1.0,  # Perfect match for ID lookup
                    metadata=vector_data.metadata if include_metadata else {},
                    values=vector_data.values if include_values else None
                )
                results.append(result)
                
            logger.debug(f"Fetched {len(results)} vectors by ID")
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch vectors by ID: {str(e)}")
            return []
            
    def delete_vectors(self, 
                      vec_ids: Optional[List[str]] = None,
                      namespace: str = "",
                      filter_dict: Optional[Dict[str, Any]] = None,
                      delete_all: bool = False) -> bool:
        """
        Delete vectors from the index.
        
        Args:
            vec_ids: List of vector IDs to delete
            namespace: Namespace to delete from
            filter_dict: Metadata filter for deletion
            delete_all: Delete all vectors in namespace
            
        Returns:
            True if deletion successful
        """
        self._ensure_connected()
        
        try:
            if delete_all:
                self._index.delete(delete_all=True, namespace=namespace)
                logger.info(f"Deleted all vectors from namespace '{namespace}'")
            elif vec_ids:
                self._index.delete(ids=vec_ids, namespace=namespace)
                logger.info(f"Deleted {len(vec_ids)} vectors from Pinecone")
            elif filter_dict:
                self._index.delete(filter=filter_dict, namespace=namespace)
                logger.info("Deleted vectors matching filter from Pinecone")
            else:
                logger.warning("No deletion criteria specified")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vectors: {str(e)}")
            return False
            
    def get_index_stats(self, namespace: str = "") -> Optional[PineconeStats]:
        """
        Get index statistics.
        
        Args:
            namespace: Namespace to get stats for
            
        Returns:
            Index statistics
        """
        self._ensure_connected()
        
        try:
            stats = self._index.describe_index_stats()
            
            namespace_stats = stats.namespaces.get(namespace, stats.total_vector_count)
            
            return PineconeStats(
                vector_count=namespace_stats.vector_count if hasattr(namespace_stats, 'vector_count') else stats.total_vector_count,
                index_fullness=stats.index_fullness,
                dimension=stats.dimension,
                index_size=getattr(stats, 'index_size', 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {str(e)}")
            return None
            
    def list_indexes(self) -> List[str]:
        """
        List all available indexes.
        
        Returns:
            List of index names
        """
        try:
            return pinecone.list_indexes()
        except Exception as e:
            logger.error(f"Failed to list indexes: {str(e)}")
            return []
            
    def update_metadata(self,
                       vec_id: str,
                       metadata: Dict[str, Any],
                       namespace: str = "") -> bool:
        """
        Update metadata for a vector.
        
        Args:
            vec_id: Vector ID
            metadata: New metadata
            namespace: Namespace
            
        Returns:
            True if update successful
        """
        self._ensure_connected()
        
        try:
            self._index.update(
                id=vec_id,
                set_metadata=metadata,
                namespace=namespace
            )
            
            logger.debug(f"Updated metadata for vector '{vec_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {str(e)}")
            return False
            
    def similarity_search(self,
                         query_vector: List[float],
                         top_k: int = 10,
                         threshold: float = 0.0,
                         namespace: str = "",
                         filter_dict: Optional[Dict[str, Any]] = None) -> List[PineconeSearchResult]:
        """
        Perform similarity search with score threshold.
        
        Args:
            query_vector: Query vector
            top_k: Number of results
            threshold: Minimum similarity score
            namespace: Namespace to search
            filter_dict: Metadata filter
            
        Returns:
            Filtered search results
        """
        results = self.query_vectors(
            query_vector=query_vector,
            top_k=top_k,
            namespace=namespace,
            filter_dict=filter_dict
        )
        
        # Filter by threshold
        filtered_results = [r for r in results if r.score >= threshold]
        
        return filtered_results
        
    def batch_query(self,
                   query_vectors: List[List[float]],
                   top_k: int = 10,
                   namespace: str = "",
                   filter_dict: Optional[Dict[str, Any]] = None) -> List[List[PineconeSearchResult]]:
        """
        Perform batch queries.
        
        Args:
            query_vectors: List of query vectors
            top_k: Number of results per query
            namespace: Namespace to search
            filter_dict: Metadata filter
            
        Returns:
            List of result lists
        """
        all_results = []
        
        for query_vector in query_vectors:
            results = self.query_vectors(
                query_vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter_dict=filter_dict
            )
            all_results.append(results)
            
        return all_results
        
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Pinecone connection.
        
        Returns:
            Health status information
        """
        try:
            indexes = self.list_indexes()
            connected = self._index is not None
            
            if connected:
                stats = self.get_index_stats()
                
                return {
                    "status": "healthy",
                    "connected": True,
                    "index_name": self.config.index_name,
                    "available_indexes": indexes,
                    "vector_count": stats.vector_count if stats else 0,
                    "dimension": stats.dimension if stats else 0
                }
            else:
                return {
                    "status": "disconnected",
                    "connected": False,
                    "available_indexes": indexes
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "connected": False
            }