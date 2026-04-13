# Phase 6.3 — EWC Integration: Wiring EWCRegulariser into STDPOnlineLearner

**Status**: 🟡 In Progress — Issue #249  
**Depends on**: Phase 6.1 (#241), Phase 6.2 (#245)  
**Previous**: [Phase-6-Fisher-Backends](Phase-6-Fisher-Backends) (Phase 6.2)  
**Next**: Phase 6.4 — Fisher warm-up prior + task registry (planned)

---

## Overview

Phase 6.3 makes EWC **active** in the learning pipeline. `EWCRegulariser` (Phase 6.1) and the Fisher backends (Phase 6.2) are wired into `STDPOnlineLearner` so that every weight update is penalised proportional to Fisher importance. Parameters critical to previously consolidated tasks are protected; less-used parameters remain free to adapt.

---

## EWC in the Learning Pipeline

```
CognitiveCycle.tick()
      │
      ▼ LEARNING phase
STDPOnlineLearner.update(pre_times, post_times, task_id)
      │
      ├─ 1. Compute raw STDP delta
      │       delta_w = A+ · exp(-Δt/τ+) - A- · exp(Δt/τ-)
      │
      ├─ 2. Apply EWC constraint (NEW in 6.3)
      │       grad = 2λ · F · (w - w*)
      │       delta_w = delta_w - grad          ← penalised delta
      │
      ├─ 3. Clip delta to [w_min, w_max]
      │
      └─ 4. Update weights + emit WeightUpdate
```

```
      │
      ▼ SLEEP_PHASE (existing from 6.1)
MemoryConsolidator._ewc_hook()
      ├─ 1. Estimate Fisher from recent weight deltas
      ├─ 2. Save FisherSnapshot (backend: InMemory / Neo4j / Cached)
      └─ 3. anchor_weights = current weights
```

---

## New / Modified Components

### `EWCRegulariser.penalty_gradient()` — new method

Returns the per-weight gradient of the EWC quadratic penalty:

```python
async def penalty_gradient(
    self,
    weights: npt.NDArray[np.float32],
    task_id: str,
) -> npt.NDArray[np.float32]:
    """Return 2 * lambda * F * (w - w_star).

    Returns zeros if no snapshot exists (first episode, no SLEEP yet).
    Returns zeros if snapshot shape doesn't match (architecture changed).
    """
    snapshot = await self._store.load(task_id)
    if snapshot is None:
        return np.zeros_like(weights)
    if snapshot.anchor_weights.shape != weights.shape:
        logger.warning(
            "Fisher shape mismatch: %s vs %s — EWC disabled for this update",
            snapshot.anchor_weights.shape, weights.shape,
        )
        return np.zeros_like(weights)
    grad = (
        2.0
        * self._config.ewc_lambda
        * snapshot.fisher_diag
        * (weights - snapshot.anchor_weights)
    )
    # Clip to prevent gradient explosion when Fisher >> 1
    clipped = np.clip(grad, -self._config.max_penalty_clip, self._config.max_penalty_clip)
    n_clipped = int(np.sum(np.abs(grad) > self._config.max_penalty_clip))
    if n_clipped > 0:
        PENALTY_CLIPPED.labels(task_id=task_id).inc(n_clipped)
    PENALTY_MAGNITUDE.labels(task_id=task_id).observe(float(np.linalg.norm(clipped)))
    return clipped
```

### `STDPOnlineLearner._apply_ewc_constraint()` — new method

```python
async def _apply_ewc_constraint(
    self,
    delta_w: npt.NDArray[np.float32],
    task_id: str,
) -> npt.NDArray[np.float32]:
    """Subtract EWC penalty gradient from raw STDP delta."""
    if self._ewc is None:
        return delta_w  # Pass-through: backward compatible with ewc=None
    WEIGHT_DELTA_BEFORE.observe(float(np.linalg.norm(delta_w)))
    grad = await self._ewc.penalty_gradient(self._weights, task_id)
    constrained = delta_w - grad
    WEIGHT_DELTA_AFTER.observe(float(np.linalg.norm(constrained)))
    return constrained
```

### `STDPOnlineLearner.update()` — modified signature

```python
async def update(
    self,
    pre_times:  npt.NDArray[np.float32],
    post_times: npt.NDArray[np.float32],
    task_id:    str = "default",       # NEW: default preserves backward compat
) -> WeightUpdate:
    delta_w = self._stdp_kernel(pre_times, post_times)
    delta_w = await self._apply_ewc_constraint(delta_w, task_id)
    self._weights = np.clip(
        self._weights + self._config.learning_rate * delta_w,
        self._config.w_min,
        self._config.w_max,
    )
    return WeightUpdate(delta_w=delta_w, new_weights=self._weights.copy())
```

### `STDPOnlineLearner.__init__()` — new optional parameter

```python
def __init__(
    self,
    config:  STDPConfig,
    ewc:     EWCRegulariser | None = None,   # NEW: optional EWC integration
) -> None:
    self._config  = config
    self._ewc     = ewc
    self._weights = np.zeros(config.weight_shape, dtype=np.float32)
```

---

## EWCConfig — New Fields (Phase 6.3)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `max_penalty_clip` | `float` | `1.0` | Per-weight gradient clip |
| `penalty_accumulation` | `Literal["per_update", "batch"]` | `"per_update"` | When to apply penalty |

---

## Prometheus Metrics (4 new)

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `phase6_ewc_penalty_magnitude` | Histogram | `task_id` | L2 norm of clipped penalty gradient |
| `phase6_ewc_penalty_clipped_total` | Counter | `task_id` | Weights where raw gradient exceeded clip |
| `phase6_weight_delta_before_ewc` | Histogram | — | Raw STDP delta L2 |
| `phase6_weight_delta_after_ewc` | Histogram | — | Constrained delta L2 |

### Grafana PromQL

```promql
# Effective learning ratio (1.0 = no EWC; 0.0 = fully constrained)
rate(phase6_weight_delta_after_ewc_sum[5m])
/ rate(phase6_weight_delta_before_ewc_sum[5m])

# Penalty clip rate (spikes = Fisher instability)
rate(phase6_ewc_penalty_clipped_total[1m])

# Penalty magnitude over time
histogram_quantile(0.95, rate(phase6_ewc_penalty_magnitude_bucket[5m]))
```

---

## Test Targets (10)

| Test | File | What it verifies |
|---|---|---|
| `test_penalty_gradient_no_snapshot` | `test_ewc_integration.py` | Returns zeros when store is empty |
| `test_penalty_gradient_values` | `test_ewc_integration.py` | Correct 2λF(w-w*) formula |
| `test_penalty_gradient_clip` | `test_ewc_integration.py` | Clips when Fisher is huge (1e6) |
| `test_penalty_gradient_shape_mismatch` | `test_ewc_integration.py` | Returns zeros when shapes differ |
| `test_update_without_ewc` | `test_stdp_ewc.py` | Pass-through: ewc=None preserves old behaviour |
| `test_update_with_ewc_reduces_delta` | `test_stdp_ewc.py` | Constraint reduces effective delta |
| `test_update_ewc_zero_fisher` | `test_stdp_ewc.py` | Fisher=0 → gradient=0 → delta unchanged |
| `test_ewc_anchor_respected` | `test_stdp_ewc.py` | Near anchor = small penalty; far = large |
| `test_prometheus_penalty_histogram` | `test_stdp_ewc.py` | Histogram emits on every update |
| `test_prometheus_clip_counter` | `test_stdp_ewc.py` | Counter increments on clip event |

---

## Implementation Order

1. Add `max_penalty_clip` and `penalty_accumulation` to `EWCConfig` (`learning/ewc.py`)
2. Implement `EWCRegulariser.penalty_gradient()` with clip logic and Prometheus hooks
3. Add `ewc: EWCRegulariser | None = None` to `STDPOnlineLearner.__init__()`
4. Implement `_apply_ewc_constraint()` method with before/after metrics
5. Modify `update()` signature — add `task_id: str = "default"`
6. Write 10 unit tests (mock `FisherMatrixBase`, no real Neo4j/Redis)
7. Run `mypy --strict asi/phase6/`
8. Update `build_phase5_cycle()` factory to accept optional `EWCRegulariser`

---

## EWC Interaction with Other Phase 5/6 Components

| Component | Interaction |
|---|---|
| `MemoryConsolidator` | Produces Fisher snapshots during SLEEP_PHASE (Phase 6.1) |
| `FisherStoreFactory` | Selects backend for EWCRegulariser store (Phase 6.2) |
| `Phase5RollbackManager` | Hot-reload sets weights to pre-degradation state; EWC anchor becomes temporarily stale — large penalty will push weights back toward anchor (desired behaviour) |
| `CognitiveCycle` | `_phase5_dispatch()` calls `STDPOnlineLearner.update()` during LEARNING |
| `Phase5MetricsExporter` | Phase 6 metrics co-exist in same Prometheus registry; no prefix collision |

---

## EWC Warm-up (Phase 6.4 Preview)

The first LEARNING episode after startup has no Fisher snapshot, so EWC returns zero gradient. This is correct but means the first episode is unconstrained.

**Phase 6.4 will add**:
- `EWCConfig.warm_up_fisher_prior`: a synthetic uniform Fisher value for the very first SLEEP_PHASE
- `EWCConfig.task_registry`: a map of `task_id → EWCConfig overrides` for multi-task agents

---

## References

- Issue #249 — this phase
- Issue #241 — Phase 6.1 (EWC Foundation)
- Issue #245 — Phase 6.2 (Fisher Backends)
- Issue #181 — STDPOnlineLearner
- Discussion #248 — Phase 6.3 integration strategy
- Discussion #250 — EWC penalty math + visualization
- Discussion #251 — EWCRegulariser tuning & debugging
- [Phase-6-EWC-Foundation](Phase-6-EWC-Foundation)
- [Phase-6-Fisher-Backends](Phase-6-Fisher-Backends)
