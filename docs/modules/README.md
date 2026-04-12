# ASI-Build Module Index

> **29 modules** in `src/asi_build/` · **24 blackboard adapters** · **1 stable, 7 beta, 12 alpha, 9 experimental**

## Module List

| # | Module | Maturity | Adapter | Description |
|---|--------|----------|---------|-------------|
| 1 | [**agi_communication**](agi_communication.md) | 🟡 alpha | `AGICommunicationBlackboardAdapter` | Multi-agent communication protocols, trust authentication, goal negotiation |
| 2 | [**agi_economics**](agi_economics.md) | 🔴 experimental | `AGIEconomicsBlackboardAdapter` | Token economics, bonding curves, reputation systems, game theory |
| 3 | [**agi_reproducibility**](agi_reproducibility.md) | 🟡 alpha | `ReproducibilityBlackboardAdapter` | Experiment tracking, version management, reproducibility auditing |
| 4 | [**bci**](bci.md) | 🔴 experimental | `BCIBlackboardAdapter` | Brain-computer interface: EEG/fNIRS signal processing, neural decoding |
| 5 | [**bio_inspired**](bio_inspired.md) | 🟢 beta | `BioInspiredAdapter` | Bio-inspired algorithms: evolutionary optimization, swarm intelligence, homeostasis |
| 6 | [**blockchain**](blockchain.md) | 🟡 alpha | `BlockchainBlackboardAdapter` | Hash management, Merkle trees, hash chains, integrity verification |
| 7 | [**cognitive_synergy**](cognitive_synergy.md) | 🟢 beta | `CognitiveSynergyAdapter` | Cross-module synergy measurement, emergence detection, coherence tracking |
| 8 | [**compute**](compute.md) | 🟡 alpha | `ComputeBlackboardAdapter` | Job scheduling, resource allocation, compute pool management |
| 9 | [**consciousness**](consciousness.md) | 🟢 beta | `ConsciousnessAdapter` | IIT Φ computation, Global Workspace Theory, Attention Schema Theory |
| 10 | [**deployment**](deployment.md) | 🔴 experimental | — | CI/CD integration, CUDO + HuggingFace deployment scripts |
| 11 | [**distributed_training**](distributed_training.md) | 🟡 alpha | `DistributedTrainingAdapter` | Federated orchestration, Byzantine-tolerant gradient aggregation |
| 12 | [**federated**](federated.md) | 🟡 alpha | `FederatedLearningBlackboardAdapter` | Federated learning: FedAvg, differential privacy, secure aggregation |
| 13 | [**graph_intelligence**](graph_intelligence.md) | 🟢 beta | `GraphIntelligenceAdapter` | Community detection (Louvain, Girvan-Newman), graph-based reasoning |
| 14 | [**holographic**](holographic.md) | 🔴 experimental | `HolographicBlackboardAdapter` | Holographic memory engine, light field processing, volumetric display |
| 15 | [**homomorphic**](homomorphic.md) | 🟡 alpha | — (Issue #120) | Fully Homomorphic Encryption: CKKS/BFV/BGV, encrypted ML, MPC |
| 16 | [**integration**](integration.md) | 🟢 beta | N/A (IS the layer) | Cognitive Blackboard, EventBus, CognitiveCycle, 24 adapter protocols |
| 17 | [**integrations**](integrations.md) | 🟡 alpha | `IntegrationsBlackboardBridge` | LangChain-Memgraph, SQL-to-Graph (HyGM), MCP-Memgraph bridge |
| 18 | [**knowledge_graph**](knowledge_graph.md) | ✅ stable | `KnowledgeGraphAdapter` | Bi-temporal knowledge graph (SQLite), A* pathfinding, contradiction detection |
| 19 | [**knowledge_management**](knowledge_management.md) | 🟡 alpha | `KnowledgeManagementAdapter` | Knowledge engine, predictive synthesis, contextual learning |
| 20 | [**memgraph_toolbox**](memgraph_toolbox.md) | 🔴 experimental | — | Memgraph graph database toolbox, Cypher query utilities |
| 21 | [**neuromorphic**](neuromorphic.md) | 🔴 experimental | `NeuromorphicBlackboardAdapter` | Spiking neural networks, STDP learning, neuromorphic hardware simulation |
| 22 | [**optimization**](optimization.md) | 🟡 alpha | `VLABlackboardAdapter` (partial) | VLA++ optimization, hyperparameter tuning |
| 23 | [**pln_accelerator**](pln_accelerator.md) | 🟡 alpha | — | Probabilistic Logic Network accelerator (FPGA, quantum, distributed) |
| 24 | [**quantum**](quantum.md) | 🔴 experimental | `QuantumBlackboardAdapter` | Quantum circuit simulation, hybrid ML, QAOA, VQE |
| 25 | [**reasoning**](reasoning.md) | 🟡 alpha | `ReasoningAdapter` | Hybrid reasoning: deductive, inductive, abductive, analogical modes |
| 26 | [**rings**](rings.md) | 🟢 beta | `RingsNetworkAdapter` | Rings P2P network SDK: DHT, DID authentication, reputation scoring |
| 27 | [**safety**](safety.md) | 🟢 beta | `SafetyBlackboardAdapter` | Constitutional AI, ethical verification, formal theorem proving, governance |
| 28 | [**servers**](servers.md) | 🔴 experimental | `KennyGraphBlackboardAdapter` | Kenny Graph SSE server, Kenny MCP server |
| 29 | [**vectordb**](vectordb.md) | 🟡 alpha | `VectorDBBlackboardAdapter` | Vector database: semantic search, embedding pipeline, multi-backend |

## Maturity Levels

| Level | Count | Meaning |
|-------|-------|---------|
| ✅ **stable** | 1 | Production-ready, well-tested, API frozen |
| 🟢 **beta** | 7 | Feature-complete, tested, API may evolve |
| 🟡 **alpha** | 12 | Functional, partial test coverage, API unstable |
| 🔴 **experimental** | 9 | Proof-of-concept, may have missing features |

## Architecture

### Integration Layer

The `integration` module provides the **Cognitive Blackboard** and **EventBus** — the shared workspace enabling cross-module communication. The **CognitiveCycle** orchestrates a real-time perception → cognition → action tick loop. All 24 blackboard adapters implement the `BlackboardProducer`, `BlackboardConsumer`, and `BlackboardTransformer` protocols defined here.

```
┌─────────────────────────────────────────────────┐
│              CognitiveCycle                       │
│         (perception → cognition → action)         │
├─────────────────────────────────────────────────┤
│              CognitiveBlackboard                  │
│    ┌──────────┬──────────┬──────────┐            │
│    │ Producers│ Consumers│Transformers│           │
│    │ (post)   │ (query)  │ (enrich)  │           │
│    └──────────┴──────────┴──────────┘            │
├─────────────────────────────────────────────────┤
│              EventBus (pub/sub)                   │
│         fnmatch wildcards · priority dispatch     │
└─────────────────────────────────────────────────┘
```

### Key Module Groups

| Group | Modules | Purpose |
|-------|---------|---------|
| **Core Intelligence** | reasoning, knowledge_graph, consciousness, cognitive_synergy | Thinking, memory, awareness |
| **Learning** | federated, distributed_training, bio_inspired, neuromorphic | Training and adaptation |
| **Security** | safety, blockchain, homomorphic, rings | Safety, integrity, privacy, P2P trust |
| **Infrastructure** | compute, vectordb, graph_intelligence, integration | Resource management, search, coordination |
| **Interfaces** | bci, holographic, servers, integrations | External world interaction |
| **Research** | quantum, pln_accelerator, agi_communication, agi_economics | Experimental capabilities |

### Safety Architecture

The `SafetyBlackboardAdapter` is **fail-closed** — if safety verification fails, operations are blocked. It automatically verifies proposals from reasoning and economics modules with CRITICAL priority on verification failures.

## Test Coverage

The project has **3,000+ passing tests** across 40+ test files. Run with:

```bash
pytest                    # All tests
pytest tests/ -x          # Stop on first failure
pytest --tb=short -q      # Quick summary
```

## ⚠️ Historical Note

Previous documentation described "47 subsystems" — this was aspirational and included modules that existed only as templates. The current **29 modules** represent the actual working codebase. Many v1 module names (e.g., `reality_engine`, `divine_mathematics`, `cosmic`, `telepathy`, `omniscience`) were removed during the restructuring.

## License

MIT — see [LICENSE](/LICENSE).
