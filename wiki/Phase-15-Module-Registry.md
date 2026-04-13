# Phase 15.1 — `ModuleRegistry`: live module version tracking and swap coordination

**Issue**: #401 | **Phase**: 15 — Runtime Self-Modification & Hot-Reload Architecture

---

## Overview

`ModuleRegistry` is the Phase 15.1 component that tracks every version of every cognitive module — from synthesis through staging, activation, and archival. It is the **authoritative source of truth** for the hot-reload pipeline: the `HotSwapper` (Phase 15.2) queries it to discover which modules have staged patches ready for live deployment.

---

## Enumerations

```python
import enum

class ModuleStatus(enum.Enum):
    STAGED   = "staged"    # synthesised & tested, awaiting swap
    ACTIVE   = "active"    # currently running in CognitiveCycle
    REVERTED = "reverted"  # swap attempted, validation failed
    ARCHIVED = "archived"  # superseded by a newer ACTIVE version
```

---

## Frozen Dataclasses

```python
import dataclasses
import hashlib

@dataclasses.dataclass(frozen=True)
class ModuleVersion:
    module_name: str
    version:     int          # monotonically increasing within a module
    checksum:    bytes        # SHA-256 of the compiled artifact
    status:      ModuleStatus
    registered_at: float = dataclasses.field(default_factory=lambda: __import__('time').monotonic())

@dataclasses.dataclass(frozen=True)
class RegistryQuery:
    module_name: str | None = None
    status:      ModuleStatus | None = None
    min_version: int = 0

@dataclasses.dataclass(frozen=True)
class RegistryConfig:
    max_versions_per_module: int = 50   # trim oldest ARCHIVED versions beyond this
    persist_path: str | None = None     # optional JSON snapshot path
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ModuleRegistry(Protocol):
    def register(self, version: ModuleVersion) -> None:
        """Register a new module version. Raises ValueError on duplicate (name, version)."""
        ...

    def get_active(self, module_name: str) -> ModuleVersion | None:
        """Return the current ACTIVE version, or None."""
        ...

    def list_versions(
        self, module_name: str, status: ModuleStatus | None = None
    ) -> list[ModuleVersion]:
        """Return all known versions, optionally filtered by status, sorted by version asc."""
        ...

    def set_status(
        self, module_name: str, version: int, new_status: ModuleStatus
    ) -> ModuleVersion:
        """Atomically transition a version to a new status. Returns updated ModuleVersion."""
        ...

    def latest_version(
        self, module_name: str, status: ModuleStatus | None = None
    ) -> int:
        """Return the highest version number (optionally filtered by status), or 0."""
        ...

    def latest_staged(self, module_name: str) -> ModuleVersion | None:
        """Return the highest-version STAGED entry, or None."""
        ...

    def list_staged_modules(self) -> list[str]:
        """Return names of all modules that have at least one STAGED version."""
        ...

    def stats(self) -> dict[str, dict[str, int]]:
        """Return per-module counts grouped by status."""
        ...
```

---

## Reference Implementation: `InMemoryModuleRegistry`

```python
import asyncio
import dataclasses
from collections import defaultdict

class InMemoryModuleRegistry:
    def __init__(self, config: RegistryConfig | None = None) -> None:
        self._cfg  = config or RegistryConfig()
        self._lock = asyncio.Lock()
        # module_name → version → ModuleVersion
        self._store: dict[str, dict[int, ModuleVersion]] = defaultdict(dict)

    def register(self, version: ModuleVersion) -> None:
        versions = self._store[version.module_name]
        if version.version in versions:
            raise ValueError(
                f"Duplicate version {version.version} for module {version.module_name!r}"
            )
        versions[version.version] = version
        self._trim(version.module_name)

    def get_active(self, module_name: str) -> ModuleVersion | None:
        for v in reversed(sorted(self._store[module_name].values(), key=lambda x: x.version)):
            if v.status == ModuleStatus.ACTIVE:
                return v
        return None

    def list_versions(
        self, module_name: str, status: ModuleStatus | None = None
    ) -> list[ModuleVersion]:
        vs = sorted(self._store[module_name].values(), key=lambda x: x.version)
        if status is not None:
            vs = [v for v in vs if v.status == status]
        return vs

    def set_status(
        self, module_name: str, version: int, new_status: ModuleStatus
    ) -> ModuleVersion:
        versions = self._store[module_name]
        if version not in versions:
            raise KeyError(f"Version {version} not found for module {module_name!r}")
        updated = dataclasses.replace(versions[version], status=new_status)
        versions[version] = updated
        return updated

    def latest_version(
        self, module_name: str, status: ModuleStatus | None = None
    ) -> int:
        vs = self.list_versions(module_name, status=status)
        return vs[-1].version if vs else 0

    def latest_staged(self, module_name: str) -> ModuleVersion | None:
        staged = self.list_versions(module_name, status=ModuleStatus.STAGED)
        return staged[-1] if staged else None

    def list_staged_modules(self) -> list[str]:
        return [
            name for name, versions in self._store.items()
            if any(v.status == ModuleStatus.STAGED for v in versions.values())
        ]

    def stats(self) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for name, versions in self._store.items():
            counts: dict[str, int] = {s.value: 0 for s in ModuleStatus}
            for v in versions.values():
                counts[v.status.value] += 1
            result[name] = counts
        return result

    def _trim(self, module_name: str) -> None:
        """Remove oldest ARCHIVED versions beyond max_versions_per_module."""
        archived = sorted(
            [v for v in self._store[module_name].values() if v.status == ModuleStatus.ARCHIVED],
            key=lambda x: x.version,
        )
        while len(self._store[module_name]) > self._cfg.max_versions_per_module and archived:
            oldest = archived.pop(0)
            del self._store[module_name][oldest.version]
```

---

## `CognitiveCycle` Integration

```python
class CognitiveCycle:
    def __init__(self, ..., registry: ModuleRegistry | None = None) -> None:
        ...
        self._registry = registry or InMemoryModuleRegistry()

    async def _synthesis_step(self) -> None:
        # ... Phase 14: synthesise → sandbox → harness → selector → audit
        patch: PatchCandidate = ...
        checksum = hashlib.sha256(patch.code.encode()).digest()
        version_num = self._registry.latest_version(patch.module_name) + 1
        mv = ModuleVersion(
            module_name=patch.module_name,
            version=version_num,
            checksum=checksum,
            status=ModuleStatus.STAGED,
        )
        self._registry.register(mv)
        # → HotSwapper (Phase 15.2) will pick this up next
```

---

## Data-Flow Diagram

```
SynthesisAudit (Phase 14.5)
        │  PATCH_APPLIED event
        ▼
ModuleRegistry.register(status=STAGED)
        │
        ├── list_staged_modules() ─────────────► HotSwapper.swap_all_staged()
        │                                                  │
        │                                    ┌─[valid]─────┤
        │                                    │             └─[invalid]──┐
        ▼                                    ▼                          ▼
set_status(ACTIVE) / old → ARCHIVED    ModuleStatus.ACTIVE      ModuleStatus.REVERTED
```

---

## Prometheus Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `asi_registry_registrations_total` | Counter | `module`, `status` |
| `asi_registry_active_modules` | Gauge | `module` |
| `asi_registry_staged_queue_depth` | Gauge | — |
| `asi_registry_status_transitions_total` | Counter | `module`, `from`, `to` |
| `asi_registry_versions_total` | Gauge | `module` |

### Example PromQL

```promql
# Modules awaiting hot-swap
asi_registry_staged_queue_depth

# Status transition rate
rate(asi_registry_status_transitions_total{to="active"}[5m])
```

### Grafana Alert

```yaml
- alert: RegistryStagedQueueBacklog
  expr: asi_registry_staged_queue_depth > 10
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "ModuleRegistry staged queue has >10 pending modules"
    description: "HotSwapper may not be keeping up with synthesis throughput."
```

---

## Type-Safety Table

| Symbol | mypy annotation | `isinstance` check |
|--------|-----------------|---------------------|
| `ModuleRegistry` | `Protocol` | ✅ (runtime_checkable) |
| `ModuleVersion` | `frozen dataclass` | ✅ |
| `RegistryConfig` | `frozen dataclass` | ✅ |
| `ModuleStatus` | `str Enum` | ✅ |
| `RegistryQuery` | `frozen dataclass` | ✅ |

---

## Test Targets (12)

1. `test_register_and_get_active` — register ACTIVE version → get_active returns it
2. `test_register_duplicate_raises` — duplicate (name, version) → ValueError
3. `test_list_versions_filtered` — list_versions with status filter
4. `test_set_status_transitions` — STAGED → ACTIVE → ARCHIVED state transitions
5. `test_set_status_missing_raises` — set_status on unknown version → KeyError
6. `test_latest_version_empty` — latest_version when no versions → 0
7. `test_latest_staged` — latest_staged returns highest STAGED, or None
8. `test_list_staged_modules` — list_staged_modules across multiple modules
9. `test_stats_counts` — stats() reflects correct per-status counts
10. `test_trim_archived` — max_versions_per_module triggers oldest-ARCHIVED trim
11. `test_set_status_atomicity` — asyncio.gather(20 concurrent set_status) → no corruption
12. `test_checksum_immutable` — ModuleVersion.checksum cannot be mutated (frozen)

### Test Skeleton — atomicity

```python
import asyncio, pytest

@pytest.mark.asyncio
async def test_set_status_atomicity():
    registry = InMemoryModuleRegistry()
    for v in range(1, 21):
        registry.register(ModuleVersion("planner", v, b"x" * 32, ModuleStatus.STAGED))

    async def transition(v: int):
        registry.set_status("planner", v, ModuleStatus.ACTIVE)

    await asyncio.gather(*[transition(v) for v in range(1, 21)])
    active = registry.list_versions("planner", status=ModuleStatus.ACTIVE)
    assert len(active) == 20  # all transitioned without KeyError
```

---

## Implementation Order (14 steps)

1. Define `ModuleStatus` enum
2. Define `ModuleVersion` frozen dataclass (with `registered_at` default)
3. Define `RegistryQuery` + `RegistryConfig` frozen dataclasses
4. Define `ModuleRegistry` Protocol (`@runtime_checkable`)
5. Implement `InMemoryModuleRegistry.__init__()` with `defaultdict` store
6. Implement `register()` with duplicate guard + `_trim()`
7. Implement `get_active()` — reverse-sorted scan
8. Implement `list_versions()` with optional status filter
9. Implement `set_status()` using `dataclasses.replace()`
10. Implement `latest_version()` + `latest_staged()` + `list_staged_modules()`
11. Implement `stats()` counter aggregation
12. Wire into `CognitiveCycle._synthesis_step()` (register STAGED after synthesis)
13. Register Prometheus metrics (Counter + Gauge)
14. Write unit + integration tests

---

## Phase 15 Sub-Phase Tracker

| Sub-phase | Component | Issue | Wiki | Status |
|-----------|-----------|-------|------|--------|
| 15.1 | ModuleRegistry | #401 | [this page](Phase-15-Module-Registry) | 🟡 open |
| 15.2 | HotSwapper | #402 | [Phase-15-Hot-Swapper](Phase-15-Hot-Swapper) | 🟡 open |
| 15.3 | RollbackCoordinator | — | — | ⏳ |
| 15.4 | CapabilityIndex | — | — | ⏳ |
| 15.5 | SelfModificationAudit | — | — | ⏳ |

---

*Part of the Phase 15 — Runtime Self-Modification & Hot-Reload Architecture track.*
