# Phase 16.1 — PerformanceProfiler

> Part of **Phase 16: Cognitive Reflection & Self-Improvement** | Issue: [#417](https://github.com/web3guru888/asi-build/issues/417) | Discussions: [S&T #418](https://github.com/web3guru888/asi-build/discussions/418) · [Q&A #419](https://github.com/web3guru888/asi-build/discussions/419)

## Overview

The `PerformanceProfiler` is the observability foundation of Phase 16. It instruments every module call within the `CognitiveCycle`, collecting per-module latency samples in a sliding time-window and exposing percentile statistics (p50/p95/p99), throughput (rps), and error counts that feed the `WeaknessDetector` (Phase 16.2).

## Data Structures

### `ProfilerGranularity` enum

```python
class ProfilerGranularity(enum.Enum):
    MODULE   = "module"    # one profile per module (default)
    METHOD   = "method"    # one profile per method within a module
    PIPELINE = "pipeline"  # aggregate across all modules
```

### `LatencyBucket` frozen dataclass

```python
@dataclass(frozen=True)
class LatencyBucket:
    latency_ms: float
    timestamp:  float   # time.monotonic()
    error:      bool = False
```

### `ModuleProfile` frozen dataclass

```python
@dataclass(frozen=True)
class ModuleProfile:
    module_name:    str
    sample_count:   int
    p50_ms:         float
    p95_ms:         float
    p99_ms:         float
    error_count:    int
    throughput_rps: float
    window_start:   float
    window_end:     float
```

### `ProfilerConfig` frozen dataclass

```python
@dataclass(frozen=True)
class ProfilerConfig:
    window_seconds:    float = 300.0    # 5-minute sliding window
    max_samples:       int   = 10_000   # per-module deque maxlen
    flush_interval_s:  float = 60.0     # stale-eviction period
    granularity:       ProfilerGranularity = ProfilerGranularity.MODULE
    enabled_modules:   frozenset[str] | None = None  # None = all
```

## Protocol

```python
@runtime_checkable
class PerformanceProfiler(Protocol):
    def record(self, module_name: str, latency_ms: float, *, error: bool = False) -> None: ...
    def profile(self, module_name: str) -> ModuleProfile | None: ...
    def stats(self) -> dict[str, ModuleProfile]: ...
    def flush(self) -> None: ...
    def reset(self, module_name: str | None = None) -> None: ...
```

## Reference Implementation — `SlidingWindowProfiler`

```python
class SlidingWindowProfiler:
    def __init__(self, config: ProfilerConfig) -> None:
        self._cfg = config
        self._buckets: defaultdict[str, deque[LatencyBucket]] = defaultdict(
            lambda: deque(maxlen=config.max_samples)
        )
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def record(self, module_name: str, latency_ms: float, *, error: bool = False) -> None:
        self._buckets[module_name].append(
            LatencyBucket(latency_ms=latency_ms, timestamp=time.monotonic(), error=error)
        )

    def profile(self, module_name: str) -> ModuleProfile | None:
        buckets = self._buckets.get(module_name)
        if not buckets:
            return None
        return self._compute_profile(module_name, list(buckets))

    def _compute_profile(self, module_name: str, buckets: list[LatencyBucket]) -> ModuleProfile:
        now   = time.monotonic()
        cutoff = now - self._cfg.window_seconds
        recent = [b for b in buckets if b.timestamp >= cutoff]
        if not recent:
            recent = buckets   # fall back to all if window empty
        latencies = sorted(b.latency_ms for b in recent)
        n = len(latencies)

        def percentile(p: float) -> float:
            # nearest-rank
            idx = max(0, int(math.ceil(p / 100 * n)) - 1)
            return latencies[idx]

        elapsed = (recent[-1].timestamp - recent[0].timestamp) or 1e-6
        return ModuleProfile(
            module_name    = module_name,
            sample_count   = n,
            p50_ms         = percentile(50),
            p95_ms         = percentile(95),
            p99_ms         = percentile(99),
            error_count    = sum(1 for b in recent if b.error),
            throughput_rps = n / elapsed if elapsed > 0 else 0.0,
            window_start   = recent[0].timestamp,
            window_end     = recent[-1].timestamp,
        )

    def stats(self) -> dict[str, ModuleProfile]:
        return {name: self._compute_profile(name, list(bkts))
                for name, bkts in self._buckets.items() if bkts}

    def flush(self) -> None:
        cutoff = time.monotonic() - self._cfg.window_seconds
        for bkts in self._buckets.values():
            while bkts and bkts[0].timestamp < cutoff:
                bkts.popleft()

    def reset(self, module_name: str | None = None) -> None:
        if module_name is None:
            self._buckets.clear()
        else:
            self._buckets.pop(module_name, None)
```

## `NullProfiler` (testing)

```python
class NullProfiler:
    def record(self, module_name, latency_ms, *, error=False): pass
    def profile(self, module_name): return None
    def stats(self): return {}
    def flush(self): pass
    def reset(self, module_name=None): pass
```

## Data Flow

```
CognitiveCycle._run_module("memory", ...)
        │
        │  finally block (always runs)
        ▼
SlidingWindowProfiler.record("memory", latency_ms)
        │
        │  deque(maxlen=10_000) — O(1) append, auto-evicts oldest
        ▼
_compute_profile("memory")
        │
        │  nearest-rank percentiles on sorted latencies
        ▼
ModuleProfile(p50=..., p95=..., p99=..., throughput_rps=...)
        │
        ▼
WeaknessDetector (Phase 16.2) ──► ImprovementPlanner (16.3) ──► ...
```

## CognitiveCycle Integration

```python
class CognitiveCycle:
    def __init__(self, ..., profiler: PerformanceProfiler) -> None:
        self._profiler = profiler

    async def _run_module(self, name: str, fn: Callable) -> Any:
        t0 = time.monotonic()
        error = False
        try:
            return await fn()
        except Exception:
            error = True
            raise
        finally:
            elapsed_ms = (time.monotonic() - t0) * 1_000
            self._profiler.record(name, elapsed_ms, error=error)
```

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_profiler_record_total` | Counter | `module`, `error` | Total latency samples recorded |
| `asi_profiler_p95_ms` | Gauge | `module` | Latest p95 latency (ms) |
| `asi_profiler_p99_ms` | Gauge | `module` | Latest p99 latency (ms) |
| `asi_profiler_throughput_rps` | Gauge | `module` | Latest throughput (req/s) |
| `asi_profiler_window_samples` | Gauge | `module` | Samples in current window |

### PromQL examples

```promql
# Modules breaching 500 ms p95 SLA
asi_profiler_p95_ms{job="asi-build"} > 500

# p95/p50 latency spread ratio
asi_profiler_p95_ms / on(module) asi_profiler_p50_ms > 3
```

## mypy Type-Check Table

| Symbol | Type annotation | Notes |
|--------|----------------|-------|
| `record()` return | `None` | side-effect only |
| `profile()` return | `ModuleProfile \| None` | callers must guard |
| `stats()` return | `dict[str, ModuleProfile]` | copy, not live view |
| `_buckets` | `defaultdict[str, deque[LatencyBucket]]` | thread-local via asyncio |
| `config.enabled_modules` | `frozenset[str] \| None` | None = all |

## Test Targets

1. `test_record_and_profile_returns_profile` — single record → profile() returns ModuleProfile
2. `test_percentiles_correct` — known latency set → p50/p95/p99 match nearest-rank formula
3. `test_window_eviction` — records older than window_seconds excluded from profile
4. `test_deque_maxlen_evicts_oldest` — maxlen exceeded → oldest sample dropped
5. `test_error_count_tracked` — record with error=True → error_count incremented
6. `test_throughput_rps_calculation` — n samples over t seconds → n/t rps
7. `test_flush_removes_stale` — flush() clears entries outside window
8. `test_reset_single_module` — reset("x") clears only module x
9. `test_reset_all_modules` — reset() clears everything
10. `test_stats_returns_all_modules` — stats() includes all recorded modules
11. `test_concurrent_record` — asyncio.gather 100 concurrent records → no data corruption
12. `test_null_profiler_noop` — NullProfiler methods return None / {} without side effects

## Implementation Order (14 steps)

1. Add `ProfilerGranularity`, `LatencyBucket`, `ModuleProfile`, `ProfilerConfig` to `core/types.py`
2. Define `PerformanceProfiler` Protocol in `core/protocols.py`
3. Implement `SlidingWindowProfiler` in `profiling/sliding_window.py`
4. Implement `NullProfiler` in `profiling/null.py`
5. Add `make_profiler()` factory in `profiling/__init__.py`
6. Integrate `_run_module()` finally-block in `CognitiveCycle`
7. Add `_flush_loop` background task to `CognitiveCycle.__init__()`
8. Register all 5 Prometheus metrics in `profiling/metrics.py`
9. Update `metrics.py` export in `__init__.py`
10. Write unit tests (targets 1–10)
11. Write concurrency test (target 11)
12. Write NullProfiler test (target 12)
13. Run `mypy --strict profiling/` — fix any errors
14. Update `CognitiveCycle` type stubs in `*.pyi` if present

## Phase 16 Sub-Phase Tracker

| Sub-Phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 16.1 | PerformanceProfiler | #417 | Open |
| 16.2 | WeaknessDetector | #420 | Open |
| 16.3 | ImprovementPlanner | #423 | Open |
| 16.4 | SelfOptimiser | #426 | Open |
| 16.5 | ReflectionCycle | #430 | Open |

---

*Next: [Phase 16.2 — WeaknessDetector](Phase-16-Weakness-Detector)*
