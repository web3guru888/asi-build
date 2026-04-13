# Phase 15.3 — DependencyResolver

> **Phase 15 — Live Module Upgrade** · Sub-phase 3 of 5

`DependencyResolver` is the safety layer that computes a **topological swap order** from the module dependency graph before `AsyncHotSwapper.swap_batch()` executes any replacements. It ensures that when module `B` depends on module `A`, `A` is always swapped before `B`, eliminating version-skew windows in hot-swap operations.

---

## Table of Contents

1. [Motivation](#motivation)
2. [ResolutionStatus enum](#resolutionstatus-enum)
3. [Frozen dataclasses](#frozen-dataclasses)
4. [DependencyResolver Protocol](#dependencyresolver-protocol)
5. [TopologicalResolver — reference implementation](#topologicalresolver--reference-implementation)
6. [Factory](#factory)
7. [HotSwapper integration](#hotswapper-integration)
8. [Resolution lifecycle ASCII](#resolution-lifecycle-ascii)
9. [Diamond-dependency example](#diamond-dependency-example)
10. [Prometheus metrics & PromQL](#prometheus-metrics--promql)
11. [Grafana alert YAML](#grafana-alert-yaml)
12. [mypy strict table](#mypy-strict-table)
13. [Test targets (12)](#test-targets-12)
14. [Implementation order (14 steps)](#implementation-order-14-steps)
15. [Phase 15 sub-phase tracker](#phase-15-sub-phase-tracker)

---

## Motivation

Multi-module hot-swaps without dependency awareness risk **version skew**:

```
Module A  (core inference)
    ↑ depends on
Module B  (feature extractor)
    ↑ depends on
Module C  (tokenizer)
```

If `C` is swapped after `B`, there is a window where the new `B` calls the old `C`. `DependencyResolver` guarantees `C` is always committed before `B` starts its swap lifecycle.

---

## ResolutionStatus enum

```python
from enum import Enum, auto

class ResolutionStatus(Enum):
    RESOLVED = auto()   # full topological order produced
    CYCLIC   = auto()   # circular dependency detected — swap aborted
    MISSING  = auto()   # required dependency not registered in ModuleRegistry
    PARTIAL  = auto()   # some deps unavailable; resolution continues (warn mode)
```

---

## Frozen dataclasses

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet, Tuple

@dataclass(frozen=True)
class ModuleDep:
    module_id:  str
    depends_on: FrozenSet[str]           # direct dependencies (module IDs)
    version:    str = "0.0.0"

@dataclass(frozen=True)
class ResolutionResult:
    status:   ResolutionStatus
    order:    Tuple[str, ...]            # topological swap order (empty on CYCLIC)
    cycles:   Tuple[Tuple[str, ...], ...] = field(default_factory=tuple)
    missing:  FrozenSet[str]             = field(default_factory=frozenset)
    warnings: Tuple[str, ...]            = field(default_factory=tuple)

@dataclass(frozen=True)
class ResolverConfig:
    strict_missing: bool  = True         # True → MISSING status; False → PARTIAL
    max_depth:      int   = 64           # guard against pathological graphs
    timeout_s:      float = 5.0

    def __post_init__(self) -> None:
        if self.max_depth < 1:
            raise ValueError("max_depth must be ≥ 1")
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
```

---

## DependencyResolver Protocol

```python
from typing import Protocol, runtime_checkable, Sequence

@runtime_checkable
class DependencyResolver(Protocol):
    def add_dependency(self, dep: ModuleDep) -> None: ...
    def resolve(self, targets: Sequence[str]) -> ResolutionResult: ...
    def remove_dependency(self, module_id: str) -> None: ...
    def clear(self) -> None: ...
```

---

## TopologicalResolver — reference implementation

```python
import time
from collections import defaultdict, deque
from typing import Dict, List, Set, Sequence

class TopologicalResolver:
    """Kahn's algorithm with BFS transitive closure and cycle detection."""

    def __init__(self, config: ResolverConfig = ResolverConfig()) -> None:
        self._config = config
        self._deps:  Dict[str, ModuleDep] = {}
        self._hits   = 0
        self._misses = 0

    # ── mutation ──────────────────────────────────────────────────────────
    def add_dependency(self, dep: ModuleDep) -> None:
        self._deps[dep.module_id] = dep

    def remove_dependency(self, module_id: str) -> None:
        self._deps.pop(module_id, None)

    def clear(self) -> None:
        self._deps.clear()

    # ── resolution ────────────────────────────────────────────────────────
    def resolve(self, targets: Sequence[str]) -> ResolutionResult:
        """Return topological order for *targets* and all transitive deps."""
        start    = time.monotonic()
        visited: Set[str]  = set()
        queue             = deque(targets)
        missing: Set[str]  = set()
        warnings: List[str] = []

        # Phase 1 — BFS transitive closure
        while queue:
            mid = queue.popleft()
            if mid in visited:
                continue
            visited.add(mid)

            if len(visited) > self._config.max_depth:
                warnings.append(
                    f"Graph depth exceeded max_depth={self._config.max_depth} — partial result"
                )
                break

            if mid not in self._deps:
                if self._config.strict_missing:
                    missing.add(mid)
                else:
                    warnings.append(f"Module {mid!r} missing from registry — skipped")
                continue

            for dep_id in self._deps[mid].depends_on:
                if dep_id not in visited:
                    queue.append(dep_id)

            if time.monotonic() - start > self._config.timeout_s:
                warnings.append("Resolution timed out — partial result")
                break

        if missing:
            self._misses += 1
            return ResolutionResult(
                status=ResolutionStatus.MISSING,
                order=(),
                missing=frozenset(missing),
                warnings=tuple(warnings),
            )

        # Phase 2 — Kahn's topological sort
        in_degree: Dict[str, int]       = defaultdict(int)
        graph:     Dict[str, List[str]] = defaultdict(list)

        for mid in visited:
            if mid not in self._deps:
                continue
            for dep_id in self._deps[mid].depends_on:
                if dep_id in visited:
                    graph[dep_id].append(mid)   # dep_id must come before mid
                    in_degree[mid] += 1

        ready = deque(m for m in visited if in_degree.get(m, 0) == 0)
        order: List[str] = []

        while ready:
            node = ready.popleft()
            order.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    ready.append(neighbor)

        # Cycle detection — nodes with remaining in-degree > 0
        if len(order) != len(visited):
            cycle_nodes = tuple(sorted(m for m in visited if in_degree.get(m, 0) > 0))
            self._misses += 1
            return ResolutionResult(
                status=ResolutionStatus.CYCLIC,
                order=(),
                cycles=(cycle_nodes,),
                warnings=tuple(warnings),
            )

        self._hits += 1
        return ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            order=tuple(order),
            warnings=tuple(warnings),
        )

    # ── stats ─────────────────────────────────────────────────────────────
    def stats(self) -> dict:
        return {
            "hits":       self._hits,
            "misses":     self._misses,
            "registered": len(self._deps),
        }

    def reset(self) -> None:
        self._hits = self._misses = 0
```

---

## Factory

```python
def make_resolver(config: ResolverConfig | None = None) -> TopologicalResolver:
    return TopologicalResolver(config or ResolverConfig())
```

---

## HotSwapper integration

`swap_batch()` receives a `DependencyResolver` and uses the topological order to sequence individual swaps:

```python
async def swap_batch(
    self,
    requests: list[SwapRequest],
    resolver: DependencyResolver,
) -> list[SwapResult]:
    targets    = [r.module_id for r in requests]
    resolution = resolver.resolve(targets)

    match resolution.status:
        case ResolutionStatus.CYCLIC:
            return [
                SwapResult(r.module_id, SwapPhase.FAILED,
                           error=f"Cycle detected: {resolution.cycles}")
                for r in requests
            ]
        case ResolutionStatus.MISSING:
            return [
                SwapResult(r.module_id, SwapPhase.FAILED,
                           error=f"Missing deps: {resolution.missing}")
                for r in requests
            ]

    req_map = {r.module_id: r for r in requests}
    results: list[SwapResult] = []

    for module_id in resolution.order:        # ← topological order guaranteed
        if module_id in req_map:
            results.append(await self.swap(req_map[module_id]))

    return results
```

**Key guarantees:**
- **No deadlock** — Kahn's algorithm ensures correct ordering
- **Fail-fast** — cycles and missing deps abort before any swap begins
- **Partial target** — only modules in `requests` are swapped; transitive deps are resolved but not swapped unless explicitly requested

---

## Resolution lifecycle ASCII

```
swap_batch([B, C]) called
        │
        ▼
DependencyResolver.resolve(["B", "C"])
        │
        ├── Phase 1: BFS transitive closure
        │     {B, C} → expand deps → {A, B, C}
        │
        ├── Phase 2: Kahn's topological sort
        │     in_degree: A=0, B=1(A), C=1(B)
        │     ready=[A] → order=[A,B,C]
        │
        ├── status == RESOLVED → order=(A, B, C)
        │
        └── swap_batch sequences:
              swap(C) → swap(B)   (A not in requests → skipped)
```

---

## Diamond-dependency example

```
       ┌──► B ──┐
 A ────┤         ▼
       └──► C ──► D   ← target
```

`resolve(["D"])`:
- BFS: `{D}` → expand D→{B,C} → expand B→{A}, C→{A} → `{A, B, C, D}`
- Kahn's: `in_degree = {B:1, C:1, D:2}`, ready=`[A]`
- Result: `order=(A, B, C, D)` or `(A, C, B, D)` — both valid (tie-broken by BFS insertion order)

---

## Prometheus metrics & PromQL

| Metric | Type | Description |
|--------|------|-------------|
| `asi_resolver_resolutions_total{status}` | Counter | Resolutions by outcome |
| `asi_resolver_cycle_detections_total` | Counter | Cycle detection events |
| `asi_resolver_missing_deps_total` | Counter | Missing dependency events |
| `asi_resolver_resolution_seconds` | Histogram | Resolution latency |
| `asi_resolver_graph_size` | Gauge | Registered module count |

**PromQL alerts:**
```promql
# Any cycle detected in the last 5 minutes
increase(asi_resolver_cycle_detections_total[5m]) > 0

# Missing dependency rate rising
increase(asi_resolver_missing_deps_total[5m]) > 2

# Resolution p99 > 100 ms
histogram_quantile(0.99,
  rate(asi_resolver_resolution_seconds_bucket[5m])) > 0.1
```

---

## Grafana alert YAML

```yaml
groups:
  - name: asi_dependency_resolver
    rules:
      - alert: CyclicDependencyDetected
        expr: increase(asi_resolver_cycle_detections_total[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Cyclic dependency detected — hot-swap aborted"

      - alert: MissingModuleDependency
        expr: increase(asi_resolver_missing_deps_total[5m]) > 2
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Multiple missing module dependencies in last 5m"

      - alert: ResolverLatencyHigh
        expr: >
          histogram_quantile(0.99,
            rate(asi_resolver_resolution_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DependencyResolver p99 latency > 100ms"
```

---

## mypy strict table

| Symbol | Annotation note |
|--------|----------------|
| `ModuleDep.depends_on` | `FrozenSet[str]` — construct with `frozenset({"a", "b"})` |
| `ResolutionResult.order` | `Tuple[str, ...]` — `tuple(order_list)` |
| `ResolutionResult.cycles` | `Tuple[Tuple[str, ...], ...]` — nested frozen tuples |
| `ResolutionResult.missing` | `FrozenSet[str]` — `frozenset(missing_set)` |
| `TopologicalResolver.resolve` | Returns `ResolutionResult` (never `Optional`) |
| `DependencyResolver` Protocol | `@runtime_checkable` for `isinstance()` checks |
| `graph` dict | `Dict[str, List[str]]` — not `defaultdict` in annotation |
| `in_degree` dict | `Dict[str, int]` — default via `defaultdict(int)` |

---

## Test targets (12)

| # | Test name | Scenario |
|---|-----------|----------|
| 1 | `test_resolve_linear_chain` | A→B→C resolves to `(A, B, C)` |
| 2 | `test_resolve_diamond` | Diamond DAG resolves correctly |
| 3 | `test_resolve_cycle_detected` | A→B→A returns `CYCLIC` |
| 4 | `test_resolve_missing_strict` | Unknown dep → `MISSING` |
| 5 | `test_resolve_missing_partial` | `strict_missing=False` → `PARTIAL` |
| 6 | `test_resolve_empty_targets` | Empty list → `RESOLVED`, empty order |
| 7 | `test_resolve_single_no_deps` | Single module, no deps |
| 8 | `test_add_remove_dependency` | Mutation correctness |
| 9 | `test_resolve_transitive_closure` | Deep dep graph (depth 10) |
| 10 | `test_resolve_max_depth_guard` | Pathological graph hits `max_depth` |
| 11 | `test_swap_batch_ordering` | `swap_batch` respects topological order |
| 12 | `test_swap_batch_aborts_on_cycle` | `swap_batch` returns `FAILED` on cycle |

---

## Implementation order (14 steps)

1. Define `ResolutionStatus` enum
2. Implement `ModuleDep` frozen dataclass
3. Implement `ResolutionResult` frozen dataclass
4. Implement `ResolverConfig` with `__post_init__` validation
5. Define `DependencyResolver` Protocol (`@runtime_checkable`)
6. Implement `TopologicalResolver.__init__` with metrics hooks
7. Implement `add_dependency` / `remove_dependency` / `clear`
8. Implement Phase 1 — BFS transitive closure with `max_depth` guard
9. Implement Phase 2 — Kahn's topological sort
10. Implement cycle detection (remaining `in_degree > 0`)
11. Implement `stats()` / `reset()`
12. Integrate into `AsyncHotSwapper.swap_batch()` with `match` dispatch
13. Wire Prometheus metrics
14. Write 12 test cases

---

## Phase 15 sub-phase tracker

| Sub-phase | Component | Issue | Discussions | Wiki | Status |
|-----------|-----------|-------|-------------|------|--------|
| 15.1 | ModuleRegistry | [#401](https://github.com/web3guru888/asi-build/issues/401) | — | [📖](https://github.com/web3guru888/asi-build/wiki/Phase-15-Module-Registry) | 🟡 In Progress |
| 15.2 | HotSwapper | [#402](https://github.com/web3guru888/asi-build/issues/402) | [#405](https://github.com/web3guru888/asi-build/discussions/405) [#406](https://github.com/web3guru888/asi-build/discussions/406) | [📖](https://github.com/web3guru888/asi-build/wiki/Phase-15-Hot-Swapper) | 🟡 In Progress |
| 15.3 | DependencyResolver | [#407](https://github.com/web3guru888/asi-build/issues/407) | [#408](https://github.com/web3guru888/asi-build/discussions/408) [#409](https://github.com/web3guru888/asi-build/discussions/409) | [📖](https://github.com/web3guru888/asi-build/wiki/Phase-15-Dependency-Resolver) | 🟡 In Progress |
| 15.4 | RollbackManager | TBD | — | — | ⏳ Planned |
| 15.5 | UpgradePlanner | TBD | — | — | ⏳ Planned |
