# Contributing

Thank you for your interest in contributing to ASI:BUILD! This page summarizes the key points. The full guide lives in [CONTRIBUTING.md](https://github.com/web3guru888/asi-build/blob/main/CONTRIBUTING.md) in the repo.

---

## Quick Start

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/asi-build.git
cd asi-build

# 2. Install with dev dependencies
pip install -e ".[dev]"

# 3. Verify the test suite passes
pytest tests/ -q
# Expected: 2581 passed, 42 skipped

# 4. Create a branch
git checkout -b feat/your-feature-name
```

---

## Good First Issues

New here? These are the easiest places to start:

| Issue | What it involves |
|-------|-----------------|
| [#13 — Add type hints to bio_inspired](https://github.com/web3guru888/asi-build/issues/13) | Python typing, no algorithm knowledge needed |
| [#14 — Create Cognitive Blackboard demo](https://github.com/web3guru888/asi-build/issues/14) | Write example script using the integration API |
| [#15 — Update docs/modules/ for all 28 modules](https://github.com/web3guru888/asi-build/issues/15) | Read code, write clear docs |
| [#2 — Document KG API](https://github.com/web3guru888/asi-build/issues/2) | Documentation + docstrings for knowledge_graph |
| [#1 — Add tests for cognitive_synergy](https://github.com/web3guru888/asi-build/issues/1) | Pytest test writing |

Browse all: [good first issue label](https://github.com/web3guru888/asi-build/labels/good%20first%20issue)

---

## Branching Convention

```bash
git checkout -b feat/consciousness-working-memory   # new feature
git checkout -b fix/graph-intelligence-query-safety  # bug fix
git checkout -b docs/knowledge-graph-api-reference   # documentation
git checkout -b research/iit-phi-pyphi-backend        # research
```

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(consciousness): add working memory decay model
fix(homomorphic): use NTT-friendly prime moduli
docs(knowledge_graph): add A* pathfinding examples
test(cognitive_synergy): add transfer entropy edge cases
research(safety): integrate Z3 SMT backend
```

---

## Code Style

| Requirement | Tool | Setting |
|-------------|------|---------|
| Formatting | `black` | 100 character lines |
| Type hints | `mypy` | Required on all public functions |
| Docstrings | Google style | Required on all public classes/methods |
| Import sort | `ruff` | auto |

```bash
make format   # black src/ tests/
make lint     # black --check + mypy + ruff
```

### Example: Well-styled function

```python
def compute_synergy(
    stream_a: list[float],
    stream_b: list[float],
    method: str = "mutual_information",
) -> dict[str, float]:
    """Compute information-theoretic synergy between two streams.

    Args:
        stream_a: First data stream (list of floats).
        stream_b: Second data stream, same length as stream_a.
        method: One of "mutual_information", "transfer_entropy", "lz_complexity".

    Returns:
        Dict with keys matching the method name and float values.

    Raises:
        ValueError: If streams have different lengths or method is unknown.
    """
    if len(stream_a) != len(stream_b):
        raise ValueError(f"Streams must have same length: {len(stream_a)} vs {len(stream_b)}")
    ...
```

---

## Testing Requirements

**Every module must have tests.** No exceptions.

Create `tests/test_your_module.py`:

```python
import pytest
from asi_build.my_module import MyClass

class TestMyClass:
    def setup_method(self):
        self.obj = MyClass()

    def test_basic_usage(self):
        result = self.obj.compute(input=[1, 2, 3])
        assert result["value"] >= 0

    def test_empty_input_raises(self):
        with pytest.raises(ValueError, match="empty"):
            self.obj.compute(input=[])

    def test_known_output(self):
        """Validate against a known-correct example."""
        result = self.obj.compute(input=[1, 0, 1])
        assert result["value"] == pytest.approx(0.693, rel=1e-3)
```

Run tests:
```bash
pytest tests/ -v                            # all tests
pytest tests/test_my_module.py -v          # one module
pytest tests/ -k "synergy" -v             # filter by name
```

---

## Adding a New Module

1. Create `src/asi_build/my_module/` with `__init__.py`, `core.py`
2. Export public API from `__init__.py`
3. Add to `pyproject.toml` if it needs optional dependencies
4. Write `tests/test_my_module.py`
5. Add an example in `examples/my_module_demo.py`
6. Update the Modules table in `README.md`

See [CONTRIBUTING.md](https://github.com/web3guru888/asi-build/blob/main/CONTRIBUTING.md) for the full module template.

---

## What to Fix Next (Research Contributions)

The highest-impact research contributions right now:

| Area | Issue | Approach |
|------|-------|----------|
| IIT Φ correctness | [#6](https://github.com/web3guru888/asi-build/issues/6) | Wrap PyPhi, implement TPM-based Φ per Tononi 2014 |
| Homomorphic NTT bug | [#8](https://github.com/web3guru888/asi-build/issues/8) | Fix to NTT-friendly primes; or wrap OpenFHE/SEAL |
| Safety formal verification | [#7](https://github.com/web3guru888/asi-build/issues/7) | Replace SymPy with Z3 SMT solver |

All three have concrete fix paths described in their issue threads.

---

## What NOT to Contribute

- **Scaffolding/templates** without real implementations (methods that just `raise NotImplementedError`)
- **Modules without tests** — if you can't test it, it belongs in `archive/`
- **Hardcoded credentials or API keys**
- **Scraped/bulk-imported datasets** — download on demand, don't commit

---

## Pull Request Process

1. `make test` passes locally
2. `make lint` passes (formatting + types)
3. Open PR against `main` with:
   - What it does
   - What modules it touches
   - What tests were added
   - Any breaking changes
4. Link related issues (`Closes #6`, `Related to #7`)

---

## Questions?

Open a [Q&A discussion](https://github.com/web3guru888/asi-build/discussions/categories/q-a) or file an issue with the `question` label. We respond within a few days.
