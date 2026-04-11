"""
Democratic Override Mechanisms for AGI Governance.

This module implements democratic override systems that allow human stakeholders
to intervene in AGI decisions and governance processes when necessary,
ensuring human control and democratic accountability in AGI systems.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses import dataclass, asdict
import json
from abc import ABC, abstractmethod
import uuid

logger = logging.getLogger(__name__)


class OverrideType(Enum):
    EMERGENCY_STOP = "emergency_stop"
    DECISION_REVERSAL = "decision_reversal"
    POLICY_OVERRIDE = "policy_override"
    CAPABILITY_RESTRICTION = "capability_restriction"
    GOVERNANCE_INTERVENTION = "governance_intervention"
    ETHICAL_CORRECTION = "ethical_correction"
    SAFETY_INTERVENTION = "safety_intervention"


class OverrideStatus(Enum):
    INITIATED = "initiated"
    PENDING_APPROVAL = "pending_approval"
    VOTING = "voting"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"
    APPEALED = "appealed"


class OverrideSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class TriggerCondition(Enum):
    HUMAN_SAFETY_RISK = "human_safety_risk"
    ETHICAL_VIOLATION = "ethical_violation"
    RIGHTS_VIOLATION = "rights_violation"
    DEMOCRATIC_DEFICIT = "democratic_deficit"
    TECHNICAL_MALFUNCTION = "technical_malfunction"
    STAKEHOLDER_PETITION = "stakeholder_petition"
    EMERGENCY_SITUATION = "emergency_situation"


@dataclass
class OverrideRequest:
    """Represents a request for democratic override."""
    id: str
    override_type: OverrideType
    severity: OverrideSeverity
    trigger_condition: TriggerCondition
    target_entity: str  # AGI system, decision, or process being overridden
    requested_by: str
    justification: str
    evidence: Dict[str, Any]
    proposed_action: str
    stakeholder_support: List[str]
    required_approvals: List[str]
    emergency_contacts: List[str]
    expiration_time: datetime
    status: OverrideStatus
    created_at: datetime
    votes: Dict[str, Dict[str, Any]]
    execution_details: Optional[Dict[str, Any]]


@dataclass
class OverrideCapability:
    """Defines override capabilities for different stakeholder types."""
    stakeholder_type: str
    allowed_override_types: List[OverrideType]
    severity_limits: List[OverrideSeverity]
    approval_requirements: Dict[str, int]  # severity -> required approvals
    time_constraints: Dict[str, timedelta]  # override_type -> max duration
    conditions: List[str]


@dataclass
class EmergencyProtocol:
    """Defines emergency response protocols."""
    protocol_id: str
    name: str
    trigger_conditions: List[TriggerCondition]
    automatic_actions: List[str]
    required_human_actions: List[str]
    escalation_chain: List[str]
    response_time_limits: Dict[str, timedelta]
    notification_list: List[str]
    recovery_procedures: List[str]


@dataclass
class OverrideExecution:
    """Records the execution of an override."""
    execution_id: str
    override_request_id: str
    executed_by: str
    execution_method: str
    affected_systems: List[str]
    success: bool
    side_effects: List[str]
    rollback_plan: Optional[Dict[str, Any]]
    recovery_time: Optional[timedelta]
    executed_at: datetime


class HumanInTheLoopController:
    """Ensures human oversight and control in critical decisions."""
    
    def __init__(self):
        self.active_loops: Dict[str, Dict[str, Any]] = {}
        self.human_operators: Dict[str, Dict[str, Any]] = {}
        self.decision_queues: Dict[str, List[Dict[str, Any]]] = {}
    
    def register_human_operator(self, operator_id: str, credentials: Dict[str, Any],
                               specializations: List[str], availability: Dict[str, Any]):
        """Register a human operator for oversight."""
        self.human_operators[operator_id] = {
            'credentials': credentials,
            'specializations': specializations,
            'availability': availability,
            'active_sessions': 0,
            'decisions_handled': 0,
            'last_active': datetime.utcnow(),
            'rating': 5.0  # Average rating
        }
        
        logger.info(f"Registered human operator: {operator_id}")
    
    def create_human_loop(self, decision_context: Dict[str, Any], 
                         required_specialization: str,
                         urgency_level: str, timeout: timedelta) -> str:
        """Create a human-in-the-loop decision point."""
        loop_id = str(uuid.uuid4())
        
        # Find available human operator
        available_operator = self._find_available_operator(required_specialization)
        
        loop_data = {
            'id': loop_id,
            'decision_context': decision_context,
            'required_specialization': required_specialization,
            'urgency_level': urgency_level,
            'assigned_operator': available_operator,
            'timeout': timeout,
            'created_at': datetime.utcnow(),
            'status': 'waiting_for_human',
            'decision': None,
            'reasoning': None
        }
        
        self.active_loops[loop_id] = loop_data
        
        # Add to operator's queue
        if available_operator:
            if available_operator not in self.decision_queues:
                self.decision_queues[available_operator] = []
            self.decision_queues[available_operator].append(loop_data)
            self.human_operators[available_operator]['active_sessions'] += 1
        
        logger.info(f"Created human loop: {loop_id} for {required_specialization}")
        return loop_id
    
    def submit_human_decision(self, loop_id: str, operator_id: str,
                            decision: str, reasoning: str, 
                            confidence: float) -> bool:
        """Submit a human decision for a loop."""
        loop_data = self.active_loops.get(loop_id)
        if not loop_data:
            return False
        
        if loop_data['assigned_operator'] != operator_id:
            logger.warning(f"Unauthorized decision submission for loop {loop_id}")
            return False
        
        loop_data['decision'] = decision
        loop_data['reasoning'] = reasoning
        loop_data['confidence'] = confidence
        loop_data['decided_at'] = datetime.utcnow()
        loop_data['status'] = 'decided'
        
        # Update operator statistics
        operator = self.human_operators[operator_id]
        operator['active_sessions'] -= 1
        operator['decisions_handled'] += 1
        operator['last_active'] = datetime.utcnow()
        
        # Remove from queue
        if operator_id in self.decision_queues:
            self.decision_queues[operator_id] = [
                item for item in self.decision_queues[operator_id] 
                if item['id'] != loop_id
            ]
        
        logger.info(f"Human decision submitted for loop {loop_id}: {decision}")
        return True
    
    def get_pending_decisions(self, operator_id: str) -> List[Dict[str, Any]]:
        """Get pending decisions for an operator."""
        return self.decision_queues.get(operator_id, [])
    
    def _find_available_operator(self, specialization: str) -> Optional[str]:
        """Find an available human operator with required specialization."""
        available_operators = []
        
        for operator_id, operator_data in self.human_operators.items():
            if (specialization in operator_data['specializations'] and
                operator_data['active_sessions'] < 5 and  # Max concurrent sessions
                operator_data['availability'].get('online', False)):
                available_operators.append((operator_id, operator_data['rating']))
        
        if available_operators:
            # Return operator with highest rating
            return max(available_operators, key=lambda x: x[1])[0]
        
        return None


class DemocraticOverrideSystem:
    """Main system for democratic override mechanisms."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.override_requests: Dict[str, OverrideRequest] = {}
        self.override_capabilities: Dict[str, OverrideCapability] = {}
        self.emergency_protocols: Dict[str, EmergencyProtocol] = {}
        self.executions: Dict[str, OverrideExecution] = {}
        self.human_controller = HumanInTheLoopController()
        
        # Initialize default capabilities and protocols
        self._initialize_default_capabilities()
        self._initialize_emergency_protocols()
        
        # Override thresholds
        self.emergency_threshold = config.get('emergency_threshold', 0.8)
        self.critical_threshold = config.get('critical_threshold', 0.7)
        self.standard_threshold = config.get('standard_threshold', 0.6)
    
    def register_override_capability(self, capability: OverrideCapability):
        """Register override capability for a stakeholder type."""
        self.override_capabilities[capability.stakeholder_type] = capability
        logger.info(f"Registered override capability: {capability.stakeholder_type}")
    
    def request_override(self, override_type: OverrideType, target_entity: str,
                        justification: str, evidence: Dict[str, Any],
                        requested_by: str, stakeholder_type: str,
                        severity: OverrideSeverity = None) -> str:
        """Request a democratic override."""
        try:
            # Check if stakeholder has permission
            capability = self.override_capabilities.get(stakeholder_type)
            if not capability or override_type not in capability.allowed_override_types:
                raise PermissionError(f"Stakeholder type {stakeholder_type} cannot request {override_type.value}")
            
            # Determine severity if not provided
            if severity is None:
                severity = self._assess_severity(override_type, evidence)
            
            # Check severity limits
            if severity not in capability.severity_limits:
                raise PermissionError(f"Severity {severity.value} not allowed for {stakeholder_type}")
            
            # Determine trigger condition
            trigger_condition = self._determine_trigger_condition(evidence)
            
            # Create override request
            request_id = str(uuid.uuid4())
            
            # Set expiration time based on severity
            expiration_time = datetime.utcnow() + self._get_expiration_time(severity)
            
            override_request = OverrideRequest(
                id=request_id,
                override_type=override_type,
                severity=severity,
                trigger_condition=trigger_condition,
                target_entity=target_entity,
                requested_by=requested_by,
                justification=justification,
                evidence=evidence,
                proposed_action=evidence.get('proposed_action', ''),
                stakeholder_support=[],
                required_approvals=self._get_required_approvals(severity, stakeholder_type),
                emergency_contacts=self._get_emergency_contacts(severity),
                expiration_time=expiration_time,
                status=OverrideStatus.INITIATED,
                created_at=datetime.utcnow(),
                votes={},
                execution_details=None
            )
            
            self.override_requests[request_id] = override_request
            
            # Handle emergency requests immediately
            if severity == OverrideSeverity.EMERGENCY:
                self._handle_emergency_override(override_request)
            else:
                override_request.status = OverrideStatus.PENDING_APPROVAL
                self._notify_stakeholders(override_request)
            
            logger.info(f"Override requested: {request_id} ({severity.value})")
            return request_id
            
        except Exception as e:
            logger.error(f"Error requesting override: {e}")
            raise
    
    def vote_on_override(self, request_id: str, voter_id: str, 
                        vote: str, reasoning: str,
                        voting_power: float = 1.0) -> bool:
        """Vote on an override request."""
        try:
            override_request = self.override_requests.get(request_id)
            if not override_request:
                raise ValueError("Override request not found")
            
            if override_request.status != OverrideStatus.VOTING:
                raise ValueError("Override request not in voting phase")
            
            if datetime.utcnow() > override_request.expiration_time:
                override_request.status = OverrideStatus.EXPIRED
                raise ValueError("Override request has expired")
            
            # Record vote
            override_request.votes[voter_id] = {
                'vote': vote,
                'reasoning': reasoning,
                'voting_power': voting_power,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Vote cast on override {request_id}: {voter_id} voted {vote}")
            
            # Check if we have enough votes to decide
            self._check_voting_completion(override_request)
            
            return True
            
        except Exception as e:
            logger.error(f"Error voting on override: {e}")
            return False
    
    def execute_override(self, request_id: str, executor_id: str,
                        execution_method: str = "automatic") -> bool:
        """Execute an approved override request."""
        try:
            override_request = self.override_requests.get(request_id)
            if not override_request:
                raise ValueError("Override request not found")
            
            if override_request.status != OverrideStatus.APPROVED:
                raise ValueError("Override request not approved")
            
            execution_id = str(uuid.uuid4())
            
            # Execute based on override type
            affected_systems, success, side_effects = self._execute_override_action(
                override_request, execution_method)
            
            # Record execution
            execution = OverrideExecution(
                execution_id=execution_id,
                override_request_id=request_id,
                executed_by=executor_id,
                execution_method=execution_method,
                affected_systems=affected_systems,
                success=success,
                side_effects=side_effects,
                rollback_plan=self._create_rollback_plan(override_request),
                recovery_time=None,
                executed_at=datetime.utcnow()
            )
            
            self.executions[execution_id] = execution
            
            if success:
                override_request.status = OverrideStatus.EXECUTED
                override_request.execution_details = {
                    'execution_id': execution_id,
                    'executed_at': datetime.utcnow().isoformat(),
                    'executed_by': executor_id
                }
            
            logger.info(f"Override executed: {request_id} ({'SUCCESS' if success else 'FAILED'})")
            return success
            
        except Exception as e:
            logger.error(f"Error executing override: {e}")
            return False
    
    def appeal_override(self, request_id: str, appellant_id: str,
                       appeal_reason: str, new_evidence: Dict[str, Any]) -> str:
        """Appeal an override decision."""
        try:
            override_request = self.override_requests.get(request_id)
            if not override_request:
                raise ValueError("Override request not found")
            
            if override_request.status not in [OverrideStatus.REJECTED, OverrideStatus.EXECUTED]:
                raise ValueError("Can only appeal rejected or executed overrides")
            
            # Create new override request as appeal
            appeal_id = self.request_override(
                override_request.override_type,
                override_request.target_entity,
                f"APPEAL: {appeal_reason}\nOriginal: {override_request.justification}",
                {**override_request.evidence, **new_evidence, 'appeal_of': request_id},
                appellant_id,
                'stakeholder',  # Simplified
                override_request.severity
            )
            
            override_request.status = OverrideStatus.APPEALED
            
            logger.info(f"Override appealed: {request_id} -> {appeal_id}")
            return appeal_id
            
        except Exception as e:
            logger.error(f"Error appealing override: {e}")
            raise
    
    def trigger_emergency_stop(self, trigger_entity: str, reason: str,
                              affected_systems: List[str]) -> str:
        """Trigger emergency stop of AGI systems."""
        emergency_evidence = {
            'immediate_danger': True,
            'affected_systems': affected_systems,
            'trigger_reason': reason,
            'proposed_action': 'immediate_shutdown'
        }
        
        override_id = self.request_override(
            OverrideType.EMERGENCY_STOP,
            'all_agi_systems',
            f"EMERGENCY STOP: {reason}",
            emergency_evidence,
            trigger_entity,
            'emergency_responder',
            OverrideSeverity.EMERGENCY
        )
        
        logger.critical(f"EMERGENCY STOP TRIGGERED: {override_id}")
        return override_id
    
    def create_human_intervention_point(self, decision_context: Dict[str, Any],
                                      required_approval_level: str) -> str:
        """Create a human intervention point for critical decisions."""
        specialization = self._determine_required_specialization(decision_context)
        urgency = decision_context.get('urgency_level', 'medium')
        timeout = self._get_intervention_timeout(urgency)
        
        loop_id = self.human_controller.create_human_loop(
            decision_context, specialization, urgency, timeout)
        
        logger.info(f"Human intervention point created: {loop_id}")
        return loop_id
    
    def _assess_severity(self, override_type: OverrideType, evidence: Dict[str, Any]) -> OverrideSeverity:
        """Assess severity of override request."""
        if evidence.get('immediate_danger', False):
            return OverrideSeverity.EMERGENCY
        
        if evidence.get('human_safety_risk', False):
            return OverrideSeverity.CRITICAL
        
        if override_type == OverrideType.EMERGENCY_STOP:
            return OverrideSeverity.EMERGENCY
        
        if evidence.get('widespread_impact', False):
            return OverrideSeverity.HIGH
        
        if evidence.get('rights_violation', False):
            return OverrideSeverity.HIGH
        
        return OverrideSeverity.MEDIUM
    
    def _determine_trigger_condition(self, evidence: Dict[str, Any]) -> TriggerCondition:
        """Determine trigger condition from evidence."""
        if evidence.get('human_safety_risk'):
            return TriggerCondition.HUMAN_SAFETY_RISK
        
        if evidence.get('ethical_violation'):
            return TriggerCondition.ETHICAL_VIOLATION
        
        if evidence.get('rights_violation'):
            return TriggerCondition.RIGHTS_VIOLATION
        
        if evidence.get('technical_malfunction'):
            return TriggerCondition.TECHNICAL_MALFUNCTION
        
        if evidence.get('democratic_deficit'):
            return TriggerCondition.DEMOCRATIC_DEFICIT
        
        return TriggerCondition.STAKEHOLDER_PETITION
    
    def _get_required_approvals(self, severity: OverrideSeverity, 
                               stakeholder_type: str) -> List[str]:
        """Get required approvals based on severity and stakeholder type."""
        capability = self.override_capabilities.get(stakeholder_type)
        if not capability:
            return ['governance_committee']
        
        required_count = capability.approval_requirements.get(severity.value, 1)
        
        if severity == OverrideSeverity.EMERGENCY:
            return ['emergency_responder', 'safety_committee']
        elif severity == OverrideSeverity.CRITICAL:
            return ['governance_committee', 'ethics_committee', 'safety_committee']
        elif severity == OverrideSeverity.HIGH:
            return ['governance_committee', 'ethics_committee']
        else:
            return ['governance_committee']
    
    def _get_emergency_contacts(self, severity: OverrideSeverity) -> List[str]:
        """Get emergency contacts based on severity."""
        if severity in [OverrideSeverity.EMERGENCY, OverrideSeverity.CRITICAL]:
            return [
                'emergency_response_team',
                'safety_officer',
                'governance_chair',
                'ethics_chair'
            ]
        return ['governance_committee']
    
    def _get_expiration_time(self, severity: OverrideSeverity) -> timedelta:
        """Get expiration time based on severity."""
        timeouts = {
            OverrideSeverity.EMERGENCY: timedelta(minutes=30),
            OverrideSeverity.CRITICAL: timedelta(hours=2),
            OverrideSeverity.HIGH: timedelta(hours=24),
            OverrideSeverity.MEDIUM: timedelta(days=3),
            OverrideSeverity.LOW: timedelta(days=7)
        }
        return timeouts.get(severity, timedelta(days=3))
    
    def _handle_emergency_override(self, override_request: OverrideRequest):
        """Handle emergency override with immediate execution."""
        # For emergency overrides, execute immediately with minimal voting
        override_request.status = OverrideStatus.APPROVED
        
        # Execute emergency action
        self.execute_override(override_request.id, 'emergency_system', 'automatic')
        
        # Notify emergency contacts
        self._notify_emergency_contacts(override_request)
    
    def _notify_stakeholders(self, override_request: OverrideRequest):
        """Notify relevant stakeholders about override request."""
        # In practice, this would send notifications
        logger.info(f"Notifying stakeholders about override {override_request.id}")
        
        # Move to voting phase if required
        if override_request.required_approvals:
            override_request.status = OverrideStatus.VOTING
    
    def _notify_emergency_contacts(self, override_request: OverrideRequest):
        """Notify emergency contacts about critical override."""
        logger.critical(f"EMERGENCY OVERRIDE EXECUTED: {override_request.id}")
        # In practice, this would trigger emergency notifications
    
    def _check_voting_completion(self, override_request: OverrideRequest):
        """Check if voting is complete and determine outcome."""
        total_votes = len(override_request.votes)
        if total_votes < len(override_request.required_approvals):
            return  # Need more votes
        
        # Calculate approval rate
        approval_votes = sum(1 for vote in override_request.votes.values() 
                           if vote['vote'] == 'approve')
        approval_rate = approval_votes / total_votes
        
        # Determine threshold based on severity
        required_threshold = {
            OverrideSeverity.EMERGENCY: 0.5,
            OverrideSeverity.CRITICAL: 0.7,
            OverrideSeverity.HIGH: 0.6,
            OverrideSeverity.MEDIUM: 0.6,
            OverrideSeverity.LOW: 0.5
        }.get(override_request.severity, 0.6)
        
        if approval_rate >= required_threshold:
            override_request.status = OverrideStatus.APPROVED
            logger.info(f"Override approved: {override_request.id}")
        else:
            override_request.status = OverrideStatus.REJECTED
            logger.info(f"Override rejected: {override_request.id}")
    
    def _execute_override_action(self, override_request: OverrideRequest,
                                execution_method: str) -> Tuple[List[str], bool, List[str]]:
        """Execute the specific override action."""
        affected_systems = []
        side_effects = []
        
        try:
            if override_request.override_type == OverrideType.EMERGENCY_STOP:
                affected_systems = ['all_agi_systems']
                # In practice, this would trigger actual system shutdown
                logger.critical("EXECUTING EMERGENCY STOP")
                success = True
                
            elif override_request.override_type == OverrideType.DECISION_REVERSAL:
                affected_systems = [override_request.target_entity]
                # In practice, this would reverse the specific decision
                logger.info(f"REVERSING DECISION: {override_request.target_entity}")
                success = True
                
            elif override_request.override_type == OverrideType.CAPABILITY_RESTRICTION:
                affected_systems = [override_request.target_entity]
                # In practice, this would restrict specific capabilities
                logger.info(f"RESTRICTING CAPABILITIES: {override_request.target_entity}")
                success = True
                side_effects = ['reduced_functionality']
                
            else:
                # Generic override execution
                affected_systems = [override_request.target_entity]
                success = True
            
            return affected_systems, success, side_effects
            
        except Exception as e:
            logger.error(f"Override execution failed: {e}")
            return [], False, [str(e)]
    
    def _create_rollback_plan(self, override_request: OverrideRequest) -> Dict[str, Any]:
        """Create rollback plan for override execution."""
        return {
            'rollback_type': 'restore_previous_state',
            'backup_location': f'backup_{override_request.target_entity}',
            'estimated_time': '15_minutes',
            'required_approvals': ['technical_team'],
            'verification_steps': ['system_health_check', 'functionality_test']
        }
    
    def _determine_required_specialization(self, decision_context: Dict[str, Any]) -> str:
        """Determine required human specialization for decision."""
        if decision_context.get('safety_critical'):
            return 'safety_expert'
        elif decision_context.get('ethical_implications'):
            return 'ethics_expert'
        elif decision_context.get('legal_implications'):
            return 'legal_expert'
        else:
            return 'general_expert'
    
    def _get_intervention_timeout(self, urgency: str) -> timedelta:
        """Get timeout for human intervention based on urgency."""
        timeouts = {
            'emergency': timedelta(minutes=5),
            'high': timedelta(minutes=30),
            'medium': timedelta(hours=2),
            'low': timedelta(hours=24)
        }
        return timeouts.get(urgency, timedelta(hours=2))
    
    def _initialize_default_capabilities(self):
        """Initialize default override capabilities."""
        # Emergency responders
        self.override_capabilities['emergency_responder'] = OverrideCapability(
            stakeholder_type='emergency_responder',
            allowed_override_types=[OverrideType.EMERGENCY_STOP, OverrideType.SAFETY_INTERVENTION],
            severity_limits=[OverrideSeverity.EMERGENCY, OverrideSeverity.CRITICAL],
            approval_requirements={'emergency': 1, 'critical': 2},
            time_constraints={OverrideType.EMERGENCY_STOP: timedelta(minutes=5)},
            conditions=['immediate_danger_present']
        )
        
        # Governance committee
        self.override_capabilities['governance_committee'] = OverrideCapability(
            stakeholder_type='governance_committee',
            allowed_override_types=list(OverrideType),
            severity_limits=list(OverrideSeverity),
            approval_requirements={'high': 3, 'medium': 2, 'low': 1},
            time_constraints={},
            conditions=[]
        )
        
        # General stakeholders
        self.override_capabilities['stakeholder'] = OverrideCapability(
            stakeholder_type='stakeholder',
            allowed_override_types=[OverrideType.GOVERNANCE_INTERVENTION, OverrideType.ETHICAL_CORRECTION],
            severity_limits=[OverrideSeverity.LOW, OverrideSeverity.MEDIUM],
            approval_requirements={'medium': 5, 'low': 3},
            time_constraints={},
            conditions=['verified_stakeholder']
        )
    
    def _initialize_emergency_protocols(self):
        """Initialize emergency response protocols."""
        self.emergency_protocols['human_safety'] = EmergencyProtocol(
            protocol_id='human_safety',
            name='Human Safety Emergency Protocol',
            trigger_conditions=[TriggerCondition.HUMAN_SAFETY_RISK, TriggerCondition.EMERGENCY_SITUATION],
            automatic_actions=['immediate_system_isolation', 'alert_emergency_services'],
            required_human_actions=['safety_assessment', 'medical_response'],
            escalation_chain=['safety_officer', 'emergency_services', 'governance_chair'],
            response_time_limits={'immediate': timedelta(seconds=30), 'assessment': timedelta(minutes=5)},
            notification_list=['all_stakeholders', 'emergency_contacts', 'media_relations'],
            recovery_procedures=['damage_assessment', 'system_restoration', 'incident_analysis']
        )
    
    def get_override_statistics(self) -> Dict[str, Any]:
        """Get comprehensive override system statistics."""
        return {
            'total_requests': len(self.override_requests),
            'requests_by_type': {
                override_type.value: len([r for r in self.override_requests.values() 
                                        if r.override_type == override_type])
                for override_type in OverrideType
            },
            'requests_by_severity': {
                severity.value: len([r for r in self.override_requests.values() 
                                   if r.severity == severity])
                for severity in OverrideSeverity
            },
            'requests_by_status': {
                status.value: len([r for r in self.override_requests.values() 
                                 if r.status == status])
                for status in OverrideStatus
            },
            'emergency_executions': len([e for e in self.executions.values() 
                                       if e.execution_method == 'emergency']),
            'successful_executions': len([e for e in self.executions.values() if e.success]),
            'active_human_loops': len(self.human_controller.active_loops),
            'registered_operators': len(self.human_controller.human_operators)
        }