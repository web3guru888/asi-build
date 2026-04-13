# Phase 8.2 — CausalGraph: Temporal Cause-Effect Relationship Mapping

**Phase**: 8 — Introspection & Explainability  
**Sub-phase**: 8.2  
**Module**: `asi/phase8/causal_graph.py`  
**Depends on**: [Phase 8.1 — Decision Tracer](Phase-8-Decision-Tracer)  
**Feeds into**: Phase 8.3 — ExplainAPI *(planned)*

---

## Overview

`CausalGraph` is a **directed acyclic graph (DAG)** that records temporal cause-effect relationships between `DecisionTrace` events produced by Phase 8.1's `DecisionTracer`.  It enables post-hoc reasoning about which past decisions influenced later outcomes and exposes the graph to the `ExplainAPI` (Phase 8.3).

```
DecisionTracer ──produces──► DecisionTrace
                                   │
                           CausalEdge (cause → effect, weight, lag_ms)
                                   │
                           CausalGraph (DAG, topological order, cycle guard)
                                   │
                          CausalGraphSnapshot ──► ExplainAPI (Phase 8.3)
```

---

## Core Data Types

### `CausalEdge` (frozen dataclass)

```python
@dataclass(frozen=True)
class CausalEdge:
    cause_trace_id: str          # DecisionTrace.trace_id of the cause
    effect_trace_id: str         # DecisionTrace.trace_id of the effect
    weight: float                # Jaccard overlap in [0.0, 1.0]
    lag_ms: float                # temporal lag (effect_ts - cause_ts) in ms
    edge_type: str = "temporal"  # "temporal" | "saliency" | "attention" | "shapley"
```

### `CausalNode` (frozen dataclass)

```python
@dataclass(frozen=True)
class CausalNode:
    trace_id: str
    module_id: str
    phase: str                   # CyclePhase value at decision time
    timestamp_ms: float          # epoch milliseconds
    summary: str                 # short label for visualisation
```

### `CausalGraphSnapshot` (dataclass)

```python
@dataclass
class CausalGraphSnapshot:
    nodes: list[CausalNode]
    edges: list[CausalEdge]
    captured_at: float           # time.time()
    max_depth: int               # longest path length from any root
    root_ids: list[str]          # trace_ids with in-degree == 0
    leaf_ids: list[str]          # trace_ids with out-degree == 0
```

---

## `CausalGraph` Class

```python
class CausalGraph:
    """Thread-safe DAG of causal relationships between DecisionTrace events."""

    def __init__(
        self,
        max_nodes: int = 1024,
        eviction: Literal["lru", "fifo"] = "lru",
    ) -> None:
        self._nodes: OrderedDict[str, CausalNode] = OrderedDict()
        self._fwd: dict[str, set[str]] = {}   # forward edges
        self._rev: dict[str, set[str]] = {}   # reverse edges (for ancestors)
        self._in_degree: dict[str, int] = {}
        self._max_nodes = max_nodes
        self._eviction = eviction
        self._lock = threading.Lock()
        self._init_metrics()

    # ── Mutation ──────────────────────────────────────────────────────────
    def add_node(self, node: CausalNode) -> None: ...
    def add_edge(self, edge: CausalEdge) -> None: ...  # raises CycleDetectedError

    # ── Query ─────────────────────────────────────────────────────────────
    def ancestors(self, trace_id: str, depth: int = 3) -> list[CausalNode]: ...
    def descendants(self, trace_id: str, depth: int = 3) -> list[CausalNode]: ...
    def critical_path(self) -> list[CausalNode]: ...   # longest path in DAG
    def topological_sort(self) -> list[CausalNode]: ...

    # ── Serialisation ─────────────────────────────────────────────────────
    def snapshot(self) -> CausalGraphSnapshot: ...
    def to_dot(self) -> str: ...    # Graphviz DOT language output
    def to_json(self) -> str: ...   # JSON adjacency list
```

### `CycleDetectedError`

```python
class CycleDetectedError(ValueError):
    """Raised by CausalGraph.add_edge() when a proposed edge would create a cycle."""
```

---

## Cycle Detection Algorithm

`add_edge()` runs a **DFS reachability check** before committing each new edge:

```python
def _has_path(self, src: str, dst: str) -> bool:
    """DFS: returns True if dst is reachable from src via _fwd adjacency."""
    visited: set[str] = set()
    stack = [src]
    while stack:
        node = stack.pop()
        if node == dst:
            return True
        if node in visited:
            continue
        visited.add(node)
        stack.extend(self._fwd.get(node, set()))
    return False

def add_edge(self, edge: CausalEdge) -> None:
    with self._lock:
        # Would effect → cause path already exist?
        if self._has_path(edge.effect_trace_id, edge.cause_trace_id):
            CAUSAL_CYCLE_REJECTED.inc()
            raise CycleDetectedError(
                f"{edge.cause_trace_id!r} → {edge.effect_trace_id!r} would create a cycle"
            )
        self._fwd.setdefault(edge.cause_trace_id, set()).add(edge.effect_trace_id)
        self._rev.setdefault(edge.effect_trace_id, set()).add(edge.cause_trace_id)
        self._in_degree[edge.effect_trace_id] = (
            self._in_degree.get(edge.effect_trace_id, 0) + 1
        )
        CAUSAL_EDGES_GAUGE.labels(edge_type=edge.edge_type).inc()
```

**Complexity**: O(V + E) per insertion, bounded by `max_nodes`.

---

## Node Eviction

When `len(nodes) >= max_nodes`, the graph evicts one node **and all its incident edges**:

| Policy | Eviction target | Use case |
|--------|----------------|----------|
| `lru` | Least-recently-accessed node | Default; preserves recent causal chains |
| `fifo` | Oldest-inserted node by `timestamp_ms` | Deterministic in tests |

`OrderedDict.move_to_end()` provides O(1) LRU touch:

```python
def _touch(self, trace_id: str) -> None:
    if trace_id in self._nodes:
        self._nodes.move_to_end(trace_id)  # move to MRU position

def _evict_one_lru(self) -> None:
    lru_id, _ = next(iter(self._nodes.items()))  # first = LRU
    self._remove_node(lru_id)
    CAUSAL_EVICTION_COUNTER.labels(policy="lru").inc()
```

---

## Topological Sort (Kahn's Algorithm)

```python
def topological_sort(self) -> list[CausalNode]:
    in_deg = dict(self._in_degree)   # local copy
    queue = deque(
        tid for tid, deg in in_deg.items() if deg == 0
    )
    result: list[CausalNode] = []
    while queue:
        tid = queue.popleft()
        if tid in self._nodes:
            result.append(self._nodes[tid])
        for eff_id in self._fwd.get(tid, set()):
            in_deg[eff_id] -= 1
            if in_deg[eff_id] == 0:
                queue.append(eff_id)
    return result
```

---

## Critical Path (DP on DAG)

```python
def critical_path(self) -> list[CausalNode]:
    topo = self.topological_sort()
    dp:   dict[str, int]       = {n.trace_id: 0 for n in topo}
    prev: dict[str, str | None] = {n.trace_id: None for n in topo}
    for node in topo:
        for eff_id in self._fwd.get(node.trace_id, set()):
            if dp[node.trace_id] + 1 > dp.get(eff_id, 0):
                dp[eff_id] = dp[node.trace_id] + 1
                prev[eff_id] = node.trace_id
    end_id = max(dp, key=dp.__getitem__) if dp else None
    if end_id is None:
        return []
    path: list[str] = []
    cur: str | None = end_id
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return [self._nodes[tid] for tid in path if tid in self._nodes]
```

**Example** — diamond DAG (A→B→D, A→B→C→D):

| Node | DP depth | Predecessor |
|------|----------|-------------|
| A | 0 | None |
| B | 1 | A |
| C | 2 | B |
| D | 3 | C |

Critical path: **A → B → C → D**

---

## `CausalGraphBuilder` — Automatic Edge Inference

```python
class CausalGraphBuilder:
    """Watches TraceStorage and infers CausalEdge entries automatically."""

    def __init__(
        self,
        graph: CausalGraph,
        storage: TraceStorage,
        window_ms: float = 5000.0,
        min_weight: float = 0.1,
        edge_strategy: Literal["saliency", "uniform", "attention"] = "saliency",
    ) -> None: ...

    async def infer_edges(self, new_trace: DecisionTrace) -> int:
        """Scan recent traces in storage; add edges where contributor overlap
        exceeds min_weight.  Returns number of edges added."""
        now_ms = new_trace.timestamp_ms
        recent = await self._storage.recent(since_ms=now_ms - self._window_ms)
        added = 0
        for past_trace in recent:
            if past_trace.trace_id == new_trace.trace_id:
                continue
            lag = now_ms - past_trace.timestamp_ms
            if lag < 0:
                continue                         # clock skew — skip
            past_ids = {c.module_id for c in past_trace.contributors}
            new_ids  = {c.module_id for c in new_trace.contributors}
            overlap  = len(past_ids & new_ids) / max(len(past_ids | new_ids), 1)
            if overlap < self._min_weight:
                continue
            edge = CausalEdge(
                cause_trace_id=past_trace.trace_id,
                effect_trace_id=new_trace.trace_id,
                weight=overlap,
                lag_ms=lag,
                edge_type=self._edge_strategy,
            )
            try:
                self._graph.add_edge(edge)
                added += 1
            except CycleDetectedError:
                pass                             # silently skip; metric already inc'd
        return added

    def build_node(self, trace: DecisionTrace) -> CausalNode: ...
```

### Edge Strategy vs. AttributionStrategy Alignment

| `DecisionTracer` strategy | Recommended `edge_strategy` |
|--------------------------|----------------------------|
| `UniformAttribution` | `"uniform"` |
| `SaliencyAttribution` | `"saliency"` |
| `AttentionAttribution` | `"attention"` |
| `ShapleyAttribution` | `"saliency"` (proxy) |

---

## `build_causal_graph()` Factory

```python
def build_causal_graph(
    storage: TraceStorage,
    *,
    max_nodes: int = 1024,
    eviction: Literal["lru", "fifo"] = "lru",
    window_ms: float = 5000.0,
    min_weight: float = 0.1,
    edge_strategy: Literal["saliency", "uniform", "attention"] = "saliency",
) -> tuple[CausalGraph, CausalGraphBuilder]:
    """Return a (graph, builder) pair ready for CognitiveCycle integration."""
    graph = CausalGraph(max_nodes=max_nodes, eviction=eviction)
    builder = CausalGraphBuilder(
        graph=graph,
        storage=storage,
        window_ms=window_ms,
        min_weight=min_weight,
        edge_strategy=edge_strategy,
    )
    return graph, builder
```

---

## `CognitiveCycle` Integration

```python
# In CognitiveCycle._run_phase8():
tracer: DecisionTracer         = self._phase8_tracer
graph: CausalGraph             = self._phase8_graph
builder: CausalGraphBuilder    = self._phase8_builder

# Phase 8.1: trace the current decision
trace = await tracer.trace(context, strategy="saliency")

# Phase 8.2: update the causal graph
node = builder.build_node(trace)
graph.add_node(node)
edges_added = await builder.infer_edges(trace)

# Phase 8.3 (planned): serve via ExplainAPI
# snapshot = graph.snapshot()
```

---

## `to_dot()` Output (Graphviz)

```python
def to_dot(self) -> str:
    lines = ["digraph CausalGraph {", "  rankdir=LR;", "  node [shape=box];"]
    for node in self._nodes.values():
        label = f"{node.module_id}\\n{node.phase}"
        lines.append(f'  "{node.trace_id}" [label="{label}"];')
    for cause_id, effects in self._fwd.items():
        for eff_id in effects:
            lines.append(f'  "{cause_id}" -> "{eff_id}";')
    lines.append("}")
    return "\n".join(lines)
```

Render: `dot -Tsvg causal.dot -o causal.svg`

---

## Prometheus Metrics

Pre-initialise **all counters/gauges to 0** at module import:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_causal_nodes_total` | Gauge | — | Current live node count |
| `asi_causal_edges_total` | Gauge | `edge_type` | Current live edge count by type |
| `asi_causal_cycle_rejected_total` | Counter | — | Edges rejected due to cycle detection |
| `asi_causal_eviction_total` | Counter | `policy` | Nodes evicted (lru/fifo) |
| `asi_causal_infer_duration_seconds` | Histogram | — | `infer_edges()` wall-clock time |

```python
CAUSAL_NODES_GAUGE      = Gauge("asi_causal_nodes_total", "Live causal nodes")
CAUSAL_EDGES_GAUGE      = Gauge("asi_causal_edges_total", "Live causal edges", ["edge_type"])
CAUSAL_CYCLE_REJECTED   = Counter("asi_causal_cycle_rejected_total", "Cycle-rejected edges")
CAUSAL_EVICTION_COUNTER = Counter("asi_causal_eviction_total", "Evicted nodes", ["policy"])
CAUSAL_INFER_HIST       = Histogram("asi_causal_infer_duration_seconds", "infer_edges() latency")

# Pre-init
CAUSAL_NODES_GAUGE.set(0)
for et in ("temporal", "saliency", "attention", "shapley"):
    CAUSAL_EDGES_GAUGE.labels(edge_type=et)
for pol in ("lru", "fifo"):
    CAUSAL_EVICTION_COUNTER.labels(policy=pol)
```

**PromQL alerts**:

```promql
# Cycle rejection rate (should be ~0; spikes = clock skew)
rate(asi_causal_cycle_rejected_total[5m]) > 5

# Eviction pressure (max_nodes too small)
rate(asi_causal_eviction_total[5m]) > 10

# Edge inference latency p95
histogram_quantile(0.95, rate(asi_causal_infer_duration_seconds_bucket[5m])) > 0.05
```

---

## Test Targets (12)

| # | Test | Covers |
|---|------|--------|
| 1 | `test_add_node_deduplicates` | Same `trace_id` twice → still 1 node; LRU touch called |
| 2 | `test_add_edge_cycle_raises` | A→B→C→A raises `CycleDetectedError` |
| 3 | `test_topological_sort_order` | DAG of 5 nodes → Kahn's order verified |
| 4 | `test_ancestors_depth` | `ancestors(leaf, depth=2)` returns ≤2 hops |
| 5 | `test_descendants_depth` | `descendants(root, depth=2)` returns ≤2 hops |
| 6 | `test_critical_path_linear` | Linear DAG → path = all nodes in order |
| 7 | `test_lru_eviction` | `max_nodes=3`; access node A, add 2 more; LRU (not A) evicted |
| 8 | `test_fifo_eviction` | `max_nodes=3`; oldest by insertion order evicted |
| 9 | `test_to_dot_output` | `to_dot()` contains `digraph`, node labels, edge arrows |
| 10 | `test_infer_edges_window` | Traces outside `window_ms` → no edge added |
| 11 | `test_infer_edges_min_weight` | Weak contributors below `min_weight` → no edge |
| 12 | `test_snapshot_fields` | `snapshot()` root_ids/leaf_ids correct for diamond DAG |

---

## Implementation Order (14 steps)

1. `CausalEdge` + `CausalNode` frozen dataclasses
2. `CycleDetectedError`
3. `_AdjList` helper (`dict[str, set[str]]` — forward + reverse)
4. `CausalGraph.__init__()` — `OrderedDict`, adjacency dicts, `in_degree`, `Lock`
5. `CausalGraph.add_node()` + eviction logic (`_evict_one_lru` / `_evict_one_fifo`)
6. `CausalGraph.add_edge()` + `_has_path()` DFS cycle check
7. `CausalGraph.ancestors()` / `descendants()` (BFS up to `depth`)
8. `CausalGraph.topological_sort()` (Kahn's algorithm)
9. `CausalGraph.critical_path()` (DP on topological order)
10. `CausalGraph.to_dot()` / `to_json()` / `snapshot()`
11. Prometheus pre-init block + metric instrumentation
12. `CausalGraphBuilder` — `build_node()` + `infer_edges()`
13. `build_causal_graph()` factory
14. Unit tests (12 targets above)

---

## Phase 8 Roadmap

| Sub-phase | Title | Status |
|-----------|-------|--------|
| 8.1 | [DecisionTracer](Phase-8-Decision-Tracer) — causal attribution & introspection | 🟡 In spec |
| 8.2 | **CausalGraph** — DAG of cause-effect relationships | 🟡 In spec |
| 8.3 | ExplainAPI — REST endpoint for trace + graph queries | 📋 Planned |
| 8.4 | Docker / Helm deployment hardening | 📋 Planned |
| 8.5 | Sepolia CI integration | 📋 Planned |
