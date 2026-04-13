# Phase 18.2 — MemoryConsolidator

> **Phase 18: Distributed Temporal Cognition & Multi-Horizon Memory**
> Sub-phase 18.2 of 5 — offline episodic→semantic consolidation

## Overview

`MemoryConsolidator` runs as a background `asyncio` task that periodically sweeps **episodic memory traces** (stored in `TemporalGraph`) and consolidates them into **semantic memory** (in `WorldModel`). Inspired by hippocampal-neocortical consolidation in neuroscience — the hippocampus (TemporalGraph) temporarily holds high-fidelity episodic traces, then gradually transfers generalised patterns into long-term cortical storage (WorldModel) during periods of low cognitive load.

**Key benefits:**
- Bounds `TemporalGraph` growth — old consolidated traces are pruned after `retention_days`
- Enriches `WorldModel` with generalised semantic patterns derived from repeated/surprising events
- Decoupled from the hot `CognitiveCycle` path — runs in a separate `asyncio.Task`
- Strategy-configurable: RECENCY, FREQUENCY, SURPRISE, or HYBRID scoring

**GitHub issue:** [#453](https://github.com/web3guru888/asi-build/issues/453)

---

## Data Flow Diagram

```
CognitiveCycle (hot path)
  EventSequencer --> TemporalGraph --> SurpriseDetector
                          |                  |
                  [EpisodicTrace written]  [surprise_score]
                          |                  |
              (background asyncio.Task - low priority)
                          v                  v
              MemoryConsolidator.sweep()
                  get_unconsolidated_traces(limit=N)
                          |
                  _score_trace(t, max_freq)
                    RECENCY:   1/(age_s+1)
                    FREQUENCY: freq/max_freq
                    SURPRISE:  surprise_score
                    HYBRID:    0.3R + 0.4F + 0.3S
                  sort DESC -> top-N
                          |
                  asyncio.Lock (per-sweep)
                          |
                  _consolidate_trace(trace)
                    get_event_features()
                    _compute_centroid()
                    build SemanticPattern
                    world_model.upsert_pattern()
                    emit metrics
                          |
                          v
              WorldModel (semantic)
                SemanticPattern store
                --> HorizonPlanner (18.1) input
                --> GoalDecomposer (10.2) planning
```

---

## `ConsolidationStrategy` Enum

```python
class ConsolidationStrategy(str, enum.Enum):
    RECENCY   = "recency"    # consolidate oldest traces first
    FREQUENCY = "frequency"  # consolidate most-repeated patterns first
    SURPRISE  = "surprise"   # SurpriseDetector-driven: highest surprise_score first
    HYBRID    = "hybrid"     # weighted blend: 0.3*recency + 0.4*frequency + 0.3*surprise
```

### Strategy Comparison Table

| Strategy | Use Case | Score Formula | Gate Condition |
|---|---|---|---|
| `RECENCY` | Prevent indefinite backlog; oldest traces first | `1 / (age_seconds + 1)` | none |
| `FREQUENCY` | Compress repeated patterns into stable knowledge | `trace.frequency / max_freq` | `frequency >= min_frequency_threshold` |
| `SURPRISE` | Prioritise novel/unexpected events for fast learning | `trace.surprise_score` | `surprise_score >= surprise_threshold` |
| `HYBRID` | Balanced consolidation for production systems | `0.3·recency + 0.4·frequency + 0.3·surprise` | none (weights handle gating softly) |

---

## Data Structures

### `EpisodicTrace` (frozen dataclass)

```python
@dataclasses.dataclass(frozen=True)
class EpisodicTrace:
    trace_id: str
    event_ids: FrozenSet[str]          # IDs of constituent TemporalGraph events
    timestamp_ns: int                  # creation time (monotonic ns)
    surprise_score: float              # from SurpriseDetector [0.0, 1.0]
    frequency: int                     # how many times this pattern was observed
    consolidated: bool = False         # True once passed to WorldModel
```

### `SemanticPattern` (frozen dataclass)

```python
@dataclasses.dataclass(frozen=True)
class SemanticPattern:
    pattern_id: str
    source_trace_ids: FrozenSet[str]   # which EpisodicTraces contributed
    abstraction: Dict[str, Any]        # centroid feature dict extracted from traces
    confidence: float                  # [0.0, 1.0] — weighted by frequency + surprise
    created_ns: int
```

### `ConsolidatorConfig` (frozen dataclass)

```python
@dataclasses.dataclass(frozen=True)
class ConsolidatorConfig:
    strategy: ConsolidationStrategy
    sweep_interval_s: float = 30.0     # seconds between background sweeps
    max_traces_per_sweep: int = 50     # cap on traces processed per sweep
    min_frequency_threshold: int = 3   # FREQUENCY strategy gate
    surprise_threshold: float = 0.7    # SURPRISE strategy gate
    retention_days: float = 7.0        # prune traces older than this
    dry_run: bool = False              # score + log, do NOT mutate WorldModel
```

---

## `MemoryConsolidator` Protocol

```python
@typing.runtime_checkable
class MemoryConsolidator(typing.Protocol):
    async def consolidate(self) -> int:
        """Run one sweep; return number of traces newly consolidated."""
        ...

    async def sweep(self) -> None:
        """Fetch candidates, score, consolidate top-N, emit metrics."""
        ...

    async def get_patterns(self) -> List[SemanticPattern]:
        """Return all SemanticPatterns sorted by confidence descending."""
        ...

    async def prune_old_traces(self, retention_ns: int) -> int:
        """Remove TemporalGraph traces older than retention_ns; return count."""
        ...
```

---

## `AsyncMemoryConsolidator` Implementation

```python
class AsyncMemoryConsolidator:
    def __init__(
        self,
        temporal_graph: TemporalGraph,
        world_model: WorldModel,
        surprise_detector: SurpriseDetector,
        config: ConsolidatorConfig,
    ) -> None:
        self._graph = temporal_graph
        self._world = world_model
        self._surprise = surprise_detector
        self._config = config
        self._patterns: Dict[str, SemanticPattern] = {}
        self._lock = asyncio.Lock()
        self._sweep_count: int = 0
        self._stop_event: asyncio.Event = asyncio.Event()
        self._loop_task: Optional[asyncio.Task] = None

    async def sweep(self) -> None:
        candidates = await self._graph.get_unconsolidated_traces(
            limit=self._config.max_traces_per_sweep
        )
        if not candidates:
            return
        max_freq = max((t.frequency for t in candidates), default=1)
        scored = sorted(
            candidates,
            key=lambda t: self._score_trace(t, max_freq),
            reverse=True,
        )
        async with self._lock:
            for trace in scored[: self._config.max_traces_per_sweep]:
                await self._consolidate_trace(trace)
        self._sweep_count += 1

    def _score_trace(self, trace: EpisodicTrace, max_freq: int) -> float:
        now_ns = time.monotonic_ns()
        age_s = (now_ns - trace.timestamp_ns) / 1e9
        recency   = 1.0 / (age_s + 1.0)
        frequency = trace.frequency / max(max_freq, 1)
        surprise  = trace.surprise_score
        if self._config.strategy == ConsolidationStrategy.RECENCY:
            return recency
        if self._config.strategy == ConsolidationStrategy.FREQUENCY:
            return frequency if trace.frequency >= self._config.min_frequency_threshold else 0.0
        if self._config.strategy == ConsolidationStrategy.SURPRISE:
            return surprise if trace.surprise_score >= self._config.surprise_threshold else 0.0
        # HYBRID: 0.3*recency + 0.4*frequency + 0.3*surprise
        return 0.3 * recency + 0.4 * frequency + 0.3 * surprise

    async def _consolidate_trace(self, trace: EpisodicTrace) -> None:
        if self._config.dry_run:
            return  # log only — no mutations
        features = await self._graph.get_event_features(trace.event_ids)
        abstraction = _compute_centroid(features)
        confidence  = min(1.0, (trace.frequency / 10.0) * 0.5 + trace.surprise_score * 0.5)
        pattern = SemanticPattern(
            pattern_id=f"pat-{trace.trace_id}",
            source_trace_ids=frozenset({trace.trace_id}),
            abstraction=abstraction,
            confidence=confidence,
            created_ns=time.monotonic_ns(),
        )
        await self._world.upsert_pattern(pattern)
        self._patterns[pattern.pattern_id] = pattern

    async def consolidate(self) -> int:
        before = len(self._patterns)
        await self.sweep()
        return len(self._patterns) - before

    async def get_patterns(self) -> List[SemanticPattern]:
        return sorted(self._patterns.values(), key=lambda p: p.confidence, reverse=True)

    async def prune_old_traces(self, retention_ns: int) -> int:
        return await self._graph.delete_traces_older_than(retention_ns)

    async def _run_consolidation_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.sweep()
            except Exception:
                pass  # degraded — log, continue
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._config.sweep_interval_s,
                )
            except asyncio.TimeoutError:
                pass

    def start(self) -> None:
        self._stop_event.clear()
        self._loop_task = asyncio.ensure_future(self._run_consolidation_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._loop_task:
            await self._loop_task
```

### `_compute_centroid()` Pattern Extraction Algorithm

```
1. Call temporal_graph.get_event_features(trace.event_ids)
   -> returns List[Dict[str, Any]], one dict per event_id

2. Cluster features by key presence (simple key-union centroid):
   centroid = {}
   for key in union of all feature dicts:
       values = [f[key] for f in features if key in f]
       if all numeric: centroid[key] = mean(values)
       else:           centroid[key] = mode(values)  # most common value

3. Compute confidence:
   confidence = clamp(frequency/10 * 0.5 + surprise_score * 0.5, 0.0, 1.0)

4. Build SemanticPattern(
       pattern_id       = f"pat-{trace.trace_id}",
       source_trace_ids = frozenset({trace.trace_id}),
       abstraction      = centroid,
       confidence       = confidence,
       created_ns       = time.monotonic_ns(),
   )

5. await world_model.upsert_pattern(pattern)
6. self._patterns[pattern.pattern_id] = pattern
7. Emit traces_consolidated_total.inc() + patterns_created_total.inc()
```

---

## Background Loop Lifecycle

```
start()
  |
  v
_stop_event.clear()
asyncio.ensure_future(_run_consolidation_loop())
  |
  [loop iteration]
  |
  +-- stop_event set? --> EXIT
  |
  +-- No: call sweep()
          fetch candidates, score+sort
          _consolidate_trace() x N (under asyncio.Lock)
          _sweep_count += 1
          emit consolidation_sweep_total.inc()
          |
          wait_for(stop_event, timeout=sweep_interval_s)
          TimeoutError (no stop) --> loop again
          stop_event set --> EXIT

stop()
  _stop_event.set()
  await _loop_task
```

---

## `NullMemoryConsolidator`

```python
class NullMemoryConsolidator:
    """No-op implementation for dependency injection in tests / null-object pattern."""
    async def consolidate(self) -> int: return 0
    async def sweep(self) -> None: pass
    async def get_patterns(self) -> List[SemanticPattern]: return []
    async def prune_old_traces(self, retention_ns: int) -> int: return 0
    def start(self) -> None: pass
    async def stop(self) -> None: pass
```

---

## `make_memory_consolidator()` Factory

```python
def make_memory_consolidator(
    temporal_graph: TemporalGraph,
    world_model: WorldModel,
    surprise_detector: SurpriseDetector,
    config: ConsolidatorConfig,
    *,
    null: bool = False,
) -> MemoryConsolidator:
    if null:
        return NullMemoryConsolidator()
    return AsyncMemoryConsolidator(temporal_graph, world_model, surprise_detector, config)
```

---

## Scoring Formula Reference Table

| Strategy | Formula | Range | Notes |
|---|---|---|---|
| RECENCY | `1 / (age_seconds + 1)` | `(0, 1]` | age=0 → 1.0; age=29 → 0.033; age=3599 → 0.00028 |
| FREQUENCY | `trace.frequency / max_freq` | `[0, 1]` | normalised per-sweep batch; gate: `freq >= min_frequency_threshold` |
| SURPRISE | `trace.surprise_score` | `[0, 1]` | from SurpriseDetector; gate: `score >= surprise_threshold` |
| HYBRID | `0.3R + 0.4F + 0.3S` | `[0, 1]` | weights sum to 1.0; no hard gate |

**HYBRID weight rationale**: Frequency (0.4) has the highest weight because repeated patterns have the strongest evidence for generalisation. Recency (0.3) prevents indefinite deferral. Surprise (0.3) ensures informationally-rich novel events are promoted.

---

## Integration Diagrams

### WorldModel Integration

```
_consolidate_trace(trace)
  |
  +-- dry_run=True --> LOG + RETURN (no mutations)
  |
  +-- dry_run=False:
       get_event_features(trace.event_ids) --> List[Dict]
       _compute_centroid(features)         --> abstraction: Dict
       build SemanticPattern(confidence=freq*0.5 + surprise*0.5)
       world_model.upsert_pattern(pattern)
         |
         +-- new pattern_id   --> INSERT
         +-- existing pattern --> MERGE abstraction (new wins), max confidence
         +-- WorldModelError  --> LOG + CONTINUE (no retry)
       self._patterns[pattern.pattern_id] = pattern
```

### HorizonPlanner Integration

```
MemoryConsolidator
  --> WorldModel.SemanticPattern store (high-confidence patterns)
       |
       v
HorizonPlanner (18.1)
  WorldModel.get_patterns(module=X)
  --> use abstraction.duration_estimate_ms as duration hint
  --> use confidence to weight EDF deadline tightness
  --> HIGH confidence pattern --> LONG horizon if deadline > 24h
  --> LOW  confidence pattern --> SHORT horizon (conservative)
```

### SurpriseDetector Integration

```
EventSequencer --> TemporalGraph
                       |
                  [event written]
                       |
                  SurpriseDetector.score(event)
                       |
                  EpisodicTrace.surprise_score = score
                       |
              MemoryConsolidator.sweep()
                _score_trace(trace, max_freq)
                  SURPRISE: score if score >= surprise_threshold else 0.0
                  HYBRID:   0.3 * score
```

---

## Prometheus Metrics + Grafana

### Metrics

| Metric | Type | Description | PromQL |
|---|---|---|---|
| `consolidation_sweep_total` | Counter | Total background sweeps completed | `rate(consolidation_sweep_total[5m])` |
| `traces_consolidated_total` | Counter | Total episodic traces consolidated | `rate(traces_consolidated_total[5m])` |
| `patterns_created_total` | Counter | Total SemanticPatterns created | `increase(patterns_created_total[1h])` |
| `consolidation_sweep_duration_seconds` | Histogram | Wall time per sweep | `histogram_quantile(0.95, ..._bucket)` |
| `active_patterns_count` | Gauge | Current count of live SemanticPatterns | `active_patterns_count` |

### Grafana Alert YAML Snippets

```yaml
# Alert 1: Consolidation loop stalled
alert: ConsolidationSweepStalled
expr: rate(consolidation_sweep_total[10m]) == 0
for: 5m
labels:
  severity: warning
annotations:
  summary: "MemoryConsolidator background loop has stalled"
  description: "No consolidation sweeps in 10 minutes"

# Alert 2: Semantic pattern store growing unboundedly
alert: SemanticPatternStoreOverflow
expr: active_patterns_count > 5000
for: 2m
labels:
  severity: warning
annotations:
  summary: "SemanticPattern store exceeds 5000 entries"
  description: "Consider reducing retention_days or increasing prune frequency"

# Alert 3: High sweep latency
alert: ConsolidationSweepSlowP95
expr: >
  histogram_quantile(0.95,
    rate(consolidation_sweep_duration_seconds_bucket[5m])) > 5
for: 3m
labels:
  severity: warning
annotations:
  summary: "Consolidation sweep p95 latency exceeds 5s"
  description: "WorldModel.upsert_pattern() may be slow or blocking"
```

---

## mypy Narrowing Table

| Expression | Inferred type | Notes |
|---|---|---|
| `make_memory_consolidator(..., null=False)` | `AsyncMemoryConsolidator` | concrete return |
| `make_memory_consolidator(..., null=True)` | `NullMemoryConsolidator` | concrete return |
| `isinstance(mc, MemoryConsolidator)` | `True` for both | `@runtime_checkable` Protocol |
| `mc._lock` | only on `AsyncMemoryConsolidator` | not in Protocol — guard with `isinstance` |
| `mc._patterns` | only on `AsyncMemoryConsolidator` | internal, not Protocol surface |
| `mc._sweep_count` | only on `AsyncMemoryConsolidator` | for introspection/debug only |
| `mc.start()` | available on both | not in Protocol — add if lifecycle management needed |

---

## 12 Test Targets

1. `test_recency_scoring_prefers_older_traces`
2. `test_frequency_scoring_below_threshold_scores_zero`
3. `test_surprise_scoring_below_threshold_scores_zero`
4. `test_hybrid_weights_sum_to_one` — verify 0.3+0.4+0.3=1.0 and trace ordering
5. `test_dry_run_no_world_model_mutations`
6. `test_consolidate_returns_correct_count`
7. `test_get_patterns_sorted_by_confidence_desc`
8. `test_prune_old_traces_removes_correct_count`
9. `test_background_loop_stops_cleanly_on_stop_event`
10. `test_semantic_pattern_is_immutable`
11. `test_surprise_threshold_gate_excludes_low_surprise`
12. `test_frequency_threshold_gate_excludes_low_frequency`

### Test Skeletons

```python
def test_hybrid_scoring_weights_sum_to_one():
    """HYBRID weights 0.3+0.4+0.3 must equal 1.0 and produce expected ordering."""
    config = ConsolidatorConfig(strategy=ConsolidationStrategy.HYBRID)
    mc = AsyncMemoryConsolidator(
        temporal_graph=FakeGraph(),
        world_model=FakeWorldModel(),
        surprise_detector=FakeSurpriseDetector(),
        config=config,
    )
    # trace A: high frequency, low surprise, recent
    trace_a = EpisodicTrace("a", frozenset({"e1"}), time.monotonic_ns(), 0.1, 10, False)
    # trace B: low frequency, high surprise, recent
    trace_b = EpisodicTrace("b", frozenset({"e2"}), time.monotonic_ns(), 0.9, 1, False)
    score_a = mc._score_trace(trace_a, max_freq=10)
    score_b = mc._score_trace(trace_b, max_freq=10)
    # A should beat B: frequency weight 0.4 * 1.0 vs 0.4 * 0.1
    assert score_a > score_b
    # weights sanity: 0.3 + 0.4 + 0.3 == 1.0
    assert abs(0.3 + 0.4 + 0.3 - 1.0) < 1e-9


@pytest.mark.asyncio
async def test_dry_run_no_mutations():
    """dry_run=True must not call world_model.upsert_pattern()."""
    fake_world = MagicMock(spec=WorldModel)
    config = ConsolidatorConfig(
        strategy=ConsolidationStrategy.HYBRID,
        dry_run=True,
    )
    mc = AsyncMemoryConsolidator(
        temporal_graph=FakeGraphWithTraces(),
        world_model=fake_world,
        surprise_detector=FakeSurpriseDetector(),
        config=config,
    )
    count = await mc.consolidate()
    fake_world.upsert_pattern.assert_not_called()
    assert count == 0  # dry_run does not update _patterns
```

---

## 14-Step Implementation Order

1. Add `ConsolidationStrategy` enum to `asi_build/memory/types.py`
2. Add `EpisodicTrace` frozen dataclass
3. Add `SemanticPattern` frozen dataclass
4. Add `ConsolidatorConfig` frozen dataclass with all defaults
5. Define `MemoryConsolidator` Protocol with `@runtime_checkable`
6. Implement `_compute_centroid()` helper (key-union centroid, numeric mean, string mode)
7. Implement `_score_trace()` dispatch over 4 strategies
8. Implement `_consolidate_trace()` with dry_run guard
9. Implement `sweep()` with `asyncio.Lock` per-sweep
10. Implement `consolidate()`, `get_patterns()`, `prune_old_traces()`
11. Implement `_run_consolidation_loop()` with `asyncio.wait_for` stop pattern
12. Implement `start()` / `stop()` lifecycle methods
13. Implement `NullMemoryConsolidator` and `make_memory_consolidator()` factory
14. Add Prometheus metrics (Counter×3, Histogram×1, Gauge×1) and emit in `sweep()` + `_consolidate_trace()`

---

## Phase 18 Sub-Phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 18.1 | HorizonPlanner | [#450](https://github.com/web3guru888/asi-build/issues/450) | 🟡 Spec'd |
| 18.2 | MemoryConsolidator | [#453](https://github.com/web3guru888/asi-build/issues/453) | 🟡 Spec'd |
| 18.3 | DistributedTemporalSync | TBD | ⏳ Upcoming |
| 18.4 | CausalMemoryIndex | TBD | ⏳ Upcoming |
| 18.5 | TemporalCoherenceArbiter | TBD | ⏳ Upcoming |

---

## Cross-Phase Integration Map

| Phase | Component | Integration Point |
|---|---|---|
| 13.1 | WorldModel | SemanticPattern upsert target |
| 13.4 | SurpriseDetector | `surprise_score` on EpisodicTrace |
| 17.1 | TemporalGraph | episodic trace source + `get_unconsolidated_traces()` |
| 17.2 | EventSequencer | event ordering before trace creation |
| 17.3 | PredictiveEngine | basis_window_ids may reference consolidated patterns |
| 17.5 | TemporalOrchestrator | calls `MemoryConsolidator.start()/stop()` in lifecycle |
| 18.1 | HorizonPlanner | consumes `WorldModel` semantic patterns for horizon classification |
| 16.5 | ReflectionCycle | `active_patterns_count` metric feeds self-improvement loop |
