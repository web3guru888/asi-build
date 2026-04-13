# MeshTaskQueue — Priority Task Queue for AgentMesh

The `MeshTaskQueue` provides durable, priority-ordered task queuing for the [AgentMesh](Multi-Agent-Orchestration) coordinator. It handles task lifecycle from enqueue through dispatch, completion, retry, and dead-lettering.

> **Status**: Design — Issue [#154](https://github.com/web3guru888/asi-build/issues/154) | Phase 4.2

---

## Why a Task Queue?

Without a durable queue, `AgentMesh.dispatch()` would drop tasks silently when agents are busy or when the coordinator restarts. The `MeshTaskQueue` provides:

| Problem | Solution |
|---------|----------|
| Tasks lost on agent crash | In-flight tracking + automatic retry |
| No prioritization | 5-level `TaskPriority` enum with asyncio.PriorityQueue |
| Unbounded backlog | `MAX_QUEUE_SIZE = 1000` with QueueFull exception |
| No audit trail | Blackboard events for every lifecycle transition |
| Timeout-silent tasks | Background `check_timeouts()` sweep |

---

## Data Model

### `TaskPriority`

```python
class TaskPriority(Enum):
    CRITICAL  = 0   # safety / emergency override — never dropped
    HIGH      = 1   # planning / real-time perception
    NORMAL    = 2   # standard cognitive cycle work
    LOW       = 3   # background / batch processing
    IDLE      = 4   # opportunistic / prefetch
```

CRITICAL tasks bypass `MAX_QUEUE_SIZE` — they cannot be dropped even when the queue is full. All other priority levels respect the size limit.

### `TaskStatus`

```python
class TaskStatus(Enum):
    QUEUED      = auto()   # waiting in the priority queue
    DISPATCHED  = auto()   # removed from queue; sent to agent namespace
    IN_PROGRESS = auto()   # agent acknowledged receipt
    COMPLETED   = auto()   # result returned
    FAILED      = auto()   # non-retryable failure
    DEAD_LETTER = auto()   # max_retries exhausted
```

### `MeshTask`

```python
@dataclass
class MeshTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    required_capability: str = ""          # routes via AgentDiscovery.by_capability()
    payload: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    dispatched_at: Optional[float] = None
    completed_at: Optional[float] = None
    assigned_agent_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_s: float = 30.0
    result: Optional[Any] = None
    error: Optional[str] = None
```

---

## MeshTaskQueue API

```python
class MeshTaskQueue:
    MAX_QUEUE_SIZE = 1000

    def __init__(self, blackboard: CognitiveBlackboard): ...

    async def enqueue(self, task: MeshTask) -> None: ...
    async def dequeue(self) -> MeshTask: ...
    async def complete(self, task_id: str, result: Any) -> None: ...
    async def fail(self, task_id: str, error: str) -> None: ...
    async def check_timeouts(self) -> None: ...

    @property
    def dead_letter_queue(self) -> list[MeshTask]: ...
    @property
    def queue_depth(self) -> int: ...
    @property
    def in_flight_count(self) -> int: ...
```

### `enqueue(task)`

Inserts the task into the priority queue using `(priority.value, created_at)` as the sort key. Publishes `mesh.task.queued` to the Blackboard. Raises `asyncio.QueueFull` if the queue is at capacity (unless `task.priority == CRITICAL`).

### `dequeue()`

Pops the highest-priority task (lowest `priority.value`, then earliest `created_at` for tiebreaks). Marks the task as `DISPATCHED`, records `dispatched_at`, and adds it to `_in_flight`. Blocks until a task is available.

### `complete(task_id, result)`

Removes the task from `_in_flight`, sets status to `COMPLETED`, records `completed_at`, stores the result, and publishes `mesh.task.completed` with `duration_ms`.

### `fail(task_id, error)`

Removes from `_in_flight`. If `retry_count < max_retries`, increments retry count, re-enqueues with exponential backoff (`2 ** retry_count` seconds), and publishes `mesh.task.failed`. If exhausted, moves to `_dead_letter` and publishes `mesh.task.dead_letter`.

### `check_timeouts()`

Sweeps `_in_flight` for tasks where `time.time() - dispatched_at > timeout_s`. Calls `fail()` for each timed-out task. Should be called by a background loop (see Background Loop below).

---

## Retry with Exponential Backoff

```python
async def fail(self, task_id: str, error: str) -> None:
    async with self._lock:
        task = self._in_flight.pop(task_id, None)
    if not task:
        return
    task.error = error
    task.retry_count += 1
    if task.retry_count < task.max_retries:
        backoff = 2 ** task.retry_count   # 2s, 4s, 8s
        await asyncio.sleep(backoff)
        task.status = TaskStatus.QUEUED
        await self.enqueue(task)
    else:
        task.status = TaskStatus.DEAD_LETTER
        async with self._lock:
            self._dead_letter.append(task)
        await self._bb.publish("mesh.task.dead_letter", {
            "task_id": task_id,
            "error": error,
            "retry_count": task.retry_count,
        })
```

---

## Blackboard Event Map

| Event | Trigger | Key Payload Fields |
|-------|---------|-------------------|
| `mesh.task.queued` | `enqueue()` | task_id, priority, capability |
| `mesh.task.dispatched` | `AgentMesh.dispatch()` | task_id, agent_id, namespace |
| `mesh.task.completed` | `complete()` | task_id, duration_ms |
| `mesh.task.failed` | `fail()` before retry | task_id, error, retry_count |
| `mesh.task.dead_letter` | `fail()` at max_retries | task_id, error, retry_count |
| `mesh.queue.depth` | Background sweep | depth, in_flight_count |

---

## Background Loop

The background dispatcher dequeues tasks and routes them via `AgentDiscovery`:

```python
class MeshDispatcher:
    """Background coroutine: dequeue → route → dispatch."""

    SWEEP_INTERVAL_S = 1.0

    def __init__(
        self,
        queue: MeshTaskQueue,
        discovery: AgentDiscovery,
        blackboard: CognitiveBlackboard,
    ):
        self._queue = queue
        self._discovery = discovery
        self._bb = blackboard

    async def _dispatch_loop(self) -> None:
        while True:
            task = await self._queue.dequeue()  # blocks for next task
            agents = self._discovery.by_capability(task.required_capability)
            if not agents:
                await self._queue.fail(task.task_id, "no_eligible_agents")
                continue
            target = min(agents, key=lambda a: a.current_task_count)
            target.current_task_count += 1
            task.assigned_agent_id = target.agent_id
            task.status = TaskStatus.IN_PROGRESS
            await self._bb.write(
                target.blackboard_namespace,
                {"task": task},
                ttl_seconds=task.timeout_s,
            )
            await self._bb.publish("mesh.task.dispatched", {
                "task_id": task.task_id,
                "agent_id": target.agent_id,
                "namespace": target.blackboard_namespace,
            })

    async def _timeout_sweep_loop(self) -> None:
        while True:
            await asyncio.sleep(self.SWEEP_INTERVAL_S)
            await self._queue.check_timeouts()
            await self._bb.write("mesh.queue.depth", {
                "depth": self._queue.queue_depth,
                "in_flight": self._queue.in_flight_count,
            })

    async def start(self) -> None:
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        self._sweep_task = asyncio.create_task(self._timeout_sweep_loop())

    async def stop(self) -> None:
        for task in [self._dispatch_task, self._sweep_task]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
```

---

## CognitiveCycle Backpressure

The CognitiveCycle can observe `mesh.queue.depth` to apply backpressure:

```python
depth_entry = await blackboard.read("mesh.queue.depth")
if depth_entry and depth_entry["depth"] > 500:
    # Skip LOW/IDLE dispatches this tick
    skip_priorities = {TaskPriority.LOW, TaskPriority.IDLE}
else:
    skip_priorities = set()
```

This prevents the cognitive cycle from flooding the mesh during high-load ticks.

---

## Test Plan

| Test | Scenario |
|------|----------|
| `test_enqueue_dequeue_priority_order` | IDLE+CRITICAL+NORMAL enqueued → dequeue order is CRITICAL, NORMAL, IDLE |
| `test_critical_bypasses_max_size` | Queue at MAX_QUEUE_SIZE → CRITICAL enqueues, NORMAL raises QueueFull |
| `test_complete_removes_from_inflight` | complete() → task not in _in_flight, event published |
| `test_fail_retry_with_backoff` | fail() with retry_count < max_retries → re-enqueued |
| `test_fail_dead_letter_at_max_retries` | fail() at max_retries → in dead_letter_queue |
| `test_check_timeouts_fails_stale` | dispatched_at 31s ago + timeout_s=30 → fail() called |
| `test_queue_depth_property` | enqueue 3, dequeue 1 → queue_depth == 2 |
| `test_in_flight_count` | dequeue 2, complete 1 → in_flight_count == 1 |
| `test_blackboard_events_roundtrip` | full lifecycle → 5 events in correct order |
| `test_tiebreak_by_created_at` | Two NORMAL tasks → earlier created_at dequeued first |

---

## Integration with AgentMesh (#147) and AgentDiscovery (#150)

```
MeshTask created
    └──→ MeshTaskQueue.enqueue()
              └──→ MeshDispatcher dequeues
                        └──→ AgentDiscovery.by_capability() → target agent
                                  └──→ Blackboard write to agent namespace
                                            └──→ Agent processes + writes result
                                                      └──→ MeshTaskQueue.complete()
```

The three-component design:
- **`AgentDiscovery`** — who is available and what they can do
- **`MeshTaskQueue`** — what work is pending and in what order
- **`AgentMesh`** — the coordinator that connects the two

---

## Related

- [Multi-Agent Orchestration](Multi-Agent-Orchestration) — AgentMesh coordinator
- [AgentDiscovery](AgentDiscovery) — service registry (capability routing)
- [Fault Tolerance](Fault-Tolerance) — retry/circuit breaker patterns for CognitiveCycle
- [Health Monitoring](Health-Monitoring) — `mesh.queue.depth` integration
- Issue [#154](https://github.com/web3guru888/asi-build/issues/154) — implementation tracking
- Issue [#147](https://github.com/web3guru888/asi-build/issues/147) — AgentMesh coordinator
- Issue [#150](https://github.com/web3guru888/asi-build/issues/150) — AgentDiscovery
