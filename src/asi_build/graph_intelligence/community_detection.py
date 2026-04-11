"""
Community Detection Engine for Kenny Graph Intelligence System

Implements community detection algorithms to group related UI elements, workflows, and patterns.
Based on FastToG research paper and Kenny's graph-based automation needs.
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np

from .schema import CommunityNode, NodeType, RelationshipType, create_community
from .schema_manager import SchemaManager

logger = logging.getLogger(__name__)


@dataclass
class CommunityDetectionResult:
    """Result of community detection analysis."""

    communities: List[Dict[str, Any]]
    algorithm: str
    modularity: float
    processing_time: float
    node_count: int
    edge_count: int
    community_count: int
    quality_metrics: Dict[str, float]


@dataclass
class CommunityQualityMetrics:
    """Quality metrics for community evaluation."""

    modularity: float
    coverage: float
    performance: float
    conductance: float
    internal_density: float
    external_density: float


class LouvainCommunityDetection:
    """Louvain algorithm for community detection."""

    def __init__(self, resolution: float = 1.0, max_iterations: int = 100):
        self.resolution = resolution
        self.max_iterations = max_iterations

    def detect_communities(self, graph: nx.Graph) -> Tuple[Dict[str, int], float]:
        """
        Detect communities using Louvain algorithm.

        Returns:
            (community_assignments, modularity_score)
        """
        if len(graph.nodes()) == 0:
            return {}, 0.0

        # Initialize each node in its own community
        communities = {node: i for i, node in enumerate(graph.nodes())}
        current_modularity = self._calculate_modularity(graph, communities)

        improved = True
        iteration = 0

        while improved and iteration < self.max_iterations:
            improved = False
            iteration += 1

            # Phase 1: Local optimization
            for node in graph.nodes():
                best_community = communities[node]
                best_gain = 0.0

                # Try moving node to neighboring communities
                neighbor_communities = set()
                for neighbor in graph.neighbors(node):
                    neighbor_communities.add(communities[neighbor])

                for community in neighbor_communities:
                    if community != communities[node]:
                        # Calculate gain from moving to this community
                        gain = self._calculate_modularity_gain(
                            graph, node, communities[node], community, communities
                        )

                        if gain > best_gain:
                            best_gain = gain
                            best_community = community

                # Move node if improvement found
                if best_gain > 0:
                    communities[node] = best_community
                    improved = True

            # Phase 2: Community aggregation (simplified version)
            new_modularity = self._calculate_modularity(graph, communities)
            if new_modularity <= current_modularity:
                break
            current_modularity = new_modularity

        logger.info(
            f"Louvain completed in {iteration} iterations, modularity: {current_modularity:.3f}"
        )
        return communities, current_modularity

    def _calculate_modularity(self, graph: nx.Graph, communities: Dict[str, int]) -> float:
        """Calculate modularity of current community assignment."""
        if len(graph.edges()) == 0:
            return 0.0

        m = len(graph.edges())
        modularity = 0.0

        for node1 in graph.nodes():
            for node2 in graph.nodes():
                if communities[node1] == communities[node2]:
                    A_ij = 1 if graph.has_edge(node1, node2) else 0
                    k_i = graph.degree(node1)
                    k_j = graph.degree(node2)
                    expected = (k_i * k_j) / (2 * m) if m > 0 else 0
                    modularity += A_ij - expected

        return modularity / (2 * m) if m > 0 else 0.0

    def _calculate_modularity_gain(
        self,
        graph: nx.Graph,
        node: str,
        old_community: int,
        new_community: int,
        communities: Dict[str, int],
    ) -> float:
        """Calculate modularity gain from moving a node."""
        # Simplified gain calculation
        gain = 0.0

        # Calculate connections within new community vs old community
        new_community_connections = 0
        old_community_connections = 0

        for neighbor in graph.neighbors(node):
            if communities[neighbor] == new_community:
                new_community_connections += 1
            elif communities[neighbor] == old_community:
                old_community_connections += 1

        # Simple heuristic: prefer communities with more connections
        gain = new_community_connections - old_community_connections
        return float(gain)


class GirvanNewmanCommunityDetection:
    """Girvan-Newman algorithm for community detection."""

    def __init__(self, max_communities: int = 20):
        self.max_communities = max_communities

    def detect_communities(self, graph: nx.Graph) -> Tuple[Dict[str, int], float]:
        """
        Detect communities using Girvan-Newman algorithm.

        Returns:
            (community_assignments, modularity_score)
        """
        if len(graph.nodes()) == 0:
            return {}, 0.0

        # Start with the entire graph as one community
        current_graph = graph.copy()
        best_communities = {node: 0 for node in graph.nodes()}
        best_modularity = 0.0

        for iteration in range(min(self.max_communities, len(graph.edges()))):
            if len(current_graph.edges()) == 0:
                break

            # Calculate edge betweenness centrality
            betweenness = nx.edge_betweenness_centrality(current_graph)

            # Remove edge with highest betweenness
            if betweenness:
                max_edge = max(betweenness.items(), key=lambda x: x[1])[0]
                current_graph.remove_edge(*max_edge)

            # Find connected components (communities)
            components = list(nx.connected_components(current_graph))

            if len(components) > 1:
                # Assign community IDs
                communities = {}
                for i, component in enumerate(components):
                    for node in component:
                        communities[node] = i

                # Calculate modularity
                modularity = self._calculate_modularity(graph, communities)

                if modularity > best_modularity:
                    best_modularity = modularity
                    best_communities = communities

        logger.info(
            f"Girvan-Newman found {len(set(best_communities.values()))} communities, "
            f"modularity: {best_modularity:.3f}"
        )
        return best_communities, best_modularity

    def _calculate_modularity(self, graph: nx.Graph, communities: Dict[str, int]) -> float:
        """Calculate modularity - same as Louvain implementation."""
        if len(graph.edges()) == 0:
            return 0.0

        m = len(graph.edges())
        modularity = 0.0

        for edge in graph.edges():
            node1, node2 = edge
            if communities[node1] == communities[node2]:
                modularity += 1

        # Subtract expected edges
        community_degrees = defaultdict(int)
        for node in graph.nodes():
            community_degrees[communities[node]] += graph.degree(node)

        expected = 0.0
        for community_degree in community_degrees.values():
            expected += (community_degree**2) / (4 * m)

        return (modularity - expected) / m if m > 0 else 0.0


class LocalCommunitySearch:
    """Local community search for expanding communities around seed nodes."""

    def __init__(self, alpha: float = 0.15, max_size: int = 50):
        self.alpha = alpha  # Random walk parameter
        self.max_size = max_size

    def find_local_community(self, graph: nx.Graph, seed_nodes: List[str]) -> List[str]:
        """
        Find local community around seed nodes using random walks.

        Args:
            graph: NetworkX graph
            seed_nodes: Starting nodes for community expansion

        Returns:
            List of node IDs in the local community
        """
        if not seed_nodes or len(graph.nodes()) == 0:
            return []

        # Initialize scores
        scores = defaultdict(float)
        for seed in seed_nodes:
            if seed in graph.nodes():
                scores[seed] = 1.0

        # Perform random walks
        community = set(seed_nodes)

        for _ in range(10):  # Number of walk iterations
            new_scores = defaultdict(float)

            for node in scores:
                if node not in graph.nodes():
                    continue

                neighbors = list(graph.neighbors(node))
                if not neighbors:
                    new_scores[node] += scores[node]
                    continue

                # Distribute score to neighbors
                score_per_neighbor = scores[node] / len(neighbors)
                for neighbor in neighbors:
                    new_scores[neighbor] += score_per_neighbor * (1 - self.alpha)

                # Keep some score at current node
                new_scores[node] += scores[node] * self.alpha

            scores = new_scores

            # Expand community with high-scoring nodes
            sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            for node, score in sorted_nodes[: self.max_size]:
                if score > 0.1:  # Threshold for inclusion
                    community.add(node)

        return list(community)


class CommunityDetectionEngine:
    """Main community detection engine coordinating different algorithms."""

    def __init__(self, schema_manager: SchemaManager):
        self.sm = schema_manager
        self.louvain = LouvainCommunityDetection()
        self.girvan_newman = GirvanNewmanCommunityDetection()
        self.local_search = LocalCommunitySearch()

    def detect_communities(self, algorithm: str = "louvain") -> List[Dict[str, Any]]:
        """
        Detect communities in the graph (alias for detect_all_communities).

        Args:
            algorithm: "louvain", "girvan_newman", or "hybrid"

        Returns:
            List of community dictionaries
        """
        result = self.detect_all_communities(algorithm)
        return result.communities

    def get_all_communities(self) -> List[Dict[str, Any]]:
        """
        Get all stored communities from the database.

        Returns:
            List of community dictionaries
        """
        communities = self.sm.find_nodes(NodeType.COMMUNITY, limit=1000)
        return communities

    def detect_all_communities(self, algorithm: str = "louvain") -> CommunityDetectionResult:
        """
        Run community detection on the entire knowledge graph.

        Args:
            algorithm: "louvain", "girvan_newman", or "hybrid"

        Returns:
            CommunityDetectionResult with discovered communities
        """
        start_time = time.time()
        logger.info(f"🔍 Starting community detection with {algorithm} algorithm...")

        # Build NetworkX graph from database
        graph = self._build_networkx_graph()

        if len(graph.nodes()) == 0:
            logger.warning("No nodes found in graph database")
            return CommunityDetectionResult(
                communities=[],
                algorithm=algorithm,
                modularity=0.0,
                processing_time=0.0,
                node_count=0,
                edge_count=0,
                community_count=0,
                quality_metrics={},
            )

        # Run selected algorithm
        if algorithm == "louvain":
            communities, modularity = self.louvain.detect_communities(graph)
        elif algorithm == "girvan_newman":
            communities, modularity = self.girvan_newman.detect_communities(graph)
        elif algorithm == "hybrid":
            communities, modularity = self._hybrid_detection(graph)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        # Convert to community groups
        community_groups = self._group_communities(communities)

        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(graph, communities)

        # Store communities in database
        stored_communities = []
        for i, (community_id, members) in enumerate(community_groups.items()):
            community_purpose = self._infer_community_purpose(members)

            community_node = create_community(
                purpose=community_purpose,
                members=members,
                modularity=modularity,
                frequency=self._calculate_frequency(members),
                success_rate=0.8,  # Default, will be updated with usage
                avg_completion_time=5.0,  # Default
                detection_algorithm=algorithm,
            )

            community_db_id = self.sm.create_node(community_node, NodeType.COMMUNITY)

            stored_communities.append(
                {
                    "id": community_db_id,
                    "purpose": community_purpose,
                    "members": members,
                    "size": len(members),
                    "modularity": modularity,
                }
            )

            # Create CONTAINS relationships to members
            for member_id in members:
                rel = self.sm.schema.create_relationship(
                    from_node=community_db_id,
                    to_node=member_id,
                    rel_type=RelationshipType.CONTAINS,
                    weight=1.0,
                    confidence=0.9,
                )
                self.sm.create_relationship(rel)

        processing_time = time.time() - start_time

        logger.info(
            f"✅ Community detection completed: {len(stored_communities)} communities "
            f"found in {processing_time:.2f}s"
        )

        return CommunityDetectionResult(
            communities=stored_communities,
            algorithm=algorithm,
            modularity=modularity,
            processing_time=processing_time,
            node_count=len(graph.nodes()),
            edge_count=len(graph.edges()),
            community_count=len(stored_communities),
            quality_metrics=(
                quality_metrics.__dict__
                if hasattr(quality_metrics, "__dict__")
                else quality_metrics
            ),
        )

    def find_communities_for_nodes(self, node_ids: List[str]) -> List[Dict[str, Any]]:
        """Find existing communities that contain the specified nodes."""
        communities = []

        for node_id in node_ids:
            node_communities = self.sm.get_communities_containing_node(node_id)
            for community in node_communities:
                if community not in communities:
                    communities.append(community)

        return communities

    def expand_community_locally(self, seed_nodes: List[str]) -> List[str]:
        """Expand a community around seed nodes using local search."""
        graph = self._build_networkx_graph()
        return self.local_search.find_local_community(graph, seed_nodes)

    def _build_networkx_graph(self) -> nx.Graph:
        """Build NetworkX graph from database."""
        graph = nx.Graph()

        # Add all nodes
        for node_type in NodeType:
            nodes = self.sm.find_nodes(node_type, limit=1000)
            for node in nodes:
                graph.add_node(node["id"], **node)

        # Add all relationships
        relationships = self.sm.find_relationships(limit=5000)
        for rel in relationships:
            if rel["from_id"] in graph.nodes() and rel["to_id"] in graph.nodes():
                graph.add_edge(rel["from_id"], rel["to_id"], type=rel["type"], **rel["properties"])

        logger.info(f"Built graph: {len(graph.nodes())} nodes, {len(graph.edges())} edges")
        return graph

    def _hybrid_detection(self, graph: nx.Graph) -> Tuple[Dict[str, int], float]:
        """Hybrid approach combining Louvain and Girvan-Newman."""
        # Run both algorithms
        louvain_communities, louvain_mod = self.louvain.detect_communities(graph)
        gn_communities, gn_mod = self.girvan_newman.detect_communities(graph)

        # Choose better result based on modularity
        if louvain_mod >= gn_mod:
            logger.info(f"Hybrid: Selected Louvain (mod: {louvain_mod:.3f} vs {gn_mod:.3f})")
            return louvain_communities, louvain_mod
        else:
            logger.info(f"Hybrid: Selected Girvan-Newman (mod: {gn_mod:.3f} vs {louvain_mod:.3f})")
            return gn_communities, gn_mod

    def _group_communities(self, communities: Dict[str, int]) -> Dict[int, List[str]]:
        """Group nodes by community ID."""
        groups = defaultdict(list)
        for node, community in communities.items():
            groups[community].append(node)
        return dict(groups)

    def _calculate_quality_metrics(
        self, graph: nx.Graph, communities: Dict[str, int]
    ) -> CommunityQualityMetrics:
        """Calculate comprehensive quality metrics for communities."""
        if not communities or len(graph.edges()) == 0:
            return CommunityQualityMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Basic modularity calculation
        modularity = self.louvain._calculate_modularity(graph, communities)

        # Coverage: fraction of edges within communities
        internal_edges = 0
        for edge in graph.edges():
            if communities[edge[0]] == communities[edge[1]]:
                internal_edges += 1

        coverage = internal_edges / len(graph.edges()) if graph.edges() else 0.0

        # Performance: coverage minus inter-community edges normalized
        performance = coverage - (1 - coverage)

        # Simplified metrics for conductance and densities
        conductance = 1 - coverage  # Simplified
        internal_density = coverage
        external_density = 1 - coverage

        return CommunityQualityMetrics(
            modularity=modularity,
            coverage=coverage,
            performance=performance,
            conductance=conductance,
            internal_density=internal_density,
            external_density=external_density,
        )

    def _infer_community_purpose(self, member_ids: List[str]) -> str:
        """Infer the purpose of a community based on its members."""
        # Get member nodes and analyze their types/content
        purposes = []

        for member_id in member_ids[:5]:  # Sample first 5 members
            node = self.sm.get_node(member_id)
            if not node:
                continue

            # Analyze based on node type and content
            if "text" in node:
                text = node["text"].lower()
                if any(word in text for word in ["save", "export", "download"]):
                    purposes.append("save_operations")
                elif any(word in text for word in ["file", "folder", "directory"]):
                    purposes.append("file_management")
                elif any(word in text for word in ["email", "message", "send"]):
                    purposes.append("communication")
                elif any(word in text for word in ["settings", "config", "preferences"]):
                    purposes.append("configuration")
                else:
                    purposes.append("general_interaction")
            elif "name" in node:
                name = node["name"].lower()
                if "workflow" in name:
                    purposes.append("workflow_execution")
                else:
                    purposes.append("automation_task")
            else:
                purposes.append("ui_interaction")

        # Return most common purpose or default
        if purposes:
            from collections import Counter

            most_common = Counter(purposes).most_common(1)[0][0]
            return most_common

        return "mixed_operations"

    def _calculate_frequency(self, member_ids: List[str]) -> int:
        """Calculate estimated frequency based on community size and member activity."""
        # Simple heuristic: larger communities are likely used more frequently
        base_frequency = len(member_ids) * 5

        # Check for workflow nodes which might have execution counts
        for member_id in member_ids[:3]:
            node = self.sm.get_node(member_id)
            if node and "execution_count" in node:
                base_frequency += int(node["execution_count"])

        return min(base_frequency, 500)  # Cap at reasonable maximum


# Test the community detection engine
if __name__ == "__main__":
    print("🧪 Testing Community Detection Engine...")

    with SchemaManager() as sm:
        engine = CommunityDetectionEngine(sm)

        # Test community detection
        result = engine.detect_all_communities("louvain")

        print(f"✅ Community Detection Results:")
        print(f"   - Algorithm: {result.algorithm}")
        print(f"   - Communities found: {result.community_count}")
        print(f"   - Modularity: {result.modularity:.3f}")
        print(f"   - Processing time: {result.processing_time:.2f}s")
        print(f"   - Graph size: {result.node_count} nodes, {result.edge_count} edges")

        if result.communities:
            print(f"   - Sample communities:")
            for i, community in enumerate(result.communities[:3]):
                print(f"     {i+1}. Purpose: {community['purpose']}, Size: {community['size']}")

        # Test local community expansion
        if result.communities:
            first_community = result.communities[0]
            seed_nodes = first_community["members"][:2]
            expanded = engine.expand_community_locally(seed_nodes)
            print(f"✅ Local expansion: {len(seed_nodes)} seeds → {len(expanded)} nodes")

    print("✅ Community Detection Engine testing completed!")
