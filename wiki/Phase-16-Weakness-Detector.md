# Phase 16.2 — `WeaknessDetector`

**Phase**: 16 — Cognitive Reflection & Self-Improvement
**Component**: `WeaknessDetector`
**Depends on**: Phase 16.1 [`PerformanceProfiler`](Phase-16-Performance-Profiler) (#417)
**Feeds into**: Phase 16.3 `ImprovementPlanner`
**Issue**: #420 | **Show & Tell**: #421 | **Q&A**: #422

---

## Overview

`WeaknessDetector` is the diagnostic layer of the Cognitive Reflection cycle. It consumes `ModuleProfile` snapshots produced by `PerformanceProfiler` and applies a battery of heuristic checks to identify modules that are violating SLA thresholds, experiencing regression, exhibiting instability, or generating excessive errors. Each detected problem is emitted as a `Weakness` record, severity-ranked, and forwarded to `ImprovementPlanner` for action planning.

The detector maintains a rolling **baseline** of historical profile data (a configurable window of recent observations) against which current measurements are compared. This makes the detector robust to gradual drift — it flags regression relative to *recent* normal behaviour, not a static factory default.

---

## Enumerations

### `WeaknessCategory`

```python
from enum import Enum, auto

class WeaknessCategory(Enum):
    LATENCY_SLA      = auto()   # p95 latency exceeds per-module SLA
    THROUGHPUT_DROP  = auto()   # calls/s has fallen below floor
    REGRESSION       = auto()   # metric has regressed vs rolling baseline
    STABILITY        = auto()   # high spread between p50 and p95 (jitter)
    ERROR_RATE       = auto()   # error fraction exceeds threshold
```

### `WeaknessSeverity`

```python
class WeaknessSeverity(Enum):
    CRITICAL = 0   # immediate action required (sort key: lowest = highest urgency)
    HIGH     = 1
    MEDIUM   = 2
    LOW      = 3
```

Severity is assigned per-category and scaled by how far the observed value exceeds the threshold:

| `delta_pct` vs threshold | Assigned severity |
|--------------------------|-------------------|
| ≥ 100 %                  | `CRITICAL`        |
| 50 – 99 %                | `HIGH`            |
| 20 – 49 %                | `MEDIUM`          |
| 0 – 19 %                 | `LOW`             |

---

## Frozen Dataclasses

### `Weakness`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class Weakness:
    module_name:  str
    category:     WeaknessCategory
    severity:     WeaknessSeverity
    metric_name:  str                         # e.g. "latency_p95_ms"
    observed:     float                       # current measured value
    threshold:    float                       # limit that was breached
    delta_pct:    float                       # (observed - threshold) / threshold × 100
    evidence:     str                         # human-readable explanation
    tags:         Tuple[str, ...] = ()        # e.g. ("phase:16", "module:planner")
```

`tags` is a `Tuple` (not `list`) so the dataclass remains hashable and sortable.

### `DetectorConfig`

```python
@dataclass(frozen=True)
class DetectorConfig:
    # per-module SLA overrides: module_name → ms; fallback = default_latency_sla_ms
    latency_sla_ms:           Tuple[Tuple[str, float], ...] = ()
    default_latency_sla_ms:   float = 500.0   # ms
    throughput_floor_rps:     float = 1.0     # calls/s minimum
    regression_threshold_pct: float = 20.0   # % degradation vs baseline
    stability_spread_ratio:   float = 5.0    # p95 / p50 ratio above which jitter fires
    error_rate_threshold:     float = 0.01   # 1 % default
    baseline_window:          int   = 10     # how many historical snapshots to average
    min_samples:              int   = 5      # minimum baseline entries before firing
    enabled_categories:       Tuple[WeaknessCategory, ...] = (
        WeaknessCategory.LATENCY_SLA,
        WeaknessCategory.THROUGHPUT_DROP,
        WeaknessCategory.REGRESSION,
        WeaknessCategory.STABILITY,
        WeaknessCategory.ERROR_RATE,
    )

    def sla_for(self, module: str) -> float:
        return dict(self.latency_sla_ms).get(module, self.default_latency_sla_ms)
```

---

## Protocol

```python
from typing import Protocol, Sequence, runtime_checkable

@runtime_checkable
class WeaknessDetector(Protocol):
    async def detect(
        self,
        profiles: Sequence[ModuleProfile],
    ) -> Sequence[Weakness]: ...

    async def update_baseline(
        self,
        profiles: Sequence[ModuleProfile],
    ) -> None: ...

    async def reset(self) -> None: ...
    def stats(self) -> dict[str, int]: ...
```

`detect` **does not mutate baseline** — call `update_baseline` separately (typically once per reflection cycle, after acting on results).

---

## `HeuristicWeaknessDetector` — Canonical Implementation

```python
import asyncio
import statistics
from collections import defaultdict, deque

class HeuristicWeaknessDetector:
    """Rule-based weakness detection with rolling baseline."""

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self._cfg = config or DetectorConfig()
        # module_name → deque of ModuleProfile snapshots
        self._baseline: dict[str, deque[ModuleProfile]] = defaultdict(
            lambda: deque(maxlen=self._cfg.baseline_window)
        )
        self._lock = asyncio.Lock()
        self._counters: dict[str, int] = defaultdict(int)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def detect(
        self,
        profiles: Sequence[ModuleProfile],
    ) -> Sequence[Weakness]:
        weaknesses: list[Weakness] = []
        async with self._lock:
            for profile in profiles:
                weaknesses.extend(self._check_profile(profile))
        # Sort: CRITICAL first, then HIGH, MEDIUM, LOW
        weaknesses.sort(key=lambda w: w.severity.value)
        self._counters["detect_calls"] += 1
        self._counters["weaknesses_found"] += len(weaknesses)
        return weaknesses

    async def update_baseline(
        self,
        profiles: Sequence[ModuleProfile],
    ) -> None:
        async with self._lock:
            for profile in profiles:
                self._baseline[profile.module_name].append(profile)
        self._counters["baseline_updates"] += 1

    async def reset(self) -> None:
        async with self._lock:
            self._baseline.clear()
            self._counters.clear()

    def stats(self) -> dict[str, int]:
        return dict(self._counters)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _compute_baseline(
        self,
        module: str,
        attr: str,
    ) -> float | None:
        """Return mean of `attr` over baseline window, or None if too few samples."""
        history = self._baseline[module]
        if len(history) < self._cfg.min_samples:
            return None
        values = [getattr(snap, attr) for snap in history]
        return statistics.mean(values)

    def _severity_from_delta(self, delta_pct: float) -> WeaknessSeverity:
        if delta_pct >= 100.0:
            return WeaknessSeverity.CRITICAL
        if delta_pct >= 50.0:
            return WeaknessSeverity.HIGH
        if delta_pct >= 20.0:
            return WeaknessSeverity.MEDIUM
        return WeaknessSeverity.LOW

    def _check_profile(self, profile: ModuleProfile) -> list[Weakness]:
        found: list[Weakness] = []
        enabled = set(self._cfg.enabled_categories)

        # ── LATENCY_SLA ────────────────────────────────────────────────
        if WeaknessCategory.LATENCY_SLA in enabled:
            sla = self._cfg.sla_for(profile.module_name)
            if profile.p95_ms > sla:
                delta = (profile.p95_ms - sla) / sla * 100
                found.append(Weakness(
                    module_name=profile.module_name,
                    category=WeaknessCategory.LATENCY_SLA,
                    severity=self._severity_from_delta(delta),
                    metric_name="latency_p95_ms",
                    observed=profile.p95_ms,
                    threshold=sla,
                    delta_pct=round(delta, 2),
                    evidence=(
                        f"p95={profile.p95_ms:.1f}ms exceeds SLA={sla:.1f}ms "
                        f"({delta:.1f}% over)"
                    ),
                ))

        # ── THROUGHPUT_DROP ────────────────────────────────────────────
        if WeaknessCategory.THROUGHPUT_DROP in enabled:
            floor = self._cfg.throughput_floor_rps
            if profile.throughput_rps < floor:
                delta = (floor - profile.throughput_rps) / max(floor, 1e-9) * 100
                found.append(Weakness(
                    module_name=profile.module_name,
                    category=WeaknessCategory.THROUGHPUT_DROP,
                    severity=self._severity_from_delta(delta),
                    metric_name="throughput_rps",
                    observed=profile.throughput_rps,
                    threshold=floor,
                    delta_pct=round(delta, 2),
                    evidence=(
                        f"throughput={profile.throughput_rps:.2f} rps "
                        f"below floor={floor:.2f} rps"
                    ),
                ))

        # ── REGRESSION ────────────────────────────────────────────────
        if WeaknessCategory.REGRESSION in enabled:
            baseline_p95 = self._compute_baseline(profile.module_name, "p95_ms")
            if baseline_p95 is not None:
                delta = (profile.p95_ms - baseline_p95) / max(baseline_p95, 1e-9) * 100
                if delta >= self._cfg.regression_threshold_pct:
                    found.append(Weakness(
                        module_name=profile.module_name,
                        category=WeaknessCategory.REGRESSION,
                        severity=self._severity_from_delta(delta),
                        metric_name="latency_p95_regression_pct",
                        observed=profile.p95_ms,
                        threshold=baseline_p95,
                        delta_pct=round(delta, 2),
                        evidence=(
                            f"p95={profile.p95_ms:.1f}ms regressed "
                            f"{delta:.1f}% vs baseline {baseline_p95:.1f}ms"
                        ),
                    ))

        # ── STABILITY ─────────────────────────────────────────────────
        if WeaknessCategory.STABILITY in enabled:
            p50 = profile.p50_ms
            ratio = profile.p95_ms / max(p50, 1e-9)
            if ratio >= self._cfg.stability_spread_ratio:
                delta = (ratio - self._cfg.stability_spread_ratio) / self._cfg.stability_spread_ratio * 100
                found.append(Weakness(
                    module_name=profile.module_name,
                    category=WeaknessCategory.STABILITY,
                    severity=self._severity_from_delta(delta),
                    metric_name="p95_p50_spread_ratio",
                    observed=round(ratio, 2),
                    threshold=self._cfg.stability_spread_ratio,
                    delta_pct=round(delta, 2),
                    evidence=(
                        f"p95/p50 ratio={ratio:.2f} exceeds "
                        f"stability_spread_ratio={self._cfg.stability_spread_ratio}"
                    ),
                ))

        # ── ERROR_RATE ────────────────────────────────────────────────
        if WeaknessCategory.ERROR_RATE in enabled:
            thresh = self._cfg.error_rate_threshold
            if profile.error_rate > thresh:
                delta = (profile.error_rate - thresh) / max(thresh, 1e-9) * 100
                found.append(Weakness(
                    module_name=profile.module_name,
                    category=WeaknessCategory.ERROR_RATE,
                    severity=self._severity_from_delta(delta),
                    metric_name="error_rate",
                    observed=profile.error_rate,
                    threshold=thresh,
                    delta_pct=round(delta, 2),
                    evidence=(
                        f"error_rate={profile.error_rate:.4f} exceeds "
                        f"threshold={thresh:.4f} ({delta:.1f}% over)"
                    ),
                ))

        return found
```

---

## `NullWeaknessDetector` — No-op for Testing

```python
class NullWeaknessDetector:
    """Accepts any profile; always reports no weaknesses."""

    async def detect(self, profiles):
        return []

    async def update_baseline(self, profiles):
        pass

    async def reset(self):
        pass

    def stats(self):
        return {}
```

Use `NullWeaknessDetector` in unit tests for components that depend on `WeaknessDetector` but whose tests are not focused on weakness detection logic.

---

## Data Flow — ASCII Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   CognitiveCycle (Phase 16.5)                   │
│                                                                 │
│  every reflection_interval_s:                                   │
│  ┌──────────────────┐    profiles: list[ModuleProfile]          │
│  │ PerformanceProfiler│─────────────────────────────────────────►│
│  │  (Phase 16.1)    │                                           │
│  └──────────────────┘                                           │
│                        ┌──────────────────────────────────────┐ │
│         profiles ──────► HeuristicWeaknessDetector             │ │
│                        │  _check_profile() × N modules        │ │
│                        │  ├─ LATENCY_SLA check                 │ │
│                        │  ├─ THROUGHPUT_DROP check             │ │
│                        │  ├─ REGRESSION check (vs baseline)    │ │
│                        │  ├─ STABILITY check (p95/p50 ratio)   │ │
│                        │  └─ ERROR_RATE check                  │ │
│                        │                                       │ │
│                        │  sorted(weaknesses, key=severity)     │ │
│                        └──────────────┬───────────────────────┘ │
│                                       │ Sequence[Weakness]       │
│                                       ▼                          │
│                        ┌─────────────────────────┐              │
│                        │   ImprovementPlanner     │              │
│                        │     (Phase 16.3)         │              │
│                        └─────────────────────────┘              │
│                                                                 │
│  update_baseline(profiles)   ◄── called after acting on results │
└─────────────────────────────────────────────────────────────────┘
```

---

## Integration with `ReflectionCycle` (Phase 16.5 Preview)

```python
class ReflectionCycle:
    def __init__(
        self,
        profiler: PerformanceProfiler,
        detector: WeaknessDetector,
        planner: ImprovementPlanner,
        optimiser: SelfOptimiser,
        config: ReflectionConfig,
    ) -> None: ...

    async def _run_cycle(self) -> None:
        # 1. Gather profiles from all active modules
        profiles = await self._profiler.get_all_profiles()

        # 2. Detect weaknesses
        weaknesses = await self._detector.detect(profiles)

        # 3. Plan improvements
        actions = await self._planner.plan(weaknesses)

        # 4. Execute improvements
        results = await self._optimiser.execute_batch(actions)

        # 5. Update baseline with current profiles
        await self._detector.update_baseline(profiles)
```

The baseline update happens **after** acting on results so that improvements made in step 4 are reflected in the next cycle's baseline rather than being immediately compared against themselves.

---

## Prometheus Metrics

| Metric name | Type | Labels | Description |
|---|---|---|---|
| `asi_weakness_detector_detect_calls_total` | Counter | `module` | Total `detect()` invocations |
| `asi_weakness_detector_weaknesses_total` | Counter | `module`, `category`, `severity` | Weaknesses found per category/severity |
| `asi_weakness_detector_baseline_updates_total` | Counter | — | Total baseline update calls |
| `asi_weakness_detector_baseline_depth` | Gauge | `module` | Current baseline snapshot count per module |
| `asi_weakness_detector_detect_duration_seconds` | Histogram | — | Wall time for each `detect()` call |

### Example PromQL

```promql
# Modules currently in CRITICAL/HIGH weakness state
sum by (module, category) (
  increase(asi_weakness_detector_weaknesses_total{severity=~"CRITICAL|HIGH"}[5m])
)

# Latency SLA breach rate
rate(asi_weakness_detector_weaknesses_total{category="LATENCY_SLA"}[5m])
```

### Grafana Alert — Sustained CRITICAL Weakness

```yaml
alert: ASICriticalWeaknessSustained
expr: |
  increase(
    asi_weakness_detector_weaknesses_total{severity="CRITICAL"}[10m]
  ) > 0
for: 2m
labels:
  severity: critical
annotations:
  summary: "Module {{ $labels.module }} has sustained CRITICAL weakness"
  description: "Category {{ $labels.category }} — consider triggering SelfOptimiser"
```

---

## mypy Type-Check Compatibility

| Expression | Expected type | Notes |
|---|---|---|
| `HeuristicWeaknessDetector()` | `WeaknessDetector` | passes `isinstance(x, WeaknessDetector)` |
| `NullWeaknessDetector()` | `WeaknessDetector` | structural subtype via Protocol |
| `weakness.severity` | `WeaknessSeverity` | frozen dataclass — immutable |
| `weakness.tags` | `Tuple[str, ...]` | hashable, works in `frozenset` |
| `config.enabled_categories` | `Tuple[WeaknessCategory, ...]` | iterate with `set(config.enabled_categories)` |
| `_compute_baseline(...)` | `float \| None` | callers must guard `if baseline is not None` |
| `sorted(weaknesses, key=lambda w: w.severity.value)` | `list[Weakness]` | `value` is `int` (0–3) |

Run `mypy --strict asi_build/cognition/weakness_detector.py` — target zero errors.

---

## Test Targets (12)

| # | Test name | What it covers |
|---|---|---|
| 1 | `test_detect_latency_sla_breach` | p95 > default SLA → `LATENCY_SLA` weakness emitted |
| 2 | `test_detect_latency_sla_per_module_override` | per-module SLA via `latency_sla_ms` tuple |
| 3 | `test_detect_throughput_drop` | throughput < floor → `THROUGHPUT_DROP` weakness |
| 4 | `test_detect_regression_after_baseline` | update_baseline then regression → `REGRESSION` weakness |
| 5 | `test_detect_regression_below_min_samples` | fewer than `min_samples` → no regression fired |
| 6 | `test_detect_stability_spread` | p95/p50 ratio ≥ spread_ratio → `STABILITY` weakness |
| 7 | `test_detect_error_rate` | error_rate > threshold → `ERROR_RATE` weakness |
| 8 | `test_detect_severity_scaling` | delta_pct 10/40/60/110 → LOW/MEDIUM/HIGH/CRITICAL |
| 9 | `test_detect_sorted_by_severity` | result order is CRITICAL → HIGH → MEDIUM → LOW |
| 10 | `test_detect_disabled_category` | category not in `enabled_categories` → not fired |
| 11 | `test_concurrent_detect_update_baseline` | `asyncio.gather` with detect+update_baseline — no race |
| 12 | `test_null_weakness_detector_protocol` | `isinstance(NullWeaknessDetector(), WeaknessDetector)` is True |

### Skeleton — `test_concurrent_detect_update_baseline`

```python
import asyncio
import pytest

@pytest.mark.asyncio
async def test_concurrent_detect_update_baseline():
    detector = HeuristicWeaknessDetector()
    profiles = [make_profile("mod_a", p95_ms=600.0, throughput_rps=5.0)]

    # Seed baseline
    for _ in range(5):
        await detector.update_baseline(profiles)

    # Concurrent detect + additional baseline updates should not deadlock
    results = await asyncio.gather(
        detector.detect(profiles),
        detector.update_baseline(profiles),
        detector.detect(profiles),
        detector.update_baseline(profiles),
    )
    assert all(isinstance(r, (list, type(None))) for r in results)
```

---

## 14-Step Implementation Order

1. Add `WeaknessCategory` and `WeaknessSeverity` enums to `asi_build/cognition/enums.py`
2. Add `Weakness` frozen dataclass to `asi_build/cognition/profiles.py`
3. Add `DetectorConfig` frozen dataclass (same file, or `configs.py`)
4. Implement `_severity_from_delta()` pure function
5. Implement `HeuristicWeaknessDetector.__init__()` with `defaultdict(deque)` baseline
6. Implement `_compute_baseline()` using `statistics.mean`
7. Implement `_check_profile()` — LATENCY_SLA check
8. Extend `_check_profile()` — THROUGHPUT_DROP check
9. Extend `_check_profile()` — REGRESSION check (guarded by `min_samples`)
10. Extend `_check_profile()` — STABILITY check
11. Extend `_check_profile()` — ERROR_RATE check
12. Implement `detect()` — call `_check_profile` per profile, sort, update counters
13. Implement `update_baseline()` and `reset()`
14. Wire Prometheus metrics and write 12 tests

---

## Phase 16 Sub-Phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 16.1 | `PerformanceProfiler` | #417 | 🟡 Open |
| 16.2 | `WeaknessDetector` | #420 | 🟡 Open |
| 16.3 | `ImprovementPlanner` | #423 | 🟡 Open |
| 16.4 | `SelfOptimiser` | #426 | ⏳ Planned |
| 16.5 | `ReflectionCycle` | #429 | ⏳ Planned |
