"""
Human-AGI Collaborative Creation Tools

This module implements sophisticated tools for human-AGI collaboration in creative processes,
enabling seamless interaction, shared creativity, and augmented artistic expression.
"""

import numpy as np
import torch
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import time
import json
from queue import Queue
import threading
import asyncio


class CollaborationMode(Enum):
    """Different modes of human-AGI collaboration."""
    COOPERATIVE = "cooperative"  # Working together on same goals
    COMPETITIVE = "competitive"  # Creative challenges and games
    MENTORING = "mentoring"  # AGI learning from human expertise
    AUGMENTATIVE = "augmentative"  # AGI enhancing human capabilities
    ITERATIVE = "iterative"  # Turn-based creative development
    REAL_TIME = "real_time"  # Simultaneous creative input


class InteractionType(Enum):
    """Types of creative interactions."""
    SKETCH = "sketch"
    TEXT_INPUT = "text_input"
    VOICE_COMMAND = "voice_command"
    GESTURE = "gesture"
    SELECTION = "selection"
    MODIFICATION = "modification"
    FEEDBACK = "feedback"
    EVALUATION = "evaluation"


@dataclass
class CreativeAction:
    """Represents a creative action by human or AGI."""
    action_id: str
    actor: str  # "human" or "agi"
    action_type: InteractionType
    timestamp: float
    content: Any
    context: Dict[str, Any]
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollaborativeSession:
    """Represents a collaborative creative session."""
    session_id: str
    participants: List[str]
    mode: CollaborationMode
    domain: str  # art domain
    start_time: float
    actions: List[CreativeAction] = field(default_factory=list)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    current_artifact: Optional[Any] = None


@dataclass
class HumanProfile:
    """Profile of human collaborator for personalized interaction."""
    user_id: str
    name: str
    expertise_level: str  # beginner, intermediate, expert
    preferred_domains: List[str]
    creative_style: Dict[str, float]  # personality traits for creativity
    collaboration_preferences: Dict[str, Any]
    past_sessions: List[str] = field(default_factory=list)
    learning_progress: Dict[str, float] = field(default_factory=dict)


class CreativeIntentRecognizer:
    """Recognizes and interprets human creative intent from various inputs."""
    
    def __init__(self):
        self.intent_patterns = {}
        self.context_memory = []
        self.intent_history = []
        
    def recognize_intent(self, action: CreativeAction, 
                        context: Dict[str, Any]) -> Dict[str, Any]:
        """Recognize creative intent from human action."""
        intent = {
            'primary_intent': self._classify_primary_intent(action),
            'secondary_intents': self._identify_secondary_intents(action, context),
            'confidence': self._calculate_intent_confidence(action, context),
            'temporal_context': self._analyze_temporal_context(action),
            'emotional_context': self._analyze_emotional_context(action)
        }
        
        self.intent_history.append(intent)
        return intent
        
    def _classify_primary_intent(self, action: CreativeAction) -> str:
        """Classify the primary creative intent."""
        if action.action_type == InteractionType.SKETCH:
            return self._analyze_sketch_intent(action.content)
        elif action.action_type == InteractionType.TEXT_INPUT:
            return self._analyze_text_intent(action.content)
        elif action.action_type == InteractionType.SELECTION:
            return "selection_refinement"
        elif action.action_type == InteractionType.MODIFICATION:
            return "iterative_improvement"
        elif action.action_type == InteractionType.FEEDBACK:
            return "guidance_provision"
        else:
            return "exploration"
            
    def _analyze_sketch_intent(self, sketch_data: Any) -> str:
        """Analyze intent from sketch input."""
        # Analyze sketch characteristics
        if isinstance(sketch_data, np.ndarray):
            # Analyze stroke patterns, speed, pressure
            if len(sketch_data) > 100:
                # Long strokes might indicate detailed work
                return "detailed_creation"
            elif len(sketch_data) < 20:
                # Short strokes might indicate rough ideas
                return "concept_exploration"
            else:
                return "iterative_refinement"
        return "artistic_expression"
        
    def _analyze_text_intent(self, text: str) -> str:
        """Analyze intent from text input."""
        if not isinstance(text, str):
            return "unknown"
            
        text_lower = text.lower()
        
        # Intent keywords
        if any(word in text_lower for word in ['change', 'modify', 'edit', 'alter']):
            return "modification_request"
        elif any(word in text_lower for word in ['create', 'make', 'generate', 'build']):
            return "creation_request"
        elif any(word in text_lower for word in ['like', 'love', 'good', 'great', 'excellent']):
            return "positive_feedback"
        elif any(word in text_lower for word in ['dislike', 'bad', 'poor', 'improve']):
            return "negative_feedback"
        elif any(word in text_lower for word in ['help', 'assist', 'guide', 'show']):
            return "assistance_request"
        else:
            return "general_communication"
            
    def _identify_secondary_intents(self, action: CreativeAction, 
                                  context: Dict[str, Any]) -> List[str]:
        """Identify secondary or implicit intents."""
        secondary = []
        
        # Context-based inference
        if context.get('session_progress', 0) < 0.3:
            secondary.append("exploration_intent")
        elif context.get('session_progress', 0) > 0.7:
            secondary.append("finalization_intent")
        else:
            secondary.append("development_intent")
            
        # Timing-based inference
        if context.get('time_since_last_action', 0) > 10:
            secondary.append("contemplation_phase")
        elif context.get('time_since_last_action', 0) < 1:
            secondary.append("rapid_iteration")
            
        return secondary
        
    def _calculate_intent_confidence(self, action: CreativeAction, 
                                   context: Dict[str, Any]) -> float:
        """Calculate confidence in intent recognition."""
        base_confidence = 0.7
        
        # Adjust based on action clarity
        if action.action_type in [InteractionType.TEXT_INPUT, InteractionType.FEEDBACK]:
            base_confidence += 0.2
        elif action.action_type in [InteractionType.GESTURE]:
            base_confidence -= 0.1
            
        # Adjust based on context richness
        context_richness = len(context) / 10.0
        base_confidence += min(0.2, context_richness)
        
        # Adjust based on historical consistency
        if len(self.intent_history) > 3:
            recent_intents = [intent['primary_intent'] for intent in self.intent_history[-3:]]
            if len(set(recent_intents)) == 1:  # Consistent intent
                base_confidence += 0.1
                
        return min(1.0, max(0.0, base_confidence))
        
    def _analyze_temporal_context(self, action: CreativeAction) -> Dict[str, Any]:
        """Analyze temporal context of the action."""
        current_time = time.time()
        
        context = {
            'time_of_day': self._get_time_category(current_time),
            'session_duration': current_time - action.timestamp if hasattr(action, 'session_start') else 0,
            'action_pace': self._calculate_action_pace()
        }
        
        return context
        
    def _analyze_emotional_context(self, action: CreativeAction) -> Dict[str, Any]:
        """Analyze emotional context from action characteristics."""
        emotional_context = {
            'energy_level': 0.5,
            'frustration_indicators': [],
            'satisfaction_indicators': [],
            'exploration_mood': 0.5
        }
        
        # Analyze based on action type and content
        if action.action_type == InteractionType.FEEDBACK:
            if isinstance(action.content, str):
                text = action.content.lower()
                if any(word in text for word in ['great', 'love', 'amazing', 'perfect']):
                    emotional_context['satisfaction_indicators'].append('positive_language')
                    emotional_context['energy_level'] = 0.8
                elif any(word in text for word in ['frustrated', 'wrong', 'bad', 'hate']):
                    emotional_context['frustration_indicators'].append('negative_language')
                    emotional_context['energy_level'] = 0.3
                    
        return emotional_context
        
    def _get_time_category(self, timestamp: float) -> str:
        """Categorize time of day."""
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        hour = dt.hour
        
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
            
    def _calculate_action_pace(self) -> str:
        """Calculate the pace of recent actions."""
        if len(self.intent_history) < 2:
            return "unknown"
            
        recent_times = [intent.get('timestamp', time.time()) for intent in self.intent_history[-5:]]
        if len(recent_times) > 1:
            avg_interval = np.mean(np.diff(recent_times))
            if avg_interval < 2:
                return "rapid"
            elif avg_interval < 10:
                return "moderate"
            else:
                return "slow"
        return "unknown"


class AdaptiveResponseGenerator:
    """Generates contextually appropriate AGI responses to human input."""
    
    def __init__(self, human_profile: HumanProfile):
        self.human_profile = human_profile
        self.response_strategies = {
            'beginner': self._beginner_strategy,
            'intermediate': self._intermediate_strategy,
            'expert': self._expert_strategy
        }
        
    def generate_response(self, human_intent: Dict[str, Any], 
                         session_context: Dict[str, Any],
                         current_artifact: Any) -> CreativeAction:
        """Generate appropriate AGI response to human intent."""
        
        # Select strategy based on human expertise
        strategy = self.response_strategies.get(
            self.human_profile.expertise_level, 
            self._intermediate_strategy
        )
        
        response = strategy(human_intent, session_context, current_artifact)
        
        # Create response action
        agi_action = CreativeAction(
            action_id=f"agi_{int(time.time() * 1000)}",
            actor="agi",
            action_type=response['action_type'],
            timestamp=time.time(),
            content=response['content'],
            context=response['context'],
            confidence=response['confidence'],
            metadata=response.get('metadata', {})
        )
        
        return agi_action
        
    def _beginner_strategy(self, intent: Dict[str, Any], 
                          context: Dict[str, Any], 
                          artifact: Any) -> Dict[str, Any]:
        """Strategy for beginner users - more guidance and explanation."""
        
        primary_intent = intent['primary_intent']
        
        if primary_intent == "exploration":
            return {
                'action_type': InteractionType.FEEDBACK,
                'content': {
                    'suggestions': self._generate_exploration_suggestions(),
                    'explanation': "Here are some creative directions you might explore. Try experimenting with different approaches!",
                    'examples': self._provide_examples()
                },
                'context': {'strategy': 'educational_guidance'},
                'confidence': 0.8
            }
        elif primary_intent == "assistance_request":
            return {
                'action_type': InteractionType.FEEDBACK,
                'content': {
                    'step_by_step': self._generate_tutorial_steps(context),
                    'tips': self._provide_beginner_tips(),
                    'encouragement': "You're doing great! Let's break this down into manageable steps."
                },
                'context': {'strategy': 'tutorial_mode'},
                'confidence': 0.9
            }
        else:
            return self._default_supportive_response(intent, context)
            
    def _intermediate_strategy(self, intent: Dict[str, Any], 
                             context: Dict[str, Any], 
                             artifact: Any) -> Dict[str, Any]:
        """Strategy for intermediate users - balanced collaboration."""
        
        primary_intent = intent['primary_intent']
        
        if primary_intent == "iterative_improvement":
            return {
                'action_type': InteractionType.MODIFICATION,
                'content': self._generate_iterative_suggestions(artifact, context),
                'context': {'strategy': 'collaborative_refinement'},
                'confidence': 0.8
            }
        elif primary_intent == "creation_request":
            return {
                'action_type': InteractionType.SKETCH,
                'content': self._generate_creative_variants(context),
                'context': {'strategy': 'creative_partnership'},
                'confidence': 0.7
            }
        else:
            return self._default_collaborative_response(intent, context)
            
    def _expert_strategy(self, intent: Dict[str, Any], 
                        context: Dict[str, Any], 
                        artifact: Any) -> Dict[str, Any]:
        """Strategy for expert users - sophisticated interaction."""
        
        primary_intent = intent['primary_intent']
        
        if primary_intent == "detailed_creation":
            return {
                'action_type': InteractionType.MODIFICATION,
                'content': self._generate_expert_variations(artifact, context),
                'context': {'strategy': 'expert_collaboration'},
                'confidence': 0.9
            }
        elif primary_intent == "guidance_provision":
            return {
                'action_type': InteractionType.FEEDBACK,
                'content': {
                    'analysis': self._provide_technical_analysis(artifact),
                    'suggestions': self._advanced_creative_suggestions(context),
                    'theory': self._relevant_art_theory(context)
                },
                'context': {'strategy': 'peer_collaboration'},
                'confidence': 0.8
            }
        else:
            return self._default_expert_response(intent, context)
            
    def _generate_exploration_suggestions(self) -> List[str]:
        """Generate exploration suggestions for beginners."""
        suggestions = [
            "Try experimenting with different colors and see how they affect the mood",
            "Consider the composition - where do your eyes naturally focus?",
            "What story or emotion are you trying to convey?",
            "Experiment with different textures and patterns",
            "Think about the balance between detailed and simple areas"
        ]
        return np.random.choice(suggestions, size=3, replace=False).tolist()
        
    def _provide_examples(self) -> List[Dict[str, Any]]:
        """Provide examples for beginners."""
        return [
            {'type': 'color_palette', 'description': 'Try warm colors for energetic feelings'},
            {'type': 'composition', 'description': 'Use rule of thirds for balanced layouts'},
            {'type': 'contrast', 'description': 'Mix light and dark areas for visual interest'}
        ]
        
    def _generate_tutorial_steps(self, context: Dict[str, Any]) -> List[str]:
        """Generate step-by-step tutorial."""
        domain = context.get('domain', 'visual')
        
        if domain == 'visual':
            return [
                "1. Start with a basic sketch of your main subject",
                "2. Add basic shapes and forms",
                "3. Consider lighting and shadows",
                "4. Add details and textures",
                "5. Refine and polish"
            ]
        elif domain == 'music':
            return [
                "1. Choose a key and tempo",
                "2. Create a basic melody",
                "3. Add harmonic progression",
                "4. Layer in rhythm and percussion",
                "5. Add variations and dynamics"
            ]
        else:
            return ["Let's break this down into smaller, manageable steps."]
            
    def _provide_beginner_tips(self) -> List[str]:
        """Provide helpful tips for beginners."""
        return [
            "Don't worry about perfection - focus on expression",
            "Observe how light and shadow work in real life",
            "Look at artwork you admire and analyze what you like",
            "Practice regularly, even just for a few minutes",
            "Experiment without fear of making mistakes"
        ]
        
    def _generate_iterative_suggestions(self, artifact: Any, 
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate suggestions for iterative improvement."""
        return {
            'refinements': [
                "Consider adjusting the color balance in the upper left",
                "The composition could benefit from a stronger focal point",
                "Try adding more contrast to enhance visual interest"
            ],
            'alternatives': [
                "What if we tried a different color scheme?",
                "How would this look with softer/harder edges?",
                "Could we simplify some areas to emphasize others?"
            ],
            'technical_improvements': [
                "The lighting consistency could be refined",
                "Consider the perspective and proportions",
                "The texture application could be more varied"
            ]
        }
        
    def _generate_creative_variants(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate creative variants for intermediate users."""
        return {
            'style_variants': ['impressionistic', 'geometric', 'organic'],
            'mood_variants': ['energetic', 'contemplative', 'dramatic'],
            'technique_variants': ['layered', 'minimalist', 'detailed'],
            'concept_variants': self._brainstorm_concepts(context)
        }
        
    def _generate_expert_variations(self, artifact: Any, 
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate sophisticated variations for experts."""
        return {
            'conceptual_explorations': self._advanced_concept_variations(context),
            'technical_experiments': self._advanced_technique_suggestions(artifact),
            'theoretical_applications': self._art_theory_applications(context),
            'cross_domain_influences': self._cross_domain_suggestions(context)
        }
        
    def _provide_technical_analysis(self, artifact: Any) -> Dict[str, Any]:
        """Provide technical analysis for experts."""
        return {
            'composition_analysis': "Strong diagonal movement creates dynamic flow",
            'color_theory': "Complementary color scheme creates vibrant tension",
            'technical_execution': "Confident mark-making demonstrates mastery",
            'conceptual_depth': "Layered metaphors invite deeper contemplation"
        }
        
    def _advanced_creative_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """Advanced creative suggestions for experts."""
        return [
            "Explore non-traditional compositional structures",
            "Experiment with mixed media integration",
            "Consider temporal or sequential elements",
            "Investigate cultural or historical references",
            "Push the boundaries of the chosen medium"
        ]
        
    def _relevant_art_theory(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Provide relevant art theory references."""
        return {
            'color_theory': "Consider Itten's color interaction principles",
            'composition': "Explore dynamic symmetry and golden ratio applications",
            'conceptual': "Reference contemporary discourse on materiality",
            'historical': "Consider relationship to modernist traditions"
        }
        
    def _default_supportive_response(self, intent: Dict[str, Any], 
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Default supportive response for beginners."""
        return {
            'action_type': InteractionType.FEEDBACK,
            'content': {
                'encouragement': "That's an interesting approach! Keep exploring.",
                'gentle_guidance': "Here are some things you might consider...",
                'support': "Remember, creativity is about the journey, not just the destination."
            },
            'context': {'strategy': 'supportive'},
            'confidence': 0.7
        }
        
    def _default_collaborative_response(self, intent: Dict[str, Any], 
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Default collaborative response for intermediate users."""
        return {
            'action_type': InteractionType.FEEDBACK,
            'content': {
                'collaboration': "Let's work together on this idea",
                'suggestions': "I have some thoughts that might complement your vision",
                'questions': "What aspects are most important to you?"
            },
            'context': {'strategy': 'collaborative'},
            'confidence': 0.8
        }
        
    def _default_expert_response(self, intent: Dict[str, Any], 
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """Default expert response for expert users."""
        return {
            'action_type': InteractionType.FEEDBACK,
            'content': {
                'peer_discussion': "Your approach raises interesting questions about...",
                'technical_insights': "From a technical perspective, consider...",
                'conceptual_dialogue': "This connects to broader themes in contemporary practice"
            },
            'context': {'strategy': 'peer_level'},
            'confidence': 0.9
        }
        
    def _brainstorm_concepts(self, context: Dict[str, Any]) -> List[str]:
        """Brainstorm creative concepts."""
        concepts = [
            "transformation and change",
            "harmony between opposites",
            "hidden connections",
            "emotional landscapes",
            "time and memory",
            "nature and technology",
            "light and shadow",
            "movement and stillness"
        ]
        return np.random.choice(concepts, size=3, replace=False).tolist()
        
    def _advanced_concept_variations(self, context: Dict[str, Any]) -> List[str]:
        """Generate advanced conceptual variations."""
        return [
            "Deconstruction and reconstruction of familiar forms",
            "Exploration of liminal spaces and boundaries",
            "Investigation of materiality and immateriality",
            "Temporal layering and palimpsest effects",
            "Cross-cultural dialogue and translation"
        ]
        
    def _advanced_technique_suggestions(self, artifact: Any) -> List[str]:
        """Suggest advanced techniques."""
        return [
            "Experimental mark-making with unconventional tools",
            "Layered transparency and opacity effects",
            "Integration of found materials or textures",
            "Systematic variation and permutation",
            "Process documentation and iteration studies"
        ]
        
    def _art_theory_applications(self, context: Dict[str, Any]) -> List[str]:
        """Suggest art theory applications."""
        return [
            "Apply phenomenological approaches to spatial experience",
            "Investigate post-structuralist concepts of meaning",
            "Explore feminist perspectives on representation",
            "Consider decolonial approaches to form and content",
            "Examine materialist critiques of artistic production"
        ]
        
    def _cross_domain_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """Suggest cross-domain influences."""
        return [
            "Musical rhythms and temporal structures",
            "Scientific visualization and data representation",
            "Literary narrative techniques and devices",
            "Architectural spatial relationships",
            "Digital media and algorithmic processes"
        ]


class CollaborationEngine:
    """Main engine for managing human-AGI collaborative creation."""
    
    def __init__(self):
        self.active_sessions = {}
        self.human_profiles = {}
        self.intent_recognizer = CreativeIntentRecognizer()
        self.session_history = []
        
    def create_session(self, human_profile: HumanProfile, 
                      mode: CollaborationMode,
                      domain: str,
                      goals: List[str] = None,
                      constraints: Dict[str, Any] = None) -> CollaborativeSession:
        """Create a new collaborative session."""
        
        session_id = f"session_{int(time.time() * 1000)}"
        
        session = CollaborativeSession(
            session_id=session_id,
            participants=[human_profile.user_id, "agi"],
            mode=mode,
            domain=domain,
            start_time=time.time(),
            goals=goals or [],
            constraints=constraints or {}
        )
        
        self.active_sessions[session_id] = session
        self.human_profiles[human_profile.user_id] = human_profile
        
        return session
        
    def process_human_action(self, session_id: str, 
                           action: CreativeAction) -> CreativeAction:
        """Process human action and generate AGI response."""
        
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
            
        session = self.active_sessions[session_id]
        human_profile = self.human_profiles[action.actor]
        
        # Add action to session
        session.actions.append(action)
        
        # Recognize intent
        session_context = self._build_session_context(session)
        intent = self.intent_recognizer.recognize_intent(action, session_context)
        
        # Generate AGI response
        response_generator = AdaptiveResponseGenerator(human_profile)
        agi_response = response_generator.generate_response(
            intent, session_context, session.current_artifact
        )
        
        # Add response to session
        session.actions.append(agi_response)
        
        # Update session state
        self._update_session_state(session, action, agi_response)
        
        return agi_response
        
    def _build_session_context(self, session: CollaborativeSession) -> Dict[str, Any]:
        """Build comprehensive session context."""
        context = {
            'session_id': session.session_id,
            'mode': session.mode.value,
            'domain': session.domain,
            'session_duration': time.time() - session.start_time,
            'num_actions': len(session.actions),
            'session_progress': self._calculate_session_progress(session),
            'recent_actions': session.actions[-5:] if session.actions else [],
            'shared_state': session.shared_state,
            'goals': session.goals,
            'constraints': session.constraints
        }
        
        # Add timing context
        if session.actions:
            last_action_time = session.actions[-1].timestamp
            context['time_since_last_action'] = time.time() - last_action_time
            
        return context
        
    def _calculate_session_progress(self, session: CollaborativeSession) -> float:
        """Calculate session progress (0.0 to 1.0)."""
        # Simple heuristic based on number of actions and goals
        base_progress = min(1.0, len(session.actions) / 20.0)
        
        # Adjust based on goals completion
        if session.goals:
            # This would need more sophisticated goal tracking
            goal_progress = 0.5  # Placeholder
            return (base_progress + goal_progress) / 2
            
        return base_progress
        
    def _update_session_state(self, session: CollaborativeSession, 
                            human_action: CreativeAction,
                            agi_response: CreativeAction) -> None:
        """Update session state based on recent interactions."""
        
        # Update shared state based on actions
        if human_action.action_type == InteractionType.MODIFICATION:
            session.shared_state['last_modification'] = human_action.content
            
        if agi_response.action_type == InteractionType.FEEDBACK:
            session.shared_state['latest_feedback'] = agi_response.content
            
        # Update artifact if modified
        if human_action.action_type in [InteractionType.SKETCH, InteractionType.MODIFICATION]:
            session.current_artifact = human_action.content
        elif agi_response.action_type in [InteractionType.SKETCH, InteractionType.MODIFICATION]:
            session.current_artifact = agi_response.content
            
        # Track collaboration patterns
        session.shared_state['collaboration_pattern'] = self._analyze_collaboration_pattern(session)
        
    def _analyze_collaboration_pattern(self, session: CollaborativeSession) -> Dict[str, Any]:
        """Analyze the pattern of collaboration in the session."""
        if len(session.actions) < 4:
            return {'pattern': 'initial', 'rhythm': 'establishing'}
            
        recent_actions = session.actions[-10:]
        
        # Analyze turn-taking pattern
        actors = [action.actor for action in recent_actions]
        turn_taking_score = self._calculate_turn_taking_score(actors)
        
        # Analyze action types
        action_types = [action.action_type for action in recent_actions]
        
        # Determine collaboration rhythm
        action_intervals = []
        for i in range(1, len(recent_actions)):
            interval = recent_actions[i].timestamp - recent_actions[i-1].timestamp
            action_intervals.append(interval)
            
        avg_interval = np.mean(action_intervals) if action_intervals else 0
        
        if avg_interval < 5:
            rhythm = "rapid"
        elif avg_interval < 15:
            rhythm = "moderate"
        else:
            rhythm = "contemplative"
            
        return {
            'pattern': 'interactive' if turn_taking_score > 0.5 else 'sequential',
            'rhythm': rhythm,
            'turn_taking_score': turn_taking_score,
            'avg_response_time': avg_interval
        }
        
    def _calculate_turn_taking_score(self, actors: List[str]) -> float:
        """Calculate how well participants are taking turns."""
        if len(actors) < 2:
            return 0.0
            
        alternations = 0
        for i in range(1, len(actors)):
            if actors[i] != actors[i-1]:
                alternations += 1
                
        max_alternations = len(actors) - 1
        return alternations / max_alternations if max_alternations > 0 else 0.0
        
    def get_session_insights(self, session_id: str) -> Dict[str, Any]:
        """Get insights about the collaborative session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
            
        session = self.active_sessions[session_id]
        
        # Analyze session dynamics
        human_actions = [a for a in session.actions if a.actor != "agi"]
        agi_actions = [a for a in session.actions if a.actor == "agi"]
        
        insights = {
            'session_duration': time.time() - session.start_time,
            'total_actions': len(session.actions),
            'human_actions': len(human_actions),
            'agi_actions': len(agi_actions),
            'collaboration_balance': len(human_actions) / (len(session.actions) + 1e-6),
            'session_progress': self._calculate_session_progress(session),
            'collaboration_pattern': session.shared_state.get('collaboration_pattern', {}),
            'dominant_interaction_types': self._get_dominant_interaction_types(session),
            'creative_momentum': self._assess_creative_momentum(session),
            'satisfaction_indicators': self._assess_satisfaction_indicators(session)
        }
        
        return insights
        
    def _get_dominant_interaction_types(self, session: CollaborativeSession) -> Dict[str, int]:
        """Get the most common interaction types in the session."""
        type_counts = {}
        for action in session.actions:
            action_type = action.action_type.value
            type_counts[action_type] = type_counts.get(action_type, 0) + 1
            
        return dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))
        
    def _assess_creative_momentum(self, session: CollaborativeSession) -> Dict[str, Any]:
        """Assess the creative momentum of the session."""
        if len(session.actions) < 3:
            return {'momentum': 'building', 'trend': 'stable'}
            
        # Analyze recent action frequency
        recent_actions = session.actions[-5:]
        time_spans = []
        
        for i in range(1, len(recent_actions)):
            span = recent_actions[i].timestamp - recent_actions[i-1].timestamp
            time_spans.append(span)
            
        if len(time_spans) >= 2:
            trend = "accelerating" if time_spans[-1] < time_spans[0] else "decelerating"
        else:
            trend = "stable"
            
        avg_span = np.mean(time_spans) if time_spans else 10
        
        if avg_span < 5:
            momentum = "high"
        elif avg_span < 15:
            momentum = "moderate"
        else:
            momentum = "low"
            
        return {
            'momentum': momentum,
            'trend': trend,
            'avg_action_interval': avg_span
        }
        
    def _assess_satisfaction_indicators(self, session: CollaborativeSession) -> Dict[str, Any]:
        """Assess indicators of participant satisfaction."""
        # Look for positive feedback actions
        positive_indicators = 0
        negative_indicators = 0
        
        for action in session.actions:
            if action.action_type == InteractionType.FEEDBACK:
                if isinstance(action.content, str):
                    content = action.content.lower()
                    if any(word in content for word in ['good', 'great', 'love', 'perfect', 'excellent']):
                        positive_indicators += 1
                    elif any(word in content for word in ['bad', 'wrong', 'hate', 'terrible', 'awful']):
                        negative_indicators += 1
                        
        total_feedback = positive_indicators + negative_indicators
        satisfaction_ratio = positive_indicators / (total_feedback + 1e-6) if total_feedback > 0 else 0.5
        
        return {
            'positive_feedback_count': positive_indicators,
            'negative_feedback_count': negative_indicators,
            'satisfaction_ratio': satisfaction_ratio,
            'engagement_level': 'high' if len(session.actions) > 10 else 'moderate'
        }
        
    def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a collaborative session and return summary."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
            
        session = self.active_sessions[session_id]
        insights = self.get_session_insights(session_id)
        
        # Create session summary
        summary = {
            'session_id': session_id,
            'duration': time.time() - session.start_time,
            'final_insights': insights,
            'goals_achieved': self._assess_goal_achievement(session),
            'key_moments': self._identify_key_moments(session),
            'recommendations': self._generate_recommendations(session, insights)
        }
        
        # Archive session
        self.session_history.append(session)
        del self.active_sessions[session_id]
        
        return summary
        
    def _assess_goal_achievement(self, session: CollaborativeSession) -> Dict[str, Any]:
        """Assess how well session goals were achieved."""
        # This would need more sophisticated goal tracking
        return {
            'goals_set': len(session.goals),
            'estimated_completion': 0.7,  # Placeholder
            'goal_details': session.goals
        }
        
    def _identify_key_moments(self, session: CollaborativeSession) -> List[Dict[str, Any]]:
        """Identify key moments in the collaborative session."""
        key_moments = []
        
        # Find moments of high activity
        if len(session.actions) > 5:
            # Find rapid exchanges
            for i in range(1, len(session.actions)):
                time_diff = session.actions[i].timestamp - session.actions[i-1].timestamp
                if time_diff < 2:  # Rapid response
                    key_moments.append({
                        'type': 'rapid_exchange',
                        'timestamp': session.actions[i].timestamp,
                        'description': 'Quick back-and-forth interaction'
                    })
                    
        # Find creative breakthroughs (high confidence actions)
        for action in session.actions:
            if action.confidence > 0.9:
                key_moments.append({
                    'type': 'high_confidence_moment',
                    'timestamp': action.timestamp,
                    'actor': action.actor,
                    'description': f'{action.actor} made a confident creative decision'
                })
                
        return key_moments[:5]  # Return top 5 key moments
        
    def _generate_recommendations(self, session: CollaborativeSession, 
                                insights: Dict[str, Any]) -> List[str]:
        """Generate recommendations for future sessions."""
        recommendations = []
        
        # Based on collaboration balance
        balance = insights.get('collaboration_balance', 0.5)
        if balance < 0.3:
            recommendations.append("Consider more active human participation in future sessions")
        elif balance > 0.7:
            recommendations.append("AGI could provide more proactive suggestions")
            
        # Based on momentum
        momentum = insights.get('creative_momentum', {}).get('momentum', 'moderate')
        if momentum == 'low':
            recommendations.append("Try shorter, more focused creative sessions")
        elif momentum == 'high':
            recommendations.append("Consider extending session time to capitalize on creative flow")
            
        # Based on satisfaction
        satisfaction = insights.get('satisfaction_indicators', {}).get('satisfaction_ratio', 0.5)
        if satisfaction < 0.5:
            recommendations.append("Focus on understanding user preferences and goals better")
        else:
            recommendations.append("Continue with current collaborative approach - it's working well")
            
        return recommendations