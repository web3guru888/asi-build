# Phase 17.2 — `EventSequencer` 🕐

**Phase**: 17 — Temporal Reasoning & Predictive Cognition
**Component**: `EventSequencer`
**Issue**: [#437](https://github.com/web3guru888/asi-build/issues/437)
**Depends on**: Phase 17.1 `TemporalGraph` ([#434](https://github.com/web3guru888/asi-build/issues/434)), Phase 13 `WorldModel`, Phase 16 `ReflectionCycle` ([#430](https://github.com/web3guru888/asi-build/issues/430))

---

## Motivation

`TemporalGraph` stores Allen-relation edges between cognitive events, but it needs a **time-ordered, causally-validated stream** to feed it. Raw events emitted by `CognitiveCycle` modules arrive concurrently and potentially out-of-order. `EventSequencer` is the gatekeeper: it buffers, reorders, validates causal chains, and windows events before handing them off to `TemporalGraph.add_node()`.

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    CognitiveCycle._run_step()                    │
│                                                                  │
│  module_a.run() ──┐                                             │
│  module_b.run() ──┼──► emit CognitiveEvent(ts=T, parent=P) ──► │
│  module_c.run() ──┘                                             │
└──────────────────────────────────┬──────────────────────────────┘
                                   │  raw, unordered events
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                    AsyncEventSequencer                            │
│                                                                  │
│   ingest(event)                                                  │
│     ├── causal_check: parent_id ∈ seen_ids? ──► violation cnt   │
│     ├── overflow check: len(heap) >= max_buffer ──► LRU evict   │
│     ├── heapq.heappush(heap, event)  [O(log n)]                 │
│     └── _accumulate_window(event)   [bucket assignment]          │
│                                                                  │
│   drain()  [called from CognitiveCycle]                          │
│     └── while heap: yield heapq.heappop(heap)  [timestamp order] │
│                                                                  │
│   flush_windows()  [called periodically]                         │
│     └── return completed WindowedAggregates                      │
└──────────┬──────────────────────────┬───────────────────────────┘
           │ ordered CognitiveEvents  │ WindowedAggregates
           ▼                          ▼
┌─────────────────────┐   ┌──────────────────────────┐
│   TemporalGraph     │   │     PredictiveEngine      │
│  .add_node(e.id,    │   │   (Phase 17.3)            │
│   e.timestamp_ns)   │   │  consumes window batches  │
└─────────────────────┘   └──────────────────────────┘
```

---

## `OrderPolicy` Enum

```python
from enum import Enum, auto

class OrderPolicy(Enum):
    STRICT      = auto()  # reject any out-of-order event (causal_check=True required)
    RELAXED     = auto()  # reorder up to max_buffer depth before emitting
    BEST_EFFORT = auto()  # emit as-arrived, reorder opportunistically
```

### OrderPolicy Behaviour Table

| Policy | Out-of-order event | Causal violation | Use case |
|---|---|---|---|
| `STRICT` | ❌ Dropped immediately | ❌ Dropped, counter++ | Safety-critical decision loops |
| `RELAXED` | ✅ Reordered in heapq | ⚠️ Accepted, counter++ | Standard cognitive pipeline |
| `BEST_EFFORT` | ✅ Accepted as-arrived | ✅ Ignored | Telemetry / low-priority events |

---

## Frozen Dataclasses

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping

@dataclass(frozen=True)
class CognitiveEvent:
    event_id:         str
    source_module:    str
    event_type:       str
    payload:          Mapping[str, Any]
    timestamp_ns:     int                   # monotonic nanoseconds (no float rounding)
    causal_parent_id: str | None = None     # event_id of causal predecessor

    def __lt__(self, other: "CognitiveEvent") -> bool:
        return self.timestamp_ns < other.timestamp_ns


@dataclass(frozen=True)
class WindowedAggregate:
    window_id:   str                  # f"{start_ns}_{end_ns}"
    start_ns:    int
    end_ns:      int
    event_count: int
    event_types: frozenset[str]
    summary:     Mapping[str, Any]    # module → count, dominant event_type, etc.


@dataclass(frozen=True)
class SequencerConfig:
    window_size_ms:    int          = 500             # tumbling window width in milliseconds
    max_buffer:        int          = 10_000          # maximum heapq depth before eviction
    causal_check:      bool         = True            # validate causal_parent_id chain
    drop_out_of_order: bool         = False           # False→reorder, True→drop
    order_policy:      OrderPolicy  = field(default=OrderPolicy.RELAXED)
```

---

## Protocol

```python
from typing import AsyncIterator, Protocol, runtime_checkable

@runtime_checkable
class EventSequencer(Protocol):
    async def ingest(self, event: CognitiveEvent) -> bool:
        """Buffer event; returns True if accepted, False if dropped."""
        ...

    async def drain(self) -> AsyncIterator[CognitiveEvent]:
        """Yield events in timestamp_ns order until buffer empty."""
        ...

    def get_window(self, window_id: str) -> WindowedAggregate | None:
        """Return accumulated window by ID, or None if not found."""
        ...

    def flush_windows(self) -> list[WindowedAggregate]:
        """Flush and return all completed windows."""
        ...

    def stats(self) -> dict[str, int | float]:
        """Return buffer_size, dropped, causal_violations, windows_flushed."""
        ...
```

---

## Implementation: `AsyncEventSequencer`

```python
import asyncio
import heapq
import time
from collections import defaultdict
from typing import AsyncIterator

class AsyncEventSequencer:
    def __init__(self, config: SequencerConfig) -> None:
        self._cfg = config
        self._heap: list[CognitiveEvent] = []          # min-heap by timestamp_ns
        self._lock = asyncio.Lock()
        self._seen_ids: set[str] = set()               # for causal parent validation
        self._windows: dict[str, dict] = {}            # window_id → accumulator
        self._window_size_ns = config.window_size_ms * 1_000_000
        # counters
        self._ingested    = 0
        self._dropped     = 0
        self._causal_viol = 0
        self._windows_flushed = 0

    async def ingest(self, event: CognitiveEvent) -> bool:
        async with self._lock:
            # causal check
            if self._cfg.causal_check and event.causal_parent_id is not None:
                if event.causal_parent_id not in self._seen_ids:
                    self._causal_viol += 1
                    if self._cfg.order_policy == OrderPolicy.STRICT:
                        self._dropped += 1
                        return False

            # buffer overflow → LRU eviction (drop oldest)
            if len(self._heap) >= self._cfg.max_buffer:
                heapq.heappop(self._heap)   # evict smallest timestamp
                self._dropped += 1

            heapq.heappush(self._heap, event)
            self._seen_ids.add(event.event_id)
            self._ingested += 1
            self._accumulate_window(event)
            return True

    def _accumulate_window(self, event: CognitiveEvent) -> None:
        """Assign event to its tumbling window bucket."""
        bucket = (event.timestamp_ns // self._window_size_ns) * self._window_size_ns
        wid = f"{bucket}_{bucket + self._window_size_ns}"
        if wid not in self._windows:
            self._windows[wid] = {
                "start_ns": bucket,
                "end_ns": bucket + self._window_size_ns,
                "event_count": 0,
                "event_types": set(),
                "module_counts": defaultdict(int),
            }
        w = self._windows[wid]
        w["event_count"] += 1
        w["event_types"].add(event.event_type)
        w["module_counts"][event.source_module] += 1

    async def drain(self) -> AsyncIterator[CognitiveEvent]:
        async with self._lock:
            while self._heap:
                yield heapq.heappop(self._heap)

    def get_window(self, window_id: str) -> WindowedAggregate | None:
        w = self._windows.get(window_id)
        if w is None:
            return None
        return WindowedAggregate(
            window_id=window_id,
            start_ns=w["start_ns"],
            end_ns=w["end_ns"],
            event_count=w["event_count"],
            event_types=frozenset(w["event_types"]),
            summary=dict(w["module_counts"]),
        )

    def flush_windows(self) -> list[WindowedAggregate]:
        now_ns = time.monotonic_ns()
        result = []
        to_delete = []
        for wid, w in self._windows.items():
            if w["end_ns"] <= now_ns:
                result.append(self.get_window(wid))
                to_delete.append(wid)
        for wid in to_delete:
            del self._windows[wid]
        self._windows_flushed += len(result)
        return result

    def stats(self) -> dict[str, int | float]:
        return {
            "ingested":           self._ingested,
            "dropped":            self._dropped,
            "causal_violations":  self._causal_viol,
            "windows_flushed":    self._windows_flushed,
            "buffer_size":        len(self._heap),
            "buffer_utilization": len(self._heap) / self._cfg.max_buffer,
        }
```

---

## `NullSequencer` (no-op)

```python
class NullSequencer:
    """No-op sequencer for testing / dependency injection."""

    async def ingest(self, event: CognitiveEvent) -> bool:
        return True

    async def drain(self) -> AsyncIterator[CognitiveEvent]:
        return
        yield  # make it an async generator

    def get_window(self, window_id: str) -> WindowedAggregate | None:
        return None

    def flush_windows(self) -> list[WindowedAggregate]:
        return []

    def stats(self) -> dict[str, int | float]:
        return {}
```

---

## Tumbling vs Sliding Windows

```
Timeline: ──────────────────────────────────────────────────────►

TUMBLING (window_size_ms=500):
  │←── 500ms ──►│←── 500ms ──►│←── 500ms ──►│
  [  Window 1   ][  Window 2   ][  Window 3   ]
  Events: e1 e2   Events: e3     Events: e4 e5
  Clean boundaries → predictable PredictiveEngine input ✅

SLIDING (step_ms=250, size_ms=500):
  │←───── 500ms ─────►│
        │←───── 500ms ─────►│
              │←───── 500ms ─────►│
  e1 e2 appear in Windows 1 AND 2 → duplicate processing ❌

Decision: Tumbling windows for deterministic batch delivery to PredictiveEngine.
```

---

## Causal Ordering Validation Algorithm

```
FUNCTION validate_causal(event, seen_ids, policy):
  IF event.causal_parent_id IS NULL:
    RETURN ACCEPTED              # root event, no parent needed

  IF event.causal_parent_id IN seen_ids:
    RETURN ACCEPTED              # parent arrived before child ✅

  # Parent not yet seen
  causal_violations_total.inc(source_module=event.source_module)

  IF policy == STRICT:
    events_dropped_total.inc(reason="causal")
    RETURN DROPPED               # reject orphan in strict mode

  IF policy == RELAXED:
    RETURN ACCEPTED_WITH_WARNING # accept but flag for review

  IF policy == BEST_EFFORT:
    RETURN ACCEPTED              # causal order ignored
```

**TTL hardening**: Replace `set[str]` with `OrderedDict` trimmed to `max_buffer * 2` entries.

---

## CognitiveCycle Integration

```python
# In CognitiveCycle._run_step():
event = CognitiveEvent(
    event_id=str(uuid4()),
    source_module=module.name,
    event_type="module_output",
    payload=result,
    timestamp_ns=time.monotonic_ns(),
    causal_parent_id=prev_event_id,
)
accepted = await self._sequencer.ingest(event)
if accepted:
    async for ordered_event in self._sequencer.drain():
        await self._temporal_graph.add_node(
            ordered_event.event_id,
            ordered_event.timestamp_ns,
        )
        if prev_node_id:
            relation = allen_relation(prev_ts, ordered_event.timestamp_ns)
            await self._temporal_graph.add_edge(prev_node_id, ordered_event.event_id, relation)
        prev_node_id = ordered_event.event_id
        prev_ts = ordered_event.timestamp_ns
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `asi_sequencer_events_ingested_total` | Counter | `source_module`, `event_type` | Events accepted into heapq buffer |
| `asi_sequencer_events_dropped_total` | Counter | `reason` | Events dropped (overflow/causal/strict) |
| `asi_sequencer_windows_flushed_total` | Counter | — | Completed tumbling windows flushed |
| `asi_sequencer_causal_violations_total` | Counter | `source_module` | Causal parent not found in seen set |
| `asi_sequencer_buffer_utilization_ratio` | Gauge | — | `len(heap) / max_buffer` |

### PromQL

```promql
# Event throughput
rate(asi_sequencer_events_ingested_total[1m])

# Drop rate (alert > 1% of ingested)
rate(asi_sequencer_events_dropped_total[5m]) / rate(asi_sequencer_events_ingested_total[5m]) > 0.01

# Buffer saturation alert
asi_sequencer_buffer_utilization_ratio > 0.8

# Causal violation alert (> 5/min)
rate(asi_sequencer_causal_violations_total[1m]) > 0.083

# Window flush rate
rate(asi_sequencer_windows_flushed_total[1m])
```

### Grafana Alert YAML

```yaml
groups:
  - name: event_sequencer
    rules:
      - alert: SequencerBufferHigh
        expr: asi_sequencer_buffer_utilization_ratio > 0.8
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "EventSequencer buffer > 80% full — risk of overflow eviction"

      - alert: SequencerDropRateHigh
        expr: >
          rate(asi_sequencer_events_dropped_total[5m])
          / rate(asi_sequencer_events_ingested_total[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "EventSequencer drop rate > 1% — causal chain integrity at risk"

      - alert: CausalViolationSpike
        expr: rate(asi_sequencer_causal_violations_total[1m]) > 0.083
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Causal violations > 5/min — check module ordering in CognitiveCycle"
```

---

## mypy Narrowing Table

| Pattern | Type Before | Type After |
|---|---|---|
| `if event.causal_parent_id is not None:` | `str \| None` | `str` |
| `agg = get_window(wid); if agg is not None:` | `WindowedAggregate \| None` | `WindowedAggregate` |
| `async for e in drain():` | `AsyncIterator[CognitiveEvent]` | `CognitiveEvent` per iteration |
| `stats = sequencer.stats()` | `dict[str, int \| float]` | needs `cast` for specific keys |
| `if isinstance(seq, NullSequencer):` | `EventSequencer` | `NullSequencer` |

---

## 12 Test Targets

1. `test_ingest_returns_true_on_success`
2. `test_ingest_returns_false_on_strict_causal_violation`
3. `test_ingest_drops_oldest_on_overflow`
4. `test_drain_yields_timestamp_ordered`
5. `test_drain_empty_buffer_yields_nothing`
6. `test_causal_violation_increments_counter`
7. `test_causal_parent_accepted_when_parent_seen_first`
8. `test_window_accumulates_events_in_bucket`
9. `test_flush_windows_returns_completed_only`
10. `test_null_sequencer_always_accepts`
11. `test_stats_reflects_all_counters`
12. `test_order_policy_best_effort_never_drops`

### Skeletons

```python
async def test_causal_violation_dropped():
    cfg = SequencerConfig(causal_check=True, order_policy=OrderPolicy.STRICT)
    seq = AsyncEventSequencer(cfg)
    orphan = CognitiveEvent(
        event_id="e2", source_module="mod", event_type="t",
        payload={}, timestamp_ns=1000, causal_parent_id="e1_missing"
    )
    accepted = await seq.ingest(orphan)
    assert accepted is False
    assert seq.stats()["causal_violations"] == 1
    assert seq.stats()["dropped"] == 1


async def test_window_flush_accumulates():
    cfg = SequencerConfig(window_size_ms=100)
    seq = AsyncEventSequencer(cfg)
    base_ns = 0
    for i in range(5):
        e = CognitiveEvent(
            event_id=f"e{i}", source_module="mod_a", event_type="output",
            payload={}, timestamp_ns=base_ns + i * 10_000_000,  # 10ms apart
        )
        await seq.ingest(e)
    windows = seq.flush_windows()
    assert len(windows) >= 1
    assert windows[0].event_count == 5
    assert "output" in windows[0].event_types
```

---

## 14-Step Implementation Order

1. Define `OrderPolicy` enum
2. Implement `CognitiveEvent` frozen dataclass with `__lt__`
3. Implement `WindowedAggregate` frozen dataclass
4. Implement `SequencerConfig` frozen dataclass with defaults
5. Define `EventSequencer` Protocol (`@runtime_checkable`)
6. Implement `AsyncEventSequencer.__init__` (heap + lock + counters)
7. Implement `_accumulate_window()` (tumbling bucket assignment)
8. Implement `ingest()` with causal check + overflow eviction
9. Implement `drain()` as async generator
10. Implement `get_window()` + `flush_windows()`
11. Implement `stats()`
12. Implement `NullSequencer`
13. Register Prometheus metrics (Counter + Gauge)
14. Wire into `CognitiveCycle._run_step()` drain loop

---

## Phase 17 Sub-phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 17.1 | TemporalGraph | [#434](https://github.com/web3guru888/asi-build/issues/434) | 🟡 In Progress |
| 17.2 | EventSequencer | [#437](https://github.com/web3guru888/asi-build/issues/437) | 🟡 In Progress |
| 17.3 | PredictiveEngine | — | 🔲 Pending |
| 17.4 | TemporalCalibrator | — | 🔲 Pending |
| 17.5 | TemporalOrchestrator | — | 🔲 Pending |

---

*Part of [Phase 17 — Temporal Reasoning & Predictive Cognition](https://github.com/web3guru888/asi-build/discussions/433)*
*Previous: [Phase 17.1 — TemporalGraph](Phase-17-Temporal-Graph)*
