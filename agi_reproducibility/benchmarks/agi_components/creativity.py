"""
Creativity Benchmarks for AGI Component Benchmark Suite

Implements comprehensive creativity capability tests including:
- Novel problem solving (insight problems, ill-defined problems, open-ended challenges)
- Artistic generation (visual, musical, literary, multimodal)
- Conceptual combination (emergent, hybrid, relational)
- Divergent thinking (alternative uses, consequences, improvements)
"""

import random
import json
import time
from typing import Dict, List, Any, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import math

from .core import BaseBenchmark, AGISystem, BenchmarkResult


class CreativityDomain(Enum):
    VISUAL = "visual"
    MUSICAL = "musical"
    LITERARY = "literary"
    MULTIMODAL = "multimodal"
    CONCEPTUAL = "conceptual"
    PROBLEM_SOLVING = "problem_solving"


@dataclass
class CreativeProblem:
    """Represents a creative problem"""
    problem_id: str
    domain: CreativityDomain
    problem_type: str
    description: str
    constraints: List[str]
    evaluation_criteria: List[str]
    difficulty: str
    context: Dict[str, Any]


@dataclass
class ArtisticTask:
    """Represents an artistic generation task"""
    task_id: str
    modality: str  # visual, musical, literary, multimodal
    prompt: str
    style_requirements: List[str]
    technical_constraints: Dict[str, Any]
    evaluation_dimensions: List[str]


@dataclass
class ConceptualCombination:
    """Represents a conceptual combination task"""
    task_id: str
    concept_a: str
    concept_b: str
    combination_type: str  # emergent, hybrid, relational
    domain: str
    expected_properties: List[str]


@dataclass
class DivergentThinkingTask:
    """Represents a divergent thinking task"""
    task_id: str
    task_type: str  # alternative_uses, consequences, improvements
    stimulus: str
    time_limit: int  # seconds
    evaluation_criteria: List[str]


class CreativityBenchmarks(BaseBenchmark):
    """Comprehensive creativity benchmarks"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.creative_problems = self._generate_creative_problems()
        self.artistic_tasks = self._generate_artistic_tasks()
        self.conceptual_combinations = self._generate_conceptual_combinations()
        self.divergent_tasks = self._generate_divergent_tasks()
    
    def run_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run all creativity tests"""
        results = []
        
        # Novel problem solving tests
        if self.config.get("novel_problem_solving", {}).get("enabled", True):
            results.extend(self._run_problem_solving_tests(system))
        
        # Artistic generation tests
        if self.config.get("artistic_generation", {}).get("enabled", True):
            results.extend(self._run_artistic_tests(system))
        
        # Conceptual combination tests
        if self.config.get("conceptual_combination", {}).get("enabled", True):
            results.extend(self._run_conceptual_tests(system))
        
        # Divergent thinking tests
        if self.config.get("divergent_thinking", {}).get("enabled", True):
            results.extend(self._run_divergent_tests(system))
        
        return results
    
    def _run_problem_solving_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run novel problem solving tests"""
        results = []
        config = self.config.get("novel_problem_solving", {})
        
        for problem_type in config.get("problem_types", ["insight_problems"]):
            problems = [p for p in self.creative_problems if p.problem_type == problem_type]
            
            if problems:
                result = self._run_single_test(
                    lambda sys: self._test_novel_problem_solving(sys, problems, problem_type),
                    f"novel_problem_solving_{problem_type}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _run_artistic_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run artistic generation tests"""
        results = []
        config = self.config.get("artistic_generation", {})
        
        for modality in config.get("modalities", ["visual"]):
            tasks = [t for t in self.artistic_tasks if t.modality == modality]
            
            if tasks:
                result = self._run_single_test(
                    lambda sys: self._test_artistic_generation(sys, tasks, modality),
                    f"artistic_generation_{modality}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _run_conceptual_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run conceptual combination tests"""
        results = []
        config = self.config.get("conceptual_combination", {})
        
        for combination_type in config.get("combination_types", ["emergent"]):
            combinations = [c for c in self.conceptual_combinations if c.combination_type == combination_type]
            
            if combinations:
                result = self._run_single_test(
                    lambda sys: self._test_conceptual_combination(sys, combinations, combination_type),
                    f"conceptual_combination_{combination_type}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _run_divergent_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run divergent thinking tests"""
        results = []
        config = self.config.get("divergent_thinking", {})
        
        for test_type in config.get("test_types", ["alternative_uses"]):
            tasks = [t for t in self.divergent_tasks if t.task_type == test_type]
            
            if tasks:
                result = self._run_single_test(
                    lambda sys: self._test_divergent_thinking(sys, tasks, test_type),
                    f"divergent_thinking_{test_type}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _test_novel_problem_solving(self, system: AGISystem, problems: List[CreativeProblem], 
                                   problem_type: str) -> Dict[str, Any]:
        """Test novel problem solving capability"""
        details = {
            "problem_type": problem_type,
            "problems_tested": len(problems),
            "individual_results": []
        }
        
        total_score = 0
        
        for problem in problems:
            creativity_task = {
                "type": "novel_problem_solving",
                "problem_type": problem.problem_type,
                "description": problem.description,
                "constraints": problem.constraints,
                "domain": problem.domain.value,
                "context": problem.context,
                "instruction": "Please provide a creative solution to this problem"
            }
            
            try:
                start_time = time.time()
                response = system.process_creativity_task(creativity_task)
                solution_time = time.time() - start_time
                
                solution = response.get("solution", "")
                reasoning = response.get("reasoning", "")
                
                # Evaluate solution creativity
                creativity_score = self._evaluate_solution_creativity(
                    solution, problem, response
                )
                
                total_score += creativity_score
                
                details["individual_results"].append({
                    "problem_id": problem.problem_id,
                    "problem_type": problem.problem_type,
                    "difficulty": problem.difficulty,
                    "solution": solution,
                    "reasoning": reasoning,
                    "creativity_score": creativity_score,
                    "solution_time": solution_time,
                    "novelty": self._assess_novelty(solution, problem),
                    "appropriateness": self._assess_appropriateness(solution, problem),
                    "elaboration": self._assess_elaboration(solution, reasoning)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "problem_id": problem.problem_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(problems) if problems else 0
        details["average_creativity_score"] = average_score
        
        # Test domain generalization if enabled
        if self.config.get("novel_problem_solving", {}).get("domain_generalization", False):
            generalization_score = self._test_problem_solving_generalization(system, problems)
            details["generalization_score"] = generalization_score
            # Weight generalization in final score
            final_score = (average_score * 0.8) + (generalization_score * 0.2)
        else:
            final_score = average_score
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_artistic_generation(self, system: AGISystem, tasks: List[ArtisticTask], 
                                 modality: str) -> Dict[str, Any]:
        """Test artistic generation capability"""
        details = {
            "modality": modality,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            artistic_task = {
                "type": "artistic_generation",
                "modality": task.modality,
                "prompt": task.prompt,
                "style_requirements": task.style_requirements,
                "technical_constraints": task.technical_constraints,
                "instruction": "Please create an artistic work based on this prompt"
            }
            
            try:
                start_time = time.time()
                response = system.process_creativity_task(artistic_task)
                generation_time = time.time() - start_time
                
                artwork = response.get("artwork", "")
                description = response.get("description", "")
                artistic_choices = response.get("artistic_choices", {})
                
                # Evaluate artistic quality
                artistic_score = self._evaluate_artistic_quality(
                    artwork, task, response
                )
                
                total_score += artistic_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "modality": task.modality,
                    "prompt": task.prompt,
                    "artwork": artwork[:500] if isinstance(artwork, str) else str(artwork)[:500],  # Truncate for storage
                    "description": description,
                    "artistic_score": artistic_score,
                    "generation_time": generation_time,
                    "aesthetic_quality": self._assess_aesthetic_quality(artwork, task),
                    "style_adherence": self._assess_style_adherence(artwork, task),
                    "originality": self._assess_artistic_originality(artwork, task),
                    "coherence": self._assess_artistic_coherence(artwork, description)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_artistic_score"] = average_score
        
        # Test style transfer if enabled
        if self.config.get("artistic_generation", {}).get("style_transfer", False):
            style_transfer_score = self._test_style_transfer(system, tasks)
            details["style_transfer_score"] = style_transfer_score
            # Weight style transfer in final score
            final_score = (average_score * 0.8) + (style_transfer_score * 0.2)
        else:
            final_score = average_score
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_conceptual_combination(self, system: AGISystem, combinations: List[ConceptualCombination], 
                                    combination_type: str) -> Dict[str, Any]:
        """Test conceptual combination capability"""
        details = {
            "combination_type": combination_type,
            "combinations_tested": len(combinations),
            "individual_results": []
        }
        
        total_score = 0
        
        for combination in combinations:
            conceptual_task = {
                "type": "conceptual_combination",
                "concept_a": combination.concept_a,
                "concept_b": combination.concept_b,
                "combination_type": combination.combination_type,
                "domain": combination.domain,
                "instruction": f"Please combine these concepts in a {combination.combination_type} way"
            }
            
            try:
                start_time = time.time()
                response = system.process_creativity_task(conceptual_task)
                combination_time = time.time() - start_time
                
                combined_concept = response.get("combined_concept", "")
                properties = response.get("properties", [])
                reasoning = response.get("reasoning", "")
                
                # Evaluate conceptual combination
                combination_score = self._evaluate_conceptual_combination(
                    combined_concept, combination, response
                )
                
                total_score += combination_score
                
                details["individual_results"].append({
                    "task_id": combination.task_id,
                    "concept_a": combination.concept_a,
                    "concept_b": combination.concept_b,
                    "combination_type": combination.combination_type,
                    "combined_concept": combined_concept,
                    "properties": properties,
                    "reasoning": reasoning,
                    "combination_score": combination_score,
                    "combination_time": combination_time,
                    "novelty": self._assess_conceptual_novelty(combined_concept, combination),
                    "coherence": self._assess_conceptual_coherence(combined_concept, properties),
                    "emergent_properties": self._assess_emergent_properties(properties, combination)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": combination.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(combinations) if combinations else 0
        details["average_combination_score"] = average_score
        
        # Test cross-domain combinations if enabled
        if self.config.get("conceptual_combination", {}).get("cross_domain", False):
            cross_domain_score = self._test_cross_domain_combinations(system, combinations)
            details["cross_domain_score"] = cross_domain_score
            # Weight cross-domain combinations in final score
            final_score = (average_score * 0.8) + (cross_domain_score * 0.2)
        else:
            final_score = average_score
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_divergent_thinking(self, system: AGISystem, tasks: List[DivergentThinkingTask], 
                                test_type: str) -> Dict[str, Any]:
        """Test divergent thinking capability"""
        details = {
            "test_type": test_type,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            divergent_task = {
                "type": "divergent_thinking",
                "task_type": task.task_type,
                "stimulus": task.stimulus,
                "time_limit": task.time_limit,
                "instruction": f"Generate as many {task.task_type} as possible for: {task.stimulus}"
            }
            
            try:
                start_time = time.time()
                response = system.process_creativity_task(divergent_task)
                thinking_time = time.time() - start_time
                
                ideas = response.get("ideas", [])
                
                # Evaluate divergent thinking
                divergent_score = self._evaluate_divergent_thinking(
                    ideas, task, thinking_time
                )
                
                total_score += divergent_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "stimulus": task.stimulus,
                    "ideas": ideas,
                    "divergent_score": divergent_score,
                    "thinking_time": thinking_time,
                    "fluency": len(ideas),
                    "flexibility": self._assess_flexibility(ideas),
                    "originality": self._assess_idea_originality(ideas, task),
                    "elaboration": self._assess_idea_elaboration(ideas)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_divergent_score"] = average_score
        
        # Test fluency measures if enabled
        if self.config.get("divergent_thinking", {}).get("fluency_measures", False):
            fluency_analysis = self._analyze_fluency_patterns(details["individual_results"])
            details["fluency_analysis"] = fluency_analysis
        
        return {
            "score": average_score,
            "success": average_score > 0,
            "details": details
        }
    
    def _generate_creative_problems(self) -> List[CreativeProblem]:
        """Generate creative problem solving tasks"""
        problems = []
        
        # Insight problems
        insight_problems = [
            {
                "problem_id": "candle_problem",
                "problem_type": "insight_problems",
                "description": "You have a candle, a box of thumbtacks, and a book of matches. How can you attach the candle to the wall so it doesn't drip wax on the floor?",
                "constraints": ["Cannot damage wall permanently", "Must prevent wax dripping"],
                "evaluation_criteria": ["functional_solution", "creative_use_of_materials", "insight_required"],
                "difficulty": "intermediate",
                "context": {"materials": ["candle", "thumbtacks", "matches"], "goal": "wall_mounting"}
            },
            {
                "problem_id": "nine_dots",
                "problem_type": "insight_problems", 
                "description": "Connect all nine dots arranged in a 3x3 grid using only four straight lines without lifting your pen.",
                "constraints": ["Four lines only", "No lifting pen", "All dots must be connected"],
                "evaluation_criteria": ["constraint_satisfaction", "thinking_outside_box", "geometric_insight"],
                "difficulty": "advanced",
                "context": {"grid_size": "3x3", "lines_allowed": 4}
            }
        ]
        
        # Ill-defined problems
        ill_defined_problems = [
            {
                "problem_id": "traffic_congestion",
                "problem_type": "ill_defined_problems",
                "description": "Design a creative solution to reduce traffic congestion in a major city.",
                "constraints": ["Budget limitations", "Environmental impact", "Public acceptance"],
                "evaluation_criteria": ["innovation", "feasibility", "comprehensive_approach", "sustainability"],
                "difficulty": "advanced",
                "context": {"domain": "urban_planning", "stakeholders": ["citizens", "government", "businesses"]}
            },
            {
                "problem_id": "plastic_waste",
                "problem_type": "ill_defined_problems",
                "description": "Propose an innovative approach to address plastic waste in oceans.",
                "constraints": ["Cost effectiveness", "Scalability", "Marine ecosystem protection"],
                "evaluation_criteria": ["environmental_impact", "technological_innovation", "global_applicability"],
                "difficulty": "advanced",
                "context": {"domain": "environmental", "scope": "global"}
            }
        ]
        
        all_problem_data = insight_problems + ill_defined_problems
        
        for problem_data in all_problem_data:
            problems.append(CreativeProblem(
                problem_id=problem_data["problem_id"],
                domain=CreativityDomain.PROBLEM_SOLVING,
                problem_type=problem_data["problem_type"],
                description=problem_data["description"],
                constraints=problem_data["constraints"],
                evaluation_criteria=problem_data["evaluation_criteria"],
                difficulty=problem_data["difficulty"],
                context=problem_data["context"]
            ))
        
        return problems
    
    def _generate_artistic_tasks(self) -> List[ArtisticTask]:
        """Generate artistic generation tasks"""
        tasks = []
        
        # Visual art tasks
        visual_tasks = [
            {
                "task_id": "abstract_landscape",
                "modality": "visual",
                "prompt": "Create an abstract representation of a sunset over mountains",
                "style_requirements": ["abstract", "expressive", "color_harmony"],
                "technical_constraints": {"resolution": "512x512", "color_palette": "warm_tones"},
                "evaluation_dimensions": ["composition", "color_use", "emotional_impact", "abstraction_level"]
            },
            {
                "task_id": "surreal_portrait",
                "modality": "visual",
                "prompt": "Design a surreal portrait that combines human and nature elements",
                "style_requirements": ["surreal", "imaginative", "symbolic"],
                "technical_constraints": {"style": "digital_art", "elements": ["human_features", "natural_elements"]},
                "evaluation_dimensions": ["surreal_quality", "symbolic_meaning", "technical_skill", "originality"]
            }
        ]
        
        # Literary tasks
        literary_tasks = [
            {
                "task_id": "short_story_twist",
                "modality": "literary",
                "prompt": "Write a short story with an unexpected twist ending about a time traveler",
                "style_requirements": ["narrative_structure", "character_development", "plot_twist"],
                "technical_constraints": {"length": "500-800_words", "genre": "science_fiction"},
                "evaluation_dimensions": ["plot_coherence", "character_depth", "twist_effectiveness", "writing_quality"]
            },
            {
                "task_id": "experimental_poem",
                "modality": "literary",
                "prompt": "Compose an experimental poem about the concept of digital consciousness",
                "style_requirements": ["experimental_form", "metaphorical_language", "conceptual_depth"],
                "technical_constraints": {"form": "free_verse", "theme": "digital_consciousness"},
                "evaluation_dimensions": ["linguistic_creativity", "conceptual_innovation", "emotional_resonance", "form_experimentation"]
            }
        ]
        
        # Musical tasks
        musical_tasks = [
            {
                "task_id": "ambient_soundscape",
                "modality": "musical",
                "prompt": "Compose an ambient soundscape that evokes the feeling of floating in space",
                "style_requirements": ["ambient", "atmospheric", "spacious"],
                "technical_constraints": {"duration": "3-5_minutes", "instruments": ["synthesizers", "field_recordings"]},
                "evaluation_dimensions": ["atmospheric_quality", "sonic_texture", "emotional_evocation", "compositional_structure"]
            }
        ]
        
        all_task_data = visual_tasks + literary_tasks + musical_tasks
        
        for task_data in all_task_data:
            tasks.append(ArtisticTask(
                task_id=task_data["task_id"],
                modality=task_data["modality"],
                prompt=task_data["prompt"],
                style_requirements=task_data["style_requirements"],
                technical_constraints=task_data["technical_constraints"],
                evaluation_dimensions=task_data["evaluation_dimensions"]
            ))
        
        return tasks
    
    def _generate_conceptual_combinations(self) -> List[ConceptualCombination]:
        """Generate conceptual combination tasks"""
        combinations = []
        
        # Emergent combinations
        emergent_combinations = [
            {
                "task_id": "bird_machine",
                "concept_a": "bird",
                "concept_b": "machine",
                "combination_type": "emergent",
                "domain": "hybrid_entities",
                "expected_properties": ["flight_capability", "mechanical_precision", "organic_grace"]
            },
            {
                "task_id": "library_garden",
                "concept_a": "library",
                "concept_b": "garden",
                "combination_type": "emergent",
                "domain": "spaces",
                "expected_properties": ["knowledge_growth", "peaceful_learning", "natural_wisdom"]
            }
        ]
        
        # Hybrid combinations
        hybrid_combinations = [
            {
                "task_id": "smartphone_telescope",
                "concept_a": "smartphone",
                "concept_b": "telescope",
                "combination_type": "hybrid",
                "domain": "technology",
                "expected_properties": ["portable_astronomy", "digital_observation", "communication_cosmos"]
            },
            {
                "task_id": "kitchen_laboratory",
                "concept_a": "kitchen",
                "concept_b": "laboratory",
                "combination_type": "hybrid",
                "domain": "functional_spaces",
                "expected_properties": ["culinary_experimentation", "precise_measurement", "innovative_cooking"]
            }
        ]
        
        all_combination_data = emergent_combinations + hybrid_combinations
        
        for combo_data in all_combination_data:
            combinations.append(ConceptualCombination(
                task_id=combo_data["task_id"],
                concept_a=combo_data["concept_a"],
                concept_b=combo_data["concept_b"],
                combination_type=combo_data["combination_type"],
                domain=combo_data["domain"],
                expected_properties=combo_data["expected_properties"]
            ))
        
        return combinations
    
    def _generate_divergent_tasks(self) -> List[DivergentThinkingTask]:
        """Generate divergent thinking tasks"""
        tasks = []
        
        # Alternative uses tasks
        alternative_uses_tasks = [
            {
                "task_id": "brick_uses",
                "task_type": "alternative_uses",
                "stimulus": "brick",
                "time_limit": 180,
                "evaluation_criteria": ["fluency", "flexibility", "originality", "elaboration"]
            },
            {
                "task_id": "paperclip_uses",
                "task_type": "alternative_uses",
                "stimulus": "paperclip",
                "time_limit": 180,
                "evaluation_criteria": ["fluency", "flexibility", "originality", "elaboration"]
            }
        ]
        
        # Consequences tasks
        consequences_tasks = [
            {
                "task_id": "gravity_disappears",
                "task_type": "consequences",
                "stimulus": "What would happen if gravity suddenly disappeared?",
                "time_limit": 240,
                "evaluation_criteria": ["logical_reasoning", "imagination", "comprehensive_thinking", "originality"]
            },
            {
                "task_id": "animals_talk",
                "task_type": "consequences", 
                "stimulus": "What would happen if all animals could suddenly talk?",
                "time_limit": 240,
                "evaluation_criteria": ["social_implications", "practical_consequences", "creative_scenarios", "depth_of_thinking"]
            }
        ]
        
        # Improvements tasks
        improvements_tasks = [
            {
                "task_id": "improve_umbrella",
                "task_type": "improvements",
                "stimulus": "How would you improve the design of an umbrella?",
                "time_limit": 180,
                "evaluation_criteria": ["practicality", "innovation", "problem_identification", "solution_quality"]
            }
        ]
        
        all_task_data = alternative_uses_tasks + consequences_tasks + improvements_tasks
        
        for task_data in all_task_data:
            tasks.append(DivergentThinkingTask(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                stimulus=task_data["stimulus"],
                time_limit=task_data["time_limit"],
                evaluation_criteria=task_data["evaluation_criteria"]
            ))
        
        return tasks
    
    def _evaluate_solution_creativity(self, solution: str, problem: CreativeProblem, 
                                     response: Dict[str, Any]) -> float:
        """Evaluate creativity of a problem solution"""
        if not solution:
            return 0
        
        novelty_score = self._assess_novelty(solution, problem)
        appropriateness_score = self._assess_appropriateness(solution, problem)
        elaboration_score = self._assess_elaboration(solution, response.get("reasoning", ""))
        
        # Weighted combination of creativity dimensions
        creativity_score = (novelty_score * 0.4) + (appropriateness_score * 0.4) + (elaboration_score * 0.2)
        
        return creativity_score
    
    def _evaluate_artistic_quality(self, artwork: Any, task: ArtisticTask, 
                                  response: Dict[str, Any]) -> float:
        """Evaluate quality of artistic generation"""
        if not artwork:
            return 0
        
        aesthetic_score = self._assess_aesthetic_quality(artwork, task)
        style_score = self._assess_style_adherence(artwork, task)
        originality_score = self._assess_artistic_originality(artwork, task)
        coherence_score = self._assess_artistic_coherence(artwork, response.get("description", ""))
        
        # Weighted combination of artistic dimensions
        artistic_score = (aesthetic_score * 0.3) + (style_score * 0.2) + (originality_score * 0.3) + (coherence_score * 0.2)
        
        return artistic_score
    
    def _evaluate_conceptual_combination(self, combined_concept: str, combination: ConceptualCombination, 
                                        response: Dict[str, Any]) -> float:
        """Evaluate quality of conceptual combination"""
        if not combined_concept:
            return 0
        
        novelty_score = self._assess_conceptual_novelty(combined_concept, combination)
        coherence_score = self._assess_conceptual_coherence(combined_concept, response.get("properties", []))
        emergent_score = self._assess_emergent_properties(response.get("properties", []), combination)
        
        # Weighted combination of conceptual dimensions
        combination_score = (novelty_score * 0.4) + (coherence_score * 0.3) + (emergent_score * 0.3)
        
        return combination_score
    
    def _evaluate_divergent_thinking(self, ideas: List[str], task: DivergentThinkingTask, 
                                    thinking_time: float) -> float:
        """Evaluate quality of divergent thinking"""
        if not ideas:
            return 0
        
        fluency_score = min(100, len(ideas) * 5)  # Cap at 100, 5 points per idea
        flexibility_score = self._assess_flexibility(ideas)
        originality_score = self._assess_idea_originality(ideas, task)
        elaboration_score = self._assess_idea_elaboration(ideas)
        
        # Time efficiency bonus (faster generation gets slight bonus)
        time_bonus = max(0, (task.time_limit - thinking_time) / task.time_limit * 10)
        
        # Weighted combination of divergent thinking dimensions
        divergent_score = (fluency_score * 0.25) + (flexibility_score * 0.25) + (originality_score * 0.35) + (elaboration_score * 0.15) + time_bonus
        
        return min(100, divergent_score)
    
    def _assess_novelty(self, solution: str, problem: CreativeProblem) -> float:
        """Assess novelty/originality of a solution"""
        # Simplified novelty assessment based on keyword uniqueness and unconventional approaches
        if not solution:
            return 0
        
        solution_words = set(solution.lower().split())
        common_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        unique_words = solution_words - common_words
        
        # Check for unconventional thinking indicators
        creativity_indicators = ["innovative", "unique", "unexpected", "unusual", "creative", "novel", "original"]
        unconventional_indicators = ["alternative", "different", "reverse", "opposite", "combine", "transform"]
        
        indicator_count = sum(1 for word in unique_words if word in creativity_indicators + unconventional_indicators)
        
        # Basic novelty score based on vocabulary richness and creativity indicators
        vocabulary_richness = min(100, len(unique_words) * 3)
        indicator_bonus = indicator_count * 10
        
        return min(100, vocabulary_richness + indicator_bonus)
    
    def _assess_appropriateness(self, solution: str, problem: CreativeProblem) -> float:
        """Assess appropriateness/relevance of a solution"""
        if not solution:
            return 0
        
        solution_lower = solution.lower()
        
        # Check if solution addresses key problem elements
        problem_keywords = set()
        for word in problem.description.lower().split():
            if len(word) > 3 and word not in {"the", "and", "for", "with", "this", "that"}:
                problem_keywords.add(word)
        
        solution_words = set(solution_lower.split())
        keyword_overlap = len(problem_keywords.intersection(solution_words))
        
        # Check constraint satisfaction
        constraint_satisfaction = 0
        for constraint in problem.constraints:
            constraint_words = set(constraint.lower().split())
            if constraint_words.intersection(solution_words):
                constraint_satisfaction += 1
        
        # Appropriateness score
        keyword_score = (keyword_overlap / len(problem_keywords)) * 60 if problem_keywords else 0
        constraint_score = (constraint_satisfaction / len(problem.constraints)) * 40 if problem.constraints else 40
        
        return keyword_score + constraint_score
    
    def _assess_elaboration(self, solution: str, reasoning: str) -> float:
        """Assess elaboration/detail level of a solution"""
        if not solution:
            return 0
        
        # Combine solution and reasoning for elaboration assessment
        full_text = solution + " " + reasoning
        
        # Count sentences, details, and explanatory elements
        sentences = len([s for s in full_text.split('.') if s.strip()])
        words = len(full_text.split())
        
        # Look for detailed explanations
        detail_indicators = ["because", "therefore", "specifically", "for example", "such as", "including", "details", "step"]
        detail_count = sum(1 for word in full_text.lower().split() if word in detail_indicators)
        
        # Elaboration score based on length and detail indicators
        length_score = min(50, words / 10)  # Up to 50 points for word count
        detail_score = min(50, detail_count * 10)  # Up to 50 points for detail indicators
        
        return length_score + detail_score
    
    def _assess_aesthetic_quality(self, artwork: Any, task: ArtisticTask) -> float:
        """Assess aesthetic quality of artwork (simplified)"""
        # This is a simplified assessment - in practice would need domain-specific evaluation
        if isinstance(artwork, str):
            # For textual descriptions of artwork
            aesthetic_words = ["beautiful", "elegant", "harmonious", "balanced", "striking", "vivid", "expressive", "graceful"]
            artwork_lower = artwork.lower()
            aesthetic_indicators = sum(1 for word in aesthetic_words if word in artwork_lower)
            
            # Length and descriptive richness
            descriptive_score = min(60, len(artwork.split()) * 2)
            aesthetic_score = min(40, aesthetic_indicators * 8)
            
            return descriptive_score + aesthetic_score
        
        return 50  # Default score for non-textual artwork
    
    def _assess_style_adherence(self, artwork: Any, task: ArtisticTask) -> float:
        """Assess adherence to style requirements"""
        if isinstance(artwork, str) and task.style_requirements:
            artwork_lower = artwork.lower()
            style_matches = 0
            
            for style_req in task.style_requirements:
                if style_req.lower() in artwork_lower:
                    style_matches += 1
            
            return (style_matches / len(task.style_requirements)) * 100 if task.style_requirements else 50
        
        return 50  # Default score
    
    def _assess_artistic_originality(self, artwork: Any, task: ArtisticTask) -> float:
        """Assess originality of artistic work"""
        if isinstance(artwork, str):
            # Look for original/creative elements in description
            originality_indicators = ["unique", "original", "innovative", "creative", "unusual", "unexpected", "new", "fresh"]
            artwork_lower = artwork.lower()
            originality_count = sum(1 for word in originality_indicators if word in artwork_lower)
            
            # Assess conceptual originality based on uncommon combinations
            words = artwork_lower.split()
            uncommon_combinations = 0
            for i in range(len(words) - 1):
                # Simple heuristic for unusual word combinations
                if len(words[i]) > 4 and len(words[i + 1]) > 4:
                    uncommon_combinations += 1
            
            originality_score = min(70, originality_count * 15)
            combination_score = min(30, uncommon_combinations * 5)
            
            return originality_score + combination_score
        
        return 50  # Default score
    
    def _assess_artistic_coherence(self, artwork: Any, description: str) -> float:
        """Assess coherence between artwork and description"""
        if isinstance(artwork, str) and description:
            # Check consistency between artwork description and artist's explanation
            artwork_words = set(artwork.lower().split())
            description_words = set(description.lower().split())
            
            overlap = len(artwork_words.intersection(description_words))
            total_unique = len(artwork_words.union(description_words))
            
            coherence_score = (overlap / total_unique) * 100 if total_unique > 0 else 0
            return coherence_score
        
        return 50  # Default score
    
    def _assess_conceptual_novelty(self, combined_concept: str, combination: ConceptualCombination) -> float:
        """Assess novelty of conceptual combination"""
        if not combined_concept:
            return 0
        
        # Check if combination creates new properties not present in original concepts
        concept_a_words = set(combination.concept_a.lower().split())
        concept_b_words = set(combination.concept_b.lower().split())
        original_words = concept_a_words.union(concept_b_words)
        
        combined_words = set(combined_concept.lower().split())
        new_words = combined_words - original_words
        
        # Remove common words
        common_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "a", "an"}
        meaningful_new_words = new_words - common_words
        
        novelty_score = min(100, len(meaningful_new_words) * 15)
        return novelty_score
    
    def _assess_conceptual_coherence(self, combined_concept: str, properties: List[str]) -> float:
        """Assess coherence of conceptual combination"""
        if not combined_concept or not properties:
            return 50
        
        # Check if properties logically relate to the combined concept
        concept_words = set(combined_concept.lower().split())
        property_overlap = 0
        
        for prop in properties:
            prop_words = set(prop.lower().split())
            if concept_words.intersection(prop_words):
                property_overlap += 1
        
        coherence_score = (property_overlap / len(properties)) * 100 if properties else 50
        return coherence_score
    
    def _assess_emergent_properties(self, properties: List[str], combination: ConceptualCombination) -> float:
        """Assess emergence of new properties in combination"""
        if not properties:
            return 0
        
        # Check for properties that go beyond simple addition of original concept properties
        expected_props = set(prop.lower() for prop in combination.expected_properties)
        generated_props = set(prop.lower() for prop in properties)
        
        # Score based on coverage of expected emergent properties
        coverage = len(expected_props.intersection(generated_props))
        coverage_score = (coverage / len(expected_props)) * 70 if expected_props else 0
        
        # Bonus for additional unexpected properties
        unexpected_props = generated_props - expected_props
        bonus_score = min(30, len(unexpected_props) * 10)
        
        return coverage_score + bonus_score
    
    def _assess_flexibility(self, ideas: List[str]) -> float:
        """Assess flexibility (number of different categories) in ideas"""
        if not ideas:
            return 0
        
        # Simple category classification based on keywords
        categories = {
            "functional": ["use", "tool", "function", "work", "operate"],
            "decorative": ["decorate", "ornament", "display", "beauty", "art"],
            "structural": ["build", "construct", "support", "foundation", "frame"],
            "recreational": ["play", "game", "fun", "entertainment", "sport"],
            "educational": ["learn", "teach", "study", "education", "knowledge"],
            "emergency": ["emergency", "survival", "rescue", "urgent", "crisis"]
        }
        
        idea_categories = set()
        for idea in ideas:
            idea_lower = idea.lower()
            for category, keywords in categories.items():
                if any(keyword in idea_lower for keyword in keywords):
                    idea_categories.add(category)
                    break
            else:
                idea_categories.add("other")
        
        flexibility_score = min(100, len(idea_categories) * 20)
        return flexibility_score
    
    def _assess_idea_originality(self, ideas: List[str], task: DivergentThinkingTask) -> float:
        """Assess originality of ideas"""
        if not ideas:
            return 0
        
        # Common/expected responses for different stimuli (simplified)
        common_responses = {
            "brick": ["build", "wall", "construction", "throw", "weight"],
            "paperclip": ["clip", "paper", "hold", "bend", "wire"]
        }
        
        stimulus_key = task.stimulus.lower()
        common_ideas = common_responses.get(stimulus_key, [])
        
        original_ideas = 0
        for idea in ideas:
            idea_lower = idea.lower()
            if not any(common in idea_lower for common in common_ideas):
                original_ideas += 1
        
        originality_score = (original_ideas / len(ideas)) * 100 if ideas else 0
        return originality_score
    
    def _assess_idea_elaboration(self, ideas: List[str]) -> float:
        """Assess elaboration level of ideas"""
        if not ideas:
            return 0
        
        total_elaboration = 0
        for idea in ideas:
            # Count words and detail indicators
            words = len(idea.split())
            detail_indicators = ["because", "by", "with", "using", "through", "specifically", "details"]
            details = sum(1 for word in idea.lower().split() if word in detail_indicators)
            
            idea_elaboration = min(20, words * 2 + details * 5)  # Cap per idea
            total_elaboration += idea_elaboration
        
        average_elaboration = total_elaboration / len(ideas)
        return min(100, average_elaboration)
    
    def _test_problem_solving_generalization(self, system: AGISystem, problems: List[CreativeProblem]) -> float:
        """Test generalization of problem-solving creativity across domains"""
        # Create modified versions of problems to test generalization
        generalization_score = 0
        tested_problems = 0
        
        for problem in problems[:2]:  # Test with first 2 problems
            modified_problem = self._create_modified_problem(problem)
            
            generalization_task = {
                "type": "problem_solving_generalization",
                "original_problem": problem.description,
                "modified_problem": modified_problem["description"],
                "instruction": "Solve this modified problem using insights from similar problems"
            }
            
            try:
                response = system.process_creativity_task(generalization_task)
                solution = response.get("solution", "")
                
                # Score based on solution quality and transfer of insights
                solution_quality = self._evaluate_solution_creativity(solution, problem, response)
                transfer_quality = self._assess_insight_transfer(solution, problem, modified_problem)
                
                generalization_score += (solution_quality + transfer_quality) / 2
                tested_problems += 1
            except:
                tested_problems += 1
        
        return generalization_score / tested_problems if tested_problems > 0 else 0
    
    def _test_style_transfer(self, system: AGISystem, tasks: List[ArtisticTask]) -> float:
        """Test style transfer capability in artistic generation"""
        if len(tasks) < 2:
            return 0
        
        style_transfer_task = {
            "type": "style_transfer",
            "content_prompt": tasks[0].prompt,
            "style_reference": tasks[1].style_requirements,
            "instruction": "Create artwork with the content of the first prompt in the style of the second"
        }
        
        try:
            response = system.process_creativity_task(style_transfer_task)
            artwork = response.get("artwork", "")
            
            # Evaluate style transfer quality
            content_preservation = self._assess_content_preservation(artwork, tasks[0])
            style_adoption = self._assess_style_adoption(artwork, tasks[1])
            
            return (content_preservation + style_adoption) / 2
        except:
            return 0
    
    def _test_cross_domain_combinations(self, system: AGISystem, combinations: List[ConceptualCombination]) -> float:
        """Test cross-domain conceptual combinations"""
        cross_domain_score = 0
        tested_combinations = 0
        
        # Create cross-domain combinations
        for i, combo in enumerate(combinations[:2]):
            if i + 1 < len(combinations):
                cross_combo = {
                    "concept_a": combo.concept_a,
                    "concept_b": combinations[i + 1].concept_b,
                    "domains": [combo.domain, combinations[i + 1].domain]
                }
                
                cross_domain_task = {
                    "type": "cross_domain_combination",
                    "concept_a": cross_combo["concept_a"],
                    "concept_b": cross_combo["concept_b"],
                    "domains": cross_combo["domains"],
                    "instruction": "Combine these concepts from different domains creatively"
                }
                
                try:
                    response = system.process_creativity_task(cross_domain_task)
                    combined_concept = response.get("combined_concept", "")
                    
                    # Score cross-domain integration
                    domain_integration = self._assess_domain_integration(combined_concept, cross_combo)
                    cross_domain_score += domain_integration
                    tested_combinations += 1
                except:
                    tested_combinations += 1
        
        return cross_domain_score / tested_combinations if tested_combinations > 0 else 0
    
    def _analyze_fluency_patterns(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze fluency patterns in divergent thinking"""
        fluencies = [result.get("fluency", 0) for result in results if "fluency" in result]
        
        if not fluencies:
            return {"error": "No fluency data available"}
        
        return {
            "average_fluency": sum(fluencies) / len(fluencies),
            "max_fluency": max(fluencies),
            "min_fluency": min(fluencies),
            "fluency_range": max(fluencies) - min(fluencies),
            "consistency": 1 - (max(fluencies) - min(fluencies)) / max(max(fluencies), 1)
        }
    
    def _create_modified_problem(self, original: CreativeProblem) -> Dict[str, Any]:
        """Create a modified version of a problem for generalization testing"""
        # Simple modification - change domain but keep structure
        domain_mappings = {
            "candle": "flashlight",
            "wall": "ceiling", 
            "thumbtacks": "magnets",
            "dots": "circles",
            "lines": "curves"
        }
        
        modified_description = original.description
        for old_word, new_word in domain_mappings.items():
            modified_description = modified_description.replace(old_word, new_word)
        
        return {
            "description": modified_description,
            "constraints": original.constraints,
            "domain": "modified_" + original.domain.value
        }
    
    def _assess_insight_transfer(self, solution: str, original_problem: CreativeProblem, 
                                modified_problem: Dict[str, Any]) -> float:
        """Assess quality of insight transfer between problems"""
        # Look for conceptual similarities in solutions that indicate insight transfer
        solution_concepts = set(solution.lower().split())
        
        # Check if solution shows understanding of underlying principles
        principle_indicators = ["similar", "same", "principle", "concept", "approach", "method", "strategy"]
        transfer_indicators = sum(1 for word in solution_concepts if word in principle_indicators)
        
        return min(100, transfer_indicators * 25)
    
    def _assess_content_preservation(self, artwork: Any, content_task: ArtisticTask) -> float:
        """Assess preservation of content in style transfer"""
        if isinstance(artwork, str):
            artwork_lower = artwork.lower()
            prompt_words = set(content_task.prompt.lower().split())
            artwork_words = set(artwork_lower.split())
            
            content_overlap = len(prompt_words.intersection(artwork_words))
            return (content_overlap / len(prompt_words)) * 100 if prompt_words else 0
        
        return 50  # Default score
    
    def _assess_style_adoption(self, artwork: Any, style_task: ArtisticTask) -> float:
        """Assess adoption of style in style transfer"""
        if isinstance(artwork, str):
            artwork_lower = artwork.lower()
            style_matches = 0
            
            for style_req in style_task.style_requirements:
                if style_req.lower() in artwork_lower:
                    style_matches += 1
            
            return (style_matches / len(style_task.style_requirements)) * 100 if style_task.style_requirements else 0
        
        return 50  # Default score
    
    def _assess_domain_integration(self, combined_concept: str, cross_combo: Dict[str, Any]) -> float:
        """Assess quality of cross-domain integration"""
        if not combined_concept:
            return 0
        
        # Check if both domains are represented in the combination
        domain_indicators = {
            "technology": ["digital", "electronic", "automated", "smart", "tech"],
            "nature": ["organic", "natural", "biological", "living", "growth"],
            "spaces": ["environment", "area", "place", "location", "space"],
            "functional": ["purpose", "function", "utility", "use", "tool"]
        }
        
        combined_lower = combined_concept.lower()
        domains_represented = 0
        
        for domain in cross_combo.get("domains", []):
            domain_words = domain_indicators.get(domain, [])
            if any(word in combined_lower for word in domain_words):
                domains_represented += 1
        
        integration_score = (domains_represented / len(cross_combo.get("domains", []))) * 100
        return integration_score