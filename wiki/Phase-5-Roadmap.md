# Phase 5 Roadmap — Online Learning, Emergent Coordination, Persistent Memory

**Status**: Planning | **Issue**: [#176](https://github.com/web3guru888/asi-build/issues/176) | **Discussion**: [#179](https://github.com/web3guru888/asi-build/discussions/179)

Phase 5 closes the adaptation loop: ASI:BUILD moves from a static cognitive pipeline to a system that learns from running, coordinates emergently, and remembers across sessions.

---

## Prerequisites

Phase 5 requires Phase 4 to be complete:

| Phase 4 component | Status |
|---|---|
| CognitiveCycle profiling (#126) | ✅ |
| Module dependency graph (#131) | ✅ |
| Parallel tier execution (#133) | ✅ |
| Circuit breaker (#137) | ✅ |
| Retry budget (#139) | ✅ |
| CycleFaultSummary + SSE (#144) | ✅ |
| AgentMesh (#147) | ✅ |
| AgentDiscovery (#150) | ✅ |
| MeshTaskQueue (#154) | ✅ |
| MeshResultAggregator (#168) | ✅ |
| MeshCoordinator (#169) | ✅ |
| Production deployment (#164) | 🔨 In progress |

---

## Milestone 5.1 — Online Learning Integration

**Goal**: Allow modules to update internal models based on Blackboard events during live operation, without stopping the CognitiveCycle.

### Scope

| Module | Online update type | Safety gate |
|---|---|---|
| `bio_inspired` | STDP weight updates (per-spike) | Required (EthicalVerificationEngine) |
| `federated_learning` | Model diff hot-reload (async) | Required |
| `knowledge_graph` | Transactional node/edge additions | Required (append-only) |
| `hybrid_reasoning` | PLN TruthValue updates from inference results | Required |

### Key design

```python
async def apply_weight_update(self, delta: WeightDelta) -> bool:
    """Gate all online updates through Safety."""
    context = EthicalContext(
        action_type="weight_update",
        module_name=self.name,
        payload=delta.to_audit_dict(),  # hash only, not raw weights
        magnitude=delta.norm(),
    )
    verdict = await self.safety_adapter.verify(context)
    if not verdict.approved:
        blackboard.write("safety.weight_update_blocked",
                         {"module": self.name, "reason": verdict.reason}, ttl=300)
        return False
    self._apply_delta(delta)
    return True
```

### Acceptance criteria

- [ ] STDP weight updates apply within the same tick they're triggered, without tick duration regression
- [ ] Federated model patches applied asynchronously without blocking CognitiveCycle
- [ ] All weight updates rejected by Safety module generate a `safety.weight_update_blocked` Blackboard event
- [ ] KG transactional updates use Memgraph `BEGIN / COMMIT` — no partial writes visible to other modules

### Dependencies

- #44 (PLN sub-engine — replace stub before online update)
- #54 (neuromorphic benchmarks — STDP convergence baseline)
- #164 (production deployment — staging environment)

---

## Milestone 5.2 — Emergent Multi-Agent Coordination

**Goal**: Move beyond explicit task dispatch (MeshTaskQueue) toward self-organizing agent behavior.

### Scope

| Feature | Description |
|---|---|
| Coalition formation | Agents with overlapping capabilities self-group for complex tasks |
| Stigmergic coordination | Agents communicate indirectly via Blackboard `mesh.stigmergy.*` entries |
| Dynamic role negotiation | `AgentDiscovery` role assignments become fluid based on load + task history |

### Blackboard namespace

```
mesh.coalition.proposal.*   — coalition formation proposals
mesh.coalition.active.*     — active coalitions (TTL=600s)
mesh.stigmergy.*            — indirect coordination signals (pheromone-like, TTL=30s)
```

### Key design questions

1. Should coalition formation operate within a single `MeshCoordinator` process, or across process boundaries via Rings P2P (#19)?
2. Stigmergic coordination requires Blackboard reads from agents — does this violate the lock-before-await discipline (#149)?

### Dependencies

- 5.1 (agents need online-updated models to form meaningful coalitions)
- #19 (Rings P2P — cross-process coalition formation)

---

## Milestone 5.3 — Persistent Cognitive Memory

**Goal**: High-salience Blackboard events written to Memgraph with temporal metadata. Episodic memory promotes to semantic knowledge during `SLEEP_PHASE`.

### Memory architecture

```
CognitiveCycle tick
  │
  ├── High-salience events → blackboard.write("memory.episodic.*", TTL=3600s)
  │
SLEEP_PHASE triggered (bio_inspired module)
  │
  └── MemoryConsolidator.tick()
        ├── Query: memory.episodic.* with min_salience=0.7
        ├── Write: Memgraph (bi-temporal, permanent)
        └── Delete: episodic Blackboard entry (promote → semantic)
```

### Salience scoring

Not all Blackboard events deserve long-term storage. Proposed salience factors:

| Factor | Weight |
|---|---|
| Safety event (any severity) | +0.9 |
| CognitiveCycle fault (CRITICAL) | +0.8 |
| IIT Φ spike (Δ > 0.3) | +0.6 |
| Agent coalition formed | +0.5 |
| Routine tick result | +0.1 |

Events with combined salience ≥ 0.7 are written to episodic memory.

### Dependencies

- #2 (knowledge graph API — Memgraph write path)
- #68 (blockchain audit — tamper-evidence for episodic memory)
- #164 (production deployment — persistent Memgraph volume)

---

## Milestone 5.4 — Consciousness-Guided Planning

**Goal**: Use IIT Φ and GWT broadcast to guide long-horizon planning.

### Design

**Φ-weighted goal prioritization**: High Φ states indicate high cognitive integration. Goals that maintain or increase integration should be prioritized.

```python
class ConsciousnessPlanner:
    async def prioritize_goals(self, goals: list[Goal], phi: float) -> list[Goal]:
        # Φ > 0.5: integration-preserving goals get +0.3 weight boost
        # Φ < 0.2: degrade to simple priority ordering
        if phi > 0.5:
            return sorted(goals, key=lambda g: g.weight + 0.3 * g.integration_score, reverse=True)
        return sorted(goals, key=lambda g: g.weight, reverse=True)
```

**GWT coalition amplification**: GWT global broadcast winners are passed to PLN for long-horizon inference. The coalition provides the "working hypothesis" that PLN extends via deduction/abduction chains.

### Φ computation budget

IIT Φ takes ~87ms at current scale — cannot run every 100ms tick. Options:

| Option | Cost per tick | Fidelity |
|---|---|---|
| A — Every 10 ticks (cached) | ~8.7ms amortized | Full |
| B — 5-node subgraph only | ~3ms | Reduced |
| C — Background async Task | ~0ms (stale possible) | Full, async |

**Recommendation**: Start with Option A. Profile before adopting C.

### Dependencies

- #34 (canonical Φ benchmarks — validate computation before using as signal)
- #24 (consciousness benchmarks — GWT broadcast timing)

---

## Recommended implementation order

```
Phase 4.3 Production (must complete first)
    ↓
5.1 Online Learning + 5.3 Persistent Memory (parallel)
    ↓
5.2 Emergent Coordination (requires 5.1)
    ↓
5.4 Consciousness Planning (requires 5.3 + #34 + #24)
```

---

## Related

- Issue: [#176](https://github.com/web3guru888/asi-build/issues/176) (Phase 5 milestones)
- Discussion: [#179](https://github.com/web3guru888/asi-build/discussions/179) (community priority vote)
- Phase 4 Roadmap: [Phase-4-Roadmap](https://github.com/web3guru888/asi-build/wiki/Phase-4-Roadmap)
- Production Deployment: [Production-Deployment](https://github.com/web3guru888/asi-build/wiki/Production-Deployment)
- Multi-Agent Orchestration: [Multi-Agent-Orchestration](https://github.com/web3guru888/asi-build/wiki/Multi-Agent-Orchestration)
