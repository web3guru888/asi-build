# Integration Layer

> **Maturity**: `beta` · **Adapter**: `N/A` (IS the integration layer)

The central integration layer providing the Cognitive Blackboard, EventBus, and CognitiveCycle — the shared workspace that enables cross-module communication across all 29 ASI:BUILD modules. The Cognitive Blackboard is a thread-safe, priority-aware data store where modules publish findings and consume others' outputs. The EventBus provides pub/sub messaging with wildcard topic matching. The CognitiveCycle orchestrates a real-time perception→cognition→action tick loop that drives the system.

Defines Protocol-based interfaces (BlackboardProducer, BlackboardConsumer, BlackboardTransformer) that all 24 adapters implement, with both sync and async variants.

## Key Classes

| Class | Description |
|-------|-------------|
| `CognitiveBlackboard` | Shared workspace with CRUD, TTL, priority eviction, supersession chains |
| `CognitiveCycle` | Real-time perception→cognition→action tick loop orchestration |
| `CyclePhase` | Enum for cycle phases (PERCEIVE, COGNIZE, ACT) |
| `CycleState` | Enum for cycle states (IDLE, RUNNING, PAUSED, STOPPED) |
| `CycleMetrics` | Per-tick performance metrics |
| `TickResult` | Result of a single tick execution |
| `AdapterRole` | Enum for adapter roles (GENERAL, SAFETY, PERCEPTION, ACTION) |
| `EventBus` | Pub/sub messaging with wildcard topic matching |
| `CognitiveEvent` | Typed event payload |
| `Subscription` | Event subscription handle |
| `DeadLetter` | Undeliverable event record |
| `BlackboardEntry` | Data entry in the blackboard |
| `BlackboardQuery` | Query specification for blackboard search |
| `EntryPriority` | Priority levels (LOW, NORMAL, HIGH, CRITICAL) |
| `EntryStatus` | Entry lifecycle status |
| `BlackboardProducer` | Sync protocol for modules that publish data |
| `BlackboardConsumer` | Sync protocol for modules that consume data |
| `BlackboardTransformer` | Sync protocol for modules that transform data |
| `AsyncBlackboardProducer` | Async protocol for modules that publish data |
| `AsyncBlackboardConsumer` | Async protocol for modules that consume data |
| `AsyncBlackboardTransformer` | Async protocol for modules that transform data |
| `EventEmitter` | Sync protocol for event emission |
| `EventListener` | Sync protocol for event listening |
| `AsyncEventListener` | Async protocol for event listening |
| `EventHandler` | Event handler callable protocol |
| `ModuleInfo` | Module registration metadata |
| `ModuleCapability` | Module capability flags |

## Example Usage

```python
from asi_build.integration import CognitiveBlackboard, EventBus, BlackboardEntry, EntryPriority
bb = CognitiveBlackboard()
bus = EventBus()
bb.register_module("reasoning", capabilities=["produce", "consume"])
entry = BlackboardEntry(topic="reasoning.inference", source="reasoning",
                        data={"conclusion": "X causes Y"}, priority=EntryPriority.HIGH)
bb.post(entry)
results = bb.query(topic="reasoning.*")
```

## Blackboard Integration

This IS the integration layer — all 24 blackboard adapters implement its protocols. Not an adapter itself.
