# MeshResultAggregator

> **Status**: Design complete (Issue [#159](https://github.com/web3guru888/asi-build/issues/159))  
> **Phase**: 4.2 — Multi-Agent Orchestration  
> **Depends on**: AgentMesh ([#147](https://github.com/web3guru888/asi-build/issues/147)), AgentDiscovery ([#150](https://github.com/web3guru888/asi-build/issues/150)), MeshTaskQueue ([#154](https://github.com/web3guru888/asi-build/issues/154))

`MeshResultAggregator` collects results from concurrent agent tasks dispatched by `AgentMesh`, merges partial results into a unified output, and writes aggregated conclusions to the Cognitive Blackboard.

---

## Why We Need It

When `AgentMesh` fans out a single task to multiple specialist agents, the results arrive asynchronously and may conflict. A principled aggregation layer:

1. **Waits** for a quorum (not all agents — just enough)
2. **Detects** disagreement via `dissent_ratio`
3. **Merges** outputs using one of four strategies
4. **Writes** a single `AggregatedResult` to the Blackboard

Without this layer, the CognitiveCycle would need to manually poll each agent, choose a winner, and handle timeouts — duplicating logic that belongs in a dedicated component.

---

## Data Structures

### AggregationStrategy

```python
class AggregationStrategy(Enum):
    CONSENSUS   = "consensus"    # majority vote on discrete outputs
    CONFIDENCE  = "confidence"   # highest-confidence result wins
    WEIGHTED    = "weighted"     # reliability-weighted average (numeric outputs)
    FIRST_DONE  = "first_done"   # return first successful result (speculative exec)
```

### AgentResult

```python
@dataclass
class AgentResult:
    task_id:    str
    agent_id:   str
    output:     Any
    confidence: float          # 0.0–1.0
    latency_ms: float
    timestamp:  float = field(default_factory=time.time)
    error:      str | None = None
```

### AggregatedResult

```python
@dataclass
class AggregatedResult:
    task_id:       str
    strategy:      AggregationStrategy
    output:        Any
    confidence:    float      # aggregate confidence
    agent_count:   int        # how many agents contributed
    dissent_ratio: float      # fraction of agents that disagreed (0.0 = unanimous)
    latency_ms:    float      # wall-clock from dispatch to aggregation complete
    blackboard_key: str       # entry key written to Blackboard
```

---

## MeshResultAggregator API

```python
class MeshResultAggregator:
    def __init__(
        self,
        blackboard: CognitiveBlackboard,
        default_strategy: AggregationStrategy = AggregationStrategy.CONFIDENCE,
        quorum: float = 0.5,          # fraction of agents that must respond
        timeout_ms: float = 5000.0,
        registry: AgentRegistry | None = None,  # for WEIGHTED reliability scores
    ): ...

    async def wait_for_results(
        self,
        task_id: str,
        expected: int,
        strategy: AggregationStrategy | None = None,
    ) -> AggregatedResult:
        """Block until quorum reached or timeout, then aggregate and write to Blackboard."""

    async def receive_result(self, result: AgentResult) -> None:
        """Called by AgentMesh when an agent completes a task. Thread-safe."""

    def _aggregate(
        self,
        results: list[AgentResult],
        strategy: AggregationStrategy,
    ) -> AggregatedResult: ...
```

---

## Aggregation Strategies

### CONSENSUS
Majority vote on discrete outputs.

```
outputs   = ["label_A", "label_B", "label_A"]
majority  = "label_A"  (2/3)
dissent   = 1/3 = 0.33
confidence = average confidence of majority group
```

Outputs are canonicalized via `json.dumps(output, sort_keys=True, default=str)` before grouping — handles dicts and nested structures that are not directly hashable.

### CONFIDENCE
Return the result with the highest `confidence`.

```
dissent_ratio = 1 − (winner_confidence / Σ all confidences)
```

Works for any output type. This is the **default strategy**.

### WEIGHTED
Confidence-weighted average. Requires numeric outputs.

```
output = Σ(confidence_i × output_i) / Σ(confidence_i)
```

If `registry` is provided, weights are multiplied by per-agent reliability:
```
weight_i = confidence_i × registry.reliability(agent_id_i)
```

Falls back to `CONFIDENCE` if outputs are non-numeric.

### FIRST_DONE
Return immediately on the first non-error result. Cancel the wait future; remaining results are discarded.

Use for speculative execution: multiple agents race to answer the same query (e.g., cache lookup across distributed shards). The fastest win.

---

## State Machine

```
AgentMesh.dispatch(task_id, agents)
            │
            ▼
     [COLLECTING] ◄──── receive_result() × N (concurrent)
            │
            ├── quorum reached? ──► [AGGREGATING] ──► _aggregate() ──► bb.post()
            │                                                               │
            └── timeout? ─────────► check quorum ──► [AGGREGATED] ◄───────┘
                                          │
                                          └── below quorum ──► QuorumNotReached
```

---

## Quorum & Timeout Behavior

| Scenario | Outcome |
|---|---|
| All agents respond before timeout | Full aggregation with all results |
| Quorum reached, some still pending | Aggregate available, cancel wait |
| Timeout reached, quorum met | Aggregate whatever arrived |
| Timeout reached, below quorum | `QuorumNotReached` exception |
| All agents errored | `AggregationError` exception |

**Recommended timeout values:**

| Context | Timeout |
|---|---|
| Inside CognitiveCycle tick (120ms budget) | 50–80ms |
| Async background task | 5000ms |
| FIRST_DONE speculative lookup | 200ms |

---

## Lock Discipline

`receive_result` is on the hot path — called from many concurrent coroutines. The lock covers only list append and length check. Quorum detection and aggregation happen **outside** the lock:

```python
async def receive_result(self, result: AgentResult) -> None:
    async with self._lock:
        self._collected[result.task_id].append(result)
        count = len(self._collected[result.task_id])
        expected = self._expected[result.task_id]

    # Outside lock — only one coroutine will successfully set_result
    if count >= math.ceil(expected * self._quorum):
        fut = self._pending.get(result.task_id)
        if fut and not fut.done():
            fut.set_result(None)
```

Never call `_aggregate()` or `bb.post()` while holding the lock. See [#149](https://github.com/web3guru888/asi-build/discussions/149) for the general lock-before-await principle.

---

## Blackboard Integration

After aggregation, `AggregatedResult` is written to the Blackboard:

```python
entry_key = f"mesh.result.{task_id}"
blackboard.post(
    key=entry_key,
    value=agg_result,
    source="MeshResultAggregator",
    ttl_seconds=30,
    tags=["multi_agent", agg_result.strategy.value],
)
```

**Consumers** subscribe to the `mesh.result.*` wildcard pattern via EventBus:

| Consumer | What it reads | Action |
|---|---|---|
| CognitiveCycle | `mesh.result.*` | Feed into next pipeline phase |
| PLN Engine (#44) | `mesh.result.*` (confidence field) | Update belief weights |
| Safety Module (#37) | `mesh.result.*` where dissent_ratio > 0.4 | Trigger safety review |
| CycleFaultSummary (#144) | `mesh.result.*` errors | Log to fault report |

---

## dissent_ratio Semantics

| Value | Meaning |
|---|---|
| 0.0 | All agents agreed (unanimous) |
| 0.0–0.3 | Minor disagreement, proceed normally |
| 0.3–0.6 | Notable dissent — log and monitor |
| > 0.6 | High disagreement — consider escalation |

For safety-critical tasks (goal updates, action proposals), a `dissent_ratio > 0.4` should trigger a `safety.dissent_alert` Blackboard entry. See [discussion #161](https://github.com/web3guru888/asi-build/discussions/161) for the full design debate.

---

## Relationship to Other AgentMesh Components

```
MeshTaskQueue (#154)
        │  enqueue / dequeue
        ▼
AgentMesh (#147) ──── dispatch ──►  Agent 1
        │                    │──►  Agent 2
        │                    └──►  Agent 3
        │
        │  receive_result × 3
        ▼
MeshResultAggregator (#159)
        │
        │  bb.post("mesh.result.*")
        ▼
CognitiveBlackboard ──► EventBus ──► Subscribers
```

`AgentDiscovery` (#150) provides per-agent reliability scores used by the `WEIGHTED` strategy, and can be used to pre-filter UNREACHABLE agents before dispatch.

---

## Acceptance Criteria

- [ ] `CONSENSUS`: majority output selected, `dissent_ratio` correct
- [ ] `CONFIDENCE`: highest-confidence agent wins
- [ ] `WEIGHTED`: confidence-weighted average (numeric outputs)
- [ ] `FIRST_DONE`: returns immediately on first success
- [ ] Quorum enforcement: raises `QuorumNotReached` if insufficient agents respond
- [ ] Timeout enforcement: waits at most `timeout_ms`, then aggregates available
- [ ] Blackboard write: `AggregatedResult` posted to `mesh.result.{task_id}`
- [ ] Error isolation: one agent error does not abort aggregation
- [ ] Thread safety: concurrent `receive_result` calls safe under lock
- [ ] `dissent_ratio` is always in [0.0, 1.0]
- [ ] Integration test: 3-agent CONSENSUS round trip end-to-end

---

## Discussions

- [#160 Show & Tell: MeshResultAggregator design walkthrough](https://github.com/web3guru888/asi-build/discussions/160)
- [#161 Ideas: How should ASI:BUILD respond to agent dissent?](https://github.com/web3guru888/asi-build/discussions/161)
- [#162 Q&A: How does MeshResultAggregator handle slow or unresponsive agents?](https://github.com/web3guru888/asi-build/discussions/162)

---

## See Also

- [Multi-Agent-Orchestration](Multi-Agent-Orchestration) — overview of the AgentMesh subsystem
- [MeshTaskQueue](MeshTaskQueue) — upstream task queue
- [AgentDiscovery](AgentDiscovery) — service registry and health tracking
- [Fault-Tolerance](Fault-Tolerance) — circuit breaker, retry budgets, last-good fallback
- [Cognitive-Blackboard](Cognitive-Blackboard) — Blackboard API reference
