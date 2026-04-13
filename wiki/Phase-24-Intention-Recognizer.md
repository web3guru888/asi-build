# Phase 24.2 — IntentionRecognizer: Plan Recognition & BDI Goal Inference

> **Issue**: [#547](https://github.com/web3guru888/asi-build/issues/547) | **Show & Tell**: [#553](https://github.com/web3guru888/asi-build/discussions/553) | **Q&A**: [#554](https://github.com/web3guru888/asi-build/discussions/554)

## Overview

The `IntentionRecognizer` observes other agents' actions and infers their underlying **intentions, goals, and plans** using Bratman's BDI (Belief-Desire-Intention) framework and probabilistic plan recognition. Given a sequence of observed actions, it maintains a ranked set of intention hypotheses explaining the behavior, enabling prediction of future actions.

## Theoretical Foundations

### Bratman's BDI Framework (1987)

The BDI model explains rational agency through three mental attitudes:

| Attitude | Role | Persistence |
|----------|------|-------------|
| **Beliefs** | Informational — what agent thinks is true | Updated by evidence |
| **Desires** | Motivational — what agent wants to achieve | Relatively stable |
| **Intentions** | Deliberative — what agent has committed to do | Resist reconsideration |

Key insight: **Intentions are conduct-controlling pro-attitudes**. Once an agent forms an intention, they don't reconsider at every step—they persist through minor obstacles. This creates a predictability that plan recognition exploits.

### Bayesian Inverse Planning (Baker et al. 2009)

```
P(goal | observations) ∝ P(observations | goal) × P(goal)
```

This inverts the planning model: instead of "given a goal, what actions?", we ask "given actions, what goal?" The likelihood P(observations | goal) measures how well the observed action sequence aligns with optimal plans for the goal.

### Plan Recognition (Kautz & Allen 1986)

A plan library maps goals to action sequences. Given observed actions, we find which plan templates they partially match, creating intention hypotheses weighted by alignment quality.

## Data Structures

### Enums

```python
class GoalStatus(enum.Enum):
    ACTIVE = "active"          # Currently being pursued
    ACHIEVED = "achieved"      # Goal reached
    ABANDONED = "abandoned"    # Agent stopped pursuing
    BLOCKED = "blocked"        # Progress stalled
    HYPOTHETICAL = "hypothetical"  # Weakly supported
```

### State Machine

```
HYPOTHETICAL ──confidence > 0.3──► ACTIVE
     ▲                               │
     │                          ┌────┴─────┐
     │                          │          │
     │                     expected    all postconds
     │                     action      satisfied
     │                     timeout         │
     │                          │          ▼
     │                          ▼      ACHIEVED
     │                       BLOCKED
     │                          │
     │                     resumed  confidence
     │                     actions  < threshold
     │                          │       │
     │                          ▼       ▼
     │                       ACTIVE  ABANDONED
     └──────────────────────────────────┘
              (re-hypothesis if new evidence)
```

### Frozen Dataclasses

```python
@dataclass(frozen=True)
class ObservedAction:
    agent_id: str
    action_type: str
    parameters: Mapping[str, Any]
    timestamp_ms: int
    context: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class PlanTemplate:
    goal: str
    preconditions: tuple[str, ...]
    action_sequence: tuple[str, ...]
    postconditions: tuple[str, ...]
    flexibility: float         # 0=strict, 1=any order

@dataclass(frozen=True)
class IntentionHypothesis:
    agent_id: str
    goal: str
    plan_template: PlanTemplate | None
    status: GoalStatus
    confidence: float          # P(goal | observations)
    evidence: tuple[ObservedAction, ...]
    progress: float            # Estimated completion [0, 1]
    predicted_next: tuple[str, ...]
    competing_hypotheses: int

@dataclass(frozen=True)
class BDIState:
    agent_id: str
    beliefs: tuple[str, ...]   # Ref to BeliefTracker 24.1
    desires: tuple[str, ...]   # Inferred goals
    intentions: tuple[IntentionHypothesis, ...]
    timestamp_ms: int
```

## Protocol

```python
@runtime_checkable
class IntentionRecognizer(Protocol):
    async def observe_action(self, action: ObservedAction) -> None: ...
    async def infer_intention(self, agent_id: str, top_k: int = 5) -> tuple[IntentionHypothesis, ...]: ...
    async def predict_next_action(self, agent_id: str) -> tuple[tuple[str, float], ...]: ...
    async def get_bdi_state(self, agent_id: str) -> BDIState: ...
    async def register_plan_template(self, template: PlanTemplate) -> None: ...
    async def get_hypotheses(self, agent_id: str, status_filter: GoalStatus | None = None) -> tuple[IntentionHypothesis, ...]: ...
    async def prune_hypotheses(self, agent_id: str, min_confidence: float = 0.01) -> int: ...
```

## Implementation: ProbabilisticIntentionRecognizer

### Internal State

```python
class ProbabilisticIntentionRecognizer:
    _plan_library: list[PlanTemplate]
    _hypotheses: dict[str, list[_MutableHypothesis]]
    _action_log: dict[str, deque[ObservedAction]]  # Bounded per-agent
    _belief_tracker: BeliefTracker
    _lock: asyncio.Lock
```

### observe_action Algorithm

```python
async def observe_action(self, action):
    async with self._lock:
        agent = action.agent_id
        self._action_log.setdefault(agent, deque(maxlen=1000)).append(action)
        
        # Update existing hypotheses
        for hyp in self._hypotheses.get(agent, []):
            likelihood = self._alignment_score(hyp, action)
            hyp.posterior *= likelihood
        
        # Scan for new matching templates
        for template in self._plan_library:
            if self._matches_start(template, action) and not self._has_hypothesis(agent, template.goal):
                self._hypotheses.setdefault(agent, []).append(
                    _MutableHypothesis(agent, template.goal, template, 1.0 / len(self._plan_library))
                )
        
        # Normalize posteriors
        total = sum(h.posterior for h in self._hypotheses.get(agent, []))
        if total > 0:
            for h in self._hypotheses[agent]:
                h.posterior /= total
        
        # Prune below threshold
        self._hypotheses[agent] = [h for h in self._hypotheses.get(agent, []) if h.posterior > 0.01]
        
        # Update predicted_next for top hypotheses
        for h in sorted(self._hypotheses.get(agent, []), key=lambda x: -x.posterior)[:5]:
            h.predicted_next = self._compute_next_actions(h)
```

### Plan Template Alignment

```python
def _alignment_score(self, hyp, action):
    template = hyp.plan_template
    if template is None:
        return 0.5  # No template → neutral evidence
    
    strict_match = action.action_type == template.action_sequence[hyp.progress_idx]
    flex_match = action.action_type in set(template.action_sequence[hyp.progress_idx:])
    
    strict_score = 1.0 if strict_match else 0.1
    flex_score = 1.0 if flex_match else 0.1
    
    return template.flexibility * flex_score + (1 - template.flexibility) * strict_score
```

### predict_next_action — Marginalization

```python
async def predict_next_action(self, agent_id):
    hypotheses = await self.infer_intention(agent_id, top_k=10)
    action_probs = defaultdict(float)
    for hyp in hypotheses:
        for action in hyp.predicted_next:
            action_probs[action] += hyp.confidence / max(len(hyp.predicted_next), 1)
    return tuple(sorted(action_probs.items(), key=lambda x: -x[1]))
```

## Data Flow

```
ObservedAction stream
      │
      ▼
┌──────────────────────┐
│  Action Log          │  Per-agent bounded deque (1000)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐     ┌───────────────────┐
│  Plan Library Scan   │◄────│  PlanTemplate[]   │
│  Match action vs     │     │  goal → actions   │
│  templates           │     └───────────────────┘
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Bayesian Update     │  P(goal|obs) ∝ P(obs|goal) × P(goal)
│  Normalize across    │  Competing hypotheses sum to 1.0
│  hypotheses          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Prune + Predict     │  Remove P < 0.01
│  Update next actions │  Compute predicted_next
└──────────┬───────────┘
           │
           ▼
    IntentionHypothesis[]
    (ranked by confidence)
```

## Integration Points

| Component | Direction | Interface |
|-----------|-----------|-----------|
| BeliefTracker 24.1 | ← input | Agent beliefs inform goal priors |
| PerspectiveTaker 24.3 | → output | Intentions feed perspective simulation |
| SocialPredictor 24.4 | → output | Intentions predict cooperation/defection |
| NegotiationEngine 12.2 | ← input | Negotiation moves as actions |
| CommunicationOrchestrator 19.5 | ← input | Messages as evidence |
| SocialOrchestrator 24.5 | → output | BDI state aggregation |

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_intention_observations_total` | Counter | Total actions observed |
| `asi_intention_hypotheses_active` | Gauge | Active hypotheses per agent |
| `asi_intention_inference_seconds` | Histogram | Inference latency |
| `asi_intention_predictions_accuracy` | Gauge | Rolling prediction accuracy |
| `asi_intention_prune_total` | Counter | Hypotheses pruned |

### PromQL Examples

```promql
rate(asi_intention_observations_total[5m])
avg(asi_intention_hypotheses_active) by (agent_id)
histogram_quantile(0.99, asi_intention_inference_seconds_bucket) > 0.5
```

## Test Targets (12)

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_observe_action_creates_hypothesis` | Template match → hypothesis |
| 2 | `test_bayesian_update_increases_confidence` | Consistent evidence raises posterior |
| 3 | `test_conflicting_action_decreases_confidence` | Off-plan lowers posterior |
| 4 | `test_infer_intention_top_k_ordering` | Sorted by descending confidence |
| 5 | `test_predict_next_action_marginalization` | Probabilities sum ≤ 1 |
| 6 | `test_plan_template_strict_sequence` | Strict requires exact order |
| 7 | `test_plan_template_flexible_any_order` | Flexible accepts permutations |
| 8 | `test_goal_achieved_status_transition` | → ACHIEVED on postconditions |
| 9 | `test_prune_removes_low_confidence` | Below-threshold removed |
| 10 | `test_bdi_state_consistency` | BDI beliefs ref matches tracker |
| 11 | `test_concurrent_multi_agent_isolation` | Agent A doesn't affect B |
| 12 | `test_null_intention_recognizer_no_ops` | Returns empty |

## Implementation Order

1. `GoalStatus` enum + `ObservedAction` dataclass
2. `PlanTemplate` dataclass
3. `IntentionHypothesis` + `BDIState` dataclasses
4. `IntentionRecognizer` Protocol
5. `ProbabilisticIntentionRecognizer.__init__`
6. `register_plan_template`
7. `observe_action` — Bayesian update + new hypothesis
8. `infer_intention` — ranked retrieval
9. `predict_next_action` — marginalization
10. `get_bdi_state` — compose BDI triple
11. `prune_hypotheses`
12. `NullIntentionRecognizer` no-op
13. `make_intention_recognizer()` factory
14. Metrics + tests

## Phase 24 Sub-phase Tracker

| # | Component | Issue | Status |
|---|-----------|-------|--------|
| 24.1 | BeliefTracker | [#546](https://github.com/web3guru888/asi-build/issues/546) | ✅ Spec'd |
| 24.2 | IntentionRecognizer | [#547](https://github.com/web3guru888/asi-build/issues/547) | ✅ Spec'd |
| 24.3 | PerspectiveTaker | [#548](https://github.com/web3guru888/asi-build/issues/548) | ✅ Spec'd |
| 24.4 | SocialPredictor | [#549](https://github.com/web3guru888/asi-build/issues/549) | ✅ Spec'd |
| 24.5 | SocialOrchestrator | [#550](https://github.com/web3guru888/asi-build/issues/550) | ✅ Spec'd |
