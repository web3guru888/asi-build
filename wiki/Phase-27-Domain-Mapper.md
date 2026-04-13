# Phase 27.1 — DomainMapper

> Structural correspondence mapping between source and target domains.

## Overview

DomainMapper computes structural correspondences between domains using Gentner's Structure Mapping Theory (1983). It identifies relational isomorphisms — not surface similarity, but deep structural parallels that make knowledge transfer productive.

## Theoretical Foundation

| Concept | Source | Application |
|---------|--------|-------------|
| Structure Mapping | Gentner (1983) | Core mapping algorithm |
| Progressive Alignment | Gentner & Markman (1997) | Incremental match refinement |
| Systematicity Principle | Gentner (1983) | Prefer deep relational structure |
| Identical Elements | Thorndike (1901) | Transfer depends on shared structure |

## Data Model

### DomainSchema

```python
@dataclass(frozen=True, slots=True)
class DomainSchema:
    domain_id: str
    entities: frozenset[str]
    relations: frozenset[tuple[str, str, str]]  # (subject, predicate, object)
    constraints: frozenset[str]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    embedding: tuple[float, ...] | None = None
```

### DomainMapping

```python
@dataclass(frozen=True, slots=True)
class DomainMapping:
    source: DomainSchema
    target: DomainSchema
    entity_map: Mapping[str, str]
    relation_map: Mapping[str, str]
    confidence: float              # [0.0, 1.0]
    structural_score: float        # systematicity score
    transferred_inferences: tuple[str, ...] = ()
    unmapped_source: frozenset[str] = frozenset()
    unmapped_target: frozenset[str] = frozenset()
```

## Protocol

```python
@runtime_checkable
class DomainMapper(Protocol):
    async def map_domains(self, source: DomainSchema, target: DomainSchema) -> DomainMapping: ...
    async def evaluate_mapping(self, mapping: DomainMapping) -> float: ...
    async def find_analogous_domains(self, target: DomainSchema, candidates: Sequence[DomainSchema], top_k: int = 5) -> Sequence[DomainMapping]: ...
    async def transfer_knowledge(self, mapping: DomainMapping) -> Sequence[str]: ...
```

## Implementation: StructuralDomainMapper

### Progressive Alignment Algorithm

```
Source Relations ──▶ Local Match ──▶ Consistent Merge ──▶ Systematicity Score ──▶ Best Mapping
                     (predicate       (one-to-one         (depth-weighted        (highest SCR)
                      similarity)      constraint)         scoring)
```

**Phase 1** — Local match generation: Compare all source-target relation pairs by predicate similarity. Threshold: 0.3.

**Phase 2** — Consistent merge: Greedy combination maintaining one-to-one entity constraint. Sort matches by similarity descending; add each match if consistent with existing assignments.

**Phase 3** — Systematicity scoring: `score = Σ(similarity_i × depth_i^1.5)`. Higher-order relations (relations between relations) receive super-linear bonus.

### Transfer Inference

Unmapped source relations are projected through the entity mapping onto the target domain. These candidate inferences represent knowledge the source domain has that may apply to the target.

## Data Flow

```
AnalogicalReasoner (20.2) ──▶ DomainMapper (27.1) ──▶ AbstractionEngine (27.2)
       │                            │                         │
ConceptGraph (26.1) ──────▶ DomainSchema           KnowledgeFusion (20.3)
  entities + relations        extraction             cross-domain merge
```

## Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_domain_mapper_mappings_total` | Counter | Total mappings computed |
| `asi_domain_mapper_mapping_duration_seconds` | Histogram | Time per mapping |
| `asi_domain_mapper_structural_score` | Histogram | Score distribution |
| `asi_domain_mapper_cache_hits_total` | Counter | Cache hits |
| `asi_domain_mapper_transfer_inferences_total` | Counter | Inferences transferred |

## Test Targets (12)

1. `test_domain_schema_immutability`
2. `test_domain_mapping_confidence_bounds`
3. `test_map_identical_domains_perfect_score`
4. `test_map_disjoint_domains_zero_score`
5. `test_progressive_alignment_one_to_one`
6. `test_systematicity_prefers_deep_relations`
7. `test_transfer_knowledge_projects_unmapped`
8. `test_find_analogous_domains_top_k`
9. `test_mapping_cache_hit`
10. `test_null_mapper_returns_defaults`
11. `test_factory_structural`
12. `test_factory_unknown_raises`

## Phase 27 Sub-phase Tracker

| # | Component | Issue | Wiki | Status |
|---|-----------|-------|------|--------|
| 27.1 | DomainMapper | [#594](https://github.com/web3guru888/asi-build/issues/594) | [[Phase-27-Domain-Mapper]] | ✅ Spec'd |
| 27.2 | AbstractionEngine | [#595](https://github.com/web3guru888/asi-build/issues/595) | [[Phase-27-Abstraction-Engine]] | ✅ Spec'd |
| 27.3 | FewShotAdapter | [#596](https://github.com/web3guru888/asi-build/issues/596) | [[Phase-27-Few-Shot-Adapter]] | ✅ Spec'd |
| 27.4 | CurriculumDesigner | [#597](https://github.com/web3guru888/asi-build/issues/597) | [[Phase-27-Curriculum-Designer]] | ✅ Spec'd |
| 27.5 | GeneralizationOrchestrator | [#598](https://github.com/web3guru888/asi-build/issues/598) | [[Phase-27-Generalization-Orchestrator]] | ✅ Spec'd |

---
*Issue: [#594](https://github.com/web3guru888/asi-build/issues/594) | S&T: [#599](https://github.com/web3guru888/asi-build/discussions/599) | Q&A: [#600](https://github.com/web3guru888/asi-build/discussions/600) | Planning: [#593](https://github.com/web3guru888/asi-build/discussions/593)*
