"""
DAO (Decentralized Autonomous Organization) Mechanisms for AGI Governance.

This module implements blockchain-based DAO mechanisms for decentralized
governance of AGI systems, including proposal management, voting systems,
and treasury management.
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


class ProposalType(Enum):
    POLICY = "policy"
    BUDGET = "budget"
    TECHNICAL = "technical"
    EMERGENCY = "emergency"
    CONSTITUTIONAL = "constitutional"


class TokenType(Enum):
    GOVERNANCE = "governance"
    UTILITY = "utility"
    REPUTATION = "reputation"


@dataclass
class DAOToken:
    """Represents a token in the DAO system."""

    id: str
    holder_id: str
    token_type: TokenType
    amount: float
    locked_until: Optional[datetime]
    voting_power_multiplier: float
    earned_from: str  # How the token was earned
    created_at: datetime


@dataclass
class DAOProposal:
    """DAO-specific proposal with blockchain integration."""

    id: str
    title: str
    description: str
    proposal_type: ProposalType
    proposer_id: str
    required_tokens: float
    voting_period: timedelta
    execution_delay: timedelta
    treasury_impact: Optional[Dict[str, float]]
    smart_contract_code: Optional[str]
    implementation_hash: str
    votes: Dict[str, Dict[str, Any]]
    created_at: datetime
    voting_starts_at: datetime
    voting_ends_at: datetime
    execution_at: Optional[datetime]


@dataclass
class DAOTransaction:
    """Represents a transaction in the DAO."""

    id: str
    from_address: str
    to_address: str
    amount: float
    token_type: TokenType
    transaction_type: str
    proposal_id: Optional[str]
    block_height: int
    transaction_hash: str
    gas_used: float
    timestamp: datetime


class QuadraticVoting:
    """Implements quadratic voting mechanism for fair representation."""

    def __init__(self, max_tokens_per_vote: float = 100.0):
        self.max_tokens_per_vote = max_tokens_per_vote

    def calculate_vote_cost(self, vote_count: int) -> float:
        """Calculate the token cost for a given number of votes."""
        return vote_count**2

    def calculate_max_votes(self, available_tokens: float) -> int:
        """Calculate maximum votes possible with available tokens."""
        return int(available_tokens**0.5)

    def cast_quadratic_vote(
        self, voter_id: str, proposal_id: str, vote_intensity: int, vote_direction: str
    ) -> Dict[str, Any]:
        """Cast a quadratic vote with specified intensity."""
        cost = self.calculate_vote_cost(abs(vote_intensity))

        return {
            "voter_id": voter_id,
            "proposal_id": proposal_id,
            "vote_intensity": vote_intensity,
            "vote_direction": vote_direction,
            "token_cost": cost,
            "voting_power": abs(vote_intensity),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }


class DAOTreasury:
    """Manages DAO treasury and resource allocation."""

    def __init__(self, initial_balance: Dict[str, float]):
        self.balances = initial_balance.copy()
        self.transactions: List[DAOTransaction] = []
        self.allocation_rules: Dict[str, Dict[str, Any]] = {}
        self.spending_limits: Dict[str, float] = {}

    def get_balance(self, token_type: str) -> float:
        """Get current balance for a token type."""
        return self.balances.get(token_type, 0.0)

    def allocate_funds(self, proposal_id: str, allocations: Dict[str, float]) -> bool:
        """Allocate treasury funds based on approved proposal."""
        try:
            # Check if sufficient funds available
            for token_type, amount in allocations.items():
                if self.get_balance(token_type) < amount:
                    raise ValueError(f"Insufficient {token_type} tokens")

            # Execute allocation
            for token_type, amount in allocations.items():
                self.balances[token_type] -= amount

                # Record transaction
                transaction = DAOTransaction(
                    id=self._generate_transaction_id(),
                    from_address="treasury",
                    to_address=f"allocation_{proposal_id}",
                    amount=amount,
                    token_type=TokenType(token_type),
                    transaction_type="allocation",
                    proposal_id=proposal_id,
                    block_height=len(self.transactions) + 1,
                    transaction_hash=self._generate_hash(f"alloc_{proposal_id}_{amount}"),
                    gas_used=0.1,
                    timestamp=datetime.now(tz=timezone.utc),
                )

                self.transactions.append(transaction)

            logger.info(f"Allocated funds for proposal {proposal_id}: {allocations}")
            return True

        except Exception as e:
            logger.error(f"Failed to allocate funds for proposal {proposal_id}: {e}")
            return False

    def add_revenue(self, token_type: str, amount: float, source: str):
        """Add revenue to treasury."""
        self.balances[token_type] = self.balances.get(token_type, 0) + amount

        transaction = DAOTransaction(
            id=self._generate_transaction_id(),
            from_address=source,
            to_address="treasury",
            amount=amount,
            token_type=TokenType(token_type),
            transaction_type="revenue",
            proposal_id=None,
            block_height=len(self.transactions) + 1,
            transaction_hash=self._generate_hash(f"revenue_{source}_{amount}"),
            gas_used=0.05,
            timestamp=datetime.now(tz=timezone.utc),
        )

        self.transactions.append(transaction)
        logger.info(f"Added {amount} {token_type} from {source} to treasury")

    def _generate_transaction_id(self) -> str:
        return f"tx_{hashlib.md5(str(datetime.now(tz=timezone.utc)).encode()).hexdigest()[:12]}"

    def _generate_hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()


class ReputationSystem:
    """Manages reputation-based voting power and token distribution."""

    def __init__(self):
        self.reputation_scores: Dict[str, float] = {}
        self.reputation_history: Dict[str, List[Dict[str, Any]]] = {}
        self.reputation_decay_rate = 0.01  # Daily decay rate

    def update_reputation(
        self, stakeholder_id: str, action: str, impact: float, context: Dict[str, Any]
    ):
        """Update stakeholder reputation based on actions."""
        current_score = self.reputation_scores.get(stakeholder_id, 0.0)

        # Calculate reputation change based on action
        reputation_change = self._calculate_reputation_change(action, impact, context)
        new_score = max(0, current_score + reputation_change)

        self.reputation_scores[stakeholder_id] = new_score

        # Record in history
        if stakeholder_id not in self.reputation_history:
            self.reputation_history[stakeholder_id] = []

        self.reputation_history[stakeholder_id].append(
            {
                "action": action,
                "impact": impact,
                "context": context,
                "reputation_change": reputation_change,
                "new_score": new_score,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        )

        logger.info(f"Updated reputation for {stakeholder_id}: {current_score} -> {new_score}")

    def get_voting_power(self, stakeholder_id: str, base_tokens: float) -> float:
        """Calculate voting power based on reputation and tokens."""
        reputation = self.reputation_scores.get(stakeholder_id, 0.0)
        reputation_multiplier = 1 + (reputation / 100)  # 1% increase per reputation point
        return base_tokens * reputation_multiplier

    def decay_reputation(self, days_passed: int = 1):
        """Apply time-based reputation decay."""
        decay_factor = (1 - self.reputation_decay_rate) ** days_passed

        for stakeholder_id in self.reputation_scores:
            old_score = self.reputation_scores[stakeholder_id]
            new_score = old_score * decay_factor
            self.reputation_scores[stakeholder_id] = new_score

            if abs(old_score - new_score) > 0.1:  # Only log significant changes
                logger.info(
                    f"Reputation decay for {stakeholder_id}: {old_score:.2f} -> {new_score:.2f}"
                )

    def _calculate_reputation_change(
        self, action: str, impact: float, context: Dict[str, Any]
    ) -> float:
        """Calculate reputation change based on action and impact."""
        base_changes = {
            "good_proposal": 5.0,
            "bad_proposal": -2.0,
            "constructive_vote": 1.0,
            "helpful_feedback": 2.0,
            "expertise_demonstration": 3.0,
            "community_service": 4.0,
            "malicious_behavior": -10.0,
            "vote_buying": -15.0,
            "manipulation_attempt": -20.0,
        }

        base_change = base_changes.get(action, 0.0)

        # Scale by impact magnitude
        impact_multiplier = min(abs(impact), 5.0)  # Cap at 5x

        # Apply context modifiers
        quality_modifier = context.get("quality_score", 1.0)
        consensus_modifier = context.get("consensus_level", 1.0)

        total_change = base_change * impact_multiplier * quality_modifier * consensus_modifier

        return total_change


class DAOGovernance:
    """Main DAO governance system integrating all mechanisms."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.proposals: Dict[str, DAOProposal] = {}
        self.tokens: Dict[str, List[DAOToken]] = {}  # stakeholder_id -> tokens
        self.treasury = DAOTreasury(config.get("initial_treasury", {}))
        self.reputation_system = ReputationSystem()
        self.quadratic_voting = QuadraticVoting()
        self.voting_records: Dict[str, List[Dict[str, Any]]] = {}

        # Governance parameters
        self.min_proposal_tokens = config.get("min_proposal_tokens", 100.0)
        self.voting_period_days = config.get("voting_period_days", 7)
        self.execution_delay_days = config.get("execution_delay_days", 2)
        self.quorum_threshold = config.get("quorum_threshold", 0.1)

    def create_dao_proposal(self, proposal_data: Dict[str, Any]) -> Optional[DAOProposal]:
        """Create a new DAO proposal."""
        try:
            proposer_id = proposal_data["proposer_id"]

            # Check if proposer has sufficient tokens
            if not self._has_sufficient_tokens(proposer_id, self.min_proposal_tokens):
                raise ValueError(f"Proposer needs {self.min_proposal_tokens} tokens")

            # Lock tokens for proposal
            self._lock_tokens(
                proposer_id, self.min_proposal_tokens, reason=f"proposal_{proposal_data['title']}"
            )

            voting_starts = datetime.now(tz=timezone.utc) + timedelta(hours=24)  # 24h delay
            voting_ends = voting_starts + timedelta(days=self.voting_period_days)

            proposal = DAOProposal(
                id=self._generate_id("prop"),
                title=proposal_data["title"],
                description=proposal_data["description"],
                proposal_type=ProposalType(proposal_data["proposal_type"]),
                proposer_id=proposer_id,
                required_tokens=self.min_proposal_tokens,
                voting_period=timedelta(days=self.voting_period_days),
                execution_delay=timedelta(days=self.execution_delay_days),
                treasury_impact=proposal_data.get("treasury_impact"),
                smart_contract_code=proposal_data.get("smart_contract_code"),
                implementation_hash=self._generate_hash(proposal_data["description"]),
                votes={},
                created_at=datetime.now(tz=timezone.utc),
                voting_starts_at=voting_starts,
                voting_ends_at=voting_ends,
                execution_at=None,
            )

            self.proposals[proposal.id] = proposal

            logger.info(f"Created DAO proposal: {proposal.title} ({proposal.id})")
            return proposal

        except Exception as e:
            logger.error(f"Failed to create DAO proposal: {e}")
            return None

    def cast_dao_vote(
        self, proposal_id: str, voter_id: str, vote_intensity: int, vote_direction: str
    ) -> bool:
        """Cast a vote using quadratic voting mechanism."""
        try:
            proposal = self.proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Unknown proposal: {proposal_id}")

            current_time = datetime.now(tz=timezone.utc)
            if current_time < proposal.voting_starts_at:
                raise ValueError("Voting has not started yet")

            if current_time > proposal.voting_ends_at:
                raise ValueError("Voting period has ended")

            # Get voter's available tokens
            available_tokens = self._get_available_tokens(voter_id, TokenType.GOVERNANCE)

            # Calculate quadratic vote
            vote_data = self.quadratic_voting.cast_quadratic_vote(
                voter_id, proposal_id, vote_intensity, vote_direction
            )

            if vote_data["token_cost"] > available_tokens:
                raise ValueError(f"Insufficient tokens for vote intensity {vote_intensity}")

            # Lock tokens for vote
            self._lock_tokens(voter_id, vote_data["token_cost"], reason=f"vote_{proposal_id}")

            # Apply reputation-based voting power
            voting_power = self.reputation_system.get_voting_power(
                voter_id, vote_data["voting_power"]
            )

            vote_data["reputation_adjusted_power"] = voting_power

            # Record vote
            proposal.votes[voter_id] = vote_data

            # Update voting records
            if voter_id not in self.voting_records:
                self.voting_records[voter_id] = []

            self.voting_records[voter_id].append(
                {
                    "proposal_id": proposal_id,
                    "vote_data": vote_data,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                }
            )

            logger.info(
                f"DAO vote cast: {voter_id} voted {vote_direction} "
                f"with intensity {vote_intensity} on {proposal_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to cast DAO vote: {e}")
            return False

    def execute_proposal(self, proposal_id: str) -> bool:
        """Execute an approved DAO proposal."""
        try:
            proposal = self.proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Unknown proposal: {proposal_id}")

            if datetime.now(tz=timezone.utc) <= proposal.voting_ends_at:
                raise ValueError("Voting period not yet ended")

            # Calculate results
            results = self._calculate_dao_results(proposal)

            if not results["approved"]:
                logger.info(f"Proposal {proposal_id} was not approved: {results['reason']}")
                return False

            # Wait for execution delay
            execution_time = proposal.voting_ends_at + proposal.execution_delay
            if datetime.now(tz=timezone.utc) < execution_time:
                proposal.execution_at = execution_time
                logger.info(f"Proposal {proposal_id} scheduled for execution at {execution_time}")
                return True

            # Execute proposal based on type
            success = self._execute_proposal_action(proposal)

            if success:
                # Update reputation for successful proposal
                self.reputation_system.update_reputation(
                    proposal.proposer_id,
                    "good_proposal",
                    results["approval_rate"],
                    {"quality_score": 1.0},
                )

                logger.info(f"Successfully executed proposal {proposal_id}")
            else:
                logger.error(f"Failed to execute proposal {proposal_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to execute proposal {proposal_id}: {e}")
            return False

    def distribute_tokens(
        self, stakeholder_id: str, token_type: TokenType, amount: float, reason: str
    ) -> bool:
        """Distribute tokens to a stakeholder."""
        try:
            token = DAOToken(
                id=self._generate_id("token"),
                holder_id=stakeholder_id,
                token_type=token_type,
                amount=amount,
                locked_until=None,
                voting_power_multiplier=1.0,
                earned_from=reason,
                created_at=datetime.now(tz=timezone.utc),
            )

            if stakeholder_id not in self.tokens:
                self.tokens[stakeholder_id] = []

            self.tokens[stakeholder_id].append(token)

            logger.info(f"Distributed {amount} {token_type.value} tokens to {stakeholder_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to distribute tokens: {e}")
            return False

    def _has_sufficient_tokens(self, stakeholder_id: str, required_amount: float) -> bool:
        """Check if stakeholder has sufficient unlocked tokens."""
        available = self._get_available_tokens(stakeholder_id, TokenType.GOVERNANCE)
        return available >= required_amount

    def _get_available_tokens(self, stakeholder_id: str, token_type: TokenType) -> float:
        """Get available (unlocked) tokens for a stakeholder."""
        if stakeholder_id not in self.tokens:
            return 0.0

        total = 0.0
        current_time = datetime.now(tz=timezone.utc)

        for token in self.tokens[stakeholder_id]:
            if token.token_type == token_type:
                if token.locked_until is None or current_time >= token.locked_until:
                    total += token.amount

        return total

    def _lock_tokens(self, stakeholder_id: str, amount: float, reason: str):
        """Lock tokens for a stakeholder."""
        if stakeholder_id not in self.tokens:
            raise ValueError(f"No tokens found for stakeholder {stakeholder_id}")

        remaining_to_lock = amount
        current_time = datetime.now(tz=timezone.utc)
        lock_until = current_time + timedelta(
            days=self.voting_period_days + self.execution_delay_days
        )

        for token in self.tokens[stakeholder_id]:
            if token.token_type == TokenType.GOVERNANCE and token.locked_until is None:
                if token.amount <= remaining_to_lock:
                    token.locked_until = lock_until
                    remaining_to_lock -= token.amount
                else:
                    # Split token
                    locked_token = DAOToken(
                        id=self._generate_id("token"),
                        holder_id=stakeholder_id,
                        token_type=token.token_type,
                        amount=remaining_to_lock,
                        locked_until=lock_until,
                        voting_power_multiplier=token.voting_power_multiplier,
                        earned_from=f"split_from_{token.id}",
                        created_at=datetime.now(tz=timezone.utc),
                    )

                    token.amount -= remaining_to_lock
                    self.tokens[stakeholder_id].append(locked_token)
                    remaining_to_lock = 0

                if remaining_to_lock <= 0:
                    break

        if remaining_to_lock > 0:
            raise ValueError(f"Insufficient tokens to lock: {remaining_to_lock} remaining")

    def _calculate_dao_results(self, proposal: DAOProposal) -> Dict[str, Any]:
        """Calculate DAO voting results."""
        total_votes = 0
        for_votes = 0
        against_votes = 0

        for vote_data in proposal.votes.values():
            voting_power = vote_data["reputation_adjusted_power"]
            total_votes += voting_power

            if vote_data["vote_direction"] == "for":
                for_votes += voting_power
            elif vote_data["vote_direction"] == "against":
                against_votes += voting_power

        # Calculate participation and approval
        total_possible_votes = sum(
            self._get_available_tokens(sid, TokenType.GOVERNANCE) for sid in self.tokens.keys()
        )
        participation_rate = total_votes / total_possible_votes if total_possible_votes > 0 else 0
        approval_rate = for_votes / total_votes if total_votes > 0 else 0

        approved = participation_rate >= self.quorum_threshold and approval_rate > 0.5

        reason = ""
        if not approved:
            if participation_rate < self.quorum_threshold:
                reason = f"Insufficient participation: {participation_rate:.1%}"
            else:
                reason = f"Insufficient approval: {approval_rate:.1%}"

        return {
            "total_votes": total_votes,
            "for_votes": for_votes,
            "against_votes": against_votes,
            "participation_rate": participation_rate,
            "approval_rate": approval_rate,
            "approved": approved,
            "reason": reason,
        }

    def _execute_proposal_action(self, proposal: DAOProposal) -> bool:
        """Execute the specific action defined in the proposal."""
        if proposal.proposal_type == ProposalType.BUDGET:
            if proposal.treasury_impact:
                return self.treasury.allocate_funds(proposal.id, proposal.treasury_impact)

        elif proposal.proposal_type == ProposalType.TECHNICAL:
            # Execute technical changes (placeholder)
            logger.info(f"Executing technical proposal: {proposal.title}")
            return True

        elif proposal.proposal_type == ProposalType.POLICY:
            # Update governance policies (placeholder)
            logger.info(f"Implementing policy proposal: {proposal.title}")
            return True

        elif proposal.proposal_type == ProposalType.EMERGENCY:
            # Execute emergency actions (placeholder)
            logger.info(f"Executing emergency proposal: {proposal.title}")
            return True

        elif proposal.proposal_type == ProposalType.CONSTITUTIONAL:
            # Update constitutional rules (placeholder)
            logger.info(f"Implementing constitutional change: {proposal.title}")
            return True

        return False

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix."""
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        data = f"{prefix}_{timestamp}_{id(self)}"
        return f"{prefix}_{hashlib.md5(data.encode()).hexdigest()[:8]}"

    def _generate_hash(self, data: str) -> str:
        """Generate a hash for data integrity."""
        return hashlib.sha256(data.encode()).hexdigest()

    def get_dao_statistics(self) -> Dict[str, Any]:
        """Get comprehensive DAO statistics."""
        return {
            "total_proposals": len(self.proposals),
            "active_proposals": sum(
                1 for p in self.proposals.values() if datetime.now(tz=timezone.utc) <= p.voting_ends_at
            ),
            "total_stakeholders": len(self.tokens),
            "treasury_balances": self.treasury.balances,
            "total_transactions": len(self.treasury.transactions),
            "average_reputation": (
                sum(self.reputation_system.reputation_scores.values())
                / len(self.reputation_system.reputation_scores)
                if self.reputation_system.reputation_scores
                else 0
            ),
        }
