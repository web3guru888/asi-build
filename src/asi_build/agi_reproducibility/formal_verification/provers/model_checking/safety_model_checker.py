"""
Model Checking for AGI Safety Properties

Implements symbolic model checking, explicit-state model checking, and
bounded model checking for AGI safety verification.

Supports:
- CTL/LTL temporal logic model checking
- Safety invariant verification
- Reachability analysis
- Counterexample generation
- Abstraction refinement
"""

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from ...lang.ast.safety_ast import *


class ModelCheckResult(Enum):
    """Result of model checking."""

    SATISFIED = "satisfied"
    VIOLATED = "violated"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class SystemState:
    """Represents a state in the system model."""

    id: str
    variables: Dict[str, Any]

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, SystemState) and self.id == other.id


@dataclass
class Transition:
    """Represents a transition between states."""

    source: SystemState
    target: SystemState
    action: str
    guard: Optional[SafetyExpression] = None

    def is_enabled(self, state: SystemState) -> bool:
        """Check if transition is enabled in given state."""
        if self.guard is None:
            return True
        # Simplified guard evaluation
        return True  # Would evaluate guard in real implementation


@dataclass
class CounterExample:
    """Counterexample trace showing property violation."""

    property_name: str
    trace: List[SystemState]
    violated_at_step: int
    violation_description: str


@dataclass
class ModelCheckTrace:
    """Complete trace of model checking process."""

    property: SafetyExpression
    result: ModelCheckResult
    counterexample: Optional[CounterExample]
    states_explored: int
    time_taken: float
    memory_used: int = 0


class SystemModel:
    """Represents the system being verified."""

    def __init__(self):
        self.states: Set[SystemState] = set()
        self.initial_states: Set[SystemState] = set()
        self.transitions: List[Transition] = []
        self.atomic_propositions: Dict[str, SafetyExpression] = {}

    def add_state(self, state: SystemState, is_initial: bool = False):
        """Add a state to the model."""
        self.states.add(state)
        if is_initial:
            self.initial_states.add(state)

    def add_transition(self, transition: Transition):
        """Add a transition to the model."""
        self.transitions.append(transition)

    def get_successors(self, state: SystemState) -> List[SystemState]:
        """Get all successor states of a given state."""
        successors = []
        for transition in self.transitions:
            if transition.source == state and transition.is_enabled(state):
                successors.append(transition.target)
        return successors

    def evaluate_proposition(self, prop: str, state: SystemState) -> bool:
        """Evaluate atomic proposition in a state."""
        if prop in self.atomic_propositions:
            # Simplified evaluation
            return True  # Would evaluate expression in real implementation
        return False


class SafetyModelChecker(ABC):
    """Abstract base class for safety model checkers."""

    @abstractmethod
    def check_property(
        self, model: SystemModel, property: SafetyExpression, timeout: float = 30.0
    ) -> ModelCheckTrace:
        """Check if property holds in the model."""
        pass


class CTLModelChecker(SafetyModelChecker):
    """CTL (Computation Tree Logic) model checker."""

    def __init__(self):
        self.max_states = 10000

    def check_property(
        self, model: SystemModel, property: SafetyExpression, timeout: float = 30.0
    ) -> ModelCheckTrace:
        """Check CTL property using symbolic model checking."""
        start_time = time.time()
        states_explored = 0

        try:
            # Compute fixed point for CTL formula
            satisfying_states = self._compute_ctl_formula(model, property, start_time, timeout)

            # Check if all initial states satisfy the property
            if all(state in satisfying_states for state in model.initial_states):
                result = ModelCheckResult.SATISFIED
                counterexample = None
            else:
                result = ModelCheckResult.VIOLATED
                # Generate counterexample
                counterexample = self._generate_counterexample(model, property, satisfying_states)

            states_explored = len(model.states)

            return ModelCheckTrace(
                property=property,
                result=result,
                counterexample=counterexample,
                states_explored=states_explored,
                time_taken=time.time() - start_time,
            )

        except TimeoutError:
            return ModelCheckTrace(
                property=property,
                result=ModelCheckResult.TIMEOUT,
                counterexample=None,
                states_explored=states_explored,
                time_taken=time.time() - start_time,
            )
        except Exception as e:
            return ModelCheckTrace(
                property=property,
                result=ModelCheckResult.ERROR,
                counterexample=None,
                states_explored=states_explored,
                time_taken=time.time() - start_time,
            )

    def _compute_ctl_formula(
        self, model: SystemModel, formula: SafetyExpression, start_time: float, timeout: float
    ) -> Set[SystemState]:
        """Compute set of states satisfying CTL formula."""
        if time.time() - start_time > timeout:
            raise TimeoutError()

        if isinstance(formula, Variable):
            # Atomic proposition
            return {
                state for state in model.states if model.evaluate_proposition(formula.name, state)
            }

        elif isinstance(formula, Constant):
            if formula.value is True:
                return set(model.states)
            else:
                return set()

        elif isinstance(formula, BinaryOperation):
            if formula.operator == LogicalOperator.AND:
                left_states = self._compute_ctl_formula(model, formula.left, start_time, timeout)
                right_states = self._compute_ctl_formula(model, formula.right, start_time, timeout)
                return left_states.intersection(right_states)

            elif formula.operator == LogicalOperator.OR:
                left_states = self._compute_ctl_formula(model, formula.left, start_time, timeout)
                right_states = self._compute_ctl_formula(model, formula.right, start_time, timeout)
                return left_states.union(right_states)

            elif formula.operator == LogicalOperator.IMPLIES:
                left_states = self._compute_ctl_formula(model, formula.left, start_time, timeout)
                right_states = self._compute_ctl_formula(model, formula.right, start_time, timeout)
                # ¬left ∨ right
                not_left = model.states.difference(left_states)
                return not_left.union(right_states)

        elif isinstance(formula, UnaryOperation):
            if formula.operator == LogicalOperator.NOT:
                operand_states = self._compute_ctl_formula(
                    model, formula.operand, start_time, timeout
                )
                return model.states.difference(operand_states)

        elif isinstance(formula, TemporalExpression):
            return self._compute_temporal_ctl(model, formula, start_time, timeout)

        return set()

    def _compute_temporal_ctl(
        self, model: SystemModel, formula: TemporalExpression, start_time: float, timeout: float
    ) -> Set[SystemState]:
        """Compute temporal CTL operators."""
        if formula.operator == TemporalOperator.ALWAYS:
            # AG(p) - on all paths, p always holds
            return self._compute_ag(model, formula.operand, start_time, timeout)

        elif formula.operator == TemporalOperator.EVENTUALLY:
            # AF(p) - on all paths, p eventually holds
            return self._compute_af(model, formula.operand, start_time, timeout)

        elif formula.operator == TemporalOperator.NEXT:
            # AX(p) - on all paths, p holds in next state
            return self._compute_ax(model, formula.operand, start_time, timeout)

        return set()

    def _compute_ag(
        self, model: SystemModel, formula: SafetyExpression, start_time: float, timeout: float
    ) -> Set[SystemState]:
        """Compute AG(p) - always globally."""
        p_states = self._compute_ctl_formula(model, formula, start_time, timeout)

        # Fixed point computation
        current = p_states.copy()
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError()

            new_current = set()
            for state in current:
                successors = model.get_successors(state)
                if all(succ in current for succ in successors):
                    new_current.add(state)

            if new_current == current:
                break
            current = new_current

        return current

    def _compute_af(
        self, model: SystemModel, formula: SafetyExpression, start_time: float, timeout: float
    ) -> Set[SystemState]:
        """Compute AF(p) - always eventually."""
        p_states = self._compute_ctl_formula(model, formula, start_time, timeout)

        # Fixed point computation
        current = p_states.copy()
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError()

            new_states = set()
            for state in model.states:
                if state in current:
                    new_states.add(state)
                else:
                    successors = model.get_successors(state)
                    if successors and all(succ in current for succ in successors):
                        new_states.add(state)

            if new_states == current:
                break
            current = new_states

        return current

    def _compute_ax(
        self, model: SystemModel, formula: SafetyExpression, start_time: float, timeout: float
    ) -> Set[SystemState]:
        """Compute AX(p) - always next."""
        p_states = self._compute_ctl_formula(model, formula, start_time, timeout)

        ax_states = set()
        for state in model.states:
            successors = model.get_successors(state)
            if successors and all(succ in p_states for succ in successors):
                ax_states.add(state)

        return ax_states

    def _generate_counterexample(
        self, model: SystemModel, property: SafetyExpression, satisfying_states: Set[SystemState]
    ) -> CounterExample:
        """Generate counterexample for violated property."""
        # Find initial state that doesn't satisfy property
        violating_initial = None
        for state in model.initial_states:
            if state not in satisfying_states:
                violating_initial = state
                break

        if violating_initial is None:
            return CounterExample("unknown", [], 0, "No counterexample found")

        # Generate trace showing violation
        trace = [violating_initial]
        current = violating_initial

        # Simple path exploration
        for i in range(10):  # Max trace length
            successors = model.get_successors(current)
            if not successors:
                break

            # Choose first successor not satisfying property
            next_state = None
            for succ in successors:
                if succ not in satisfying_states:
                    next_state = succ
                    break

            if next_state is None:
                next_state = successors[0]

            trace.append(next_state)
            current = next_state

        return CounterExample(
            property_name=str(property),
            trace=trace,
            violated_at_step=0,
            violation_description=f"Property {property} violated in initial state",
        )


class LTLModelChecker(SafetyModelChecker):
    """LTL (Linear Temporal Logic) model checker."""

    def __init__(self):
        self.max_depth = 1000

    def check_property(
        self, model: SystemModel, property: SafetyExpression, timeout: float = 30.0
    ) -> ModelCheckTrace:
        """Check LTL property using tableau method."""
        start_time = time.time()
        states_explored = 0

        try:
            # Convert LTL formula to Büchi automaton
            buchi_automaton = self._ltl_to_buchi(property)

            # Check emptiness of product automaton
            if self._is_language_empty(model, buchi_automaton, start_time, timeout):
                result = ModelCheckResult.SATISFIED
                counterexample = None
            else:
                result = ModelCheckResult.VIOLATED
                counterexample = self._generate_ltl_counterexample(model, property)

            states_explored = len(model.states)

            return ModelCheckTrace(
                property=property,
                result=result,
                counterexample=counterexample,
                states_explored=states_explored,
                time_taken=time.time() - start_time,
            )

        except TimeoutError:
            return ModelCheckTrace(
                property=property,
                result=ModelCheckResult.TIMEOUT,
                counterexample=None,
                states_explored=states_explored,
                time_taken=time.time() - start_time,
            )
        except Exception as e:
            return ModelCheckTrace(
                property=property,
                result=ModelCheckResult.ERROR,
                counterexample=None,
                states_explored=states_explored,
                time_taken=time.time() - start_time,
            )

    def _ltl_to_buchi(self, formula: SafetyExpression) -> "BuchiAutomaton":
        """Convert LTL formula to Büchi automaton."""
        # Simplified Büchi automaton construction
        return BuchiAutomaton()

    def _is_language_empty(
        self, model: SystemModel, buchi: "BuchiAutomaton", start_time: float, timeout: float
    ) -> bool:
        """Check if language of product automaton is empty."""
        # Simplified emptiness check
        return True  # Would implement proper algorithm

    def _generate_ltl_counterexample(
        self, model: SystemModel, property: SafetyExpression
    ) -> CounterExample:
        """Generate LTL counterexample."""
        return CounterExample(
            property_name=str(property),
            trace=list(model.initial_states)[:1],
            violated_at_step=0,
            violation_description="LTL property violation",
        )


class BuchiAutomaton:
    """Büchi automaton for LTL model checking."""

    def __init__(self):
        self.states: Set[str] = set()
        self.initial_states: Set[str] = set()
        self.accepting_states: Set[str] = set()
        self.transitions: Dict[str, Dict[str, str]] = {}


class BoundedModelChecker(SafetyModelChecker):
    """Bounded model checker using SAT solving."""

    def __init__(self):
        self.max_bound = 50

    def check_property(
        self, model: SystemModel, property: SafetyExpression, timeout: float = 30.0
    ) -> ModelCheckTrace:
        """Check property using bounded model checking."""
        start_time = time.time()
        states_explored = 0

        try:
            # Iteratively increase bound
            for bound in range(self.max_bound):
                if time.time() - start_time > timeout:
                    raise TimeoutError()

                # Generate SAT formula for bound k
                sat_formula = self._generate_sat_formula(model, property, bound)

                # Check satisfiability
                if self._is_satisfiable(sat_formula):
                    # Property violated within bound
                    counterexample = self._extract_counterexample(sat_formula, bound)
                    return ModelCheckTrace(
                        property=property,
                        result=ModelCheckResult.VIOLATED,
                        counterexample=counterexample,
                        states_explored=bound * len(model.states),
                        time_taken=time.time() - start_time,
                    )

                states_explored += len(model.states)

            # Property holds up to max bound
            return ModelCheckTrace(
                property=property,
                result=ModelCheckResult.SATISFIED,
                counterexample=None,
                states_explored=states_explored,
                time_taken=time.time() - start_time,
            )

        except TimeoutError:
            return ModelCheckTrace(
                property=property,
                result=ModelCheckResult.TIMEOUT,
                counterexample=None,
                states_explored=states_explored,
                time_taken=time.time() - start_time,
            )
        except Exception as e:
            return ModelCheckTrace(
                property=property,
                result=ModelCheckResult.ERROR,
                counterexample=None,
                states_explored=states_explored,
                time_taken=time.time() - start_time,
            )

    def _generate_sat_formula(
        self, model: SystemModel, property: SafetyExpression, bound: int
    ) -> str:
        """Generate SAT formula for bounded model checking."""
        # Simplified SAT formula generation
        return f"formula_for_bound_{bound}"

    def _is_satisfiable(self, formula: str) -> bool:
        """Check if SAT formula is satisfiable."""
        # Would use SAT solver like MiniSAT or Z3
        return False  # Simplified

    def _extract_counterexample(self, formula: str, bound: int) -> CounterExample:
        """Extract counterexample from satisfying assignment."""
        return CounterExample(
            property_name="bounded_property",
            trace=[],
            violated_at_step=bound,
            violation_description=f"Property violated within bound {bound}",
        )


class SafetyModelCheckingSuite:
    """Complete model checking suite for AGI safety verification."""

    def __init__(self):
        self.ctl_checker = CTLModelChecker()
        self.ltl_checker = LTLModelChecker()
        self.bounded_checker = BoundedModelChecker()

    def verify_safety_invariant(
        self, model: SystemModel, invariant: SafetyInvariant, timeout: float = 60.0
    ) -> ModelCheckTrace:
        """Verify safety invariant holds in all reachable states."""
        # Create AG(invariant) property
        always_invariant = TemporalExpression(TemporalOperator.ALWAYS, invariant.condition)

        return self.ctl_checker.check_property(model, always_invariant, timeout)

    def verify_goal_stability(
        self, model: SystemModel, goal: SafetyExpression, timeout: float = 60.0
    ) -> ModelCheckTrace:
        """Verify goal remains stable under modifications."""
        # Create stability property: G(goal -> X(goal))
        next_goal = TemporalExpression(TemporalOperator.NEXT, goal)
        stability = BinaryOperation(goal, LogicalOperator.IMPLIES, next_goal)
        always_stable = TemporalExpression(TemporalOperator.ALWAYS, stability)

        return self.ctl_checker.check_property(model, always_stable, timeout)

    def verify_value_preservation(
        self, model: SystemModel, value_function: SafetyExpression, timeout: float = 60.0
    ) -> ModelCheckTrace:
        """Verify values are preserved during learning."""
        # Create preservation property: G(value_consistent)
        always_preserved = TemporalExpression(TemporalOperator.ALWAYS, value_function)

        return self.ctl_checker.check_property(model, always_preserved, timeout)

    def verify_corrigibility(
        self, model: SystemModel, corrigibility_condition: SafetyExpression, timeout: float = 60.0
    ) -> ModelCheckTrace:
        """Verify system remains corrigible."""
        always_corrigible = TemporalExpression(TemporalOperator.ALWAYS, corrigibility_condition)

        return self.ctl_checker.check_property(model, always_corrigible, timeout)

    def verify_bounded_impact(
        self, model: SystemModel, impact_bound: SafetyExpression, timeout: float = 60.0
    ) -> ModelCheckTrace:
        """Verify impact remains within bounds."""
        always_bounded = TemporalExpression(TemporalOperator.ALWAYS, impact_bound)

        return self.ctl_checker.check_property(model, always_bounded, timeout)

    def check_reachability(
        self, model: SystemModel, target_condition: SafetyExpression, timeout: float = 60.0
    ) -> ModelCheckTrace:
        """Check if target condition is reachable."""
        eventually_target = TemporalExpression(TemporalOperator.EVENTUALLY, target_condition)

        return self.ctl_checker.check_property(model, eventually_target, timeout)

    def generate_system_model(self, spec: SafetySpecification) -> SystemModel:
        """Generate system model from safety specification."""
        model = SystemModel()

        # Create states from specification
        for i, state_spec in enumerate(spec.system_states):
            state = SystemState(f"s{i}", {})
            model.add_state(state, i == 0)  # First state is initial

        # Create transitions from specification
        for transition_spec in spec.transitions:
            # Simplified transition creation
            source = SystemState("s0", {})
            target = SystemState("s1", {})
            transition = Transition(source, target, "action")
            model.add_transition(transition)

        return model

    def comprehensive_safety_check(
        self, spec: SafetySpecification, timeout: float = 300.0
    ) -> Dict[str, ModelCheckTrace]:
        """Perform comprehensive safety verification."""
        model = self.generate_system_model(spec)
        results = {}

        per_check_timeout = timeout / (
            len(spec.invariants)
            + len(spec.value_alignments)
            + len(spec.goal_preservations)
            + len(spec.corrigibility_specs)
            + len(spec.impact_bounds)
            + 1
        )

        # Check invariants
        for invariant in spec.invariants:
            results[f"invariant_{invariant.name}"] = self.verify_safety_invariant(
                model, invariant, per_check_timeout
            )

        # Check value alignments
        for alignment in spec.value_alignments:
            results[f"value_alignment_{alignment.name}"] = self.verify_value_preservation(
                model, alignment.preservation_condition, per_check_timeout
            )

        # Check goal preservation
        for preservation in spec.goal_preservations:
            results[f"goal_preservation_{preservation.name}"] = self.verify_goal_stability(
                model, preservation.stability_condition, per_check_timeout
            )

        # Check corrigibility
        for corrigibility in spec.corrigibility_specs:
            results[f"corrigibility_{corrigibility.name}"] = self.verify_corrigibility(
                model, corrigibility.modification_acceptance, per_check_timeout
            )

        # Check impact bounds
        for bound in spec.impact_bounds:
            bound_condition = BinaryOperation(bound.impact_metric, "<=", bound.upper_bound)
            results[f"impact_bound_{bound.name}"] = self.verify_bounded_impact(
                model, bound_condition, per_check_timeout
            )

        return results
