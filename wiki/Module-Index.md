# Module Index

All 29 modules in `src/asi_build/`. Status legend:

- 🟢 **Implemented** — Core algorithms present, tested, documented
- 🟡 **Structural** — Framework and interfaces defined; full backends pending

---

## Core Cognitive Modules

| Module | Status | Description | LOC | Path |
|--------|--------|-------------|-----|------|
| `consciousness` | 🟢 | Multi-theory consciousness: GWT, IIT (Φ), AST, metacognition, predictive processing, attention schema — 15 submodules | ~12,960 | `src/asi_build/consciousness/` |
| `cognitive_synergy` | 🟢 | Synergy metrics: mutual information, transfer entropy, phase-locking value, LZ complexity | ~6,314 | `src/asi_build/cognitive_synergy/` |
| `knowledge_graph` | 🟢 | Bi-temporal knowledge graph, provenance tracking, A\* pathfinding, pheromone-based learning | ~1,468 | `src/asi_build/knowledge_graph/` |
| `reasoning` | 🟡 | Hybrid symbolic-neural reasoning engine (framework scaffolding, adapters wired) | ~922 | `src/asi_build/reasoning/` |
| `graph_intelligence` | 🟢 | KG reasoning with FastToG (arXiv:2501.14300), Memgraph integration, community detection | ~8,762 | `src/asi_build/graph_intelligence/` |

## Integration

| Module | Status | Description | LOC | Path |
|--------|--------|-------------|-----|------|
| `integration` | 🟢 | Cognitive Blackboard + EventBus. 4 module adapters (consciousness, KG, synergy, reasoning) | ~3,782 | `src/asi_build/integration/` |
| `integrations` | 🟢 | LangChain-Memgraph adapter, MCP-Memgraph server, SQL→graph migration agent, HyGM | ~7,217 | `src/asi_build/integrations/` |

## Security & Formal Methods

| Module | Status | Description | LOC | Path |
|--------|--------|-------------|-----|------|
| `homomorphic` | 🟢\* | FHE: BGV, BFV, CKKS schemes with polynomial ring arithmetic | ~12,258 | `src/asi_build/homomorphic/` |
| `safety` | 🟢\* | Constitutional AI, SymPy formal verification, DAO governance, Merkle audit ledger | ~6,523 | `src/asi_build/safety/` |
| `blockchain` | 🟡 | Audit trails, IPFS storage, Web3 interaction | ~5,963 | `src/asi_build/blockchain/` |

> \* **Known issues**: `homomorphic` NTT has broken polynomial ring arithmetic ([issue #8](https://github.com/web3guru888/asi-build/issues/8)). `safety` `formal_verification` auto-proves all statements ([issue #7](https://github.com/web3guru888/asi-build/issues/7)).

## Compute & Optimization

| Module | Status | Description | LOC | Path |
|--------|--------|-------------|-----|------|
| `compute` | 🟡 | Job scheduling, resource management, GPU allocation | ~11,697 | `src/asi_build/compute/` |
| `optimization` | 🟡 | PyTorch quantization, pruning, knowledge distillation | ~4,166 | `src/asi_build/optimization/` |
| `distributed_training` | 🟡 | Federated orchestration, Byzantine tolerance, secure aggregation | ~8,595 | `src/asi_build/distributed_training/` |
| `federated` | 🟡 | Federated learning framework with secure aggregation | ~6,811 | `src/asi_build/federated/` |
| `quantum` | 🟡 | Quantum-classical hybrid via Qiskit (circuit templates implemented) | ~5,330 | `src/asi_build/quantum/` |

## Bio-Inspired & Neural

| Module | Status | Description | LOC | Path |
|--------|--------|-------------|-----|------|
| `bio_inspired` | 🟡 | Evolutionary optimization, swarm intelligence, genetic algorithms | ~5,239 | `src/asi_build/bio_inspired/` |
| `neuromorphic` | 🟡 | Spiking neural networks, brain-inspired processors | ~5,226 | `src/asi_build/neuromorphic/` |
| `bci` | 🟢 | Brain-Computer Interface: EEG processing, CSP, SSVEP detection | ~8,294 | `src/asi_build/bci/` |

## Knowledge & Storage

| Module | Status | Description | LOC | Path |
|--------|--------|-------------|-----|------|
| `vectordb` | 🟡 | Unified client for Pinecone, Qdrant, Weaviate (backends not fully wired) | ~8,142 | `src/asi_build/vectordb/` |
| `knowledge_management` | 🟡 | Omniscience knowledge management system | ~5,816 | `src/asi_build/knowledge_management/` |
| `memgraph_toolbox` | 🟡 | Memgraph tools: PageRank, betweenness centrality, Cypher helpers | ~917 | `src/asi_build/memgraph_toolbox/` |
| `pln_accelerator` | 🟡 | Hardware-accelerated Probabilistic Logic Networks | ~12,653 | `src/asi_build/pln_accelerator/` |

## Infrastructure & Deployment

| Module | Status | Description | LOC | Path |
|--------|--------|-------------|-----|------|
| `deployment` | 🟡 | CUDO Compute + HuggingFace Transformers deployment | ~3,378 | `src/asi_build/deployment/` |
| `servers` | 🟡 | MCP + SSE graph servers | ~1,024 | `src/asi_build/servers/` |
| `holographic` | 🟡 | Volumetric display, spatial audio, mixed reality engine | ~8,430 | `src/asi_build/holographic/` |

## AGI Research Modules

| Module | Status | Description | LOC | Path |
|--------|--------|-------------|-----|------|
| `agi_communication` | 🟡 | AGI communication protocols | ~4,267 | `src/asi_build/agi_communication/` |
| `agi_economics` | 🟡 | AGI economics: algorithms, DeFi, tokenomics | ~7,741 | `src/asi_build/agi_economics/` |
| `agi_reproducibility` | 🟡 | Experiment tracking, PLN validation, reproducibility | ~7,926 | `src/asi_build/agi_reproducibility/` |
| `rings` | 🔬 | Rings Network P2P integration: async SDK wrapper, DID auth, reputation scoring | ~1,951 | `src/asi_build/rings/` |

---

## By Implementation Status

### 🟢 Implemented (8 modules)

`consciousness` · `cognitive_synergy` · `knowledge_graph` · `graph_intelligence` · `integration` · `integrations` · `bci` · `homomorphic`\* · `safety`\*

### 🟡 Structural (19 modules)

`reasoning` · `vectordb` · `optimization` · `quantum` · `compute` · `bio_inspired` · `deployment` · `memgraph_toolbox` · `blockchain` · `distributed_training` · `holographic` · `neuromorphic` · `pln_accelerator` · `knowledge_management` · `federated` · `agi_economics` · `agi_reproducibility` · `agi_communication` · `servers`

### 🔬 Experimental (1 module)

`rings` — Rings Network integration (Phase 4 preview)

---

## Module Sizes (Top 10)

```
pln_accelerator      12,653 LOC
consciousness        12,960 LOC
homomorphic          12,258 LOC
compute              11,697 LOC
graph_intelligence    8,762 LOC
bci                   8,294 LOC
distributed_training  8,595 LOC
holographic           8,430 LOC
vectordb              8,142 LOC
agi_reproducibility   7,926 LOC
```

---

## Related Pages

- [[Architecture]] — How modules fit together
- [[Cognitive Blackboard]] — The integration layer connecting modules
- [[Roadmap]] — When will structural modules be completed?
- [[Contributing]] — Want to implement a structural module? See this first.
