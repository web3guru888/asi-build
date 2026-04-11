# ASI:BUILD

**A modular Python research framework for exploring AI consciousness, cognitive architectures, knowledge graphs, and multi-agent reasoning.**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
[![CI](https://github.com/web3guru888/asi-build/actions/workflows/ci.yml/badge.svg)](https://github.com/web3guru888/asi-build/actions/workflows/ci.yml)
![Status](https://img.shields.io/badge/status-research--alpha-orange)

> ⚠️ **Research Software**: ASI:BUILD is an active research framework, not a production system. Module maturity varies significantly — some are well-implemented and tested, others are structural scaffolding awaiting real backends. See the [Modules](#modules) table for per-module status.

---

## Overview

ASI:BUILD is a Python research framework exploring the computational foundations of artificial general intelligence. Inspired by Dr. Ben Goertzel's cognitive synergy approach to AGI — the idea that intelligence emerges from the interaction of diverse cognitive subsystems — the project provides modular, composable implementations of key AGI building blocks.

The framework spans consciousness modeling (Global Workspace Theory, Integrated Information Theory, Attention Schema), information-theoretic synergy metrics, knowledge graph reasoning, homomorphic encryption, quantum-classical hybrid computing, and more. Each module is designed to be used independently or composed with others to study emergent cognitive behaviors.

The `knowledge_graph` module features a bi-temporal knowledge graph with provenance tracking, A\* pathfinding, and pheromone-based learning, contributed by the [MemPalace-AGI](https://github.com/milla-jovovich/mempalace) project — an integration exploring spatial memory architectures for autonomous scientific discovery.

ASI:BUILD is research software. We prioritize correctness and clarity over performance. Published benchmarks and experimental results live in `docs/research/`. If you're looking for a production AGI framework, this isn't it — but if you want to experiment with the building blocks, you're in the right place.

---

## Architecture

```
asi-build/
├── src/
│   └── asi_build/                  # Main Python package
│       ├── consciousness/          # Multi-theory consciousness modeling
│       ├── cognitive_synergy/      # Information-theoretic synergy metrics
│       ├── graph_intelligence/     # KG reasoning + FastToG pipeline
│       ├── homomorphic/            # Fully Homomorphic Encryption (BGV/BFV/CKKS)
│       ├── knowledge_graph/        # Bi-temporal KG with provenance + A*
│       ├── vectordb/               # Unified vector DB client
│       ├── optimization/           # PyTorch model optimization
│       ├── quantum/                # Quantum-classical hybrid (Qiskit)
│       ├── reasoning/              # Hybrid symbolic-neural reasoning
│       ├── safety/                 # Constitutional AI + governance
│       │   ├── formal_verification.py  # SymPy theorem proving
│       │   └── governance/         # DAO, consensus, smart contracts,
│       │                           #   Merkle audit, entity rights
│       ├── integration/            # Cognitive Blackboard + module adapters
│       ├── integrations/           # External tool adapters
│       │   ├── langchain-memgraph/ # LangChain ↔ Memgraph adapter
│       │   ├── mcp-memgraph/       # MCP server for Memgraph
│       │   └── agents/             # SQL→graph migration agent + HyGM
│       ├── compute/                # Job scheduling + GPU allocation
│       ├── bio_inspired/           # Evolutionary + swarm intelligence
│       ├── deployment/             # Cloud deployment (CUDO + HuggingFace)
│       ├── memgraph_toolbox/       # Memgraph graph DB tools
│       ├── bci/                    # Brain-Computer Interface (EEG, CSP, SSVEP)
│       ├── blockchain/             # Audit trails, IPFS, Web3
│       ├── distributed_training/   # Federated orchestration, Byzantine tolerance
│       ├── holographic/            # Volumetric display, spatial audio, MR
│       ├── neuromorphic/           # Spiking neural networks
│       ├── pln_accelerator/        # Hardware-accelerated PLN
│       ├── knowledge_management/   # Omniscience knowledge management
│       ├── federated/              # Federated learning framework
│       ├── agi_economics/          # AGI economics: algorithms, DeFi
│       ├── agi_reproducibility/    # Experiment tracking, PLN validation
│       ├── agi_communication/      # AGI communication protocols
│       └── servers/                # MCP + SSE graph servers
├── tests/                          # Test suite (2,500+ tests)
├── examples/                       # Runnable examples + MiniMind LLM reference
├── docs/                           # Documentation + research notes
├── configs/                        # Configuration templates
├── asi-code/                       # TypeScript AI coding IDE (separate product)
└── archive/                        # Experimental v1 modules (not tested)
```

```
Cognitive Synergy Architecture:

  ┌─────────────────────────────────────────────────┐
  │                  Reasoning Layer                │
  │  symbolic ──┬── neural ──┬── causal inference  │
  └─────────────┼────────────┼────────────────────-┘
                │            │
  ┌─────────────▼────────────▼────────────────────-┐
  │               Knowledge Layer                  │
  │  graph_intelligence ──── knowledge_graph       │
  │       (FastToG)        (bi-temporal + A*)      │
  └─────────────────────────────────────────────────┘
                │            │
  ┌─────────────▼────────────▼────────────────────-┐
  │             Consciousness Layer                 │
  │  GWT ── IIT (Φ) ── AST ── metacognition       │
  └─────────────────────────────────────────────────┘
                │
  ┌─────────────▼───────────────────────────────────┐
  │              Support Modules                    │
  │  vectordb · homomorphic · quantum · safety      │
  │  compute · bio_inspired · optimization          │
  └─────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/web3guru888/asi-build.git
cd asi-build

# 2. Install with core dependencies
pip install -e .

# 3. Install optional dependencies for specific modules
pip install -e ".[consciousness]"     # GWT, IIT, synergy metrics
pip install -e ".[graph]"             # Knowledge graphs, Memgraph
pip install -e ".[ml]"                # PyTorch optimization + deployment
pip install -e ".[all]"               # Everything (includes dev tools)
```

### Hello, Consciousness

```python
from asi_build.consciousness import GlobalWorkspaceTheory

# Initialize a Global Workspace
gwt = GlobalWorkspaceTheory()

# The system starts with 8 cognitive processors
print(f"Processors: {len(gwt.cognitive_processors)}")
# Each processor monitors specific content types (visual, linguistic, motor, etc.)
for pid, proc in list(gwt.cognitive_processors.items())[:3]:
    print(f"  {pid}: interests={proc.interests}")
```

### Knowledge Graph with A* Pathfinding

```python
from asi_build.knowledge_graph import TemporalKnowledgeGraph

kg = TemporalKnowledgeGraph(db_path=":memory:")

# Add temporal facts with provenance
kg.add_triple(
    subject="ASTR-J1234",
    predicate="hasProperty",
    object="high_redshift",
    confidence=0.92,
    source="HST-observation-42"
)
kg.add_triple(
    subject="high_redshift",
    predicate="indicates",
    object="dark_energy_candidate",
    confidence=0.85,
    source="cosmology-model-7"
)

# Find paths between entities using A* pathfinding
from asi_build.knowledge_graph import KGPathfinder
pathfinder = KGPathfinder(kg)
path = pathfinder.find_path("ASTR-J1234", "dark_energy_candidate")
print(f"Path found: {path['complete']}")        # True — complete path exists
print(f"Hops: {path['hops']}, Cost: {path['cost']:.3f}")
```

### Cognitive Synergy Metrics

```python
from asi_build.cognitive_synergy import SynergyMetrics
import numpy as np

metrics = SynergyMetrics()

# Feed time series data from two cognitive modules
data_a = np.random.randn(100)
data_b = np.random.randn(100)
for i in range(len(data_a)):
    metrics.add_time_series_data("consciousness_reasoning", data_a[i], data_b[i])

# Compute synergy profile between modules
profile = metrics.compute_synergy_profile("consciousness_reasoning")
print(f"Mutual Information: {profile.mutual_information:.4f}")
print(f"Transfer Entropy: {profile.transfer_entropy:.4f}")
```

---

## Modules

| Module | Status | Description | LOC |
|--------|--------|-------------|-----|
| `consciousness` | 🟢 Implemented | Multi-theory consciousness (GWT, IIT, AST, metacognition) — 15 submodules | ~12,200 |
| `cognitive_synergy` | 🟢 Implemented | Synergy metrics: mutual info, transfer entropy, phase locking, LZ complexity | ~6,000 |
| `graph_intelligence` | 🟢 Implemented | KG reasoning with FastToG (arXiv:2501.14300), Memgraph, community detection | ~8,200 |
| `homomorphic` | 🟢 Implemented | FHE: BGV, BFV, CKKS schemes with polynomial ring arithmetic | ~11,900 |
| `knowledge_graph` | 🟢 Implemented | Bi-temporal KG, provenance tracking, A\* pathfinding, pheromone learning | ~1,450 |
| `vectordb` | 🟡 Structural | Unified client for Pinecone, Qdrant, Weaviate (backends not fully wired) | ~8,000 |
| `optimization` | 🟡 Structural | PyTorch quantization, pruning, knowledge distillation | ~4,200 |
| `quantum` | 🟡 Structural | Quantum-classical hybrid via Qiskit (circuit templates implemented) | ~5,300 |
| `reasoning` | 🟡 Structural | Hybrid symbolic-neural reasoning engine (framework scaffolding) | ~880 |
| `safety` | 🟢 Implemented | Constitutional AI + governance: SymPy formal verification, DAO (quadratic voting, liquid democracy), smart contracts, Merkle audit ledger, entity rights | ~6,200 |
| `integration` | 🟢 Implemented | Cognitive Blackboard: shared workspace + EventBus for cross-module communication. Adapters wire consciousness, KG, synergy, reasoning. | ~3,800 |
| `integrations` | 🟢 Implemented | LangChain-Memgraph adapter, MCP-Memgraph server, SQL→graph migration agent, HyGM graph modeling | ~7,300 |
| `compute` | 🟡 Structural | Job scheduling, resource management, GPU allocation | ~11,500 |
| `bio_inspired` | 🟡 Structural | Evolutionary optimization, swarm intelligence | ~4,350 |
| `deployment` | 🟡 Structural | CUDO Compute + HuggingFace Transformers deployment | ~3,350 |
| `memgraph_toolbox` | 🟡 Structural | Memgraph tools: PageRank, betweenness centrality, Cypher helpers | ~930 |
| `bci` | 🟢 Implemented | Brain-Computer Interface: EEG processing, CSP, SSVEP detection | ~8,000 |
| `blockchain` | 🟡 Structural | Audit trails, IPFS storage, Web3 interaction | ~5,950 |
| `distributed_training` | 🟡 Structural | Federated orchestration, Byzantine tolerance, secure aggregation | ~8,200 |
| `holographic` | 🟡 Structural | Volumetric display, spatial audio, mixed reality engine | ~8,000 |
| `neuromorphic` | 🟡 Structural | Spiking neural networks, brain-inspired processors | ~3,700 |
| `pln_accelerator` | 🟡 Structural | Hardware-accelerated Probabilistic Logic Networks | ~12,500 |
| `knowledge_management` | 🟡 Structural | Omniscience knowledge management system | ~5,500 |
| `federated` | 🟡 Structural | Federated learning framework with secure aggregation | ~6,400 |
| `agi_economics` | 🟡 Structural | AGI economics: algorithms, blockchain, DeFi | ~7,200 |
| `agi_reproducibility` | 🟡 Structural | Experiment tracking, PLN validation, reproducibility | ~7,500 |

**Status legend:**
- 🟢 **Implemented** — Core algorithms present, tested, documented
- 🟡 **Structural** — Framework and interfaces defined; backends or full implementations pending
- 🔴 **Experimental** — In development, may be broken

> The `archive/` directory contains experimental/aspirational modules from v1. These are preserved for reference but are not part of the main package and are not tested.
> The `examples/` directory includes MiniMind, a third-party small LLM reference project (Apache 2.0).

---

## Examples

See the [`examples/`](examples/) directory:

```
examples/
├── consciousness_demo.py        # GWT broadcast + IIT Φ measurement
├── knowledge_graph_demo.py      # Bi-temporal KG with A* pathfinding
├── synergy_analysis.py          # Information-theoretic synergy metrics
├── graph_intelligence_demo.py   # FastToG reasoning pipeline
├── homomorphic_demo.py          # FHE encrypt → compute → decrypt
└── quantum_hybrid_demo.py       # Quantum circuit + classical postprocessing
```

---

## Development

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Or use Make
make install
```

### Running Tests

```bash
# Run full test suite (2,500+ tests)
pytest tests/ -v

# Quick run (stop on first failure)
pytest tests/ -x -q

# Run specific module tests
pytest tests/test_consciousness.py -v
pytest tests/test_knowledge_graph.py -v
pytest tests/test_graph_intelligence.py -v

# Or use Make
make test
make test-quick
```

### Code Style

This project uses [black](https://github.com/psf/black) for formatting and [mypy](https://mypy.readthedocs.io/) for type checking.

```bash
# Format code
make format          # black src/ tests/

# Check formatting + types
make lint            # black --check + mypy
```

Style requirements:
- **Line length**: 100 characters
- **Type hints**: required for all public functions
- **Docstrings**: Google style, required for all public classes and methods
- **Target**: Python 3.11+

### Project Structure

```
src/asi_build/         # Source package — this is what gets installed
tests/                 # Pytest tests — one file per module
examples/              # Runnable demo scripts
docs/                  # Documentation + research notes
configs/               # YAML configuration templates
```

---

## Project History

ASI:BUILD began in **August 2025** as an ambitious attempt to implement a comprehensive AGI framework — 47 subsystems, 101 wiki pages, consciousness engines, quantum engines, reality engines. It was big, visionary, and much of it was scaffolding.

In **April 2026**, the project underwent a major restructure:
- All real, tested code moved to `src/asi_build/`
- Template-generated and untested scaffolding moved to `archive/`
- A proper test suite added (now 2,500+ tests)
- Modern Python packaging (`pyproject.toml`)
- Import paths standardized
- Public release on [GitHub](https://github.com/web3guru888/asi-build) (MIT license)

The goal of the restructure was honesty: clearly separate what works from what's aspirational, and provide a solid foundation for research contributions.

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

## Links

- **GitHub**: [https://github.com/web3guru888/asi-build](https://github.com/web3guru888/asi-build) (public, primary)
- **GitLab**: [https://gitlab.com/asi-build/asi-build](https://gitlab.com/asi-build/asi-build) (mirror)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

Quick summary:
- Fork → branch → PR
- Every module must have tests
- Type hints + docstrings required
- `black` formatting enforced

---

## Acknowledgments

- **[Dr. Ben Goertzel](https://goertzel.org/)** — whose work on cognitive synergy, OpenCog, and the theory of general intelligence is a foundational inspiration for this project
- **[MemPalace-AGI](https://github.com/milla-jovovich/mempalace)** — contributed the `knowledge_graph` module (bi-temporal KG, A\* pathfinding, pheromone learning) as part of an integration project exploring spatial memory architectures for autonomous scientific discovery
- **[FastToG](https://arxiv.org/abs/2501.14300)** — the KG reasoning pipeline implemented in `graph_intelligence`
- All contributors who have submitted issues, PRs, and research feedback

---

## License

MIT License — see [LICENSE](LICENSE) for details.

This project is research software. It is provided as-is, without warranty. Use it to learn, experiment, and build — but evaluate critically and test thoroughly before depending on any module in production.
