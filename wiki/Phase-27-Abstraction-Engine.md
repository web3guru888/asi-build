# Phase 27.2 — AbstractionEngine

> Hierarchical abstraction and schema induction for transfer learning.

## Overview

AbstractionEngine builds and navigates abstraction hierarchies, enabling the system to operate at the right level of generality for knowledge transfer. It extracts principles from instances, induces schemas from categories, and finds the optimal abstraction level using information-theoretic criteria.

## Theoretical Foundation

| Concept | Source | Application |
|---------|--------|-------------|
| Perceptual Symbol Systems | Barsalou (1999) | Abstraction as selective attention |
| Image Schemas | Lakoff (1987) | Recurring embodied patterns |
| Expert/Novice Differences | Chi et al. (1981) | Abstraction level distinguishes expertise |
| Minimum Description Length | Rissanen (1978) | Optimal level selection |
| Anti-Unification | Plotkin (1970) | Least general generalization |

## Data Model

### AbstractionLevel

```python
class AbstractionLevel(IntEnum):
    INSTANCE = 0      # "my cat Whiskers"
    CATEGORY = 1      # "cats"
    PRINCIPLE = 2     # "predator-prey dynamics"
    SCHEMA = 3        # "resource competition"
    META_SCHEMA = 4   # "optimization under constraints"
```

### AbstractionNode

```python
@dataclass(frozen=True, slots=True)
class AbstractionNode:
    node_id: str
    level: AbstractionLevel
    content: str
    generalizations: frozenset[str] = frozenset()  # parent IDs
    specializations: frozenset[str] = frozenset()   # child IDs
    coverage: float = 0.0
    exemplars: tuple[str, ...] = ()
    constraints: frozenset[str] = frozenset()
```

### AbstractionHierarchy

```python
@dataclass(frozen=True, slots=True)
class AbstractionHierarchy:
    root_id: str
    nodes: Mapping[str, AbstractionNode]
    depth: int
    domain_id: str | None = None
```

## Protocol

```python
@runtime_checkable
class AbstractionEngine(Protocol):
    async def abstract(self, instances: Sequence[str], target_level: AbstractionLevel) -> AbstractionNode: ...
    async def specialize(self, node: AbstractionNode, context: Mapping[str, Any] | None = None) -> Sequence[AbstractionNode]: ...
    async def find_level(self, content: str, hierarchy: AbstractionHierarchy) -> AbstractionLevel: ...
    async def induce_schema(self, examples: Sequence[AbstractionNode]) -> AbstractionNode: ...
    async def get_hierarchy(self, domain_id: str) -> AbstractionHierarchy: ...
```

## Implementation: HierarchicalAbstractionEngine

### Bottom-Up Induction

```
Instances ──▶ Cluster ──▶ Extract Invariants ──▶ Generalize ──▶ AbstractionNode
```

1. Cluster instances by relational similarity (agglomerative)
2. Extract shared relations as structural invariants
3. Progressively generalize to target abstraction level
4. Wrap in AbstractionNode with coverage and exemplars

### Schema Induction via Anti-Unification

Anti-unification finds the **least general generalization** that subsumes all examples:

| Example 1 | Example 2 | Anti-Unification |
|-----------|-----------|-----------------|
| `loves(romeo, juliet)` | `loves(tristan, isolde)` | `loves(X, Y)` |
| `bigger(elephant, mouse)` | `bigger(whale, fish)` | `bigger(X, Y)` |

The induced schema captures structural invariants while abstracting over specific entities.

### MDL Level Selection

The optimal level minimizes `model_cost + data_cost`:
- **Model cost**: increases with abstraction (more parameters for schema)
- **Data cost**: decreases with abstraction (fewer bits to encode instances)
- **Optimal**: the level where the sum is minimized

## Integration

```
ConceptGraph (26.1) ──▶ AbstractionEngine (27.2) ──▶ FewShotAdapter (27.3)
KnowledgeCompiler (26.3) ──▶ schema induction input
CreativeOrchestrator (22.5) ──▶ conceptual blending at higher levels
DomainMapper (27.1) ──▶ mapping granularity selection
```

## Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_abstraction_operations_total` | Counter | Total operations |
| `asi_abstraction_duration_seconds` | Histogram | Time per operation |
| `asi_abstraction_hierarchy_depth` | Gauge | Max hierarchy depth |
| `asi_abstraction_schema_inductions_total` | Counter | Schemas induced |
| `asi_abstraction_level_distribution` | Histogram | Level distribution |

## Test Targets (12)

1. `test_abstraction_level_ordering`
2. `test_abstraction_node_immutability`
3. `test_abstract_instances_to_category`
4. `test_abstract_categories_to_principle`
5. `test_specialize_schema_to_instances`
6. `test_find_level_selects_optimal`
7. `test_induce_schema_anti_unification`
8. `test_hierarchy_traversal_up_down`
9. `test_mdl_prefers_compact_representation`
10. `test_null_engine_returns_defaults`
11. `test_factory_hierarchical`
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
*Issue: [#595](https://github.com/web3guru888/asi-build/issues/595) | S&T: [#601](https://github.com/web3guru888/asi-build/discussions/601) | Q&A: [#602](https://github.com/web3guru888/asi-build/discussions/602) | Planning: [#593](https://github.com/web3guru888/asi-build/discussions/593)*
