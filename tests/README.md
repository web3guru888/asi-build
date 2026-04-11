# ASI:BUILD Test Suite

## Running Tests

```bash
cd /path/to/asi-build
python -m pytest tests/ --rootdir=tests -v
```

The `--rootdir=tests` flag is required because the repo root has a broken `__init__.py` that pytest would otherwise try to import.

With coverage:
```bash
python -m pytest tests/ --rootdir=tests -v --cov=consciousness_engine --cov=graph_intelligence --cov=cognitive_synergy --cov-report=term-missing
```

## Test Dependencies

```bash
pip install -r tests/requirements-test.txt
```

## What's Tested

### `test_consciousness_engine.py`
- **Data types**: `ConsciousnessState`, `ConsciousnessEvent`, `ConsciousnessMetrics` — creation, serialization, defaults
- **Subclass instantiation**: All 14 `BaseConsciousness` subclasses (5 with own `_initialize`, 9 patched via conftest)
- **BaseConsciousness infra**: Event queue priority ordering, subscribe/emit, state callbacks, save/load state
- **Global Workspace Theory**: Default processors, competition selecting highest activation, workspace size limits, processor interest/capacity checks, broadcast history
- **Integrated Information Theory**: Default network topology, Φ=0 for single/disconnected elements, Φ≥0 for connected systems, element/connection management, sigmoid/threshold activation, state history, reset
- **Memory Integration**: form/retrieve/consolidate memories, keyword-based retrieval, type filtering, working memory capacity, reconsolidation, decay, consciousness binding, event processing

### `test_graph_intelligence.py`
- **Enums**: `NodeType` (13 members), `RelationshipType` (14 members)
- **Node dataclasses**: All 11 node types — creation, field storage, `to_dict()` serialization (JSON for lists/dicts)
- **Relationship**: Creation, `to_dict()` serialization
- **KnowledgeGraphSchema**: `create_node`, `create_relationship`, `validate_node`, Cypher generation for nodes and relationships
- **Factory functions**: All 7 convenience factories (`create_ui_element`, `create_community`, etc.)
- **SchemaManager**: Skipped (requires live Neo4j/Memgraph instance)

### `test_cognitive_synergy.py`
- **Data types**: `SynergyMeasurement`, `SynergyProfile` — creation and defaults
- **Mutual Information**: High MI for identical signals, low MI for independent, MI=0 for constant
- **Transfer Entropy**: Positive TE for coupled signals (y[t+1] depends on x[t]), low TE for independent
- **Phase Locking Value**: PLV≈1.0 for identical/phase-shifted sine waves, low PLV for random signals
- **Coherence**: High for identical signals, lower for unrelated broadband noise
- **Composite metrics**: Emergence index, integration index, complexity resonance — all bounded [0,1]
- **Edge cases**: Insufficient data, unknown pairs, history length limits, all-metrics-bounded check
- **Helpers**: `get_synergy_strength`, `get_emergence_indicators`, `compute_global_synergy`
- **Internals**: `_discretize_signal`, `_entropy`, `_lempel_ziv_complexity` edge cases

## Known Issues

### Consciousness Engine Init-Ordering Bug
`BaseConsciousness.__init__` calls `self._initialize()` before subclass constructors set up their own attributes (e.g. `self.elements`, `self.workspace_buffer`). This means **all** subclasses crash on instantiation on `main`.

Additionally, 9 of the 14 subclasses are missing the required abstract `_initialize()` method entirely, and `MetacognitionSystem` has a `_initialize` that references a shadowed enum (`MetacognitiveStrategy` is defined as both an Enum and a dataclass in the same file).

The conftest applies three patches at module scope:
1. Rewrites `BaseConsciousness.__init__` to skip the premature `_initialize()` call
2. Wraps each subclass `__init__` to call `_initialize()` after attribute setup completes
3. Adds no-op `_initialize` for the 10 classes that lack a working one

Once `fix/security-and-bugs` merges, these patches should become unnecessary.

### Root `__init__.py` Conflict  
The repo root has an `__init__.py` that imports non-existent sibling packages via relative imports. Tests must be run with `--rootdir=tests` to prevent pytest from treating the repo root as a package.

### SchemaManager Tests Skipped
`TestSchemaManager` is skipped because it requires a running Neo4j or Memgraph instance. Un-skip the class when a graph database service is available in the test environment.
