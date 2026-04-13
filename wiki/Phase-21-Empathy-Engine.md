# Phase 21.3 — EmpathyEngine

> **Epic**: Phase 21 — Emotional Intelligence & Social Cognition · [Planning Discussion](https://github.com/web3guru888/asi-build/discussions/497)
> **Issue**: [#498](https://github.com/web3guru888/asi-build/issues/498) · **Show & Tell**: [#504](https://github.com/web3guru888/asi-build/discussions/504) · **Q&A**: [#505](https://github.com/web3guru888/asi-build/discussions/505)
> **Source**: `src/asi_build/emotional/empathy_engine.py` · **Tests**: `tests/unit/emotional/test_empathy_engine.py`

---

## Overview

The **EmpathyEngine** provides theory-of-mind emotional modeling — the ability to understand, predict, and respond to other agents' emotional states. It maintains Bayesian belief profiles for each interacting agent, tracks empathic accuracy over time, and modulates responses through three empathy modes: cognitive understanding, affective mirroring, and compassionate action.

This component builds on the `PADState` representation from Phase 21.1 (EmotionCore) and feeds into the DialogueManager (Phase 19.2) and ResponseGenerator (Phase 19.3) for emotionally-aware communication.

---

## Public API

### `EmpathyMode` — Enum

| Member | Value | Description |
|---|---|---|
| `COGNITIVE` | `"cognitive"` | Understanding others' emotions without necessarily feeling them |
| `AFFECTIVE` | `"affective"` | Vicariously experiencing others' emotional states (mirror neurons) |
| `COMPASSIONATE` | `"compassionate"` | Emotion understanding that motivates helping/adaptive behavior |

### `AgentProfile` — Frozen Dataclass

| Field | Type | Default | Description |
|---|---|---|---|
| `agent_id` | `str` | — | Unique identifier for the target agent |
| `estimated_pad` | `PADState` | — | Current Bayesian estimate of the agent's PAD state |
| `confidence` | `float` | `0.5` | Confidence in the estimate (0.0–1.0) |
| `interaction_count` | `int` | `0` | Number of observations incorporated |
| `last_updated` | `float` | — | Monotonic timestamp of last profile update |
| `accuracy_history` | `tuple[float, ...]` | `()` | Rolling window of empathic accuracy scores |

### `EmpathyConfig` — Frozen Dataclass

| Field | Type | Default | Description |
|---|---|---|---|
| `perspective_decay` | `float` | `0.1` | Exponential decay rate for older observations |
| `min_interactions` | `int` | `3` | Minimum observations before COGNITIVE mode activates |
| `mirror_strength` | `float` | `0.3` | Blending weight for AFFECTIVE mirroring (0.0–1.0) |
| `compassion_threshold` | `float` | `0.6` | Confidence threshold to trigger COMPASSIONATE mode |
| `max_profiles` | `int` | `500` | LRU eviction cap for agent profiles |
| `accuracy_window` | `int` | `20` | Rolling window size for accuracy tracking |
| `prior_pad` | `PADState \| None` | `None` | Bayesian prior (defaults to neutral PAD) |

### `EmpathyResult` — Frozen Dataclass

| Field | Type | Default | Description |
|---|---|---|---|
| `target_id` | `str` | — | Agent being assessed |
| `mode` | `EmpathyMode` | — | Which empathy mode was applied |
| `estimated_state` | `PADState` | — | Estimated PAD state for the target |
| `accuracy` | `float` | — | Historical empathic accuracy (0.0–1.0) |
| `confidence` | `float` | — | Confidence in this assessment |
| `recommended_response_tone` | `str` | — | `"supportive"`, `"neutral"`, `"celebratory"`, `"calming"` |

### `EmpathyEngine` — Protocol (`@runtime_checkable`)

```python
@runtime_checkable
class EmpathyEngine(Protocol):
    async def assess(self, target_id: str, context: dict[str, Any] | None = None) -> EmpathyResult: ...
    async def update_profile(self, target_id: str, observed_pad: PADState) -> AgentProfile: ...
    async def get_profile(self, target_id: str) -> AgentProfile | None: ...
    async def mirror(self, target_pad: PADState) -> PADState: ...
    async def get_accuracy_history(self, target_id: str, n: int = 10) -> tuple[float, ...]: ...
```

| Method | Description |
|---|---|
| `assess(target_id, context)` | Predict target's emotional state and recommend response tone |
| `update_profile(target_id, observed_pad)` | Incorporate new observation via Bayesian update |
| `get_profile(target_id)` | Retrieve current belief profile for an agent |
| `mirror(target_pad)` | Blend target's PAD into own state (affective empathy) |
| `get_accuracy_history(target_id, n)` | Return last `n` accuracy scores |

---

## Implementation — `CognitiveEmpathyEngine`

```python
class CognitiveEmpathyEngine:
    def __init__(self, config: EmpathyConfig | None = None) -> None: ...
```

### Internal State

- `_profiles: dict[str, AgentProfile]` — LRU-ordered agent profiles
- `_lock: asyncio.Lock` — serialises profile mutations
- `_config: EmpathyConfig` — frozen configuration
- `_prior: PADState` — Bayesian prior (neutral if not configured)

### Key Algorithms

#### 1. Bayesian PAD Estimation (`update_profile`)

```
α = perspective_decay ^ interaction_count
posterior = α · prior + (1 - α) · observed
confidence = min(1.0, interaction_count / (interaction_count + min_interactions))
```

Convergence behavior with default `perspective_decay = 0.1`:

| Interaction | α | Weight on observation |
|---|---|---|
| 0 | 1.000 | 0% (pure prior) |
| 1 | 0.100 | 90% |
| 3 | 0.001 | 99.9% |
| 5 | 0.00001 | ≈100% |

#### 2. Empathy Mode Selection (`assess`)

```
interaction_count < min_interactions  →  COGNITIVE (inference-only)
confidence ≥ compassion_threshold
  AND estimated_pad.pleasure < -0.3  →  COMPASSIONATE (help mode)
otherwise                            →  AFFECTIVE (mirror mode)
```

#### 3. Affective Mirroring (`mirror`)

```python
mirrored = PADState(
    pleasure = clamp(own.pleasure * (1 - s) + target.pleasure * s),
    arousal  = clamp(own.arousal  * (1 - s) + target.arousal  * s),
    dominance= clamp(own.dominance* (1 - s) + target.dominance* s),
)
```

Where `s = mirror_strength` (default 0.3). Each dimension clamped to [-1.0, 1.0].

#### 4. Accuracy Tracking

On each `update_profile`:
1. `distance = sqrt((p₁-p₂)² + (a₁-a₂)² + (d₁-d₂)²)`
2. `accuracy = 1.0 - distance / sqrt(12)` — normalised to [0, 1]
3. Append to rolling `accuracy_history` (capped at `accuracy_window`)

#### 5. Response Tone Mapping

| Condition | Tone |
|---|---|
| `pleasure < -0.3 AND dominance < 0.0` | `"supportive"` |
| `pleasure > 0.5` | `"celebratory"` |
| `arousal > 0.6 AND pleasure < 0.0` | `"calming"` |
| otherwise | `"neutral"` |

#### 6. LRU Eviction

When `len(_profiles) > max_profiles`, evict the profile with the oldest `last_updated` timestamp.

---

## Implementation — `NullEmpathyEngine`

No-op implementation for testing and dependency injection. Returns neutral `EmpathyResult`, `None` profiles, identity mirror, and empty accuracy history.

---

## Factory

```python
def make_empathy_engine(
    config: EmpathyConfig | None = None,
    *,
    null: bool = False,
) -> EmpathyEngine:
    if null:
        return NullEmpathyEngine()
    return CognitiveEmpathyEngine(config)
```

---

## Architecture

```
                ┌─────────────────────────────────────────────────────────┐
                │                    EmpathyEngine                        │
                │                                                         │
  observed PAD  │  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
  ─────────────►│  │   Bayesian   │───►│    Mode      │───►│  Tone     │ │──► EmpathyResult
                │  │   Updater    │    │  Selector    │    │  Mapper   │ │
                │  └──────┬───────┘    └──────────────┘    └───────────┘ │
                │         │                                               │
                │         ▼                                               │
                │  ┌──────────────┐    ┌──────────────┐                  │
                │  │   Agent      │    │  Accuracy    │                  │
                │  │  Profiles    │◄──►│  Tracker     │                  │
                │  │  (LRU dict)  │    │  (rolling)   │                  │
                │  └──────────────┘    └──────────────┘                  │
                │                                                         │
                │  ┌──────────────┐                                      │
  target PAD    │  │  Affective   │                                      │
  ─────────────►│  │   Mirror     │──► mirrored PADState                 │
                │  └──────────────┘                                      │
                └─────────────────────────────────────────────────────────┘
```

### Perspective-Taking Pipeline

```
1. RETRIEVE     agent_profiles[target_id]
        │
        ▼
2. EVALUATE     interaction_count vs min_interactions
        │
        ├── < min_interactions ──► COGNITIVE (inference only)
        │
        ▼
3. CHECK        confidence ≥ compassion_threshold AND pleasure < -0.3
        │
        ├── threshold met ──► COMPASSIONATE (help mode)
        │
        ▼
4. DEFAULT      ──► AFFECTIVE (mirror mode)
        │
        ▼
5. MAP TONE     PAD → "supportive" | "calming" | "celebratory" | "neutral"
        │
        ▼
6. EMIT         EmpathyResult { target_id, mode, estimated_state, accuracy, tone }
```

### Agent Profile Lifecycle

```
  New Agent          Observation #1        Observation #3+         Observation #10+
  ┌─────────┐       ┌─────────────┐       ┌──────────────┐       ┌───────────────┐
  │ Unknown  │──────►│  COGNITIVE   │──────►│  AFFECTIVE   │──────►│ COMPASSIONATE │
  │ (prior)  │       │  α = 0.1    │       │  confidence↑ │       │  if distressed│
  │ conf=0.0 │       │  conf≈0.25  │       │  conf≈0.50   │       │  conf≥0.60    │
  └─────────┘       └─────────────┘       └──────────────┘       └───────────────┘
```

---

## Integration Map

```
EmotionCore (21.1) ──► PADState ──► EmpathyEngine (21.3)
                                         │
MoodRegulator (21.2) ◄── mirror() ◄──────┤
                                         │
DialogueManager (19.2) ◄── assess() ◄────┤
                                         │
ResponseGenerator (19.3) ◄── tone ◄──────┤
                                         │
AlignmentAuditor (11.2) ◄── COMPASSIONATE mode gate
                                         │
SocialCognition (21.4) ◄── AgentProfile ─┘
```

- **EmotionCore (21.1)**: Provides `PADState` representation used throughout
- **MoodRegulator (21.2)**: Receives mirrored PAD from `mirror()`, applies damping
- **DialogueManager (19.2)**: Calls `assess()` before generating responses
- **ResponseGenerator (19.3)**: Uses `recommended_response_tone` to modulate output
- **AlignmentAuditor (11.2)**: Gates COMPASSIONATE mode actions through value bounds
- **SocialCognition (21.4)**: Consumes `AgentProfile` data for group dynamics modeling

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `empathy_assessments_total` | Counter | `mode`, `tone` | Total assessments by mode and tone |
| `empathic_accuracy_gauge` | Gauge | `target_id` | Rolling accuracy per tracked agent |
| `active_profiles_gauge` | Gauge | — | Number of active agent profiles |
| `compassion_triggers_total` | Counter | — | COMPASSIONATE mode activations |
| `mirror_strength_histogram` | Histogram | — | Distribution of mirror strength values |

### PromQL Examples

```promql
# Compassion trigger rate
rate(compassion_triggers_total[1h])

# Fleet-wide empathic accuracy
avg(empathic_accuracy_gauge)

# Memory pressure
active_profiles_gauge / 500  # ratio to max_profiles

# Mode distribution
sum by (mode) (rate(empathy_assessments_total[5m]))
```

### Grafana Alerts

```yaml
# Empathy model degraded
- alert: EmpathicAccuracyLow
  expr: avg(empathic_accuracy_gauge) < 0.3
  for: 10m
  labels: { severity: warning }
  annotations:
    summary: "Fleet-wide empathic accuracy below 30%"

# Profile eviction pressure
- alert: ProfileEvictionPressure
  expr: active_profiles_gauge > 450  # 90% of default max
  for: 5m
  labels: { severity: info }

# Unusual distress detection
- alert: HighCompassionRate
  expr: rate(compassion_triggers_total[5m]) > 20
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "Unusually high distress detection rate"
```

---

## mypy Strict Compliance

| Pattern | Narrowing |
|---|---|
| `EmpathyMode(value)` | `str → EmpathyMode` via enum constructor |
| `get_profile() → AgentProfile \| None` | `if profile is not None:` guard |
| `context: dict[str, Any] \| None` | `context = context or {}` at method entry |
| `_prior: PADState` | Assigned in `__init__`, never `None` |
| `accuracy_history: tuple[float, ...]` | Immutable, safe for frozen dataclass |

---

## Test Targets (12)

| # | Test | Assertion |
|---|---|---|
| 1 | `test_empathy_mode_values` | Enum members match expected strings |
| 2 | `test_agent_profile_frozen` | `AgentProfile` is immutable |
| 3 | `test_empathy_config_defaults` | Default values match spec |
| 4 | `test_bayesian_update_converges` | After 20 observations of same PAD, estimate within ε |
| 5 | `test_cognitive_mode_low_interactions` | < min_interactions → COGNITIVE |
| 6 | `test_compassionate_mode_triggers` | High confidence + negative pleasure → COMPASSIONATE |
| 7 | `test_affective_mirror_blending` | `mirror()` produces correct weighted blend |
| 8 | `test_accuracy_tracking_rolling_window` | History capped at `accuracy_window` |
| 9 | `test_lru_eviction` | Exceeding max_profiles evicts oldest |
| 10 | `test_response_tone_mapping` | Tone labels match PAD thresholds |
| 11 | `test_null_engine_no_op` | NullEmpathyEngine returns defaults |
| 12 | `test_factory_dispatch` | `make_empathy_engine(null=True/False)` returns correct type |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_bayesian_update_converges():
    """After 20 identical observations, estimate should be within ε of observed."""
    engine = CognitiveEmpathyEngine(EmpathyConfig(perspective_decay=0.1))
    target = PADState(pleasure=0.8, arousal=-0.3, dominance=0.5)
    for _ in range(20):
        await engine.update_profile("agent-A", target)
    profile = await engine.get_profile("agent-A")
    assert profile is not None
    assert abs(profile.estimated_pad.pleasure - 0.8) < 0.01
    assert abs(profile.estimated_pad.arousal - (-0.3)) < 0.01
    assert abs(profile.estimated_pad.dominance - 0.5) < 0.01


@pytest.mark.asyncio
async def test_compassionate_mode_triggers():
    """High confidence + negative pleasure should trigger COMPASSIONATE mode."""
    cfg = EmpathyConfig(compassion_threshold=0.6, min_interactions=2)
    engine = CognitiveEmpathyEngine(cfg)
    distressed = PADState(pleasure=-0.5, arousal=0.7, dominance=-0.2)
    for _ in range(10):
        await engine.update_profile("agent-B", distressed)
    result = await engine.assess("agent-B")
    assert result.mode == EmpathyMode.COMPASSIONATE
    assert result.recommended_response_tone == "supportive"
```

---

## Implementation Order (14 steps)

1. `EmpathyMode` enum
2. `AgentProfile` frozen dataclass
3. `EmpathyConfig` frozen dataclass with validators
4. `EmpathyResult` frozen dataclass
5. `EmpathyEngine` Protocol
6. `CognitiveEmpathyEngine.__init__` + `_prior`
7. `update_profile` — Bayesian posterior + accuracy tracking
8. `assess` — mode selection + tone mapping
9. `mirror` — weighted PAD blending
10. `get_profile` + `get_accuracy_history`
11. LRU eviction logic
12. Prometheus instrumentation
13. `NullEmpathyEngine`
14. `make_empathy_engine` factory + integration test

---

## Phase 21 Sub-phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 21.1 | EmotionCore | [#496](https://github.com/web3guru888/asi-build/issues/496) | 🟡 spec'd |
| 21.2 | MoodRegulator | [#497](https://github.com/web3guru888/asi-build/issues/497) | 🟡 spec'd |
| **21.3** | **EmpathyEngine** | **[#498](https://github.com/web3guru888/asi-build/issues/498)** | **🟡 spec'd** |
| 21.4 | SocialCognition | — | ⬜ queued |
| 21.5 | EmotionalOrchestrator | — | ⬜ queued |
