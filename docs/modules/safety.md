# Safety

> **Maturity**: `beta` · **Adapter**: `SafetyBlackboardAdapter`

Comprehensive safety architecture implementing constitutional AI principles, ethical verification, formal theorem proving, and governance frameworks. The ConstitutionalAI module enforces behavioral constraints and value alignment. The formal verification subsystem uses SymPy-based theorem proving with resolution, natural deduction, and model checking — recently fixed to prevent auto-proving (Issue #7). The governance package provides DAO mechanisms, quadratic voting, Merkle audit trails, liquid democracy, and entity rights management.

The SafetyBlackboardAdapter is fail-closed by design — if safety verification fails, operations are blocked.

## Key Classes

| Class | Description |
|-------|-------------|
| `ConstitutionalAI` | Constitutional constraint enforcement for value-aligned behavior |
| `ValueAlignmentEngine` | Value alignment scoring and assessment |
| `BehavioralConstraints` | Behavioral boundary enforcement |
| `TheoremProver` | SymPy-based formal theorem proving: resolution, natural deduction, model checking |
| `EthicalVerificationEngine` | Ethical constraint verification pipeline |
| `EthicalAxiom` | Axiom parsing and management for ethical reasoning |
| `GovernanceFramework` | DAO, voting, and audit framework |
| `ComplianceChecker` | Compliance verification against governance policies |
| `governance` | Sub-package: DAO, quadratic voting, Merkle audit, liquid democracy, entity rights |

## Example Usage

```python
from asi_build.safety import ConstitutionalAI, TheoremProver
ai = ConstitutionalAI()
ai.add_constraint("Do not cause harm", formal="~harm")
is_safe = ai.verify_action(proposed_action="deploy_model", context={"risk": "low"})
prover = TheoremProver()
proved = prover.prove(premises=["A -> B", "B -> C"], conclusion="A -> C")
```

## Blackboard Integration

SafetyBlackboardAdapter is fail-closed — publishes verification results with CRITICAL priority on failures; auto-verifies proposals from reasoning and economics modules; blocks operations that fail safety checks.
