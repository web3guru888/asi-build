# Graph Intelligence Module

**Path**: `src/asi_build/graph_intelligence/`  
**Size**: 20 Python files, **8,762 LOC**  
**Status**: ✅ Active — Community detection, FastToG reasoning, graph schema, performance caching

---

## Overview

The Graph Intelligence module implements a **FastToG (Fast Think-on-Graph)** reasoning system that enables community-structured graph reasoning. It provides:

- **Community detection** using Louvain and other algorithms
- **FastToG reasoning** — thinking "community by community" for 75%+ faster, more accurate decisions (based on [arXiv:2501.14300v1](https://arxiv.org/abs/2501.14300))
- **Graph schema** with typed nodes, typed relationships, and Cypher-safe sanitization
- **Performance optimisation** — LRU cache with TTL, parallel processing, memory management

The module was designed for UI/workflow automation intelligence ("Kenny Integration") but its graph reasoning architecture is domain-agnostic and integrates naturally with the Cognitive Blackboard.

---

## Architecture

```
graph_intelligence/
├── schema.py                # NodeType, RelationshipType enums + data classes
├── schema_manager.py        # DDL/DML for Memgraph/Neo4j backends
├── community_detection.py   # Louvain + quality metrics
├── community_pruning.py     # Noise filtering, relevance thresholds
├── community_to_text.py     # Verbalize community for LLM prompts
├── fastog_reasoning.py      # Core FastToG engine (858 LOC)
├── kenny_integration.py     # High-level integration facade
├── performance_optimizer.py # LRU cache, thread pool, gc tuning
├── data_ingestion.py        # Bulk graph loading utilities
├── memgraph_connection.py   # Connection pool + retry logic
├── backup_memgraph.py       # JSON backup/restore
└── rebuild_schema.py        # Schema migration helper
```

---

## Core Concepts

### Graph Schema

The module defines a rich typed schema for knowledge graphs:

**Node Types** (`NodeType` enum):

| Type | Description |
|------|-------------|
| `UIElement` | A widget, button, or interactive component |
| `Workflow` | A named sequence of user actions |
| `Community` | A detected cluster of related nodes |
| `Application` | A software application context |
| `Screen` | A specific screen/view within an application |
| `Pattern` | A recurring interaction or navigation pattern |
| `Error` | A captured error event |
| `UserAction` | A single recorded user interaction |
| `Prediction` | A predicted next action or outcome |
| `MemoryItem` | A persisted memory artefact |
| `MemorySession` | A bounded session of memory items |
| `UserProfile` | User preferences and behavioural profile |
| `MemoryPattern` | A recurring pattern across sessions |

**Relationship Types** (`RelationshipType` enum):

| Relationship | Direction | Semantics |
|-------------|-----------|-----------|
| `CONTAINS` | parent → child | UI hierarchy |
| `TRIGGERS` | action → result | cause-effect |
| `NAVIGATES_TO` | screen → screen | navigation flow |
| `REQUIRES` | step → dependency | prerequisite |
| `PRECEDES` | A → B | temporal ordering |
| `BELONGS_TO` | node → community | cluster membership |
| `SIMILAR_TO` | A ↔ B | pattern similarity (undirected) |
| `CAUSED_BY` | error → cause | root cause tracing |
| `RESOLVES` | fix → error | resolution edge |
| `FOLLOWED_BY` | A → B | action sequence |
| `REMEMBERS` | entity → memory | memory linkage |
| `CONTAINS_MEMORY` | session → item | session scoping |

**Security note**: All Cypher labels and relationship types are sanitised through `_sanitize_label()` (regex: `[^a-zA-Z0-9_]`) to prevent Cypher injection — this is explicitly noted in the source.

---

## Community Detection

### Louvain Algorithm (`LouvainCommunityDetection`)

The Louvain algorithm maximises graph **modularity** `Q`:

```
Q = (1/2m) Σ[A_ij - k_i·k_j/(2m)] · δ(c_i, c_j)
```

Where:
- `m` = total edge weight
- `A_ij` = adjacency matrix entry
- `k_i` = weighted degree of node i
- `c_i` = community assignment
- `δ` = Kronecker delta

Parameters:
- `resolution`: float (default 1.0) — higher values yield smaller, more granular communities
- `max_iterations`: int (default 100) — stopping criterion

### Quality Metrics (`CommunityQualityMetrics`)

After detection, communities are evaluated on six dimensions:

| Metric | Measures |
|--------|----------|
| `modularity` | Global community separation quality (higher = better) |
| `coverage` | Fraction of edges inside communities |
| `performance` | Ratio of intra-community edges + non-edges |
| `conductance` | Boundary sharpness (lower = better) |
| `internal_density` | Intra-community edge density |
| `external_density` | Cross-community edge density |

### Result Object

```python
@dataclass
class CommunityDetectionResult:
    communities: List[Dict[str, Any]]
    algorithm: str          # "louvain", "leiden", etc.
    modularity: float
    processing_time: float
    node_count: int
    edge_count: int
    community_count: int
    quality_metrics: Dict[str, float]
```

---

## FastToG Reasoning Engine

Based on the [FastToG paper (arXiv:2501.14300)](https://arxiv.org/abs/2501.14300), the engine reasons **community-by-community** rather than node-by-node. This yields:

- **~75% faster** traversal on large graphs (communities collapse sub-graphs)
- **Higher accuracy** because community context primes the reasoning
- **Explainability** — each reasoning step maps to a named community

### Reasoning Modes

```python
class ReasoningMode(Enum):
    COMMUNITY_BASED = "community_based"  # Full FastToG — community-first
    TRADITIONAL     = "traditional"      # Node-by-node (baseline)
    HYBRID          = "hybrid"           # FastToG + fallback node traversal
```

### Usage

```python
from asi_build.graph_intelligence.fastog_reasoning import (
    FastToGReasoningEngine, ReasoningRequest, ReasoningMode
)

engine = FastToGReasoningEngine(schema_manager)

request = ReasoningRequest(
    user_intent="Find the shortest workflow to submit a support ticket",
    context={"application": "helpdesk", "current_screen": "home"},
    max_communities=10,
    reasoning_mode=ReasoningMode.HYBRID,
    include_explanations=True,
    timeout_seconds=30
)

result = await engine.reason(request)
print(result.explanation)     # Natural language reasoning trace
print(result.recommended_path) # Ordered list of workflow steps
print(result.confidence)      # [0.0, 1.0] confidence score
```

### `CommunityReasoning` Data Class

Each community visited during reasoning produces:

```python
@dataclass
class CommunityReasoning:
    community_id: str
    community_description: str  # from community_to_text
    relevance_score: float
    reasoning_steps: List[str]
    nodes_visited: List[str]
    confidence: float
```

---

## Community Pruning

`CommunityPruningSystem` filters low-signal communities before they reach the reasoning engine:

- **Noise threshold**: communities below minimum modularity contribution are dropped
- **Relevance scoring**: cosine similarity between community centroid and query embedding
- **Size constraints**: min/max node count per community (prevents giant or singleton communities)

---

## Community-to-Text

`CommunityTextGenerator` converts community structure into natural-language descriptions suitable for LLM prompts:

```
"Community 'checkout_flow' contains 8 UIElements and 3 Workflows.
 Key nodes: [AddToCart, Checkout, PaymentForm]. 
 Dominant relationship: NAVIGATES_TO (12 edges).
 This community represents the e-commerce purchase path."
```

This bridges graph structure and language models — a key step in neurosymbolic reasoning.

---

## Performance Layer

`PerformanceOptimizer` wraps `FastToGReasoningEngine` with:

### LRU Cache with TTL

```python
class LRUCache:
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0):
        ...
```

Thread-safe (uses `threading.RLock()`). Cache keys are query hashes. Expired entries are lazily evicted.

### Parallel Community Scoring

Uses `ThreadPoolExecutor` to score community relevance in parallel — important when `max_communities` is large.

### Memory Management

Periodic `gc.collect()` calls and configurable object limits prevent memory leaks during long-running graph sessions.

---

## Integration with Cognitive Blackboard

The Graph Intelligence module is a natural candidate for Blackboard integration. A `GraphBlackboardAdapter` would:

1. **Publish** community detection results as `GRAPH_COMMUNITY_DETECTED` events
2. **Subscribe** to `KNOWLEDGE_UPDATED` events to trigger incremental re-analysis
3. **Write** `FastToGResult` objects as Blackboard entries with `source="graph_intelligence"`

```python
# Proposed integration (see Issue #XX)
class GraphBlackboardAdapter(BlackboardAdapter):
    async def on_event(self, event: BlackboardEvent):
        if event.type == "KNOWLEDGE_UPDATED":
            result = await self.engine.reason(
                ReasoningRequest(user_intent=event.data["query"])
            )
            await self.blackboard.write(
                "graph_intelligence/latest_reasoning",
                result.model_dump()
            )
```

---

## Open Questions

1. **Scalability**: The current Louvain implementation uses NetworkX in-process. For production-scale graphs (millions of nodes), this needs either a distributed implementation or a native Memgraph/Neo4j community-detection plugin. At what graph scale should we switch?

2. **Dynamic graphs**: Communities are detected on a static snapshot. How should the system handle continuous graph updates — re-run full detection periodically, or maintain community membership incrementally?

3. **Embedding alignment**: `CommunityTextGenerator` uses structural descriptions. Should it instead use learned node embeddings (e.g. GraphSAGE, Node2Vec) to produce richer community representations?

4. **FastToG + IIT Φ**: Could community structure inform consciousness measurement? IIT Φ measures information integration — graph communities with high internal modularity might correspond to candidate "conscious complexes". Worth exploring.

5. **Blackboard adapter**: Issue #XX (planned) will wire this module to the Cognitive Blackboard. What should the event schema look like?

---

## Related

- [[Knowledge-Graph]] — bi-temporal knowledge representation layer
- [[Knowledge-Graph-Pathfinder]] — semantic A* over the knowledge graph
- [[Cognitive-Blackboard]] — central integration hub
- [[Hybrid-Reasoning]] — reasoning engine that could consume FastToG results
- [[Architecture]] — layered module design
