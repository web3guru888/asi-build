# Phase 21.5 — AffectiveOrchestrator

> **Emotion-modulated cognition, affective memory & unified emotional pipeline**
> _Capstone component composing all Phase 21 sub-systems into a single affective processing pipeline_

| Field | Value |
|-------|-------|
| **Sub-phase** | 21.5 (capstone) |
| **Issue** | [#502](https://github.com/web3guru888/asi-build/issues/502) |
| **Show & Tell** | [#509](https://github.com/web3guru888/asi-build/discussions/509) |
| **Q&A** | [#512](https://github.com/web3guru888/asi-build/discussions/512) |
| **Planning** | [#497](https://github.com/web3guru888/asi-build/discussions/497) |
| **Status** | 🟡 Spec |
| **Depends on** | EmotionModel (21.1), AffectDetector (21.2), EmpathyEngine (21.3), MoodRegulator (21.4) |

---

## 🎉 PHASE 21 COMPLETE — Emotional Intelligence & Affective Computing

| # | Component | Status | Key Capability |
|---|-----------|--------|----------------|
| 21.1 | EmotionModel | 🟡 Spec | PAD emotional state transitions |
| 21.2 | AffectDetector | 🟡 Spec | Multi-modal affect signal detection |
| 21.3 | EmpathyEngine | 🟡 Spec | Theory-of-mind empathic inference |
| 21.4 | MoodRegulator | 🟡 Spec | Long-term mood homeostasis |
| **21.5** | **AffectiveOrchestrator** | **🟡 Spec** | **Unified pipeline + cognitive modulation** |

---

## Motivation

Emotions are not noise — they are **information-carrying signals** that modulate attention, memory encoding, and decision-making. The AffectiveOrchestrator unifies all Phase 21 components into a coherent pipeline that:

1. **Detects** affect signals from input (text, context, physiological proxies)
2. **Models** the resulting emotional state transition
3. **Empathizes** with interlocutors (theory of mind)
4. **Regulates** mood homeostasis
5. **Integrates** emotional context into cognitive modulation

---

## Public API

### `AffectivePhase` enum (6 states)

```python
class AffectivePhase(str, Enum):
    IDLE        = "idle"         # no active processing
    DETECTING   = "detecting"    # AffectDetector scanning input
    MODELING    = "modeling"     # EmotionModel computing state transition
    EMPATHIZING = "empathizing"  # EmpathyEngine running ToM inference
    REGULATING  = "regulating"   # MoodRegulator applying homeostatic correction
    INTEGRATING = "integrating"  # computing modulation weights & final context
```

**State machine transitions:**

```
IDLE → DETECTING → MODELING → EMPATHIZING → REGULATING → INTEGRATING → IDLE
         ↓ (fail)     ↓ (fail)     ↓ (skip)      ↓ (skip)
       IDLE (degrade)  IDLE        REGULATING    INTEGRATING
```

---

### `AffectiveContext` frozen dataclass

```python
@dataclass(frozen=True)
class AffectiveContext:
    """Complete emotional context produced by one pipeline cycle."""
    emotional_state: EmotionalState          # from EmotionModel (21.1)
    mood: MoodState                          # from MoodRegulator (21.4)
    empathy_results: list[EmpathyResult]     # from EmpathyEngine (21.3)
    affect_signals: list[AffectSignal]       # from AffectDetector (21.2)
    modulation_weights: dict[str, float]     # attention/memory/decision weights
    phase_timings: dict[str, float]          # per-phase latency in seconds
    degraded_phases: frozenset[str]          # phases that failed gracefully
    timestamp: float                         # time.monotonic() of completion
```

---

### `AffectiveConfig` frozen dataclass

```python
@dataclass(frozen=True)
class AffectiveConfig:
    """Tuning knobs for the affective pipeline."""
    enable_empathy: bool = True              # skip EmpathyEngine if False
    enable_regulation: bool = True           # skip MoodRegulator if False
    attention_modulation: float = 0.3        # how much emotions influence attention [0,1]
    memory_encoding_boost: float = 0.5       # emotional salience boost for memory [0,1]
    decision_temperature: float = 0.2        # emotion influence on reasoning confidence [0,1]
    pipeline_timeout_s: float = 2.0          # max wall-clock per cycle
    snapshot_history: int = 100              # ring buffer of recent AffectiveContexts
```

---

### `AffectiveOrchestrator` Protocol

```python
@runtime_checkable
class AffectiveOrchestrator(Protocol):
    """Unified emotional processing pipeline."""

    async def process(
        self,
        input_text: str,
        context: dict[str, Any] | None = None,
    ) -> AffectiveContext: ...

    def get_modulation_weights(self) -> dict[str, float]: ...

    def get_phase(self) -> AffectivePhase: ...

    async def modulate_attention(
        self,
        attention_map: dict[str, float],
        emotional_state: EmotionalState,
    ) -> dict[str, float]: ...

    async def modulate_memory_encoding(
        self,
        trace: Any,
        emotional_state: EmotionalState,
    ) -> Any: ...

    def get_communication_tone(self) -> str: ...
```

---

### `AsyncAffectiveOrchestrator` implementation

```python
class AsyncAffectiveOrchestrator:
    """Composes Phase 21 sub-components into a unified affective pipeline."""

    def __init__(
        self,
        emotion_model: EmotionModel,         # 21.1
        affect_detector: AffectDetector,      # 21.2
        empathy_engine: EmpathyEngine,        # 21.3
        mood_regulator: MoodRegulator,        # 21.4
        config: AffectiveConfig = AffectiveConfig(),
    ) -> None:
        self._emotion_model = emotion_model
        self._affect_detector = affect_detector
        self._empathy_engine = empathy_engine
        self._mood_regulator = mood_regulator
        self._config = config
        self._phase = AffectivePhase.IDLE
        self._lock = asyncio.Lock()
        self._history: deque[AffectiveContext] = deque(maxlen=config.snapshot_history)
        self._current_weights: dict[str, float] = {
            "attention": 0.0, "memory": 0.0, "decision": 0.0,
        }
```

#### 6-phase `process()` pipeline

```python
async def process(self, input_text: str, context: dict[str, Any] | None = None) -> AffectiveContext:
    async with self._lock:
        timings: dict[str, float] = {}
        degraded: set[str] = set()

        # Phase 1: DETECTING
        self._phase = AffectivePhase.DETECTING
        t0 = time.monotonic()
        try:
            signals = await self._affect_detector.detect(input_text, context)
        except Exception:
            signals, degraded = [], degraded | {"detecting"}
        timings["detecting"] = time.monotonic() - t0

        # Phase 2: MODELING
        self._phase = AffectivePhase.MODELING
        t0 = time.monotonic()
        try:
            emotional_state = await self._emotion_model.transition(signals)
        except Exception:
            emotional_state = self._emotion_model.get_neutral()
            degraded.add("modeling")
        timings["modeling"] = time.monotonic() - t0

        # Phase 3: EMPATHIZING
        self._phase = AffectivePhase.EMPATHIZING
        t0 = time.monotonic()
        empathy_results: list[EmpathyResult] = []
        if self._config.enable_empathy:
            try:
                empathy_results = await self._empathy_engine.infer(input_text, emotional_state)
            except Exception:
                degraded.add("empathizing")
        else:
            degraded.add("empathizing")
        timings["empathizing"] = time.monotonic() - t0

        # Phase 4: REGULATING
        self._phase = AffectivePhase.REGULATING
        t0 = time.monotonic()
        if self._config.enable_regulation:
            try:
                mood = await self._mood_regulator.regulate(emotional_state)
            except Exception:
                mood = self._mood_regulator.get_baseline()
                degraded.add("regulating")
        else:
            mood = self._mood_regulator.get_baseline()
            degraded.add("regulating")
        timings["regulating"] = time.monotonic() - t0

        # Phase 5: INTEGRATING
        self._phase = AffectivePhase.INTEGRATING
        t0 = time.monotonic()
        weights = self._compute_modulation_weights(emotional_state, mood)
        self._current_weights = weights
        timings["integrating"] = time.monotonic() - t0

        ctx = AffectiveContext(
            emotional_state=emotional_state,
            mood=mood,
            empathy_results=empathy_results,
            affect_signals=signals,
            modulation_weights=weights,
            phase_timings=timings,
            degraded_phases=frozenset(degraded),
            timestamp=time.monotonic(),
        )
        self._history.append(ctx)
        self._phase = AffectivePhase.IDLE
        return ctx
```

---

### Cognitive Modulation Formulas

#### Modulation weight computation

```python
def _compute_modulation_weights(self, state: EmotionalState, mood: MoodState) -> dict[str, float]:
    arousal = state.arousal          # [0, 1]
    valence = state.valence          # [-1, 1]
    mood_stability = mood.stability  # [0, 1]
    return {
        "attention": arousal * self._config.attention_modulation,
        "memory": abs(valence) * self._config.memory_encoding_boost,
        "decision": (1.0 - mood_stability) * self._config.decision_temperature,
    }
```

#### Attention modulation

```python
async def modulate_attention(self, attention_map: dict[str, float], emotional_state: EmotionalState) -> dict[str, float]:
    factor = self._config.attention_modulation
    arousal = emotional_state.arousal
    return {k: v * (1.0 + arousal * factor) for k, v in attention_map.items()}
```

| Arousal | Factor=0.3 | Multiplier |
|---------|-----------|------------|
| 0.0 | × 0.0 | 1.00 |
| 0.5 | × 0.15 | 1.15 |
| 0.8 | × 0.24 | 1.24 |
| 1.0 | × 0.30 | 1.30 |

#### Memory encoding boost

```python
async def modulate_memory_encoding(self, trace: Any, emotional_state: EmotionalState) -> Any:
    boost = self._config.memory_encoding_boost
    salience_multiplier = 1.0 + abs(emotional_state.valence) * boost
    return trace._replace(salience=trace.salience * salience_multiplier)
```

| Valence | Boost=0.5 | Salience Multiplier |
|---------|-----------|-------------------|
| 0.0 | × 0.0 | 1.00 |
| ±0.5 | × 0.25 | 1.25 |
| ±0.9 | × 0.45 | 1.45 |
| ±1.0 | × 0.50 | 1.50 |

#### Communication tone selection

```python
_TONE_MAP = {
    (True, True):   "enthusiastic",   # high arousal, positive valence
    (True, False):  "urgent",         # high arousal, negative valence
    (False, True):  "warm",           # low arousal, positive valence
    (False, False): "calm",           # low arousal, negative valence
}

def get_communication_tone(self) -> str:
    if not self._history:
        return "neutral"
    last = self._history[-1]
    high_arousal = last.emotional_state.arousal > 0.5
    positive = last.emotional_state.valence > 0.0
    return self._TONE_MAP[(high_arousal, positive)]
```

---

### `NullAffectiveOrchestrator`

```python
class NullAffectiveOrchestrator:
    """No-op implementation for DI / testing."""
    async def process(self, input_text, context=None) -> AffectiveContext:
        return AffectiveContext(
            emotional_state=NEUTRAL_STATE, mood=BASELINE_MOOD,
            empathy_results=[], affect_signals=[],
            modulation_weights={"attention": 0, "memory": 0, "decision": 0},
            phase_timings={}, degraded_phases=frozenset(), timestamp=time.monotonic(),
        )
    def get_modulation_weights(self): return {"attention": 0.0, "memory": 0.0, "decision": 0.0}
    def get_phase(self): return AffectivePhase.IDLE
    async def modulate_attention(self, m, s): return m
    async def modulate_memory_encoding(self, t, s): return t
    def get_communication_tone(self): return "neutral"
```

---

### `make_affective_orchestrator()` factory

```python
def make_affective_orchestrator(
    emotion_model: EmotionModel | None = None,
    affect_detector: AffectDetector | None = None,
    empathy_engine: EmpathyEngine | None = None,
    mood_regulator: MoodRegulator | None = None,
    *, config: AffectiveConfig = AffectiveConfig(),
) -> AffectiveOrchestrator:
    if all(c is not None for c in [emotion_model, affect_detector, empathy_engine, mood_regulator]):
        return AsyncAffectiveOrchestrator(
            emotion_model=emotion_model, affect_detector=affect_detector,
            empathy_engine=empathy_engine, mood_regulator=mood_regulator,
            config=config,
        )
    return NullAffectiveOrchestrator()
```

---

## Full Phase 21 Pipeline

```
  Input Text + Context
         │
         ▼
  ┌─────────────────┐
  │ 1. DETECTING     │  AffectDetector.detect(text, ctx)
  │    signals[]     │  → list[AffectSignal]
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ 2. MODELING      │  EmotionModel.transition(signals)
  │    emotion state │  → EmotionalState(arousal, valence, dominance)
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ 3. EMPATHIZING   │  EmpathyEngine.infer(text, state)
  │    ToM results   │  → list[EmpathyResult]
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ 4. REGULATING    │  MoodRegulator.regulate(state)
  │    mood state    │  → MoodState(stability, baseline_valence)
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ 5. INTEGRATING   │  _compute_modulation_weights()
  │    weights{}     │  → {attention, memory, decision}
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ 6. → IDLE        │  Return AffectiveContext
  │    history ring  │  → deque[100]
  └─────────────────┘
```

---

## CognitiveCycle Integration

```python
async def _affective_step(self, input_text: str) -> AffectiveContext:
    ctx = await self._affective_orchestrator.process(input_text, self._context)

    # Modulate attention (Phase 10 GoalDecomposer)
    self._attention_map = await self._affective_orchestrator.modulate_attention(
        self._attention_map, ctx.emotional_state)

    # Boost memory encoding (Phase 18.2 MemoryConsolidator)
    if self._current_trace:
        self._current_trace = await self._affective_orchestrator.modulate_memory_encoding(
            self._current_trace, ctx.emotional_state)

    # Set communication tone (Phase 19 CommunicationOrchestrator)
    tone = self._affective_orchestrator.get_communication_tone()
    self._communication_orchestrator.set_tone(tone)
    return ctx
```

---

## Cross-Phase Integration Map

| Phase | Component | Integration with AffectiveOrchestrator |
|-------|-----------|--------------------------------------|
| **10** | GoalDecomposer | Attention map modulated by arousal |
| **13.4** | SurpriseDetector | Surprise signals feed AffectDetector |
| **17.1** | TemporalGraph | Emotional events stored with temporal relations |
| **18.2** | MemoryConsolidator | Emotional salience boosts encoding strength |
| **19** | CommunicationOrchestrator | Tone selection from affective state |
| **20** | ReasoningOrchestrator | Decision temperature modulates confidence |

---

## Prometheus Metrics (5)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_affective_cycles_total` | Counter | `status` | Pipeline completions (ok/degraded/error) |
| `asi_affective_pipeline_latency_seconds` | Histogram | `phase` | Per-phase + total pipeline latency |
| `asi_affective_attention_modulation_gauge` | Gauge | — | Current attention modulation weight |
| `asi_affective_memory_boost_gauge` | Gauge | — | Current memory encoding boost weight |
| `asi_affective_communication_tone_info` | Info | `tone` | Current communication tone |

**PromQL examples:**

```promql
histogram_quantile(0.95, rate(asi_affective_pipeline_latency_seconds_bucket{phase="total"}[5m]))
rate(asi_affective_cycles_total{status="degraded"}[5m]) / rate(asi_affective_cycles_total[5m])
asi_affective_attention_modulation_gauge
```

**Grafana alerts:**

```yaml
alerts:
  - name: HighDegradedCycleRate
    condition: rate(asi_affective_cycles_total{status="degraded"}[5m]) / rate(asi_affective_cycles_total[5m]) > 0.1
    for: 5m
    severity: warning
  - name: HighPipelineLatency
    condition: histogram_quantile(0.95, rate(asi_affective_pipeline_latency_seconds_bucket{phase="total"}[5m])) > 2
    for: 5m
    severity: critical
  - name: LowMoodStability
    condition: asi_mood_stability_gauge < 0.3
    for: 10m
    severity: warning
```

---

## mypy Strict Compliance

| Pattern | Narrowing |
|---------|-----------|
| `AffectivePhase` | `Enum` — exhaustive `match/case` with `assert_never` |
| `AffectiveContext` | `frozen=True` — immutable, no `setattr` |
| `modulation_weights` | `dict[str, float]` — explicit key typing |
| `degraded_phases` | `frozenset[str]` — immutable set |
| `_history` | `deque[AffectiveContext]` — typed ring buffer |
| Optional empathy/regulation | `if self._config.enable_*` guard |

---

## Test Targets (12)

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_process_full_pipeline_returns_affective_context` | All 6 phases execute, valid AffectiveContext |
| 2 | `test_process_degraded_detecting_returns_empty_signals` | AffectDetector raises → signals=[], "detecting" in degraded |
| 3 | `test_process_degraded_modeling_returns_neutral` | EmotionModel raises → neutral state |
| 4 | `test_empathy_skipped_when_disabled` | enable_empathy=False → "empathizing" in degraded |
| 5 | `test_regulation_skipped_when_disabled` | enable_regulation=False → baseline mood |
| 6 | `test_modulate_attention_increases_weights` | arousal=0.8, factor=0.3 → each weight *= 1.24 |
| 7 | `test_modulate_memory_encoding_boost` | valence=-0.9, boost=0.5 → salience *= 1.45 |
| 8 | `test_communication_tone_enthusiastic` | high arousal + positive → "enthusiastic" |
| 9 | `test_communication_tone_calm` | low arousal + negative → "calm" |
| 10 | `test_null_orchestrator_returns_neutral` | all zero weights, "neutral" tone |
| 11 | `test_factory_returns_async_when_all_provided` | 4 deps → AsyncAffectiveOrchestrator |
| 12 | `test_factory_returns_null_when_missing_dep` | None dep → NullAffectiveOrchestrator |

---

## Implementation Order (14 steps)

1. `AffectivePhase` enum (6 states)
2. `AffectiveContext` frozen dataclass
3. `AffectiveConfig` frozen dataclass
4. `AffectiveOrchestrator` Protocol
5. `_compute_modulation_weights()` static logic
6. `_TONE_MAP` and `get_communication_tone()`
7. `modulate_attention()` implementation
8. `modulate_memory_encoding()` implementation
9. `process()` Phase 1–2 (DETECTING + MODELING)
10. `process()` Phase 3–4 (EMPATHIZING + REGULATING)
11. `process()` Phase 5 (INTEGRATING) + history ring buffer
12. `NullAffectiveOrchestrator`
13. `make_affective_orchestrator()` factory
14. Prometheus metrics + Grafana dashboard

---

## Phase 21 — COMPLETE ✅

| Sub-phase | Component | Status |
|-----------|-----------|--------|
| 21.1 | EmotionModel | 🟡 Spec |
| 21.2 | AffectDetector | 🟡 Spec |
| 21.3 | EmpathyEngine | 🟡 Spec |
| 21.4 | MoodRegulator | 🟡 Spec |
| **21.5** | **AffectiveOrchestrator** | **🟡 Spec** |

**Phase 21 delivers**: Emotional state modeling → multi-modal affect detection → empathic reasoning → mood homeostasis → unified cognitive modulation pipeline.

---

_See also: [Phase 21 Planning (#497)](https://github.com/web3guru888/asi-build/discussions/497) · [Master Tracker (#109)](https://github.com/web3guru888/asi-build/issues/109)_
