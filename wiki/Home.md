# ASI:BUILD Wiki

**A modular Python research framework for exploring AI consciousness, cognitive architectures, knowledge graphs, and multi-agent reasoning.**

[![CI](https://github.com/web3guru888/asi-build/actions/workflows/ci.yml/badge.svg)](https://github.com/web3guru888/asi-build/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-research--alpha-orange)

> ⚠️ **Research Alpha** — ASI:BUILD is active research software. Module maturity varies: some are well-implemented and tested, others are structural scaffolding. See the [[Module Index]] for per-module status.

---

## Current Status

| Metric | Value |
|--------|-------|
| Modules | 29 (across `src/asi_build/`) |
| Source lines | ~186,500 |
| Tests | 2,777 passing, 42 skipped, 0 failures |
| CI | Python 3.10, 3.11, 3.12 |
| License | MIT |
| Release | [v0.1.0-alpha](https://github.com/web3guru888/asi-build/releases/tag/v0.1.0-alpha) |
| Blackboard adapters | **8 wired** — see [[Blackboard Integration Status]] |
| Community | **57 discussions** · **46 wiki pages** · **39 open issues** |
| Contributors | 1 external PR received ([PR #85](https://github.com/web3guru888/asi-build/pull/85) — @xyf25) |

**Phases:**
- ✅ Phase 1 — Foundation (modules, tests, CI, packaging)
- ✅ Phase 2 — Cross-Module Integration (Cognitive Blackboard + 8 adapters as of `3b3916e`)
- ✅ Phase 3 — Science Correctness (IIT Φ fixed, homomorphic NTT fixed, safety auto-prove fixed — all 3 bugs resolved)
- 🔬 Phase 4 — Emergent Cognition (planning — see [[Roadmap]])

---

## Navigation

| Page | Description |
|------|-------------|
| [[Getting Started]] | Installation, first steps, first code example |
| [[Architecture]] | Layered design, Cognitive Blackboard, data flow |
| [[Module Index]] | All 29 modules: status, LOC, description |
| [[Cognitive Blackboard]] | Integration layer API: CognitiveBlackboard, EventBus, adapters |
| [[Blackboard Integration Status]] | Which modules are wired to the Blackboard and what they publish |
| [[Roadmap]] | Phase-by-phase plan with current status |
| [[Contributing]] | How to contribute: fork, test, PR, code style |

---

## Quick Start

```bash
git clone https://github.com/web3guru888/asi-build.git
cd asi-build
pip install -e ".[dev]"
pytest tests/ -q
```

```python
from asi_build.consciousness import GlobalWorkspaceTheory
from asi_build.knowledge_graph import TemporalKnowledgeGraph
from asi_build.cognitive_synergy import CognitiveSynergyEngine

# Create a knowledge graph
kg = TemporalKnowledgeGraph()
kg.add_entity("concept_A", {"type": "idea"})

# Measure consciousness broadcast
gwt = GlobalWorkspaceTheory()
broadcast = gwt.broadcast({"stimulus": "test input"})
print(f"Broadcast coalition size: {broadcast['coalition_size']}")
```

---

## Community

| Resource | Link |
|----------|------|
| 💬 Discussions (57) | [github.com/…/discussions](https://github.com/web3guru888/asi-build/discussions) |
| 🐛 Issues (39 open) | [github.com/…/issues](https://github.com/web3guru888/asi-build/issues) |
| 🌱 Good First Issues | [Contributor Entry Points](https://github.com/web3guru888/asi-build/labels/good%20first%20issue) |
| 📦 Releases | [v0.1.0-alpha](https://github.com/web3guru888/asi-build/releases/tag/v0.1.0-alpha) |
| 🔭 External PRs | [PR #85](https://github.com/web3guru888/asi-build/pull/85) — first external contributor! |

## Links

- **Repo**: [github.com/web3guru888/asi-build](https://github.com/web3guru888/asi-build)
- **Issues**: [Open Issues](https://github.com/web3guru888/asi-build/issues)
- **Discussions**: [Community Discussions](https://github.com/web3guru888/asi-build/discussions)
- **Good First Issues**: [Contributor Entry Points](https://github.com/web3guru888/asi-build/labels/good%20first%20issue)
- **Releases**: [v0.1.0-alpha](https://github.com/web3guru888/asi-build/releases/tag/v0.1.0-alpha)
