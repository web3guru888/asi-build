# Module Maturity Tiers

ASI:BUILD uses a four-tier maturity model to communicate the readiness of each module. This helps contributors and users quickly understand what to expect.

## Tier Definitions

### 🔬 Draft
- Module exists in codebase with basic structure
- May have correctness issues or missing implementations
- API may change significantly or be removed
- **Not recommended for production use**

### 🧪 Alpha
- Core functionality works and is unit-tested
- ≥80% of public API covered by tests
- Known limitations are documented
- API may change without advance notice

### 🚧 Beta
- Functionally complete with tests and benchmarks
- API is stabilizing; breaking changes announced in advance
- Performance characteristics documented
- Not yet integrated into full CognitiveCycle

### ✅ Stable
- Full test coverage + integration tests
- Benchmarked against external baselines
- API frozen (semver guaranteed within major version)
- Integrated into and validated through CognitiveCycle

---

## Current Module Status

| Module | Maturity | Notes |
|--------|----------|-------|
| `consciousness` | 🚧 Beta | IIT Φ fixed (#6), benchmarks complete (#24), real-time integration pending (#41) |
| `reasoning` | 🚧 Beta | HybridReasoningEngine solid; PLN sub-engine stub pending (#44) |
| `knowledge_graph` | 🚧 Beta | Bi-temporal KG + A* pathfinder; temporal filtering pending (#51) |
| `safety` | 🚧 Beta | Formal prover fixed (#7); Blackboard gating pending (#37) |
| `bio_inspired` | 🧪 Alpha | Wired to Blackboard; sleep-wake cycles are simplified models |
| `cognitive_synergy` | 🧪 Alpha | PRIMUS theory + 10 synergy pairs; first external PR (#85) adding tests |
| `rings` | 🚧 Beta | DID auth + Blackboard adapter wired; Phase 1 deployed |
| `quantum` | 🧪 Alpha | VQE/QAOA/QNN functional; no GPU backend yet; Blackboard pending (#53) |
| `homomorphic` | 🧪 Alpha | NTT fixed (#8); MPC/ZKP research-grade |
| `neuromorphic` | 🧪 Alpha | STDP works; benchmarks pending (#54) |
| `holographic` | 🔬 Draft | No Blackboard wiring yet (#56) |
| `federated_learning` | 🧪 Alpha | Byzantine robustness + DP implemented; Blackboard pending (#58) |
| `graph_intelligence` | 🧪 Alpha | FastToG + community detection wired to Blackboard |
| `knowledge_management` | 🧪 Alpha | Wired to Blackboard; Omniscience Network research-grade |
| `agi_communication` | 🧪 Alpha | Game-theoretic negotiation; Blackboard pending (#48) |
| `agi_economics` | 🧪 Alpha | Reputation + incentives implemented; Blackboard adapter TBD |
| `agi_reproducibility` | 🧪 Alpha | AGSSL + formal provers; Blackboard pending (#80) |
| `blockchain` | 🧪 Alpha | Merkle chains + IPFS audit trails; Blackboard pending (#96) |
| `bci` | 🧪 Alpha | EEG pipelines + P300 detection; privacy architecture pending (#105) |
| `compute` | 🧪 Alpha | GPU/TPU resource management; Blackboard pending (#70) |
| `distributed_training` | 🧪 Alpha | 1000-node FL + Byzantine FT; Blackboard pending (#75) |
| `vectordb` | 🧪 Alpha | Pinecone/Weaviate/Qdrant unified; Blackboard pending (#77) |
| `deployment` | 🧪 Alpha | HuggingFace + CUDO backends; container orchestration planned |
| `servers` | 🧪 Alpha | FastAPI + MCP/SSE working; rate limiting + service mesh pending |
| `integrations` | 🧪 Alpha | LangChain + MCP + LangGraph; Blackboard pending (#90) |
| `multimodal` | 🔬 Draft | Proposed in Issue #108; not yet implemented |
| `pln_accelerator` | 🧪 Alpha | NL↔logic bridge + hardware backends; PLN sub-engine pending (#44) |
| `vla_optimization` | 🧪 Alpha | 217MB→50MB compression; Blackboard pending (#83) |
| `optimization` | 🧪 Alpha | Various optimizers; module-level scope |

---

## Maturity Criteria (detailed)

### Alpha → Beta promotion requires:
1. All public classes/functions have type hints and docstrings
2. Unit test coverage ≥ 80% (measured by `pytest-cov`)
3. Performance benchmarks exist and are checked into `tests/benchmarks/`
4. Module has a wiki page documenting API + known limitations
5. No open `bug` label issues without a documented workaround

### Beta → Stable promotion requires:
1. All Alpha → Beta criteria met
2. Integration tests pass with CognitiveCycle (Issue #41)
3. Blackboard adapter wired and tested (integration tests per Issue #99)
4. API documented in `docs/modules/{module_name}.md`
5. Benchmarks compared against at least one external baseline

---

## Declaring Maturity in Code

Modules can declare their maturity level via the `__maturity__` attribute in `__init__.py`:

```python
# src/asi_build/consciousness/__init__.py
__maturity__ = "beta"
__maturity_notes__ = (
    "IIT Φ fixed (#6), GWT/AST benchmarks complete (#24). "
    "Real-time CognitiveCycle integration pending (#41)."
)
```

This is queryable at runtime:

```python
from asi_build import consciousness
print(consciousness.__maturity__)       # "beta"
print(consciousness.__maturity_notes__) # "IIT Φ fixed..."
```

Tracking issue for adding `__maturity__` declarations to all modules: see Discussion #111.

---

## See Also

- [Roadmap](Roadmap) — Phase 4 targets stable-tier modules
- [Testing Strategy](Testing-Strategy) — Coverage requirements
- [Architecture Overview](Architecture-Overview) — How modules connect
