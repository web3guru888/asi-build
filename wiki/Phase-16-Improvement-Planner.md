# Phase 16.3 — `ImprovementPlanner`

**Phase**: 16 — Cognitive Reflection & Self-Improvement
**Component**: `ImprovementPlanner`
**Depends on**: Phase 16.2 [`WeaknessDetector`](Phase-16-Weakness-Detector) (#420)
**Feeds into**: Phase 16.4 `SelfOptimiser`
**Issue**: #423 | **Show & Tell**: #424 | **Q&A**: #425

---

## Overview

`ImprovementPlanner` bridges diagnostic signal and executable change. It consumes ranked `WeaknessReport` objects from `WeaknessDetector` and emits priority-sorted, safety-gated `ImprovementAction` records that the `SelfOptimiser` can schedule for execution.

---

## Enumerations

### `ActionKind`

```python
from enum import Enum, auto

class ActionKind(Enum):
    TUNE_THRESHOLD   = auto()   # adjust a detector/profiler parameter
    HOT_SWAP_MODULE  = auto()   # replace module via Phase 15 HotSwapper
    INCREASE_BUDGET  = auto()   # raise time/memory budget for a module
    REDUCE_LOAD      = auto()   # shed non-critical tasks from overloaded module
    FLAG_FOR_REVIEW  = auto()   # escalate to human operator (safety gate)
    NO_OP            = auto()   # weakness acknowledged but no safe action exists
```

---

## Frozen Dataclasses

### `ImprovementAction`

```python
@dataclass(frozen=True)
class ImprovementAction:
    module_name:   str
    action_kind:   ActionKind
    priority:      float                          # 0.0 – 1.0 (higher = more urgent)
    cost_estimate: float                          # 0.0 – 1.0 (normalised resource overhead)
    rationale:     str
    parameters:    Tuple[Tuple[str, str], ...] = ()
```

`parameters` uses a tuple of 2-tuples (not dict) so the dataclass remains hashable.
Convert to dict when reading: `dict(action.parameters)`.

### `PlannerConfig`

```python
@dataclass(frozen=True)
class PlannerConfig:
    max_actions_per_report: int   = 3
    safety_check_enabled:   bool  = True
    min_priority_threshold: float = 0.2   # discard actions below this
    cost_weight:            float = 0.3   # priority = urgency - cost_weight × cost
```

---

## Protocol

```python
from typing import Protocol, Sequence, runtime_checkable

@runtime_checkable
class ImprovementPlanner(Protocol):
    async def plan(
        self,
        reports: Sequence[WeaknessReport],
    ) -> Sequence[ImprovementAction]: ...

    async def reset(self) -> None: ...
    def stats(self) -> dict[str, int]: ...
```

---

## `RuleBasedPlanner` — Canonical Implementation

```python
import asyncio
from collections import defaultdict

_COST_TABLE: dict[ActionKind, float] = {
    ActionKind.TUNE_THRESHOLD:  0.05,
    ActionKind.INCREASE_BUDGET: 0.30,
    ActionKind.REDUCE_LOAD:     0.20,
    ActionKind.HOT_SWAP_MODULE: 0.70,
    ActionKind.FLAG_FOR_REVIEW: 0.01,
    ActionKind.NO_OP:           0.00,
}

class RuleBasedPlanner:
    _RULES: dict[WeaknessKind, list[ActionKind]] = {
        WeaknessKind.HIGH_LATENCY:    [ActionKind.HOT_SWAP_MODULE, ActionKind.INCREASE_BUDGET],
        WeaknessKind.HIGH_ERROR_RATE: [ActionKind.HOT_SWAP_MODULE, ActionKind.FLAG_FOR_REVIEW],
        WeaknessKind.LOW_THROUGHPUT:  [ActionKind.REDUCE_LOAD,      ActionKind.TUNE_THRESHOLD],
        WeaknessKind.LATENCY_SPIKE:   [ActionKind.INCREASE_BUDGET,  ActionKind.TUNE_THRESHOLD],
        WeaknessKind.DEGRADED:        [ActionKind.FLAG_FOR_REVIEW,  ActionKind.HOT_SWAP_MODULE],
    }

    def __init__(self, config: PlannerConfig | None = None, safety_filter=None) -> None:
        self._cfg      = config or PlannerConfig()
        self._safety   = safety_filter          # optional Phase 11 SafetyFilter
        self._lock     = asyncio.Lock()
        self._counters: dict[str, int] = defaultdict(int)

    async def plan(self, reports: Sequence[WeaknessReport]) -> Sequence[ImprovementAction]:
        actions: list[ImprovementAction] = []
        cap = self._cfg.max_actions_per_report * len(reports)
        async with self._lock:
            for report in reports:
                for kind in report.kinds:
                    for action_kind in self._RULES.get(kind, [ActionKind.NO_OP]):
                        urgency  = report.severity * report.confidence
                        cost     = _COST_TABLE.get(action_kind, 0.5)
                        priority = urgency - self._cfg.cost_weight * cost
                        priority = round(min(1.0, max(0.0, priority)), 4)
                        if priority < self._cfg.min_priority_threshold:
                            continue
                        action = ImprovementAction(
                            module_name   = report.module_name,
                            action_kind   = action_kind,
                            priority      = priority,
                            cost_estimate = cost,
                            rationale     = _rationale(report, action_kind),
                            parameters    = _params(report, action_kind),
                        )
                        if self._cfg.safety_check_enabled and self._safety:
                            if not await self._safety.is_safe(action):
                                action = _downgrade(action)
                        actions.append(action)
                        self._counters["planned"] += 1
                        if len(actions) >= cap:
                            break

        actions.sort(key=lambda a: a.priority, reverse=True)
        return actions

    async def reset(self) -> None:
        async with self._lock:
            self._counters.clear()

    def stats(self) -> dict[str, int]:
        return dict(self._counters)
```

---

## `NullPlanner` (testing / safe-mode stub)

```python
class NullPlanner:
    async def plan(self, reports): return []
    async def reset(self): pass
    def stats(self): return {}
```

---

## Helper Functions

```python
def _rationale(report: WeaknessReport, kind: ActionKind) -> str:
    return (
        f"{report.module_name} shows {', '.join(k.name for k in report.kinds)} "
        f"(severity={report.severity:.2f}, confidence={report.confidence:.2f}); "
        f"proposed action: {kind.name}"
    )

def _params(report: WeaknessReport, kind: ActionKind) -> tuple:
    if kind == ActionKind.TUNE_THRESHOLD:
        return (("target_module", report.module_name), ("metric", "p95_latency_ms"))
    if kind == ActionKind.HOT_SWAP_MODULE:
        return (("target_module", report.module_name),)
    return ()

def _downgrade(action: ImprovementAction) -> ImprovementAction:
    return ImprovementAction(
        module_name   = action.module_name,
        action_kind   = ActionKind.FLAG_FOR_REVIEW,
        priority      = action.priority,
        cost_estimate = 0.01,
        rationale     = f"[safety-gated] original={action.action_kind.name}; " + action.rationale,
        parameters    = action.parameters,
    )
```

---

## Data Flow

```
PerformanceProfiler
       |  ModuleProfile stream (p50/p95/p99 latency, error_rate, throughput_rps)
       v
WeaknessDetector ─────────────────────────────────> WeaknessReport[]
  (EMA baseline + threshold + spike detection)          severity, confidence, kinds
                                                              |
                                              ImprovementPlanner._lock acquired
                                                              |
                                              for report in reports:
                                                for kind in report.kinds:
                                                  for action_kind in _RULES[kind]:
                                                    compute urgency = sev × conf
                                                    compute priority = urgency - cost_weight × cost
                                                    if priority < min_priority_threshold: skip
                                                    if safety_filter.is_safe(): emit
                                                    else: _downgrade() → FLAG_FOR_REVIEW
                                                              |
                                              actions.sort(priority DESC)
                                                              |
                                              ImprovementAction[] ──────────> SelfOptimiser (Phase 16.4)
```

---

## Priority Formula

```
urgency  = severity × confidence      # both ∈ [0, 1]
priority = urgency − cost_weight × cost_estimate
priority = clamp(priority, 0.0, 1.0)
```

| severity | confidence | ActionKind | cost | priority |
|----------|-----------|------------|------|----------|
| 0.90 | 0.95 | TUNE_THRESHOLD | 0.05 | **0.840** |
| 0.90 | 0.95 | REDUCE_LOAD | 0.20 | **0.795** |
| 0.90 | 0.95 | HOT_SWAP_MODULE | 0.70 | **0.645** |
| 0.50 | 0.60 | INCREASE_BUDGET | 0.30 | **0.210** |

---

## Safety Gate

```
HOT_SWAP_MODULE ─[safety blocks]─> FLAG_FOR_REVIEW
  priority=0.645                     priority=0.645
  cost=0.70                          cost=0.01
  rationale: "[safety-gated] original=HOT_SWAP_MODULE; ..."
```

The safety gate is **non-lossy**: the operator sees the original intent, escalated not dropped.

---

## CognitiveCycle Integration

```python
# In CognitiveCycle._reflection_step():
async def _reflection_step(self) -> None:
    reports = await self._weakness_detector.analyse(self._profiler)
    actions = await self._improvement_planner.plan(reports)
    if actions:
        await self._self_optimiser.enqueue(actions)   # Phase 16.4
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_planner_actions_planned_total` | Counter | `module`, `action_kind` | Actions emitted |
| `asi_planner_actions_gated_total` | Counter | `module`, `action_kind` | Actions downgraded by safety gate |
| `asi_planner_plan_duration_seconds` | Histogram | — | End-to-end `plan()` latency |
| `asi_planner_priority_score` | Gauge | `module`, `action_kind` | Latest priority for each action |
| `asi_planner_no_op_total` | Counter | `module` | Reports mapped to NO_OP |

### PromQL Alerts

```promql
# Safety gate ratio too high
rate(asi_planner_actions_gated_total[5m])
  / rate(asi_planner_actions_planned_total[5m]) > 0.5

# Plan duration p99 > 100ms
histogram_quantile(0.99, rate(asi_planner_plan_duration_seconds_bucket[5m])) > 0.1
```

### Grafana Panel (4-panel layout)

```yaml
panels:
  - title: "Actions Planned/Gated per minute"
    type: timeseries
    targets:
      - expr: rate(asi_planner_actions_planned_total[1m])
        legendFormat: "planned {{ module }}/{{ action_kind }}"
      - expr: rate(asi_planner_actions_gated_total[1m])
        legendFormat: "gated {{ module }}/{{ action_kind }}"
  - title: "Safety Gate Ratio"
    type: gauge
    targets:
      - expr: |
          rate(asi_planner_actions_gated_total[5m])
          / rate(asi_planner_actions_planned_total[5m])
    fieldConfig:
      thresholds:
        steps: [{value: 0, color: green}, {value: 0.3, color: yellow}, {value: 0.5, color: red}]
  - title: "Plan Duration p99"
    type: stat
    targets:
      - expr: histogram_quantile(0.99, rate(asi_planner_plan_duration_seconds_bucket[5m]))
  - title: "Priority Score by Module"
    type: heatmap
    targets:
      - expr: asi_planner_priority_score
        legendFormat: "{{ module }}/{{ action_kind }}"
```

---

## `mypy --strict` Table

| Symbol | Type |
|--------|------|
| `ImprovementAction.parameters` | `Tuple[Tuple[str, str], ...]` |
| `RuleBasedPlanner._RULES` | `dict[WeaknessKind, list[ActionKind]]` |
| `RuleBasedPlanner.plan` return | `Sequence[ImprovementAction]` |
| `safety_filter.is_safe` | `Callable[[ImprovementAction], Awaitable[bool]]` |

---

## Test Targets (12 minimum)

1. `test_plan_single_high_latency` — HIGH_LATENCY report → HOT_SWAP_MODULE + INCREASE_BUDGET
2. `test_plan_priority_ordering` — multiple reports → sorted descending by priority
3. `test_priority_formula` — urgency - cost_weight × cost formula correctness
4. `test_min_priority_threshold_filters` — actions below threshold discarded
5. `test_safety_gate_downgrades` — HOT_SWAP_MODULE gated → FLAG_FOR_REVIEW
6. `test_null_planner` — empty return, no exceptions
7. `test_plan_degraded_report` — DEGRADED kind → FLAG_FOR_REVIEW + HOT_SWAP_MODULE
8. `test_max_actions_per_report` — cap respected under multi-report batch
9. `test_concurrent_plan_calls` — asyncio.gather(plan, plan) → no race
10. `test_reset_clears_counters` — stats() zero after reset()
11. `test_rationale_string_format` — rationale contains module_name + kind names
12. `test_no_op_emitted_for_unknown_kind` — unknown WeaknessKind → NO_OP

---

## Implementation Order (14 steps)

1. Add `ActionKind` enum to `asi_build/reflection/improvement_planner.py`
2. Add `ImprovementAction` frozen dataclass (tuple parameters)
3. Add `PlannerConfig` frozen dataclass
4. Add `ImprovementPlanner` Protocol (`@runtime_checkable`)
5. Implement `_COST_TABLE`, `_rationale()`, `_params()`, `_downgrade()` helpers
6. Implement `RuleBasedPlanner.__init__` (config + safety_filter + lock + counters)
7. Implement `RuleBasedPlanner.plan()` rule loop + priority formula + safety gate
8. Implement sort-by-priority + max_actions cap
9. Add `NullPlanner`
10. Add `make_planner()` factory
11. Wire `CognitiveCycle._reflection_step()` planner call
12. Add 5 Prometheus metrics
13. Write 12+ tests
14. Update `__init__.py` exports

---

## Phase 16 Sub-Phase Tracker

| Sub-phase | Component | Issue | Discussions | Status |
|-----------|-----------|-------|-------------|--------|
| 16.1 | PerformanceProfiler | #417 | #418 · #419 | 🟡 spec'd |
| 16.2 | WeaknessDetector | #420 | #421 · #422 | 🟡 spec'd |
| 16.3 | ImprovementPlanner | #423 | #424 · #425 | 🟡 spec'd |
| 16.4 | SelfOptimiser | — | — | ⏳ |
| 16.5 | ReflectionCycle | — | — | ⏳ |
