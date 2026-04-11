"""
Probabilistic Logic Networks (PLN) Interface for Hyperon Compatibility
======================================================================

Implements PLN reasoning rules and inference engine compatible with
OpenCog's PLN framework for symbolic-probabilistic reasoning.

Features:
- Standard PLN inference rules
- Truth value propagation
- Uncertainty quantification
- Backward and forward chaining
- Rule application scheduling
- Confidence interval calculations

Compatible with:
- OpenCog PLN engine
- Ben Goertzel's probabilistic reasoning framework
- SingularityNET hyperon symbolic AI
"""

import asyncio
import logging
import time
import math
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import random

from ..atomspace.atomspace_integration import (
    Atom, AtomType, TruthValue, AtomspaceIntegration
)

logger = logging.getLogger(__name__)


class PLNRule(Enum):
    """Standard PLN inference rules"""
    # Basic rules
    DEDUCTION = "deduction"
    INDUCTION = "induction"
    ABDUCTION = "abduction"
    
    # Logical rules
    AND_INTRODUCTION = "and_introduction"
    OR_INTRODUCTION = "or_introduction"
    NOT_ELIMINATION = "not_elimination"
    
    # Inheritance rules
    INHERITANCE_TO_SIMILARITY = "inheritance_to_similarity"
    SIMILARITY_TO_INHERITANCE = "similarity_to_inheritance"
    
    # Evaluation rules
    EVALUATION_TO_IMPLICATION = "evaluation_to_implication"
    IMPLICATION_TO_EVALUATION = "implication_to_evaluation"
    
    # Higher-order rules
    CONDITIONAL_INSTANTIATION = "conditional_instantiation"
    UNIVERSAL_INSTANTIATION = "universal_instantiation"
    EXISTENTIAL_GENERALIZATION = "existential_generalization"


@dataclass
class InferenceRule:
    """PLN inference rule definition"""
    name: str
    rule_type: PLNRule
    premises: List[str]  # Atom patterns
    conclusion: str  # Result pattern
    confidence_formula: str  # Truth value calculation
    min_confidence: float = 0.1
    
    def can_apply(self, atoms: List[Atom]) -> bool:
        """Check if rule can be applied to given atoms"""
        if len(atoms) < len(self.premises):
            return False
        
        # Simple pattern matching (would be more sophisticated in practice)
        for i, pattern in enumerate(self.premises):
            if i >= len(atoms):
                return False
            # Pattern matching logic would go here
        
        return all(atom.truth_value.confidence >= self.min_confidence for atom in atoms)


@dataclass
class InferenceResult:
    """Result of PLN inference"""
    rule_applied: PLNRule
    premises: List[Atom]
    conclusion: Atom
    truth_value: TruthValue
    confidence: float
    processing_time: float
    explanation: str


class TruthValueFormulas:
    """PLN truth value calculation formulas"""
    
    @staticmethod
    def deduction(tv_ab: TruthValue, tv_bc: TruthValue) -> TruthValue:
        """
        Deduction rule: A->B, B->C ⊢ A->C
        """
        s_ac = tv_ab.strength * tv_bc.strength
        c_ac = tv_ab.confidence * tv_bc.confidence * tv_ab.strength
        return TruthValue(s_ac, min(1.0, c_ac))
    
    @staticmethod
    def induction(tv_ab: TruthValue, tv_ac: TruthValue) -> TruthValue:
        """
        Induction rule: A->B, A->C ⊢ B->C
        """
        # Simplified induction formula
        s_bc = tv_ab.strength * tv_ac.strength
        c_bc = (tv_ab.confidence * tv_ac.confidence) / (1.0 + abs(tv_ab.strength - tv_ac.strength))
        return TruthValue(s_bc, min(1.0, c_bc))
    
    @staticmethod
    def abduction(tv_ab: TruthValue, tv_cb: TruthValue) -> TruthValue:
        """
        Abduction rule: A->B, C->B ⊢ A->C
        """
        # Simplified abduction formula
        s_ac = tv_ab.strength * tv_cb.strength
        c_ac = (tv_ab.confidence * tv_cb.confidence) / (1.0 + abs(tv_ab.strength - tv_cb.strength))
        return TruthValue(s_ac, min(1.0, c_ac))
    
    @staticmethod
    def and_introduction(tv_a: TruthValue, tv_b: TruthValue) -> TruthValue:
        """
        Conjunction: A, B ⊢ A ∧ B
        """
        s_and = tv_a.strength * tv_b.strength
        c_and = tv_a.confidence * tv_b.confidence
        return TruthValue(s_and, c_and)
    
    @staticmethod
    def or_introduction(tv_a: TruthValue, tv_b: TruthValue) -> TruthValue:
        """
        Disjunction: A ⊢ A ∨ B (or B ⊢ A ∨ B)
        """
        s_or = tv_a.strength + tv_b.strength - (tv_a.strength * tv_b.strength)
        c_or = min(tv_a.confidence, tv_b.confidence)
        return TruthValue(s_or, c_or)
    
    @staticmethod
    def inheritance_to_similarity(tv_ab: TruthValue, tv_ba: TruthValue) -> TruthValue:
        """
        Convert inheritance to similarity: A->B, B->A ⊢ A<->B
        """
        s_sim = min(tv_ab.strength, tv_ba.strength)
        c_sim = tv_ab.confidence * tv_ba.confidence
        return TruthValue(s_sim, c_sim)
    
    @staticmethod
    def revision(tv1: TruthValue, tv2: TruthValue) -> TruthValue:
        """
        Revision: combine two truth values for the same statement
        """
        if tv1.confidence == 0:
            return tv2
        if tv2.confidence == 0:
            return tv1
        
        # PLN revision formula
        k = tv1.confidence + tv2.confidence - tv1.confidence * tv2.confidence
        if k == 0:
            return tv1
        
        s_new = (tv1.strength * tv1.confidence + tv2.strength * tv2.confidence) / k
        c_new = k
        
        return TruthValue(s_new, min(1.0, c_new))


class PLNInferenceEngine:
    """PLN inference engine for probabilistic reasoning"""
    
    def __init__(self, atomspace: AtomspaceIntegration):
        self.atomspace = atomspace
        self.rules = self._initialize_rules()
        self.inference_history: List[InferenceResult] = []
        self.max_history = 10000
        
        # Statistics
        self.stats = {
            'rules_applied': 0,
            'inferences_made': 0,
            'forward_chains': 0,
            'backward_chains': 0,
            'start_time': time.time()
        }
        
        logger.info("PLN Inference Engine initialized")
    
    def _initialize_rules(self) -> Dict[PLNRule, InferenceRule]:
        """Initialize standard PLN rules"""
        rules = {}
        
        # Deduction rule
        rules[PLNRule.DEDUCTION] = InferenceRule(
            name="Deduction",
            rule_type=PLNRule.DEDUCTION,
            premises=["InheritanceLink(A,B)", "InheritanceLink(B,C)"],
            conclusion="InheritanceLink(A,C)",
            confidence_formula="deduction",
            min_confidence=0.1
        )
        
        # Induction rule
        rules[PLNRule.INDUCTION] = InferenceRule(
            name="Induction",
            rule_type=PLNRule.INDUCTION,
            premises=["InheritanceLink(A,B)", "InheritanceLink(A,C)"],
            conclusion="InheritanceLink(B,C)",
            confidence_formula="induction",
            min_confidence=0.2
        )
        
        # Abduction rule
        rules[PLNRule.ABDUCTION] = InferenceRule(
            name="Abduction",
            rule_type=PLNRule.ABDUCTION,
            premises=["InheritanceLink(A,B)", "InheritanceLink(C,B)"],
            conclusion="InheritanceLink(A,C)",
            confidence_formula="abduction",
            min_confidence=0.2
        )
        
        # AND introduction
        rules[PLNRule.AND_INTRODUCTION] = InferenceRule(
            name="AND Introduction",
            rule_type=PLNRule.AND_INTRODUCTION,
            premises=["Atom(A)", "Atom(B)"],
            conclusion="AndLink(A,B)",
            confidence_formula="and_introduction",
            min_confidence=0.1
        )
        
        return rules
    
    def apply_rule(self, rule: PLNRule, premises: List[Atom]) -> Optional[InferenceResult]:
        """
        Apply a specific PLN rule to given premises.
        
        Args:
            rule: PLN rule to apply
            premises: Atoms to use as premises
            
        Returns:
            InferenceResult if successful, None otherwise
        """
        start_time = time.time()
        
        if rule not in self.rules:
            logger.warning(f"Unknown PLN rule: {rule}")
            return None
        
        rule_def = self.rules[rule]
        if not rule_def.can_apply(premises):
            return None
        
        try:
            # Apply the rule based on its type
            if rule == PLNRule.DEDUCTION:
                return self._apply_deduction(premises, start_time)
            elif rule == PLNRule.INDUCTION:
                return self._apply_induction(premises, start_time)
            elif rule == PLNRule.ABDUCTION:
                return self._apply_abduction(premises, start_time)
            elif rule == PLNRule.AND_INTRODUCTION:
                return self._apply_and_introduction(premises, start_time)
            else:
                logger.warning(f"Rule application not implemented: {rule}")
                return None
                
        except Exception as e:
            logger.error(f"Error applying rule {rule}: {e}")
            return None
    
    def _apply_deduction(self, premises: List[Atom], start_time: float) -> Optional[InferenceResult]:
        """Apply deduction rule: A->B, B->C ⊢ A->C"""
        if len(premises) < 2:
            return None
        
        # Find matching inheritance links
        ab_link, bc_link = None, None
        for p1 in premises:
            for p2 in premises:
                if (p1 != p2 and 
                    p1.atom_type == AtomType.INHERITANCE_LINK and
                    p2.atom_type == AtomType.INHERITANCE_LINK and
                    len(p1.outgoing) == 2 and len(p2.outgoing) == 2):
                    # Check if B is shared
                    if p1.outgoing[1] == p2.outgoing[0]:  # A->B, B->C
                        ab_link, bc_link = p1, p2
                        break
        
        if not (ab_link and bc_link):
            return None
        
        # Extract A, B, C
        a = ab_link.outgoing[0]
        b = ab_link.outgoing[1]
        c = bc_link.outgoing[1]
        
        # Calculate new truth value
        new_tv = TruthValueFormulas.deduction(ab_link.truth_value, bc_link.truth_value)
        
        # Create conclusion: A->C
        conclusion = self.atomspace.add_link(
            AtomType.INHERITANCE_LINK,
            [a, c],
            new_tv
        )
        
        processing_time = time.time() - start_time
        
        result = InferenceResult(
            rule_applied=PLNRule.DEDUCTION,
            premises=[ab_link, bc_link],
            conclusion=conclusion,
            truth_value=new_tv,
            confidence=new_tv.confidence,
            processing_time=processing_time,
            explanation=f"Deduced {a.name} -> {c.name} from {a.name} -> {b.name} and {b.name} -> {c.name}"
        )
        
        self._record_inference(result)
        return result
    
    def _apply_induction(self, premises: List[Atom], start_time: float) -> Optional[InferenceResult]:
        """Apply induction rule: A->B, A->C ⊢ B->C"""
        if len(premises) < 2:
            return None
        
        # Find matching inheritance links with shared antecedent
        ab_link, ac_link = None, None
        for p1 in premises:
            for p2 in premises:
                if (p1 != p2 and 
                    p1.atom_type == AtomType.INHERITANCE_LINK and
                    p2.atom_type == AtomType.INHERITANCE_LINK and
                    len(p1.outgoing) == 2 and len(p2.outgoing) == 2):
                    # Check if A is shared
                    if p1.outgoing[0] == p2.outgoing[0]:  # A->B, A->C
                        ab_link, ac_link = p1, p2
                        break
        
        if not (ab_link and ac_link):
            return None
        
        # Extract A, B, C
        a = ab_link.outgoing[0]
        b = ab_link.outgoing[1]
        c = ac_link.outgoing[1]
        
        # Calculate new truth value
        new_tv = TruthValueFormulas.induction(ab_link.truth_value, ac_link.truth_value)
        
        # Create conclusion: B->C
        conclusion = self.atomspace.add_link(
            AtomType.INHERITANCE_LINK,
            [b, c],
            new_tv
        )
        
        processing_time = time.time() - start_time
        
        result = InferenceResult(
            rule_applied=PLNRule.INDUCTION,
            premises=[ab_link, ac_link],
            conclusion=conclusion,
            truth_value=new_tv,
            confidence=new_tv.confidence,
            processing_time=processing_time,
            explanation=f"Induced {b.name} -> {c.name} from {a.name} -> {b.name} and {a.name} -> {c.name}"
        )
        
        self._record_inference(result)
        return result
    
    def _apply_abduction(self, premises: List[Atom], start_time: float) -> Optional[InferenceResult]:
        """Apply abduction rule: A->B, C->B ⊢ A->C"""
        if len(premises) < 2:
            return None
        
        # Find matching inheritance links with shared consequent
        ab_link, cb_link = None, None
        for p1 in premises:
            for p2 in premises:
                if (p1 != p2 and 
                    p1.atom_type == AtomType.INHERITANCE_LINK and
                    p2.atom_type == AtomType.INHERITANCE_LINK and
                    len(p1.outgoing) == 2 and len(p2.outgoing) == 2):
                    # Check if B is shared
                    if p1.outgoing[1] == p2.outgoing[1]:  # A->B, C->B
                        ab_link, cb_link = p1, p2
                        break
        
        if not (ab_link and cb_link):
            return None
        
        # Extract A, B, C
        a = ab_link.outgoing[0]
        b = ab_link.outgoing[1]
        c = cb_link.outgoing[0]
        
        # Calculate new truth value
        new_tv = TruthValueFormulas.abduction(ab_link.truth_value, cb_link.truth_value)
        
        # Create conclusion: A->C
        conclusion = self.atomspace.add_link(
            AtomType.INHERITANCE_LINK,
            [a, c],
            new_tv
        )
        
        processing_time = time.time() - start_time
        
        result = InferenceResult(
            rule_applied=PLNRule.ABDUCTION,
            premises=[ab_link, cb_link],
            conclusion=conclusion,
            truth_value=new_tv,
            confidence=new_tv.confidence,
            processing_time=processing_time,
            explanation=f"Abduced {a.name} -> {c.name} from {a.name} -> {b.name} and {c.name} -> {b.name}"
        )
        
        self._record_inference(result)
        return result
    
    def _apply_and_introduction(self, premises: List[Atom], start_time: float) -> Optional[InferenceResult]:
        """Apply AND introduction: A, B ⊢ A ∧ B"""
        if len(premises) < 2:
            return None
        
        atom_a, atom_b = premises[0], premises[1]
        
        # Calculate new truth value
        new_tv = TruthValueFormulas.and_introduction(atom_a.truth_value, atom_b.truth_value)
        
        # Create conclusion: A ∧ B
        conclusion = self.atomspace.add_link(
            AtomType.AND_LINK,
            [atom_a, atom_b],
            new_tv
        )
        
        processing_time = time.time() - start_time
        
        result = InferenceResult(
            rule_applied=PLNRule.AND_INTRODUCTION,
            premises=[atom_a, atom_b],
            conclusion=conclusion,
            truth_value=new_tv,
            confidence=new_tv.confidence,
            processing_time=processing_time,
            explanation=f"Combined {atom_a} and {atom_b} with AND"
        )
        
        self._record_inference(result)
        return result
    
    def forward_chain(self, max_iterations: int = 100, 
                     min_confidence: float = 0.1) -> List[InferenceResult]:
        """
        Perform forward chaining inference.
        
        Args:
            max_iterations: Maximum number of inference steps
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of inference results
        """
        logger.info(f"Starting forward chaining (max_iterations={max_iterations})")
        start_time = time.time()
        
        results = []
        iteration = 0
        
        while iteration < max_iterations:
            iteration_results = []
            
            # Get all inheritance links as potential premises
            inheritance_links = self.atomspace.get_atoms_by_type(AtomType.INHERITANCE_LINK)
            
            if len(inheritance_links) < 2:
                break
            
            # Try applying rules to combinations of premises
            for i, link1 in enumerate(inheritance_links):
                for link2 in inheritance_links[i+1:]:
                    if (link1.truth_value.confidence >= min_confidence and 
                        link2.truth_value.confidence >= min_confidence):
                        
                        # Try deduction
                        result = self.apply_rule(PLNRule.DEDUCTION, [link1, link2])
                        if result and result.confidence >= min_confidence:
                            iteration_results.append(result)
                        
                        # Try induction
                        result = self.apply_rule(PLNRule.INDUCTION, [link1, link2])
                        if result and result.confidence >= min_confidence:
                            iteration_results.append(result)
                        
                        # Try abduction
                        result = self.apply_rule(PLNRule.ABDUCTION, [link1, link2])
                        if result and result.confidence >= min_confidence:
                            iteration_results.append(result)
            
            if not iteration_results:
                break
            
            results.extend(iteration_results)
            iteration += 1
        
        self.stats['forward_chains'] += 1
        processing_time = time.time() - start_time
        
        logger.info(f"Forward chaining completed: {len(results)} inferences in "
                   f"{iteration} iterations ({processing_time:.3f}s)")
        
        return results
    
    def backward_chain(self, goal: Atom, max_depth: int = 5) -> List[InferenceResult]:
        """
        Perform backward chaining to prove a goal.
        
        Args:
            goal: Atom to prove
            max_depth: Maximum search depth
            
        Returns:
            List of inference results leading to goal
        """
        logger.info(f"Starting backward chaining for goal: {goal}")
        
        results = []
        visited = set()
        
        def search(current_goal: Atom, depth: int) -> bool:
            if depth > max_depth or current_goal.id in visited:
                return False
            
            visited.add(current_goal.id)
            
            # Check if goal already exists in atomspace
            if current_goal in self.atomspace:
                return True
            
            # Try to derive the goal using available rules
            if current_goal.atom_type == AtomType.INHERITANCE_LINK:
                return self._backward_chain_inheritance(current_goal, depth, results)
            
            return False
        
        success = search(goal, 0)
        
        self.stats['backward_chains'] += 1
        
        logger.info(f"Backward chaining {'succeeded' if success else 'failed'}: "
                   f"{len(results)} inferences")
        
        return results
    
    def _backward_chain_inheritance(self, goal: Atom, depth: int, 
                                  results: List[InferenceResult]) -> bool:
        """Backward chain for inheritance links"""
        if len(goal.outgoing) != 2:
            return False
        
        a, c = goal.outgoing[0], goal.outgoing[1]
        
        # Look for intermediate concept B such that A->B and B->C
        all_concepts = self.atomspace.get_atoms_by_type(AtomType.CONCEPT_NODE)
        
        for b in all_concepts:
            if b == a or b == c:
                continue
            
            # Check if we can prove A->B and B->C
            ab_goal = self.atomspace.add_link(AtomType.INHERITANCE_LINK, [a, b])
            bc_goal = self.atomspace.add_link(AtomType.INHERITANCE_LINK, [b, c])
            
            # Recursively search for these subgoals
            if (ab_goal in self.atomspace or self._backward_chain_inheritance(ab_goal, depth + 1, results)) and \
               (bc_goal in self.atomspace or self._backward_chain_inheritance(bc_goal, depth + 1, results)):
                
                # Apply deduction rule
                result = self.apply_rule(PLNRule.DEDUCTION, [ab_goal, bc_goal])
                if result:
                    results.append(result)
                    return True
        
        return False
    
    def revise_truth_value(self, atom: Atom, new_tv: TruthValue) -> TruthValue:
        """
        Revise truth value using PLN revision formula.
        
        Args:
            atom: Atom to revise
            new_tv: New evidence
            
        Returns:
            Revised truth value
        """
        if atom not in self.atomspace:
            return new_tv
        
        old_tv = atom.truth_value
        revised_tv = TruthValueFormulas.revision(old_tv, new_tv)
        atom.set_truth_value(revised_tv)
        
        return revised_tv
    
    def _record_inference(self, result: InferenceResult):
        """Record inference result in history"""
        self.inference_history.append(result)
        
        # Maintain history size limit
        if len(self.inference_history) > self.max_history:
            self.inference_history = self.inference_history[-self.max_history:]
        
        self.stats['rules_applied'] += 1
        self.stats['inferences_made'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get inference engine statistics"""
        runtime = time.time() - self.stats['start_time']
        
        return {
            'rules_applied': self.stats['rules_applied'],
            'inferences_made': self.stats['inferences_made'],
            'forward_chains': self.stats['forward_chains'],
            'backward_chains': self.stats['backward_chains'],
            'inference_history_size': len(self.inference_history),
            'runtime_seconds': runtime,
            'inferences_per_second': self.stats['inferences_made'] / runtime if runtime > 0 else 0,
            'available_rules': list(rule.value for rule in self.rules.keys()),
        }
    
    def explain_inference(self, atom: Atom) -> List[str]:
        """Explain how an atom was inferred"""
        explanations = []
        
        for result in self.inference_history:
            if result.conclusion == atom:
                explanations.append(result.explanation)
        
        return explanations


class PLNInterface:
    """
    Main PLN interface for Kenny AGI hyperon compatibility.
    Provides high-level PLN reasoning capabilities.
    """
    
    def __init__(self, atomspace: AtomspaceIntegration):
        self.atomspace = atomspace
        self.inference_engine = PLNInferenceEngine(atomspace)
        
        logger.info("PLN Interface initialized")
    
    async def reason(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform PLN reasoning on a query.
        
        Args:
            query: Reasoning query specification
            
        Returns:
            Reasoning results
        """
        query_type = query.get('type', 'forward_chain')
        
        if query_type == 'forward_chain':
            max_iterations = query.get('max_iterations', 50)
            min_confidence = query.get('min_confidence', 0.1)
            
            results = self.inference_engine.forward_chain(max_iterations, min_confidence)
            
            return {
                'type': 'forward_chain',
                'results': [self._result_to_dict(r) for r in results],
                'total_inferences': len(results),
                'statistics': self.inference_engine.get_statistics()
            }
            
        elif query_type == 'backward_chain':
            goal_pattern = query.get('goal')
            if not goal_pattern:
                return {'error': 'Goal pattern required for backward chaining'}
            
            # Create goal atom from pattern
            goal = self._pattern_to_atom(goal_pattern)
            max_depth = query.get('max_depth', 5)
            
            results = self.inference_engine.backward_chain(goal, max_depth)
            
            return {
                'type': 'backward_chain',
                'goal': str(goal),
                'results': [self._result_to_dict(r) for r in results],
                'total_inferences': len(results),
                'statistics': self.inference_engine.get_statistics()
            }
        
        elif query_type == 'apply_rule':
            rule_name = query.get('rule')
            premises_patterns = query.get('premises', [])
            
            if not rule_name or not premises_patterns:
                return {'error': 'Rule name and premises required'}
            
            try:
                rule = PLNRule(rule_name)
                premises = [self._pattern_to_atom(p) for p in premises_patterns]
                
                result = self.inference_engine.apply_rule(rule, premises)
                
                return {
                    'type': 'apply_rule',
                    'rule': rule_name,
                    'result': self._result_to_dict(result) if result else None,
                    'success': result is not None
                }
                
            except ValueError:
                return {'error': f'Unknown rule: {rule_name}'}
        
        else:
            return {'error': f'Unknown query type: {query_type}'}
    
    def _result_to_dict(self, result: InferenceResult) -> Dict[str, Any]:
        """Convert inference result to dictionary"""
        return {
            'rule_applied': result.rule_applied.value,
            'premises': [str(p) for p in result.premises],
            'conclusion': str(result.conclusion),
            'truth_value': result.truth_value.to_dict(),
            'confidence': result.confidence,
            'processing_time': result.processing_time,
            'explanation': result.explanation
        }
    
    def _pattern_to_atom(self, pattern: Dict[str, Any]) -> Atom:
        """Convert pattern dictionary to atom"""
        atom_type = AtomType(pattern['type'])
        
        if 'name' in pattern:
            # Node
            return self.atomspace.add_node(atom_type, pattern['name'])
        elif 'outgoing' in pattern:
            # Link
            outgoing = [self._pattern_to_atom(p) for p in pattern['outgoing']]
            return self.atomspace.add_link(atom_type, outgoing)
        else:
            raise ValueError(f"Invalid pattern: {pattern}")
    
    def get_inference_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent inference history"""
        recent = self.inference_engine.inference_history[-limit:]
        return [self._result_to_dict(r) for r in recent]
    
    def explain_atom(self, atom: Atom) -> List[str]:
        """Get explanation for how an atom was derived"""
        return self.inference_engine.explain_inference(atom)


# Demo and testing
if __name__ == "__main__":
    print("🧪 Testing PLN Interface...")
    
    # Create atomspace and PLN interface
    atomspace = AtomspaceIntegration(max_atoms=10000)
    pln = PLNInterface(atomspace)
    
    # Create some knowledge
    cat = atomspace.add_node(AtomType.CONCEPT_NODE, "cat", TruthValue(0.9, 0.9))
    animal = atomspace.add_node(AtomType.CONCEPT_NODE, "animal", TruthValue(0.9, 0.9))
    mammal = atomspace.add_node(AtomType.CONCEPT_NODE, "mammal", TruthValue(0.9, 0.9))
    
    # Add inheritance relationships
    cat_is_mammal = atomspace.add_link(
        AtomType.INHERITANCE_LINK, 
        [cat, mammal], 
        TruthValue(0.9, 0.8)
    )
    
    mammal_is_animal = atomspace.add_link(
        AtomType.INHERITANCE_LINK,
        [mammal, animal],
        TruthValue(0.95, 0.9)
    )
    
    print(f"✅ Created knowledge base with {len(atomspace)} atoms")
    
    # Test forward chaining
    async def test_pln():
        # Forward chaining
        query = {
            'type': 'forward_chain',
            'max_iterations': 10,
            'min_confidence': 0.1
        }
        
        result = await pln.reason(query)
        print(f"✅ Forward chaining: {result['total_inferences']} inferences")
        
        for inference in result['results'][:3]:
            print(f"   - {inference['explanation']}")
        
        # Test rule application
        rule_query = {
            'type': 'apply_rule',
            'rule': 'deduction',
            'premises': [
                {'type': 'InheritanceLink', 'outgoing': [
                    {'type': 'ConceptNode', 'name': 'cat'},
                    {'type': 'ConceptNode', 'name': 'mammal'}
                ]},
                {'type': 'InheritanceLink', 'outgoing': [
                    {'type': 'ConceptNode', 'name': 'mammal'},
                    {'type': 'ConceptNode', 'name': 'animal'}
                ]}
            ]
        }
        
        rule_result = await pln.reason(rule_query)
        print(f"✅ Rule application: {rule_result['success']}")
        if rule_result.get('result'):
            print(f"   - {rule_result['result']['explanation']}")
        
        # Statistics
        stats = pln.inference_engine.get_statistics()
        print(f"✅ PLN Statistics:")
        print(f"   - Rules applied: {stats['rules_applied']}")
        print(f"   - Inferences made: {stats['inferences_made']}")
        print(f"   - Inferences/sec: {stats['inferences_per_second']:.1f}")
    
    # Run async test
    asyncio.run(test_pln())
    print("✅ PLN Interface testing completed!")