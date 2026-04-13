# Phase 9.3 — FederatedTaskRouter: load-aware capability-first task dispatch

Phase 9.3 extends the multi-agent federation stack with `FederatedTaskRouter` — a load-aware, pluggable task dispatcher that routes cognitive tasks to the peer best positioned to handle them.  It reads live `PeerCapSnapshot` entries from `FederatedBlackboard` (Phase 9.2), selects the target peer via a `RoutingStrategy`, and delivers the `TaskEnvelope` through `FederationGateway` (Phase 9.1) with configurable retry and fallback-to-local semantics.

---

## Motivation

| Gap | Solution |
|-----|---------|
| Every node handles all tasks locally regardless of cluster load | Route tasks to underutilised peers with matching capabilities |
| No way to express "I need a peer with vector-search capability" | `TaskEnvelope.required_caps` + `CapabilityFirstStrategy` filter |
| Hard-coded routing breaks under changing topology | Pluggable `RoutingStrategy` Protocol — swap strategies at runtime |
| Remote call failures crash the task pipeline | Retry loop with transient degradation tracking + FALLBACK to local |
| No observability of routing decisions | 5 Prometheus metrics: outcomes, latency, retries, stale caps, active peers |

---

## Data model

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol, runtime_checkable

class RoutingDecision(Enum):
    LOCAL    = auto()   # handled on this node (no suitable peer)
    REMOTE   = auto()   # forwarded to a peer
    FALLBACK = auto()   # remote failed → handled locally after retries

@dataclass(frozen=True)
class TaskEnvelope:
    task_id:       str
    task_type:     str            # e.g. "reasoning", "consolidation"
    payload:       bytes
    required_caps: frozenset[str]
    priority:      int  = 0
    deadline_ms:   int  = 30_000
    origin_peer:   str  = ""

@dataclass(frozen=True)
class RoutingResult:
    task_id:     str
    decision:    RoutingDecision
    target_peer: str | None
    latency_ms:  float
    attempt:     int
    error:       str | None = None

@dataclass(frozen=True)
class PeerCapSnapshot:
    peer_id:       str
    capabilities:  frozenset[str]
    load_score:    float          # 0.0 (idle) – 1.0 (saturated)
    latency_ms:    float
    updated_at_ms: int
```

---

## `RoutingStrategy` Protocol

```python
@runtime_checkable
class RoutingStrategy(Protocol):
    def select(
        self,
        envelope:   TaskEnvelope,
        candidates: list[PeerCapSnapshot],
    ) -> str | None: ...          # peer DID, or None → local
```

### Three built-in strategies

| Strategy | Algorithm | Best for |
|----------|-----------|----------|
| `CapabilityFirstStrategy` | Filter `required_caps ⊆ peer.capabilities`; sort ascending `load_score`; tie-break DID | Heterogeneous clusters |
| `ConsistentHashStrategy` | Rendezvous hash `sha256(peer:task_type:task_id)[:8]`; skip `load ≥ 0.9` | Cache/session affinity |
| `AuctionStrategy` | `bid = load_score × (1 + min(latency_ms/1000, 1.0))`; lowest bid wins | Latency-sensitive throughput |

#### `CapabilityFirstStrategy`

```python
class CapabilityFirstStrategy:
    def select(self, envelope: TaskEnvelope, candidates: list[PeerCapSnapshot]) -> str | None:
        eligible = [p for p in candidates if envelope.required_caps.issubset(p.capabilities)]
        if not eligible:
            return None
        eligible.sort(key=lambda p: (p.load_score, p.peer_id))
        return eligible[0].peer_id
```

#### `ConsistentHashStrategy`

```python
import hashlib

class ConsistentHashStrategy:
    def __init__(self, overload_threshold: float = 0.9) -> None:
        self._thr = overload_threshold

    def _score(self, peer_id: str, key: str) -> int:
        h = hashlib.sha256(f"{peer_id}:{key}".encode()).digest()
        return int.from_bytes(h[:8], "big")

    def select(self, envelope: TaskEnvelope, candidates: list[PeerCapSnapshot]) -> str | None:
        eligible = [p for p in candidates if p.load_score < self._thr]
        if not eligible:
            return None
        key = f"{envelope.task_type}:{envelope.task_id}"
        return max(eligible, key=lambda p: self._score(p.peer_id, key)).peer_id
```

#### `AuctionStrategy`

```python
class AuctionStrategy:
    def _bid(self, p: PeerCapSnapshot) -> float:
        return p.load_score * (1.0 + min(p.latency_ms / 1000.0, 1.0))

    def select(self, envelope: TaskEnvelope, candidates: list[PeerCapSnapshot]) -> str | None:
        eligible = [p for p in candidates if envelope.required_caps.issubset(p.capabilities)]
        if not eligible:
            return None
        eligible.sort(key=lambda p: (self._bid(p), p.peer_id))
        return eligible[0].peer_id
```

---

## `FederatedTaskRouter` Protocol

```python
@runtime_checkable
class FederatedTaskRouter(Protocol):
    async def route(self, envelope: TaskEnvelope) -> RoutingResult: ...
    async def snapshot(self) -> RouterSnapshot: ...
```

---

## `RouterSnapshot`

```python
@dataclass
class RouterSnapshot:
    total_routed:   int
    local_count:    int
    remote_count:   int
    fallback_count: int
    peer_counts:    dict[str, int]   # peer_id → tasks routed to that peer
    strategy_name:  str
```

---

## `InMemoryFederatedTaskRouter`

```python
class InMemoryFederatedTaskRouter:
    def __init__(
        self,
        *,
        local_peer_id: str,
        gateway:       FederationGateway,
        blackboard:    FederatedBlackboard,
        strategy:      RoutingStrategy,
        max_retries:   int = 2,
        stale_cap_ms:  int = 5_000,
        timeout_ms:    int = 5_000,
    ) -> None:
        self._local_peer_id = local_peer_id
        self._gateway       = gateway
        self._blackboard    = blackboard
        self._strategy      = strategy
        self._max_retries   = max_retries
        self._stale_cap_ms  = stale_cap_ms
        self._timeout_ms    = timeout_ms
        # counters
        self._total = self._local = self._remote = self._fallback = 0
        self._peer_counts: dict[str, int] = {}
```

### `_get_fresh_snapshots()`

```python
async def _get_fresh_snapshots(self) -> list[PeerCapSnapshot]:
    now_ms = int(time.time() * 1000)
    result: list[PeerCapSnapshot] = []
    async for key, value in self._blackboard.scan(prefix="peer/"):
        if not key.endswith("/cap"):
            continue
        snap = PeerCapSnapshot(**json.loads(value))
        if (now_ms - snap.updated_at_ms) > self._stale_cap_ms:
            _ROUTER_STALE.inc()
            continue
        if snap.peer_id == self._local_peer_id:
            continue
        result.append(snap)
    _ROUTER_ACTIVE.set(len(result))
    return result
```

### `route()` — retry loop

```python
async def route(self, envelope: TaskEnvelope) -> RoutingResult:
    t0 = time.monotonic()
    degraded: set[str] = set()

    for attempt in range(1, self._max_retries + 2):
        candidates = [p for p in await self._get_fresh_snapshots()
                      if p.peer_id not in degraded]

        target = self._strategy.select(envelope, candidates)
        if target is None:
            return self._record(RoutingResult(
                task_id=envelope.task_id, decision=RoutingDecision.LOCAL,
                target_peer=None, latency_ms=_elapsed(t0), attempt=attempt,
            ))
        try:
            await asyncio.wait_for(
                self._gateway.send_message(target, _wrap(envelope)),
                timeout=self._timeout_ms / 1000.0,
            )
            return self._record(RoutingResult(
                task_id=envelope.task_id, decision=RoutingDecision.REMOTE,
                target_peer=target, latency_ms=_elapsed(t0), attempt=attempt,
            ))
        except (asyncio.TimeoutError, PeerUnreachableError):
            degraded.add(target)
            _ROUTER_RETRIES.inc()

    return self._record(RoutingResult(
        task_id=envelope.task_id, decision=RoutingDecision.FALLBACK,
        target_peer=None, latency_ms=_elapsed(t0),
        attempt=self._max_retries + 1, error="all_peers_unreachable",
    ))
```

### `snapshot()`

```python
async def snapshot(self) -> RouterSnapshot:
    return RouterSnapshot(
        total_routed=self._total, local_count=self._local,
        remote_count=self._remote, fallback_count=self._fallback,
        peer_counts=dict(self._peer_counts),
        strategy_name=type(self._strategy).__name__,
    )
```

---

## Factory

```python
def build_task_router(
    *,
    local_peer_id: str,
    gateway:       FederationGateway,
    blackboard:    FederatedBlackboard,
    strategy:      str = "capability_first",
    max_retries:   int = 2,
    stale_cap_ms:  int = 5_000,
    timeout_ms:    int = 5_000,
) -> FederatedTaskRouter:
    _strategies: dict[str, RoutingStrategy] = {
        "capability_first": CapabilityFirstStrategy(),
        "consistent_hash":  ConsistentHashStrategy(),
        "auction":          AuctionStrategy(),
    }
    if isinstance(strategy, str):
        strat = _strategies[strategy]
    else:
        strat = strategy   # custom Protocol impl
    return InMemoryFederatedTaskRouter(
        local_peer_id=local_peer_id,
        gateway=gateway, blackboard=blackboard, strategy=strat,
        max_retries=max_retries, stale_cap_ms=stale_cap_ms, timeout_ms=timeout_ms,
    )
```

---

## `CognitiveCycle` integration

```python
class CognitiveCycle:
    def __init__(self, ..., task_router: FederatedTaskRouter | None = None) -> None:
        self._router = task_router

    async def _dispatch_task(self, task_type: str, payload: bytes,
                             required_caps: frozenset[str] = frozenset()) -> RoutingResult | None:
        if self._router is None:
            return None    # local-only mode
        envelope = TaskEnvelope(
            task_id=str(uuid.uuid4()), task_type=task_type,
            payload=payload, required_caps=required_caps,
        )
        return await self._router.route(envelope)
```

---

## Prometheus metrics

```python
from prometheus_client import Counter, Gauge, Histogram

_ROUTER_TASKS   = Counter("asi_router_tasks_total",           "Routing outcomes",        ["decision"])
_ROUTER_LATENCY = Histogram("asi_router_latency_seconds",     "Routing latency",         ["decision"])
_ROUTER_RETRIES = Counter("asi_router_retries_total",         "Retry attempts")
_ROUTER_STALE   = Counter("asi_router_stale_snapshots_total", "Stale cap snapshots")
_ROUTER_ACTIVE  = Gauge("asi_router_active_peers",            "Peers with fresh caps")

# Pre-initialise all label combinations
for _d in ("local", "remote", "fallback"):
    _ROUTER_TASKS.labels(decision=_d)
    _ROUTER_LATENCY.labels(decision=_d)
```

### PromQL monitoring

```promql
# Routing outcome distribution
sum by (decision) (rate(asi_router_tasks_total[5m]))

# P95 routing latency
histogram_quantile(0.95, sum by (le, decision) (rate(asi_router_latency_seconds_bucket[5m])))

# Retry rate (spikes = peer instability)
rate(asi_router_retries_total[5m])

# Stale snapshot rate (spikes = heartbeat gaps)
rate(asi_router_stale_snapshots_total[5m])

# Live cluster size
asi_router_active_peers
```

---

## mypy type table

| Symbol | Type annotation |
|--------|----------------|
| `TaskEnvelope.required_caps` | `frozenset[str]` |
| `RoutingStrategy.select()` return | `str \| None` |
| `route()` `degraded` set | `set[str]` |
| `RouterSnapshot.peer_counts` | `dict[str, int]` |
| `build_task_router()` return | `FederatedTaskRouter` |
| `InMemoryFederatedTaskRouter._strategy` | `RoutingStrategy` |

---

## Test targets (12)

| # | Test name | What it verifies |
|---|-----------|-----------------|
| 1 | `test_capability_first_selects_lowest_load` | Two eligible peers; lower `load_score` wins |
| 2 | `test_capability_first_no_matching_cap` | No peer has `required_caps` → LOCAL |
| 3 | `test_consistent_hash_affinity` | Same `task_type` always routes to same peer |
| 4 | `test_consistent_hash_skips_overloaded` | Peer with `load ≥ 0.9` excluded |
| 5 | `test_auction_tie_break_by_did` | Equal bid → lexicographically smaller DID wins |
| 6 | `test_route_remote_success` | Happy path → REMOTE, `latency_ms > 0` |
| 7 | `test_route_retry_on_timeout` | First attempt times out; second succeeds → `attempt=2` |
| 8 | `test_route_fallback_after_all_retries` | All `max_retries+1` attempts fail → FALLBACK |
| 9 | `test_stale_snapshot_excluded` | Snapshot age > `stale_cap_ms` → excluded |
| 10 | `test_snapshot_counters` | `RouterSnapshot` local/remote/fallback counts correct |
| 11 | `test_prometheus_metrics_pre_init` | All 5 label combos registered before first call |
| 12 | `test_runtime_checkable_protocol` | `isinstance(router, FederatedTaskRouter)` is `True` |

---

## 14-step implementation order

1. `RoutingDecision` enum
2. `TaskEnvelope` frozen dataclass
3. `RoutingResult` frozen dataclass
4. `PeerCapSnapshot` frozen dataclass
5. `RoutingStrategy` Protocol (`@runtime_checkable`)
6. `CapabilityFirstStrategy`
7. `ConsistentHashStrategy` (rendezvous hash + overload skip)
8. `AuctionStrategy` (bid score + tie-break)
9. `FederatedTaskRouter` Protocol (`@runtime_checkable`)
10. `RouterSnapshot` dataclass
11. `InMemoryFederatedTaskRouter.__init__` + `_get_fresh_snapshots()`
12. `InMemoryFederatedTaskRouter.route()` (retry loop + FALLBACK)
13. `InMemoryFederatedTaskRouter.snapshot()` + Prometheus pre-init
14. `build_task_router()` factory + 12 pytest targets

---

## Phase 9 roadmap

| Sub-phase | Component | Status |
|-----------|-----------|--------|
| 9.1 | `FederationGateway` — peer registry + mTLS | ✅ spec + wiki |
| 9.2 | `FederatedBlackboard` — CRDT event log | ✅ spec + wiki |
| **9.3** | **`FederatedTaskRouter` — load-aware dispatch** | 🟡 in progress |
| 9.4 | `FederatedConsensus` — quorum voting | 🔜 planned |
| 9.5 | `FederationHealthMonitor` — observability | 🔜 planned |

→ **Discussions**: [#307 Show & Tell](https://github.com/web3guru888/asi-build/discussions/307) · [#308 Q&A](https://github.com/web3guru888/asi-build/discussions/308) · [#309 Ideas (9.4)](https://github.com/web3guru888/asi-build/discussions/309)  
→ **Issue**: [#306](https://github.com/web3guru888/asi-build/issues/306)
