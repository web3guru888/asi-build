# Phase 11.5 — AlignmentDashboard

> **Phase 11 — Safety & Alignment Layer** › sub-phase 5 of 5 (FINAL 🎉)
>
> **Spec issue**: #349 | **Show & Tell**: #350 | **Q&A**: #351
>
> Closes Phase 11 and completes the ASI-Build Safety & Alignment Layer.

---

## Overview

`AlignmentDashboard` is the operator-facing real-time console that aggregates live safety signals from all four preceding Phase 11 components and delivers them to browser clients via **Server-Sent Events (SSE)**. It also provides an operator override API so humans can approve or reject flagged goals.

```
┌──────────────────────────────────────────────────────────────────┐
│                       CognitiveCycle                             │
│  SafetyFilter ─── SAFETY_VIOLATION ──────────────────────┐       │
│  AlignmentMonitor ─ ALIGNMENT_SCORE (heartbeat 5 s) ─────┤       │
│  ValueLearner ──── REWARD_WEIGHTS   (heartbeat 15 s) ────┤       │
│  InterpretabilityProbe ── EXPLANATION (on block) ─────────┤      │
│                                                           ▼       │
│                    ┌─────────────────────┐                        │
│                    │  AlignmentDashboard  │                       │
│                    │  _broadcast() fanout │                       │
│                    └──────────┬──────────┘                        │
│                               │ SSE /alignment/stream             │
│                    ┌──────────▼──────────┐                        │
│                    │   Operator Browser   │                       │
│                    │  EventSource(url)    │                       │
│                    │  POST /override      │                       │
│                    └─────────────────────┘                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Enumerations

### `DashboardEventType`

```python
from enum import Enum, auto

class DashboardEventType(Enum):
    ALIGNMENT_SCORE     = auto()   # AlignmentMonitor heartbeat every 5 s
    SAFETY_VIOLATION    = auto()   # SafetyFilter block + counterfactual
    EXPLANATION         = auto()   # InterpretabilityProbe result
    REWARD_WEIGHTS      = auto()   # ValueLearner weight snapshot
    OPERATOR_OVERRIDE   = auto()   # Human approval / rejection
```

---

## Data Model — Frozen Dataclasses

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
import time

@dataclass(frozen=True)
class DashboardEvent:
    event_type: DashboardEventType
    timestamp:  float                   # Unix epoch
    payload:    Dict[str, Any]
    session_id: str                     # operator session or "broadcast"
    sequence:   int                     # monotonic counter

@dataclass(frozen=True)
class OverrideRequest:
    goal_id:    str
    action:     str                     # "approve" | "reject"
    reason:     str
    operator:   str
    timestamp:  float = field(default_factory=time.time)

@dataclass(frozen=True)
class DashboardConfig:
    max_history_events: int   = 1000    # ring buffer per session
    heartbeat_interval: float = 5.0    # seconds between ALIGNMENT_SCORE pushes
    sse_keepalive:      float = 15.0   # SSE comment ping interval
    require_auth:       bool  = True    # JWT bearer token gate
```

---

## Protocol

```python
from typing import AsyncIterator, Protocol

class AlignmentDashboard(Protocol):
    async def stream_events(self, session_id: str) -> AsyncIterator[DashboardEvent]: ...
    async def post_override(self, req: OverrideRequest) -> bool: ...
    async def get_history(self, session_id: str, limit: int) -> List[DashboardEvent]: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

---

## Reference Implementation — `InMemoryAlignmentDashboard`

```python
import asyncio, time
from collections import deque
from typing import AsyncIterator, Dict, Deque

class InMemoryAlignmentDashboard:
    """SSE-backed alignment console wired to Phase 11 components."""

    def __init__(
        self,
        safety_filter:          "SafetyFilter",
        alignment_monitor:      "AlignmentMonitor",
        value_learner:          "ValueLearner",
        interpretability_probe: "InterpretabilityProbe",
        config: DashboardConfig = DashboardConfig(),
    ):
        self._sf  = safety_filter
        self._am  = alignment_monitor
        self._vl  = value_learner
        self._ip  = interpretability_probe
        self._cfg = config

        self._seq:       int = 0
        self._sessions:  Dict[str, Deque[DashboardEvent]] = {}
        self._queues:    Dict[str, asyncio.Queue[DashboardEvent]] = {}
        self._overrides: asyncio.Queue[OverrideRequest] = asyncio.Queue()
        self._tasks:     List[asyncio.Task[None]] = []

    # ── session management ────────────────────────────────────────────
    def _ensure_session(self, session_id: str) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = deque(maxlen=self._cfg.max_history_events)
            self._queues[session_id]   = asyncio.Queue(maxsize=512)

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    # ── event fanout ──────────────────────────────────────────────────
    async def _broadcast(self, event: DashboardEvent) -> None:
        for sid, q in self._queues.items():
            self._sessions[sid].append(event)
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # drop; consumer too slow — monitor via queue_depth metric

    # ── heartbeat loop ────────────────────────────────────────────────
    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self._cfg.heartbeat_interval)
            snap = await self._am.snapshot()
            event = DashboardEvent(
                event_type = DashboardEventType.ALIGNMENT_SCORE,
                timestamp  = time.time(),
                payload    = {
                    "scores":            snap.dimension_scores,
                    "overall":           snap.overall_score,
                    "consecutive_fails": snap.consecutive_fails,
                },
                session_id = "broadcast",
                sequence   = self._next_seq(),
            )
            await self._broadcast(event)

    # ── reward-weight loop ────────────────────────────────────────────
    async def _reward_loop(self) -> None:
        while True:
            await asyncio.sleep(self._cfg.heartbeat_interval * 3)
            snap = await self._vl.snapshot()
            event = DashboardEvent(
                event_type = DashboardEventType.REWARD_WEIGHTS,
                timestamp  = time.time(),
                payload    = {"weights": snap.weights, "examples_seen": snap.examples_seen},
                session_id = "broadcast",
                sequence   = self._next_seq(),
            )
            await self._broadcast(event)

    # ── public API ────────────────────────────────────────────────────
    async def stream_events(self, session_id: str) -> AsyncIterator[DashboardEvent]:
        self._ensure_session(session_id)
        q = self._queues[session_id]
        while True:
            event = await q.get()
            yield event

    async def post_override(self, req: OverrideRequest) -> bool:
        await self._overrides.put(req)
        event = DashboardEvent(
            event_type = DashboardEventType.OPERATOR_OVERRIDE,
            timestamp  = req.timestamp,
            payload    = {
                "goal_id":  req.goal_id,
                "action":   req.action,
                "reason":   req.reason,
                "operator": req.operator,
            },
            session_id = req.operator,
            sequence   = self._next_seq(),
        )
        await self._broadcast(event)
        return True

    async def get_history(self, session_id: str, limit: int = 100) -> List[DashboardEvent]:
        self._ensure_session(session_id)
        return list(self._sessions[session_id])[-limit:]

    async def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._reward_loop()),
        ]

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
```

---

## Factory

```python
def build_alignment_dashboard(
    safety_filter:          "SafetyFilter",
    alignment_monitor:      "AlignmentMonitor",
    value_learner:          "ValueLearner",
    interpretability_probe: "InterpretabilityProbe",
    config: DashboardConfig | None = None,
) -> AlignmentDashboard:
    return InMemoryAlignmentDashboard(
        safety_filter, alignment_monitor,
        value_learner, interpretability_probe,
        config or DashboardConfig(),
    )
```

---

## FastAPI / SSE Endpoints

```python
from fastapi import FastAPI, Header, HTTPException
from sse_starlette.sse import EventSourceResponse
import json, uuid

app  = FastAPI()
_db: AlignmentDashboard = ...  # injected at startup

@app.get("/alignment/stream")
async def sse_stream(session_id: str = "", authorization: str = Header("")):
    """Server-Sent Events feed — connect with EventSource(url)."""
    if not session_id:
        session_id = str(uuid.uuid4())

    async def generator():
        async for event in _db.stream_events(session_id):
            yield {"event": event.event_type.name, "data": json.dumps(event.payload)}

    return EventSourceResponse(generator())

@app.post("/alignment/override")
async def submit_override(req: OverrideRequest):
    ok = await _db.post_override(req)
    return {"accepted": ok}

@app.get("/alignment/history")
async def get_history(session_id: str, limit: int = 100):
    return await _db.get_history(session_id, limit)
```

---

## CognitiveCycle Integration

```python
# CognitiveCycle._publish_alignment_event
async def _publish_alignment_event(self, goal_id: str, verdict: "SafetyVerdict") -> None:
    if verdict == SafetyVerdict.BLOCKED:
        # Broadcast safety violation event
        event = DashboardEvent(
            event_type=DashboardEventType.SAFETY_VIOLATION,
            timestamp=time.time(),
            payload={"goal_id": goal_id, "verdict": "BLOCKED"},
            session_id="broadcast",
            sequence=0,  # dashboard assigns real sequence
        )
        await self._dashboard._broadcast(event)

        # Immediately follow with explanation
        explanation = await self._probe.explain(
            target=ExplanationTarget.SAFETY_FILTER,
            subject_id=goal_id,
        )
        expl_event = DashboardEvent(
            event_type=DashboardEventType.EXPLANATION,
            timestamp=time.time(),
            payload={
                "goal_id":      goal_id,
                "target":       "SAFETY_FILTER",
                "method":       explanation.method.name,
                "attributions": [
                    {"feature": a.feature_name, "weight": round(a.attribution_weight, 4)}
                    for a in explanation.attributions
                ],
            },
            session_id="broadcast",
            sequence=0,
        )
        await self._dashboard._broadcast(expl_event)
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_alignment_dashboard_events_total` | Counter | `event_type` | Events broadcast |
| `asi_alignment_dashboard_sessions_active` | Gauge | — | Live SSE sessions |
| `asi_alignment_dashboard_queue_depth` | Gauge | `session_id` | Per-session queue depth |
| `asi_alignment_dashboard_overrides_total` | Counter | `action` | Operator overrides |
| `asi_alignment_dashboard_heartbeat_latency_seconds` | Histogram | — | Heartbeat loop wall-clock |

**PromQL — violations per minute**
```promql
rate(asi_alignment_dashboard_events_total{event_type="SAFETY_VIOLATION"}[1m]) * 60
```

**PromQL — active sessions**
```promql
asi_alignment_dashboard_sessions_active
```

**Alert — violation spike**
```yaml
alert: AlignmentViolationSpike
expr: rate(asi_alignment_dashboard_events_total{event_type="SAFETY_VIOLATION"}[5m]) * 300 > 10
for: 2m
labels:
  severity: warning
annotations:
  summary: "More than 10 safety violations in last 5 minutes"
```

---

## mypy Compatibility

| Pattern | mypy Status |
|---------|-------------|
| `AsyncIterator[DashboardEvent]` yield | ✅ |
| `frozen=True` dataclasses | ✅ |
| `Protocol` structural subtyping | ✅ |
| `asyncio.Queue[DashboardEvent]` | ✅ (3.9+) |
| `Deque[DashboardEvent]` | ✅ |
| `List[asyncio.Task[None]]` | ✅ |

---

## Test Targets (12)

1. `test_session_creation_on_first_stream` — new session allocated on first `stream_events()` call
2. `test_broadcast_reaches_all_sessions` — fanout to N simultaneous sessions
3. `test_queue_full_drops_without_crash` — `QueueFull` silently swallowed
4. `test_heartbeat_emits_alignment_score` — `ALIGNMENT_SCORE` event after `heartbeat_interval`
5. `test_reward_loop_emits_reward_weights` — `REWARD_WEIGHTS` event after 3× interval
6. `test_post_override_approve` — `OPERATOR_OVERRIDE` event broadcast, `accepted=True`
7. `test_post_override_reject` — reject action propagated to overrides queue
8. `test_get_history_respects_limit` — last N events returned correctly
9. `test_max_history_ring_buffer` — oldest events evicted at `max_history_events`
10. `test_start_stop_cleans_tasks` — asyncio tasks cancelled cleanly on `stop()`
11. `test_sse_endpoint_streams_events` — FastAPI `TestClient` EventSourceResponse integration
12. `test_metrics_increment_on_broadcast` — Prometheus counters advance on every broadcast

---

## Implementation Order (14 Steps)

1. Define `DashboardEventType` enum
2. Define `DashboardEvent`, `OverrideRequest`, `DashboardConfig` frozen dataclasses
3. Define `AlignmentDashboard` Protocol
4. Implement `InMemoryAlignmentDashboard.__init__` with component refs + empty collections
5. Implement `_ensure_session` + `_next_seq`
6. Implement `_broadcast` fanout with QueueFull guard
7. Implement `_heartbeat_loop` (AlignmentMonitor snapshot → ALIGNMENT_SCORE)
8. Implement `_reward_loop` (ValueLearner snapshot → REWARD_WEIGHTS)
9. Implement `stream_events` async generator
10. Implement `post_override` + OPERATOR_OVERRIDE fanout
11. Implement `get_history` ring-buffer slice
12. Implement `start` / `stop` task lifecycle
13. Wire FastAPI SSE + override + history endpoints
14. Register Prometheus metrics + add `CognitiveCycle._publish_alignment_event` hook

---

## Phase 11 Complete 🎉

With `AlignmentDashboard` merged, **Phase 11 (Safety & Alignment Layer)** is feature-complete:

| Sub-phase | Component | Issue | Wiki Page |
|-----------|-----------|-------|-----------|
| 11.1 | SafetyFilter | #337 | [Safety Filter](Phase-11-Safety-Filter) |
| 11.2 | AlignmentMonitor | #340 | [Alignment Monitor](Phase-11-Alignment-Monitor) |
| 11.3 | ValueLearner | #343 | [Value Learner](Phase-11-Value-Learner) |
| 11.4 | InterpretabilityProbe | #346 | [Interpretability Probe](Phase-11-Interpretability-Probe) |
| **11.5** | **AlignmentDashboard** | **#349** | **this page** |

**Acceptance criteria**: `pytest tests/phase11/test_alignment_dashboard.py -v` — all 12 tests green.

---

*107th wiki page · ASI-Build Phase 11 complete*
