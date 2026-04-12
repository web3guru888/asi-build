"""
Tests for KGPathfinder temporal edge filtering (Issue #51).

Verifies that the ``valid_at`` parameter on ``find_path()`` correctly
filters edges by their temporal validity window, only traversing triples
whose ``valid_at <= t AND (invalid_at IS NULL OR invalid_at > t)``.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from asi_build.knowledge_graph.temporal_kg import TemporalKnowledgeGraph
from asi_build.knowledge_graph.pathfinder import KGPathfinder


# ── Helpers ────────────────────────────────────────────────────────────


def _iso(dt: Optional[datetime] = None) -> str:
    """ISO-8601 UTC timestamp."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_time(year: int = 2025, month: int = 1, day: int = 1,
               hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


T_2024 = _iso(_make_time(2024, 1, 1))
T_2025_JAN = _iso(_make_time(2025, 1, 1))
T_2025_JUN = _iso(_make_time(2025, 6, 1))
T_2025_DEC = _iso(_make_time(2025, 12, 1))
T_2026 = _iso(_make_time(2026, 1, 1))
T_2027 = _iso(_make_time(2027, 1, 1))


@pytest.fixture()
def kg(tmp_path):
    """Fresh in-memory KG (uses tmp_path for the DB file)."""
    db_path = str(tmp_path / "test.db")
    kg = TemporalKnowledgeGraph(db_path=db_path)
    return kg


@pytest.fixture()
def pf(kg):
    """Pathfinder wrapping the KG fixture."""
    return KGPathfinder(kg)


def _add_triple(kg, subj, pred, obj, *,
                valid_at=None, invalid_at=None,
                confidence=0.9, source="test"):
    """Low-level triple insert bypassing some TemporalKG sugar."""
    triple_id = str(uuid.uuid4())[:8]
    now = _iso()
    kg._conn.execute(
        """INSERT INTO triples
           (id, subject, predicate, object, source, confidence,
            valid_at, created_at, invalid_at, statement_type, temporal_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'fact', 'dynamic')""",
        (triple_id, subj.lower(), pred, obj.lower(), source,
         confidence, valid_at, now, invalid_at),
    )
    kg._conn.commit()
    return triple_id


# ── Tests: basic temporal filtering ──────────────────────────────────


class TestTemporalFilterBasics:
    """Basic temporal filtering on find_path()."""

    def test_no_filter_default_behaviour(self, kg, pf):
        """Without valid_at, only invalid_at IS NULL filter applies."""
        _add_triple(kg, "a", "causes", "b", valid_at=T_2025_JAN)
        result = pf.find_path("a", "b")
        assert result["complete"] is True
        assert result["path"] == ["a", "b"]

    def test_filter_includes_valid_edge(self, kg, pf):
        """Edge valid at query time is traversed."""
        _add_triple(kg, "a", "causes", "b", valid_at=T_2025_JAN)
        result = pf.find_path("a", "b", valid_at=T_2025_JUN)
        assert result["complete"] is True
        assert result["path"] == ["a", "b"]

    def test_filter_excludes_future_edge(self, kg, pf):
        """Edge whose valid_at is AFTER query time is NOT traversed."""
        _add_triple(kg, "a", "causes", "b", valid_at=T_2026)
        result = pf.find_path("a", "b", valid_at=T_2025_JUN)
        assert result["complete"] is False

    def test_filter_excludes_expired_edge(self, kg, pf):
        """Edge whose invalid_at is BEFORE query time is NOT traversed."""
        _add_triple(kg, "a", "causes", "b",
                    valid_at=T_2024, invalid_at=T_2025_JAN)
        result = pf.find_path("a", "b", valid_at=T_2025_JUN)
        assert result["complete"] is False

    def test_filter_includes_edge_at_boundary(self, kg, pf):
        """Edge where valid_at == query time is included."""
        _add_triple(kg, "a", "causes", "b", valid_at=T_2025_JUN)
        result = pf.find_path("a", "b", valid_at=T_2025_JUN)
        assert result["complete"] is True

    def test_filter_excludes_edge_at_invalidation_boundary(self, kg, pf):
        """Edge where invalid_at == query time is excluded (strict <, not <=)."""
        _add_triple(kg, "a", "causes", "b",
                    valid_at=T_2024, invalid_at=T_2025_JUN)
        result = pf.find_path("a", "b", valid_at=T_2025_JUN)
        assert result["complete"] is False

    def test_null_valid_at_triple_always_traversed(self, kg, pf):
        """Triple with NULL valid_at is traversable at any query time."""
        _add_triple(kg, "a", "causes", "b", valid_at=None)
        result = pf.find_path("a", "b", valid_at=T_2025_JUN)
        assert result["complete"] is True

    def test_null_invalid_at_means_still_valid(self, kg, pf):
        """Triple with NULL invalid_at (never expired) is still valid."""
        _add_triple(kg, "a", "causes", "b",
                    valid_at=T_2024, invalid_at=None)
        result = pf.find_path("a", "b", valid_at=T_2027)
        assert result["complete"] is True


# ── Tests: multi-edge scenarios ──────────────────────────────────────


class TestTemporalMultiEdge:
    """Scenarios with multiple edges and temporal mixtures."""

    def test_path_exists_without_filter_but_not_with(self, kg, pf):
        """A→B→C path exists without filter; B→C is future → fails with filter."""
        _add_triple(kg, "a", "causes", "b", valid_at=T_2024)
        _add_triple(kg, "b", "causes", "c", valid_at=T_2026)  # future

        without = pf.find_path("a", "c")
        assert without["complete"] is True

        with_filter = pf.find_path("a", "c", valid_at=T_2025_JUN)
        assert with_filter["complete"] is False

    def test_path_changes_with_different_valid_at(self, kg, pf):
        """Different valid_at selects different routes.

        Graph:
          A --[2024-2025]--> B --[2024-∞]--> D
          A --[2025-∞]-----> C --[2025-∞]--> D

        At 2024-06-01: only A→B→D available
        At 2025-06-01: both routes available (A→B→D and A→C→D)
        """
        _add_triple(kg, "a", "causes", "b",
                    valid_at=_iso(_make_time(2024, 1, 1)),
                    invalid_at=_iso(_make_time(2025, 1, 1)))
        _add_triple(kg, "b", "causes", "d",
                    valid_at=_iso(_make_time(2024, 1, 1)))
        _add_triple(kg, "a", "causes", "c",
                    valid_at=_iso(_make_time(2025, 1, 1)))
        _add_triple(kg, "c", "causes", "d",
                    valid_at=_iso(_make_time(2025, 1, 1)))

        early = pf.find_path("a", "d",
                             valid_at=_iso(_make_time(2024, 6, 1)))
        assert early["complete"] is True
        assert "b" in early["path"]  # must go through B
        assert "c" not in early["path"]

        late = pf.find_path("a", "d",
                            valid_at=_iso(_make_time(2025, 6, 1)))
        assert late["complete"] is True
        # A→B no longer valid, so must go through C
        assert "c" in late["path"]
        assert "b" not in late["path"]

    def test_mixed_valid_and_invalid_neighbours(self, kg, pf):
        """Some neighbours are valid, some expired — only valid ones appear."""
        _add_triple(kg, "hub", "causes", "alive",
                    valid_at=T_2024)
        _add_triple(kg, "hub", "causes", "expired",
                    valid_at=T_2024, invalid_at=T_2025_JAN)
        _add_triple(kg, "hub", "causes", "future",
                    valid_at=T_2026)

        result = pf.find_path("hub", "alive", valid_at=T_2025_JUN)
        assert result["complete"] is True

        result = pf.find_path("hub", "expired", valid_at=T_2025_JUN)
        assert result["complete"] is False

        result = pf.find_path("hub", "future", valid_at=T_2025_JUN)
        assert result["complete"] is False

    def test_three_hop_path_all_valid(self, kg, pf):
        """A→B→C→D — all edges valid at query time."""
        for s, o in [("a", "b"), ("b", "c"), ("c", "d")]:
            _add_triple(kg, s, "causes", o, valid_at=T_2024)

        result = pf.find_path("a", "d", valid_at=T_2025_JUN)
        assert result["complete"] is True
        assert result["path"] == ["a", "b", "c", "d"]
        assert result["hops"] == 3

    def test_three_hop_path_middle_expired(self, kg, pf):
        """A→B→C→D — B→C expired → no path."""
        _add_triple(kg, "a", "causes", "b", valid_at=T_2024)
        _add_triple(kg, "b", "causes", "c",
                    valid_at=T_2024, invalid_at=T_2025_JAN)
        _add_triple(kg, "c", "causes", "d", valid_at=T_2024)

        result = pf.find_path("a", "d", valid_at=T_2025_JUN)
        assert result["complete"] is False


# ── Tests: entity existence temporal filtering ───────────────────────


class TestTemporalEntityExists:
    """The _entity_exists check respects temporal filtering."""

    def test_entity_not_exist_if_all_triples_expired(self, kg, pf):
        """If every triple mentioning an entity is expired, entity 'does not exist'."""
        _add_triple(kg, "ghost", "causes", "something",
                    valid_at=T_2024, invalid_at=T_2025_JAN)
        result = pf.find_path("ghost", "something", valid_at=T_2025_JUN)
        assert result["complete"] is False

    def test_entity_exists_without_filter_even_if_expired(self, kg, pf):
        """Without filter, expired entities still show up (backward compat)."""
        _add_triple(kg, "ghost", "causes", "something",
                    valid_at=T_2024, invalid_at=T_2025_JAN)
        # No valid_at filter — entity_exists should still find it
        # (the old behaviour: no invalid_at filter in _entity_exists)
        result = pf.find_path("ghost", "something")
        # Path won't complete because _get_neighbours filters invalid_at IS NULL,
        # but entity_exists should pass.  Actually, the default _get_neighbours
        # also filters invalid_at IS NULL, so the hop itself is blocked.
        # What matters is that entity_exists returns True without the temporal filter.
        assert result["complete"] is False
        # But the fact we got beyond the "entity not found" stage means
        # _entity_exists returned True.  Check nodes_explored > 0 to confirm
        # the search was attempted.
        assert result["nodes_explored"] >= 1

    def test_start_entity_future_only(self, kg, pf):
        """Start entity's only triple is in the future → entity does not exist at query time."""
        _add_triple(kg, "future_start", "causes", "b", valid_at=T_2026)
        result = pf.find_path("future_start", "b", valid_at=T_2025_JUN)
        assert result["complete"] is False
        assert result["nodes_explored"] == 0  # search never started

    def test_goal_entity_future_only(self, kg, pf):
        """Goal entity's only triple is in the future → cannot reach it."""
        _add_triple(kg, "a", "causes", "b", valid_at=T_2024)
        _add_triple(kg, "b", "causes", "future_goal", valid_at=T_2026)
        result = pf.find_path("a", "future_goal", valid_at=T_2025_JUN)
        assert result["complete"] is False


# ── Tests: edge-cost & best-edge temporal ────────────────────────────


class TestTemporalBestEdge:
    """_get_best_edge respects temporal filter."""

    def test_best_edge_picks_valid_lower_confidence(self, kg, pf):
        """When the highest-confidence edge is expired, the pathfinder
        uses the lower-confidence but temporally-valid edge."""
        # High-confidence but expired
        _add_triple(kg, "x", "causes", "y",
                    valid_at=T_2024, invalid_at=T_2025_JAN,
                    confidence=0.99)
        # Lower confidence but still valid
        _add_triple(kg, "x", "related_to", "y",
                    valid_at=T_2024,
                    confidence=0.5)

        result = pf.find_path("x", "y", valid_at=T_2025_JUN)
        assert result["complete"] is True
        assert len(result["edges"]) == 1
        assert result["edges"][0]["predicate"] == "related_to"

    def test_no_valid_edge_between_connected_nodes(self, kg, pf):
        """Nodes are connected but all edges expired → no path."""
        _add_triple(kg, "x", "causes", "y",
                    valid_at=T_2024, invalid_at=T_2025_JAN)
        _add_triple(kg, "x", "related_to", "y",
                    valid_at=T_2024, invalid_at=T_2025_JAN)
        result = pf.find_path("x", "y", valid_at=T_2025_JUN)
        assert result["complete"] is False


# ── Tests: backward compatibility ────────────────────────────────────


class TestBackwardCompatibility:
    """Existing behaviour is preserved when valid_at=None."""

    def test_none_valid_at_default(self, kg, pf):
        """Calling find_path without valid_at works exactly as before."""
        _add_triple(kg, "a", "causes", "b", valid_at=T_2024)
        _add_triple(kg, "b", "causes", "c", valid_at=T_2025_JAN)
        result = pf.find_path("a", "c")
        assert result["complete"] is True
        assert result["hops"] == 2

    def test_trivial_same_node(self, kg, pf):
        """Same start/goal still returns immediately."""
        _add_triple(kg, "x", "causes", "y", valid_at=T_2024)
        result = pf.find_path("x", "x", valid_at=T_2025_JUN)
        assert result["complete"] is True
        assert result["path"] == ["x"]
        assert result["hops"] == 0

    def test_empty_result_missing_entities(self, kg, pf):
        """Missing entities produce empty result regardless of filter."""
        result = pf.find_path("nonexistent", "also_missing", valid_at=T_2025_JUN)
        assert result["complete"] is False
        assert result["path"] == []

    def test_max_hops_respected_with_filter(self, kg, pf):
        """max_hops limit still applies when temporal filter is active."""
        # Chain: a→b→c→d→e (4 hops)
        for s, o in [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")]:
            _add_triple(kg, s, "causes", o, valid_at=T_2024)

        result = pf.find_path("a", "e", max_hops=3, valid_at=T_2025_JUN)
        assert result["complete"] is False  # 4 hops needed, only 3 allowed

        result = pf.find_path("a", "e", max_hops=4, valid_at=T_2025_JUN)
        assert result["complete"] is True


# ── Tests: temporal windows ──────────────────────────────────────────


class TestTemporalWindows:
    """Tests for overlapping and adjacent temporal windows."""

    def test_edge_valid_window_before_query(self, kg, pf):
        """Edge was valid 2024-01 to 2025-01 but query is 2025-06 → expired."""
        _add_triple(kg, "a", "causes", "b",
                    valid_at=T_2024, invalid_at=T_2025_JAN)
        result = pf.find_path("a", "b", valid_at=T_2025_JUN)
        assert result["complete"] is False

    def test_edge_valid_window_containing_query(self, kg, pf):
        """Edge valid 2024-01 to 2026-01, query 2025-06 → valid."""
        _add_triple(kg, "a", "causes", "b",
                    valid_at=T_2024, invalid_at=T_2026)
        result = pf.find_path("a", "b", valid_at=T_2025_JUN)
        assert result["complete"] is True

    def test_edge_valid_window_after_query(self, kg, pf):
        """Edge valid from 2026 onward, query 2025-06 → not yet valid."""
        _add_triple(kg, "a", "causes", "b", valid_at=T_2026)
        result = pf.find_path("a", "b", valid_at=T_2025_JUN)
        assert result["complete"] is False

    def test_successive_edges_different_windows(self, kg, pf):
        """Two edges for same pair in different windows — only one valid at a time.

        Edge 1: A→B valid 2024-01 to 2025-01 (predicate: caused_by)
        Edge 2: A→B valid 2025-06 onward      (predicate: causes)
        """
        _add_triple(kg, "a", "caused_by", "b",
                    valid_at=T_2024, invalid_at=T_2025_JAN,
                    confidence=0.8)
        _add_triple(kg, "a", "causes", "b",
                    valid_at=T_2025_JUN,
                    confidence=0.9)

        # At 2024-06: only first edge
        r1 = pf.find_path("a", "b",
                          valid_at=_iso(_make_time(2024, 6, 1)))
        assert r1["complete"] is True
        assert r1["edges"][0]["predicate"] == "caused_by"

        # At 2025-03: gap — neither edge valid
        r2 = pf.find_path("a", "b",
                          valid_at=_iso(_make_time(2025, 3, 1)))
        assert r2["complete"] is False

        # At 2025-12: only second edge
        r3 = pf.find_path("a", "b", valid_at=T_2025_DEC)
        assert r3["complete"] is True
        assert r3["edges"][0]["predicate"] == "causes"
