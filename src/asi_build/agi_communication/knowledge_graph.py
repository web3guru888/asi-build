"""
Knowledge Graph Merging with Conflict Resolution
==============================================

Advanced system for merging knowledge graphs from different AGIs
with sophisticated conflict detection and resolution mechanisms.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from .core import CommunicationMessage, MessageType
from .semantic import KnowledgeRepresentation, SemanticEntity

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of conflicts in knowledge graph merging."""

    ONTOLOGICAL = "ontological"  # Different types for same entity
    FACTUAL = "factual"  # Contradictory facts
    TEMPORAL = "temporal"  # Different time validity
    CONFIDENCE = "confidence"  # Different confidence levels
    STRUCTURAL = "structural"  # Different graph structures
    SEMANTIC = "semantic"  # Semantic misalignment


class ResolutionStrategy(Enum):
    """Strategies for resolving conflicts."""

    TRUST_BASED = "trust_based"  # Use trust scores
    EVIDENCE_BASED = "evidence_based"  # Use evidence strength
    TEMPORAL_BASED = "temporal_based"  # Use recency
    CONSENSUS_BASED = "consensus_based"  # Use majority consensus
    CONFIDENCE_BASED = "confidence_based"  # Use confidence scores
    HYBRID = "hybrid"  # Combination of strategies


@dataclass
class KnowledgeNode:
    """Node in a knowledge graph."""

    id: str
    type: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_agi: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    def __hash__(self):
        return hash(self.id)


@dataclass
class KnowledgeEdge:
    """Edge in a knowledge graph."""

    id: str
    source: str
    target: str
    relation_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_agi: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    def __hash__(self):
        return hash(f"{self.source}_{self.relation_type}_{self.target}")


@dataclass
class KnowledgeGraph:
    """Knowledge graph representation."""

    id: str
    nodes: Dict[str, KnowledgeNode] = field(default_factory=dict)
    edges: Dict[str, KnowledgeEdge] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_agi: str = ""
    version: int = 1

    def add_node(self, node: KnowledgeNode):
        """Add node to graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: KnowledgeEdge):
        """Add edge to graph."""
        self.edges[edge.id] = edge

    def get_node_neighbors(self, node_id: str) -> List[str]:
        """Get neighbors of a node."""
        neighbors = []
        for edge in self.edges.values():
            if edge.source == node_id:
                neighbors.append(edge.target)
            elif edge.target == node_id:
                neighbors.append(edge.source)
        return neighbors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type,
                    "label": node.label,
                    "properties": node.properties,
                    "confidence": node.confidence,
                    "source_agi": node.source_agi,
                    "timestamp": node.timestamp.isoformat(),
                    "evidence": node.evidence,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "id": edge.id,
                    "source": edge.source,
                    "target": edge.target,
                    "relation_type": edge.relation_type,
                    "properties": edge.properties,
                    "confidence": edge.confidence,
                    "source_agi": edge.source_agi,
                    "timestamp": edge.timestamp.isoformat(),
                    "evidence": edge.evidence,
                }
                for edge in self.edges.values()
            ],
            "metadata": self.metadata,
            "source_agi": self.source_agi,
            "version": self.version,
        }


@dataclass
class Conflict:
    """Represents a conflict between knowledge elements."""

    id: str
    conflict_type: ConflictType
    elements: List[Union[KnowledgeNode, KnowledgeEdge]]
    description: str
    severity: float  # 0-1, higher is more severe
    resolution_strategies: List[ResolutionStrategy] = field(default_factory=list)

    def __post_init__(self):
        if not self.resolution_strategies:
            self.resolution_strategies = [ResolutionStrategy.HYBRID]


@dataclass
class MergeResult:
    """Result of a knowledge graph merge operation."""

    merged_graph: KnowledgeGraph
    conflicts: List[Conflict]
    resolved_conflicts: List[Conflict]
    unresolved_conflicts: List[Conflict]
    merge_statistics: Dict[str, Any]
    confidence_score: float


class KnowledgeGraphMerger:
    """
    Knowledge Graph Merging System

    Merges knowledge graphs from different AGIs with sophisticated
    conflict detection and resolution mechanisms.
    """

    def __init__(self, protocol):
        self.protocol = protocol
        self.graphs: Dict[str, KnowledgeGraph] = {}
        self.merge_history: List[Dict[str, Any]] = []
        self.conflict_resolution_strategies = {
            ConflictType.ONTOLOGICAL: [
                ResolutionStrategy.CONSENSUS_BASED,
                ResolutionStrategy.TRUST_BASED,
            ],
            ConflictType.FACTUAL: [
                ResolutionStrategy.EVIDENCE_BASED,
                ResolutionStrategy.CONFIDENCE_BASED,
            ],
            ConflictType.TEMPORAL: [ResolutionStrategy.TEMPORAL_BASED],
            ConflictType.CONFIDENCE: [ResolutionStrategy.CONFIDENCE_BASED],
            ConflictType.STRUCTURAL: [
                ResolutionStrategy.TRUST_BASED,
                ResolutionStrategy.CONSENSUS_BASED,
            ],
            ConflictType.SEMANTIC: [
                ResolutionStrategy.EVIDENCE_BASED,
                ResolutionStrategy.TRUST_BASED,
            ],
        }

    async def merge_graphs(
        self,
        graphs: List[KnowledgeGraph],
        resolution_strategy: ResolutionStrategy = ResolutionStrategy.HYBRID,
    ) -> MergeResult:
        """Merge multiple knowledge graphs with conflict resolution."""
        if len(graphs) < 2:
            raise ValueError("At least 2 graphs required for merging")

        # Initialize merge result
        merged_graph_id = f"merged_{int(datetime.now().timestamp())}"
        merged_graph = KnowledgeGraph(
            id=merged_graph_id,
            source_agi=f"merged_from_{len(graphs)}_sources",
            metadata={
                "merge_timestamp": datetime.now().isoformat(),
                "source_graphs": [g.id for g in graphs],
                "resolution_strategy": resolution_strategy.value,
            },
        )

        conflicts = []

        # Step 1: Entity resolution and node merging
        node_conflicts = await self._merge_nodes(graphs, merged_graph)
        conflicts.extend(node_conflicts)

        # Step 2: Relationship merging and edge conflicts
        edge_conflicts = await self._merge_edges(graphs, merged_graph)
        conflicts.extend(edge_conflicts)

        # Step 3: Conflict resolution
        resolved_conflicts, unresolved_conflicts = await self._resolve_conflicts(
            conflicts, resolution_strategy
        )

        # Step 4: Apply resolutions to merged graph
        await self._apply_resolutions(merged_graph, resolved_conflicts)

        # Step 5: Calculate merge statistics
        merge_statistics = self._calculate_merge_statistics(graphs, merged_graph, conflicts)

        # Step 6: Calculate overall confidence
        confidence_score = self._calculate_confidence_score(
            merged_graph, resolved_conflicts, unresolved_conflicts
        )

        merge_result = MergeResult(
            merged_graph=merged_graph,
            conflicts=conflicts,
            resolved_conflicts=resolved_conflicts,
            unresolved_conflicts=unresolved_conflicts,
            merge_statistics=merge_statistics,
            confidence_score=confidence_score,
        )

        # Record merge operation
        self._record_merge(graphs, merge_result)

        return merge_result

    async def _merge_nodes(
        self, graphs: List[KnowledgeGraph], merged_graph: KnowledgeGraph
    ) -> List[Conflict]:
        """Merge nodes from multiple graphs and detect conflicts."""
        conflicts = []
        node_clusters = {}  # Group similar nodes

        # Collect all nodes
        all_nodes = []
        for graph in graphs:
            all_nodes.extend(graph.nodes.values())

        # Entity resolution - group similar nodes
        for node in all_nodes:
            cluster_key = self._get_node_cluster_key(node)
            if cluster_key not in node_clusters:
                node_clusters[cluster_key] = []
            node_clusters[cluster_key].append(node)

        # Process each cluster
        for cluster_key, nodes in node_clusters.items():
            if len(nodes) == 1:
                # No conflict, add directly
                merged_graph.add_node(nodes[0])
            else:
                # Potential conflict, analyze
                conflict = await self._analyze_node_conflict(nodes)
                if conflict:
                    conflicts.append(conflict)

                # Create merged node (preliminary)
                merged_node = await self._create_merged_node(nodes)
                merged_graph.add_node(merged_node)

        return conflicts

    async def _merge_edges(
        self, graphs: List[KnowledgeGraph], merged_graph: KnowledgeGraph
    ) -> List[Conflict]:
        """Merge edges from multiple graphs and detect conflicts."""
        conflicts = []
        edge_clusters = {}

        # Collect all edges
        all_edges = []
        for graph in graphs:
            all_edges.extend(graph.edges.values())

        # Group similar edges
        for edge in all_edges:
            cluster_key = self._get_edge_cluster_key(edge)
            if cluster_key not in edge_clusters:
                edge_clusters[cluster_key] = []
            edge_clusters[cluster_key].append(edge)

        # Process each cluster
        for cluster_key, edges in edge_clusters.items():
            if len(edges) == 1:
                # No conflict
                merged_graph.add_edge(edges[0])
            else:
                # Potential conflict
                conflict = await self._analyze_edge_conflict(edges)
                if conflict:
                    conflicts.append(conflict)

                # Create merged edge
                merged_edge = await self._create_merged_edge(edges)
                merged_graph.add_edge(merged_edge)

        return conflicts

    def _get_node_cluster_key(self, node: KnowledgeNode) -> str:
        """Get cluster key for node entity resolution."""
        # Use normalized label and type for clustering
        normalized_label = node.label.lower().strip()
        return f"{node.type}:{normalized_label}"

    def _get_edge_cluster_key(self, edge: KnowledgeEdge) -> str:
        """Get cluster key for edge entity resolution."""
        return f"{edge.source}:{edge.relation_type}:{edge.target}"

    async def _analyze_node_conflict(self, nodes: List[KnowledgeNode]) -> Optional[Conflict]:
        """Analyze potential conflicts between nodes."""
        if len(nodes) < 2:
            return None

        conflicts_found = []

        # Check type conflicts
        types = set(node.type for node in nodes)
        if len(types) > 1:
            conflicts_found.append(ConflictType.ONTOLOGICAL)

        # Check property conflicts
        all_properties = {}
        for node in nodes:
            for prop, value in node.properties.items():
                if prop not in all_properties:
                    all_properties[prop] = []
                all_properties[prop].append((value, node.source_agi, node.confidence))

        for prop, values in all_properties.items():
            unique_values = set(v[0] for v in values)
            if len(unique_values) > 1:
                conflicts_found.append(ConflictType.FACTUAL)

        # Check temporal conflicts
        timestamps = [node.timestamp for node in nodes]
        time_diff = max(timestamps) - min(timestamps)
        if time_diff.days > 30:  # More than 30 days difference
            conflicts_found.append(ConflictType.TEMPORAL)

        # Check confidence conflicts
        confidences = [node.confidence for node in nodes]
        if max(confidences) - min(confidences) > 0.5:
            conflicts_found.append(ConflictType.CONFIDENCE)

        if conflicts_found:
            conflict_id = (
                f"node_conflict_{hashlib.md5(str([n.id for n in nodes]).encode()).hexdigest()[:8]}"
            )
            return Conflict(
                id=conflict_id,
                conflict_type=conflicts_found[0],  # Primary conflict type
                elements=nodes,
                description=f"Node conflict: {', '.join(c.value for c in conflicts_found)}",
                severity=len(conflicts_found) / 4.0,  # Normalize by max possible conflicts
            )

        return None

    async def _analyze_edge_conflict(self, edges: List[KnowledgeEdge]) -> Optional[Conflict]:
        """Analyze potential conflicts between edges."""
        if len(edges) < 2:
            return None

        # Check for contradictory relationships
        relation_types = set(edge.relation_type for edge in edges)
        if len(relation_types) > 1:
            # Check if relations are contradictory
            contradictory_pairs = [
                {"is_a", "is_not_a"},
                {"has", "lacks"},
                {"causes", "prevents"},
                {"supports", "opposes"},
            ]

            for pair in contradictory_pairs:
                if pair.issubset(relation_types):
                    conflict_id = f"edge_conflict_{hashlib.md5(str([e.id for e in edges]).encode()).hexdigest()[:8]}"
                    return Conflict(
                        id=conflict_id,
                        conflict_type=ConflictType.FACTUAL,
                        elements=edges,
                        description=f"Contradictory relationships: {relation_types}",
                        severity=1.0,
                    )

        return None

    async def _create_merged_node(self, nodes: List[KnowledgeNode]) -> KnowledgeNode:
        """Create merged node from multiple nodes."""
        # Use the node with highest confidence as base
        base_node = max(nodes, key=lambda n: n.confidence)

        # Merge properties
        merged_properties = {}
        for node in nodes:
            for prop, value in node.properties.items():
                if prop not in merged_properties:
                    merged_properties[prop] = []
                merged_properties[prop].append(
                    {"value": value, "confidence": node.confidence, "source_agi": node.source_agi}
                )

        # Select best value for each property
        final_properties = {}
        for prop, values in merged_properties.items():
            best_value = max(values, key=lambda v: v["confidence"])
            final_properties[prop] = best_value["value"]

        # Calculate merged confidence
        avg_confidence = sum(node.confidence for node in nodes) / len(nodes)

        return KnowledgeNode(
            id=base_node.id,
            type=base_node.type,
            label=base_node.label,
            properties=final_properties,
            confidence=avg_confidence,
            source_agi=f"merged_from_{len(nodes)}_sources",
            timestamp=max(node.timestamp for node in nodes),
            evidence=[item for node in nodes for item in node.evidence],
        )

    async def _create_merged_edge(self, edges: List[KnowledgeEdge]) -> KnowledgeEdge:
        """Create merged edge from multiple edges."""
        base_edge = max(edges, key=lambda e: e.confidence)

        # Merge properties
        merged_properties = {}
        for edge in edges:
            merged_properties.update(edge.properties)

        # Calculate merged confidence
        avg_confidence = sum(edge.confidence for edge in edges) / len(edges)

        return KnowledgeEdge(
            id=base_edge.id,
            source=base_edge.source,
            target=base_edge.target,
            relation_type=base_edge.relation_type,
            properties=merged_properties,
            confidence=avg_confidence,
            source_agi=f"merged_from_{len(edges)}_sources",
            timestamp=max(edge.timestamp for edge in edges),
            evidence=[item for edge in edges for item in edge.evidence],
        )

    async def _resolve_conflicts(
        self, conflicts: List[Conflict], strategy: ResolutionStrategy
    ) -> Tuple[List[Conflict], List[Conflict]]:
        """Resolve conflicts using specified strategy."""
        resolved_conflicts = []
        unresolved_conflicts = []

        for conflict in conflicts:
            try:
                if strategy == ResolutionStrategy.HYBRID:
                    # Use conflict-type specific strategies
                    strategies = self.conflict_resolution_strategies.get(
                        conflict.conflict_type, [ResolutionStrategy.TRUST_BASED]
                    )
                    resolution_successful = False

                    for strat in strategies:
                        if await self._apply_resolution_strategy(conflict, strat):
                            resolved_conflicts.append(conflict)
                            resolution_successful = True
                            break

                    if not resolution_successful:
                        unresolved_conflicts.append(conflict)
                else:
                    # Use specified strategy
                    if await self._apply_resolution_strategy(conflict, strategy):
                        resolved_conflicts.append(conflict)
                    else:
                        unresolved_conflicts.append(conflict)

            except Exception as e:
                logger.error(f"Error resolving conflict {conflict.id}: {e}")
                unresolved_conflicts.append(conflict)

        return resolved_conflicts, unresolved_conflicts

    async def _apply_resolution_strategy(
        self, conflict: Conflict, strategy: ResolutionStrategy
    ) -> bool:
        """Apply specific resolution strategy to conflict."""
        if strategy == ResolutionStrategy.TRUST_BASED:
            return await self._resolve_by_trust(conflict)
        elif strategy == ResolutionStrategy.EVIDENCE_BASED:
            return await self._resolve_by_evidence(conflict)
        elif strategy == ResolutionStrategy.TEMPORAL_BASED:
            return await self._resolve_by_time(conflict)
        elif strategy == ResolutionStrategy.CONSENSUS_BASED:
            return await self._resolve_by_consensus(conflict)
        elif strategy == ResolutionStrategy.CONFIDENCE_BASED:
            return await self._resolve_by_confidence(conflict)

        return False

    async def _resolve_by_trust(self, conflict: Conflict) -> bool:
        """Resolve conflict based on AGI trust scores."""
        trust_scores = {}
        for element in conflict.elements:
            agi_id = element.source_agi
            if agi_id in self.protocol.known_agis:
                trust_scores[agi_id] = self.protocol.known_agis[agi_id].trust_score

        if trust_scores:
            most_trusted_agi = max(trust_scores.keys(), key=lambda k: trust_scores[k])
            # Mark elements from most trusted AGI as preferred
            for element in conflict.elements:
                if element.source_agi == most_trusted_agi:
                    element.metadata = getattr(element, "metadata", {})
                    element.metadata["resolution"] = "trust_preferred"
            return True

        return False

    async def _resolve_by_evidence(self, conflict: Conflict) -> bool:
        """Resolve conflict based on evidence strength."""
        evidence_scores = {}
        for element in conflict.elements:
            evidence_count = len(element.evidence) if hasattr(element, "evidence") else 0
            evidence_scores[element] = evidence_count

        if evidence_scores:
            best_element = max(evidence_scores.keys(), key=lambda k: evidence_scores[k])
            best_element.metadata = getattr(best_element, "metadata", {})
            best_element.metadata["resolution"] = "evidence_preferred"
            return True

        return False

    async def _resolve_by_time(self, conflict: Conflict) -> bool:
        """Resolve conflict based on recency."""
        most_recent = max(conflict.elements, key=lambda e: e.timestamp)
        most_recent.metadata = getattr(most_recent, "metadata", {})
        most_recent.metadata["resolution"] = "temporal_preferred"
        return True

    async def _resolve_by_consensus(self, conflict: Conflict) -> bool:
        """Resolve conflict based on majority consensus."""
        # Group elements by similarity
        element_groups = {}
        for element in conflict.elements:
            if isinstance(element, KnowledgeNode):
                key = f"{element.type}_{element.label}"
            else:  # KnowledgeEdge
                key = f"{element.relation_type}"

            if key not in element_groups:
                element_groups[key] = []
            element_groups[key].append(element)

        # Find majority group
        if element_groups:
            majority_group = max(element_groups.values(), key=len)
            for element in majority_group:
                element.metadata = getattr(element, "metadata", {})
                element.metadata["resolution"] = "consensus_preferred"
            return True

        return False

    async def _resolve_by_confidence(self, conflict: Conflict) -> bool:
        """Resolve conflict based on confidence scores."""
        highest_confidence = max(conflict.elements, key=lambda e: e.confidence)
        highest_confidence.metadata = getattr(highest_confidence, "metadata", {})
        highest_confidence.metadata["resolution"] = "confidence_preferred"
        return True

    async def _apply_resolutions(
        self, merged_graph: KnowledgeGraph, resolved_conflicts: List[Conflict]
    ):
        """Apply conflict resolutions to merged graph."""
        for conflict in resolved_conflicts:
            # Find preferred elements and update graph
            preferred_elements = [
                e
                for e in conflict.elements
                if hasattr(e, "metadata") and e.metadata.get("resolution")
            ]

            # Update graph with preferred elements
            for element in preferred_elements:
                if isinstance(element, KnowledgeNode):
                    merged_graph.nodes[element.id] = element
                else:  # KnowledgeEdge
                    merged_graph.edges[element.id] = element

    def _calculate_merge_statistics(
        self,
        source_graphs: List[KnowledgeGraph],
        merged_graph: KnowledgeGraph,
        conflicts: List[Conflict],
    ) -> Dict[str, Any]:
        """Calculate merge operation statistics."""
        total_source_nodes = sum(len(g.nodes) for g in source_graphs)
        total_source_edges = sum(len(g.edges) for g in source_graphs)

        return {
            "source_graphs": len(source_graphs),
            "total_source_nodes": total_source_nodes,
            "total_source_edges": total_source_edges,
            "merged_nodes": len(merged_graph.nodes),
            "merged_edges": len(merged_graph.edges),
            "total_conflicts": len(conflicts),
            "node_reduction_ratio": (
                1.0 - (len(merged_graph.nodes) / total_source_nodes)
                if total_source_nodes > 0
                else 0
            ),
            "edge_reduction_ratio": (
                1.0 - (len(merged_graph.edges) / total_source_edges)
                if total_source_edges > 0
                else 0
            ),
        }

    def _calculate_confidence_score(
        self,
        merged_graph: KnowledgeGraph,
        resolved_conflicts: List[Conflict],
        unresolved_conflicts: List[Conflict],
    ) -> float:
        """Calculate overall confidence score for merged graph."""
        # Base confidence from nodes and edges
        node_confidences = [node.confidence for node in merged_graph.nodes.values()]
        edge_confidences = [edge.confidence for edge in merged_graph.edges.values()]

        base_confidence = (
            (
                (sum(node_confidences) + sum(edge_confidences))
                / (len(node_confidences) + len(edge_confidences))
            )
            if (node_confidences or edge_confidences)
            else 0.5
        )

        # Adjust for conflict resolution
        total_conflicts = len(resolved_conflicts) + len(unresolved_conflicts)
        if total_conflicts > 0:
            resolution_ratio = len(resolved_conflicts) / total_conflicts
            conflict_penalty = (1 - resolution_ratio) * 0.3  # Max 30% penalty
            base_confidence -= conflict_penalty

        return max(0.0, min(1.0, base_confidence))

    def _record_merge(self, source_graphs: List[KnowledgeGraph], merge_result: MergeResult):
        """Record merge operation for analysis."""
        merge_record = {
            "timestamp": datetime.now().isoformat(),
            "source_graph_ids": [g.id for g in source_graphs],
            "merged_graph_id": merge_result.merged_graph.id,
            "conflicts_total": len(merge_result.conflicts),
            "conflicts_resolved": len(merge_result.resolved_conflicts),
            "confidence_score": merge_result.confidence_score,
            "statistics": merge_result.merge_statistics,
        }

        self.merge_history.append(merge_record)

    async def handle_knowledge_share(self, message: CommunicationMessage):
        """Handle knowledge sharing message from another AGI."""
        payload = message.payload

        try:
            # Parse knowledge graph from message
            graph_data = payload["knowledge_graph"]
            graph = self._parse_graph_from_dict(graph_data)

            # Store graph
            self.graphs[graph.id] = graph

            # If auto-merge is enabled, merge with existing graphs
            if payload.get("auto_merge", False):
                existing_graphs = list(self.graphs.values())
                if len(existing_graphs) > 1:
                    merge_result = await self.merge_graphs(existing_graphs)

                    # Send merge result back
                    response_message = CommunicationMessage(
                        id=f"merge_result_{message.id}",
                        sender_id=self.protocol.identity.id,
                        receiver_id=message.sender_id,
                        message_type=MessageType.KNOWLEDGE_SHARE,
                        timestamp=datetime.now(),
                        payload={
                            "original_message_id": message.id,
                            "merge_result": {
                                "merged_graph_id": merge_result.merged_graph.id,
                                "conflicts_resolved": len(merge_result.resolved_conflicts),
                                "confidence_score": merge_result.confidence_score,
                            },
                        },
                        session_id=message.session_id,
                    )

                    await self.protocol.send_message(response_message)

        except Exception as e:
            logger.error(f"Error handling knowledge share: {e}")

    def _parse_graph_from_dict(self, graph_data: Dict[str, Any]) -> KnowledgeGraph:
        """Parse knowledge graph from dictionary."""
        graph = KnowledgeGraph(
            id=graph_data["id"],
            source_agi=graph_data.get("source_agi", ""),
            version=graph_data.get("version", 1),
            metadata=graph_data.get("metadata", {}),
        )

        # Parse nodes
        for node_data in graph_data.get("nodes", []):
            node = KnowledgeNode(
                id=node_data["id"],
                type=node_data["type"],
                label=node_data["label"],
                properties=node_data.get("properties", {}),
                confidence=node_data.get("confidence", 1.0),
                source_agi=node_data.get("source_agi", ""),
                timestamp=datetime.fromisoformat(
                    node_data.get("timestamp", datetime.now().isoformat())
                ),
                evidence=node_data.get("evidence", []),
            )
            graph.add_node(node)

        # Parse edges
        for edge_data in graph_data.get("edges", []):
            edge = KnowledgeEdge(
                id=edge_data["id"],
                source=edge_data["source"],
                target=edge_data["target"],
                relation_type=edge_data["relation_type"],
                properties=edge_data.get("properties", {}),
                confidence=edge_data.get("confidence", 1.0),
                source_agi=edge_data.get("source_agi", ""),
                timestamp=datetime.fromisoformat(
                    edge_data.get("timestamp", datetime.now().isoformat())
                ),
                evidence=edge_data.get("evidence", []),
            )
            graph.add_edge(edge)

        return graph

    def get_merge_statistics(self) -> Dict[str, Any]:
        """Get merge operation statistics."""
        if not self.merge_history:
            return {"total_merges": 0}

        total_merges = len(self.merge_history)
        avg_confidence = (
            sum(record["confidence_score"] for record in self.merge_history) / total_merges
        )
        total_conflicts = sum(record["conflicts_total"] for record in self.merge_history)
        resolved_conflicts = sum(record["conflicts_resolved"] for record in self.merge_history)

        return {
            "total_merges": total_merges,
            "average_confidence": avg_confidence,
            "total_conflicts": total_conflicts,
            "resolved_conflicts": resolved_conflicts,
            "resolution_rate": resolved_conflicts / total_conflicts if total_conflicts > 0 else 1.0,
            "stored_graphs": len(self.graphs),
        }
