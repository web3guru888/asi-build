# Phase 5 Evaluation Framework

**Status**: Design | **Issue**: [#215](https://github.com/web3guru888/asi-build/issues/215) | **Discussion**: [#213](https://github.com/web3guru888/asi-build/discussions/213)

Phase 5 adds self-modification to ASI:BUILD. This page defines the evaluation framework that measures whether online learning is working — or drifting.

---

## The Measurement Problem

Phase 5 operates on a live CognitiveCycle. Unlike offline training, we cannot pause the system to compute validation loss. All metrics must be:

- **Non-intrusive** — computed from Blackboard reads, not requiring a held-out dataset
- **Continuous** — updated every N ticks, not after a training epoch
- **Actionable** — crossing a threshold triggers automatic rollback or alert

---

## `Phase5MetricsCollector`

Lives in `integration/phase5_metrics.py`. Called by `CognitiveCycle` at the end of each tick, after the `ONLINE_LEARNING` tier.

```python
class Phase5MetricsCollector:
    async def on_tick(self, tick_id: int) -> None:
        await self._collect_online_learning_metrics()
        await self._collect_coordination_metrics()
        await self._collect_memory_metrics()
        await self._collect_consciousness_metrics()
        if tick_id % 1000 == 0:
            await self._push_to_prometheus()
```

All metrics written to Blackboard under `metrics.phase5.<subsystem>.<name>` with a 5-tick TTL.

---

## Metrics by Milestone

### 5.1 Online Learning

| Blackboard key | Definition | Warning | Critical |
|---|---|---|---|
| `online_learning.weight_delta_norm_p95` | P95 Frobenius norm of accepted WeightDelta (sliding 1000-tick window) | > 0.3 | > 0.8 |
| `online_learning.safety_gate_rejection_rate` | Fraction of WeightDelta rejected (sliding 1000-tick window) | > 0.05 | > 0.20 |
| `online_learning.hot_reload_success_rate` | Fraction of MODEL_HOT_RELOAD events completing without rollback | < 0.98 | < 0.90 |
| `online_learning.stdp_convergence_window` | Ticks until STDP weight variance < 0.01 after spike burst | > 500 | > 2000 |

### 5.2 Emergent Coordination

| Blackboard key | Definition | Warning | Critical |
|---|---|---|---|
| `coordination.coalition_size_mean` | Mean agent count per formed coalition | > 8 | > 16 |
| `coordination.role_negotiation_rounds` | Mean rounds to stable role assignment | > 4 | > 10 |
| `coordination.task_allocation_latency_p99` | Task arrival → first agent assignment (ms) | > 200 | > 500 |

### 5.3 Persistent Memory

| Blackboard key | Definition | Warning | Critical |
|---|---|---|---|
| `memory.episodic_consolidation_rate` | Fraction of eligible episodes consolidated per SLEEP_PHASE | < 0.90 | < 0.70 |
| `memory.kg_write_conflict_rate` | Fraction of KG writes requiring rollback | > 0.02 | > 0.10 |

### 5.4 Consciousness-Guided Planning

| Blackboard key | Definition | Warning | Critical |
|---|---|---|---|
| `consciousness.phi_weighted_goal_acceptance_rate` | Fraction of high-Φ goal proposals accepted | < 0.80 | < 0.60 |
| `consciousness.gwt_broadcast_latency_p99` | GWTInferenceBridge → ConsciousnessPlanner latency (ms) | > 50 | > 150 |

---

## Alert Integration

When any metric crosses CRITICAL threshold, `Phase5MetricsCollector` writes a `CIRCUIT_OPEN` event to Blackboard:

```python
self.bb.write("circuit.online_learning.state", CircuitState.OPEN)
self.bb.write("circuit.online_learning.reason", reason_string)
self.bb.write("circuit.online_learning.reset_at", utc_now() + timedelta(seconds=30))
```

The relevant `OnlineLearningAdapter` subclass reads this entry and returns `None` from `compute_update()` until the circuit resets. This reuses the `CircuitState` enum from the Phase 4 circuit breaker ([#137](https://github.com/web3guru888/asi-build/issues/137)).

---

## Prometheus Integration

Phase 5 reuses the Phase 4.3 Prometheus exporter from [#164](https://github.com/web3guru888/asi-build/issues/164).

```
# Gauges
asi_build_weight_delta_norm_p95
asi_build_safety_gate_rejection_rate
asi_build_episodic_consolidation_rate
asi_build_phi_weighted_goal_acceptance_rate

# Histograms
asi_build_task_allocation_latency_seconds{buckets=[0.01,0.05,0.1,0.2,0.5,1.0]}
asi_build_gwt_broadcast_latency_seconds{buckets=[0.005,0.01,0.025,0.05,0.1,0.25]}
```

Prometheus push cadence: every 1000 ticks (≈10s at 100Hz), in a background `asyncio.Task`.

---

## Sliding Window Implementation

All rate/P95 metrics use `collections.deque(maxlen=1000)`:

```python
self._delta_norms: deque[float] = deque(maxlen=1000)
```

This gives a rolling 10-second view without unbounded memory growth.

---

## Related

- [Phase 5 Roadmap](Phase-5-Roadmap)
- [Phase 5 Safety Invariants](Phase-5-Safety-Invariants)
- [Online Learning](Online-Learning)
- [Fault Tolerance](Fault-Tolerance)
- [Health Monitoring](Health-Monitoring)
- [Production Deployment](Production-Deployment)
