"""
Reputation System
================

Advanced reputation and trust scoring system for AGI agents in the
SingularityNET ecosystem with economic incentives and validation mechanisms.
"""

import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from decimal import Decimal, getcontext
from dataclasses import dataclass, field
from enum import Enum
import time
import logging

from ..core.base_engine import BaseEconomicEngine, EconomicEvent
from ..core.types import (
    Agent, AgentID, TokenType, ReputationEvent, AgentType
)
from ..core.exceptions import (
    ReputationError, InvalidReputationScoreError, TrustThresholdError
)

# Set decimal precision
getcontext().prec = 28

logger = logging.getLogger(__name__)

class ReputationDimension(Enum):
    """Different dimensions of reputation"""
    TECHNICAL_QUALITY = "technical_quality"
    RELIABILITY = "reliability"
    COOPERATION = "cooperation"
    HONESTY = "honesty"
    INNOVATION = "innovation"
    RESPONSIVENESS = "responsiveness"
    RESOURCE_EFFICIENCY = "resource_efficiency"
    VALUE_ALIGNMENT = "value_alignment"

class ValidationMethod(Enum):
    """Methods for validating reputation events"""
    PEER_REVIEW = "peer_review"
    AUTOMATED_METRICS = "automated_metrics"
    HUMAN_EVALUATION = "human_evaluation"
    CONSENSUS_ALGORITHM = "consensus_algorithm"
    BLOCKCHAIN_PROOF = "blockchain_proof"
    MULTI_STAKEHOLDER = "multi_stakeholder"

@dataclass
class ReputationScore:
    """Multi-dimensional reputation score"""
    agent_id: str
    dimensions: Dict[ReputationDimension, float]
    overall_score: float
    confidence: float
    evidence_count: int
    last_updated: float
    
    def __post_init__(self):
        # Ensure scores are within valid range
        for dim in ReputationDimension:
            if dim in self.dimensions:
                self.dimensions[dim] = max(0.0, min(1.0, self.dimensions[dim]))
        self.overall_score = max(0.0, min(1.0, self.overall_score))
        self.confidence = max(0.0, min(1.0, self.confidence))

@dataclass
class TrustRelationship:
    """Trust relationship between agents"""
    truster_id: str
    trustee_id: str
    trust_score: float
    trust_category: str  # e.g., 'service_quality', 'financial', 'collaboration'
    evidence_events: List[str]  # Event IDs supporting this trust score
    created_at: float
    last_updated: float
    
    def __post_init__(self):
        self.trust_score = max(0.0, min(1.0, self.trust_score))

@dataclass
class ReputationValidator:
    """Validator for reputation events"""
    validator_id: str
    validator_type: str  # 'human', 'agent', 'system'
    expertise_areas: List[ReputationDimension]
    validation_history: List[str]  # Event IDs they've validated
    own_reputation: float
    stake_amount: Decimal
    is_active: bool = True

class ReputationSystem(BaseEconomicEngine):
    """
    Comprehensive reputation system with multi-dimensional scoring,
    trust networks, and economic incentives for honest validation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Agent reputation scores
        self.reputation_scores: Dict[str, ReputationScore] = {}
        
        # Trust relationships between agents
        self.trust_relationships: Dict[Tuple[str, str], TrustRelationship] = {}
        
        # Trust network graph (adjacency list)
        self.trust_network: Dict[str, Dict[str, float]] = {}
        
        # Reputation events history
        self.reputation_events: List[ReputationEvent] = []
        
        # Validators
        self.validators: Dict[str, ReputationValidator] = {}
        
        # Reputation parameters
        self.decay_rate = config.get('decay_rate', 0.001)
        self.min_validators_required = config.get('min_validators_required', 3)
        self.validator_stake_requirement = Decimal(str(config.get('validator_stake_requirement', '100')))
        self.trust_propagation_depth = config.get('trust_propagation_depth', 3)
        
        # Dimension weights for overall score calculation
        self.dimension_weights = config.get('dimension_weights', {
            ReputationDimension.TECHNICAL_QUALITY: 0.25,
            ReputationDimension.RELIABILITY: 0.20,
            ReputationDimension.COOPERATION: 0.15,
            ReputationDimension.HONESTY: 0.15,
            ReputationDimension.INNOVATION: 0.10,
            ReputationDimension.RESPONSIVENESS: 0.05,
            ReputationDimension.RESOURCE_EFFICIENCY: 0.05,
            ReputationDimension.VALUE_ALIGNMENT: 0.05
        })
    
    def start(self) -> bool:
        """Start the reputation system"""
        try:
            self.is_active = True
            self.metrics['start_time'] = time.time()
            self.log_event('reputation_system_started')
            logger.info("Reputation System started")
            return True
        except Exception as e:
            logger.error(f"Failed to start Reputation System: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the reputation system"""
        try:
            self.is_active = False
            self.log_event('reputation_system_stopped')
            logger.info("Reputation System stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop Reputation System: {e}")
            return False
    
    def process_event(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process reputation system events"""
        if not self.is_active:
            return {'error': 'System not active'}
        
        try:
            if event.event_type == 'reputation_update':
                return self._process_reputation_update(event)
            elif event.event_type == 'trust_update':
                return self._process_trust_update(event)
            elif event.event_type == 'register_validator':
                return self._process_validator_registration(event)
            elif event.event_type == 'validate_reputation_event':
                return self._process_reputation_validation(event)
            elif event.event_type == 'calculate_trust_score':
                return self._process_trust_calculation(event)
            else:
                return {'error': f'Unknown event type: {event.event_type}'}
        except Exception as e:
            logger.error(f"Error processing reputation event {event.event_type}: {e}")
            return {'error': str(e)}
    
    def initialize_agent_reputation(self, agent_id: str, initial_scores: Dict[ReputationDimension, float] = None) -> bool:
        """Initialize reputation scoring for a new agent"""
        try:
            if agent_id in self.reputation_scores:
                return True  # Already initialized
            
            # Set initial scores
            initial_scores = initial_scores or {}
            dimensions = {}
            
            for dimension in ReputationDimension:
                dimensions[dimension] = initial_scores.get(dimension, 0.5)  # Neutral start
            
            overall_score = self._calculate_overall_score(dimensions)
            
            reputation = ReputationScore(
                agent_id=agent_id,
                dimensions=dimensions,
                overall_score=overall_score,
                confidence=0.1,  # Low confidence initially
                evidence_count=0,
                last_updated=time.time()
            )
            
            self.reputation_scores[agent_id] = reputation
            self.trust_network[agent_id] = {}
            
            self.log_event('agent_reputation_initialized', agent_id, {
                'initial_overall_score': overall_score
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize reputation for agent {agent_id}: {e}")
            return False
    
    def submit_reputation_event(self, event: ReputationEvent) -> Dict[str, Any]:
        """Submit a reputation event for validation and processing"""
        try:
            # Validate event
            if not self._validate_reputation_event(event):
                raise ReputationError("Invalid reputation event")
            
            # Ensure agent has reputation profile
            if event.agent_id not in self.reputation_scores:
                self.initialize_agent_reputation(event.agent_id)
            
            # Add to events list
            self.reputation_events.append(event)
            
            # Get validators for this event
            validators = self._select_validators_for_event(event)
            
            if len(validators) < self.min_validators_required:
                return {
                    'success': False,
                    'message': f'Insufficient validators available. Required: {self.min_validators_required}, Available: {len(validators)}',
                    'event_id': event.event_id
                }
            
            # Submit to validators (in real system, this would be asynchronous)
            validation_results = self._conduct_validation(event, validators)
            
            # Process validation results
            if validation_results['consensus_reached']:
                self._apply_reputation_update(event, validation_results)
                
                return {
                    'success': True,
                    'event_id': event.event_id,
                    'validators': len(validators),
                    'consensus_score': validation_results['consensus_score'],
                    'reputation_updated': True
                }
            else:
                return {
                    'success': False,
                    'message': 'Validation consensus not reached',
                    'event_id': event.event_id,
                    'consensus_score': validation_results['consensus_score']
                }
                
        except Exception as e:
            logger.error(f"Failed to submit reputation event: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_reputation_event(self, event: ReputationEvent) -> bool:
        """Validate a reputation event"""
        if not (-1.0 <= event.impact <= 1.0):
            return False
        
        if event.timestamp > time.time():
            return False
        
        if not event.evidence:
            return False
        
        return True
    
    def _select_validators_for_event(self, event: ReputationEvent) -> List[ReputationValidator]:
        """Select appropriate validators for a reputation event"""
        suitable_validators = []
        
        for validator in self.validators.values():
            if not validator.is_active:
                continue
            
            # Check if validator has sufficient stake
            if validator.stake_amount < self.validator_stake_requirement:
                continue
            
            # Check if validator has relevant expertise
            event_dimension = self._event_to_dimension(event.event_type)
            if event_dimension and event_dimension in validator.expertise_areas:
                suitable_validators.append(validator)
            elif not event_dimension:  # General event, any validator can handle
                suitable_validators.append(validator)
        
        # Sort by reputation and return top validators
        suitable_validators.sort(key=lambda v: v.own_reputation, reverse=True)
        return suitable_validators[:self.min_validators_required * 2]  # Select more than minimum
    
    def _event_to_dimension(self, event_type: str) -> Optional[ReputationDimension]:
        """Map event type to reputation dimension"""
        mapping = {
            'service_completed': ReputationDimension.RELIABILITY,
            'quality_feedback': ReputationDimension.TECHNICAL_QUALITY,
            'collaboration_feedback': ReputationDimension.COOPERATION,
            'innovation_report': ReputationDimension.INNOVATION,
            'response_time_measured': ReputationDimension.RESPONSIVENESS,
            'resource_usage_reported': ReputationDimension.RESOURCE_EFFICIENCY,
            'value_alignment_measured': ReputationDimension.VALUE_ALIGNMENT,
            'honesty_verification': ReputationDimension.HONESTY
        }
        return mapping.get(event_type)
    
    def _conduct_validation(self, event: ReputationEvent, validators: List[ReputationValidator]) -> Dict[str, Any]:
        """Conduct validation of reputation event"""
        # In a real system, this would involve asynchronous validation
        # For simulation, we'll create validation scores based on validator reputation
        
        validations = []
        
        for validator in validators:
            # Simulate validation score based on validator quality and random factor
            base_accuracy = validator.own_reputation
            noise = np.random.normal(0, 0.1)  # Some randomness
            
            # Validator's assessment of the event impact
            assessed_impact = event.impact + noise
            assessed_impact = max(-1.0, min(1.0, assessed_impact))  # Clamp to valid range
            
            confidence = min(base_accuracy + 0.1, 1.0)
            
            validations.append({
                'validator_id': validator.validator_id,
                'assessed_impact': assessed_impact,
                'confidence': confidence,
                'validator_reputation': validator.own_reputation
            })
        
        # Calculate consensus
        if not validations:
            return {'consensus_reached': False, 'consensus_score': 0.0}
        
        # Weighted average based on validator reputation and confidence
        weighted_sum = 0.0
        total_weight = 0.0
        
        for validation in validations:
            weight = validation['confidence'] * validation['validator_reputation']
            weighted_sum += validation['assessed_impact'] * weight
            total_weight += weight
        
        consensus_impact = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Check if consensus is reached (validators mostly agree)
        impact_variance = np.var([v['assessed_impact'] for v in validations])
        consensus_reached = impact_variance < 0.25  # Threshold for agreement
        
        return {
            'consensus_reached': consensus_reached,
            'consensus_score': consensus_impact,
            'impact_variance': impact_variance,
            'validator_count': len(validations),
            'validations': validations
        }
    
    def _apply_reputation_update(self, event: ReputationEvent, validation_results: Dict[str, Any]):
        """Apply reputation update based on validated event"""
        agent_id = event.agent_id
        consensus_impact = validation_results['consensus_score']
        
        # Get current reputation
        reputation = self.reputation_scores[agent_id]
        
        # Determine which dimension to update
        dimension = self._event_to_dimension(event.event_type)
        if not dimension:
            # If no specific dimension, update based on overall impact
            dimension = ReputationDimension.TECHNICAL_QUALITY  # Default
        
        # Calculate update magnitude based on confidence and evidence
        validator_confidence = np.mean([v['confidence'] for v in validation_results['validations']])
        
        # Apply temporal decay to existing score
        time_since_update = time.time() - reputation.last_updated
        decay_factor = math.exp(-self.decay_rate * time_since_update)
        
        current_score = reputation.dimensions[dimension] * decay_factor
        
        # Calculate new score using exponential moving average
        learning_rate = min(0.1 + (validator_confidence * 0.1), 0.3)
        new_score = current_score * (1 - learning_rate) + (consensus_impact + 1) / 2 * learning_rate
        new_score = max(0.0, min(1.0, new_score))
        
        # Update dimension score
        reputation.dimensions[dimension] = new_score
        
        # Recalculate overall score
        reputation.overall_score = self._calculate_overall_score(reputation.dimensions)
        
        # Update metadata
        reputation.evidence_count += 1
        reputation.confidence = min(reputation.confidence + validator_confidence * 0.05, 1.0)
        reputation.last_updated = time.time()
        
        self.log_event('reputation_updated', agent_id, {
            'dimension': dimension.value,
            'old_score': current_score,
            'new_score': new_score,
            'overall_score': reputation.overall_score,
            'consensus_impact': consensus_impact
        })
    
    def _calculate_overall_score(self, dimensions: Dict[ReputationDimension, float]) -> float:
        """Calculate weighted overall reputation score"""
        weighted_sum = 0.0
        total_weight = 0.0
        
        for dimension, score in dimensions.items():
            weight = self.dimension_weights.get(dimension, 1.0 / len(ReputationDimension))
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.5
    
    def register_validator(self, validator: ReputationValidator) -> bool:
        """Register a new reputation validator"""
        try:
            # Validate stake requirement
            if validator.stake_amount < self.validator_stake_requirement:
                raise ReputationError(
                    f"Insufficient stake. Required: {self.validator_stake_requirement}, "
                    f"Provided: {validator.stake_amount}"
                )
            
            self.validators[validator.validator_id] = validator
            
            self.log_event('validator_registered', validator.validator_id, {
                'validator_type': validator.validator_type,
                'expertise_areas': [area.value for area in validator.expertise_areas],
                'stake_amount': str(validator.stake_amount)
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register validator {validator.validator_id}: {e}")
            return False
    
    def update_trust_relationship(self, truster_id: str, trustee_id: str, 
                                trust_score: float, trust_category: str,
                                evidence_event_id: str = None) -> bool:
        """Update trust relationship between two agents"""
        try:
            if not (0.0 <= trust_score <= 1.0):
                raise InvalidReputationScoreError("Trust score must be between 0.0 and 1.0")
            
            relationship_key = (truster_id, trustee_id)
            current_time = time.time()
            
            if relationship_key in self.trust_relationships:
                # Update existing relationship
                relationship = self.trust_relationships[relationship_key]
                
                # Exponential moving average for trust score update
                alpha = 0.2  # Learning rate
                relationship.trust_score = (1 - alpha) * relationship.trust_score + alpha * trust_score
                relationship.last_updated = current_time
                
                if evidence_event_id:
                    relationship.evidence_events.append(evidence_event_id)
            else:
                # Create new relationship
                relationship = TrustRelationship(
                    truster_id=truster_id,
                    trustee_id=trustee_id,
                    trust_score=trust_score,
                    trust_category=trust_category,
                    evidence_events=[evidence_event_id] if evidence_event_id else [],
                    created_at=current_time,
                    last_updated=current_time
                )
                self.trust_relationships[relationship_key] = relationship
            
            # Update trust network
            if truster_id not in self.trust_network:
                self.trust_network[truster_id] = {}
            self.trust_network[truster_id][trustee_id] = relationship.trust_score
            
            self.log_event('trust_relationship_updated', truster_id, {
                'trustee_id': trustee_id,
                'trust_score': relationship.trust_score,
                'trust_category': trust_category
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update trust relationship: {e}")
            return False
    
    def calculate_transitive_trust(self, source_id: str, target_id: str, max_depth: int = None) -> float:
        """Calculate transitive trust through the trust network"""
        if max_depth is None:
            max_depth = self.trust_propagation_depth
        
        if source_id == target_id:
            return 1.0
        
        # Direct trust
        if source_id in self.trust_network and target_id in self.trust_network[source_id]:
            return self.trust_network[source_id][target_id]
        
        if max_depth <= 1:
            return 0.0  # No path found within depth limit
        
        # BFS for transitive trust calculation
        visited = set()
        queue = [(source_id, 1.0, 0)]  # (node, trust_so_far, depth)
        max_trust = 0.0
        
        while queue:
            current_node, current_trust, depth = queue.pop(0)
            
            if current_node in visited or depth >= max_depth:
                continue
            
            visited.add(current_node)
            
            if current_node not in self.trust_network:
                continue
            
            for neighbor, direct_trust in self.trust_network[current_node].items():
                if neighbor == target_id:
                    # Found path to target
                    transitive_trust = current_trust * direct_trust * (0.9 ** depth)  # Decay with distance
                    max_trust = max(max_trust, transitive_trust)
                elif neighbor not in visited:
                    # Continue searching
                    new_trust = current_trust * direct_trust * (0.9 ** depth)
                    if new_trust > 0.1:  # Only continue if trust is still meaningful
                        queue.append((neighbor, new_trust, depth + 1))
        
        return max_trust
    
    def get_agent_reputation(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive reputation information for an agent"""
        if agent_id not in self.reputation_scores:
            return None
        
        reputation = self.reputation_scores[agent_id]
        
        # Get trust relationships
        trust_as_truster = {
            trustee: rel.trust_score 
            for (truster, trustee), rel in self.trust_relationships.items()
            if truster == agent_id
        }
        
        trust_as_trustee = {
            truster: rel.trust_score
            for (truster, trustee), rel in self.trust_relationships.items()
            if trustee == agent_id
        }
        
        # Calculate trust metrics
        avg_given_trust = sum(trust_as_truster.values()) / len(trust_as_truster) if trust_as_truster else 0.0
        avg_received_trust = sum(trust_as_trustee.values()) / len(trust_as_trustee) if trust_as_trustee else 0.0
        
        return {
            'agent_id': agent_id,
            'overall_reputation': reputation.overall_score,
            'reputation_dimensions': {dim.value: score for dim, score in reputation.dimensions.items()},
            'confidence': reputation.confidence,
            'evidence_count': reputation.evidence_count,
            'last_updated': reputation.last_updated,
            'trust_relationships': {
                'given_trust': trust_as_truster,
                'received_trust': trust_as_trustee,
                'avg_given_trust': avg_given_trust,
                'avg_received_trust': avg_received_trust,
                'trust_network_size': len(trust_as_truster) + len(trust_as_trustee)
            }
        }
    
    def get_trust_score(self, truster_id: str, trustee_id: str, include_transitive: bool = True) -> float:
        """Get trust score between two agents"""
        # Direct trust
        relationship_key = (truster_id, trustee_id)
        if relationship_key in self.trust_relationships:
            direct_trust = self.trust_relationships[relationship_key].trust_score
        else:
            direct_trust = 0.0
        
        if not include_transitive:
            return direct_trust
        
        # Combine direct and transitive trust
        transitive_trust = self.calculate_transitive_trust(truster_id, trustee_id)
        
        # Weighted combination (prefer direct trust)
        combined_trust = 0.7 * direct_trust + 0.3 * transitive_trust
        return combined_trust
    
    def check_trust_threshold(self, agent_id: str, threshold: float) -> bool:
        """Check if agent meets minimum trust threshold"""
        if agent_id not in self.reputation_scores:
            return False
        
        reputation = self.reputation_scores[agent_id]
        return reputation.overall_score >= threshold
    
    def get_system_reputation_metrics(self) -> Dict[str, Any]:
        """Get system-wide reputation metrics"""
        if not self.reputation_scores:
            return {}
        
        all_scores = [rep.overall_score for rep in self.reputation_scores.values()]
        dimension_scores = {dim: [] for dim in ReputationDimension}
        
        for reputation in self.reputation_scores.values():
            for dim, score in reputation.dimensions.items():
                dimension_scores[dim].append(score)
        
        return {
            'total_agents': len(self.reputation_scores),
            'overall_reputation': {
                'mean': sum(all_scores) / len(all_scores),
                'median': sorted(all_scores)[len(all_scores) // 2],
                'min': min(all_scores),
                'max': max(all_scores),
                'std': np.std(all_scores)
            },
            'dimension_statistics': {
                dim.value: {
                    'mean': sum(scores) / len(scores) if scores else 0,
                    'std': np.std(scores) if scores else 0
                }
                for dim, scores in dimension_scores.items()
            },
            'trust_network': {
                'total_relationships': len(self.trust_relationships),
                'network_density': self._calculate_network_density(),
                'avg_trust_score': self._calculate_average_trust()
            },
            'validators': {
                'total_validators': len(self.validators),
                'active_validators': len([v for v in self.validators.values() if v.is_active])
            },
            'events_processed': len(self.reputation_events)
        }
    
    def _calculate_network_density(self) -> float:
        """Calculate trust network density"""
        total_agents = len(self.reputation_scores)
        if total_agents <= 1:
            return 0.0
        
        max_possible_edges = total_agents * (total_agents - 1)
        actual_edges = len(self.trust_relationships)
        
        return actual_edges / max_possible_edges if max_possible_edges > 0 else 0.0
    
    def _calculate_average_trust(self) -> float:
        """Calculate average trust score across all relationships"""
        if not self.trust_relationships:
            return 0.0
        
        total_trust = sum(rel.trust_score for rel in self.trust_relationships.values())
        return total_trust / len(self.trust_relationships)
    
    def _process_reputation_update(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process reputation update event"""
        data = event.data
        try:
            reputation_event = ReputationEvent(
                event_id=data.get('event_id'),
                agent_id=event.agent_id,
                event_type=data['event_type'],
                impact=data['impact'],
                validator_id=data.get('validator_id'),
                evidence=data.get('evidence', {}),
                timestamp=time.time()
            )
            
            return self.submit_reputation_event(reputation_event)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_trust_update(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process trust relationship update event"""
        data = event.data
        try:
            success = self.update_trust_relationship(
                truster_id=event.agent_id,
                trustee_id=data['trustee_id'],
                trust_score=data['trust_score'],
                trust_category=data['trust_category'],
                evidence_event_id=data.get('evidence_event_id')
            )
            return {'success': success}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_validator_registration(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process validator registration event"""
        data = event.data
        try:
            validator = ReputationValidator(
                validator_id=event.agent_id,
                validator_type=data['validator_type'],
                expertise_areas=[ReputationDimension(area) for area in data['expertise_areas']],
                validation_history=[],
                own_reputation=data.get('own_reputation', 0.5),
                stake_amount=Decimal(str(data['stake_amount']))
            )
            
            success = self.register_validator(validator)
            return {'success': success}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_reputation_validation(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process reputation validation event"""
        # This would be called when a validator submits validation results
        return {'success': True, 'message': 'Validation processing not yet implemented'}
    
    def _process_trust_calculation(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process trust score calculation event"""
        data = event.data
        try:
            trust_score = self.get_trust_score(
                truster_id=event.agent_id,
                trustee_id=data['trustee_id'],
                include_transitive=data.get('include_transitive', True)
            )
            return {'success': True, 'trust_score': trust_score}
        except Exception as e:
            return {'success': False, 'error': str(e)}