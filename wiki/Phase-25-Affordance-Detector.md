# Phase 25.2 — AffordanceDetector

> Gibson-inspired affordance detection and object-action reasoning engine.

| Property | Value |
|----------|-------|
| **Phase** | 25.2 |
| **Component** | `AffordanceDetector` |
| **Type** | Protocol + `NeuralAffordanceDetector` impl |
| **Issue** | [#563](https://github.com/web3guru888/asi-build/issues/563) |
| **Depends on** | SensorFusion 25.1, WorldModel 13.1, GoalDecomposer 10.2 |
| **Consumers** | MotorPlanner 25.3, EmbodiedOrchestrator 25.5 |

## Theoretical Basis

Based on Gibson's (1979) ecological psychology — affordances are action possibilities that exist in the relationship between an agent and its environment. Objects afford actions based on their properties relative to the agent's capabilities.

## Data Structures

### Enums

- `AffordanceType` — GRASP, PUSH, PULL, LIFT, PLACE, USE_TOOL, NAVIGATE, OBSERVE
- `ConfidenceLevel` — HIGH (>0.8), MEDIUM (0.4–0.8), LOW (<0.4)

### Frozen Dataclasses

- `Affordance(object_id, action, preconditions, effects, confidence, energy_cost, risk)`
- `ObjectState(object_id, position, orientation, properties, bounding_box)`
- `AffordanceConfig(min_confidence, max_affordances_per_object, physics_sim_steps, enable_tool_use, cache_ttl_ms)`

## Protocol

```python
@runtime_checkable
class AffordanceDetector(Protocol):
    async def detect_affordances(self, state: FusedState) -> Sequence[Affordance]: ...
    async def evaluate_action(self, affordance: Affordance) -> float: ...
    async def get_object_affordances(self, object_id: str) -> Sequence[Affordance]: ...
    async def update_model(self, observation: ObjectState, outcome: bool) -> None: ...
```

## Architecture

```
FusedState 25.1 ──→ Feature Extraction ──→ Affordance Scoring (MLP)
                          │                       │
                    ObjectState 13.1         Physics Sim
                          │                       │
                    Object Properties ──→ Precondition Check
                          │                       │
                    Tool-Use Graph ──→ Compositional Reasoning
                          │                       │
                          └───────────────→ Affordance Set ──→ MotorPlanner 25.3
```

## Key Algorithms

- **Neural scoring**: MLP over (object_embedding, action_type) → confidence
- **Physics verification**: N-step simulation for precondition checking
- **Tool-use reasoning**: compositional capability extension
- **Bayesian update**: P(aff|outcome) ∝ P(outcome|aff)·P(aff)
- **LRU cache**: TTL-based caching for unchanged scenes

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `affordance_detect_total` | Counter | Detection runs |
| `affordance_detect_seconds` | Histogram | Detection latency |
| `affordance_count` | Gauge | Detected affordances |
| `affordance_confidence_mean` | Gauge | Mean confidence |
| `affordance_model_updates_total` | Counter | Learning updates |

## Test Targets (12)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_affordance_frozen` | Immutability |
| 2 | `test_object_state_frozen` | Immutability |
| 3 | `test_detect_affordances_basic` | Basic detection |
| 4 | `test_detect_affordances_empty_scene` | Empty scene |
| 5 | `test_evaluate_action_confidence` | Action eval |
| 6 | `test_get_object_affordances_cached` | Cache hit |
| 7 | `test_update_model_increases_confidence` | Positive feedback |
| 8 | `test_update_model_decreases_confidence` | Negative feedback |
| 9 | `test_tool_use_affordance` | Tool reasoning |
| 10 | `test_physics_sim_precondition_check` | Simulation |
| 11 | `test_null_affordance_detector_noop` | Null impl |
| 12 | `test_factory_returns_neural` | Factory |

## References

- Gibson (1979) — "The Ecological Approach to Visual Perception"
- Montesano et al. (2008) — "Learning object affordances"
- Zech et al. (2017) — "Computational models of affordance in robotics"

---

### Phase 25 Sub-phase Tracker

| # | Component | Status |
|---|-----------|--------|
| 25.1 | SensorFusion | 📋 Spec'd |
| 25.2 | AffordanceDetector | 📋 Spec'd |
| 25.3 | MotorPlanner | 📋 Spec'd |
| 25.4 | SpatialReasoner | 📋 Spec'd |
| 25.5 | EmbodiedOrchestrator | 📋 Spec'd |
