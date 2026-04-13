# Cognitive Blackboard

The `integration` module provides the **Cognitive Blackboard** — a shared workspace for cross-module communication in ASI:BUILD. It implements the classical Blackboard Architecture pattern (Erman et al., 1980) adapted for modern async Python.

---

## Overview

Modules don't call each other directly. Instead, they **post findings** to a central blackboard and **subscribe to events** when other modules post. This creates a loosely coupled architecture where:

- Any module can observe any other module's output
- Modules can be added or removed without changing others
- The full cognitive state is inspectable at any time

```python
from asi_build.integration import (
    CognitiveBlackboard,
    BlackboardEntry,
    EntryPriority,
    BlackboardQuery,
    EventBus,
    CognitiveEvent,
)
```

---

## Core Classes

### `BlackboardEntry`

The fundamental data unit. Every piece of information posted to the blackboard is wrapped in a `BlackboardEntry`:

```python
@dataclass
class BlackboardEntry:
    topic: str                           # e.g. "consciousness.phi", "reasoning.conclusion"
    data: Any                            # arbitrary payload
    source_module: str                   # who posted this
    entry_id: str                        # UUID (auto-generated)
    timestamp: float                     # UNIX epoch
    confidence: float = 1.0             # producer's confidence (0.0–1.0)
    priority: EntryPriority = NORMAL    # LOW / NORMAL / HIGH / CRITICAL
    status: EntryStatus = ACTIVE        # ACTIVE / CONSUMED / SUPERSEDED / EXPIRED
    ttl_seconds: Optional[float] = None # None = never expires
    tags: FrozenSet[str] = frozenset()
    parent_id: Optional[str] = None     # provenance chain
    metadata: Dict[str, Any] = {}
```

**Topic hierarchy** — topics are dotted strings. `get_by_topic("consciousness")` retrieves both `consciousness.phi` and `consciousness.broadcast` entries.

### `EntryPriority`

```python
class EntryPriority(IntEnum):
    LOW      = 0
    NORMAL   = 1
    HIGH     = 2
    CRITICAL = 3
```

Higher-priority entries are returned first by queries and are evicted last when the blackboard reaches capacity.

### `CognitiveBlackboard`

The main shared workspace:

```python
bb = CognitiveBlackboard(
    event_bus=None,         # Uses internal EventBus if not provided
    max_entries=10_000,     # Hard cap; oldest low-priority entries evicted
    auto_expire=True,       # Automatically expire entries past their TTL
)
```

---

## API Reference

### Posting Entries

```python
# Post a single entry
entry_id = bb.post(BlackboardEntry(
    topic="consciousness.phi",
    data={"phi": 3.14, "method": "IIT", "elements": 3},
    source_module="consciousness",
    priority=EntryPriority.HIGH,
    confidence=0.85,
    ttl_seconds=300.0,   # expires in 5 minutes
))

# Post multiple entries atomically
ids = bb.post_many([entry1, entry2, entry3])
```

### Querying Entries

```python
# Get all entries for a topic (including subtopics)
results = bb.get_by_topic("consciousness")

# Get a specific entry by ID
entry = bb.get(entry_id)

# Structured query with filters
from asi_build.integration import BlackboardQuery

q = BlackboardQuery(
    topics=["consciousness", "reasoning"],
    source_modules=["consciousness"],
    min_confidence=0.8,
    status_filter={EntryStatus.ACTIVE},
    limit=10,
)
results = bb.query(q)
```

### Updating and Removing

```python
# Update a field in an existing entry
bb.update_entry(entry_id, data={"phi": 4.2, "updated": True})

# Remove explicitly
bb.remove(entry_id, reason="superseded by newer measurement")

# Retract (mark as retracted, keep in log)
bb.retract(entry_id)

# Supersede: retract old, post new, link provenance
new_id = bb.supersede(old_entry_id, new_entry)
```

### Lifecycle Management

```python
# Manually expire TTL-exceeded entries
count = bb.sweep_expired()

# Get statistics
stats = bb.get_stats()
# Returns: {"total_entries", "active_entries", "total_posted",
#           "total_removed", "module_count", "topics"}

# List all known topics
topics = bb.get_topics()
```

### Module Registration

```python
from asi_build.integration import ModuleInfo, ModuleCapability

bb.register_module(
    ModuleInfo(
        name="my_module",
        version="1.0.0",
        capabilities=ModuleCapability.PRODUCER | ModuleCapability.CONSUMER,
        description="My custom module",
    ),
    instance=my_module_object,  # optional reference to the actual object
)
```

---

## EventBus

The blackboard includes an embedded `EventBus` at `bb.event_bus`. Use it for reactive patterns:

```python
# Subscribe to all consciousness events
def on_consciousness_event(event: CognitiveEvent):
    print(f"Consciousness event: {event.event_type}")
    print(f"Payload: {event.payload}")

bb.event_bus.subscribe("consciousness.*", on_consciousness_event)

# Subscribe to blackboard lifecycle events
def on_entry_added(event):
    print(f"New entry: {event.payload['topic']} from {event.payload['source_module']}")

bb.event_bus.subscribe("blackboard.entry.added", on_entry_added)

# Unsubscribe by subscription ID
sub_id = bb.event_bus.subscribe("reasoning.*", my_handler)
bb.event_bus.unsubscribe(sub_id)
```

**Pattern syntax**: uses `fnmatch` — `*` matches anything within a segment, but `"consciousness.*"` matches `"consciousness.phi"` and `"consciousness.broadcast"`.

**System events emitted by the blackboard:**

| Event | Payload keys |
|-------|-------------|
| `blackboard.entry.added` | `entry_id`, `topic`, `source_module`, `priority` |
| `blackboard.entry.updated` | `entry_id`, `topic`, `field`, `old`, `new` |
| `blackboard.entry.expired` | `entry_id`, `topic` |
| `blackboard.entry.removed` | `entry_id`, `topic`, `reason` |
| `blackboard.module.registered` | `module_name`, `capabilities` |
| `blackboard.module.unregistered` | `module_name` |
| `blackboard.sweep.complete` | `expired_count`, `active_count` |

---

## Module Adapters

Four adapters bridge ASI:BUILD modules to the blackboard:

### `ConsciousnessAdapter`

```python
from asi_build.integration.adapters import ConsciousnessAdapter

adapter = ConsciousnessAdapter(
    gwt=my_gwt_instance,       # GlobalWorkspaceTheory
    iit=my_iit_instance,       # IntegratedInformation
    base=my_base_instance,     # optional BaseConsciousness
)
# Produces: consciousness.phi, consciousness.broadcast, consciousness.metrics
```

### `KnowledgeGraphAdapter`

```python
from asi_build.integration.adapters import KnowledgeGraphAdapter

adapter = KnowledgeGraphAdapter(
    kg=my_temporal_kg,         # TemporalKnowledgeGraph
    pathfinder=my_pathfinder,  # optional KGPathfinder
)
# Produces: knowledge_graph.entity, knowledge_graph.path, knowledge_graph.updated
```

### `CognitiveSynergyAdapter`

```python
from asi_build.integration.adapters import CognitiveSynergyAdapter

adapter = CognitiveSynergyAdapter(
    engine=my_synergy_engine,  # CognitiveSynergyEngine
    metrics=my_metrics,        # optional SynergyMetrics
)
# Produces: synergy.measure, synergy.transfer_entropy, synergy.phi
```

### `ReasoningAdapter`

```python
from asi_build.integration.adapters import ReasoningAdapter

adapter = ReasoningAdapter(engine=my_reasoning_engine)
# Produces: reasoning.conclusion, reasoning.inference, reasoning.hypothesis
```

---

## wire_all() and production_sweep()

```python
from asi_build.integration import CognitiveBlackboard
from asi_build.integration.adapters import wire_all, production_sweep

bb = CognitiveBlackboard()

# Register all adapters and wire event subscriptions
wire_all(bb, cons_adapter, kg_adapter, syn_adapter, reas_adapter)

# Trigger an initial production pass — each adapter calls produce() once
production_sweep(bb, cons_adapter, kg_adapter, syn_adapter, reas_adapter)

# Now the blackboard has initial findings from all modules
print(f"Entries after sweep: {bb.active_entry_count}")
```

`wire_all()` calls `register_module()` on each adapter and sets up cross-wired event subscriptions (e.g., ReasoningAdapter subscribes to `consciousness.*`).

---

## Complete Example

```python
from asi_build.consciousness import GlobalWorkspaceTheory, IntegratedInformation
from asi_build.knowledge_graph import TemporalKnowledgeGraph
from asi_build.cognitive_synergy import CognitiveSynergyEngine
from asi_build.integration import CognitiveBlackboard, BlackboardEntry, EntryPriority, CognitiveEvent
from asi_build.integration.adapters import (
    ConsciousnessAdapter, KnowledgeGraphAdapter,
    CognitiveSynergyAdapter, wire_all
)

# 1. Instantiate modules
gwt = GlobalWorkspaceTheory()
iit = IntegratedInformation()
kg  = TemporalKnowledgeGraph()
syn = CognitiveSynergyEngine()

# 2. Create blackboard + adapters
bb   = CognitiveBlackboard()
cons = ConsciousnessAdapter(gwt=gwt, iit=iit)
kg_a = KnowledgeGraphAdapter(kg=kg)
syn_a = CognitiveSynergyAdapter(engine=syn)

# 3. Wire everything together
wire_all(bb, cons, kg_a, syn_a)

# 4. React to consciousness events
def on_phi(event: CognitiveEvent):
    if event.event_type == "blackboard.entry.added":
        print(f"New consciousness finding: {event.payload['topic']}")

bb.event_bus.subscribe("blackboard.entry.added", on_phi)

# 5. Post a finding
bb.post(BlackboardEntry(
    topic="consciousness.broadcast",
    data={"winner": "visual_cortex", "coalition_size": 4},
    source_module="consciousness",
    priority=EntryPriority.HIGH,
))

# 6. Query results
entries = bb.get_by_topic("consciousness")
for e in entries:
    print(f"  [{e.source_module}] {e.topic} = {e.data}")

print(f"Total active entries: {bb.active_entry_count}")
```

---

## Thread Safety

`CognitiveBlackboard` is fully **thread-safe** — all reads and writes are guarded by a reentrant lock (`threading.RLock`). The `EventBus` is similarly thread-safe.

For async (asyncio) workflows, use `emit_async()` on the event bus and the `AsyncBlackboardProducer` / `AsyncBlackboardConsumer` protocols.

---

## Related Pages

- [[Architecture]] — Where the blackboard fits in the overall design
- [[Module Index]] — All modules that can connect to the blackboard
- [[Getting Started]] — Quick start guide
