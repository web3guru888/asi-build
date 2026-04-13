# Phase 15.4 — `VersionManager`

**Module**: `asi/self_modification/version_manager.py`  
**Depends on**: Phase 15.1 `ModuleRegistry` (#401), Phase 15.3 `DependencyResolver` (#407)  
**Issue**: #410  
**Phase**: 15 — Hot-Reload & Self-Modification  
**Discussions**: [Show & Tell #411](https://github.com/web3guru888/asi-build/discussions/411) · [Q&A #412](https://github.com/web3guru888/asi-build/discussions/412)

---

## Overview

`VersionManager` maintains a complete **version lineage** for every hot-swappable module. It records upgrade/rollback checkpoints, enforces semantic-version compatibility constraints, and exposes a clean API for `HotSwapper` (#402) to query *"is version B backward-compatible with version A?"* before committing a live swap.

---

## Enumerations

```python
from enum import Enum, auto

class CompatibilityLevel(Enum):
    COMPATIBLE     = auto()   # Drop-in replacement — no interface changes
    MINOR_CHANGE   = auto()   # Additive change — new optional fields/methods
    BREAKING       = auto()   # Interface removed or signature changed
    UNKNOWN        = auto()   # Insufficient information to determine

class RollbackReason(Enum):
    MANUAL         = auto()   # Operator-initiated rollback
    HEALTH_FAILURE = auto()   # Post-swap health check failed
    DEPENDENCY     = auto()   # Downstream dependency broke
    TIMEOUT        = auto()   # Rollback triggered by swap timeout
```

---

## Data Model

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet, Mapping

@dataclass(frozen=True)
class VersionCheckpoint:
    module_id:   str
    version:     int
    checksum:    str
    timestamp:   float          # Unix epoch
    parent_ver:  int | None     # None for initial version
    tags:        FrozenSet[str] = field(default_factory=frozenset)
    metadata:    Mapping[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class CompatibilityReport:
    module_id:   str
    from_ver:    int
    to_ver:      int
    level:       CompatibilityLevel
    rationale:   str
    approved_by: str = "auto"   # "auto" | operator id

@dataclass(frozen=True)
class VersionManagerConfig:
    max_checkpoints:           int  = 20
    require_approval:          bool = False
    auto_rollback_on_breaking: bool = True

    def __post_init__(self):
        if self.max_checkpoints < 2:
            raise ValueError("max_checkpoints must be >= 2")
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable, Sequence

@runtime_checkable
class VersionManager(Protocol):
    def record_checkpoint(self, cp: VersionCheckpoint) -> None: ...
    def get_lineage(self, module_id: str) -> Sequence[VersionCheckpoint]: ...
    def latest_checkpoint(self, module_id: str) -> VersionCheckpoint | None: ...
    def rollback_target(self, module_id: str, reason: RollbackReason) -> VersionCheckpoint | None: ...
    def assess_compatibility(self, report: CompatibilityReport) -> CompatibilityLevel: ...
    def pending_approvals(self) -> Sequence[CompatibilityReport]: ...
    def stats(self) -> dict[str, int]: ...
```

---

## Reference Implementation — `LinearVersionManager`

```python
import asyncio, time
from collections import defaultdict
from typing import Sequence

class LinearVersionManager:
    """
    Thread-safe version manager backed by in-memory lists.

    Rollback target selection: walk backwards from current checkpoint,
    skip any version assessed as BREAKING, return first safe prior.
    """

    def __init__(self, cfg: VersionManagerConfig | None = None):
        self._cfg = cfg or VersionManagerConfig()
        self._lineage: dict[str, list[VersionCheckpoint]] = defaultdict(list)
        self._reports: dict[tuple, CompatibilityReport] = {}
        self._pending: list[CompatibilityReport] = []
        self._lock = asyncio.Lock()

    async def record_checkpoint(self, cp: VersionCheckpoint) -> None:
        async with self._lock:
            chain = self._lineage[cp.module_id]
            chain.append(cp)
            if len(chain) > self._cfg.max_checkpoints:
                self._lineage[cp.module_id] = chain[-self._cfg.max_checkpoints:]

    async def get_lineage(self, module_id: str) -> list[VersionCheckpoint]:
        async with self._lock:
            return list(self._lineage.get(module_id, []))

    async def latest_checkpoint(self, module_id: str) -> VersionCheckpoint | None:
        async with self._lock:
            chain = self._lineage.get(module_id, [])
            return chain[-1] if chain else None

    async def rollback_target(
        self, module_id: str, reason: RollbackReason
    ) -> VersionCheckpoint | None:
        async with self._lock:
            chain = self._lineage.get(module_id, [])
            if len(chain) < 2:
                return None
            current_ver = chain[-1].version
            for cp in reversed(chain[:-1]):
                key = (module_id, cp.version, current_ver)
                report = self._reports.get(key)
                if report is None or report.level != CompatibilityLevel.BREAKING:
                    return cp
            return chain[0]

    async def assess_compatibility(
        self, report: CompatibilityReport
    ) -> CompatibilityLevel:
        async with self._lock:
            key = (report.module_id, report.from_ver, report.to_ver)
            self._reports[key] = report
            if (report.level == CompatibilityLevel.BREAKING
                    and self._cfg.require_approval
                    and report.approved_by == "auto"
                    and report not in self._pending):
                self._pending.append(report)
            return report.level

    async def pending_approvals(self) -> list[CompatibilityReport]:
        async with self._lock:
            return list(self._pending)

    def stats(self) -> dict[str, int]:
        return {
            "tracked_modules":       len(self._lineage),
            "total_checkpoints":     sum(len(v) for v in self._lineage.values()),
            "compatibility_records": len(self._reports),
            "pending_approvals":     len(self._pending),
        }

    def reset(self) -> None:
        self._lineage.clear()
        self._reports.clear()
        self._pending.clear()


def make_version_manager(cfg: VersionManagerConfig | None = None) -> VersionManager:
    return LinearVersionManager(cfg)
```

---

## Version Lifecycle

```
register(v=1)                    register(v=2)               HEALTH_FAIL
     │                                │                           │
     ▼                                ▼                           ▼
[VersionCheckpoint v=1]   [VersionCheckpoint v=2]    rollback_target() → v=1
 parent=None               parent=v=1                ModuleRegistry.set_status(REVERTED)
```

---

## Compatibility Assessment Table

| `CompatibilityLevel` | Meaning | HotSwapper action |
|----------------------|---------|-------------------|
| `COMPATIBLE` | Drop-in — no interface changes | Proceed |
| `MINOR_CHANGE` | Additive — new optional fields | Proceed |
| `BREAKING` | Interface removed or signature changed | Block if `reject_breaking=True` |
| `UNKNOWN` | Insufficient information | Proceed (log warning) |

---

## `require_approval` × `auto_rollback_on_breaking` Matrix

| `require_approval` | `auto_rollback_on_breaking` | Behaviour |
|-|-|-|
| `False` | `False` | BREAKING swaps proceed; no rollback |
| `False` | `True` | BREAKING swaps proceed; rolled back on health failure |
| `True` | `False` | BREAKING swaps blocked until approved; no auto-rollback |
| `True` | `True` | BREAKING swaps blocked until approved; rolled back if health fails post-approval |

Recommended production setting: `require_approval=True, auto_rollback_on_breaking=True`.

---

## HotSwapper Integration

`HotSwapper.swap()` gains a `version_manager` keyword argument:

```python
async def swap(
    self,
    request: SwapRequest,
    *,
    resolver: DependencyResolver | None = None,
    version_manager: VersionManager | None = None,
) -> SwapResult:
    if version_manager:
        compat = await version_manager.assess_compatibility(
            CompatibilityReport(
                module_id   = request.module_id,
                from_ver    = request.from_version,
                to_ver      = request.to_version,
                level       = CompatibilityLevel.UNKNOWN,
                rationale   = "pre-swap auto-assessment",
            )
        )
        if (compat == CompatibilityLevel.BREAKING
                and self._cfg.reject_breaking):
            return SwapResult(
                module_id = request.module_id,
                phase     = SwapPhase.FAILED,
                error     = "breaking change rejected by config",
            )
    result = await self._do_swap(request)
    if version_manager and result.phase == SwapPhase.COMMITTED:
        await version_manager.record_checkpoint(
            VersionCheckpoint(
                module_id  = request.module_id,
                version    = request.to_version,
                checksum   = request.checksum,
                timestamp  = time.time(),
                parent_ver = request.from_version,
            )
        )
    return result
```

---

## CognitiveCycle Integration

```python
async def _synthesis_step(self, goal: Goal) -> SynthesisResult:
    ...
    match selector_result.status:
        case SelectionStatus.WINNER:
            swap_req = SwapRequest(
                module_id    = goal.target_module,
                from_version = self._registry.latest_version(goal.target_module),
                to_version   = selector_result.winner.version,
                checksum     = selector_result.winner.checksum,
            )
            swap_result = await self._hot_swapper.swap(
                swap_req,
                resolver        = self._dep_resolver,
                version_manager = self._version_manager,   # ← Phase 15.4
            )
            match swap_result.phase:
                case SwapPhase.COMMITTED:
                    return SynthesisResult.success(swap_result)
                case SwapPhase.ROLLED_BACK:
                    rb_target = await self._version_manager.rollback_target(
                        goal.target_module, RollbackReason.HEALTH_FAILURE
                    )
                    return SynthesisResult.rolled_back(rb_target)
        case _:
            return SynthesisResult.no_candidate()
```

---

## Full Pipeline Data Flow

```
ModuleRegistry          VersionManager          HotSwapper          DependencyResolver
     │                       │                      │                       │
     │  register(v=1) ──────►│ record_checkpoint    │                       │
     │                       │  (v=1, parent=None)  │                       │
     │                       │                      │                       │
     │                       │                      │◄── resolve(deps) ────►│
     │                       │                      │    topological order  │
     │                       │                      │                       │
     │  register(v=2) ──────►│◄── assess_compat ────│                       │
     │                       │    UNKNOWN→COMPATIBLE│                       │
     │                       │                      │                       │
     │                       │ record_checkpoint ───│ COMMITTED             │
     │                       │  (v=2, parent=v=1)   │                       │
     │                       │                      │                       │
     │             HEALTH FAILURE ─────────────────►│                       │
     │                       │◄── rollback_target ──│                       │
     │                       │    returns v=1       │                       │
     │◄── set_status(REVERTED)│                      │                       │
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asm_version_checkpoints_total` | Counter | `module_id` | Checkpoints recorded |
| `asm_version_rollbacks_total` | Counter | `module_id`, `reason` | Rollbacks triggered |
| `asm_version_breaking_changes_total` | Counter | `module_id` | BREAKING assessments |
| `asm_version_pending_approvals` | Gauge | — | Pending approval queue depth |
| `asm_version_lineage_depth` | Gauge | `module_id` | Checkpoint chain length |

### PromQL Alerts

```yaml
- alert: VersionRollbackStorm
  expr: rate(asm_version_rollbacks_total[5m]) > 0.5
  for: 2m
  annotations:
    summary: "High rollback rate — check module stability"

- alert: BreakingChangePending
  expr: asm_version_pending_approvals > 0
  for: 1m
  annotations:
    summary: "Breaking-change swap awaiting operator approval"
```

### Grafana Dashboard (4-panel)

```yaml
panels:
  - title: "Checkpoint Rate"
    type: timeseries
    expr: rate(asm_version_checkpoints_total[5m])
  - title: "Rollback Rate by Module"
    type: timeseries
    expr: rate(asm_version_rollbacks_total[5m])
    legendFormat: "{{module_id}} / {{reason}}"
  - title: "Lineage Depth"
    type: bargauge
    expr: asm_version_lineage_depth
    legendFormat: "{{module_id}}"
  - title: "Pending Approvals"
    type: stat
    expr: asm_version_pending_approvals
    thresholds: [{value: 1, color: "red"}]
```

---

## mypy Checklist

| Pattern | mypy-clean? |
|---------|------------|
| `VersionCheckpoint` frozen dataclass | ✅ |
| `CompatibilityReport` frozen dataclass | ✅ |
| `VersionManagerConfig.__post_init__` guard | ✅ |
| `VersionManager` `@runtime_checkable` Protocol | ✅ |
| `LinearVersionManager` structural subtype | ✅ |
| `asyncio.Lock` in `__init__` | ✅ |
| `rollback_target` returns `VersionCheckpoint \| None` | ✅ |
| `tags: FrozenSet[str]` field | ✅ |
| `Mapping[str, str]` metadata field | ✅ |
| `HotSwapper.swap()` `version_manager` kwarg | ✅ |

---

## Test Targets (12)

| # | Test | Description |
|---|------|-------------|
| 1 | `test_record_checkpoint_basic` | Single module, single checkpoint recorded and retrievable |
| 2 | `test_record_checkpoint_trim` | Exceeds `max_checkpoints`, oldest trimmed correctly |
| 3 | `test_get_lineage_order` | Checkpoints returned in ascending version order |
| 4 | `test_latest_checkpoint_none` | Returns `None` for unknown module |
| 5 | `test_rollback_target_healthy` | Skips BREAKING, returns last COMPATIBLE |
| 6 | `test_rollback_target_single` | Only one checkpoint returns `None` |
| 7 | `test_assess_compatibility_stored` | Report indexed by `(module, from, to)` |
| 8 | `test_assess_compatibility_pending` | BREAKING + `require_approval=True` → pending queue |
| 9 | `test_pending_approvals_empty` | No BREAKING changes → empty list |
| 10 | `test_concurrent_record` | `asyncio.gather(20 record_checkpoint calls)` — no data corruption |
| 11 | `test_hotswapper_integration` | Mock HotSwapper calls `record_checkpoint` after COMMITTED swap |
| 12 | `test_stats` | All four stat keys match expected counts |

---

## Implementation Order (14 steps)

1. Define `CompatibilityLevel` and `RollbackReason` enums
2. Implement `VersionCheckpoint` frozen dataclass with `tags` frozenset
3. Implement `CompatibilityReport` frozen dataclass
4. Implement `VersionManagerConfig` with `__post_init__` guard
5. Define `VersionManager` `@runtime_checkable` Protocol
6. Implement `LinearVersionManager.__init__` with `asyncio.Lock`
7. Implement `record_checkpoint` with trim logic
8. Implement `get_lineage` and `latest_checkpoint`
9. Implement `rollback_target` (backwards walk, skip BREAKING)
10. Implement `assess_compatibility` with pending-queue logic + deduplication
11. Implement `pending_approvals` and `stats`/`reset`
12. Implement `make_version_manager` factory
13. Add `version_manager` parameter and `reject_breaking` config flag to `HotSwapper.swap()`
14. Wire `_version_manager` into `CognitiveCycle._synthesis_step()`

---

## Phase 15 Sub-Phase Tracker

| Sub-phase | Component | Issue | Discussions | Status |
|-----------|-----------|-------|-------------|--------|
| 15.1 | ModuleRegistry | [#401](https://github.com/web3guru888/asi-build/issues/401) | — | 🟡 spec filed |
| 15.2 | HotSwapper | [#402](https://github.com/web3guru888/asi-build/issues/402) | [#405](https://github.com/web3guru888/asi-build/discussions/405) · [#406](https://github.com/web3guru888/asi-build/discussions/406) | 🟡 spec filed |
| 15.3 | DependencyResolver | [#407](https://github.com/web3guru888/asi-build/issues/407) | [#408](https://github.com/web3guru888/asi-build/discussions/408) · [#409](https://github.com/web3guru888/asi-build/discussions/409) | 🟡 spec filed |
| **15.4** | **VersionManager** | [**#410**](https://github.com/web3guru888/asi-build/issues/410) | [**#411**](https://github.com/web3guru888/asi-build/discussions/411) · [**#412**](https://github.com/web3guru888/asi-build/discussions/412) | 🟡 **spec filed** |
| 15.5 | SelfModificationOrchestrator | — | — | ⏳ upcoming |
