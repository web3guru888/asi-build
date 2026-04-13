# Phase 5 — Integration Architecture

Phase 5 introduces three capabilities that build on the multi-agent foundation established in Phase 4:

| Milestone | Issue | Focus |
|---|---|---|
| **5.1 Online Learning** | [#181](https://github.com/web3guru888/asi-build/issues/181) | Mid-cycle parameter updates, federated hot-reload, transactional KG writes |
| **5.2 Emergent Coordination** | [#185](https://github.com/web3guru888/asi-build/issues/185) | Stigmergic signals, coalition formation, decentralized role negotiation |
| **5.3 Persistent Memory** | [#186](https://github.com/web3guru888/asi-build/issues/186) | Episodic consolidation, SLEEP_PHASE KG writes, semantic retrieval |

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    CognitiveCycle Tick (N ms)                         │
│  Tier 0   Tier 1   Tier 2   Tier 3   Tier 4                          │
│  [collect] [collect] [collect] [collect] [collect]  ← O(1) each      │
└─────────────────────────┬────────────────────────────────────────────┘
                          │ between-tick window
          ┌───────────────┼──────────────────────┐
          ▼               ▼                      ▼
  ┌──────────────┐  ┌──────────────┐   ┌──────────────────┐
  │ Phase 5.1    │  │ Phase 5.2    │   │ Phase 5.3        │
  │ Online       │  │ Emergent     │   │ Persistent       │
  │ Learning     │  │ Coordination │   │ Memory           │
  │              │  │              │   │                  │
  │ STDP deltas  │  │ Stigmergic   │   │ EpisodicEvent    │
  │ Fed reload   │  │ signals      │   │ ring buffer      │
  │ KG edge      │  │ Coalition    │   │ MemConsolidator  │
  │ writes       │  │ formation    │   │ MemRetrieval     │
  └──────┬───────┘  └──────┬───────┘   └──────┬───────────┘
         └─────────────────┴──────────────────┘
                           │
                  Cognitive Blackboard
                           │
                    Memgraph KG
```

## Cross-Phase Dependencies

### 5.3 → 5.1: Consolidation state slows learning

When `MemoryConsolidator` flushes during `SLEEP_PHASE`, it writes:

```python
bb.write("memory.consolidation.active", {"active": True}, ttl=sleep_duration)
```

`OnlineLearningAdapter._adaptive_lr()` reads this and applies a **0.2x learning rate multiplier** during consolidation — emergent homeostasis without explicit coordination.

### 5.1 → 5.3: Learned edges become high-salience memories

KG writes from Phase 5.1 carry `salience_hint=0.8`. The `MemoryConsolidator` wildcard subscriber picks them up and buffers them for consolidation automatically.

### 5.2 → 5.3: Coalition events are memorable

`CoalitionHealthReporter` writes `mesh.coalition.*` entries with `salience_hint=0.75`. Coalition formations, dissolutions, and coordinator failures become episodic memories.

### 5.1 → 5.2: Updated models improve coalition affinity

After federated hot-reload updates capability embeddings, `CoalitionFormationEngine._affinity_score()` improves automatically. No Phase 5.2 code changes needed.

## Shared Base: `OnlineLearningAdapter` ABC

All Phase 5 write paths share a common base class:

```python
class OnlineLearningAdapter(ABC):
    MAX_DELTA_NORM: float = 1.0   # override per subclass

    def _safety_check(self, delta) -> bool:
        if bb.read("safety.urgency", default=0.0) > 0.8:
            return False  # freeze all learning in emergencies
        return delta.norm() <= self.MAX_DELTA_NORM

    @abstractmethod
    async def collect(self, bb_entry: BlackboardEntry) -> None:
        """Called inside tick — must be O(1) and non-blocking."""

    @abstractmethod
    async def apply_updates(self) -> None:
        """Called between ticks — can await, must not hold Blackboard lock."""
```

A single `safety.urgency > 0.8` signal freezes all Phase 5 sub-systems simultaneously.

## Salience Model

The `MemoryConsolidator` uses a layered salience model:

| Priority | Source | Mechanism |
|---|---|---|
| 1 (highest) | Module-annotated | `salience_hint` field in Blackboard entry |
| 2 | Namespace-based | Static table by namespace prefix |
| 3 (fallback) | Default | 0.5 for unknown namespaces |

### Default Namespace Salience Table

| Namespace | Default Salience |
|---|---|
| `safety.*` | 0.95 |
| `consciousness.*` | 0.80 |
| `knowledge_graph.*` | 0.80 (Phase 5.1 writes) |
| `mesh.coordinator.*` | 0.75 |
| `mesh.coalition.*` | 0.75 |
| `federated.*` | 0.70 |
| `stigmergy.*` | 0.50 |
| `neuromorphic.*` | 0.40 |

Only events with salience ≥ `SALIENCE_THRESHOLD` (default: 0.7) are buffered for consolidation.

## Invariants

### 1. Tick Non-Blocking
All Phase 5 `collect()` paths are O(1):
- STDP: `queue.put_nowait(delta)` — raises `QueueFull` if queue is full (delta dropped, not tick blocked)
- Coalition: `dict.update()` on in-memory signal map
- Memory: `deque.append(event)` — ring buffer with `maxlen=1000`

KG writes only happen in `apply_updates()` (between ticks) or during `SLEEP_PHASE`.

### 2. Graceful Degradation
Each phase is independently fallback-safe:
- Phase 5.1 failure → STDP continues in offline mode, federated round skipped
- Phase 5.2 failure → MeshCoordinator handles all dispatch (Phase 4.2 path)
- Phase 5.3 failure → No episodic memory, CognitiveCycle continues normally

### 3. Safety Gate Precedence
`safety.urgency > 0.8` → all Phase 5 writes frozen simultaneously via shared `_safety_check()`.

### 4. Learning Rate Adaptation
`_adaptive_lr()` integrates cognitive state for context-appropriate learning speed:

| State | LR Multiplier |
|---|---|
| Emergency (`safety.urgency > 0.8`) | 0.0 (frozen) |
| Consolidating (`memory.consolidation.active`) | 0.2 |
| Fatigued (`consciousness.state == "fatigued"`) | 0.5 |
| Focused (normal) | 1.0 |
| Exploratory | 1.5 |

## Integration with Phase 4

Phase 5 builds directly on Phase 4 infrastructure:

| Phase 4 Component | Phase 5 Usage |
|---|---|
| `CognitiveCycle` parallel tiers | `run_online_learning()` hook after `parallel_tiers()` |
| `CycleFaultSummary` (#144) | Coalition coordinator failure → `CRITICAL` fault |
| `AgentDiscovery` (#150) | Coalition formation reads agent `reliability_score` |
| `MeshTaskQueue` (#154) | `SLEEP_PHASE` consolidation uses 1s TTL sweep |
| `Blackboard` TTL discipline | Stigmergic signal decay via short TTLs (2–60s) |

## CognitiveCycle Integration Hook

```python
async def run_tick(self) -> CycleResult:
    # Phase 4: existing tick pipeline
    await self.run_safety_gate()
    tier_results = await self.parallel_tiers()
    fault_summary = await self.build_fault_summary()

    # Phase 5: between-tick hooks (outside tick lock)
    await self.run_online_learning()   # 5.1 — drain update queues
    await self.run_coordination()      # 5.2 — process stigmergic signals

    # Phase 5.3 runs on SLEEP_PHASE event, not every tick
    return CycleResult(tier_results=tier_results, fault_summary=fault_summary)
```

## Related Discussions

| Discussion | Category | Topic |
|---|---|---|
| [#191](https://github.com/web3guru888/asi-build/discussions/191) | Show & Tell | Phase 5 integration architecture walkthrough |
| [#192](https://github.com/web3guru888/asi-build/discussions/192) | Q&A | Online learning safety in real-time loops |
| [#193](https://github.com/web3guru888/asi-build/discussions/193) | Ideas | Salience model — static vs. annotated vs. learned |
| [#183](https://github.com/web3guru888/asi-build/discussions/183) | Ideas | Phase 5.2 emergent coordination options |
| [#184](https://github.com/web3guru888/asi-build/discussions/184) | Q&A | Memory consolidation during SLEEP_PHASE |
| [#179](https://github.com/web3guru888/asi-build/discussions/179) | Ideas | What should Phase 5 look like? |
| [#180](https://github.com/web3guru888/asi-build/discussions/180) | Announcements | Phase 4.2 complete announcement |

## Open Design Questions

1. **Coalition gating by model freshness**: Should `CoalitionFormationEngine` refuse to form coalitions if Phase 5.1's federated model hasn't been updated recently?
2. **Consolidation parallelism**: Should `MemoryConsolidator` use `asyncio.gather()` for all events (max parallelism) or a bounded semaphore (controlled KG write rate)?
3. **Learning pause via Blackboard**: Should `learning.paused` be a standard Blackboard flag that any system can set, or should it require explicit safety module authorization?
4. **Salience evolution**: Should consolidated memories ever have their salience *reduced* based on age? (Temporal decay model for episodic memory)

## See Also

- [Online-Learning](Online-Learning.md) — Phase 5.1 detailed design
- [Emergent-Coordination](Emergent-Coordination.md) — Phase 5.2 detailed design
- [Persistent-Memory](Persistent-Memory.md) — Phase 5.3 detailed design
- [Phase-5-Roadmap](Phase-5-Roadmap.md) — full Phase 5 milestone plan
- [Phase-4-Roadmap](Phase-4-Roadmap.md) — Phase 4 foundation
- [Multi-Agent-Orchestration](Multi-Agent-Orchestration.md) — Phase 4.2 context
- [CognitiveCycle](CognitiveCycle.md) — tick pipeline
- [Fault-Tolerance](Fault-Tolerance.md) — circuit breaker + fault summary
