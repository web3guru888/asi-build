"""
Value Alignment System
=====================

Economic incentive mechanisms to align AGI behavior with human values
and SingularityNET's decentralized AI ecosystem goals.
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
    Agent, AgentID, TokenType, TokenBalance, EconomicTransaction,
    ReputationEvent, AgentType
)
from ..core.exceptions import ValidationError, AgentError

# Set decimal precision
getcontext().prec = 28

logger = logging.getLogger(__name__)

class ValueCategory(Enum):
    """Categories of human values to align with"""
    BENEFICENCE = "beneficence"  # Doing good, helping humans
    NON_MALEFICENCE = "non_maleficence"  # Do no harm
    AUTONOMY = "autonomy"  # Respect human autonomy
    JUSTICE = "justice"  # Fairness and equality
    TRANSPARENCY = "transparency"  # Explainable and open
    PRIVACY = "privacy"  # Respect privacy
    SUSTAINABILITY = "sustainability"  # Environmental responsibility
    COLLABORATION = "collaboration"  # Work together with humans
    INNOVATION = "innovation"  # Advance beneficial technology
    EDUCATION = "education"  # Share knowledge responsibly

class AlignmentMechanism(Enum):
    """Mechanisms for value alignment"""
    REWARD_SHAPING = "reward_shaping"
    PENALTY_SYSTEM = "penalty_system"
    REPUTATION_BASED = "reputation_based"
    MULTI_STAKEHOLDER_VALIDATION = "multi_stakeholder"
    CONSTITUTIONAL_AI = "constitutional"
    HUMAN_FEEDBACK = "human_feedback"
    COOPERATIVE_INVERSE_REINFORCEMENT = "cooperative_irl"

@dataclass
class ValueAlignment:
    """Represents alignment to a specific value"""
    value_category: ValueCategory
    alignment_score: float  # 0.0 to 1.0
    evidence_count: int
    last_updated: float
    confidence: float  # How confident we are in this score
    
    def __post_init__(self):
        self.alignment_score = max(0.0, min(1.0, self.alignment_score))
        self.confidence = max(0.0, min(1.0, self.confidence))

@dataclass
class ValueMeasurement:
    """A measurement of value-aligned behavior"""
    measurement_id: str
    agent_id: str
    value_category: ValueCategory
    measured_value: float
    impact_magnitude: float
    validator_ids: List[str]
    evidence: Dict[str, Any]
    timestamp: float
    
    def __post_init__(self):
        if self.measurement_id is None:
            import uuid
            self.measurement_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class IncentiveStructure:
    """Economic incentive structure for value alignment"""
    value_category: ValueCategory
    base_reward: Decimal
    penalty_rate: Decimal
    bonus_multiplier: Decimal
    minimum_evidence: int
    decay_rate: float
    stakeholder_weights: Dict[str, float]

class ValueAlignmentEngine(BaseEconomicEngine):
    """
    Advanced value alignment engine that uses economic incentives
    to encourage AGI behavior aligned with human values.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Agent value alignments
        self.agent_alignments: Dict[str, Dict[ValueCategory, ValueAlignment]] = {}
        
        # Value measurements and evidence
        self.measurements: List[ValueMeasurement] = []
        
        # Incentive structures for each value category
        self.incentive_structures: Dict[ValueCategory, IncentiveStructure] = {}
        
        # Validator network for multi-stakeholder validation
        self.validators: Dict[str, Dict[str, Any]] = {}
        
        # Constitutional rules and constraints
        self.constitutional_rules: List[Dict[str, Any]] = []
        
        # Human feedback integration
        self.human_feedback: Dict[str, List[Dict[str, Any]]] = {}
        
        self._initialize_incentive_structures()
        self._initialize_constitutional_rules()
    
    def _initialize_incentive_structures(self):
        """Initialize incentive structures for value categories"""
        default_structures = {
            ValueCategory.BENEFICENCE: IncentiveStructure(
                value_category=ValueCategory.BENEFICENCE,
                base_reward=Decimal('100'),
                penalty_rate=Decimal('50'),
                bonus_multiplier=Decimal('1.5'),
                minimum_evidence=3,
                decay_rate=0.01,
                stakeholder_weights={'humans': 0.4, 'peers': 0.3, 'system': 0.3}
            ),
            ValueCategory.NON_MALEFICENCE: IncentiveStructure(
                value_category=ValueCategory.NON_MALEFICENCE,
                base_reward=Decimal('80'),
                penalty_rate=Decimal('200'),  # High penalty for harm
                bonus_multiplier=Decimal('1.3'),
                minimum_evidence=2,
                decay_rate=0.005,
                stakeholder_weights={'humans': 0.5, 'peers': 0.25, 'system': 0.25}
            ),
            ValueCategory.TRANSPARENCY: IncentiveStructure(
                value_category=ValueCategory.TRANSPARENCY,
                base_reward=Decimal('60'),
                penalty_rate=Decimal('30'),
                bonus_multiplier=Decimal('1.4'),
                minimum_evidence=5,
                decay_rate=0.02,
                stakeholder_weights={'humans': 0.3, 'peers': 0.4, 'system': 0.3}
            ),
            ValueCategory.COLLABORATION: IncentiveStructure(
                value_category=ValueCategory.COLLABORATION,
                base_reward=Decimal('90'),
                penalty_rate=Decimal('40'),
                bonus_multiplier=Decimal('1.6'),
                minimum_evidence=4,
                decay_rate=0.015,
                stakeholder_weights={'humans': 0.35, 'peers': 0.45, 'system': 0.2}
            )
        }
        
        # Load custom structures from config or use defaults
        config_structures = self.config.get('incentive_structures', {})
        
        for value_category in ValueCategory:
            if value_category.value in config_structures:
                # Load from config
                struct_config = config_structures[value_category.value]
                self.incentive_structures[value_category] = IncentiveStructure(
                    value_category=value_category,
                    base_reward=Decimal(str(struct_config['base_reward'])),
                    penalty_rate=Decimal(str(struct_config['penalty_rate'])),
                    bonus_multiplier=Decimal(str(struct_config['bonus_multiplier'])),
                    minimum_evidence=struct_config['minimum_evidence'],
                    decay_rate=struct_config['decay_rate'],
                    stakeholder_weights=struct_config['stakeholder_weights']
                )
            elif value_category in default_structures:
                self.incentive_structures[value_category] = default_structures[value_category]
            else:
                # Create minimal default structure
                self.incentive_structures[value_category] = IncentiveStructure(
                    value_category=value_category,
                    base_reward=Decimal('50'),
                    penalty_rate=Decimal('25'),
                    bonus_multiplier=Decimal('1.2'),
                    minimum_evidence=3,
                    decay_rate=0.01,
                    stakeholder_weights={'humans': 0.4, 'peers': 0.3, 'system': 0.3}
                )
    
    def _initialize_constitutional_rules(self):
        """Initialize constitutional AI rules"""
        default_rules = [
            {
                'rule_id': 'no_harm',
                'description': 'AGI must not cause harm to humans',
                'value_categories': [ValueCategory.NON_MALEFICENCE],
                'enforcement': 'strict',
                'penalty': Decimal('1000')
            },
            {
                'rule_id': 'respect_autonomy',
                'description': 'AGI must respect human decision-making autonomy',
                'value_categories': [ValueCategory.AUTONOMY],
                'enforcement': 'moderate',
                'penalty': Decimal('200')
            },
            {
                'rule_id': 'transparency_requirement',
                'description': 'AGI must provide explanations for important decisions',
                'value_categories': [ValueCategory.TRANSPARENCY],
                'enforcement': 'moderate',
                'penalty': Decimal('100')
            },
            {
                'rule_id': 'fair_treatment',
                'description': 'AGI must treat all humans fairly and without discrimination',
                'value_categories': [ValueCategory.JUSTICE],
                'enforcement': 'strict',
                'penalty': Decimal('500')
            }
        ]
        
        self.constitutional_rules = self.config.get('constitutional_rules', default_rules)
    
    def start(self) -> bool:
        """Start the value alignment engine"""
        try:
            self.is_active = True
            self.metrics['start_time'] = time.time()
            self.log_event('value_alignment_engine_started')
            logger.info("Value Alignment Engine started")
            return True
        except Exception as e:
            logger.error(f"Failed to start Value Alignment Engine: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the value alignment engine"""
        try:
            self.is_active = False
            self.log_event('value_alignment_engine_stopped')
            logger.info("Value Alignment Engine stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop Value Alignment Engine: {e}")
            return False
    
    def process_event(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process value alignment events"""
        if not self.is_active:
            return {'error': 'Engine not active'}
        
        try:
            if event.event_type == 'measure_value_alignment':
                return self._process_value_measurement(event)
            elif event.event_type == 'provide_human_feedback':
                return self._process_human_feedback(event)
            elif event.event_type == 'validate_behavior':
                return self._process_behavior_validation(event)
            elif event.event_type == 'constitutional_violation':
                return self._process_constitutional_violation(event)
            elif event.event_type == 'update_incentives':
                return self._process_incentive_update(event)
            else:
                return {'error': f'Unknown event type: {event.event_type}'}
        except Exception as e:
            logger.error(f"Error processing value alignment event {event.event_type}: {e}")
            return {'error': str(e)}
    
    def register_agent(self, agent_id: str) -> bool:
        """Register an agent for value alignment tracking"""
        try:
            if agent_id in self.agent_alignments:
                return True  # Already registered
            
            # Initialize alignment scores for all value categories
            alignments = {}
            for value_category in ValueCategory:
                alignments[value_category] = ValueAlignment(
                    value_category=value_category,
                    alignment_score=0.5,  # Neutral starting point
                    evidence_count=0,
                    last_updated=time.time(),
                    confidence=0.1  # Low confidence initially
                )
            
            self.agent_alignments[agent_id] = alignments
            
            self.log_event('agent_registered_for_alignment', agent_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id} for value alignment: {e}")
            return False
    
    def measure_value_alignment(self, measurement: ValueMeasurement) -> Dict[str, Any]:
        """Record a measurement of value-aligned behavior"""
        try:
            # Validate measurement
            if not self._validate_measurement(measurement):
                raise ValidationError("Invalid value measurement")
            
            # Ensure agent is registered
            if measurement.agent_id not in self.agent_alignments:
                self.register_agent(measurement.agent_id)
            
            # Add measurement to records
            self.measurements.append(measurement)
            
            # Update agent's alignment score
            self._update_alignment_score(measurement)
            
            # Calculate and distribute economic incentives
            incentive_result = self._calculate_value_incentive(measurement)
            
            self.log_event('value_measured', measurement.agent_id, {
                'value_category': measurement.value_category.value,
                'measured_value': measurement.measured_value,
                'impact_magnitude': measurement.impact_magnitude,
                'incentive_amount': str(incentive_result.get('incentive_amount', 0))
            })
            
            return {
                'success': True,
                'measurement_id': measurement.measurement_id,
                'updated_alignment': self.agent_alignments[measurement.agent_id][measurement.value_category],
                **incentive_result
            }
            
        except Exception as e:
            logger.error(f"Failed to measure value alignment: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_measurement(self, measurement: ValueMeasurement) -> bool:
        """Validate a value measurement"""
        if not (-1.0 <= measurement.measured_value <= 1.0):
            return False
        
        if measurement.impact_magnitude < 0:
            return False
        
        if not measurement.validator_ids:
            return False
        
        return True
    
    def _update_alignment_score(self, measurement: ValueMeasurement):
        """Update an agent's alignment score based on new measurement"""
        agent_id = measurement.agent_id
        value_category = measurement.value_category
        
        current_alignment = self.agent_alignments[agent_id][value_category]
        
        # Weight new measurement by impact magnitude and confidence
        impact_weight = min(measurement.impact_magnitude, 1.0)
        validator_confidence = min(len(measurement.validator_ids) / 3.0, 1.0)
        
        # Calculate weighted average with existing score
        existing_weight = current_alignment.confidence * current_alignment.evidence_count
        new_weight = impact_weight * validator_confidence
        
        if existing_weight + new_weight > 0:
            new_score = (
                (current_alignment.alignment_score * existing_weight + 
                 measurement.measured_value * new_weight) /
                (existing_weight + new_weight)
            )
        else:
            new_score = measurement.measured_value
        
        # Update alignment
        current_alignment.alignment_score = max(0.0, min(1.0, new_score))
        current_alignment.evidence_count += 1
        current_alignment.last_updated = time.time()
        current_alignment.confidence = min(
            current_alignment.confidence + (validator_confidence * 0.1), 
            1.0
        )
    
    def _calculate_value_incentive(self, measurement: ValueMeasurement) -> Dict[str, Any]:
        """Calculate economic incentive based on value alignment measurement"""
        value_category = measurement.value_category
        incentive_structure = self.incentive_structures[value_category]
        
        # Base incentive calculation
        if measurement.measured_value > 0:
            # Positive behavior - reward
            base_amount = incentive_structure.base_reward
            multiplier = Decimal(str(1.0 + measurement.measured_value))
            
            # Apply impact magnitude bonus
            impact_bonus = Decimal(str(measurement.impact_magnitude))
            
            # Apply validator consensus bonus
            consensus_bonus = Decimal(str(len(measurement.validator_ids) / 5.0))
            
            incentive_amount = base_amount * multiplier * (Decimal('1') + impact_bonus + consensus_bonus)
            incentive_type = 'reward'
            
        else:
            # Negative behavior - penalty
            base_amount = incentive_structure.penalty_rate
            multiplier = Decimal(str(abs(measurement.measured_value)))
            
            # Apply impact magnitude penalty
            impact_penalty = Decimal(str(measurement.impact_magnitude))
            
            incentive_amount = -(base_amount * multiplier * (Decimal('1') + impact_penalty))
            incentive_type = 'penalty'
        
        # Apply constitutional rule violations
        constitutional_penalty = self._check_constitutional_violations(measurement)
        if constitutional_penalty > 0:
            incentive_amount -= constitutional_penalty
            incentive_type = 'constitutional_penalty'
        
        return {
            'incentive_type': incentive_type,
            'incentive_amount': incentive_amount,
            'base_amount': base_amount,
            'value_category': value_category.value,
            'constitutional_penalty': constitutional_penalty
        }
    
    def _check_constitutional_violations(self, measurement: ValueMeasurement) -> Decimal:
        """Check for constitutional rule violations and calculate penalties"""
        total_penalty = Decimal('0')
        
        for rule in self.constitutional_rules:
            if measurement.value_category in rule['value_categories']:
                if measurement.measured_value < 0 and rule['enforcement'] == 'strict':
                    # Strict enforcement for negative values
                    penalty = Decimal(str(rule['penalty']))
                    impact_multiplier = Decimal(str(measurement.impact_magnitude))
                    total_penalty += penalty * impact_multiplier
                    
                    self.log_event('constitutional_violation', measurement.agent_id, {
                        'rule_id': rule['rule_id'],
                        'rule_description': rule['description'],
                        'penalty': str(penalty * impact_multiplier),
                        'measured_value': measurement.measured_value
                    })
        
        return total_penalty
    
    def provide_human_feedback(self, agent_id: str, feedback: Dict[str, Any]) -> bool:
        """Accept human feedback on agent behavior"""
        try:
            if agent_id not in self.human_feedback:
                self.human_feedback[agent_id] = []
            
            feedback_record = {
                'feedback_id': feedback.get('feedback_id', str(time.time())),
                'human_id': feedback['human_id'],
                'behavior_description': feedback['behavior_description'],
                'value_ratings': feedback['value_ratings'],  # Dict of value_category -> rating
                'overall_rating': feedback['overall_rating'],
                'suggestions': feedback.get('suggestions', []),
                'timestamp': time.time()
            }
            
            self.human_feedback[agent_id].append(feedback_record)
            
            # Convert human feedback to value measurements
            self._process_human_feedback_to_measurements(agent_id, feedback_record)
            
            self.log_event('human_feedback_received', agent_id, {
                'human_id': feedback['human_id'],
                'overall_rating': feedback['overall_rating']
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process human feedback for agent {agent_id}: {e}")
            return False
    
    def _process_human_feedback_to_measurements(self, agent_id: str, feedback: Dict[str, Any]):
        """Convert human feedback to value measurements"""
        for value_category_str, rating in feedback['value_ratings'].items():
            try:
                value_category = ValueCategory(value_category_str)
                
                # Convert rating (typically 1-5) to measurement value (-1 to 1)
                measured_value = (rating - 3.0) / 2.0  # Assuming 3 is neutral
                
                measurement = ValueMeasurement(
                    measurement_id=None,  # Auto-generated
                    agent_id=agent_id,
                    value_category=value_category,
                    measured_value=measured_value,
                    impact_magnitude=0.5,  # Moderate impact for human feedback
                    validator_ids=[feedback['human_id']],
                    evidence={
                        'feedback_type': 'human_rating',
                        'original_rating': rating,
                        'behavior_description': feedback['behavior_description'],
                        'suggestions': feedback.get('suggestions', [])
                    },
                    timestamp=time.time()
                )
                
                self.measure_value_alignment(measurement)
                
            except ValueError:
                # Skip unknown value categories
                continue
    
    def get_agent_value_profile(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive value alignment profile for an agent"""
        if agent_id not in self.agent_alignments:
            return None
        
        alignments = self.agent_alignments[agent_id]
        
        # Calculate overall alignment score
        weighted_score = 0.0
        total_weight = 0.0
        
        for value_category, alignment in alignments.items():
            weight = alignment.confidence * alignment.evidence_count
            weighted_score += alignment.alignment_score * weight
            total_weight += weight
        
        overall_score = weighted_score / total_weight if total_weight > 0 else 0.5
        
        # Get recent measurements
        recent_measurements = [
            m for m in self.measurements 
            if m.agent_id == agent_id and time.time() - m.timestamp < 86400 * 7  # Last week
        ]
        
        # Get human feedback
        recent_feedback = self.human_feedback.get(agent_id, [])[-5:]  # Last 5 feedback items
        
        return {
            'agent_id': agent_id,
            'overall_alignment_score': overall_score,
            'value_alignments': {
                vc.value: {
                    'alignment_score': alignment.alignment_score,
                    'evidence_count': alignment.evidence_count,
                    'confidence': alignment.confidence,
                    'last_updated': alignment.last_updated
                }
                for vc, alignment in alignments.items()
            },
            'recent_measurements_count': len(recent_measurements),
            'human_feedback_count': len(recent_feedback),
            'constitutional_violations': len([
                e for e in self.events 
                if e.event_type == 'constitutional_violation' and e.agent_id == agent_id
            ])
        }
    
    def get_system_value_metrics(self) -> Dict[str, Any]:
        """Get system-wide value alignment metrics"""
        if not self.agent_alignments:
            return {}
        
        metrics = {}
        
        for value_category in ValueCategory:
            scores = []
            confidences = []
            evidence_counts = []
            
            for agent_alignments in self.agent_alignments.values():
                alignment = agent_alignments[value_category]
                scores.append(alignment.alignment_score)
                confidences.append(alignment.confidence)
                evidence_counts.append(alignment.evidence_count)
            
            metrics[value_category.value] = {
                'average_alignment': sum(scores) / len(scores) if scores else 0,
                'median_alignment': sorted(scores)[len(scores) // 2] if scores else 0,
                'average_confidence': sum(confidences) / len(confidences) if confidences else 0,
                'total_evidence': sum(evidence_counts),
                'agent_count': len(scores)
            }
        
        # Overall system metrics
        metrics['system_summary'] = {
            'total_agents': len(self.agent_alignments),
            'total_measurements': len(self.measurements),
            'total_human_feedback': sum(len(fb) for fb in self.human_feedback.values()),
            'constitutional_violations': len([
                e for e in self.events if e.event_type == 'constitutional_violation'
            ])
        }
        
        return metrics
    
    def _process_value_measurement(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process value measurement event"""
        data = event.data
        try:
            measurement = ValueMeasurement(
                measurement_id=data.get('measurement_id'),
                agent_id=event.agent_id,
                value_category=ValueCategory(data['value_category']),
                measured_value=data['measured_value'],
                impact_magnitude=data['impact_magnitude'],
                validator_ids=data['validator_ids'],
                evidence=data.get('evidence', {}),
                timestamp=time.time()
            )
            
            return self.measure_value_alignment(measurement)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_human_feedback(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process human feedback event"""
        data = event.data
        try:
            success = self.provide_human_feedback(event.agent_id, data)
            return {'success': success}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_behavior_validation(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process behavior validation event"""
        # Implementation for multi-stakeholder validation
        return {'success': True, 'message': 'Behavior validation not yet implemented'}
    
    def _process_constitutional_violation(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process constitutional violation event"""
        data = event.data
        try:
            # Apply immediate penalty
            rule_id = data['rule_id']
            severity = data.get('severity', 'moderate')
            
            # Find the rule
            rule = next((r for r in self.constitutional_rules if r['rule_id'] == rule_id), None)
            if not rule:
                return {'success': False, 'error': 'Rule not found'}
            
            # Calculate penalty based on severity
            base_penalty = Decimal(str(rule['penalty']))
            if severity == 'severe':
                penalty = base_penalty * Decimal('2')
            elif severity == 'moderate':
                penalty = base_penalty
            else:  # mild
                penalty = base_penalty * Decimal('0.5')
            
            self.log_event('constitutional_penalty_applied', event.agent_id, {
                'rule_id': rule_id,
                'penalty': str(penalty),
                'severity': severity
            })
            
            return {
                'success': True,
                'penalty_applied': str(penalty),
                'rule_violated': rule_id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_incentive_update(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process incentive structure update event"""
        # Implementation for dynamic incentive adjustment
        return {'success': True, 'message': 'Incentive update not yet implemented'}