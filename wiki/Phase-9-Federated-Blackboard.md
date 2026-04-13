# Phase 9.2 — FederatedBlackboard: CRDT event log and Lamport-ordered state synchronisation

Phase 9.2 extends the multi-agent federation stack with `FederatedBlackboard` — a replicated, conflict-free blackboard that lets multiple ASI-Build nodes share cognitive state without a central coordinator.  Every write is wrapped in a `BlackboardEvent` with a Lamport clock timestamp, so events from any peer can be merged consistently without locks or consensus rounds.

---

## Motivation

| Gap | Solution |
|-----|---------|
| Nodes hold independent, diverging blackboard state | CRDT merge: last-write-wins per key with Lamport ordering |
| No mechanism to broadcast writes to peers | `FederationGateway.broadcast()` delivers `BlackboardEvent` envelopes |
| No partial sync (expensive full state transfer) | Delta-sync: only events with `lamport > peer_hwm` are sent |
| Reordering under network jitter | Delivery buffer: hold events until causal gap is bridged |
| No observability of replication lag | `federated_bb_lag_events` Prometheus gauge per peer |

---

## Data model

### `LamportClock` — thread-safe monotone counter

```python
from threading import Lock

class LamportClock:
    """Thread-safe Lamport logical clock."""
    def __init__(self) -> None:
        self._t: int = 0
        self._lock = Lock()

    def tick(self) -> int:
        """Increment and return new timestamp (local event)."""
        with self._lock:
            self._t += 1
            return self._t

    def update(self, received: int) -> int:
        """Merge received timestamp (on message receipt): t = max(t, received) + 1."""
        with self._lock:
            self._t = max(self._t, received) + 1
            return self._t

    @property
    def value(self) -> int:
        with self._lock:
            return self._t
```

**Why Lamport instead of wall-clock?**  Wall-clock skew across nodes can be tens of milliseconds.  Lamport counters give a consistent total order that reflects causality, not time.

### `BlackboardEvent` — frozen dataclass

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass(frozen=True)
class BlackboardEvent:
    key: str                        # blackboard slot key
    value: Any                      # serialisable payload
    lamport: int                    # Lamport clock of originating node
    origin_peer_id: str             # DID of writing node
    sequence: int                   # per-peer monotone sequence number
    phase: str = "UNKNOWN"          # CyclePhase name for context
    ttl_ms: Optional[int] = None    # 0/None → no expiry
    vector_clock: dict[str, int] = field(default_factory=dict)
    # vector_clock maps peer_id → last known Lamport at write time
```

**Key field rationale:**

| Field | Rationale |
|-------|-----------|
| `lamport` | Total ordering across peers without wall-clock skew |
| `sequence` | Per-peer gap detection — gaps trigger delta-sync request |
| `vector_clock` | Optional causality tracking; enables `happened-before` queries |
| `ttl_ms` | Entries auto-expire from local cache; not propagated as deletes |

### `BlackboardSnapshot` — immutable view

```python
@dataclass(frozen=True)
class BlackboardSnapshot:
    entries: dict[str, Any]              # key → latest value
    lamport: int                          # current clock value
    event_count: int                      # total events merged (all-time)
    peer_hwm: dict[str, int]             # peer_id → highest Lamport merged
    pending_events: int                   # delivery-buffer depth
    ttl_evictions: int                    # entries expired since start
```

---

## `FederatedBlackboard` Protocol

```python
from typing import Protocol, runtime_checkable, AsyncIterator

@runtime_checkable
class FederatedBlackboard(Protocol):
    async def write(self, key: str, value: Any, phase: str = "UNKNOWN") -> BlackboardEvent:
        """Write locally + broadcast event to all federation peers."""
        ...

    async def read(self, key: str) -> Any:
        """Return latest (highest Lamport) value for key, or raise KeyError."""
        ...

    async def merge(self, event: BlackboardEvent) -> bool:
        """Accept a remote event; returns True if it advanced local state."""
        ...

    async def delta_sync(self, peer_id: str, since_lamport: int) -> list[BlackboardEvent]:
        """Return all local events with lamport > since_lamport for catch-up."""
        ...

    async def subscribe(self, key: str) -> AsyncIterator[BlackboardEvent]:
        """Async generator yielding new events for a key as they arrive."""
        ...

    def snapshot(self) -> BlackboardSnapshot:
        """Return immutable snapshot of current state."""
        ...
```

---

## `InMemoryFederatedBlackboard` — reference implementation

```python
import asyncio, time
from collections import defaultdict
from typing import Any

class InMemoryFederatedBlackboard:
    def __init__(
        self,
        peer_id: str,
        gateway: FederationGateway,
        delivery_buffer_ms: int = 50,   # max wait to bridge causal gap
        max_events: int = 10_000,        # ring-buffer cap for delta-sync
    ) -> None:
        self._peer_id = peer_id
        self._gateway = gateway
        self._clock = LamportClock()
        self._state: dict[str, tuple[int, Any]] = {}   # key → (lamport, value)
        self._log: list[BlackboardEvent] = []           # append-only (capped)
        self._hwm: dict[str, int] = defaultdict(int)   # peer → max lamport seen
        self._seq: dict[str, int] = defaultdict(int)   # peer → next expected seq
        self._buffer: list[BlackboardEvent] = []        # out-of-order buffer
        self._lock = asyncio.Lock()
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._max_events = max_events
        self._delivery_buffer_ms = delivery_buffer_ms
        self._ttl_evictions = 0
```

### `write()` — local write + broadcast

```python
    async def write(self, key: str, value: Any, phase: str = "UNKNOWN") -> BlackboardEvent:
        async with self._lock:
            lamport = self._clock.tick()
            seq = self._seq[self._peer_id]
            self._seq[self._peer_id] = seq + 1
            event = BlackboardEvent(
                key=key,
                value=value,
                lamport=lamport,
                origin_peer_id=self._peer_id,
                sequence=seq,
                phase=phase,
                vector_clock={self._peer_id: lamport},
            )
            self._apply(event)
        await self._gateway.broadcast(event)
        return event
```

### `merge()` — accept remote event with gap detection

```python
    async def merge(self, event: BlackboardEvent) -> bool:
        async with self._lock:
            expected_seq = self._seq[event.origin_peer_id]
            if event.sequence < expected_seq:
                return False  # duplicate — already applied
            if event.sequence > expected_seq:
                self._buffer.append(event)
                return False  # causal gap — trigger delta-sync
            self._clock.update(event.lamport)
            self._seq[event.origin_peer_id] = event.sequence + 1
            return self._apply(event)
```

### `_apply()` — inner state machine (lock held)

```python
    def _apply(self, event: BlackboardEvent) -> bool:
        key, lamport, value = event.key, event.lamport, event.value
        current = self._state.get(key)
        if current is None or lamport > current[0]:
            self._state[key] = (lamport, value)
            self._hwm[event.origin_peer_id] = max(
                self._hwm[event.origin_peer_id], lamport
            )
            if len(self._log) >= self._max_events:
                self._log.pop(0)
            self._log.append(event)
            # fan-out to subscribers
            for q in self._subscribers.get(key, []):
                q.put_nowait(event)
            return True
        return False
```

**Last-write-wins rule:** If two peers write to the same key concurrently, the event with the higher Lamport wins.  Ties are broken by `origin_peer_id` lexicographic order to ensure determinism.

### TTL eviction — background task

```python
    async def _evict_expired(self) -> None:
        """Background task: remove entries whose TTL has elapsed."""
        while True:
            await asyncio.sleep(1)
            now_ms = int(time.monotonic() * 1000)
            async with self._lock:
                expired = [
                    e.key for e in self._log
                    if e.ttl_ms and (e.lamport + e.ttl_ms) < now_ms
                ]
                for key in expired:
                    self._state.pop(key, None)
                    self._ttl_evictions += 1
```

### Delta-sync — catch-up on gap detection

```python
    async def delta_sync(self, peer_id: str, since_lamport: int) -> list[BlackboardEvent]:
        """Return events this node has that the requesting peer is missing."""
        async with self._lock:
            return [e for e in self._log if e.lamport > since_lamport]
```

On detecting a sequence gap the gateway requests catch-up:
```python
missing = await remote_peer.delta_sync(local_peer_id, local_hwm[remote_peer_id])
for event in sorted(missing, key=lambda e: e.lamport):
    await self.merge(event)
```

### `subscribe()` — async generator

```python
    async def subscribe(self, key: str) -> AsyncIterator[BlackboardEvent]:
        q: asyncio.Queue[BlackboardEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers[key].append(q)
        try:
            while True:
                yield await q.get()
        finally:
            async with self._lock:
                self._subscribers[key].remove(q)
```

### `snapshot()` — immutable state view

```python
    def snapshot(self) -> BlackboardSnapshot:
        return BlackboardSnapshot(
            entries={k: v for k, (_, v) in self._state.items()},
            lamport=self._clock.value,
            event_count=len(self._log),
            peer_hwm=dict(self._hwm),
            pending_events=len(self._buffer),
            ttl_evictions=self._ttl_evictions,
        )
```

---

## Factory

```python
def build_federated_blackboard(
    peer_id: str,
    gateway: FederationGateway,
    delivery_buffer_ms: int = 50,
    max_events: int = 10_000,
) -> FederatedBlackboard:
    """Construct and return an InMemoryFederatedBlackboard."""
    bb = InMemoryFederatedBlackboard(
        peer_id=peer_id,
        gateway=gateway,
        delivery_buffer_ms=delivery_buffer_ms,
        max_events=max_events,
    )
    return bb
```

---

## Integration with `CognitiveCycle`

```python
class CognitiveCycle:
    def __init__(
        self,
        ...,
        fed_blackboard: FederatedBlackboard | None = None,
    ):
        self._fed_bb = fed_blackboard

    async def _run_phase(self, phase: CyclePhase) -> None:
        result = await self._dispatch(phase)
        if self._fed_bb:
            await self._fed_bb.write(
                key=f"cycle.{phase.name}",
                value=result,
                phase=phase.name,
            )
```

Every completed cycle phase emits a `BlackboardEvent` that all federation peers can observe and react to in real-time.

---

## 5 Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `federated_bb_events_merged_total` | Counter | `origin_peer_id` | Events successfully merged |
| `federated_bb_events_rejected_total` | Counter | `reason` (`duplicate`\|`gap`) | Events not applied |
| `federated_bb_lag_events` | Gauge | `peer_id` | Delivery-buffer depth (replication lag proxy) |
| `federated_bb_ttl_evictions_total` | Counter | — | Entries expired by TTL eviction task |
| `federated_bb_delta_sync_requests_total` | Counter | `direction` (`sent`\|`recv`) | Delta-sync round-trips |

### Prometheus pre-init

```python
from prometheus_client import Counter, Gauge

BB_MERGED   = Counter("federated_bb_events_merged_total",   "Events merged", ["origin_peer_id"])
BB_REJECTED = Counter("federated_bb_events_rejected_total", "Events rejected", ["reason"])
BB_LAG      = Gauge("federated_bb_lag_events",              "Delivery buffer depth", ["peer_id"])
BB_TTL_EV   = Counter("federated_bb_ttl_evictions_total",   "TTL evictions")
BB_DELTA    = Counter("federated_bb_delta_sync_requests_total", "Delta-sync", ["direction"])
```

### Grafana PromQL panels

```promql
# Replication lag heatmap (delivery buffer depth per peer)
federated_bb_lag_events

# Merge throughput
rate(federated_bb_events_merged_total[1m])

# Rejection rate by reason
rate(federated_bb_events_rejected_total[5m])

# Delta-sync frequency
rate(federated_bb_delta_sync_requests_total[5m])

# TTL eviction rate
rate(federated_bb_ttl_evictions_total[5m])
```

**Alert rule (replication lag):**
```yaml
- alert: FederatedBBHighLag
  expr: sum(federated_bb_lag_events) > 100
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "FederatedBlackboard delivery buffer > 100 events"
```

---

## Mypy Compliance Table

| Class | Generics | `frozen=True` | `Protocol` | Runtime-checkable |
|-------|----------|---------------|------------|-------------------|
| `LamportClock` | — | — | — | — |
| `BlackboardEvent` | — | ✅ | — | — |
| `BlackboardSnapshot` | — | ✅ | — | — |
| `FederatedBlackboard` | — | — | ✅ | ✅ |
| `InMemoryFederatedBlackboard` | — | — | — | — |

---

## 12 Test Targets

| # | Target | Assertion |
|---|--------|-----------|
| 1 | `LamportClock.tick()` | monotone increment (thread-safe) |
| 2 | `LamportClock.update(received > current)` | adopts max+1 |
| 3 | `LamportClock.update(received < current)` | local clock advances past received |
| 4 | `write()` | returns event with correct lamport; `gateway.broadcast` called once |
| 5 | `merge()` — in-order event | state advances, returns `True` |
| 6 | `merge()` — duplicate (`seq < expected`) | returns `False`, state unchanged |
| 7 | `merge()` — out-of-order (seq gap) | buffered, delta-sync triggered |
| 8 | `read()` after concurrent writes from 2 peers | highest Lamport wins |
| 9 | `delta_sync(since_lamport=N)` | returns only events with `lamport > N` |
| 10 | `subscribe(key)` | async generator yields events as they arrive |
| 11 | TTL eviction task | expired entries removed; counter incremented |
| 12 | `snapshot()` | reflects current `entries`, `hwm`, `pending_events` |

### Test isolation

```python
import pytest
from prometheus_client import CollectorRegistry

@pytest.fixture
def registry():
    """Isolated Prometheus registry per test to prevent counter conflicts."""
    return CollectorRegistry()

@pytest.fixture
def mock_gateway(mocker):
    gw = mocker.AsyncMock()
    gw.broadcast = mocker.AsyncMock(return_value=None)
    return gw

@pytest.fixture
def fedbb(mock_gateway):
    return build_federated_blackboard(
        peer_id="did:key:testnode",
        gateway=mock_gateway,
    )
```

---

## 14-Step Implementation Order

1. Add `LamportClock` (thread-safe tick/update with `threading.Lock`)
2. Add `BlackboardEvent` frozen dataclass (all fields + `vector_clock` default factory)
3. Add `BlackboardSnapshot` frozen dataclass
4. Add `FederatedBlackboard` Protocol (`@runtime_checkable`)
5. Add `InMemoryFederatedBlackboard.__init__` (clock, state dict, log list, hwm/seq dicts, lock, subscribers)
6. Implement `_apply()` (last-write-wins, log ring-buffer, subscriber fan-out)
7. Implement `write()` (tick clock, build event, _apply, broadcast)
8. Implement `merge()` (duplicate check, gap check, update clock, _apply)
9. Implement `delta_sync()` (filter log by lamport > since)
10. Implement `_evict_expired()` background task (`asyncio.sleep(1)` loop)
11. Implement `subscribe()` async generator (per-key `asyncio.Queue`)
12. Implement `snapshot()` (build frozen `BlackboardSnapshot`)
13. Add `build_federated_blackboard()` factory
14. Wire optional `fed_blackboard` param into `CognitiveCycle._run_phase()`

---

## Phase 9 Roadmap

| Sub-phase | Component | Key abstractions |
|-----------|-----------|-----------------|
| ✅ 9.1 | `FederationGateway` | PeerRecord, PeerStatus FSM, mTLS, gossip bootstrap |
| ✅ 9.2 | `FederatedBlackboard` | LamportClock, BlackboardEvent, CRDT merge, delta-sync |
| 9.3 | `FederatedTaskRouter` | capability-first routing, load estimation, retry/fallback |
| 9.4 | `FederatedConsensus` | BFT-lite voting, quorum, proposal/commit FSM |
| 9.5 | `FederationHealthMonitor` | cross-node Prometheus aggregation, alert routing |
