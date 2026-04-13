# Phase 25.4 — SpatialReasoner

> Cognitive mapping and spatial reasoning with dual topological-metric representation.

| Property | Value |
|----------|-------|
| **Phase** | 25.4 |
| **Component** | `SpatialReasoner` |
| **Type** | Protocol + `HybridSpatialReasoner` impl |
| **Issue** | [#565](https://github.com/web3guru888/asi-build/issues/565) |
| **Depends on** | SensorFusion 25.1, MotorPlanner 25.3, TemporalGraph 17.1 |
| **Consumers** | EmbodiedOrchestrator 25.5 |

## Theoretical Basis

Based on Tolman's (1948) cognitive map theory and O'Keefe & Nadel's (1978) hippocampal place/grid cell models. Dual representation: topological graph for high-level reasoning and metric occupancy grid for precise navigation.

## Data Structures

### Enums

- `SpatialRelation` — ABOVE, BELOW, LEFT_OF, RIGHT_OF, IN_FRONT, BEHIND, INSIDE, NEAR, FAR, ADJACENT
- `ReferenceFrame` — EGOCENTRIC, ALLOCENTRIC, OBJECT_RELATIVE

### Frozen Dataclasses

- `SpatialNode(node_id, position, label, properties)`
- `SpatialEdge(source_id, target_id, relation, distance, traversable)`
- `SpatialMap(nodes, edges, landmarks, reference_frame, resolution, bounds)`
- `SpatialConfig(default_frame, grid_resolution, max_nodes, pathfinding_algorithm, mental_rotation_steps)`

## Protocol

```python
@runtime_checkable
class SpatialReasoner(Protocol):
    async def reason_spatial(self, query: str, context: SpatialMap) -> Sequence[SpatialRelation]: ...
    async def find_path(self, start: str, goal: str) -> Sequence[SpatialNode]: ...
    async def transform_frame(self, node: SpatialNode, target_frame: ReferenceFrame) -> SpatialNode: ...
    async def build_map(self, observations: Sequence[FusedState]) -> SpatialMap: ...
    async def query_region(self, center: tuple[float, float, float], radius: float) -> Sequence[SpatialNode]: ...
    async def mental_rotate(self, map_: SpatialMap, angle_degrees: float, axis: str) -> SpatialMap: ...
```

## Architecture

```
FusedState 25.1 ──→ HybridSpatialReasoner
                     ├─ Topological Graph (networkx)
                     │   ├─ Places / Rooms / Landmarks
                     │   └─ Spatial edges (relations + distances)
                     ├─ Metric Grid (numpy occupancy)
                     │   ├─ Bayesian cell updates
                     │   └─ Fine-grained queries
                     ├─ A* Pathfinding
                     ├─ Frame Transforms (R·p + t)
                     ├─ Mental Rotation (Shepard & Metzler)
                     └─ KD-Tree Spatial Queries
                          │
                          └──→ SpatialMap ──→ MotorPlanner 25.3
                                              EmbodiedOrchestrator 25.5
```

## Key Algorithms

- **A* pathfinding**: f(n) = g(n) + h(n) on topological graph
- **Occupancy grid**: Bayesian update from sensor observations
- **Frame transform**: T_alloc = R·T_ego + t
- **Mental rotation**: Shepard & Metzler angular disparity model
- **KD-tree**: O(log n) nearest-neighbor spatial queries

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `spatial_reason_total` | Counter | Reasoning queries |
| `spatial_reason_seconds` | Histogram | Query latency |
| `spatial_map_nodes` | Gauge | Map node count |
| `spatial_pathfind_length` | Histogram | Path length |
| `spatial_frame_transforms_total` | Counter | Frame transforms |

## Test Targets (12)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_spatial_node_frozen` | Immutability |
| 2 | `test_spatial_map_frozen` | Immutability |
| 3 | `test_find_path_direct` | Direct A* |
| 4 | `test_find_path_obstacle` | Route around |
| 5 | `test_transform_ego_to_alloc` | Frame convert |
| 6 | `test_build_map_from_observations` | Map building |
| 7 | `test_query_region_radius` | Spatial query |
| 8 | `test_mental_rotate_90` | Mental rotation |
| 9 | `test_dual_representation_consistency` | Topo-metric |
| 10 | `test_kd_tree_nearest_neighbor` | Efficient lookup |
| 11 | `test_null_spatial_reasoner_empty` | Null impl |
| 12 | `test_factory_returns_hybrid` | Factory |

## References

- Tolman (1948) — "Cognitive maps in rats and men"
- O'Keefe & Nadel (1978) — "The Hippocampus as a Cognitive Map"
- Shepard & Metzler (1971) — "Mental rotation of three-dimensional objects"
- Hart, Nilsson & Raphael (1968) — "A* algorithm"

---

### Phase 25 Sub-phase Tracker

| # | Component | Status |
|---|-----------|--------|
| 25.1 | SensorFusion | 📋 Spec'd |
| 25.2 | AffordanceDetector | 📋 Spec'd |
| 25.3 | MotorPlanner | 📋 Spec'd |
| 25.4 | SpatialReasoner | 📋 Spec'd |
| 25.5 | EmbodiedOrchestrator | 📋 Spec'd |
