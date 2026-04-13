# Phase 8.1 — DecisionTracer: Causal Attribution and Introspection

**Phase**: 8.1 · **Sub-system**: Explainability / Introspection  
**Issue**: [#276](https://github.com/web3guru888/asi-build/issues/276)  
**Discussions**: [#277 (S&T)](https://github.com/web3guru888/asi-build/discussions/277) · [#278 (Q&A)](https://github.com/web3guru888/asi-build/discussions/278) · [#279 (Ideas)](https://github.com/web3guru888/asi-build/discussions/279)  
**Depends on**: Phase 7.5 (`SleepPhaseOrchestrator`), Phase 5 (`CognitiveCycle`)

---

## Motivation

ASI-Build has 4 936+ tests, 222K+ LOC, a live Sepolia bridge, and a complete meta-learning stack (Phases 1–7). The missing observability layer is **decision explanation**: why did the agent choose action A over B? Which memories, modules, and weights contributed?

`DecisionTracer` answers this without requiring an LLM — via deterministic attribution strategies operating on numpy weight arrays, KG edge scores, and module activity logs.

---

## Architecture

```
CognitiveCycle tick
       │
       ▼
   DecisionTracer.trace(candidates, scores, context)
       │
       ├─▶  AttributionStrategy.attribute()
       │         ├── UniformAttribution   (equal weights — O(n) baseline)
       │         ├── SaliencyAttribution  (|∂score/∂w|, numpy finite-diff)
       │         ├── AttentionAttribution (KG edge-weight rollout)
       │         └── ShapleyAttribution   (256-perm approx, asyncio executor)
       │
       ├─▶  Contributor list (normalised to 1.0, sorted desc by score)
       │
       ├─▶  DecisionTrace (frozen dataclass, uuid4 trace_id)
       │
       └─▶  TraceStorage.save(trace)
                 ├── InMemoryTraceStorage  (deque ring-buffer, O(1) eviction)
                 └── JsonlTraceStorage     (append-only .jsonl, aiofiles)
```

---

## Data Models

### `Contributor` (frozen dataclass)

```python
@dataclass(frozen=True)
class Contributor:
    source:  str    # module / memory key / hook id
    kind:    str    # "memory" | "module" | "weight" | "hook" | "external"
    score:   float  # attribution score in [0, 1], normalised across contributors
    excerpt: str    # human-readable snippet ≤ 200 chars
```

### `DecisionTrace` (frozen dataclass)

```python
@dataclass(frozen=True)
class DecisionTrace:
    trace_id:     str                 # uuid4 hex
    tick:         int                 # CognitiveCycle tick counter
    timestamp:    float               # time.time()
    chosen:       str                 # selected action / output key
    candidates:   list[str]           # all evaluated alternatives
    scores:       dict[str, float]    # raw score per candidate
    contributors: list[Contributor]   # ranked evidence sources (normalised)
    metadata:     dict[str, Any]      # freeform: task_id, phase, etc.
```

### `TraceContext` (dataclass)

```python
@dataclass
class TraceContext:
    tick:           int
    task_id:        str
    active_modules: list[str]         # modules active this tick
    memory_hits:    list[str]         # memory keys accessed
    hook_results:   list[HookResult]  # from SleepPhaseOrchestrator
    extra:          dict[str, Any]    # freeform
```

### `TraceSnapshot` (frozen dataclass)

```python
@dataclass(frozen=True)
class TraceSnapshot:
    total_traces:     int
    storage_kind:     str      # "memory" | "jsonl"
    strategy_kind:    str      # "uniform" | "saliency" | "attention" | "shapley"
    recent_trace_ids: list[str]  # last 5 trace_ids
```

---

## Attribution Strategies

### Strategy comparison table

| Strategy | Complexity | Requires | Best for |
|---|---|---|---|
| `UniformAttribution` | O(n) | nothing | baseline, debugging |
| `SaliencyAttribution` | O(n·p) | `get_weights()` on learner | weight-driven decisions |
| `AttentionAttribution` | O(e) | KG edge scores | knowledge-graph lookups |
| `ShapleyAttribution` | O(256·n) | active_modules + memory_hits | full causal attribution |

*n = source count, p = weight parameter count, e = KG edge count*

### `AttributionStrategy` Protocol

```python
@runtime_checkable
class AttributionStrategy(Protocol):
    def attribute(
        self,
        candidates: list[str],
        scores: dict[str, float],
        context: TraceContext,
    ) -> list[Contributor]: ...
```

### `UniformAttribution`

Equal attribution weight to all active modules and memory hits:

```python
class UniformAttribution:
    def attribute(self, candidates, scores, context) -> list[Contributor]:
        sources = context.active_modules + context.memory_hits
        w = 1.0 / len(sources) if sources else 1.0
        return _normalise([
            Contributor(s, "module" if s in context.active_modules else "memory", w, "")
            for s in sources
        ])
```

### `SaliencyAttribution`

Finite-difference gradient approximation over learner weight arrays:

```python
class SaliencyAttribution:
    def __init__(self, learner: STDPOnlineLearner, ewc: EWCRegulariser | None = None):
        self._learner = learner
        self._ewc = ewc

    def attribute(self, candidates, scores, context) -> list[Contributor]:
        weights = self._learner.get_weights()          # numpy array
        mask = self._ewc.fisher_diag if self._ewc else np.ones_like(weights)
        saliency = np.abs(weights) * mask              # Fisher-weighted magnitude
        # Map to active modules by index slice
        ...
```

### `ShapleyAttribution`

256-permutation approximate Shapley values, run in `asyncio.get_running_loop().run_in_executor(None, ...)` to avoid blocking the event loop:

```python
class ShapleyAttribution:
    def __init__(self, n_permutations: int = 256, max_sources: int = 32):
        self.n_permutations = n_permutations
        self.max_sources = max_sources

    async def attribute(self, candidates, scores, context) -> list[Contributor]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._sync_shapley, candidates, scores, context
        )
```

---

## `DecisionTracer`

### Constructor

```python
class DecisionTracer:
    def __init__(
        self,
        strategy: AttributionStrategy,
        storage: TraceStorage,
        max_candidates: int = 32,
        async_flush: bool = True,   # True = non-blocking background save
    ) -> None: ...
```

### Core loop

```python
async def trace(
    self,
    candidates: list[str],
    scores: dict[str, float],
    context: TraceContext,
) -> DecisionTrace:
    _start = time.monotonic()
    chosen = max(scores, key=scores.__getitem__)
    contributors = await self._strategy.attribute(candidates[:self._max_candidates], scores, context)
    trace = DecisionTrace(
        trace_id=uuid.uuid4().hex,
        tick=context.tick,
        timestamp=time.time(),
        chosen=chosen,
        candidates=candidates[:self._max_candidates],
        scores=dict(scores),
        contributors=contributors,
        metadata=dict(context.extra),
    )
    if self._async_flush:
        asyncio.create_task(self._storage.save(trace))
    else:
        await self._storage.save(trace)
    elapsed = time.monotonic() - _start
    _TRACE_DURATION.labels(strategy=type(self._strategy).__name__.lower()).observe(elapsed)
    _TRACE_TOTAL.labels(strategy=type(self._strategy).__name__.lower()).inc()
    return trace
```

### `explain()` — deterministic natural-language output

```python
async def explain(self, trace_id: str) -> str:
    trace = await self._storage.load(trace_id)
    if trace is None:
        return f"No trace found for id={trace_id!r}"
    top = trace.contributors[:3]
    lines = [
        f"  {i+1}. [{c.kind}] {c.source} ({c.score:.2%})"
        for i, c in enumerate(top)
    ]
    return (
        f"Trace {trace.trace_id[:8]}... @ tick={trace.tick}\n"
        f"Chosen: {trace.chosen!r}  (score={trace.scores.get(trace.chosen, 0):.4f})\n"
        f"Top contributors:\n" + "\n".join(lines)
    )
```

---

## Storage Backends

### `TraceStorage` Protocol

```python
@runtime_checkable
class TraceStorage(Protocol):
    async def save(self, trace: DecisionTrace) -> None: ...
    async def load(self, trace_id: str) -> DecisionTrace | None: ...
    async def recent(self, n: int) -> list[DecisionTrace]: ...
```

### `InMemoryTraceStorage`

`collections.deque(maxlen=capacity)` ring-buffer with `dict` index for O(1) lookup:

```python
class InMemoryTraceStorage:
    def __init__(self, capacity: int = 1_000) -> None:
        self._buf: deque[DecisionTrace] = deque(maxlen=capacity)
        self._idx: dict[str, DecisionTrace] = {}
        self._lock = asyncio.Lock()
```

Memory budget:

| Capacity | Approx RAM |
|---|---|
| 100 | ~400 KB |
| 1 000 (default) | ~4 MB |
| 10 000 | ~40 MB |

### `JsonlTraceStorage`

Append-only `.jsonl` file using `aiofiles`:

```python
class JsonlTraceStorage:
    def __init__(self, path: str | Path, capacity: int = 10_000) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()

    async def save(self, trace: DecisionTrace) -> None:
        line = json.dumps(dataclasses.asdict(trace)) + "\n"
        async with self._lock:
            async with aiofiles.open(self._path, "a") as f:
                await f.write(line)
```

---

## `build_decision_tracer()` Factory

```python
def build_decision_tracer(
    strategy: str = "uniform",      # "saliency" | "attention" | "shapley" | "uniform"
    storage: str = "memory",        # "memory" | "jsonl"
    jsonl_path: str | None = None,
    buffer_capacity: int = 1_000,
    async_flush: bool = True,
) -> DecisionTracer:
    _storage = (
        InMemoryTraceStorage(capacity=buffer_capacity)
        if storage == "memory"
        else JsonlTraceStorage(path=jsonl_path or "traces.jsonl")
    )
    _strategy = {
        "uniform":   UniformAttribution(),
        "saliency":  SaliencyAttribution(...),
        "attention": AttentionAttribution(),
        "shapley":   ShapleyAttribution(),
    }[strategy]
    return DecisionTracer(
        strategy=_strategy,
        storage=_storage,
        async_flush=async_flush,
    )
```

---

## CognitiveCycle Integration

```python
# At end of each tick in CognitiveCycle:
context = TraceContext(
    tick=self._tick,
    task_id=current_task.id,
    active_modules=list(self._active_modules),
    memory_hits=self._last_memory_hits,
    hook_results=orchestrator_result.hook_results,
    extra={"phase": "decision"},
)
trace = await self._tracer.trace(
    candidates=list(action_scores.keys()),
    scores=action_scores,
    context=context,
)
tick_metadata["trace_id"] = trace.trace_id
```

---

## Prometheus Metrics

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `asi_trace_total` | Counter | `strategy` | Total traces recorded |
| `asi_trace_duration_seconds` | Histogram | `strategy` | Attribution latency |
| `asi_trace_candidates` | Histogram | — | Candidate set size dist. |
| `asi_trace_storage_size` | Gauge | `backend` | Current stored count |
| `asi_explain_total` | Counter | `strategy` | Explain() call rate |

### Key PromQL

```promql
# Trace throughput by strategy
rate(asi_trace_total[5m])

# p99 attribution latency
histogram_quantile(0.99, rate(asi_trace_duration_seconds_bucket[5m]))

# Storage fill alert (memory backend > 900)
asi_trace_storage_size{backend="memory"} > 900

# Candidate set explosion
histogram_quantile(0.95, rate(asi_trace_candidates_bucket[5m]))
```

---

## Test Targets (12 minimum)

| # | Test | What it verifies |
|---|---|---|
| 1 | `test_trace_produces_valid_dataclass` | All required fields populated |
| 2 | `test_contributor_scores_sum_to_one` | Normalisation invariant |
| 3 | `test_uniform_attribution_equal_scores` | Equal-weight baseline |
| 4 | `test_saliency_attribution_gradient_sign` | Sign consistency with weights |
| 5 | `test_shapley_attribution_n_permutations` | Correct sample count (mock) |
| 6 | `test_attention_attribution_rollout` | KG edge weight rollout |
| 7 | `test_in_memory_storage_capacity_eviction` | Oldest trace evicted at capacity |
| 8 | `test_jsonl_storage_roundtrip` | Save → load fidelity |
| 9 | `test_get_recent_ordering` | Newest first |
| 10 | `test_explain_returns_string` | Non-empty natural-language output |
| 11 | `test_async_flush_does_not_block` | Returns before storage completes |
| 12 | `test_snapshot_reflects_state` | `TraceSnapshot` counts match storage |

---

## 10-Step Implementation Order

1. `models.py` — `Contributor` + `DecisionTrace` frozen dataclasses + `__str__` repr
2. `attribution.py` — `AttributionStrategy` Protocol + `UniformAttribution`
3. `attribution.py` — `SaliencyAttribution` (numpy finite-diff proxy)
4. `attribution.py` — `AttentionAttribution` (KG edge rollout)
5. `attribution.py` — `ShapleyAttribution` (256-perm approx, asyncio executor)
6. `trace_storage.py` — `TraceStorage` Protocol + `InMemoryTraceStorage` (deque + asyncio.Lock)
7. `trace_storage.py` — `JsonlTraceStorage` (aiofiles append + index rebuild on load)
8. `decision_tracer.py` — `TraceContext` + `DecisionTracer` core loop + `explain()`
9. `factory.py` — `build_decision_tracer()` + Prometheus pre-init
10. Tests for all 12 targets (pytest-asyncio, mock time + CollectorRegistry isolation)

---

## Phase 8 Roadmap

| Sub-phase | Component | Status |
|---|---|---|
| **8.1** | `DecisionTracer` — causal attribution core | 🟡 In spec (#276) |
| **8.2** | `CausalGraph` — decision lineage DAG | 🔵 Planned |
| **8.3** | `ExplainAPI` — REST/WebSocket trace endpoint | 🔵 Planned |
| **8.4** | Docker multi-stage + Helm chart | 🔵 Planned |
| **8.5** | Sepolia CI integration + bridge health metrics | 🔵 Planned |

See discussion [#279](https://github.com/web3guru888/asi-build/discussions/279) for full Phase 8 direction thread.
