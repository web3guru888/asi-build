#!/usr/bin/env python3
"""
Cognitive Blackboard — Cross-Module Communication Demo
=======================================================

Demonstrates all four module adapters communicating through the shared
CognitiveBlackboard, the central integration layer of ASI:BUILD.

Data flow:
  1. Consciousness computes Φ (integrated information) and posts it
  2. Reasoning queries the blackboard for context, produces an inference
  3. Knowledge Graph stores the inference as a triple
  4. Cognitive Synergy measures the cross-module interaction

Run:
    cd /path/to/asi-build
    python3 examples/blackboard_demo.py

Requires: numpy, scipy, networkx  (all in project deps)

Addresses: Issue #14 — End-to-end integration demo
"""

import sys
import time

# ── 0. Setup ─────────────────────────────────────────────────────────

print("=" * 70)
print("  ASI:BUILD — Cognitive Blackboard Cross-Module Demo")
print("  Four modules, one shared workspace, real data flow")
print("=" * 70)

# ── 1. Create module instances ───────────────────────────────────────

print("\n📦 Step 1: Instantiating modules...\n")

# Consciousness — IIT (Integrated Information Theory)
# We build a small 3-element network with bidirectional connections
# so that Φ is computable quickly and yields a non-trivial value.
from asi_build.consciousness.integrated_information import (
    IntegratedInformationTheory,
    SystemElement,
    Connection,
)

iit = IntegratedInformationTheory(config={
    "phi_threshold": 0.05,
    "max_partition_size": 3,   # Keep it small for fast exact Φ
})

# Clear the default large network — we want a controlled 3-element system
iit.elements.clear()
iit.connections.clear()
iit.system_graph.clear()

# Build a 3-element bidirectionally connected network
for name in ["alpha", "beta", "gamma"]:
    iit.add_element(SystemElement(
        element_id=name, state=0.0, activation_function="sigmoid",
    ))

# Bidirectional connections with varying weights
for src, dst, w in [
    ("alpha", "beta",  0.8),
    ("beta",  "alpha", 0.6),
    ("beta",  "gamma", 0.9),
    ("gamma", "beta",  0.7),
    ("alpha", "gamma", 0.5),
    ("gamma", "alpha", 0.4),
]:
    iit.add_connection(Connection(from_element=src, to_element=dst, weight=w))

print(f"  ✓ IIT engine: {len(iit.elements)} elements, "
      f"{len(iit.connections)} connections (custom bidirectional network)")

# Knowledge Graph — Temporal KG (in-memory SQLite)
from asi_build.knowledge_graph.temporal_kg import TemporalKnowledgeGraph

kg = TemporalKnowledgeGraph(db_path=":memory:")
print(f"  ✓ Temporal KG: in-memory SQLite (empty)")

# Reasoning — Hybrid Reasoning Engine
from asi_build.reasoning.hybrid_reasoning import HybridReasoningEngine

reasoning = HybridReasoningEngine()
print(f"  ✓ Hybrid Reasoning: 6 modes, adaptive weights")

# Cognitive Synergy — Metrics engine
from asi_build.cognitive_synergy.core.synergy_metrics import SynergyMetrics

metrics = SynergyMetrics(history_length=500, sampling_rate=10.0)
print(f"  ✓ Synergy Metrics: MI, TE, PLV, coherence, emergence")

# ── 2. Create the Cognitive Blackboard ───────────────────────────────

print("\n📋 Step 2: Creating Cognitive Blackboard...\n")

from asi_build.integration import CognitiveBlackboard

bb = CognitiveBlackboard()
print(f"  ✓ Blackboard created (max_entries={bb._max_entries}, "
      f"auto_expire={bb._auto_expire})")

# ── 3. Create adapters and wire them ────────────────────────────────

print("\n🔌 Step 3: Wiring adapters to blackboard...\n")

from asi_build.integration.adapters import (
    ConsciousnessAdapter,
    KnowledgeGraphAdapter,
    CognitiveSynergyAdapter,
    ReasoningAdapter,
    wire_all,
    production_sweep,
)

cons_adapter = ConsciousnessAdapter(iit=iit)
kg_adapter = KnowledgeGraphAdapter(kg=kg)
reas_adapter = ReasoningAdapter(engine=reasoning)
syn_adapter = CognitiveSynergyAdapter(metrics=metrics)

wire_all(bb, cons_adapter, kg_adapter, reas_adapter, syn_adapter)

for mod in bb.list_modules():
    print(f"  ✓ {mod.name:20s} — produces: {sorted(mod.topics_produced)}")

# ── 4. Set up IIT network and stimulate it ──────────────────────────

print("\n🧠 Step 4: Stimulating the neural network...\n")

# Feed external input to drive the 3-element system into a non-trivial state.
stimuli = {"alpha": 0.9, "beta": 0.6, "gamma": 0.3}
print(f"  Injecting stimuli: {stimuli}")

# Run a few update cycles so activation propagates through connections
for step in range(5):
    if step == 0:
        iit.update_system_state(external_inputs=stimuli)
    else:
        iit.update_system_state()

# Show element states after propagation
states = {eid: round(e.state, 4) for eid, e in iit.elements.items()}
print(f"  After 5 update steps: {states}")

# ── 5. Production Sweep #1 — Consciousness ──────────────────────────

print("\n🔄 Step 5: Production sweep #1 — Consciousness computes Φ...\n")

sweep1_ids = production_sweep(bb, cons_adapter)
print(f"  Posted {len(sweep1_ids)} entries to blackboard")

phi_entries = bb.get_by_topic("consciousness.phi")
if phi_entries:
    phi_val = phi_entries[0].data.get("phi", 0)
    complexes = phi_entries[0].data.get("complexes_count", "?")
    print(f"  ✦ Φ = {phi_val:.4f}  (complexes found: {complexes})")
    print(f"    Confidence: {phi_entries[0].confidence:.2f}, "
          f"Priority: {phi_entries[0].priority.name}")
else:
    print("  (No Φ entry — IIT may need more state history)")

state_entries = bb.get_by_topic("consciousness.state")
if state_entries:
    state = state_entries[0].data
    print(f"  ✦ State snapshot: {state.get('num_elements')} elements, "
          f"Φ={state.get('current_phi', 0):.4f}, "
          f"{state.get('num_complexes', 0)} complexes")

# ── 6. Reasoning with blackboard context ────────────────────────────

print("\n🤔 Step 6: Reasoning engine queries blackboard context...\n")

# The HybridReasoningEngine.reason() is async, so we need asyncio.
import asyncio

async def _run_reasoning():
    return await reasoning.reason(
        query="Given the current consciousness state, what cognitive processes "
              "are most active and what does this imply about system integration?",
        context={"phi_value": phi_entries[0].data.get("phi", 0) if phi_entries else 0},
    )

raw_result = asyncio.run(_run_reasoning())

# The adapter expects to call engine.reason() — since it's async it returns
# a coroutine.  We post the real result manually for this demo.
result = reas_adapter._result_to_dict(raw_result)
reas_adapter._pending_results.append(result)
reas_adapter._inference_count += 1

# Also emit the event the adapter would normally emit
from asi_build.integration.protocols import CognitiveEvent
reas_adapter._emit("reasoning.inference.completed", {
    "query": "consciousness integration analysis",
    "conclusion": result.get("conclusion", ""),
    "confidence": result.get("confidence", 0),
    "mode": result.get("reasoning_mode", ""),
})

if result:
    conclusion = str(result.get("conclusion", "N/A"))
    print(f"  ✦ Conclusion: {conclusion[:120]}{'...' if len(conclusion)>120 else ''}")
    print(f"    Mode: {result.get('reasoning_mode', 'hybrid')}, "
          f"Confidence: {result.get('confidence', 0):.2f}")
    steps = result.get("reasoning_steps", [])
    if steps:
        print(f"    Steps: {len(steps)} reasoning steps executed")
        for i, s in enumerate(steps[:3]):
            mode = s.get("reasoning_type", s.get("mode", "?"))
            conf = s.get("confidence", 0)
            print(f"      [{i+1}] {mode} (conf={conf:.2f})")
else:
    print("  (Reasoning returned no result)")

# Flush reasoning results to blackboard
sweep2_ids = production_sweep(bb, reas_adapter)
print(f"\n  → Posted {len(sweep2_ids)} reasoning entries to blackboard")

# ── 7. KG ingests the inference ─────────────────────────────────────

print("\n📊 Step 7: Knowledge Graph ingests the inference...\n")

# The KG adapter auto-ingests reasoning entries.  But let's also
# explicitly add a triple to demonstrate the public API.
triple_id = kg_adapter.add_triple(
    subject="consciousness_system",
    predicate="exhibits_integration_level",
    obj=f"phi={phi_entries[0].data.get('phi', 0):.4f}" if phi_entries else "phi=unknown",
    source="blackboard_demo",
    confidence=0.95,
    statement_type="observation",
)
print(f"  ✦ Added triple: {triple_id}")

# Add a causal relationship
triple_id2 = kg_adapter.add_triple(
    subject="sensory_stimulation",
    predicate="causes",
    obj="increased_integration",
    source="blackboard_demo",
    confidence=0.85,
    statement_type="inference",
)
print(f"  ✦ Added triple: {triple_id2}")

# Flush KG entries to blackboard
sweep3_ids = production_sweep(bb, kg_adapter)
print(f"\n  → Posted {len(sweep3_ids)} KG entries to blackboard")

# Show KG statistics
stats = kg.get_statistics()
print(f"  ✦ KG now has {stats['total_triples']} triples "
      f"({stats['active_triples']} active), "
      f"{stats['unique_entities']} entities, "
      f"{stats['unique_predicates']} predicates")
print(f"    Statement types: {stats['statement_types']}")

# ── 8. Feed synergy data and measure cross-module interaction ───────

print("\n🌊 Step 8: Synergy measures cross-module interaction...\n")

# Simulate time-series data from each module into synergy metrics.
# In production, the adapters do this automatically via consume().
# Here we seed enough data points for the metrics to be computable.
import numpy as np

np.random.seed(42)
t_base = time.time()

for i in range(120):
    t = t_base + i * 0.1  # 10 Hz sampling
    # Consciousness signal: Φ oscillating around measured value
    phi_signal = (phi_entries[0].data.get("phi", 1.0) if phi_entries else 1.0) + \
                 0.3 * np.sin(2 * np.pi * 0.5 * i * 0.1) + np.random.normal(0, 0.05)
    # Reasoning signal: correlated with consciousness but lagged
    reas_signal = 0.6 + 0.2 * np.sin(2 * np.pi * 0.5 * (i - 3) * 0.1) + \
                  np.random.normal(0, 0.08)

    metrics.add_time_series_data("conscious_unconscious", phi_signal, 0.5, t)
    metrics.add_time_series_data("pattern_reasoning", phi_signal, reas_signal, t)
    metrics.add_time_series_data("memory_learning", 0.7 + np.random.normal(0, 0.1),
                                 reas_signal, t)

# Compute synergy profiles
for pair_name in ["conscious_unconscious", "pattern_reasoning", "memory_learning"]:
    profile = metrics.compute_synergy_profile(pair_name)
    if profile:
        print(f"  ✦ {pair_name}:")
        print(f"      MI={profile.mutual_information:.4f}  "
              f"TE={profile.transfer_entropy:.4f}  "
              f"PLV={profile.phase_coupling:.4f}")
        print(f"      Coherence={profile.coherence:.4f}  "
              f"Emergence={profile.emergence_index:.4f}  "
              f"Integration={profile.integration_index:.4f}")
    else:
        print(f"  ✦ {pair_name}: insufficient data for profile")

# Flush synergy entries
sweep4_ids = production_sweep(bb, syn_adapter)
print(f"\n  → Posted {len(sweep4_ids)} synergy entries to blackboard")

# ── 9. Event history — what happened behind the scenes ──────────────

print("\n📡 Step 9: Event trail — what fired during the demo...\n")

events = bb.event_bus.get_history(limit=30)
print(f"  {len(events)} events in history (showing up to 15):\n")

seen_types = set()
for ev in events[:15]:
    if ev.event_type in seen_types:
        continue
    seen_types.add(ev.event_type)
    source = ev.source
    payload_keys = list(ev.payload.keys()) if isinstance(ev.payload, dict) else []
    print(f"    {source:20s} → {ev.event_type}")
    if payload_keys:
        print(f"    {'':20s}   payload: {', '.join(payload_keys)}")

# ── 10. Final blackboard state ──────────────────────────────────────

print("\n" + "=" * 70)
print("  FINAL BLACKBOARD STATE")
print("=" * 70)

bb_stats = bb.get_stats()
print(f"\n  Registered modules:  {bb_stats['registered_modules']}")
print(f"  Total posted:        {bb_stats['total_posted']}")
print(f"  Active entries:      {bb.active_entry_count}")

print(f"\n  Entries by topic:")
for topic, count in sorted(bb_stats["entries_by_topic"].items()):
    print(f"    {topic:40s}  {count:3d}")

print(f"\n  Entries by source module:")
for source, count in sorted(bb_stats["entries_by_source"].items()):
    print(f"    {source:20s}  {count:3d}")

eb_stats = bb_stats.get("event_bus", {})
print(f"\n  Event bus:")
print(f"    Total emitted:     {eb_stats.get('total_emitted', 0)}")
print(f"    Subscriptions:     {eb_stats.get('subscription_count', 0)}")
print(f"    Errors:            {eb_stats.get('error_count', 0)}")

# ── 11. Summary ─────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("  DEMO COMPLETE — Cross-Module Data Flow Summary")
print("=" * 70)
print("""
  The data flowed through four modules via the Cognitive Blackboard:

  ┌─────────────────┐    Φ value     ┌────────────────────┐
  │  Consciousness  │───────────────►│     Blackboard     │
  │  (IIT, Φ comp)  │                │                    │
  └─────────────────┘                │  ┌──────────────┐  │
                                     │  │   EventBus   │  │
  ┌─────────────────┐   inference    │  └──────┬───────┘  │
  │    Reasoning    │◄───────────────│         │          │
  │  (6-mode hybrid)│───────────────►│         ▼          │
  └─────────────────┘                │  topic routing     │
                                     │  + subscriptions   │
  ┌─────────────────┐    triples     │                    │
  │  Knowledge Graph│◄───────────────│                    │
  │  (Temporal KG)  │───────────────►│                    │
  └─────────────────┘                │                    │
                                     │                    │
  ┌─────────────────┐   MI/TE/PLV   │                    │
  │   Cog. Synergy  │◄───────────────│                    │
  │  (7 metrics)    │───────────────►│                    │
  └─────────────────┘                └────────────────────┘

  Each module both produces TO and consumes FROM the blackboard.
  Events propagate in real-time via the embedded EventBus.
  The Knowledge Graph persists inferences as temporal triples.
  Synergy metrics quantify cross-module information flow.
""")

kg_triples = kg.get_triples()
print(f"  Knowledge Graph triples:  {len(kg_triples)}")
for t in kg_triples[:5]:
    print(f"    ({t['subject']}) —[{t['predicate']}]→ ({t['object']})  "
          f"conf={t['confidence']:.2f}  type={t['statement_type']}")
if len(kg_triples) > 5:
    print(f"    ... and {len(kg_triples) - 5} more")

print(f"\n  Blackboard active entries: {bb.active_entry_count}")
print(f"  Events fired:             {eb_stats.get('total_emitted', 0)}")
print(f"  Modules communicating:    {bb.module_count}")
print()
