# Phase 18.4 — CausalMemoryIndex

> **Spec issue:** [#459](https://github.com/web3guru888/asi-build/issues/459) &nbsp;|&nbsp; **Show & Tell:** [#462](https://github.com/web3guru888/asi-build/discussions/462) &nbsp;|&nbsp; **Q&A:** [#463](https://github.com/web3guru888/asi-build/discussions/463)

**Causal indexing of MemoryChunks with fast retrieval by cause/effect chain, recency, and salience.**

| Field | Value |
|---|---|
| **Sub-phase** | 18.4 |
| **Component** | `CausalMemoryIndex` |
| **Depends on** | Phase 18.2 MemoryConsolidator (#453), Phase 8.2 CausalGraph (#280) |
| **Blocking** | Phase 18.5 (TBD) |
| **Estimated tests** | 12 |

---

## Problem

After MemoryConsolidator (18.2) sweeps episodic traces into semantic patterns and CausalGraph (8.2) captures cause→effect edges, there is no unified index that lets downstream modules **query memory chunks by causal lineage, temporal range, or salience ranking** with sub-millisecond latency. Without such an index, any component needing "why did X happen?" or "what were the most salient memories in the last hour?" must perform full scans across multiple stores.

## Solution

`CausalMemoryIndex` provides a purpose-built in-memory index over MemoryChunks that supports four query modes — cause-chain traversal, effect fan-out, temporal range, and salience top-K — with background rebuild, exponential salience decay, and an LRU query cache.

---

## Public API

### 1. `IndexMode` Enum

```python
from enum import Enum, auto

class IndexMode(Enum):
    """Query mode for the causal memory index."""
    CAUSE_CHAIN    = auto()  # Walk backward through cause links
    EFFECT_FAN     = auto()  # Walk forward through effect links
    TEMPORAL_RANGE = auto()  # Range query over timestamp_ns
    SALIENCE_TOP_K = auto()  # Top-K by decayed salience score
```

### 2. `IndexEntry` Frozen Dataclass

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True, slots=True)
class IndexEntry:
    """Single entry in the causal memory index."""
    chunk_id: str
    cause_ids: frozenset[str]      # IDs of direct causes
    effect_ids: frozenset[str]     # IDs of direct effects
    salience: float                # Raw salience score [0.0, 1.0]
    timestamp_ns: int              # Ingestion time (monotonic nanoseconds)
    embedding: tuple[float, ...] | None = None  # Optional vector for future semantic queries
```

### 3. `IndexConfig` Frozen Dataclass

```python
@dataclass(frozen=True, slots=True)
class IndexConfig:
    """Tuneable knobs for CausalMemoryIndex."""
    max_entries: int = 100_000         # Hard cap on index size
    salience_decay_rate: float = 1e-6  # Exponential decay λ (per second)
    rebuild_interval_s: float = 300.0  # Background rebuild period
    cache_ttl_s: float = 60.0         # LRU query-cache TTL
```

### 4. `CausalMemoryIndex` Protocol

```python
from typing import Protocol, runtime_checkable, Sequence

@runtime_checkable
class CausalMemoryIndex(Protocol):
    """Index over MemoryChunks for causal, temporal, and salience queries."""

    async def index_chunk(self, entry: IndexEntry) -> None:
        """Add or update an entry in the index."""
        ...

    async def query_by_cause(self, chunk_id: str, *, max_depth: int = 3) -> Sequence[IndexEntry]:
        """Walk backward through cause links up to max_depth."""
        ...

    async def query_by_effect(self, chunk_id: str, *, max_depth: int = 3) -> Sequence[IndexEntry]:
        """Walk forward through effect links up to max_depth."""
        ...

    async def query_temporal_range(
        self, start_ns: int, end_ns: int, *, limit: int = 100
    ) -> Sequence[IndexEntry]:
        """Return entries whose timestamp_ns ∈ [start_ns, end_ns], ordered by time."""
        ...

    async def query_top_k_salient(self, k: int = 10) -> Sequence[IndexEntry]:
        """Return the K entries with highest decayed salience."""
        ...

    async def rebuild(self) -> int:
        """Full rebuild from upstream stores. Returns entry count."""
        ...

    async def prune(self, max_age_s: float | None = None) -> int:
        """Remove stale entries. Returns pruned count."""
        ...

    async def stats(self) -> dict[str, object]:
        """Return index statistics (size, hit rate, rebuild age, etc.)."""
        ...
```

### 5. `AsyncCausalMemoryIndex` Implementation

```python
import asyncio
import time
import math
from collections import OrderedDict
from sortedcontainers import SortedList

class AsyncCausalMemoryIndex:
    """Production implementation of CausalMemoryIndex.

    Internal data structures
    ========================
    - _entries: dict[str, IndexEntry]           — primary store keyed by chunk_id
    - _temporal: SortedList[tuple[int, str]]    — (timestamp_ns, chunk_id) for range queries
    - _cause_adj: dict[str, set[str]]           — chunk_id → set of chunk_ids that CAUSED it
    - _effect_adj: dict[str, set[str]]          — chunk_id → set of chunk_ids it CAUSED
    - _lock: asyncio.Lock                       — serialises writes
    - _cache: OrderedDict[str, tuple[float, Sequence[IndexEntry]]]  — LRU query cache
    - _rebuild_task: asyncio.Task | None        — background rebuild loop
    """

    def __init__(self, config: IndexConfig | None = None) -> None: ...

    # --- write path ---
    async def index_chunk(self, entry: IndexEntry) -> None:
        """Insert/update entry; invalidates overlapping cache keys."""
        ...

    # --- read paths ---
    async def query_by_cause(self, chunk_id: str, *, max_depth: int = 3) -> Sequence[IndexEntry]:
        """BFS backward through _cause_adj, collect entries up to max_depth."""
        ...

    async def query_by_effect(self, chunk_id: str, *, max_depth: int = 3) -> Sequence[IndexEntry]:
        """BFS forward through _effect_adj, collect entries up to max_depth."""
        ...

    async def query_temporal_range(
        self, start_ns: int, end_ns: int, *, limit: int = 100
    ) -> Sequence[IndexEntry]:
        """SortedList.irange bisect for O(log n + k) retrieval."""
        ...

    async def query_top_k_salient(self, k: int = 10) -> Sequence[IndexEntry]:
        """Apply salience_decay, heapq.nlargest over _entries.values()."""
        ...

    # --- maintenance ---
    async def rebuild(self) -> int:
        """Pull all chunks from MemoryConsolidator.get_patterns() and
        CausalGraph.edges(), re-index from scratch."""
        ...

    async def prune(self, max_age_s: float | None = None) -> int:
        """Remove entries older than max_age_s; update _temporal + adjacency."""
        ...

    async def stats(self) -> dict[str, object]:
        """Return {size, cache_hit_ratio, last_rebuild_ts, decay_rate, ...}."""
        ...

    # --- lifecycle ---
    async def start(self) -> None:
        """Launch _rebuild_loop background task."""
        ...

    async def stop(self) -> None:
        """Cancel _rebuild_loop, drain pending writes."""
        ...

    # --- internals ---
    def _decayed_salience(self, entry: IndexEntry) -> float:
        """salience * exp(-decay_rate * age_seconds)"""
        ...

    async def _rebuild_loop(self) -> None:
        """while True: await asyncio.sleep(config.rebuild_interval_s); await rebuild()"""
        ...

    def _invalidate_cache(self, chunk_id: str) -> None:
        """Remove any cache key whose result set includes chunk_id."""
        ...
```

### 6. `NullCausalMemoryIndex`

```python
class NullCausalMemoryIndex:
    """No-op implementation for DI/testing."""
    async def index_chunk(self, entry: IndexEntry) -> None: ...
    async def query_by_cause(self, chunk_id: str, *, max_depth: int = 3) -> Sequence[IndexEntry]:
        return ()
    async def query_by_effect(self, chunk_id: str, *, max_depth: int = 3) -> Sequence[IndexEntry]:
        return ()
    async def query_temporal_range(self, start_ns: int, end_ns: int, *, limit: int = 100) -> Sequence[IndexEntry]:
        return ()
    async def query_top_k_salient(self, k: int = 10) -> Sequence[IndexEntry]:
        return ()
    async def rebuild(self) -> int:
        return 0
    async def prune(self, max_age_s: float | None = None) -> int:
        return 0
    async def stats(self) -> dict[str, object]:
        return {"size": 0, "status": "null"}
```

### 7. Factory

```python
def make_causal_memory_index(
    *,
    config: IndexConfig | None = None,
    null: bool = False,
) -> CausalMemoryIndex:
    if null:
        return NullCausalMemoryIndex()
    return AsyncCausalMemoryIndex(config=config or IndexConfig())
```

---

## Data Flow

```
   MemoryConsolidator (18.2)          CausalGraph (8.2)
   ┌──────────────────┐               ┌─────────────┐
   │  sweep() produces │               │  edges()    │
   │  SemanticPatterns │               │  returns    │
   │                   │               │  cause→     │
   └────────┬──────────┘               │  effect     │
            │                          └──────┬──────┘
            │  _consolidate_trace callback     │  rebuild() pulls
            ▼                                  ▼
   ┌──────────────────────────────────────────────────┐
   │              AsyncCausalMemoryIndex               │
   │                                                   │
   │  ┌─────────────┐  ┌────────────┐  ┌───────────┐ │
   │  │ _entries     │  │ _temporal   │  │ _cause_adj│ │
   │  │ dict[str,    │  │ SortedList  │  │ dict[str, │ │
   │  │  IndexEntry] │  │ [(ts, id)] │  │  set[str]]│ │
   │  └─────────────┘  └────────────┘  └───────────┘ │
   │  ┌─────────────┐  ┌────────────┐                │
   │  │ _effect_adj  │  │ _cache     │                │
   │  │ dict[str,    │  │ OrderedDict│                │
   │  │  set[str]]   │  │ LRU+TTL   │                │
   │  └─────────────┘  └────────────┘                │
   └───────────────────────┬──────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
      query_by_cause  query_temporal  query_top_k
      query_by_effect    _range       _salient
```

### Background Rebuild Loop Lifecycle

```
start()
  │
  ▼
┌─────────────────────────────────────────┐
│ _rebuild_loop (asyncio.Task)            │
│                                         │
│  while True:                            │
│    await asyncio.sleep(rebuild_interval)│
│    async with _lock:                    │
│      pull edges from CausalGraph        │
│      pull patterns from Consolidator    │
│      clear _entries, _temporal, adj     │
│      re-index all entries               │
│      update asi_causal_index_size       │
│      record rebuild_duration_seconds    │
└──────────────────┬──────────────────────┘
                   │
stop()  ───────────┘  (cancels task, drains pending)
```

---

## Internal Data Structures

| Structure | Type | Purpose | Complexity |
|---|---|---|---|
| `_entries` | `dict[str, IndexEntry]` | Primary store, keyed by chunk_id | O(1) lookup |
| `_temporal` | `SortedList[(ts, id)]` | Temporal range queries via `irange()` | O(log n) bisect |
| `_cause_adj` | `dict[str, set[str]]` | Backward causal traversal (BFS) | O(1 + degree) |
| `_effect_adj` | `dict[str, set[str]]` | Forward causal traversal (BFS) | O(1 + degree) |
| `_cache` | `OrderedDict` | LRU query cache with TTL | O(1) lookup |

### Query Mode → Data Structure Mapping

```
┌─────────────────────────────────────────────────────────┐
│                    IndexMode Enum                        │
├──────────────┬──────────────┬──────────────┬────────────┤
│ CAUSE_CHAIN  │ EFFECT_FAN   │TEMPORAL_RANGE│SALIENCE_K  │
│ BFS backward │ BFS forward  │ SortedList   │ heapq +    │
│ via _cause_  │ via _effect_ │ .irange()    │ exp decay  │
│ adj dict     │ adj dict     │ O(log n + k) │ nlargest   │
└──────────────┴──────────────┴──────────────┴────────────┘
```

---

## Salience Decay

Salience decays exponentially over time:

```python
def _decayed_salience(self, entry: IndexEntry) -> float:
    age_s = (time.monotonic_ns() - entry.timestamp_ns) / 1e9
    return entry.salience * math.exp(-self._config.salience_decay_rate * age_s)
```

| Age | Decay Factor (λ=1e-6) | Interpretation |
|---|---|---|
| 1 hour | 0.9964 | ~unchanged |
| 1 day | 0.9172 | ~8% decay |
| 1 week | 0.5462 | ~45% decay |
| 1 month | 0.0725 | ~93% decay |

Half-life ≈ `ln(2) / 1e-6 ≈ 693,147 seconds ≈ 8 days`.

---

## Integration Map

```
Phase 8.2 CausalGraph ──edges()──┐
                                  │
Phase 18.2 MemoryConsolidator ──┐ │
  SemanticPattern output        │ │
                                ▼ ▼
                    ┌─────────────────────┐
                    │  CausalMemoryIndex  │
                    │       (18.4)        │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ExplainAPI (8.3)   DreamPlanner (13.2)  HorizonPlanner (18.1)
    "why did X         causal chains for    salience-weighted
     happen?"          counterfactual       horizon bucket
                       planning             assignment
```

### Integration Details

| Upstream | Interface | Data |
|---|---|---|
| MemoryConsolidator (18.2) | `_consolidate_trace()` callback → `index_chunk()` | SemanticPattern ID, salience score, timestamp |
| CausalGraph (8.2) | `edges()` at rebuild time | cause→effect chunk_id pairs |

| Downstream | Query Mode | Use Case |
|---|---|---|
| ExplainAPI (8.3) | `CAUSE_CHAIN` | "Why did event X happen?" — walks backward |
| DreamPlanner (13.2) | `EFFECT_FAN` | Counterfactual planning — "what if X?" |
| HorizonPlanner (18.1) | `SALIENCE_TOP_K` | Assign high-salience items to SHORT horizon |
| ReflectionCycle (16.5) | `TEMPORAL_RANGE` | Recent memories for self-reflection |

---

## Prometheus Metrics

| Metric | Type | Description |
|---|---|---|
| `asi_causal_index_size` | Gauge | Current number of entries in the index |
| `asi_causal_index_query_latency_seconds` | Histogram | Per-query latency bucketed by IndexMode |
| `asi_causal_index_rebuild_duration_seconds` | Histogram | Time taken for a full rebuild |
| `asi_causal_index_cache_hit_ratio` | Gauge | Rolling cache hit / (hit + miss) ratio |
| `asi_causal_index_prune_total` | Counter | Cumulative number of entries pruned |

### PromQL Examples

```promql
# Average query latency by mode (5m window)
rate(asi_causal_index_query_latency_seconds_sum[5m])
  / rate(asi_causal_index_query_latency_seconds_count[5m])

# Cache effectiveness
asi_causal_index_cache_hit_ratio > 0.8  # healthy threshold

# Rebuild duration spike
histogram_quantile(0.99, rate(asi_causal_index_rebuild_duration_seconds_bucket[10m])) > 5
```

### Grafana Alerts

```yaml
- alert: CausalIndexQueryLatencyHigh
  expr: histogram_quantile(0.99, rate(asi_causal_index_query_latency_seconds_bucket[5m])) > 0.05
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "CausalMemoryIndex p99 query latency > 50ms"

- alert: CausalIndexCacheHitLow
  expr: asi_causal_index_cache_hit_ratio < 0.5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "CausalMemoryIndex cache hit ratio below 50%"

- alert: CausalIndexRebuildSlow
  expr: histogram_quantile(0.99, rate(asi_causal_index_rebuild_duration_seconds_bucket[10m])) > 10
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "CausalMemoryIndex rebuild taking > 10s at p99"
```

---

## mypy Strict Compliance

| Pattern | Narrowing technique |
|---|---|
| `IndexMode` dispatch | `match mode:` with exhaustive cases |
| `embedding: tuple[float,...] \| None` | `if entry.embedding is not None:` |
| `_rebuild_task: asyncio.Task \| None` | `if self._rebuild_task is not None:` |
| `max_age_s: float \| None` | `if max_age_s is not None:` guard |
| `_entries.get(chunk_id)` | `entry := self._entries.get(cid)` walrus |

---

## Test Targets (12)

| # | Test | Validates |
|---|---|---|
| 1 | `test_index_chunk_stores_and_retrieves` | Round-trip index→query |
| 2 | `test_query_by_cause_depth_limit` | BFS respects max_depth |
| 3 | `test_query_by_effect_fan_out` | Forward traversal correctness |
| 4 | `test_temporal_range_inclusive_bounds` | SortedList bisect boundaries |
| 5 | `test_temporal_range_empty` | No matches returns empty |
| 6 | `test_top_k_salience_ordering` | Decayed salience sort order |
| 7 | `test_salience_decay_reduces_score` | Exponential decay formula |
| 8 | `test_rebuild_repopulates_from_upstream` | rebuild() re-indexes all |
| 9 | `test_prune_removes_old_entries` | Age-based eviction |
| 10 | `test_cache_hit_after_identical_query` | LRU cache returns cached |
| 11 | `test_cache_invalidation_on_index_chunk` | Write invalidates cache |
| 12 | `test_null_implementation_noop` | NullCausalMemoryIndex contract |

### Test Skeletons

```python
import pytest
import asyncio
import time

@pytest.mark.asyncio
async def test_query_by_cause_depth_limit():
    """BFS backward should stop at max_depth even if deeper causes exist."""
    idx = AsyncCausalMemoryIndex(IndexConfig())
    # Build chain: A → B → C → D (each caused by the previous)
    await idx.index_chunk(IndexEntry("A", frozenset(), frozenset({"B"}), 0.5, time.monotonic_ns()))
    await idx.index_chunk(IndexEntry("B", frozenset({"A"}), frozenset({"C"}), 0.5, time.monotonic_ns()))
    await idx.index_chunk(IndexEntry("C", frozenset({"B"}), frozenset({"D"}), 0.5, time.monotonic_ns()))
    await idx.index_chunk(IndexEntry("D", frozenset({"C"}), frozenset(), 0.5, time.monotonic_ns()))

    # Query causes of D with max_depth=2 → should get C and B, NOT A
    results = await idx.query_by_cause("D", max_depth=2)
    result_ids = {e.chunk_id for e in results}
    assert result_ids == {"C", "B"}
    assert "A" not in result_ids  # depth 3 — excluded


@pytest.mark.asyncio
async def test_cache_invalidation_on_index_chunk():
    """Inserting a new chunk should invalidate cached queries that reference it."""
    idx = AsyncCausalMemoryIndex(IndexConfig(cache_ttl_s=60.0))
    await idx.index_chunk(IndexEntry("X", frozenset(), frozenset(), 0.9, time.monotonic_ns()))

    # First query populates cache
    r1 = await idx.query_top_k_salient(k=5)
    assert len(r1) == 1

    # Insert a more salient chunk
    await idx.index_chunk(IndexEntry("Y", frozenset(), frozenset(), 1.0, time.monotonic_ns()))

    # Second query should NOT return stale cache — Y must appear
    r2 = await idx.query_top_k_salient(k=5)
    assert len(r2) == 2
    assert r2[0].chunk_id == "Y"  # highest salience
```

---

## Implementation Order (14 steps)

1. Create `asi/memory/causal_index/__init__.py` with `__all__`
2. Define `IndexMode` enum in `enums.py`
3. Define `IndexEntry` + `IndexConfig` frozen dataclasses in `models.py`
4. Define `CausalMemoryIndex` Protocol in `protocol.py`
5. Implement `NullCausalMemoryIndex` in `null.py`
6. Scaffold `AsyncCausalMemoryIndex.__init__` with all data structures
7. Implement `index_chunk` (write path + adjacency update + cache invalidation)
8. Implement `query_by_cause` + `query_by_effect` (BFS with depth limit)
9. Implement `query_temporal_range` (SortedList.irange)
10. Implement `query_top_k_salient` (heapq.nlargest + `_decayed_salience`)
11. Implement `rebuild` + `prune` + `_rebuild_loop` lifecycle
12. Implement `stats` + Prometheus metric hooks
13. Wire `make_causal_memory_index` factory in `factory.py`
14. Write 12 tests in `tests/test_causal_memory_index.py`

---

## Phase 18 Sub-phase Tracker

| # | Component | Issue | Wiki | Status |
|---|---|---|---|---|
| 18.1 | HorizonPlanner | [#450](https://github.com/web3guru888/asi-build/issues/450) | ✅ | 🟡 Spec |
| 18.2 | MemoryConsolidator | [#453](https://github.com/web3guru888/asi-build/issues/453) | ✅ | 🟡 Spec |
| 18.3 | DistributedTemporalSync | [#456](https://github.com/web3guru888/asi-build/issues/456) | ✅ | 🟡 Spec |
| **18.4** | **CausalMemoryIndex** | [**#459**](https://github.com/web3guru888/asi-build/issues/459) | ✅ | 🟡 **Spec** |
| 18.5 | TBD | — | — | ⏳ Planned |
