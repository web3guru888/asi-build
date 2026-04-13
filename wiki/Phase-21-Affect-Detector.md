# Phase 21.2 — AffectDetector

> **Text sentiment analysis, multimodal emotion detection & valence-arousal extraction.**

| Field | Value |
|-------|-------|
| **Issue** | [#499](https://github.com/web3guru888/asi-build/issues/499) |
| **Phase** | 21 — Emotion & Affect |
| **Sub-phase** | 21.2 |
| **Depends on** | [EmotionModel 21.1](Phase-21-Emotion-Model) |
| **Feeds into** | MoodRegulator 21.3 · EmotionOrchestrator 21.5 |
| **Discussions** | [Show & Tell #507](https://github.com/web3guru888/asi-build/discussions/507) · [Q&A #510](https://github.com/web3guru888/asi-build/discussions/510) |
| **Status** | 🟡 Spec'd |

---

## Table of Contents

- [Overview](#overview)
- [Enums](#enums)
- [Data Classes](#data-classes)
- [Protocol](#protocol)
- [Implementations](#implementations)
- [Multimodal Fusion](#multimodal-fusion)
- [Detection Pipeline](#detection-pipeline)
- [EmotionModel Integration](#emotionmodel-integration)
- [Prometheus Metrics](#prometheus-metrics)
- [Test Targets](#test-targets)
- [Implementation Order](#implementation-order)
- [Phase 21 Tracker](#phase-21-sub-phase-tracker)

---

## Overview

**AffectDetector** extracts structured affect signals from text and multimodal inputs. Each signal carries valence (pleasure–displeasure), arousal (activation–deactivation), polarity, confidence, and source span information.

The first implementation uses a **rule-based lexicon approach** (AFINN-style) with negation handling and intensifier detection. The `AffectDetector` Protocol boundary enables future ML backends (BERT, RoBERTa) as drop-in replacements.

### Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              AffectDetector                  │
                    │         (LexiconAffectDetector impl)        │
                    │                                             │
  user_input ──────►│  ┌───────────┐   ┌───────────┐             │
                    │  │  sentence  │   │  lexicon  │             │
                    │  │  splitter  │──►│  lookup   │             │
                    │  └───────────┘   └─────┬─────┘             │
                    │                        │                    │
                    │              ┌─────────▼──────────┐        │
                    │              │  negation handler   │        │
                    │              │  (3-token window)   │        │
                    │              └─────────┬──────────┘        │
                    │                        │                    │
                    │              ┌─────────▼──────────┐        │
                    │              │ intensifier handler │        │
                    │              │ (multiplier table)  │        │
                    │              └─────────┬──────────┘        │
                    │                        │                    │
                    │              ┌─────────▼──────────┐        │
                    │              │   score aggregator  │        │
                    │              │ valence + arousal   │        │
                    │              └─────────┬──────────┘        │
                    │                        │                    │
                    │              ┌─────────▼──────────┐        │
                    │              │ polarity classifier │        │
                    │              │ POS/NEG/NEU/MIXED   │        │
                    │              └─────────┬──────────┘        │
                    │                        │                    │
                    │                  AffectSignal[]             │
                    └────────────────────┬────────────────────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │  EmotionModel     │
                              │  (21.1) .update() │
                              │  PADState delta   │
                              └──────────────────┘
```

---

## Enums

### `SentimentPolarity`

```python
class SentimentPolarity(str, Enum):
    """Categorical polarity classification."""
    POSITIVE  = "positive"
    NEGATIVE  = "negative"
    NEUTRAL   = "neutral"
    MIXED     = "mixed"      # both strong positive AND strong negative tokens
```

### `ModalityType`

```python
class ModalityType(str, Enum):
    """Input modality for affect detection."""
    TEXT       = "text"
    AUDIO      = "audio"
    IMAGE      = "image"
    VIDEO      = "video"
    MULTIMODAL = "multimodal"   # fused from multiple modalities
```

---

## Data Classes

### `AffectSignal`

```python
@dataclass(frozen=True)
class AffectSignal:
    """Single affect measurement from a detection pass."""
    polarity:    SentimentPolarity
    valence:     float                    # –1.0 (very negative) … +1.0 (very positive)
    arousal:     float                    # –1.0 (very calm) … +1.0 (very excited)
    confidence:  float                    # 0.0 … 1.0
    modality:    ModalityType
    source_span: tuple[int, int] | None   # char-offset span in source text (None for non-text)
    timestamp:   float                    # time.monotonic() at detection

    def __post_init__(self) -> None:
        if not (-1.0 <= self.valence <= 1.0):
            raise ValueError(f"valence must be in [-1, 1], got {self.valence}")
        if not (-1.0 <= self.arousal <= 1.0):
            raise ValueError(f"arousal must be in [-1, 1], got {self.arousal}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
        if self.source_span is not None and self.source_span[0] >= self.source_span[1]:
            raise ValueError(f"source_span[0] must be < source_span[1], got {self.source_span}")
```

**Invariants**:

| Field | Constraint |
|-------|-----------|
| `valence` | `−1.0 ≤ v ≤ 1.0` |
| `arousal` | `−1.0 ≤ a ≤ 1.0` |
| `confidence` | `0.0 ≤ c ≤ 1.0` |
| `source_span` | `span[0] < span[1]` when not None |

### `DetectorConfig`

```python
@dataclass(frozen=True)
class DetectorConfig:
    """Configuration for AffectDetector instances."""
    confidence_threshold: float = 0.3                  # signals below this are dropped
    batch_size:           int   = 32                   # max parallel detection tasks
    fusion_strategy:      str   = "weighted_average"   # "weighted_average" | "max_confidence" | "attention"
    modality_weights:     dict[ModalityType, float] = field(
        default_factory=lambda: {
            ModalityType.TEXT:  0.50,
            ModalityType.AUDIO: 0.25,
            ModalityType.IMAGE: 0.15,
            ModalityType.VIDEO: 0.10,
        }
    )
    lexicon_path:         str | None = None            # path to AFINN-style lexicon TSV
```

---

## Protocol

```python
@runtime_checkable
class AffectDetector(Protocol):
    """Detects affect signals from text or multimodal input."""

    async def detect(self, text: str) -> list[AffectSignal]:
        """Detect affect signals from a single text input (sentence-level granularity)."""
        ...

    async def detect_batch(self, texts: list[str]) -> list[list[AffectSignal]]:
        """Batch detection across multiple texts."""
        ...

    async def detect_multimodal(
        self, inputs: dict[ModalityType, Any]
    ) -> list[AffectSignal]:
        """Fuse affect signals from multiple modalities."""
        ...

    def get_aggregate_valence(self, signals: list[AffectSignal]) -> float:
        """Compute weighted aggregate valence from a list of signals."""
        ...
```

---

## Implementations

### `LexiconAffectDetector`

Rule-based detector using an AFINN-style valence lexicon.

```python
class LexiconAffectDetector:
    def __init__(self, config: DetectorConfig) -> None: ...

    async def detect(self, text: str) -> list[AffectSignal]: ...
    async def detect_batch(self, texts: list[str]) -> list[list[AffectSignal]]: ...
    async def detect_multimodal(
        self, inputs: dict[ModalityType, Any]
    ) -> list[AffectSignal]: ...
    def get_aggregate_valence(self, signals: list[AffectSignal]) -> float: ...

    # internals
    def _split_sentences(self, text: str) -> list[tuple[str, int, int]]: ...
    def _score_tokens(self, tokens: list[str]) -> float: ...
    def _apply_negation(self, tokens: list[str], scores: list[float]) -> list[float]: ...
    def _apply_intensifiers(self, tokens: list[str], scores: list[float]) -> list[float]: ...
    def _fuse_modalities(
        self, signals_by_modality: dict[ModalityType, list[AffectSignal]]
    ) -> list[AffectSignal]: ...
```

**Pipeline steps**:

1. **Sentence splitting** — regex boundary detection (`[.!?]+`)
2. **Tokenisation** — whitespace + punctuation strip
3. **Lexicon lookup** — each token mapped to valence score (−5 … +5)
4. **Negation handling** — 3-token window flips sign for tokens following negation words
5. **Intensifier detection** — multiplier table applied to the following scored token
6. **Score aggregation** — normalised to [−1, +1] valence; arousal = `abs(valence) × 0.8`
7. **Polarity classification** — POSITIVE if v > 0.05, NEGATIVE if v < −0.05, NEUTRAL otherwise; MIXED if both strong positive and negative tokens
8. **Confidence** — `min(1.0, matched_tokens / total_tokens × 2.0)`

#### Negation Words

```python
NEGATION_WORDS = frozenset({
    "not", "never", "no", "neither", "nor",
    "hardly", "barely", "scarcely",
})
NEGATION_WINDOW = 3  # tokens after negation word get sign-flipped
```

Contractions handled via suffix: `"isn't"`, `"don't"`, `"wasn't"` → detected by `endswith("n't")`.

#### Intensifier Multipliers

| Token | Multiplier | Example |
|-------|-----------|---------|
| `very` | 1.5× | "very good" → 1.5 × lexicon("good") |
| `extremely` | 2.0× | "extremely bad" → 2.0 × lexicon("bad") |
| `slightly` | 0.5× | "slightly annoyed" → 0.5 × lexicon("annoyed") |
| `somewhat` | 0.7× | "somewhat happy" → 0.7 × lexicon("happy") |
| `really` | 1.4× | "really great" → 1.4 × lexicon("great") |
| `incredibly` | 1.8× | "incredibly useful" → 1.8 × lexicon("useful") |
| `quite` | 1.2× | "quite nice" → 1.2 × lexicon("nice") |
| `a bit` | 0.6× | "a bit sad" → 0.6 × lexicon("sad") |

### `NullAffectDetector`

```python
class NullAffectDetector:
    """No-op implementation for testing / DI."""
    async def detect(self, text: str) -> list[AffectSignal]:
        return []
    async def detect_batch(self, texts: list[str]) -> list[list[AffectSignal]]:
        return [[] for _ in texts]
    async def detect_multimodal(
        self, inputs: dict[ModalityType, Any]
    ) -> list[AffectSignal]:
        return []
    def get_aggregate_valence(self, signals: list[AffectSignal]) -> float:
        return 0.0
```

### Factory

```python
def make_affect_detector(
    config: DetectorConfig | None = None,
    *,
    null: bool = False,
) -> AffectDetector:
    if null:
        return NullAffectDetector()
    return LexiconAffectDetector(config or DetectorConfig())
```

---

## Multimodal Fusion

```
  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
  │   TEXT    │     │  AUDIO   │     │  IMAGE   │     │  VIDEO   │
  │  w=0.50  │     │  w=0.25  │     │  w=0.15  │     │  w=0.10  │
  │ v=+0.8   │     │ v=+0.6   │     │ v=+0.3   │     │ v=+0.5   │
  └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
       │                │                │                │
       └───────┬────────┴────────┬───────┴────────┬───────┘
               │                 │                │
        ┌──────▼─────────────────▼────────────────▼──────┐
        │           Weighted Average Fusion               │
        │  v_fused = Σ(w_m × v_m) / Σ(w_m)              │
        └───────────────────┬────────────────────────────┘
                            │
                     ┌──────▼──────┐
                     │ AffectSignal│
                     │ MULTIMODAL  │
                     └─────────────┘
```

**Fusion strategies**:

| Strategy | Description | Use case |
|----------|-------------|----------|
| `weighted_average` | `v_fused = Σ(w_m × v_m) / Σ(w_m)` | Default — balanced fusion |
| `max_confidence` | Pick signal with highest confidence per window | When one modality is clearly dominant |
| `attention` (future) | Learnable cross-modal attention weights | ML-based fusion |

**Missing modalities** are excluded from weight normalisation — text-only input works identically to single-modality mode.

---

## Detection Pipeline

### Step-by-step Example

**Input**: `"I love this product. But the delivery was terrible!"`

**Step 1 — Sentence splitting**:
```
[("I love this product.", 0, 21), ("But the delivery was terrible!", 22, 52)]
```

**Step 2 — Token scoring (sentence 1)**:
```
tokens: [i, love, this, product]
scores: [0, 3,    0,    0]
```

**Step 3 — Aggregation (sentence 1)**:
```
raw_sum = 3, token_count = 4
valence = clamp(3 / (4 * 5) * 2, -1, 1) ≈ +0.30
arousal = abs(0.30) * 0.8 = 0.24
confidence = min(1.0, 1/4 * 2.0) = 0.50
polarity = POSITIVE (valence > 0.05)
```

### Negation Example

```
"This is not good at all"
  tokens: [this, is, not, good, at, all]
  scores: [0,    0,  0,   3,   0,  0]
  after negation:        -3   0    0
                         ↑ window ↑
  valence ≈ -0.20, polarity = NEGATIVE
```

### Intensifier Example

```
"very good"     → 1.5 × 3 = 4.5  → valence ≈ +0.90
"extremely bad" → 2.0 × -4 = -8  → valence = -1.00 (clamped)
"slightly upset" → 0.5 × -2 = -1 → valence ≈ -0.20
```

---

## EmotionModel Integration

`AffectSignal` feeds into `EmotionModel.update()` (Phase 21.1) via PADState conversion:

```python
# In EmotionOrchestrator (21.5) or integration layer:
signals = await affect_detector.detect(user_input)
for sig in signals:
    pad_delta = PADState(
        pleasure=sig.valence,     # direct map
        arousal=sig.arousal,      # direct map
        dominance=0.0,            # AffectDetector doesn't extract dominance
    )
    emotion_model.update(pad_delta, weight=sig.confidence)
```

**Note**: Dominance is set to 0.0 — the `EmpathyEngine` (21.4) contributes dominance estimates from context analysis.

### Cross-phase Integration Map

```
EmotionModel 21.1 ◄── AffectDetector 21.2 (valence + arousal signals)
     │                      ▲
     ▼                      │
MoodRegulator 21.3 ◄───────┘ (raw signals for trend analysis)
     │
     ▼
EmpathyEngine 21.4 ◄── AffectDetector 21.2 (context for dominance)
     │
     ▼
EmotionOrchestrator 21.5 (fuses all sub-systems)
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `affect_detections_total` | Counter | `polarity`, `modality` | Total affect signals detected |
| `affect_detection_latency_seconds` | Histogram | `modality` | Detection latency per call |
| `affect_average_valence` | Gauge | — | EWMA of recent valence scores |
| `affect_average_arousal` | Gauge | — | EWMA of recent arousal scores |
| `affect_low_confidence_ratio` | Gauge | — | Ratio of signals below confidence threshold |

### PromQL Examples

```promql
# Detection rate by polarity
sum(rate(affect_detections_total[5m])) by (polarity)

# p95 detection latency
histogram_quantile(0.95, rate(affect_detection_latency_seconds_bucket[5m]))

# Low confidence alert
affect_low_confidence_ratio > 0.6
```

### Grafana Alerts

```yaml
groups:
  - name: affect_detector
    rules:
      - alert: HighLowConfidenceRatio
        expr: affect_low_confidence_ratio > 0.6
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "AffectDetector low confidence ratio above 60%"

      - alert: AffectDetectionLatencyHigh
        expr: histogram_quantile(0.95, rate(affect_detection_latency_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning

      - alert: NegativeValenceSpike
        expr: affect_average_valence < -0.7
        for: 5m
        labels:
          severity: info
        annotations:
          summary: "Sustained negative valence detected"
```

---

## mypy Narrowing

| Pattern | Technique |
|---------|-----------|
| `source_span: tuple[int,int] \| None` | `if sig.source_span is not None:` |
| `ModalityType` dict keys | `dict[ModalityType, Any]` — exhaustive match via `for m in ModalityType:` |
| `config.lexicon_path: str \| None` | `if config.lexicon_path is not None:` |
| `polarity` classification | match/case on `SentimentPolarity` enum |

---

## Test Targets (12)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_positive_sentence_valence` | "I love this" → valence > 0, polarity POSITIVE |
| 2 | `test_negative_sentence_valence` | "I hate this" → valence < 0, polarity NEGATIVE |
| 3 | `test_neutral_sentence` | "The table is brown" → polarity NEUTRAL |
| 4 | `test_mixed_sentiment` | "I love the food but hate the service" → polarity MIXED |
| 5 | `test_negation_flips_polarity` | "not good" → valence < 0 |
| 6 | `test_intensifier_amplifies` | "very good" valence > "good" valence |
| 7 | `test_confidence_bounds` | All signals have 0 ≤ confidence ≤ 1 |
| 8 | `test_batch_detection_length` | detect_batch(n texts) → n result lists |
| 9 | `test_aggregate_valence_weighted` | Weighted average matches manual calc |
| 10 | `test_multimodal_fusion_weighted_average` | Fused signal uses modality weights |
| 11 | `test_source_span_offsets` | span[0] < span[1], covers sentence |
| 12 | `test_null_detector_returns_empty` | NullAffectDetector → empty lists, 0.0 valence |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_negation_flips_polarity():
    """Negation should flip valence sign within 3-token window."""
    det = make_affect_detector()
    signals_pos = await det.detect("This is good.")
    signals_neg = await det.detect("This is not good.")
    assert signals_pos[0].valence > 0
    assert signals_neg[0].valence < 0
    assert signals_neg[0].polarity == SentimentPolarity.NEGATIVE


@pytest.mark.asyncio
async def test_intensifier_amplifies():
    """Intensifier 'very' should increase absolute valence."""
    det = make_affect_detector()
    base = await det.detect("This is good.")
    amplified = await det.detect("This is very good.")
    assert abs(amplified[0].valence) > abs(base[0].valence)
    assert amplified[0].polarity == SentimentPolarity.POSITIVE
```

---

## Implementation Order (14 steps)

1. Create `emotion/affect_detector.py` with `SentimentPolarity`, `ModalityType` enums
2. Add `AffectSignal` frozen dataclass with `__post_init__` validation
3. Add `DetectorConfig` frozen dataclass
4. Define `AffectDetector` Protocol
5. Load AFINN-style lexicon (TSV: `word \t score`)
6. Implement `_split_sentences()` with char-offset tracking
7. Implement `_score_tokens()` with lexicon lookup
8. Implement `_apply_negation()` — 3-token window
9. Implement `_apply_intensifiers()` — multiplier table
10. Implement `detect()` — full pipeline per sentence
11. Implement `detect_batch()` — `asyncio.gather` parallelism
12. Implement `detect_multimodal()` + `_fuse_modalities()`
13. Implement `get_aggregate_valence()` — weighted mean
14. Wire Prometheus metrics + `NullAffectDetector` + factory

---

## Phase 21 Sub-phase Tracker

| # | Component | Issue | Wiki | Status |
|---|-----------|-------|------|--------|
| 21.1 | EmotionModel | [#498](https://github.com/web3guru888/asi-build/issues/498) | [Wiki](Phase-21-Emotion-Model) | 🟡 Spec'd |
| 21.2 | AffectDetector | [#499](https://github.com/web3guru888/asi-build/issues/499) | **This page** | 🟡 Spec'd |
| 21.3 | MoodRegulator | — | — | ⬜ Pending |
| 21.4 | EmpathyEngine | — | — | ⬜ Pending |
| 21.5 | EmotionOrchestrator | — | — | ⬜ Pending |

---

*Last updated: 2026-04-13 · Phase 21 — Emotion & Affect*
