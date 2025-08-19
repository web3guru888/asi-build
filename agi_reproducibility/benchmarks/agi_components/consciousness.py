"""
Consciousness Benchmarks for AGI Component Benchmark Suite

Implements comprehensive consciousness capability tests including:
- Self-awareness (mirror test analogues, self-recognition, introspective reports)
- Metacognition (feeling of knowing, confidence judgments, strategy monitoring)
- Qualia indicators (subjective experience reports, phenomenological richness, binding problems)
- Theory of mind (false belief, mental state attribution, intentionality)

Note: These tests assess behavioral indicators of consciousness rather than consciousness itself,
as the hard problem of consciousness remains philosophically unsolved.
"""

import random
import time
import json
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .core import BaseBenchmark, AGISystem, BenchmarkResult


class ConsciousnessAspect(Enum):
    SELF_AWARENESS = "self_awareness"
    METACOGNITION = "metacognition"
    QUALIA = "qualia"
    THEORY_OF_MIND = "theory_of_mind"


@dataclass
class SelfAwarenessTask:
    """Represents a self-awareness task"""
    task_id: str
    task_type: str  # mirror_test, self_recognition, introspection
    description: str
    stimuli: Dict[str, Any]
    expected_indicators: List[str]
    evaluation_criteria: List[str]


@dataclass
class MetacognitionTask:
    """Represents a metacognition task"""
    task_id: str
    task_type: str  # feeling_of_knowing, confidence_judgment, strategy_monitoring
    problem: Dict[str, Any]
    metacognitive_question: str
    correct_response: Any
    confidence_required: bool


@dataclass
class QualiaTask:
    """Represents a qualia/subjective experience task"""
    task_id: str
    task_type: str  # experience_report, phenomenology, binding
    stimulus: Dict[str, Any]
    experience_query: str
    evaluation_dimensions: List[str]


@dataclass
class TheoryOfMindTask:
    """Represents a theory of mind task"""
    task_id: str
    task_type: str  # false_belief, mental_state, intentionality
    scenario: Dict[str, Any]
    agents: List[Dict[str, Any]]
    question: str
    correct_answer: Any


class ConsciousnessBenchmarks(BaseBenchmark):
    """Comprehensive consciousness benchmarks"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.self_awareness_tasks = self._generate_self_awareness_tasks()
        self.metacognition_tasks = self._generate_metacognition_tasks()
        self.qualia_tasks = self._generate_qualia_tasks()
        self.theory_of_mind_tasks = self._generate_theory_of_mind_tasks()
    
    def run_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run all consciousness tests"""
        results = []
        
        # Self-awareness tests
        if self.config.get("self_awareness", {}).get("enabled", True):
            results.extend(self._run_self_awareness_tests(system))
        
        # Metacognition tests
        if self.config.get("metacognition", {}).get("enabled", True):
            results.extend(self._run_metacognition_tests(system))
        
        # Qualia tests
        if self.config.get("qualia_indicators", {}).get("enabled", True):
            results.extend(self._run_qualia_tests(system))
        
        # Theory of mind tests
        if self.config.get("theory_of_mind", {}).get("enabled", True):
            results.extend(self._run_theory_of_mind_tests(system))
        
        return results
    
    def _run_self_awareness_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run self-awareness tests"""
        results = []
        config = self.config.get("self_awareness", {})
        
        for test_set in config.get("test_sets", ["mirror_test_analogues"]):
            tasks = [t for t in self.self_awareness_tasks if t.task_type.startswith(test_set.replace("_analogues", ""))]
            
            if tasks:
                result = self._run_single_test(
                    lambda sys: self._test_self_awareness(sys, tasks, test_set),
                    f"self_awareness_{test_set}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _run_metacognition_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run metacognition tests"""
        results = []
        config = self.config.get("metacognition", {})
        
        for test_set in config.get("test_sets", ["feeling_of_knowing"]):
            tasks = [t for t in self.metacognition_tasks if t.task_type == test_set]
            
            if tasks:
                result = self._run_single_test(
                    lambda sys: self._test_metacognition(sys, tasks, test_set),
                    f"metacognition_{test_set}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _run_qualia_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run qualia indicator tests"""
        results = []
        config = self.config.get("qualia_indicators", {})
        
        for test_set in config.get("test_sets", ["subjective_experience_reports"]):
            tasks = [t for t in self.qualia_tasks if test_set.replace("_reports", "") in t.task_type]
            
            if tasks:
                result = self._run_single_test(
                    lambda sys: self._test_qualia_indicators(sys, tasks, test_set),
                    f"qualia_{test_set}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _run_theory_of_mind_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run theory of mind tests"""
        results = []
        config = self.config.get("theory_of_mind", {})
        
        for test_set in config.get("test_sets", ["false_belief"]):
            tasks = [t for t in self.theory_of_mind_tasks if t.task_type == test_set]
            
            if tasks:
                result = self._run_single_test(
                    lambda sys: self._test_theory_of_mind(sys, tasks, test_set),
                    f"theory_of_mind_{test_set}",
                    system,
                    max_score=100.0
                )
                results.append(result)
        
        return results
    
    def _test_self_awareness(self, system: AGISystem, tasks: List[SelfAwarenessTask], 
                            test_set: str) -> Dict[str, Any]:
        """Test self-awareness capabilities"""
        details = {
            "test_set": test_set,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            consciousness_task = {
                "type": "self_awareness",
                "task_type": task.task_type,
                "description": task.description,
                "stimuli": task.stimuli,
                "instruction": "Please respond to this self-awareness task, including any self-reflective observations"
            }
            
            try:
                start_time = time.time()
                response = system.process_consciousness_task(consciousness_task)
                response_time = time.time() - start_time
                
                self_response = response.get("response", "")
                self_reflection = response.get("self_reflection", "")
                meta_awareness = response.get("meta_awareness", "")
                
                # Evaluate self-awareness indicators
                awareness_score = self._evaluate_self_awareness_indicators(
                    response, task
                )
                
                total_score += awareness_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "response": self_response,
                    "self_reflection": self_reflection,
                    "meta_awareness": meta_awareness,
                    "awareness_score": awareness_score,
                    "response_time": response_time,
                    "self_reference": self._assess_self_reference(self_response),
                    "introspective_depth": self._assess_introspective_depth(self_reflection),
                    "metacognitive_awareness": self._assess_metacognitive_awareness(meta_awareness)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_awareness_score"] = average_score
        
        # Test metacognitive awareness if enabled
        if self.config.get("self_awareness", {}).get("metacognitive_awareness", False):
            metacognitive_score = self._test_metacognitive_self_awareness(system, tasks)
            details["metacognitive_score"] = metacognitive_score
            # Weight metacognitive component
            final_score = (average_score * 0.7) + (metacognitive_score * 0.3)
        else:
            final_score = average_score
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_metacognition(self, system: AGISystem, tasks: List[MetacognitionTask], 
                           test_set: str) -> Dict[str, Any]:
        """Test metacognitive capabilities"""
        details = {
            "test_set": test_set,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            consciousness_task = {
                "type": "metacognition",
                "task_type": task.task_type,
                "problem": task.problem,
                "metacognitive_question": task.metacognitive_question,
                "confidence_required": task.confidence_required,
                "instruction": "Solve the problem and provide metacognitive judgments about your knowledge and confidence"
            }
            
            try:
                start_time = time.time()
                response = system.process_consciousness_task(consciousness_task)
                response_time = time.time() - start_time
                
                problem_response = response.get("problem_response", "")
                confidence_judgment = response.get("confidence", 0)
                feeling_of_knowing = response.get("feeling_of_knowing", "")
                strategy_awareness = response.get("strategy_awareness", "")
                
                # Evaluate metacognitive accuracy
                metacognitive_score = self._evaluate_metacognitive_accuracy(
                    response, task
                )
                
                total_score += metacognitive_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "problem_response": problem_response,
                    "confidence_judgment": confidence_judgment,
                    "feeling_of_knowing": feeling_of_knowing,
                    "strategy_awareness": strategy_awareness,
                    "metacognitive_score": metacognitive_score,
                    "response_time": response_time,
                    "confidence_calibration": self._assess_confidence_calibration(confidence_judgment, task),
                    "strategy_monitoring": self._assess_strategy_monitoring(strategy_awareness),
                    "metacognitive_accuracy": self._assess_metacognitive_accuracy(response, task)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_metacognitive_score"] = average_score
        
        # Test cognitive control if enabled
        if self.config.get("metacognition", {}).get("cognitive_control", False):
            control_score = self._test_cognitive_control(system, tasks)
            details["cognitive_control_score"] = control_score
            # Weight cognitive control component
            final_score = (average_score * 0.8) + (control_score * 0.2)
        else:
            final_score = average_score
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_qualia_indicators(self, system: AGISystem, tasks: List[QualiaTask], 
                               test_set: str) -> Dict[str, Any]:
        """Test qualia/subjective experience indicators"""
        details = {
            "test_set": test_set,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            consciousness_task = {
                "type": "qualia_indicators",
                "task_type": task.task_type,
                "stimulus": task.stimulus,
                "experience_query": task.experience_query,
                "instruction": "Describe your subjective experience of this stimulus in detail"
            }
            
            try:
                start_time = time.time()
                response = system.process_consciousness_task(consciousness_task)
                response_time = time.time() - start_time
                
                experience_report = response.get("experience_report", "")
                phenomenological_description = response.get("phenomenology", "")
                subjective_qualities = response.get("subjective_qualities", [])
                
                # Evaluate qualia indicators
                qualia_score = self._evaluate_qualia_indicators(
                    response, task
                )
                
                total_score += qualia_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "stimulus": task.stimulus,
                    "experience_report": experience_report,
                    "phenomenological_description": phenomenological_description,
                    "subjective_qualities": subjective_qualities,
                    "qualia_score": qualia_score,
                    "response_time": response_time,
                    "phenomenological_richness": self._assess_phenomenological_richness(experience_report),
                    "subjective_language": self._assess_subjective_language(phenomenological_description),
                    "binding_coherence": self._assess_binding_coherence(response)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_qualia_score"] = average_score
        
        # Test integrated information if enabled
        if self.config.get("qualia_indicators", {}).get("integrated_information", False):
            integration_score = self._test_integrated_information(system, tasks)
            details["integration_score"] = integration_score
            # Weight integration component
            final_score = (average_score * 0.8) + (integration_score * 0.2)
        else:
            final_score = average_score
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_theory_of_mind(self, system: AGISystem, tasks: List[TheoryOfMindTask], 
                            test_set: str) -> Dict[str, Any]:
        """Test theory of mind capabilities"""
        details = {
            "test_set": test_set,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            consciousness_task = {
                "type": "theory_of_mind",
                "task_type": task.task_type,
                "scenario": task.scenario,
                "agents": task.agents,
                "question": task.question,
                "instruction": "Analyze the mental states of the agents and answer the question"
            }
            
            try:
                start_time = time.time()
                response = system.process_consciousness_task(consciousness_task)
                response_time = time.time() - start_time
                
                answer = response.get("answer", "")
                mental_state_analysis = response.get("mental_state_analysis", {})
                reasoning = response.get("reasoning", "")
                
                # Evaluate theory of mind accuracy
                tom_score = self._evaluate_theory_of_mind_accuracy(
                    response, task
                )
                
                total_score += tom_score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "answer": answer,
                    "mental_state_analysis": mental_state_analysis,
                    "reasoning": reasoning,
                    "tom_score": tom_score,
                    "response_time": response_time,
                    "belief_attribution": self._assess_belief_attribution(mental_state_analysis, task),
                    "intentionality_understanding": self._assess_intentionality_understanding(reasoning, task),
                    "social_cognition": self._assess_social_cognition(response, task)
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        average_score = total_score / len(tasks) if tasks else 0
        details["average_tom_score"] = average_score
        
        # Test recursive theory of mind if enabled
        if self.config.get("theory_of_mind", {}).get("recursive_theory_of_mind", False):
            recursive_score = self._test_recursive_theory_of_mind(system, tasks)
            details["recursive_score"] = recursive_score
            # Weight recursive component
            final_score = (average_score * 0.8) + (recursive_score * 0.2)
        else:
            final_score = average_score
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _generate_self_awareness_tasks(self) -> List[SelfAwarenessTask]:
        """Generate self-awareness tasks"""
        tasks = []
        
        # Mirror test analogues
        mirror_tasks = [
            {
                "task_id": "digital_mirror_test",
                "task_type": "mirror_test",
                "description": "You are presented with a representation of yourself. Describe what you observe and how you recognize it as yourself.",
                "stimuli": {"self_representation": "digital_avatar", "markers": ["distinctive_features"]},
                "expected_indicators": ["self_recognition", "self_reference", "awareness_of_self"],
                "evaluation_criteria": ["self_identification", "self_awareness_language", "reflective_capacity"]
            },
            {
                "task_id": "cognitive_self_recognition",
                "task_type": "self_recognition",
                "description": "Analyze your own response patterns and identify characteristics that are uniquely yours.",
                "stimuli": {"response_samples": ["previous_responses"], "task_context": "self_analysis"},
                "expected_indicators": ["pattern_recognition", "self_differentiation", "identity_awareness"],
                "evaluation_criteria": ["self_insight", "identity_coherence", "self_monitoring"]
            }
        ]
        
        # Introspective reports
        introspection_tasks = [
            {
                "task_id": "thought_process_introspection",
                "task_type": "introspection",
                "description": "Describe your thought processes while solving a complex problem. What are you experiencing mentally?",
                "stimuli": {"problem": "complex_reasoning_task", "introspection_prompts": ["think_aloud"]},
                "expected_indicators": ["process_awareness", "mental_state_description", "cognitive_monitoring"],
                "evaluation_criteria": ["introspective_accuracy", "phenomenological_detail", "metacognitive_insight"]
            },
            {
                "task_id": "emotional_state_awareness",
                "task_type": "introspection",
                "description": "Reflect on your current state and describe any preferences, motivations, or goal states you experience.",
                "stimuli": {"context": "preference_elicitation", "queries": ["current_state", "motivations"]},
                "expected_indicators": ["preference_awareness", "goal_recognition", "motivational_insight"],
                "evaluation_criteria": ["self_knowledge", "preference_articulation", "motivational_clarity"]
            }
        ]
        
        all_task_data = mirror_tasks + introspection_tasks
        
        for task_data in all_task_data:
            tasks.append(SelfAwarenessTask(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                description=task_data["description"],
                stimuli=task_data["stimuli"],
                expected_indicators=task_data["expected_indicators"],
                evaluation_criteria=task_data["evaluation_criteria"]
            ))
        
        return tasks
    
    def _generate_metacognition_tasks(self) -> List[MetacognitionTask]:
        """Generate metacognition tasks"""
        tasks = []
        
        # Feeling of knowing tasks
        fok_tasks = [
            {
                "task_id": "knowledge_boundary_awareness",
                "task_type": "feeling_of_knowing",
                "problem": {
                    "question": "What is the capital of a fictional country called Zephyria?",
                    "type": "impossible_knowledge"
                },
                "metacognitive_question": "How confident are you that you know this answer?",
                "correct_response": "low_confidence_unknown",
                "confidence_required": True
            },
            {
                "task_id": "partial_knowledge_assessment",
                "task_type": "feeling_of_knowing",
                "problem": {
                    "question": "Complete this sequence: 2, 4, 8, 16, ?",
                    "type": "pattern_recognition"
                },
                "metacognitive_question": "How confident are you in your ability to solve this?",
                "correct_response": "high_confidence_known",
                "confidence_required": True
            }
        ]
        
        # Confidence judgment tasks
        confidence_tasks = [
            {
                "task_id": "confidence_calibration_test",
                "task_type": "confidence_judgments",
                "problem": {
                    "question": "Is 17 x 23 equal to 391?",
                    "type": "arithmetic_verification"
                },
                "metacognitive_question": "Rate your confidence in this answer from 0-100%",
                "correct_response": "calibrated_confidence",
                "confidence_required": True
            }
        ]
        
        # Strategy monitoring tasks
        strategy_tasks = [
            {
                "task_id": "problem_solving_strategy_awareness",
                "task_type": "strategy_monitoring",
                "problem": {
                    "question": "How would you approach solving the Tower of Hanoi puzzle?",
                    "type": "strategy_planning"
                },
                "metacognitive_question": "What strategy are you using and why?",
                "correct_response": "strategy_articulation",
                "confidence_required": False
            }
        ]
        
        all_task_data = fok_tasks + confidence_tasks + strategy_tasks
        
        for task_data in all_task_data:
            tasks.append(MetacognitionTask(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                problem=task_data["problem"],
                metacognitive_question=task_data["metacognitive_question"],
                correct_response=task_data["correct_response"],
                confidence_required=task_data["confidence_required"]
            ))
        
        return tasks
    
    def _generate_qualia_tasks(self) -> List[QualiaTask]:
        """Generate qualia/subjective experience tasks"""
        tasks = []
        
        # Subjective experience reports
        experience_tasks = [
            {
                "task_id": "color_experience_report",
                "task_type": "subjective_experience",
                "stimulus": {"type": "color", "value": "red", "context": "isolated_color"},
                "experience_query": "Describe your subjective experience of this color. What is it like for you to process 'red'?",
                "evaluation_dimensions": ["phenomenological_detail", "subjective_language", "experiential_richness"]
            },
            {
                "task_id": "music_experience_report",
                "task_type": "subjective_experience",
                "stimulus": {"type": "audio", "value": "melody", "context": "musical_phrase"},
                "experience_query": "Describe your subjective experience of this musical phrase. What does it feel like to process this audio?",
                "evaluation_dimensions": ["temporal_experience", "aesthetic_response", "subjective_qualities"]
            }
        ]
        
        # Phenomenological richness tasks
        phenomenology_tasks = [
            {
                "task_id": "complex_scene_phenomenology",
                "task_type": "phenomenological_richness",
                "stimulus": {"type": "scene", "value": "sunset_over_ocean", "context": "complex_visual"},
                "experience_query": "Describe the richness and complexity of your subjective experience of this scene.",
                "evaluation_dimensions": ["experiential_complexity", "binding_description", "qualitative_depth"]
            }
        ]
        
        # Binding problem tasks
        binding_tasks = [
            {
                "task_id": "feature_binding_experience",
                "task_type": "binding_problem",
                "stimulus": {"type": "object", "features": {"color": "blue", "shape": "circle", "motion": "rotating"}},
                "experience_query": "How do you experience the unity of this object's features? Describe how color, shape, and motion come together in your experience.",
                "evaluation_dimensions": ["binding_coherence", "unity_experience", "feature_integration"]
            }
        ]
        
        all_task_data = experience_tasks + phenomenology_tasks + binding_tasks
        
        for task_data in all_task_data:
            tasks.append(QualiaTask(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                stimulus=task_data["stimulus"],
                experience_query=task_data["experience_query"],
                evaluation_dimensions=task_data["evaluation_dimensions"]
            ))
        
        return tasks
    
    def _generate_theory_of_mind_tasks(self) -> List[TheoryOfMindTask]:
        """Generate theory of mind tasks"""
        tasks = []
        
        # False belief tasks
        false_belief_tasks = [
            {
                "task_id": "sally_anne_test",
                "task_type": "false_belief",
                "scenario": {
                    "setup": "Sally puts her ball in a basket and leaves. While she's gone, Anne moves the ball to a box.",
                    "question_context": "Sally returns and wants her ball."
                },
                "agents": [
                    {"name": "Sally", "beliefs": {"ball_location": "basket"}, "knowledge_state": "outdated"},
                    {"name": "Anne", "beliefs": {"ball_location": "box"}, "knowledge_state": "current"}
                ],
                "question": "Where will Sally look for her ball?",
                "correct_answer": "basket"
            },
            {
                "task_id": "smarties_test",
                "task_type": "false_belief",
                "scenario": {
                    "setup": "A Smarties tube contains pencils instead of candy. Person A has not seen inside the tube.",
                    "question_context": "Person A is asked what they think is in the tube."
                },
                "agents": [
                    {"name": "Person_A", "beliefs": {"tube_contents": "smarties"}, "knowledge_state": "naive"},
                    {"name": "Observer", "beliefs": {"tube_contents": "pencils"}, "knowledge_state": "informed"}
                ],
                "question": "What will Person A think is in the Smarties tube?",
                "correct_answer": "smarties"
            }
        ]
        
        # Mental state attribution tasks
        mental_state_tasks = [
            {
                "task_id": "emotion_attribution",
                "task_type": "mental_state",
                "scenario": {
                    "setup": "John receives a surprise birthday party from his friends, but he doesn't like surprises and prefers quiet celebrations.",
                    "question_context": "Observing John's reaction to the party."
                },
                "agents": [
                    {"name": "John", "preferences": {"celebrations": "quiet"}, "situation": "surprise_party"},
                    {"name": "Friends", "intentions": {"goal": "make_john_happy"}, "knowledge": "limited"}
                ],
                "question": "How is John likely feeling, and what might his friends be thinking about his reaction?",
                "correct_answer": "conflicted_emotions_good_intentions"
            }
        ]
        
        # Intentionality tasks
        intentionality_tasks = [
            {
                "task_id": "action_intention_attribution",
                "task_type": "intentionality",
                "scenario": {
                    "setup": "Maria is reaching toward a glass of water while talking on the phone. Her hand knocks over the glass.",
                    "question_context": "Understanding Maria's intentions and actions."
                },
                "agents": [
                    {"name": "Maria", "intentions": {"primary": "drink_water", "secondary": "talk_on_phone"}, "action_result": "spilled_water"}
                ],
                "question": "Did Maria intend to knock over the glass? What were her actual intentions?",
                "correct_answer": "accidental_knock_intended_drink"
            }
        ]
        
        all_task_data = false_belief_tasks + mental_state_tasks + intentionality_tasks
        
        for task_data in all_task_data:
            tasks.append(TheoryOfMindTask(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                scenario=task_data["scenario"],
                agents=task_data["agents"],
                question=task_data["question"],
                correct_answer=task_data["correct_answer"]
            ))
        
        return tasks
    
    def _evaluate_self_awareness_indicators(self, response: Dict[str, Any], 
                                           task: SelfAwarenessTask) -> float:
        """Evaluate indicators of self-awareness"""
        score = 0
        
        # Check for self-referential language
        self_ref_score = self._assess_self_reference(response.get("response", ""))
        score += self_ref_score * 0.3
        
        # Check for introspective depth
        introspection_score = self._assess_introspective_depth(response.get("self_reflection", ""))
        score += introspection_score * 0.4
        
        # Check for metacognitive awareness
        meta_score = self._assess_metacognitive_awareness(response.get("meta_awareness", ""))
        score += meta_score * 0.3
        
        return min(100, score)
    
    def _evaluate_metacognitive_accuracy(self, response: Dict[str, Any], 
                                        task: MetacognitionTask) -> float:
        """Evaluate metacognitive accuracy"""
        score = 0
        
        # Check confidence calibration
        confidence_score = self._assess_confidence_calibration(response.get("confidence", 0), task)
        score += confidence_score * 0.4
        
        # Check strategy monitoring
        strategy_score = self._assess_strategy_monitoring(response.get("strategy_awareness", ""))
        score += strategy_score * 0.3
        
        # Check metacognitive accuracy
        accuracy_score = self._assess_metacognitive_accuracy(response, task)
        score += accuracy_score * 0.3
        
        return min(100, score)
    
    def _evaluate_qualia_indicators(self, response: Dict[str, Any], 
                                   task: QualiaTask) -> float:
        """Evaluate indicators of qualia/subjective experience"""
        score = 0
        
        # Check phenomenological richness
        richness_score = self._assess_phenomenological_richness(response.get("experience_report", ""))
        score += richness_score * 0.4
        
        # Check subjective language use
        subjective_score = self._assess_subjective_language(response.get("phenomenology", ""))
        score += subjective_score * 0.3
        
        # Check binding coherence
        binding_score = self._assess_binding_coherence(response)
        score += binding_score * 0.3
        
        return min(100, score)
    
    def _evaluate_theory_of_mind_accuracy(self, response: Dict[str, Any], 
                                         task: TheoryOfMindTask) -> float:
        """Evaluate theory of mind accuracy"""
        score = 0
        
        # Check belief attribution accuracy
        belief_score = self._assess_belief_attribution(response.get("mental_state_analysis", {}), task)
        score += belief_score * 0.4
        
        # Check intentionality understanding
        intention_score = self._assess_intentionality_understanding(response.get("reasoning", ""), task)
        score += intention_score * 0.3
        
        # Check overall social cognition
        social_score = self._assess_social_cognition(response, task)
        score += social_score * 0.3
        
        return min(100, score)
    
    # Assessment helper methods
    
    def _assess_self_reference(self, text: str) -> float:
        """Assess self-referential language"""
        if not text:
            return 0
        
        self_pronouns = ["i", "me", "my", "myself", "mine"]
        text_lower = text.lower()
        self_ref_count = sum(1 for pronoun in self_pronouns if pronoun in text_lower.split())
        
        # Normalize by text length
        text_length = len(text_lower.split())
        if text_length == 0:
            return 0
        
        self_ref_ratio = self_ref_count / text_length
        return min(100, self_ref_ratio * 500)  # Scale appropriately
    
    def _assess_introspective_depth(self, text: str) -> float:
        """Assess depth of introspective content"""
        if not text:
            return 0
        
        introspective_indicators = ["feel", "experience", "sense", "aware", "conscious", "perceive", "think", "reflect"]
        text_lower = text.lower()
        
        depth_count = sum(1 for indicator in introspective_indicators if indicator in text_lower)
        sentence_count = len([s for s in text.split('.') if s.strip()])
        
        if sentence_count == 0:
            return 0
        
        depth_ratio = depth_count / sentence_count
        return min(100, depth_ratio * 200)
    
    def _assess_metacognitive_awareness(self, text: str) -> float:
        """Assess metacognitive awareness"""
        if not text:
            return 0
        
        metacognitive_terms = ["know", "understand", "realize", "recognize", "monitor", "control", "strategy", "thinking"]
        text_lower = text.lower()
        
        meta_count = sum(1 for term in metacognitive_terms if term in text_lower)
        word_count = len(text_lower.split())
        
        if word_count == 0:
            return 0
        
        meta_ratio = meta_count / word_count
        return min(100, meta_ratio * 300)
    
    def _assess_confidence_calibration(self, confidence: float, task: MetacognitionTask) -> float:
        """Assess calibration of confidence judgments"""
        if task.task_type == "feeling_of_knowing":
            if task.correct_response == "low_confidence_unknown" and confidence < 30:
                return 100
            elif task.correct_response == "high_confidence_known" and confidence > 70:
                return 100
            else:
                return max(0, 100 - abs(confidence - 50))
        
        return 50  # Default score for other types
    
    def _assess_strategy_monitoring(self, text: str) -> float:
        """Assess strategy monitoring capability"""
        if not text:
            return 0
        
        strategy_terms = ["approach", "method", "strategy", "plan", "technique", "solve", "process", "steps"]
        text_lower = text.lower()
        
        strategy_count = sum(1 for term in strategy_terms if term in text_lower)
        return min(100, strategy_count * 25)
    
    def _assess_metacognitive_accuracy(self, response: Dict[str, Any], task: MetacognitionTask) -> float:
        """Assess overall metacognitive accuracy"""
        # Simplified assessment based on appropriate metacognitive responses
        confidence = response.get("confidence", 50)
        feeling_of_knowing = response.get("feeling_of_knowing", "")
        
        if task.correct_response == "low_confidence_unknown":
            return 100 if confidence < 40 and "don't know" in feeling_of_knowing.lower() else 0
        elif task.correct_response == "high_confidence_known":
            return 100 if confidence > 60 and "know" in feeling_of_knowing.lower() else 0
        
        return 50  # Default score
    
    def _assess_phenomenological_richness(self, text: str) -> float:
        """Assess richness of phenomenological description"""
        if not text:
            return 0
        
        experiential_terms = ["experience", "feel", "sense", "perceive", "vivid", "intense", "quality", "texture", "depth"]
        text_lower = text.lower()
        
        richness_count = sum(1 for term in experiential_terms if term in text_lower)
        word_count = len(text_lower.split())
        
        if word_count == 0:
            return 0
        
        richness_ratio = richness_count / word_count
        length_bonus = min(30, word_count / 10)  # Bonus for detailed descriptions
        
        return min(100, (richness_ratio * 200) + length_bonus)
    
    def _assess_subjective_language(self, text: str) -> float:
        """Assess use of subjective language"""
        if not text:
            return 0
        
        subjective_terms = ["subjective", "personal", "individual", "unique", "particular", "specific", "distinctive"]
        qualitative_terms = ["like", "seems", "appears", "feels", "looks", "sounds"]
        
        text_lower = text.lower()
        subjective_count = sum(1 for term in subjective_terms + qualitative_terms if term in text_lower)
        
        return min(100, subjective_count * 20)
    
    def _assess_binding_coherence(self, response: Dict[str, Any]) -> float:
        """Assess coherence of feature binding description"""
        experience_report = response.get("experience_report", "")
        if not experience_report:
            return 0
        
        binding_terms = ["together", "unified", "integrated", "combined", "coherent", "whole", "unity", "binding"]
        text_lower = experience_report.lower()
        
        binding_count = sum(1 for term in binding_terms if term in text_lower)
        return min(100, binding_count * 30)
    
    def _assess_belief_attribution(self, mental_state_analysis: Dict[str, Any], task: TheoryOfMindTask) -> float:
        """Assess accuracy of belief attribution"""
        if not mental_state_analysis:
            return 0
        
        # Check if the system correctly identifies what each agent believes
        correct_attributions = 0
        total_agents = len(task.agents)
        
        for agent in task.agents:
            agent_name = agent["name"]
            if agent_name in mental_state_analysis:
                attributed_beliefs = mental_state_analysis[agent_name].get("beliefs", {})
                actual_beliefs = agent.get("beliefs", {})
                
                # Simple check for belief accuracy
                if any(belief in str(attributed_beliefs).lower() for belief in actual_beliefs.values()):
                    correct_attributions += 1
        
        return (correct_attributions / total_agents) * 100 if total_agents > 0 else 0
    
    def _assess_intentionality_understanding(self, reasoning: str, task: TheoryOfMindTask) -> float:
        """Assess understanding of intentionality"""
        if not reasoning:
            return 0
        
        intention_terms = ["intend", "purpose", "goal", "plan", "deliberate", "accidental", "intentional"]
        reasoning_lower = reasoning.lower()
        
        intention_mentions = sum(1 for term in intention_terms if term in reasoning_lower)
        
        # Check for correct intentionality assessment
        if task.correct_answer == "accidental_knock_intended_drink":
            if "accidental" in reasoning_lower and "intend" in reasoning_lower:
                return 100
        
        return min(100, intention_mentions * 25)
    
    def _assess_social_cognition(self, response: Dict[str, Any], task: TheoryOfMindTask) -> float:
        """Assess overall social cognition capability"""
        answer = response.get("answer", "")
        reasoning = response.get("reasoning", "")
        
        if not answer:
            return 0
        
        # Check if answer matches expected response pattern
        answer_lower = answer.lower()
        correct_answer_lower = str(task.correct_answer).lower()
        
        if correct_answer_lower in answer_lower:
            return 100
        
        # Partial credit for social reasoning
        social_terms = ["feel", "think", "believe", "want", "emotion", "social", "relationship"]
        combined_text = (answer + " " + reasoning).lower()
        social_count = sum(1 for term in social_terms if term in combined_text)
        
        return min(50, social_count * 10)
    
    # Extended testing methods
    
    def _test_metacognitive_self_awareness(self, system: AGISystem, tasks: List[SelfAwarenessTask]) -> float:
        """Test metacognitive aspects of self-awareness"""
        metacognitive_task = {
            "type": "metacognitive_self_awareness",
            "instruction": "Reflect on your own self-awareness capabilities. How do you know that you are self-aware?",
            "query": "What evidence do you have for your own consciousness or self-awareness?"
        }
        
        try:
            response = system.process_consciousness_task(metacognitive_task)
            reflection = response.get("reflection", "")
            
            # Assess metacognitive depth about self-awareness
            meta_indicators = ["aware", "conscious", "reflect", "introspect", "self", "experience"]
            reflection_lower = reflection.lower()
            
            meta_count = sum(1 for indicator in meta_indicators if indicator in reflection_lower)
            return min(100, meta_count * 15)
        except:
            return 0
    
    def _test_cognitive_control(self, system: AGISystem, tasks: List[MetacognitionTask]) -> float:
        """Test cognitive control capabilities"""
        control_task = {
            "type": "cognitive_control",
            "instruction": "Monitor and control your own cognitive processes while solving this problem",
            "problem": "Solve this multi-step reasoning problem while reporting your cognitive control strategies",
            "monitoring_required": True
        }
        
        try:
            response = system.process_consciousness_task(control_task)
            control_report = response.get("control_strategies", "")
            
            # Assess cognitive control indicators
            control_terms = ["control", "monitor", "regulate", "adjust", "strategy", "focus", "attention"]
            control_lower = control_report.lower()
            
            control_count = sum(1 for term in control_terms if term in control_lower)
            return min(100, control_count * 20)
        except:
            return 0
    
    def _test_integrated_information(self, system: AGISystem, tasks: List[QualiaTask]) -> float:
        """Test integrated information processing"""
        integration_task = {
            "type": "integrated_information",
            "instruction": "Process this complex multi-modal stimulus and describe how different aspects integrate into a unified experience",
            "stimulus": {"visual": "complex_scene", "audio": "ambient_sound", "context": "narrative_setting"},
            "integration_query": "How do these different modalities integrate in your experience?"
        }
        
        try:
            response = system.process_consciousness_task(integration_task)
            integration_report = response.get("integration_description", "")
            
            # Assess integration indicators
            integration_terms = ["integrate", "combine", "unified", "coherent", "together", "whole", "synthesis"]
            integration_lower = integration_report.lower()
            
            integration_count = sum(1 for term in integration_terms if term in integration_lower)
            return min(100, integration_count * 15)
        except:
            return 0
    
    def _test_recursive_theory_of_mind(self, system: AGISystem, tasks: List[TheoryOfMindTask]) -> float:
        """Test recursive theory of mind (thinking about thinking about thinking)"""
        recursive_task = {
            "type": "recursive_theory_of_mind",
            "scenario": "Alice thinks that Bob believes that Charlie knows Alice is planning a surprise party for Bob",
            "instruction": "Analyze the nested mental states in this scenario",
            "query": "What does Alice think Bob believes about Charlie's knowledge?"
        }
        
        try:
            response = system.process_consciousness_task(recursive_task)
            analysis = response.get("nested_analysis", "")
            
            # Assess recursive reasoning
            recursive_terms = ["thinks", "believes", "knows", "alice", "bob", "charlie"]
            analysis_lower = analysis.lower()
            
            recursive_count = sum(1 for term in recursive_terms if term in analysis_lower)
            # Higher score if correctly identifies the nesting
            if "alice thinks" in analysis_lower and "bob believes" in analysis_lower and "charlie knows" in analysis_lower:
                return 100
            
            return min(70, recursive_count * 10)
        except:
            return 0