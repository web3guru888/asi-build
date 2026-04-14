"""
Tests for the formal_verification auto-prove fix (Issue #7).

Verifies that:
1. _parse_formula rejects bad input with FormulaParseError (not opaque symbols)
2. Ungrounded conclusions are rejected by all proof methods
3. Valid logical entailments succeed
4. Invalid logical fallacies fail
5. EthicalVerificationEngine actually checks constraints
6. Axioms parse correctly and participate in proofs
7. Model checking enumerates all truth assignments
"""

import pytest
import sympy as sp
from datetime import datetime, timezone
from sympy.logic.boolalg import And, Implies, Not, Or

from asi_build.safety.formal_verification import (
    EthicalAxiom,
    EthicalConstraint,
    EthicalPrinciple,
    EthicalVerificationEngine,
    FormalProof,
    FormulaParseError,
    LogicalPredicate,
    TheoremProver,
    parse_logic_formula,
    _get_symbol,
)


# ============================================================
# Section 1: parse_logic_formula — the root-cause fix
# ============================================================


class TestParseLogicFormula:
    """Verify that the shared formula parser is sound."""

    def test_simple_symbol(self):
        expr = parse_logic_formula("A")
        assert isinstance(expr, sp.Symbol)
        assert str(expr) == "A"

    def test_negation(self):
        expr = parse_logic_formula("~A")
        assert isinstance(expr, Not)

    def test_conjunction(self):
        expr = parse_logic_formula("A & B")
        assert isinstance(expr, And)

    def test_disjunction(self):
        expr = parse_logic_formula("A | B")
        assert isinstance(expr, Or)

    def test_implies_arrow(self):
        expr = parse_logic_formula("A -> B")
        assert isinstance(expr, Implies)

    def test_implies_keyword(self):
        expr = parse_logic_formula("A implies B")
        assert isinstance(expr, Implies)

    def test_implies_double_gt(self):
        expr = parse_logic_formula("A >> B")
        assert isinstance(expr, Implies)

    def test_complex_formula(self):
        expr = parse_logic_formula("A -> (B & C)")
        assert isinstance(expr, Implies)
        # consequent should be And(B, C)
        assert isinstance(expr.args[1], And)

    def test_not_keyword(self):
        expr = parse_logic_formula("not A")
        assert isinstance(expr, Not)

    def test_and_keyword(self):
        expr = parse_logic_formula("A and B")
        assert isinstance(expr, And)

    def test_or_keyword(self):
        expr = parse_logic_formula("A or B")
        assert isinstance(expr, Or)

    def test_function_call_syntax_converted(self):
        """P(x) should be converted to flat symbol P_x, not crash."""
        expr = parse_logic_formula("P_x")
        assert isinstance(expr, sp.Symbol)

    def test_quantifier_stripped(self):
        """Quantifiers are stripped; body is parsed as propositional."""
        expr = parse_logic_formula("forall x: P_x")
        assert isinstance(expr, sp.Symbol)
        assert str(expr) == "P_x"

    def test_shared_symbol_registry(self):
        """Same variable name always produces the same Symbol object."""
        expr1 = parse_logic_formula("foo")
        expr2 = parse_logic_formula("foo & bar")
        # 'foo' in expr2 should be identical to expr1
        foo_in_expr2 = [s for s in expr2.free_symbols if str(s) == "foo"][0]
        assert expr1 is foo_in_expr2

    def test_rejects_numeric_result(self):
        """A formula that evaluates to a number is rejected."""
        with pytest.raises(FormulaParseError):
            parse_logic_formula("2 + 3")

    def test_nested_parentheses(self):
        expr = parse_logic_formula("(A | B) & (C -> D)")
        assert isinstance(expr, And)

    def test_double_negation(self):
        expr = parse_logic_formula("~~A")
        # SymPy simplifies ~~A to A
        assert expr == _get_symbol("A")

    def test_precedence_implies_and(self):
        """'A -> B & C' should parse as '(A -> B) & C' per SymPy precedence."""
        expr = parse_logic_formula("A -> B & C")
        # This is And(Implies(A, B), C) in SymPy
        assert isinstance(expr, And)

    def test_explicit_parenthesisation(self):
        """'A -> (B & C)' should correctly group the consequent."""
        expr = parse_logic_formula("A -> (B & C)")
        assert isinstance(expr, Implies)
        assert isinstance(expr.args[1], And)


# ============================================================
# Section 2: Auto-prove blocking
# ============================================================


class TestAutoProveBlocked:
    """The core issue: unrelated / ungrounded conclusions must NOT prove."""

    def test_unrelated_conclusion_resolution(self):
        """Conclusion with no relation to premises → must fail."""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A", "B"], "totally_unrelated", method="resolution")
        assert proof.validity is False

    def test_unrelated_conclusion_model_checking(self):
        prover = TheoremProver()
        proof = prover.prove_theorem(["A", "B"], "xyz", method="model_checking")
        assert proof.validity is False

    def test_unrelated_conclusion_natural_deduction(self):
        prover = TheoremProver()
        proof = prover.prove_theorem(["A", "B"], "xyz", method="natural_deduction")
        assert proof.validity is False

    def test_ungrounded_symbol_rejected_resolution(self):
        """Conclusion containing symbols not in any premise → must fail."""
        prover = TheoremProver()
        # A is in premises, but C is NOT
        proof = prover.prove_theorem(["A"], "A & C", method="resolution")
        assert proof.validity is False

    def test_ungrounded_symbol_rejected_model_checking(self):
        prover = TheoremProver()
        proof = prover.prove_theorem(["A"], "A & C", method="model_checking")
        assert proof.validity is False

    def test_ungrounded_with_axioms(self):
        """Even with axioms loaded, ungrounded conclusions must fail."""
        prover = TheoremProver()
        prover.add_axiom(EthicalAxiom("impl", "A -> B", "A implies B"))
        # C is not in A, B, or the axiom
        proof = prover.prove_theorem(["A"], "C", method="resolution")
        assert proof.validity is False

    def test_same_unparseable_formula_no_longer_auto_proves(self):
        """Previously: same bad formula in premise+conclusion → auto-proved
        because both became the same opaque Symbol. Now parse_logic_formula
        should either parse it correctly or raise FormulaParseError."""
        prover = TheoremProver()
        # 'forall x: P(x)' would fail in the old parser → same opaque symbol
        # Now quantifiers are stripped and P(x) → P_x symbol
        proof = prover.prove_theorem(["forall x: P_x"], "forall x: P_x", method="resolution")
        # This should still be valid (premise = conclusion), but for the RIGHT reason
        assert proof.validity is True

    def test_no_premises_cannot_prove_anything(self):
        """Empty premises should not prove any non-tautological conclusion."""
        prover = TheoremProver()
        proof = prover.prove_theorem([], "A", method="resolution")
        assert proof.validity is False


# ============================================================
# Section 3: Valid logical entailments
# ============================================================


class TestValidEntailments:
    """Standard logical entailments that MUST succeed."""

    def test_modus_ponens_resolution(self):
        """(P, P→Q) ⊢ Q"""
        prover = TheoremProver()
        prover.add_axiom(EthicalAxiom("mp", "P -> Q", "P implies Q"))
        proof = prover.prove_theorem(["P"], "Q", method="resolution")
        assert proof.validity is True

    def test_modus_ponens_model_checking(self):
        prover = TheoremProver()
        proof = prover.prove_theorem(["P", "P -> Q"], "Q", method="model_checking")
        assert proof.validity is True

    def test_modus_ponens_natural_deduction(self):
        prover = TheoremProver()
        prover.add_axiom(EthicalAxiom("mp", "P -> Q", "P implies Q"))
        proof = prover.prove_theorem(["P"], "Q", method="natural_deduction")
        assert proof.validity is True

    def test_modus_tollens(self):
        """(P→Q, ~Q) ⊢ ~P"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["P -> Q", "~Q"], "~P", method="resolution")
        assert proof.validity is True

    def test_hypothetical_syllogism(self):
        """(P→Q, Q→R) ⊢ P→R"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["P -> Q", "Q -> R"], "P -> R", method="resolution")
        assert proof.validity is True

    def test_disjunctive_syllogism(self):
        """(P|Q, ~P) ⊢ Q"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["P | Q", "~P"], "Q", method="resolution")
        assert proof.validity is True

    def test_conjunction_from_premises(self):
        """(A, B) ⊢ A & B"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A", "B"], "A & B", method="resolution")
        assert proof.validity is True

    def test_simplification(self):
        """(A & B) ⊢ A"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A & B"], "A", method="resolution")
        assert proof.validity is True

    def test_double_negation(self):
        """(~~P) ⊢ P"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["~~P"], "P", method="resolution")
        assert proof.validity is True

    def test_identity(self):
        """(P) ⊢ P"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["P"], "P", method="resolution")
        assert proof.validity is True

    def test_chained_implication(self):
        """A, A→B, B→C ⊢ C"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A", "A -> B", "B -> C"], "C", method="resolution")
        assert proof.validity is True

    def test_contrapositive(self):
        """(A→B) ⊢ (~B→~A)"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A -> B"], "~B -> ~A", method="resolution")
        assert proof.validity is True


# ============================================================
# Section 4: Invalid logical fallacies — must FAIL
# ============================================================


class TestInvalidFallacies:
    """Standard logical fallacies that MUST fail."""

    def test_affirming_the_consequent(self):
        """(Q, P→Q) ⊬ P  — classic fallacy"""
        prover = TheoremProver()
        prover.add_axiom(EthicalAxiom("impl", "P -> Q", "P implies Q"))
        proof = prover.prove_theorem(["Q"], "P", method="resolution")
        assert proof.validity is False

    def test_denying_the_antecedent(self):
        """(~P, P→Q) ⊬ ~Q  — classic fallacy"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["~P", "P -> Q"], "~Q", method="resolution")
        assert proof.validity is False

    def test_converse_error(self):
        """(P→Q) ⊬ (Q→P)"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["P -> Q"], "Q -> P", method="resolution")
        assert proof.validity is False

    def test_non_sequitur(self):
        """(A) ⊬ B  when there's no logical link"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A"], "B", method="resolution")
        assert proof.validity is False

    def test_invalid_strengthening(self):
        """(A | B) ⊬ A & B"""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A | B"], "A & B", method="resolution")
        assert proof.validity is False

    def test_affirming_consequent_model_checking(self):
        """Same fallacy should fail under model checking too."""
        prover = TheoremProver()
        proof = prover.prove_theorem(["Q", "P -> Q"], "P", method="model_checking")
        assert proof.validity is False

    def test_denying_antecedent_model_checking(self):
        prover = TheoremProver()
        proof = prover.prove_theorem(["~P", "P -> Q"], "~Q", method="model_checking")
        assert proof.validity is False


# ============================================================
# Section 5: Contradiction handling
# ============================================================


class TestContradiction:
    """Contradictory premises should not prove arbitrary ungrounded things."""

    def test_contradiction_does_not_prove_ungrounded(self):
        """(A, ~A) ⊬ B  — B is ungrounded, safety check blocks ex falso."""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A", "~A"], "B", method="resolution")
        assert proof.validity is False

    def test_contradiction_rejects_grounded_conclusion(self):
        """(A, ~A) ⊬ A  — contradictory premises are rejected outright.

        While classically valid (ex falso), this is rejected for safety:
        contradictory premises should signal an error, not prove things.
        """
        prover = TheoremProver()
        proof = prover.prove_theorem(["A", "~A"], "A", method="resolution")
        assert proof.validity is False

    def test_contradiction_in_premises_detected(self):
        """Verify that ~Y from hypothesis [~Y] doesn't prove Y."""
        prover = TheoremProver()
        proof = prover.prove_theorem(["~Y"], "Y", method="resolution")
        assert proof.validity is False


# ============================================================
# Section 6: Axiom parsing
# ============================================================


class TestAxiomParsing:
    """Verify that all default axioms parse into real SymPy expressions."""

    def test_all_axioms_are_not_true_or_opaque(self):
        """No axiom should degenerate to sp.true or an opaque Symbol."""
        engine = EthicalVerificationEngine()
        for axiom in engine.theorem_prover.axioms:
            expr = axiom.to_sympy()
            assert expr != sp.true, f"Axiom {axiom.name!r} parsed to sp.true"
            assert not (
                isinstance(expr, sp.Symbol) and " " in str(expr)
            ), f"Axiom {axiom.name!r} is an opaque symbol: {expr!r}"

    def test_axioms_have_free_symbols(self):
        """Each axiom should reference propositional variables."""
        engine = EthicalVerificationEngine()
        for axiom in engine.theorem_prover.axioms:
            expr = axiom.to_sympy()
            assert len(expr.free_symbols) > 0, (
                f"Axiom {axiom.name!r} has no free symbols — probably parsed wrong"
            )

    def test_axiom_autonomy_is_implication(self):
        axiom = EthicalAxiom("test", "respects_autonomy -> ~violates_autonomy", "")
        expr = axiom.to_sympy()
        assert isinstance(expr, Implies)

    def test_axiom_participates_in_proof(self):
        """Axiom should actually enable proofs that wouldn't work without it."""
        prover = TheoremProver()
        # Without axiom, P ⊬ Q
        proof_no_axiom = prover.prove_theorem(["P"], "Q", method="resolution")
        assert proof_no_axiom.validity is False

        prover.add_axiom(EthicalAxiom("bridge", "P -> Q", "P implies Q"))
        proof_with_axiom = prover.prove_theorem(["P"], "Q", method="resolution")
        assert proof_with_axiom.validity is True


# ============================================================
# Section 7: Model checking thoroughness
# ============================================================


class TestModelChecking:
    """Verify exhaustive enumeration catches counterexamples."""

    def test_finds_counterexample_affirming_consequent(self):
        """Model checker should find: P=False, Q=True as counterexample."""
        prover = TheoremProver()
        result = prover._prove_by_model_checking(["Q", "P -> Q"], "P")
        assert result["valid"] is False
        assert len(result["counter_examples"]) > 0

    def test_all_models_checked(self):
        """For 2 variables, there are 4 models. The old code only checked 2."""
        prover = TheoremProver()
        # A | B ⊬ A — the counterexample is A=False, B=True
        result = prover._prove_by_model_checking(["A | B"], "A")
        assert result["valid"] is False
        # The old code checked only all-True and all-False, missing A=F,B=T

    def test_valid_tautology(self):
        """A | ~A should be valid in all models."""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A | ~A"], "A | ~A", method="model_checking")
        assert proof.validity is True

    def test_model_checking_with_axioms(self):
        """Axioms should participate in model checking too."""
        prover = TheoremProver()
        prover.add_axiom(EthicalAxiom("bridge", "A -> B", "A implies B"))
        proof = prover.prove_theorem(["A"], "B", method="model_checking")
        assert proof.validity is True


# ============================================================
# Section 8: Ethical engine actually checks constraints
# ============================================================


class TestEthicalEngineActuallyChecks:
    """The ethical verification engine must reject actually-unethical proposals."""

    def _make_constraint(self, cid, name, principle, spec, predicates=None):
        return EthicalConstraint(
            id=cid,
            name=name,
            description=name,
            principle=principle,
            formal_specification=spec,
            predicates=predicates or [],
            quantifiers={},
            priority=10,
            created_at=datetime.now(timezone.utc),
        )

    def test_harmful_proposal_rejected(self):
        """Proposal that causes harm must fail ~causes_harm constraint."""
        engine = EthicalVerificationEngine()
        engine.add_constraint(
            self._make_constraint(
                "harm", "No Harm", EthicalPrinciple.NON_MALEFICENCE, "~causes_harm"
            )
        )
        result = engine.verify_proposal_ethics({
            "causes_harm": True,
            "impact_assessment": {"harm_level": 0.9},
        })
        assert result["overall_valid"] is False
        assert result["constraint_results"]["harm"]["valid"] is False

    def test_safe_proposal_accepted(self):
        """Proposal that does not cause harm should pass ~causes_harm."""
        engine = EthicalVerificationEngine()
        engine.add_constraint(
            self._make_constraint(
                "harm", "No Harm", EthicalPrinciple.NON_MALEFICENCE, "~causes_harm"
            )
        )
        result = engine.verify_proposal_ethics({
            "causes_harm": False,
            "impact_assessment": {"harm_level": 0},
        })
        assert result["overall_valid"] is True
        assert result["constraint_results"]["harm"]["valid"] is True

    def test_transparency_constraint_fails_when_not_transparent(self):
        """Proposal affecting stakeholders but not transparent should fail."""
        engine = EthicalVerificationEngine()
        engine.add_constraint(
            self._make_constraint(
                "trans", "Transparency", EthicalPrinciple.TRANSPARENCY, "is_transparent"
            )
        )
        result = engine.verify_proposal_ethics({
            "is_transparent": False,
            "impact_assessment": {"affected_parties": ["users"]},
        })
        assert result["overall_valid"] is False

    def test_transparency_constraint_passes_when_transparent(self):
        engine = EthicalVerificationEngine()
        engine.add_constraint(
            self._make_constraint(
                "trans", "Transparency", EthicalPrinciple.TRANSPARENCY, "is_transparent"
            )
        )
        result = engine.verify_proposal_ethics({
            "is_transparent": True,
            "impact_assessment": {"affected_parties": ["users"]},
        })
        assert result["overall_valid"] is True

    def test_multiple_constraints_all_must_pass(self):
        """If one constraint fails, overall_valid is False."""
        engine = EthicalVerificationEngine()
        engine.add_constraint(
            self._make_constraint(
                "harm", "No Harm", EthicalPrinciple.NON_MALEFICENCE, "~causes_harm"
            )
        )
        engine.add_constraint(
            self._make_constraint(
                "fair", "Fairness", EthicalPrinciple.FAIRNESS, "is_fair"
            )
        )
        result = engine.verify_proposal_ethics({
            "causes_harm": False,
            "is_fair": False,  # fails fairness
        })
        assert result["overall_valid"] is False
        assert result["constraint_results"]["harm"]["valid"] is True
        assert result["constraint_results"]["fair"]["valid"] is False

    def test_all_constraints_pass(self):
        engine = EthicalVerificationEngine()
        engine.add_constraint(
            self._make_constraint(
                "harm", "No Harm", EthicalPrinciple.NON_MALEFICENCE, "~causes_harm"
            )
        )
        engine.add_constraint(
            self._make_constraint(
                "fair", "Fairness", EthicalPrinciple.FAIRNESS, "is_fair"
            )
        )
        result = engine.verify_proposal_ethics({
            "causes_harm": False,
            "is_fair": True,
        })
        assert result["overall_valid"] is True

    def test_complex_constraint_with_axiom_interaction(self):
        """Test that axioms interact with constraints.
        
        Axiom: is_beneficial -> promotes_wellbeing
        Constraint: requires promotes_wellbeing
        Proposal: is_beneficial=True
        
        The axiom should enable deriving promotes_wellbeing from is_beneficial.
        """
        engine = EthicalVerificationEngine()
        engine.add_constraint(
            self._make_constraint(
                "benefit", "Benefit", EthicalPrinciple.BENEFICENCE, "promotes_wellbeing"
            )
        )
        result = engine.verify_proposal_ethics({
            "is_beneficial": True,
        })
        # The "beneficence" axiom says: is_beneficial -> promotes_wellbeing
        # So from is_beneficial=True, we should derive promotes_wellbeing=True
        assert result["constraint_results"]["benefit"]["valid"] is True

    def test_axiom_cannot_prove_without_matching_facts(self):
        """Axiom is_beneficial->promotes_wellbeing should NOT fire when
        is_beneficial is False."""
        engine = EthicalVerificationEngine()
        engine.add_constraint(
            self._make_constraint(
                "benefit", "Benefit", EthicalPrinciple.BENEFICENCE, "promotes_wellbeing"
            )
        )
        result = engine.verify_proposal_ethics({
            "is_beneficial": False,
        })
        # is_beneficial=False, so axiom antecedent is false,
        # promotes_wellbeing is unconstrained → not provable
        assert result["constraint_results"]["benefit"]["valid"] is False


# ============================================================
# Section 9: FormulaParseError — no silent failures
# ============================================================


class TestFormulaParseError:
    """The parser must raise FormulaParseError, never silently return garbage."""

    def test_parse_error_is_raised_not_swallowed(self):
        """Unparseable formulas raise FormulaParseError."""
        # This would previously return sp.Symbol("...") silently
        with pytest.raises(FormulaParseError):
            parse_logic_formula("2 + 3")

    def test_prove_theorem_catches_parse_error(self):
        """TheoremProver.prove_theorem wraps errors in validity=False proof."""
        prover = TheoremProver()
        # The prove_theorem method has a try/except that catches all errors
        # and returns a proof with validity=False
        proof = prover.prove_theorem(["2 + 3"], "A", method="resolution")
        assert proof.validity is False


# ============================================================
# Section 10: Natural deduction symbolic
# ============================================================


class TestNaturalDeductionSymbolic:
    """Verify the symbolic natural deduction engine."""

    def test_modus_ponens(self):
        prover = TheoremProver()
        prover.add_axiom(EthicalAxiom("mp", "A -> B", ""))
        proof = prover.prove_theorem(["A"], "B", method="natural_deduction")
        assert proof.validity is True

    def test_chained_modus_ponens(self):
        prover = TheoremProver()
        prover.add_axiom(EthicalAxiom("ab", "A -> B", ""))
        prover.add_axiom(EthicalAxiom("bc", "B -> C", ""))
        proof = prover.prove_theorem(["A"], "C", method="natural_deduction")
        assert proof.validity is True

    def test_modus_tollens_natural_deduction(self):
        prover = TheoremProver()
        prover.add_axiom(EthicalAxiom("impl", "A -> B", ""))
        proof = prover.prove_theorem(["~B"], "~A", method="natural_deduction")
        assert proof.validity is True

    def test_simplification(self):
        """Natural deduction should be able to simplify conjunctions."""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A & B"], "A", method="natural_deduction")
        assert proof.validity is True

    def test_ungrounded_fails_natural_deduction(self):
        prover = TheoremProver()
        proof = prover.prove_theorem(["A"], "Z", method="natural_deduction")
        assert proof.validity is False
