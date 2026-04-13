# Troubleshooting

Common issues and solutions when working with ASI:BUILD.

---

## Installation Issues

### `ImportError: No module named 'torch'`

Several modules require PyTorch but it's not listed as a hard dependency to keep install size small.

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

For GPU support, follow the [PyTorch installation guide](https://pytorch.org/get-started/locally/).

### `ImportError: No module named 'z3'`

The `safety/` module uses the Z3 SMT solver for formal verification.

```bash
pip install z3-solver
```

### Tests fail with `ModuleNotFoundError` after install

Make sure you installed in editable mode from the repo root:

```bash
pip install -e ".[dev]"
```

Running `pip install asi-build` from PyPI is not yet supported (pre-release).

---

## Test Failures

### Many tests skipped on first run

This is expected. Several modules check for optional dependencies at import time and skip gracefully if they're missing. Run:

```bash
pip install -e ".[dev]"  # installs all dev extras
python -m pytest tests/ -v 2>&1 | grep SKIP | head -20
```

Each skipped test prints the reason. Install the missing package to un-skip it.

### `AssertionError` in `test_consciousness.py`

Known issue — see [Issue #6](https://github.com/web3guru888/asi-build/issues/6). The IIT Φ computation uses entropy difference instead of the correct TPM-based Φ from Tononi 2014. The test asserts structure, not correctness. Fix in progress.

### `test_safety.py` — formal_verification always passes

Known issue — see [Issue #7](https://github.com/web3guru888/asi-build/issues/7). The Z3 backend is invoked but conclusion symbols are not grounded to the input proposition set, so Z3 always proves `True`. This is a bug, not a feature.

### `test_homomorphic.py` — NTT produces wrong ciphertext

Known issue — see [Issue #8](https://github.com/web3guru888/asi-build/issues/8). Multi-modulus NTT uses mismatched primitive roots across moduli. The result is wrong but the test only checks shapes. Fix requires selecting co-prime moduli with consistent NTT-friendly roots.

---

## Common Runtime Errors

### `BlackboardEntryError: entry already exists`

The Cognitive Blackboard rejects duplicate entries by default. If you're re-running a script without restarting the process, either:

1. Clear the entry first: `blackboard.delete_entry(key)`
2. Use `update=True` in the put call (if the API supports it — check the module)
3. Create a fresh `CognitiveBlackboard` instance for each test run

### `EventBus: no subscribers for event type X`

This is a warning, not an error. It means you published an event but nothing is listening. Register a subscriber before publishing:

```python
from asi_build.integration.event_bus import EventBus

bus = EventBus()
bus.subscribe("my_event", lambda e: print(e))
bus.publish("my_event", {"data": "hello"})
```

### `RingsSDKError: connection refused`

The Rings Network module requires a running Rings node endpoint. In tests, mock the transport layer:

```python
from unittest.mock import patch, MagicMock

with patch('asi_build.rings.client.RingsClient._connect') as mock_connect:
    mock_connect.return_value = MagicMock()
    # run your code
```

See `tests/test_rings_*.py` for full mock patterns.

---

## Development Workflow

### CI fails on my branch but tests pass locally

Check Python version. CI runs on 3.10, 3.11, and 3.12. A common cause is f-string syntax only supported in newer Pythons, or a package that behaves differently across versions.

Run locally with multiple versions using pyenv:

```bash
pyenv install 3.10.14
pyenv local 3.10.14
python -m pytest tests/ -q
```

### How do I add a new module?

1. Create `src/asi_build/your_module/` with `__init__.py`
2. Add your implementation files
3. Create `tests/test_your_module.py` (minimum: smoke test that the module imports and instantiates)
4. Add your module to the table in [Module Index](https://github.com/web3guru888/asi-build/wiki/Module-Index)
5. Open a PR — see [Contributing](https://github.com/web3guru888/asi-build/wiki/Contributing)

### Tests are slow — how to run a subset

```bash
# Run only rings tests
python -m pytest tests/test_rings_*.py -v

# Run one test file
python -m pytest tests/test_consciousness.py -v

# Run tests matching a pattern
python -m pytest tests/ -k "blackboard" -v

# Skip slow tests (if marked)
python -m pytest tests/ -m "not slow" -q
```

---

## Getting Help

- **Q&A Discussions**: Post in [Discussions → Q&A](https://github.com/web3guru888/asi-build/discussions/categories/q-a) — check [Discussion #16](https://github.com/web3guru888/asi-build/discussions/16) for existing FAQ
- **Open an Issue**: For bugs, use the issue tracker with reproduction steps
- **Wiki**: Browse the [full wiki](https://github.com/web3guru888/asi-build/wiki) for architecture and module docs

When reporting a bug, include:
1. Python version (`python --version`)
2. ASI:BUILD version / commit hash (`git rev-parse HEAD`)
3. Full traceback
4. Minimal reproduction case
