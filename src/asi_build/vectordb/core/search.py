"""
Semantic search engine for Kenny Vector Database System

This module provides advanced semantic search capabilities including:
- Multi-database search coordination
- Query expansion and refinement
- Hybrid search combining vector and keyword search
- Result ranking and filtering
- Search analytics and optimization
"""

import logging
import time
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import numpy as np

from .embeddings import EmbeddingPipeline
from .utils import VectorUtils, TextUtils, timed_operation
from .config import SearchConfig
from ..databases.pinecone_client import PineconeClient, PineconeSearchResult
from ..databases.weaviate_client import WeaviateClient, WeaviateSearchResult  
from ..databases.qdrant_client import QdrantClient, QdrantSearchResult

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Unified search result across all databases."""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    source_db: str
    vector: Optional[List[float]] = None
    explanation: Optional[Dict[str, Any]] = None
    
@dataclass
class SearchQuery:
    """Search query with parameters."""
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    top_k: int = 10
    score_threshold: float = 0.0
    include_vectors: bool = False
    expand_query: bool = True
    rerank: bool = True
    database_weights: Dict[str, float] = field(default_factory=lambda: {"pinecone": 1.0, "weaviate": 1.0, "qdrant": 1.0})

@dataclass
class SearchStats:
    """Search operation statistics."""
    query: str
    total_results: int
    databases_searched: List[str]
    search_time: float
    embedding_time: float
    rerank_time: float
    top_score: float
    avg_score: float
    
class BaseSearchEngine(ABC):
    """Abstract base class for search engines."""
    
    @abstractmethod
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute search query."""
        pass

class QueryExpander:
    """Query expansion for improved search results."""
    
    def __init__(self):
        self.synonyms = self._load_synonyms()
        
    def _load_synonyms(self) -> Dict[str, List[str]]:
        """Load synonym dictionary."""
        # Basic synonym mapping - in production, use a comprehensive thesaurus
        return {
            "ai": ["artificial intelligence", "machine learning", "ml", "deep learning"],
            "database": ["db", "datastore", "repository", "storage"],
            "search": ["find", "query", "lookup", "retrieve"],
            "vector": ["embedding", "representation", "feature"],
            "similarity": ["resemblance", "likeness", "closeness"],
            "neural": ["network", "deep", "artificial"],
            "model": ["algorithm", "system", "method"],
            "data": ["information", "content", "records"],
            "analysis": ["analytics", "examination", "evaluation"],
            "performance": ["speed", "efficiency", "optimization"]
        }
        
    def expand_query(self, query: str, max_expansions: int = 3) -> List[str]:
        """
        Expand query with synonyms and related terms.
        
        Args:
            query: Original query
            max_expansions: Maximum number of expansions per term
            
        Returns:
            List of expanded queries
        """
        query_terms = query.lower().split()
        expanded_queries = [query]  # Include original query
        
        # Generate synonym-based expansions
        for term in query_terms:
            if term in self.synonyms:
                synonyms = self.synonyms[term][:max_expansions]
                for synonym in synonyms:
                    expanded_query = query.lower().replace(term, synonym)
                    if expanded_query != query.lower():
                        expanded_queries.append(expanded_query)
                        
        # Generate phrase-based expansions
        keywords = TextUtils.extract_keywords(query, top_k=5)
        for keyword in keywords:
            if keyword not in query.lower():
                expanded_queries.append(f"{query} {keyword}")
                
        # Remove duplicates and limit
        expanded_queries = list(dict.fromkeys(expanded_queries))
        return expanded_queries[:max_expansions + 1]

class ResultReranker:
    """Re-ranking system for search results."""
    
    def __init__(self):
        self.boost_factors = {
            "recency": 0.1,
            "popularity": 0.15,
            "relevance": 0.75
        }
        
    def rerank_results(self, 
                      results: List[SearchResult],
                      query: str,
                      rerank_top_k: int = 100) -> List[SearchResult]:
        """
        Re-rank search results using multiple factors.
        
        Args:
            results: Search results to rerank
            query: Original query
            rerank_top_k: Number of top results to rerank
            
        Returns:
            Reranked results
        """
        if len(results) <= 1:
            return results
            
        # Take top results for reranking
        candidates = results[:rerank_top_k]
        remaining = results[rerank_top_k:]
        
        # Calculate boost scores
        boosted_results = []
        for result in candidates:
            boost_score = self._calculate_boost_score(result, query)
            final_score = result.score * (1 + boost_score)
            
            boosted_result = SearchResult(
                id=result.id,
                score=final_score,
                content=result.content,
                metadata=result.metadata,
                source_db=result.source_db,
                vector=result.vector,
                explanation=result.explanation
            )
            boosted_results.append(boosted_result)
            
        # Sort by boosted scores
        boosted_results.sort(key=lambda x: x.score, reverse=True)
        
        return boosted_results + remaining
        
    def _calculate_boost_score(self, result: SearchResult, query: str) -> float:
        """Calculate boost score for a result."""
        boost = 0.0
        
        # Content length boost (moderate length preferred)
        content_len = len(result.content)
        if 100 <= content_len <= 1000:
            boost += 0.05
        elif content_len > 2000:
            boost -= 0.05
            
        # Keyword match boost
        query_terms = set(query.lower().split())
        content_terms = set(result.content.lower().split())
        match_ratio = len(query_terms.intersection(content_terms)) / len(query_terms)
        boost += match_ratio * 0.1
        
        # Metadata-based boosts
        metadata = result.metadata
        
        # Recency boost (if timestamp available)
        if 'timestamp' in metadata:
            try:
                timestamp = metadata['timestamp']
                if isinstance(timestamp, (int, float)):
                    current_time = time.time()
                    days_old = (current_time - timestamp) / (24 * 3600)
                    if days_old < 30:
                        boost += self.boost_factors["recency"] * (30 - days_old) / 30
            except:
                pass
                
        # Popularity boost (if view count available)
        if 'views' in metadata or 'popularity' in metadata:
            try:
                views = metadata.get('views', metadata.get('popularity', 0))
                if views > 100:
                    boost += self.boost_factors["popularity"] * min(views / 1000, 1.0)
            except:
                pass
                
        # Category/tag relevance boost
        if 'category' in metadata or 'tags' in metadata:
            category = metadata.get('category', '')
            tags = metadata.get('tags', [])
            
            if isinstance(tags, list):
                all_tags = [category] + tags
            else:
                all_tags = [category, str(tags)]
                
            for tag in all_tags:
                if any(term in str(tag).lower() for term in query.lower().split()):
                    boost += 0.05
                    
        return boost

class SemanticSearchEngine(BaseSearchEngine):
    """
    Advanced semantic search engine with multi-database support.
    
    Provides unified search across Pinecone, Weaviate, and Qdrant with
    intelligent query expansion, result reranking, and performance optimization.
    """
    
    def __init__(self, 
                 embedding_pipeline: EmbeddingPipeline,
                 config: SearchConfig,
                 pinecone_client: Optional[PineconeClient] = None,
                 weaviate_client: Optional[WeaviateClient] = None,
                 qdrant_client: Optional[QdrantClient] = None):
        """
        Initialize semantic search engine.
        
        Args:
            embedding_pipeline: Embedding generation pipeline
            config: Search configuration
            pinecone_client: Pinecone client (optional)
            weaviate_client: Weaviate client (optional)
            qdrant_client: Qdrant client (optional)
        """
        self.embedding_pipeline = embedding_pipeline
        self.config = config
        
        # Database clients
        self.pinecone_client = pinecone_client
        self.weaviate_client = weaviate_client
        self.qdrant_client = qdrant_client
        
        # Search components
        self.query_expander = QueryExpander()
        self.reranker = ResultReranker()
        
        # Statistics
        self.search_stats: List[SearchStats] = []
        
    @timed_operation("semantic_search")
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Execute semantic search across configured databases.
        
        Args:
            query: Search query with parameters
            
        Returns:
            Unified search results
        """
        start_time = time.time()
        
        # Generate embeddings for query
        embedding_start = time.time()
        if query.expand_query:
            expanded_queries = self.query_expander.expand_query(query.query)
            embeddings_result = self.embedding_pipeline.generate_embeddings(expanded_queries)
            query_embeddings = embeddings_result.embeddings
        else:
            embedding_result = self.embedding_pipeline.generate_embeddings([query.query])
            query_embeddings = embedding_result.embeddings
            
        embedding_time = time.time() - embedding_start
        
        # Search across databases
        all_results = []
        databases_searched = []
        
        if self.pinecone_client and query.database_weights.get("pinecone", 0) > 0:
            pinecone_results = self._search_pinecone(query, query_embeddings[0])
            weighted_results = self._apply_database_weight(pinecone_results, query.database_weights.get("pinecone", 1.0))
            all_results.extend(weighted_results)
            databases_searched.append("pinecone")
            
        if self.weaviate_client and query.database_weights.get("weaviate", 0) > 0:
            weaviate_results = self._search_weaviate(query, query_embeddings[0])
            weighted_results = self._apply_database_weight(weaviate_results, query.database_weights.get("weaviate", 1.0))
            all_results.extend(weighted_results)
            databases_searched.append("weaviate")
            
        if self.qdrant_client and query.database_weights.get("qdrant", 0) > 0:
            qdrant_results = self._search_qdrant(query, query_embeddings[0])
            weighted_results = self._apply_database_weight(qdrant_results, query.database_weights.get("qdrant", 1.0))
            all_results.extend(weighted_results)
            databases_searched.append("qdrant")
            
        # Remove duplicates based on content similarity
        all_results = self._deduplicate_results(all_results)
        
        # Filter by score threshold
        if query.score_threshold > 0:
            all_results = [r for r in all_results if r.score >= query.score_threshold]
            
        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Rerank if enabled
        rerank_time = 0.0
        if query.rerank and len(all_results) > 1:
            rerank_start = time.time()
            all_results = self.reranker.rerank_results(
                all_results, 
                query.query,
                self.config.rerank_top_k
            )
            rerank_time = time.time() - rerank_start
            
        # Limit results
        final_results = all_results[:query.top_k]
        
        # Record statistics
        search_time = time.time() - start_time
        stats = SearchStats(
            query=query.query,
            total_results=len(final_results),
            databases_searched=databases_searched,
            search_time=search_time,
            embedding_time=embedding_time,
            rerank_time=rerank_time,
            top_score=final_results[0].score if final_results else 0.0,
            avg_score=np.mean([r.score for r in final_results]) if final_results else 0.0
        )
        self.search_stats.append(stats)
        
        logger.info(f"Search completed: {len(final_results)} results in {search_time:.3f}s")
        return final_results
        
    def _search_pinecone(self, query: SearchQuery, query_embedding: List[float]) -> List[SearchResult]:
        """Search Pinecone database."""
        try:
            results = self.pinecone_client.query_vectors(
                query_vector=query_embedding,
                top_k=query.top_k * 2,  # Get extra for reranking
                filter_dict=query.filters,
                include_values=query.include_vectors,
                include_metadata=True
            )
            
            search_results = []
            for result in results:
                search_result = SearchResult(
                    id=result.id,
                    score=result.score,
                    content=result.metadata.get('content', ''),
                    metadata=result.metadata,
                    source_db="pinecone",
                    vector=result.values if query.include_vectors else None
                )
                search_results.append(search_result)
                
            return search_results
            
        except Exception as e:
            logger.error(f"Pinecone search failed: {str(e)}")
            return []
            
    def _search_weaviate(self, query: SearchQuery, query_embedding: List[float]) -> List[SearchResult]:
        """Search Weaviate database."""
        try:
            if self.config.enable_hybrid_search:
                results = self.weaviate_client.hybrid_search(
                    class_name="Document",  # Default class
                    query=query.query,
                    alpha=self.config.alpha,
                    top_k=query.top_k * 2,
                    where_filter=query.filters if query.filters else None
                )
            else:
                results = self.weaviate_client.vector_search(
                    class_name="Document",
                    vector=query_embedding,
                    top_k=query.top_k * 2,
                    where_filter=query.filters if query.filters else None
                )
                
            search_results = []
            for result in results:
                search_result = SearchResult(
                    id=result.id,
                    score=result.score,
                    content=result.properties.get('content', ''),
                    metadata=result.properties,
                    source_db="weaviate",
                    vector=result.vector if query.include_vectors else None,
                    explanation=result.explanation
                )
                search_results.append(search_result)
                
            return search_results
            
        except Exception as e:
            logger.error(f"Weaviate search failed: {str(e)}")
            return []
            
    def _search_qdrant(self, query: SearchQuery, query_embedding: List[float]) -> List[SearchResult]:
        """Search Qdrant database."""
        try:
            results = self.qdrant_client.search_points(
                query_vector=query_embedding,
                query_filter=query.filters if query.filters else None,
                limit=query.top_k * 2,
                with_payload=True,
                with_vectors=query.include_vectors,
                score_threshold=query.score_threshold
            )
            
            search_results = []
            for result in results:
                search_result = SearchResult(
                    id=str(result.id),
                    score=result.score,
                    content=result.payload.get('content', ''),
                    metadata=result.payload,
                    source_db="qdrant",
                    vector=result.vector if query.include_vectors else None
                )
                search_results.append(search_result)
                
            return search_results
            
        except Exception as e:
            logger.error(f"Qdrant search failed: {str(e)}")
            return []
            
    def _apply_database_weight(self, results: List[SearchResult], weight: float) -> List[SearchResult]:
        """Apply database weight to search scores."""
        if weight == 1.0:
            return results
            
        weighted_results = []
        for result in results:
            weighted_result = SearchResult(
                id=result.id,
                score=result.score * weight,
                content=result.content,
                metadata=result.metadata,
                source_db=result.source_db,
                vector=result.vector,
                explanation=result.explanation
            )
            weighted_results.append(weighted_result)
            
        return weighted_results
        
    def _deduplicate_results(self, results: List[SearchResult], similarity_threshold: float = 0.9) -> List[SearchResult]:
        """Remove duplicate results based on content similarity."""
        if len(results) <= 1:
            return results
            
        deduplicated = []
        seen_content = []
        
        for result in results:
            is_duplicate = False
            
            # Check content similarity with existing results
            for existing_content in seen_content:
                if self._content_similarity(result.content, existing_content) > similarity_threshold:
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                deduplicated.append(result)
                seen_content.append(result.content)
                
        return deduplicated
        
    def _content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        if not content1 or not content2:
            return 0.0
            
        # Simple word overlap similarity
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
        
    def hybrid_search(self, 
                     query: str,
                     top_k: int = 10,
                     vector_weight: float = 0.7,
                     keyword_weight: float = 0.3,
                     filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Perform hybrid search combining vector and keyword search.
        
        Args:
            query: Search query
            top_k: Number of results
            vector_weight: Weight for vector search
            keyword_weight: Weight for keyword search  
            filters: Query filters
            
        Returns:
            Hybrid search results
        """
        # Vector search
        vector_query = SearchQuery(
            query=query,
            filters=filters or {},
            top_k=top_k,
            expand_query=True,
            rerank=False,
            database_weights={"weaviate": 1.0, "pinecone": 1.0, "qdrant": 1.0}
        )
        
        vector_results = self.search(vector_query)
        
        # Apply weights and combine
        final_results = []
        for result in vector_results:
            # For hybrid search, we primarily rely on the vector search
            # but could add keyword matching boost here
            weighted_score = result.score * vector_weight
            
            # Simple keyword matching boost
            query_terms = set(query.lower().split())
            content_terms = set(result.content.lower().split())
            keyword_match = len(query_terms.intersection(content_terms)) / len(query_terms)
            weighted_score += keyword_match * keyword_weight
            
            hybrid_result = SearchResult(
                id=result.id,
                score=weighted_score,
                content=result.content,
                metadata=result.metadata,
                source_db=result.source_db,
                vector=result.vector,
                explanation=result.explanation
            )
            final_results.append(hybrid_result)
            
        # Sort by hybrid score
        final_results.sort(key=lambda x: x.score, reverse=True)
        
        return final_results[:top_k]
        
    def get_search_analytics(self) -> Dict[str, Any]:
        """Get search analytics and performance metrics."""
        if not self.search_stats:
            return {"message": "No search statistics available"}
            
        total_searches = len(self.search_stats)
        avg_search_time = np.mean([s.search_time for s in self.search_stats])
        avg_results = np.mean([s.total_results for s in self.search_stats])
        avg_top_score = np.mean([s.top_score for s in self.search_stats if s.top_score > 0])
        
        # Database usage statistics
        db_usage = {"pinecone": 0, "weaviate": 0, "qdrant": 0}
        for stats in self.search_stats:
            for db in stats.databases_searched:
                db_usage[db] += 1
                
        return {
            "total_searches": total_searches,
            "avg_search_time": avg_search_time,
            "avg_results_per_search": avg_results,
            "avg_top_score": avg_top_score,
            "database_usage": db_usage,
            "recent_queries": [s.query for s in self.search_stats[-10:]]
        }
        
    def clear_analytics(self):
        """Clear search analytics."""
        self.search_stats = []
        logger.info("Search analytics cleared")