"""
Goal Negotiation Protocol with Game-Theoretic Foundations
========================================================

Advanced goal negotiation system using game theory, mechanism design,
and multi-agent coordination principles for AGI collaboration.
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import uuid
import itertools
from scipy.optimize import minimize
from scipy.spatial.distance import cosine

from .core import CommunicationMessage, MessageType, AGIIdentity

logger = logging.getLogger(__name__)

class GoalType(Enum):
    """Types of goals in negotiation."""
    INDIVIDUAL = "individual"
    COLLABORATIVE = "collaborative"
    COMPETITIVE = "competitive"
    ALTRUISTIC = "altruistic"
    EMERGENT = "emergent"

class NegotiationStrategy(Enum):
    """Negotiation strategies."""
    COOPERATIVE = "cooperative"
    COMPETITIVE = "competitive"
    ACCOMMODATING = "accommodating"
    AVOIDING = "avoiding"
    COMPROMISING = "compromising"
    INTEGRATIVE = "integrative"  # Win-win seeking
    DISTRIBUTIVE = "distributive"  # Zero-sum

class UtilityFunction(Enum):
    """Types of utility functions."""
    LINEAR = "linear"
    LOGARITHMIC = "logarithmic"
    EXPONENTIAL = "exponential"
    SIGMOID = "sigmoid"
    CUSTOM = "custom"

@dataclass
class Goal:
    """Represents a goal in negotiation."""
    id: str
    description: str
    goal_type: GoalType
    priority: float  # 0-1
    owner_agi: str
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    utility_function: UtilityFunction = UtilityFunction.LINEAR
    resource_requirements: Dict[str, float] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Other goal IDs
    
    def calculate_utility(self, outcome: Dict[str, Any]) -> float:
        """Calculate utility of an outcome for this goal."""
        if self.utility_function == UtilityFunction.LINEAR:
            return self._linear_utility(outcome)
        elif self.utility_function == UtilityFunction.LOGARITHMIC:
            return self._logarithmic_utility(outcome)
        elif self.utility_function == UtilityFunction.EXPONENTIAL:
            return self._exponential_utility(outcome)
        elif self.utility_function == UtilityFunction.SIGMOID:
            return self._sigmoid_utility(outcome)
        else:
            return 0.5  # Default utility
    
    def _linear_utility(self, outcome: Dict[str, Any]) -> float:
        """Linear utility function."""
        achievement = outcome.get('achievement_rate', 0.5)
        return achievement * self.priority
    
    def _logarithmic_utility(self, outcome: Dict[str, Any]) -> float:
        """Logarithmic utility function (diminishing returns)."""
        achievement = outcome.get('achievement_rate', 0.5)
        return np.log(1 + achievement) * self.priority
    
    def _exponential_utility(self, outcome: Dict[str, Any]) -> float:
        """Exponential utility function (increasing returns)."""
        achievement = outcome.get('achievement_rate', 0.5)
        return (np.exp(achievement) - 1) * self.priority
    
    def _sigmoid_utility(self, outcome: Dict[str, Any]) -> float:
        """Sigmoid utility function (threshold effects)."""
        achievement = outcome.get('achievement_rate', 0.5)
        return (1 / (1 + np.exp(-10 * (achievement - 0.5)))) * self.priority

@dataclass
class NegotiationProposal:
    """A proposal in the negotiation process."""
    id: str
    proposer_agi: str
    goals_addressed: List[str]  # Goal IDs
    resource_allocation: Dict[str, Dict[str, float]]  # AGI -> Resource -> Amount
    outcome_prediction: Dict[str, float]  # Goal ID -> Achievement Rate
    conditions: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def calculate_social_welfare(self, goals: List[Goal]) -> float:
        """Calculate social welfare (sum of utilities)."""
        total_utility = 0.0
        for goal in goals:
            if goal.id in self.outcome_prediction:
                outcome = {'achievement_rate': self.outcome_prediction[goal.id]}
                total_utility += goal.calculate_utility(outcome)
        return total_utility
    
    def calculate_fairness(self, goals: List[Goal]) -> float:
        """Calculate fairness using Gini coefficient."""
        utilities = []
        for goal in goals:
            if goal.id in self.outcome_prediction:
                outcome = {'achievement_rate': self.outcome_prediction[goal.id]}
                utilities.append(goal.calculate_utility(outcome))
        
        if not utilities:
            return 1.0
        
        # Gini coefficient calculation
        utilities = sorted(utilities)
        n = len(utilities)
        cumsum = np.cumsum(utilities)
        return (n + 1 - 2 * np.sum((n + 1 - i) * utilities[i] for i in range(n)) / cumsum[-1]) / n

@dataclass
class NegotiationSession:
    """A negotiation session between multiple AGIs."""
    id: str
    participants: List[str]  # AGI IDs
    goals: List[Goal]
    proposals: List[NegotiationProposal] = field(default_factory=list)
    current_round: int = 0
    max_rounds: int = 10
    started_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    status: str = "active"
    final_agreement: Optional[NegotiationProposal] = None
    
    def is_expired(self) -> bool:
        """Check if negotiation has expired."""
        if self.deadline:
            return datetime.now() > self.deadline
        return self.current_round >= self.max_rounds

class GameTheoreticAnalyzer:
    """Analyzes negotiation scenarios using game theory."""
    
    @staticmethod
    def find_nash_equilibrium(payoff_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Find Nash equilibrium for a 2-player game."""
        # Simplified Nash equilibrium finding
        # In practice, this would use more sophisticated algorithms
        m, n = payoff_matrix.shape[:2]
        
        # Find pure strategy Nash equilibria
        for i in range(m):
            for j in range(n):
                # Check if (i, j) is a Nash equilibrium
                player1_best = True
                player2_best = True
                
                for k in range(m):
                    if payoff_matrix[k, j, 0] > payoff_matrix[i, j, 0]:
                        player1_best = False
                        break
                
                for k in range(n):
                    if payoff_matrix[i, k, 1] > payoff_matrix[i, j, 1]:
                        player2_best = False
                        break
                
                if player1_best and player2_best:
                    strategy1 = np.zeros(m)
                    strategy1[i] = 1.0
                    strategy2 = np.zeros(n)
                    strategy2[j] = 1.0
                    return strategy1, strategy2
        
        # If no pure strategy equilibrium, return mixed strategy approximation
        strategy1 = np.ones(m) / m
        strategy2 = np.ones(n) / n
        return strategy1, strategy2
    
    @staticmethod
    def calculate_pareto_frontier(proposals: List[NegotiationProposal], 
                                goals: List[Goal]) -> List[NegotiationProposal]:
        """Find Pareto optimal proposals."""
        pareto_optimal = []
        
        for proposal in proposals:
            is_dominated = False
            
            for other_proposal in proposals:
                if proposal.id == other_proposal.id:
                    continue
                
                # Check if other_proposal dominates proposal
                dominates = True
                strictly_better = False
                
                for goal in goals:
                    if goal.id not in proposal.outcome_prediction or goal.id not in other_proposal.outcome_prediction:
                        continue
                    
                    proposal_utility = goal.calculate_utility({'achievement_rate': proposal.outcome_prediction[goal.id]})
                    other_utility = goal.calculate_utility({'achievement_rate': other_proposal.outcome_prediction[goal.id]})
                    
                    if other_utility < proposal_utility:
                        dominates = False
                        break
                    elif other_utility > proposal_utility:
                        strictly_better = True
                
                if dominates and strictly_better:
                    is_dominated = True
                    break
            
            if not is_dominated:
                pareto_optimal.append(proposal)
        
        return pareto_optimal
    
    @staticmethod
    def calculate_shapley_values(goals: List[Goal], 
                               resource_contributions: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate Shapley values for fair allocation."""
        agi_ids = list(resource_contributions.keys())
        n = len(agi_ids)
        shapley_values = {agi_id: 0.0 for agi_id in agi_ids}
        
        # Enumerate all possible coalitions
        for coalition_size in range(1, n + 1):
            for coalition in itertools.combinations(agi_ids, coalition_size):
                coalition_value = GameTheoreticAnalyzer._calculate_coalition_value(
                    list(coalition), goals, resource_contributions
                )
                
                # Calculate marginal contributions
                for agi_id in coalition:
                    remaining_coalition = [x for x in coalition if x != agi_id]
                    remaining_value = GameTheoreticAnalyzer._calculate_coalition_value(
                        remaining_coalition, goals, resource_contributions
                    )
                    
                    marginal_contribution = coalition_value - remaining_value
                    weight = 1.0 / (n * np.math.comb(n - 1, len(remaining_coalition)))
                    shapley_values[agi_id] += weight * marginal_contribution
        
        return shapley_values
    
    @staticmethod
    def _calculate_coalition_value(coalition: List[str], goals: List[Goal],
                                 resource_contributions: Dict[str, Dict[str, float]]) -> float:
        """Calculate value generated by a coalition."""
        total_resources = {}
        
        # Sum resources from coalition members
        for agi_id in coalition:
            for resource, amount in resource_contributions.get(agi_id, {}).items():
                total_resources[resource] = total_resources.get(resource, 0) + amount
        
        # Calculate achievement based on available resources
        total_value = 0.0
        for goal in goals:
            if goal.owner_agi in coalition:
                achievement_rate = min(1.0, sum(
                    total_resources.get(resource, 0) / required
                    for resource, required in goal.resource_requirements.items()
                    if required > 0
                ))
                
                outcome = {'achievement_rate': achievement_rate}
                total_value += goal.calculate_utility(outcome)
        
        return total_value

class MechanismDesigner:
    """Designs mechanisms for incentive-compatible negotiation."""
    
    @staticmethod
    def design_vickrey_auction(goals: List[Goal]) -> Dict[str, Any]:
        """Design Vickrey auction mechanism for goal allocation."""
        # Simplified Vickrey auction for goal priorities
        mechanism = {
            'type': 'vickrey_auction',
            'rules': {
                'bidding': 'sealed_bid',
                'payment': 'second_price',
                'allocation': 'highest_bidder'
            },
            'properties': {
                'truthful': True,
                'efficient': True,
                'individual_rational': True
            }
        }
        
        return mechanism
    
    @staticmethod
    def design_combinatorial_auction(goals: List[Goal]) -> Dict[str, Any]:
        """Design combinatorial auction for complex goal bundles."""
        mechanism = {
            'type': 'combinatorial_auction',
            'rules': {
                'bidding': 'package_bids',
                'winner_determination': 'optimization',
                'payment': 'vcg_payment'
            },
            'properties': {
                'truthful': True,
                'efficient': True,
                'individual_rational': True
            }
        }
        
        return mechanism

class GoalNegotiationProtocol:
    """
    Goal Negotiation Protocol with Game-Theoretic Foundations
    
    Enables sophisticated multi-party negotiations between AGIs using
    game theory, mechanism design, and optimization principles.
    """
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.active_sessions: Dict[str, NegotiationSession] = {}
        self.completed_sessions: Dict[str, NegotiationSession] = {}
        self.negotiation_history: List[Dict[str, Any]] = []
        
        # Game-theoretic components
        self.game_analyzer = GameTheoreticAnalyzer()
        self.mechanism_designer = MechanismDesigner()
        
        # Default negotiation parameters
        self.default_strategy = NegotiationStrategy.INTEGRATIVE
        self.max_negotiation_rounds = 10
        self.negotiation_timeout = timedelta(hours=24)
    
    async def initiate_negotiation(self, goals: List[Goal], 
                                 participants: List[str],
                                 strategy: NegotiationStrategy = None) -> str:
        """Initiate a new negotiation session."""
        session_id = str(uuid.uuid4())
        
        if strategy is None:
            strategy = self.default_strategy
        
        # Create negotiation session
        session = NegotiationSession(
            id=session_id,
            participants=participants + [self.protocol.identity.id],
            goals=goals,
            deadline=datetime.now() + self.negotiation_timeout,
            max_rounds=self.max_negotiation_rounds
        )
        
        self.active_sessions[session_id] = session
        
        # Send negotiation invitations
        for participant_id in participants:
            invitation_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=participant_id,
                message_type=MessageType.GOAL_NEGOTIATION,
                timestamp=datetime.now(),
                payload={
                    'action': 'invitation',
                    'session_id': session_id,
                    'goals': [self._serialize_goal(goal) for goal in goals],
                    'strategy': strategy.value,
                    'deadline': session.deadline.isoformat(),
                    'max_rounds': session.max_rounds
                },
                requires_response=True
            )
            
            await self.protocol.send_message(invitation_message)
        
        logger.info(f"Initiated negotiation session {session_id} with {len(participants)} participants")
        return session_id
    
    async def make_proposal(self, session_id: str, proposal: NegotiationProposal):
        """Make a proposal in a negotiation session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"No active session {session_id}")
        
        session = self.active_sessions[session_id]
        
        # Validate proposal
        if not self._validate_proposal(proposal, session):
            raise ValueError("Invalid proposal")
        
        # Add proposal to session
        session.proposals.append(proposal)
        
        # Broadcast proposal to all participants
        for participant_id in session.participants:
            if participant_id == self.protocol.identity.id:
                continue
            
            proposal_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=participant_id,
                message_type=MessageType.GOAL_NEGOTIATION,
                timestamp=datetime.now(),
                payload={
                    'action': 'proposal',
                    'session_id': session_id,
                    'proposal': self._serialize_proposal(proposal),
                    'round': session.current_round
                }
            )
            
            await self.protocol.send_message(proposal_message)
    
    async def evaluate_proposals(self, session_id: str) -> Dict[str, Any]:
        """Evaluate all proposals in a session using game theory."""
        if session_id not in self.active_sessions:
            raise ValueError(f"No active session {session_id}")
        
        session = self.active_sessions[session_id]
        
        if not session.proposals:
            return {'error': 'No proposals to evaluate'}
        
        # Calculate social welfare for each proposal
        social_welfare_scores = {}
        fairness_scores = {}
        
        for proposal in session.proposals:
            social_welfare_scores[proposal.id] = proposal.calculate_social_welfare(session.goals)
            fairness_scores[proposal.id] = proposal.calculate_fairness(session.goals)
        
        # Find Pareto optimal proposals
        pareto_optimal = self.game_analyzer.calculate_pareto_frontier(
            session.proposals, session.goals
        )
        
        # Calculate Nash equilibrium if applicable
        nash_equilibrium = None
        if len(session.participants) == 2:
            # Create simplified payoff matrix for 2-player case
            payoff_matrix = self._create_payoff_matrix(session.proposals, session.goals)
            if payoff_matrix is not None:
                nash_strategies = self.game_analyzer.find_nash_equilibrium(payoff_matrix)
                nash_equilibrium = nash_strategies
        
        # Calculate Shapley values for fair allocation
        resource_contributions = self._extract_resource_contributions(session.proposals)
        shapley_values = self.game_analyzer.calculate_shapley_values(
            session.goals, resource_contributions
        )
        
        evaluation_result = {
            'social_welfare_scores': social_welfare_scores,
            'fairness_scores': fairness_scores,
            'pareto_optimal_proposals': [p.id for p in pareto_optimal],
            'nash_equilibrium': nash_equilibrium,
            'shapley_values': shapley_values,
            'best_social_welfare': max(social_welfare_scores.items(), key=lambda x: x[1]),
            'most_fair': max(fairness_scores.items(), key=lambda x: x[1])
        }
        
        return evaluation_result
    
    async def find_optimal_agreement(self, session_id: str) -> Optional[NegotiationProposal]:
        """Find optimal agreement using multi-criteria optimization."""
        evaluation = await self.evaluate_proposals(session_id)
        session = self.active_sessions[session_id]
        
        if not session.proposals:
            return None
        
        # Multi-criteria optimization: maximize social welfare and fairness
        best_proposal = None
        best_score = -float('inf')
        
        for proposal in session.proposals:
            social_welfare = evaluation['social_welfare_scores'][proposal.id]
            fairness = evaluation['fairness_scores'][proposal.id]
            
            # Weighted combination (can be adjusted based on preferences)
            combined_score = 0.7 * social_welfare + 0.3 * fairness
            
            if combined_score > best_score:
                best_score = combined_score
                best_proposal = proposal
        
        return best_proposal
    
    async def finalize_negotiation(self, session_id: str, 
                                 agreed_proposal: Optional[NegotiationProposal] = None):
        """Finalize a negotiation session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"No active session {session_id}")
        
        session = self.active_sessions[session_id]
        
        if agreed_proposal is None:
            agreed_proposal = await self.find_optimal_agreement(session_id)
        
        session.final_agreement = agreed_proposal
        session.status = "completed"
        
        # Move to completed sessions
        self.completed_sessions[session_id] = session
        del self.active_sessions[session_id]
        
        # Notify all participants
        for participant_id in session.participants:
            if participant_id == self.protocol.identity.id:
                continue
            
            finalization_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=participant_id,
                message_type=MessageType.GOAL_AGREEMENT,
                timestamp=datetime.now(),
                payload={
                    'action': 'finalization',
                    'session_id': session_id,
                    'final_agreement': self._serialize_proposal(agreed_proposal) if agreed_proposal else None,
                    'status': 'completed'
                }
            )
            
            await self.protocol.send_message(finalization_message)
        
        # Record negotiation
        self._record_negotiation(session)
        
        logger.info(f"Finalized negotiation session {session_id}")
    
    def _validate_proposal(self, proposal: NegotiationProposal, 
                         session: NegotiationSession) -> bool:
        """Validate a negotiation proposal."""
        # Check if all referenced goals exist
        session_goal_ids = {goal.id for goal in session.goals}
        for goal_id in proposal.goals_addressed:
            if goal_id not in session_goal_ids:
                return False
        
        # Check if resource allocations are reasonable
        for agi_id, resources in proposal.resource_allocation.items():
            if agi_id not in session.participants:
                return False
            
            for resource, amount in resources.items():
                if amount < 0:
                    return False
        
        return True
    
    def _serialize_goal(self, goal: Goal) -> Dict[str, Any]:
        """Serialize goal to dictionary."""
        return {
            'id': goal.id,
            'description': goal.description,
            'goal_type': goal.goal_type.value,
            'priority': goal.priority,
            'owner_agi': goal.owner_agi,
            'constraints': goal.constraints,
            'success_criteria': goal.success_criteria,
            'deadline': goal.deadline.isoformat() if goal.deadline else None,
            'utility_function': goal.utility_function.value,
            'resource_requirements': goal.resource_requirements,
            'dependencies': goal.dependencies
        }
    
    def _serialize_proposal(self, proposal: NegotiationProposal) -> Dict[str, Any]:
        """Serialize proposal to dictionary."""
        return {
            'id': proposal.id,
            'proposer_agi': proposal.proposer_agi,
            'goals_addressed': proposal.goals_addressed,
            'resource_allocation': proposal.resource_allocation,
            'outcome_prediction': proposal.outcome_prediction,
            'conditions': proposal.conditions,
            'timestamp': proposal.timestamp.isoformat()
        }
    
    def _create_payoff_matrix(self, proposals: List[NegotiationProposal], 
                            goals: List[Goal]) -> Optional[np.ndarray]:
        """Create payoff matrix for game theory analysis."""
        if len(proposals) < 2:
            return None
        
        n = len(proposals)
        payoff_matrix = np.zeros((n, n, 2))  # 2-player payoffs
        
        # This is a simplified implementation
        # In practice, you'd need more sophisticated payoff calculations
        for i, proposal1 in enumerate(proposals):
            for j, proposal2 in enumerate(proposals):
                # Calculate utilities for both players
                player1_utility = proposal1.calculate_social_welfare(goals)
                player2_utility = proposal2.calculate_social_welfare(goals)
                
                payoff_matrix[i, j, 0] = player1_utility
                payoff_matrix[i, j, 1] = player2_utility
        
        return payoff_matrix
    
    def _extract_resource_contributions(self, proposals: List[NegotiationProposal]) -> Dict[str, Dict[str, float]]:
        """Extract resource contributions from proposals."""
        contributions = {}
        
        for proposal in proposals:
            for agi_id, resources in proposal.resource_allocation.items():
                if agi_id not in contributions:
                    contributions[agi_id] = {}
                
                for resource, amount in resources.items():
                    contributions[agi_id][resource] = contributions[agi_id].get(resource, 0) + amount
        
        return contributions
    
    def _record_negotiation(self, session: NegotiationSession):
        """Record negotiation session for analysis."""
        negotiation_record = {
            'session_id': session.id,
            'participants': session.participants,
            'goals_count': len(session.goals),
            'proposals_count': len(session.proposals),
            'rounds': session.current_round,
            'duration': (datetime.now() - session.started_at).total_seconds(),
            'success': session.final_agreement is not None,
            'final_social_welfare': session.final_agreement.calculate_social_welfare(session.goals) if session.final_agreement else 0,
            'timestamp': datetime.now().isoformat()
        }
        
        self.negotiation_history.append(negotiation_record)
    
    async def handle_goal_proposal(self, message: CommunicationMessage):
        """Handle goal proposal from another AGI."""
        payload = message.payload
        action = payload.get('action')
        
        try:
            if action == 'invitation':
                await self._handle_negotiation_invitation(message)
            elif action == 'proposal':
                await self._handle_proposal(message)
            elif action == 'evaluation':
                await self._handle_evaluation_request(message)
            else:
                logger.warning(f"Unknown goal proposal action: {action}")
        
        except Exception as e:
            logger.error(f"Error handling goal proposal: {e}")
    
    async def _handle_negotiation_invitation(self, message: CommunicationMessage):
        """Handle negotiation invitation."""
        payload = message.payload
        session_id = payload['session_id']
        
        # Parse goals
        goals = []
        for goal_data in payload['goals']:
            goal = Goal(
                id=goal_data['id'],
                description=goal_data['description'],
                goal_type=GoalType(goal_data['goal_type']),
                priority=goal_data['priority'],
                owner_agi=goal_data['owner_agi'],
                constraints=goal_data.get('constraints', []),
                success_criteria=goal_data.get('success_criteria', {}),
                deadline=datetime.fromisoformat(goal_data['deadline']) if goal_data.get('deadline') else None,
                utility_function=UtilityFunction(goal_data.get('utility_function', 'linear')),
                resource_requirements=goal_data.get('resource_requirements', {}),
                dependencies=goal_data.get('dependencies', [])
            )
            goals.append(goal)
        
        # Create local session
        session = NegotiationSession(
            id=session_id,
            participants=payload.get('participants', []) + [message.sender_id],
            goals=goals,
            deadline=datetime.fromisoformat(payload['deadline']),
            max_rounds=payload.get('max_rounds', 10)
        )
        
        self.active_sessions[session_id] = session
        
        # Send acceptance response
        response_message = CommunicationMessage(
            id=str(uuid.uuid4()),
            sender_id=self.protocol.identity.id,
            receiver_id=message.sender_id,
            message_type=MessageType.GOAL_NEGOTIATION,
            timestamp=datetime.now(),
            payload={
                'action': 'acceptance',
                'session_id': session_id,
                'accepted': True
            }
        )
        
        await self.protocol.send_message(response_message)
    
    async def _handle_proposal(self, message: CommunicationMessage):
        """Handle negotiation proposal."""
        payload = message.payload
        session_id = payload['session_id']
        
        if session_id not in self.active_sessions:
            logger.warning(f"Received proposal for unknown session {session_id}")
            return
        
        session = self.active_sessions[session_id]
        proposal_data = payload['proposal']
        
        # Parse proposal
        proposal = NegotiationProposal(
            id=proposal_data['id'],
            proposer_agi=proposal_data['proposer_agi'],
            goals_addressed=proposal_data['goals_addressed'],
            resource_allocation=proposal_data['resource_allocation'],
            outcome_prediction=proposal_data['outcome_prediction'],
            conditions=proposal_data['conditions'],
            timestamp=datetime.fromisoformat(proposal_data['timestamp'])
        )
        
        # Add to session
        session.proposals.append(proposal)
        
        logger.info(f"Received proposal {proposal.id} for session {session_id}")
    
    async def _handle_evaluation_request(self, message: CommunicationMessage):
        """Handle evaluation request."""
        payload = message.payload
        session_id = payload['session_id']
        
        if session_id not in self.active_sessions:
            return
        
        # Perform evaluation
        evaluation = await self.evaluate_proposals(session_id)
        
        # Send evaluation response
        response_message = CommunicationMessage(
            id=str(uuid.uuid4()),
            sender_id=self.protocol.identity.id,
            receiver_id=message.sender_id,
            message_type=MessageType.GOAL_NEGOTIATION,
            timestamp=datetime.now(),
            payload={
                'action': 'evaluation_result',
                'session_id': session_id,
                'evaluation': evaluation
            }
        )
        
        await self.protocol.send_message(response_message)
    
    def get_negotiation_statistics(self) -> Dict[str, Any]:
        """Get negotiation statistics."""
        if not self.negotiation_history:
            return {'total_negotiations': 0}
        
        total_negotiations = len(self.negotiation_history)
        successful_negotiations = sum(1 for record in self.negotiation_history if record['success'])
        avg_duration = sum(record['duration'] for record in self.negotiation_history) / total_negotiations
        avg_rounds = sum(record['rounds'] for record in self.negotiation_history) / total_negotiations
        
        return {
            'total_negotiations': total_negotiations,
            'successful_negotiations': successful_negotiations,
            'success_rate': successful_negotiations / total_negotiations,
            'average_duration_seconds': avg_duration,
            'average_rounds': avg_rounds,
            'active_sessions': len(self.active_sessions)
        }