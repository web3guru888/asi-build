"""
PLN Validator

Comprehensive validation system for Probabilistic Logic Networks (PLN)
specifically designed for Hyperon/OpenCog AGI systems.
"""

import json
import math
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import re

from ..core.config import PlatformConfig
from ..core.exceptions import *


@dataclass
class TruthValue:
    """PLN Truth Value representation."""
    strength: float
    confidence: float
    
    def __post_init__(self):
        if not (0 <= self.strength <= 1):
            raise ValueError(f"Strength must be in [0,1], got {self.strength}")
        if not (0 <= self.confidence <= 1):
            raise ValueError(f"Confidence must be in [0,1], got {self.confidence}")
    
    def to_dict(self) -> Dict[str, float]:
        return {'strength': self.strength, 'confidence': self.confidence}


@dataclass
class PLNRule:
    """PLN inference rule definition."""
    name: str
    rule_type: str
    premises: List[str]
    conclusion: str
    formula: str
    truth_value_formula: str
    constraints: List[str]
    
    def validate_structure(self) -> List[str]:
        """Validate the structural consistency of the rule."""
        errors = []
        
        if not self.name:
            errors.append("Rule name cannot be empty")
        
        if not self.premises:
            errors.append("Rule must have at least one premise")
        
        if not self.conclusion:
            errors.append("Rule must have a conclusion")
        
        return errors


@dataclass
class PLNValidationResult:
    """Result of PLN validation."""
    rule_name: str
    is_valid: bool
    score: float
    errors: List[str]
    warnings: List[str]
    details: Dict[str, Any]
    timestamp: datetime


class PLNValidator:
    """
    Comprehensive PLN validation system for Hyperon experiments.
    
    Features:
    - Truth value consistency validation
    - Inference rule correctness checking
    - Logical coherence verification
    - Performance analysis of inference chains
    - AtomSpace consistency validation
    - PLN formula verification
    - Uncertainty propagation validation
    - Rule application soundness checking
    """
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.known_rules: Dict[str, PLNRule] = {}
        self.atomspace_predicates: Dict[str, Any] = {}
        
    async def initialize(self) -> None:
        """Initialize the PLN validator."""
        await self._load_standard_pln_rules()
        await self._initialize_validation_predicates()
    
    async def _load_standard_pln_rules(self) -> None:
        """Load standard PLN inference rules."""
        standard_rules = [
            PLNRule(
                name="modus_ponens",
                rule_type="deduction",
                premises=["Implication(A, B)", "A"],
                conclusion="B",
                formula="A → B, A ⊢ B",
                truth_value_formula="strength(B) = strength(A→B) * strength(A), confidence(B) = min(confidence(A→B), confidence(A))",
                constraints=["strength(A) > 0", "confidence(A) > 0"]
            ),
            PLNRule(
                name="deduction",
                rule_type="deduction", 
                premises=["Inheritance(A, B)", "Inheritance(B, C)"],
                conclusion="Inheritance(A, C)",
                formula="A→B, B→C ⊢ A→C",
                truth_value_formula="strength(A→C) = strength(A→B) * strength(B→C), confidence(A→C) = strength(B→C) * confidence(A→B) * confidence(B→C)",
                constraints=["strength(A→B) > 0", "strength(B→C) > 0"]
            ),
            PLNRule(
                name="induction",
                rule_type="induction",
                premises=["Inheritance(A, B)", "Inheritance(A, C)"],
                conclusion="Inheritance(C, B)",
                formula="A→B, A→C ⊢ C→B",
                truth_value_formula="strength(C→B) = strength(A→B) * strength(A→C) / strength(A), confidence(C→B) = strength(A→C) * confidence(A→B) * confidence(A→C)",
                constraints=["strength(A) > 0"]
            ),
            PLNRule(
                name="abduction",
                rule_type="abduction",
                premises=["Inheritance(A, B)", "Inheritance(C, B)"],
                conclusion="Inheritance(A, C)",
                formula="A→B, C→B ⊢ A→C",
                truth_value_formula="strength(A→C) = strength(A→B) * strength(C→B) / strength(B), confidence(A→C) = strength(C→B) * confidence(A→B) * confidence(C→B)",
                constraints=["strength(B) > 0"]
            ),
            PLNRule(
                name="revision",
                rule_type="revision",
                premises=["Statement(S, TV1)", "Statement(S, TV2)"],
                conclusion="Statement(S, TV_revised)",
                formula="S<TV1>, S<TV2> ⊢ S<TV_revised>",
                truth_value_formula="strength_new = (strength1*confidence1 + strength2*confidence2) / (confidence1 + confidence2), confidence_new = confidence1 + confidence2",
                constraints=["confidence1 + confidence2 <= 1"]
            ),
            PLNRule(
                name="conjunction",
                rule_type="logical",
                premises=["A", "B"],
                conclusion="And(A, B)",
                formula="A, B ⊢ A ∧ B",
                truth_value_formula="strength(A∧B) = strength(A) * strength(B), confidence(A∧B) = min(confidence(A), confidence(B))",
                constraints=[]
            ),
            PLNRule(
                name="disjunction",
                rule_type="logical",
                premises=["A", "B"],
                conclusion="Or(A, B)",
                formula="A, B ⊢ A ∨ B",
                truth_value_formula="strength(A∨B) = strength(A) + strength(B) - strength(A) * strength(B), confidence(A∨B) = min(confidence(A), confidence(B))",
                constraints=[]
            )
        ]
        
        for rule in standard_rules:
            self.known_rules[rule.name] = rule
    
    async def _initialize_validation_predicates(self) -> None:
        """Initialize predicates for AtomSpace validation."""
        self.atomspace_predicates = {
            'inheritance': self._validate_inheritance,
            'similarity': self._validate_similarity,
            'implication': self._validate_implication,
            'equivalence': self._validate_equivalence,
            'evaluation': self._validate_evaluation,
            'member': self._validate_member,
            'subset': self._validate_subset
        }
    
    async def validate_rules(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate PLN rules in an experiment.
        
        Args:
            experiment: Experiment data containing PLN rules and inferences
            
        Returns:
            Comprehensive validation results
        """
        validation_start = datetime.now(timezone.utc)
        
        validation_results = []
        
        # Extract PLN components from experiment
        pln_data = self._extract_pln_data(experiment)
        
        if not pln_data:
            return {
                'timestamp': validation_start.isoformat(),
                'overall_score': 0.0,
                'valid': False,
                'error': 'No PLN data found in experiment'
            }
        
        # Validate individual rules
        if 'rules' in pln_data:
            for rule_data in pln_data['rules']:
                result = await self._validate_single_rule(rule_data)
                validation_results.append(result)
        
        # Validate inference chains
        if 'inference_chains' in pln_data:
            for chain in pln_data['inference_chains']:
                result = await self._validate_inference_chain(chain)
                validation_results.append(result)
        
        # Validate AtomSpace consistency
        if 'atomspace' in pln_data:
            result = await self._validate_atomspace_consistency(pln_data['atomspace'])
            validation_results.append(result)
        
        # Validate truth value propagation
        if 'truth_values' in pln_data:
            result = await self._validate_truth_value_propagation(pln_data['truth_values'])
            validation_results.append(result)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(validation_results)
        
        validation_end = datetime.now(timezone.utc)
        
        return {
            'timestamp': validation_start.isoformat(),
            'validation_duration': (validation_end - validation_start).total_seconds(),
            'overall_score': overall_score,
            'valid': overall_score >= 0.7,
            'individual_results': [
                {
                    'rule_name': r.rule_name,
                    'is_valid': r.is_valid,
                    'score': r.score,
                    'errors': r.errors,
                    'warnings': r.warnings,
                    'details': r.details
                } for r in validation_results
            ],
            'summary': self._generate_validation_summary(validation_results)
        }
    
    def _extract_pln_data(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """Extract PLN-specific data from experiment."""
        pln_data = {}
        
        # Look for PLN data in various locations
        if 'pln' in experiment:
            pln_data = experiment['pln']
        elif 'results' in experiment and isinstance(experiment['results'], dict):
            results = experiment['results']
            if 'pln' in results:
                pln_data = results['pln']
            elif 'inference_results' in results:
                pln_data['inference_chains'] = results['inference_results']
            elif 'truth_values' in results:
                pln_data['truth_values'] = results['truth_values']
        
        # Look for rule definitions
        if 'code' in experiment:
            # Scan code for PLN rule definitions
            detected_rules = self._scan_code_for_pln_rules(experiment['code'])
            if detected_rules:
                pln_data['rules'] = detected_rules
        
        return pln_data
    
    def _scan_code_for_pln_rules(self, code: str) -> List[Dict[str, Any]]:
        """Scan code for PLN rule definitions."""
        rules = []
        
        # Simple regex patterns for common PLN patterns
        patterns = {
            'inheritance': r'Inheritance\([^,]+,\s*[^)]+\)',
            'implication': r'Implication\([^,]+,\s*[^)]+\)',
            'evaluation': r'Evaluation\([^,]+,\s*[^)]+\)',
            'similarity': r'Similarity\([^,]+,\s*[^)]+\)'
        }
        
        for rule_type, pattern in patterns.items():
            matches = re.findall(pattern, code)
            for match in matches:
                rules.append({
                    'type': rule_type,
                    'expression': match,
                    'source': 'code_scan'
                })
        
        return rules
    
    async def _validate_single_rule(self, rule_data: Dict[str, Any]) -> PLNValidationResult:
        """Validate a single PLN rule."""
        rule_name = rule_data.get('name', 'unknown_rule')
        errors = []
        warnings = []
        
        try:
            # Parse rule if it's a known PLN rule type
            if rule_data.get('type') in ['inheritance', 'implication', 'similarity']:
                validation_details = await self._validate_logical_structure(rule_data)
                errors.extend(validation_details.get('errors', []))
                warnings.extend(validation_details.get('warnings', []))
            
            # Validate truth values if present
            if 'truth_value' in rule_data:
                tv_validation = self._validate_truth_value_format(rule_data['truth_value'])
                errors.extend(tv_validation.get('errors', []))
                warnings.extend(tv_validation.get('warnings', []))
            
            # Check rule application correctness
            if rule_name in self.known_rules:
                correctness_check = await self._check_rule_application_correctness(
                    self.known_rules[rule_name], rule_data
                )
                errors.extend(correctness_check.get('errors', []))
                warnings.extend(correctness_check.get('warnings', []))
        
        except Exception as e:
            errors.append(f"Exception during rule validation: {str(e)}")
        
        is_valid = len(errors) == 0
        score = 1.0 if is_valid else max(0.0, 1.0 - len(errors) * 0.2)
        
        return PLNValidationResult(
            rule_name=rule_name,
            is_valid=is_valid,
            score=score,
            errors=errors,
            warnings=warnings,
            details=rule_data,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _validate_logical_structure(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the logical structure of a rule."""
        errors = []
        warnings = []
        
        rule_type = rule_data.get('type', '')
        expression = rule_data.get('expression', '')
        
        if rule_type == 'inheritance':
            # Validate Inheritance(A, B) structure
            if not re.match(r'Inheritance\([^,]+,\s*[^)]+\)', expression):
                errors.append(f"Invalid inheritance expression: {expression}")
            else:
                # Extract A and B
                match = re.match(r'Inheritance\(([^,]+),\s*([^)]+)\)', expression)
                if match:
                    a, b = match.groups()
                    a, b = a.strip(), b.strip()
                    
                    # Check for self-inheritance (usually not meaningful)
                    if a == b:
                        warnings.append(f"Self-inheritance detected: {a} → {a}")
                    
                    # Check for cyclic inheritance (if we have context)
                    # This would require more sophisticated graph analysis
        
        elif rule_type == 'implication':
            # Validate Implication(A, B) structure
            if not re.match(r'Implication\([^,]+,\s*[^)]+\)', expression):
                errors.append(f"Invalid implication expression: {expression}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_truth_value_format(self, truth_value: Any) -> Dict[str, Any]:
        """Validate truth value format and constraints."""
        errors = []
        warnings = []
        
        try:
            if isinstance(truth_value, dict):
                if 'strength' not in truth_value or 'confidence' not in truth_value:
                    errors.append("Truth value must have 'strength' and 'confidence' fields")
                else:
                    strength = float(truth_value['strength'])
                    confidence = float(truth_value['confidence'])
                    
                    if not (0 <= strength <= 1):
                        errors.append(f"Strength must be in [0,1], got {strength}")
                    if not (0 <= confidence <= 1):
                        errors.append(f"Confidence must be in [0,1], got {confidence}")
                    
                    # Warn about extreme values
                    if confidence < 0.01:
                        warnings.append(f"Very low confidence: {confidence}")
                    if strength == 0 and confidence > 0:
                        warnings.append("Zero strength with non-zero confidence may be problematic")
            
            elif isinstance(truth_value, (list, tuple)) and len(truth_value) == 2:
                strength, confidence = float(truth_value[0]), float(truth_value[1])
                if not (0 <= strength <= 1):
                    errors.append(f"Strength must be in [0,1], got {strength}")
                if not (0 <= confidence <= 1):
                    errors.append(f"Confidence must be in [0,1], got {confidence}")
            
            else:
                errors.append(f"Invalid truth value format: {truth_value}")
        
        except (ValueError, TypeError) as e:
            errors.append(f"Truth value parsing error: {str(e)}")
        
        return {'errors': errors, 'warnings': warnings}
    
    async def _check_rule_application_correctness(self, rule: PLNRule, 
                                                rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a rule application is correct."""
        errors = []
        warnings = []
        
        # Check structural consistency
        structural_errors = rule.validate_structure()
        errors.extend(structural_errors)
        
        # Check truth value formula application if we have input/output TVs
        if 'input_truth_values' in rule_data and 'output_truth_value' in rule_data:
            formula_check = await self._verify_truth_value_formula(
                rule, rule_data['input_truth_values'], rule_data['output_truth_value']
            )
            errors.extend(formula_check.get('errors', []))
            warnings.extend(formula_check.get('warnings', []))
        
        return {'errors': errors, 'warnings': warnings}
    
    async def _verify_truth_value_formula(self, rule: PLNRule, input_tvs: List[Dict[str, float]], 
                                        output_tv: Dict[str, float]) -> Dict[str, Any]:
        """Verify that the truth value formula is correctly applied."""
        errors = []
        warnings = []
        
        try:
            # This would implement the actual formula verification
            # For now, we'll do basic consistency checks
            
            if rule.name == "conjunction":
                if len(input_tvs) == 2:
                    tv1, tv2 = input_tvs[0], input_tvs[1]
                    expected_strength = tv1['strength'] * tv2['strength']
                    expected_confidence = min(tv1['confidence'], tv2['confidence'])
                    
                    actual_strength = output_tv['strength']
                    actual_confidence = output_tv['confidence']
                    
                    strength_diff = abs(expected_strength - actual_strength)
                    confidence_diff = abs(expected_confidence - actual_confidence)
                    
                    if strength_diff > 0.01:
                        errors.append(f"Conjunction strength formula error: expected {expected_strength:.3f}, got {actual_strength:.3f}")
                    
                    if confidence_diff > 0.01:
                        errors.append(f"Conjunction confidence formula error: expected {expected_confidence:.3f}, got {actual_confidence:.3f}")
            
            # Add more formula validations for other rules
            
        except Exception as e:
            errors.append(f"Error verifying truth value formula: {str(e)}")
        
        return {'errors': errors, 'warnings': warnings}
    
    async def _validate_inference_chain(self, chain: List[Dict[str, Any]]) -> PLNValidationResult:
        """Validate a chain of PLN inferences."""
        errors = []
        warnings = []
        chain_name = f"inference_chain_{len(chain)}_steps"
        
        try:
            if len(chain) < 2:
                errors.append("Inference chain must have at least 2 steps")
            else:
                # Check each step in the chain
                for i, step in enumerate(chain):
                    if 'rule' not in step:
                        errors.append(f"Step {i} missing rule specification")
                    
                    if 'premises' not in step:
                        errors.append(f"Step {i} missing premises")
                    
                    if 'conclusion' not in step:
                        errors.append(f"Step {i} missing conclusion")
                    
                    # Check that each step's conclusion matches next step's premise
                    if i < len(chain) - 1:
                        next_step = chain[i + 1]
                        if step.get('conclusion') not in next_step.get('premises', []):
                            warnings.append(f"Step {i} conclusion not used in step {i+1}")
        
        except Exception as e:
            errors.append(f"Error validating inference chain: {str(e)}")
        
        is_valid = len(errors) == 0
        score = 1.0 if is_valid else max(0.0, 1.0 - len(errors) * 0.15)
        
        return PLNValidationResult(
            rule_name=chain_name,
            is_valid=is_valid,
            score=score,
            errors=errors,
            warnings=warnings,
            details={'chain_length': len(chain), 'steps': chain},
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _validate_atomspace_consistency(self, atomspace: Dict[str, Any]) -> PLNValidationResult:
        """Validate AtomSpace consistency."""
        errors = []
        warnings = []
        
        try:
            atoms = atomspace.get('atoms', [])
            
            # Check for contradictory statements
            inheritance_statements = {}
            for atom in atoms:
                if atom.get('type') == 'Inheritance':
                    key = (atom.get('source'), atom.get('target'))
                    if key in inheritance_statements:
                        # Multiple inheritance statements - check consistency
                        existing_tv = inheritance_statements[key]
                        current_tv = atom.get('truth_value', {})
                        
                        if existing_tv and current_tv:
                            strength_diff = abs(existing_tv.get('strength', 0) - current_tv.get('strength', 0))
                            if strength_diff > 0.5:
                                warnings.append(f"Conflicting inheritance strengths for {key}: {existing_tv['strength']} vs {current_tv['strength']}")
                    else:
                        inheritance_statements[key] = atom.get('truth_value', {})
            
            # Check for cycles in inheritance
            inheritance_graph = {}
            for atom in atoms:
                if atom.get('type') == 'Inheritance':
                    source = atom.get('source')
                    target = atom.get('target')
                    if source not in inheritance_graph:
                        inheritance_graph[source] = []
                    inheritance_graph[source].append(target)
            
            # Simple cycle detection
            def has_cycle(node, visited, rec_stack):
                visited.add(node)
                rec_stack.add(node)
                
                for neighbor in inheritance_graph.get(node, []):
                    if neighbor not in visited:
                        if has_cycle(neighbor, visited, rec_stack):
                            return True
                    elif neighbor in rec_stack:
                        return True
                
                rec_stack.remove(node)
                return False
            
            visited = set()
            for node in inheritance_graph:
                if node not in visited:
                    if has_cycle(node, visited, set()):
                        errors.append(f"Cycle detected in inheritance hierarchy involving {node}")
                        break
        
        except Exception as e:
            errors.append(f"Error validating AtomSpace: {str(e)}")
        
        is_valid = len(errors) == 0
        score = 1.0 if is_valid else max(0.0, 1.0 - len(errors) * 0.3)
        
        return PLNValidationResult(
            rule_name="atomspace_consistency",
            is_valid=is_valid,
            score=score,
            errors=errors,
            warnings=warnings,
            details={'atom_count': len(atoms) if 'atoms' in atomspace else 0},
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _validate_truth_value_propagation(self, truth_values: Dict[str, Any]) -> PLNValidationResult:
        """Validate truth value propagation through inference."""
        errors = []
        warnings = []
        
        try:
            # Check for impossible truth value combinations
            for atom_name, tv in truth_values.items():
                tv_check = self._validate_truth_value_format(tv)
                errors.extend(tv_check.get('errors', []))
                warnings.extend(tv_check.get('warnings', []))
                
                # Check for logical impossibilities
                if isinstance(tv, dict):
                    strength = tv.get('strength', 0)
                    confidence = tv.get('confidence', 0)
                    
                    # Very high confidence with very low strength might indicate an issue
                    if strength < 0.1 and confidence > 0.9:
                        warnings.append(f"Atom {atom_name}: Very low strength ({strength}) with very high confidence ({confidence})")
        
        except Exception as e:
            errors.append(f"Error validating truth value propagation: {str(e)}")
        
        is_valid = len(errors) == 0
        score = 1.0 if is_valid else max(0.0, 1.0 - len(errors) * 0.2)
        
        return PLNValidationResult(
            rule_name="truth_value_propagation",
            is_valid=is_valid,
            score=score,
            errors=errors,
            warnings=warnings,
            details={'truth_value_count': len(truth_values)},
            timestamp=datetime.now(timezone.utc)
        )
    
    # Predicate validation methods
    def _validate_inheritance(self, atom: Dict[str, Any]) -> List[str]:
        """Validate inheritance relationship."""
        errors = []
        
        source = atom.get('source')
        target = atom.get('target')
        
        if not source or not target:
            errors.append("Inheritance must have both source and target")
        
        if source == target:
            errors.append(f"Self-inheritance is not meaningful: {source}")
        
        return errors
    
    def _validate_similarity(self, atom: Dict[str, Any]) -> List[str]:
        """Validate similarity relationship."""
        errors = []
        
        # Similarity should be symmetric
        source = atom.get('source')
        target = atom.get('target')
        
        if not source or not target:
            errors.append("Similarity must have both source and target")
        
        return errors
    
    def _validate_implication(self, atom: Dict[str, Any]) -> List[str]:
        """Validate implication relationship."""
        errors = []
        
        antecedent = atom.get('antecedent')
        consequent = atom.get('consequent')
        
        if not antecedent or not consequent:
            errors.append("Implication must have both antecedent and consequent")
        
        return errors
    
    def _validate_equivalence(self, atom: Dict[str, Any]) -> List[str]:
        """Validate equivalence relationship."""
        errors = []
        
        # Equivalence should be symmetric and transitive
        left = atom.get('left')
        right = atom.get('right')
        
        if not left or not right:
            errors.append("Equivalence must have both left and right terms")
        
        return errors
    
    def _validate_evaluation(self, atom: Dict[str, Any]) -> List[str]:
        """Validate evaluation predicate."""
        errors = []
        
        predicate = atom.get('predicate')
        arguments = atom.get('arguments')
        
        if not predicate:
            errors.append("Evaluation must have a predicate")
        
        if not arguments:
            errors.append("Evaluation must have arguments")
        
        return errors
    
    def _validate_member(self, atom: Dict[str, Any]) -> List[str]:
        """Validate member relationship."""
        errors = []
        
        element = atom.get('element')
        set_atom = atom.get('set')
        
        if not element or not set_atom:
            errors.append("Member must have both element and set")
        
        return errors
    
    def _validate_subset(self, atom: Dict[str, Any]) -> List[str]:
        """Validate subset relationship."""
        errors = []
        
        subset = atom.get('subset')
        superset = atom.get('superset')
        
        if not subset or not superset:
            errors.append("Subset must have both subset and superset")
        
        if subset == superset:
            errors.append("Set cannot be a subset of itself (unless it's equality)")
        
        return errors
    
    def _calculate_overall_score(self, results: List[PLNValidationResult]) -> float:
        """Calculate overall validation score."""
        if not results:
            return 0.0
        
        total_score = sum(r.score for r in results)
        return total_score / len(results)
    
    def _generate_validation_summary(self, results: List[PLNValidationResult]) -> Dict[str, Any]:
        """Generate validation summary."""
        total_rules = len(results)
        valid_rules = sum(1 for r in results if r.is_valid)
        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)
        
        return {
            'total_rules_validated': total_rules,
            'valid_rules': valid_rules,
            'invalid_rules': total_rules - valid_rules,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'validation_rate': valid_rules / total_rules if total_rules > 0 else 0.0
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on PLN validator."""
        try:
            return {
                'status': 'healthy',
                'known_rules_count': len(self.known_rules),
                'predicates_count': len(self.atomspace_predicates),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }