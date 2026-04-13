# Phase 7.5 — SleepPhaseOrchestrator

> **Status**: Specification (Issue #272)
> **Depends on**: Phase 6 (EWC + Fisher), Phase 7.1–7.4

---

## Overview

`SleepPhaseOrchestrator` is the final component of the Phase 7 meta-learning suite.  
It provides a single, fault-tolerant executor that wires every adaptation hook into the `SLEEP_PHASE` lifecycle in a deterministic, priority-sorted order.

---

## The Problem It Solves

After Phases 6–7.4 we have seven adaptation hooks that must run during each `SLEEP_PHASE`:

| Hook | Source |
|------|--------|
| Fisher accumulation flush | `FisherAccumulator` (Phase 6.4) |
| EWC regulariser update | `EWCRegulariser` (Phase 6.1–6.3) |
| Multi-task Fisher registration | `MultiTaskEWCRegulariser` (Phase 6.5) |
| Reptile meta-update | `ReptileMetaLearner` (Phase 7.1) |
| Curriculum scheduler step | `CurriculumScheduler` (Phase 7.2) |
| Replay buffer priority flush | `PrioritisedReplayBuffer` (Phase 7.3) |
| Hypernetwork context modulation | `HyperController` (Phase 7.4) |

Without an orchestrator: wrong ordering causes bugs, silent failures go undetected, and latency is opaque.

---

## Component Map

```
SLEEP_PHASE trigger
      │
      ▼
SleepPhaseOrchestrator.run_sleep_phase(ctx: SleepContext)
      │
      ├─ [priority 10]  FisherAccumulatorHook   ──► FisherAccumulator
      ├─ [priority 20]  EWCHook                 ──► EWCRegulariser
      ├─ [priority 25]  MultiTaskEWCHook        ──► MultiTaskEWCRegulariser
      ├─ [priority 30]  ReptileHook             ──► ReptileMetaLearner
      ├─ [priority 40]  CurriculumHook          ──► CurriculumScheduler
      ├─ [priority 50]  ReplayBufferHook        ──► PrioritisedReplayBuffer
      └─ [priority 60]  HyperControllerHook     ──► HyperController
             │
             ▼
      OrchestratorResult
        .hook_results       List[HookResult]
        .total_duration_s   float
        .budget_exceeded    bool
        .rolled_back        List[str]
```

---

## Data Classes

### `SleepContext` — immutable invocation context
```python
@dataclass(frozen=True)
class SleepContext:
    cycle_id: str
    task_id: str
    wall_clock_budget_s: float   # abort remaining hooks if exceeded
    metadata: dict[str, object]  # hook-to-hook data pass-through
```

### `HookResult` — per-hook outcome
```python
@dataclass(frozen=True)
class HookResult:
    hook_name: str
    success: bool
    duration_s: float
    error: Exception | None = None
```

### `OrchestratorResult` — full run summary
```python
@dataclass(frozen=True)
class OrchestratorResult:
    cycle_id: str
    hook_results: list[HookResult]
    total_duration_s: float
    budget_exceeded: bool
    rolled_back: list[str]   # hook names that were rolled back
```

### `OrchestratorSnapshot` — serialisable state for persistence
```python
@dataclass(frozen=True)
class OrchestratorSnapshot:
    circuit_states: dict[str, dict]   # hook_name → circuit breaker state
    hook_order: list[str]             # priority-sorted hook names
    captured_at: float
```

---

## `AdaptationHook` Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class AdaptationHook(Protocol):
    hook_name: str        # used as Prometheus label
    priority: int         # lower = runs first (0–99)
    async def run(self, ctx: SleepContext) -> HookResult: ...
    async def rollback(self, ctx: SleepContext) -> None: ...
```

Because it is `@runtime_checkable`, `isinstance(obj, AdaptationHook)` works at runtime without inheritance.

---

## Circuit-Breaker

Each hook gets its own independent `CircuitBreaker`:

```
    [CLOSED]  ──── N consecutive failures ────►  [OPEN]
        ▲                                            │
        │                                     recovery_window
        └──── trial success ────  [HALF-OPEN] ◄─────┘
                                       │
                                 trial failure ───► [OPEN]
```

```python
@dataclass
class CircuitBreaker:
    hook_name: str
    failure_threshold: int = 3
    recovery_window_s: float = 60.0
    _consecutive_failures: int = 0
    _tripped_at: float | None = None

    def is_open(self) -> bool:
        if self._tripped_at is None:
            return False
        if time.monotonic() - self._tripped_at >= self.recovery_window_s:
            # half-open: allow one trial
            self._tripped_at = None
            self._consecutive_failures = 0
            return False
        return True

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._tripped_at = None

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._tripped_at = time.monotonic()
```

---

## `SleepPhaseOrchestrator`

```python
class SleepPhaseOrchestrator:
    def __init__(
        self,
        hooks: list[AdaptationHook],
        *,
        wall_clock_budget_s: float = 30.0,
        circuit_failure_threshold: int = 3,
        circuit_recovery_window_s: float = 60.0,
    ) -> None:
        self._hooks = sorted(hooks, key=lambda h: h.priority)
        self._circuit_breakers: dict[str, CircuitBreaker] = {
            h.hook_name: CircuitBreaker(
                h.hook_name,
                failure_threshold=circuit_failure_threshold,
                recovery_window_s=circuit_recovery_window_s,
            )
            for h in hooks
        }
        self._budget = wall_clock_budget_s

    async def run_sleep_phase(self, ctx: SleepContext) -> OrchestratorResult: ...
    async def snapshot(self) -> OrchestratorSnapshot: ...
    async def restore(self, snap: OrchestratorSnapshot) -> None: ...
    def register_hook(self, hook: AdaptationHook) -> None: ...
    def deregister_hook(self, hook_name: str) -> None: ...
```

### Core loop (simplified)

```python
async def run_sleep_phase(self, ctx: SleepContext) -> OrchestratorResult:
    succeeded: list[AdaptationHook] = []
    rolled_back: list[str] = []
    results: list[HookResult] = []
    t_start = time.monotonic()

    for hook in self._hooks:
        elapsed = time.monotonic() - t_start
        if elapsed >= ctx.wall_clock_budget_s:
            ASI_BUDGET_EXCEEDED.inc()
            break

        cb = self._circuit_breakers[hook.hook_name]
        if cb.is_open():
            ASI_HOOKS_SKIPPED.labels(hook=hook.hook_name, reason="circuit_open").inc()
            continue

        result = await hook.run(ctx)
        results.append(result)
        ASI_HOOK_DURATION.labels(
            hook=hook.hook_name,
            status="success" if result.success else "failure",
        ).observe(result.duration_s)

        if result.success:
            cb.record_success()
            succeeded.append(hook)
        else:
            cb.record_failure()
            if cb.is_open():
                ASI_CIRCUIT_TRIPS.labels(hook=hook.hook_name).inc()
            for h in reversed(succeeded):
                await h.rollback(ctx)
                rolled_back.append(h.hook_name)
            # continue — fault-tolerant, not abort

    total = time.monotonic() - t_start
    ASI_ORCHESTRATOR_DURATION.observe(total)
    return OrchestratorResult(
        cycle_id=ctx.cycle_id,
        hook_results=results,
        total_duration_s=total,
        budget_exceeded=total >= ctx.wall_clock_budget_s,
        rolled_back=rolled_back,
    )
```

> **Design note**: hook failures trigger rollback of succeeded hooks in reverse order, but the orchestrator **continues** to remaining hooks. Partial adaptation is preferred over no adaptation. Set `failure_threshold=1` for strict abort behaviour.

---

## `build_sleep_orchestrator()` Factory

```python
def build_sleep_orchestrator(
    ewc: EWCRegulariser | None = None,
    fisher_accum: FisherAccumulator | None = None,
    multitask_ewc: MultiTaskEWCRegulariser | None = None,
    reptile: ReptileMetaLearner | None = None,
    curriculum: CurriculumScheduler | None = None,
    replay_buffer: PrioritisedReplayBuffer | None = None,
    hyper_controller: HyperController | None = None,
    *,
    wall_clock_budget_s: float = 30.0,
) -> SleepPhaseOrchestrator:
    hooks: list[AdaptationHook] = []
    if fisher_accum is not None:
        hooks.append(FisherAccumulatorHook(fisher_accum))    # priority 10
    if ewc is not None:
        hooks.append(EWCHook(ewc))                           # priority 20
    if multitask_ewc is not None:
        hooks.append(MultiTaskEWCHook(multitask_ewc))        # priority 25
    if reptile is not None:
        hooks.append(ReptileHook(reptile))                   # priority 30
    if curriculum is not None:
        hooks.append(CurriculumHook(curriculum))             # priority 40
    if replay_buffer is not None:
        hooks.append(ReplayBufferHook(replay_buffer))        # priority 50
    if hyper_controller is not None:
        hooks.append(HyperControllerHook(hyper_controller))  # priority 60
    return SleepPhaseOrchestrator(hooks, wall_clock_budget_s=wall_clock_budget_s)
```

`None` components are omitted — the orchestrator degrades gracefully to whatever hooks are registered.

---

## SLEEP_PHASE 9-Step Hook Order

| Step | Priority | Hook | Component | Phase |
|------|----------|------|-----------|-------|
| 1 | 10 | Fisher accumulation flush | `FisherAccumulator` | 6.4 |
| 2 | 20 | EWC regulariser update | `EWCRegulariser` | 6.1–6.3 |
| 3 | 25 | Multi-task Fisher registration | `MultiTaskEWCRegulariser` | 6.5 |
| 4 | 30 | Reptile meta-update | `ReptileMetaLearner` | 7.1 |
| 5 | 40 | Curriculum scheduler step | `CurriculumScheduler` | 7.2 |
| 6 | 50 | Replay buffer priority flush | `PrioritisedReplayBuffer` | 7.3 |
| 7 | 60 | Hypernetwork context modulation | `HyperController` | 7.4 |
| 8 | 70 | Snapshot all components | (internal) | 7.5 |
| 9 | 80 | Prometheus metric flush | (internal) | 7.5 |

### Why this ordering?

- **Fisher before EWC** — regulariser needs up-to-date importance weights.  
- **EWC before Reptile** — meta-update gradient must be constrained by EWC.  
- **Curriculum before replay** — task IDs sampled in step 5 affect priorities in step 6.  
- **Hypernetwork last** — reads post-Reptile weights for context-conditioned modulation.

---

## Prometheus Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `asi_sleep_orchestrator_duration_seconds` | Histogram | `cycle_id` |
| `asi_sleep_hook_duration_seconds` | Histogram | `hook`, `status` (`success`\|`failure`) |
| `asi_sleep_hook_circuit_trips_total` | Counter | `hook` |
| `asi_sleep_budget_exceeded_total` | Counter | — |
| `asi_sleep_hooks_skipped_total` | Counter | `hook`, `reason` (`circuit_open`\|`budget_exceeded`) |

### Recommended PromQL

```promql
# Any circuit tripped in last 5 min?
increase(asi_sleep_hook_circuit_trips_total[5m]) > 0

# Hook p95 latency (find slowest hook)
histogram_quantile(0.95, rate(asi_sleep_hook_duration_seconds_bucket[10m]))

# Budget breach rate per hour
increase(asi_sleep_budget_exceeded_total[1h])

# Skipped hooks (circuit open) as fraction of total runs
rate(asi_sleep_hooks_skipped_total{reason="circuit_open"}[10m])
/ rate(asi_sleep_orchestrator_duration_seconds_count[10m])
```

---

## Test Targets (12)

| # | Test |
|---|------|
| 1 | Hook ordering by priority matches expected sequence |
| 2 | Successful full run — all hooks execute, `budget_exceeded == False` |
| 3 | Circuit opens after `failure_threshold` consecutive failures |
| 4 | Open circuit skips hook, increments `circuit_trips_total` |
| 5 | Circuit half-open after `recovery_window_s` (mock `time.monotonic`) |
| 6 | Budget exceeded mid-run — remaining hooks skipped |
| 7 | `hook.rollback()` called on hook failure |
| 8 | Partial rollback — only succeeded hooks rolled back in reverse order |
| 9 | `register_hook` / `deregister_hook` round-trip |
| 10 | `snapshot()` / `restore()` preserves circuit states |
| 11 | Prometheus metrics emitted correctly (mock `CollectorRegistry`) |
| 12 | Factory with `None` components omits them from hook list |

---

## 10-Step Implementation Order

1. Define frozen dataclasses: `SleepContext`, `HookResult`, `OrchestratorResult`, `OrchestratorSnapshot`
2. Implement `AdaptationHook` Protocol with `@runtime_checkable`
3. Implement `CircuitBreaker` (closed / open / half-open FSM)
4. Implement `SleepPhaseOrchestrator.__init__` (sorted hooks + circuit map)
5. Implement `run_sleep_phase()` core loop with budget enforcement
6. Implement rollback logic (reverse succeeded list on failure)
7. Implement `snapshot()` / `restore()` for circuit state persistence
8. Add `register_hook()` / `deregister_hook()` mutation helpers
9. Pre-init Prometheus labels; add `build_sleep_orchestrator()` factory
10. Write 12 pytest tests; wire orchestrator into `CognitiveCycle.sleep_phase_hook()`

---

## Phase 7 Roadmap

| Sub-phase | Issue | Component |
|-----------|-------|-----------|
| 7.1 | #259 | `ReptileMetaLearner` |
| 7.2 | #262 | `TaskSampler`, `CurriculumScheduler` |
| 7.3 | #265 | `PrioritisedReplayBuffer` |
| 7.4 | #269 | `HyperNetwork`, `HyperController` |
| **7.5** | **#272** | **`SleepPhaseOrchestrator`** ← *this page* |

---

## Related Pages

- [Phase 6 EWC Foundation](Phase-6-EWC-Foundation)
- [Phase 6 Online Fisher](Phase-6-Online-Fisher)
- [Phase 6 Multi-Task EWC](Phase-6-Multi-Task-EWC)
- [Phase 7 Meta-Learning](Phase-7-Meta-Learning)
- [Phase 7 Task Sampler](Phase-7-Task-Sampler)
- [Phase 7 Replay Buffer](Phase-7-Replay-Buffer)
- [Phase 7 Hypernetwork](Phase-7-Hypernetwork)
