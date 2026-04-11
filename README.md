# ASI:BUILD

**A modular Python research framework for exploring AI consciousness, cognitive architectures, knowledge graphs, and multi-agent reasoning.**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-160%2B-brightgreen)
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
│       ├── integrations/           # External tool adapters
│       │   ├── langchain-memgraph/ # LangChain ↔ Memgraph adapter
│       │   ├── mcp-memgraph/       # MCP server for Memgraph
│       │   └── agents/             # SQL→graph migration agent + HyGM
│       ├── compute/                # Job scheduling + GPU allocation
│       ├── bio_inspired/           # Evolutionary + swarm intelligence
│       ├── deployment/             # Cloud deployment (CUDO + HuggingFace)
│       └── memgraph_toolbox/       # Memgraph graph DB tools
├── tests/                          # Test suite (160+ tests)
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
git clone https://gitlab.com/asi-build/asi-build.git
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
from asi_build.consciousness import GlobalWorkspaceTheory, IntegratedInformationTheory

# Initialize a Global Workspace
gwt = GlobalWorkspaceTheory(workspace_capacity=7)
gwt.initialize()

# Broadcast information to the workspace
result = gwt.broadcast(content="novel sensory input", salience=0.85)
print(f"Access consciousness: {result.is_conscious}")  # True if salience > threshold

# Measure integrated information (Φ)
iit = IntegratedInformationTheory(phi_threshold=0.3)
phi = iit.compute_phi(network_state=[[1,0,1],[0,1,0],[1,1,0]])
print(f"Φ = {phi:.3f}")  # Higher Φ → more integrated information
```

### Knowledge Graph with A* Pathfinding

```python
from asi_build.knowledge_graph import BiTemporalKnowledgeGraph

kg = BiTemporalKnowledgeGraph(database="sqlite", path="data/kg.db")

# Add bi-temporal facts with provenance
kg.add_triple(
    subject="ASTR-J1234",
    predicate="hasProperty",
    object="high_redshift",
    valid_time=("2024-01-01", "2024-12-31"),
    transaction_time="now",
    confidence=0.92,
    source="HST-observation-42"
)

# Find paths between entities
path = kg.find_path("ASTR-J1234", "dark_energy_candidate", algorithm="astar")
print(f"Path length: {len(path.edges)}, cost: {path.cost:.2f}")
```

### Cognitive Synergy Metrics

```python
from asi_build.cognitive_synergy import SynergyAnalyzer

analyzer = SynergyAnalyzer()

# Measure information synergy between cognitive modules
synergy = analyzer.compute_synergy(
    sources=[consciousness_output, knowledge_graph_output],
    target=reasoning_output,
    metric="transfer_entropy"
)
print(f"Synergy Φ_SI = {synergy.value:.4f} bits")
```

---

## Modules

| Module | Status | Description | LOC |
|--------|--------|-------------|-----|
| `consciousness` | 🟢 Implemented | Multi-theory consciousness (GWT, IIT, AST, metacognition) — 15 submodules | ~3,200 |
| `cognitive_synergy` | 🟢 Implemented | Synergy metrics: mutual info, transfer entropy, phase locking, LZ complexity | ~1,100 |
| `graph_intelligence` | 🟢 Implemented | KG reasoning with FastToG (arXiv:2501.14300), Memgraph, community detection | ~1,800 |
| `homomorphic` | 🟢 Implemented | FHE: BGV, BFV, CKKS schemes with polynomial ring arithmetic | ~2,400 |
| `knowledge_graph` | 🟢 Implemented | Bi-temporal KG, provenance tracking, A\* pathfinding, pheromone learning | ~1,600 |
| `vectordb` | 🟡 Structural | Unified client for Pinecone, Qdrant, Weaviate (backends not fully wired) | ~800 |
| `optimization` | 🟡 Structural | PyTorch quantization, pruning, knowledge distillation | ~900 |
| `quantum` | 🟡 Structural | Quantum-classical hybrid via Qiskit (circuit templates implemented) | ~700 |
| `reasoning` | 🟡 Structural | Hybrid symbolic-neural reasoning engine (framework scaffolding) | ~1,100 |
| `safety` | 🟢 Implemented | Constitutional AI + governance: SymPy formal verification, DAO (quadratic voting, liquid democracy), smart contracts, Merkle audit ledger, entity rights | ~6,800 |
| `integrations` | 🟢 Implemented | LangChain-Memgraph adapter, MCP-Memgraph server, SQL→graph migration agent, HyGM graph modeling | ~6,300 |
| `compute` | 🟡 Structural | Job scheduling, resource management, GPU allocation | ~500 |
| `bio_inspired` | 🟡 Structural | Evolutionary optimization, swarm intelligence | ~700 |
| `deployment` | 🟡 Structural | CUDO Compute + HuggingFace Transformers deployment | ~600 |
| `memgraph_toolbox` | 🟡 Structural | Memgraph tools: PageRank, betweenness centrality, Cypher helpers | ~400 |

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
# Run full test suite
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
- A proper test suite added (125+ tests)
- Modern Python packaging (`pyproject.toml`)
- Import paths standardized

The goal of the restructure was honesty: clearly separate what works from what's aspirational, and provide a solid foundation for research contributions.

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

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
