"""
Preemption Manager - Handles job preemption and migration for resource optimization
"""

import asyncio
import heapq
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class PreemptionPolicy(Enum):
    PRIORITY_BASED = "priority"
    FAIR_SHARE = "fair_share"
    DEADLINE_AWARE = "deadline"
    RESOURCE_BASED = "resource"
    COST_BASED = "cost"
    HYBRID = "hybrid"


class MigrationType(Enum):
    CHECKPOINT_RESTART = "checkpoint_restart"
    LIVE_MIGRATION = "live_migration"
    CONTAINER_MIGRATION = "container_migration"
    PROCESS_MIGRATION = "process_migration"


@dataclass
class PreemptionCandidate:
    """Candidate job for preemption"""

    job_id: str
    current_priority: float
    resource_usage: Dict[str, float]
    runtime: float
    checkpoint_cost: float
    preemption_cost: float
    migration_feasible: bool = False
    score: float = 0.0  # Higher score = better candidate for preemption

    def __lt__(self, other):
        return self.score > other.score  # Reverse for max-heap behavior


@dataclass
class MigrationPlan:
    """Migration plan for a job"""

    job_id: str
    source_node: str
    target_node: str
    migration_type: MigrationType
    estimated_duration: float
    estimated_cost: float
    checkpoint_size: int  # bytes
    network_bandwidth_required: float  # Mbps
    success_probability: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "migration_type": self.migration_type.value,
            "estimated_duration": self.estimated_duration,
            "estimated_cost": self.estimated_cost,
            "checkpoint_size": self.checkpoint_size,
            "network_bandwidth_required": self.network_bandwidth_required,
            "success_probability": self.success_probability,
        }


class PreemptionManager:
    """
    Advanced preemption manager supporting multiple preemption policies
    and intelligent migration strategies
    """

    def __init__(self, policy: PreemptionPolicy = PreemptionPolicy.HYBRID):
        self.policy = policy
        self.logger = logging.getLogger("preemption_manager")

        # Preemption parameters
        self.preemption_threshold = 0.8  # Resource utilization threshold for preemption
        self.min_runtime_for_preemption = 60.0  # Minimum runtime before considering preemption
        self.preemption_cooldown = 300.0  # 5 minutes between preemptions of same job
        self.migration_success_threshold = 0.7  # Minimum migration success probability

        # Job tracking
        self.running_jobs: Dict[str, Any] = {}  # job_id -> job info
        self.preempted_jobs: Dict[str, float] = {}  # job_id -> last preemption time
        self.migration_history: List[MigrationPlan] = []

        # Node and resource tracking
        self.node_resources: Dict[str, Dict[str, float]] = {}
        self.node_loads: Dict[str, float] = {}

        # Preemption statistics
        self._stats = {
            "total_preemptions": 0,
            "successful_preemptions": 0,
            "failed_preemptions": 0,
            "total_migrations": 0,
            "successful_migrations": 0,
            "failed_migrations": 0,
            "average_preemption_time": 0.0,
            "average_migration_time": 0.0,
            "resource_savings": 0.0,
        }

    async def initialize(self) -> None:
        """Initialize the preemption manager"""
        self.logger.info(f"Initializing preemption manager with policy: {self.policy.value}")

    async def find_preemption_candidates(
        self,
        running_jobs: List[Any],
        pending_jobs: List[str],
        resource_pressure: Optional[Dict[str, float]] = None,
    ) -> List[Any]:
        """
        Find jobs that should be preempted to make room for higher priority jobs
        """
        if not pending_jobs:
            return []

        candidates = []
        current_time = time.time()

        # Analyze resource pressure
        if not resource_pressure:
            resource_pressure = await self._calculate_resource_pressure()

        # Skip if no significant resource pressure
        if max(resource_pressure.values()) < self.preemption_threshold:
            return []

        # Evaluate each running job as a potential preemption candidate
        for job in running_jobs:
            if not self._is_preemptible(job, current_time):
                continue

            candidate = await self._evaluate_preemption_candidate(job, resource_pressure)
            if candidate and candidate.score > 0:
                candidates.append(candidate)

        # Sort candidates by score (best candidates first)
        candidates.sort(reverse=True, key=lambda x: x.score)

        # Apply policy-specific selection
        selected = await self._apply_preemption_policy(candidates, pending_jobs)

        return [
            self._find_job_by_id(job_id, running_jobs)
            for job_id in selected
            if self._find_job_by_id(job_id, running_jobs)
        ]

    def _find_job_by_id(self, job_id: str, job_list: List[Any]) -> Optional[Any]:
        """Find job by ID in job list"""
        for job in job_list:
            if hasattr(job, "job_id") and job.job_id == job_id:
                return job
        return None

    def _is_preemptible(self, job: Any, current_time: float) -> bool:
        """Check if a job is eligible for preemption"""
        # Check minimum runtime
        if hasattr(job, "started_at") and job.started_at:
            runtime = current_time - job.started_at
            if runtime < self.min_runtime_for_preemption:
                return False

        # Check cooldown period
        job_id = getattr(job, "job_id", "")
        if job_id in self.preempted_jobs:
            time_since_preemption = current_time - self.preempted_jobs[job_id]
            if time_since_preemption < self.preemption_cooldown:
                return False

        # Check preemption count
        if hasattr(job, "preemption_count") and job.preemption_count >= 3:
            return False  # Avoid repeated preemption

        return True

    async def _evaluate_preemption_candidate(
        self, job: Any, resource_pressure: Dict[str, float]
    ) -> Optional[PreemptionCandidate]:
        """Evaluate a job as a preemption candidate"""
        try:
            job_id = getattr(job, "job_id", "")
            priority = getattr(job, "priority", 5)
            started_at = getattr(job, "started_at", time.time())
            resource_requirements = getattr(job, "resource_requirements", {})

            current_time = time.time()
            runtime = current_time - started_at if started_at else 0

            # Calculate resource usage
            resource_usage = {}
            for resource, amount in resource_requirements.items():
                resource_usage[resource] = amount

            # Estimate costs
            checkpoint_cost = await self._estimate_checkpoint_cost(job)
            preemption_cost = await self._estimate_preemption_cost(job, runtime)
            migration_feasible = await self._is_migration_feasible(job)

            candidate = PreemptionCandidate(
                job_id=job_id,
                current_priority=priority,
                resource_usage=resource_usage,
                runtime=runtime,
                checkpoint_cost=checkpoint_cost,
                preemption_cost=preemption_cost,
                migration_feasible=migration_feasible,
            )

            # Calculate preemption score based on policy
            candidate.score = await self._calculate_preemption_score(candidate, resource_pressure)

            return candidate

        except Exception as e:
            self.logger.error(f"Error evaluating preemption candidate: {e}")
            return None

    async def _calculate_preemption_score(
        self, candidate: PreemptionCandidate, resource_pressure: Dict[str, float]
    ) -> float:
        """Calculate preemption score based on policy"""
        base_score = 0.0

        if self.policy == PreemptionPolicy.PRIORITY_BASED:
            # Lower priority jobs have higher preemption score
            base_score = 10.0 - candidate.current_priority

        elif self.policy == PreemptionPolicy.RESOURCE_BASED:
            # Jobs using heavily pressured resources have higher score
            resource_score = 0.0
            for resource, usage in candidate.resource_usage.items():
                pressure = resource_pressure.get(resource, 0.0)
                resource_score += usage * pressure
            base_score = resource_score

        elif self.policy == PreemptionPolicy.COST_BASED:
            # Jobs with lower preemption cost have higher score
            if candidate.preemption_cost > 0:
                base_score = 100.0 / candidate.preemption_cost

        elif self.policy == PreemptionPolicy.HYBRID:
            # Combine multiple factors
            priority_score = (10.0 - candidate.current_priority) * 2.0

            resource_score = 0.0
            for resource, usage in candidate.resource_usage.items():
                pressure = resource_pressure.get(resource, 0.0)
                resource_score += usage * pressure

            cost_score = 10.0 / max(candidate.preemption_cost, 1.0)

            # Runtime factor - prefer jobs that have run longer
            runtime_score = min(candidate.runtime / 3600.0, 5.0)  # Cap at 5 hours

            base_score = priority_score + resource_score + cost_score + runtime_score

        # Boost score if migration is feasible
        if candidate.migration_feasible:
            base_score *= 1.2

        return max(0.0, base_score)

    async def _apply_preemption_policy(
        self, candidates: List[PreemptionCandidate], pending_jobs: List[str]
    ) -> List[str]:
        """Apply policy-specific preemption selection"""
        selected = []

        # For now, select top candidates based on score
        # This could be enhanced with more sophisticated policies

        max_preemptions = min(len(candidates), len(pending_jobs), 5)  # Limit concurrent preemptions

        for i in range(max_preemptions):
            if i < len(candidates):
                selected.append(candidates[i].job_id)

        return selected

    async def plan_migration(
        self, job: Any, target_nodes: Optional[List[str]] = None
    ) -> Optional[MigrationPlan]:
        """Plan migration for a job"""
        try:
            job_id = getattr(job, "job_id", "")
            current_node = getattr(job, "node_id", "unknown")

            if not target_nodes:
                target_nodes = await self._find_suitable_target_nodes(job)

            if not target_nodes:
                self.logger.warning(f"No suitable target nodes found for job {job_id}")
                return None

            best_plan = None
            best_score = 0.0

            for target_node in target_nodes:
                plan = await self._create_migration_plan(job, current_node, target_node)
                if plan:
                    score = await self._score_migration_plan(plan)
                    if score > best_score:
                        best_score = score
                        best_plan = plan

            return best_plan

        except Exception as e:
            self.logger.error(f"Error planning migration for job {job_id}: {e}")
            return None

    async def _create_migration_plan(
        self, job: Any, source_node: str, target_node: str
    ) -> Optional[MigrationPlan]:
        """Create detailed migration plan"""
        try:
            job_id = getattr(job, "job_id", "")

            # Determine migration type
            migration_type = await self._determine_migration_type(job)

            # Estimate checkpoint size
            checkpoint_size = await self._estimate_checkpoint_size(job)

            # Estimate network bandwidth requirement
            network_bandwidth = await self._estimate_network_bandwidth_requirement(
                checkpoint_size, migration_type
            )

            # Estimate migration duration
            duration = await self._estimate_migration_duration(
                checkpoint_size, network_bandwidth, migration_type
            )

            # Estimate migration cost
            cost = await self._estimate_migration_cost(duration, checkpoint_size, migration_type)

            # Calculate success probability
            success_probability = await self._calculate_migration_success_probability(
                source_node, target_node, migration_type, checkpoint_size
            )

            plan = MigrationPlan(
                job_id=job_id,
                source_node=source_node,
                target_node=target_node,
                migration_type=migration_type,
                estimated_duration=duration,
                estimated_cost=cost,
                checkpoint_size=checkpoint_size,
                network_bandwidth_required=network_bandwidth,
                success_probability=success_probability,
            )

            return plan

        except Exception as e:
            self.logger.error(f"Error creating migration plan: {e}")
            return None

    async def execute_migration(self, plan: MigrationPlan) -> bool:
        """Execute a migration plan"""
        start_time = time.time()
        self._stats["total_migrations"] += 1

        try:
            self.logger.info(
                f"Starting migration of job {plan.job_id} from {plan.source_node} to {plan.target_node}"
            )

            # Step 1: Create checkpoint
            checkpoint_success = await self._create_checkpoint(plan.job_id, plan.checkpoint_size)
            if not checkpoint_success:
                raise RuntimeError("Checkpoint creation failed")

            # Step 2: Transfer checkpoint to target node
            transfer_success = await self._transfer_checkpoint(plan)
            if not transfer_success:
                raise RuntimeError("Checkpoint transfer failed")

            # Step 3: Start job on target node
            restart_success = await self._restart_job_from_checkpoint(plan)
            if not restart_success:
                raise RuntimeError("Job restart failed")

            # Step 4: Cleanup on source node
            await self._cleanup_source_node(plan)

            # Record successful migration
            self.migration_history.append(plan)
            self._stats["successful_migrations"] += 1

            duration = time.time() - start_time
            self._stats["average_migration_time"] = (
                self._stats["average_migration_time"] * (self._stats["total_migrations"] - 1)
                + duration
            ) / self._stats["total_migrations"]

            self.logger.info(f"Successfully migrated job {plan.job_id} in {duration:.2f} seconds")
            return True

        except Exception as e:
            self._stats["failed_migrations"] += 1
            self.logger.error(f"Migration failed for job {plan.job_id}: {e}")

            # Attempt rollback
            await self._rollback_migration(plan)

            return False

    async def _calculate_resource_pressure(self) -> Dict[str, float]:
        """Calculate current resource pressure across the system"""
        # This would integrate with actual resource monitoring
        # For now, return simulated values
        return {"cpu": 0.85, "memory": 0.75, "gpu": 0.90, "storage": 0.60, "network": 0.70}

    async def _estimate_checkpoint_cost(self, job: Any) -> float:
        """Estimate the cost of checkpointing a job"""
        # Factors: checkpoint size, I/O overhead, computation pause time
        return 30.0  # seconds

    async def _estimate_preemption_cost(self, job: Any, runtime: float) -> float:
        """Estimate the total cost of preempting a job"""
        checkpoint_cost = await self._estimate_checkpoint_cost(job)
        restart_cost = 60.0  # Time to restart
        lost_work = min(runtime * 0.1, 300.0)  # 10% of runtime, max 5 minutes

        return checkpoint_cost + restart_cost + lost_work

    async def _is_migration_feasible(self, job: Any) -> bool:
        """Check if migration is feasible for a job"""
        # Check job type, state, dependencies, etc.
        return True  # Simplified for now

    async def _find_suitable_target_nodes(self, job: Any) -> List[str]:
        """Find nodes suitable for migrating a job"""
        # This would analyze node resources, compatibility, etc.
        return ["node1", "node2", "node3"]

    async def _determine_migration_type(self, job: Any) -> MigrationType:
        """Determine the best migration type for a job"""
        # Analyze job characteristics to choose migration strategy
        return MigrationType.CHECKPOINT_RESTART

    async def _estimate_checkpoint_size(self, job: Any) -> int:
        """Estimate checkpoint size in bytes"""
        # Based on job type, memory usage, state size
        return 1024 * 1024 * 100  # 100 MB default

    async def _estimate_network_bandwidth_requirement(
        self, checkpoint_size: int, migration_type: MigrationType
    ) -> float:
        """Estimate network bandwidth requirement in Mbps"""
        if migration_type == MigrationType.LIVE_MIGRATION:
            return 1000.0  # Higher bandwidth for live migration
        else:
            return 100.0  # Lower for checkpoint/restart

    async def _estimate_migration_duration(
        self, checkpoint_size: int, network_bandwidth: float, migration_type: MigrationType
    ) -> float:
        """Estimate migration duration in seconds"""
        transfer_time = (checkpoint_size * 8) / (
            network_bandwidth * 1024 * 1024
        )  # Convert to seconds

        if migration_type == MigrationType.LIVE_MIGRATION:
            return transfer_time + 30.0  # Additional overhead
        else:
            return transfer_time + 120.0  # Checkpoint + restart overhead

    async def _estimate_migration_cost(
        self, duration: float, checkpoint_size: int, migration_type: MigrationType
    ) -> float:
        """Estimate migration cost"""
        base_cost = duration * 0.1  # Time cost
        network_cost = checkpoint_size / (1024 * 1024) * 0.01  # Data transfer cost

        return base_cost + network_cost

    async def _calculate_migration_success_probability(
        self,
        source_node: str,
        target_node: str,
        migration_type: MigrationType,
        checkpoint_size: int,
    ) -> float:
        """Calculate probability of successful migration"""
        base_probability = 0.9

        # Reduce probability for larger checkpoints
        if checkpoint_size > 1024 * 1024 * 1024:  # > 1GB
            base_probability *= 0.8

        # Live migration is less reliable
        if migration_type == MigrationType.LIVE_MIGRATION:
            base_probability *= 0.85

        return base_probability

    async def _score_migration_plan(self, plan: MigrationPlan) -> float:
        """Score a migration plan (higher is better)"""
        success_score = plan.success_probability * 10
        cost_score = max(0, 10 - plan.estimated_cost)
        duration_score = max(0, 10 - plan.estimated_duration / 60.0)

        return success_score + cost_score + duration_score

    # Migration execution methods (simplified implementations)
    async def _create_checkpoint(self, job_id: str, checkpoint_size: int) -> bool:
        """Create checkpoint for job"""
        await asyncio.sleep(1.0)  # Simulate checkpoint creation
        return True

    async def _transfer_checkpoint(self, plan: MigrationPlan) -> bool:
        """Transfer checkpoint to target node"""
        transfer_time = plan.estimated_duration * 0.6  # 60% of total time
        await asyncio.sleep(min(transfer_time, 5.0))  # Simulate transfer
        return True

    async def _restart_job_from_checkpoint(self, plan: MigrationPlan) -> bool:
        """Restart job from checkpoint on target node"""
        await asyncio.sleep(1.0)  # Simulate restart
        return True

    async def _cleanup_source_node(self, plan: MigrationPlan) -> None:
        """Clean up resources on source node"""
        await asyncio.sleep(0.5)  # Simulate cleanup

    async def _rollback_migration(self, plan: MigrationPlan) -> None:
        """Rollback failed migration"""
        self.logger.info(f"Rolling back migration for job {plan.job_id}")
        await asyncio.sleep(1.0)  # Simulate rollback

    async def get_preemption_stats(self) -> Dict[str, Any]:
        """Get preemption and migration statistics"""
        return {
            **self._stats,
            "policy": self.policy.value,
            "active_migrations": len(
                [p for p in self.migration_history if time.time() - p.estimated_duration < 300]
            ),
            "preemption_success_rate": (
                self._stats["successful_preemptions"]
                / max(self._stats["total_preemptions"], 1)
                * 100
            ),
            "migration_success_rate": (
                self._stats["successful_migrations"] / max(self._stats["total_migrations"], 1) * 100
            ),
        }

    async def shutdown(self) -> None:
        """Shutdown the preemption manager"""
        self.logger.info("Preemption manager shutdown")
