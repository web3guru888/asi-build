# Phase 10.3 — PlanExecutor
> **🎉 100th wiki page milestone!** This page marks the 100th entry in the ASI-Build knowledge base — from Cognitive Blackboard to Autonomous Goal Execution.

**Component**: `InMemoryPlanExecutor`
**Module**: `src/asi_build/cognition/goal_management/plan_executor.py`
**Phase**: 10.3 — Autonomous Goal Management
**Depends on**: Phase 10.1 GoalRegistry, Phase 10.2 GoalDecomposer, Phase 9.3 FederatedTaskRouter
**Issue**: [#326](https://github.com/web3guru888/asi-build/issues/326)

---

## Overview

`PlanExecutor` consumes a `TaskGraph` produced by `GoalDecomposer` and drives execution through topological ordering using `asyncio` concurrency. Each `SubTask` is dispatched through `FederatedTaskRouter` via the `TaskDispatcher` protocol, with configurable concurrency limits, exponential-backoff retry semantics, and partial-failure recovery modes.

**Integration chain**:
```
GoalRegistry (ACTIVE goal)
    → GoalDecomposer.decompose(goal)
    → TaskGraph
    → PlanExecutor.execute(graph, context)
    → PlanResult
    → GoalRegistry.update_status()
```

---

## Dataclasses

### `ExecutionState` (enum)

```python
from enum import Enum

class ExecutionState(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    FAILED    = "failed"
    SKIPPED   = "skipped"
    RETRYING  = "retrying"
```

### `SubTaskResult`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class SubTaskResult:
    subtask_id:      str
    state:           ExecutionState
    output:          dict[str, Any]
    error:           str | None
    attempts:        int
    duration_ms:     float
    completed_at_ms: int
```

### `PlanResult`

```python
@dataclass(frozen=True)
class PlanResult:
    plan_id:         str
    goal_id:         str
    total_subtasks:  int
    completed:       int
    failed:          int
    skipped:         int
    duration_ms:     float
    subtask_results: tuple[SubTaskResult, ...]
```

### `ExecutorConfig`

```python
@dataclass(frozen=True)
class ExecutorConfig:
    max_concurrency:  int   = 8
    max_retries:      int   = 3
    retry_backoff_ms: int   = 500
    timeout_ms:       int   = 30_000
    skip_on_failure:  bool  = False
```

### `ExecutorSnapshot`

```python
@dataclass(frozen=True)
class ExecutorSnapshot:
    plan_id:         str
    active_subtasks: tuple[str, ...]
    pending_count:   int
    completed_count: int
    failed_count:    int
```

---

## Protocols

### `TaskDispatcher`

```python
from typing import Protocol, runtime_checkable
from asi_build.cognition.goal_management.types import SubTask, SubTaskResult

@runtime_checkable
class TaskDispatcher(Protocol):
    async def dispatch(
        self, subtask: SubTask, context: dict[str, Any]
    ) -> SubTaskResult: ...
```

### `PlanExecutor`

```python
@runtime_checkable
class PlanExecutor(Protocol):
    async def execute(
        self, graph: TaskGraph, context: dict[str, Any]
    ) -> PlanResult: ...

    def snapshot(self) -> ExecutorSnapshot: ...
```

---

## `InMemoryPlanExecutor`

### `__init__()`

```python
import asyncio
import random
import time

class InMemoryPlanExecutor:
    def __init__(
        self,
        config: ExecutorConfig,
        dispatcher: TaskDispatcher,
    ) -> None:
        self._cfg = config
        self._dispatcher = dispatcher
        self._sem = asyncio.Semaphore(config.max_concurrency)
        self._active: set[str] = set()
        self._plan_id: str = ""
        self._results: dict[str, SubTaskResult] = {}
```

### `_kahn_waves()` — Topological Sort into Execution Waves

```python
def _kahn_waves(self, graph: TaskGraph) -> list[list[SubTask]]:
    """Group SubTasks into execution waves using Kahn's algorithm."""
    in_degree: dict[str, int] = {st.subtask_id: 0 for st in graph.subtasks}
    dependents: dict[str, list[str]] = {st.subtask_id: [] for st in graph.subtasks}
    subtask_map: dict[str, SubTask] = {st.subtask_id: st for st in graph.subtasks}

    for edge in graph.edges:
        in_degree[edge.to_id] += 1
        dependents[edge.from_id].append(edge.to_id)

    waves: list[list[SubTask]] = []
    ready = [sid for sid, deg in in_degree.items() if deg == 0]

    while ready:
        wave = [subtask_map[sid] for sid in ready]
        waves.append(wave)
        next_ready: list[str] = []
        for sid in ready:
            for dep_id in dependents[sid]:
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    next_ready.append(dep_id)
        ready = next_ready

    if sum(len(w) for w in waves) != len(graph.subtasks):
        from asi_build.cognition.goal_management.errors import CycleDetectedError
        raise CycleDetectedError("TaskGraph contains a cycle — cannot execute")
    return waves
```

**Wave example — diamond DAG `A → {B, C} → D`**:
- Wave 0: `[A]`
- Wave 1: `[B, C]` — both dispatched concurrently
- Wave 2: `[D]` — after B and C complete

### `_dispatch_with_retry()` — Exponential Backoff

```python
async def _dispatch_with_retry(
    self, subtask: SubTask, context: dict[str, Any]
) -> SubTaskResult:
    cfg = self._cfg
    last_error: str = ""
    t0 = _now_ms()

    for attempt in range(cfg.max_retries + 1):
        if attempt > 0:
            delay = (cfg.retry_backoff_ms * (2 ** (attempt - 1)) / 1000
                     + random.uniform(0, 0.05))
            await asyncio.sleep(delay)
            _SUBTASKS_TOTAL.labels(state="retried").inc()

        try:
            result = await asyncio.wait_for(
                self._dispatcher.dispatch(subtask, context),
                timeout=cfg.timeout_ms / 1000,
            )
            _SUBTASKS_TOTAL.labels(state="success").inc()
            if attempt > 0:
                _RETRY_ATTEMPTS.labels(result="success").inc()
            return result
        except asyncio.TimeoutError:
            last_error = f"timeout after {cfg.timeout_ms}ms"
        except Exception as exc:
            last_error = str(exc)

    _SUBTASKS_TOTAL.labels(state="failed").inc()
    _RETRY_ATTEMPTS.labels(result="exhausted").inc()
    return SubTaskResult(
        subtask_id=subtask.subtask_id,
        state=ExecutionState.FAILED,
        output={}, error=last_error,
        attempts=cfg.max_retries + 1,
        duration_ms=float(_now_ms() - t0),
        completed_at_ms=_now_ms(),
    )
```

### `_execute_wave()` — Concurrent Dispatch with Semaphore

```python
async def _execute_wave(
    self,
    wave: list[SubTask],
    context: dict[str, Any],
    failed_ids: set[str],
) -> list[SubTaskResult]:
    async def run_one(subtask: SubTask) -> SubTaskResult:
        if subtask.subtask_id in failed_ids:
            _SUBTASKS_TOTAL.labels(state="skipped").inc()
            return SubTaskResult(
                subtask_id=subtask.subtask_id,
                state=ExecutionState.SKIPPED,
                output={}, error=None, attempts=0,
                duration_ms=0.0, completed_at_ms=_now_ms(),
            )
        async with self._sem:
            self._active.add(subtask.subtask_id)
            _ACTIVE_TASKS.set(len(self._active))
            try:
                return await self._dispatch_with_retry(subtask, context)
            finally:
                self._active.discard(subtask.subtask_id)
                _ACTIVE_TASKS.set(len(self._active))

    wave_start = _now_ms()
    results: list[SubTaskResult] = []
    try:
        results = list(await asyncio.gather(*[run_one(st) for st in wave]))
    except asyncio.CancelledError:
        executed_ids = {r.subtask_id for r in results}
        for st in wave:
            if st.subtask_id not in executed_ids:
                results.append(SubTaskResult(
                    subtask_id=st.subtask_id,
                    state=ExecutionState.SKIPPED,
                    output={}, error="cancelled", attempts=0,
                    duration_ms=0.0, completed_at_ms=_now_ms(),
                ))
        raise
    finally:
        _WAVE_DURATION.observe((_now_ms() - wave_start) / 1000)
    return results
```

### `execute()` — Main Execution Loop

```python
async def execute(
    self, graph: TaskGraph, context: dict[str, Any]
) -> PlanResult:
    self._plan_id = graph.plan_id
    self._results.clear()
    plan_start = _now_ms()
    failed_ids: set[str] = set()
    all_results: list[SubTaskResult] = []

    try:
        waves = self._kahn_waves(graph)
        for wave in waves:
            wave_results = await self._execute_wave(wave, context, failed_ids)
            all_results.extend(wave_results)
            for r in wave_results:
                self._results[r.subtask_id] = r
                if r.state == ExecutionState.FAILED:
                    if not self._cfg.skip_on_failure:
                        # Propagate: mark all dependents as failed_ids
                        failed_ids.update(
                            _collect_dependents(graph, r.subtask_id)
                        )
    except asyncio.CancelledError:
        pass  # remaining tasks already marked SKIPPED in _execute_wave

    completed = sum(1 for r in all_results if r.state == ExecutionState.SUCCESS)
    failed = sum(1 for r in all_results if r.state == ExecutionState.FAILED)
    skipped = sum(1 for r in all_results if r.state == ExecutionState.SKIPPED)

    plan_result = PlanResult(
        plan_id=graph.plan_id,
        goal_id=graph.goal_id,
        total_subtasks=len(graph.subtasks),
        completed=completed,
        failed=failed,
        skipped=skipped,
        duration_ms=float(_now_ms() - plan_start),
        subtask_results=tuple(all_results),
    )
    _PLAN_DURATION.observe(plan_result.duration_ms / 1000)
    return plan_result
```

### `snapshot()`

```python
def snapshot(self) -> ExecutorSnapshot:
    completed = sum(
        1 for r in self._results.values()
        if r.state == ExecutionState.SUCCESS
    )
    failed = sum(
        1 for r in self._results.values()
        if r.state == ExecutionState.FAILED
    )
    return ExecutorSnapshot(
        plan_id=self._plan_id,
        active_subtasks=tuple(sorted(self._active)),
        pending_count=0,  # computed dynamically from wave state if needed
        completed_count=completed,
        failed_count=failed,
    )
```

---

## `RouterTaskDispatcher`

```python
from asi_build.cognition.federation.router import FederatedTaskRouter
from asi_build.cognition.federation.types import (
    TaskEnvelope, RoutingDecision,
)

class RouterTaskDispatcher:
    def __init__(self, router: FederatedTaskRouter) -> None:
        self._router = router

    async def dispatch(
        self, subtask: SubTask, context: dict[str, Any]
    ) -> SubTaskResult:
        envelope = TaskEnvelope(
            task_id=subtask.subtask_id,
            payload={"subtask": subtask, "context": context},
            required_caps=frozenset(
                subtask.metadata.get("required_caps", [])
            ),
            priority=subtask.metadata.get("priority", 5),
        )
        t0 = _now_ms()
        routing_result = await self._router.route(envelope)
        elapsed = float(_now_ms() - t0)

        if routing_result.decision == RoutingDecision.FALLBACK:
            return SubTaskResult(
                subtask_id=subtask.subtask_id,
                state=ExecutionState.FAILED,
                output={},
                error="routing fallback — no eligible peer",
                attempts=1,
                duration_ms=elapsed,
                completed_at_ms=_now_ms(),
            )
        return SubTaskResult(
            subtask_id=subtask.subtask_id,
            state=ExecutionState.SUCCESS,
            output=routing_result.peer_response or {},
            error=None,
            attempts=1,
            duration_ms=elapsed,
            completed_at_ms=_now_ms(),
        )
```

---

## `build_plan_executor()` Factory

```python
import os

def build_plan_executor(
    dispatcher: TaskDispatcher | None = None,
    router: FederatedTaskRouter | None = None,
) -> PlanExecutor:
    """
    Factory that reads configuration from environment variables.

    Environment variables:
      ASI_MAX_CONCURRENCY   — int (default: 8)
      ASI_MAX_RETRIES       — int (default: 3)
      ASI_RETRY_BACKOFF_MS  — int (default: 500)
      ASI_TASK_TIMEOUT_MS   — int (default: 30_000)
    """
    config = ExecutorConfig(
        max_concurrency=int(os.getenv("ASI_MAX_CONCURRENCY", "8")),
        max_retries=int(os.getenv("ASI_MAX_RETRIES", "3")),
        retry_backoff_ms=int(os.getenv("ASI_RETRY_BACKOFF_MS", "500")),
        timeout_ms=int(os.getenv("ASI_TASK_TIMEOUT_MS", "30000")),
    )
    if dispatcher is None:
        if router is None:
            from asi_build.cognition.federation.router import build_federated_task_router
            router = build_federated_task_router()
        dispatcher = RouterTaskDispatcher(router)
    return InMemoryPlanExecutor(config, dispatcher)
```

---

## CognitiveCycle Integration

```python
# In CognitiveCycle.run_once():
async def run_once(self, context: dict[str, Any]) -> None:
    # Gate: only execute if a goal is ACTIVE
    goal = await self.goal_registry.get_active_goal()
    if not goal:
        return

    # Decompose: generate TaskGraph
    graph = await self.goal_decomposer.decompose(goal)

    # Execute: run all sub-tasks in topological order
    result = await self.plan_executor.execute(graph, context=context)

    # Update: reflect outcome in GoalRegistry
    new_status = (
        GoalStatus.ACHIEVED if result.failed == 0 else GoalStatus.FAILED
    )
    await self.goal_registry.update_status(goal.goal_id, new_status)
```

---

## 5 Prometheus Metrics

```python
from prometheus_client import Counter, Gauge, Histogram

_SUBTASKS_TOTAL = Counter(
    "asi_plan_executor_subtasks_total",
    "SubTask execution outcomes",
    ["state"],
)
_ACTIVE_TASKS = Gauge(
    "asi_plan_executor_active_tasks",
    "Currently executing sub-tasks",
)
_WAVE_DURATION = Histogram(
    "asi_plan_executor_wave_duration_seconds",
    "Duration of each execution wave",
    buckets=[.05, .1, .25, .5, 1, 2.5, 5, 10],
)
_PLAN_DURATION = Histogram(
    "asi_plan_executor_plan_duration_seconds",
    "End-to-end plan execution duration",
    buckets=[.5, 1, 2.5, 5, 10, 30, 60, 120],
)
_RETRY_ATTEMPTS = Counter(
    "asi_plan_executor_retry_attempts_total",
    "Retry attempt outcomes",
    ["result"],
)

# Pre-initialize label combinations
for _s in ("success", "failed", "skipped", "retried"):
    _SUBTASKS_TOTAL.labels(state=_s)
for _r in ("success", "exhausted"):
    _RETRY_ATTEMPTS.labels(result=_r)
```

### PromQL Examples

| Panel | PromQL |
|---|---|
| SubTask failure rate | `rate(asi_plan_executor_subtasks_total{state="failed"}[5m])` |
| Active concurrency | `asi_plan_executor_active_tasks` |
| Wave p95 latency | `histogram_quantile(0.95, rate(asi_plan_executor_wave_duration_seconds_bucket[5m]))` |
| Plan p99 latency | `histogram_quantile(0.99, rate(asi_plan_executor_plan_duration_seconds_bucket[5m]))` |
| Retry exhaustion rate | `rate(asi_plan_executor_retry_attempts_total{result="exhausted"}[5m])` |

---

## mypy Strict Compliance Table

| Class | `--strict` requirement | Solution |
|---|---|---|
| `SubTaskResult` | `output: dict[str, Any]` → import `Any` | `from typing import Any` |
| `PlanResult` | `subtask_results: tuple[SubTaskResult, ...]` | Use built-in `tuple` (Python 3.9+) |
| `ExecutorConfig` | `skip_on_failure: bool = False` | No issue |
| `ExecutorSnapshot` | `active_subtasks: tuple[str, ...]` | No issue |
| `RouterTaskDispatcher` | `router: FederatedTaskRouter` type param | Import from federation module |
| `InMemoryPlanExecutor` | `_active: set[str]` — annotate explicitly | `self._active: set[str] = set()` |

---

## 12 Test Targets

| Test | Coverage |
|---|---|
| `test_execute_linear_graph` | A→B→C runs in order, all SUCCESS |
| `test_execute_diamond_dag` | A→{B,C}→D, B+C concurrent, D after both |
| `test_execute_concurrent_wave` | N independent tasks in single wave |
| `test_retry_success_on_second_attempt` | Fails once, succeeds on retry |
| `test_retry_exhausted_propagates_failure` | Exhausts max_retries → FAILED |
| `test_skip_on_failure_mode` | skip_on_failure=True → failed+dependents SKIPPED |
| `test_timeout_marks_subtask_failed` | Dispatcher hangs > timeout_ms → FAILED |
| `test_cancellation_skips_pending` | CancelledError mid-wave → remaining SKIPPED |
| `test_snapshot_reflects_active_tasks` | snapshot() during execute() shows active set |
| `test_metrics_incremented` | All 5 Prometheus metrics updated correctly |
| `test_router_dispatcher_integration` | RouterTaskDispatcher wraps TaskEnvelope correctly |
| `test_config_from_env` | build_plan_executor() reads ASI_* env vars |

---

## 14-Step Implementation Order

1. Add `ExecutionState` enum → `types.py`
2. Add `SubTaskResult`, `PlanResult`, `ExecutorConfig`, `ExecutorSnapshot` frozen dataclasses → `types.py`
3. Define `TaskDispatcher` Protocol → `protocols.py`
4. Define `PlanExecutor` Protocol → `protocols.py`
5. Initialize 5 Prometheus metrics with pre-init → `metrics.py`
6. Implement `_kahn_waves()` standalone function → `plan_executor.py`
7. Implement `InMemoryPlanExecutor.__init__()` (semaphore, state dicts, lock) → `plan_executor.py`
8. Implement `_dispatch_with_retry()` (backoff, timeout, state updates) → `plan_executor.py`
9. Implement `_execute_wave()` (gather, semaphore, cancellation guard) → `plan_executor.py`
10. Implement `execute()` (wave loop, failure propagation, PlanResult) → `plan_executor.py`
11. Implement `snapshot()` → `plan_executor.py`
12. Implement `RouterTaskDispatcher` → `router_dispatcher.py`
13. Implement `build_plan_executor()` factory (env-var config) → `factory.py`
14. Wire into `CognitiveCycle` with GoalRegistry gate check → `cycle.py`

---

## Phase 10 Roadmap

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 10.1 | GoalRegistry | [#319](https://github.com/web3guru888/asi-build/issues/319) | ✅ Spec complete |
| 10.2 | GoalDecomposer | [#323](https://github.com/web3guru888/asi-build/issues/323) | 🟡 In progress |
| 10.3 | PlanExecutor | [#326](https://github.com/web3guru888/asi-build/issues/326) | 🟡 In progress |
| 10.4 | ExecutionMonitor | — | 📋 Planned |
| 10.5 | ReplanningEngine | — | 📋 Planned |

---

## See Also

- [Phase 10.1 — Goal Registry](Phase-10-Goal-Registry)
- [Phase 10.2 — Goal Decomposer](Phase-10-Goal-Decomposer)
- [Phase 9.3 — Federated Task Router](Phase-9-Federated-Task-Router)
- [Phase 9.1 — Federation Gateway](Phase-9-Federation-Gateway)
