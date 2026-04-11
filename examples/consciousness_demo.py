#!/usr/bin/env python3
"""
Demonstrate the consciousness engine:
- Initialize Global Workspace Theory (GWT)
- Create workspace content with competing coalitions
- Run competition and broadcast winner
- Compute IIT Φ (Integrated Information Theory)

Requires: numpy, scipy, networkx
"""

import time
import numpy as np

# --- Part 1: Global Workspace Theory ---
from asi_build.consciousness.global_workspace import (
    GlobalWorkspaceTheory, WorkspaceContent, CognitiveProcessor,
)

print("=" * 60)
print("Part 1: Global Workspace Theory (GWT)")
print("=" * 60)

# Create GWT instance. The constructor calls _initialize(), which
# registers 8 default cognitive processors (visual, linguistic, etc.).
gwt = GlobalWorkspaceTheory(config={"competition_threshold": 0.1})

# Show the processors that were auto-created
print(f"\nDefault processors ({len(gwt.cognitive_processors)}):")
for pid, proc in gwt.cognitive_processors.items():
    print(f"  {pid:12s}  interests={sorted(proc.interests)}")

# Add a custom processor
gwt.add_processor(CognitiveProcessor(
    "scientific", "scientific_reasoning",
    interests={"hypothesis", "data", "experiment"},
))
print(f"\nAfter adding 'scientific': {len(gwt.cognitive_processors)} processors")

# Submit competing workspace content
contents = [
    WorkspaceContent("visual_alert", {"type": "alert", "tags": ["visual", "ui"]},
                     source="screen_monitor", activation_level=0.9),
    WorkspaceContent("text_query", {"type": "query", "tags": ["text", "nlp"]},
                     source="user_input", activation_level=0.6),
    WorkspaceContent("experiment", {"type": "result", "tags": ["hypothesis", "data"]},
                     source="research_engine", activation_level=0.7),
]

for c in contents:
    gwt.submit_content(c)
    print(f"\nSubmitted '{c.content_id}' (activation={c.activation_level})")

# The submit_content method triggers competition automatically when
# the buffer has ≥ 2 items. The strongest content gets broadcast.
state = gwt.get_current_state()
print(f"\n--- GWT State ---")
print(f"  Total broadcasts : {state['total_broadcasts']}")
print(f"  Competition events: {state['competition_events']}")
print(f"  Conscious content : {state['conscious_content']}")
print(f"  Attention focus   : {dict(list(state['attention_focus'].items())[:5])}")

# Show broadcast history
for bh in gwt.get_broadcast_history():
    print(f"  Broadcast {bh['broadcast_id']}: "
          f"content={bh['content_id']} → {len(bh['recipients'])} processors")


# --- Part 2: Integrated Information Theory (IIT) ---
from asi_build.consciousness.integrated_information import (
    IntegratedInformationTheory, SystemElement, Connection,
)

print("\n" + "=" * 60)
print("Part 2: Integrated Information Theory (IIT)")
print("=" * 60)

# Create IIT instance. _initialize() builds a default 3-layer network
# (4 sensory → 6 processing → 3 output) with probabilistic connections.
iit = IntegratedInformationTheory(config={
    "phi_threshold": 0.01,    # lower threshold so we find complexes
    "max_partition_size": 6,  # cap partition search for speed
})

state = iit.get_current_state()
print(f"\nDefault network: {state['num_elements']} elements, "
      f"{state['num_connections']} connections")

# Add a custom element and connect it
custom = SystemElement("custom_0", state=0.5, activation_function="sigmoid")
iit.add_element(custom)
iit.add_connection(Connection("process_0", "custom_0", weight=0.6))
iit.add_connection(Connection("custom_0", "output_0", weight=0.4))
print(f"After additions: {len(iit.elements)} elements, "
      f"{len([c for c in iit.connections if c.active])} connections")

# Drive the system with external input and let state propagate
for step in range(5):
    inputs = {f"sensory_{i}": np.random.random() for i in range(4)}
    iit.update_system_state(inputs)

# Compute Φ for the whole system
phi_all = iit.calculate_phi()
print(f"\nΦ (whole system) = {phi_all:.4f}")

# Compute Φ for a small subset
subset = {"process_0", "process_1", "process_2"}
phi_sub = iit.calculate_phi(subset)
print(f"Φ (process_0..2) = {phi_sub:.4f}")

# Find conscious complexes (subsets with Φ > threshold)
complexes = iit.find_conscious_complexes()
print(f"\nConscious complexes found: {len(complexes)}")
for cx in complexes[:3]:
    print(f"  {cx.complex_id}: Φ={cx.phi_value:.4f}, "
          f"elements={sorted(cx.elements)}, main={cx.main_complex}")

print("\n✅ Consciousness engine demo complete.")
