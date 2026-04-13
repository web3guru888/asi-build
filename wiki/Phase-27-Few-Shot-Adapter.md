# Phase 27.3 — FewShotAdapter

> Meta-learning and rapid task adaptation from minimal examples.

## Overview

FewShotAdapter enables rapid adaptation to new tasks and domains from as few as 1–5 examples. It leverages meta-learned representations and prototype-based reasoning to achieve data-efficient learning — the "learning to learn" capability.

## Theoretical Foundation

| Concept | Source | Application |
|---------|--------|-------------|
| MAML | Finn et al. (2017) | Learn initialization easy to fine-tune |
| Prototypical Networks | Snell et al. (2017) | Classify by distance to class prototypes |
| Matching Networks | Vinyals et al. (2016) | Attention over support set |
| Meta-Learning | Schmidhuber (1987) | Learning the learning algorithm |

## Data Model

### TaskEmbedding

```python
@dataclass(frozen=True, slots=True)
class TaskEmbedding:
    task_id: str
    embedding: tuple[float, ...]
    support_set: tuple[str, ...]
    query_set: tuple[str, ...] = ()
    domain: str | None = None
    difficulty: float = 0.5
    similarity_to_known: float = 0.0
```

### AdaptationResult

```python
@dataclass(frozen=True, slots=True)
class AdaptationResult:
    task_id: str
    adapted_params: Mapping[str, Any]
    performance: float          # [0.0, 1.0]
    shots_used: int
    confidence: float           # [0.0, 1.0]
    adaptation_time_ms: float
    transfer_source: str | None = None
    abstraction_level: str | None = None
```

## Protocol

```python
@runtime_checkable
class FewShotAdapter(Protocol):
    async def adapt(self, task: TaskEmbedding, max_shots: int = 5) -> AdaptationResult: ...
    async def evaluate(self, result: AdaptationResult, test_instances: Sequence[str]) -> float: ...
    async def get_task_embedding(self, task_description: str, examples: Sequence[str]) -> TaskEmbedding: ...
    async def select_support_set(self, task: TaskEmbedding, candidates: Sequence[str], k: int = 5) -> Sequence[str]: ...
```

## Implementation: MetaFewShotAdapter

### Gradient-Free Meta-Adaptation Pipeline

```
Task ──▶ Embed ──▶ Find Prototypes ──▶ Fast Weights ──▶ Refine ──▶ Result
              │         │                    │              │
         compositional  nearest           softmax       online
         encoding      neighbor           weighted      centroid
                       retrieval          combination    update
```

1. **Embed task**: Compositional encoding from description + examples + domain
2. **Retrieve prototypes**: k-nearest neighbors from meta-knowledge base
3. **Compute fast weights**: Softmax-normalized similarity-weighted parameter combination
4. **Refine on support**: Online centroid update on support examples (no backprop)
5. **Evaluate**: Score on query set, update meta-knowledge if performance exceeds threshold

### Support Set Selection

Maximum diversity + relevance via greedy DPP approximation:
1. Filter candidates by relevance threshold (≥ 0.3)
2. Select most relevant candidate first
3. Iteratively add candidate maximizing `relevance × min_distance_to_selected`
4. Stop at k examples

### Meta-Knowledge Base

Grows as system encounters new tasks. Prototypes with performance > threshold are stored. MemoryConsolidator (18.2) periodically merges similar prototypes (similarity > 0.95) to prevent unbounded growth.

## Integration

```
DomainMapper (27.1) ──▶ which prototypes are relevant
AbstractionEngine (27.2) ──▶ adaptation granularity
MemoryConsolidator (18.2) ──▶ prototype consolidation
CurriculumDesigner (27.4) ──▶ difficulty calibration from results
```

## Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_few_shot_adaptations_total` | Counter | Total adaptations |
| `asi_few_shot_adaptation_duration_seconds` | Histogram | Time per adaptation |
| `asi_few_shot_performance` | Histogram | Post-adaptation performance |
| `asi_few_shot_shots_used` | Histogram | Examples consumed |
| `asi_few_shot_meta_knowledge_size` | Gauge | Prototype count |

## Test Targets (12)

1. `test_task_embedding_immutability`
2. `test_adaptation_result_bounds`
3. `test_adapt_known_task_high_performance`
4. `test_adapt_novel_task_uses_prototypes`
5. `test_adapt_respects_max_shots`
6. `test_select_support_set_diversity`
7. `test_get_task_embedding_deterministic`
8. `test_evaluate_on_test_instances`
9. `test_meta_knowledge_grows_on_success`
10. `test_null_adapter_returns_defaults`
11. `test_factory_meta`
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
*Issue: [#596](https://github.com/web3guru888/asi-build/issues/596) | S&T: [#603](https://github.com/web3guru888/asi-build/discussions/603) | Q&A: [#604](https://github.com/web3guru888/asi-build/discussions/604) | Planning: [#593](https://github.com/web3guru888/asi-build/discussions/593)*
