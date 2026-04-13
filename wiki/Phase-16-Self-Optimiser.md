# Phase 16.4 — `SelfOptimiser`

**Phase**: 16 — Cognitive Reflection & Self-Improvement
**Component**: `SelfOptimiser`
**Depends on**: Phase 16.3 [`ImprovementPlanner`](Phase-16-Improvement-Planner) (#423)
**Feeds into**: Phase 16.5 `ReflectionCycle`
**Issue**: #426 | **Show & Tell**: #427 | **Q&A**: #428

---

## Overview

`SelfOptimiser` is the **action-enacting** layer of the Cognitive Reflection cycle. It receives `ImprovementAction` records from `ImprovementPlanner` and dispatches them to the appropriate subsystem:

| `ActionType` | Dispatcher | Phase dependency |
|---|---|---|
| `HOT_SWAP` | Phase 15 `LiveModuleOrchestrator` | Replace a running module at zero downtime |
| `CONFIG_TUNE` | In-process parameter registry | Adjust detector/profiler thresholds |
| `SANDBOX_TEST` | Phase 14 `SandboxRunner` | Validate a candidate patch before commit |
| `NO_OP` | — | Acknowledged; no structural change made |

The optimiser enforces **concurrency** (Semaphore) and **rate limiting** (token-bucket) so that a burst of improvement actions does not destabilise the system it is trying to improve.

---

## Enumerations

### `ActionType`

```python
from enum import Enum, auto

class ActionType(Enum):
    HOT_SWAP       = auto()   # swap a module via LiveModuleOrchestrator
    CONFIG_TUNE    = auto()   # update a runtime configuration parameter
    SANDBOX_TEST   = auto()   # run candidate patch in isolated sandbox
    NO_OP          = auto()   # plan acknowledged; no action taken
```

---

## Frozen Dataclasses

### `OptimiserResult`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class OptimiserResult:
    action_type:  ActionType
    module_name:  str
    success:      bool
    error_msg:    str                         # "" on success
    duration_ms:  float                       # wall-clock execution time
    metadata:     Tuple[Tuple[str, str], ...] = ()   # action-specific key/value pairs
```

Convert `metadata` to a dict when reading: `dict(result.metadata)`.

### `OptimiserConfig`

```python
@dataclass(frozen=True)
class OptimiserConfig:
    max_concurrent_actions: int   = 4          # asyncio.Semaphore capacity
    rate_limit_per_minute:  int   = 20         # token-bucket replenishment rate
    dry_run:                bool  = False      # log actions without executing
    enabled_action_types:   Tuple[ActionType, ...] = (
        ActionType.HOT_SWAP,
        ActionType.CONFIG_TUNE,
        ActionType.SANDBOX_TEST,
        ActionType.NO_OP,
    )
    timeout_seconds:        float = 30.0       # per-action timeout
```

When `dry_run=True`, every `_execute_single` call returns `OptimiserResult(success=True, error_msg="dry_run", ...)` without calling the downstream system.

---

## Protocol

```python
from typing import Protocol, Sequence, runtime_checkable

@runtime_checkable
class SelfOptimiser(Protocol):
    async def execute(
        self,
        action: ImprovementAction,
    ) -> OptimiserResult: ...

    async def execute_batch(
        self,
        actions: Sequence[ImprovementAction],
    ) -> Sequence[OptimiserResult]: ...

    def stats(self) -> dict[str, int]: ...
    async def reset(self) -> None: ...
```

`execute_batch` runs actions **concurrently** (subject to Semaphore), so callers must not rely on ordering of returned results relative to input actions. The index of each result corresponds to the same index in the input sequence.

---

## `AsyncSelfOptimiser` — Canonical Implementation

```python
import asyncio
import time
from collections import defaultdict

class AsyncSelfOptimiser:
    """
    Concurrent, rate-limited optimiser that dispatches ImprovementActions
    to HOT_SWAP / CONFIG_TUNE / SANDBOX_TEST / NO_OP handlers.
    """

    def __init__(
        self,
        config: OptimiserConfig | None = None,
        orchestrator=None,    # Phase 15 LiveModuleOrchestrator
        sandbox=None,         # Phase 14 SandboxRunner
        param_registry=None,  # runtime config parameter store
    ) -> None:
        self._cfg          = config or OptimiserConfig()
        self._orchestrator = orchestrator
        self._sandbox      = sandbox
        self._params       = param_registry
        self._semaphore    = asyncio.Semaphore(self._cfg.max_concurrent_actions)
        # Token-bucket state
        self._tokens       = float(self._cfg.rate_limit_per_minute)
        self._max_tokens   = float(self._cfg.rate_limit_per_minute)
        self._last_refill  = time.monotonic()
        self._token_lock   = asyncio.Lock()
        self._counters: dict[str, int] = defaultdict(int)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def execute(self, action: ImprovementAction) -> OptimiserResult:
        await self._acquire_token()
        async with self._semaphore:
            return await self._execute_single(action)

    async def execute_batch(
        self,
        actions: Sequence[ImprovementAction],
    ) -> Sequence[OptimiserResult]:
        tasks = [self.execute(action) for action in actions]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

    def stats(self) -> dict[str, int]:
        return dict(self._counters)

    async def reset(self) -> None:
        async with self._token_lock:
            self._tokens = self._max_tokens
            self._last_refill = time.monotonic()
            self._counters.clear()

    # ------------------------------------------------------------------ #
    # Token-bucket rate limiter                                            #
    # ------------------------------------------------------------------ #

    async def _acquire_token(self) -> None:
        """Block until a rate-limit token is available."""
        async with self._token_lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            # Replenish: rate_limit_per_minute tokens per 60 seconds
            refill = elapsed * (self._max_tokens / 60.0)
            self._tokens = min(self._max_tokens, self._tokens + refill)
            self._last_refill = now
            if self._tokens < 1.0:
                # Must wait
                wait_s = (1.0 - self._tokens) / (self._max_tokens / 60.0)
            else:
                wait_s = 0.0
            self._tokens = max(0.0, self._tokens - 1.0)
        if wait_s > 0:
            await asyncio.sleep(wait_s)

    # ------------------------------------------------------------------ #
    # Dispatcher                                                           #
    # ------------------------------------------------------------------ #

    async def _execute_single(self, action: ImprovementAction) -> OptimiserResult:
        if action.action_kind.name not in {at.name for at in self._cfg.enabled_action_types}:
            return OptimiserResult(
                action_type=ActionType.NO_OP,
                module_name=action.module_name,
                success=True,
                error_msg="action_type disabled in config",
                duration_ms=0.0,
            )

        if self._cfg.dry_run:
            return OptimiserResult(
                action_type=ActionType[action.action_kind.name],
                module_name=action.module_name,
                success=True,
                error_msg="dry_run",
                duration_ms=0.0,
            )

        t0 = time.monotonic()
        try:
            result = await asyncio.wait_for(
                self._dispatch(action),
                timeout=self._cfg.timeout_seconds,
            )
        except asyncio.TimeoutError:
            result = OptimiserResult(
                action_type=ActionType[action.action_kind.name],
                module_name=action.module_name,
                success=False,
                error_msg=f"timeout after {self._cfg.timeout_seconds}s",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        self._counters["actions_executed"] += 1
        if result.success:
            self._counters["actions_succeeded"] += 1
        else:
            self._counters["actions_failed"] += 1
        return result

    async def _dispatch(self, action: ImprovementAction) -> OptimiserResult:
        match action.action_kind.name:
            case "HOT_SWAP_MODULE" | "HOT_SWAP":
                return await self._do_hot_swap(action)
            case "TUNE_THRESHOLD" | "CONFIG_TUNE":
                return await self._do_config_tune(action)
            case "SANDBOX_TEST":
                return await self._do_sandbox_test(action)
            case _:
                return await self._do_noop(action)

    # ------------------------------------------------------------------ #
    # Action handlers                                                      #
    # ------------------------------------------------------------------ #

    async def _do_hot_swap(self, action: ImprovementAction) -> OptimiserResult:
        t0 = time.monotonic()
        params = dict(action.parameters)
        new_version = params.get("new_version", "latest")
        try:
            outcome = await self._orchestrator.orchestrate(
                module_name=action.module_name,
                new_version=new_version,
            )
            return OptimiserResult(
                action_type=ActionType.HOT_SWAP,
                module_name=action.module_name,
                success=outcome.success,
                error_msg=outcome.error_msg if not outcome.success else "",
                duration_ms=(time.monotonic() - t0) * 1000,
                metadata=(("new_version", new_version), ("outcome", str(outcome.state))),
            )
        except Exception as exc:
            return OptimiserResult(
                action_type=ActionType.HOT_SWAP,
                module_name=action.module_name,
                success=False,
                error_msg=str(exc),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    async def _do_config_tune(self, action: ImprovementAction) -> OptimiserResult:
        t0 = time.monotonic()
        params = dict(action.parameters)
        try:
            for key, value in params.items():
                await self._params.set(f"{action.module_name}.{key}", value)
            return OptimiserResult(
                action_type=ActionType.CONFIG_TUNE,
                module_name=action.module_name,
                success=True,
                error_msg="",
                duration_ms=(time.monotonic() - t0) * 1000,
                metadata=tuple(params.items()),
            )
        except Exception as exc:
            return OptimiserResult(
                action_type=ActionType.CONFIG_TUNE,
                module_name=action.module_name,
                success=False,
                error_msg=str(exc),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    async def _do_sandbox_test(self, action: ImprovementAction) -> OptimiserResult:
        t0 = time.monotonic()
        params = dict(action.parameters)
        patch_ref = params.get("patch_ref", "")
        try:
            run = await self._sandbox.run(
                module_name=action.module_name,
                patch_ref=patch_ref,
            )
            return OptimiserResult(
                action_type=ActionType.SANDBOX_TEST,
                module_name=action.module_name,
                success=run.passed,
                error_msg=run.stderr if not run.passed else "",
                duration_ms=(time.monotonic() - t0) * 1000,
                metadata=(("patch_ref", patch_ref), ("exit_code", str(run.exit_code))),
            )
        except Exception as exc:
            return OptimiserResult(
                action_type=ActionType.SANDBOX_TEST,
                module_name=action.module_name,
                success=False,
                error_msg=str(exc),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    async def _do_noop(self, action: ImprovementAction) -> OptimiserResult:
        return OptimiserResult(
            action_type=ActionType.NO_OP,
            module_name=action.module_name,
            success=True,
            error_msg="",
            duration_ms=0.0,
        )
```

---

## `NullSelfOptimiser` — No-op for Testing

```python
class NullSelfOptimiser:
    """Always reports success without calling any downstream system."""

    async def execute(self, action):
        return OptimiserResult(
            action_type=ActionType.NO_OP,
            module_name=action.module_name,
            success=True,
            error_msg="null_optimiser",
            duration_ms=0.0,
        )

    async def execute_batch(self, actions):
        return [await self.execute(a) for a in actions]

    def stats(self):
        return {}

    async def reset(self):
        pass
```

---

## Data Flow — ASCII Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ReflectionCycle (Phase 16.5)                    │
│                                                                     │
│  ┌──────────────────┐  Sequence[ImprovementAction]                  │
│  │ ImprovementPlanner│──────────────────────────────────────────────►│
│  │   (Phase 16.3)   │                                               │
│  └──────────────────┘                                               │
│                                                                     │
│         actions ──────► AsyncSelfOptimiser                          │
│                         │                                           │
│                         │  asyncio.gather(*tasks)                   │
│                         │  ┌──────────────────────────────────────┐ │
│                         │  │  _acquire_token() [token-bucket]     │ │
│                         │  │  asyncio.Semaphore(max_concurrent)   │ │
│                         │  │  asyncio.wait_for(timeout)           │ │
│                         │  │                                      │ │
│                         │  │  match action_kind:                  │ │
│                         │  │  ├─ HOT_SWAP  ──► LiveModuleOrch    │ │
│                         │  │  │              (Phase 15)           │ │
│                         │  │  ├─ CONFIG_TUNE ► ParamRegistry      │ │
│                         │  │  ├─ SANDBOX_TEST► SandboxRunner      │ │
│                         │  │  │              (Phase 14)           │ │
│                         │  │  └─ NO_OP      ► instant return      │ │
│                         │  └──────────────────────────────────────┘ │
│                         │                                           │
│                         │  Sequence[OptimiserResult]                │
│                         └──────────────────────────────────────────►│
│                                                                     │
│  update_baseline()   ◄── WeaknessDetector (Phase 16.2)             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Integration with `ReflectionCycle` (Phase 16.5 Preview)

```python
class ReflectionCycle:
    async def _run_cycle(self) -> None:
        # 1. Profile
        profiles = await self._profiler.get_all_profiles()

        # 2. Detect weaknesses
        weaknesses = await self._detector.detect(profiles)
        if not weaknesses:
            return  # healthy — skip planning & execution

        # 3. Plan
        actions = await self._planner.plan(weaknesses)

        # 4. Optimise (execute actions)
        results = await self._optimiser.execute_batch(actions)

        # 5. Update baseline after acting
        await self._detector.update_baseline(profiles)

        # 6. Log outcomes
        for result in results:
            if not result.success:
                logger.warning(
                    "optimiser action failed",
                    action_type=result.action_type.name,
                    module=result.module_name,
                    error=result.error_msg,
                )
```

### Rate-limit + concurrency interaction

With `max_concurrent_actions=4` and `rate_limit_per_minute=20`:
- At most 4 actions can be in-flight simultaneously (Semaphore).
- No more than 20 action initiations per 60 seconds (token-bucket).
- Timeout of 30 s per action prevents indefinite blocking.

---

## Prometheus Metrics

| Metric name | Type | Labels | Description |
|---|---|---|---|
| `asi_self_optimiser_actions_total` | Counter | `action_type`, `module`, `success` | All executed actions |
| `asi_self_optimiser_action_duration_seconds` | Histogram | `action_type` | Per-action wall-clock time |
| `asi_self_optimiser_rate_limit_wait_seconds` | Histogram | — | Time spent waiting for token-bucket |
| `asi_self_optimiser_semaphore_queue_depth` | Gauge | — | Actions waiting for Semaphore slot |
| `asi_self_optimiser_timeout_total` | Counter | `action_type`, `module` | Actions that exceeded `timeout_seconds` |

### Example PromQL

```promql
# Success rate by action type
sum by (action_type) (rate(asi_self_optimiser_actions_total{success="true"}[5m]))
/
sum by (action_type) (rate(asi_self_optimiser_actions_total[5m]))

# P99 action latency
histogram_quantile(0.99,
  sum by (action_type, le) (
    rate(asi_self_optimiser_action_duration_seconds_bucket[5m])
  )
)
```

### Grafana Alert — High Timeout Rate

```yaml
alert: ASISelfOptimiserTimeouts
expr: |
  rate(asi_self_optimiser_timeout_total[5m]) > 0.1
for: 3m
labels:
  severity: warning
annotations:
  summary: "SelfOptimiser action timeouts elevated"
  description: >
    Module {{ $labels.module }} action {{ $labels.action_type }} timing out.
    Consider increasing timeout_seconds or reducing action concurrency.
```

---

## mypy Type-Check Compatibility

| Expression | Expected type | Notes |
|---|---|---|
| `AsyncSelfOptimiser()` | `SelfOptimiser` | passes `isinstance(x, SelfOptimiser)` |
| `NullSelfOptimiser()` | `SelfOptimiser` | structural subtype via Protocol |
| `result.metadata` | `Tuple[Tuple[str, str], ...]` | hashable; `dict(result.metadata)` to read |
| `result.action_type` | `ActionType` | frozen dataclass — immutable |
| `config.enabled_action_types` | `Tuple[ActionType, ...]` | iterate or convert to set |
| `_acquire_token()` | `Coroutine[None, None, None]` | must be `await`ed |
| `asyncio.wait_for(self._dispatch(action), timeout=...)` | `OptimiserResult` | narrows type after `match` |

Run `mypy --strict asi_build/cognition/self_optimiser.py` — target zero errors.

---

## Test Targets (12)

| # | Test name | What it covers |
|---|---|---|
| 1 | `test_execute_hot_swap_success` | HOT_SWAP → orchestrator called, result.success=True |
| 2 | `test_execute_hot_swap_failure` | orchestrator raises → result.success=False, error_msg set |
| 3 | `test_execute_config_tune` | CONFIG_TUNE → param_registry.set called per param |
| 4 | `test_execute_sandbox_test_pass` | SANDBOX_TEST → sandbox run.passed=True |
| 5 | `test_execute_sandbox_test_fail` | SANDBOX_TEST → sandbox run.passed=False, stderr captured |
| 6 | `test_execute_noop` | NO_OP → no external calls, success=True |
| 7 | `test_dry_run_mode` | dry_run=True → no dispatcher called, success=True, error_msg="dry_run" |
| 8 | `test_disabled_action_type` | action_type not in enabled_action_types → NO_OP result |
| 9 | `test_timeout` | `_dispatch` hangs → `asyncio.TimeoutError` → result.success=False |
| 10 | `test_execute_batch_concurrency` | 8 actions with Semaphore(4) — at most 4 in-flight simultaneously |
| 11 | `test_rate_limit_token_bucket` | burst > rate_limit_per_minute → wait observed |
| 12 | `test_null_optimiser_protocol` | `isinstance(NullSelfOptimiser(), SelfOptimiser)` is True |

### Skeleton — `test_execute_batch_concurrency`

```python
import asyncio
import pytest

@pytest.mark.asyncio
async def test_execute_batch_concurrency():
    max_concurrent = 4
    in_flight = 0
    peak = 0

    async def fake_hot_swap(**kwargs):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.05)
        in_flight -= 1
        return FakeOutcome(success=True, state="ACTIVE", error_msg="")

    mock_orch = AsyncMock()
    mock_orch.orchestrate = fake_hot_swap

    cfg = OptimiserConfig(max_concurrent_actions=max_concurrent)
    optimiser = AsyncSelfOptimiser(config=cfg, orchestrator=mock_orch)
    actions = [make_hot_swap_action(f"mod_{i}") for i in range(8)]

    await optimiser.execute_batch(actions)
    assert peak <= max_concurrent
```

### Skeleton — `test_timeout`

```python
@pytest.mark.asyncio
async def test_timeout():
    async def slow_swap(**kwargs):
        await asyncio.sleep(999)

    mock_orch = AsyncMock()
    mock_orch.orchestrate = slow_swap

    cfg = OptimiserConfig(timeout_seconds=0.05)
    optimiser = AsyncSelfOptimiser(config=cfg, orchestrator=mock_orch)
    result = await optimiser.execute(make_hot_swap_action("slow_mod"))

    assert result.success is False
    assert "timeout" in result.error_msg
```

---

## 14-Step Implementation Order

1. Add `ActionType` enum to `asi_build/cognition/enums.py`
2. Add `OptimiserResult` frozen dataclass to `asi_build/cognition/profiles.py`
3. Add `OptimiserConfig` frozen dataclass (same file, or `configs.py`)
4. Implement `SelfOptimiser` Protocol with `@runtime_checkable`
5. Implement `AsyncSelfOptimiser.__init__()` — Semaphore + token-bucket state
6. Implement `_acquire_token()` — monotonic refill + sleep
7. Implement `_do_noop()` — trivial base case
8. Implement `_do_config_tune()` — param_registry integration
9. Implement `_do_sandbox_test()` — Phase 14 SandboxRunner integration
10. Implement `_do_hot_swap()` — Phase 15 LiveModuleOrchestrator integration
11. Implement `_dispatch()` — `match` on `action_kind.name`
12. Implement `_execute_single()` — dry_run gate + `wait_for` timeout wrapper
13. Implement `execute()` and `execute_batch()` — token acquire + Semaphore
14. Wire Prometheus metrics, `NullSelfOptimiser`, and write 12 tests

---

## Phase 16 Sub-Phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 16.1 | `PerformanceProfiler` | #417 | 🟡 Open |
| 16.2 | `WeaknessDetector` | #420 | 🟡 Open |
| 16.3 | `ImprovementPlanner` | #423 | 🟡 Open |
| 16.4 | `SelfOptimiser` | #426 | 🟡 Open |
| 16.5 | `ReflectionCycle` | #429 | ⏳ Planned |
