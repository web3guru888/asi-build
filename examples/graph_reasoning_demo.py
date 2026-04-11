#!/usr/bin/env python3
"""
Demonstrate graph intelligence:
- Create a knowledge graph with NetworkX (no Memgraph required)
- Run community detection (Louvain algorithm)
- Show how FastToG reasoning pipeline works

Note: The full FastToG pipeline requires a running Memgraph instance.
      This demo uses NetworkX directly to show the community detection
      algorithms, and explains the FastToG API.

Requires: numpy, networkx
"""

import networkx as nx
import numpy as np
from collections import defaultdict

print("=" * 60)
print("Graph Intelligence — Community Detection & FastToG Demo")
print("=" * 60)

# --- Part 1: Build a knowledge graph with clear community structure ---
print("\n--- Part 1: Building knowledge graph ---")

G = nx.Graph()

# Community 1: File operations
file_nodes = ["Save Button", "Save As Dialog", "File Menu", "Recent Files", "File Path Input"]
for n in file_nodes:
    G.add_node(n, community="file_ops", node_type="ui_element")
for i in range(len(file_nodes)):
    for j in range(i + 1, len(file_nodes)):
        if np.random.random() < 0.6:
            G.add_edge(file_nodes[i], file_nodes[j], weight=np.random.uniform(0.5, 1.0))

# Community 2: Edit operations
edit_nodes = ["Undo Button", "Redo Button", "Cut", "Copy", "Paste", "Find Dialog"]
for n in edit_nodes:
    G.add_node(n, community="edit_ops", node_type="ui_element")
for i in range(len(edit_nodes)):
    for j in range(i + 1, len(edit_nodes)):
        if np.random.random() < 0.6:
            G.add_edge(edit_nodes[i], edit_nodes[j], weight=np.random.uniform(0.5, 1.0))

# Community 3: Navigation
nav_nodes = ["Tab Bar", "Sidebar", "Breadcrumb", "Back Button", "Forward Button"]
for n in nav_nodes:
    G.add_node(n, community="navigation", node_type="ui_element")
for i in range(len(nav_nodes)):
    for j in range(i + 1, len(nav_nodes)):
        if np.random.random() < 0.6:
            G.add_edge(nav_nodes[i], nav_nodes[j], weight=np.random.uniform(0.5, 1.0))

# Add sparse cross-community edges (bridges)
G.add_edge("File Menu", "Find Dialog", weight=0.3)
G.add_edge("Tab Bar", "Recent Files", weight=0.2)

print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# --- Part 2: Louvain community detection ---
print("\n--- Part 2: Community detection (Louvain) ---")

try:
    # NetworkX ≥ 3.x includes community detection
    communities = nx.community.louvain_communities(G, seed=42)
except AttributeError:
    # Fallback: greedy modularity
    communities = list(nx.community.greedy_modularity_communities(G))

for i, comm in enumerate(communities):
    members = sorted(comm)
    print(f"  Community {i}: {members}")

# Calculate modularity
partition = {}
for i, comm in enumerate(communities):
    for node in comm:
        partition[node] = i
modularity = nx.community.modularity(G, communities)
print(f"\n  Modularity score: {modularity:.4f}")
print(f"  (> 0.3 indicates meaningful community structure)")

# --- Part 3: Community-level reasoning (FastToG concept) ---
print("\n--- Part 3: FastToG reasoning (concept demo) ---")
print("""
FastToG ("Fast Think-on-Graph") reasons community-by-community instead
of node-by-node, achieving ~75% faster reasoning for automation tasks.

Pipeline:
  1. PRUNE  → Select relevant communities for the user's intent
  2. REASON → Analyze each community's structure and purpose
  3. RANK   → Score communities by relevance × confidence
  4. ACT    → Extract recommended actions from top communities
""")

user_intent = "save document to file"
print(f"User intent: '{user_intent}'")
print()

# Simulate community relevance scoring
intent_words = set(user_intent.lower().split())
for i, comm in enumerate(communities):
    # Score based on keyword overlap with node names
    comm_words = set()
    for node in comm:
        comm_words.update(node.lower().split())

    overlap = intent_words & comm_words
    relevance = len(overlap) / max(len(intent_words), 1)

    # Determine community purpose from majority ground truth
    gt_communities = defaultdict(int)
    for node in comm:
        gt = G.nodes[node].get("community", "unknown")
        gt_communities[gt] += 1
    purpose = max(gt_communities, key=gt_communities.get)

    status = "⭐ SELECTED" if relevance > 0 else "   skipped"
    print(f"  Community {i} ({purpose:12s}): relevance={relevance:.2f} "
          f"overlap={overlap or '∅':} {status}")

print("""
  In production, the FastToGReasoningEngine:
  - Uses SchemaManager to query Memgraph (graph DB)
  - Runs CommunityDetectionEngine for real-time community updates
  - Applies CommunityPruningSystem to filter irrelevant communities
  - Generates CommunityTextGenerator summaries for LLM reasoning

  API usage:
    from asi_build.graph_intelligence.fastog_reasoning import (
        FastToGReasoningEngine, ReasoningRequest, ReasoningMode
    )
    engine = FastToGReasoningEngine(schema_manager)
    result = await engine.reason(ReasoningRequest(
        user_intent="save document to file",
        context={"application": "notepad"},
        reasoning_mode=ReasoningMode.COMMUNITY_BASED,
    ))
    print(result.final_recommendation)
""")

print("✅ Graph intelligence demo complete.")
