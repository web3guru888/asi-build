# Phase 27.5 — GeneralizationOrchestrator

> Unified transfer learning and cross-domain generalization pipeline.

## Overview

GeneralizationOrchestrator is the capstone of Phase 27 — a unified 5-stage pipeline that coordinates domain mapping, abstraction, few-shot adaptation, and curriculum design for systematic cross-domain knowledge transfer. It includes negative transfer detection and rollback safety.

## Theoretical Foundation

| Concept | Source | Application |
|---------|--------|-------------|
| Building Machines That Learn Like People | Lake et al. (2017) | Compositionality + learning-to-learn |
| Systematic Generalization | Marcus (2018) | Structured representations for transfer |
| Abstraction and Reasoning Corpus | Chollet (2019) | Measuring skill-acquisition efficiency |
| Transfer Learning Taxonomy | Ruder (2019) | Pre-training, multi-task, domain adaptation |

## Data Model

### TransferPlan

```python
@dataclass(frozen=True, slots=True)
class TransferPlan:
    plan_id: str
    source_domains: tuple[str, ...]
    target_domain: str
    mapping_strategy: str          # "structural" | "embedding" | "hybrid"
    abstraction_level: str
    adaptation_budget: int         # max few-shot examples
    curriculum_objectives: tuple[str, ...] = ()
    estimated_transferability: float = 0.0
```

### TransferResult

```python
@dataclass(frozen=True, slots=True)
class TransferResult:
    plan_id: str
    success: bool
    performance_before: float
    performance_after: float
    transfer_gain: float           # after - before
    negative_transfer_detected: bool = False
    mappings_used: int = 0
    abstractions_formed: int = 0
    shots_consumed: int = 0
    total_duration_ms: float = 0.0
```

### TransferContext

```python
@dataclass(frozen=True, slots=True)
class TransferContext:
    source_domains: tuple[DomainSchema, ...]
    target_domain: DomainSchema
    mappings: tuple[DomainMapping, ...] = ()
    abstractions: tuple[AbstractionNode, ...] = ()
    adaptations: tuple[AdaptationResult, ...] = ()
    curriculum: Curriculum | None = None
    active_plan: TransferPlan | None = None
```

## Protocol

```python
@runtime_checkable
class GeneralizationOrchestrator(Protocol):
    async def plan_transfer(self, source_domains: Sequence[DomainSchema], target: DomainSchema) -> TransferPlan: ...
    async def execute_transfer(self, plan: TransferPlan) -> TransferResult: ...
    async def evaluate_generalization(self, result: TransferResult, test_tasks: Sequence[str]) -> float: ...
    async def get_transfer_context(self) -> TransferContext: ...
```

## Implementation: AsyncGeneralizationOrchestrator

### 5-Stage Systematic Transfer Protocol

```
┌────────┐    ┌────────┐    ┌──────────┐    ┌────────┐    ┌────────┐
│ 1.PLAN │──▶│ 2.MAP  │──▶│ 3.ABSTR. │──▶│ 4.ADAPT│──▶│ 5.VERI.│
│        │    │        │    │          │    │        │    │        │
│assess  │    │struct. │    │lift to   │    │fast    │    │test set│
│similar.│    │mapping │    │optimal   │    │weights │    │eval    │
│select  │    │filter  │    │level     │    │refine  │    │neg.    │
│level   │    │merge   │    │induce    │    │iterate │    │transfer│
│estimate│    │        │    │schemas   │    │        │    │check   │
└────────┘    └────────┘    └──────────┘    └────────┘    └────────┘
```

### Transferability Score

Multi-factor assessment: `0.4 × structural_overlap + 0.3 × abstraction_compatibility + 0.3 × (1 - domain_distance)`

### Negative Transfer Guard

If post-transfer performance drops below baseline - ε (default: 0.05):
1. Halt transfer immediately
2. Rollback to pre-transfer parameters
3. Increment `negative_transfer_detections_total`
4. Add source-target pair to blacklist
5. Log for offline analysis

### Mapping Merge Strategy

Multiple source→target mappings merged by confidence ranking. Highest-confidence mapping wins entity/relation conflicts. Inferences deduplicated.

## Composition

```python
AsyncGeneralizationOrchestrator(
    mapper: DomainMapper,          # 27.1
    abstraction: AbstractionEngine, # 27.2
    adapter: FewShotAdapter,       # 27.3
    curriculum: CurriculumDesigner, # 27.4
)
```

## Integration

```
KnowledgeOrchestrator (26.5) ──▶ domain schema source
EmbodiedOrchestrator (25.5) ──▶ sensorimotor skill transfer
DecisionOrchestrator (23.5) ──▶ decision strategy transfer
```

## Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_transfer_attempts_total` | Counter | Transfer attempts |
| `asi_transfer_success_total` | Counter | Successful transfers |
| `asi_transfer_gain` | Histogram | Transfer gain distribution |
| `asi_transfer_duration_seconds` | Histogram | Pipeline duration |
| `asi_negative_transfer_detections_total` | Counter | Negative transfers |
| `asi_transfer_pipeline_stage` | Gauge | Current stage (1-5) |

## Test Targets (12)

1. `test_transfer_plan_immutability`
2. `test_transfer_result_gain_calculation`
3. `test_plan_transfer_selects_best_sources`
4. `test_execute_transfer_full_pipeline`
5. `test_negative_transfer_detection_halts`
6. `test_evaluate_generalization_on_held_out`
7. `test_get_transfer_context_reflects_state`
8. `test_merge_mappings_consistency`
9. `test_iterative_curriculum_loop`
10. `test_null_orchestrator_returns_defaults`
11. `test_factory_with_all_components`
12. `test_factory_all_none_returns_null`

## Phase 27 Sub-phase Tracker

| # | Component | Issue | Wiki | Status |
|---|-----------|-------|------|--------|
| 27.1 | DomainMapper | [#594](https://github.com/web3guru888/asi-build/issues/594) | [[Phase-27-Domain-Mapper]] | ✅ Spec'd |
| 27.2 | AbstractionEngine | [#595](https://github.com/web3guru888/asi-build/issues/595) | [[Phase-27-Abstraction-Engine]] | ✅ Spec'd |
| 27.3 | FewShotAdapter | [#596](https://github.com/web3guru888/asi-build/issues/596) | [[Phase-27-Few-Shot-Adapter]] | ✅ Spec'd |
| 27.4 | CurriculumDesigner | [#597](https://github.com/web3guru888/asi-build/issues/597) | [[Phase-27-Curriculum-Designer]] | ✅ Spec'd |
| 27.5 | GeneralizationOrchestrator | [#598](https://github.com/web3guru888/asi-build/issues/598) | [[Phase-27-Generalization-Orchestrator]] | ✅ Spec'd |

---
*Issue: [#598](https://github.com/web3guru888/asi-build/issues/598) | S&T: [#607](https://github.com/web3guru888/asi-build/discussions/607) | Q&A: [#608](https://github.com/web3guru888/asi-build/discussions/608) | Planning: [#593](https://github.com/web3guru888/asi-build/discussions/593)*
