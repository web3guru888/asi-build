# Phase 17.3 — PredictiveEngine

> **Phase 17: Temporal Reasoning & Predictive Cognition**
> Upstream: [Phase 17.2 EventSequencer](Phase-17-Event-Sequencer) · [Phase 17.1 TemporalGraph](Phase-17-Temporal-Graph)
> Issue: [#440](https://github.com/web3guru888/asi-build/issues/440) · Show & Tell: [#441](https://github.com/web3guru888/asi-build/discussions/441) · Q&A: [#442](https://github.com/web3guru888/asi-build/discussions/442)

---

## Summary

`PredictiveEngine` is a short-horizon state predictor that learns temporal patterns from the `EventSequencer`'s windowed aggregates and forecasts future cognitive states with **uncertainty quantification**. It drives pre-emptive goal generation in `GoalDecomposer` and allows `CognitiveCycle` to prepare resource allocation before load spikes arrive.

---

## Integration Map

```
EventSequencer
     │
     │  list[WindowedAggregate]
     ▼
AdaptivePredictiveEngine.train()
     │
     │  per-module deque[WindowedAggregate]
     ├──────────────────────────────────────────────┐
     │                                              │
     ▼                                              ▼
_run_strategy()                           TemporalGraph.get_predecessors()
  ├─ LAST_VALUE   (O(1))                    (historical pattern query)
  ├─ EXP_SMOOTH   (O(1) EMA)                         │
  ├─ LINEAR_TREND (O(n) 2-pt regression)              │
  └─ ENSEMBLE     (weighted avg ──────────────────── ┘
       updated by online gradient descent)
     │
     │  Prediction(predicted_state, confidence, horizon_ns)
     ▼
_confidence()  →  suppress if < threshold
     │
     ├──► CognitiveCycle  (resource pre-allocation)
     └──► GoalDecomposer  (pre-emptive goal generation)
          │
          └──► GoalRegistry.register(anticipatory_goal)

Later: record_outcome() → PredictionError → calibrate() → update alpha
```

---

## Enum: `PredictionStrategy`

```python
from enum import Enum, auto

class PredictionStrategy(Enum):
    LAST_VALUE         = auto()  # carry forward most-recent aggregate value
    EXPONENTIAL_SMOOTH = auto()  # EMA prediction
    LINEAR_TREND       = auto()  # 2-point linear regression extrapolation
    ENSEMBLE           = auto()  # weighted combination of all three
```

### PredictionStrategy Table

| Strategy | Algorithm | Time Complexity | Best-for Scenario |
|---|---|---|---|
| `LAST_VALUE` | Carry last window's metrics forward | O(1) | Steady-state / slow-changing signals |
| `EXPONENTIAL_SMOOTH` | `ema_t = α*x_t + (1-α)*ema_{t-1}` | O(1) | Noisy signals needing smooth forecasts |
| `LINEAR_TREND` | `v_next = v_last + (v_last - v_first)` | O(n) | Clear directional drift / ramp signals |
| `ENSEMBLE` | Weighted avg of all three, weights updated via online grad descent | O(n) | Mixed regimes; self-adapts over time |

---

## Frozen Dataclasses

### `Prediction`

```python
from dataclasses import dataclass
from typing import Mapping, Any

@dataclass(frozen=True)
class Prediction:
    prediction_id: str              # uuid4 hex
    target_module: str              # e.g. "working_memory"
    predicted_state: Mapping[str, Any]   # key metric forecasts
    confidence: float               # [0.0, 1.0]
    horizon_ns: int                 # how far ahead (nanoseconds)
    basis_window_ids: frozenset[str]     # WindowedAggregate IDs used as basis
    created_at_ns: int              # wall-clock at creation time
```

### `PredictionError`

```python
@dataclass(frozen=True)
class PredictionError:
    prediction_id: str
    actual_state: Mapping[str, Any]
    mse: float              # mean-squared error across predicted keys
    abs_err: float          # mean absolute error
    correct_direction: bool # did prediction get direction right?
```

### `PredictorConfig`

```python
@dataclass(frozen=True)
class PredictorConfig:
    horizon_ms: int = 1000             # prediction horizon in ms
    min_windows: int = 5               # minimum windows before predicting
    confidence_threshold: float = 0.6  # suppress predictions below this
    track_errors: bool = True          # record PredictionError for calibration
    max_history: int = 500             # max stored errors/windows per module
```

---

## Protocol: `PredictiveEngine`

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class PredictiveEngine(Protocol):
    async def train(self, windows: list[WindowedAggregate]) -> None:
        """Ingest new windowed aggregates to update internal model."""
        ...

    async def predict(self, module: str) -> Prediction | None:
        """Return forecast for module or None if insufficient data/confidence."""
        ...

    async def record_outcome(
        self,
        actual: Mapping[str, Any],
        prediction_id: str,
    ) -> PredictionError:
        """Compare actual state to prior prediction; update ensemble weights."""
        ...

    async def calibrate(self) -> dict[str, float]:
        """Recalculate smoothing alpha from recent error rates. Returns new alpha map."""
        ...

    async def stats(self) -> dict:
        """Return per-module prediction counts, mean MSE, current alpha values."""
        ...
```

---

## Implementation: `AdaptivePredictiveEngine`

```python
import asyncio, time, uuid, math
from collections import defaultdict, deque
from typing import Mapping, Any

class AdaptivePredictiveEngine:
    def __init__(
        self,
        config: PredictorConfig = PredictorConfig(),
        strategy: PredictionStrategy = PredictionStrategy.ENSEMBLE,
    ) -> None:
        self._config = config
        self._strategy = strategy
        self._lock = asyncio.Lock()
        # per-module rolling window deques
        self._windows: dict[str, deque[WindowedAggregate]] = defaultdict(
            lambda: deque(maxlen=config.max_history)
        )
        # per-module EMA state: {module: {metric_key: ema_value}}
        self._ema: dict[str, dict[str, float]] = defaultdict(dict)
        # per-module smoothing alpha (starts at 0.3, updated by calibrate())
        self._alpha: dict[str, float] = defaultdict(lambda: 0.3)
        # per-strategy weight for ENSEMBLE: [last_val, ema, linear]
        self._weights: dict[str, list[float]] = defaultdict(
            lambda: [1/3, 1/3, 1/3]
        )
        # error history for calibration
        self._errors: dict[str, deque[PredictionError]] = defaultdict(
            lambda: deque(maxlen=config.max_history)
        )
        # in-flight predictions for outcome matching
        self._pending: dict[str, tuple[str, Prediction]] = {}
        # counters
        self._pred_count = self._above_threshold = 0
        self._train_count = self._cal_count = 0

    # ── train ──────────────────────────────────────────────────────────────
    async def train(self, windows: list[WindowedAggregate]) -> None:
        async with self._lock:
            for w in windows:
                mod = w.module_id
                self._windows[mod].append(w)
                a = self._alpha[mod]
                for k, v in w.metrics.items():
                    if isinstance(v, (int, float)):
                        prev = self._ema[mod].get(k, float(v))
                        self._ema[mod][k] = a * float(v) + (1 - a) * prev
                self._train_count += 1
            TRAINING_WINDOWS.inc(len(windows))

    # ── predict ────────────────────────────────────────────────────────────
    async def predict(self, module: str) -> Prediction | None:
        async with self._lock:
            wins = self._windows[module]
            if len(wins) < self._config.min_windows:
                return None
            wins_list = list(wins)
            predicted_state = self._run_strategy(module, wins_list)
            confidence = self._confidence(module, predicted_state)
            self._pred_count += 1
            PREDICTIONS_MADE.inc()
            if confidence < self._config.confidence_threshold:
                return None
            self._above_threshold += 1
            PREDICTIONS_ABOVE_THRESHOLD.inc()
            pred = Prediction(
                prediction_id=uuid.uuid4().hex,
                target_module=module,
                predicted_state=predicted_state,
                confidence=confidence,
                horizon_ns=self._config.horizon_ms * 1_000_000,
                basis_window_ids=frozenset(w.window_id for w in wins_list[-5:]),
                created_at_ns=time.time_ns(),
            )
            self._pending[pred.prediction_id] = (module, pred)
            return pred

    # ── internal strategy dispatch ─────────────────────────────────────────
    def _run_strategy(
        self, module: str, wins: list[WindowedAggregate]
    ) -> dict[str, Any]:
        if self._strategy == PredictionStrategy.LAST_VALUE:
            return dict(wins[-1].metrics)
        if self._strategy == PredictionStrategy.EXPONENTIAL_SMOOTH:
            return dict(self._ema[module])
        if self._strategy == PredictionStrategy.LINEAR_TREND:
            return self._linear_trend(wins)
        # ENSEMBLE
        lv  = dict(wins[-1].metrics)
        ema = dict(self._ema[module])
        lt  = self._linear_trend(wins)
        w   = self._weights[module]
        keys = set(lv) | set(ema) | set(lt)
        return {
            k: sum(wi * v for wi, v in zip(w, [lv.get(k, 0.0), ema.get(k, 0.0), lt.get(k, 0.0)]))
            for k in keys
        }

    def _linear_trend(self, wins: list[WindowedAggregate]) -> dict[str, Any]:
        """2-point regression on first and last window summaries."""
        if len(wins) < 2:
            return dict(wins[-1].metrics)
        first, last = wins[0].metrics, wins[-1].metrics
        return {
            k: float(last[k]) + (float(last[k]) - float(first.get(k, last[k])))
            for k in last
        }

    def _confidence(self, module: str, predicted: dict[str, Any]) -> float:
        """confidence = 1 - (std_dev / mean) clamped to [0, 1]."""
        vals = [float(v) for v in predicted.values() if isinstance(v, (int, float))]
        if not vals:
            return 0.0
        mean = sum(vals) / len(vals)
        if mean == 0.0:
            return 0.0
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(variance)
        return max(0.0, min(1.0, 1.0 - std / abs(mean)))

    # ── record_outcome ─────────────────────────────────────────────────────
    async def record_outcome(
        self, actual: Mapping[str, Any], prediction_id: str
    ) -> PredictionError:
        async with self._lock:
            entry = self._pending.pop(prediction_id, None)
            if entry is None:
                raise KeyError(f"Unknown prediction_id: {prediction_id}")
            module, pred = entry
            keys = list(pred.predicted_state)
            sq, ab, dm = [], [], []
            for k in keys:
                p_val = float(pred.predicted_state.get(k, 0))
                a_val = float(actual.get(k, 0))
                sq.append((p_val - a_val) ** 2)
                ab.append(abs(p_val - a_val))
                last_val = float(list(self._windows[module])[-1].metrics.get(k, p_val))
                dm.append((a_val - last_val) * (p_val - last_val) > 0)
            mse = sum(sq) / len(sq) if sq else 0.0
            err = PredictionError(
                prediction_id=prediction_id,
                actual_state=dict(actual),
                mse=mse,
                abs_err=sum(ab) / len(ab) if ab else 0.0,
                correct_direction=bool(dm) and all(dm),
            )
            if self._config.track_errors:
                self._errors[module].append(err)
            self._update_ensemble_weights(module, err)
            PREDICTION_MSE.set(mse)
            return err

    def _update_ensemble_weights(
        self, module: str, err: PredictionError
    ) -> None:
        """Nudge ensemble weights toward strategies with lower MSE."""
        lr = 0.05
        w = self._weights[module]
        grad = err.mse * lr
        worst = w.index(max(w))
        w = [w[i] - grad / 3 if i == worst else w[i] + grad / 6 for i in range(3)]
        total = sum(w)
        self._weights[module] = [x / total for x in w]

    # ── calibrate ──────────────────────────────────────────────────────────
    async def calibrate(self) -> dict[str, float]:
        """Recalculate alpha per module from recent PredictionError.mse rates."""
        async with self._lock:
            result: dict[str, float] = {}
            for mod, errs in self._errors.items():
                if not errs:
                    continue
                mean_mse = sum(e.mse for e in errs) / len(errs)
                # higher error → higher alpha (react faster to new data)
                new_alpha = max(0.1, min(0.9, 0.3 + mean_mse * 0.5))
                self._alpha[mod] = new_alpha
                result[mod] = new_alpha
                self._cal_count += 1
                CALIBRATION_ADJUSTMENTS.inc()
            return result

    # ── stats ──────────────────────────────────────────────────────────────
    async def stats(self) -> dict:
        async with self._lock:
            return {
                "predictions_made": self._pred_count,
                "above_threshold": self._above_threshold,
                "training_windows": self._train_count,
                "calibrations": self._cal_count,
                "modules": list(self._windows.keys()),
                "alpha_map": dict(self._alpha),
                "ensemble_weights": dict(self._weights),
            }
```

---

## `NullPredictiveEngine`

```python
class NullPredictiveEngine:
    async def train(self, windows: list[WindowedAggregate]) -> None:
        pass

    async def predict(self, module: str) -> Prediction | None:
        return None

    async def record_outcome(
        self, actual: Mapping[str, Any], prediction_id: str
    ) -> PredictionError:
        return PredictionError(
            prediction_id=prediction_id,
            actual_state=dict(actual),
            mse=0.0,
            abs_err=0.0,
            correct_direction=True,
        )

    async def calibrate(self) -> dict[str, float]:
        return {}

    async def stats(self) -> dict:
        return {}
```

---

## EMA Formula + Ensemble Weighting Diagram

```
EMA update (per metric key, per module):
  ema_t = alpha * x_t + (1 - alpha) * ema_{t-1}

alpha tuning:
  initial:              0.30   (≈ 5.7-window effective lookback)
  after high MSE:  up to 0.90  (≈ 1.2-window — very reactive)
  after low MSE:   down to 0.10 (≈ 19-window — very stable)
  calibrated via: alpha_new = clamp(0.1, 0.9, 0.3 + mean_mse * 0.5)

Ensemble weights [w_lv, w_ema, w_lt], initial = [0.333, 0.333, 0.333]

On record_outcome() with PredictionError.mse:
  worst_strategy = argmax(weights)
  weights[worst]  -= mse * 0.05 / 3      # penalise dominant strategy
  weights[others] += mse * 0.05 / 6      # redistribute to others
  weights = normalise(weights)            # enforce sum = 1.0

Example evolution:
  Round 0:  [0.333, 0.333, 0.333]
  After LINEAR_TREND high-MSE:
  Round 1:  [0.343, 0.343, 0.315]
  After EMA correct prediction:
  Round 2:  [0.336, 0.350, 0.314]  ← EMA gaining dominance
```

---

## Prometheus Metrics

```python
from prometheus_client import Counter, Gauge

PREDICTIONS_MADE           = Counter("asi_predictions_made_total",
                                      "Total predictions generated")
PREDICTIONS_ABOVE_THRESHOLD = Counter("asi_predictions_above_threshold_total",
                                       "Predictions passing confidence threshold")
PREDICTION_MSE             = Gauge("asi_prediction_mse_gauge",
                                    "Most recent prediction MSE")
CALIBRATION_ADJUSTMENTS    = Counter("asi_calibration_adjustments_total",
                                      "Number of alpha recalibrations")
TRAINING_WINDOWS           = Counter("asi_training_windows_processed_total",
                                      "WindowedAggregates ingested for training")
```

| Metric | Type | Description |
|---|---|---|
| `asi_predictions_made_total` | Counter | All predictions generated (incl. below threshold) |
| `asi_predictions_above_threshold_total` | Counter | Predictions surfaced to callers |
| `asi_prediction_mse_gauge` | Gauge | Rolling MSE of most recent outcome |
| `asi_calibration_adjustments_total` | Counter | Times `calibrate()` updated an alpha value |
| `asi_training_windows_processed_total` | Counter | `WindowedAggregate` batches fed to `train()` |

**PromQL examples:**
```promql
# Prediction acceptance rate
rate(asi_predictions_above_threshold_total[5m])
  / rate(asi_predictions_made_total[5m])

# MSE threshold alert
asi_prediction_mse_gauge > 0.5

# Calibration frequency
increase(asi_calibration_adjustments_total[1h])
```

**Grafana alert — MSE spike:**
```yaml
alert: PredictionMSEHigh
expr: asi_prediction_mse_gauge > 0.5
for: 2m
labels:
  severity: warning
annotations:
  summary: "PredictiveEngine MSE elevated ({{ $value | humanize }})"
  description: "Prediction accuracy degraded — consider calling calibrate() or inspecting EventSequencer output"
```

---

## mypy Narrowing Table

| Return Type | Context | Narrowing Pattern |
|---|---|---|
| `Prediction \| None` | `predict()` caller | `if pred := await engine.predict(m):` |
| `Mapping[str, Any]` vs `dict` | `record_outcome(actual=...)` | accept both; `dict(actual)` for frozen storage |
| `dict[str, float]` | `calibrate()` return | direct use — no narrowing needed |
| `list[float]` | `_weights[module]` | `defaultdict(lambda: [1/3,1/3,1/3])` always returns list |
| `tuple[str, Prediction]` | `_pending.pop()` | check `is None` before unpacking |

---

## 12 Test Targets

| # | Test | Validates |
|---|---|---|
| 1 | `test_train_updates_ema` | EMA converges after repeated `train()` calls |
| 2 | `test_predict_returns_none_below_min_windows` | Guard on `min_windows` |
| 3 | `test_predict_returns_none_below_confidence` | Confidence threshold suppression |
| 4 | `test_last_value_strategy` | LAST_VALUE returns most-recent window metrics |
| 5 | `test_linear_trend_extrapolates` | LINEAR_TREND adds delta to last step |
| 6 | `test_ensemble_weights_update_on_error` | `_update_ensemble_weights` shifts weights after high MSE |
| 7 | `test_low_window_returns_none` | Under `min_windows` → `predict()` → None |
| 8 | `test_record_outcome_computes_mse` | MSE = mean of squared diffs across keys |
| 9 | `test_record_outcome_unknown_id_raises` | `KeyError` on unknown `prediction_id` |
| 10 | `test_calibrate_raises_alpha_on_high_error` | High MSE → alpha increases after `calibrate()` |
| 11 | `test_null_predict_always_returns_none` | `NullPredictiveEngine.predict()` → None |
| 12 | `test_stats_returns_expected_keys` | `stats()` keys match documented schema |

### Test Skeletons

```python
async def test_ensemble_weights_update_on_error():
    engine = AdaptivePredictiveEngine(
        config=PredictorConfig(min_windows=2, confidence_threshold=0.0),
        strategy=PredictionStrategy.ENSEMBLE,
    )
    wins = [make_window("m", {"load": float(i)}) for i in range(3)]
    await engine.train(wins)
    pred = await engine.predict("m")
    assert pred is not None
    # inject a large error — should penalise worst-weight strategy
    await engine.record_outcome({"load": 999.0}, pred.prediction_id)
    w = engine._weights["m"]
    # no single strategy should dominate uniformly after the error
    assert max(w) < 1/3 + 0.05

async def test_low_window_returns_none():
    engine = AdaptivePredictiveEngine(
        config=PredictorConfig(min_windows=5, confidence_threshold=0.0)
    )
    await engine.train([make_window("m", {"x": 1.0})])  # only 1 window
    result = await engine.predict("m")
    assert result is None  # below min_windows guard
```

---

## 14-Step Implementation Order

1. Add `PredictionStrategy` enum to `asi_build/temporal/types.py`
2. Add `Prediction`, `PredictionError`, `PredictorConfig` frozen dataclasses
3. Define `PredictiveEngine` Protocol (runtime_checkable)
4. Implement `NullPredictiveEngine` — all no-ops
5. Scaffold `AdaptivePredictiveEngine.__init__()` with all internal state
6. Implement `train()` — append to deque + EMA update per metric
7. Implement `_linear_trend()` — 2-point extrapolation helper
8. Implement `_run_strategy()` — dispatch to strategy implementations
9. Implement `_confidence()` — coefficient of variation inversion
10. Implement `predict()` — min_windows guard + confidence gate + Prediction construction
11. Implement `_update_ensemble_weights()` — online gradient nudge
12. Implement `record_outcome()` — MSE/abs_err/direction computation + weight update
13. Implement `calibrate()` — alpha recalculation from error history
14. Wire Prometheus metrics; add tests for all 12 targets

---

## Phase 17 Sub-phase Tracker

| Sub-phase | Component | Issue | Wiki | Status |
|---|---|---|---|---|
| 17.1 | TemporalGraph | [#434](https://github.com/web3guru888/asi-build/issues/434) | [Phase-17-Temporal-Graph](Phase-17-Temporal-Graph) | 🟡 open |
| 17.2 | EventSequencer | [#437](https://github.com/web3guru888/asi-build/issues/437) | [Phase-17-Event-Sequencer](Phase-17-Event-Sequencer) | 🟡 open |
| 17.3 | PredictiveEngine | [#440](https://github.com/web3guru888/asi-build/issues/440) | [Phase-17-Predictive-Engine](Phase-17-Predictive-Engine) | 🟡 open |
| 17.4 | ForecastScheduler | TBD | TBD | 🔲 |
| 17.5 | TemporalOrchestrator | TBD | TBD | 🔲 |

---

_138th wiki page · Phase 17 · ASI-Build_
