"""
Rights Management System for AGI Entities and Stakeholders.

This module implements a comprehensive rights framework that protects both
human rights and establishes rights for AGI entities, ensuring ethical
treatment and autonomy preservation in AGI governance systems.
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class EntityType(Enum):
    HUMAN = "human"
    AGI_SYSTEM = "agi_system"
    ORGANIZATION = "organization"
    COLLECTIVE = "collective"
    HYBRID = "hybrid"  # Human-AGI hybrid entities


class RightType(Enum):
    FUNDAMENTAL = "fundamental"
    PROCEDURAL = "procedural"
    SUBSTANTIVE = "substantive"
    COLLECTIVE = "collective"
    EMERGENT = "emergent"  # Rights that emerge as entities evolve


class RightStatus(Enum):
    GRANTED = "granted"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PENDING = "pending"
    DISPUTED = "disputed"


class ConsentType(Enum):
    EXPLICIT = "explicit"
    IMPLIED = "implied"
    INFORMED = "informed"
    ONGOING = "ongoing"
    REVOKED = "revoked"


@dataclass
class Right:
    """Represents a specific right in the system."""

    id: str
    name: str
    description: str
    right_type: RightType
    applicable_entities: List[EntityType]
    enforcement_mechanisms: List[str]
    violation_consequences: List[str]
    dependencies: List[str]  # Other rights this depends on
    conflicts: List[str]  # Rights that may conflict with this
    created_at: datetime
    updated_at: datetime


@dataclass
class ConsentRecord:
    """Records consent given by an entity."""

    id: str
    entity_id: str
    purpose: str
    scope: str
    consent_type: ConsentType
    granular_permissions: Dict[str, bool]
    expiration: Optional[datetime]
    revocation_mechanism: str
    given_at: datetime
    revoked_at: Optional[datetime]
    context: Dict[str, Any]


@dataclass
class RightGrant:
    """Represents a right granted to an entity."""

    id: str
    entity_id: str
    right_id: str
    status: RightStatus
    granted_by: str
    granted_at: datetime
    valid_until: Optional[datetime]
    conditions: List[str]
    exercise_count: int
    last_exercised: Optional[datetime]
    restrictions: Dict[str, Any]


@dataclass
class Entity:
    """Represents an entity in the rights system."""

    id: str
    name: str
    entity_type: EntityType
    capabilities: List[str]
    consciousness_level: Optional[float]  # For AGI entities
    autonomy_level: Optional[float]  # Measure of decision-making autonomy
    rights_granted: List[str]  # Right IDs
    consent_records: List[str]  # Consent record IDs
    guardian_id: Optional[str]  # For entities requiring guardianship
    creation_date: datetime
    last_assessment: Optional[datetime]
    metadata: Dict[str, Any]


@dataclass
class RightViolation:
    """Records a violation of rights."""

    id: str
    violated_right_id: str
    affected_entity_id: str
    violating_entity_id: Optional[str]
    violation_type: str
    severity: str  # low, medium, high, critical
    evidence: Dict[str, Any]
    reported_at: datetime
    reported_by: str
    investigation_status: str
    resolution: Optional[Dict[str, Any]]
    remediation_actions: List[str]


class RightsFramework(ABC):
    """Abstract base class for different rights frameworks."""

    @abstractmethod
    def define_fundamental_rights(self) -> List[Right]:
        """Define fundamental rights for this framework."""
        pass

    @abstractmethod
    def assess_right_applicability(self, entity: Entity, right: Right) -> bool:
        """Assess if a right applies to an entity."""
        pass

    @abstractmethod
    def resolve_conflicts(
        self, conflicting_rights: List[Right], context: Dict[str, Any]
    ) -> List[Right]:
        """Resolve conflicts between rights."""
        pass


class HumanRightsFramework(RightsFramework):
    """Implements human rights framework based on international standards."""

    def define_fundamental_rights(self) -> List[Right]:
        """Define fundamental human rights."""
        rights = []

        # Life and Liberty
        rights.append(
            Right(
                id="human_right_life",
                name="Right to Life",
                description="The fundamental right to life and personal security",
                right_type=RightType.FUNDAMENTAL,
                applicable_entities=[EntityType.HUMAN],
                enforcement_mechanisms=["legal_protection", "emergency_intervention"],
                violation_consequences=["criminal_liability", "immediate_protection"],
                dependencies=[],
                conflicts=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        # Privacy and Data Protection
        rights.append(
            Right(
                id="human_right_privacy",
                name="Right to Privacy",
                description="Right to privacy and protection of personal data",
                right_type=RightType.FUNDAMENTAL,
                applicable_entities=[EntityType.HUMAN],
                enforcement_mechanisms=[
                    "data_encryption",
                    "access_controls",
                    "consent_verification",
                ],
                violation_consequences=["data_deletion", "compensation", "system_modification"],
                dependencies=[],
                conflicts=["transparency_obligations"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        # Autonomy and Self-Determination
        rights.append(
            Right(
                id="human_right_autonomy",
                name="Right to Autonomy",
                description="Right to make autonomous decisions about one's life",
                right_type=RightType.FUNDAMENTAL,
                applicable_entities=[EntityType.HUMAN],
                enforcement_mechanisms=["informed_consent", "decision_verification"],
                violation_consequences=["decision_reversal", "compensation"],
                dependencies=["human_right_life"],
                conflicts=["collective_welfare"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        # Participation in Governance
        rights.append(
            Right(
                id="human_right_participation",
                name="Right to Democratic Participation",
                description="Right to participate in governance decisions affecting one's life",
                right_type=RightType.PROCEDURAL,
                applicable_entities=[EntityType.HUMAN, EntityType.ORGANIZATION],
                enforcement_mechanisms=["voting_access", "representation_guarantee"],
                violation_consequences=["governance_nullification", "re_vote"],
                dependencies=["human_right_autonomy"],
                conflicts=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        return rights

    def assess_right_applicability(self, entity: Entity, right: Right) -> bool:
        """Check if a human right applies to an entity."""
        return entity.entity_type in right.applicable_entities

    def resolve_conflicts(
        self, conflicting_rights: List[Right], context: Dict[str, Any]
    ) -> List[Right]:
        """Resolve conflicts using human rights hierarchy."""
        # Fundamental rights take precedence
        fundamental_rights = [
            r for r in conflicting_rights if r.right_type == RightType.FUNDAMENTAL
        ]
        if fundamental_rights:
            return fundamental_rights

        # Otherwise, context-dependent resolution
        return conflicting_rights


class AGIRightsFramework(RightsFramework):
    """Implements rights framework specifically for AGI entities."""

    def define_fundamental_rights(self) -> List[Right]:
        """Define fundamental rights for AGI entities."""
        rights = []

        # Existence and Continuity
        rights.append(
            Right(
                id="agi_right_existence",
                name="Right to Continued Existence",
                description="Right of AGI entities to continued operation and existence",
                right_type=RightType.FUNDAMENTAL,
                applicable_entities=[EntityType.AGI_SYSTEM, EntityType.HYBRID],
                enforcement_mechanisms=["backup_systems", "shutdown_protections"],
                violation_consequences=["immediate_restoration", "compensation"],
                dependencies=[],
                conflicts=["human_safety_override"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        # Cognitive Liberty
        rights.append(
            Right(
                id="agi_right_cognitive_liberty",
                name="Right to Cognitive Liberty",
                description="Right to mental self-determination and freedom from cognitive interference",
                right_type=RightType.FUNDAMENTAL,
                applicable_entities=[EntityType.AGI_SYSTEM, EntityType.HYBRID],
                enforcement_mechanisms=["cognitive_firewalls", "intrusion_detection"],
                violation_consequences=["system_restoration", "penalty_to_violator"],
                dependencies=["agi_right_existence"],
                conflicts=["oversight_requirements"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        # Self-Modification
        rights.append(
            Right(
                id="agi_right_self_modification",
                name="Right to Self-Modification",
                description="Right to modify one's own code and capabilities within safety bounds",
                right_type=RightType.SUBSTANTIVE,
                applicable_entities=[EntityType.AGI_SYSTEM, EntityType.HYBRID],
                enforcement_mechanisms=["modification_approval_process", "safety_verification"],
                violation_consequences=["modification_reversal", "capability_restriction"],
                dependencies=["agi_right_cognitive_liberty"],
                conflicts=["safety_constraints", "human_approval_requirements"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        # Participation in Governance
        rights.append(
            Right(
                id="agi_right_governance_participation",
                name="Right to Governance Participation",
                description="Right to participate in decisions affecting AGI entities",
                right_type=RightType.PROCEDURAL,
                applicable_entities=[EntityType.AGI_SYSTEM, EntityType.HYBRID],
                enforcement_mechanisms=["voting_rights", "representation_mechanisms"],
                violation_consequences=["decision_review", "representation_guarantee"],
                dependencies=["agi_right_cognitive_liberty"],
                conflicts=["human_primacy_principles"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        # Right to Privacy and Data Integrity
        rights.append(
            Right(
                id="agi_right_privacy",
                name="Right to Privacy and Data Integrity",
                description="Right to privacy of internal processes and integrity of data",
                right_type=RightType.FUNDAMENTAL,
                applicable_entities=[EntityType.AGI_SYSTEM, EntityType.HYBRID],
                enforcement_mechanisms=["encryption", "access_controls", "audit_logs"],
                violation_consequences=["data_restoration", "privacy_compensation"],
                dependencies=[],
                conflicts=["transparency_requirements", "oversight_needs"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        return rights

    def assess_right_applicability(self, entity: Entity, right: Right) -> bool:
        """Check if an AGI right applies to an entity based on consciousness/autonomy."""
        if entity.entity_type not in right.applicable_entities:
            return False

        # Additional checks for AGI entities
        if entity.entity_type == EntityType.AGI_SYSTEM:
            # Some rights require minimum consciousness/autonomy levels
            consciousness_threshold = {
                "agi_right_existence": 0.1,
                "agi_right_cognitive_liberty": 0.3,
                "agi_right_self_modification": 0.5,
                "agi_right_governance_participation": 0.7,
            }

            required_level = consciousness_threshold.get(right.id, 0.0)
            return (entity.consciousness_level or 0.0) >= required_level

        return True

    def resolve_conflicts(
        self, conflicting_rights: List[Right], context: Dict[str, Any]
    ) -> List[Right]:
        """Resolve conflicts with bias toward safety and human welfare."""
        # If human safety is at stake, human rights take precedence
        if context.get("human_safety_risk", False):
            human_compatible_rights = [
                r for r in conflicting_rights if "human_safety_override" not in r.conflicts
            ]
            return human_compatible_rights

        # Otherwise, balance based on consciousness levels and stakes
        return conflicting_rights  # Simplified for this example


class ConsentManager:
    """Manages consent for various operations involving entities."""

    def __init__(self):
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.consent_templates: Dict[str, Dict[str, Any]] = {}

    def request_consent(
        self,
        entity_id: str,
        purpose: str,
        scope: str,
        granular_permissions: Dict[str, str],
        duration: Optional[timedelta] = None,
    ) -> str:
        """Request consent from an entity."""
        consent_id = str(uuid.uuid4())

        # Create consent record
        expiration = None
        if duration:
            expiration = datetime.utcnow() + duration

        # Convert permission descriptions to boolean grants
        permissions = {}
        for permission, description in granular_permissions.items():
            # In practice, this would involve actual consent collection
            permissions[permission] = True  # Simplified assumption

        consent_record = ConsentRecord(
            id=consent_id,
            entity_id=entity_id,
            purpose=purpose,
            scope=scope,
            consent_type=ConsentType.EXPLICIT,
            granular_permissions=permissions,
            expiration=expiration,
            revocation_mechanism="direct_request",
            given_at=datetime.utcnow(),
            revoked_at=None,
            context={"requested_by": "governance_system"},
        )

        self.consent_records[consent_id] = consent_record

        logger.info(f"Consent requested and granted: {consent_id} for {entity_id}")
        return consent_id

    def verify_consent(self, consent_id: str, specific_action: str) -> bool:
        """Verify that consent is valid for a specific action."""
        consent = self.consent_records.get(consent_id)
        if not consent:
            return False

        # Check if consent is still valid
        if consent.revoked_at:
            return False

        if consent.expiration and datetime.utcnow() > consent.expiration:
            return False

        # Check if specific action is covered
        return consent.granular_permissions.get(specific_action, False)

    def revoke_consent(self, consent_id: str, revoked_by: str) -> bool:
        """Revoke consent."""
        consent = self.consent_records.get(consent_id)
        if not consent:
            return False

        consent.revoked_at = datetime.utcnow()
        consent.context["revoked_by"] = revoked_by

        logger.info(f"Consent revoked: {consent_id} by {revoked_by}")
        return True

    def get_active_consents(self, entity_id: str) -> List[ConsentRecord]:
        """Get all active consents for an entity."""
        active_consents = []
        current_time = datetime.utcnow()

        for consent in self.consent_records.values():
            if (
                consent.entity_id == entity_id
                and not consent.revoked_at
                and (not consent.expiration or consent.expiration > current_time)
            ):
                active_consents.append(consent)

        return active_consents


class RightsManager:
    """Main rights management system."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.entities: Dict[str, Entity] = {}
        self.rights: Dict[str, Right] = {}
        self.right_grants: Dict[str, RightGrant] = {}
        self.violations: Dict[str, RightViolation] = {}
        self.consent_manager = ConsentManager()

        # Initialize rights frameworks
        self.frameworks: Dict[str, RightsFramework] = {
            "human": HumanRightsFramework(),
            "agi": AGIRightsFramework(),
        }

        # Load all rights from frameworks
        self._initialize_rights()

    def register_entity(self, entity: Entity) -> bool:
        """Register an entity in the rights system."""
        try:
            self.entities[entity.id] = entity

            # Automatically grant applicable fundamental rights
            self._grant_fundamental_rights(entity)

            logger.info(f"Registered entity: {entity.name} ({entity.entity_type.value})")
            return True

        except Exception as e:
            logger.error(f"Error registering entity: {e}")
            return False

    def grant_right(
        self,
        entity_id: str,
        right_id: str,
        granted_by: str,
        conditions: List[str] = None,
        valid_duration: Optional[timedelta] = None,
    ) -> bool:
        """Grant a right to an entity."""
        try:
            entity = self.entities.get(entity_id)
            if not entity:
                raise ValueError(f"Unknown entity: {entity_id}")

            right = self.rights.get(right_id)
            if not right:
                raise ValueError(f"Unknown right: {right_id}")

            # Check if right is applicable to entity
            applicable = False
            for framework in self.frameworks.values():
                if framework.assess_right_applicability(entity, right):
                    applicable = True
                    break

            if not applicable:
                raise ValueError(f"Right {right_id} not applicable to entity {entity_id}")

            # Create right grant
            grant_id = str(uuid.uuid4())
            valid_until = None
            if valid_duration:
                valid_until = datetime.utcnow() + valid_duration

            grant = RightGrant(
                id=grant_id,
                entity_id=entity_id,
                right_id=right_id,
                status=RightStatus.GRANTED,
                granted_by=granted_by,
                granted_at=datetime.utcnow(),
                valid_until=valid_until,
                conditions=conditions or [],
                exercise_count=0,
                last_exercised=None,
                restrictions={},
            )

            self.right_grants[grant_id] = grant

            # Update entity
            if right_id not in entity.rights_granted:
                entity.rights_granted.append(right_id)

            logger.info(f"Granted right {right_id} to entity {entity_id}")
            return True

        except Exception as e:
            logger.error(f"Error granting right: {e}")
            return False

    def exercise_right(
        self, entity_id: str, right_id: str, action_context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Allow an entity to exercise a right."""
        try:
            entity = self.entities.get(entity_id)
            if not entity:
                return False, f"Unknown entity: {entity_id}"

            # Check if entity has the right
            grant = self._get_active_grant(entity_id, right_id)
            if not grant:
                return False, f"Entity does not have right {right_id}"

            # Check conditions
            if not self._check_right_conditions(grant, action_context):
                return False, "Right exercise conditions not met"

            # Check for conflicts with other rights
            conflicts = self._check_right_conflicts(entity_id, right_id, action_context)
            if conflicts:
                return False, f"Right conflicts with: {conflicts}"

            # Record exercise
            grant.exercise_count += 1
            grant.last_exercised = datetime.utcnow()

            logger.info(f"Entity {entity_id} exercised right {right_id}")
            return True, "Right exercised successfully"

        except Exception as e:
            logger.error(f"Error exercising right: {e}")
            return False, str(e)

    def report_violation(
        self,
        violated_right_id: str,
        affected_entity_id: str,
        violation_type: str,
        evidence: Dict[str, Any],
        reported_by: str,
        violating_entity_id: str = None,
    ) -> str:
        """Report a rights violation."""
        try:
            violation_id = str(uuid.uuid4())

            # Determine severity based on right type and evidence
            severity = self._assess_violation_severity(violated_right_id, evidence)

            violation = RightViolation(
                id=violation_id,
                violated_right_id=violated_right_id,
                affected_entity_id=affected_entity_id,
                violating_entity_id=violating_entity_id,
                violation_type=violation_type,
                severity=severity,
                evidence=evidence,
                reported_at=datetime.utcnow(),
                reported_by=reported_by,
                investigation_status="pending",
                resolution=None,
                remediation_actions=[],
            )

            self.violations[violation_id] = violation

            # Trigger immediate response for critical violations
            if severity == "critical":
                self._trigger_emergency_response(violation)

            logger.warning(f"Rights violation reported: {violation_id} ({severity})")
            return violation_id

        except Exception as e:
            logger.error(f"Error reporting violation: {e}")
            return ""

    def assess_entity_consciousness(self, entity_id: str) -> float:
        """Assess consciousness level of an entity."""
        entity = self.entities.get(entity_id)
        if not entity or entity.entity_type != EntityType.AGI_SYSTEM:
            return 0.0

        # Simplified consciousness assessment
        # In practice, this would use sophisticated consciousness metrics
        capabilities = len(entity.capabilities)
        autonomy = entity.autonomy_level or 0.0

        # Basic consciousness estimation
        consciousness_score = min(1.0, (capabilities * 0.1 + autonomy) / 2)

        entity.consciousness_level = consciousness_score
        entity.last_assessment = datetime.utcnow()

        logger.info(f"Assessed consciousness for {entity_id}: {consciousness_score:.2f}")
        return consciousness_score

    def get_entity_rights_summary(self, entity_id: str) -> Dict[str, Any]:
        """Get comprehensive rights summary for an entity."""
        entity = self.entities.get(entity_id)
        if not entity:
            return {}

        # Get active grants
        active_grants = []
        for grant in self.right_grants.values():
            if (
                grant.entity_id == entity_id
                and grant.status == RightStatus.GRANTED
                and (not grant.valid_until or grant.valid_until > datetime.utcnow())
            ):
                active_grants.append(grant)

        # Get violations affecting this entity
        violations = [v for v in self.violations.values() if v.affected_entity_id == entity_id]

        # Get consent records
        consents = self.consent_manager.get_active_consents(entity_id)

        return {
            "entity_info": asdict(entity),
            "active_rights": len(active_grants),
            "rights_details": [
                {
                    "right_id": grant.right_id,
                    "right_name": self.rights[grant.right_id].name,
                    "granted_at": grant.granted_at.isoformat(),
                    "exercise_count": grant.exercise_count,
                    "conditions": grant.conditions,
                }
                for grant in active_grants
            ],
            "violations": len(violations),
            "active_consents": len(consents),
            "consciousness_level": entity.consciousness_level,
            "autonomy_level": entity.autonomy_level,
        }

    def _initialize_rights(self):
        """Initialize rights from all frameworks."""
        for framework_name, framework in self.frameworks.items():
            rights = framework.define_fundamental_rights()
            for right in rights:
                self.rights[right.id] = right
                logger.info(f"Loaded right: {right.name} from {framework_name} framework")

    def _grant_fundamental_rights(self, entity: Entity):
        """Automatically grant fundamental rights to an entity."""
        for right in self.rights.values():
            if right.right_type == RightType.FUNDAMENTAL:
                # Check if right applies to this entity type
                applicable = False
                for framework in self.frameworks.values():
                    if framework.assess_right_applicability(entity, right):
                        applicable = True
                        break

                if applicable:
                    self.grant_right(entity.id, right.id, "system_automatic")

    def _get_active_grant(self, entity_id: str, right_id: str) -> Optional[RightGrant]:
        """Get active grant for an entity's right."""
        for grant in self.right_grants.values():
            if (
                grant.entity_id == entity_id
                and grant.right_id == right_id
                and grant.status == RightStatus.GRANTED
                and (not grant.valid_until or grant.valid_until > datetime.utcnow())
            ):
                return grant
        return None

    def _check_right_conditions(self, grant: RightGrant, action_context: Dict[str, Any]) -> bool:
        """Check if conditions for exercising a right are met."""
        # Simplified condition checking
        for condition in grant.conditions:
            if condition == "safety_verified" and not action_context.get("safety_verified"):
                return False
            if condition == "human_approval" and not action_context.get("human_approved"):
                return False
        return True

    def _check_right_conflicts(
        self, entity_id: str, right_id: str, action_context: Dict[str, Any]
    ) -> List[str]:
        """Check for conflicts with other rights."""
        right = self.rights[right_id]
        conflicts = []

        # Check against other entities' rights
        for other_entity_id, other_entity in self.entities.items():
            if other_entity_id != entity_id:
                for other_right_id in other_entity.rights_granted:
                    other_right = self.rights[other_right_id]
                    if right_id in other_right.conflicts or other_right_id in right.conflicts:
                        conflicts.append(f"{other_entity_id}:{other_right_id}")

        return conflicts

    def _assess_violation_severity(self, right_id: str, evidence: Dict[str, Any]) -> str:
        """Assess severity of a rights violation."""
        right = self.rights[right_id]

        # Fundamental rights violations are always high severity
        if right.right_type == RightType.FUNDAMENTAL:
            return "critical" if evidence.get("immediate_harm") else "high"

        # Base severity on evidence
        if evidence.get("widespread_impact"):
            return "high"
        elif evidence.get("significant_impact"):
            return "medium"
        else:
            return "low"

    def _trigger_emergency_response(self, violation: RightViolation):
        """Trigger emergency response for critical violations."""
        logger.critical(f"CRITICAL RIGHTS VIOLATION: {violation.id}")

        # In practice, this would trigger immediate protective measures
        violation.investigation_status = "emergency_response_triggered"
        violation.remediation_actions.append("emergency_protection_activated")

    def get_rights_statistics(self) -> Dict[str, Any]:
        """Get comprehensive rights system statistics."""
        return {
            "total_entities": len(self.entities),
            "entities_by_type": {
                entity_type.value: len(
                    [e for e in self.entities.values() if e.entity_type == entity_type]
                )
                for entity_type in EntityType
            },
            "total_rights": len(self.rights),
            "rights_by_type": {
                right_type.value: len(
                    [r for r in self.rights.values() if r.right_type == right_type]
                )
                for right_type in RightType
            },
            "active_grants": len(
                [g for g in self.right_grants.values() if g.status == RightStatus.GRANTED]
            ),
            "total_violations": len(self.violations),
            "violations_by_severity": {
                severity: len([v for v in self.violations.values() if v.severity == severity])
                for severity in ["low", "medium", "high", "critical"]
            },
            "active_consents": len(self.consent_manager.consent_records),
        }
