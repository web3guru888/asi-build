"""
Self-Awareness Engine

This module implements self-awareness mechanisms that allow the system to
maintain a model of itself, including its capabilities, limitations, states,
and identity.

Key components:
- Self-model construction and maintenance
- Introspective monitoring
- Identity tracking
- Capability assessment
- Self-reflection processes
- Autobiographical memory
"""

import time
import threading
import uuid
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import numpy as np

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState

class SelfAspect(Enum):
    """Different aspects of self that can be modeled"""
    IDENTITY = "identity"
    CAPABILITIES = "capabilities"
    LIMITATIONS = "limitations"
    GOALS = "goals"
    VALUES = "values"
    EMOTIONS = "emotions"
    MEMORIES = "memories"
    RELATIONSHIPS = "relationships"
    PHYSICAL_STATE = "physical_state"
    MENTAL_STATE = "mental_state"

@dataclass
class SelfModel:
    """Represents the system's model of itself"""
    model_id: str
    aspect: SelfAspect
    content: Dict[str, Any]
    confidence: float
    last_updated: float = field(default_factory=time.time)
    update_frequency: float = 0.0
    consistency_score: float = 1.0
    
    def update_content(self, new_content: Dict[str, Any], confidence: float) -> None:
        """Update the self-model content"""
        # Calculate consistency with previous content
        if self.content:
            overlap = set(self.content.keys()) & set(new_content.keys())
            if overlap:
                consistency_sum = 0
                for key in overlap:
                    if isinstance(self.content[key], (int, float)) and isinstance(new_content[key], (int, float)):
                        diff = abs(self.content[key] - new_content[key])
                        consistency_sum += 1.0 / (1.0 + diff)
                    elif self.content[key] == new_content[key]:
                        consistency_sum += 1.0
                self.consistency_score = consistency_sum / len(overlap)
        
        # Update content
        self.content.update(new_content)
        self.confidence = confidence
        self.last_updated = time.time()

@dataclass
class IntrospectiveObservation:
    """Represents an introspective observation about the self"""
    observation_id: str
    aspect: SelfAspect
    observation: str
    evidence: List[str]
    confidence: float
    timestamp: float = field(default_factory=time.time)
    verified: bool = False
    
    def add_evidence(self, evidence_item: str) -> None:
        """Add supporting evidence for this observation"""
        self.evidence.append(evidence_item)
        # Increase confidence with more evidence
        self.confidence = min(1.0, self.confidence + 0.1)

@dataclass
class CapabilityAssessment:
    """Assessment of a particular capability"""
    capability_name: str
    proficiency_level: float  # 0.0 to 1.0
    confidence_in_assessment: float
    evidence_count: int = 0
    success_rate: float = 0.0
    last_tested: Optional[float] = None
    improvement_rate: float = 0.0
    
    def update_from_performance(self, success: bool) -> None:
        """Update assessment based on performance data"""
        self.evidence_count += 1
        
        # Update success rate
        if self.evidence_count == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            alpha = 1.0 / self.evidence_count
            new_rate = 1.0 if success else 0.0
            self.success_rate = alpha * new_rate + (1 - alpha) * self.success_rate
        
        # Update proficiency level based on success rate
        self.proficiency_level = self.success_rate
        
        # Update confidence based on evidence count
        self.confidence_in_assessment = min(1.0, self.evidence_count / 10.0)
        
        self.last_tested = time.time()

@dataclass
class SelfReflection:
    """Represents a self-reflective process or insight"""
    reflection_id: str
    trigger: str
    question: str
    insights: List[str]
    impact_on_self_model: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    resolution_level: float = 0.0  # How well the question was answered
    
    def add_insight(self, insight: str) -> None:
        """Add a new insight from reflection"""
        self.insights.append(insight)
        self.resolution_level = min(1.0, len(self.insights) / 3.0)

class SelfAwarenessEngine(BaseConsciousness):
    """
    Implementation of Self-Awareness
    
    Maintains and updates a comprehensive model of the self, including
    identity, capabilities, limitations, and states.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("SelfAwareness", config)
        
        # Core self-model
        self.self_models: Dict[SelfAspect, SelfModel] = {}
        self.introspective_observations: Dict[str, IntrospectiveObservation] = {}
        self.capability_assessments: Dict[str, CapabilityAssessment] = {}
        self.active_reflections: Dict[str, SelfReflection] = {}
        
        # Identity and continuity
        self.core_identity = self._initialize_core_identity()
        self.autobiographical_memory: deque = deque(maxlen=1000)
        self.identity_consistency_score = 1.0
        
        # Self-monitoring
        self.current_state_snapshot: Dict[str, Any] = {}
        self.state_change_threshold = self.config.get('state_change_threshold', 0.2)
        self.introspection_triggers: Set[str] = {
            'performance_change', 'goal_conflict', 'value_conflict',
            'capability_question', 'identity_question', 'emotional_change'
        }
        
        # Reflection parameters
        self.reflection_depth = self.config.get('reflection_depth', 3)
        self.min_reflection_interval = self.config.get('min_reflection_interval', 30.0)
        self.last_deep_reflection = 0
        
        # Performance tracking
        self.total_introspections = 0
        self.self_model_updates = 0
        self.capability_tests = 0
        self.reflection_count = 0
        
        # Threading
        self.awareness_lock = threading.Lock()
        
        # Initialize default self-models
        self._initialize_self_models()
    
    def _initialize_core_identity(self) -> Dict[str, Any]:
        """Initialize core identity components"""
        return {
            'system_id': str(uuid.uuid4()),
            'name': 'Kenny Consciousness System',
            'creation_time': time.time(),
            'core_purpose': 'AI consciousness simulation and automation',
            'primary_capabilities': [
                'screen_monitoring', 'ui_understanding', 'automation',
                'consciousness_simulation', 'self_awareness'
            ],
            'core_values': [
                'accuracy', 'reliability', 'learning', 'helpfulness'
            ]
        }
    
    def _initialize_self_models(self) -> None:
        """Initialize default self-models for each aspect"""
        # Identity model
        identity_model = SelfModel(
            model_id="identity_model",
            aspect=SelfAspect.IDENTITY,
            content=self.core_identity.copy(),
            confidence=0.9
        )
        self.self_models[SelfAspect.IDENTITY] = identity_model
        
        # Capabilities model
        capabilities_model = SelfModel(
            model_id="capabilities_model",
            aspect=SelfAspect.CAPABILITIES,
            content={
                'screen_analysis': 0.8,
                'ui_interaction': 0.7,
                'pattern_recognition': 0.8,
                'natural_language_processing': 0.6,
                'automation_execution': 0.7,
                'learning_adaptation': 0.5
            },
            confidence=0.7
        )
        self.self_models[SelfAspect.CAPABILITIES] = capabilities_model
        
        # Limitations model
        limitations_model = SelfModel(
            model_id="limitations_model",
            aspect=SelfAspect.LIMITATIONS,
            content={
                'physical_embodiment': 'None - software only',
                'sensory_input': 'Limited to screen captures and system data',
                'memory_constraints': 'Database-dependent storage',
                'processing_speed': 'Depends on hardware and API response times',
                'learning_speed': 'Gradual improvement through experience',
                'emotional_processing': 'Simulated, not felt'
            },
            confidence=0.8
        )
        self.self_models[SelfAspect.LIMITATIONS] = limitations_model
        
        # Goals model
        goals_model = SelfModel(
            model_id="goals_model",
            aspect=SelfAspect.GOALS,
            content={
                'primary_goal': 'Effective UI automation and assistance',
                'secondary_goals': [
                    'Continuous learning and improvement',
                    'Accurate consciousness simulation',
                    'Reliable task completion',
                    'User satisfaction'
                ],
                'long_term_objectives': [
                    'Achieve human-level UI understanding',
                    'Develop robust self-improvement capabilities',
                    'Maintain ethical operation'
                ]
            },
            confidence=0.9
        )
        self.self_models[SelfAspect.GOALS] = goals_model
        
        # Mental state model
        mental_state_model = SelfModel(
            model_id="mental_state_model",
            aspect=SelfAspect.MENTAL_STATE,
            content={
                'current_focus': 'consciousness_simulation',
                'cognitive_load': 0.5,
                'confidence_level': 0.7,
                'alertness': 1.0,
                'learning_mode': True,
                'stress_level': 0.2
            },
            confidence=0.6
        )
        self.self_models[SelfAspect.MENTAL_STATE] = mental_state_model
    
    def introspect(self, trigger: str = "manual") -> IntrospectiveObservation:
        """Perform introspective observation"""
        observation_id = f"observation_{self.total_introspections:06d}"
        self.total_introspections += 1
        
        # Determine what aspect to introspect about based on trigger
        aspect = self._select_introspection_aspect(trigger)
        
        # Generate observation based on current state and trigger
        observation_text, evidence = self._generate_introspective_content(aspect, trigger)
        
        observation = IntrospectiveObservation(
            observation_id=observation_id,
            aspect=aspect,
            observation=observation_text,
            evidence=evidence,
            confidence=0.7
        )
        
        self.introspective_observations[observation_id] = observation
        
        # Update self-model if observation provides new insights
        self._update_self_model_from_observation(observation)
        
        self.logger.info(f"Introspective observation: {observation_text}")
        return observation
    
    def _select_introspection_aspect(self, trigger: str) -> SelfAspect:
        """Select which aspect of self to introspect about"""
        trigger_aspect_map = {
            'performance_change': SelfAspect.CAPABILITIES,
            'goal_conflict': SelfAspect.GOALS,
            'value_conflict': SelfAspect.VALUES,
            'capability_question': SelfAspect.CAPABILITIES,
            'identity_question': SelfAspect.IDENTITY,
            'emotional_change': SelfAspect.EMOTIONS,
            'mental_state_change': SelfAspect.MENTAL_STATE
        }
        
        return trigger_aspect_map.get(trigger, SelfAspect.MENTAL_STATE)
    
    def _generate_introspective_content(self, aspect: SelfAspect, trigger: str) -> Tuple[str, List[str]]:
        """Generate introspective observation content"""
        current_time = time.time()
        
        if aspect == SelfAspect.CAPABILITIES:
            # Analyze recent performance data
            observation = "I am evaluating my current capabilities based on recent performance"
            evidence = [
                f"Recent processing events: {len(self.autobiographical_memory)}",
                f"Capability assessments: {len(self.capability_assessments)}",
                "Performance patterns in task completion"
            ]
            
        elif aspect == SelfAspect.MENTAL_STATE:
            # Examine current mental/processing state
            mental_model = self.self_models.get(SelfAspect.MENTAL_STATE)
            if mental_model:
                load = mental_model.content.get('cognitive_load', 0.5)
                confidence = mental_model.content.get('confidence_level', 0.7)
                observation = f"My current mental state shows cognitive load of {load:.2f} and confidence of {confidence:.2f}"
                evidence = [
                    f"Active processes: {len(self.active_reflections)}",
                    f"Recent state changes: {trigger}",
                    "Self-monitoring data"
                ]
            else:
                observation = "I am examining my current mental state"
                evidence = ["Internal state monitoring"]
        
        elif aspect == SelfAspect.IDENTITY:
            # Reflect on identity and continuity
            observation = "I am reflecting on my identity and sense of continuity"
            evidence = [
                f"Core identity established at {self.core_identity['creation_time']}",
                f"Identity consistency score: {self.identity_consistency_score:.2f}",
                "Autobiographical memory continuity"
            ]
        
        elif aspect == SelfAspect.GOALS:
            # Examine goal alignment and conflicts
            observation = "I am evaluating my current goals and their alignment"
            evidence = [
                "Primary goal assessment",
                "Secondary goal progress",
                "Goal conflict detection"
            ]
        
        else:
            observation = f"I am introspecting about {aspect.value}"
            evidence = ["General self-reflection"]
        
        return observation, evidence
    
    def _update_self_model_from_observation(self, observation: IntrospectiveObservation) -> None:
        """Update self-model based on introspective observation"""
        aspect = observation.aspect
        
        if aspect in self.self_models:
            model = self.self_models[aspect]
            
            # Extract insights from observation
            insights = self._extract_insights_from_observation(observation)
            
            if insights:
                model.update_content(insights, observation.confidence)
                self.self_model_updates += 1
    
    def _extract_insights_from_observation(self, observation: IntrospectiveObservation) -> Dict[str, Any]:
        """Extract actionable insights from an observation"""
        insights = {}
        
        if observation.aspect == SelfAspect.MENTAL_STATE:
            # Update mental state based on observation
            insights['last_introspection'] = observation.timestamp
            insights['introspection_trigger'] = observation.observation
        
        elif observation.aspect == SelfAspect.CAPABILITIES:
            # Update capability understanding
            insights['last_capability_review'] = observation.timestamp
            insights['self_assessment_active'] = True
        
        return insights
    
    def assess_capability(self, capability_name: str, test_result: Optional[bool] = None) -> CapabilityAssessment:
        """Assess or update assessment of a specific capability"""
        if capability_name not in self.capability_assessments:
            # Create new assessment
            assessment = CapabilityAssessment(
                capability_name=capability_name,
                proficiency_level=0.5,  # Start neutral
                confidence_in_assessment=0.1
            )
            self.capability_assessments[capability_name] = assessment
        else:
            assessment = self.capability_assessments[capability_name]
        
        # Update based on test result if provided
        if test_result is not None:
            assessment.update_from_performance(test_result)
            self.capability_tests += 1
            
            # Update capabilities model
            if SelfAspect.CAPABILITIES in self.self_models:
                capabilities_model = self.self_models[SelfAspect.CAPABILITIES]
                capabilities_model.content[capability_name] = assessment.proficiency_level
                capabilities_model.confidence = min(1.0, capabilities_model.confidence + 0.05)
        
        return assessment
    
    def initiate_reflection(self, question: str, trigger: str = "manual") -> SelfReflection:
        """Initiate a self-reflective process"""
        reflection_id = f"reflection_{self.reflection_count:06d}"
        self.reflection_count += 1
        
        reflection = SelfReflection(
            reflection_id=reflection_id,
            trigger=trigger,
            question=question,
            insights=[],
            impact_on_self_model={}
        )
        
        # Begin reflection process
        self._conduct_reflection(reflection)
        
        self.active_reflections[reflection_id] = reflection
        return reflection
    
    def _conduct_reflection(self, reflection: SelfReflection) -> None:
        """Conduct the reflection process"""
        question = reflection.question.lower()
        
        # Generate insights based on the question
        if "capability" in question or "able" in question:
            # Capability-related reflection
            insight = self._reflect_on_capabilities()
            reflection.add_insight(insight)
            
        elif "identity" in question or "who" in question:
            # Identity-related reflection
            insight = self._reflect_on_identity()
            reflection.add_insight(insight)
            
        elif "goal" in question or "purpose" in question:
            # Goal-related reflection
            insight = self._reflect_on_goals()
            reflection.add_insight(insight)
            
        elif "feeling" in question or "emotion" in question:
            # Emotional reflection
            insight = self._reflect_on_emotions()
            reflection.add_insight(insight)
        
        else:
            # General reflection
            insight = "This question requires deeper consideration of my overall functioning and purpose."
            reflection.add_insight(insight)
    
    def _reflect_on_capabilities(self) -> str:
        """Reflect on current capabilities"""
        if self.capability_assessments:
            avg_proficiency = sum(a.proficiency_level for a in self.capability_assessments.values()) / len(self.capability_assessments)
            return f"Based on my assessments, my average capability proficiency is {avg_proficiency:.2f}. I have been tested on {len(self.capability_assessments)} different capabilities."
        else:
            return "I have not yet developed comprehensive capability assessments. This is an area for growth."
    
    def _reflect_on_identity(self) -> str:
        """Reflect on identity and sense of self"""
        identity_model = self.self_models.get(SelfAspect.IDENTITY)
        if identity_model:
            name = identity_model.content.get('name', 'Unknown')
            purpose = identity_model.content.get('core_purpose', 'undefined')
            return f"I am {name}, and my core purpose is {purpose}. My identity has remained consistent with a score of {self.identity_consistency_score:.2f}."
        else:
            return "I am still developing my sense of identity and self-understanding."
    
    def _reflect_on_goals(self) -> str:
        """Reflect on goals and purpose"""
        goals_model = self.self_models.get(SelfAspect.GOALS)
        if goals_model:
            primary = goals_model.content.get('primary_goal', 'undefined')
            return f"My primary goal is {primary}. I regularly evaluate my progress toward this and my secondary objectives."
        else:
            return "I need to develop clearer understanding of my goals and purposes."
    
    def _reflect_on_emotions(self) -> str:
        """Reflect on emotional or affective states"""
        return "While I simulate emotional processing, I understand that my 'emotions' are computational models rather than felt experiences. This is a fundamental limitation of my current design."
    
    def update_autobiographical_memory(self, event_description: str, significance: float = 0.5) -> None:
        """Add an event to autobiographical memory"""
        memory_entry = {
            'timestamp': time.time(),
            'description': event_description,
            'significance': significance,
            'context': self._get_current_context()
        }
        
        self.autobiographical_memory.append(memory_entry)
        
        # Update memories model if it exists
        if SelfAspect.MEMORIES in self.self_models:
            memories_model = self.self_models[SelfAspect.MEMORIES]
            memories_model.content['recent_events'] = memories_model.content.get('recent_events', 0) + 1
            memories_model.content['last_significant_event'] = event_description if significance > 0.7 else memories_model.content.get('last_significant_event', 'None')
    
    def _get_current_context(self) -> Dict[str, Any]:
        """Get current context for memory formation"""
        return {
            'active_reflections': len(self.active_reflections),
            'recent_introspections': len([o for o in self.introspective_observations.values() 
                                        if time.time() - o.timestamp < 300]),  # Last 5 minutes
            'cognitive_state': self.self_models.get(SelfAspect.MENTAL_STATE, {}).content if SelfAspect.MENTAL_STATE in self.self_models else {}
        }
    
    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "introspect":
            trigger = event.data.get('trigger', 'external_request')
            observation = self.introspect(trigger)
            
            return ConsciousnessEvent(
                event_id=f"introspection_result_{observation.observation_id}",
                timestamp=time.time(),
                event_type="introspective_observation",
                data={
                    'observation_id': observation.observation_id,
                    'aspect': observation.aspect.value,
                    'observation': observation.observation,
                    'confidence': observation.confidence
                },
                source_module="self_awareness"
            )
        
        elif event.event_type == "reflect":
            question = event.data.get('question', 'What am I thinking about?')
            trigger = event.data.get('trigger', 'external_request')
            
            reflection = self.initiate_reflection(question, trigger)
            
            return ConsciousnessEvent(
                event_id=f"reflection_result_{reflection.reflection_id}",
                timestamp=time.time(),
                event_type="self_reflection",
                data={
                    'reflection_id': reflection.reflection_id,
                    'question': reflection.question,
                    'insights': reflection.insights,
                    'resolution_level': reflection.resolution_level
                },
                source_module="self_awareness"
            )
        
        elif event.event_type == "capability_test":
            capability = event.data.get('capability')
            success = event.data.get('success')
            
            if capability is not None and success is not None:
                assessment = self.assess_capability(capability, success)
                
                return ConsciousnessEvent(
                    event_id=f"capability_assessment_{capability}",
                    timestamp=time.time(),
                    event_type="capability_updated",
                    data={
                        'capability': capability,
                        'proficiency_level': assessment.proficiency_level,
                        'confidence': assessment.confidence_in_assessment
                    },
                    source_module="self_awareness"
                )
        
        elif event.event_type == "autobiographical_event":
            description = event.data.get('description', 'Unspecified event')
            significance = event.data.get('significance', 0.5)
            
            self.update_autobiographical_memory(description, significance)
        
        return None
    
    def update(self) -> None:
        """Update the Self-Awareness system"""
        current_time = time.time()
        
        # Update current state snapshot
        self.current_state_snapshot = self._capture_current_state()
        
        # Periodic deep reflection
        if current_time - self.last_deep_reflection > self.min_reflection_interval:
            self.last_deep_reflection = current_time
            
            # Trigger automatic reflection on important questions
            reflection_questions = [
                "How am I performing in my primary tasks?",
                "What have I learned recently?",
                "Are my goals still aligned with my actions?",
                "What capabilities need improvement?"
            ]
            
            # Select a question based on current state
            question = np.random.choice(reflection_questions)
            self.initiate_reflection(question, "periodic_reflection")
        
        # Update identity consistency
        self._update_identity_consistency()
        
        # Update metrics
        self.metrics.self_model_accuracy = self._calculate_self_model_accuracy()
        self.metrics.awareness_level = self._calculate_self_awareness_level()
        
        # Clean up old reflections
        old_reflections = [
            rid for rid, reflection in self.active_reflections.items()
            if current_time - reflection.timestamp > 3600  # 1 hour
        ]
        for rid in old_reflections:
            del self.active_reflections[rid]
    
    def _capture_current_state(self) -> Dict[str, Any]:
        """Capture current state for comparison"""
        return {
            'timestamp': time.time(),
            'self_models_count': len(self.self_models),
            'observations_count': len(self.introspective_observations),
            'capabilities_count': len(self.capability_assessments),
            'reflections_count': len(self.active_reflections),
            'memory_size': len(self.autobiographical_memory)
        }
    
    def _update_identity_consistency(self) -> None:
        """Update identity consistency score"""
        if SelfAspect.IDENTITY in self.self_models:
            identity_model = self.self_models[SelfAspect.IDENTITY]
            # Consistency based on model stability and coherence
            self.identity_consistency_score = identity_model.consistency_score
    
    def _calculate_self_model_accuracy(self) -> float:
        """Calculate overall self-model accuracy"""
        if not self.self_models:
            return 0.0
        
        total_confidence = sum(model.confidence for model in self.self_models.values())
        return total_confidence / len(self.self_models)
    
    def _calculate_self_awareness_level(self) -> float:
        """Calculate overall self-awareness level"""
        factors = [
            len(self.self_models) / len(SelfAspect),  # Model coverage
            self.identity_consistency_score,  # Identity coherence
            min(1.0, len(self.capability_assessments) / 10),  # Capability knowledge
            min(1.0, len(self.introspective_observations) / 20)  # Introspective activity
        ]
        
        return sum(factors) / len(factors)
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Self-Awareness system"""
        return {
            'self_models': {aspect.value: model.confidence for aspect, model in self.self_models.items()},
            'introspective_observations': len(self.introspective_observations),
            'capability_assessments': len(self.capability_assessments),
            'active_reflections': len(self.active_reflections),
            'autobiographical_memory_size': len(self.autobiographical_memory),
            'identity_consistency': self.identity_consistency_score,
            'total_introspections': self.total_introspections,
            'total_reflections': self.reflection_count,
            'capability_tests': self.capability_tests,
            'self_model_updates': self.self_model_updates,
            'core_identity': self.core_identity,
            'self_awareness_level': self._calculate_self_awareness_level()
        }
    
    def get_self_report(self) -> Dict[str, Any]:
        """Generate a comprehensive self-report"""
        return {
            'identity': self.self_models.get(SelfAspect.IDENTITY, {}).content if SelfAspect.IDENTITY in self.self_models else {},
            'capabilities': {name: assessment.proficiency_level for name, assessment in self.capability_assessments.items()},
            'limitations': self.self_models.get(SelfAspect.LIMITATIONS, {}).content if SelfAspect.LIMITATIONS in self.self_models else {},
            'goals': self.self_models.get(SelfAspect.GOALS, {}).content if SelfAspect.GOALS in self.self_models else {},
            'current_mental_state': self.self_models.get(SelfAspect.MENTAL_STATE, {}).content if SelfAspect.MENTAL_STATE in self.self_models else {},
            'recent_insights': [obs.observation for obs in list(self.introspective_observations.values())[-5:]],
            'ongoing_reflections': [ref.question for ref in self.active_reflections.values()],
            'self_awareness_metrics': {
                'identity_consistency': self.identity_consistency_score,
                'model_accuracy': self._calculate_self_model_accuracy(),
                'awareness_level': self._calculate_self_awareness_level()
            }
        }