"""
Stakeholder Consensus Mechanisms for AGI Governance.

This module implements advanced consensus mechanisms including quadratic voting,
liquid democracy, and multi-stakeholder decision-making processes to ensure
fair and representative governance of AGI systems.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses import dataclass, asdict
import json
import math
import numpy as np
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class VotingMethod(Enum):
    QUADRATIC = "quadratic"
    LIQUID_DEMOCRACY = "liquid_democracy"
    RANKED_CHOICE = "ranked_choice"
    APPROVAL = "approval"
    WEIGHTED = "weighted"
    FUTARCHY = "futarchy"


class StakeholderCategory(Enum):
    GENERAL_PUBLIC = "general_public"
    TECHNICAL_EXPERTS = "technical_experts"
    ETHICISTS = "ethicists"
    POLICYMAKERS = "policymakers"
    AFFECTED_COMMUNITIES = "affected_communities"
    AGI_ENTITIES = "agi_entities"
    ORGANIZATIONS = "organizations"


class ConsensusStatus(Enum):
    GATHERING = "gathering"
    DELIBERATING = "deliberating"
    VOTING = "voting"
    CONSENSUS_REACHED = "consensus_reached"
    CONSENSUS_FAILED = "consensus_failed"
    APPEALED = "appealed"


@dataclass
class StakeholderProfile:
    """Comprehensive stakeholder profile for consensus mechanisms."""
    id: str
    name: str
    category: StakeholderCategory
    expertise_domains: List[str]
    credibility_score: float
    voting_power_base: float
    delegation_received: float
    active_delegations: Dict[str, float]  # issue_domain -> voting power delegated
    participation_history: Dict[str, Any]
    verification_status: str
    created_at: datetime


@dataclass
class QuadraticVote:
    """Represents a quadratic vote with cost calculation."""
    voter_id: str
    proposal_id: str
    vote_direction: str  # 'for', 'against', 'abstain'
    vote_intensity: int  # Number of votes (sqrt of tokens spent)
    token_cost: float
    reasoning: str
    cast_at: datetime


@dataclass
class Delegation:
    """Represents delegation in liquid democracy."""
    delegator_id: str
    delegate_id: str
    scope: str  # 'general' or specific issue domain
    voting_power: float
    expiration: Optional[datetime]
    revocable: bool
    created_at: datetime


@dataclass
class ConsensusProcess:
    """Manages a complete consensus process."""
    id: str
    proposal_id: str
    method: VotingMethod
    phases: List[str]
    current_phase: str
    phase_deadlines: Dict[str, datetime]
    stakeholder_weights: Dict[StakeholderCategory, float]
    consensus_threshold: float
    participation_threshold: float
    votes: Dict[str, Any]
    delegations: List[Delegation]
    deliberation_log: List[Dict[str, Any]]
    status: ConsensusStatus
    final_result: Optional[Dict[str, Any]]
    created_at: datetime


class QuadraticVotingSystem:
    """Implements quadratic voting with voice credits."""
    
    def __init__(self, max_credits_per_voter: int = 100):
        self.max_credits_per_voter = max_credits_per_voter
        self.vote_records: Dict[str, List[QuadraticVote]] = {}
    
    def calculate_vote_cost(self, num_votes: int) -> float:
        """Calculate the credit cost for a given number of votes."""
        return num_votes ** 2
    
    def calculate_max_votes(self, available_credits: float) -> int:
        """Calculate maximum votes possible with available credits."""
        return int(math.sqrt(available_credits))
    
    def cast_quadratic_vote(self, voter_id: str, proposal_id: str, 
                           vote_direction: str, vote_intensity: int,
                           reasoning: str = "") -> Tuple[bool, str]:
        """Cast a quadratic vote."""
        try:
            cost = self.calculate_vote_cost(vote_intensity)
            
            # Check if voter has sufficient credits
            used_credits = self._get_used_credits(voter_id, proposal_id)
            if used_credits + cost > self.max_credits_per_voter:
                return False, f"Insufficient credits. Need {cost}, have {self.max_credits_per_voter - used_credits}"
            
            # Create vote record
            vote = QuadraticVote(
                voter_id=voter_id,
                proposal_id=proposal_id,
                vote_direction=vote_direction,
                vote_intensity=vote_intensity,
                token_cost=cost,
                reasoning=reasoning,
                cast_at=datetime.utcnow()
            )
            
            # Store vote
            if voter_id not in self.vote_records:
                self.vote_records[voter_id] = []
            
            # Remove any previous vote on same proposal
            self.vote_records[voter_id] = [
                v for v in self.vote_records[voter_id] 
                if v.proposal_id != proposal_id
            ]
            
            self.vote_records[voter_id].append(vote)
            
            logger.info(f"Quadratic vote cast: {voter_id} voted {vote_direction} "
                       f"with intensity {vote_intensity} on {proposal_id}")
            return True, "Vote cast successfully"
            
        except Exception as e:
            logger.error(f"Error casting quadratic vote: {e}")
            return False, str(e)
    
    def get_proposal_results(self, proposal_id: str) -> Dict[str, Any]:
        """Calculate quadratic voting results for a proposal."""
        votes_for = 0
        votes_against = 0
        votes_abstain = 0
        total_voters = 0
        total_credits_used = 0
        
        voter_votes = {}
        
        for voter_id, votes in self.vote_records.items():
            for vote in votes:
                if vote.proposal_id == proposal_id:
                    voter_votes[voter_id] = vote
                    total_voters += 1
                    total_credits_used += vote.token_cost
                    
                    if vote.vote_direction == 'for':
                        votes_for += vote.vote_intensity
                    elif vote.vote_direction == 'against':
                        votes_against += vote.vote_intensity
                    elif vote.vote_direction == 'abstain':
                        votes_abstain += vote.vote_intensity
        
        total_votes = votes_for + votes_against + votes_abstain
        
        return {
            'votes_for': votes_for,
            'votes_against': votes_against,
            'votes_abstain': votes_abstain,
            'total_votes': total_votes,
            'total_voters': total_voters,
            'total_credits_used': total_credits_used,
            'support_ratio': votes_for / total_votes if total_votes > 0 else 0,
            'opposition_ratio': votes_against / total_votes if total_votes > 0 else 0,
            'voter_details': voter_votes
        }
    
    def _get_used_credits(self, voter_id: str, current_proposal_id: str) -> float:
        """Get credits already used by voter (excluding current proposal)."""
        if voter_id not in self.vote_records:
            return 0.0
        
        return sum(vote.token_cost for vote in self.vote_records[voter_id] 
                  if vote.proposal_id != current_proposal_id)


class LiquidDemocracy:
    """Implements liquid democracy with transitive delegation."""
    
    def __init__(self):
        self.delegations: Dict[str, List[Delegation]] = {}
        self.delegation_graph: Dict[str, Set[str]] = {}
        self.voting_power_cache: Dict[str, float] = {}
    
    def delegate_voting_power(self, delegator_id: str, delegate_id: str,
                             scope: str, voting_power: float,
                             expiration: Optional[datetime] = None) -> bool:
        """Delegate voting power to another stakeholder."""
        try:
            # Check for delegation cycles
            if self._would_create_cycle(delegator_id, delegate_id):
                logger.warning(f"Delegation would create cycle: {delegator_id} -> {delegate_id}")
                return False
            
            delegation = Delegation(
                delegator_id=delegator_id,
                delegate_id=delegate_id,
                scope=scope,
                voting_power=voting_power,
                expiration=expiration,
                revocable=True,
                created_at=datetime.utcnow()
            )
            
            # Store delegation
            if delegator_id not in self.delegations:
                self.delegations[delegator_id] = []
            
            # Remove any existing delegation for same scope
            self.delegations[delegator_id] = [
                d for d in self.delegations[delegator_id] 
                if d.scope != scope or d.delegate_id != delegate_id
            ]
            
            self.delegations[delegator_id].append(delegation)
            
            # Update delegation graph
            if delegator_id not in self.delegation_graph:
                self.delegation_graph[delegator_id] = set()
            self.delegation_graph[delegator_id].add(delegate_id)
            
            # Clear cache
            self.voting_power_cache.clear()
            
            logger.info(f"Delegation created: {delegator_id} -> {delegate_id} "
                       f"({scope}, {voting_power} power)")
            return True
            
        except Exception as e:
            logger.error(f"Error creating delegation: {e}")
            return False
    
    def revoke_delegation(self, delegator_id: str, delegate_id: str, scope: str) -> bool:
        """Revoke a delegation."""
        try:
            if delegator_id not in self.delegations:
                return False
            
            # Remove delegation
            original_count = len(self.delegations[delegator_id])
            self.delegations[delegator_id] = [
                d for d in self.delegations[delegator_id]
                if not (d.delegate_id == delegate_id and d.scope == scope)
            ]
            
            # Update delegation graph
            if not any(d.delegate_id == delegate_id for d in self.delegations[delegator_id]):
                self.delegation_graph[delegator_id].discard(delegate_id)
            
            # Clear cache
            self.voting_power_cache.clear()
            
            revoked = len(self.delegations[delegator_id]) < original_count
            if revoked:
                logger.info(f"Delegation revoked: {delegator_id} -> {delegate_id} ({scope})")
            
            return revoked
            
        except Exception as e:
            logger.error(f"Error revoking delegation: {e}")
            return False
    
    def calculate_effective_voting_power(self, stakeholder_id: str, scope: str) -> float:
        """Calculate effective voting power including delegations."""
        if stakeholder_id in self.voting_power_cache:
            return self.voting_power_cache[stakeholder_id]
        
        power = 1.0  # Base voting power
        
        # Add delegated power received
        for delegator_id, delegations in self.delegations.items():
            for delegation in delegations:
                if (delegation.delegate_id == stakeholder_id and 
                    (delegation.scope == scope or delegation.scope == 'general') and
                    self._is_delegation_active(delegation)):
                    
                    # Recursively calculate delegator's power
                    delegator_power = self.calculate_effective_voting_power(delegator_id, scope)
                    power += delegation.voting_power * delegator_power
        
        self.voting_power_cache[stakeholder_id] = power
        return power
    
    def get_delegation_chain(self, stakeholder_id: str, scope: str) -> List[str]:
        """Get the chain of delegations for a stakeholder."""
        chain = [stakeholder_id]
        visited = set([stakeholder_id])
        
        current = stakeholder_id
        while current in self.delegations:
            for delegation in self.delegations[current]:
                if ((delegation.scope == scope or delegation.scope == 'general') and
                    self._is_delegation_active(delegation) and
                    delegation.delegate_id not in visited):
                    
                    chain.append(delegation.delegate_id)
                    visited.add(delegation.delegate_id)
                    current = delegation.delegate_id
                    break
            else:
                break
        
        return chain
    
    def _would_create_cycle(self, delegator_id: str, delegate_id: str) -> bool:
        """Check if delegation would create a cycle."""
        visited = set()
        current = delegate_id
        
        while current and current not in visited:
            visited.add(current)
            
            # Find if current delegates to someone
            if current in self.delegation_graph:
                # Follow the first delegation (simplified)
                next_delegates = self.delegation_graph[current]
                if next_delegates:
                    current = next(iter(next_delegates))
                    if current == delegator_id:
                        return True
                else:
                    break
            else:
                break
        
        return False
    
    def _is_delegation_active(self, delegation: Delegation) -> bool:
        """Check if a delegation is currently active."""
        if delegation.expiration and datetime.utcnow() > delegation.expiration:
            return False
        return True


class MultiStakeholderConsensus:
    """Manages multi-stakeholder consensus processes."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stakeholders: Dict[str, StakeholderProfile] = {}
        self.consensus_processes: Dict[str, ConsensusProcess] = {}
        self.quadratic_voting = QuadraticVotingSystem()
        self.liquid_democracy = LiquidDemocracy()
        
        # Default stakeholder weights
        self.default_weights = {
            StakeholderCategory.GENERAL_PUBLIC: 0.3,
            StakeholderCategory.TECHNICAL_EXPERTS: 0.2,
            StakeholderCategory.ETHICISTS: 0.15,
            StakeholderCategory.POLICYMAKERS: 0.15,
            StakeholderCategory.AFFECTED_COMMUNITIES: 0.15,
            StakeholderCategory.AGI_ENTITIES: 0.05
        }
    
    def register_stakeholder(self, stakeholder: StakeholderProfile) -> bool:
        """Register a stakeholder in the consensus system."""
        try:
            self.stakeholders[stakeholder.id] = stakeholder
            logger.info(f"Registered stakeholder: {stakeholder.name} ({stakeholder.category.value})")
            return True
        except Exception as e:
            logger.error(f"Error registering stakeholder: {e}")
            return False
    
    def initiate_consensus_process(self, proposal_id: str, method: VotingMethod,
                                 custom_weights: Optional[Dict[StakeholderCategory, float]] = None,
                                 custom_thresholds: Optional[Dict[str, float]] = None) -> str:
        """Initiate a new consensus process."""
        try:
            process_id = f"consensus_{proposal_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Define process phases
            phases = []
            if method in [VotingMethod.LIQUID_DEMOCRACY, VotingMethod.QUADRATIC]:
                phases = ['information', 'deliberation', 'voting', 'finalization']
            else:
                phases = ['information', 'voting', 'finalization']
            
            # Calculate phase deadlines
            phase_deadlines = {}
            base_time = datetime.utcnow()
            
            phase_durations = {
                'information': timedelta(days=2),
                'deliberation': timedelta(days=3),
                'voting': timedelta(days=5),
                'finalization': timedelta(days=1)
            }
            
            current_time = base_time
            for phase in phases:
                current_time += phase_durations[phase]
                phase_deadlines[phase] = current_time
            
            process = ConsensusProcess(
                id=process_id,
                proposal_id=proposal_id,
                method=method,
                phases=phases,
                current_phase=phases[0],
                phase_deadlines=phase_deadlines,
                stakeholder_weights=custom_weights or self.default_weights,
                consensus_threshold=custom_thresholds.get('consensus', 0.65) if custom_thresholds else 0.65,
                participation_threshold=custom_thresholds.get('participation', 0.15) if custom_thresholds else 0.15,
                votes={},
                delegations=[],
                deliberation_log=[],
                status=ConsensusStatus.GATHERING,
                final_result=None,
                created_at=datetime.utcnow()
            )
            
            self.consensus_processes[process_id] = process
            
            logger.info(f"Initiated consensus process: {process_id} using {method.value}")
            return process_id
            
        except Exception as e:
            logger.error(f"Error initiating consensus process: {e}")
            return ""
    
    def cast_consensus_vote(self, process_id: str, voter_id: str, 
                          vote_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Cast a vote in a consensus process."""
        try:
            process = self.consensus_processes.get(process_id)
            if not process:
                return False, "Unknown consensus process"
            
            if process.current_phase != 'voting':
                return False, f"Not in voting phase (current: {process.current_phase})"
            
            stakeholder = self.stakeholders.get(voter_id)
            if not stakeholder:
                return False, "Unregistered stakeholder"
            
            if process.method == VotingMethod.QUADRATIC:
                return self._cast_quadratic_consensus_vote(process, stakeholder, vote_data)
            elif process.method == VotingMethod.LIQUID_DEMOCRACY:
                return self._cast_liquid_democracy_vote(process, stakeholder, vote_data)
            elif process.method == VotingMethod.WEIGHTED:
                return self._cast_weighted_vote(process, stakeholder, vote_data)
            else:
                return False, f"Unsupported voting method: {process.method}"
            
        except Exception as e:
            logger.error(f"Error casting consensus vote: {e}")
            return False, str(e)
    
    def _cast_quadratic_consensus_vote(self, process: ConsensusProcess, 
                                     stakeholder: StakeholderProfile,
                                     vote_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Cast a quadratic vote in consensus process."""
        success, message = self.quadratic_voting.cast_quadratic_vote(
            stakeholder.id,
            process.proposal_id,
            vote_data['direction'],
            vote_data['intensity'],
            vote_data.get('reasoning', '')
        )
        
        if success:
            # Apply stakeholder category weight
            category_weight = process.stakeholder_weights.get(stakeholder.category, 1.0)
            effective_power = vote_data['intensity'] * category_weight * stakeholder.credibility_score
            
            process.votes[stakeholder.id] = {
                'method': 'quadratic',
                'raw_intensity': vote_data['intensity'],
                'effective_power': effective_power,
                'direction': vote_data['direction'],
                'reasoning': vote_data.get('reasoning', ''),
                'timestamp': datetime.utcnow().isoformat()
            }
        
        return success, message
    
    def _cast_liquid_democracy_vote(self, process: ConsensusProcess,
                                  stakeholder: StakeholderProfile,
                                  vote_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Cast a vote using liquid democracy."""
        # Calculate effective voting power including delegations
        scope = process.proposal_id  # Use proposal as scope
        effective_power = self.liquid_democracy.calculate_effective_voting_power(
            stakeholder.id, scope)
        
        # Apply stakeholder category weight
        category_weight = process.stakeholder_weights.get(stakeholder.category, 1.0)
        final_power = effective_power * category_weight * stakeholder.credibility_score
        
        process.votes[stakeholder.id] = {
            'method': 'liquid_democracy',
            'base_power': 1.0,
            'delegated_power': effective_power - 1.0,
            'effective_power': final_power,
            'direction': vote_data['direction'],
            'reasoning': vote_data.get('reasoning', ''),
            'delegation_chain': self.liquid_democracy.get_delegation_chain(stakeholder.id, scope),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return True, "Liquid democracy vote cast successfully"
    
    def _cast_weighted_vote(self, process: ConsensusProcess,
                          stakeholder: StakeholderProfile,
                          vote_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Cast a weighted vote."""
        category_weight = process.stakeholder_weights.get(stakeholder.category, 1.0)
        effective_power = category_weight * stakeholder.credibility_score * stakeholder.voting_power_base
        
        process.votes[stakeholder.id] = {
            'method': 'weighted',
            'effective_power': effective_power,
            'direction': vote_data['direction'],
            'reasoning': vote_data.get('reasoning', ''),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return True, "Weighted vote cast successfully"
    
    def advance_consensus_phase(self, process_id: str) -> bool:
        """Advance consensus process to next phase."""
        try:
            process = self.consensus_processes.get(process_id)
            if not process:
                return False
            
            current_phase_index = process.phases.index(process.current_phase)
            
            if current_phase_index < len(process.phases) - 1:
                next_phase = process.phases[current_phase_index + 1]
                process.current_phase = next_phase
                
                if next_phase == 'voting':
                    process.status = ConsensusStatus.VOTING
                elif next_phase == 'finalization':
                    process.status = ConsensusStatus.CONSENSUS_REACHED
                
                logger.info(f"Advanced process {process_id} to phase: {next_phase}")
                return True
            else:
                # Process complete
                result = self.finalize_consensus(process_id)
                return result is not None
            
        except Exception as e:
            logger.error(f"Error advancing consensus phase: {e}")
            return False
    
    def finalize_consensus(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Finalize consensus process and calculate results."""
        try:
            process = self.consensus_processes.get(process_id)
            if not process:
                return None
            
            # Calculate results based on voting method
            if process.method == VotingMethod.QUADRATIC:
                results = self._calculate_quadratic_results(process)
            elif process.method == VotingMethod.LIQUID_DEMOCRACY:
                results = self._calculate_liquid_democracy_results(process)
            elif process.method == VotingMethod.WEIGHTED:
                results = self._calculate_weighted_results(process)
            else:
                results = self._calculate_simple_results(process)
            
            # Check if consensus achieved
            consensus_reached = (
                results['participation_rate'] >= process.participation_threshold and
                results['support_ratio'] >= process.consensus_threshold
            )
            
            process.final_result = {
                'consensus_reached': consensus_reached,
                'results': results,
                'finalized_at': datetime.utcnow().isoformat()
            }
            
            process.status = (ConsensusStatus.CONSENSUS_REACHED if consensus_reached 
                            else ConsensusStatus.CONSENSUS_FAILED)
            
            logger.info(f"Finalized consensus {process_id}: {'REACHED' if consensus_reached else 'FAILED'}")
            return process.final_result
            
        except Exception as e:
            logger.error(f"Error finalizing consensus: {e}")
            return None
    
    def _calculate_quadratic_results(self, process: ConsensusProcess) -> Dict[str, Any]:
        """Calculate results for quadratic voting."""
        total_power = 0
        support_power = 0
        opposition_power = 0
        abstain_power = 0
        
        for vote in process.votes.values():
            total_power += vote['effective_power']
            
            if vote['direction'] == 'for':
                support_power += vote['effective_power']
            elif vote['direction'] == 'against':
                opposition_power += vote['effective_power']
            else:
                abstain_power += vote['effective_power']
        
        total_eligible = len(self.stakeholders)
        participation_rate = len(process.votes) / total_eligible if total_eligible > 0 else 0
        support_ratio = support_power / total_power if total_power > 0 else 0
        
        return {
            'method': 'quadratic',
            'total_power': total_power,
            'support_power': support_power,
            'opposition_power': opposition_power,
            'abstain_power': abstain_power,
            'support_ratio': support_ratio,
            'opposition_ratio': opposition_power / total_power if total_power > 0 else 0,
            'participation_rate': participation_rate,
            'total_voters': len(process.votes)
        }
    
    def _calculate_liquid_democracy_results(self, process: ConsensusProcess) -> Dict[str, Any]:
        """Calculate results for liquid democracy."""
        return self._calculate_weighted_results(process)  # Similar calculation
    
    def _calculate_weighted_results(self, process: ConsensusProcess) -> Dict[str, Any]:
        """Calculate results for weighted voting."""
        total_power = 0
        support_power = 0
        opposition_power = 0
        
        for vote in process.votes.values():
            total_power += vote['effective_power']
            
            if vote['direction'] == 'for':
                support_power += vote['effective_power']
            elif vote['direction'] == 'against':
                opposition_power += vote['effective_power']
        
        # Calculate total eligible power
        total_eligible_power = sum(
            self.default_weights.get(s.category, 1.0) * s.credibility_score * s.voting_power_base
            for s in self.stakeholders.values()
        )
        
        participation_rate = total_power / total_eligible_power if total_eligible_power > 0 else 0
        support_ratio = support_power / total_power if total_power > 0 else 0
        
        return {
            'method': 'weighted',
            'total_power': total_power,
            'support_power': support_power,
            'opposition_power': opposition_power,
            'support_ratio': support_ratio,
            'opposition_ratio': opposition_power / total_power if total_power > 0 else 0,
            'participation_rate': participation_rate,
            'total_voters': len(process.votes)
        }
    
    def _calculate_simple_results(self, process: ConsensusProcess) -> Dict[str, Any]:
        """Calculate results for simple voting methods."""
        support_votes = sum(1 for vote in process.votes.values() if vote['direction'] == 'for')
        opposition_votes = sum(1 for vote in process.votes.values() if vote['direction'] == 'against')
        total_votes = len(process.votes)
        
        total_eligible = len(self.stakeholders)
        participation_rate = total_votes / total_eligible if total_eligible > 0 else 0
        support_ratio = support_votes / total_votes if total_votes > 0 else 0
        
        return {
            'method': 'simple',
            'support_votes': support_votes,
            'opposition_votes': opposition_votes,
            'total_votes': total_votes,
            'support_ratio': support_ratio,
            'opposition_ratio': opposition_votes / total_votes if total_votes > 0 else 0,
            'participation_rate': participation_rate,
            'total_voters': total_votes
        }
    
    def get_consensus_summary(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Get a comprehensive summary of consensus process."""
        process = self.consensus_processes.get(process_id)
        if not process:
            return None
        
        summary = {
            'process_id': process_id,
            'proposal_id': process.proposal_id,
            'method': process.method.value,
            'status': process.status.value,
            'current_phase': process.current_phase,
            'phases_completed': process.phases[:process.phases.index(process.current_phase) + 1],
            'participation_stats': {
                'total_eligible': len(self.stakeholders),
                'voted': len(process.votes),
                'participation_rate': len(process.votes) / len(self.stakeholders) if self.stakeholders else 0
            },
            'thresholds': {
                'consensus': process.consensus_threshold,
                'participation': process.participation_threshold
            }
        }
        
        if process.final_result:
            summary['final_result'] = process.final_result
        
        return summary
    
    def get_stakeholder_influence_analysis(self, process_id: str) -> Dict[str, Any]:
        """Analyze stakeholder influence in consensus process."""
        process = self.consensus_processes.get(process_id)
        if not process:
            return {}
        
        influence_analysis = {
            'by_category': {},
            'by_individual': {},
            'power_distribution': {},
            'delegation_impact': {}
        }
        
        # Analyze by category
        category_power = {}
        for vote in process.votes.values():
            voter = self.stakeholders.get(vote.get('voter_id'))
            if voter:
                category = voter.category.value
                category_power[category] = category_power.get(category, 0) + vote['effective_power']
        
        influence_analysis['by_category'] = category_power
        
        # Analyze individual influence
        individual_power = {
            voter_id: vote['effective_power'] 
            for voter_id, vote in process.votes.items()
        }
        influence_analysis['by_individual'] = individual_power
        
        return influence_analysis