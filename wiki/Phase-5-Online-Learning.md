# Phase 5 Online Learning

Online learning is Phase 5.1 of the ASI:BUILD roadmap. It enables the system to **update neural network weights mid-cycle** — without full retraining — using spike-timing-dependent plasticity (STDP) rules and federated hot-reload.

## Architecture

```
STDPOnlineLearner
│
├── compute_stdp_kernel(pre_spike, post_spike)
│   ├── LTP: Δw = A+ × exp(-Δt / τ+)  if Δt > 0  (post after pre)
│   └── LTD: Δw = A- × exp(-Δt / τ-)  if Δt < 0  (post before pre)
│
├── Safety gate
│   └── assert delta.norm() < MAX_DELTA_NORM = 1.0
│       raises WeightUpdateRejected if exceeded
│
└── WeightUpdate emission
    ├── Blackboard.write("phase5.learning.weight_update", update)
    └── MeshCoordinator._on_weight_delta() → MODEL_HOT_RELOAD broadcast
```

## OnlineLearnerBase ABC

All online learning strategies implement the `OnlineLearnerBase` interface:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

@dataclass
class WeightUpdate:
    """A validated weight delta ready for application."""
    layer:      str
    delta:      np.ndarray
    delta_norm: float
    kernel:     str              # "stdp" | "federated" | "ewc"
    tick:       int
    metadata:   dict = field(default_factory=dict)

class OnlineLearnerBase(ABC):
    """Abstract base for all Phase 5 online learning strategies."""

    MAX_DELTA_NORM: float = 1.0  # safety invariant — see #210

    @abstractmethod
    async def compute_update(self, pre_spikes: np.ndarray, post_spikes: np.ndarray) -> WeightUpdate:
        """Compute a weight delta without applying it."""
        ...

    @abstractmethod
    async def apply_pending_updates(self) -> list[WeightUpdate]:
        """Apply all pending updates; return list of applied updates."""
        ...

    def _safety_gate(self, update: WeightUpdate) -> None:
        """Raise WeightUpdateRejected if delta exceeds safety threshold."""
        if update.delta_norm > self.MAX_DELTA_NORM:
            raise WeightUpdateRejected(
                f"delta_norm={update.delta_norm:.3f} exceeds MAX_DELTA_NORM={self.MAX_DELTA_NORM}"
            )
```

## STDPOnlineLearner Implementation Sketch

```python
class STDPOnlineLearner(OnlineLearnerBase):
    """Spike-Timing-Dependent Plasticity online learner."""

    # STDP kernel parameters (biological defaults)
    A_PLUS:  float = 0.01   # LTP amplitude
    A_MINUS: float = 0.012  # LTD amplitude (slightly stronger — weight decay bias)
    TAU_PLUS:  float = 20.0  # ms — LTP time constant
    TAU_MINUS: float = 20.0  # ms — LTD time constant

    def __init__(self, blackboard):
        self._blackboard = blackboard
        self._pending: list[WeightUpdate] = []

    async def compute_update(
        self, pre_spikes: np.ndarray, post_spikes: np.ndarray
    ) -> WeightUpdate:
        dt = post_spikes - pre_spikes  # spike time differences (ms)

        ltp_mask = dt > 0
        ltd_mask = dt < 0

        delta = np.zeros_like(dt)
        delta[ltp_mask] = self.A_PLUS  * np.exp(-dt[ltp_mask]  / self.TAU_PLUS)
        delta[ltd_mask] = -self.A_MINUS * np.exp( dt[ltd_mask]  / self.TAU_MINUS)

        update = WeightUpdate(
            layer="stdp_target",
            delta=delta,
            delta_norm=float(np.linalg.norm(delta)),
            kernel="stdp",
            tick=self._blackboard.current_tick,
        )
        self._safety_gate(update)   # raises WeightUpdateRejected if > 1.0
        self._pending.append(update)
        return update

    async def apply_pending_updates(self) -> list[WeightUpdate]:
        applied, self._pending = self._pending, []
        for update in applied:
            self._blackboard.write(
                "phase5.learning.weight_update", update, ttl=200
            )
        return applied
```

## STDP Kernel Parameters

| Parameter | Default | Biology | Notes |
|-----------|---------|---------|-------|
| `A+` | 0.01 | 0.005–0.02 | LTP amplitude |
| `A-` | 0.012 | 0.005–0.025 | LTD amplitude (depression slightly > potentiation) |
| `τ+` | 20 ms | 10–40 ms | LTP time window |
| `τ-` | 20 ms | 10–40 ms | LTD time window |
| `MAX_DELTA_NORM` | 1.0 | — | Safety gate (cross-phase invariant from #210) |

## Integration with CognitiveCycle

Phase 5.1 adds a `LEARNING` phase to `CognitiveCycle` (see #233 for full wiring spec):

```
REASONING → [LEARNING] → INTEGRATION
               │
               └── STDPOnlineLearner.apply_pending_updates()
                       └── Blackboard.write("phase5.learning.weight_update", ...)
                               └── MeshCoordinator broadcasts MODEL_HOT_RELOAD
```

The `LEARNING` phase runs **after** `REASONING` (so ConsciousnessPlanner goal updates influence which layers learn) and **before** `INTEGRATION` (so the weight update itself can be recorded as a high-salience event if `delta_norm > 0.7`).

## Safety Invariants

Derived from the cross-cutting safety spec in #210:

| Invariant | Value | Enforcement |
|-----------|-------|-------------|
| Max delta norm | `delta_norm ≤ 1.0` | `OnlineLearnerBase._safety_gate()` |
| SLEEP_PHASE exclusivity | STDP disabled during SLEEP_PHASE | `CyclePhaseguard` check |
| Frozen kernel during rollback | `phase5.learning.kernel == "frozen"` | `Phase5RollbackManager` circuit open |
| Weight snapshot before hot-reload | Snapshot saved to Blackboard before `MODEL_HOT_RELOAD` | `MeshCoordinator._on_weight_delta()` |

## Acceptance Criteria

From #181:

- [ ] `WeightUpdate` dataclass with `layer`, `delta`, `delta_norm`, `kernel`, `tick`, `metadata`
- [ ] `OnlineLearnerBase` ABC with `compute_update()` and `apply_pending_updates()`
- [ ] `STDPOnlineLearner` with biological default parameters
- [ ] STDP kernel: LTP for `Δt > 0`, LTD for `Δt < 0`, zero for `Δt == 0`
- [ ] Safety gate: `WeightUpdateRejected` if `delta_norm > MAX_DELTA_NORM`
- [ ] Blackboard write: `phase5.learning.weight_update` with TTL=200
- [ ] 10+ tests: kernel shape, LTP/LTD polarity, safety gate, zero-delta, large-batch, frozen kernel

## Test Targets

```python
def test_ltp_for_positive_dt(): ...           # post after pre → positive delta
def test_ltd_for_negative_dt(): ...           # pre after post → negative delta
def test_zero_delta_for_simultaneous(): ...   # Δt == 0 → delta = 0
def test_safety_gate_rejects_large_norm(): ...
def test_safety_gate_passes_small_norm(): ...
def test_pending_queue_cleared_after_apply(): ...
def test_blackboard_write_on_apply(): ...
def test_frozen_kernel_no_apply(): ...
def test_kernel_parameters_configurable(): ...
def test_multiple_layers(): ...
```

## Related

- **Issue**: [#181 — Phase 5.1 online learning](../issues/181)
- **Issue**: [#233 — Phase 5 CognitiveCycle wiring](../issues/233)
- **Issue**: [#210 — Cross-cutting safety invariants](../issues/210)
- **Discussion**: [#231 — Phase 5 tick walkthrough](../discussions/231)
- **Discussion**: [#208 — Online learning weight update strategy](../discussions/208)
- **Wiki**: [Phase-5-Safety-Invariants](Phase-5-Safety-Invariants)
- **Wiki**: [Phase-5-Rollback-Runbook](Phase-5-Rollback-Runbook)

