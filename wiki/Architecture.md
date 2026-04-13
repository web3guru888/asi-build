# Architecture

ASI:BUILD is organized as a **layered cognitive architecture** — inspired by Dr. Ben Goertzel's cognitive synergy hypothesis that intelligence emerges from the interaction of diverse cognitive subsystems.

---

## Layered Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        Reasoning Layer                          │
│   reasoning ──── graph_intelligence ──── pln_accelerator       │
│   (hybrid symbolic-neural, FastToG pipeline, PLN inference)     │
└──────────────────────────┬──────────────────────────────────────┘
                           │  Cognitive Blackboard
┌──────────────────────────▼──────────────────────────────────────┐
│                       Knowledge Layer                           │
│   knowledge_graph ──── graph_intelligence ──── knowledge_mgmt  │
│   (bi-temporal KG, A* pathfinding, pheromone learning)         │
└──────────────────────────┬──────────────────────────────────────┘
                           │  Cognitive Blackboard
┌──────────────────────────▼──────────────────────────────────────┐
│                    Consciousness Layer                          │
│   GWT ── IIT (Φ) ── AST ── metacognition ── predictive proc   │
│   cognitive_synergy: mutual info, transfer entropy, LZ         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Support Modules                            │
│  homomorphic · quantum · safety · compute · bio_inspired        │
│  bci · optimization · vectordb · neuromorphic · federated       │
│  deployment · blockchain · distributed_training · holographic   │
└─────────────────────────────────────────────────────────────────┘
```

Each layer communicates upward and downward through the **Cognitive Blackboard** — a shared workspace where modules post findings and subscribe to events from other modules.

---

## Cognitive Blackboard Pattern

The Cognitive Blackboard is a classical AI architecture pattern (Erman et al., 1980; Hayes-Roth, 1985) adapted for modern async Python. It acts as a **neutral shared workspace** — no module directly calls another. Instead:

1. Module A **posts** a `BlackboardEntry` (e.g., `consciousness.phi` with `phi=3.14`)
2. The `EventBus` fires `blackboard.entry.added` to all subscribers
3. Module B, subscribed to `"consciousness.*"`, wakes up and acts on the new data
4. Module B posts its own findings (e.g., `reasoning.conclusion`)

This decouples modules: they only depend on the blackboard protocol, not on each other's APIs.

```
┌──────────┐    post()    ┌───────────────────────┐   events   ┌──────────┐
│ Module A │ ────────────►│  CognitiveBlackboard   │──────────►│ Module B │
│          │◄────────────│                         │◄──────────│          │
└──────────┘   query()   │   ┌─────────────────┐  │ subscribe()└──────────┘
                          │   │    EventBus     │  │
                          │   │ entry.added     │  │
                          │   │ entry.updated   │  │
                          │   │ entry.expired   │  │
                          │   └─────────────────┘  │
                          └───────────────────────┘
```

See [[Cognitive Blackboard]] for the full API reference.

---

## EventBus: Pub/Sub Model

The `EventBus` embedded in the blackboard provides **topic-based routing** with fnmatch wildcards:

```python
# Subscribe to all consciousness events
bus.subscribe("consciousness.*", my_handler)

# Subscribe to a specific event
bus.subscribe("reasoning.conclusion", handle_conclusion)

# Catch-all
bus.subscribe("*", log_everything)
```

Events are `CognitiveEvent` objects with:
- `event_type` — dotted topic string (e.g., `"blackboard.entry.added"`)
- `payload` — arbitrary dict
- `source_module` — which module emitted it
- `timestamp` — float (UTC)

**System events emitted by the blackboard:**

| Event | Trigger |
|-------|---------|
| `blackboard.entry.added` | `post()` called |
| `blackboard.entry.updated` | `update_entry()` called |
| `blackboard.entry.expired` | TTL elapsed, swept by `sweep_expired()` |
| `blackboard.module.registered` | `register_module()` called |
| `blackboard.sweep.complete` | Periodic sweep finished |

---

## Module Adapter Pattern

Direct module integration uses **adapters** that implement the `BlackboardProducer` / `BlackboardConsumer` protocols:

```
Module Instance               Adapter                 Blackboard
─────────────────────────────────────────────────────────────────
ConsciousnessEngine  ──────►  ConsciousnessAdapter ──►  post()
                              │  implements:              │
                              │  - produce()              │
                              │  - handle_event()         │
                              │  - module_info()          │
                              ◄─────────────────────────subscribe()
```

The four available adapters are:

| Adapter | Module Wrapped | Produces |
|---------|---------------|----------|
| `ConsciousnessAdapter` | GWT, IIT, BaseConsciousness | `consciousness.phi`, `consciousness.broadcast` |
| `KnowledgeGraphAdapter` | TemporalKG, KGPathfinder | `knowledge_graph.entity`, `knowledge_graph.path` |
| `CognitiveSynergyAdapter` | CognitiveSynergyEngine, SynergyMetrics | `synergy.measure`, `synergy.transfer_entropy` |
| `ReasoningAdapter` | HybridReasoningEngine | `reasoning.conclusion`, `reasoning.inference` |

---

## Data Flow: Cross-Module Communication

Here's an example data flow through a full cognitive cycle:

```
1. External stimulus arrives
   └─► ConsciousnessAdapter.produce()
       └─► GWT.broadcast(stimulus)
           └─► bb.post(BlackboardEntry(topic="consciousness.broadcast", ...))
               └─► EventBus fires "blackboard.entry.added"

2. ReasoningAdapter receives event (subscribed to "consciousness.*")
   └─► HybridReasoningEngine.infer(broadcast_data)
       └─► bb.post(BlackboardEntry(topic="reasoning.conclusion", ...))

3. KnowledgeGraphAdapter receives reasoning conclusion
   └─► TemporalKG.add_relationship(entities_from_conclusion)
       └─► bb.post(BlackboardEntry(topic="knowledge_graph.updated", ...))

4. CognitiveSynergyAdapter measures integration across entries
   └─► SynergyEngine.compute_synergy(consciousness_entries, reasoning_entries)
       └─► bb.post(BlackboardEntry(topic="synergy.measure", ...))
```

---

## Integration Layer: wire_all()

The `wire_all()` utility registers all adapters with the blackboard in one call:

```python
from asi_build.integration import CognitiveBlackboard
from asi_build.integration.adapters import wire_all, ConsciousnessAdapter, ReasoningAdapter

bb = CognitiveBlackboard()
cons = ConsciousnessAdapter(gwt=my_gwt)
reas = ReasoningAdapter(engine=my_reasoning)

wire_all(bb, cons, reas)  # register + subscribe all cross-wired events
```

After `wire_all()`, call `production_sweep(bb, *adapters)` to trigger an initial production pass (each adapter calls `produce()` once to populate the blackboard).

---

## Module Maturity Model

```
🟢 Implemented — Core algorithms present, tested, API stable
🟡 Structural  — Interfaces defined; backends or implementations pending
```

For per-module status, see [[Module Index]].

---

## Related Pages

- [[Cognitive Blackboard]] — Full API reference
- [[Module Index]] — All 28 modules with status
- [[Roadmap]] — What's coming next
