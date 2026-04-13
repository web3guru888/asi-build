# Multi-Agent Orchestration

Phase 4.2 of the ASI:BUILD roadmap introduces **AgentMesh** — a coordinator for running multiple `CognitiveCycle` instances in parallel, each specializing in a subset of the 29 modules.

> **Status**: Design phase (see [Issue #147](https://github.com/web3guru888/asi-build/issues/147))

## Motivation

A single `CognitiveCycle` running all 29 modules is bounded by the ~100ms tick budget (#126). Distributing modules across specialized agents enables:

- **Lower per-agent tick latency** — each agent runs a subset, completing faster
- **Variable tick rates** — perception at 10Hz, reasoning at 2Hz, action at 1Hz
- **Fault isolation** — a crashed quantum agent does not affect the safety agent
- **Hardware specialization** — GPU node for vision, CPU node for logic

## Agent Roles

```python
class AgentRole(str, Enum):
    PERCEPTION    = "perception"     # BCI, holographic, multimodal, neuromorphic
    REASONING     = "reasoning"      # hybrid_reasoning, PLN, graph_intelligence
    MEMORY        = "memory"         # knowledge_graph, vector_db, knowledge_mgmt
    ACTION        = "action"         # agi_communication, economics, vla
    SAFETY        = "safety"         # safety, agi_reproducibility (mandatory)
    COMPUTE       = "compute"        # quantum, neuromorphic, homomorphic
    COORDINATION  = "coordination"   # orchestrates other roles
```

## Recommended Module Partition

| Role | Modules | Tick Hz |
|------|---------|---------|
| PERCEPTION | bci, holographic, multimodal_fusion, neuromorphic | 10 |
| REASONING | hybrid_reasoning, pln, graph_intelligence, knowledge_graph | 2 |
| MEMORY | vector_db, knowledge_mgmt, bi_temporal_kg | 5 |
| ACTION | agi_communication, economics, vla, federated_learning | 1 |
| SAFETY | safety, agi_reproducibility | (every tick — gating) |
| COMPUTE | quantum, neuromorphic (deep), homomorphic | on-demand |

## AgentSpec & AgentMesh

```python
@dataclass
class AgentSpec:
    agent_id: str
    role: AgentRole
    modules: list[str]
    tick_hz: float
    blackboard_topics: list[str]
    node_affinity: Optional[str] = None

class AgentMesh:
    async def register(self, spec: AgentSpec) -> None: ...
    async def start_all(self) -> None: ...
    async def get_mesh_health(self) -> dict[str, CycleFaultSummary]: ...
```

## Communication Pattern

All agents communicate **exclusively through the shared `CognitiveBlackboard`** — no direct inter-agent calls:

```
PERCEPTION agent  ->  "perception.perceptual_state"  ->  Blackboard
REASONING  agent  <-  "perception.perceptual_state"  <-  Blackboard
REASONING  agent  ->  "reasoning.reasoning_result"   ->  Blackboard
ACTION     agent  <-  "reasoning.reasoning_result"   <-  Blackboard
SAFETY     agent  <-  ALL topics                     <-  Blackboard
```

Entry types are **namespaced by role** (e.g. `"perception.perceptual_state"`) to prevent schema collisions between agents posting to the same logical topic.

## TTL Discipline

TTLs must align with the producing agent's tick rate:

| Role | TTL |
|------|-----|
| PERCEPTION | 100ms (one 10Hz tick) |
| REASONING | 500ms (one 2Hz tick) |
| MEMORY | 200ms (one 5Hz tick) |
| ACTION | 1000ms (one 1Hz tick) |
| SAFETY | 50ms (must always be fresh) |

Consumers must check `expires_at > time.monotonic() + margin` before trusting an entry.

## Health Monitoring

The `AgentMesh` exposes health at two levels:

1. **Per-agent**: each `CognitiveCycle` produces a `CycleFaultSummary` per tick (see [[Health-Monitoring]])
2. **Mesh-level**: `/mesh/health/stream` SSE endpoint streaming a dict of per-agent summaries

## Scope Boundaries

| In scope (Phase 4.2) | Out of scope |
|---------------------|-------------|
| Single-process `AgentMesh` | Multi-process / multi-node |
| Shared in-memory Blackboard | Distributed Blackboard (Redis/NATS) |
| `asyncio.gather()` concurrency | Kubernetes scheduling |
| Per-agent health monitoring | Cross-agent tracing/metrics |

Distributed Blackboard is planned for Phase 5.

## Related

- [Issue #147](https://github.com/web3guru888/asi-build/issues/147) — AgentMesh implementation issue
- [Discussion #148](https://github.com/web3guru888/asi-build/discussions/148) — Task distribution strategy
- [Discussion #149](https://github.com/web3guru888/asi-build/discussions/149) — Concurrent Blackboard writes
- [[Health-Monitoring]] — CycleFaultSummary and SSE streaming
- [[CognitiveCycle]] — Single-agent tick pipeline
