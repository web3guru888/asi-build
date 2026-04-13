# Integration Layer

The `integration` package is the central nervous system of ASI:BUILD — the glue that makes 29 independent modules work as a coherent, coordinated framework. It provides a type-safe, thread-safe, async-compatible **Cognitive Blackboard** plus an **EventBus** with wildcard routing, all backed by explicit module protocols.

---

## Package Overview

```
src/asi_build/integration/
├── __init__.py          # 108 LOC — public API surface
├── blackboard.py        # 558 LOC — CognitiveBlackboard implementation
├── events.py            # 385 LOC — EventBus with wildcard routing
├── protocols.py         # 364 LOC — type-safe interfaces and data containers
└── adapters/
    ├── consciousness_adapter.py       # IIT Φ, GWT, AST → consciousness.state
    ├── reasoning_adapter.py           # HybridReasoningEngine → reasoning.result
    ├── bio_inspired_adapter.py        # CognitiveState → bio_inspired.state
    ├── cognitive_synergy_adapter.py   # Synergy events → cognitive_synergy.pattern
    ├── knowledge_graph_adapter.py     # KG writes → knowledge_graph.entry
    ├── knowledge_management_adapter.py # KnowledgeEngine → knowledge_management.insight
    ├── graph_intelligence_adapter.py  # FastToG → graph_intelligence.subgraph
    └── rings_adapter.py               # P2P DID events → rings.peer_event
```

**Total: 1,415 LOC** for the core integration layer. 8 of 29 modules are wired; 21 more are tracked in open issues.

---

## protocols.py — The Type System

`protocols.py` defines the contracts every Blackboard participant must fulfill. Everything is explicitly typed using `runtime_checkable` Protocol classes — no duck typing.

### ModuleCapability Flags

```python
class ModuleCapability(enum.Flag):
    PRODUCER    = enum.auto()  # Can write new entries to the blackboard
    CONSUMER    = enum.auto()  # Reads entries from the blackboard
    TRANSFORMER = enum.auto()  # Reads, transforms, and writes back
    REASONER    = enum.auto()  # Can perform reasoning over entries
    VALIDATOR   = enum.auto()  # Can validate / score entries
    LEARNER     = enum.auto()  # Adapts based on blackboard history
```

Flags are combinable with `|`:
```python
blackboard.register_module(
    "consciousness",
    ModuleCapability.PRODUCER | ModuleCapability.REASONER
)
```

### EntryStatus Lifecycle

```
ACTIVE → CONSUMED    (entry was read by a subscriber)
ACTIVE → SUPERSEDED  (newer entry on same topic arrived)
ACTIVE → EXPIRED     (TTL elapsed — swept by GC)
ACTIVE → RETRACTED   (explicit removal by source module)
```

The Blackboard never hard-deletes entries — it transitions their `status`. Expired and retracted entries remain in the log for audit, debugging, and future replay.

### EntryPriority

```python
class EntryPriority(enum.IntEnum):
    LOW      = 0
    NORMAL   = 1
    HIGH     = 2
    CRITICAL = 3
```

Entries with `confidence < 0.5` are automatically downgraded to `LOW` priority at write time.

### BlackboardEntry Dataclass

Every write is wrapped in a `BlackboardEntry`:

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | `str` | UUID generated at write time |
| `topic` | `str` | Dot-notation namespace, e.g. `consciousness.state` |
| `data` | `Any` | Module output payload |
| `source_module` | `str` | Who wrote this entry |
| `confidence` | `float` | 0.0–1.0 — entries < 0.5 auto-downgraded |
| `priority` | `EntryPriority` | Delivery urgency |
| `ttl` | `float` | Seconds until expiry (0 = never expires) |
| `timestamp` | `float` | `time.monotonic()` at write |
| `status` | `EntryStatus` | Current lifecycle state |

---

## events.py — The EventBus

The `EventBus` provides lightweight pub/sub with **dot-notation wildcard routing**:

```python
bus.subscribe("blackboard.*", audit_logger)           # all lifecycle events
bus.subscribe("blackboard.entry.added", handler)      # specific event type
bus.subscribe("module.consciousness.*", listener)     # all consciousness events
bus.subscribe("*", global_observer)                   # everything
```

### Built-in Lifecycle Events

| Event | Payload |
|-------|---------|
| `blackboard.entry.added` | `{entry_id, topic, source_module}` |
| `blackboard.entry.updated` | `{entry_id, topic, field, old, new}` |
| `blackboard.entry.expired` | `{entry_id, topic}` |
| `blackboard.entry.removed` | `{entry_id, topic, reason}` |
| `blackboard.module.registered` | `{module_name, capabilities}` |
| `blackboard.module.unregistered` | `{module_name}` |
| `blackboard.sweep.complete` | `{expired_count, active_count}` |

### Performance Benchmarks

| Metric | Value |
|--------|-------|
| Publish throughput | 20,000 events/sec (single-threaded) |
| Subscriber notification lag | < 1ms (up to 50 concurrent subscribers) |
| Wildcard routing overhead | < 5µs per pattern match |

---

## blackboard.py — CognitiveBlackboard

`CognitiveBlackboard` is the central shared workspace. It wraps a topic-partitioned entry store, embeds the `EventBus`, and manages a module registry.

### Core API

```python
from asi_build.integration.blackboard import CognitiveBlackboard
from asi_build.integration.protocols import ModuleCapability, EntryPriority

bb = CognitiveBlackboard()

# Register a module
bb.register_module("mymodule", ModuleCapability.PRODUCER | ModuleCapability.CONSUMER)

# Write an entry
bb.post(
    topic="mymodule.result",
    data={"answer": 42},
    source_module="mymodule",
    confidence=0.9,
    priority=EntryPriority.NORMAL,
    ttl=30.0,          # seconds; 0 = no expiry
)

# Read active entries on a topic
entries = bb.read("mymodule.result", active_only=True)

# Subscribe to a topic (sync callback)
def on_entry(entry):
    print(f"New entry from {entry.source_module}: {entry.data}")

bb.subscribe("mymodule.result", on_entry)

# Shutdown (stops GC sweep thread)
bb.shutdown()
```

### Thread Safety

All reads and writes are protected by a `threading.RLock`. The sweep GC runs in a background daemon thread and transitions expired entries to `EXPIRED` status. It does not delete — audit logs remain intact.

---

## The 8 Wired Adapters

Each adapter follows the same pattern:

1. Instantiate with a `CognitiveBlackboard` reference
2. Call `blackboard.register_module(...)` with capability flags
3. Subscribe to relevant topics from other modules
4. Provide a `post_*()` method that wraps module output as a `BlackboardEntry`

### Adapter Topic Map

| Adapter | Writes topic | Reads from | Typical confidence |
|---------|-------------|------------|-------------------|
| `consciousness_adapter` | `consciousness.state` | `reasoning.result` | 0.88 |
| `reasoning_adapter` | `reasoning.result` | `consciousness.state` | 0.90 |
| `bio_inspired_adapter` | `bio_inspired.state` | `consciousness.state` | 0.85 |
| `cognitive_synergy_adapter` | `cognitive_synergy.pattern` | `bio_inspired.state` | 0.87 |
| `knowledge_graph_adapter` | `knowledge_graph.entry` | `reasoning.result` | 0.92 |
| `knowledge_management_adapter` | `knowledge_management.insight` | `knowledge_graph.entry` | 0.90 |
| `graph_intelligence_adapter` | `graph_intelligence.subgraph` | `knowledge_graph.entry` | 0.88 |
| `rings_adapter` | `rings.peer_event` | `reasoning.result` | 0.85 |

### Writing a New Adapter

A new adapter is typically **150–200 lines**. Follow the pattern from `consciousness_adapter.py`:

```python
class MyModuleBlackboardAdapter:
    TOPIC = "my_module.result"

    def __init__(self, blackboard: CognitiveBlackboard):
        self.blackboard = blackboard
        self.blackboard.register_module(
            "my_module",
            ModuleCapability.PRODUCER | ModuleCapability.CONSUMER,
        )
        self.blackboard.subscribe("reasoning.result", self._on_reasoning_result)

    def post_result(self, result: dict, confidence: float = 0.9):
        self.blackboard.post(
            topic=self.TOPIC,
            data=result,
            source_module="my_module",
            confidence=confidence,
            priority=EntryPriority.NORMAL,
            ttl=60.0,
        )

    def _on_reasoning_result(self, entry):
        # React to reasoning module output
        pass
```

---

## Open Adapter Issues

21 more adapters are tracked in open issues — each with a full design sketch in the comments:

| Module | Issue | Difficulty |
|--------|-------|------------|
| quantum | [#53](https://github.com/web3guru888/asi-build/issues/53) | Medium |
| holographic | [#56](https://github.com/web3guru888/asi-build/issues/56) | Medium |
| federated | [#58](https://github.com/web3guru888/asi-build/issues/58) | Medium |
| homomorphic | [#60](https://github.com/web3guru888/asi-build/issues/60) | Medium-Hard |
| agi_economics | [#63](https://github.com/web3guru888/asi-build/issues/63) | Easy-Medium |
| bci | [#65](https://github.com/web3guru888/asi-build/issues/65) | Medium |
| blockchain | [#96](https://github.com/web3guru888/asi-build/issues/96) | Medium |
| servers (Kenny Graph SSE) | [#89](https://github.com/web3guru888/asi-build/issues/89) | Medium |
| integrations (LangChain/MCP) | [#90](https://github.com/web3guru888/asi-build/issues/90) | Medium |

All are labeled `good first issue` — great entry point for new contributors.

---

## Integration Tests

End-to-end pipeline tests are tracked in [#99](https://github.com/web3guru888/asi-build/issues/99). Key invariants to test:

- **Delivery**: Entry posted by adapter A arrives at subscriber in adapter B
- **TTL expiry**: Short-TTL entry is gone after expiry period
- **Wildcard routing**: `consciousness.*` subscriber gets all consciousness events
- **Thread safety**: 50 concurrent posts from 5 modules don't corrupt state
- **Priority ordering**: HIGH entries delivered before NORMAL/LOW under load

See the design sketch in [#99](https://github.com/web3guru888/asi-build/issues/99) for a full test scaffold.

---

## Related Pages

- [Cognitive Blackboard](Cognitive-Blackboard) — architecture overview
- [Blackboard Integration Status](Blackboard-Integration-Status) — adapter completion tracker
- [Testing Strategy](Testing-Strategy) — how we test integration
- [Architecture](Architecture) — layered design overview
