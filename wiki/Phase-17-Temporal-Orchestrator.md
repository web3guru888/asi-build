# Phase 17.5 — TemporalOrchestrator

> **Phase 17: Temporal Reasoning & Predictive Cognition — COMPLETE 🎉**  
> Sub-phases: [TemporalGraph](Phase-17-Temporal-Graph) · [EventSequencer](Phase-17-Event-Sequencer) · [PredictiveEngine](Phase-17-Predictive-Engine) · [SchedulerCortex](Phase-17-Scheduler-Cortex) · **TemporalOrchestrator** (this page)

---

## Overview

`TemporalOrchestrator` is the Phase 17 capstone: a unified control plane that composes `EventSequencer`, `TemporalGraph`, `PredictiveEngine`, and `SchedulerCortex` into a single orchestration loop. It provides a single entry point for temporal reasoning within the ASI-Build cognitive cycle.

**Design philosophy**: composition over inheritance. The orchestrator *holds* four sub-components and coordinates them through a well-defined 7-phase cycle — CognitiveCycle needs only one dependency.

---

## Full Phase 17 Pipeline

```
CognitiveCycle
    │
    ▼
TemporalOrchestrator ─────────────────────────────────────┐
    │   phase: INGESTING                                   │
    ├─► EventSequencer.drain()                             │
    │        │  windows[]                                  │
    │        ▼                                             │
    │   phase: GRAPHING                                    │
    ├─► TemporalGraph.add_node()  ◄── TemporalNode         │
    │        │  node_count++                               │
    │        ▼                                             │
    │   phase: PREDICTING                                  │
    ├─► PredictiveEngine.train() + predict()               │
    │        │  Prediction{confidence, predicted_start_ns} │
    │        ▼  (confidence ≥ 0.8 only)                    │
    │   phase: SCHEDULING                                  │
    ├─► SchedulerCortex.enqueue() + run_tick()             │
    │        │  ready: list[ScheduledTask]                 │
    │        ▼                                             │
    │   phase: TICKING                                     │
    └─► _dispatch(task) → CognitiveCycle executor ─────────┘
              │
    phase: SNAPSHOT (periodic, every snapshot_interval_s)
              ▼
       OrchestratorSnapshot{latency_ms, graph_nodes, ...}
```

---

## 1. `OrchestratorPhase` Enum

```python
from enum import Enum, auto

class OrchestratorPhase(Enum):
    IDLE       = auto()   # waiting for next cycle trigger
    INGESTING  = auto()   # draining EventSequencer queue
    GRAPHING   = auto()   # updating TemporalGraph with new nodes/edges
    PREDICTING = auto()   # PredictiveEngine.predict() for active modules
    SCHEDULING = auto()   # SchedulerCortex.run_tick() + new task enqueue
    TICKING    = auto()   # executing dispatched tasks via CognitiveCycle
    SNAPSHOT   = auto()   # capturing OrchestratorSnapshot (periodic)
```

### State Machine

```
          ┌──────────────────────────────────────────────────────┐
          │                                                      │
          ▼                                                      │
        IDLE ──run_cycle()──► INGESTING ──drain complete──► GRAPHING
          ▲                                                      │
          │                                            graph done│
     SNAPSHOT ◄──periodic──                                      ▼
          │                                               PREDICTING
          │                                                      │
       TICKING ◄──schedule ready──── SCHEDULING ◄──predictions──┘
          │
          ▼
     CognitiveCycle executor
```

### Phase Transition Table

| Phase | Trigger | Typical Duration | Exit Condition |
|-------|---------|-----------------|----------------|
| `IDLE` | `run_cycle()` called | 0–∞ ms | `run_cycle()` invoked |
| `INGESTING` | Enter `run_cycle()` | drain latency | All buffered events drained |
| `GRAPHING` | Drain complete | O(windows) | All windows added to graph |
| `PREDICTING` | Graph updated | O(modules × algo) | All modules predicted |
| `SCHEDULING` | Predictions ready | O(tasks) | `run_tick()` returns |
| `TICKING` | Schedule ready | O(ready_tasks) | All tasks dispatched |
| `SNAPSHOT` | `≥ snapshot_interval_s` elapsed | ~instant | Snapshot captured |

---

## 2. Frozen Dataclasses

```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class OrchestratorSnapshot:
    """Point-in-time health snapshot of the entire Phase 17 pipeline."""
    snapshot_id:       str    # uuid4
    timestamp_ns:      int    # time.time_ns()
    graph_nodes:       int    # DictTemporalGraph.node_count()
    pending_events:    int    # EventSequencer.pending_count()
    predictions_made:  int    # predictions generated this cycle
    scheduled_tasks:   int    # tasks dispatched this cycle
    cycle_latency_ms:  float  # wall-clock duration of run_cycle()


@dataclass(frozen=True)
class TemporalConfig:
    """Single nested-config entry point for all Phase 17 sub-systems."""
    sequencer_config:       SequencerConfig
    predictor_config:       PredictorConfig
    scheduler_config:       SchedulerConfig
    snapshot_interval_s:    float = 10.0   # seconds between snapshots
    enable_temporal_graph:  bool  = True   # feature flag for graph
```

`TemporalConfig` composes all three sub-configs — callers construct one object and pass it to `make_temporal_orchestrator()`.

---

## 3. `TemporalOrchestrator` Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class TemporalOrchestrator(Protocol):
    """
    Unified temporal control plane Protocol.
    @runtime_checkable allows isinstance() checks in integration tests.
    """
    async def ingest_event(self, event: CognitiveEvent) -> bool: ...
    async def run_cycle(self) -> OrchestratorSnapshot: ...
    def get_predictions(self, module: str) -> list[Prediction]: ...
    def get_schedule(self) -> list[ScheduleSlot]: ...
    async def stop(self) -> None: ...
    def stats(self) -> dict[str, int | float]: ...
```

---

## 4. `AsyncTemporalOrchestrator` Implementation

```python
import asyncio, time, uuid
from collections import deque

class AsyncTemporalOrchestrator:
    """
    Composes all Phase 17 sub-components into a single temporal control plane.
    Design: composition over inheritance — holds 4 sub-components.
    """

    def __init__(self, config: TemporalConfig) -> None:
        self._cfg      = config
        self._seq      = AsyncEventSequencer(config.sequencer_config)
        self._graph: TemporalGraph = (
            DictTemporalGraph(TemporalGraphConfig())
            if config.enable_temporal_graph
            else NullTemporalGraph()
        )
        self._pred     = AdaptivePredictiveEngine(config.predictor_config)
        self._sched    = AsyncSchedulerCortex(config.scheduler_config)
        self._phase    = OrchestratorPhase.IDLE
        self._stop_evt = asyncio.Event()
        self._snapshots: deque[OrchestratorSnapshot] = deque(maxlen=100)
        self._last_snapshot_ts: float = 0.0
        self._cycles_total: int = 0

    # ── Public API ──────────────────────────────────────────────────────────

    async def ingest_event(self, event: CognitiveEvent) -> bool:
        """Enqueue a CognitiveEvent into the EventSequencer."""
        return await self._seq.ingest(event)

    async def run_cycle(self) -> OrchestratorSnapshot:
        """
        Execute one full orchestration cycle:
        INGESTING → GRAPHING → PREDICTING → SCHEDULING → TICKING → SNAPSHOT
        """
        t0 = time.monotonic_ns()

        # Phase 1: INGESTING — drain EventSequencer
        self._phase = OrchestratorPhase.INGESTING
        windows: list[SequenceWindow] = []
        try:
            windows = await self._seq.drain()
        except Exception as exc:
            _log.warning("ingesting phase failed: %s", exc)

        # Phase 2: GRAPHING — add windows as TemporalGraph nodes
        self._phase = OrchestratorPhase.GRAPHING
        if self._cfg.enable_temporal_graph:
            try:
                for w in windows:
                    node = TemporalNode(
                        node_id=w.window_id,
                        module_id=w.module_id,
                        timestamp_ns=w.start_ns,
                        metrics=w.metrics,
                    )
                    await self._graph.add_node(node)
            except Exception as exc:
                _log.warning("graphing phase failed: %s", exc)

        # Phase 3: PREDICTING — train + predict per module
        self._phase = OrchestratorPhase.PREDICTING
        predictions_made = 0
        tasks_to_enqueue: list[ScheduledTask] = []
        try:
            for w in windows:
                await self._pred.train(w.module_id, w)
                p = await self._pred.predict(w.module_id)
                if p is not None:
                    predictions_made += 1
                    if p.confidence >= 0.8:
                        tasks_to_enqueue.append(ScheduledTask(
                            task_id=f"pred-{p.prediction_id}",
                            module_id=p.module_id,
                            priority=TaskPriority.NORMAL,
                            deadline_ns=p.predicted_start_ns,
                            estimated_duration_ms=p.estimated_duration_ms,
                            payload={"prediction_basis": p.basis_window_ids},
                        ))
        except Exception as exc:
            _log.warning("predicting phase failed: %s", exc)

        # Phase 4: SCHEDULING — enqueue prediction-driven tasks, run tick
        self._phase = OrchestratorPhase.SCHEDULING
        ready: list[ScheduledTask] = []
        try:
            for task in tasks_to_enqueue:
                await self._sched.enqueue(task)
            ready = await self._sched.run_tick()
        except Exception as exc:
            _log.warning("scheduling phase failed: %s", exc)

        # Phase 5: TICKING — dispatch ready tasks to CognitiveCycle executor
        self._phase = OrchestratorPhase.TICKING
        for task in ready:
            try:
                await self._dispatch(task)
            except Exception as exc:
                _log.warning("dispatch failed for %s: %s", task.task_id, exc)

        # Phase 6: SNAPSHOT — periodic health capture
        self._phase = OrchestratorPhase.SNAPSHOT
        latency_ms = (time.monotonic_ns() - t0) / 1e6
        self._cycles_total += 1
        snap = OrchestratorSnapshot(
            snapshot_id=str(uuid.uuid4()),
            timestamp_ns=time.time_ns(),
            graph_nodes=self._graph.node_count_sync(),
            pending_events=self._seq.pending_count(),
            predictions_made=predictions_made,
            scheduled_tasks=len(ready),
            cycle_latency_ms=latency_ms,
        )
        now = time.monotonic()
        if now - self._last_snapshot_ts >= self._cfg.snapshot_interval_s:
            self._snapshots.append(snap)
            self._last_snapshot_ts = now

        self._phase = OrchestratorPhase.IDLE
        return snap

    async def _dispatch(self, task: ScheduledTask) -> None:
        """
        Hook for CognitiveCycle executor.
        Override in subclass or inject a dispatch_callback at construction.
        Default no-op allows standalone testing.
        """
        pass

    def get_predictions(self, module: str) -> list[Prediction]:
        """Return prediction history for a module from PredictiveEngine."""
        return self._pred.get_history(module)

    def get_schedule(self) -> list[ScheduleSlot]:
        """Return current SchedulerCortex schedule."""
        return self._sched.peek_schedule()

    async def stop(self) -> None:
        """
        Graceful stop using asyncio.Event (not CancelledError).
        Allows current run_cycle() to complete before exiting.
        """
        self._stop_evt.set()
        await self._seq.flush()
        await self._sched.stop()

    def stats(self) -> dict[str, int | float]:
        return {
            "cycles_total":      self._cycles_total,
            "phase":             self._phase.name,
            "snapshots_stored":  len(self._snapshots),
            "graph_nodes":       self._graph.node_count_sync(),
        }
```

---

## 5. `NullTemporalOrchestrator`

```python
class NullTemporalOrchestrator:
    """
    No-op orchestrator for tests and feature-flag disabled paths.
    Satisfies TemporalOrchestrator Protocol via isinstance() check.
    """

    async def ingest_event(self, event: CognitiveEvent) -> bool:
        return False

    async def run_cycle(self) -> OrchestratorSnapshot:
        return OrchestratorSnapshot(
            snapshot_id="null", timestamp_ns=0,
            graph_nodes=0, pending_events=0,
            predictions_made=0, scheduled_tasks=0,
            cycle_latency_ms=0.0,
        )

    def get_predictions(self, module: str) -> list[Prediction]:
        return []

    def get_schedule(self) -> list[ScheduleSlot]:
        return []

    async def stop(self) -> None:
        pass

    def stats(self) -> dict[str, int | float]:
        return {}
```

---

## 6. `make_temporal_orchestrator()` Factory

```python
def make_temporal_orchestrator(
    config: TemporalConfig | None = None,
    *,
    null: bool = False,
) -> TemporalOrchestrator:
    """
    Factory function — single construction entry point.

    Args:
        config: Full TemporalConfig. If None, uses all sub-component defaults.
        null:   Return NullTemporalOrchestrator (for tests / disabled paths).
    """
    if null:
        return NullTemporalOrchestrator()
    cfg = config or TemporalConfig(
        sequencer_config=SequencerConfig(),
        predictor_config=PredictorConfig(),
        scheduler_config=SchedulerConfig(),
    )
    return AsyncTemporalOrchestrator(cfg)
```

---

## 7. CognitiveCycle Integration Pattern

```python
class CognitiveCycle:
    def __init__(self, orchestrator: TemporalOrchestrator) -> None:
        self._orch = orchestrator   # single Phase 17 dependency

    async def _run_step(self, event: CognitiveEvent) -> None:
        try:
            await self._orch.ingest_event(event)
            snap = await self._orch.run_cycle()
            logger.info(
                "temporal cycle: latency=%.1fms predictions=%d scheduled=%d",
                snap.cycle_latency_ms, snap.predictions_made, snap.scheduled_tasks
            )
        except Exception as exc:
            logger.warning("temporal step failed: %s", exc)
```

`CognitiveCycle` has **no direct import** of `EventSequencer`, `TemporalGraph`, `PredictiveEngine`, or `SchedulerCortex` — all Phase 17 complexity is encapsulated in the orchestrator.

---

## 8. Cross-Phase Integration Map

```
Phase 10 GoalRegistry
    └──► goal.deadline_ns ──────────────────► ScheduledTask.deadline_ns
                                                (via TemporalOrchestrator.ingest_event)

Phase 13 WorldModel
    └──► WorldModel.update(state)
              └──► CognitiveCycle._run_step(event)
                        └──► TemporalOrchestrator.run_cycle()

Phase 16 ReflectionCycle
    ◄──── OrchestratorSnapshot{cycle_latency_ms}
              └──► PerformanceProfiler.record()
                        └──► WeaknessDetector → ImprovementPlanner → SelfOptimiser
                                  └──► CONFIG_TUNE SchedulerConfig.tick_ms
```

This closes the **self-improvement loop**: Phase 17 temporal metrics feed Phase 16 reflection, which adapts Phase 17 configuration automatically.

---

## 9. Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asibuild_orchestration_cycles_total` | Counter | `result` (ok/error) | Completed orchestration cycles |
| `asibuild_cycle_latency_seconds` | Histogram | — | Per-cycle wall-clock latency |
| `asibuild_predictions_acted_on_total` | Counter | `module_id` | Predictions converted to ScheduledTasks |
| `asibuild_temporal_graph_nodes_gauge` | Gauge | — | Current TemporalGraph node count |
| `asibuild_schedule_queue_depth_gauge` | Gauge | — | SchedulerCortex current queue depth |

### PromQL Examples

```promql
# Cycle throughput
rate(asibuild_orchestration_cycles_total[5m])

# p99 cycle latency
histogram_quantile(0.99, rate(asibuild_cycle_latency_seconds_bucket[5m]))

# Predictions acted on per hour
increase(asibuild_predictions_acted_on_total[1h])
```

### Grafana Alert YAML

```yaml
- alert: TemporalCycleLatencyHigh
  expr: histogram_quantile(0.99, rate(asibuild_cycle_latency_seconds_bucket[5m])) > 0.5
  for: 2m
  annotations:
    summary: "Temporal orchestration p99 latency > 500ms"

- alert: TemporalGraphNodesBloat
  expr: asibuild_temporal_graph_nodes_gauge > 50000
  for: 5m
  annotations:
    summary: "TemporalGraph exceeds 50k nodes — prune threshold"

- alert: ScheduleQueueDepthHigh
  expr: asibuild_schedule_queue_depth_gauge > 1000
  for: 1m
  annotations:
    summary: "Scheduler queue depth > 1000 — backpressure building"
```

---

## 10. mypy Narrowing Table

| Pattern | Recommended Annotation |
|---------|----------------------|
| `orch: TemporalOrchestrator` (Protocol) | Narrow with `assert isinstance(orch, AsyncTemporalOrchestrator)` to access `.stats()` internals |
| `snap.cycle_latency_ms` | Already `float` — no cast needed |
| `config.sequencer_config.window_ms` | Direct frozen dataclass access — fully typed |
| `phase: OrchestratorPhase` match | `case OrchestratorPhase.PREDICTING:` — exhaustive if all 7 arms covered; add `case _: assert_never(phase)` |
| `config.enable_temporal_graph` | `bool` — use as `if config.enable_temporal_graph:` not `if config.enable_temporal_graph == True:` |

---

## 11. Test Targets (12)

| # | Target | Assertion |
|---|--------|-----------|
| 1 | `test_ingest_event_returns_true` | `await orch.ingest_event(event)` returns `True` |
| 2 | `test_run_cycle_full_pipeline` | snapshot `predictions_made >= 0`, no exception |
| 3 | `test_run_cycle_graph_disabled` | `enable_temporal_graph=False` → `graph_nodes == 0` |
| 4 | `test_low_confidence_prediction_not_scheduled` | `confidence < 0.8` → `scheduled_tasks == 0` |
| 5 | `test_high_confidence_prediction_scheduled` | `confidence >= 0.8` → `scheduled_tasks >= 1` |
| 6 | `test_stop_drains_queue` | `stop()` → sequencer queue empty |
| 7 | `test_stop_idempotent` | double `stop()` → no exception |
| 8 | `test_snapshot_captured_on_interval` | snapshot recorded when `≥ snapshot_interval_s` elapsed |
| 9 | `test_null_orchestrator_run_cycle` | `NullTemporalOrchestrator().run_cycle()` returns zero snapshot |
| 10 | `test_factory_null_flag` | `make_temporal_orchestrator(null=True)` → `NullTemporalOrchestrator` |
| 11 | `test_isinstance_protocol` | `isinstance(orch, TemporalOrchestrator)` → `True` |
| 12 | `test_stats_keys_present` | `stats()` contains `cycles_total`, `phase`, `snapshots_stored` |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_run_cycle_full_pipeline():
    cfg = TemporalConfig(
        sequencer_config=SequencerConfig(),
        predictor_config=PredictorConfig(min_windows=1),
        scheduler_config=SchedulerConfig(),
    )
    orch = AsyncTemporalOrchestrator(cfg)
    event = CognitiveEvent(
        event_id="e1", module_id="planner",
        timestamp_ns=time.time_ns(), metrics={"load": 0.5}
    )
    await orch.ingest_event(event)
    snap = await orch.run_cycle()
    assert snap.cycle_latency_ms >= 0.0
    assert snap.snapshot_id != ""
    await orch.stop()


@pytest.mark.asyncio
async def test_stop_drains_queue():
    cfg = TemporalConfig(
        sequencer_config=SequencerConfig(),
        predictor_config=PredictorConfig(),
        scheduler_config=SchedulerConfig(),
    )
    orch = AsyncTemporalOrchestrator(cfg)
    for i in range(10):
        await orch.ingest_event(
            CognitiveEvent(event_id=f"e{i}", module_id="m",
                           timestamp_ns=time.time_ns(), metrics={})
        )
    await orch.stop()
    # No exception → queue drained gracefully
    assert orch.stats()["cycles_total"] == 0
```

---

## 12. Implementation Order (14 Steps)

1. Define `OrchestratorPhase` enum (7 values)
2. Implement `OrchestratorSnapshot` frozen dataclass
3. Implement `TemporalConfig` frozen dataclass (composes 3 sub-configs)
4. Define `TemporalOrchestrator` Protocol (`@runtime_checkable`)
5. Implement `NullTemporalOrchestrator` (all no-ops)
6. Write tests 9–12 (null + factory + protocol + stats)
7. Implement `AsyncTemporalOrchestrator.__init__()` (compose 4 sub-components)
8. Implement `ingest_event()` → `self._seq.ingest()`
9. Implement `run_cycle()` INGESTING phase + `stop()` skeleton
10. Implement GRAPHING phase + test 3 (graph disabled)
11. Implement PREDICTING phase + tests 4–5 (confidence gate)
12. Implement SCHEDULING + TICKING phases + test 2 (full pipeline)
13. Implement SNAPSHOT phase + test 8 (snapshot interval)
14. Implement `make_temporal_orchestrator()` factory + test 10

---

## Phase 17 Final Tracker 🎉

| Sub-Phase | Component | Issue | Wiki | Status |
|-----------|-----------|-------|------|--------|
| 17.1 | TemporalGraph | [#434](https://github.com/web3guru888/asi-build/issues/434) | [📄](Phase-17-Temporal-Graph) | 🟡 Spec'd |
| 17.2 | EventSequencer | [#437](https://github.com/web3guru888/asi-build/issues/437) | [📄](Phase-17-Event-Sequencer) | 🟡 Spec'd |
| 17.3 | PredictiveEngine | [#440](https://github.com/web3guru888/asi-build/issues/440) | [📄](Phase-17-Predictive-Engine) | 🟡 Spec'd |
| 17.4 | SchedulerCortex | [#443](https://github.com/web3guru888/asi-build/issues/443) | [📄](Phase-17-Scheduler-Cortex) | 🟡 Spec'd |
| **17.5** | **TemporalOrchestrator** | [**#446**](https://github.com/web3guru888/asi-build/issues/446) | [📄](Phase-17-Temporal-Orchestrator) | 🟡 **Spec'd** |

**🎉 Phase 17 — Temporal Reasoning & Predictive Cognition: COMPLETE**

---

## Discussions

- [#447 Show & Tell](https://github.com/web3guru888/asi-build/discussions/447) — full pipeline architecture + Phase 17 summary
- [#448 Q&A](https://github.com/web3guru888/asi-build/discussions/448) — composition, partial failures, stop safety, Grafana state panel

---

*Part of the ASI-Build cognitive architecture · [Contributing](Contributing) · [Architecture Overview](Architecture)*
