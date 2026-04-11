"""
Qdrant vector database client for Kenny Vector Database System

This module provides comprehensive integration with Qdrant, including:
- Collection management and configuration
- Vector operations with payload filtering
- Similarity search with advanced filtering
- Batch operations and clustering
- Performance optimization and monitoring
"""

import time
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
import numpy as np
import uuid

try:
    from qdrant_client import QdrantClient as QdrantClientBase
    from qdrant_client.models import (
        Distance, VectorParams, CollectionStatus, SearchRequest,
        PointStruct, Filter, FieldCondition, Range, MatchValue,
        CountRequest, ScrollRequest, UpdateResult, PointsSelector,
        PointIdsList, FilterSelector, OptimizersConfigDiff,
        CreateCollection, UpdateCollection
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    # Provide stub names so the module can be imported without qdrant_client installed
    QdrantClientBase = None
    Distance = VectorParams = CollectionStatus = SearchRequest = None
    PointStruct = Filter = FieldCondition = Range = MatchValue = None
    CountRequest = ScrollRequest = UpdateResult = PointsSelector = None
    PointIdsList = FilterSelector = OptimizersConfigDiff = None
    CreateCollection = UpdateCollection = None

from ..core.config import QdrantConfig

logger = logging.getLogger(__name__)

@dataclass
class QdrantSearchResult:
    """Container for Qdrant search results."""
    id: Union[str, int]
    score: float
    payload: Dict[str, Any]
    vector: Optional[List[float]] = None

@dataclass
class QdrantStats:
    """Container for Qdrant collection statistics."""
    vectors_count: int
    indexed_vectors_count: int
    points_count: int
    segments_count: int
    collection_status: str
    optimizer_status: str
    disk_data_size: int
    ram_data_size: int

class QdrantClient:
    """
    Qdrant vector database client for Kenny AGI system.
    
    Provides comprehensive vector database operations including collection management,
    vector storage, similarity search, and advanced filtering capabilities.
    """
    
    def __init__(self, config: QdrantConfig):
        """
        Initialize Qdrant client.
        
        Args:
            config: Qdrant configuration object
        """
        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client not available. Install with: pip install qdrant-client")
            
        self.config = config
        self.client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize Qdrant client and connection."""
        try:
            # Configure client based on connection type
            if self.config.prefer_grpc:
                self.client = QdrantClientBase(
                    host=self.config.host,
                    grpc_port=self.config.grpc_port,
                    prefer_grpc=True,
                    api_key=self.config.api_key,
                    https=self.config.https,
                    timeout=self.config.timeout
                )
            else:
                self.client = QdrantClientBase(
                    host=self.config.host,
                    port=self.config.port,
                    api_key=self.config.api_key,
                    https=self.config.https,
                    timeout=self.config.timeout
                )
                
            # Test connection
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant at {self.config.host}:{self.config.port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {str(e)}")
            raise
            
    def create_collection(self,
                         collection_name: Optional[str] = None,
                         vector_size: Optional[int] = None,
                         distance: Optional[str] = None,
                         hnsw_config: Optional[Dict] = None,
                         optimizers_config: Optional[Dict] = None,
                         replication_factor: int = 1,
                         write_consistency_factor: int = 1) -> bool:
        """
        Create a new collection in Qdrant.
        
        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors
            distance: Distance metric (Cosine, Euclid, Dot)
            hnsw_config: HNSW index configuration
            optimizers_config: Optimizer configuration
            replication_factor: Number of replicas
            write_consistency_factor: Write consistency factor
            
        Returns:
            True if collection created successfully
        """
        collection_name = collection_name or self.config.collection_name
        vector_size = vector_size or self.config.vector_size
        distance_metric = distance or self.config.distance
        
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            for collection in collections.collections:
                if collection.name == collection_name:
                    logger.warning(f"Collection '{collection_name}' already exists")
                    return True
                    
            # Map distance string to enum
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclid": Distance.EUCLID,
                "Dot": Distance.DOT
            }
            distance_enum = distance_map.get(distance_metric, Distance.COSINE)
            
            # Default HNSW configuration
            default_hnsw = {
                "m": 16,
                "ef_construct": 200,
                "full_scan_threshold": 10000,
                "max_indexing_threads": 0,
                "on_disk": False
            }
            hnsw_config = hnsw_config or default_hnsw
            
            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance_enum,
                    hnsw_config=hnsw_config
                ),
                optimizers_config=optimizers_config,
                replication_factor=replication_factor,
                write_consistency_factor=write_consistency_factor
            )
            
            logger.info(f"Created Qdrant collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {str(e)}")
            return False
            
    def delete_collection(self, collection_name: Optional[str] = None) -> bool:
        """
        Delete a collection from Qdrant.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if collection deleted successfully
        """
        collection_name = collection_name or self.config.collection_name
        
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_exists = any(c.name == collection_name for c in collections.collections)
            
            if not collection_exists:
                logger.warning(f"Collection '{collection_name}' does not exist")
                return True
                
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted Qdrant collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {str(e)}")
            return False
            
    def upsert_points(self,
                     collection_name: Optional[str] = None,
                     points: List[Tuple[Union[str, int], List[float], Dict[str, Any]]] = None,
                     batch_size: int = 100,
                     wait: bool = True) -> bool:
        """
        Upsert points to a collection.
        
        Args:
            collection_name: Target collection name
            points: List of (id, vector, payload) tuples
            batch_size: Batch size for upsert operations
            wait: Wait for operation to complete
            
        Returns:
            True if upsert successful
        """
        collection_name = collection_name or self.config.collection_name
        
        if not points:
            logger.warning("No points provided for upsert")
            return False
            
        try:
            # Process in batches
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                
                # Convert to PointStruct objects
                point_structs = []
                for point_id, vector, payload in batch:
                    point_struct = PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload or {}
                    )
                    point_structs.append(point_struct)
                    
                # Upsert batch
                result = self.client.upsert(
                    collection_name=collection_name,
                    points=point_structs,
                    wait=wait
                )
                
                logger.debug(f"Upserted batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1}")
                
            logger.info(f"Upserted {len(points)} points to collection '{collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert points: {str(e)}")
            return False
            
    def upsert_single(self,
                     collection_name: Optional[str] = None,
                     point_id: Union[str, int] = None,
                     vector: List[float] = None,
                     payload: Optional[Dict[str, Any]] = None) -> bool:
        """
        Upsert a single point.
        
        Args:
            collection_name: Target collection name
            point_id: Point ID
            vector: Vector values
            payload: Point payload
            
        Returns:
            True if upsert successful
        """
        if point_id is None:
            point_id = str(uuid.uuid4())
            
        return self.upsert_points(
            collection_name=collection_name,
            points=[(point_id, vector, payload or {})]
        )
        
    def search_points(self,
                     collection_name: Optional[str] = None,
                     query_vector: List[float] = None,
                     query_filter: Optional[Dict[str, Any]] = None,
                     limit: int = 10,
                     offset: int = 0,
                     with_payload: bool = True,
                     with_vectors: bool = False,
                     score_threshold: Optional[float] = None) -> List[QdrantSearchResult]:
        """
        Search for similar points in a collection.
        
        Args:
            collection_name: Collection to search
            query_vector: Query vector
            query_filter: Payload filter
            limit: Maximum number of results
            offset: Offset for pagination
            with_payload: Include payload in results
            with_vectors: Include vectors in results
            score_threshold: Minimum similarity score
            
        Returns:
            List of search results
        """
        collection_name = collection_name or self.config.collection_name
        
        if not query_vector:
            logger.error("Query vector is required for search")
            return []
            
        try:
            # Build filter if provided
            search_filter = None
            if query_filter:
                search_filter = self._build_filter(query_filter)
                
            # Perform search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                with_vectors=with_vectors,
                score_threshold=score_threshold
            )
            
            # Convert to search results
            search_results = []
            for result in results:
                search_result = QdrantSearchResult(
                    id=result.id,
                    score=result.score,
                    payload=result.payload if with_payload else {},
                    vector=result.vector if with_vectors else None
                )
                search_results.append(search_result)
                
            logger.debug(f"Search returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search points: {str(e)}")
            return []
            
    def _build_filter(self, filter_dict: Dict[str, Any]) -> Filter:
        """
        Build Qdrant filter from dictionary.
        
        Args:
            filter_dict: Filter specification
            
        Returns:
            Qdrant Filter object
        """
        conditions = []
        
        for field, condition in filter_dict.items():
            if isinstance(condition, dict):
                # Range or complex condition
                if "gte" in condition or "lte" in condition:
                    range_condition = Range()
                    if "gte" in condition:
                        range_condition.gte = condition["gte"]
                    if "lte" in condition:
                        range_condition.lte = condition["lte"]
                    if "gt" in condition:
                        range_condition.gt = condition["gt"]
                    if "lt" in condition:
                        range_condition.lt = condition["lt"]
                        
                    field_condition = FieldCondition(
                        key=field,
                        range=range_condition
                    )
                    conditions.append(field_condition)
                    
            elif isinstance(condition, (list, tuple)):
                # Match any value in list
                for value in condition:
                    field_condition = FieldCondition(
                        key=field,
                        match=MatchValue(value=value)
                    )
                    conditions.append(field_condition)
            else:
                # Exact match
                field_condition = FieldCondition(
                    key=field,
                    match=MatchValue(value=condition)
                )
                conditions.append(field_condition)
                
        return Filter(must=conditions)
        
    def get_points(self,
                  collection_name: Optional[str] = None,
                  point_ids: List[Union[str, int]] = None,
                  with_payload: bool = True,
                  with_vectors: bool = True) -> List[QdrantSearchResult]:
        """
        Retrieve points by IDs.
        
        Args:
            collection_name: Collection name
            point_ids: List of point IDs
            with_payload: Include payload
            with_vectors: Include vectors
            
        Returns:
            List of points
        """
        collection_name = collection_name or self.config.collection_name
        
        if not point_ids:
            logger.error("Point IDs are required")
            return []
            
        try:
            results = self.client.retrieve(
                collection_name=collection_name,
                ids=point_ids,
                with_payload=with_payload,
                with_vectors=with_vectors
            )
            
            # Convert to search results
            search_results = []
            for result in results:
                search_result = QdrantSearchResult(
                    id=result.id,
                    score=1.0,  # Perfect match for ID retrieval
                    payload=result.payload if with_payload else {},
                    vector=result.vector if with_vectors else None
                )
                search_results.append(search_result)
                
            logger.debug(f"Retrieved {len(search_results)} points by ID")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve points: {str(e)}")
            return []
            
    def delete_points(self,
                     collection_name: Optional[str] = None,
                     point_ids: Optional[List[Union[str, int]]] = None,
                     points_filter: Optional[Dict[str, Any]] = None,
                     wait: bool = True) -> bool:
        """
        Delete points from a collection.
        
        Args:
            collection_name: Collection name
            point_ids: List of point IDs to delete
            points_filter: Filter for bulk deletion
            wait: Wait for operation to complete
            
        Returns:
            True if deletion successful
        """
        collection_name = collection_name or self.config.collection_name
        
        try:
            if point_ids:
                # Delete specific points
                result = self.client.delete(
                    collection_name=collection_name,
                    points_selector=PointIdsList(points=point_ids),
                    wait=wait
                )
                logger.info(f"Deleted {len(point_ids)} points from collection '{collection_name}'")
            elif points_filter:
                # Delete with filter
                search_filter = self._build_filter(points_filter)
                result = self.client.delete(
                    collection_name=collection_name,
                    points_selector=FilterSelector(filter=search_filter),
                    wait=wait
                )
                logger.info(f"Deleted points matching filter from collection '{collection_name}'")
            else:
                logger.warning("No deletion criteria specified")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete points: {str(e)}")
            return False
            
    def update_payload(self,
                      collection_name: Optional[str] = None,
                      point_ids: List[Union[str, int]] = None,
                      payload: Dict[str, Any] = None,
                      replace: bool = False,
                      wait: bool = True) -> bool:
        """
        Update payload for points.
        
        Args:
            collection_name: Collection name
            point_ids: List of point IDs
            payload: New payload data
            replace: Replace entire payload vs merge
            wait: Wait for operation to complete
            
        Returns:
            True if update successful
        """
        collection_name = collection_name or self.config.collection_name
        
        if not point_ids or not payload:
            logger.error("Point IDs and payload are required for update")
            return False
            
        try:
            if replace:
                result = self.client.overwrite_payload(
                    collection_name=collection_name,
                    points=point_ids,
                    payload=payload,
                    wait=wait
                )
            else:
                result = self.client.set_payload(
                    collection_name=collection_name,
                    points=point_ids,
                    payload=payload,
                    wait=wait
                )
                
            logger.debug(f"Updated payload for {len(point_ids)} points")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update payload: {str(e)}")
            return False
            
    def scroll_points(self,
                     collection_name: Optional[str] = None,
                     scroll_filter: Optional[Dict[str, Any]] = None,
                     limit: int = 10,
                     offset: Optional[Union[str, int]] = None,
                     with_payload: bool = True,
                     with_vectors: bool = False) -> Tuple[List[QdrantSearchResult], Optional[Union[str, int]]]:
        """
        Scroll through points in a collection.
        
        Args:
            collection_name: Collection name
            scroll_filter: Filter for scrolling
            limit: Number of points per scroll
            offset: Pagination offset
            with_payload: Include payload
            with_vectors: Include vectors
            
        Returns:
            Tuple of (points, next_offset)
        """
        collection_name = collection_name or self.config.collection_name
        
        try:
            # Build filter if provided
            search_filter = None
            if scroll_filter:
                search_filter = self._build_filter(scroll_filter)
                
            result = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=search_filter,
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                with_vectors=with_vectors
            )
            
            # Convert to search results
            points = []
            for point in result[0]:
                search_result = QdrantSearchResult(
                    id=point.id,
                    score=1.0,  # No scoring in scroll
                    payload=point.payload if with_payload else {},
                    vector=point.vector if with_vectors else None
                )
                points.append(search_result)
                
            next_offset = result[1]
            
            logger.debug(f"Scrolled {len(points)} points, next offset: {next_offset}")
            return points, next_offset
            
        except Exception as e:
            logger.error(f"Failed to scroll points: {str(e)}")
            return [], None
            
    def count_points(self,
                    collection_name: Optional[str] = None,
                    count_filter: Optional[Dict[str, Any]] = None,
                    exact: bool = False) -> int:
        """
        Count points in a collection.
        
        Args:
            collection_name: Collection name
            count_filter: Filter for counting
            exact: Whether to return exact count
            
        Returns:
            Number of points
        """
        collection_name = collection_name or self.config.collection_name
        
        try:
            # Build filter if provided
            search_filter = None
            if count_filter:
                search_filter = self._build_filter(count_filter)
                
            result = self.client.count(
                collection_name=collection_name,
                count_filter=search_filter,
                exact=exact
            )
            
            return result.count
            
        except Exception as e:
            logger.error(f"Failed to count points: {str(e)}")
            return 0
            
    def get_collection_info(self, collection_name: Optional[str] = None) -> Optional[QdrantStats]:
        """
        Get collection information and statistics.
        
        Args:
            collection_name: Collection name
            
        Returns:
            Collection statistics
        """
        collection_name = collection_name or self.config.collection_name
        
        try:
            info = self.client.get_collection(collection_name)
            
            return QdrantStats(
                vectors_count=info.vectors_count or 0,
                indexed_vectors_count=info.indexed_vectors_count or 0,
                points_count=info.points_count or 0,
                segments_count=info.segments_count or 0,
                collection_status=str(info.status),
                optimizer_status=str(info.optimizer_status),
                disk_data_size=getattr(info, 'disk_data_size', 0),
                ram_data_size=getattr(info, 'ram_data_size', 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to get collection info: {str(e)}")
            return None
            
    def list_collections(self) -> List[str]:
        """
        List all collections.
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.get_collections()
            return [c.name for c in collections.collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {str(e)}")
            return []
            
    def create_index(self,
                    collection_name: Optional[str] = None,
                    field_name: str = None,
                    field_type: str = "keyword",
                    wait: bool = True) -> bool:
        """
        Create payload index for faster filtering.
        
        Args:
            collection_name: Collection name
            field_name: Field to index
            field_type: Type of index (keyword, integer, float, bool)
            wait: Wait for operation to complete
            
        Returns:
            True if index created successfully
        """
        collection_name = collection_name or self.config.collection_name
        
        if not field_name:
            logger.error("Field name is required for creating index")
            return False
            
        try:
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_type,
                wait=wait
            )
            
            logger.info(f"Created index on field '{field_name}' in collection '{collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index: {str(e)}")
            return False
            
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Qdrant connection.
        
        Returns:
            Health status information
        """
        try:
            collections = self.list_collections()
            
            # Check if default collection exists and get its stats
            collection_stats = None
            if self.config.collection_name in collections:
                collection_stats = self.get_collection_info()
                
            return {
                "status": "healthy",
                "connected": True,
                "available_collections": collections,
                "collection_count": len(collections),
                "default_collection": self.config.collection_name,
                "default_collection_stats": {
                    "points_count": collection_stats.points_count if collection_stats else 0,
                    "vectors_count": collection_stats.vectors_count if collection_stats else 0,
                    "status": collection_stats.collection_status if collection_stats else "not_found"
                } if collection_stats else None
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "connected": False
            }