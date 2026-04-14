"""
AGI Governance Engine - Core governance framework for democratic AGI oversight.

This module implements the central governance engine that orchestrates all
governance mechanisms including DAO voting, ethical verification, and
stakeholder consensus.
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ProposalStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VOTING = "voting"
    PASSED = "passed"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    VETOED = "vetoed"


class VoteType(Enum):
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


class StakeholderType(Enum):
    HUMAN_INDIVIDUAL = "human_individual"
    ORGANIZATION = "organization"
    AGI_ENTITY = "agi_entity"
    EXPERT = "expert"
    AFFECTED_PARTY = "affected_party"


@dataclass
class Stakeholder:
    """Represents a stakeholder in the governance system."""

    id: str
    name: str
    type: StakeholderType
    reputation_score: float
    voting_power: float
    expertise_domains: List[str]
    verified: bool
    created_at: datetime


@dataclass
class Proposal:
    """Represents a governance proposal."""

    id: str
    title: str
    description: str
    category: str
    proposer_id: str
    status: ProposalStatus
    voting_deadline: datetime
    implementation_deadline: Optional[datetime]
    ethical_constraints: List[str]
    impact_assessment: Dict[str, Any]
    required_approvals: List[str]
    votes: Dict[str, Dict[str, Any]]  # stakeholder_id -> vote details
    created_at: datetime
    updated_at: datetime


@dataclass
class GovernanceDecision:
    """Represents a final governance decision."""

    id: str
    proposal_id: str
    decision: str
    rationale: str
    ethical_verification: Dict[str, Any]
    stakeholder_consensus: Dict[str, Any]
    implementation_plan: Dict[str, Any]
    oversight_requirements: List[str]
    created_at: datetime


class EthicalFramework(ABC):
    """Abstract base class for ethical frameworks."""

    @abstractmethod
    def verify_proposal(self, proposal: Proposal) -> Tuple[bool, str]:
        """Verify if a proposal meets ethical constraints."""
        pass

    @abstractmethod
    def get_framework_name(self) -> str:
        """Return the name of the ethical framework."""
        pass


class GovernanceEngine:
    """
    Core governance engine that orchestrates democratic decision-making
    for AGI systems.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stakeholders: Dict[str, Stakeholder] = {}
        self.proposals: Dict[str, Proposal] = {}
        self.decisions: Dict[str, GovernanceDecision] = {}
        self.ethical_frameworks: List[EthicalFramework] = []
        self.audit_trail: List[Dict[str, Any]] = []

        # Governance parameters
        self.voting_period_days = config.get("voting_period_days", 7)
        self.quorum_threshold = config.get("quorum_threshold", 0.1)
        self.approval_threshold = config.get("approval_threshold", 0.6)
        self.veto_threshold = config.get("veto_threshold", 0.8)

    def register_stakeholder(self, stakeholder: Stakeholder) -> bool:
        """Register a new stakeholder in the governance system."""
        try:
            self.stakeholders[stakeholder.id] = stakeholder

            self._log_audit_event(
                {
                    "event_type": "stakeholder_registered",
                    "stakeholder_id": stakeholder.id,
                    "stakeholder_type": stakeholder.type.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info(f"Registered stakeholder: {stakeholder.name} ({stakeholder.id})")
            return True

        except Exception as e:
            logger.error(f"Failed to register stakeholder {stakeholder.id}: {e}")
            return False

    def submit_proposal(self, proposal: Proposal) -> bool:
        """Submit a new governance proposal."""
        try:
            # Validate proposer
            if proposal.proposer_id not in self.stakeholders:
                raise ValueError(f"Unknown proposer: {proposal.proposer_id}")

            # Set voting deadline
            proposal.voting_deadline = datetime.now(timezone.utc) + timedelta(days=self.voting_period_days)
            proposal.status = ProposalStatus.SUBMITTED

            # Store proposal
            self.proposals[proposal.id] = proposal

            self._log_audit_event(
                {
                    "event_type": "proposal_submitted",
                    "proposal_id": proposal.id,
                    "proposer_id": proposal.proposer_id,
                    "title": proposal.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info(f"Proposal submitted: {proposal.title} ({proposal.id})")
            return True

        except Exception as e:
            logger.error(f"Failed to submit proposal {proposal.id}: {e}")
            return False

    def cast_vote(
        self, proposal_id: str, stakeholder_id: str, vote_type: VoteType, reasoning: str = ""
    ) -> bool:
        """Cast a vote on a proposal."""
        try:
            proposal = self.proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Unknown proposal: {proposal_id}")

            stakeholder = self.stakeholders.get(stakeholder_id)
            if not stakeholder:
                raise ValueError(f"Unknown stakeholder: {stakeholder_id}")

            if proposal.status != ProposalStatus.VOTING:
                if proposal.status == ProposalStatus.SUBMITTED:
                    proposal.status = ProposalStatus.VOTING
                else:
                    raise ValueError(f"Proposal not in voting phase: {proposal.status}")

            if datetime.now(timezone.utc) > proposal.voting_deadline:
                raise ValueError("Voting deadline has passed")

            # Record vote
            proposal.votes[stakeholder_id] = {
                "vote_type": vote_type.value,
                "reasoning": reasoning,
                "voting_power": stakeholder.voting_power,
                "reputation_score": stakeholder.reputation_score,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._log_audit_event(
                {
                    "event_type": "vote_cast",
                    "proposal_id": proposal_id,
                    "stakeholder_id": stakeholder_id,
                    "vote_type": vote_type.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info(
                f"Vote cast by {stakeholder_id} on proposal {proposal_id}: {vote_type.value}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to cast vote: {e}")
            return False

    def calculate_vote_results(self, proposal_id: str) -> Dict[str, Any]:
        """Calculate voting results for a proposal."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Unknown proposal: {proposal_id}")

        total_voting_power = sum(s.voting_power for s in self.stakeholders.values() if s.verified)
        votes_cast_power = 0
        for_power = 0
        against_power = 0
        abstain_power = 0

        for stakeholder_id, vote_data in proposal.votes.items():
            voting_power = vote_data["voting_power"]
            votes_cast_power += voting_power

            if vote_data["vote_type"] == VoteType.FOR.value:
                for_power += voting_power
            elif vote_data["vote_type"] == VoteType.AGAINST.value:
                against_power += voting_power
            elif vote_data["vote_type"] == VoteType.ABSTAIN.value:
                abstain_power += voting_power

        # Calculate participation and approval rates
        participation_rate = votes_cast_power / total_voting_power if total_voting_power > 0 else 0
        approval_rate = for_power / votes_cast_power if votes_cast_power > 0 else 0

        return {
            "total_voting_power": total_voting_power,
            "votes_cast_power": votes_cast_power,
            "for_power": for_power,
            "against_power": against_power,
            "abstain_power": abstain_power,
            "participation_rate": participation_rate,
            "approval_rate": approval_rate,
            "meets_quorum": participation_rate >= self.quorum_threshold,
            "meets_approval": approval_rate >= self.approval_threshold,
        }

    def finalize_proposal(self, proposal_id: str) -> Optional[GovernanceDecision]:
        """Finalize a proposal and create a governance decision."""
        try:
            proposal = self.proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Unknown proposal: {proposal_id}")

            if datetime.now(timezone.utc) <= proposal.voting_deadline:
                raise ValueError("Voting period not yet ended")

            # Calculate vote results
            results = self.calculate_vote_results(proposal_id)

            # Verify ethical constraints
            ethical_verification = self._verify_ethical_constraints(proposal)

            # Determine decision
            if not results["meets_quorum"]:
                decision = "rejected"
                rationale = "Failed to meet quorum threshold"
            elif not ethical_verification["all_passed"]:
                decision = "rejected"
                rationale = f"Failed ethical verification: {ethical_verification['failures']}"
            elif results["meets_approval"]:
                decision = "approved"
                rationale = f"Approved with {results['approval_rate']:.1%} support"
            else:
                decision = "rejected"
                rationale = f"Failed to meet approval threshold ({results['approval_rate']:.1%})"

            # Create governance decision
            governance_decision = GovernanceDecision(
                id=self._generate_id("decision"),
                proposal_id=proposal_id,
                decision=decision,
                rationale=rationale,
                ethical_verification=ethical_verification,
                stakeholder_consensus=results,
                implementation_plan=(
                    {} if decision != "approved" else self._create_implementation_plan(proposal)
                ),
                oversight_requirements=(
                    [] if decision != "approved" else self._create_oversight_requirements(proposal)
                ),
                created_at=datetime.now(timezone.utc),
            )

            # Update proposal status
            proposal.status = (
                ProposalStatus.PASSED if decision == "approved" else ProposalStatus.REJECTED
            )

            # Store decision
            self.decisions[governance_decision.id] = governance_decision

            self._log_audit_event(
                {
                    "event_type": "proposal_finalized",
                    "proposal_id": proposal_id,
                    "decision_id": governance_decision.id,
                    "decision": decision,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info(f"Proposal {proposal_id} finalized: {decision}")
            return governance_decision

        except Exception as e:
            logger.error(f"Failed to finalize proposal {proposal_id}: {e}")
            return None

    def add_ethical_framework(self, framework: EthicalFramework):
        """Add an ethical framework for proposal verification."""
        self.ethical_frameworks.append(framework)
        logger.info(f"Added ethical framework: {framework.get_framework_name()}")

    def _verify_ethical_constraints(self, proposal: Proposal) -> Dict[str, Any]:
        """Verify proposal against all ethical frameworks."""
        results = {"all_passed": True, "frameworks_checked": [], "failures": []}

        for framework in self.ethical_frameworks:
            framework_name = framework.get_framework_name()
            passed, reason = framework.verify_proposal(proposal)

            results["frameworks_checked"].append(
                {"name": framework_name, "passed": passed, "reason": reason}
            )

            if not passed:
                results["all_passed"] = False
                results["failures"].append(f"{framework_name}: {reason}")

        return results

    def _create_implementation_plan(self, proposal: Proposal) -> Dict[str, Any]:
        """Create an implementation plan for an approved proposal."""
        return {
            "phases": [
                {
                    "name": "Preparation",
                    "duration_days": 7,
                    "requirements": ["Stakeholder notification", "Resource allocation"],
                },
                {
                    "name": "Implementation",
                    "duration_days": 30,
                    "requirements": ["Progressive rollout", "Monitoring setup"],
                },
                {
                    "name": "Review",
                    "duration_days": 14,
                    "requirements": ["Impact assessment", "Stakeholder feedback"],
                },
            ],
            "milestones": [],
            "success_criteria": [],
            "rollback_plan": {},
        }

    def _create_oversight_requirements(self, proposal: Proposal) -> List[str]:
        """Create oversight requirements for an approved proposal."""
        return [
            "Weekly progress reports",
            "Monthly stakeholder review",
            "Continuous ethical monitoring",
            "Impact measurement and reporting",
            "Emergency intervention capabilities",
        ]

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix."""
        timestamp = datetime.now(timezone.utc).isoformat()
        data = f"{prefix}_{timestamp}_{id(self)}"
        return f"{prefix}_{hashlib.md5(data.encode()).hexdigest()[:8]}"

    def _log_audit_event(self, event: Dict[str, Any]):
        """Log an event to the audit trail."""
        self.audit_trail.append(event)

    def get_governance_statistics(self) -> Dict[str, Any]:
        """Get governance system statistics."""
        total_stakeholders = len(self.stakeholders)
        verified_stakeholders = sum(1 for s in self.stakeholders.values() if s.verified)
        total_proposals = len(self.proposals)
        active_proposals = sum(
            1
            for p in self.proposals.values()
            if p.status in [ProposalStatus.SUBMITTED, ProposalStatus.VOTING]
        )

        return {
            "total_stakeholders": total_stakeholders,
            "verified_stakeholders": verified_stakeholders,
            "total_proposals": total_proposals,
            "active_proposals": active_proposals,
            "total_decisions": len(self.decisions),
            "ethical_frameworks": len(self.ethical_frameworks),
            "audit_events": len(self.audit_trail),
        }

    def export_audit_trail(self) -> List[Dict[str, Any]]:
        """Export the complete audit trail."""
        return self.audit_trail.copy()

    def get_proposal_summary(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a proposal including current status."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return None

        summary = asdict(proposal)

        if proposal.votes:
            summary["vote_results"] = self.calculate_vote_results(proposal_id)

        return summary


# Example ethical frameworks
class UtilitarianFramework(EthicalFramework):
    """Utilitarian ethical framework focusing on maximizing overall wellbeing."""

    def verify_proposal(self, proposal: Proposal) -> Tuple[bool, str]:
        # Check if proposal maximizes overall utility
        impact = proposal.impact_assessment

        if "net_utility" not in impact:
            return False, "Missing net utility assessment"

        if impact["net_utility"] < 0:
            return False, "Proposal has negative net utility"

        return True, "Proposal maximizes overall utility"

    def get_framework_name(self) -> str:
        return "Utilitarian Ethics"


class DeontologicalFramework(EthicalFramework):
    """Deontological ethical framework focusing on duties and rights."""

    def verify_proposal(self, proposal: Proposal) -> Tuple[bool, str]:
        # Check for violations of fundamental duties/rights
        constraints = proposal.ethical_constraints

        prohibited_actions = [
            "harm_without_consent",
            "deception",
            "rights_violation",
            "autonomy_violation",
        ]

        for constraint in constraints:
            if constraint in prohibited_actions:
                return False, f"Proposal violates fundamental duty: {constraint}"

        return True, "Proposal respects fundamental duties and rights"

    def get_framework_name(self) -> str:
        return "Deontological Ethics"


class VirtueEthicsFramework(EthicalFramework):
    """Virtue ethics framework focusing on character and virtues."""

    def verify_proposal(self, proposal: Proposal) -> Tuple[bool, str]:
        # Check if proposal promotes virtuous behavior
        impact = proposal.impact_assessment

        virtues_promoted = impact.get("virtues_promoted", [])
        vices_encouraged = impact.get("vices_encouraged", [])

        if vices_encouraged:
            return False, f"Proposal encourages vices: {vices_encouraged}"

        if not virtues_promoted:
            return False, "Proposal does not promote any virtues"

        return True, f"Proposal promotes virtues: {virtues_promoted}"

    def get_framework_name(self) -> str:
        return "Virtue Ethics"
