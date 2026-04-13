"""Tests for Phase 17.1 — TemporalGraph with Allen interval relations (#434).

12 test targets covering:
  - Node add / duplicate / eviction
  - Edge creation / unknown-node / cycle detection
  - Successor / predecessor queries
  - DAG consistency check
  - Prune (stale nodes + dangling edges)
  - NullTemporalGraph no-ops
"""

from __future__ import annotations

import pytest

from asi_build.temporal import (
    AllenRelation,
    DictTemporalGraph,
    NullTemporalGraph,
    TemporalEdge,
    TemporalGraph,
    TemporalGraphConfig,
    TemporalNode,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node(nid: str, ts: int = 0, **snapshot: object) -> TemporalNode:
    return TemporalNode(nid, ts, dict(snapshot), frozenset())


def _edge(
    src: str,
    dst: str,
    rel: AllenRelation = AllenRelation.BEFORE,
    dur: int = 0,
) -> TemporalEdge:
    return TemporalEdge(src, dst, rel, dur)


# ---------------------------------------------------------------------------
# 1. test_add_node_increments_counter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_node_increments_counter() -> None:
    g = DictTemporalGraph()
    await g.add_node(_node("a", 1))
    await g.add_node(_node("b", 2))
    s = g.stats()
    assert s["nodes"] == 2
    assert s["nodes_added_total"] == 2


# ---------------------------------------------------------------------------
# 2. test_duplicate_node_ignored
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_node_ignored() -> None:
    g = DictTemporalGraph()
    await g.add_node(_node("a", 1))
    await g.add_node(_node("a", 1))          # duplicate
    s = g.stats()
    assert s["nodes"] == 1
    assert s["nodes_added_total"] == 1        # counter should NOT increment


# ---------------------------------------------------------------------------
# 3. test_max_nodes_evicts_oldest
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_max_nodes_evicts_oldest() -> None:
    cfg = TemporalGraphConfig(max_nodes=3)
    g = DictTemporalGraph(cfg)
    for i in range(4):
        await g.add_node(_node(str(i), ts=i))
    s = g.stats()
    assert s["nodes"] == 3                    # oldest ("0") evicted
    succs = await g.get_successors("0")
    assert succs == []                        # node "0" is gone


# ---------------------------------------------------------------------------
# 4. test_add_edge_unknown_node_raises
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_edge_unknown_node_raises() -> None:
    g = DictTemporalGraph()
    await g.add_node(_node("a"))
    with pytest.raises(KeyError, match="Unknown node"):
        await g.add_edge(_edge("a", "missing"))


# ---------------------------------------------------------------------------
# 5. test_add_edge_creates_allen_relation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_edge_creates_allen_relation() -> None:
    g = DictTemporalGraph()
    n1 = TemporalNode("a", 1_000_000_000, {}, frozenset())
    n2 = TemporalNode("b", 2_000_000_000, {}, frozenset())
    await g.add_node(n1)
    await g.add_node(n2)
    edge = TemporalEdge("a", "b", AllenRelation.BEFORE, 1_000_000_000)
    await g.add_edge(edge)
    succs = await g.get_successors("a")
    assert len(succs) == 1
    assert succs[0].node_id == "b"
    assert g.stats()["edges"] == 1


# ---------------------------------------------------------------------------
# 6. test_cycle_detection_raises
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cycle_detection_raises() -> None:
    g = DictTemporalGraph()
    for nid in ["x", "y", "z"]:
        await g.add_node(TemporalNode(nid, 0, {}, frozenset()))
    await g.add_edge(TemporalEdge("x", "y", AllenRelation.BEFORE, 0))
    await g.add_edge(TemporalEdge("y", "z", AllenRelation.BEFORE, 0))
    with pytest.raises(ValueError, match="cycle"):
        await g.add_edge(TemporalEdge("z", "x", AllenRelation.BEFORE, 0))
    assert g.stats()["cycle_rejections"] == 1
    # Graph should still be consistent after the rejected edge
    assert await g.check_consistency() is True


# ---------------------------------------------------------------------------
# 7. test_get_successors_returns_correct_nodes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_successors_returns_correct_nodes() -> None:
    g = DictTemporalGraph()
    for nid in "abcd":
        await g.add_node(_node(nid))
    await g.add_edge(_edge("a", "b"))
    await g.add_edge(_edge("a", "c"))
    succs = await g.get_successors("a")
    ids = {n.node_id for n in succs}
    assert ids == {"b", "c"}
    # "d" has no successors
    assert await g.get_successors("d") == []


# ---------------------------------------------------------------------------
# 8. test_get_predecessors_returns_correct_nodes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_predecessors_returns_correct_nodes() -> None:
    g = DictTemporalGraph()
    for nid in "abc":
        await g.add_node(_node(nid))
    await g.add_edge(_edge("a", "c"))
    await g.add_edge(_edge("b", "c"))
    preds = await g.get_predecessors("c")
    ids = {n.node_id for n in preds}
    assert ids == {"a", "b"}
    # "a" has no predecessors
    assert await g.get_predecessors("a") == []


# ---------------------------------------------------------------------------
# 9. test_check_consistency_clean_dag
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_consistency_clean_dag() -> None:
    g = DictTemporalGraph()
    for nid in "abcde":
        await g.add_node(_node(nid))
    await g.add_edge(_edge("a", "b"))
    await g.add_edge(_edge("b", "c"))
    await g.add_edge(_edge("c", "d"))
    await g.add_edge(_edge("a", "d"))          # diamond (still DAG)
    await g.add_edge(_edge("d", "e"))
    assert await g.check_consistency() is True


# ---------------------------------------------------------------------------
# 10. test_prune_removes_stale_nodes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prune_removes_stale_nodes() -> None:
    g = DictTemporalGraph()
    await g.add_node(_node("old", ts=100))
    await g.add_node(_node("new", ts=9000))
    removed = await g.prune(horizon_ns=5000)
    assert removed == 1
    assert g.stats()["nodes"] == 1
    assert g.stats()["pruned_total"] == 1


# ---------------------------------------------------------------------------
# 11. test_prune_removes_dangling_edges
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prune_removes_dangling_edges() -> None:
    g = DictTemporalGraph()
    await g.add_node(_node("old", ts=100))
    await g.add_node(_node("new", ts=9000))
    await g.add_edge(_edge("old", "new"))
    assert g.stats()["edges"] == 1
    await g.prune(horizon_ns=5000)
    assert g.stats()["edges"] == 0            # dangling edge removed


# ---------------------------------------------------------------------------
# 12. test_null_temporal_graph_no_ops
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_null_temporal_graph_no_ops() -> None:
    g = NullTemporalGraph()
    # Verify it satisfies the protocol
    assert isinstance(g, TemporalGraph)
    # All operations are no-ops / return empty
    await g.add_node(_node("a"))
    await g.add_edge(_edge("a", "b"))
    assert await g.get_successors("a") == []
    assert await g.get_predecessors("a") == []
    assert await g.check_consistency() is True
    assert await g.prune(0) == 0
    assert g.stats() == {}
