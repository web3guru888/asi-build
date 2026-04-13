# Phase 12.3 — CollaborationChannel

**Status**: 🟡 In Progress  
**Issue**: [#358](https://github.com/web3guru888/asi-build/issues/358)  
**Discussions**: [Show & Tell #359](https://github.com/web3guru888/asi-build/discussions/359) · [Q&A #360](https://github.com/web3guru888/asi-build/discussions/360)  
**Depends on**: [Phase 12.1 AgentRegistry](Phase-12-Agent-Registry) · [Phase 12.2 NegotiationEngine](Phase-12-Negotiation-Engine)  
**Next**: Phase 12.4 ConsensusVoting (planned)

---

## Motivation

Once `NegotiationEngine` assigns a task to a winning agent, that agent may need to collaborate in real-time with peers: sharing intermediate results, broadcasting state snapshots, and requesting specialised help mid-execution. `CollaborationChannel` provides a **pub/sub workspace** scoped to a single collaboration session, bridging the negotiation layer and the consensus/coalition layers.

---

## Enumerations

### `MessageType`

```python
class MessageType(Enum):
    STATE_SNAPSHOT   = auto()   # agent broadcasts its current internal state
    PARTIAL_RESULT   = auto()   # intermediate computation result
    HELP_REQUEST     = auto()   # agent requests assistance from peers
    HELP_RESPONSE    = auto()   # peer responds to a help request
    SYNC_BARRIER     = auto()   # all-or-nothing synchronisation point
    HEARTBEAT        = auto()   # keep-alive / liveness probe
```

### `ChannelStatus`

```python
class ChannelStatus(Enum):
    OPEN    = auto()   # accepting posts and subscribers
    CLOSED  = auto()   # no new posts; existing subscribers drain
    EXPIRED = auto()   # TTL elapsed; channel evicted
```

**FSM**:
```
OPEN ──(ttl elapsed)──► EXPIRED ──(evict loop)──► removed
 │
 └──(close() called)──► CLOSED  ──(evict loop)──► removed
```

---

## Frozen Dataclasses

### `ChannelMessage`

```python
@dataclass(frozen=True)
class ChannelMessage:
    message_id:   str
    channel_id:   str
    sender_did:   str
    message_type: MessageType
    payload:      Any                # arbitrary JSON-serialisable
    reply_to:     str | None = None  # message_id of message being replied to
    timestamp:    float = field(default_factory=time.time)
```

### `ChannelConfig`

```python
@dataclass(frozen=True)
class ChannelConfig:
    max_subscribers:    int   = 32     # hard cap on concurrent subscribers
    max_history:        int   = 256    # ring-buffer depth for late joiners
    ttl_seconds:        float = 600.0  # auto-expire after this idle period
    heartbeat_interval: float = 10.0   # seconds between HEARTBEAT posts
    require_membership: bool  = True   # only registered agents may post
```

### `ChannelInfo`

```python
@dataclass(frozen=True)
class ChannelInfo:
    channel_id:    str
    owner_did:     str
    topic:         str
    status:        ChannelStatus
    member_dids:   frozenset[str]
    message_count: int
    created_at:    float
    last_activity: float
```

---

## Protocols

### `CollaborationChannel`

```python
class CollaborationChannel(Protocol):
    async def post(
        self, sender_did, message_type, payload, reply_to=None
    ) -> ChannelMessage: ...
    async def subscribe(self, subscriber_did) -> AsyncIterator[ChannelMessage]: ...
    async def add_member(self, agent_did) -> None: ...
    async def remove_member(self, agent_did) -> None: ...
    async def close(self) -> None: ...
    async def info(self) -> ChannelInfo: ...
```

### `ChannelManager`

```python
class ChannelManager(Protocol):
    async def create_channel(
        self, owner_did, topic, initial_members, config=None
    ) -> CollaborationChannel: ...
    async def get_channel(self, channel_id) -> CollaborationChannel: ...
    async def list_channels(self, agent_did) -> list[ChannelInfo]: ...
    async def close_channel(self, channel_id) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

---

## `InMemoryCollaborationChannel`

### `__init__`

```python
def __init__(self, channel_id, owner_did, topic, config):
    self._channel_id    = channel_id
    self._owner_did     = owner_did
    self._topic         = topic
    self._cfg           = config
    self._status        = ChannelStatus.OPEN
    self._members:      set[str] = {owner_did}
    self._queues:       dict[str, asyncio.Queue[ChannelMessage]] = {}
    self._history:      deque[ChannelMessage] = deque(maxlen=config.max_history)
    self._msg_count     = 0
    self._created_at    = time.time()
    self._last_activity = time.time()
    self._heartbeat_task: asyncio.Task | None = None
```

### `post()`

```python
async def post(self, sender_did, message_type, payload, reply_to=None):
    if self._status != ChannelStatus.OPEN:
        raise RuntimeError(f"Channel {self._channel_id} is {self._status.name}")
    if self._cfg.require_membership and sender_did not in self._members:
        raise PermissionError(f"{sender_did} is not a channel member")

    msg = ChannelMessage(
        message_id=str(uuid.uuid4()), channel_id=self._channel_id,
        sender_did=sender_did, message_type=message_type,
        payload=payload, reply_to=reply_to,
    )
    self._history.append(msg)
    self._msg_count += 1
    self._last_activity = msg.timestamp

    for q in self._queues.values():
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            COLLAB_QUEUE_DROP_TOTAL.labels(channel=self._channel_id).inc()

    COLLAB_MESSAGES_TOTAL.labels(channel=self._channel_id, type=message_type.name).inc()
    return msg
```

### `subscribe()`

```python
async def subscribe(self, subscriber_did) -> AsyncIterator[ChannelMessage]:
    if len(self._queues) >= self._cfg.max_subscribers:
        raise RuntimeError("subscriber cap reached")
    q: asyncio.Queue[ChannelMessage] = asyncio.Queue(maxsize=512)
    # replay ring-buffer history for late joiners
    for old_msg in self._history:
        q.put_nowait(old_msg)
    self._queues[subscriber_did] = q
    COLLAB_ACTIVE_SUBSCRIBERS.labels(channel=self._channel_id).inc()
    try:
        while self._status == ChannelStatus.OPEN:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=self._cfg.heartbeat_interval)
                yield msg
            except asyncio.TimeoutError:
                continue    # re-check status
    finally:
        del self._queues[subscriber_did]
        COLLAB_ACTIVE_SUBSCRIBERS.labels(channel=self._channel_id).dec()
```

### `add_member()` / `remove_member()` / `close()` / `info()`

```python
async def add_member(self, agent_did): self._members.add(agent_did)
async def remove_member(self, agent_did): self._members.discard(agent_did)
async def close(self):
    self._status = ChannelStatus.CLOSED
    if self._heartbeat_task:
        self._heartbeat_task.cancel()
async def info(self) -> ChannelInfo:
    return ChannelInfo(
        channel_id=self._channel_id, owner_did=self._owner_did,
        topic=self._topic, status=self._status,
        member_dids=frozenset(self._members), message_count=self._msg_count,
        created_at=self._created_at, last_activity=self._last_activity,
    )
```

### `_heartbeat_loop()`

```python
async def _heartbeat_loop(self) -> None:
    while self._status == ChannelStatus.OPEN:
        await asyncio.sleep(self._cfg.heartbeat_interval)
        now = time.time()
        if now - self._last_activity > self._cfg.ttl_seconds:
            self._status = ChannelStatus.EXPIRED
            COLLAB_CHANNELS_EVICTED_TOTAL.inc()
            break
        msg = ChannelMessage(
            message_id=str(uuid.uuid4()), channel_id=self._channel_id,
            sender_did=self._owner_did, message_type=MessageType.HEARTBEAT,
            payload={"ts": now},
        )
        self._history.append(msg)
        self._msg_count += 1
        self._last_activity = now
        for q in self._queues.values():
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                COLLAB_QUEUE_DROP_TOTAL.labels(channel=self._channel_id).inc()
```

---

## `InMemoryChannelManager`

```python
class InMemoryChannelManager:
    def __init__(self, default_config=None):
        self._cfg = default_config or ChannelConfig()
        self._channels: dict[str, InMemoryCollaborationChannel] = {}
        self._evict_task: asyncio.Task | None = None

    async def create_channel(self, owner_did, topic, initial_members, config=None):
        ch_id = str(uuid.uuid4())
        ch = InMemoryCollaborationChannel(ch_id, owner_did, topic, config or self._cfg)
        for m in initial_members:
            await ch.add_member(m)
        ch._heartbeat_task = asyncio.create_task(ch._heartbeat_loop())
        self._channels[ch_id] = ch
        COLLAB_CHANNELS_TOTAL.inc()
        return ch

    async def get_channel(self, channel_id):
        try:
            return self._channels[channel_id]
        except KeyError:
            raise LookupError(f"Channel {channel_id!r} not found")

    async def list_channels(self, agent_did):
        return [await ch.info() for ch in self._channels.values() if agent_did in ch._members]

    async def close_channel(self, channel_id):
        ch = self._channels.pop(channel_id, None)
        if ch:
            await ch.close()

    async def start(self):
        self._evict_task = asyncio.create_task(self._evict_loop())

    async def stop(self):
        if self._evict_task:
            self._evict_task.cancel()
        for ch in list(self._channels.values()):
            await ch.close()

    async def _evict_loop(self):
        while True:
            await asyncio.sleep(60)
            expired = [
                cid for cid, ch in self._channels.items()
                if ch._status in (ChannelStatus.CLOSED, ChannelStatus.EXPIRED)
            ]
            for cid in expired:
                self._channels.pop(cid, None)
                COLLAB_CHANNELS_EVICTED_TOTAL.inc()
```

---

## Factory

```python
def build_channel_manager(
    config: ChannelConfig | None = None,
) -> InMemoryChannelManager:
    return InMemoryChannelManager(default_config=config)
```

---

## `CognitiveCycle` integration

```python
# In CognitiveCycle.__init__
self._channel_manager: ChannelManager = build_channel_manager()
self._active_channels: dict[str, CollaborationChannel] = {}

# Called after NegotiationEngine selects a winner:
async def _open_collaboration_channel(
    self, task_id: str, winner_did: str, peer_dids: list[str]
) -> None:
    ch = await self._channel_manager.create_channel(
        owner_did       = self.agent_did,
        topic           = f"task:{task_id}",
        initial_members = [winner_did] + peer_dids,
    )
    self._active_channels[task_id] = ch
    await self._federated_task_router.dispatch(
        task_id, winner_did, collaboration_channel_id=ch._channel_id
    )
```

---

## Prometheus Metrics

| Metric | Type | Labels | Notes |
|---|---|---|---|
| `asi_collab_channels_total` | Counter | — | Incremented on `create_channel()` |
| `asi_collab_channels_evicted_total` | Counter | — | Incremented by eviction loop |
| `asi_collab_messages_total` | Counter | `channel`, `type` | Per message-type breakdown |
| `asi_collab_active_subscribers` | Gauge | `channel` | Tracks live subscriber count |
| `asi_collab_queue_drop_total` | Counter | `channel` | Slow-subscriber drops |

### PromQL — drop-rate alert

```promql
rate(asi_collab_queue_drop_total[5m])
  / rate(asi_collab_messages_total[5m]) > 0.05
```

### Grafana alert YAML

```yaml
- alert: CollabHighDropRate
  expr: >
    rate(asi_collab_queue_drop_total[5m])
    / rate(asi_collab_messages_total[5m]) > 0.05
  for: 2m
  annotations:
    summary: "Channel {{ $labels.channel }} dropping >5% of messages"
```

---

## mypy Compatibility Table

| Class | `--strict` clean | Notes |
|---|---|---|
| `ChannelMessage` | ✅ | `payload: Any` intentional |
| `ChannelConfig` | ✅ | all primitives |
| `ChannelInfo` | ✅ | `frozenset[str]` typed |
| `InMemoryCollaborationChannel` | ✅ | `AsyncIterator` return typed |
| `InMemoryChannelManager` | ✅ | — |
| `build_channel_manager` | ✅ | — |

---

## Test Targets (12)

| # | Test | Asserts |
|---|---|---|
| 1 | `test_post_and_receive` | Single subscriber receives posted message |
| 2 | `test_late_join_history_replay` | Ring-buffer replayed on subscribe |
| 3 | `test_require_membership_guard` | Non-member post raises `PermissionError` |
| 4 | `test_max_subscribers_cap` | 33rd subscriber raises `RuntimeError` |
| 5 | `test_slow_subscriber_drop` | Full queue drops without blocking sender |
| 6 | `test_heartbeat_posted` | Heartbeat message delivered after interval |
| 7 | `test_ttl_expiry` | Channel transitions to `EXPIRED` after idle TTL |
| 8 | `test_close_drains_subscribers` | `close()` terminates subscribe generators |
| 9 | `test_reply_threading` | `reply_to` field chains messages correctly |
| 10 | `test_create_and_get_channel` | Manager round-trip via `channel_id` |
| 11 | `test_list_channels_by_member` | `list_channels()` filters by DID |
| 12 | `test_evict_loop_removes_expired` | Eviction task cleans up expired channels |

---

## Implementation Order (14 Steps)

1. Add `MessageType` and `ChannelStatus` enums to `asi_build/multi_agent/enums.py`
2. Add `ChannelMessage`, `ChannelConfig`, `ChannelInfo` frozen dataclasses
3. Add `CollaborationChannel` and `ChannelManager` Protocols to `protocols.py`
4. Implement `InMemoryCollaborationChannel.__init__` + `post()`
5. Implement `subscribe()` async generator with history replay
6. Implement `add_member()`, `remove_member()`, `close()`, `info()`
7. Implement `_heartbeat_loop()` asyncio task
8. Implement `InMemoryChannelManager` (create / get / list / close)
9. Implement `_evict_loop()` asyncio background task
10. Add `build_channel_manager()` factory
11. Wire into `CognitiveCycle._open_collaboration_channel()`
12. Register Prometheus metrics in `asi_build/metrics.py`
13. Write 12 pytest tests in `tests/multi_agent/test_collaboration_channel.py`
14. Update Phase 12 wiki page with sub-phase status

---

## Phase 12 Roadmap

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 12.1 | `AgentRegistry` | [#352](https://github.com/web3guru888/asi-build/issues/352) | ✅ Complete |
| 12.2 | `NegotiationEngine` | [#355](https://github.com/web3guru888/asi-build/issues/355) | 🟡 In Progress |
| 12.3 | `CollaborationChannel` | [#358](https://github.com/web3guru888/asi-build/issues/358) | 🟡 In Progress |
| 12.4 | `ConsensusVoting` | planned | ⬜ Planned |
| 12.5 | `CoalitionFormation` | planned | ⬜ Planned |
