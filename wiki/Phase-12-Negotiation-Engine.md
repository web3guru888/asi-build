# Phase 12.2 — NegotiationEngine: Task-Offer Negotiation Between Distributed Agents

**Phase**: 12.2 | **Component**: `NegotiationEngine` | **Issue**: [#355](https://github.com/web3guru888/asi-build/issues/355)

---

## Overview

`NegotiationEngine` provides a **bid-based task allocation protocol** for multi-agent collaboration. When `CognitiveCycle` needs to delegate a task to a remote peer, it:

1. **Announces** a `TaskOffer` to the network
2. Collects `Bid` objects during a configurable time window
3. Runs a `BidStrategy` to select the winner
4. Emits a `NegotiationResult` that `FederatedTaskRouter` uses to route the task

---

## 1. Enums

```python
class NegotiationStatus(Enum):
    """Lifecycle of a negotiation round."""
    OPEN        = auto()   # accepting bids
    EVALUATING  = auto()   # bid window closed, ranking in progress
    AWARDED     = auto()   # winner selected
    FAILED      = auto()   # no bids or strategy rejected all
    CANCELLED   = auto()   # originator cancelled before window closed

class BidOutcome(Enum):
    """Result for a single bid submission."""
    PENDING  = auto()
    WINNER   = auto()
    LOSER    = auto()
    INVALID  = auto()   # bid arrived after window / agent not AVAILABLE
```

### `NegotiationStatus` FSM

```
OPEN ──► EVALUATING ──► AWARDED
  │           │
  │           └──────► FAILED
  │
  └─────────────────► CANCELLED
```

---

## 2. Frozen Dataclasses

### `TaskOffer`

```python
@dataclass(frozen=True)
class TaskOffer:
    offer_id:    str           # uuid4
    task_type:   str           # capability tag ("planning", "vision", …)
    payload:     dict          # budget, deadline, priority 1-10
    window_secs: float = 5.0   # bid-acceptance window
    max_bids:    int   = 8     # hard cap; excess bids discarded
```

### `Bid`

```python
@dataclass(frozen=True)
class Bid:
    bid_id:    str
    offer_id:  str
    agent_id:  str        # must be AVAILABLE in AgentRegistry
    score:     float      # 0.0–1.0 confidence / cost estimate
    latency_ms: float     # estimated time to first result
    metadata:  dict = field(default_factory=dict)
```

### `NegotiationResult`

```python
@dataclass(frozen=True)
class NegotiationResult:
    offer_id:    str
    status:      NegotiationStatus
    winning_bid: Bid | None
    all_bids:    list[Bid]
    selected_at: datetime | None
```

### `NegotiationConfig`

```python
@dataclass(frozen=True)
class NegotiationConfig:
    default_window_secs: float = 5.0
    max_concurrent:      int   = 32
    history_ttl_secs:    float = 300.0
    min_score_threshold: float = 0.1   # bids below this → INVALID
```

---

## 3. Protocols

```python
class BidStrategy(Protocol):
    """Pluggable bid-ranking strategy."""
    def select(self, offer: TaskOffer, bids: list[Bid]) -> Bid | None: ...

class NegotiationEngine(Protocol):
    async def announce(self, offer: TaskOffer) -> str: ...
    async def submit_bid(self, bid: Bid) -> BidOutcome: ...
    async def get_result(self, offer_id: str) -> NegotiationResult | None: ...
    async def cancel(self, offer_id: str) -> bool: ...
    def active_offers(self) -> list[TaskOffer]: ...
    async def snapshot(self) -> dict: ...
```

---

## 4. `InMemoryNegotiationEngine`

### Internal State

```python
class InMemoryNegotiationEngine:
    _offers:   dict[str, TaskOffer]              # OPEN offers
    _bids:     dict[str, deque[Bid]]             # bids per offer
    _results:  dict[str, NegotiationResult]      # completed results
    _tasks:    dict[str, asyncio.Task[None]]     # window tasks
    _lock:     asyncio.Lock
    _registry: AgentRegistry
    _strategy: BidStrategy
    _cfg:      NegotiationConfig
```

### Key Methods

| Method | Complexity | Notes |
|---|---|---|
| `announce()` | O(1) | spawns `_window_task` |
| `submit_bid()` | O(1) | inserts into deque, validates AVAILABLE |
| `_evaluate()` | O(n log n) | called by `_window_task` on close |
| `get_result()` | O(1) | dict lookup |
| `cancel()` | O(1) | cancels asyncio.Task → CANCELLED |
| `_evict_task` | O(n) | sweeps by `selected_at + history_ttl_secs` |

### `_window_task` skeleton

```python
async def _window_task(self, offer: TaskOffer, event: asyncio.Event) -> None:
    try:
        await asyncio.wait_for(
            asyncio.shield(event.wait()),
            timeout=offer.window_secs,
        )
    except asyncio.TimeoutError:
        pass
    finally:
        await self._evaluate(offer.offer_id)
```

### `_evaluate()` skeleton

```python
async def _evaluate(self, offer_id: str) -> None:
    async with self._lock:
        offer = self._offers.pop(offer_id, None)
        if offer is None:
            return
        bids = list(self._bids.pop(offer_id, []))
        winner = self._strategy.select(offer, bids) if bids else None
        self._results[offer_id] = NegotiationResult(
            offer_id=offer_id,
            status=NegotiationStatus.AWARDED if winner else NegotiationStatus.FAILED,
            winning_bid=winner,
            all_bids=bids,
            selected_at=datetime.now(tz=timezone.utc),
        )
        NEG_ACTIVE.set(len(self._offers))
```

---

## 5. Built-in `BidStrategy` Implementations

```python
class HighestScoreStrategy:
    """Select bid with highest score; tie-break: lowest latency_ms."""
    def select(self, offer: TaskOffer, bids: list[Bid]) -> Bid | None:
        if not bids:
            return None
        return max(bids, key=lambda b: (b.score, -b.latency_ms))

class LowestLatencyStrategy:
    """Select bid with lowest latency_ms; tie-break: highest score."""
    def select(self, offer: TaskOffer, bids: list[Bid]) -> Bid | None:
        if not bids:
            return None
        return min(bids, key=lambda b: (b.latency_ms, -b.score))

class WeightedStrategy:
    """Configurable α·score + (1-α)·1/(1+latency_ms)."""
    def __init__(self, alpha: float = 0.7) -> None:
        self._alpha = alpha

    def select(self, offer: TaskOffer, bids: list[Bid]) -> Bid | None:
        if not bids:
            return None
        def _rank(b: Bid) -> float:
            return self._alpha * b.score + (1.0 - self._alpha) / (1.0 + b.latency_ms)
        return max(bids, key=_rank)
```

### Strategy Tuning Guide

| alpha | Behaviour |
|---|---|
| 1.0 | pure score = `HighestScoreStrategy` |
| 0.7 | **default** — balanced confidence + latency |
| 0.3 | latency-favoured |
| 0.0 | pure latency = `LowestLatencyStrategy` |

---

## 6. Factory

```python
def build_negotiation_engine(
    registry: AgentRegistry,
    strategy: BidStrategy | None = None,
    config:   NegotiationConfig | None = None,
) -> NegotiationEngine:
    """Returns InMemoryNegotiationEngine with WeightedStrategy(alpha=0.7) default."""
    return InMemoryNegotiationEngine(
        registry=registry,
        strategy=strategy or WeightedStrategy(),
        config=config or NegotiationConfig(),
    )
```

---

## 7. `CognitiveCycle` Integration

```python
# In CognitiveCycle._dispatch_to_peer():
async def _dispatch_to_peer(self, task: SubTask) -> None:
    offer = TaskOffer(
        offer_id=str(uuid.uuid4()),
        task_type=task.capability_tag,
        payload={"priority": task.priority, "deadline": task.deadline_iso},
        window_secs=self._negotiation_cfg.default_window_secs,
    )
    offer_id = await self._negotiation.announce(offer)
    await asyncio.sleep(offer.window_secs + 0.1)
    result = await self._negotiation.get_result(offer_id)
    if result and result.status == NegotiationStatus.AWARDED:
        await self._federation.route(result.winning_bid.agent_id, task)
    else:
        await self._replan(task, reason="no_bids")
```

---

## 8. Prometheus Metrics

```python
NEG_OFFERS  = Counter("negotiation_offers_total",       "Offers announced",    ["task_type"])
NEG_AWARDED = Counter("negotiation_awarded_total",      "Offers awarded",      ["task_type", "strategy"])
NEG_FAILED  = Counter("negotiation_failed_total",       "Offers failed",       ["task_type", "reason"])
NEG_WINDOW  = Histogram("negotiation_bid_window_seconds","Bid window duration", ["task_type"])
NEG_ACTIVE  = Gauge("negotiation_active_offers",        "Open offers")
```

**PromQL examples:**

```promql
# Award rate
rate(negotiation_awarded_total[5m]) / rate(negotiation_offers_total[5m])

# Median bid window duration
histogram_quantile(0.5, rate(negotiation_bid_window_seconds_bucket[10m]))

# Active offers gauge
negotiation_active_offers
```

---

## 9. mypy Checklist

| Symbol | Expected type |
|---|---|
| `_offers` | `dict[str, TaskOffer]` |
| `_bids` | `dict[str, deque[Bid]]` |
| `_results` | `dict[str, NegotiationResult]` |
| `_tasks` | `dict[str, asyncio.Task[None]]` |
| `submit_bid()` return | `BidOutcome` |
| `announce()` return | `str` (offer_id) |
| `get_result()` return | `NegotiationResult \| None` |

---

## 10. Test Targets (12)

| # | Test | What it checks |
|---|---|---|
| 1 | `test_announce_returns_offer_id` | UUID format, status OPEN |
| 2 | `test_submit_bid_pending_within_window` | returns PENDING |
| 3 | `test_submit_bid_invalid_offline_agent` | INVALID when agent not AVAILABLE |
| 4 | `test_window_close_evaluates_bids` | AWARDED after window expires |
| 5 | `test_highest_score_strategy_selects_winner` | correct bid selected |
| 6 | `test_lowest_latency_strategy_tiebreak` | lowest latency wins on tie |
| 7 | `test_weighted_strategy_alpha_1_is_highest_score` | degenerate case |
| 8 | `test_max_bids_cap_discards_excess` | 9th bid → INVALID when cap=8 |
| 9 | `test_cancel_open_negotiation` | status CANCELLED |
| 10 | `test_cancel_awarded_returns_false` | cannot cancel finished round |
| 11 | `test_ttl_eviction_removes_results` | `get_result()` → None after TTL |
| 12 | `test_no_bids_yields_failed_status` | FAILED when window closes empty |

---

## 11. Implementation Order (14 steps)

1. Enums `NegotiationStatus`, `BidOutcome`
2. Frozen dataclasses `TaskOffer`, `Bid`, `NegotiationResult`, `NegotiationConfig`
3. `BidStrategy` Protocol
4. `NegotiationEngine` Protocol
5. `HighestScoreStrategy`
6. `LowestLatencyStrategy`
7. `WeightedStrategy`
8. `InMemoryNegotiationEngine.__init__` (dicts + locks + task handles)
9. `announce()` + `_window_task` coroutine
10. `submit_bid()` + AVAILABLE guard
11. `_evaluate()` → strategy select → mark WINNER/LOSER
12. `cancel()` — cancel asyncio.Task + set CANCELLED
13. `_evict_task` — TTL sweep loop
14. `build_negotiation_engine()` factory + Prometheus pre-init

---

## 12. Phase 12 Roadmap

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 12.1 | `AgentRegistry` | [#352](https://github.com/web3guru888/asi-build/issues/352) | ✅ spec'd |
| 12.2 | `NegotiationEngine` | [#355](https://github.com/web3guru888/asi-build/issues/355) | 🟡 this issue |
| 12.3 | `CollaborationChannel` | planned | 📋 |
| 12.4 | `ConsensusVoting` | planned | 📋 |
| 12.5 | `CoalitionFormation` | planned | 📋 |
