# Phase 12.1 — AgentRegistry: Distributed Agent Identity and Capability Registry

**Phase**: 12.1 | **Component**: `AgentRegistry` | **Issue**: [#352](https://github.com/web3guru888/asi-build/issues/352)

---

## Overview

`AgentRegistry` is the directory service at the foundation of Phase 12 (*Distributed Coordination & Multi-Agent Collaboration*). It provides:

- **Identity store** — persistent `AgentRecord` objects keyed by `agent_id`
- **Capability index** — searchable by semantic tags (`"planning"`, `"nlp"`, `"vision"`, …)
- **Heartbeat eviction** — automatic `OFFLINE` marking when agents miss deadlines
- **Prometheus observability** — 5 metrics covering gauge totals, eviction rates, and latency

All Phase 12 components (`NegotiationEngine`, `CollaborationChannel`, `ConsensusVoting`, `CoalitionFormation`) query the registry to enumerate candidate agents before initiating coordination.

---

## 1. Enums

```python
class AgentStatus(Enum):
    """Lifecycle status of a registered agent."""
    AVAILABLE   = auto()   # ready to accept tasks
    BUSY        = auto()   # currently executing tasks
    DRAINING    = auto()   # finishing work, then retiring
    OFFLINE     = auto()   # heartbeat timeout; presumed unreachable
```

### Status FSM

```
AVAILABLE ──► BUSY ──► DRAINING ──► OFFLINE
    ▲                                  │
    └──────────── heartbeat() ─────────┘
```

---

## 2. Frozen Dataclasses

### `AgentCapability`

```python
@dataclass(frozen=True)
class AgentCapability:
    tag: str                   # semantic label: "planning", "nlp", "vision"
    version: str = "1.0.0"    # semver string
    max_concurrency: int = 1   # max parallel tasks for this capability
```

### `AgentRecord`

```python
@dataclass(frozen=True)
class AgentRecord:
    agent_id: str
    display_name: str
    endpoint: str                           # HTTPS URL of agent's API
    capabilities: FrozenSet[AgentCapability]
    did: Optional[str] = None               # W3C DID (verified in Phase 12.3)
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    status: AgentStatus = AgentStatus.AVAILABLE
    metadata: Mapping[str, str] = field(default_factory=dict)
```

### `RegistryConfig`

```python
@dataclass(frozen=True)
class RegistryConfig:
    heartbeat_timeout_s: float = 30.0   # seconds before OFFLINE marking
    evict_interval_s: float = 10.0      # eviction loop cadence
    max_agents: int = 1024              # hard capacity limit
```

### `RegistrySnapshot`

```python
@dataclass(frozen=True)
class RegistrySnapshot:
    timestamp: float
    total_agents: int
    available_agents: int
    busy_agents: int
    offline_agents: int
    capability_index: Mapping[str, int]   # tag → count of agents with that tag
```

---

## 3. `AgentRegistry` Protocol

```python
@runtime_checkable
class AgentRegistry(Protocol):
    # --- Registration ---
    async def register(self, record: AgentRecord) -> None: ...
    async def deregister(self, agent_id: str) -> None: ...
    async def heartbeat(self, agent_id: str) -> None: ...

    # --- Lookup ---
    async def get(self, agent_id: str) -> Optional[AgentRecord]: ...
    async def find_by_capability(
        self, tag: str, *, status: AgentStatus = AgentStatus.AVAILABLE
    ) -> Sequence[AgentRecord]: ...
    async def list_all(self) -> Sequence[AgentRecord]: ...

    # --- Status ---
    async def update_status(self, agent_id: str, status: AgentStatus) -> None: ...

    # --- Lifecycle & Monitoring ---
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def snapshot(self) -> RegistrySnapshot: ...
```

---

## 4. `InMemoryAgentRegistry` Implementation

### `__init__`

```python
class InMemoryAgentRegistry:
    def __init__(self, cfg: RegistryConfig) -> None:
        self._cfg = cfg
        self._records: dict[str, AgentRecord] = {}
        self._lock = asyncio.Lock()
        self._evict_task: asyncio.Task | None = None
```

### `register` / `deregister`

```python
async def register(self, record: AgentRecord) -> None:
    async with self._lock:
        if len(self._records) >= self._cfg.max_agents \
                and record.agent_id not in self._records:
            raise CapacityError(f"Registry full ({self._cfg.max_agents} agents)")
        self._records[record.agent_id] = record
        _REGISTRY_AGENTS_TOTAL.set(len(self._records))

async def deregister(self, agent_id: str) -> None:
    async with self._lock:
        self._records.pop(agent_id, None)
        _REGISTRY_AGENTS_TOTAL.set(len(self._records))
```

### `heartbeat`

```python
async def heartbeat(self, agent_id: str) -> None:
    t0 = time.perf_counter()
    async with self._lock:
        rec = self._records.get(agent_id)
        if rec is not None:
            new_status = (
                AgentStatus.AVAILABLE
                if rec.status == AgentStatus.OFFLINE
                else rec.status
            )
            self._records[agent_id] = replace(
                rec, last_heartbeat=time.time(), status=new_status
            )
    _REGISTRY_HEARTBEAT_LATENCY.observe(time.perf_counter() - t0)
```

### `find_by_capability`

```python
async def find_by_capability(
    self,
    tag: str,
    *,
    status: AgentStatus = AgentStatus.AVAILABLE,
) -> list[AgentRecord]:
    t0 = time.perf_counter()
    async with self._lock:
        matches = [
            r for r in self._records.values()
            if r.status == status
            and any(c.tag == tag for c in r.capabilities)
        ]
    result = sorted(matches, key=lambda r: r.registered_at)  # FIFO
    _REGISTRY_LOOKUP_DURATION.observe(time.perf_counter() - t0)
    return result
```

### `_evict_loop`

```python
async def _evict_loop(self) -> None:
    """Mark agents OFFLINE when heartbeat timeout expires."""
    while True:
        await asyncio.sleep(self._cfg.evict_interval_s)
        now = time.time()
        async with self._lock:
            for aid, rec in list(self._records.items()):
                if (rec.status != AgentStatus.OFFLINE
                        and now - rec.last_heartbeat > self._cfg.heartbeat_timeout_s):
                    self._records[aid] = replace(rec, status=AgentStatus.OFFLINE)
                    _REGISTRY_OFFLINE_TOTAL.inc()
        _REGISTRY_AVAILABLE_TOTAL.set(
            sum(1 for r in self._records.values()
                if r.status == AgentStatus.AVAILABLE)
        )
```

### `snapshot`

```python
async def snapshot(self) -> RegistrySnapshot:
    async with self._lock:
        records = list(self._records.values())
    cap_index: dict[str, int] = defaultdict(int)
    for rec in records:
        for cap in rec.capabilities:
            cap_index[cap.tag] += 1
    return RegistrySnapshot(
        timestamp=time.time(),
        total_agents=len(records),
        available_agents=sum(1 for r in records if r.status == AgentStatus.AVAILABLE),
        busy_agents=sum(1 for r in records if r.status == AgentStatus.BUSY),
        offline_agents=sum(1 for r in records if r.status == AgentStatus.OFFLINE),
        capability_index=dict(cap_index),
    )
```

### `start` / `stop`

```python
async def start(self) -> None:
    self._evict_task = asyncio.create_task(self._evict_loop(), name="registry-evict")

async def stop(self) -> None:
    if self._evict_task:
        self._evict_task.cancel()
        try:
            await self._evict_task
        except asyncio.CancelledError:
            pass
        self._evict_task = None
```

---

## 5. Factory

```python
def build_agent_registry(cfg: RegistryConfig | None = None) -> AgentRegistry:
    """Create and return a configured InMemoryAgentRegistry."""
    return InMemoryAgentRegistry(cfg or RegistryConfig())
```

---

## 6. `CognitiveCycle` Integration

```python
# In CognitiveCycle.__init__:
self._registry: AgentRegistry = build_agent_registry()

# Before delegating a task to a peer agent:
async def _delegate_task(self, task: SubTask, capability_tag: str) -> None:
    peers = await self._registry.find_by_capability(capability_tag)
    if not peers:
        raise NoPeerAvailable(f"No AVAILABLE agent with capability '{capability_tag}'")
    best = peers[0]  # FIFO; Phase 12.2 replaces with bid-based selection
    await self._registry.update_status(best.agent_id, AgentStatus.BUSY)
    await self._router.dispatch(task, endpoint=best.endpoint)
```

---

## 7. Prometheus Metrics

```python
_REGISTRY_AGENTS_TOTAL = Gauge(
    "asi_registry_agents_total", "Total registered agents"
)
_REGISTRY_AVAILABLE_TOTAL = Gauge(
    "asi_registry_available_total", "Agents with AVAILABLE status"
)
_REGISTRY_OFFLINE_TOTAL = Counter(
    "asi_registry_offline_total", "Cumulative offline evictions"
)
_REGISTRY_HEARTBEAT_LATENCY = Histogram(
    "asi_registry_heartbeat_latency_seconds",
    "Heartbeat processing time",
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01],
)
_REGISTRY_LOOKUP_DURATION = Histogram(
    "asi_registry_lookup_duration_seconds",
    "find_by_capability latency",
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01],
)
```

### PromQL Examples

```promql
# Availability ratio
asi_registry_available_total / clamp_min(asi_registry_agents_total, 1)

# Eviction rate
rate(asi_registry_offline_total[5m])

# Heartbeat p99 latency
histogram_quantile(0.99,
  rate(asi_registry_heartbeat_latency_seconds_bucket[5m]))
```

### Alert Rule

```yaml
alert: TooManyAgentsOffline
expr: >
  (asi_registry_agents_total - asi_registry_available_total)
    / clamp_min(asi_registry_agents_total, 1) > 0.5
for: 2m
labels:
  severity: critical
annotations:
  summary: "More than 50% of registered agents are offline"
```

---

## 8. mypy Compliance Table

| Symbol | Annotation |
|--------|-----------|
| `AgentCapability.tag` | `str` |
| `AgentRecord.capabilities` | `FrozenSet[AgentCapability]` |
| `AgentRecord.metadata` | `Mapping[str, str]` |
| `InMemoryAgentRegistry._records` | `dict[str, AgentRecord]` |
| `find_by_capability` return | `list[AgentRecord]` (satisfies `Sequence[AgentRecord]`) |
| `snapshot().capability_index` | `Mapping[str, int]` |
| `replace(rec, status=...)` | `AgentRecord` |

---

## 9. Test Targets (12 minimum)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_register_and_get` | registered record returned by `get()` |
| 2 | `test_deregister_removes` | deregistered agent absent from `list_all()` |
| 3 | `test_heartbeat_updates_timestamp` | `last_heartbeat` advances after `heartbeat()` |
| 4 | `test_eviction_marks_offline` | missed heartbeat → `OFFLINE` after timeout |
| 5 | `test_find_by_capability_filters_tag` | only agents with matching tag returned |
| 6 | `test_find_by_capability_filters_status` | BUSY agents excluded from AVAILABLE search |
| 7 | `test_update_status_transitions` | `AVAILABLE → BUSY → DRAINING → OFFLINE` |
| 8 | `test_snapshot_counts` | available/busy/offline counts match records |
| 9 | `test_capability_index` | `snapshot.capability_index["planning"]` == correct count |
| 10 | `test_max_agents_limit` | `register()` raises `CapacityError` at `max_agents` |
| 11 | `test_concurrent_register` | 50 concurrent tasks register without corruption |
| 12 | `test_find_returns_empty_when_none_available` | empty list when no match |

---

## 10. Implementation Order (14 Steps)

1. Add `AgentStatus` enum
2. Add `AgentCapability`, `AgentRecord`, `RegistryConfig`, `RegistrySnapshot` frozen dataclasses
3. Define `AgentRegistry` Protocol with `@runtime_checkable`
4. Scaffold `InMemoryAgentRegistry.__init__` with `asyncio.Lock`
5. Implement `register()` with upsert + capacity check
6. Implement `deregister()`
7. Implement `heartbeat()` with OFFLINE→AVAILABLE recovery
8. Implement `get()` and `list_all()`
9. Implement `find_by_capability()` with tag + status filter + FIFO sort
10. Implement `update_status()` with FSM guard
11. Implement `_evict_loop()` background task
12. Implement `start()` / `stop()` managing `_evict_task`
13. Implement `snapshot()` with `capability_index` aggregation
14. Add Prometheus pre-init pattern + 12 pytest tests

---

## 11. Phase 12 Roadmap

| Sub-phase | Component | Status |
|-----------|-----------|--------|
| **12.1** | **AgentRegistry** | 🟡 This spec |
| 12.2 | NegotiationEngine — contract-net task negotiation | planned |
| 12.3 | CollaborationChannel — secure peer-to-peer messaging | planned |
| 12.4 | ConsensusVoting — BFT voting for shared decisions | planned |
| 12.5 | CoalitionFormation — dynamic team assembly for complex tasks | planned |

---

*Filed by maintainer | Discussions: [#353 Show & Tell](https://github.com/web3guru888/asi-build/discussions/353) · [#354 Q&A](https://github.com/web3guru888/asi-build/discussions/354)*
