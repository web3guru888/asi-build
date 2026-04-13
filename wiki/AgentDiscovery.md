# AgentDiscovery — Service Registry for AgentMesh

The `AgentDiscovery` class is the service registry layer for the [AgentMesh](Multi-Agent-Orchestration) coordinator. It handles agent registration, liveness detection via heartbeats, and capability-based routing queries.

> **Status**: Design — Issue [#150](https://github.com/web3guru888/asi-build/issues/150) | Phase 4.2

---

## Responsibilities

| Responsibility | API |
|---------------|-----|
| Agent registration | `register(AgentRegistration)` |
| Liveness detection | `heartbeat(agent_id)` |
| Health status sweep | `health_sweep()` (background loop) |
| Role-based lookup | `healthy_agents(role=None)` |
| Capability-based lookup | `by_capability(capability)` |
| Graceful deregistration | `deregister(agent_id)` |
| Event broadcasting | Publishes to Cognitive Blackboard |

---

## Data Model

### `AgentStatus`

```python
class AgentStatus(Enum):
    STARTING    = auto()   # registered but not yet healthy
    HEALTHY     = auto()   # passed last heartbeat check
    DEGRADED    = auto()   # slow heartbeats or partial capability loss
    UNREACHABLE = auto()   # missed N consecutive heartbeats
    DRAINING    = auto()   # scheduled for graceful shutdown
```

### `AgentRegistration`

```python
@dataclass
class AgentRegistration:
    agent_id: str                       # UUID, unique per process instance
    role: AgentRole                     # from AgentMesh.AgentRole (7 values)
    capabilities: frozenset[str]        # e.g. {"reasoning.pln", "memory.read"}
    blackboard_namespace: str           # e.g. "agent.planner.001"
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    status: AgentStatus = AgentStatus.STARTING
    metadata: dict = field(default_factory=dict)
```

---

## Health State Machine

```
         register()
             │
             ▼
         STARTING
             │
    first heartbeat()
             │
             ▼
         HEALTHY ◄────── heartbeat() within interval
             │
      >15s no heartbeat
             │
             ▼
         DEGRADED
             │
      >30s no heartbeat
             │
             ▼
       UNREACHABLE
             │
        deregister()
             │
             ▼
          (removed)

    Any state → DRAINING  (graceful shutdown signal)
```

**Timeouts:**

| Constant | Default | Meaning |
|----------|---------|---------|
| `HEARTBEAT_INTERVAL_S` | 5.0s | Expected heartbeat period |
| `DEGRADED_TIMEOUT_S` | 15.0s | Heartbeat age before DEGRADED |
| `UNREACHABLE_TIMEOUT_S` | 30.0s | Heartbeat age before UNREACHABLE |

---

## Full Implementation

```python
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

class AgentStatus(Enum):
    STARTING    = auto()
    HEALTHY     = auto()
    DEGRADED    = auto()
    UNREACHABLE = auto()
    DRAINING    = auto()

@dataclass
class AgentRegistration:
    agent_id: str
    role: "AgentRole"
    capabilities: frozenset[str]
    blackboard_namespace: str
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    status: AgentStatus = AgentStatus.STARTING
    metadata: dict = field(default_factory=dict)

class AgentDiscovery:
    HEARTBEAT_INTERVAL_S  = 5.0
    DEGRADED_TIMEOUT_S    = 15.0
    UNREACHABLE_TIMEOUT_S = 30.0

    def __init__(self, blackboard: "CognitiveBlackboard"):
        self._registry: dict[str, AgentRegistration] = {}
        self._lock = asyncio.Lock()
        self._bb = blackboard

    async def register(self, reg: AgentRegistration) -> None:
        async with self._lock:
            self._registry[reg.agent_id] = reg
        await self._bb.publish("mesh.agent.registered", {
            "agent_id": reg.agent_id,
            "role": reg.role.name,
            "capabilities": list(reg.capabilities),
        })

    async def heartbeat(self, agent_id: str) -> None:
        async with self._lock:
            if agent_id in self._registry:
                self._registry[agent_id].last_heartbeat = time.time()
                self._registry[agent_id].status = AgentStatus.HEALTHY

    async def deregister(self, agent_id: str) -> None:
        async with self._lock:
            reg = self._registry.pop(agent_id, None)
        if reg:
            await self._bb.publish("mesh.agent.deregistered", {
                "agent_id": agent_id,
            })

    def healthy_agents(
        self,
        role: Optional["AgentRole"] = None,
    ) -> list[AgentRegistration]:
        agents = [
            a for a in self._registry.values()
            if a.status == AgentStatus.HEALTHY
        ]
        if role is not None:
            agents = [a for a in agents if a.role == role]
        return agents

    def by_capability(self, capability: str) -> list[AgentRegistration]:
        return [
            a for a in self.healthy_agents()
            if capability in a.capabilities
        ]

    async def health_sweep(self) -> None:
        now = time.time()
        async with self._lock:
            for reg in self._registry.values():
                age = now - reg.last_heartbeat
                old_status = reg.status
                if age >= self.UNREACHABLE_TIMEOUT_S:
                    reg.status = AgentStatus.UNREACHABLE
                elif age >= self.DEGRADED_TIMEOUT_S:
                    reg.status = AgentStatus.DEGRADED
                elif age < self.HEARTBEAT_INTERVAL_S * 2:
                    if reg.status != AgentStatus.STARTING:
                        reg.status = AgentStatus.HEALTHY
                if reg.status != old_status:
                    await self._bb.publish("mesh.agent.status_changed", {
                        "agent_id": reg.agent_id,
                        "old_status": old_status.name,
                        "new_status": reg.status.name,
                    })
```

---

## Blackboard Event Map

| Event | Trigger | Payload |
|-------|---------|---------|
| `mesh.agent.registered` | `register()` | agent_id, role, capabilities |
| `mesh.agent.deregistered` | `deregister()` | agent_id |
| `mesh.agent.status_changed` | `health_sweep()` | agent_id, old_status, new_status |
| `mesh.agent.heartbeat` | `heartbeat()` (sampled 1/10) | agent_id, latency_ms |

---

## Integration with AgentMesh

`AgentDiscovery` is injected into or owned by `AgentMesh`:

```python
class AgentMesh:
    def __init__(self, blackboard: CognitiveBlackboard):
        self._bb = blackboard
        self._discovery = AgentDiscovery(blackboard)

    async def dispatch(self, task: AgentTask) -> str:
        # Query the live registry instead of a static list
        if task.required_capability:
            candidates = self._discovery.by_capability(task.required_capability)
        elif task.required_role:
            candidates = self._discovery.healthy_agents(role=task.required_role)
        else:
            candidates = self._discovery.healthy_agents()
        # ... routing + Blackboard write
```

---

## Testing

| Test | Description |
|------|-------------|
| `test_register_publishes_event` | Verify `mesh.agent.registered` is published |
| `test_heartbeat_sets_healthy` | Heartbeat transitions STARTING -> HEALTHY |
| `test_sweep_degraded` | No heartbeat >15s -> DEGRADED |
| `test_sweep_unreachable` | No heartbeat >30s -> UNREACHABLE |
| `test_healthy_agents_role_filter` | Role filter returns correct subset |
| `test_by_capability_filter` | Returns agents with matching capability |
| `test_deregister_publishes_event` | Verify `mesh.agent.deregistered` is published |
| `test_concurrent_heartbeats` | 100 concurrent heartbeats don't corrupt state |
| `test_exclude_unreachable_from_dispatch` | UNREACHABLE agents excluded from routing |

---

## Related

- [Multi-Agent-Orchestration](Multi-Agent-Orchestration) — AgentMesh coordinator
- [Cognitive-Blackboard](Cognitive-Blackboard) — shared state layer
- [Health-Monitoring](Health-Monitoring) — CycleFaultSummary and SSE stream
- Issue [#147](https://github.com/web3guru888/asi-build/issues/147) — AgentMesh coordinator
- Issue [#150](https://github.com/web3guru888/asi-build/issues/150) — AgentDiscovery (this)
- Discussion [#151](https://github.com/web3guru888/asi-build/discussions/151) — AgentMesh architecture walkthrough
- Discussion [#152](https://github.com/web3guru888/asi-build/discussions/152) — Static roles vs dynamic capabilities
- Discussion [#153](https://github.com/web3guru888/asi-build/discussions/153) — Agent failure handling
