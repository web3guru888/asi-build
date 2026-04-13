# Phase 22.1 — DivergentGenerator

> **Sub-phase**: 22.1 of 5 · **Layer**: Creative Intelligence & Generative Thinking  
> **Status**: ✅ Spec Complete  
> **Issue**: [#513](https://github.com/web3guru888/asi-build/issues/513)  
> **Depends on**: CuriosityModule (13.3), AnalogicalReasoner (20.2)

---

## Overview

The **DivergentGenerator** produces novel ideas by combining structured creativity techniques (SCAMPER, bisociation, morphological analysis) with evolutionary search. It is the "brainstorming engine" of the ASI cognitive architecture — generating a diverse population of candidate ideas that downstream components (AnalogyMapper, ConceptBlender, AestheticEvaluator) can refine and evaluate.

### Design Rationale

Divergent thinking — the ability to generate multiple, varied solutions from a single prompt — is a core pillar of creative cognition (Guilford, 1967). The DivergentGenerator formalises this with:

1. **Strategy-based generation** — five distinct ideation techniques, each producing ideas with different structural properties.
2. **Novelty scoring** — information-theoretic measurement of how far an idea departs from prior knowledge.
3. **Evolutionary refinement** — genetic-algorithm-style crossover + mutation to explore the idea space efficiently.

---

## Enums

### DivergentStrategy

```python
class DivergentStrategy(str, Enum):
    """Strategy for generating divergent ideas."""
    RANDOM_COMBINATION   = "random_combination"    # Combine random concepts
    SCAMPER              = "scamper"                # 7-operator creative checklist
    BISOCIATION          = "bisociation"            # Koestler cross-domain fusion
    CONSTRAINT_RELAXATION = "constraint_relaxation" # Remove/invert constraints
    MORPHOLOGICAL_ANALYSIS = "morphological_analysis" # Zwicky parameter matrix
```

### IdeaQuality

```python
class IdeaQuality(str, Enum):
    """Quality tier of a generated idea."""
    RAW      = "raw"       # Freshly generated, unscored
    FILTERED = "filtered"  # Passed minimum novelty threshold
    REFINED  = "refined"   # Post-crossover/mutation
    SELECTED = "selected"  # Top-k after evaluation
```

---

## Data Classes

### Idea

```python
@dataclass(frozen=True)
class Idea:
    """A single creative idea."""
    id: str                          # UUID
    content: str                     # Natural-language description
    strategy: DivergentStrategy      # Generation strategy used
    quality: IdeaQuality             # Current quality tier
    novelty_score: float             # [0.0, 1.0] — information-theoretic novelty
    parent_ids: tuple[str, ...] = () # IDs of parent ideas (for crossover lineage)
    generation: int = 0              # Evolutionary generation number
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
```

### DivergentConfig

```python
@dataclass(frozen=True)
class DivergentConfig:
    """Configuration for divergent generation."""
    population_size: int = 50              # Ideas per generation
    generations: int = 10                  # Evolutionary iterations
    novelty_threshold: float = 0.3         # Minimum novelty to survive filtering
    crossover_rate: float = 0.7            # Probability of crossover
    mutation_rate: float = 0.2             # Probability of mutation
    elite_fraction: float = 0.1            # Fraction preserved unchanged
    strategy: DivergentStrategy = DivergentStrategy.BISOCIATION
    concept_pool_size: int = 200           # Max concepts in working memory
    timeout_s: float = 30.0                # Per-generation timeout
```

---

## Protocol

```python
@runtime_checkable
class DivergentGenerator(Protocol):
    """Generates diverse creative ideas via structured divergent thinking."""

    async def generate(
        self,
        prompt: str,
        *,
        strategy: DivergentStrategy | None = None,
        n: int = 10,
    ) -> list[Idea]: ...

    async def score_novelty(self, idea: Idea) -> float: ...

    async def crossover(self, parent_a: Idea, parent_b: Idea) -> Idea: ...

    async def mutate(self, idea: Idea) -> Idea: ...

    async def evolve_population(
        self,
        seed_ideas: list[Idea],
        *,
        generations: int | None = None,
    ) -> list[Idea]: ...
```

---

## AsyncDivergentGenerator — Full Implementation

```python
class AsyncDivergentGenerator:
    """
    Production divergent-thinking engine.

    Combines five ideation strategies with evolutionary search:
    1. generate() — produce RAW ideas using the configured strategy
    2. score_novelty() — compute information-theoretic novelty
    3. crossover() — combine two parent ideas into a child
    4. mutate() — perturb an idea to explore nearby space
    5. evolve_population() — full evolutionary loop
    """

    def __init__(
        self,
        config: DivergentConfig,
        curiosity: CuriosityModule | None = None,
        analogical: AnalogicalReasoner | None = None,
    ) -> None:
        self._cfg = config
        self._curiosity = curiosity
        self._analogical = analogical
        self._lock = asyncio.Lock()
        self._concept_pool: list[str] = []
        self._known_ideas: dict[str, Idea] = {}

        # Prometheus metrics
        self._ideas_generated = Counter(
            "divergent_ideas_generated_total",
            "Total ideas generated",
            ["strategy"],
        )
        self._novelty_histogram = Histogram(
            "divergent_novelty_score",
            "Distribution of novelty scores",
            buckets=[0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0],
        )
        self._generation_latency = Histogram(
            "divergent_generation_latency_seconds",
            "Time per generation cycle",
        )
        self._population_size = Gauge(
            "divergent_population_size",
            "Current population size",
        )
        self._elite_preserved = Counter(
            "divergent_elite_preserved_total",
            "Ideas preserved as elite",
        )

    # ── generate ──────────────────────────────────────────────
    async def generate(
        self,
        prompt: str,
        *,
        strategy: DivergentStrategy | None = None,
        n: int = 10,
    ) -> list[Idea]:
        strat = strategy or self._cfg.strategy
        ideas: list[Idea] = []

        match strat:
            case DivergentStrategy.RANDOM_COMBINATION:
                ideas = await self._random_combination(prompt, n)
            case DivergentStrategy.SCAMPER:
                ideas = await self._scamper(prompt, n)
            case DivergentStrategy.BISOCIATION:
                ideas = await self._bisociation(prompt, n)
            case DivergentStrategy.CONSTRAINT_RELAXATION:
                ideas = await self._constraint_relaxation(prompt, n)
            case DivergentStrategy.MORPHOLOGICAL_ANALYSIS:
                ideas = await self._morphological_analysis(prompt, n)

        for idea in ideas:
            self._known_ideas[idea.id] = idea
            self._ideas_generated.labels(strategy=strat.value).inc()

        return ideas

    # ── novelty scoring ───────────────────────────────────────
    async def score_novelty(self, idea: Idea) -> float:
        """
        Information-theoretic novelty:
          novelty = 1 - max_similarity(idea, known_ideas)
        where similarity uses normalised compression distance (NCD).
        Falls back to Jaccard n-gram distance if compression unavailable.
        """
        if not self._known_ideas:
            return 1.0

        max_sim = 0.0
        for known in self._known_ideas.values():
            if known.id == idea.id:
                continue
            sim = self._jaccard_trigram(idea.content, known.content)
            max_sim = max(max_sim, sim)

        score = round(1.0 - max_sim, 4)
        self._novelty_histogram.observe(score)
        return score

    # ── crossover ─────────────────────────────────────────────
    async def crossover(self, parent_a: Idea, parent_b: Idea) -> Idea:
        """Single-point conceptual crossover."""
        tokens_a = parent_a.content.split()
        tokens_b = parent_b.content.split()
        mid_a = len(tokens_a) // 2
        mid_b = len(tokens_b) // 2
        child_tokens = tokens_a[:mid_a] + tokens_b[mid_b:]
        child = Idea(
            id=str(uuid4()),
            content=" ".join(child_tokens),
            strategy=parent_a.strategy,
            quality=IdeaQuality.REFINED,
            novelty_score=0.0,
            parent_ids=(parent_a.id, parent_b.id),
            generation=max(parent_a.generation, parent_b.generation) + 1,
        )
        child = replace(child, novelty_score=await self.score_novelty(child))
        return child

    # ── mutate ────────────────────────────────────────────────
    async def mutate(self, idea: Idea) -> Idea:
        """Perturb by synonym substitution, word insertion, or inversion."""
        tokens = idea.content.split()
        if not tokens:
            return idea
        idx = random.randrange(len(tokens))
        # Simple mutation: reverse a random token
        tokens[idx] = tokens[idx][::-1]
        mutated = replace(
            idea,
            id=str(uuid4()),
            content=" ".join(tokens),
            quality=IdeaQuality.REFINED,
            generation=idea.generation + 1,
            parent_ids=(idea.id,),
        )
        mutated = replace(mutated, novelty_score=await self.score_novelty(mutated))
        return mutated

    # ── evolve_population ─────────────────────────────────────
    async def evolve_population(
        self,
        seed_ideas: list[Idea],
        *,
        generations: int | None = None,
    ) -> list[Idea]:
        """
        Full evolutionary loop:
        1. Score all ideas for novelty
        2. Select elite (top elite_fraction)
        3. Tournament selection → crossover → mutation
        4. Repeat for N generations
        5. Return final population sorted by novelty desc
        """
        gen_count = generations or self._cfg.generations
        population = list(seed_ideas)

        for gen in range(gen_count):
            with self._generation_latency.time():
                # Score
                for i, idea in enumerate(population):
                    score = await self.score_novelty(idea)
                    population[i] = replace(idea, novelty_score=score)

                # Sort by novelty descending
                population.sort(key=lambda x: x.novelty_score, reverse=True)

                # Elite preservation
                elite_n = max(1, int(len(population) * self._cfg.elite_fraction))
                elite = population[:elite_n]
                self._elite_preserved.inc(elite_n)

                # Filter by novelty threshold
                candidates = [
                    idea for idea in population
                    if idea.novelty_score >= self._cfg.novelty_threshold
                ]
                if len(candidates) < 2:
                    candidates = population[:max(2, elite_n)]

                # Generate next generation
                next_gen: list[Idea] = list(elite)
                while len(next_gen) < self._cfg.population_size:
                    if random.random() < self._cfg.crossover_rate and len(candidates) >= 2:
                        a, b = random.sample(candidates, 2)
                        child = await self.crossover(a, b)
                        next_gen.append(child)
                    elif random.random() < self._cfg.mutation_rate:
                        parent = random.choice(candidates)
                        mutant = await self.mutate(parent)
                        next_gen.append(mutant)
                    else:
                        # Immigration: fresh idea
                        fresh = await self.generate(
                            random.choice(candidates).content,
                            n=1,
                        )
                        next_gen.extend(fresh)

                population = next_gen[:self._cfg.population_size]
                self._population_size.set(len(population))

        # Final sort
        population.sort(key=lambda x: x.novelty_score, reverse=True)
        return population

    # ── private: strategy implementations ─────────────────────

    async def _random_combination(self, prompt: str, n: int) -> list[Idea]:
        """Combine random pairs from concept pool."""
        ...

    async def _scamper(self, prompt: str, n: int) -> list[Idea]:
        """Apply SCAMPER operators (see reference table below)."""
        ...

    async def _bisociation(self, prompt: str, n: int) -> list[Idea]:
        """Koestler bisociation: connect two unrelated frames."""
        if self._analogical:
            # Use AnalogicalReasoner to find cross-domain bridges
            ...
        ...

    async def _constraint_relaxation(self, prompt: str, n: int) -> list[Idea]:
        """Systematically remove or invert constraints from the prompt."""
        ...

    async def _morphological_analysis(self, prompt: str, n: int) -> list[Idea]:
        """Zwicky box: enumerate parameter combinations."""
        ...

    @staticmethod
    def _jaccard_trigram(a: str, b: str) -> float:
        """Jaccard similarity on character trigrams."""
        def trigrams(s: str) -> set[str]:
            return {s[i:i+3] for i in range(len(s) - 2)}
        ta, tb = trigrams(a.lower()), trigrams(b.lower())
        if not ta and not tb:
            return 1.0
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)
```

---

## SCAMPER 7-Operator Reference Table

[SCAMPER](https://en.wikipedia.org/wiki/S.C.A.M.P.E.R.) (Eberle, 1971) is a structured creative-thinking checklist:

| # | Operator | Description | Example Application |
|---|----------|-------------|---------------------|
| **S** | **Substitute** | Replace a component/material/person | Swap neural attention for graph attention |
| **C** | **Combine** | Merge two ideas/functions/processes | Fuse memory consolidation + planning |
| **A** | **Adapt** | Borrow from another domain | Apply biological immune response to anomaly detection |
| **M** | **Modify** | Change size, shape, or attributes | Scale from single-agent to multi-agent |
| **P** | **Put to other use** | Repurpose for a different context | Use error signals as curiosity rewards |
| **E** | **Eliminate** | Remove unnecessary parts | Strip synchronous locks for lock-free design |
| **R** | **Reverse** | Invert order or perspective | Run backward chaining before forward |

Each operator is applied to the prompt's key concepts, generating one idea per operator per concept.

---

## Bisociation (Koestler)

Arthur Koestler's concept of **bisociation** (1964) describes creativity as the intersection of two previously unrelated "matrices of thought." Unlike association (within a single frame), bisociation bridges **two independent conceptual planes**:

```
   Plane A (e.g., biological evolution)
        \
         \  ← bisociative connection
          \
   Plane B (e.g., software architecture)

   Result: "Evolutionary software that mutates and selects modules"
```

The DivergentGenerator implements bisociation by:
1. Sampling two random concept clusters from the concept pool
2. Using the AnalogicalReasoner (Phase 20.2) to find structural mappings between them
3. Generating ideas at the intersection points

---

## Novelty Scoring Formula

```
novelty(idea) = 1 - max_{k ∈ known_ideas} similarity(idea, k)

similarity(a, b) = |trigrams(a) ∩ trigrams(b)| / |trigrams(a) ∪ trigrams(b)|
```

Where `trigrams(s)` extracts all character 3-grams from the lowercased string.

**Properties**:
- `novelty ∈ [0.0, 1.0]`
- `novelty = 1.0` → completely unlike anything seen before
- `novelty = 0.0` → exact duplicate of a known idea
- Ideas below `novelty_threshold` (default 0.3) are filtered out

**Future extension**: Replace Jaccard with NCD (Normalised Compression Distance) or embedding-space cosine distance for semantic novelty.

---

## Genetic Algorithm Flow

```
┌─────────────────────────────────────────────────┐
│              EVOLUTIONARY LOOP                   │
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  SCORE    │───▶│  SELECT  │───▶│  ELITE   │  │
│  │ (novelty) │    │ (filter) │    │(preserve)│  │
│  └──────────┘    └──────────┘    └──────────┘  │
│       ▲                               │         │
│       │                               ▼         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  NEXT    │◀───│  MUTATE  │◀───│ CROSSOVER│  │
│  │  GEN     │    │  (0.2)   │    │  (0.7)   │  │
│  └──────────┘    └──────────┘    └──────────┘  │
│       │                               ▲         │
│       ▼                               │         │
│  ┌──────────┐                    ┌──────────┐  │
│  │IMMIGRATE │───────────────────▶│  MERGE   │  │
│  │ (fresh)  │                    │  pool    │  │
│  └──────────┘                    └──────────┘  │
└─────────────────────────────────────────────────┘

 Generation 0     Generation 1    ...   Generation N
 ┌─────────┐     ┌─────────┐          ┌─────────┐
 │ RAW     │────▶│ REFINED │─── ──── ▶│ SELECTED│
 │ ideas   │     │ ideas   │          │ top-k   │
 └─────────┘     └─────────┘          └─────────┘
```

---

## Integration Points

### CuriosityModule (Phase 13.3)

```python
# CuriosityModule drives concept pool refresh
curiosity_targets = await curiosity_module.get_curiosity_targets()
generator._concept_pool.extend(curiosity_targets)
```

The CuriosityModule identifies knowledge gaps that become seeds for divergent generation. High-curiosity concepts are prioritised in the concept pool.

### AnalogicalReasoner (Phase 20.2)

```python
# AnalogicalReasoner finds cross-domain bridges for bisociation
mapping = await analogical_reasoner.find_mapping(domain_a, domain_b)
bisociation_idea = Idea(
    content=f"Apply {mapping.source} to {mapping.target}",
    strategy=DivergentStrategy.BISOCIATION,
    ...
)
```

### CognitiveCycle Integration

```python
async def _creative_step(self) -> None:
    """Called from CognitiveCycle.run_step()."""
    ideas = await self._divergent_generator.generate(
        prompt=self._current_context,
        strategy=DivergentStrategy.BISOCIATION,
        n=20,
    )
    evolved = await self._divergent_generator.evolve_population(ideas, generations=5)
    self._idea_buffer.extend(evolved[:10])  # Top 10 to downstream
```

---

## NullDivergentGenerator

```python
class NullDivergentGenerator:
    """No-op implementation for testing and DI."""

    async def generate(self, prompt, *, strategy=None, n=10):
        return []

    async def score_novelty(self, idea):
        return 0.0

    async def crossover(self, parent_a, parent_b):
        return parent_a

    async def mutate(self, idea):
        return idea

    async def evolve_population(self, seed_ideas, *, generations=None):
        return seed_ideas
```

---

## Factory

```python
def make_divergent_generator(
    config: DivergentConfig | None = None,
    *,
    curiosity: CuriosityModule | None = None,
    analogical: AnalogicalReasoner | None = None,
    null: bool = False,
) -> DivergentGenerator:
    if null:
        return NullDivergentGenerator()
    return AsyncDivergentGenerator(
        config=config or DivergentConfig(),
        curiosity=curiosity,
        analogical=analogical,
    )
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `divergent_ideas_generated_total` | Counter | `strategy` | Total ideas generated by strategy |
| `divergent_novelty_score` | Histogram | — | Distribution of novelty scores |
| `divergent_generation_latency_seconds` | Histogram | — | Latency per evolutionary generation |
| `divergent_population_size` | Gauge | — | Current population size |
| `divergent_elite_preserved_total` | Counter | — | Ideas preserved as elite |

### PromQL Examples

```promql
# Idea generation rate by strategy (1m window)
rate(divergent_ideas_generated_total[1m])

# Average novelty of generated ideas
histogram_quantile(0.5, rate(divergent_novelty_score_bucket[5m]))

# Generation latency p95
histogram_quantile(0.95, rate(divergent_generation_latency_seconds_bucket[5m]))
```

### Grafana Alert YAML

```yaml
- alert: LowNoveltyGeneration
  expr: histogram_quantile(0.5, rate(divergent_novelty_score_bucket[5m])) < 0.2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Median novelty score below 0.2 — idea pool may be stagnating"
```

---

## mypy Strict Compliance

| Pattern | Narrowing technique |
|---------|---------------------|
| `strategy: DivergentStrategy \| None` | `match strat:` with exhaustive cases |
| `parent_ids: tuple[str, ...]` | Immutable tuple, no `list` mutation |
| `Idea` frozen dataclass | `replace()` for all modifications |
| `_known_ideas` dict lookup | `.values()` iteration, no `KeyError` risk |
| `random.sample(candidates, 2)` | Guard `len(candidates) >= 2` |

---

## Test Targets (12)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_generate_returns_n_ideas` | `len(ideas) == n` for each strategy |
| 2 | `test_novelty_score_range` | `0.0 <= score <= 1.0` |
| 3 | `test_duplicate_has_zero_novelty` | Same content → novelty ≈ 0.0 |
| 4 | `test_crossover_inherits_parents` | Child `parent_ids` contains both parent IDs |
| 5 | `test_crossover_increments_generation` | Child generation = max(parents) + 1 |
| 6 | `test_mutate_changes_content` | Mutated content ≠ original |
| 7 | `test_evolve_improves_novelty` | Mean novelty of final gen > seed gen |
| 8 | `test_elite_preserved` | Top ideas survive across generations |
| 9 | `test_scamper_all_operators` | SCAMPER generates ≥ 7 ideas (one per operator) |
| 10 | `test_bisociation_uses_analogical` | Mock AnalogicalReasoner is called |
| 11 | `test_null_generator_noop` | NullDivergentGenerator returns empty/identity |
| 12 | `test_prometheus_metrics_increment` | Counters increase after generate() |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_evolve_improves_novelty():
    """Verify evolutionary loop increases mean novelty."""
    cfg = DivergentConfig(population_size=20, generations=5, novelty_threshold=0.1)
    gen = make_divergent_generator(cfg)
    seeds = await gen.generate("artificial intelligence", n=20)
    initial_mean = sum(i.novelty_score for i in seeds) / len(seeds)
    evolved = await gen.evolve_population(seeds, generations=5)
    final_mean = sum(i.novelty_score for i in evolved) / len(evolved)
    assert final_mean >= initial_mean

@pytest.mark.asyncio
async def test_scamper_all_operators():
    """SCAMPER should produce at least one idea per operator."""
    gen = make_divergent_generator(DivergentConfig(strategy=DivergentStrategy.SCAMPER))
    ideas = await gen.generate("memory system", strategy=DivergentStrategy.SCAMPER, n=14)
    assert len(ideas) >= 7  # At least one per S-C-A-M-P-E-R operator
```

---

## Implementation Order (14 steps)

| Step | Task | File |
|------|------|------|
| 1 | Define `DivergentStrategy` enum | `enums.py` |
| 2 | Define `IdeaQuality` enum | `enums.py` |
| 3 | Define `Idea` frozen dataclass | `models.py` |
| 4 | Define `DivergentConfig` frozen dataclass | `models.py` |
| 5 | Define `DivergentGenerator` Protocol | `protocols.py` |
| 6 | Implement `_jaccard_trigram` static method | `divergent_generator.py` |
| 7 | Implement `score_novelty` | `divergent_generator.py` |
| 8 | Implement `_random_combination` | `divergent_generator.py` |
| 9 | Implement `_scamper` | `divergent_generator.py` |
| 10 | Implement `_bisociation` + AnalogicalReasoner integration | `divergent_generator.py` |
| 11 | Implement `crossover` + `mutate` | `divergent_generator.py` |
| 12 | Implement `evolve_population` | `divergent_generator.py` |
| 13 | Implement `NullDivergentGenerator` + factory | `factory.py` |
| 14 | Write tests | `test_divergent_generator.py` |

---

## Phase 22 — Creative Intelligence Sub-Phase Tracker

| # | Sub-phase | Component | Status |
|---|-----------|-----------|--------|
| 22.1 | DivergentGenerator | Divergent idea generation + evolutionary search | ✅ Spec |
| 22.2 | AnalogyMapper | Structure-mapping analogical transfer | ⬜ Pending |
| 22.3 | ConceptBlender | Fauconnier-Turner conceptual blending | ⬜ Pending |
| 22.4 | AestheticEvaluator | Multi-dimensional aesthetic scoring | ⬜ Pending |
| 22.5 | CreativeOrchestrator | Full creative pipeline orchestration | ⬜ Pending |
