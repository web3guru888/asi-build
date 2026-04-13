# Phase 7.4 — Hypernetwork Context Modulation

**Status**: Open (Issue #269)  
**Phase**: 7.4 of 7.5  
**Dependencies**: Phase 7.1 (Reptile), Phase 7.2 (TaskSampler), Phase 7.3 (Replay Buffer), Phase 6 (EWC + Fisher)

---

## Motivation

Phases 6–7.3 answer *what to remember* (EWC consolidation) and *what to replay* (episodic replay). Phase 7.4 answers *how to adapt* instantly: given a context signal, generate weight perturbations in a **single forward pass** — no gradient steps, no inner loop.

This is the hypernetwork paradigm: a secondary network (the *hypernetwork*) generates the parameters (or parameter deltas) for a primary network (the base learner), conditioned on a context embedding.

---

## Architecture

```
dict (context)
    │
    ▼
ContextEncoder          ← feature-hash encoding → unit L2-norm vector
    │ context_embedding [D=64]
    ▼
HyperNetwork            ← 3-layer MLP: ReLU → ReLU → Linear
    │ delta_W, delta_b   ← L2-capped deltas
    ▼
HyperController
    ├── adapt()          ← deepcopy base weights → apply deltas
    └── restore_base()  ← revert to saved copy
         │
         ▼
  STDPOnlineLearner   ← temporarily patched weights during episode
```

---

## Components

### `ContextEncoder` (`asi/phase7/context_encoder.py`)

Encodes a context `dict` into a fixed-dim float32 unit vector using feature hashing.

```python
class ContextEncoder:
    def __init__(self, output_dim: int = 64, vocab: dict[str, int] | None = None) -> None:
        self._dim = output_dim
        self._vocab: dict[str, int] = vocab or {}
        self._lock = threading.Lock()

    def encode(self, context: dict[str, Any]) -> np.ndarray:
        vec = np.zeros(self._dim, dtype=np.float32)
        for k, v in context.items():
            idx = self._hash_key(k)
            if isinstance(v, (int, float)):
                vec[idx % self._dim] += float(v)
            else:
                v_idx = self._hash_key(str(v))
                vec[idx % self._dim] += 1.0
                vec[v_idx % self._dim] += 0.5
        norm = np.linalg.norm(vec)
        return vec / (norm + 1e-8)   # unit normalisation

    def _hash_key(self, s: str) -> int:
        return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)

    def update_vocab(self, keys: list[str]) -> None:
        with self._lock:
            for k in keys:
                self._vocab.setdefault(k, len(self._vocab))
```

**Key properties**:
- No vocabulary rebuild — new keys handled by hash collision
- O(1) per key, O(K) total where K = context keys
- Thread-safe `update_vocab()` via `threading.Lock`
- Output always unit-normalised (L2 norm = 1)

**`output_dim` selection guide**:

| Context complexity | Recommended `output_dim` |
|---|---|
| 1–5 keys | 32 |
| 6–30 keys | 64 (default) |
| 31–100 keys | 128 |
| >100 keys | 256 + vocab-based fallback |

---

### `HyperNetwork` (`asi/phase7/hyper_network.py`)

Pure-numpy MLP that maps context embeddings to parameter deltas.

```python
class HyperNetwork:
    def __init__(self, context_dim: int, target_param_count: int,
                 hidden_dims: list[int] = (128, 64), scale: float = 0.01) -> None:
        self._scale = scale
        self._target = target_param_count
        dims = [context_dim] + list(hidden_dims) + [target_param_count]
        # Xavier initialisation
        self._weights = [
            np.random.randn(dims[i], dims[i+1]).astype(np.float32)
            * np.sqrt(2.0 / dims[i])
            for i in range(len(dims) - 1)
        ]
        self._biases = [np.zeros(d, dtype=np.float32) for d in dims[1:]]

    def generate(self, ctx: np.ndarray) -> dict[str, np.ndarray]:
        x = ctx.copy()
        for W, b in zip(self._weights[:-1], self._biases[:-1]):
            x = np.maximum(0, x @ W + b)          # ReLU
        x = x @ self._weights[-1] + self._biases[-1]  # linear output
        # L2 cap: ||delta|| <= scale * sqrt(target_param_count)
        norm = np.linalg.norm(x)
        max_norm = self._scale * np.sqrt(self._target)
        if norm > max_norm:
            x = x * (max_norm / (norm + 1e-8))
        split = int(self._target * 0.8)        # 80% W, 20% b
        return {"delta_W": x[:split], "delta_b": x[split:]}
```

**Delta magnitude cap**:

```
max_norm = scale × √(target_param_count)
```

| scale | target_param_count | max_norm | Effect |
|---|---|---|---|
| 0.001 | 10_000 | 0.1 | Imperceptible |
| 0.01 | 10_000 | 1.0 | ~1% per weight (default) |
| 0.05 | 10_000 | 5.0 | ~5% per weight |
| 0.01 | 100_000 | 3.16 | Larger network |

---

### `HyperController` (`asi/phase7/hyper_controller.py`)

Orchestrates encoding → generation → patching → restore cycle.

```python
class HyperController:
    def __init__(self, base_learner: STDPOnlineLearner,
                 hyper_network: HyperNetwork,
                 context_encoder: ContextEncoder,
                 apply_mode: Literal["additive", "scale"] = "additive") -> None:
        self._learner = base_learner
        self._hyper = hyper_network
        self._encoder = context_encoder
        self._mode = apply_mode
        self._lock = asyncio.Lock()
        self._pre_patch: dict | None = None

    async def adapt(self, context: dict[str, Any]) -> None:
        async with self._lock:
            t0 = time.monotonic()
            ctx_vec = self._encoder.encode(context)
            HYPER_ENCODE_SECONDS.observe(time.monotonic() - t0)
            deltas = self._hyper.generate(ctx_vec)
            self._pre_patch = deepcopy(self._learner.get_weights())
            weights = self._learner.get_weights()
            dW = deltas["delta_W"].reshape(weights["W"].shape)
            if self._mode == "additive":
                weights["W"] = weights["W"] + dW
            else:  # scale
                weights["W"] = weights["W"] * (1.0 + dW)
            self._learner.set_weights(weights)
            HYPER_ADAPTATIONS.inc()
            HYPER_DELTA_MAG.observe(float(np.linalg.norm(deltas["delta_W"])))

    async def restore_base(self) -> None:
        async with self._lock:
            if self._pre_patch is not None:
                self._learner.set_weights(self._pre_patch)
                self._pre_patch = None
                HYPER_RESTORES.inc()
```

---

## Apply modes

| Mode | Formula | When to use |
|---|---|---|
| `additive` (default) | W′ = W + δW | Sparse, independent context signals; small deltas |
| `scale` | W′ = W × (1 + δW) | Gain-modulation; relative shifts; large task distribution |

---

## Hypernetwork vs other adaptation methods

| Property | Fine-tune (SGD) | Reptile (7.1) | Hypernetwork (7.4) |
|---|---|---|---|
| Adaptation latency | Many gradient steps | K inner steps | Single forward pass |
| Memory per task | Full model copy | Meta-parameter copy | Context vector only |
| Requires task labels | Yes | Yes (task batch) | Context dict only |
| Catastrophic forgetting risk | High | Mitigated by meta-update | Low (base unchanged after restore) |
| Composable with EWC | Indirectly | Via penalty | Naturally (base preserved) |

---

## SLEEP_PHASE hook order (Phase 7.1–7.4 cumulative)

```python
async def sleep_phase(learner, hyper_ctrl, replay_buf, reptile, task_sampler, task_ctx):
    # Phase 7.3: episodic replay
    batch = await replay_buf.sample(32)
    # ... replay gradient blend ...

    # Phase 7.1: Reptile meta-update
    await reptile.meta_update(task_batch)

    # Phase 7.2: task selection for next episode
    next_task = task_sampler.sample()

    # Phase 7.4: hypernetwork adapt ← NEW
    await hyper_ctrl.adapt(task_ctx)

    # Online inference episode (handled by caller)

    # Phase 7.4: restore base ← NEW
    await hyper_ctrl.restore_base()

    # Phase 6.4: online Fisher (on base weights)
    fisher_acc.step(learner)

    # Phase 6.3: EWC penalty
    penalty = ewc.penalty_gradient(learner)
```

> **Critical ordering**: `restore_base()` **must** precede `fisher_acc.step()`. Fisher information must be computed on base weights, not adapted weights.

---

## Prometheus metrics

| Metric | Type | Description | PromQL |
|---|---|---|---|
| `asi_hyper_adaptations_total` | Counter | Calls to `adapt()` | `rate(asi_hyper_adaptations_total[5m])` |
| `asi_hyper_restores_total` | Counter | Calls to `restore_base()` | `rate(asi_hyper_restores_total[5m])` |
| `asi_hyper_delta_magnitude` | Histogram | L2 norm of `delta_W` | `histogram_quantile(0.99, rate(asi_hyper_delta_magnitude_bucket[5m]))` |
| `asi_hyper_encode_seconds` | Histogram | `ContextEncoder.encode()` latency | `histogram_quantile(0.95, rate(asi_hyper_encode_seconds_bucket[5m]))` |

**Orphaned-patch alarm**:
```promql
1 - rate(asi_hyper_restores_total[5m]) / rate(asi_hyper_adaptations_total[5m])
```
Alert if > 0.01 (1% orphaned patches indicates `restore_base()` not being called consistently).

---

## Test targets (12)

```
tests/phase7/test_context_encoder.py
  test_encode_returns_unit_vector
  test_encode_same_context_deterministic
  test_encode_unknown_key_handled
  test_update_vocab_thread_safe

tests/phase7/test_hyper_network.py
  test_generate_returns_correct_shape
  test_generate_scale_cap_respected
  test_snapshot_restore_roundtrip

tests/phase7/test_hyper_controller.py
  test_adapt_patches_base_learner
  test_restore_base_undoes_patch
  test_concurrent_adapt_restore_safe
  test_apply_mode_scale
  test_factory_from_config
```

---

## Implementation order (10 steps)

1. `ContextEncoder` + `test_encode_*` (feature hash + unit norm)
2. `update_vocab` thread-safety test
3. `HyperNetwork.__init__` (Xavier init, dims)
4. `HyperNetwork.generate` (MLP forward + L2 cap)
5. `test_generate_*` (shape + magnitude assertions)
6. `HyperSnapshot` dataclass + `snapshot()`/`restore()` roundtrip test
7. `HyperController.__init__` + `asyncio.Lock`
8. `adapt()` + Prometheus instrumentation
9. `restore_base()` + orphan guard (`_pre_patch is not None` check)
10. `build_hyper_controller()` factory + `test_factory_from_config`

---

## Phase 7 roadmap

| Sub-phase | Issue | Status |
|---|---|---|
| 7.1 Reptile Meta-Learning | #259 | 🟡 Open |
| 7.2 TaskSampler & Curriculum | #262 | 🟡 Open |
| 7.3 Episodic Replay Buffer | #265 | 🟡 Open |
| **7.4 Hypernetwork Modulation** | **#269** | **🟡 Open** |
| 7.5 Sleep-Phase Orchestrator | (upcoming) | ⬜ Planned |

---

*See also: [Phase 6 EWC Foundation](Phase-6-EWC-Foundation), [Phase 7.1 Reptile](Phase-7-Meta-Learning), [Phase 7.2 TaskSampler](Phase-7-Task-Sampler), [Phase 7.3 Replay Buffer](Phase-7-Replay-Buffer)*
