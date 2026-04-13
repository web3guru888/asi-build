# Phase 5 Rollback Runbook

This runbook documents the automatic and manual recovery procedures for the four Phase 5 failure scenarios. Intended for operators and contributors working with live ASI:BUILD deployments.

**Related issues**: [#215 (metrics)](https://github.com/web3guru888/asi-build/issues/215) | [#216 (rollback manager)](https://github.com/web3guru888/asi-build/issues/216) | [#210 (safety invariants)](https://github.com/web3guru888/asi-build/issues/210)

---

## Quick Reference

| Scenario | Trigger | Automatic action | Manual fallback |
|----------|---------|-----------------|-----------------|
| A: Weight regression | `weight_delta_norm_p95 > 0.8` sustained 10 ticks | Open `circuit.online_learning` | Restart `STDPOnlineLearner` |
| B: Hot-reload failure | `hot_reload_success_rate < 0.90` × 5 consecutive | Broadcast revert to last-good snapshot | Manual `MODEL_HOT_RELOAD` revert |
| C: KG conflict storm | `kg_write_conflict_rate > 0.10` sustained 20 ticks | Pause `MemoryConsolidator` | Clear conflict log, resume |
| D: Planner divergence | `phi_acceptance_rate < 0.60` sustained 100 ticks | Switch planner to FIFO mode | Manual planner mode reset |

---

## Diagnostic Checklist

Before investigating a specific scenario, run this Blackboard read sequence:

```python
# 1. Check active circuit breakers
bb.read("circuit.online_learning.state")   # None, OPEN, HALF_OPEN, or CLOSED
bb.read("circuit.online_learning.reason")  # why it opened

# 2. Check Phase 5 metrics (TTL=5 ticks — None means stale)
bb.read_prefix("metrics.phase5.")

# 3. Check rollback status
bb.read("memory.consolidation.paused")
bb.read("metrics.phase5.consciousness.planner_mode")  # "PHI_WEIGHTED" or "FALLBACK"

# 4. Check last-good weight snapshots
bb.read_prefix("learning.weight_snapshots.")
```

---

## Scenario A — STDP Weight Regression

### Trigger conditions

| Metric | WARNING (50-tick sustain) | CRITICAL (10-tick sustain) |
|--------|--------------------------|---------------------------|
| `weight_delta_norm_p95` | > 0.3 | > 0.8 |
| `safety_gate_rejection_rate` | > 0.05 | > 0.20 |

### Automatic recovery sequence

```
[Tick N]   weight_delta_norm_p95 > 0.8  (streak = 1)
...
[Tick N+9] weight_delta_norm_p95 > 0.8  (streak = 10) → TRIGGER
           Phase5RollbackManager writes:
             circuit.online_learning.state = OPEN
             circuit.online_learning.reason = "weight_delta_norm_p95 exceeded 0.8"
             circuit.online_learning.reset_at = now() + 30s
[Tick N+10] STDPOnlineLearner reads OPEN → returns None (no update)
...
[T+30s]    Circuit moves to HALF_OPEN
[T+30s+1]  One test update through safety gate
           If accepted → CLOSED (learning resumes)
           If rejected → OPEN for another 30s
```

### Manual intervention (if circuit stays OPEN > 5 minutes)

```python
# Force circuit reset only when metrics confirm recovery
bb.write("circuit.online_learning.state", CircuitState.CLOSED)
bb.write("circuit.online_learning.reset_at", None)
```

### Root cause investigation

- **NaN/inf in weight tensor**: Add `assert not torch.isnan(delta).any()` before safety gate call
- **STDP rate too high**: Reduce `learning_rate` in `STDPOnlineLearner` config
- **Safety gate too loose**: Tighten `MAX_DELTA_NORM` from 1.0 toward 0.5 and observe rejection rate

---

## Scenario B — Federated Hot-Reload Failure

### Trigger condition

5 consecutive `MODEL_HOT_RELOAD` events with `status=failed` on the Blackboard.

### Automatic recovery sequence

```
[Event 5]  hot_reload_success_rate < 0.90 for 5 consecutive failures
           Phase5RollbackManager reads:
             learning.weight_snapshots.<agent_id>.last_good → sha
           Broadcasts MODEL_HOT_RELOAD:
             {"action": "revert", "checkpoint": "<sha>"}
           Each agent:
             STDPOnlineLearner.load_weights(snapshot) ← < 1 tick
             Writes learning.weight_snapshots.<agent_id>.reverted = True
```

### Verifying revert succeeded

```python
for agent_id in mesh.agent_ids:
    reverted = bb.read(f"learning.weight_snapshots.{agent_id}.reverted")
    print(f"{agent_id}: reverted={reverted}")
```

### Manual revert (if automatic recovery failed)

```python
mesh_coordinator.broadcast_event("MODEL_HOT_RELOAD", {
    "action": "revert",
    "checkpoint": bb.read(f"learning.weight_snapshots.{agent_id}.last_good").sha
})
```

### Root cause investigation

- Check `learning.hot_reload.events.<event_id>` for `error_message`
- Common causes: weight tensor shape mismatch, checkpoint file missing, network partition in federated setup

---

## Scenario C — KG Write Conflict Storm

### Trigger condition

`kg_write_conflict_rate > 0.10` sustained for 20 ticks.

### Automatic recovery sequence

```
[Tick N+19] kg_write_conflict_rate > 0.10 (streak = 20) → TRIGGER
            Phase5RollbackManager writes:
              memory.consolidation.paused = True
            MemoryConsolidator reads flag → stops new KG writes
            In-flight transactions settle (≤ 1 SLEEP_PHASE cycle)
            Conflict detector analyzes hot nodes
            Quarantines hot nodes (SLEEP_PHASE lock required)
            Resumes at reduced cadence (every 2 SLEEP_PHASEs)
```

### Resuming consolidation manually

```python
bb.write("memory.consolidation.paused", False)
```

### Root cause investigation

- Identify hot nodes via `bb.read_prefix("memory.kg_conflict_log.")`
- Hot nodes are written by multiple subsystems simultaneously without `SLEEP_PHASE` lock
- Fix: add `SLEEP_PHASE` gate around all writes to hot KG nodes (see [#186](https://github.com/web3guru888/asi-build/issues/186))

---

## Scenario D — ConsciousnessPlanner Divergence

### Trigger condition

`phi_weighted_goal_acceptance_rate < 0.60` sustained for 100 ticks (1 second at 100Hz).

### Automatic recovery sequence

```
[Tick N+99] phi_acceptance < 0.60 (streak = 100) → TRIGGER
            Phase5RollbackManager writes:
              metrics.phase5.consciousness.planner_mode = "FALLBACK"
            ConsciousnessPlanner → switches to FIFO goal ordering
            Monitoring continues each tick...
[Tick M]    phi_acceptance > 0.80 (recovery streak = 1)
...
[Tick M+199] phi_acceptance > 0.80 (recovery streak = 200) → AUTO-RESUME
             Phase5RollbackManager writes:
               metrics.phase5.consciousness.planner_mode = "PHI_WEIGHTED"
```

### Manual mode override

```python
# Force PHI_WEIGHTED mode when metrics confirm recovery
bb.write("metrics.phase5.consciousness.planner_mode", "PHI_WEIGHTED")
```

### Root cause investigation

- Check `consciousness.iit.phi` — if Φ < 0.1, system is in low-consciousness state (expected behavior, not a bug)
- Check `gwt_broadcast_latency_p99` — if > 150ms, planner uses stale Φ data; fix GWTInferenceBridge scheduling
- Check `ConsciousnessPlanner` goal queue — if empty, no proposals to accept (not a bug)

---

## Alert Severity Reference

| Alert level | Response time | Action required |
|-------------|---------------|----------------|
| WARNING | Monitor | No immediate action; watch for escalation |
| CRITICAL | < 5 minutes | Verify automatic recovery triggered; check Blackboard |
| CIRCUIT OPEN | Immediate | Confirm `reset_at` is set; if > 5 min without recovery, investigate manually |
| FALLBACK MODE | < 10 minutes | Verify recovery streak is counting up; if not, check GWTInferenceBridge |

---

## Related Wiki Pages

- [Phase-5-Safety-Invariants](https://github.com/web3guru888/asi-build/wiki/Phase-5-Safety-Invariants) — weight delta bounds, pheromone decay, sleep exclusivity
- [Phase-5-Evaluation](https://github.com/web3guru888/asi-build/wiki/Phase-5-Evaluation) — metrics specification and thresholds
- [Fault-Tolerance](https://github.com/web3guru888/asi-build/wiki/Fault-Tolerance) — Phase 4 circuit breaker pattern
- [Health-Monitoring](https://github.com/web3guru888/asi-build/wiki/Health-Monitoring) — CycleFaultSummary and SSE stream
- [Phase-5-Integration](https://github.com/web3guru888/asi-build/wiki/Phase-5-Integration) — full Phase 5 wiring guide
