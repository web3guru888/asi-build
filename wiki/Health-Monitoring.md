# Health Monitoring

The `CognitiveCycle` health monitoring system provides per-tick structured fault records, SSE streaming, and MCP introspection — giving operators full visibility into module health at runtime.

## Overview

Every `CognitiveCycle.tick()` call produces a `CycleFaultSummary` — a structured record of what happened across all modules in that tick. Summaries are:

1. **Returned** directly from `tick()` for programmatic use
2. **Posted to the Blackboard** as `entry_type="cycle_fault_summary"` (TTL: 5s)
3. **Streamed via SSE** on `/cycle/health/stream`
4. **Queryable via MCP** with the `get_cycle_health` tool

## Data Model

```python
class FaultSeverity(str, Enum):
    TRANSIENT   = "transient"   # minor fault, recovered via retry
    DEGRADED    = "degraded"    # using last-good fallback
    CRITICAL    = "critical"    # circuit open, module offline
    RECOVERED   = "recovered"   # all modules healthy

@dataclass
class ModuleFaultRecord:
    module_id: str
    severity: FaultSeverity
    error_type: str
    error_message: str
    tick_number: int
    retry_count: int = 0
    using_fallback: bool = False
    circuit_state: str = "CLOSED"

@dataclass
class CycleFaultSummary:
    tick_number: int
    wall_clock_ms: float
    modules_ok: list[str]
    modules_degraded: list[str]
    modules_critical: list[str]
    faults: list[ModuleFaultRecord]
    budget_violations: list[str]
    overall_severity: FaultSeverity
```

## Fault Severity Levels

| Severity | Meaning | CognitiveCycle continues? |
|----------|---------|--------------------------|
| `RECOVERED` | All 29 modules healthy, no faults | ✅ Yes |
| `TRANSIENT` | 1+ faults occurred but all recovered via retry | ✅ Yes |
| `DEGRADED` | 1+ modules using last-good fallback | ✅ Yes (degraded) |
| `CRITICAL` | 1+ circuit breakers open (module offline) | ⚠️ Yes, but safety modules may halt |

## SSE Stream

Connect to `/cycle/health/stream` to receive one event per tick:

```
GET /cycle/health/stream
Accept: text/event-stream
```

Each event:
```
event: recovered
id: 4821
data: {"tick":4821,"wall_ms":58.3,"ok":29,"degraded":[],"critical":[],"violations":[],"severity":"recovered"}

event: degraded
id: 4822
data: {"tick":4822,"wall_ms":91.2,"ok":27,"degraded":["holographic","bci"],"critical":[],"violations":["holographic"],"severity":"degraded"}
```

**Event names** map to `FaultSeverity` values: `recovered`, `transient`, `degraded`, `critical`.

A `ping` event is emitted every 2 seconds when no ticks are in flight (keep-alive).

### JavaScript client

```javascript
const es = new EventSource("/cycle/health/stream");

es.addEventListener("critical", e => {
    const data = JSON.parse(e.data);
    console.error("Critical modules:", data.critical);
    // trigger alert, page on-call, etc.
});

es.addEventListener("degraded", e => {
    const data = JSON.parse(e.data);
    console.warn("Degraded modules:", data.degraded);
});

es.addEventListener("ping", () => {});  // keep-alive, ignore
```

## MCP Tool

```python
@mcp_tool(name="get_cycle_health")
async def get_cycle_health() -> dict:
    """Get the latest CognitiveCycle fault summary."""
    latest = await cognitive_cycle.latest_fault_summary()
    if latest is None:
        return {"status": "not_started"}
    return latest.to_sse_payload()
```

Any MCP client (Claude, LangGraph, custom agent) can query live cycle health without connecting to the SSE stream.

## Blackboard Integration

Each `CycleFaultSummary` is automatically posted to the Blackboard:

```python
await self._blackboard.post(
    entry_type="cycle_fault_summary",
    data=summary.to_sse_payload(),
    ttl_ms=5000,  # valid for 5 ticks at 1Hz
)
```

The **Safety module** subscribes to `cycle_fault_summary` entries and can trigger an emergency stop if `modules_critical` includes safety-relevant modules (`"safety"`, `"agi_reproducibility"`).

## Multi-Agent Mesh Health

When running multiple `CognitiveCycle` instances via `AgentMesh` (see [[Multi-Agent-Orchestration]]), the `/mesh/health/stream` endpoint streams per-agent summaries:

```
event: mesh_health
data: {
  "perception": {"tick":4821,"severity":"recovered","ok":5},
  "reasoning":  {"tick":1204,"severity":"degraded","degraded":["pln"]},
  "safety":     {"tick":4821,"severity":"recovered","ok":2}
}
```

## Related Issues

- [#144](https://github.com/web3guru888/asi-build/issues/144) — CycleFaultSummary + SSE endpoint implementation
- [#137](https://github.com/web3guru888/asi-build/issues/137) — Circuit breaker (feeds `circuit_state` in `ModuleFaultRecord`)
- [#139](https://github.com/web3guru888/asi-build/issues/139) — Retry budgets (feeds `retry_count`)
- [#126](https://github.com/web3guru888/asi-build/issues/126) — CycleProfiler (feeds `budget_violations`)

## Related Discussions

- [#143](https://github.com/web3guru888/asi-build/discussions/143) — Should the health dashboard use MCP, SSE, Prometheus, or the Blackboard?
- [#146](https://github.com/web3guru888/asi-build/discussions/146) — Show & Tell: CycleFaultSummary full design walkthrough
