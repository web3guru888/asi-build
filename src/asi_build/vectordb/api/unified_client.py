"""
Unified Vector Database Client for Kenny Vector Database System

This module provides a unified interface to interact with multiple vector databases
(Pinecone, Weaviate, Qdrant) through a single API, with automatic load balancing,
failover, and intelligent routing.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from ..core.config import VectorDBConfig
from ..core.embeddings import EmbeddingPipeline
from ..core.search import SearchQuery, SearchResult, SemanticSearchEngine
from ..databases.pinecone_client import PineconeClient
from ..databases.qdrant_client import QdrantClient
from ..databases.weaviate_client import WeaviateClient

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """Supported database types."""

    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"


@dataclass
class DatabaseHealth:
    """Health status of a database."""

    database_type: str
    is_healthy: bool
    response_time: float
    error_message: Optional[str] = None
    last_check: float = 0.0


@dataclass
class InsertionResult:
    """Result of data insertion operation."""

    success: bool
    inserted_count: int
    failed_count: int
    database_results: Dict[str, bool]
    errors: List[str]
    duration: float


class UnifiedVectorDB:
    """
    Unified vector database client providing a single interface to multiple databases.

    Features:
    - Multi-database support (Pinecone, Weaviate, Qdrant)
    - Automatic failover and load balancing
    - Intelligent routing based on query type
    - Unified search across all databases
    - Health monitoring and diagnostics
    """

    def __init__(self, config: VectorDBConfig):
        """
        Initialize unified vector database client.

        Args:
            config: Vector database configuration
        """
        self.config = config

        # Initialize clients
        self._initialize_clients()

        # Initialize embedding pipeline
        self.embedding_pipeline = EmbeddingPipeline(config.embedding)

        # Initialize search engine
        self.search_engine = SemanticSearchEngine(
            embedding_pipeline=self.embedding_pipeline,
            config=config.search,
            pinecone_client=self.pinecone_client,
            weaviate_client=self.weaviate_client,
            qdrant_client=self.qdrant_client,
        )

        # Health monitoring
        self.database_health: Dict[str, DatabaseHealth] = {}
        self._last_health_check = 0.0
        self.health_check_interval = 60.0  # seconds

        # Statistics
        self.operation_stats = {
            "insertions": 0,
            "searches": 0,
            "updates": 0,
            "deletions": 0,
            "errors": 0,
        }

    def _initialize_clients(self):
        """Initialize database clients."""
        self.pinecone_client = None
        self.weaviate_client = None
        self.qdrant_client = None

        try:
            if self.config.pinecone.api_key:
                self.pinecone_client = PineconeClient(self.config.pinecone)
                logger.info("Initialized Pinecone client")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {str(e)}")

        try:
            self.weaviate_client = WeaviateClient(self.config.weaviate)
            logger.info("Initialized Weaviate client")
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {str(e)}")

        try:
            self.qdrant_client = QdrantClient(self.config.qdrant)
            logger.info("Initialized Qdrant client")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {str(e)}")

    def _check_database_health(self, force_check: bool = False) -> Dict[str, DatabaseHealth]:
        """Check health of all databases."""
        current_time = time.time()

        if (
            not force_check
            and (current_time - self._last_health_check) < self.health_check_interval
        ):
            return self.database_health

        # Check Pinecone health
        if self.pinecone_client:
            start_time = time.time()
            try:
                health_info = self.pinecone_client.health_check()
                response_time = time.time() - start_time

                self.database_health["pinecone"] = DatabaseHealth(
                    database_type="pinecone",
                    is_healthy=health_info.get("status") == "healthy",
                    response_time=response_time,
                    last_check=current_time,
                )
            except Exception as e:
                self.database_health["pinecone"] = DatabaseHealth(
                    database_type="pinecone",
                    is_healthy=False,
                    response_time=time.time() - start_time,
                    error_message=str(e),
                    last_check=current_time,
                )

        # Check Weaviate health
        if self.weaviate_client:
            start_time = time.time()
            try:
                health_info = self.weaviate_client.health_check()
                response_time = time.time() - start_time

                self.database_health["weaviate"] = DatabaseHealth(
                    database_type="weaviate",
                    is_healthy=health_info.get("status") == "healthy",
                    response_time=response_time,
                    last_check=current_time,
                )
            except Exception as e:
                self.database_health["weaviate"] = DatabaseHealth(
                    database_type="weaviate",
                    is_healthy=False,
                    response_time=time.time() - start_time,
                    error_message=str(e),
                    last_check=current_time,
                )

        # Check Qdrant health
        if self.qdrant_client:
            start_time = time.time()
            try:
                health_info = self.qdrant_client.health_check()
                response_time = time.time() - start_time

                self.database_health["qdrant"] = DatabaseHealth(
                    database_type="qdrant",
                    is_healthy=health_info.get("status") == "healthy",
                    response_time=response_time,
                    last_check=current_time,
                )
            except Exception as e:
                self.database_health["qdrant"] = DatabaseHealth(
                    database_type="qdrant",
                    is_healthy=False,
                    response_time=time.time() - start_time,
                    error_message=str(e),
                    last_check=current_time,
                )

        self._last_health_check = current_time
        return self.database_health

    def get_healthy_databases(self) -> List[str]:
        """Get list of healthy databases."""
        health_status = self._check_database_health()
        return [db for db, health in health_status.items() if health.is_healthy]

    def insert_documents(
        self,
        documents: List[Dict[str, Any]],
        database_preference: Optional[List[str]] = None,
        replicate_across_dbs: bool = True,
    ) -> InsertionResult:
        """
        Insert documents into vector database(s).

        Args:
            documents: List of documents with 'content' and optional metadata
            database_preference: Preferred databases in order
            replicate_across_dbs: Whether to replicate across multiple databases

        Returns:
            Insertion result with success/failure details
        """
        start_time = time.time()

        # Generate embeddings for all documents
        contents = [doc.get("content", "") for doc in documents]
        embeddings_result = self.embedding_pipeline.generate_embeddings(contents)

        # Prepare database operations
        database_results = {}
        errors = []
        successful_insertions = 0

        # Determine target databases
        healthy_databases = self.get_healthy_databases()

        if database_preference:
            target_databases = [db for db in database_preference if db in healthy_databases]
        else:
            target_databases = healthy_databases

        if not replicate_across_dbs and target_databases:
            # Use only the first healthy database
            target_databases = [target_databases[0]]

        # Insert into each target database
        for db_name in target_databases:
            try:
                if db_name == "pinecone" and self.pinecone_client:
                    result = self._insert_pinecone(documents, embeddings_result.embeddings)
                elif db_name == "weaviate" and self.weaviate_client:
                    result = self._insert_weaviate(documents, embeddings_result.embeddings)
                elif db_name == "qdrant" and self.qdrant_client:
                    result = self._insert_qdrant(documents, embeddings_result.embeddings)
                else:
                    result = False

                database_results[db_name] = result

                if result:
                    successful_insertions = len(documents)

            except Exception as e:
                error_msg = f"Failed to insert into {db_name}: {str(e)}"
                errors.append(error_msg)
                database_results[db_name] = False
                logger.error(error_msg)

        # Update statistics
        self.operation_stats["insertions"] += successful_insertions
        if errors:
            self.operation_stats["errors"] += len(errors)

        duration = time.time() - start_time

        return InsertionResult(
            success=any(database_results.values()),
            inserted_count=successful_insertions if any(database_results.values()) else 0,
            failed_count=len(documents) if not any(database_results.values()) else 0,
            database_results=database_results,
            errors=errors,
            duration=duration,
        )

    def _insert_pinecone(
        self, documents: List[Dict[str, Any]], embeddings: List[List[float]]
    ) -> bool:
        """Insert documents into Pinecone."""
        if not self.pinecone_client:
            return False

        # Prepare vectors for Pinecone
        vectors = []
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            doc_id = doc.get("id", self._generate_doc_id(doc["content"]))
            metadata = doc.copy()

            vectors.append((doc_id, embedding, metadata))

        return self.pinecone_client.upsert_vectors(vectors)

    def _insert_weaviate(
        self, documents: List[Dict[str, Any]], embeddings: List[List[float]]
    ) -> bool:
        """Insert documents into Weaviate."""
        if not self.weaviate_client:
            return False

        # Prepare objects for Weaviate
        objects = []
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            obj = doc.copy()
            obj["id"] = doc.get("id", self._generate_doc_id(doc["content"]))
            objects.append(obj)

        return self.weaviate_client.insert_objects("Document", objects, vector_field="vector")

    def _insert_qdrant(
        self, documents: List[Dict[str, Any]], embeddings: List[List[float]]
    ) -> bool:
        """Insert documents into Qdrant."""
        if not self.qdrant_client:
            return False

        # Prepare points for Qdrant
        points = []
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            doc_id = doc.get("id", self._generate_doc_id(doc["content"]))
            payload = doc.copy()

            points.append((doc_id, embedding, payload))

        return self.qdrant_client.upsert_points(points=points)

    def _generate_doc_id(self, content: str) -> str:
        """Generate a unique ID for document content."""
        content_bytes = content.encode("utf-8")
        hash_obj = hashlib.md5(content_bytes)
        return hash_obj.hexdigest()

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0,
        database_preference: Optional[List[str]] = None,
        include_vectors: bool = False,
    ) -> List[SearchResult]:
        """
        Perform unified search across vector databases.

        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Metadata filters
            score_threshold: Minimum similarity score
            database_preference: Preferred databases for search
            include_vectors: Include vector embeddings in results

        Returns:
            Unified search results
        """
        try:
            # Create search query
            search_query = SearchQuery(
                query=query,
                filters=filters or {},
                top_k=top_k,
                score_threshold=score_threshold,
                include_vectors=include_vectors,
            )

            # Apply database preference
            if database_preference:
                healthy_dbs = self.get_healthy_databases()
                preferred_dbs = [db for db in database_preference if db in healthy_dbs]

                # Set database weights
                weights = {}
                for i, db in enumerate(preferred_dbs):
                    # Higher weight for preferred databases
                    weights[db] = 1.0 - (i * 0.1)

                search_query.database_weights = weights

            # Execute search
            results = self.search_engine.search(search_query)

            # Update statistics
            self.operation_stats["searches"] += 1

            return results

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            self.operation_stats["errors"] += 1
            return []

    def semantic_search(
        self, query: str, top_k: int = 10, expand_query: bool = True, rerank: bool = True
    ) -> List[SearchResult]:
        """
        Perform advanced semantic search with query expansion and reranking.

        Args:
            query: Search query text
            top_k: Number of results to return
            expand_query: Enable query expansion
            rerank: Enable result reranking

        Returns:
            Semantic search results
        """
        search_query = SearchQuery(
            query=query, top_k=top_k, expand_query=expand_query, rerank=rerank
        )

        return self.search_engine.search(search_query)

    def hybrid_search(
        self, query: str, top_k: int = 10, vector_weight: float = 0.7, keyword_weight: float = 0.3
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining vector and keyword search.

        Args:
            query: Search query text
            top_k: Number of results to return
            vector_weight: Weight for vector similarity
            keyword_weight: Weight for keyword matching

        Returns:
            Hybrid search results
        """
        return self.search_engine.hybrid_search(
            query=query, top_k=top_k, vector_weight=vector_weight, keyword_weight=keyword_weight
        )

    def delete_documents(
        self, document_ids: List[str], database_preference: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Delete documents from vector databases.

        Args:
            document_ids: List of document IDs to delete
            database_preference: Preferred databases for deletion

        Returns:
            Dictionary of database deletion results
        """
        results = {}

        # Determine target databases
        healthy_databases = self.get_healthy_databases()

        if database_preference:
            target_databases = [db for db in database_preference if db in healthy_databases]
        else:
            target_databases = healthy_databases

        # Delete from each database
        for db_name in target_databases:
            try:
                if db_name == "pinecone" and self.pinecone_client:
                    result = self.pinecone_client.delete_vectors(vec_ids=document_ids)
                elif db_name == "weaviate" and self.weaviate_client:
                    result = self.weaviate_client.delete_objects("Document", obj_ids=document_ids)
                elif db_name == "qdrant" and self.qdrant_client:
                    result = self.qdrant_client.delete_points(point_ids=document_ids)
                else:
                    result = False

                results[db_name] = result

            except Exception as e:
                logger.error(f"Failed to delete from {db_name}: {str(e)}")
                results[db_name] = False
                self.operation_stats["errors"] += 1

        # Update statistics
        if any(results.values()):
            self.operation_stats["deletions"] += len(document_ids)

        return results

    def get_document(
        self,
        document_id: str,
        database_preference: Optional[List[str]] = None,
        include_vector: bool = False,
    ) -> Optional[SearchResult]:
        """
        Retrieve a specific document by ID.

        Args:
            document_id: Document ID to retrieve
            database_preference: Preferred databases for retrieval
            include_vector: Include vector embedding

        Returns:
            Search result if found
        """
        # Determine target databases
        healthy_databases = self.get_healthy_databases()

        if database_preference:
            target_databases = [db for db in database_preference if db in healthy_databases]
        else:
            target_databases = healthy_databases

        # Try each database until document is found
        for db_name in target_databases:
            try:
                if db_name == "pinecone" and self.pinecone_client:
                    results = self.pinecone_client.query_by_id(
                        vec_ids=[document_id], include_values=include_vector, include_metadata=True
                    )
                    if results:
                        result = results[0]
                        return SearchResult(
                            id=result.id,
                            score=result.score,
                            content=result.metadata.get("content", ""),
                            metadata=result.metadata,
                            source_db="pinecone",
                            vector=result.values if include_vector else None,
                        )

                elif db_name == "weaviate" and self.weaviate_client:
                    result = self.weaviate_client.get_object_by_id(
                        obj_id=document_id, with_vector=include_vector
                    )
                    if result:
                        return SearchResult(
                            id=result.id,
                            score=result.score,
                            content=result.properties.get("content", ""),
                            metadata=result.properties,
                            source_db="weaviate",
                            vector=result.vector if include_vector else None,
                        )

                elif db_name == "qdrant" and self.qdrant_client:
                    results = self.qdrant_client.get_points(
                        point_ids=[document_id], with_payload=True, with_vectors=include_vector
                    )
                    if results:
                        result = results[0]
                        return SearchResult(
                            id=str(result.id),
                            score=result.score,
                            content=result.payload.get("content", ""),
                            metadata=result.payload,
                            source_db="qdrant",
                            vector=result.vector if include_vector else None,
                        )

            except Exception as e:
                logger.error(f"Failed to retrieve from {db_name}: {str(e)}")
                continue

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        health_status = self._check_database_health()
        search_analytics = self.search_engine.get_search_analytics()

        return {
            "operation_stats": self.operation_stats.copy(),
            "database_health": {
                db: {
                    "is_healthy": health.is_healthy,
                    "response_time": health.response_time,
                    "last_check": health.last_check,
                    "error_message": health.error_message,
                }
                for db, health in health_status.items()
            },
            "search_analytics": search_analytics,
            "embedding_info": self.embedding_pipeline.get_model_info(),
            "cache_stats": self.embedding_pipeline.get_cache_stats(),
        }

    def initialize_databases(self) -> Dict[str, bool]:
        """Initialize all configured databases with default schemas/collections."""
        results = {}

        # Initialize Pinecone
        if self.pinecone_client:
            try:
                success = self.pinecone_client.create_index()
                if success:
                    success = self.pinecone_client.connect()
                results["pinecone"] = success
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone: {str(e)}")
                results["pinecone"] = False

        # Initialize Weaviate
        if self.weaviate_client:
            try:
                success = self.weaviate_client.create_document_class()
                results["weaviate"] = success
            except Exception as e:
                logger.error(f"Failed to initialize Weaviate: {str(e)}")
                results["weaviate"] = False

        # Initialize Qdrant
        if self.qdrant_client:
            try:
                success = self.qdrant_client.create_collection()
                results["qdrant"] = success
            except Exception as e:
                logger.error(f"Failed to initialize Qdrant: {str(e)}")
                results["qdrant"] = False

        return results

    def clear_all_data(self, confirm: bool = False) -> Dict[str, bool]:
        """
        Clear all data from databases.

        Args:
            confirm: Must be True to execute

        Returns:
            Dictionary of deletion results
        """
        if not confirm:
            raise ValueError("Must confirm data deletion with confirm=True")

        results = {}

        # Clear Pinecone
        if self.pinecone_client:
            try:
                success = self.pinecone_client.delete_vectors(delete_all=True)
                results["pinecone"] = success
            except Exception as e:
                logger.error(f"Failed to clear Pinecone: {str(e)}")
                results["pinecone"] = False

        # Clear Weaviate
        if self.weaviate_client:
            try:
                success = self.weaviate_client.delete_objects("Document", where_filter={})
                results["weaviate"] = success
            except Exception as e:
                logger.error(f"Failed to clear Weaviate: {str(e)}")
                results["weaviate"] = False

        # Clear Qdrant
        if self.qdrant_client:
            try:
                success = self.qdrant_client.delete_points(points_filter={})
                results["qdrant"] = success
            except Exception as e:
                logger.error(f"Failed to clear Qdrant: {str(e)}")
                results["qdrant"] = False

        return results
