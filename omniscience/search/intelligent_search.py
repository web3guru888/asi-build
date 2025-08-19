"""
Intelligent Search System - Advanced Knowledge Retrieval
=======================================================

Sophisticated search and retrieval system that combines semantic search,
contextual understanding, and multiple search strategies to find relevant
information across all knowledge sources.
"""

import asyncio
import logging
import time
import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import difflib
import hashlib


@dataclass
class SearchQuery:
    """Represents a search query with metadata."""
    query: str
    search_type: str = 'comprehensive'  # 'semantic', 'keyword', 'fuzzy', 'comprehensive'
    filters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    max_results: int = 50
    confidence_threshold: float = 0.3
    
    
@dataclass
class SearchResult:
    """Represents a single search result."""
    content: str
    source: str
    relevance_score: float
    confidence: float
    metadata: Dict[str, Any]
    highlighted_text: str = ""
    
    
@dataclass
class SearchResponse:
    """Complete search response."""
    query: SearchQuery
    results: List[SearchResult]
    total_results: int
    search_time: float
    search_strategies_used: List[str]
    metadata: Dict[str, Any]


class IntelligentSearch:
    """
    Advanced intelligent search system for the omniscience network.
    
    Provides multiple search strategies:
    - Semantic search using embeddings and similarity
    - Fuzzy matching for approximate queries
    - Contextual search leveraging domain knowledge
    - Pattern-based search for structured queries
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.logger = self._setup_logging()
        
        # Search indices and caches
        self.keyword_index = defaultdict(set)
        self.semantic_cache = {}
        self.search_history = []
        
        # Performance tracking
        self.total_searches = 0
        self.total_search_time = 0.0
        self.cache_hits = 0
        
        # Initialize search strategies
        self._initialize_search_strategies()
        
        self.logger.info("Intelligent Search System initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'semantic_search_enabled': True,
            'fuzzy_search_threshold': 0.6,
            'keyword_boost_factor': 1.5,
            'context_expansion_enabled': True,
            'max_semantic_cache_size': 10000,
            'search_timeout': 15.0,
            'parallel_search_strategies': True,
            'result_ranking': {
                'relevance_weight': 0.4,
                'confidence_weight': 0.3,
                'recency_weight': 0.2,
                'source_authority_weight': 0.1
            },
            'search_strategies': [
                'keyword_search',
                'semantic_search', 
                'fuzzy_search',
                'pattern_search',
                'contextual_search'
            ]
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        logger = logging.getLogger('kenny.omniscience.search')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_search_strategies(self):
        """Initialize search strategy configurations."""
        self.strategies = {
            'keyword_search': {
                'enabled': True,
                'weight': 1.0,
                'preprocessing': ['lowercase', 'tokenize', 'stem']
            },
            'semantic_search': {
                'enabled': self.config.get('semantic_search_enabled', True),
                'weight': 1.2,
                'similarity_threshold': 0.7
            },
            'fuzzy_search': {
                'enabled': True,
                'weight': 0.8,
                'threshold': self.config.get('fuzzy_search_threshold', 0.6)
            },
            'pattern_search': {
                'enabled': True,
                'weight': 1.1,
                'patterns': [
                    r'how to (.*)',
                    r'what is (.*)',
                    r'where can I (.*)',
                    r'when does (.*)'
                ]
            },
            'contextual_search': {
                'enabled': self.config.get('context_expansion_enabled', True),
                'weight': 1.3,
                'context_expansion_factor': 2
            }
        }
    
    async def search_comprehensive(self, query, aggregated_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive search using multiple strategies.
        
        Args:
            query: KnowledgeQuery object
            aggregated_info: Information from aggregation phase
            
        Returns:
            Dictionary containing comprehensive search results
        """
        start_time = time.time()
        self.total_searches += 1
        
        self.logger.info(f"Performing comprehensive search for: {query.query[:100]}...")
        
        try:
            # Create search query object
            search_query = SearchQuery(
                query=query.query,
                search_type='comprehensive',
                context=getattr(query, 'context', {}),
                max_results=self.config.get('max_results', 50)
            )
            
            # Check cache first
            cache_key = self._generate_search_cache_key(search_query)
            cached_result = self._get_from_search_cache(cache_key)
            if cached_result:
                self.cache_hits += 1
                self.logger.info("Search cache hit - returning cached results")
                return cached_result
            
            # Prepare search corpus from aggregated information
            search_corpus = self._prepare_search_corpus(aggregated_info)
            
            # Execute search strategies in parallel
            if self.config.get('parallel_search_strategies', True):
                search_results = await self._execute_parallel_search(search_query, search_corpus)
            else:
                search_results = await self._execute_sequential_search(search_query, search_corpus)
            
            # Merge and rank results
            merged_results = self._merge_search_results(search_results)
            ranked_results = self._rank_search_results(merged_results, search_query)
            
            # Apply filters and limits
            filtered_results = self._filter_and_limit_results(ranked_results, search_query)
            
            search_time = time.time() - start_time
            self.total_search_time += search_time
            
            # Create response
            response = SearchResponse(
                query=search_query,
                results=filtered_results,
                total_results=len(filtered_results),
                search_time=search_time,
                search_strategies_used=list(search_results.keys()),
                metadata={
                    'corpus_size': len(search_corpus),
                    'strategies_executed': len(search_results),
                    'cache_hit': False
                }
            )
            
            # Cache the result
            self._cache_search_result(cache_key, response)
            
            # Convert to dictionary format
            result_dict = {
                'search_results': [self._search_result_to_dict(r) for r in response.results],
                'total_results': response.total_results,
                'search_time': response.search_time,
                'strategies_used': response.search_strategies_used,
                'query_analysis': self._analyze_query(search_query),
                'search_metadata': response.metadata
            }
            
            self.logger.info(f"Search completed in {search_time:.2f}s with {len(filtered_results)} results")
            return result_dict
            
        except Exception as e:
            search_time = time.time() - start_time
            self.logger.error(f"Error in comprehensive search: {str(e)}")
            return {
                'error': str(e),
                'search_time': search_time,
                'search_metadata': {'error': True}
            }
    
    def _prepare_search_corpus(self, aggregated_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare search corpus from aggregated information."""
        corpus = []
        
        for source_name, content in aggregated_info.get('aggregated_content', {}).items():
            if isinstance(content, dict):
                # Extract searchable content
                searchable_text = ""
                
                if 'content' in content:
                    searchable_text += str(content['content'])
                
                if 'type' in content:
                    searchable_text += f" {content['type']}"
                
                if 'metadata' in content:
                    metadata = content['metadata']
                    if isinstance(metadata, dict):
                        for key, value in metadata.items():
                            searchable_text += f" {key}:{value}"
                
                corpus_item = {
                    'text': searchable_text,
                    'source': source_name,
                    'original_content': content,
                    'confidence': content.get('confidence', 0.5),
                    'metadata': content.get('metadata', {})
                }
                corpus.append(corpus_item)
        
        return corpus
    
    async def _execute_parallel_search(self, search_query: SearchQuery, corpus: List[Dict[str, Any]]) -> Dict[str, List[SearchResult]]:
        """Execute multiple search strategies in parallel."""
        tasks = []
        enabled_strategies = [name for name, config in self.strategies.items() if config['enabled']]
        
        for strategy_name in enabled_strategies:
            task = self._execute_search_strategy(strategy_name, search_query, corpus)
            tasks.append((strategy_name, task))
        
        results = {}
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for i, (strategy_name, _) in enumerate(tasks):
            result = completed_tasks[i]
            if isinstance(result, Exception):
                self.logger.warning(f"Strategy {strategy_name} failed: {str(result)}")
                results[strategy_name] = []
            else:
                results[strategy_name] = result
        
        return results
    
    async def _execute_sequential_search(self, search_query: SearchQuery, corpus: List[Dict[str, Any]]) -> Dict[str, List[SearchResult]]:
        """Execute search strategies sequentially."""
        results = {}
        enabled_strategies = [name for name, config in self.strategies.items() if config['enabled']]
        
        for strategy_name in enabled_strategies:
            try:
                strategy_results = await self._execute_search_strategy(strategy_name, search_query, corpus)
                results[strategy_name] = strategy_results
            except Exception as e:
                self.logger.warning(f"Strategy {strategy_name} failed: {str(e)}")
                results[strategy_name] = []
        
        return results
    
    async def _execute_search_strategy(self, strategy_name: str, search_query: SearchQuery, corpus: List[Dict[str, Any]]) -> List[SearchResult]:
        """Execute a specific search strategy."""
        if strategy_name == 'keyword_search':
            return await self._keyword_search(search_query, corpus)
        elif strategy_name == 'semantic_search':
            return await self._semantic_search(search_query, corpus)
        elif strategy_name == 'fuzzy_search':
            return await self._fuzzy_search(search_query, corpus)
        elif strategy_name == 'pattern_search':
            return await self._pattern_search(search_query, corpus)
        elif strategy_name == 'contextual_search':
            return await self._contextual_search(search_query, corpus)
        else:
            return []
    
    async def _keyword_search(self, search_query: SearchQuery, corpus: List[Dict[str, Any]]) -> List[SearchResult]:
        """Perform keyword-based search."""
        results = []
        query_terms = self._extract_keywords(search_query.query)
        
        for item in corpus:
            text = item['text'].lower()
            matches = 0
            total_terms = len(query_terms)
            highlighted_spans = []
            
            for term in query_terms:
                if term.lower() in text:
                    matches += 1
                    # Find all occurrences for highlighting
                    start = 0
                    while True:
                        pos = text.find(term.lower(), start)
                        if pos == -1:
                            break
                        highlighted_spans.append((pos, pos + len(term)))
                        start = pos + 1
            
            if matches > 0:
                relevance = matches / total_terms
                confidence = item['confidence'] * relevance
                
                # Generate highlighted text
                highlighted_text = self._highlight_text(item['text'], highlighted_spans)
                
                result = SearchResult(
                    content=item['text'][:500],  # Truncate for display
                    source=item['source'],
                    relevance_score=relevance,
                    confidence=confidence,
                    metadata={
                        'strategy': 'keyword_search',
                        'matches': matches,
                        'total_terms': total_terms,
                        **item['metadata']
                    },
                    highlighted_text=highlighted_text
                )
                results.append(result)
        
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)[:20]
    
    async def _semantic_search(self, search_query: SearchQuery, corpus: List[Dict[str, Any]]) -> List[SearchResult]:
        """Perform semantic search (simplified implementation)."""
        results = []
        
        # For this implementation, we'll use a simplified semantic matching
        # In production, this would use embeddings and vector similarity
        
        query_concepts = self._extract_semantic_concepts(search_query.query)
        
        for item in corpus:
            text_concepts = self._extract_semantic_concepts(item['text'])
            
            # Calculate semantic similarity
            similarity = self._calculate_semantic_similarity(query_concepts, text_concepts)
            
            if similarity >= self.strategies['semantic_search']['similarity_threshold']:
                result = SearchResult(
                    content=item['text'][:500],
                    source=item['source'],
                    relevance_score=similarity,
                    confidence=item['confidence'] * similarity,
                    metadata={
                        'strategy': 'semantic_search',
                        'similarity': similarity,
                        'query_concepts': query_concepts,
                        'text_concepts': text_concepts,
                        **item['metadata']
                    }
                )
                results.append(result)
        
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)[:15]
    
    async def _fuzzy_search(self, search_query: SearchQuery, corpus: List[Dict[str, Any]]) -> List[SearchResult]:
        """Perform fuzzy matching search."""
        results = []
        query_lower = search_query.query.lower()
        threshold = self.strategies['fuzzy_search']['threshold']
        
        for item in corpus:
            text_lower = item['text'].lower()
            
            # Use difflib for fuzzy matching
            similarity = difflib.SequenceMatcher(None, query_lower, text_lower).ratio()
            
            if similarity >= threshold:
                result = SearchResult(
                    content=item['text'][:500],
                    source=item['source'],
                    relevance_score=similarity,
                    confidence=item['confidence'] * similarity,
                    metadata={
                        'strategy': 'fuzzy_search',
                        'similarity': similarity,
                        **item['metadata']
                    }
                )
                results.append(result)
        
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)[:10]
    
    async def _pattern_search(self, search_query: SearchQuery, corpus: List[Dict[str, Any]]) -> List[SearchResult]:
        """Perform pattern-based search."""
        results = []
        patterns = self.strategies['pattern_search']['patterns']
        
        # Check if query matches any patterns
        matched_patterns = []
        for pattern in patterns:
            match = re.search(pattern, search_query.query, re.IGNORECASE)
            if match:
                matched_patterns.append((pattern, match.groups()))
        
        if not matched_patterns:
            return results
        
        # Search corpus for pattern-relevant content
        for item in corpus:
            relevance = 0.0
            pattern_matches = []
            
            for pattern, groups in matched_patterns:
                # Look for extracted terms in the content
                for group in groups:
                    if group and group.lower() in item['text'].lower():
                        relevance += 0.3
                        pattern_matches.append(group)
            
            if relevance > 0:
                result = SearchResult(
                    content=item['text'][:500],
                    source=item['source'],
                    relevance_score=min(relevance, 1.0),
                    confidence=item['confidence'] * relevance,
                    metadata={
                        'strategy': 'pattern_search',
                        'matched_patterns': [p for p, _ in matched_patterns],
                        'pattern_matches': pattern_matches,
                        **item['metadata']
                    }
                )
                results.append(result)
        
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)[:10]
    
    async def _contextual_search(self, search_query: SearchQuery, corpus: List[Dict[str, Any]]) -> List[SearchResult]:
        """Perform context-aware search."""
        results = []
        
        # Expand query with context
        expanded_terms = self._expand_query_with_context(search_query)
        
        for item in corpus:
            relevance = 0.0
            context_matches = []
            
            # Check for expanded terms
            for term, weight in expanded_terms.items():
                if term.lower() in item['text'].lower():
                    relevance += weight
                    context_matches.append(term)
            
            # Boost based on source authority
            source_boost = self._get_source_authority_boost(item['source'])
            relevance *= source_boost
            
            if relevance > 0:
                result = SearchResult(
                    content=item['text'][:500],
                    source=item['source'],
                    relevance_score=min(relevance, 1.0),
                    confidence=item['confidence'] * relevance,
                    metadata={
                        'strategy': 'contextual_search',
                        'context_matches': context_matches,
                        'source_authority_boost': source_boost,
                        **item['metadata']
                    }
                )
                results.append(result)
        
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)[:15]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        return keywords[:10]  # Limit keywords
    
    def _extract_semantic_concepts(self, text: str) -> List[str]:
        """Extract semantic concepts from text (simplified)."""
        # In production, this would use NLP libraries like spaCy or transformers
        concepts = []
        
        # Domain-specific concept extraction
        domain_concepts = {
            'automation': ['automation', 'workflow', 'process', 'task'],
            'technology': ['system', 'software', 'application', 'program'],
            'analysis': ['analysis', 'data', 'information', 'insight'],
            'kenny': ['kenny', 'screen', 'monitor', 'ai']
        }
        
        text_lower = text.lower()
        for domain, terms in domain_concepts.items():
            for term in terms:
                if term in text_lower:
                    concepts.append(domain)
                    break
        
        # Add significant words as concepts
        words = self._extract_keywords(text)
        concepts.extend(words[:5])
        
        return list(set(concepts))
    
    def _calculate_semantic_similarity(self, concepts1: List[str], concepts2: List[str]) -> float:
        """Calculate semantic similarity between concept lists."""
        if not concepts1 or not concepts2:
            return 0.0
        
        # Simple Jaccard similarity
        set1 = set(concepts1)
        set2 = set(concepts2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _expand_query_with_context(self, search_query: SearchQuery) -> Dict[str, float]:
        """Expand query terms with contextual information."""
        expanded = {}
        
        # Add original query terms with high weight
        keywords = self._extract_keywords(search_query.query)
        for keyword in keywords:
            expanded[keyword] = 1.0
        
        # Add context-based terms
        context = search_query.context
        if 'domain' in context:
            domain = context['domain']
            if domain == 'kenny':
                expanded.update({
                    'automation': 0.8,
                    'screen': 0.7,
                    'workflow': 0.6
                })
            elif domain == 'technical':
                expanded.update({
                    'system': 0.6,
                    'code': 0.5,
                    'api': 0.5
                })
        
        return expanded
    
    def _get_source_authority_boost(self, source: str) -> float:
        """Get authority boost factor for a source."""
        authority_scores = {
            'kenny_memory_analytics': 1.2,
            'kenny_graph_intelligence': 1.2,
            'kenny_screen_analysis': 1.1,
            'kenny_workflow_patterns': 1.1,
            'kenny_logs': 1.0,
            'kenny_documentation': 1.0,
            'wikipedia_api': 0.9,
            'technical_documentation': 0.8
        }
        return authority_scores.get(source, 0.7)
    
    def _highlight_text(self, text: str, spans: List[Tuple[int, int]]) -> str:
        """Add highlighting to text spans."""
        if not spans:
            return text[:200] + "..." if len(text) > 200 else text
        
        # Sort spans by position
        spans.sort()
        
        # Add highlighting markers
        highlighted = ""
        last_end = 0
        
        for start, end in spans[:5]:  # Limit highlights
            highlighted += text[last_end:start]
            highlighted += f"**{text[start:end]}**"
            last_end = end
        
        highlighted += text[last_end:last_end+200]  # Add some context
        
        return highlighted
    
    def _merge_search_results(self, strategy_results: Dict[str, List[SearchResult]]) -> List[SearchResult]:
        """Merge results from different search strategies."""
        all_results = []
        seen_content = set()
        
        for strategy, results in strategy_results.items():
            strategy_weight = self.strategies[strategy]['weight']
            
            for result in results:
                # Check for duplicates based on content similarity
                content_hash = hashlib.md5(result.content.encode()).hexdigest()
                if content_hash not in seen_content:
                    # Apply strategy weight
                    result.relevance_score *= strategy_weight
                    all_results.append(result)
                    seen_content.add(content_hash)
        
        return all_results
    
    def _rank_search_results(self, results: List[SearchResult], search_query: SearchQuery) -> List[SearchResult]:
        """Rank search results using multiple factors."""
        weights = self.config['result_ranking']
        
        for result in results:
            # Calculate composite score
            score = (
                result.relevance_score * weights['relevance_weight'] +
                result.confidence * weights['confidence_weight'] +
                self._calculate_recency_score(result) * weights['recency_weight'] +
                self._get_source_authority_boost(result.source) * weights['source_authority_weight']
            )
            result.relevance_score = score
        
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)
    
    def _calculate_recency_score(self, result: SearchResult) -> float:
        """Calculate recency score for a result."""
        # Simple recency calculation based on metadata timestamp
        if 'timestamp' in result.metadata:
            timestamp = result.metadata['timestamp']
            age_hours = (time.time() - timestamp) / 3600
            # Exponential decay with 24-hour half-life
            return 2 ** (-age_hours / 24)
        return 0.5  # Default score for unknown age
    
    def _filter_and_limit_results(self, results: List[SearchResult], search_query: SearchQuery) -> List[SearchResult]:
        """Apply filters and limits to search results."""
        filtered = []
        
        for result in results:
            # Apply confidence threshold
            if result.confidence >= search_query.confidence_threshold:
                filtered.append(result)
        
        # Apply limit
        return filtered[:search_query.max_results]
    
    def _analyze_query(self, search_query: SearchQuery) -> Dict[str, Any]:
        """Analyze the search query and provide insights."""
        return {
            'query_length': len(search_query.query),
            'keywords_extracted': len(self._extract_keywords(search_query.query)),
            'query_type': self._classify_query_type(search_query.query),
            'complexity': self._assess_query_complexity(search_query.query)
        }
    
    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query."""
        query_lower = query.lower()
        
        if query_lower.startswith(('how', 'how to')):
            return 'procedural'
        elif query_lower.startswith(('what', 'what is')):
            return 'definitional'
        elif query_lower.startswith(('where', 'when')):
            return 'factual'
        elif query_lower.startswith(('why')):
            return 'causal'
        elif '?' in query:
            return 'interrogative'
        else:
            return 'descriptive'
    
    def _assess_query_complexity(self, query: str) -> str:
        """Assess query complexity."""
        word_count = len(query.split())
        
        if word_count <= 3:
            return 'simple'
        elif word_count <= 8:
            return 'moderate'
        else:
            return 'complex'
    
    def _search_result_to_dict(self, result: SearchResult) -> Dict[str, Any]:
        """Convert SearchResult to dictionary."""
        return {
            'content': result.content,
            'source': result.source,
            'relevance_score': result.relevance_score,
            'confidence': result.confidence,
            'highlighted_text': result.highlighted_text,
            'metadata': result.metadata
        }
    
    def _generate_search_cache_key(self, search_query: SearchQuery) -> str:
        """Generate cache key for search query."""
        key_data = f"{search_query.query}_{search_query.search_type}_{search_query.max_results}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_from_search_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from search cache."""
        if cache_key in self.semantic_cache:
            cached_item = self.semantic_cache[cache_key]
            if time.time() - cached_item['timestamp'] < 1800:  # 30 minutes TTL
                return cached_item['data']
            else:
                del self.semantic_cache[cache_key]
        return None
    
    def _cache_search_result(self, cache_key: str, response: SearchResponse):
        """Cache search result."""
        # Convert response to cacheable format
        cacheable_data = {
            'search_results': [self._search_result_to_dict(r) for r in response.results],
            'total_results': response.total_results,
            'search_time': response.search_time,
            'strategies_used': response.search_strategies_used,
            'search_metadata': response.metadata
        }
        
        self.semantic_cache[cache_key] = {
            'data': cacheable_data,
            'timestamp': time.time()
        }
        
        # Limit cache size
        if len(self.semantic_cache) > self.config.get('max_semantic_cache_size', 10000):
            # Remove oldest entries
            oldest_keys = sorted(
                self.semantic_cache.keys(),
                key=lambda k: self.semantic_cache[k]['timestamp']
            )[:1000]
            for key in oldest_keys:
                del self.semantic_cache[key]
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search performance statistics."""
        avg_search_time = (self.total_search_time / self.total_searches 
                          if self.total_searches > 0 else 0.0)
        cache_hit_rate = self.cache_hits / self.total_searches if self.total_searches > 0 else 0.0
        
        return {
            'total_searches': self.total_searches,
            'total_search_time': self.total_search_time,
            'average_search_time': avg_search_time,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': cache_hit_rate,
            'cache_size': len(self.semantic_cache),
            'enabled_strategies': [name for name, config in self.strategies.items() if config['enabled']],
            'strategy_count': len([s for s in self.strategies.values() if s['enabled']])
        }
    
    async def shutdown(self):
        """Gracefully shutdown the search system."""
        self.logger.info("Shutting down Intelligent Search System...")
        # Clear caches, close connections, etc.
        self.semantic_cache.clear()
        self.logger.info("Intelligent Search System shutdown complete")