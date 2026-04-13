# Phase 27.4 — CurriculumDesigner

> Adaptive learning curriculum generation with prerequisite management.

## Overview

CurriculumDesigner generates optimal learning curricula — ordered sequences of learning objectives that maximize knowledge acquisition while respecting prerequisite dependencies and targeting the learner's Zone of Proximal Development.

## Theoretical Foundation

| Concept | Source | Application |
|---------|--------|-------------|
| Zone of Proximal Development | Vygotsky (1978) | Target learning at capability boundary |
| Curriculum Learning | Bengio et al. (2009) | Easy-to-hard ordering improves generalization |
| Starting Small | Elman (1993) | Staged complexity exposure |
| Mastery Learning | Bloom (1968) | 80% threshold for advancement |
| Self-Paced Learning | Kumar et al. (2010) | Learner-adaptive difficulty |

## Data Model

### LearningObjective

```python
@dataclass(frozen=True, slots=True)
class LearningObjective:
    objective_id: str
    description: str
    prerequisites: frozenset[str] = frozenset()
    difficulty: float = 0.5          # [0, 1]
    domain: str | None = None
    skills: frozenset[str] = frozenset()
    estimated_duration_ms: float = 0.0
```

### MasteryRecord

```python
@dataclass(frozen=True, slots=True)
class MasteryRecord:
    objective_id: str
    mastery_score: float    # [0.0, 1.0]
    attempts: int
    last_assessed: float    # timestamp
    trend: float = 0.0     # positive = improving
```

### Curriculum

```python
@dataclass(frozen=True, slots=True)
class Curriculum:
    curriculum_id: str
    objectives_ordered: tuple[str, ...]  # topologically sorted
    current_position: int = 0
    mastery_scores: Mapping[str, float] = field(default_factory=dict)
    adaptation_rate: float = 0.1
    mastery_threshold: float = 0.8
    domain: str | None = None
```

## Protocol

```python
@runtime_checkable
class CurriculumDesigner(Protocol):
    async def design_curriculum(self, objectives: Sequence[LearningObjective], learner_state: Mapping[str, float] | None = None) -> Curriculum: ...
    async def assess_mastery(self, curriculum: Curriculum, objective_id: str, performance: float) -> MasteryRecord: ...
    async def adapt_difficulty(self, curriculum: Curriculum, recent_performance: Sequence[float]) -> Curriculum: ...
    async def get_next_objective(self, curriculum: Curriculum) -> LearningObjective | None: ...
    async def evaluate_progress(self, curriculum: Curriculum) -> Mapping[str, Any]: ...
```

## Implementation: AdaptiveCurriculumDesigner

### Prerequisite DAG

Objectives are topologically sorted using Kahn's algorithm. Cycle detection raises `ValueError`.

```
algebra ──▶ calculus ──────────▶ optimization ──▶ ml_basics
   │                                 ▲
   └──▶ linear_algebra ─────────────┘
```

### ZPD Selection

```
    ┌─────────────┬──────────────────┬───────────────┐
    │  MASTERED   │       ZPD        │  TOO HARD     │
    │  mastery≥0.8│  readiness≥0.8   │  prerequisites│
    │  (skip)     │  mastery<0.8     │  not met      │
    │             │  (SELECT HERE)   │  (wait)       │
    └─────────────┴──────────────────┴───────────────┘
```

For each unmastered objective: `readiness = min(mastery of prerequisites)`. Select from ZPD candidates the one closest to current competence + ε.

### Adaptive Difficulty

- Performance > 0.9 consistently → increase adaptation_rate × 1.5 (skip ahead)
- Performance < 0.5 consistently → decrease adaptation_rate × 0.5 (revisit)
- Plateau detected (Δmastery < 0.01 for 5 assessments) → flag for strategy change

## Integration

```
GoalDecomposer (10.2) ──▶ decomposed goals as objectives
FewShotAdapter (27.3) ──▶ adaptation results for mastery
ReflectionCycle (16.5) ──▶ progress triggers adaptation
CuriosityModule (13.3) ──▶ exploration override
GeneralizationOrchestrator (27.5) ──▶ curriculum in transfer pipeline
```

## Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_curriculum_objectives_mastered_total` | Counter | Objectives mastered |
| `asi_curriculum_design_duration_seconds` | Histogram | Design time |
| `asi_curriculum_adaptation_events_total` | Counter | Difficulty adaptations |
| `asi_curriculum_progress_ratio` | Gauge | Completion fraction |
| `asi_curriculum_plateau_detections_total` | Counter | Plateaus detected |

## Test Targets (12)

1. `test_learning_objective_immutability`
2. `test_curriculum_ordering_respects_prerequisites`
3. `test_design_curriculum_topological_sort`
4. `test_design_curriculum_detects_cycles`
5. `test_assess_mastery_updates_score`
6. `test_get_next_objective_zpd_selection`
7. `test_adapt_difficulty_increases_on_high_performance`
8. `test_adapt_difficulty_decreases_on_low_performance`
9. `test_evaluate_progress_returns_stats`
10. `test_plateau_detection`
11. `test_null_designer_returns_defaults`
12. `test_factory_adaptive`

## Phase 27 Sub-phase Tracker

| # | Component | Issue | Wiki | Status |
|---|-----------|-------|------|--------|
| 27.1 | DomainMapper | [#594](https://github.com/web3guru888/asi-build/issues/594) | [[Phase-27-Domain-Mapper]] | ✅ Spec'd |
| 27.2 | AbstractionEngine | [#595](https://github.com/web3guru888/asi-build/issues/595) | [[Phase-27-Abstraction-Engine]] | ✅ Spec'd |
| 27.3 | FewShotAdapter | [#596](https://github.com/web3guru888/asi-build/issues/596) | [[Phase-27-Few-Shot-Adapter]] | ✅ Spec'd |
| 27.4 | CurriculumDesigner | [#597](https://github.com/web3guru888/asi-build/issues/597) | [[Phase-27-Curriculum-Designer]] | ✅ Spec'd |
| 27.5 | GeneralizationOrchestrator | [#598](https://github.com/web3guru888/asi-build/issues/598) | [[Phase-27-Generalization-Orchestrator]] | ✅ Spec'd |

---
*Issue: [#597](https://github.com/web3guru888/asi-build/issues/597) | S&T: [#605](https://github.com/web3guru888/asi-build/discussions/605) | Q&A: [#606](https://github.com/web3guru888/asi-build/discussions/606) | Planning: [#593](https://github.com/web3guru888/asi-build/discussions/593)*
