"""
Tests for the ASI:BUILD Knowledge Graph module.

Covers:
- Triple CRUD (add, get, invalidate, update confidence)
- Contradiction detection and resolution
- Temporal history and point-in-time queries
- Entity relations
- Statistics
- Pheromone deposit, decay, modifier, and path deposit
- Provenance tracking
- Text search
- A* pathfinding (basic, disconnected, with embedding fn, pheromone-aware)
"""

import time

import pytest

from asi_build.knowledge_graph.temporal_kg import TemporalKnowledgeGraph
from asi_build.knowledge_graph.pathfinder import KGPathfinder


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def kg():
    """Fresh in-memory KG for each test."""
    return TemporalKnowledgeGraph(db_path=":memory:")


@pytest.fixture
def populated_kg(kg):
    """KG pre-loaded with a small graph for relationship tests.

    Graph:
        temperature --causes--> ice_melting (conf 0.9)
        ice_melting --causes--> sea_level_rise (conf 0.85)
        co2 --correlated_with--> temperature (conf 0.8)
        sea_level_rise --affects--> coastal_cities (conf 0.75)
    """
    kg.add_triple("temperature", "causes", "ice_melting",
                   source="climate_study", confidence=0.9, agent="researcher_1")
    kg.add_triple("ice_melting", "causes", "sea_level_rise",
                   source="climate_study", confidence=0.85, agent="researcher_1")
    kg.add_triple("co2", "correlated_with", "temperature",
                   source="ipcc_ar6", confidence=0.8, agent="researcher_2")
    kg.add_triple("sea_level_rise", "affects", "coastal_cities",
                   source="impact_analysis", confidence=0.75, agent="researcher_2")
    return kg


# ── Triple CRUD ────────────────────────────────────────────────────────

class TestTripleCRUD:
    def test_add_and_get_triple(self, kg):
        tid = kg.add_triple("Sun", "causes", "daylight", confidence=0.95)
        assert isinstance(tid, str)
        assert len(tid) == 12

        triples = kg.get_triples(subject="Sun")
        assert len(triples) == 1
        assert triples[0]["subject"] == "sun"  # normalised
        assert triples[0]["predicate"] == "causes"
        assert triples[0]["object"] == "daylight"
        assert triples[0]["confidence"] == 0.95

    def test_get_by_predicate(self, kg):
        kg.add_triple("A", "causes", "B")
        kg.add_triple("C", "correlated_with", "D")
        assert len(kg.get_triples(predicate="causes")) == 1
        assert len(kg.get_triples(predicate="correlated_with")) == 1

    def test_get_by_object(self, kg):
        kg.add_triple("A", "causes", "B")
        kg.add_triple("C", "causes", "B")
        triples = kg.get_triples(object="B")
        assert len(triples) == 2

    def test_invalidate_triple(self, kg):
        tid = kg.add_triple("A", "causes", "B")
        kg.invalidate_triple(tid, reason="Disproven", agent="reviewer")

        # Current-only query should exclude it
        assert len(kg.get_triples(subject="A", current_only=True)) == 0
        # Including invalidated should show it
        assert len(kg.get_triples(subject="A", current_only=False)) == 1

    def test_update_confidence(self, kg):
        tid = kg.add_triple("A", "causes", "B", confidence=0.5)
        kg.update_confidence(tid, 0.9, reason="New evidence", agent="updater")

        triples = kg.get_triples(subject="A")
        assert triples[0]["confidence"] == 0.9

    def test_normalisation(self, kg):
        """Entity names are normalised to lowercase with underscores."""
        kg.add_triple("Global Temperature", "causes", "Ice Sheet Melting")
        triples = kg.get_triples(subject="global_temperature")
        assert len(triples) == 1
        assert triples[0]["object"] == "ice_sheet_melting"


# ── Contradiction Detection ────────────────────────────────────────────

class TestContradictions:
    def test_detect_contradiction(self, kg):
        kg.add_triple("earth", "orbits", "sun", confidence=0.99)
        conflicts = kg.detect_contradictions(
            "earth", "orbits", "mars", 0.5,
        )
        assert len(conflicts) == 1
        assert conflicts[0]["object"] == "sun"
        assert conflicts[0]["dominated"] is False  # 0.5 < 0.99

    def test_detect_no_contradiction(self, kg):
        kg.add_triple("earth", "orbits", "sun", confidence=0.99)
        # Same object — not a contradiction
        conflicts = kg.detect_contradictions(
            "earth", "orbits", "sun", 0.8,
        )
        assert len(conflicts) == 0

    def test_resolve_contradiction_invalidates_weaker(self, kg):
        kg.add_triple("planet_x", "orbits", "star_a", confidence=0.4)

        result = kg.resolve_contradictions(
            subject="planet_x",
            predicate="orbits",
            new_object="star_b",
            new_confidence=0.9,
            agent="hypothesis_tester",
        )

        assert len(result["invalidated"]) == 1
        assert len(result["kept"]) == 0
        assert result["new_triple_id"]

        # The old triple should be invalidated
        active = kg.get_triples(subject="planet_x", current_only=True)
        assert len(active) == 1
        assert active[0]["object"] == "star_b"

    def test_resolve_contradiction_keeps_stronger(self, kg):
        kg.add_triple("planet_x", "orbits", "star_a", confidence=0.95)

        result = kg.resolve_contradictions(
            subject="planet_x",
            predicate="orbits",
            new_object="star_b",
            new_confidence=0.3,
        )

        # Weaker new triple is still added but doesn't invalidate the old
        assert len(result["invalidated"]) == 0
        assert len(result["kept"]) == 1

        # Both should be active
        active = kg.get_triples(subject="planet_x", current_only=True)
        assert len(active) == 2


# ── Temporal Queries ───────────────────────────────────────────────────

class TestTemporalQueries:
    def test_temporal_history(self, kg):
        # Two versions of the same relationship
        kg.add_triple("earth", "temperature", "15C", confidence=0.8,
                       valid_at="2020-01-01T00:00:00Z")
        kg.add_triple("earth", "temperature", "15.5C", confidence=0.9,
                       valid_at="2025-01-01T00:00:00Z")

        history = kg.get_temporal_history("earth", "temperature")
        assert len(history) == 2
        # Should be ordered by created_at ascending
        assert history[0]["valid_at"] == "2020-01-01T00:00:00Z"
        assert history[1]["valid_at"] == "2025-01-01T00:00:00Z"

    def test_get_valid_at_point_in_time(self, kg):
        tid1 = kg.add_triple("earth", "status", "warming",
                              valid_at="2000-01-01T00:00:00Z")
        # Invalidate after a while
        kg.invalidate_triple(tid1)

        kg.add_triple("earth", "status", "critical_warming",
                       valid_at="2025-01-01T00:00:00Z")

        # At 2010, only the first should be valid (it wasn't invalidated yet
        # by that time — but since invalidation happened instantly in test,
        # use a point before the actual invalidation timestamp)
        # For the test we just check that valid_at queries work
        valid_2025 = kg.get_valid_at("2025-06-01T00:00:00Z")
        objects = {t["object"] for t in valid_2025}
        assert "critical_warming" in objects

    def test_get_valid_at_excludes_not_yet_valid(self, kg):
        kg.add_triple("future_event", "happens_at", "2030",
                       valid_at="2030-01-01T00:00:00Z")
        valid_now = kg.get_valid_at("2025-01-01T00:00:00Z")
        future_ids = [t for t in valid_now if t["subject"] == "future_event"]
        assert len(future_ids) == 0


# ── Entity Relations ───────────────────────────────────────────────────

class TestEntityRelations:
    def test_get_entity_relations(self, populated_kg):
        rels = populated_kg.get_entity_relations("temperature")
        # temperature is subject in 1 triple, object in 1 triple
        assert len(rels) == 2
        predicates = {r["predicate"] for r in rels}
        assert "causes" in predicates
        assert "correlated_with" in predicates

    def test_entity_relations_bidirectional(self, populated_kg):
        rels = populated_kg.get_entity_relations("ice_melting")
        # ice_melting: object of "temperature causes ice_melting"
        #              subject of "ice_melting causes sea_level_rise"
        assert len(rels) == 2


# ── Statistics ─────────────────────────────────────────────────────────

class TestStatistics:
    def test_empty_kg_stats(self, kg):
        stats = kg.get_statistics()
        assert stats["total_triples"] == 0
        assert stats["active_triples"] == 0
        assert stats["unique_entities"] == 0

    def test_populated_stats(self, populated_kg):
        stats = populated_kg.get_statistics()
        assert stats["total_triples"] == 4
        assert stats["active_triples"] == 4
        assert stats["invalidated_triples"] == 0
        assert stats["unique_predicates"] >= 2
        assert stats["unique_entities"] == 5  # temp, ice, sea, co2, coastal
        assert 0.0 < stats["avg_confidence"] <= 1.0

    def test_stats_reflect_invalidation(self, kg):
        tid = kg.add_triple("A", "rel", "B")
        kg.add_triple("C", "rel", "D")
        kg.invalidate_triple(tid)

        stats = kg.get_statistics()
        assert stats["total_triples"] == 2
        assert stats["active_triples"] == 1
        assert stats["invalidated_triples"] == 1


# ── Pheromones ─────────────────────────────────────────────────────────

class TestPheromones:
    def test_deposit_and_read(self, kg):
        tid = kg.add_triple("A", "causes", "B")
        kg.deposit_pheromone(tid, "success", 1.0)

        triples = kg.get_triples(subject="A")
        assert triples[0]["pheromone_success"] == 1.0
        assert triples[0]["pheromone_traversal"] == 0.0

    def test_deposit_accumulates(self, kg):
        tid = kg.add_triple("A", "causes", "B")
        kg.deposit_pheromone(tid, "traversal", 0.5)
        kg.deposit_pheromone(tid, "traversal", 0.3)

        triples = kg.get_triples(subject="A")
        assert abs(triples[0]["pheromone_traversal"] - 0.8) < 1e-6

    def test_invalid_channel_raises(self, kg):
        tid = kg.add_triple("A", "causes", "B")
        with pytest.raises(ValueError, match="Invalid pheromone channel"):
            kg.deposit_pheromone(tid, "invalid_channel", 1.0)

    def test_decay(self, kg):
        tid = kg.add_triple("A", "causes", "B")
        kg.deposit_pheromone(tid, "recency", 1.0)

        affected = kg.decay_pheromones("recency", rate=0.15)
        assert affected == 1

        triples = kg.get_triples(subject="A")
        assert abs(triples[0]["pheromone_recency"] - 0.85) < 1e-6

    def test_pheromone_modifier(self, kg):
        tid = kg.add_triple("A", "causes", "B")
        # No pheromones → modifier should be 1.0
        assert kg.get_pheromone_modifier(tid) == 1.0

        # Max out all channels
        kg.deposit_pheromone(tid, "success", 2.0)
        kg.deposit_pheromone(tid, "traversal", 2.0)
        kg.deposit_pheromone(tid, "recency", 2.0)

        modifier = kg.get_pheromone_modifier(tid)
        # modifier = 1.0 - (0.5*1 + 0.3*1 + 0.2*1) * 0.5 = 1.0 - 0.5 = 0.5
        assert abs(modifier - 0.5) < 1e-6

    def test_path_deposit(self, kg):
        t1 = kg.add_triple("A", "causes", "B")
        t2 = kg.add_triple("B", "causes", "C")
        t3 = kg.add_triple("C", "causes", "D")

        kg.deposit_path_pheromone([t1, t2, t3], channel="success", total_amount=1.0)

        triples_a = kg.get_triples(subject="A")
        triples_b = kg.get_triples(subject="B", predicate="causes", object="C")
        triples_c = kg.get_triples(subject="C")

        # First triple should get more pheromone than last
        assert triples_a[0]["pheromone_success"] > triples_c[0]["pheromone_success"]

    def test_pheromone_stats(self, kg):
        kg.add_triple("A", "causes", "B")
        tid = kg.add_triple("C", "causes", "D")
        kg.deposit_pheromone(tid, "success", 0.5)

        stats = kg.get_pheromone_stats()
        assert stats["success"]["max"] == 0.5
        assert stats["success"]["nonzero_count"] == 1


# ── Provenance ─────────────────────────────────────────────────────────

class TestProvenance:
    def test_provenance_recorded_on_add(self, kg):
        tid = kg.add_triple("A", "causes", "B", agent="agent_1", source="study_x")
        prov = kg.get_provenance(tid)
        assert len(prov) == 1
        assert prov[0]["agent"] == "agent_1"
        assert prov[0]["source"] == "study_x"
        assert prov[0]["reason"] == "Initial assertion"

    def test_provenance_on_invalidation(self, kg):
        tid = kg.add_triple("A", "causes", "B")
        kg.invalidate_triple(tid, reason="Disproven", agent="reviewer")

        prov = kg.get_provenance(tid)
        assert len(prov) == 2
        assert prov[1]["confidence"] == 0.0
        assert prov[1]["reason"] == "Disproven"

    def test_provenance_on_confidence_update(self, kg):
        tid = kg.add_triple("A", "causes", "B", confidence=0.5)
        kg.update_confidence(tid, 0.9, reason="Replicated", agent="replicator")

        prov = kg.get_provenance(tid)
        assert len(prov) == 2
        assert prov[1]["confidence"] == 0.9


# ── Text Search ────────────────────────────────────────────────────────

class TestSearch:
    def test_search_by_subject(self, populated_kg):
        results = populated_kg.search_triples("temperature")
        assert len(results) >= 1

    def test_search_by_predicate(self, populated_kg):
        results = populated_kg.search_triples("causes")
        assert len(results) >= 2

    def test_search_no_match(self, populated_kg):
        results = populated_kg.search_triples("quantum_entanglement")
        assert len(results) == 0


# ── Pathfinder ─────────────────────────────────────────────────────────

class TestPathfinder:
    def test_basic_path(self, populated_kg):
        pf = KGPathfinder(populated_kg)
        result = pf.find_path("temperature", "sea_level_rise")

        assert result["complete"] is True
        assert result["hops"] == 2
        assert result["path"] == ["temperature", "ice_melting", "sea_level_rise"]
        assert result["cost"] > 0
        assert len(result["edges"]) == 2

    def test_direct_path(self, populated_kg):
        pf = KGPathfinder(populated_kg)
        result = pf.find_path("temperature", "ice_melting")

        assert result["complete"] is True
        assert result["hops"] == 1

    def test_same_entity(self, populated_kg):
        pf = KGPathfinder(populated_kg)
        result = pf.find_path("temperature", "temperature")

        assert result["complete"] is True
        assert result["hops"] == 0
        assert result["cost"] == 0.0

    def test_no_path_disconnected(self, kg):
        """Two disconnected subgraphs — no path should exist."""
        kg.add_triple("A", "causes", "B")
        kg.add_triple("X", "causes", "Y")

        pf = KGPathfinder(kg)
        result = pf.find_path("A", "Y")

        assert result["complete"] is False
        assert result["path"] == []

    def test_nonexistent_entity(self, kg):
        pf = KGPathfinder(kg)
        result = pf.find_path("nonexistent", "also_nonexistent")

        assert result["complete"] is False

    def test_path_with_embedding_fn(self, populated_kg):
        """A* with a simple mock embedding function."""
        # Simple embeddings: hash-based deterministic vectors
        def mock_embedding(entity: str):
            import hashlib
            h = hashlib.md5(entity.encode()).hexdigest()
            return [int(c, 16) / 15.0 for c in h]

        pf = KGPathfinder(populated_kg)
        result = pf.find_path(
            "co2", "coastal_cities",
            max_hops=10,
            embedding_fn=mock_embedding,
        )

        assert result["complete"] is True
        # co2 → temperature → ice_melting → sea_level_rise → coastal_cities
        assert result["hops"] >= 2

    def test_pheromone_affects_path_cost(self, populated_kg):
        """Depositing pheromones on a path should reduce its cost."""
        pf = KGPathfinder(populated_kg)

        # Measure cost without pheromones
        result_before = pf.find_path("temperature", "sea_level_rise")
        cost_before = result_before["cost"]

        # Deposit pheromones on the path's edges
        for edge in result_before["edges"]:
            if edge["triple_id"]:
                populated_kg.deposit_pheromone(edge["triple_id"], "success", 2.0)
                populated_kg.deposit_pheromone(edge["triple_id"], "traversal", 2.0)

        result_after = pf.find_path("temperature", "sea_level_rise")
        cost_after = result_after["cost"]

        assert cost_after < cost_before

    def test_max_hops_limit(self, kg):
        """Path longer than max_hops should not be found."""
        # Create a chain: A → B → C → D → E → F
        kg.add_triple("A", "causes", "B")
        kg.add_triple("B", "causes", "C")
        kg.add_triple("C", "causes", "D")
        kg.add_triple("D", "causes", "E")
        kg.add_triple("E", "causes", "F")

        pf = KGPathfinder(kg)

        # max_hops=2 should not reach F from A (needs 5 hops)
        result = pf.find_path("A", "F", max_hops=2)
        assert result["complete"] is False

        # max_hops=6 should find it
        result = pf.find_path("A", "F", max_hops=6)
        assert result["complete"] is True
        assert result["hops"] == 5

    def test_bidirectional_traversal(self, kg):
        """Pathfinder should traverse triples in both directions."""
        kg.add_triple("A", "causes", "B")
        kg.add_triple("C", "causes", "B")

        pf = KGPathfinder(kg)
        # A → B ← C  (B→C via reverse traversal)
        result = pf.find_path("A", "C")
        assert result["complete"] is True
        assert result["hops"] == 2
        assert result["path"] == ["a", "b", "c"]
