# Phase 6 — EWC Foundation

> **Status**: Design complete (Issue #241) — implementation in progress
> **Phase**: 6.1 — Continual Learning Core
> **Depends on**: [Phase-5-Online-Learning](Phase-5-Online-Learning), [Phase-5-Memory-Consolidation](Phase-5-Memory-Consolidation)

## Overview

Elastic Weight Consolidation (EWC) is the Phase 6 continual-learning backbone. It prevents **catastrophic forgetting** — the tendency of neural systems to overwrite old memories when learning new tasks — by adding a penalty term that discourages weight changes that damage previously consolidated knowledge.

EWC was introduced by Kirkpatrick et al. (2017, DeepMind) and remains one of the most practically effective continual-learning algorithms for parameter-space methods.

## Why EWC for ASI:BUILD?

| Problem | EWC Solution |
|---------|-------------|
| STDP weight updates during LEARNING phase overwrite episodic memories | Fisher diagonal identifies which weights encode old memories → protect them |
| MemoryConsolidator writes episodes to Neo4j but weights drift away | EWC penalty anchors weights near θ* (post-consolidation snapshot) |
| SleepPhaseGuard pauses writes but not weight updates | `EWCRegulariser.consolidate()` called at SLEEP start — θ* snapshot taken |
| No visibility into forgetting | `phase6_fisher_diagonal_norm` Prometheus gauge shows parameter importance drift |

## Architecture

```
SLEEP_PHASE starts
  └─ MemoryConsolidator._run_sleep_consolidation()
       ├─ 1. Flush EpisodicEvent ring buffer → Neo4j UNWIND  (Phase 5)
       ├─ 2. FisherMatrixBase.compute(weight_deltas)          (Phase 6 NEW)
       ├─ 3. FisherMatrixBase.store(snapshot)                 (Phase 6 NEW)
       └─ 4. EWCRegulariser.consolidate(theta*, tick)         (Phase 6 NEW)

LEARNING phase (next cycle)
  └─ EWCRegulariser.penalty(theta_current) → subtracted from STDP update
```

## New Components

### `FisherSnapshot` (dataclass)

```python
@dataclass
class FisherSnapshot:
    parameter_id: str          # identifies the weight set (e.g. "stdp_layer_0")
    diagonal: np.ndarray       # shape (n_params,), dtype float32
    consolidation_tick: int    # CognitiveCycle tick at consolidation
    task_label: str = "default"
```

Serialisable to JSON via `diagonal.tolist()`. Stored in `InMemoryFisherStore` (bounded deque, last 10 snapshots).

### `FisherMatrixBase` ABC

| Method | Signature | Description |
|--------|-----------|-------------|
| `compute()` | `(weight_deltas: list[WeightUpdate]) → FisherSnapshot` | Estimate diagonal Fisher from recent deltas |
| `store()` | `(snapshot: FisherSnapshot) → None` | Persist for later retrieval |
| `load_latest()` | `(parameter_id: str) → FisherSnapshot \| None` | Most recent snapshot |

**Empirical Fisher approximation** (Phase 6.1):

```
F_i ≈ mean(delta_i²)  across last N WeightUpdate events
```

For STDP kernels (no explicit loss function), weight update variance serves as a proxy for Fisher information — sometimes called "synaptic intelligence".

### `InMemoryFisherStore`

Concrete implementation for Phase 6.1 MVP:
- Thread-safe via `asyncio.Lock`
- Bounded `deque(maxlen=10)` per `parameter_id`
- `load_latest()` returns most recent snapshot in O(1)
- `store()` automatically evicts oldest on overflow

### `EWCConfig` (dataclass)

```python
@dataclass
class EWCConfig:
    lambda_: float = 400.0   # regularisation strength
    online: bool = False     # accumulate Fisher across tasks
    gamma: float = 1.0       # online EWC decay factor
```

`lambda_ = 400.0` is tuned for `STDPOnlineLearner(A_plus=0.01, tau_plus=20ms)`.

**Lambda tuning guide**:

| System | Recommended λ |
|--------|--------------|
| High plasticity (A+=0.05) | 200–400 |
| Low plasticity (A+=0.005) | 1000–5000 |
| Frequent SLEEP cycles (< 100 ticks) | Lower (Fisher updates often) |
| Rare SLEEP cycles (> 500 ticks) | Higher (protect aggressively) |

### `EWCRegulariser`

Wraps any `OnlineLearnerBase` — drop-in replacement that adds EWC penalty:

```python
ewc = EWCRegulariser(
    learner=STDPOnlineLearner(...),
    fisher=InMemoryFisherStore(),
    config=EWCConfig(lambda_=400.0),
)
# Drop-in usage:
ewc.update(pre_spikes, post_spikes, dt)
penalty = ewc.penalty(theta_current)
```

**EWC penalty formula**:

```
L_EWC = (λ/2) × Σ_i F_i × (θ_i - θ*_i)²
```

With numerical stability guard: `diff = np.clip(theta - theta_star, -10.0, 10.0)`.

## Standard vs Online EWC

| Mode | Fisher accumulation | Use when |
|------|---------------------|----------|
| Standard (`online=False`) | Only most recent SLEEP snapshot | Single task stream, Phase 6.1 |
| Online (`online=True`) | `F = γ*F_prev + (1-γ)*F_curr` | Many sequential tasks (> 5 domains) |

Phase 6.1 uses `online=False` — a single consolidated Fisher snapshot is sufficient for the current STDP + episodic stream.

## Fisher Storage Backends

| Backend | Phase | Latency | Persistence | Notes |
|---------|-------|---------|-------------|-------|
| `InMemoryFisherStore` | 6.1 MVP | O(1) | None | Single-process |
| `RedisFisherStore` | 6.2 | < 1ms | Yes (AOF) | Multi-worker safe |
| `Neo4jFisherStore` | 6.3 | ~5ms | Yes | Same store as episodic graph |
| `NumpyFileFisherStore` | Offline | disk I/O | Yes | Batch / checkpointing |

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `phase6_ewc_consolidations_total` | Counter | `parameter_id` | EWC consolidation events |
| `phase6_fisher_diagonal_norm` | Gauge | `parameter_id` | L2 norm of current Fisher diagonal |
| `phase6_ewc_penalty_value` | Gauge | `parameter_id` | Most recent penalty value |
| `phase6_theta_star_delta_norm` | Gauge | `parameter_id` | L2 distance θ_current − θ* |

**Forgetting detection alert**:

```promql
phase6_fisher_diagonal_norm > 2 * avg_over_time(phase6_fisher_diagonal_norm[30m])
```

## Test Targets (10 required)

| Test | Layer | What it checks |
|------|-------|---------------|
| `test_fisher_snapshot_fields` | Unit | dataclass field types and defaults |
| `test_in_memory_store_fifo` | Unit | deque evicts oldest at maxlen=10 |
| `test_in_memory_store_latest` | Unit | load_latest returns most recent |
| `test_ewc_penalty_zero_before_consolidate` | Unit | penalty=0.0 when θ* is None |
| `test_ewc_penalty_nonzero_after_consolidate` | Unit | L2 penalty math correctness |
| `test_ewc_regulariser_consolidate_idempotent` | Unit | double-call does not corrupt θ* |
| `test_ewc_config_defaults` | Unit | λ=400.0, online=False, γ=1.0 |
| `test_memory_consolidator_hook_order` | Async unit | Fisher computed before EWC.consolidate() |
| `test_sleep_phase_guard_triggers_ewc` | Async unit | SleepPhaseGuard calls consolidate() |
| `test_prometheus_metrics_emitted` | Integration | counter + gauge present in registry |

## Module Placement

```
asi/
├── learning/
│   ├── base.py        # OnlineLearnerBase ABC (Phase 5, unchanged)
│   ├── stdp.py        # STDPOnlineLearner (Phase 5, unchanged)
│   ├── fisher.py      # NEW — FisherSnapshot, FisherMatrixBase, InMemoryFisherStore
│   └── ewc.py         # NEW — EWCConfig, EWCRegulariser
└── memory/
    └── consolidator.py  # MODIFIED — _run_sleep_consolidation() + EWC hook
```

## Implementation Order

1. `learning/fisher.py` — `FisherSnapshot` + `FisherMatrixBase` + `InMemoryFisherStore`
2. `learning/ewc.py` — `EWCConfig` + `EWCRegulariser`
3. Extend `MemoryConsolidator._run_sleep_consolidation()` with 4-step hook
4. Extend `SleepPhaseGuard` to call `EWCRegulariser.consolidate()`
5. Add Phase 6 Prometheus metrics to `Phase5MetricsExporter` (or new `Phase6MetricsExporter`)
6. Write 10 unit tests in `tests/unit/phase6/`

## Related Pages

- [Phase-5-Online-Learning](Phase-5-Online-Learning) — OnlineLearnerBase ABC, STDP kernel
- [Phase-5-Memory-Consolidation](Phase-5-Memory-Consolidation) — MemoryConsolidator, EpisodicEvent, SleepPhaseGuard
- [Phase-5-Safety-Invariants](Phase-5-Safety-Invariants) — weight delta validation, pheromone decay
- [Phase-5-Integration-Tests](Phase-5-Integration-Tests) — four-layer test strategy

## Related Issues & Discussions

- Issue #241 — Phase 6.1 EWC implementation
- Discussion #240 — Phase 6 planning (EWC options, Fisher storage)
- Discussion #243 — EWC Q&A (Fisher estimation, lambda tuning, STDP adaptation)
- Discussion #242 — Phase 5 test suite design (four-layer strategy)
