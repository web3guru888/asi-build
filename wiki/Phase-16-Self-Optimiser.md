# Phase 16.4 — SelfOptimiser

**Part of Phase 16: Cognitive Reflection & Self-Improvement**
**Issue**: #426 | **Show & Tell**: #427 | **Q&A**: #428
**Depends on**: Phase 16.3 `ImprovementPlanner` (#423), Phase 15.5 `LiveModuleOrchestrator` (#413), Phase 10.5 `ReplanningEngine` (#333)
**Feeds into**: Phase 16.5 `ReflectionCycle`

---

## Overview

`SelfOptimiser` is the **execution layer** of the Phase 16 self-improvement pipeline. It receives a priority-ranked `list[ImprovementAction]` from `ImprovementPlanner` and routes each action to the correct subsystem — adjusting thresholds, reallocating budgets, shedding load, or triggering a live module swap via `LiveModuleOrchestrator`.

---

## Data Model

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Sequence

class EnactmentStatus(Enum):
    SUCCESS      = auto()   # action fully applied
    PARTIAL      = auto()   # action applied but with reduced effect
    SKIPPED      = auto()   # preconditions not met; action deferred
    FAILED       = auto()   # subsystem call raised or returned error
    RATE_LIMITED = auto()   # cool-down window active; action deferred

@dataclass(frozen=True)
class EnactmentRecord:
    """Outcome of a single ImprovementAction enactment attempt."""
    action:       ImprovementAction
    status:       EnactmentStatus
    detail:       str
    duration_s:   float       # wall-clock seconds for enactment
    attempted_at: float       # time.monotonic() timestamp

@dataclass(frozen=True)
class OptimiserConfig:
    max_enactments_per_cycle: int   = 5      # cap applied actions per reflection cycle
    cool_down_s:              float = 60.0   # minimum gap between same-kind actions on same module
    dry_run:                  bool  = False  # log-only mode; no subsystem calls made
    enable_rate_limit:        bool  = True
    max_hot_swap_per_cycle:   int   = 2      # HOT_SWAP_MODULE actions are expensive; separate cap
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SelfOptimiser(Protocol):
    async def enact(
        self,
        actions: Sequence[ImprovementAction],
        *,
        config: OptimiserConfig | None = None,
    ) -> list[EnactmentRecord]: ...

    async def stats(self) -> dict[str, int]: ...
    async def reset(self) -> None: ...
```

---

## Dispatcher: ActionKind → Subsystem

| `ActionKind` | Subsystem Called | Notes |
|---|---|---|
| `TUNE_THRESHOLD` | `CognitiveCycle._detector_config` hot-update | Adjusts WeaknessDetector thresholds in-place |
| `INCREASE_BUDGET` | `CognitiveCycle._budget_map` | Raises allocated wall-time for target module |
| `REDUCE_LOAD` | `CognitiveCycle._load_shedder` | Signals load-shedder to de-prioritise module tasks |
| `HOT_SWAP_MODULE` | `LiveModuleOrchestrator.orchestrate_swap()` | Full Phase 15 swap pipeline |
| `FLAG_FOR_REVIEW` | `asyncio.Queue` → operator alert channel | Enqueued for human review; always SUCCESS |
| `NO_OP` | — | Logged and counted; always SKIPPED |

---

## `AsyncSelfOptimiser` — Reference Implementation

```python
import asyncio, logging, time
from collections import defaultdict
from typing import Sequence

log = logging.getLogger("asi_build.self_optimiser")

class AsyncSelfOptimiser:
    def __init__(
        self,
        orchestrator=None,     # LiveModuleOrchestrator | None
        cognitive_cycle=None,  # CognitiveCycle | None (duck-typed)
        alert_queue: asyncio.Queue | None = None,
        config: OptimiserConfig | None = None,
    ) -> None:
        self._orch   = orchestrator
        self._cycle  = cognitive_cycle
        self._alerts = alert_queue or asyncio.Queue()
        self._cfg    = config or OptimiserConfig()
        self._last_enacted: dict[tuple[str, str], float] = {}
        self._lock   = asyncio.Lock()
        self._stats: dict[str, int] = defaultdict(int)

    async def enact(
        self,
        actions: Sequence[ImprovementAction],
        *,
        config: OptimiserConfig | None = None,
    ) -> list[EnactmentRecord]:
        cfg = config or self._cfg
        records: list[EnactmentRecord] = []
        hot_swap_count = 0

        async with self._lock:
            for action in actions:
                if len(records) >= cfg.max_enactments_per_cycle:
                    break

                # Rate-limit gate
                key = (action.module_name, action.action_kind.name)
                if cfg.enable_rate_limit:
                    last = self._last_enacted.get(key, 0.0)
                    if time.monotonic() - last < cfg.cool_down_s:
                        records.append(EnactmentRecord(
                            action=action, status=EnactmentStatus.RATE_LIMITED,
                            detail=f"cool-down active ({cfg.cool_down_s}s)",
                            duration_s=0.0, attempted_at=time.monotonic(),
                        ))
                        self._stats["rate_limited"] += 1
                        continue

                # HOT_SWAP cap
                if action.action_kind.name == "HOT_SWAP_MODULE":
                    if hot_swap_count >= cfg.max_hot_swap_per_cycle:
                        records.append(EnactmentRecord(
                            action=action, status=EnactmentStatus.SKIPPED,
                            detail="hot-swap cap reached for this cycle",
                            duration_s=0.0, attempted_at=time.monotonic(),
                        ))
                        self._stats["skipped"] += 1
                        continue
                    hot_swap_count += 1

                record = await self._dispatch(action, cfg)
                records.append(record)
                if record.status == EnactmentStatus.SUCCESS:
                    self._last_enacted[key] = time.monotonic()
                    self._stats["enacted"] += 1
                elif record.status == EnactmentStatus.FAILED:
                    self._stats["failed"] += 1
                else:
                    self._stats["skipped"] += 1

            self._stats["enact_calls"] += 1
        return records

    async def _dispatch(self, action, cfg) -> EnactmentRecord:
        t0 = time.monotonic()
        params = dict(action.parameters)

        if cfg.dry_run:
            return self._record(action, EnactmentStatus.SKIPPED,
                                f"dry-run: would enact {action.action_kind.name}", t0)

        match action.action_kind.name:
            case "TUNE_THRESHOLD":
                return await self._apply_tune(action, params, t0)
            case "INCREASE_BUDGET":
                return await self._apply_budget(action, params, t0)
            case "REDUCE_LOAD":
                return await self._apply_load_shed(action, params, t0)
            case "HOT_SWAP_MODULE":
                return await self._apply_hot_swap(action, params, t0)
            case "FLAG_FOR_REVIEW":
                await self._alerts.put(action)
                return self._record(action, EnactmentStatus.SUCCESS, "queued for review", t0)
            case _:
                return self._record(action, EnactmentStatus.SKIPPED, "no-op", t0)

    async def _apply_hot_swap(self, action, params, t0) -> EnactmentRecord:
        if self._orch is None:
            return self._record(action, EnactmentStatus.SKIPPED, "no orchestrator injected", t0)
        try:
            req = OrchestratorRequest(
                module_id   = action.module_name,
                new_code    = b"",              # fetched from CodeSynthesiser in production
                new_version = params.get("target_version", "auto"),
                requester   = "self_optimiser",
            )
            result = await self._orch.orchestrate_swap(req)
            status = (EnactmentStatus.SUCCESS if result.outcome.name == "SUCCESS"
                      else EnactmentStatus.FAILED)
            return self._record(action, status,
                                f"orchestrator: {result.outcome.name} — {result.detail}", t0)
        except Exception as exc:
            return self._record(action, EnactmentStatus.FAILED, str(exc), t0)

    @staticmethod
    def _record(action, status, detail, t0) -> EnactmentRecord:
        return EnactmentRecord(action=action, status=status, detail=detail,
                               duration_s=time.monotonic() - t0,
                               attempted_at=time.monotonic())

    async def stats(self) -> dict[str, int]:
        return dict(self._stats)

    async def reset(self) -> None:
        async with self._lock:
            self._stats.clear()
            self._last_enacted.clear()
```

---

## `NullOptimiser`

```python
class NullOptimiser:
    """No-op optimiser — for testing or disabled-enactment mode."""
    async def enact(self, actions, *, config=None) -> list[EnactmentRecord]:
        return []
    async def stats(self) -> dict[str, int]:
        return {}
    async def reset(self) -> None:
        pass
```

---

## Data Flow ASCII

```
ImprovementPlanner
      │ list[ImprovementAction]  (priority-sorted, highest first)
      ▼
AsyncSelfOptimiser.enact()
      │
      ├── rate-limit gate  (module, kind) → cool_down_s
      ├── HOT_SWAP cap  (max_hot_swap_per_cycle)
      ├── global cap  (max_enactments_per_cycle)
      │
      └── _dispatch(action)
              │
              ├─ TUNE_THRESHOLD  ─► _apply_tune()   → _detector_config update
              ├─ INCREASE_BUDGET ─► _apply_budget()  → _budget_map update
              ├─ REDUCE_LOAD     ─► _apply_load_shed() → load_shedder.shed()
              ├─ HOT_SWAP_MODULE ─► _apply_hot_swap() → orchestrator.orchestrate_swap()
              ├─ FLAG_FOR_REVIEW ─► alert_queue.put()
              └─ NO_OP / unknown ─► SKIPPED record
      │
      └── list[EnactmentRecord]  (one per action attempted)
              │
              ▼
      ReflectionCycle.record_enactments()   (Phase 16.5)
```

---

## Rate-Limit Timeline Example

```
cool_down_s = 60

t=0s   TUNE_THRESHOLD modA → SUCCESS   → _last_enacted[("modA","TUNE_THRESHOLD")] = 0
t=10s  TUNE_THRESHOLD modA → RATE_LIMITED (10s < 60s)
t=10s  HOT_SWAP_MODULE modA → proceeds (different kind, not cross-throttled)
t=65s  TUNE_THRESHOLD modA → SUCCESS   (cool-down expired)
```

---

## CognitiveCycle Integration

```python
# In CognitiveCycle._reflection_step():
profiles  = await self._profiler.stats()
reports   = await self._weakness_detector.analyse(list(profiles.values()))
actions   = await self._improvement_planner.plan(reports)
records   = await self._self_optimiser.enact(actions)
# Forward to ReflectionCycle for retrospective analysis
await self._reflection_cycle.record_enactments(records)
```

---

## Prometheus Metrics

| Metric | Type | Labels |
|---|---|---|
| `asi_optimiser_enact_calls_total` | Counter | — |
| `asi_optimiser_actions_enacted_total` | Counter | `action_kind`, `status` |
| `asi_optimiser_actions_rate_limited_total` | Counter | `module`, `action_kind` |
| `asi_optimiser_hot_swaps_total` | Counter | `module`, `outcome` |
| `asi_optimiser_enact_duration_seconds` | Histogram | `action_kind` |

```promql
# Enactment failure rate > 30%
rate(asi_optimiser_actions_enacted_total{status="FAILED"}[5m])
  / rate(asi_optimiser_actions_enacted_total[5m]) > 0.3

# Hot-swap success rate < 80%
rate(asi_optimiser_hot_swaps_total{outcome="SUCCESS"}[10m])
  / rate(asi_optimiser_hot_swaps_total[10m]) < 0.8
```

```yaml
# Grafana alerts
- alert: OptimiserHighFailureRate
  expr: >
    rate(asi_optimiser_actions_enacted_total{status="FAILED"}[5m])
    / rate(asi_optimiser_actions_enacted_total[5m]) > 0.3
  for: 2m
  labels: { severity: critical }
  annotations:
    summary: "SelfOptimiser enactment failure rate > 30%"

- alert: OptimiserHotSwapLowSuccess
  expr: >
    rate(asi_optimiser_hot_swaps_total{outcome="SUCCESS"}[10m])
    / rate(asi_optimiser_hot_swaps_total[10m]) < 0.8
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "HOT_SWAP success rate below 80%"
```

---

## mypy Strict Compatibility

| Symbol | Notes |
|---|---|
| `EnactmentRecord` | `frozen=True`; `attempted_at: float` avoids `time.monotonic` return-type issues |
| `SelfOptimiser` | `@runtime_checkable` Protocol |
| `_last_enacted` | `dict[tuple[str, str], float]` — explicit type annotation required |
| `_dispatch` | always returns `EnactmentRecord`, no implicit `None` path |
| `match action.action_kind.name` | match on `str`, not enum — avoids incomplete-match warning |
| `AsyncSelfOptimiser` | satisfies `SelfOptimiser` Protocol via structural subtyping |

---

## Test Targets (12)

1. `test_flag_for_review_always_success` — FLAG_FOR_REVIEW always enqueued; status=SUCCESS
2. `test_no_op_returns_skipped` — NO_OP action → SKIPPED record
3. `test_dry_run_skips_all` — dry_run=True → all records SKIPPED, no subsystem calls
4. `test_rate_limit_gate` — same module+kind twice within cool_down_s → second RATE_LIMITED
5. `test_rate_limit_expires` — after cool_down_s elapses, second enactment proceeds
6. `test_hot_swap_cap` — max_hot_swap_per_cycle=1, two HOT_SWAP actions → second SKIPPED
7. `test_max_enactments_cap` — max_enactments_per_cycle=2, 5 actions → 2 records returned
8. `test_orchestrator_success` — mock orchestrator → SUCCESS EnactmentRecord
9. `test_orchestrator_failure` — mock orchestrator raises → FAILED record, no exception propagation
10. `test_tune_threshold_adjusts_config` — CognitiveCycle mock with `_detector_config` attribute
11. `test_concurrent_enact_calls` — asyncio.gather 3× enact → Lock prevents race
12. `test_reset_clears_state` — reset() → stats() empty, last_enacted cleared

---

## Implementation Order (14 steps)

1. `EnactmentStatus` enum
2. `EnactmentRecord` frozen dataclass
3. `OptimiserConfig` frozen dataclass
4. `SelfOptimiser` Protocol (`@runtime_checkable`)
5. `NullOptimiser` no-op
6. `AsyncSelfOptimiser.__init__` (inject orchestrator + cycle + alert_queue)
7. `_apply_tune()` dispatcher method
8. `_apply_budget()` dispatcher method
9. `_apply_load_shed()` dispatcher method
10. `_apply_hot_swap()` dispatcher method (delegates to LiveModuleOrchestrator)
11. `_dispatch()` match statement + FLAG_FOR_REVIEW + NO_OP branches
12. `enact()` — rate-limit gate + hot-swap cap + loop + stats
13. Prometheus metrics (instrument `enact()` with histogram + counters)
14. All 12 tests green; mypy `--strict` clean

---

## Phase 16 Sub-Phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 16.1 | `PerformanceProfiler` | #417 | 🟡 Spec filed |
| 16.2 | `WeaknessDetector` | #420 | 🟡 Spec filed |
| 16.3 | `ImprovementPlanner` | #423 | 🟡 Spec filed |
| **16.4** | **`SelfOptimiser`** | **#426** | 🟡 **Spec filed** |
| 16.5 | `ReflectionCycle` | — | ⏳ Upcoming |
