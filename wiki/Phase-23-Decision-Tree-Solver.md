# Phase 23.4 — DecisionTreeSolver

> **Status**: ✅ Spec Complete
> **Tracks**: Phase 23 — Decision Intelligence & Uncertainty Management
> **Depends on**: UncertaintyQuantifier (23.1), RiskAssessor (23.2), UtilityComputer (23.3)
> **Feeds into**: DecisionOrchestrator (23.5)

---

## Overview

The **DecisionTreeSolver** provides algorithmic decision-making through tree search, game-theoretic reasoning, and information-theoretic analysis. It unifies backward induction, minimax with alpha-beta pruning, expectimax, Monte Carlo Tree Search (MCTS), and Value of Information (VoI) computation into a single adaptive solver.

Key theoretical foundations:
- **Decision trees & backward induction** — Raiffa (1968)
- **Minimax + alpha-beta pruning** — Knuth & Moore (1975)
- **Expectimax** — Michie (1966); chance-node extension of minimax
- **Monte Carlo Tree Search (MCTS)** — Kocsis & Szepesvári (2006), UCB1 = V̄ + C√(ln N / n)
- **Value of Information** — Howard (1966); VoI = EU(with info) - EU(without info)

---

## Enums

### `NodeType`

```python
class NodeType(str, Enum):
    """Type of node in a decision tree."""
    DECISION = "decision"        # Agent chooses action (max node)
    CHANCE = "chance"            # Nature chooses outcome (expectation node)
    TERMINAL = "terminal"        # Leaf with payoff
    OPPONENT = "opponent"        # Adversary chooses action (min node)
```

### `SolverStrategy`

```python
class SolverStrategy(str, Enum):
    """Algorithm selection for tree solving."""
    BACKWARD_INDUCTION = "backward_induction"  # Exact solve via dynamic programming
    MINIMAX = "minimax"                        # Min-max with alpha-beta pruning
    EXPECTIMAX = "expectimax"                  # Expected value at chance nodes
    MCTS = "mcts"                              # Monte Carlo Tree Search with UCB1
    ADAPTIVE = "adaptive"                      # Auto-select based on tree properties
```

---

## Frozen Dataclasses

### `DecisionNode`

```python
@dataclass(frozen=True)
class DecisionNode:
    """A node in the decision tree."""
    id: str                                        # Unique node identifier
    node_type: NodeType                            # DECISION / CHANCE / TERMINAL / OPPONENT
    label: str = ""                                # Human-readable description
    payoff: float | None = None                    # Only for TERMINAL nodes
    probability: float | None = None               # Only for CHANCE children (edge prob)
    children: tuple["DecisionNode", ...] = ()      # Child nodes
    actions: tuple[str, ...] = ()                  # Action labels (DECISION/OPPONENT nodes)
    uncertainty: UncertaintyEstimate | None = None  # From 23.1
    metadata: dict[str, Any] = field(default_factory=dict)
```

### `MCTSConfig`

```python
@dataclass(frozen=True)
class MCTSConfig:
    """Configuration for Monte Carlo Tree Search."""
    num_simulations: int = 10_000                  # Rollout count
    exploration_constant: float = 1.414            # C in UCB1 = V̄ + C√(ln N/n)
    max_depth: int = 50                            # Maximum rollout depth
    rollout_policy: str = "random"                 # random | heuristic | neural
    discount_factor: float = 1.0                   # γ for discounted returns
    temperature: float = 1.0                       # Action selection temperature
    progressive_widening: bool = False             # Limit branching factor
    widening_alpha: float = 0.5                    # k = N^α children allowed
```

### `SolverResult`

```python
@dataclass(frozen=True)
class SolverResult:
    """Result from solving a decision tree."""
    optimal_action: str                            # Best action at root
    expected_value: float                          # Expected payoff of optimal action
    strategy_used: SolverStrategy                  # Which algorithm was applied
    action_values: dict[str, float] = field(default_factory=dict)  # Q(a) per action
    visit_counts: dict[str, int] = field(default_factory=dict)     # N(a) for MCTS
    tree_depth: int = 0                            # Depth explored
    nodes_evaluated: int = 0                       # Total nodes visited
    voi_scores: dict[str, float] = field(default_factory=dict)     # Value of Information
    computation_time_s: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
```

### `SolverConfig`

```python
@dataclass(frozen=True)
class SolverConfig:
    """Configuration for DecisionTreeSolver."""
    default_strategy: SolverStrategy = SolverStrategy.ADAPTIVE
    mcts_config: MCTSConfig = MCTSConfig()
    alpha_beta_pruning: bool = True                # Enable pruning in minimax
    max_tree_size: int = 1_000_000                 # Safety limit on node count
    timeout_s: float = 30.0                        # Max solve time
    voi_sample_count: int = 1_000                  # Samples for VoI estimation
    adaptive_threshold: int = 10_000               # Nodes above this → MCTS
```

---

## Protocol

```python
@runtime_checkable
class DecisionTreeSolver(Protocol):
    """Solves decision trees using multiple algorithms."""

    async def solve(
        self,
        root: DecisionNode,
        *,
        strategy: SolverStrategy | None = None,
    ) -> SolverResult:
        """Solve the decision tree from root. Returns optimal action + value."""
        ...

    async def mcts_search(
        self,
        root: DecisionNode,
        *,
        config: MCTSConfig | None = None,
    ) -> SolverResult:
        """Run MCTS from root node."""
        ...

    async def value_of_information(
        self,
        root: DecisionNode,
        observable: str,
    ) -> float:
        """Compute VoI for observing a chance variable before deciding."""
        ...

    async def minimax(
        self,
        root: DecisionNode,
        *,
        alpha: float = float("-inf"),
        beta: float = float("inf"),
    ) -> SolverResult:
        """Minimax search with optional alpha-beta pruning."""
        ...
```

---

## Implementation — `AdaptiveDecisionTreeSolver`

```python
class AdaptiveDecisionTreeSolver:
    """
    Production implementation of DecisionTreeSolver.

    Strategy selection (ADAPTIVE mode):
      - tree_size < adaptive_threshold AND no CHANCE nodes → MINIMAX
      - tree_size < adaptive_threshold AND has CHANCE nodes → EXPECTIMAX
      - tree_size ≥ adaptive_threshold → MCTS
      - only DECISION + TERMINAL → BACKWARD_INDUCTION

    Backward Induction:
      - Post-order traversal
      - TERMINAL → return payoff
      - DECISION → max over children
      - CHANCE   → Σ p_i · V(child_i)

    Minimax with Alpha-Beta:
      - DECISION (max) → α = max(α, V(child))
      - OPPONENT (min) → β = min(β, V(child))
      - Prune when α ≥ β
      - CHANCE nodes → expectimax extension

    Expectimax:
      - Like minimax but CHANCE nodes compute E[V] instead of min/max
      - No pruning at chance nodes (expectation cannot be bounded)

    MCTS (UCB1):
      Selection:   argmax_a [ Q(a)/N(a) + C·√(ln N_parent / N(a)) ]
      Expansion:   add one unvisited child
      Simulation:  random rollout to depth limit → payoff
      Backprop:    update Q(a) and N(a) up the tree

    Value of Information:
      VoI(X) = E_x[ max_a EU(a | X=x) ] - max_a EU(a)
      Estimated via Monte Carlo: sample x ~ P(X), solve conditioned tree
    """

    def __init__(self, config: SolverConfig | None = None) -> None:
        self._config = config or SolverConfig()

    async def solve(
        self,
        root: DecisionNode,
        *,
        strategy: SolverStrategy | None = None,
    ) -> SolverResult:
        """
        1. Count tree size
        2. If strategy is ADAPTIVE → _select_strategy(root, size)
        3. Dispatch to appropriate algorithm
        4. Wrap in SolverResult with timing
        """
        ...

    async def mcts_search(
        self,
        root: DecisionNode,
        *,
        config: MCTSConfig | None = None,
    ) -> SolverResult:
        """
        for i in range(num_simulations):
          1. SELECT: tree-walk using UCB1
          2. EXPAND: add unvisited child
          3. SIMULATE: rollout to terminal/depth
          4. BACKPROPAGATE: update Q, N up path
        Return: action with highest visit count at root
        """
        ...

    async def value_of_information(
        self,
        root: DecisionNode,
        observable: str,
    ) -> float:
        """
        1. Solve tree without information → EU_prior
        2. For s in range(voi_sample_count):
             sample observable value x_s
             condition tree on X = x_s
             solve conditioned tree → EU_s
        3. VoI = mean(EU_s) - EU_prior
        """
        ...

    async def minimax(
        self,
        root: DecisionNode,
        *,
        alpha: float = float("-inf"),
        beta: float = float("inf"),
    ) -> SolverResult:
        """
        Recursive minimax with alpha-beta pruning.
        DECISION → maximise, update α
        OPPONENT → minimise, update β
        CHANCE   → weighted expectation (no pruning)
        TERMINAL → return payoff
        """
        ...

    def _select_strategy(self, root: DecisionNode, size: int) -> SolverStrategy:
        has_chance = self._has_node_type(root, NodeType.CHANCE)
        has_opponent = self._has_node_type(root, NodeType.OPPONENT)
        if size < self._config.adaptive_threshold:
            if has_opponent: return SolverStrategy.MINIMAX
            if has_chance: return SolverStrategy.EXPECTIMAX
            return SolverStrategy.BACKWARD_INDUCTION
        return SolverStrategy.MCTS
```

---

## Null Implementation

```python
class NullDecisionTreeSolver:
    """No-op for testing and DI wiring."""

    async def solve(self, root, *, strategy=None):
        action = root.actions[0] if root.actions else "noop"
        return SolverResult(optimal_action=action, expected_value=0.0,
                            strategy_used=SolverStrategy.BACKWARD_INDUCTION)

    async def mcts_search(self, root, *, config=None):
        return await self.solve(root)

    async def value_of_information(self, root, observable):
        return 0.0

    async def minimax(self, root, *, alpha=float("-inf"), beta=float("inf")):
        return await self.solve(root)
```

---

## Factory

```python
def make_decision_tree_solver(
    config: SolverConfig | None = None,
    *,
    null: bool = False,
) -> DecisionTreeSolver:
    if null:
        return NullDecisionTreeSolver()
    return AdaptiveDecisionTreeSolver(config)
```

---

## Data Flow

### Decision Tree Structure

```
                      ┌──────────────┐
                      │  DECISION    │  ← Agent chooses
                      │  "Invest?"   │
                      └──┬───────┬───┘
                    Buy  │       │ Hold
              ┌──────────▼──┐ ┌─▼──────────┐
              │   CHANCE    │ │  TERMINAL   │
              │  "Market"   │ │  payoff: 0  │
              └─┬────────┬──┘ └────────────┘
           Bull │    Bear│
          p=0.6 │  p=0.4│
         ┌──────▼──┐ ┌──▼──────┐
         │TERMINAL │ │TERMINAL │
         │ +100    │ │  -50    │
         └─────────┘ └─────────┘

    Backward Induction:
      CHANCE  = 0.6·100 + 0.4·(-50) = 40
      DECISION = max(40, 0) = 40 → "Buy"
```

### MCTS Loop

```
    ┌───────────────────────────────────────┐
    │           MCTS Iteration              │
    │                                       │
    │  1. SELECT (UCB1)                     │
    │     ┌──Root──┐                        │
    │     │ N=100  │                        │
    │     └─┬───┬──┘                        │
    │   A   │   │ B                         │
    │  Q=45 │   │ Q=38     UCB1(A) = 45/60 │
    │  N=60 │   │ N=40      + 1.41·√(ln100 │
    │       │   │                    /60)   │
    │  2. EXPAND                            │
    │     Add unvisited child C             │
    │                                       │
    │  3. SIMULATE                          │
    │     Random rollout → payoff = 72      │
    │                                       │
    │  4. BACKPROPAGATE                     │
    │     C: Q←72, N←1                      │
    │     A: Q←45+72=117, N←61              │
    │     Root: N←101                       │
    └───────────────────────────────────────┘
```

---

## Algorithm Comparison

| Algorithm | Tree Size | Chance Nodes | Opponent | Optimal | Time Complexity |
|-----------|-----------|-------------|----------|---------|-----------------|
| Backward Induction | Small | ✅ | ❌ | ✅ Exact | O(n) |
| Minimax + α-β | Small-Med | ❌ | ✅ | ✅ Exact | O(b^(d/2)) best |
| Expectimax | Small-Med | ✅ | ❌ | ✅ Exact | O(b^d) |
| MCTS (UCB1) | Any | ✅ | ✅ | ≈ Approx | O(simulations) |
| VoI | Any | ✅ | ❌ | — | O(samples · solve) |

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_solver_solve_total` | Counter | Total solve() calls |
| `asi_solver_solve_seconds` | Histogram | solve() latency |
| `asi_solver_strategy_used` | Counter (label: strategy) | Strategy selection distribution |
| `asi_solver_nodes_evaluated` | Histogram | Nodes visited per solve |
| `asi_solver_voi_computed_total` | Counter | VoI computations |

### PromQL Examples

```promql
# Solve rate
rate(asi_solver_solve_total[5m])

# Average nodes evaluated
histogram_quantile(0.50, asi_solver_nodes_evaluated_bucket)

# MCTS usage fraction
rate(asi_solver_strategy_used{strategy="mcts"}[1h]) / rate(asi_solver_solve_total[1h])
```

### Grafana Alerts

```yaml
- alert: SolverTimeout
  expr: histogram_quantile(0.99, asi_solver_solve_seconds_bucket) > 30.0
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "Decision tree solver p99 latency exceeds timeout (30s)"

- alert: ExcessiveTreeSize
  expr: histogram_quantile(0.99, asi_solver_nodes_evaluated_bucket) > 500000
  for: 10m
  labels: { severity: warning }
  annotations:
    summary: "Tree search evaluating >500K nodes — consider MCTS or pruning"

- alert: LowMCTSExploration
  expr: histogram_quantile(0.05, asi_solver_nodes_evaluated_bucket{strategy="mcts"}) < 100
  for: 5m
  labels: { severity: info }
  annotations:
    summary: "MCTS running with very few simulations — results may be unreliable"
```

---

## Integration Notes

| Component | Direction | Contract |
|-----------|-----------|----------|
| **UncertaintyQuantifier (23.1)** | ← upstream | `UncertaintyEstimate` attached to CHANCE nodes |
| **RiskAssessor (23.2)** | ← upstream | VaR/CVaR as terminal node payoff bounds |
| **UtilityComputer (23.3)** | ← upstream | Utility values assigned to terminal payoffs |
| **DecisionOrchestrator (23.5)** | → downstream | `SolverResult` feeds orchestrator pipeline |
| **ReasoningOrchestrator (20.5)** | ← upstream | Causal models structure tree topology |
| **GoalDecomposer (10.2)** | ← upstream | Sub-goals → decision node actions |

---

## Mypy Strict Compliance

| Check | Status |
|-------|--------|
| `--strict` | ✅ Required |
| `--warn-return-any` | ✅ |
| `--disallow-untyped-defs` | ✅ |
| `@runtime_checkable` Protocol | ✅ |
| Frozen dataclasses only | ✅ |

---

## Test Targets (12)

| # | Test | Focus |
|---|------|-------|
| 1 | `test_backward_induction_simple_tree` | Exact optimal action on 3-node tree |
| 2 | `test_minimax_selects_maximin` | OPPONENT minimises, DECISION maximises |
| 3 | `test_alpha_beta_prunes_correctly` | Fewer nodes evaluated than full minimax |
| 4 | `test_expectimax_weighted_average` | Chance node = Σ p_i · V(child_i) |
| 5 | `test_mcts_converges_to_optimal` | With enough simulations, matches exact |
| 6 | `test_mcts_ucb1_exploration` | Low-visit nodes get explored |
| 7 | `test_voi_positive_for_informative` | VoI > 0 when observation changes decision |
| 8 | `test_voi_zero_for_uninformative` | VoI = 0 when observation irrelevant |
| 9 | `test_adaptive_selects_mcts_for_large` | Trees > threshold → MCTS |
| 10 | `test_adaptive_selects_minimax_for_opponent` | Opponent nodes → minimax |
| 11 | `test_solver_respects_timeout` | Terminates within timeout_s |
| 12 | `test_null_solver_passthrough` | NullDecisionTreeSolver returns defaults |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_backward_induction_simple_tree():
    """Simple invest/hold tree should return 'buy' with EV=40."""
    solver = AdaptiveDecisionTreeSolver()
    tree = DecisionNode(
        id="root", node_type=NodeType.DECISION, actions=("buy", "hold"),
        children=(
            DecisionNode(id="market", node_type=NodeType.CHANCE, children=(
                DecisionNode(id="bull", node_type=NodeType.TERMINAL, payoff=100.0, probability=0.6),
                DecisionNode(id="bear", node_type=NodeType.TERMINAL, payoff=-50.0, probability=0.4),
            )),
            DecisionNode(id="hold", node_type=NodeType.TERMINAL, payoff=0.0),
        ),
    )
    result = await solver.solve(tree, strategy=SolverStrategy.BACKWARD_INDUCTION)
    assert result.optimal_action == "buy"
    assert abs(result.expected_value - 40.0) < 1e-9

@pytest.mark.asyncio
async def test_alpha_beta_prunes_correctly():
    """Alpha-beta should evaluate fewer nodes than full minimax."""
    solver_pruned = AdaptiveDecisionTreeSolver(SolverConfig(alpha_beta_pruning=True))
    solver_full = AdaptiveDecisionTreeSolver(SolverConfig(alpha_beta_pruning=False))
    # Build a tree with opponent nodes where pruning applies
    tree = _build_adversarial_tree(depth=4, branching=3)
    r_pruned = await solver_pruned.minimax(tree)
    r_full = await solver_full.minimax(tree)
    assert r_pruned.expected_value == r_full.expected_value  # Same result
    assert r_pruned.nodes_evaluated < r_full.nodes_evaluated  # Fewer nodes
```

---

## Implementation Order (14 steps)

1. Create `src/asi_build/decision/tree/__init__.py`
2. Define `NodeType` and `SolverStrategy` enums
3. Define `DecisionNode`, `MCTSConfig`, `SolverResult`, `SolverConfig` frozen dataclasses
4. Define `DecisionTreeSolver` Protocol with `@runtime_checkable`
5. Implement `AdaptiveDecisionTreeSolver.__init__` + tree utilities
6. Implement `_backward_induction()` — recursive post-order
7. Implement `minimax()` — with alpha-beta pruning branch
8. Implement `_expectimax()` — chance node expected value
9. Implement `mcts_search()` — select/expand/simulate/backprop loop
10. Implement `_select_strategy()` — adaptive dispatch
11. Implement `value_of_information()` — Monte Carlo VoI estimation
12. Implement `solve()` — strategy dispatch + timing + SolverResult
13. Implement `NullDecisionTreeSolver` + `make_decision_tree_solver()` factory
14. Register Prometheus metrics + write 12 tests + verify mypy strict

---

## Phase 23 Sub-Phase Tracker

| Sub-Phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 23.1 | UncertaintyQuantifier | #529 | ✅ Spec |
| 23.2 | RiskAssessor | #530 | ✅ Spec |
| 23.3 | UtilityComputer | #531 | ✅ Spec |
| 23.4 | DecisionTreeSolver | #532 | ✅ Spec |
| 23.5 | DecisionOrchestrator | #533 | ⬜ Pending |
