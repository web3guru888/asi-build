# Phase 15.1 — Module Registry

> **Status**: 🟡 Spec open — Issue [#401](https://github.com/web3guru888/asi-build/issues/401)
> **Phase**: 15.1 of 5 in the Runtime Self-Modification pipeline
> **Depends on**: [PatchSelector](Phase-14-Patch-Selector) · [SynthesisAudit](Phase-14-Synthesis-Audit)
> **Planning**: [Discussion #400](https://github.com/web3guru888/asi-build/discussions/400)

---

## Overview

`ModuleRegistry` is the **central version store** for the ASI-Build runtime. After `PatchSelector` selects a winning patch, the registry records the new `ModuleVersion`, tracks its lifecycle (STAGED → ACTIVE → ARCHIVED/REVERTED), and serves as the source of truth for `HotReloader` (15.3) and `RollbackManager` (15.4).

---

## Phase 15 Roadmap

| Sub-phase | Component | Role |
|-----------|-----------|------|
| **15.1** | **ModuleRegistry** | Version store and lifecycle tracker |
| 15.2 | HotLoader | Python `importlib` live module swap |
| 15.3 | HotReloader | Orchestrates swap + health check |
| 15.4 | RollbackManager | Automatic revert on regression |
| 15.5 | SelfModificationAudit | Unified observability for runtime changes |

---

## Data Model

### `ModuleStatus` — enum

```python
class ModuleStatus(str, Enum):
    ACTIVE   = "active"    # currently loaded in the Python runtime
    STAGED   = "staged"    # validated but not yet swapped in
    REVERTED = "reverted"  # rolled back after regression
    ARCHIVED = "archived"  # older version, kept for audit/rollback
```

### `ModuleVersion` — frozen dataclass

```python
@dataclass(frozen=True)
class ModuleVersion:
    module_name: str            # e.g. "asi.synthesis.code_synthesiser"
    version:     int            # monotonically increasing (1, 2, 3, …)
    patch_id:    str            # links to SynthesisResult.patch_id
    source_code: str            # full Python source of this version
    checksum:    str            # sha256(source_code.encode())
    applied_at:  float          # time.time()
    status:      ModuleStatus
    cycle_id:    str            # CognitiveCycle run that produced this version

    def __post_init__(self) -> None:
        expected = hashlib.sha256(self.source_code.encode()).hexdigest()
        if self.checksum != expected:
            raise ValueError("ModuleVersion checksum mismatch")
```

### `RegistryQuery` — frozen dataclass

```python
@dataclass(frozen=True)
class RegistryQuery:
    module_name: str | None           = None
    status:      ModuleStatus | None  = None
    since:       float | None         = None
    limit:       int                  = 50
```

### `RegistryConfig` — frozen dataclass

```python
@dataclass(frozen=True)
class RegistryConfig:
    backend:      str  = "memory"     # "memory" | "sqlite"
    db_path:      str  = "registry.db"
    max_versions: int  = 10           # per module; older → ARCHIVED
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ModuleRegistry(Protocol):
    async def register(self, version: ModuleVersion) -> None: ...
    async def get_active(self, module_name: str) -> ModuleVersion | None: ...
    async def list_versions(self, q: RegistryQuery) -> list[ModuleVersion]: ...
    async def set_status(
        self, module_name: str, version: int, status: ModuleStatus
    ) -> None: ...
    async def latest_version(self, module_name: str) -> int: ...
    def stats(self) -> dict[str, int]: ...
```

---

## `InMemoryModuleRegistry` Implementation

```python
class InMemoryModuleRegistry:
    def __init__(self, cfg: RegistryConfig) -> None:
        self._cfg = cfg
        self._versions: dict[str, list[ModuleVersion]] = {}
        self._lock = asyncio.Lock()

    async def register(self, version: ModuleVersion) -> None:
        async with self._lock:
            bucket = self._versions.setdefault(version.module_name, [])
            bucket.append(version)
            # Trim oldest to ARCHIVED if over max_versions
            if len(bucket) > self._cfg.max_versions:
                oldest = bucket[0]
                bucket[0] = dataclasses.replace(oldest, status=ModuleStatus.ARCHIVED)
            ASI_REGISTRY_VERSIONS_TOTAL.labels(status=version.status.value).inc()

    async def get_active(self, module_name: str) -> ModuleVersion | None:
        async with self._lock:
            bucket = self._versions.get(module_name, [])
            return next(
                (v for v in reversed(bucket) if v.status == ModuleStatus.ACTIVE),
                None,
            )

    async def set_status(
        self, module_name: str, version: int, status: ModuleStatus
    ) -> None:
        async with self._lock:
            bucket = self._versions.get(module_name, [])
            for i, v in enumerate(bucket):
                if v.version == version:
                    bucket[i] = dataclasses.replace(v, status=status)
                    return
            raise KeyError(f"Version {version} of {module_name!r} not found")
```

---

## `CognitiveCycle._synthesis_step()` Integration

```python
async def _synthesis_step(
    self,
    task: Task,
    registry: ModuleRegistry,
) -> ModuleVersion | None:
    selection = await self._selector.select(candidates, self._selector_cfg)
    if selection.winner is None:
        await self._replanning_engine.replan(task)
        return None

    checksum = hashlib.sha256(selection.winner.source_code.encode()).hexdigest()
    new_version = ModuleVersion(
        module_name=selection.winner.target_module,
        version=await registry.latest_version(selection.winner.target_module) + 1,
        patch_id=selection.winner.patch_id,
        source_code=selection.winner.source_code,
        checksum=checksum,
        applied_at=time.time(),
        status=ModuleStatus.STAGED,
        cycle_id=self._cycle_id,
    )
    await registry.register(new_version)
    # Hand off to HotReloader (Phase 15.3) …
    return new_version
```

---

## Data Flow ASCII

```
PatchSelector.select()
       │
       ▼
ModuleVersion(status=STAGED)
       │
       ▼
ModuleRegistry.register()
       │
       ├──► HotReloader.swap() ──► ModuleVersion(status=ACTIVE)
       │
       └──► RollbackManager.watch() ──► ModuleVersion(status=REVERTED)
                                              │
                                              ▼
                                      ModuleRegistry.set_status(ARCHIVED)
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_registry_versions_total` | Counter | `status` | Versions registered |
| `asi_registry_register_latency_seconds` | Histogram | — | `register()` latency |
| `asi_registry_query_latency_seconds` | Histogram | — | `list_versions()` latency |
| `asi_registry_active_modules` | Gauge | — | Modules with ACTIVE version |
| `asi_registry_archived_versions_total` | Counter | — | Versions trimmed to ARCHIVED |

### PromQL Queries

```promql
# New staged versions rate (should mirror synthesis rate)
rate(asi_registry_versions_total{status="staged"}[1m])

# Active module count
asi_registry_active_modules

# Registry query latency P99
histogram_quantile(0.99, rate(asi_registry_query_latency_seconds_bucket[5m]))
```

### Grafana Alert — No Active Modules

```yaml
- alert: RegistryNoActiveModules
  expr: asi_registry_active_modules == 0
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "ModuleRegistry has no ACTIVE module versions — HotReloader may not have fired"
```

---

## mypy --strict Compliance

| Class | Notes |
|-------|-------|
| `ModuleVersion` | `dataclasses.replace()` in `set_status` returns `ModuleVersion` — cast if needed |
| `InMemoryModuleRegistry.get_active` | `next(..., None)` is typed `ModuleVersion \| None` ✓ |
| `ModuleRegistry` Protocol | `@runtime_checkable` — no `__init__` signature |
| `RegistryConfig.backend` | `Literal["memory", "sqlite"]` preferred over `str` |

---

## Test Targets (12)

| # | Test | Key assertion |
|---|------|---------------|
| 1 | `test_module_version_frozen` | `FrozenInstanceError` on mutation |
| 2 | `test_register_first_version` | version=1, status=STAGED |
| 3 | `test_get_active_none_if_no_active` | `None` before `set_status(ACTIVE)` |
| 4 | `test_get_active_returns_correct_version` | most-recent ACTIVE returned |
| 5 | `test_set_status_atomicity` | concurrent `set_status` under `asyncio.gather` |
| 6 | `test_max_versions_trim` | oldest → ARCHIVED when limit exceeded |
| 7 | `test_list_versions_by_status` | filter works |
| 8 | `test_list_versions_by_since` | time filter works |
| 9 | `test_list_versions_limit` | at most `limit` results |
| 10 | `test_latest_version_increments` | monotonic increment |
| 11 | `test_stats_counters` | `stats()` reflects all registered versions |
| 12 | `test_cognitive_cycle_registry_integration` | `register()` called with correct `ModuleVersion` |

---

## Implementation Order (14 steps)

1. `ModuleStatus` enum
2. `ModuleVersion` frozen dataclass + checksum `__post_init__`
3. `RegistryQuery` frozen dataclass
4. `RegistryConfig` frozen dataclass
5. `ModuleRegistry` Protocol + `@runtime_checkable`
6. `InMemoryModuleRegistry.__init__()` — `dict + asyncio.Lock`
7. `InMemoryModuleRegistry.register()` — append + trim + lock
8. `InMemoryModuleRegistry.get_active()`
9. `InMemoryModuleRegistry.list_versions()` — filter by `RegistryQuery`
10. `InMemoryModuleRegistry.set_status()` — atomic status update
11. `InMemoryModuleRegistry.latest_version()`
12. `InMemoryModuleRegistry.stats()`
13. 5 Prometheus metrics + registration
14. `CognitiveCycle._synthesis_step()` `registry.register()` call

---

## Phase 15 Sub-Phase Tracker

| Sub-phase | Component | Issue | Wiki | Status |
|-----------|-----------|-------|------|--------|
| **15.1** | **ModuleRegistry** | [#401](https://github.com/web3guru888/asi-build/issues/401) | This page | 🟡 Spec |
| 15.2 | HotLoader | ⏳ | ⏳ | ⏳ |
| 15.3 | HotReloader | ⏳ | ⏳ | ⏳ |
| 15.4 | RollbackManager | ⏳ | ⏳ | ⏳ |
| 15.5 | SelfModificationAudit | ⏳ | ⏳ | ⏳ |

