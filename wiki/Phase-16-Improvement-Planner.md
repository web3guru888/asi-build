# Phase 16.3 — ImprovementPlanner

**Part of Phase 16: Cognitive Reflection & Self-Improvement**
**Issue**: #423 | **Show & Tell**: #424 | **Q&A**: #425
**Depends on**: Phase 16.2 `WeaknessDetector` | **Feeds into**: Phase 16.4 `SelfOptimiser`

---

## Overview

`ImprovementPlanner` bridges diagnostic signal and executable change. It consumes priority-ranked `WeaknessReport` objects from `WeaknessDetector` and produces priority-sorted `ImprovementAction` lists that `SelfOptimiser` can enact.

---

## Data Model

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Sequence

class ActionKind(Enum):
    TUNE_THRESHOLD   = auto()   # tighten/relax a detector/profiler param
    INCREASE_BUDGET  = auto()   # expand time or memory budget for the module
    REDUCE_LOAD      = auto()   # shed non-critical tasks to ease pressure
    HOT_SWAP_MODULE  = auto()   # replace underperforming module via Phase 15
    FLAG_FOR_REVIEW  = auto()   # safety-gated or composite: escalate to operator
    NO_OP            = auto()   # weakness acknowledged, no safe action available

# Cost estimates (higher = more disruptive)
_COSTS: dict[ActionKind, float] = {
    ActionKind.TUNE_THRESHOLD:  0.05,
    ActionKind.INCREASE_BUDGET: 0.30,
    ActionKind.REDUCE_LOAD:     0.20,
    ActionKind.HOT_SWAP_MODULE: 0.70,
    ActionKind.FLAG_FOR_REVIEW: 0.01,
    ActionKind.NO_OP:           0.00,
}

@dataclass(frozen=True)
class ImprovementAction:
    """A single, hashable improvement directive."""
    module_name:  str
    action_kind:  ActionKind
    priority:     float                        # [0.0, 1.0]  higher = more urgent
    rationale:    str
    parameters:   tuple[tuple[str, str], ...]  # key-value pairs; use dict() to read

@dataclass(frozen=True)
class PlannerConfig:
    cost_weight:            float = 0.3    # weight of cost in priority formula
    min_priority_threshold: float = 0.2   # discard actions below this priority
    max_actions_per_report: int   = 3     # global cap = this × len(reports)
    enable_safety_gate:     bool  = True
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ImprovementPlanner(Protocol):
    async def plan(
        self,
        reports: Sequence[WeaknessReport],
        *,
        config: PlannerConfig | None = None,
    ) -> list[ImprovementAction]: ...

    async def stats(self) -> dict[str, int]: ...
    async def reset(self) -> None: ...
```

---

## Priority Formula

```
urgency  = severity × confidence           # both ∈ [0, 1]
priority = urgency − cost_weight × cost    # clamp to [0.0, 1.0]
```

### Worked Example (severity=0.9, confidence=0.95, urgency=0.855)

| ActionKind | Cost | Priority |
|---|---|---|
| `TUNE_THRESHOLD` | 0.05 | **0.840** |
| `REDUCE_LOAD` | 0.20 | **0.795** |
| `INCREASE_BUDGET` | 0.30 | **0.765** |
| `HOT_SWAP_MODULE` | 0.70 | **0.645** |

Low-cost actions float to the top — the planner prefers cheap fixes unless urgency is extreme.

---

## Rule Table: WeaknessKind → ActionKind

```python
_RULES: dict[WeaknessKind, list[ActionKind]] = {
    WeaknessKind.HIGH_LATENCY:    [ActionKind.HOT_SWAP_MODULE, ActionKind.INCREASE_BUDGET],
    WeaknessKind.HIGH_ERROR_RATE: [ActionKind.HOT_SWAP_MODULE, ActionKind.FLAG_FOR_REVIEW],
    WeaknessKind.LOW_THROUGHPUT:  [ActionKind.REDUCE_LOAD,     ActionKind.TUNE_THRESHOLD],
    WeaknessKind.LATENCY_SPIKE:   [ActionKind.INCREASE_BUDGET, ActionKind.TUNE_THRESHOLD],
    WeaknessKind.DEGRADED:        [ActionKind.FLAG_FOR_REVIEW, ActionKind.HOT_SWAP_MODULE],
}
```

---

## `RuleBasedPlanner` Implementation

```python
import asyncio
from collections import defaultdict

class RuleBasedPlanner:
    def __init__(
        self,
        config: PlannerConfig | None = None,
        safety_filter=None,          # duck-typed: async def is_safe(action) -> bool
    ) -> None:
        self._cfg   = config or PlannerConfig()
        self._safety = safety_filter
        self._lock  = asyncio.Lock()
        self._stats: dict[str, int] = defaultdict(int)

    async def plan(
        self,
        reports: Sequence[WeaknessReport],
        *,
        config: PlannerConfig | None = None,
    ) -> list[ImprovementAction]:
        cfg = config or self._cfg
        actions: list[ImprovementAction] = []
        cap = cfg.max_actions_per_report * len(reports)

        async with self._lock:
            for report in reports:
                if len(actions) >= cap:
                    break
                for kind in report.kinds:
                    if kind not in _RULES:
                        continue
                    for action_kind in _RULES[kind]:
                        cost     = _COSTS[action_kind]
                        urgency  = report.severity * getattr(report, "confidence", 1.0)
                        priority = urgency - cfg.cost_weight * cost
                        priority = min(1.0, max(0.0, priority))
                        if priority < cfg.min_priority_threshold:
                            self._stats["actions_below_threshold"] += 1
                            continue

                        action = ImprovementAction(
                            module_name = report.module_name,
                            action_kind = action_kind,
                            priority    = priority,
                            rationale   = (
                                f"{kind.name} detected; severity={report.severity:.2f}; "
                                f"confidence={getattr(report, 'confidence', 1.0):.2f}"
                            ),
                            parameters  = self._params(action_kind, report),
                        )

                        if cfg.enable_safety_gate and self._safety is not None:
                            if not await self._safety.is_safe(action):
                                action = self._downgrade(action)
                                self._stats["actions_gated"] += 1

                        actions.append(action)
                        self._stats["actions_planned"] += 1
                        if len(actions) >= cap:
                            break
                    if len(actions) >= cap:
                        break

            actions.sort(key=lambda a: a.priority, reverse=True)
            self._stats["plan_calls"] += 1
        return actions

    def _params(self, kind: ActionKind, report) -> tuple[tuple[str, str], ...]:
        base = (("module_name", report.module_name),)
        if kind == ActionKind.TUNE_THRESHOLD:
            return base + (("suggested_delta", "0.1"),)
        if kind == ActionKind.INCREASE_BUDGET:
            return base + (("budget_factor", "1.5"),)
        return base

    def _downgrade(self, action: ImprovementAction) -> ImprovementAction:
        return ImprovementAction(
            module_name = action.module_name,
            action_kind = ActionKind.FLAG_FOR_REVIEW,
            priority    = action.priority,
            rationale   = f"[safety-gated] original={action.action_kind.name}; " + action.rationale,
            parameters  = action.parameters,
        )

    async def stats(self) -> dict[str, int]:
        return dict(self._stats)

    async def reset(self) -> None:
        async with self._lock:
            self._stats.clear()
```

---

## `NullPlanner`

```python
class NullPlanner:
    """No-op planner — for testing or disabled-planning mode."""
    async def plan(self, reports, *, config=None) -> list[ImprovementAction]:
        return []
    async def stats(self) -> dict[str, int]:
        return {}
    async def reset(self) -> None:
        pass
```

---

## Data Flow ASCII

```
WeaknessDetector
      │ Sequence[WeaknessReport]  (sorted CRITICAL-first)
      ▼
RuleBasedPlanner.plan()
      │
      ├── for each report.kinds → _RULES lookup
      │       └── for each ActionKind → compute priority
      │               └── priority formula: urgency − cost_weight × cost
      │               └── safety gate → _downgrade() if blocked
      │
      ├── sort by priority DESC
      └── return list[ImprovementAction] (capped)
              │
              ▼
      SelfOptimiser.enact()   (Phase 16.4)
```

---

## Safety Gate Flow

```
Action produced
      │
      ▼
safety_filter.is_safe(action)?
      │
      ├── True  → action kept as-is
      └── False → _downgrade(action)
                     │
                     └── action_kind = FLAG_FOR_REVIEW
                         rationale = "[safety-gated] original=..." + original
                         priority = unchanged (priority preserved for ordering)
```

---

## CognitiveCycle Integration

```python
# In CognitiveCycle._reflection_step():
profiles  = await self._profiler.stats()
reports   = await self._weakness_detector.analyse(list(profiles.values()))
actions   = await self._improvement_planner.plan(reports)
# actions are priority-sorted; SelfOptimiser (16.4) enacts them
records   = await self._self_optimiser.enact(actions)
```

---

## Prometheus Metrics

| Metric | Type | Labels |
|---|---|---|
| `asi_planner_plan_calls_total` | Counter | `module` |
| `asi_planner_actions_planned_total` | Counter | `module`, `action_kind` |
| `asi_planner_actions_gated_total` | Counter | `module`, `action_kind` |
| `asi_planner_actions_below_threshold_total` | Counter | `module` |
| `asi_planner_plan_duration_seconds` | Histogram | `module` |

```promql
# Alert: high safety-gate rate
rate(asi_planner_actions_gated_total[5m])
  / rate(asi_planner_actions_planned_total[5m]) > 0.5

# Alert: slow planning
histogram_quantile(0.99, rate(asi_planner_plan_duration_seconds_bucket[5m])) > 0.1
```

```yaml
# Grafana alert
- alert: PlannerHighGateRate
  expr: >
    rate(asi_planner_actions_gated_total[5m])
    / rate(asi_planner_actions_planned_total[5m]) > 0.5
  for: 3m
  labels: { severity: warning }
  annotations:
    summary: "ImprovementPlanner safety-gate rate > 50%"
```

---

## mypy Strict Compatibility

| Symbol | Notes |
|---|---|
| `ImprovementAction` | `frozen=True`; `parameters: tuple[tuple[str,str],...]` — fully hashable |
| `PlannerConfig` | `frozen=True`; all fields typed |
| `ImprovementPlanner` | `@runtime_checkable` Protocol |
| `_downgrade()` | returns `ImprovementAction`, no `None` path |
| `_params()` | return type `tuple[tuple[str,str],...]` — matches field type |
| `asyncio.Lock` | held only in async context; no implicit `None` |

---

## Test Targets (12)

1. `test_high_latency_produces_hot_swap` — HIGH_LATENCY → HOT_SWAP_MODULE + INCREASE_BUDGET
2. `test_priority_formula_ordering` — TUNE_THRESHOLD beats HOT_SWAP_MODULE at equal urgency
3. `test_safety_gate_downgrades_hot_swap` — blocked HOT_SWAP → FLAG_FOR_REVIEW with gated rationale
4. `test_min_priority_threshold_filters` — low-severity reports produce no actions
5. `test_max_actions_cap_respected` — cap = max_actions_per_report × len(reports)
6. `test_null_planner_returns_empty` — NullPlanner → []
7. `test_concurrent_plan_calls` — asyncio.gather 3× plan, no exceptions, all non-empty
8. `test_stats_increment` — plan_calls / actions_planned / actions_gated counters
9. `test_reset_clears_stats` — reset() → stats() returns empty
10. `test_no_op_for_unknown_kind` — WeaknessKind not in _RULES → action skipped
11. `test_parameters_hashable` — ImprovementAction can be added to a set
12. `test_protocol_compliance` — `isinstance(RuleBasedPlanner(), ImprovementPlanner)`

---

## Implementation Order (14 steps)

1. `ActionKind` enum + `_COSTS` dict
2. `ImprovementAction` frozen dataclass
3. `PlannerConfig` frozen dataclass
4. `ImprovementPlanner` Protocol (`@runtime_checkable`)
5. `NullPlanner` no-op
6. `RuleBasedPlanner.__init__` (Lock + stats defaultdict)
7. `_params()` helper
8. `_downgrade()` helper
9. `RuleBasedPlanner.plan()` — rule loop + priority formula + cap
10. Safety gate integration (`is_safe` + `_downgrade`)
11. Prometheus metrics (wrap `plan()` with histogram timer)
12. `stats()` + `reset()`
13. `CognitiveCycle._reflection_step()` integration
14. All 12 tests green

---

## Phase 16 Sub-Phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 16.1 | `PerformanceProfiler` | #417 | 🟡 Spec filed |
| 16.2 | `WeaknessDetector` | #420 | 🟡 Spec filed |
| **16.3** | **`ImprovementPlanner`** | **#423** | 🟡 **Spec filed** |
| 16.4 | `SelfOptimiser` | #426 | 🟡 Spec filed |
| 16.5 | `ReflectionCycle` | — | ⏳ Upcoming |
