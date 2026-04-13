# Phase 18.5 — TemporalCoherenceArbiter

> **Unified clock & multi-source temporal coherence arbitration — resolves conflicts from distributed sync.**
>
> Issue: [#460](https://github.com/web3guru888/asi-build/issues/460) | Show & Tell: [#461](https://github.com/web3guru888/asi-build/discussions/461) | Q&A: [#464](https://github.com/web3guru888/asi-build/discussions/464)

---

## Overview

The `TemporalCoherenceArbiter` is the **capstone component of Phase 18**. It unifies clock signals from heterogeneous temporal sources — local monotonic clocks, vector clocks from DistributedTemporalSync, external NTP, and peer gossip timestamps — into a single **coherence-verified unified clock** that the entire cognitive pipeline can trust.

| Field | Value |
|---|---|
| **Phase** | 18 — Temporal Intelligence & Memory Consolidation |
| **Sub-phase** | 18.5 (final) |
| **Module** | `asi_build/temporal/coherence_arbiter.py` |
| **Test** | `tests/temporal/test_coherence_arbiter.py` |
| **Dependencies** | Phase 18.3 DistributedTemporalSync (#456), Phase 17.5 TemporalOrchestrator (#446) |

---

## 1 — Public Enums

```python
from enum import Enum, auto

class CoherenceVerdict(Enum):
    """Outcome of a coherence arbitration round."""
    COHERENT       = auto()  # All sources agree within max_drift_ns
    DRIFT_DETECTED = auto()  # Some sources drifted but resolvable
    CONFLICT       = auto()  # Sources disagree within conflict_window_ns — resolved by policy
    UNRESOLVABLE   = auto()  # Cannot produce a trustworthy unified clock
```

**Verdict decision flow:**

```
drift ≤ max_drift_ns           → COHERENT
drift ≤ conflict_window_ns     → DRIFT_DETECTED
drift > conflict_window_ns     → CONFLICT (if enough clean sources remain)
                               → UNRESOLVABLE (if too many conflicts)
```

---

## 2 — Frozen Dataclasses

### ClockSource

```python
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ClockSource:
    """A single clock reading from one temporal source."""
    source_id: str                          # e.g. "local_monotonic", "peer_alpha_vector", "ntp_pool"
    clock_type: str                         # "monotonic" | "vector" | "ntp" | "wall"
    timestamp_ns: int                       # Nanosecond-precision timestamp
    confidence: float                       # 0.0–1.0 — trust weight for this source
    metadata: dict = field(default_factory=dict)  # Opaque extra data (vector clock payload, RTT, etc.)
```

### ArbiterConfig

```python
@dataclass(frozen=True)
class ArbiterConfig:
    """Tuning knobs for the arbiter."""
    max_drift_ns: int       = 50_000_000    # 50 ms — beyond this, DRIFT_DETECTED
    conflict_window_ns: int = 200_000_000   # 200 ms — beyond this, CONFLICT
    min_sources: int        = 2             # Minimum sources for arbitration
    decay_rate: float       = 0.95          # Per-tick confidence decay for stale sources
    tick_interval_s: float  = 1.0           # Background tick frequency
```

### CoherenceReport

```python
from typing import FrozenSet

@dataclass(frozen=True)
class CoherenceReport:
    """Result of an arbitration round."""
    verdict: CoherenceVerdict
    unified_timestamp_ns: int               # Weighted median fused clock
    drift_ns: int                           # Max observed drift across sources
    conflicting_sources: FrozenSet[str]     # source_ids that disagree (empty if COHERENT)
    resolution_notes: str                   # Human-readable summary
```

---

## 3 — Protocol (runtime-checkable)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class TemporalCoherenceArbiter(Protocol):
    """Arbitrates temporal coherence across multiple clock sources."""

    async def register_source(self, source_id: str, clock_type: str, initial_confidence: float = 1.0) -> None:
        """Register a new clock source."""
        ...

    async def unregister_source(self, source_id: str) -> None:
        """Remove a clock source."""
        ...

    async def report_clock(self, source: ClockSource) -> None:
        """Submit a clock reading."""
        ...

    async def arbitrate(self) -> CoherenceReport:
        """Run one arbitration round — fuse clocks, detect drift/conflicts."""
        ...

    async def get_unified_clock(self) -> int:
        """Return the latest unified timestamp_ns."""
        ...

    async def check_coherence(self) -> CoherenceVerdict:
        """Quick coherence check without full report."""
        ...

    async def start(self) -> None:
        """Start background tick loop."""
        ...

    async def stop(self) -> None:
        """Stop background tick loop."""
        ...
```

---

## 4 — AsyncTemporalCoherenceArbiter (Production)

```python
import asyncio
import time
from typing import Dict, Optional

class AsyncTemporalCoherenceArbiter:
    """Production implementation — weighted median clock fusion + coherence arbitration."""

    def __init__(self, config: ArbiterConfig | None = None) -> None:
        self._config = config or ArbiterConfig()
        self._sources: Dict[str, ClockSource] = {}
        self._registered: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._last_report: Optional[CoherenceReport] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    # ── Source Management ──

    async def register_source(self, source_id: str, clock_type: str, initial_confidence: float = 1.0) -> None:
        async with self._lock:
            self._registered[source_id] = initial_confidence
            _active_sources.set(len(self._registered))

    async def unregister_source(self, source_id: str) -> None:
        async with self._lock:
            self._registered.pop(source_id, None)
            self._sources.pop(source_id, None)
            _active_sources.set(len(self._registered))

    async def report_clock(self, source: ClockSource) -> None:
        async with self._lock:
            if source.source_id not in self._registered:
                raise ValueError(f"Unknown source: {source.source_id}")
            self._sources[source.source_id] = source

    # ── Core Arbitration ──

    async def arbitrate(self) -> CoherenceReport:
        t0 = time.monotonic()
        async with self._lock:
            report = self._do_arbitrate()
            self._last_report = report
        elapsed = time.monotonic() - t0
        _arbitration_latency.observe(elapsed)
        _coherence_verdicts.labels(verdict=report.verdict.name).inc()
        _drift_nanoseconds.set(report.drift_ns)
        if report.verdict == CoherenceVerdict.CONFLICT:
            _conflict_total.inc(len(report.conflicting_sources))
        return report

    def _do_arbitrate(self) -> CoherenceReport:
        readings = list(self._sources.values())
        if len(readings) < self._config.min_sources:
            return CoherenceReport(
                verdict=CoherenceVerdict.UNRESOLVABLE,
                unified_timestamp_ns=readings[0].timestamp_ns if readings else 0,
                drift_ns=0,
                conflicting_sources=frozenset(),
                resolution_notes=f"Insufficient sources: {len(readings)} < {self._config.min_sources}",
            )

        # Weighted median fusion
        unified_ns = self._weighted_median(readings)

        # Drift detection
        drifts = {r.source_id: abs(r.timestamp_ns - unified_ns) for r in readings}
        max_drift = max(drifts.values())

        # Conflict detection
        conflicting = frozenset(
            sid for sid, d in drifts.items() if d > self._config.conflict_window_ns
        )

        # Verdict determination
        if conflicting:
            if len(conflicting) >= len(readings) - 1:
                verdict = CoherenceVerdict.UNRESOLVABLE
                notes = f"Too many conflicts ({len(conflicting)}/{len(readings)})"
            else:
                verdict = CoherenceVerdict.CONFLICT
                notes = f"Resolved conflict from {len(conflicting)} source(s) via weighted median exclusion"
                clean = [r for r in readings if r.source_id not in conflicting]
                if clean:
                    unified_ns = self._weighted_median(clean)
        elif max_drift > self._config.max_drift_ns:
            verdict = CoherenceVerdict.DRIFT_DETECTED
            notes = f"Max drift {max_drift}ns exceeds threshold {self._config.max_drift_ns}ns"
        else:
            verdict = CoherenceVerdict.COHERENT
            notes = f"All {len(readings)} sources within {self._config.max_drift_ns}ns tolerance"

        return CoherenceReport(
            verdict=verdict,
            unified_timestamp_ns=unified_ns,
            drift_ns=max_drift,
            conflicting_sources=conflicting,
            resolution_notes=notes,
        )

    @staticmethod
    def _weighted_median(readings: list[ClockSource]) -> int:
        """Confidence-weighted median — sort by timestamp, walk cumulative weight to 0.5."""
        sorted_r = sorted(readings, key=lambda r: r.timestamp_ns)
        total_weight = sum(r.confidence for r in sorted_r)
        if total_weight == 0:
            return sorted_r[len(sorted_r) // 2].timestamp_ns
        cumulative = 0.0
        for r in sorted_r:
            cumulative += r.confidence
            if cumulative >= total_weight * 0.5:
                return r.timestamp_ns
        return sorted_r[-1].timestamp_ns

    # ── Quick Accessors ──

    async def get_unified_clock(self) -> int:
        async with self._lock:
            return self._last_report.unified_timestamp_ns if self._last_report else 0

    async def check_coherence(self) -> CoherenceVerdict:
        async with self._lock:
            return self._last_report.verdict if self._last_report else CoherenceVerdict.UNRESOLVABLE

    # ── Background Tick Loop ──

    async def start(self) -> None:
        self._stop_event.clear()
        self._task = asyncio.create_task(self._tick_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            await self._task
            self._task = None

    async def _tick_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._config.tick_interval_s)
                break
            except asyncio.TimeoutError:
                pass
            self._decay_stale_sources()
            await self.arbitrate()

    def _decay_stale_sources(self) -> None:
        """Apply decay_rate to sources that haven't reported recently."""
        now_ns = time.monotonic_ns()
        for sid, src in list(self._sources.items()):
            age_ns = now_ns - src.timestamp_ns
            if age_ns > self._config.tick_interval_s * 2 * 1_000_000_000:
                decayed = src.confidence * self._config.decay_rate
                self._sources[sid] = ClockSource(
                    source_id=src.source_id,
                    clock_type=src.clock_type,
                    timestamp_ns=src.timestamp_ns,
                    confidence=max(decayed, 0.01),
                    metadata=src.metadata,
                )
```

---

## 5 — NullTemporalCoherenceArbiter

```python
class NullTemporalCoherenceArbiter:
    """No-op implementation for testing / DI."""

    async def register_source(self, source_id: str, clock_type: str, initial_confidence: float = 1.0) -> None: ...
    async def unregister_source(self, source_id: str) -> None: ...
    async def report_clock(self, source: ClockSource) -> None: ...
    async def arbitrate(self) -> CoherenceReport:
        return CoherenceReport(CoherenceVerdict.COHERENT, 0, 0, frozenset(), "null")
    async def get_unified_clock(self) -> int: return 0
    async def check_coherence(self) -> CoherenceVerdict: return CoherenceVerdict.COHERENT
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

---

## 6 — Factory

```python
def make_temporal_coherence_arbiter(
    *, config: ArbiterConfig | None = None, null: bool = False,
) -> TemporalCoherenceArbiter:
    if null:
        return NullTemporalCoherenceArbiter()
    return AsyncTemporalCoherenceArbiter(config=config)
```

---

## 7 — Architecture: Clock Fusion Pipeline

```
              ┌──────────────────┐
              │  Clock Sources   │
              └────────┬─────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ Local    │  │ Vector   │  │ NTP /    │
  │ Monotonic│  │ Clock    │  │ Wall     │
  │ (1.0)    │  │ (0.8)    │  │ (0.6)    │
  └────┬─────┘  └────┬─────┘  └────┬─────┘
       │              │              │
       ▼              ▼              ▼
  ┌──────────────────────────────────────┐
  │       report_clock(ClockSource)      │
  │                                      │
  │   ┌──────────────────────────────┐   │
  │   │  Weighted Median Fusion      │   │
  │   │  Sort by timestamp_ns        │   │
  │   │  Walk cumulative confidence  │   │
  │   │  Pick median at 50% weight   │   │
  │   └──────────────┬───────────────┘   │
  │                  │                   │
  │   ┌──────────────▼───────────────┐   │
  │   │  Drift & Conflict Detection  │   │
  │   │  🟢 ≤ max_drift_ns          │   │
  │   │  🟡 ≤ conflict_window_ns    │   │
  │   │  🔴 > conflict_window_ns    │   │
  │   └──────────────┬───────────────┘   │
  │                  │                   │
  │   ┌──────────────▼───────────────┐   │
  │   │  CoherenceVerdict            │   │
  │   │  COHERENT | DRIFT_DETECTED   │   │
  │   │  CONFLICT | UNRESOLVABLE     │   │
  │   └──────────────┬───────────────┘   │
  │                  │                   │
  │   AsyncTemporalCoherenceArbiter      │
  └──────────────────┬───────────────────┘
                     │
                     ▼
            unified_timestamp_ns
            ──────────────────→ TemporalOrchestrator → CognitiveCycle
```

---

## 8 — Weighted Median: Worked Example

```
3 sources report timestamps (ns):
  Local  (confidence=1.0): 1,000,000,000
  Vector (confidence=0.8): 1,000,050,000   ← 50μs drift (normal)
  NTP    (confidence=0.6): 5,000,000,000   ← ROGUE (5s ahead!)

Weighted mean:   2,333,350,000  ← corrupted by rogue
Weighted median: 1,000,050,000  ← resilient!

Steps:
  total_weight = 1.0 + 0.8 + 0.6 = 2.4
  threshold    = 2.4 × 0.5 = 1.2

  Sort by timestamp_ns:
    Local  (1.0B, w=1.0) → cumulative = 1.0 (< 1.2)
    Vector (1.0B, w=0.8) → cumulative = 1.8 (≥ 1.2) ✓ ← PICK
    NTP    (5.0B, w=0.6) → skipped

  Result: unified_timestamp_ns = 1,000,050,000
```

---

## 9 — Coherence State Machine

```
                    ┌─────────┐
         ┌─────────│  START   │
         │         └────┬─────┘
         │              │ arbitrate()
         │              ▼
         │    ┌───────────────────┐    all within max_drift_ns
         │    │ Evaluate Drifts   │──────────────────────────→ COHERENT ✅
         │    └────────┬──────────┘
         │             │ some > max_drift_ns
         │             ▼
         │    ┌───────────────────┐    all within conflict_window_ns
         │    │ Check Conflicts   │──────────────────────────→ DRIFT_DETECTED ⚠️
         │    └────────┬──────────┘
         │             │ some > conflict_window_ns
         │             ▼
         │    ┌───────────────────┐    enough clean sources
         │    │ Exclude & Re-fuse │──────────────────────────→ CONFLICT 🔶
         │    └────────┬──────────┘
         │             │ too many conflicts
         │             ▼
         │         UNRESOLVABLE 🔴
         │              │
         └──────────────┘  (next tick)
```

---

## 10 — Background Tick Loop Lifecycle

```
start()
  │
  ▼
┌─────────────────────────────┐
│ _tick_loop (asyncio.Task)   │
│                             │
│ ┌─────────────────────────┐ │
│ │ wait_for(stop, timeout) │◄┼─── tick_interval_s (1.0s)
│ └──────────┬──────────────┘ │
│            │ timeout         │
│            ▼                 │
│ ┌─────────────────────────┐ │
│ │ _decay_stale_sources()  │ │
│ │ Apply decay_rate to     │ │
│ │ sources not reported    │ │
│ │ in 2×tick_interval_s    │ │
│ └──────────┬──────────────┘ │
│            │                 │
│            ▼                 │
│ ┌─────────────────────────┐ │
│ │ arbitrate()             │ │
│ │ Full weighted median +  │ │
│ │ verdict + metrics       │ │
│ └──────────┬──────────────┘ │
│            │                 │
│            └───→ loop ───────┤
│                              │
│ stop_event.set() → break     │
└──────────────────────────────┘
  │
  ▼
stop()  ← await task
```

---

## 11 — Integration Map

### DistributedTemporalSync (18.3) → TemporalCoherenceArbiter (18.5)

```python
# Inside DistributedTemporalSync.receive_push():
async def receive_push(self, peer_id: str, edges: list, peer_clock: VectorClock) -> None:
    # ... existing apply_edges logic ...

    # Bridge to coherence arbiter
    await self._arbiter.report_clock(ClockSource(
        source_id=f"peer_{peer_id}_vector",
        clock_type="vector",
        timestamp_ns=max(peer_clock.clocks.values()),
        confidence=0.8,
        metadata={"vector_clock": dict(peer_clock.clocks)},
    ))
```

### TemporalOrchestrator (17.5) → TemporalCoherenceArbiter (18.5)

```python
# Inside TemporalOrchestrator.run_cycle():
verdict = await self._arbiter.check_coherence()
if verdict == CoherenceVerdict.UNRESOLVABLE:
    logger.warning("Skipping temporal step — clock coherence unresolvable")
    return
unified_ns = await self._arbiter.get_unified_clock()
# proceed with canonical timestamp
```

### Full Phase 18 Integration Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 18 Complete Stack                       │
│                                                                 │
│  ┌──────────────┐    ┌───────────────────┐    ┌──────────────┐ │
│  │ HorizonPlan. │◄───│ MemoryConsolid.   │◄───│ Temporal     │ │
│  │ 18.1 (#450)  │    │ 18.2 (#453)       │    │ Graph 17.1   │ │
│  └──────┬───────┘    └────────┬──────────┘    └──────┬───────┘ │
│         │                     │                      │         │
│         │            ┌────────▼──────────┐           │         │
│         │            │ DistributedTemp.   │◄──────────┘         │
│         │            │ Sync 18.3 (#456)  │                     │
│         │            └────────┬──────────┘                     │
│         │                     │ vector clocks                  │
│         │            ┌────────▼──────────┐                     │
│         │            │ CausalMemory      │                     │
│         │            │ Index 18.4        │                     │
│         │            └────────┬──────────┘                     │
│         │                     │                                │
│         │    ┌────────────────▼─────────────────┐              │
│         └───►│ TemporalCoherenceArbiter 18.5    │◄─────────────┤
│              │ #460 — THIS COMPONENT            │   local clk  │
│              │ Unified clock + coherence verdicts│              │
│              └────────────────┬─────────────────┘              │
│                               │                                │
│                    unified_timestamp_ns                         │
│                               │                                │
│              ┌────────────────▼─────────────────┐              │
│              │ TemporalOrchestrator 17.5 (#446) │              │
│              │ Consumes unified clock for        │              │
│              │ CognitiveCycle temporal step       │              │
│              └──────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12 — Prometheus Metrics

| # | Metric | Type | Labels | Description |
|---|--------|------|--------|-------------|
| 1 | `asi_coherence_verdicts_total` | Counter | `verdict` | Arbitration outcomes by verdict type |
| 2 | `asi_drift_nanoseconds` | Gauge | — | Current max observed drift across sources |
| 3 | `asi_arbitration_latency_seconds` | Histogram | — | Wall-clock time per arbitration round |
| 4 | `asi_coherence_active_sources` | Gauge | — | Number of registered clock sources |
| 5 | `asi_coherence_conflict_total` | Counter | — | Cumulative conflicting source readings |

### PromQL Examples

```promql
# Conflict rate over 5m
rate(asi_coherence_conflict_total[5m])

# Coherence success ratio
sum(rate(asi_coherence_verdicts_total{verdict="COHERENT"}[10m]))
/ sum(rate(asi_coherence_verdicts_total[10m]))

# Drift alert threshold
asi_drift_nanoseconds > 100000000
```

### Grafana Alerts

```yaml
- alert: TemporalCoherenceDegraded
  expr: asi_drift_nanoseconds > 100000000
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Temporal drift exceeds 100ms for 2+ minutes"

- alert: TemporalCoherenceUnresolvable
  expr: increase(asi_coherence_verdicts_total{verdict="UNRESOLVABLE"}[5m]) > 3
  labels:
    severity: critical
  annotations:
    summary: "Multiple UNRESOLVABLE verdicts — clock sources severely diverged"

- alert: TemporalSourcesLow
  expr: asi_coherence_active_sources < 2
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Fewer than 2 clock sources registered — arbitration cannot function"
```

---

## 13 — mypy Strict Compliance

| Pattern | Narrowing technique |
|---------|---------------------|
| `self._last_report` access | `if self._last_report is not None` guard |
| `ClockSource.metadata` dict | `field(default_factory=dict)` — no mutable default |
| `_weighted_median` return | Explicit `int` return type + fallback branch |
| `_task` lifecycle | `Optional[asyncio.Task]` with `None` checks |
| `FrozenSet[str]` return | `frozenset(...)` constructor ensures immutable |
| `readings` empty list | Early return before `_weighted_median` (min_sources guard) |

---

## 14 — Test Targets (12)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_register_and_report_single_source` | register_source + report_clock round-trip |
| 2 | `test_arbitrate_coherent_within_threshold` | All sources within max_drift_ns → COHERENT |
| 3 | `test_arbitrate_drift_detected` | One source beyond max_drift_ns → DRIFT_DETECTED |
| 4 | `test_arbitrate_conflict_detected` | Source beyond conflict_window_ns → CONFLICT |
| 5 | `test_arbitrate_unresolvable_too_few_sources` | < min_sources → UNRESOLVABLE |
| 6 | `test_arbitrate_unresolvable_too_many_conflicts` | Almost all sources conflicting → UNRESOLVABLE |
| 7 | `test_weighted_median_respects_confidence` | High-confidence source dominates median |
| 8 | `test_confidence_decay_on_stale_source` | Stale source confidence decayed by decay_rate |
| 9 | `test_unregister_source_removes_from_arbitration` | Unregistered source excluded from next arbitrate |
| 10 | `test_background_tick_loop_periodic_arbitration` | start()/stop() lifecycle + at least 2 arbitrations |
| 11 | `test_null_arbiter_returns_coherent` | NullTemporalCoherenceArbiter always COHERENT |
| 12 | `test_factory_null_flag` | make_temporal_coherence_arbiter(null=True) returns Null impl |

### Test Skeletons

```python
import asyncio
import pytest
from asi_build.temporal.coherence_arbiter import (
    AsyncTemporalCoherenceArbiter,
    ArbiterConfig,
    ClockSource,
    CoherenceVerdict,
)


@pytest.mark.asyncio
async def test_weighted_median_respects_confidence():
    """High-confidence source should dominate the weighted median."""
    arbiter = AsyncTemporalCoherenceArbiter(
        config=ArbiterConfig(max_drift_ns=100_000_000, min_sources=2)
    )
    await arbiter.register_source("high", "monotonic", initial_confidence=0.9)
    await arbiter.register_source("low", "monotonic", initial_confidence=0.1)

    await arbiter.report_clock(ClockSource("high", "monotonic", 1_000_000_000, 0.9))
    await arbiter.report_clock(ClockSource("low", "monotonic", 2_000_000_000, 0.1))

    report = await arbiter.arbitrate()
    assert report.unified_timestamp_ns == 1_000_000_000
    assert report.verdict == CoherenceVerdict.COHERENT


@pytest.mark.asyncio
async def test_background_tick_loop_periodic_arbitration():
    """start()/stop() lifecycle should produce at least 2 arbitration rounds."""
    arbiter = AsyncTemporalCoherenceArbiter(
        config=ArbiterConfig(tick_interval_s=0.1, min_sources=1)
    )
    await arbiter.register_source("local", "monotonic")
    await arbiter.report_clock(ClockSource("local", "monotonic", 1_000_000_000, 1.0))

    await arbiter.start()
    await asyncio.sleep(0.35)
    await arbiter.stop()

    verdict = await arbiter.check_coherence()
    assert verdict != CoherenceVerdict.UNRESOLVABLE
```

---

## 15 — Implementation Order (14 steps)

1. Create `asi_build/temporal/coherence_arbiter.py`
2. Define `CoherenceVerdict` enum
3. Define `ClockSource`, `ArbiterConfig`, `CoherenceReport` frozen dataclasses
4. Define `TemporalCoherenceArbiter` Protocol
5. Implement `NullTemporalCoherenceArbiter`
6. Implement `AsyncTemporalCoherenceArbiter.__init__`
7. Implement `register_source` / `unregister_source`
8. Implement `report_clock`
9. Implement `_weighted_median` static method
10. Implement `_do_arbitrate` (drift detection, conflict detection, verdict)
11. Implement `arbitrate` wrapper with Prometheus instrumentation
12. Implement `_decay_stale_sources` + `_tick_loop` + `start`/`stop`
13. Implement `make_temporal_coherence_arbiter` factory
14. Write all 12 tests in `tests/temporal/test_coherence_arbiter.py`

---

## 🎉 Phase 18 — COMPLETE Tracker

| Sub-phase | Component | Issue | Wiki | Status |
|-----------|-----------|-------|------|--------|
| 18.1 | HorizonPlanner | [#450](https://github.com/web3guru888/asi-build/issues/450) | [Wiki](Phase-18-Horizon-Planner) | ✅ Spec'd |
| 18.2 | MemoryConsolidator | [#453](https://github.com/web3guru888/asi-build/issues/453) | [Wiki](Phase-18-Memory-Consolidator) | ✅ Spec'd |
| 18.3 | DistributedTemporalSync | [#456](https://github.com/web3guru888/asi-build/issues/456) | [Wiki](Phase-18-Distributed-Temporal-Sync) | ✅ Spec'd |
| 18.4 | CausalMemoryIndex | — | [Wiki](Phase-18-Causal-Memory-Index) | ✅ Spec'd |
| **18.5** | **TemporalCoherenceArbiter** | [**#460**](https://github.com/web3guru888/asi-build/issues/460) | **this page** | **✅ Spec'd** |

**🎉🎉🎉 Phase 18 "Temporal Intelligence & Memory Consolidation" is COMPLETE!**

All five sub-phases have been fully specified with Protocol definitions, production + null implementations, factory functions, Prometheus metrics, and test targets.

---

*See also: [Phase 17 — TemporalOrchestrator](Phase-17-Temporal-Orchestrator) | [Phase 18 Planning Discussion (#449)](https://github.com/web3guru888/asi-build/discussions/449)*
