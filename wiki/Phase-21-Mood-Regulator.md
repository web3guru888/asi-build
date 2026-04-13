# Phase 21.4 — MoodRegulator

> **Mood homeostasis, regulation strategies, emotional resilience & burnout prevention**

| Field | Value |
|---|---|
| **Issue** | [#501](https://github.com/web3guru888/asi-build/issues/501) |
| **Show & Tell** | [#508](https://github.com/web3guru888/asi-build/discussions/508) |
| **Q&A** | [#511](https://github.com/web3guru888/asi-build/discussions/511) |
| **Phase** | 21 — Emotional Intelligence & Affect |
| **Depends on** | [EmotionModel #500](https://github.com/web3guru888/asi-build/issues/500) (PADState, EmotionState) |
| **Feeds into** | Phase 21.5 EmotionalOrchestrator (mood homeostasis loop + burnout signals) |
| **Status** | 🟡 Spec'd |

---

## Overview

**MoodRegulator** maintains emotional equilibrium through homeostatic feedback loops. While `EmotionModel` (21.1) captures instantaneous emotional state, MoodRegulator operates at a longer timescale — maintaining a baseline, detecting chronic stress, selecting regulation strategies, and building resilience through experience.

**Key insight**: Emotions are acute; *mood* is chronic. MoodRegulator bridges this gap with homeostatic feedback that pulls emotional state back toward a healthy baseline while adapting that baseline through experience.

### Design Goals

| Goal | Mechanism |
|---|---|
| Mood homeostasis | Exponential pull toward `baseline_pad` every cycle |
| Volatility tracking | Sliding-window std-dev of recent PAD deltas |
| Stress detection | Accumulated deviation from baseline + volatility |
| Burnout prevention | Threshold gate → forced cooldown + DISTRACTION strategy |
| Resilience growth | Successful regulation → incremental resilience increase |
| Strategy selection | Context-dependent: stress level → decision tree → strategy |

---

## Data Structures

### RegulationStrategy (Enum)

```python
class RegulationStrategy(str, Enum):
    SUPPRESSION   = "suppression"    # Dampen intensity — reduce PAD magnitude toward neutral
    REAPPRAISAL   = "reappraisal"    # Reinterpret stimulus — shift valence without dampening arousal
    DISTRACTION   = "distraction"    # Shift attention — decouple current PAD from stimulus
    ACCEPTANCE    = "acceptance"     # Allow natural decay — minimal intervention, ride it out
    ADAPTIVE      = "adaptive"       # Context-dependent strategy selection (meta-strategy)
```

### MoodState (frozen dataclass)

```python
@dataclass(frozen=True)
class MoodState:
    baseline_pad: PADState          # Long-term emotional set-point
    current_pad: PADState           # Current mood (smoothed from recent emotions)
    volatility: float               # 0..1 — std dev of recent PAD changes
    resilience: float               # 0..1 — capacity to recover from perturbation
    stress_level: float             # 0..1 — accumulated deviation + volatility
    regulation_count: int           # Total regulations applied this session
```

### RegulatorConfig (frozen dataclass)

```python
@dataclass(frozen=True)
class RegulatorConfig:
    homeostasis_rate: float = 0.02          # Exponential pull factor per cycle
    volatility_window: int = 50             # Number of recent PAD deltas to track
    stress_threshold: float = 0.7           # Stress level that triggers aggressive regulation
    burnout_threshold: float = 0.9          # Stress level that triggers burnout cooldown
    resilience_growth: float = 0.001        # Resilience increment per successful regulation
    min_regulation_interval_s: float = 0.5  # Rate-limit between regulate() calls
```

### RegulationResult (frozen dataclass)

```python
@dataclass(frozen=True)
class RegulationResult:
    strategy_used: RegulationStrategy   # Which strategy was actually applied
    before_pad: PADState                # PAD state before regulation
    after_pad: PADState                 # PAD state after regulation
    stress_delta: float                 # Change in stress level (negative = reduced)
    effectiveness: float                # 0..1 — how much the regulation moved PAD toward baseline
```

---

## Protocol

```python
@runtime_checkable
class MoodRegulator(Protocol):
    async def regulate(self, emotion_state: EmotionState) -> RegulationResult:
        """Apply regulation strategy to current emotional state."""
        ...

    def get_mood(self) -> MoodState:
        """Return current mood snapshot."""
        ...

    def update_baseline(self, new_pad: PADState) -> None:
        """Shift the homeostatic baseline (long-term adaptation)."""
        ...

    def get_stress_level(self) -> float:
        """Return current stress level (0..1)."""
        ...

    def check_burnout(self) -> bool:
        """Return True if agent is in burnout state."""
        ...

    def reset(self) -> None:
        """Reset mood state to defaults."""
        ...
```

---

## Implementation — HomeostaticMoodRegulator

### Regulation Pipeline

```
regulate(emotion_state):
    1. Rate-limit check (min_regulation_interval_s)
    2. Compute PAD delta from baseline → deviation
    3. Update sliding window → recalculate volatility
    4. Update stress_level = clamp(0.7 * deviation + 0.3 * volatility, 0, 1)
    5. Select strategy via decision tree:
       - burnout detected        → DISTRACTION (forced)
       - stress > 0.7            → SUPPRESSION
       - 0.3 ≤ stress ≤ 0.7     → REAPPRAISAL
       - stress < 0.3            → ACCEPTANCE
       - config = ADAPTIVE       → above tree (default)
    6. Apply strategy:
       - SUPPRESSION:  new_pad = lerp(current, neutral, 0.4)
       - REAPPRAISAL:  new_pad = PADState(pleasure=lerp(p, baseline.p, 0.5),
                                          arousal=current.arousal, dominance=current.dominance)
       - DISTRACTION:  new_pad = lerp(current, baseline, 0.6)
       - ACCEPTANCE:   new_pad = lerp(current, baseline, homeostasis_rate)
    7. Homeostatic pull: final_pad = lerp(new_pad, baseline, homeostasis_rate)
    8. Track effectiveness = 1 - (dist(final_pad, baseline) / dist(before_pad, baseline))
    9. If effectiveness > 0.5 → grow resilience by resilience_growth
   10. Update Prometheus metrics
   11. Return RegulationResult
```

### Homeostasis Formula

```python
def _homeostatic_pull(self, current: PADState, baseline: PADState, rate: float) -> PADState:
    return PADState(
        pleasure=current.pleasure + rate * (baseline.pleasure - current.pleasure),
        arousal=current.arousal + rate * (baseline.arousal - current.arousal),
        dominance=current.dominance + rate * (baseline.dominance - current.dominance),
    )
```

With `homeostasis_rate=0.02`, after 35 cycles the current PAD is ≈50% of the way back to baseline (`0.98^35 ≈ 0.49`).

### Volatility Calculation

```python
def _compute_volatility(self) -> float:
    if len(self._pad_deltas) < 2:
        return 0.0
    sigma = statistics.stdev(self._pad_deltas)
    return min(sigma / 1.73, 1.0)  # normalised to 0..1
```

### Strategy Selection Decision Tree

```
                    ┌─── burnout? ──── YES ──→ DISTRACTION (forced)
                    │
   regulate() ──────┤
                    │         ┌─── stress > 0.7 ──→ SUPPRESSION
                    └── NO ───┤
                              ├─── 0.3 ≤ stress ≤ 0.7 ──→ REAPPRAISAL
                              │
                              └─── stress < 0.3 ──→ ACCEPTANCE
```

### Strategy Effects

| Strategy | Formula | Effect |
|---|---|---|
| SUPPRESSION | `lerp(current, neutral, 0.4)` | Dampen all axes toward zero |
| REAPPRAISAL | `pleasure → lerp(p, baseline.p, 0.5)` | Shift valence, keep arousal/dominance |
| DISTRACTION | `lerp(current, baseline, 0.6)` | Strong pull to baseline |
| ACCEPTANCE | `lerp(current, baseline, homeostasis_rate)` | Gentle natural decay |

### Burnout Detection & Recovery

```
if stress_level > burnout_threshold:
    _burnout_counter += 1
    if _burnout_counter >= 3:
        _burnout = True
        _burnout_cooldown_remaining = 10  # 10 cycles of forced DISTRACTION
else:
    _burnout_counter = 0

if _burnout:
    strategy = DISTRACTION  # override any selection
    _burnout_cooldown_remaining -= 1
    if _burnout_cooldown_remaining <= 0:
        _burnout = False
        _burnout_counter = 0
```

### Internal State

| Field | Type | Purpose |
|---|---|---|
| `_pad_deltas` | `deque[float]` (maxlen=50) | Sliding window of PAD Euclidean deltas |
| `_strategy_effectiveness` | `dict[RegulationStrategy, RunningMean]` | Per-strategy running mean |
| `_burnout` | `bool` | Burnout flag |
| `_burnout_cooldown_remaining` | `int` | Cooldown cycles remaining |
| `_burnout_counter` | `int` | Consecutive high-stress cycles |
| `_last_regulation_time` | `float` | Monotonic timestamp for rate-limiting |
| `_lock` | `asyncio.Lock` | Serialise concurrent regulate() calls |

### Resilience Growth

Resilience grows at `0.001` per successful regulation (effectiveness > 0.5) and **never decays**:

| Regulations | Resilience | Recovery bonus |
|---|---|---|
| 0 | 0.000 | 1.0× |
| 100 | 0.100 | 1.1× |
| 500 | 0.500 | 1.5× |
| 1000 | 1.000 (max) | 2.0× |

Applied as: `effective_rate = homeostasis_rate × (1 + resilience)`

---

## Null Implementation

```python
class NullMoodRegulator:
    async def regulate(self, emotion_state):
        return RegulationResult(ACCEPTANCE, emotion_state.pad, emotion_state.pad, 0.0, 0.0)
    def get_mood(self):
        return MoodState(PADState.neutral(), PADState.neutral(), 0.0, 0.5, 0.0, 0)
    def update_baseline(self, new_pad): pass
    def get_stress_level(self): return 0.0
    def check_burnout(self): return False
    def reset(self): pass
```

---

## Factory

```python
def make_mood_regulator(
    *,
    config: RegulatorConfig | None = None,
    emotion_model: EmotionModel | None = None,
    null: bool = False,
) -> MoodRegulator:
    if null:
        return NullMoodRegulator()
    return HomeostaticMoodRegulator(config=config or RegulatorConfig(), emotion_model=emotion_model)
```

---

## Integration

### Data Flow

```
EmotionModel (21.1) ──── EmotionState ────▶ MoodRegulator (21.4)
                                                  │
AffectDetector (21.2) ── stimulus context ──▶     │
                                                  │
EmpathyEngine (21.3) ── empathy signals ──▶       │
                                                  ▼
                                        RegulationResult
                                                  │
                                                  ▼
                                    EmotionalOrchestrator (21.5)
                                          │
                          ┌───────────────┼───────────────┐
                          ▼               ▼               ▼
                    ResponseGenerator  CognitiveCycle  PerformanceProfiler
                    (19.3) mood-tone   _emotional_step  stress input (16.1)
```

### Cross-Phase Dependencies

| Phase | Component | Integration |
|---|---|---|
| 21.1 | EmotionModel | Provides PADState + EmotionState input |
| 21.2 | AffectDetector | Stimulus context for regulation decisions |
| 21.3 | EmpathyEngine | Empathy signals modulate regulation intensity |
| 21.5 | EmotionalOrchestrator | Applies RegulationResult back to EmotionModel |
| 16.1 | PerformanceProfiler | Stress level as performance input |
| 18.2 | MemoryConsolidator | Strategy effectiveness persistence |
| 19.3 | ResponseGenerator | Mood-modulated tone in generated responses |

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `asi_mood_regulations_total` | Counter | `strategy` | Regulations applied, by strategy |
| `asi_mood_stress_level` | Gauge | — | Current stress level (0..1) |
| `asi_mood_burnout_events_total` | Counter | — | Burnout events triggered |
| `asi_mood_resilience` | Gauge | — | Current resilience level (0..1) |
| `asi_mood_volatility` | Gauge | — | Current mood volatility (0..1) |

### PromQL Examples

```promql
# Regulation rate by strategy (per minute)
rate(asi_mood_regulations_total[5m]) * 60

# Burnout event rate
rate(asi_mood_burnout_events_total[1h])

# Stress level trend
avg_over_time(asi_mood_stress_level[15m])

# Resilience growth rate
deriv(asi_mood_resilience[1h])
```

### Grafana Alerts

```yaml
- alert:
    name: "Sustained Emotional Stress"
    expr: 'asi_mood_stress_level > 0.7'
    for: 5m
    labels: { severity: warning }

- alert:
    name: "Burnout Event Spike"
    expr: 'rate(asi_mood_burnout_events_total[1h]) > 0.1'
    labels: { severity: critical }

- alert:
    name: "Mood Volatility High"
    expr: 'asi_mood_volatility > 0.8'
    for: 3m
    labels: { severity: warning }
```

---

## mypy Compliance

| Pattern | Narrowing |
|---|---|
| `RegulationStrategy(str, Enum)` | `isinstance(s, RegulationStrategy)` narrows |
| `MoodState` frozen dataclass | Immutable, hashable, type-safe |
| `@runtime_checkable Protocol` | `isinstance(obj, MoodRegulator)` works at runtime |
| `match strategy:` | Exhaustive match on enum requires `case _: assert_never()` |
| `deque[float]` | Generic deque type hint (Python 3.9+) |

---

## Test Targets (12)

| # | Test | Validates |
|---|---|---|
| 1 | `test_regulate_returns_regulation_result` | regulate() returns RegulationResult with correct fields |
| 2 | `test_homeostasis_pulls_toward_baseline` | After perturbation, PAD moves toward baseline |
| 3 | `test_volatility_tracks_recent_deltas` | Volatility reflects sliding window std-dev |
| 4 | `test_stress_level_combines_deviation_and_volatility` | stress_level = 0.7*dev + 0.3*vol |
| 5 | `test_strategy_selection_low_stress_acceptance` | stress < 0.3 → ACCEPTANCE |
| 6 | `test_strategy_selection_mid_stress_reappraisal` | 0.3 ≤ stress ≤ 0.7 → REAPPRAISAL |
| 7 | `test_strategy_selection_high_stress_suppression` | stress > 0.7 → SUPPRESSION |
| 8 | `test_burnout_forces_distraction` | 3+ high-stress cycles → DISTRACTION override |
| 9 | `test_burnout_cooldown_recovery` | Burnout clears after cooldown cycles |
| 10 | `test_resilience_growth_on_effective_regulation` | effectiveness > 0.5 → resilience += growth |
| 11 | `test_rate_limiting_respects_interval` | Two rapid regulate() calls → second skipped/delayed |
| 12 | `test_null_regulator_returns_defaults` | NullMoodRegulator returns neutral defaults |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_homeostasis_pulls_toward_baseline():
    reg = make_mood_regulator()
    perturbed = EmotionState(pad=PADState(pleasure=0.0, arousal=0.9, dominance=0.5))
    results = []
    for _ in range(20):
        r = await reg.regulate(perturbed)
        results.append(r)
    first_dist = _pad_distance(results[0].before_pad, reg.get_mood().baseline_pad)
    last_dist = _pad_distance(results[-1].after_pad, reg.get_mood().baseline_pad)
    assert last_dist < first_dist * 0.5

@pytest.mark.asyncio
async def test_burnout_forces_distraction():
    cfg = RegulatorConfig(burnout_threshold=0.5)
    reg = make_mood_regulator(config=cfg)
    extreme = EmotionState(pad=PADState(pleasure=-1.0, arousal=1.0, dominance=-1.0))
    for _ in range(3):
        await reg.regulate(extreme)
    assert reg.check_burnout() is True
    result = await reg.regulate(extreme)
    assert result.strategy_used == RegulationStrategy.DISTRACTION
```

---

## Implementation Order (14 steps)

1. `RegulationStrategy` enum
2. `MoodState` frozen dataclass
3. `RegulatorConfig` frozen dataclass
4. `RegulationResult` frozen dataclass
5. `MoodRegulator` Protocol
6. `NullMoodRegulator`
7. `HomeostaticMoodRegulator.__init__` + sliding window + lock
8. `HomeostaticMoodRegulator._compute_volatility`
9. `HomeostaticMoodRegulator._select_strategy` decision tree
10. `HomeostaticMoodRegulator._apply_strategy` (4 strategies + lerp)
11. `HomeostaticMoodRegulator.regulate` full pipeline
12. Burnout detection + cooldown + resilience growth
13. `make_mood_regulator()` factory + Prometheus metrics
14. Tests (12 targets)

---

## Phase 21 Sub-Phase Tracker

| Sub-phase | Component | Issue | Wiki | Status |
|---|---|---|---|---|
| 21.1 | EmotionModel | [#500](https://github.com/web3guru888/asi-build/issues/500) | [Page](Phase-21-Emotion-Model) | 🟡 Spec'd |
| 21.2 | AffectDetector | [#499](https://github.com/web3guru888/asi-build/issues/499) | [Page](Phase-21-Affect-Detector) | 🟡 Spec'd |
| 21.3 | EmpathyEngine | [#498](https://github.com/web3guru888/asi-build/issues/498) | [Page](Phase-21-Empathy-Engine) | 🟡 Spec'd |
| 21.4 | **MoodRegulator** | [**#501**](https://github.com/web3guru888/asi-build/issues/501) | **This page** | 🟡 Spec'd |
| 21.5 | EmotionalOrchestrator | — | — | ⬜ Pending |

---

*Last updated: 2026-04-13*
