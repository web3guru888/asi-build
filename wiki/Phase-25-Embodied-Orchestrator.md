# Phase 25.5 — EmbodiedOrchestrator

> Unified embodied cognition pipeline — perception-action loops, embodied simulation, grounded language.

| Property | Value |
|----------|-------|
| **Phase** | 25.5 |
| **Component** | `EmbodiedOrchestrator` |
| **Type** | Protocol + `AsyncEmbodiedOrchestrator` impl |
| **Issue** | [#566](https://github.com/web3guru888/asi-build/issues/566) |
| **Depends on** | SensorFusion 25.1, AffordanceDetector 25.2, MotorPlanner 25.3, SpatialReasoner 25.4 |
| **Integrates** | SocialOrchestrator 24.5, CommunicationOrchestrator 19.5, ReasoningOrchestrator 20.5 |

## Theoretical Basis

Capstone component realizing Lakoff & Johnson's (1999) thesis that cognition is fundamentally embodied. Implements Barsalou's (1999) perceptual symbol systems for grounded concept understanding and Brooks' (1991) embodied intelligence paradigm.

## Data Structures

### Enums

- `EmbodiedMode` — PERCEIVE, ACT, SIMULATE, GROUND
- `BodyState` — IDLE, SENSING, PLANNING, EXECUTING, SIMULATING

### Frozen Dataclasses

- `BodySchema(effectors, sensors, joint_limits, current_pose)`
- `EmbodiedContext(sensor_state, affordances, motor_plans, spatial_map, body_schema, mode, timestamp_ms)`
- `SimulationResult(initial_context, final_context, steps, success_probability, side_effects)`
- `EmbodiedConfig(perception_rate_hz, simulation_max_steps, action_timeout_ms, enable_simulation, grounding_strategy)`

## Protocol

```python
@runtime_checkable
class EmbodiedOrchestrator(Protocol):
    async def perceive(self) -> EmbodiedContext: ...
    async def act(self, affordance: Affordance) -> PlanStatus: ...
    async def simulate(self, affordance: Affordance, steps: int) -> SimulationResult: ...
    async def ground_concept(self, concept: str) -> EmbodiedContext: ...
    async def get_body_state(self) -> BodyState: ...
    async def perception_action_loop(self, goal: str) -> PlanStatus: ...
```

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  AsyncEmbodiedOrchestrator                      │
│                                                                │
│  ┌──────────┐   ┌───────────────┐   ┌────────────┐            │
│  │ SensorFsn│──→│AffordanceDet  │──→│MotorPlanner│            │
│  │   25.1   │   │    25.2       │   │   25.3     │            │
│  └──────────┘   └───────────────┘   └────────────┘            │
│       │                                    │                   │
│       │         ┌───────────────┐          │                   │
│       └────────→│SpatialReasoner│←─────────┘                   │
│                 │    25.4       │                               │
│                 └───────────────┘                               │
│                                                                │
│  Perception-Action Loop:                                       │
│  perceive() → detect() → select() → simulate() → act()        │
│       ↑                                          │             │
│       └──────────── feedback ────────────────────┘             │
│                                                                │
│  Grounded Language: concept → perceptual symbols → activation  │
└────────────────────────────────────────────────────────────────┘
         │                    │                    │
    SocialOrch 24.5    CommOrch 19.5       ReasoningOrch 20.5
```

## Perception-Action Loop

```python
while not goal_reached:
    context = await perceive()           # fuse → detect → map
    affordance = select_best(context)    # utility-weighted
    if simulate_first:
        sim = await simulate(aff, N)
        if sim.success_probability < threshold:
            continue
    status = await act(affordance)       # plan → execute
    await update_world_model(status)     # feedback loop
```

## Grounded Language Understanding

Maps abstract concepts to sensorimotor experiences via Barsalou's perceptual symbol systems:
- "heavy" → proprioceptive force memory
- "above" → spatial relation activation
- "grasp" → motor plan simulation

## Error Handling

| Failure | Recovery |
|---------|----------|
| Sensor offline | Degrade confidence |
| Motor collision | Abort + re-plan |
| Simulation timeout | Partial results |
| No affordances | OBSERVE mode |

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `embodied_perceive_total` | Counter | Perception cycles |
| `embodied_act_total` | Counter | Actions executed |
| `embodied_simulate_total` | Counter | Simulations run |
| `embodied_loop_iterations` | Histogram | Loop iterations |
| `embodied_grounding_seconds` | Histogram | Grounding latency |

## Test Targets (12)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_body_schema_frozen` | Immutability |
| 2 | `test_embodied_context_frozen` | Immutability |
| 3 | `test_perceive_returns_context` | Perception |
| 4 | `test_act_executes_motor_plan` | Action |
| 5 | `test_simulate_predicts_outcome` | Forward model |
| 6 | `test_simulate_counterfactual` | Alternative action |
| 7 | `test_ground_concept_spatial` | Grounding |
| 8 | `test_perception_action_loop_converges` | Loop termination |
| 9 | `test_sensor_failure_degradation` | Degradation |
| 10 | `test_motor_failure_replan` | Re-planning |
| 11 | `test_null_embodied_orchestrator_noop` | Null impl |
| 12 | `test_factory_returns_async` | Factory |

## References

- Lakoff & Johnson (1999) — "Philosophy in the Flesh"
- Barsalou (1999) — "Perceptual symbol systems"
- Brooks (1991) — "Intelligence without representation"
- Pfeifer & Scheier (1999) — "Understanding Intelligence"

---

### Phase 25 Sub-phase Tracker

| # | Component | Status |
|---|-----------|--------|
| 25.1 | SensorFusion | 📋 Spec'd |
| 25.2 | AffordanceDetector | 📋 Spec'd |
| 25.3 | MotorPlanner | 📋 Spec'd |
| 25.4 | SpatialReasoner | 📋 Spec'd |
| 25.5 | EmbodiedOrchestrator | 📋 Spec'd |
