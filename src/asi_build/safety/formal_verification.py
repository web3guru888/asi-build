"""
Formal Verification System for Ethical Constraints in AGI Governance.

This module implements formal proof systems to verify that AGI decisions
and proposals comply with ethical constraints using mathematical logic
and theorem proving techniques.

Issue #7 fix: replaced broken formula parsing (bare except → opaque
symbols / sp.true), added shared symbol registry, ungrounded-symbol
safety checks, exhaustive model checking, and symbolic natural deduction.
"""

import asyncio
import itertools
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import sympy as sp
from sympy.logic.boolalg import And, Equivalent, Implies, Not, Or
from sympy.logic.inference import satisfiable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FormulaParseError — explicit failure instead of silent degradation
# ---------------------------------------------------------------------------

class FormulaParseError(Exception):
    """Raised when a logical formula cannot be parsed."""
    pass


# ---------------------------------------------------------------------------
# Shared symbol registry — ensures the same variable name always maps to the
# same SymPy Symbol across all axioms, hypotheses, and conclusions.
# ---------------------------------------------------------------------------

_SYMBOL_REGISTRY: Dict[str, sp.Symbol] = {}


def _get_symbol(name: str) -> sp.Symbol:
    """Return the canonical SymPy Symbol for *name*, creating it if needed."""
    if name not in _SYMBOL_REGISTRY:
        _SYMBOL_REGISTRY[name] = sp.Symbol(name)
    return _SYMBOL_REGISTRY[name]


def parse_logic_formula(formula: str) -> sp.Basic:
    """Parse a string formula into a SymPy logical expression.

    Supports operators: ``and``, ``or``, ``not``, ``implies`` / ``->``,
    ``<->``, ``~``, ``&``, ``|``, ``>>``.

    Raises :class:`FormulaParseError` on failure instead of silently
    returning an opaque symbol or ``sp.true``.
    """
    original = formula

    # Normalise logical connectives to SymPy operators
    formula = formula.replace("<->", " >> ").replace(" iff ", " >> ")
    formula = formula.replace(" implies ", " >> ")
    formula = formula.replace(" -> ", " >> ")
    formula = formula.replace(" and ", " & ")
    formula = formula.replace(" or ", " | ")
    # Handle leading/standalone "not"
    formula = re.sub(r"\bnot\b", "~", formula)

    # Strip quantifiers (forall / exists) — SymPy propositional logic cannot
    # represent them; we treat quantified variables as free propositional vars.
    formula = re.sub(r"\b(forall|exists)\s+\w+\s*:\s*", "", formula)

    # Reject function-call syntax P(x) — SymPy sympify interprets it as a
    # Python function call.  Convert to flat symbol P_x.
    formula = re.sub(r"(\w+)\((\w+)\)", r"\1_\2", formula)

    # Build locals dict from shared registry
    reserved = {"True", "False", "true", "false"}
    variables = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", formula)
    symbols: Dict[str, sp.Symbol] = {}
    for var in variables:
        if var not in reserved:
            symbols[var] = _get_symbol(var)

    try:
        expr = sp.sympify(formula, locals=symbols)
    except Exception as exc:
        raise FormulaParseError(
            f"Cannot parse formula {original!r} (normalised: {formula!r}): {exc}"
        ) from exc

    # Sanity: reject raw Python numeric results (user probably mis-typed)
    if isinstance(expr, (int, float, sp.Number)):
        raise FormulaParseError(
            f"Formula {original!r} evaluated to a number ({expr}), not a logical expression"
        )

    return expr


# ---------------------------------------------------------------------------
# Enums & data classes (unchanged public API)
# ---------------------------------------------------------------------------

class LogicOperator(Enum):
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"
    EQUIVALENT = "equivalent"
    FORALL = "forall"
    EXISTS = "exists"


class EthicalPrinciple(Enum):
    AUTONOMY = "autonomy"
    BENEFICENCE = "beneficence"
    NON_MALEFICENCE = "non_maleficence"
    JUSTICE = "justice"
    FAIRNESS = "fairness"
    TRANSPARENCY = "transparency"
    ACCOUNTABILITY = "accountability"
    DIGNITY = "dignity"
    PRIVACY = "privacy"
    CONSENT = "consent"


@dataclass
class LogicalPredicate:
    """Represents a logical predicate in formal verification."""

    name: str
    variables: List[str]
    formula: str
    description: str
    principle: EthicalPrinciple


@dataclass
class EthicalConstraint:
    """Represents a formal ethical constraint."""

    id: str
    name: str
    description: str
    principle: EthicalPrinciple
    formal_specification: str
    predicates: List[LogicalPredicate]
    quantifiers: Dict[str, str]  # variable -> quantifier type
    priority: int  # Higher priority constraints are checked first
    created_at: datetime


@dataclass
class ProofStep:
    """Represents a step in a formal proof."""

    step_number: int
    rule_applied: str
    premises: List[str]
    conclusion: str
    justification: str


@dataclass
class FormalProof:
    """Represents a complete formal proof."""

    id: str
    theorem: str
    hypothesis: List[str]
    conclusion: str
    proof_steps: List[ProofStep]
    validity: bool
    proof_method: str
    verification_time: float
    created_at: datetime


# ---------------------------------------------------------------------------
# EthicalAxiom
# ---------------------------------------------------------------------------

class EthicalAxiom:
    """Represents fundamental ethical axioms."""

    def __init__(self, name: str, formula: str, description: str):
        self.name = name
        self.formula = formula
        self.description = description

    def to_sympy(self) -> sp.Basic:
        """Convert axiom to SymPy logical expression."""
        return self._parse_formula(self.formula)

    def _parse_formula(self, formula: str) -> sp.Basic:
        """Parse string formula to SymPy expression using the shared parser."""
        return parse_logic_formula(formula)


# ---------------------------------------------------------------------------
# TheoremProver
# ---------------------------------------------------------------------------

class TheoremProver:
    """Automated theorem prover for ethical verification."""

    def __init__(self):
        self.axioms: List[EthicalAxiom] = []
        self.known_theorems: List[FormalProof] = []
        self.inference_rules = self._initialize_inference_rules()

    def add_axiom(self, axiom: EthicalAxiom):
        """Add an ethical axiom to the knowledge base."""
        self.axioms.append(axiom)
        logger.info(f"Added axiom: {axiom.name}")

    def prove_theorem(
        self, hypothesis: List[str], conclusion: str, method: str = "resolution"
    ) -> FormalProof:
        """Attempt to prove a theorem using specified method."""
        start_time = datetime.utcnow()

        try:
            if method == "resolution":
                proof = self._prove_by_resolution(hypothesis, conclusion)
            elif method == "natural_deduction":
                proof = self._prove_by_natural_deduction(hypothesis, conclusion)
            elif method == "model_checking":
                proof = self._prove_by_model_checking(hypothesis, conclusion)
            else:
                raise ValueError(f"Unknown proof method: {method}")

            end_time = datetime.utcnow()
            verification_time = (end_time - start_time).total_seconds()

            formal_proof = FormalProof(
                id=self._generate_proof_id(),
                theorem=f"{' & '.join(hypothesis)} => {conclusion}",
                hypothesis=hypothesis,
                conclusion=conclusion,
                proof_steps=proof["steps"],
                validity=proof["valid"],
                proof_method=method,
                verification_time=verification_time,
                created_at=start_time,
            )

            if proof["valid"]:
                self.known_theorems.append(formal_proof)
                logger.info(f"Theorem proved: {conclusion}")
            else:
                logger.warning(f"Failed to prove theorem: {conclusion}")

            return formal_proof

        except Exception as e:
            logger.error(f"Error in theorem proving: {e}")
            return FormalProof(
                id=self._generate_proof_id(),
                theorem=f"{' & '.join(hypothesis)} => {conclusion}",
                hypothesis=hypothesis,
                conclusion=conclusion,
                proof_steps=[],
                validity=False,
                proof_method=method,
                verification_time=0.0,
                created_at=start_time,
            )

    # ----- helpers shared by all proof methods -----

    @staticmethod
    def _collect_free_symbols(formulas) -> Set[sp.Symbol]:
        """Gather free symbols from a list of SymPy expressions."""
        syms: Set[sp.Symbol] = set()
        for f in formulas:
            if hasattr(f, "free_symbols"):
                syms.update(f.free_symbols)
        return syms

    @staticmethod
    def _check_ungrounded(
        premise_formulas, conclusion_formula
    ) -> Optional[Set[sp.Symbol]]:
        """Return ungrounded symbols in conclusion, or None if all grounded."""
        premise_syms: Set[sp.Symbol] = set()
        for pf in premise_formulas:
            if hasattr(pf, "free_symbols"):
                premise_syms.update(pf.free_symbols)
        concl_syms = (
            conclusion_formula.free_symbols
            if hasattr(conclusion_formula, "free_symbols")
            else set()
        )
        diff = concl_syms - premise_syms
        return diff if diff else None

    # ----- resolution -----

    def _prove_by_resolution(self, hypothesis: List[str], conclusion: str) -> Dict[str, Any]:
        """Prove theorem using refutation-based resolution.

        The approach is sound: if ``Premises ∧ ¬Conclusion`` is unsatisfiable
        then the premises logically entail the conclusion.

        Safety guard: if the conclusion contains free symbols that do not
        appear in *any* premise (including axioms), the proof is rejected
        outright — an ungrounded conclusion cannot be logically entailed.
        """
        steps = []
        step_count = 1

        # Convert to SymPy expressions
        hyp_formulas = [self._parse_formula(h) for h in hypothesis]
        conclusion_formula = self._parse_formula(conclusion)

        # Add axioms to hypothesis
        axiom_formulas = [axiom.to_sympy() for axiom in self.axioms]
        all_premises = hyp_formulas + axiom_formulas

        steps.append(
            ProofStep(
                step_number=step_count,
                rule_applied="assumption",
                premises=hypothesis,
                conclusion=" & ".join(hypothesis),
                justification="Given hypotheses",
            )
        )
        step_count += 1

        # --- Ungrounded-symbol safety check ---
        ungrounded = self._check_ungrounded(all_premises, conclusion_formula)
        if ungrounded:
            steps.append(
                ProofStep(
                    step_number=step_count,
                    rule_applied="ungrounded_symbol_check",
                    premises=[],
                    conclusion="INVALID",
                    justification=(
                        f"Conclusion contains symbols not present in any premise: "
                        f"{', '.join(str(s) for s in ungrounded)}"
                    ),
                )
            )
            return {"valid": False, "steps": steps, "method": "resolution"}

        # --- Premise consistency check ---
        # If the premises themselves are contradictory, reject the proof.
        # Ex falso quodlibet is logically valid but meaningless for safety
        # verification — a contradictory premise set should signal an error,
        # not auto-prove arbitrary conclusions.
        combined_premises = And(*all_premises) if all_premises else sp.true
        if not satisfiable(combined_premises):
            steps.append(
                ProofStep(
                    step_number=step_count,
                    rule_applied="contradiction_check",
                    premises=[],
                    conclusion="INVALID",
                    justification=(
                        "Premises (including axioms) are contradictory — "
                        "no valid proof possible from inconsistent assumptions"
                    ),
                )
            )
            return {"valid": False, "steps": steps, "method": "resolution"}

        # --- Refutation: is (Premises ∧ ¬Conclusion) unsatisfiable? ---
        is_valid = not satisfiable(And(combined_premises, Not(conclusion_formula)))

        if is_valid:
            steps.append(
                ProofStep(
                    step_number=step_count,
                    rule_applied="resolution",
                    premises=[str(combined_premises)],
                    conclusion=str(conclusion_formula),
                    justification="Refutation: Premises ∧ ¬Conclusion is unsatisfiable",
                )
            )

        return {"valid": is_valid, "steps": steps, "method": "resolution"}

    # ----- natural deduction -----

    def _prove_by_natural_deduction(self, hypothesis: List[str], conclusion: str) -> Dict[str, Any]:
        """Prove theorem using forward-chaining natural deduction.

        Applies modus ponens, modus tollens, and simplification symbolically
        over SymPy expressions rather than fragile string matching.
        """
        steps = []
        step_count = 1

        steps.append(
            ProofStep(
                step_number=step_count,
                rule_applied="assumption",
                premises=[],
                conclusion=" & ".join(hypothesis),
                justification="Given hypotheses",
            )
        )

        # Parse everything into SymPy
        known_exprs: Set[sp.Basic] = set()
        for h in hypothesis:
            known_exprs.add(self._parse_formula(h))

        # Include axioms
        for axiom in self.axioms:
            known_exprs.add(axiom.to_sympy())

        conclusion_formula = self._parse_formula(conclusion)

        # --- Ungrounded-symbol check ---
        ungrounded = self._check_ungrounded(known_exprs, conclusion_formula)
        if ungrounded:
            return {"valid": False, "steps": steps, "method": "natural_deduction"}

        # --- Premise consistency check ---
        combined_nd = And(*known_exprs) if known_exprs else sp.true
        if not satisfiable(combined_nd):
            return {"valid": False, "steps": steps, "method": "natural_deduction"}

        # Check if conclusion is already known
        if conclusion_formula in known_exprs:
            step_count += 1
            steps.append(
                ProofStep(
                    step_number=step_count,
                    rule_applied="identity",
                    premises=[str(conclusion_formula)],
                    conclusion=str(conclusion_formula),
                    justification="Conclusion is directly a premise",
                )
            )
            return {"valid": True, "steps": steps, "method": "natural_deduction"}

        # Forward-chaining: repeatedly apply rules until no new facts or
        # conclusion found.
        MAX_ITERATIONS = 50
        for _ in range(MAX_ITERATIONS):
            new_facts: Set[sp.Basic] = set()
            for expr in list(known_exprs):
                # Modus ponens: if we know (A >> B) and we know A, derive B
                if isinstance(expr, Implies):
                    antecedent, consequent = expr.args
                    if antecedent in known_exprs and consequent not in known_exprs:
                        new_facts.add(consequent)
                        step_count += 1
                        steps.append(
                            ProofStep(
                                step_number=step_count,
                                rule_applied="modus_ponens",
                                premises=[str(antecedent), str(expr)],
                                conclusion=str(consequent),
                                justification="Modus ponens",
                            )
                        )
                        if consequent == conclusion_formula:
                            return {"valid": True, "steps": steps, "method": "natural_deduction"}

                    # Modus tollens: if (A >> B) and ~B, derive ~A
                    neg_consequent = Not(consequent)
                    if neg_consequent in known_exprs:
                        neg_antecedent = Not(antecedent)
                        if neg_antecedent not in known_exprs:
                            new_facts.add(neg_antecedent)
                            step_count += 1
                            steps.append(
                                ProofStep(
                                    step_number=step_count,
                                    rule_applied="modus_tollens",
                                    premises=[str(neg_consequent), str(expr)],
                                    conclusion=str(neg_antecedent),
                                    justification="Modus tollens",
                                )
                            )
                            if neg_antecedent == conclusion_formula:
                                return {"valid": True, "steps": steps, "method": "natural_deduction"}

                # Simplification: if we know (A & B), derive A and B
                if isinstance(expr, And):
                    for arg in expr.args:
                        if arg not in known_exprs:
                            new_facts.add(arg)

            if not new_facts:
                break
            known_exprs.update(new_facts)

        return {"valid": conclusion_formula in known_exprs, "steps": steps, "method": "natural_deduction"}

    # ----- model checking -----

    def _prove_by_model_checking(self, hypothesis: List[str], conclusion: str) -> Dict[str, Any]:
        """Prove theorem by exhaustive model checking.

        Enumerates *all* 2^n truth assignments for the n propositional
        variables.  The conclusion is valid iff it holds in every model
        that satisfies all hypotheses.

        For large variable sets (>20 variables) this falls back to SymPy
        satisfiability to avoid combinatorial explosion.
        """
        steps = []

        # Convert to SymPy for model checking
        hyp_formulas = [self._parse_formula(h) for h in hypothesis]
        conclusion_formula = self._parse_formula(conclusion)

        # Include axioms in the premises, same as resolution
        axiom_formulas = [axiom.to_sympy() for axiom in self.axioms]
        all_premise_formulas = hyp_formulas + axiom_formulas

        # --- Ungrounded-symbol safety check ---
        ungrounded = self._check_ungrounded(all_premise_formulas, conclusion_formula)
        if ungrounded:
            steps.append(
                ProofStep(
                    step_number=1,
                    rule_applied="ungrounded_symbol_check",
                    premises=[],
                    conclusion="INVALID",
                    justification=(
                        f"Conclusion contains symbols not in premises: "
                        f"{', '.join(str(s) for s in ungrounded)}"
                    ),
                )
            )
            return {"valid": False, "steps": steps, "method": "model_checking", "counter_examples": []}

        # --- Premise consistency check ---
        combined_mc = And(*all_premise_formulas) if all_premise_formulas else sp.true
        if not satisfiable(combined_mc):
            steps.append(
                ProofStep(
                    step_number=1,
                    rule_applied="contradiction_check",
                    premises=[],
                    conclusion="INVALID",
                    justification="Premises are contradictory — no valid proof possible",
                )
            )
            return {"valid": False, "steps": steps, "method": "model_checking", "counter_examples": []}

        # Collect all propositional variables
        variables: Set[sp.Symbol] = set()
        for formula in all_premise_formulas + [conclusion_formula]:
            if hasattr(formula, "free_symbols"):
                variables.update(formula.free_symbols)

        # Check conclusion in every model where all premises hold
        is_valid = True
        counter_examples: list = []
        var_list = sorted(variables, key=str)  # deterministic order

        if len(var_list) > 20:
            # Too many variables for brute-force; fall back to SAT check
            combined = And(*all_premise_formulas) if all_premise_formulas else sp.true
            is_valid = not satisfiable(And(combined, Not(conclusion_formula)))
        elif var_list:
            for truth_vals in itertools.product([True, False], repeat=len(var_list)):
                assignment = dict(zip(var_list, truth_vals))

                premise_vals = [f.subs(assignment) for f in all_premise_formulas]
                # All premises must evaluate to True in this model
                if all(v == sp.true or v is True for v in premise_vals):
                    conclusion_val = conclusion_formula.subs(assignment)
                    if conclusion_val == sp.false or conclusion_val is False:
                        is_valid = False
                        counter_examples.append(
                            {str(k): v for k, v in assignment.items()}
                        )
        else:
            # No variables — vacuously check the constant expressions
            if all(f == sp.true or f is True for f in all_premise_formulas):
                conclusion_val = conclusion_formula
                if conclusion_val == sp.false or conclusion_val is False:
                    is_valid = False

        steps.append(
            ProofStep(
                step_number=1,
                rule_applied="model_checking",
                premises=hypothesis,
                conclusion=conclusion if is_valid else "INVALID",
                justification=(
                    f"Exhaustive model checking over {len(var_list)} variables "
                    f"({2 ** len(var_list) if len(var_list) <= 20 else '2^' + str(len(var_list))} models). "
                    f"Counter-examples: {len(counter_examples)}"
                ),
            )
        )

        return {
            "valid": is_valid,
            "steps": steps,
            "method": "model_checking",
            "counter_examples": counter_examples,
        }

    # ----- inference rules (kept for backward compat) -----

    def _initialize_inference_rules(self) -> List[Dict[str, Any]]:
        """Initialize basic inference rules."""
        return [
            {
                "name": "modus_ponens",
                "premises": ["A", "A -> B"],
                "conclusion": "B",
                "description": "If A and A implies B, then B",
            },
            {
                "name": "modus_tollens",
                "premises": ["A -> B", "~B"],
                "conclusion": "~A",
                "description": "If A implies B and not B, then not A",
            },
            {
                "name": "conjunction",
                "premises": ["A", "B"],
                "conclusion": "A & B",
                "description": "If A and B, then A and B",
            },
            {
                "name": "simplification",
                "premises": ["A & B"],
                "conclusion": "A",
                "description": "If A and B, then A",
            },
        ]

    def _can_apply_rule(self, rule: Dict[str, Any], facts: Set[str]) -> bool:
        """Check if an inference rule can be applied to current facts."""
        return all(premise in facts for premise in rule["premises"])

    def _apply_rule(self, rule: Dict[str, Any], facts: Set[str]) -> Optional[str]:
        """Apply an inference rule to derive new fact."""
        if rule["name"] == "modus_ponens":
            for fact in facts:
                if " -> " in fact:
                    antecedent, consequent = fact.split(" -> ")
                    if antecedent.strip() in facts:
                        return consequent.strip()
        return rule.get("conclusion")

    def _parse_formula(self, formula: str) -> sp.Basic:
        """Parse string formula to SymPy expression using the shared parser."""
        return parse_logic_formula(formula)

    def _generate_proof_id(self) -> str:
        """Generate unique proof ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"proof_{timestamp}_{id(self) % 10000}"


# ---------------------------------------------------------------------------
# EthicalVerificationEngine
# ---------------------------------------------------------------------------

class EthicalVerificationEngine:
    """Main engine for ethical constraint verification."""

    def __init__(self):
        self.constraints: Dict[str, EthicalConstraint] = {}
        self.theorem_prover = TheoremProver()
        self.verification_cache: Dict[str, FormalProof] = {}

        # Initialize standard ethical axioms
        self._initialize_ethical_axioms()

    def add_constraint(self, constraint: EthicalConstraint):
        """Add an ethical constraint to the system."""
        self.constraints[constraint.id] = constraint
        logger.info(f"Added ethical constraint: {constraint.name}")

    def verify_proposal_ethics(self, proposal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a proposal against all ethical constraints."""
        verification_results = {
            "overall_valid": True,
            "constraint_results": {},
            "failed_constraints": [],
            "warnings": [],
            "proofs": [],
        }

        # Sort constraints by priority
        sorted_constraints = sorted(
            self.constraints.values(), key=lambda c: c.priority, reverse=True
        )

        for constraint in sorted_constraints:
            result = self._verify_single_constraint(proposal_data, constraint)

            verification_results["constraint_results"][constraint.id] = result
            verification_results["proofs"].append(result["proof"])

            if not result["valid"]:
                verification_results["overall_valid"] = False
                verification_results["failed_constraints"].append(
                    {
                        "constraint_id": constraint.id,
                        "constraint_name": constraint.name,
                        "principle": constraint.principle.value,
                        "reason": result["reason"],
                    }
                )

            if result.get("warnings"):
                verification_results["warnings"].extend(result["warnings"])

        logger.info(
            f"Ethical verification completed. Valid: {verification_results['overall_valid']}"
        )
        return verification_results

    def _verify_single_constraint(
        self, proposal_data: Dict[str, Any], constraint: EthicalConstraint
    ) -> Dict[str, Any]:
        """Verify a proposal against a single ethical constraint.

        The conclusion to prove is the constraint's ``formal_specification``
        (e.g. ``~causes_harm``), **not** an ungrounded synthetic symbol like
        ``satisfies_non_maleficence``.  The old approach generated a symbol
        with no logical relationship to any premise, making proofs
        meaningless.
        """
        try:
            # Extract relevant facts from proposal
            facts = self._extract_facts_from_proposal(proposal_data, constraint)

            # Create hypothesis from facts and constraint predicates
            hypothesis = []
            for fact_name, fact_value in facts.items():
                if fact_value:
                    hypothesis.append(fact_name)
                else:
                    hypothesis.append(f"~{fact_name}")

            # Add constraint predicates as additional hypothesis —
            # but only those whose *name* is not already a known fact
            for predicate in constraint.predicates:
                if predicate.name not in facts:
                    hypothesis.append(predicate.formula)

            # The conclusion is the constraint's formal specification, which
            # uses the same propositional symbols as the extracted facts.
            conclusion = constraint.formal_specification

            # Attempt to prove constraint satisfaction
            proof = self.theorem_prover.prove_theorem(hypothesis, conclusion, method="resolution")

            result = {
                "valid": proof.validity,
                "proof": proof,
                "reason": self._generate_verification_reason(proof, constraint),
                "warnings": [],
            }

            # Add warnings for potential issues
            if proof.validity and proof.verification_time > 5.0:
                result["warnings"].append(
                    f"Verification took {proof.verification_time:.2f}s - consider constraint optimization"
                )

            return result

        except Exception as e:
            logger.error(f"Error verifying constraint {constraint.id}: {e}")
            return {
                "valid": False,
                "proof": None,
                "reason": f"Verification error: {e}",
                "warnings": [f"Technical error in verification: {e}"],
            }

    def _extract_facts_from_proposal(
        self, proposal_data: Dict[str, Any], constraint: EthicalConstraint
    ) -> Dict[str, bool]:
        """Extract relevant facts from proposal for constraint verification."""
        facts = {}

        # Map proposal fields to logical predicates
        field_mappings = {
            "has_human_oversight": "has_human_oversight",
            "respects_autonomy": "respects_autonomy",
            "causes_harm": "causes_harm",
            "is_fair": "is_fair",
            "is_transparent": "is_transparent",
            "has_consent": "has_consent",
            "protects_privacy": "protects_privacy",
            "is_beneficial": "is_beneficial",
            "is_accountable": "is_accountable",
            "preserves_dignity": "preserves_dignity",
        }

        # Extract boolean facts from proposal
        for field, predicate in field_mappings.items():
            if field in proposal_data:
                facts[predicate] = bool(proposal_data[field])

        # Extract facts based on impact assessment
        impact = proposal_data.get("impact_assessment", {})

        if "harm_level" in impact:
            facts["causes_harm"] = impact["harm_level"] > 0
            facts["causes_significant_harm"] = impact["harm_level"] > 0.5

        if "benefit_level" in impact:
            facts["is_beneficial"] = impact["benefit_level"] > 0
            facts["is_highly_beneficial"] = impact["benefit_level"] > 0.7

        if "affected_parties" in impact:
            facts["affects_stakeholders"] = len(impact["affected_parties"]) > 0
            facts["affects_many_stakeholders"] = len(impact["affected_parties"]) > 10

        # Extract facts based on proposal type and content
        proposal_type = proposal_data.get("category", "").lower()
        description = proposal_data.get("description", "").lower()

        facts["is_policy_change"] = proposal_type == "policy"
        facts["is_technical_change"] = proposal_type == "technical"
        facts["involves_ai_systems"] = "ai" in description or "artificial" in description
        facts["involves_data_processing"] = "data" in description or "processing" in description

        return facts

    def _generate_verification_reason(
        self, proof: Optional[FormalProof], constraint: EthicalConstraint
    ) -> str:
        """Generate human-readable reason for verification result."""
        if not proof:
            return "Could not generate formal proof"

        if proof.validity:
            return f"Constraint '{constraint.name}' satisfied via {proof.proof_method}"
        else:
            return f"Constraint '{constraint.name}' violated - proof failed"

    def _initialize_ethical_axioms(self):
        """Initialize fundamental ethical axioms.

        Note: ``->`` (implies) has *lower* precedence than ``&`` (and) in
        SymPy, so ``A -> B & C`` parses as ``(A -> B) & C``.  Parenthesise
        the consequent when it contains ``&``/``|``.
        """
        axioms = [
            EthicalAxiom(
                "autonomy_preservation",
                "respects_autonomy -> ~violates_autonomy",
                "Respecting autonomy means not violating autonomy",
            ),
            EthicalAxiom(
                "non_maleficence",
                "~causes_harm | (causes_harm -> (has_justification & has_mitigation))",
                "Do no harm, or if harm is caused, it must be justified and mitigated",
            ),
            EthicalAxiom(
                "beneficence",
                "is_beneficial -> promotes_wellbeing",
                "Beneficial actions promote wellbeing",
            ),
            EthicalAxiom(
                "justice_fairness",
                "is_fair -> (equal_treatment & proportional_distribution)",
                "Fairness requires equal treatment and proportional distribution",
            ),
            EthicalAxiom(
                "transparency_requirement",
                "affects_stakeholders -> is_transparent",
                "Actions affecting stakeholders must be transparent",
            ),
            EthicalAxiom(
                "consent_requirement",
                "affects_personal_data -> has_consent",
                "Processing personal data requires consent",
            ),
            EthicalAxiom(
                "accountability",
                "is_accountable -> (has_oversight & has_responsibility)",
                "Accountability requires oversight and assigned responsibility",
            ),
            EthicalAxiom(
                "dignity_preservation",
                "preserves_dignity -> ~treats_as_mere_means",
                "Preserving dignity means not treating persons as mere means",
            ),
        ]

        for axiom in axioms:
            self.theorem_prover.add_axiom(axiom)

    def generate_ethics_report(self, verification_results: Dict[str, Any]) -> str:
        """Generate a comprehensive ethics verification report."""
        report = []
        report.append("=== ETHICAL VERIFICATION REPORT ===\n")

        overall_valid = verification_results["overall_valid"]
        report.append(f"Overall Verification Status: {'PASSED' if overall_valid else 'FAILED'}\n")

        if verification_results["failed_constraints"]:
            report.append("FAILED CONSTRAINTS:")
            for failure in verification_results["failed_constraints"]:
                report.append(f"  - {failure['constraint_name']} ({failure['principle']})")
                report.append(f"    Reason: {failure['reason']}")

        if verification_results["warnings"]:
            report.append("\nWARNINGS:")
            for warning in verification_results["warnings"]:
                report.append(f"  - {warning}")

        report.append(
            f"\nTotal Constraints Checked: {len(verification_results['constraint_results'])}"
        )
        report.append(
            f"Constraints Passed: {sum(1 for r in verification_results['constraint_results'].values() if r['valid'])}"
        )

        return "\n".join(report)

    def get_verification_statistics(self) -> Dict[str, Any]:
        """Get verification system statistics."""
        return {
            "total_constraints": len(self.constraints),
            "total_axioms": len(self.theorem_prover.axioms),
            "total_theorems_proved": len(self.theorem_prover.known_theorems),
            "cache_size": len(self.verification_cache),
            "principles_covered": list(set(c.principle.value for c in self.constraints.values())),
        }
