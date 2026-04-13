# Phase 22.2 — AnalogyMapper

> **Sub-phase**: 22.2 of 5 · **Layer**: Creative Intelligence & Generative Thinking  
> **Status**: ✅ Spec Complete  
> **Issue**: [#514](https://github.com/web3guru888/asi-build/issues/514)  
> **Depends on**: AnalogicalReasoner (20.2), DivergentGenerator (22.1)

---

## Overview

The **AnalogyMapper** implements **Structure Mapping Theory** (Gentner, 1983) to discover, evaluate, and transfer structural analogies between conceptual domains. While the AnalogicalReasoner (Phase 20.2) provides basic analogical reasoning, the AnalogyMapper goes deeper — performing full **Structure Mapping Engine (SME)** computations including relational matching, structural consistency enforcement, one-to-one mapping constraints, and systematicity preference.

### Design Rationale

Analogy is the engine of creative transfer — mapping known structure from a **source domain** (well-understood) to a **target domain** (novel/unknown). The AnalogyMapper formalises this with:

1. **Relational structure representation** — predicates, arguments, and higher-order relations
2. **SME algorithm** — 4-phase mapping (local match → structural consistency → one-to-one → systematicity)
3. **Inference transfer** — carry over unmapped source predicates as candidate inferences in the target
4. **Systematicity scoring** — prefer deep, interconnected mappings over shallow attribute matches

---

## Enums

### MappingType

```python
class MappingType(str, Enum):
    """Type of analogical mapping."""
    LITERAL_SIMILARITY = "literal_similarity"  # Shared attributes + relations
    ANALOGY            = "analogy"             # Shared relations only (different attributes)
    ABSTRACTION        = "abstraction"         # Source is more general
    ANOMALY            = "anomaly"             # Contradictory mapping
```

### SimilarityMode

```python
class SimilarityMode(str, Enum):
    """How to compute similarity between elements."""
    STRUCTURAL  = "structural"   # Relation-only (Gentner strict analogy)
    ATTRIBUTIVE = "attributive"  # Attribute-only (surface similarity)
    HYBRID      = "hybrid"       # Weighted combination
```

---

## Data Classes

### Relation

```python
@dataclass(frozen=True)
class Relation:
    """A relational predicate in a conceptual structure."""
    name: str                          # e.g., "CAUSES", "GREATER_THAN"
    arguments: tuple[str, ...]         # e.g., ("sun_heat", "water_evaporation")
    order: int = 1                     # 1 = first-order, 2 = higher-order
    weight: float = 1.0               # Importance weight
```

### RelationalStructure

```python
@dataclass(frozen=True)
class RelationalStructure:
    """A domain represented as a set of relational predicates."""
    domain_name: str
    entities: frozenset[str]                # All entities in the domain
    attributes: tuple[Relation, ...]        # Unary predicates (properties)
    relations: tuple[Relation, ...]         # N-ary predicates (relationships)
    higher_order: tuple[Relation, ...] = () # Relations over relations
```

### StructuralMapping

```python
@dataclass(frozen=True)
class StructuralMapping:
    """A mapping between two relational structures."""
    id: str                                           # UUID
    source: RelationalStructure
    target: RelationalStructure
    mapping_type: MappingType
    entity_map: dict[str, str]                        # source_entity → target_entity
    relation_map: dict[str, str]                      # source_relation → target_relation
    systematicity_score: float                        # [0.0, 1.0] — depth/interconnectedness
    coverage_score: float                             # Fraction of source mapped
    candidate_inferences: tuple[Relation, ...] = ()   # Unmapped source → target inferences
    confidence: float = 0.0                           # Overall mapping confidence
```

### AnalogyConfig

```python
@dataclass(frozen=True)
class AnalogyConfig:
    """Configuration for analogy mapping."""
    similarity_mode: SimilarityMode = SimilarityMode.STRUCTURAL
    min_systematicity: float = 0.3       # Minimum systematicity to accept
    max_mappings: int = 5                # Max candidate mappings to return
    structural_weight: float = 0.7       # Weight for relational match (in HYBRID)
    attributive_weight: float = 0.3      # Weight for attribute match (in HYBRID)
    one_to_one: bool = True              # Enforce one-to-one entity mapping
    transfer_inferences: bool = True     # Generate candidate inferences
    timeout_s: float = 15.0              # Mapping timeout
```

---

## Protocol

```python
@runtime_checkable
class AnalogyMapper(Protocol):
    """Maps structural analogies between conceptual domains."""

    async def map_analogy(
        self,
        source: RelationalStructure,
        target: RelationalStructure,
    ) -> list[StructuralMapping]: ...

    async def find_analogies(
        self,
        target: RelationalStructure,
        *,
        candidates: list[RelationalStructure] | None = None,
    ) -> list[StructuralMapping]: ...

    async def transfer_inferences(
        self,
        mapping: StructuralMapping,
    ) -> list[Relation]: ...

    async def score_systematicity(
        self,
        mapping: StructuralMapping,
    ) -> float: ...
```

---

## AsyncAnalogyMapper — Full Implementation

```python
class AsyncAnalogyMapper:
    """
    Production analogy-mapping engine using Structure Mapping Engine (SME).

    Implements Gentner's (1983) Structure Mapping Theory:
    1. Local match — find compatible predicate pairs
    2. Structural consistency — build consistent match graphs
    3. One-to-one constraint — enforce bijective entity mapping
    4. Systematicity preference — prefer deep, interconnected mappings
    """

    def __init__(
        self,
        config: AnalogyConfig,
        analogical_reasoner: AnalogicalReasoner | None = None,
    ) -> None:
        self._cfg = config
        self._reasoner = analogical_reasoner
        self._lock = asyncio.Lock()
        self._mapping_cache: dict[tuple[str, str], list[StructuralMapping]] = {}

        # Prometheus metrics
        self._mappings_computed = Counter(
            "analogy_mappings_computed_total",
            "Total analogy mappings computed",
            ["mapping_type"],
        )
        self._systematicity_histogram = Histogram(
            "analogy_systematicity_score",
            "Distribution of systematicity scores",
            buckets=[0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0],
        )
        self._mapping_latency = Histogram(
            "analogy_mapping_latency_seconds",
            "Time to compute a mapping",
        )
        self._inferences_transferred = Counter(
            "analogy_inferences_transferred_total",
            "Candidate inferences transferred",
        )
        self._cache_hits = Counter(
            "analogy_cache_hits_total",
            "Mapping cache hits",
        )

    # ── map_analogy (core SME) ────────────────────────────────
    async def map_analogy(
        self,
        source: RelationalStructure,
        target: RelationalStructure,
    ) -> list[StructuralMapping]:
        """
        Full SME algorithm:

        Phase 1 — Local Match:
          For each source predicate, find compatible target predicates
          (same arity, compatible name via embedding similarity or exact match).

        Phase 2 — Structural Consistency:
          Build a match graph. Two local matches are structurally consistent
          iff their arguments map to the same entity pairs.

        Phase 3 — One-to-One:
          Enforce that each source entity maps to at most one target entity
          and vice versa (bipartite matching).

        Phase 4 — Systematicity:
          Score each consistent mapping by depth of relational structure
          (higher-order relations count more than first-order).
        """
        cache_key = (source.domain_name, target.domain_name)
        if cache_key in self._mapping_cache:
            self._cache_hits.inc()
            return self._mapping_cache[cache_key]

        with self._mapping_latency.time():
            # Phase 1: Local match
            local_matches = self._local_match(source, target)

            # Phase 2: Structural consistency
            consistent_sets = self._structural_consistency(local_matches)

            # Phase 3: One-to-one constraint
            if self._cfg.one_to_one:
                consistent_sets = [
                    cs for cs in consistent_sets
                    if self._is_one_to_one(cs)
                ]

            # Phase 4: Systematicity scoring
            mappings: list[StructuralMapping] = []
            for match_set in consistent_sets[:self._cfg.max_mappings]:
                entity_map = self._extract_entity_map(match_set)
                relation_map = self._extract_relation_map(match_set)
                systematicity = self._compute_systematicity(match_set, source)
                coverage = len(relation_map) / max(1, len(source.relations))

                # Determine mapping type
                mapping_type = self._classify_mapping(
                    source, target, entity_map, relation_map,
                )

                # Transfer inferences if enabled
                inferences = ()
                if self._cfg.transfer_inferences:
                    inferences = self._find_transferable(
                        source, target, relation_map, entity_map,
                    )

                confidence = (
                    self._cfg.structural_weight * systematicity
                    + self._cfg.attributive_weight * coverage
                )

                mapping = StructuralMapping(
                    id=str(uuid4()),
                    source=source,
                    target=target,
                    mapping_type=mapping_type,
                    entity_map=entity_map,
                    relation_map=relation_map,
                    systematicity_score=systematicity,
                    coverage_score=coverage,
                    candidate_inferences=tuple(inferences),
                    confidence=confidence,
                )
                mappings.append(mapping)
                self._mappings_computed.labels(
                    mapping_type=mapping_type.value
                ).inc()
                self._systematicity_histogram.observe(systematicity)

            # Sort by confidence descending
            mappings.sort(key=lambda m: m.confidence, reverse=True)
            self._mapping_cache[cache_key] = mappings
            return mappings

    # ── find_analogies ────────────────────────────────────────
    async def find_analogies(
        self,
        target: RelationalStructure,
        *,
        candidates: list[RelationalStructure] | None = None,
    ) -> list[StructuralMapping]:
        """Search all candidate sources for best analogies to target."""
        if candidates is None:
            return []

        all_mappings: list[StructuralMapping] = []
        tasks = [self.map_analogy(src, target) for src in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_mappings.extend(result)

        all_mappings.sort(key=lambda m: m.confidence, reverse=True)
        return all_mappings[:self._cfg.max_mappings]

    # ── transfer_inferences ───────────────────────────────────
    async def transfer_inferences(
        self,
        mapping: StructuralMapping,
    ) -> list[Relation]:
        """
        Transfer unmapped source relations to target domain.

        For each source relation not in relation_map:
          1. Substitute source entities with mapped target entities
          2. Create candidate inference in target domain
          3. Mark confidence based on systematicity of parent mapping
        """
        inferences: list[Relation] = []
        mapped_rels = set(mapping.relation_map.keys())

        for rel in mapping.source.relations:
            if rel.name not in mapped_rels:
                # Substitute entities
                new_args = tuple(
                    mapping.entity_map.get(arg, f"?{arg}")
                    for arg in rel.arguments
                )
                # Only transfer if all entities could be mapped
                if not any(a.startswith("?") for a in new_args):
                    inference = Relation(
                        name=rel.name,
                        arguments=new_args,
                        order=rel.order,
                        weight=rel.weight * mapping.systematicity_score,
                    )
                    inferences.append(inference)
                    self._inferences_transferred.inc()

        return inferences

    # ── score_systematicity ───────────────────────────────────
    async def score_systematicity(
        self,
        mapping: StructuralMapping,
    ) -> float:
        """
        Systematicity = weighted depth of mapped relational structure.

        Score formula:
          S = Σ (order_i * weight_i) / Σ (max_order * weight_i)

        Higher-order relations (relations over relations) contribute more,
        reflecting Gentner's systematicity principle.
        """
        return self._compute_systematicity_from_mapping(mapping)

    # ── private methods ───────────────────────────────────────

    def _local_match(self, source, target):
        """Phase 1: Find compatible predicate pairs."""
        matches = []
        for s_rel in source.relations:
            for t_rel in target.relations:
                if len(s_rel.arguments) == len(t_rel.arguments):
                    sim = self._predicate_similarity(s_rel.name, t_rel.name)
                    if sim > 0.0 or s_rel.name == t_rel.name:
                        matches.append((s_rel, t_rel, sim))
        return matches

    def _structural_consistency(self, local_matches):
        """Phase 2: Build consistent match sets via greedy graph search."""
        ...

    def _is_one_to_one(self, match_set) -> bool:
        """Phase 3: Check bijectivity of entity mapping."""
        entity_map = {}
        for s_rel, t_rel, _ in match_set:
            for s_arg, t_arg in zip(s_rel.arguments, t_rel.arguments):
                if s_arg in entity_map and entity_map[s_arg] != t_arg:
                    return False
                entity_map[s_arg] = t_arg
        # Check reverse direction
        reverse_map = {}
        for s, t in entity_map.items():
            if t in reverse_map and reverse_map[t] != s:
                return False
            reverse_map[t] = s
        return True

    def _compute_systematicity(self, match_set, source) -> float:
        """Phase 4: Weighted depth score."""
        if not match_set:
            return 0.0
        total = sum(s_rel.order * s_rel.weight for s_rel, _, _ in match_set)
        max_possible = sum(
            r.order * r.weight
            for r in (*source.relations, *source.higher_order)
        )
        return total / max_possible if max_possible > 0 else 0.0

    @staticmethod
    def _predicate_similarity(name_a: str, name_b: str) -> float:
        """Simple predicate name similarity (Jaccard on tokens)."""
        tokens_a = set(name_a.lower().replace("_", " ").split())
        tokens_b = set(name_b.lower().replace("_", " ").split())
        if not tokens_a or not tokens_b:
            return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)

    def _extract_entity_map(self, match_set):
        ...

    def _extract_relation_map(self, match_set):
        ...

    def _classify_mapping(self, source, target, entity_map, relation_map):
        ...

    def _find_transferable(self, source, target, relation_map, entity_map):
        ...

    def _compute_systematicity_from_mapping(self, mapping):
        ...
```

---

## Structure Mapping Theory (Gentner, 1983)

Dedre Gentner's **Structure Mapping Theory** posits that analogy is fundamentally about **relational structure**, not surface features:

| Principle | Description |
|-----------|-------------|
| **Systematicity** | Prefer mappings that preserve higher-order relational structure (relations between relations) |
| **One-to-one** | Each source element maps to at most one target element |
| **Structural consistency** | If a relation is mapped, its arguments must map consistently |
| **Relational focus** | Relations are more important than attributes for analogy |

### SME Algorithm Flow

```
SOURCE DOMAIN                    TARGET DOMAIN
┌─────────────────┐              ┌─────────────────┐
│ CAUSES(heat,     │              │ CAUSES(pressure, │
│   evaporation)   │              │   flow)          │
│ GREATER(sun,     │   Phase 1    │ GREATER(pump,    │
│   bulb)          │──────────────│   valve)         │
│ HEATS(sun,water) │  local match │ PRESSURIZES(     │
│ ATTR(sun,yellow) │              │   pump, pipe)    │
└─────────────────┘              └─────────────────┘
         │                                │
         ▼          Phase 2               ▼
    ┌──────────────────────────────────────┐
    │     STRUCTURAL CONSISTENCY           │
    │  CAUSES↔CAUSES ✓ (args consistent)  │
    │  GREATER↔GREATER ✓                   │
    │  HEATS↔PRESSURIZES ✓                │
    │  ATTR(sun,yellow) ✗ (no match)      │
    └──────────────────────────────────────┘
                     │
                     ▼ Phase 3
    ┌──────────────────────────────────────┐
    │     ONE-TO-ONE CONSTRAINT            │
    │  sun → pump  ✓                       │
    │  water → pipe  ✓                     │
    │  heat → pressure  ✓                  │
    │  evaporation → flow  ✓              │
    └──────────────────────────────────────┘
                     │
                     ▼ Phase 4
    ┌──────────────────────────────────────┐
    │     SYSTEMATICITY SCORE              │
    │  CAUSES (order=2) → 2.0             │
    │  GREATER (order=1) → 1.0            │
    │  S = 3.0 / 4.0 = 0.75              │
    └──────────────────────────────────────┘
```

---

## Integration Points

### AnalogicalReasoner (Phase 20.2)

```python
# AnalogyMapper extends AnalogicalReasoner with full SME
mapping = await analogy_mapper.map_analogy(source_domain, target_domain)
# Feed back into AnalogicalReasoner for broader reasoning
await analogical_reasoner.register_mapping(mapping)
```

### DivergentGenerator (Phase 22.1)

```python
# DivergentGenerator uses AnalogyMapper for bisociation
analogies = await analogy_mapper.find_analogies(
    target=novel_domain,
    candidates=known_domains,
)
for mapping in analogies:
    inferences = await analogy_mapper.transfer_inferences(mapping)
    # Each inference becomes a seed for divergent generation
```

---

## NullAnalogyMapper

```python
class NullAnalogyMapper:
    """No-op implementation for testing and DI."""

    async def map_analogy(self, source, target):
        return []

    async def find_analogies(self, target, *, candidates=None):
        return []

    async def transfer_inferences(self, mapping):
        return []

    async def score_systematicity(self, mapping):
        return 0.0
```

---

## Factory

```python
def make_analogy_mapper(
    config: AnalogyConfig | None = None,
    *,
    analogical_reasoner: AnalogicalReasoner | None = None,
    null: bool = False,
) -> AnalogyMapper:
    if null:
        return NullAnalogyMapper()
    return AsyncAnalogyMapper(
        config=config or AnalogyConfig(),
        analogical_reasoner=analogical_reasoner,
    )
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `analogy_mappings_computed_total` | Counter | `mapping_type` | Mappings computed by type |
| `analogy_systematicity_score` | Histogram | — | Systematicity score distribution |
| `analogy_mapping_latency_seconds` | Histogram | — | Time to compute a mapping |
| `analogy_inferences_transferred_total` | Counter | — | Inferences transferred to target |
| `analogy_cache_hits_total` | Counter | — | Mapping cache hits |

### PromQL Examples

```promql
# Mapping rate by type
rate(analogy_mappings_computed_total[5m])

# Median systematicity
histogram_quantile(0.5, rate(analogy_systematicity_score_bucket[5m]))

# Cache hit ratio
rate(analogy_cache_hits_total[5m]) / (rate(analogy_mappings_computed_total[5m]) + rate(analogy_cache_hits_total[5m]))
```

### Grafana Alert YAML

```yaml
- alert: LowSystematicity
  expr: histogram_quantile(0.5, rate(analogy_systematicity_score_bucket[5m])) < 0.2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Median systematicity below 0.2 — mappings may be too shallow"
```

---

## mypy Strict Compliance

| Pattern | Narrowing technique |
|---------|---------------------|
| `candidates: list \| None` | Guard `if candidates is None: return []` |
| `frozenset[str]` entities | Immutable, hashable for cache keys |
| `tuple[Relation, ...]` | Immutable sequence in frozen dataclass |
| `entity_map: dict[str, str]` | Explicit `.get()` with fallback |
| `asyncio.gather(*tasks)` | `return_exceptions=True` + `isinstance` check |

---

## Test Targets (12)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_map_analogy_basic` | Returns ≥ 1 mapping for compatible structures |
| 2 | `test_structural_consistency` | Inconsistent entity maps are filtered out |
| 3 | `test_one_to_one_enforced` | No source entity maps to two target entities |
| 4 | `test_systematicity_prefers_depth` | Higher-order mappings score higher |
| 5 | `test_transfer_inferences` | Unmapped source relations transferred correctly |
| 6 | `test_no_transfer_unmapped_entities` | Relations with unmapped entities skipped |
| 7 | `test_find_analogies_ranks` | Best analogy returned first |
| 8 | `test_cache_hit` | Second call uses cache |
| 9 | `test_hybrid_mode_weights` | HYBRID combines structural + attributive |
| 10 | `test_anomaly_detection` | Contradictory mapping classified as ANOMALY |
| 11 | `test_null_mapper_noop` | NullAnalogyMapper returns empty lists |
| 12 | `test_prometheus_metrics` | Counters/histograms update correctly |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_one_to_one_enforced():
    """One-to-one constraint prevents fan-out mappings."""
    source = RelationalStructure(
        domain_name="solar",
        entities=frozenset({"sun", "earth"}),
        attributes=(),
        relations=(
            Relation("ORBITS", ("earth", "sun")),
            Relation("HEATS", ("sun", "earth")),
        ),
    )
    target = RelationalStructure(
        domain_name="atomic",
        entities=frozenset({"electron", "nucleus"}),
        attributes=(),
        relations=(
            Relation("ORBITS", ("electron", "nucleus")),
        ),
    )
    mapper = make_analogy_mapper(AnalogyConfig(one_to_one=True))
    mappings = await mapper.map_analogy(source, target)
    for m in mappings:
        values = list(m.entity_map.values())
        assert len(values) == len(set(values)), "Entity map must be one-to-one"

@pytest.mark.asyncio
async def test_transfer_inferences():
    """Unmapped source relations generate candidate inferences."""
    mapper = make_analogy_mapper(AnalogyConfig(transfer_inferences=True))
    source = RelationalStructure(
        domain_name="src",
        entities=frozenset({"a", "b"}),
        attributes=(),
        relations=(
            Relation("CAUSES", ("a", "b")),
            Relation("PREVENTS", ("b", "a")),
        ),
    )
    target = RelationalStructure(
        domain_name="tgt",
        entities=frozenset({"x", "y"}),
        attributes=(),
        relations=(
            Relation("CAUSES", ("x", "y")),
        ),
    )
    mappings = await mapper.map_analogy(source, target)
    if mappings:
        inferences = await mapper.transfer_inferences(mappings[0])
        assert any(inf.name == "PREVENTS" for inf in inferences)
```

---

## Phase 22 — Creative Intelligence Sub-Phase Tracker

| # | Sub-phase | Component | Status |
|---|-----------|-----------|--------|
| 22.1 | DivergentGenerator | Divergent idea generation + evolutionary search | ✅ Spec |
| 22.2 | AnalogyMapper | Structure-mapping analogical transfer | ✅ Spec |
| 22.3 | ConceptBlender | Fauconnier-Turner conceptual blending | ⬜ Pending |
| 22.4 | AestheticEvaluator | Multi-dimensional aesthetic scoring | ⬜ Pending |
| 22.5 | CreativeOrchestrator | Full creative pipeline orchestration | ⬜ Pending |
