# Phase 5 Integration Tests

This page documents the integration test strategy for Phase 5 — covering the full `CognitiveCycle` pipeline from `PERCEPTION` through `LEARNING`, `INTEGRATION`, `REFLECTION`, `ACTION`, and the conditional `SLEEP_PHASE`.

---

## Test layers

Phase 5 tests are organised into four layers, from fastest to slowest:

| Layer | Scope | Duration | Requires |
|---|---|---|---|
| 1 — Pure unit | Enum values, dataclass fields | < 10ms | Nothing |
| 2 — Async unit | Component logic with mocked I/O | < 500ms | pytest-asyncio |
| 3 — Prometheus isolation | Metric cardinality, label pre-init | < 200ms | prometheus_client |
| 4 — Full integration | End-to-end cycle, real Blackboard | 1-30s | Docker Compose |

---

## Layer 1 — Pure unit tests

No fixtures, no mocking. Tests that validate deterministic properties of enums, dataclasses, and pure functions.

### CyclePhase enum (Issue #235)

```python
# tests/unit/test_cognitive_cycle_phases.py

def test_cycle_phase_learning_value():
    assert CyclePhase.LEARNING == "learning"
    assert CyclePhase.LEARNING.value == "learning"

def test_cycle_phase_sleep_phase_value():
    assert CyclePhase.SLEEP_PHASE == "sleep_phase"
    assert CyclePhase.SLEEP_PHASE.value == "sleep_phase"

def test_cycle_phase_str_coercion():
    assert CyclePhase("learning") is CyclePhase.LEARNING
    assert CyclePhase("sleep_phase") is CyclePhase.SLEEP_PHASE

def test_cycle_phase_ordering():
    phases = list(CyclePhase)
    assert phases.index(CyclePhase.SLEEP_PHASE) == len(phases) - 1
    assert phases.index(CyclePhase.LEARNING) < phases.index(CyclePhase.INTEGRATION)

def test_cycle_phase_prometheus_label():
    label = CyclePhase.LEARNING.value
    assert isinstance(label, str)
    assert label == "learning"

def test_cycle_phase_blackboard_namespace():
    key = f"{CyclePhase.LEARNING.value}:weight_delta"
    assert key == "learning:weight_delta"

def test_cycle_phase_all_phases_present():
    values = {p.value for p in CyclePhase}
    assert values >= {"perception", "integration", "reflection",
                      "action", "learning", "sleep_phase"}

def test_legacy_phases_unchanged():
    assert CyclePhase.PERCEPTION == "perception"
    assert CyclePhase.INTEGRATION == "integration"
    assert CyclePhase.REFLECTION == "reflection"
    assert CyclePhase.ACTION == "action"
```

---

## Layer 2 — Async unit tests

Use `pytest-asyncio` with `asyncio_mode = "auto"` in `pyproject.toml`. Mock external I/O (Neo4j, Redis) using `unittest.mock.AsyncMock`.

### pyproject.toml configuration

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### STDPOnlineLearner (Issue #181)

```python
# tests/unit/test_stdp_online_learner.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_blackboard():
    bb = AsyncMock()
    bb.read.return_value = {"embedding": [0.1, 0.2, 0.3]}
    return bb

async def test_stdp_produces_positive_delta_for_causal_spike(mock_blackboard):
    """LTP: post fires after pre → positive weight delta."""
    learner = STDPOnlineLearner(blackboard=mock_blackboard, A_plus=0.01, A_minus=0.012)
    delta = await learner.compute_delta(pre_spike_t=10.0, post_spike_t=12.0)
    assert delta.norm > 0

async def test_stdp_produces_negative_delta_for_anti_causal_spike(mock_blackboard):
    """LTD: post fires before pre → negative weight delta."""
    learner = STDPOnlineLearner(blackboard=mock_blackboard, A_plus=0.01, A_minus=0.012)
    delta = await learner.compute_delta(pre_spike_t=12.0, post_spike_t=10.0)
    assert delta.norm < 0

async def test_stdp_delta_respects_max_delta_norm(mock_blackboard):
    """Weight delta must not exceed MAX_DELTA_NORM safety gate."""
    learner = STDPOnlineLearner(blackboard=mock_blackboard)
    delta = await learner.compute_delta(pre_spike_t=0.0, post_spike_t=0.0)
    assert abs(delta.norm) <= MAX_DELTA_NORM
```

### SleepPhaseGuard (Issue #210)

```python
# tests/unit/test_sleep_phase_guard.py

def test_sleep_phase_guard_triggers_at_interval():
    guard = SleepPhaseGuard(interval=3)
    results = [guard.should_sleep(i) for i in range(10)]
    # Should be True at tick 3, 6, 9
    assert results == [False, False, False, True, False, False, True, False, False, True]

def test_sleep_phase_guard_interval_1_always_sleeps():
    guard = SleepPhaseGuard(interval=1)
    assert all(guard.should_sleep(i) for i in range(5))
```

---

## Layer 3 — Prometheus isolation tests

The global `prometheus_client.REGISTRY` causes `ValueError: Duplicated timeseries` when tests run in the same process. Always use a per-test isolated registry.

### conftest.py fixture

```python
# tests/conftest.py
import pytest
from prometheus_client import CollectorRegistry

@pytest.fixture
def prometheus_registry():
    """Isolated Prometheus registry — prevents duplicate registration errors."""
    return CollectorRegistry()
```

### Phase5MetricsExporter (Issue #220)

```python
# tests/unit/test_phase5_metrics_exporter.py

def test_phase5_exporter_pre_init_all_phase_labels(prometheus_registry):
    exporter = Phase5MetricsExporter(registry=prometheus_registry)
    exporter.pre_init_labels()
    sample_names = {s.name for m in prometheus_registry.collect() for s in m.samples}
    assert "phase5_cycle_duration_seconds_count" in sample_names

def test_phase5_exporter_label_values_are_plain_strings(prometheus_registry):
    """Labels must be str, not enum repr like 'CyclePhase.LEARNING'."""
    exporter = Phase5MetricsExporter(registry=prometheus_registry)
    exporter.pre_init_labels()
    for metric in prometheus_registry.collect():
        for sample in metric.samples:
            if "phase" in sample.labels:
                assert sample.labels["phase"] in {p.value for p in CyclePhase}
```

> **Implementation note**: `Phase5MetricsExporter.__init__` must accept a `registry=` kwarg, defaulting to `prometheus_client.REGISTRY`. All internal `Gauge`/`Counter`/`Histogram` constructors receive this registry.

---

## Layer 4 — Full-cycle integration tests (Issue #239)

These tests drive `build_phase5_cycle()` end-to-end with a real in-memory Blackboard and mocked Neo4j/Prometheus.

### Full-cycle fixture

```python
# tests/integration/test_phase5_full_cycle.py
import pytest
from unittest.mock import AsyncMock
from prometheus_client import CollectorRegistry

@pytest.fixture
def phase5_cycle(prometheus_registry):
    """Build a full Phase 5 CognitiveCycle with mocked I/O adapters."""
    blackboard   = InMemoryCognitiveBlackboard()
    learner      = STDPOnlineLearner(blackboard=blackboard, A_plus=0.01, A_minus=0.012)
    consolidator = AsyncMock()
    planner      = AsyncMock()
    guard        = SleepPhaseGuard(interval=1)   # sleep every tick for test
    metrics      = Phase5MetricsExporter(registry=prometheus_registry)

    return build_phase5_cycle(
        blackboard=blackboard,
        learner=learner,
        consolidator=consolidator,
        planner=planner,
        sleep_guard=guard,
        metrics=metrics,
    )
```

### Test targets

| Test | Assertion |
|---|---|
| `test_full_phase5_tick_produces_weight_delta` | `bb.read("learning:weight_delta")` is not None after one tick |
| `test_full_phase5_tick_runs_sleep_phase` | `consolidator.consolidate` awaited when `guard.should_sleep()` is True |
| `test_full_phase5_tick_skips_sleep_phase` | `consolidator.consolidate` not called when interval=500 |
| `test_full_phase5_tick_records_prometheus_metrics` | `phase5_cycle_duration_seconds_count` in registry samples |
| `test_full_phase5_tick_graceful_learner_error` | Cycle continues when learner raises `TransientModuleError` |
| `test_full_phase5_tick_propagates_weight_to_planner` | Planner receives WeightDelta from LEARNING phase |
| `test_full_phase5_cycle_phase_order` | Blackboard write timestamps confirm LEARNING < INTEGRATION < ACTION < SLEEP_PHASE |
| `test_build_phase5_cycle_factory_returns_configured_instance` | Factory returns `CognitiveCycle` with all Phase 5 adapters |

---

## Running the tests

```bash
# Layer 1-3 (fast, default)
pytest tests/unit/ -v

# Layer 4 (integration, requires Docker)
pytest tests/integration/ -m integration -v

# All layers (CI)
make test-all
```

---

## Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| No `asyncio_mode = "auto"` | `coroutine never awaited` warning | Set in `pyproject.toml` |
| Global Prometheus registry | `ValueError: Duplicated timeseries` | Use per-test `CollectorRegistry` fixture |
| Real Neo4j in unit tests | 10-30s suite runtime | Mock `AsyncDriver` via `AsyncMock` |
| SleepPhaseGuard counter not reset | Flaky ordering-dependent failures | Instantiate new guard in each fixture |
| Missing `SLEEP_PHASE` pre-init | "no data" gap in Grafana panels | Call `exporter.pre_init_labels()` on startup |

---

## Related

- Issue #235 — `CyclePhase.LEARNING` and `SLEEP_PHASE` enum
- Issue #239 — Full-cycle integration test tracker
- Issue #228 — CI integration test harness (Prometheus scrape, Grafana smoke)
- Issue #220 — Phase5MetricsExporter
- Issue #233 — `build_phase5_cycle()` factory
- Discussion #237 — CyclePhase enum design
- Discussion #238 — Phase 5 test structure Q&A
