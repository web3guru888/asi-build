# ASI:BUILD Roadmap

> **Status**: v0.1.0-alpha — Research prototype. See module table in README for per-module maturity.

This document describes the planned development trajectory for ASI:BUILD. It is a research project, so timelines are approximate and priorities can shift based on experimental findings.

---

## Guiding Principles

1. **Cognitive synergy first** — the value of ASI:BUILD is in how modules interact, not in each module in isolation
2. **Correctness before performance** — we validate against published benchmarks before optimizing
3. **Honest labeling** — scaffolding is marked as scaffolding; only tested code reaches `main`
4. **Incremental integration** — each integration milestone should produce a measurable emergent capability

---

## Current: v0.1.0-alpha (April 2026)

**Theme: Foundation — core modules + integration layer**

### Completed ✅
- [x] Core module structure: `consciousness`, `cognitive_synergy`, `knowledge_graph`, `reasoning`, `homomorphic`, `quantum`, `safety`
- [x] Cognitive Blackboard integration layer (`integration/`) with event bus and module adapters
- [x] CI pipeline: lint, type checking (mypy), test matrix (Python 3.10/3.11/3.12), security scan
- [x] Community infrastructure: issue templates, PR template, CODE_OF_CONDUCT, CONTRIBUTING guide
- [x] GitHub Discussions enabled with announcement + research directions threads
- [x] v0.1.0-alpha release published

### In Progress 🔄
- [ ] Unit tests for `cognitive_synergy` module (#1 — good first issue)
- [ ] Documented examples for bi-temporal knowledge graph API (#2)
- [ ] IIT Φ benchmark against reference implementations (#3)

---

## v0.2.0 — Synergy Experiments (Q2 2026)

**Theme: Making modules talk to each other and measuring what happens**

### Integration Layer Expansion
- [ ] `ConsciousnessAdapter` → real-time φ reporting to Blackboard (currently partial mock)
- [ ] `KnowledgeGraphAdapter` → entity discovery feeding consciousness attention weights
- [ ] `CognitiveSynergyAdapter` → TC/DTC computed from live Blackboard state
- [ ] Cross-module correlation studies: does KG growth predict φ increase?

### Benchmarking Suite
- [ ] IIT Φ: comparison against [pyphi](https://github.com/wmayner/pyphi) reference implementation
- [ ] Transfer entropy: validation against Schreiber (2000) examples
- [ ] A* pathfinding: benchmark on FB15k-237 and WordNet knowledge graphs
- [ ] Synergy metrics: comparison against [idtxl](https://github.com/pwollstadt/IDTxl)

### Documentation
- [ ] Rendered API docs (Sphinx or MkDocs) hosted on GitHub Pages
- [ ] Research notebook series: "Building a cognitive synergy loop from scratch"
- [ ] Module-by-module deep-dive docs in `docs/`

---

## v0.3.0 — Experimental AGI Loop (Q3 2026)

**Theme: A minimal sense-think-act cycle using ASI:BUILD modules**

### Core Loop
- [ ] Perception input: structured text → knowledge graph ingestion
- [ ] Reasoning: hybrid symbolic-neural query over KG
- [ ] Consciousness integration: GWT working memory selects relevant KG subgraph
- [ ] Action output: structured decision + explanation

### Safety Integration
- [ ] Constitutional AI wrapper around reasoning outputs
- [ ] Formal verification of safety constraints for simple action space
- [ ] Governance module: human override protocol

### Evaluation
- [ ] GAIA benchmark (subset appropriate for text-KG reasoning)
- [ ] Custom cognitive synergy micro-benchmarks
- [ ] Published evaluation report in `docs/research/`

---

## v0.4.0 — Multi-Agent Reasoning (Q4 2026)

**Theme: Multiple ASI:BUILD instances coordinating**

- [ ] Inter-agent communication protocol (using `agi_communication` module)
- [ ] Distributed knowledge graph synchronization
- [ ] Byzantine-fault-tolerant consensus for shared beliefs
- [ ] Swarm optimization experiments (`bio_inspired` module)
- [ ] Federated learning across agents (`federated` module)

---

## Longer-Term Research Directions

These are research questions, not committed milestones:

- **Neuromorphic backend**: Can spiking neural networks replace some PyTorch components while preserving module interfaces?
- **Quantum advantage**: Are there specific cognitive synergy computations where the `quantum` module offers a real advantage?
- **Homomorphic reasoning**: Can the `homomorphic` module enable privacy-preserving KG queries?
- **BCI integration**: Real EEG data feeding the `bci` module into the consciousness model
- **Holographic memory**: Does a holographic representation (`holographic` module) improve retrieval in the KG?

---

## What We Are NOT Building

To keep scope honest:

- ❌ A chat assistant or LLM wrapper
- ❌ A plug-and-play "deploy AGI in production" system
- ❌ A reproduction of any specific proprietary AI system
- ❌ A framework that claims to "solve" AGI

ASI:BUILD is a research testbed. The goal is to produce and share knowledge about how cognitive architectures behave when implemented and composed.

---

## Contributing to the Roadmap

Ideas welcome! Open an issue with the `research` label or start a discussion in the [Research Directions thread](https://github.com/web3guru888/asi-build/discussions/5). Implemented research milestones earn a place in the CHANGELOG.

---

*Last updated: 2026-04-11 | Maintained by [@web3guru888](https://github.com/web3guru888)*

