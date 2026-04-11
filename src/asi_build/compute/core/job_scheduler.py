"""
Job Scheduler - Implements various scheduling algorithms and job management
"""

import asyncio
import heapq
import logging
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict, deque


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PREEMPTED = "preempted"


class JobPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BATCH = 5


@dataclass
class Job:
    """Job specification and tracking"""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str = ""
    command: str = ""
    arguments: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    
    # Resource requirements
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    allocated_resources: Optional[Dict[str, Any]] = None
    
    # Scheduling metadata
    priority: int = 3  # 1-5 scale (1 = highest)
    queue: str = "default"
    estimated_duration: Optional[float] = None
    deadline: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)
    
    # Job lifecycle
    status: JobStatus = JobStatus.PENDING
    submitted_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # Progress tracking
    progress: int = 0  # 0-100
    checkpoints: List[str] = field(default_factory=list)
    
    # Preemption and migration
    preempted: bool = False
    preemption_count: int = 0
    migration_count: int = 0
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Gang scheduling
    gang_id: Optional[str] = None
    gang_size: int = 1
    
    @classmethod
    def from_spec(cls, spec: Dict[str, Any]) -> 'Job':
        """Create job from specification dictionary"""
        job = cls()
        
        for key, value in spec.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        # Ensure job_id is set
        if not job.job_id:
            job.job_id = str(uuid.uuid4())
            
        return job
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "name": self.name,
            "command": self.command,
            "arguments": self.arguments,
            "environment": self.environment,
            "resource_requirements": self.resource_requirements,
            "allocated_resources": self.allocated_resources,
            "priority": self.priority,
            "queue": self.queue,
            "estimated_duration": self.estimated_duration,
            "deadline": self.deadline,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "checkpoints": self.checkpoints,
            "preempted": self.preempted,
            "preemption_count": self.preemption_count,
            "migration_count": self.migration_count,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "gang_id": self.gang_id,
            "gang_size": self.gang_size
        }


class SchedulingAlgorithm(Enum):
    FIFO = "fifo"
    PRIORITY = "priority"
    FAIR_SHARE = "fair_share"
    BACKFILL = "backfill"
    GANG = "gang"
    ELASTIC = "elastic"
    DEADLINE = "deadline_aware"
    LOTTERY = "lottery"


@dataclass
class SchedulingPolicy:
    """Scheduling policy configuration"""
    algorithm: SchedulingAlgorithm = SchedulingAlgorithm.FAIR_SHARE
    max_concurrent_jobs: int = 1000
    max_jobs_per_user: int = 100
    backfill_enabled: bool = True
    preemption_enabled: bool = True
    gang_scheduling_enabled: bool = True
    elastic_scaling_enabled: bool = True
    deadline_enforcement: bool = True
    aging_enabled: bool = True  # Increase priority over time
    aging_factor: float = 0.1  # Priority increase per hour


class JobQueue:
    """Priority-based job queue with multiple scheduling strategies"""
    
    def __init__(self, name: str, policy: SchedulingPolicy):
        self.name = name
        self.policy = policy
        self.logger = logging.getLogger(f"queue.{name}")
        
        # Job storage
        self._pending_jobs: List[Tuple[float, int, Job]] = []  # (priority, timestamp, job)
        self._running_jobs: Dict[str, Job] = {}
        self._completed_jobs: deque = deque(maxlen=1000)  # Keep last 1000
        
        # Gang scheduling
        self._gang_groups: Dict[str, List[Job]] = defaultdict(list)
        
        # User tracking
        self._user_jobs: Dict[str, Set[str]] = defaultdict(set)
        
        # Statistics
        self._stats = {
            "jobs_submitted": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "average_wait_time": 0.0,
            "average_turnaround_time": 0.0
        }
    
    def submit_job(self, job: Job) -> bool:
        """Submit a job to the queue"""
        # Check user limits
        if len(self._user_jobs.get(job.user_id, set())) >= self.policy.max_jobs_per_user:
            self.logger.warning(f"User {job.user_id} has reached job limit")
            return False
        
        # Check queue capacity
        if len(self._pending_jobs) + len(self._running_jobs) >= self.policy.max_concurrent_jobs:
            self.logger.warning("Queue is at capacity")
            return False
        
        # Calculate effective priority (with aging if enabled)
        effective_priority = job.priority
        if self.policy.aging_enabled:
            age_hours = (time.time() - job.submitted_at) / 3600.0
            effective_priority -= age_hours * self.policy.aging_factor
            effective_priority = max(1, effective_priority)  # Min priority is 1
        
        # Add to pending queue
        heapq.heappush(self._pending_jobs, (effective_priority, job.submitted_at, job))
        self._user_jobs[job.user_id].add(job.job_id)
        
        # Handle gang scheduling
        if job.gang_id and self.policy.gang_scheduling_enabled:
            self._gang_groups[job.gang_id].append(job)
        
        self._stats["jobs_submitted"] += 1
        self.logger.info(f"Submitted job {job.job_id} with priority {effective_priority}")
        
        return True
    
    def get_next_job(self, resource_availability: Dict[str, Any]) -> Optional[Job]:
        """Get the next job to schedule based on the policy"""
        if self.policy.algorithm == SchedulingAlgorithm.FIFO:
            return self._fifo_schedule()
        elif self.policy.algorithm == SchedulingAlgorithm.PRIORITY:
            return self._priority_schedule()
        elif self.policy.algorithm == SchedulingAlgorithm.FAIR_SHARE:
            return self._fair_share_schedule()
        elif self.policy.algorithm == SchedulingAlgorithm.BACKFILL:
            return self._backfill_schedule(resource_availability)
        elif self.policy.algorithm == SchedulingAlgorithm.GANG:
            return self._gang_schedule()
        elif self.policy.algorithm == SchedulingAlgorithm.DEADLINE:
            return self._deadline_schedule()
        else:
            return self._priority_schedule()  # Default
    
    def _fifo_schedule(self) -> Optional[Job]:
        """First In, First Out scheduling"""
        while self._pending_jobs:
            priority, timestamp, job = heapq.heappop(self._pending_jobs)
            
            if job.status == JobStatus.PENDING:
                return job
        
        return None
    
    def _priority_schedule(self) -> Optional[Job]:
        """Priority-based scheduling"""
        return self._fifo_schedule()  # Priority queue already handles this
    
    def _fair_share_schedule(self) -> Optional[Job]:
        """Fair share scheduling - balance resources among users"""
        if not self._pending_jobs:
            return None
        
        # Count running jobs per user
        user_running_counts = defaultdict(int)
        for job in self._running_jobs.values():
            user_running_counts[job.user_id] += 1
        
        # Find user with least running jobs
        min_running = min(user_running_counts.values()) if user_running_counts else 0
        
        # Look for jobs from users with minimal running jobs
        pending_jobs_copy = list(self._pending_jobs)
        pending_jobs_copy.sort()  # Sort by priority
        
        for i, (priority, timestamp, job) in enumerate(pending_jobs_copy):
            if job.status == JobStatus.PENDING:
                user_running = user_running_counts.get(job.user_id, 0)
                if user_running <= min_running:
                    # Remove from heap
                    self._pending_jobs.remove((priority, timestamp, job))
                    heapq.heapify(self._pending_jobs)
                    return job
        
        # Fallback to priority scheduling
        return self._priority_schedule()
    
    def _backfill_schedule(self, resource_availability: Dict[str, Any]) -> Optional[Job]:
        """Backfill scheduling - fill gaps with smaller jobs"""
        if not self._pending_jobs:
            return None
        
        # First try to schedule highest priority job
        high_priority_job = self._priority_schedule()
        if high_priority_job:
            # Check if it can run now
            if self._can_job_run(high_priority_job, resource_availability):
                return high_priority_job
            else:
                # Put it back and try backfill
                self._pending_jobs.insert(0, (high_priority_job.priority, high_priority_job.submitted_at, high_priority_job))
                heapq.heapify(self._pending_jobs)
        
        # Try to backfill with smaller jobs
        pending_jobs_copy = list(self._pending_jobs)
        for i, (priority, timestamp, job) in enumerate(pending_jobs_copy):
            if job.status == JobStatus.PENDING and self._can_job_run(job, resource_availability):
                # Remove from heap
                self._pending_jobs.remove((priority, timestamp, job))
                heapq.heapify(self._pending_jobs)
                return job
        
        return None
    
    def _gang_schedule(self) -> Optional[Job]:
        """Gang scheduling - schedule related jobs together"""
        if not self.policy.gang_scheduling_enabled:
            return self._priority_schedule()
        
        # Check for complete gangs ready to run
        for gang_id, gang_jobs in self._gang_groups.items():
            if not gang_jobs:
                continue
            
            # Check if all gang members are pending
            pending_gang_jobs = [job for job in gang_jobs if job.status == JobStatus.PENDING]
            
            if len(pending_gang_jobs) == gang_jobs[0].gang_size:
                # All gang members are ready, return the first one
                job = pending_gang_jobs[0]
                
                # Remove from pending queue
                for priority, timestamp, queued_job in list(self._pending_jobs):
                    if queued_job.job_id == job.job_id:
                        self._pending_jobs.remove((priority, timestamp, queued_job))
                        break
                heapq.heapify(self._pending_jobs)
                
                return job
        
        # Fallback to single job scheduling
        return self._priority_schedule()
    
    def _deadline_schedule(self) -> Optional[Job]:
        """Deadline-aware scheduling - prioritize jobs approaching deadlines"""
        if not self._pending_jobs:
            return None
        
        current_time = time.time()
        urgent_jobs = []
        
        # Find jobs with approaching deadlines
        for priority, timestamp, job in self._pending_jobs:
            if job.status == JobStatus.PENDING and job.deadline:
                time_to_deadline = job.deadline - current_time
                urgency_score = 1.0 / max(time_to_deadline, 1.0)  # Higher score = more urgent
                urgent_jobs.append((urgency_score, priority, timestamp, job))
        
        if urgent_jobs:
            # Sort by urgency (highest first)
            urgent_jobs.sort(reverse=True)
            urgency_score, priority, timestamp, job = urgent_jobs[0]
            
            # Remove from pending queue
            self._pending_jobs.remove((priority, timestamp, job))
            heapq.heapify(self._pending_jobs)
            
            return job
        
        # No deadline-constrained jobs, use priority scheduling
        return self._priority_schedule()
    
    def _can_job_run(self, job: Job, resource_availability: Dict[str, Any]) -> bool:
        """Check if a job can run with current resource availability"""
        required = job.resource_requirements
        
        for resource, amount in required.items():
            if amount > 0:
                available = resource_availability.get(resource, 0)
                if available < amount:
                    return False
        
        return True
    
    def start_job(self, job: Job) -> bool:
        """Mark a job as running"""
        if job.job_id not in self._running_jobs:
            job.status = JobStatus.RUNNING
            job.started_at = time.time()
            self._running_jobs[job.job_id] = job
            
            self.logger.info(f"Started job {job.job_id}")
            return True
        
        return False
    
    def complete_job(self, job_id: str, success: bool = True) -> bool:
        """Mark a job as completed"""
        if job_id in self._running_jobs:
            job = self._running_jobs.pop(job_id)
            job.completed_at = time.time()
            
            if success:
                job.status = JobStatus.COMPLETED
                self._stats["jobs_completed"] += 1
            else:
                job.status = JobStatus.FAILED
                self._stats["jobs_failed"] += 1
            
            # Update statistics
            if job.started_at:
                turnaround_time = job.completed_at - job.submitted_at
                wait_time = job.started_at - job.submitted_at
                
                # Running average
                count = self._stats["jobs_completed"] + self._stats["jobs_failed"]
                self._stats["average_wait_time"] = (
                    (self._stats["average_wait_time"] * (count - 1) + wait_time) / count
                )
                self._stats["average_turnaround_time"] = (
                    (self._stats["average_turnaround_time"] * (count - 1) + turnaround_time) / count
                )
            
            # Clean up user tracking
            self._user_jobs[job.user_id].discard(job_id)
            
            # Clean up gang scheduling
            if job.gang_id and job.gang_id in self._gang_groups:
                gang_jobs = self._gang_groups[job.gang_id]
                self._gang_groups[job.gang_id] = [j for j in gang_jobs if j.job_id != job_id]
                if not self._gang_groups[job.gang_id]:
                    del self._gang_groups[job.gang_id]
            
            self._completed_jobs.append(job)
            self.logger.info(f"Completed job {job_id} with status {job.status.value}")
            
            return True
        
        return False
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job"""
        # Check running jobs
        if job_id in self._running_jobs:
            job = self._running_jobs.pop(job_id)
            job.status = JobStatus.CANCELLED
            job.completed_at = time.time()
            self._completed_jobs.append(job)
            
            # Clean up user tracking
            self._user_jobs[job.user_id].discard(job_id)
            
            self.logger.info(f"Cancelled running job {job_id}")
            return True
        
        # Check pending jobs
        for i, (priority, timestamp, job) in enumerate(self._pending_jobs):
            if job.job_id == job_id:
                job.status = JobStatus.CANCELLED
                job.completed_at = time.time()
                self._pending_jobs.pop(i)
                heapq.heapify(self._pending_jobs)
                
                # Clean up user tracking
                self._user_jobs[job.user_id].discard(job_id)
                
                self._completed_jobs.append(job)
                self.logger.info(f"Cancelled pending job {job_id}")
                return True
        
        return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "name": self.name,
            "policy": self.policy.algorithm.value,
            "pending_jobs": len(self._pending_jobs),
            "running_jobs": len(self._running_jobs),
            "completed_jobs": len(self._completed_jobs),
            "statistics": self._stats.copy(),
            "gang_groups": len(self._gang_groups)
        }


class JobScheduler:
    """
    Main job scheduler that manages multiple queues and implements
    advanced scheduling algorithms
    """
    
    def __init__(self, max_concurrent_jobs: int = 1000):
        self.logger = logging.getLogger("job_scheduler")
        self.max_concurrent_jobs = max_concurrent_jobs
        
        # Job queues
        self.queues: Dict[str, JobQueue] = {}
        self.default_queue_name = "default"
        
        # Global job tracking
        self.all_jobs: Dict[str, Job] = {}
        
        # Elastic scheduling
        self._elastic_jobs: Dict[str, List[Job]] = {}  # Scalable job groups
        
        # Statistics
        self._global_stats = {
            "total_jobs": 0,
            "active_queues": 0,
            "total_throughput": 0.0
        }
        
    async def initialize(self) -> None:
        """Initialize the job scheduler"""
        self.logger.info("Initializing job scheduler")
        
        # Create default queue
        default_policy = SchedulingPolicy()
        await self.create_queue(self.default_queue_name, default_policy)
        
    async def create_queue(self, name: str, policy: SchedulingPolicy) -> bool:
        """Create a new job queue"""
        if name in self.queues:
            self.logger.warning(f"Queue {name} already exists")
            return False
        
        queue = JobQueue(name, policy)
        self.queues[name] = queue
        self._global_stats["active_queues"] += 1
        
        self.logger.info(f"Created queue: {name} with policy: {policy.algorithm.value}")
        return True
    
    async def submit_job(self, job_spec: Dict[str, Any], queue_name: Optional[str] = None) -> str:
        """Submit a job to a specific queue"""
        job = Job.from_spec(job_spec)
        queue_name = queue_name or job.queue or self.default_queue_name
        
        if queue_name not in self.queues:
            raise ValueError(f"Queue {queue_name} does not exist")
        
        queue = self.queues[queue_name]
        
        if queue.submit_job(job):
            self.all_jobs[job.job_id] = job
            self._global_stats["total_jobs"] += 1
            
            self.logger.info(f"Submitted job {job.job_id} to queue {queue_name}")
            return job.job_id
        else:
            raise RuntimeError(f"Failed to submit job to queue {queue_name}")
    
    async def get_next_jobs(self, resource_availability: Dict[str, Any]) -> List[Job]:
        """Get next jobs to schedule from all queues"""
        next_jobs = []
        
        # Round-robin through queues (can be made more sophisticated)
        for queue_name, queue in self.queues.items():
            job = queue.get_next_job(resource_availability)
            if job:
                next_jobs.append(job)
        
        return next_jobs
    
    async def start_job(self, job_id: str) -> bool:
        """Start a job"""
        if job_id not in self.all_jobs:
            return False
        
        job = self.all_jobs[job_id]
        queue_name = job.queue or self.default_queue_name
        
        if queue_name in self.queues:
            return self.queues[queue_name].start_job(job)
        
        return False
    
    async def complete_job(self, job_id: str, success: bool = True) -> bool:
        """Complete a job"""
        if job_id not in self.all_jobs:
            return False
        
        job = self.all_jobs[job_id]
        queue_name = job.queue or self.default_queue_name
        
        if queue_name in self.queues:
            return self.queues[queue_name].complete_job(job_id, success)
        
        return False
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        if job_id not in self.all_jobs:
            return False
        
        job = self.all_jobs[job_id]
        queue_name = job.queue or self.default_queue_name
        
        if queue_name in self.queues:
            return self.queues[queue_name].cancel_job(job_id)
        
        return False
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        if job_id in self.all_jobs:
            return self.all_jobs[job_id].to_dict()
        return None
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get comprehensive scheduler status"""
        queue_statuses = {}
        for name, queue in self.queues.items():
            queue_statuses[name] = queue.get_queue_status()
        
        return {
            "queues": queue_statuses,
            "global_statistics": self._global_stats,
            "total_jobs": len(self.all_jobs)
        }
    
    # Elastic scheduling methods
    async def create_elastic_job_group(self, group_id: str, jobs: List[Job]) -> bool:
        """Create a group of jobs that can scale elastically"""
        if group_id in self._elastic_jobs:
            return False
        
        self._elastic_jobs[group_id] = jobs
        self.logger.info(f"Created elastic job group {group_id} with {len(jobs)} jobs")
        
        return True
    
    async def scale_elastic_group(self, group_id: str, target_size: int) -> bool:
        """Scale an elastic job group up or down"""
        if group_id not in self._elastic_jobs:
            return False
        
        current_jobs = self._elastic_jobs[group_id]
        current_size = len([j for j in current_jobs if j.status == JobStatus.RUNNING])
        
        if target_size > current_size:
            # Scale up - start more jobs
            pending_jobs = [j for j in current_jobs if j.status == JobStatus.PENDING]
            jobs_to_start = min(target_size - current_size, len(pending_jobs))
            
            for i in range(jobs_to_start):
                await self.start_job(pending_jobs[i].job_id)
                
        elif target_size < current_size:
            # Scale down - stop some jobs
            running_jobs = [j for j in current_jobs if j.status == JobStatus.RUNNING]
            jobs_to_stop = current_size - target_size
            
            for i in range(jobs_to_stop):
                await self.cancel_job(running_jobs[i].job_id)
        
        self.logger.info(f"Scaled elastic group {group_id} to {target_size} jobs")
        return True