"""Tests for knowledge management module (Candidate 11 — omniscience)."""

import pytest

aiohttp = pytest.importorskip("aiohttp", reason="aiohttp not installed")
import asyncio
import time


class TestKnowledgeGraphManager:
    """Test knowledge graph with networkx."""

    def _make_manager(self):
        from src.asi_build.knowledge_management.core.knowledge_graph_manager import (
            KnowledgeGraphManager,
        )

        return KnowledgeGraphManager()

    def test_init_creates_empty_graph(self):
        mgr = self._make_manager()
        assert len(mgr.nodes) == 0
        assert len(mgr.relationships) == 0
        assert len(mgr.graph.nodes()) == 0

    def test_add_node_manually(self):
        from src.asi_build.knowledge_management.core.knowledge_graph_manager import KnowledgeNode

        mgr = self._make_manager()
        node = KnowledgeNode(id="n1", label="test", node_type="concept", properties={"k": "v"})
        mgr.nodes[node.id] = node
        mgr.graph.add_node(node.id)
        assert "n1" in mgr.graph.nodes()

    def test_add_relationship(self):
        from src.asi_build.knowledge_management.core.knowledge_graph_manager import (
            KnowledgeGraphManager,
            KnowledgeRelationship,
        )

        mgr = self._make_manager()
        mgr.graph.add_node("a")
        mgr.graph.add_node("b")
        rel = KnowledgeRelationship(
            source_id="a",
            target_id="b",
            relationship_type="relates_to",
            properties={},
            strength=0.9,
        )
        mgr.relationships.append(rel)
        mgr.graph.add_edge(rel.source_id, rel.target_id, relationship_type=rel.relationship_type)
        assert mgr.graph.has_edge("a", "b")

    def test_graph_statistics(self):
        mgr = self._make_manager()
        mgr.graph.add_node("x")
        mgr.graph.add_node("y")
        mgr.graph.add_edge("x", "y")
        stats = mgr._get_graph_statistics()
        assert stats["graph_nodes"] == 2
        assert stats["graph_edges"] == 1

    def test_complexity_empty(self):
        mgr = self._make_manager()
        assert mgr._calculate_graph_complexity() == 0.0

    def test_complexity_with_edges(self):
        mgr = self._make_manager()
        for i in range(5):
            mgr.graph.add_node(f"n{i}")
        for i in range(4):
            mgr.graph.add_edge(f"n{i}", f"n{i+1}")
        complexity = mgr._calculate_graph_complexity()
        assert complexity > 0

    def test_get_subgraph(self):
        mgr = self._make_manager()
        mgr.graph.add_node("concept_ai")
        mgr.graph.add_node("concept_ml")
        mgr.graph.add_node("concept_data")
        mgr.graph.add_edge("concept_ai", "concept_ml")
        mgr.graph.add_edge("concept_ml", "concept_data")
        subgraph = mgr.get_knowledge_subgraph(["ai"], max_depth=2)
        assert "ai" in subgraph["nodes"]
        assert subgraph["subgraph_size"] >= 1

    def test_default_config(self):
        mgr = self._make_manager()
        config = mgr.config
        assert "max_analysis_depth" in config
        assert "relationship_types" in config
        assert len(config["relationship_types"]) > 0


class TestKnowledgeQuery:
    """Test knowledge query dataclass."""

    def test_query_auto_timestamp(self):
        from src.asi_build.knowledge_management.core.knowledge_engine import KnowledgeQuery

        q = KnowledgeQuery(query="test", context={})
        assert q.timestamp is not None
        assert q.timestamp > 0

    def test_knowledge_result(self):
        from src.asi_build.knowledge_management.core.knowledge_engine import (
            KnowledgeQuery,
            KnowledgeResult,
        )

        q = KnowledgeQuery(query="test", context={})
        r = KnowledgeResult(
            query=q,
            result={"answer": "yes"},
            confidence=0.9,
            sources=["src1"],
            processing_time=0.5,
            metadata={},
        )
        assert r.confidence == 0.9


class TestKnowledgeEngine:
    """Test knowledge engine initialization."""

    def test_init_with_defaults(self):
        from src.asi_build.knowledge_management.core.knowledge_engine import KnowledgeEngine

        engine = KnowledgeEngine()
        assert engine.query_count == 0
        assert engine.average_confidence == 0.0

    def test_performance_metrics(self):
        from src.asi_build.knowledge_management.core.knowledge_engine import KnowledgeEngine

        engine = KnowledgeEngine()
        metrics = engine.get_performance_metrics()
        assert metrics["total_queries"] == 0
        assert "subsystem_status" in metrics
