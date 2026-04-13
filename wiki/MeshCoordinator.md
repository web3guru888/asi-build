# MeshCoordinator

> **Status**: Design complete (Issue [#169](https://github.com/web3guru888/asi-build/issues/169))  
> **Phase**: 4.2 — Multi-Agent Orchestration  
> **Depends on**: AgentMesh ([#147](https://github.com/web3guru888/asi-build/issues/147)), AgentDiscovery ([#150](https://github.com/web3guru888/asi-build/issues/150)), MeshTaskQueue ([#154](https://github.com/web3guru888/asi-build/issues/154)), MeshResultAggregator ([#168](https://github.com/web3guru888/asi-build/issues/168))

`MeshCoordinator` is the **top-level entry point** for ASI:BUILD's multi-agent runtime. It composes `AgentDiscovery`, `MeshTaskQueue`, `MeshResultAggregator`, and `MeshDispatcher` into a single coherent API that `CognitiveCycle` can call with a single `await`.

---

## Why We Need It

The four Phase 4.2 components each solve a distinct problem:

| Component | Responsibility |
|---|---|
| `AgentDiscovery` | Registry: which agents exist, their state, load, capabilities |
| `MeshTaskQueue` | Dispatch: priority queueing, retry, dead-letter |
| `MeshResultAggregator` | Collection: gather N results, merge, write to Blackboard |
| `MeshDispatcher` | Execution: pull tasks from queue, invoke agents |

Without `MeshCoordinator`, a caller (like `CognitiveCycle`) would need to orchestrate all four components manually — 4 separate API calls, lifecycle management, error handling, and background task tracking.

`MeshCoordinator` hides this complexity behind three public methods: `start()`, `run_task()`, and `stop()`.

---

## Architecture Diagram

```
CognitiveCycle.tick()
       │
       ▼
  MeshCoordinator.run_task(task)
       │
       ├─► AgentDiscovery.find_agents(role, capability, state=HEALTHY)
       │         │
       │         └── returns list[AgentSpec]
       │
       ├─► MeshResultAggregator.register_task(task_id, agent_count)
       │
       ├─► MeshTaskQueue.enqueue(task, agent_id)  ─── (× N agents)
       │         │
       │         └── MeshDispatcher.run()  [background task]
       │                   │
       │                   ├─ invoke agent A  ──► aggregator.submit_result()
       │                   ├─ invoke agent B  ──► aggregator.submit_result()
       │                   └─ invoke agent C  ──► aggregator.submit_result()
       │
       └─► MeshResultAggregator.wait_for(task_id)
                 │
                 └── returns AggregatedResult ──► Blackboard write
```

---

## Class Design

```python
class MeshCoordinator:
    """Top-level multi-agent runtime coordinator.

    Lifecycle:
        coordinator = MeshCoordinator(blackboard=bb)
        await coordinator.start()       # starts dispatcher + health sweep
        result = await coordinator.run_task(task)
        await coordinator.stop()        # drains queue, cancels background tasks
    """

    def __init__(
        self,
        blackboard: CognitiveBlackboard,
        strategy: AggregationStrategy = AggregationStrategy.BEST_EFFORT,
        quorum_n: int = 1,
        dispatch_timeout_ms: float = 5000.0,
        max_queue_depth: int = 256,
    ) -> None:
        self._discovery = AgentDiscovery()
        self._queue = MeshTaskQueue(max_size=max_queue_depth)
        self._aggregator = MeshResultAggregator(
            strategy=strategy,
            quorum_n=quorum_n,
            timeout_ms=dispatch_timeout_ms,
            blackboard=blackboard,
        )
        self._dispatcher = MeshDispatcher(
            queue=self._queue,
            discovery=self._discovery,
            aggregator=self._aggregator,
        )
        self._blackboard = blackboard
        self._running = False
        self._dispatcher_task: asyncio.Task | None = None
        self._health_task: asyncio.Task | None = None
```

---

## Lifecycle Methods

### `start()`

```python
async def start(self) -> None:
    """Start background tasks: dispatcher loop + discovery health sweep."""
    self._running = True
    self._dispatcher_task = asyncio.create_task(
        self._dispatcher.run(), name="mesh-dispatcher"
    )
    self._health_task = asyncio.create_task(
        self._health_sweep(), name="mesh-health-sweep"
    )
```

Both tasks are named for easier debugging in `asyncio.all_tasks()` output.

### `stop()`

```python
async def stop(self) -> None:
    """Graceful shutdown: drain queue then cancel background tasks."""
    self._running = False
    await self._queue.join()           # wait for all in-flight tasks to complete
    if self._dispatcher_task:
        self._dispatcher_task.cancel()
    if self._health_task:
        self._health_task.cancel()
    await asyncio.gather(
        self._dispatcher_task, self._health_task,
        return_exceptions=True          # suppress CancelledError
    )
```

The `queue.join()` call ensures no tasks are silently dropped on shutdown — matches the semantics of `asyncio.Queue.join()`.

### `run_task()`

```python
async def run_task(
    self,
    task: MeshTask,
    target_role: AgentRole | None = None,
    target_capability: AgentCapability | None = None,
) -> AggregatedResult:
    """Enqueue task, dispatch to matched agents, await aggregated result."""
    agents = self._discovery.find_agents(
        role=target_role,
        capability=target_capability,
        state=AgentState.HEALTHY,
    )
    if not agents:
        raise NoAgentsAvailableError(target_role, target_capability)

    await self._aggregator.register_task(task.task_id, agent_count=len(agents))
    for agent in agents:
        await self._queue.enqueue(task, agent_id=agent.agent_id)

    return await self._aggregator.wait_for(task.task_id)
```

This is the **entire public API** for dispatching a multi-agent task. Callers never touch the queue, aggregator, or dispatcher directly.

---

## Health Sweep

```python
async def _health_sweep(self) -> None:
    """Periodic sweep: transition DEGRADED→UNREACHABLE, update load counters."""
    while self._running:
        await self._discovery.sweep()
        await asyncio.sleep(10)    # 10-second sweep interval
```

The sweep runs every 10 seconds, matching `AgentDiscovery`'s DEGRADED→UNREACHABLE timeout window (see [AgentDiscovery](AgentDiscovery)).

---

## `NoAgentsAvailableError`

```python
class NoAgentsAvailableError(Exception):
    def __init__(
        self,
        role: AgentRole | None,
        capability: AgentCapability | None,
    ) -> None:
        super().__init__(
            f"No HEALTHY agents available for role={role}, capability={capability}"
        )
        self.role = role
        self.capability = capability
```

Callers should handle this error by:
1. Checking `mesh.agent_count` in the Blackboard (written by AgentDiscovery)
2. Waiting and retrying with backoff
3. Escalating to the CognitiveCycle's fault tolerance layer (#137 circuit breaker)

---

## CognitiveCycle Integration

`MeshCoordinator` plugs into `CognitiveCycle` as a Phase 6 component:

```python
# In CognitiveCycle.__init__()
self._mesh = MeshCoordinator(
    blackboard=self._blackboard,
    strategy=AggregationStrategy.BEST_EFFORT,
    dispatch_timeout_ms=200.0,   # 200ms budget within 300ms tick
)

# In CognitiveCycle.start()
await self._mesh.start()

# In CognitiveCycle.tick()
async with measure_phase(CyclePhase.MULTI_AGENT_DISPATCH):
    task = MeshTask(
        task_id=str(uuid4()),
        priority=TaskPriority.HIGH,
        payload={"snapshot": self._blackboard.snapshot()},
        required_capability=AgentCapability.REASONING,
    )
    try:
        result = await self._mesh.run_task(
            task, target_capability=AgentCapability.REASONING
        )
        self._blackboard.write(
            "mesh.last_result", result.merged_payload, ttl=30
        )
    except NoAgentsAvailableError:
        # Degrade gracefully — cycle continues without agent dispatch
        pass
    except AggregationTimeoutError:
        # Record in CycleFaultSummary (#144)
        self._fault_summary.record("multi_agent", FaultSeverity.DEGRADED)
```

---

## MeshDispatcher Extension

`MeshDispatcher` (introduced in #154) is extended by `MeshCoordinator` to call `submit_result` after each agent task completes:

```python
# In MeshDispatcher._execute_task()
async def _execute_task(self, task: MeshTask, agent_id: str) -> None:
    start = time.monotonic()
    try:
        raw_result = await self._invoke_agent(task, agent_id)
        await self._aggregator.submit_result(AgentResult(
            agent_id=agent_id,
            task_id=task.task_id,
            success=True,
            payload=raw_result.payload,
            confidence=raw_result.confidence,
            latency_ms=(time.monotonic() - start) * 1000,
        ))
    except asyncio.CancelledError:
        # FASTEST_WINS cancelled this task — not a true failure
        await self._aggregator.submit_result(AgentResult(
            agent_id=agent_id,
            task_id=task.task_id,
            success=False,
            payload={},
            confidence=0.0,
            latency_ms=(time.monotonic() - start) * 1000,
            error="cancelled",
        ))
        raise
    except Exception as e:
        await self._aggregator.submit_result(AgentResult(
            agent_id=agent_id,
            task_id=task.task_id,
            success=False,
            payload={},
            confidence=0.0,
            latency_ms=(time.monotonic() - start) * 1000,
            error=str(e),
        ))
```

The `CancelledError` is **re-raised** after submitting the result — this is important to preserve asyncio task cancellation semantics.

---

## Acceptance Criteria

- [ ] `MeshCoordinator.__init__` composes all 4 sub-components
- [ ] `start()` launches dispatcher + health sweep as named `asyncio.Task`s
- [ ] `stop()` calls `queue.join()` before cancelling background tasks
- [ ] `run_task()` performs discovery → enqueue → await aggregation in one call
- [ ] `run_task()` raises `NoAgentsAvailableError` when no HEALTHY agents match
- [ ] `register_agent()` delegates to `AgentDiscovery.register()`
- [ ] Health sweep calls `AgentDiscovery.sweep()` every 10 seconds
- [ ] `MeshDispatcher._execute_task()` calls `aggregator.submit_result()` on completion AND cancellation
- [ ] Integration test: 3-agent task, 2 succeed, 1 fails → BEST_EFFORT returns merged result
- [ ] Integration test: `stop()` with 5 queued tasks → all complete before shutdown

---

## Related Pages

- [Multi-Agent Orchestration](Multi-Agent-Orchestration) — overview and design space
- [AgentDiscovery](AgentDiscovery) — service registry and health state machine
- [MeshTaskQueue](MeshTaskQueue) — priority queuing and retry
- [MeshResultAggregator](MeshResultAggregator) — result collection and merging
- [CognitiveCycle](CognitiveCycle) — tick pipeline and phase budgets
- [Fault-Tolerance](Fault-Tolerance) — circuit breaker and last-good-value patterns
