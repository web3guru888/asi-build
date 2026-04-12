# AGI Communication

> **Maturity**: `alpha` · **Adapter**: `AGICommunicationBlackboardAdapter`

Multi-agent communication protocols for AGI systems. Provides trust-based authentication, goal negotiation between agents, collaborative problem solving, semantic messaging with intent parsing, and knowledge graph merging for shared understanding. Uses a dynamic auto-import pattern that loads all callables from the package.

## Key Classes

| Class | Description |
|-------|-------------|
| `Protocol` | Communication protocol management |
| `Negotiation` | Goal negotiation between agents |
| `Collaboration` | Collaborative problem-solving sessions |
| `SemanticMessaging` | Intent-aware message parsing |
| `KGMerger` | Knowledge graph merging across agents |

## Example Usage

```python
from asi_build.agi_communication import Protocol, Negotiation
protocol = Protocol()
negotiation = Negotiation(protocol=protocol)
result = negotiation.propose_goal("shared_research", participants=["agent_a", "agent_b"])
```

## Blackboard Integration

AGICommunicationBlackboardAdapter publishes negotiation results and collaboration state to the blackboard; consumes reasoning outputs and KG updates for cross-agent synchronization.
