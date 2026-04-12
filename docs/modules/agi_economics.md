# AGI Economics

> **Maturity**: `experimental` · **Adapter**: `AGIEconomicsBlackboardAdapter`

Token economics and market simulation for AGI resource allocation. Implements bonding curves for dynamic pricing, reputation systems for agent trustworthiness scoring, game-theoretic strategy analysis, and marketplace simulation for resource trading. Explores value alignment through economic incentive design.

## Key Classes

| Class | Description |
|-------|-------------|
| `TokenEconomics` | Token minting, burning, transfer |
| `BondingCurves` | Dynamic pricing curves |
| `ReputationSystem` | Agent reputation scoring |
| `GameTheory` | Strategy analysis, Nash equilibrium |
| `Marketplace` | Resource trading simulation |

## Example Usage

```python
from asi_build.agi_economics import TokenEconomics, BondingCurves
tokens = TokenEconomics(initial_supply=1000)
curve = BondingCurves(base_price=1.0, curve_type="sigmoid")
price = curve.get_price(supply=tokens.total_supply)
```

## Blackboard Integration

AGIEconomicsBlackboardAdapter publishes token prices, reputation scores, and market state; consumes safety adapter proposals for automatic economic verification.
