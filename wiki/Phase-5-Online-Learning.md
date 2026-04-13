# Phase 5 Online Learning

This page documents the online learning subsystem introduced in Phase 5, covering `STDPOnlineLearner`, the `OnlineLearnerBase` ABC, the pluggable kernel protocol, `WeightUpdate` data model, and integration with the Phase 5 safety framework.

**Related issues**: #181 (STDPOnlineLearner), #210 (safety invariants), #208 (weight update strategy)  
**Related discussions**: #227 (STDP architecture), #228 (weight update strategy), #229 (pluggable kernels)  
**Related wiki**: [Phase-5-Safety-Invariants](Phase-5-Safety-Invariants), [Phase-5-Rollback-Runbook](Phase-5-Rollback-Runbook), [Phase-5-Prometheus-Integration](Phase-5-Prometheus-Integration)

---

## Architecture Overview

```
CognitiveCycle tick
        │
        ▼
STDPOnlineLearner.on_weight_update(WeightUpdate)
        │
        ├─► PlasticityKernel.__call__(pre_t, post_t, weight) → Δw
        │
        ├─► SafetyGate: delta_norm = ‖Δw‖ / (‖w‖ + ε)
        │       if delta_norm > MAX_DELTA_NORM (1.0):
        │           skip update → log warning
        │
        ├─► Apply update: w_new = w + Δw
        │
        ├─► Blackboard["phase5.learning.last_delta_norm"] = delta_norm
        │
        └─► Phase5MetricsExporter: phase5_stdp_weight_delta_norm.observe(delta_norm)
```

---

## Data Model

### `WeightUpdate`

```python
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

@dataclass
class WeightUpdate:
    source_module: str          # e.g. "perceptual_encoder", "pln_engine"
    target_module: str          # e.g. "working_memory", "goal_planner"
    pre_spike_time:  float      # ms; time of pre-synaptic event this tick
    post_spike_time: float      # ms; time of post-synaptic event this tick
    current_weight:  np.ndarray # Current weight tensor (shape: [pre_dim, post_dim])
    tick:            int = 0
    metadata:        dict = field(default_factory=dict)
```

**Key fields**:
- `pre_spike_time` / `post_spike_time` — millisecond timestamps within the tick window (0–100 ms by convention)
- `current_weight` — passed by reference; mutated in-place by the learner
- `metadata` — optional context (e.g. `{"phase": "PERCEIVE", "cycle_id": "abc123"}`)

---

## `OnlineLearnerBase` ABC

```python
from abc import ABC, abstractmethod

class OnlineLearnerBase(ABC):
    """Abstract base for all Phase 5 online weight update strategies."""

    @abstractmethod
    def on_weight_update(self, update: WeightUpdate) -> None:
        """Apply one weight update. Must be thread-safe."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state (eligibility traces, running averages, etc.)."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this learner (used in Blackboard keys and metrics)."""
        ...
```

---

## `STDPOnlineLearner`

### Full Skeleton

```python
import math, threading, numpy as np
from asi_build.phase5.online_learning.base import OnlineLearnerBase, WeightUpdate
from asi_build.phase5.online_learning.kernels import STDPKernel, PlasticityKernel

MAX_DELTA_NORM = 1.0  # Safety gate — see Issue #210

class STDPOnlineLearner(OnlineLearnerBase):
    def __init__(
        self,
        blackboard,
        kernel: PlasticityKernel | None = None,
        max_delta_norm: float = MAX_DELTA_NORM,
    ):
        self._blackboard    = blackboard
        self._kernel        = kernel or STDPKernel()
        self._max_delta_norm = max_delta_norm
        self._lock          = threading.Lock()

    @property
    def name(self) -> str:
        return "stdp_online_learner"

    def on_weight_update(self, update: WeightUpdate) -> None:
        with self._lock:
            # Check if rollback manager has frozen learning
            kernel_name = self._blackboard.get("phase5.learning.kernel", "stdp")
            if kernel_name == "frozen":
                return  # FrozenKernel — skip all updates during circuit-OPEN

            delta = self._kernel(
                pre_t=update.pre_spike_time,
                post_t=update.post_spike_time,
                weight=float(np.mean(update.current_weight)),
            )
            delta_w = np.full_like(update.current_weight, delta)

            # Safety gate (Issue #210)
            w_norm = np.linalg.norm(update.current_weight) + 1e-8
            delta_norm = np.linalg.norm(delta_w) / w_norm
            if delta_norm > self._max_delta_norm:
                self._blackboard.set(
                    "phase5.learning.last_delta_norm", float(delta_norm)
                )
                return  # Reject oversized update; metrics collector will see spike

            # Apply update
            update.current_weight += delta_w
            self._blackboard.set("phase5.learning.last_delta_norm", float(delta_norm))

    def reset(self) -> None:
        with self._lock:
            if hasattr(self._kernel, 'theta'):
                self._kernel.theta = 0.5  # Reset BCMKernel sliding threshold if applicable
```

---

## Pluggable Kernel Protocol

See Discussion #229 for the full design rationale.

### `PlasticityKernel` Protocol

```python
from typing import Protocol

class PlasticityKernel(Protocol):
    def __call__(self, pre_t: float, post_t: float, weight: float) -> float:
        """Return scalar Δw."""
        ...
```

### Built-in Kernels

| Kernel | Class | Best For | Key Params |
|--------|-------|----------|------------|
| **STDP** (default) | `STDPKernel` | Temporal correlation encoding | `A_plus=0.01`, `A_minus=0.012`, `tau_plus=20ms`, `tau_minus=20ms` |
| **BCM** | `BCMKernel` | Goal state maintenance; prevents runaway LTP | `lr=0.01`, `theta=0.5`, `theta_lr=0.001` |
| **Oja** | `OjaKernel` | KG embedding; PCA-like normalisation | `lr=0.01` |
| **Frozen** | `FrozenKernel` | Rollback circuit-OPEN phase (no updates) | — |

### Kernel Registry

```python
from asi_build.phase5.online_learning.kernels import (
    STDPKernel, BCMKernel, OjaKernel, FrozenKernel, KERNEL_REGISTRY
)

# KERNEL_REGISTRY["stdp"](A_plus=0.005)  →  STDPKernel(A_plus=0.005)
```

### Rollback Integration

`Phase5RollbackManager` swaps the active kernel via Blackboard during circuit transitions:

| Circuit state | Blackboard key | Value |
|--------------|---------------|-------|
| CLOSED (normal) | `phase5.learning.kernel` | `"stdp"` |
| OPEN (rollback) | `phase5.learning.kernel` | `"frozen"` |
| HALF_OPEN (recovery) | `phase5.learning.kernel` | `"stdp"` (restored) |

The swap is **epoch-boundary** (applied at the start of the next tick) to avoid mid-tick race conditions.

---

## Safety Invariants

| Invariant | Enforcement point | Threshold |
|-----------|-----------------|-----------|
| Max weight delta norm | `STDPOnlineLearner.on_weight_update()` safety gate | `delta_norm ≤ 1.0` |
| No updates during SLEEP_PHASE consolidation | `Blackboard["phase5.sleep.active"]` checked before write | Boolean gate |
| Frozen kernel during circuit-OPEN | `Blackboard["phase5.learning.kernel"] == "frozen"` check | Rollback manager writes |
| Weight snapshot before hot-reload | `Phase5RollbackManager._snapshot_weights()` | Before every `MODEL_HOT_RELOAD` |

---

## Test Targets

| Test | Description |
|------|-------------|
| `test_stdp_ltp` | `pre_t < post_t` → positive Δw |
| `test_stdp_ltd` | `post_t < pre_t` → negative Δw |
| `test_safety_gate_rejects_large_delta` | `delta_norm > 1.0` → weight unchanged |
| `test_frozen_kernel_no_update` | `Blackboard["phase5.learning.kernel"] = "frozen"` → weight unchanged |
| `test_bcm_theta_slides` | Multiple calls → `BCMKernel.theta` converges toward `mean(activation²)` |
| `test_oja_weight_normalisation` | Repeated Oja updates → weight vector magnitude stabilises |
| `test_concurrent_update_thread_safety` | 10 threads calling `on_weight_update()` simultaneously → no race |
| `test_kernel_swap_epoch_boundary` | Kernel swap not applied mid-tick; applied at start of next |
| `test_blackboard_delta_norm_written` | After each update, `Blackboard["phase5.learning.last_delta_norm"]` is set |
| `test_reset_clears_bcm_theta` | `reset()` restores BCM theta to 0.5 |

---

## Module Layout

```
asi_build/
└── phase5/
    └── online_learning/
        ├── __init__.py
        ├── base.py           # OnlineLearnerBase ABC, WeightUpdate dataclass
        ├── kernels.py        # PlasticityKernel Protocol, STDPKernel, BCMKernel, OjaKernel, FrozenKernel, KERNEL_REGISTRY
        ├── stdp_learner.py   # STDPOnlineLearner (concrete impl, uses kernel registry)
        └── tests/
            ├── test_stdp_learner.py
            └── test_kernels.py
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `phase5_stdp_weight_delta_norm` | Histogram | `source_module`, `target_module` | Distribution of per-update delta norms |
| `phase5_stdp_updates_total` | Counter | `kernel`, `accepted` | Total updates processed; `accepted=false` = safety gate rejection |
| `phase5_kernel_swaps_total` | Counter | `from_kernel`, `to_kernel` | Kernel swap events (e.g. stdp→frozen on circuit-OPEN) |

See [Phase-5-Prometheus-Integration](Phase-5-Prometheus-Integration) for the full metric reference and `Phase5MetricsExporter` skeleton.

---

## Related Pages

- [Phase-5-Safety-Invariants](Phase-5-Safety-Invariants)
- [Phase-5-Rollback-Runbook](Phase-5-Rollback-Runbook)
- [Phase-5-Prometheus-Integration](Phase-5-Prometheus-Integration)
- [Phase-5-Grafana-Dashboard](Phase-5-Grafana-Dashboard)
