# Phase 23.1 — UncertaintyQuantifier

> **Status**: ✅ Spec Complete
> **Tracks**: Phase 23 — Decision Intelligence & Uncertainty Management
> **Depends on**: Phase 20 (Reasoning), Phase 22 (Creative Intelligence)
> **Feeds into**: RiskAssessor (23.2), DecisionOrchestrator (23.5)

---

## Overview

The **UncertaintyQuantifier** decomposes, estimates, and calibrates uncertainty across all cognitive sub-systems. Every downstream decision component (risk assessment, utility computation, tree search) requires well-calibrated confidence intervals rather than point estimates. This module provides the epistemic foundation for the entire Decision Intelligence pipeline.

Key theoretical foundations:
- **Bayesian uncertainty decomposition** — epistemic vs. aleatoric (Der Kiureghian & Ditlevsen, 2009)
- **Ensemble disagreement** — mutual information across model ensemble (Lakshminarayanan et al., 2017)
- **Calibration theory** — Platt scaling, isotonic regression, temperature scaling, beta calibration (Guo et al., 2017; Kull et al., 2017)

---

## Enums

### `UncertaintyType`

```python
class UncertaintyType(str, Enum):
    """Classification of uncertainty source."""
    EPISTEMIC = "epistemic"      # Reducible — lack of knowledge / data
    ALEATORIC = "aleatoric"      # Irreducible — inherent randomness
    MIXED = "mixed"              # Combined epistemic + aleatoric
```

### `CalibrationMethod`

```python
class CalibrationMethod(str, Enum):
    """Post-hoc calibration technique."""
    PLATT_SCALING = "platt_scaling"                # Logistic regression on logits
    ISOTONIC_REGRESSION = "isotonic_regression"    # Non-parametric monotonic fit
    TEMPERATURE_SCALING = "temperature_scaling"    # Single scalar T on logits
    BETA_CALIBRATION = "beta_calibration"          # Beta distribution fit (Kull 2017)
```

---

## Frozen Dataclasses

### `UncertaintyEstimate`

```python
@dataclass(frozen=True)
class UncertaintyEstimate:
    """Result of uncertainty quantification for a single prediction."""
    point_estimate: float                          # Best-guess value
    confidence_interval: tuple[float, float]       # (lower, upper) at configured level
    confidence_level: float                        # e.g. 0.95
    uncertainty_type: UncertaintyType              # EPISTEMIC / ALEATORIC / MIXED
    epistemic_component: float                     # Variance from model disagreement
    aleatoric_component: float                     # Variance from data noise
    mutual_information: float                      # MI across ensemble members
    entropy: float                                 # Predictive entropy H[y|x]
    calibration_error: float                       # ECE after calibration
    timestamp: float                               # time.monotonic()
    metadata: dict[str, Any] = field(default_factory=dict)
```

### `EnsembleDisagreement`

```python
@dataclass(frozen=True)
class EnsembleDisagreement:
    """Statistics from ensemble member predictions."""
    member_predictions: tuple[float, ...]          # Individual predictions
    mean: float                                    # Ensemble mean
    variance: float                                # Inter-member variance
    mutual_information: float                      # I[y; θ | x, D]
    predictive_entropy: float                      # H[y | x, D]
    conditional_entropy: float                     # E_θ[H[y | x, θ]]
    member_count: int                              # Number of ensemble members
```

### `QuantifierConfig`

```python
@dataclass(frozen=True)
class QuantifierConfig:
    """Configuration for UncertaintyQuantifier."""
    ensemble_size: int = 10                        # Number of ensemble members
    confidence_level: float = 0.95                 # Default CI level
    calibration_method: CalibrationMethod = CalibrationMethod.TEMPERATURE_SCALING
    recalibration_interval_s: float = 300.0        # Re-calibrate every 5 min
    min_samples_for_calibration: int = 100         # Minimum calibration dataset size
    ece_bins: int = 15                             # Bins for ECE computation
    decomposition_method: str = "mutual_information"  # epistemic/aleatoric split
    max_calibration_error: float = 0.05            # Threshold for is_calibrated()
```

---

## Protocol

```python
@runtime_checkable
class UncertaintyQuantifier(Protocol):
    """Quantifies and calibrates prediction uncertainty."""

    async def quantify(
        self,
        predictions: Sequence[float],
        *,
        context: dict[str, Any] | None = None,
    ) -> UncertaintyEstimate:
        """Produce a calibrated uncertainty estimate from ensemble predictions."""
        ...

    async def calibrate(
        self,
        predictions: Sequence[float],
        ground_truth: Sequence[float],
        *,
        method: CalibrationMethod | None = None,
    ) -> float:
        """Calibrate model outputs. Returns post-calibration ECE."""
        ...

    async def decompose(
        self,
        predictions: Sequence[float],
    ) -> EnsembleDisagreement:
        """Decompose total uncertainty into epistemic and aleatoric components."""
        ...

    def is_calibrated(self) -> bool:
        """True if current calibration error < max_calibration_error."""
        ...
```

---

## Implementation — `BayesianUncertaintyQuantifier`

```python
class BayesianUncertaintyQuantifier:
    """
    Production implementation of UncertaintyQuantifier.

    Uncertainty decomposition via ensemble disagreement:
      - Predictive entropy:   H[y|x,D] = -Σ p̄(y) log p̄(y)
      - Conditional entropy:  E_θ[H[y|x,θ]] = -(1/M) Σ_m Σ p_m(y) log p_m(y)
      - Mutual information:   I[y;θ|x,D] = H[y|x,D] - E_θ[H[y|x,θ]]  (epistemic)
      - Aleatoric component:  E_θ[H[y|x,θ]]  (conditional entropy)

    Calibration pipeline:
      1. Collect (prediction, ground_truth) pairs into calibration buffer
      2. When buffer >= min_samples_for_calibration, fit calibrator
      3. Platt:       σ(a·z + b)  — logistic regression
      4. Temperature: σ(z / T)    — single scalar optimised on NLL
      5. Isotonic:    non-parametric monotonic mapping
      6. Beta:        1 / (1 + 1/(e^c · p^a / (1-p)^b))
      7. Recompute ECE after fit → update is_calibrated flag

    Recalibration loop:
      - Background asyncio.Task every recalibration_interval_s
      - Re-fits calibrator if new samples available
      - Emits asi_uncertainty_recalibration_total counter
    """

    def __init__(self, config: QuantifierConfig | None = None) -> None:
        self._config = config or QuantifierConfig()
        self._calibrator: _Calibrator | None = None
        self._calibration_buffer: list[tuple[float, float]] = []
        self._ece: float = 1.0  # Pre-calibration: worst case
        self._lock = asyncio.Lock()
        self._recalibration_task: asyncio.Task[None] | None = None

    # --- Protocol methods ---

    async def quantify(
        self,
        predictions: Sequence[float],
        *,
        context: dict[str, Any] | None = None,
    ) -> UncertaintyEstimate:
        """
        1. Compute ensemble disagreement via decompose()
        2. Apply calibration map if available
        3. Build confidence interval from variance + confidence_level
        4. Classify UncertaintyType from MI / conditional entropy ratio
        5. Return frozen UncertaintyEstimate
        """
        ...

    async def calibrate(
        self,
        predictions: Sequence[float],
        ground_truth: Sequence[float],
        *,
        method: CalibrationMethod | None = None,
    ) -> float:
        """
        Append to _calibration_buffer, fit calibrator, return ECE.
        Dispatches on CalibrationMethod:
          PLATT_SCALING         → _fit_platt(z, y)
          ISOTONIC_REGRESSION   → _fit_isotonic(z, y)
          TEMPERATURE_SCALING   → _fit_temperature(z, y)
          BETA_CALIBRATION      → _fit_beta(z, y)
        """
        ...

    async def decompose(
        self,
        predictions: Sequence[float],
    ) -> EnsembleDisagreement:
        """
        Compute ensemble statistics:
          mean = Σ p_m / M
          variance = Σ (p_m - mean)² / M
          predictive_entropy = -Σ p̄ log p̄
          conditional_entropy = -(1/M) Σ_m Σ p_m log p_m
          mutual_information = predictive_entropy - conditional_entropy
        """
        ...

    def is_calibrated(self) -> bool:
        return self._ece < self._config.max_calibration_error

    # --- Background recalibration ---

    async def start(self) -> None:
        self._recalibration_task = asyncio.create_task(self._recalibration_loop())

    async def stop(self) -> None:
        if self._recalibration_task:
            self._recalibration_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._recalibration_task

    async def _recalibration_loop(self) -> None:
        while True:
            await asyncio.sleep(self._config.recalibration_interval_s)
            async with self._lock:
                if len(self._calibration_buffer) >= self._config.min_samples_for_calibration:
                    await self._refit()
```

---

## Null Implementation

```python
class NullUncertaintyQuantifier:
    """No-op for testing and DI wiring."""

    async def quantify(self, predictions, *, context=None):
        return UncertaintyEstimate(
            point_estimate=0.0, confidence_interval=(0.0, 0.0),
            confidence_level=0.95, uncertainty_type=UncertaintyType.MIXED,
            epistemic_component=0.0, aleatoric_component=0.0,
            mutual_information=0.0, entropy=0.0,
            calibration_error=0.0, timestamp=0.0,
        )

    async def calibrate(self, predictions, ground_truth, *, method=None):
        return 0.0

    async def decompose(self, predictions):
        return EnsembleDisagreement(
            member_predictions=(), mean=0.0, variance=0.0,
            mutual_information=0.0, predictive_entropy=0.0,
            conditional_entropy=0.0, member_count=0,
        )

    def is_calibrated(self):
        return True
```

---

## Factory

```python
def make_uncertainty_quantifier(
    config: QuantifierConfig | None = None,
    *,
    null: bool = False,
) -> UncertaintyQuantifier:
    if null:
        return NullUncertaintyQuantifier()
    return BayesianUncertaintyQuantifier(config)
```

---

## Data Flow

```
                    ┌──────────────────────────────┐
                    │     Ensemble Predictions      │
                    │   [p₁, p₂, ..., p_M]         │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │        decompose()            │
                    │  ┌─────────┐ ┌─────────────┐ │
                    │  │ mean/var│ │ MI = H - E_H │ │
                    │  └────┬────┘ └──────┬──────┘ │
                    │       │  epistemic  │aleator. │
                    └───────┼─────────────┼────────┘
                            │             │
                    ┌───────▼─────────────▼────────┐
                    │         quantify()            │
                    │  ┌────────────────────────┐   │
                    │  │ calibrate(predictions) │   │
                    │  │ → apply Platt/Temp/... │   │
                    │  └───────────┬────────────┘   │
                    │              │                 │
                    │  confidence_interval(μ, σ²)   │
                    │  classify(UncertaintyType)     │
                    └──────────────┬────────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     UncertaintyEstimate       │
                    │  → RiskAssessor (23.2)        │
                    │  → UtilityComputer (23.3)     │
                    │  → DecisionOrchestrator (23.5)│
                    └──────────────────────────────┘

        Background:  _recalibration_loop()
                     every 300s → refit calibrator → update ECE
```

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_uncertainty_quantify_total` | Counter | Total quantify() calls |
| `asi_uncertainty_quantify_seconds` | Histogram | quantify() latency |
| `asi_uncertainty_ece` | Gauge | Current expected calibration error |
| `asi_uncertainty_recalibration_total` | Counter | Recalibration events |
| `asi_uncertainty_epistemic_ratio` | Histogram | epistemic / total uncertainty ratio |

### PromQL Examples

```promql
# Current calibration error
asi_uncertainty_ece

# Quantification rate
rate(asi_uncertainty_quantify_total[5m])

# High epistemic ratio (model needs more data)
histogram_quantile(0.95, asi_uncertainty_epistemic_ratio_bucket)
```

### Grafana Alerts

```yaml
- alert: UncertaintyCalibrationDrift
  expr: asi_uncertainty_ece > 0.10
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "Calibration error exceeds 10% — recalibration may be stale"

- alert: HighEpistemicUncertainty
  expr: histogram_quantile(0.95, asi_uncertainty_epistemic_ratio_bucket) > 0.8
  for: 10m
  labels: { severity: info }
  annotations:
    summary: "Epistemic uncertainty dominates — consider data augmentation"

- alert: RecalibrationStalled
  expr: rate(asi_uncertainty_recalibration_total[30m]) == 0
  for: 30m
  labels: { severity: warning }
  annotations:
    summary: "No recalibration events in 30 min — loop may be stuck"
```

---

## Integration Notes

| Component | Direction | Contract |
|-----------|-----------|----------|
| **RiskAssessor (23.2)** | → downstream | `UncertaintyEstimate` feeds `assess()` confidence intervals |
| **UtilityComputer (23.3)** | → downstream | Uncertainty envelope used in prospect theory weighting |
| **DecisionOrchestrator (23.5)** | → downstream | Orchestrator queries `is_calibrated()` gate before decide |
| **ReasoningOrchestrator (20.5)** | ← upstream | Reasoning output predictions become ensemble input |
| **CreativeOrchestrator (22.5)** | ← upstream | Novelty scores carry epistemic uncertainty |
| **WorldModel (13.1)** | ← upstream | WorldModel state predictions → ensemble members |

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
| 1 | `test_quantify_returns_frozen_estimate` | Immutability + required fields |
| 2 | `test_decompose_mutual_information_nonnegative` | MI ≥ 0 invariant |
| 3 | `test_decompose_entropy_decomposition` | H = MI + E_θ[H] identity |
| 4 | `test_calibrate_platt_reduces_ece` | ECE decreases after Platt scaling |
| 5 | `test_calibrate_temperature_single_scalar` | Only T parameter optimised |
| 6 | `test_calibrate_isotonic_monotonic` | Mapping is non-decreasing |
| 7 | `test_calibrate_beta_bounded` | Output in [0, 1] |
| 8 | `test_is_calibrated_threshold` | True iff ECE < max_calibration_error |
| 9 | `test_recalibration_loop_refits` | Background task triggers refit |
| 10 | `test_confidence_interval_coverage` | Empirical coverage ≈ confidence_level |
| 11 | `test_epistemic_dominant_when_few_members` | Few ensemble → high epistemic ratio |
| 12 | `test_null_quantifier_passthrough` | NullUncertaintyQuantifier returns defaults |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_decompose_entropy_decomposition():
    """H[y|x,D] = I[y;θ|x,D] + E_θ[H[y|x,θ]]."""
    q = BayesianUncertaintyQuantifier(QuantifierConfig(ensemble_size=5))
    preds = [0.1, 0.3, 0.5, 0.7, 0.9]
    d = await q.decompose(preds)
    assert abs(d.predictive_entropy - (d.mutual_information + d.conditional_entropy)) < 1e-9

@pytest.mark.asyncio
async def test_recalibration_loop_refits():
    """Background loop should refit when enough samples accumulate."""
    cfg = QuantifierConfig(recalibration_interval_s=0.1, min_samples_for_calibration=5)
    q = BayesianUncertaintyQuantifier(cfg)
    # Seed calibration buffer
    await q.calibrate([0.2, 0.4, 0.6, 0.8, 0.9], [0, 0, 1, 1, 1])
    ece_before = q._ece
    await q.start()
    await asyncio.sleep(0.3)  # Allow loop to run
    await q.stop()
    assert q._ece <= ece_before
```

---

## Implementation Order (14 steps)

1. Create `src/asi_build/decision/uncertainty/__init__.py`
2. Define `UncertaintyType` and `CalibrationMethod` enums
3. Define `UncertaintyEstimate`, `EnsembleDisagreement`, `QuantifierConfig` frozen dataclasses
4. Define `UncertaintyQuantifier` Protocol with `@runtime_checkable`
5. Implement `BayesianUncertaintyQuantifier.__init__` and state
6. Implement `decompose()` — ensemble statistics + MI decomposition
7. Implement `_fit_platt()`, `_fit_temperature()`, `_fit_isotonic()`, `_fit_beta()`
8. Implement `calibrate()` — dispatch on CalibrationMethod + ECE computation
9. Implement `quantify()` — decompose → calibrate → CI → classify → estimate
10. Implement `_recalibration_loop()` background task + start/stop lifecycle
11. Implement `NullUncertaintyQuantifier`
12. Implement `make_uncertainty_quantifier()` factory
13. Register Prometheus metrics + instrument all methods
14. Write 12 tests — run `pytest -x` — verify mypy strict

---

## Phase 23 Sub-Phase Tracker

| Sub-Phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 23.1 | UncertaintyQuantifier | #529 | ✅ Spec |
| 23.2 | RiskAssessor | #530 | ⬜ Pending |
| 23.3 | UtilityComputer | #531 | ⬜ Pending |
| 23.4 | DecisionTreeSolver | #532 | ⬜ Pending |
| 23.5 | DecisionOrchestrator | #533 | ⬜ Pending |
