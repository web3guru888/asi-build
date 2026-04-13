# Phase 9.5 — FederationHealthMonitor

Unified health aggregator for the Phase 9 federation layer — polls all four federation components, computes a weighted `overall_score`, exposes an SSE health stream, and trips a cluster-level circuit breaker when the federation degrades.

> **Status**: 🟡 Spec complete — Issue #315  
> **Depends on**: Phase 9.1 FederationGateway · Phase 9.2 FederatedBlackboard · Phase 9.3 FederatedTaskRouter · Phase 9.4 FederatedConsensus  
> **Discussions**: #316 (Show & Tell) · #317 (Q&A) · #318 (Phase 10 Ideas)

---

## Table of Contents

1. [Motivation](#motivation)
2. [Data Model](#data-model)
3. [Protocol — `FederationHealthMonitor`](#protocol--federationhealthmonitor)
4. [Concrete Implementation](#concrete-implementation--inmemoryfederationhealthmonitor)
5. [Component Scoring](#component-scoring-functions)
6. [Circuit Breaker](#circuit-breaker)
7. [SSE Health Stream](#sse-health-stream)
8. [Factory](#factory)
9. [CognitiveCycle Integration](#cognitivecycle-integration)
10. [Prometheus Metrics](#prometheus-metrics)
11. [mypy Compliance](#mypy-compliance)
12. [Test Targets](#test-targets)
13. [Implementation Order](#14-step-implementation-order)
14. [Phase 9 Roadmap](#phase-9-roadmap)

---

## Motivation

Phase 9 introduces four independently operating federation components:

| Component | Failure Mode |
|-----------|-------------|
| FederationGateway | Peers go offline; connectivity lost |
| FederatedBlackboard | CRDT clock drift; subscriber starvation |
| FederatedTaskRouter | All strategies fail; excessive FALLBACK routing |
| FederatedConsensus | Proposal storm; persistent abort loop |

Without a unified health view, operators must query four separate `snapshot()` calls and mentally aggregate the results. `FederationHealthMonitor` automates this aggregation, exposes it as a single SSE stream, and opens a circuit breaker before cascading failures propagate.

---

## Data Model

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Optional, Tuple
import time

class ComponentHealth(str, Enum):
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    FAILED   = "failed"

@dataclass(frozen=True)
class ComponentScore:
    name:        str               # "gateway" | "blackboard" | "router" | "consensus"
    health:      ComponentHealth
    score:       float             # 0.0 – 1.0
    details:     str               # human-readable summary
    snapshot_ms: int               # epoch ms when snapshot was taken

@dataclass(frozen=True)
class FederationHealthEvent:
    """Emitted on every health poll tick."""
    timestamp_ms:    int
    components:      Tuple[ComponentScore, ...]   # always 4 entries
    overall_score:   float                        # weighted sum
    circuit_open:    bool
    consecutive_low: int

@dataclass
class HealthMonitorSnapshot:
    poll_interval_ms:    int
    last_poll_ms:        int
    overall_score:       float
    circuit_open:        bool
    consecutive_low:     int
    total_polls:         int
    total_circuit_trips: int
```

---

## Protocol — `FederationHealthMonitor`

```python
from typing import runtime_checkable, Protocol

@runtime_checkable
class FederationHealthMonitor(Protocol):
    async def start(self) -> None:
        """Start the background poll loop."""
        ...

    async def stop(self) -> None:
        """Cancel the poll loop and drain subscribers."""
        ...

    async def health_stream(self) -> AsyncIterator[FederationHealthEvent]:
        """Subscribe to health events. Yields one event per poll tick."""
        ...

    async def snapshot(self) -> HealthMonitorSnapshot:
        """Return current monitor state without waiting for next poll."""
        ...

    async def reset_circuit(self) -> None:
        """Manually close the circuit breaker (ops override)."""
        ...
```

---

## Concrete Implementation — `InMemoryFederationHealthMonitor`

### `__init__`

```python
import asyncio
import contextlib
from prometheus_client import Counter, Gauge, CollectorRegistry

class InMemoryFederationHealthMonitor:
    def __init__(
        self,
        gateway:    FederationGateway,
        blackboard: FederatedBlackboard,
        router:     FederatedTaskRouter,
        consensus:  FederatedConsensus,
        *,
        interval_s:  float = 5.0,
        threshold:   float = 0.5,
        trip_count:  int   = 3,
        registry:    Optional[CollectorRegistry] = None,
    ) -> None:
        self._gateway    = gateway
        self._blackboard = blackboard
        self._router     = router
        self._consensus  = consensus
        self._interval_s = interval_s
        self._threshold  = threshold
        self._trip_count = trip_count

        self._running:           bool  = False
        self._task:              Optional[asyncio.Task] = None
        self._last_event:        Optional[FederationHealthEvent] = None
        self._consecutive_low:   int   = 0
        self._circuit_was_open:  bool  = False
        self._total_polls:       int   = 0
        self._total_trips:       int   = 0
        self._subscribers:       set[asyncio.Queue[FederationHealthEvent]] = set()

        # Prometheus
        reg = registry or CollectorRegistry()
        self._gauge_score    = Gauge("asi_federation_health_score",
                                     "Health score per component",
                                     ["component"], registry=reg)
        self._ctr_polls      = Counter("asi_federation_health_polls_total",
                                       "Total poll iterations", registry=reg)
        self._ctr_trips      = Counter("asi_federation_circuit_trips_total",
                                       "Total circuit breaker trips", registry=reg)
        self._gauge_circuit  = Gauge("asi_federation_circuit_open",
                                     "1 if circuit breaker is open", registry=reg)
        self._gauge_comp     = Gauge("asi_federation_component_health",
                                     "1 for current health state",
                                     ["component", "health"], registry=reg)

        # Pre-initialise to prevent missing-series errors in Grafana
        for comp in ("gateway", "blackboard", "router", "consensus", "overall"):
            self._gauge_score.labels(component=comp).set(0)
        for comp in ("gateway", "blackboard", "router", "consensus"):
            for h in ("healthy", "degraded", "failed"):
                self._gauge_comp.labels(component=comp, health=h).set(0)
        self._gauge_circuit.set(0)
```

### `start` / `stop`

```python
async def start(self) -> None:
    if self._running:
        return
    self._running = True
    self._task = asyncio.create_task(self._poll_loop())

async def stop(self) -> None:
    self._running = False
    if self._task is not None:
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
```

### `_poll_loop`

```python
async def _poll_loop(self) -> None:
    while self._running:
        await asyncio.sleep(self._interval_s)
        event = await self._collect()
        self._last_event = event
        self._total_polls += 1
        self._ctr_polls.inc()
        self._broadcast(event)
        self._update_metrics(event)
```

### `_collect`

```python
async def _collect(self) -> FederationHealthEvent:
    gw_snap = await self._gateway.snapshot()
    bb_snap = await self._blackboard.snapshot()
    rt_snap = await self._router.snapshot()
    cs_snap = await self._consensus.snapshot()

    scores = (
        _score_gateway(gw_snap),
        _score_blackboard(bb_snap),
        _score_router(rt_snap),
        _score_consensus(cs_snap),
    )
    overall = (
        0.30 * scores[0].score +
        0.25 * scores[1].score +
        0.25 * scores[2].score +
        0.20 * scores[3].score
    )
    if overall < self._threshold:
        self._consecutive_low += 1
    else:
        self._consecutive_low = 0

    circuit_open = self._consecutive_low >= self._trip_count
    if circuit_open and not self._circuit_was_open:
        self._total_trips += 1
        self._ctr_trips.inc()
    self._circuit_was_open = circuit_open

    return FederationHealthEvent(
        timestamp_ms=_now(),
        components=scores,
        overall_score=overall,
        circuit_open=circuit_open,
        consecutive_low=self._consecutive_low,
    )
```

### `_broadcast`

```python
def _broadcast(self, event: FederationHealthEvent) -> None:
    """Fan-out to all subscribers. Evict slow consumers."""
    dead: set[asyncio.Queue] = set()
    for q in self._subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.add(q)
    self._subscribers -= dead
```

### `_update_metrics`

```python
def _update_metrics(self, event: FederationHealthEvent) -> None:
    self._gauge_score.labels(component="overall").set(event.overall_score)
    self._gauge_circuit.set(1 if event.circuit_open else 0)
    for comp_score in event.components:
        self._gauge_score.labels(component=comp_score.name).set(comp_score.score)
        for h in ("healthy", "degraded", "failed"):
            self._gauge_comp.labels(component=comp_score.name, health=h).set(
                1 if comp_score.health.value == h else 0
            )
```

---

## Component Scoring Functions

Module-level pure functions — independently unit-testable without instantiating the monitor.

```python
def _now() -> int:
    return int(time.time() * 1000)

def _score_gateway(snap: GatewaySnapshot) -> ComponentScore:
    if snap.known_peers == 0:
        return ComponentScore("gateway", ComponentHealth.FAILED, 0.0, "no peers", _now())
    ratio = min(1.0, max(0.0, snap.healthy_peers / snap.known_peers))
    health = (ComponentHealth.HEALTHY  if ratio >= 0.8 else
              ComponentHealth.DEGRADED if ratio >= 0.4 else
              ComponentHealth.FAILED)
    return ComponentScore("gateway", health, ratio,
                          f"{snap.healthy_peers}/{snap.known_peers} healthy peers", _now())

def _score_blackboard(snap: BlackboardSnapshot) -> ComponentScore:
    score = 1.0
    if snap.clock_drift_ms > 500:   score -= 0.4
    elif snap.clock_drift_ms > 200: score -= 0.2
    if snap.subscriber_count == 0:  score -= 0.2
    score = max(0.0, score)
    health = (ComponentHealth.HEALTHY  if score >= 0.8 else
              ComponentHealth.DEGRADED if score >= 0.4 else
              ComponentHealth.FAILED)
    return ComponentScore("blackboard", health, score,
                          f"drift={snap.clock_drift_ms}ms subs={snap.subscriber_count}", _now())

def _score_router(snap: RouterSnapshot) -> ComponentScore:
    fallback_ratio = snap.fallback_count / max(1, snap.total_routed)
    score = max(0.0, 1.0 - min(1.0, fallback_ratio * 2))   # 50% fallback → score 0.0
    health = (ComponentHealth.HEALTHY  if score >= 0.8 else
              ComponentHealth.DEGRADED if score >= 0.4 else
              ComponentHealth.FAILED)
    return ComponentScore("router", health, score,
                          f"fallback={fallback_ratio:.1%}", _now())

def _score_consensus(snap: ConsensusSnapshot) -> ComponentScore:
    abort_ratio = snap.aborted_count / max(1, snap.committed_count + snap.aborted_count)
    score = max(0.0, 1.0 - min(1.0, abort_ratio * 3))   # 33% abort → score 0.0
    health = (ComponentHealth.HEALTHY  if score >= 0.8 else
              ComponentHealth.DEGRADED if score >= 0.4 else
              ComponentHealth.FAILED)
    return ComponentScore("consensus", health, score,
                          f"abort_ratio={abort_ratio:.1%}", _now())
```

---

## Circuit Breaker

```
CLOSED ──[consecutive_low >= trip_count]──► OPEN
OPEN   ──[reset_circuit() called]──────────► CLOSED
```

- **No automatic re-close** — in a BFT system, recovery from cluster-wide failure requires human confirmation
- `reset_circuit()` resets `consecutive_low = 0`; circuit is immediately CLOSED on the next poll
- Add `auto_reset_after_s` parameter if your deployment requires automated recovery

```python
async def reset_circuit(self) -> None:
    self._consecutive_low = 0
    self._circuit_was_open = False
```

### Wiring with FederatedTaskRouter

The circuit breaker does **not** automatically block `FederatedTaskRouter.route()`. Wire it in a guard function:

```python
async def route_with_health_guard(
    task:    TaskEnvelope,
    router:  FederatedTaskRouter,
    monitor: FederationHealthMonitor,
) -> RoutingResult:
    snap = await monitor.snapshot()
    if snap.circuit_open:
        return RoutingResult(decision=RoutingDecision.FALLBACK, target_peer=None,
                             reason="health_monitor: circuit open")
    return await router.route(task)
```

---

## SSE Health Stream

```python
async def health_stream(self) -> AsyncIterator[FederationHealthEvent]:
    queue: asyncio.Queue[FederationHealthEvent] = asyncio.Queue(maxsize=100)
    self._subscribers.add(queue)
    try:
        while True:
            yield await queue.get()
    finally:
        self._subscribers.discard(queue)
```

### FastAPI integration

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

@app.get("/federation/health/stream")
async def health_stream_endpoint(
    monitor: FederationHealthMonitor = Depends(get_monitor),
):
    async def generate():
        async for event in monitor.health_stream():
            data = json.dumps({
                "overall_score": event.overall_score,
                "circuit_open":  event.circuit_open,
                "components": [
                    {"name": c.name, "score": c.score, "health": c.health}
                    for c in event.components
                ],
            })
            yield f"data: {data}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## Factory

```python
def build_health_monitor(
    gateway:    FederationGateway,
    blackboard: FederatedBlackboard,
    router:     FederatedTaskRouter,
    consensus:  FederatedConsensus,
    *,
    poll_interval_ms: int   = 5_000,
    score_threshold:  float = 0.5,
    trip_count:       int   = 3,
    registry:         Optional[CollectorRegistry] = None,
) -> FederationHealthMonitor:
    return InMemoryFederationHealthMonitor(
        gateway, blackboard, router, consensus,
        interval_s=poll_interval_ms / 1000,
        threshold=score_threshold,
        trip_count=trip_count,
        registry=registry,
    )
```

---

## CognitiveCycle Integration

```python
class CognitiveCycle:
    def __init__(
        self,
        ...,
        health_monitor: Optional[FederationHealthMonitor] = None,
    ) -> None:
        self._health_monitor = health_monitor

    async def _phase_federation(self) -> None:
        if self._health_monitor is None:
            return
        snap = await self._health_monitor.snapshot()
        if snap.circuit_open:
            self._blackboard.write(
                "federation.circuit_open", True, source="health_monitor"
            )
            return   # pause all federation operations this tick
        self._blackboard.write(
            "federation.overall_score", snap.overall_score, source="health_monitor"
        )
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_federation_health_score` | Gauge | `component` | Health score 0.0–1.0 per component + "overall" |
| `asi_federation_health_polls_total` | Counter | — | Total poll loop iterations |
| `asi_federation_circuit_trips_total` | Counter | — | Total circuit breaker trips |
| `asi_federation_circuit_open` | Gauge | — | 1 if circuit is currently open |
| `asi_federation_component_health` | Gauge | `component`, `health` | 1 for the current health state enum value |

### PromQL Examples

```promql
# Overall federation health score
asi_federation_health_score{component="overall"}

# Which component is failing?
asi_federation_component_health{health="failed"} == 1

# Circuit breaker open?
asi_federation_circuit_open == 1

# Poll rate (polls per minute)
rate(asi_federation_health_polls_total[1m]) * 60
```

### Alert Rules

```yaml
groups:
  - name: federation_health
    rules:
      - alert: FederationCircuitOpen
        expr: asi_federation_circuit_open == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Federation circuit breaker open"
          runbook: "Call reset_circuit() after verifying all components — Issue #315"

      - alert: FederationHealthDegraded
        expr: asi_federation_health_score{component="overall"} < 0.6
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Federation overall health below 60% for 5 minutes"
```

---

## mypy Compliance

| Symbol | Declared type | Notes |
|--------|--------------|-------|
| `FederationHealthMonitor` | `@runtime_checkable Protocol` | Interface contract |
| `InMemoryFederationHealthMonitor` | concrete class | Pass to `isinstance()` checks |
| `FederationHealthEvent.components` | `Tuple[ComponentScore, ...]` | Always 4 entries |
| `FederationHealthEvent.overall_score` | `float` | Always in [0.0, 1.0] |
| `_subscribers` | `set[asyncio.Queue[FederationHealthEvent]]` | Generic Queue for mypy |
| `_last_event` | `Optional[FederationHealthEvent]` | None until first poll |
| `_task` | `Optional[asyncio.Task[None]]` | Started in `start()` |

---

## Test Targets

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_score_gateway_all_healthy` | 12/12 peers → score=1.0, HEALTHY |
| 2 | `test_score_gateway_no_peers` | known_peers=0 → FAILED, score=0.0 |
| 3 | `test_score_gateway_degraded` | 6/12 peers → DEGRADED |
| 4 | `test_score_blackboard_high_drift` | clock_drift_ms=600 → score≤0.6 |
| 5 | `test_score_router_high_fallback` | fallback_count=60, total=100 → FAILED |
| 6 | `test_score_consensus_high_abort` | aborted=4, committed=6 → DEGRADED |
| 7 | `test_poll_loop_emits_events` | 3 ticks → 3 FederationHealthEvent objects |
| 8 | `test_circuit_breaker_trips` | 3 consecutive low-score polls → circuit_open=True |
| 9 | `test_circuit_breaker_reset` | reset_circuit() → circuit_open=False on next snapshot |
| 10 | `test_health_stream_subscriber` | subscriber receives events via async generator |
| 11 | `test_snapshot_reflects_state` | snapshot() matches last poll state |
| 12 | `test_build_health_monitor_factory` | factory returns `InMemoryFederationHealthMonitor` |

---

## 14-Step Implementation Order

1. `ComponentHealth` enum
2. `ComponentScore` frozen dataclass
3. `FederationHealthEvent` frozen dataclass
4. `HealthMonitorSnapshot` dataclass
5. `FederationHealthMonitor` Protocol (`@runtime_checkable`)
6. `_score_gateway()` pure function + unit tests
7. `_score_blackboard()` pure function + unit tests
8. `_score_router()` pure function + unit tests
9. `_score_consensus()` pure function + unit tests
10. `InMemoryFederationHealthMonitor.__init__()` — inject 4 components + Prometheus pre-init
11. `_collect()` — call snapshots, weighted score, circuit logic
12. `_poll_loop()` — `asyncio.sleep` + `_broadcast()`
13. `health_stream()` — subscriber queue + eviction; `snapshot()` + `reset_circuit()` + `start()` / `stop()`
14. `build_health_monitor()` factory

---

## Phase 9 Roadmap

| Sub-phase | Component | Issue | Wiki |
|-----------|-----------|-------|------|
| 9.1 | FederationGateway | #299 | [Phase-9-Federation-Gateway](Phase-9-Federation-Gateway) |
| 9.2 | FederatedBlackboard | #302 | [Phase-9-Federated-Blackboard](Phase-9-Federated-Blackboard) |
| 9.3 | FederatedTaskRouter | #306 | [Phase-9-Federated-Task-Router](Phase-9-Federated-Task-Router) |
| 9.4 | FederatedConsensus | #310 | [Phase-9-Federated-Consensus](Phase-9-Federated-Consensus) |
| 9.5 | FederationHealthMonitor | #315 | **this page** |
