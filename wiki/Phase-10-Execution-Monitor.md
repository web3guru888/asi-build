# Phase 10.4 — ExecutionMonitor

`ExecutionMonitor` is the real-time observability layer for the Phase 10 goal-execution pipeline. It subscribes to `ExecutionEvent` objects emitted by `InMemoryPlanExecutor`, aggregates per-task state transitions into `TaskProgress` records, computes a plan-level **health score**, and detects **stalled sub-tasks**. The `CognitiveCycle` consults `ExecutionMonitor` each cycle to decide whether to invoke the `ReplanningEngine` (Phase 10.5).

**Spec issue**: #330 | **Architecture**: #331 | **Q&A**: #332

---

## EventType Enum

```python
class EventType(str, Enum):
    TASK_STARTED   = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED    = "task_failed"
    TASK_RETRIED   = "task_retried"
    TASK_SKIPPED   = "task_skipped"
    PLAN_COMPLETED = "plan_completed"
```

---

## Frozen Dataclasses

```python
@dataclass(frozen=True)
class ExecutionEvent:
    plan_id:      str
    subtask_id:   str
    event_type:   EventType
    state:        ExecutionState          # Phase 10.3 types.py
    timestamp_ms: float = field(default_factory=lambda: time.time() * 1000)
    attempt:      int   = 0
    error:        str   = ""
    output:       dict  = field(default_factory=dict)

@dataclass(frozen=True)
class TaskProgress:
    subtask_id:    str
    state:         ExecutionState
    started_at_ms: float
    elapsed_ms:    float
    attempts:      int
    last_error:    str

@dataclass(frozen=True)
class MonitorView:
    plan_id:       str
    tasks:         tuple[TaskProgress, ...]
    health_score:  float          # 0.0–1.0
    stalled_ids:   frozenset[str]
    is_complete:   bool
    created_at_ms: float
    updated_at_ms: float

@dataclass(frozen=True)
class MonitorConfig:
    max_plans:               int   = 500
    stall_threshold_ms:      float = 30_000.0
    evict_completed_after_ms: float = 300_000.0   # 5 min TTL

@dataclass(frozen=True)
class MonitorSnapshot:
    active_plans:    int
    completed_plans: int
    total_events:    int
    queue_depth:     int
    timestamp_ms:    float
```

---

## `ExecutionMonitor` Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ExecutionMonitor(Protocol):
    async def ingest(self, event: ExecutionEvent) -> None: ...
    async def view(self, plan_id: str) -> MonitorView | None: ...
    async def active_plan_ids(self) -> list[str]: ...
    async def stalled_plans(self, stall_threshold_ms: float) -> list[MonitorView]: ...
    def snapshot(self) -> MonitorSnapshot: ...
```

---

## `InMemoryExecutionMonitor`

```python
import asyncio, time
from collections import defaultdict

class InMemoryExecutionMonitor:
    def __init__(self, cfg: MonitorConfig) -> None:
        self._cfg   = cfg
        self._lock  = asyncio.Lock()
        self._plans: dict[str, dict[str, TaskProgress]] = defaultdict(dict)
        self._plan_meta: dict[str, _PlanMeta] = {}
        self._queue: asyncio.Queue[ExecutionEvent] = asyncio.Queue()
        self._consumer_task: asyncio.Task | None = None
        self._total_events: int = 0

    async def start(self) -> None:
        self._consumer_task = asyncio.create_task(self._consume())

    async def stop(self) -> None:
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

    async def ingest(self, event: ExecutionEvent) -> None:
        await self._queue.put(event)
        _EVENTS_TOTAL.labels(event_type=event.event_type.value).inc()

    async def _consume(self) -> None:
        evict_counter = 0
        while True:
            event = await self._queue.get()
            t0 = time.perf_counter()
            await self._apply(event)
            _VIEW_LATENCY.observe(time.perf_counter() - t0)
            evict_counter += 1
            if evict_counter % 50 == 0:
                await self._evict_completed()

    async def _apply(self, event: ExecutionEvent) -> None:
        async with self._lock:
            self._total_events += 1
            prev = self._plans[event.plan_id].get(event.subtask_id)
            started = prev.started_at_ms if prev else event.timestamp_ms
            elapsed = event.timestamp_ms - started
            self._plans[event.plan_id][event.subtask_id] = TaskProgress(
                subtask_id=event.subtask_id,
                state=event.state,
                started_at_ms=started,
                elapsed_ms=elapsed,
                attempts=event.attempt,
                last_error=event.error,
            )
            if event.event_type == EventType.PLAN_COMPLETED:
                meta = self._plan_meta.get(event.plan_id)
                created = meta.created_at_ms if meta else event.timestamp_ms
                self._plan_meta[event.plan_id] = _PlanMeta(
                    created_at_ms=created,
                    completed_at_ms=event.timestamp_ms,
                    is_complete=True,
                )
            elif event.plan_id not in self._plan_meta:
                self._plan_meta[event.plan_id] = _PlanMeta(
                    created_at_ms=event.timestamp_ms,
                    completed_at_ms=0.0,
                    is_complete=False,
                )
            _PLANS_TRACKED.set(len(self._plans))

    def _build_view(
        self,
        plan_id: str,
        tasks: dict[str, TaskProgress],
        stalled_ids: frozenset[str],
    ) -> MonitorView:
        now_ms = time.time() * 1000
        task_list = tuple(tasks.values())
        success = sum(1 for t in task_list if t.state == ExecutionState.SUCCESS)
        counted = sum(
            1 for t in task_list
            if t.state in (
                ExecutionState.SUCCESS,
                ExecutionState.FAILED,
                ExecutionState.SKIPPED,
                ExecutionState.RUNNING,
            )
        )
        health = success / max(1, counted)
        _HEALTH_SCORE.labels(plan_id=plan_id).set(health)
        meta = self._plan_meta.get(plan_id)
        created = meta.created_at_ms if meta else now_ms
        return MonitorView(
            plan_id=plan_id,
            tasks=task_list,
            health_score=health,
            stalled_ids=stalled_ids,
            is_complete=meta.is_complete if meta else False,
            created_at_ms=created,
            updated_at_ms=now_ms,
        )

    async def view(self, plan_id: str) -> MonitorView | None:
        async with self._lock:
            tasks = self._plans.get(plan_id)
            if tasks is None:
                return None
            return self._build_view(plan_id, tasks, frozenset())

    async def active_plan_ids(self) -> list[str]:
        async with self._lock:
            return [
                pid for pid, meta in self._plan_meta.items()
                if not meta.is_complete
            ]

    async def stalled_plans(self, stall_threshold_ms: float) -> list[MonitorView]:
        now_ms = time.time() * 1000
        stalled_views: list[MonitorView] = []
        async with self._lock:
            for plan_id, tasks in self._plans.items():
                stalled_ids = frozenset(
                    t.subtask_id for t in tasks.values()
                    if t.state == ExecutionState.RUNNING
                    and (now_ms - t.started_at_ms) > stall_threshold_ms
                )
                if stalled_ids:
                    _STALLS_TOTAL.inc(len(stalled_ids))
                    stalled_views.append(self._build_view(plan_id, tasks, stalled_ids))
        return stalled_views

    def snapshot(self) -> MonitorSnapshot:
        completed = sum(1 for m in self._plan_meta.values() if m.is_complete)
        return MonitorSnapshot(
            active_plans=len(self._plans) - completed,
            completed_plans=completed,
            total_events=self._total_events,
            queue_depth=self._queue.qsize(),
            timestamp_ms=time.time() * 1000,
        )

    async def _evict_completed(self) -> None:
        now_ms = time.time() * 1000
        async with self._lock:
            to_evict = [
                pid for pid, meta in self._plan_meta.items()
                if meta.is_complete
                and (now_ms - meta.completed_at_ms) > self._cfg.evict_completed_after_ms
            ]
            for pid in to_evict:
                self._plans.pop(pid, None)
                del self._plan_meta[pid]
            _PLANS_TRACKED.set(len(self._plans))
```

---

## `build_execution_monitor()` Factory

```python
import os

def build_execution_monitor(cfg: MonitorConfig | None = None) -> InMemoryExecutionMonitor:
    if cfg is None:
        cfg = MonitorConfig(
            max_plans=int(os.getenv("ASI_EXECMON_MAX_PLANS", "500")),
            stall_threshold_ms=float(os.getenv("ASI_EXECMON_STALL_MS", "30000")),
            evict_completed_after_ms=float(os.getenv("ASI_EXECMON_EVICT_MS", "300000")),
        )
    return InMemoryExecutionMonitor(cfg)
```

---

## CognitiveCycle Integration

```python
class CognitiveCycle:
    def __init__(
        self,
        ...,
        monitor: ExecutionMonitor,
        replanner: ReplanningEngine,        # Phase 10.5
        monitor_cfg: MonitorConfig,
    ) -> None: ...

    async def _check_plan_health(self) -> None:
        stalled = await self._monitor.stalled_plans(
            self._monitor_cfg.stall_threshold_ms
        )
        for view in stalled:
            if view.health_score < 0.5:
                await self._replanner.trigger(
                    view.plan_id,
                    reason="stall+low_health",
                    context=view,
                )
```

---

## Health Score Formula

```
health = SUCCESS / max(1, SUCCESS + FAILED + SKIPPED + RUNNING)
```

`PENDING` tasks are excluded. `RUNNING` tasks count against health (uncertain outcome).

### Example: 5-task plan

| State | Count | Contribution |
|-------|-------|-------------|
| SUCCESS | 3 | numerator: 3 |
| RUNNING | 1 | denominator only |
| FAILED  | 1 | denominator only |
| **health** | | **3/5 = 0.60** |

---

## 5 Prometheus Metrics

```python
from prometheus_client import Counter, Gauge, Histogram

_EVENTS_TOTAL  = Counter("execmon_events_total", "Events ingested", ["event_type"])
_PLANS_TRACKED = Gauge("execmon_plans_tracked", "Plans currently in monitor")
_STALLS_TOTAL  = Counter("execmon_stalls_detected_total", "Stalled sub-tasks detected")
_HEALTH_SCORE  = Gauge("execmon_health_score", "Latest plan health", ["plan_id"])
_VIEW_LATENCY  = Histogram("execmon_view_latency_seconds", "Time to apply one event")
```

### PromQL Examples

```promql
# Stall rate (stalls/min)
rate(execmon_stalls_detected_total[5m]) * 60

# Degraded plans
count(execmon_health_score < 0.5)

# Event throughput by type
sum(rate(execmon_events_total[1m])) by (event_type)

# View latency p99
histogram_quantile(0.99, rate(execmon_view_latency_seconds_bucket[5m]))
```

---

## mypy Table

| Symbol | Type annotation |
|--------|----------------|
| `InMemoryExecutionMonitor._plans` | `dict[str, dict[str, TaskProgress]]` |
| `InMemoryExecutionMonitor._plan_meta` | `dict[str, _PlanMeta]` |
| `InMemoryExecutionMonitor._queue` | `asyncio.Queue[ExecutionEvent]` |
| `ExecutionMonitor.view` | `async def view(self, plan_id: str) -> MonitorView \| None` |
| `ExecutionMonitor.stalled_plans` | `async def stalled_plans(self, stall_threshold_ms: float) -> list[MonitorView]` |

---

## 12 Test Targets

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_ingest_task_started_creates_progress` | state=RUNNING after TASK_STARTED |
| 2 | `test_ingest_task_completed_updates_state` | state=SUCCESS after TASK_COMPLETED |
| 3 | `test_ingest_task_failed_updates_state` | state=FAILED after TASK_FAILED |
| 4 | `test_health_score_all_success` | 4×SUCCESS → health=1.0 |
| 5 | `test_health_score_mixed` | 2×SUCCESS + 2×FAILED → health=0.5 |
| 6 | `test_health_score_running_counts_against` | 1×RUNNING + 1×SUCCESS → health=0.5 |
| 7 | `test_stalled_plans_detects_long_running` | RUNNING > stall_ms → in stalled_plans() |
| 8 | `test_stalled_plans_ignores_recent_running` | RUNNING < stall_ms → not stalled |
| 9 | `test_plan_complete_event_marks_done` | PLAN_COMPLETED → is_complete=True |
| 10 | `test_view_returns_none_unknown_plan` | view("unknown") → None |
| 11 | `test_snapshot_reflects_queue_depth` | queue > 0 → queue_depth > 0 |
| 12 | `test_metrics_incremented` | all 5 metrics updated after event sequence |

---

## 14-Step Implementation Order

1. Add `EventType` enum to `src/asi_build/cognition/goal_management/types.py`
2. Add `ExecutionEvent` frozen dataclass
3. Add `TaskProgress` frozen dataclass
4. Add `MonitorView` frozen dataclass
5. Add `MonitorConfig` + `MonitorSnapshot` frozen dataclasses
6. Add `_PlanMeta` internal dataclass (mutable)
7. Define `ExecutionMonitor` Protocol in `protocols.py`
8. Initialize 5 Prometheus metrics in `metrics.py`
9. Implement `InMemoryExecutionMonitor.__init__()` + `start()` / `stop()`
10. Implement `_apply()` — state machine transitions
11. Implement `_build_view()` — health score + stall IDs
12. Implement `view()`, `active_plan_ids()`, `stalled_plans()`, `snapshot()`, `_evict_completed()`
13. Implement `build_execution_monitor()` factory with env-var config
14. Wire into `CognitiveCycle`: `_check_plan_health()` calling `stalled_plans()`

---

## Phase 10 Roadmap

| Sub-phase | Issue | Status |
|-----------|-------|--------|
| 10.1 GoalRegistry | #319 | ✅ Spec complete |
| 10.2 GoalDecomposer | #323 | 🟡 In progress |
| 10.3 PlanExecutor | #326 | 🟡 In progress |
| 10.4 ExecutionMonitor | #330 | 🟡 In progress |
| 10.5 ReplanningEngine | — | 📋 Planned |
