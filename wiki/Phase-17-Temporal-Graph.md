# Phase 17.1 — TemporalGraph

> **Phase 17 — Temporal Reasoning & Predictive Cognition** · Sub-phase 17.1  
> Issue: [#434](https://github.com/web3guru888/asi-build/issues/434) · Show & Tell: [#435](https://github.com/web3guru888/asi-build/discussions/435) · Q&A: [#436](https://github.com/web3guru888/asi-build/discussions/436) · Planning: [#433](https://github.com/web3guru888/asi-build/discussions/433)

---

## Purpose

`TemporalGraph` is the foundational data structure for Phase 17. It maintains a **directed acyclic graph (DAG)** of time-stamped cognitive events and world-state snapshots, annotated with **Allen interval relations** to express qualitative temporal relationships between events.

Downstream components — `EventSequencer` (17.2), `PredictiveEngine` (17.3), `SchedulerCortex` (17.4) — all query the `TemporalGraph` to obtain causal and temporal context for their operations.

---

## Enum — `AllenRelation`

Allen's (1983) interval algebra defines 13 mutually exclusive, exhaustive relations between time intervals. For a directed graph only 7 base relations and their 6 inverses are needed:

```python
from enum import Enum, auto

class AllenRelation(Enum):
    # 7 base relations
    BEFORE = auto()        # A ends before B starts
    MEETS = auto()         # A ends exactly when B starts
    OVERLAPS = auto()      # A starts before B, ends inside B
    STARTS = auto()        # A and B start together; A ends first
    DURING = auto()        # A is fully inside B
    FINISHES = auto()      # A and B end together; B starts first
    EQUALS = auto()        # A and B are identical intervals
    # 6 inverses
    AFTER = auto()
    MET_BY = auto()
    OVERLAPPED_BY = auto()
    STARTED_BY = auto()
    CONTAINS = auto()
    FINISHED_BY = auto()
```

| Relation | Symbol | CognitiveCycle Example |
|----------|--------|------------------------|
| BEFORE | A ──► B (gap) | `percept` ends before `reasoning` starts |
| MEETS | A ─┤├─ B | `reasoning` ends exactly when `action` starts |
| OVERLAPS | A ══► B | Planning overlaps with perception |
| STARTS | A ═ B (A shorter) | Fast check starts with slow scan |
| DURING | ──A── inside B | Sub-goal runs inside main goal |
| FINISHES | A ends = B ends | Safety check finishes with action step |
| EQUALS | A = B | Redundant paths produce same interval |

---

## Frozen Dataclasses

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet, Any

@dataclass(frozen=True)
class TemporalNode:
    node_id: str                        # UUID or stable hash
    timestamp_ns: int                   # time.time_ns() at event creation
    state_snapshot: dict[str, Any]      # shallow copy of relevant state
    tags: FrozenSet[str] = field(default_factory=frozenset)

@dataclass(frozen=True)
class TemporalEdge:
    from_id: str
    to_id: str
    relation: AllenRelation
    duration_ns: int                    # |to.timestamp_ns - from.timestamp_ns|

@dataclass(frozen=True)
class TemporalGraphConfig:
    max_nodes: int = 10_000
    consistency_check: bool = True      # enforce DAG on add_edge
    prune_horizon_s: float = 3600.0     # prune nodes older than this
```

---

## Protocol — `TemporalGraph`

```python
from typing import Protocol, runtime_checkable, Sequence

@runtime_checkable
class TemporalGraph(Protocol):
    async def add_node(self, node: TemporalNode) -> None: ...
    async def add_edge(self, edge: TemporalEdge) -> None: ...
    async def get_successors(self, node_id: str) -> Sequence[TemporalNode]: ...
    async def get_predecessors(self, node_id: str) -> Sequence[TemporalNode]: ...
    async def check_consistency(self) -> bool: ...
    async def prune(self, horizon_ns: int) -> int: ...  # returns nodes removed
    def stats(self) -> dict[str, int]: ...
```

---

## Implementation — `DictTemporalGraph`

```python
import asyncio
import time
from collections import defaultdict, deque
from typing import Sequence

class DictTemporalGraph:
    def __init__(self, config: TemporalGraphConfig = TemporalGraphConfig()) -> None:
        self._config = config
        self._lock = asyncio.Lock()
        self._nodes: dict[str, TemporalNode] = {}
        self._edges: list[TemporalEdge] = []
        self._successors: dict[str, list[str]] = defaultdict(list)
        self._predecessors: dict[str, list[str]] = defaultdict(list)
        self._insertion_order: deque[str] = deque()
        self._nodes_added = 0
        self._edges_added = 0
        self._cycle_rejections = 0
        self._prune_count = 0

    async def add_node(self, node: TemporalNode) -> None:
        async with self._lock:
            if node.node_id in self._nodes:
                return  # idempotent
            if len(self._nodes) >= self._config.max_nodes:
                oldest = self._insertion_order.popleft()
                self._nodes.pop(oldest, None)
            self._nodes[node.node_id] = node
            self._insertion_order.append(node.node_id)
            self._nodes_added += 1

    async def add_edge(self, edge: TemporalEdge) -> None:
        async with self._lock:
            if edge.from_id not in self._nodes or edge.to_id not in self._nodes:
                raise KeyError(f"Unknown node(s): {edge.from_id!r}, {edge.to_id!r}")
            if self._config.consistency_check:
                # Temporarily add edge then check for cycle
                self._successors[edge.from_id].append(edge.to_id)
                if self._has_cycle(edge.to_id):
                    self._successors[edge.from_id].remove(edge.to_id)
                    self._cycle_rejections += 1
                    raise ValueError(f"Edge {edge.from_id!r}→{edge.to_id!r} would create a cycle")
                # Revert temp add, then do the real persistent add below
                self._successors[edge.from_id].remove(edge.to_id)
            self._successors[edge.from_id].append(edge.to_id)
            self._predecessors[edge.to_id].append(edge.from_id)
            self._edges.append(edge)
            self._edges_added += 1

    def _has_cycle(self, start: str) -> bool:
        """DFS cycle detection — O(V+E), runs synchronously under lock."""
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            in_stack.add(node)
            for nxt in self._successors.get(node, []):
                if nxt not in visited:
                    if dfs(nxt):
                        return True
                elif nxt in in_stack:
                    return True  # back-edge detected
            in_stack.discard(node)
            return False

        return dfs(start)

    async def get_successors(self, node_id: str) -> Sequence[TemporalNode]:
        async with self._lock:
            return [self._nodes[nid] for nid in self._successors.get(node_id, [])
                    if nid in self._nodes]

    async def get_predecessors(self, node_id: str) -> Sequence[TemporalNode]:
        async with self._lock:
            return [self._nodes[nid] for nid in self._predecessors.get(node_id, [])
                    if nid in self._nodes]

    async def check_consistency(self) -> bool:
        """Full DAG validation — O(V+E)."""
        async with self._lock:
            visited: set[str] = set()
            in_stack: set[str] = set()

            def dfs(node: str) -> bool:
                visited.add(node)
                in_stack.add(node)
                for nxt in self._successors.get(node, []):
                    if nxt not in visited:
                        if dfs(nxt): return True
                    elif nxt in in_stack: return True
                in_stack.discard(node)
                return False

            for nid in list(self._nodes):
                if nid not in visited:
                    if dfs(nid): return False
            return True

    async def prune(self, horizon_ns: int) -> int:
        async with self._lock:
            stale = {nid for nid, n in self._nodes.items()
                     if n.timestamp_ns < horizon_ns}
            for nid in stale:
                self._nodes.pop(nid)
                self._successors.pop(nid, None)
                self._predecessors.pop(nid, None)
            self._insertion_order = deque(
                x for x in self._insertion_order if x not in stale)
            self._edges = [e for e in self._edges
                           if e.from_id not in stale and e.to_id not in stale]
            self._prune_count += len(stale)
            return len(stale)

    def stats(self) -> dict[str, int]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "nodes_added_total": self._nodes_added,
            "edges_added_total": self._edges_added,
            "cycle_rejections": self._cycle_rejections,
            "pruned_total": self._prune_count,
        }
```

---

## `NullTemporalGraph` — no-op sentinel

```python
class NullTemporalGraph:
    async def add_node(self, node: TemporalNode) -> None: pass
    async def add_edge(self, edge: TemporalEdge) -> None: pass
    async def get_successors(self, node_id: str) -> list[TemporalNode]: return []
    async def get_predecessors(self, node_id: str) -> list[TemporalNode]: return []
    async def check_consistency(self) -> bool: return True
    async def prune(self, horizon_ns: int) -> int: return 0
    def stats(self) -> dict[str, int]: return {}
```

---

## State Machine — Node Lifecycle

```
                  add_node()
                      │
                      ▼
             ┌────────────────┐
             │    RESIDENT     │  ← live in self._nodes
             │  timestamp_ns  │
             │  state_snapshot│
             └───────┬────────┘
                     │ prune(horizon_ns) if timestamp_ns < horizon_ns
                     ▼
             ┌────────────────┐
             │    EVICTED     │  ← removed from nodes, successors, predecessors
             │  dangling edges│     + edges referencing node also removed
             │  also removed  │
             └────────────────┘

  OR: max_nodes exceeded → oldest (insertion_order.popleft()) evicted first
```

---

## Data Flow — CognitiveCycle Integration

```
CognitiveCycle._run_step(step_name):
    t0 = time.time_ns()
    result = await step_fn()
    node = TemporalNode(
        node_id = f"{step_name}:{uuid4()}",
        timestamp_ns = t0,
        state_snapshot = result.to_dict(),
        tags = frozenset({step_name}),
    )
    await temporal_graph.add_node(node)
    if prev_node_id:
        await temporal_graph.add_edge(TemporalEdge(
            prev_node_id, node.node_id,
            AllenRelation.BEFORE,
            node.timestamp_ns - prev_ts,
        ))
    prev_node_id, prev_ts = node.node_id, t0

                    ┌──────────────────────┐
   Cycle N:         │ percept → reason →   │
                    │ action               │
                    └──────────┬───────────┘
                               │  BEFORE edges
                    ┌──────────▼───────────┐
   Cycle N+1:       │ percept → reason →   │
                    │ action               │
                    └──────────────────────┘
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_temporal_graph_nodes_total` | Counter | — | Cumulative nodes added |
| `asi_temporal_graph_edges_total` | Counter | — | Cumulative edges added |
| `asi_temporal_graph_cycle_rejections_total` | Counter | — | Edges rejected due to cycle |
| `asi_temporal_graph_size` | Gauge | — | Current live node count |
| `asi_temporal_graph_prune_total` | Counter | — | Total nodes pruned |

**PromQL examples**:
```promql
# Node ingestion rate
rate(asi_temporal_graph_nodes_total[1m])

# Graph fill percentage (assuming max_nodes=10000)
asi_temporal_graph_size / 10000

# Cycle rejection rate (should be near zero in healthy system)
increase(asi_temporal_graph_cycle_rejections_total[5m])
```

**Grafana alert YAML**:
```yaml
alert: TemporalGraphNearCapacity
expr: asi_temporal_graph_size > 9000
for: 2m
labels:
  severity: warning
annotations:
  summary: "TemporalGraph approaching max_nodes capacity ({{ $value }} nodes)"
  runbook_url: "https://github.com/web3guru888/asi-build/wiki/Phase-17-Temporal-Graph"
```

---

## mypy Narrowing Table

| Pattern | Issue | Fix |
|---------|-------|-----|
| `self._nodes[nid]` after `.pop()` | Possible `KeyError` | Use `.get(nid)` + assert or guard |
| `Sequence[TemporalNode]` return type | Covariance | Return `list[TemporalNode]` in impl |
| `AllenRelation` enum in `TemporalEdge` | No issue | Already typed; no narrowing needed |
| `deque[str]` reconstruction in prune | Reassignment type | Annotate `_insertion_order: deque[str]` explicitly |
| `defaultdict(list)` | `list[Any]` inferred | Annotate as `defaultdict[str, list[str]]` |

---

## 12 Test Targets

1. `test_add_node_increments_counter`
2. `test_duplicate_node_ignored`
3. `test_max_nodes_evicts_oldest`
4. `test_add_edge_unknown_node_raises`
5. `test_add_edge_creates_allen_relation`
6. `test_cycle_detection_raises`
7. `test_get_successors_returns_correct_nodes`
8. `test_get_predecessors_returns_correct_nodes`
9. `test_check_consistency_clean_dag`
10. `test_prune_removes_stale_nodes`
11. `test_prune_removes_dangling_edges`
12. `test_null_temporal_graph_no_ops`

### Test Skeletons

```python
import pytest, asyncio, time

@pytest.mark.asyncio
async def test_add_edge_creates_allen_relation():
    g = DictTemporalGraph()
    n1 = TemporalNode("a", 1_000_000_000, {}, frozenset())
    n2 = TemporalNode("b", 2_000_000_000, {}, frozenset())
    await g.add_node(n1); await g.add_node(n2)
    edge = TemporalEdge("a", "b", AllenRelation.BEFORE, 1_000_000_000)
    await g.add_edge(edge)
    succs = await g.get_successors("a")
    assert succs[0].node_id == "b"
    assert g.stats()["edges"] == 1

@pytest.mark.asyncio
async def test_cycle_detection_raises():
    g = DictTemporalGraph()
    for nid in ["x", "y", "z"]:
        await g.add_node(TemporalNode(nid, 0, {}, frozenset()))
    await g.add_edge(TemporalEdge("x", "y", AllenRelation.BEFORE, 0))
    await g.add_edge(TemporalEdge("y", "z", AllenRelation.BEFORE, 0))
    with pytest.raises(ValueError, match="cycle"):
        await g.add_edge(TemporalEdge("z", "x", AllenRelation.BEFORE, 0))
    assert g.stats()["cycle_rejections"] == 1
```

---

## 14-Step Implementation Order

1. Define `AllenRelation` enum
2. Define `TemporalNode` frozen dataclass
3. Define `TemporalEdge` frozen dataclass
4. Define `TemporalGraphConfig` frozen dataclass
5. Define `TemporalGraph` Protocol with `@runtime_checkable`
6. Implement `DictTemporalGraph.__init__` with all fields
7. Implement `add_node()` with idempotency + max_nodes eviction
8. Implement `_has_cycle()` DFS helper (synchronous)
9. Implement `add_edge()` with consistency check gate
10. Implement `get_successors()` and `get_predecessors()`
11. Implement `check_consistency()` full DAG DFS
12. Implement `prune()` with stale-node + edge cleanup
13. Implement `stats()` dict
14. Implement `NullTemporalGraph` no-op + register Prometheus metrics

---

## Phase 17 Sub-phase Tracker

| Sub-phase | Component | Status |
|-----------|-----------|--------|
| 17.1 | TemporalGraph | 🟡 Spec'd |
| 17.2 | EventSequencer | 🔲 Pending |
| 17.3 | PredictiveEngine | 🔲 Pending |
| 17.4 | SchedulerCortex | 🔲 Pending |
| 17.5 | TemporalOrchestrator | 🔲 Pending |

---

*Previous phase: [Phase 16 — ReflectionCycle](Phase-16-Reflection-Cycle) · Next: Phase 17.2 — EventSequencer (TBD)*
