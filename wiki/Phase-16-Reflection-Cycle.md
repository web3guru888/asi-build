# Phase 16.5 — ReflectionCycle

> **Phase 16: Cognitive Reflection & Self-Improvement** | Sub-phase 5 of 5 | **Phase 16 COMPLETE 🎉**

## Overview

`ReflectionCycle` is the **capstone component of Phase 16**. It ties together the entire self-improvement pipeline into a continuous closed-loop that runs asynchronously alongside the `CognitiveCycle`:

```
PerformanceProfiler (16.1) ──► WeaknessDetector (16.2) ──► ImprovementPlanner (16.3) ──► SelfOptimiser (16.4)
         ▲                                                                                         │
         └─────────────────────── ReflectionCycle (16.5) ◄────────────────────────────────────────┘
```

The cycle runs **non-intrusively** inside the same asyncio event loop as `CognitiveCycle`, respecting the rate limits set by `SelfOptimiser` and optionally pausing for human approval before applying any changes.

---

## Enumerations

```python
from enum import Enum, auto

class CycleState(Enum):
    IDLE       = auto()   # waiting for next interval
    PROFILING  = auto()   # collecting profiler.stats()
    DETECTING  = auto()   # running WeaknessDetector
    PLANNING   = auto()   # running ImprovementPlanner
    OPTIMISING = auto()   # running SelfOptimiser.execute_batch()
    COOLDOWN   = auto()   # post-cycle cooldown sleep
    STOPPED    = auto()   # permanently halted
```

---

## Data Structures

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import time

@dataclass(frozen=True)
class CycleResult:
    cycle_id:          int
    weaknesses_found:  int
    actions_attempted: int
    actions_succeeded: int
    duration_ms:       float
    next_cycle_at:     float   # time.monotonic() epoch

@dataclass(frozen=True)
class ReflectionConfig:
    cycle_interval_seconds:   float = 300.0   # 5 min between cycles
    max_weaknesses_per_cycle: int   = 10       # cap planner input
    cooldown_seconds:         float = 60.0    # post-cycle sleep
    human_approval_required:  bool  = False   # approval gate
    enabled:                  bool  = True    # master on/off
    dry_run:                  bool  = False   # no-op optimise pass

    def __post_init__(self) -> None:
        if self.cycle_interval_seconds <= 0:
            raise ValueError("cycle_interval_seconds must be positive")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        if self.max_weaknesses_per_cycle < 1:
            raise ValueError("max_weaknesses_per_cycle must be >= 1")
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable, Any

@runtime_checkable
class ReflectionCycle(Protocol):
    async def start(self) -> None:
        """Launch the background cycle loop."""
        ...

    async def stop(self) -> None:
        """Signal stop and await clean drain."""
        ...

    async def run_once(self) -> CycleResult:
        """Execute one full reflection cycle synchronously."""
        ...

    def stats(self) -> dict[str, Any]:
        """Return cumulative statistics."""
        ...
```

---

## AsyncReflectionCycle Implementation

```python
import asyncio
import time
import logging
from dataclasses import replace
from typing import Callable, Awaitable, Any

logger = logging.getLogger(__name__)


class AsyncReflectionCycle:
    """Closed-loop self-improvement orchestrator."""

    def __init__(
        self,
        profiler:          PerformanceProfiler,
        detector:          WeaknessDetector,
        planner:           ImprovementPlanner,
        optimiser:         SelfOptimiser,
        config:            ReflectionConfig = ReflectionConfig(),
        approval_callback: Callable[[list[ImprovementAction]], Awaitable[bool]] | None = None,
    ) -> None:
        self._profiler     = profiler
        self._detector     = detector
        self._planner      = planner
        self._optimiser    = optimiser
        self._config       = config
        self._approval_cb  = approval_callback
        self._state        = CycleState.IDLE
        self._stopped      = False
        self._task: asyncio.Task | None = None
        self._cycle_count             = 0
        self._total_weaknesses_found  = 0
        self._total_actions_succeeded = 0
        self._start_time              = time.monotonic()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopped    = False
        self._start_time = time.monotonic()
        self._task = asyncio.create_task(
            self._cycle_loop(), name="reflection-cycle"
        )
        logger.info("ReflectionCycle started (interval=%.1fs)", self._config.cycle_interval_seconds)

    async def _cycle_loop(self) -> None:
        while not self._stopped:
            await asyncio.sleep(self._config.cycle_interval_seconds)
            if self._stopped:
                break
            if not self._config.enabled:
                continue
            try:
                result = await self.run_once()
                logger.info(
                    "ReflectionCycle #%d complete: %d weaknesses, %d/%d actions succeeded",
                    result.cycle_id, result.weaknesses_found,
                    result.actions_succeeded, result.actions_attempted,
                )
            except Exception as exc:
                logger.exception("ReflectionCycle iteration failed: %s", exc)

    async def run_once(self) -> CycleResult:
        t0 = time.monotonic()
        self._cycle_count += 1
        cycle_id = self._cycle_count

        # 1. PROFILING
        self._state = CycleState.PROFILING
        profiles = self._profiler.stats()

        # 2. DETECTING
        self._state = CycleState.DETECTING
        weaknesses = await self._detector.detect(profiles)
        capped = weaknesses[: self._config.max_weaknesses_per_cycle]
        self._total_weaknesses_found += len(capped)

        actions_attempted = 0
        actions_succeeded = 0

        if capped:
            # 3. PLANNING
            self._state = CycleState.PLANNING
            plan = await self._planner.plan(capped)

            # 3a. Human approval gate
            if self._config.human_approval_required and self._approval_cb is not None:
                approved = await self._approval_cb(plan.actions)
                if not approved:
                    logger.warning(
                        "ReflectionCycle #%d: human rejected plan, skipping optimise", cycle_id
                    )
                    plan = replace(plan, actions=[])

            # 4. OPTIMISING
            self._state = CycleState.OPTIMISING
            if not self._config.dry_run:
                results = await self._optimiser.execute_batch(plan.actions)
            else:
                results = []  # dry_run: no side effects
            actions_attempted = len(plan.actions)
            actions_succeeded = sum(1 for r in results if r.applied)
            self._total_actions_succeeded += actions_succeeded

        # 5. COOLDOWN
        self._state = CycleState.COOLDOWN
        await asyncio.sleep(self._config.cooldown_seconds)

        self._state = CycleState.IDLE
        duration_ms   = (time.monotonic() - t0) * 1000.0
        next_cycle_at = time.monotonic() + self._config.cycle_interval_seconds

        # Prometheus
        ASI_REFLECTION_CYCLES_TOTAL.inc()
        ASI_REFLECTION_WEAKNESSES_FOUND.inc(len(capped))
        ASI_REFLECTION_ACTIONS_SUCCEEDED.inc(actions_succeeded)
        ASI_REFLECTION_CYCLE_DURATION.observe(duration_ms / 1000.0)
        ASI_REFLECTION_STATE.set(int(self._state.value))

        return CycleResult(
            cycle_id=cycle_id,
            weaknesses_found=len(capped),
            actions_attempted=actions_attempted,
            actions_succeeded=actions_succeeded,
            duration_ms=duration_ms,
            next_cycle_at=next_cycle_at,
        )

    async def stop(self) -> None:
        self._stopped = True
        self._state   = CycleState.STOPPED
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ReflectionCycle stopped after %d cycles", self._cycle_count)

    def stats(self) -> dict[str, Any]:
        return {
            "cycle_count":             self._cycle_count,
            "total_weaknesses_found":  self._total_weaknesses_found,
            "total_actions_succeeded": self._total_actions_succeeded,
            "uptime_seconds":          time.monotonic() - self._start_time,
            "current_state":           self._state.name,
        }
```

---

## NullReflectionCycle

```python
class NullReflectionCycle:
    """No-op implementation for testing and dry environments."""

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def run_once(self) -> CycleResult:
        return CycleResult(
            cycle_id=0, weaknesses_found=0,
            actions_attempted=0, actions_succeeded=0,
            duration_ms=0.0,
            next_cycle_at=time.monotonic(),
        )

    def stats(self) -> dict[str, Any]:
        return {
            "cycle_count": 0, "total_weaknesses_found": 0,
            "total_actions_succeeded": 0, "uptime_seconds": 0.0,
            "current_state": "STOPPED",
        }
```

---

## State Machine

```
         ┌──────────────────────────────────────────────────────────┐
         │                    ReflectionCycle                        │
         │                                                            │
  start()│      sleep(interval)                                       │
    ──►  IDLE ──────────────► PROFILING                             │
         ▲                        │ profiler.stats()                  │
         │                        ▼                                   │
         │                    DETECTING                               │
         │                        │ detector.detect()                 │
         │                        ▼                                   │
         │                    PLANNING                                │
         │                        │ planner.plan()                    │
         │                        │ [approval gate?]                  │
         │                        ▼                                   │
         │  COOLDOWN ◄── OPTIMISING                                  │
         │  sleep(60s)    optimiser.execute_batch()                   │
         │     │                                                      │
         └─────┘                                                      │
                                                                      │
  stop() ──► STOPPED (from any state)                                │
         └──────────────────────────────────────────────────────────┘
```

---

## CycleState Transition Table

| From | To | Trigger |
|---|---|---|
| `IDLE` | `PROFILING` | `sleep(cycle_interval_seconds)` elapsed |
| `PROFILING` | `DETECTING` | `profiler.stats()` returned |
| `DETECTING` | `PLANNING` | weaknesses found (len > 0) |
| `DETECTING` | `COOLDOWN` | no weaknesses detected |
| `PLANNING` | `OPTIMISING` | plan ready, approved (or no approval required) |
| `PLANNING` | `COOLDOWN` | human rejected plan |
| `OPTIMISING` | `COOLDOWN` | `execute_batch()` complete |
| `COOLDOWN` | `IDLE` | `sleep(cooldown_seconds)` elapsed |
| any | `STOPPED` | `stop()` called |

---

## Integration: Running Alongside CognitiveCycle

```python
async def run_agent(
    cognitive:  CognitiveCycle,
    reflection: ReflectionCycle,
) -> None:
    """Launch both loops in the same event loop."""
    await asyncio.gather(
        cognitive.run(),     # primary perception-action loop
        reflection.start(),  # background self-improvement loop
    )
```

The two loops are **fully decoupled**:
- `CognitiveCycle` never blocks on reflection operations.
- `ReflectionCycle` operates on snapshots (`profiler.stats()`) not live data structures.
- `SelfOptimiser` rate-limits apply agent-wide — both loops respect them automatically.

### Closed-Loop Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        asyncio Event Loop                         │
│                                                                    │
│  ┌──────────────────────┐    ┌───────────────────────────────┐   │
│  │    CognitiveCycle     │    │      ReflectionCycle           │   │
│  │                       │    │                                │   │
│  │  perception           │    │  ① PROFILING                  │   │
│  │  → memory retrieval   │    │     profiler.stats()           │   │
│  │  → reasoning          │    │         ↓                     │   │
│  │  → action generation  │    │  ② DETECTING                  │   │
│  │  → execution          │    │     detector.detect(profiles)  │   │
│  │                       │    │         ↓                     │   │
│  │  (every tick)         │    │  ③ PLANNING                   │   │
│  └──────────────────────┘    │     planner.plan(weaknesses)   │   │
│          ↑                    │         ↓                     │   │
│    reads snapshots only       │  ④ [approval gate?]          │   │
│    (zero blocking)            │         ↓                     │   │
│                               │  ⑤ OPTIMISING                │   │
│                               │     optimiser.execute_batch() │   │
│                               │         ↓                     │   │
│                               │  ⑥ COOLDOWN → IDLE           │   │
│                               └───────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 16 Component Integration Map

| Component | Role in ReflectionCycle | Integration Point |
|---|---|---|
| **PerformanceProfiler** (16.1) | Provides per-module latency snapshots | `profiler.stats()` in PROFILING state |
| **WeaknessDetector** (16.2) | Identifies regressions from profiles | `detector.detect(profiles)` in DETECTING state |
| **ImprovementPlanner** (16.3) | Produces ranked action list | `planner.plan(weaknesses[:max])` in PLANNING state |
| **SelfOptimiser** (16.4) | Enacts improvements with rate limiting | `optimiser.execute_batch(plan.actions)` in OPTIMISING state |
| **Phase 15 LiveModuleOrchestrator** | HOT_SWAP delivery mechanism | Called by SelfOptimiser per HOT_SWAP action |
| **Phase 14 SandboxRunner** | SANDBOX_TEST validation | Called by SelfOptimiser before hot-swapping |
| **Phase 11 SafetyFilter** | Human approval gate | `approval_callback` before OPTIMISING |
| **Phase 10 ReplanningEngine** | Trigger re-plan if cycle fails | Monitor `CycleResult.actions_succeeded == 0` |

---

## Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

ASI_REFLECTION_CYCLES_TOTAL = Counter(
    "asi_reflection_cycles_total",
    "Total completed reflection cycles",
)
ASI_REFLECTION_WEAKNESSES_FOUND = Counter(
    "asi_reflection_weaknesses_found",
    "Cumulative weaknesses detected across all cycles",
)
ASI_REFLECTION_ACTIONS_SUCCEEDED = Counter(
    "asi_reflection_actions_succeeded",
    "Cumulative successful optimisation actions applied",
)
ASI_REFLECTION_CYCLE_DURATION = Histogram(
    "asi_reflection_cycle_duration_seconds",
    "Wall-clock duration of each full reflection cycle",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)
ASI_REFLECTION_STATE = Gauge(
    "asi_reflection_state",
    "Current CycleState as integer (1=IDLE … 7=STOPPED)",
)
```

### PromQL Examples

```promql
# Cycle rate per hour
rate(asi_reflection_cycles_total[1h]) * 3600

# Action success rate per cycle
rate(asi_reflection_actions_succeeded[1h]) /
clamp_min(rate(asi_reflection_cycles_total[1h]), 0.001)

# Average cycle duration (5 min window)
rate(asi_reflection_cycle_duration_seconds_sum[5m]) /
rate(asi_reflection_cycle_duration_seconds_count[5m])

# p95 cycle duration
histogram_quantile(0.95, rate(asi_reflection_cycle_duration_seconds_bucket[10m]))
```

### Grafana Alert — Cycle Stall

```yaml
- alert: ReflectionCycleStall
  expr: time() - asi_reflection_cycle_last_completed_timestamp > 600
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "ReflectionCycle has not completed in 10+ minutes"
    description: "Check asi_reflection_state gauge and container logs."
```

---

## mypy / Type Narrowing

| Pattern | Issue | Fix |
|---|---|---|
| `plan.actions` after approval gate | May be `[]` after `replace(plan, actions=[])` | Guard `if plan.actions:` before `execute_batch` |
| `results` list | `list[OptimiseResult]` vs empty `[]` | Declare `results: list[OptimiseResult] = []` before branch |
| `approval_callback` | `Callable[..., Awaitable[bool]] \| None` | `if self._approval_cb is not None:` before `await` |
| `CycleState.value` for gauge | `int` — must cast | `int(self._state.value)` for `ASI_REFLECTION_STATE.set()` |

---

## Test Targets

| # | Test | What it covers |
|---|---|---|
| 1 | `test_run_once_full_pipeline` | Happy path: all 4 components called in order |
| 2 | `test_run_once_no_weaknesses` | detector returns `[]`; planner/optimiser never called |
| 3 | `test_max_weaknesses_cap` | 20 detected; only 10 passed to planner |
| 4 | `test_human_approval_approved` | `approval_callback` returns `True`; optimise fires |
| 5 | `test_human_approval_rejected` | `approval_callback` returns `False`; optimise skipped |
| 6 | `test_dry_run_noop` | `dry_run=True`; `execute_batch` called with `[]` |
| 7 | `test_cycle_loop_repeats` | `start()` + sleep mock; `run_once` called N times |
| 8 | `test_stop_cancels_task` | `stop()` cancels background task cleanly |
| 9 | `test_stop_from_optimising_state` | Stop mid-cycle; no deadlock |
| 10 | `test_stats_after_cycles` | `stats()` returns correct cumulative counts |
| 11 | `test_null_reflection_cycle` | `NullReflectionCycle` satisfies `isinstance(x, ReflectionCycle)` |
| 12 | `test_concurrent_cognitive_reflection` | `asyncio.gather(cognitive.run(), reflection.start())` no interference |

---

## Implementation Order

1. Define `CycleState` enum (7 values)
2. Define `CycleResult` frozen dataclass (6 fields)
3. Define `ReflectionConfig` frozen dataclass + `__post_init__` validation
4. Define `ReflectionCycle` Protocol with `@runtime_checkable`
5. Implement `AsyncReflectionCycle.__init__` (inject all 4 components)
6. Implement `run_once()` — 5-phase state machine
7. Add human approval gate branch
8. Add `dry_run` passthrough
9. Implement `_cycle_loop()` with exception guard
10. Implement `start()` / `stop()` — task lifecycle
11. Implement `stats()`
12. Register 5 Prometheus metrics
13. Implement `NullReflectionCycle`
14. Write 12 test targets

---

## Phase 16 — Cognitive Reflection & Self-Improvement: COMPLETE 🎉

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 16.1 | PerformanceProfiler | #417 | 🟡 Open |
| 16.2 | WeaknessDetector | #420 | 🟡 Open |
| 16.3 | ImprovementPlanner | #423 | 🟡 Open |
| 16.4 | SelfOptimiser | #426 | 🟡 Open |
| **16.5** | **ReflectionCycle** | **#430** | 🟡 **Open** |

> **Phase 16 complete!** The ASI-Build engine can now profile its own performance, detect weaknesses, plan improvements, apply them safely, and repeat — all autonomously in the same event loop as the primary `CognitiveCycle`.

---

*See also: [Phase 15 — Runtime Self-Modification](Phase-15-Live-Module-Orchestrator) | [Phase 14 — Code Synthesis](Phase-14-Synthesis-Audit) | [Phase 11 — Safety & Alignment](Phase-11-Alignment-Dashboard)*

