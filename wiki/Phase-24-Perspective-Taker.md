# Phase 24.3 — PerspectiveTaker: Recursive Viewpoint Simulation & Level-k Reasoning

> **Issue**: [#548](https://github.com/web3guru888/asi-build/issues/548) | **Show & Tell**: [#555](https://github.com/web3guru888/asi-build/discussions/555) | **Q&A**: [#556](https://github.com/web3guru888/asi-build/discussions/556)

## Overview

The `PerspectiveTaker` implements the core Theory of Mind capability: **simulating another agent's reasoning from their information state**. Using Level-k reasoning (Stahl & Wilson 1994) and Cognitive Hierarchy Theory (Camerer, Ho, Chong 2004), it supports recursive mental simulation with configurable depth and bounded rationality.

This is the computational equivalent of the Sally-Anne false-belief test, extended to arbitrary strategic reasoning depth.

## Theoretical Foundations

### Level-k Reasoning (Stahl & Wilson 1994)

A hierarchy of increasingly sophisticated strategic thinkers:

| Level | Assumption about opponents | Strategy |
|-------|---------------------------|----------|
| Level-0 | N/A (anchor) | Random / heuristic |
| Level-1 | Opponents are Level-0 | Best-respond to random |
| Level-2 | Opponents are Level-1 | Best-respond to strategic |
| Level-3 | Opponents are Level-2 | Best-respond to recursive |
| Level-k | Opponents are Level-(k-1) | Recursive best-response |

### Cognitive Hierarchy Theory (Camerer et al. 2004)

Rather than assuming all opponents are at one level below, agents at level k believe opponents are *distributed* over levels 0..k-1:

```
P(opponent at level j | my level = k) = Poisson(j; τ) / Σ_{m=0}^{k-1} Poisson(m; τ)
```

For τ = 1.5 (empirical mean from laboratory games):

| My Level | P(opp=0) | P(opp=1) | P(opp=2) | P(opp=3) |
|----------|----------|----------|----------|----------|
| k=1 | 1.00 | — | — | — |
| k=2 | 0.40 | 0.60 | — | — |
| k=3 | 0.21 | 0.32 | 0.47 | — |
| k=4 | 0.13 | 0.19 | 0.29 | 0.39 |

### Sally-Anne Test (Baron-Cohen et al. 1985)

The canonical false-belief test:
1. Sally puts marble in basket A
2. Sally leaves
3. Anne moves marble to basket B
4. **Question**: Where does Sally look for the marble?

**Correct ToM answer**: Basket A (Sally's false belief)
**Failing answer**: Basket B (projects own knowledge)

## Data Structures

### Enums

```python
class ReasoningLevel(enum.IntEnum):
    NAIVE = 0       # Random / heuristic
    STRATEGIC = 1   # Best-respond to naive
    RECURSIVE = 2   # Best-respond to strategic
    DEEP = 3        # Best-respond to recursive
    EXPERT = 4      # Maximum practical depth
```

### Frozen Dataclasses

```python
@dataclass(frozen=True)
class Perspective:
    agent_id: str
    visible_state: Mapping[str, Any]     # Observable by agent
    believed_state: Mapping[str, Any]    # Agent's beliefs (may ≠ truth)
    inferred_goals: tuple[str, ...]
    reasoning_level: ReasoningLevel
    reasoning_model: str                 # "bayesian" | "heuristic" | "bounded_rational"
    confidence: float

@dataclass(frozen=True)
class CommonGround:
    agents: tuple[str, ...]
    shared_beliefs: FrozenSet[str]
    shared_goals: tuple[str, ...]
    disagreements: tuple[str, ...]
    alignment_score: float

@dataclass(frozen=True)
class SimulationResult:
    agent_id: str
    perspective: Perspective
    predicted_action: str
    predicted_reasoning: str
    alternatives: tuple[tuple[str, float], ...]
    simulation_depth: int
    computation_ms: int

@dataclass(frozen=True)
class PerspectiveConfig:
    max_recursion_depth: int = 3
    timeout_ms: int = 500
    cognitive_hierarchy_tau: float = 1.5
    bounded_rationality: float = 0.9
    false_belief_enabled: bool = True
```

## Protocol

```python
@runtime_checkable
class PerspectiveTaker(Protocol):
    async def take_perspective(self, agent_id: str,
                               context: Mapping[str, Any] | None = None) -> Perspective: ...
    async def simulate_reasoning(self, agent_id: str, decision_context: Mapping[str, Any],
                                  level: ReasoningLevel = ReasoningLevel.STRATEGIC) -> SimulationResult: ...
    async def predict_response(self, agent_id: str, our_action: str,
                                context: Mapping[str, Any] | None = None) -> SimulationResult: ...
    async def evaluate_common_ground(self, agent_ids: tuple[str, ...]) -> CommonGround: ...
    async def check_false_belief(self, agent_id: str, proposition: str,
                                  ground_truth: bool) -> tuple[bool, float]: ...
```

## Implementation: RecursivePerspectiveTaker

### Internal State

```python
class RecursivePerspectiveTaker:
    _belief_tracker: BeliefTracker
    _intention_recognizer: IntentionRecognizer
    _empathy_engine: EmpathyEngine
    _config: PerspectiveConfig
    _simulation_cache: LRUCache[str, SimulationResult]  # Size 256
    _lock: asyncio.Lock
```

### Core Algorithm — simulate_reasoning

```python
async def simulate_reasoning(self, agent_id, decision_context, level=ReasoningLevel.STRATEGIC):
    # Check cache
    cache_key = (agent_id, self._hash_context(decision_context), int(level))
    if cache_key in self._simulation_cache:
        return self._simulation_cache[cache_key]
    
    t0 = time.monotonic_ns()
    perspective = await self.take_perspective(agent_id)
    
    if level == ReasoningLevel.NAIVE:
        # Level 0: uniform random
        actions = self._legal_actions(decision_context, perspective)
        action = random.choice(actions)
        probs = [(a, 1.0 / len(actions)) for a in actions]
    else:
        # Cognitive hierarchy weights
        weights = self._ch_weights(int(level))
        
        # Model opponents at each level
        opponents = decision_context.get("opponents", [])
        opponent_models = {}
        for opp_id in opponents:
            weighted_actions = []
            for j, w in enumerate(weights):
                sim = await self.simulate_reasoning(opp_id, decision_context, ReasoningLevel(j))
                weighted_actions.append((sim.predicted_action, w))
            opponent_models[opp_id] = weighted_actions
        
        # Best response given opponent models
        actions = self._legal_actions(decision_context, perspective)
        action_values = {}
        for a in actions:
            ev = self._expected_value(a, opponent_models, perspective)
            action_values[a] = ev
        
        # Softmax (bounded rationality)
        temp = 1.0 / self._config.bounded_rationality
        probs = self._softmax(action_values, temp)
        action = max(probs, key=lambda x: x[1])[0]
    
    computation_ms = (time.monotonic_ns() - t0) // 1_000_000
    result = SimulationResult(agent_id, perspective, action, 
                               f"Level-{level} best response", 
                               tuple(probs), int(level), computation_ms)
    self._simulation_cache[cache_key] = result
    return result
```

### Cognitive Hierarchy Weights

```python
def _ch_weights(self, k: int) -> list[float]:
    tau = self._config.cognitive_hierarchy_tau
    raw = [math.exp(-tau) * tau**j / math.factorial(j) for j in range(k)]
    total = sum(raw)
    return [w / total for w in raw] if total > 0 else [1.0 / k] * k
```

### Sally-Anne Implementation

```python
async def check_false_belief(self, agent_id, proposition, ground_truth):
    if not self._config.false_belief_enabled:
        return (False, 0.0)
    entry = await self._belief_tracker.query_belief(
        agent_id, Proposition(proposition, ())
    )
    if entry is None:
        return (False, 0.5)  # No model
    agent_believes_true = entry.posterior > 0.5
    has_false_belief = agent_believes_true != ground_truth
    confidence = abs(entry.posterior - 0.5) * 2.0
    return (has_false_belief, confidence)
```

### Cache Invalidation

```python
def _invalidate_cache(self, agent_id: str):
    """Called when BeliefTracker updates agent's model."""
    keys_to_evict = [k for k in self._simulation_cache if k[0] == agent_id]
    for k in keys_to_evict:
        del self._simulation_cache[k]
```

### Timeout Enforcement

```python
async def simulate_reasoning(self, agent_id, context, level):
    try:
        return await asyncio.wait_for(
            self._simulate_inner(agent_id, context, level),
            timeout=self._config.timeout_ms / 1000.0
        )
    except asyncio.TimeoutError:
        # Fall back to lower level
        for fl in range(int(level) - 1, -1, -1):
            cached = self._simulation_cache.get((agent_id, self._hash_context(context), fl))
            if cached:
                return cached
        return self._default_result(agent_id)
```

## Data Flow

```
take_perspective(agent_id)
         │
         ├── BeliefTracker 24.1 → believed_state
         ├── IntentionRecognizer 24.2 → inferred_goals
         └── EmpathyEngine 21.3 → emotional coloring
                    │
                    ▼
            Perspective (may contain false beliefs!)
                    │
                    ▼
simulate_reasoning(agent_id, context, level=k)
         │
         ├── Cache check (LRU)
         │
         ├── if k=0: uniform random
         │
         └── if k>0:
              ├── CH weights for levels 0..k-1
              ├── Recursive simulate for each opponent
              ├── Best response given opponent models
              └── Softmax (bounded rationality)
                    │
                    ▼
            SimulationResult
```

## Integration Points

| Component | Direction | Interface |
|-----------|-----------|-----------|
| BeliefTracker 24.1 | ← input | Epistemic state |
| IntentionRecognizer 24.2 | ← input | Goals for perspective |
| EmpathyEngine 21.3 | ← input | Emotional coloring |
| SocialPredictor 24.4 | → output | Perspectives inform predictions |
| SocialOrchestrator 24.5 | → output | Simulation results |
| DecisionOrchestrator 23.5 | → output | Perspective-aware decisions |

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_perspective_simulations_total` | Counter | Total simulations |
| `asi_perspective_recursion_depth` | Histogram | Depth distribution |
| `asi_perspective_simulation_seconds` | Histogram | Wall time |
| `asi_perspective_cache_hit_ratio` | Gauge | LRU cache hit rate |
| `asi_perspective_false_beliefs_detected` | Counter | False beliefs found |

## Test Targets (12)

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_take_perspective_filters_by_belief` | Reflects agent's beliefs, not truth |
| 2 | `test_level_0_uniform_random` | Level-0 = uniform |
| 3 | `test_level_1_best_responds_to_naive` | Level-1 optimizes vs random |
| 4 | `test_level_2_recursion_correct` | Level-2 reasons about Level-1 |
| 5 | `test_cognitive_hierarchy_poisson_weights` | Weights follow Poisson |
| 6 | `test_false_belief_detection` | Sally-Anne passes |
| 7 | `test_common_ground_intersection` | Shared = intersection |
| 8 | `test_bounded_rationality_softmax` | Temperature modulates randomness |
| 9 | `test_simulation_cache_invalidation` | Cache cleared on belief update |
| 10 | `test_predict_response_to_our_action` | Counter-factual reasoning |
| 11 | `test_timeout_respected` | Aborts within timeout_ms |
| 12 | `test_null_perspective_taker_no_ops` | Returns defaults |

## Implementation Order

1. `ReasoningLevel` enum
2. `Perspective` + `CommonGround` + `SimulationResult` dataclasses
3. `PerspectiveConfig` dataclass
4. `PerspectiveTaker` Protocol
5. `RecursivePerspectiveTaker.__init__`
6. `take_perspective` — belief-filtered state
7. `simulate_reasoning` — recursive Level-k
8. `predict_response` — counter-factual
9. `evaluate_common_ground` — intersection
10. `check_false_belief` — Sally-Anne
11. `NullPerspectiveTaker` no-op
12. `make_perspective_taker()` factory
13. Metrics + tests
14. Cache invalidation hooks

## Phase 24 Sub-phase Tracker

| # | Component | Issue | Status |
|---|-----------|-------|--------|
| 24.1 | BeliefTracker | [#546](https://github.com/web3guru888/asi-build/issues/546) | ✅ Spec'd |
| 24.2 | IntentionRecognizer | [#547](https://github.com/web3guru888/asi-build/issues/547) | ✅ Spec'd |
| 24.3 | PerspectiveTaker | [#548](https://github.com/web3guru888/asi-build/issues/548) | ✅ Spec'd |
| 24.4 | SocialPredictor | [#549](https://github.com/web3guru888/asi-build/issues/549) | ✅ Spec'd |
| 24.5 | SocialOrchestrator | [#550](https://github.com/web3guru888/asi-build/issues/550) | ✅ Spec'd |
