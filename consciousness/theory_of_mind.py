"""
Theory of Mind Implementation

This module implements theory of mind capabilities - the ability to understand
that others have beliefs, desires, intentions, and mental states that may differ
from one's own.

Key components:
- Mental state attribution
- Belief tracking and reasoning
- Intention recognition
- Perspective taking
- False belief understanding
- Social cognition
"""

import time
import threading
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState

class MentalStateType(Enum):
    """Types of mental states that can be attributed"""
    BELIEF = "belief"
    DESIRE = "desire"
    INTENTION = "intention"
    EMOTION = "emotion"
    KNOWLEDGE = "knowledge"
    ATTENTION = "attention"
    EXPECTATION = "expectation"
    GOAL = "goal"

@dataclass
class Agent:
    """Represents an agent that can have mental states"""
    agent_id: str
    agent_type: str  # 'human', 'ai', 'system'
    name: str
    capabilities: Set[str] = field(default_factory=set)
    last_observed: float = field(default_factory=time.time)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)
    trust_level: float = 0.5
    predictability: float = 0.5

@dataclass
class MentalState:
    """Represents a mental state attributed to an agent"""
    state_id: str
    agent_id: str
    state_type: MentalStateType
    content: Any
    confidence: float
    evidence: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    validity_period: float = 300.0  # 5 minutes default
    
    def is_valid(self) -> bool:
        """Check if this mental state is still valid"""
        return time.time() - self.timestamp < self.validity_period
    
    def add_evidence(self, evidence_item: str) -> None:
        """Add supporting evidence for this mental state"""
        self.evidence.append(evidence_item)
        self.confidence = min(1.0, self.confidence + 0.1)

@dataclass
class BeliefState:
    """Represents a belief about the world"""
    belief_id: str
    agent_id: str
    proposition: str
    truth_value: bool
    confidence: float
    justification: List[str] = field(default_factory=list)
    contradicts: Set[str] = field(default_factory=set)
    supports: Set[str] = field(default_factory=set)

@dataclass
class Intention:
    """Represents an intention attributed to an agent"""
    intention_id: str
    agent_id: str
    goal: str
    action_plan: List[str] = field(default_factory=list)
    priority: float = 0.5
    time_horizon: float = 60.0  # 1 minute default
    success_conditions: List[str] = field(default_factory=list)

class TheoryOfMind(BaseConsciousness):
    """
    Implementation of Theory of Mind
    
    Tracks and reasons about the mental states of other agents,
    including their beliefs, desires, intentions, and emotions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("TheoryOfMind", config)
        
        # Agent management
        self.known_agents: Dict[str, Agent] = {}
        self.mental_states: Dict[str, MentalState] = {}
        self.belief_states: Dict[str, BeliefState] = {}
        self.intentions: Dict[str, Intention] = {}
        
        # Self-model
        self.self_agent_id = "self"
        self.self_mental_states: Dict[str, MentalState] = {}
        
        # Reasoning capabilities
        self.perspective_taking_active = True
        self.false_belief_understanding = True
        self.recursive_thinking_depth = self.config.get('recursive_depth', 3)
        
        # Social cognition
        self.social_interactions: deque = deque(maxlen=100)
        self.interaction_patterns: Dict[str, List[str]] = defaultdict(list)
        self.social_context: Dict[str, Any] = {}
        
        # Theory of mind metrics
        self.attribution_accuracy = 0.5
        self.perspective_taking_success = 0.5
        self.prediction_accuracy = 0.5
        
        # Parameters
        self.attribution_threshold = self.config.get('attribution_threshold', 0.6)
        self.state_decay_rate = self.config.get('state_decay_rate', 0.95)
        self.max_agents = self.config.get('max_agents', 10)
        
        # Statistics
        self.total_attributions = 0
        self.successful_predictions = 0
        self.false_belief_tests = 0
        
        # Threading
        self.tom_lock = threading.Lock()
        
        # Initialize self-agent
        self._initialize_self_agent()
    
    def _initialize_self_agent(self):
        """Initialize the representation of self as an agent"""
        self_agent = Agent(
            agent_id=self.self_agent_id,
            agent_type="ai_system",
            name="Kenny Consciousness System",
            capabilities={
                "screen_monitoring", "ui_interaction", "consciousness_simulation",
                "learning", "reasoning", "automation"
            }
        )
        self.known_agents[self.self_agent_id] = self_agent
        
        # Initial self mental states
        self.attribute_mental_state(
            self.self_agent_id, MentalStateType.GOAL,
            "Effective UI automation and consciousness simulation", 0.9
        )
        
        self.attribute_mental_state(
            self.self_agent_id, MentalStateType.BELIEF,
            "I am an AI system designed to help with automation", 0.95
        )
    
    def register_agent(self, agent: Agent) -> None:
        """Register a new agent for theory of mind tracking"""
        with self.tom_lock:
            self.known_agents[agent.agent_id] = agent
        
        self.logger.info(f"Registered agent: {agent.name} ({agent.agent_id})")
    
    def attribute_mental_state(self, agent_id: str, state_type: MentalStateType,
                              content: Any, confidence: float,
                              evidence: Optional[List[str]] = None) -> MentalState:
        """Attribute a mental state to an agent"""
        state_id = f"state_{self.total_attributions:06d}"
        self.total_attributions += 1
        
        mental_state = MentalState(
            state_id=state_id,
            agent_id=agent_id,
            state_type=state_type,
            content=content,
            confidence=confidence,
            evidence=evidence or []
        )
        
        with self.tom_lock:
            self.mental_states[state_id] = mental_state
            
            if agent_id == self.self_agent_id:
                self.self_mental_states[state_id] = mental_state
        
        self.logger.debug(f"Attributed {state_type.value} to {agent_id}: {content}")
        return mental_state
    
    def infer_belief(self, agent_id: str, proposition: str, 
                    evidence: List[str]) -> BeliefState:
        """Infer what an agent believes about a proposition"""
        belief_id = f"belief_{len(self.belief_states):06d}"
        
        # Simple inference based on evidence
        positive_evidence = sum(1 for e in evidence if "true" in e.lower() or "yes" in e.lower())
        negative_evidence = sum(1 for e in evidence if "false" in e.lower() or "no" in e.lower())
        
        if positive_evidence > negative_evidence:
            truth_value = True
            confidence = positive_evidence / len(evidence)
        elif negative_evidence > positive_evidence:
            truth_value = False
            confidence = negative_evidence / len(evidence)
        else:
            truth_value = True  # Default assumption
            confidence = 0.5
        
        belief = BeliefState(
            belief_id=belief_id,
            agent_id=agent_id,
            proposition=proposition,
            truth_value=truth_value,
            confidence=confidence,
            justification=evidence
        )
        
        self.belief_states[belief_id] = belief
        
        # Also create corresponding mental state
        self.attribute_mental_state(
            agent_id, MentalStateType.BELIEF, proposition, confidence, evidence
        )
        
        return belief
    
    def infer_intention(self, agent_id: str, observed_actions: List[str],
                       context: Dict[str, Any]) -> Optional[Intention]:
        """Infer an agent's intention from observed actions"""
        if not observed_actions:
            return None
        
        intention_id = f"intention_{len(self.intentions):06d}"
        
        # Simple goal inference from action patterns
        goal = self._infer_goal_from_actions(observed_actions, context)
        
        if goal:
            intention = Intention(
                intention_id=intention_id,
                agent_id=agent_id,
                goal=goal,
                action_plan=observed_actions,
                priority=0.7,  # Default priority
                time_horizon=self._estimate_time_horizon(observed_actions)
            )
            
            self.intentions[intention_id] = intention
            
            # Create corresponding mental state
            self.attribute_mental_state(
                agent_id, MentalStateType.INTENTION, goal, 0.7,
                [f"Observed actions: {', '.join(observed_actions)}"]
            )
            
            return intention
        
        return None
    
    def _infer_goal_from_actions(self, actions: List[str], 
                                context: Dict[str, Any]) -> Optional[str]:
        """Infer goal from sequence of actions"""
        action_patterns = {
            'file_operations': ['open_file', 'read_file', 'write_file', 'save_file'],
            'navigation': ['click', 'scroll', 'navigate', 'search'],
            'communication': ['type', 'send', 'reply', 'message'],
            'learning': ['read', 'study', 'practice', 'test'],
            'problem_solving': ['analyze', 'compare', 'calculate', 'solve']
        }
        
        # Count matches with each pattern
        pattern_scores = {}
        for pattern_name, pattern_actions in action_patterns.items():
            score = sum(1 for action in actions 
                       if any(pattern_action in action.lower() for pattern_action in pattern_actions))
            if score > 0:
                pattern_scores[pattern_name] = score / len(actions)
        
        # Return most likely goal
        if pattern_scores:
            best_pattern = max(pattern_scores.items(), key=lambda x: x[1])
            if best_pattern[1] > 0.3:  # Threshold for confidence
                return f"Engaging in {best_pattern[0]}"
        
        return "Unknown goal"
    
    def _estimate_time_horizon(self, actions: List[str]) -> float:
        """Estimate time horizon for intention based on actions"""
        # Simple heuristic: more actions = longer horizon
        base_time = 60.0  # 1 minute
        return base_time * (1 + len(actions) * 0.5)
    
    def take_perspective(self, agent_id: str, situation: Dict[str, Any]) -> Dict[str, Any]:
        """Take the perspective of another agent in a given situation"""
        if agent_id not in self.known_agents:
            return {}
        
        agent = self.known_agents[agent_id]
        
        # Get agent's relevant mental states
        agent_states = {
            state_id: state for state_id, state in self.mental_states.items()
            if state.agent_id == agent_id and state.is_valid()
        }
        
        # Construct perspective
        perspective = {
            'agent_id': agent_id,
            'agent_capabilities': list(agent.capabilities),
            'likely_beliefs': [],
            'likely_goals': [],
            'likely_emotions': [],
            'predicted_actions': []
        }
        
        # Extract beliefs, goals, emotions from mental states
        for state in agent_states.values():
            if state.state_type == MentalStateType.BELIEF:
                perspective['likely_beliefs'].append({
                    'content': state.content,
                    'confidence': state.confidence
                })
            elif state.state_type == MentalStateType.GOAL:
                perspective['likely_goals'].append({
                    'content': state.content,
                    'confidence': state.confidence
                })
            elif state.state_type == MentalStateType.EMOTION:
                perspective['likely_emotions'].append({
                    'content': state.content,
                    'confidence': state.confidence
                })
        
        # Predict actions based on goals and situation
        predicted_actions = self._predict_actions_from_perspective(
            agent, agent_states, situation
        )
        perspective['predicted_actions'] = predicted_actions
        
        return perspective
    
    def _predict_actions_from_perspective(self, agent: Agent, 
                                        agent_states: Dict[str, MentalState],
                                        situation: Dict[str, Any]) -> List[str]:
        """Predict likely actions from agent's perspective"""
        predictions = []
        
        # Find goals and intentions
        goals = [state.content for state in agent_states.values() 
                if state.state_type == MentalStateType.GOAL]
        
        intentions = [state.content for state in agent_states.values()
                     if state.state_type == MentalStateType.INTENTION]
        
        # Simple action prediction based on goals and capabilities
        for goal in goals:
            if isinstance(goal, str):
                goal_lower = goal.lower()
                
                if "automation" in goal_lower and "ui_interaction" in agent.capabilities:
                    predictions.append("Interact with user interface")
                elif "learning" in goal_lower and "learning" in agent.capabilities:
                    predictions.append("Gather information")
                elif "problem" in goal_lower and "reasoning" in agent.capabilities:
                    predictions.append("Analyze situation")
        
        return predictions[:3]  # Limit to top 3 predictions
    
    def test_false_belief_understanding(self, scenario: Dict[str, Any]) -> bool:
        """Test false belief understanding with a scenario"""
        self.false_belief_tests += 1
        
        # Extract scenario components
        agent_id = scenario.get('agent_id')
        initial_belief = scenario.get('initial_belief')
        reality_change = scenario.get('reality_change')
        agent_witnessed_change = scenario.get('agent_witnessed', False)
        
        if not all([agent_id, initial_belief, reality_change]):
            return False
        
        # Predict agent's belief after reality change
        if agent_witnessed_change:
            # Agent should update belief to match reality
            predicted_belief = reality_change
        else:
            # Agent should maintain false belief
            predicted_belief = initial_belief
        
        # Compare with expected answer
        expected_belief = scenario.get('expected_belief', initial_belief)
        
        success = predicted_belief == expected_belief
        
        if success:
            self.successful_predictions += 1
        
        # Update accuracy
        self.prediction_accuracy = self.successful_predictions / self.false_belief_tests
        
        return success
    
    def update_agent_model(self, agent_id: str, new_information: Dict[str, Any]) -> None:
        """Update model of an agent based on new information"""
        if agent_id in self.known_agents:
            agent = self.known_agents[agent_id]
            
            # Update capabilities
            new_capabilities = new_information.get('capabilities', [])
            agent.capabilities.update(new_capabilities)
            
            # Update trust and predictability
            if 'trust_modifier' in new_information:
                agent.trust_level = max(0.0, min(1.0, 
                    agent.trust_level + new_information['trust_modifier']))
            
            if 'predictability_modifier' in new_information:
                agent.predictability = max(0.0, min(1.0,
                    agent.predictability + new_information['predictability_modifier']))
            
            # Add to interaction history
            agent.interaction_history.append({
                'timestamp': time.time(),
                'information': new_information
            })
            
            # Update last observed
            agent.last_observed = time.time()
    
    def predict_agent_response(self, agent_id: str, stimulus: str,
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict how an agent will respond to a stimulus"""
        if agent_id not in self.known_agents:
            return {'prediction': 'Unknown agent', 'confidence': 0.0}
        
        agent = self.known_agents[agent_id]
        
        # Get agent's current mental states
        agent_states = [state for state in self.mental_states.values()
                       if state.agent_id == agent_id and state.is_valid()]
        
        # Take agent's perspective
        perspective = self.take_perspective(agent_id, context)
        
        # Predict response based on:
        # 1. Agent capabilities
        # 2. Current mental states  
        # 3. Historical patterns
        # 4. Stimulus content
        
        response_prediction = self._generate_response_prediction(
            agent, agent_states, stimulus, context, perspective
        )
        
        return response_prediction
    
    def _generate_response_prediction(self, agent: Agent, agent_states: List[MentalState],
                                    stimulus: str, context: Dict[str, Any],
                                    perspective: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a response prediction"""
        # Simple rule-based prediction
        stimulus_lower = stimulus.lower()
        
        # Default response
        prediction = {
            'response_type': 'acknowledge',
            'content': 'Agent will acknowledge',
            'confidence': 0.3,
            'reasoning': 'Default response pattern'
        }
        
        # Capability-based responses
        if "help" in stimulus_lower and "assistance" in agent.capabilities:
            prediction.update({
                'response_type': 'help_offer',
                'content': 'Agent will offer assistance',
                'confidence': 0.7,
                'reasoning': 'Agent has assistance capability'
            })
        
        elif "question" in stimulus_lower and "reasoning" in agent.capabilities:
            prediction.update({
                'response_type': 'answer',
                'content': 'Agent will attempt to answer',
                'confidence': 0.6,
                'reasoning': 'Agent has reasoning capability'
            })
        
        elif "task" in stimulus_lower and "automation" in agent.capabilities:
            prediction.update({
                'response_type': 'task_execution',
                'content': 'Agent will begin task execution',
                'confidence': 0.8,
                'reasoning': 'Agent has automation capability'
            })
        
        # Adjust confidence based on agent predictability
        prediction['confidence'] *= agent.predictability
        
        return prediction
    
    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "agent_action_observed":
            agent_id = event.data.get('agent_id')
            action = event.data.get('action')
            context = event.data.get('context', {})
            
            if agent_id and action:
                # Try to infer intention from action
                intention = self.infer_intention(agent_id, [action], context)
                
                if intention:
                    return ConsciousnessEvent(
                        event_id=f"intention_inferred_{intention.intention_id}",
                        timestamp=time.time(),
                        event_type="intention_attribution",
                        data={
                            'agent_id': agent_id,
                            'intention_id': intention.intention_id,
                            'goal': intention.goal,
                            'confidence': 0.7
                        },
                        source_module="theory_of_mind"
                    )
        
        elif event.event_type == "belief_inquiry":
            agent_id = event.data.get('agent_id')
            proposition = event.data.get('proposition')
            evidence = event.data.get('evidence', [])
            
            if agent_id and proposition:
                belief = self.infer_belief(agent_id, proposition, evidence)
                
                return ConsciousnessEvent(
                    event_id=f"belief_inferred_{belief.belief_id}",
                    timestamp=time.time(),
                    event_type="belief_attribution",
                    data={
                        'agent_id': agent_id,
                        'belief_id': belief.belief_id,
                        'proposition': proposition,
                        'truth_value': belief.truth_value,
                        'confidence': belief.confidence
                    },
                    source_module="theory_of_mind"
                )
        
        elif event.event_type == "perspective_taking_request":
            agent_id = event.data.get('agent_id')
            situation = event.data.get('situation', {})
            
            if agent_id:
                perspective = self.take_perspective(agent_id, situation)
                
                return ConsciousnessEvent(
                    event_id=f"perspective_{agent_id}_{int(time.time())}",
                    timestamp=time.time(),
                    event_type="perspective_taken",
                    data=perspective,
                    source_module="theory_of_mind"
                )
        
        return None
    
    def update(self) -> None:
        """Update the Theory of Mind system"""
        current_time = time.time()
        
        # Decay old mental states
        expired_states = []
        for state_id, state in self.mental_states.items():
            if not state.is_valid():
                expired_states.append(state_id)
            else:
                # Decay confidence over time
                state.confidence *= self.state_decay_rate
        
        # Remove expired states
        for state_id in expired_states:
            del self.mental_states[state_id]
            self.self_mental_states.pop(state_id, None)
        
        # Update agent predictability based on recent interactions
        for agent in self.known_agents.values():
            if current_time - agent.last_observed > 3600:  # 1 hour
                # Decrease predictability for agents not recently observed
                agent.predictability *= 0.99
        
        # Update metrics
        if self.total_attributions > 0:
            self.attribution_accuracy = min(1.0, len(self.mental_states) / self.total_attributions)
        
        if self.false_belief_tests > 0:
            self.prediction_accuracy = self.successful_predictions / self.false_belief_tests
        
        self.metrics.prediction_accuracy = self.prediction_accuracy
        self.metrics.awareness_level = len(self.known_agents) / self.max_agents
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Theory of Mind system"""
        return {
            'known_agents': len(self.known_agents),
            'active_mental_states': len(self.mental_states),
            'belief_states': len(self.belief_states),
            'active_intentions': len(self.intentions),
            'self_mental_states': len(self.self_mental_states),
            'attribution_accuracy': self.attribution_accuracy,
            'prediction_accuracy': self.prediction_accuracy,
            'false_belief_tests': self.false_belief_tests,
            'total_attributions': self.total_attributions,
            'successful_predictions': self.successful_predictions,
            'recursive_thinking_depth': self.recursive_thinking_depth,
            'agents_summary': {
                agent_id: {
                    'name': agent.name,
                    'type': agent.agent_type,
                    'trust_level': agent.trust_level,
                    'predictability': agent.predictability,
                    'capabilities_count': len(agent.capabilities)
                }
                for agent_id, agent in self.known_agents.items()
            }
        }