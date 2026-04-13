# Phase 22.3 — ConceptBlender

> **Sub-phase**: 22.3 of 5 · **Layer**: Creative Intelligence & Generative Thinking  
> **Status**: ✅ Spec Complete  
> **Issue**: [#515](https://github.com/web3guru888/asi-build/issues/515)  
> **Depends on**: DivergentGenerator (22.1), AnalogyMapper (22.2)

---

## Overview

The **ConceptBlender** implements Fauconnier & Turner's (2002) **Conceptual Blending Theory** (also called Conceptual Integration Theory). It takes two or more mental spaces, finds cross-space mappings, and produces a **blended space** with emergent structure — properties that exist in the blend but not in either input space. This is the computational foundation for creative synthesis: metaphor, novel concepts, and inventive combinations.

### Design Rationale

Conceptual blending goes beyond analogy. While the AnalogyMapper (22.2) finds structural correspondences between domains, the ConceptBlender **creates something new** by:

1. **Composition** — projecting structure from both inputs into the blend
2. **Completion** — filling in background knowledge from long-term memory
3. **Elaboration** — running the blend as a mental simulation to discover emergent properties

This **CCE triple** (Composition-Completion-Elaboration) is the core creative operation.

---

## Enums

### BlendType

```python
class BlendType(str, Enum):
    """Classification of conceptual blend."""
    SIMPLEX      = "simplex"       # Frame + values (simple role filling)
    MIRROR       = "mirror"        # Same organising frame in both spaces
    SINGLE_SCOPE = "single_scope"  # One space provides organising frame
    DOUBLE_SCOPE = "double_scope"  # Both spaces contribute frame structure
```

### BlendQuality

```python
class BlendQuality(str, Enum):
    """Quality assessment of a blend."""
    INCOHERENT  = "incoherent"   # Blend has contradictions
    BASIC       = "basic"        # Composition only, no emergence
    EMERGENT    = "emergent"     # Has novel properties
    CREATIVE    = "creative"     # High emergence + coherence
    OPTIMAL     = "optimal"      # Passes all optimality constraints
```

---

## Data Classes

### MentalSpace

```python
@dataclass(frozen=True)
class MentalSpace:
    """A conceptual space with entities, properties, and relations."""
    name: str
    entities: frozenset[str]
    properties: dict[str, frozenset[str]]   # entity → set of properties
    relations: tuple[tuple[str, str, str], ...]  # (relation, entity1, entity2)
    frame: str = ""                          # Organising frame name
    metadata: dict[str, Any] = field(default_factory=dict)
```

### GenericSpace

```python
@dataclass(frozen=True)
class GenericSpace:
    """Abstract structure shared by input spaces."""
    roles: frozenset[str]                          # Abstract role names
    abstract_relations: tuple[tuple[str, str, str], ...]  # Abstract relational skeleton
```

### CrossSpaceMapping

```python
@dataclass(frozen=True)
class CrossSpaceMapping:
    """Mapping between elements of two mental spaces."""
    space_a_name: str
    space_b_name: str
    entity_map: dict[str, str]       # space_a entity → space_b entity
    relation_map: dict[str, str]     # space_a relation → space_b relation
    vital_relations: frozenset[str]  # Preserved vital relations (CAUSE, TIME, IDENTITY, ...)
```

### Blend

```python
@dataclass(frozen=True)
class Blend:
    """The blended conceptual space."""
    id: str                                  # UUID
    input_spaces: tuple[MentalSpace, ...]    # Input mental spaces
    generic_space: GenericSpace              # Shared abstract structure
    cross_space_mapping: CrossSpaceMapping   # How inputs relate
    blended_entities: frozenset[str]         # Entities in the blend
    blended_properties: dict[str, frozenset[str]]
    blended_relations: tuple[tuple[str, str, str], ...]
    emergent_properties: frozenset[str]      # Properties not in any input
    emergent_relations: tuple[tuple[str, str, str], ...]  # Novel relations
    blend_type: BlendType
    quality: BlendQuality
    coherence_score: float                   # [0.0, 1.0]
    novelty_score: float                     # [0.0, 1.0]
    created_at: float = field(default_factory=time.time)
```

### BlenderConfig

```python
@dataclass(frozen=True)
class BlenderConfig:
    """Configuration for conceptual blending."""
    max_blend_entities: int = 50             # Cap on blended entities
    min_coherence: float = 0.3               # Minimum coherence to accept
    elaboration_steps: int = 5               # Mental simulation iterations
    enable_completion: bool = True           # Use background knowledge
    enable_elaboration: bool = True          # Run mental simulation
    optimize_iterations: int = 3             # Blend optimisation passes
    timeout_s: float = 20.0                  # Per-blend timeout
```

---

## Protocol

```python
@runtime_checkable
class ConceptBlender(Protocol):
    """Blends mental spaces to create novel conceptual structures."""

    async def blend(
        self,
        space_a: MentalSpace,
        space_b: MentalSpace,
        *,
        generic_space: GenericSpace | None = None,
    ) -> Blend: ...

    async def detect_emergent_structure(
        self,
        blend: Blend,
    ) -> tuple[frozenset[str], tuple[tuple[str, str, str], ...]]: ...

    async def evaluate_blend(
        self,
        blend: Blend,
    ) -> BlendQuality: ...

    async def optimize_blend(
        self,
        blend: Blend,
        *,
        iterations: int | None = None,
    ) -> Blend: ...
```

---

## AsyncConceptBlender — Full Implementation

```python
class AsyncConceptBlender:
    """
    Production conceptual blending engine.

    Implements Fauconnier-Turner (2002) 4-space model:
      Input Space 1 ──┐
                       ├── Generic Space (shared structure)
      Input Space 2 ──┘
                       │
                       ▼
                  Blended Space (with emergent structure)

    Three core operations:
      1. Composition — selective projection from inputs
      2. Completion — pattern completion from background knowledge
      3. Elaboration — mental simulation to discover emergence
    """

    def __init__(
        self,
        config: BlenderConfig,
        divergent: DivergentGenerator | None = None,
        analogy_mapper: AnalogyMapper | None = None,
    ) -> None:
        self._cfg = config
        self._divergent = divergent
        self._mapper = analogy_mapper
        self._lock = asyncio.Lock()
        self._blend_history: deque[Blend] = deque(maxlen=200)

        # Prometheus metrics
        self._blends_created = Counter(
            "blender_blends_created_total",
            "Total blends created",
            ["blend_type"],
        )
        self._emergent_count = Counter(
            "blender_emergent_properties_total",
            "Emergent properties discovered",
        )
        self._coherence_histogram = Histogram(
            "blender_coherence_score",
            "Blend coherence score distribution",
            buckets=[0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0],
        )
        self._blend_latency = Histogram(
            "blender_blend_latency_seconds",
            "Time to produce a blend",
        )
        self._optimisation_rounds = Counter(
            "blender_optimisation_rounds_total",
            "Blend optimisation iterations executed",
        )

    # ── blend (core CCE pipeline) ─────────────────────────────
    async def blend(
        self,
        space_a: MentalSpace,
        space_b: MentalSpace,
        *,
        generic_space: GenericSpace | None = None,
    ) -> Blend:
        """
        4-step blending process:

        Step 1 — Generic space extraction:
          Find the shared abstract structure between inputs.
          If not provided, automatically infer using AnalogyMapper.

        Step 2 — Composition:
          Selectively project entities, properties, and relations
          from both input spaces into the blend. Cross-space mapping
          determines which elements are fused vs. kept separate.

        Step 3 — Completion:
          Fill in background knowledge: if the blend has a "journey"
          frame and an "agent", complete with "destination", "path", etc.
          Uses WorldModel (Phase 13.1) for background retrieval.

        Step 4 — Elaboration:
          Run the blend as a mental simulation for N steps.
          Each step may produce emergent properties — things that
          are true in the blend but not in either input.
        """
        with self._blend_latency.time():
            # Step 1: Generic space
            if generic_space is None:
                generic_space = await self._infer_generic_space(space_a, space_b)

            # Step 2: Composition
            cross_map = await self._compute_cross_space_mapping(space_a, space_b)
            blend_entities, blend_props, blend_rels = self._compose(
                space_a, space_b, cross_map,
            )

            # Step 3: Completion
            if self._cfg.enable_completion:
                blend_props, blend_rels = await self._complete(
                    blend_entities, blend_props, blend_rels, space_a, space_b,
                )

            # Step 4: Elaboration
            emergent_props: frozenset[str] = frozenset()
            emergent_rels: tuple[tuple[str, str, str], ...] = ()
            if self._cfg.enable_elaboration:
                emergent_props, emergent_rels = await self._elaborate(
                    blend_entities, blend_props, blend_rels,
                    steps=self._cfg.elaboration_steps,
                )
                self._emergent_count.inc(len(emergent_props) + len(emergent_rels))

            # Classify and score
            blend_type = self._classify_blend(space_a, space_b, cross_map)
            coherence = self._score_coherence(
                blend_entities, blend_props, blend_rels,
            )
            novelty = self._score_novelty(
                emergent_props, emergent_rels, space_a, space_b,
            )

            quality = self._assess_quality(coherence, novelty, emergent_props)

            result = Blend(
                id=str(uuid4()),
                input_spaces=(space_a, space_b),
                generic_space=generic_space,
                cross_space_mapping=cross_map,
                blended_entities=blend_entities,
                blended_properties=blend_props,
                blended_relations=tuple(blend_rels),
                emergent_properties=emergent_props,
                emergent_relations=emergent_rels,
                blend_type=blend_type,
                quality=quality,
                coherence_score=coherence,
                novelty_score=novelty,
            )

            self._blends_created.labels(blend_type=blend_type.value).inc()
            self._coherence_histogram.observe(coherence)
            self._blend_history.append(result)
            return result

    # ── detect_emergent_structure ──────────────────────────────
    async def detect_emergent_structure(
        self,
        blend: Blend,
    ) -> tuple[frozenset[str], tuple[tuple[str, str, str], ...]]:
        """
        Identify properties and relations in the blend that don't
        exist in any input space. These are the creative payoff.

        Detection algorithm:
        1. Collect all properties from all input spaces
        2. Subtract from blended properties → emergent properties
        3. Collect all relations from all input spaces
        4. Subtract from blended relations → emergent relations
        """
        input_props: set[str] = set()
        input_rels: set[tuple[str, str, str]] = set()
        for space in blend.input_spaces:
            for props in space.properties.values():
                input_props.update(props)
            input_rels.update(space.relations)

        all_blend_props: set[str] = set()
        for props in blend.blended_properties.values():
            all_blend_props.update(props)

        emergent_props = frozenset(all_blend_props - input_props)
        emergent_rels = tuple(
            r for r in blend.blended_relations if r not in input_rels
        )
        return emergent_props, emergent_rels

    # ── evaluate_blend ────────────────────────────────────────
    async def evaluate_blend(self, blend: Blend) -> BlendQuality:
        """Evaluate blend against Fauconnier-Turner optimality constraints."""
        return self._assess_quality(
            blend.coherence_score,
            blend.novelty_score,
            blend.emergent_properties,
        )

    # ── optimize_blend ────────────────────────────────────────
    async def optimize_blend(
        self,
        blend: Blend,
        *,
        iterations: int | None = None,
    ) -> Blend:
        """
        Iteratively improve a blend by:
        1. Removing incoherent relations (contradiction elimination)
        2. Re-running elaboration to find more emergence
        3. Pruning entities that don't participate in any relation
        """
        iters = iterations or self._cfg.optimize_iterations
        current = blend

        for _ in range(iters):
            self._optimisation_rounds.inc()
            # Remove contradictions
            clean_rels = self._remove_contradictions(current.blended_relations)
            # Re-elaborate
            new_emergent_props, new_emergent_rels = await self._elaborate(
                current.blended_entities,
                current.blended_properties,
                clean_rels,
                steps=2,
            )
            # Prune orphan entities
            active_entities = self._get_active_entities(clean_rels + list(new_emergent_rels))
            # Rebuild
            coherence = self._score_coherence(
                frozenset(active_entities),
                current.blended_properties,
                clean_rels + list(new_emergent_rels),
            )
            current = replace(
                current,
                blended_entities=frozenset(active_entities),
                blended_relations=tuple(clean_rels + list(new_emergent_rels)),
                emergent_properties=current.emergent_properties | new_emergent_props,
                emergent_relations=current.emergent_relations + new_emergent_rels,
                coherence_score=coherence,
                quality=self._assess_quality(
                    coherence, current.novelty_score,
                    current.emergent_properties | new_emergent_props,
                ),
            )

        return current

    # ── private methods ───────────────────────────────────────

    async def _infer_generic_space(self, a, b):
        """Use AnalogyMapper to find shared abstract structure."""
        if self._mapper:
            mappings = await self._mapper.map_analogy(
                RelationalStructure(a.name, a.entities, (), tuple(
                    Relation(r[0], (r[1], r[2])) for r in a.relations
                )),
                RelationalStructure(b.name, b.entities, (), tuple(
                    Relation(r[0], (r[1], r[2])) for r in b.relations
                )),
            )
            if mappings:
                ...  # Extract generic space from top mapping
        return GenericSpace(roles=frozenset(), abstract_relations=())

    async def _compute_cross_space_mapping(self, a, b):
        """Compute entity/relation mappings between input spaces."""
        ...

    def _compose(self, a, b, cross_map):
        """Selective projection from both spaces."""
        ...

    async def _complete(self, entities, props, rels, a, b):
        """Background knowledge completion."""
        ...

    async def _elaborate(self, entities, props, rels, *, steps):
        """Mental simulation to discover emergence."""
        ...

    def _classify_blend(self, a, b, cross_map) -> BlendType:
        """Determine blend type based on frame structure."""
        ...

    def _score_coherence(self, entities, props, rels) -> float:
        """Internal consistency of the blend."""
        ...

    def _score_novelty(self, emergent_props, emergent_rels, a, b) -> float:
        """Fraction of blend that is emergent."""
        ...

    def _assess_quality(self, coherence, novelty, emergent_props) -> BlendQuality:
        if coherence < 0.2:
            return BlendQuality.INCOHERENT
        if not emergent_props:
            return BlendQuality.BASIC
        if coherence >= 0.7 and novelty >= 0.5:
            return BlendQuality.CREATIVE
        if coherence >= 0.8 and novelty >= 0.7:
            return BlendQuality.OPTIMAL
        return BlendQuality.EMERGENT

    def _remove_contradictions(self, rels):
        ...

    def _get_active_entities(self, rels):
        ...
```

---

## Fauconnier-Turner 4-Space Model

```
┌──────────────────┐           ┌──────────────────┐
│   INPUT SPACE 1  │           │   INPUT SPACE 2   │
│                  │           │                   │
│  "surgeon"       │           │  "butcher"        │
│  "scalpel"       │           │  "cleaver"        │
│  "patient"       │           │  "carcass"        │
│  CUTS(surgeon,   │           │  CUTS(butcher,    │
│    patient)      │           │    carcass)       │
│  HEALS(surgeon,  │           │  CARELESS(butcher)│
│    patient)      │           │                   │
└────────┬─────────┘           └────────┬──────────┘
         │                              │
         │    ┌──────────────────┐      │
         └───▶│  GENERIC SPACE   │◀─────┘
              │                  │
              │  "agent"         │
              │  "instrument"    │
              │  "target"        │
              │  CUTS(agent,     │
              │    target)       │
              └────────┬─────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │     BLENDED SPACE        │
         │                          │
         │  "surgeon-butcher"       │
         │  "scalpel" (from I1)     │
         │  "patient" (from I1)     │
         │  CUTS(surgeon, patient)  │
         │  CARELESS(surgeon)  ← ✨ │  ← EMERGENT: surgeon is careless
         │  HARMS(surgeon, patient) │  ← EMERGENT: carelessness + cutting = harm
         │                          │
         │  🔑 "This surgeon is     │
         │     a butcher"           │
         └──────────────────────────┘
```

### Composition–Completion–Elaboration (CCE)

| Operation | Description | Example |
|-----------|-------------|---------|
| **Composition** | Selectively project elements from inputs into blend | "surgeon" + "careless" → blend has careless surgeon |
| **Completion** | Fill in background knowledge | Careless surgery → risk of harm (from medical knowledge) |
| **Elaboration** | Simulate the blend to discover emergence | "This surgeon is a butcher" = surgeon who harms patients |

### Fauconnier-Turner Optimality Constraints

| Constraint | Description |
|------------|-------------|
| **Integration** | The blend must form a tightly integrated scene |
| **Topology** | Relations in the blend should mirror input relations |
| **Web** | Maintain connections back to input spaces |
| **Unpacking** | Must be possible to reconstruct inputs from blend |
| **Relevance** | Blend elements must be relevant to the purpose |
| **Good reason** | Every element in the blend should have a motivated source |

---

## Integration Points

### DivergentGenerator (Phase 22.1)

```python
# DivergentGenerator provides raw ideas → ConceptBlender fuses them
ideas = await divergent_gen.generate(prompt, n=10)
for i in range(0, len(ideas), 2):
    space_a = self._idea_to_mental_space(ideas[i])
    space_b = self._idea_to_mental_space(ideas[i+1])
    blend = await blender.blend(space_a, space_b)
```

### AnalogyMapper (Phase 22.2)

```python
# AnalogyMapper provides cross-space mappings for blending
mapping = await analogy_mapper.map_analogy(source_struct, target_struct)
cross_map = CrossSpaceMapping(
    space_a_name=source.name,
    space_b_name=target.name,
    entity_map=mapping.entity_map,
    relation_map=mapping.relation_map,
    vital_relations=frozenset({"CAUSE", "IDENTITY"}),
)
blend = await blender.blend(space_a, space_b, generic_space=generic)
```

---

## NullConceptBlender

```python
class NullConceptBlender:
    """No-op implementation for testing and DI."""

    async def blend(self, space_a, space_b, *, generic_space=None):
        return Blend(
            id="null", input_spaces=(space_a, space_b),
            generic_space=GenericSpace(frozenset(), ()),
            cross_space_mapping=CrossSpaceMapping("", "", {}, {}, frozenset()),
            blended_entities=frozenset(), blended_properties={},
            blended_relations=(), emergent_properties=frozenset(),
            emergent_relations=(), blend_type=BlendType.SIMPLEX,
            quality=BlendQuality.BASIC, coherence_score=0.0, novelty_score=0.0,
        )

    async def detect_emergent_structure(self, blend):
        return frozenset(), ()

    async def evaluate_blend(self, blend):
        return BlendQuality.BASIC

    async def optimize_blend(self, blend, *, iterations=None):
        return blend
```

---

## Factory

```python
def make_concept_blender(
    config: BlenderConfig | None = None,
    *,
    divergent: DivergentGenerator | None = None,
    analogy_mapper: AnalogyMapper | None = None,
    null: bool = False,
) -> ConceptBlender:
    if null:
        return NullConceptBlender()
    return AsyncConceptBlender(
        config=config or BlenderConfig(),
        divergent=divergent,
        analogy_mapper=analogy_mapper,
    )
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `blender_blends_created_total` | Counter | `blend_type` | Blends created by type |
| `blender_emergent_properties_total` | Counter | — | Emergent properties discovered |
| `blender_coherence_score` | Histogram | — | Blend coherence distribution |
| `blender_blend_latency_seconds` | Histogram | — | Time to produce a blend |
| `blender_optimisation_rounds_total` | Counter | — | Optimisation iterations |

### PromQL Examples

```promql
# Blend creation rate by type
rate(blender_blends_created_total[5m])

# Average emergent properties per minute
rate(blender_emergent_properties_total[1m])

# Coherence p50
histogram_quantile(0.5, rate(blender_coherence_score_bucket[5m]))
```

### Grafana Alert YAML

```yaml
- alert: LowBlendCoherence
  expr: histogram_quantile(0.5, rate(blender_coherence_score_bucket[5m])) < 0.2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Median blend coherence below 0.2 — blends may be incoherent"
```

---

## mypy Strict Compliance

| Pattern | Narrowing technique |
|---------|---------------------|
| `generic_space: GenericSpace \| None` | `if generic_space is None: ... = await self._infer_generic_space()` |
| `frozenset[str]` entities | Immutable, safe for frozen dataclass |
| `dict[str, frozenset[str]]` properties | Nested immutable values |
| `tuple[tuple[str, str, str], ...]` relations | Immutable relation triples |
| `deque[Blend]` history | Bounded `maxlen=200` |

---

## Test Targets (12)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_blend_basic` | Blend produced with non-empty entities |
| 2 | `test_composition_projects_both` | Blend entities ⊇ subset of both inputs |
| 3 | `test_emergent_detection` | Emergent properties not in any input |
| 4 | `test_coherence_range` | `0.0 <= coherence <= 1.0` |
| 5 | `test_incoherent_classified` | Low-coherence blend → INCOHERENT quality |
| 6 | `test_creative_classification` | High coherence + novelty → CREATIVE |
| 7 | `test_optimize_improves_coherence` | Post-optimisation coherence ≥ pre |
| 8 | `test_double_scope_blend` | Both frames contribute → DOUBLE_SCOPE type |
| 9 | `test_elaboration_discovers_emergence` | Elaboration steps increase emergent count |
| 10 | `test_analogy_mapper_integration` | Mock AnalogyMapper used for generic space |
| 11 | `test_null_blender_noop` | NullConceptBlender returns default blend |
| 12 | `test_prometheus_metrics` | Counters update after blend() |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_emergent_detection():
    """Emergent properties should not exist in any input space."""
    space_a = MentalSpace(
        name="fire", entities=frozenset({"flame", "heat"}),
        properties={"flame": frozenset({"hot", "bright"})},
        relations=(("PRODUCES", "flame", "heat"),),
    )
    space_b = MentalSpace(
        name="water", entities=frozenset({"steam", "liquid"}),
        properties={"steam": frozenset({"hot", "gaseous"})},
        relations=(("PRODUCES", "liquid", "steam"),),
    )
    blender = make_concept_blender(BlenderConfig(enable_elaboration=True))
    blend = await blender.blend(space_a, space_b)
    emergent_p, emergent_r = await blender.detect_emergent_structure(blend)
    # Emergent properties should not be in either input
    input_props = {"hot", "bright", "gaseous"}
    assert not (emergent_p & input_props)

@pytest.mark.asyncio
async def test_optimize_improves_coherence():
    """Optimisation should not decrease coherence."""
    blender = make_concept_blender()
    space_a = MentalSpace("a", frozenset({"x"}), {}, ())
    space_b = MentalSpace("b", frozenset({"y"}), {}, ())
    blend = await blender.blend(space_a, space_b)
    optimized = await blender.optimize_blend(blend, iterations=3)
    assert optimized.coherence_score >= blend.coherence_score
```

---

## Implementation Order (14 steps)

| Step | Task | File |
|------|------|------|
| 1 | Define `BlendType` enum | `enums.py` |
| 2 | Define `BlendQuality` enum | `enums.py` |
| 3 | Define `MentalSpace` frozen dataclass | `models.py` |
| 4 | Define `GenericSpace`, `CrossSpaceMapping` frozen dataclasses | `models.py` |
| 5 | Define `Blend` frozen dataclass | `models.py` |
| 6 | Define `BlenderConfig` frozen dataclass | `models.py` |
| 7 | Define `ConceptBlender` Protocol | `protocols.py` |
| 8 | Implement `_compose` (selective projection) | `concept_blender.py` |
| 9 | Implement `_complete` (background knowledge) | `concept_blender.py` |
| 10 | Implement `_elaborate` (mental simulation) | `concept_blender.py` |
| 11 | Implement `detect_emergent_structure` | `concept_blender.py` |
| 12 | Implement `optimize_blend` | `concept_blender.py` |
| 13 | Implement `NullConceptBlender` + factory | `factory.py` |
| 14 | Write tests | `test_concept_blender.py` |

---

## Phase 22 — Creative Intelligence Sub-Phase Tracker

| # | Sub-phase | Component | Status |
|---|-----------|-----------|--------|
| 22.1 | DivergentGenerator | Divergent idea generation + evolutionary search | ✅ Spec |
| 22.2 | AnalogyMapper | Structure-mapping analogical transfer | ✅ Spec |
| 22.3 | ConceptBlender | Fauconnier-Turner conceptual blending | ✅ Spec |
| 22.4 | AestheticEvaluator | Multi-dimensional aesthetic scoring | ⬜ Pending |
| 22.5 | CreativeOrchestrator | Full creative pipeline orchestration | ⬜ Pending |
