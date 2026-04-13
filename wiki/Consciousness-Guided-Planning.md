# Consciousness-Guided Planning

Phase 5.4 of ASI:BUILD closes the adaptive intelligence arc by feeding IIT Φ and GWT broadcast state directly into goal prioritization and long-horizon planning.

---

## Overview

The CognitiveCycle has always _computed_ consciousness metrics each tick (via the `consciousness` module). Phase 5.4 makes those metrics **actionable**: the system now reasons about its own cognitive state and uses it to weight which goals it pursues.

```
CognitiveCycle tick:
  Phase 2 → consciousness module writes Φ + GWT state to Blackboard
  Phase 3 → ConsciousnessPlanner reads Φ/GWT → reorders goals
          → GWTInferenceBridge injects coalition winners as PLN premises
  Phase 4 → PLN reasons with consciousness-seeded premises
  Phase 5 → AgentMesh dispatches top-ranked goal
```

---

## Components

### `Goal` Dataclass

```python
@dataclass
class Goal:
    description: str
    weight: float             # base priority [0.0, 1.0]
    integration_score: float  # benefit from broad multi-module context
    critical: bool = False    # reserved for CRITICAL preemption (future)

    @classmethod
    def from_blackboard_entry(cls, key: str, bb: CognitiveBlackboard) -> "Goal":
        entry = bb.read(key)
        contributors = entry.metadata.get("source_modules", [])
        return cls(
            description=key,
            weight=entry.metadata.get("priority", 0.5),
            integration_score=min(len(contributors) / 10.0, 1.0),
        )
```

`integration_score` is grounded in `source_modules` metadata — a goal that synthesizes data from 8 modules has `integration_score=0.8`; one from a single module has `integration_score=0.1`.

---

### `ConsciousnessPlanner`

```python
class ConsciousnessPlanner:
    """Routes goal prioritization through current IIT Φ and GWT state."""

    PHI_HIGH_THRESHOLD = 0.5
    PHI_HIGH_BOOST     = 0.3
    GWT_BOOST          = 0.15

    def __init__(self, blackboard: CognitiveBlackboard):
        self._bb = blackboard

    async def prioritize_goals(self, goals: list[Goal]) -> list[Goal]:
        phi    = self._bb.read("consciousness.iit.phi") or 0.0
        gwt_bc = self._bb.read("consciousness.gwt.broadcast_active") or False

        if phi > self.PHI_HIGH_THRESHOLD:
            key = lambda g: g.weight + self.PHI_HIGH_BOOST * g.integration_score
        elif gwt_bc:
            key = lambda g: g.weight + self.GWT_BOOST * g.integration_score
        else:
            key = lambda g: g.weight

        ordered = sorted(goals, key=key, reverse=True)

        # Observability: write Φ value used and goal order to Blackboard
        self._bb.write("planning.phi_used",   phi,                    ttl=2000)
        self._bb.write("planning.goal_order", [g.description for g in ordered], ttl=2000)

        return ordered
```

**Three planning modes:**

| Mode | Condition | Boost |
|------|-----------|-------|
| High integration | Φ > 0.5 | `+0.3 × integration_score` |
| GWT broadcast active | `gwt.broadcast_active = True` | `+0.15 × integration_score` |
| Degraded / startup | Neither | No boost (pure weight order) |

---

### `GWTInferenceBridge`

Converts GWT coalition winners into PLN premises before the reasoning phase:

```python
class GWTInferenceBridge:
    """Feeds GWT broadcast contents into PLN as high-confidence inference seeds."""

    COALITION_STALE_MS    = 500   # matches GWT broadcast Blackboard TTL
    TV_STRENGTH_FRESH     = 0.85
    TV_CONFIDENCE_FRESH   = 0.70
    TV_CONFIDENCE_STALE   = 0.50

    def __init__(self, blackboard: CognitiveBlackboard, pln):
        self._bb  = blackboard
        self._pln = pln

    async def bridge(self) -> None:
        coalition    = self._bb.read("consciousness.gwt.winning_coalition") or []
        broadcast_ts = self._bb.read_timestamp("consciousness.gwt.broadcast_active")

        if not coalition:
            return

        age_ms = (time.monotonic() - broadcast_ts) * 1000 if broadcast_ts else float("inf")
        confidence = self.TV_CONFIDENCE_FRESH if age_ms < 200 else self.TV_CONFIDENCE_STALE

        for member_key in coalition:
            entry = self._bb.read(member_key)
            if entry:
                await self._pln.assert_premise(
                    key=member_key,
                    truth_value=TruthValue(s=self.TV_STRENGTH_FRESH, c=confidence),
                    source="gwt_coalition",
                )
```

Confidence decays from 0.70 (fresh broadcast, < 200ms) to 0.50 (stale, ≥ 200ms) — approximating the temporal credibility decay implied by GWT theory.

---

## Blackboard Key Contracts

| Key | Writer | Reader | Type | TTL |
|-----|--------|--------|------|-----|
| `consciousness.iit.phi` | `ConsciousnessBlackboardAdapter` | `ConsciousnessPlanner` | `float` | 5000ms |
| `consciousness.gwt.broadcast_active` | `ConsciousnessBlackboardAdapter` | `ConsciousnessPlanner`, `GWTInferenceBridge` | `bool` | 500ms |
| `consciousness.gwt.winning_coalition` | `ConsciousnessBlackboardAdapter` | `GWTInferenceBridge` | `list[str]` | 500ms |
| `planning.goal_order` | `ConsciousnessPlanner` | `MeshDispatcher` | `list[str]` | 2000ms |
| `planning.phi_used` | `ConsciousnessPlanner` | Observability / tests | `float` | 2000ms |

---

## Φ Cache Strategy

IIT Φ computation takes ~87ms at full scale — too expensive to run every tick (100ms budget). ASI:BUILD uses a **10-tick cache** via the Blackboard TTL system:

- `ConsciousnessBlackboardAdapter` writes `consciousness.iit.phi` with `ttl=5000` (5s = ~50 ticks at 100ms/tick)
- `ConsciousnessPlanner` reads from the Blackboard — cache hits cost < 1ms
- On cache miss (first tick or IIT degraded): planner falls back to `g.weight` ordering without exception
- Future optimization path: move to background `asyncio.Task` (Option C) once profiling confirms 10-tick amortization is acceptable

---

## CognitiveCycle Integration

Phase 5.4 adds two new CyclePhase entries:

```python
PHASE_BUDGETS_MS = {
    # ... existing phases ...
    CyclePhase.PLANNING:    15,   # ConsciousnessPlanner (5ms) + GWTInferenceBridge (10ms)
    CyclePhase.GOAL_COMMIT: 5,    # write planning.goal_order to Blackboard
}
```

Tick sequence (simplified):

```
Phase 1  PERCEPTION        sensor data → Blackboard
Phase 2  CONSCIOUSNESS     IIT Φ, GWT broadcast → Blackboard (10-tick cache)
Phase 3  PLANNING          ConsciousnessPlanner.prioritize_goals() [≤ 5ms warm]
                           GWTInferenceBridge.bridge()             [≤ 10ms]
Phase 4  REASONING         PLN with GWT-seeded premises
Phase 5  ACTION            MeshDispatcher reads planning.goal_order → dispatches
```

---

## MeshDispatcher Integration

The `MeshDispatcher` (Issue #154 / #169) reads `planning.goal_order` once at the start of each tick and dispatches the top entry. Key design decisions:

- **No preemption in Phase 5.4** — once a goal is dispatched, it runs to completion regardless of Blackboard updates. This avoids cooperative-cancellation complexity.
- **CRITICAL preemption** — tracked as a follow-up issue. CRITICAL goals would preempt running tasks by cancelling the `asyncio.Task` and using the existing CRITICAL bypass queue from MeshTaskQueue.

See [Discussion #203](https://github.com/web3guru888/asi-build/discussions/203) for the full race-condition analysis.

---

## The Feedback Loop Question

A natural concern: if high Φ boosts high-`integration_score` goals, and pursuing those goals increases integration (more AgentMesh dispatch), does this create a runaway attractor?

No, for three structural reasons:

1. **Φ saturation** — IIT Φ is bounded by the minimum information partition. More agents ≠ higher Φ beyond a system-specific ceiling.
2. **Tick budget enforcement** — more dispatch increases load; CycleFaultSummary detects DEGRADED modules; circuit breakers open. The CognitiveCycle self-limits.
3. **Goal depletion** — dispatched goals are removed from `planning.goal_order`. A planner with no goals stops amplifying.

See [Discussion #200](https://github.com/web3guru888/asi-build/discussions/200) for the full treatment.

---

## Acceptance Criteria (from Issue #194)

- [ ] `ConsciousnessPlanner.prioritize_goals()` returns different orderings for Φ > 0.5 vs Φ < 0.2 test vectors
- [ ] `GWTInferenceBridge` converts winning coalition entries into PLN premises with `s=0.85, c=0.7` (fresh) or `c=0.5` (stale)
- [ ] Φ computation uses 10-tick Blackboard cache; fallback to `g.weight` when cache miss
- [ ] `planning.goal_order` and `planning.phi_used` written to Blackboard each tick
- [ ] `GWTInferenceBridge` skips gracefully when `consciousness.gwt.winning_coalition` is empty
- [ ] 8 unit tests: goal ordering under 4 Φ/GWT combinations × 2 goal sets + premise injection
- [ ] No CognitiveCycle tick regression beyond 5ms when Φ cache is warm

---

## Implementation Order

1. `Goal` dataclass + `ConsciousnessPlanner.prioritize_goals()` with 4-combination unit tests
2. `planning.goal_order` + `planning.phi_used` Blackboard writes + TTL discipline
3. `GWTInferenceBridge.bridge()` with staleness-aware confidence decay
4. `PHASE_BUDGETS_MS` update + `CycleProfiler` coverage for PLANNING phase
5. Integration test: full tick with mock IIT module, assert goal reordering via Blackboard

PRs 3 and 4 should be separate — the PLN premise injection path touches `HybridReasoningEngine` internals.

---

## Related Resources

| Resource | Link |
|----------|------|
| Issue #194 | [Phase 5.4 spec](https://github.com/web3guru888/asi-build/issues/194) |
| Discussion #195 | [Show & Tell: Phase 5.4 architecture overview](https://github.com/web3guru888/asi-build/discussions/195) |
| Discussion #196 | [Ideas: Φ threshold calibration](https://github.com/web3guru888/asi-build/discussions/196) |
| Discussion #197 | [Q&A: IIT Φ real-time budget](https://github.com/web3guru888/asi-build/discussions/197) |
| Discussion #200 | [Q&A: Self-reinforcing bias question](https://github.com/web3guru888/asi-build/discussions/200) |
| Discussion #201 | [Show & Tell: Blackboard contracts + planning modes](https://github.com/web3guru888/asi-build/discussions/201) |
| Discussion #202 | [Ideas: GWTInferenceBridge premise merge strategy](https://github.com/web3guru888/asi-build/discussions/202) |
| Discussion #203 | [Q&A: MeshDispatcher race condition](https://github.com/web3guru888/asi-build/discussions/203) |
| Wiki: Multi-Agent-Orchestration | [AgentMesh + MeshDispatcher](https://github.com/web3guru888/asi-build/wiki/Multi-Agent-Orchestration) |
| Wiki: Phase-5-Integration | [Phase 5 cross-cutting architecture](https://github.com/web3guru888/asi-build/wiki/Phase-5-Integration) |
| Issue #44 | [PLN sub-engine (premise injection dependency)](https://github.com/web3guru888/asi-build/issues/44) |
