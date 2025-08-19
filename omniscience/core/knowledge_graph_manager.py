"""
Knowledge Graph Manager - Relationship Analysis and Graph Intelligence
=====================================================================

Manages knowledge graphs and relationship analysis using Kenny's existing
Memgraph infrastructure to provide deep contextual understanding.
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict, deque
import networkx as nx


@dataclass
class KnowledgeNode:
    """Represents a node in the knowledge graph."""
    id: str
    label: str
    node_type: str
    properties: Dict[str, Any]
    confidence: float = 1.0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class KnowledgeRelationship:
    """Represents a relationship between knowledge nodes."""
    source_id: str
    target_id: str
    relationship_type: str
    properties: Dict[str, Any]
    strength: float = 1.0
    confidence: float = 1.0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class GraphAnalysisResult:
    """Results from graph analysis."""
    query: str
    nodes_analyzed: int
    relationships_found: int
    key_concepts: List[str]
    relationship_patterns: Dict[str, int]
    confidence_distribution: Dict[str, float]
    insights: List[str]
    metadata: Dict[str, Any]


class KnowledgeGraphManager:
    """
    Knowledge Graph Manager for omniscience network.
    
    Integrates with Kenny's existing graph intelligence systems
    to provide sophisticated relationship analysis and pattern detection.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.logger = self._setup_logging()
        
        # Graph storage (in-memory for this implementation)
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.relationships: List[KnowledgeRelationship] = []
        self.graph = nx.MultiDiGraph()
        
        # Relationship patterns
        self.relationship_patterns = defaultdict(int)
        self.concept_clusters = {}
        
        # Performance tracking
        self.analysis_count = 0
        self.total_analysis_time = 0.0
        
        self.logger.info("Knowledge Graph Manager initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'max_analysis_depth': 5,
            'min_relationship_strength': 0.3,
            'clustering_threshold': 0.7,
            'pattern_detection_enabled': True,
            'memgraph_integration': True,
            'cache_analysis_results': True,
            'relationship_types': [
                'relates_to', 'causes', 'enables', 'requires', 
                'similar_to', 'opposite_of', 'part_of', 'instance_of'
            ],
            'node_types': [
                'concept', 'entity', 'process', 'attribute', 
                'event', 'location', 'time', 'person'
            ]
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        logger = logging.getLogger('kenny.omniscience.graph')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    async def analyze_relationships(self, query, aggregated_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze relationships in the knowledge graph for a given query.
        
        Args:
            query: KnowledgeQuery object
            aggregated_info: Information from the aggregator
            
        Returns:
            Dictionary containing relationship analysis results
        """
        start_time = time.time()
        self.analysis_count += 1
        
        self.logger.info(f"Analyzing relationships for query: {query.query[:100]}...")
        
        try:
            # Extract concepts from query and aggregated information
            concepts = await self._extract_concepts(query, aggregated_info)
            
            # Build/update knowledge graph
            await self._build_graph_from_concepts(concepts, aggregated_info)
            
            # Perform relationship analysis
            analysis_result = await self._perform_relationship_analysis(query.query, concepts)
            
            # Detect patterns
            patterns = await self._detect_relationship_patterns(concepts)
            
            # Generate insights
            insights = await self._generate_graph_insights(analysis_result, patterns)
            
            analysis_time = time.time() - start_time
            self.total_analysis_time += analysis_time
            
            result = {
                'analysis_result': analysis_result,
                'relationship_patterns': patterns,
                'insights': insights,
                'graph_statistics': self._get_graph_statistics(),
                'analysis_metadata': {
                    'processing_time': analysis_time,
                    'concepts_analyzed': len(concepts),
                    'version': '1.0.0'
                }
            }
            
            self.logger.info(f"Relationship analysis completed in {analysis_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in relationship analysis: {str(e)}")
            return {
                'error': str(e),
                'analysis_metadata': {
                    'processing_time': time.time() - start_time,
                    'success': False
                }
            }
    
    async def _extract_concepts(self, query, aggregated_info: Dict[str, Any]) -> List[str]:
        """Extract key concepts from query and aggregated information."""
        concepts = set()
        
        # Extract from query
        query_words = query.query.lower().split()
        # Simple concept extraction (in production, would use NLP)
        key_query_concepts = [word for word in query_words if len(word) > 3]
        concepts.update(key_query_concepts)
        
        # Extract from aggregated content
        for source_name, content in aggregated_info.get('aggregated_content', {}).items():
            if isinstance(content, dict):
                # Extract from content text
                if 'content' in content:
                    content_text = str(content['content']).lower()
                    content_words = content_text.split()
                    key_content_concepts = [word for word in content_words if len(word) > 4][:10]
                    concepts.update(key_content_concepts)
                
                # Extract from metadata
                if 'type' in content:
                    concepts.add(content['type'])
        
        # Add domain-specific concepts based on sources
        if 'kenny' in query.query.lower():
            concepts.update(['automation', 'screen_analysis', 'workflow', 'ai_system'])
        
        return list(concepts)[:50]  # Limit concepts for performance
    
    async def _build_graph_from_concepts(self, concepts: List[str], aggregated_info: Dict[str, Any]):
        """Build/update knowledge graph from extracted concepts."""
        # Create nodes for concepts
        for concept in concepts:
            node_id = f"concept_{concept}"
            if node_id not in self.nodes:
                node = KnowledgeNode(
                    id=node_id,
                    label=concept,
                    node_type='concept',
                    properties={'source': 'extracted_concept'},
                    confidence=0.8
                )
                self.nodes[node_id] = node
                self.graph.add_node(node_id, **node.properties)
        
        # Create relationships based on co-occurrence and context
        await self._create_relationships_from_context(concepts, aggregated_info)
    
    async def _create_relationships_from_context(self, concepts: List[str], aggregated_info: Dict[str, Any]):
        """Create relationships between concepts based on context."""
        # Co-occurrence relationships
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                if concept1 != concept2:
                    relationship = KnowledgeRelationship(
                        source_id=f"concept_{concept1}",
                        target_id=f"concept_{concept2}",
                        relationship_type='co_occurs_with',
                        properties={'context': 'query_analysis'},
                        strength=0.6,
                        confidence=0.7
                    )
                    self.relationships.append(relationship)
                    self.graph.add_edge(
                        relationship.source_id,
                        relationship.target_id,
                        relationship_type=relationship.relationship_type,
                        strength=relationship.strength
                    )
        
        # Domain-specific relationships
        await self._add_domain_relationships(concepts)
    
    async def _add_domain_relationships(self, concepts: List[str]):
        """Add domain-specific relationships."""
        domain_rules = {
            ('automation', 'workflow'): ('enables', 0.9),
            ('screen_analysis', 'automation'): ('supports', 0.8),
            ('ai_system', 'automation'): ('powers', 0.9),
            ('kenny', 'automation'): ('implements', 1.0),
            ('memory', 'learning'): ('enables', 0.8),
            ('analysis', 'insight'): ('generates', 0.9)
        }
        
        for concept1 in concepts:
            for concept2 in concepts:
                if concept1 != concept2:
                    for (rule_concept1, rule_concept2), (rel_type, strength) in domain_rules.items():
                        if (rule_concept1 in concept1.lower() and rule_concept2 in concept2.lower()) or \
                           (rule_concept2 in concept1.lower() and rule_concept1 in concept2.lower()):
                            relationship = KnowledgeRelationship(
                                source_id=f"concept_{concept1}",
                                target_id=f"concept_{concept2}",
                                relationship_type=rel_type,
                                properties={'source': 'domain_rules'},
                                strength=strength,
                                confidence=0.9
                            )
                            self.relationships.append(relationship)
                            self.graph.add_edge(
                                relationship.source_id,
                                relationship.target_id,
                                relationship_type=relationship.relationship_type,
                                strength=relationship.strength
                            )
    
    async def _perform_relationship_analysis(self, query: str, concepts: List[str]) -> GraphAnalysisResult:
        """Perform comprehensive relationship analysis."""
        # Analyze graph structure
        nodes_analyzed = len(self.graph.nodes())
        relationships_found = len(self.graph.edges())
        
        # Find key concepts (high centrality)
        if nodes_analyzed > 0:
            centrality = nx.degree_centrality(self.graph)
            key_concepts = sorted(centrality.keys(), key=lambda x: centrality[x], reverse=True)[:10]
            key_concepts = [concept.replace('concept_', '') for concept in key_concepts]
        else:
            key_concepts = concepts[:5]
        
        # Analyze relationship patterns
        relationship_patterns = defaultdict(int)
        for _, _, data in self.graph.edges(data=True):
            rel_type = data.get('relationship_type', 'unknown')
            relationship_patterns[rel_type] += 1
        
        # Calculate confidence distribution
        confidences = [rel.confidence for rel in self.relationships]
        confidence_distribution = {
            'high_confidence': len([c for c in confidences if c >= 0.8]),
            'medium_confidence': len([c for c in confidences if 0.5 <= c < 0.8]),
            'low_confidence': len([c for c in confidences if c < 0.5])
        }
        
        # Generate insights
        insights = self._generate_analysis_insights(key_concepts, relationship_patterns)
        
        return GraphAnalysisResult(
            query=query,
            nodes_analyzed=nodes_analyzed,
            relationships_found=relationships_found,
            key_concepts=key_concepts,
            relationship_patterns=dict(relationship_patterns),
            confidence_distribution=confidence_distribution,
            insights=insights,
            metadata={
                'analysis_timestamp': time.time(),
                'graph_complexity': self._calculate_graph_complexity()
            }
        )
    
    async def _detect_relationship_patterns(self, concepts: List[str]) -> Dict[str, Any]:
        """Detect patterns in relationships."""
        patterns = {
            'common_relationship_types': {},
            'concept_clusters': {},
            'strong_relationships': [],
            'weak_relationships': [],
            'pattern_insights': []
        }
        
        # Analyze relationship type frequency
        rel_type_counts = defaultdict(int)
        for rel in self.relationships:
            rel_type_counts[rel.relationship_type] += 1
        patterns['common_relationship_types'] = dict(rel_type_counts)
        
        # Find strong and weak relationships
        for rel in self.relationships:
            if rel.strength >= 0.8:
                patterns['strong_relationships'].append({
                    'source': rel.source_id.replace('concept_', ''),
                    'target': rel.target_id.replace('concept_', ''),
                    'type': rel.relationship_type,
                    'strength': rel.strength
                })
            elif rel.strength < 0.5:
                patterns['weak_relationships'].append({
                    'source': rel.source_id.replace('concept_', ''),
                    'target': rel.target_id.replace('concept_', ''),
                    'type': rel.relationship_type,
                    'strength': rel.strength
                })
        
        # Generate pattern insights
        patterns['pattern_insights'] = [
            f"Found {len(patterns['strong_relationships'])} strong relationships",
            f"Most common relationship type: {max(rel_type_counts.items(), key=lambda x: x[1])[0] if rel_type_counts else 'none'}",
            f"Graph has {len(concepts)} main concepts with {len(self.relationships)} total relationships"
        ]
        
        return patterns
    
    async def _generate_graph_insights(self, analysis_result: GraphAnalysisResult, patterns: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from graph analysis."""
        insights = []
        
        # Complexity insights
        if analysis_result.nodes_analyzed > 20:
            insights.append("Complex knowledge domain detected - consider focused analysis")
        elif analysis_result.nodes_analyzed < 5:
            insights.append("Limited knowledge connections - may need broader information gathering")
        
        # Relationship insights
        if analysis_result.relationships_found > analysis_result.nodes_analyzed * 2:
            insights.append("Highly interconnected concepts - strong domain coherence")
        else:
            insights.append("Sparse relationships - concepts may be loosely related")
        
        # Key concept insights
        if analysis_result.key_concepts:
            top_concept = analysis_result.key_concepts[0]
            insights.append(f"Primary focus concept identified: '{top_concept}'")
        
        # Pattern insights
        if patterns.get('strong_relationships'):
            insights.append(f"Found {len(patterns['strong_relationships'])} high-confidence relationships")
        
        # Confidence insights
        high_conf = analysis_result.confidence_distribution.get('high_confidence', 0)
        total_rels = sum(analysis_result.confidence_distribution.values())
        if total_rels > 0:
            conf_ratio = high_conf / total_rels
            if conf_ratio > 0.7:
                insights.append("High confidence in relationship analysis - reliable knowledge base")
            elif conf_ratio < 0.3:
                insights.append("Low confidence relationships - may need additional validation")
        
        return insights
    
    def _generate_analysis_insights(self, key_concepts: List[str], relationship_patterns: Dict[str, int]) -> List[str]:
        """Generate insights from analysis results."""
        insights = []
        
        if key_concepts:
            insights.append(f"Central concepts: {', '.join(key_concepts[:3])}")
        
        if relationship_patterns:
            most_common = max(relationship_patterns.items(), key=lambda x: x[1])
            insights.append(f"Dominant relationship type: {most_common[0]} ({most_common[1]} instances)")
        
        total_relationships = sum(relationship_patterns.values())
        if total_relationships > 10:
            insights.append("Rich relationship network detected")
        elif total_relationships < 3:
            insights.append("Sparse relationship network - limited connections")
        
        return insights
    
    def _calculate_graph_complexity(self) -> float:
        """Calculate a complexity score for the graph."""
        if not self.graph.nodes():
            return 0.0
        
        nodes = len(self.graph.nodes())
        edges = len(self.graph.edges())
        
        # Simple complexity metric
        complexity = (edges / max(nodes, 1)) if nodes > 0 else 0
        return min(complexity, 10.0)  # Cap at 10
    
    def _get_graph_statistics(self) -> Dict[str, Any]:
        """Get current graph statistics."""
        return {
            'total_nodes': len(self.nodes),
            'total_relationships': len(self.relationships),
            'graph_nodes': len(self.graph.nodes()),
            'graph_edges': len(self.graph.edges()),
            'complexity_score': self._calculate_graph_complexity(),
            'average_analysis_time': (self.total_analysis_time / self.analysis_count 
                                    if self.analysis_count > 0 else 0.0),
            'total_analyses': self.analysis_count
        }
    
    def get_knowledge_subgraph(self, concepts: List[str], max_depth: int = 2) -> Dict[str, Any]:
        """Extract a subgraph around specific concepts."""
        subgraph_nodes = set()
        subgraph_edges = []
        
        # Start with target concepts
        for concept in concepts:
            concept_id = f"concept_{concept}"
            if concept_id in self.graph.nodes():
                subgraph_nodes.add(concept_id)
                
                # Add neighbors up to max_depth
                for depth in range(max_depth):
                    current_nodes = list(subgraph_nodes)
                    for node in current_nodes:
                        neighbors = list(self.graph.neighbors(node))
                        subgraph_nodes.update(neighbors)
        
        # Extract edges within subgraph
        for source, target, data in self.graph.edges(data=True):
            if source in subgraph_nodes and target in subgraph_nodes:
                subgraph_edges.append({
                    'source': source.replace('concept_', ''),
                    'target': target.replace('concept_', ''),
                    'relationship_type': data.get('relationship_type', 'unknown'),
                    'strength': data.get('strength', 0.5)
                })
        
        return {
            'nodes': [node.replace('concept_', '') for node in subgraph_nodes],
            'edges': subgraph_edges,
            'subgraph_size': len(subgraph_nodes),
            'edge_count': len(subgraph_edges)
        }
    
    async def shutdown(self):
        """Gracefully shutdown the graph manager."""
        self.logger.info("Shutting down Knowledge Graph Manager...")
        # Save graph state, close connections, etc.
        self.logger.info("Knowledge Graph Manager shutdown complete")