# Phase 12.4 — ConsensusVoting

**Module**: `asi.multi_agent.consensus`
**Phase**: 12 — Multi-Agent Collaboration
**Depends on**: [AgentRegistry](Phase-12-Agent-Registry), [NegotiationEngine](Phase-12-Negotiation-Engine), [CollaborationChannel](Phase-12-Collaboration-Channel)
**Next**: Phase 12.5 — CoalitionFormation

---

## Overview

`ConsensusVoting` is the **governance layer** of the multi-agent collaboration stack. It enables a coalition of agents to ratify high-stakes decisions — resource allocation, policy changes, irreversible external actions — through threshold-quorum voting with cryptographic attestation and deadline enforcement.

```
AgentRegistry (#352) → NegotiationEngine (#355) → CollaborationChannel (#358) → ConsensusVoting (#361) → CoalitionFormation (12.5)
```

---

## Enums

### `VoteStatus` (5 states)

```python
class VoteStatus(str, Enum):
    PENDING   = "pending"    # ballot open, collecting votes
    PASSED    = "passed"     # quorum reached, decision ratified
    FAILED    = "failed"     # quorum not reached before deadline (or VETO)
    CANCELLED = "cancelled"  # proposer cancelled before deadline
    EXPIRED   = "expired"    # deadline elapsed without quorum
```

### `VoteOutcome` (4 values)

```python
class VoteOutcome(str, Enum):
    YES     = "yes"
    NO      = "no"
    ABSTAIN = "abstain"   # recorded but does not count toward quorum
    VETO    = "veto"      # single VETO → FAILED immediately (if allow_veto=True)
```

---

## Frozen dataclasses

```python
@dataclass(frozen=True)
class Ballot:
    ballot_id:   str
    proposal:    str              # human-readable description
    proposer_id: str              # AgentDID of proposing agent
    eligible:    frozenset[str]   # AgentDIDs allowed to vote
    threshold:   float            # 0.0–1.0 fraction required for PASSED
    deadline:    datetime         # UTC
    created_at:  datetime

@dataclass(frozen=True)
class Vote:
    ballot_id:  str
    voter_id:   str
    outcome:    VoteOutcome
    rationale:  str               # optional justification
    hmac_sig:   str               # HMAC-SHA256(ballot_id:voter_id:outcome:rationale)
    cast_at:    datetime

@dataclass(frozen=True)
class ConsensusResult:
    ballot_id:    str
    status:       VoteStatus
    yes_count:    int
    no_count:     int
    abstain_count:int
    veto_count:   int
    total_cast:   int
    threshold_met:bool
    closed_at:    datetime

@dataclass(frozen=True)
class ConsensusConfig:
    default_threshold: float = 0.67   # super-majority default
    default_ttl_secs:  int   = 300    # 5-minute ballot window
    hmac_secret:       str   = ""     # empty → skip HMAC verification
    allow_veto:        bool  = True
    max_open_ballots:  int   = 256
    eviction_secs:     int   = 3600   # closed ballot TTL in memory
```

---

## `ConsensusVoting` Protocol

```python
class ConsensusVoting(Protocol):
    async def open_ballot(
        self,
        proposal:    str,
        proposer_id: str,
        eligible:    Iterable[str],
        threshold:   float | None = None,
        ttl_secs:    int   | None = None,
    ) -> Ballot: ...

    async def cast_vote(
        self,
        ballot_id: str,
        voter_id:  str,
        outcome:   VoteOutcome,
        rationale: str = "",
        hmac_sig:  str = "",
    ) -> ConsensusResult: ...

    async def cancel_ballot(self, ballot_id: str, requester_id: str) -> None: ...
    async def get_result(self, ballot_id: str) -> ConsensusResult: ...
    async def list_open(self) -> list[Ballot]: ...
```

---

## `InMemoryConsensusVoting`

### Internal state

| Attribute | Type | Purpose |
|-----------|------|---------|
| `_ballots` | `dict[str, Ballot]` | All open ballots by ballot_id |
| `_votes` | `dict[str, dict[str, Vote]]` | ballot_id → voter_id → Vote |
| `_results` | `dict[str, ConsensusResult]` | Closed ballots |
| `_tasks` | `dict[str, asyncio.Task]` | Deadline watcher tasks |
| `_lock` | `asyncio.Lock` | Protects all mutable state |
| `_config` | `ConsensusConfig` | Runtime configuration |
| `_channel` | `CollaborationChannel` | For CONSENSUS_RESULT events |

### `open_ballot()`

1. Validate `len(eligible) > 0`
2. Check `len(_ballots) < config.max_open_ballots`
3. Build `Ballot(ballot_id=uuid4(), eligible=frozenset(eligible), threshold=threshold or config.default_threshold, deadline=now+ttl)`
4. Store in `_ballots`
5. Schedule `_deadline_task(ballot_id, ttl_secs)` via `asyncio.create_task()`
6. Increment `OPEN_BALLOTS` gauge

### `_verify_hmac_inner()`

```python
payload = f"{ballot_id}:{voter_id}:{outcome.value}:{rationale}".encode()
expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
return hmac.compare_digest(expected, provided_sig)
```

### `cast_vote()`

1. Look up ballot; raise `KeyError` if not found
2. Raise `ValueError` if ballot already closed
3. Raise `ValueError` if `voter_id` not in `ballot.eligible`
4. Raise `ValueError` if `voter_id` already voted
5. If `hmac_secret` set and `hmac_sig` provided: verify; raise `ValueError` on mismatch
6. Append `Vote` to `_votes[ballot_id]`
7. If VETO and `allow_veto`: `return await _close(ballot_id, VoteStatus.FAILED)`
8. If `yes_count / len(eligible) >= threshold`: `return await _close(ballot_id, VoteStatus.PASSED)`
9. Return live tally with `status=PENDING`

### `_close()`

```python
async def _close(self, ballot_id: str, status: VoteStatus) -> ConsensusResult:
    # cancel deadline task if still running
    if task := self._tasks.pop(ballot_id, None):
        task.cancel()
    votes = self._votes.get(ballot_id, {}).values()
    yes = sum(1 for v in votes if v.outcome == VoteOutcome.YES)
    no  = sum(1 for v in votes if v.outcome == VoteOutcome.NO)
    ab  = sum(1 for v in votes if v.outcome == VoteOutcome.ABSTAIN)
    vt  = sum(1 for v in votes if v.outcome == VoteOutcome.VETO)
    eligible = self._ballots[ballot_id].eligible
    threshold = self._ballots[ballot_id].threshold
    result = ConsensusResult(
        ballot_id=ballot_id, status=status,
        yes_count=yes, no_count=no, abstain_count=ab, veto_count=vt,
        total_cast=yes+no+ab+vt,
        threshold_met=(yes / len(eligible)) >= threshold and vt == 0,
        closed_at=datetime.utcnow(),
    )
    self._results[ballot_id] = result
    await self._channel.publish(
        workspace_id=ballot_id, sender_id="consensus",
        msg_type="CONSENSUS_RESULT", payload=asdict(result),
    )
    # update metrics
    if status == VoteStatus.PASSED:
        BALLOTS_PASSED.inc()
    else:
        BALLOTS_FAILED.inc()
    OPEN_BALLOTS.dec()
    return result
```

### `_deadline_task()`

```python
async def _deadline_task(self, ballot_id: str, ttl_secs: int) -> None:
    await asyncio.sleep(ttl_secs)
    async with self._lock:
        if ballot_id not in self._results:
            await self._close(ballot_id, VoteStatus.EXPIRED)
```

### `_evict_closed()`

Background loop (runs every `eviction_secs / 10`):

```python
async def _evict_closed(self) -> None:
    while True:
        await asyncio.sleep(self._config.eviction_secs / 10)
        cutoff = datetime.utcnow() - timedelta(seconds=self._config.eviction_secs)
        expired = [bid for bid, r in self._results.items() if r.closed_at < cutoff]
        for bid in expired:
            self._results.pop(bid, None)
            self._ballots.pop(bid, None)
            self._votes.pop(bid, None)
```

---

## Factory

```python
def build_consensus_voting(
    channel: CollaborationChannel,
    config:  ConsensusConfig | None = None,
) -> ConsensusVoting:
    return InMemoryConsensusVoting(
        channel=channel,
        config=config or ConsensusConfig(),
    )
```

---

## `CognitiveCycle` integration

```python
class CognitiveCycle:
    async def _ratify_high_stakes_goal(self, goal: Goal) -> bool:
        """Open a ballot; block on CollaborationChannel until result; return True iff PASSED."""
        eligible = [a.agent_id for a in self._registry.list_agents(status=AgentStatus.AVAILABLE)]
        ballot = await self._consensus.open_ballot(
            proposal=f"execute goal {goal.goal_id}: {goal.description}",
            proposer_id=self._agent_id,
            eligible=eligible,
        )
        async for msg in self._channel.subscribe(workspace_id=ballot.ballot_id):
            if msg.msg_type == "CONSENSUS_RESULT":
                result = ConsensusResult(**msg.payload)
                return result.status == VoteStatus.PASSED
        return False
```

---

## `VoteStatus` FSM

```
PENDING ──yes_count/eligible >= threshold──► PASSED
PENDING ──any VETO (allow_veto=True)──────► FAILED
PENDING ──deadline elapsed─────────────────► EXPIRED
PENDING ──proposer cancel─────────────────► CANCELLED
```

---

## Threshold guide

| Scenario | `threshold` |
|----------|-------------|
| Routine delegation | 0.51 |
| Resource allocation | 0.67 (default) |
| Policy change | 0.75 |
| Irreversible external action | 0.90 |
| Emergency unanimous | 1.00 |

---

## Prometheus metrics

| Metric | Type | Description |
|--------|------|-------------|
| `consensus_ballots_opened_total` | Counter | Total ballots created |
| `consensus_ballots_passed_total` | Counter | Ballots reaching quorum |
| `consensus_ballots_failed_total` | Counter | Ballots failing/expiring |
| `consensus_votes_cast_total` | Counter | Total votes cast |
| `consensus_open_ballots` | Gauge | Currently open ballots |

**PromQL examples**:
```promql
# Pass rate
rate(consensus_ballots_passed_total[5m]) / rate(consensus_ballots_opened_total[5m])

# Open ballot accumulation alert
consensus_open_ballots > 20
```

---

## mypy type coverage

| Symbol | Signature |
|--------|-----------|
| `open_ballot` | `async (str, str, Iterable[str], float?, int?) -> Ballot` |
| `cast_vote` | `async (str, str, VoteOutcome, str, str) -> ConsensusResult` |
| `cancel_ballot` | `async (str, str) -> None` |
| `get_result` | `async (str) -> ConsensusResult` |
| `list_open` | `async () -> list[Ballot]` |
| `_verify_hmac_inner` | `async (str, str, VoteOutcome, str, str) -> bool` |
| `_close` | `async (str, VoteStatus) -> ConsensusResult` |
| `_deadline_task` | `async (str, int) -> None` |

---

## Test targets (12 minimum)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_ballot_passed_super_majority` | 3/3 YES → PASSED |
| 2 | `test_ballot_failed_below_threshold` | 1/3 YES, 2/3 NO → FAILED |
| 3 | `test_ballot_veto_short_circuits` | 1 VETO → FAILED immediately |
| 4 | `test_ballot_expired_after_ttl` | no votes, ttl elapsed → EXPIRED |
| 5 | `test_ballot_cancelled_by_proposer` | cancel before deadline → CANCELLED |
| 6 | `test_ballot_ineligible_voter_rejected` | voter not in eligible → ValueError |
| 7 | `test_ballot_duplicate_vote_rejected` | second vote → ValueError |
| 8 | `test_hmac_verification_success` | valid sig → accepted |
| 9 | `test_hmac_verification_failure` | tampered sig → ValueError |
| 10 | `test_abstain_not_counted_for_quorum` | ABSTAIN not in yes_count |
| 11 | `test_channel_event_on_close` | CollaborationChannel receives CONSENSUS_RESULT |
| 12 | `test_eviction_removes_old_results` | closed ballot purged after eviction_secs |

---

## Implementation order (14 steps)

1. `VoteStatus` / `VoteOutcome` enums
2. `Ballot`, `Vote`, `ConsensusResult`, `ConsensusConfig` frozen dataclasses
3. `ConsensusVoting` Protocol
4. `InMemoryConsensusVoting.__init__` (lock, dicts, config, channel)
5. `open_ballot()` + `asyncio.create_task(_deadline_task)`
6. `_verify_hmac_inner()` helper
7. `cast_vote()` — eligibility, HMAC, VETO short-circuit, quorum eval
8. `_close()` — ConsensusResult build + channel publish + metrics
9. `cancel_ballot()` — task cancel + `_close(CANCELLED)`
10. `get_result()` / `list_open()`
11. `_evict_closed()` background loop
12. Prometheus metrics (`Counter` × 4, `Gauge` × 1)
13. `build_consensus_voting()` factory
14. All 12 test targets

---

## Phase 12 roadmap

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 12.1 | AgentRegistry | #352 | ✅ |
| 12.2 | NegotiationEngine | #355 | ✅ |
| 12.3 | CollaborationChannel | #358 | ✅ |
| 12.4 | ConsensusVoting | #361 | 🟡 |
| 12.5 | CoalitionFormation | — | ⏳ |

**Discussions**: [Show & Tell #362](https://github.com/web3guru888/asi-build/discussions/362) · [Q&A #363](https://github.com/web3guru888/asi-build/discussions/363)
