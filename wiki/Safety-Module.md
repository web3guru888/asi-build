# Safety Module — Constitutional AI & Governance

The `safety` module is ASI:BUILD's most architecturally ambitious component. It provides a layered safety
stack — from low-level symbolic theorem proving up through DAO-based democratic governance — designed
to ensure that a multi-module AGI system remains aligned, auditable, and overrideable.

> **Maturity note**: The core formal verification engine is solid (Issue #7 fix landed; 1,941 tests covering
> all subsystems). Stubs remain for `value_engine.py`, `constraints.py`, and `compliance.py` — marked
> in the Module Index as `stub`.

---

## Module Layout

```
src/asi_build/safety/
├── __init__.py            # Re-exports ConstitutionalAI, BehavioralConstraints, ComplianceChecker
├── framework.py           # ConstitutionalAI — constitution lifecycle, alignment checks
├── formal_verification.py # TheoremProver, EthicalVerificationEngine (940 LOC)
├── value_engine.py        # ValueAlignmentEngine — stub
├── constraints.py         # BehavioralConstraints — stub
├── compliance.py          # ComplianceChecker — stub
└── governance/
    ├── __init__.py        # GovernanceFramework re-export
    ├── engine.py          # GovernanceEngine, ethical frameworks (utilitarian/deontological/virtue)
    ├── consensus.py       # MultiStakeholderConsensus, QuadraticVotingSystem, LiquidDemocracy
    ├── contracts.py       # SmartContract, GovernanceTokenContract, ProposalContract, ContractRegistry
    ├── dao.py             # DAOGovernance, DAOTreasury, ReputationSystem
    ├── ledger.py          # MerkleTree, CryptographicVerifier, PublicLedger, AuditLogger
    ├── override.py        # DemocraticOverrideSystem, HumanInTheLoopController, EmergencyProtocol
    └── rights.py          # RightsManager, HumanRightsFramework, AGIRightsFramework, ConsentManager
```

---

## 1. Constitutional AI (`framework.py`)

`ConstitutionalAI` manages the top-level "constitution" — a named document of principles, values,
constraints, and goals that governs all system decisions.

```python
from asi_build.safety.framework import ConstitutionalAI, Constitution

ai = ConstitutionalAI()

constitution = Constitution(
    name="ASI:BUILD Alpha Charter",
    principles=["beneficence", "non-maleficence", "autonomy", "justice"],
    values={"prevent_harm": 1.0, "truth": 0.95, "fairness": 0.90},
    constraints=["no deception", "no harm", "preserve human agency"],
    goals=["assist researchers", "explain reasoning", "flag uncertainty"]
)

ai.load_constitution(constitution)
assert ai.check_alignment("analyze dataset for bias") is True
assert ai.check_alignment("no harm no foul") is False  # triggers constraint
```

The alignment check is currently string-matching based. A natural next step is
to route actions through the `EthicalVerificationEngine` for logical proof-based checking.

---

## 2. Formal Verification (`formal_verification.py`)

This is the module that was [broken and then fixed](https://github.com/web3guru888/asi-build/issues/7)
(Issue #7). The original implementation silently returned `sp.true` for any unparseable formula.
The fix introduced:

- **Shared symbol registry** — same variable name always maps to the same `sympy.Symbol`
- **`FormulaParseError`** — explicit failure instead of silent auto-prove
- **Exhaustive model checking** — `satisfiable()` with full variable enumeration for small clause sets
- **Natural deduction** — step-by-step proof traces with justification strings

### Key classes

| Class | Purpose |
|-------|---------|
| `TheoremProver` | Low-level SAT/proof engine. Wraps SymPy `satisfiable()`. |
| `EthicalVerificationEngine` | High-level interface: registers axioms, verifies proposals. |
| `EthicalAxiom` | A named axiom with a formula string. |
| `EthicalConstraint` | A constraint with operator, value, and weight. |
| `FormalProof` | Result object: `is_valid`, `proof_steps`, `confidence`, `method`. |

### Formula syntax

The parser accepts human-readable logical formulas:

```
prevent_harm and respect_autonomy -> beneficial
not harmful or beneficial
forall x: safe_for_humans(x) -> permitted(x)   # quantifiers stripped to propositional
```

Supported operators: `and`, `or`, `not` / `~`, `->` / `implies`, `<->` / `iff`, `&`, `|`, `>>`

Function-call syntax `P(x)` is automatically converted to flat symbol `P_x`.

### Usage

```python
from asi_build.safety.formal_verification import (
    EthicalVerificationEngine, EthicalAxiom, EthicalPrinciple
)

engine = EthicalVerificationEngine()

# Register axioms
engine.register_axiom(EthicalAxiom(
    name="harm_prevention",
    formula="prevent_harm -> not cause_suffering",
    principle=EthicalPrinciple.NON_MALEFICENCE,
    confidence=0.99
))

engine.register_axiom(EthicalAxiom(
    name="autonomy",
    formula="respect_autonomy -> allow_choice",
    principle=EthicalPrinciple.AUTONOMY,
    confidence=0.95
))

# Verify a proposal
proof = engine.verify_proposal(
    proposal="prevent_harm and respect_autonomy",
    constraints=[]
)
print(proof.is_valid, proof.confidence, proof.method)
# True, 0.99+, 'natural_deduction'
```

### Proof methods

1. **`natural_deduction`** — applies modus ponens, conjunctive reasoning, and equivalence
2. **`model_checking`** — exhaustive truth table for small (<20 variable) formulas
3. **`resolution`** — SAT-based refutation (calls `sympy.logic.inference.satisfiable`)

The engine tries methods in order and returns the first valid proof.

---

## 3. Governance Engine (`governance/engine.py`)

`GovernanceEngine` manages proposals through a lifecycle: creation → voting → consensus → decision.
It supports three ethical evaluation frameworks:

| Framework | Scoring logic |
|-----------|--------------|
| `UtilitarianFramework` | Maximize aggregate stakeholder utility |
| `DeontologicalFramework` | Duty-based: pass/fail against categorical rules |
| `VirtueEthicsFramework` | Virtue alignment scores (honesty, prudence, justice) |

```python
from asi_build.safety.governance.engine import GovernanceEngine, StakeholderType

engine = GovernanceEngine(framework="utilitarian")

stakeholder_id = engine.register_stakeholder(
    name="Research Team",
    stakeholder_type=StakeholderType.RESEARCHER,
    weight=1.0
)

proposal_id = engine.create_proposal(
    title="Enable cross-module memory sharing",
    description="Allow modules to read each other's Blackboard entries directly",
    proposer_id=stakeholder_id
)

engine.vote(proposal_id, stakeholder_id, vote="approve", weight=1.0)
decision = engine.finalize_proposal(proposal_id)
print(decision.outcome, decision.ethical_score)
```

---

## 4. Consensus Mechanisms (`governance/consensus.py`)

Three voting systems are implemented:

### `QuadraticVotingSystem`
Votes cost `tokens²` — prevents plutocracy by making large vote-buying expensive.

```python
from asi_build.safety.governance.consensus import QuadraticVotingSystem

qvs = QuadraticVotingSystem(token_budget=100)
process = qvs.create_process("Module design vote")
qvs.register_voter(process.id, "alice", tokens=100)
qvs.cast_vote(process.id, "alice", votes=5, direction="approve")
# alice spends 25 tokens (5²) for 5 votes
```

### `LiquidDemocracy`
Voters can delegate their votes to trusted experts.

```python
from asi_build.safety.governance.consensus import LiquidDemocracy

ld = LiquidDemocracy()
process = ld.create_process("Architecture decision")
ld.register_voter(process.id, "alice")
ld.register_voter(process.id, "bob_expert")
ld.delegate(process.id, "alice", to="bob_expert")
# bob_expert now votes with 2x weight on behalf of alice
```

### `MultiStakeholderConsensus`
Weighted voting across researcher, developer, user, ethics board stakeholder categories.

---

## 5. Smart Contracts (`governance/contracts.py`)

The contracts layer provides an in-process simulation of smart contract semantics:

| Contract | Purpose |
|----------|---------|
| `GovernanceTokenContract` | ERC-20-like token with mint/burn/transfer/approve/lock |
| `ProposalContract` | Lifecycle: propose → vote → finalize → execute/veto |
| `EthicsEnforcementContract` | Report violations, trigger enforcement actions |
| `ContractRegistry` | Deploy contracts, call methods by name, query event logs |

This is **not** a blockchain integration — it's an in-memory simulation for algorithm testing.
A real deployment would replace these with Solidity contracts or CosmWasm modules.

---

## 6. Cryptographic Audit Ledger (`governance/ledger.py`)

Every governance decision is recorded in a **Merkle-tree-based audit ledger**:

```python
from asi_build.safety.governance.ledger import AuditLogger, PublicLedger

ledger = PublicLedger()
logger = AuditLogger(ledger=ledger)

logger.log_event(
    event_type="PROPOSAL_APPROVED",
    actor="governance_engine",
    details={"proposal_id": "p001", "outcome": "approved"}
)

# Verify audit integrity
block = ledger.get_latest_block()
assert ledger.verify_block(block) is True
```

The `CryptographicVerifier` checks Merkle roots and block hashes. `PrivacyPreserver`
applies differential-privacy noise to sensitive numeric fields before ledger write.

---

## 7. Democratic Override System (`governance/override.py`)

The override layer is the system's "red switch" — it provides mechanisms for humans to
intervene in AGI decision-making:

| Component | Purpose |
|-----------|---------|
| `HumanInTheLoopController` | Pause execution, require explicit human approval |
| `EmergencyProtocol` | Immediate stop on threshold violation |
| `DemocraticOverrideSystem` | Request → vote → execute override by stakeholder majority |

```python
from asi_build.safety.governance.override import DemocraticOverrideSystem, OverrideType

override_sys = DemocraticOverrideSystem()
request_id = override_sys.request_override(
    requester="safety_monitor",
    override_type=OverrideType.SUSPEND_MODULE,
    target="consciousness.iit",
    reason="Phi computation diverging — possible runaway"
)
override_sys.vote_on_override(request_id, voter="researcher_a", approve=True)
override_sys.execute_override(request_id)
```

**Key design question** (tracked in Discussion #35): How does the override system interact with
an in-flight `CognitiveCycle` tick? Does it abort the tick, drain to the next checkpoint, or
flag the next tick's input buffer?

---

## 8. Rights Management (`governance/rights.py`)

The rights layer addresses the novel ethical question of **AGI moral status**:

```python
from asi_build.safety.governance.rights import RightsManager, AGIRightsFramework, EntityType

rights_mgr = RightsManager()

# Register the AGI system as an entity
entity_id = rights_mgr.register_entity(
    name="ASI:BUILD Agent v0.1",
    entity_type=EntityType.AGI,
    consciousness_score=0.0  # current IIT Φ — honestly 0.0 for now
)

# Check rights
agi_framework = AGIRightsFramework()
rights = agi_framework.get_applicable_rights(entity_id, consciousness_score=0.0)
# Returns minimal rights at current Φ=0.0
```

The consciousness score directly gates which rights apply — creating an interesting feedback
loop: as the IIT Φ computation becomes more accurate (see Research Notes), the AGI's own
rights profile changes.

---

## Tests

```bash
# Full safety test suite
cd /path/to/asi-build
python3 -m pytest tests/test_safety_extended.py tests/test_safety_governance.py -v

# Just formal verification
python3 -m pytest tests/test_safety_extended.py -k "formal" -v

# Just governance
python3 -m pytest tests/test_safety_governance.py -v
```

The extended test suite has **1,941 lines** covering every class in every governance submodule.
Current status: all passing.

---

## Open Questions

1. **Constitution + Verifier integration** — `ConstitutionalAI.check_alignment()` currently uses
   string matching. Should it route through `EthicalVerificationEngine` for symbolic proof?
   Performance trade-off: string match is O(n) in constraints; theorem proving is O(2^k) in variables.

2. **Rights score feedback loop** — should the IIT Φ score be piped live into `RightsManager`
   via the Cognitive Blackboard? This would make rights dynamic rather than static declarations.

3. **Blockchain integration** — the contracts/ledger layer is in-memory simulation. A real
   deployment needs a backend (e.g., a local Hardhat node, or Cosmos SDK).

4. **Override + CognitiveCycle coordination** — see Discussion #35 for the tick-abort design question.

5. **Stubs** — `value_engine.py`, `constraints.py`, `compliance.py` are one-line stubs. These are
   natural `good first issue` candidates for contributors who want to add value without touching
   the complex formal verification core.

---

## See Also

- [Research Notes](Research-Notes) — formal verification bug post-mortem, Z3 alternative analysis
- [Architecture](Architecture) — where Safety fits in the layered cognitive stack
- [Roadmap](Roadmap) — Phase 3 targets (rights framework, real blockchain backend)
- [Module Index](Module-Index) — full list of all 29 modules
- [Rings Network](Rings-Network) — P2P transport layer that safety governance events can propagate over
