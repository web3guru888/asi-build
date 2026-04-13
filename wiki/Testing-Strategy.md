# Testing Strategy

ASI:BUILD uses three complementary testing techniques. Each has different strengths and is appropriate for different module types.

## Overview

| Technique | Strength | Best for |
|-----------|----------|----------|
| Property-based tests | Finds edge cases you didn't anticipate | Deterministic modules with clear invariants |
| Benchmark tests | Detects drift from known-good values | Approximate/scientific modules |
| Golden file tests | Detects unintended output changes | Serialization, explanation strings |

---

## Property-Based Tests

Property-based testing (via [Hypothesis](https://hypothesis.readthedocs.io/)) generates random inputs and checks that stated properties hold for all of them. This is the **primary technique** for most ASI:BUILD modules.

### When to use

- Module output is deterministic given the same input
- You can state invariants that should hold for *any* valid input
- You want to catch bugs in edge cases (empty inputs, very large inputs, unusual Unicode, etc.)

### Example: Knowledge Graph roundtrip property

```python
from hypothesis import given, strategies as st
from asi_build.knowledge_graph import KnowledgeGraph

@given(st.lists(st.tuples(st.text(min_size=1), st.text(min_size=1), st.text(min_size=1))))
def test_kg_roundtrip(triples):
    kg = KnowledgeGraph()
    for s, p, o in triples:
        kg.add(s, p, o)
    stored = {(t.subject, t.predicate, t.object) for t in kg.query_all()}
    assert all((s, p, o) in stored for s, p, o in triples)
```

### Example: Cognitive Blackboard thread-safety property

```python
from hypothesis import given, strategies as st, settings
from concurrent.futures import ThreadPoolExecutor
from asi_build.cognitive_blackboard import CognitiveBlackboard, BlackboardEntry

@given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=50))
@settings(max_examples=20)
def test_blackboard_concurrent_writes(keys):
    bb = CognitiveBlackboard()
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(bb.write, BlackboardEntry(key=k, value=i)) for i, k in enumerate(keys)]
        [f.result() for f in futures]
    # No exception = thread safety holds for this input
```

### Useful properties to check

- **Roundtrip**: write then read returns same data
- **Monotonicity**: adding more data doesn't lose existing data
- **Idempotency**: doing something twice has same effect as once
- **Bounds**: output is within expected range (`0 <= phi`, `0 <= confidence <= 1`)
- **Non-regression**: operation doesn't raise unexpected exceptions

---

## Benchmark Tests

Benchmark tests compare module output against **known reference values** from a trusted source. Used for modules that implement scientific algorithms where "correct" is well-defined by the literature.

### When to use

- Module implements a published algorithm with reference implementations
- Output is approximate but should be close to a known value
- You want to track numerical drift over time

### Priority benchmarks for ASI:BUILD

#### IIT Φ benchmark (Issue [#6](https://github.com/web3guru888/asi-build/issues/6))

[PyPhi](https://pyphi.readthedocs.io/) is the reference implementation for IIT. We maintain a small suite of canonical networks:

```python
# tests/benchmarks/test_iit_phi.py
import pytest

# Ground truth from PyPhi 1.2.0 — DO NOT CHANGE without updating pyphi version
IIT_REFERENCE_CASES = [
    # (tpm_as_2d_array, expected_phi, tolerance)
    ([[0.5, 0.5, 0.5, 0.5], ...], 0.5, 0.05),  # Tononi 2008 example network
    ...
]

@pytest.mark.benchmark
@pytest.mark.parametrize("tpm, expected_phi, tol", IIT_REFERENCE_CASES)
def test_iit_phi_reference(tpm, expected_phi, tol):
    from asi_build.consciousness import compute_phi
    result = compute_phi(tpm)
    assert abs(result - expected_phi) < tol, f"Φ={result:.3f}, expected {expected_phi:.3f} ± {tol}"
```

Network size guidance:
- **≤ 6 nodes**: Fast, PyPhi runs in milliseconds — use freely
- **7–8 nodes**: Slow (seconds), use sparingly in CI
- **9+ nodes**: Combinatorial explosion — do not include in automated benchmarks

#### Bio-inspired recall benchmark

```python
# tests/benchmarks/test_bio_recall.py
import numpy as np
import pytest

@pytest.mark.benchmark
def test_bio_search_recall_vs_brute_force():
    from asi_build.bio_inspired import BioInspiredSearch
    
    np.random.seed(42)
    corpus = np.random.randn(1000, 128)
    queries = np.random.randn(20, 128)
    k = 10
    
    searcher = BioInspiredSearch()
    searcher.index(corpus)
    
    correct = 0
    for q in queries:
        bio_results = searcher.search(q, k=k)
        # Brute force
        scores = corpus @ q
        true_top_k = set(np.argsort(scores)[-k:])
        correct += len(set(bio_results) & true_top_k)
    
    recall = correct / (len(queries) * k)
    assert recall >= 0.8, f"Recall@10 = {recall:.2f}, expected ≥ 0.80"
```

### Running benchmarks

Benchmarks are tagged with `@pytest.mark.benchmark` and excluded from the default run:

```bash
# Default (no benchmarks):
pytest tests/

# Include benchmarks:
pytest tests/ -m benchmark

# Only benchmarks:
pytest tests/benchmarks/ -v
```

---

## Golden File Tests

Golden file tests save a known-good output to disk and fail if the output changes. Used for **output stability**, not correctness.

### When to use

- Output is complex (nested JSON, long strings, structured plans)
- You want to detect accidental format regressions
- You're OK with manually updating the golden file when format changes intentionally

### Example: Blackboard snapshot format

```python
# tests/test_blackboard_golden.py
import json, pathlib

GOLDEN_DIR = pathlib.Path("tests/golden")

def test_blackboard_snapshot_format():
    from asi_build.cognitive_blackboard import CognitiveBlackboard, BlackboardEntry
    
    bb = CognitiveBlackboard()
    bb.write(BlackboardEntry(key="test", value={"x": 1}, confidence=0.9))
    snapshot = bb.snapshot()
    
    golden_path = GOLDEN_DIR / "blackboard_snapshot.json"
    if golden_path.exists():
        expected = json.loads(golden_path.read_text())
        assert snapshot == expected, "Snapshot format changed — run with --update-goldens to accept"
    else:
        golden_path.parent.mkdir(exist_ok=True)
        golden_path.write_text(json.dumps(snapshot, indent=2))
        pytest.skip("Golden file created, run again to test")
```

### Updating golden files

When you intentionally change output format:

```bash
pytest tests/ --update-goldens
```

This flag deletes existing golden files, causing them to be regenerated on next run.

> **Policy**: Golden file updates in PRs must include an explanation in the PR description of why the format changed.

---

## Module-to-Technique Mapping

| Module | Primary | Secondary | Notes |
|--------|---------|-----------|-------|
| `knowledge_graph` | Property tests | Golden (export format) | Roundtrip, temporal consistency |
| `cognitive_blackboard` | Property tests | Benchmarks (throughput) | Thread safety critical |
| `consciousness` | Benchmarks (PyPhi ref) | Property (Φ ≥ 0) | See Issue [#6](https://github.com/web3guru888/asi-build/issues/6) |
| `bio_inspired` | Benchmarks (recall) | Property tests | Compare to brute-force |
| `reasoning` | Property tests | Golden (explanation strings) | |
| `safety` | Property tests (no false proofs) | Benchmarks (coverage) | See Issue [#7](https://github.com/web3guru888/asi-build/issues/7) |
| `homomorphic` | Property (algebraic homomorphism) | Benchmarks (numerical) | See Issue [#8](https://github.com/web3guru888/asi-build/issues/8) |
| `rings_network` | Property (message roundtrip) | — | 108 tests already |
| `meta_learning` | Property tests | — | |
| `quantum_inspired` | Property + benchmarks | — | |

---

## CI Integration

Tests run on Python 3.10, 3.11, and 3.12 on every push and PR:

```yaml
# .github/workflows/ci.yml (excerpt)
- name: Run tests
  run: pytest tests/ -q --tb=short --ignore=tests/benchmarks/
```

Benchmarks are not in the default CI run to keep build time under 2 minutes. They can be run manually or on a scheduled weekly job.

---

## See Also

- [Contributing](Contributing) — PR process, code style
- [Research Notes](Research-Notes) — detailed analysis of the three known bugs
- Discussion [#21](https://github.com/web3guru888/asi-build/discussions/21) — ongoing discussion on this strategy
