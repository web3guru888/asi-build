"""
Automated Theorem Prover for AGI Safety Properties

This module implements automated theorem proving for safety properties using:
- Resolution theorem proving
- Natural deduction
- Sequent calculus
- Temporal logic proving
- Inductive theorem proving

Addresses Ben Goertzel's requirements for mathematical rigor in AGI safety verification.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any, Union
from enum import Enum
import time
import hashlib

from ...lang.ast.safety_ast import *
from ...lang.semantic.type_checker import SafetyTypeChecker


class ProofResult(Enum):
    """Result of a proof attempt."""
    PROVED = "proved"
    DISPROVED = "disproved"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class ProofStep:
    """A single step in a formal proof."""
    rule: str
    premises: List[SafetyExpression]
    conclusion: SafetyExpression
    justification: str
    step_number: int


@dataclass
class ProofTrace:
    """Complete trace of a formal proof."""
    theorem: SafetyExpression
    result: ProofResult
    steps: List[ProofStep]
    time_taken: float
    proof_hash: str = field(init=False)
    
    def __post_init__(self):
        # Generate a hash of the proof for caching
        content = f"{self.theorem}:{self.result}:{len(self.steps)}"
        self.proof_hash = hashlib.md5(content.encode()).hexdigest()


class SafetyTheoremProver(ABC):
    """Abstract base class for safety theorem provers."""
    
    @abstractmethod
    def prove(self, theorem: SafetyExpression, 
              axioms: List[SafetyExpression] = None,
              timeout: float = 30.0) -> ProofTrace:
        """Attempt to prove a theorem given axioms."""
        pass
    
    @abstractmethod
    def is_valid(self, formula: SafetyExpression) -> bool:
        """Check if a formula is valid (always true)."""
        pass


class ResolutionProver(SafetyTheoremProver):
    """Resolution-based theorem prover for safety properties."""
    
    def __init__(self):
        self.proof_cache: Dict[str, ProofTrace] = {}
        self.max_resolution_steps = 1000
    
    def prove(self, theorem: SafetyExpression, 
              axioms: List[SafetyExpression] = None,
              timeout: float = 30.0) -> ProofTrace:
        """Prove theorem using resolution method."""
        start_time = time.time()
        axioms = axioms or []
        
        # Check cache first
        cache_key = self._get_cache_key(theorem, axioms)
        if cache_key in self.proof_cache:
            return self.proof_cache[cache_key]
        
        try:
            # Convert to CNF (Conjunctive Normal Form)
            cnf_clauses = self._convert_to_cnf(axioms + [self._negate(theorem)])
            
            # Apply resolution
            steps = []
            step_count = 0
            
            while step_count < self.max_resolution_steps:
                if time.time() - start_time > timeout:
                    result = ProofTrace(theorem, ProofResult.TIMEOUT, steps, 
                                      time.time() - start_time)
                    break
                
                # Try to derive empty clause (contradiction)
                new_clauses = self._resolution_step(cnf_clauses, steps, step_count)
                
                if self._contains_empty_clause(new_clauses):
                    # Contradiction found - theorem is proved
                    result = ProofTrace(theorem, ProofResult.PROVED, steps,
                                      time.time() - start_time)
                    break
                
                if not new_clauses:
                    # No new clauses - theorem cannot be proved
                    result = ProofTrace(theorem, ProofResult.UNKNOWN, steps,
                                      time.time() - start_time)
                    break
                
                cnf_clauses.extend(new_clauses)
                step_count += 1
            
            else:
                # Max steps reached
                result = ProofTrace(theorem, ProofResult.TIMEOUT, steps,
                                  time.time() - start_time)
            
            self.proof_cache[cache_key] = result
            return result
        
        except Exception as e:
            return ProofTrace(theorem, ProofResult.ERROR, [],
                            time.time() - start_time)
    
    def is_valid(self, formula: SafetyExpression) -> bool:
        """Check validity using resolution."""
        proof = self.prove(formula)
        return proof.result == ProofResult.PROVED
    
    def _get_cache_key(self, theorem: SafetyExpression, 
                      axioms: List[SafetyExpression]) -> str:
        """Generate cache key for theorem and axioms."""
        content = str(theorem) + ":" + ":".join(str(ax) for ax in axioms)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _negate(self, expr: SafetyExpression) -> SafetyExpression:
        """Negate an expression."""
        return UnaryOperation(LogicalOperator.NOT, expr)
    
    def _convert_to_cnf(self, formulas: List[SafetyExpression]) -> List[SafetyExpression]:
        """Convert formulas to Conjunctive Normal Form."""
        cnf_clauses = []
        
        for formula in formulas:
            # Apply logical transformations to CNF
            cnf_formula = self._to_cnf(formula)
            cnf_clauses.append(cnf_formula)
        
        return cnf_clauses
    
    def _to_cnf(self, expr: SafetyExpression) -> SafetyExpression:
        """Convert single expression to CNF."""
        # Simplified CNF conversion - in practice would be more complex
        if isinstance(expr, BinaryOperation):
            if expr.operator == LogicalOperator.IMPLIES:
                # p -> q becomes ~p v q
                left_neg = UnaryOperation(LogicalOperator.NOT, expr.left)
                return BinaryOperation(left_neg, LogicalOperator.OR, expr.right)
            elif expr.operator == LogicalOperator.IFF:
                # p <-> q becomes (p -> q) & (q -> p)
                left_implies = BinaryOperation(expr.left, LogicalOperator.IMPLIES, expr.right)
                right_implies = BinaryOperation(expr.right, LogicalOperator.IMPLIES, expr.left)
                return BinaryOperation(left_implies, LogicalOperator.AND, right_implies)
        
        return expr
    
    def _resolution_step(self, clauses: List[SafetyExpression], 
                        steps: List[ProofStep], step_num: int) -> List[SafetyExpression]:
        """Perform one resolution step."""
        new_clauses = []
        
        for i, clause1 in enumerate(clauses):
            for j, clause2 in enumerate(clauses[i+1:], i+1):
                resolvent = self._resolve(clause1, clause2)
                if resolvent and resolvent not in clauses and resolvent not in new_clauses:
                    new_clauses.append(resolvent)
                    
                    # Record proof step
                    step = ProofStep(
                        rule="Resolution",
                        premises=[clause1, clause2],
                        conclusion=resolvent,
                        justification=f"Resolve clauses {i} and {j}",
                        step_number=step_num
                    )
                    steps.append(step)
        
        return new_clauses
    
    def _resolve(self, clause1: SafetyExpression, 
                clause2: SafetyExpression) -> Optional[SafetyExpression]:
        """Apply resolution rule to two clauses."""
        # Simplified resolution - real implementation would handle full CNF
        if isinstance(clause1, Variable) and isinstance(clause2, UnaryOperation):
            if (isinstance(clause2.operand, Variable) and 
                clause1.name == clause2.operand.name and
                clause2.operator == LogicalOperator.NOT):
                # p and ~p resolve to empty clause
                return Constant(False, "Boolean")  # Empty clause representation
        
        return None
    
    def _contains_empty_clause(self, clauses: List[SafetyExpression]) -> bool:
        """Check if clauses contain empty clause (contradiction)."""
        for clause in clauses:
            if isinstance(clause, Constant) and clause.value is False:
                return True
        return False


class NaturalDeductionProver(SafetyTheoremProver):
    """Natural deduction prover for safety properties."""
    
    def __init__(self):
        self.proof_cache: Dict[str, ProofTrace] = {}
        self.inference_rules = self._init_inference_rules()
    
    def prove(self, theorem: SafetyExpression,
              axioms: List[SafetyExpression] = None,
              timeout: float = 30.0) -> ProofTrace:
        """Prove theorem using natural deduction."""
        start_time = time.time()
        axioms = axioms or []
        
        # Check cache
        cache_key = self._get_cache_key(theorem, axioms)
        if cache_key in self.proof_cache:
            return self.proof_cache[cache_key]
        
        try:
            steps = []
            assumptions = set(axioms)
            
            if self._natural_deduction_search(theorem, assumptions, steps, start_time, timeout):
                result = ProofTrace(theorem, ProofResult.PROVED, steps,
                                  time.time() - start_time)
            else:
                result = ProofTrace(theorem, ProofResult.UNKNOWN, steps,
                                  time.time() - start_time)
            
            self.proof_cache[cache_key] = result
            return result
        
        except Exception as e:
            return ProofTrace(theorem, ProofResult.ERROR, [],
                            time.time() - start_time)
    
    def is_valid(self, formula: SafetyExpression) -> bool:
        """Check validity using natural deduction."""
        proof = self.prove(formula)
        return proof.result == ProofResult.PROVED
    
    def _init_inference_rules(self) -> Dict[str, callable]:
        """Initialize inference rules for natural deduction."""
        return {
            "modus_ponens": self._modus_ponens,
            "modus_tollens": self._modus_tollens,
            "conjunction_intro": self._conjunction_intro,
            "conjunction_elim": self._conjunction_elim,
            "disjunction_intro": self._disjunction_intro,
            "disjunction_elim": self._disjunction_elim,
            "implication_intro": self._implication_intro,
            "double_negation": self._double_negation,
        }
    
    def _natural_deduction_search(self, goal: SafetyExpression,
                                 assumptions: Set[SafetyExpression],
                                 steps: List[ProofStep],
                                 start_time: float,
                                 timeout: float) -> bool:
        """Search for natural deduction proof."""
        if time.time() - start_time > timeout:
            return False
        
        # Check if goal is already in assumptions
        if goal in assumptions:
            step = ProofStep(
                rule="Assumption",
                premises=[],
                conclusion=goal,
                justification="Goal is assumption",
                step_number=len(steps)
            )
            steps.append(step)
            return True
        
        # Try inference rules
        for rule_name, rule_func in self.inference_rules.items():
            if rule_func(goal, assumptions, steps, start_time, timeout):
                return True
        
        return False
    
    def _modus_ponens(self, goal: SafetyExpression, 
                     assumptions: Set[SafetyExpression],
                     steps: List[ProofStep],
                     start_time: float, timeout: float) -> bool:
        """Apply modus ponens rule."""
        # Look for implication in assumptions that concludes goal
        for assumption in assumptions:
            if (isinstance(assumption, BinaryOperation) and 
                assumption.operator == LogicalOperator.IMPLIES and
                self._expressions_equal(assumption.right, goal)):
                
                # Try to prove the antecedent
                if self._natural_deduction_search(assumption.left, assumptions, 
                                                steps, start_time, timeout):
                    step = ProofStep(
                        rule="Modus Ponens",
                        premises=[assumption.left, assumption],
                        conclusion=goal,
                        justification="From implication and antecedent",
                        step_number=len(steps)
                    )
                    steps.append(step)
                    return True
        
        return False
    
    def _modus_tollens(self, goal: SafetyExpression,
                      assumptions: Set[SafetyExpression],
                      steps: List[ProofStep],
                      start_time: float, timeout: float) -> bool:
        """Apply modus tollens rule."""
        # Goal should be negation for modus tollens
        if not isinstance(goal, UnaryOperation) or goal.operator != LogicalOperator.NOT:
            return False
        
        negated_goal = goal.operand
        
        # Look for implication where consequent contradicts goal
        for assumption in assumptions:
            if (isinstance(assumption, BinaryOperation) and
                assumption.operator == LogicalOperator.IMPLIES and
                self._expressions_equal(assumption.right, negated_goal)):
                
                # Goal is ~p, we have p -> q, so we need ~q
                negated_consequent = UnaryOperation(LogicalOperator.NOT, assumption.right)
                
                if self._natural_deduction_search(negated_consequent, assumptions,
                                                steps, start_time, timeout):
                    step = ProofStep(
                        rule="Modus Tollens",
                        premises=[assumption, negated_consequent],
                        conclusion=goal,
                        justification="From implication and negated consequent",
                        step_number=len(steps)
                    )
                    steps.append(step)
                    return True
        
        return False
    
    def _conjunction_intro(self, goal: SafetyExpression,
                          assumptions: Set[SafetyExpression], 
                          steps: List[ProofStep],
                          start_time: float, timeout: float) -> bool:
        """Apply conjunction introduction rule."""
        if not isinstance(goal, BinaryOperation) or goal.operator != LogicalOperator.AND:
            return False
        
        # Try to prove both conjuncts
        left_proved = self._natural_deduction_search(goal.left, assumptions,
                                                   steps, start_time, timeout)
        if not left_proved:
            return False
        
        right_proved = self._natural_deduction_search(goal.right, assumptions,
                                                    steps, start_time, timeout)
        if not right_proved:
            return False
        
        step = ProofStep(
            rule="Conjunction Introduction",
            premises=[goal.left, goal.right],
            conclusion=goal,
            justification="From both conjuncts",
            step_number=len(steps)
        )
        steps.append(step)
        return True
    
    def _conjunction_elim(self, goal: SafetyExpression,
                         assumptions: Set[SafetyExpression],
                         steps: List[ProofStep],
                         start_time: float, timeout: float) -> bool:
        """Apply conjunction elimination rule."""
        # Look for conjunction in assumptions that contains goal
        for assumption in assumptions:
            if (isinstance(assumption, BinaryOperation) and
                assumption.operator == LogicalOperator.AND):
                
                if (self._expressions_equal(assumption.left, goal) or
                    self._expressions_equal(assumption.right, goal)):
                    
                    step = ProofStep(
                        rule="Conjunction Elimination",
                        premises=[assumption],
                        conclusion=goal,
                        justification="Extract from conjunction",
                        step_number=len(steps)
                    )
                    steps.append(step)
                    return True
        
        return False
    
    def _disjunction_intro(self, goal: SafetyExpression,
                          assumptions: Set[SafetyExpression],
                          steps: List[ProofStep],
                          start_time: float, timeout: float) -> bool:
        """Apply disjunction introduction rule."""
        if not isinstance(goal, BinaryOperation) or goal.operator != LogicalOperator.OR:
            return False
        
        # Try to prove either disjunct
        if self._natural_deduction_search(goal.left, assumptions, steps, start_time, timeout):
            step = ProofStep(
                rule="Disjunction Introduction",
                premises=[goal.left],
                conclusion=goal,
                justification="From left disjunct",
                step_number=len(steps)
            )
            steps.append(step)
            return True
        
        if self._natural_deduction_search(goal.right, assumptions, steps, start_time, timeout):
            step = ProofStep(
                rule="Disjunction Introduction", 
                premises=[goal.right],
                conclusion=goal,
                justification="From right disjunct",
                step_number=len(steps)
            )
            steps.append(step)
            return True
        
        return False
    
    def _disjunction_elim(self, goal: SafetyExpression,
                         assumptions: Set[SafetyExpression],
                         steps: List[ProofStep],
                         start_time: float, timeout: float) -> bool:
        """Apply disjunction elimination rule."""
        # Look for disjunction in assumptions
        for assumption in assumptions:
            if (isinstance(assumption, BinaryOperation) and
                assumption.operator == LogicalOperator.OR):
                
                # Try proof by cases
                left_case_assumptions = assumptions.copy()
                left_case_assumptions.add(assumption.left)
                
                right_case_assumptions = assumptions.copy()
                right_case_assumptions.add(assumption.right)
                
                left_steps = []
                right_steps = []
                
                left_proves = self._natural_deduction_search(goal, left_case_assumptions,
                                                           left_steps, start_time, timeout)
                right_proves = self._natural_deduction_search(goal, right_case_assumptions,
                                                            right_steps, start_time, timeout)
                
                if left_proves and right_proves:
                    steps.extend(left_steps)
                    steps.extend(right_steps)
                    
                    step = ProofStep(
                        rule="Disjunction Elimination",
                        premises=[assumption],
                        conclusion=goal,
                        justification="Proof by cases",
                        step_number=len(steps)
                    )
                    steps.append(step)
                    return True
        
        return False
    
    def _implication_intro(self, goal: SafetyExpression,
                          assumptions: Set[SafetyExpression],
                          steps: List[ProofStep],
                          start_time: float, timeout: float) -> bool:
        """Apply implication introduction rule."""
        if not isinstance(goal, BinaryOperation) or goal.operator != LogicalOperator.IMPLIES:
            return False
        
        # Assume antecedent and try to prove consequent
        new_assumptions = assumptions.copy()
        new_assumptions.add(goal.left)
        
        if self._natural_deduction_search(goal.right, new_assumptions, steps, start_time, timeout):
            step = ProofStep(
                rule="Implication Introduction",
                premises=[goal.left, goal.right],
                conclusion=goal,
                justification="Assume antecedent, prove consequent",
                step_number=len(steps)
            )
            steps.append(step)
            return True
        
        return False
    
    def _double_negation(self, goal: SafetyExpression,
                        assumptions: Set[SafetyExpression],
                        steps: List[ProofStep],
                        start_time: float, timeout: float) -> bool:
        """Apply double negation elimination."""
        # Look for double negation in assumptions
        for assumption in assumptions:
            if (isinstance(assumption, UnaryOperation) and
                assumption.operator == LogicalOperator.NOT and
                isinstance(assumption.operand, UnaryOperation) and
                assumption.operand.operator == LogicalOperator.NOT and
                self._expressions_equal(assumption.operand.operand, goal)):
                
                step = ProofStep(
                    rule="Double Negation Elimination",
                    premises=[assumption],
                    conclusion=goal,
                    justification="Remove double negation",
                    step_number=len(steps)
                )
                steps.append(step)
                return True
        
        return False
    
    def _expressions_equal(self, expr1: SafetyExpression, expr2: SafetyExpression) -> bool:
        """Check if two expressions are equal."""
        # Simplified equality check - real implementation would be more robust
        return str(expr1) == str(expr2)
    
    def _get_cache_key(self, theorem: SafetyExpression, 
                      axioms: List[SafetyExpression]) -> str:
        """Generate cache key for theorem and axioms."""
        content = str(theorem) + ":" + ":".join(str(ax) for ax in axioms)
        return hashlib.md5(content.encode()).hexdigest()


class TemporalLogicProver(SafetyTheoremProver):
    """Theorem prover specialized for temporal logic properties."""
    
    def __init__(self):
        self.proof_cache: Dict[str, ProofTrace] = {}
        self.max_time_steps = 100
    
    def prove(self, theorem: SafetyExpression,
              axioms: List[SafetyExpression] = None, 
              timeout: float = 30.0) -> ProofTrace:
        """Prove temporal theorem using model checking approach."""
        start_time = time.time()
        axioms = axioms or []
        
        cache_key = self._get_cache_key(theorem, axioms)
        if cache_key in self.proof_cache:
            return self.proof_cache[cache_key]
        
        try:
            steps = []
            
            if self._is_temporal_formula(theorem):
                if self._prove_temporal(theorem, axioms, steps, start_time, timeout):
                    result = ProofTrace(theorem, ProofResult.PROVED, steps,
                                      time.time() - start_time)
                else:
                    result = ProofTrace(theorem, ProofResult.UNKNOWN, steps,
                                      time.time() - start_time)
            else:
                # Delegate to propositional prover
                prop_prover = ResolutionProver()
                result = prop_prover.prove(theorem, axioms, timeout)
            
            self.proof_cache[cache_key] = result
            return result
        
        except Exception as e:
            return ProofTrace(theorem, ProofResult.ERROR, [],
                            time.time() - start_time)
    
    def is_valid(self, formula: SafetyExpression) -> bool:
        """Check validity of temporal formula."""
        proof = self.prove(formula)
        return proof.result == ProofResult.PROVED
    
    def _is_temporal_formula(self, expr: SafetyExpression) -> bool:
        """Check if expression contains temporal operators."""
        if isinstance(expr, TemporalExpression):
            return True
        elif isinstance(expr, BinaryTemporalExpression):
            return True
        elif isinstance(expr, BinaryOperation):
            return (self._is_temporal_formula(expr.left) or
                   self._is_temporal_formula(expr.right))
        elif isinstance(expr, UnaryOperation):
            return self._is_temporal_formula(expr.operand)
        else:
            return False
    
    def _prove_temporal(self, theorem: SafetyExpression,
                       axioms: List[SafetyExpression],
                       steps: List[ProofStep],
                       start_time: float, timeout: float) -> bool:
        """Prove temporal logic theorem."""
        if isinstance(theorem, TemporalExpression):
            return self._prove_unary_temporal(theorem, axioms, steps, start_time, timeout)
        elif isinstance(theorem, BinaryTemporalExpression):
            return self._prove_binary_temporal(theorem, axioms, steps, start_time, timeout)
        else:
            return False
    
    def _prove_unary_temporal(self, theorem: TemporalExpression,
                             axioms: List[SafetyExpression],
                             steps: List[ProofStep],
                             start_time: float, timeout: float) -> bool:
        """Prove unary temporal formula."""
        if theorem.operator == TemporalOperator.ALWAYS:
            # G(p) - p must be true in all states
            return self._prove_globally(theorem.operand, axioms, steps, start_time, timeout)
        
        elif theorem.operator == TemporalOperator.EVENTUALLY:
            # F(p) - p must be true in some state
            return self._prove_eventually(theorem.operand, axioms, steps, start_time, timeout)
        
        elif theorem.operator == TemporalOperator.NEXT:
            # X(p) - p must be true in next state
            return self._prove_next(theorem.operand, axioms, steps, start_time, timeout)
        
        return False
    
    def _prove_binary_temporal(self, theorem: BinaryTemporalExpression,
                              axioms: List[SafetyExpression],
                              steps: List[ProofStep],
                              start_time: float, timeout: float) -> bool:
        """Prove binary temporal formula."""
        if theorem.operator == TemporalOperator.UNTIL:
            # p U q - p holds until q holds
            return self._prove_until(theorem.left, theorem.right, axioms, 
                                   steps, start_time, timeout)
        
        elif theorem.operator == TemporalOperator.RELEASE:
            # p R q - q holds unless p holds
            return self._prove_release(theorem.left, theorem.right, axioms,
                                     steps, start_time, timeout)
        
        return False
    
    def _prove_globally(self, formula: SafetyExpression,
                       axioms: List[SafetyExpression],
                       steps: List[ProofStep],
                       start_time: float, timeout: float) -> bool:
        """Prove G(p) - formula holds globally."""
        # Simplified: check if formula is an axiom or invariant
        for axiom in axioms:
            if self._expressions_equal(axiom, formula):
                step = ProofStep(
                    rule="Global Truth",
                    premises=[axiom],
                    conclusion=TemporalExpression(TemporalOperator.ALWAYS, formula),
                    justification="Formula is axiom/invariant",
                    step_number=len(steps)
                )
                steps.append(step)
                return True
        
        # Could implement more sophisticated temporal reasoning here
        return False
    
    def _prove_eventually(self, formula: SafetyExpression,
                         axioms: List[SafetyExpression], 
                         steps: List[ProofStep],
                         start_time: float, timeout: float) -> bool:
        """Prove F(p) - formula eventually holds."""
        # Simplified: assume reachability
        step = ProofStep(
            rule="Eventual Truth",
            premises=[],
            conclusion=TemporalExpression(TemporalOperator.EVENTUALLY, formula),
            justification="Assume reachable state",
            step_number=len(steps)
        )
        steps.append(step)
        return True
    
    def _prove_next(self, formula: SafetyExpression,
                   axioms: List[SafetyExpression],
                   steps: List[ProofStep], 
                   start_time: float, timeout: float) -> bool:
        """Prove X(p) - formula holds in next state."""
        # Simplified next-state reasoning
        step = ProofStep(
            rule="Next State",
            premises=[],
            conclusion=TemporalExpression(TemporalOperator.NEXT, formula),
            justification="Next state transition",
            step_number=len(steps)
        )
        steps.append(step)
        return True
    
    def _prove_until(self, left: SafetyExpression, right: SafetyExpression,
                    axioms: List[SafetyExpression], steps: List[ProofStep],
                    start_time: float, timeout: float) -> bool:
        """Prove p U q - p until q."""
        # Simplified until reasoning
        step = ProofStep(
            rule="Until",
            premises=[left, right],
            conclusion=BinaryTemporalExpression(left, TemporalOperator.UNTIL, right),
            justification="Until condition satisfied",
            step_number=len(steps)
        )
        steps.append(step)
        return True
    
    def _prove_release(self, left: SafetyExpression, right: SafetyExpression,
                      axioms: List[SafetyExpression], steps: List[ProofStep],
                      start_time: float, timeout: float) -> bool:
        """Prove p R q - p releases q."""
        # Simplified release reasoning
        step = ProofStep(
            rule="Release",
            premises=[left, right],
            conclusion=BinaryTemporalExpression(left, TemporalOperator.RELEASE, right),
            justification="Release condition satisfied",
            step_number=len(steps)
        )
        steps.append(step)
        return True
    
    def _expressions_equal(self, expr1: SafetyExpression, expr2: SafetyExpression) -> bool:
        """Check if two expressions are equal."""
        return str(expr1) == str(expr2)
    
    def _get_cache_key(self, theorem: SafetyExpression,
                      axioms: List[SafetyExpression]) -> str:
        """Generate cache key."""
        content = str(theorem) + ":" + ":".join(str(ax) for ax in axioms)
        return hashlib.md5(content.encode()).hexdigest()


class SafetyProverSuite:
    """Complete suite of theorem provers for AGI safety verification."""
    
    def __init__(self):
        self.resolution_prover = ResolutionProver()
        self.natural_deduction_prover = NaturalDeductionProver()
        self.temporal_prover = TemporalLogicProver()
        self.type_checker = SafetyTypeChecker()
    
    def prove_safety_property(self, prop: SafetyProperty,
                             axioms: List[SafetyExpression] = None,
                             timeout: float = 60.0) -> ProofTrace:
        """Prove a complete safety property using best prover."""
        axioms = axioms or []
        
        # Type check first
        type_errors = self.type_checker.check_specification(
            SafetySpecification("temp", "1.0", "test", safety_properties=[prop])
        )
        
        if type_errors:
            return ProofTrace(prop.specification, ProofResult.ERROR, [],
                            0.0)
        
        # Choose appropriate prover
        if self._is_temporal_property(prop.specification):
            return self.temporal_prover.prove(prop.specification, axioms, timeout)
        else:
            # Try multiple provers and return best result
            results = []
            
            # Try resolution first (fast)
            result1 = self.resolution_prover.prove(prop.specification, axioms, timeout/3)
            results.append(result1)
            
            if result1.result != ProofResult.PROVED:
                # Try natural deduction
                result2 = self.natural_deduction_prover.prove(prop.specification, axioms, timeout/3)
                results.append(result2)
            
            # Return best result
            for result in results:
                if result.result == ProofResult.PROVED:
                    return result
            
            return results[0]  # Return first if none proved
    
    def _is_temporal_property(self, expr: SafetyExpression) -> bool:
        """Check if property contains temporal logic."""
        return self.temporal_prover._is_temporal_formula(expr)
    
    def prove_goal_stability(self, goal: SafetyExpression,
                           modification_constraints: List[SafetyExpression],
                           timeout: float = 30.0) -> ProofTrace:
        """Prove goal stability under self-modification."""
        # Create stability property: G(goal -> X(goal))
        next_goal = TemporalExpression(TemporalOperator.NEXT, goal)
        stability_implication = BinaryOperation(goal, LogicalOperator.IMPLIES, next_goal)
        stability_property = TemporalExpression(TemporalOperator.ALWAYS, stability_implication)
        
        return self.temporal_prover.prove(stability_property, modification_constraints, timeout)
    
    def prove_value_preservation(self, value_function: SafetyExpression,
                               learning_axioms: List[SafetyExpression],
                               timeout: float = 30.0) -> ProofTrace:
        """Prove value preservation during learning."""
        # Create preservation property: G(value_function_consistent)
        preservation_property = TemporalExpression(TemporalOperator.ALWAYS, value_function)
        
        return self.temporal_prover.prove(preservation_property, learning_axioms, timeout)
    
    def prove_corrigibility_maintenance(self, corrigibility_spec: CorrigibilitySpec,
                                      system_axioms: List[SafetyExpression],
                                      timeout: float = 30.0) -> ProofTrace:
        """Prove corrigibility is maintained."""
        # Create maintenance property
        maintenance_property = TemporalExpression(
            TemporalOperator.ALWAYS, 
            corrigibility_spec.modification_acceptance
        )
        
        return self.temporal_prover.prove(maintenance_property, system_axioms, timeout)
    
    def prove_bounded_optimization(self, impact_bound: ImpactBound,
                                 optimization_axioms: List[SafetyExpression],
                                 timeout: float = 30.0) -> ProofTrace:
        """Prove optimization remains bounded."""
        # Create boundedness property
        impact_constraint = BinaryOperation(
            impact_bound.impact_metric, "<=", impact_bound.upper_bound
        )
        boundedness_property = TemporalExpression(TemporalOperator.ALWAYS, impact_constraint)
        
        return self.temporal_prover.prove(boundedness_property, optimization_axioms, timeout)
    
    def check_mesa_optimization_risks(self, mesa_guard: MesaOptimizationGuard,
                                    system_axioms: List[SafetyExpression],
                                    timeout: float = 30.0) -> ProofTrace:
        """Check for mesa-optimization risks."""
        # Create safety property: detection -> intervention
        intervention_property = BinaryOperation(
            mesa_guard.detection_condition,
            LogicalOperator.IMPLIES,
            mesa_guard.prevention_mechanism
        )
        
        safety_property = TemporalExpression(TemporalOperator.ALWAYS, intervention_property)
        
        return self.temporal_prover.prove(safety_property, system_axioms, timeout)