# Phase 25.3 — MotorPlanner

> Motion planning and trajectory optimization using RRT*, DMPs, and potential fields.

| Property | Value |
|----------|-------|
| **Phase** | 25.3 |
| **Component** | `MotorPlanner` |
| **Type** | Protocol + `HierarchicalMotorPlanner` impl |
| **Issue** | [#564](https://github.com/web3guru888/asi-build/issues/564) |
| **Depends on** | AffordanceDetector 25.2, PlanExecutor 10.3, DecisionOrchestrator 23.5 |
| **Consumers** | EmbodiedOrchestrator 25.5 |

## Theoretical Basis

Hierarchical motor planning inspired by Brooks' subsumption architecture — layered control from task-level planning to reactive obstacle avoidance. Combines sampling-based planning (RRT*), trajectory optimization, and learned movement primitives (DMPs).

## Data Structures

### Enums

- `PlanningAlgorithm` — RRT_STAR, TRAJECTORY_OPT, DMP, HYBRID
- `PlanStatus` — PENDING, FEASIBLE, INFEASIBLE, EXECUTING, COMPLETED, FAILED

### Frozen Dataclasses

- `Waypoint(position, velocity, timestamp_ms)`
- `MotorPlan(plan_id, actions, trajectory, duration_ms, energy_cost, safety_margin, status)`
- `MotorConfig(algorithm, max_iterations, step_size, goal_tolerance, safety_margin_min, max_velocity, max_acceleration)`

## Protocol

```python
@runtime_checkable
class MotorPlanner(Protocol):
    async def plan_motion(self, start: Waypoint, goal: Waypoint, obstacles: Sequence[ObjectState]) -> MotorPlan: ...
    async def optimize_trajectory(self, plan: MotorPlan) -> MotorPlan: ...
    async def check_feasibility(self, plan: MotorPlan) -> tuple[bool, str]: ...
    async def execute_plan(self, plan: MotorPlan) -> PlanStatus: ...
    async def abort(self) -> None: ...
```

## Architecture

```
Affordance 25.2 ──→ Task Decomposition ──→ Sub-goals
                          │
                    RRT* Path Finding ──→ Raw Path
                          │
                    Trajectory Optimization ──→ Smooth Trajectory
                          │
                    Potential Fields ──→ Reactive Adjustments
                          │
                    DMP Library ──→ Learned Primitives
                          │
                          └──→ MotorPlan ──→ PlanExecutor 10.3
```

## Key Algorithms

- **RRT***: Asymptotically optimal sampling-based planner with rewiring
- **Trajectory optimization**: minimize ∫(τ² + λ·jerk²)dt subject to constraints
- **Inverse kinematics**: Jacobian pseudo-inverse iterative solver
- **DMP**: τ·ẍ = K(g-x) - D·ẋ + f(s), learned forcing function
- **Potential fields**: attractive goal + repulsive obstacles

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `motor_plan_total` | Counter | Plans generated |
| `motor_plan_seconds` | Histogram | Planning latency |
| `motor_plan_feasible_ratio` | Gauge | Feasible ratio |
| `motor_trajectory_length` | Histogram | Trajectory length |
| `motor_plan_replan_total` | Counter | Re-planning events |

## Test Targets (12)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_waypoint_frozen` | Immutability |
| 2 | `test_motor_plan_frozen` | Immutability |
| 3 | `test_plan_motion_straight_line` | Unobstructed |
| 4 | `test_plan_motion_with_obstacles` | Obstacle avoidance |
| 5 | `test_optimize_trajectory_reduces_energy` | Optimization |
| 6 | `test_check_feasibility_valid` | Valid plan |
| 7 | `test_check_feasibility_collision` | Collision detect |
| 8 | `test_rrt_star_convergence` | RRT* finds path |
| 9 | `test_dmp_learned_primitive` | DMP reproduction |
| 10 | `test_abort_stops_execution` | Abort mechanism |
| 11 | `test_null_motor_planner_infeasible` | Null impl |
| 12 | `test_factory_returns_hierarchical` | Factory |

## References

- LaValle (2006) — "Planning Algorithms"
- Ijspeert et al. (2013) — "Dynamical Movement Primitives"
- Khatib (1986) — "Real-time obstacle avoidance"

---

### Phase 25 Sub-phase Tracker

| # | Component | Status |
|---|-----------|--------|
| 25.1 | SensorFusion | 📋 Spec'd |
| 25.2 | AffordanceDetector | 📋 Spec'd |
| 25.3 | MotorPlanner | 📋 Spec'd |
| 25.4 | SpatialReasoner | 📋 Spec'd |
| 25.5 | EmbodiedOrchestrator | 📋 Spec'd |
