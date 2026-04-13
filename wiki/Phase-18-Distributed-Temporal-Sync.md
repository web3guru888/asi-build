# Phase 18.3 — DistributedTemporalSync

**Phase 18: Distributed Temporal Cognition & Multi-Horizon Memory**  
Sub-phase 3 of 5 · [Issue #456](https://github.com/web3guru888/asi-build/issues/456) · [Show & Tell #457](https://github.com/web3guru888/asi-build/discussions/457) · [Q&A #458](https://github.com/web3guru888/asi-build/discussions/458)

---

## Overview

`DistributedTemporalSync` implements a **vector-clock–based gossip protocol** that keeps `TemporalGraph` replicas across federated ASI agents eventually consistent. Each gossip round computes a delta (edges the peer lacks), pushes it, pulls the peer's delta, resolves conflicts via a configurable policy, and advances the vector clock.

---

## Enums

### `SyncState`

| Value | Meaning |
|-------|---------|
| `IDLE` | No active sync |
| `DIALING` | Connecting to peer |
| `DIFFING` | Computing delta edges |
| `PUSHING` | Sending missing edges |
| `PULLING` | Receiving peer edges |
| `MERGING` | Applying delta to local graph |
| `VERIFYING` | Post-merge consistency check |

### `ConflictPolicy`

| Value | Behaviour | Use when |
|-------|-----------|----------|
| `LAST_WRITER_WINS` | Accept remote if `remote_clock.dominates(local)` | Low contention |
| `MERGE_ALL` | Union of both edge sets | Maximum consistency |
| `LOCAL_PRIORITY` | Keep local; discard remote | Read-only mirroring |

---

## Data Classes

### `VectorClock`

```python
@dataclass(frozen=True)
class VectorClock:
    clocks: Mapping[str, int]  # agent_id → logical time

    def increment(self, agent_id: str) -> "VectorClock": ...
    def merge(self, other: "VectorClock") -> "VectorClock": ...
    def dominates(self, other: "VectorClock") -> bool: ...
```

**Clock operations**:

| Operation | Formula | Purpose |
|-----------|---------|---------|
| `increment(id)` | `clock[id] += 1` | Mark local progress |
| `merge(other)` | `max(a[k], b[k]) ∀k` | Absorb peer causal history |
| `dominates(other)` | `∀k: self[k] ≥ other[k]` | Detect stale peers |

### `SyncConfig`

```python
@dataclass(frozen=True)
class SyncConfig:
    agent_id: str
    peer_ids: FrozenSet[str]
    sync_interval_s: float = 5.0
    max_delta_edges: int = 1_000
    conflict_policy: ConflictPolicy = ConflictPolicy.LAST_WRITER_WINS
    verify_post_merge: bool = True
    metrics_prefix: str = "asi_temporal_sync"
```

---

## Protocol

```python
@runtime_checkable
class DistributedTemporalSync(Protocol):
    agent_id: str
    peers: FrozenSet[str]

    async def sync_with(self, peer_id: str) -> int: ...          # edges exchanged
    async def broadcast_sync(self) -> Mapping[str, int]: ...     # {peer_id: edges}
    async def receive_push(self, peer_id, edges, clock) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    @property
    def vector_clock(self) -> VectorClock: ...
    @property
    def state(self) -> SyncState: ...
```

---

## `AsyncDistributedTemporalSync`

### Full Implementation

```python
class AsyncDistributedTemporalSync:
    def __init__(self, config: SyncConfig, graph, transport) -> None:
        self._cfg       = config
        self._graph     = graph
        self._transport = transport
        self._clock     = VectorClock(clocks={config.agent_id: 0})
        self._state     = SyncState.IDLE
        self._lock      = asyncio.Lock()
        self._task: asyncio.Task | None = None

    async def sync_with(self, peer_id: str) -> int:
        async with self._lock:
            self._state = SyncState.DIALING
            peer_clock = await self._transport.fetch_clock(peer_id)

            self._state = SyncState.DIFFING
            local_edges = self._graph.edges_since(peer_clock)

            self._state = SyncState.PUSHING
            await self._transport.push_edges(peer_id, local_edges, self._clock)

            self._state = SyncState.PULLING
            remote_edges, remote_clock = await self._transport.pull_edges(peer_id, self._clock)

            self._state = SyncState.MERGING
            merged = self._resolve_conflicts(local_edges, remote_edges, remote_clock)
            await self._graph.apply_edges(merged)

            if self._cfg.verify_post_merge:
                self._state = SyncState.VERIFYING
                await self._graph.verify_consistency()

            self._clock = self._clock.merge(remote_clock).increment(self._cfg.agent_id)
            self._state = SyncState.IDLE
            return len(remote_edges)

    def _resolve_conflicts(self, local, remote, remote_clock):
        match self._cfg.conflict_policy:
            case ConflictPolicy.LAST_WRITER_WINS:
                return [e for e in remote if remote_clock.dominates(self._clock)]
            case ConflictPolicy.MERGE_ALL:
                return list(remote)
            case ConflictPolicy.LOCAL_PRIORITY:
                return []

    async def broadcast_sync(self) -> Mapping[str, int]:
        results = {}
        for peer_id in self._cfg.peer_ids:
            try:
                results[peer_id] = await self.sync_with(peer_id)
            except Exception:
                results[peer_id] = -1  # degraded
        return results

    async def receive_push(self, peer_id, edges, clock) -> None:
        async with self._lock:
            self._state = SyncState.MERGING
            await self._graph.apply_edges(edges)
            self._clock = self._clock.merge(clock)
            self._state = SyncState.IDLE

    async def start(self) -> None:
        self._task = asyncio.create_task(
            self._sync_loop(), name=f"temporal-sync-{self._cfg.agent_id}"
        )

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _sync_loop(self) -> None:
        while True:
            await self.broadcast_sync()
            await asyncio.sleep(self._cfg.sync_interval_s)

    @property
    def vector_clock(self) -> VectorClock: return self._clock
    @property
    def state(self) -> SyncState: return self._state
```

---

## `NullDistributedTemporalSync`

```python
class NullDistributedTemporalSync:
    agent_id = "null"
    peers: FrozenSet[str] = frozenset()
    vector_clock = VectorClock(clocks={})
    state = SyncState.IDLE

    async def sync_with(self, peer_id: str) -> int: return 0
    async def broadcast_sync(self) -> Mapping[str, int]: return {}
    async def receive_push(self, peer_id, edges, clock) -> None: pass
    async def start(self) -> None: pass
    async def stop(self) -> None: pass
```

---

## Factory

```python
def make_temporal_sync(
    config: SyncConfig,
    graph=None,
    transport=None,
) -> DistributedTemporalSync:
    if graph is None or transport is None:
        return NullDistributedTemporalSync()
    return AsyncDistributedTemporalSync(config, graph, transport)
```

---

## Data Flow: Gossip Round

```
┌──────────────────────────────────────────────────────────────┐
│                     Agent A (local)                          │
│                                                              │
│  TemporalGraph ──edges_since(peer_clock)──► delta_edges      │
│       │                                        │            │
│       │                              PeerTransport.push()   │
│       │                                        │            │
│       │         ┌──────────────────────────────▼──────┐     │
│       │         │           NETWORK / gRPC             │     │
│       │         └──────────────────────────────┬──────┘     │
│       │                                        │            │
│  apply_edges() ◄── _resolve_conflicts() ◄─ pull()          │
│       │                                                     │
│  verify_consistency() ──► clock.merge().increment()         │
└──────────────────────────────────────────────────────────────┘
                     (repeated for each peer in peer_ids)
```

## Background Loop Lifecycle

```
start()
  └── asyncio.create_task(_sync_loop)
          │
          ▼
    ┌─ broadcast_sync() ─────────────────────────┐
    │   └── sync_with(peer_1) → edges_1          │
    │   └── sync_with(peer_2) → edges_2          │
    │   └── sync_with(peer_N) → -1 (degraded)   │
    └─ asyncio.sleep(sync_interval_s) ───────────┘
          │
        stop() ──► task.cancel() ──► CancelledError
```

---

## Integration

### TemporalGraph (17.1)

`TemporalGraph` must expose:
- `edges_since(clock: VectorClock) → list[Edge]` — filtered by per-agent clock value
- `apply_edges(edges: list[Edge]) → None` — batch insert with dedup
- `verify_consistency() → None` — acyclicity + causal order check

Edges must carry `source_agent_id: str` + `agent_clock_value: int` for correct delta computation.

### MemoryConsolidator (18.2)

After `apply_edges()` succeeds, newly merged edges are immediately available to `TemporalGraph.get_unconsolidated_traces()`. The consolidator's background sweep picks them up on the next cycle — no direct coupling needed.

### FederationHealthMonitor (9.5)

Consumes `asi_temporal_sync_peers_reachable` to surface network isolation events in the federation health dashboard.

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_temporal_sync_edges_pushed_total` | Counter | `agent_id`, `peer_id` | Edges pushed |
| `asi_temporal_sync_edges_pulled_total` | Counter | `agent_id`, `peer_id` | Edges received |
| `asi_temporal_sync_conflicts_resolved_total` | Counter | `agent_id`, `policy` | Conflicts by policy |
| `asi_temporal_sync_round_duration_seconds` | Histogram | `agent_id`, `peer_id` | Gossip round latency |
| `asi_temporal_sync_peers_reachable` | Gauge | `agent_id` | Live peer count |

**PromQL alerts**:

```promql
# Backlog burst (partition heal)
increase(asi_temporal_sync_edges_pulled_total[5m]) > 5000

# p99 sync latency
histogram_quantile(0.99, rate(asi_temporal_sync_round_duration_seconds_bucket[5m])) > 2.0

# Isolated agent (no peers reachable)
asi_temporal_sync_peers_reachable == 0
```

---

## Mypy Narrowing Table

| Variable | Declared type | Narrowed to | How |
|----------|---------------|-------------|-----|
| `merged` | `list[object]` | `list[Edge]` | cast after `_resolve_conflicts` |
| `remote_clock` | `VectorClock` | same | already concrete |
| `transport` | `PeerTransport` | protocol check | `isinstance` guard in factory |
| `config.peer_ids` | `FrozenSet[str]` | same | frozen dataclass |

---

## Test Targets (12)

1. `test_vector_clock_increment_advances_local_component`
2. `test_vector_clock_merge_takes_max_per_component`
3. `test_vector_clock_dominates_strict_partial_order`
4. `test_sync_with_peer_exchanges_edges`
5. `test_conflict_policy_last_writer_wins`
6. `test_conflict_policy_merge_all_union`
7. `test_conflict_policy_local_priority_keeps_local`
8. `test_broadcast_sync_degrades_on_unreachable_peer`
9. `test_receive_push_applies_edges_and_merges_clock`
10. `test_sync_loop_runs_periodically`
11. `test_null_sync_no_ops`
12. `test_verify_post_merge_called_when_enabled`

### Skeletons

```python
@pytest.mark.asyncio
async def test_vector_clock_dominates_strict_partial_order():
    a = VectorClock(clocks={"A": 3, "B": 1})
    b = VectorClock(clocks={"A": 2, "B": 4})
    assert not a.dominates(b)
    assert not b.dominates(a)

@pytest.mark.asyncio
async def test_broadcast_sync_degrades_on_unreachable_peer():
    transport = FailingTransport(fail_peer="B")
    sync = AsyncDistributedTemporalSync(
        config_with_peers({"A", "B"}), mock_graph(), transport
    )
    results = await sync.broadcast_sync()
    assert results["B"] == -1
    assert results["A"] >= 0
```

---

## Implementation Order (14 steps)

1. Add `source_agent_id` + `agent_clock_value` fields to `TemporalGraph.Edge`
2. Implement `VectorClock` frozen dataclass with `increment/merge/dominates`
3. Add `edges_since(clock)` + `_clock_index` to `TemporalGraph`
4. Add `apply_edges()` + `verify_consistency()` to `TemporalGraph`
5. Define `PeerTransport` Protocol
6. Implement `InMemoryPeerTransport` for tests
7. Implement `SyncConfig` frozen dataclass
8. Implement `AsyncDistributedTemporalSync.__init__` + properties
9. Implement `sync_with()` with 7-state machine
10. Implement `_resolve_conflicts()` with match/case + concurrent fallback
11. Implement `broadcast_sync()` with degraded mode
12. Implement `receive_push()` + background `_sync_loop()`
13. Implement `NullDistributedTemporalSync` + factory
14. Wire metrics + write all 12 tests

---

## Phase 18 Sub-phase Tracker

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 18.1 | HorizonPlanner | #450 | 🟡 open |
| 18.2 | MemoryConsolidator | #453 | 🟡 open |
| 18.3 | DistributedTemporalSync | #456 | 🟡 open |
| 18.4 | CausalMemoryIndex | — | ⏳ next |
| 18.5 | TemporalCoherenceArbiter | — | ⏳ upcoming |
