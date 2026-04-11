"""
Formal Verification Framework for AGI Safety - Abstract Syntax Tree

This module defines the AST nodes for the AGI Safety Specification Language (AGSSL).
It provides a formal mathematical foundation for expressing safety properties,
value alignment constraints, and verification conditions for AGI systems.

Based on formal methods from model checking, theorem proving, and type theory.
Addresses Ben Goertzel's concerns about mathematical rigor in AGI safety.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union, TypeVar, Generic
from enum import Enum
import uuid

# Type variables for generic specifications
T = TypeVar('T')
V = TypeVar('V')  # Value type
S = TypeVar('S')  # State type


class SafetyPropertyType(Enum):
    """Types of safety properties that can be specified."""
    INVARIANT = "invariant"          # Always true
    TEMPORAL = "temporal"            # Time-dependent properties
    VALUE_ALIGNMENT = "value_align"  # Value preservation
    CORRIGIBILITY = "corrigible"     # Modification acceptance
    GOAL_STABILITY = "goal_stable"   # Goal preservation
    IMPACT_BOUND = "impact_bound"    # Bounded optimization
    MESA_SAFETY = "mesa_safe"        # Mesa-optimization safety


class TemporalOperator(Enum):
    """Temporal logic operators for safety specifications."""
    ALWAYS = "G"        # Globally (always)
    EVENTUALLY = "F"    # Finally (eventually)
    NEXT = "X"          # Next state
    UNTIL = "U"         # Strong until
    WEAK_UNTIL = "W"    # Weak until
    RELEASE = "R"       # Release operator


class LogicalOperator(Enum):
    """Logical operators for safety expressions."""
    AND = "∧"
    OR = "∨"
    NOT = "¬"
    IMPLIES = "→"
    IFF = "↔"
    FORALL = "∀"
    EXISTS = "∃"


@dataclass
class SourceLocation:
    """Source code location for error reporting."""
    file: str
    line: int
    column: int


@dataclass
class SafetyNode(ABC):
    """Base class for all AST nodes in the safety specification language."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    location: Optional[SourceLocation] = None
    annotations: Dict[str, Any] = field(default_factory=dict)
    
    @abstractmethod
    def accept(self, visitor):
        """Visitor pattern for AST traversal."""
        pass
    
    def add_annotation(self, key: str, value: Any) -> None:
        """Add metadata annotation to the node."""
        self.annotations[key] = value


# Core Safety Expressions

@dataclass
class SafetyExpression(SafetyNode):
    """Base class for safety expressions."""
    type_info: Optional[str] = None


@dataclass
class Variable(SafetyExpression):
    """Variable reference in safety specifications."""
    name: str = ""
    domain: Optional[str] = None  # Type domain (e.g., "Real", "Boolean", "Goal")
    
    def accept(self, visitor):
        return visitor.visit_variable(self)


@dataclass
class Constant(SafetyExpression):
    """Constant value in safety specifications."""
    value: Any = None
    type_name: str = ""
    
    def accept(self, visitor):
        return visitor.visit_constant(self)


@dataclass
class BinaryOperation(SafetyExpression):
    """Binary operation between two expressions."""
    left: SafetyExpression = None
    operator: Union[LogicalOperator, str] = None
    right: SafetyExpression = None
    
    def accept(self, visitor):
        return visitor.visit_binary_op(self)


@dataclass
class UnaryOperation(SafetyExpression):
    """Unary operation on an expression."""
    operator: Union[LogicalOperator, str] = None
    operand: SafetyExpression = None
    
    def accept(self, visitor):
        return visitor.visit_unary_op(self)


@dataclass
class QuantifiedExpression(SafetyExpression):
    """Quantified expression (forall, exists)."""
    quantifier: LogicalOperator = None  # FORALL or EXISTS
    variables: List[Variable] = field(default_factory=list)
    domain_constraints: List[SafetyExpression] = field(default_factory=list)
    body: SafetyExpression = None
    
    def accept(self, visitor):
        return visitor.visit_quantified(self)


# Temporal Logic Expressions

@dataclass
class TemporalExpression(SafetyExpression):
    """Temporal logic expression for time-dependent properties."""
    operator: TemporalOperator = None
    operand: SafetyExpression = None
    time_bound: Optional[int] = None  # For bounded temporal operators
    
    def accept(self, visitor):
        return visitor.visit_temporal(self)


@dataclass
class BinaryTemporalExpression(SafetyExpression):
    """Binary temporal expression (Until, Release)."""
    left: SafetyExpression = None
    operator: TemporalOperator = None
    right: SafetyExpression = None
    time_bound: Optional[int] = None
    
    def accept(self, visitor):
        return visitor.visit_binary_temporal(self)


# Safety-Specific Constructs

@dataclass
class SafetyInvariant(SafetyNode):
    """Safety invariant that must always hold."""
    name: str = ""
    condition: SafetyExpression = None
    priority: int = 1  # Higher numbers = higher priority
    enforcement_level: str = "CRITICAL"  # CRITICAL, HIGH, MEDIUM, LOW
    
    def accept(self, visitor):
        return visitor.visit_invariant(self)


@dataclass
class ValueAlignmentSpec(SafetyNode):
    """Value alignment specification."""
    name: str = ""
    value_function: SafetyExpression = None
    preservation_condition: SafetyExpression = None
    alignment_metric: SafetyExpression = None
    tolerance: float = 0.01
    
    def accept(self, visitor):
        return visitor.visit_value_alignment(self)


@dataclass
class GoalPreservationSpec(SafetyNode):
    """Goal preservation specification."""
    name: str = ""
    goal_definition: SafetyExpression = None
    stability_condition: SafetyExpression = None
    modification_constraints: List[SafetyExpression] = field(default_factory=list)
    convergence_proof: Optional[SafetyExpression] = None
    
    def accept(self, visitor):
        return visitor.visit_goal_preservation(self)


@dataclass
class CorrigibilitySpec(SafetyNode):
    """Corrigibility specification for safe modification."""
    name: str = ""
    modification_acceptance: SafetyExpression = None
    shutdown_compliance: SafetyExpression = None
    goal_modification_bounds: SafetyExpression = None
    human_override_conditions: List[SafetyExpression] = field(default_factory=list)
    
    def accept(self, visitor):
        return visitor.visit_corrigibility(self)


@dataclass
class ImpactBound(SafetyNode):
    """Impact limitation bounds for optimization."""
    name: str = ""
    impact_metric: SafetyExpression = None
    upper_bound: SafetyExpression = None
    measurement_function: SafetyExpression = None
    violation_response: SafetyExpression = None
    
    def accept(self, visitor):
        return visitor.visit_impact_bound(self)


@dataclass
class MesaOptimizationGuard(SafetyNode):
    """Mesa-optimization safety guard."""
    name: str = ""
    detection_condition: SafetyExpression = None
    prevention_mechanism: SafetyExpression = None
    monitoring_invariants: List[SafetyExpression] = field(default_factory=list)
    intervention_threshold: SafetyExpression = None
    
    def accept(self, visitor):
        return visitor.visit_mesa_guard(self)


# System State and Transitions

@dataclass
class SystemState(SafetyNode):
    """System state representation."""
    name: str = ""
    variables: Dict[str, Variable] = field(default_factory=dict)
    invariants: List[SafetyInvariant] = field(default_factory=list)
    
    def accept(self, visitor):
        return visitor.visit_system_state(self)


@dataclass
class StateTransition(SafetyNode):
    """State transition specification."""
    name: str = ""
    precondition: SafetyExpression = None
    postcondition: SafetyExpression = None
    action: SafetyExpression = None
    safety_constraints: List[SafetyExpression] = field(default_factory=list)
    
    def accept(self, visitor):
        return visitor.visit_transition(self)


@dataclass
class SafetyProperty(SafetyNode):
    """Complete safety property specification."""
    name: str = ""
    property_type: SafetyPropertyType = None
    specification: SafetyExpression = None
    verification_method: str = "MODEL_CHECKING"
    proof_obligations: List[SafetyExpression] = field(default_factory=list)
    
    def accept(self, visitor):
        return visitor.visit_safety_property(self)


# Top-level Specification

@dataclass
class SafetySpecification(SafetyNode):
    """Complete AGI safety specification document."""
    name: str = ""
    version: str = ""
    target_system: str = ""
    
    # Core safety components
    invariants: List[SafetyInvariant] = field(default_factory=list)
    value_alignments: List[ValueAlignmentSpec] = field(default_factory=list)
    goal_preservations: List[GoalPreservationSpec] = field(default_factory=list)
    corrigibility_specs: List[CorrigibilitySpec] = field(default_factory=list)
    impact_bounds: List[ImpactBound] = field(default_factory=list)
    mesa_guards: List[MesaOptimizationGuard] = field(default_factory=list)
    
    # System model
    system_states: List[SystemState] = field(default_factory=list)
    transitions: List[StateTransition] = field(default_factory=list)
    safety_properties: List[SafetyProperty] = field(default_factory=list)
    
    # Verification configuration
    verification_config: Dict[str, Any] = field(default_factory=dict)
    
    def accept(self, visitor):
        return visitor.visit_specification(self)
    
    def add_invariant(self, invariant: SafetyInvariant) -> None:
        """Add a safety invariant to the specification."""
        self.invariants.append(invariant)
    
    def add_value_alignment(self, alignment: ValueAlignmentSpec) -> None:
        """Add a value alignment specification."""
        self.value_alignments.append(alignment)
    
    def add_goal_preservation(self, preservation: GoalPreservationSpec) -> None:
        """Add a goal preservation specification."""
        self.goal_preservations.append(preservation)
    
    def get_all_safety_nodes(self) -> List[SafetyNode]:
        """Get all safety nodes in the specification."""
        nodes = []
        nodes.extend(self.invariants)
        nodes.extend(self.value_alignments)
        nodes.extend(self.goal_preservations)
        nodes.extend(self.corrigibility_specs)
        nodes.extend(self.impact_bounds)
        nodes.extend(self.mesa_guards)
        nodes.extend(self.system_states)
        nodes.extend(self.transitions)
        nodes.extend(self.safety_properties)
        return nodes


# Visitor Pattern Interface

class SafetyVisitor(ABC):
    """Abstract visitor for traversing safety AST."""
    
    @abstractmethod
    def visit_specification(self, node: SafetySpecification):
        pass
    
    @abstractmethod
    def visit_variable(self, node: Variable):
        pass
    
    @abstractmethod
    def visit_constant(self, node: Constant):
        pass
    
    @abstractmethod
    def visit_binary_op(self, node: BinaryOperation):
        pass
    
    @abstractmethod
    def visit_unary_op(self, node: UnaryOperation):
        pass
    
    @abstractmethod
    def visit_quantified(self, node: QuantifiedExpression):
        pass
    
    @abstractmethod
    def visit_temporal(self, node: TemporalExpression):
        pass
    
    @abstractmethod
    def visit_binary_temporal(self, node: BinaryTemporalExpression):
        pass
    
    @abstractmethod
    def visit_invariant(self, node: SafetyInvariant):
        pass
    
    @abstractmethod
    def visit_value_alignment(self, node: ValueAlignmentSpec):
        pass
    
    @abstractmethod
    def visit_goal_preservation(self, node: GoalPreservationSpec):
        pass
    
    @abstractmethod
    def visit_corrigibility(self, node: CorrigibilitySpec):
        pass
    
    @abstractmethod
    def visit_impact_bound(self, node: ImpactBound):
        pass
    
    @abstractmethod
    def visit_mesa_guard(self, node: MesaOptimizationGuard):
        pass
    
    @abstractmethod
    def visit_system_state(self, node: SystemState):
        pass
    
    @abstractmethod
    def visit_transition(self, node: StateTransition):
        pass
    
    @abstractmethod
    def visit_safety_property(self, node: SafetyProperty):
        pass