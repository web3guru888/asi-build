# Phase 15.2 — HotSwapper: Zero-Downtime Live Module Replacement

**Phase 15** — Runtime Self-Modification | **Sub-phase 15.2**

---

## Overview

`HotSwapper` performs **live, zero-downtime replacement** of cognitive modules within a running `CognitiveCycle`. It consumes `ModuleRegistry` (Phase 15.1) to discover staged versions, acquires per-module locks to serialise concurrent swaps of the same module while allowing parallel swaps of different modules, executes the swap atomically, and rolls back automatically on failure.

HotSwapper is the execution engine that makes self-modification operational: `ModuleRegistry` tracks *what* is available; `HotSwapper` decides *when* and *how* to apply it with safety guarantees.

---

## Data Model

```python
from __future__ import annotations
from dataclasses import dataclass, field
import enum
from typing import Any

class SwapPhase(enum.Enum):
    """Lifecycle stages of a single swap attempt."""
    PENDING     = "pending"
    VALIDATING  = "validating"
    SWAPPING    = "swapping"
    VERIFYING   = "verifying"
    COMMITTED   = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED      = "failed"

@dataclass(frozen=True)
class SwapRequest:
    """Caller-supplied intent to swap a module to a target version."""
    module_name:    str
    target_version: int                     # must exist in ModuleRegistry
    initiator:      str = "CognitiveCycle"  # who triggered the swap
    timeout_s:      float = 10.0            # max seconds for the full swap

@dataclass(frozen=True)
class SwapResult:
    """Outcome record produced after each swap attempt."""
    module_name:      str
    from_version:     int
    to_version:       int
    phase:            SwapPhase             # terminal phase only
    duration_s:       float
    error:            str | None = None     # set on ROLLED_BACK / FAILED

@dataclass(frozen=True)
class SwapperConfig:
    """Static configuration for HotSwapper."""
    max_concurrent_modules: int   = 8      # parallel swaps of *different* modules
    validation_timeout_s:   float = 2.0    # per-module pre-swap validation budget
    verification_timeout_s: float = 3.0    # post-swap health-check budget
    rollback_on_verify_fail: bool = True   # auto-rollback when verify fails
    emit_audit_events:       bool = True   # push swap lifecycle to SynthesisAudit
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class HotSwapper(Protocol):
    """Zero-downtime module replacement contract."""

    async def swap(self, request: SwapRequest) -> SwapResult:
        """
        Execute a single module swap end-to-end.

        Lifecycle:
          PENDING -> VALIDATING -> SWAPPING -> VERIFYING -> COMMITTED
                                                         \-> ROLLED_BACK (on verify failure)
        Any unhandled exception -> FAILED (no rollback possible).
        """
        ...

    async def swap_batch(
        self, requests: list[SwapRequest]
    ) -> list[SwapResult]:
        """
        Swap multiple modules concurrently (different modules in parallel,
        same module serialised).  Partial failure is acceptable.
        """
        ...

    def stats(self) -> dict[str, Any]:
        """Return cumulative counters: attempted / committed / rolled_back / failed."""
        ...

    def reset(self) -> None:
        """Clear all counters and per-module locks (test helper)."""
        ...
```

---

## Reference Implementation — `AsyncHotSwapper`

```python
import asyncio, time, logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

class AsyncHotSwapper:
    """
    Production HotSwapper implementation.

    Thread-safety model
    -------------------
    * One asyncio.Lock per module name  ->  serialises concurrent swaps of the same module.
    * A shared asyncio.Semaphore(max_concurrent_modules)  ->  caps total parallel swaps.
    """

    def __init__(self, registry, cycle, config=None):
        self._registry = registry
        self._cycle    = cycle
        self._cfg      = config or SwapperConfig()
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._sem   = asyncio.Semaphore(self._cfg.max_concurrent_modules)
        self._counters = {"attempted": 0, "committed": 0, "rolled_back": 0, "failed": 0}

    async def swap(self, request: SwapRequest) -> SwapResult:
        self._counters["attempted"] += 1
        t0 = time.monotonic()
        async with self._locks[request.module_name]:
            try:
                result = await asyncio.wait_for(
                    self._do_swap(request, t0), timeout=request.timeout_s
                )
            except asyncio.TimeoutError:
                self._counters["failed"] += 1
                return SwapResult(
                    module_name=request.module_name, from_version=-1,
                    to_version=request.target_version, phase=SwapPhase.FAILED,
                    duration_s=time.monotonic()-t0,
                    error=f"Swap timed out after {request.timeout_s}s",
                )
            except Exception as exc:
                self._counters["failed"] += 1
                return SwapResult(
                    module_name=request.module_name, from_version=-1,
                    to_version=request.target_version, phase=SwapPhase.FAILED,
                    duration_s=time.monotonic()-t0, error=str(exc),
                )
        if result.phase == SwapPhase.COMMITTED:
            self._counters["committed"] += 1
        elif result.phase == SwapPhase.ROLLED_BACK:
            self._counters["rolled_back"] += 1
        else:
            self._counters["failed"] += 1
        return result

    async def swap_batch(self, requests):
        async def _guarded(req):
            async with self._sem:
                return await self.swap(req)
        return list(await asyncio.gather(*(_guarded(r) for r in requests)))

    def stats(self): return dict(self._counters)
    def reset(self):
        self._counters = {k: 0 for k in self._counters}
        self._locks.clear()

    async def _do_swap(self, request, t0):
        name, target_ver = request.module_name, request.target_version
        active   = self._registry.get_active(name)
        from_ver = active.version if active else 0

        # VALIDATING
        await asyncio.wait_for(self._validate(name, target_ver),
                               timeout=self._cfg.validation_timeout_s)

        # SWAPPING
        old_impl = self._cycle.get_module(name)
        new_ver  = self._registry.get_version(name, target_ver)
        self._cycle.set_module(name, new_ver.implementation)

        # VERIFYING
        try:
            await asyncio.wait_for(self._verify(name, new_ver.implementation),
                                   timeout=self._cfg.verification_timeout_s)
        except Exception as err:
            if self._cfg.rollback_on_verify_fail:
                self._cycle.set_module(name, old_impl)
                self._registry.set_status(name, target_ver, "REVERTED")
                return SwapResult(module_name=name, from_version=from_ver,
                                  to_version=target_ver, phase=SwapPhase.ROLLED_BACK,
                                  duration_s=time.monotonic()-t0, error=str(err))
            raise

        # COMMITTED
        self._registry.set_status(name, target_ver, "ACTIVE")
        if from_ver:
            self._registry.set_status(name, from_ver, "ARCHIVED")
        return SwapResult(module_name=name, from_version=from_ver,
                          to_version=target_ver, phase=SwapPhase.COMMITTED,
                          duration_s=time.monotonic()-t0)

    async def _validate(self, name, target_ver):
        ver = self._registry.get_version(name, target_ver)
        if ver is None:
            raise ValueError(f"Module {name!r} v{target_ver} not found in registry")
        if ver.status.value != "STAGED":
            raise ValueError(f"Module {name!r} v{target_ver} has status {ver.status!r}; "
                             "only STAGED versions may be swapped in")

    async def _verify(self, name, impl):
        if hasattr(impl, "health_check") and asyncio.iscoroutinefunction(impl.health_check):
            await impl.health_check()
```

---

## CognitiveCycle Integration

```python
class CognitiveCycle:
    def __init__(self, ..., swapper: HotSwapper | None = None) -> None:
        ...
        self._swapper = swapper or AsyncHotSwapper(self._registry, self)

    def get_module(self, name: str):
        return self._modules[name]

    def set_module(self, name: str, impl) -> None:
        """Atomic reference replacement — GIL sufficient for dict write."""
        self._modules[name] = impl

    async def _synthesis_step(self) -> None:
        # ... CodeSynthesiser -> SandboxRunner -> TestHarness -> PatchSelector ...
        patch = self._selector.select(candidates)
        if patch:
            version = self._registry.register(
                module_name=patch.module_name,
                implementation=patch.implementation,
                metadata={"source": "synthesis"},
            )
            result = await self._swapper.swap(
                SwapRequest(module_name=patch.module_name,
                            target_version=version.version)
            )
            if result.phase == SwapPhase.COMMITTED:
                self._audit.append(AuditRecord(event_type=AuditEventType.PATCH_APPLIED, ...))
            elif result.phase == SwapPhase.ROLLED_BACK:
                logger.warning("Swap rolled back: %s", result.error)
```

---

## Data-Flow Diagram

```
CognitiveCycle._synthesis_step()
          |
          v
   ModuleRegistry.register()  -->  STAGED version
          |
          v
   HotSwapper.swap(SwapRequest)
          |
    +-----+------------------+
    |  per-module Lock        |
    |  + global Semaphore     |
    +-----+------------------+
          |
    +-----v-----+
    | VALIDATING|  registry.get_version -> must be STAGED
    +-----+-----+
          | OK
    +-----v-----+
    |  SWAPPING |  cycle.set_module(name, new_impl)
    +-----+-----+
          |
    +-----v------+
    | VERIFYING  |  impl.health_check() [if exists]
    +-----+------+
         / \
       OK   FAIL
       |      |
       |   rollback: cycle.set_module(old_impl)
       |         registry.set_status -> REVERTED
       |
    +--v------+
    |COMMITTED|  registry.set_status -> ACTIVE
    +---------+  old version -> ARCHIVED
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_hot_swapper_swaps_total` | Counter | `module`, `phase` | Swap attempts by terminal phase |
| `asi_hot_swapper_duration_seconds` | Histogram | `module` | End-to-end swap latency |
| `asi_hot_swapper_rollbacks_total` | Counter | `module` | Rolled-back swaps (verify failures) |
| `asi_hot_swapper_concurrent` | Gauge | — | Active concurrent swaps right now |
| `asi_hot_swapper_timeout_total` | Counter | `module` | Swaps aborted by timeout |

### PromQL Alerts

```yaml
# Rollback rate > 10% over 5 min
- alert: HighSwapRollbackRate
  expr: |
    rate(asi_hot_swapper_swaps_total{phase="rolled_back"}[5m])
    / rate(asi_hot_swapper_swaps_total[5m]) > 0.10
  for: 2m
  labels: { severity: warning }
  annotations:
    summary: "HotSwapper rollback rate {{ $value | humanizePercentage }}"

# p99 swap latency > 8s
- alert: SlowSwapLatency
  expr: histogram_quantile(0.99, rate(asi_hot_swapper_duration_seconds_bucket[5m])) > 8
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "HotSwapper p99 latency {{ $value }}s"
```

---

## Static-Analysis Contract (mypy strict)

| Symbol | Return | Notes |
|--------|--------|-------|
| `AsyncHotSwapper.swap` | `Coroutine[Any, Any, SwapResult]` | `await`-able |
| `AsyncHotSwapper.swap_batch` | `Coroutine[Any, Any, list[SwapResult]]` | parallel gather |
| `AsyncHotSwapper.stats` | `dict[str, Any]` | counters only |
| `SwapRequest` | frozen dataclass | `eq=True, frozen=True` |
| `SwapResult` | frozen dataclass | `error: str \| None` |
| `SwapperConfig` | frozen dataclass | all fields typed |
| `SwapPhase` | `enum.Enum` | 7 lifecycle values |

---

## Test Targets

```
tests/phase15/test_hot_swapper.py
├── test_swap_committed_happy_path          # STAGED -> COMMITTED, registry updates
├── test_swap_rolled_back_on_verify_fail    # verify raises -> ROLLED_BACK, old impl restored
├── test_swap_failed_on_timeout             # asyncio.wait_for times out -> FAILED
├── test_swap_failed_non_staged_version     # ACTIVE version rejected in VALIDATING
├── test_swap_batch_concurrent_different    # 4 different modules swap concurrently
├── test_swap_batch_serialised_same_module  # 2 swaps of same module run sequentially
├── test_semaphore_max_concurrency          # semaphore caps parallel swaps
├── test_rollback_restores_old_impl         # cycle.get_module() returns old after rollback
├── test_stats_counters_increment           # attempted/committed/rolled_back/failed track correctly
├── test_reset_clears_counters              # reset() zeroes counters + clears locks
├── test_health_check_called_when_present   # _verify calls impl.health_check()
├── test_health_check_skipped_when_absent   # _verify safe when health_check not defined
```

---

## Implementation Order

1. Add `SwapPhase`, `SwapRequest`, `SwapResult`, `SwapperConfig` frozen dataclasses
2. Define `HotSwapper` Protocol (`@runtime_checkable`)
3. Stub `AsyncHotSwapper.__init__` with `defaultdict(asyncio.Lock)` + `Semaphore`
4. Implement `_validate` (registry STAGED check)
5. Implement `_do_swap` SWAPPING step (cycle reference swap)
6. Implement `_verify` (duck-type health_check)
7. Wire rollback path in `_do_swap`
8. Implement `swap` with `asyncio.wait_for` + timeout handling
9. Implement `swap_batch` using `asyncio.gather` + semaphore guard
10. Add Prometheus metrics (`Counter`, `Histogram`, `Gauge`)
11. Add `stats()` and `reset()` helpers
12. Wire into `CognitiveCycle._synthesis_step()`
13. Write 12 test targets
14. `mypy --strict` — zero errors

---

## Phase 15 Sub-phase Tracker

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 15.1 | ModuleRegistry | #401 | In Progress |
| 15.2 | HotSwapper | #402 | In Progress |
| 15.3 | RollbackManager | — | Planned |
| 15.4 | VersionDiffer | — | Planned |
| 15.5 | SelfModAudit | — | Planned |

---

## Phase 14 -> 15 Integration

| Phase 14 Component | Feeds into Phase 15 |
|--------------------|---------------------|
| PatchSelector (14.4) | SwapRequest.module_name / target_version |
| SynthesisAudit (14.5) | PATCH_APPLIED / SWAP_ROLLED_BACK events |
| ModuleRegistry (15.1) | Version discovery + status transitions |
| HotSwapper (15.2) | Live replacement + rollback |

---

*Part of the ASI-Build wiki - Phase 15: Runtime Self-Modification*
