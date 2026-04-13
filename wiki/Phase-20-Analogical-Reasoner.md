# Phase 20.2 — AnalogicalReasoner

> **Structure Mapping Theory implementation for cross-domain analogical transfer and relational similarity scoring.**

| Field | Value |
|---|---|
| **Package** | `asi.reasoning.analogy` |
| **Since** | Phase 20.2 |
| **Depends on** | WorldModel 13.1, LogicalInferenceEngine 20.1 |
| **Integrates with** | CognitiveCycle, CuriosityModule 13.3, KnowledgeFusion 20.3 |
| **Complexity** | High — constraint-satisfaction mapping, systematic scoring |

---

## Overview

The **AnalogicalReasoner** implements Gentner's **Structure Mapping Theory (SMT)** for analogical reasoning. It maps relational structure from a familiar *source* domain to a novel *target* domain, enabling cross-domain knowledge transfer. When the system encounters a new problem, the analogical reasoner finds structurally similar known domains and transfers applicable relations — filling knowledge gaps without requiring direct experience.

Analogical reasoning is uniquely powerful because it enables:
- **Cross-domain learning** — apply solar-system knowledge to atomic structure
- **Creative problem solving** — recognise structural parallels in novel situations
- **Efficient knowledge acquisition** — bootstrap understanding of new domains from existing knowledge

### Design Principles

| Principle | Rationale |
|---|---|
| **Structure over surface** | Prefer relational matches over attribute matches (Gentner's systematicity principle) |
| **One-to-one mapping** | Each source entity maps to at most one target entity (prevents degenerate mappings) |
| **Pragmatic centrality** | Prefer mappings involving goal-relevant relations |
| **Confidence decay** | Transferred knowledge carries reduced confidence proportional to mapping quality |
| **Frozen dataclasses** | Immutable domain structures and mappings |

---

## Enums

### `MappingConstraint`

```python
class MappingConstraint(str, enum.Enum):
    ONE_TO_ONE             = "one_to_one"             # Bijective entity mapping
    PARALLEL_CONNECTIVITY  = "parallel_connectivity"  # Connected predicates must co-map
    SYSTEMATICITY          = "systematicity"           # Prefer deep relational chains
    PRAGMATIC_CENTRALITY   = "pragmatic_centrality"   # Prefer goal-relevant relations
```

### `AnalogyStrength`

```python
class AnalogyStrength(str, enum.Enum):
    STRONG   = "strong"    # similarity ≥ 0.7
    MODERATE = "moderate"  # 0.4 ≤ similarity < 0.7
    WEAK     = "weak"      # 0.2 ≤ similarity < 0.4
    NONE     = "none"      # similarity < 0.2
```

### `RelationType`

```python
class RelationType(str, enum.Enum):
    CAUSAL     = "causal"      # A causes B
    TEMPORAL   = "temporal"    # A before/after B
    SPATIAL    = "spatial"     # A near/far B
    FUNCTIONAL = "functional"  # A enables/prevents B
    TAXONOMIC  = "taxonomic"   # A is-a/part-of B
    PART_WHOLE = "part_whole"  # A contains B
```

---

## Frozen Dataclasses

### `Relation`

```python
@dataclass(frozen=True, slots=True)
class Relation:
    relation_type: RelationType         # Causal, temporal, etc.
    predicate: str                      # e.g. "attracts", "orbits"
    arguments: tuple[str, ...]          # Participating entities
    weight: float = 1.0                 # Importance weight
    is_higher_order: bool = False       # Relations between relations
```

### `DomainStructure`

```python
@dataclass(frozen=True, slots=True)
class DomainStructure:
    domain_id: str                              # Unique identifier
    entities: frozenset[str]                    # Domain entities
    relations: tuple[Relation, ...]             # Relational structure
    attributes: dict[str, Any] = field(default_factory=dict)  # Entity attributes
```

### `StructureMapping`

```python
@dataclass(frozen=True, slots=True)
class StructureMapping:
    source: DomainStructure                     # Known domain
    target: DomainStructure                     # Novel domain
    entity_map: dict[str, str]                  # source_entity → target_entity
    relation_map: dict[str, str]                # source_predicate → target_predicate
    similarity_score: float                     # Overall mapping quality (0–1)
    strength: AnalogyStrength                   # Binned strength
    inferred_relations: tuple[Relation, ...]    # New target relations from transfer
```

### `AnalogyConfig`

```python
@dataclass(frozen=True, slots=True)
class AnalogyConfig:
    min_similarity: float = 0.3           # Below this, return NONE
    max_candidates: int = 50              # Max source candidates to evaluate
    systematicity_weight: float = 0.6     # Weight for deep relational chains
    pragmatic_weight: float = 0.2         # Weight for goal-relevant relations
    one_to_one_strict: bool = True        # Enforce bijective mapping
    max_depth: int = 5                    # Max higher-order relation depth
```

---

## Protocol

```python
@runtime_checkable
class AnalogicalReasoner(Protocol):

    async def find_analogy(
        self, source: DomainStructure, target: DomainStructure
    ) -> StructureMapping:
        """Find the best structural mapping between source and target."""
        ...

    async def transfer_knowledge(
        self, mapping: StructureMapping
    ) -> tuple[Relation, ...]:
        """Infer new target relations from the mapping."""
        ...

    async def find_best_source(
        self, target: DomainStructure, candidates: tuple[DomainStructure, ...]
    ) -> StructureMapping:
        """Find the best source domain for a given target from candidates."""
        ...

    async def similarity(
        self, a: DomainStructure, b: DomainStructure
    ) -> float:
        """Compute structural similarity between two domains (0–1)."""
        ...

    async def get_mappings(self) -> tuple[StructureMapping, ...]:
        """Return all cached mappings."""
        ...
```

---

## Implementation — `AsyncAnalogicalReasoner`

### Construction

```python
class AsyncAnalogicalReasoner:
    def __init__(self, config: AnalogyConfig) -> None:
        self._config = config
        self._cached_mappings: dict[tuple[str, str], StructureMapping] = {}
        self._lock = asyncio.Lock()
```

### SMT Algorithm

The Structure Mapping algorithm proceeds in four phases:

```
Phase 1 — Predicate Matching
  For each source relation, find target relations with matching RelationType.
  Build candidate predicate pairs: (source_pred, target_pred).

Phase 2 — Entity Mapping Extension
  From predicate pairs, derive entity correspondences.
  Enforce one-to-one constraint: each entity maps to at most one target.
  Use greedy best-first search with backtracking for conflicts.

Phase 3 — Scoring
  systematicity_score = depth-weighted count of matched relational chains
  pragmatic_score = fraction of goal-relevant relations mapped
  entity_overlap_score = |mapped_entities| / max(|source|, |target|)
  
  similarity = (systematicity × 0.6) + (pragmatic × 0.2) + (entity_overlap × 0.2)

Phase 4 — Selection
  Return highest-scoring consistent mapping.
  Bin into AnalogyStrength based on similarity threshold.
```

### Knowledge Transfer

For each unmapped source relation where all arguments have target mappings:

```python
for source_rel in source.relations:
    if source_rel.predicate not in mapping.relation_map:
        mapped_args = tuple(mapping.entity_map.get(a) for a in source_rel.arguments)
        if all(a is not None for a in mapped_args):
            inferred = Relation(
                relation_type=source_rel.relation_type,
                predicate=f"inferred_{source_rel.predicate}",
                arguments=mapped_args,
                weight=source_rel.weight * mapping.similarity_score * 0.8,  # decay
                is_higher_order=source_rel.is_higher_order,
            )
            inferred_relations.append(inferred)
```

The **confidence decay** factor (0.8) ensures transferred knowledge is always less certain than directly observed knowledge.

### Classic Example: Solar System → Atom

```
Source (Solar System):
  Entities: {sun, planet, moon}
  Relations: gravity(sun, planet), orbits(planet, sun), massive(sun)

Target (Atom):
  Entities: {nucleus, electron}
  Relations: electrostatic(nucleus, electron), orbits(electron, nucleus)

Mapping:
  sun → nucleus, planet → electron
  gravity → electrostatic, orbits → orbits

Inferred:
  massive(nucleus) [transferred with 0.8 × similarity confidence]
```

### Similarity Scoring

```python
async def similarity(self, a: DomainStructure, b: DomainStructure) -> float:
    # Entity overlap (Jaccard on entity names is a surface heuristic)
    entity_score = len(a.entities & b.entities) / max(len(a.entities | b.entities), 1)
    
    # Relational overlap (match by RelationType)
    a_types = Counter(r.relation_type for r in a.relations)
    b_types = Counter(r.relation_type for r in b.relations)
    common = sum((a_types & b_types).values())
    total = sum((a_types | b_types).values())
    relational_score = common / max(total, 1)
    
    # Systematicity (count higher-order relations)
    a_ho = sum(1 for r in a.relations if r.is_higher_order)
    b_ho = sum(1 for r in b.relations if r.is_higher_order)
    systematicity = min(a_ho, b_ho) / max(max(a_ho, b_ho), 1)
    
    return (entity_score * 0.2) + (relational_score * 0.4) + (systematicity * 0.4)
```

---

## Null Implementation

```python
class NullAnalogicalReasoner:
    async def find_analogy(self, source, target) -> StructureMapping:
        return StructureMapping(
            source=source, target=target, entity_map={}, relation_map={},
            similarity_score=0.0, strength=AnalogyStrength.NONE, inferred_relations=(),
        )
    async def transfer_knowledge(self, mapping) -> tuple[Relation, ...]: return ()
    async def find_best_source(self, target, candidates) -> StructureMapping:
        return await self.find_analogy(candidates[0] if candidates else target, target)
    async def similarity(self, a, b) -> float: return 0.0
    async def get_mappings(self) -> tuple[StructureMapping, ...]: return ()
```

---

## Factory

```python
def make_analogical_reasoner(
    config: AnalogyConfig | None = None,
) -> AnalogicalReasoner:
    if config is None:
        return NullAnalogicalReasoner()
    return AsyncAnalogicalReasoner(config)
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `asi_analogy_query_total` | Counter | — | Total analogy queries |
| `asi_analogy_query_seconds` | Histogram | — | Query latency |
| `asi_analogy_similarity_score` | Histogram | — | Similarity score distribution |
| `asi_analogy_transfers_total` | Counter | — | Knowledge transfers executed |
| `asi_analogy_cached_mappings` | Gauge | — | Active cached mappings |

### PromQL Examples

```promql
# Average similarity score
rate(asi_analogy_similarity_score_sum[5m]) / rate(asi_analogy_similarity_score_count[5m])

# Transfer rate
rate(asi_analogy_transfers_total[5m])

# Cache hit ratio (if find_analogy checks cache first)
asi_analogy_cached_mappings
```

### Grafana Alerts

```yaml
- alert: AnalogySimilarityDrift
  expr: |
    (rate(asi_analogy_similarity_score_sum[10m]) / rate(asi_analogy_similarity_score_count[10m])) < 0.2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Average analogy similarity below 0.2 — poor source domain matches"

- alert: AnalogyHighLatency
  expr: histogram_quantile(0.99, rate(asi_analogy_query_seconds_bucket[5m])) > 2.0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Analogy P99 latency > 2s"
```

---

## Integration Map

### WorldModel 13.1 → Domain Structures

`WorldModel` provides `DomainStructure` objects derived from the world-state graph. Each observation cluster becomes a domain with entities (objects) and relations (observed interactions).

### CuriosityModule 13.3 → Novelty-Driven Analogy Search

When `CuriosityModule` detects a novel domain, it triggers `find_best_source()` to find the most structurally similar known domain, enabling rapid understanding of the new domain via analogical transfer.

### LogicalInferenceEngine 20.1 → Consistency Checking

Transferred relations are fed to the inference engine as "soft rules" with reduced confidence. The engine's contradiction detection ensures analogically inferred knowledge doesn't violate established logical constraints.

### KnowledgeFusion 20.3 → Knowledge Integration

Analogically transferred relations are submitted to `KnowledgeFusion` as candidate `KnowledgeAtom`s with `SourceTrust.MEDIUM`, enabling conflict detection against directly observed knowledge.

---

## mypy Strict Compliance

| Pattern | Technique |
|---|---|
| `DomainStructure.attributes` mutable dict | `field(default_factory=dict)` in frozen DC |
| `StructureMapping.entity_map` | `dict[str, str]` — fully typed |
| `Relation.arguments` | `tuple[str, ...]` — variadic but typed |
| Optional config | `AnalogyConfig \| None` with explicit check |
| `get_mappings()` return | `tuple[StructureMapping, ...]` not `list` |
| Protocol async methods | All fully annotated |

---

## Test Targets (12)

| # | Test | Validates |
|---|---|---|
| 1 | `test_find_analogy_basic_mapping` | Solar system → atom produces non-empty entity_map |
| 2 | `test_one_to_one_constraint` | No entity maps to two targets |
| 3 | `test_transfer_knowledge_creates_inferred` | Unmapped source relations produce inferred target relations |
| 4 | `test_confidence_decay_on_transfer` | Inferred relation weight < source relation weight |
| 5 | `test_find_best_source_selects_highest` | Best source has highest similarity |
| 6 | `test_similarity_identical_domains` | Same domain → similarity ≈ 1.0 |
| 7 | `test_similarity_disjoint_domains` | No overlap → similarity ≈ 0.0 |
| 8 | `test_systematicity_prefers_deep_chains` | Domain with higher-order relations scores higher |
| 9 | `test_min_similarity_returns_none_strength` | Below min_similarity → AnalogyStrength.NONE |
| 10 | `test_cached_mappings_returned` | After find_analogy, get_mappings() includes result |
| 11 | `test_null_reasoner_returns_zero` | NullAnalogicalReasoner returns similarity=0.0 |
| 12 | `test_concurrent_find_analogy_safe` | asyncio.gather 10 queries → no corruption |

---

## Implementation Order

1. Define `MappingConstraint`, `AnalogyStrength`, `RelationType` enums
2. Define `Relation` frozen dataclass
3. Define `DomainStructure` frozen dataclass
4. Define `StructureMapping` frozen dataclass
5. Define `AnalogyConfig` frozen dataclass
6. Define `AnalogicalReasoner` Protocol
7. Register 5 Prometheus metrics
8. Implement `AsyncAnalogicalReasoner.__init__` + cache
9. Implement predicate matching (Phase 1)
10. Implement entity mapping extension with one-to-one constraint (Phase 2)
11. Implement scoring with systematicity + pragmatic weights (Phase 3)
12. Implement `find_analogy()` with selection (Phase 4)
13. Implement `transfer_knowledge()` with confidence decay
14. Implement `find_best_source()` + `similarity()` + `get_mappings()`
15. Implement `NullAnalogicalReasoner`
16. Implement `make_analogical_reasoner()` factory
17. Write 12 tests
18. `mypy --strict`, `ruff`, green CI

---

## Phase 20 — Knowledge Synthesis & Reasoning — Sub-phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 20.1 | LogicalInferenceEngine | #484 | 🟡 Spec'd |
| **20.2** | **AnalogicalReasoner** | **#485** | **🟡 Spec'd** |
| 20.3 | KnowledgeFusion | #482 | 🟡 Spec'd |
| 20.4 | AbductiveReasoner | #483 | 🟡 Spec'd |
| 20.5 | ReasoningOrchestrator | #486 | 🟡 Spec'd |

---

*Tracking: #109 · Discussion: #481*
