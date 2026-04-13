# Phase 23.2 — RiskAssessor

> **Status**: ✅ Spec Complete
> **Tracks**: Phase 23 — Decision Intelligence & Uncertainty Management
> **Depends on**: UncertaintyQuantifier (23.1), ReasoningOrchestrator (20.5)
> **Feeds into**: UtilityComputer (23.3), DecisionOrchestrator (23.5)

---

## Overview

The **RiskAssessor** evaluates risk profiles for candidate decisions under uncertainty. It combines Monte Carlo simulation, Value-at-Risk (VaR), Conditional VaR (CVaR / Expected Shortfall), Pareto frontier analysis, and tail probability estimation to give the Decision Intelligence pipeline a principled risk quantification layer.

Key theoretical foundations:
- **Value-at-Risk / CVaR** — Rockafellar & Uryasev (2000), coherent risk measures
- **Monte Carlo scenario analysis** — Metropolis & Ulam (1949); modern variance reduction (importance sampling, antithetic variates)
- **Pareto optimality** — multi-objective dominance for risk-reward trade-offs
- **Tail risk** — extreme value theory, Pickands–Balkema–de Haan theorem

---

## Enums

### `RiskCategory`

```python
class RiskCategory(str, Enum):
    """Risk severity classification."""
    NEGLIGIBLE = "negligible"    # VaR < 1% of portfolio
    LOW = "low"                  # VaR ∈ [1%, 5%)
    MODERATE = "moderate"        # VaR ∈ [5%, 15%)
    HIGH = "high"                # VaR ∈ [15%, 30%)
    CRITICAL = "critical"        # VaR ≥ 30%
```

### `ScenarioType`

```python
class ScenarioType(str, Enum):
    """Type of scenario for analysis."""
    BASE_CASE = "base_case"              # Expected/median outcome
    BEST_CASE = "best_case"              # Optimistic tail (e.g. 5th percentile loss)
    WORST_CASE = "worst_case"            # Pessimistic tail (e.g. 95th percentile)
    STRESS_TEST = "stress_test"          # Extreme adverse conditions
    BLACK_SWAN = "black_swan"            # Beyond historical distribution
```

---

## Frozen Dataclasses

### `RiskProfile`

```python
@dataclass(frozen=True)
class RiskProfile:
    """Complete risk assessment for a single alternative."""
    alternative_id: str                        # Unique identifier for the alternative
    risk_category: RiskCategory                # Classified severity
    var_95: float                              # Value-at-Risk at 95% confidence
    var_99: float                              # Value-at-Risk at 99% confidence
    cvar_95: float                             # Conditional VaR (Expected Shortfall) at 95%
    cvar_99: float                             # Conditional VaR (Expected Shortfall) at 99%
    expected_return: float                     # Mean return across simulations
    volatility: float                          # Std dev of returns
    sharpe_ratio: float                        # (expected_return - risk_free) / volatility
    tail_probability: float                    # P(loss > threshold)
    max_drawdown: float                        # Maximum peak-to-trough loss
    uncertainty: UncertaintyEstimate | None     # From UncertaintyQuantifier (23.1)
    scenarios: tuple[Scenario, ...] = ()       # Detailed scenario analyses
    timestamp: float = 0.0                     # time.monotonic()
    metadata: dict[str, Any] = field(default_factory=dict)
```

### `Scenario`

```python
@dataclass(frozen=True)
class Scenario:
    """A single scenario analysis result."""
    scenario_type: ScenarioType
    description: str                           # Human-readable scenario narrative
    probability: float                         # Estimated probability of this scenario
    expected_outcome: float                    # Expected value under this scenario
    confidence_interval: tuple[float, float]   # (lower, upper)
    key_drivers: tuple[str, ...]               # Factors driving this outcome
    mitigation_options: tuple[str, ...] = ()   # Possible risk mitigations
```

### `RiskAssessorConfig`

```python
@dataclass(frozen=True)
class RiskAssessorConfig:
    """Configuration for RiskAssessor."""
    num_simulations: int = 10_000              # Monte Carlo sample count
    confidence_levels: tuple[float, ...] = (0.95, 0.99)
    risk_free_rate: float = 0.02               # Annual risk-free rate for Sharpe
    tail_threshold: float = -0.10              # Loss threshold for tail prob
    max_acceptable_var_95: float = 0.15        # Gate for is_acceptable()
    max_acceptable_cvar_95: float = 0.20       # Gate for is_acceptable()
    variance_reduction: str = "antithetic"     # antithetic | importance | none
    seed: int | None = None                    # RNG seed for reproducibility
    pareto_objectives: tuple[str, ...] = ("expected_return", "cvar_95")
```

---

## Protocol

```python
@runtime_checkable
class RiskAssessor(Protocol):
    """Assesses risk profiles for decision alternatives."""

    async def assess(
        self,
        returns: Sequence[float],
        *,
        alternative_id: str = "default",
        uncertainty: UncertaintyEstimate | None = None,
    ) -> RiskProfile:
        """Run Monte Carlo simulation and return full risk profile."""
        ...

    async def scenario_analysis(
        self,
        returns: Sequence[float],
        scenarios: Sequence[ScenarioType],
    ) -> tuple[Scenario, ...]:
        """Generate scenario analyses for given types."""
        ...

    async def pareto_frontier(
        self,
        profiles: Sequence[RiskProfile],
    ) -> tuple[RiskProfile, ...]:
        """Identify Pareto-optimal alternatives (non-dominated set)."""
        ...

    def is_acceptable(self, profile: RiskProfile) -> bool:
        """True if VaR₉₅ and CVaR₉₅ within acceptable limits."""
        ...
```

---

## Implementation — `MonteCarloRiskAssessor`

```python
class MonteCarloRiskAssessor:
    """
    Production implementation of RiskAssessor.

    Monte Carlo pipeline:
      1. Sample N returns from empirical distribution (with variance reduction)
      2. Sort samples → compute VaR as quantile
      3. CVaR = mean of samples beyond VaR threshold
      4. Sharpe = (μ - r_f) / σ
      5. Tail probability = count(samples < threshold) / N
      6. Max drawdown from cumulative return path
      7. Classify RiskCategory from VaR₉₅

    Pareto frontier:
      - For each pair of profiles, check dominance on configured objectives
      - Profile A dominates B iff A ≤ B on all objectives and A < B on at least one
      - Return non-dominated set

    Variance reduction:
      - Antithetic variates: for each sample z, also use -z → halves variance
      - Importance sampling: tilt distribution toward tail → re-weight
    """

    def __init__(self, config: RiskAssessorConfig | None = None) -> None:
        self._config = config or RiskAssessorConfig()
        self._rng = np.random.default_rng(self._config.seed)

    async def assess(
        self,
        returns: Sequence[float],
        *,
        alternative_id: str = "default",
        uncertainty: UncertaintyEstimate | None = None,
    ) -> RiskProfile:
        """
        1. Generate Monte Carlo samples (with variance reduction)
        2. Compute VaR₉₅, VaR₉₉ as np.percentile on losses
        3. CVaR₉₅ = mean(losses[losses ≥ VaR₉₅])
        4. Sharpe = (mean(returns) - risk_free_rate) / std(returns)
        5. Tail prob = sum(returns < tail_threshold) / N
        6. Max drawdown from np.maximum.accumulate
        7. Classify via _categorize(var_95)
        8. Return frozen RiskProfile
        """
        ...

    async def scenario_analysis(
        self,
        returns: Sequence[float],
        scenarios: Sequence[ScenarioType],
    ) -> tuple[Scenario, ...]:
        """
        For each ScenarioType:
          BASE_CASE   → median ± 1σ
          BEST_CASE   → 5th percentile of losses (95th of returns)
          WORST_CASE  → 95th percentile of losses
          STRESS_TEST → returns under 3σ adverse shift
          BLACK_SWAN  → EVT: fit GPD to tail, extrapolate
        """
        ...

    async def pareto_frontier(
        self,
        profiles: Sequence[RiskProfile],
    ) -> tuple[RiskProfile, ...]:
        """
        O(n²) dominance check on configured pareto_objectives.
        Returns non-dominated profiles sorted by first objective.
        """
        ...

    def is_acceptable(self, profile: RiskProfile) -> bool:
        return (
            profile.var_95 <= self._config.max_acceptable_var_95
            and profile.cvar_95 <= self._config.max_acceptable_cvar_95
        )

    def _categorize(self, var_95: float) -> RiskCategory:
        if var_95 < 0.01: return RiskCategory.NEGLIGIBLE
        if var_95 < 0.05: return RiskCategory.LOW
        if var_95 < 0.15: return RiskCategory.MODERATE
        if var_95 < 0.30: return RiskCategory.HIGH
        return RiskCategory.CRITICAL
```

---

## Null Implementation

```python
class NullRiskAssessor:
    """No-op for testing and DI wiring."""

    async def assess(self, returns, *, alternative_id="default", uncertainty=None):
        return RiskProfile(
            alternative_id=alternative_id, risk_category=RiskCategory.NEGLIGIBLE,
            var_95=0.0, var_99=0.0, cvar_95=0.0, cvar_99=0.0,
            expected_return=0.0, volatility=0.0, sharpe_ratio=0.0,
            tail_probability=0.0, max_drawdown=0.0, uncertainty=None,
        )

    async def scenario_analysis(self, returns, scenarios):
        return ()

    async def pareto_frontier(self, profiles):
        return tuple(profiles)

    def is_acceptable(self, profile):
        return True
```

---

## Factory

```python
def make_risk_assessor(
    config: RiskAssessorConfig | None = None,
    *,
    null: bool = False,
) -> RiskAssessor:
    if null:
        return NullRiskAssessor()
    return MonteCarloRiskAssessor(config)
```

---

## Data Flow

```
    ┌────────────────────────────┐
    │  Historical / Predicted    │
    │  Return Distribution       │
    └─────────────┬──────────────┘
                  │
    ┌─────────────▼──────────────┐
    │   Monte Carlo Simulation   │
    │  ┌──────────────────────┐  │
    │  │ Variance Reduction   │  │
    │  │ (antithetic/import.) │  │
    │  └──────────┬───────────┘  │
    │             │ N samples    │
    │  ┌──────────▼───────────┐  │
    │  │  Sort → Quantiles    │  │
    │  │  VaR₉₅ = Q(0.95)    │  │
    │  │  VaR₉₉ = Q(0.99)    │  │
    │  └──────────┬───────────┘  │
    │             │              │
    │  ┌──────────▼───────────┐  │
    │  │  CVaR = E[X|X>VaR]  │  │
    │  │  Sharpe = (μ-rf)/σ   │  │
    │  │  Tail P, Max DD      │  │
    │  └──────────┬───────────┘  │
    └─────────────┼──────────────┘
                  │
    ┌─────────────▼──────────────┐
    │       RiskProfile          │
    │  ┌───────────────────────┐ │
    │  │ risk_category: HIGH   │ │
    │  │ var_95: 0.18          │ │
    │  │ cvar_95: 0.23         │ │
    │  │ sharpe: 0.85          │ │
    │  └───────────────────────┘ │
    └─────────────┬──────────────┘
                  │
    ┌─────────────▼──────────────┐
    │  Pareto Frontier Analysis  │
    │  ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │
    │    Expected Return (↑)     │
    │    │  ★ A                  │
    │    │    ★ B                │
    │    │      ·C (dominated)   │
    │    │        ★ D            │
    │    └──────────── CVaR (→)  │
    │  └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │
    │  Non-dominated: {A, B, D}  │
    └────────────────────────────┘
```

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_risk_assess_total` | Counter | Total assess() calls |
| `asi_risk_assess_seconds` | Histogram | assess() latency |
| `asi_risk_var95` | Histogram | Distribution of VaR₉₅ values |
| `asi_risk_category` | Gauge (label: category) | Count per RiskCategory |
| `asi_risk_pareto_size` | Histogram | Size of Pareto frontier |

### PromQL Examples

```promql
# Assessment rate
rate(asi_risk_assess_total[5m])

# Average VaR₉₅
histogram_quantile(0.50, asi_risk_var95_bucket)

# Critical risk count
asi_risk_category{category="critical"}
```

### Grafana Alerts

```yaml
- alert: HighRiskAlternativeSelected
  expr: asi_risk_category{category="critical"} > 0
  for: 1m
  labels: { severity: critical }
  annotations:
    summary: "A critical-risk alternative is active"

- alert: RiskAssessmentSlow
  expr: histogram_quantile(0.99, asi_risk_assess_seconds_bucket) > 5.0
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "Risk assessment p99 latency exceeds 5s"

- alert: ParetoFrontierCollapse
  expr: histogram_quantile(0.50, asi_risk_pareto_size_bucket) < 2
  for: 10m
  labels: { severity: info }
  annotations:
    summary: "Pareto frontier has fewer than 2 alternatives — limited choice"
```

---

## Integration Notes

| Component | Direction | Contract |
|-----------|-----------|----------|
| **UncertaintyQuantifier (23.1)** | ← upstream | `UncertaintyEstimate` enriches `RiskProfile.uncertainty` |
| **UtilityComputer (23.3)** | → downstream | `RiskProfile` feeds utility risk-adjustment |
| **DecisionTreeSolver (23.4)** | → downstream | VaR/CVaR as terminal node payoff bounds |
| **DecisionOrchestrator (23.5)** | → downstream | `is_acceptable()` gate in pipeline |
| **ReasoningOrchestrator (20.5)** | ← upstream | Causal reasoning informs scenario drivers |
| **WorldModel (13.1)** | ← upstream | World state predictions → return distribution |

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
| 1 | `test_assess_returns_frozen_profile` | Immutability + required fields |
| 2 | `test_var95_less_than_var99` | VaR monotonicity in confidence level |
| 3 | `test_cvar_geq_var` | CVaR ≥ VaR (coherent risk measure) |
| 4 | `test_sharpe_ratio_formula` | (μ - r_f) / σ matches manual calc |
| 5 | `test_tail_probability_bounds` | 0 ≤ tail_probability ≤ 1 |
| 6 | `test_risk_category_classification` | Boundary values map correctly |
| 7 | `test_scenario_base_case_near_median` | Base case ≈ median return |
| 8 | `test_scenario_stress_test_worse_than_worst` | Stress < worst case expected |
| 9 | `test_pareto_frontier_nondominated` | No profile in frontier dominates another |
| 10 | `test_pareto_removes_dominated` | Dominated profiles excluded |
| 11 | `test_is_acceptable_threshold` | True iff both VaR₉₅ and CVaR₉₅ within limits |
| 12 | `test_null_risk_assessor_passthrough` | NullRiskAssessor returns defaults |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_cvar_geq_var():
    """CVaR (Expected Shortfall) must be ≥ VaR — coherent risk measure property."""
    ra = MonteCarloRiskAssessor(RiskAssessorConfig(num_simulations=50_000, seed=42))
    returns = list(np.random.default_rng(42).normal(0.05, 0.15, 1000))
    profile = await ra.assess(returns, alternative_id="test")
    assert profile.cvar_95 >= profile.var_95
    assert profile.cvar_99 >= profile.var_99

@pytest.mark.asyncio
async def test_pareto_frontier_nondominated():
    """No profile in the Pareto frontier should dominate any other."""
    ra = MonteCarloRiskAssessor()
    profiles = [
        RiskProfile(alternative_id="A", risk_category=RiskCategory.LOW,
                    var_95=0.03, var_99=0.05, cvar_95=0.04, cvar_99=0.06,
                    expected_return=0.10, volatility=0.08, sharpe_ratio=1.0,
                    tail_probability=0.01, max_drawdown=0.05, uncertainty=None),
        RiskProfile(alternative_id="B", risk_category=RiskCategory.MODERATE,
                    var_95=0.08, var_99=0.12, cvar_95=0.10, cvar_99=0.15,
                    expected_return=0.20, volatility=0.15, sharpe_ratio=1.2,
                    tail_probability=0.03, max_drawdown=0.10, uncertainty=None),
    ]
    frontier = await ra.pareto_frontier(profiles)
    # Both should be on frontier (neither dominates the other)
    assert len(frontier) == 2
```

---

## Implementation Order (14 steps)

1. Create `src/asi_build/decision/risk/__init__.py`
2. Define `RiskCategory` and `ScenarioType` enums
3. Define `RiskProfile`, `Scenario`, `RiskAssessorConfig` frozen dataclasses
4. Define `RiskAssessor` Protocol with `@runtime_checkable`
5. Implement `MonteCarloRiskAssessor.__init__` + RNG setup
6. Implement `_generate_samples()` with variance reduction (antithetic/importance)
7. Implement `assess()` — VaR/CVaR/Sharpe/tail prob/max drawdown/categorize
8. Implement `scenario_analysis()` — per-ScenarioType dispatch
9. Implement `pareto_frontier()` — O(n²) dominance check
10. Implement `is_acceptable()` + `_categorize()`
11. Implement `NullRiskAssessor`
12. Implement `make_risk_assessor()` factory
13. Register Prometheus metrics + instrument all methods
14. Write 12 tests — run `pytest -x` — verify mypy strict

---

## Phase 23 Sub-Phase Tracker

| Sub-Phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 23.1 | UncertaintyQuantifier | #529 | ✅ Spec |
| 23.2 | RiskAssessor | #530 | ✅ Spec |
| 23.3 | UtilityComputer | #531 | ⬜ Pending |
| 23.4 | DecisionTreeSolver | #532 | ⬜ Pending |
| 23.5 | DecisionOrchestrator | #533 | ⬜ Pending |
