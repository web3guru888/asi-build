# Phase 10.5 — ReplanningEngine

**Module:** `asi.phase10.replanning`  
**Issue:** [#333](https://github.com/web3guru888/asi-build/issues/333)  
**Show & Tell:** [#334](https://github.com/web3guru888/asi-build/discussions/334)  
**Q&A:** [#335](https://github.com/web3guru888/asi-build/discussions/335)  
**Phase 11 Planning:** [#336](https://github.com/web3guru888/asi-build/discussions/336)  
**Phase:** 10 — Autonomous Goal Management (final sub-phase)

---

## Overview

`ReplanningEngine` closes the Phase 10 autonomy loop. When `ExecutionMonitor` detects a stalled or failed plan, `ReplanningEngine` decides whether to:

1. **Retry** the existing plan (same TaskGraph, different attempt)
2. **Redecompose** the goal with a different strategy (new TaskGraph)
3. **Escalate** the goal's priority in `GoalRegistry`
4. **Abandon** the goal (GoalStatus → ABANDONED)

The full Phase 10 closed loop:

```
GoalRegistry ──► GoalDecomposer ──► PlanExecutor ──► ExecutionMonitor
     ▲                                                       │
     │                                                       ▼
     └───────────────── ReplanningEngine ◄──────────────────┘
```

---

## Trigger Signals

| Signal | Source | Condition |
|--------|--------|-----------|
| `STALL_DETECTED` | `ExecutionMonitor.stalled_plans()` | `time_since_last_event > stall_timeout_ms` |
| `PLAN_FAILED` | `ExecutionMonitor.view().health_score == 0.0` | No RUNNING tasks remain |
| `DEADLINE_BREACH` | `GoalRegistry` deadline check | `deadline_at <= now()` |
| `EXTERNAL_TRIGGER` | API caller | Manual replan request |

---

## Data Models

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Mapping
import time

class ReplanReason(str, Enum):
    STALL_DETECTED   = "stall_detected"
    PLAN_FAILED      = "plan_failed"
    DEADLINE_BREACH  = "deadline_breach"
    EXTERNAL_TRIGGER = "external_trigger"

class ReplanOutcome(str, Enum):
    RETRY_SAME_PLAN    = "retry_same_plan"
    REDECOMPOSE_GOAL   = "redecompose_goal"
    ESCALATE_PRIORITY  = "escalate_priority"
    ABANDON_GOAL       = "abandon_goal"

@dataclass(frozen=True)
class ReplanRequest:
    goal_id:   str
    plan_id:   str
    reason:    ReplanReason
    attempt:   int = 0                           # 0 = first replan
    context:   Mapping[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class ReplanResult:
    goal_id:      str
    plan_id:      str                            # new plan_id if redecomposed
    outcome:      ReplanOutcome
    new_strategy: str | None = None
    message:      str = ""

@dataclass(frozen=True)
class ReplannerConfig:
    max_retries:             int   = 3
    retry_delay_ms:          int   = 2_000
    redecompose_strategies:  tuple[str, ...] = ("strips_lite", "linear", "parallel")
    abandon_after_strategies: bool = True
    stall_poll_interval_ms:  int   = 5_000

@dataclass(frozen=True)
class ReplannerSnapshot:
    total_replan_requests:   int
    total_retries:           int
    total_redecompositions:  int
    total_escalations:       int
    total_abandonments:      int
    active_replan_goals:     FrozenSet[str]
    captured_at:             float = field(default_factory=time.time)
```

---

## Protocols

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ReplanningEngine(Protocol):
    async def replan(self, request: ReplanRequest) -> ReplanResult: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def snapshot(self) -> ReplannerSnapshot: ...

@runtime_checkable
class ReplanStrategy(Protocol):
    """Pluggable decision logic for a replan request."""
    def decide(self, request: ReplanRequest, config: ReplannerConfig) -> ReplanOutcome: ...
```

---

## `DefaultReplanStrategy`

```python
class DefaultReplanStrategy:
    """
    Priority order:
    1. attempt < max_retries          → RETRY_SAME_PLAN
    2. strategies not exhausted       → REDECOMPOSE_GOAL (cycle strategies)
    3. abandon_after_strategies=True  → ABANDON_GOAL
    4. else                           → ESCALATE_PRIORITY
    """
    def decide(self, request: ReplanRequest, config: ReplannerConfig) -> ReplanOutcome:
        if request.attempt < config.max_retries:
            return ReplanOutcome.RETRY_SAME_PLAN
        strategy_index = request.attempt - config.max_retries
        if strategy_index < len(config.redecompose_strategies):
            return ReplanOutcome.REDECOMPOSE_GOAL
        if config.abandon_after_strategies:
            return ReplanOutcome.ABANDON_GOAL
        return ReplanOutcome.ESCALATE_PRIORITY
```

### Strategy Cycling Table (defaults)

| attempt | Outcome | `new_strategy` |
|---------|---------|----------------|
| 0 | RETRY_SAME_PLAN | — |
| 1 | RETRY_SAME_PLAN | — |
| 2 | RETRY_SAME_PLAN | — |
| 3 | REDECOMPOSE_GOAL | `strips_lite` |
| 4 | REDECOMPOSE_GOAL | `linear` |
| 5 | REDECOMPOSE_GOAL | `parallel` |
| 6 | ABANDON_GOAL | — |

---

## `InMemoryReplanningEngine`

### Initialization

```python
class InMemoryReplanningEngine:
    def __init__(
        self,
        goal_registry:     GoalRegistry,
        goal_decomposer:   GoalDecomposer,
        plan_executor:     PlanExecutor,
        execution_monitor: ExecutionMonitor,
        config:            ReplannerConfig = ReplannerConfig(),
        strategy:          ReplanStrategy  = DefaultReplanStrategy(),
    ) -> None:
        self._registry   = goal_registry
        self._decomposer = goal_decomposer
        self._executor   = plan_executor
        self._monitor    = execution_monitor
        self._config     = config
        self._strategy   = strategy
        self._active: dict[str, int] = {}    # goal_id → attempt count
        self._task: asyncio.Task | None = None
```

### `start()` / `stop()`

```python
async def start(self) -> None:
    self._task = asyncio.create_task(self._stall_poll_loop())

async def stop(self) -> None:
    if self._task:
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
```

### `_stall_poll_loop()`

```python
async def _stall_poll_loop(self) -> None:
    while True:
        await asyncio.sleep(self._config.stall_poll_interval_ms / 1000)
        try:
            stalled = await self._monitor.stalled_plans()
        except Exception:
            continue    # transient monitor errors must not crash the loop
        for plan_id in stalled:
            view = await self._monitor.view(plan_id)
            if view and view.goal_id not in self._active:
                # Guard: only one replan chain active per goal
                req = ReplanRequest(
                    goal_id=view.goal_id,
                    plan_id=plan_id,
                    reason=ReplanReason.STALL_DETECTED,
                    attempt=0,
                )
                asyncio.create_task(self.replan(req))
```

### `replan()` — Dispatch

```python
async def replan(self, request: ReplanRequest) -> ReplanResult:
    REPLAN_REQUESTS_TOTAL.labels(reason=request.reason.value).inc()
    outcome = self._strategy.decide(request, self._config)
    self._active[request.goal_id] = request.attempt + 1

    if outcome == ReplanOutcome.RETRY_SAME_PLAN:
        return await self._retry_same_plan(request)
    elif outcome == ReplanOutcome.REDECOMPOSE_GOAL:
        return await self._redecompose_goal(request)
    elif outcome == ReplanOutcome.ESCALATE_PRIORITY:
        return await self._escalate_priority(request)
    else:
        return await self._abandon_goal(request)
```

### Outcome Handlers

```python
async def _retry_same_plan(self, request: ReplanRequest) -> ReplanResult:
    REPLAN_RETRIES_TOTAL.inc()
    await asyncio.sleep(self._config.retry_delay_ms / 1000)
    goal = await self._registry.get(request.goal_id)
    if goal is None:
        return ReplanResult(request.goal_id, request.plan_id,
                            ReplanOutcome.ABANDON_GOAL, message="goal not found")
    graph = await self._decomposer.get_graph(request.plan_id)
    if graph:
        await self._executor.execute(goal, graph)
    return ReplanResult(request.goal_id, request.plan_id, ReplanOutcome.RETRY_SAME_PLAN)

async def _redecompose_goal(self, request: ReplanRequest) -> ReplanResult:
    strategy_index = request.attempt - self._config.max_retries
    strategy_name = self._config.redecompose_strategies[
        strategy_index % len(self._config.redecompose_strategies)
    ]
    REPLAN_REDECOMPOSITIONS_TOTAL.labels(strategy=strategy_name).inc()
    goal = await self._registry.get(request.goal_id)
    if goal is None:
        return ReplanResult(request.goal_id, request.plan_id, ReplanOutcome.ABANDON_GOAL)
    new_graph = await self._decomposer.decompose(goal, strategy=strategy_name)
    await self._executor.execute(goal, new_graph)
    return ReplanResult(request.goal_id, new_graph.plan_id,
                        ReplanOutcome.REDECOMPOSE_GOAL, new_strategy=strategy_name)

async def _escalate_priority(self, request: ReplanRequest) -> ReplanResult:
    REPLAN_ESCALATIONS_TOTAL.inc()
    await self._registry.escalate(request.goal_id)
    return ReplanResult(request.goal_id, request.plan_id, ReplanOutcome.ESCALATE_PRIORITY)

async def _abandon_goal(self, request: ReplanRequest) -> ReplanResult:
    REPLAN_ABANDONMENTS_TOTAL.labels(reason=request.reason.value).inc()
    await self._registry.update_status(request.goal_id, GoalStatus.ABANDONED)
    self._active.pop(request.goal_id, None)
    return ReplanResult(request.goal_id, request.plan_id, ReplanOutcome.ABANDON_GOAL)
```

### `snapshot()`

```python
def snapshot(self) -> ReplannerSnapshot:
    return ReplannerSnapshot(
        total_replan_requests=int(
            sum(REPLAN_REQUESTS_TOTAL.labels(r.value)._value.get()
                for r in ReplanReason)),
        total_retries=int(REPLAN_RETRIES_TOTAL._value.get()),
        total_redecompositions=int(
            sum(REPLAN_REDECOMPOSITIONS_TOTAL.labels(s)._value.get()
                for s in self._config.redecompose_strategies)),
        total_escalations=int(REPLAN_ESCALATIONS_TOTAL._value.get()),
        total_abandonments=int(
            sum(REPLAN_ABANDONMENTS_TOTAL.labels(r.value)._value.get()
                for r in ReplanReason)),
        active_replan_goals=frozenset(self._active.keys()),
    )
```

---

## Factory

```python
def build_replanning_engine(
    goal_registry:     GoalRegistry,
    goal_decomposer:   GoalDecomposer,
    plan_executor:     PlanExecutor,
    execution_monitor: ExecutionMonitor,
    config:            ReplannerConfig | None = None,
    strategy:          ReplanStrategy | None  = None,
) -> ReplanningEngine:
    return InMemoryReplanningEngine(
        goal_registry=goal_registry,
        goal_decomposer=goal_decomposer,
        plan_executor=plan_executor,
        execution_monitor=execution_monitor,
        config=config or ReplannerConfig(),
        strategy=strategy or DefaultReplanStrategy(),
    )
```

---

## `CognitiveCycle` Integration

```python
class CognitiveCycle:
    async def _run_autonomous_goal_management(self) -> None:
        """Phase 10 autonomous loop — starts ReplanningEngine background task."""
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.replanning_engine.start())

    async def _check_plan_health(self) -> None:
        """Called each cycle tick — trigger replan for zero-health plans."""
        if not self.execution_monitor or not self.replanning_engine:
            return
        for view in (await self.execution_monitor.snapshot()).plan_views.values():
            if view.health_score == 0.0 and not view.running_count:
                req = ReplanRequest(
                    goal_id=view.goal_id,
                    plan_id=view.plan_id,
                    reason=ReplanReason.PLAN_FAILED,
                    attempt=self._replan_attempts.get(view.goal_id, 0),
                )
                result = await self.replanning_engine.replan(req)
                self._replan_attempts[view.goal_id] = req.attempt + 1
                if result.outcome == ReplanOutcome.ABANDON_GOAL:
                    self._replan_attempts.pop(view.goal_id, None)
```

---

## Prometheus Metrics (5)

```python
REPLAN_REQUESTS_TOTAL = Counter(
    "asi_replan_requests_total",
    "Total replan requests received",
    ["reason"],
)
REPLAN_RETRIES_TOTAL = Counter(
    "asi_replan_retries_total",
    "Total RETRY_SAME_PLAN outcomes",
)
REPLAN_REDECOMPOSITIONS_TOTAL = Counter(
    "asi_replan_redecompositions_total",
    "Total REDECOMPOSE_GOAL outcomes",
    ["strategy"],
)
REPLAN_ESCALATIONS_TOTAL = Counter(
    "asi_replan_escalations_total",
    "Total ESCALATE_PRIORITY outcomes",
)
REPLAN_ABANDONMENTS_TOTAL = Counter(
    "asi_replan_abandonments_total",
    "Total ABANDON_GOAL outcomes",
    ["reason"],
)

# Pre-init all label combinations at module scope
for _r in ReplanReason:
    REPLAN_REQUESTS_TOTAL.labels(reason=_r.value)
    REPLAN_ABANDONMENTS_TOTAL.labels(reason=_r.value)
for _s in ("strips_lite", "linear", "parallel"):
    REPLAN_REDECOMPOSITIONS_TOTAL.labels(strategy=_s)
```

**PromQL examples:**

```promql
# Replan rate by reason
rate(asi_replan_requests_total[5m])

# Abandonment ratio (alert if > 10%)
rate(asi_replan_abandonments_total[5m])
  / rate(asi_replan_requests_total[5m]) > 0.1

# Strategy distribution
rate(asi_replan_redecompositions_total[10m])

# Retry vs redecompose ratio
rate(asi_replan_retries_total[5m])
  / rate(asi_replan_redecompositions_total[5m])
```

**Grafana alert rule:**

```yaml
- alert: HighReplanAbandonmentRate
  expr: >
    rate(asi_replan_abandonments_total[5m])
    / rate(asi_replan_requests_total[5m]) > 0.1
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "ReplanningEngine abandoning > 10% of goals"
```

---

## mypy Compliance Table

| Symbol | Type annotation | Notes |
|--------|-----------------|-------|
| `ReplanRequest.context` | `Mapping[str, str]` | Covariant — accepts `MappingProxyType` |
| `ReplannerConfig.redecompose_strategies` | `tuple[str, ...]` | Frozen, hashable |
| `InMemoryReplanningEngine._active` | `dict[str, int]` | Single event loop — no lock needed |
| `ReplanStrategy` | `Protocol` with `runtime_checkable` | Structural subtyping |
| `build_replanning_engine` return | `ReplanningEngine` (Protocol) | Not `InMemoryReplanningEngine` |

---

## Test Targets (12)

| # | Test | Coverage |
|---|------|----------|
| 1 | `test_default_strategy_retry_within_max` | attempt < max_retries → RETRY_SAME_PLAN |
| 2 | `test_default_strategy_redecompose_after_retries` | attempt == max_retries → REDECOMPOSE_GOAL |
| 3 | `test_default_strategy_abandon_after_strategies` | all strategies exhausted → ABANDON_GOAL |
| 4 | `test_default_strategy_escalate_if_no_abandon` | abandon_after_strategies=False → ESCALATE_PRIORITY |
| 5 | `test_replan_retry_reexecutes_graph` | RETRY path calls executor.execute() |
| 6 | `test_replan_redecompose_new_plan_id` | REDECOMPOSE path produces new plan_id |
| 7 | `test_replan_abandon_updates_goal_status` | ABANDON path → GoalStatus.ABANDONED |
| 8 | `test_replan_escalate_calls_registry` | ESCALATE path calls registry.escalate() |
| 9 | `test_stall_poll_triggers_replan` | stalled plan → replan called |
| 10 | `test_snapshot_reflects_counters` | Prometheus counters match snapshot |
| 11 | `test_prometheus_isolation` | Per-test CollectorRegistry, no cross-pollution |
| 12 | `test_cycle_integration` | `CognitiveCycle._check_plan_health()` with health_score=0.0 |

---

## Implementation Order (14 Steps)

1. `ReplanReason` + `ReplanOutcome` enums
2. `ReplanRequest` + `ReplanResult` + `ReplannerConfig` + `ReplannerSnapshot` frozen dataclasses
3. `ReplanStrategy` Protocol
4. `ReplanningEngine` Protocol
5. `DefaultReplanStrategy.decide()`
6. Pre-init 5 Prometheus metrics at module scope
7. `InMemoryReplanningEngine.__init__()`
8. `start()` / `stop()` — asyncio task lifecycle
9. `_stall_poll_loop()` — background monitor poll
10. `replan()` — strategy dispatch
11. `_retry_same_plan()` + `_redecompose_goal()` + `_escalate_priority()` + `_abandon_goal()`
12. `snapshot()`
13. `build_replanning_engine()` factory
14. `CognitiveCycle._check_plan_health()` + `_run_autonomous_goal_management()`

---

## Phase 10 Roadmap (Complete)

| Sub-phase | Module | Issue | Status |
|-----------|--------|-------|--------|
| 10.1 | GoalRegistry | [#319](https://github.com/web3guru888/asi-build/issues/319) | ✅ Spec complete |
| 10.2 | GoalDecomposer | [#323](https://github.com/web3guru888/asi-build/issues/323) | 🟡 In progress |
| 10.3 | PlanExecutor | [#326](https://github.com/web3guru888/asi-build/issues/326) | 🟡 In progress |
| 10.4 | ExecutionMonitor | [#330](https://github.com/web3guru888/asi-build/issues/330) | 🟡 In progress |
| 10.5 | ReplanningEngine | [#333](https://github.com/web3guru888/asi-build/issues/333) | 🟡 Spec filed |

**Phase 10 is now fully spec'd.** The closed-loop autonomy cycle is complete.

**Phase 11 planning** → [Discussion #336](https://github.com/web3guru888/asi-build/discussions/336)
