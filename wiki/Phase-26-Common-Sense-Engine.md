# Phase 26.4 — CommonSenseEngine: Common-Sense Knowledge & Plausibility Reasoning

> **Issue**: [#581](https://github.com/web3guru888/asi-build/issues/581) | **S&T**: [#589](https://github.com/web3guru888/asi-build/discussions/589) | **Q&A**: [#590](https://github.com/web3guru888/asi-build/discussions/590) | **Planning**: [#577](https://github.com/web3guru888/asi-build/discussions/577)

## Overview

`CommonSenseEngine` provides common-sense knowledge and reasoning capabilities. Implements ConceptNet-style relational knowledge (Liu & Singh 2004), qualitative physics (Hayes 1985), naive psychology (Schank & Abelson 1977), and plausibility-based inference (Collins & Michalski 1989).

## Theoretical Background

### ConceptNet (Liu & Singh 2004)
A crowd-sourced common-sense knowledge graph with ~21 million assertions and 34 relation types. Enables inference by path-finding and analogy.

### Scripts (Schank & Abelson 1977)
Stereotyped event sequences (e.g., restaurant script: enter → sit → order → eat → pay → leave). Used to generate expectations and detect violations.

### Plausible Reasoning (Collins & Michalski 1989)
Reasoning under uncertainty using certainty of premises, typicality of instances, similarity of domains, and frequency of association.

## Data Structures

### CommonSenseRelation Enum (14 types)

| Relation | Example | Category |
|----------|---------|----------|
| `IsA` | "cat IsA animal" | Taxonomic |
| `HasProperty` | "fire HasProperty hot" | Attribute |
| `CapableOf` | "bird CapableOf fly" | Ability |
| `UsedFor` | "knife UsedFor cut" | Function |
| `AtLocation` | "book AtLocation library" | Spatial |
| `Causes` | "rain Causes wet" | Causal |
| `HasPrerequisite` | "cook HasPrerequisite ingredients" | Precondition |
| `HasEffect` | "exercise HasEffect healthy" | Consequence |
| `MotivatedByGoal` | "study MotivatedByGoal learn" | Psychology |
| `Desires` | "human Desires happiness" | Agent goals |
| `CreatedBy` | "bread CreatedBy baking" | Origin |
| `MadeOf` | "table MadeOf wood" | Composition |
| `ReceivesAction` | "ball ReceivesAction kick" | Patient role |
| `DistinctFrom` | "cat DistinctFrom dog" | Negative |

### CommonSenseAssertion Frozen Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `assertion_id` | `str` | Unique identifier |
| `subject` | `str` | Source concept |
| `relation` | `CommonSenseRelation` | Relation type |
| `object` | `str` | Target concept |
| `confidence` | `float` | [0, 1] assertion confidence |
| `source` | `str` | Provenance |
| `context` | `Optional[str]` | Situational qualifier |
| `weight` | `float` | ConceptNet-style weight |

### PlausibilityScore Frozen Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `score` | `float` | [-1, 1] plausible to implausible |
| `supporting_assertions` | `Tuple[str, ...]` | Supporting evidence |
| `contradicting_assertions` | `Tuple[str, ...]` | Contradicting evidence |
| `confidence` | `float` | Meta-confidence |
| `reasoning_chain` | `Tuple[str, ...]` | Explanation steps |

### ExpectationFrame Frozen Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `frame_id` | `str` | Unique identifier |
| `context` | `str` | Situation description |
| `expected_events` | `Tuple[str, ...]` | Expected event sequence |
| `expected_properties` | `FrozenSet[str]` | Expected attributes |
| `violation_threshold` | `float` | Surprise threshold (default 0.3) |

## Protocol

```python
@runtime_checkable
class CommonSenseEngine(Protocol):
    async def query(self, subject: str, relation: CommonSenseRelation,
                    limit: int = 10) -> Tuple[CommonSenseAssertion, ...]: ...
    async def infer(self, subject: str, relation: CommonSenseRelation,
                    max_hops: int = 3) -> Tuple[CommonSenseAssertion, ...]: ...
    async def validate_plausibility(self, statement: str) -> PlausibilityScore: ...
    async def generate_expectations(self, context: str) -> ExpectationFrame: ...
    async def explain(self, subject: str, object: str) -> Tuple[str, ...]: ...
    async def add_assertion(self, assertion: CommonSenseAssertion) -> None: ...
    async def get_related(self, concept: str, limit: int = 20) -> Tuple[CommonSenseAssertion, ...]: ...
```

## Implementation: HybridCommonSenseEngine

### Triple Indexing
```python
self._by_subject: dict[str, list[CommonSenseAssertion]]
self._by_relation: dict[CommonSenseRelation, list[CommonSenseAssertion]]
self._by_object: dict[str, list[CommonSenseAssertion]]
```

### Three-Signal Plausibility Scoring

```
Statement → Parse (subject, relation, object)
    │
    ├── Direct Evidence (weight 0.40)
    │   KB lookup: matching/contradicting assertions
    │
    ├── Analogical Transfer (weight 0.35)
    │   ConceptGraph similarity → transfer from similar concepts
    │
    └── Script Consistency (weight 0.25)
        ExpectationFrame → check against expected properties/events
    │
    ▼
Weighted Average → PlausibilityScore
```

### Multi-hop Inference
BFS over assertion graph with confidence decay: `conf_chain = ∏ conf_i × 0.85^hop`. Follows CAUSES/HAS_EFFECT/HAS_PREREQUISITE chains for transitive reasoning.

### Context-Aware Resolution
Assertions with matching context are preferred over universal (null-context) assertions, inspired by Cyc's microtheory approach.

## Metrics (Prometheus)

| Metric | Type | Description |
|--------|------|-------------|
| `common_sense_assertions_total` | Gauge | Total assertions |
| `common_sense_query_seconds` | Histogram | Query latency |
| `common_sense_inference_hops` | Histogram | Hops per inference |
| `common_sense_plausibility_score` | Histogram | Score distribution |
| `common_sense_expectations_generated_total` | Counter | Frames generated |

## Integration Points

- **ConceptGraph (26.1)**: Similarity for analogical transfer
- **AnalogicalReasoner (20.2)**: Structured analogy enriches inference
- **WorldModel (13.1)**: Entity grounding for assertions
- **SurpriseDetector (13.4)**: Expectation violations → surprise signals

## References

- Liu, H. & Singh, P. (2004). *ConceptNet*
- Lenat, D.B. (1995). *CYC*
- Schank, R.C. & Abelson, R.P. (1977). *Scripts, Plans, Goals, and Understanding*
- Collins, A. & Michalski, R. (1989). *The logic of plausible reasoning*
- Hayes, P.J. (1985). *The second naive physics manifesto*

---

## Phase 26 Sub-phase Tracker

| # | Component | Issue | Status |
|---|-----------|-------|--------|
| 26.1 | ConceptGraph | #578 | ✅ Spec'd |
| 26.2 | OntologyManager | #579 | ✅ Spec'd |
| 26.3 | KnowledgeCompiler | #580 | ✅ Spec'd |
| 26.4 | CommonSenseEngine | #581 | ✅ Spec'd |
| 26.5 | KnowledgeOrchestrator | #582 | ✅ Spec'd |
