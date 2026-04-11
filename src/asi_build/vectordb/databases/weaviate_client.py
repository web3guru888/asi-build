"""
Weaviate vector database client for Kenny Vector Database System

This module provides comprehensive integration with Weaviate, including:
- Schema management and class creation
- Vector operations with automatic vectorization
- GraphQL queries and semantic search
- Hybrid search combining vector and keyword search
- Multi-tenant and cross-reference support
"""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import weaviate
    from weaviate.classes.config import Configure, DataType, Property
    from weaviate.classes.query import MetadataQuery, Move

    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False

from ..core.config import WeaviateConfig

logger = logging.getLogger(__name__)


@dataclass
class WeaviateSearchResult:
    """Container for Weaviate search results."""

    id: str
    score: float
    metadata: Dict[str, Any]
    properties: Dict[str, Any]
    vector: Optional[List[float]] = None
    explanation: Optional[Dict] = None


@dataclass
class WeaviateStats:
    """Container for Weaviate class statistics."""

    object_count: int
    class_name: str
    properties: List[str]
    vectorizer: str
    vector_index_type: str


class WeaviateClient:
    """
    Weaviate vector database client for Kenny AGI system.

    Provides comprehensive vector database operations including schema management,
    vectorization, semantic search, and hybrid search capabilities.
    """

    def __init__(self, config: WeaviateConfig):
        """
        Initialize Weaviate client.

        Args:
            config: Weaviate configuration object
        """
        if not WEAVIATE_AVAILABLE:
            raise ImportError(
                "weaviate-client not available. Install with: pip install weaviate-client"
            )

        self.config = config
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Weaviate client and connection."""
        try:
            # Build connection URL
            url = f"{self.config.scheme}://{self.config.host}:{self.config.port}"

            # Configure authentication if API key provided
            if self.config.api_key:
                auth_config = weaviate.AuthApiKey(api_key=self.config.api_key)
                self.client = weaviate.Client(
                    url=url,
                    auth_client_secret=auth_config,
                    timeout_config=(self.config.timeout, self.config.timeout),
                )
            else:
                self.client = weaviate.Client(
                    url=url, timeout_config=(self.config.timeout, self.config.timeout)
                )

            # Test connection
            if self.client.is_ready():
                logger.info(f"Connected to Weaviate at {url}")
            else:
                raise ConnectionError("Weaviate is not ready")

        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {str(e)}")
            raise

    def create_schema_class(
        self,
        class_name: str,
        properties: List[Dict[str, Any]],
        vectorizer: str = "text2vec-transformers",
        vector_index_type: str = "hnsw",
        distance_metric: str = "cosine",
    ) -> bool:
        """
        Create a new schema class in Weaviate.

        Args:
            class_name: Name of the class
            properties: List of property definitions
            vectorizer: Vectorization module
            vector_index_type: Vector index type
            distance_metric: Distance metric for vectors

        Returns:
            True if class created successfully
        """
        try:
            # Check if class already exists
            if self.client.schema.exists(class_name):
                logger.warning(f"Class '{class_name}' already exists")
                return True

            # Define class schema
            class_schema = {
                "class": class_name,
                "description": f"Class for {class_name} objects in Kenny Vector DB",
                "vectorizer": vectorizer,
                "vectorIndexType": vector_index_type,
                "vectorIndexConfig": {
                    "distance": distance_metric,
                    "efConstruction": 128,
                    "maxConnections": 64,
                },
                "properties": properties,
            }

            # Create class
            self.client.schema.create_class(class_schema)
            logger.info(f"Created Weaviate class: {class_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create class '{class_name}': {str(e)}")
            return False

    def delete_schema_class(self, class_name: str) -> bool:
        """
        Delete a schema class from Weaviate.

        Args:
            class_name: Name of the class to delete

        Returns:
            True if class deleted successfully
        """
        try:
            if not self.client.schema.exists(class_name):
                logger.warning(f"Class '{class_name}' does not exist")
                return True

            self.client.schema.delete_class(class_name)
            logger.info(f"Deleted Weaviate class: {class_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete class '{class_name}': {str(e)}")
            return False

    def create_document_class(self, class_name: str = "Document") -> bool:
        """
        Create a standard document class with common properties.

        Args:
            class_name: Name of the document class

        Returns:
            True if class created successfully
        """
        properties = [
            {
                "name": "content",
                "dataType": ["text"],
                "description": "The main content of the document",
            },
            {"name": "title", "dataType": ["string"], "description": "Title of the document"},
            {"name": "source", "dataType": ["string"], "description": "Source of the document"},
            {"name": "timestamp", "dataType": ["date"], "description": "Creation timestamp"},
            {"name": "category", "dataType": ["string"], "description": "Document category"},
            {"name": "tags", "dataType": ["string[]"], "description": "Document tags"},
            {"name": "metadata", "dataType": ["object"], "description": "Additional metadata"},
        ]

        return self.create_schema_class(class_name, properties)

    def insert_objects(
        self,
        class_name: str,
        objects: List[Dict[str, Any]],
        batch_size: int = 100,
        vector_field: Optional[str] = None,
    ) -> bool:
        """
        Insert objects into a Weaviate class.

        Args:
            class_name: Target class name
            objects: List of objects to insert
            batch_size: Batch size for insertion
            vector_field: Field containing custom vectors

        Returns:
            True if insertion successful
        """
        try:
            with self.client.batch(batch_size=batch_size, dynamic=True) as batch:
                for obj in objects:
                    # Generate UUID if not provided
                    obj_id = obj.get("id", str(uuid.uuid4()))

                    # Extract vector if provided
                    vector = None
                    if vector_field and vector_field in obj:
                        vector = obj.pop(vector_field)

                    # Add object to batch
                    batch.add_data_object(
                        data_object=obj, class_name=class_name, uuid=obj_id, vector=vector
                    )

            logger.info(f"Inserted {len(objects)} objects into class '{class_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to insert objects: {str(e)}")
            return False

    def insert_single(
        self,
        class_name: str,
        obj: Dict[str, Any],
        obj_id: Optional[str] = None,
        vector: Optional[List[float]] = None,
    ) -> Optional[str]:
        """
        Insert a single object.

        Args:
            class_name: Target class name
            obj: Object to insert
            obj_id: Object ID (generated if not provided)
            vector: Custom vector

        Returns:
            Object ID if successful
        """
        try:
            obj_id = obj_id or str(uuid.uuid4())

            result = self.client.data_object.create(
                data_object=obj, class_name=class_name, uuid=obj_id, vector=vector
            )

            logger.debug(f"Inserted object with ID: {obj_id}")
            return obj_id

        except Exception as e:
            logger.error(f"Failed to insert single object: {str(e)}")
            return None

    def semantic_search(
        self,
        class_name: str,
        query: str,
        top_k: int = 10,
        where_filter: Optional[Dict] = None,
        properties: Optional[List[str]] = None,
        with_vector: bool = False,
    ) -> List[WeaviateSearchResult]:
        """
        Perform semantic search using vector similarity.

        Args:
            class_name: Class to search
            query: Search query
            top_k: Number of results
            where_filter: Metadata filter
            properties: Properties to return
            with_vector: Include vectors in results

        Returns:
            List of search results
        """
        try:
            # Build GraphQL query
            query_builder = self.client.query.get(class_name, properties or ["*"])

            # Add semantic search
            query_builder = query_builder.with_near_text({"concepts": [query]}).with_limit(top_k)

            # Add filters
            if where_filter:
                query_builder = query_builder.with_where(where_filter)

            # Add additional metadata
            additional = ["certainty", "id"]
            if with_vector:
                additional.append("vector")

            query_builder = query_builder.with_additional(additional)

            # Execute query
            result = query_builder.do()

            # Parse results
            search_results = []
            if "data" in result and "Get" in result["data"] and class_name in result["data"]["Get"]:
                objects = result["data"]["Get"][class_name]

                for obj in objects:
                    additional_data = obj.get("_additional", {})

                    search_result = WeaviateSearchResult(
                        id=additional_data.get("id", ""),
                        score=additional_data.get("certainty", 0.0),
                        metadata=additional_data,
                        properties=obj,
                        vector=additional_data.get("vector") if with_vector else None,
                    )
                    search_results.append(search_result)

            logger.debug(f"Semantic search returned {len(search_results)} results")
            return search_results

        except Exception as e:
            logger.error(f"Failed to perform semantic search: {str(e)}")
            return []

    def hybrid_search(
        self,
        class_name: str,
        query: str,
        alpha: float = 0.5,
        top_k: int = 10,
        where_filter: Optional[Dict] = None,
        properties: Optional[List[str]] = None,
    ) -> List[WeaviateSearchResult]:
        """
        Perform hybrid search combining vector and keyword search.

        Args:
            class_name: Class to search
            query: Search query
            alpha: Balance between vector (1.0) and keyword (0.0) search
            top_k: Number of results
            where_filter: Metadata filter
            properties: Properties to return

        Returns:
            List of search results
        """
        try:
            # Build hybrid query
            query_builder = self.client.query.get(class_name, properties or ["*"])

            # Add hybrid search
            query_builder = query_builder.with_hybrid(query=query, alpha=alpha).with_limit(top_k)

            # Add filters
            if where_filter:
                query_builder = query_builder.with_where(where_filter)

            # Add metadata
            query_builder = query_builder.with_additional(["score", "id", "explainScore"])

            # Execute query
            result = query_builder.do()

            # Parse results
            search_results = []
            if "data" in result and "Get" in result["data"] and class_name in result["data"]["Get"]:
                objects = result["data"]["Get"][class_name]

                for obj in objects:
                    additional_data = obj.get("_additional", {})

                    search_result = WeaviateSearchResult(
                        id=additional_data.get("id", ""),
                        score=additional_data.get("score", 0.0),
                        metadata=additional_data,
                        properties=obj,
                        explanation=additional_data.get("explainScore"),
                    )
                    search_results.append(search_result)

            logger.debug(f"Hybrid search returned {len(search_results)} results")
            return search_results

        except Exception as e:
            logger.error(f"Failed to perform hybrid search: {str(e)}")
            return []

    def vector_search(
        self,
        class_name: str,
        vector: List[float],
        top_k: int = 10,
        where_filter: Optional[Dict] = None,
        properties: Optional[List[str]] = None,
    ) -> List[WeaviateSearchResult]:
        """
        Perform vector similarity search.

        Args:
            class_name: Class to search
            vector: Query vector
            top_k: Number of results
            where_filter: Metadata filter
            properties: Properties to return

        Returns:
            List of search results
        """
        try:
            # Build vector query
            query_builder = self.client.query.get(class_name, properties or ["*"])

            # Add vector search
            query_builder = query_builder.with_near_vector({"vector": vector}).with_limit(top_k)

            # Add filters
            if where_filter:
                query_builder = query_builder.with_where(where_filter)

            # Add metadata
            query_builder = query_builder.with_additional(["certainty", "id"])

            # Execute query
            result = query_builder.do()

            # Parse results
            search_results = []
            if "data" in result and "Get" in result["data"] and class_name in result["data"]["Get"]:
                objects = result["data"]["Get"][class_name]

                for obj in objects:
                    additional_data = obj.get("_additional", {})

                    search_result = WeaviateSearchResult(
                        id=additional_data.get("id", ""),
                        score=additional_data.get("certainty", 0.0),
                        metadata=additional_data,
                        properties=obj,
                    )
                    search_results.append(search_result)

            logger.debug(f"Vector search returned {len(search_results)} results")
            return search_results

        except Exception as e:
            logger.error(f"Failed to perform vector search: {str(e)}")
            return []

    def get_object_by_id(
        self,
        obj_id: str,
        class_name: Optional[str] = None,
        properties: Optional[List[str]] = None,
        with_vector: bool = False,
    ) -> Optional[WeaviateSearchResult]:
        """
        Get object by ID.

        Args:
            obj_id: Object ID
            class_name: Class name (optional)
            properties: Properties to return
            with_vector: Include vector

        Returns:
            Search result if found
        """
        try:
            additional = ["id"]
            if with_vector:
                additional.append("vector")

            obj = self.client.data_object.get(
                uuid=obj_id, class_name=class_name, with_vector=with_vector
            )

            if obj:
                additional_data = obj.get("additional", {})

                return WeaviateSearchResult(
                    id=obj.get("id", obj_id),
                    score=1.0,  # Perfect match for ID
                    metadata=additional_data,
                    properties=obj.get("properties", {}),
                    vector=additional_data.get("vector") if with_vector else None,
                )

            return None

        except Exception as e:
            logger.error(f"Failed to get object by ID: {str(e)}")
            return None

    def update_object(
        self, obj_id: str, class_name: str, properties: Dict[str, Any], merge: bool = True
    ) -> bool:
        """
        Update an object.

        Args:
            obj_id: Object ID
            class_name: Class name
            properties: Properties to update
            merge: Whether to merge with existing properties

        Returns:
            True if update successful
        """
        try:
            if merge:
                self.client.data_object.update(
                    uuid=obj_id, class_name=class_name, data_object=properties
                )
            else:
                self.client.data_object.replace(
                    uuid=obj_id, class_name=class_name, data_object=properties
                )

            logger.debug(f"Updated object '{obj_id}' in class '{class_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to update object: {str(e)}")
            return False

    def delete_objects(
        self,
        class_name: str,
        where_filter: Optional[Dict] = None,
        obj_ids: Optional[List[str]] = None,
    ) -> bool:
        """
        Delete objects from a class.

        Args:
            class_name: Class name
            where_filter: Filter for bulk deletion
            obj_ids: List of object IDs to delete

        Returns:
            True if deletion successful
        """
        try:
            if obj_ids:
                # Delete specific objects
                for obj_id in obj_ids:
                    self.client.data_object.delete(uuid=obj_id, class_name=class_name)
                logger.info(f"Deleted {len(obj_ids)} objects from class '{class_name}'")
            elif where_filter:
                # Bulk delete with filter
                result = self.client.batch.delete_objects(class_name=class_name, where=where_filter)
                logger.info(f"Bulk deleted objects from class '{class_name}'")
            else:
                logger.warning("No deletion criteria specified")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to delete objects: {str(e)}")
            return False

    def get_class_stats(self, class_name: str) -> Optional[WeaviateStats]:
        """
        Get statistics for a class.

        Args:
            class_name: Class name

        Returns:
            Class statistics
        """
        try:
            # Get object count
            result = self.client.query.aggregate(class_name).with_meta_count().do()

            object_count = 0
            if "data" in result and "Aggregate" in result["data"]:
                agg_data = result["data"]["Aggregate"][class_name]
                if agg_data and len(agg_data) > 0:
                    object_count = agg_data[0].get("meta", {}).get("count", 0)

            # Get schema info
            schema = self.client.schema.get(class_name)
            properties = [prop["name"] for prop in schema.get("properties", [])]
            vectorizer = schema.get("vectorizer", "")
            vector_index_type = schema.get("vectorIndexType", "")

            return WeaviateStats(
                object_count=object_count,
                class_name=class_name,
                properties=properties,
                vectorizer=vectorizer,
                vector_index_type=vector_index_type,
            )

        except Exception as e:
            logger.error(f"Failed to get class stats: {str(e)}")
            return None

    def list_classes(self) -> List[str]:
        """
        List all schema classes.

        Returns:
            List of class names
        """
        try:
            schema = self.client.schema.get()
            classes = [cls["class"] for cls in schema.get("classes", [])]
            return classes
        except Exception as e:
            logger.error(f"Failed to list classes: {str(e)}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Weaviate connection.

        Returns:
            Health status information
        """
        try:
            is_ready = self.client.is_ready()
            is_live = self.client.is_live()

            if is_ready and is_live:
                classes = self.list_classes()

                return {
                    "status": "healthy",
                    "ready": is_ready,
                    "live": is_live,
                    "available_classes": classes,
                    "class_count": len(classes),
                }
            else:
                return {"status": "unhealthy", "ready": is_ready, "live": is_live}

        except Exception as e:
            return {"status": "error", "error": str(e), "ready": False, "live": False}
