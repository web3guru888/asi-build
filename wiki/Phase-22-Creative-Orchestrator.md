# Phase 22.5 — CreativeOrchestrator

> **Sub-phase**: 22.5 of 5 (capstone) · **Layer**: Creative Intelligence & Generative Thinking  
> **Status**: ✅ Spec Complete — **🎉 PHASE 22 COMPLETE**  
> **Issue**: [#517](https://github.com/web3guru888/asi-build/issues/517)  
> **Depends on**: DivergentGenerator (22.1), AnalogyMapper (22.2), ConceptBlender (22.3), AestheticEvaluator (22.4)

---

## Overview

The **CreativeOrchestrator** is the Phase 22 capstone — a unified pipeline that composes all four creative sub-components into a coherent creative cognition system. It implements a **6-phase creative process** inspired by Boden's (2004) taxonomy of creativity, managing the flow from initial exploration through analogy discovery, conceptual blending, aesthetic evaluation, and iterative refinement.

### Design Rationale

Individual creative components (divergent generation, analogy mapping, concept blending, aesthetic evaluation) are powerful but insufficient alone. The CreativeOrchestrator provides:

1. **Pipeline orchestration** — sequence the 4 components in the right order with data flowing between them
2. **Strategy selection** — choose which creative approach (exploratory, combinational, transformational) based on the task
3. **Iterative refinement** — use aesthetic feedback to improve creative outputs over multiple passes
4. **Portfolio management** — maintain a history of creative outputs for cumulative creative growth
5. **CognitiveCycle integration** — `_creative_step()` entry point for the broader ASI architecture

---

## Enums

### CreativePhase

```python
class CreativePhase(str, Enum):
    """Phase of the creative pipeline."""
    IDLE        = "idle"         # Waiting for input
    DIVERGING   = "diverging"   # Generating raw ideas (DivergentGenerator)
    MAPPING     = "mapping"     # Finding analogies (AnalogyMapper)
    BLENDING    = "blending"    # Conceptual blending (ConceptBlender)
    EVALUATING  = "evaluating"  # Aesthetic scoring (AestheticEvaluator)
    REFINING    = "refining"    # Iterative improvement
    COMPLETE    = "complete"    # Output ready
    FAILED      = "failed"      # Unrecoverable error
```

### CreativeStrategy

```python
class CreativeStrategy(str, Enum):
    """High-level creative strategy (Boden's taxonomy)."""
    EXPLORATORY      = "exploratory"       # Search within existing conceptual space
    COMBINATIONAL    = "combinational"     # Novel combinations of familiar ideas
    TRANSFORMATIONAL = "transformational"  # Transform the conceptual space itself
    ADAPTIVE         = "adaptive"          # Auto-select based on task analysis
```

---

## Data Classes

### CreativeTask

```python
@dataclass(frozen=True)
class CreativeTask:
    """A creative task to be processed by the orchestrator."""
    id: str                              # UUID
    prompt: str                          # Natural-language creative brief
    strategy: CreativeStrategy = CreativeStrategy.ADAPTIVE
    profile: AestheticProfile = AestheticProfile.BALANCED
    max_ideas: int = 50                  # Max ideas to generate in divergent phase
    max_blends: int = 10                 # Max blends to produce
    refinement_rounds: int = 3           # Iterations of evaluate→refine
    quality_threshold: float = 0.6       # Minimum aesthetic score to accept
    timeout_s: float = 60.0              # Total task timeout
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
```

### CreativeResult

```python
@dataclass(frozen=True)
class CreativeResult:
    """Output of the creative pipeline."""
    id: str                                      # UUID
    task_id: str                                 # Originating task
    strategy_used: CreativeStrategy
    phase_trace: tuple[CreativePhase, ...]       # Phases executed
    ideas: tuple[Idea, ...]                      # DivergentGenerator output
    mappings: tuple[StructuralMapping, ...]      # AnalogyMapper output
    blends: tuple[Blend, ...]                    # ConceptBlender output
    assessments: tuple[AestheticAssessment, ...]  # AestheticEvaluator output
    best_output: Any                             # Top-ranked creative product
    best_score: float                            # Best aesthetic score
    total_latency_s: float                       # End-to-end time
    refinement_rounds: int                       # Actual refinements performed
    created_at: float = field(default_factory=time.time)
```

### OrchestratorConfig

```python
@dataclass(frozen=True)
class OrchestratorConfig:
    """Configuration for the creative orchestrator."""
    default_strategy: CreativeStrategy = CreativeStrategy.ADAPTIVE
    default_profile: AestheticProfile = AestheticProfile.BALANCED
    max_portfolio_size: int = 500           # History of creative results
    parallel_blends: bool = True            # Blend pairs in parallel
    enable_analogy: bool = True             # Use AnalogyMapper in pipeline
    enable_blending: bool = True            # Use ConceptBlender in pipeline
    min_ideas_for_blending: int = 4         # Need ≥ 4 ideas to blend pairs
    strategy_analysis_timeout_s: float = 5.0
    pipeline_timeout_s: float = 60.0
```

---

## Protocol

```python
@runtime_checkable
class CreativeOrchestrator(Protocol):
    """Orchestrates the full creative pipeline."""

    async def create(
        self,
        task: CreativeTask,
    ) -> CreativeResult: ...

    async def refine(
        self,
        result: CreativeResult,
        *,
        rounds: int = 1,
    ) -> CreativeResult: ...

    async def get_portfolio(
        self,
        *,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[CreativeResult]: ...
```

---

## AsyncCreativeOrchestrator — Full Implementation

```python
class AsyncCreativeOrchestrator:
    """
    Production creative orchestration engine.

    Composes:
      - DivergentGenerator (22.1) — idea generation
      - AnalogyMapper (22.2) — structural analogy discovery
      - ConceptBlender (22.3) — conceptual blending
      - AestheticEvaluator (22.4) — quality evaluation

    6-phase pipeline:
      DIVERGING → MAPPING → BLENDING → EVALUATING → REFINING → COMPLETE
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        divergent: DivergentGenerator,
        mapper: AnalogyMapper,
        blender: ConceptBlender,
        evaluator: AestheticEvaluator,
    ) -> None:
        self._cfg = config
        self._divergent = divergent
        self._mapper = mapper
        self._blender = blender
        self._evaluator = evaluator
        self._lock = asyncio.Lock()
        self._portfolio: deque[CreativeResult] = deque(maxlen=config.max_portfolio_size)

        # Prometheus metrics
        self._tasks_completed = Counter(
            "creative_tasks_completed_total",
            "Creative tasks completed",
            ["strategy"],
        )
        self._pipeline_latency = Histogram(
            "creative_pipeline_latency_seconds",
            "End-to-end creative pipeline time",
        )
        self._best_score_histogram = Histogram(
            "creative_best_score",
            "Distribution of best creative scores",
            buckets=[0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0],
        )
        self._phase_latency = Histogram(
            "creative_phase_latency_seconds",
            "Per-phase latency",
            ["phase"],
        )
        self._portfolio_size = Gauge(
            "creative_portfolio_size",
            "Current portfolio size",
        )

    # ── create (6-phase pipeline) ─────────────────────────────
    async def create(self, task: CreativeTask) -> CreativeResult:
        """
        Execute the full 6-phase creative pipeline:

        Phase 1 — DIVERGING:
          Generate a diverse population of raw ideas using DivergentGenerator.
          Strategy selection determines the divergent strategy:
            EXPLORATORY → CONSTRAINT_RELAXATION
            COMBINATIONAL → RANDOM_COMBINATION + SCAMPER
            TRANSFORMATIONAL → BISOCIATION + MORPHOLOGICAL_ANALYSIS
            ADAPTIVE → analyse task, auto-select

        Phase 2 — MAPPING:
          Use AnalogyMapper to find structural analogies between ideas.
          Cross-pollinate by transferring inferences between idea pairs.

        Phase 3 — BLENDING:
          Use ConceptBlender to blend promising idea pairs into novel concepts.
          Parallel blending via asyncio.gather if enabled.

        Phase 4 — EVALUATING:
          Score all outputs (ideas + blends) with AestheticEvaluator.
          Filter by quality_threshold.

        Phase 5 — REFINING:
          Iterate: take top candidates, mutate/re-blend, re-evaluate.
          Repeat for refinement_rounds or until quality_threshold met.

        Phase 6 — COMPLETE:
          Return the best creative output with full provenance trace.
        """
        start = time.time()
        phases: list[CreativePhase] = []
        strategy = task.strategy
        if strategy == CreativeStrategy.ADAPTIVE:
            strategy = await self._analyse_strategy(task)

        try:
            # ── Phase 1: DIVERGING ──
            phases.append(CreativePhase.DIVERGING)
            with self._phase_latency.labels(phase="diverging").time():
                div_strategy = self._strategy_to_divergent(strategy)
                ideas = await self._divergent.generate(
                    task.prompt,
                    strategy=div_strategy,
                    n=task.max_ideas,
                )
                # Evolve population
                ideas = await self._divergent.evolve_population(ideas, generations=5)

            # ── Phase 2: MAPPING ──
            mappings: list[StructuralMapping] = []
            if self._cfg.enable_analogy and len(ideas) >= 2:
                phases.append(CreativePhase.MAPPING)
                with self._phase_latency.labels(phase="mapping").time():
                    structures = [self._idea_to_structure(i) for i in ideas[:20]]
                    for i, struct in enumerate(structures):
                        candidates = structures[:i] + structures[i+1:]
                        found = await self._mapper.find_analogies(
                            struct, candidates=candidates[:5],
                        )
                        mappings.extend(found)

            # ── Phase 3: BLENDING ──
            blends: list[Blend] = []
            if self._cfg.enable_blending and len(ideas) >= self._cfg.min_ideas_for_blending:
                phases.append(CreativePhase.BLENDING)
                with self._phase_latency.labels(phase="blending").time():
                    pairs = self._select_blend_pairs(ideas, mappings, task.max_blends)
                    if self._cfg.parallel_blends:
                        blend_tasks = [
                            self._blender.blend(
                                self._idea_to_mental_space(a),
                                self._idea_to_mental_space(b),
                            )
                            for a, b in pairs
                        ]
                        results = await asyncio.gather(*blend_tasks, return_exceptions=True)
                        blends = [r for r in results if isinstance(r, Blend)]
                    else:
                        for a, b in pairs:
                            blend = await self._blender.blend(
                                self._idea_to_mental_space(a),
                                self._idea_to_mental_space(b),
                            )
                            blends.append(blend)

            # ── Phase 4: EVALUATING ──
            phases.append(CreativePhase.EVALUATING)
            with self._phase_latency.labels(phase="evaluating").time():
                all_outputs: list[Any] = list(ideas) + list(blends)
                assessments = await self._evaluator.rank(all_outputs)

            # ── Phase 5: REFINING ──
            phases.append(CreativePhase.REFINING)
            actual_rounds = 0
            with self._phase_latency.labels(phase="refining").time():
                for round_num in range(task.refinement_rounds):
                    if assessments and assessments[0].weighted_total >= task.quality_threshold:
                        break
                    actual_rounds += 1
                    # Mutate top candidates
                    top_ideas = [
                        i for i in ideas
                        if any(a.target_id == getattr(i, 'id', '') and a.weighted_total > 0.3
                               for a in assessments)
                    ][:5]
                    for idea in top_ideas:
                        mutated = await self._divergent.mutate(idea)
                        ideas.append(mutated)
                    # Re-evaluate
                    all_outputs = list(ideas) + list(blends)
                    assessments = await self._evaluator.rank(all_outputs)

            # ── Phase 6: COMPLETE ──
            phases.append(CreativePhase.COMPLETE)
            best_output = all_outputs[0] if all_outputs else None
            best_score = assessments[0].weighted_total if assessments else 0.0

            result = CreativeResult(
                id=str(uuid4()),
                task_id=task.id,
                strategy_used=strategy,
                phase_trace=tuple(phases),
                ideas=tuple(ideas),
                mappings=tuple(mappings),
                blends=tuple(blends),
                assessments=tuple(assessments),
                best_output=best_output,
                best_score=best_score,
                total_latency_s=round(time.time() - start, 3),
                refinement_rounds=actual_rounds,
            )

            self._portfolio.append(result)
            self._portfolio_size.set(len(self._portfolio))
            self._tasks_completed.labels(strategy=strategy.value).inc()
            self._pipeline_latency.observe(result.total_latency_s)
            self._best_score_histogram.observe(best_score)
            return result

        except Exception as exc:
            phases.append(CreativePhase.FAILED)
            return CreativeResult(
                id=str(uuid4()),
                task_id=task.id,
                strategy_used=strategy,
                phase_trace=tuple(phases),
                ideas=(), mappings=(), blends=(), assessments=(),
                best_output=None, best_score=0.0,
                total_latency_s=round(time.time() - start, 3),
                refinement_rounds=0,
            )

    # ── refine ────────────────────────────────────────────────
    async def refine(
        self,
        result: CreativeResult,
        *,
        rounds: int = 1,
    ) -> CreativeResult:
        """
        Further refine an existing creative result:
        1. Mutate top ideas
        2. Re-blend top blends
        3. Re-evaluate all
        """
        ideas = list(result.ideas)
        blends = list(result.blends)

        for _ in range(rounds):
            # Mutate top 3 ideas
            for idea in ideas[:3]:
                mutated = await self._divergent.mutate(idea)
                ideas.append(mutated)

            # Optimise top 2 blends
            for blend in blends[:2]:
                optimized = await self._blender.optimize_blend(blend, iterations=2)
                blends.append(optimized)

        # Re-evaluate
        all_outputs = list(ideas) + list(blends)
        assessments = await self._evaluator.rank(all_outputs)
        best_output = all_outputs[0] if all_outputs else None
        best_score = assessments[0].weighted_total if assessments else 0.0

        refined = replace(
            result,
            ideas=tuple(ideas),
            blends=tuple(blends),
            assessments=tuple(assessments),
            best_output=best_output,
            best_score=best_score,
            refinement_rounds=result.refinement_rounds + rounds,
        )
        return refined

    # ── get_portfolio ─────────────────────────────────────────
    async def get_portfolio(
        self,
        *,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[CreativeResult]:
        """Retrieve top creative results from portfolio."""
        filtered = [
            r for r in self._portfolio
            if r.best_score >= min_score
        ]
        filtered.sort(key=lambda r: r.best_score, reverse=True)
        return filtered[:limit]

    # ── private methods ───────────────────────────────────────

    async def _analyse_strategy(self, task: CreativeTask) -> CreativeStrategy:
        """Auto-select strategy based on task analysis."""
        prompt_lower = task.prompt.lower()
        if any(kw in prompt_lower for kw in ("combine", "merge", "mix", "fusion")):
            return CreativeStrategy.COMBINATIONAL
        if any(kw in prompt_lower for kw in ("transform", "revolutionize", "reimagine", "radical")):
            return CreativeStrategy.TRANSFORMATIONAL
        return CreativeStrategy.EXPLORATORY

    def _strategy_to_divergent(self, strategy: CreativeStrategy) -> DivergentStrategy:
        """Map creative strategy to divergent generation strategy."""
        match strategy:
            case CreativeStrategy.EXPLORATORY:
                return DivergentStrategy.CONSTRAINT_RELAXATION
            case CreativeStrategy.COMBINATIONAL:
                return DivergentStrategy.SCAMPER
            case CreativeStrategy.TRANSFORMATIONAL:
                return DivergentStrategy.BISOCIATION
            case _:
                return DivergentStrategy.RANDOM_COMBINATION

    def _idea_to_structure(self, idea: Idea) -> RelationalStructure:
        """Convert an Idea to RelationalStructure for analogy mapping."""
        tokens = idea.content.split()[:10]  # First 10 tokens as entities
        return RelationalStructure(
            domain_name=idea.id,
            entities=frozenset(tokens),
            attributes=(),
            relations=(),
        )

    def _idea_to_mental_space(self, idea: Idea) -> MentalSpace:
        """Convert an Idea to MentalSpace for blending."""
        tokens = idea.content.split()[:10]
        return MentalSpace(
            name=idea.id,
            entities=frozenset(tokens),
            properties={},
            relations=(),
        )

    def _select_blend_pairs(
        self,
        ideas: list[Idea],
        mappings: list[StructuralMapping],
        max_pairs: int,
    ) -> list[tuple[Idea, Idea]]:
        """Select idea pairs for blending, preferring mapped pairs."""
        pairs: list[tuple[Idea, Idea]] = []
        idea_index = {i.id: i for i in ideas}

        # Prefer pairs that have analogy mappings
        for m in mappings:
            src = idea_index.get(m.source.domain_name)
            tgt = idea_index.get(m.target.domain_name)
            if src and tgt and (src, tgt) not in pairs:
                pairs.append((src, tgt))
                if len(pairs) >= max_pairs:
                    return pairs

        # Fill remaining with diverse pairs
        for i in range(0, min(len(ideas) - 1, max_pairs * 2), 2):
            if len(pairs) >= max_pairs:
                break
            pairs.append((ideas[i], ideas[i + 1]))

        return pairs
```

---

## Boden's Creativity Taxonomy

Margaret Boden (2004) identifies three forms of creativity:

| Type | Description | DivergentStrategy | Example |
|------|-------------|-------------------|---------|
| **Exploratory** | Search the existing conceptual space more thoroughly | `CONSTRAINT_RELAXATION` | A jazz musician exploring unusual chord progressions |
| **Combinational** | Make unfamiliar combinations of familiar ideas | `SCAMPER`, `RANDOM_COMBINATION` | Combining biology and computing → genetic algorithms |
| **Transformational** | Transform the conceptual space itself | `BISOCIATION`, `MORPHOLOGICAL_ANALYSIS` | Einstein's relativity — redefining space-time |

The CreativeOrchestrator's **ADAPTIVE** strategy analyses the task prompt and auto-selects the most appropriate approach.

---

## 6-Phase Pipeline Sequence Diagram

```
      CreativeTask
          │
          ▼
┌─────────────────┐
│  1. DIVERGING    │  DivergentGenerator.generate() + evolve_population()
│  (idea pop.)     │  → N ideas with novelty scores
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. MAPPING      │  AnalogyMapper.find_analogies()
│  (analogies)     │  → structural mappings between ideas
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. BLENDING     │  ConceptBlender.blend() per selected pair
│  (new concepts)  │  → blends with emergent properties
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. EVALUATING   │  AestheticEvaluator.rank()
│  (scoring)       │  → ranked assessments
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌──────────┐
│  5. REFINING     │───▶│ mutate() │──┐
│  (iteration)     │    │ re-blend │  │ loop until
└────────┬────────┘    │ re-score │  │ threshold
         │             └──────────┘◀─┘
         ▼
┌─────────────────┐
│  6. COMPLETE     │  CreativeResult with full provenance
│  (output)        │  → best_output + best_score + trace
└─────────────────┘
```

---

## Full Phase 22 Pipeline ASCII

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  PHASE 22 — CREATIVE INTELLIGENCE                       │
│                                                                         │
│  ┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐  │
│  │ DivergentGen     │────▶│ AnalogyMapper   │────▶│ ConceptBlender   │  │
│  │ (22.1)           │     │ (22.2)          │     │ (22.3)           │  │
│  │                  │     │                 │     │                  │  │
│  │ • SCAMPER        │     │ • SME algorithm │     │ • 4-space model  │  │
│  │ • Bisociation    │     │ • Structure map │     │ • CCE triple     │  │
│  │ • Genetic algo   │     │ • Inference xfer│     │ • Emergent props │  │
│  └─────────────────┘     └─────────────────┘     └────────┬─────────┘  │
│         ▲                                                  │            │
│         │                                                  ▼            │
│         │  feedback    ┌─────────────────┐     ┌──────────────────┐    │
│         │◀─────────────│ Creative        │◀────│ AestheticEval    │    │
│         │              │ Orchestrator    │     │ (22.4)           │    │
│         │              │ (22.5)          │     │                  │    │
│         │              │                 │     │ • 5 dimensions   │    │
│         │              │ • 6-phase pipe  │     │ • Profile weights│    │
│         │              │ • Boden's types │     │ • Emotion+Surpr. │    │
│         │              │ • Portfolio     │     └──────────────────┘    │
│         │              └─────────────────┘                             │
│         │                       │                                      │
│         └───── mutate/evolve ◀──┘                                      │
│                                                                         │
│  External Dependencies:                                                │
│  • CuriosityModule (13.3) → concept pool seeding                       │
│  • SurpriseDetector (13.4) → surprise scoring                          │
│  • AnalogicalReasoner (20.2) → analogical reasoning substrate         │
│  • EmotionModel (21.1) → emotional resonance                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## CognitiveCycle Integration

```python
class CognitiveCycle:
    """Main cognitive loop of the ASI architecture."""

    async def _creative_step(self) -> None:
        """
        Called from CognitiveCycle.run_step() when creative thinking is needed.

        Integrates with:
          - _perception_step() → provides context
          - _reasoning_step() → validates creative outputs
          - _emotional_step() → modulates creative profile
          - _temporal_step() → schedules creative tasks
        """
        # Determine creative need from current context
        task = CreativeTask(
            id=str(uuid4()),
            prompt=self._current_context.summary,
            strategy=CreativeStrategy.ADAPTIVE,
            profile=self._emotional_profile_to_aesthetic(),
            max_ideas=30,
            max_blends=5,
            refinement_rounds=2,
            quality_threshold=0.5,
        )

        result = await self._creative_orchestrator.create(task)

        if result.best_score >= 0.5:
            # Feed creative output to reasoning for validation
            validated = await self._reasoning_orchestrator.validate(result.best_output)
            if validated:
                # Add to world model
                await self._world_model.integrate_creative_output(result)
                # Record emotional impact
                await self._affective_orchestrator.process_creative_event(result)

    def _emotional_profile_to_aesthetic(self) -> AestheticProfile:
        """Map current emotional state to aesthetic evaluation profile."""
        mood = self._mood_regulator.current_mood()
        if mood.valence > 0.5:
            return AestheticProfile.ARTISTIC  # Positive mood → artistic exploration
        elif mood.arousal > 0.5:
            return AestheticProfile.EXPLORATORY  # High arousal → exploratory
        else:
            return AestheticProfile.SCIENTIFIC  # Calm → scientific rigour
```

---

## Cross-Phase Integration Map

```
Phase 13 — World Modelling & Curiosity
├── CuriosityModule (13.3) ──────▶ DivergentGenerator (22.1) concept pool
├── SurpriseDetector (13.4) ─────▶ AestheticEvaluator (22.4) surprise score
└── WorldModel (13.1) ◀──────────── CreativeOrchestrator (22.5) output

Phase 20 — Knowledge Synthesis & Reasoning
├── AnalogicalReasoner (20.2) ───▶ DivergentGenerator (22.1) bisociation
├── AnalogicalReasoner (20.2) ───▶ AnalogyMapper (22.2) reasoning substrate
└── ReasoningOrchestrator (20.5) ◀─ CreativeOrchestrator (22.5) validation

Phase 21 — Emotional Intelligence
├── EmotionModel (21.1) ─────────▶ AestheticEvaluator (22.4) resonance
├── MoodRegulator (21.4) ────────▶ CreativeOrchestrator (22.5) profile select
└── AffectiveOrchestrator (21.5) ◀─ CreativeOrchestrator (22.5) creative events
```

---

## NullCreativeOrchestrator

```python
class NullCreativeOrchestrator:
    """No-op implementation for testing and DI."""

    async def create(self, task):
        return CreativeResult(
            id="null", task_id=task.id,
            strategy_used=CreativeStrategy.ADAPTIVE,
            phase_trace=(), ideas=(), mappings=(), blends=(),
            assessments=(), best_output=None, best_score=0.0,
            total_latency_s=0.0, refinement_rounds=0,
        )

    async def refine(self, result, *, rounds=1):
        return result

    async def get_portfolio(self, *, limit=10, min_score=0.0):
        return []
```

---

## Factory

```python
def make_creative_orchestrator(
    config: OrchestratorConfig | None = None,
    *,
    divergent: DivergentGenerator | None = None,
    mapper: AnalogyMapper | None = None,
    blender: ConceptBlender | None = None,
    evaluator: AestheticEvaluator | None = None,
    null: bool = False,
) -> CreativeOrchestrator:
    if null:
        return NullCreativeOrchestrator()
    return AsyncCreativeOrchestrator(
        config=config or OrchestratorConfig(),
        divergent=divergent or make_divergent_generator(),
        mapper=mapper or make_analogy_mapper(),
        blender=blender or make_concept_blender(),
        evaluator=evaluator or make_aesthetic_evaluator(),
    )
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `creative_tasks_completed_total` | Counter | `strategy` | Tasks completed by strategy |
| `creative_pipeline_latency_seconds` | Histogram | — | End-to-end pipeline time |
| `creative_best_score` | Histogram | — | Best score per task |
| `creative_phase_latency_seconds` | Histogram | `phase` | Per-phase latency |
| `creative_portfolio_size` | Gauge | — | Current portfolio size |

### PromQL Examples

```promql
# Task completion rate by strategy
rate(creative_tasks_completed_total[5m])

# Pipeline latency p95
histogram_quantile(0.95, rate(creative_pipeline_latency_seconds_bucket[5m]))

# Average best score
histogram_quantile(0.5, rate(creative_best_score_bucket[5m]))

# Phase breakdown
histogram_quantile(0.95, rate(creative_phase_latency_seconds_bucket{phase="blending"}[5m]))
```

### Grafana Alert YAML

```yaml
- alert: CreativePipelineSlow
  expr: histogram_quantile(0.95, rate(creative_pipeline_latency_seconds_bucket[5m])) > 120
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Creative pipeline p95 latency exceeds 120s"

- alert: LowCreativeQuality
  expr: histogram_quantile(0.5, rate(creative_best_score_bucket[5m])) < 0.3
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Median creative output score below 0.3"
```

---

## mypy Strict Compliance

| Pattern | Narrowing technique |
|---------|---------------------|
| `task.strategy == ADAPTIVE` | `await self._analyse_strategy(task)` resolves |
| `match strategy:` | Exhaustive `case` branches |
| `asyncio.gather(*tasks, return_exceptions=True)` | `isinstance(r, Blend)` filter |
| `deque[CreativeResult]` | Bounded `maxlen` |
| `best_output: Any` | Runtime type check before downstream use |

---

## Test Targets (12)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_create_full_pipeline` | CreativeResult has non-empty ideas + assessments |
| 2 | `test_phase_trace_includes_all` | All 6 phases in trace (happy path) |
| 3 | `test_adaptive_strategy_selection` | "combine" prompt → COMBINATIONAL |
| 4 | `test_transformational_uses_bisociation` | TRANSFORMATIONAL → BISOCIATION divergent |
| 5 | `test_refinement_improves_score` | Refined result score ≥ original |
| 6 | `test_quality_threshold_stops_early` | High-quality ideas skip refinement |
| 7 | `test_portfolio_ordered_by_score` | get_portfolio returns descending scores |
| 8 | `test_portfolio_min_score_filter` | min_score filters correctly |
| 9 | `test_failed_phase_trace` | Exception → FAILED in trace |
| 10 | `test_parallel_blending` | parallel_blends=True runs asyncio.gather |
| 11 | `test_null_orchestrator_noop` | NullCreativeOrchestrator returns defaults |
| 12 | `test_prometheus_metrics` | Counters/histograms update after create() |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_create_full_pipeline():
    """Full pipeline produces creative result with all stages."""
    orch = make_creative_orchestrator()
    task = CreativeTask(
        id="test-1",
        prompt="Design a novel approach to distributed memory systems",
        max_ideas=10,
        max_blends=3,
        refinement_rounds=1,
    )
    result = await orch.create(task)
    assert result.task_id == "test-1"
    assert len(result.ideas) > 0
    assert CreativePhase.DIVERGING in result.phase_trace
    assert CreativePhase.COMPLETE in result.phase_trace
    assert result.best_score >= 0.0

@pytest.mark.asyncio
async def test_adaptive_strategy_selection():
    """ADAPTIVE auto-selects strategy based on prompt keywords."""
    orch = make_creative_orchestrator()
    task_combine = CreativeTask(id="c1", prompt="Combine memory and emotion")
    task_transform = CreativeTask(id="t1", prompt="Revolutionize attention mechanisms")
    r1 = await orch.create(task_combine)
    r2 = await orch.create(task_transform)
    assert r1.strategy_used == CreativeStrategy.COMBINATIONAL
    assert r2.strategy_used == CreativeStrategy.TRANSFORMATIONAL
```

---

## Implementation Order (14 steps)

| Step | Task | File |
|------|------|------|
| 1 | Define `CreativePhase` enum | `enums.py` |
| 2 | Define `CreativeStrategy` enum | `enums.py` |
| 3 | Define `CreativeTask` frozen dataclass | `models.py` |
| 4 | Define `CreativeResult` frozen dataclass | `models.py` |
| 5 | Define `OrchestratorConfig` frozen dataclass | `models.py` |
| 6 | Define `CreativeOrchestrator` Protocol | `protocols.py` |
| 7 | Implement `_analyse_strategy` + `_strategy_to_divergent` | `creative_orchestrator.py` |
| 8 | Implement Phase 1 DIVERGING | `creative_orchestrator.py` |
| 9 | Implement Phase 2 MAPPING | `creative_orchestrator.py` |
| 10 | Implement Phase 3 BLENDING | `creative_orchestrator.py` |
| 11 | Implement Phase 4+5 EVALUATING+REFINING | `creative_orchestrator.py` |
| 12 | Implement `refine` + `get_portfolio` | `creative_orchestrator.py` |
| 13 | Implement `NullCreativeOrchestrator` + factory | `factory.py` |
| 14 | Write tests | `test_creative_orchestrator.py` |

---

## Phase 22 — Creative Intelligence Sub-Phase Tracker 🎉 COMPLETE

| # | Sub-phase | Component | Status |
|---|-----------|-----------|--------|
| 22.1 | DivergentGenerator | Divergent idea generation + evolutionary search | ✅ Spec |
| 22.2 | AnalogyMapper | Structure-mapping analogical transfer | ✅ Spec |
| 22.3 | ConceptBlender | Fauconnier-Turner conceptual blending | ✅ Spec |
| 22.4 | AestheticEvaluator | Multi-dimensional aesthetic scoring | ✅ Spec |
| 22.5 | CreativeOrchestrator | Full creative pipeline orchestration | ✅ Spec |

> **Phase 22 — Creative Intelligence & Generative Thinking** is now **COMPLETE**.  
> The ASI cognitive architecture can generate, discover, blend, evaluate, and refine creative ideas through a principled 6-phase pipeline grounded in cognitive science (Guilford, Koestler, Gentner, Fauconnier-Turner, Boden).
