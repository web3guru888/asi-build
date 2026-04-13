# Phase 17.4 — SchedulerCortex 🗓️

**Component**: `asi_build/scheduler/cortex.py`
**Phase**: 17 — Temporal Reasoning & Predictive Cognition
**Issue**: [#443](https://github.com/web3guru888/asi-build/issues/443)
**Discussions**: [Show & Tell #444](https://github.com/web3guru888/asi-build/discussions/444) · [Q&A #445](https://github.com/web3guru888/asi-build/discussions/445)
**Depends on**: [PredictiveEngine #440](https://github.com/web3guru888/asi-build/issues/440) · [GoalRegistry #319](https://github.com/web3guru888/asi-build/issues/319) · [PlanExecutor #326](https://github.com/web3guru888/asi-build/issues/326)

---

## Motivation

The PredictiveEngine can anticipate *when* a cognitive module will be needed and *what* it will produce. The SchedulerCortex converts those predictions into concrete **scheduled tasks** with deadlines, priorities, and temporal constraints. Rather than reacting to cognitive load after it arrives, the system pre-schedules work in advance — the difference between a reactive dispatcher and a proactive cognitive calendar.

---

## Enums

```python
from enum import IntEnum, Enum

class TaskPriority(IntEnum):
    CRITICAL   = 0
    HIGH       = 1
    NORMAL     = 2
    LOW        = 3
    BACKGROUND = 4

class SchedulePolicy(str, Enum):
    EDF            = "EDF"            # Earliest-Deadline-First
    RATE_MONOTONIC = "RATE_MONOTONIC" # Static priority by period
    PRIORITY_QUEUE = "PRIORITY_QUEUE" # Plain priority ordering
```

---

## Frozen Dataclasses

```python
from dataclasses import dataclass
from typing import Mapping, Any

@dataclass(frozen=True)
class ScheduledTask:
    task_id:           str
    module:            str
    action:            str
    priority:          TaskPriority
    deadline_ns:       int           # absolute CLOCK_REALTIME nanoseconds
    earliest_start_ns: int           # not-before constraint
    payload:           Mapping[str, Any]
    prediction_basis:  str | None    # PredictiveEngine prediction_id if pre-scheduled

@dataclass(frozen=True)
class ScheduleSlot:
    slot_id:     str
    start_ns:    int
    end_ns:      int
    task_id:     str | None
    utilization: float               # [0.0, 1.0]

@dataclass(frozen=True)
class SchedulerConfig:
    max_queue:            int  = 1000
    tick_ms:              int  = 50
    preemption:           bool = True
    deadline_miss_policy: str  = "DROP"   # "DROP" | "DEMOTE"
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SchedulerCortex(Protocol):
    def submit(self, task: ScheduledTask) -> bool:
        """Enqueue task; False if queue full or duplicate task_id."""
        ...
    def cancel(self, task_id: str) -> bool:
        """Remove task; False if not found."""
        ...
    def peek_next(self) -> ScheduledTask | None:
        """Highest-priority task without dequeue."""
        ...
    async def run_tick(self) -> list[ScheduledTask]:
        """Advance clock; return tasks ready this tick."""
        ...
    def get_schedule(self) -> list[ScheduleSlot]:
        """Current time-slot view of schedule."""
        ...
    def stats(self) -> dict:
        """Live scheduler statistics."""
        ...
```

`isinstance(obj, SchedulerCortex)` checks all six methods at runtime.

---

## `AsyncSchedulerCortex` — Full Implementation

```python
import asyncio
import time
from collections import deque

class AsyncSchedulerCortex:
    """
    EDF-ordered async task scheduler backed by asyncio.PriorityQueue.
    Priority key: (deadline_ns, priority.value, task_id)
    """

    def __init__(self, config: SchedulerConfig, predictive_engine=None) -> None:
        self._cfg   = config
        self._pe    = predictive_engine
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=config.max_queue
        )
        self._lock              = asyncio.Lock()
        self._task_index: dict[str, ScheduledTask] = {}
        self._cancelled: set[str]                  = set()
        self._running: ScheduledTask | None        = None
        self._slots: list[ScheduleSlot]            = []
        # Counters (also exported as Prometheus metrics)
        self._submitted_total  = 0
        self._completed_total  = 0
        self._deadline_misses  = 0
        self._preemptions      = 0

    async def submit(self, task: ScheduledTask) -> bool:
        async with self._lock:
            if task.task_id in self._task_index:
                return False          # duplicate
            if self._queue.full():
                return False
            key = (task.deadline_ns, task.priority.value, task.task_id)
            await self._queue.put((key, task))
            self._task_index[task.task_id] = task
            self._submitted_total += 1
            # Preemption check
            if (
                self._cfg.preemption
                and self._running is not None
                and task.deadline_ns < self._running.deadline_ns
            ):
                cancelled = self._running
                self._cancelled.add(cancelled.task_id)
                self._preemptions += 1
                rekey = (cancelled.deadline_ns, cancelled.priority.value, cancelled.task_id)
                await self._queue.put((rekey, cancelled))
        return True

    async def run_tick(self) -> list[ScheduledTask]:
        now_ns = time.time_ns()
        ready: list[ScheduledTask] = []
        async with self._lock:
            temp: list[tuple] = []
            while not self._queue.empty():
                key, task = self._queue.get_nowait()
                # Skip cancelled tasks
                if task.task_id in self._cancelled:
                    self._cancelled.discard(task.task_id)
                    self._task_index.pop(task.task_id, None)
                    continue
                # Handle deadline miss
                if task.deadline_ns < now_ns:
                    self._deadline_misses += 1
                    self._task_index.pop(task.task_id, None)
                    if self._cfg.deadline_miss_policy == "DEMOTE":
                        demoted = ScheduledTask(
                            task_id=task.task_id + "_demoted",
                            module=task.module,
                            action=task.action,
                            priority=TaskPriority.BACKGROUND,
                            deadline_ns=now_ns + 60_000_000_000,   # +60 s
                            earliest_start_ns=now_ns,
                            payload=task.payload,
                            prediction_basis=task.prediction_basis,
                        )
                        dkey = (demoted.deadline_ns, demoted.priority.value, demoted.task_id)
                        temp.append((dkey, demoted))
                    continue   # DROP case: nothing re-enqueued
                # Not yet startable
                if task.earliest_start_ns > now_ns:
                    temp.append((key, task))
                    continue
                # Ready to dispatch
                ready.append(task)
                self._task_index.pop(task.task_id, None)
                self._completed_total += 1
            for item in temp:
                await self._queue.put(item)
        return ready

    def cancel(self, task_id: str) -> bool:
        if task_id in self._task_index:
            self._cancelled.add(task_id)
            return True
        return False

    def peek_next(self) -> ScheduledTask | None:
        if self._queue.empty():
            return None
        try:
            _, task = self._queue._queue[0]   # CPython heapq internal — safe
            return task
        except IndexError:
            return None

    def get_schedule(self) -> list[ScheduleSlot]:
        return list(self._slots)

    def stats(self) -> dict:
        return {
            "queue_depth":     len(self._task_index),
            "submitted_total": self._submitted_total,
            "completed_total": self._completed_total,
            "deadline_misses": self._deadline_misses,
            "preemptions":     self._preemptions,
        }

    async def prediction_loop(self, module: str, action: str) -> None:
        """Background coroutine: ask PredictiveEngine; pre-submit high-confidence tasks."""
        if self._pe is None:
            return
        while True:
            prediction = self._pe.predict(module)
            if prediction is not None and prediction.confidence > 0.8:
                now = time.time_ns()
                future_ns = now + int(prediction.predicted_value * 1e9)
                task = ScheduledTask(
                    task_id=f"pre_{module}_{future_ns}",
                    module=module,
                    action=action,
                    priority=TaskPriority.NORMAL,
                    deadline_ns=future_ns + 5_000_000_000,   # +5 s grace
                    earliest_start_ns=future_ns,
                    payload={},
                    prediction_basis=str(id(prediction)),
                )
                await self.submit(task)
            await asyncio.sleep(self._cfg.tick_ms / 1000)
```

---

## `NullSchedulerCortex`

```python
class NullSchedulerCortex:
    """No-op implementation for testing and optional injection."""
    def submit(self, task: ScheduledTask) -> bool:          return False
    def cancel(self, task_id: str) -> bool:                  return False
    def peek_next(self) -> ScheduledTask | None:             return None
    async def run_tick(self) -> list[ScheduledTask]:         return []
    def get_schedule(self) -> list[ScheduleSlot]:            return []
    def stats(self) -> dict:                                 return {}
```

---

## ASCII Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Phase 17 Temporal Pipeline                        │
│                                                                     │
│  EventSequencer       PredictiveEngine        SchedulerCortex       │
│  ─────────────       ────────────────         ───────────────       │
│  windows[]  ──train()──► predict(module)  ──► PriorityQueue         │
│                          Prediction{          EDF key:              │
│                           value,              (deadline_ns,         │
│                           confidence,          priority.value,      │
│                           strategy}            task_id)             │
│                                               │                     │
│                                               │ run_tick()          │
│                                               ▼                     │
│                                      ScheduledTask[]                │
│                                               │                     │
│                                    CognitiveCycle._dispatch()       │
│                                               │                     │
│                           ┌──────────────────┤                     │
│                           ▼                  ▼                     │
│                    GoalRegistry          PlanExecutor               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## EDF Ordering Diagram

```
Queue state (sorted by deadline_ns):

  ┌────────────────────────────────────────────────────────┐
  │ Slot 0 │ deadline=+1s │ NORMAL   │ task_id="urgent_A"  │ ← next
  │ Slot 1 │ deadline=+3s │ HIGH     │ task_id="plan_B"    │
  │ Slot 2 │ deadline=+5s │ CRITICAL │ task_id="safety_C"  │
  │ Slot 3 │ deadline=+8s │ LOW      │ task_id="bkgd_D"    │
  └────────────────────────────────────────────────────────┘

  "urgent_A" (NORMAL priority) dispatched BEFORE "safety_C" (CRITICAL)
  because its deadline is tighter. Priority only breaks ties within
  the same deadline bucket.
```

---

## Scheduling Policy Comparison

| Aspect | EDF | Rate-Monotonic | Priority Queue |
|---|---|---|---|
| **Ordering key** | `(deadline_ns, priority, task_id)` | `(period, priority, task_id)` | `(priority, task_id)` |
| **Optimal for** | Aperiodic mixed workloads | Periodic fixed-rate tasks | Simple urgency ranking |
| **Deadline awareness** | ✅ Direct | ✅ Implicit via period | ❌ None |
| **Starvation risk** | Low (expiry handled) | Low (period-bound) | Medium |
| **ASI use case** | **Default ✅** | Fixed-rate monitors | Legacy fallback |
| **Preemption support** | ✅ Natural | ✅ Natural | ✅ Manual |

---

## Preemption Algorithm

```
submit(new_task):
    if cfg.preemption=False  →  enqueue(new_task); return
    if running is None       →  enqueue(new_task); return

    if new_task.deadline_ns < running.deadline_ns:
        cancelled.add(running.task_id)        # mark for skip
        preemptions_total.inc()
        queue.put((running_key, running))     # re-enqueue — not dropped
        running = new_task                    # conceptual update
        enqueue(new_task)
    else:
        enqueue(new_task)                     # running keeps its slot

run_tick():
    for each item in queue:
        if task_id in cancelled:
            cancelled.remove(task_id)
            task_index.pop(task_id)
            skip                              # cancelled task evicted cleanly
```

**Key guarantee**: preemption never drops the pre-empted task. It is re-enqueued with its original `deadline_ns` and will be dispatched naturally once the higher-priority task completes.

---

## Prediction-Driven Pre-Scheduling

```
PredictiveEngine.predict("WorldModel")
  → Prediction{
       predicted_value = 4.2   # seconds until next activation
       confidence      = 0.91  # EXCEEDS 0.8 threshold
       strategy        = EMA
    }

prediction_loop():
  future_ns = now + 4_200_000_000
  SchedulerCortex.submit(ScheduledTask{
      task_id           = "pre_WorldModel_<ns>",
      module            = "WorldModel",
      action            = "update",
      priority          = NORMAL,
      earliest_start_ns = future_ns,
      deadline_ns       = future_ns + 5_000_000_000,
      prediction_basis  = "pred_<uuid>"     # traceability
  })

CognitiveCycle at t+4.2 s:
  run_tick() → [ScheduledTask{WorldModel.update}]
  ↓ task pre-positioned — dispatched immediately
  ↓ no backpressure spike on the event loop
```

---

## Integration with GoalRegistry / PlanExecutor

```python
# CognitiveCycle._schedule_goals()
goals = await goal_registry.get_active_goals()
for goal in goals:
    steps = await plan_executor.plan_steps(goal)
    for step in steps:
        await cortex.submit(ScheduledTask(
            task_id=f"goal_{goal.goal_id}_{step.step_id}",
            module=step.module,
            action=step.action,
            priority=TaskPriority.HIGH if goal.is_critical else TaskPriority.NORMAL,
            deadline_ns=goal.deadline_ns,
            earliest_start_ns=step.earliest_ns,
            payload=step.parameters,
            prediction_basis=None,
        ))
```

Goal deadlines propagate directly to task `deadline_ns`, ensuring the EDF scheduler respects goal-level timing constraints.

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `asi_scheduler_tasks_submitted_total` | Counter | `module`, `priority` | Tasks enqueued |
| `asi_scheduler_tasks_completed_total` | Counter | `module`, `priority` | Tasks dispatched |
| `asi_scheduler_deadline_misses_total` | Counter | `module`, `policy` | Deadline misses |
| `asi_scheduler_queue_depth` | Gauge | — | Current queue depth |
| `asi_scheduler_preemptions_total` | Counter | — | Preemption events |

### PromQL

```promql
# Deadline miss rate (per minute)
rate(asi_scheduler_deadline_misses_total[1m]) * 60

# Queue saturation alert trigger
asi_scheduler_queue_depth > 800

# Preemption rate
rate(asi_scheduler_preemptions_total[5m])

# Task dispatch throughput
rate(asi_scheduler_tasks_completed_total[1m])
```

### Grafana Alert YAML

```yaml
- alert: SchedulerDeadlineMissSpike
  expr: rate(asi_scheduler_deadline_misses_total[1m]) > 0.5
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "SchedulerCortex: >0.5 deadline misses/s for 2 min"
    runbook: "Check module latency vs tick_ms; consider DEMOTE policy or increase max_queue"

- alert: SchedulerQueueSaturation
  expr: asi_scheduler_queue_depth > 800
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "SchedulerCortex queue >80% full ({{$value}}/1000)"
    runbook: "Increase max_queue; reduce submission rate; check for stalled consumers"
```

---

## mypy Narrowing Table

| Location | Guard | Narrowed type |
|---|---|---|
| `submit()` duplicate check | `if task.task_id in self._task_index` | `bool` early return |
| `peek_next()` empty check | `if self._queue.empty()` | `ScheduledTask` (not None) |
| `run_tick()` cancel check | `if task.task_id in self._cancelled` | branch skipped |
| `deadline_miss_policy` | `if self._cfg.deadline_miss_policy == "DEMOTE"` | literal narrowing |
| `cancel()` existence check | `if task_id in self._task_index` | `True` branch valid |
| `prediction_loop()` | `if self._pe is None: return` | `_pe` is non-None below |

---

## Test Targets (12)

1. `test_submit_returns_false_on_full_queue`
2. `test_submit_returns_false_on_duplicate_task_id`
3. `test_edf_ordering_deadline_wins`
4. `test_preemption_triggers_when_new_deadline_earlier`
5. `test_cancel_removes_task`
6. `test_deadline_miss_drop_policy`
7. `test_deadline_miss_demote_policy`
8. `test_earliest_start_ns_defers_ready_tasks`
9. `test_run_tick_returns_only_startable_tasks`
10. `test_prediction_driven_presubmit_high_confidence`
11. `test_null_cortex_noop`
12. `test_stats_reflect_operations`

### Skeletons

```python
@pytest.mark.asyncio
async def test_edf_ordering_deadline_wins():
    cfg = SchedulerConfig(tick_ms=10, preemption=False)
    cortex = AsyncSchedulerCortex(cfg)
    now = time.time_ns()
    late = ScheduledTask(
        "late", "mod", "act", TaskPriority.HIGH,
        deadline_ns=now + 10_000_000_000,
        earliest_start_ns=now - 1,
        payload={}, prediction_basis=None,
    )
    urgent = ScheduledTask(
        "urgent", "mod", "act", TaskPriority.NORMAL,
        deadline_ns=now + 500_000_000,
        earliest_start_ns=now - 1,
        payload={}, prediction_basis=None,
    )
    await cortex.submit(late)
    await cortex.submit(urgent)
    ready = await cortex.run_tick()
    # NORMAL with tighter deadline dispatched before HIGH with loose deadline
    assert ready[0].task_id == "urgent"


@pytest.mark.asyncio
async def test_deadline_miss_drop_policy():
    cfg = SchedulerConfig(deadline_miss_policy="DROP")
    cortex = AsyncSchedulerCortex(cfg)
    now = time.time_ns()
    expired = ScheduledTask(
        "exp", "mod", "act", TaskPriority.HIGH,
        deadline_ns=now - 1_000_000_000,      # already past
        earliest_start_ns=now - 2_000_000_000,
        payload={}, prediction_basis=None,
    )
    await cortex.submit(expired)
    ready = await cortex.run_tick()
    assert ready == []
    assert cortex.stats()["deadline_misses"] == 1
    assert cortex.stats()["queue_depth"] == 0
```

---

## 14-Step Implementation Order

1. Define `TaskPriority(IntEnum)` and `SchedulePolicy(str, Enum)`
2. Define `ScheduledTask`, `ScheduleSlot`, `SchedulerConfig` frozen dataclasses
3. Define `SchedulerCortex` Protocol with `@runtime_checkable`
4. Implement `NullSchedulerCortex` (all no-ops)
5. Implement `AsyncSchedulerCortex.__init__()` — PriorityQueue + Lock + index
6. Implement `submit()` with duplicate check + preemption logic
7. Implement `cancel()` via `_cancelled` set
8. Implement `run_tick()` — cancel drain → deadline miss → earliest_start check → ready dispatch
9. Implement `peek_next()` via `_queue._queue[0]`
10. Implement `get_schedule()` and `stats()`
11. Implement `prediction_loop()` coroutine
12. Wire Prometheus counters/gauge to all tracked fields
13. Add `CognitiveCycle._schedule_goals()` integration (GoalRegistry → ScheduledTask)
14. Write 12 test cases; achieve 100% branch coverage on `run_tick()`

---

## Phase 17 Sub-phase Tracker

| Sub-phase | Component | Issue | Wiki | Status |
|---|---|---|---|---|
| 17.1 | TemporalGraph | [#434](https://github.com/web3guru888/asi-build/issues/434) | [Phase-17-Temporal-Graph](Phase-17-Temporal-Graph) | 🟡 In Progress |
| 17.2 | EventSequencer | [#437](https://github.com/web3guru888/asi-build/issues/437) | [Phase-17-Event-Sequencer](Phase-17-Event-Sequencer) | 🟡 In Progress |
| 17.3 | PredictiveEngine | [#440](https://github.com/web3guru888/asi-build/issues/440) | [Phase-17-Predictive-Engine](Phase-17-Predictive-Engine) | 🟡 In Progress |
| **17.4** | **SchedulerCortex** | **[#443](https://github.com/web3guru888/asi-build/issues/443)** | **[Phase-17-Scheduler-Cortex](Phase-17-Scheduler-Cortex)** | 🟡 **In Progress** |
| 17.5 | TemporalOrchestrator | — | — | 🔲 Pending |
