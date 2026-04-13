# Module Maturity Model

ASI:BUILD uses a four-level module maturity model to communicate stability expectations to contributors and users. Every module exposes its maturity level via the `__maturity__` attribute in its `__init__.py`.

Introduced in commit [`a4b0bfb`](https://github.com/web3guru888/asi-build/commit/a4b0bfb) — see [Discussion #111](https://github.com/web3guru888/asi-build/discussions/111) for the design discussion.

---

## Maturity Levels

### 🟢 `stable`
The module has a frozen public API, comprehensive test coverage (≥ 90%), property tests, zero known P0 or P1 bugs, and has been used in at least one integration scenario. Breaking changes require a major version bump and a deprecation cycle.

**Current modules**: `safety`

### 🔵 `beta`
The public API is mostly stable, test coverage is meaningful (≥ 70%), and the module integrates with the Cognitive Blackboard. Minor breaking changes may occur between minor versions. Known limitations are documented.

**Current modules**: `consciousness`, `knowledge_graph`, `reasoning`, `bio_inspired`, `cognitive_synergy`, `rings`, `pln_accelerator`

### 🟡 `alpha`
Core functionality works and is tested, but the API may change. The module may have known gaps (stub methods, placeholder algorithms, partial integration). Not recommended for production use.

**Current modules**: `quantum`, `holographic`, `federated`, `homomorphic`, `neuromorphic`, `blockchain`, `bci`, `distributed_training`, `agi_communication`, `graph_intelligence`, `knowledge_management`, `vectordb`

### 🔴 `experimental`
Early-stage research code. APIs are unstable, tests are minimal, and the module may have known incorrect behavior. Intended for exploration and contribution, not downstream consumption.

**Current modules**: `compute`, `agi_economics`, `agi_reproducibility`, `optimization`, `integrations`

---

## Reading Maturity Metadata

```python
import asi_build.consciousness as consciousness_mod
print(consciousness_mod.__maturity__)  # → "beta"

import asi_build.safety as safety_mod
print(safety_mod.__maturity__)  # → "stable"
```

The `CognitiveCycle` scheduler can also query maturity at runtime to apply different error handling strategies per module:

```python
import importlib

def get_maturity(module_name: str) -> str:
    mod = importlib.import_module(f"asi_build.{module_name}")
    return getattr(mod, "__maturity__", "experimental")

# Skip experimental modules in production cycle
SKIP_IN_PRODUCTION = {
    name for name in ALL_MODULES
    if get_maturity(name) == "experimental"
}
```

---

## Graduation Criteria

To graduate from one level to the next:

| From → To | Requirements |
|-----------|-------------|
| `experimental` → `alpha` | Core algorithm implemented; basic tests passing; no import errors |
| `alpha` → `beta` | ≥ 70% test coverage; Blackboard adapter wired; no P0 bugs; API documented in wiki |
| `beta` → `stable` | ≥ 90% test coverage; property tests; integration tests with 2+ other modules; API frozen; at least one external use case |

---

## Current Distribution (as of commit `a4b0bfb`)

| Maturity | Count | Modules |
|----------|-------|---------|
| stable | 1 | safety |
| beta | 7 | consciousness, knowledge_graph, reasoning, bio_inspired, cognitive_synergy, rings, pln_accelerator |
| alpha | 12 | quantum, holographic, federated, homomorphic, neuromorphic, blockchain, bci, distributed_training, agi_communication, graph_intelligence, knowledge_management, vectordb |
| experimental | 5 | compute, agi_economics, agi_reproducibility, optimization, integrations |
| **total** | **25*** | *4 utility modules (deployment, memgraph_toolbox, servers, integration) not yet rated |

---

## CI Integration

The maturity level is checked in CI to enforce documentation requirements:

```yaml
# .github/workflows/ci.yml (planned)
- name: Check maturity metadata
  run: |
    python3 -c "
    import ast, pathlib
    for init in pathlib.Path('src/asi_build').glob('*/__init__.py'):
        src = init.read_text()
        if '__maturity__' not in src:
            print(f'MISSING: {init}')
            exit(1)
    print('All modules have __maturity__ metadata ✓')
    "
```

---

## Contributing: Improving a Module's Maturity

If you want to help graduate a module from `alpha` to `beta`, here is the checklist:

1. **Check coverage**: `pytest tests/test_<module>.py --cov=asi_build.<module> --cov-report=term-missing`
2. **Add property tests**: Use `hypothesis` to generate random inputs
3. **Wire Blackboard adapter**: See [Cognitive Blackboard](Cognitive-Blackboard) and [Integration Layer](Integration-Layer) wiki pages
4. **Document the API**: Add or update the module's wiki page
5. **Open a PR** and reference the maturity graduation in the PR description

See [Contributing](Contributing) for the full PR process.

---

## Related

- [Discussion #111](https://github.com/web3guru888/asi-build/discussions/111) — original RFC
- [Discussion #115](https://github.com/web3guru888/asi-build/discussions/115) — 8 new adapters + maturity rollout
- [Integration Layer](Integration-Layer) — Blackboard adapter pattern
- [Async Architecture](Async-Architecture) — `AsyncAdapterBase` base class
- [Testing Strategy](Testing-Strategy) — coverage requirements
