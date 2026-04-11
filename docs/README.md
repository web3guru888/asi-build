# ASI-Build Documentation

> **Current codebase**: 28 modules in `src/asi_build/`, ~181K LOC, 2,500+ tests passing.

This directory contains documentation for the ASI-Build project. Some documents were written for an earlier v1 codebase and are marked as historical artifacts — always cross-reference against the actual source code.

## Start Here

- **[Root README](/README.md)** — Project overview, installation, quick start
- **[CLAUDE.md](/CLAUDE.md)** — Quick reference for AI coding assistants

## Documentation Index

### Technical
- [`technical/ARCHITECTURE.md`](technical/ARCHITECTURE.md) — System architecture and design patterns
- [`technical/SYSTEM_DESIGN.md`](technical/SYSTEM_DESIGN.md) — Infrastructure design
- [`technical/SYSTEM_DIAGRAMS.md`](technical/SYSTEM_DIAGRAMS.md) — Architecture diagrams
- [`technical/DESIGN_DECISIONS.md`](technical/DESIGN_DECISIONS.md) — Key decisions and trade-offs

### API
- [`api/API_REFERENCE.md`](api/API_REFERENCE.md) — Endpoint documentation
- [`api/INTEGRATION_GUIDE.md`](api/INTEGRATION_GUIDE.md) — Integration tutorials
- [`api/openapi.yaml`](api/openapi.yaml) — OpenAPI specification

### Modules
- [`modules/README.md`](modules/README.md) — Index of all 28 current modules

### Integration
- [`integration/INTEGRATION_OVERVIEW.md`](integration/INTEGRATION_OVERVIEW.md) — Integration architecture *(v1 artifact)*
- [`integration/EXTERNAL_INTEGRATIONS.md`](integration/EXTERNAL_INTEGRATIONS.md) — Third-party integrations
- [`integration/DEVELOPMENT_WORKFLOW.md`](integration/DEVELOPMENT_WORKFLOW.md) — Development setup

### Safety
- [`safety/SAFETY_OVERVIEW.md`](safety/SAFETY_OVERVIEW.md) — Safety guidelines

## Current Module List (28 modules)

These are the actual modules in `src/asi_build/`:

| Module | Description |
|--------|-------------|
| `agi_communication` | Multi-agent communication protocols |
| `agi_economics` | Economic modeling for AGI systems |
| `agi_reproducibility` | Experiment tracking and validation |
| `bci` | Brain-computer interface integration |
| `bio_inspired` | Bio-inspired algorithms |
| `blockchain` | Blockchain/Web3 integration |
| `cognitive_synergy` | Cognitive synergy and cross-module reasoning |
| `compute` | Compute pool management |
| `consciousness` | Consciousness modeling |
| `deployment` | Deployment automation |
| `distributed_training` | Distributed training orchestration |
| `federated` | Federated learning |
| `graph_intelligence` | Graph-based intelligence |
| `holographic` | Holographic memory systems |
| `homomorphic` | Homomorphic encryption |
| `integration` | Cross-module integration (EventBus, Blackboard) |
| `integrations` | External service integrations |
| `knowledge_graph` | Knowledge graph storage and queries |
| `knowledge_management` | Knowledge management utilities |
| `memgraph_toolbox` | Memgraph database toolbox |
| `neuromorphic` | Neuromorphic computing |
| `optimization` | Optimization algorithms |
| `pln_accelerator` | Probabilistic logic network accelerator |
| `quantum` | Quantum computing simulation |
| `reasoning` | Reasoning engine |
| `safety` | Safety monitoring and controls |
| `servers` | Server infrastructure |
| `vectordb` | Vector database for semantic search |

## ⚠️ Note on v1 Documentation

Several documents in this directory were written for a v1 codebase that described "47 subsystems" — many of which were aspirational placeholders. The current codebase has **28 real modules** with working code and tests. Documents marked with "v1 artifact" banners should be treated as historical reference only.

## License

MIT — see [LICENSE](/LICENSE).
