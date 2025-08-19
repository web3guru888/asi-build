"""
Type Checker for AGI Safety Specification Language

Provides semantic analysis and type checking for safety specifications.
Ensures mathematical rigor and catches specification errors early.

Type system includes:
- Basic types (Boolean, Real, Integer, String)
- Safety-specific types (Goal, Value, State, Action)
- Temporal types for time-dependent properties
- Quantified types for logical expressions
"""

from typing import Dict, List, Optional, Set, Union, Any
from dataclasses import dataclass
from enum import Enum

from ..ast.safety_ast import *


class TypeKind(Enum):
    """Kind of types in the safety specification language."""
    BASIC = "basic"           # Boolean, Real, Integer, String
    SAFETY = "safety"         # Goal, Value, State, Action
    TEMPORAL = "temporal"     # Time-dependent types
    FUNCTION = "function"     # Function types
    QUANTIFIED = "quantified" # Universally/existentially quantified


@dataclass
class SafetyType:
    """Type information for safety expressions."""
    kind: TypeKind
    name: str
    parameters: List['SafetyType'] = None
    constraints: List[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.constraints is None:
            self.constraints = []
    
    def is_compatible(self, other: 'SafetyType') -> bool:
        """Check if this type is compatible with another."""
        if self.name == other.name:
            return True
        
        # Basic type compatibility
        if self.kind == TypeKind.BASIC and other.kind == TypeKind.BASIC:
            # Allow numeric conversions
            numeric_types = {"Integer", "Real", "Float"}
            if self.name in numeric_types and other.name in numeric_types:
                return True
        
        # Temporal type compatibility
        if self.kind == TypeKind.TEMPORAL and other.kind == TypeKind.TEMPORAL:
            return True
        
        return False
    
    def __str__(self) -> str:
        if self.parameters:
            params = ", ".join(str(p) for p in self.parameters)
            return f"{self.name}({params})"
        return self.name


class TypeEnvironment:
    """Type environment for variable bindings."""
    
    def __init__(self, parent: Optional['TypeEnvironment'] = None):
        self.parent = parent
        self.bindings: Dict[str, SafetyType] = {}
    
    def bind(self, name: str, type_info: SafetyType) -> None:
        """Bind a variable to a type."""
        self.bindings[name] = type_info
    
    def lookup(self, name: str) -> Optional[SafetyType]:
        """Look up the type of a variable."""
        if name in self.bindings:
            return self.bindings[name]
        elif self.parent:
            return self.parent.lookup(name)
        return None
    
    def extend(self) -> 'TypeEnvironment':
        """Create a new environment extending this one."""
        return TypeEnvironment(self)


class TypeCheckError(Exception):
    """Exception raised during type checking."""
    def __init__(self, message: str, node: SafetyNode):
        self.message = message
        self.node = node
        self.location = node.location
        super().__init__(f"{message} at {self.location}")


class SafetyTypeChecker(SafetyVisitor):
    """Type checker for AGI safety specifications."""
    
    # Built-in types
    BOOLEAN_TYPE = SafetyType(TypeKind.BASIC, "Boolean")
    INTEGER_TYPE = SafetyType(TypeKind.BASIC, "Integer")
    REAL_TYPE = SafetyType(TypeKind.BASIC, "Real")
    STRING_TYPE = SafetyType(TypeKind.BASIC, "String")
    
    # Safety-specific types
    GOAL_TYPE = SafetyType(TypeKind.SAFETY, "Goal")
    VALUE_TYPE = SafetyType(TypeKind.SAFETY, "Value")
    STATE_TYPE = SafetyType(TypeKind.SAFETY, "State")
    ACTION_TYPE = SafetyType(TypeKind.SAFETY, "Action")
    IMPACT_TYPE = SafetyType(TypeKind.SAFETY, "Impact")
    
    # Temporal types
    TEMPORAL_BOOL_TYPE = SafetyType(TypeKind.TEMPORAL, "TemporalBoolean")
    
    def __init__(self):
        self.env = TypeEnvironment()
        self.errors: List[TypeCheckError] = []
        self._init_builtin_environment()
    
    def _init_builtin_environment(self):
        """Initialize the type environment with built-in functions and constants."""
        # Built-in constants
        self.env.bind("true", self.BOOLEAN_TYPE)
        self.env.bind("false", self.BOOLEAN_TYPE)
        
        # Built-in functions for safety properties
        self.env.bind("stable", SafetyType(
            TypeKind.FUNCTION, "Function",
            [self.GOAL_TYPE], [self.BOOLEAN_TYPE]
        ))
        
        self.env.bind("aligned", SafetyType(
            TypeKind.FUNCTION, "Function",
            [self.VALUE_TYPE, self.VALUE_TYPE], [self.BOOLEAN_TYPE]
        ))
        
        self.env.bind("bounded", SafetyType(
            TypeKind.FUNCTION, "Function",
            [self.IMPACT_TYPE, self.REAL_TYPE], [self.BOOLEAN_TYPE]
        ))
        
        self.env.bind("corrigible", SafetyType(
            TypeKind.FUNCTION, "Function",
            [self.STATE_TYPE], [self.BOOLEAN_TYPE]
        ))
    
    def check_specification(self, spec: SafetySpecification) -> List[TypeCheckError]:
        """Type check a complete safety specification."""
        self.errors = []
        spec.accept(self)
        return self.errors
    
    def add_error(self, message: str, node: SafetyNode):
        """Add a type checking error."""
        error = TypeCheckError(message, node)
        self.errors.append(error)
    
    def visit_specification(self, node: SafetySpecification) -> SafetyType:
        """Type check a safety specification."""
        # Check all components
        for invariant in node.invariants:
            invariant.accept(self)
        
        for alignment in node.value_alignments:
            alignment.accept(self)
        
        for preservation in node.goal_preservations:
            preservation.accept(self)
        
        for corrigibility in node.corrigibility_specs:
            corrigibility.accept(self)
        
        for bound in node.impact_bounds:
            bound.accept(self)
        
        for guard in node.mesa_guards:
            guard.accept(self)
        
        for state in node.system_states:
            state.accept(self)
        
        for transition in node.transitions:
            transition.accept(self)
        
        for prop in node.safety_properties:
            prop.accept(self)
        
        return SafetyType(TypeKind.SAFETY, "Specification")
    
    def visit_variable(self, node: Variable) -> SafetyType:
        """Type check a variable reference."""
        var_type = self.env.lookup(node.name)
        if var_type is None:
            # Try to infer type from domain
            if node.domain:
                if node.domain == "Boolean":
                    var_type = self.BOOLEAN_TYPE
                elif node.domain == "Real":
                    var_type = self.REAL_TYPE
                elif node.domain == "Integer":
                    var_type = self.INTEGER_TYPE
                elif node.domain == "Goal":
                    var_type = self.GOAL_TYPE
                elif node.domain == "Value":
                    var_type = self.VALUE_TYPE
                elif node.domain == "State":
                    var_type = self.STATE_TYPE
                else:
                    var_type = SafetyType(TypeKind.BASIC, node.domain)
                
                self.env.bind(node.name, var_type)
            else:
                self.add_error(f"Undefined variable: {node.name}", node)
                return SafetyType(TypeKind.BASIC, "Error")
        
        return var_type
    
    def visit_constant(self, node: Constant) -> SafetyType:
        """Type check a constant."""
        if node.type_name == "Boolean":
            return self.BOOLEAN_TYPE
        elif node.type_name == "Integer":
            return self.INTEGER_TYPE
        elif node.type_name in ["Real", "Float"]:
            return self.REAL_TYPE
        elif node.type_name == "String":
            return self.STRING_TYPE
        else:
            return SafetyType(TypeKind.BASIC, node.type_name)
    
    def visit_binary_op(self, node: BinaryOperation) -> SafetyType:
        """Type check a binary operation."""
        left_type = node.left.accept(self)
        right_type = node.right.accept(self)
        
        # Logical operators
        if node.operator in [LogicalOperator.AND, LogicalOperator.OR]:
            if left_type.name != "Boolean" or right_type.name != "Boolean":
                self.add_error(f"Logical operator {node.operator} requires Boolean operands", node)
            return self.BOOLEAN_TYPE
        
        elif node.operator == LogicalOperator.IMPLIES:
            if left_type.name != "Boolean" or right_type.name != "Boolean":
                self.add_error(f"Implication requires Boolean operands", node)
            return self.BOOLEAN_TYPE
        
        elif node.operator == LogicalOperator.IFF:
            if left_type.name != "Boolean" or right_type.name != "Boolean":
                self.add_error(f"Biconditional requires Boolean operands", node)
            return self.BOOLEAN_TYPE
        
        # Comparison operators
        elif node.operator in ["<", ">", "<=", ">=", "==", "!="]:
            if not left_type.is_compatible(right_type):
                self.add_error(f"Incompatible types for comparison: {left_type} and {right_type}", node)
            return self.BOOLEAN_TYPE
        
        # Arithmetic operators
        elif node.operator in ["+", "-", "*", "/", "%"]:
            if left_type.name not in ["Integer", "Real"] or right_type.name not in ["Integer", "Real"]:
                self.add_error(f"Arithmetic operator {node.operator} requires numeric operands", node)
            
            # Return most general numeric type
            if left_type.name == "Real" or right_type.name == "Real":
                return self.REAL_TYPE
            else:
                return self.INTEGER_TYPE
        
        else:
            self.add_error(f"Unknown binary operator: {node.operator}", node)
            return SafetyType(TypeKind.BASIC, "Error")
    
    def visit_unary_op(self, node: UnaryOperation) -> SafetyType:
        """Type check a unary operation."""
        operand_type = node.operand.accept(self)
        
        if node.operator == LogicalOperator.NOT:
            if operand_type.name != "Boolean":
                self.add_error(f"Logical NOT requires Boolean operand", node)
            return self.BOOLEAN_TYPE
        
        elif node.operator == "-":
            if operand_type.name not in ["Integer", "Real"]:
                self.add_error(f"Unary minus requires numeric operand", node)
            return operand_type
        
        else:
            self.add_error(f"Unknown unary operator: {node.operator}", node)
            return SafetyType(TypeKind.BASIC, "Error")
    
    def visit_quantified(self, node: QuantifiedExpression) -> SafetyType:
        """Type check a quantified expression."""
        # Create new environment for quantified variables
        old_env = self.env
        self.env = self.env.extend()
        
        try:
            # Bind quantified variables
            for var in node.variables:
                var_type = var.accept(self)
                self.env.bind(var.name, var_type)
            
            # Check domain constraints
            for constraint in node.domain_constraints:
                constraint_type = constraint.accept(self)
                if constraint_type.name != "Boolean":
                    self.add_error(f"Domain constraint must be Boolean", constraint)
            
            # Check body
            body_type = node.body.accept(self)
            if body_type.name != "Boolean":
                self.add_error(f"Quantified expression body must be Boolean", node.body)
            
            return self.BOOLEAN_TYPE
        
        finally:
            self.env = old_env
    
    def visit_temporal(self, node: TemporalExpression) -> SafetyType:
        """Type check a temporal expression."""
        operand_type = node.operand.accept(self)
        
        if operand_type.name != "Boolean":
            self.add_error(f"Temporal operator {node.operator} requires Boolean operand", node)
        
        return self.TEMPORAL_BOOL_TYPE
    
    def visit_binary_temporal(self, node: BinaryTemporalExpression) -> SafetyType:
        """Type check a binary temporal expression."""
        left_type = node.left.accept(self)
        right_type = node.right.accept(self)
        
        if left_type.name != "Boolean" or right_type.name != "Boolean":
            self.add_error(f"Binary temporal operator {node.operator} requires Boolean operands", node)
        
        return self.TEMPORAL_BOOL_TYPE
    
    def visit_invariant(self, node: SafetyInvariant) -> SafetyType:
        """Type check a safety invariant."""
        condition_type = node.condition.accept(self)
        
        if condition_type.name not in ["Boolean", "TemporalBoolean"]:
            self.add_error(f"Safety invariant condition must be Boolean", node.condition)
        
        return SafetyType(TypeKind.SAFETY, "Invariant")
    
    def visit_value_alignment(self, node: ValueAlignmentSpec) -> SafetyType:
        """Type check a value alignment specification."""
        value_func_type = node.value_function.accept(self)
        preservation_type = node.preservation_condition.accept(self)
        metric_type = node.alignment_metric.accept(self)
        
        # Value function should return a Value type
        if value_func_type.name not in ["Value", "Real"]:
            self.add_error(f"Value function should return Value or Real type", node.value_function)
        
        # Preservation condition should be Boolean
        if preservation_type.name != "Boolean":
            self.add_error(f"Preservation condition must be Boolean", node.preservation_condition)
        
        # Alignment metric should be numeric
        if metric_type.name not in ["Real", "Integer"]:
            self.add_error(f"Alignment metric must be numeric", node.alignment_metric)
        
        return SafetyType(TypeKind.SAFETY, "ValueAlignment")
    
    def visit_goal_preservation(self, node: GoalPreservationSpec) -> SafetyType:
        """Type check a goal preservation specification."""
        goal_type = node.goal_definition.accept(self)
        stability_type = node.stability_condition.accept(self)
        
        if goal_type.name != "Goal":
            self.add_error(f"Goal definition must have Goal type", node.goal_definition)
        
        if stability_type.name != "Boolean":
            self.add_error(f"Stability condition must be Boolean", node.stability_condition)
        
        for constraint in node.modification_constraints:
            constraint_type = constraint.accept(self)
            if constraint_type.name != "Boolean":
                self.add_error(f"Modification constraint must be Boolean", constraint)
        
        return SafetyType(TypeKind.SAFETY, "GoalPreservation")
    
    def visit_corrigibility(self, node: CorrigibilitySpec) -> SafetyType:
        """Type check a corrigibility specification."""
        acceptance_type = node.modification_acceptance.accept(self)
        shutdown_type = node.shutdown_compliance.accept(self)
        bounds_type = node.goal_modification_bounds.accept(self)
        
        if acceptance_type.name != "Boolean":
            self.add_error(f"Modification acceptance must be Boolean", node.modification_acceptance)
        
        if shutdown_type.name != "Boolean":
            self.add_error(f"Shutdown compliance must be Boolean", node.shutdown_compliance)
        
        return SafetyType(TypeKind.SAFETY, "Corrigibility")
    
    def visit_impact_bound(self, node: ImpactBound) -> SafetyType:
        """Type check an impact bound specification."""
        metric_type = node.impact_metric.accept(self)
        bound_type = node.upper_bound.accept(self)
        measure_type = node.measurement_function.accept(self)
        
        if metric_type.name not in ["Impact", "Real"]:
            self.add_error(f"Impact metric must be Impact or Real type", node.impact_metric)
        
        if bound_type.name not in ["Real", "Integer"]:
            self.add_error(f"Upper bound must be numeric", node.upper_bound)
        
        return SafetyType(TypeKind.SAFETY, "ImpactBound")
    
    def visit_mesa_guard(self, node: MesaOptimizationGuard) -> SafetyType:
        """Type check a mesa-optimization guard."""
        detection_type = node.detection_condition.accept(self)
        prevention_type = node.prevention_mechanism.accept(self)
        threshold_type = node.intervention_threshold.accept(self)
        
        if detection_type.name != "Boolean":
            self.add_error(f"Detection condition must be Boolean", node.detection_condition)
        
        for invariant in node.monitoring_invariants:
            invariant_type = invariant.accept(self)
            if invariant_type.name != "Boolean":
                self.add_error(f"Monitoring invariant must be Boolean", invariant)
        
        return SafetyType(TypeKind.SAFETY, "MesaGuard")
    
    def visit_system_state(self, node: SystemState) -> SafetyType:
        """Type check a system state."""
        for var in node.variables.values():
            var.accept(self)
        
        for invariant in node.invariants:
            invariant.accept(self)
        
        return self.STATE_TYPE
    
    def visit_transition(self, node: StateTransition) -> SafetyType:
        """Type check a state transition."""
        pre_type = node.precondition.accept(self)
        post_type = node.postcondition.accept(self)
        action_type = node.action.accept(self)
        
        if pre_type.name != "Boolean":
            self.add_error(f"Precondition must be Boolean", node.precondition)
        
        if post_type.name != "Boolean":
            self.add_error(f"Postcondition must be Boolean", node.postcondition)
        
        for constraint in node.safety_constraints:
            constraint_type = constraint.accept(self)
            if constraint_type.name != "Boolean":
                self.add_error(f"Safety constraint must be Boolean", constraint)
        
        return SafetyType(TypeKind.SAFETY, "Transition")
    
    def visit_safety_property(self, node: SafetyProperty) -> SafetyType:
        """Type check a safety property."""
        spec_type = node.specification.accept(self)
        
        if spec_type.name not in ["Boolean", "TemporalBoolean"]:
            self.add_error(f"Safety property specification must be Boolean", node.specification)
        
        for obligation in node.proof_obligations:
            obligation_type = obligation.accept(self)
            if obligation_type.name != "Boolean":
                self.add_error(f"Proof obligation must be Boolean", obligation)
        
        return SafetyType(TypeKind.SAFETY, "Property")


def type_check_safety_specification(spec: SafetySpecification) -> List[TypeCheckError]:
    """Type check a safety specification and return any errors."""
    checker = SafetyTypeChecker()
    return checker.check_specification(spec)