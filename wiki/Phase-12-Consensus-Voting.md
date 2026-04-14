# Phase 12.4 — ConsensusVoting

**Status**: 🟡 In Progress  
**Issue**: [#361](https://github.com/web3guru888/asi-build/issues/361)  
**Discussions**: [Show & Tell #362](https://github.com/web3guru888/asi-build/discussions/362) · [Q&A #363](https://github.com/web3guru888/asi-build/discussions/363)  
**Depends on**: [Phase 12.3 CollaborationChannel](Phase-12-Collaboration-Channel) · [Phase 12.1 AgentRegistry](Phase-12-Agent-Registry)  
**Next**: Phase 12.5 CoalitionFormation (planned)

---

## Motivation

When multiple cooperating agents must jointly commit to a high-stakes goal — a large resource allocation, an external API action, or a cross-federation plan — no single agent should be authorised to proceed alone. `ConsensusVoting` provides a **HMAC-attested, threshold-quorum ballot** mechanism: every involved agent casts a cryptographically signed vote; the system tallies results only when the quorum deadline expires or when all eligible voters have cast their ballot, and publishes the final `VoteOutcome` through `CollaborationChannel`.

---

## Enumerations

### `VoteStatus`

```python
class VoteStatus(Enum):
    PENDING    = auto()   # ballot open, awaiting votes
    QUORUM_MET = auto()   # threshold reached, but deadline not yet expired
    CLOSED     = auto()   # deadline passed; outcome computed
    RATIFIED   = auto()   # outcome PASS — goal approved for execution
    REJECTED   = auto()   # outcome FAIL/VETO/TIE — goal blocked
```

#### VoteStatus FSM

```
PENDING ──(cast_vote hits threshold)──► QUORUM_MET
PENDING ──(deadline expires)──────────► CLOSED ──(tally)──► RATIFIED | REJECTED
QUORUM_MET ──(deadline expires)───────► CLOSED ──(tally)──► RATIFIED | REJECTED
```

---

### `VoteOutcome`

```python
class VoteOutcome(Enum):
    PASS    = auto()   # ≥ threshold fraction voted YES
    FAIL    = auto()   # threshold not met within deadline
    VETO    = auto()   # one or more authoritative VETO votes received
    TIE     = auto()   # exactly 50/50 — falls back to FAIL by convention
```

---

## Data Classes

All dataclasses are **frozen** (`@dataclass(frozen=True)`) for immutable, hashable records.

### `Ballot`

```python
@dataclass(frozen=True)
class Ballot:
    ballot_id:    str              # UUID4 string
    goal_id:      str              # opaque goal identifier (links to GoalRegistry)
    eligible:     frozenset[str]   # agent_ids authorised to vote
    threshold:    float            # fraction of YES votes required (0.0–1.0)
    opened_at:    datetime
    deadline:     datetime         # UTC; _deadline_task cancels and tallies at this time
    hmac_key:     bytes            # 32-byte shared secret for vote attestation
    allow_veto:   bool = True      # if False, VETO votes are treated as NO
```

### `Vote`

```python
@dataclass(frozen=True)
class Vote:
    ballot_id:  str
    agent_id:   str
    choice:     Literal["YES", "NO", "ABSTAIN", "VETO"]
    rationale:  str                # free-text, stored for audit
    hmac_tag:   bytes              # HMAC-SHA256(ballot_id + agent_id + choice, key=ballot.hmac_key)
    cast_at:    datetime
```

### `ConsensusResult`

```python
@dataclass(frozen=True)
class ConsensusResult:
    ballot_id:   str
    goal_id:     str
    outcome:     VoteOutcome
    yes_count:   int
    no_count:    int
    veto_count:  int
    abstain_count: int
    total_cast:  int
    finalized_at: datetime
```

### `ConsensusConfig`

```python
@dataclass(frozen=True)
class ConsensusConfig:
    default_threshold:   float = 0.6   # 60% YES required
    default_ttl_secs:    float = 30.0  # ballot lifetime
    eviction_interval_secs: float = 5.0
    allow_veto:          bool  = True
    channel_id:          str   = "consensus"  # CollaborationChannel to publish results on
```

---

## Protocol

```python
class ConsensusVoting(Protocol):
    async def open_ballot(
        self,
        goal_id:    str,
        eligible:   Iterable[str],
        threshold:  float | None = None,
        ttl_secs:   float | None = None,
        hmac_key:   bytes | None = None,
    ) -> Ballot: ...

    async def cast_vote(
        self,
        ballot_id: str,
        agent_id:  str,
        choice:    Literal["YES", "NO", "ABSTAIN", "VETO"],
        rationale: str = "",
        hmac_tag:  bytes | None = None,
    ) -> VoteStatus: ...

    async def get_result(self, ballot_id: str) -> ConsensusResult | None: ...

    async def list_open(self) -> list[Ballot]: ...
```

---

## Reference Implementation: `InMemoryConsensusVoting`

```python
class InMemoryConsensusVoting:
    """Thread-safe, asyncio-based in-memory consensus voting engine."""

    def __init__(
        self,
        config:   ConsensusConfig,
        channel:  CollaborationChannel,
        metrics:  ConsensusMetrics,
    ) -> None:
        self._config   = config
        self._channel  = channel
        self._metrics  = metrics
        self._lock     = asyncio.Lock()
        self._ballots: dict[str, Ballot]         = {}
        self._votes:   dict[str, list[Vote]]     = {}
        self._results: dict[str, ConsensusResult] = {}
        self._tasks:   dict[str, asyncio.Task]   = {}

    # ── open_ballot ───────────────────────────────────────────────────────────

    async def open_ballot(
        self,
        goal_id:   str,
        eligible:  Iterable[str],
        threshold: float | None = None,
        ttl_secs:  float | None = None,
        hmac_key:  bytes | None = None,
    ) -> Ballot:
        threshold = threshold if threshold is not None else self._config.default_threshold
        ttl       = ttl_secs  if ttl_secs  is not None else self._config.default_ttl_secs
        key       = hmac_key  if hmac_key  is not None else secrets.token_bytes(32)

        ballot = Ballot(
            ballot_id  = str(uuid.uuid4()),
            goal_id    = goal_id,
            eligible   = frozenset(eligible),
            threshold  = threshold,
            opened_at  = datetime.now(tz=timezone.utc),
            deadline   = datetime.now(tz=timezone.utc) + timedelta(seconds=ttl),
            hmac_key   = key,
            allow_veto = self._config.allow_veto,
        )
        async with self._lock:
            self._ballots[ballot.ballot_id] = ballot
            self._votes[ballot.ballot_id]   = []
        self._tasks[ballot.ballot_id] = asyncio.create_task(
            self._deadline_task(ballot.ballot_id, ttl)
        )
        self._metrics.ballots_opened.inc()
        return ballot

    # ── _verify_hmac_inner ────────────────────────────────────────────────────

    def _verify_hmac_inner(
        self, ballot: Ballot, agent_id: str,
        choice: str, hmac_tag: bytes
    ) -> bool:
        """Constant-time HMAC-SHA256 verification."""
        msg      = f"{ballot.ballot_id}{agent_id}{choice}".encode()
        expected = hmac_mod.new(ballot.hmac_key, msg, digestmod="sha256").digest()
        return hmac_mod.compare_digest(expected, hmac_tag)

    # ── cast_vote ─────────────────────────────────────────────────────────────

    async def cast_vote(
        self,
        ballot_id: str,
        agent_id:  str,
        choice:    Literal["YES", "NO", "ABSTAIN", "VETO"],
        rationale: str = "",
        hmac_tag:  bytes | None = None,
    ) -> VoteStatus:
        async with self._lock:
            ballot = self._ballots.get(ballot_id)
            if ballot is None:
                raise KeyError(f"ballot {ballot_id!r} not found or already closed")
            if agent_id not in ballot.eligible:
                raise PermissionError(f"agent {agent_id!r} not eligible for ballot {ballot_id!r}")
            if any(v.agent_id == agent_id for v in self._votes[ballot_id]):
                raise ValueError(f"agent {agent_id!r} already voted on ballot {ballot_id!r}")
            if hmac_tag is not None and not self._verify_hmac_inner(ballot, agent_id, choice, hmac_tag):
                self._metrics.hmac_failures.inc()
                raise ValueError("HMAC attestation failed")

            vote = Vote(
                ballot_id = ballot_id,
                agent_id  = agent_id,
                choice    = choice,
                rationale = rationale,
                hmac_tag  = hmac_tag or b"",
                cast_at   = datetime.now(tz=timezone.utc),
            )
            self._votes[ballot_id].append(vote)
            self._metrics.votes_cast.inc()

            # Check if all eligible agents have voted
            cast_ids = {v.agent_id for v in self._votes[ballot_id]}
            if cast_ids >= ballot.eligible:
                return await self._close(ballot_id, lock_held=True)

        return VoteStatus.PENDING

    # ── _close ────────────────────────────────────────────────────────────────

    async def _close(self, ballot_id: str, lock_held: bool = False) -> VoteStatus:
        """Tally votes, compute outcome, publish to CollaborationChannel."""
        if not lock_held:
            async with self._lock:
                return await self._close(ballot_id, lock_held=True)

        ballot = self._ballots.pop(ballot_id, None)
        if ballot is None:
            return VoteStatus.CLOSED  # already closed

        votes     = self._votes.pop(ballot_id, [])
        yes       = sum(1 for v in votes if v.choice == "YES")
        no        = sum(1 for v in votes if v.choice == "NO")
        veto      = sum(1 for v in votes if v.choice == "VETO")
        abstain   = sum(1 for v in votes if v.choice == "ABSTAIN")
        total     = len(votes)

        if ballot.allow_veto and veto > 0:
            outcome = VoteOutcome.VETO
        elif total == 0:
            outcome = VoteOutcome.FAIL
        else:
            eligible_voters = len(ballot.eligible)
            yes_fraction    = yes / eligible_voters
            if yes_fraction > 0.5 and abs(yes_fraction - 0.5) < 1e-9:
                outcome = VoteOutcome.TIE
            elif yes_fraction >= ballot.threshold:
                outcome = VoteOutcome.PASS
            else:
                outcome = VoteOutcome.FAIL

        result = ConsensusResult(
            ballot_id     = ballot_id,
            goal_id       = ballot.goal_id,
            outcome       = outcome,
            yes_count     = yes,
            no_count      = no,
            veto_count    = veto,
            abstain_count = abstain,
            total_cast    = total,
            finalized_at  = datetime.now(tz=timezone.utc),
        )
        self._results[ballot_id] = result

        # Publish to CollaborationChannel
        await self._channel.publish(
            channel_id  = self._config.channel_id,
            sender_id   = "consensus-voting",
            msg_type    = MessageType.CONSENSUS_RESULT,
            payload     = result.__dict__,
        )
        self._metrics.ballots_closed.inc()
        if outcome == VoteOutcome.PASS:
            self._metrics.ratifications.inc()
        return VoteStatus.RATIFIED if outcome == VoteOutcome.PASS else VoteStatus.REJECTED

    # ── _deadline_task ────────────────────────────────────────────────────────

    async def _deadline_task(self, ballot_id: str, ttl_secs: float) -> None:
        """Wait for TTL then force-close the ballot."""
        await asyncio.sleep(ttl_secs)
        await self._close(ballot_id)

    # ── _evict_closed ─────────────────────────────────────────────────────────

    async def _evict_closed(self) -> None:
        """Periodic cleanup of old results to bound memory growth."""
        while True:
            await asyncio.sleep(self._config.eviction_interval_secs)
            cutoff = datetime.now(tz=timezone.utc) - timedelta(seconds=300)
            async with self._lock:
                stale = [bid for bid, r in self._results.items()
                         if r.finalized_at < cutoff]
                for bid in stale:
                    del self._results[bid]

    async def get_result(self, ballot_id: str) -> ConsensusResult | None:
        return self._results.get(ballot_id)

    async def list_open(self) -> list[Ballot]:
        async with self._lock:
            return list(self._ballots.values())
```

---

## Factory

```python
def build_consensus_voting(
    config:  ConsensusConfig | None = None,
    channel: CollaborationChannel | None = None,
) -> ConsensusVoting:
    config  = config  or ConsensusConfig()
    channel = channel or build_collaboration_channel()
    metrics = ConsensusMetrics()
    cv = InMemoryConsensusVoting(config, channel, metrics)
    asyncio.get_event_loop().create_task(cv._evict_closed())
    return cv
```

---

## CognitiveCycle Integration

```python
# In CognitiveCycle.__init__
self._consensus = build_consensus_voting(channel=self._channel)

# New method
async def _ratify_high_stakes_goal(
    self,
    goal_id:    str,
    peer_ids:   list[str],
    threshold:  float = 0.6,
    ttl_secs:   float = 30.0,
) -> bool:
    ballot = await self._consensus.open_ballot(
        goal_id   = goal_id,
        eligible  = peer_ids + [self.agent_id],
        threshold = threshold,
        ttl_secs  = ttl_secs,
    )
    # Cast own vote (YES by default; replace with actual policy)
    await self._consensus.cast_vote(
        ballot_id = ballot.ballot_id,
        agent_id  = self.agent_id,
        choice    = "YES",
        rationale = "initiator auto-approves",
    )
    # Broadcast ballot to peers via CollaborationChannel
    await self._channel.publish(
        channel_id = "consensus",
        sender_id  = self.agent_id,
        msg_type   = MessageType.HELP_REQUEST,
        payload    = {"ballot_id": ballot.ballot_id, "goal_id": goal_id},
    )
    # Await result (peers vote asynchronously)
    await asyncio.sleep(ttl_secs + 0.1)
    result = await self._consensus.get_result(ballot.ballot_id)
    return result is not None and result.outcome == VoteOutcome.PASS
```

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `consensus_ballots_opened_total` | Counter | Ballots opened |
| `consensus_votes_cast_total` | Counter | Individual votes received |
| `consensus_ballots_closed_total` | Counter | Ballots finalized (any outcome) |
| `consensus_ratifications_total` | Counter | Ballots that passed (PASS outcome) |
| `consensus_hmac_failures_total` | Counter | HMAC attestation failures |

### PromQL Queries

```promql
# Pass rate over last 5 minutes
rate(consensus_ratifications_total[5m]) / rate(consensus_ballots_closed_total[5m])

# HMAC failure rate (security alarm)
rate(consensus_hmac_failures_total[5m]) > 0.01

# Votes-per-ballot ratio
rate(consensus_votes_cast_total[5m]) / rate(consensus_ballots_opened_total[5m])
```

---

## Mypy Surface

| Symbol | Kind | Notes |
|--------|------|-------|
| `VoteStatus` | `Enum` | 5 members |
| `VoteOutcome` | `Enum` | 4 members |
| `Ballot` | `@dataclass(frozen=True)` | `hmac_key: bytes` |
| `Vote` | `@dataclass(frozen=True)` | `choice: Literal[...]` |
| `ConsensusResult` | `@dataclass(frozen=True)` | All ints, no floats |
| `ConsensusConfig` | `@dataclass(frozen=True)` | Defaults safe |
| `ConsensusVoting` | `Protocol` | 4 async methods |
| `InMemoryConsensusVoting` | `class` | Implements Protocol |
| `build_consensus_voting` | `def` | Factory |

---

## Test Targets

1. `test_open_ballot_returns_ballot` — UUID, deadline future, eligible set
2. `test_cast_vote_happy_path` — YES vote returns PENDING if below threshold
3. `test_quorum_closes_ballot` — all eligible vote YES → RATIFIED immediately
4. `test_deadline_closes_ballot` — TTL expiry triggers `_close`
5. `test_veto_overrides_majority` — 3 YES + 1 VETO → VETO outcome
6. `test_abstain_not_counted_as_yes` — abstain → FAIL if below threshold
7. `test_duplicate_vote_raises` — second vote from same agent raises ValueError
8. `test_ineligible_vote_raises` — unknown agent_id raises PermissionError
9. `test_hmac_verification_constant_time` — valid HMAC passes, mutated fails
10. `test_result_published_to_channel` — `_close` publishes CONSENSUS_RESULT event
11. `test_eviction_removes_stale_results` — old results pruned after 5 min
12. `test_cognitive_cycle_ratify_high_stakes_goal` — integration test with fake peers

---

## Implementation Order

1. Add `VoteStatus` and `VoteOutcome` enums to `src/asi_build/multiagent/enums.py`
2. Add frozen dataclasses (`Ballot`, `Vote`, `ConsensusResult`, `ConsensusConfig`) to `src/asi_build/multiagent/types.py`
3. Define `ConsensusVoting` Protocol in `src/asi_build/multiagent/protocols.py`
4. Implement `InMemoryConsensusVoting._verify_hmac_inner()` with `hmac.compare_digest`
5. Implement `InMemoryConsensusVoting.open_ballot()` with `_deadline_task` spawn
6. Implement `InMemoryConsensusVoting.cast_vote()` with double-vote guard
7. Implement `InMemoryConsensusVoting._close()` with tally logic and channel publish
8. Implement `ConsensusMetrics` (5 Prometheus counters) in `src/asi_build/multiagent/metrics.py`
9. Wire `MessageType.CONSENSUS_RESULT` into `CollaborationChannel` (Phase 12.3 extension)
10. Add `build_consensus_voting()` factory to `src/asi_build/multiagent/factory.py`
11. Add `_evict_closed()` background task to factory startup
12. Integrate `_ratify_high_stakes_goal()` into `CognitiveCycle`
13. Write 12 unit tests in `tests/multiagent/test_consensus_voting.py`
14. Update `pyproject.toml` dependencies (no new deps — uses stdlib `hmac` and `secrets`)

---

## Phase 12 Roadmap

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 12.1 | AgentRegistry | [#352](https://github.com/web3guru888/asi-build/issues/352) | ✅ Spec complete |
| 12.2 | NegotiationEngine | [#355](https://github.com/web3guru888/asi-build/issues/355) | ✅ Spec complete |
| 12.3 | CollaborationChannel | [#358](https://github.com/web3guru888/asi-build/issues/358) | ✅ Spec complete |
| 12.4 | ConsensusVoting | [#361](https://github.com/web3guru888/asi-build/issues/361) | 🟡 In progress |
| 12.5 | CoalitionFormation | (planned) | 📋 Planned |
