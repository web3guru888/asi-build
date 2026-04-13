# Phase 10.1 — GoalRegistry

Typed, thread-safe goal store for the ASI:BUILD autonomous goal management layer. `GoalRegistry` is the entry point for Phase 10 — it provides CRUD operations for goals, enforces a status FSM, and expires goals that miss their deadline.

> **Status**: 🟡 Spec complete — Issue #319  
> **Depends on**: Phase 9 complete (all 5 federation sub-phases)  
> **Discussions**: #320 (Show & Tell) · #321 (Q&A) · #322 (Phase 10.2 Ideas)

---

## Table of Contents

1. [Motivation](#motivation)
2. [Data Model](#data-model)
3. [Status FSM](#status-fsm)
4. [Protocol — `GoalRegistry`](#protocol--goalregistry)
5. [Concrete Implementation](#concrete-implementation--inmemorybgoalregistry)
6. [Factory](#factory)
7. [CognitiveCycle Integration](#cognitivecycle-integration)
8. [Prometheus Metrics](#prometheus-metrics)
9. [mypy Compliance](#mypy-compliance)
10. [Test Targets](#test-targets)
11. [Implementation Order](#14-step-implementation-order)
12. [Phase 10 Roadmap](#phase-10-roadmap)

---

## Motivation

Phase 9 gave ASI:BUILD distributed *execution* — the federation can route tasks, sync state, reach consensus, and monitor cluster health. What it cannot do is decide *which tasks should exist* or *why*.

`GoalRegistry` is the intent layer: a structured store where goals are registered, prioritised, tracked, and expired. Downstream components (`GoalDecomposer`, `GoalTracker`, `ReplanningEngine`) consume the registry to turn high-level intent into actionable sub-tasks.

---

## Data Model

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time

class GoalStatus(str, Enum):
    PENDING    = "pending"     # created, not yet decomposed
    ACTIVE     = "active"      # decomposed, sub-tasks dispatched
    BLOCKED    = "blocked"     # at least one sub-task blocked
    ACHIEVED   = "achieved"    # all sub-tasks completed successfully
    ABANDONED  = "abandoned"   # deadline exceeded or manually cancelled

class GoalPriority(int, Enum):
    CRITICAL = 0   # must complete; blocks CognitiveCycle SLEEP_PHASE
    HIGH     = 1
    NORMAL   = 2
    LOW      = 3
    IDLE     = 4   # background; paused when CRITICAL goal is active

@dataclass(frozen=True)
class Goal:
    goal_id:      str
    description:  str
    priority:     GoalPriority
    created_ms:   int
    deadline_ms:  Optional[int]          # None = no deadline
    tags:         frozenset[str] = field(default_factory=frozenset)
    parent_id:    Optional[str] = None   # for sub-goals created by GoalDecomposer

@dataclass
class GoalRecord:
    goal:         Goal
    status:       GoalStatus = GoalStatus.PENDING
    updated_ms:   int = field(default_factory=lambda: int(time.time() * 1000))
    sub_task_ids: list[str] = field(default_factory=list)
    error:        Optional[str] = None

@dataclass
class RegistrySnapshot:
    total_goals:    int
    by_status:      dict[str, int]   # GoalStatus.value → count
    by_priority:    dict[int, int]   # GoalPriority.value → count
    overdue_count:  int
```

---

## Status FSM

```
PENDING ──► ACTIVE ──► ACHIEVED
               │
          BLOCKED ──► ACTIVE   (re-plan)
               │
PENDING / ACTIVE / BLOCKED ──► ABANDONED
```

| Transition | Method | `valid_from` guard |
|-----------|--------|-------------------|
| PENDING → ACTIVE | `activate()` | `{PENDING}` |
| ACTIVE → BLOCKED | `block()` | `{ACTIVE}` |
| BLOCKED → ACTIVE | `reactivate()` | `{BLOCKED}` |
| ACTIVE → ACHIEVED | `achieve()` | `{ACTIVE}` |
| any → ABANDONED | `abandon()` | `None` (any non-terminal) |
| any → ABANDONED | `evict_expired()` | `None` (deadline passed) |

`InvalidTransitionError` is raised for any disallowed transition.

---

## Protocol — `GoalRegistry`

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class GoalRegistry(Protocol):
    async def register(self, goal: Goal) -> None: ...
    async def get(self, goal_id: str) -> Optional[GoalRecord]: ...
    async def list_by_status(self, status: GoalStatus) -> list[GoalRecord]: ...
    async def list_by_priority(self, max_priority: GoalPriority) -> list[GoalRecord]: ...
    async def activate(self, goal_id: str) -> None: ...
    async def block(self, goal_id: str, reason: str) -> None: ...
    async def reactivate(self, goal_id: str) -> None: ...
    async def achieve(self, goal_id: str) -> None: ...
    async def abandon(self, goal_id: str, reason: str) -> None: ...
    async def evict_expired(self) -> int: ...
    async def snapshot(self) -> RegistrySnapshot: ...
```

---

## Concrete Implementation — `InMemoryGoalRegistry`

### `__init__`

```python
import asyncio

class InMemoryGoalRegistry:
    def __init__(self, *, max_goals: int = 1_000) -> None:
        self._records: dict[str, GoalRecord] = {}
        self._lock = asyncio.Lock()
        self._max_goals = max_goals
        # Prometheus pre-init
        for p in GoalPriority:
            _GOAL_ACTIVE.labels(priority=p.value).set(0)
        for fs in GoalStatus:
            for ts in GoalStatus:
                _GOAL_TRANSITIONS.labels(from_status=fs.value, to_status=ts.value)
```

### `_require()` + `_transition()`

```python
def _require(self, goal_id: str) -> GoalRecord:
    if goal_id not in self._records:
        raise GoalNotFoundError(goal_id)
    return self._records[goal_id]

def _transition(
    self,
    rec: GoalRecord,
    to: GoalStatus,
    valid_from: Optional[set[GoalStatus]],
) -> None:
    if valid_from is not None and rec.status not in valid_from:
        raise InvalidTransitionError(
            f"Cannot transition {rec.goal.goal_id!r} "
            f"from {rec.status!r} to {to!r}"
        )
    old = rec.status
    rec.status = to
    rec.updated_ms = int(time.time() * 1000)
    _GOAL_TRANSITIONS.labels(from_status=old.value, to_status=to.value).inc()
    _GOAL_ACTIVE.labels(priority=rec.goal.priority.value).set(
        sum(1 for r in self._records.values()
            if r.status == GoalStatus.ACTIVE
            and r.goal.priority == rec.goal.priority)
    )
```

### `register()`

```python
async def register(self, goal: Goal) -> None:
    async with self._lock:
        if len(self._records) >= self._max_goals:
            raise RegistryFullError(f"max_goals={self._max_goals} reached")
        if goal.goal_id in self._records:
            raise DuplicateGoalError(goal.goal_id)
        self._records[goal.goal_id] = GoalRecord(goal=goal)
        _GOAL_REGISTERED.inc()
        _GOAL_REGISTRY_SIZE.set(len(self._records))
```

### `evict_expired()`

```python
async def evict_expired(self) -> int:
    now_ms = int(time.time() * 1000)
    count = 0
    async with self._lock:
        for rec in list(self._records.values()):   # snapshot to avoid mutation
            if (rec.goal.deadline_ms is not None
                    and rec.goal.deadline_ms < now_ms
                    and rec.status not in {GoalStatus.ACHIEVED, GoalStatus.ABANDONED}):
                self._transition(rec, GoalStatus.ABANDONED, valid_from=None)
                rec.error = "deadline exceeded"
                count += 1
                _GOALS_OVERDUE.inc()
    return count
```

### `list_by_priority()`

```python
async def list_by_priority(self, max_priority: GoalPriority) -> list[GoalRecord]:
    async with self._lock:
        return sorted(
            [r for r in self._records.values()
             if r.goal.priority.value <= max_priority.value],
            key=lambda r: (r.goal.priority.value, r.goal.created_ms)
        )
```

---

## Factory

```python
def build_goal_registry(*, max_goals: int = 1_000) -> GoalRegistry:
    return InMemoryGoalRegistry(max_goals=max_goals)
```

---

## CognitiveCycle Integration

```python
class CognitiveCycle:
    def __init__(self, ..., goal_registry: Optional[GoalRegistry] = None):
        self._goal_registry = goal_registry

    async def _phase_goal_management(self) -> None:
        if self._goal_registry is None:
            return
        # Evict expired goals each tick
        expired = await self._goal_registry.evict_expired()
        if expired:
            self._blackboard.write("goal.expired_count", expired, source="goal_registry")

        # Gate IDLE goals when CRITICAL is active
        snap = await self._goal_registry.snapshot()
        critical_active = snap.by_status.get("active", 0) > 0 and snap.by_priority.get(0, 0) > 0
        self._blackboard.write("goal.critical_active", critical_active, source="goal_registry")

        # Suspend IDLE goals if circuit is open
        circuit_open = self._blackboard.read("federation.circuit_open") or False
        if circuit_open:
            for rec in await self._goal_registry.list_by_status(GoalStatus.ACTIVE):
                if rec.goal.priority == GoalPriority.IDLE:
                    await self._goal_registry.block(rec.goal.goal_id, "federation circuit open")
```

---

## Prometheus Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `asi_goal_registered_total` | Counter | — |
| `asi_goal_status_transitions_total` | Counter | `from_status`, `to_status` |
| `asi_goal_active` | Gauge | `priority` |
| `asi_goal_overdue_total` | Counter | — |
| `asi_goal_registry_size` | Gauge | — |

### PromQL Examples

```promql
# Active CRITICAL goals
asi_goal_active{priority="0"}

# Goal achievement rate (5m window)
rate(asi_goal_status_transitions_total{to_status="achieved"}[5m])

# Overdue goals in last hour
increase(asi_goal_overdue_total[1h])
```

---

## mypy Compliance

| Symbol | Type hint |
|--------|-----------|
| `GoalRegistry` | `@runtime_checkable Protocol` |
| `InMemoryGoalRegistry` | concrete class |
| `Goal.tags` | `frozenset[str]` |
| `GoalRecord.sub_task_ids` | `list[str]` |
| `RegistrySnapshot.by_status` | `dict[str, int]` |
| `_records` | `dict[str, GoalRecord]` |
| `_lock` | `asyncio.Lock` |

---

## Test Targets

| # | Test name | What it verifies |
|---|-----------|-----------------|
| 1 | `test_register_goal` | register creates PENDING record |
| 2 | `test_register_duplicate_raises` | `DuplicateGoalError` on second register |
| 3 | `test_register_at_capacity_raises` | `RegistryFullError` when max_goals reached |
| 4 | `test_activate_transitions_to_active` | PENDING → ACTIVE |
| 5 | `test_invalid_transition_raises` | ACHIEVED → ACTIVE raises `InvalidTransitionError` |
| 6 | `test_block_and_reactivate` | ACTIVE → BLOCKED → ACTIVE |
| 7 | `test_achieve` | ACTIVE → ACHIEVED |
| 8 | `test_abandon` | any non-terminal → ABANDONED with reason |
| 9 | `test_evict_expired` | deadline_ms in past → ABANDONED, returns count |
| 10 | `test_list_by_status` | filters correctly across multiple goals |
| 11 | `test_list_by_priority` | returns goals at or above given priority |
| 12 | `test_snapshot` | reflects correct by_status and overdue_count |

---

## 14-Step Implementation Order

1. `GoalStatus` enum
2. `GoalPriority` enum
3. `Goal` frozen dataclass
4. `GoalRecord` dataclass
5. `RegistrySnapshot` dataclass
6. `InvalidTransitionError` + `DuplicateGoalError` + `RegistryFullError` + `GoalNotFoundError`
7. `GoalRegistry` Protocol (`@runtime_checkable`)
8. `InMemoryGoalRegistry.__init__()` — `_records` dict + `asyncio.Lock` + `_max_goals`
9. `_require()` + `_transition()` helpers
10. `register()` + Prometheus pre-init
11. `activate()` + `block()` + `reactivate()` + `achieve()` + `abandon()`
12. `list_by_status()` + `list_by_priority()`
13. `evict_expired()` + `snapshot()`
14. `build_goal_registry()` factory

---

## Phase 10 Roadmap

| Sub-phase | Component | Issue | Discussions |
|-----------|-----------|-------|-------------|
| 10.1 | `GoalRegistry` | #319 🟡 | #320 (S&T) · #321 (Q&A) · #322 (10.2 Ideas) |
| 10.2 | `GoalDecomposer` | TBD | #322 (Ideas) |
| 10.3 | `GoalTracker` | TBD | Planned |
| 10.4 | `ReplanningEngine` | TBD | Planned |
| 10.5 | `GoalBlackboardBridge` + Phase 11 stubs | TBD | Planned |
