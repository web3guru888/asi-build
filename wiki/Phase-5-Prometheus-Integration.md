# Phase 5 Prometheus Integration

**Issue**: [#220 — Phase 5 Prometheus metrics layer](https://github.com/web3guru888/asi-build/issues/220)  
**Related**: [Phase-5-Rollback-Runbook](Phase-5-Rollback-Runbook) · [Phase-5-Safety-Invariants](Phase-5-Safety-Invariants) · [Health-Monitoring](Health-Monitoring)

---

## Overview

Phase 5 introduces runtime self-modification — STDP weight updates, federated hot-reload, pheromone decay, and consciousness-guided replanning. The Phase 4.3 `/metrics` endpoint (Issue #164) handles infrastructure metrics. This page documents the **Phase 5 Prometheus layer**: 20+ new metrics added by `Phase5MetricsExporter` that cover learning quality, safety invariant status, and rollback state.

All Phase 5 metrics are prefixed `phase5_` to prevent collision with Phase 4 names (`cycle_`, `mesh_`, `agent_`).

---

## Architecture

```
CognitiveCycle tick
  │
  ├── Phase5MetricsCollector (deque windows, amortized P95)
  │       │
  │       └── Phase5MetricsExporter
  │               │
  │               ├── prometheus_client registry
  │               │   ├── Counters
  │               │   ├── Histograms
  │               │   └── Gauges
  │               │
  │               └── FastAPI GET /metrics
  │                     └── prometheus_client.generate_latest()
  │
  └── Phase5RollbackManager
          │
          └── Blackboard writes → Phase5MetricsExporter.on_blackboard_event()
```

`Phase5MetricsExporter` subscribes to the `CognitiveBlackboard` event bus (same pattern as `Phase5MetricsCollector`) and pushes raw observations into the Prometheus registry on every relevant Blackboard write. The `/metrics` endpoint is unchanged from Phase 4.3 — it serves all registered metrics automatically.

---

## Full Metric Reference

### Group 1: Online Learning (6 metrics)

| Metric | Type | Description |
|---|---|---|
| `phase5_stdp_weight_updates_total` | Counter | Accepted STDP WeightDelta events |
| `phase5_stdp_weight_rejections_total` | Counter | WeightDelta events rejected by SafetyBlackboardAdapter |
| `phase5_hot_reload_total{status}` | Counter | MODEL_HOT_RELOAD events; `status`: `success`, `rollback`, `timeout` |
| `phase5_weight_delta_norm` | Histogram | Frobenius norm of accepted WeightDelta per event |
| `phase5_stdp_convergence_ticks` | Gauge | Ticks since last spike burst until weight variance < 0.01 |
| `phase5_safety_gate_rejection_rate_1k` | Gauge | Rolling rejection fraction over last 1000 ticks |

**Histogram buckets** for `phase5_weight_delta_norm`:
```
[0.001, 0.005, 0.01, 0.05, 0.1, 0.3, 0.8, 2.0]
```
Rationale: warning threshold = 0.3, critical = 0.8; the 2.0 bucket prevents `+Inf` bleed at critical thresholds.

### Group 2: Emergent Coordination (5 metrics)

| Metric | Type | Description |
|---|---|---|
| `phase5_active_coalitions` | Gauge | Current live AgentMesh coalition count |
| `phase5_pheromone_signal_strength` | Gauge | Strongest pheromone value on Blackboard at last tick |
| `phase5_role_negotiation_failures_total` | Counter | AgentMesh role conflicts unresolved within 5 ticks |
| `phase5_coalition_size` | Histogram | Agents per coalition at formation time |
| `phase5_pheromone_decay_lag_ms` | Histogram | Time between pheromone deposit and first decay tick |

**Histogram buckets** for `phase5_coalition_size`: `[1, 2, 3, 4, 6, 8, 12, 16]`  
**Histogram buckets** for `phase5_pheromone_decay_lag_ms`: `[1, 5, 10, 50, 100, 500]`

### Group 3: Persistent Memory (6 metrics)

| Metric | Type | Description |
|---|---|---|
| `phase5_kg_writes_total{tier}` | Counter | KG writes by tier: `hot`, `warm`, `cold` |
| `phase5_kg_conflicts_total` | Counter | Temporal contradictions detected in KG |
| `phase5_consolidation_runs_total{status}` | Counter | SLEEP_PHASE consolidation runs; `status`: `success`, `skipped`, `interrupted` |
| `phase5_sleep_phase_active` | Gauge | 1 during SLEEP_PHASE, 0 otherwise |
| `phase5_kg_episode_count` | Gauge | Current episodic memory depth (entry count) |
| `phase5_kg_conflict_resolution_lag_ticks` | Gauge | Ticks to resolve last KG conflict |

### Group 4: Consciousness-Guided Planning (4 metrics)

| Metric | Type | Description |
|---|---|---|
| `phase5_phi_score` | Gauge | Current IIT Φ from ConsciousnessModule |
| `phase5_gwt_broadcast_strength` | Gauge | GWT global workspace broadcast amplitude |
| `phase5_goal_reprioritization_total` | Counter | ConsciousnessPlanner-triggered goal re-rankings |
| `phase5_planner_decision_latency_ms` | Histogram | Time from Φ update to goal re-rank completion |

**Histogram buckets** for `phase5_planner_decision_latency_ms`:
```
[1, 5, 10, 50, 100, 500, 2000]
```
Rationale: CognitiveCycle tick budget = 100ms; warning = 200ms; critical = 500ms; 2000ms captures severe degradation.

### Group 5: Rollback Manager (5 metrics)

| Metric | Type | Description |
|---|---|---|
| `phase5_rollback_active{scenario}` | Gauge | 1 if rollback active for this scenario, 0 otherwise |
| `phase5_rollback_ticks_remaining` | Gauge | Estimated ticks until auto-resume (0 if no rollback) |
| `phase5_rollback_triggered_total{scenario}` | Counter | Cumulative rollback trigger count per scenario |
| `phase5_rollback_recovered_total{scenario}` | Counter | Cumulative successful auto-resume count per scenario |
| `phase5_rollback_manual_interventions_total` | Counter | Times operator manually reset rollback state |

**Scenario label values**: `weight_regression`, `hot_reload_failure`, `kg_conflict_storm`, `planner_divergence`

---

## Implementation

### `Phase5MetricsExporter` skeleton

```python
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from typing import Optional

_ROLLBACK_SCENARIOS = (
    "weight_regression",
    "hot_reload_failure",
    "kg_conflict_storm",
    "planner_divergence",
)

class Phase5MetricsExporter:
    """
    Prometheus bridge for Phase 5 Blackboard events.
    Inject `registry` in tests to avoid duplicate-registration errors.
    """

    def __init__(
        self,
        blackboard: "CognitiveBlackboard",
        registry: Optional[CollectorRegistry] = None,
    ):
        import prometheus_client
        self._bb = blackboard
        self._r = registry or prometheus_client.REGISTRY
        self._setup_metrics()
        self._pre_initialize_labels()

    def _setup_metrics(self):
        r = self._r
        self.weight_updates = Counter(
            "phase5_stdp_weight_updates_total",
            "Accepted STDP WeightDelta events", registry=r,
        )
        self.weight_rejections = Counter(
            "phase5_stdp_weight_rejections_total",
            "WeightDelta events rejected by safety gate", registry=r,
        )
        self.hot_reload = Counter(
            "phase5_hot_reload_total",
            "MODEL_HOT_RELOAD events",
            labelnames=["status"], registry=r,
        )
        self.weight_delta_norm = Histogram(
            "phase5_weight_delta_norm",
            "Frobenius norm of accepted WeightDelta",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.3, 0.8, 2.0], registry=r,
        )
        self.rollback_active = Gauge(
            "phase5_rollback_active",
            "1 if rollback active for this scenario",
            labelnames=["scenario"], registry=r,
        )
        self.rollback_ticks_remaining = Gauge(
            "phase5_rollback_ticks_remaining",
            "Ticks until auto-resume (0 if no rollback active)", registry=r,
        )
        self.rollback_triggered = Counter(
            "phase5_rollback_triggered_total",
            "Cumulative rollback trigger count",
            labelnames=["scenario"], registry=r,
        )
        self.rollback_recovered = Counter(
            "phase5_rollback_recovered_total",
            "Cumulative auto-resume success count",
            labelnames=["scenario"], registry=r,
        )
        self.phi_score = Gauge(
            "phase5_phi_score",
            "Current IIT Phi from ConsciousnessModule", registry=r,
        )
        self.sleep_phase_active = Gauge(
            "phase5_sleep_phase_active",
            "1 during SLEEP_PHASE, 0 otherwise", registry=r,
        )
        self.planner_latency = Histogram(
            "phase5_planner_decision_latency_ms",
            "Time from Phi update to goal re-rank completion (ms)",
            buckets=[1, 5, 10, 50, 100, 500, 2000], registry=r,
        )

    def _pre_initialize_labels(self):
        """Ensure all labeled metrics exist before first event — prevents no-data in Prometheus."""
        for scenario in _ROLLBACK_SCENARIOS:
            self.rollback_active.labels(scenario=scenario).set(0)
            self.rollback_triggered.labels(scenario=scenario)
            self.rollback_recovered.labels(scenario=scenario)
        for status in ("success", "rollback", "timeout"):
            self.hot_reload.labels(status=status)

    async def on_blackboard_event(self, event: "BlackboardEvent") -> None:
        key = event.key
        meta = event.metadata or {}

        if key.startswith("stdp.weight_delta"):
            if meta.get("accepted"):
                self.weight_updates.inc()
                if "norm" in meta:
                    self.weight_delta_norm.observe(meta["norm"])
            else:
                self.weight_rejections.inc()

        elif key == "phase5.hot_reload.status":
            status = event.value  # "success" | "rollback" | "timeout"
            self.hot_reload.labels(status=status).inc()

        elif key == "phase5.rollback.active":
            for scenario, active in event.value.items():
                self.rollback_active.labels(scenario=scenario).set(1 if active else 0)
            if "ticks_remaining" in event.value:
                self.rollback_ticks_remaining.set(event.value["ticks_remaining"])

        elif key == "consciousness.phi":
            self.phi_score.set(event.value)

        elif key == "cycle.sleep_phase.active":
            self.sleep_phase_active.set(1 if event.value else 0)
```

### Wiring into CognitiveCycle startup

```python
# In CognitiveCycle.__init__() or startup()
from asi_build.phase5.metrics_exporter import Phase5MetricsExporter

self._phase5_exporter = Phase5MetricsExporter(self._blackboard)
self._blackboard.subscribe(self._phase5_exporter.on_blackboard_event)
```

No new FastAPI route needed — `prometheus_client.REGISTRY` is served by the existing `/metrics` endpoint from Phase 4.3.

---

## Test Isolation

```python
# conftest.py
import pytest
from prometheus_client import CollectorRegistry

@pytest.fixture
def prometheus_registry():
    """Fresh registry per test — no duplicate-registration errors."""
    return CollectorRegistry()

@pytest.fixture
def phase5_exporter(mock_blackboard, prometheus_registry):
    from asi_build.phase5.metrics_exporter import Phase5MetricsExporter
    return Phase5MetricsExporter(mock_blackboard, registry=prometheus_registry)
```

---

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| No `registry=` in tests | `ValueError: Duplicated timeseries` | Inject `CollectorRegistry()` per test |
| Counter for rollback state | Negative delta error or wrong semantics | Use `Gauge` for binary on/off state |
| Missing upper histogram bucket | P95 returns `+Inf` at critical threshold | Add bucket at 2× critical value |
| Labels not pre-initialized | Alert rule returns no-data (not 0) | Call `_pre_initialize_labels()` in `__init__` |

See also: [Discussion #223 — Prometheus pitfalls Q&A](https://github.com/web3guru888/asi-build/discussions/223)

---

## Grafana Dashboard

See [Discussion #222](https://github.com/web3guru888/asi-build/discussions/222) for layout options. The planned template (`docs/grafana/phase5.json`) uses a four-row layout:

| Row | Content |
|---|---|
| Alert header | `phase5_rollback_active` for all scenarios |
| Row 1 | Online Learning: delta norm P95, hot-reload rate, rejection rate |
| Row 2 | Emergent Coordination: coalitions, pheromone strength, coalition size |
| Row 3 | Persistent Memory: KG write tiers, sleep-phase timeline, conflict rate |
| Row 4 | Rollback Manager: active scenarios table, ticks remaining, recovery count |

---

## Acceptance Criteria

- [ ] `Phase5MetricsExporter` initialises all 20+ metrics without collision with Phase 4 names
- [ ] Weight delta counter increments on every `WEIGHT_DELTA_ACCEPTED` Blackboard key write
- [ ] Weight rejection counter increments on every `WEIGHT_DELTA_REJECTED` key write
- [ ] `phase5_rollback_active{scenario}` goes to 1 within 1 tick of `Phase5RollbackManager` opening that circuit
- [ ] All histogram buckets cover realistic Phase 5 operating ranges (validated by integration test)
- [ ] `/metrics` scrape returns all Phase 5 metrics when `Phase5MetricsExporter` is running
- [ ] Metrics survive a `Phase5RollbackManager` reset without double-registration errors
- [ ] Grafana dashboard JSON template added to `docs/grafana/phase5.json`

---

## Related Pages

- [Phase-5-Rollback-Runbook](Phase-5-Rollback-Runbook)
- [Phase-5-Safety-Invariants](Phase-5-Safety-Invariants)
- [Health-Monitoring](Health-Monitoring)
- [Multi-Agent-Orchestration](Multi-Agent-Orchestration)
- [Roadmap](Roadmap)
