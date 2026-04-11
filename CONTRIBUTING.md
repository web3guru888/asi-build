# Contributing to ASI:BUILD

Thank you for your interest in contributing to ASI:BUILD! This document describes how to contribute effectively to the project.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Adding a New Module](#adding-a-new-module)
- [What NOT to Contribute](#what-not-to-contribute)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Research Contributions](#research-contributions)

---

## Getting Started

1. **Fork** the repository on GitLab
2. **Clone** your fork locally:
   ```bash
   git clone https://gitlab.com/YOUR_USERNAME/asi-build.git
   cd asi-build
   ```
3. **Install** with dev dependencies:
   ```bash
   pip install -e ".[dev]"
   # or
   make install
   ```
4. **Verify** the test suite passes:
   ```bash
   make test
   ```

---

## Development Workflow

### Branching

Create a descriptive branch for your work:

```bash
# For new features
git checkout -b feat/consciousness-working-memory

# For bug fixes
git checkout -b fix/graph-intelligence-cypher-injection

# For documentation
git checkout -b docs/knowledge-graph-api-reference

# For research experiments
git checkout -b research/iit-phi-approximation
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(consciousness): add working memory decay model
fix(graph_intelligence): sanitize Cypher query parameters
docs(knowledge_graph): add pathfinding examples
test(cognitive_synergy): add transfer entropy edge cases
refactor(homomorphic): simplify CKKS encoding pipeline
```

### Keeping Your Fork Updated

```bash
git remote add upstream https://gitlab.com/asi-build/asi-build.git
git fetch upstream
git rebase upstream/main
```

---

## Code Standards

### Python Version

Target Python **3.11+**. Use modern Python features (match statements, `typing.Self`, `tomllib`, etc.) — but don't add dependencies just to use a newer feature.

### Type Hints

**Required** for all public functions and methods:

```python
# ✅ Good
def compute_phi(
    self,
    network_state: list[list[int]],
    threshold: float = 0.3
) -> PhiResult:
    ...

# ❌ Bad — no type hints
def compute_phi(self, network_state, threshold=0.3):
    ...
```

Use `from __future__ import annotations` at the top of files with forward references.

### Docstrings

**Required** for all public classes and methods. Use Google style:

```python
def find_path(
    self,
    source: str,
    target: str,
    algorithm: str = "astar"
) -> PathResult:
    """Find the shortest path between two knowledge graph entities.

    Uses A* search with pheromone-weighted edge costs. Falls back to
    Dijkstra if no heuristic is available for the given node types.

    Args:
        source: Entity ID of the starting node.
        target: Entity ID of the destination node.
        algorithm: Pathfinding algorithm. One of "astar", "dijkstra",
            "bfs". Default "astar".

    Returns:
        PathResult with .edges (list of triples), .cost (float),
        and .hops (int).

    Raises:
        EntityNotFoundError: If source or target are not in the graph.
        NoPathError: If no path exists between source and target.

    Example:
        >>> kg = BiTemporalKnowledgeGraph()
        >>> path = kg.find_path("concept_A", "concept_B")
        >>> print(f"Found path in {path.hops} hops")
    """
```

### Formatting

**black** is enforced in CI. Line length is **100 characters**.

```bash
# Format before committing
make format
# or
black src/ tests/
```

### Import Order

Use [isort](https://pycran.org/isort/) compatible ordering:
1. Standard library
2. Third-party packages
3. Local (`asi_build`) imports

```python
# Standard library
import asyncio
from typing import Optional

# Third-party
import numpy as np
import networkx as nx

# Local
from asi_build.knowledge_graph import BiTemporalKnowledgeGraph
from asi_build.consciousness.types import PhiResult
```

### Error Handling

- Raise specific, descriptive exceptions (define them in `module/exceptions.py`)
- Don't swallow exceptions silently
- Include context in error messages:

```python
# ✅ Good
raise EntityNotFoundError(
    f"Entity '{entity_id}' not found in knowledge graph. "
    f"Graph has {len(self._nodes)} entities. "
    f"Did you mean: {self._suggest_similar(entity_id)}?"
)

# ❌ Bad
raise ValueError("not found")
```

---

## Testing Requirements

**Every module must have tests.** PRs without tests will not be merged.

### Test Structure

Tests live in `tests/`, one file per module:

```
tests/
├── test_consciousness.py
├── test_cognitive_synergy.py
├── test_graph_intelligence.py
├── test_homomorphic.py
├── test_knowledge_graph.py
└── ...
```

### What to Test

For each module, test:

1. **Happy path** — normal usage works correctly
2. **Edge cases** — empty inputs, boundary values, large inputs
3. **Error cases** — invalid inputs raise the right exceptions
4. **Invariants** — mathematical properties hold (e.g., Φ ≥ 0 always)

```python
import pytest
from asi_build.consciousness import IntegratedInformationTheory

class TestIIT:
    def setup_method(self):
        self.iit = IntegratedInformationTheory(phi_threshold=0.3)

    def test_phi_non_negative(self):
        """Φ must always be non-negative."""
        for _ in range(10):
            state = np.random.randint(0, 2, (5, 5)).tolist()
            phi = self.iit.compute_phi(state)
            assert phi >= 0.0

    def test_disconnected_network_phi_zero(self):
        """A fully disconnected network has Φ = 0."""
        disconnected = [[0,0,0],[0,0,0],[0,0,0]]
        phi = self.iit.compute_phi(disconnected)
        assert phi == pytest.approx(0.0, abs=1e-6)

    def test_invalid_state_raises(self):
        """Non-square matrix should raise ValueError."""
        with pytest.raises(ValueError, match="square"):
            self.iit.compute_phi([[1,0],[0,1,0]])
```

### Running Tests

```bash
pytest tests/ -v              # Full suite with output
pytest tests/ -x -q           # Stop on first failure
pytest tests/test_consciousness.py -v -k "phi"  # Filter by name
```

### Async Tests

Use `pytest-asyncio` for async code:

```python
import pytest

@pytest.mark.asyncio
async def test_async_knowledge_query():
    kg = BiTemporalKnowledgeGraph()
    result = await kg.async_query("MATCH (n) RETURN n LIMIT 5")
    assert len(result) <= 5
```

---

## Adding a New Module

Here's how to add a new module to `src/asi_build/`:

### 1. Create the module directory

```bash
mkdir -p src/asi_build/my_module
```

### 2. Required files

```
src/asi_build/my_module/
├── __init__.py          # Public API exports
├── core.py              # Main implementation
├── types.py             # Data classes, TypedDicts, enums
├── exceptions.py        # Module-specific exceptions
└── README.md            # Module documentation (optional but encouraged)
```

### 3. `__init__.py` — Export your public API explicitly

```python
"""
asi_build.my_module
===================
Brief one-line description.

Longer description of what this module does, what algorithms it
implements, and what external dependencies it requires.

Dependencies:
    pip install asi-build[my_module_extra]

Example:
    >>> from asi_build.my_module import MyMainClass
    >>> obj = MyMainClass(param=42)
    >>> result = obj.compute()
"""

from asi_build.my_module.core import MyMainClass, MySecondClass
from asi_build.my_module.types import MyResult, MyConfig
from asi_build.my_module.exceptions import MyModuleError

__all__ = [
    "MyMainClass",
    "MySecondClass",
    "MyResult",
    "MyConfig",
    "MyModuleError",
]
```

### 4. Update `pyproject.toml`

Add an optional dependency group if your module needs external packages:

```toml
[project.optional-dependencies]
my_module = ["some-package>=1.0"]
all = ["asi-build[consciousness,graph,...,my_module,dev]"]
```

### 5. Write tests

Create `tests/test_my_module.py` with comprehensive coverage.

### 6. Add an example

Create `examples/my_module_demo.py` showing the key use cases.

### 7. Document it

Add a row to the Modules table in README.md:

```markdown
| `my_module` | 🟢 Implemented | Brief description | ~1,200 |
```

---

## What NOT to Contribute

To keep the project lean and honest, please **do not** contribute:

- **Template-generated code** — Files produced by code generators with no real implementation. If a class has all methods as `pass` or `raise NotImplementedError`, that's scaffolding, not code.
- **Modules without tests** — No exceptions. If you can't test it, it belongs in `archive/` not `src/`.
- **Duplicate functionality** — Check existing modules before adding new ones. We already have `graph_intelligence` and `knowledge_graph`; a third KG module needs a very clear justification.
- **Hardcoded credentials or API keys** — These will be rejected immediately. Use `configs/default.yaml` and environment variables.
- **Scraped content or bulk-imported data** — External datasets should be downloaded on demand, not committed.
- **One-time scripts** — Scripts you ran once to migrate data or fix something. If it's not reusable, it doesn't belong here.
- **Internal correspondence or private docs** — Even as "examples". This repository is public.
- **Archive content** — The `archive/` directory exists to preserve v1 history. Don't add to it — it's read-only.

---

## Submitting a Pull Request

1. **Ensure tests pass** locally: `make test`
2. **Ensure formatting** is correct: `make lint`
3. **Push** your branch and open a PR against `main`
4. Fill in the PR template:
   - What does this PR do?
   - Which modules does it touch?
   - What tests were added?
   - Are there breaking changes?
5. **Link** any related issues

PRs are reviewed for:
- Correctness of implementation
- Test coverage
- Code style compliance
- Documentation quality
- Absence of hardcoded credentials

---

## Research Contributions

ASI:BUILD is primarily a research project. We welcome:

- **Algorithm implementations** — New implementations of published algorithms (with citations)
- **Benchmarks** — Rigorous comparisons between approaches
- **Research notes** — Findings from experiments, documented in `docs/research/`
- **Integration studies** — How ASI:BUILD modules interact and produce emergent behavior

For research contributions, include:
- The paper(s) you're implementing (arXiv IDs preferred)
- Validation that your implementation produces results matching the paper
- Notes on any deviations from the paper and why

---

## Questions?

Open an issue with the `question` label. We try to respond within a few days.
