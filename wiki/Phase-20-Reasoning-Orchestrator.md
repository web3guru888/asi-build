# Phase 20.5 — ReasoningOrchestrator

> **Multi-strategy reasoning pipeline, confidence aggregation & cognitive integration — Phase 20 capstone.**

| Field | Value |
|---|---|
| **Package** | `asi.reasoning.orchestrator` |
| **Since** | Phase 20.5 |
| **Depends on** | LogicalInferenceEngine 20.1, AnalogicalReasoner 20.2, KnowledgeFusion 20.3, AbductiveReasoner 20.4 |
| **Integrates with** | CognitiveCycle, GoalRegistry 10.1, SemanticParser 19.1, TemporalOrchestrator 17.5, CommunicationOrchestrator 19.5 |
| **Complexity** | High — multi-strategy dispatch, parallel fusion, confidence aggregation |

---

## Overview

The **ReasoningOrchestrator** is the capstone of Phase 20 (Knowledge Synthesis & Reasoning). It composes all four Phase 20 sub-components — LogicalInferenceEngine (20.1), AnalogicalReasoner (20.2), KnowledgeFusion (20.3 → #482), and AbductiveReasoner (20.4 → #483) — into a **unified multi-strategy reasoning pipeline**.

For any reasoning query, the orchestrator:

1. Executes a **configurable strategy chain** (default: deductive → analogical → abductive fallback)
2. **Aggregates confidence** across strategy results using pluggable methods (weighted average, max, Bayesian)
3. Produces a **full ReasoningTrace** capturing every strategy attempt, timing, and the final aggregated conclusion
4. Exposes a **single `reason()` entry-point** for the CognitiveCycle

The design follows the same composition-over-inheritance pattern used in TemporalOrchestrator (17.5) and CommunicationOrchestrator (19.5): each sub-component is injected via its Protocol, and the orchestrator coordinates without subclassing.

### Design Principles

| Principle | Rationale |
|---|---|
| **Composition over inheritance** | Sub-components injected via Protocol; no MRO complexity |
| **Strategy chain** | Configurable fallback order allows domain-specific tuning |
| **Early stop** | If a strategy exceeds the confidence threshold, skip remaining |
| **Parallel fusion** | KnowledgeFusion runs in background while sequential strategies execute |
| **LRU trace store** | Bounded memory for reasoning history; eviction prevents unbounded growth |
| **Frozen dataclasses** | Immutable queries, results, and traces |

---

## Enums

### `ReasoningStrategy`

```python
from enum import Enum, auto

class ReasoningStrategy(Enum):
    """Available reasoning strategies."""
    DEDUCTIVE   = auto()  # Formal logical inference (modus ponens, resolution)
    ANALOGICAL  = auto()  # Cross-domain structural mapping
    ABDUCTIVE   = auto()  # Best-explanation hypothesis generation
    FUSION      = auto()  # Multi-source knowledge integration
    COMPOSITE   = auto()  # Full chain (multiple strategies combined)
```

### `ReasoningPhase`

```python
class ReasoningPhase(Enum):
    """Orchestrator execution phases."""
    IDLE        = auto()
    DEDUCTING   = auto()  # Running LogicalInferenceEngine
    ANALOGISING = auto()  # Running AnalogicalReasoner
    ABDUCTING   = auto()  # Running AbductiveReasoner
    FUSING      = auto()  # Running KnowledgeFusion
    AGGREGATING = auto()  # Combining strategy results
    COMPLETE    = auto()
    FAILED      = auto()
```

### `ConfidenceLevel`

```python
class ConfidenceLevel(Enum):
    """Discretised confidence for downstream consumers."""
    HIGH   = auto()  # confidence >= 0.85
    MEDIUM = auto()  # 0.50 <= confidence < 0.85
    LOW    = auto()  # confidence < 0.50
```

---

## Frozen Dataclasses

### `ReasoningQuery`

```python
@dataclass(frozen=True, slots=True)
class ReasoningQuery:
    """Immutable reasoning request."""
    query_id: str                                   # UUID
    question: str                                   # Natural language or structured query
    context: dict[str, Any]                         # Arbitrary context (goals, memory refs, etc.)
    preferred_strategy: ReasoningStrategy | None     # Hint; None = use full chain
    max_time_s: float                               # Per-query timeout budget
```

### `StrategyResult`

```python
@dataclass(frozen=True, slots=True)
class StrategyResult:
    """Result from a single reasoning strategy."""
    strategy: ReasoningStrategy
    conclusion: str
    confidence: float                               # 0.0–1.0
    evidence: tuple[str, ...]                       # Supporting evidence / proof steps
    elapsed_ms: float
    success: bool                                   # False if strategy raised or timed out
```

### `ReasoningTrace`

```python
@dataclass(frozen=True, slots=True)
class ReasoningTrace:
    """Full trace of a multi-strategy reasoning session."""
    query: ReasoningQuery
    phase: ReasoningPhase
    strategy_results: tuple[StrategyResult, ...]    # Every strategy attempt in order
    final_conclusion: str
    aggregated_confidence: float
    confidence_level: ConfidenceLevel
    total_elapsed_ms: float
    timestamp_ns: int                               # time.time_ns()
```

### `OrchestratorConfig`

```python
@dataclass(frozen=True, slots=True)
class OrchestratorConfig:
    """Immutable orchestrator configuration."""
    strategy_chain: tuple[ReasoningStrategy, ...] = (
        ReasoningStrategy.DEDUCTIVE,
        ReasoningStrategy.ANALOGICAL,
        ReasoningStrategy.ABDUCTIVE,
    )
    confidence_threshold: float = 0.70               # Early-stop if any strategy >= this
    max_time_s: float = 10.0                         # Default per-query budget
    enable_fusion: bool = True                       # Run KnowledgeFusion in parallel
    aggregation_method: str = "weighted_average"     # "weighted_average" | "max" | "bayesian"
    max_traces: int = 1000                           # Trace store capacity (LRU eviction)
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ReasoningOrchestrator(Protocol):
    """Unified reasoning pipeline interface."""

    async def reason(self, query: ReasoningQuery) -> ReasoningTrace:
        """Execute full strategy chain and return aggregated trace."""
        ...

    async def reason_with_strategy(
        self, query: ReasoningQuery, strategy: ReasoningStrategy
    ) -> StrategyResult:
        """Execute a single named strategy (bypass chain)."""
        ...

    async def get_trace(self, query_id: str) -> ReasoningTrace | None:
        """Retrieve a stored reasoning trace by query_id."""
        ...

    async def health(self) -> dict[str, bool]:
        """Health probe for each sub-component."""
        ...

    async def start(self) -> None:
        """Initialise sub-components and background tasks."""
        ...

    async def stop(self) -> None:
        """Graceful shutdown."""
        ...
```

---

## Implementation — `AsyncReasoningOrchestrator`

### Construction

```python
import asyncio
import time
from collections import OrderedDict

class AsyncReasoningOrchestrator:
    """Production multi-strategy reasoning pipeline.

    Composition (no subclassing):
      - inference_engine: LogicalInferenceEngine   (Phase 20.1)
      - analogical:       AnalogicalReasoner       (Phase 20.2)
      - fusion:           KnowledgeFusion          (Phase 20.3 → #482)
      - abductive:        AbductiveReasoner        (Phase 20.4 → #483)
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        inference_engine: LogicalInferenceEngine,
        analogical: AnalogicalReasoner,
        fusion: KnowledgeFusion,
        abductive: AbductiveReasoner,
    ) -> None: ...
```

### Core Pipeline — `reason()`

```
Algorithm:
1. Start KnowledgeFusion enrichment in background (if enable_fusion)
2. Iterate strategy_chain in order:
   a. Dispatch to _run_strategy() with per-strategy timeout
   b. If result.confidence >= confidence_threshold → early stop
3. Wait for fusion task (if running)
4. Aggregate all StrategyResults → final conclusion + confidence
5. Store trace in LRU OrderedDict
6. Return ReasoningTrace
```

### Strategy Dispatch

```python
async def _run_strategy(
    self, query: ReasoningQuery, strategy: ReasoningStrategy, timeout_s: float
) -> StrategyResult:
    """Dispatch to the appropriate sub-component with asyncio.wait_for.

    match strategy:
        case DEDUCTIVE   → self._inference_engine.infer(...)
        case ANALOGICAL  → self._analogical.find_analogy(...)
        case ABDUCTIVE   → self._abductive.abduce(...)
        case FUSION      → self._fusion.fuse(...)
        case COMPOSITE   → self.reason(...)  # recursive full-chain

    On TimeoutError or Exception → StrategyResult(success=False, confidence=0.0)
    """
    ...
```

### Confidence Aggregation

```python
def _aggregate(
    self, results: list[StrategyResult], method: str
) -> tuple[str, float, ConfidenceLevel]:
    """Aggregate strategy results into a single conclusion + confidence.

    Methods:
      weighted_average: Σ(w_i × c_i) / Σ(w_i)
                       where w_i = (1 / rank_i) × c_i (successful only)
      max:             Take result with highest confidence
      bayesian:        Π(c_i) / (Π(c_i) + Π(1 - c_i))
                       (naive Bayesian combination of independent estimates)

    Returns (best_conclusion, aggregated_confidence, confidence_level).
    """
    ...

@staticmethod
def _classify_confidence(c: float) -> ConfidenceLevel:
    if c >= 0.85: return ConfidenceLevel.HIGH
    if c >= 0.50: return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW
```

### Trace Store

```python
async def get_trace(self, query_id: str) -> ReasoningTrace | None:
    async with self._lock:
        return self._traces.get(query_id)
```

LRU eviction via `OrderedDict` — when `len(self._traces) > config.max_traces`, the oldest entry is popped.

### Health Probes

```python
async def health(self) -> dict[str, bool]:
    """Probe each sub-component; return {component_name: is_healthy}."""
    ...
```

### Lifecycle

```python
async def start(self) -> None:
    """Start all sub-components."""
    ...

async def stop(self) -> None:
    """Stop all sub-components; flush pending traces."""
    ...
```

---

## Null Implementation

```python
class NullReasoningOrchestrator:
    """No-op implementation for testing and DI."""
    async def reason(self, query: ReasoningQuery) -> ReasoningTrace:
        return ReasoningTrace(
            query=query, phase=ReasoningPhase.COMPLETE,
            strategy_results=(), final_conclusion="",
            aggregated_confidence=0.0, confidence_level=ConfidenceLevel.LOW,
            total_elapsed_ms=0.0, timestamp_ns=time.time_ns(),
        )
    async def reason_with_strategy(self, q, s) -> StrategyResult:
        return StrategyResult(s, "", 0.0, (), 0.0, False)
    async def get_trace(self, query_id): return None
    async def health(self): return {}
    async def start(self): pass
    async def stop(self): pass
```

---

## Factory

```python
def make_reasoning_orchestrator(
    config: OrchestratorConfig | None = None,
    inference_engine: LogicalInferenceEngine | None = None,
    analogical: AnalogicalReasoner | None = None,
    fusion: KnowledgeFusion | None = None,
    abductive: AbductiveReasoner | None = None,
) -> ReasoningOrchestrator:
    """Create production or null orchestrator depending on available sub-components."""
    if all(c is not None for c in (inference_engine, analogical, fusion, abductive)):
        return AsyncReasoningOrchestrator(
            config or OrchestratorConfig(),
            inference_engine, analogical, fusion, abductive,
        )
    return NullReasoningOrchestrator()
```

---

## Data Flow

```
                  ┌────────────────────────────────────────────────────┐
                  │           ReasoningOrchestrator 20.5               │
                  │                                                     │
  ReasoningQuery ─┤  ┌── LogicalInferenceEngine 20.1  (DEDUCTIVE)     │
                  │  ├── AnalogicalReasoner 20.2       (ANALOGICAL)    │
                  │  ├── AbductiveReasoner 20.4        (ABDUCTIVE)     │
                  │  └── KnowledgeFusion 20.3  (#482)  (FUSION ∥)     │
                  │                                                     │
                  │  → _aggregate() → ReasoningTrace                   │
                  └──────────────────┬─────────────────────────────────┘
                                     │
                    CognitiveCycle._reasoning_step()
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
   GoalRegistry 10.1         SemanticParser 19.1       TemporalOrchestrator 17.5
   (action from conclusion)  (query construction)      (record reasoning events)
          │                                                     │
   CommunicationOrchestrator 19.5                    TemporalGraph 17.1
   (human-readable explanation)                      (event persistence)
```

---

## Integration Map

### CognitiveCycle → `reason()`

The main cognitive loop calls `orchestrator.reason(query)` during its reasoning step. The `ReasoningTrace` drives downstream action planning via `GoalRegistry`.

### SemanticParser 19.1 → Query Construction

`SemanticParser.parse()` converts natural-language user input into a structured `ReasoningQuery`, selecting the appropriate `preferred_strategy` based on query intent.

### CommunicationOrchestrator 19.5 → Explanation

Renders `ReasoningTrace` into human-readable multi-step reasoning explanations, including which strategies contributed and their individual confidence scores.

### GoalRegistry 10.1 → Action Planning

`trace.final_conclusion` feeds into `GoalRegistry` to drive downstream planning — confirmed conclusions become goals for the action system.

### TemporalOrchestrator 17.5 → Event Persistence

Records `ReasoningTrace` events in the `TemporalGraph` for causal tracking and temporal reasoning.

### KnowledgeFusion 20.3 → Parallel Enrichment

When `enable_fusion=True`, the orchestrator starts a background `fuse()` task that enriches the shared knowledge base while sequential strategies execute, ensuring all strategies benefit from the latest fused knowledge.

### Cross-Phase Integration Table

| Consumer | Interface | Data Flow |
|---|---|---|
| **CognitiveCycle** | `orchestrator.reason(query)` → `ReasoningTrace` | Main reasoning step; feeds conclusion to GoalRegistry |
| **SemanticParser 19.1** | Parses user input → `ReasoningQuery` | Converts natural language to structured query |
| **CommunicationOrchestrator 19.5** | Renders `ReasoningTrace` → explanation | Human-readable multi-step reasoning display |
| **GoalRegistry 10.1** | `trace.final_conclusion` → goal/action | Drives downstream planning from reasoning output |
| **TemporalOrchestrator 17.5** | Records `ReasoningTrace` events | Temporal event persistence & causal tracking |
| **KnowledgeFusion 20.3** | Parallel enrichment during reasoning | Supplies merged knowledge for strategy execution |

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `asi_reasoning_query_total` | Counter | `strategy` | Total reasoning queries dispatched |
| `asi_reasoning_query_seconds` | Histogram | — | End-to-end reasoning latency (full chain) |
| `asi_reasoning_strategy_seconds` | Histogram | `strategy` | Per-strategy execution latency |
| `asi_reasoning_confidence` | Histogram | — | Aggregated confidence score distribution |
| `asi_reasoning_fallback_total` | Counter | — | Queries that fell through to next strategy in chain |

### PromQL Examples

```promql
# Average end-to-end reasoning latency (5m window)
rate(asi_reasoning_query_seconds_sum[5m]) / rate(asi_reasoning_query_seconds_count[5m])

# Fallback rate (% of queries needing > 1 strategy)
rate(asi_reasoning_fallback_total[5m]) / rate(asi_reasoning_query_total[5m])

# Confidence distribution (p50, p99)
histogram_quantile(0.50, rate(asi_reasoning_confidence_bucket[5m]))
histogram_quantile(0.99, rate(asi_reasoning_confidence_bucket[5m]))

# Per-strategy success rate
rate(asi_reasoning_query_total{strategy="DEDUCTIVE"}[5m])
```

### Grafana Alerts

```yaml
- alert: ReasoningLatencyHigh
  expr: histogram_quantile(0.95, rate(asi_reasoning_query_seconds_bucket[5m])) > 5
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "95th percentile reasoning latency exceeds 5s"

- alert: ReasoningConfidenceLow
  expr: histogram_quantile(0.50, rate(asi_reasoning_confidence_bucket[5m])) < 0.5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Median reasoning confidence below 0.5 for 10m"

- alert: ReasoningFallbackRateHigh
  expr: rate(asi_reasoning_fallback_total[5m]) / rate(asi_reasoning_query_total[5m]) > 0.8
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "80%+ queries falling back beyond first strategy"
```

---

## mypy Strict Compliance

| Pattern | Technique |
|---|---|
| `ReasoningStrategy \| None` | Explicit `if strategy is not None` guard |
| `dict[str, Any]` context | Type-narrow with `TypeGuard` or runtime checks |
| `match/case` dispatch | Exhaustive match on `ReasoningStrategy` with `assert_never` fallback |
| `tuple[StrategyResult, ...]` | Immutable; avoid `list` for frozen dataclass fields |
| `OrderedDict` trace store | `OrderedDict[str, ReasoningTrace]` with explicit type annotation |
| `asyncio.wait_for` return | Explicitly typed; handle `asyncio.TimeoutError` |
| Protocol fields | `@runtime_checkable` with `isinstance` guard at factory boundary |

---

## Test Targets (12)

| # | Test | Validates |
|---|---|---|
| 1 | `test_reason_full_chain_returns_trace` | Full strategy chain produces ReasoningTrace with all results |
| 2 | `test_reason_early_stop_on_high_confidence` | Strategy with confidence ≥ 0.70 stops the chain |
| 3 | `test_reason_with_strategy_deductive` | Single DEDUCTIVE strategy produces StrategyResult |
| 4 | `test_reason_with_strategy_analogical` | Single ANALOGICAL strategy produces StrategyResult |
| 5 | `test_reason_with_strategy_abductive` | Single ABDUCTIVE strategy produces StrategyResult |
| 6 | `test_fusion_runs_parallel_during_chain` | KnowledgeFusion task starts before first strategy completes |
| 7 | `test_aggregate_weighted_average` | Weighted average aggregation produces correct confidence |
| 8 | `test_aggregate_max` | Max aggregation picks highest-confidence result |
| 9 | `test_aggregate_bayesian` | Bayesian aggregation computes correct combined posterior |
| 10 | `test_timeout_produces_failed_result` | Per-strategy timeout → StrategyResult(success=False) |
| 11 | `test_trace_store_lru_eviction` | Exceeding max_traces evicts oldest entry |
| 12 | `test_health_probes_all_subcomponents` | health() returns status for all 4 sub-components |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_reason_full_chain_returns_trace():
    orchestrator = make_reasoning_orchestrator(
        config=OrchestratorConfig(),
        inference_engine=mock_inference_engine(),
        analogical=mock_analogical_reasoner(),
        fusion=mock_knowledge_fusion(),
        abductive=mock_abductive_reasoner(),
    )
    await orchestrator.start()
    query = ReasoningQuery("q1", "Why did the temperature spike?", {}, None, 10.0)
    trace = await orchestrator.reason(query)
    assert trace.phase == ReasoningPhase.COMPLETE
    assert len(trace.strategy_results) >= 1
    assert trace.aggregated_confidence >= 0.0
    await orchestrator.stop()

@pytest.mark.asyncio
async def test_reason_early_stop_on_high_confidence():
    orchestrator = make_reasoning_orchestrator(
        config=OrchestratorConfig(confidence_threshold=0.70),
        inference_engine=mock_inference_engine(confidence=0.95),
        analogical=mock_analogical_reasoner(),
        fusion=mock_knowledge_fusion(),
        abductive=mock_abductive_reasoner(),
    )
    await orchestrator.start()
    query = ReasoningQuery("q2", "Is X true?", {}, None, 10.0)
    trace = await orchestrator.reason(query)
    # Should early-stop after DEDUCTIVE succeeds with 0.95
    assert len(trace.strategy_results) == 1
    assert trace.strategy_results[0].strategy == ReasoningStrategy.DEDUCTIVE
    await orchestrator.stop()
```

---

## Implementation Order

1. Create `asi/reasoning/orchestrator/__init__.py` with `__all__`
2. Define `ReasoningStrategy`, `ReasoningPhase`, `ConfidenceLevel` enums
3. Define frozen dataclasses: `ReasoningQuery`, `StrategyResult`, `ReasoningTrace`, `OrchestratorConfig`
4. Define `ReasoningOrchestrator` Protocol (`@runtime_checkable`)
5. Implement `NullReasoningOrchestrator`
6. Implement `_classify_confidence()` static method
7. Implement `_aggregate()` with weighted_average method
8. Add max and bayesian aggregation methods
9. Implement `_run_strategy()` dispatch with `asyncio.wait_for` timeout
10. Implement `reason()` — full chain with early-stop + parallel fusion
11. Implement `reason_with_strategy()` — single strategy bypass
12. Implement trace store (LRU `OrderedDict` + `asyncio.Lock`)
13. Implement `health()`, `start()`, `stop()` lifecycle
14. Add `make_reasoning_orchestrator()` factory + Prometheus metrics

---

## Phase 20 — Knowledge Synthesis & Reasoning — Sub-phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 20.1 | LogicalInferenceEngine | #484 | 🟡 Spec'd |
| 20.2 | AnalogicalReasoner | #485 | 🟡 Spec'd |
| 20.3 | KnowledgeFusion | #482 | 🟡 Spec'd |
| 20.4 | AbductiveReasoner | #483 | 🟡 Spec'd |
| **20.5** | **ReasoningOrchestrator** | **#486** | **🟡 Spec'd** |

> **Phase 20 delivers**: a complete knowledge synthesis & reasoning subsystem with deductive logic, analogical mapping, abductive hypothesis generation, multi-source knowledge fusion, and a unified orchestrator that chains strategies, aggregates confidence, and integrates with the CognitiveCycle.

---

*Tracking: #109 · Discussion: #481*
