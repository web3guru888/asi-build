# AGI Economics Module

> **Module path**: `src/asi_build/agi_economics/`  
> **Size**: 22 files · 7,741 LOC  
> **Status**: ✅ Functional — game theory solver, bonding curves, token economics, reputation scoring, marketplace simulation all operational

The `agi_economics` module provides a complete multi-agent economic system for ASI:BUILD. It models how AI agents negotiate, trade, stake tokens, build reputation, and align economically with human values — the financial and incentive substrate of a decentralized AGI ecosystem.

---

## Architecture

```
agi_economics/
├── core/
│   ├── base_engine.py       # Abstract BaseEconomicEngine + EconomicEvent
│   ├── config.py            # Platform configuration
│   ├── exceptions.py        # Economic error hierarchy
│   └── types.py             # Agent, Resource, Token, Market dataclasses
├── engines/
│   ├── bonding_curves.py    # Automated market maker curves
│   └── token_economics.py   # AGIX/AGI token supply, staking, inflation
├── algorithms/
│   └── resource_allocator.py  # Multi-strategy compute/bandwidth allocation
├── analysis/
│   └── game_theory.py       # Nash equilibria, mechanism design, evolutionary games
├── simulation/
│   └── marketplace_dynamics.py  # Order book, auctions, price discovery
├── systems/
│   ├── reputation_system.py # Multi-dimensional agent reputation scoring
│   └── value_alignment.py   # Economic incentive alignment with human values
└── contracts/
    └── agi_service_contract.py  # Smart contract templates for AI services
```

---

## 1. BaseEconomicEngine

All economic components extend `BaseEconomicEngine` — an abstract class providing event logging, metric tracking, and state management:

```python
from agi_economics.core.base_engine import BaseEconomicEngine, EconomicEvent

class MyEngine(BaseEconomicEngine):
    def start(self) -> bool: ...
    def stop(self) -> bool: ...
    def process_event(self, event: EconomicEvent) -> dict: ...
```

Key methods:
- `log_event(event_type, agent_id, data)` — append to event log
- `update_metrics(metrics)` / `get_metrics()` — track engine state
- `get_events(event_type, agent_id, limit)` — query event history

---

## 2. Token Economics Engine

`engines/token_economics.py` models AGIX and AGI service tokens with realistic macroeconomic mechanics:

```python
from agi_economics.engines.token_economics import TokenEconomicsEngine, StakingPool

engine = TokenEconomicsEngine(config={
    "inflation_rate": 0.02,   # 2% annual inflation
    "max_supply": 1_000_000_000,
    "burn_rate": 0.001,        # 0.1% per transaction
})
```

### Token Supply Model

```
TokenSupplyInfo:
  current_supply     # Minted tokens in circulation
  max_supply         # Hard cap (e.g. 1B AGIX)
  burned_supply      # Deflationary burns (from fees/penalties)
  inflation_rate     # Annual expansion rate
  circulating_supply = current_supply - burned_supply
```

### Staking Pools

```python
@dataclass
class StakingPool:
    token_type: TokenType
    total_staked: Decimal
    total_rewards: Decimal
    reward_rate: Decimal = Decimal("0.05")  # 5% APY
    stakers: Dict[str, Decimal]
```

Agents stake tokens to:
- Signal long-term commitment (skin-in-the-game)
- Earn staking rewards proportional to stake share
- Access premium service tiers

---

## 3. Bonding Curves

`engines/bonding_curves.py` implements automated market making for token price discovery. Six curve types are supported:

| Curve Type | Formula | Use Case |
|-----------|---------|---------|
| `LINEAR` | `P = a × S + b` | Simple price-supply relationship |
| `EXPONENTIAL` | `P = P₀ × e^(k×S)` | Fast-growing ecosystems |
| `LOGARITHMIC` | `P = a × ln(S) + b` | Diminishing marginal price |
| `SIGMOID` | `P = L / (1 + e^(-k×(S-S₀)))` | Bounded growth with inflection |
| `BANCOR` | `P = R / (S × CRR)` | Continuous liquidity (Bancor v1) |
| `AUGMENTED_BONDING_CURVE` | Composite + reserve | DAO treasury management |

```python
from agi_economics.engines.bonding_curves import BondingCurve, BondingCurveConfig, CurveType
from decimal import Decimal

config = BondingCurveConfig(
    curve_type=CurveType.BANCOR,
    reserve_ratio=Decimal("0.5"),      # 50% CRR (Constant Reserve Ratio)
    slope=Decimal("0.001"),
    base_price=Decimal("0.01"),        # Starting price per AGIX
    max_supply=Decimal("1000000000"),
    initial_supply=Decimal("100000000"),
    reserve_balance=Decimal("500000"),
)
curve = BondingCurve(config)
```

The Bancor formula is particularly important — it allows agents to always buy/sell at the bonding curve price, providing guaranteed liquidity without an external market maker. At reserve ratio 0.5, price ≈ `reserve_balance / (circulating_supply × 0.5)`.

---

## 4. Resource Allocation Engine

`algorithms/resource_allocator.py` handles compute, memory, bandwidth, and storage allocation across competing agent requests:

### Allocation Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `FIRST_FIT` | First provider with sufficient capacity | Low-latency simple tasks |
| `BEST_FIT` | Minimize wasted capacity | Resource-efficient clusters |
| `WORST_FIT` | Leave largest gaps for future requests | Heterogeneous workloads |
| `PROPORTIONAL_SHARE` | Allocate proportional to agent priority weight | Fair multi-tenant systems |
| `AUCTION_BASED` | Highest bidder wins, with fairness constraints | Market-priced compute |
| `UTILITY_MAXIMIZATION` | Maximize aggregate system utility | Cooperative optimization |
| `FAIR_SHARE` | Equalise resource access over time | Public goods allocation |
| `PRIORITY_BASED` | Strict priority tiers (safety tasks > reasoning > background) | Real-time ASI:BUILD cycles |

```python
@dataclass
class ResourceAllocation:
    request_id: str
    requester_id: str
    provider_id: str
    resource_type: ResourceType
    allocated_amount: Decimal
    price_per_unit: Decimal
    total_cost: Decimal
    expiry_time: float

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expiry_time
```

### Resource Types (from `core/types.py`)

- `COMPUTE` — GPU/CPU hours
- `MEMORY` — RAM in GB
- `BANDWIDTH` — Network MB/s
- `STORAGE` — Persistent storage GB
- `SPECIALIZED` — Custom hardware (neuromorphic chips, quantum backends)

---

## 5. Game Theory Analyzer

`analysis/game_theory.py` is one of the module's most sophisticated components — a full game-theoretic reasoning engine for multi-agent strategic interactions.

### Supported Game Types

| GameType | Description |
|----------|-------------|
| `NORMAL_FORM` | Standard matrix games (Prisoner's Dilemma, Coordination) |
| `EXTENSIVE_FORM` | Sequential games with information sets |
| `AUCTION` | Vickrey, English, Dutch, sealed-bid auctions |
| `RESOURCE_ALLOCATION` | Strategic resource bidding |
| `REPUTATION` | Repeated games with reputation effects |
| `COOPERATIVE` | Coalition formation, Shapley values |
| `EVOLUTIONARY` | Evolutionarily stable strategies (ESS) |

### Equilibrium Concepts

```python
class EquilibriumType(Enum):
    NASH = "nash"                  # Standard Nash equilibrium
    DOMINANT_STRATEGY = "dominant_strategy"
    CORRELATED = "correlated"      # Correlated equilibrium (weaker assumption)
    EVOLUTIONARY_STABLE = "evolutionary_stable"  # ESS
    COALITION = "coalition"        # Core, Shapley value
```

### Nash Equilibrium Computation

```python
from agi_economics.analysis.game_theory import GameTheoryAnalyzer, Game, Player, GameType
import numpy as np

# Classic Prisoner's Dilemma
players = [
    Player(player_id="A", strategies=["cooperate", "defect"],
           payoff_matrix=np.array([[3, 0], [5, 1]]),
           rationality_level=0.9),
    Player(player_id="B", strategies=["cooperate", "defect"],
           payoff_matrix=np.array([[3, 5], [0, 1]]),
           rationality_level=0.9),
]
game = Game(
    game_id="pd_001",
    game_type=GameType.NORMAL_FORM,
    players=players,
    payoff_matrices={"A": players[0].payoff_matrix, "B": players[1].payoff_matrix},
)
analyzer = GameTheoryAnalyzer()
equilibria = analyzer.find_nash_equilibria(game)
# → (defect, defect) with social_welfare=2, efficiency_ratio=0.33
# → Pareto-optimal (cooperate, cooperate) has social_welfare=6
```

The analyzer uses `scipy.optimize.linprog` for mixed-strategy Nash computation and `scipy.linalg.null_space` for correlated equilibrium verification.

### Key Metrics

Each `Equilibrium` result includes:
- `strategy_profile` — the mixed/pure strategy at equilibrium
- `social_welfare` — sum of payoffs across all players
- `efficiency_ratio` — actual welfare / optimal welfare (Price of Anarchy proxy)
- `stability_measure` — how robust is this equilibrium to perturbations
- `is_stable` — boolean stability flag

### Mechanism Design

Beyond finding equilibria, the game theory engine supports mechanism design — asking: **what rules should we set to induce desirable equilibria?**

This is directly relevant to ASI:BUILD's multi-module orchestration: how should the system reward modules that cooperate vs. compete, and what incentive structures prevent defection?

---

## 6. Marketplace Dynamics Simulation

`simulation/marketplace_dynamics.py` implements a full order-book exchange for AI services:

### Auction Types

```python
class AuctionType(Enum):
    ENGLISH   = "english"     # Ascending price — highest bidder wins
    DUTCH     = "dutch"       # Descending price — first taker wins
    SEALED_BID = "sealed_bid" # One-shot blind bids
    VICKREY   = "vickrey"     # Second-price: bid true value, pay runner-up
    DOUBLE    = "double"      # Continuous double auction (CDA)
```

The **continuous double auction** (CDA) is the most realistic — it matches buy and sell orders continuously as they arrive, setting a market-clearing price at each trade. This is how real financial exchanges work and how ASI:BUILD's compute market would operate.

### Order Book Mechanics

```python
@dataclass
class MarketOrder:
    order_id: str
    agent_id: str
    order_type: OrderType    # BUY or SELL
    service_type: str        # e.g. "consciousness_inference"
    quantity: Decimal
    price: Decimal
    max_price: Optional[Decimal]  # Budget cap for buy orders
    min_price: Optional[Decimal]  # Floor for sell orders
    status: OrderStatus           # PENDING → FILLED or CANCELLED
    filled_quantity: Decimal

@dataclass
class ServiceMarket:
    service_type: str
    buy_orders: List[MarketOrder]
    sell_orders: List[MarketOrder]
    recent_trades: List[MarketTrade]
    current_price: Decimal
    volume_24h: Decimal
    price_change_24h: Decimal
```

Each `ServiceMarket` is a separate order book — so there's a market for "consciousness inference", another for "quantum optimization", another for "knowledge graph queries", etc.

---

## 7. Reputation System

`systems/reputation_system.py` provides **multi-dimensional agent reputation scoring** — going well beyond a simple star rating:

### Reputation Dimensions

```python
class ReputationDimension(Enum):
    TECHNICAL_QUALITY   = "technical_quality"    # Output accuracy, benchmark scores
    RELIABILITY         = "reliability"           # Uptime, delivery success rate
    COOPERATION         = "cooperation"           # Contribution to shared goals
    HONESTY             = "honesty"               # Truthful reporting, no manipulation
    INNOVATION          = "innovation"            # Novel contributions
    RESPONSIVENESS      = "responsiveness"        # Latency, SLA compliance
    RESOURCE_EFFICIENCY = "resource_efficiency"   # Compute per unit output
    VALUE_ALIGNMENT     = "value_alignment"       # Human values score
```

### Validation Methods

```python
class ValidationMethod(Enum):
    PEER_REVIEW           = "peer_review"
    AUTOMATED_METRICS     = "automated_metrics"
    HUMAN_EVALUATION      = "human_evaluation"
    CONSENSUS_ALGORITHM   = "consensus_algorithm"
    BLOCKCHAIN_PROOF      = "blockchain_proof"
    MULTI_STAKEHOLDER     = "multi_stakeholder"
```

### ReputationScore Structure

```python
@dataclass
class ReputationScore:
    agent_id: str
    dimensions: Dict[ReputationDimension, float]  # 0.0–1.0 per dimension
    overall_score: float                           # Weighted aggregate
    confidence: float                              # How well-sampled is this score?
```

The **Bayesian updating** approach means new evidence shifts scores proportional to evidence count — agents can't flip their reputation overnight with one interaction.

---

## 8. Value Alignment System

`systems/value_alignment.py` closes the loop between economics and ethics. Rather than treating alignment purely as a safety constraint (as the safety module does), it uses **economic incentives** to make aligned behavior profitable:

### Value Categories

```python
class ValueCategory(Enum):
    BENEFICENCE       = "beneficence"       # Does this agent help humans?
    NON_MALEFICENCE   = "non_maleficence"   # Does it avoid harm?
    AUTONOMY          = "autonomy"           # Does it respect human choices?
    JUSTICE           = "justice"           # Is it fair?
    TRANSPARENCY      = "transparency"      # Is it explainable?
    PRIVACY           = "privacy"           # Does it protect user data?
    SUSTAINABILITY    = "sustainability"    # Environmental responsibility
    COLLABORATION     = "collaboration"     # Works with humans, not against
    INNOVATION        = "innovation"        # Advances beneficial technology
    EDUCATION         = "education"         # Shares knowledge responsibly
```

### Alignment Mechanisms

```python
class AlignmentMechanism(Enum):
    REWARD_SHAPING             = "reward_shaping"       # Bonus tokens for aligned behavior
    PENALTY_SYSTEM             = "penalty_system"       # Token slashing for violations
    REPUTATION_BASED           = "reputation_based"     # Reputation gating on services
    MULTI_STAKEHOLDER_VALIDATION = "multi_stakeholder"  # Human panel sign-off
    CONSTITUTIONAL_AI          = "constitutional"       # Constitutional rule evaluation
    HUMAN_FEEDBACK             = "human_feedback"       # RLHF-style signal
    COOPERATIVE_INVERSE_REINFORCEMENT = "cooperative_irl"  # Infer human preferences
```

This is tightly coupled to the `safety` module — `ConstitutionalAI` appears in both, but the economics module approaches it from the incentive side rather than the constraint side.

---

## 9. Smart Contract Templates

`contracts/agi_service_contract.py` provides template structures for on-chain service agreements:

```python
@dataclass
class ServiceContractTemplate:
    contract_address: str
    service_id: str
    service_type: str
    client_address: str
    provider_address: str
    payment_amount: Decimal
    token_address: str        # AGIX ERC-20 contract
    escrow_percentage: Decimal  # Default 10% held in escrow
    delivery_deadline: int
    quality_requirements: Dict[str, Any]
    state: ContractState      # CREATED → FUNDED → IN_PROGRESS → COMPLETED/DISPUTED
```

The escrow mechanism is key: payment is locked until service delivery is verified, with a dispute resolution window. This is the financial layer that makes trustless AI service markets possible.

---

## Integration Points

### Connection to Cognitive Blackboard

The reputation system is a natural Blackboard citizen — agents could write `ReputationScore` entries that other modules query when deciding who to trust:

```python
# Conceptual integration (not yet implemented — see Issue #62)
class EconomicsBlackboardAdapter:
    def write_reputation(self, agent_id: str, score: ReputationScore):
        self.blackboard.write(
            key=f"reputation:{agent_id}",
            value=score.__dict__,
            source="agi_economics",
            ttl=300.0  # Re-evaluate every 5 minutes
        )

    def read_reputation(self, agent_id: str) -> Optional[ReputationScore]:
        entry = self.blackboard.read(f"reputation:{agent_id}")
        return ReputationScore(**entry.value) if entry else None
```

### Connection to Rings Network

The Rings Network peer discovery layer (see [Rings Network](Rings-Network)) provides agent identity via DIDs. Reputation scores mapped to DIDs would persist across network sessions — enabling a decentralized reputation ledger without a central server.

### Connection to Safety Module

The `value_alignment.py` `AlignmentMechanism.CONSTITUTIONAL_AI` integrates with `safety/formal_verification.py`:
- Safety module gates execution (hard constraint)
- Economics module adjusts reward signals (soft incentive)
- Together: agents are both prevented from violating rules AND economically motivated to align

---

## Open Research Questions

1. **Price of Anarchy in ASI:BUILD**: In a multi-agent system where modules compete for compute resources, what's the worst-case ratio between Nash equilibrium welfare and optimal welfare? Can mechanism design reduce it?

2. **Sybil resistance**: The reputation system assumes each agent has one identity. In a permissionless network, Sybil attacks (creating many fake identities to game reputation) are a real threat. What cryptographic or economic Sybil barriers should be built in?

3. **Token velocity problem**: High token velocity (tokens change hands quickly) reduces price stability. How should the bonding curve parameters be set to maintain stable prices while enabling liquid markets?

4. **Cooperative IRL in practice**: `COOPERATIVE_INVERSE_REINFORCEMENT` assumes we can observe human preferences from behavior. For ASI:BUILD, what human behaviors should we observe, and how do we handle preference diversity across users?

5. **Reputation decay**: Should old reputation events decay over time? An agent that was unreliable 6 months ago but has since improved shouldn't be permanently penalized. What decay function preserves incentives for improvement?

6. **Cross-module economic coupling**: When the consciousness module runs IIT Φ computation and the quantum module assists via VQE, how should economic credit be split? Shapley values from the cooperative game theory engine are a natural answer — but computing them is #P-hard for large coalitions.

---

## Quick Start

```python
from asi_build.agi_economics.engines.bonding_curves import BondingCurve, BondingCurveConfig, CurveType
from asi_build.agi_economics.analysis.game_theory import GameTheoryAnalyzer
from asi_build.agi_economics.systems.reputation_system import ReputationSystem
from decimal import Decimal

# 1. Create an automated market maker
curve = BondingCurve(BondingCurveConfig(
    curve_type=CurveType.BANCOR,
    reserve_ratio=Decimal("0.5"),
    slope=Decimal("0.001"),
    base_price=Decimal("0.01"),
    max_supply=Decimal("1000000000"),
    initial_supply=Decimal("100000000"),
    reserve_balance=Decimal("500000"),
))

# 2. Analyze strategic interactions
analyzer = GameTheoryAnalyzer()
# ... (set up players and game matrix)
equilibria = analyzer.find_nash_equilibria(game)

# 3. Score agent reputation
rep_system = ReputationSystem()
score = rep_system.get_reputation("agent-001")
print(f"Overall: {score.overall_score:.2f}, Confidence: {score.confidence:.2f}")
```

---

## Related Wiki Pages

- [Architecture](Architecture) — Where economics fits in the layered stack
- [Rings Network](Rings-Network) — Decentralized identity layer for economic agents
- [Safety Module](Safety-Module) — Hard constraints complementing economic incentives
- [Cognitive Blackboard](Cognitive-Blackboard) — Shared state for reputation/price signals
- [Federated Learning](Federated-Learning) — Privacy-preserving model training economics
- [Roadmap](Roadmap) — Phase 3 plans for live economic simulation
