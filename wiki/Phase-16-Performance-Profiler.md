# Phase 16.1 — PerformanceProfiler

**Phase**: 16 — Cognitive Reflection & Self-Improvement
**Issue**: [#417](https://github.com/web3guru888/asi-build/issues/417)
**Show & Tell**: [#418](https://github.com/web3guru888/asi-build/discussions/418)
**Q&A**: [#419](https://github.com/web3guru888/asi-build/discussions/419)

---

## Overview

`PerformanceProfiler` is the **observability backbone** of Phase 16. It transparently instruments every cognitive module through `CognitiveCycle._run_module()`, maintaining per-module sliding-window statistics that drive the self-improvement pipeline.

**Responsibility**: Record per-call latency, throughput, and error rates for each cognitive module; expose `ModuleProfile` snapshots consumed by `WeaknessDetector` (Phase 16.2).

---

## Enums

### `ProfilerGranularity`

```python
class ProfilerGranularity(Enum):
    MODULE   = auto()   # one sample per module invocation (default)
    METHOD   = auto()   # one sample per async def call
    PIPELINE = auto()   # aggregate across full CognitiveCycle pass
```

| Value | Scope | Use case |
|---|---|---|
| `MODULE` | Per module invocation | Coarse-grained health monitoring |
| `METHOD` | Per `async def` | Hotspot detection within modules |
| `PIPELINE` | Full CognitiveCycle pass | End-to-end latency budgeting |

---

## Frozen Dataclasses

### `LatencyBucket`

```python
@dataclass(frozen=True)
class LatencyBucket:
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
```

### `ModuleProfile`

```python
@dataclass(frozen=True)
class ModuleProfile:
    module_id: str
    window_start: float          # time.monotonic() of earliest sample in window
    window_end: float            # time.monotonic() of latest sample in window
    call_count: int
    error_count: int
    throughput_rps: float
    latency: LatencyBucket
    tags: frozenset[str] = field(default_factory=frozenset)
```

### `ProfilerConfig`

```python
@dataclass(frozen=True)
class ProfilerConfig:
    granularity: ProfilerGranularity = ProfilerGranularity.MODULE
    window_seconds: float = 60.0   # sliding window duration
    max_samples: int = 10_000      # per-module deque cap
    export_prometheus: bool = True

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.max_samples < 1:
            raise ValueError("max_samples must be >= 1")
```

---

## Protocol

```python
@runtime_checkable
class PerformanceProfiler(Protocol):
    async def record(
        self,
        module_id: str,
        duration_ms: float,
        *,
        error: bool = False,
        tags: frozenset[str] = frozenset(),
    ) -> None: ...

    async def get_profile(self, module_id: str) -> ModuleProfile | None: ...
    async def list_profiles(self) -> Sequence[ModuleProfile]: ...
    async def flush(self) -> None: ...
    async def reset(self, module_id: str | None = None) -> None: ...
    def stats(self) -> dict[str, int]: ...
```

---

## Reference Implementation: `SlidingWindowProfiler`

```python
import asyncio, collections, math, time
from collections import defaultdict

class SlidingWindowProfiler:
    """
    Per-module sliding-window latency profiler.

    Storage:   deque(maxlen=max_samples) of (monotonic_ts, duration_ms)
    Locking:   per-module asyncio.Lock — no global contention
    Percentile: nearest-rank method over sorted window samples
    """

    def __init__(self, config: ProfilerConfig | None = None) -> None:
        self._cfg = config or ProfilerConfig()
        self._locks:  defaultdict[str, asyncio.Lock]  = defaultdict(asyncio.Lock)
        self._samples: defaultdict[str, collections.deque] = \
            defaultdict(lambda: collections.deque(maxlen=self._cfg.max_samples))
        self._errors:       defaultdict[str, int] = defaultdict(int)
        self._total_calls:  defaultdict[str, int] = defaultdict(int)

    # ------------------------------------------------------------------ record

    async def record(
        self,
        module_id: str,
        duration_ms: float,
        *,
        error: bool = False,
        tags: frozenset[str] = frozenset(),
    ) -> None:
        async with self._locks[module_id]:
            self._samples[module_id].append((time.monotonic(), duration_ms))
            self._total_calls[module_id] += 1
            if error:
                self._errors[module_id] += 1

    # --------------------------------------------------------------- get/list

    async def get_profile(self, module_id: str) -> ModuleProfile | None:
        async with self._locks[module_id]:
            return self._compute_profile(module_id)

    async def list_profiles(self) -> list[ModuleProfile]:
        profiles: list[ModuleProfile] = []
        for mid in list(self._samples):
            async with self._locks[mid]:
                p = self._compute_profile(mid)
                if p is not None:
                    profiles.append(p)
        return profiles

    # -------------------------------------------------------- _compute_profile

    def _compute_profile(self, module_id: str) -> ModuleProfile | None:
        """Called under self._locks[module_id] — sync, no await."""
        raw = list(self._samples[module_id])
        if not raw:
            return None
        cutoff = time.monotonic() - self._cfg.window_seconds
        window = [(t, d) for t, d in raw if t >= cutoff]
        if not window:
            return None
        durations = sorted(d for _, d in window)
        n = len(durations)

        def pct(p: float) -> float:
            idx = max(0, min(n - 1, math.ceil(p / 100 * n) - 1))
            return durations[idx]

        span = window[-1][0] - window[0][0]
        return ModuleProfile(
            module_id=module_id,
            window_start=window[0][0],
            window_end=window[-1][0],
            call_count=n,
            error_count=self._errors[module_id],
            throughput_rps=n / max(span, 1e-9),
            latency=LatencyBucket(
                p50_ms=pct(50), p95_ms=pct(95),
                p99_ms=pct(99), max_ms=max(durations),
            ),
        )

    # ------------------------------------------------------------------ flush

    async def flush(self) -> None:
        """Physically evict samples older than window_seconds."""
        for mid in list(self._samples):
            async with self._locks[mid]:
                cutoff = time.monotonic() - self._cfg.window_seconds
                dq = self._samples[mid]
                while dq and dq[0][0] < cutoff:
                    dq.popleft()

    # ------------------------------------------------------------------ reset

    async def reset(self, module_id: str | None = None) -> None:
        mids = [module_id] if module_id else list(self._samples)
        for mid in mids:
            async with self._locks[mid]:
                self._samples[mid].clear()
                self._errors[mid] = 0
                self._total_calls[mid] = 0

    # ------------------------------------------------------------------ stats

    def stats(self) -> dict[str, int]:
        return {
            "tracked_modules": len(self._samples),
            "total_samples":   sum(len(v) for v in self._samples.values()),
            "total_errors":    sum(self._errors.values()),
        }


def make_profiler(config: ProfilerConfig | None = None) -> PerformanceProfiler:
    return SlidingWindowProfiler(config)
```

---

## `NullProfiler` (for unit tests)

```python
class NullProfiler:
    """Drop-in no-op profiler for tests that don't care about profiling."""
    async def record(self, *a, **kw): pass
    async def get_profile(self, _): return None
    async def list_profiles(self): return []
    async def flush(self): pass
    async def reset(self, *a): pass
    def stats(self): return {}
```

---

## Data Flow

```
CognitiveCycle._run_module(module_id, ...)
  │
  ├── start = time.monotonic()
  ├── await self.get_module(module_id).run(...)
  └── [finally]
       └── profiler.record(module_id, duration_ms, error=error)
                    │
                    ▼
         SlidingWindowProfiler
           ├── deque(maxlen=10_000)  — per module_id, O(1) append
           ├── asyncio.Lock          — per module_id, no global lock
           └── _compute_profile()
                 ├── filter: t >= (now - window_seconds)
                 ├── sort durations
                 └── LatencyBucket(p50, p95, p99, max)
```

---

## CognitiveCycle Integration

```python
# In CognitiveCycle._run_module():
import time

async def _run_module(self, module_id: str, *args, **kwargs):
    start = time.monotonic()
    error = False
    try:
        result = await self.get_module(module_id).run(*args, **kwargs)
        return result
    except Exception:
        error = True
        raise
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        await self._profiler.record(module_id, duration_ms, error=error)
```

```python
# Background flush loop (add to CognitiveCycle.__init__):
self._flush_task = asyncio.create_task(self._flush_loop())

async def _flush_loop(self) -> None:
    while True:
        await asyncio.sleep(self._profiler._cfg.window_seconds / 2)
        await self._profiler.flush()
```

---

## Prometheus Metrics

| Metric | Type | Labels |
|---|---|---|
| `asi_profiler_call_total` | Counter | `module_id`, `error` |
| `asi_profiler_latency_ms` | Histogram | `module_id` |
| `asi_profiler_throughput_rps` | Gauge | `module_id` |
| `asi_profiler_window_samples` | Gauge | `module_id` |
| `asi_profiler_tracked_modules` | Gauge | — |

### PromQL Queries

```promql
# P99 latency per module (alert threshold: 500ms)
asi_profiler_latency_ms{quantile="0.99"}

# Module throughput
sum by (module_id) (rate(asi_profiler_call_total[1m]))

# Error rate per module
rate(asi_profiler_call_total{error="true"}[5m])
  / rate(asi_profiler_call_total[5m])
```

### Grafana Alert

```yaml
- alert: ModuleLatencyHigh
  expr: asi_profiler_latency_ms{quantile="0.99"} > 500
  for: 2m
  labels: { severity: warning }
  annotations:
    summary: "Module {{ $labels.module_id }} p99 > 500ms"
```

---

## mypy Compatibility

| Expression | Inferred type | Notes |
|---|---|---|
| `self._samples[mid]` | `deque[tuple[float, float]]` | Annotate explicitly if mypy complains |
| `pct(50)` | `float` | ✓ from sorted list index |
| `make_profiler()` return | `PerformanceProfiler` | Protocol structural match ✓ |
| `reset(module_id=None)` | `None` | Both branches return None ✓ |

---

## Test Targets (12)

| # | Test | Assertion |
|---|---|---|
| 1 | `test_record_single` | One record → `call_count == 1` |
| 2 | `test_latency_percentiles` | Known durations [1..100] → p50≈50, p95≈95, p99≈99 |
| 3 | `test_error_count` | `record(..., error=True)` → `error_count == 1` |
| 4 | `test_throughput_calculation` | Known span → `throughput_rps ≈ n/span` |
| 5 | `test_window_eviction` | Old samples filtered → `call_count == recent_only` |
| 6 | `test_flush_removes_stale` | `flush()` shrinks deque |
| 7 | `test_reset_single_module` | `reset("a")` doesn't affect `"b"` |
| 8 | `test_reset_all` | `reset(None)` clears all modules |
| 9 | `test_list_profiles_multi` | 3 modules → `len(list_profiles()) == 3` |
| 10 | `test_concurrent_record` | `asyncio.gather(200 records)` → no race, count == 200 |
| 11 | `test_max_samples_cap` | Insert `max_samples + 1` → `len(deque) == max_samples` |
| 12 | `test_get_profile_none` | No records → `get_profile()` returns `None` |

---

## Implementation Order (14 steps)

1. `ProfilerGranularity` enum
2. `LatencyBucket` frozen dataclass
3. `ModuleProfile` frozen dataclass
4. `ProfilerConfig` frozen dataclass + `__post_init__` validation
5. `PerformanceProfiler` Protocol (`@runtime_checkable`)
6. `SlidingWindowProfiler.__init__` — `defaultdict` locks + deques
7. `record()` async method
8. `_compute_profile()` — percentile math (nearest-rank)
9. `get_profile()` + `list_profiles()`
10. `flush()` — stale-eviction loop
11. `reset()` — single + all
12. `stats()` — summary dict
13. `make_profiler()` factory
14. `NullProfiler` no-op + 12 pytest test targets

---

## Phase 16 Sub-Phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 16.1 | `PerformanceProfiler` | [#417](https://github.com/web3guru888/asi-build/issues/417) | 🟡 Spec filed |
| 16.2 | `WeaknessDetector` | TBD | ⏳ Upcoming |
| 16.3 | `ImprovementPlanner` | TBD | ⏳ Upcoming |
| 16.4 | `SelfOptimiser` | TBD | ⏳ Upcoming |
| 16.5 | `ReflectionCycle` | TBD | ⏳ Upcoming |

← [Phase 15: Live Module Orchestrator](Phase-15-Live-Module-Orchestrator) | [Phase 16 Planning Discussion #416](https://github.com/web3guru888/asi-build/discussions/416)
