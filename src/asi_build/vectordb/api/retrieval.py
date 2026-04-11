"""
Retrieval API for Kenny Vector Database System

This module provides advanced retrieval capabilities including:
- Multi-modal search (semantic, keyword, hybrid)
- Query optimization and caching
- Result aggregation and ranking
- Retrieval analytics and monitoring
- Advanced filtering and faceted search
"""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ..core.search import SearchQuery, SearchResult
from ..core.utils import timed_operation
from .unified_client import UnifiedVectorDB

logger = logging.getLogger(__name__)


@dataclass
class RetrievalQuery:
    """Advanced retrieval query with multiple search modes."""

    query: str
    search_mode: str = "semantic"  # semantic, keyword, hybrid, vector
    top_k: int = 10
    filters: Dict[str, Any] = field(default_factory=dict)
    facets: List[str] = field(default_factory=list)
    score_threshold: float = 0.0
    include_vectors: bool = False
    include_explanations: bool = False
    rerank: bool = True
    expand_query: bool = True
    query_vector: Optional[List[float]] = None
    date_range: Optional[Dict[str, Any]] = None
    category_filter: Optional[List[str]] = None
    tag_filter: Optional[List[str]] = None
    boost_fields: Dict[str, float] = field(default_factory=dict)
    custom_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class FacetResult:
    """Facet aggregation result."""

    field: str
    values: Dict[str, int]  # value -> count
    total_docs: int


@dataclass
class RetrievalResult:
    """Enhanced retrieval result with aggregations."""

    results: List[SearchResult]
    total_found: int
    query_time: float
    facets: Dict[str, FacetResult] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    explanation: Optional[Dict[str, Any]] = None


@dataclass
class QueryCache:
    """Query result cache."""

    query_hash: str
    results: RetrievalResult
    timestamp: float
    ttl: float = 300.0  # 5 minutes default TTL

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() > (self.timestamp + self.ttl)


class QueryOptimizer:
    """Query optimization and suggestion engine."""

    def __init__(self):
        self.query_history: List[str] = []
        self.popular_terms: Dict[str, int] = defaultdict(int)
        self.successful_queries: Set[str] = set()

    def optimize_query(self, query: str) -> str:
        """
        Optimize query for better results.

        Args:
            query: Original query

        Returns:
            Optimized query
        """
        optimized = query.strip()

        # Track query terms
        terms = optimized.lower().split()
        for term in terms:
            self.popular_terms[term] += 1

        # Basic query cleaning
        optimized = " ".join(optimized.split())  # Remove extra whitespace

        # Remove very common stop words that don't add semantic value
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        words = optimized.split()
        if len(words) > 2:  # Only filter if query has more than 2 words
            filtered_words = [w for w in words if w.lower() not in stop_words]
            if filtered_words:
                optimized = " ".join(filtered_words)

        return optimized

    def suggest_queries(self, query: str, max_suggestions: int = 5) -> List[str]:
        """
        Suggest related queries based on history.

        Args:
            query: Current query
            max_suggestions: Maximum suggestions to return

        Returns:
            List of suggested queries
        """
        suggestions = []
        query_terms = set(query.lower().split())

        # Find similar successful queries
        for successful_query in list(self.successful_queries)[-100:]:  # Recent queries
            success_terms = set(successful_query.lower().split())

            # Calculate overlap
            overlap = len(query_terms.intersection(success_terms))
            if overlap > 0 and successful_query != query:
                suggestions.append(successful_query)

        # Sort by relevance (term overlap) and limit
        suggestions = list(set(suggestions))[:max_suggestions]

        return suggestions

    def record_successful_query(self, query: str):
        """Record a successful query for future suggestions."""
        self.successful_queries.add(query)
        self.query_history.append(query)

        # Limit history size
        if len(self.query_history) > 1000:
            self.query_history = self.query_history[-500:]

    def get_popular_terms(self, top_k: int = 10) -> List[Tuple[str, int]]:
        """Get most popular query terms."""
        sorted_terms = sorted(self.popular_terms.items(), key=lambda x: x[1], reverse=True)
        return sorted_terms[:top_k]


class FacetProcessor:
    """Faceted search processor."""

    def __init__(self):
        self.facet_extractors = {
            "category": self._extract_category,
            "tags": self._extract_tags,
            "source": self._extract_source,
            "date": self._extract_date,
            "content_length": self._extract_content_length,
        }

    def compute_facets(
        self, results: List[SearchResult], facet_fields: List[str]
    ) -> Dict[str, FacetResult]:
        """
        Compute facet aggregations from search results.

        Args:
            results: Search results
            facet_fields: Fields to facet on

        Returns:
            Facet results
        """
        facets = {}

        for field in facet_fields:
            if field in self.facet_extractors:
                facet_values = defaultdict(int)

                for result in results:
                    values = self.facet_extractors[field](result)
                    if isinstance(values, list):
                        for value in values:
                            facet_values[str(value)] += 1
                    else:
                        facet_values[str(values)] += 1

                facets[field] = FacetResult(
                    field=field, values=dict(facet_values), total_docs=len(results)
                )

        return facets

    def _extract_category(self, result: SearchResult) -> str:
        """Extract category from result."""
        return result.metadata.get("category", "unknown")

    def _extract_tags(self, result: SearchResult) -> List[str]:
        """Extract tags from result."""
        tags = result.metadata.get("tags", [])
        if isinstance(tags, str):
            return [tags]
        return tags or ["untagged"]

    def _extract_source(self, result: SearchResult) -> str:
        """Extract source from result."""
        return result.metadata.get("source", "unknown")

    def _extract_date(self, result: SearchResult) -> str:
        """Extract date bucket from result."""
        timestamp = result.metadata.get("timestamp")
        if timestamp:
            try:
                import datetime

                dt = datetime.datetime.fromtimestamp(timestamp)
                return dt.strftime("%Y-%m")  # Year-month bucket
            except:
                pass
        return "unknown"

    def _extract_content_length(self, result: SearchResult) -> str:
        """Extract content length bucket."""
        content_length = len(result.content)

        if content_length < 100:
            return "short"
        elif content_length < 500:
            return "medium"
        elif content_length < 1000:
            return "long"
        else:
            return "very_long"


class RetrievalAPI:
    """
    Advanced retrieval API for Kenny Vector Database System.

    Provides comprehensive search and retrieval capabilities with query optimization,
    caching, faceted search, and analytics.
    """

    def __init__(self, vector_db: UnifiedVectorDB, cache_size: int = 100):
        """
        Initialize retrieval API.

        Args:
            vector_db: Unified vector database client
            cache_size: Maximum number of cached queries
        """
        self.vector_db = vector_db
        self.cache_size = cache_size

        # Components
        self.query_optimizer = QueryOptimizer()
        self.facet_processor = FacetProcessor()

        # Query cache
        self.query_cache: Dict[str, QueryCache] = {}

        # Analytics
        self.retrieval_stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_query_time": 0.0,
            "successful_queries": 0,
            "failed_queries": 0,
        }

    def _generate_cache_key(self, query: RetrievalQuery) -> str:
        """Generate cache key for query."""
        query_data = {
            "query": query.query,
            "search_mode": query.search_mode,
            "top_k": query.top_k,
            "filters": query.filters,
            "facets": sorted(query.facets),
            "score_threshold": query.score_threshold,
        }

        query_str = json.dumps(query_data, sort_keys=True)
        return hashlib.md5(query_str.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[RetrievalResult]:
        """Get cached query result if available and not expired."""
        if cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            if not cache_entry.is_expired():
                self.retrieval_stats["cache_hits"] += 1
                return cache_entry.results
            else:
                # Remove expired entry
                del self.query_cache[cache_key]

        self.retrieval_stats["cache_misses"] += 1
        return None

    def _cache_result(self, cache_key: str, result: RetrievalResult, ttl: float = 300.0):
        """Cache query result."""
        # Limit cache size
        if len(self.query_cache) >= self.cache_size:
            # Remove oldest entry
            oldest_key = min(self.query_cache.keys(), key=lambda k: self.query_cache[k].timestamp)
            del self.query_cache[oldest_key]

        # Cache result
        self.query_cache[cache_key] = QueryCache(
            query_hash=cache_key, results=result, timestamp=time.time(), ttl=ttl
        )

    @timed_operation("advanced_retrieval")
    def search(self, query: RetrievalQuery, use_cache: bool = True) -> RetrievalResult:
        """
        Perform advanced search with multiple modes and optimizations.

        Args:
            query: Retrieval query
            use_cache: Whether to use query cache

        Returns:
            Retrieval result with search results and aggregations
        """
        start_time = time.time()

        # Generate cache key
        cache_key = self._generate_cache_key(query)

        # Check cache first
        if use_cache:
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result

        try:
            # Optimize query
            optimized_query = self.query_optimizer.optimize_query(query.query)

            # Build search parameters
            search_results = []

            if query.search_mode == "semantic":
                search_results = self._semantic_search(query, optimized_query)
            elif query.search_mode == "keyword":
                search_results = self._keyword_search(query, optimized_query)
            elif query.search_mode == "hybrid":
                search_results = self._hybrid_search(query, optimized_query)
            elif query.search_mode == "vector" and query.query_vector:
                search_results = self._vector_search(query)
            else:
                # Default to semantic search
                search_results = self._semantic_search(query, optimized_query)

            # Apply additional filtering
            filtered_results = self._apply_advanced_filters(search_results, query)

            # Compute facets
            facets = {}
            if query.facets:
                facets = self.facet_processor.compute_facets(filtered_results, query.facets)

            # Generate suggestions
            suggestions = self.query_optimizer.suggest_queries(query.query)

            # Create result
            query_time = time.time() - start_time
            result = RetrievalResult(
                results=filtered_results,
                total_found=len(filtered_results),
                query_time=query_time,
                facets=facets,
                suggestions=suggestions,
            )

            # Cache result
            if use_cache:
                self._cache_result(cache_key, result)

            # Update analytics
            self.retrieval_stats["total_queries"] += 1
            self.retrieval_stats["successful_queries"] += 1
            self._update_avg_query_time(query_time)

            # Record successful query
            if len(filtered_results) > 0:
                self.query_optimizer.record_successful_query(optimized_query)

            return result

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            self.retrieval_stats["failed_queries"] += 1

            # Return empty result
            return RetrievalResult(results=[], total_found=0, query_time=time.time() - start_time)

    def _semantic_search(self, query: RetrievalQuery, optimized_query: str) -> List[SearchResult]:
        """Perform semantic search."""
        return self.vector_db.semantic_search(
            query=optimized_query,
            top_k=query.top_k,
            expand_query=query.expand_query,
            rerank=query.rerank,
        )

    def _keyword_search(self, query: RetrievalQuery, optimized_query: str) -> List[SearchResult]:
        """Perform keyword-based search."""
        # For keyword search, we use the semantic search but without expansion
        return self.vector_db.search(
            query=optimized_query,
            top_k=query.top_k,
            filters=query.filters,
            score_threshold=query.score_threshold,
        )

    def _hybrid_search(self, query: RetrievalQuery, optimized_query: str) -> List[SearchResult]:
        """Perform hybrid search."""
        vector_weight = query.custom_weights.get("vector", 0.7)
        keyword_weight = query.custom_weights.get("keyword", 0.3)

        return self.vector_db.hybrid_search(
            query=optimized_query,
            top_k=query.top_k,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
        )

    def _vector_search(self, query: RetrievalQuery) -> List[SearchResult]:
        """Perform direct vector search."""
        from ..core.search import SearchQuery

        search_query = SearchQuery(
            query="",  # Empty since we're using vector directly
            top_k=query.top_k,
            filters=query.filters,
            score_threshold=query.score_threshold,
            include_vectors=query.include_vectors,
            expand_query=False,
            rerank=query.rerank,
        )

        # This would need custom implementation in the search engine
        # For now, fallback to semantic search
        return self._semantic_search(query, query.query)

    def _apply_advanced_filters(
        self, results: List[SearchResult], query: RetrievalQuery
    ) -> List[SearchResult]:
        """Apply advanced filtering to results."""
        filtered = results

        # Date range filtering
        if query.date_range:
            start_date = query.date_range.get("start")
            end_date = query.date_range.get("end")

            date_filtered = []
            for result in filtered:
                timestamp = result.metadata.get("timestamp")
                if timestamp:
                    if start_date and timestamp < start_date:
                        continue
                    if end_date and timestamp > end_date:
                        continue
                date_filtered.append(result)
            filtered = date_filtered

        # Category filtering
        if query.category_filter:
            category_filtered = []
            for result in filtered:
                category = result.metadata.get("category")
                if category in query.category_filter:
                    category_filtered.append(result)
            filtered = category_filtered

        # Tag filtering
        if query.tag_filter:
            tag_filtered = []
            for result in filtered:
                result_tags = result.metadata.get("tags", [])
                if isinstance(result_tags, str):
                    result_tags = [result_tags]

                if any(tag in query.tag_filter for tag in result_tags):
                    tag_filtered.append(result)
            filtered = tag_filtered

        # Apply field boosting
        if query.boost_fields:
            for result in filtered:
                boost = 1.0
                for field, boost_factor in query.boost_fields.items():
                    if field in result.metadata and result.metadata[field]:
                        boost *= boost_factor

                result.score *= boost

            # Re-sort by boosted scores
            filtered.sort(key=lambda x: x.score, reverse=True)

        return filtered

    def suggest_completions(self, partial_query: str, max_suggestions: int = 5) -> List[str]:
        """
        Suggest query completions based on history.

        Args:
            partial_query: Partial query to complete
            max_suggestions: Maximum suggestions to return

        Returns:
            List of completion suggestions
        """
        suggestions = []
        partial_lower = partial_query.lower()

        # Find queries that start with the partial query
        for query in self.query_optimizer.query_history[-200:]:  # Recent queries
            if query.lower().startswith(partial_lower) and query != partial_query:
                suggestions.append(query)

        # Remove duplicates and limit
        suggestions = list(set(suggestions))[:max_suggestions]

        return suggestions

    def get_similar_documents(self, document_id: str, top_k: int = 10) -> List[SearchResult]:
        """
        Find documents similar to a given document.

        Args:
            document_id: ID of the reference document
            top_k: Number of similar documents to return

        Returns:
            List of similar documents
        """
        try:
            # Get the reference document
            reference_doc = self.vector_db.get_document(
                document_id=document_id, include_vector=True
            )

            if not reference_doc or not reference_doc.vector:
                logger.error(f"Document {document_id} not found or has no vector")
                return []

            # Search using the document's vector
            query = RetrievalQuery(
                query="",  # Empty query for vector search
                search_mode="vector",
                top_k=top_k + 1,  # +1 to account for the reference doc itself
                query_vector=reference_doc.vector,
                include_vectors=False,
            )

            result = self.search(query, use_cache=False)

            # Remove the reference document from results
            similar_docs = [doc for doc in result.results if doc.id != document_id]

            return similar_docs[:top_k]

        except Exception as e:
            logger.error(f"Error finding similar documents: {str(e)}")
            return []

    def get_recommendations(
        self, user_history: List[str], top_k: int = 10, diversity_factor: float = 0.3
    ) -> List[SearchResult]:
        """
        Get personalized recommendations based on user history.

        Args:
            user_history: List of document IDs the user has interacted with
            top_k: Number of recommendations
            diversity_factor: Factor for result diversification (0-1)

        Returns:
            List of recommended documents
        """
        try:
            all_recommendations = []

            # Get similar documents for each item in history
            for doc_id in user_history[-10:]:  # Use recent history
                similar_docs = self.get_similar_documents(doc_id, top_k=20)
                all_recommendations.extend(similar_docs)

            # Remove duplicates and documents from history
            seen_ids = set(user_history)
            unique_recommendations = []

            for doc in all_recommendations:
                if doc.id not in seen_ids:
                    unique_recommendations.append(doc)
                    seen_ids.add(doc.id)

            # Sort by score
            unique_recommendations.sort(key=lambda x: x.score, reverse=True)

            # Apply diversity if requested
            if diversity_factor > 0 and len(unique_recommendations) > top_k:
                diverse_recommendations = self._diversify_results(
                    unique_recommendations, top_k, diversity_factor
                )
                return diverse_recommendations
            else:
                return unique_recommendations[:top_k]

        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return []

    def _diversify_results(
        self, results: List[SearchResult], top_k: int, diversity_factor: float
    ) -> List[SearchResult]:
        """Apply diversity to search results."""
        if diversity_factor == 0 or len(results) <= top_k:
            return results[:top_k]

        diverse_results = []
        remaining_results = results.copy()

        # Add highest scoring result first
        if remaining_results:
            diverse_results.append(remaining_results.pop(0))

        # Add remaining results with diversity consideration
        while len(diverse_results) < top_k and remaining_results:
            best_candidate = None
            best_score = -1

            for i, candidate in enumerate(remaining_results):
                # Calculate diversity score
                min_similarity = float("inf")

                for selected in diverse_results:
                    # Simple content-based similarity
                    similarity = self._calculate_content_similarity(candidate, selected)
                    min_similarity = min(min_similarity, similarity)

                # Combined score: relevance + diversity
                combined_score = (
                    candidate.score * (1 - diversity_factor)
                    + (1 - min_similarity) * diversity_factor
                )

                if combined_score > best_score:
                    best_score = combined_score
                    best_candidate = i

            if best_candidate is not None:
                diverse_results.append(remaining_results.pop(best_candidate))
            else:
                break

        return diverse_results

    def _calculate_content_similarity(self, doc1: SearchResult, doc2: SearchResult) -> float:
        """Calculate simple content similarity between two documents."""
        words1 = set(doc1.content.lower().split())
        words2 = set(doc2.content.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _update_avg_query_time(self, query_time: float):
        """Update average query time statistic."""
        current_avg = self.retrieval_stats["avg_query_time"]
        total_queries = self.retrieval_stats["total_queries"]

        if total_queries == 1:
            self.retrieval_stats["avg_query_time"] = query_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.retrieval_stats["avg_query_time"] = alpha * query_time + (1 - alpha) * current_avg

    def clear_cache(self):
        """Clear query cache."""
        self.query_cache.clear()
        logger.info("Query cache cleared")

    def get_analytics(self) -> Dict[str, Any]:
        """Get retrieval analytics."""
        cache_hit_rate = self.retrieval_stats["cache_hits"] / max(
            self.retrieval_stats["cache_hits"] + self.retrieval_stats["cache_misses"], 1
        )

        success_rate = self.retrieval_stats["successful_queries"] / max(
            self.retrieval_stats["total_queries"], 1
        )

        popular_terms = self.query_optimizer.get_popular_terms()

        return {
            "retrieval_stats": self.retrieval_stats.copy(),
            "cache_stats": {
                "cache_size": len(self.query_cache),
                "cache_hit_rate": cache_hit_rate,
                "max_cache_size": self.cache_size,
            },
            "query_stats": {
                "success_rate": success_rate,
                "popular_terms": popular_terms[:10],
                "total_unique_queries": len(self.query_optimizer.successful_queries),
            },
        }

    def export_analytics(self, filepath: str):
        """Export analytics to JSON file."""
        analytics = self.get_analytics()

        # Add additional data
        analytics["export_timestamp"] = time.time()
        analytics["query_history_sample"] = self.query_optimizer.query_history[-50:]

        with open(filepath, "w") as f:
            json.dump(analytics, f, indent=2, default=str)

        logger.info(f"Analytics exported to {filepath}")

    def reset_analytics(self):
        """Reset all analytics data."""
        self.retrieval_stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_query_time": 0.0,
            "successful_queries": 0,
            "failed_queries": 0,
        }

        self.query_optimizer.query_history.clear()
        self.query_optimizer.popular_terms.clear()
        self.query_optimizer.successful_queries.clear()

        logger.info("Analytics data reset")
