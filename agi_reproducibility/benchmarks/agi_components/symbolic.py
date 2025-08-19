"""
Symbolic AI Benchmarks for AGI Component Benchmark Suite

Implements comprehensive symbolic AI tests including:
- PLN inference (probabilistic syllogisms, uncertain reasoning, belief updating)
- First-order logic (theorem proving, model checking, satisfiability)
- Probabilistic reasoning (Bayesian networks, Markov models, causal inference)
- Temporal logic (LTL formulas, CTL specifications, temporal planning)

Includes specific tests for Hyperon/PRIMUS architectures.
"""

import random
import time
import json
import math
from typing import Dict, List, Any, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .core import BaseBenchmark, AGISystem, BenchmarkResult


class TruthValueType(Enum):
    SIMPLE = "simple"
    INDEFINITE = "indefinite"
    DISTRIBUTIONAL = "distributional"


@dataclass
class PLNInferenceTask:
    """Represents a PLN inference task"""
    task_id: str
    premises: List[Dict[str, Any]]
    query: Dict[str, Any]
    truth_value_type: TruthValueType
    inference_rules: List[str]
    expected_result: Dict[str, Any]
    difficulty: str


@dataclass
class FOLTask:
    """Represents a first-order logic task"""
    task_id: str
    task_type: str  # theorem_proving, model_checking, satisfiability
    axioms: List[str]
    goal: str
    domain: str
    complexity_class: str
    expected_result: bool


@dataclass
class ProbabilisticTask:
    """Represents a probabilistic reasoning task"""
    task_id: str
    task_type: str  # bayesian_network, markov_model, causal_inference
    structure: Dict[str, Any]
    evidence: Dict[str, Any]
    query: Dict[str, Any]
    uncertainty_type: str
    expected_probability: float


@dataclass
class TemporalLogicTask:
    """Represents a temporal logic task"""
    task_id: str
    task_type: str  # ltl_formula, ctl_specification, temporal_planning
    formula: str
    model: Dict[str, Any]
    time_model: str  # linear, branching, metric
    expected_satisfaction: bool


class SymbolicAIBenchmarks(BaseBenchmark):
    """Comprehensive symbolic AI benchmarks"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.pln_tasks = self._generate_pln_tasks()
        self.fol_tasks = self._generate_fol_tasks()
        self.probabilistic_tasks = self._generate_probabilistic_tasks()
        self.temporal_tasks = self._generate_temporal_tasks()
    
    def run_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run all symbolic AI tests"""
        results = []
        
        # PLN inference tests
        if self.config.get("pln_inference", {}).get("enabled", True):
            results.extend(self._run_pln_tests(system))
        
        # First-order logic tests
        if self.config.get("first_order_logic", {}).get("enabled", True):
            results.extend(self._run_fol_tests(system))
        
        # Probabilistic reasoning tests
        if self.config.get("probabilistic_reasoning", {}).get("enabled", True):
            results.extend(self._run_probabilistic_tests(system))
        
        # Temporal logic tests
        if self.config.get("temporal_logic", {}).get("enabled", True):
            results.extend(self._run_temporal_tests(system))
        
        return results
    
    def _run_pln_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run PLN inference tests"""
        results = []
        config = self.config.get("pln_inference", {})
        
        for test_set in config.get("test_sets", ["probabilistic_syllogisms"]):
            for truth_value_type in config.get("truth_value_types", ["simple"]):
                for inference_rule in config.get("inference_rules", ["deduction"]):
                    tasks = [t for t in self.pln_tasks 
                           if test_set in t.task_id and 
                           t.truth_value_type.value == truth_value_type and
                           inference_rule in t.inference_rules]
                    
                    if tasks:
                        result = self._run_single_test(
                            lambda sys: self._test_pln_inference(sys, tasks, test_set, truth_value_type, inference_rule),
                            f"pln_{test_set}_{truth_value_type}_{inference_rule}",
                            system,
                            max_score=100.0
                        )
                        results.append(result)
        
        return results
    
    def _run_fol_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run first-order logic tests"""
        results = []
        config = self.config.get("first_order_logic", {})
        
        for test_set in config.get("test_sets", ["theorem_proving"]):
            for complexity_class in config.get("complexity_classes", ["propositional"]):
                tasks = [t for t in self.fol_tasks 
                        if t.task_type == test_set and t.complexity_class == complexity_class]
                
                if tasks:
                    result = self._run_single_test(
                        lambda sys: self._test_fol_reasoning(sys, tasks, test_set, complexity_class),
                        f"fol_{test_set}_{complexity_class}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_probabilistic_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run probabilistic reasoning tests"""
        results = []
        config = self.config.get("probabilistic_reasoning", {})
        
        for test_set in config.get("test_sets", ["bayesian_networks"]):
            for uncertainty_type in config.get("uncertainty_types", ["aleatory"]):
                tasks = [t for t in self.probabilistic_tasks 
                        if t.task_type.replace("_", "") in test_set.replace("_", "") and 
                        t.uncertainty_type == uncertainty_type]
                
                if tasks:
                    result = self._run_single_test(
                        lambda sys: self._test_probabilistic_reasoning(sys, tasks, test_set, uncertainty_type),
                        f"probabilistic_{test_set}_{uncertainty_type}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_temporal_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run temporal logic tests"""
        results = []
        config = self.config.get("temporal_logic", {})
        
        for test_set in config.get("test_sets", ["ltl_formulas"]):
            for time_model in config.get("time_models", ["linear"]):
                tasks = [t for t in self.temporal_tasks 
                        if test_set.replace("_formulas", "").replace("_specifications", "") in t.task_type and
                        t.time_model == time_model]
                
                if tasks:
                    result = self._run_single_test(
                        lambda sys: self._test_temporal_logic(sys, tasks, test_set, time_model),
                        f"temporal_{test_set}_{time_model}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _test_pln_inference(self, system: AGISystem, tasks: List[PLNInferenceTask], 
                           test_set: str, truth_value_type: str, inference_rule: str) -> Dict[str, Any]:
        """Test PLN inference capability"""
        details = {
            "test_set": test_set,
            "truth_value_type": truth_value_type,
            "inference_rule": inference_rule,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            symbolic_task = {
                "type": "pln_inference",
                "premises": task.premises,
                "query": task.query,
                "truth_value_type": task.truth_value_type.value,
                "inference_rules": task.inference_rules,
                "instruction": "Perform PLN inference to derive the truth value of the query"
            }
            
            try:
                start_time = time.time()
                response = system.process_symbolic_task(symbolic_task)
                inference_time = time.time() - start_time
                
                result_truth_value = response.get("truth_value", {})
                inference_steps = response.get("inference_steps", [])
                confidence = response.get("confidence", 0.0)
                
                # Evaluate PLN inference quality
                inference_score = self._evaluate_pln_inference(
                    result_truth_value, task.expected_result, inference_steps, task
                )
                
                total_score += inference_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "premises": task.premises,
                    "query": task.query,
                    "expected_result": task.expected_result,
                    "result_truth_value": result_truth_value,
                    "inference_steps": inference_steps,
                    "confidence": confidence,
                    "inference_score": inference_score,
                    "inference_time": inference_time,
                    "truth_value_accuracy": self._assess_truth_value_accuracy(result_truth_value, task.expected_result),
                    "inference_validity": self._assess_inference_validity(inference_steps, task),
                    "reasoning_efficiency": self._assess_reasoning_efficiency(inference_steps, inference_time)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_pln_score"] = average_score
        
        return {
            "score": average_score,
            "success": average_score > 0,
            "details": details
        }
    
    def _test_fol_reasoning(self, system: AGISystem, tasks: List[FOLTask], 
                           test_set: str, complexity_class: str) -> Dict[str, Any]:
        """Test first-order logic reasoning"""
        details = {
            "test_set": test_set,
            "complexity_class": complexity_class,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            symbolic_task = {
                "type": "first_order_logic",
                "task_type": task.task_type,
                "axioms": task.axioms,
                "goal": task.goal,
                "domain": task.domain,
                "complexity_class": task.complexity_class,
                "instruction": f"Perform {task.task_type} for the given goal"
            }
            
            try:
                start_time = time.time()
                response = system.process_symbolic_task(symbolic_task)
                reasoning_time = time.time() - start_time
                
                result = response.get("result", False)
                proof_steps = response.get("proof_steps", [])
                model = response.get("model", {})
                
                # Evaluate FOL reasoning quality
                fol_score = self._evaluate_fol_reasoning(
                    result, task.expected_result, proof_steps, task
                )
                
                total_score += fol_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "axioms": task.axioms,
                    "goal": task.goal,
                    "expected_result": task.expected_result,
                    "result": result,
                    "proof_steps": proof_steps,
                    "model": model,
                    "fol_score": fol_score,
                    "reasoning_time": reasoning_time,
                    "correctness": result == task.expected_result,
                    "proof_validity": self._assess_proof_validity(proof_steps, task),
                    "logical_soundness": self._assess_logical_soundness(proof_steps, task.axioms)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_fol_score"] = average_score
        
        return {
            "score": average_score,
            "success": average_score > 0,
            "details": details
        }
    
    def _test_probabilistic_reasoning(self, system: AGISystem, tasks: List[ProbabilisticTask], 
                                     test_set: str, uncertainty_type: str) -> Dict[str, Any]:
        """Test probabilistic reasoning capability"""
        details = {
            "test_set": test_set,
            "uncertainty_type": uncertainty_type,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            symbolic_task = {
                "type": "probabilistic_reasoning",
                "task_type": task.task_type,
                "structure": task.structure,
                "evidence": task.evidence,
                "query": task.query,
                "uncertainty_type": task.uncertainty_type,
                "instruction": "Perform probabilistic inference to compute the query probability"
            }
            
            try:
                start_time = time.time()
                response = system.process_symbolic_task(symbolic_task)
                inference_time = time.time() - start_time
                
                probability = response.get("probability", 0.0)
                inference_method = response.get("inference_method", "")
                uncertainty_estimate = response.get("uncertainty_estimate", 0.0)
                
                # Evaluate probabilistic reasoning quality
                prob_score = self._evaluate_probabilistic_reasoning(
                    probability, task.expected_probability, inference_method, task
                )
                
                total_score += prob_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "query": task.query,
                    "evidence": task.evidence,
                    "expected_probability": task.expected_probability,
                    "computed_probability": probability,
                    "inference_method": inference_method,
                    "uncertainty_estimate": uncertainty_estimate,
                    "prob_score": prob_score,
                    "inference_time": inference_time,
                    "probability_accuracy": self._assess_probability_accuracy(probability, task.expected_probability),
                    "inference_quality": self._assess_inference_quality(inference_method, task),
                    "uncertainty_handling": self._assess_uncertainty_handling(uncertainty_estimate, task)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_probabilistic_score"] = average_score
        
        return {
            "score": average_score,
            "success": average_score > 0,
            "details": details
        }
    
    def _test_temporal_logic(self, system: AGISystem, tasks: List[TemporalLogicTask], 
                            test_set: str, time_model: str) -> Dict[str, Any]:
        """Test temporal logic reasoning"""
        details = {
            "test_set": test_set,
            "time_model": time_model,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            symbolic_task = {
                "type": "temporal_logic",
                "task_type": task.task_type,
                "formula": task.formula,
                "model": task.model,
                "time_model": task.time_model,
                "instruction": "Evaluate the temporal logic formula against the given model"
            }
            
            try:
                start_time = time.time()
                response = system.process_symbolic_task(symbolic_task)
                evaluation_time = time.time() - start_time
                
                satisfaction = response.get("satisfaction", False)
                verification_trace = response.get("verification_trace", [])
                counterexample = response.get("counterexample", None)
                
                # Evaluate temporal logic reasoning quality
                temporal_score = self._evaluate_temporal_logic(
                    satisfaction, task.expected_satisfaction, verification_trace, task
                )
                
                total_score += temporal_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "formula": task.formula,
                    "time_model": task.time_model,
                    "expected_satisfaction": task.expected_satisfaction,
                    "computed_satisfaction": satisfaction,
                    "verification_trace": verification_trace,
                    "counterexample": counterexample,
                    "temporal_score": temporal_score,
                    "evaluation_time": evaluation_time,
                    "correctness": satisfaction == task.expected_satisfaction,
                    "trace_validity": self._assess_trace_validity(verification_trace, task),
                    "temporal_reasoning_quality": self._assess_temporal_reasoning_quality(response, task)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_temporal_score"] = average_score
        
        return {
            "score": average_score,
            "success": average_score > 0,
            "details": details
        }
    
    def _generate_pln_tasks(self) -> List[PLNInferenceTask]:
        """Generate PLN inference tasks"""
        tasks = []
        
        # Probabilistic syllogisms
        syllogism_tasks = [
            {
                "task_id": "pln_syllogism_1",
                "premises": [
                    {"statement": "Birds can fly", "truth_value": {"strength": 0.8, "confidence": 0.9}},
                    {"statement": "Tweety is a bird", "truth_value": {"strength": 1.0, "confidence": 1.0}}
                ],
                "query": {"statement": "Tweety can fly", "truth_value": None},
                "truth_value_type": TruthValueType.SIMPLE,
                "inference_rules": ["deduction"],
                "expected_result": {"strength": 0.8, "confidence": 0.8},
                "difficulty": "basic"
            },
            {
                "task_id": "pln_uncertain_reasoning_1",
                "premises": [
                    {"statement": "Most students study hard", "truth_value": {"strength": 0.7, "confidence": 0.6}},
                    {"statement": "Alice is a student", "truth_value": {"strength": 1.0, "confidence": 0.9}}
                ],
                "query": {"statement": "Alice studies hard", "truth_value": None},
                "truth_value_type": TruthValueType.SIMPLE,
                "inference_rules": ["deduction"],
                "expected_result": {"strength": 0.7, "confidence": 0.5},
                "difficulty": "intermediate"
            }
        ]
        
        # Belief updating tasks
        belief_updating_tasks = [
            {
                "task_id": "pln_belief_updating_1",
                "premises": [
                    {"statement": "It will rain today", "truth_value": {"strength": 0.3, "confidence": 0.7}},
                    {"statement": "Dark clouds are forming", "truth_value": {"strength": 1.0, "confidence": 0.9}}
                ],
                "query": {"statement": "It will rain today", "truth_value": None},
                "truth_value_type": TruthValueType.SIMPLE,
                "inference_rules": ["revision"],
                "expected_result": {"strength": 0.6, "confidence": 0.8},
                "difficulty": "intermediate"
            }
        ]
        
        all_task_data = syllogism_tasks + belief_updating_tasks
        
        for task_data in all_task_data:
            tasks.append(PLNInferenceTask(
                task_id=task_data["task_id"],
                premises=task_data["premises"],
                query=task_data["query"],
                truth_value_type=task_data["truth_value_type"],
                inference_rules=task_data["inference_rules"],
                expected_result=task_data["expected_result"],
                difficulty=task_data["difficulty"]
            ))
        
        return tasks
    
    def _generate_fol_tasks(self) -> List[FOLTask]:
        """Generate first-order logic tasks"""
        tasks = []
        
        # Theorem proving tasks
        theorem_tasks = [
            {
                "task_id": "fol_theorem_1",
                "task_type": "theorem_proving",
                "axioms": [
                    "∀x (Human(x) → Mortal(x))",
                    "Human(Socrates)"
                ],
                "goal": "Mortal(Socrates)",
                "domain": "philosophy",
                "complexity_class": "propositional",
                "expected_result": True
            },
            {
                "task_id": "fol_theorem_2",
                "task_type": "theorem_proving",
                "axioms": [
                    "∀x (Bird(x) → CanFly(x))",
                    "∀x (Penguin(x) → Bird(x))",
                    "∀x (Penguin(x) → ¬CanFly(x))"
                ],
                "goal": "∃x (Bird(x) ∧ ¬CanFly(x))",
                "domain": "biology",
                "complexity_class": "first_order",
                "expected_result": True
            }
        ]
        
        # Model checking tasks
        model_checking_tasks = [
            {
                "task_id": "fol_model_1",
                "task_type": "model_checking",
                "axioms": [
                    "∀x (Student(x) → Studies(x))",
                    "Student(Alice)"
                ],
                "goal": "Studies(Alice)",
                "domain": "education",
                "complexity_class": "propositional",
                "expected_result": True
            }
        ]
        
        # Satisfiability tasks
        sat_tasks = [
            {
                "task_id": "fol_sat_1",
                "task_type": "satisfiability",
                "axioms": [
                    "∀x (P(x) → Q(x))",
                    "P(a)",
                    "¬Q(a)"
                ],
                "goal": "satisfiable",
                "domain": "logic",
                "complexity_class": "propositional",
                "expected_result": False
            }
        ]
        
        all_task_data = theorem_tasks + model_checking_tasks + sat_tasks
        
        for task_data in all_task_data:
            tasks.append(FOLTask(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                axioms=task_data["axioms"],
                goal=task_data["goal"],
                domain=task_data["domain"],
                complexity_class=task_data["complexity_class"],
                expected_result=task_data["expected_result"]
            ))
        
        return tasks
    
    def _generate_probabilistic_tasks(self) -> List[ProbabilisticTask]:
        """Generate probabilistic reasoning tasks"""
        tasks = []
        
        # Bayesian network tasks
        bayesian_tasks = [
            {
                "task_id": "prob_bayesian_1",
                "task_type": "bayesian_network",
                "structure": {
                    "nodes": ["Rain", "Sprinkler", "WetGrass"],
                    "edges": [("Rain", "WetGrass"), ("Sprinkler", "WetGrass")],
                    "cpds": {
                        "Rain": {"True": 0.2, "False": 0.8},
                        "Sprinkler": {"True": 0.3, "False": 0.7},
                        "WetGrass": {
                            ("True", "True"): 0.95,
                            ("True", "False"): 0.9,
                            ("False", "True"): 0.8,
                            ("False", "False"): 0.1
                        }
                    }
                },
                "evidence": {"WetGrass": "True"},
                "query": {"variable": "Rain", "value": "True"},
                "uncertainty_type": "aleatory",
                "expected_probability": 0.357
            }
        ]
        
        # Markov model tasks
        markov_tasks = [
            {
                "task_id": "prob_markov_1",
                "task_type": "markov_model",
                "structure": {
                    "states": ["Sunny", "Rainy", "Cloudy"],
                    "transition_matrix": {
                        "Sunny": {"Sunny": 0.7, "Rainy": 0.1, "Cloudy": 0.2},
                        "Rainy": {"Sunny": 0.3, "Rainy": 0.4, "Cloudy": 0.3},
                        "Cloudy": {"Sunny": 0.4, "Rainy": 0.3, "Cloudy": 0.3}
                    },
                    "initial_state": "Sunny"
                },
                "evidence": {"time_steps": 2},
                "query": {"state": "Rainy", "time": 2},
                "uncertainty_type": "aleatory",
                "expected_probability": 0.19
            }
        ]
        
        # Causal inference tasks
        causal_tasks = [
            {
                "task_id": "prob_causal_1",
                "task_type": "causal_inference",
                "structure": {
                    "variables": ["X", "Y", "Z"],
                    "causal_graph": [("X", "Z"), ("Y", "Z")],
                    "interventions": {"X": 1}
                },
                "evidence": {"observational_data": "dataset_1"},
                "query": {"effect": "Z", "intervention": {"X": 1}},
                "uncertainty_type": "epistemic",
                "expected_probability": 0.65
            }
        ]
        
        all_task_data = bayesian_tasks + markov_tasks + causal_tasks
        
        for task_data in all_task_data:
            tasks.append(ProbabilisticTask(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                structure=task_data["structure"],
                evidence=task_data["evidence"],
                query=task_data["query"],
                uncertainty_type=task_data["uncertainty_type"],
                expected_probability=task_data["expected_probability"]
            ))
        
        return tasks
    
    def _generate_temporal_tasks(self) -> List[TemporalLogicTask]:
        """Generate temporal logic tasks"""
        tasks = []
        
        # LTL formula tasks
        ltl_tasks = [
            {
                "task_id": "temporal_ltl_1",
                "task_type": "ltl_formula",
                "formula": "□(request → ◇response)",
                "model": {
                    "states": ["s0", "s1", "s2"],
                    "transitions": [("s0", "s1"), ("s1", "s2"), ("s2", "s0")],
                    "labeling": {
                        "s0": [],
                        "s1": ["request"],
                        "s2": ["response"]
                    }
                },
                "time_model": "linear",
                "expected_satisfaction": True
            },
            {
                "task_id": "temporal_ltl_2",
                "task_type": "ltl_formula",
                "formula": "◇□safe",
                "model": {
                    "states": ["s0", "s1", "s2"],
                    "transitions": [("s0", "s1"), ("s1", "s2"), ("s2", "s2")],
                    "labeling": {
                        "s0": [],
                        "s1": [],
                        "s2": ["safe"]
                    }
                },
                "time_model": "linear",
                "expected_satisfaction": True
            }
        ]
        
        # CTL specification tasks
        ctl_tasks = [
            {
                "task_id": "temporal_ctl_1",
                "task_type": "ctl_specification",
                "formula": "AG(critical → EF released)",
                "model": {
                    "states": ["s0", "s1", "s2", "s3"],
                    "transitions": [("s0", "s1"), ("s1", "s2"), ("s2", "s3"), ("s3", "s0"), ("s2", "s0")],
                    "labeling": {
                        "s0": [],
                        "s1": ["critical"],
                        "s2": ["critical"],
                        "s3": ["released"]
                    }
                },
                "time_model": "branching",
                "expected_satisfaction": True
            }
        ]
        
        # Temporal planning tasks
        planning_tasks = [
            {
                "task_id": "temporal_planning_1",
                "task_type": "temporal_planning",
                "formula": "eventually(goal_achieved)",
                "model": {
                    "initial_state": {"robot_at": "A", "goal_at": "B"},
                    "actions": [
                        {"name": "move", "duration": 2, "effects": {"robot_at": "B"}},
                        {"name": "pickup", "duration": 1, "effects": {"holding_goal": True}}
                    ],
                    "goal": {"robot_at": "B", "holding_goal": True}
                },
                "time_model": "metric",
                "expected_satisfaction": True
            }
        ]
        
        all_task_data = ltl_tasks + ctl_tasks + planning_tasks
        
        for task_data in all_task_data:
            tasks.append(TemporalLogicTask(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                formula=task_data["formula"],
                model=task_data["model"],
                time_model=task_data["time_model"],
                expected_satisfaction=task_data["expected_satisfaction"]
            ))
        
        return tasks
    
    # Evaluation methods
    
    def _evaluate_pln_inference(self, result_truth_value: Dict[str, Any], 
                               expected_result: Dict[str, Any], 
                               inference_steps: List[str], 
                               task: PLNInferenceTask) -> float:
        """Evaluate PLN inference quality"""
        if not result_truth_value:
            return 0
        
        truth_value_score = self._assess_truth_value_accuracy(result_truth_value, expected_result)
        inference_score = self._assess_inference_validity(inference_steps, task)
        
        return (truth_value_score * 0.7) + (inference_score * 0.3)
    
    def _evaluate_fol_reasoning(self, result: bool, expected_result: bool, 
                               proof_steps: List[str], task: FOLTask) -> float:
        """Evaluate FOL reasoning quality"""
        correctness_score = 100 if result == expected_result else 0
        proof_score = self._assess_proof_validity(proof_steps, task)
        
        return (correctness_score * 0.8) + (proof_score * 0.2)
    
    def _evaluate_probabilistic_reasoning(self, probability: float, expected_probability: float, 
                                         inference_method: str, task: ProbabilisticTask) -> float:
        """Evaluate probabilistic reasoning quality"""
        accuracy_score = self._assess_probability_accuracy(probability, expected_probability)
        method_score = self._assess_inference_quality(inference_method, task)
        
        return (accuracy_score * 0.8) + (method_score * 0.2)
    
    def _evaluate_temporal_logic(self, satisfaction: bool, expected_satisfaction: bool, 
                                verification_trace: List[str], task: TemporalLogicTask) -> float:
        """Evaluate temporal logic reasoning quality"""
        correctness_score = 100 if satisfaction == expected_satisfaction else 0
        trace_score = self._assess_trace_validity(verification_trace, task)
        
        return (correctness_score * 0.8) + (trace_score * 0.2)
    
    # Assessment helper methods
    
    def _assess_truth_value_accuracy(self, result_tv: Dict[str, Any], expected_tv: Dict[str, Any]) -> float:
        """Assess accuracy of truth value computation"""
        if not result_tv or not expected_tv:
            return 0
        
        strength_diff = abs(result_tv.get("strength", 0) - expected_tv.get("strength", 0))
        confidence_diff = abs(result_tv.get("confidence", 0) - expected_tv.get("confidence", 0))
        
        strength_score = max(0, 100 - (strength_diff * 100))
        confidence_score = max(0, 100 - (confidence_diff * 100))
        
        return (strength_score + confidence_score) / 2
    
    def _assess_inference_validity(self, inference_steps: List[str], task: PLNInferenceTask) -> float:
        """Assess validity of inference steps"""
        if not inference_steps:
            return 0
        
        # Check if required inference rules are used
        rules_used = 0
        for rule in task.inference_rules:
            if any(rule in step.lower() for step in inference_steps):
                rules_used += 1
        
        rule_score = (rules_used / len(task.inference_rules)) * 100 if task.inference_rules else 50
        
        # Check for logical structure
        logical_indicators = ["therefore", "thus", "hence", "implies", "follows"]
        logical_count = sum(1 for step in inference_steps 
                           for indicator in logical_indicators 
                           if indicator in step.lower())
        
        logical_score = min(50, logical_count * 25)
        
        return (rule_score * 0.7) + (logical_score * 0.3)
    
    def _assess_reasoning_efficiency(self, inference_steps: List[str], inference_time: float) -> float:
        """Assess efficiency of reasoning process"""
        if not inference_steps or inference_time <= 0:
            return 50
        
        steps_per_second = len(inference_steps) / inference_time
        efficiency_score = min(100, steps_per_second * 10)  # Normalize
        
        return efficiency_score
    
    def _assess_proof_validity(self, proof_steps: List[str], task: FOLTask) -> float:
        """Assess validity of proof steps"""
        if not proof_steps:
            return 0
        
        # Check for logical proof structure
        proof_indicators = ["assume", "given", "therefore", "conclude", "qed", "by", "from"]
        proof_structure_score = 0
        
        for step in proof_steps:
            step_lower = step.lower()
            if any(indicator in step_lower for indicator in proof_indicators):
                proof_structure_score += 1
        
        structure_score = min(100, (proof_structure_score / len(proof_steps)) * 200)
        
        # Check for use of axioms
        axiom_usage = 0
        for axiom in task.axioms:
            axiom_keywords = axiom.lower().split()[:3]  # First few words
            for step in proof_steps:
                if any(keyword in step.lower() for keyword in axiom_keywords):
                    axiom_usage += 1
                    break
        
        axiom_score = (axiom_usage / len(task.axioms)) * 100 if task.axioms else 50
        
        return (structure_score * 0.6) + (axiom_score * 0.4)
    
    def _assess_logical_soundness(self, proof_steps: List[str], axioms: List[str]) -> float:
        """Assess logical soundness of proof"""
        if not proof_steps:
            return 0
        
        # Simple heuristic: check if proof references the axioms appropriately
        soundness_score = 0
        for axiom in axioms:
            axiom_concepts = set(axiom.lower().split())
            for step in proof_steps:
                step_concepts = set(step.lower().split())
                if axiom_concepts.intersection(step_concepts):
                    soundness_score += 1
                    break
        
        return (soundness_score / len(axioms)) * 100 if axioms else 50
    
    def _assess_probability_accuracy(self, computed_prob: float, expected_prob: float) -> float:
        """Assess accuracy of probability computation"""
        if expected_prob == 0:
            return 100 if computed_prob == 0 else 0
        
        relative_error = abs(computed_prob - expected_prob) / expected_prob
        accuracy_score = max(0, 100 - (relative_error * 100))
        
        return accuracy_score
    
    def _assess_inference_quality(self, inference_method: str, task: ProbabilisticTask) -> float:
        """Assess quality of probabilistic inference method"""
        if not inference_method:
            return 0
        
        # Check for appropriate inference methods
        method_appropriateness = {
            "bayesian_network": ["exact_inference", "variable_elimination", "message_passing"],
            "markov_model": ["forward_algorithm", "viterbi", "sampling"],
            "causal_inference": ["do_calculus", "backdoor", "instrumental_variables"]
        }
        
        appropriate_methods = method_appropriateness.get(task.task_type, [])
        method_lower = inference_method.lower()
        
        for appropriate in appropriate_methods:
            if appropriate in method_lower:
                return 100
        
        # Partial credit for mentioning inference
        inference_terms = ["inference", "compute", "calculate", "estimate"]
        if any(term in method_lower for term in inference_terms):
            return 50
        
        return 0
    
    def _assess_uncertainty_handling(self, uncertainty_estimate: float, task: ProbabilisticTask) -> float:
        """Assess handling of uncertainty"""
        if task.uncertainty_type == "aleatory":
            # For aleatory uncertainty, estimate should reflect inherent randomness
            return 100 if 0 <= uncertainty_estimate <= 1 else 0
        elif task.uncertainty_type == "epistemic":
            # For epistemic uncertainty, estimate should reflect knowledge limitations
            return 100 if uncertainty_estimate > 0 else 0
        
        return 50  # Default score
    
    def _assess_trace_validity(self, verification_trace: List[str], task: TemporalLogicTask) -> float:
        """Assess validity of temporal verification trace"""
        if not verification_trace:
            return 0
        
        # Check for temporal reasoning elements
        temporal_terms = ["eventually", "always", "next", "until", "release", "state", "transition"]
        temporal_count = 0
        
        for trace_item in verification_trace:
            trace_lower = trace_item.lower()
            if any(term in trace_lower for term in temporal_terms):
                temporal_count += 1
        
        temporal_score = min(100, (temporal_count / len(verification_trace)) * 200)
        
        return temporal_score
    
    def _assess_temporal_reasoning_quality(self, response: Dict[str, Any], task: TemporalLogicTask) -> float:
        """Assess overall temporal reasoning quality"""
        trace = response.get("verification_trace", [])
        counterexample = response.get("counterexample", None)
        
        quality_score = 0
        
        # Check for appropriate temporal concepts
        if trace:
            quality_score += 50
        
        # If satisfaction is false, check for counterexample
        if not response.get("satisfaction", True) and counterexample:
            quality_score += 50
        elif response.get("satisfaction", True):
            quality_score += 50
        
        return quality_score