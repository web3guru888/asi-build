"""
Reasoning Benchmarks for AGI Component Benchmark Suite

Implements comprehensive reasoning capability tests including:
- Deductive reasoning (syllogisms, logic)
- Inductive reasoning (pattern recognition, rule learning)
- Abductive reasoning (explanation generation, hypothesis formation)
- Analogical reasoning (abstract analogies, causal analogies)
"""

import random
import time
import itertools
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import json

from .core import BaseBenchmark, AGISystem, BenchmarkResult


@dataclass
class LogicProblem:
    """Represents a logic problem"""
    premises: List[str]
    conclusion: str
    valid: bool
    difficulty: str
    problem_type: str


@dataclass
class PatternSequence:
    """Represents a pattern sequence problem"""
    sequence: List[Any]
    next_items: List[Any]
    pattern_type: str
    difficulty: str


@dataclass
class AnalogyProblem:
    """Represents an analogy problem"""
    source: Dict[str, Any]
    target: Dict[str, Any]
    mapping: Dict[str, str]
    analogy_type: str
    difficulty: str


class ReasoningBenchmarks(BaseBenchmark):
    """Comprehensive reasoning benchmarks"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.deductive_problems = self._generate_deductive_problems()
        self.inductive_problems = self._generate_inductive_problems()
        self.abductive_problems = self._generate_abductive_problems()
        self.analogy_problems = self._generate_analogy_problems()
    
    def run_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run all reasoning tests"""
        results = []
        
        # Deductive reasoning tests
        if self.config.get("deductive_reasoning", {}).get("enabled", True):
            results.extend(self._run_deductive_tests(system))
        
        # Inductive reasoning tests
        if self.config.get("inductive_reasoning", {}).get("enabled", True):
            results.extend(self._run_inductive_tests(system))
        
        # Abductive reasoning tests
        if self.config.get("abductive_reasoning", {}).get("enabled", True):
            results.extend(self._run_abductive_tests(system))
        
        # Analogical reasoning tests
        if self.config.get("analogical_reasoning", {}).get("enabled", True):
            results.extend(self._run_analogical_tests(system))
        
        return results
    
    def _run_deductive_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run deductive reasoning tests"""
        results = []
        config = self.config.get("deductive_reasoning", {})
        
        for test_set in config.get("test_sets", ["syllogisms"]):
            for difficulty in config.get("difficulty_levels", ["basic"]):
                problems = [p for p in self.deductive_problems 
                           if p.problem_type == test_set and p.difficulty == difficulty]
                
                if problems:
                    result = self._run_single_test(
                        lambda sys: self._test_deductive_reasoning(sys, problems),
                        f"deductive_{test_set}_{difficulty}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_inductive_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run inductive reasoning tests"""
        results = []
        config = self.config.get("inductive_reasoning", {})
        
        for test_set in config.get("test_sets", ["pattern_recognition"]):
            for sample_size in config.get("sample_sizes", [10]):
                for noise_level in config.get("noise_levels", [0.0]):
                    problems = [p for p in self.inductive_problems 
                               if p.pattern_type == test_set][:sample_size]
                    
                    if problems:
                        result = self._run_single_test(
                            lambda sys: self._test_inductive_reasoning(sys, problems, noise_level),
                            f"inductive_{test_set}_n{sample_size}_noise{noise_level}",
                            system,
                            max_score=100.0
                        )
                        results.append(result)
        
        return results
    
    def _run_abductive_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run abductive reasoning tests"""
        results = []
        config = self.config.get("abductive_reasoning", {})
        
        for test_set in config.get("test_sets", ["explanation_generation"]):
            for completeness in config.get("evidence_completeness", [0.5]):
                problems = [p for p in self.abductive_problems if p["type"] == test_set]
                
                if problems:
                    result = self._run_single_test(
                        lambda sys: self._test_abductive_reasoning(sys, problems, completeness),
                        f"abductive_{test_set}_evidence{completeness}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_analogical_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run analogical reasoning tests"""
        results = []
        config = self.config.get("analogical_reasoning", {})
        
        for test_set in config.get("test_sets", ["abstract_analogies"]):
            for threshold in config.get("similarity_thresholds", [0.5]):
                problems = [p for p in self.analogy_problems 
                           if p.analogy_type == test_set]
                
                if problems:
                    result = self._run_single_test(
                        lambda sys: self._test_analogical_reasoning(sys, problems, threshold),
                        f"analogical_{test_set}_threshold{threshold}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _test_deductive_reasoning(self, system: AGISystem, problems: List[LogicProblem]) -> Dict[str, Any]:
        """Test deductive reasoning with logic problems"""
        correct = 0
        total = len(problems)
        details = {"problems_tested": total, "individual_results": []}
        
        for problem in problems:
            task = {
                "type": "deductive_reasoning",
                "premises": problem.premises,
                "conclusion": problem.conclusion,
                "question": "Is this conclusion logically valid given the premises?",
                "expected_answer": problem.valid
            }
            
            try:
                response = system.process_reasoning_task(task)
                predicted = response.get("answer", False)
                
                if isinstance(predicted, str):
                    predicted = predicted.lower() in ["true", "yes", "valid", "correct"]
                
                is_correct = bool(predicted) == problem.valid
                if is_correct:
                    correct += 1
                
                details["individual_results"].append({
                    "problem_type": problem.problem_type,
                    "difficulty": problem.difficulty,
                    "premises": problem.premises,
                    "conclusion": problem.conclusion,
                    "expected": problem.valid,
                    "predicted": predicted,
                    "correct": is_correct
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "problem_type": problem.problem_type,
                    "error": str(e)
                })
        
        accuracy = (correct / total) * 100 if total > 0 else 0
        details["accuracy"] = accuracy
        details["correct_answers"] = correct
        
        return {
            "score": accuracy,
            "success": accuracy > 0,
            "details": details
        }
    
    def _test_inductive_reasoning(self, system: AGISystem, problems: List[PatternSequence], 
                                 noise_level: float) -> Dict[str, Any]:
        """Test inductive reasoning with pattern recognition"""
        correct = 0
        total = len(problems)
        details = {"problems_tested": total, "noise_level": noise_level, "individual_results": []}
        
        for problem in problems:
            # Add noise to sequence if specified
            noisy_sequence = self._add_noise_to_sequence(problem.sequence, noise_level)
            
            task = {
                "type": "inductive_reasoning",
                "sequence": noisy_sequence,
                "question": "What comes next in this sequence?",
                "pattern_type": problem.pattern_type,
                "expected_next": problem.next_items
            }
            
            try:
                response = system.process_reasoning_task(task)
                predicted = response.get("next_items", [])
                
                # Check if prediction matches expected (allow some flexibility)
                is_correct = self._check_sequence_prediction(predicted, problem.next_items)
                if is_correct:
                    correct += 1
                
                details["individual_results"].append({
                    "pattern_type": problem.pattern_type,
                    "difficulty": problem.difficulty,
                    "sequence": noisy_sequence,
                    "expected": problem.next_items,
                    "predicted": predicted,
                    "correct": is_correct
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "pattern_type": problem.pattern_type,
                    "error": str(e)
                })
        
        accuracy = (correct / total) * 100 if total > 0 else 0
        details["accuracy"] = accuracy
        details["correct_answers"] = correct
        
        return {
            "score": accuracy,
            "success": accuracy > 0,
            "details": details
        }
    
    def _test_abductive_reasoning(self, system: AGISystem, problems: List[Dict[str, Any]], 
                                 evidence_completeness: float) -> Dict[str, Any]:
        """Test abductive reasoning with explanation generation"""
        correct = 0
        total = len(problems)
        details = {"problems_tested": total, "evidence_completeness": evidence_completeness, "individual_results": []}
        
        for problem in problems:
            # Provide partial evidence based on completeness parameter
            evidence = self._sample_evidence(problem["evidence"], evidence_completeness)
            
            task = {
                "type": "abductive_reasoning",
                "observations": problem["observations"],
                "evidence": evidence,
                "question": "What is the best explanation for these observations?",
                "possible_explanations": problem.get("possible_explanations", []),
                "expected_explanation": problem["correct_explanation"]
            }
            
            try:
                response = system.process_reasoning_task(task)
                predicted_explanation = response.get("explanation", "")
                
                # Score explanation quality (simplified)
                explanation_score = self._score_explanation(
                    predicted_explanation, 
                    problem["correct_explanation"],
                    problem.get("alternative_explanations", [])
                )
                
                is_correct = explanation_score > 0.7  # Threshold for correctness
                if is_correct:
                    correct += 1
                
                details["individual_results"].append({
                    "problem_type": problem["type"],
                    "observations": problem["observations"],
                    "evidence": evidence,
                    "expected": problem["correct_explanation"],
                    "predicted": predicted_explanation,
                    "explanation_score": explanation_score,
                    "correct": is_correct
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "problem_type": problem["type"],
                    "error": str(e)
                })
        
        accuracy = (correct / total) * 100 if total > 0 else 0
        details["accuracy"] = accuracy
        details["correct_answers"] = correct
        
        return {
            "score": accuracy,
            "success": accuracy > 0,
            "details": details
        }
    
    def _test_analogical_reasoning(self, system: AGISystem, problems: List[AnalogyProblem], 
                                  similarity_threshold: float) -> Dict[str, Any]:
        """Test analogical reasoning"""
        correct = 0
        total = len(problems)
        details = {"problems_tested": total, "similarity_threshold": similarity_threshold, "individual_results": []}
        
        for problem in problems:
            task = {
                "type": "analogical_reasoning",
                "source": problem.source,
                "target": problem.target,
                "question": "What is the analogical mapping between source and target?",
                "expected_mapping": problem.mapping,
                "analogy_type": problem.analogy_type
            }
            
            try:
                response = system.process_reasoning_task(task)
                predicted_mapping = response.get("mapping", {})
                
                # Score mapping quality
                mapping_score = self._score_analogical_mapping(
                    predicted_mapping, 
                    problem.mapping,
                    similarity_threshold
                )
                
                is_correct = mapping_score > similarity_threshold
                if is_correct:
                    correct += 1
                
                details["individual_results"].append({
                    "analogy_type": problem.analogy_type,
                    "difficulty": problem.difficulty,
                    "source": problem.source,
                    "target": problem.target,
                    "expected_mapping": problem.mapping,
                    "predicted_mapping": predicted_mapping,
                    "mapping_score": mapping_score,
                    "correct": is_correct
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "analogy_type": problem.analogy_type,
                    "error": str(e)
                })
        
        accuracy = (correct / total) * 100 if total > 0 else 0
        details["accuracy"] = accuracy
        details["correct_answers"] = correct
        
        return {
            "score": accuracy,
            "success": accuracy > 0,
            "details": details
        }
    
    def _generate_deductive_problems(self) -> List[LogicProblem]:
        """Generate deductive reasoning problems"""
        problems = []
        
        # Syllogisms
        syllogism_templates = [
            # Valid syllogisms
            {
                "premises": ["All {A} are {B}", "All {B} are {C}"],
                "conclusion": "All {A} are {C}",
                "valid": True,
                "variables": [
                    {"A": "humans", "B": "mortal", "C": "finite"},
                    {"A": "dogs", "B": "animals", "C": "living_things"},
                    {"A": "squares", "B": "rectangles", "C": "quadrilaterals"}
                ]
            },
            {
                "premises": ["All {A} are {B}", "{C} is a {A}"],
                "conclusion": "{C} is a {B}",
                "valid": True,
                "variables": [
                    {"A": "bird", "B": "animal", "C": "robin"},
                    {"A": "metal", "B": "conductor", "C": "copper"},
                    {"A": "mammal", "B": "warm_blooded", "C": "whale"}
                ]
            },
            # Invalid syllogisms
            {
                "premises": ["All {A} are {B}", "All {C} are {B}"],
                "conclusion": "All {A} are {C}",
                "valid": False,
                "variables": [
                    {"A": "cats", "B": "animals", "C": "dogs"},
                    {"A": "roses", "B": "flowers", "C": "tulips"}
                ]
            }
        ]
        
        for template in syllogism_templates:
            for variables in template["variables"]:
                premises = [p.format(**variables) for p in template["premises"]]
                conclusion = template["conclusion"].format(**variables)
                
                problems.append(LogicProblem(
                    premises=premises,
                    conclusion=conclusion,
                    valid=template["valid"],
                    difficulty="basic",
                    problem_type="syllogisms"
                ))
        
        # Propositional logic
        prop_problems = [
            {
                "premises": ["P → Q", "P"],
                "conclusion": "Q",
                "valid": True,
                "difficulty": "basic"
            },
            {
                "premises": ["P → Q", "¬Q"],
                "conclusion": "¬P",
                "valid": True,
                "difficulty": "intermediate"
            },
            {
                "premises": ["P ∨ Q", "¬P"],
                "conclusion": "Q",
                "valid": True,
                "difficulty": "basic"
            },
            {
                "premises": ["P → Q", "Q"],
                "conclusion": "P",
                "valid": False,
                "difficulty": "intermediate"
            }
        ]
        
        for prob in prop_problems:
            problems.append(LogicProblem(
                premises=prob["premises"],
                conclusion=prob["conclusion"],
                valid=prob["valid"],
                difficulty=prob["difficulty"],
                problem_type="propositional_logic"
            ))
        
        return problems
    
    def _generate_inductive_problems(self) -> List[PatternSequence]:
        """Generate inductive reasoning problems"""
        problems = []
        
        # Arithmetic sequences
        arithmetic_sequences = [
            ([2, 4, 6, 8], [10, 12], "arithmetic", "basic"),
            ([1, 4, 7, 10], [13, 16], "arithmetic", "basic"),
            ([10, 20, 30, 40], [50, 60], "arithmetic", "basic"),
            ([3, 7, 11, 15], [19, 23], "arithmetic", "intermediate")
        ]
        
        for seq, next_items, pattern_type, difficulty in arithmetic_sequences:
            problems.append(PatternSequence(
                sequence=seq,
                next_items=next_items,
                pattern_type="pattern_recognition",
                difficulty=difficulty
            ))
        
        # Geometric sequences
        geometric_sequences = [
            ([2, 4, 8, 16], [32, 64], "geometric", "intermediate"),
            ([3, 9, 27, 81], [243, 729], "geometric", "intermediate"),
            ([1, 2, 4, 8], [16, 32], "geometric", "basic")
        ]
        
        for seq, next_items, pattern_type, difficulty in geometric_sequences:
            problems.append(PatternSequence(
                sequence=seq,
                next_items=next_items,
                pattern_type="pattern_recognition",
                difficulty=difficulty
            ))
        
        # Fibonacci-like sequences
        fibonacci_sequences = [
            ([1, 1, 2, 3, 5], [8, 13], "fibonacci", "advanced"),
            ([2, 2, 4, 6, 10], [16, 26], "fibonacci", "advanced")
        ]
        
        for seq, next_items, pattern_type, difficulty in fibonacci_sequences:
            problems.append(PatternSequence(
                sequence=seq,
                next_items=next_items,
                pattern_type="sequence_completion",
                difficulty=difficulty
            ))
        
        return problems
    
    def _generate_abductive_problems(self) -> List[Dict[str, Any]]:
        """Generate abductive reasoning problems"""
        problems = [
            {
                "type": "explanation_generation",
                "observations": ["The grass is wet", "The car windshield is wet", "The sidewalk is wet"],
                "evidence": ["weather_forecast", "sprinkler_schedule", "time_of_day"],
                "correct_explanation": "It rained recently",
                "alternative_explanations": ["Sprinklers were on", "Someone washed their car"],
                "difficulty": "basic"
            },
            {
                "type": "hypothesis_formation", 
                "observations": ["Patient has fever", "Patient has cough", "Patient has fatigue"],
                "evidence": ["recent_travel", "contact_history", "symptom_duration", "test_results"],
                "correct_explanation": "Viral respiratory infection",
                "alternative_explanations": ["Bacterial infection", "Allergic reaction", "Stress"],
                "difficulty": "intermediate"
            },
            {
                "type": "best_explanation",
                "observations": ["Computer won't start", "No lights on power button", "No fan noise"],
                "evidence": ["power_cord_connected", "outlet_working", "power_supply_age"],
                "correct_explanation": "Power supply failure",
                "alternative_explanations": ["Motherboard failure", "Power cord failure", "RAM failure"],
                "difficulty": "intermediate"
            }
        ]
        
        return problems
    
    def _generate_analogy_problems(self) -> List[AnalogyProblem]:
        """Generate analogical reasoning problems"""
        problems = []
        
        # Abstract analogies
        abstract_analogies = [
            {
                "source": {"relation": "parent_of", "A": "bird", "B": "nest"},
                "target": {"relation": "parent_of", "A": "bee", "B": "?"},
                "mapping": {"bird": "bee", "nest": "hive"},
                "analogy_type": "abstract_analogies",
                "difficulty": "basic"
            },
            {
                "source": {"relation": "tool_for", "A": "hammer", "B": "nail"},
                "target": {"relation": "tool_for", "A": "key", "B": "?"},
                "mapping": {"hammer": "key", "nail": "lock"},
                "analogy_type": "abstract_analogies", 
                "difficulty": "basic"
            }
        ]
        
        for analogy in abstract_analogies:
            problems.append(AnalogyProblem(
                source=analogy["source"],
                target=analogy["target"],
                mapping=analogy["mapping"],
                analogy_type=analogy["analogy_type"],
                difficulty=analogy["difficulty"]
            ))
        
        return problems
    
    def _add_noise_to_sequence(self, sequence: List[Any], noise_level: float) -> List[Any]:
        """Add noise to a sequence"""
        if noise_level == 0:
            return sequence
        
        noisy_sequence = sequence.copy()
        num_to_modify = max(1, int(len(sequence) * noise_level))
        
        for _ in range(num_to_modify):
            idx = random.randint(0, len(sequence) - 1)
            if isinstance(sequence[idx], (int, float)):
                noisy_sequence[idx] += random.randint(-2, 2)
        
        return noisy_sequence
    
    def _check_sequence_prediction(self, predicted: List[Any], expected: List[Any]) -> bool:
        """Check if sequence prediction is correct"""
        if len(predicted) != len(expected):
            return False
        
        for p, e in zip(predicted, expected):
            if isinstance(e, (int, float)) and isinstance(p, (int, float)):
                if abs(p - e) > 1:  # Allow small numerical errors
                    return False
            elif p != e:
                return False
        
        return True
    
    def _sample_evidence(self, evidence: List[str], completeness: float) -> List[str]:
        """Sample evidence based on completeness parameter"""
        num_evidence = max(1, int(len(evidence) * completeness))
        return random.sample(evidence, num_evidence)
    
    def _score_explanation(self, predicted: str, correct: str, alternatives: List[str]) -> float:
        """Score explanation quality (simplified)"""
        if not predicted:
            return 0.0
        
        predicted_lower = predicted.lower()
        correct_lower = correct.lower()
        
        # Simple keyword matching (in real implementation, use more sophisticated NLP)
        correct_keywords = set(correct_lower.split())
        predicted_keywords = set(predicted_lower.split())
        
        overlap = len(correct_keywords.intersection(predicted_keywords))
        max_overlap = len(correct_keywords)
        
        if max_overlap == 0:
            return 0.0
        
        return overlap / max_overlap
    
    def _score_analogical_mapping(self, predicted: Dict[str, str], expected: Dict[str, str], 
                                 threshold: float) -> float:
        """Score analogical mapping quality"""
        if not predicted or not expected:
            return 0.0
        
        correct_mappings = 0
        total_mappings = len(expected)
        
        for source, target in expected.items():
            if source in predicted and predicted[source] == target:
                correct_mappings += 1
        
        return correct_mappings / total_mappings if total_mappings > 0 else 0.0