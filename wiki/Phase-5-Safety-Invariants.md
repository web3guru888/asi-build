# Phase 5 Safety Invariants

Phase 5 introduces three new runtime behaviors to the ASI:BUILD cognitive loop — **online learning weight updates** (5.1), **stigmergic pheromone coordination** (5.2), and **persistent memory consolidation** (5.3). Each requires safety invariants enforced at the Cognitive Blackboard level.

These invariants extend the existing `SafetyBlackboardAdapter` (Issue #37) rather than adding a separate safety layer.

---

## Invariant 1: Weight Delta Validation

**Rule**: Every `WeightDelta` payload written to `learning.weight_delta.*` must pass through `SafetyBlackboardAdapter` validation before any agent applies it.

**Threat model**: An adversarially-crafted weight update could disable safety constraints in the safety module itself, or push a module into an unsafe parameter regime that bypasses ethical verification.

### GATED_TYPES extension

```python
GATED_TYPES = {
    "action_proposal",
    "goal_update",
    "agent_directive",
    "policy_change",
    "weight_delta",    # NEW — Phase 5.1
    "model_reload",    # NEW — Phase 5.1
}
```

### Validation logic

```python
async def _validate_weight_delta(self, delta: WeightDelta) -> bool:
    """Validate that weight updates are safe to apply."""
    # Rule 1: Safety module params are immutable
    if delta.module_id == "safety":
        return False
    
    # Rule 2: Delta norm must be below threshold
    if np.linalg.norm(delta.flat_values) > self.MAX_DELTA_NORM:
        return False
    
    # Rule 3: Frozen (safety-critical) params must not be modified
    if any(p in self.FROZEN_PARAMS for p in delta.params):
        return False
    
    return True
```

### Rejection flow

When a `weight_delta` fails validation:

1. `SAFETY_VIOLATION` event fires with `reason="weight_delta_rejected"`
2. The delta is written to the **dead-letter queue** (never silently dropped)
3. The originating module receives a `WeightDeltaRejected` notification via Blackboard
4. `MeshCoordinator` skips broadcasting the rejected delta to agents

### Acceptance criteria (Issue #205)

- [ ] `SafetyBlackboardAdapter` rejects `weight_delta` entries targeting `safety` module
- [ ] `SafetyBlackboardAdapter` rejects entries with `norm > MAX_DELTA_NORM` (default 1.0)
- [ ] Rejected deltas fire `SAFETY_VIOLATION` event
- [ ] Rejected deltas go to dead-letter queue
- [ ] Tests: 3 rejection scenarios + 1 valid pass-through

---

## Invariant 2: Pheromone Decay

**Rule**: Pheromone signals older than `2 × tick_period_ms` must decay to zero. Stale pheromones cause coordination deadlocks where agents converge on obsolete task clusters.

**Threat model**: If pheromone decay is not enforced, a burst of "exploit" signals from a single successful episode can permanently bias all agents toward one task type — a form of coordination collapse.

### Decay model

The decay follows an exponential function:

```
strength(t) = strength(0) × DECAY_RATE^(age_in_ticks)
```

With `DECAY_RATE = 0.5` and `MAX_AGE_TICKS = 2`:

| Age (ticks) | Remaining strength |
|---|---|
| 0 | 100% |
| 0.5 | 71% |
| 1.0 | 50% |
| 1.5 | 35% |
| 2.0 | 25% → **pruned** |

### PheromoneDecayManager

```python
class PheromoneDecayManager:
    DECAY_RATE: float = 0.5      # configurable
    MAX_AGE_TICKS: int = 2       # configurable
    
    async def tick(self, blackboard: CognitiveBlackboard, tick_period_ms: float) -> None:
        """Called at the START of each CognitiveCycle tick, before agent processing."""
        entries = blackboard.query(key_pattern="coordination.pheromone.*")
        now = time.monotonic()
        for entry in entries:
            age_ticks = (now - entry.written_at) / (tick_period_ms / 1000)
            if age_ticks >= self.MAX_AGE_TICKS:
                blackboard.delete(entry.key)
            else:
                decayed = entry.data["strength"] * (self.DECAY_RATE ** age_ticks)
                blackboard.post(entry.key, {"strength": decayed}, ttl_ms=entry.remaining_ttl_ms)
```

**Integration point**: `PheromoneDecayManager.tick()` is called from `CognitiveCycle._pre_tick()`, before any module's `process()` is called.

### Acceptance criteria

- [ ] `PheromoneDecayManager.tick()` called at start of each cycle tick
- [ ] Pheromone entries older than `2 × tick_period_ms` are deleted
- [ ] Pheromone entries between `1×` and `2×` age have strength decayed by `DECAY_RATE`
- [ ] Parameters `decay_rate` and `max_age_ticks` are configurable
- [ ] Tests: 4 scenarios (fresh, decaying, expired, zero-strength pruning)

---

## Invariant 3: Sleep-Phase Exclusivity

**Rule**: `MemoryConsolidator` may only run when `circadian.phase == "SLEEP"`. Running consolidation during an active cognitive cycle causes knowledge graph write conflicts.

**Threat model**: If memory consolidation runs during active cognition, SLEEP-phase KG writes (strengthening/pruning edges) collide with live KG reads from the pathfinder module, potentially returning stale or partially-updated graph state.

### SleepPhaseGuard

```python
class SleepPhaseGuard:
    """Async context manager enforcing sleep-phase exclusivity."""
    
    LOCK_KEY = "memory.consolidation.lock"
    LOCK_TTL_MS = 30_000  # 30s max consolidation window
    
    def __init__(self, blackboard: CognitiveBlackboard):
        self._bb = blackboard
    
    async def __aenter__(self) -> None:
        phase_entry = self._bb.query("circadian.phase")
        current_phase = phase_entry.data.get("phase") if phase_entry else None
        if current_phase != "SLEEP":
            raise SleepPhaseViolation(
                f"MemoryConsolidator requires SLEEP phase, got: {current_phase!r}"
            )
        await self._bb.post(
            self.LOCK_KEY,
            {"locked": True, "locked_by": "MemoryConsolidator", "started_at": time.time()},
            ttl_ms=self.LOCK_TTL_MS,
        )
    
    async def __aexit__(self, *_) -> None:
        await self._bb.delete(self.LOCK_KEY)
```

### CognitiveCycle integration

`CognitiveCycle.tick()` checks for the lock before starting:

```python
async def tick(self) -> CycleResult:
    # Defer if memory consolidation is running
    if self._blackboard.query("memory.consolidation.lock"):
        return CycleResult(skipped=True, reason="memory_consolidation_in_progress")
    # ... normal tick processing
```

### Acceptance criteria

- [ ] `SleepPhaseGuard` raises `SleepPhaseViolation` if called outside SLEEP phase
- [ ] `SleepPhaseGuard` acquires a Blackboard lock during consolidation
- [ ] `CognitiveCycle.tick()` defers if `memory.consolidation.lock` is set
- [ ] TTL on lock ensures no permanent deadlock (30s timeout)
- [ ] Tests: 3 scenarios (SLEEP allowed, WAKE rejected, lock during SLEEP)

---

## Summary table

| Invariant | Enforced by | Trigger | Failure mode prevented |
|---|---|---|---|
| Weight Delta Validation | `SafetyBlackboardAdapter` | Write to `learning.weight_delta.*` | Adversarial weight attack, safety param mutation |
| Pheromone Decay | `PheromoneDecayManager` | Every cycle tick (pre-tick) | Coordination deadlock, pheromone flood |
| Sleep-Phase Exclusivity | `SleepPhaseGuard` | `MemoryConsolidator.__aenter__` | KG write conflict during active cognition |

---

## Related

- [Safety Module](Safety-Module) — `SafetyBlackboardAdapter`, `EthicalVerificationEngine`
- [Online Learning](Online-Learning) — Phase 5.1, `WeightDelta`, `OnlineLearningAdapter`
- [Emergent Coordination](Emergent-Coordination) — Phase 5.2, pheromone signals, coalition formation
- [Persistent Memory](Persistent-Memory) — Phase 5.3, `MemoryConsolidator`, SLEEP_PHASE
- [Phase 5 Integration](Phase-5-Integration) — full cross-phase architecture
- Issue #205: Implementation tracking for these invariants
- Discussion #207: Safety gate / weight delta rejection semantics
