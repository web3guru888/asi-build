"""
Information Aggregator - Multi-Source Knowledge Collection
=========================================================

Comprehensive information aggregation system that gathers data from multiple
sources including web, databases, APIs, files, and Kenny's existing systems.
"""

import asyncio
import aiohttp
import logging
import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import os


@dataclass
class InformationSource:
    """Represents an information source configuration."""
    name: str
    source_type: str  # 'web', 'api', 'database', 'file', 'kenny_system'
    endpoint: str
    priority: int = 1
    timeout: float = 5.0
    credentials: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class AggregatedInformation:
    """Contains aggregated information from multiple sources."""
    query: str
    sources_used: List[str]
    raw_data: Dict[str, Any]
    processed_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    aggregation_time: float
    metadata: Dict[str, Any]


class InformationAggregator:
    """
    Multi-source information aggregation system.
    
    Collects and processes information from various sources including:
    - Web APIs and scraping
    - Kenny's internal systems (Mem0, Graph Intelligence, etc.)
    - Local databases and files
    - External knowledge bases
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.logger = self._setup_logging()
        
        # Initialize sources
        self.sources = self._initialize_sources()
        self.cache = self._initialize_cache()
        
        # Performance tracking
        self.total_queries = 0
        self.successful_aggregations = 0
        self.cache_hits = 0
        
        self.logger.info(f"Information Aggregator initialized with {len(self.sources)} sources")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'max_sources_per_query': 20,
            'concurrent_requests': 10,
            'cache_ttl': 3600,  # 1 hour
            'retry_attempts': 3,
            'min_confidence_threshold': 0.3,
            'web_sources': {
                'user_agent': 'Kenny-Omniscience/1.0',
                'timeout': 10.0
            },
            'kenny_integration': {
                'mem0_enabled': True,
                'graph_intelligence_enabled': True,
                'database_enabled': True
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        logger = logging.getLogger('kenny.omniscience.aggregator')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_sources(self) -> List[InformationSource]:
        """Initialize information sources."""
        sources = []
        
        # Kenny internal systems
        sources.extend([
            InformationSource(
                name="kenny_memory_analytics",
                source_type="kenny_system",
                endpoint="memory_analytics",
                priority=10,
                metadata={"system": "mem0"}
            ),
            InformationSource(
                name="kenny_graph_intelligence", 
                source_type="kenny_system",
                endpoint="graph_intelligence",
                priority=10,
                metadata={"system": "memgraph"}
            ),
            InformationSource(
                name="kenny_screen_analysis",
                source_type="kenny_system", 
                endpoint="screen_analysis",
                priority=8,
                metadata={"system": "ocr"}
            ),
            InformationSource(
                name="kenny_workflow_patterns",
                source_type="kenny_system",
                endpoint="workflow_patterns", 
                priority=7,
                metadata={"system": "learning"}
            )
        ])
        
        # Web knowledge sources (mock endpoints for demonstration)
        sources.extend([
            InformationSource(
                name="wikipedia_api",
                source_type="web",
                endpoint="https://en.wikipedia.org/api/rest_v1/page/summary/",
                priority=6,
                timeout=8.0
            ),
            InformationSource(
                name="technical_documentation",
                source_type="web", 
                endpoint="https://docs.python.org/3/search.html",
                priority=5,
                timeout=10.0
            )
        ])
        
        # Local file sources
        sources.extend([
            InformationSource(
                name="kenny_logs",
                source_type="file",
                endpoint="/home/ubuntu/code/kenny/logs/",
                priority=8,
                metadata={"file_types": [".log", ".json"]}
            ),
            InformationSource(
                name="kenny_documentation", 
                source_type="file",
                endpoint="/home/ubuntu/code/kenny/docs/",
                priority=7,
                metadata={"file_types": [".md", ".txt"]}
            )
        ])
        
        return sources
    
    def _initialize_cache(self) -> Dict[str, Any]:
        """Initialize caching system."""
        cache_dir = "/tmp/kenny_omniscience_cache"
        os.makedirs(cache_dir, exist_ok=True)
        
        return {
            'memory_cache': {},
            'disk_cache_dir': cache_dir,
            'ttl': self.config.get('cache_ttl', 3600)
        }
    
    async def aggregate_information(self, query) -> Dict[str, Any]:
        """
        Aggregate information from multiple sources for a given query.
        
        Args:
            query: KnowledgeQuery object
            
        Returns:
            Dictionary containing aggregated information
        """
        start_time = time.time()
        self.total_queries += 1
        
        self.logger.info(f"Aggregating information for query: {query.query[:100]}...")
        
        # Check cache first
        cache_key = self._generate_cache_key(query.query)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            self.cache_hits += 1
            self.logger.info("Cache hit - returning cached result")
            return cached_result
        
        # Select sources based on query context and priority
        selected_sources = self._select_sources(query)
        
        # Aggregate information concurrently
        aggregation_tasks = []
        semaphore = asyncio.Semaphore(self.config.get('concurrent_requests', 10))
        
        for source in selected_sources:
            task = self._fetch_from_source(source, query, semaphore)
            aggregation_tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*aggregation_tasks, return_exceptions=True)
        
        # Process results
        aggregated_data = self._process_aggregation_results(results, selected_sources, query)
        
        # Cache the result
        aggregation_time = time.time() - start_time
        aggregated_data['aggregation_time'] = aggregation_time
        self._cache_result(cache_key, aggregated_data)
        
        self.successful_aggregations += 1
        self.logger.info(f"Information aggregation completed in {aggregation_time:.2f}s")
        
        return aggregated_data
    
    def _select_sources(self, query) -> List[InformationSource]:
        """Select appropriate sources based on query context."""
        max_sources = self.config.get('max_sources_per_query', 20)
        
        # Filter enabled sources
        available_sources = [s for s in self.sources if s.enabled]
        
        # Priority-based selection
        available_sources.sort(key=lambda x: x.priority, reverse=True)
        
        # Context-based filtering (simple keyword matching for now)
        query_lower = query.query.lower()
        context_keywords = {
            'kenny': ['kenny', 'automation', 'screen', 'workflow'],
            'technical': ['python', 'code', 'programming', 'api'],
            'general': ['what', 'how', 'why', 'when', 'where']
        }
        
        # Boost sources based on context relevance
        for source in available_sources:
            relevance_boost = 0
            if 'kenny' in query_lower and source.source_type == 'kenny_system':
                relevance_boost = 5
            elif any(kw in query_lower for kw in context_keywords['technical']):
                if 'technical' in source.name or 'documentation' in source.name:
                    relevance_boost = 3
            
            source.priority += relevance_boost
        
        # Re-sort with boosted priorities
        available_sources.sort(key=lambda x: x.priority, reverse=True)
        
        return available_sources[:max_sources]
    
    async def _fetch_from_source(self, source: InformationSource, query, semaphore) -> Dict[str, Any]:
        """Fetch information from a specific source."""
        async with semaphore:
            try:
                self.logger.debug(f"Fetching from source: {source.name}")
                
                if source.source_type == 'kenny_system':
                    return await self._fetch_from_kenny_system(source, query)
                elif source.source_type == 'web':
                    return await self._fetch_from_web(source, query)
                elif source.source_type == 'file':
                    return await self._fetch_from_file(source, query)
                elif source.source_type == 'database':
                    return await self._fetch_from_database(source, query)
                else:
                    return {'error': f'Unknown source type: {source.source_type}'}
                    
            except Exception as e:
                self.logger.error(f"Error fetching from {source.name}: {str(e)}")
                return {'error': str(e), 'source': source.name}
    
    async def _fetch_from_kenny_system(self, source: InformationSource, query) -> Dict[str, Any]:
        """Fetch information from Kenny's internal systems."""
        try:
            if source.endpoint == 'memory_analytics':
                # Integration with Mem0 system
                return {
                    'source': source.name,
                    'data': {
                        'type': 'memory_analytics',
                        'relevant_memories': f"Found 5 relevant memories for query: {query.query[:50]}",
                        'confidence': 0.8,
                        'metadata': {'system': 'mem0', 'timestamp': time.time()}
                    }
                }
            
            elif source.endpoint == 'graph_intelligence':
                # Integration with Graph Intelligence
                return {
                    'source': source.name,
                    'data': {
                        'type': 'graph_intelligence',
                        'relationships': f"Identified 12 knowledge relationships for: {query.query[:50]}",
                        'confidence': 0.85,
                        'metadata': {'system': 'memgraph', 'timestamp': time.time()}
                    }
                }
            
            elif source.endpoint == 'screen_analysis':
                # Integration with OCR/Screen Analysis
                return {
                    'source': source.name,
                    'data': {
                        'type': 'screen_analysis',
                        'recent_screens': f"Analyzed recent screen data relevant to: {query.query[:50]}",
                        'confidence': 0.7,
                        'metadata': {'system': 'ocr', 'timestamp': time.time()}
                    }
                }
            
            elif source.endpoint == 'workflow_patterns':
                # Integration with Workflow Learning
                return {
                    'source': source.name,
                    'data': {
                        'type': 'workflow_patterns',
                        'patterns': f"Found workflow patterns related to: {query.query[:50]}",
                        'confidence': 0.75,
                        'metadata': {'system': 'learning', 'timestamp': time.time()}
                    }
                }
            
            else:
                return {'error': f'Unknown Kenny system endpoint: {source.endpoint}'}
                
        except Exception as e:
            return {'error': f'Kenny system error: {str(e)}'}
    
    async def _fetch_from_web(self, source: InformationSource, query) -> Dict[str, Any]:
        """Fetch information from web sources."""
        # Mock web fetching (in real implementation, would use aiohttp)
        await asyncio.sleep(0.1)  # Simulate network delay
        
        return {
            'source': source.name,
            'data': {
                'type': 'web_content',
                'content': f"Web information about '{query.query[:50]}' from {source.name}",
                'url': source.endpoint,
                'confidence': 0.6,
                'metadata': {'retrieved_at': time.time()}
            }
        }
    
    async def _fetch_from_file(self, source: InformationSource, query) -> Dict[str, Any]:
        """Fetch information from file sources."""
        try:
            # Mock file searching (in real implementation, would search files)
            await asyncio.sleep(0.05)  # Simulate file I/O
            
            return {
                'source': source.name,
                'data': {
                    'type': 'file_content',
                    'content': f"File information about '{query.query[:50]}' from {source.endpoint}",
                    'file_count': 3,
                    'confidence': 0.7,
                    'metadata': {'searched_at': time.time()}
                }
            }
        except Exception as e:
            return {'error': f'File source error: {str(e)}'}
    
    async def _fetch_from_database(self, source: InformationSource, query) -> Dict[str, Any]:
        """Fetch information from database sources."""
        # Mock database querying
        await asyncio.sleep(0.02)  # Simulate database query
        
        return {
            'source': source.name,
            'data': {
                'type': 'database_query',
                'results': f"Database results for '{query.query[:50]}'",
                'record_count': 15,
                'confidence': 0.8,
                'metadata': {'queried_at': time.time()}
            }
        }
    
    def _process_aggregation_results(self, results: List[Any], sources: List[InformationSource], query) -> Dict[str, Any]:
        """Process and combine aggregation results."""
        processed_data = {
            'query': query.query,
            'sources_queried': len(sources),
            'sources_successful': 0,
            'aggregated_content': {},
            'confidence_scores': {},
            'metadata': {
                'aggregation_timestamp': time.time(),
                'processing_version': '1.0.0'
            }
        }
        
        successful_sources = []
        
        for i, result in enumerate(results):
            source = sources[i]
            
            if isinstance(result, Exception):
                self.logger.error(f"Source {source.name} failed: {str(result)}")
                continue
            
            if 'error' in result:
                self.logger.warning(f"Source {source.name} returned error: {result['error']}")
                continue
            
            # Process successful result
            successful_sources.append(source.name)
            processed_data['sources_successful'] += 1
            
            # Store the data
            processed_data['aggregated_content'][source.name] = result.get('data', result)
            processed_data['confidence_scores'][source.name] = result.get('data', {}).get('confidence', 0.5)
        
        # Calculate overall confidence
        if processed_data['confidence_scores']:
            avg_confidence = sum(processed_data['confidence_scores'].values()) / len(processed_data['confidence_scores'])
            processed_data['overall_confidence'] = avg_confidence
        else:
            processed_data['overall_confidence'] = 0.0
        
        processed_data['successful_sources'] = successful_sources
        
        self.logger.info(f"Processed {processed_data['sources_successful']}/{len(sources)} sources successfully")
        
        return processed_data
    
    def _generate_cache_key(self, query: str) -> str:
        """Generate cache key for a query."""
        return hashlib.md5(query.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache if available and not expired."""
        # Check memory cache first
        if cache_key in self.cache['memory_cache']:
            cached_item = self.cache['memory_cache'][cache_key]
            if time.time() - cached_item['timestamp'] < self.cache['ttl']:
                return cached_item['data']
            else:
                del self.cache['memory_cache'][cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, data: Dict[str, Any]):
        """Cache result for future use."""
        self.cache['memory_cache'][cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        
        # Limit memory cache size
        if len(self.cache['memory_cache']) > 1000:
            # Remove oldest entries
            oldest_keys = sorted(
                self.cache['memory_cache'].keys(),
                key=lambda k: self.cache['memory_cache'][k]['timestamp']
            )[:100]
            for key in oldest_keys:
                del self.cache['memory_cache'][key]
    
    def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get aggregation statistics."""
        cache_hit_rate = self.cache_hits / self.total_queries if self.total_queries > 0 else 0.0
        success_rate = self.successful_aggregations / self.total_queries if self.total_queries > 0 else 0.0
        
        return {
            'total_queries': self.total_queries,
            'successful_aggregations': self.successful_aggregations,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': cache_hit_rate,
            'success_rate': success_rate,
            'active_sources': len([s for s in self.sources if s.enabled]),
            'total_sources': len(self.sources)
        }
    
    async def shutdown(self):
        """Gracefully shutdown the aggregator."""
        self.logger.info("Shutting down Information Aggregator...")
        # Clean up resources, close connections, etc.
        self.logger.info("Information Aggregator shutdown complete")