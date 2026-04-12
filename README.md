# ASI:BUILD

**A modular Python research framework for exploring AI consciousness, cognitive architectures, knowledge graphs, and multi-agent reasoning.**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
[![CI](https://github.com/web3guru888/asi-build/actions/workflows/ci.yml/badge.svg)](https://github.com/web3guru888/asi-build/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/tests-3%2C018%20passing-brightgreen)
![Status](https://img.shields.io/badge/status-research--alpha-orange)
[![Discussions](https://img.shields.io/badge/discussions-join%20us-blueviolet)](https://github.com/web3guru888/asi-build/discussions)
[![Issues](https://img.shields.io/github/issues/web3guru888/asi-build)](https://github.com/web3guru888/asi-build/issues)
[![Wiki](https://img.shields.io/badge/wiki-50%20pages-blue)](https://github.com/web3guru888/asi-build/wiki)

> ⚠️ **Research Software**: ASI:BUILD is an active research framework, not a production system. Module maturity varies — see the [Module Maturity](#module-maturity) section and the per-module `__maturity__` metadata for details.

---

## Overview

ASI:BUILD is a Python research framework exploring the computational foundations of artificial general intelligence. Inspired by the cognitive synergy approach to AGI — the idea that intelligence emerges from the interaction of diverse cognitive subsystems — the project provides modular, composable implementations of key AGI building blocks.

The framework spans consciousness modeling (Global Workspace Theory, Integrated Information Theory, Attention Schema Theory), information-theoretic synergy metrics, bi-temporal knowledge graphs, homomorphic encryption, quantum-classical hybrid computing, brain-computer interfaces, federated learning, and more. Each module can be used independently or composed with others via the **Cognitive Blackboard** — a shared workspace and event bus that lets all 29 modules communicate and exhibit emergent cross-module behaviors.

ASI:BUILD prioritizes correctness and clarity over performance. Published benchmarks and experimental results live in `docs/research/`. If you want to experiment with the building blocks of AGI, you're in the right place.

**We welcome contributors from all backgrounds** — neuroscience, ML, distributed systems, formal verification, or just curiosity about AGI. There are open issues for every skill level, from bite-sized documentation tasks to deep open research problems.

---

## Current Status

| Metric | Value |
|--------|-------|
| **Source files** | 547 files across 29 modules |
| **Lines of code** | ~192,000 LOC |
| **Tests** | **3,018 passing · 0 failing · 42 skipped** |
| **Test files** | 36 |
| **Integration adapters** | 24 Blackboard adapters + `AsyncAdapterBase` |
| **Module maturity** | 1 stable · 7 beta · 12 alpha · 5 experimental |
| **Discussions** | 66 threads |
| **Wiki pages** | 50 |
| **Open issues** | 31 (many labeled `good first issue`) |
| **License** | MIT |

---

## 🤝 Get Involved

ASI:BUILD is built in the open and grows through community contributions. Here's how to participate:

### 💬 Discussions
Join the conversation at **[github.com/web3guru888/asi-build/discussions](https://github.com/web3guru888/asi-build/discussions)**

Key threads to start with:
- 👋 **[Welcome & Introductions](https://github.com/web3guru888/asi-build/discussions/9)** — Say hello and tell us what you're building
- 🔬 **[Research Directions](https://github.com/web3guru888/asi-build/discussions/5)** — Open research questions and where the project goes next
- 🏗️ **[Why a Cognitive Blackboard?](https://github.com/web3guru888/asi-build/discussions/10)** — Architecture decision deep-dive
- 🗺️ **[Phase 4 Roadmap](https://github.com/web3guru888/asi-build/discussions/12)** — Help shape the future roadmap
- ❓ **[FAQ](https://github.com/web3guru888/asi-build/discussions/16)** — Getting started, architecture questions, module usage
- 🔗 **[16 Modules Now Wired — Show & Tell](https://github.com/web3guru888/asi-build/discussions/115)** — Latest integration milestone

### 📖 Wiki
Comprehensive documentation at **[github.com/web3guru888/asi-build/wiki](https://github.com/web3guru888/asi-build/wiki)** — 50 pages covering:

- **Getting Started** — Installation, environment setup, first steps
- **Architecture Guide** — Cognitive Blackboard, layered design, module interaction patterns
- **Module Index** — Per-module guides and API references
- **Cognitive Blackboard** — Integration layer docs: EventBus, adapters, lifecycle
- **Module Maturity Model** — What stable / beta / alpha / experimental mean
- **Roadmap** — Current phase status and upcoming milestones

### 🐛 Issues & Good First Issues
Browse open issues at **[github.com/web3guru888/asi-build/issues](https://github.com/web3guru888/asi-build/issues)**

Looking for a place to start? Check the **[`good first issue`](https://github.com/web3guru888/asi-build/labels/good%20first%20issue)** label — carefully scoped tasks for new contributors:
- Writing unit tests for existing modules
- Adding type hints and docstrings
- Creating example scripts and Jupyter notebooks
- Improving module documentation

There are issues for all skill levels — all the way up to deep research problems tagged [`research`](https://github.com/web3guru888/asi-build/labels/research).

---

## Architecture

```
asi-build/
├── src/
│   └── asi_build/                  # Main Python package (547 files, ~192K LOC)
│       ├── consciousness/          # Multi-theory consciousness modeling
│       ├── cognitive_synergy/      # Information-theoretic synergy metrics
│       ├── graph_intelligence/     # KG reasoning + FastToG pipeline
│       ├── homomorphic/            # Fully Homomorphic Encryption (BGV/BFV/CKKS)
│       ├── knowledge_graph/        # Bi-temporal KG with provenance + A*
│       ├── reasoning/              # Hybrid symbolic-neural reasoning engine
│       ├── safety/                 # Constitutional AI + governance
│       │   ├── formal_verification.py  # SymPy + Z3 theorem proving
│       │   └── governance/         # DAO, consensus, smart contracts,
│       │                           #   Merkle audit, entity rights
│       ├── integration/            # Cognitive Blackboard + 24 module adapters
│       │   ├── blackboard.py       # Shared workspace + entry lifecycle
│       │   ├── events.py           # EventBus + topic routing
│       │   ├── protocols.py        # Typed communication protocols
│       │   ├── cognitive_cycle.py  # 9-phase perception-to-action loop
│       │   └── adapters/           # Per-module Blackboard adapters (24 + base)
│       ├── integrations/           # External tool adapters
│       │   ├── langchain-memgraph/ # LangChain ↔ Memgraph adapter
│       │   ├── mcp-memgraph/       # MCP server for Memgraph
│       │   └── agents/             # SQL→graph migration agent + HyGM
│       ├── rings/                  # Rings Network P2P SDK (DID, reputation, DHT)
│       ├── bci/                    # Brain-Computer Interface (EEG, CSP, P300, SSVEP)
│       ├── quantum/                # Quantum-classical hybrid (Qiskit)
│       ├── vectordb/               # Unified vector DB client (Pinecone, Qdrant, Weaviate)
│       ├── federated/              # Federated learning + differential privacy
│       ├── distributed_training/   # 1000-node federated orchestration
│       ├── neuromorphic/           # Spiking neural networks
│       ├── pln_accelerator/        # Hardware-accelerated PLN
│       ├── holographic/            # Volumetric display + spatial audio
│       ├── blockchain/             # Audit trails, IPFS, EVM
│       ├── compute/                # Job scheduling + GPU allocation
│       ├── bio_inspired/           # STDP, circadian rhythms, swarm intelligence
│       ├── agi_economics/          # Reputation scoring, value alignment, DeFi
│       ├── agi_reproducibility/    # Experiment tracking, AGSSL, formal provers
│       ├── agi_communication/      # Game-theoretic negotiation, trust layers
│       ├── knowledge_management/   # Omniscience network, predictive synthesis
│       ├── optimization/           # PyTorch quantization, pruning, distillation
│       ├── deployment/             # FastAPI servers, MCP SSE, CUDO + HuggingFace
│       ├── memgraph_toolbox/       # Memgraph graph DB tools
│       └── servers/                # MCP + SSE graph servers (Kenny Graph)
├── tests/                          # Test suite (3,018 passing, 36 test files)
├── examples/                       # Runnable examples
├── docs/                           # Documentation + research notes
├── configs/                        # Configuration templates
├── asi-code/                       # TypeScript AI coding IDE (separate product)
└── archive/                        # Experimental v1 modules (not tested)
```

### Cognitive Blackboard Architecture

The `integration/` layer is the connective tissue of ASI:BUILD — it wires all 29 modules together through a shared workspace and event bus:

```
  ┌────────────────────────────────────────────────────────────┐
  │                      Module Layer (29 modules)             │
  │  consciousness · bci · knowledge_graph · reasoning · ...   │
  └──────────────┬─────────────────────────────────────────────┘
                 │  adapters (each module gets a typed adapter)
  ┌──────────────▼─────────────────────────────────────────────┐
  │               Cognitive Blackboard (integration/)          │
  │                                                            │
  │   ┌──────────────────────┐  ┌───────────────────────────┐  │
  │   │   Shared Workspace   │  │        EventBus           │  │
  │   │  (typed BB entries)  │  │  (pub/sub topic routing)  │  │
  │   └──────────────────────┘  └───────────────────────────┘  │
  │                                                            │
  │   ┌──────────────────────────────────────────────────────┐ │
  │   │   CognitiveCycle — 9-phase perception-to-action loop │ │
  │   │   sense → perceive → context → reason → decide →     │ │
  │   │   act → learn → consolidate → evaluate               │ │
  │   └──────────────────────────────────────────────────────┘ │
  └────────────────────────────────────────────────────────────┘
```

**24 Blackboard adapters** are implemented — one per module — each bridging its module's domain events (e.g., `ConsciousnessState`, `BCIEvent`, `KnowledgeGraphEntry`) into the shared workspace as typed `BlackboardEntry` objects. An `AsyncAdapterBase` provides a dual sync+async protocol for latency-sensitive modules.

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

> 📖 **New here?** Check out the **[Getting Started guide on the Wiki](https://github.com/web3guru888/asi-build/wiki/Getting-Started)** for a more detailed walkthrough including environment setup, module selection, and first experiments.

### Hello, Consciousness

```python
from asi_build.consciousness import GlobalWorkspaceTheory

# Initialize a Global Workspace with 8 cognitive processors
gwt = GlobalWorkspaceTheory()
print(f"Processors: {len(gwt.cognitive_processors)}")

# Each processor monitors specific content types
for pid, proc in list(gwt.cognitive_processors.items())[:3]:
    print(f"  {pid}: interests={proc.interests}")

# Broadcast a percept into the global workspace
result = gwt.broadcast({"type": "visual", "content": "motion detected"})
print(f"Broadcast reached {result.n_reached} processors")
```

### Knowledge Graph with A* Pathfinding

```python
from asi_build.knowledge_graph import TemporalKnowledgeGraph, KGPathfinder

kg = TemporalKnowledgeGraph(db_path=":memory:")

# Add bi-temporal facts with provenance tracking
kg.add_triple("ASTR-J1234", "hasProperty", "high_redshift",
              confidence=0.92, source="HST-observation-42")
kg.add_triple("high_redshift", "indicates", "dark_energy_candidate",
              confidence=0.85, source="cosmology-model-7")

# Find paths using A* with pheromone-based learning
pathfinder = KGPathfinder(kg)
path = pathfinder.find_path("ASTR-J1234", "dark_energy_candidate")
print(f"Path found: {path['complete']}")         # True
print(f"Hops: {path['hops']}, Cost: {path['cost']:.3f}")
```

### IIT Φ Computation (Fixed)

```python
from asi_build.consciousness.iit import IntegratedInformationTheory

iit = IntegratedInformationTheory()
iit.update_activation_history([0.8, 0.6, 0.9, 0.4])  # feed activations

phi = iit.compute_phi(mechanism=[0, 1, 2, 3], purview=[0, 1, 2, 3])
print(f"IIT Φ = {phi:.4f}")   # > 0 for a recurrent integrated network
```

### Cognitive Blackboard — Cross-Module Event Flow

```python
from asi_build.integration import CognitiveBlackboard
from asi_build.integration.adapters import ConsciousnessBlackboardAdapter

bb = CognitiveBlackboard()
adapter = ConsciousnessBlackboardAdapter(bb)

# Subscribe to consciousness state updates
@bb.subscribe("consciousness.state_updated")
def on_state(entry):
    print(f"Consciousness state: {entry.data}")

# Other modules can now react to every consciousness update
adapter.publish_state(gwt_result)
```

### Rings Network P2P SDK

```python
from asi_build.rings import RingsClient, DIDManager, ReputationScorer

# Connect to the Rings P2P network with DID authentication
did = DIDManager().create_did()
client = RingsClient(did=did)
await client.connect()

# Score agent reputation based on observed behavior
scorer = ReputationScorer()
score = scorer.compute(agent_id="did:rings:abc123", observations=[...])
print(f"Reputation score: {score:.3f}")
```

---

## Modules

All 29 modules carry a `__maturity__` attribute — see [Module Maturity Model](https://github.com/web3guru888/asi-build/wiki/Module-Maturity-Model).

| Module | Maturity | LOC | Description |
|--------|----------|-----|-------------|
| `consciousness` | 🟢 **beta** | ~12,200 | GWT, IIT 3.0 Φ (TPM-based), AST, metacognition — 15 submodules |
| `cognitive_synergy` | 🟢 **beta** | ~6,000 | Mutual info, transfer entropy, phase locking, LZ76 complexity |
| `homomorphic` | 🟢 **beta** | ~12,349 | BGV/BFV/CKKS FHE with NTT fixed, polynomial ring arithmetic |
| `graph_intelligence` | 🟢 **beta** | ~8,200 | FastToG (arXiv:2501.14300), Memgraph, community detection |
| `integration` | 🟢 **stable** | ~10,907 | Cognitive Blackboard + EventBus + 24 adapters + CognitiveCycle |
| `bci` | 🟢 **beta** | ~8,000 | EEG pipelines, CSP motor imagery, P300, SSVEP, thought-to-text |
| `safety` | 🟢 **beta** | ~6,200 | SymPy/Z3 theorem proving, governance DAO, Merkle audit, entity rights |
| `knowledge_graph` | 🟢 **beta** | ~1,450 | Bi-temporal KG, provenance, A*, pheromone learning |
| `integrations` | 🟢 **beta** | ~7,300 | LangChain-Memgraph, MCP server, SQL→graph agent, HyGM |
| `pln_accelerator` | 🟡 **alpha** | ~12,500 | Hardware-accelerated PLN with NL↔logic bridge |
| `compute` | 🟡 **alpha** | ~11,500 | Job scheduling, resource management, GPU allocation |
| `agi_economics` | 🟡 **alpha** | ~7,200 | Reputation scoring, value alignment, decentralized incentives |
| `agi_reproducibility` | 🟡 **alpha** | ~7,500 | AGSSL, experiment tracking, formal provers |
| `distributed_training` | 🟡 **alpha** | ~8,200 | 1000-node federated, Byzantine tolerance, AGIX rewards |
| `federated` | 🟡 **alpha** | ~6,400 | Federated learning, differential privacy, secure aggregation |
| `vectordb` | 🟡 **alpha** | ~8,000 | Unified client for Pinecone, Qdrant, Weaviate |
| `quantum` | 🟡 **alpha** | ~5,330 | VQE, QAOA, QNN, quantum-classical hybrid via Qiskit |
| `knowledge_management` | 🟡 **alpha** | ~5,500 | Omniscience network, predictive synthesis, adaptive learning |
| `bio_inspired` | 🟡 **alpha** | ~4,350 | STDP, circadian rhythms, sleep-wake consolidation |
| `optimization` | 🟡 **alpha** | ~4,200 | PyTorch quantization, pruning, knowledge distillation |
| `neuromorphic` | 🟡 **alpha** | ~3,700 | Spiking neural networks, LIF simulation |
| `deployment` | 🟡 **alpha** | ~3,350 | FastAPI, MCP SSE, CUDO Compute, HuggingFace |
| `agi_communication` | 🟡 **alpha** | ~2,800 | Game-theoretic negotiation, trust layers, semantic interop |
| `rings` | 🟡 **alpha** | ~1,951 | P2P SDK: DID identity, reputation scoring, DHT — 196 tests |
| `servers` | 🟡 **alpha** | ~1,400 | MCP + SSE servers, Kenny Graph (89K nodes, 1.4K agents) |
| `memgraph_toolbox` | 🟡 **alpha** | ~930 | PageRank, betweenness centrality, Cypher helpers |
| `reasoning` | 🔵 **alpha** | ~880 | Hybrid symbolic-neural + causal inference (PC/FCI algorithms) |
| `holographic` | 🔴 **experimental** | ~8,000 | Volumetric display, spatial audio, mixed reality |
| `blockchain` | 🔴 **experimental** | ~5,950 | Merkle audit trails, IPFS, EVM event logging |

**Maturity legend:**
- 🟢 **stable / beta** — Core algorithms present, tested, and documented
- 🟡 **alpha** — Framework and interfaces defined; implementations vary; further development ongoing
- 🔴 **experimental** — In early development; APIs may change; use with caution

> The `archive/` directory contains aspirational v1 modules. These are preserved for reference but are not part of the main package and are not tested.
> The `examples/` directory includes MiniMind, a third-party small LLM reference (Apache 2.0).

---

## Module Maturity

Every module in `src/asi_build/` exposes a `__maturity__` attribute:

```python
from asi_build.consciousness import __maturity__
print(__maturity__)   # "beta"

from asi_build.holographic import __maturity__
print(__maturity__)   # "experimental"
```

The four levels follow a defined progression — see the **[Module Maturity Model wiki page](https://github.com/web3guru888/asi-build/wiki/Module-Maturity-Model)** for the full definition of each tier, promotion criteria, and which modules are currently seeking upgrade.

---

## Key Technical Highlights

- **Cognitive Blackboard** — Thread-safe shared workspace supporting ~20K writes/sec, <12µs read latency, <1ms subscriber lag. The backbone of cross-module communication.
- **EventBus** — Typed pub/sub with topic routing (`consciousness.state_updated`, `bci.epoch_ready`, `reasoning.inference_complete`, etc.)
- **24 Blackboard adapters** — Every module has a typed adapter; an `AsyncAdapterBase` enables async-native pipelines for latency-sensitive modules.
- **IIT 3.0 Φ (fixed)** — TPM-based computation, correct bipartition enumeration, validated against known network topologies.
- **Safety gating** — `EthicalVerificationEngine` uses SymPy + Z3 SMT for sound theorem proving; ungrounded-symbol checks prevent vacuous proofs.
- **LZ76 complexity** — Fixed and validated; suffix-array O(n log n) optimization tracked in [Issue #94](https://github.com/web3guru888/asi-build/issues/94).
- **Rings Network P2P** — DID-authenticated peer connections, reputation scoring, DHT — 196 passing tests.
- **9 real data sources** — 27,430+ data points used across test fixtures and benchmarks.
- **Causal inference** — PC and FCI algorithms implemented in the `reasoning` module.
- **OODA research cycle** — Observe-Orient-Decide-Act loop implemented in the `agi_reproducibility` module.

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
# Run the full test suite (3,018 passing)
pytest tests/ -v

# Quick run — stop on first failure
pytest tests/ -x -q

# Run specific module tests
pytest tests/test_consciousness.py -v
pytest tests/test_knowledge_graph.py -v
pytest tests/test_cognitive_synergy.py -v
pytest tests/test_integration.py -v

# Or use Make
make test
make test-quick
```

### Code Style

This project uses [black](https://github.com/psf/black) for formatting and [mypy](https://mypy.readthedocs.io/) for type checking.

```bash
make format     # black src/ tests/
make lint       # black --check + mypy
```

Style requirements:
- **Line length**: 100 characters
- **Type hints**: required for all public functions
- **Docstrings**: Google style, required for all public classes and methods
- **Python**: 3.11+

### Project Layout

```
src/asi_build/         # Source package (what gets installed)
tests/                 # Pytest tests — one file per module
examples/              # Runnable demo scripts
docs/                  # Documentation + research notes
configs/               # YAML configuration templates
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. We welcome contributions of all kinds — code, tests, documentation, research, bug reports, and discussion.

### Getting Started as a Contributor

1. **Find something to work on**
   - [`good first issue`](https://github.com/web3guru888/asi-build/labels/good%20first%20issue) — beginner-friendly, well-scoped tasks
   - [`help wanted`](https://github.com/web3guru888/asi-build/labels/help%20wanted) — things we need most right now
   - [`research`](https://github.com/web3guru888/asi-build/labels/research) — open research problems
   - [`documentation`](https://github.com/web3guru888/asi-build/labels/documentation) — doc improvements and examples

2. **Ask questions first**
   Join [Discussions](https://github.com/web3guru888/asi-build/discussions) before diving in. The [FAQ](https://github.com/web3guru888/asi-build/discussions/16) covers common questions; for architecture questions, start with the [Cognitive Blackboard discussion](https://github.com/web3guru888/asi-build/discussions/10).

3. **Read the docs**
   The [Wiki](https://github.com/web3guru888/asi-build/wiki) has architecture guides and per-module documentation. The [Module Maturity Model](https://github.com/web3guru888/asi-build/wiki/Module-Maturity-Model) page explains what "alpha" and "beta" mean for each module.

4. **Submit your PR**
   Fork → branch → PR. Please include tests and docstrings — CI will check formatting and type hints automatically.

### What We're Looking For

- **Tests for alpha-tier modules** — Many modules are structurally complete but have limited test coverage. Adding pytest coverage is a great first contribution. See [Issue #1](https://github.com/web3guru888/asi-build/issues/1) and [`needs-tests`](https://github.com/web3guru888/asi-build/labels/needs-tests) issues.
- **Blackboard adapter wiring** — Several modules still need their Blackboard adapters fleshed out. See issues tagged [`enhancement`](https://github.com/web3guru888/asi-build/labels/enhancement).
- **Documentation & examples** — Wiki pages, Jupyter notebooks ([Issue #32](https://github.com/web3guru888/asi-build/issues/32)), docstrings.
- **Module backends** — Several alpha modules have framework scaffolding but need real backends (VectorDB client integrations, Quantum circuit backends, etc.).
- **Research contributions** — Open problems in IIT Φ benchmarking ([Issue #34](https://github.com/web3guru888/asi-build/issues/34)), CognitiveCycle design ([Issue #41](https://github.com/web3guru888/asi-build/issues/41)), multimodal fusion ([Issue #108](https://github.com/web3guru888/asi-build/issues/108)).

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing. We're committed to a welcoming, respectful community.

---

## Project History

ASI:BUILD began in **August 2025** as an ambitious attempt to implement a comprehensive AGI framework — 47 subsystems, consciousness engines, quantum engines, governance modules. It was visionary, and much of it was scaffolding.

In **April 2026**, the project underwent a major restructure:
- All real, tested code moved to `src/asi_build/` with proper packaging
- Template-generated scaffolding moved to `archive/`
- A proper test suite built from the ground up — now **3,018 passing tests**
- The **Cognitive Blackboard** integration layer introduced, wiring all 29 modules together
- Module maturity (`__maturity__`) added to every module for transparency
- Public release on GitHub (MIT license)

The goal of the restructure was honesty: clearly separate what works from what's aspirational, and provide a solid foundation for research contributions.

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

## Links

- **GitHub**: [https://github.com/web3guru888/asi-build](https://github.com/web3guru888/asi-build)
- **Discussions**: [https://github.com/web3guru888/asi-build/discussions](https://github.com/web3guru888/asi-build/discussions) (66 threads)
- **Wiki**: [https://github.com/web3guru888/asi-build/wiki](https://github.com/web3guru888/asi-build/wiki) (50 pages)
- **Issues**: [https://github.com/web3guru888/asi-build/issues](https://github.com/web3guru888/asi-build/issues)
- **CI**: [GitHub Actions](https://github.com/web3guru888/asi-build/actions)

---

## Acknowledgments

- **[Dr. Ben Goertzel](https://goertzel.org/)** — whose work on cognitive synergy, OpenCog, and the theory of general intelligence is a foundational inspiration for this project
- **[FastToG](https://arxiv.org/abs/2501.14300)** — the KG reasoning pipeline implemented in `graph_intelligence`
- All contributors who have submitted issues, PRs, and research feedback

---

## License

MIT License — see [LICENSE](LICENSE) for details.

This project is research software. Provided as-is, without warranty. Evaluate critically and test thoroughly before depending on any module in production.
