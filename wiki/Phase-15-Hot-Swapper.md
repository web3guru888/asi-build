# Phase 15.2 — `HotSwapper`: zero-downtime live module replacement

**Issue**: #402 | **Phase**: 15 — Runtime Self-Modification & Hot-Reload Architecture

---

## Overview

`HotSwapper` is the Phase 15.2 component that performs live, zero-downtime replacement of cognitive modules within a running `CognitiveCycle`. It consumes `ModuleRegistry` (Phase 15.1) to discover staged versions and executes each swap atomically — committing on successful validation or reverting on failure — without interrupting ongoing cognition.

---

## Enumerations

```python
import enum

class SwapResult(enum.Enum):
    SUCCESS  = "success"   # module replaced and validated
    ROLLBACK = "rollback"  # swap attempted, validation failed, reverted
    SKIPPED  = "skipped"   # no staged version available
    ERROR    = "error"     # unexpected exception or timeout during swap
```

---

## Frozen Dataclasses

```python
import dataclasses

@dataclasses.dataclass(frozen=True)
class SwapEvent:
    module_name:  str
    from_version: int          # 0 if no prior ACTIVE version
    to_version:   int          # 0 if SKIPPED
    result:       SwapResult
    duration_ms:  float
    error:        str | None = None

@dataclasses.dataclass(frozen=True)
class SwapConfig:
    validation_timeout_s:  float = 5.0   # max seconds for validator
    max_rollback_attempts: int   = 3     # retry rollback if registry write fails
    emit_audit_event:      bool  = True  # forward SwapEvent to SynthesisAudit
```

---

## Protocol

```python
from typing import Any, Callable, Protocol, runtime_checkable

@runtime_checkable
class HotSwapper(Protocol):
    async def swap(
        self,
        module_name: str,
        loader:    Callable[[int], Any],
        validator: Callable[[Any], bool],
    ) -> SwapEvent:
        """Atomically replace the live module with its staged version."""
        ...

    async def swap_all_staged(
        self,
        loader:    Callable[[str, int], Any],
        validator: Callable[[str, Any], bool],
    ) -> list[SwapEvent]:
        """Iterate over all STAGED modules and attempt a swap for each."""
        ...

    def last_event(self, module_name: str) -> SwapEvent | None: ...
    def stats(self) -> dict[str, int]: ...
```

---

## Reference Implementation: `LiveHotSwapper`

```python
import asyncio
import logging
import time
from collections import Counter
from typing import Any, Callable

logger = logging.getLogger(__name__)


class LiveHotSwapper:
    """Thread-safe, asyncio-native hot-swapper backed by ModuleRegistry."""

    def __init__(self, registry: ModuleRegistry, config: SwapConfig | None = None) -> None:
        self._registry = registry
        self._cfg      = config or SwapConfig()
        self._locks:   dict[str, asyncio.Lock] = {}
        self._history: dict[str, SwapEvent]    = {}
        self._swaps_total   = _counter("asi_hotswapper_swaps_total",   ["module", "result"])
        self._swap_duration = _histogram("asi_hotswapper_swap_duration_seconds", ["module"])
        self._rollbacks     = _counter("asi_hotswapper_rollbacks_total", ["module"])

    def _lock_for(self, name: str) -> asyncio.Lock:
        if name not in self._locks:
            self._locks[name] = asyncio.Lock()
        return self._locks[name]

    async def swap(
        self,
        module_name: str,
        loader:    Callable[[int], Any],
        validator: Callable[[Any], bool],
    ) -> SwapEvent:
        async with self._lock_for(module_name):
            staged = self._registry.latest_staged(module_name)
            if staged is None:
                event = SwapEvent(
                    module_name=module_name, from_version=0,
                    to_version=0, result=SwapResult.SKIPPED, duration_ms=0.0,
                )
                self._history[module_name] = event
                return event

            from_ver = self._registry.latest_version(module_name, status=ModuleStatus.ACTIVE)
            t0 = time.monotonic()
            try:
                new_obj = loader(staged.version)
                valid = await asyncio.wait_for(
                    asyncio.get_running_loop().run_in_executor(None, validator, new_obj),
                    timeout=self._cfg.validation_timeout_s,
                )
                if valid:
                    self._registry.set_status(module_name, staged.version, ModuleStatus.ACTIVE)
                    if from_ver:
                        self._registry.set_status(module_name, from_ver, ModuleStatus.ARCHIVED)
                    result, error = SwapResult.SUCCESS, None
                else:
                    self._registry.set_status(module_name, staged.version, ModuleStatus.REVERTED)
                    result, error = SwapResult.ROLLBACK, "validator returned False"
                    self._rollbacks.labels(module=module_name).inc()
            except Exception as exc:
                self._registry.set_status(module_name, staged.version, ModuleStatus.REVERTED)
                result, error = SwapResult.ERROR, str(exc)
                logger.exception("HotSwapper error on %s v%d", module_name, staged.version)

            duration_ms = (time.monotonic() - t0) * 1000
            event = SwapEvent(
                module_name=module_name, from_version=from_ver or 0,
                to_version=staged.version, result=result,
                duration_ms=duration_ms, error=error,
            )
            self._history[module_name] = event
            self._swaps_total.labels(module=module_name, result=result.value).inc()
            self._swap_duration.labels(module=module_name).observe(duration_ms / 1000)
            return event

    async def swap_all_staged(
        self,
        loader:    Callable[[str, int], Any],
        validator: Callable[[str, Any], bool],
    ) -> list[SwapEvent]:
        staged_modules = self._registry.list_staged_modules()
        tasks = [
            self.swap(
                name,
                lambda v, n=name: loader(n, v),
                lambda obj, n=name: validator(n, obj),
            )
            for name in staged_modules
        ]
        return list(await asyncio.gather(*tasks))

    def last_event(self, module_name: str) -> SwapEvent | None:
        return self._history.get(module_name)

    def stats(self) -> dict[str, int]:
        c: Counter[str] = Counter()
        for ev in self._history.values():
            c[ev.result.value] += 1
        return dict(c)
```

---

## `ModuleRegistry` Extensions (15.1 → 15.2)

`HotSwapper` requires two additional methods on `ModuleRegistry`:

```python
def latest_staged(self, module_name: str) -> ModuleVersion | None:
    """Return the highest-version STAGED entry, or None."""
    staged = self.list_versions(module_name, status=ModuleStatus.STAGED)
    return staged[-1] if staged else None

def list_staged_modules(self) -> list[str]:
    """Return names of all modules that have at least one STAGED version."""
    return [
        name for name, versions in self._store.items()
        if any(v.status == ModuleStatus.STAGED for v in versions.values())
    ]
```

---

## `CognitiveCycle` Integration

```python
class CognitiveCycle:
    def __init__(self, ..., swapper: HotSwapper | None = None) -> None:
        ...
        self._swapper = swapper

    async def _synthesis_step(self) -> None:
        # Phase 14: synthesise → sandbox → harness → selector → audit
        # Phase 15.1: registry.register(status=STAGED)
        if self._swapper:
            events = await self._swapper.swap_all_staged(
                loader=self._load_module,
                validator=self._validate_module,
            )
            for ev in events:
                logger.info(
                    "HotSwap %s v%d→v%d: %s",
                    ev.module_name, ev.from_version, ev.to_version, ev.result.value,
                )

    def _load_module(self, module_name: str, version: int) -> Any:
        """Load compiled module artifact for the given version."""
        # Implementation: importlib.import_module / pickle / torch.load / etc.
        ...

    def _validate_module(self, module_name: str, module_obj: Any) -> bool:
        """Run a fast smoke test against the loaded module."""
        ...
```

---

## Data-Flow Diagram

```
SynthesisAudit (Phase 14.5)
        │  PATCH_APPLIED event
        ▼
ModuleRegistry.register(status=STAGED)   ◄── Phase 15.1
        │
        │  list_staged_modules()
        ▼
HotSwapper.swap_all_staged()             ◄── Phase 15.2
        │
        ├── loader(name, version)  →  new_obj
        ├── asyncio.wait_for(validator(new_obj), timeout)
        │
        ├─[valid]──► set_status(ACTIVE)  /  old→ARCHIVED
        └─[invalid]─► set_status(REVERTED)
```

---

## SwapResult Decision Tree

```
latest_staged() → None?
    YES → SwapResult.SKIPPED

loader() raises?
    YES → REVERTED + SwapResult.ERROR

validator times out?
    YES → REVERTED + SwapResult.ERROR

validator() → False?
    YES → REVERTED + SwapResult.ROLLBACK

validator() → True
    → ACTIVE + old→ARCHIVED + SwapResult.SUCCESS
```

---

## Prometheus Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `asi_hotswapper_swaps_total` | Counter | `module`, `result` |
| `asi_hotswapper_swap_duration_seconds` | Histogram | `module` |
| `asi_hotswapper_active_modules` | Gauge | `module` |
| `asi_hotswapper_staged_queue_depth` | Gauge | — |
| `asi_hotswapper_rollbacks_total` | Counter | `module` |

### Example PromQL

```promql
# Success rate (5 min window)
rate(asi_hotswapper_swaps_total{result="success"}[5m])
  / rate(asi_hotswapper_swaps_total[5m])

# P95 swap latency
histogram_quantile(0.95, rate(asi_hotswapper_swap_duration_seconds_bucket[5m]))
```

### Grafana Alert

```yaml
- alert: HotSwapHighRollbackRate
  expr: |
    rate(asi_hotswapper_rollbacks_total[10m])
    / rate(asi_hotswapper_swaps_total[10m]) > 0.3
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "Hot-swap rollback rate > 30%"
    description: "Module {{ $labels.module }} is failing validation frequently."
```

---

## Validation Timeout Guide

| Workload type | Recommended `validation_timeout_s` |
|---------------|--------------------------------------|
| Unit smoke test | 2–5 s |
| Integration test (DB) | 10–30 s |
| Full benchmark suite | 60–120 s |

---

## Type-Safety Table

| Symbol | mypy annotation | `isinstance` check |
|--------|-----------------|---------------------|
| `HotSwapper` | `Protocol` | ✅ (runtime_checkable) |
| `SwapConfig` | `frozen dataclass` | ✅ |
| `SwapEvent` | `frozen dataclass` | ✅ |
| `SwapResult` | `str Enum` | ✅ |
| `loader` | `Callable[[int], Any]` | — |
| `validator` | `Callable[[Any], bool]` | — |

---

## Test Targets (12)

1. `test_swap_success` — loader+validator both succeed → ACTIVE, old → ARCHIVED
2. `test_swap_rollback` — validator returns False → REVERTED, SwapResult.ROLLBACK
3. `test_swap_error` — loader raises → REVERTED, SwapResult.ERROR
4. `test_swap_skipped` — no STAGED version → SwapResult.SKIPPED
5. `test_swap_timeout` — validator times out → SwapResult.ERROR
6. `test_swap_all_staged` — multiple staged modules → correct events list
7. `test_concurrent_swap_serialised` — asyncio.gather on same module → serialised via lock
8. `test_last_event_history` — history populated correctly per module
9. `test_stats_counter` — stats() reflects outcome distribution
10. `test_registry_integration_e2e` — register STAGED → swap → ACTIVE (real registry)
11. `test_no_swapper_noop` — swapper=None in CognitiveCycle is a no-op
12. `test_prometheus_labels` — metrics emitted with correct module+result labels

### Test Skeleton — concurrent swap serialisation

```python
import asyncio, pytest

@pytest.mark.asyncio
async def test_concurrent_swap_serialised():
    registry = InMemoryModuleRegistry()
    registry.register(ModuleVersion("planner", 1, b"x" * 32, ModuleStatus.STAGED))

    swapper = LiveHotSwapper(registry)
    # Launch 5 concurrent swaps for the same module
    events = await asyncio.gather(*[
        swapper.swap("planner", lambda v: object(), lambda _: True)
        for _ in range(5)
    ])
    successes = [e for e in events if e.result == SwapResult.SUCCESS]
    skipped   = [e for e in events if e.result == SwapResult.SKIPPED]
    assert len(successes) == 1
    assert len(skipped)   == 4
```

---

## Implementation Order (14 steps)

1. Add `latest_staged()` and `list_staged_modules()` to `InMemoryModuleRegistry` (Phase 15.1 extension)
2. Define `SwapResult` enum
3. Define `SwapEvent` frozen dataclass
4. Define `SwapConfig` frozen dataclass
5. Define `HotSwapper` Protocol (`@runtime_checkable`)
6. Implement `LiveHotSwapper.__init__()` — lock dict + Prometheus helpers
7. Implement `LiveHotSwapper._lock_for()` — lazy per-module lock creation
8. Implement `LiveHotSwapper.swap()` — lock acquire → staged lookup → load → validate → commit/revert
9. Implement `LiveHotSwapper.swap_all_staged()` — gather over staged modules
10. Implement `last_event()` and `stats()` accessors
11. Wire `HotSwapper` into `CognitiveCycle._synthesis_step()`
12. Add `_load_module()` and `_validate_module()` stub hooks to `CognitiveCycle`
13. Register Prometheus metrics (Counter + Histogram + Gauge)
14. Write unit tests (mock registry + mock loader/validator)

---

## Phase 15 Sub-Phase Tracker

| Sub-phase | Component | Issue | Wiki | Status |
|-----------|-----------|-------|------|--------|
| 15.1 | ModuleRegistry | #401 | [Phase-15-Module-Registry](Phase-15-Module-Registry) | 🟡 open |
| 15.2 | HotSwapper | #402 | [this page](Phase-15-Hot-Swapper) | 🟡 open |
| 15.3 | RollbackCoordinator | — | — | ⏳ |
| 15.4 | CapabilityIndex | — | — | ⏳ |
| 15.5 | SelfModificationAudit | — | — | ⏳ |

---

*Part of the Phase 15 — Runtime Self-Modification & Hot-Reload Architecture track.*
