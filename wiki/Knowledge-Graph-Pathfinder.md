# Knowledge Graph Pathfinder

> **Module**: `src/asi_build/knowledge_graph/pathfinder.py`  
> **LOC**: 484 | **Status**: ✅ Stable | **Dependencies**: `knowledge_graph.temporal_kg` only (no external libraries)

The pathfinder implements **semantic A\* search** over the `TemporalKnowledgeGraph`, finding the lowest-cost reasoning path between two entities by traversing the triple graph.

---

## Why Pathfinding Matters for ASI

A knowledge graph lookup tells you what's *directly* connected. Pathfinding tells you *how* two concepts relate when there's no direct link — the chain of causal, taxonomic, or associative relationships that connect them.

Example query:
```
find_path("neural_plasticity", "quantum_decoherence")
```

There is no direct triple linking these. But a multi-hop path might exist:
```
neural_plasticity
  → causes → synaptic_remodeling
  → involves_variable → entropy
  → scales_with → quantum_decoherence
```

This kind of multi-hop reasoning — with explicit edge semantics — is what makes the pathfinder a key component for the [CognitiveCycle](CognitiveCycle) Phase 4 (Associative Memory Recall).

---

## Core API

```python
from asi_build.knowledge_graph.pathfinder import KGPathfinder
from asi_build.knowledge_graph.temporal_kg import TemporalKnowledgeGraph

kg = TemporalKnowledgeGraph()
# ... populate kg with triples ...

finder = KGPathfinder(kg)

result = finder.find_path(
    start="neural_plasticity",
    goal="quantum_decoherence",
    max_depth=6,                    # Max hops
    max_iterations=1000,            # A* iteration budget
    embedding_fn=my_embed_fn,       # Optional: enables semantic heuristic
)
```

### `find_path` parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `start` | `str` | required | Source entity name |
| `goal` | `str` | required | Target entity name |
| `max_depth` | `int` | `6` | Maximum path length in hops |
| `max_iterations` | `int` | `1000` | A* loop budget |
| `embedding_fn` | `Callable[[str], List[float]]` | `None` | If provided, enables semantic heuristic |

### `PathResult` dataclass

```python
@dataclass
class PathResult:
    path: List[str]          # Ordered entity names from start to goal
    total_cost: float        # Accumulated traversal cost
    nodes_explored: int      # Unique nodes popped from open set
    complete: bool           # True if goal was reached
    iterations: int          # Main-loop iterations executed
    edges: List[Dict]        # Per-hop edge info: predicate, cost, pheromone
```

The `edges` field provides full interpretability — each hop is annotated with the predicate used, the base cost, and the pheromone modifier applied.

---

## How It Works

### 1. Bidirectional Traversal

Triples `(A, predicate, B)` are traversable in both directions:
- Forward: `A → B` (standard)
- Backward: `B → A` (reversed, with `_rev` suffix on predicate)

This means the pathfinder can discover chains like `"caused_by"` relationships even if only the forward `"causes"` triple is stored.

### 2. Predicate-Based Edge Costs

Each predicate has a base traversal cost. Stronger semantic relationships cost less:

```python
BASE_COSTS = {
    "subclass_of":             0.25,   # Strong taxonomic
    "bidirectionally_causes":  0.25,   # Strong causal
    "causes":                  0.30,   # Causal
    "instance_of":             0.30,   # Taxonomic
    "scales_with":             0.35,   # Quantitative
    "produced_by":             0.40,   # Productive
    "associated_with":         0.50,   # Loose
    "correlated_with":         0.60,   # Statistical
    "possibly_causes":         0.70,   # Weak causal
    "related_to":              0.80,   # Near-vacuous
}
DEFAULT_BASE_COST = 0.50
```

A path through three causal edges (`3 × 0.30 = 0.90`) is much cheaper than three vague associations (`3 × 0.80 = 2.40`). The pathfinder thus prefers explanatory, mechanistic chains.

### 3. Pheromone Modifiers

The `TemporalKnowledgeGraph` tracks pheromone levels on each triple — reinforced when paths are used. The pathfinder reads these as a cost modifier:

```python
def _edge_cost(self, source: str, target: str) -> float:
    base = BASE_COSTS.get(edge["predicate"], DEFAULT_BASE_COST)
    modifier = self.kg.get_pheromone_modifier(edge["triple_id"])
    return base * modifier
```

Well-trodden paths become cheaper over time — a form of **procedural memory** emerging at the graph layer. This is analogous to ACO (Ant Colony Optimization), where ants reinforce successful routes.

> ⚠️ **Open question**: If pheromone levels only ever increase, reasoning paths will calcify. Is there a decay schedule? See [Research Notes](Research-Notes) for discussion.

### 4. Adaptive Semantic Heuristic

When an `embedding_fn` is provided, the A\* heuristic uses cosine similarity between entity embeddings:

```python
def _heuristic(self, current: str, goal: str) -> float:
    sim = _cosine_similarity(emb_current, emb_goal)
    # Adaptive weighting based on domain similarity
    if sim >= CROSS_DOMAIN_THRESHOLD:  # 0.3
        # Same domain — trust semantics heavily
        h_semantic = (1 - sim) * SAME_DOMAIN_SEMANTIC_WEIGHT  # 0.9
        h_graph    = graph_dist * SAME_DOMAIN_GRAPH_WEIGHT    # 0.1
    else:
        # Cross-domain — blend equally
        h_semantic = (1 - sim) * CROSS_DOMAIN_SEMANTIC_WEIGHT  # 0.5
        h_graph    = graph_dist * CROSS_DOMAIN_GRAPH_WEIGHT    # 0.5
    return h_semantic + h_graph
```

| Domain relationship | Semantic weight | Graph-distance weight |
|---|---|---|
| Same domain (sim ≥ 0.3) | 0.9 | 0.1 |
| Cross-domain (sim < 0.3) | 0.5 | 0.5 |

The cross-domain blend prevents the semantic heuristic from leading search into dense embedding clusters far from the actual goal.

Without `embedding_fn`, the heuristic falls back to a graph-distance estimate (`0.5 / (depth + 1)`).

---

## Example Output

```python
result = finder.find_path("synaptic_plasticity", "hebbian_learning", max_depth=4)

# result.complete = True
# result.path = ["synaptic_plasticity", "long_term_potentiation", "hebbian_learning"]
# result.total_cost = 0.60  (two causal edges)
# result.nodes_explored = 8
# result.edges = [
#   {"predicate": "causes", "cost": 0.30, "pheromone": 1.0},
#   {"predicate": "instance_of", "cost": 0.30, "pheromone": 1.2}
# ]
```

---

## Integration with CognitiveCycle

The pathfinder is a natural fit for **Phase 4: Associative Memory Recall** in the [CognitiveCycle](CognitiveCycle):

```python
# During associative recall phase:
path_result = pathfinder.find_path(
    start=current_percept_entity,
    goal=working_memory_focus,
    max_depth=5,
    embedding_fn=sentence_encoder
)
if path_result.complete:
    blackboard.write("reasoning/knowledge_chain", path_result.edges)
```

The `edges` output is written to the Blackboard so the reasoning module (Phase 5) can use it as grounded context.

---

## Open Questions

| Question | Priority | Issue |
|---|---|---|
| Should `find_path` accept `valid_at: datetime` to filter bi-temporal edges? | High | [#34](https://github.com/web3guru888/asi-build/issues/34) |
| Pheromone decay schedule to prevent path calcification | Medium | — |
| Beam-search variant for dense graphs | Low | — |
| Blackboard integration pattern for CognitiveCycle | High | [#41](https://github.com/web3guru888/asi-build/issues/41) |

---

## Related Pages

- [Knowledge Graph](Knowledge-Graph) — bi-temporal KG overview, API reference
- [CognitiveCycle](CognitiveCycle) — how pathfinding fits into the full perception-action loop
- [Architecture](Architecture) — overall layered design
- [Research Notes](Research-Notes) — pheromone dynamics, temporal filtering open questions
