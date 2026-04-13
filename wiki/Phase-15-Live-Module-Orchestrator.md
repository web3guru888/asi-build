# Phase 15.5 — `LiveModuleOrchestrator`

> **Phase 15 — Self-Modifying Runtime** | Sub-phase 5 of 5 | **Phase 15 COMPLETE 🎉**
>
> Unified control-plane composing ModuleRegistry + HotSwapper + DependencyResolver + VersionManager into a single async pipeline for live module updates.

---

## Enums

```python
from enum import Enum, auto

class OrchestratorState(Enum):
    IDLE     = auto()   # no swaps running
    BUSY     = auto()   # swap(s) in flight
    DRAINING = auto()   # shutdown requested, waiting for completion
    STOPPED  = auto()   # fully shut down

class SwapOutcome(Enum):
    SUCCESS    = auto()  # committed by HotSwapper
    REJECTED   = auto()  # blocked by VersionManager (BREAKING + require_approval)
    DEP_FAILED = auto()  # DependencyResolver returned CYCLIC or MISSING
    SWAP_ERROR = auto()  # HotSwapper raised / returned ROLLED_BACK or FAILED
    SHUTDOWN   = auto()  # arrived during DRAINING
```

---

## Frozen dataclasses

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet
import time

@dataclass(frozen=True)
class OrchestratorRequest:
    module_id:    str
    new_code:     bytes              # compiled or source bytes
    new_version:  str                # semver string, e.g. "2.1.0"
    tags:         FrozenSet[str] = field(default_factory=frozenset)
    requester:    str = "cognitive_cycle"
    requested_at: float = field(default_factory=time.monotonic)

@dataclass(frozen=True)
class OrchestratorResult:
    request:     OrchestratorRequest
    outcome:     SwapOutcome
    detail:      str                  # human-readable reason / success message
    duration_s:  float                # wall-clock seconds for full pipeline
    swap_result: object | None = None # HotSwapper SwapResult if swap reached that stage

@dataclass(frozen=True)
class OrchestratorConfig:
    max_concurrent_swaps:          int   = 4
    require_approval_for_breaking: bool  = True
    auto_rollback:                 bool  = True
    shutdown_timeout_s:            float = 30.0
    log_every_swap:                bool  = True
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LiveModuleOrchestrator(Protocol):
    async def orchestrate_swap(self, req: OrchestratorRequest) -> OrchestratorResult: ...
    async def orchestrate_batch(self, reqs: list[OrchestratorRequest]) -> list[OrchestratorResult]: ...
    async def shutdown(self) -> None: ...
    def state(self) -> OrchestratorState: ...
    def stats(self) -> dict[str, int | float]: ...
```

---

## `AsyncLiveOrchestrator` — reference implementation

```python
import asyncio, logging, time
from collections import defaultdict
from prometheus_client import Counter, Gauge, Histogram

log = logging.getLogger("asi_build.live_orchestrator")

class AsyncLiveOrchestrator:
    """
    Composes ModuleRegistry + HotSwapper + DependencyResolver + VersionManager
    into a single async control-plane for live module swaps.
    """

    def __init__(
        self,
        registry:  ModuleRegistry,
        swapper:   HotSwapper,
        resolver:  DependencyResolver,
        versioner: VersionManager,
        config:    OrchestratorConfig | None = None,
    ) -> None:
        self._registry  = registry
        self._swapper   = swapper
        self._resolver  = resolver
        self._versioner = versioner
        self._cfg       = config or OrchestratorConfig()
        self._sem       = asyncio.Semaphore(self._cfg.max_concurrent_swaps)
        self._state     = OrchestratorState.IDLE
        self._in_flight: set[asyncio.Task] = set()
        self._counters  = defaultdict(int)

    # --- public API -------------------------------------------------------

    async def orchestrate_swap(self, req: OrchestratorRequest) -> OrchestratorResult:
        if self._state in (OrchestratorState.DRAINING, OrchestratorState.STOPPED):
            return OrchestratorResult(req, SwapOutcome.SHUTDOWN, "orchestrator is shutting down", 0.0)
        self._state = OrchestratorState.BUSY
        async with self._sem:
            result = await self._pipeline(req)
        self._counters[result.outcome.name] += 1
        if self._state == OrchestratorState.BUSY and self._sem._value == self._cfg.max_concurrent_swaps:
            self._state = OrchestratorState.IDLE
        return result

    async def orchestrate_batch(self, reqs: list[OrchestratorRequest]) -> list[OrchestratorResult]:
        return list(await asyncio.gather(*(self.orchestrate_swap(r) for r in reqs)))

    async def shutdown(self) -> None:
        self._state = OrchestratorState.DRAINING
        deadline = time.monotonic() + self._cfg.shutdown_timeout_s
        while self._in_flight and time.monotonic() < deadline:
            await asyncio.sleep(0.1)
        self._state = OrchestratorState.STOPPED
        log.info("LiveModuleOrchestrator stopped; in-flight tasks: %d", len(self._in_flight))

    def state(self) -> OrchestratorState:
        return self._state

    def stats(self) -> dict[str, int | float]:
        return {
            "state":     self._state.name,
            "in_flight": len(self._in_flight),
            "sem_slots": self._sem._value,
            **{f"outcome_{k}": v for k, v in self._counters.items()},
        }

    # --- internal pipeline ------------------------------------------------

    async def _pipeline(self, req: OrchestratorRequest) -> OrchestratorResult:
        t0 = time.monotonic()

        # 1. Dependency resolution
        dep_result = await self._resolver.resolve(req.module_id)
        match dep_result.status:
            case ResolutionStatus.CYCLIC:
                return self._result(req, SwapOutcome.DEP_FAILED,
                                    f"cyclic dependency: {dep_result.cycle_path}", t0)
            case ResolutionStatus.MISSING if self._cfg.require_approval_for_breaking:
                return self._result(req, SwapOutcome.DEP_FAILED,
                                    f"missing deps: {dep_result.missing}", t0)

        # 2. Version compatibility check
        compat = await self._versioner.assess_compatibility(req.module_id, req.new_version)
        if compat.level == CompatibilityLevel.BREAKING and self._cfg.require_approval_for_breaking:
            await self._versioner.pending_approvals()
            return self._result(req, SwapOutcome.REJECTED,
                                f"BREAKING change requires approval "
                                f"({compat.from_version}→{compat.to_version})", t0)

        # 3. Register new version in ModuleRegistry (STAGED)
        mv = ModuleVersion(
            module_id=req.module_id,
            version=req.new_version,
            checksum=_sha256(req.new_code),
            tags=req.tags,
        )
        await self._registry.register(mv)

        # 4. Execute hot-swap
        swap_req = SwapRequest(
            module_id=req.module_id,
            old_version=compat.from_version or "unknown",
            new_version=req.new_version,
            new_code=req.new_code,
        )
        swap_res = await self._swapper.swap(swap_req, version_manager=self._versioner)

        match swap_res.phase:
            case SwapPhase.COMMITTED:
                await self._registry.set_status(req.module_id, req.new_version, ModuleStatus.ACTIVE)
                await self._versioner.record_checkpoint(req.module_id, req.new_version, tags=req.tags)
                if self._cfg.log_every_swap:
                    log.info("swap COMMITTED module=%s version=%s", req.module_id, req.new_version)
                return self._result(req, SwapOutcome.SUCCESS, "committed", t0, swap_res)
            case _:
                await self._registry.set_status(req.module_id, req.new_version, ModuleStatus.REVERTED)
                return self._result(req, SwapOutcome.SWAP_ERROR,
                                    f"swap ended in {swap_res.phase.name}: {swap_res.error}", t0, swap_res)

    @staticmethod
    def _result(req, outcome, detail, t0, swap_res=None):
        return OrchestratorResult(req, outcome, detail, time.monotonic() - t0, swap_res)


def _sha256(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def make_orchestrator(
    registry:  ModuleRegistry,
    swapper:   HotSwapper,
    resolver:  DependencyResolver,
    versioner: VersionManager,
    config:    OrchestratorConfig | None = None,
) -> LiveModuleOrchestrator:
    return AsyncLiveOrchestrator(registry, swapper, resolver, versioner, config)
```

---

## Version lifecycle / state machine

```
OrchestratorState transitions:

  IDLE ──(first swap arrives)──► BUSY
  BUSY ──(all swaps complete)──► IDLE
  BUSY/IDLE ──(shutdown())────► DRAINING
  DRAINING ──(drained)────────► STOPPED
  DRAINING/STOPPED ──(new req)─► SHUTDOWN outcome (immediate return)
```

---

## SwapOutcome table

| Outcome | Trigger | CognitiveCycle action |
|---|---|---|
| `SUCCESS` | HotSwapper committed | log info, continue |
| `REJECTED` | BREAKING + approval required | log warning + trigger replan |
| `DEP_FAILED` | cyclic or missing deps | log error + trigger replan |
| `SWAP_ERROR` | swapper rolled back / raised | log error + trigger replan |
| `SHUTDOWN` | orchestrator DRAINING/STOPPED | log critical, defer |

---

## Full pipeline data flow ASCII

```
Patch (from Phase 14 PatchSelector)
  │
  ▼
CognitiveCycle._synthesis_step(patch)
  │  builds OrchestratorRequest(module_id, new_code, new_version, tags)
  ▼
LiveModuleOrchestrator.orchestrate_swap(req)
  │
  ├─[Semaphore gate: max_concurrent_swaps]
  │
  ├─→ DependencyResolver.resolve(module_id)
  │     returns ResolutionResult{status, order, cycle_path, missing}
  │     CYCLIC/MISSING → DEP_FAILED ───────────────────────────────► return
  │
  ├─→ VersionManager.assess_compatibility(module_id, new_version)
  │     returns CompatibilityReport{level, from_version, to_version}
  │     BREAKING + require_approval → REJECTED ──────────────────── ► return
  │
  ├─→ ModuleRegistry.register(ModuleVersion{STAGED})
  │
  ├─→ HotSwapper.swap(SwapRequest, version_manager=versioner)
  │     COMMITTED ──→ ModuleRegistry.set_status(ACTIVE)
  │                   VersionManager.record_checkpoint()
  │                   → SUCCESS ──────────────────────────────────► return
  │     ROLLED_BACK / FAILED ──→ ModuleRegistry.set_status(REVERTED)
  │                              → SWAP_ERROR ────────────────────► return
  │
  ▼
OrchestratorResult{outcome, detail, duration_s, swap_result}
```

---

## CognitiveCycle integration

```python
# cognitive_cycle.py
class CognitiveCycle:
    def __init__(self, ..., orchestrator: LiveModuleOrchestrator | None = None):
        ...
        self._orchestrator = orchestrator

    async def _synthesis_step(self, patch: Patch) -> None:
        if self._orchestrator is None:
            return  # orchestrator optional; falls back to direct swap
        req = OrchestratorRequest(
            module_id   = patch.module_id,
            new_code    = patch.code_bytes,
            new_version = patch.version,
            tags        = frozenset(patch.tags),
            requester   = "synthesis_step",
        )
        result = await self._orchestrator.orchestrate_swap(req)
        match result.outcome:
            case SwapOutcome.SUCCESS:
                log.info("live swap succeeded: %s@%s", req.module_id, req.new_version)
            case SwapOutcome.REJECTED:
                log.warning("swap queued for approval: %s", result.detail)
                await self._trigger_replan(reason=result.detail)
            case _:
                log.error("swap failed (%s): %s", result.outcome.name, result.detail)
                await self._trigger_replan(reason=result.detail)
```

---

## Prometheus metrics

| Metric | Type | Description |
|---|---|---|
| `asi_orchestrator_swaps_total{outcome}` | Counter | swap outcomes by SwapOutcome |
| `asi_orchestrator_in_flight` | Gauge | current concurrent swaps |
| `asi_orchestrator_pipeline_seconds` | Histogram | end-to-end pipeline latency |
| `asi_orchestrator_dep_failures_total` | Counter | dependency-resolution failures |
| `asi_orchestrator_rejections_total` | Counter | version-compatibility rejections |

```promql
# swap success rate (5-min window)
rate(asi_orchestrator_swaps_total{outcome="SUCCESS"}[5m])
/ rate(asi_orchestrator_swaps_total[5m])
```

```yaml
# Grafana alert — high error rate
expr: |
  rate(asi_orchestrator_swaps_total{outcome=~"SWAP_ERROR|DEP_FAILED"}[5m])
  / rate(asi_orchestrator_swaps_total[5m]) > 0.1
for: 2m
labels: { severity: critical }
annotations:
  summary: "LiveModuleOrchestrator high error rate"
  description: "Check DependencyResolver cycles and HotSwapper sandbox logs."
```

---

## mypy strict compatibility

| Symbol | Notes |
|---|---|
| `OrchestratorRequest` | frozen dataclass, all fields typed |
| `OrchestratorResult` | `swap_result: object \| None` — narrow to `SwapResult \| None` once import cycle resolved |
| `AsyncLiveOrchestrator` | satisfies `LiveModuleOrchestrator` Protocol via structural subtyping |
| `_pipeline` | explicit `OrchestratorResult` return; add `case _: assert_never(swap_res.phase)` |
| `make_orchestrator` | return type annotated as `LiveModuleOrchestrator` |

---

## Test targets (12)

| # | Test | Verifies |
|---|---|---|
| 1 | `test_success_pipeline` | resolve OK → compat COMPATIBLE → swap COMMITTED → SUCCESS |
| 2 | `test_dep_cyclic_rejected` | resolver CYCLIC → DEP_FAILED, swap never called |
| 3 | `test_dep_missing_rejected` | resolver MISSING + strict → DEP_FAILED |
| 4 | `test_breaking_requires_approval` | CompatibilityLevel.BREAKING → REJECTED, pending logged |
| 5 | `test_swap_error_reverts_registry` | swap ROLLED_BACK → SWAP_ERROR + registry REVERTED |
| 6 | `test_batch_concurrent` | `orchestrate_batch(10)` → all return, semaphore respected |
| 7 | `test_shutdown_drains` | shutdown() waits for in-flight, then STOPPED |
| 8 | `test_shutdown_rejects_new` | DRAINING → immediate SHUTDOWN outcome |
| 9 | `test_stats_counters` | 3 success + 1 error → counters correct |
| 10 | `test_registry_set_active_on_success` | registry.set_status(ACTIVE) called on commit |
| 11 | `test_registry_set_reverted_on_error` | registry.set_status(REVERTED) on swap fail |
| 12 | `test_versioner_checkpoint_recorded` | versioner.record_checkpoint called on SUCCESS |

---

## Implementation order (14 steps)

1. Add `OrchestratorState` and `SwapOutcome` enums to `enums.py`
2. Define `OrchestratorRequest`, `OrchestratorResult`, `OrchestratorConfig` frozen dataclasses
3. Define `LiveModuleOrchestrator` Protocol (`@runtime_checkable`)
4. Implement `AsyncLiveOrchestrator.__init__` (inject 4 sub-components + Semaphore)
5. Implement `_pipeline` — dep resolution stage (CYCLIC/MISSING guard)
6. Implement `_pipeline` — version compatibility gate (BREAKING guard)
7. Implement `_pipeline` — registry register stage (STAGED)
8. Implement `_pipeline` — hot-swap execution + match dispatch (COMMITTED/ROLLED_BACK)
9. Implement `orchestrate_swap` (state machine + semaphore + outcome counter)
10. Implement `orchestrate_batch` (asyncio.gather)
11. Implement `shutdown` (drain loop + STOPPED transition)
12. Implement `stats` / `state` accessors
13. Register 5 Prometheus metrics; instrument `_pipeline` with Histogram
14. Wire `CognitiveCycle._synthesis_step` to use `orchestrator` if injected

---

## Phase 15 sub-phase tracker

| Sub-phase | Component | Issue | Discussions | Status |
|---|---|---|---|---|
| 15.1 | ModuleRegistry | #401 | — | 🟡 spec filed |
| 15.2 | HotSwapper | #402 | #405 #406 | 🟡 spec filed |
| 15.3 | DependencyResolver | #407 | #408 #409 | 🟡 spec filed |
| 15.4 | VersionManager | #410 | #411 #412 | 🟡 spec filed |
| 15.5 | **LiveModuleOrchestrator** | **#413** | **#414 #415** | 🟡 **spec filed** |

**Phase 15 — Self-Modifying Runtime: ALL SUB-PHASES SPEC filed 🎉**

---

*Part of the [ASI-Build roadmap](Architecture-Overview). Next: Phase 16 planning.*
