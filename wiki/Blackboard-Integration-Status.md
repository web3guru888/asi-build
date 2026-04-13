# Cognitive Blackboard — Module Integration Status

This page tracks which ASI:BUILD modules are currently wired to the Cognitive Blackboard and what each adapter publishes/consumes.

**Last updated:** April 12, 2026 · Commit [`3b3916e`](https://github.com/web3guru888/asi-build/commit/3b3916ea646091ba6e5debb5662a66853285a4c8)

---

## Summary

| Status | Count |
|--------|-------|
| ✅ Wired to Blackboard | **8** |
| 🔲 Not yet wired | **21** |
| **Total modules** | **29** |

---

## ✅ Wired Adapters (8)

### 1. Consciousness Adapter
**File:** `src/asi_build/integration/adapters/consciousness_adapter.py`  
**Module:** `consciousness`

| Direction | Topics / Events |
|-----------|----------------|
| **Produces** | `consciousness.state`, `consciousness.phi`, `consciousness.gwt`, `consciousness.ast` |
| **Consumes** | `reasoning.*` |
| **Emits events** | `consciousness.state.changed`, `consciousness.phi.updated` |
| **Listens** | `reasoning.inference.completed` |

**Highlights:**
- Publishes IIT Φ value (TPM-based IIT 3.0) every poll cycle
- Φ=0 on random networks is expected and documented
- GWT and AST timings available as separate topics

---

### 2. Knowledge Graph Adapter
**File:** `src/asi_build/integration/adapters/knowledge_graph_adapter.py`  
**Module:** `knowledge_graph`

| Direction | Topics / Events |
|-----------|----------------|
| **Produces** | `knowledge_graph.triples`, `knowledge_graph.paths`, `knowledge_graph.stats` |
| **Consumes** | `consciousness.*` |
| **Emits events** | `knowledge_graph.triple.added`, `knowledge_graph.path.found` |
| **Listens** | `consciousness.state.changed` |

**Highlights:**
- Bi-temporal KG — all entries carry `valid_from`/`valid_to` timestamps
- Path results include full semantic distance scoring
- Consciousness state modulates query prioritization

---

### 3. Reasoning Adapter
**File:** `src/asi_build/integration/adapters/reasoning_adapter.py`  
**Module:** `reasoning`

| Direction | Topics / Events |
|-----------|----------------|
| **Produces** | `reasoning.inference`, `reasoning.mode`, `reasoning.confidence` |
| **Consumes** | `consciousness.*`, `knowledge_graph.*` |
| **Emits events** | `reasoning.inference.completed`, `reasoning.mode.switched` |
| **Listens** | `consciousness.state.changed`, `knowledge_graph.triple.added` |

**Highlights:**
- 6 reasoning modes (deductive, inductive, abductive, analogical, causal, probabilistic)
- Mode is selected adaptively based on incoming consciousness state
- Confidence scores feed into downstream module gating

---

### 4. Cognitive Synergy Adapter
**File:** `src/asi_build/integration/adapters/cognitive_synergy_adapter.py`  
**Module:** `cognitive_synergy`

| Direction | Topics / Events |
|-----------|----------------|
| **Produces** | `cognitive_synergy.metrics`, `cognitive_synergy.patterns`, `cognitive_synergy.emergent` |
| **Consumes** | `consciousness.*`, `reasoning.*` |
| **Emits events** | `cognitive_synergy.pair.activated`, `cognitive_synergy.emergent.detected` |
| **Listens** | `consciousness.state.changed`, `reasoning.inference.completed` |

**Highlights:**
- Tracks 10 synergy pairs (PRIMUS theory)
- LZ76 complexity resonance metric (fixed in `3b3916e`)
- Emergent property detection (DBSCAN + PCA)

---

### 5. Rings Network Adapter
**File:** `src/asi_build/integration/adapters/rings_adapter.py`  
**Module:** `rings` (Rings Network SDK)  
**LOC:** 635 lines

| Direction | Topics / Events |
|-----------|----------------|
| **Produces** | `rings.peer_state`, `rings.message_received`, `rings.did_status` |
| **Consumes** | `consciousness.*`, `reasoning.*` |
| **Emits events** | `rings.message.received`, `rings.did.authenticated`, `rings.peer.connected` |
| **Listens** | `consciousness.state.changed`, `reasoning.inference.completed` |

**Highlights:**
- DID-auth P2P transport via Rings Network SDK
- 108 dedicated tests
- Phase 1 of distributed cognition roadmap
- See [Rings Network wiki page](Rings-Network) for full documentation

---

### 6. Bio-Inspired Adapter *(new in `3b3916e`)*
**File:** `src/asi_build/integration/adapters/bio_inspired_adapter.py`  
**LOC:** 535 lines

| Direction | Topics / Events |
|-----------|----------------|
| **Produces** | `bio_inspired.fitness`, `bio_inspired.population`, `bio_inspired.homeostasis`, `bio_inspired.system_status` |
| **Consumes** | `reasoning.*`, `consciousness.*`, `cognitive_synergy.*` |
| **Emits events** | `bio_inspired.fitness.improved`, `bio_inspired.homeostasis.alert`, `bio_inspired.system_status.changed` |
| **Listens** | `reasoning.inference.completed`, `consciousness.state.changed` |

**Highlights:**
- Homeostatic alerts publish at `CRITICAL` priority immediately (no poll delay)
- Sleeping/dreaming consciousness states lower homeostatic tolerance ranges
- Synergy metrics can serve as fitness evaluation criteria for the evolutionary optimizer
- Open question: should safety module gate objective function selection? (Issue #37)

---

### 7. Graph Intelligence Adapter *(new in `3b3916e`)*
**File:** `src/asi_build/integration/adapters/graph_intelligence_adapter.py`  
**LOC:** 393 lines

| Direction | Topics / Events |
|-----------|----------------|
| **Produces** | `graph_intelligence.communities`, `graph_intelligence.reasoning`, `graph_intelligence.graph_stats` |
| **Consumes** | `knowledge_graph.*`, `reasoning.*`, `consciousness.*` |
| **Emits events** | `graph_intelligence.communities.detected`, `graph_intelligence.reasoning.completed`, `graph_intelligence.graph.updated` |
| **Listens** | `knowledge_graph.triple.added`, `reasoning.inference.completed` |

**Highlights:**
- `knowledge_graph.triple.added` triggers re-analysis through FastToG
- Community membership becomes a KG edge attribute (closes KG↔graph_intelligence loop)
- Consciousness broadcasts prioritize communities of recently activated concepts
- Modularity score published with every community update

---

### 8. Knowledge Management Adapter *(new in `3b3916e`)*
**File:** `src/asi_build/integration/adapters/knowledge_management_adapter.py`  
**LOC:** 489 lines

| Direction | Topics / Events |
|-----------|----------------|
| **Produces** | `knowledge_management.synthesis`, `knowledge_management.patterns`, `knowledge_management.performance`, `knowledge_management.learning` |
| **Consumes** | `knowledge_graph.*`, `reasoning.*`, `consciousness.*` |
| **Emits events** | `knowledge_management.synthesis.completed`, `knowledge_management.pattern.detected`, `knowledge_management.performance.degraded` |
| **Listens** | `knowledge_graph.triple.added`, `reasoning.inference.completed` |

**Highlights:**
- `ContextualLearner` triggers an adaptation pass on every `reasoning.inference.completed` event
- Synthesis results publish at `HIGH` priority for downstream planning modules
- Performance degradation can gate expensive reasoning operations
- 4 synthesis types: keyword, semantic, fuzzy, comprehensive

---

## 🔲 Not Yet Wired (21 modules)

These modules have open issues for Blackboard integration. Each issue has a full design sketch and follows the pattern established by the 8 adapters above.

| Module | Issue | Complexity Estimate |
|--------|-------|---------------------|
| `holographic` | [#56](https://github.com/web3guru888/asi-build/issues/56) | Medium |
| `federated` | [#58](https://github.com/web3guru888/asi-build/issues/58) | Medium |
| `quantum` | [#53](https://github.com/web3guru888/asi-build/issues/53) | High |
| `homomorphic` | *(planned)* | High |
| `neuromorphic` | *(planned)* | Medium |
| `agi_communication` | [#48](https://github.com/web3guru888/asi-build/issues/48) | Medium |
| `agi_economics` | *(planned)* | Medium |
| `agi_reproducibility` | [#80](https://github.com/web3guru888/asi-build/issues/80) | Medium |
| `vectordb` | [#77](https://github.com/web3guru888/asi-build/issues/77) | Low |
| `distributed_training` | [#75](https://github.com/web3guru888/asi-build/issues/75) | High |
| `compute` | [#70](https://github.com/web3guru888/asi-build/issues/70) | Medium |
| `optimization` | [#83](https://github.com/web3guru888/asi-build/issues/83) | Medium |
| `integrations` | [#90](https://github.com/web3guru888/asi-build/issues/90) | Medium |
| `bci` | *(planned)* | High |
| `blockchain` | *(planned)* | Low |
| `deployment` | *(planned)* | Low |
| `servers` | *(planned)* | Low |
| `pln_accelerator` | *(planned)* | Medium |
| `knowledge_graph_pathfinder` | *(planned, sub-module)* | Medium |
| `memgraph_toolbox` | *(planned)* | Low |
| `kenny_graph` | [#89](https://github.com/web3guru888/asi-build/issues/89) | Medium |

---

## Topic Namespace Map

All Blackboard topics follow the pattern `<module>.<subtopic>`:

```
consciousness.*       → IIT Φ, GWT, AST, state
knowledge_graph.*     → triples, paths, stats
reasoning.*           → inference, mode, confidence
cognitive_synergy.*   → metrics, patterns, emergent
rings.*               → peer_state, message_received, did_status
bio_inspired.*        → fitness, population, homeostasis, system_status
graph_intelligence.*  → communities, reasoning, graph_stats
knowledge_management.* → synthesis, patterns, performance, learning
```

---

## Writing a New Adapter

The pattern is well-established. Copy the closest existing adapter and adapt:

1. **Define topics** — what your module produces and what it reads
2. **Implement `get_module_info()`** — return a `ModuleInfo` with capabilities
3. **Implement `produce()`** — instantiate your module and serialize state to `BlackboardEntry`
4. **Implement `_consume_*()`** — handle incoming entries from other modules
5. **Implement `on_event()`** — react to `CognitiveEvent` objects
6. **Register** in `src/asi_build/integration/adapters/__init__.py`

See [Cognitive Blackboard](Cognitive-Blackboard) for the full protocol documentation.

**Good entry points for contributors:**
- `vectordb` adapter (Issue #77) — straightforward, well-defined API surface
- `blockchain` adapter *(planned)* — simple event bridge, no real-time loop needed
- `deployment` adapter *(planned)* — health-check style metrics only

---

## Related Pages

- [Cognitive Blackboard](Cognitive-Blackboard) — protocol, thread safety, entry lifecycle
- [Rings Network](Rings-Network) — distributed Blackboard via P2P
- [Architecture](Architecture) — system design overview
- [CognitiveCycle](CognitiveCycle) — how all adapters are ticked in a real-time loop
