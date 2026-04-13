# Phase 20.4 — AbductiveReasoner

> **Hypothesis generation, best-explanation selection & Bayesian belief updating for creative reasoning.**

| Field | Value |
|---|---|
| **Package** | `asi.reasoning.abduction` |
| **Since** | Phase 20.4 |
| **Depends on** | WorldModel 13.1, LogicalInferenceEngine 20.1, KnowledgeFusion 20.3 |
| **Integrates with** | CognitiveCycle, CuriosityModule 13.3, SurpriseDetector 13.4 |
| **Complexity** | High — probabilistic inference + hypothesis explosion management |

---

## Overview

The **AbductiveReasoner** implements **inference to the best explanation (IBE)**. Given a set of observations, it generates candidate hypotheses, scores them by simplicity / coverage / coherence, applies Bayesian belief updating as new evidence arrives, and prunes low-probability hypotheses.

This is the **"creative reasoning" engine** — where deduction *proves* and induction *generalises*, abduction **explains**. It answers the question: *"What state of the world, if true, would best account for what we observe?"*

The module draws candidate explanations from the rule store managed by LogicalInferenceEngine (20.1), fuses cross-domain knowledge via KnowledgeFusion (20.3), and feeds high-confidence hypotheses back into WorldModel (13.1) as believed propositions. SurpriseDetector (13.4) triggers abduction when an observation deviates from expectation; CuriosityModule (13.3) consumes low-confidence hypotheses as exploration targets.

### Design Principles

| Principle | Rationale |
|---|---|
| **Inference to the best explanation** | Abduction fills the gap between deductive proof and inductive generalisation |
| **Bayesian belief updating** | Posterior probabilities must be principled and renormalisable |
| **Hypothesis pruning** | Prevent combinatorial explosion of candidate explanations |
| **Scoring pipeline** | Multi-criteria scoring (simplicity, coverage, coherence) follows Occam's razor |
| **Frozen dataclasses** | Immutable hypotheses and evidence prevent accidental mutation across async boundaries |

---

## Enums

### `HypothesisStatus`

```python
class HypothesisStatus(enum.Enum):
    """Lifecycle states for a hypothesis."""
    ACTIVE    = "active"       # Under evaluation
    CONFIRMED = "confirmed"    # Sufficient evidence, posterior > 0.8
    REFUTED   = "refuted"      # Contradicted by strong evidence
    PRUNED    = "pruned"       # Posterior fell below pruning_threshold
    SUSPENDED = "suspended"    # Temporarily paused (e.g. missing data)
```

### `ScoringCriterion`

```python
class ScoringCriterion(enum.Enum):
    """Criteria for ranking hypotheses."""
    SIMPLICITY  = "simplicity"   # Fewer assumptions → higher score
    COVERAGE    = "coverage"     # More observations explained → higher
    COHERENCE   = "coherence"    # Consistency with confirmed hypotheses
    ANALOGY     = "analogy"      # Structural similarity to past explanations
    COMPOSITE   = "composite"    # Weighted combination of all criteria
```

### `EvidenceType`

```python
class EvidenceType(enum.Enum):
    """Relationship between evidence and a hypothesis."""
    SUPPORTING    = "supporting"     # Increases posterior
    CONTRADICTING = "contradicting"  # Decreases posterior
    NEUTRAL       = "neutral"        # No effect on posterior
    AMBIGUOUS     = "ambiguous"      # Direction unclear — small update
```

---

## Frozen Dataclasses

### `Observation`

```python
@dataclasses.dataclass(frozen=True, slots=True)
class Observation:
    """An atomic observed fact fed into the abduction engine."""
    obs_id: str                # UUID
    description: str           # Human-readable description
    timestamp_ns: int          # Monotonic nanosecond timestamp
    source: str                # Origin system (e.g. "sensor.vision", "nlu.parse")
    confidence: float          # [0.0, 1.0] — observation reliability
```

### `Hypothesis`

```python
@dataclasses.dataclass(frozen=True, slots=True)
class Hypothesis:
    """A candidate explanation for one or more observations."""
    hyp_id: str
    description: str
    status: HypothesisStatus
    prior_probability: float           # Initial P(H)
    posterior_probability: float        # Current P(H|E₁,E₂,…)
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]
    simplicity_score: float            # [0.0, 1.0]
    coverage_score: float              # [0.0, 1.0]
    coherence_score: float             # [0.0, 1.0]
    composite_score: float             # Weighted sum
    created_ns: int
    updated_ns: int
```

### `Evidence`

```python
@dataclasses.dataclass(frozen=True, slots=True)
class Evidence:
    """A piece of evidence linking an observation to a hypothesis."""
    evidence_id: str           # UUID
    observation: Observation
    hypothesis_id: str
    evidence_type: EvidenceType
    likelihood_ratio: float    # P(E|H) / P(E|¬H) — >1 supports, <1 contradicts
```

### `ExplanationResult`

```python
@dataclasses.dataclass(frozen=True, slots=True)
class ExplanationResult:
    """Result of an explain() call — best hypothesis + alternatives."""
    best_hypothesis: Hypothesis
    alternatives: tuple[Hypothesis, ...]
    observations_explained: int
    total_observations: int
    confidence: float          # Posterior of best hypothesis
    elapsed_ms: float
```

### `AbductionConfig`

```python
@dataclasses.dataclass(frozen=True, slots=True)
class AbductionConfig:
    """Tuning knobs for the abduction engine."""
    max_hypotheses: int = 100
    pruning_threshold: float = 0.01        # Below this posterior → PRUNED
    prior_uniform: bool = True             # Start all hypotheses with equal prior
    simplicity_weight: float = 0.3
    coverage_weight: float = 0.4
    coherence_weight: float = 0.3
    bayesian_update: bool = True
    min_evidence_for_confirm: int = 3      # Supporting evidence count to confirm
```

---

## Protocol

```python
@typing.runtime_checkable
class AbductiveReasoner(typing.Protocol):
    """Inference-to-the-best-explanation engine."""

    async def observe(self, observation: Observation) -> tuple[Hypothesis, ...]:
        """Ingest an observation, generate/update candidate hypotheses."""
        ...

    async def explain(
        self, observations: tuple[Observation, ...]
    ) -> ExplanationResult:
        """Given observations, return the best explanation + alternatives."""
        ...

    async def update_belief(self, evidence: Evidence) -> Hypothesis:
        """Bayesian update: adjust posterior of the target hypothesis."""
        ...

    async def prune(self) -> tuple[Hypothesis, ...]:
        """Remove hypotheses whose posterior < pruning_threshold."""
        ...

    async def get_hypotheses(
        self, status: HypothesisStatus | None = None
    ) -> tuple[Hypothesis, ...]:
        """Retrieve hypotheses, optionally filtered by status."""
        ...

    async def confirm(self, hyp_id: str) -> Hypothesis:
        """Mark hypothesis as CONFIRMED if evidence threshold met."""
        ...

    async def refute(self, hyp_id: str) -> Hypothesis:
        """Mark hypothesis as REFUTED."""
        ...
```

---

## Implementation — `AsyncAbductiveReasoner`

### Hypothesis Generation

For each new observation:

1. Query the rule store (LogicalInferenceEngine 20.1) for rules whose **consequent** matches the observation.
2. Each matching rule's **antecedent** becomes a candidate hypothesis (abductive step: "if A→B and we see B, maybe A").
3. Deduplicate against existing hypotheses (by description hash).
4. If `prior_uniform`, assign `prior_probability = 1 / n` where n = number of active hypotheses.
5. Score each hypothesis on simplicity / coverage / coherence.
6. If active count > `max_hypotheses`, trigger immediate prune.

```
Observation("temperature anomaly detected")
    → Rule: EquipmentMalfunction → TemperatureAnomaly
    → Hypothesis: EquipmentMalfunction (abduced)
    → Rule: ClimateShift → TemperatureAnomaly
    → Hypothesis: ClimateShift (abduced)
```

### Scoring Pipeline

```python
def _score_simplicity(self, hyp: Hypothesis) -> float:
    """Fewer assumptions → higher simplicity. Occam's razor."""
    num_assumptions = len(hyp.supporting_evidence) + 1  # +1 for the hypothesis itself
    return 1.0 / (1.0 + num_assumptions)

def _score_coverage(self, hyp: Hypothesis, observations: Sequence[Observation]) -> float:
    """Fraction of observations the hypothesis explains."""
    explained = sum(1 for obs in observations if self._explains(hyp, obs))
    return explained / max(len(observations), 1)

def _score_coherence(self, hyp: Hypothesis) -> float:
    """Consistency with confirmed hypotheses. 1.0 if no contradictions."""
    confirmed = [h for h in self._hypotheses.values() if h.status == HypothesisStatus.CONFIRMED]
    contradictions = sum(1 for c in confirmed if self._contradicts(hyp, c))
    return 1.0 / (1.0 + contradictions)

def _composite_score(self, hyp: Hypothesis) -> float:
    """Weighted sum: 0.3×simplicity + 0.4×coverage + 0.3×coherence."""
    return (
        self._config.simplicity_weight * hyp.simplicity_score
        + self._config.coverage_weight * hyp.coverage_score
        + self._config.coherence_weight * hyp.coherence_score
    )
```

### Bayesian Belief Updating

```
P(H|E) = P(E|H) × P(H) / P(E)

where:
  P(E|H) = evidence.likelihood_ratio × P(E|¬H)   [derived from LR]
  P(H)   = hypothesis.posterior_probability        [current belief]
  P(E)   = Σ_i P(E|H_i) × P(H_i)                 [marginalised over all hypotheses]
```

- **SUPPORTING** evidence: likelihood_ratio > 1.0 → posterior increases
- **CONTRADICTING** evidence: likelihood_ratio < 1.0 → posterior decreases
- **NEUTRAL**: likelihood_ratio ≈ 1.0 → no meaningful change
- **AMBIGUOUS**: small perturbation (LR in [0.8, 1.2])
- After each update, **renormalise** all active posteriors to sum to 1.0

### Pruning

```python
async def prune(self) -> tuple[Hypothesis, ...]:
    pruned = []
    async with self._lock:
        for hyp in list(self._hypotheses.values()):
            if (
                hyp.status == HypothesisStatus.ACTIVE
                and hyp.posterior_probability < self._config.pruning_threshold
            ):
                updated = dataclasses.replace(hyp, status=HypothesisStatus.PRUNED)
                self._hypotheses[hyp.hyp_id] = updated
                pruned.append(updated)
                self._pruned_counter.inc()
    return tuple(pruned)
```

### Confirmation Logic

```python
async def confirm(self, hyp_id: str) -> Hypothesis:
    async with self._lock:
        hyp = self._hypotheses[hyp_id]
        if (
            len(hyp.supporting_evidence) >= self._config.min_evidence_for_confirm
            and hyp.posterior_probability > 0.8
        ):
            confirmed = dataclasses.replace(hyp, status=HypothesisStatus.CONFIRMED)
            self._hypotheses[hyp_id] = confirmed
            # Feed back into WorldModel as a believed proposition
            await self._world_model.assert_belief(confirmed.description, confirmed.posterior_probability)
            return confirmed
        raise ValueError(f"Hypothesis {hyp_id} does not meet confirmation criteria")
```

### Concurrency

- `asyncio.Lock` guards `self._hypotheses: dict[str, Hypothesis]` for all mutations
- Read-only methods (`get_hypotheses`) acquire the lock briefly to snapshot
- Evidence ingestion is serialised to maintain Bayesian consistency

---

## Null Implementation

```python
class NullAbductiveReasoner:
    """No-op implementation for DI / testing.
    observe() returns empty tuple, explain() raises NotImplementedError,
    update_belief() returns unchanged hypothesis.
    Satisfies isinstance(..., AbductiveReasoner).
    """
    async def observe(self, observation): return ()
    async def explain(self, observations): raise NotImplementedError
    async def update_belief(self, evidence): raise NotImplementedError
    async def prune(self): return ()
    async def get_hypotheses(self, status=None): return ()
    async def confirm(self, hyp_id): raise NotImplementedError
    async def refute(self, hyp_id): raise NotImplementedError
```

---

## Factory

```python
def make_abductive_reasoner(
    config: AbductionConfig | None = None,
    *,
    inference_engine: LogicalInferenceEngine | None = None,
    world_model: WorldModel | None = None,
    null: bool = False,
) -> AbductiveReasoner:
    if null:
        return NullAbductiveReasoner()
    return AsyncAbductiveReasoner(
        config=config or AbductionConfig(),
        inference_engine=inference_engine,
        world_model=world_model,
    )
```

---

## Integration Map

```
┌─────────────────────┐     rules whose consequent
│ LogicalInference     │◄─── matches observation
│ Engine 20.1          │     (abductive query)
└─────────┬───────────┘
          │ candidate hypotheses
          ▼
┌─────────────────────┐     cross-domain
│ KnowledgeFusion     │◄─── knowledge for
│ 20.3                │     hypothesis scoring
└─────────┬───────────┘
          │ enriched hypotheses
          ▼
┌─────────────────────────────────────────┐
│         AbductiveReasoner 20.4          │
│  ┌───────────┐  ┌──────────┐  ┌──────┐ │
│  │ Generate  │→ │  Score   │→ │Update│ │
│  │ Hypotheses│  │ S/C/C/A  │  │Belief│ │
│  └───────────┘  └──────────┘  └──┬───┘ │
│                                  │      │
│  ┌──────┐  ┌─────────┐  ┌──────┐│      │
│  │Prune │← │Normalise│← │Bayes ││      │
│  └──┬───┘  └─────────┘  └──────┘│      │
└─────┼────────────────────────────┼──────┘
      │ pruned                     │ confirmed
      ▼                            ▼
┌─────────────┐          ┌─────────────────┐
│ Curiosity   │          │ WorldModel 13.1 │
│ Module 13.3 │          │ (assert_belief) │
│(explore low │          └────────┬────────┘
│ confidence) │                   │
└─────────────┘                   ▼
                         ┌─────────────────┐
┌─────────────┐          │ SurpriseDetector│
│ Cognitive   │◄────────▶│ 13.4 (triggers  │
│ Cycle       │          │  new abduction) │
└─────────────┘          └─────────────────┘
```

### Integration Contracts

| Component | Interface | Direction |
|---|---|---|
| LogicalInferenceEngine 20.1 | `query_rules(consequent=obs)` → matching rules | AbductiveReasoner reads |
| KnowledgeFusion 20.3 | `enrich(hypothesis)` → cross-domain evidence | AbductiveReasoner reads |
| WorldModel 13.1 | `assert_belief(description, confidence)` | AbductiveReasoner writes |
| CuriosityModule 13.3 | `add_exploration_target(hyp_id, posterior)` | AbductiveReasoner writes |
| SurpriseDetector 13.4 | `on_surprise(observation)` → triggers `observe()` | SurpriseDetector calls |
| CognitiveCycle | `_abductive_step()` in main loop | CognitiveCycle calls |

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `asi_abduction_observations_total` | Counter | — | Observations processed |
| `asi_abduction_hypotheses_active` | Gauge | `status` | Active hypotheses by status |
| `asi_abduction_explain_seconds` | Histogram | — | Explanation generation latency |
| `asi_abduction_belief_updates_total` | Counter | — | Bayesian updates performed |
| `asi_abduction_pruned_total` | Counter | — | Hypotheses pruned |

### PromQL Examples

```promql
# Hypothesis generation rate (per minute)
rate(asi_abduction_observations_total[5m]) * 60

# Average explain latency (p99)
histogram_quantile(0.99, rate(asi_abduction_explain_seconds_bucket[5m]))

# Pruning ratio
rate(asi_abduction_pruned_total[5m]) / rate(asi_abduction_observations_total[5m])
```

### Grafana Alerts

```yaml
- alert: AbductionHypothesisExplosion
  expr: asi_abduction_hypotheses_active{status="active"} > 500
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Hypothesis count exceeding safe limit"

- alert: AbductionExplainLatency
  expr: histogram_quantile(0.99, rate(asi_abduction_explain_seconds_bucket[5m])) > 3.0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Abduction P99 explain latency > 3s"

- alert: AbductionPruneRateHigh
  expr: rate(asi_abduction_pruned_total[5m]) / rate(asi_abduction_observations_total[5m]) > 0.9
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: ">90% of hypotheses being pruned — possible prior miscalibration"
```

---

## mypy Strict Compliance

| Pattern | Technique |
|---|---|
| `HypothesisStatus \| None` parameter | `if status is not None:` guard |
| `dict[str, Hypothesis]` mutation under lock | `async with self._lock:` |
| `tuple[Hypothesis, ...]` return | Always `tuple(...)` wrap |
| `dataclasses.replace()` on frozen | Returns new instance — no `type: ignore` |
| `float` division | Guard `max(..., 1)` to prevent ZeroDivisionError |
| `LogicalInferenceEngine \| None` | `assert self._engine is not None` before use |

---

## Test Targets (12)

| # | Test | Assertion |
|---|---|---|
| 1 | `test_observe_generates_hypotheses` | New observation produces ≥1 hypothesis |
| 2 | `test_observe_deduplicates` | Same observation twice → no duplicate hypotheses |
| 3 | `test_explain_returns_best` | `best_hypothesis.composite_score >= max(alternatives)` |
| 4 | `test_bayesian_update_supporting` | Supporting evidence → posterior increases |
| 5 | `test_bayesian_update_contradicting` | Contradicting evidence → posterior decreases |
| 6 | `test_posteriors_sum_to_one` | After any update, Σ posteriors of ACTIVE = 1.0 (±ε) |
| 7 | `test_prune_below_threshold` | Hypotheses with posterior < 0.01 get PRUNED |
| 8 | `test_confirm_requires_min_evidence` | Confirm fails if supporting count < 3 |
| 9 | `test_confirm_updates_world_model` | Confirmed hypothesis calls `assert_belief()` |
| 10 | `test_max_hypotheses_triggers_prune` | Exceeding 100 active hypotheses triggers auto-prune |
| 11 | `test_null_reasoner_protocol` | `isinstance(NullAbductiveReasoner(), AbductiveReasoner)` |
| 12 | `test_factory_null_flag` | `make_abductive_reasoner(null=True)` returns Null impl |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_observe_generates_hypotheses():
    reasoner = make_abductive_reasoner(
        config=AbductionConfig(),
        inference_engine=mock_inference_engine(),
        world_model=mock_world_model(),
    )
    obs = Observation("obs1", "temperature anomaly detected", time.time_ns(), "sensor.temp", 0.95)
    hypotheses = await reasoner.observe(obs)
    assert len(hypotheses) >= 1
    assert all(h.status == HypothesisStatus.ACTIVE for h in hypotheses)

@pytest.mark.asyncio
async def test_bayesian_update_supporting():
    reasoner = make_abductive_reasoner(
        config=AbductionConfig(),
        inference_engine=mock_inference_engine(),
        world_model=mock_world_model(),
    )
    obs = Observation("obs1", "temperature anomaly", time.time_ns(), "sensor", 0.9)
    hypotheses = await reasoner.observe(obs)
    hyp = hypotheses[0]
    initial_posterior = hyp.posterior_probability
    evidence = Evidence(
        "ev1", obs, hyp.hyp_id, EvidenceType.SUPPORTING, likelihood_ratio=5.0
    )
    updated = await reasoner.update_belief(evidence)
    assert updated.posterior_probability > initial_posterior
```

---

## Implementation Order

1. Create `asi/reasoning/abduction/__init__.py`
2. Define `HypothesisStatus`, `ScoringCriterion`, `EvidenceType` enums
3. Define `Observation`, `Hypothesis`, `Evidence`, `ExplanationResult`, `AbductionConfig` frozen dataclasses
4. Define `AbductiveReasoner` Protocol with `@runtime_checkable`
5. Implement `NullAbductiveReasoner`
6. Scaffold `AsyncAbductiveReasoner.__init__()` — config, lock, hypothesis store, metrics
7. Implement `observe()` — rule-store query + hypothesis generation + dedup
8. Implement `_score_simplicity()`, `_score_coverage()`, `_score_coherence()`, `_composite_score()`
9. Implement `update_belief()` — Bayesian update + renormalisation
10. Implement `explain()` — observation batch → score → rank → ExplanationResult
11. Implement `prune()`, `confirm()`, `refute()`
12. Implement `get_hypotheses()` with optional status filter
13. Implement `make_abductive_reasoner()` factory
14. Write all 12 tests + mypy strict pass

---

## Phase 20 — Knowledge Synthesis & Reasoning — Sub-phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 20.1 | LogicalInferenceEngine | #484 | 🟡 Spec'd |
| 20.2 | AnalogicalReasoner | #485 | 🟡 Spec'd |
| 20.3 | KnowledgeFusion | #482 | 🟡 Spec'd |
| **20.4** | **AbductiveReasoner** | **#483** | **🟡 Spec'd** |
| 20.5 | ReasoningOrchestrator | #486 | 🟡 Spec'd |

---

*Tracking: #109 · Discussion: #481*
