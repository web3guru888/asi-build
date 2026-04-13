# Phase 24.4 — SocialPredictor: Trust Networks, Coalition Dynamics & Group Behavior

> **Issue**: [#549](https://github.com/web3guru888/asi-build/issues/549) | **Show & Tell**: [#557](https://github.com/web3guru888/asi-build/discussions/557) | **Q&A**: [#558](https://github.com/web3guru888/asi-build/discussions/558)

## Overview

The `SocialPredictor` models and predicts **social dynamics** across multi-agent systems: trust evolution, coalition formation and dissolution, reputation propagation, and emergent group behaviors. It combines game-theoretic analysis (Shapley values), trust network propagation (Marsh 1994), and evolutionary game dynamics (replicator equations).

## Theoretical Foundations

### Trust Networks (Marsh 1994)

Trust is modeled as a directed weighted graph where edge weights represent directed trust scores in [0, 1]. Key properties:
- **Asymmetric**: T(A→B) ≠ T(B→A)
- **Transitive** (with decay): T(A→C) ≈ T(A→B) × T(B→C) × discount
- **Dynamic**: Trust evolves with interaction outcomes
- **Contextual**: Trust can vary by domain

### Shapley Value (1953)

The unique value allocation satisfying efficiency, symmetry, null player, and additivity:

```
φᵢ(v) = Σ_{S ⊆ N\{i}} [|S|!(|N|-|S|-1)! / |N|!] × [v(S∪{i}) - v(S)]
```

Interpretation: agent i's expected marginal contribution, averaged over all possible orderings of agents.

### Cooperative Game Theory — The Core

A coalition structure is in the **core** if no sub-coalition can improve by deviating:

```
∀ S ⊆ N: Σ_{i∈S} xᵢ ≥ v(S)
```

Where xᵢ is agent i's allocation and v(S) is the coalition value function.

### Replicator Dynamics

Evolutionary model for strategy frequency evolution:

```
ẋᵢ = xᵢ × (fᵢ - φ̄)
```

Where xᵢ = proportion using strategy i, fᵢ = fitness of strategy i, φ̄ = mean fitness.

## Data Structures

### Enums

```python
class RelationshipType(enum.Enum):
    COOPERATIVE = "cooperative"
    COMPETITIVE = "competitive"
    NEUTRAL = "neutral"
    ADVERSARIAL = "adversarial"
    DEPENDENT = "dependent"

class TrustLevel(enum.Enum):
    BLIND_TRUST = "blind_trust"      # > 0.9
    HIGH_TRUST = "high_trust"        # 0.7 - 0.9
    MODERATE_TRUST = "moderate"      # 0.4 - 0.7
    LOW_TRUST = "low_trust"          # 0.1 - 0.4
    DISTRUST = "distrust"            # < 0.1
```

### Frozen Dataclasses

```python
@dataclass(frozen=True)
class AgentRelationship:
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    trust_score: float
    interaction_count: int
    last_interaction_ms: int
    reciprocity: float           # [-1, 1]

@dataclass(frozen=True)
class Coalition:
    coalition_id: str
    members: FrozenSet[str]
    formation_ms: int
    stability: float             # [0, 1]
    shared_goals: tuple[str, ...]
    shapley_values: Mapping[str, float]
    total_value: float

@dataclass(frozen=True)
class SocialGraph:
    agents: tuple[str, ...]
    relationships: tuple[AgentRelationship, ...]
    trust_matrix: Mapping[str, Mapping[str, float]]
    coalitions: tuple[Coalition, ...]
    clustering_coefficient: float
    average_trust: float
    timestamp_ms: int

@dataclass(frozen=True)
class SocialPrediction:
    prediction_type: str         # "coalition_formation" | "trust_change" | "defection"
    agents_involved: tuple[str, ...]
    probability: float
    time_horizon_ms: int
    reasoning: str
    confidence: float

@dataclass(frozen=True)
class SocialPredictorConfig:
    trust_decay_rate: float = 0.01
    trust_propagation_depth: int = 3
    trust_propagation_discount: float = 0.5
    shapley_sampling_n: int = 1000
    coalition_min_stability: float = 0.3
    replicator_dt: float = 0.1
```

## Protocol

```python
@runtime_checkable
class SocialPredictor(Protocol):
    async def predict_behavior(self, agent_id: str,
                                context: Mapping[str, Any]) -> tuple[SocialPrediction, ...]: ...
    async def forecast_coalition(self, agents: tuple[str, ...],
                                  time_horizon_ms: int) -> tuple[Coalition, ...]: ...
    async def update_trust(self, source_id: str, target_id: str, outcome: float) -> float: ...
    async def propagate_trust(self) -> int: ...
    async def get_social_graph(self) -> SocialGraph: ...
    async def get_social_dynamics(self, time_steps: int = 10) -> tuple[SocialGraph, ...]: ...
    async def compute_shapley_values(self, agents: tuple[str, ...], value_fn: Any) -> Mapping[str, float]: ...
```

## Implementation: GraphSocialPredictor

### Internal State

```python
class GraphSocialPredictor:
    _trust_matrix: dict[str, dict[str, float]]
    _relationships: dict[tuple[str, str], AgentRelationship]
    _coalitions: list[Coalition]
    _interaction_history: dict[tuple[str, str], deque[float]]
    _perspective_taker: PerspectiveTaker
    _config: SocialPredictorConfig
    _lock: asyncio.Lock
```

### Trust Update — Adaptive Learning Rate

```python
async def update_trust(self, source_id, target_id, outcome):
    async with self._lock:
        current = self._trust_matrix.get(source_id, {}).get(target_id, 0.5)
        surprise = abs(outcome - current)
        alpha = 0.1 * (1.0 + surprise)  # Adaptive: higher surprise → faster learn
        new_trust = current + alpha * (outcome - current)
        new_trust = max(0.0, min(1.0, new_trust))
        self._trust_matrix.setdefault(source_id, {})[target_id] = new_trust
        
        # Update relationship type
        if new_trust > 0.7:
            rel_type = RelationshipType.COOPERATIVE
        elif new_trust > 0.4:
            rel_type = RelationshipType.NEUTRAL
        elif new_trust > 0.1:
            rel_type = RelationshipType.COMPETITIVE
        else:
            rel_type = RelationshipType.ADVERSARIAL
        
        self._relationships[(source_id, target_id)] = AgentRelationship(
            source_id, target_id, rel_type, new_trust, ..., now_ms(), ...
        )
        return new_trust
```

### Trust Propagation — BFS

```python
async def propagate_trust(self):
    updated = 0
    async with self._lock:
        for source in list(self._trust_matrix.keys()):
            visited = {source}
            queue = deque([(source, 1.0, 0)])
            while queue:
                current, acc_trust, depth = queue.popleft()
                if depth >= self._config.trust_propagation_depth:
                    continue
                for target, direct_trust in self._trust_matrix.get(current, {}).items():
                    if target in visited or target == source:
                        continue
                    visited.add(target)
                    transitive = acc_trust * direct_trust * self._config.trust_propagation_discount
                    existing = self._trust_matrix.get(source, {}).get(target, 0.0)
                    if transitive > existing:
                        self._trust_matrix.setdefault(source, {})[target] = transitive
                        updated += 1
                    queue.append((target, transitive, depth + 1))
    return updated
```

### Shapley Value — Monte Carlo

```python
async def compute_shapley_values(self, agents, value_fn):
    n = len(agents)
    shapley = {a: 0.0 for a in agents}
    agents_list = list(agents)
    
    for _ in range(self._config.shapley_sampling_n):
        random.shuffle(agents_list)
        prev_value = 0.0
        for i, agent in enumerate(agents_list):
            coalition = frozenset(agents_list[:i + 1])
            curr_value = await value_fn(coalition)
            marginal = curr_value - prev_value
            shapley[agent] += marginal / self._config.shapley_sampling_n
            prev_value = curr_value
    
    return shapley
```

### Coalition Formation

```python
async def forecast_coalition(self, agents, time_horizon_ms):
    # Step 1: Compute pairwise cooperation potential
    potential = {}
    for a in agents:
        for b in agents:
            if a != b:
                t_ab = self._trust_matrix.get(a, {}).get(b, 0.5)
                t_ba = self._trust_matrix.get(b, {}).get(a, 0.5)
                potential[(a, b)] = t_ab * t_ba  # Mutual trust
    
    # Step 2: Hierarchical clustering
    clusters = self._hierarchical_cluster(agents, potential)
    
    # Step 3: Evaluate each cluster as coalition
    coalitions = []
    for cluster in clusters:
        members = frozenset(cluster)
        value = sum(potential.get((a, b), 0) for a in cluster for b in cluster if a != b)
        shapley = await self.compute_shapley_values(tuple(cluster), 
                                                      lambda s: sum(potential.get((a,b),0) for a in s for b in s if a!=b))
        stability = self._core_stability(members, shapley, potential)
        
        if stability >= self._config.coalition_min_stability:
            coalitions.append(Coalition(
                f"coalition_{hash(members)}", members, now_ms(),
                stability, (), shapley, value
            ))
    
    return tuple(sorted(coalitions, key=lambda c: -c.total_value))
```

### Replicator Dynamics

```python
async def get_social_dynamics(self, time_steps=10):
    snapshots = [await self.get_social_graph()]
    strategies = self._extract_strategy_proportions()
    payoff = self._compute_payoff_matrix()
    
    for _ in range(time_steps):
        fitness = payoff @ strategies
        avg_fitness = strategies @ fitness
        if avg_fitness > 0:
            strategies = strategies * fitness / avg_fitness
            strategies = np.clip(strategies, 1e-10, None)
            strategies /= strategies.sum()
        
        self._apply_strategy_proportions(strategies)
        snapshots.append(await self.get_social_graph())
    
    return tuple(snapshots)
```

## Data Flow

```
Interaction Outcome (cooperation/betrayal)
         │
         ▼
┌────────────────────────────┐
│  Trust Update              │  α = 0.1 × (1 + surprise)
│  Adaptive learning rate    │  T_new = T_old + α(O - T_old)
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐
│  Trust Propagation (BFS)   │  Transitive trust
│  Up to depth 3             │  T(A,C) = max(T(A,B)×T(B,C)×d)
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐
│  Coalition Analysis        │  Mutual trust clustering
│  Shapley values            │  Core stability check
│  Core stability            │
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐
│  Replicator Dynamics       │  Strategy evolution
│  Evolutionary forecast     │  Convergence to ESS
└────────┬───────────────────┘
         │
         ▼
    SocialGraph + Predictions
```

## Integration Points

| Component | Direction | Interface |
|-----------|-----------|-----------|
| PerspectiveTaker 24.3 | ← input | Perspectives inform trust |
| ConsensusVoting 12.4 | ← input | Voting → coalition signals |
| AffectiveOrchestrator 21.5 | ← input | Emotions modulate trust |
| IntentionRecognizer 24.2 | ← input | Intentions predict cooperation |
| SocialOrchestrator 24.5 | → output | Graph + predictions |
| NegotiationEngine 12.2 | → output | Trust informs negotiation |

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_social_trust_updates_total` | Counter | Trust updates |
| `asi_social_coalitions_active` | Gauge | Active coalitions |
| `asi_social_trust_propagation_seconds` | Histogram | Propagation time |
| `asi_social_shapley_computation_seconds` | Histogram | Shapley computation |
| `asi_social_prediction_accuracy` | Gauge | Rolling accuracy |

## Test Targets (12)

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_trust_update_learning_rate` | Moves toward outcome at rate α |
| 2 | `test_trust_update_clamp_bounds` | Stays in [0, 1] |
| 3 | `test_trust_propagation_transitive` | T(A,C) from T(A,B)×T(B,C) |
| 4 | `test_trust_propagation_depth_limit` | No beyond depth |
| 5 | `test_shapley_values_efficiency` | Sum to v(N) |
| 6 | `test_shapley_values_symmetry` | Equal → equal share |
| 7 | `test_coalition_stability_core` | Stable satisfies core |
| 8 | `test_coalition_dissolution_prediction` | Low stability → dissolution |
| 9 | `test_replicator_dynamics_convergence` | Converges to ESS |
| 10 | `test_social_graph_snapshot_consistency` | Reflects current state |
| 11 | `test_trust_decay_without_interaction` | Decays toward 0.5 |
| 12 | `test_null_social_predictor_no_ops` | Returns empty graph |

## Implementation Order

1. `RelationshipType` + `TrustLevel` enums
2. `AgentRelationship` + `Coalition` dataclasses
3. `SocialGraph` + `SocialPrediction` dataclasses
4. `SocialPredictorConfig` dataclass
5. `SocialPredictor` Protocol
6. `GraphSocialPredictor.__init__`
7. `update_trust` — adaptive learning rate
8. `propagate_trust` — BFS transitive
9. `compute_shapley_values` — Monte Carlo
10. `forecast_coalition` — core + stability
11. `predict_behavior` — composite prediction
12. `get_social_dynamics` — replicator
13. `NullSocialPredictor` no-op
14. `make_social_predictor()` factory + metrics + tests

## Phase 24 Sub-phase Tracker

| # | Component | Issue | Status |
|---|-----------|-------|--------|
| 24.1 | BeliefTracker | [#546](https://github.com/web3guru888/asi-build/issues/546) | ✅ Spec'd |
| 24.2 | IntentionRecognizer | [#547](https://github.com/web3guru888/asi-build/issues/547) | ✅ Spec'd |
| 24.3 | PerspectiveTaker | [#548](https://github.com/web3guru888/asi-build/issues/548) | ✅ Spec'd |
| 24.4 | SocialPredictor | [#549](https://github.com/web3guru888/asi-build/issues/549) | ✅ Spec'd |
| 24.5 | SocialOrchestrator | [#550](https://github.com/web3guru888/asi-build/issues/550) | ✅ Spec'd |
