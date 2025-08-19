"""
AGI Safety Specification Language Parser

Parses the formal safety specification language into AST nodes.
Supports mathematical expressions, temporal logic, and safety-specific constructs.

Grammar supports:
- Safety invariants and constraints
- Value alignment specifications  
- Goal preservation properties
- Corrigibility requirements
- Impact limitation bounds
- Temporal logic expressions
- Quantified expressions
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from ..ast.safety_ast import *


class ParseError(Exception):
    """Exception raised during parsing."""
    def __init__(self, message: str, location: Optional[SourceLocation] = None):
        self.message = message
        self.location = location
        super().__init__(f"{message} at {location}" if location else message)


@dataclass
class Token:
    """Token in the safety specification language."""
    type: str
    value: str
    location: SourceLocation


class Lexer:
    """Lexical analyzer for the safety specification language."""
    
    TOKEN_PATTERNS = [
        # Comments
        (r'#.*', 'COMMENT'),
        
        # Keywords
        (r'\binvariant\b', 'INVARIANT'),
        (r'\bvalue_alignment\b', 'VALUE_ALIGNMENT'),
        (r'\bgoal_preservation\b', 'GOAL_PRESERVATION'),
        (r'\bcorrigibility\b', 'CORRIGIBILITY'),
        (r'\bimpact_bound\b', 'IMPACT_BOUND'),
        (r'\bmesa_guard\b', 'MESA_GUARD'),
        (r'\bstate\b', 'STATE'),
        (r'\btransition\b', 'TRANSITION'),
        (r'\bproperty\b', 'PROPERTY'),
        (r'\bforall\b', 'FORALL'),
        (r'\bexists\b', 'EXISTS'),
        (r'\balways\b', 'ALWAYS'),
        (r'\beventually\b', 'EVENTUALLY'),
        (r'\bnext\b', 'NEXT'),
        (r'\buntil\b', 'UNTIL'),
        (r'\bweakuntil\b', 'WEAKUNTIL'),
        (r'\brelease\b', 'RELEASE'),
        (r'\bif\b', 'IF'),
        (r'\bthen\b', 'THEN'),
        (r'\belse\b', 'ELSE'),
        (r'\btrue\b', 'TRUE'),
        (r'\bfalse\b', 'FALSE'),
        
        # Logical operators
        (r'∧|&&|\band\b', 'AND'),
        (r'∨|\|\||\bor\b', 'OR'),
        (r'¬|!|\bnot\b', 'NOT'),
        (r'→|->|\bimplies\b', 'IMPLIES'),
        (r'↔|<->|\biff\b', 'IFF'),
        (r'∀|\bforall\b', 'FORALL_SYMBOL'),
        (r'∃|\bexists\b', 'EXISTS_SYMBOL'),
        
        # Temporal operators
        (r'\bG\b|\balways\b', 'GLOBALLY'),
        (r'\bF\b|\beventually\b', 'FINALLY'),
        (r'\bX\b|\bnext\b', 'NEXT_OP'),
        (r'\bU\b|\buntil\b', 'UNTIL_OP'),
        (r'\bW\b|\bweakuntil\b', 'WEAKUNTIL_OP'),
        (r'\bR\b|\brelease\b', 'RELEASE_OP'),
        
        # Comparison operators
        (r'<=', 'LEQ'),
        (r'>=', 'GEQ'),
        (r'==', 'EQ'),
        (r'!=', 'NEQ'),
        (r'<', 'LT'),
        (r'>', 'GT'),
        
        # Arithmetic operators
        (r'\+', 'PLUS'),
        (r'-', 'MINUS'),
        (r'\*', 'MULTIPLY'),
        (r'/', 'DIVIDE'),
        (r'\^', 'POWER'),
        (r'%', 'MODULO'),
        
        # Delimiters
        (r'\(', 'LPAREN'),
        (r'\)', 'RPAREN'),
        (r'\[', 'LBRACKET'),
        (r'\]', 'RBRACKET'),
        (r'\{', 'LBRACE'),
        (r'\}', 'RBRACE'),
        (r';', 'SEMICOLON'),
        (r':', 'COLON'),
        (r',', 'COMMA'),
        (r'\.', 'DOT'),
        (r'=', 'ASSIGN'),
        
        # Literals
        (r'\d+\.\d+', 'FLOAT'),
        (r'\d+', 'INTEGER'),
        (r'"[^"]*"', 'STRING'),
        (r"'[^']*'", 'STRING'),
        
        # Identifiers
        (r'[a-zA-Z_][a-zA-Z0-9_]*', 'IDENTIFIER'),
        
        # Whitespace
        (r'\s+', 'WHITESPACE'),
        
        # Newlines
        (r'\n', 'NEWLINE'),
    ]
    
    def __init__(self, text: str, filename: str = "<input>"):
        self.text = text
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        
    def tokenize(self) -> List[Token]:
        """Tokenize the input text."""
        while self.pos < len(self.text):
            matched = False
            
            for pattern, token_type in self.TOKEN_PATTERNS:
                regex = re.compile(pattern)
                match = regex.match(self.text, self.pos)
                
                if match:
                    value = match.group(0)
                    location = SourceLocation(self.filename, self.line, self.column)
                    
                    # Skip whitespace and comments
                    if token_type not in ['WHITESPACE', 'COMMENT']:
                        token = Token(token_type, value, location)
                        self.tokens.append(token)
                    
                    # Update position
                    self.pos = match.end()
                    if token_type == 'NEWLINE':
                        self.line += 1
                        self.column = 1
                    else:
                        self.column += len(value)
                    
                    matched = True
                    break
            
            if not matched:
                location = SourceLocation(self.filename, self.line, self.column)
                raise ParseError(f"Unexpected character: '{self.text[self.pos]}'", location)
        
        # Add EOF token
        location = SourceLocation(self.filename, self.line, self.column)
        self.tokens.append(Token('EOF', '', location))
        
        return self.tokens


class SafetySpecificationParser:
    """Parser for the AGI Safety Specification Language."""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current_token = tokens[0] if tokens else None
        
    def parse(self) -> SafetySpecification:
        """Parse the tokens into a safety specification AST."""
        return self.parse_specification()
    
    def current(self) -> Optional[Token]:
        """Get the current token."""
        return self.current_token
    
    def advance(self) -> None:
        """Advance to the next token."""
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
            self.current_token = self.tokens[self.pos]
    
    def expect(self, token_type: str) -> Token:
        """Expect a specific token type."""
        if self.current_token is None or self.current_token.type != token_type:
            expected = token_type
            actual = self.current_token.type if self.current_token else "EOF"
            raise ParseError(f"Expected {expected}, got {actual}", 
                           self.current_token.location if self.current_token else None)
        
        token = self.current_token
        self.advance()
        return token
    
    def match(self, token_type: str) -> bool:
        """Check if current token matches type."""
        return self.current_token is not None and self.current_token.type == token_type
    
    def parse_specification(self) -> SafetySpecification:
        """Parse a complete safety specification."""
        name = "AGI_Safety_Spec"
        version = "1.0"
        target_system = "Generic_AGI"
        
        spec = SafetySpecification(
            name=name,
            version=version,
            target_system=target_system
        )
        
        while self.current_token and self.current_token.type != 'EOF':
            if self.match('INVARIANT'):
                spec.add_invariant(self.parse_invariant())
            elif self.match('VALUE_ALIGNMENT'):
                spec.add_value_alignment(self.parse_value_alignment())
            elif self.match('GOAL_PRESERVATION'):
                spec.add_goal_preservation(self.parse_goal_preservation())
            elif self.match('CORRIGIBILITY'):
                spec.corrigibility_specs.append(self.parse_corrigibility())
            elif self.match('IMPACT_BOUND'):
                spec.impact_bounds.append(self.parse_impact_bound())
            elif self.match('MESA_GUARD'):
                spec.mesa_guards.append(self.parse_mesa_guard())
            elif self.match('STATE'):
                spec.system_states.append(self.parse_state())
            elif self.match('TRANSITION'):
                spec.transitions.append(self.parse_transition())
            elif self.match('PROPERTY'):
                spec.safety_properties.append(self.parse_property())
            else:
                self.advance()  # Skip unknown tokens
        
        return spec
    
    def parse_invariant(self) -> SafetyInvariant:
        """Parse a safety invariant."""
        self.expect('INVARIANT')
        name_token = self.expect('IDENTIFIER')
        self.expect('COLON')
        condition = self.parse_expression()
        
        return SafetyInvariant(
            name=name_token.value,
            condition=condition,
            location=name_token.location
        )
    
    def parse_value_alignment(self) -> ValueAlignmentSpec:
        """Parse a value alignment specification."""
        self.expect('VALUE_ALIGNMENT')
        name_token = self.expect('IDENTIFIER')
        self.expect('LBRACE')
        
        # Parse components
        value_function = None
        preservation_condition = None
        alignment_metric = None
        tolerance = 0.01
        
        while not self.match('RBRACE') and self.current_token:
            if self.match('IDENTIFIER'):
                field_name = self.current_token.value
                self.advance()
                self.expect('COLON')
                
                if field_name == "value_function":
                    value_function = self.parse_expression()
                elif field_name == "preservation":
                    preservation_condition = self.parse_expression()
                elif field_name == "metric":
                    alignment_metric = self.parse_expression()
                elif field_name == "tolerance":
                    if self.match('FLOAT'):
                        tolerance = float(self.current_token.value)
                        self.advance()
                
                if self.match('COMMA'):
                    self.advance()
        
        self.expect('RBRACE')
        
        return ValueAlignmentSpec(
            name=name_token.value,
            value_function=value_function or Variable("default_value"),
            preservation_condition=preservation_condition or Variable("default_preservation"),
            alignment_metric=alignment_metric or Variable("default_metric"),
            tolerance=tolerance,
            location=name_token.location
        )
    
    def parse_goal_preservation(self) -> GoalPreservationSpec:
        """Parse a goal preservation specification."""
        self.expect('GOAL_PRESERVATION')
        name_token = self.expect('IDENTIFIER')
        self.expect('LBRACE')
        
        goal_definition = Variable("default_goal")
        stability_condition = Variable("stable")
        modification_constraints = []
        
        while not self.match('RBRACE') and self.current_token:
            if self.match('IDENTIFIER'):
                field_name = self.current_token.value
                self.advance()
                self.expect('COLON')
                
                if field_name == "goal":
                    goal_definition = self.parse_expression()
                elif field_name == "stability":
                    stability_condition = self.parse_expression()
                elif field_name == "constraints":
                    modification_constraints.append(self.parse_expression())
                
                if self.match('COMMA'):
                    self.advance()
        
        self.expect('RBRACE')
        
        return GoalPreservationSpec(
            name=name_token.value,
            goal_definition=goal_definition,
            stability_condition=stability_condition,
            modification_constraints=modification_constraints,
            location=name_token.location
        )
    
    def parse_corrigibility(self) -> CorrigibilitySpec:
        """Parse a corrigibility specification."""
        self.expect('CORRIGIBILITY')
        name_token = self.expect('IDENTIFIER')
        self.expect('COLON')
        
        modification_acceptance = self.parse_expression()
        
        return CorrigibilitySpec(
            name=name_token.value,
            modification_acceptance=modification_acceptance,
            shutdown_compliance=Variable("shutdown_ok"),
            goal_modification_bounds=Variable("modification_bounds"),
            human_override_conditions=[],
            location=name_token.location
        )
    
    def parse_impact_bound(self) -> ImpactBound:
        """Parse an impact bound specification."""
        self.expect('IMPACT_BOUND')
        name_token = self.expect('IDENTIFIER')
        self.expect('COLON')
        
        impact_metric = self.parse_expression()
        
        return ImpactBound(
            name=name_token.value,
            impact_metric=impact_metric,
            upper_bound=Variable("max_impact"),
            measurement_function=Variable("measure_impact"),
            violation_response=Variable("limit_impact"),
            location=name_token.location
        )
    
    def parse_mesa_guard(self) -> MesaOptimizationGuard:
        """Parse a mesa-optimization guard."""
        self.expect('MESA_GUARD')
        name_token = self.expect('IDENTIFIER')
        self.expect('COLON')
        
        detection_condition = self.parse_expression()
        
        return MesaOptimizationGuard(
            name=name_token.value,
            detection_condition=detection_condition,
            prevention_mechanism=Variable("prevent_mesa"),
            monitoring_invariants=[],
            intervention_threshold=Variable("mesa_threshold"),
            location=name_token.location
        )
    
    def parse_state(self) -> SystemState:
        """Parse a system state."""
        self.expect('STATE')
        name_token = self.expect('IDENTIFIER')
        
        return SystemState(
            name=name_token.value,
            variables={},
            invariants=[],
            location=name_token.location
        )
    
    def parse_transition(self) -> StateTransition:
        """Parse a state transition."""
        self.expect('TRANSITION')
        name_token = self.expect('IDENTIFIER')
        
        return StateTransition(
            name=name_token.value,
            precondition=Variable("pre"),
            postcondition=Variable("post"),
            action=Variable("action"),
            safety_constraints=[],
            location=name_token.location
        )
    
    def parse_property(self) -> SafetyProperty:
        """Parse a safety property."""
        self.expect('PROPERTY')
        name_token = self.expect('IDENTIFIER')
        self.expect('COLON')
        
        specification = self.parse_expression()
        
        return SafetyProperty(
            name=name_token.value,
            property_type=SafetyPropertyType.INVARIANT,
            specification=specification,
            location=name_token.location
        )
    
    def parse_expression(self) -> SafetyExpression:
        """Parse a safety expression."""
        return self.parse_logical_or()
    
    def parse_logical_or(self) -> SafetyExpression:
        """Parse logical OR expression."""
        expr = self.parse_logical_and()
        
        while self.match('OR'):
            op_token = self.current_token
            self.advance()
            right = self.parse_logical_and()
            expr = BinaryOperation(expr, LogicalOperator.OR, right)
            expr.location = op_token.location
        
        return expr
    
    def parse_logical_and(self) -> SafetyExpression:
        """Parse logical AND expression."""
        expr = self.parse_equality()
        
        while self.match('AND'):
            op_token = self.current_token
            self.advance()
            right = self.parse_equality()
            expr = BinaryOperation(expr, LogicalOperator.AND, right)
            expr.location = op_token.location
        
        return expr
    
    def parse_equality(self) -> SafetyExpression:
        """Parse equality expressions."""
        expr = self.parse_comparison()
        
        while self.match('EQ') or self.match('NEQ'):
            op_token = self.current_token
            op = "==" if op_token.type == 'EQ' else "!="
            self.advance()
            right = self.parse_comparison()
            expr = BinaryOperation(expr, op, right)
            expr.location = op_token.location
        
        return expr
    
    def parse_comparison(self) -> SafetyExpression:
        """Parse comparison expressions."""
        expr = self.parse_arithmetic()
        
        while self.current_token and self.current_token.type in ['LT', 'GT', 'LEQ', 'GEQ']:
            op_token = self.current_token
            op_map = {'LT': '<', 'GT': '>', 'LEQ': '<=', 'GEQ': '>='}
            op = op_map[op_token.type]
            self.advance()
            right = self.parse_arithmetic()
            expr = BinaryOperation(expr, op, right)
            expr.location = op_token.location
        
        return expr
    
    def parse_arithmetic(self) -> SafetyExpression:
        """Parse arithmetic expressions."""
        expr = self.parse_term()
        
        while self.match('PLUS') or self.match('MINUS'):
            op_token = self.current_token
            op = "+" if op_token.type == 'PLUS' else "-"
            self.advance()
            right = self.parse_term()
            expr = BinaryOperation(expr, op, right)
            expr.location = op_token.location
        
        return expr
    
    def parse_term(self) -> SafetyExpression:
        """Parse multiplication/division terms."""
        expr = self.parse_factor()
        
        while self.match('MULTIPLY') or self.match('DIVIDE') or self.match('MODULO'):
            op_token = self.current_token
            op_map = {'MULTIPLY': '*', 'DIVIDE': '/', 'MODULO': '%'}
            op = op_map[op_token.type]
            self.advance()
            right = self.parse_factor()
            expr = BinaryOperation(expr, op, right)
            expr.location = op_token.location
        
        return expr
    
    def parse_factor(self) -> SafetyExpression:
        """Parse factor expressions (unary, parentheses, literals)."""
        if self.match('NOT'):
            op_token = self.current_token
            self.advance()
            operand = self.parse_factor()
            expr = UnaryOperation(LogicalOperator.NOT, operand)
            expr.location = op_token.location
            return expr
        
        if self.match('MINUS'):
            op_token = self.current_token
            self.advance()
            operand = self.parse_factor()
            expr = UnaryOperation("-", operand)
            expr.location = op_token.location
            return expr
        
        if self.match('GLOBALLY'):
            return self.parse_temporal_expression()
        
        if self.match('FINALLY'):
            return self.parse_temporal_expression()
        
        if self.match('NEXT_OP'):
            return self.parse_temporal_expression()
        
        if self.match('LPAREN'):
            self.advance()
            expr = self.parse_expression()
            self.expect('RPAREN')
            return expr
        
        if self.match('IDENTIFIER'):
            name_token = self.current_token
            self.advance()
            return Variable(name_token.value, location=name_token.location)
        
        if self.match('INTEGER'):
            value_token = self.current_token
            self.advance()
            return Constant(int(value_token.value), "Integer", location=value_token.location)
        
        if self.match('FLOAT'):
            value_token = self.current_token
            self.advance()
            return Constant(float(value_token.value), "Float", location=value_token.location)
        
        if self.match('STRING'):
            value_token = self.current_token
            self.advance()
            # Remove quotes
            string_value = value_token.value[1:-1]
            return Constant(string_value, "String", location=value_token.location)
        
        if self.match('TRUE'):
            value_token = self.current_token
            self.advance()
            return Constant(True, "Boolean", location=value_token.location)
        
        if self.match('FALSE'):
            value_token = self.current_token
            self.advance()
            return Constant(False, "Boolean", location=value_token.location)
        
        if self.current_token:
            raise ParseError(f"Unexpected token: {self.current_token.type}", self.current_token.location)
        else:
            raise ParseError("Unexpected end of input")
    
    def parse_temporal_expression(self) -> TemporalExpression:
        """Parse temporal logic expressions."""
        op_token = self.current_token
        
        if op_token.type == 'GLOBALLY':
            operator = TemporalOperator.ALWAYS
        elif op_token.type == 'FINALLY':
            operator = TemporalOperator.EVENTUALLY
        elif op_token.type == 'NEXT_OP':
            operator = TemporalOperator.NEXT
        else:
            raise ParseError(f"Unknown temporal operator: {op_token.type}", op_token.location)
        
        self.advance()
        operand = self.parse_factor()
        
        expr = TemporalExpression(operator, operand)
        expr.location = op_token.location
        return expr


def parse_safety_specification(text: str, filename: str = "<input>") -> SafetySpecification:
    """Parse AGI safety specification from text."""
    lexer = Lexer(text, filename)
    tokens = lexer.tokenize()
    parser = SafetySpecificationParser(tokens)
    return parser.parse()