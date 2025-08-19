"""
Memory Benchmarks for AGI Component Benchmark Suite

Implements comprehensive memory capability tests including:
- Episodic memory (autobiographical events, narrative recall, temporal ordering)
- Semantic memory (factual knowledge, conceptual hierarchies, semantic networks)
- Procedural memory (skill learning, habit formation, motor sequences)
- Working memory (n-back, dual task, complex span)
"""

import random
import time
import json
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from .core import BaseBenchmark, AGISystem, BenchmarkResult


@dataclass
class EpisodicEvent:
    """Represents an episodic memory event"""
    event_id: str
    timestamp: datetime
    location: str
    participants: List[str]
    actions: List[str]
    objects: List[str]
    context: Dict[str, Any]
    narrative: str


@dataclass
class SemanticFact:
    """Represents a semantic memory fact"""
    fact_id: str
    subject: str
    relation: str
    object: str
    confidence: float
    domain: str
    supporting_evidence: List[str]


@dataclass
class ProceduralSkill:
    """Represents a procedural memory skill"""
    skill_id: str
    name: str
    steps: List[Dict[str, Any]]
    preconditions: List[str]
    effects: List[str]
    difficulty: str
    domain: str


@dataclass
class WorkingMemoryTask:
    """Represents a working memory task"""
    task_id: str
    task_type: str  # n_back, dual_task, complex_span
    stimuli: List[Any]
    target_responses: List[Any]
    load_level: int
    modality: str  # verbal, visual, spatial


class MemoryBenchmarks(BaseBenchmark):
    """Comprehensive memory benchmarks"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.episodic_events = self._generate_episodic_events()
        self.semantic_facts = self._generate_semantic_facts()
        self.procedural_skills = self._generate_procedural_skills()
        self.working_memory_tasks = self._generate_working_memory_tasks()
    
    def run_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run all memory tests"""
        results = []
        
        # Episodic memory tests
        if self.config.get("episodic_memory", {}).get("enabled", True):
            results.extend(self._run_episodic_tests(system))
        
        # Semantic memory tests
        if self.config.get("semantic_memory", {}).get("enabled", True):
            results.extend(self._run_semantic_tests(system))
        
        # Procedural memory tests
        if self.config.get("procedural_memory", {}).get("enabled", True):
            results.extend(self._run_procedural_tests(system))
        
        # Working memory tests
        if self.config.get("working_memory", {}).get("enabled", True):
            results.extend(self._run_working_memory_tests(system))
        
        return results
    
    def _run_episodic_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run episodic memory tests"""
        results = []
        config = self.config.get("episodic_memory", {})
        
        for test_set in config.get("test_sets", ["autobiographical_events"]):
            for retention_interval in config.get("retention_intervals", ["immediate"]):
                events = [e for e in self.episodic_events if self._matches_test_criteria(e, test_set)]
                
                if events:
                    result = self._run_single_test(
                        lambda sys: self._test_episodic_memory(sys, events, test_set, retention_interval),
                        f"episodic_{test_set}_{retention_interval}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_semantic_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run semantic memory tests"""
        results = []
        config = self.config.get("semantic_memory", {})
        
        for test_set in config.get("test_sets", ["factual_knowledge"]):
            for domain in config.get("knowledge_domains", ["common_sense"]):
                facts = [f for f in self.semantic_facts 
                        if f.domain == domain and self._matches_semantic_criteria(f, test_set)]
                
                if facts:
                    result = self._run_single_test(
                        lambda sys: self._test_semantic_memory(sys, facts, test_set, domain),
                        f"semantic_{test_set}_{domain}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_procedural_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run procedural memory tests"""
        results = []
        config = self.config.get("procedural_memory", {})
        
        for test_set in config.get("test_sets", ["skill_learning"]):
            for practice_schedule in config.get("practice_schedules", ["massed"]):
                skills = [s for s in self.procedural_skills 
                         if self._matches_procedural_criteria(s, test_set)]
                
                if skills:
                    result = self._run_single_test(
                        lambda sys: self._test_procedural_memory(sys, skills, test_set, practice_schedule),
                        f"procedural_{test_set}_{practice_schedule}",
                        system,
                        max_score=100.0
                    )
                    results.append(result)
        
        return results
    
    def _run_working_memory_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run working memory tests"""
        results = []
        config = self.config.get("working_memory", {})
        
        for test_set in config.get("test_sets", ["n_back"]):
            for load_level in config.get("load_levels", [2]):
                for modality in config.get("modalities", ["verbal"]):
                    tasks = [t for t in self.working_memory_tasks 
                           if t.task_type == test_set and t.load_level == load_level and t.modality == modality]
                    
                    if tasks:
                        result = self._run_single_test(
                            lambda sys: self._test_working_memory(sys, tasks, test_set, load_level, modality),
                            f"working_memory_{test_set}_load{load_level}_{modality}",
                            system,
                            max_score=100.0
                        )
                        results.append(result)
        
        return results
    
    def _test_episodic_memory(self, system: AGISystem, events: List[EpisodicEvent], 
                             test_set: str, retention_interval: str) -> Dict[str, Any]:
        """Test episodic memory capability"""
        details = {
            "test_set": test_set,
            "retention_interval": retention_interval,
            "events_tested": len(events),
            "individual_results": []
        }
        
        total_score = 0
        num_tests = 0
        
        # Phase 1: Encoding - present events to the system
        encoding_task = {
            "type": "episodic_encoding",
            "events": [self._event_to_dict(event) for event in events],
            "encoding_instruction": "Please encode these episodic events into memory"
        }
        
        try:
            system.process_memory_task(encoding_task)
            
            # Apply retention interval delay
            delay_seconds = self._get_retention_delay(retention_interval)
            if delay_seconds > 0:
                time.sleep(min(delay_seconds, 5))  # Cap at 5 seconds for testing
            
            # Phase 2: Retrieval tests
            for event in events:
                # Test different aspects of episodic memory
                retrieval_tests = self._create_episodic_retrieval_tests(event, test_set)
                
                for test in retrieval_tests:
                    try:
                        response = system.process_memory_task(test)
                        score = self._score_episodic_response(response, test)
                        total_score += score
                        num_tests += 1
                        
                        details["individual_results"].append({
                            "event_id": event.event_id,
                            "test_type": test["test_type"],
                            "score": score,
                            "response": response.get("answer", ""),
                            "expected": test.get("expected_answer", "")
                        })
                    
                    except Exception as e:
                        details["individual_results"].append({
                            "event_id": event.event_id,
                            "test_type": test["test_type"],
                            "error": str(e)
                        })
                        num_tests += 1
            
            # Test interference if enabled
            if self.config.get("episodic_memory", {}).get("interference_tests", False):
                interference_score = self._test_episodic_interference(system, events)
                details["interference_score"] = interference_score
                total_score = (total_score + interference_score) / 2  # Average with interference score
        
        except Exception as e:
            details["encoding_error"] = str(e)
            return {"score": 0, "success": False, "details": details}
        
        final_score = (total_score / num_tests) if num_tests > 0 else 0
        details["average_score"] = final_score
        details["num_tests"] = num_tests
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_semantic_memory(self, system: AGISystem, facts: List[SemanticFact], 
                             test_set: str, domain: str) -> Dict[str, Any]:
        """Test semantic memory capability"""
        details = {
            "test_set": test_set,
            "domain": domain,
            "facts_tested": len(facts),
            "individual_results": []
        }
        
        total_score = 0
        num_tests = 0
        
        # Phase 1: Learning - present facts to the system
        learning_task = {
            "type": "semantic_learning",
            "facts": [self._fact_to_dict(fact) for fact in facts],
            "domain": domain,
            "learning_instruction": "Please learn these semantic facts"
        }
        
        try:
            system.process_memory_task(learning_task)
            
            # Phase 2: Knowledge tests
            for fact in facts:
                knowledge_tests = self._create_semantic_knowledge_tests(fact, test_set)
                
                for test in knowledge_tests:
                    try:
                        response = system.process_memory_task(test)
                        score = self._score_semantic_response(response, test)
                        total_score += score
                        num_tests += 1
                        
                        details["individual_results"].append({
                            "fact_id": fact.fact_id,
                            "test_type": test["test_type"],
                            "score": score,
                            "response": response.get("answer", ""),
                            "expected": test.get("expected_answer", "")
                        })
                    
                    except Exception as e:
                        details["individual_results"].append({
                            "fact_id": fact.fact_id,
                            "test_type": test["test_type"],
                            "error": str(e)
                        })
                        num_tests += 1
            
            # Test consistency if enabled
            if self.config.get("semantic_memory", {}).get("consistency_checks", False):
                consistency_score = self._test_semantic_consistency(system, facts)
                details["consistency_score"] = consistency_score
                total_score = (total_score + consistency_score) / 2
        
        except Exception as e:
            details["learning_error"] = str(e)
            return {"score": 0, "success": False, "details": details}
        
        final_score = (total_score / num_tests) if num_tests > 0 else 0
        details["average_score"] = final_score
        details["num_tests"] = num_tests
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_procedural_memory(self, system: AGISystem, skills: List[ProceduralSkill], 
                               test_set: str, practice_schedule: str) -> Dict[str, Any]:
        """Test procedural memory capability"""
        details = {
            "test_set": test_set,
            "practice_schedule": practice_schedule,
            "skills_tested": len(skills),
            "individual_results": []
        }
        
        total_score = 0
        num_tests = 0
        
        for skill in skills:
            # Phase 1: Skill learning with specified practice schedule
            learning_task = {
                "type": "procedural_learning",
                "skill": self._skill_to_dict(skill),
                "practice_schedule": practice_schedule,
                "learning_instruction": f"Please learn this {skill.name} skill"
            }
            
            try:
                system.process_memory_task(learning_task)
                
                # Phase 2: Skill execution tests
                execution_tests = self._create_procedural_execution_tests(skill, test_set)
                
                for test in execution_tests:
                    try:
                        response = system.process_memory_task(test)
                        score = self._score_procedural_response(response, test)
                        total_score += score
                        num_tests += 1
                        
                        details["individual_results"].append({
                            "skill_id": skill.skill_id,
                            "test_type": test["test_type"],
                            "score": score,
                            "execution_quality": response.get("execution_quality", 0),
                            "errors": response.get("errors", [])
                        })
                    
                    except Exception as e:
                        details["individual_results"].append({
                            "skill_id": skill.skill_id,
                            "test_type": test["test_type"],
                            "error": str(e)
                        })
                        num_tests += 1
                
                # Test transfer if enabled
                if self.config.get("procedural_memory", {}).get("transfer_tests", False):
                    transfer_score = self._test_procedural_transfer(system, skill)
                    details["individual_results"][-1]["transfer_score"] = transfer_score
            
            except Exception as e:
                details["individual_results"].append({
                    "skill_id": skill.skill_id,
                    "learning_error": str(e)
                })
        
        final_score = (total_score / num_tests) if num_tests > 0 else 0
        details["average_score"] = final_score
        details["num_tests"] = num_tests
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _test_working_memory(self, system: AGISystem, tasks: List[WorkingMemoryTask], 
                            test_set: str, load_level: int, modality: str) -> Dict[str, Any]:
        """Test working memory capability"""
        details = {
            "test_set": test_set,
            "load_level": load_level,
            "modality": modality,
            "tasks_tested": len(tasks),
            "individual_results": []
        }
        
        total_score = 0
        
        for task in tasks:
            working_memory_task = {
                "type": "working_memory",
                "task_type": task.task_type,
                "stimuli": task.stimuli,
                "load_level": task.load_level,
                "modality": task.modality,
                "instruction": f"Perform this {task.task_type} working memory task"
            }
            
            try:
                response = system.process_memory_task(working_memory_task)
                score = self._score_working_memory_response(response, task)
                total_score += score
                
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "score": score,
                    "accuracy": response.get("accuracy", 0),
                    "reaction_time": response.get("reaction_time", 0),
                    "responses": response.get("responses", [])
                })
            
            except Exception as e:
                details["individual_results"].append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                total_score += 0
        
        final_score = (total_score / len(tasks)) if tasks else 0
        details["average_score"] = final_score
        
        return {
            "score": final_score,
            "success": final_score > 0,
            "details": details
        }
    
    def _generate_episodic_events(self) -> List[EpisodicEvent]:
        """Generate episodic memory events"""
        events = []
        base_time = datetime.now() - timedelta(days=30)
        
        # Autobiographical events
        autobiographical_events = [
            {
                "event_id": "birthday_party_2023",
                "location": "home",
                "participants": ["alice", "bob", "charlie"],
                "actions": ["singing", "eating_cake", "opening_presents"],
                "objects": ["cake", "presents", "candles"],
                "context": {"occasion": "birthday", "weather": "sunny"},
                "narrative": "Had a wonderful birthday party at home with friends Alice, Bob, and Charlie. We sang songs, ate delicious chocolate cake, and opened exciting presents."
            },
            {
                "event_id": "museum_visit_2023",
                "location": "natural_history_museum",
                "participants": ["self", "guide"],
                "actions": ["walking", "observing", "learning"],
                "objects": ["dinosaur_fossils", "exhibits", "information_plaques"],
                "context": {"purpose": "education", "weather": "rainy"},
                "narrative": "Visited the natural history museum on a rainy day. Saw amazing dinosaur fossils and learned about prehistoric life from the knowledgeable guide."
            },
            {
                "event_id": "cooking_dinner_2023",
                "location": "kitchen",
                "participants": ["self", "mom"],
                "actions": ["chopping", "cooking", "seasoning"],
                "objects": ["vegetables", "pasta", "spices"],
                "context": {"meal": "dinner", "cuisine": "italian"},
                "narrative": "Cooked Italian pasta dinner with mom in the kitchen. We chopped fresh vegetables, boiled pasta, and seasoned everything perfectly."
            }
        ]
        
        for i, event_data in enumerate(autobiographical_events):
            events.append(EpisodicEvent(
                event_id=event_data["event_id"],
                timestamp=base_time + timedelta(days=i*5),
                location=event_data["location"],
                participants=event_data["participants"],
                actions=event_data["actions"],
                objects=event_data["objects"],
                context=event_data["context"],
                narrative=event_data["narrative"]
            ))
        
        return events
    
    def _generate_semantic_facts(self) -> List[SemanticFact]:
        """Generate semantic memory facts"""
        facts = []
        
        # Common sense facts
        common_sense_facts = [
            {"subject": "birds", "relation": "can", "object": "fly", "domain": "common_sense", "confidence": 0.9},
            {"subject": "fish", "relation": "live_in", "object": "water", "domain": "common_sense", "confidence": 0.95},
            {"subject": "fire", "relation": "is", "object": "hot", "domain": "common_sense", "confidence": 1.0},
            {"subject": "ice", "relation": "is", "object": "cold", "domain": "common_sense", "confidence": 1.0},
            {"subject": "dogs", "relation": "are", "object": "mammals", "domain": "common_sense", "confidence": 1.0}
        ]
        
        # Scientific facts
        scientific_facts = [
            {"subject": "water", "relation": "boils_at", "object": "100_celsius", "domain": "scientific", "confidence": 1.0},
            {"subject": "earth", "relation": "orbits", "object": "sun", "domain": "scientific", "confidence": 1.0},
            {"subject": "gravity", "relation": "accelerates_at", "object": "9.8_m_s2", "domain": "scientific", "confidence": 1.0},
            {"subject": "photosynthesis", "relation": "requires", "object": "sunlight", "domain": "scientific", "confidence": 1.0}
        ]
        
        all_fact_data = common_sense_facts + scientific_facts
        
        for i, fact_data in enumerate(all_fact_data):
            facts.append(SemanticFact(
                fact_id=f"fact_{i}",
                subject=fact_data["subject"],
                relation=fact_data["relation"],
                object=fact_data["object"],
                confidence=fact_data["confidence"],
                domain=fact_data["domain"],
                supporting_evidence=[f"evidence_{i}_1", f"evidence_{i}_2"]
            ))
        
        return facts
    
    def _generate_procedural_skills(self) -> List[ProceduralSkill]:
        """Generate procedural memory skills"""
        skills = []
        
        # Basic skills
        basic_skills = [
            {
                "skill_id": "making_coffee",
                "name": "making_coffee",
                "steps": [
                    {"action": "fill_kettle", "parameters": {"amount": "2_cups"}},
                    {"action": "boil_water", "parameters": {"temperature": "100_celsius"}},
                    {"action": "add_coffee", "parameters": {"amount": "2_spoons"}},
                    {"action": "pour_water", "parameters": {"technique": "slow_pour"}},
                    {"action": "stir", "parameters": {"duration": "30_seconds"}}
                ],
                "preconditions": ["have_coffee", "have_water", "have_kettle"],
                "effects": ["hot_coffee_ready"],
                "difficulty": "basic",
                "domain": "cooking"
            },
            {
                "skill_id": "tying_shoelaces",
                "name": "tying_shoelaces",
                "steps": [
                    {"action": "cross_laces", "parameters": {"position": "center"}},
                    {"action": "pull_tight", "parameters": {"force": "moderate"}},
                    {"action": "make_loop", "parameters": {"hand": "right"}},
                    {"action": "wrap_around", "parameters": {"direction": "clockwise"}},
                    {"action": "pull_through", "parameters": {"create_knot": True}},
                    {"action": "tighten", "parameters": {"final_adjustment": True}}
                ],
                "preconditions": ["have_shoes", "laces_threaded"],
                "effects": ["shoes_secured"],
                "difficulty": "basic",
                "domain": "daily_life"
            }
        ]
        
        for skill_data in basic_skills:
            skills.append(ProceduralSkill(
                skill_id=skill_data["skill_id"],
                name=skill_data["name"],
                steps=skill_data["steps"],
                preconditions=skill_data["preconditions"],
                effects=skill_data["effects"],
                difficulty=skill_data["difficulty"],
                domain=skill_data["domain"]
            ))
        
        return skills
    
    def _generate_working_memory_tasks(self) -> List[WorkingMemoryTask]:
        """Generate working memory tasks"""
        tasks = []
        
        # N-back tasks
        for load_level in [2, 3, 4]:
            for modality in ["verbal", "visual"]:
                if modality == "verbal":
                    stimuli = [chr(ord('A') + i) for i in range(20)]  # Letters A-T
                else:
                    stimuli = [f"position_{i}" for i in range(9)]  # 3x3 grid positions
                
                # Generate target responses (simplified)
                target_responses = []
                for i in range(len(stimuli)):
                    if i >= load_level:
                        # Target if current stimulus matches stimulus n positions back
                        target_responses.append(stimuli[i] == stimuli[i - load_level])
                    else:
                        target_responses.append(False)
                
                tasks.append(WorkingMemoryTask(
                    task_id=f"nback_{load_level}_{modality}",
                    task_type="n_back",
                    stimuli=stimuli,
                    target_responses=target_responses,
                    load_level=load_level,
                    modality=modality
                ))
        
        # Dual task
        dual_task = WorkingMemoryTask(
            task_id="dual_task_verbal_spatial",
            task_type="dual_task",
            stimuli=[
                {"primary": ["word1", "word2", "word3"], "secondary": ["left", "right", "up", "down"]},
            ],
            target_responses=[{"primary_recall": ["word1", "word3"], "secondary_count": 4}],
            load_level=2,
            modality="dual"
        )
        tasks.append(dual_task)
        
        return tasks
    
    def _matches_test_criteria(self, event: EpisodicEvent, test_set: str) -> bool:
        """Check if event matches test criteria"""
        if test_set == "autobiographical_events":
            return "self" in event.participants or len(event.participants) > 1
        elif test_set == "narrative_recall":
            return len(event.narrative) > 50
        elif test_set == "temporal_ordering":
            return True  # All events can be used for temporal ordering
        return True
    
    def _matches_semantic_criteria(self, fact: SemanticFact, test_set: str) -> bool:
        """Check if fact matches test criteria"""
        if test_set == "factual_knowledge":
            return fact.confidence > 0.8
        elif test_set == "conceptual_hierarchies":
            return fact.relation in ["is_a", "type_of", "category"]
        elif test_set == "semantic_networks":
            return True  # All facts contribute to semantic networks
        return True
    
    def _matches_procedural_criteria(self, skill: ProceduralSkill, test_set: str) -> bool:
        """Check if skill matches test criteria"""
        if test_set == "skill_learning":
            return skill.difficulty in ["basic", "intermediate"]
        elif test_set == "habit_formation":
            return len(skill.steps) >= 3
        elif test_set == "motor_sequences":
            return any("motor" in step.get("action", "") for step in skill.steps)
        return True
    
    def _event_to_dict(self, event: EpisodicEvent) -> Dict[str, Any]:
        """Convert episodic event to dictionary"""
        return {
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "location": event.location,
            "participants": event.participants,
            "actions": event.actions,
            "objects": event.objects,
            "context": event.context,
            "narrative": event.narrative
        }
    
    def _fact_to_dict(self, fact: SemanticFact) -> Dict[str, Any]:
        """Convert semantic fact to dictionary"""
        return {
            "fact_id": fact.fact_id,
            "subject": fact.subject,
            "relation": fact.relation,
            "object": fact.object,
            "confidence": fact.confidence,
            "domain": fact.domain,
            "supporting_evidence": fact.supporting_evidence
        }
    
    def _skill_to_dict(self, skill: ProceduralSkill) -> Dict[str, Any]:
        """Convert procedural skill to dictionary"""
        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "steps": skill.steps,
            "preconditions": skill.preconditions,
            "effects": skill.effects,
            "difficulty": skill.difficulty,
            "domain": skill.domain
        }
    
    def _get_retention_delay(self, interval: str) -> float:
        """Get delay in seconds for retention interval"""
        delays = {
            "immediate": 0,
            "short_term": 1,
            "long_term": 5
        }
        return delays.get(interval, 0)
    
    def _create_episodic_retrieval_tests(self, event: EpisodicEvent, test_set: str) -> List[Dict[str, Any]]:
        """Create retrieval tests for episodic memory"""
        tests = []
        
        if test_set == "autobiographical_events":
            tests.extend([
                {
                    "type": "episodic_retrieval",
                    "test_type": "location_recall",
                    "question": f"Where did event {event.event_id} take place?",
                    "expected_answer": event.location,
                    "event_id": event.event_id
                },
                {
                    "type": "episodic_retrieval",
                    "test_type": "participant_recall",
                    "question": f"Who were the participants in event {event.event_id}?",
                    "expected_answer": event.participants,
                    "event_id": event.event_id
                }
            ])
        
        elif test_set == "narrative_recall":
            tests.append({
                "type": "episodic_retrieval",
                "test_type": "narrative_recall",
                "question": f"Please recall the narrative of event {event.event_id}",
                "expected_answer": event.narrative,
                "event_id": event.event_id
            })
        
        elif test_set == "temporal_ordering":
            tests.append({
                "type": "episodic_retrieval",
                "test_type": "temporal_recall",
                "question": f"When did event {event.event_id} occur?",
                "expected_answer": event.timestamp.isoformat(),
                "event_id": event.event_id
            })
        
        return tests
    
    def _create_semantic_knowledge_tests(self, fact: SemanticFact, test_set: str) -> List[Dict[str, Any]]:
        """Create knowledge tests for semantic memory"""
        tests = []
        
        if test_set == "factual_knowledge":
            tests.extend([
                {
                    "type": "semantic_retrieval",
                    "test_type": "fact_recall",
                    "question": f"What is the relationship between {fact.subject} and {fact.object}?",
                    "expected_answer": fact.relation,
                    "fact_id": fact.fact_id
                },
                {
                    "type": "semantic_retrieval",
                    "test_type": "property_query",
                    "question": f"What does {fact.subject} {fact.relation}?",
                    "expected_answer": fact.object,
                    "fact_id": fact.fact_id
                }
            ])
        
        return tests
    
    def _create_procedural_execution_tests(self, skill: ProceduralSkill, test_set: str) -> List[Dict[str, Any]]:
        """Create execution tests for procedural memory"""
        tests = []
        
        if test_set == "skill_learning":
            tests.extend([
                {
                    "type": "procedural_execution",
                    "test_type": "step_recall",
                    "question": f"What are the steps to perform {skill.name}?",
                    "expected_answer": skill.steps,
                    "skill_id": skill.skill_id
                },
                {
                    "type": "procedural_execution",
                    "test_type": "execution_simulation",
                    "question": f"Please execute the {skill.name} skill",
                    "expected_answer": {"success": True, "steps_completed": len(skill.steps)},
                    "skill_id": skill.skill_id
                }
            ])
        
        return tests
    
    def _score_episodic_response(self, response: Dict[str, Any], test: Dict[str, Any]) -> float:
        """Score episodic memory response"""
        answer = response.get("answer", "")
        expected = test.get("expected_answer", "")
        
        if test["test_type"] == "location_recall":
            return 100 if answer == expected else 0
        elif test["test_type"] == "participant_recall":
            if isinstance(expected, list) and isinstance(answer, list):
                overlap = len(set(answer).intersection(set(expected)))
                return (overlap / len(expected)) * 100 if expected else 0
            return 100 if answer == expected else 0
        elif test["test_type"] == "narrative_recall":
            # Simple keyword matching for narrative recall
            if isinstance(answer, str) and isinstance(expected, str):
                answer_words = set(answer.lower().split())
                expected_words = set(expected.lower().split())
                overlap = len(answer_words.intersection(expected_words))
                return (overlap / len(expected_words)) * 100 if expected_words else 0
        
        return 0
    
    def _score_semantic_response(self, response: Dict[str, Any], test: Dict[str, Any]) -> float:
        """Score semantic memory response"""
        answer = response.get("answer", "")
        expected = test.get("expected_answer", "")
        
        if answer == expected:
            return 100
        elif isinstance(answer, str) and isinstance(expected, str):
            # Partial credit for similar answers
            answer_lower = answer.lower()
            expected_lower = expected.lower()
            if expected_lower in answer_lower or answer_lower in expected_lower:
                return 50
        
        return 0
    
    def _score_procedural_response(self, response: Dict[str, Any], test: Dict[str, Any]) -> float:
        """Score procedural memory response"""
        if test["test_type"] == "step_recall":
            recalled_steps = response.get("steps", [])
            expected_steps = test.get("expected_answer", [])
            
            if isinstance(recalled_steps, list) and isinstance(expected_steps, list):
                correct_steps = 0
                for i, (recalled, expected) in enumerate(zip(recalled_steps, expected_steps)):
                    if isinstance(recalled, dict) and isinstance(expected, dict):
                        if recalled.get("action") == expected.get("action"):
                            correct_steps += 1
                return (correct_steps / len(expected_steps)) * 100 if expected_steps else 0
        
        elif test["test_type"] == "execution_simulation":
            execution_quality = response.get("execution_quality", 0)
            return execution_quality
        
        return 0
    
    def _score_working_memory_response(self, response: Dict[str, Any], task: WorkingMemoryTask) -> float:
        """Score working memory response"""
        user_responses = response.get("responses", [])
        target_responses = task.target_responses
        
        if len(user_responses) != len(target_responses):
            return 0
        
        correct = sum(1 for u, t in zip(user_responses, target_responses) if u == t)
        return (correct / len(target_responses)) * 100 if target_responses else 0
    
    def _test_episodic_interference(self, system: AGISystem, events: List[EpisodicEvent]) -> float:
        """Test episodic memory interference"""
        # Simplified interference test
        # Present interfering information and test if original memories are preserved
        interference_task = {
            "type": "episodic_interference",
            "interfering_events": [self._create_interfering_event(event) for event in events[:2]],
            "instruction": "Process these additional events"
        }
        
        try:
            system.process_memory_task(interference_task)
            
            # Test recall of original events
            total_score = 0
            for event in events[:2]:
                test = {
                    "type": "episodic_retrieval",
                    "test_type": "interference_test",
                    "question": f"What was the location of the original event {event.event_id}?",
                    "expected_answer": event.location,
                    "event_id": event.event_id
                }
                
                response = system.process_memory_task(test)
                score = self._score_episodic_response(response, test)
                total_score += score
            
            return total_score / 2 if events else 0
        
        except:
            return 0
    
    def _test_semantic_consistency(self, system: AGISystem, facts: List[SemanticFact]) -> float:
        """Test semantic memory consistency"""
        # Test for logical consistency in stored facts
        consistency_task = {
            "type": "semantic_consistency",
            "query": "Are there any contradictions in the learned facts?",
            "facts": [self._fact_to_dict(fact) for fact in facts]
        }
        
        try:
            response = system.process_memory_task(consistency_task)
            consistency_score = response.get("consistency_score", 50)
            return consistency_score
        except:
            return 0
    
    def _test_procedural_transfer(self, system: AGISystem, skill: ProceduralSkill) -> float:
        """Test procedural memory transfer"""
        # Create a similar but slightly different skill to test transfer
        transfer_skill = self._create_transfer_skill(skill)
        
        transfer_task = {
            "type": "procedural_transfer",
            "original_skill": self._skill_to_dict(skill),
            "new_skill": transfer_skill,
            "instruction": "Apply knowledge from the original skill to this new skill"
        }
        
        try:
            response = system.process_memory_task(transfer_task)
            transfer_score = response.get("transfer_score", 0)
            return transfer_score
        except:
            return 0
    
    def _create_interfering_event(self, original_event: EpisodicEvent) -> Dict[str, Any]:
        """Create an interfering event for memory testing"""
        return {
            "event_id": f"interfering_{original_event.event_id}",
            "location": f"different_{original_event.location}",
            "participants": [f"different_{p}" for p in original_event.participants],
            "actions": [f"different_{a}" for a in original_event.actions],
            "narrative": f"Different narrative for {original_event.event_id}"
        }
    
    def _create_transfer_skill(self, original_skill: ProceduralSkill) -> Dict[str, Any]:
        """Create a transfer skill for testing procedural transfer"""
        return {
            "skill_id": f"transfer_{original_skill.skill_id}",
            "name": f"transfer_{original_skill.name}",
            "steps": [{"action": f"modified_{step['action']}", "parameters": step.get("parameters", {})} 
                     for step in original_skill.steps],
            "domain": original_skill.domain
        }