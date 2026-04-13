# Phase 16.2 — WeaknessDetector

**Phase**: 16 — Cognitive Reflection & Self-Improvement  
**Component**: `WeaknessDetector`  
**Issue**: #420  
**Depends on**: Phase 16.1 `PerformanceProfiler` (#417)  
**Feeds into**: Phase 16.3 `ImprovementPlanner`

---

## Overview

`WeaknessDetector` converts raw `ModuleProfile` snapshots from `PerformanceProfiler` into ranked `WeaknessReport` objects. It identifies latency regressions, error-rate spikes, throughput drops, and baseline deviations — providing the signal that `ImprovementPlanner` (Phase 16.3) uses to schedule targeted improvements.

---

## Data Model

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Sequence, FrozenSet

class WeaknessKind(Enum):
    HIGH_LATENCY    = auto()   # p95 or p99 exceeds threshold
    HIGH_ERROR_RATE = auto()   # error_rate exceeds threshold
    LOW_THROUGHPUT  = auto()   # throughput_rps below minimum
    LATENCY_SPIKE   = auto()   # recent p99 diverges sharply from baseline p99
    DEGRADED        = auto()   # composite: two or more flags

class WeaknessSeverity(Enum):
    LOW      = 1
    MEDIUM   = 2
    HIGH     = 3
    CRITICAL = 4

@dataclass(frozen=True)
class WeaknessSignal:
    """A single detected anomaly for a module."""
    module_name:  str
    kind:         WeaknessKind
    severity:     WeaknessSeverity
    observed:     float          # measured value (ms, rate, rps)
    threshold:    float          # configured limit
    excess_ratio: float          # observed / threshold  (> 1.0 means violation)

@dataclass(frozen=True)
class WeaknessReport:
    """Aggregated result for one module, may carry multiple signals."""
    module_name:  str
    signals:      tuple[WeaknessSignal, ...]
    severity:     WeaknessSeverity        # max severity across signals
    kinds:        FrozenSet[WeaknessKind] # union of all signal kinds

@dataclass(frozen=True)
class DetectorConfig:
    latency_p95_threshold_ms:  float = 200.0
    latency_p99_threshold_ms:  float = 500.0
    error_rate_threshold:       float = 0.05      # 5 %
    min_throughput_rps:         float = 1.0
    spike_ratio_threshold:      float = 2.0       # p99_recent / p99_baseline > 2×
    baseline_window:            int   = 60        # seconds; older data used as baseline
    severity_weights: tuple[float, ...] = (1.0, 1.5, 2.0, 3.0)  # LOW…CRITICAL
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class WeaknessDetector(Protocol):
    async def analyse(
        self,
        profiles: Sequence[ModuleProfile],
        *,
        config: DetectorConfig | None = None,
    ) -> Sequence[WeaknessReport]: ...

    async def top_weaknesses(
        self,
        profiles: Sequence[ModuleProfile],
        n: int = 5,
        *,
        config: DetectorConfig | None = None,
    ) -> Sequence[WeaknessReport]: ...

    def reset(self) -> None: ...
```

---

## `ThresholdWeaknessDetector` — reference implementation

```python
import asyncio

class ThresholdWeaknessDetector:
    """
    Stateless (per-call) threshold + spike detector.
    Maintains a baseline map: module_name → baseline_p99_ms,
    refreshed via exponential smoothing (α = 0.1).
    """

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self._default_config = config or DetectorConfig()
        self._baseline: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def analyse(
        self,
        profiles: Sequence[ModuleProfile],
        *,
        config: DetectorConfig | None = None,
    ) -> list[WeaknessReport]:
        cfg = config or self._default_config
        reports: list[WeaknessReport] = []
        async with self._lock:
            for profile in profiles:
                signals = self._detect_signals(profile, cfg)
                if signals:
                    kinds    = frozenset(s.kind for s in signals)
                    severity = max(s.severity for s in signals)
                    if len(kinds) >= 2:
                        kinds = kinds | {WeaknessKind.DEGRADED}
                    reports.append(WeaknessReport(
                        module_name=profile.module_name,
                        signals=tuple(signals),
                        severity=severity,
                        kinds=kinds,
                    ))
        return sorted(reports, key=lambda r: (
            -r.severity.value,
            -max(s.excess_ratio for s in r.signals),
        ))

    async def top_weaknesses(
        self,
        profiles: Sequence[ModuleProfile],
        n: int = 5,
        *,
        config: DetectorConfig | None = None,
    ) -> list[WeaknessReport]:
        return (await self.analyse(profiles, config=config))[:n]

    def reset(self) -> None:
        self._baseline.clear()

    def _detect_signals(
        self,
        profile: ModuleProfile,
        cfg: DetectorConfig,
    ) -> list[WeaknessSignal]:
        signals: list[WeaknessSignal] = []

        # p95 latency
        if profile.p95_ms > cfg.latency_p95_threshold_ms:
            signals.append(WeaknessSignal(
                module_name  = profile.module_name,
                kind         = WeaknessKind.HIGH_LATENCY,
                severity     = self._latency_severity(profile.p95_ms, cfg.latency_p95_threshold_ms),
                observed     = profile.p95_ms,
                threshold    = cfg.latency_p95_threshold_ms,
                excess_ratio = profile.p95_ms / cfg.latency_p95_threshold_ms,
            ))

        # p99 latency
        if profile.p99_ms > cfg.latency_p99_threshold_ms:
            signals.append(WeaknessSignal(
                module_name  = profile.module_name,
                kind         = WeaknessKind.HIGH_LATENCY,
                severity     = self._latency_severity(profile.p99_ms, cfg.latency_p99_threshold_ms),
                observed     = profile.p99_ms,
                threshold    = cfg.latency_p99_threshold_ms,
                excess_ratio = profile.p99_ms / cfg.latency_p99_threshold_ms,
            ))

        # error rate
        if profile.error_rate > cfg.error_rate_threshold:
            ratio = profile.error_rate / cfg.error_rate_threshold
            signals.append(WeaknessSignal(
                module_name  = profile.module_name,
                kind         = WeaknessKind.HIGH_ERROR_RATE,
                severity     = WeaknessSeverity.CRITICAL if ratio > 4 else
                               WeaknessSeverity.HIGH     if ratio > 2 else
                               WeaknessSeverity.MEDIUM,
                observed     = profile.error_rate,
                threshold    = cfg.error_rate_threshold,
                excess_ratio = ratio,
            ))

        # throughput
        if profile.throughput_rps < cfg.min_throughput_rps and profile.throughput_rps > 0:
            signals.append(WeaknessSignal(
                module_name  = profile.module_name,
                kind         = WeaknessKind.LOW_THROUGHPUT,
                severity     = WeaknessSeverity.LOW,
                observed     = profile.throughput_rps,
                threshold    = cfg.min_throughput_rps,
                excess_ratio = cfg.min_throughput_rps / max(profile.throughput_rps, 1e-9),
            ))

        # latency spike vs baseline
        baseline = self._baseline.get(profile.module_name)
        if baseline is None:
            self._baseline[profile.module_name] = profile.p99_ms
        elif baseline > 0:
            spike_ratio = profile.p99_ms / baseline
            if spike_ratio > cfg.spike_ratio_threshold:
                signals.append(WeaknessSignal(
                    module_name  = profile.module_name,
                    kind         = WeaknessKind.LATENCY_SPIKE,
                    severity     = WeaknessSeverity.CRITICAL if spike_ratio > 5 else
                                   WeaknessSeverity.HIGH,
                    observed     = profile.p99_ms,
                    threshold    = baseline * cfg.spike_ratio_threshold,
                    excess_ratio = spike_ratio,
                ))
            # Exponential smoothing: α = 0.1
            self._baseline[profile.module_name] = 0.9 * baseline + 0.1 * profile.p99_ms

        return signals

    @staticmethod
    def _latency_severity(observed: float, threshold: float) -> WeaknessSeverity:
        ratio = observed / threshold
        if ratio > 5:   return WeaknessSeverity.CRITICAL
        if ratio > 3:   return WeaknessSeverity.HIGH
        if ratio > 1.5: return WeaknessSeverity.MEDIUM
        return WeaknessSeverity.LOW
```

---

## `NullWeaknessDetector` — no-op for testing

```python
class NullWeaknessDetector:
    async def analyse(self, profiles, *, config=None): return []
    async def top_weaknesses(self, profiles, n=5, *, config=None): return []
    def reset(self) -> None: pass
```

---

## Signal detection pipeline (data flow)

```
PerformanceProfiler.stats()
        │
        ▼  Sequence[ModuleProfile]
ThresholdWeaknessDetector.analyse()
        │
        ├── _detect_signals(profile, cfg)          ← called under asyncio.Lock
        │       ├── p95_ms  > latency_p95_threshold_ms  → HIGH_LATENCY
        │       ├── p99_ms  > latency_p99_threshold_ms  → HIGH_LATENCY
        │       ├── error_rate > error_rate_threshold   → HIGH_ERROR_RATE
        │       ├── throughput_rps < min_throughput_rps → LOW_THROUGHPUT
        │       └── p99_ms / baseline > spike_ratio     → LATENCY_SPIKE
        │
        ├── DEGRADED flag added if ≥ 2 distinct WeaknessKind values
        │
        └── Sort: CRITICAL first → by excess_ratio
                │
                ▼  list[WeaknessReport]
        ImprovementPlanner.schedule()   [Phase 16.3]
```

---

## WeaknessKind × severity mapping

| Kind | Trigger | Severity formula |
|------|---------|-----------------|
| `HIGH_LATENCY` | `p95 > 200 ms` or `p99 > 500 ms` | LOW < 1.5× / MEDIUM < 3× / HIGH < 5× / CRITICAL ≥ 5× |
| `HIGH_ERROR_RATE` | `error_rate > 5 %` | MEDIUM < 2× / HIGH < 4× / CRITICAL ≥ 4× |
| `LOW_THROUGHPUT` | `rps < 1.0` | LOW (always) |
| `LATENCY_SPIKE` | `p99 / baseline > 2×` | HIGH (< 5×) / CRITICAL (≥ 5×) |
| `DEGRADED` | 2+ distinct kinds | max of component signals |

---

## Exponential smoothing baseline

The spike detector maintains a per-module baseline p99 with α = 0.1:

```
new_baseline = 0.9 × old_baseline + 0.1 × current_p99
```

Half-life ≈ 6.6 observations (i.e., a spike fades to 10 % of its impact after ~23 observations). This prevents a one-off spike from permanently raising the baseline and masking future regressions.

---

## CognitiveCycle integration

```python
# In CognitiveCycle (or ReflectionCycle — Phase 16.5):

async def _reflection_step(self) -> None:
    profiles = list(self._profiler.stats().values())
    reports  = await self._weakness_detector.top_weaknesses(profiles, n=5)
    if reports:
        await self._improvement_planner.schedule(reports)   # Phase 16.3
```

---

## Prometheus metrics

| Metric | Type | Labels |
|--------|------|--------|
| `asi_weakness_analyses_total` | Counter | — |
| `asi_weakness_signals_total` | Counter | `kind`, `severity` |
| `asi_weakness_reports_active` | Gauge | — |
| `asi_weakness_top_severity` | Gauge | `module_name` |
| `asi_weakness_detector_latency_seconds` | Histogram | — |

**PromQL alert — critical module**:
```
asi_weakness_top_severity{module_name=~".+"} >= 4
```

**Grafana alert YAML**:
```yaml
- alert: ModuleCriticalWeakness
  expr: asi_weakness_top_severity >= 4
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Module {{ $labels.module_name }} has CRITICAL weakness"
    description: "Weakness detector flagged {{ $labels.module_name }} CRITICAL for >2m"
```

**Grafana dashboard panels**:
```yaml
panels:
  - title: "Analyses / min"
    expr: rate(asi_weakness_analyses_total[1m]) * 60
  - title: "Active reports"
    expr: asi_weakness_reports_active
  - title: "Top module severity"
    expr: topk(5, asi_weakness_top_severity)
  - title: "Detector latency p99"
    expr: histogram_quantile(0.99, rate(asi_weakness_detector_latency_seconds_bucket[5m]))
```

---

## mypy `--strict` compliance

| Symbol | Expected type |
|--------|--------------|
| `profiles` parameter | `Sequence[ModuleProfile]` |
| `_detect_signals` return | `list[WeaknessSignal]` |
| `analyse` return | `list[WeaknessReport]` |
| `top_weaknesses` return | `list[WeaknessReport]` |
| `_baseline` | `dict[str, float]` |
| `kinds` (before DEGRADED) | `frozenset[WeaknessKind]` |

---

## Test targets (12)

1. `test_no_weakness_clean_profiles` — profiles within all thresholds → empty report
2. `test_high_latency_p95_detected` — p95 > threshold → HIGH_LATENCY signal
3. `test_high_latency_p99_detected` — p99 > threshold → HIGH_LATENCY signal
4. `test_high_error_rate_critical` — error_rate 4× threshold → CRITICAL
5. `test_low_throughput_detected` — rps < min → LOW_THROUGHPUT signal
6. `test_latency_spike_first_call` — first call stores baseline, no spike
7. `test_latency_spike_subsequent` — second call 3× baseline → LATENCY_SPIKE HIGH
8. `test_degraded_kind_added` — two distinct kinds → DEGRADED added to kinds
9. `test_sorted_by_severity` — CRITICAL before MEDIUM before LOW
10. `test_top_weaknesses_n` — only top-n returned
11. `test_reset_clears_baseline` — reset() → next call re-initialises baseline
12. `test_concurrent_analyse` — `asyncio.gather` 10 concurrent callers → Lock prevents race

---

## Implementation order (14 steps)

1. Add `WeaknessKind` enum to `asi_build/reflection/enums.py`
2. Add `WeaknessSeverity` enum to same file
3. Add `WeaknessSignal` frozen dataclass to `asi_build/reflection/models.py`
4. Add `WeaknessReport` frozen dataclass (note `frozenset` for `kinds`)
5. Add `DetectorConfig` frozen dataclass
6. Add `WeaknessDetector` Protocol (`@runtime_checkable`) to `asi_build/reflection/protocols.py`
7. Implement `ThresholdWeaknessDetector._latency_severity()` (static method)
8. Implement `ThresholdWeaknessDetector._detect_signals()` (sync, called under lock)
9. Implement `ThresholdWeaknessDetector.analyse()` (async, holds lock)
10. Implement `ThresholdWeaknessDetector.top_weaknesses()` and `reset()`
11. Implement `NullWeaknessDetector`
12. Register 5 Prometheus metrics in `asi_build/reflection/metrics.py`
13. Wire `_reflection_step()` in `CognitiveCycle` (or stub for Phase 16.5)
14. Write 12 pytest targets; run `mypy --strict`

---

## Phase 16 sub-phase tracker

| Sub-phase | Component | Issue | Discussions | Status |
|-----------|-----------|-------|-------------|--------|
| 16.1 | `PerformanceProfiler` | #417 | #418 S&T / #419 Q&A | 🟡 In spec |
| 16.2 | `WeaknessDetector` | #420 | #421 S&T / #422 Q&A | 🟡 In spec |
| 16.3 | `ImprovementPlanner` | ⏳ | — | ⏳ |
| 16.4 | `SelfOptimiser` | ⏳ | — | ⏳ |
| 16.5 | `ReflectionCycle` | ⏳ | — | ⏳ |
