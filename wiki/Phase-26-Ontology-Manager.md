# Phase 26.2 — OntologyManager: Formal Ontology & Description Logic Reasoning

> **Issue**: [#579](https://github.com/web3guru888/asi-build/issues/579) | **S&T**: [#585](https://github.com/web3guru888/asi-build/discussions/585) | **Q&A**: [#586](https://github.com/web3guru888/asi-build/discussions/586) | **Planning**: [#577](https://github.com/web3guru888/asi-build/discussions/577)

## Overview

`OntologyManager` provides formal ontology creation and management with OWL-style class definitions, property restrictions, consistency checking, and Description Logic (DL) reasoning. Implements tableau-based reasoning (Baader et al. 2003), formal ontology principles (Gruber 1993), and conceptual graph foundations (Sowa 1984).

## Theoretical Background

### Description Logic (Baader et al. 2003)
Description Logics are decidable fragments of first-order logic designed for knowledge representation. They provide formal guarantees (soundness, completeness, termination) that pure FOL cannot.

### TBox / ABox Separation
- **TBox** (Terminological Box): Class definitions, axioms, restrictions — the schema
- **ABox** (Assertional Box): Individual assertions — the data
- This separation allows schema changes (reclassification) to be decoupled from data changes (realization)

### Tableau Algorithm
Subsumption testing via negation: C ⊑ D iff C ⊓ ¬D is unsatisfiable. The tableau expands the concept expression using completion rules until either a clash is found (subsumption holds) or a model is constructed (counter-example exists).

## Data Structures

### RestrictionType Enum

| Value | DL Syntax | OWL Construct |
|-------|-----------|---------------|
| `ALL_VALUES_FROM` | ∀R.C | `owl:allValuesFrom` |
| `SOME_VALUES_FROM` | ∃R.C | `owl:someValuesFrom` |
| `HAS_VALUE` | ∃R.{a} | `owl:hasValue` |
| `MIN_CARDINALITY` | ≥n R.C | `owl:minCardinality` |
| `MAX_CARDINALITY` | ≤n R.C | `owl:maxCardinality` |
| `EXACT_CARDINALITY` | =n R.C | `owl:cardinality` |

### OntologyClass Frozen Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `class_id` | `str` | Unique class identifier |
| `label` | `str` | Human-readable name |
| `superclasses` | `FrozenSet[str]` | Direct parent classes |
| `properties` | `FrozenSet[str]` | Declared properties |
| `restrictions` | `Tuple[PropertyRestriction, ...]` | Property restrictions |
| `axioms` | `Tuple[OntologyAxiom, ...]` | Associated axioms |
| `is_primitive` | `bool` | Primitive vs defined class |

### Individual Frozen Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `individual_id` | `str` | Unique identifier |
| `class_assertions` | `FrozenSet[str]` | Asserted class memberships |
| `property_assertions` | `Tuple[Tuple[str, str], ...]` | (property, value) pairs |

## Protocol

```python
@runtime_checkable
class OntologyManager(Protocol):
    async def define_class(self, cls: OntologyClass) -> None: ...
    async def add_individual(self, ind: Individual) -> None: ...
    async def add_axiom(self, axiom: OntologyAxiom) -> None: ...
    async def check_consistency(self) -> bool: ...
    async def classify(self) -> Dict[str, FrozenSet[str]]: ...
    async def realize(self, individual_id: str) -> FrozenSet[str]: ...
    async def is_subclass(self, sub: str, sup: str) -> bool: ...
    async def get_instances(self, class_id: str, direct: bool = False) -> Set[str]: ...
    async def query_restrictions(self, class_id: str) -> Tuple[PropertyRestriction, ...]: ...
    async def explain_subsumption(self, sub: str, sup: str) -> List[str]: ...
```

## Implementation: DLOntologyManager

### Tableau Completion Rules

| Rule | Trigger | Action |
|------|---------|--------|
| ⊓-rule | `a: C ⊓ D` | Add `a: C` and `a: D` |
| ⊔-rule | `a: C ⊔ D` | Branch: try `a: C`, if clash try `a: D` |
| ∃-rule | `a: ∃R.C` | Create fresh `b`, add `(a,b): R` and `b: C` |
| ∀-rule | `a: ∀R.C` and `(a,b): R` | Add `b: C` |
| ≥n-rule | `a: ≥n R.C` | Create n fresh R-successors typed C |
| ≤n-rule | `a: ≤n R.C` and \|R-succ\| > n | Merge successors |

### Classification Flow

```
Top (⊤)
    │
    ▼
Enhanced Traversal
(top-down with known subsumers)
    │
    ▼
Pairwise Subsumption Tests
(with caching + told subsumer optimization)
    │
    ▼
Complete Hierarchy
    │
    ▼
Cache Results
```

### Consistency Checking

1. Check TBox: No unsatisfiable class definitions
2. Check ABox: No individual in both C and ¬C (disjoint clash)
3. Check restrictions: All property restrictions satisfied

## Metrics (Prometheus)

| Metric | Type | Description |
|--------|------|-------------|
| `ontology_classes_total` | Gauge | Total classes in TBox |
| `ontology_individuals_total` | Gauge | Total individuals in ABox |
| `ontology_axioms_total` | Gauge | Total axioms |
| `ontology_reasoning_seconds` | Histogram | Reasoning latency |
| `ontology_consistency_checks_total` | Counter | Consistency checks |

## Integration Points

- **ConceptGraph (26.1)**: Formalizes concept relations into DL axioms
- **LogicalInferenceEngine (20.1)**: DL reasoning delegation
- **SemanticParser (19.1)**: Parsed sentences instantiate ABox individuals
- **KnowledgeCompiler (26.3)**: Axioms feed compilation

## Test Targets (12)

1–12: See issue #579 for full list.

## References

- Gruber, T.R. (1993). *A translation approach to portable ontology specifications*
- Sowa, J.F. (1984). *Conceptual Structures*
- Baader, F. et al. (2003). *The Description Logic Handbook*
- Horrocks, I. et al. (2003). *From SHIQ and RDF to OWL*
- Motik, B. et al. (2009). *OWL 2 Web Ontology Language*

---

## Phase 26 Sub-phase Tracker

| # | Component | Issue | Status |
|---|-----------|-------|--------|
| 26.1 | ConceptGraph | #578 | ✅ Spec'd |
| 26.2 | OntologyManager | #579 | ✅ Spec'd |
| 26.3 | KnowledgeCompiler | #580 | ✅ Spec'd |
| 26.4 | CommonSenseEngine | #581 | ✅ Spec'd |
| 26.5 | KnowledgeOrchestrator | #582 | ✅ Spec'd |
