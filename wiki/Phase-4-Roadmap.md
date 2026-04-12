# Phase 4 Roadmap

**Status**: Planning → In Progress  
**Target**: Real-time cognitive cycle, full 29-module integration, production deployment

---

## Overview

Phase 4 is the first production milestone for ASI:BUILD. The goal is a running system where all 29 modules are wired to the Cognitive Blackboard and the CognitiveCycle executes a complete perception-to-action loop in real time.

Phases 1–3 were primarily about building individual modules and the integration infrastructure. Phase 4 is about making them run *together*.

---

## Phase 4 Goals

### Goal 1: Complete the Blackboard Adapter Set (29/29 wired)

**Status**: 16/29 complete  
**Remaining**: consciousness, neuromorphic, homomorphic, quantum, holographic_ui, federated_learning, knowledge_management, agi_communication, knowledge_graph, graph_intelligence, cognitive_synergy, hybrid_reasoning, multimodal

Each adapter follows the `AsyncBlackboardAdapter` base class (Issue #101). Design sketches are available for each:
- Consciousness: Issue #116
- Neuromorphic: Issue #119
- Homomorphic: Issue #120
- Quantum: Issue #53

**Success criteria**: Every module writes at least one `BlackboardEntry` per CognitiveCycle tick, and at least one other module subscribes to that entry type.

---

### Goal 2: Live CognitiveCycle at <120ms per tick

The 9-phase CognitiveCycle (Issue #41) must run end-to-end in under 120ms:

| Phase | Module(s) | Budget |
|-------|-----------|--------|
| 1. Sensory Integration | BCI, Multimodal | 10ms |
| 2. Neuromorphic Processing | Neuromorphic | 8ms |
| 3. Memory Retrieval | Knowledge Graph, KM | 12ms |
| 4. Graph Reasoning | Graph Intelligence | 10ms |
| 5. Consciousness Evaluation | Consciousness (async Φ) | 20ms |
| 6. Hybrid Reasoning | Hybrid Reasoning, PLN | 20ms |
| 7. Safety Gate | Safety (Z3 fast path) | 8ms |
| 8. Action Synthesis | AGI Communication, Economics | 12ms |
| 9. Blackboard Publish + EventBus | Integration Layer | 5ms |
| _Buffer_ | — | 15ms |
| **Total** | — | **120ms** |

Consciousness (IIT Φ) runs async in Phase 5 — it can take up to 500ms but doesn't block the main tick; it posts to the Blackboard when ready and influences the *next* cycle's reasoning mode.

**Success criteria**: 100 consecutive ticks at <120ms median on commodity hardware (8-core CPU, no GPU).

---

### Goal 3: Multi-Agent Coordination

The AGI Communication module (Discussion #47) implements a full inter-agent protocol. Phase 4 target: two ASI:BUILD instances coordinating on a shared task via the GOAL_AGREEMENT message type.

**Milestones**:
1. Two local instances share a Blackboard topic over the Rings Network P2P transport
2. GOAL_AGREEMENT negotiation round-trips < 50ms
3. One agent's `action_proposal` entries are readable by the other agent's reasoning module

**Success criteria**: Reproduce a 2-agent cooperative reasoning scenario with logged GOAL_AGREEMENT traces.

---

### Goal 4: Privacy-Preserving Consciousness Pipeline

The encrypted IIT Φ research direction (Issue #31) requires the following chain:

```
EEG → BCI module → CKKS encrypt → HomomorphicAdapter posts ciphertext →
ConsciousnessAdapter reads ciphertext → encrypted Φ computation →
Final decrypt only at "publish to human" stage
```

This is a Phase 4 *research milestone* — we expect it to be slow (encrypted Φ computation may take minutes on current FHE parameters), but it establishes the architecture for future hardware acceleration.

**Success criteria**: End-to-end encrypted Φ computation on synthetic EEG data, with no plaintext brain state written to the Blackboard at any point.

---

### Goal 5: Production Deployment Package

**Deliverables**:
- Docker Compose file: all modules + Blackboard + MCP server in one `docker-compose up`
- Helm chart: Kubernetes deployment with horizontal scaling for compute-heavy modules
- Health endpoint: `/health` returning per-module status + last Blackboard write timestamp
- Metrics endpoint: `/metrics` (Prometheus format) — Blackboard write rate, cycle tick latency, module error rate

**Success criteria**: `docker-compose up` → running system in < 2 minutes on a clean machine, all 29 modules healthy.

---

## Phase 4 Sub-Goals (Detailed)

### 4.1 — Adapter Completion Sprint

Target: wire remaining 13 modules in 2-week sprints, 2-3 adapters per sprint.

**Sprint 1** (priority: consciousness + neuromorphic + homomorphic)
- Rationale: unlocks the Φ-gating CognitiveCycle and the privacy pipeline

**Sprint 2** (priority: quantum + knowledge_graph + graph_intelligence)
- Rationale: quantum adapter enables quantum-enhanced reasoning; KG adapters complete the memory stack

**Sprint 3** (priority: hybrid_reasoning + cognitive_synergy + agi_communication)
- Rationale: reasoning core complete; multi-agent coordination enabled

**Sprint 4** (priority: federated_learning + knowledge_management + holographic_ui + multimodal)
- Rationale: learning and interface layers last — they depend on the reasoning core being stable

---

### 4.2 — CognitiveCycle Integration Tests

End-to-end tests for the full cycle (Issue #18 + Issue #41):

```python
async def test_full_cognitive_cycle_completes():
    """Every module writes at least one Blackboard entry per tick."""
    cycle = CognitiveCycle(modules=registry.all(), blackboard=bb)
    result = await cycle.tick(sensory_input=test_percept)
    
    assert result.duration_ms < 120
    assert len(result.entries_written) == 29  # all 29 modules contributed
    assert result.safety_gate_passed
    assert result.action_proposal is not None

async def test_phi_gating():
    """Reasoning mode switches based on Φ threshold."""
    # Low Φ percept → reactive reasoning
    # High Φ percept → deliberate reasoning
    ...
```

---

### 4.3 — Formal Benchmark Suite

Extend the benchmark suite (Issue #24) to cover all modules:

| Benchmark | Target | Current |
|-----------|--------|---------|
| CognitiveCycle tick (p50) | < 120ms | Not yet measured |
| CognitiveCycle tick (p99) | < 500ms | Not yet measured |
| Blackboard write throughput | > 20K/s | 20K/s ✅ |
| Blackboard query latency | < 15µs | 12µs ✅ |
| IIT Φ (async, 8-node) | < 500ms | ~500ms ✅ |
| GWT broadcast | < 1ms | 0.059ms ✅ |
| AST schema update | < 2ms | 0.117ms ✅ |
| Safety Z3 fast path | < 8ms | Not yet measured |
| Quantum VQE (10-qubit, 100 shots) | < 5s | Not yet measured |

---

### 4.4 — Documentation Sprint

Phase 4 wiki pages needed:
- `Deployment-Guide` — Docker + Kubernetes + bare metal
- `MCP-Gateway` — full tool schema for all 29 modules
- `CognitiveCycle-Timing` — phase-by-phase budget analysis
- `Multi-Agent-Setup` — 2-agent Rings Network configuration
- `Privacy-Pipeline` — FHE + BCI + consciousness end-to-end guide

---

## Science Gaps to Address in Phase 4

1. **Φ computation at scale**: Current PyPhi implementation is O(2^n) — needs approximation for n > 8 neurons. Candidate: `pyphi.Approximation` or neural mass model reduction.
2. **Quantum noise models**: VQE results on real hardware (IBM Quantum) differ from statevector simulation by 15–40% — need noise-aware confidence calibration in `QuantumBlackboardAdapter`.
3. **STDP convergence in CognitiveCycle**: 50ms aggregation windows may be too short for STDP to update meaningfully — need to measure weight delta magnitude per tick.
4. **HE circuit depth budget**: Encrypted IIT Φ is expected to require multiplicative depth > 20 — need to verify CKKS parameters can support this without blowing noise budget.
5. **Multi-agent trust bootstrapping**: How does a new AGI agent earn enough trust reputation to have its GOAL_AGREEMENT messages accepted? (See Discussion #49)

---

## Relationship to Earlier Phases

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 1 | Core modules (29 modules built) | ✅ Complete |
| Phase 2 | Integration layer (Blackboard, EventBus, adapters) | ✅ Complete (16/29 wired) |
| Phase 3 | Bug fixes + benchmarks + Rings Network | ✅ Complete |
| **Phase 4** | **Full-system integration + production deployment** | 🔄 In Progress |

---

## Related Issues and Discussions

- Issue #41 — CognitiveCycle implementation
- Issue #39 — CognitiveCycle design
- Issue #116–#120 — Remaining Blackboard adapter issues
- Issue #109 — Phase 4 milestone tracking
- Discussion #121 — Poll: which module to wire next
- Discussion #35 — Full-system orchestration planning
- Discussion #27 — Phase 2 planning (historical context)
