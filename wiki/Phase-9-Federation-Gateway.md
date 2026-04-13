# Phase 9.1 — FederationGateway: mTLS peer registry and message routing

Phase 9.1 opens the **Multi-Agent Federation** track.  `FederationGateway` is the foundational component: every ASI-Build node runs one instance, maintaining a live registry of peer nodes and providing authenticated message routing between them.

---

## Motivation

| Gap | Solution |
|-----|---------|
| Single-node cognitive bottleneck | Route tasks to least-loaded peer via Phase 9.3 |
| No inter-node trust model | DID-based identity + mTLS authentication |
| No peer discovery | Gossip-based membership bootstrap |
| No federation observability | `federation_*` Prometheus metrics per node |
| Incompatible blackboard namespaces | FederatedBlackboard in Phase 9.2 |

---

## Data model

### `PeerRecord` — frozen dataclass

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet

@dataclass(frozen=True)
class PeerRecord:
    peer_id: str           # DID string, e.g. "did:key:z6Mk..."
    endpoint: str          # "https://peer-host:8443"
    public_key_pem: str    # PEM-encoded Ed25519 public key
    capabilities: FrozenSet[str] = field(default_factory=frozenset)
    joined_at_ms: int = 0  # Unix ms — set by registry on join
```

**Why frozen?**  Immutability ensures peer records can be safely shared across async tasks without locking every read.

### `PeerStatus` — enum

```python
from enum import Enum, auto

class PeerStatus(Enum):
    HEALTHY     = auto()
    DEGRADED    = auto()    # health check latency > 500 ms
    UNREACHABLE = auto()    # 3 consecutive failures
    EVICTED     = auto()    # TTL expired or manual removal
```

### `GatewaySnapshot` — frozen dataclass

```python
@dataclass(frozen=True)
class GatewaySnapshot:
    local_peer_id: str
    peers: tuple[PeerRecord, ...]
    peer_statuses: dict[str, PeerStatus]
    total_messages_sent: int
    total_messages_failed: int
    uptime_ms: int
```

---

## `FederationGateway` Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class FederationGateway(Protocol):
    async def register_peer(self, record: PeerRecord) -> None: ...
    async def deregister_peer(self, peer_id: str) -> None: ...
    async def get_peer(self, peer_id: str) -> PeerRecord | None: ...
    async def list_peers(
        self, status: PeerStatus | None = None
    ) -> list[PeerRecord]: ...
    async def send_message(
        self, peer_id: str, payload: bytes, timeout_ms: int = 5_000
    ) -> bytes: ...
    async def broadcast(
        self, payload: bytes, exclude: frozenset[str] = frozenset()
    ) -> dict[str, bytes | Exception]: ...
    def snapshot(self) -> GatewaySnapshot: ...
```

---

## `InMemoryFederationGateway` — concrete implementation

### Init

```python
class InMemoryFederationGateway:
    def __init__(
        self,
        local_record: PeerRecord,
        seed_peers: list[str] = (),
        ttl_ms: int = 300_000,
        health_interval_s: float = 30.0,
        _transport: Callable[[str, bytes], Awaitable[bytes]] | None = None,
        _registry: CollectorRegistry | None = None,
    ) -> None:
        self._local = local_record
        self._peers: dict[str, PeerRecord] = {}
        self._status: dict[str, PeerStatus] = {}
        self._fail_counts: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._ttl_ms = ttl_ms
        self._health_interval_s = health_interval_s
        self._seed_peers = list(seed_peers)
        self._transport = _transport or self._default_transport
        self._metrics = _init_metrics(_registry)
        self._health_task: asyncio.Task[None] | None = None
        self._evict_task: asyncio.Task[None] | None = None
        self._started_at_ms = int(time.time() * 1000)
```

### Peer status FSM

```
        register()
            │
            ▼
        HEALTHY ◄──────── health_ok (latency < 500ms)
            │
    latency > 500ms
            │
            ▼
        DEGRADED
            │
     3 consecutive failures
            │
            ▼
      UNREACHABLE
            │
    deregister() / TTL
            │
            ▼
        EVICTED
```

### `register_peer()` / `deregister_peer()`

```python
async def register_peer(self, record: PeerRecord) -> None:
    async with self._lock:
        self._peers[record.peer_id] = record
        self._status.setdefault(record.peer_id, PeerStatus.HEALTHY)
        self._fail_counts[record.peer_id] = 0

async def deregister_peer(self, peer_id: str) -> None:
    async with self._lock:
        self._peers.pop(peer_id, None)
        self._status[peer_id] = PeerStatus.EVICTED
```

### `send_message()` + timeout guard

```python
async def send_message(
    self, peer_id: str, payload: bytes, timeout_ms: int = 5_000
) -> bytes:
    record = self._peers.get(peer_id)
    if record is None:
        raise KeyError(f"Unknown peer: {peer_id}")
    try:
        result = await asyncio.wait_for(
            self._transport(record.endpoint, payload),
            timeout=timeout_ms / 1000,
        )
        self._metrics["sent"].labels(peer_id=peer_id).inc()
        return result
    except Exception as exc:
        self._metrics["failed"].labels(
            peer_id=peer_id, reason=type(exc).__name__
        ).inc()
        raise
```

### `broadcast()` fan-out

```python
async def broadcast(
    self, payload: bytes, exclude: frozenset[str] = frozenset()
) -> dict[str, bytes | Exception]:
    peers = [pid for pid in self._peers if pid not in exclude]
    tasks = [self.send_message(pid, payload) for pid in peers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    self._metrics["broadcasts"].inc()
    return dict(zip(peers, results))
```

### Health poll loop

```python
async def _health_poll_loop(self) -> None:
    while True:
        await asyncio.sleep(self._health_interval_s)
        async with self._lock:
            peer_ids = list(self._peers)
        for pid in peer_ids:
            await self._check_peer_health(pid)

async def _check_peer_health(self, peer_id: str) -> None:
    record = self._peers.get(peer_id)
    if record is None:
        return
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(
            self._transport(record.endpoint + "/health", b""),
            timeout=0.5,
        )
        latency = time.monotonic() - t0
        self._fail_counts[peer_id] = 0
        new_status = (
            PeerStatus.HEALTHY if latency < 0.5 else PeerStatus.DEGRADED
        )
    except Exception:
        self._fail_counts[peer_id] = self._fail_counts.get(peer_id, 0) + 1
        new_status = (
            PeerStatus.UNREACHABLE
            if self._fail_counts[peer_id] >= 3
            else PeerStatus.DEGRADED
        )
    self._status[peer_id] = new_status
    self._metrics["peers_total"].labels(status=new_status.name).set(
        sum(1 for s in self._status.values() if s == new_status)
    )
```

### TTL eviction loop

```python
async def _evict_stale_peers(self) -> None:
    while True:
        await asyncio.sleep(60)  # check every minute
        now_ms = int(time.time() * 1000)
        async with self._lock:
            stale = [
                pid
                for pid, rec in self._peers.items()
                if now_ms - rec.joined_at_ms > self._ttl_ms
                and self._status.get(pid) != PeerStatus.HEALTHY
            ]
            for pid in stale:
                del self._peers[pid]
                self._status[pid] = PeerStatus.EVICTED
```

---

## `build_federation_gateway()` — factory

```python
def build_federation_gateway(
    local_peer_id: str,
    endpoint: str,
    public_key_pem: str,
    capabilities: frozenset[str] = frozenset(),
    seed_peers: list[str] = (),
    ttl_ms: int = 300_000,
    health_interval_s: float = 30.0,
    _transport: Callable | None = None,
    _registry: CollectorRegistry | None = None,
) -> InMemoryFederationGateway:
    local = PeerRecord(
        peer_id=local_peer_id,
        endpoint=endpoint,
        public_key_pem=public_key_pem,
        capabilities=capabilities,
        joined_at_ms=int(time.time() * 1000),
    )
    return InMemoryFederationGateway(
        local_record=local,
        seed_peers=seed_peers,
        ttl_ms=ttl_ms,
        health_interval_s=health_interval_s,
        _transport=_transport,
        _registry=_registry,
    )
```

---

## CognitiveCycle integration

`FederationGateway` runs as a long-lived service alongside the `CognitiveCycle`.  During the **PERCEPTION** phase, the `FederatedTaskRouter` (Phase 9.3) queries `gateway.list_peers(status=PeerStatus.HEALTHY)` to select a peer for offloaded tasks.

```python
# In CognitiveCycle.run() startup sequence
gw = build_federation_gateway(
    local_peer_id=config.did,
    endpoint=config.endpoint,
    public_key_pem=config.public_key_pem,
    capabilities=frozenset(config.capabilities),
    seed_peers=config.seed_peers,
)
# Start background tasks
asyncio.create_task(gw._health_poll_loop())
asyncio.create_task(gw._evict_stale_peers())
await gw._bootstrap_from_seeds()
```

---

## Prometheus metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `federation_peers_total` | Gauge | `status` | Live peer count by status |
| `federation_messages_sent_total` | Counter | `peer_id` | Outbound messages per peer |
| `federation_messages_failed_total` | Counter | `peer_id`, `reason` | Failed sends |
| `federation_health_check_duration_seconds` | Histogram | `peer_id` | Health poll latency |
| `federation_broadcast_fan_out_total` | Counter | — | Broadcast events |

### Key PromQL queries

```promql
# Isolated node alert
federation_peers_total{status="HEALTHY"} == 0

# Message failure rate per peer
rate(federation_messages_failed_total[5m])
  / ignoring(reason) group_left
  rate(federation_messages_sent_total[5m])

# Health check latency p95
histogram_quantile(0.95,
  rate(federation_health_check_duration_seconds_bucket[5m]))
```

---

## Test targets (12 minimum)

```
test_register_and_retrieve_peer
test_deregister_peer_updates_status_to_evicted
test_list_peers_filters_by_status
test_list_peers_returns_all_when_status_is_none
test_send_message_calls_transport_with_endpoint_and_payload
test_send_message_timeout_raises_and_increments_failed_counter
test_broadcast_fan_out_collects_all_results_including_errors
test_broadcast_excludes_specified_peers
test_health_poller_marks_degraded_on_slow_response
test_health_poller_marks_unreachable_after_three_failures
test_ttl_eviction_removes_stale_unhealthy_peers
test_snapshot_reflects_current_peers_and_statuses
```

---

## mypy annotations

| Symbol | Type |
|--------|------|
| `_peers` | `dict[str, PeerRecord]` |
| `_status` | `dict[str, PeerStatus]` |
| `_fail_counts` | `dict[str, int]` |
| `_transport` | `Callable[[str, bytes], Awaitable[bytes]]` |
| `_lock` | `asyncio.Lock` |
| `_health_task` | `asyncio.Task[None] \| None` |
| `_evict_task` | `asyncio.Task[None] \| None` |

---

## Implementation order (14 steps)

1. `PeerRecord`, `PeerStatus`, `GatewaySnapshot` dataclasses
2. `FederationGateway` Protocol + `@runtime_checkable`
3. `InMemoryFederationGateway.__init__()` + lock + peer dict
4. `register_peer()` / `deregister_peer()` / `get_peer()` / `list_peers()`
5. `_default_transport()` (`aiohttp` stub)
6. `send_message()` + timeout guard + Prometheus counter
7. `broadcast()` + `asyncio.gather` fan-out
8. `_check_peer_health()` + status FSM
9. `_health_poll_loop()` background task
10. `_evict_stale_peers()` background task
11. `_bootstrap_from_seeds()` gossip bootstrap
12. Prometheus pre-init in `__init__()`
13. `snapshot()` method
14. `build_federation_gateway()` factory + 12 unit tests

---

## Phase 9 roadmap

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| **9.1** | `FederationGateway` — peer registry + mTLS | #299 | 🟡 this phase |
| 9.2 | `FederatedBlackboard` — CRDT event log + Lamport clocks | — | 🔜 planned |
| 9.3 | `FederatedTaskRouter` — load-aware task dispatch | — | 🔜 planned |
| 9.4 | `FederatedConsensus` — BFT-lite voting | — | 🔜 planned |
| 9.5 | `FederationHealthMonitor` — Prometheus aggregation | — | 🔜 planned |
