"""
Knowledge Graph Construction from Text.

This module builds knowledge graphs from natural language text by extracting
entities, relations, and logical structures, creating a comprehensive
semantic representation of the knowledge.
"""

import asyncio
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np

from ..core.bridge import TranslationResult
from ..core.logic_systems import LogicFormalism


class NodeType(Enum):
    """Types of nodes in the knowledge graph."""

    ENTITY = "entity"
    CONCEPT = "concept"
    EVENT = "event"
    PROPERTY = "property"
    RELATION = "relation"
    LOGICAL_EXPRESSION = "logical_expression"


class EdgeType(Enum):
    """Types of edges in the knowledge graph."""

    IS_A = "is_a"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    CAUSES = "causes"
    TEMPORAL = "temporal"
    SIMILAR_TO = "similar_to"
    IMPLIES = "implies"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"


@dataclass
class KnowledgeNode:
    """Represents a node in the knowledge graph."""

    node_id: str
    node_type: NodeType
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_texts: List[str] = field(default_factory=list)
    logical_forms: List[str] = field(default_factory=list)
    embeddings: Optional[np.ndarray] = None
    frequency: int = 1

    def add_source(self, text: str):
        """Add a source text for this node."""
        if text not in self.source_texts:
            self.source_texts.append(text)
            self.frequency += 1


@dataclass
class KnowledgeEdge:
    """Represents an edge in the knowledge graph."""

    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    strength: float = 1.0
    source_texts: List[str] = field(default_factory=list)
    logical_forms: List[str] = field(default_factory=list)
    frequency: int = 1

    def add_evidence(self, text: str, logical_form: str = None):
        """Add evidence for this edge."""
        if text not in self.source_texts:
            self.source_texts.append(text)
            self.frequency += 1

        if logical_form and logical_form not in self.logical_forms:
            self.logical_forms.append(logical_form)


@dataclass
class KnowledgeGraph:
    """Complete knowledge graph structure."""

    graph_id: str
    nodes: Dict[str, KnowledgeNode]
    edges: Dict[str, KnowledgeEdge]
    metadata: Dict[str, Any]
    statistics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize the NetworkX graph."""
        self.nx_graph = nx.MultiDiGraph()
        self._build_nx_graph()

    def _build_nx_graph(self):
        """Build NetworkX graph from nodes and edges."""
        # Add nodes
        for node_id, node in self.nodes.items():
            self.nx_graph.add_node(
                node_id,
                type=node.node_type.value,
                label=node.label,
                confidence=node.confidence,
                properties=node.properties,
            )

        # Add edges
        for edge_id, edge in self.edges.items():
            self.nx_graph.add_edge(
                edge.source_id,
                edge.target_id,
                key=edge_id,
                type=edge.edge_type.value,
                label=edge.label,
                confidence=edge.confidence,
                strength=edge.strength,
                properties=edge.properties,
            )


class KnowledgeGraphBuilder:
    """
    Knowledge Graph Builder for constructing graphs from text.

    This class processes natural language texts and their logical
    representations to build comprehensive knowledge graphs.
    """

    def __init__(self):
        """Initialize the knowledge graph builder."""
        self.logger = logging.getLogger(__name__)

        # Graph storage
        self.graphs: Dict[str, KnowledgeGraph] = {}

        # Entity and relation extractors
        self.entity_patterns = self._init_entity_patterns()
        self.relation_patterns = self._init_relation_patterns()

        # Statistics
        self.stats = {"graphs_built": 0, "total_nodes": 0, "total_edges": 0, "processing_time": 0.0}

    def _init_entity_patterns(self) -> List[Dict[str, Any]]:
        """Initialize patterns for entity extraction."""
        return [
            {
                "pattern": r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
                "type": NodeType.ENTITY,
                "description": "Proper nouns",
            },
            {
                "pattern": r"\b(all|some|many|few|most)\s+([a-z]+)\b",
                "type": NodeType.CONCEPT,
                "description": "Quantified concepts",
            },
            {
                "pattern": r"\b([a-z]+(?:ing|ed|s))\b",
                "type": NodeType.EVENT,
                "description": "Actions and events",
            },
        ]

    def _init_relation_patterns(self) -> List[Dict[str, Any]]:
        """Initialize patterns for relation extraction."""
        return [
            {
                "pattern": r"(.+?)\s+(?:is|are)\s+(?:a|an)?\s*(.+)",
                "relation": EdgeType.IS_A,
                "description": "IS-A relations",
            },
            {
                "pattern": r"(.+?)\s+(?:causes|leads to|results in)\s+(.+)",
                "relation": EdgeType.CAUSES,
                "description": "Causal relations",
            },
            {
                "pattern": r"(.+?)\s+(?:is part of|belongs to)\s+(.+)",
                "relation": EdgeType.PART_OF,
                "description": "Part-of relations",
            },
            {
                "pattern": r"(.+?)\s+(?:is similar to|resembles)\s+(.+)",
                "relation": EdgeType.SIMILAR_TO,
                "description": "Similarity relations",
            },
            {
                "pattern": r"if\s+(.+?),?\s+then\s+(.+)",
                "relation": EdgeType.IMPLIES,
                "description": "Implication relations",
            },
        ]

    async def build_graph(
        self,
        translation_results: List[TranslationResult],
        formalism: LogicFormalism,
        graph_id: Optional[str] = None,
    ) -> KnowledgeGraph:
        """
        Build knowledge graph from translation results.

        Args:
            translation_results: List of NL-Logic translation results
            formalism: Logic formalism used
            graph_id: Optional graph identifier

        Returns:
            Constructed knowledge graph
        """
        import time

        start_time = time.time()

        if not graph_id:
            graph_id = f"kg_{int(start_time)}"

        try:
            # Initialize graph components
            nodes = {}
            edges = {}

            # Process each translation result
            for result in translation_results:
                # Extract nodes and edges from natural language
                nl_nodes, nl_edges = await self._extract_from_natural_language(result.source_text)

                # Extract nodes and edges from logical representation
                logic_nodes, logic_edges = await self._extract_from_logical_form(
                    result.target_representation, formalism
                )

                # Merge nodes
                nodes = self._merge_nodes(nodes, nl_nodes, result.source_text)
                nodes = self._merge_nodes(nodes, logic_nodes, result.source_text)

                # Merge edges
                edges = self._merge_edges(
                    edges, nl_edges, result.source_text, result.target_representation
                )
                edges = self._merge_edges(
                    edges, logic_edges, result.source_text, result.target_representation
                )

            # Perform graph enrichment
            nodes, edges = await self._enrich_graph(nodes, edges)

            # Calculate statistics
            statistics = self._calculate_graph_statistics(nodes, edges)

            # Create knowledge graph
            knowledge_graph = KnowledgeGraph(
                graph_id=graph_id,
                nodes=nodes,
                edges=edges,
                metadata={
                    "formalism": formalism.value,
                    "source_count": len(translation_results),
                    "construction_time": time.time() - start_time,
                    "builder_version": "1.0",
                },
                statistics=statistics,
            )

            # Store graph
            self.graphs[graph_id] = knowledge_graph

            # Update global statistics
            self.stats["graphs_built"] += 1
            self.stats["total_nodes"] += len(nodes)
            self.stats["total_edges"] += len(edges)
            self.stats["processing_time"] += time.time() - start_time

            self.logger.info(
                f"Built knowledge graph {graph_id} with {len(nodes)} nodes and {len(edges)} edges"
            )
            return knowledge_graph

        except Exception as e:
            self.logger.error(f"Error building knowledge graph: {str(e)}")
            raise

    async def _extract_from_natural_language(
        self, text: str
    ) -> Tuple[Dict[str, KnowledgeNode], Dict[str, KnowledgeEdge]]:
        """Extract nodes and edges from natural language text."""
        nodes = {}
        edges = {}

        # Extract entities using patterns
        import re

        for pattern_info in self.entity_patterns:
            matches = re.findall(pattern_info["pattern"], text, re.IGNORECASE)

            for match in matches:
                if isinstance(match, tuple):
                    entity = match[-1]  # Take the last group (main entity)
                else:
                    entity = match

                if len(entity) > 2:  # Filter out very short matches
                    node_id = self._generate_node_id(entity, pattern_info["type"])

                    if node_id not in nodes:
                        nodes[node_id] = KnowledgeNode(
                            node_id=node_id,
                            node_type=pattern_info["type"],
                            label=entity,
                            confidence=0.8,
                            source_texts=[text],
                        )
                    else:
                        nodes[node_id].add_source(text)

        # Extract relations using patterns
        for pattern_info in self.relation_patterns:
            matches = re.findall(pattern_info["pattern"], text, re.IGNORECASE)

            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    source_entity = match[0].strip()
                    target_entity = match[1].strip()

                    # Create nodes if they don't exist
                    source_id = self._generate_node_id(source_entity, NodeType.CONCEPT)
                    target_id = self._generate_node_id(target_entity, NodeType.CONCEPT)

                    if source_id not in nodes:
                        nodes[source_id] = KnowledgeNode(
                            node_id=source_id,
                            node_type=NodeType.CONCEPT,
                            label=source_entity,
                            confidence=0.7,
                            source_texts=[text],
                        )

                    if target_id not in nodes:
                        nodes[target_id] = KnowledgeNode(
                            node_id=target_id,
                            node_type=NodeType.CONCEPT,
                            label=target_entity,
                            confidence=0.7,
                            source_texts=[text],
                        )

                    # Create edge
                    edge_id = f"{source_id}_{pattern_info['relation'].value}_{target_id}"

                    if edge_id not in edges:
                        edges[edge_id] = KnowledgeEdge(
                            edge_id=edge_id,
                            source_id=source_id,
                            target_id=target_id,
                            edge_type=pattern_info["relation"],
                            label=pattern_info["relation"].value,
                            confidence=0.8,
                            source_texts=[text],
                        )
                    else:
                        edges[edge_id].add_evidence(text)

        return nodes, edges

    async def _extract_from_logical_form(
        self, logical_expression: str, formalism: LogicFormalism
    ) -> Tuple[Dict[str, KnowledgeNode], Dict[str, KnowledgeEdge]]:
        """Extract nodes and edges from logical representation."""
        nodes = {}
        edges = {}

        try:
            if formalism == LogicFormalism.PLN:
                nodes, edges = await self._extract_from_pln(logical_expression)
            elif formalism == LogicFormalism.FOL:
                nodes, edges = await self._extract_from_fol(logical_expression)
            else:
                # Generic extraction for other formalisms
                nodes, edges = await self._extract_generic_logical_form(logical_expression)

        except Exception as e:
            self.logger.warning(f"Error extracting from logical form: {str(e)}")

        return nodes, edges

    async def _extract_from_pln(
        self, pln_expression: str
    ) -> Tuple[Dict[str, KnowledgeNode], Dict[str, KnowledgeEdge]]:
        """Extract nodes and edges from PLN expression."""
        nodes = {}
        edges = {}

        import re

        # Parse PLN links
        link_pattern = r"(\w+Link)\s*<([^>]+)>\s*([^\n]+)\s*([^\n]+)"
        matches = re.findall(link_pattern, pln_expression, re.MULTILINE)

        for link_type, strength_conf, concept1, concept2 in matches:
            # Parse strength and confidence
            values = strength_conf.split(",")
            strength = float(values[0].strip()) if len(values) > 0 else 0.5
            confidence = float(values[1].strip()) if len(values) > 1 else 0.5

            # Create nodes
            concept1 = concept1.strip()
            concept2 = concept2.strip()

            node1_id = self._generate_node_id(concept1, NodeType.CONCEPT)
            node2_id = self._generate_node_id(concept2, NodeType.CONCEPT)

            nodes[node1_id] = KnowledgeNode(
                node_id=node1_id,
                node_type=NodeType.CONCEPT,
                label=concept1,
                confidence=confidence,
                logical_forms=[pln_expression],
            )

            nodes[node2_id] = KnowledgeNode(
                node_id=node2_id,
                node_type=NodeType.CONCEPT,
                label=concept2,
                confidence=confidence,
                logical_forms=[pln_expression],
            )

            # Determine edge type based on PLN link type
            edge_type_mapping = {
                "InheritanceLink": EdgeType.IS_A,
                "SimilarityLink": EdgeType.SIMILAR_TO,
                "ImplicationLink": EdgeType.IMPLIES,
                "CausalLink": EdgeType.CAUSES,
            }

            edge_type = edge_type_mapping.get(link_type, EdgeType.RELATED_TO)

            # Create edge
            edge_id = f"{node1_id}_{edge_type.value}_{node2_id}"

            edges[edge_id] = KnowledgeEdge(
                edge_id=edge_id,
                source_id=node1_id,
                target_id=node2_id,
                edge_type=edge_type,
                label=link_type,
                confidence=confidence,
                strength=strength,
                logical_forms=[pln_expression],
            )

        return nodes, edges

    async def _extract_from_fol(
        self, fol_expression: str
    ) -> Tuple[Dict[str, KnowledgeNode], Dict[str, KnowledgeEdge]]:
        """Extract nodes and edges from FOL expression."""
        nodes = {}
        edges = {}

        import re

        # Extract predicates and their arguments
        predicate_pattern = r"(\w+)\s*\(([^)]+)\)"
        matches = re.findall(predicate_pattern, fol_expression)

        for predicate, args in matches:
            # Create node for predicate
            pred_id = self._generate_node_id(predicate, NodeType.RELATION)

            nodes[pred_id] = KnowledgeNode(
                node_id=pred_id,
                node_type=NodeType.RELATION,
                label=predicate,
                confidence=0.9,
                logical_forms=[fol_expression],
            )

            # Process arguments
            arg_list = [arg.strip() for arg in args.split(",")]

            for i, arg in enumerate(arg_list):
                # Create node for argument
                arg_id = self._generate_node_id(arg, NodeType.ENTITY)

                if arg_id not in nodes:
                    nodes[arg_id] = KnowledgeNode(
                        node_id=arg_id,
                        node_type=NodeType.ENTITY,
                        label=arg,
                        confidence=0.8,
                        logical_forms=[fol_expression],
                    )

                # Create edge from predicate to argument
                edge_id = f"{pred_id}_arg{i}_{arg_id}"

                edges[edge_id] = KnowledgeEdge(
                    edge_id=edge_id,
                    source_id=pred_id,
                    target_id=arg_id,
                    edge_type=EdgeType.RELATED_TO,
                    label=f"arg{i}",
                    confidence=0.8,
                    logical_forms=[fol_expression],
                )

        return nodes, edges

    async def _extract_generic_logical_form(
        self, expression: str
    ) -> Tuple[Dict[str, KnowledgeNode], Dict[str, KnowledgeEdge]]:
        """Extract nodes and edges from generic logical expression."""
        nodes = {}
        edges = {}

        # Simple extraction of identifiers as concepts
        import re

        identifiers = re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", expression)

        for identifier in set(identifiers):  # Remove duplicates
            if len(identifier) > 1:  # Skip single characters
                node_id = self._generate_node_id(identifier, NodeType.CONCEPT)

                nodes[node_id] = KnowledgeNode(
                    node_id=node_id,
                    node_type=NodeType.CONCEPT,
                    label=identifier,
                    confidence=0.6,
                    logical_forms=[expression],
                )

        return nodes, edges

    def _merge_nodes(
        self,
        existing_nodes: Dict[str, KnowledgeNode],
        new_nodes: Dict[str, KnowledgeNode],
        source_text: str,
    ) -> Dict[str, KnowledgeNode]:
        """Merge new nodes with existing nodes."""
        for node_id, new_node in new_nodes.items():
            if node_id in existing_nodes:
                # Merge with existing node
                existing_node = existing_nodes[node_id]
                existing_node.add_source(source_text)

                # Update confidence (weighted average)
                total_freq = existing_node.frequency + new_node.frequency
                existing_node.confidence = (
                    existing_node.confidence * existing_node.frequency
                    + new_node.confidence * new_node.frequency
                ) / total_freq

                # Merge properties
                existing_node.properties.update(new_node.properties)

                # Merge logical forms
                for logical_form in new_node.logical_forms:
                    if logical_form not in existing_node.logical_forms:
                        existing_node.logical_forms.append(logical_form)
            else:
                # Add new node
                new_node.add_source(source_text)
                existing_nodes[node_id] = new_node

        return existing_nodes

    def _merge_edges(
        self,
        existing_edges: Dict[str, KnowledgeEdge],
        new_edges: Dict[str, KnowledgeEdge],
        source_text: str,
        logical_form: str,
    ) -> Dict[str, KnowledgeEdge]:
        """Merge new edges with existing edges."""
        for edge_id, new_edge in new_edges.items():
            if edge_id in existing_edges:
                # Merge with existing edge
                existing_edge = existing_edges[edge_id]
                existing_edge.add_evidence(source_text, logical_form)

                # Update confidence (weighted average)
                total_freq = existing_edge.frequency + new_edge.frequency
                existing_edge.confidence = (
                    existing_edge.confidence * existing_edge.frequency
                    + new_edge.confidence * new_edge.frequency
                ) / total_freq

                # Update strength (take maximum)
                existing_edge.strength = max(existing_edge.strength, new_edge.strength)

                # Merge properties
                existing_edge.properties.update(new_edge.properties)
            else:
                # Add new edge
                new_edge.add_evidence(source_text, logical_form)
                existing_edges[edge_id] = new_edge

        return existing_edges

    async def _enrich_graph(
        self, nodes: Dict[str, KnowledgeNode], edges: Dict[str, KnowledgeEdge]
    ) -> Tuple[Dict[str, KnowledgeNode], Dict[str, KnowledgeEdge]]:
        """Enrich graph with additional relationships and properties."""
        # Add transitivity for IS-A relationships
        isa_edges = [e for e in edges.values() if e.edge_type == EdgeType.IS_A]

        for edge1 in isa_edges:
            for edge2 in isa_edges:
                if edge1.target_id == edge2.source_id:
                    # Create transitive IS-A relationship
                    new_edge_id = f"{edge1.source_id}_transitive_isa_{edge2.target_id}"

                    if new_edge_id not in edges:
                        edges[new_edge_id] = KnowledgeEdge(
                            edge_id=new_edge_id,
                            source_id=edge1.source_id,
                            target_id=edge2.target_id,
                            edge_type=EdgeType.IS_A,
                            label="transitive_is_a",
                            confidence=min(edge1.confidence, edge2.confidence) * 0.8,
                            properties={"transitive": True},
                        )

        # Calculate node centrality and importance
        temp_graph = nx.DiGraph()

        # Add nodes and edges to temporary graph
        for node in nodes.values():
            temp_graph.add_node(node.node_id)

        for edge in edges.values():
            if edge.source_id in temp_graph and edge.target_id in temp_graph:
                temp_graph.add_edge(edge.source_id, edge.target_id)

        # Calculate centrality measures
        if temp_graph.nodes():
            try:
                centrality = nx.degree_centrality(temp_graph)
                pagerank = nx.pagerank(temp_graph)

                # Update node properties with centrality measures
                for node_id, node in nodes.items():
                    node.properties["degree_centrality"] = centrality.get(node_id, 0.0)
                    node.properties["pagerank"] = pagerank.get(node_id, 0.0)

            except Exception as e:
                self.logger.warning(f"Error calculating centrality: {str(e)}")

        return nodes, edges

    def _calculate_graph_statistics(
        self, nodes: Dict[str, KnowledgeNode], edges: Dict[str, KnowledgeEdge]
    ) -> Dict[str, Any]:
        """Calculate statistics for the knowledge graph."""
        # Node statistics
        node_type_counts = Counter(node.node_type.value for node in nodes.values())
        avg_node_confidence = (
            sum(node.confidence for node in nodes.values()) / len(nodes) if nodes else 0.0
        )

        # Edge statistics
        edge_type_counts = Counter(edge.edge_type.value for edge in edges.values())
        avg_edge_confidence = (
            sum(edge.confidence for edge in edges.values()) / len(edges) if edges else 0.0
        )
        avg_edge_strength = (
            sum(edge.strength for edge in edges.values()) / len(edges) if edges else 0.0
        )

        # Graph connectivity
        temp_graph = nx.Graph()  # Undirected for connectivity analysis

        for edge in edges.values():
            temp_graph.add_edge(edge.source_id, edge.target_id)

        connected_components = (
            list(nx.connected_components(temp_graph)) if temp_graph.nodes() else []
        )

        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "node_types": dict(node_type_counts),
            "edge_types": dict(edge_type_counts),
            "average_node_confidence": avg_node_confidence,
            "average_edge_confidence": avg_edge_confidence,
            "average_edge_strength": avg_edge_strength,
            "connected_components": len(connected_components),
            "largest_component_size": (
                max(len(comp) for comp in connected_components) if connected_components else 0
            ),
            "graph_density": nx.density(temp_graph) if temp_graph.nodes() else 0.0,
        }

    def _generate_node_id(self, label: str, node_type: NodeType) -> str:
        """Generate a unique node ID."""
        normalized_label = label.lower().replace(" ", "_").replace("-", "_")
        normalized_label = "".join(c for c in normalized_label if c.isalnum() or c == "_")
        return f"{node_type.value}_{normalized_label}"

    async def query_graph(
        self, logical_query: str, formalism: LogicFormalism, graph_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query the knowledge graph using logical expressions.

        Args:
            logical_query: Logical query expression
            formalism: Logic formalism used
            graph_id: Optional specific graph to query

        Returns:
            Query results
        """
        try:
            # If no specific graph, query all graphs
            graphs_to_query = (
                [self.graphs[graph_id]]
                if graph_id and graph_id in self.graphs
                else list(self.graphs.values())
            )

            if not graphs_to_query:
                return {"matches": [], "total_results": 0}

            all_matches = []

            for graph in graphs_to_query:
                # Simple pattern matching for now
                # In a full implementation, this would use more sophisticated query processing
                matches = await self._simple_pattern_match(graph, logical_query, formalism)
                all_matches.extend(matches)

            return {
                "matches": all_matches,
                "total_results": len(all_matches),
                "query": logical_query,
                "formalism": formalism.value,
            }

        except Exception as e:
            self.logger.error(f"Error querying graph: {str(e)}")
            return {"matches": [], "total_results": 0, "error": str(e)}

    async def _simple_pattern_match(
        self, graph: KnowledgeGraph, query: str, formalism: LogicFormalism
    ) -> List[Dict[str, Any]]:
        """Perform simple pattern matching on the graph."""
        matches = []

        # Extract key terms from query
        import re

        terms = re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", query.lower())

        # Search nodes for matching labels
        for node in graph.nodes.values():
            node_label_lower = node.label.lower()

            for term in terms:
                if term in node_label_lower or node_label_lower in term:
                    matches.append(
                        {
                            "type": "node",
                            "id": node.node_id,
                            "label": node.label,
                            "node_type": node.node_type.value,
                            "confidence": node.confidence,
                            "relevance_score": len([t for t in terms if t in node_label_lower])
                            / len(terms),
                        }
                    )
                    break

        # Search edges for matching patterns
        for edge in graph.edges.values():
            edge_label_lower = edge.label.lower()

            for term in terms:
                if term in edge_label_lower:
                    source_node = graph.nodes.get(edge.source_id)
                    target_node = graph.nodes.get(edge.target_id)

                    matches.append(
                        {
                            "type": "edge",
                            "id": edge.edge_id,
                            "label": edge.label,
                            "edge_type": edge.edge_type.value,
                            "source": source_node.label if source_node else "Unknown",
                            "target": target_node.label if target_node else "Unknown",
                            "confidence": edge.confidence,
                            "strength": edge.strength,
                        }
                    )
                    break

        # Sort by relevance score
        matches.sort(key=lambda x: x.get("relevance_score", x.get("confidence", 0.0)), reverse=True)

        return matches

    def get_graph_info(self, graph_id: str) -> Dict[str, Any]:
        """Get information about a specific graph."""
        if graph_id not in self.graphs:
            return {"error": "Graph not found"}

        graph = self.graphs[graph_id]

        return {
            "graph_id": graph_id,
            "metadata": graph.metadata,
            "statistics": graph.statistics,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        }

    def list_graphs(self) -> List[Dict[str, Any]]:
        """List all available graphs."""
        return [
            {
                "graph_id": graph_id,
                "node_count": len(graph.nodes),
                "edge_count": len(graph.edges),
                "formalism": graph.metadata.get("formalism", "unknown"),
                "construction_time": graph.metadata.get("construction_time", 0.0),
            }
            for graph_id, graph in self.graphs.items()
        ]

    def export_graph(self, graph_id: str, format: str = "json") -> str:
        """Export graph in specified format."""
        if graph_id not in self.graphs:
            return json.dumps({"error": "Graph not found"})

        graph = self.graphs[graph_id]

        if format.lower() == "json":
            return self._export_to_json(graph)
        elif format.lower() == "rdf":
            return self._export_to_rdf(graph)
        elif format.lower() == "graphml":
            return self._export_to_graphml(graph)
        else:
            return json.dumps({"error": f"Unsupported format: {format}"})

    def _export_to_json(self, graph: KnowledgeGraph) -> str:
        """Export graph to JSON format."""
        export_data = {
            "graph_id": graph.graph_id,
            "metadata": graph.metadata,
            "statistics": graph.statistics,
            "nodes": [
                {
                    "id": node.node_id,
                    "type": node.node_type.value,
                    "label": node.label,
                    "properties": node.properties,
                    "confidence": node.confidence,
                    "frequency": node.frequency,
                }
                for node in graph.nodes.values()
            ],
            "edges": [
                {
                    "id": edge.edge_id,
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "type": edge.edge_type.value,
                    "label": edge.label,
                    "properties": edge.properties,
                    "confidence": edge.confidence,
                    "strength": edge.strength,
                    "frequency": edge.frequency,
                }
                for edge in graph.edges.values()
            ],
        }

        return json.dumps(export_data, indent=2)

    def _export_to_rdf(self, graph: KnowledgeGraph) -> str:
        """Export graph to RDF format (simplified)."""
        # This would require an RDF library like rdflib
        # For now, return a placeholder
        return f"# RDF export for graph {graph.graph_id}\n# (RDF export requires additional dependencies)"

    def _export_to_graphml(self, graph: KnowledgeGraph) -> str:
        """Export graph to GraphML format."""
        import xml.etree.ElementTree as ET

        # Create GraphML structure
        graphml = ET.Element("graphml")
        graphml.set("xmlns", "http://graphml.graphdrawing.org/xmlns")

        # Add graph element
        graph_elem = ET.SubElement(graphml, "graph")
        graph_elem.set("id", graph.graph_id)
        graph_elem.set("edgedefault", "directed")

        # Add nodes
        for node in graph.nodes.values():
            node_elem = ET.SubElement(graph_elem, "node")
            node_elem.set("id", node.node_id)

            # Add node data
            label_data = ET.SubElement(node_elem, "data")
            label_data.set("key", "label")
            label_data.text = node.label

            type_data = ET.SubElement(node_elem, "data")
            type_data.set("key", "type")
            type_data.text = node.node_type.value

        # Add edges
        for edge in graph.edges.values():
            edge_elem = ET.SubElement(graph_elem, "edge")
            edge_elem.set("id", edge.edge_id)
            edge_elem.set("source", edge.source_id)
            edge_elem.set("target", edge.target_id)

            # Add edge data
            label_data = ET.SubElement(edge_elem, "data")
            label_data.set("key", "label")
            label_data.text = edge.label

            type_data = ET.SubElement(edge_elem, "data")
            type_data.set("key", "type")
            type_data.text = edge.edge_type.value

        return ET.tostring(graphml, encoding="unicode")

    def get_builder_stats(self) -> Dict[str, Any]:
        """Get knowledge graph builder statistics."""
        return self.stats.copy()
