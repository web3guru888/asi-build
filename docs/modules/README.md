# ASI-Build Module Index

> **28 modules** in `src/asi_build/` — auto-generated from actual codebase structure.

## Module List

| # | Module | Path | Description |
|---|--------|------|-------------|
| 1 | **agi_communication** | `src/asi_build/agi_communication/` | Multi-agent communication protocols |
| 2 | **agi_economics** | `src/asi_build/agi_economics/` | Economic modeling and resource allocation for AGI |
| 3 | **agi_reproducibility** | `src/asi_build/agi_reproducibility/` | Experiment tracking, validation, reproducibility |
| 4 | **bci** | `src/asi_build/bci/` | Brain-computer interface integration |
| 5 | **bio_inspired** | `src/asi_build/bio_inspired/` | Bio-inspired algorithms (evolutionary, swarm, etc.) |
| 6 | **blockchain** | `src/asi_build/blockchain/` | Blockchain/Web3 integration |
| 7 | **cognitive_synergy** | `src/asi_build/cognitive_synergy/` | Cross-module cognitive synergy and reasoning coordination |
| 8 | **compute** | `src/asi_build/compute/` | Compute pool management and scheduling |
| 9 | **consciousness** | `src/asi_build/consciousness/` | Consciousness modeling (IIT-inspired metrics) |
| 10 | **deployment** | `src/asi_build/deployment/` | CI/CD and deployment automation |
| 11 | **distributed_training** | `src/asi_build/distributed_training/` | Distributed model training orchestration |
| 12 | **federated** | `src/asi_build/federated/` | Federated learning across distributed nodes |
| 13 | **graph_intelligence** | `src/asi_build/graph_intelligence/` | Graph-based reasoning and intelligence |
| 14 | **holographic** | `src/asi_build/holographic/` | Holographic memory and associative storage |
| 15 | **homomorphic** | `src/asi_build/homomorphic/` | Homomorphic encryption (⚠️ needs overhaul — see issues) |
| 16 | **integration** | `src/asi_build/integration/` | Cross-module integration: EventBus + Cognitive Blackboard |
| 17 | **integrations** | `src/asi_build/integrations/` | External service integrations |
| 18 | **knowledge_graph** | `src/asi_build/knowledge_graph/` | Knowledge graph storage and SPARQL-like queries |
| 19 | **knowledge_management** | `src/asi_build/knowledge_management/` | Knowledge management utilities |
| 20 | **memgraph_toolbox** | `src/asi_build/memgraph_toolbox/` | Memgraph graph database toolbox |
| 21 | **neuromorphic** | `src/asi_build/neuromorphic/` | Neuromorphic computing (spiking neural networks) |
| 22 | **optimization** | `src/asi_build/optimization/` | Optimization algorithms and hyperparameter tuning |
| 23 | **pln_accelerator** | `src/asi_build/pln_accelerator/` | Probabilistic Logic Network accelerator |
| 24 | **quantum** | `src/asi_build/quantum/` | Quantum computing simulation |
| 25 | **reasoning** | `src/asi_build/reasoning/` | Reasoning engine (deductive, inductive, abductive) |
| 26 | **safety** | `src/asi_build/safety/` | Safety monitoring, circuit breakers, emergency controls |
| 27 | **servers** | `src/asi_build/servers/` | Server infrastructure and API hosting |
| 28 | **vectordb** | `src/asi_build/vectordb/` | Vector database for semantic search |

## Key Modules

### Integration Layer (NEW)
The `integration` module provides the **Cognitive Blackboard** and **EventBus** — the shared workspace enabling cross-module communication. This replaces the v1 "Kenny Integration" pattern. See `src/asi_build/integration/` for implementation.

### Safety
The `safety` module implements circuit breakers, phased autonomy controls, and emergency shutdown. All modules should register with the safety system.

### Knowledge Graph + VectorDB
Together these provide hybrid symbolic+semantic knowledge storage — the knowledge graph handles structured entity-relationship triples while vectordb enables semantic similarity search.

## Test Coverage

The project has **2,500+ passing tests** across 35+ test files. Run with:

```bash
pytest                    # All tests
pytest tests/ -x          # Stop on first failure
pytest --tb=short -q      # Quick summary
```

## ⚠️ Historical Note

Previous documentation described "47 subsystems" — this was aspirational and included modules that existed only as templates. The current **28 modules** represent the actual working codebase. Many v1 module names (e.g., `reality_engine`, `divine_mathematics`, `cosmic`, `telepathy`, `omniscience`) were removed during the restructuring.

## License

MIT — see [LICENSE](/LICENSE).
