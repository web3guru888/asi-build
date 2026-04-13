# Phase 26.3 — KnowledgeCompiler: Declarative-to-Operational Knowledge Compilation

> **Issue**: [#580](https://github.com/web3guru888/asi-build/issues/580) | **S&T**: [#587](https://github.com/web3guru888/asi-build/discussions/587) | **Q&A**: [#588](https://github.com/web3guru888/asi-build/discussions/588) | **Planning**: [#577](https://github.com/web3guru888/asi-build/discussions/577)

## Overview

`KnowledgeCompiler` compiles declarative knowledge into efficient operational forms. Implements knowledge compilation theory from ACT-R (Anderson 1993), production rule chunking from Soar (Laird et al. 1987), and compilation complexity theory (Darwiche & Marquis 2002).

## Theoretical Background

### ACT-R Compilation (Anderson 1993)
In ACT-R, frequently accessed declarative facts are compiled into production rules — direct condition→action mappings that bypass the retrieval bottleneck. This mirrors how humans develop expertise: novices reason from first principles; experts apply compiled patterns.

### Soar Chunking (Laird et al. 1987)
Soar compiles every goal resolution into a chunk (production rule). When the same subgoal is encountered again, the chunk fires directly, avoiding re-derivation. Explanation-based generalization creates rules that are more general than the specific episode.

## Data Structures

### CompilationStrategy Enum

| Value | Description | When to Use |
|-------|-------------|-------------|
| `FREQUENCY` | Compile most frequently accessed | Stable knowledge base |
| `RECENCY` | Compile most recently used | Dynamic, rapidly changing KB |
| `UTILITY` | Compile by expected utility (speedup) | Performance-critical |
| `HYBRID` | Weighted combination (0.4F + 0.3R + 0.3U) | Default — balanced |

### CompiledRule Frozen Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `rule_id` | `str` | Unique rule identifier |
| `conditions` | `Tuple[str, ...]` | LHS condition patterns |
| `actions` | `Tuple[str, ...]` | RHS action patterns |
| `priority` | `float` | Conflict resolution priority |
| `activation_count` | `int` | Times this rule has fired |
| `last_used` | `Optional[float]` | Timestamp of last activation |
| `source_axioms` | `FrozenSet[str]` | Original declarative sources |
| `speedup_factor` | `float` | Measured speedup vs declarative |

### CompilationConfig Frozen Dataclass

| Field | Default | Description |
|-------|---------|-------------|
| `strategy` | `HYBRID` | Compilation strategy |
| `frequency_weight` | `0.4` | HYBRID frequency weight |
| `recency_weight` | `0.3` | HYBRID recency weight |
| `utility_weight` | `0.3` | HYBRID utility weight |
| `compilation_threshold` | `0.5` | Minimum score to compile |
| `decay_rate` | `0.95` | Activation decay per cycle |
| `max_compiled_rules` | `10,000` | Memory bound |
| `merge_similar_threshold` | `0.85` | Merge threshold |

## Protocol

```python
@runtime_checkable
class KnowledgeCompiler(Protocol):
    async def compile(self, axioms: Sequence[OntologyAxiom],
                      config: Optional[CompilationConfig] = None) -> CompilationResult: ...
    async def decompile(self, rule_id: str) -> Sequence[OntologyAxiom]: ...
    async def optimize(self) -> CompilationResult: ...
    async def get_compiled_rules(self, pattern: Optional[str] = None) -> Tuple[CompiledRule, ...]: ...
    async def measure_speedup(self, rule_id: str) -> float: ...
    async def fire_rule(self, rule_id: str, bindings: Dict[str, str]) -> Dict[str, str]: ...
    async def decay_activations(self) -> int: ...
    async def merge_similar_rules(self, threshold: Optional[float] = None) -> int: ...
```

## Implementation: AdaptiveKnowledgeCompiler

### Compilation Pipeline

```
OntologyAxiom → Pattern Extraction → Scoring → Compile/Skip → Rule Store
                                                                   │
                                                              Maintenance
                                                          (Decay + Merge + Evict)
```

### HYBRID Scoring Function

```
score = 0.4 × freq_norm + 0.3 × recency_norm + 0.3 × utility_norm

freq_norm    = activation_count / max_activation
recency_norm = exp(-λ × age_seconds)
utility_norm = speedup_factor / max_speedup
```

### Rule Lifecycle

1. **Compilation**: Axiom crosses threshold → create CompiledRule
2. **Usage**: Rule fires → increment activation_count, update last_used
3. **Decay**: Each cycle × decay_rate → gradual fade without reinforcement
4. **Merge**: Similar rules (Jaccard > 0.85) → combined rule
5. **Eviction**: Below threshold or capacity exceeded → decompile back to declarative

### Dependency Tracking

```python
self._source_index: dict[str, set[str]] = defaultdict(set)  # axiom_id → rule_ids
```

When an axiom changes in OntologyManager, all dependent rules are invalidated via O(1) lookup.

## Metrics (Prometheus)

| Metric | Type | Description |
|--------|------|-------------|
| `knowledge_compiled_rules_total` | Gauge | Currently compiled rules |
| `knowledge_compilation_seconds` | Histogram | Compilation latency |
| `knowledge_rule_firings_total` | Counter | Total rule firings |
| `knowledge_rules_merged_total` | Counter | Rules merged |
| `knowledge_average_speedup` | Gauge | Mean speedup factor |

## Integration Points

- **OntologyManager (26.2)**: Axioms are input to compilation
- **ReasoningOrchestrator (20.5)**: Compiled rules accelerate reasoning
- **MemoryConsolidator (18.2)**: Consolidated patterns feed scoring

## References

- Anderson, J.R. (1993). *Rules of the Mind*
- Laird, J.E., Rosenbloom, P.S., & Newell, A. (1987). *Soar*
- Darwiche, A. & Marquis, P. (2002). *A knowledge compilation map*
- Minton, S. (1990). *Quantitative results concerning the utility of EBL*

---

## Phase 26 Sub-phase Tracker

| # | Component | Issue | Status |
|---|-----------|-------|--------|
| 26.1 | ConceptGraph | #578 | ✅ Spec'd |
| 26.2 | OntologyManager | #579 | ✅ Spec'd |
| 26.3 | KnowledgeCompiler | #580 | ✅ Spec'd |
| 26.4 | CommonSenseEngine | #581 | ✅ Spec'd |
| 26.5 | KnowledgeOrchestrator | #582 | ✅ Spec'd |
