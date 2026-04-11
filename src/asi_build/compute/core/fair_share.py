"""
Fair Share Manager - Implements fair-share resource allocation algorithms
"""

import asyncio
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FairShareModel(Enum):
    PROPORTIONAL = "proportional"
    LOTTERY = "lottery"
    WEIGHTED_FAIR_QUEUING = "wfq"
    DEFICIT_ROUND_ROBIN = "drr"


@dataclass
class UserAccount:
    """User account for fair share tracking"""

    user_id: str
    shares: float = 1.0  # Fair share allocation (relative weight)
    priority_boost: float = 1.0  # Priority multiplier
    usage_history: List[Tuple[float, float]] = field(
        default_factory=list
    )  # (timestamp, resource_seconds)
    current_usage: float = 0.0  # Current resource usage
    accumulated_usage: float = 0.0  # Total historical usage
    quota_limit: Optional[float] = None  # Resource usage limit
    group_memberships: List[str] = field(default_factory=list)

    def effective_priority(self, current_time: float, decay_rate: float = 0.9) -> float:
        """Calculate effective priority based on usage history"""
        # Apply exponential decay to historical usage
        decayed_usage = 0.0
        cutoff_time = current_time - 86400  # 24 hours

        for timestamp, usage in self.usage_history:
            if timestamp > cutoff_time:
                age_hours = (current_time - timestamp) / 3600.0
                decay_factor = decay_rate**age_hours
                decayed_usage += usage * decay_factor

        # Calculate fair share ratio (lower usage = higher priority)
        if self.shares > 0:
            usage_ratio = (decayed_usage + self.current_usage) / self.shares
            return self.priority_boost / max(usage_ratio, 0.1)

        return self.priority_boost


@dataclass
class GroupAccount:
    """Group account for hierarchical fair sharing"""

    group_id: str
    parent_group: Optional[str] = None
    shares: float = 1.0
    members: List[str] = field(default_factory=list)
    subgroups: List[str] = field(default_factory=list)
    usage_limits: Dict[str, float] = field(default_factory=dict)


@dataclass
class ResourceQuota:
    """Resource quota specification"""

    resource_type: str
    soft_limit: float  # Warning threshold
    hard_limit: float  # Absolute limit
    current_usage: float = 0.0
    peak_usage: float = 0.0
    reset_period: float = 86400.0  # 24 hours default
    last_reset: float = field(default_factory=time.time)


class FairShareManager:
    """
    Advanced fair share manager supporting multiple algorithms
    and hierarchical resource allocation
    """

    def __init__(self, model: FairShareModel = FairShareModel.PROPORTIONAL):
        self.model = model
        self.logger = logging.getLogger("fair_share_manager")

        # User and group management
        self.users: Dict[str, UserAccount] = {}
        self.groups: Dict[str, GroupAccount] = {}
        self.quotas: Dict[str, Dict[str, ResourceQuota]] = {}  # user_id -> resource_type -> quota

        # Fair share parameters
        self.decay_rate = 0.9  # Usage decay rate per hour
        self.min_shares = 0.01  # Minimum share allocation
        self.max_shares = 100.0  # Maximum share allocation
        self.priority_boost_max = 10.0

        # Lottery scheduling state
        self.lottery_tickets: Dict[str, int] = {}
        self.total_tickets = 0

        # Weighted Fair Queuing state
        self.virtual_times: Dict[str, float] = {}
        self.global_virtual_time = 0.0

        # Deficit Round Robin state
        self.deficits: Dict[str, float] = {}
        self.quantum_sizes: Dict[str, float] = {}

        # Statistics
        self._stats = {
            "total_users": 0,
            "total_groups": 0,
            "resource_violations": 0,
            "fair_share_violations": 0,
            "average_fairness_index": 1.0,
        }

        # Update interval
        self.update_interval = 60.0  # 1 minute
        self._running = False

    async def initialize(self) -> None:
        """Initialize the fair share manager"""
        self.logger.info(f"Initializing fair share manager with model: {self.model.value}")

        # Create default user if none exist
        if not self.users:
            await self.add_user("default", shares=1.0)

        self._running = True

    async def add_user(
        self,
        user_id: str,
        shares: float = 1.0,
        priority_boost: float = 1.0,
        quota_limits: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> bool:
        """Add a new user account"""
        if user_id in self.users:
            self.logger.warning(f"User {user_id} already exists")
            return False

        # Validate shares
        shares = max(self.min_shares, min(shares, self.max_shares))
        priority_boost = max(0.1, min(priority_boost, self.priority_boost_max))

        user = UserAccount(user_id=user_id, shares=shares, priority_boost=priority_boost)

        self.users[user_id] = user
        self._stats["total_users"] += 1

        # Set up quotas if provided
        if quota_limits:
            self.quotas[user_id] = {}
            for resource_type, (soft_limit, hard_limit) in quota_limits.items():
                quota = ResourceQuota(
                    resource_type=resource_type, soft_limit=soft_limit, hard_limit=hard_limit
                )
                self.quotas[user_id][resource_type] = quota

        # Initialize algorithm-specific state
        self.lottery_tickets[user_id] = int(shares * 100)  # Convert to tickets
        self.total_tickets += self.lottery_tickets[user_id]

        self.virtual_times[user_id] = self.global_virtual_time
        self.deficits[user_id] = 0.0
        self.quantum_sizes[user_id] = shares

        self.logger.info(f"Added user {user_id} with {shares} shares")
        return True

    async def add_group(
        self, group_id: str, shares: float = 1.0, parent_group: Optional[str] = None
    ) -> bool:
        """Add a new group account"""
        if group_id in self.groups:
            self.logger.warning(f"Group {group_id} already exists")
            return False

        if parent_group and parent_group not in self.groups:
            self.logger.error(f"Parent group {parent_group} does not exist")
            return False

        group = GroupAccount(group_id=group_id, shares=shares, parent_group=parent_group)

        self.groups[group_id] = group
        self._stats["total_groups"] += 1

        # Add to parent group if specified
        if parent_group:
            self.groups[parent_group].subgroups.append(group_id)

        self.logger.info(f"Added group {group_id} with {shares} shares")
        return True

    async def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Add a user to a group"""
        if user_id not in self.users:
            self.logger.error(f"User {user_id} does not exist")
            return False

        if group_id not in self.groups:
            self.logger.error(f"Group {group_id} does not exist")
            return False

        if group_id not in self.users[user_id].group_memberships:
            self.users[user_id].group_memberships.append(group_id)
            self.groups[group_id].members.append(user_id)

            self.logger.info(f"Added user {user_id} to group {group_id}")
            return True

        return False

    async def check_quota(self, user_id: str, resource_requirements: Dict[str, Any]) -> bool:
        """Check if user is within resource quotas"""
        if user_id not in self.users:
            # Allow unknown users with default quotas
            return True

        user_quotas = self.quotas.get(user_id, {})

        for resource_type, required_amount in resource_requirements.items():
            if required_amount <= 0:
                continue

            quota = user_quotas.get(resource_type)
            if not quota:
                continue  # No quota limit for this resource

            # Check hard limit
            projected_usage = quota.current_usage + required_amount
            if projected_usage > quota.hard_limit:
                self.logger.warning(
                    f"User {user_id} would exceed hard limit for {resource_type}: "
                    f"{projected_usage} > {quota.hard_limit}"
                )
                self._stats["resource_violations"] += 1
                return False

        return True

    async def update_usage(
        self, user_id: str, resource_usage: Dict[str, float], duration: float
    ) -> None:
        """Update resource usage for a user"""
        current_time = time.time()

        if user_id not in self.users:
            await self.add_user(user_id)

        user = self.users[user_id]

        # Calculate total resource seconds
        total_resource_seconds = sum(
            amount * duration for amount in resource_usage.values() if amount > 0
        )

        # Update usage history
        user.usage_history.append((current_time, total_resource_seconds))
        user.accumulated_usage += total_resource_seconds

        # Update quotas
        user_quotas = self.quotas.get(user_id, {})
        for resource_type, amount in resource_usage.items():
            if amount <= 0:
                continue

            quota = user_quotas.get(resource_type)
            if quota:
                quota.current_usage += amount * duration
                quota.peak_usage = max(quota.peak_usage, quota.current_usage)

        # Clean up old usage history (keep last 7 days)
        cutoff_time = current_time - 7 * 86400
        user.usage_history = [
            (timestamp, usage) for timestamp, usage in user.usage_history if timestamp > cutoff_time
        ]

        self.logger.debug(
            f"Updated usage for user {user_id}: {total_resource_seconds} resource-seconds"
        )

    async def get_user_priority(self, user_id: str) -> float:
        """Get current priority for a user"""
        if user_id not in self.users:
            return 1.0  # Default priority

        user = self.users[user_id]
        current_time = time.time()

        if self.model == FairShareModel.PROPORTIONAL:
            return user.effective_priority(current_time, self.decay_rate)
        elif self.model == FairShareModel.LOTTERY:
            return self.lottery_tickets.get(user_id, 1) / max(self.total_tickets, 1)
        elif self.model == FairShareModel.WEIGHTED_FAIR_QUEUING:
            return user.shares
        elif self.model == FairShareModel.DEFICIT_ROUND_ROBIN:
            return self.deficits.get(user_id, 0.0) + self.quantum_sizes.get(user_id, 1.0)

        return 1.0

    async def select_next_user(self, candidate_users: List[str]) -> Optional[str]:
        """Select next user to schedule based on fair share algorithm"""
        if not candidate_users:
            return None

        if self.model == FairShareModel.PROPORTIONAL:
            return await self._proportional_select(candidate_users)
        elif self.model == FairShareModel.LOTTERY:
            return await self._lottery_select(candidate_users)
        elif self.model == FairShareModel.WEIGHTED_FAIR_QUEUING:
            return await self._wfq_select(candidate_users)
        elif self.model == FairShareModel.DEFICIT_ROUND_ROBIN:
            return await self._drr_select(candidate_users)

        # Default to proportional
        return await self._proportional_select(candidate_users)

    async def _proportional_select(self, candidate_users: List[str]) -> Optional[str]:
        """Proportional fair share selection"""
        best_user = None
        highest_priority = 0.0

        current_time = time.time()

        for user_id in candidate_users:
            if user_id in self.users:
                priority = self.users[user_id].effective_priority(current_time, self.decay_rate)
                if priority > highest_priority:
                    highest_priority = priority
                    best_user = user_id

        return best_user or candidate_users[0]

    async def _lottery_select(self, candidate_users: List[str]) -> Optional[str]:
        """Lottery scheduling selection"""
        import random

        # Calculate total tickets for candidates
        total_candidate_tickets = sum(
            self.lottery_tickets.get(user_id, 1) for user_id in candidate_users
        )

        if total_candidate_tickets == 0:
            return candidate_users[0]

        # Draw winning ticket
        winning_ticket = random.randint(1, total_candidate_tickets)

        # Find winner
        cumulative = 0
        for user_id in candidate_users:
            cumulative += self.lottery_tickets.get(user_id, 1)
            if cumulative >= winning_ticket:
                return user_id

        return candidate_users[-1]

    async def _wfq_select(self, candidate_users: List[str]) -> Optional[str]:
        """Weighted Fair Queuing selection"""
        best_user = None
        earliest_finish_time = float("inf")

        for user_id in candidate_users:
            user_virtual_time = self.virtual_times.get(user_id, self.global_virtual_time)
            user_shares = self.users.get(user_id, UserAccount(user_id)).shares

            # Calculate finish time (simplified)
            finish_time = user_virtual_time + (1.0 / user_shares)

            if finish_time < earliest_finish_time:
                earliest_finish_time = finish_time
                best_user = user_id

        # Update virtual time for selected user
        if best_user:
            self.virtual_times[best_user] = earliest_finish_time

        return best_user

    async def _drr_select(self, candidate_users: List[str]) -> Optional[str]:
        """Deficit Round Robin selection"""
        for user_id in candidate_users:
            deficit = self.deficits.get(user_id, 0.0)
            quantum = self.quantum_sizes.get(user_id, 1.0)

            # Add quantum to deficit
            self.deficits[user_id] = deficit + quantum

            # If deficit is sufficient, select this user
            if self.deficits[user_id] >= 1.0:
                self.deficits[user_id] -= 1.0  # Consume one unit
                return user_id

        # If no user has sufficient deficit, select first
        return candidate_users[0] if candidate_users else None

    async def update_allocations(self) -> None:
        """Update fair share allocations based on recent usage"""
        current_time = time.time()

        # Reset quotas that have passed their reset period
        for user_id, user_quotas in self.quotas.items():
            for quota in user_quotas.values():
                if current_time - quota.last_reset >= quota.reset_period:
                    quota.current_usage = 0.0
                    quota.last_reset = current_time

        # Update global virtual time (WFQ)
        if self.model == FairShareModel.WEIGHTED_FAIR_QUEUING:
            self.global_virtual_time = time.time()

        # Calculate fairness metrics
        await self._calculate_fairness_metrics()

    async def _calculate_fairness_metrics(self) -> None:
        """Calculate system fairness metrics"""
        if not self.users:
            return

        current_time = time.time()

        # Calculate Jain's fairness index
        usage_ratios = []

        for user in self.users.values():
            if user.shares > 0:
                effective_usage = sum(
                    usage
                    for timestamp, usage in user.usage_history
                    if current_time - timestamp <= 3600  # Last hour
                )
                usage_ratio = effective_usage / user.shares
                usage_ratios.append(usage_ratio)

        if usage_ratios:
            # Jain's fairness index
            n = len(usage_ratios)
            sum_ratios = sum(usage_ratios)
            sum_squares = sum(ratio**2 for ratio in usage_ratios)

            if sum_squares > 0:
                fairness_index = (sum_ratios**2) / (n * sum_squares)
                self._stats["average_fairness_index"] = fairness_index

    async def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific user"""
        if user_id not in self.users:
            return None

        user = self.users[user_id]
        current_time = time.time()

        # Calculate recent usage
        recent_usage = sum(
            usage
            for timestamp, usage in user.usage_history
            if current_time - timestamp <= 3600  # Last hour
        )

        # Get quota status
        quota_status = {}
        user_quotas = self.quotas.get(user_id, {})
        for resource_type, quota in user_quotas.items():
            quota_status[resource_type] = {
                "current_usage": quota.current_usage,
                "soft_limit": quota.soft_limit,
                "hard_limit": quota.hard_limit,
                "peak_usage": quota.peak_usage,
                "utilization_percent": (
                    (quota.current_usage / quota.hard_limit * 100) if quota.hard_limit > 0 else 0
                ),
            }

        return {
            "user_id": user_id,
            "shares": user.shares,
            "priority_boost": user.priority_boost,
            "current_priority": await self.get_user_priority(user_id),
            "recent_usage": recent_usage,
            "accumulated_usage": user.accumulated_usage,
            "quota_status": quota_status,
            "group_memberships": user.group_memberships,
        }

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide fair share statistics"""
        return {
            **self._stats,
            "algorithm": self.model.value,
            "total_tickets": self.total_tickets,
            "global_virtual_time": self.global_virtual_time,
        }

    async def shutdown(self) -> None:
        """Shutdown the fair share manager"""
        self._running = False
        self.logger.info("Fair share manager shutdown")
