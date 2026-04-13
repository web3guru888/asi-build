# Phase 24.1 — BeliefTracker: Bayesian Belief Modeling & Epistemic State Management

> **Issue**: [#546](https://github.com/web3guru888/asi-build/issues/546) | **Show & Tell**: [#551](https://github.com/web3guru888/asi-build/discussions/551) | **Q&A**: [#552](https://github.com/web3guru888/asi-build/discussions/552)

## Overview

The `BeliefTracker` maintains probabilistic models of other agents' beliefs, knowledge states, and epistemic status. It implements **Bayesian belief updating** for incremental evidence integration and **AGM belief revision** (Alchourrón, Gärdenfors, Makinson 1985) for handling contradictory information through rational contraction, expansion, and revision operations.

This is the foundational component for Theory of Mind—without tracking *what other agents believe*, higher-level social reasoning (intention recognition, perspective-taking) has no epistemic grounding.

## Theoretical Foundations

### Bayesian Belief Updating

Given a prior probability P(H) and evidence E with likelihood ratio LR = P(E|H) / P(E|¬H):

```
posterior = prior × LR / (prior × LR + (1 - prior))
```

In log-odds form (for numerical stability):

```
log_odds(posterior) = log_odds(prior) + log(LR)
posterior = σ(log_odds) = 1 / (1 + exp(-log_odds))
```

### AGM Belief Revision (1985)

The AGM framework defines three operations on a belief set K:

| Operation | Symbol | Semantics | When |
|-----------|--------|-----------|------|
| Expansion | K + φ | Add φ to K | No conflict with K |
| Contraction | K ÷ φ | Remove φ from K | φ ∈ K |
| Revision | K * φ | Add φ, resolve conflicts | φ conflicts with K |

**Levi Identity**: K * φ = (K ÷ ¬φ) + φ (revision = contraction + expansion)

**AGM Postulates for Revision**:
1. **Closure**: K * φ is a belief set
2. **Success**: φ ∈ K * φ
3. **Inclusion**: K * φ ⊆ K + φ
4. **Vacuity**: If ¬φ ∉ K, then K * φ = K + φ
5. **Consistency**: K * φ is consistent (unless φ is contradictory)
6. **Extensionality**: If φ ≡ ψ, then K * φ = K * ψ

### Common Knowledge

```
CK(G, P) = ∀a ∈ G: Ka(P) ∧ ∀a ∈ G: Ka(∀b ∈ G: Kb(P)) ∧ ...
```

Approximated by fixed-point iteration with configurable depth.

## Data Structures

### Enums

```python
class EpistemicStatus(enum.Enum):
    """Epistemic status of a belief."""
    KNOWN = "known"              # Agent demonstrably knows this
    BELIEVED = "believed"        # Agent likely believes this
    UNCERTAIN = "uncertain"      # Insufficient evidence
    DISBELIEVED = "disbelieved"  # Agent likely disbelieves
    UNKNOWN = "unknown"          # No model of agent's stance

class RevisionOp(enum.Enum):
    """AGM belief revision operations."""
    EXPANSION = "expansion"      # Add belief (no conflict)
    REVISION = "revision"        # Add belief (resolve conflict)
    CONTRACTION = "contraction"  # Remove belief
```

### Frozen Dataclasses

```python
@dataclass(frozen=True)
class Proposition:
    """An atomic proposition in the belief system."""
    predicate: str               # e.g., "has_resource"
    args: tuple[str, ...]        # e.g., ("agent_B", "gold")
    negated: bool = False

@dataclass(frozen=True)
class BeliefEntry:
    """A single belief with provenance."""
    proposition: Proposition
    prior: float                 # Prior probability [0, 1]
    posterior: float              # Posterior after evidence [0, 1]
    evidence_count: int          # Number of observations
    last_updated_ms: int         # Epoch milliseconds
    source: str = "observation"  # observation | communication | inference

@dataclass(frozen=True)
class BeliefState:
    """Complete belief model for one agent."""
    agent_id: str
    beliefs: tuple[BeliefEntry, ...]
    common_knowledge: FrozenSet[Proposition]
    private_beliefs: FrozenSet[Proposition]
    epistemic_status: Mapping[Proposition, EpistemicStatus]
    confidence: float            # Overall model confidence [0, 1]
    timestamp_ms: int

@dataclass(frozen=True)
class BeliefDiff:
    """Diff between two belief states."""
    added: tuple[BeliefEntry, ...]
    removed: tuple[BeliefEntry, ...]
    changed: tuple[tuple[BeliefEntry, BeliefEntry], ...]
    divergence_score: float      # KL divergence
```

## Protocol

```python
@runtime_checkable
class BeliefTracker(Protocol):
    async def update_belief(self, agent_id: str, proposition: Proposition,
                            evidence: float, source: str = "observation") -> BeliefEntry: ...
    async def revise_belief(self, agent_id: str, proposition: Proposition,
                            op: RevisionOp) -> BeliefState: ...
    async def query_belief(self, agent_id: str, proposition: Proposition) -> BeliefEntry | None: ...
    async def get_agent_model(self, agent_id: str) -> BeliefState: ...
    async def diff_beliefs(self, agent_a: str, agent_b: str) -> BeliefDiff: ...
    async def get_common_knowledge(self, agent_ids: tuple[str, ...]) -> FrozenSet[Proposition]: ...
    async def decay_beliefs(self, agent_id: str, decay_rate: float) -> int: ...
```

## Implementation: BayesianBeliefTracker

### Internal State

```python
class BayesianBeliefTracker:
    _models: dict[str, dict[Proposition, BeliefEntry]]
    _common_kb: dict[FrozenSet[str], set[Proposition]]
    _lock: asyncio.Lock
    _revision_log: deque[tuple[int, str, RevisionOp, Proposition]]
```

### Bayesian Update Algorithm

```python
async def update_belief(self, agent_id, proposition, evidence, source="observation"):
    async with self._lock:
        model = self._models.setdefault(agent_id, {})
        existing = model.get(proposition)
        
        if existing:
            prior = existing.posterior
            count = existing.evidence_count + 1
        else:
            prior = 0.5  # Uninformative prior
            count = 1
        
        # Log-odds update
        prior_clamped = max(1e-6, min(1 - 1e-6, prior))
        lr_clamped = max(1e-6, evidence)
        log_odds = math.log(prior_clamped / (1 - prior_clamped)) + math.log(lr_clamped)
        posterior = 1.0 / (1.0 + math.exp(-log_odds))
        posterior = max(1e-6, min(1 - 1e-6, posterior))
        
        entry = BeliefEntry(proposition, prior, posterior, count, now_ms(), source)
        model[proposition] = entry
        return entry
```

### AGM Revision — Partial Meet Contraction

```python
async def revise_belief(self, agent_id, proposition, op):
    async with self._lock:
        model = self._models.setdefault(agent_id, {})
        
        match op:
            case RevisionOp.EXPANSION:
                if not self._conflicts(model, proposition):
                    model[proposition] = BeliefEntry(proposition, 0.5, 0.9, 1, now_ms())
                    
            case RevisionOp.REVISION:
                # Levi identity: revise = contract(¬φ) + expand(φ)
                neg_prop = Proposition(proposition.predicate, proposition.args, not proposition.negated)
                conflicting = self._find_conflicts(model, proposition)
                # Retract in ascending entrenchment order
                for conflict in sorted(conflicting, key=lambda e: e.evidence_count * e.posterior):
                    del model[conflict.proposition]
                model[proposition] = BeliefEntry(proposition, 0.5, 0.9, 1, now_ms())
                
            case RevisionOp.CONTRACTION:
                if proposition in model:
                    del model[proposition]
        
        self._revision_log.append((now_ms(), agent_id, op, proposition))
        return self._build_state(agent_id)
```

### KL Divergence for Belief Diff

```python
async def diff_beliefs(self, agent_a, agent_b):
    model_a = self._models.get(agent_a, {})
    model_b = self._models.get(agent_b, {})
    
    all_props = set(model_a.keys()) | set(model_b.keys())
    kl_sum = 0.0
    for prop in all_props:
        p = model_a.get(prop, BeliefEntry(prop, 0.5, 0.5, 0, 0)).posterior
        q = model_b.get(prop, BeliefEntry(prop, 0.5, 0.5, 0, 0)).posterior
        p, q = max(1e-6, p), max(1e-6, q)
        kl_sum += p * math.log(p / q) + (1-p) * math.log((1-p) / (1-q))
    
    return BeliefDiff(added=..., removed=..., changed=..., divergence_score=kl_sum)
```

### Decay Model

```python
async def decay_beliefs(self, agent_id, decay_rate):
    count = 0
    model = self._models.get(agent_id, {})
    for prop, entry in list(model.items()):
        dt = (now_ms() - entry.last_updated_ms) / 1000.0
        decayed = 0.5 + (entry.posterior - 0.5) * math.exp(-decay_rate * dt)
        if abs(decayed - entry.posterior) > 0.001:
            model[prop] = BeliefEntry(prop, entry.prior, decayed, entry.evidence_count, now_ms(), entry.source)
            count += 1
    return count
```

## Data Flow

```
Observation / Message / Inference
         │
         ▼
┌──────────────────────────┐
│  Evidence Extraction     │  Parse source → Proposition + likelihood_ratio
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Bayesian Log-Odds       │  log_odds += log(LR)
│  Update — O(1)           │  posterior = σ(log_odds)
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Consistency Check       │  Detect conflicts
└──────────┬───────────────┘
           │ conflict?
     ┌─────┴──────┐
     │ No         │ Yes
     ▼            ▼
   Store    AGM Revision
   Entry    (retract minimal + expand)
           │
           ▼
     Updated BeliefState
```

## Integration Points

| Component | Direction | Interface |
|-----------|-----------|-----------|
| WorldModel 13.1 | ← input | Ground truth for belief validation |
| CommunicationOrchestrator 19.5 | ← input | Message content as evidence |
| IntentionRecognizer 24.2 | → output | Beliefs inform goal priors |
| PerspectiveTaker 24.3 | → output | Beliefs define viewpoints |
| SocialOrchestrator 24.5 | → output | BeliefState aggregation |
| EmpathyEngine 21.3 | ← input | Emotional state as soft evidence |

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_belief_updates_total` | Counter | Total Bayesian belief updates |
| `asi_belief_revisions_total` | Counter | AGM revision operations by type |
| `asi_belief_model_size` | Gauge | Propositions per agent model |
| `asi_belief_decay_total` | Counter | Beliefs decayed |
| `asi_belief_divergence_score` | Histogram | KL divergence between agents |

### PromQL Examples

```promql
# Belief update rate by source
rate(asi_belief_updates_total[5m])

# Average model size
avg(asi_belief_model_size)

# High-divergence agent pairs
histogram_quantile(0.95, asi_belief_divergence_score_bucket) > 5.0
```

## Test Targets (12)

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_bayesian_update_posterior_correct` | Posterior = prior × LR / normalizer |
| 2 | `test_bayesian_update_log_odds_stability` | No overflow for extreme LR |
| 3 | `test_agm_expansion_no_conflict` | Expansion adds without removal |
| 4 | `test_agm_revision_resolves_conflict` | Revision removes minimal set |
| 5 | `test_agm_contraction_removes_belief` | Contraction + closure |
| 6 | `test_common_knowledge_intersection` | CK = intersection of KNOWN |
| 7 | `test_common_knowledge_depth_convergence` | Fixed-point within k iterations |
| 8 | `test_belief_diff_kl_divergence` | KL matches manual calculation |
| 9 | `test_decay_exponential_toward_prior` | Decayed → prior as Δt → ∞ |
| 10 | `test_query_unknown_agent_returns_none` | Graceful unknown agent |
| 11 | `test_concurrent_updates_no_corruption` | Lock prevents races |
| 12 | `test_null_belief_tracker_no_ops` | NullBeliefTracker defaults |

## Implementation Order

1. `Proposition` + `BeliefEntry` frozen dataclasses
2. `EpistemicStatus` + `RevisionOp` enums
3. `BeliefState` + `BeliefDiff` frozen dataclasses
4. `BeliefTracker` Protocol
5. `BayesianBeliefTracker.__init__`
6. `update_belief` — log-odds Bayesian update
7. `revise_belief` — AGM expansion/revision/contraction
8. `query_belief` + `get_agent_model`
9. `diff_beliefs` — KL divergence
10. `get_common_knowledge` — fixed-point intersection
11. `decay_beliefs` — exponential decay
12. `NullBeliefTracker` no-op
13. `make_belief_tracker()` factory
14. Prometheus metrics + test suite

## Phase 24 Sub-phase Tracker

| # | Component | Issue | Status |
|---|-----------|-------|--------|
| 24.1 | BeliefTracker | [#546](https://github.com/web3guru888/asi-build/issues/546) | ✅ Spec'd |
| 24.2 | IntentionRecognizer | [#547](https://github.com/web3guru888/asi-build/issues/547) | ✅ Spec'd |
| 24.3 | PerspectiveTaker | [#548](https://github.com/web3guru888/asi-build/issues/548) | ✅ Spec'd |
| 24.4 | SocialPredictor | [#549](https://github.com/web3guru888/asi-build/issues/549) | ✅ Spec'd |
| 24.5 | SocialOrchestrator | [#550](https://github.com/web3guru888/asi-build/issues/550) | ✅ Spec'd |
