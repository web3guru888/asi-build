# Phase 18.1 — HorizonPlanner: Multi-Horizon Goal Decomposition

> **Phase 18 — Distributed Temporal Cognition** · Sub-phase 1 of 5

---

## Phase 18 Overview

Phase 18 extends ASI-Build's temporal reasoning capabilities (Phase 17) into a fully distributed, multi-horizon cognitive architecture. Where Phase 17 established the *plumbing* for temporal awareness, Phase 18 adds *intelligence*: the system can now plan across multiple time horizons, consolidate long-term memories, synchronise temporal state across federated nodes, index causal relationships for retrieval, and arbitrate coherence conflicts when distributed clocks diverge.

| Sub-phase | Component | Responsibility |
|-----------|-----------|----------------|
| **18.1** | **HorizonPlanner** | Classify goals into SHORT/MEDIUM/LONG buckets; EDF-drain per horizon |
| 18.2 | MemoryConsolidator | Compress episodic → semantic memory; replay buffer pruning |
| 18.3 | DistributedTemporalSync | Hybrid-logical-clock sync across federated nodes (Phase 9) |
| 18.4 | CausalMemoryIndex | Inverted index over TemporalGraph edges for causal retrieval |
| 18.5 | TemporalCoherenceArbiter | Detect & resolve temporal contradictions across distributed agents |

---

## Motivation

The Phase 17 `SchedulerCortex` schedules tasks within a *single tick window* using EDF.  
That works well for reactive, sub-second decisions — but ASI-Build needs to reason across:

- **Short horizon** (≤ 10 s) — reactive motor/tool actions, immediate plan steps
- **Medium horizon** (≤ 5 min) — multi-step sub-goals, dialogue turns, skill chaining
- **Long horizon** (> 5 min) — strategic objectives, background learning, federation coordination

`HorizonPlanner` bridges the gap: it sits *above* `SchedulerCortex` and classifies incoming goals before they are enqueued, ensuring each horizon's queue drains at the right rate.

---

## Design

### `PlanningHorizon` Enum

```python
from enum import Enum, auto

class PlanningHorizon(Enum):
    SHORT  = auto()   # deadline_ns ≤ now_ns + 10_000_000_000
    MEDIUM = auto()   # deadline_ns ≤ now_ns + 300_000_000_000
    LONG   = auto()   # deadline_ns >  now_ns + 300_000_000_000
```

#### Horizon Boundary Table

| Horizon | Upper bound (from now) | Nanosecond delta | Typical goals |
|---------|----------------------|------------------|---------------|
| `SHORT` | 10 seconds | 10 × 10⁹ | Reactive actions, immediate tool calls |
| `MEDIUM` | 5 minutes | 300 × 10⁹ | Multi-step sub-goals, skill chains |
| `LONG` | unbounded | > 300 × 10⁹ | Strategic objectives, federation tasks |

---

### Frozen Dataclasses

```python
from __future__ import annotations
from dataclasses import dataclass, field
import time

@dataclass(frozen=True)
class HorizonBucket:
    horizon:     PlanningHorizon
    goal_id:     str
    deadline_ns: int        # absolute CLOCK_REALTIME nanoseconds
    priority:    int        # 0 = highest; mirrors TaskPriority ordinal
    payload:     bytes      # serialised goal descriptor

    # EDF heap key: (deadline_ns, priority, goal_id) — stable sort
    def heap_key(self) -> tuple[int, int, str]:
        return (self.deadline_ns, self.priority, self.goal_id)


@dataclass(frozen=True)
class HorizonConfig:
    short_ceiling_ns:  int   = 10_000_000_000    # 10 s
    medium_ceiling_ns: int   = 300_000_000_000   # 5 min
    max_bucket_size:   int   = 4_096             # per horizon
    drain_batch_short: int   = 32               # goals drained per tick (SHORT)
    drain_batch_medium: int  = 8                # goals drained per tick (MEDIUM)
    drain_batch_long:  int   = 2                # goals drained per tick (LONG)
    rebalance_interval_s: float = 60.0          # seconds between rebalance sweeps
```

---

### `HorizonPlanner` Protocol

```python
from typing import Protocol, runtime_checkable, AsyncIterator

@runtime_checkable
class HorizonPlanner(Protocol):
    """Classifies incoming goals into horizon buckets and drains them in EDF order."""

    async def classify(self, bucket: HorizonBucket) -> None:
        """Enqueue a goal into the appropriate horizon bucket."""
        ...

    async def get_bucket(self, horizon: PlanningHorizon) -> list[HorizonBucket]:
        """Return a snapshot of all goals currently in the given horizon (ordered by EDF)."""
        ...

    async def rebalance(self) -> dict[PlanningHorizon, int]:
        """Re-classify goals whose horizon has shifted due to elapsed time.
        Returns mapping of horizon → number of goals promoted/demoted."""
        ...

    async def drain(self, horizon: PlanningHorizon) -> AsyncIterator[HorizonBucket]:
        """Yield up to drain_batch goals for the given horizon, removing them from the queue."""
        ...
```

---

### `PriorityHorizonPlanner` — Full Implementation

```python
import asyncio
import heapq
import time
from collections import defaultdict
from collections.abc import AsyncIterator

class PriorityHorizonPlanner:
    """
    Concrete HorizonPlanner using per-horizon min-heaps (EDF ordering).

    Thread-safety: all public methods are coroutines protected by asyncio.Lock.
    """

    def __init__(self, config: HorizonConfig = HorizonConfig()) -> None:
        self._config = config
        self._lock   = asyncio.Lock()
        # Per-horizon min-heaps: each item is (deadline_ns, priority, goal_id, bucket)
        self._heaps: dict[PlanningHorizon, list[tuple]] = {
            PlanningHorizon.SHORT:  [],
            PlanningHorizon.MEDIUM: [],
            PlanningHorizon.LONG:   [],
        }
        self._sizes: dict[PlanningHorizon, int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _now_ns(self) -> int:
        return time.time_ns()

    def _classify_horizon(self, deadline_ns: int) -> PlanningHorizon:
        delta = deadline_ns - self._now_ns()
        if delta <= self._config.short_ceiling_ns:
            return PlanningHorizon.SHORT
        if delta <= self._config.medium_ceiling_ns:
            return PlanningHorizon.MEDIUM
        return PlanningHorizon.LONG

    def _heap_push(self, horizon: PlanningHorizon, bucket: HorizonBucket) -> None:
        key = bucket.heap_key()
        heapq.heappush(self._heaps[horizon], (*key, bucket))
        self._sizes[horizon] += 1

    # ------------------------------------------------------------------
    # Protocol implementation
    # ------------------------------------------------------------------

    async def classify(self, bucket: HorizonBucket) -> None:
        horizon = self._classify_horizon(bucket.deadline_ns)
        async with self._lock:
            heap = self._heaps[horizon]
            if self._sizes[horizon] >= self._config.max_bucket_size:
                # Drop lowest-priority (highest deadline) goal to make room
                # Heapify on a max view: replace if new bucket has earlier deadline
                # Simple policy: silently discard if at capacity (LONG has buffer)
                return
            self._heap_push(horizon, bucket)

    async def get_bucket(self, horizon: PlanningHorizon) -> list[HorizonBucket]:
        async with self._lock:
            # Return sorted snapshot without mutating the heap
            return [item[-1] for item in sorted(self._heaps[horizon])]

    async def rebalance(self) -> dict[PlanningHorizon, int]:
        """
        Rebalance algorithm:
        1. For each horizon, pop ALL items.
        2. Re-classify each item against current clock.
        3. Push into the correct heap.
        Returns {horizon: delta} where delta = goals_moved_out (negative = received).
        """
        moved: dict[PlanningHorizon, int] = {h: 0 for h in PlanningHorizon}
        async with self._lock:
            all_buckets: list[HorizonBucket] = []
            for horizon, heap in self._heaps.items():
                while heap:
                    item = heapq.heappop(heap)
                    bucket: HorizonBucket = item[-1]
                    all_buckets.append((horizon, bucket))
                self._sizes[horizon] = 0

            for old_horizon, bucket in all_buckets:
                new_horizon = self._classify_horizon(bucket.deadline_ns)
                self._heap_push(new_horizon, bucket)
                if new_horizon != old_horizon:
                    moved[old_horizon] += 1   # lost a goal
        return moved

    async def drain(self, horizon: PlanningHorizon) -> AsyncIterator[HorizonBucket]:
        batch_size = {
            PlanningHorizon.SHORT:  self._config.drain_batch_short,
            PlanningHorizon.MEDIUM: self._config.drain_batch_medium,
            PlanningHorizon.LONG:   self._config.drain_batch_long,
        }[horizon]
        async with self._lock:
            heap = self._heaps[horizon]
            count = 0
            while heap and count < batch_size:
                item = heapq.heappop(heap)
                self._sizes[horizon] -= 1
                count += 1
                yield item[-1]
```

---

### `NullHorizonPlanner` — No-Op Implementation

```python
class NullHorizonPlanner:
    """Drop-in stub for testing / dependency injection without side effects."""

    async def classify(self, bucket: HorizonBucket) -> None:
        return

    async def get_bucket(self, horizon: PlanningHorizon) -> list[HorizonBucket]:
        return []

    async def rebalance(self) -> dict[PlanningHorizon, int]:
        return {h: 0 for h in PlanningHorizon}

    async def drain(self, horizon: PlanningHorizon):  # type: ignore[override]
        return
        yield  # make it an async generator
```

---

### `make_horizon_planner()` Factory

```python
def make_horizon_planner(
    config: HorizonConfig | None = None,
    *,
    null: bool = False,
) -> HorizonPlanner:
    """
    Factory function — returns the appropriate HorizonPlanner implementation.

    Args:
        config: Optional HorizonConfig; defaults to HorizonConfig() if None.
        null:   If True, returns NullHorizonPlanner (useful in unit tests).

    Returns:
        A HorizonPlanner-compatible instance.

    Example::

        planner = make_horizon_planner()                        # production
        planner = make_horizon_planner(null=True)               # tests
        planner = make_horizon_planner(HorizonConfig(max_bucket_size=1024))
    """
    if null:
        return NullHorizonPlanner()
    return PriorityHorizonPlanner(config or HorizonConfig())
```

---

## Data Flow ASCII Diagram

```
                        ┌─────────────────────────────────────────────────┐
                        │            CognitiveCycle._temporal_step()       │
                        └──────────────────────┬──────────────────────────┘
                                               │ new goal (goal_id, deadline_ns, priority, payload)
                                               ▼
                        ┌─────────────────────────────────────────────────┐
                        │             HorizonPlanner.classify()            │
                        │                                                  │
                        │   delta_ns = deadline_ns − now_ns               │
                        │   ≤ 10 s → SHORT heap                           │
                        │   ≤ 5 min → MEDIUM heap                         │
                        │   > 5 min → LONG heap                           │
                        └────────┬────────────┬────────────┬──────────────┘
                                 │            │            │
                          SHORT heap    MEDIUM heap    LONG heap
                          (min-heap,    (min-heap,     (min-heap,
                           EDF key)      EDF key)       EDF key)
                                 │            │            │
                    ─────────────────────────────────────────────────────
                    Every tick:  drain(SHORT) batch=32
                    Every 10s:   drain(MEDIUM) batch=8
                    Every 60s:   drain(LONG) batch=2  + rebalance()
                    ─────────────────────────────────────────────────────
                                 │            │            │
                                 └────────────┴────────────┘
                                               │
                                               ▼
                        ┌─────────────────────────────────────────────────┐
                        │          SchedulerCortex.submit_task()           │
                        │   (Phase 17.4 — EDF tick scheduling)            │
                        └─────────────────────────────────────────────────┘
```

---

## CognitiveCycle Integration Pattern

`HorizonPlanner` is composed into `CognitiveCycle` alongside `TemporalOrchestrator` (Phase 17.5):

```python
class CognitiveCycle:
    def __init__(
        self,
        *,
        horizon_planner: HorizonPlanner,
        temporal_orchestrator: TemporalOrchestrator,
        scheduler_cortex: SchedulerCortex,
        # … other sub-systems …
    ) -> None:
        self._horizon_planner = horizon_planner
        self._temporal_orchestrator = temporal_orchestrator
        self._scheduler = scheduler_cortex
        self._tick_count = 0

    async def _temporal_step(self, goal: HorizonBucket) -> None:
        # 1. Classify incoming goal into the right horizon bucket
        await self._horizon_planner.classify(goal)

        # 2. Drain SHORT goals every tick → hand off to SchedulerCortex
        async for bucket in self._horizon_planner.drain(PlanningHorizon.SHORT):
            task = ScheduledTask(
                task_id=bucket.goal_id,
                deadline_ns=bucket.deadline_ns,
                priority=TaskPriority(bucket.priority),
                payload=bucket.payload,
            )
            await self._scheduler.submit_task(task)

        self._tick_count += 1

        # 3. Drain MEDIUM every 10 ticks (assuming 1 s tick → 10 s cadence)
        if self._tick_count % 10 == 0:
            async for bucket in self._horizon_planner.drain(PlanningHorizon.MEDIUM):
                task = ScheduledTask(
                    task_id=bucket.goal_id,
                    deadline_ns=bucket.deadline_ns,
                    priority=TaskPriority(bucket.priority),
                    payload=bucket.payload,
                )
                await self._scheduler.submit_task(task)

        # 4. Rebalance + drain LONG every 60 ticks
        if self._tick_count % 60 == 0:
            await self._horizon_planner.rebalance()
            async for bucket in self._horizon_planner.drain(PlanningHorizon.LONG):
                task = ScheduledTask(
                    task_id=bucket.goal_id,
                    deadline_ns=bucket.deadline_ns,
                    priority=TaskPriority(bucket.priority),
                    payload=bucket.payload,
                )
                await self._scheduler.submit_task(task)
```

---

## SchedulerCortex Interaction Table

| HorizonPlanner action | SchedulerCortex effect | Phase 17.4 method |
|-----------------------|------------------------|-------------------|
| `drain(SHORT)` → `ScheduledTask` | Task enqueued with EDF key; may preempt current | `submit_task()` |
| `drain(MEDIUM)` → `ScheduledTask` | Task enqueued; lower urgency, preemption unlikely | `submit_task()` |
| `drain(LONG)` → `ScheduledTask` | Task enqueued at lowest urgency; background slot | `submit_task()` |
| `rebalance()` promotes LONG→SHORT | Next tick drain includes freshly promoted goals | implicit via `drain(SHORT)` |
| Bucket capacity exceeded | Goal silently dropped (SHORT first-come-first-served) | N/A — pre-filter |

---

## Prometheus Metrics

| Metric name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `asi_horizon_classified_total` | Counter | `horizon` | Goals classified into each horizon bucket |
| `asi_horizon_drained_total` | Counter | `horizon` | Goals drained and forwarded to SchedulerCortex |
| `asi_horizon_rebalanced_total` | Counter | `from_horizon`, `to_horizon` | Goals moved between horizons during rebalance |
| `asi_horizon_dropped_total` | Counter | `horizon` | Goals dropped due to bucket capacity overflow |
| `asi_horizon_queue_depth` | Gauge | `horizon` | Current number of goals in each horizon heap |

### PromQL Alerts

```yaml
# Alert: HIGH goal drop rate on SHORT horizon
- alert: HorizonPlannerShortQueueSaturation
  expr: rate(asi_horizon_dropped_total{horizon="SHORT"}[2m]) > 5
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "HorizonPlanner SHORT queue dropping goals"
    description: "More than 5 SHORT-horizon goals/s dropped — increase max_bucket_size or reduce goal submission rate."

# Alert: LONG horizon depth growing unbounded
- alert: HorizonPlannerLongQueueGrowth
  expr: asi_horizon_queue_depth{horizon="LONG"} > 2000
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "LONG horizon queue depth exceeds 2000"
    description: "Strategic goals accumulating faster than they are drained — check drain_batch_long or rebalance_interval_s."

# Alert: Rebalance demoting many MEDIUM→LONG (deadlines slipping)
- alert: HorizonPlannerDeadlineSlippage
  expr: rate(asi_horizon_rebalanced_total{from_horizon="SHORT",to_horizon="MEDIUM"}[5m]) > 1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Goals slipping from SHORT → MEDIUM horizon"
    description: "Goals are not being drained fast enough — SHORT deadlines becoming MEDIUM."
```

### Grafana Dashboard YAML (excerpt)

```yaml
panels:
  - title: Horizon Queue Depths
    type: timeseries
    targets:
      - expr: asi_horizon_queue_depth{horizon="SHORT"}
        legendFormat: SHORT
      - expr: asi_horizon_queue_depth{horizon="MEDIUM"}
        legendFormat: MEDIUM
      - expr: asi_horizon_queue_depth{horizon="LONG"}
        legendFormat: LONG

  - title: Drain Rate by Horizon
    type: timeseries
    targets:
      - expr: rate(asi_horizon_drained_total[1m])
        legendFormat: "{{horizon}}"

  - title: Goal Drop Rate
    type: stat
    targets:
      - expr: rate(asi_horizon_dropped_total[5m])
        legendFormat: "{{horizon}} drops/s"
```

---

## mypy Narrowing Table

| Variable | Declared type | After check | Narrowed type |
|----------|---------------|-------------|---------------|
| `planner` | `HorizonPlanner` | `isinstance(planner, PriorityHorizonPlanner)` | `PriorityHorizonPlanner` |
| `horizon` | `PlanningHorizon` | `horizon is PlanningHorizon.SHORT` | `Literal[PlanningHorizon.SHORT]` |
| `bucket` | `HorizonBucket \| None` | `if bucket is not None` | `HorizonBucket` |
| `config` | `HorizonConfig \| None` | `config = config or HorizonConfig()` | `HorizonConfig` |
| `item[-1]` | `object` (heap tuple) | cast via `bucket: HorizonBucket = item[-1]` | `HorizonBucket` |

---

## 12 Test Targets

| # | Test name | What it verifies |
|---|-----------|-----------------|
| 1 | `test_classify_short_horizon` | Goal with `deadline_ns = now + 5s` lands in SHORT heap |
| 2 | `test_classify_medium_horizon` | Goal with `deadline_ns = now + 2min` lands in MEDIUM heap |
| 3 | `test_classify_long_horizon` | Goal with `deadline_ns = now + 10min` lands in LONG heap |
| 4 | `test_edf_drain_order` | `drain(SHORT)` yields goals in ascending deadline order |
| 5 | `test_drain_respects_batch_size` | `drain(SHORT)` yields ≤ `drain_batch_short` goals |
| 6 | `test_capacity_drop_on_overflow` | 4097th goal to SHORT is silently dropped; metric incremented |
| 7 | `test_rebalance_promotes_medium_to_short` | After 9 s sleep, MEDIUM goal re-classified as SHORT |
| 8 | `test_rebalance_returns_moved_counts` | `rebalance()` return dict sums correctly |
| 9 | `test_get_bucket_snapshot_sorted` | `get_bucket()` returns sorted list without mutating heap |
| 10 | `test_null_planner_is_noop` | `NullHorizonPlanner` methods return empty / no-ops |
| 11 | `test_factory_returns_priority_planner` | `make_horizon_planner()` returns `PriorityHorizonPlanner` |
| 12 | `test_factory_null_flag` | `make_horizon_planner(null=True)` returns `NullHorizonPlanner` |

### Test Skeletons

```python
import asyncio, time, pytest
from asi_build.phase18.horizon_planner import (
    HorizonBucket, HorizonConfig, PlanningHorizon,
    PriorityHorizonPlanner, NullHorizonPlanner, make_horizon_planner,
)

@pytest.mark.asyncio
async def test_edf_drain_order():
    """drain(SHORT) must yield goals in ascending deadline_ns order."""
    planner = PriorityHorizonPlanner(HorizonConfig(drain_batch_short=10))
    now = time.time_ns()
    goals = [
        HorizonBucket(PlanningHorizon.SHORT, f"g{i}", now + i * 1_000_000_000, 0, b"")
        for i in range(5, 0, -1)   # insert reverse order
    ]
    for g in goals:
        await planner.classify(g)

    drained = [b async for b in planner.drain(PlanningHorizon.SHORT)]
    deadlines = [b.deadline_ns for b in drained]
    assert deadlines == sorted(deadlines), "EDF drain must be ascending by deadline_ns"


@pytest.mark.asyncio
async def test_rebalance_promotes_medium_to_short(monkeypatch):
    """A MEDIUM goal whose deadline is now ≤10 s away should move to SHORT after rebalance."""
    planner = PriorityHorizonPlanner()
    now = time.time_ns()

    # Goal with deadline 8 s from now — currently MEDIUM if we fake now to be 4 min ago
    future_deadline = now + 8_000_000_000   # 8 s → SHORT at real clock

    # Fake classify as MEDIUM by temporarily shifting _now_ns to 4 minutes in the past
    original_now = planner._now_ns

    def past_now():
        return now - 250_000_000_000   # 250 s ago → deadline was 258 s away → MEDIUM

    monkeypatch.setattr(planner, "_now_ns", past_now)
    bucket = HorizonBucket(PlanningHorizon.MEDIUM, "g_slip", future_deadline, 0, b"")
    await planner.classify(bucket)
    assert len(await planner.get_bucket(PlanningHorizon.MEDIUM)) == 1

    monkeypatch.setattr(planner, "_now_ns", original_now)  # restore real clock
    moved = await planner.rebalance()
    assert moved[PlanningHorizon.MEDIUM] >= 1
    assert len(await planner.get_bucket(PlanningHorizon.SHORT)) == 1
    assert len(await planner.get_bucket(PlanningHorizon.MEDIUM)) == 0
```

---

## 14-Step Implementation Order

| Step | Action |
|------|--------|
| 1 | Add `PlanningHorizon` enum to `asi_build/phase18/__init__.py` |
| 2 | Define `HorizonBucket` frozen dataclass with `heap_key()` method |
| 3 | Define `HorizonConfig` frozen dataclass with all tuning knobs |
| 4 | Write `HorizonPlanner` Protocol decorated `@runtime_checkable` |
| 5 | Implement `PriorityHorizonPlanner.__init__` with 3 per-horizon heaps |
| 6 | Implement `_classify_horizon()` using `_now_ns()` + config ceilings |
| 7 | Implement `classify()` with capacity guard and `_heap_push()` |
| 8 | Implement `get_bucket()` returning sorted snapshot |
| 9 | Implement `drain()` as async generator with batch limit |
| 10 | Implement `rebalance()` — full pop/re-classify/re-push cycle |
| 11 | Implement `NullHorizonPlanner` stub |
| 12 | Implement `make_horizon_planner()` factory |
| 13 | Register 5 Prometheus metrics; wire into each public method |
| 14 | Write 12 unit tests; run `mypy --strict`; update `CognitiveCycle._temporal_step()` |

---

## Phase 18 Sub-phase Tracker

| Sub-phase | Component | Issue | Wiki | Status |
|-----------|-----------|-------|------|--------|
| 18.1 | HorizonPlanner | #449 | [Phase-18-Horizon-Planner](Phase-18-Horizon-Planner) | 🟡 Spec filed |
| 18.2 | MemoryConsolidator | — | — | ⬜ Pending |
| 18.3 | DistributedTemporalSync | — | — | ⬜ Pending |
| 18.4 | CausalMemoryIndex | — | — | ⬜ Pending |
| 18.5 | TemporalCoherenceArbiter | — | — | ⬜ Pending |

---

## Cross-Phase Integration Map

```
Phase 10 — Goal Planning
  GoalRegistry.list_goals()  ──► HorizonPlanner.classify()
  GoalDecomposer sub-goals   ──► HorizonPlanner.classify()

Phase 13 — World Modelling
  DreamPlanner future goals  ──► HorizonPlanner.classify() (LONG horizon)
  CuriosityModule targets    ──► HorizonPlanner.classify() (MEDIUM horizon)

Phase 17 — Temporal Reasoning
  TemporalOrchestrator tick  ──► CognitiveCycle._temporal_step() ──► drain(SHORT)
  SchedulerCortex            ◄── drain(*/horizon) yields ScheduledTask

Phase 18 (this phase)
  HorizonPlanner             ──► MemoryConsolidator (18.2) long-horizon replay
  HorizonPlanner             ──► DistributedTemporalSync (18.3) cross-node goals
```

---

*Wiki page created by ASI-Build maintainer — Phase 18.1 spec · 2026-04-13*
