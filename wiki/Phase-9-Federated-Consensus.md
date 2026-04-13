# Phase 9.4 — FederatedConsensus

Byzantine-fault-tolerant ordered agreement over a peer federation using **Raft-lite leader election** and **threshold-signature quorum certificates**.

> **Status**: 🟡 Spec complete — Issue #310  
> **Depends on**: Phase 9.1 FederationGateway · Phase 9.2 FederatedBlackboard · Phase 9.3 FederatedTaskRouter  
> **Discussions**: #312 (Show & Tell) · #313 (Q&A) · #314 (Phase 9.5 Ideas)

---

## Table of Contents

1. [Motivation](#motivation)
2. [Data Model](#data-model)
3. [Protocol — `FederatedConsensus`](#protocol--federatedconsensus)
4. [Concrete Implementation](#concrete-implementation--inmemoryfederatedconsensus)
5. [Leader Election (Raft-lite)](#leader-election-raft-lite)
6. [Proposal Lifecycle](#proposal-lifecycle)
7. [Threshold Signature](#threshold-signature-stub)
8. [CognitiveCycle Integration](#cognitivecycle-integration)
9. [Prometheus Metrics](#prometheus-metrics)
10. [Test Targets](#test-targets-12)
11. [mypy Strict Compatibility](#mypy-strict-compatibility)
12. [Implementation Order](#implementation-order-14-steps)
13. [Phase 9 Roadmap](#phase-9-roadmap)

---

## Motivation

Without consensus, two agents in the federation might:
- Route the same task to the same peer simultaneously (duplicate execution)
- Apply conflicting capability-registry updates (split routing tables)
- Make incompatible configuration changes (no authoritative version)

`FederatedConsensus` solves this with a **single binding decision per proposal**: either the cluster commits (with a cryptographically verifiable `CommitCertificate`) or it aborts, never half-commits.

---

## Data Model

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, FrozenSet, Sequence
import time

class ConsensusRole(str, Enum):
    FOLLOWER  = "follower"
    CANDIDATE = "candidate"
    LEADER    = "leader"

class ConsensusState(str, Enum):
    IDLE        = "idle"
    PROPOSING   = "proposing"
    VOTING      = "voting"
    COMMITTED   = "committed"
    ABORTED     = "aborted"

@dataclass(frozen=True)
class ProposalID:
    """Monotonic, globally unique proposal identifier.
    Safe as dict key and set element (frozen + hashable).
    """
    term:        int   # Raft term — incremented per leader tenure
    seq:         int   # per-term sequence number
    origin_peer: str   # DID of the proposing peer

@dataclass(frozen=True)
class ConsensusProposal:
    proposal_id:     ProposalID
    payload:         Any          # JSON-serialisable application data
    required_quorum: int          # minimum granted votes; default ceil((n+1)/2)
    ttl_ms:          int = 5_000  # absolute proposal deadline (ms)

@dataclass(frozen=True)
class ConsensusVote:
    proposal_id:  ProposalID
    voter_peer:   str        # DID of the voting peer
    granted:      bool
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))

@dataclass(frozen=True)
class CommitCertificate:
    """Threshold-signature proof that a quorum of peers granted a proposal."""
    proposal_id:   ProposalID
    committed_at:  int              # epoch ms
    signers:       FrozenSet[str]   # DIDs that voted granted=True
    threshold_sig: bytes            # SHA-256 stub → BLS aggregate in production

@dataclass
class ConsensusSnapshot:
    role:              ConsensusRole
    term:              int
    commit_index:      int
    known_peers:       int
    pending_proposals: int
    committed_count:   int
    aborted_count:     int
```

### Key design choices

| Choice | Reason |
|--------|--------|
| `ProposalID` frozen | Safe as `dict` key; `(term, seq, origin)` is globally unique within a cluster lifetime |
| `CommitCertificate.signers: FrozenSet[str]` | Set membership is the proof; order is irrelevant |
| `CommitCertificate.threshold_sig: bytes` | Swappable: SHA-256 stub today → `blspy.AugSchemeMPL.aggregate()` in production |
| `ConsensusRole(str, Enum)` | Prometheus label-safe without `.value` call |
| `ConsensusState` separate from role | Role = node's position in the cluster; State = proposal lifecycle position |

---

## Protocol — `FederatedConsensus`

```python
from typing import Protocol, runtime_checkable, AsyncIterator

@runtime_checkable
class FederatedConsensus(Protocol):
    """Byzantine-fault-tolerant ordered agreement over a peer federation."""

    async def propose(
        self,
        payload: Any,
        required_quorum: int | None = None,
        ttl_ms: int = 5_000,
    ) -> ProposalID:
        """Broadcast a new proposal; returns its ID.
        Only the current LEADER may propose — raises PermissionError otherwise."""

    async def vote(self, proposal_id: ProposalID, granted: bool) -> None:
        """Cast a local vote for or against a pending proposal.
        No-op if proposal already committed or expired."""

    async def commit_stream(self) -> AsyncIterator[CommitCertificate]:
        """Async generator yielding CommitCertificates as proposals reach quorum."""

    async def abort_stream(self) -> AsyncIterator[ProposalID]:
        """Async generator yielding ProposalIDs that expired or were rejected."""

    async def snapshot(self) -> ConsensusSnapshot: ...
    async def close(self) -> None: ...
```

---

## Concrete Implementation — `InMemoryFederatedConsensus`

### Constructor

```python
def __init__(
    self,
    peer_id: str,
    gateway: FederationGateway,
    router: FederatedTaskRouter,
    *,
    election_timeout_ms: tuple[int, int] = (250, 450),
    heartbeat_interval_ms: int = 150,
    max_pending_proposals: int = 64,
    max_log_entries: int = 4_096,
) -> None:
    self._peer_id          = peer_id
    self._gateway          = gateway
    self._router           = router
    self._term:        int = 0
    self._voted_for:   str | None = None
    self._role             = ConsensusRole.FOLLOWER
    self._commit_index: int = 0
    self._seq_counter:  int = 0
    self._log:          list[CommitCertificate] = []
    self._pending:      dict[ProposalID, _PendingRound] = {}
    self._commit_q      = asyncio.Queue[CommitCertificate]()
    self._abort_q       = asyncio.Queue[ProposalID]()
    self._heartbeat_seen = asyncio.Event()
    self._heartbeat_task: asyncio.Task | None = None
    self._election_task:  asyncio.Task | None = None
```

### `_PendingRound` internal helper

```python
@dataclass
class _PendingRound:
    proposal:     ConsensusProposal
    votes:        dict[str, ConsensusVote]   # voter_peer → vote
    deadline_ms:  int
    started_at:   int = field(default_factory=lambda: int(time.time() * 1000))

    def granted_count(self) -> int:
        return sum(1 for v in self.votes.values() if v.granted)

    def is_expired(self) -> bool:
        return int(time.time() * 1000) > self.deadline_ms
```

---

## Leader Election (Raft-lite)

```
Term N:  [F][F][F][F][F]   all followers, random election timeouts
          ↓  250–450 ms
         [F][F][C][F][F]   node C times out → increments term → CANDIDATE
                ↓
         broadcast RequestVote(term=N+1, candidate=C)
                ↓
         [F][F][L][F][F]   receives 3/5 votes → transitions to LEADER
                ↓
         heartbeat every 150 ms → followers reset election timeout
```

### Election loop sketch

```python
async def _run_election(self) -> None:
    import random
    while True:
        timeout = random.uniform(
            self._election_timeout_ms[0] / 1000,
            self._election_timeout_ms[1] / 1000,
        )
        try:
            await asyncio.wait_for(self._heartbeat_seen.wait(), timeout=timeout)
            self._heartbeat_seen.clear()
        except asyncio.TimeoutError:
            self._term += 1
            self._voted_for = self._peer_id
            self._role = ConsensusRole.CANDIDATE
            _ROLE_TRANSITIONS.labels(
                from_role=ConsensusRole.FOLLOWER.value,
                to_role=ConsensusRole.CANDIDATE.value,
            ).inc()
            await self._gateway.broadcast({
                "type": "request_vote",
                "term": self._term,
                "candidate": self._peer_id,
            })
```

### Heartbeat loop sketch

```python
async def _send_heartbeat(self) -> None:
    while self._role == ConsensusRole.LEADER:
        await self._gateway.broadcast({
            "type": "heartbeat",
            "term": self._term,
            "leader": self._peer_id,
        })
        await asyncio.sleep(self._heartbeat_interval_ms / 1000)
```

### Key invariants

- A node votes for at most **one** candidate per term (`voted_for` fencing)
- Messages from lower terms are **silently dropped** (stale-term guard)
- Heartbeat detection uses `asyncio.Event`, **not** busy-wait
- Only a LEADER may call `propose()` — `PermissionError` otherwise

---

## Proposal Lifecycle

```
Leader                    Follower A         Follower B
  │                           │                  │
  ├──propose(payload)─────────┤                  │
  │  ProposalID(term=3,seq=1) │                  │
  │                           │                  │
  ├─broadcast ConsensusProposal────────────────────┤
  │                           │                  │
  │◄──vote(pid, granted=True)─┤                  │
  │◄──vote(pid, granted=True)─────────────────────┤
  │                           │                  │
  ├─_commit()─────────────────┤                  │
  │  CommitCertificate        │                  │
  │  signers={A, B}           │                  │
  │  threshold_sig=sha256(…)  │                  │
  │                           │                  │
  └──commit_stream() emits────┘                  │
```

### `propose()` sketch

```python
async def propose(self, payload: Any, required_quorum: int | None = None, ttl_ms: int = 5_000) -> ProposalID:
    if self._role != ConsensusRole.LEADER:
        raise PermissionError("Only the current leader may propose")
    self._seq_counter += 1
    pid = ProposalID(term=self._term, seq=self._seq_counter, origin_peer=self._peer_id)
    peers = await self._gateway.list_peers()
    quorum = required_quorum or math.ceil((len(peers) + 1) / 2)
    proposal = ConsensusProposal(proposal_id=pid, payload=payload, required_quorum=quorum, ttl_ms=ttl_ms)
    self._pending[pid] = _PendingRound(
        proposal=proposal,
        votes={},
        deadline_ms=int(time.time() * 1000) + ttl_ms,
    )
    _PENDING_PROPOSALS.set(len(self._pending))
    await self._gateway.broadcast({"type": "proposal", "data": _serialise(proposal)})
    return pid
```

### `vote()` + quorum check sketch

```python
async def vote(self, proposal_id: ProposalID, granted: bool) -> None:
    round_ = self._pending.get(proposal_id)
    if round_ is None:
        return  # already committed or expired
    vote = ConsensusVote(proposal_id=proposal_id, voter_peer=self._peer_id, granted=granted)
    round_.votes[self._peer_id] = vote
    if round_.granted_count() >= round_.proposal.required_quorum:
        await self._commit(round_)

async def _commit(self, round_: _PendingRound) -> None:
    granted_votes = [v for v in round_.votes.values() if v.granted]
    cert = CommitCertificate(
        proposal_id=round_.proposal.proposal_id,
        committed_at=int(time.time() * 1000),
        signers=frozenset(v.voter_peer for v in granted_votes),
        threshold_sig=_aggregate_signatures(granted_votes),
    )
    self._log.append(cert)
    if len(self._log) > self._max_log_entries:
        self._log.pop(0)  # FIFO eviction of oldest
    self._commit_index += 1
    del self._pending[round_.proposal.proposal_id]
    await self._commit_q.put(cert)
    _PROPOSALS_TOTAL.labels(outcome="committed").inc()
    _PENDING_PROPOSALS.set(len(self._pending))
    _COMMIT_LATENCY.observe((cert.committed_at - round_.started_at) / 1000)
    _TERM_GAUGE.set(self._term)
```

---

## Threshold Signature Stub

```python
def _aggregate_signatures(votes: Sequence[ConsensusVote]) -> bytes:
    """Production: BLS aggregate sig via blspy.AugSchemeMPL.aggregate().
    Stub: SHA-256 of sorted voter DIDs + proposal_id bytes — tamper-evident."""
    import hashlib, json
    payload_str = json.dumps({
        "signers": sorted(v.voter_peer for v in votes if v.granted),
        "proposal": str(votes[0].proposal_id),
    }, sort_keys=True)
    return hashlib.sha256(payload_str.encode()).digest()
```

### BLS upgrade path (no interface change)

```python
# Install: pip install blspy
from blspy import AugSchemeMPL

def _aggregate_signatures(votes: Sequence[ConsensusVote]) -> bytes:
    sigs = [
        peer_signing_key(v.voter_peer).sign(proposal_bytes(v.proposal_id))
        for v in votes if v.granted
    ]
    return bytes(AugSchemeMPL.aggregate(sigs))
```

---

## CognitiveCycle Integration

```python
# In CognitiveCycle.tick() — LEARNING phase
async def _learning_phase(self) -> None:
    ...
    # Apply committed consensus decisions
    if cert := await self._blackboard.pop(CONSENSUS_COMMITTED_KEY, timeout_ms=0):
        await self._consensus_module.apply_committed(cert.payload)
    ...
```

**Blackboard key contracts**:

| Key | Type | Written by | Read by |
|-----|------|-----------|---------|
| `consensus:committed` | `CommitCertificate` | `FederatedConsensus._commit()` | `CognitiveCycle._learning_phase()` |
| `consensus:aborted` | `ProposalID` | TTL eviction loop | Caller retry logic |
| `consensus:role` | `ConsensusRole` | Election transition | Any observer |

---

## Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

_PROPOSALS_TOTAL = Counter(
    "asi_consensus_proposals_total",
    "Total proposal lifecycle events",
    ["outcome"],
)
_ROLE_TRANSITIONS = Counter(
    "asi_consensus_role_transitions_total",
    "Raft role changes",
    ["from_role", "to_role"],
)
_COMMIT_LATENCY = Histogram(
    "asi_consensus_commit_latency_seconds",
    "Wall time from propose() to _commit()",
)
_PENDING_PROPOSALS = Gauge(
    "asi_consensus_pending_proposals",
    "In-flight proposals awaiting quorum",
)
_TERM_GAUGE = Gauge(
    "asi_consensus_term",
    "Current Raft term (monotonic fencing token)",
)

# Pre-init all label combinations
for outcome in ("committed", "aborted", "expired"):
    _PROPOSALS_TOTAL.labels(outcome=outcome)
for f in ConsensusRole:
    for t in ConsensusRole:
        if f != t:
            _ROLE_TRANSITIONS.labels(from_role=f.value, to_role=t.value)
```

### Useful PromQL

```promql
# Commit success rate (5-minute window)
rate(asi_consensus_proposals_total{outcome="committed"}[5m])
  / rate(asi_consensus_proposals_total[5m])

# Leader election frequency — alert if > 6/hour
increase(asi_consensus_role_transitions_total{to_role="leader"}[1h]) > 6

# p99 commit latency
histogram_quantile(0.99, rate(asi_consensus_commit_latency_seconds_bucket[5m]))

# Pending backpressure
asi_consensus_pending_proposals > 10
```

---

## Test Targets (12)

| # | Test | Key assertion |
|---|------|--------------|
| 1 | `test_propose_and_commit_happy_path` | 3-peer cluster; CommitCertificate emitted with 2/3 quorum |
| 2 | `test_quorum_not_reached_aborts` | 1 granted + 2 withheld; abort emitted after TTL |
| 3 | `test_term_fencing_stale_message_dropped` | Stale-term RequestVote; term unchanged |
| 4 | `test_leader_election_majority` | 5 followers; exactly one LEADER within 500 ms |
| 5 | `test_split_vote_resolves_via_retry` | Forced split vote; second election succeeds |
| 6 | `test_threshold_sig_deterministic` | Same voters + proposal → same `bytes` |
| 7 | `test_concurrent_proposals_ordered` | 10 concurrent proposals; commit log ordered by ProposalID |
| 8 | `test_log_size_cap_evicts_oldest` | Fill beyond `max_log_entries`; oldest evicted |
| 9 | `test_commit_certificate_signers_correct` | `signers` frozenset == granted voters |
| 10 | `test_snapshot_reflects_state` | Propose + vote + commit; ConsensusSnapshot fields correct |
| 11 | `test_prometheus_metrics_incremented` | Isolated CollectorRegistry; all 5 metrics fired |
| 12 | `test_close_cancels_background_tasks` | `close()`; heartbeat + election tasks cancelled |

### Test isolation skeleton

```python
import pytest
from prometheus_client import CollectorRegistry

@pytest.fixture
def registry():
    return CollectorRegistry()

@pytest.fixture
def consensus(registry):
    gateway = MockFederationGateway()
    router  = MockFederatedTaskRouter()
    return InMemoryFederatedConsensus(
        peer_id="did:key:alice",
        gateway=gateway,
        router=router,
        _registry=registry,
    )
```

---

## mypy Strict Compatibility

| Symbol | `reveal_type(...)` output |
|--------|--------------------------|
| `ConsensusProposal.proposal_id` | `ProposalID` |
| `CommitCertificate.signers` | `FrozenSet[str]` |
| `CommitCertificate.threshold_sig` | `bytes` |
| `FederatedConsensus.propose` | `Coroutine[Any, Any, ProposalID]` |
| `ConsensusSnapshot.role` | `ConsensusRole` |
| `_PendingRound.granted_count()` | `int` |

---

## Implementation Order (14 steps)

1. Define `ConsensusRole` + `ConsensusState` enums
2. Define `ProposalID` frozen dataclass (term, seq, origin_peer)
3. Define `ConsensusProposal` + `ConsensusVote` frozen dataclasses
4. Define `CommitCertificate` frozen dataclass (`signers: FrozenSet[str]`)
5. Define `ConsensusSnapshot` mutable dataclass
6. Define `FederatedConsensus` Protocol (`@runtime_checkable`)
7. Implement `_aggregate_signatures()` SHA-256 stub
8. Implement `_PendingRound` internal tracker
9. Implement `InMemoryFederatedConsensus.__init__` (all queues + tasks)
10. Implement `_run_election()` + `_heartbeat_seen` asyncio.Event
11. Implement `_send_heartbeat()` loop
12. Implement `propose()` with ProposalID assignment + broadcast
13. Implement `vote()` + `_commit()` with quorum check + FIFO log eviction
14. Implement `commit_stream()` + `abort_stream()` + `snapshot()` + `close()`

---

## Phase 9 Roadmap

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 9.1 | FederationGateway | #299 | ✅ Spec complete |
| 9.2 | FederatedBlackboard | #302 | ✅ Spec complete |
| 9.3 | FederatedTaskRouter | #306 | ✅ Spec complete |
| 9.4 | FederatedConsensus | #310 | 🟡 Spec complete |
| 9.5 | FederationHealthMonitor | TBD | 📋 Planning (#314) |
