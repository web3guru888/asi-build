# Phase 7.1 — Reptile Meta-Learning: ReptileMetaLearner, TaskSample, and SLEEP_PHASE Integration

> **Status**: Spec — implementation tracked in issue #259
> **Depends on**: Phase 6.1 (#241), Phase 6.4 (#252), Phase 6.5 (#255)

---

## Motivation

Phase 6 built a complete continual-learning system: EWC prevents catastrophic forgetting, Online Fisher tracks parameter importance incrementally, and TaskRegistry routes context to per-task Fisher matrices. However, the agent still **starts from scratch** each time it encounters a new task — adaptation requires many gradient steps.

**Meta-learning** solves this: instead of learning how to solve tasks, the agent learns an *initialisation* that can be adapted to any new task in very few steps. Phase 7 introduces this capability via the Reptile algorithm.

### Why Reptile?

| Criterion | MAML | **Reptile** | Episodic Replay |
|---|---|---|---|
| Second-order gradients | ✅ Required (expensive) | ❌ Not needed | ❌ Not needed |
| Hessian computation | ✅ Yes | ❌ No | ❌ No |
| Memory per meta-step | O(k × params) | **O(2 × params)** | O(buffer) |
| Inner-loop differentiability | ✅ Unrolled | ❌ Plain SGD | N/A |
| Pure-numpy compatible | ❌ | ✅ | ✅ |
| Few-shot accuracy (Omniglot) | 98.7% | **97.9%** | ~90% |

The 0.8% accuracy gap is worth the ~10× compute savings for on-device ASI agents. More importantly, Reptile's first-order nature means it integrates cleanly with the existing `FisherAccumulator` EWC penalty **without autograd**.

---

## Algorithm

Reptile (Nichol et al., 2018) maintains a set of **meta-parameters** $\theta$ that represent an optimal initialisation for fast adaptation:

$$\theta \leftarrow \theta + \varepsilon \cdot (\phi_i - \theta)$$

where $\phi_i$ are the task-adapted parameters after $k$ inner-loop SGD steps on task $T_i$ and $\varepsilon$ is the meta step-size.

### With a task batch of size $B$:

$$\phi_i = \theta - \alpha \sum_{j=1}^{k} \nabla_\theta \mathcal{L}_{T_i}(\theta^{(j)})$$

$$\theta \leftarrow \theta + \varepsilon \cdot \frac{1}{B} \sum_{i=1}^{B} (\phi_i - \theta)$$

### EWC Penalty in the Inner Loop

When `ewc_regulariser` is provided, the inner-loop gradient is augmented with the EWC penalty:

$$\nabla^{\text{EWC}} = \nabla_\phi \mathcal{L}_{T_i}(\phi) + \lambda \cdot F \odot (\phi - \theta_{\text{anchor}})$$

where $F$ is the Fisher diagonal from `FisherAccumulator` and $\theta_{\text{anchor}}$ are the pre-SLEEP parameters. This doubly guards against catastrophic forgetting: EWC consolidation in step 2 of the SLEEP hook, and EWC penalty during Reptile inner-loop in step 4.

---

## Component Map

```
asi/phase7/
├── __init__.py
│   └── exports: ReptileMetaLearner, TaskSample, MetaParamSnapshot, ReptileMetaUpdateResult
├── meta_types.py
│   ├── TaskSample             — frozen dataclass: task_id, support_set, query_set, labels
│   ├── MetaParamSnapshot      — params dict, step counter, timestamp
│   └── ReptileMetaUpdateResult — meta_loss, inner_losses, param_norm, update_norm, tasks_processed
└── reptile.py
    └── ReptileMetaLearner
            ├── __init__(base_learner, meta_lr, inner_steps, inner_lr, task_batch_size, metrics_registry)
            ├── meta_update(task_batch) → ReptileMetaUpdateResult   [async]
            ├── snapshot_meta_params()  → MetaParamSnapshot
            └── restore_meta_params(snapshot) → None
```

---

## Data Types

### `TaskSample`

```python
@dataclass(frozen=True)
class TaskSample:
    """A single task episode for meta-learning.
    
    support_set: examples the inner loop trains on  (shape: [k, feature_dim])
    query_set:   examples used to compute meta-loss (shape: [q, feature_dim])
    labels:      class indices for support+query     (shape: [k+q])
    """
    task_id:     str
    support_set: npt.NDArray[np.float32]
    query_set:   npt.NDArray[np.float32]
    labels:      npt.NDArray[np.int32]
```

`TaskSample` is `frozen=True` — mutation after construction raises `FrozenInstanceError`.

### `MetaParamSnapshot`

```python
@dataclass
class MetaParamSnapshot:
    """Serialisable checkpoint of meta-parameters for rollback."""
    params:    dict[str, npt.NDArray[np.float32]]  # deep-copied on creation
    step:      int                                   # monotonic step counter
    timestamp: float                                 # time.time() at snapshot
```

### `ReptileMetaUpdateResult`

```python
@dataclass(frozen=True)
class ReptileMetaUpdateResult:
    meta_loss:       float        # mean query-set loss after meta-update
    inner_losses:    list[float]  # per-task inner-loop final loss
    param_norm:      float        # L2 norm of meta-parameters
    update_norm:     float        # L2 norm of mean update vector
    tasks_processed: int          # tasks in this batch
```

---

## `ReptileMetaLearner` — Full Skeleton

```python
class ReptileMetaLearner:
    """First-order meta-learning via the Reptile algorithm.
    
    Maintains meta-parameters θ and performs per-task inner-loop adaptation
    followed by meta-parameter interpolation. Compatible with FisherAccumulator
    (Phase 6.4) and TaskContextManager (Phase 6.5).
    """

    def __init__(
        self,
        base_learner: LearningKernel,
        meta_lr: float = 0.01,
        inner_steps: int = 5,
        inner_lr: float = 1e-3,
        task_batch_size: int = 4,
        ewc_regulariser: EWCRegulariser | None = None,
        fisher_accumulator: FisherAccumulator | None = None,
        metrics_registry: CollectorRegistry | None = None,
    ) -> None:
        self._base_learner = base_learner
        self._meta_lr = meta_lr
        self._inner_steps = inner_steps
        self._inner_lr = inner_lr
        self._task_batch_size = task_batch_size
        self._ewc = ewc_regulariser
        self._fisher = fisher_accumulator
        self._meta_params: dict[str, npt.NDArray[np.float32]] = {}
        self._step: int = 0
        self._update_lock = asyncio.Lock()

        reg = metrics_registry or REGISTRY
        self._meta_updates_total = Counter(
            "asi_reptile_meta_updates_total",
            "Total Reptile meta-update calls",
            registry=reg,
        )
        self._inner_loss_hist = Histogram(
            "asi_reptile_inner_loss",
            "Per-task inner-loop loss",
            labelnames=["task_id"],
            registry=reg,
        )
        self._meta_loss_gauge = Gauge(
            "asi_reptile_meta_loss",
            "Current Reptile meta-loss",
            registry=reg,
        )
        self._param_norm_gauge = Gauge(
            "asi_reptile_param_norm",
            "L2 norm of meta-parameters",
            registry=reg,
        )
        self._update_norm_gauge = Gauge(
            "asi_reptile_update_norm",
            "L2 norm of meta-update vector",
            registry=reg,
        )
        self._tasks_per_batch_hist = Histogram(
            "asi_reptile_tasks_per_batch",
            "Task batch size distribution",
            registry=reg,
        )
        # Pre-initialise counters
        self._meta_updates_total.inc(0)
        self._meta_loss_gauge.set(0)
        self._param_norm_gauge.set(0)
        self._update_norm_gauge.set(0)

    async def meta_update(
        self,
        task_batch: Sequence[TaskSample],
        *,
        task_id: str | None = None,
    ) -> ReptileMetaUpdateResult:
        updates: list[dict[str, npt.NDArray[np.float32]]] = []
        inner_losses: list[float] = []

        for task in task_batch:
            # Set TaskContextManager context for Phase 6.5 routing
            token = set_current_task(task.task_id)
            try:
                phi = {k: v.copy() for k, v in self._meta_params.items()}
                loss = 0.0
                for _ in range(self._inner_steps):
                    grad, loss = self._compute_grad(phi, task)
                    # EWC penalty in inner loop (optional)
                    if self._ewc is not None and self._fisher is not None:
                        ewc_grad = await self._ewc.penalty_gradient(phi, task.task_id)
                        grad = {k: grad[k] + ewc_grad.get(k, 0.0) for k in grad}
                    phi = {k: v - self._inner_lr * grad[k] for k, v in phi.items()}
                updates.append({k: phi[k] - self._meta_params[k] for k in phi})
                inner_losses.append(loss)
                task_label = task.task_id[:16]  # cardinality guard
                self._inner_loss_hist.labels(task_id=task_label).observe(loss)
            finally:
                reset_current_task(token)

        # Compute mean update and apply (serialised)
        mean_update = {
            k: np.mean([u[k] for u in updates], axis=0) for k in updates[0]
        }
        update_norm = float(np.sqrt(sum(np.sum(v**2) for v in mean_update.values())))

        async with self._update_lock:
            self._meta_params = {
                k: self._meta_params[k] + self._meta_lr * mean_update[k]
                for k in self._meta_params
            }
            self._step += 1

        # Metrics
        meta_loss = float(np.mean(inner_losses))
        param_norm = float(np.sqrt(sum(np.sum(v**2) for v in self._meta_params.values())))
        self._meta_updates_total.inc()
        self._meta_loss_gauge.set(meta_loss)
        self._param_norm_gauge.set(param_norm)
        self._update_norm_gauge.set(update_norm)
        self._tasks_per_batch_hist.observe(len(task_batch))

        return ReptileMetaUpdateResult(
            meta_loss=meta_loss,
            inner_losses=inner_losses,
            param_norm=param_norm,
            update_norm=update_norm,
            tasks_processed=len(task_batch),
        )

    def snapshot_meta_params(self) -> MetaParamSnapshot:
        return MetaParamSnapshot(
            params={k: v.copy() for k, v in self._meta_params.items()},
            step=self._step,
            timestamp=time.time(),
        )

    def restore_meta_params(self, snapshot: MetaParamSnapshot) -> None:
        # Note: self._step is NOT reset — monotonic for Prometheus label consistency
        self._meta_params = {k: v.copy() for k, v in snapshot.params.items()}
```

---

## SLEEP_PHASE Hook Order (cumulative Phase 6 → 7)

```
MemoryConsolidator._run_sleep_phase()
├── 1. FisherAccumulator.force_snapshot()     [Phase 6.4]
├── 2. EWCRegulariser.consolidate()           [Phase 6.1]
├── 3. TaskRegistry.evict_lru()              [Phase 6.5]
└── 4. ReptileMetaLearner.meta_update()      [Phase 7.1]  ← NEW
         └── (only called if meta_learner is not None)
```

`ReptileMetaLearner` is optional — when not configured, `SLEEP_PHASE` behaves identically to Phase 6.5.

---

## Prometheus Metrics

| Metric | Type | Labels | PromQL Example |
|---|---|---|---|
| `asi_reptile_meta_updates_total` | Counter | — | `rate(asi_reptile_meta_updates_total[5m])` |
| `asi_reptile_inner_loss` | Histogram | `task_id` | `histogram_quantile(0.95, rate(asi_reptile_inner_loss_bucket[1h]))` |
| `asi_reptile_meta_loss` | Gauge | — | `asi_reptile_meta_loss` |
| `asi_reptile_param_norm` | Gauge | — | `asi_reptile_param_norm` |
| `asi_reptile_update_norm` | Gauge | — | `asi_reptile_update_norm` |
| `asi_reptile_tasks_per_batch` | Histogram | — | `histogram_quantile(0.5, rate(asi_reptile_tasks_per_batch_bucket[1h]))` |

**Cardinality guard**: `task_id` label is truncated to 16 characters, same pattern as Phase 6.5 `MultiTaskEWCRegulariser`.

---

## Test Targets (14)

| # | Test | Scope |
|---|---|---|
| 1 | `test_reptile_meta_learner_init_defaults` | Default hyperparams, Prometheus pre-init |
| 2 | `test_reptile_meta_update_single_task` | 1-task batch, param shift direction |
| 3 | `test_reptile_meta_update_batch` | 4-task batch, averaged update |
| 4 | `test_reptile_inner_steps_k_equals_1` | Degenerate case (no adaptation) |
| 5 | `test_reptile_inner_steps_k_equals_10` | Larger inner loop |
| 6 | `test_reptile_snapshot_restore_roundtrip` | Snapshot → mutate → restore → equality |
| 7 | `test_reptile_meta_lr_zero_no_update` | `meta_lr=0` leaves params unchanged |
| 8 | `test_reptile_task_sample_frozen` | `TaskSample` immutability |
| 9 | `test_reptile_prometheus_counters_increment` | Per-update metric assertions |
| 10 | `test_reptile_prometheus_histogram_labels` | `task_id` label cardinality guard |
| 11 | `test_reptile_ewc_integration` | EWC penalty applied during inner loop |
| 12 | `test_reptile_task_registry_integration` | `TaskContextManager` sets `task_id` during inner loop |
| 13 | `test_reptile_param_norm_finite` | No NaN/Inf after 100 updates |
| 14 | `test_reptile_concurrent_meta_updates` | `asyncio.gather(4 meta_update)` — no data race |

---

## Implementation Order

1. `asi/phase7/__init__.py` — package stub, version = "7.1.0"
2. `asi/phase7/meta_types.py` — `TaskSample`, `MetaParamSnapshot`, `ReptileMetaUpdateResult`
3. `asi/phase7/reptile.py` — `ReptileMetaLearner` (Prometheus pre-init, asyncio.Lock)
4. `tests/phase7/conftest.py` — shared fixtures: mock `base_learner`, `TaskSample` factory
5. `tests/phase7/test_meta_types.py` — dataclass invariants
6. `tests/phase7/test_reptile.py` — 14 test targets
7. `MemoryConsolidator` update — `_run_sleep_phase()` calls `meta_update()` when `meta_learner is not None`
8. `pyproject.toml` — `phase7` extras group (no new heavy deps if using pure numpy)

---

## Phase 7 Roadmap

| Sub-phase | Component | Status |
|---|---|---|
| **7.1** | `ReptileMetaLearner`, `TaskSample`, inner-loop adaptation | 🔵 Issue #259 |
| 7.2 | `TaskSampler` — curriculum scheduling, N-way K-shot sampling | Planned |
| 7.3 | Few-shot evaluation harness — N-way K-shot accuracy, confusion matrix | Planned |
| 7.4 | Meta-checkpoint store — persist/restore meta-params across restarts | Planned |
| 7.5 | Full SLEEP_PHASE integration tests — Reptile + EWC + TaskRegistry | Planned |

---

*Previous phase: [Multi-task EWC](Phase-6-Multi-Task-EWC) · [Phase 6 EWC Foundation](Phase-6-EWC-Foundation)*
