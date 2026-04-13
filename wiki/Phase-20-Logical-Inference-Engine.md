# Phase 20.1 — LogicalInferenceEngine

> **Forward/backward chaining, resolution refutation & truth maintenance for formal logical reasoning.**

| Field | Value |
|---|---|
| **Package** | `asi.reasoning.inference` |
| **Since** | Phase 20.1 |
| **Depends on** | WorldModel 13.1, KnowledgeFusion 20.3 |
| **Integrates with** | CognitiveCycle, GoalDecomposer 10.2, SemanticParser 19.1 |
| **Complexity** | High — multiple inference strategies, TMS, contradiction detection |

---

## Overview

The **LogicalInferenceEngine** provides formal logical reasoning capabilities for the ASI-Build cognitive architecture. It supports three complementary inference strategies — **forward chaining** (data-driven saturation), **backward chaining** (goal-driven search), and **resolution refutation** (completeness for first-order logic) — unified under a single `infer()` interface with automatic strategy selection via the HYBRID mode.

A **Truth Maintenance System (TMS)** tracks the dependency graph between derived facts and their supporting rules, enabling principled belief revision: when a base fact is retracted, all transitively dependent conclusions are automatically invalidated and re-derived if alternative support exists.

### Design Principles

| Principle | Rationale |
|---|---|
| **Multiple strategies** | Forward chaining is complete for Horn clauses; backward is efficient for sparse goals; resolution handles full FOL |
| **TMS for belief revision** | Derived facts must be retractable without full re-computation |
| **Frozen dataclasses** | Immutable propositions prevent accidental mutation across async boundaries |
| **Protocol-first** | `@runtime_checkable` Protocol enables implementation swapping |
| **Bounded computation** | `max_depth` and `max_rules` prevent unbounded inference chains |

---

## Enums

### `InferenceStrategy`

```python
class InferenceStrategy(str, enum.Enum):
    FORWARD_CHAIN  = "forward_chain"   # Data-driven: saturate all applicable rules
    BACKWARD_CHAIN = "backward_chain"  # Goal-driven: DFS from query to base facts
    RESOLUTION     = "resolution"      # Negate goal, convert to CNF, resolve to ⊥
    HYBRID         = "hybrid"          # Backward first, forward fallback
```

### `TruthValue`

```python
class TruthValue(str, enum.Enum):
    TRUE          = "true"
    FALSE         = "false"
    UNKNOWN       = "unknown"
    CONTRADICTORY = "contradictory"  # Both TRUE and FALSE derived
```

### `RuleType`

```python
class RuleType(str, enum.Enum):
    HORN_CLAUSE  = "horn_clause"   # A ∧ B ∧ C → D (single head)
    DISJUNCTIVE  = "disjunctive"   # A ∧ B → C ∨ D
    NEGATION     = "negation"      # ¬A → B (negation as failure)
    CONDITIONAL  = "conditional"   # A → B (material conditional)
```

---

## Frozen Dataclasses

### `LogicalProposition`

```python
@dataclass(frozen=True, slots=True)
class LogicalProposition:
    subject: str                    # e.g. "Socrates"
    predicate: str                  # e.g. "is_mortal"
    object_: str | None = None     # e.g. "True" (optional for unary predicates)
    truth_value: TruthValue = TruthValue.UNKNOWN
    confidence: float = 1.0        # 0.0–1.0
    timestamp_ns: int = 0          # time.time_ns() at creation
```

### `InferenceRule`

```python
@dataclass(frozen=True, slots=True)
class InferenceRule:
    rule_id: str                                    # Unique identifier
    rule_type: RuleType                             # Horn, disjunctive, etc.
    antecedents: tuple[LogicalProposition, ...]     # If all these hold...
    consequent: LogicalProposition                  # ...then this follows
    confidence: float = 1.0                         # Rule reliability
    metadata: dict[str, Any] = field(default_factory=dict)
```

### `InferenceResult`

```python
@dataclass(frozen=True, slots=True)
class InferenceResult:
    conclusion: LogicalProposition              # Derived or queried proposition
    supporting_rules: tuple[str, ...]           # Rule IDs in proof chain
    proof_depth: int                            # Depth of inference chain
    confidence: float                           # Aggregated confidence
    inference_strategy: InferenceStrategy       # Strategy that produced this
    elapsed_ms: float                           # Wall-clock time
```

### `InferenceConfig`

```python
@dataclass(frozen=True, slots=True)
class InferenceConfig:
    max_depth: int = 20                                      # Max inference chain depth
    strategy: InferenceStrategy = InferenceStrategy.HYBRID   # Default strategy
    enable_tms: bool = True                                  # Truth Maintenance System
    contradiction_threshold: float = 0.3                     # Min confidence to flag
    max_rules: int = 10_000                                  # Hard cap on rule store
```

---

## Protocol

```python
@runtime_checkable
class LogicalInferenceEngine(Protocol):

    async def infer(self, query: LogicalProposition) -> InferenceResult:
        """Run inference to determine the truth of a proposition."""
        ...

    async def add_rule(self, rule: InferenceRule) -> None:
        """Add an inference rule to the knowledge base."""
        ...

    async def add_fact(self, fact: LogicalProposition) -> None:
        """Assert a ground fact."""
        ...

    async def retract(self, fact: LogicalProposition) -> None:
        """Retract a fact and cascade through TMS dependencies."""
        ...

    async def get_contradictions(self) -> tuple[tuple[LogicalProposition, LogicalProposition], ...]:
        """Return all detected contradictions (TRUE/FALSE pairs)."""
        ...

    async def explain(self, result: InferenceResult) -> str:
        """Generate human-readable proof trace."""
        ...
```

---

## Implementation — `AsyncLogicalInferenceEngine`

### Construction

```python
class AsyncLogicalInferenceEngine:
    def __init__(self, config: InferenceConfig) -> None:
        self._config = config
        self._rules: dict[str, InferenceRule] = {}
        self._facts: dict[str, LogicalProposition] = {}
        self._tms_deps: dict[str, set[str]] = {}  # fact_key → supporting rule_ids
        self._lock = asyncio.Lock()
```

### Forward Chaining

BFS saturation algorithm:

```
1. queue ← all facts
2. while queue not empty:
3.   fact ← dequeue
4.   for each rule where fact matches an antecedent:
5.     if all antecedents of rule satisfied:
6.       derive consequent
7.       if consequent is new:
8.         add to facts, record TMS dependency
9.         enqueue consequent
10.      if depth > max_depth: stop
```

Forward chaining is **complete for Horn clauses** — it will derive every possible conclusion. Worst-case complexity is O(n² × m) where n = facts and m = rules, but predicate indexing reduces this to amortised O(n log n) for typical knowledge bases.

### Backward Chaining

Goal-driven DFS with memoisation:

```
backward_chain(goal, depth, memo):
  if goal in facts: return SUCCESS
  if goal in memo: return memo[goal]
  if depth > max_depth: return FAILURE
  for each rule where rule.consequent matches goal:
    if all(backward_chain(ant, depth+1, memo) for ant in rule.antecedents):
      memo[goal] = SUCCESS
      record proof chain
      return SUCCESS
  memo[goal] = FAILURE
  return FAILURE
```

Backward chaining is efficient when the goal is specific and the knowledge base is large — it only explores the relevant subgraph.

### Resolution Refutation

For full first-order logic completeness:

```
1. Negate the goal proposition
2. Convert all rules + negated goal to CNF (Conjunctive Normal Form)
3. Repeatedly resolve pairs of clauses:
   a. Find complementary literals (P and ¬P)
   b. Produce resolvent (remaining literals)
   c. If resolvent is empty clause ⊥ → goal is PROVEN
   d. If no new resolvents possible → goal UNPROVEN
```

CNF conversion applies De Morgan's laws, distribution of OR over AND, and Skolemisation for existential quantifiers.

### HYBRID Strategy

```
1. Try backward_chain(goal, max_depth=config.max_depth/2)
2. If SUCCESS → return result
3. Else: run forward_chain() to saturate
4. Check if goal now in facts
5. If still not found, try resolution
```

### Truth Maintenance System (TMS)

The TMS maintains a dependency DAG:

```
base_fact_1 ──┐
              ├──→ rule_A ──→ derived_fact_X ──┐
base_fact_2 ──┘                                ├──→ rule_C ──→ derived_fact_Z
base_fact_3 ──────→ rule_B ──→ derived_fact_Y ──┘
```

**Retraction cascade:**
1. Mark retracted fact as UNKNOWN
2. Walk dependency DAG forward
3. For each dependent derived fact:
   a. Check if alternative support exists (other rules with all antecedents still TRUE)
   b. If no alternative: mark UNKNOWN, continue cascade
   c. If alternative exists: keep fact, update dependency record

### Contradiction Detection

Scan fact store for pairs where `(subject, predicate, object_)` matches but one has `TruthValue.TRUE` and another `TruthValue.FALSE`. Both must have confidence ≥ `contradiction_threshold`.

---

## Null Implementation

```python
class NullLogicalInferenceEngine:
    async def infer(self, query: LogicalProposition) -> InferenceResult:
        return InferenceResult(
            conclusion=query, supporting_rules=(), proof_depth=0,
            confidence=0.0, inference_strategy=InferenceStrategy.HYBRID,
            elapsed_ms=0.0,
        )
    async def add_rule(self, rule: InferenceRule) -> None: pass
    async def add_fact(self, fact: LogicalProposition) -> None: pass
    async def retract(self, fact: LogicalProposition) -> None: pass
    async def get_contradictions(self) -> tuple: return ()
    async def explain(self, result: InferenceResult) -> str: return ""
```

---

## Factory

```python
def make_logical_inference_engine(
    config: InferenceConfig | None = None,
) -> LogicalInferenceEngine:
    if config is None:
        return NullLogicalInferenceEngine()
    return AsyncLogicalInferenceEngine(config)
```

---

## Data Flow

```
                    ┌─────────────────────────────────────────┐
                    │       LogicalInferenceEngine 20.1        │
                    │                                          │
  add_fact() ──────►│  Facts Store ──┐                        │
                    │                ├──→ Strategy Dispatch    │
  add_rule() ──────►│  Rules Store ──┘       │                │
                    │                    ┌───┴───┐            │
                    │                    │FORWARD│BACKWARD│RES│
  infer(query) ────►│                    └───┬───┘            │
                    │                        │                │
                    │                  InferenceResult         │
                    │                  + proof trace           │
                    │                        │                │
                    │  TMS ◄── retract() ────┘                │
                    └────────────────────────────────────────┘
                                    │
                         CognitiveCycle / GoalDecomposer
```

---

## Integration Map

### WorldModel 13.1 → Facts

`WorldModel.observe()` produces observations that are converted to `LogicalProposition` objects and added via `add_fact()`. The engine maintains a live view of the world's logical state.

### GoalDecomposer 10.2 → Backward Chaining

`GoalDecomposer.decompose()` uses backward chaining to determine what sub-goals must be achieved to satisfy a top-level goal:

```python
sub_goals = await inference_engine.infer(
    LogicalProposition(subject="goal", predicate="achieved", object_="deploy_bridge")
)
# supporting_rules reveal the sub-goal chain
```

### SemanticParser 19.1 → Query Construction

`SemanticParser.parse()` converts natural-language questions into `LogicalProposition` queries:

```
"Is Socrates mortal?" → LogicalProposition(subject="Socrates", predicate="is_mortal")
```

### KnowledgeFusion 20.3 → Rules & Facts

Fused knowledge atoms become facts; fused ontology mappings become inference rules. Bidirectional: inference results feed back to KnowledgeFusion as derived atoms.

### CognitiveCycle → Reasoning Step

`CognitiveCycle._reasoning_step()` calls `infer()` with the current reasoning query, receives `InferenceResult`, and routes the conclusion to `GoalRegistry` for action planning.

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `asi_inference_query_total` | Counter | `strategy` | Total inference queries |
| `asi_inference_query_seconds` | Histogram | `strategy` | Query latency |
| `asi_inference_rules_active` | Gauge | — | Active rules in store |
| `asi_inference_facts_active` | Gauge | — | Active facts in store |
| `asi_inference_contradictions_total` | Counter | — | Contradictions detected |

### PromQL Examples

```promql
# Query rate by strategy
rate(asi_inference_query_total[5m])

# P99 inference latency
histogram_quantile(0.99, rate(asi_inference_query_seconds_bucket[5m]))

# Knowledge base size
asi_inference_rules_active + asi_inference_facts_active

# Contradiction rate
rate(asi_inference_contradictions_total[5m])
```

### Grafana Alerts

```yaml
- alert: InferenceHighLatency
  expr: histogram_quantile(0.99, rate(asi_inference_query_seconds_bucket[5m])) > 1.0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Inference P99 latency > 1s"

- alert: ContradictionRateHigh
  expr: rate(asi_inference_contradictions_total[5m]) > 0.1
  for: 3m
  labels:
    severity: critical
  annotations:
    summary: "Knowledge base contradiction rate > 0.1/s"

- alert: RuleStoreNearCapacity
  expr: asi_inference_rules_active / 10000 > 0.9
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Rule store > 90% capacity"
```

---

## mypy Strict Compliance

| Pattern | Technique |
|---|---|
| `LogicalProposition.object_` nullable | `str \| None`; callers narrow with `if prop.object_ is not None` |
| `InferenceRule.metadata` mutable dict | `field(default_factory=dict)` — dict mutable, frozen prevents reassignment |
| `_tms_deps` value type | `dict[str, set[str]]` — explicit generic types |
| Protocol methods | All return types fully annotated, no `Any` |
| Enum as str | `InferenceStrategy(str, enum.Enum)` passes `--strict` |
| Optional config | `InferenceConfig \| None` with explicit `None` check |

---

## Test Targets (12)

| # | Test | Validates |
|---|---|---|
| 1 | `test_forward_chain_derives_transitive_fact` | A→B, B→C rules + fact A → derives C |
| 2 | `test_backward_chain_finds_proof` | Goal C with A→B→C chain → proof_depth=2 |
| 3 | `test_resolution_proves_negation` | ¬goal + rules → empty clause = proof |
| 4 | `test_hybrid_tries_backward_first` | HYBRID strategy uses backward_chain first |
| 5 | `test_tms_retract_cascades` | Retract base fact → derived facts marked UNKNOWN |
| 6 | `test_tms_alternative_support_preserved` | Fact with two supporting rules survives single retract |
| 7 | `test_contradiction_detection` | Same prop TRUE + FALSE → detected in get_contradictions() |
| 8 | `test_max_depth_prevents_infinite_loop` | Circular rules → terminates at max_depth |
| 9 | `test_explain_produces_readable_trace` | explain() returns non-empty string with rule references |
| 10 | `test_add_rule_respects_max_rules` | Adding rule beyond max_rules raises or evicts |
| 11 | `test_null_engine_returns_zero_confidence` | NullLogicalInferenceEngine returns confidence=0.0 |
| 12 | `test_concurrent_infer_thread_safe` | asyncio.gather 20 queries → no corruption |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_forward_chain_derives_transitive_fact():
    engine = make_logical_inference_engine(InferenceConfig(strategy=InferenceStrategy.FORWARD_CHAIN))
    await engine.add_fact(LogicalProposition("Socrates", "is_human", truth_value=TruthValue.TRUE))
    await engine.add_rule(InferenceRule(
        rule_id="r1", rule_type=RuleType.HORN_CLAUSE,
        antecedents=(LogicalProposition("Socrates", "is_human"),),
        consequent=LogicalProposition("Socrates", "is_mortal", truth_value=TruthValue.TRUE),
    ))
    result = await engine.infer(LogicalProposition("Socrates", "is_mortal"))
    assert result.conclusion.truth_value == TruthValue.TRUE
    assert result.proof_depth >= 1
    assert "r1" in result.supporting_rules

@pytest.mark.asyncio
async def test_tms_retract_cascades():
    engine = make_logical_inference_engine(InferenceConfig(enable_tms=True))
    await engine.add_fact(LogicalProposition("A", "holds", truth_value=TruthValue.TRUE))
    await engine.add_rule(InferenceRule(
        rule_id="r1", rule_type=RuleType.HORN_CLAUSE,
        antecedents=(LogicalProposition("A", "holds"),),
        consequent=LogicalProposition("B", "holds", truth_value=TruthValue.TRUE),
    ))
    # Forward chain to derive B
    result = await engine.infer(LogicalProposition("B", "holds"))
    assert result.conclusion.truth_value == TruthValue.TRUE
    # Retract A → B should become UNKNOWN
    await engine.retract(LogicalProposition("A", "holds"))
    result2 = await engine.infer(LogicalProposition("B", "holds"))
    assert result2.conclusion.truth_value == TruthValue.UNKNOWN
```

---

## Implementation Order

1. Define `InferenceStrategy`, `TruthValue`, `RuleType` enums
2. Define `LogicalProposition` frozen dataclass
3. Define `InferenceRule` frozen dataclass
4. Define `InferenceResult` frozen dataclass
5. Define `InferenceConfig` frozen dataclass
6. Define `LogicalInferenceEngine` Protocol
7. Register 5 Prometheus metrics
8. Implement `AsyncLogicalInferenceEngine.__init__` + `add_fact/add_rule`
9. Implement forward chaining with BFS + depth guard
10. Implement backward chaining with DFS + memoisation
11. Implement resolution refutation with CNF conversion
12. Implement HYBRID strategy dispatch
13. Implement TMS dependency tracking + `retract()` cascade
14. Implement `get_contradictions()` + `explain()`
15. Implement `NullLogicalInferenceEngine`
16. Implement `make_logical_inference_engine()` factory
17. Write 12 tests
18. `mypy --strict`, `ruff`, green CI

---

## Phase 20 — Knowledge Synthesis & Reasoning — Sub-phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| **20.1** | **LogicalInferenceEngine** | **#484** | **🟡 Spec'd** |
| 20.2 | AnalogicalReasoner | #485 | 🟡 Spec'd |
| 20.3 | KnowledgeFusion | #482 | 🟡 Spec'd |
| 20.4 | AbductiveReasoner | #483 | 🟡 Spec'd |
| 20.5 | ReasoningOrchestrator | #486 | 🟡 Spec'd |

---

*Tracking: #109 · Discussion: #481*
