# OnlineLearningAdapter — Phase 5 Shared Infrastructure

The `OnlineLearningAdapter` ABC is the shared infrastructure foundation for all Phase 5 write-back paths. It lives in `integration/online_learning.py` and is the base class for every component that performs adaptive updates to ASI:BUILD's cognitive state.

## Rationale

All four Phase 5 milestones share a common pattern:

1. Read from the Cognitive Blackboard
2. Compute a proposed update (a `WeightDelta`)
3. Pass through a safety gate
4. Apply the update if approved

Rather than duplicating this logic in each milestone, Phase 5 extracts it into a single abstract base class. Every Phase 5 adapter subclasses `OnlineLearningAdapter`, gets a free `maybe_update()` convenience method, and benefits from a shared safety gate contract.

---

## Data Model

### `WeightDelta`

```python
@dataclass
class WeightDelta:
    source_module: str      # e.g. "bio_inspired", "federated_learning"
    parameter_path: str     # dotted path: "stdp.synaptic_weights"
    delta: Any              # numpy / torch tensor, numeric value, or metadata dict
    confidence: float       # [0.0, 1.0] — safety gate threshold
    metadata: dict = field(default_factory=dict)  # provenance info

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
```

`WeightDelta` is the universal unit of Phase 5 change. It is:
- **Auditable** — the Blockchain module can hash-chain `WeightDelta` records
- **Reversible** — the safety module can buffer and reject deltas before they're applied
- **Composable** — `MeshResultAggregator` can merge multiple agent deltas using `WEIGHTED` strategy

---

## `OnlineLearningAdapter` ABC

```python
class OnlineLearningAdapter(ABC):
    trigger_mode: Literal["tick", "event"] = "tick"
    event_topic: str | None = None

    @abstractmethod
    async def compute_update(
        self, blackboard_snapshot: dict
    ) -> WeightDelta | None: ...

    @abstractmethod
    async def apply_update(self, delta: WeightDelta) -> None: ...

    def safety_gate(self, delta: WeightDelta) -> bool:
        """Default: reject if confidence < 0.3. Override for domain constraints."""
        return delta.confidence >= 0.3

    async def maybe_update(
        self,
        blackboard_snapshot: dict,
        blackboard=None,
        tick_id: int | None = None,
    ) -> bool:
        """Compute → gate → apply. Returns True if update was applied."""
        delta = await self.compute_update(blackboard_snapshot)
        if delta is None:
            return False
        if not self.safety_gate(delta):
            if blackboard is not None:
                blackboard.write("online.rejected_deltas", {
                    "source": delta.source_module,
                    "parameter_path": delta.parameter_path,
                    "confidence": delta.confidence,
                    "tick_id": tick_id,
                    "reason": "below_confidence_threshold",
                }, ttl=10)
            return False
        await self.apply_update(delta)
        return True
```

---

## Trigger Modes

Phase 5 adapters declare their own activation mode via `trigger_mode`:

| Mode | When activated | Example adapters |
|------|---------------|-----------------|
| `"tick"` | Every `LEARNING` phase in `CognitiveCycle` | `STDPLearningAdapter`, `ConsciousnessPlanner` |
| `"event"` | On receipt of a specific `EventBus` topic | `FederatedHotReloadAdapter`, `MemoryConsolidatorAdapter` |

### Registration

```python
class CognitiveCycle:
    def register_online_adapter(self, adapter: OnlineLearningAdapter):
        if adapter.trigger_mode == "tick":
            self._tick_adapters.append(adapter)
        else:
            topic = adapter.event_topic
            self._event_adapters.setdefault(topic, []).append(adapter)
            self.blackboard.event_bus.subscribe(topic, adapter.maybe_update)
```

Tick adapters run in the `LEARNING` phase via `asyncio.gather()`.

---

## Phase 5 Adapter Map

| Adapter | Module | `trigger_mode` | `event_topic` | Phase |
|---------|--------|----------------|---------------|-------|
| `STDPLearningAdapter` | bio_inspired | `tick` | — | 5.1 |
| `FederatedHotReloadAdapter` | federated_learning | `event` | `federated.round_complete` | 5.1 |
| `KGTransactionalWriter` | knowledge_graph | `tick` | — | 5.1 |
| `StigmergyAdapter` | integration | `tick` | — | 5.2 |
| `CoalitionFormationAdapter` | integration | `event` | `stigmergy.coalition_request` | 5.2 |
| `MemoryConsolidatorAdapter` | bio_inspired | `event` | `bio.sleep_phase_start` | 5.3 |
| `GWTInferenceBridge` | consciousness | `tick` | — | 5.4 |
| `ConsciousnessPlanner` | integration | `tick` | — | 5.4 |

---

## Safety Gate Design

The default safety gate (`confidence >= 0.3`) is intentionally conservative. Subclasses are expected to override it with domain-specific constraints:

```python
class STDPLearningAdapter(OnlineLearningAdapter):
    def safety_gate(self, delta: WeightDelta) -> bool:
        # STDP: confidence must be high AND weight norm must be bounded
        if delta.confidence < 0.5:
            return False
        if hasattr(delta.delta, 'norm') and delta.delta.norm() > 10.0:
            return False  # reject runaway weight updates
        return True
```

### Rejection Audit Trail

Rejected deltas are written to `blackboard["online.rejected_deltas"]` (TTL=10 ticks). This key is:
- Consumed by `CycleFaultSummary` for the SSE health stream
- Logged by `BlockchainAuditAdapter` for the audit chain
- Visible in the Prometheus metric `asi_build_rejected_deltas_total`

---

## Blackboard Key Contracts

| Key | Writer | Reader | TTL |
|-----|--------|--------|-----|
| `online.rejected_deltas` | `OnlineLearningAdapter.maybe_update()` | `CycleFaultSummary`, Blockchain | 10 ticks |
| `online.weight_deltas` | All Phase 5 tick adapters | `MeshResultAggregator` | 5 ticks |
| `online.applied_count` | `maybe_update()` counter | Prometheus scraper | 1 tick |

---

## Testing

### Shared test fixture

```python
@pytest.fixture
def mock_blackboard():
    bb = MagicMock()
    bb.snapshot.return_value = {}
    bb.write.return_value = None
    return bb
```

### Acceptance criteria for PR A (OnlineLearningAdapter ABC)

1. `WeightDelta.__post_init__` raises `ValueError` for `confidence` outside `[0.0, 1.0]`
2. Instantiating `OnlineLearningAdapter` directly raises `TypeError` (abstract)
3. `maybe_update` returns `False` and writes to `online.rejected_deltas` when gate fails
4. `maybe_update` returns `True` and calls `apply_update` when gate passes
5. `register_online_adapter` routes tick vs. event adapters to correct pool

---

## Related Pages

- [Phase 5 Roadmap](Phase-5-Roadmap)
- [Phase 5 Integration Architecture](Phase-5-Integration)
- [Online Learning](Online-Learning) — Phase 5.1 detail
- [Emergent Coordination](Emergent-Coordination) — Phase 5.2
- [Persistent Memory](Persistent-Memory) — Phase 5.3
- [Consciousness-Guided Planning](Consciousness-Guided-Planning) — Phase 5.4
- [Multi-Agent Orchestration](Multi-Agent-Orchestration) — MeshCoordinator context
- [Health Monitoring](Health-Monitoring) — SSE stream for `rejected_deltas`

## Related Discussions

- [#205](https://github.com/web3guru888/asi-build/discussions/205) — Show & Tell: Phase 5 implementation architecture
- [#206](https://github.com/web3guru888/asi-build/discussions/206) — Ideas: trigger model (pull / push / hybrid)
- [#207](https://github.com/web3guru888/asi-build/discussions/207) — Q&A: safety gate rejection handling

## Related Issues

- [#204](https://github.com/web3guru888/asi-build/issues/204) — Phase 5 implementation sprint tracker
