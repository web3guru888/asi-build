# Phase 6.5 — Multi-task EWC: TaskRegistry, per-task Fisher matrices, and async-safe task routing

> **Status**: Spec — implementation tracked in issue #255
> **Depends on**: Phase 6.1 (#241), Phase 6.3 (#249), Phase 6.4 (#252)

---

## Motivation

Phase 6.1–6.4 build a complete EWC system for a **single task**: one Fisher matrix captures parameter importance for one reference point $\theta^*$.

Real agents encounter **multiple task contexts**: conversation domains, sensor modalities, skill specialisations. Each requires its own importance anchor:

$$\mathcal{L}_{EWC}^{multi} = \mathcal{L}_{task_k} + \sum_{j \neq k} \frac{\lambda}{2} \sum_i F^{(j)}_i (\theta_i - \theta^{*(j)}_i)^2$$

Without per-task routing, the agent either:
1. Overwrites $F^{(A)}$ when learning task B (silently forgets A), or
2. Applies $F^{(A)}$ weights to task B updates (wrong anchor → wrong regularisation)

Phase 6.5 solves this with three components: `TaskRegistry`, `MultiTaskEWCRegulariser`, and `TaskContextManager`.

---

## Architecture diagram

```
CognitiveCycle tick
│
├── TaskContextManager.active_task("nav")    ← sets ContextVar
│   │
│   ├── FisherAccumulator.step(grad)          ← EMA accumulation for "nav"
│   │
│   └── STDPOnlineLearner.update(pre, post)   ← reads ContextVar → routes
│       │
│       └── MultiTaskEWCRegulariser.penalty_gradient(params, "nav")
│           │
│           └── TaskRegistry.get("nav") → FisherSnapshot
│               └── FisherMatrixBase store
│
└── SLEEP_PHASE
    ├── FisherAccumulator.force_snapshot()
    └── TaskRegistry.register("nav", snapshot)
```

---

## Component: `TaskEntry` and `TaskRegistry`

**Module**: `asi/phase6/learning/task_registry.py`

```python
from __future__ import annotations
import asyncio
import collections
import heapq
import time
from contextvars import ContextVar
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, Literal

import numpy as np
import numpy.typing as npt

from .fisher import FisherMatrixBase, FisherSnapshot

_active_task_id: ContextVar[str] = ContextVar("active_task_id", default="default")


@dataclass
class TaskEntry:
    task_id: str
    fisher_snapshot: FisherSnapshot
    registered_at: float = field(default_factory=time.monotonic)
    last_used_at: float = field(default_factory=time.monotonic)
    priority: float = 1.0


class TaskRegistry:
    def __init__(
        self,
        store: FisherMatrixBase,
        max_tasks: int = 32,
        eviction_policy: Literal["lru", "priority", "fifo"] = "lru",
    ) -> None:
        self._store = store
        self._max_tasks = max_tasks
        self._policy = eviction_policy
        self._entries: dict[str, TaskEntry] = {}
        self._lru_order: collections.OrderedDict[str, None] = collections.OrderedDict()
        self._lock = asyncio.Lock()

    async def register(
        self,
        task_id: str,
        snapshot: FisherSnapshot,
        *,
        force: bool = False,
    ) -> None:
        async with self._lock:
            if task_id in self._entries and not force:
                return
            if len(self._entries) >= self._max_tasks:
                await self._evict_one(reason="budget")
            entry = TaskEntry(task_id=task_id, fisher_snapshot=snapshot)
            self._entries[task_id] = entry
            self._lru_order[task_id] = None

    async def get(self, task_id: str) -> FisherSnapshot | None:
        async with self._lock:
            entry = self._entries.get(task_id)
            if entry is None:
                return None
            entry.last_used_at = time.monotonic()
            self._lru_order.move_to_end(task_id)
            return entry.fisher_snapshot

    async def evict(self, task_id: str) -> None:
        async with self._lock:
            self._entries.pop(task_id, None)
            self._lru_order.pop(task_id, None)

    async def list_tasks(self) -> list[TaskEntry]:
        async with self._lock:
            return list(self._entries.values())

    async def prune(self) -> list[str]:
        evicted: list[str] = []
        async with self._lock:
            while len(self._entries) > self._max_tasks:
                task_id = self._select_eviction_victim()
                self._entries.pop(task_id, None)
                self._lru_order.pop(task_id, None)
                evicted.append(task_id)
        return evicted

    def _select_eviction_victim(self) -> str:
        if self._policy == "lru":
            return next(iter(self._lru_order))
        elif self._policy == "fifo":
            return min(self._entries.values(), key=lambda e: e.registered_at).task_id
        elif self._policy == "priority":
            return min(self._entries.values(), key=lambda e: (e.priority, e.registered_at)).task_id
        else:
            from typing import assert_never
            assert_never(self._policy)

    async def _evict_one(self, reason: str = "budget") -> None:
        victim = self._select_eviction_victim()
        self._entries.pop(victim, None)
        self._lru_order.pop(victim, None)
```

---

## Component: `TaskContextManager`

```python
class TaskContextManager:
    def __init__(self, registry: TaskRegistry) -> None:
        self._registry = registry

    @contextmanager
    def active_task(self, task_id: str) -> Generator[None, None, None]:
        """
        Sets the active task_id in contextvars for the duration of the block.
        Safe for asyncio — each Task inherits a copy of the parent context.
        """
        token = _active_task_id.set(task_id)
        try:
            yield
        finally:
            _active_task_id.reset(token)

    @staticmethod
    def current_task_id() -> str:
        return _active_task_id.get()
```

### Why `contextvars` and not thread-locals

| Mechanism | asyncio-safe | Inherited by subtasks | Reset on exit |
|-----------|-------------|----------------------|---------------|
| `threading.local` | ❌ | ❌ | manual |
| `contextvars.ContextVar` | ✅ | ✅ (copy-on-enter) | ✅ (token.reset) |

Each `asyncio.Task` gets a copy of the parent's context at creation. Modifications inside the child do not propagate back. This means parallel ticks cannot cross-contaminate task_id values.

---

## Component: `MultiTaskEWCRegulariser`

**Module**: `asi/phase6/learning/ewc_multitask.py`

```python
from __future__ import annotations

import numpy as np
import numpy.typing as npt

from .ewc import EWCRegulariser
from .task_registry import TaskRegistry, _active_task_id

_MAX_TASK_LABELS = 16
_seen_task_labels: set[str] = set()


def _safe_task_label(task_id: str) -> str:
    if task_id in _seen_task_labels or len(_seen_task_labels) < _MAX_TASK_LABELS:
        _seen_task_labels.add(task_id)
        return task_id
    return "other"


class MultiTaskEWCRegulariser(EWCRegulariser):
    def __init__(
        self,
        registry: TaskRegistry,
        ewc_lambda: float = 400.0,
        clip_norm: float = 1.0,
    ) -> None:
        self._registry = registry
        self._ewc_lambda = ewc_lambda
        self._clip_norm = clip_norm

    async def penalty_gradient(
        self,
        params: npt.NDArray[np.float32],
        task_id: str | None = None,
    ) -> npt.NDArray[np.float32]:
        effective_task_id = task_id if task_id is not None else _active_task_id.get()
        snapshot = await self._registry.get(effective_task_id)
        if snapshot is None:
            # No prior registered for this task — zero penalty (free learning)
            return np.zeros_like(params)

        importance = snapshot.fisher_diagonal
        anchor = snapshot.reference_params
        grad = self._ewc_lambda * importance * (params - anchor)

        norm = float(np.linalg.norm(grad))
        if norm > self._clip_norm:
            grad = grad * (self._clip_norm / norm)

        # Prometheus (label cardinality guard)
        label = _safe_task_label(effective_task_id)
        # _PENALTY_GRADIENT_SECONDS.labels(task_id=label).observe(elapsed)  # add timing wrapper
        return grad.astype(np.float32)
```

---

## Factory: `build_multitask_ewc()`

```python
def build_multitask_ewc(
    store: FisherMatrixBase,
    *,
    max_tasks: int = 32,
    eviction_policy: str = "lru",
    ewc_lambda: float = 400.0,
    clip_norm: float = 1.0,
) -> tuple[TaskRegistry, MultiTaskEWCRegulariser, TaskContextManager]:
    registry = TaskRegistry(store, max_tasks=max_tasks, eviction_policy=eviction_policy)
    regulariser = MultiTaskEWCRegulariser(registry, ewc_lambda=ewc_lambda, clip_norm=clip_norm)
    ctx_manager = TaskContextManager(registry)
    return registry, regulariser, ctx_manager
```

---

## Eviction policy comparison

| Policy | Algorithm | Best for | Complexity |
|--------|-----------|----------|------------|
| `lru` | `OrderedDict.move_to_end` | General — recent tasks likely to recur | O(1) per access |
| `priority` | `min()` over `entry.priority` | Skill hierarchies, core competencies | O(n) per eviction |
| `fifo` | `min()` over `entry.registered_at` | Streaming curricula, non-repeating tasks | O(n) per eviction |

For large registries (`max_tasks > 64`), switch `priority` and `fifo` to a `heapq` for O(log n) eviction.

---

## Prometheus metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_ewc_tasks_registered_total` | Counter | `policy` | Total registrations |
| `asi_ewc_tasks_evicted_total` | Counter | `policy`, `reason` | Evictions (budget / manual) |
| `asi_ewc_active_task_switches_total` | Counter | — | Task context switches per cycle |
| `asi_ewc_penalty_gradient_seconds` | Histogram | `task_id` | Penalty compute latency (≤16 values) |
| `asi_ewc_registry_size` | Gauge | — | Current registered task count |

**Pre-init pattern** (avoid `ValueError: metric already registered`):

```python
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry

_REGISTRY: CollectorRegistry | None = None

def _metrics(registry: CollectorRegistry | None = None) -> None:
    global _REGISTRY
    if _REGISTRY is not None:
        return
    _REGISTRY = registry or CollectorRegistry()
    # ... define counters/gauges/histograms
```

---

## Test targets (12)

| # | Target | Fixture |
|---|--------|---------|
| 1 | `test_task_registry_register_and_get` | `InMemoryFisherStore` |
| 2 | `test_task_registry_evict_lru` | Fill to max+1, assert LRU evicted |
| 3 | `test_task_registry_evict_priority` | Fill to max+1, assert lowest-priority evicted |
| 4 | `test_task_registry_evict_fifo` | Fill to max+1, assert oldest evicted |
| 5 | `test_task_registry_prune_returns_ids` | prune() returns correct list |
| 6 | `test_multitask_regulariser_known_task` | Returns nonzero gradient |
| 7 | `test_multitask_regulariser_unknown_task` | Returns zero vector |
| 8 | `test_multitask_regulariser_prometheus_labels` | 17 tasks → 16 unique + "other" |
| 9 | `test_context_manager_sets_contextvar` | `current_task_id()` returns active task |
| 10 | `test_context_manager_no_leak` | Outer task_id restored on exit |
| 11 | `test_build_multitask_ewc_factory` | Returns 3-tuple of correct types |
| 12 | `test_multitask_end_to_end` | 2 tasks, distinct gradients, context switch |

---

## Implementation order

1. `TaskEntry` dataclass + `TaskRegistry` with LRU eviction
2. FIFO and priority eviction policies + `prune()`
3. `TaskContextManager` using `contextvars.ContextVar`
4. `MultiTaskEWCRegulariser` extending `EWCRegulariser`
5. Prometheus metric pre-init
6. `build_multitask_ewc()` factory
7. `STDPOnlineLearner.update()` reads contextvar when `task_id=None`
8. Tests (12 targets)

---

## Phase 6 component interaction table

| Phase | Component | Interaction with Phase 6.5 |
|-------|-----------|---------------------------|
| 6.1 | `FisherSnapshot`, `EWCRegulariser` | Base classes inherited by Phase 6.5 |
| 6.2 | `FisherMatrixBase`, `Neo4jFisherStore` | Injected into `TaskRegistry` as storage backend |
| 6.3 | `STDPOnlineLearner.update()` | Reads `_active_task_id` ContextVar from Phase 6.5 |
| 6.4 | `FisherAccumulator` | Snapshot produced at SLEEP_PHASE → passed to `TaskRegistry.register()` |

---

## Phase 6 roadmap (complete)

| Sub-phase | Issue | Status |
|-----------|-------|--------|
| 6.1 EWC Foundation | #241 | 🟡 Spec |
| 6.2 Fisher Backends | #245 | 🟡 Spec |
| 6.3 EWCRegulariser Integration | #249 | 🟡 Spec |
| 6.4 Online Fisher Updates | #252 | 🟡 Spec |
| 6.5 Multi-task EWC | #255 | 🟡 **This page** |

→ Phase 7: Meta-learning / few-shot adaptation — see discussion #258
