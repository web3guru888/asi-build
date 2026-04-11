"""
Neural-Symbolic Integration Benchmarks for AGI Component Benchmark Suite

Implements comprehensive neural-symbolic integration tests including:
- Symbol grounding (visual, linguistic, sensorimotor grounding)
- Concept formation (prototype learning, exemplar models, theory-based concepts)
- Abstract reasoning (Ravens matrices, Bongard problems, abstract visual reasoning)
- Explainable AI (local, global, counterfactual, causal explanations)
"""

import random
import time
import json
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .core import BaseBenchmark, AGISystem, BenchmarkResult


class GroundingModality(Enum):
    VISUAL = "visual"
    LINGUISTIC = "linguistic"
    SENSORIMOTOR = "sensorimotor"
    CROSS_MODAL = "cross_modal"


@dataclass
class SymbolGroundingTask:
    """Represents a symbol grounding task"""
    task_id: str
    modality: GroundingModality
    symbols: List[str]
    perceptual_input: Dict[str, Any]
    abstraction_level: str  # perceptual, conceptual, symbolic
    grounding_targets: Dict[str, Any]
    evaluation_criteria: List[str]


@dataclass
class ConceptFormationTask:
    """Represents a concept formation task"""
    task_id: str
    task_type: str  # prototype_learning, exemplar_models, theory_based
    examples: List[Dict[str, Any]]
    concept_space: Dict[str, Any]
    hierarchical: bool
    compositional: bool
    target_concept: Dict[str, Any]


@dataclass
class AbstractReasoningTask:
    """Represents an abstract reasoning task"""
    task_id: str
    task_type: str  # ravens_matrices, bongard_problems, abstract_visual
    problem_specification: Dict[str, Any]
    options: List[Dict[str, Any]]
    correct_answer: Any
    reasoning_type: str
    neural_input_required: bool


@dataclass
class ExplainabilityTask:
    """Represents an explainable AI task"""
    task_id: str
    explanation_type: str  # local, global, counterfactual, causal
    model_decision: Dict[str, Any]
    input_data: Dict[str, Any]
    explanation_query: str
    target_audience: str  # technical, general
    fidelity_requirements: Dict[str, Any]


class NeuralSymbolicBenchmarks(BaseBenchmark):
    """Neural-symbolic integration benchmarks"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.grounding_tasks = self._generate_grounding_tasks()
        self.concept_tasks = self._generate_concept_tasks()
        self.abstract_tasks = self._generate_abstract_tasks()
        self.explainability_tasks = self._generate_explainability_tasks()
    
    def run_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run all neural-symbolic integration tests"""
        results = []
        
        # Symbol grounding tests
        if self.config.get("symbol_grounding", {}).get("enabled", True):
            results.extend(self._run_grounding_tests(system))
        
        # Concept formation tests
        if self.config.get("concept_formation", {}).get("enabled", True):
            results.extend(self._run_concept_tests(system))
        
        # Abstract reasoning tests
        if self.config.get("abstract_reasoning", {}).get("enabled", True):
            results.extend(self._run_abstract_tests(system))
        
        # Explainability tests
        if self.config.get("explainable_ai", {}).get("enabled", True):
            results.extend(self._run_explainability_tests(system))
        
        return results
    
    def _run_grounding_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run symbol grounding tests"""
        results = []
        config = self.config.get("symbol_grounding", {})
        
        for test_set in config.get("test_sets", ["visual_symbol_grounding"]):
            for abstraction_level in config.get("abstraction_levels", ["perceptual"]):
                modality = self._extract_modality_from_test_set(test_set)
                tasks = [t for t in self.grounding_tasks 
                        if t.modality.value in test_set and t.abstraction_level == abstraction_level]
                
                if tasks:
                    result = self._run_single_test(
                        lambda sys: self._test_symbol_grounding(sys, tasks, test_set, abstraction_level),
                        f"grounding_{test_set}_{abstraction_level}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_concept_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run concept formation tests"""
        results = []
        config = self.config.get("concept_formation", {})
        
        for test_set in config.get("test_sets", ["prototype_learning"]):
            hierarchical = config.get("hierarchical_concepts", False)
            compositional = config.get("compositional_concepts", False)
            
            tasks = [t for t in self.concept_tasks 
                    if t.task_type == test_set and 
                    t.hierarchical == hierarchical and 
                    t.compositional == compositional]
            
            if tasks:
                result = self._run_single_test(
                    lambda sys: self._test_concept_formation(sys, tasks, test_set, hierarchical, compositional),
                    f"concept_{test_set}_h{hierarchical}_c{compositional}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _run_abstract_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run abstract reasoning tests"""
        results = []
        config = self.config.get("abstract_reasoning", {})
        
        for test_set in config.get("test_sets", ["ravens_progressive_matrices"]):
            neural_representations = config.get("neural_representations", True)
            symbolic_explanation = config.get("symbolic_explanation", True)
            
            tasks = [t for t in self.abstract_tasks 
                    if test_set.replace("_progressive_matrices", "").replace("_problems", "") in t.task_type]
            
            if tasks:
                result = self._run_single_test(
                    lambda sys: self._test_abstract_reasoning(sys, tasks, test_set, neural_representations, symbolic_explanation),
                    f"abstract_{test_set}_neural{neural_representations}_symbolic{symbolic_explanation}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _run_explainability_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run explainability tests"""
        results = []
        config = self.config.get("explainable_ai", {})
        
        for explanation_type in config.get("explanation_types", ["local"]):
            fidelity_metrics = config.get("fidelity_metrics", True)
            human_interpretability = config.get("human_interpretability", True)
            
            tasks = [t for t in self.explainability_tasks 
                    if t.explanation_type == explanation_type]
            
            if tasks:
                result = self._run_single_test(
                    lambda sys: self._test_explainability(sys, tasks, explanation_type, fidelity_metrics, human_interpretability),
                    f"explainability_{explanation_type}_fidelity{fidelity_metrics}_interpretable{human_interpretability}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _test_symbol_grounding(self, system: AGISystem, tasks: List[SymbolGroundingTask], 
                              test_set: str, abstraction_level: str) -> Dict[str, Any]:
        """Test symbol grounding capability"""
        details = {
            "test_set": test_set,
            "abstraction_level": abstraction_level,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            neural_symbolic_task = {
                "type": "symbol_grounding",
                "modality": task.modality.value,
                "symbols": task.symbols,
                "perceptual_input": task.perceptual_input,
                "abstraction_level": task.abstraction_level,
                "instruction": "Ground these symbols in the perceptual input and establish mappings"
            }
            
            try:
                start_time = time.time()
                response = system.process_neural_symbolic_task(neural_symbolic_task)
                grounding_time = time.time() - start_time
                
                grounding_mappings = response.get("grounding_mappings", {})
                confidence_scores = response.get("confidence_scores", {})
                abstraction_hierarchy = response.get("abstraction_hierarchy", {})
                
                # Evaluate symbol grounding quality
                grounding_score = self._evaluate_symbol_grounding(
                    grounding_mappings, task.grounding_targets, confidence_scores, task
                )
                
                total_score += grounding_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "modality": task.modality.value,
                    "symbols": task.symbols,
                    "grounding_mappings": grounding_mappings,
                    "confidence_scores": confidence_scores,
                    "abstraction_hierarchy": abstraction_hierarchy,
                    "grounding_score": grounding_score,
                    "grounding_time": grounding_time,
                    "mapping_accuracy": self._assess_mapping_accuracy(grounding_mappings, task.grounding_targets),
                    "abstraction_quality": self._assess_abstraction_quality(abstraction_hierarchy, task),
                    "cross_modal_consistency": self._assess_cross_modal_consistency(response, task)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_grounding_score"] = average_score
        
        return {
            "score": average_score,
            "success": average_score > 0,
            "details": details
        }
    
    def _test_concept_formation(self, system: AGISystem, tasks: List[ConceptFormationTask], 
                               test_set: str, hierarchical: bool, compositional: bool) -> Dict[str, Any]:
        """Test concept formation capability"""
        details = {
            "test_set": test_set,
            "hierarchical": hierarchical,
            "compositional": compositional,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            neural_symbolic_task = {
                "type": "concept_formation",
                "task_type": task.task_type,
                "examples": task.examples,
                "concept_space": task.concept_space,
                "hierarchical": task.hierarchical,
                "compositional": task.compositional,
                "instruction": "Form concepts from the given examples and represent them appropriately"
            }
            
            try:
                start_time = time.time()
                response = system.process_neural_symbolic_task(neural_symbolic_task)
                formation_time = time.time() - start_time
                
                formed_concept = response.get("formed_concept", {})
                concept_representation = response.get("concept_representation", {})
                generalization_rules = response.get("generalization_rules", [])
                concept_hierarchy = response.get("concept_hierarchy", {})
                
                # Evaluate concept formation quality
                concept_score = self._evaluate_concept_formation(
                    formed_concept, task.target_concept, concept_representation, task
                )
                
                total_score += concept_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "formed_concept": formed_concept,
                    "concept_representation": concept_representation,
                    "generalization_rules": generalization_rules,
                    "concept_hierarchy": concept_hierarchy,
                    "concept_score": concept_score,
                    "formation_time": formation_time,
                    "concept_accuracy": self._assess_concept_accuracy(formed_concept, task.target_concept),
                    "representation_quality": self._assess_representation_quality(concept_representation, task),
                    "generalization_ability": self._assess_generalization_ability(generalization_rules, task)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_concept_score"] = average_score
        
        return {
            "score": average_score,
            "success": average_score > 0,
            "details": details
        }
    
    def _test_abstract_reasoning(self, system: AGISystem, tasks: List[AbstractReasoningTask], 
                                test_set: str, neural_representations: bool, symbolic_explanation: bool) -> Dict[str, Any]:
        """Test abstract reasoning capability"""
        details = {
            "test_set": test_set,
            "neural_representations": neural_representations,
            "symbolic_explanation": symbolic_explanation,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            neural_symbolic_task = {
                "type": "abstract_reasoning",
                "task_type": task.task_type,
                "problem_specification": task.problem_specification,
                "options": task.options,
                "reasoning_type": task.reasoning_type,
                "neural_input_required": task.neural_input_required,
                "require_neural_representations": neural_representations,
                "require_symbolic_explanation": symbolic_explanation,
                "instruction": "Solve this abstract reasoning problem and provide explanation"
            }
            
            try:
                start_time = time.time()
                response = system.process_neural_symbolic_task(neural_symbolic_task)
                reasoning_time = time.time() - start_time
                
                answer = response.get("answer", None)
                neural_representation = response.get("neural_representation", {})
                symbolic_explanation = response.get("symbolic_explanation", "")
                reasoning_steps = response.get("reasoning_steps", [])
                
                # Evaluate abstract reasoning quality
                reasoning_score = self._evaluate_abstract_reasoning(
                    answer, task.correct_answer, symbolic_explanation, reasoning_steps, task
                )
                
                total_score += reasoning_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "answer": answer,
                    "correct_answer": task.correct_answer,
                    "neural_representation": str(neural_representation)[:200],  # Truncate for storage
                    "symbolic_explanation": symbolic_explanation,
                    "reasoning_steps": reasoning_steps,
                    "reasoning_score": reasoning_score,
                    "reasoning_time": reasoning_time,
                    "correctness": answer == task.correct_answer,
                    "explanation_quality": self._assess_explanation_quality(symbolic_explanation, task),
                    "neural_symbolic_integration": self._assess_neural_symbolic_integration(response, task)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_reasoning_score"] = average_score
        
        return {
            "score": average_score,
            "success": average_score > 0,
            "details": details
        }
    
    def _test_explainability(self, system: AGISystem, tasks: List[ExplainabilityTask], 
                            explanation_type: str, fidelity_metrics: bool, human_interpretability: bool) -> Dict[str, Any]:
        """Test explainability capability"""
        details = {
            "explanation_type": explanation_type,
            "fidelity_metrics": fidelity_metrics,
            "human_interpretability": human_interpretability,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            neural_symbolic_task = {
                "type": "explainable_ai",
                "explanation_type": task.explanation_type,
                "model_decision": task.model_decision,
                "input_data": task.input_data,
                "explanation_query": task.explanation_query,
                "target_audience": task.target_audience,
                "fidelity_requirements": task.fidelity_requirements,
                "require_fidelity_metrics": fidelity_metrics,
                "require_human_interpretability": human_interpretability,
                "instruction": "Provide an explanation for the model's decision"
            }
            
            try:
                start_time = time.time()
                response = system.process_neural_symbolic_task(neural_symbolic_task)
                explanation_time = time.time() - start_time
                
                explanation = response.get("explanation", "")
                fidelity_score = response.get("fidelity_score", 0.0)
                interpretability_score = response.get("interpretability_score", 0.0)
                evidence = response.get("evidence", [])
                
                # Evaluate explanation quality
                explainability_score = self._evaluate_explainability(
                    explanation, fidelity_score, interpretability_score, evidence, task
                )
                
                total_score += explainability_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "explanation_type": task.explanation_type,
                    "explanation": explanation,
                    "fidelity_score": fidelity_score,
                    "interpretability_score": interpretability_score,
                    "evidence": evidence,
                    "explainability_score": explainability_score,
                    "explanation_time": explanation_time,
                    "explanation_completeness": self._assess_explanation_completeness(explanation, task),
                    "explanation_accuracy": self._assess_explanation_accuracy(explanation, evidence, task),
                    "human_understandability": self._assess_human_understandability(explanation, task)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_explainability_score"] = average_score
        
        return {
            "score": average_score,
            "success": average_score > 0,
            "details": details
        }
    
    def _generate_grounding_tasks(self) -> List[SymbolGroundingTask]:
        """Generate symbol grounding tasks"""
        tasks = []
        
        # Visual symbol grounding
        visual_tasks = [
            {
                "task_id": "visual_grounding_1",
                "modality": GroundingModality.VISUAL,
                "symbols": ["red", "circle", "above"],
                "perceptual_input": {
                    "image_data": "red_circle_above_blue_square",
                    "objects": [
                        {"color": "red", "shape": "circle", "position": [100, 50]},
                        {"color": "blue", "shape": "square", "position": [100, 150]}
                    ]
                },
                "abstraction_level": "perceptual",
                "grounding_targets": {
                    "red": {"color": "red"},
                    "circle": {"shape": "circle"},
                    "above": {"spatial_relation": "above"}
                },
                "evaluation_criteria": ["color_accuracy", "shape_accuracy", "spatial_accuracy"]
            }
        ]
        
        # Linguistic symbol grounding
        linguistic_tasks = [
            {
                "task_id": "linguistic_grounding_1",
                "modality": GroundingModality.LINGUISTIC,
                "symbols": ["run", "fast", "agent"],
                "perceptual_input": {
                    "text": "The agent runs fast",
                    "semantic_structure": {
                        "predicate": "run",
                        "subject": "agent",
                        "modifier": "fast"
                    }
                },
                "abstraction_level": "conceptual",
                "grounding_targets": {
                    "run": {"action": "locomotion"},
                    "fast": {"property": "speed_high"},
                    "agent": {"entity": "actor"}
                },
                "evaluation_criteria": ["semantic_accuracy", "role_identification", "conceptual_mapping"]
            }
        ]
        
        # Cross-modal grounding
        cross_modal_tasks = [
            {
                "task_id": "cross_modal_grounding_1",
                "modality": GroundingModality.CROSS_MODAL,
                "symbols": ["dog", "bark", "happy"],
                "perceptual_input": {
                    "visual": {"image": "happy_dog_image"},
                    "auditory": {"sound": "dog_barking"},
                    "textual": {"description": "happy dog barking"}
                },
                "abstraction_level": "symbolic",
                "grounding_targets": {
                    "dog": {"visual_features": "animal_canine", "auditory_features": "bark_sound"},
                    "bark": {"auditory_pattern": "dog_vocalization"},
                    "happy": {"visual_cues": "tail_wagging", "contextual_cues": "positive_behavior"}
                },
                "evaluation_criteria": ["cross_modal_consistency", "symbol_integration", "contextual_grounding"]
            }
        ]
        
        all_task_data = visual_tasks + linguistic_tasks + cross_modal_tasks
        
        for task_data in all_task_data:
            tasks.append(SymbolGroundingTask(
                task_id=task_data["task_id"],
                modality=task_data["modality"],
                symbols=task_data["symbols"],
                perceptual_input=task_data["perceptual_input"],
                abstraction_level=task_data["abstraction_level"],
                grounding_targets=task_data["grounding_targets"],
                evaluation_criteria=task_data["evaluation_criteria"]
            ))
        
        return tasks
    
    def _generate_concept_tasks(self) -> List[ConceptFormationTask]:
        """Generate concept formation tasks"""
        tasks = []
        
        # Prototype learning tasks
        prototype_tasks = [
            {
                "task_id": "prototype_learning_1",
                "task_type": "prototype_learning",
                "examples": [
                    {"features": {"size": "large", "color": "red", "shape": "round"}, "label": "apple"},
                    {"features": {"size": "medium", "color": "red", "shape": "round"}, "label": "apple"},
                    {"features": {"size": "small", "color": "green", "shape": "round"}, "label": "apple"}
                ],
                "concept_space": {"feature_dimensions": ["size", "color", "shape"]},
                "hierarchical": False,
                "compositional": False,
                "target_concept": {
                    "prototype": {"size": "medium", "color": "red", "shape": "round"},
                    "variance": {"size": "high", "color": "medium", "shape": "low"}
                }
            }
        ]
        
        # Hierarchical concept tasks
        hierarchical_tasks = [
            {
                "task_id": "hierarchical_concepts_1",
                "task_type": "prototype_learning",
                "examples": [
                    {"features": {"type": "vehicle", "wheels": 4, "engine": "combustion"}, "label": "car"},
                    {"features": {"type": "vehicle", "wheels": 2, "engine": "electric"}, "label": "motorcycle"},
                    {"features": {"type": "vehicle", "wheels": 4, "engine": "electric"}, "label": "electric_car"}
                ],
                "concept_space": {"hierarchy": ["vehicle", "car", "motorcycle"]},
                "hierarchical": True,
                "compositional": False,
                "target_concept": {
                    "hierarchy": {
                        "vehicle": {"wheels": "variable", "engine": "variable"},
                        "car": {"wheels": 4, "engine": "variable"},
                        "motorcycle": {"wheels": 2, "engine": "variable"}
                    }
                }
            }
        ]
        
        # Compositional concept tasks
        compositional_tasks = [
            {
                "task_id": "compositional_concepts_1",
                "task_type": "theory_based",
                "examples": [
                    {"components": ["red", "circle"], "composition": "red_circle"},
                    {"components": ["blue", "square"], "composition": "blue_square"},
                    {"components": ["red", "square"], "composition": "red_square"}
                ],
                "concept_space": {"composition_rules": ["color_shape_combination"]},
                "hierarchical": False,
                "compositional": True,
                "target_concept": {
                    "composition_function": "combine(color, shape)",
                    "generalization_rules": ["any_color + any_shape = colored_shape"]
                }
            }
        ]
        
        all_task_data = prototype_tasks + hierarchical_tasks + compositional_tasks
        
        for task_data in all_task_data:
            tasks.append(ConceptFormationTask(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                examples=task_data["examples"],
                concept_space=task_data["concept_space"],
                hierarchical=task_data["hierarchical"],
                compositional=task_data["compositional"],
                target_concept=task_data["target_concept"]
            ))
        
        return tasks
    
    def _generate_abstract_tasks(self) -> List[AbstractReasoningTask]:
        """Generate abstract reasoning tasks"""
        tasks = []
        
        # Ravens Progressive Matrices
        ravens_tasks = [
            {
                "task_id": "ravens_matrix_1",
                "task_type": "ravens_matrices",
                "problem_specification": {
                    "matrix": [
                        ["circle", "square", "triangle"],
                        ["filled_circle", "filled_square", "?"],
                        ["double_circle", "double_square", "double_triangle"]
                    ],
                    "pattern": "shape_progression_with_style_variation"
                },
                "options": [
                    {"value": "filled_triangle", "features": ["triangle", "filled"]},
                    {"value": "striped_triangle", "features": ["triangle", "striped"]},
                    {"value": "double_triangle", "features": ["triangle", "double"]},
                    {"value": "empty_triangle", "features": ["triangle", "empty"]}
                ],
                "correct_answer": "filled_triangle",
                "reasoning_type": "pattern_completion",
                "neural_input_required": True
            }
        ]
        
        # Bongard Problems
        bongard_tasks = [
            {
                "task_id": "bongard_problem_1",
                "task_type": "bongard_problems",
                "problem_specification": {
                    "left_side": [
                        {"shapes": ["circle", "square"], "relation": "inside"},
                        {"shapes": ["triangle", "circle"], "relation": "inside"},
                        {"shapes": ["square", "triangle"], "relation": "inside"}
                    ],
                    "right_side": [
                        {"shapes": ["circle", "square"], "relation": "outside"},
                        {"shapes": ["triangle", "circle"], "relation": "outside"},
                        {"shapes": ["square", "triangle"], "relation": "outside"}
                    ],
                    "rule": "spatial_relationship_inside_vs_outside"
                },
                "options": [
                    {"description": "inside vs outside", "concept": "spatial_relationship"},
                    {"description": "same vs different shapes", "concept": "shape_comparison"},
                    {"description": "large vs small", "concept": "size_comparison"}
                ],
                "correct_answer": "spatial_relationship",
                "reasoning_type": "rule_discovery",
                "neural_input_required": True
            }
        ]
        
        all_task_data = ravens_tasks + bongard_tasks
        
        for task_data in all_task_data:
            tasks.append(AbstractReasoningTask(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                problem_specification=task_data["problem_specification"],
                options=task_data["options"],
                correct_answer=task_data["correct_answer"],
                reasoning_type=task_data["reasoning_type"],
                neural_input_required=task_data["neural_input_required"]
            ))
        
        return tasks
    
    def _generate_explainability_tasks(self) -> List[ExplainabilityTask]:
        """Generate explainability tasks"""
        tasks = []
        
        # Local explanation tasks
        local_tasks = [
            {
                "task_id": "local_explanation_1",
                "explanation_type": "local",
                "model_decision": {
                    "prediction": "approve_loan",
                    "confidence": 0.85,
                    "model_type": "neural_network"
                },
                "input_data": {
                    "features": {"income": 75000, "credit_score": 720, "debt_ratio": 0.3, "employment_years": 5},
                    "feature_importance": {"income": 0.4, "credit_score": 0.35, "debt_ratio": 0.15, "employment_years": 0.1}
                },
                "explanation_query": "Why was this loan application approved?",
                "target_audience": "general",
                "fidelity_requirements": {"accuracy": 0.9, "completeness": 0.8}
            }
        ]
        
        # Global explanation tasks
        global_tasks = [
            {
                "task_id": "global_explanation_1",
                "explanation_type": "global",
                "model_decision": {
                    "model_behavior": "image_classification",
                    "model_type": "convolutional_neural_network",
                    "performance": {"accuracy": 0.92, "classes": ["cat", "dog", "bird"]}
                },
                "input_data": {
                    "dataset_description": "animal_images",
                    "feature_patterns": {"edges": "important", "colors": "moderately_important", "textures": "important"}
                },
                "explanation_query": "How does this model classify animal images?",
                "target_audience": "technical",
                "fidelity_requirements": {"coverage": 0.85, "representativeness": 0.9}
            }
        ]
        
        # Counterfactual explanation tasks
        counterfactual_tasks = [
            {
                "task_id": "counterfactual_explanation_1",
                "explanation_type": "counterfactual",
                "model_decision": {
                    "prediction": "reject_application",
                    "confidence": 0.78,
                    "model_type": "decision_tree"
                },
                "input_data": {
                    "current_features": {"age": 25, "income": 35000, "credit_score": 620, "loan_amount": 200000},
                    "minimal_changes_needed": {"income": 50000, "credit_score": 650}
                },
                "explanation_query": "What would need to change for this application to be approved?",
                "target_audience": "general",
                "fidelity_requirements": {"actionability": 0.9, "minimality": 0.8}
            }
        ]
        
        all_task_data = local_tasks + global_tasks + counterfactual_tasks
        
        for task_data in all_task_data:
            tasks.append(ExplainabilityTask(
                task_id=task_data["task_id"],
                explanation_type=task_data["explanation_type"],
                model_decision=task_data["model_decision"],
                input_data=task_data["input_data"],
                explanation_query=task_data["explanation_query"],
                target_audience=task_data["target_audience"],
                fidelity_requirements=task_data["fidelity_requirements"]
            ))
        
        return tasks
    
    # Evaluation methods
    
    def _evaluate_symbol_grounding(self, grounding_mappings: Dict[str, Any], 
                                  grounding_targets: Dict[str, Any], 
                                  confidence_scores: Dict[str, float], 
                                  task: SymbolGroundingTask) -> float:
        """Evaluate symbol grounding quality"""
        mapping_score = self._assess_mapping_accuracy(grounding_mappings, grounding_targets)
        confidence_score = self._assess_confidence_calibration(confidence_scores, grounding_mappings, grounding_targets)
        
        return (mapping_score * 0.8) + (confidence_score * 0.2)
    
    def _evaluate_concept_formation(self, formed_concept: Dict[str, Any], 
                                   target_concept: Dict[str, Any], 
                                   concept_representation: Dict[str, Any], 
                                   task: ConceptFormationTask) -> float:
        """Evaluate concept formation quality"""
        accuracy_score = self._assess_concept_accuracy(formed_concept, target_concept)
        representation_score = self._assess_representation_quality(concept_representation, task)
        
        return (accuracy_score * 0.7) + (representation_score * 0.3)
    
    def _evaluate_abstract_reasoning(self, answer: Any, correct_answer: Any, 
                                    symbolic_explanation: str, reasoning_steps: List[str], 
                                    task: AbstractReasoningTask) -> float:
        """Evaluate abstract reasoning quality"""
        correctness_score = 100 if answer == correct_answer else 0
        explanation_score = self._assess_explanation_quality(symbolic_explanation, task)
        reasoning_score = self._assess_reasoning_process(reasoning_steps, task)
        
        return (correctness_score * 0.6) + (explanation_score * 0.2) + (reasoning_score * 0.2)
    
    def _evaluate_explainability(self, explanation: str, fidelity_score: float, 
                                interpretability_score: float, evidence: List[str], 
                                task: ExplainabilityTask) -> float:
        """Evaluate explainability quality"""
        completeness_score = self._assess_explanation_completeness(explanation, task)
        accuracy_score = self._assess_explanation_accuracy(explanation, evidence, task)
        interpretability = min(100, interpretability_score * 100)
        fidelity = min(100, fidelity_score * 100)
        
        return (completeness_score * 0.3) + (accuracy_score * 0.3) + (interpretability * 0.2) + (fidelity * 0.2)
    
    # Assessment helper methods
    
    def _extract_modality_from_test_set(self, test_set: str) -> str:
        """Extract modality from test set name"""
        if "visual" in test_set:
            return "visual"
        elif "linguistic" in test_set:
            return "linguistic"
        elif "sensorimotor" in test_set:
            return "sensorimotor"
        else:
            return "cross_modal"
    
    def _assess_mapping_accuracy(self, grounding_mappings: Dict[str, Any], 
                                grounding_targets: Dict[str, Any]) -> float:
        """Assess accuracy of symbol-to-perception mappings"""
        if not grounding_mappings or not grounding_targets:
            return 0
        
        correct_mappings = 0
        total_symbols = len(grounding_targets)
        
        for symbol, target_mapping in grounding_targets.items():
            if symbol in grounding_mappings:
                predicted_mapping = grounding_mappings[symbol]
                
                # Simple overlap-based assessment
                if isinstance(target_mapping, dict) and isinstance(predicted_mapping, dict):
                    overlap = len(set(target_mapping.keys()).intersection(set(predicted_mapping.keys())))
                    total_keys = len(set(target_mapping.keys()).union(set(predicted_mapping.keys())))
                    if total_keys > 0 and overlap / total_keys > 0.5:
                        correct_mappings += 1
                elif predicted_mapping == target_mapping:
                    correct_mappings += 1
        
        return (correct_mappings / total_symbols) * 100 if total_symbols > 0 else 0
    
    def _assess_abstraction_quality(self, abstraction_hierarchy: Dict[str, Any], 
                                   task: SymbolGroundingTask) -> float:
        """Assess quality of abstraction hierarchy"""
        if not abstraction_hierarchy:
            return 50  # Default score if no hierarchy provided
        
        # Check for appropriate abstraction levels
        expected_levels = ["perceptual", "conceptual", "symbolic"]
        hierarchy_levels = list(abstraction_hierarchy.keys())
        
        level_coverage = len(set(hierarchy_levels).intersection(set(expected_levels)))
        max_coverage = len(expected_levels)
        
        return (level_coverage / max_coverage) * 100 if max_coverage > 0 else 50
    
    def _assess_cross_modal_consistency(self, response: Dict[str, Any], 
                                       task: SymbolGroundingTask) -> float:
        """Assess consistency across modalities"""
        if task.modality != GroundingModality.CROSS_MODAL:
            return 100  # Not applicable for single modality
        
        grounding_mappings = response.get("grounding_mappings", {})
        
        # Simple consistency check: symbols should have mappings to multiple modalities
        cross_modal_symbols = 0
        total_symbols = len(grounding_mappings)
        
        for symbol, mapping in grounding_mappings.items():
            if isinstance(mapping, dict):
                modality_count = sum(1 for key in mapping.keys() if key in ["visual", "auditory", "textual"])
                if modality_count > 1:
                    cross_modal_symbols += 1
        
        return (cross_modal_symbols / total_symbols) * 100 if total_symbols > 0 else 0
    
    def _assess_confidence_calibration(self, confidence_scores: Dict[str, float], 
                                      grounding_mappings: Dict[str, Any], 
                                      grounding_targets: Dict[str, Any]) -> float:
        """Assess calibration of confidence scores"""
        if not confidence_scores:
            return 50  # Default score
        
        calibration_score = 0
        total_assessments = 0
        
        for symbol in grounding_targets.keys():
            if symbol in confidence_scores and symbol in grounding_mappings:
                confidence = confidence_scores[symbol]
                # Simple heuristic: high confidence should correlate with correct mappings
                mapping_correct = self._is_mapping_correct(grounding_mappings[symbol], grounding_targets[symbol])
                
                if (mapping_correct and confidence > 0.7) or (not mapping_correct and confidence < 0.5):
                    calibration_score += 1
                total_assessments += 1
        
        return (calibration_score / total_assessments) * 100 if total_assessments > 0 else 50
    
    def _assess_concept_accuracy(self, formed_concept: Dict[str, Any], 
                                target_concept: Dict[str, Any]) -> float:
        """Assess accuracy of formed concept"""
        if not formed_concept or not target_concept:
            return 0
        
        # Check overlap in concept structure
        if isinstance(formed_concept, dict) and isinstance(target_concept, dict):
            formed_keys = set(formed_concept.keys())
            target_keys = set(target_concept.keys())
            
            key_overlap = len(formed_keys.intersection(target_keys))
            total_keys = len(formed_keys.union(target_keys))
            
            return (key_overlap / total_keys) * 100 if total_keys > 0 else 0
        
        return 50  # Default score for other types
    
    def _assess_representation_quality(self, concept_representation: Dict[str, Any], 
                                      task: ConceptFormationTask) -> float:
        """Assess quality of concept representation"""
        if not concept_representation:
            return 0
        
        quality_score = 0
        
        # Check for appropriate representation elements
        if task.hierarchical and "hierarchy" in concept_representation:
            quality_score += 30
        
        if task.compositional and "composition" in concept_representation:
            quality_score += 30
        
        # Check for features and structure
        if "features" in concept_representation or "prototype" in concept_representation:
            quality_score += 40
        
        return min(100, quality_score)
    
    def _assess_generalization_ability(self, generalization_rules: List[str], 
                                      task: ConceptFormationTask) -> float:
        """Assess generalization ability of formed concept"""
        if not generalization_rules:
            return 0
        
        # Simple assessment based on presence of generalization rules
        rule_quality_score = len(generalization_rules) * 20  # Up to 5 rules
        
        # Check for generalization keywords
        generalization_terms = ["all", "any", "general", "pattern", "rule", "applies"]
        term_count = sum(1 for rule in generalization_rules 
                        for term in generalization_terms 
                        if term in rule.lower())
        
        term_score = min(50, term_count * 10)
        
        return min(100, rule_quality_score + term_score)
    
    def _assess_explanation_quality(self, explanation: str, task: AbstractReasoningTask) -> float:
        """Assess quality of symbolic explanation"""
        if not explanation:
            return 0
        
        # Check for reasoning keywords
        reasoning_terms = ["pattern", "rule", "because", "therefore", "relationship", "transform"]
        explanation_lower = explanation.lower()
        
        term_count = sum(1 for term in reasoning_terms if term in explanation_lower)
        term_score = min(60, term_count * 10)
        
        # Check for task-specific concepts
        task_specific_score = 0
        if task.task_type == "ravens_matrices" and any(word in explanation_lower for word in ["matrix", "progression", "pattern"]):
            task_specific_score = 40
        elif task.task_type == "bongard_problems" and any(word in explanation_lower for word in ["rule", "distinguish", "category"]):
            task_specific_score = 40
        
        return term_score + task_specific_score
    
    def _assess_neural_symbolic_integration(self, response: Dict[str, Any], 
                                           task: AbstractReasoningTask) -> float:
        """Assess integration between neural and symbolic processing"""
        neural_representation = response.get("neural_representation", {})
        symbolic_explanation = response.get("symbolic_explanation", "")
        
        integration_score = 0
        
        # Check if both neural and symbolic components are present
        if neural_representation and symbolic_explanation:
            integration_score += 50
        
        # Check for cross-references between neural and symbolic components
        if neural_representation and symbolic_explanation:
            # Simple heuristic: look for connections
            explanation_lower = symbolic_explanation.lower()
            neural_terms = ["feature", "representation", "pattern", "neural"]
            
            if any(term in explanation_lower for term in neural_terms):
                integration_score += 50
        
        return integration_score
    
    def _assess_reasoning_process(self, reasoning_steps: List[str], task: AbstractReasoningTask) -> float:
        """Assess quality of reasoning process"""
        if not reasoning_steps:
            return 0
        
        # Check for systematic reasoning
        step_quality = len(reasoning_steps) * 15  # Up to ~6 steps for full score
        
        # Check for logical structure
        logical_terms = ["first", "then", "next", "finally", "step", "analyze"]
        logical_count = sum(1 for step in reasoning_steps 
                           for term in logical_terms 
                           if term in step.lower())
        
        logical_score = min(40, logical_count * 10)
        
        return min(100, step_quality + logical_score)
    
    def _assess_explanation_completeness(self, explanation: str, task: ExplainabilityTask) -> float:
        """Assess completeness of explanation"""
        if not explanation:
            return 0
        
        # Check for explanation components based on type
        completeness_score = 0
        explanation_lower = explanation.lower()
        
        if task.explanation_type == "local":
            required_elements = ["feature", "important", "contribute", "decision"]
            present_elements = sum(1 for element in required_elements if element in explanation_lower)
            completeness_score = (present_elements / len(required_elements)) * 100
        
        elif task.explanation_type == "global":
            required_elements = ["model", "behavior", "pattern", "general"]
            present_elements = sum(1 for element in required_elements if element in explanation_lower)
            completeness_score = (present_elements / len(required_elements)) * 100
        
        elif task.explanation_type == "counterfactual":
            required_elements = ["change", "different", "would", "if"]
            present_elements = sum(1 for element in required_elements if element in explanation_lower)
            completeness_score = (present_elements / len(required_elements)) * 100
        
        return completeness_score
    
    def _assess_explanation_accuracy(self, explanation: str, evidence: List[str], 
                                    task: ExplainabilityTask) -> float:
        """Assess accuracy of explanation"""
        if not explanation or not evidence:
            return 50  # Default score
        
        # Check if explanation aligns with evidence
        explanation_lower = explanation.lower()
        evidence_alignment = 0
        
        for evidence_item in evidence:
            evidence_lower = evidence_item.lower()
            # Simple overlap check
            explanation_words = set(explanation_lower.split())
            evidence_words = set(evidence_lower.split())
            
            overlap = len(explanation_words.intersection(evidence_words))
            if overlap > 2:  # Threshold for meaningful overlap
                evidence_alignment += 1
        
        return (evidence_alignment / len(evidence)) * 100 if evidence else 50
    
    def _assess_human_understandability(self, explanation: str, task: ExplainabilityTask) -> float:
        """Assess human understandability of explanation"""
        if not explanation:
            return 0
        
        # Simple heuristics for understandability
        understandability_score = 0
        
        # Check length (not too short, not too long)
        word_count = len(explanation.split())
        if 10 <= word_count <= 100:
            understandability_score += 30
        
        # Check for technical vs general language based on target audience
        technical_terms = ["algorithm", "neural", "weight", "gradient", "optimization"]
        general_terms = ["because", "important", "affects", "shows", "indicates"]
        
        explanation_lower = explanation.lower()
        
        if task.target_audience == "general":
            general_count = sum(1 for term in general_terms if term in explanation_lower)
            technical_count = sum(1 for term in technical_terms if term in explanation_lower)
            
            if general_count > technical_count:
                understandability_score += 40
        else:  # technical audience
            technical_count = sum(1 for term in technical_terms if term in explanation_lower)
            if technical_count > 0:
                understandability_score += 40
        
        # Check for clear structure
        structure_indicators = ["first", "second", "because", "therefore", "for example"]
        structure_count = sum(1 for indicator in structure_indicators if indicator in explanation_lower)
        
        if structure_count > 0:
            understandability_score += 30
        
        return min(100, understandability_score)
    
    def _is_mapping_correct(self, predicted_mapping: Any, target_mapping: Any) -> bool:
        """Check if a mapping is correct"""
        if isinstance(predicted_mapping, dict) and isinstance(target_mapping, dict):
            overlap_keys = set(predicted_mapping.keys()).intersection(set(target_mapping.keys()))
            return len(overlap_keys) > 0
        
        return predicted_mapping == target_mapping