"""
MeTTa Verifier

Comprehensive verification system for MeTTa code used in Hyperon AGI systems.
Validates syntax, semantics, type safety, and execution correctness.
"""

import re
import ast
import json
import asyncio
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import tempfile

from ..core.config import PlatformConfig
from ..core.exceptions import *


@dataclass
class MeTTaExpression:
    """Parsed MeTTa expression."""
    expression_type: str  # 'atom', 'application', 'lambda', 'match', etc.
    content: str
    line_number: int
    tokens: List[str]
    children: List['MeTTaExpression']
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.expression_type,
            'content': self.content,
            'line_number': self.line_number,
            'tokens': self.tokens,
            'children': [child.to_dict() for child in self.children]
        }


@dataclass
class MeTTaValidationIssue:
    """MeTTa validation issue."""
    severity: str  # 'error', 'warning', 'info'
    message: str
    line_number: Optional[int]
    column: Optional[int]
    code: str
    suggestion: Optional[str]


@dataclass
class MeTTaVerificationResult:
    """Result of MeTTa verification."""
    is_valid: bool
    score: float
    syntax_valid: bool
    semantic_issues: List[MeTTaValidationIssue]
    type_issues: List[MeTTaValidationIssue]
    execution_issues: List[MeTTaValidationIssue]
    performance_metrics: Dict[str, Any]
    suggestions: List[str]
    details: Dict[str, Any]
    timestamp: datetime


class MeTTaVerifier:
    """
    Comprehensive MeTTa code verification system.
    
    Features:
    - Syntax validation and parsing
    - Semantic analysis and type checking
    - Pattern matching validation
    - Lambda expression verification
    - Atom space interaction validation
    - Performance analysis
    - Style and best practice checking
    - Integration with Hyperon interpreter
    - Automated test generation
    - Code completion suggestions
    """
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.metta_interpreter = config.metta_interpreter
        self.builtin_functions = set()
        self.builtin_types = set()
        
    async def initialize(self) -> None:
        """Initialize the MeTTa verifier."""
        await self._load_builtin_functions()
        await self._load_builtin_types()
        await self._verify_interpreter_availability()
    
    async def _load_builtin_functions(self) -> None:
        """Load built-in MeTTa functions."""
        self.builtin_functions = {
            # Core functions
            'match', 'if', 'case', 'let', 'lambda', 'quote', 'unquote',
            # Arithmetic
            '+', '-', '*', '/', 'mod', 'abs', 'min', 'max',
            # Comparison
            '=', '!=', '<', '>', '<=', '>=', 'eq', 'neq',
            # Logic
            'and', 'or', 'not', 'xor',
            # List operations
            'cons', 'car', 'cdr', 'nil', 'list', 'length', 'append',
            # Type operations
            'type', 'typeof', 'is-type',
            # Atom space operations
            'add-atom', 'remove-atom', 'get-atoms', 'query',
            # String operations
            'concat', 'substring', 'string-length',
            # Conversion
            'str', 'num', 'bool'
        }
    
    async def _load_builtin_types(self) -> None:
        """Load built-in MeTTa types."""
        self.builtin_types = {
            # Basic types
            'Atom', 'Symbol', 'Number', 'String', 'Bool',
            # Collection types
            'List', 'Set', 'Dict',
            # Special types
            'Type', 'Variable', 'Expression',
            # Grounded types
            'Grounded', 'GroundedAtom',
            # Space types
            'Space', 'AtomSpace'
        }
    
    async def _verify_interpreter_availability(self) -> None:
        """Verify MeTTa interpreter is available."""
        if not self.metta_interpreter:
            return  # Skip if no interpreter configured
        
        try:
            result = await asyncio.create_subprocess_exec(
                self.metta_interpreter, '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise MeTTaError(f"MeTTa interpreter not working: {stderr.decode()}")
        
        except FileNotFoundError:
            raise MeTTaError(f"MeTTa interpreter not found: {self.metta_interpreter}")
    
    async def verify_code(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify MeTTa code in an experiment.
        
        Args:
            experiment: Experiment data containing MeTTa code
            
        Returns:
            Comprehensive verification results
        """
        verification_start = datetime.now(timezone.utc)
        
        # Extract MeTTa code from experiment
        metta_code = self._extract_metta_code(experiment)
        
        if not metta_code:
            return {
                'timestamp': verification_start.isoformat(),
                'overall_score': 0.0,
                'valid': False,
                'error': 'No MeTTa code found in experiment'
            }
        
        # Perform comprehensive verification
        verification_result = await self._verify_metta_code(metta_code)
        
        verification_end = datetime.now(timezone.utc)
        
        return {
            'timestamp': verification_start.isoformat(),
            'verification_duration': (verification_end - verification_start).total_seconds(),
            'overall_score': verification_result.score,
            'valid': verification_result.is_valid,
            'syntax_valid': verification_result.syntax_valid,
            'issues': {
                'semantic': [issue.__dict__ for issue in verification_result.semantic_issues],
                'type': [issue.__dict__ for issue in verification_result.type_issues],
                'execution': [issue.__dict__ for issue in verification_result.execution_issues]
            },
            'performance_metrics': verification_result.performance_metrics,
            'suggestions': verification_result.suggestions,
            'details': verification_result.details
        }
    
    def _extract_metta_code(self, experiment: Dict[str, Any]) -> Optional[str]:
        """Extract MeTTa code from experiment."""
        # Look for MeTTa code in various locations
        if 'metta_code' in experiment:
            return experiment['metta_code']
        
        if 'code' in experiment:
            code = experiment['code']
            if isinstance(code, str):
                # Check if it looks like MeTTa code
                if self._is_metta_code(code):
                    return code
            elif isinstance(code, dict):
                # Look for .metta files
                for filename, content in code.items():
                    if filename.endswith('.metta') or filename.endswith('.metta-lang'):
                        return content
        
        if 'files' in experiment:
            files = experiment['files']
            for filename, content in files.items():
                if filename.endswith('.metta') or filename.endswith('.metta-lang'):
                    return content
        
        return None
    
    def _is_metta_code(self, code: str) -> bool:
        """Heuristic to determine if code is MeTTa."""
        metta_indicators = [
            '(match ', '(let ', '(lambda ', '(case ', '(if ',
            '(add-atom ', '(get-atoms ', '(query ',
            '(: ', '(-> ', '(= ',
            'AtomSpace', 'Atom', 'Symbol'
        ]
        
        return any(indicator in code for indicator in metta_indicators)
    
    async def _verify_metta_code(self, metta_code: str) -> MeTTaVerificationResult:
        """Perform comprehensive MeTTa code verification."""
        # Parse the code
        parsed_expressions = await self._parse_metta_code(metta_code)
        
        # Syntax validation
        syntax_issues = await self._validate_syntax(metta_code, parsed_expressions)
        syntax_valid = len([issue for issue in syntax_issues if issue.severity == 'error']) == 0
        
        # Semantic analysis
        semantic_issues = await self._analyze_semantics(parsed_expressions)
        
        # Type checking
        type_issues = await self._check_types(parsed_expressions)
        
        # Execution verification
        execution_issues = []
        performance_metrics = {}
        if self.metta_interpreter and syntax_valid:
            execution_issues, performance_metrics = await self._verify_execution(metta_code)
        
        # Generate suggestions
        suggestions = await self._generate_suggestions(
            syntax_issues, semantic_issues, type_issues, execution_issues
        )
        
        # Calculate overall score
        all_issues = syntax_issues + semantic_issues + type_issues + execution_issues
        error_count = len([issue for issue in all_issues if issue.severity == 'error'])
        warning_count = len([issue for issue in all_issues if issue.severity == 'warning'])
        
        score = max(0.0, 1.0 - (error_count * 0.2) - (warning_count * 0.1))
        is_valid = error_count == 0
        
        return MeTTaVerificationResult(
            is_valid=is_valid,
            score=score,
            syntax_valid=syntax_valid,
            semantic_issues=semantic_issues,
            type_issues=type_issues,
            execution_issues=execution_issues,
            performance_metrics=performance_metrics,
            suggestions=suggestions,
            details={
                'total_expressions': len(parsed_expressions),
                'total_issues': len(all_issues),
                'error_count': error_count,
                'warning_count': warning_count
            },
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _parse_metta_code(self, code: str) -> List[MeTTaExpression]:
        """Parse MeTTa code into structured expressions."""
        expressions = []
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith(';'):  # Skip empty lines and comments
                continue
            
            try:
                parsed_expr = self._parse_expression(line, line_num)
                if parsed_expr:
                    expressions.append(parsed_expr)
            except Exception as e:
                # Create an error expression
                error_expr = MeTTaExpression(
                    expression_type='error',
                    content=line,
                    line_number=line_num,
                    tokens=[],
                    children=[]
                )
                expressions.append(error_expr)
        
        return expressions
    
    def _parse_expression(self, line: str, line_number: int) -> Optional[MeTTaExpression]:
        """Parse a single MeTTa expression."""
        if not line:
            return None
        
        # Tokenize the line
        tokens = self._tokenize(line)
        if not tokens:
            return None
        
        # Determine expression type
        expr_type = self._determine_expression_type(tokens)
        
        # Parse children (for compound expressions)
        children = []
        if line.startswith('(') and line.endswith(')'):
            # Parse nested expressions
            inner_content = line[1:-1].strip()
            if inner_content:
                nested_tokens = self._tokenize(inner_content)
                # Simple parsing - would need more sophisticated parser for real use
                children = []  # Placeholder
        
        return MeTTaExpression(
            expression_type=expr_type,
            content=line,
            line_number=line_number,
            tokens=tokens,
            children=children
        )
    
    def _tokenize(self, line: str) -> List[str]:
        """Tokenize a MeTTa expression."""
        # Simple tokenizer - would need more sophisticated implementation
        tokens = []
        current_token = ""
        in_string = False
        paren_depth = 0
        
        for char in line:
            if char == '"' and not in_string:
                in_string = True
                current_token += char
            elif char == '"' and in_string:
                in_string = False
                current_token += char
                tokens.append(current_token)
                current_token = ""
            elif in_string:
                current_token += char
            elif char in '()':
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
                tokens.append(char)
                if char == '(':
                    paren_depth += 1
                else:
                    paren_depth -= 1
            elif char.isspace():
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
            else:
                current_token += char
        
        if current_token:
            tokens.append(current_token)
        
        return tokens
    
    def _determine_expression_type(self, tokens: List[str]) -> str:
        """Determine the type of MeTTa expression."""
        if not tokens:
            return 'empty'
        
        if tokens[0] == '(':
            if len(tokens) > 1:
                second_token = tokens[1]
                if second_token in ['match', 'case']:
                    return 'pattern_match'
                elif second_token in ['let', 'lambda']:
                    return 'binding'
                elif second_token in ['if']:
                    return 'conditional'
                elif second_token in [':', '->', '=>']:
                    return 'type_annotation'
                elif second_token in ['=']:
                    return 'definition'
                elif second_token in self.builtin_functions:
                    return 'function_call'
                else:
                    return 'application'
            return 'expression'
        
        # Simple atoms
        if tokens[0].startswith('"') and tokens[0].endswith('"'):
            return 'string_literal'
        elif tokens[0].isdigit() or (tokens[0].startswith('-') and tokens[0][1:].isdigit()):
            return 'number_literal'
        elif tokens[0] in ['true', 'false']:
            return 'boolean_literal'
        elif tokens[0] in self.builtin_types:
            return 'type_reference'
        else:
            return 'symbol'
    
    async def _validate_syntax(self, code: str, expressions: List[MeTTaExpression]) -> List[MeTTaValidationIssue]:
        """Validate MeTTa syntax."""
        issues = []
        
        # Check parentheses balancing
        paren_balance = 0
        for line_num, line in enumerate(code.split('\n'), 1):
            for char_pos, char in enumerate(line):
                if char == '(':
                    paren_balance += 1
                elif char == ')':
                    paren_balance -= 1
                    if paren_balance < 0:
                        issues.append(MeTTaValidationIssue(
                            severity='error',
                            message='Unmatched closing parenthesis',
                            line_number=line_num,
                            column=char_pos + 1,
                            code='SYNTAX_UNMATCHED_PAREN',
                            suggestion='Remove extra closing parenthesis or add opening parenthesis'
                        ))
                        paren_balance = 0
        
        if paren_balance > 0:
            issues.append(MeTTaValidationIssue(
                severity='error',
                message=f'{paren_balance} unmatched opening parenthesis(es)',
                line_number=None,
                column=None,
                code='SYNTAX_UNMATCHED_PAREN',
                suggestion='Add missing closing parentheses'
            ))
        
        # Check for malformed expressions
        for expr in expressions:
            if expr.expression_type == 'error':
                issues.append(MeTTaValidationIssue(
                    severity='error',
                    message='Malformed expression',
                    line_number=expr.line_number,
                    column=None,
                    code='SYNTAX_MALFORMED',
                    suggestion='Check expression syntax'
                ))
        
        return issues
    
    async def _analyze_semantics(self, expressions: List[MeTTaExpression]) -> List[MeTTaValidationIssue]:
        """Analyze semantic correctness of MeTTa code."""
        issues = []
        defined_symbols = set(self.builtin_functions)
        
        for expr in expressions:
            # Check for undefined symbols
            if expr.expression_type == 'symbol' and expr.tokens:
                symbol_name = expr.tokens[0]
                if symbol_name not in defined_symbols and not symbol_name.startswith('$'):
                    issues.append(MeTTaValidationIssue(
                        severity='warning',
                        message=f'Undefined symbol: {symbol_name}',
                        line_number=expr.line_number,
                        column=None,
                        code='SEMANTIC_UNDEFINED_SYMBOL',
                        suggestion=f'Define {symbol_name} or check spelling'
                    ))
            
            # Track symbol definitions
            if expr.expression_type == 'definition' and len(expr.tokens) >= 3:
                if expr.tokens[1] == '=' and len(expr.tokens) >= 3:
                    symbol_name = expr.tokens[2]
                    defined_symbols.add(symbol_name)
            
            # Check pattern matching correctness
            if expr.expression_type == 'pattern_match':
                match_issues = self._validate_pattern_match(expr)
                issues.extend(match_issues)
            
            # Check lambda expressions
            if expr.expression_type == 'binding' and expr.tokens and expr.tokens[1] == 'lambda':
                lambda_issues = self._validate_lambda_expression(expr)
                issues.extend(lambda_issues)
        
        return issues
    
    def _validate_pattern_match(self, expr: MeTTaExpression) -> List[MeTTaValidationIssue]:
        """Validate pattern matching expressions."""
        issues = []
        
        # Basic pattern match structure validation
        tokens = expr.tokens
        if len(tokens) < 4:  # (match expr pattern result)
            issues.append(MeTTaValidationIssue(
                severity='error',
                message='Incomplete match expression',
                line_number=expr.line_number,
                column=None,
                code='SEMANTIC_INCOMPLETE_MATCH',
                suggestion='Match requires: (match expression pattern result)'
            ))
        
        return issues
    
    def _validate_lambda_expression(self, expr: MeTTaExpression) -> List[MeTTaValidationIssue]:
        """Validate lambda expressions."""
        issues = []
        
        # Basic lambda structure validation
        tokens = expr.tokens
        if len(tokens) < 4:  # (lambda (params) body)
            issues.append(MeTTaValidationIssue(
                severity='error',
                message='Incomplete lambda expression',
                line_number=expr.line_number,
                column=None,
                code='SEMANTIC_INCOMPLETE_LAMBDA',
                suggestion='Lambda requires: (lambda (parameters) body)'
            ))
        
        return issues
    
    async def _check_types(self, expressions: List[MeTTaExpression]) -> List[MeTTaValidationIssue]:
        """Perform type checking on MeTTa expressions."""
        issues = []
        type_context = {}
        
        for expr in expressions:
            # Type annotation validation
            if expr.expression_type == 'type_annotation':
                type_issues = self._validate_type_annotation(expr, type_context)
                issues.extend(type_issues)
            
            # Function call type checking
            if expr.expression_type == 'function_call':
                call_issues = self._check_function_call_types(expr, type_context)
                issues.extend(call_issues)
        
        return issues
    
    def _validate_type_annotation(self, expr: MeTTaExpression, type_context: Dict[str, str]) -> List[MeTTaValidationIssue]:
        """Validate type annotations."""
        issues = []
        
        tokens = expr.tokens
        if len(tokens) >= 4 and tokens[1] == ':':
            symbol_name = tokens[2] if tokens[2] != '(' else 'anonymous'
            type_name = tokens[3]
            
            # Check if type exists
            if type_name not in self.builtin_types and type_name not in type_context:
                issues.append(MeTTaValidationIssue(
                    severity='warning',
                    message=f'Unknown type: {type_name}',
                    line_number=expr.line_number,
                    column=None,
                    code='TYPE_UNKNOWN_TYPE',
                    suggestion=f'Define type {type_name} or check spelling'
                ))
            
            # Add to type context
            if symbol_name != 'anonymous':
                type_context[symbol_name] = type_name
        
        return issues
    
    def _check_function_call_types(self, expr: MeTTaExpression, type_context: Dict[str, str]) -> List[MeTTaValidationIssue]:
        """Check types in function calls."""
        issues = []
        
        # Basic type checking for built-in functions
        if len(expr.tokens) >= 2:
            func_name = expr.tokens[1]
            
            # Arithmetic functions require numbers
            if func_name in ['+', '-', '*', '/', 'mod'] and len(expr.tokens) >= 4:
                for i in range(2, len(expr.tokens)):
                    token = expr.tokens[i]
                    if token not in [')', '('] and not token.isdigit():
                        if token in type_context and type_context[token] != 'Number':
                            issues.append(MeTTaValidationIssue(
                                severity='warning',
                                message=f'Type mismatch: {func_name} expects Number, got {type_context[token]}',
                                line_number=expr.line_number,
                                column=None,
                                code='TYPE_MISMATCH',
                                suggestion=f'Ensure {token} is a Number'
                            ))
        
        return issues
    
    async def _verify_execution(self, metta_code: str) -> Tuple[List[MeTTaValidationIssue], Dict[str, Any]]:
        """Verify code execution using MeTTa interpreter."""
        issues = []
        metrics = {}
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.metta', delete=False) as f:
                f.write(metta_code)
                temp_file = f.name
            
            # Execute with interpreter
            start_time = datetime.now()
            result = await asyncio.create_subprocess_exec(
                self.metta_interpreter, temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            end_time = datetime.now()
            
            # Clean up
            Path(temp_file).unlink()
            
            # Process results
            execution_time = (end_time - start_time).total_seconds()
            metrics['execution_time_seconds'] = execution_time
            metrics['return_code'] = result.returncode
            metrics['stdout_length'] = len(stdout.decode())
            metrics['stderr_length'] = len(stderr.decode())
            
            if result.returncode != 0:
                error_message = stderr.decode().strip()
                issues.append(MeTTaValidationIssue(
                    severity='error',
                    message=f'Execution failed: {error_message}',
                    line_number=None,
                    column=None,
                    code='EXECUTION_FAILED',
                    suggestion='Fix syntax or semantic errors'
                ))
            
            # Parse output for runtime errors
            output = stdout.decode()
            if 'Error' in output or 'Exception' in output:
                issues.append(MeTTaValidationIssue(
                    severity='error',
                    message='Runtime error detected in output',
                    line_number=None,
                    column=None,
                    code='EXECUTION_RUNTIME_ERROR',
                    suggestion='Check code logic and error handling'
                ))
        
        except Exception as e:
            issues.append(MeTTaValidationIssue(
                severity='error',
                message=f'Execution verification failed: {str(e)}',
                line_number=None,
                column=None,
                code='EXECUTION_VERIFICATION_FAILED',
                suggestion='Check MeTTa interpreter configuration'
            ))
        
        return issues, metrics
    
    async def _generate_suggestions(self, syntax_issues: List[MeTTaValidationIssue],
                                  semantic_issues: List[MeTTaValidationIssue],
                                  type_issues: List[MeTTaValidationIssue],
                                  execution_issues: List[MeTTaValidationIssue]) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        # Collect suggestions from issues
        all_issues = syntax_issues + semantic_issues + type_issues + execution_issues
        for issue in all_issues:
            if issue.suggestion:
                suggestions.append(issue.suggestion)
        
        # General suggestions based on issue patterns
        error_count = len([i for i in all_issues if i.severity == 'error'])
        if error_count > 5:
            suggestions.append('Consider breaking down complex expressions into smaller, testable parts')
        
        type_issue_count = len(type_issues)
        if type_issue_count > 0:
            suggestions.append('Add explicit type annotations to improve code clarity and catch type errors early')
        
        return list(set(suggestions))  # Remove duplicates
    
    async def generate_test_cases(self, metta_code: str) -> List[Dict[str, Any]]:
        """Generate test cases for MeTTa code."""
        test_cases = []
        
        # Parse code to identify testable functions
        expressions = await self._parse_metta_code(metta_code)
        
        for expr in expressions:
            if expr.expression_type == 'definition':
                # Generate test case for function definition
                test_case = {
                    'name': f'test_{expr.tokens[2] if len(expr.tokens) > 2 else "function"}',
                    'input': '()',  # Placeholder
                    'expected_output': 'success',
                    'description': f'Test for {expr.content}'
                }
                test_cases.append(test_case)
        
        return test_cases
    
    async def suggest_optimizations(self, metta_code: str) -> List[Dict[str, str]]:
        """Suggest code optimizations."""
        suggestions = []
        
        expressions = await self._parse_metta_code(metta_code)
        
        for expr in expressions:
            # Suggest tail recursion optimization
            if 'lambda' in expr.content and expr.expression_type == 'binding':
                suggestions.append({
                    'type': 'optimization',
                    'message': 'Consider using tail recursion for better performance',
                    'line': str(expr.line_number)
                })
            
            # Suggest caching for expensive computations
            if expr.expression_type == 'function_call' and any(op in expr.content for op in ['*', '/', 'match']):
                suggestions.append({
                    'type': 'performance',
                    'message': 'Consider caching results of expensive computations',
                    'line': str(expr.line_number)
                })
        
        return suggestions
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on MeTTa verifier."""
        try:
            interpreter_available = False
            if self.metta_interpreter:
                try:
                    result = await asyncio.create_subprocess_exec(
                        self.metta_interpreter, '--version',
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await result.communicate()
                    interpreter_available = result.returncode == 0
                except:
                    pass
            
            return {
                'status': 'healthy',
                'interpreter_available': interpreter_available,
                'interpreter_path': self.metta_interpreter,
                'builtin_functions_count': len(self.builtin_functions),
                'builtin_types_count': len(self.builtin_types),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }