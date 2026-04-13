# Phase 6.4 — Online Fisher Matrix Updates

**Status**: 🔲 Spec open — see issue #252  
**Module**: `asi/learning/fisher_online.py`  
**Depends on**: Phase 6.1 (`FisherMatrixBase`, `FisherSnapshot`), Phase 6.2 (backends), Phase 6.3 (`STDPOnlineLearner`)

---

## Motivation

Phases 6.1–6.3 established EWC with a **batch Fisher estimator**: the Fisher information matrix is computed once per SLEEP cycle by passing over the recent episode buffer. This is accurate but creates a staleness window — parameters can drift significantly between SLEEP cycles without the regulariser seeing updated importance weights.

Phase 6.4 introduces **online (incremental) Fisher estimation** via exponential moving average (EMA), providing continuously-updated importance weights at O(P) per step.

---

## EMA Fisher Update Rule

```
F_i(t) = α · g_i(t)² + (1 - α) · F_i(t-1)
```

| Symbol | Meaning |
|--------|---------|
| `F_i(t)` | Fisher importance of parameter i at step t |
| `g_i(t)` | Gradient signal at step t |
| `α` | Decay rate (freshness vs. stability) |
| `1 - α` | Memory factor |
| `t_{1/2} = ln(2)/α` | Half-life in steps |

### Alpha Sensitivity

| α | Half-life (steps) | Tracks fast changes | Stable under noise |
|---|------------------|--------------------|-------------------|
| 0.001 | ~693 | No | Very stable |
| 0.01 | ~69 | Moderate | Stable ← **recommended** |
| 0.05 | ~14 | Yes | Moderate |
| 0.1 | ~7 | Yes | Noisy |

For a 10 ms agent tick, `α = 0.01` → ~690-step (~7s) half-life.

---

## Surrogate Gradient Signal

`STDPOnlineLearner` uses spike-timing rules rather than backpropagation — true log-likelihood gradients are undefined for discrete spikes. We use the **STDP weight delta as a surrogate**:

```
g_i(t) ≈ Δw_i(t) = w_i(t) − w_i(t−1)
```

- Large |Δw| → parameter is actively changing → high Fisher importance.
- Small |Δw| → parameter is stable → lower importance.

This is inspired by the **Synaptic Intelligence** approach (Zenke et al. 2017, *Continual Learning Through Synaptic Intelligence*). Key difference: SI uses `Σ Δw·g` along the trajectory; this implementation uses `Δw²` as the sole signal, which is simpler and sufficient for STDP.

Custom learners with access to true gradients can pass them directly to `accumulator.update()` for more accurate estimates.

---

## New Components

### `FisherAccumulatorConfig`

```python
@dataclass
class FisherAccumulatorConfig:
    alpha: float = 0.01            # EMA decay rate
    min_samples: int = 10          # steps before first snapshot
    snapshot_every: int = 50       # steps between FisherStore writes
    max_staleness_steps: int = 500 # warn if snapshot not written
```

### `AccumulatorStats`

```python
@dataclass
class AccumulatorStats:
    steps: int
    snapshots_written: int
    last_snapshot_step: int
    max_delta: float               # max |F_new - F_old| across params
```

### `FisherAccumulator`

```python
class FisherAccumulator:
    """
    Maintains a per-parameter EMA of squared gradients.
    Called once per STDP update step.
    Writes to FisherMatrixStore every snapshot_every steps.
    """

    def __init__(
        self,
        config: FisherAccumulatorConfig,
        store: FisherMatrixBase,
        task_id: str,
    ) -> None:
        self._config = config
        self._store = store
        self._task_id = task_id
        self._ema: dict[str, npt.NDArray[np.float32]] = {}
        self._steps: int = 0
        self._last_snapshot_step: int = 0
        self._snapshots_written: int = 0
        self._lock = asyncio.Lock()

    async def update(
        self,
        gradients: dict[str, npt.NDArray[np.float32]],
    ) -> None:
        """One EMA step. Writes snapshot when due."""
        async with self._lock:
            self._steps += 1
            for name, g in gradients.items():
                g_sq = (g * g).astype(np.float32)
                if name not in self._ema:
                    self._ema[name] = g_sq
                else:
                    a = self._config.alpha
                    self._ema[name] = a * g_sq + (1.0 - a) * self._ema[name]

            if self._steps < self._config.min_samples:
                return

            if self._steps % self._config.snapshot_every == 0:
                await self._write_snapshot()

            stale = self._steps - self._last_snapshot_step
            if stale > self._config.max_staleness_steps:
                logger.warning("Fisher snapshot stale: %d steps", stale)
                _STALENESS_WARNINGS.labels(task_id=self._task_id).inc()

    async def force_snapshot(self) -> FisherSnapshot:
        """Used by SLEEP_PHASE consolidation hook."""
        async with self._lock:
            return await self._write_snapshot()

    def stats(self) -> AccumulatorStats:
        max_delta = max(
            float(np.abs(v).max()) for v in self._ema.values()
        ) if self._ema else 0.0
        return AccumulatorStats(
            steps=self._steps,
            snapshots_written=self._snapshots_written,
            last_snapshot_step=self._last_snapshot_step,
            max_delta=max_delta,
        )
```

### `OnlineFisherSnapshot`

```python
@dataclass
class OnlineFisherSnapshot(FisherSnapshot):
    """Extends FisherSnapshot with online-estimation provenance."""
    alpha: float
    steps_accumulated: int
    estimated_at_step: int
```

---

## Modified `STDPOnlineLearner.update()`

The existing signature gains an optional keyword-only `accumulator` parameter:

```python
async def update(
    self,
    pre: npt.NDArray[np.float32],
    post: npt.NDArray[np.float32],
    weights: npt.NDArray[np.float32],
    *,
    regulariser: EWCRegulariser | None = None,
    accumulator: FisherAccumulator | None = None,   # ← NEW
    task_id: str | None = None,
) -> WeightUpdate:
    ...
    if accumulator is not None:
        await accumulator.update({"weights": weight_delta})
    ...
```

The `*` barrier ensures all existing positional-arg call sites are unaffected.

---

## SLEEP_PHASE Integration

```
SLEEP_PHASE begins
  → FisherAccumulator.force_snapshot()      # write latest EMA to store
  → MemoryConsolidator.consolidate()        # episode → KG
  → EWCRegulariser._apply_ewc_constraint()  # reads from store
SLEEP_PHASE ends
```

The hook order is critical: `force_snapshot()` must complete before the regulariser reads.

---

## Snapshot Interval Trade-offs

| `snapshot_every` | Writes / 1000 steps | Neo4j overhead | Freshness |
|-----------------|-------------------|----------------|-----------|
| 10 | 100 | High | Very fresh |
| 50 | 20 | Moderate | Fresh ← **recommended** |
| 100 | 10 | Low | Good |
| 500 | 2 | Minimal | Stale |

For `InMemoryFisherStore` (tests), `snapshot_every=1` is fine.

---

## Prometheus Metrics

Pre-init all labelled metrics at module import time:

```python
_EMA_STEPS = Counter(
    "ewc_fisher_ema_steps_total",
    "Total EMA update steps",
    ["task_id"],
)
_SNAPSHOT_AGE = Gauge(
    "ewc_fisher_snapshot_age_steps",
    "Steps since last Fisher snapshot",
    ["task_id"],
)
_MAX_DELTA = Gauge(
    "ewc_fisher_max_delta",
    "Max |F_new - F_old| across params at last snapshot",
    ["task_id"],
)
_STALENESS_WARNINGS = Counter(
    "ewc_fisher_staleness_warnings_total",
    "Fisher snapshot staleness threshold breaches",
    ["task_id"],
)
```

### PromQL Examples

```promql
# EMA update rate (steps/s)
rate(ewc_fisher_ema_steps_total[1m])

# Current snapshot age
ewc_fisher_snapshot_age_steps

# Fisher drift per snapshot (alert if > 0.5)
ewc_fisher_max_delta > 0.5

# Staleness warnings (should stay 0)
increase(ewc_fisher_staleness_warnings_total[5m]) > 0
```

---

## Test Targets

| # | Test | What it guards |
|---|------|----------------|
| 1 | `test_accumulator_ema_decay` | F(t) = α·g² + (1-α)·F(t-1) applied correctly |
| 2 | `test_accumulator_no_snapshot_before_min_samples` | guard on `min_samples` |
| 3 | `test_snapshot_written_at_interval` | store.save called every `snapshot_every` |
| 4 | `test_force_snapshot_bypasses_counter` | force_snapshot ignores step counter |
| 5 | `test_force_snapshot_resets_counter` | counter resets after force |
| 6 | `test_max_staleness_warning` | log warning + Prometheus counter when stale |
| 7 | `test_stdp_learner_accumulator_kwarg` | accumulator.update called once per STDP step |
| 8 | `test_stdp_backwards_compat_no_accumulator` | no accumulator → existing behaviour unchanged |
| 9 | `test_online_fisher_snapshot_fields` | `OnlineFisherSnapshot` carries provenance fields |
| 10 | `test_accumulator_multi_task_isolation` | separate task_id paths don't cross-contaminate |

---

## Implementation Order

1. Add `FisherAccumulatorConfig` and `AccumulatorStats` dataclasses to `learning/fisher_online.py`
2. Implement `FisherAccumulator.__init__()` (store ref, EMA dict, step counter, lock)
3. Implement `FisherAccumulator.update()` (EMA step + conditional snapshot)
4. Implement `FisherAccumulator.force_snapshot()` (bypass counter, reset)
5. Add `OnlineFisherSnapshot` dataclass
6. Wire Prometheus metrics (`ewc_fisher_ema_steps_total` etc.)
7. Modify `STDPOnlineLearner.update()` with keyword-only `accumulator` kwarg
8. Add `force_snapshot()` call to `MemoryConsolidator.on_sleep_phase()`
9. Write 10 tests (mock `FisherMatrixBase.save`, assert call counts + EMA values)
10. Update `EWCConfig` if needed (`online_fisher: bool = False` feature flag)

---

## Phase 5/6 Interaction Summary

| Phase 5 Component | Phase 6 Interaction |
|-------------------|---------------------|
| `MemoryConsolidator.on_sleep_phase()` | Calls `force_snapshot()` before consolidation |
| `STDPOnlineLearner.update()` | Forwards weight_delta to `FisherAccumulator.update()` |
| `CyclePhase.SLEEP_PHASE` | Guards Fisher operations from concurrent LEARNING ticks |
| `SleepPhaseGuard` | Ensures accumulator writes don't race consolidation |

---

## Phase 6 Roadmap

| Sub-phase | Issue | Status |
|-----------|-------|--------|
| 6.1 EWC Foundation | #241 | ✅ Spec filed |
| 6.2 Fisher Backends | #245 | ✅ Spec filed |
| 6.3 EWCRegulariser Integration | #249 | ✅ Spec filed |
| 6.4 Online Fisher Updates | #252 | 🔲 Open |

---

*See also: [Phase 6 EWC Foundation](Phase-6-EWC-Foundation), [Phase 6 Fisher Backends](Phase-6-Fisher-Backends), [Phase 6 EWC Integration](Phase-6-EWC-Integration)*
