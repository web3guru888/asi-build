"""
Performance Optimizer for Kenny Graph Intelligence System

Implements comprehensive performance optimizations including caching,
parallel processing, memory management, and query optimization for
the complete FastToG reasoning system.
"""

import asyncio
import gc
import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .fastog_reasoning import FastToGReasoningEngine, FastToGResult, ReasoningRequest
from .schema import NodeType, RelationshipType
from .schema_manager import SchemaManager

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    value: Any
    created_at: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    ttl_seconds: float = 3600.0  # 1 hour default TTL

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.created_at > self.ttl_seconds

    def touch(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


class LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]

            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                return None

            # Update access and move to end (most recently used)
            entry.touch()
            self.cache.move_to_end(key)
            return entry.value

    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Put value in cache."""
        with self._lock:
            # Remove if already exists
            if key in self.cache:
                del self.cache[key]

            # Create new entry
            entry = CacheEntry(
                key=key, value=value, created_at=time.time(), ttl_seconds=ttl or self.default_ttl
            )

            self.cache[key] = entry

            # Evict oldest if over max size
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]

    def invalidate(self, key: str) -> bool:
        """Remove entry from cache."""
        with self._lock:
            return self.cache.pop(key, None) is not None

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_accesses = sum(entry.access_count for entry in self.cache.values())
            expired_count = sum(1 for entry in self.cache.values() if entry.is_expired())

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "total_accesses": total_accesses,
                "expired_entries": expired_count,
                "hit_ratio": (
                    0.0
                    if not total_accesses
                    else sum(1 for entry in self.cache.values() if entry.access_count > 0)
                    / len(self.cache)
                ),
            }


@dataclass
class PerformanceMetrics:
    """Performance metrics collection."""

    operation_name: str
    duration: float
    cache_hits: int = 0
    cache_misses: int = 0
    parallel_tasks: int = 0
    memory_usage_mb: float = 0.0
    cpu_utilization: float = 0.0
    throughput_ops_per_sec: float = 0.0
    optimization_applied: List[str] = field(default_factory=list)


class QueryOptimizer:
    """Optimizes database queries for better performance."""

    def __init__(self, schema_manager: SchemaManager):
        self.sm = schema_manager
        self.query_cache = LRUCache(max_size=500, default_ttl=1800)  # 30 min TTL
        self.query_stats = defaultdict(int)

    def optimize(self, query: str) -> str:
        """Optimize a Cypher query for better performance."""
        # Basic query optimization rules
        optimized = query

        # Rule 1: Add LIMIT if not present for MATCH queries
        if "MATCH" in query and "LIMIT" not in query:
            optimized += " LIMIT 1000"

        # Rule 2: Use indexes when possible (add hints)
        if "WHERE" in query and "id" in query:
            optimized = optimized.replace("WHERE", "USING INDEX WHERE")

        # Rule 3: Optimize pattern matching
        optimized = optimized.replace("-[*]-", "-[*..5]-")  # Limit unbounded traversals

        return optimized

    def optimize_community_query(
        self, node_type: NodeType, filters: Dict[str, Any] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Optimize community finding queries."""
        # Generate cache key
        cache_key = self._generate_query_key("find_communities", node_type.value, filters, limit)

        # Try cache first
        cached_result = self.query_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for community query: {cache_key[:32]}")
            return cached_result

        # Execute optimized query
        start_time = time.time()

        # Use batch loading for better performance
        if not filters:
            result = self._batch_load_communities(node_type, limit)
        else:
            result = self.sm.find_nodes(node_type, filters, limit)

        duration = time.time() - start_time

        # Cache result
        self.query_cache.put(cache_key, result, ttl=1800)  # 30 minutes

        # Update stats
        self.query_stats[f"find_{node_type.value}"] += 1

        logger.debug(f"Optimized community query in {duration:.3f}s: {len(result)} results")
        return result

    def optimize_relationship_query(
        self,
        from_node: Optional[str] = None,
        to_node: Optional[str] = None,
        rel_type: Optional[RelationshipType] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Optimize relationship queries with caching."""
        # Generate cache key
        cache_key = self._generate_query_key(
            "find_relationships", from_node, to_node, rel_type.value if rel_type else None, limit
        )

        # Try cache first
        cached_result = self.query_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for relationship query")
            return cached_result

        # Execute query
        start_time = time.time()
        result = self.sm.find_relationships(from_node, to_node, rel_type, limit)
        duration = time.time() - start_time

        # Cache result with shorter TTL for relationships (more dynamic)
        self.query_cache.put(cache_key, result, ttl=600)  # 10 minutes

        logger.debug(f"Optimized relationship query in {duration:.3f}s: {len(result)} results")
        return result

    def _batch_load_communities(self, node_type: NodeType, limit: int) -> List[Dict[str, Any]]:
        """Load communities in batches for better performance."""
        batch_size = min(50, limit)
        results = []

        # Load in batches to avoid large single queries
        for offset in range(0, limit, batch_size):
            batch_limit = min(batch_size, limit - offset)
            batch_results = self.sm.find_nodes(node_type, None, batch_limit)
            results.extend(batch_results)

            if len(batch_results) < batch_limit:
                break  # No more results

        return results[:limit]

    def _generate_query_key(self, *args) -> str:
        """Generate cache key from query parameters."""
        key_data = json.dumps(args, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get query cache statistics."""
        return self.query_cache.get_stats()

    def invalidate_community_cache(self, community_id: str = None):
        """Invalidate community-related cache entries."""
        if community_id:
            # Invalidate specific community
            keys_to_remove = []
            for key in self.query_cache.cache.keys():
                if community_id in key:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                self.query_cache.invalidate(key)
        else:
            # Clear all community caches
            self.query_cache.clear()


class ParallelProcessor:
    """Handles parallel processing of graph operations."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def parallel_community_analysis(
        self, community_ids: List[str], analysis_func: callable, *args, **kwargs
    ) -> List[Any]:
        """Process communities in parallel."""
        if not community_ids:
            return []

        logger.debug(f"Starting parallel analysis of {len(community_ids)} communities")

        # Create tasks
        loop = asyncio.get_event_loop()
        tasks = []

        for community_id in community_ids:
            task = loop.run_in_executor(self.executor, analysis_func, community_id, *args, **kwargs)
            tasks.append(task)

        # Execute in parallel with timeout
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions
            valid_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Parallel task failed: {result}")
                else:
                    valid_results.append(result)

            logger.debug(
                f"Parallel analysis completed: {len(valid_results)}/{len(community_ids)} successful"
            )
            return valid_results

        except Exception as e:
            logger.error(f"Parallel processing failed: {e}")
            return []

    def batch_process_nodes(
        self, nodes: List[str], process_func: callable, batch_size: int = 10
    ) -> List[Any]:
        """Process nodes in batches for memory efficiency."""
        results = []

        for i in range(0, len(nodes), batch_size):
            batch = nodes[i : i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}/{(len(nodes)-1)//batch_size + 1}")

            # Process batch
            futures = []
            for node in batch:
                future = self.executor.submit(process_func, node)
                futures.append(future)

            # Collect results
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch processing failed for node: {e}")

        return results

    def shutdown(self):
        """Shutdown the thread executor."""
        self.executor.shutdown(wait=True)


class MemoryOptimizer:
    """Optimizes memory usage and manages garbage collection."""

    def __init__(self):
        self.memory_threshold_mb = 500  # 500 MB threshold
        self.gc_interval = 100  # Run GC every 100 operations
        self.operation_count = 0

    def optimize_for_large_graphs(self, node_count: int) -> Dict[str, Any]:
        """Apply optimizations for large graph processing."""
        optimizations = []

        # Increase memory threshold for large graphs
        if node_count > 1000:
            self.memory_threshold_mb = 1000
            optimizations.append("increased_memory_threshold")

        # Enable aggressive garbage collection
        if node_count > 500:
            gc.set_threshold(100, 10, 10)  # More aggressive GC
            optimizations.append("aggressive_gc")

        # Disable debug logging for performance
        if node_count > 100:
            logging.getLogger().setLevel(logging.INFO)
            optimizations.append("reduced_logging")

        return {
            "applied_optimizations": optimizations,
            "memory_threshold_mb": self.memory_threshold_mb,
            "estimated_memory_usage_mb": node_count * 0.1,  # Rough estimate
        }

    def check_memory_usage(self) -> Dict[str, Any]:
        """Check current memory usage."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        # Trigger GC if over threshold
        if memory_mb > self.memory_threshold_mb:
            collected = gc.collect()
            logger.info(f"Memory optimization: collected {collected} objects")

            # Check memory again after GC
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

        return {
            "memory_usage_mb": memory_mb,
            "memory_threshold_mb": self.memory_threshold_mb,
            "gc_triggered": memory_mb > self.memory_threshold_mb,
        }

    def periodic_cleanup(self):
        """Perform periodic cleanup operations."""
        self.operation_count += 1

        if self.operation_count % self.gc_interval == 0:
            collected = gc.collect()
            logger.debug(f"Periodic cleanup: collected {collected} objects")


class PerformanceOptimizer:
    """Main performance optimizer coordinating all optimization strategies."""

    def __init__(self, schema_manager: Optional[SchemaManager] = None):
        # Allow schema_manager to be optional, create one if not provided
        if schema_manager is None:
            schema_manager = SchemaManager()
        self.sm = schema_manager
        self.query_optimizer = QueryOptimizer(schema_manager)
        self.parallel_processor = ParallelProcessor()
        self.memory_optimizer = MemoryOptimizer()

        # Performance tracking
        self.metrics: List[PerformanceMetrics] = []
        self.optimization_cache = LRUCache(max_size=200, default_ttl=7200)  # 2 hour TTL

    def optimize_query(self, query: str) -> str:
        """Optimize a Cypher query for better performance."""
        return self.query_optimizer.optimize(query)

    def cache_result(self, key: str, value: Any, ttl: float = 3600):
        """Cache a result with specified TTL."""
        self.optimization_cache.put(key, value, ttl)

    def get_cached_result(self, key: str) -> Any:
        """Get a cached result."""
        return self.optimization_cache.get(key)

    async def optimize_fastog_reasoning(
        self, reasoning_request: ReasoningRequest, fastog_engine: FastToGReasoningEngine
    ) -> Tuple[FastToGResult, PerformanceMetrics]:
        """Apply comprehensive optimizations to FastToG reasoning."""
        start_time = time.time()
        operation_name = f"fastog_reasoning_{reasoning_request.reasoning_mode.value}"

        # Check optimization cache
        cache_key = self._generate_reasoning_cache_key(reasoning_request)
        cached_result = self.optimization_cache.get(cache_key)

        if cached_result:
            logger.info("Using cached FastToG reasoning result")
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                duration=time.time() - start_time,
                cache_hits=1,
                optimization_applied=["cached_result"],
            )
            return cached_result, metrics

        # Apply memory optimizations
        estimated_communities = min(reasoning_request.max_communities, 50)
        memory_opts = self.memory_optimizer.optimize_for_large_graphs(estimated_communities * 10)

        # Execute optimized reasoning
        try:
            # Pre-warm caches
            await self._prewarm_caches(reasoning_request)

            # Execute reasoning with monitoring
            reasoning_result = await fastog_engine.reason(reasoning_request)

            # Cache successful results
            if reasoning_result.overall_confidence > 0.5:
                self.optimization_cache.put(cache_key, reasoning_result, ttl=3600)  # 1 hour

            # Create performance metrics
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                duration=time.time() - start_time,
                cache_misses=1,
                parallel_tasks=reasoning_result.communities_analyzed,
                optimization_applied=memory_opts.get("applied_optimizations", []),
            )

            # Record metrics
            self.metrics.append(metrics)

            # Periodic cleanup
            self.memory_optimizer.periodic_cleanup()

            logger.info(f"Optimized FastToG reasoning completed in {metrics.duration:.3f}s")
            return reasoning_result, metrics

        except Exception as e:
            logger.error(f"Optimized reasoning failed: {e}")
            # Return error metrics
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                duration=time.time() - start_time,
                cache_misses=1,
                optimization_applied=["error_handling"],
            )
            raise

    async def optimize_community_detection(
        self, detection_algorithm: str = "louvain"
    ) -> Dict[str, Any]:
        """Optimize community detection with parallel processing."""
        start_time = time.time()

        # Use optimized queries
        all_nodes = self.query_optimizer.optimize_community_query(NodeType.UI_ELEMENT, limit=1000)

        if not all_nodes:
            return {"communities": [], "processing_time": time.time() - start_time}

        # Parallel processing for large graphs
        if len(all_nodes) > 100:
            logger.info(f"Using parallel processing for {len(all_nodes)} nodes")

            # Batch process nodes for relationship extraction
            batch_results = self.parallel_processor.batch_process_nodes(
                [node["id"] for node in all_nodes], self._extract_node_relationships, batch_size=20
            )

            relationships = []
            for batch_result in batch_results:
                if batch_result:
                    relationships.extend(batch_result)
        else:
            # Sequential processing for smaller graphs
            relationships = []
            for node in all_nodes:
                node_rels = self._extract_node_relationships(node["id"])
                if node_rels:
                    relationships.extend(node_rels)

        processing_time = time.time() - start_time

        return {
            "nodes_processed": len(all_nodes),
            "relationships_found": len(relationships),
            "processing_time": processing_time,
            "optimization": "parallel_processing" if len(all_nodes) > 100 else "sequential",
        }

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize overall memory usage."""
        memory_stats = self.memory_optimizer.check_memory_usage()

        # Clear old caches if memory is high
        if memory_stats["memory_usage_mb"] > memory_stats["memory_threshold_mb"]:
            # Clear optimization cache
            self.optimization_cache.clear()

            # Clear query cache
            self.query_optimizer.query_cache.clear()

            logger.info("Cleared caches due to high memory usage")
            memory_stats["caches_cleared"] = True
        else:
            memory_stats["caches_cleared"] = False

        return memory_stats

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        if not self.metrics:
            return {"message": "No performance metrics available"}

        # Calculate statistics
        durations = [m.duration for m in self.metrics]
        cache_hits = sum(m.cache_hits for m in self.metrics)
        cache_misses = sum(m.cache_misses for m in self.metrics)

        # Query cache stats
        query_cache_stats = self.query_optimizer.get_cache_stats()

        # Memory stats
        memory_stats = self.memory_optimizer.check_memory_usage()

        return {
            "total_operations": len(self.metrics),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "cache_hit_rate": (
                cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0.0
            ),
            "query_cache_stats": query_cache_stats,
            "memory_stats": memory_stats,
            "optimizations_applied": list(
                set([opt for m in self.metrics for opt in m.optimization_applied])
            ),
        }

    async def _prewarm_caches(self, reasoning_request: ReasoningRequest):
        """Pre-warm caches with likely needed data."""
        # Pre-load communities that might be relevant
        context = reasoning_request.context

        # Pre-load by application if specified
        if context.get("application"):
            app_communities = self.query_optimizer.optimize_community_query(
                NodeType.COMMUNITY,
                filters={"application": context["application"]},
                limit=reasoning_request.max_communities * 2,
            )
            logger.debug(f"Pre-warmed {len(app_communities)} app-specific communities")

        # Pre-load high-frequency communities
        frequent_communities = self.query_optimizer.optimize_community_query(
            NodeType.COMMUNITY, limit=reasoning_request.max_communities * 2
        )
        logger.debug(f"Pre-warmed {len(frequent_communities)} frequent communities")

    def _generate_reasoning_cache_key(self, request: ReasoningRequest) -> str:
        """Generate cache key for reasoning request."""
        key_data = {
            "user_intent": request.user_intent,
            "reasoning_mode": request.reasoning_mode.value,
            "max_communities": request.max_communities,
            "context_hash": hashlib.md5(
                json.dumps(request.context, sort_keys=True).encode()
            ).hexdigest()[:16],
        }

        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _extract_node_relationships(self, node_id: str) -> List[Dict[str, Any]]:
        """Extract relationships for a node (used in parallel processing)."""
        return self.query_optimizer.optimize_relationship_query(from_node=node_id, limit=20)

    def shutdown(self):
        """Shutdown optimizer and clean up resources."""
        self.parallel_processor.shutdown()
        self.optimization_cache.clear()
        self.query_optimizer.query_cache.clear()
        logger.info("Performance optimizer shutdown completed")


# Test the performance optimizer
if __name__ == "__main__":
    print("🚀 Testing Performance Optimizer...")

    async def test_performance_optimizer():
        with SchemaManager() as sm:
            optimizer = PerformanceOptimizer(sm)
            fastog_engine = FastToGReasoningEngine(sm)

            # Test optimized reasoning
            request = ReasoningRequest(
                user_intent="save document with optimization",
                context={
                    "application": "test_app",
                    "ui_elements": [
                        {"text": "Save", "type": "button"},
                        {"text": "File", "type": "menu"},
                    ],
                },
                max_communities=5,
            )

            # First run (cache miss)
            print("🔍 Testing optimized reasoning (first run)...")
            result1, metrics1 = await optimizer.optimize_fastog_reasoning(request, fastog_engine)

            print(f"✅ First Run Results:")
            print(f"   - Duration: {metrics1.duration:.3f}s")
            print(f"   - Cache Hits: {metrics1.cache_hits}")
            print(f"   - Cache Misses: {metrics1.cache_misses}")
            print(f"   - Communities: {result1.communities_analyzed}")
            print(f"   - Confidence: {result1.overall_confidence:.1%}")
            print(f"   - Optimizations: {metrics1.optimization_applied}")

            # Second run (should hit cache)
            print("\n🔍 Testing optimized reasoning (second run - cached)...")
            result2, metrics2 = await optimizer.optimize_fastog_reasoning(request, fastog_engine)

            print(f"✅ Second Run Results:")
            print(f"   - Duration: {metrics2.duration:.3f}s")
            print(f"   - Cache Hits: {metrics2.cache_hits}")
            print(f"   - Cache Misses: {metrics2.cache_misses}")
            print(f"   - Speedup: {metrics1.duration / max(metrics2.duration, 0.001):.2f}x faster")

            # Test community detection optimization
            print("\n🔍 Testing community detection optimization...")
            detection_result = await optimizer.optimize_community_detection("louvain")

            print(f"✅ Community Detection Results:")
            print(f"   - Nodes Processed: {detection_result['nodes_processed']}")
            print(f"   - Relationships Found: {detection_result['relationships_found']}")
            print(f"   - Processing Time: {detection_result['processing_time']:.3f}s")
            print(f"   - Optimization Method: {detection_result['optimization']}")

            # Test memory optimization
            print("\n🔍 Testing memory optimization...")
            memory_stats = optimizer.optimize_memory_usage()

            print(f"✅ Memory Optimization Results:")
            print(f"   - Memory Usage: {memory_stats['memory_usage_mb']:.1f} MB")
            print(f"   - Memory Threshold: {memory_stats['memory_threshold_mb']} MB")
            print(f"   - GC Triggered: {memory_stats.get('gc_triggered', False)}")
            print(f"   - Caches Cleared: {memory_stats.get('caches_cleared', False)}")

            # Generate performance report
            print("\n📊 Performance Report:")
            report = optimizer.get_performance_report()

            print(f"   - Total Operations: {report['total_operations']}")
            print(f"   - Average Duration: {report['avg_duration']:.3f}s")
            print(f"   - Cache Hit Rate: {report['cache_hit_rate']:.1%}")
            print(f"   - Query Cache Size: {report['query_cache_stats']['size']}")
            print(f"   - Applied Optimizations: {report['optimizations_applied']}")

            # Cleanup
            optimizer.shutdown()

    # Run async test
    asyncio.run(test_performance_optimizer())
    print("✅ Performance Optimizer testing completed!")
