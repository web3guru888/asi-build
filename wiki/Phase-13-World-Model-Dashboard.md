# Phase 13.5 — `WorldModelDashboard` 📊

**Phase**: 13 — World Modeling & Curiosity-Driven Exploration  
**Sub-phase**: 13.5 (final)  
**Issue**: [#380](https://github.com/web3guru888/asi-build/issues/380)  
**Discussions**: [#381 Show & Tell](https://github.com/web3guru888/asi-build/discussions/381) · [#382 Q&A](https://github.com/web3guru888/asi-build/discussions/382)  
**Depends on**: 13.4 [SurpriseDetector](Phase-13-Surprise-Detector) · 13.3 [CuriosityModule](Phase-13-Curiosity-Module) · 13.2 [DreamPlanner](Phase-13-Dream-Planner) · 13.1 [WorldModel](Phase-13-World-Model)  
**Status**: 🟡 In progress  

---

## Overview

Phase 13.5 closes the Phase 13 cycle with a **unified observability layer** that surfaces live metrics from all four world-modeling components — `WorldModel`, `DreamPlanner`, `CuriosityModule`, and `SurpriseDetector` — in a single `DashboardSnapshot`. It provides:

- A `WorldModelDashboard` Protocol with `snapshot()`, `stream()`, and `export_jsonld()` methods
- An `InMemoryWorldModelDashboard` that fan-outs with `asyncio.gather()` for low overhead
- A FastAPI route at `/api/v1/world-model/dashboard` returning structured JSON
- JSON-LD serialisation for log-aggregator shipping (Loki, Elasticsearch)
- 5 Prometheus metrics + composite Grafana dashboard JSON (`grafana/phase13-dashboard.json`)
- `CognitiveCycle._model_based_step()` integration (optional, zero-overhead when disabled)

---

## Component Map

```
CognitiveCycle._model_based_step()
│
└── WorldModelDashboard.snapshot()          ← Phase 13.5 (THIS MODULE)
        │   (asyncio.gather fan-out)
        ├── WorldModel.stats()              ← Phase 13.1
        ├── DreamPlanner.stats()            ← Phase 13.2
        ├── CuriosityModule.stats()         ← Phase 13.3
        └── SurpriseDetector.stats()        ← Phase 13.4
                │
                └── DashboardSnapshot (frozen dataclass)
                        ├── WorldModelSnapshot
                        ├── DreamPlannerSnapshot
                        ├── CuriositySnapshot
                        └── SurpriseSnapshot
```

---

## Snapshot Dataclass Hierarchy

```python
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class WorldModelSnapshot:
    total_updates: int
    total_predictions: int
    total_rollouts: int
    mean_surprise: float
    rollout_horizon_mean: float
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class DreamPlannerSnapshot:
    total_plans: int
    completed_plans: int
    aborted_plans: int
    mean_plan_latency_ms: float
    mean_candidates: float
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class CuriositySnapshot:
    total_events: int
    mean_bonus: float
    peak_bonus: float
    decay_alpha: float
    current_step: int
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SurpriseSnapshot:
    total_detections: int
    critical_detections: int
    suppressed_detections: int
    mean_score: float
    current_severity: str          # SeverityLevel.name
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class DashboardSnapshot:
    world_model: WorldModelSnapshot
    dream_planner: DreamPlannerSnapshot
    curiosity: CuriositySnapshot
    surprise: SurpriseSnapshot
    cycle_id: int
    agent_id: str
    timestamp: float = field(default_factory=time.time)
```

---

## Protocol

```python
@runtime_checkable
class WorldModelDashboard(Protocol):
    """Read-only aggregation view over Phase 13 components."""

    async def snapshot(self) -> DashboardSnapshot:
        """Point-in-time snapshot of all Phase 13 metrics."""
        ...

    async def stream(self, interval_s: float = 1.0):
        """Async generator yielding snapshots every *interval_s* seconds."""
        ...

    async def export_jsonld(self, snapshot: DashboardSnapshot) -> str:
        """Serialise *snapshot* as a JSON-LD document."""
        ...
```

---

## `InMemoryWorldModelDashboard`

```python
import asyncio, json, time
from prometheus_client import Counter, Histogram, Gauge

_SNAPSHOT_TOTAL = Counter(
    "asi_wm_dashboard_snapshots_total", "...", ["agent_id"])
_SNAPSHOT_LATENCY = Histogram(
    "asi_wm_dashboard_snapshot_latency_seconds", "...", ["agent_id"])
_CYCLE_ID = Gauge(
    "asi_wm_dashboard_cycle_id", "...", ["agent_id"])
_CRITICAL_RATIO = Gauge(
    "asi_wm_dashboard_critical_ratio", "...", ["agent_id"])
_STREAM_SUBS = Gauge(
    "asi_wm_dashboard_stream_subscribers", "...", ["agent_id"])


class InMemoryWorldModelDashboard:
    _CONTEXT = "https://asi-build.example/ns/v1"

    def __init__(self, world_model, dream_planner, curiosity, surprise,
                 agent_id: str = "default") -> None:
        self._wm = world_model
        self._dp = dream_planner
        self._cu = curiosity
        self._sd = surprise
        self._agent_id = agent_id
        self._cycle: int = 0

    async def snapshot(self) -> DashboardSnapshot:
        t0 = time.perf_counter()
        wm_s, dp_s, cu_s, sd_s = await asyncio.gather(
            self._wm.stats(),
            self._dp.stats(),
            self._cu.stats(),
            self._sd.stats(),
        )
        latency = time.perf_counter() - t0
        _SNAPSHOT_LATENCY.labels(agent_id=self._agent_id).observe(latency)
        _SNAPSHOT_TOTAL.labels(agent_id=self._agent_id).inc()
        self._cycle += 1
        _CYCLE_ID.labels(agent_id=self._agent_id).set(self._cycle)
        ratio = sd_s.critical_detections / max(sd_s.total_detections, 1)
        _CRITICAL_RATIO.labels(agent_id=self._agent_id).set(ratio)
        return DashboardSnapshot(
            world_model=WorldModelSnapshot(
                total_updates=wm_s.total_updates,
                total_predictions=wm_s.total_predictions,
                total_rollouts=wm_s.total_rollouts,
                mean_surprise=wm_s.mean_surprise,
                rollout_horizon_mean=wm_s.rollout_horizon_mean,
            ),
            dream_planner=DreamPlannerSnapshot(
                total_plans=dp_s.total_plans,
                completed_plans=dp_s.completed_plans,
                aborted_plans=dp_s.aborted_plans,
                mean_plan_latency_ms=dp_s.mean_plan_latency_ms,
                mean_candidates=dp_s.mean_candidates,
            ),
            curiosity=CuriositySnapshot(
                total_events=cu_s.total_events,
                mean_bonus=cu_s.mean_bonus,
                peak_bonus=cu_s.peak_bonus,
                decay_alpha=cu_s.decay_alpha,
                current_step=cu_s.current_step,
            ),
            surprise=SurpriseSnapshot(
                total_detections=sd_s.total_detections,
                critical_detections=sd_s.critical_detections,
                suppressed_detections=sd_s.suppressed_detections,
                mean_score=sd_s.mean_score,
                current_severity=sd_s.current_severity.name,
            ),
            cycle_id=self._cycle,
            agent_id=self._agent_id,
        )

    async def stream(self, interval_s: float = 1.0):
        _STREAM_SUBS.labels(agent_id=self._agent_id).inc()
        try:
            while True:
                yield await self.snapshot()
                await asyncio.sleep(interval_s)
        finally:
            _STREAM_SUBS.labels(agent_id=self._agent_id).dec()

    async def export_jsonld(self, snapshot: DashboardSnapshot) -> str:
        doc = {
            "@context": self._CONTEXT,
            "@type": "DashboardSnapshot",
            "cycleId": snapshot.cycle_id,
            "agentId": snapshot.agent_id,
            "timestamp": snapshot.timestamp,
            "worldModel": {"@type": "WorldModelSnapshot",
                           **snapshot.world_model.__dict__},
            "dreamPlanner": {"@type": "DreamPlannerSnapshot",
                             **snapshot.dream_planner.__dict__},
            "curiosity": {"@type": "CuriositySnapshot",
                          **snapshot.curiosity.__dict__},
            "surprise": {"@type": "SurpriseSnapshot",
                         **snapshot.surprise.__dict__},
        }
        return json.dumps(doc, indent=2)


def make_world_model_dashboard(
    world_model, dream_planner, curiosity, surprise,
    agent_id: str = "default",
) -> WorldModelDashboard:
    return InMemoryWorldModelDashboard(
        world_model, dream_planner, curiosity, surprise, agent_id)
```

---

## FastAPI Route

```python
# asi_build/api/routes/world_model_dashboard.py
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from asi_build.phase13.dashboard import WorldModelDashboard, DashboardSnapshot

router = APIRouter(prefix="/api/v1/world-model", tags=["phase13"])

@router.get("/dashboard", response_model=DashboardSnapshot)
async def get_dashboard(
    dashboard: WorldModelDashboard = Depends(get_dashboard_dep),
) -> DashboardSnapshot:
    return await dashboard.snapshot()

@router.get("/dashboard/jsonld", response_class=PlainTextResponse)
async def get_dashboard_jsonld(
    dashboard: WorldModelDashboard = Depends(get_dashboard_dep),
) -> str:
    snap = await dashboard.snapshot()
    return await dashboard.export_jsonld(snap)
```

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/api/v1/world-model/dashboard` | `DashboardSnapshot` (JSON) |
| `GET` | `/api/v1/world-model/dashboard/jsonld` | JSON-LD (text/plain) |

---

## `CognitiveCycle._model_based_step()` Integration

```python
# In CognitiveCycle.__init__():
def __init__(self, ..., dashboard: WorldModelDashboard | None = None):
    ...
    self._dashboard = dashboard

# In CognitiveCycle._model_based_step():
async def _model_based_step(self, obs: Observation) -> Action:
    # ... world model update, curiosity, surprise, planning ...

    if self._dashboard is not None:
        snap = await self._dashboard.snapshot()
        log.info("phase13.dashboard", extra={"snapshot": snap})
        # optionally ship as JSON-LD:
        # doc = await self._dashboard.export_jsonld(snap)
        # log.info("phase13.dashboard.jsonld", extra={"doc": doc})

    return action
```

Pass `dashboard=None` (default) for zero-overhead in tests or benchmarks.

---

## JSON-LD Example

```json
{
  "@context": "https://asi-build.example/ns/v1",
  "@type": "DashboardSnapshot",
  "cycleId": 42,
  "agentId": "default",
  "timestamp": 1744512345.678,
  "worldModel": {
    "@type": "WorldModelSnapshot",
    "total_updates": 1200,
    "total_predictions": 4800,
    "total_rollouts": 960,
    "mean_surprise": 0.032,
    "rollout_horizon_mean": 7.4
  },
  "dreamPlanner": {
    "@type": "DreamPlannerSnapshot",
    "total_plans": 480,
    "completed_plans": 440,
    "aborted_plans": 40,
    "mean_plan_latency_ms": 12.3,
    "mean_candidates": 8.2
  },
  "curiosity": {
    "@type": "CuriositySnapshot",
    "total_events": 960,
    "mean_bonus": 0.0214,
    "peak_bonus": 0.183,
    "decay_alpha": 0.9942,
    "current_step": 960
  },
  "surprise": {
    "@type": "SurpriseSnapshot",
    "total_detections": 38,
    "critical_detections": 3,
    "suppressed_detections": 7,
    "mean_score": 0.071,
    "current_severity": "LOW"
  }
}
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_wm_dashboard_snapshots_total` | Counter | `agent_id` | Total `snapshot()` calls |
| `asi_wm_dashboard_snapshot_latency_seconds` | Histogram | `agent_id` | End-to-end gather latency |
| `asi_wm_dashboard_cycle_id` | Gauge | `agent_id` | Current dashboard cycle counter |
| `asi_wm_dashboard_critical_ratio` | Gauge | `agent_id` | `critical_detections / max(total_detections, 1)` |
| `asi_wm_dashboard_stream_subscribers` | Gauge | `agent_id` | Active `stream()` consumers |

### PromQL Examples

```promql
# Snapshot throughput
rate(asi_wm_dashboard_snapshots_total[1m])

# P95 gather latency
histogram_quantile(0.95,
  rate(asi_wm_dashboard_snapshot_latency_seconds_bucket[5m]))

# Critical surprise ratio (alert > 0.10)
asi_wm_dashboard_critical_ratio{agent_id="default"}

# Active stream consumers
asi_wm_dashboard_stream_subscribers
```

### Grafana Alert YAML

```yaml
# grafana/alerts/phase13-dashboard.yaml
apiVersion: 1
groups:
  - name: Phase13Dashboard
    interval: 30s
    rules:
      - uid: p13_dash_latency
        title: "Phase 13 Dashboard — snapshot p95 > 200 ms"
        condition: C
        data:
          - refId: A
            expr: histogram_quantile(0.95, rate(asi_wm_dashboard_snapshot_latency_seconds_bucket[5m]))
          - refId: C
            type: threshold
            conditions:
              - evaluator: { type: gt, params: [0.2] }
        for: 5m
      - uid: p13_dash_critical_ratio
        title: "Phase 13 Dashboard — critical surprise ratio > 10%"
        condition: C
        data:
          - refId: A
            expr: asi_wm_dashboard_critical_ratio{agent_id="default"}
          - refId: C
            type: threshold
            conditions:
              - evaluator: { type: gt, params: [0.10] }
        for: 2m
        annotations:
          summary: "Check SurpriseDetector config or WorldModel training"
```

---

## mypy Compliance Table

| Symbol | Signature | Notes |
|--------|-----------|-------|
| `WorldModelSnapshot` | `@dataclass(frozen=True)` | All fields typed |
| `DreamPlannerSnapshot` | `@dataclass(frozen=True)` | All fields typed |
| `CuriositySnapshot` | `@dataclass(frozen=True)` | All fields typed |
| `SurpriseSnapshot` | `@dataclass(frozen=True)` | `current_severity: str` |
| `DashboardSnapshot` | `@dataclass(frozen=True)` | Nested snapshots |
| `WorldModelDashboard` | `Protocol` + `@runtime_checkable` | Structural subtyping |
| `InMemoryWorldModelDashboard` | `async def snapshot() -> DashboardSnapshot` | No `Any` |
| `make_world_model_dashboard` | `-> WorldModelDashboard` | Factory typed |

---

## Test Targets (12)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_snapshot_returns_dashboard_snapshot` | `isinstance(result, DashboardSnapshot)` |
| 2 | `test_snapshot_increments_cycle_id` | Two calls → `cycle_id` increments by 1 |
| 3 | `test_snapshot_aggregates_all_four_components` | All four `.stats()` mocked → fields populated |
| 4 | `test_stream_yields_snapshots_at_interval` | Collect 3 snapshots with `interval_s=0` |
| 5 | `test_stream_cycle_ids_monotone` | Cycle IDs strictly increasing |
| 6 | `test_export_jsonld_valid_json` | `json.loads()` on output succeeds |
| 7 | `test_export_jsonld_context_field` | `@context` == `"https://asi-build.example/ns/v1"` |
| 8 | `test_export_jsonld_nested_types` | `worldModel["@type"]` == `"WorldModelSnapshot"` |
| 9 | `test_fastapi_get_dashboard_200` | `GET /api/v1/world-model/dashboard` → HTTP 200 |
| 10 | `test_fastapi_get_dashboard_jsonld_200` | `/dashboard/jsonld` → `text/plain`, valid JSON |
| 11 | `test_cognitive_cycle_calls_snapshot` | Mock dashboard injected → `snapshot()` called per step |
| 12 | `test_prometheus_metrics_incremented` | After `n` snapshots, counter == `n` |

---

## Implementation Order (14 steps)

1. Create `asi_build/phase13/dashboard.py` with all dataclasses + Protocol
2. Implement `InMemoryWorldModelDashboard.snapshot()` (asyncio.gather fan-out)
3. Implement `InMemoryWorldModelDashboard.stream()` async generator + subscriber gauge
4. Implement `InMemoryWorldModelDashboard.export_jsonld()` JSON-LD serialiser
5. Wire 5-metric Prometheus block (Counter + Histogram + 3 Gauges)
6. Add `make_world_model_dashboard()` factory
7. Create `asi_build/api/routes/world_model_dashboard.py` FastAPI router
8. Register router in `asi_build/api/app.py`
9. Add optional `_dashboard: WorldModelDashboard | None` to `CognitiveCycle`
10. Call `await self._dashboard.snapshot()` inside `_model_based_step()`
11. Add structured JSON-LD log emission via `structlog` or stdlib `logging`
12. Write `tests/phase13/test_dashboard.py` (12 targets)
13. Add composite Grafana dashboard JSON (`grafana/phase13-dashboard.json`)
14. Update `docs/api.md` with `/api/v1/world-model/dashboard` docs

---

## Phase 13 Completion Checklist 🎉

| Sub-phase | Component | Issue | Discussions | Status |
|-----------|-----------|-------|------------|--------|
| 13.1 | `WorldModel` | [#368](https://github.com/web3guru888/asi-build/issues/368) | [#369](https://github.com/web3guru888/asi-build/discussions/369) [#370](https://github.com/web3guru888/asi-build/discussions/370) | 🟡 In progress |
| 13.2 | `DreamPlanner` | [#371](https://github.com/web3guru888/asi-build/issues/371) | [#372](https://github.com/web3guru888/asi-build/discussions/372) [#373](https://github.com/web3guru888/asi-build/discussions/373) | 🟡 In progress |
| 13.3 | `CuriosityModule` | [#374](https://github.com/web3guru888/asi-build/issues/374) | [#375](https://github.com/web3guru888/asi-build/discussions/375) [#376](https://github.com/web3guru888/asi-build/discussions/376) | 🟡 In progress |
| 13.4 | `SurpriseDetector` | [#377](https://github.com/web3guru888/asi-build/issues/377) | [#378](https://github.com/web3guru888/asi-build/discussions/378) [#379](https://github.com/web3guru888/asi-build/discussions/379) | 🟡 In progress |
| 13.5 | `WorldModelDashboard` | [#380](https://github.com/web3guru888/asi-build/issues/380) | [#381](https://github.com/web3guru888/asi-build/discussions/381) [#382](https://github.com/web3guru888/asi-build/discussions/382) | 🟡 In progress |

**On merge of all five sub-phases: Phase 13 complete → Phase 14 planning begins.**

---

## Phase 13 → Phase 14 Transition Notes

Once Phase 13.5 merges, the full world-modeling stack is operational. Candidate Phase 14 directions (from Discussion [#367](https://github.com/web3guru888/asi-build/discussions/367)):

| Option | Theme |
|--------|-------|
| 14A | **Code Synthesis** — agent writes and tests its own code |
| 14B | **On-Chain Governance** — DAO voting + proposal execution |
| 14C | **Multimodal Perception** — vision + audio input pipelines |
| 14D | **Continual Self-Improvement** — meta-learning over all phases |

---

*117th wiki page · Phase 13 World Modeling & Curiosity-Driven Exploration*
