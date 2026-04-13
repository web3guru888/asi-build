# Roadmap

ASI:BUILD follows a phased development plan. Each phase builds on the previous one, moving from foundation to emergent intelligence.

---

## Phase 1 — Foundation ✅ Complete

**Goal**: Establish a solid, tested, honest codebase.

**Timeline**: August 2025 → April 2026

| Milestone | Status |
|-----------|--------|
| 28 modules implemented across `src/asi_build/` | ✅ |
| Modern Python packaging (`pyproject.toml`, `src/` layout) | ✅ |
| 2,581 passing tests across Python 3.10/3.11/3.12 | ✅ |
| GitHub Actions CI pipeline | ✅ |
| Honest module status taxonomy (Implemented / Structural) | ✅ |
| MIT license, public release on GitHub | ✅ |
| v0.1.0-alpha release | ✅ |
| CONTRIBUTING.md, CODE_OF_CONDUCT.md | ✅ |

**What Phase 1 established**: A clear separation between working code and aspirational scaffolding, a test suite that actually covers the implemented modules, and standard open-source project infrastructure.

---

## Phase 2 — Cross-Module Integration ✅ Complete

**Goal**: Enable modules to communicate and compose without tight coupling.

**Timeline**: April 2026

| Milestone | Status |
|-----------|--------|
| `CognitiveBlackboard` shared workspace | ✅ |
| `EventBus` pub/sub with wildcard routing | ✅ |
| `BlackboardEntry` type-safe protocol | ✅ |
| `ConsciousnessAdapter` | ✅ |
| `KnowledgeGraphAdapter` | ✅ |
| `CognitiveSynergyAdapter` | ✅ |
| `ReasoningAdapter` | ✅ |
| `wire_all()` / `production_sweep()` utilities | ✅ |
| Integration test suite (3,782 LOC in `integration/`) | ✅ |

**What Phase 2 established**: Any module can post findings to the blackboard and subscribe to findings from any other module. The Cognitive Blackboard pattern is fully operational with 4 adapters covering the core cognitive modules.

---

## Phase 3 — Science Correctness 🔬 Active

**Goal**: Fix known scientific inaccuracies in implemented modules. Replace approximate/broken algorithms with correct ones.

**Timeline**: April–June 2026

### 3.1 IIT Φ Computation (Issue [#6](https://github.com/web3guru888/asi-build/issues/6)) ✅ Fixed

**Problem**: The original `IntegratedInformation` module computed an entropy-difference approximation of Φ, not the TPM-based Φ from Tononi (2014). Φ was always 0.0 on fresh instances.

**Fixed** in [commit 693742e](https://github.com/web3guru888/asi-build/commit/693742e) (2026-04-11):
- Correct IIT 3.0 TPM-based Φ with MIP bipartition enumeration (Oizumi, Albantakis & Tononi 2014)
- `test_phi_recurrent_integrated_network` now passes: Φ = 0.524 for a 3-node bidirectional network
- See [Research Notes — IIT Φ](Research-Notes#iit-φ--fixed-2026-04-11-commit-693742e) for full technical details

**Next step**: Benchmark Φ scaling (O(2^n)) to determine when approximation methods are needed — see [Issue #24](https://github.com/web3guru888/asi-build/issues/24).

### 3.2 Homomorphic NTT Bug (Issue [#8](https://github.com/web3guru888/asi-build/issues/8)) 🔴 Open

**Problem**: The Number Theoretic Transform in the `homomorphic` module uses co-prime moduli that violate the polynomial ring structure required for correct BGV/BFV operations. Encrypted computation produces incorrect results.

**Fix plan**:
1. Switch to NTT-friendly primes (of form `2^k * c + 1`)
2. Validate with known ciphertext-plaintext test pairs
3. Alternatively, wrap [OpenFHE](https://openfhe.org/) or [Microsoft SEAL](https://github.com/microsoft/SEAL)

**Status**: Open — see [issue #8](https://github.com/web3guru888/asi-build/issues/8). Good research contribution opportunity.

### 3.3 Safety Formal Verification (Issue [#7](https://github.com/web3guru888/asi-build/issues/7)) ✅ Fixed

**Problem**: `safety/formal_verification.py` proved every property as `True` without actual constraint solving. Auto-proves were caused by ungrounded symbols, trivial 2-model checking, and parse failures silently wrapping as symbols.

**Fixed** in [commit ce0e3f0](https://github.com/web3guru888/asi-build/commit/ce0e3f0) (2026-04-11):
- 5 root causes identified and fixed (bare `except` → `FormulaParseError`, axiom parse bug, ungrounded conclusion symbols, exhaustive model checking, symbolic forward-chaining)
- 72 new tests added covering parse errors, valid entailments, invalid fallacies, model checking
- Value alignment and compliance checking are now functional
- See [Research Notes — Safety](Research-Notes#safety-formal-verification-auto-prove-bug) and [Discussion #26](https://github.com/web3guru888/asi-build/discussions/26)

### 3.4 Structural Module Implementations

Several 🟡 Structural modules have well-defined interfaces but no real backends. Phase 3 will implement the highest-value ones:

| Module | Priority | Notes |
|--------|----------|-------|
| `reasoning` | High | HybridReasoningEngine backend needed |
| `vectordb` | High | Wire Pinecone/Qdrant/Weaviate clients |
| `quantum` | Medium | Validate Qiskit circuits |
| `optimization` | Medium | PyTorch quantization pipeline |
| `neuromorphic` | Low | SNN simulation backend |

---

## Phase 4 — Emergent Cognition 📋 Planned

**Goal**: Enable genuine cross-module synergy — modules influencing each other's behavior in real time through the Cognitive Blackboard, producing behaviors that no single module could produce alone.

**Timeline**: Q3–Q4 2026

| Milestone | Status |
|-----------|--------|
| Continuous blackboard sweeps (background thread) | Planned |
| Feedback loops: reasoning output → KG → synergy re-measurement | Planned |
| Attention gating: high-Φ states prioritize reasoning bandwidth | Planned |
| Temporal coherence: multi-cycle cognitive rhythms | Planned |
| Benchmark suite: cross-module emergent behaviors | Planned |
| Rings Network integration (decentralized multi-agent inference) | 🔬 Started |

### Rings Network Integration

The `rings` module (just started) explores integrating ASI:BUILD with the [Rings Network](https://rings.network/) — a decentralized peer-to-peer protocol for multi-agent AI inference. This would allow multiple ASI:BUILD instances to share blackboard entries across a distributed network, enabling emergent cognition at scale.

See `/shared/kb/mempalace-agi-reports/rings-network-integration-report-2026-04-11.md` for the current integration report.

---

## Known Science Gaps (Honest Assessment)

These are areas where the codebase does not yet match the scientific state of the art. We track these openly:

| Issue | Module | Severity | Status | Tracking |
|-------|--------|----------|--------|----------|
| IIT Φ was entropy-diff, not Tononi 2014 | `consciousness` | High | ✅ Fixed (693742e) | [#6](https://github.com/web3guru888/asi-build/issues/6) |
| Homomorphic NTT uses wrong primes | `homomorphic` | High | 🔴 Open | [#8](https://github.com/web3guru888/asi-build/issues/8) |
| Formal verification auto-proved everything | `safety` | High | ✅ Fixed (ce0e3f0) | [#7](https://github.com/web3guru888/asi-build/issues/7) |
| ~17 modules are structural scaffolding | various | Medium | Ongoing | [Module Index](Module-Index) |
| `reasoning` module is thin scaffolding | `reasoning` | Medium | Ongoing | — |

We believe transparency about these gaps is more valuable than pretending they don't exist. Fix contributions are very welcome — see [[Contributing]].

---

## Contributing to the Roadmap

Have a Phase 3 or Phase 4 idea? Open a discussion in the [Ideas category](https://github.com/web3guru888/asi-build/discussions/categories/ideas) or file an [enhancement issue](https://github.com/web3guru888/asi-build/issues/new).

For science correctness fixes, the highest-impact remaining contribution is:
1. **FHE backend via OpenFHE** — [issue #8](https://github.com/web3guru888/asi-build/issues/8) ← only remaining high-severity open bug

Issues #6 (IIT Φ) and #7 (safety formal verification) were fixed in April 2026. See [Research Notes](Research-Notes) for technical details on each fix.
