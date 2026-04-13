# Phase 5: Memory Consolidation

This page documents the **MemoryConsolidator** component introduced in Phase 5, which runs during the `SLEEP_PHASE` tick of the `CognitiveCycle`. It handles the transfer of episodic short-term events to the long-term Knowledge Graph (KG), manages write-rate backpressure, and coordinates with the `EWCKernel` for catastrophic forgetting prevention.

Related: Issue #186, Discussion #232, wiki Phase-5-Online-Learning.md, wiki Phase-5-Safety-Invariants.md

---

## Overview

The ASI:BUILD memory subsystem uses a two-tier architecture:

```
              Cognitive Cycle tick
                       │
         ┌─────────────▼─────────────┐
         │     CognitiveCycle         │
         │  PERCEPTION → LEARNING    │
         │  → INTEGRATION → ...      │
         │  → ACTION                 │
         │  → [SLEEP_PHASE?]  ──────►│  MemoryConsolidator.consolidate()
         └───────────────────────────┘         │
                                               ▼
                                    ┌─────────────────────┐
                                    │   Short-term buffer  │
                                    │   (ring buffer /     │
                                    │    Blackboard deque) │
                                    └──────────┬──────────┘
                                               │ UNWIND batch
                                               ▼
                                    ┌─────────────────────┐
                                    │   Knowledge Graph    │
                                    │   (Memgraph /        │
                                    │    Neo4j Bolt)       │
                                    └─────────────────────┘
```

**SLEEP_PHASE trigger**: `SleepPhaseGuard.should_sleep()` returns `True` every N ticks (default: 200). Between sleep cycles, episodic events accumulate in a ring buffer on the Blackboard.

---

## EpisodicEvent Dataclass

```python
from dataclasses import dataclass, field
from typing import Any
import time

@dataclass
class EpisodicEvent:
    """A single episodic memory unit queued for KG consolidation."""
    subject:    str               # KG node label or URI
    predicate:  str               # Relationship type
    obj:        str               # Target node label or URI
    confidence: float = 1.0       # 0.0–1.0
    source:     str   = "cycle"   # originating module
    timestamp:  float = field(default_factory=time.monotonic)
    metadata:   dict[str, Any] = field(default_factory=dict)

    def to_cypher_params(self) -> dict[str, Any]:
        return {
            "subject":    self.subject,
            "predicate":  self.predicate,
            "obj":        self.obj,
            "confidence": self.confidence,
            "source":     self.source,
            "ts":         self.timestamp,
        }
```

Events are written to the Blackboard under the key `"sleep_phase:episodic_queue"` as a `deque[EpisodicEvent]`.

---

## MemoryConsolidator Interface

```python
from abc import ABC, abstractmethod
from collections import deque

class MemoryConsolidatorBase(ABC):
    @abstractmethod
    async def consolidate(self, bb: Blackboard) -> ConsolidationReport:
        """
        Drain the episodic queue and write to KG.
        Must be called only during SLEEP_PHASE.
        Returns a report with write counts and any errors.
        """
        ...

    @abstractmethod
    async def on_event(self, event: EpisodicEvent, bb: Blackboard) -> None:
        """
        Called during non-sleep ticks to enqueue a new episodic event.
        Must not block. If queue is full, apply backpressure strategy.
        """
        ...
```

```python
@dataclass
class ConsolidationReport:
    events_written: int
    events_dropped: int
    duration_ms:    float
    errors:         list[str] = field(default_factory=list)
```

---

## Write Rate Analysis

Based on the Phase 5 architecture (from Discussion #232):

| Source | Events per sleep cycle (200 ticks) | Notes |
|--------|------------------------------------|-------|
| STDPOnlineLearner (`LEARNING` phase) | 30–80 | Weight delta above threshold triggers event |
| MeshCoordinator task completions | 10–40 | One event per dispatched task |
| ConsciousnessPlanner goal updates | 5–20 | Goal acceptance/rejection events |
| Perception module novelty signals | 5–15 | New entity or relationship detected |
| **Total estimated** | **50–155 events** | Per 200-tick sleep window |

At 155 events per SLEEP_PHASE, a single UNWIND batch write to Memgraph takes ~15–30 ms (Bolt round-trip) — well within the SLEEP_PHASE budget.

---

## UNWIND Batch Pattern

Instead of N individual Cypher `MERGE` statements (N round-trips), consolidation uses a single parameterised `UNWIND`:

```cypher
UNWIND $events AS e
MERGE (s:Concept {name: e.subject})
MERGE (o:Concept {name: e.obj})
MERGE (s)-[r:RELATES {type: e.predicate}]->(o)
ON CREATE SET r.confidence = e.confidence,
              r.source     = e.source,
              r.created_at = e.ts
ON MATCH  SET r.confidence = (r.confidence + e.confidence) / 2.0,
              r.updated_at = e.ts
```

This reduces 155 round-trips to **1 round-trip**, achieving ~100× latency improvement for the consolidation step.

Implementation sketch:

```python
class MemoryConsolidator(MemoryConsolidatorBase):
    MAX_QUEUE_SIZE = 500  # backpressure threshold

    def __init__(self, driver: neo4j.AsyncDriver) -> None:
        self._driver = driver
        self._queue: deque[EpisodicEvent] = deque(maxlen=self.MAX_QUEUE_SIZE)

    async def consolidate(self, bb: Blackboard) -> ConsolidationReport:
        t0 = time.monotonic()
        # Drain Blackboard queue + internal queue
        bb_queue: deque = bb.get("sleep_phase:episodic_queue", deque())
        batch = list(self._queue) + list(bb_queue)
        self._queue.clear()
        bb_queue.clear()

        if not batch:
            return ConsolidationReport(0, 0, 0.0)

        params = [e.to_cypher_params() for e in batch]
        dropped = 0
        errors = []
        try:
            async with self._driver.session() as session:
                await session.run(UNWIND_QUERY, {"events": params})
        except Exception as exc:
            errors.append(str(exc))
            dropped = len(batch)
            batch = []

        return ConsolidationReport(
            events_written = len(batch) - dropped,
            events_dropped = dropped,
            duration_ms    = (time.monotonic() - t0) * 1000,
            errors         = errors,
        )
```

---

## Backpressure Strategy

When the episodic queue exceeds `MAX_QUEUE_SIZE` (default: 500 events) between sleep cycles, the consolidator must not block the live cycle. Mitigation options:

| Strategy | Mechanism | Trade-off |
|----------|-----------|-----------|
| **Drop oldest** (default) | `deque(maxlen=N)` auto-evicts oldest | Lose low-confidence older events |
| **Drop lowest confidence** | Sorted eviction `O(N)` on enqueue | Preserves salience, but costly |
| **Trigger early sleep** | Signal `SleepPhaseGuard` to advance | Disrupts cycle timing |
| **Background flush** | Async writer task, separate from cycle | Adds concurrency risk |

**Default recommendation**: `deque(maxlen=500)` (drop oldest). Combined with a Prometheus gauge `phase5_episodic_queue_depth` that alerts when depth > 400, operators get early warning before dropping starts.

If `SLEEP_PHASE` is skipped (e.g. due to a circuit-open condition in the rollback manager, Issue #216), the ring buffer absorbs up to 500 events. If the skip persists beyond 3 cycles (600 ticks), the Grafana alert `ASIPhase5SleepSkippedTooLong` fires (see Issue #225, wiki Phase-5-Grafana-Dashboard.md).

---

## SLEEP_PHASE Exclusivity

Per the safety invariants (wiki Phase-5-Safety-Invariants.md), no Blackboard write from `STDPOnlineLearner` or `MeshCoordinator` may occur **during** `MemoryConsolidator.consolidate()`. This is enforced by the `SleepPhaseGuard`:

```python
class SleepPhaseGuard:
    def __init__(self, period_ticks: int = 200) -> None:
        self._period = period_ticks
        self._tick   = 0
        self._sleeping = False

    def should_sleep(self) -> bool:
        self._tick += 1
        if self._tick >= self._period:
            self._tick = 0
            self._sleeping = True
            return True
        return False

    @property
    def is_sleeping(self) -> bool:
        return self._sleeping

    def wake(self) -> None:
        self._sleeping = False
```

`_phase5_dispatch()` sets `guard.wake()` after `consolidate()` completes, before the next `PERCEPTION` phase begins.

---

## Integration with EWC (Phase 6)

In Phase 6, `MemoryConsolidator.consolidate()` will be extended to update the diagonal Fisher information matrix used by `EWCKernel` (Discussion #234):

```
SLEEP_PHASE tick N:
  1. MemoryConsolidator.consolidate()         → write episodic events to KG
  2. EWCKernel.update_fisher(recent_weights)  → compute F_i for current task
  3. guard.wake()
```

This sequence ensures EWC constraints are freshly calibrated after each consolidation, protecting consolidated KG structure from being overwritten in the next wake cycle.

---

## Prometheus Metrics

| Metric | Type | Label | Description |
|--------|------|-------|-------------|
| `phase5_episodic_queue_depth` | Gauge | — | Current events in ring buffer |
| `phase5_consolidation_events_total` | Counter | `result={written,dropped}` | Cumulative events |
| `phase5_consolidation_duration_seconds` | Histogram | — | UNWIND batch latency |
| `phase5_sleep_phase_total` | Counter | — | Number of SLEEP_PHASE activations |
| `phase5_sleep_skipped_total` | Counter | `reason` | Times SLEEP_PHASE was skipped |

Defined in `Phase5MetricsExporter` (Issue #220, wiki Phase-5-Prometheus-Integration.md).

---

## Test Targets

```python
# tests/test_memory_consolidator.py

async def test_consolidate_empty_queue_is_noop()
async def test_consolidate_writes_unwind_batch()
async def test_consolidate_drains_blackboard_queue()
async def test_consolidate_returns_report_with_counts()
async def test_backpressure_drops_oldest_when_full()
async def test_consolidate_handles_driver_error_gracefully()
async def test_sleep_phase_guard_period()
async def test_sleep_phase_guard_wake_resets_sleeping()
async def test_no_writes_during_sleep_phase()  # SleepPhaseGuard.is_sleeping check
async def test_consolidation_report_prometheus_labels()
```

---

## Related

- Issue #186 — MemoryConsolidator tracker issue
- Discussion #232 — KG write rates and backpressure design thread
- Issue #216 — Phase 5 rollback manager (circuit-open skips SLEEP_PHASE)
- Issue #220 — Phase 5 Prometheus metrics layer
- Issue #225 — Phase 5 Grafana dashboard (sleep skipped alert)
- Issue #233 — `_phase5_dispatch()` wiring (calls `consolidate()`)
- Issue #235 — `CyclePhase.SLEEP_PHASE` enum addition
- Discussion #234 — EWC kernel strategy (Phase 6 Fisher integration)
- Wiki: Phase-5-Safety-Invariants.md
- Wiki: Phase-5-Online-Learning.md
- Wiki: Phase-5-Rollback-Runbook.md
- Wiki: Phase-5-Prometheus-Integration.md
- Wiki: Phase-5-Grafana-Dashboard.md
