# Online Learning — Phase 5.1

**Status**: Planning | **Issue**: [#181](https://github.com/web3guru888/asi-build/issues/181) | **Discussion**: [#182](https://github.com/web3guru888/asi-build/discussions/182)

Phase 5.1 adds online learning to ASI:BUILD: modules update their internal parameters from live Blackboard events during the CognitiveCycle, without stopping or restarting.

---

## Overview

Today, ASI:BUILD modules are trained offline and loaded as fixed weights at startup. Phase 5.1 changes this: learning becomes a first-class `CyclePhase`, running between REASONING and MEMORY.

### New CyclePhase: LEARNING

```python
class CyclePhase(Enum):
    PERCEPTION    = "perception"
    PREPROCESSING = "preprocessing"
    REASONING     = "reasoning"
    LEARNING      = "learning"      # ← NEW in Phase 5.1
    MEMORY        = "memory"
    ACTION        = "action"
    SAFETY_CHECK  = "safety_check"
    AUDIT         = "audit"
    IDLE          = "idle"
```

The LEARNING phase processes buffered experience events and applies weight deltas to modules that support online updates.

---

## WeightDelta Dataclass

```python
@dataclass
class WeightDelta:
    module_name: str
    delta_type: Literal["stdp", "federated", "gradient"]
    payload: dict            # module-specific: {layer, weights} or {pre_post_pairs}
    magnitude: float         # L2 norm of the change — used by safety gate
    tick: int
    source: str              # "experience" | "federation" | "backprop"

    def to_audit_dict(self) -> dict:
        """Hash payload, not raw weights — for audit trail."""
        import hashlib, json
        return {
            "module": self.module_name,
            "type": self.delta_type,
            "magnitude": self.magnitude,
            "payload_hash": hashlib.sha256(
                json.dumps(self.payload, sort_keys=True).encode()
            ).hexdigest(),
        }
```

---

## OnlineLearningAdapter

The central class. It:

1. Subscribes to `experience.*` Blackboard entries written during PERCEPTION/REASONING
2. Computes weight deltas using the module's native learning rule
3. Routes each delta through `EthicalVerificationEngine` (safety gate — see [Issue #176](https://github.com/web3guru888/asi-build/issues/176) constraint)
4. Applies approved deltas atomically; rolls back on rejection

```python
class OnlineLearningAdapter:
    """Bridges experience events to live module weight updates, safety-gated."""

    MAX_DELTA_NORM = {
        "stdp": 0.1,
        "federated": 0.5,
        "gradient": 0.2,
    }

    async def apply_delta(self, delta: WeightDelta) -> bool:
        """Apply a weight delta if safety gate approves."""
        context = EthicalContext(
            action_type="weight_update",
            module_name=delta.module_name,
            payload=delta.to_audit_dict(),
            magnitude=delta.magnitude,
        )
        verdict = await self.safety_gate.verify(context)
        if not verdict.approved:
            blackboard.write(
                "safety.weight_update_blocked",
                {"module": delta.module_name, "reason": verdict.reason,
                 "tick": delta.tick},
                ttl=300,
            )
            return False
        await self._apply_atomic(delta)
        blackboard.write(
            f"learning.{delta.delta_type}_update",
            {"module": delta.module_name, "tick": delta.tick,
             "norm": delta.magnitude},
            ttl=600,
        )
        return True

    async def _apply_atomic(self, delta: WeightDelta) -> None:
        """Apply under write lock to prevent partial updates."""
        async with self._weight_lock:
            self._rollback_buffer = copy.deepcopy(self._weights)
            try:
                self._module.apply_delta(delta)
            except Exception:
                self._weights = self._rollback_buffer
                raise
```

---

## STDP Mid-Cycle Updates

The neuromorphic module already implements STDP learning rules. Phase 5.1 wires these into the live CognitiveCycle:

```
CognitiveCycle PERCEPTION phase
  → NeuromorphicBlackboardAdapter writes spike events to "neuromorphic.spikes"

CognitiveCycle LEARNING phase
  → OnlineLearningAdapter reads "neuromorphic.spikes"
  → Computes STDP Δw for each pre-post spike pair
  → Routes through EthicalVerificationEngine (MAX_DELTA_NORM["stdp"] = 0.1)
  → Applies Δw to live SNN weights
  → Writes "learning.stdp_update" to Blackboard (TTL=600s)
```

**Performance target**: STDP delta computation for 1K-neuron network ≤ 5ms.

---

## Federated Hot-Reload

Applies aggregated federated model updates without restarting:

```
FederatedOrchestrator receives aggregated global model update
  → Byzantine filter (DBSCAN outlier removal — existing module capability)
  → Wraps as WeightDelta(delta_type="federated", ...)
  → Routes through EthicalVerificationEngine (MAX_DELTA_NORM["federated"] = 0.5)
  → On approval: atomic weight swap (write lock, no partial update)
  → On rejection: rollback (_pending_weight_buffer discarded)
  → Writes "learning.federated_update" to Blackboard
```

Default schedule: every 100 ticks (≈ 10s at 10Hz).

---

## KG Transactional Writes

When a module learns a new high-confidence association (> 0.85), it writes to both the Knowledge Graph and Blackboard atomically:

```python
async def record_learned_association(
    self,
    subject: str,
    relation: str,
    object_: str,
    confidence: float,
    source_module: str,
) -> None:
    """Write a newly learned relation to KG + Blackboard atomically."""
    async with kg.transaction() as tx:
        tx.add_triple(
            subject, relation, object_,
            confidence=confidence,
            valid_from=datetime.utcnow(),
        )
    blackboard.write(
        f"learning.new_association.{source_module}",
        {"triple": (subject, relation, object_), "confidence": confidence},
        ttl=3600,
    )
```

The bi-temporal KG records `valid_from` = original event timestamp and `transaction_time` = consolidation timestamp.

---

## Safety Gate Design

All weight updates go through `EthicalVerificationEngine` before application:

| Delta type | MAX_DELTA_NORM | What safety gate checks |
|---|---|---|
| STDP | 0.1 | Magnitude, no forbidden spike associations |
| Federated | 0.5 | Byzantine pre-filter already applied + magnitude |
| Gradient | 0.2 | Gradient clipping already applied; magnitude final check |

If safety gate rejects, `safety.weight_update_blocked` is written to the Blackboard. Weights are unchanged.

---

## Blackboard Namespace Additions (Phase 5.1)

| Key | TTL | Producer | Consumer |
|---|---|---|---|
| `learning.stdp_update` | 600s | OnlineLearningAdapter | CognitiveSynergy, dashboard |
| `learning.federated_update` | 600s | FederatedOrchestrator | Multi-Agent, dashboard |
| `learning.new_association.*` | 3600s | OnlineLearningAdapter | KnowledgeEngine, Memory |
| `safety.weight_update_blocked` | 300s | OnlineLearningAdapter | Safety dashboard, audit |
| `experience.*` | 60s | PERCEPTION phase | LEARNING phase |

---

## Acceptance Criteria

From [Issue #181](https://github.com/web3guru888/asi-build/issues/181):

- [ ] `OnlineLearningAdapter` class with `apply_delta()` and safety gate wiring
- [ ] STDP deltas written to `learning.stdp_update` after each successful apply
- [ ] Safety gate blocks updates with `magnitude > MAX_DELTA_NORM[type]`
- [ ] Federated hot-reload applies aggregated weights atomically (no partial update)
- [ ] Rollback on safety rejection: weights unchanged if `EthicalVerificationEngine` rejects
- [ ] KG transactional write: `record_learned_association()` with `async with kg.transaction()`
- [ ] `learning.stdp_update` Blackboard entries readable during `CyclePhase.LEARNING`
- [ ] 8+ unit tests: normal apply, safety block, Byzantine filter, rollback, KG write, concurrent apply

---

## Implementation Order

1. Add `WeightDelta` dataclass and `OnlineLearningAdapter` skeleton
2. Wire STDP delta extraction from `NeuromorphicBlackboardAdapter` spike events
3. Add safety gate integration (reuse `SafetyBlackboardAdapter` pattern from [#37](https://github.com/web3guru888/asi-build/issues/37))
4. Add federated hot-reload with atomic weight swap
5. Add KG transactional write helper
6. Add `CyclePhase.LEARNING` to `CognitiveCycle` tick pipeline
7. Write 8+ unit tests

---

## Dependencies

| Dependency | Reason |
|---|---|
| [#44](https://github.com/web3guru888/asi-build/issues/44) PLN sub-engine | PLN inference tables must be finalized before online updates |
| [#54](https://github.com/web3guru888/asi-build/issues/54) Neuromorphic benchmarks | STDP convergence baseline for update quality validation |
| [#164](https://github.com/web3guru888/asi-build/issues/164) Production deployment | Staging environment for live learning tests |

---

## Related

- [Phase 5 Roadmap](Phase-5-Roadmap)
- [Phase-5-Roadmap#milestone-51](Phase-5-Roadmap#milestone-51--online-learning-integration)
- [Bio-Inspired Module](Bio-Inspired#learning-rules) — STDP/BCM rules
- [Federated Learning](Federated-Learning#byzantine-robust-aggregation) — Byzantine filter
- [Safety Module](Safety-Module) — EthicalVerificationEngine
- [Health Monitoring](Health-Monitoring) — CycleFaultSummary for learning phase faults
