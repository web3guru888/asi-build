# Phase 23.3 — UtilityComputer

> **Status**: ✅ Spec Complete
> **Tracks**: Phase 23 — Decision Intelligence & Uncertainty Management
> **Depends on**: UncertaintyQuantifier (23.1), RiskAssessor (23.2)
> **Feeds into**: DecisionTreeSolver (23.4), DecisionOrchestrator (23.5)

---

## Overview

The **UtilityComputer** translates raw outcomes and risk profiles into utility values that reflect the agent's preferences, risk attitudes, and cognitive biases. It supports multiple utility frameworks — from classical Expected Utility Theory to behavioural Prospect Theory — and learns preference models from feedback.

Key theoretical foundations:
- **Expected Utility Theory** — von Neumann & Morgenstern (1944)
- **Prospect Theory** — Kahneman & Tversky (1979); cumulative prospect theory (1992)
- **Multi-Attribute Utility Theory (MAUT)** — Keeney & Raiffa (1976)
- **Maximin / Minimax Regret** — Wald (1950); Savage (1951)
- **Preference learning** — Fürnkranz & Hüllermeier (2010)

---

## Enums

### `UtilityFramework`

```python
class UtilityFramework(str, Enum):
    """Decision-theoretic framework for utility computation."""
    EXPECTED_UTILITY = "expected_utility"    # EU = Σ p_i · u(x_i)
    PROSPECT_THEORY = "prospect_theory"      # PT = Σ w(p_i) · v(x_i)
    MAUT = "maut"                            # Multi-Attribute: U = Σ w_j · u_j(x_j)
    MAXIMIN = "maximin"                      # max_a min_s u(a, s) — pessimistic
    MINIMAX_REGRET = "minimax_regret"        # min_a max_s [max_a' u(a',s) - u(a,s)]
```

---

## Frozen Dataclasses

### `Alternative`

```python
@dataclass(frozen=True)
class Alternative:
    """A decision alternative with outcomes under states of nature."""
    id: str                                        # Unique identifier
    name: str                                      # Human-readable label
    outcomes: tuple[float, ...]                    # Payoff under each state
    probabilities: tuple[float, ...] | None = None # State probabilities (None → uniform)
    attributes: dict[str, float] = field(default_factory=dict)  # For MAUT
    risk_profile: RiskProfile | None = None        # From RiskAssessor (23.2)
    metadata: dict[str, Any] = field(default_factory=dict)
```

### `UtilityResult`

```python
@dataclass(frozen=True)
class UtilityResult:
    """Result of utility computation for a single alternative."""
    alternative_id: str
    utility: float                                 # Computed utility value
    framework: UtilityFramework                    # Which framework was used
    rank: int                                      # 1-based rank (1 = best)
    value_components: dict[str, float] = field(default_factory=dict)
    # e.g. {"gain_utility": 0.8, "loss_utility": -0.3, "weighted_prob": 0.65}
    confidence: float = 1.0                        # From uncertainty propagation
    timestamp: float = 0.0
```

### `PreferenceModel`

```python
@dataclass(frozen=True)
class PreferenceModel:
    """Learned preference parameters."""
    # Prospect Theory parameters
    alpha: float = 0.88                            # Gain curvature (Tversky & Kahneman)
    beta: float = 0.88                             # Loss curvature
    lambda_: float = 2.25                          # Loss aversion coefficient
    gamma: float = 0.61                            # Probability weighting (gains)
    delta: float = 0.69                            # Probability weighting (losses)
    reference_point: float = 0.0                   # Adaptation level
    # MAUT weights
    attribute_weights: dict[str, float] = field(default_factory=dict)
    # Learning metadata
    num_feedback_samples: int = 0
    last_updated: float = 0.0
```

### `UtilityConfig`

```python
@dataclass(frozen=True)
class UtilityConfig:
    """Configuration for UtilityComputer."""
    default_framework: UtilityFramework = UtilityFramework.PROSPECT_THEORY
    initial_preferences: PreferenceModel | None = None
    learning_rate: float = 0.01                    # SGD step size for preference learning
    min_feedback_for_update: int = 10              # Minimum pairwise comparisons
    reference_point_method: str = "running_mean"   # running_mean | status_quo | aspiration
    normalize_utilities: bool = True               # Scale to [0, 1]
```

---

## Protocol

```python
@runtime_checkable
class UtilityComputer(Protocol):
    """Computes utility values for decision alternatives."""

    async def compute(
        self,
        alternative: Alternative,
        *,
        framework: UtilityFramework | None = None,
    ) -> UtilityResult:
        """Compute utility for a single alternative."""
        ...

    async def rank(
        self,
        alternatives: Sequence[Alternative],
        *,
        framework: UtilityFramework | None = None,
    ) -> tuple[UtilityResult, ...]:
        """Rank alternatives by utility (highest first)."""
        ...

    async def learn_preferences(
        self,
        preferred: Alternative,
        dispreferred: Alternative,
    ) -> PreferenceModel:
        """Update preference model from pairwise comparison feedback."""
        ...

    def get_preference_model(self) -> PreferenceModel:
        """Return current preference model parameters."""
        ...
```

---

## Implementation — `AdaptiveUtilityComputer`

```python
class AdaptiveUtilityComputer:
    """
    Production implementation of UtilityComputer.

    Framework dispatch:
      EXPECTED_UTILITY  → EU = Σ p_i · u(x_i), u(x) = x^α
      PROSPECT_THEORY   → PT = Σ w(p_i) · v(x_i)
      MAUT              → U = Σ w_j · u_j(x_j), normalised weights
      MAXIMIN           → max_a min_s u(a, s)
      MINIMAX_REGRET    → min_a max_s [max_a' u(a',s) - u(a,s)]

    Prospect Theory value function v(x):
      v(x) = x^α                  if x ≥ reference_point  (gains)
      v(x) = -λ · (-x)^β          if x < reference_point  (losses)

    Prelec probability weighting w(p):
      w(p) = exp(-(-ln p)^γ)      (gains: γ parameter)
      w(p) = exp(-(-ln p)^δ)      (losses: δ parameter)

    Properties of v(x):
      - Concave for gains (risk-averse)
      - Convex for losses (risk-seeking)
      - Steeper for losses than gains (loss aversion, λ ≈ 2.25)
      - Reference-dependent

    Preference learning:
      - Pairwise comparison: (preferred, dispreferred) → gradient
      - SGD on Bradley-Terry model: P(A ≻ B) = σ(U(A) - U(B))
      - Update α, β, λ, γ, δ, attribute_weights
    """

    def __init__(self, config: UtilityConfig | None = None) -> None:
        self._config = config or UtilityConfig()
        self._preferences = self._config.initial_preferences or PreferenceModel()
        self._feedback_buffer: list[tuple[Alternative, Alternative]] = []

    async def compute(
        self,
        alternative: Alternative,
        *,
        framework: UtilityFramework | None = None,
    ) -> UtilityResult:
        """
        Dispatch on framework:
          EXPECTED_UTILITY  → _compute_eu(alternative)
          PROSPECT_THEORY   → _compute_pt(alternative)
          MAUT              → _compute_maut(alternative)
          MAXIMIN           → _compute_maximin(alternative)
          MINIMAX_REGRET    → raise (needs full alternative set)
        """
        ...

    async def rank(
        self,
        alternatives: Sequence[Alternative],
        *,
        framework: UtilityFramework | None = None,
    ) -> tuple[UtilityResult, ...]:
        """
        1. Compute utility for each alternative
        2. For MINIMAX_REGRET: compute regret matrix first
        3. Sort descending by utility
        4. Assign rank (1-based)
        5. Optionally normalise to [0, 1]
        """
        ...

    async def learn_preferences(
        self,
        preferred: Alternative,
        dispreferred: Alternative,
    ) -> PreferenceModel:
        """
        Bradley-Terry SGD:
          1. Compute U(preferred), U(dispreferred)
          2. p = σ(U(pref) - U(dispref))
          3. loss = -log(p)
          4. ∂loss/∂params → update α, β, λ, γ, δ
          5. Clamp parameters to valid ranges
        """
        ...

    def get_preference_model(self) -> PreferenceModel:
        return self._preferences

    # --- Private methods ---

    def _value_function(self, x: float) -> float:
        """Prospect theory S-curve."""
        ref = self._preferences.reference_point
        if x >= ref:
            return (x - ref) ** self._preferences.alpha
        else:
            return -self._preferences.lambda_ * (ref - x) ** self._preferences.beta

    def _weight_function(self, p: float, *, gains: bool = True) -> float:
        """Prelec probability weighting."""
        if p <= 0: return 0.0
        if p >= 1: return 1.0
        param = self._preferences.gamma if gains else self._preferences.delta
        return math.exp(-((-math.log(p)) ** param))
```

---

## Null Implementation

```python
class NullUtilityComputer:
    """No-op for testing and DI wiring."""

    async def compute(self, alternative, *, framework=None):
        return UtilityResult(alternative_id=alternative.id, utility=0.0,
                             framework=UtilityFramework.EXPECTED_UTILITY, rank=1)

    async def rank(self, alternatives, *, framework=None):
        return tuple(
            UtilityResult(alternative_id=a.id, utility=0.0,
                          framework=UtilityFramework.EXPECTED_UTILITY, rank=i+1)
            for i, a in enumerate(alternatives)
        )

    async def learn_preferences(self, preferred, dispreferred):
        return PreferenceModel()

    def get_preference_model(self):
        return PreferenceModel()
```

---

## Factory

```python
def make_utility_computer(
    config: UtilityConfig | None = None,
    *,
    null: bool = False,
) -> UtilityComputer:
    if null:
        return NullUtilityComputer()
    return AdaptiveUtilityComputer(config)
```

---

## Data Flow — Prospect Theory S-Curve

```
    v(x)
     │
     │          ╱ gains: v(x) = x^α
     │        ╱   (concave, risk-averse)
     │      ╱
     │    ╱
     │  ╱
─────┼╱────────────────── x (outcome)
    ╱│  reference point
   ╱ │
  ╱  │    losses: v(x) = -λ(-x)^β
 ╱   │    (convex, risk-seeking)
╱    │    (steeper — loss aversion λ≈2.25)
     │

    w(p)                  Prelec weighting
    1 ┤                    ╱
      │                  ╱
      │               ╱
      │            ╱    overweight small p
      │        . ╱      underweight large p
      │     ╱  .
      │  ╱  .
    0 ┤╱─.──────────── p
      0               1
```

### Full Computation Flow

```
    ┌──────────────────────────┐
    │  Alternative             │
    │  outcomes + probs        │
    └────────────┬─────────────┘
                 │
    ┌────────────▼─────────────┐
    │  Framework Dispatch       │
    │  ┌─────────────────────┐ │
    │  │ PROSPECT_THEORY:    │ │
    │  │  v(x) per outcome   │ │
    │  │  w(p) per prob      │ │
    │  │  PT = Σ w(p)·v(x)  │ │
    │  ├─────────────────────┤ │
    │  │ EXPECTED_UTILITY:   │ │
    │  │  EU = Σ p·u(x)     │ │
    │  ├─────────────────────┤ │
    │  │ MAUT:               │ │
    │  │  U = Σ wⱼ·uⱼ(xⱼ)  │ │
    │  └─────────┬───────────┘ │
    └────────────┼─────────────┘
                 │
    ┌────────────▼─────────────┐
    │  rank() → sort + assign  │
    │  normalise to [0, 1]     │
    └────────────┬─────────────┘
                 │
    ┌────────────▼─────────────┐
    │  tuple[UtilityResult]    │
    │  → DecisionTreeSolver    │
    │  → DecisionOrchestrator  │
    └──────────────────────────┘
```

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_utility_compute_total` | Counter | Total compute() calls |
| `asi_utility_compute_seconds` | Histogram | compute() latency |
| `asi_utility_framework_used` | Counter (label: framework) | Framework usage distribution |
| `asi_utility_preference_updates_total` | Counter | Preference learning updates |
| `asi_utility_loss_aversion_lambda` | Gauge | Current loss aversion coefficient |

### PromQL Examples

```promql
# Utility computation rate
rate(asi_utility_compute_total[5m])

# Most used framework
topk(1, rate(asi_utility_framework_used[1h]))

# Loss aversion drift
asi_utility_loss_aversion_lambda
```

### Grafana Alerts

```yaml
- alert: PreferenceDrift
  expr: abs(delta(asi_utility_loss_aversion_lambda[1h])) > 0.5
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "Loss aversion λ shifted by >0.5 in 1h — rapid preference change"

- alert: UtilityComputeSlow
  expr: histogram_quantile(0.99, asi_utility_compute_seconds_bucket) > 2.0
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "Utility computation p99 latency exceeds 2s"

- alert: InsufficientPreferenceFeedback
  expr: rate(asi_utility_preference_updates_total[1h]) == 0
  for: 2h
  labels: { severity: info }
  annotations:
    summary: "No preference feedback in 2h — model may be stale"
```

---

## Integration Notes

| Component | Direction | Contract |
|-----------|-----------|----------|
| **UncertaintyQuantifier (23.1)** | ← upstream | Uncertainty envelope modulates probability weighting |
| **RiskAssessor (23.2)** | ← upstream | `RiskProfile` feeds Alternative.risk_profile |
| **DecisionTreeSolver (23.4)** | → downstream | Utility values assigned to terminal nodes |
| **DecisionOrchestrator (23.5)** | → downstream | Ranked alternatives feed decision pipeline |
| **AffectiveOrchestrator (21.5)** | ← upstream | Emotional state modulates reference point |
| **CreativeOrchestrator (22.5)** | ← upstream | Novel alternatives added to rank set |

---

## Mypy Strict Compliance

| Check | Status |
|-------|--------|
| `--strict` | ✅ Required |
| `--warn-return-any` | ✅ |
| `--disallow-untyped-defs` | ✅ |
| `@runtime_checkable` Protocol | ✅ |
| Frozen dataclasses only | ✅ |

---

## Test Targets (12)

| # | Test | Focus |
|---|------|-------|
| 1 | `test_compute_returns_frozen_result` | Immutability + required fields |
| 2 | `test_prospect_theory_loss_aversion` | v(loss) steeper than v(gain) for |x| equal |
| 3 | `test_prospect_theory_concave_gains` | v(x) concave for x > ref |
| 4 | `test_prospect_theory_convex_losses` | v(x) convex for x < ref |
| 5 | `test_prelec_overweights_small_probs` | w(0.05) > 0.05 |
| 6 | `test_prelec_underweights_large_probs` | w(0.95) < 0.95 |
| 7 | `test_expected_utility_linear_in_probs` | EU = Σ p·u(x) |
| 8 | `test_maut_weights_sum_to_one` | Attribute weights normalised |
| 9 | `test_maximin_selects_pessimistic` | Picks alternative with best worst-case |
| 10 | `test_rank_ordering_consistent` | rank[i].utility ≥ rank[i+1].utility |
| 11 | `test_learn_preferences_updates_lambda` | λ changes after pairwise feedback |
| 12 | `test_null_utility_computer_passthrough` | NullUtilityComputer returns defaults |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_prospect_theory_loss_aversion():
    """Loss of $100 should hurt more than gain of $100 feels good."""
    uc = AdaptiveUtilityComputer()
    gain_alt = Alternative(id="gain", name="Gain", outcomes=(100.0,), probabilities=(1.0,))
    loss_alt = Alternative(id="loss", name="Loss", outcomes=(-100.0,), probabilities=(1.0,))
    gain_result = await uc.compute(gain_alt, framework=UtilityFramework.PROSPECT_THEORY)
    loss_result = await uc.compute(loss_alt, framework=UtilityFramework.PROSPECT_THEORY)
    assert abs(loss_result.utility) > abs(gain_result.utility)

@pytest.mark.asyncio
async def test_maximin_selects_pessimistic():
    """Maximin should select the alternative with the best worst-case outcome."""
    uc = AdaptiveUtilityComputer()
    safe = Alternative(id="safe", name="Safe", outcomes=(5.0, 4.0, 3.0))
    risky = Alternative(id="risky", name="Risky", outcomes=(10.0, 1.0, 0.5))
    results = await uc.rank([safe, risky], framework=UtilityFramework.MAXIMIN)
    assert results[0].alternative_id == "safe"  # min(safe)=3 > min(risky)=0.5
```

---

## Implementation Order (14 steps)

1. Create `src/asi_build/decision/utility/__init__.py`
2. Define `UtilityFramework` enum
3. Define `Alternative`, `UtilityResult`, `PreferenceModel`, `UtilityConfig` frozen dataclasses
4. Define `UtilityComputer` Protocol with `@runtime_checkable`
5. Implement `AdaptiveUtilityComputer.__init__` + state
6. Implement `_value_function()` — prospect theory S-curve
7. Implement `_weight_function()` — Prelec probability weighting
8. Implement `_compute_pt()`, `_compute_eu()`, `_compute_maut()`
9. Implement `_compute_maximin()`, `_compute_minimax_regret()`
10. Implement `compute()` — framework dispatch
11. Implement `rank()` — batch compute + sort + normalise
12. Implement `learn_preferences()` — Bradley-Terry SGD
13. Implement `NullUtilityComputer` + `make_utility_computer()` factory
14. Register Prometheus metrics + write 12 tests + verify mypy strict

---

## Phase 23 Sub-Phase Tracker

| Sub-Phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 23.1 | UncertaintyQuantifier | #529 | ✅ Spec |
| 23.2 | RiskAssessor | #530 | ✅ Spec |
| 23.3 | UtilityComputer | #531 | ✅ Spec |
| 23.4 | DecisionTreeSolver | #532 | ⬜ Pending |
| 23.5 | DecisionOrchestrator | #533 | ⬜ Pending |
