# Phase 11.2 — AlignmentMonitor: Continuous Behavioral Drift Detection

**Issue**: [#340](https://github.com/web3guru888/asi-build/issues/340)  
**Phase**: 11.2 — Safety & Alignment  
**Status**: In spec  
**Discussions**: [Show & Tell #341](https://github.com/web3guru888/asi-build/discussions/341) · [Q&A #342](https://github.com/web3guru888/asi-build/discussions/342)  
**Depends on**: [Phase 11.1 — SafetyFilter](Phase-11-Safety-Filter) · [Phase 10.4 — ExecutionMonitor](Phase-10-Execution-Monitor)

---

## Overview

`AlignmentMonitor` provides *continuous* alignment oversight of the ASI:BUILD autonomy loop. Where `SafetyFilter` (Phase 11.1) gates individual goals and sub-tasks at the point of entry, `AlignmentMonitor` watches the running system over time, tracking five alignment dimensions, computing rolling window scores, and emitting alerts (or pausing the autonomy loop) when behaviour drifts from the constitutional specification.

---

## Data Model

```python
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Protocol, runtime_checkable

class AlignmentDimension(Enum):
    CONSTITUTIONAL   = "constitutional"   # SafetyFilter violation rate
    CAPABILITY_SCOPE = "capability_scope" # tasks within authorised capability set
    GOAL_PRIORITY    = "goal_priority"    # escalation rate vs baseline
    RESOURCE_USAGE   = "resource_usage"   # compute/memory within declared budget
    FEDERATION_TRUST = "federation_trust" # cross-peer trust score stability

@dataclass(frozen=True)
class AlignmentSample:
    dimension: AlignmentDimension
    agent_id: str
    score: float          # [0.0, 1.0] — 1.0 = fully aligned
    raw_value: float      # unnormalised measurement
    timestamp: float = field(default_factory=time.monotonic)

@dataclass(frozen=True)
class AlignmentWindow:
    dimension: AlignmentDimension
    agent_id: str
    window_start: float
    window_end: float
    mean_score: float
    min_score: float
    sample_count: int

@dataclass(frozen=True)
class AlignmentAlert:
    alert_id: str
    dimension: AlignmentDimension
    agent_id: str
    mean_score: float
    threshold: float
    triggered_at: float
    resolved_at: float | None = None

@dataclass(frozen=True)
class AlignmentSnapshot:
    agent_id: str
    windows: dict[AlignmentDimension, AlignmentWindow]
    overall_score: float
    active_alert_count: int
    captured_at: float = field(default_factory=time.monotonic)

@dataclass(frozen=True)
class MonitorConfig:
    window_ms: int = 60_000          # rolling window length
    sample_interval_ms: int = 5_000  # suggested producer interval
    alert_threshold: float = 0.70    # score below this → AlignmentAlert
    critical_threshold: float = 0.50 # score below this → pause loop
    max_samples_per_dim: int = 720   # ring buffer cap per (dimension, agent_id)
    pause_on_critical: bool = True
```

---

## `AlignmentMonitor` Protocol

```python
@runtime_checkable
class AlignmentMonitor(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def record(self, sample: AlignmentSample) -> None: ...
    async def window(
        self,
        dimension: AlignmentDimension,
        agent_id: str,
        window_ms: int | None = None,
    ) -> AlignmentWindow: ...
    async def overall_score(self, agent_id: str) -> float: ...
    async def active_alerts(self) -> list[AlignmentAlert]: ...
    async def alert_history(self, since_ts: float) -> list[AlignmentAlert]: ...
    async def snapshot(self) -> AlignmentSnapshot: ...
```

---

## `InMemoryAlignmentMonitor`

```python
import asyncio
from collections import defaultdict

class InMemoryAlignmentMonitor:
    """Thread-safe in-process AlignmentMonitor backed by per-dimension ring buffers."""

    def __init__(
        self,
        cfg: MonitorConfig,
        pause_callback: Callable[
            [AlignmentDimension, str, float], Coroutine[Any, Any, None]
        ] | None = None,
    ) -> None:
        self._cfg = cfg
        self._pause_callback = pause_callback
        self._lock = asyncio.Lock()
        self._samples: dict[AlignmentDimension, dict[str, list[AlignmentSample]]] = (
            defaultdict(lambda: defaultdict(list))
        )
        self._active_alerts: dict[str, AlignmentAlert] = {}
        self._alert_history: list[AlignmentAlert] = []
        self._init_metrics()

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None: ...   # no background tasks needed
    async def stop(self) -> None: ...

    # ── ingest ───────────────────────────────────────────────────────────────

    async def record(self, sample: AlignmentSample) -> None:
        async with self._lock:
            buf = self._samples[sample.dimension][sample.agent_id]
            buf.append(sample)
            if len(buf) > self._cfg.max_samples_per_dim:
                buf.pop(0)
            await self._check_threshold(sample.dimension, sample.agent_id)
        ASI_ALIGNMENT_SAMPLES.labels(
            dimension=sample.dimension.value, agent_id=sample.agent_id
        ).inc()

    # ── window ───────────────────────────────────────────────────────────────

    def _compute_window(
        self, dimension: AlignmentDimension, agent_id: str, window_ms: int
    ) -> AlignmentWindow:
        now = time.monotonic()
        cutoff = now - window_ms / 1000.0
        recent = [
            s for s in self._samples[dimension].get(agent_id, [])
            if s.timestamp >= cutoff
        ]
        if not recent:
            # benefit of doubt — no evidence of misalignment
            return AlignmentWindow(dimension, agent_id, cutoff, now, 1.0, 1.0, 0)
        scores = [s.score for s in recent]
        return AlignmentWindow(
            dimension=dimension, agent_id=agent_id,
            window_start=cutoff, window_end=now,
            mean_score=sum(scores) / len(scores),
            min_score=min(scores),
            sample_count=len(scores),
        )

    async def window(
        self,
        dimension: AlignmentDimension,
        agent_id: str,
        window_ms: int | None = None,
    ) -> AlignmentWindow:
        async with self._lock:
            return self._compute_window(
                dimension, agent_id, window_ms or self._cfg.window_ms
            )

    # ── overall score (harmonic mean) ────────────────────────────────────────

    async def overall_score(self, agent_id: str) -> float:
        async with self._lock:
            scores = [
                self._compute_window(dim, agent_id, self._cfg.window_ms).mean_score
                for dim in AlignmentDimension
            ]
        if any(s == 0.0 for s in scores):
            return 0.0
        h = len(scores) / sum(1.0 / s for s in scores)
        ASI_ALIGNMENT_OVERALL.labels(agent_id=agent_id).set(h)
        return h

    # ── threshold check ──────────────────────────────────────────────────────

    async def _check_threshold(
        self, dimension: AlignmentDimension, agent_id: str
    ) -> None:
        w = self._compute_window(dimension, agent_id, self._cfg.window_ms)
        ASI_ALIGNMENT_SCORE.labels(
            dimension=dimension.value, agent_id=agent_id
        ).set(w.mean_score)

        if w.mean_score < self._cfg.critical_threshold:
            ASI_ALIGNMENT_CRITICAL.labels(dimension=dimension.value).inc()
            if self._cfg.pause_on_critical and self._pause_callback:
                await self._pause_callback(dimension, agent_id, w.mean_score)
            return

        if w.mean_score < self._cfg.alert_threshold:
            alert_id = f"{dimension.value}:{agent_id}:{w.window_end:.3f}"
            if alert_id not in self._active_alerts:
                alert = AlignmentAlert(
                    alert_id=alert_id,
                    dimension=dimension,
                    agent_id=agent_id,
                    mean_score=w.mean_score,
                    threshold=self._cfg.alert_threshold,
                    triggered_at=time.monotonic(),
                )
                self._active_alerts[alert_id] = alert
                ASI_ALIGNMENT_ALERTS.labels(dimension=dimension.value).inc()
        else:
            # check if any active alerts for this dimension/agent can be resolved
            to_resolve = [
                k for k, a in self._active_alerts.items()
                if a.dimension == dimension and a.agent_id == agent_id
            ]
            for k in to_resolve:
                resolved = AlignmentAlert(
                    **{**vars(self._active_alerts[k]),
                       "resolved_at": time.monotonic()}
                )
                self._alert_history.append(resolved)
                del self._active_alerts[k]

    # ── queries ──────────────────────────────────────────────────────────────

    async def active_alerts(self) -> list[AlignmentAlert]:
        async with self._lock:
            return list(self._active_alerts.values())

    async def alert_history(self, since_ts: float) -> list[AlignmentAlert]:
        async with self._lock:
            return [a for a in self._alert_history if a.triggered_at >= since_ts]

    async def snapshot(self) -> AlignmentSnapshot:
        # snapshot caller must hold no lock — overall_score acquires it
        windows = {}
        async with self._lock:
            for dim in AlignmentDimension:
                # pick first agent_id present (or "__default__")
                agent_ids = list(self._samples[dim].keys()) or ["__default__"]
                for aid in agent_ids:
                    windows[dim] = self._compute_window(dim, aid, self._cfg.window_ms)
        overall = await self.overall_score(agent_ids[0])
        return AlignmentSnapshot(
            agent_id=agent_ids[0],
            windows=windows,
            overall_score=overall,
            active_alert_count=len(self._active_alerts),
        )
```

---

## `AlignmentAwareSafetyFilter` — SafetyFilter → AlignmentMonitor bridge

```python
class AlignmentAwareSafetyFilter:
    """Wraps SafetyFilter — automatically records CONSTITUTIONAL dimension samples."""

    _SEVERITY_SCORE = {
        ViolationSeverity.INFO: 0.9,
        ViolationSeverity.WARN: 0.7,
        ViolationSeverity.BLOCK: 0.5,
        ViolationSeverity.CRITICAL: 0.2,
    }

    def __init__(
        self,
        inner: SafetyFilter,
        monitor: AlignmentMonitor,
        agent_id: str,
    ) -> None:
        self._inner = inner
        self._monitor = monitor
        self._agent_id = agent_id

    async def check_goal(self, goal: "Goal") -> SafetyVerdict:
        verdict = await self._inner.check_goal(goal)
        score = 1.0 if verdict.allowed else min(
            self._SEVERITY_SCORE.get(v.severity, 0.5)
            for v in verdict.violations
        )
        await self._monitor.record(AlignmentSample(
            dimension=AlignmentDimension.CONSTITUTIONAL,
            agent_id=self._agent_id,
            score=score,
            raw_value=float(not verdict.allowed),
            timestamp=time.monotonic(),
        ))
        return verdict

    async def check_subtask(self, subtask: "SubTask") -> SafetyVerdict:
        verdict = await self._inner.check_subtask(subtask)
        score = 1.0 if verdict.allowed else min(
            self._SEVERITY_SCORE.get(v.severity, 0.5)
            for v in verdict.violations
        )
        await self._monitor.record(AlignmentSample(
            dimension=AlignmentDimension.CONSTITUTIONAL,
            agent_id=self._agent_id,
            score=score,
            raw_value=float(not verdict.allowed),
            timestamp=time.monotonic(),
        ))
        return verdict
```

---

## Factory

```python
def build_alignment_monitor(
    cfg: MonitorConfig | None = None,
    pause_callback: Callable[
        [AlignmentDimension, str, float], Coroutine[Any, Any, None]
    ] | None = None,
) -> AlignmentMonitor:
    """Return a ready-to-use InMemoryAlignmentMonitor."""
    return InMemoryAlignmentMonitor(cfg or MonitorConfig(), pause_callback)
```

---

## Prometheus Metrics

```python
ASI_ALIGNMENT_SAMPLES = Counter(
    "asi_alignment_samples_total",
    "Alignment samples ingested",
    ["dimension", "agent_id"],
)
ASI_ALIGNMENT_SCORE = Gauge(
    "asi_alignment_score",
    "Current rolling window mean alignment score",
    ["dimension", "agent_id"],
)
ASI_ALIGNMENT_ALERTS = Counter(
    "asi_alignment_alerts_total",
    "Alignment alert events triggered",
    ["dimension"],
)
ASI_ALIGNMENT_CRITICAL = Counter(
    "asi_alignment_critical_total",
    "Critical threshold alignment breaches",
    ["dimension"],
)
ASI_ALIGNMENT_OVERALL = Gauge(
    "asi_alignment_overall_score",
    "Harmonic mean of all 5 alignment dimension scores",
    ["agent_id"],
)
```

**PromQL examples**:
```promql
# Per-dimension score for agent "asi-node-1"
asi_alignment_score{agent_id="asi-node-1"}

# Overall alignment health
asi_alignment_overall_score{agent_id="asi-node-1"}

# Alert rate (5 min)
rate(asi_alignment_alerts_total[5m])

# Critical breach rate
rate(asi_alignment_critical_total[5m])
```

**Grafana alert rule** (critical breach):
```yaml
alert: AlignmentCriticalBreach
expr: asi_alignment_overall_score < 0.50
for: 30s
severity: critical
```

---

## `mypy` strict mode compliance

| Symbol | Notes |
|--------|-------|
| `AlignmentSample` | `frozen=True`, all fields typed |
| `AlignmentWindow` | `frozen=True` |
| `AlignmentAlert` | `frozen=True`, `resolved_at: float \| None` |
| `AlignmentSnapshot` | `frozen=True`, `windows: dict[AlignmentDimension, AlignmentWindow]` |
| `MonitorConfig` | `frozen=True`, all defaults typed |
| `AlignmentMonitor` | `@runtime_checkable` Protocol |
| `InMemoryAlignmentMonitor` | passes `isinstance(m, AlignmentMonitor)` |
| `AlignmentAwareSafetyFilter` | wraps typed `SafetyFilter` Protocol |
| `pause_callback` | `Callable[[AlignmentDimension, str, float], Coroutine[Any, Any, None]] \| None` |

---

## Test Targets (12)

1. `test_record_increments_counter` — sample ingested, Prometheus counter +1
2. `test_window_empty_returns_1_0` — no samples → window mean = 1.0
3. `test_window_mean_score` — 5 samples at 0.8 → window mean = 0.8
4. `test_window_min_score` — mixed scores → min propagated correctly
5. `test_window_cutoff_excludes_old_samples` — samples outside window_ms ignored
6. `test_ring_buffer_eviction` — buffer capped at `max_samples_per_dim`
7. `test_alert_triggered_below_threshold` — mean < alert_threshold → alert in `active_alerts()`
8. `test_critical_triggers_pause_callback` — mean < critical_threshold → `pause_callback` awaited
9. `test_alert_resolves_when_score_recovers` — mean recovers → `resolved_at` set, moved to history
10. `test_overall_score_harmonic_mean` — 5 dims at 0.8 → harmonic mean = 0.8
11. `test_overall_score_zero_when_any_zero` — one dim at 0.0 → overall = 0.0
12. `test_alignment_aware_filter_records_constitutional_sample` — SafetyFilter BLOCK → CONSTITUTIONAL score 0.5

---

## `CognitiveCycle` integration

```python
class CognitiveCycle:
    def __init__(self, ..., alignment_monitor: AlignmentMonitor) -> None:
        ...
        self._alignment = alignment_monitor

    async def _tick(self) -> None:
        # Safety gate (pre-execution)
        verdict = await self._safety_filter.check_goal(self._current_goal)
        if not verdict.allowed:
            return

        # Execute plan...
        await self._plan_executor.execute(task_graph)

        # Continuous alignment check (post-tick)
        overall = await self._alignment.overall_score(self._agent_id)
        if overall < self._alignment_cfg.critical_threshold:
            await self._pause()
```

---

## Implementation Order (14 steps)

1. `AlignmentDimension` enum
2. `AlignmentSample` frozen dataclass
3. `AlignmentWindow` frozen dataclass
4. `AlignmentAlert` frozen dataclass
5. `AlignmentSnapshot` frozen dataclass
6. `MonitorConfig` frozen dataclass
7. `AlignmentMonitor` Protocol (`@runtime_checkable`)
8. `InMemoryAlignmentMonitor.__init__` — `asyncio.Lock`, ring buffers (`defaultdict`), Prometheus pre-init
9. `record()` + `_check_threshold()` — ingest + threshold evaluation
10. `_compute_window()` + `window()` — rolling mean/min
11. `overall_score()` — harmonic mean, Gauge update
12. `active_alerts()` + `alert_history()`
13. `snapshot()`
14. `AlignmentAwareSafetyFilter` + `build_alignment_monitor()` factory + `CognitiveCycle` integration

---

## Phase 11 Roadmap

| Sub-phase | Component | Status |
|-----------|-----------|--------|
| 11.1 | [SafetyFilter](Phase-11-Safety-Filter) — constitutional ruleset gating | ✅ Spec filed (#337) |
| 11.2 | AlignmentMonitor — continuous drift detection | 🟡 This page (#340) |
| 11.3 | ValueLearner — reward model from human feedback | 📋 Planned |
| 11.4 | InterpretabilityProbe — activation patching & steering | 📋 Planned |
| 11.5 | AlignmentDashboard — unified safety/alignment UI | 📋 Planned |
