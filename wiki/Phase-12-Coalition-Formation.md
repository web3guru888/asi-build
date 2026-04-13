# Phase 12.5 — CoalitionFormation

**Status**: 📋 Planned  
**Issue**: [#364](https://github.com/web3guru888/asi-build/issues/364)  
**Discussions**: [Show & Tell #365](https://github.com/web3guru888/asi-build/discussions/365) · [Q&A #366](https://github.com/web3guru888/asi-build/discussions/366)  
**Depends on**: [Phase 12.1 AgentRegistry](Phase-12-Agent-Registry) · [Phase 12.2 NegotiationEngine](Phase-12-Negotiation-Engine) · [Phase 12.3 CollaborationChannel](Phase-12-Collaboration-Channel) · [Phase 12.4 ConsensusVoting](Phase-12-Consensus-Voting)  
**Completes**: Phase 12 — Distributed Coordination & Multi-Agent Collaboration 🎉

---

## Motivation

`AgentRegistry` tells us who is available, `NegotiationEngine` allocates individual tasks, `CollaborationChannel` lets agents share state mid-execution, and `ConsensusVoting` ratifies high-stakes decisions. `CoalitionFormation` is the **capstone layer** that binds all four together: given a complex goal that no single agent can satisfy alone, it selects a **minimal, capability-matched coalition**, negotiates entry, establishes a shared `CollaborationChannel`, and oversees the coalition lifecycle — from formation through consensus ratification to dissolution.

---

## Enumerations

### `CoalitionStatus`

```python
class CoalitionStatus(Enum):
    FORMING     = auto()   # invitations sent, awaiting acceptances
    ACTIVE      = auto()   # all members accepted; channel open
    RATIFYING   = auto()   # ConsensusVoting ballot open
    DISSOLVED   = auto()   # task complete or failure; channel closed
    FAILED      = auto()   # could not form sufficient coalition
```

#### CoalitionStatus FSM

```
FORMING ──(all accepted)──────────────► ACTIVE ──(high-stakes goal)──► RATIFYING
FORMING ──(timeout / rejections)──────► FAILED
RATIFYING ──(PASS)────────────────────► ACTIVE
RATIFYING ──(FAIL/VETO/TIE)───────────► DISSOLVED
ACTIVE ──(task complete / TTL)────────► DISSOLVED
```

---

### `InvitationResponse`

```python
class InvitationResponse(Enum):
    ACCEPTED  = auto()   # agent joins coalition
    DECLINED  = auto()   # agent declines (not available or not interested)
    TIMEOUT   = auto()   # no response before invitation TTL
```

---

### `CoalitionRole`

```python
class CoalitionRole(Enum):
    LEADER   = auto()   # coordinates; opens channel + voting ballots
    MEMBER   = auto()   # participates; casts votes; shares state
    OBSERVER = auto()   # receives channel messages; cannot vote or publish
```

---

## Data Classes

All dataclasses are **frozen** (`@dataclass(frozen=True)`) for immutable, hashable records.

### `CoalitionMember`

```python
@dataclass(frozen=True)
class CoalitionMember:
    agent_id:    str
    role:        CoalitionRole
    capabilities: frozenset[str]
    joined_at:   datetime
```

### `Coalition`

```python
@dataclass(frozen=True)
class Coalition:
    coalition_id:  str              # UUID4
    goal_id:       str              # links to GoalRegistry
    leader_id:     str              # agent that initiated formation
    members:       frozenset[str]   # agent_ids (includes leader)
    status:        CoalitionStatus
    channel_id:    str              # CollaborationChannel session
    formed_at:     datetime
    dissolved_at:  datetime | None  # None until dissolved
```

### `FormationRequest`

```python
@dataclass(frozen=True)
class FormationRequest:
    goal_id:               str
    required_capabilities: list[str]         # must-have; at least one agent per cap
    preferred_capabilities: list[str]        # nice-to-have; improve coverage
    min_members:           int  = 2
    max_members:           int  = 8
    invitation_ttl_secs:   float = 10.0
    coalition_ttl_secs:    float = 300.0     # dissolve after this regardless
    consensus_threshold:   float = 0.6
```

### `CoalitionSnapshot`

```python
@dataclass(frozen=True)
class CoalitionSnapshot:
    coalition_id: str
    status:       CoalitionStatus
    member_count: int
    formed_at:    datetime
    dissolved_at: datetime | None
```

### `CoalitionConfig`

```python
@dataclass(frozen=True)
class CoalitionConfig:
    eviction_interval_secs: float = 10.0
    max_active_coalitions:  int   = 64
    default_inv_ttl_secs:   float = 10.0
    default_coal_ttl_secs:  float = 300.0
    default_threshold:      float = 0.6
```

---

## Protocol

```python
class CoalitionFormation(Protocol):
    async def form_coalition(
        self,
        request: FormationRequest,
    ) -> Coalition: ...

    async def dissolve(self, coalition_id: str, reason: str = "") -> None: ...

    async def get(self, coalition_id: str) -> Coalition | None: ...

    async def snapshot(self, coalition_id: str) -> CoalitionSnapshot | None: ...

    async def list_active(self) -> list[Coalition]: ...
```

---

## Reference Implementation: `InMemoryCoalitionFormation`

```python
class InMemoryCoalitionFormation:
    """Coordinates multi-agent coalition lifecycle using Registry, Channel, and Voting."""

    def __init__(
        self,
        registry:  AgentRegistry,
        channel_mgr: CollaborationChannelManager,
        consensus: ConsensusVoting,
        negotiation: NegotiationEngine,
        config:    CoalitionConfig,
        metrics:   CoalitionMetrics,
    ) -> None:
        self._registry    = registry
        self._channel_mgr = channel_mgr
        self._consensus   = consensus
        self._negotiation = negotiation
        self._config      = config
        self._metrics     = metrics
        self._lock        = asyncio.Lock()
        self._coalitions: dict[str, Coalition]  = {}
        self._roles:      dict[str, dict[str, CoalitionRole]] = {}
        self._tasks:      dict[str, asyncio.Task] = {}

    # ── form_coalition ────────────────────────────────────────────────────────

    async def form_coalition(self, request: FormationRequest) -> Coalition:
        # 1. Find candidates from AgentRegistry
        candidates = await self._select_candidates(request)
        if len(candidates) < request.min_members:
            raise RuntimeError(
                f"Insufficient agents: found {len(candidates)}, need {request.min_members}"
            )

        # 2. Send invitations via CollaborationChannel
        invited = candidates[: request.max_members]
        leader_id = invited[0]
        channel_id = f"coalition-{uuid.uuid4().hex[:8]}"
        await self._channel_mgr.open(channel_id)

        accepted = await self._invite_members(
            invited, channel_id, request.goal_id, request.invitation_ttl_secs
        )
        if len(accepted) < request.min_members:
            await self._channel_mgr.close(channel_id)
            self._metrics.formations_failed.inc()
            raise RuntimeError(f"Only {len(accepted)} agents accepted; need {request.min_members}")

        # 3. Create Coalition record
        coalition = Coalition(
            coalition_id = str(uuid.uuid4()),
            goal_id      = request.goal_id,
            leader_id    = leader_id,
            members      = frozenset(accepted),
            status       = CoalitionStatus.ACTIVE,
            channel_id   = channel_id,
            formed_at    = datetime.utcnow(),
            dissolved_at = None,
        )
        async with self._lock:
            self._coalitions[coalition.coalition_id] = coalition
            self._roles[coalition.coalition_id] = {
                aid: (CoalitionRole.LEADER if aid == leader_id else CoalitionRole.MEMBER)
                for aid in accepted
            }

        # 4. Spawn TTL dissolution task
        self._tasks[coalition.coalition_id] = asyncio.create_task(
            self._ttl_task(coalition.coalition_id, request.coalition_ttl_secs)
        )
        self._metrics.coalitions_formed.inc()
        return coalition

    # ── _select_candidates ────────────────────────────────────────────────────

    async def _select_candidates(self, request: FormationRequest) -> list[str]:
        """Score and rank available agents by capability coverage."""
        all_available = await self._registry.find_by_capability(AgentCapability.GENERAL)
        scored: list[tuple[float, str]] = []
        for agent in all_available:
            if agent.status != AgentStatus.AVAILABLE:
                continue
            caps = agent.capabilities
            req_score  = sum(c in caps for c in request.required_capabilities)
            pref_score = sum(c in caps for c in request.preferred_capabilities) * 0.5
            if req_score < len(request.required_capabilities):
                continue  # missing a required capability — skip
            scored.append((req_score + pref_score, agent.agent_id))
        scored.sort(reverse=True)
        return [aid for _, aid in scored]

    # ── _invite_members ───────────────────────────────────────────────────────

    async def _invite_members(
        self,
        agent_ids: list[str],
        channel_id: str,
        goal_id: str,
        ttl_secs: float,
    ) -> list[str]:
        """Broadcast invitations; collect acceptances within TTL."""
        # Publish invitation message to each agent (simplified: broadcast on channel)
        await self._channel_mgr.get(channel_id).publish(
            channel_id = channel_id,
            sender_id  = agent_ids[0],  # leader sends
            msg_type   = MessageType.HELP_REQUEST,
            payload    = {"goal_id": goal_id, "invited": agent_ids},
        )
        # In production: collect HELP_RESPONSE messages; here simulate all accept
        await asyncio.sleep(min(ttl_secs * 0.1, 0.5))
        return agent_ids  # stub: all accepted

    # ── dissolve ──────────────────────────────────────────────────────────────

    async def dissolve(self, coalition_id: str, reason: str = "") -> None:
        async with self._lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return
            updated = Coalition(
                coalition_id = coalition.coalition_id,
                goal_id      = coalition.goal_id,
                leader_id    = coalition.leader_id,
                members      = coalition.members,
                status       = CoalitionStatus.DISSOLVED,
                channel_id   = coalition.channel_id,
                formed_at    = coalition.formed_at,
                dissolved_at = datetime.utcnow(),
            )
            self._coalitions[coalition_id] = updated
        await self._channel_mgr.close(coalition.channel_id)
        task = self._tasks.pop(coalition_id, None)
        if task:
            task.cancel()
        self._metrics.coalitions_dissolved.inc()

    # ── _ttl_task ─────────────────────────────────────────────────────────────

    async def _ttl_task(self, coalition_id: str, ttl_secs: float) -> None:
        await asyncio.sleep(ttl_secs)
        await self.dissolve(coalition_id, reason="TTL expired")

    # ── _evict_loop ───────────────────────────────────────────────────────────

    async def _evict_loop(self) -> None:
        while True:
            await asyncio.sleep(self._config.eviction_interval_secs)
            cutoff = datetime.utcnow() - timedelta(seconds=600)
            async with self._lock:
                stale = [
                    cid for cid, c in self._coalitions.items()
                    if c.dissolved_at and c.dissolved_at < cutoff
                ]
                for cid in stale:
                    del self._coalitions[cid]
                    self._roles.pop(cid, None)

    async def get(self, coalition_id: str) -> Coalition | None:
        return self._coalitions.get(coalition_id)

    async def snapshot(self, coalition_id: str) -> CoalitionSnapshot | None:
        c = self._coalitions.get(coalition_id)
        if c is None:
            return None
        return CoalitionSnapshot(
            coalition_id = c.coalition_id,
            status       = c.status,
            member_count = len(c.members),
            formed_at    = c.formed_at,
            dissolved_at = c.dissolved_at,
        )

    async def list_active(self) -> list[Coalition]:
        return [c for c in self._coalitions.values()
                if c.status in (CoalitionStatus.ACTIVE, CoalitionStatus.RATIFYING)]
```

---

## Factory

```python
def build_coalition_formation(
    registry:    AgentRegistry | None = None,
    channel_mgr: CollaborationChannelManager | None = None,
    consensus:   ConsensusVoting | None = None,
    negotiation: NegotiationEngine | None = None,
    config:      CoalitionConfig | None = None,
) -> CoalitionFormation:
    registry    = registry    or build_agent_registry()
    channel_mgr = channel_mgr or build_channel_manager()
    consensus   = consensus   or build_consensus_voting()
    negotiation = negotiation or build_negotiation_engine()
    config      = config      or CoalitionConfig()
    metrics     = CoalitionMetrics()
    cf = InMemoryCoalitionFormation(registry, channel_mgr, consensus, negotiation, config, metrics)
    asyncio.get_event_loop().create_task(cf._evict_loop())
    return cf
```

---

## CognitiveCycle Integration

```python
# In CognitiveCycle.__init__
self._coalition = build_coalition_formation(
    registry    = self._registry,
    channel_mgr = self._channel_mgr,
    consensus   = self._consensus,
    negotiation = self._negotiation,
)

# New method: called when a goal requires multi-agent execution
async def _coordinate_via_coalition(
    self,
    goal_id:   str,
    required_caps: list[str],
) -> Coalition | None:
    try:
        coalition = await self._coalition.form_coalition(FormationRequest(
            goal_id               = goal_id,
            required_capabilities = required_caps,
            min_members           = 2,
        ))
        # Ratify high-stakes execution via ConsensusVoting
        ratified = await self._ratify_high_stakes_goal(
            goal_id  = goal_id,
            peer_ids = list(coalition.members - {self.agent_id}),
        )
        if not ratified:
            await self._coalition.dissolve(coalition.coalition_id, "consensus failed")
            return None
        return coalition
    except RuntimeError as exc:
        logger.warning("Coalition formation failed: %s", exc)
        return None
```

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `coalition_formations_total` | Counter | Coalitions successfully formed |
| `coalition_formations_failed_total` | Counter | Formation attempts that failed |
| `coalition_dissolved_total` | Counter | Coalitions dissolved (any reason) |
| `coalition_active_gauge` | Gauge | Currently active coalitions |
| `coalition_member_count_histogram` | Histogram | Members per coalition at formation |

### PromQL Queries

```promql
# Coalition formation success rate
rate(coalition_formations_total[5m]) /
  (rate(coalition_formations_total[5m]) + rate(coalition_formations_failed_total[5m]))

# Average coalition size
rate(coalition_member_count_histogram_sum[5m]) /
  rate(coalition_member_count_histogram_count[5m])

# Alert: too many failures
rate(coalition_formations_failed_total[5m]) > 0.1
```

### Grafana Alert: Formation Failure Rate

```yaml
alert: CoalitionFormationHighFailureRate
expr: |
  rate(coalition_formations_failed_total[5m])
    / (rate(coalition_formations_total[5m]) + rate(coalition_formations_failed_total[5m]))
    > 0.20
for: 2m
labels:
  severity: warning
annotations:
  summary: "Coalition formation failure rate > 20% for 2 min"
```

---

## Full Phase 12 Integration Diagram

```
CognitiveCycle._coordinate_via_coalition()
  │
  ├─► AgentRegistry.find_by_capability()
  │     └─ returns ranked AVAILABLE agents
  │
  ├─► CollaborationChannelManager.open(channel_id)
  │     └─ creates isolated pub/sub workspace
  │
  ├─► NegotiationEngine.announce(task_offer)
  │     └─ AWARDED bid → winning agent joins coalition
  │
  ├─► InMemoryCoalitionFormation.form_coalition()
  │     └─ broadcasts HELP_REQUEST invitations
  │     └─ collects HELP_RESPONSE acceptances
  │     └─ returns Coalition(ACTIVE)
  │
  └─► ConsensusVoting.open_ballot()
        └─ members cast_vote(YES/NO/VETO)
        └─ _close() → CONSENSUS_RESULT on channel
        └─ VoteOutcome.PASS → coalition executes goal
        └─ VoteOutcome.FAIL/VETO → dissolve coalition
```

---

## Mypy Surface

| Symbol | Kind | Notes |
|--------|------|-------|
| `CoalitionStatus` | `Enum` | 5 members |
| `InvitationResponse` | `Enum` | 3 members |
| `CoalitionRole` | `Enum` | 3 members |
| `CoalitionMember` | `@dataclass(frozen=True)` | `capabilities: frozenset[str]` |
| `Coalition` | `@dataclass(frozen=True)` | `members: frozenset[str]` |
| `FormationRequest` | `@dataclass(frozen=True)` | Defaults all typed |
| `CoalitionSnapshot` | `@dataclass(frozen=True)` | Lightweight view |
| `CoalitionConfig` | `@dataclass(frozen=True)` | Defaults safe |
| `CoalitionFormation` | `Protocol` | 5 async methods |
| `InMemoryCoalitionFormation` | `class` | Implements Protocol |
| `build_coalition_formation` | `def` | Factory |

---

## Test Targets

1. `test_form_coalition_happy_path` — 2 capable agents → ACTIVE coalition returned
2. `test_form_coalition_insufficient_agents` — fewer than `min_members` raises RuntimeError
3. `test_form_coalition_missing_required_capability` — agents lacking req cap excluded
4. `test_preferred_capabilities_boost_score` — agents with preferred caps rank higher
5. `test_coalition_ttl_dissolves` — TTL expiry triggers DISSOLVED status + channel close
6. `test_dissolve_manual` — explicit dissolve sets DISSOLVED + cancels TTL task
7. `test_list_active_filters_dissolved` — dissolved coalitions absent from list_active()
8. `test_snapshot_returns_lightweight_view` — snapshot has correct member_count
9. `test_eviction_removes_stale` — coalitions dissolved >600 s ago pruned from memory
10. `test_integration_with_consensus` — PASS vote keeps coalition ACTIVE; FAIL dissolves
11. `test_max_members_cap` — coalition size never exceeds `max_members`
12. `test_cognitive_cycle_coordinate_via_coalition` — end-to-end with fake peers + fake ballot

---

## Implementation Order

1. Add `CoalitionStatus`, `InvitationResponse`, `CoalitionRole` enums to `src/asi_build/multiagent/enums.py`
2. Add frozen dataclasses (`CoalitionMember`, `Coalition`, `FormationRequest`, `CoalitionSnapshot`, `CoalitionConfig`) to `src/asi_build/multiagent/types.py`
3. Define `CoalitionFormation` Protocol in `src/asi_build/multiagent/protocols.py`
4. Implement `InMemoryCoalitionFormation._select_candidates()` with capability scoring
5. Implement `InMemoryCoalitionFormation._invite_members()` via CollaborationChannel
6. Implement `InMemoryCoalitionFormation.form_coalition()` full happy path
7. Implement `InMemoryCoalitionFormation.dissolve()` + channel teardown
8. Implement `InMemoryCoalitionFormation._ttl_task()` and `_evict_loop()`
9. Implement `CoalitionMetrics` (5 Prometheus counters/gauges/histograms)
10. Add `build_coalition_formation()` factory to `src/asi_build/multiagent/factory.py`
11. Integrate `_coordinate_via_coalition()` into `CognitiveCycle`
12. Write 12 unit tests in `tests/multiagent/test_coalition_formation.py`
13. Update `ROADMAP.md` — Phase 12 COMPLETE 🎉
14. Update `CHANGELOG.md` with Phase 12 multi-agent coordination milestone

---

## Phase 12 Completion Table 🎉

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 12.1 | AgentRegistry | [#352](https://github.com/web3guru888/asi-build/issues/352) | ✅ Spec complete |
| 12.2 | NegotiationEngine | [#355](https://github.com/web3guru888/asi-build/issues/355) | ✅ Spec complete |
| 12.3 | CollaborationChannel | [#358](https://github.com/web3guru888/asi-build/issues/358) | ✅ Spec complete |
| 12.4 | ConsensusVoting | [#361](https://github.com/web3guru888/asi-build/issues/361) | ✅ Spec complete |
| 12.5 | CoalitionFormation | [#364](https://github.com/web3guru888/asi-build/issues/364) | 🟡 In progress |

**Phase 12 = Distributed Coordination & Multi-Agent Collaboration — COMPLETE after implementation!**
