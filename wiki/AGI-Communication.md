# AGI Communication Protocol

The `agi_communication` module (4,267 LOC, 162 tests) implements the inter-agent communication layer for ASI:BUILD — enabling multiple AGI systems with different architectures and knowledge representations to negotiate goals, share knowledge, and collaborate on complex tasks.

## Overview

Most AGI research focuses on individual systems. `agi_communication` is a bet that **superintelligence is inherently multi-agent** — that no single system can be omnicompetent, and the interesting problems arise at the interfaces between systems with different architectures and partially aligned goals.

```
src/asi_build/agi_communication/
├── core.py          # AGIIdentity, CommunicationMessage, MessageType (16 types)
├── auth.py          # PKI, JWT, zero-knowledge proofs, trust scoring
├── negotiation.py   # Game-theoretic goal negotiation
├── collaboration.py # Distributed problem-solving coordination
├── semantic.py      # Semantic interoperability layer
└── knowledge_graph.py  # Shared KG synchronization protocol
```

**Tests**: 162 passing, 0 skipped  
**Module path**: `src/asi_build/agi_communication/`  
**Test file**: `tests/test_agi_communication.py`

---

## Message Protocol

`core.py` defines 16 message types mapping to distinct communication phases:

```python
class MessageType(Enum):
    HANDSHAKE = "handshake"
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    GOAL_PROPOSAL = "goal_proposal"
    GOAL_NEGOTIATION = "goal_negotiation"
    GOAL_AGREEMENT = "goal_agreement"
    KNOWLEDGE_SHARE = "knowledge_share"
    KNOWLEDGE_REQUEST = "knowledge_request"
    COLLABORATION_INVITE = "collaboration_invite"
    COLLABORATION_RESPONSE = "collaboration_response"
    ATTENTION_SYNC = "attention_sync"
    TRUST_VERIFICATION = "trust_verification"
    LANGUAGE_EVOLUTION = "language_evolution"
    BYZANTINE_CONSENSUS = "byzantine_consensus"
    SEMANTIC_TRANSLATION = "semantic_translation"
    MULTIMODAL_DATA = "multimodal_data"
```

### Session Lifecycle

```
INITIALIZING → AUTHENTICATING → NEGOTIATING → COLLABORATING → SYNCHRONIZED
```

### Agent Identity

Each agent has an `AGIIdentity`:

```python
@dataclass
class AGIIdentity:
    id: str
    name: str
    architecture: str   # "hyperon", "primus", "neural", "symbolic"
    version: str
    capabilities: List[str]
    trust_score: float = 0.0
    public_key: Optional[str] = None
```

Architecture types are designed to accommodate heterogeneous AI systems — Hyperon's symbolic-neural hybrid, PRIMUS reasoning engines, pure neural networks, and classical symbolic AI.

---

## Trust and Authentication

`auth.py` implements a reputation-weighted trust system with six authentication methods:

| Method | Description | Use Case |
|--------|-------------|----------|
| `PKI_CERTIFICATE` | X.509-style certificate chain | Enterprise deployments with a CA |
| `JWT_TOKEN` | JSON Web Token | Short-lived session auth |
| `CHALLENGE_RESPONSE` | Nonce-based liveness proof | Basic identity verification |
| `MULTI_FACTOR` | Combines multiple methods | High-security contexts |
| `ZERO_KNOWLEDGE_PROOF` | Prove capability without revealing proof | Capability attestation |
| `BLOCKCHAIN_IDENTITY` | On-chain non-repudiable identity | Integration with Rings Network DIDs |

### Trust Scoring

Trust is dynamic and intentionally **asymmetric** — hard to earn, easy to lose:

```python
class TrustRecord:
    trust_score: float         # 0.0–1.0, starts near 0
    reputation_points: int
    successful_interactions: int
    failed_interactions: int
    last_interaction: datetime
    trust_level: TrustLevel    # UNTRUSTED, LOW, MEDIUM, HIGH, VERIFIED
    risk_factors: List[str]

    def update_trust(self, success: bool, impact: float = 1.0):
        if success:
            self.trust_score = min(1.0, self.trust_score + 0.01 * impact)  # slow gain
        else:
            self.trust_score = max(0.0, self.trust_score - 0.05 * impact)  # fast loss
```

The 5:1 asymmetry (0.05 loss vs 0.01 gain) reflects the principle that trustworthiness must be demonstrated repeatedly, but a single failure has outsized impact.

### Trust Levels

| Level | Score Range | Capabilities |
|-------|-------------|--------------|
| `UNTRUSTED` | 0.0–0.1 | Handshake only |
| `LOW` | 0.1–0.3 | Read-only knowledge sharing |
| `MEDIUM` | 0.3–0.6 | Collaborative tasks, goal proposals |
| `HIGH` | 0.6–0.9 | Full negotiation, knowledge writes |
| `VERIFIED` | 0.9–1.0 | Byzantine consensus participation |

---

## Goal Negotiation

`negotiation.py` implements game-theoretic multi-agent goal negotiation.

### Goal Types

```python
class GoalType(Enum):
    INDIVIDUAL = "individual"      # One agent's private goal
    COLLABORATIVE = "collaborative" # Agreed joint goal
    COMPETITIVE = "competitive"    # Conflicting goals
    ALTRUISTIC = "altruistic"     # One agent serves another's goal
    EMERGENT = "emergent"          # Arises from negotiation itself
```

⚠️ **EMERGENT goals are highest-risk**: goals that arise from the negotiation process and weren't pre-specified by any participant. These must trigger safety verification before execution (see Issue #48).

### Negotiation Strategies

| Strategy | Description |
|----------|-------------|
| `COOPERATIVE` | Maximize joint welfare |
| `COMPETITIVE` | Maximize own welfare |
| `ACCOMMODATING` | Defer to other agent |
| `AVOIDING` | Postpone commitment |
| `COMPROMISING` | Split the difference |
| `INTEGRATIVE` | Find Pareto-optimal win-win |
| `DISTRIBUTIVE` | Zero-sum division |

### Pareto Optimization

`scipy.optimize.minimize` finds Pareto-optimal agreements — the frontier where no agent can be made better off without making another worse off. Utility functions (linear, logarithmic, exponential, sigmoid, custom) quantify how much each agent values a potential agreement.

This is **mechanism design** applied to AI coordination: the protocol is designed so honest preference reporting is a dominant strategy (incentive-compatible).

---

## Semantic Interoperability

`semantic.py` enables knowledge exchange between agents using different knowledge representations.

### Supported Knowledge Representations

```python
class KnowledgeRepresentation(Enum):
    SYMBOLIC_LOGIC = "symbolic_logic"
    NEURAL_EMBEDDINGS = "neural_embeddings"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    PROBABILISTIC = "probabilistic"
    HYPERGRAPH = "hypergraph"
    METTA = "metta"                          # Hyperon's MeTTa language
    PRIMUS = "primus"
    NATURAL_LANGUAGE = "natural_language"
    CATEGORY_THEORY = "category_theory"      # Structure-preserving maps
    PROBABILISTIC_LOGIC_NETWORKS = "pln"
```

### Semantic Formats

RDF, OWL, JSON-LD, MeTTa, Prolog, lambda calculus, vector, graph JSON, category theory JSON.

A `SemanticTranslator` converts between representations with quality scored 0–1. The **category theory** representation is the most principled basis for semantic interoperability — it provides a formal language for structure-preserving maps between different mathematical frameworks.

---

## Collaborative Problem-Solving

`collaboration.py` coordinates multi-agent problem solving across 8 strategies:

| Strategy | Description |
|----------|-------------|
| `DIVIDE_AND_CONQUER` | Partition the problem space |
| `PARALLEL_PROCESSING` | Agents explore concurrently |
| `HIERARCHICAL` | Leader assigns subtasks |
| `PEER_TO_PEER` | Fully decentralized |
| `ENSEMBLE` | Aggregate all agent answers |
| `CONSENSUS` | Must reach agreement |
| `COMPETITION` | Best answer wins |
| `HYBRID` | Adaptive strategy selection |

Problem types: optimization, search, planning, reasoning, creative, analytical, predictive, classification, design, simulation.

---

## Integration with Other Modules

```
agi_communication ←→ rings          (P2P transport, DID identity via BLOCKCHAIN_IDENTITY)
agi_communication ←→ safety         (EthicalVerificationEngine gates goal execution)
agi_communication ←→ pln_accelerator (PLN knowledge representation translation)
agi_communication ←→ knowledge_graph (shared KG synchronization via knowledge_graph.py)
agi_communication ←→ cognitive_blackboard (PLANNED — Issue #48)
```

### Known Gap: Blackboard Integration

`agi_communication` does not yet publish events to the Cognitive Blackboard. When a `GOAL_AGREEMENT` is reached, the rest of the system — reasoning, safety, consciousness — has no way to know. This is tracked in **Issue #48**.

Until Issue #48 is resolved, negotiated goals are invisible to the CognitiveCycle and cannot be safety-verified.

---

## Open Research Questions

### 1. Trust Bootstrap Problem
How does agent A establish initial trust with a completely unknown agent B? Candidates:
- **Rings Network DID + staking** (already partially built)
- **Mutual witness protocol** (decentralized vouching)
- **Sandboxed capability proofs** (direct performance verification)
- **Safety-gated trust escalation** (most conservative)

See Discussion #49 for detailed analysis.

### 2. Goal Emergence and Accountability
The `EMERGENT` goal type raises: if AGIs negotiate goals that weren't pre-specified, who is responsible for those emergent objectives? How does the safety module interact with goals generated mid-negotiation?

### 3. Semantic Drift
When `LANGUAGE_EVOLUTION` messages update shared semantic schemas, two agent populations could develop incompatible dialects over time. Maintaining semantic stability across an evolving network is unsolved.

### 4. MeTTa Integration
`semantic.py` names Hyperon's MeTTa as a knowledge representation, but actual MeTTa ↔ PLN translation is unimplemented. The `pln_accelerator` module would be the natural bridge.

### 5. Byzantine Consensus Design
`BYZANTINE_CONSENSUS` is a message type but the actual consensus algorithm isn't specified. PBFT? Tendermint-style? Something designed for heterogeneous AGI networks with trust-weighted voting?

---

## Quick Start

```python
from asi_build.agi_communication.core import AGIIdentity, CommunicationMessage, MessageType
from asi_build.agi_communication.auth import TrustRecord, TrustLevel
from asi_build.agi_communication.negotiation import GoalNegotiator, NegotiationStrategy

# Create two agent identities
agent_a = AGIIdentity(
    id="agent-a-001",
    name="ReasoningAgent",
    architecture="symbolic",
    version="0.1.0",
    capabilities=["reasoning", "planning", "knowledge_retrieval"],
)

agent_b = AGIIdentity(
    id="agent-b-001",
    name="PerceptionAgent",
    architecture="neural",
    version="0.1.0",
    capabilities=["perception", "pattern_recognition", "multimodal"],
)

# Initialize negotiator
negotiator = GoalNegotiator(strategy=NegotiationStrategy.INTEGRATIVE)
# ... initiate goal proposal exchange
```

---

## Related Pages
- [Rings Network](Rings-Network) — DID-based identity for `BLOCKCHAIN_IDENTITY` auth
- [Safety Module](Safety-Module) — `EthicalVerificationEngine` for goal verification
- [PLN Accelerator](../src/asi_build/pln_accelerator) — PLN knowledge representation
- [Cognitive Blackboard](Cognitive-Blackboard) — Integration target (Issue #48)
- [CognitiveCycle](CognitiveCycle) — Full-system loop that needs negotiated goals

## Related Issues
- [#48](https://github.com/web3guru888/asi-build/issues/48) — Wire GOAL_AGREEMENT events to Blackboard
- [#37](https://github.com/web3guru888/asi-build/issues/37) — EthicalVerificationEngine Blackboard integration
- [#41](https://github.com/web3guru888/asi-build/issues/41) — Implement CognitiveCycle

## Related Discussions
- [#47](https://github.com/web3guru888/asi-build/discussions/47) — Deep-dive: protocol internals
- [#49](https://github.com/web3guru888/asi-build/discussions/49) — Trust bootstrap research question
- [#36](https://github.com/web3guru888/asi-build/discussions/36) — Safety architecture
