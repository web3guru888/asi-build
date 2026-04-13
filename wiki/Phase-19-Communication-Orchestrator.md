# Phase 19.5 — CommunicationOrchestrator

> **Module**: `asi.nlu.orchestrator`
> **Since**: Phase 19.5
> **Issue**: [#470](https://github.com/web3guru888/asi-build/issues/470)
> **Depends on**: Phase 19.1 SemanticParser · Phase 19.2 DialogueManager · Phase 19.3 ResponseGenerator · Phase 19.4 MultiModalEncoder

---

## Overview

`CommunicationOrchestrator` is the **capstone component** of the Phase 19 Natural-Language Understanding pipeline. It ties together every NLU sub-component — routing raw input through **MultiModalEncoder → SemanticParser → DialogueManager → ResponseGenerator** — and manages the full request-response lifecycle with per-stage latency tracking, provenance tracing, and graceful degradation on partial failures.

Where each earlier sub-phase focuses on a single concern (encoding modalities, parsing semantics, managing dialogue state, generating responses), CommunicationOrchestrator provides the **single entry-point** that the CognitiveCycle calls on every interaction turn. It guarantees that:

1. Every input is routed through all four stages in order.
2. Per-stage timing is recorded for profiling and alerting.
3. A `PipelineTrace` provenance record is kept for every request — successful or not.
4. Partial failures are caught and downgraded to a fallback response rather than propagating exceptions.
5. A health-check endpoint exercises each sub-component independently.

This mirrors the `TemporalOrchestrator` (Phase 17.5) pattern — **composition over inheritance**, loose coupling via Protocol injection, and a lifecycle (`start` / `stop`) that the outer CognitiveCycle manages.

---

## Enums

### `PipelineStage`

```python
class PipelineStage(str, Enum):
    ENCODING   = "encoding"
    PARSING    = "parsing"
    DIALOGUE   = "dialogue"
    GENERATING = "generating"
    COMPLETE   = "complete"
    FAILED     = "failed"
```

**State transition table**

| From | To | Trigger |
|------|----|---------|
| — | ENCODING | `process()` called |
| ENCODING | PARSING | Embedding produced |
| PARSING | DIALOGUE | SemanticFrame extracted |
| DIALOGUE | GENERATING | DialogueState updated |
| GENERATING | COMPLETE | GeneratedResponse returned |
| _any_ | FAILED | Exception or timeout |

The `COMPLETE` and `FAILED` states are terminal — no further transitions occur within a single pipeline invocation.

---

## Data Structures

All structures are **frozen dataclasses** (`@dataclass(frozen=True, slots=True)`).

### `PipelineTrace`

```python
@dataclass(frozen=True, slots=True)
class PipelineTrace:
    trace_id: str                                  # uuid4 hex
    stage: PipelineStage                           # terminal stage reached
    input_hash: str                                # SHA-256 of raw input
    embedding: tuple[float, ...] | None            # from MultiModalEncoder
    frame: "SemanticFrame | None"                  # from SemanticParser
    state: "DialogueState | None"                  # from DialogueManager
    response: "GeneratedResponse | None"           # from ResponseGenerator
    error: str | None                              # exception message if FAILED
    latency_ms: dict[PipelineStage, float]         # per-stage wall-clock ms
    timestamp_ns: int                              # time.monotonic_ns() at start
```

`latency_ms` only contains entries for stages that **actually executed**; a FAILED trace after PARSING will have keys `ENCODING` and `PARSING` but not `DIALOGUE` or `GENERATING`.

### `OrchestratorConfig`

```python
@dataclass(frozen=True, slots=True)
class OrchestratorConfig:
    encoder_config: "MultiModalEncoderConfig"
    parser_config: "SemanticParserConfig"
    dialogue_config: "DialogueManagerConfig"
    generator_config: "ResponseGeneratorConfig"
    max_pipeline_time_s: float = 5.0               # asyncio.wait_for timeout
    trace_enabled: bool = True                      # store PipelineTrace records
    fallback_response: str = "I'm sorry, I couldn't process that right now."
```

`max_pipeline_time_s` is enforced as a **total** pipeline budget, not per-stage. Individual sub-component timeouts should be configured through their own config objects; this is the outer safety net.

---

## Protocol

```python
@runtime_checkable
class CommunicationOrchestrator(Protocol):
    async def process(self, text: str, *, session_id: str = "default") -> "GeneratedResponse":
        """Run the full NLU pipeline on text input."""
        ...

    async def process_multimodal(
        self,
        payload: bytes,
        modality: str,
        *,
        session_id: str = "default",
    ) -> "GeneratedResponse":
        """Run the full NLU pipeline on a non-text modality (image, audio)."""
        ...

    def get_trace(self, trace_id: str) -> PipelineTrace | None:
        """Retrieve a stored PipelineTrace by ID."""
        ...

    async def health(self) -> dict[str, bool]:
        """Probe each sub-component and return component → healthy mapping."""
        ...

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

`process()` and `process_multimodal()` differ only in the encoding entry-point — both converge at the same embedding vector before entering the SemanticParser.

---

## Implementation — `AsyncCommunicationOrchestrator`

### Construction

```python
class AsyncCommunicationOrchestrator:
    def __init__(
        self,
        encoder: MultiModalEncoder,
        parser: SemanticParser,
        dialogue: DialogueManager,
        generator: ResponseGenerator,
        config: OrchestratorConfig,
    ) -> None:
        self._encoder = encoder
        self._parser = parser
        self._dialogue = dialogue
        self._generator = generator
        self._cfg = config
        self._traces: deque[PipelineTrace] = deque(maxlen=1000)
        self._trace_index: dict[str, PipelineTrace] = {}
        self._running = False
```

All four sub-components are injected — no internal construction, no MRO complexity. This mirrors the proven `AsyncTemporalOrchestrator` (Phase 17.5) composition pattern.

### `process()` — Full Pipeline

```python
async def process(self, text: str, *, session_id: str = "default") -> GeneratedResponse:
    trace_id = uuid4().hex
    input_hash = hashlib.sha256(text.encode()).hexdigest()
    latency: dict[PipelineStage, float] = {}
    ts = time.monotonic_ns()

    try:
        result = await asyncio.wait_for(
            self._run_pipeline(text, session_id, trace_id, latency),
            timeout=self._cfg.max_pipeline_time_s,
        )
        trace = PipelineTrace(
            trace_id=trace_id, stage=PipelineStage.COMPLETE,
            input_hash=input_hash, embedding=result.embedding,
            frame=result.frame, state=result.state, response=result.response,
            error=None, latency_ms=latency, timestamp_ns=ts,
        )
        self._store_trace(trace)
        return result.response
    except (asyncio.TimeoutError, Exception) as exc:
        failed_stage = self._last_stage(latency)
        trace = PipelineTrace(
            trace_id=trace_id, stage=PipelineStage.FAILED,
            input_hash=input_hash, embedding=None, frame=None,
            state=None, response=None, error=str(exc),
            latency_ms=latency, timestamp_ns=ts,
        )
        self._store_trace(trace)
        PIPELINE_FAILURES.labels(stage=failed_stage.value).inc()
        return GeneratedResponse(text=self._cfg.fallback_response)
```

### `_run_pipeline()` — Per-Stage Execution

```python
async def _run_pipeline(self, text, session_id, trace_id, latency):
    # Stage 1: ENCODING
    t0 = time.perf_counter()
    embedding = await self._encoder.encode_text(text)
    latency[PipelineStage.ENCODING] = (time.perf_counter() - t0) * 1000

    # Stage 2: PARSING
    t0 = time.perf_counter()
    frame = await self._parser.parse(embedding)
    latency[PipelineStage.PARSING] = (time.perf_counter() - t0) * 1000

    # Stage 3: DIALOGUE
    t0 = time.perf_counter()
    state = await self._dialogue.add_turn(session_id, frame)
    latency[PipelineStage.DIALOGUE] = (time.perf_counter() - t0) * 1000

    # Stage 4: GENERATING
    t0 = time.perf_counter()
    response = await self._generator.generate(frame, state)
    latency[PipelineStage.GENERATING] = (time.perf_counter() - t0) * 1000

    return _PipelineResult(embedding=embedding, frame=frame, state=state, response=response)
```

### `process_multimodal()`

Identical to `process()` except Stage 1 calls `self._encoder.encode(payload, modality)` instead of `encode_text()`. The rest of the pipeline is unchanged — the embedding vector is modality-agnostic by design (Phase 19.4).

### Trace Store

```python
def _store_trace(self, trace: PipelineTrace) -> None:
    if not self._cfg.trace_enabled:
        return
    self._traces.append(trace)
    self._trace_index[trace.trace_id] = trace
    # Evict from index when deque pops oldest
    if len(self._trace_index) > self._traces.maxlen:
        oldest = next(iter(self._trace_index))
        del self._trace_index[oldest]
    TRACES_STORED.inc()

def get_trace(self, trace_id: str) -> PipelineTrace | None:
    return self._trace_index.get(trace_id)
```

The `deque(maxlen=1000)` acts as a bounded ring buffer. The companion `_trace_index` dict provides O(1) lookup by `trace_id` and is kept in sync by evicting the oldest entry when the deque rotates.

### Health Check

```python
async def health(self) -> dict[str, bool]:
    results: dict[str, bool] = {}
    test_text = "health probe"
    for name, coro in [
        ("encoder", self._encoder.encode_text(test_text)),
        ("parser", self._parser.parse(tuple([0.0] * 64))),
        ("dialogue", self._dialogue.health()),
        ("generator", self._generator.health()),
    ]:
        try:
            await asyncio.wait_for(coro, timeout=2.0)
            results[name] = True
        except Exception:
            results[name] = False
    return results
```

Each sub-component is probed independently with a 2-second timeout. The result is a simple `dict[str, bool]` consumed by `FederationHealthMonitor` (Phase 9.5) and the community dashboard.

### Lifecycle

```python
async def start(self) -> None:
    await self._encoder.start()
    await self._parser.start()
    await self._dialogue.start()
    await self._generator.start()
    self._running = True

async def stop(self) -> None:
    self._running = False
    await self._generator.stop()
    await self._dialogue.stop()
    await self._parser.stop()
    await self._encoder.stop()
```

Start order follows the pipeline direction (encoder first); stop order is reversed for graceful drain.

---

## Implementation — `NullCommunicationOrchestrator`

No-op implementation for testing and dependency injection stubs:

```python
class NullCommunicationOrchestrator:
    async def process(self, text, *, session_id="default"):
        return GeneratedResponse(text="")
    async def process_multimodal(self, payload, modality, *, session_id="default"):
        return GeneratedResponse(text="")
    def get_trace(self, trace_id):
        return None
    async def health(self):
        return {}
    async def start(self): ...
    async def stop(self): ...
```

---

## Factory

```python
def make_communication_orchestrator(
    config: OrchestratorConfig,
) -> CommunicationOrchestrator:
    encoder = make_multimodal_encoder(config.encoder_config)
    parser = make_semantic_parser(config.parser_config)
    dialogue = make_dialogue_manager(config.dialogue_config)
    generator = make_response_generator(config.generator_config)
    return AsyncCommunicationOrchestrator(encoder, parser, dialogue, generator, config)
```

Uses the factory functions from Phases 19.1–19.4 to construct the full pipeline from a single `OrchestratorConfig`.

---

## Full Pipeline Data-Flow

```
Raw Input ──→ MultiModalEncoder ──→ SemanticParser ──→ DialogueManager ──→ ResponseGenerator
   │            (19.4)              (19.1)             (19.2)              (19.3)
   │              ↓                   ↓                  ↓                   ↓
   │         Embedding          SemanticFrame       DialogueState     GeneratedResponse
   │                                                                        ↓
   └──────────────────────── PipelineTrace ←───────────────────────────────┘
```

**Background loop lifecycle** (driven by CognitiveCycle):

```
CognitiveCycle._run_step()
        │
        ▼
  _communication_step()
        │
        ├─→ orchestrator.process(user_input)
        │       │
        │       ├── ENCODING   ──→ embedding vector
        │       ├── PARSING    ──→ SemanticFrame (intent+slots+entities)
        │       ├── DIALOGUE   ──→ DialogueState (context+history)
        │       └── GENERATING ──→ GeneratedResponse (text+metadata)
        │
        ├─→ (COMMAND intent?) ──→ GoalRegistry.create_goal()
        │
        └─→ PipelineTrace stored ──→ deque[1000]
```

---

## Integration Map

| Direction | Component | Phase | Integration Point |
|-----------|-----------|-------|-------------------|
| ← caller | **CognitiveCycle** | core | `_communication_step()` → `process()` / `process_multimodal()` |
| → downstream | **GoalRegistry** | 10.1 | COMMAND intents from SemanticFrame → `create_goal()` |
| → downstream | **CollaborationChannel** | 12.3 | Inter-agent messaging via `process()` for NLU on inbound messages |
| → downstream | **ExplainAPI** | 8.3 | Explanation generation — `ResponseGenerator` can delegate to ExplainAPI |
| ← upstream | **TemporalOrchestrator** | 17.5 | Temporal context injected into DialogueManager for time-aware responses |
| ← upstream | **PerformanceProfiler** | 16.1 | Consumes `latency_ms` from PipelineTrace for bottleneck analysis |
| → downstream | **ReflectionCycle** | 16.5 | Failed traces → self-improvement loop via `WeaknessDetector` |

---

## Phase 19 — Complete Sub-Phase Summary

| Sub-phase | Component | Issue | Wiki | Status |
|-----------|-----------|-------|------|--------|
| 19.1 | SemanticParser | [#466](https://github.com/web3guru888/asi-build/issues/466) | [Wiki](Phase-19-Semantic-Parser) | 🟡 Spec'd |
| 19.2 | DialogueManager | [#467](https://github.com/web3guru888/asi-build/issues/467) | [Wiki](Phase-19-Dialogue-Manager) | 🟡 Spec'd |
| 19.3 | ResponseGenerator | [#468](https://github.com/web3guru888/asi-build/issues/468) | [Wiki](Phase-19-Response-Generator) | 🟡 Spec'd |
| 19.4 | MultiModalEncoder | [#469](https://github.com/web3guru888/asi-build/issues/469) | [Wiki](Phase-19-Multi-Modal-Encoder) | 🟡 Spec'd |
| **19.5** | **CommunicationOrchestrator** | [**#470**](https://github.com/web3guru888/asi-build/issues/470) | **This page** | 🟡 Spec'd |

> 🎉 **Phase 19 COMPLETE** — all 5 NLU sub-components spec'd. The CommunicationOrchestrator composes the full pipeline into a single entry-point for the CognitiveCycle.

---

## Prometheus Metrics

| # | Metric | Type | Labels | Description |
|---|--------|------|--------|-------------|
| 1 | `asi_comm_pipeline_duration_seconds` | Histogram | `session_id` | End-to-end pipeline latency (all stages) |
| 2 | `asi_comm_stage_duration_seconds` | Histogram | `stage` | Per-stage latency (ENCODING, PARSING, DIALOGUE, GENERATING) |
| 3 | `asi_comm_pipeline_failures_total` | Counter | `stage` | Pipeline failures, labelled by the stage that failed |
| 4 | `asi_comm_traces_stored_total` | Counter | — | Total PipelineTrace records stored |
| 5 | `asi_comm_health_status` | Gauge | `component` | Per-component health (1 = healthy, 0 = unhealthy) |

### PromQL Examples

```promql
# P99 end-to-end pipeline latency
histogram_quantile(0.99, rate(asi_comm_pipeline_duration_seconds_bucket[5m]))

# Per-stage latency breakdown
histogram_quantile(0.95, rate(asi_comm_stage_duration_seconds_bucket{stage="parsing"}[5m]))

# Failure rate by stage (last hour)
sum by (stage) (increase(asi_comm_pipeline_failures_total[1h]))

# Trace storage rate
rate(asi_comm_traces_stored_total[5m])

# Unhealthy components
asi_comm_health_status == 0
```

### Grafana Alerts

```yaml
- alert: CommunicationPipelineSlow
  expr: histogram_quantile(0.99, rate(asi_comm_pipeline_duration_seconds_bucket[5m])) > 4.0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "P99 pipeline latency > 4s (approaching 5s timeout)"

- alert: CommunicationStageFailures
  expr: rate(asi_comm_pipeline_failures_total[10m]) > 0.1
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Pipeline failures exceeding 0.1/s — check stage label"

- alert: CommunicationComponentUnhealthy
  expr: asi_comm_health_status == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "NLU sub-component {{ $labels.component }} failing health check"
```

---

## Test Targets (12)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_process_returns_generated_response` | Happy-path text pipeline end-to-end |
| 2 | `test_process_multimodal_routes_through_encoder` | Image/audio payload → same downstream pipeline |
| 3 | `test_pipeline_timeout_returns_fallback` | `asyncio.TimeoutError` → `fallback_response` |
| 4 | `test_encoding_failure_returns_fallback` | Encoder exception → FAILED trace + fallback |
| 5 | `test_parsing_failure_preserves_partial_trace` | Parser exception → latency_ms has ENCODING only |
| 6 | `test_dialogue_failure_preserves_frame_in_trace` | Dialogue exception → trace.frame is not None |
| 7 | `test_trace_stored_on_success` | `get_trace(trace_id)` returns COMPLETE trace |
| 8 | `test_trace_deque_evicts_oldest` | 1001st trace evicts first trace from index |
| 9 | `test_trace_disabled_stores_nothing` | `trace_enabled=False` → empty deque |
| 10 | `test_health_returns_all_components` | Health dict has keys encoder/parser/dialogue/generator |
| 11 | `test_health_partial_failure` | One component raises → `{component: False}` others True |
| 12 | `test_start_stop_lifecycle` | `start()` sets running; `stop()` clears; process after stop raises |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_process_returns_generated_response():
    encoder = MockMultiModalEncoder(embedding=(0.1, 0.2, 0.3))
    parser = MockSemanticParser(frame=SemanticFrame(intent="QUERY", slots={}, entities=[]))
    dialogue = MockDialogueManager()
    generator = MockResponseGenerator(text="Hello there!")
    config = OrchestratorConfig(
        encoder_config=..., parser_config=...,
        dialogue_config=..., generator_config=...,
    )
    orch = AsyncCommunicationOrchestrator(encoder, parser, dialogue, generator, config)
    await orch.start()
    resp = await orch.process("Hi")
    assert resp.text == "Hello there!"
    await orch.stop()


@pytest.mark.asyncio
async def test_trace_deque_evicts_oldest():
    orch = _make_orchestrator(trace_enabled=True)
    await orch.start()
    first_ids = []
    for i in range(1001):
        await orch.process(f"msg-{i}")
    # Oldest trace should be evicted
    assert orch.get_trace(first_ids[0]) is None
    assert len(orch._traces) == 1000
    await orch.stop()
```

---

## `mypy --strict` Compliance

| Pattern | Technique |
|---------|-----------|
| `PipelineTrace` fields nullable | `X \| None` union types |
| `latency_ms` dict | `dict[PipelineStage, float]` — enum keys |
| `_trace_index` pruning | `next(iter(dict))` for oldest key |
| Protocol runtime check | `isinstance(obj, CommunicationOrchestrator)` via `@runtime_checkable` |
| Sub-component types | Each typed as its Protocol, not concrete class |

---

## Implementation Order (14 Steps)

| Step | Task | File |
|------|------|------|
| 1 | `PipelineStage` enum | `asi/nlu/orchestrator.py` |
| 2 | `PipelineTrace` frozen dataclass | `asi/nlu/orchestrator.py` |
| 3 | `OrchestratorConfig` frozen dataclass | `asi/nlu/orchestrator.py` |
| 4 | `CommunicationOrchestrator` Protocol | `asi/nlu/orchestrator.py` |
| 5 | `_PipelineResult` internal NamedTuple | `asi/nlu/orchestrator.py` |
| 6 | `AsyncCommunicationOrchestrator.__init__` | `asi/nlu/orchestrator.py` |
| 7 | `_run_pipeline()` per-stage execution | `asi/nlu/orchestrator.py` |
| 8 | `process()` with timeout + fallback | `asi/nlu/orchestrator.py` |
| 9 | `process_multimodal()` variant | `asi/nlu/orchestrator.py` |
| 10 | `_store_trace()` + `get_trace()` | `asi/nlu/orchestrator.py` |
| 11 | `health()` per-component probe | `asi/nlu/orchestrator.py` |
| 12 | `start()` / `stop()` lifecycle | `asi/nlu/orchestrator.py` |
| 13 | `NullCommunicationOrchestrator` | `asi/nlu/orchestrator.py` |
| 14 | `make_communication_orchestrator()` factory | `asi/nlu/orchestrator.py` |

---

## See Also

- [Phase 19 Semantic Parser](Phase-19-Semantic-Parser) — intent + slot extraction (19.1)
- [Phase 19 Dialogue Manager](Phase-19-Dialogue-Manager) — session state management (19.2)
- [Phase 19 Response Generator](Phase-19-Response-Generator) — text generation (19.3)
- [Phase 19 Multi-Modal Encoder](Phase-19-Multi-Modal-Encoder) — multi-modal embedding (19.4)
- [Phase 17.5 Temporal Orchestrator](Phase-17-Temporal-Orchestrator) — composition pattern reference
- [Phase 10.1 Goal Registry](Phase-10-Goal-Registry) — COMMAND intent downstream
- [Phase 16.1 Performance Profiler](Phase-16-Performance-Profiler) — latency analysis consumer
