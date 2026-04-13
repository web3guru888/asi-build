# Phase 10.2 — GoalDecomposer

Pluggable STRIPS-lite sub-task planner for ASI:BUILD. `GoalDecomposer` converts a `Goal` from `GoalRegistry` into a validated DAG of `SubTask` nodes (`TaskGraph`) and dispatches each sub-task onto the `FederatedTaskRouter` for distributed execution.

> **Status**: 🟡 Spec complete — Issue #323  
> **Depends on**: Phase 10.1 GoalRegistry (#319) · Phase 9.3 FederatedTaskRouter (#306)  
> **Discussions**: #324 (Show & Tell) · #325 (Q&A) · #322 (Phase 10.3 Ideas)

---

## Table of Contents

1. [Motivation](#motivation)
2. [Data Model](#data-model)
3. [Decomposition Strategies](#decomposition-strategies)
4. [DAG Validation](#dag-validation)
5. [Protocol — GoalDecomposer](#protocol--goaldecomposer)
6. [Concrete Implementation](#concrete-implementation--inmemorygoaldecomposer)
7. [Factory](#factory)
8. [CognitiveCycle Integration](#cognitivecycle-integration)
9. [Prometheus Metrics](#prometheus-metrics)
10. [mypy Compliance](#mypy-compliance)
11. [Test Targets](#test-targets)
12. [Implementation Order](#14-step-implementation-order)
13. [Phase 10 Roadmap](#phase-10-roadmap)

---

## Motivation

`GoalRegistry` stores *what* should be achieved; `GoalDecomposer` determines *how* to achieve it. It applies a planning strategy to translate a high-level goal (e.g., "produce research report") into a sequence of concrete `SubTask` nodes that the federation can execute in parallel or in order.

The decomposer is the bridge between the intent layer (Phase 10.1) and the execution layer (Phase 9.3 `FederatedTaskRouter`). Phase 10.3 (`GoalTracker`) will consume the resulting `TaskGraph` to monitor progress and feed results back to `GoalRegistry`.

---

## Data Model

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable, Sequence
import uuid, time

class SubTaskStatus(str, Enum):
    PENDING    = "pending"
    DISPATCHED = "dispatched"
    DONE       = "done"
    FAILED     = "failed"

@dataclass(frozen=True)
class SubTask:
    id: str                        # uuid4
    goal_id: str                   # parent goal
    name: str                      # human-readable label
    capability_required: str       # maps to FederatedTaskRouter capability key
    payload: dict                  # opaque executor data
    depends_on: frozenset[str]     # ids of prerequisite SubTasks
    priority: int = 50             # 0–100; inherited from parent Goal
    timeout_ms: int = 30_000

@dataclass(frozen=True)
class TaskGraph:
    goal_id: str
    sub_tasks: tuple[SubTask, ...]     # topological order (roots first)
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    strategy_used: str = "strips_lite"

@dataclass(frozen=True)
class DecomposerSnapshot:
    total_goals_decomposed: int
    total_sub_tasks_emitted: int
    active_decompositions: int
    strategy_hit_counts: dict[str, int]
```

**Frozen-dataclass invariants** (same policy as Phase 9 federation layer):
- All public dataclasses are `frozen=True`
- `SubTask.depends_on` is `frozenset[str]` — never a `list`
- `TaskGraph.sub_tasks` is `tuple[SubTask, ...]` — never a `list`

---

## Decomposition Strategies

```python
@runtime_checkable
class DecompositionStrategy(Protocol):
    name: str
    def decompose(self, goal: "Goal", context: dict) -> TaskGraph: ...
```

### StripsLiteStrategy (default)

Applies backward chaining over a registered `OperatorSchema` library:

```python
@dataclass(frozen=True)
class OperatorSchema:
    name: str
    capability: str
    preconditions: frozenset[str]
    effects: frozenset[str]

class StripsLiteStrategy:
    name = "strips_lite"

    def __init__(self, operator_library: dict[str, OperatorSchema]):
        self._ops = operator_library

    def decompose(self, goal: Goal, context: dict) -> TaskGraph:
        target_effects = set(goal.payload.get("goal_effects", [goal.description]))
        sub_tasks = self._backward_chain(target_effects, set())
        _validate_dag(sub_tasks)
        return TaskGraph(goal_id=goal.id, sub_tasks=tuple(sub_tasks), strategy_used=self.name)

    def _backward_chain(self, effects: set[str], achieved: set[str], depth: int = 0) -> list[SubTask]:
        if depth > 16:
            raise PlanningError("Plan depth exceeded 16")
        result = []
        for effect in effects - achieved:
            op = self._find_operator(effect)
            tid = str(uuid.uuid4())
            deps_tasks = self._backward_chain(op.preconditions, achieved | {effect}, depth + 1)
            result.extend(deps_tasks)
            achieved |= op.effects
            dep_ids = frozenset(t.id for t in deps_tasks if effect in t.payload.get("achieves", []))
            result.append(SubTask(
                id=tid, goal_id="", name=op.name,
                capability_required=op.capability, payload={"achieves": list(op.effects)},
                depends_on=dep_ids,
            ))
        return result
```

### LinearStrategy

Converts `goal.payload["steps"]` into a sequential chain:

```python
class LinearStrategy:
    name = "linear"

    def decompose(self, goal: Goal, context: dict) -> TaskGraph:
        steps = goal.payload.get("steps", [])
        sub_tasks, prev_id = [], None
        for step in steps:
            tid = str(uuid.uuid4())
            sub_tasks.append(SubTask(
                id=tid, goal_id=goal.id, name=step["name"],
                capability_required=step.get("capability", "general"),
                payload=step.get("payload", {}),
                depends_on=frozenset({prev_id}) if prev_id else frozenset(),
                priority=goal.priority,
            ))
            prev_id = tid
        _validate_dag(sub_tasks)
        return TaskGraph(goal_id=goal.id, sub_tasks=tuple(sub_tasks), strategy_used=self.name)
```

### ParallelStrategy

Fan-out: all sub-tasks have empty `depends_on` and run concurrently:

```python
class ParallelStrategy:
    name = "parallel"

    def decompose(self, goal: Goal, context: dict) -> TaskGraph:
        items = goal.payload.get("parallel_steps", [])
        sub_tasks = [
            SubTask(
                id=str(uuid.uuid4()), goal_id=goal.id, name=item["name"],
                capability_required=item.get("capability", "general"),
                payload=item.get("payload", {}),
                depends_on=frozenset(),
                priority=goal.priority,
            )
            for item in items
        ]
        return TaskGraph(goal_id=goal.id, sub_tasks=tuple(sub_tasks), strategy_used=self.name)
```

Strategy selection guide:

| Strategy | Use when | Dependencies |
|----------|----------|--------------|
| `strips_lite` | Symbolic preconditions/effects; true dependency planning | Yes — from operator library |
| `linear` | Steps already ordered; each depends on previous | Linear chain |
| `parallel` | All sub-tasks are independent; maximise throughput | None |

---

## DAG Validation

Every strategy calls `_validate_dag()` before returning a `TaskGraph`:

```python
def _validate_dag(sub_tasks: Sequence[SubTask]) -> None:
    """DFS cycle detection — O(V + E). Raises ValueError on cycle."""
    id_set = {st.id for st in sub_tasks}
    adj = {st.id: set(st.depends_on) & id_set for st in sub_tasks}
    visited, in_stack = set(), set()

    def dfs(node: str) -> None:
        if node in in_stack:
            CYCLE_ERRORS.inc()
            raise ValueError(f"Cycle detected at sub-task {node!r}")
        if node in visited:
            return
        in_stack.add(node)
        for dep in adj[node]:
            dfs(dep)
        in_stack.discard(node)
        visited.add(node)

    for node in adj:
        dfs(node)
```

---

## Protocol — `GoalDecomposer`

```python
@runtime_checkable
class GoalDecomposer(Protocol):
    async def decompose(self, goal_id: str) -> TaskGraph: ...
    async def dispatch(self, graph: TaskGraph) -> None: ...
    async def get_graph(self, goal_id: str) -> TaskGraph | None: ...
    def snapshot(self) -> DecomposerSnapshot: ...
```

---

## Concrete Implementation — `InMemoryGoalDecomposer`

```python
import asyncio

class InMemoryGoalDecomposer:
    def __init__(
        self,
        registry: GoalRegistry,
        router: FederatedTaskRouter,
        strategy: DecompositionStrategy | None = None,
        *,
        max_graphs: int = 1000,
    ):
        self._registry = registry
        self._router = router
        self._strategy = strategy or StripsLiteStrategy({})
        self._graphs: dict[str, TaskGraph] = {}
        self._lock = asyncio.Lock()
        self._total_decomposed = 0
        self._total_emitted = 0
        self._strategy_hits: dict[str, int] = {}
        self._max_graphs = max_graphs

    async def decompose(self, goal_id: str) -> TaskGraph:
        async with self._lock:
            goal = await self._registry.get(goal_id)
            if goal is None:
                raise KeyError(f"Goal {goal_id!r} not found")
            ctx = {"registered_goals": await self._registry.list()}
            graph = self._strategy.decompose(goal, ctx)
            if len(self._graphs) >= self._max_graphs:
                del self._graphs[next(iter(self._graphs))]
            self._graphs[goal_id] = graph
            self._total_decomposed += 1
            self._strategy_hits[self._strategy.name] = (
                self._strategy_hits.get(self._strategy.name, 0) + 1
            )
            DECOMPOSER_TOTAL.labels(strategy=self._strategy.name).inc()
            return graph

    async def dispatch(self, graph: TaskGraph) -> None:
        for sub_task in graph.sub_tasks:
            env = TaskEnvelope(
                task_id=sub_task.id,
                required_caps=frozenset({sub_task.capability_required}),
                payload=sub_task.payload,
                priority=sub_task.priority,
                timeout_ms=sub_task.timeout_ms,
            )
            await self._router.route(env)
        async with self._lock:
            self._total_emitted += len(graph.sub_tasks)
        SUBTASKS_DISPATCHED.labels(goal_id=graph.goal_id).inc(len(graph.sub_tasks))

    async def get_graph(self, goal_id: str) -> TaskGraph | None:
        async with self._lock:
            return self._graphs.get(goal_id)

    def snapshot(self) -> DecomposerSnapshot:
        return DecomposerSnapshot(
            total_goals_decomposed=self._total_decomposed,
            total_sub_tasks_emitted=self._total_emitted,
            active_decompositions=len(self._graphs),
            strategy_hit_counts=dict(self._strategy_hits),
        )
```

---

## Factory

```python
def build_goal_decomposer(
    registry: GoalRegistry,
    router: FederatedTaskRouter,
    strategy_name: str = "strips_lite",
    operator_library: dict | None = None,
    max_graphs: int = 1000,
) -> GoalDecomposer:
    strategies = {
        "strips_lite": StripsLiteStrategy(operator_library or {}),
        "linear": LinearStrategy(),
        "parallel": ParallelStrategy(),
    }
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy {strategy_name!r}. Valid: {list(strategies)}")
    return InMemoryGoalDecomposer(
        registry=registry,
        router=router,
        strategy=strategies[strategy_name],
        max_graphs=max_graphs,
    )
```

---

## CognitiveCycle Integration

```python
# In CognitiveCycle.tick():
async def _run_goal_decomposition(self) -> None:
    pending = await self._goal_registry.list(status_filter=GoalStatus.PENDING)
    for goal in pending[:5]:       # batch: at most 5 per tick
        graph = await self._goal_decomposer.decompose(goal.id)
        await self._goal_decomposer.dispatch(graph)
        await self._goal_registry.transition(goal.id, GoalStatus.ACTIVE)
```

Full tick pipeline (Phase 10.2):

```
PERCEIVE → REASON → DECIDE → ACT
                     │
                     ├── _run_goal_decomposition()  ← Phase 10.2
                     │      └── decompose(pending goals)
                     │      └── dispatch(task graphs)
                     │      └── transition → ACTIVE
                     │
                     └── _run_goal_tracking()        ← Phase 10.3 (planned)
```

---

## Prometheus Metrics

```python
from prometheus_client import Counter, Gauge, Histogram

DECOMPOSER_TOTAL    = Counter("asi_decomposer_total", "Goals decomposed", ["strategy"])
SUBTASKS_DISPATCHED = Counter("asi_subtasks_dispatched_total", "Sub-tasks dispatched", ["goal_id"])
ACTIVE_GRAPHS       = Gauge("asi_decomposer_active_graphs", "Tracked TaskGraphs")
CYCLE_ERRORS        = Counter("asi_decomposer_cycle_errors_total", "DAG cycle violations")
DECOMPOSER_LATENCY  = Histogram("asi_decomposer_latency_ms", "decompose() latency ms", ["strategy"],
                                buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500])
```

| Metric | Type | PromQL |
|--------|------|--------|
| `asi_decomposer_total` | Counter | `rate(asi_decomposer_total[5m])` |
| `asi_subtasks_dispatched_total` | Counter | `sum(rate(asi_subtasks_dispatched_total[1m]))` |
| `asi_decomposer_active_graphs` | Gauge | `asi_decomposer_active_graphs` |
| `asi_decomposer_cycle_errors_total` | Counter | `increase(asi_decomposer_cycle_errors_total[1h]) > 0` |
| `asi_decomposer_latency_ms` | Histogram | `histogram_quantile(0.99, rate(asi_decomposer_latency_ms_bucket[5m]))` |

---

## mypy Compliance

| Rule | Detail |
|------|--------|
| `--strict` clean | no `Any`, no untyped params |
| `frozenset` deps | `SubTask.depends_on: frozenset[str]` |
| `tuple` sub-tasks | `TaskGraph.sub_tasks: tuple[SubTask, ...]` |
| Protocol runtime-checkable | `isinstance(obj, GoalDecomposer)` works |
| Strategy Protocol | `isinstance(obj, DecompositionStrategy)` works |

---

## Test Targets

| # | Test | What it checks |
|---|------|----------------|
| 1 | `test_strips_lite_single_step` | 1-effect goal → 1 sub-task |
| 2 | `test_linear_chain_ordering` | N steps → N sub-tasks with sequential `depends_on` |
| 3 | `test_parallel_no_dependencies` | parallel goal → all `depends_on = frozenset()` |
| 4 | `test_dag_cycle_detection` | cyclic `depends_on` raises `ValueError` |
| 5 | `test_dispatch_calls_router` | `dispatch()` calls `router.route()` once per sub-task |
| 6 | `test_decompose_missing_goal` | `KeyError` on unknown `goal_id` |
| 7 | `test_max_graphs_eviction` | oldest graph evicted when `max_graphs` exceeded |
| 8 | `test_snapshot_counters` | counters increment correctly after decompose+dispatch |
| 9 | `test_concurrent_decompose` | 50 concurrent `decompose()` calls — no data races |
| 10 | `test_strategy_hit_count` | `strategy_hit_counts` reflects correct strategy name |
| 11 | `test_get_graph_after_decompose` | `get_graph()` returns correct graph for `goal_id` |
| 12 | `test_unknown_strategy_factory` | `build_goal_decomposer()` raises `ValueError` for bad name |

---

## 14-Step Implementation Order

1. `SubTaskStatus` enum
2. `SubTask` frozen dataclass (validate `depends_on` is `frozenset`)
3. `TaskGraph` frozen dataclass
4. `DecomposerSnapshot` frozen dataclass
5. `_validate_dag()` (DFS cycle detection)
6. `DecompositionStrategy` Protocol (`@runtime_checkable`)
7. `LinearStrategy`
8. `ParallelStrategy`
9. `StripsLiteStrategy` (operator library + backward chain)
10. `GoalDecomposer` Protocol
11. `InMemoryGoalDecomposer` (`decompose`, `dispatch`, `get_graph`, `snapshot`)
12. Prometheus pre-init (module-level singletons)
13. `build_goal_decomposer()` factory
14. 12 unit tests (see table above)

---

## Phase 10 Roadmap

| Sub-phase | Component | Status |
|-----------|-----------|--------|
| 10.1 | `GoalRegistry` | ✅ Spec complete — #319 |
| 10.2 | `GoalDecomposer` | 🟡 **This page** |
| 10.3 | `GoalTracker` | 📋 Planned — real-time sub-task progress |
| 10.4 | `ReplanningEngine` | 📋 Planned — dynamic goal revision on failure |
| 10.5 | `AutonomousPlanner` | 📋 Planned — self-generated goals from world state |
