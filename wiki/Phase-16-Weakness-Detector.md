# Phase 16.2 — WeaknessDetector

> Part of **Phase 16: Cognitive Reflection & Self-Improvement** | Issue: [#420](https://github.com/web3guru888/asi-build/issues/420) | Discussions: [S&T #421](https://github.com/web3guru888/asi-build/discussions/421) · [Q&A #422](https://github.com/web3guru888/asi-build/discussions/422)

## Overview

The `WeaknessDetector` translates raw `ModuleProfile` snapshots from the `PerformanceProfiler` (Phase 16.1) into prioritised `Weakness` records. It applies five orthogonal statistical checks (latency SLA breach, throughput drop, regression vs baseline, stability spread, error rate) and returns results sorted CRITICAL → LOW for the `ImprovementPlanner` (Phase 16.3).

## Enums

### `WeaknessCategory`

```python
class WeaknessCategory(enum.Enum):
    LATENCY_SLA      = "latency_sla"       # p95 exceeds SLA
    THROUGHPUT_DROP  = "throughput_drop"   # rps below floor
    REGRESSION       = "regression"        # metric degraded vs rolling baseline
    STABILITY        = "stability"         # p99/p50 spread too wide
    ERROR_RATE       = "error_rate"        # error_count/sample_count above threshold
```

### `WeaknessSeverity`

```python
class WeaknessSeverity(enum.Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
```

Severity mapping for latency:

| p95 / SLA ratio | Severity |
|-----------------|----------|
| < 1.5× | LOW |
| 1.5× – 2.0× | MEDIUM |
| 2.0× – 3.0× | HIGH |
| ≥ 3.0× | CRITICAL |

## Data Structures

### `Weakness` frozen dataclass

```python
@dataclass(frozen=True)
class Weakness:
    module_name:  str
    category:     WeaknessCategory
    severity:     WeaknessSeverity
    metric_name:  str              # e.g. "p95_latency_ms"
    observed:     float
    threshold:    float
    delta_pct:    float            # (observed - baseline) / baseline * 100
    evidence:     str              # human-readable explanation
    tags:         frozenset[str] = field(default_factory=frozenset)
```

### `DetectorConfig` frozen dataclass

```python
@dataclass(frozen=True)
class DetectorConfig:
    latency_sla_ms:           dict[str, float]
    default_latency_sla_ms:   float = 500.0
    throughput_floor_rps:     float = 1.0
    regression_threshold_pct: float = 20.0
    stability_spread_ratio:   float = 5.0
    error_rate_threshold:     float = 0.01
    baseline_window:          int   = 10
    min_samples:              int   = 5
    enabled_categories:       frozenset[WeaknessCategory] = field(
        default_factory=lambda: frozenset(WeaknessCategory)
    )
```

## Protocol

```python
@runtime_checkable
class WeaknessDetector(Protocol):
    def detect(self, profiles: Sequence[ModuleProfile]) -> list[Weakness]: ...
    def update_baseline(self, module_name: str, profile: ModuleProfile) -> None: ...
    def reset(self, module_name: str | None = None) -> None: ...
    def stats(self) -> dict[str, object]: ...
```

## Reference Implementation — `HeuristicWeaknessDetector`

```python
class HeuristicWeaknessDetector:
    def __init__(self, config: DetectorConfig) -> None:
        self._cfg = config
        self._baselines: defaultdict[str, deque[tuple[float, ModuleProfile]]] = defaultdict(
            lambda: deque(maxlen=config.baseline_window)
        )
        self._total_detected = 0

    def detect(self, profiles: Sequence[ModuleProfile]) -> list[Weakness]:
        weaknesses: list[Weakness] = []
        for profile in profiles:
            self.update_baseline(profile.module_name, profile)
            baseline = self._compute_baseline(profile.module_name)
            weaknesses.extend(self._check_profile(profile, baseline))
        self._total_detected += len(weaknesses)
        return sorted(weaknesses, key=lambda w: _SEVERITY_ORDER[w.severity])

    def _compute_baseline(self, module_name: str) -> ModuleProfile | None:
        entries = list(self._baselines[module_name])
        if len(entries) < self._cfg.min_samples:
            return None
        profiles = [p for _, p in entries]
        def mean_field(fn): return statistics.mean(fn(p) for p in profiles)
        return ModuleProfile(
            module_name    = module_name,
            sample_count   = int(mean_field(lambda p: p.sample_count)),
            p50_ms         = mean_field(lambda p: p.p50_ms),
            p95_ms         = mean_field(lambda p: p.p95_ms),
            p99_ms         = mean_field(lambda p: p.p99_ms),
            error_count    = int(mean_field(lambda p: p.error_count)),
            throughput_rps = mean_field(lambda p: p.throughput_rps),
            window_start   = profiles[0].window_start,
            window_end     = profiles[-1].window_end,
        )
```

## Data Flow

```
PerformanceProfiler.stats()
        │
        │  dict[str, ModuleProfile]
        ▼
HeuristicWeaknessDetector.detect(profiles)
        │
        ├── update_baseline() → deque(maxlen=baseline_window)
        │
        ├── _compute_baseline() → mean ModuleProfile (if min_samples met)
        │
        └── _check_profile()
                ├── LATENCY_SLA: p95 vs sla_ms[module]
                ├── THROUGHPUT_DROP: rps vs floor
                ├── REGRESSION: p95/rps vs mean baseline
                ├── STABILITY: p99/p50 ratio
                └── ERROR_RATE: errors/calls ratio
                        │
                        ▼
              list[Weakness] sorted CRITICAL → LOW
                        │
                        ▼
              ImprovementPlanner (16.3)
```

## `NullWeaknessDetector` (testing)

```python
class NullWeaknessDetector:
    def detect(self, profiles): return []
    def update_baseline(self, module_name, profile): pass
    def reset(self, module_name=None): pass
    def stats(self): return {}
```

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_weakness_detected_total` | Counter | `module`, `category`, `severity` | Cumulative weaknesses detected |
| `asi_weakness_active_gauge` | Gauge | `module`, `category` | Currently active weaknesses |
| `asi_detector_baseline_age_seconds` | Gauge | `module` | Age of oldest baseline entry |
| `asi_detector_run_duration_seconds` | Histogram | — | Wall-time per detect() call |
| `asi_detector_modules_tracked` | Gauge | — | Modules with baselines |

## mypy Type-Check Table

| Symbol | Type | Notes |
|--------|------|-------|
| `detect()` return | `list[Weakness]` | always sorted |
| `_baselines` | `defaultdict[str, deque[tuple[float, ModuleProfile]]]` | |
| `enabled_categories` | `frozenset[WeaknessCategory]` | checked via `in` |
| `_compute_baseline()` return | `ModuleProfile \| None` | None if < min_samples |
| `tags` field | `frozenset[str]` | immutable |

## Test Targets

1. `test_latency_sla_breach_flagged`
2. `test_latency_sla_ok_not_flagged`
3. `test_throughput_drop_flagged`
4. `test_regression_latency_flagged`
5. `test_regression_throughput_flagged`
6. `test_stability_spread_flagged`
7. `test_error_rate_flagged`
8. `test_below_min_samples_no_regression`
9. `test_severity_levels_latency`
10. `test_detect_sorted_by_severity`
11. `test_reset_clears_baseline`
12. `test_null_detector_noop`

## Implementation Order (14 steps)

1. Add `WeaknessCategory`, `WeaknessSeverity` enums to `core/types.py`
2. Add `Weakness`, `DetectorConfig` frozen dataclasses
3. Define `WeaknessDetector` Protocol in `core/protocols.py`
4. Implement `HeuristicWeaknessDetector` in `detection/heuristic.py`
5. Implement severity helper functions (`_latency_severity`, `_regression_severity`, `_error_severity`)
6. Implement `_delta_pct()` helper
7. Implement `NullWeaknessDetector` in `detection/null.py`
8. Add `make_detector()` factory
9. Register 5 Prometheus metrics in `detection/metrics.py`
10. Write unit tests (targets 1–9)
11. Write sorted-output test (target 10)
12. Write reset/null tests (targets 11–12)
13. Run `mypy --strict detection/`
14. Wire into `ReflectionCycle._reflection_step()` (Phase 16.5)

## Phase 16 Sub-Phase Tracker

| Sub-Phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 16.1 | PerformanceProfiler | #417 | Open |
| 16.2 | WeaknessDetector | #420 | Open |
| 16.3 | ImprovementPlanner | #423 | Open |
| 16.4 | SelfOptimiser | #426 | Open |
| 16.5 | ReflectionCycle | #430 | Open |

---

*Prev: [Phase 16.1 — PerformanceProfiler](Phase-16-Performance-Profiler) | Next: [Phase 16.3 — ImprovementPlanner](Phase-16-Improvement-Planner)*
