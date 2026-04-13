# Phase 26.1 — ConceptGraph: Hierarchical Concept Representation & Semantic Networks

> **Issue**: [#578](https://github.com/web3guru888/asi-build/issues/578) | **S&T**: [#583](https://github.com/web3guru888/asi-build/discussions/583) | **Q&A**: [#584](https://github.com/web3guru888/asi-build/discussions/584) | **Planning**: [#577](https://github.com/web3guru888/asi-build/discussions/577)

## Overview

`ConceptGraph` provides hierarchical concept representation with is-a, has-a, and part-of relations. It implements semantic networks (Quillian 1967), frame systems (Minsky 1974), prototype theory (Rosch 1975), and conceptual spaces (Gärdenfors 2000).

## Theoretical Background

### Semantic Networks (Quillian 1967)
Concepts are represented as nodes in a graph, connected by labeled edges (IS_A, HAS_A, etc.). Information retrieval uses **spreading activation** — activating a source node and letting activation propagate along edges with exponential decay.

### Prototype Theory (Rosch 1975)
Category membership is not binary but graded. A robin is a more *typical* bird than a penguin. The `typicality` field captures this gradient on [0, 1].

### Conceptual Spaces (Gärdenfors 2000)
Concepts can be represented as regions in geometric quality dimensions. The optional `embedding` field provides this vector representation for geometric similarity computation.

## Data Structures

### ConceptRelation Enum

```python
class ConceptRelation(str, Enum):
    IS_A = "is_a"              # taxonomic subsumption
    HAS_A = "has_a"            # property possession
    PART_OF = "part_of"        # mereological composition
    CAUSES = "causes"          # causal relation
    ENABLES = "enables"        # enablement precondition
    INHIBITS = "inhibits"      # suppression/blocking
    SIMILAR_TO = "similar_to"  # analogical similarity
```

### ConceptNode Frozen Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `concept_id` | `str` | Unique identifier |
| `name` | `str` | Human-readable label |
| `properties` | `FrozenSet[str]` | Inherited + own properties |
| `parent_ids` | `FrozenSet[str]` | IS_A parents (multiple inheritance) |
| `children_ids` | `FrozenSet[str]` | IS_A children |
| `exemplars` | `Tuple[str, ...]` | Prototype exemplar instances |
| `typicality` | `float` | Rosch typicality gradient [0,1] |
| `embedding` | `Optional[Tuple[float, ...]]` | Gärdenfors conceptual space vector |

### ConceptEdge Frozen Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | `str` | Source concept |
| `target_id` | `str` | Target concept |
| `relation` | `ConceptRelation` | Edge type |
| `weight` | `float` | Relation strength (default 1.0) |
| `context` | `Optional[str]` | Situational qualifier |

## Protocol

```python
@runtime_checkable
class ConceptGraph(Protocol):
    async def add_concept(self, node: ConceptNode) -> None: ...
    async def add_relation(self, edge: ConceptEdge) -> None: ...
    async def get_concept(self, concept_id: str) -> Optional[ConceptNode]: ...
    async def query_subsumption(self, child_id: str, ancestor_id: str) -> bool: ...
    async def find_common_ancestor(self, id_a: str, id_b: str) -> Optional[str]: ...
    async def get_neighborhood(self, concept_id: str, depth: int = 1,
                                relation_filter: Optional[Set[ConceptRelation]] = None) -> Set[ConceptNode]: ...
    async def propagate_properties(self, concept_id: str) -> FrozenSet[str]: ...
    async def compute_similarity(self, id_a: str, id_b: str) -> float: ...
    async def spreading_activation(self, source_id: str, decay: float = 0.8,
                                    threshold: float = 0.1) -> Dict[str, float]: ...
```

## Implementation: SemanticConceptGraph

### Storage
```python
self._nodes: dict[str, ConceptNode] = {}
self._adjacency: dict[str, list[ConceptEdge]] = defaultdict(list)
self._reverse_adjacency: dict[str, list[ConceptEdge]] = defaultdict(list)
```

### Key Algorithms

**Property Inheritance**: Depth-first IS_A traversal with override semantics. Child properties shadow parent properties.

**Subsumption Check**: BFS up IS_A edges from child, O(V+E) worst-case.

**Common Ancestor**: Bidirectional BFS from both nodes, first intersection = LCA.

**Spreading Activation**: Quillian-style — activate source, propagate with `activation × decay × weight` per hop, collect above threshold.

**Similarity Metric**: Weighted combination of Wu-Palmer path similarity (0.4), Jaccard coefficient on properties (0.3), cosine similarity on embeddings (0.3 if available).

### Data Flow

```
Input Knowledge
    │
    ▼
ConceptNode ──► ConceptEdge
    │               │
    ▼               ▼
Property        Adjacency Index
Inheritance     (forward + reverse)
    │               │
    ▼               ▼
Spreading ◄──── Graph Traversal
Activation
    │
    ▼
Similarity ◄── Subsumption Check
    │
    ▼
Query Results
```

## Metrics (Prometheus)

| Metric | Type | Description |
|--------|------|-------------|
| `concept_graph_nodes_total` | Gauge | Total concept nodes |
| `concept_graph_edges_total` | Gauge | Total edges by relation type |
| `concept_graph_query_seconds` | Histogram | Query latency |
| `concept_graph_activation_spread_hops` | Histogram | Hops per activation |
| `concept_graph_similarity_score` | Histogram | Similarity distribution |

## Integration Points

- **WorldModel (13.1)**: Concept layer for world entities
- **KnowledgeFusion (20.3)**: Fused entries map to properties
- **SemanticParser (19.1)**: Parsed structures instantiate nodes/edges
- **OntologyManager (26.2)**: Formalized concept relations
- **CommonSenseEngine (26.4)**: Similarity for analogical transfer

## Test Targets (12)

1. `test_add_concept_stores_node`
2. `test_add_relation_creates_edge`
3. `test_query_subsumption_transitive`
4. `test_query_subsumption_negative`
5. `test_find_common_ancestor_diamond`
6. `test_property_propagation_inheritance`
7. `test_property_propagation_override`
8. `test_spreading_activation_decay`
9. `test_spreading_activation_threshold`
10. `test_similarity_identical_concepts`
11. `test_similarity_unrelated_concepts`
12. `test_null_graph_returns_empty`

## References

- Quillian, M.R. (1967). *Word concepts: A theory and simulation of some basic semantic capabilities*
- Minsky, M. (1974). *A framework for representing knowledge*
- Rosch, E. (1975). *Cognitive representations of semantic categories*
- Gärdenfors, P. (2000). *Conceptual Spaces: The Geometry of Thought*
- Collins, A.M. & Loftus, E.F. (1975). *A spreading-activation theory of semantic processing*

---

## Phase 26 Sub-phase Tracker

| # | Component | Issue | Status |
|---|-----------|-------|--------|
| 26.1 | ConceptGraph | #578 | ✅ Spec'd |
| 26.2 | OntologyManager | #579 | ✅ Spec'd |
| 26.3 | KnowledgeCompiler | #580 | ✅ Spec'd |
| 26.4 | CommonSenseEngine | #581 | ✅ Spec'd |
| 26.5 | KnowledgeOrchestrator | #582 | ✅ Spec'd |
