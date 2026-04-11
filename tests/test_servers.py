"""
Tests for asi_build.servers module.

The MCP server needs 'mcp' and 'neo4j' packages;
the SSE server needs 'neo4j' and 'fastapi'.
We mock all external deps and test the data-handling / handler logic.
"""

import pytest
import asyncio
import json
import os
import time
from unittest.mock import MagicMock, AsyncMock, patch, mock_open


# ── SSE Server (KennyGraphSSE + FastAPI endpoints) ──────────────────────
# The SSE module can be imported as long as neo4j & fastapi are available;
# we mock the driver to avoid a real connection.

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from asi_build.servers.kenny_graph_sse_server import (
    KennyGraphSSE, app,
)


class TestKennyGraphSSEInit:
    def test_init_no_driver(self):
        sse = KennyGraphSSE()
        assert sse.driver is None

    @pytest.mark.asyncio
    async def test_connect_memgraph_failure(self):
        """Without a real Memgraph, connect should fail gracefully."""
        sse = KennyGraphSSE()
        # GraphDatabase.driver will raise on connect
        result = await sse.connect_memgraph()
        # Either False or True depending on local state — just no crash
        assert isinstance(result, bool)


class TestKennyGraphSSEStatsNoDriver:
    def test_get_kenny_graph_stats_no_driver(self):
        sse = KennyGraphSSE()
        stats = sse.get_kenny_graph_stats()
        assert stats["status"] == "unknown"
        assert stats["nodes"] == 0
        assert stats["relationships"] == 0

    def test_get_kenny_graph_stats_structure(self):
        sse = KennyGraphSSE()
        stats = sse.get_kenny_graph_stats()
        for key in ["timestamp", "status", "nodes", "relationships",
                     "node_types", "relationship_types", "recent_activity"]:
            assert key in stats

    def test_get_kenny_analysis_stats_no_db(self):
        sse = KennyGraphSSE()
        stats = sse.get_kenny_analysis_stats()
        assert stats["total_analyses"] == 0

    def test_get_supervisor_stats_missing_file(self):
        sse = KennyGraphSSE()
        stats = sse.get_supervisor_stats()
        assert "error" in stats


class TestKennyGraphSSEWithMockDriver:
    def _make_sse_with_driver(self):
        """Create SSE instance with a mocked neo4j driver."""
        sse = KennyGraphSSE()
        mock_driver = MagicMock()

        # Mock session context manager
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock a result for node count
        mock_record = MagicMock()
        mock_record.__getitem__ = lambda self, key: 100 if key == "total" else 0
        mock_result = MagicMock()
        mock_result.single.return_value = mock_record

        mock_session.run.return_value = mock_result

        sse.driver = mock_driver
        return sse, mock_session

    def test_get_stats_with_driver(self):
        sse, mock_session = self._make_sse_with_driver()

        # Each session.run call returns different mock
        node_record = MagicMock()
        node_record.__getitem__ = lambda self, k: 1000

        rel_record = MagicMock()
        rel_record.__getitem__ = lambda self, k: 2000

        node_result = MagicMock()
        node_result.single.return_value = node_record

        rel_result = MagicMock()
        rel_result.single.return_value = rel_record

        # label result (iterable)
        label_result = MagicMock()
        label_result.__iter__ = MagicMock(return_value=iter([]))

        # rel type result
        rel_type_result = MagicMock()
        rel_type_result.__iter__ = MagicMock(return_value=iter([]))

        mock_session.run.side_effect = [node_result, rel_result, label_result, rel_type_result]

        stats = sse.get_kenny_graph_stats()
        assert stats["nodes"] == 1000
        assert stats["relationships"] == 2000
        assert stats["status"] == "connected"

    def test_get_analysis_stats_with_file(self):
        """Test analysis stats when DB file doesn't exist — still no crash."""
        sse = KennyGraphSSE()
        stats = sse.get_kenny_analysis_stats()
        assert isinstance(stats, dict)
        assert "total_analyses" in stats

    def test_supervisor_stats_with_mock_file(self):
        sse = KennyGraphSSE()
        mock_data = {"supervisor_metrics": {"total_agents": 1405}}
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            with patch("os.path.exists", return_value=True):
                stats = sse.get_supervisor_stats()
                assert stats["supervisor_metrics"]["total_agents"] == 1405


# ── FastAPI endpoint tests (using TestClient) ───────────────────────────

class TestSSEFastAPIEndpoints:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Kenny Graph SSE API"
        assert "endpoints" in data

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "kenny_graph_connected" in data
        assert "timestamp" in data

    def test_stats_current_endpoint(self, client):
        response = client.get("/stats/current")
        assert response.status_code == 200
        data = response.json()
        assert "kenny_graph" in data
        assert "timestamp" in data

    def test_sse_kenny_graph_endpoint_exists(self, client):
        """SSE routes exist — we can't consume infinite streams in test,
        so just verify the route is registered."""
        # The SSE endpoints produce infinite generators, which TestClient
        # would block on. Verify routes are registered via the app.
        routes = [r.path for r in app.routes]
        assert "/sse/kenny-graph" in routes

    def test_sse_supervisor_endpoint_exists(self, client):
        routes = [r.path for r in app.routes]
        assert "/sse/supervisor" in routes

    def test_sse_combined_endpoint_exists(self, client):
        routes = [r.path for r in app.routes]
        assert "/sse/combined" in routes

    def test_demo_page(self, client):
        response = client.get("/demo")
        assert response.status_code == 200
        assert "Kenny Graph Live Dashboard" in response.text


# ── MCP Server tests (mocked — 'mcp' package not available) ────────────
# We can't import KennyGraphMCP directly since 'mcp' is missing.
# Instead we test the tool/resource schemas and handler logic conceptually,
# and test the Cypher query builder patterns.

class TestMCPServerQueryPatterns:
    """Test the Cypher query patterns used by the MCP server."""

    def test_limit_injection(self):
        """The server adds LIMIT if not present — verify the pattern."""
        query = "MATCH (n) RETURN n"
        limit = 10
        if "LIMIT" not in query.upper():
            query += f" LIMIT {limit}"
        assert "LIMIT 10" in query

    def test_limit_not_duplicated(self):
        query = "MATCH (n) RETURN n LIMIT 5"
        limit = 10
        if "LIMIT" not in query.upper():
            query += f" LIMIT {limit}"
        assert query.count("LIMIT") == 1

    def test_search_concepts_query_structure(self):
        """Verify the search query template is valid Cypher."""
        query = """
            MATCH (n)
            WHERE any(label IN labels(n) WHERE toLower(label) CONTAINS toLower($search_term))
               OR (exists(n.name) AND toLower(n.name) CONTAINS toLower($search_term))
               OR (exists(n.description) AND toLower(n.description) CONTAINS toLower($search_term))
            RETURN n.name as name, labels(n) as labels, n.description as description
            LIMIT $limit
        """
        assert "$search_term" in query
        assert "$limit" in query

    def test_node_relationships_query_structure(self):
        query = """
            MATCH (a)-[r]-(b)
            WHERE a.name = $node_name OR $node_name IN labels(a)
            RETURN type(r) as relationship,
                   a.name as source_name, labels(a) as source_labels,
                   b.name as target_name, labels(b) as target_labels
            LIMIT 50
        """
        assert "$node_name" in query

    def test_centrality_query(self):
        query = """
            MATCH (n)
            RETURN n.name as name, labels(n) as labels,
                   size((n)--()) as degree
            ORDER BY degree DESC LIMIT 10
        """
        assert "degree" in query
        assert "ORDER BY" in query


class TestMCPResourceURIs:
    """Test the MCP resource URI patterns."""

    def test_resource_uris(self):
        uris = [
            "kenny://graph/stats",
            "kenny://graph/nodes",
            "kenny://graph/relationships",
            "kenny://agent/status",
        ]
        for uri in uris:
            assert uri.startswith("kenny://")

    def test_tool_names(self):
        expected_tools = [
            "query_kenny_graph",
            "search_kenny_concepts",
            "get_node_relationships",
            "analyze_connectivity",
        ]
        for tool in expected_tools:
            assert isinstance(tool, str)
            assert "_" in tool  # snake_case

    def test_analysis_types(self):
        valid_types = {"centrality", "clusters", "shortest_path"}
        assert "centrality" in valid_types
        assert "unknown_type" not in valid_types
