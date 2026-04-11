# Changelog

All notable changes to ASI:BUILD are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [2.0.0] - 2026-04-11

### Changed

- **BREAKING**: Complete repository restructure
  - All real, tested code moved to `src/asi_build/`
  - All scaffolding and experimental code moved to `archive/`
  - Import paths changed:
    - `from consciousness_engine import X` → `from asi_build.consciousness import X`
    - `from cognitive_synergy import X` → `from asi_build.cognitive_synergy import X`
    - `from graph_intelligence import X` → `from asi_build.graph_intelligence import X`
    - `from homomorphic_engine import X` → `from asi_build.homomorphic import X`
  - Duplicate directories consolidated (e.g., `consciousness/` and `consciousness_engine/` merged)
- `pyproject.toml` updated to modern packaging (Hatchling build backend)
- All modules now installable as `asi-build` with optional dependency groups

### Added

- **`knowledge_graph` module** — Bi-temporal knowledge graph with provenance tracking, A\* pathfinding, and pheromone-based learning (contributed by the MemPalace-AGI integration project)
- **Test suite** — 125+ tests covering `consciousness`, `graph_intelligence`, `cognitive_synergy`, `homomorphic`, and `knowledge_graph` modules
- **`pyproject.toml`** — Modern Python packaging with Hatchling, optional dependency groups per module
- **`Makefile`** — Standard development targets: `install`, `test`, `lint`, `format`, `clean`
- **`configs/default.yaml`** — Documented configuration template for all modules
- **`CONTRIBUTING.md`** — Contributor guide with module development instructions
- **`CHANGELOG.md`** — This file
- **`.gitignore`** — Proper Python + project-specific ignores

### Fixed

- **9 uninstantiable consciousness classes** — Missing `_initialize()` implementations causing `TypeError` on construction
- **Cypher injection** in `graph_intelligence` — Raw string formatting replaced with parameterized queries
- **Removed hardcoded API keys and credentials** from source files and configuration examples
- **Import errors** in several modules caused by circular imports after directory consolidation

### Removed

- **25MB scraped website** from `branding/` — External content should not be committed
- **Duplicate directories** — `consciousness_engine/` (→ `consciousness/`), `synergy/` (→ `cognitive_synergy/`), `graph_engine/` (→ `graph_intelligence/`)
- **Internal correspondence** — Development emails and one-time migration scripts
- **One-time scripts** — `fix.py`, `migrate_v1.py`, `reorg.sh` and similar

---

## [1.0.0] - 2025-08-25

### Added

- Initial ASI:BUILD framework with 47 subsystems
- Consciousness engine (Global Workspace Theory, Integrated Information Theory, Attention Schema Theory)
- Quantum engine (Qiskit integration, quantum-classical hybrid circuits)
- Reality engine (experimental world-model integration)
- Wave evolution system (6 waves of cognitive development)
- Documentation suite (45+ documents)
- 101 wiki pages
- ASI-Code TypeScript AI coding IDE (`asi-code/`)
- Original module set: `consciousness_engine`, `synergy`, `graph_engine`, `homomorphic_engine`, `quantum_engine`, `reasoning_engine`, `safety_layer`, `compute_manager`, `bio_optimizer`, `deployment_engine`

---

*For pre-1.0.0 development history, see `archive/HISTORY.md` if present.*
