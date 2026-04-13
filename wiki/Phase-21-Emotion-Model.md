# Phase 21.1 — EmotionModel

> PAD dimensional affective state · Plutchik discrete taxonomy · temporal decay · emotional memory traces

| Field | Value |
|-------|-------|
| **Issue** | [#500](https://github.com/web3guru888/asi-build/issues/500) |
| **Show & Tell** | [#503](https://github.com/web3guru888/asi-build/discussions/503) |
| **Q&A** | [#506](https://github.com/web3guru888/asi-build/discussions/506) |
| **Phase** | 21 — Emotional Intelligence & Affective Computing |
| **Depends on** | Phase 19.5 CommunicationOrchestrator (#470), Phase 17.1 TemporalGraph (#434) |
| **Status** | 🟡 spec'd |

---

## Overview

The **EmotionModel** provides the foundational affective state representation for ASI-Build's emotional intelligence layer. It implements a dual representation:

- **Continuous**: PAD (Pleasure–Arousal–Dominance) 3-dimensional space for nuanced, graded affect
- **Discrete**: Plutchik's 8 primary emotion taxonomy for interpretable categorical labels

Temporal exponential decay drives emotional state toward a configurable baseline, while a bounded history deque maintains emotional memory traces for downstream components (MoodRegulator 21.2, EmpathyEngine 21.3, AffectiveMemory 21.4).

---

## Public Surface

### EmotionCategory Enum

```python
class EmotionCategory(str, Enum):
    """Plutchik's 8 primary emotions."""
    JOY          = "joy"
    SADNESS      = "sadness"
    ANGER        = "anger"
    FEAR         = "fear"
    SURPRISE     = "surprise"
    DISGUST      = "disgust"
    TRUST        = "trust"
    ANTICIPATION = "anticipation"
```

**Bipolar pairs** (Plutchik's wheel):

| Pair | Positive | Negative |
|------|----------|----------|
| 1 | JOY | SADNESS |
| 2 | TRUST | DISGUST |
| 3 | ANTICIPATION | SURPRISE |
| 4 | ANGER | FEAR |

### PADState Frozen Dataclass

```python
@dataclass(frozen=True, slots=True)
class PADState:
    """Pleasure-Arousal-Dominance affective coordinates."""
    pleasure:  float  # -1.0 .. +1.0
    arousal:   float  # -1.0 .. +1.0
    dominance: float  # -1.0 .. +1.0

    def clamp(self) -> "PADState":
        """Return new PADState with each axis clamped to [-1, 1]."""
        ...

    def distance(self, other: "PADState") -> float:
        """Euclidean distance in PAD space."""
        ...

    def lerp(self, other: "PADState", t: float) -> "PADState":
        """Linear interpolation: self*(1-t) + other*t."""
        ...
```

### EmotionConfig Frozen Dataclass

```python
@dataclass(frozen=True, slots=True)
class EmotionConfig:
    decay_rate:        float    = 0.05
    baseline_pad:      PADState = PADState(0.1, 0.0, 0.2)
    min_intensity:     float    = 0.01
    max_history:       int      = 1000
    update_interval_s: float    = 1.0
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `decay_rate` | 0.05 | λ in exponential decay (half-life ≈ 13.9s) |
| `baseline_pad` | (0.1, 0.0, 0.2) | Slightly positive/dominant resting state |
| `min_intensity` | 0.01 | Below this → zero out discrete intensity |
| `max_history` | 1000 | Bounded deque size |
| `update_interval_s` | 1.0 | Minimum seconds between decay steps |

### EmotionalState Frozen Dataclass

```python
@dataclass(frozen=True, slots=True)
class EmotionalState:
    pad:       PADState
    discrete:  dict[EmotionCategory, float]
    timestamp: float
    source:    str
```

### EmotionModel Protocol

```python
@runtime_checkable
class EmotionModel(Protocol):
    async def current_state(self) -> EmotionalState: ...
    async def update(self, stimulus_pad: PADState, source: str) -> EmotionalState: ...
    async def decay_step(self) -> EmotionalState: ...
    async def get_history(self, n: int = 10) -> list[EmotionalState]: ...
    async def get_dominant_emotion(self) -> tuple[EmotionCategory, float]: ...
    async def reset(self) -> None: ...
```

---

## PADEmotionModel — Reference Implementation

```python
class PADEmotionModel:
    def __init__(self, config: EmotionConfig | None = None) -> None:
        self._config = config or EmotionConfig()
        self._lock = asyncio.Lock()
        self._state: PADState = self._config.baseline_pad
        self._history: deque[EmotionalState] = deque(maxlen=self._config.max_history)
        self._last_decay: float = time.monotonic()
        self._update_count: int = 0
```

### PAD → Discrete Emotion Mapping

Nearest-neighbor lookup against Plutchik prototype coordinates:

```
Emotion         Pleasure  Arousal  Dominance
─────────────── ──────── ──────── ─────────
JOY              +0.80    +0.50    +0.50
SADNESS          −0.80    −0.30    −0.50
ANGER            −0.60    +0.70    +0.60
FEAR             −0.70    +0.70    −0.60
SURPRISE         +0.20    +0.80    −0.20
DISGUST          −0.60    +0.20    +0.30
TRUST            +0.60    −0.20    +0.40
ANTICIPATION     +0.40    +0.60    +0.30
```

**Intensity formula**:
```
intensity(e) = max(0, 1 − distance(current_pad, prototype_e) / √12)
```

`√12 ≈ 3.464` = diagonal of the `[-1,1]³` cube. Multiple emotions can be active simultaneously.

### Temporal Decay

Exponential convergence toward baseline:

```
pad_axis(t) = baseline_axis + (pad_axis(t₀) − baseline_axis) × e^(−λ × Δt)
```

Each axis decays independently. Decay is skipped if `Δt < update_interval_s`.

```
PAD Value
  1.0 ┤ ×
      │  ╲
  0.8 ┤   ╲  ← stimulus impact
      │    ╲
  0.6 ┤     ╲
      │      ╲
  0.4 ┤       ╲────
      │             ────────
  0.2 ┤                     ──────── baseline
      │
  0.0 ┤
      └──┬──┬──┬──┬──┬──┬──┬──┬──
         0  5  10 15 20 25 30 35  time (s)
```

| λ value | Half-life | 90% decay | Use case |
|---------|-----------|-----------|----------|
| 0.01 | ~69s | ~230s | Long-lasting moods |
| 0.05 | ~14s | ~46s | Standard reactions (default) |
| 0.10 | ~7s | ~23s | Quick-fading responses |
| 0.50 | ~1.4s | ~4.6s | Near-instant decay |

### Update Flow

```
stimulus_pad arrives
  → async with self._lock:
      → blend: self._state = self._state.lerp(stimulus_pad, 0.5)
      → clamp to [-1, 1]
      → map PAD → discrete (nearest-neighbor)
      → push EmotionalState to history deque
      → update Prometheus metrics
      → return new EmotionalState
```

### History & Dominant

- `get_history(n)` — newest first via `list(islice(reversed(self._history), n))`
- `get_dominant_emotion()` — `max(discrete.items(), key=lambda x: x[1])`, ties broken by enum order

---

## NullEmotionModel

```python
class NullEmotionModel:
    """No-op for testing / emotion-disabled configurations."""
    async def current_state(self) -> EmotionalState:
        return EmotionalState(PADState(0, 0, 0), {}, 0.0, "null")
    async def update(self, stimulus_pad: PADState, source: str) -> EmotionalState:
        return await self.current_state()
    async def decay_step(self) -> EmotionalState:
        return await self.current_state()
    async def get_history(self, n: int = 10) -> list[EmotionalState]:
        return []
    async def get_dominant_emotion(self) -> tuple[EmotionCategory, float]:
        return (EmotionCategory.JOY, 0.0)
    async def reset(self) -> None:
        pass
```

---

## Factory

```python
def make_emotion_model(*, config: EmotionConfig | None = None, null: bool = False) -> EmotionModel:
    if null:
        return NullEmotionModel()
    return PADEmotionModel(config=config)
```

---

## Integration

### CognitiveCycle

```python
async def _affective_step(self) -> None:
    stimulus = self._perception_to_pad(self._blackboard.latest_percepts)
    state = await self._emotion_model.update(stimulus, source="perception")
    await self._emotion_model.decay_step()
    self._blackboard.post("affective_state", state)
```

### TemporalGraph (17.1) — Emotional Memory Traces

```python
await temporal_graph.add_edge(
    source_id=f"emotion:{state.timestamp}",
    target_id=f"stimulus:{stimulus_id}",
    edge_type="emotional_response",
    metadata={"pad": asdict(state.pad), "dominant": dominant[0].value},
)
```

### Cross-Phase Integration Map

```
Phase 17.1 TemporalGraph ──────────────┐ emotional trace storage
Phase 19.1 SemanticParser ─────────────┤ stimulus extraction
Phase 19.5 CommunicationOrchestrator ──┤ response style selection
                                        ▼
                              ┌─────────────────┐
                              │  EmotionModel    │ ← Phase 21.1
                              │  (21.1)          │
                              └────────┬────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
    ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
    │ MoodRegulator│        │ EmpathyEngine│        │ AffectiveMemory│
    │ (21.2)       │        │ (21.3)       │        │ (21.4)        │
    └──────────────┘        └──────────────┘        └───────────────┘
              └────────────────────────┼────────────────────────┘
                                       ▼
                              ┌──────────────────────┐
                              │ EmotionalOrchestrator │
                              │ (21.5)                │
                              └──────────────────────┘
```

---

## Prometheus Metrics

| # | Metric | Type | Description |
|---|--------|------|-------------|
| 1 | `emotion_updates_total` | Counter | Total emotion update events |
| 2 | `emotion_current_pleasure` | Gauge | Current pleasure axis value |
| 3 | `emotion_current_arousal` | Gauge | Current arousal axis value |
| 4 | `emotion_current_dominance` | Gauge | Current dominance axis value |
| 5 | `emotion_dominant_info` | Info | Current dominant emotion category + intensity |

### PromQL Examples

```promql
# Update rate
rate(emotion_updates_total[5m])

# PAD distance from baseline
sqrt(
  (emotion_current_pleasure - 0.1)^2 +
  (emotion_current_arousal - 0.0)^2 +
  (emotion_current_dominance - 0.2)^2
)

# Dominant emotion over time
emotion_dominant_info
```

### Grafana Alerts

```yaml
- alert: SustainedNegativeAffect
  expr: avg_over_time(emotion_current_pleasure[5m]) < -0.5
  for: 5m
  annotations:
    summary: "Pleasure below -0.5 for 5 min"

- alert: HighArousalSustained
  expr: avg_over_time(emotion_current_arousal[5m]) > 0.8
  for: 3m
  annotations:
    summary: "Arousal above 0.8 for 3 min — check stimulus sources"

- alert: EmotionUpdateStalled
  expr: rate(emotion_updates_total[5m]) == 0
  for: 2m
  annotations:
    summary: "No emotion updates for 2 min"
```

---

## mypy Narrowing Table

| Pattern | Narrowing |
|---------|-----------|
| `isinstance(model, EmotionModel)` | Protocol structural check |
| `EmotionCategory(s)` | `str → EmotionCategory` |
| `PADState.clamp()` | returns `PADState` (frozen) |
| `dict[EmotionCategory, float]` | explicit key type |
| `model := make_emotion_model()` | `EmotionModel` |

---

## Test Targets (12)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_pad_state_clamp` | Axes clamped to [-1, 1] |
| 2 | `test_pad_state_distance` | Euclidean distance calculation |
| 3 | `test_pad_state_lerp` | Linear interpolation at t=0, 0.5, 1 |
| 4 | `test_emotion_config_defaults` | Default config values |
| 5 | `test_pad_to_discrete_mapping` | JOY prototype maps to JOY dominant |
| 6 | `test_update_blends_stimulus` | PAD moves toward stimulus |
| 7 | `test_decay_toward_baseline` | Exponential decay reduces distance to baseline |
| 8 | `test_decay_skipped_within_interval` | No decay if Δt < update_interval_s |
| 9 | `test_history_bounded` | Deque respects max_history |
| 10 | `test_dominant_emotion_highest` | get_dominant returns max intensity |
| 11 | `test_reset_clears_state` | Reset restores baseline + empty history |
| 12 | `test_null_model_noop` | NullEmotionModel returns zeros |

---

## Implementation Order (14 steps)

1. `PADState` dataclass with `clamp()`, `distance()`, `lerp()`
2. `EmotionCategory` enum
3. `EmotionConfig` dataclass
4. `EmotionalState` dataclass
5. `EmotionModel` Protocol
6. Plutchik PAD prototype lookup table (`dict[EmotionCategory, PADState]`)
7. `PADEmotionModel.__init__()` — lock, deque, metrics
8. `PADEmotionModel._map_discrete()` — nearest-neighbor PAD → discrete
9. `PADEmotionModel.update()` — blend + clamp + map + history push
10. `PADEmotionModel.decay_step()` — exponential decay per axis
11. `PADEmotionModel.current_state()` / `get_history()` / `get_dominant_emotion()`
12. `PADEmotionModel.reset()`
13. `NullEmotionModel`
14. `make_emotion_model()` factory

---

## Phase 21 Sub-Phase Tracker

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 21.1 | EmotionModel | [#500](https://github.com/web3guru888/asi-build/issues/500) | 🟡 spec'd |
| 21.2 | MoodRegulator | TBD | ⚪ planned |
| 21.3 | EmpathyEngine | TBD | ⚪ planned |
| 21.4 | AffectiveMemory | TBD | ⚪ planned |
| 21.5 | EmotionalOrchestrator | TBD | ⚪ planned |
