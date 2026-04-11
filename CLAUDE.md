# CLAUDE.md — ASI:BUILD Codebase Guide for AI Assistants

This file provides orientation for AI coding assistants (Claude, Copilot, Cursor, etc.) working on the ASI:BUILD codebase.

---

## Project Overview

**ASI:BUILD** is a Python research framework exploring AI consciousness, cognitive architectures, knowledge graphs, and multi-agent reasoning. It is **research software** — not a production system.

- **Python**: 3.11+, src layout
- **Package**: `src/asi_build/` (installable as `asi-build`)
- **Tests**: `tests/` (pytest, 250+ tests)
- **Config**: `configs/default.yaml` → copy to `config.yaml`
- **License**: MIT

---

## Repository Structure

```
asi-build/
├── src/
│   └── asi_build/          ← THE REAL CODE — this is what matters
│       ├── consciousness/   ← GWT, IIT, AST, metacognition (🟢 tested)
│       ├── cognitive_synergy/ ← Synergy metrics, engines (🟢 tested)
│       ├── graph_intelligence/ ← FastToG, Memgraph (🟢 tested)
│       ├── homomorphic/     ← FHE: BGV/BFV/CKKS (🟢 tested)
│       ├── knowledge_graph/ ← Bi-temporal KG, A* (🟢 tested)
│       ├── safety/          ← Constitutional AI, constraints (🟢 tested)
│       ├── integrations/    ← LangChain, MCP agents (🟢 tested)
│       ├── bci/             ← Brain-computer interface (🟢 tested)
│       ├── vectordb/        ← Unified VDB client (🟡 structural)
│       ├── optimization/    ← PyTorch optimization (🟡 structural)
│       ├── quantum/         ← Qiskit hybrid (🟡 structural)
│       ├── reasoning/       ← Symbolic-neural (🟡 structural)
│       ├── compute/         ← Job scheduling (🟡 structural)
│       ├── bio_inspired/    ← Evo + swarm (🟡 structural)
│       ├── deployment/      ← CUDO + HF (🟡 structural)
│       ├── memgraph_toolbox/ ← Memgraph tools (🟡 structural)
│       ├── blockchain/      ← Blockchain integration (🟡 structural)
│       ├── distributed_training/ ← Distributed ML training (🟡 structural)
│       ├── holographic/     ← Holographic memory (🟡 structural)
│       ├── neuromorphic/    ← Neuromorphic computing (🟡 structural)
│       ├── pln_accelerator/ ← PLN acceleration (🟡 structural)
│       ├── knowledge_management/ ← Knowledge mgmt (🟡 structural)
│       ├── federated/       ← Federated learning (🟡 structural)
│       ├── agi_economics/   ← AGI economics models (🟡 structural)
│       ├── agi_reproducibility/ ← AGI reproducibility (🟡 structural)
│       ├── agi_communication/ ← AGI communication (🟡 structural)
│       └── servers/         ← Server infrastructure (🟡 structural)
├── tests/                  ← pytest tests, one file per module
├── examples/               ← Runnable demo scripts
├── docs/                   ← Documentation + research notes
├── configs/
│   └── default.yaml        ← Configuration template (annotated)
├── asi-code/               ← TypeScript AI coding IDE (SEPARATE product)
├── archive/                ← v1 experimental code (READ-ONLY, don't edit)
├── pyproject.toml
├── Makefile
├── README.md
├── CONTRIBUTING.md
└── CHANGELOG.md
```

---

## Module Status Guide

When working on a module, check its status first:

- 🟢 **Implemented** (`consciousness`, `cognitive_synergy`, `graph_intelligence`, `homomorphic`, `knowledge_graph`, `safety`, `integrations`, `bci`) — These have real implementations and tests. Treat carefully; bugs here affect real functionality.
- 🟡 **Structural** (`vectordb`, `optimization`, `quantum`, `reasoning`, `compute`, `bio_inspired`, `deployment`, `memgraph_toolbox`, `blockchain`, `distributed_training`, `holographic`, `neuromorphic`, `pln_accelerator`, `knowledge_management`, `federated`, `agi_economics`, `agi_reproducibility`, `agi_communication`, `servers`) — Framework is defined but backends may be stubs or incomplete. Safe to extend, but verify what's actually wired up.

The `archive/` directory is v1 scaffolding — ~77% of it (150K of 194K LOC) is template-generated scaffolding. Only `agi_reproducibility` has been identified as potentially promote-worthy to `src/`. **Do not edit files there.** Do not use them as references for "how things work."

---

## Common Tasks

### Adding a Feature to an Existing Module

1. Read the module's `__init__.py` to understand its public API
2. Check `tests/test_<module>.py` to understand expected behavior
3. Implement in the relevant file under `src/asi_build/<module>/`
4. Add tests in `tests/test_<module>.py`
5. Update the module's `__init__.py` exports if adding new public symbols

### Running Tests

```bash
pytest tests/ -v                    # All tests
pytest tests/test_consciousness.py  # Single module
pytest tests/ -k "phi"              # Filter by name
make test-cov                       # With coverage report
```

### Checking Imports Work

```bash
pip install -e ".[dev]"
python -c "from asi_build.consciousness import GlobalWorkspaceTheory; print('ok')"
python -c "from asi_build.knowledge_graph import TemporalKnowledgeGraph; print('ok')"
python -c "from asi_build.cognitive_synergy import SynergyMetrics; print('ok')"
```

### Formatting

```bash
black src/ tests/          # Format
black --check src/ tests/  # Check (CI mode)
```

---

## Key Design Patterns

### Module `__init__.py` exports everything public

Each module uses an explicit `__all__` in its `__init__.py`. When adding new public symbols, add them there. When searching for what a module exposes, start there.

### Configuration via YAML + environment variables

Modules read configuration from `config.yaml` (user's local copy of `configs/default.yaml`). All secrets (API keys, passwords) must come from environment variables, never config files. The pattern:

```python
import os
api_key = os.environ.get("ASI_BUILD_VECTORDB_PINECONE_API_KEY", "")
```

### Bi-temporal knowledge graph

The `knowledge_graph` module tracks two time dimensions:
- **Valid time**: when the fact was true in the real world
- **Transaction time**: when the fact was recorded in the system

Both dimensions are indexed. This is important for scientific applications where facts can be retroactively corrected or have bounded validity.

### Consciousness theories are interchangeable

The `consciousness` module uses a theory-neutral interface. If you're implementing a new theory, it must implement the same interface as `GlobalWorkspaceTheory`. See `consciousness/base.py` for the abstract base class.

### Init-order pattern in consciousness modules

The consciousness base class calls `_initialize()` from its `__init__()`. This means **subclass attributes must be set before calling `super().__init__()`**, because the base class will invoke `_initialize()` which may depend on those attributes. Pattern:

```python
class MyTheory(ConsciousnessBase):
    def __init__(self, config):
        self.my_attr = config.some_value  # Set BEFORE super().__init__()
        super().__init__(config)          # This calls _initialize()

    def _initialize(self):
        # self.my_attr is safe to use here
        ...
```

---

## Things to Watch Out For

### Security

- **Never hardcode API keys or credentials** — check all modified files with `grep -r "sk-" .` before committing
- **Parameterize all Cypher queries** — raw string formatting into Cypher queries is a known injection vector (was fixed in 2.0.0, don't reintroduce)
- The `safety` module is not a security system — it's a research module exploring AI alignment concepts

### Consciousness base class init order

The consciousness base class calls `_initialize()` from `__init__()` — subclass attributes **MUST** be set before `super().__init__()`. Failing to do this causes `AttributeError` during initialization. See the init-order pattern above.

### The `homomorphic` module has known correctness issues

The polynomial ring arithmetic in the `homomorphic` module has known correctness issues. **Do not trust crypto outputs without independent verification.** The BGV/BFV/CKKS implementations are research-grade and not suitable for real cryptographic operations.

### The `cognitive_synergy/__init__.py` uses explicit imports

The `cognitive_synergy/__init__.py` uses explicit imports from subpackages. When adding new public symbols to the module, you must add corresponding import lines there — they won't be auto-discovered.

### `MetacognitiveStrategyInstance` vs `MetacognitiveStrategy`

In `consciousness/metacognition.py`, `MetacognitiveStrategy` is an **Enum** (strategy types), and `MetacognitiveStrategyInstance` is the **dataclass** (an actual strategy instance with parameters). Don't confuse them.

### The `archive/` directory

Do not treat `archive/` as a source of truth. ~77% of its content (150K of 194K LOC) is template-generated scaffolding. Files there were generated in 2025 and many contain:
- Stub implementations (all `pass` or `raise NotImplementedError`)
- Template-generated docstrings that don't match actual behavior
- Import paths that no longer exist

Only `agi_reproducibility` has been identified as having real, promote-worthy content. If you need reference implementations, look in `src/asi_build/`.

### `asi-code/` is a different product

The `asi-code/` directory contains a TypeScript AI coding IDE. It has its own `package.json`, build system, and tests. It shares the repo but is not a Python package. Don't mix it up with the Python `src/asi_build/` code.

### Module maturity varies dramatically

`homomorphic` has a complete polynomial ring implementation with BGV/BFV/CKKS. `bci` has ~8K LOC across 12 subpackages. `deployment` is mostly structural. Don't assume all modules are at the same level — always check.

---

## Dependencies

Install with optional groups depending on what you're working on:

```bash
pip install -e ".[dev]"             # Core + dev tools (pytest, black, mypy)
pip install -e ".[consciousness]"   # + scipy, scikit-learn
pip install -e ".[graph]"           # + networkx, neo4j
pip install -e ".[quantum]"         # + qiskit
pip install -e ".[ml]"              # + torch, transformers
pip install -e ".[all]"             # Everything
```

---

## Research Context

ASI:BUILD is inspired by **Ben Goertzel's cognitive synergy** framework for AGI — the hypothesis that general intelligence emerges from the cooperative interaction of diverse, specialized cognitive modules. The key insight: modules should help each other, not just run in parallel.

Key papers relevant to understanding the codebase:
- Baars (1988) — Global Workspace Theory (consciousness module)
- Tononi (2004, 2014) — Integrated Information Theory / Φ (consciousness module)
- Schroeder (2019) — Attention Schema Theory (consciousness module)
- FastToG (arXiv:2501.14300) — Knowledge graph reasoning pipeline (graph_intelligence module)
- MemPalace-AGI integration — Spatial memory architecture for autonomous discovery (knowledge_graph module)

---

## Getting Help

- Module-level questions: check `docs/` for research notes
- Architecture questions: see `README.md` and the architecture diagram
- Historical context: see `CHANGELOG.md` and `archive/`
- Contributing: see `CONTRIBUTING.md`
