"""
Core Compute Pool Manager - Orchestrates resource allocation and job scheduling
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading

from .resource_allocator import ResourceAllocator, ResourceRequest
from .job_scheduler import JobScheduler, Job, JobStatus
from .fair_share import FairShareManager
from .preemption import PreemptionManager
from ..resources.gpu_manager import GPUPoolManager
from ..resources.cpu_manager import CPUPoolManager
from ..resources.memory_manager import MemoryPoolManager
from ..resources.storage_manager import StoragePoolManager
from ..resources.network_manager import NetworkManager
from ..monitoring.metrics_collector import MetricsCollector
from ..fault_tolerance.checkpoint_manager import CheckpointManager
from ..fault_tolerance.recovery_manager import RecoveryManager


class PoolStatus(Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    SHUTDOWN = "shutdown"


@dataclass
class PoolConfig:
    """Configuration for the compute pool"""
    name: str
    max_concurrent_jobs: int = 1000
    resource_timeout: float = 300.0  # 5 minutes
    preemption_enabled: bool = True
    fair_share_enabled: bool = True
    checkpoint_interval: float = 60.0  # 1 minute
    monitoring_interval: float = 10.0  # 10 seconds
    auto_scaling_enabled: bool = True
    providers: List[str] = field(default_factory=lambda: ["local", "kubernetes", "slurm"])
    priority_levels: int = 10


class ComputePoolManager:
    """
    Main orchestrator for the compute resource pooling system.
    
    Manages dynamic resource allocation, job scheduling, monitoring,
    and fault tolerance across multiple compute providers.
    """
    
    def __init__(self, config: PoolConfig):
        self.config = config
        self.pool_id = str(uuid.uuid4())
        self.status = PoolStatus.INITIALIZING
        self.logger = logging.getLogger(f"compute_pool.{config.name}")
        
        # Core components
        self.resource_allocator = ResourceAllocator()
        self.job_scheduler = JobScheduler(config.max_concurrent_jobs)
        self.fair_share_manager = FairShareManager() if config.fair_share_enabled else None
        self.preemption_manager = PreemptionManager() if config.preemption_enabled else None
        
        # Resource managers
        self.gpu_manager = GPUPoolManager()
        self.cpu_manager = CPUPoolManager()
        self.memory_manager = MemoryPoolManager()
        self.storage_manager = StoragePoolManager()
        self.network_manager = NetworkManager()
        
        # Monitoring and fault tolerance
        self.metrics_collector = MetricsCollector(config.monitoring_interval)
        self.checkpoint_manager = CheckpointManager(config.checkpoint_interval)
        self.recovery_manager = RecoveryManager()
        
        # Internal state
        self._active_jobs: Dict[str, Job] = {}
        self._resource_usage: Dict[str, float] = {}
        self._pending_jobs: Set[str] = set()
        self._running: bool = False
        self._shutdown_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=10)
        
        # Statistics
        self._stats = {
            "jobs_submitted": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "jobs_preempted": 0,
            "total_compute_time": 0.0,
            "average_wait_time": 0.0,
            "resource_efficiency": 0.0
        }
    
    async def initialize(self) -> None:
        """Initialize all components of the compute pool"""
        self.logger.info(f"Initializing compute pool: {self.config.name}")
        
        try:
            # Initialize resource managers
            await self.gpu_manager.initialize()
            await self.cpu_manager.initialize()
            await self.memory_manager.initialize()
            await self.storage_manager.initialize()
            await self.network_manager.initialize()
            
            # Initialize core components
            await self.resource_allocator.initialize()
            await self.job_scheduler.initialize()
            
            if self.fair_share_manager:
                await self.fair_share_manager.initialize()
                
            if self.preemption_manager:
                await self.preemption_manager.initialize()
            
            # Initialize monitoring and fault tolerance
            await self.metrics_collector.initialize()
            await self.checkpoint_manager.initialize()
            await self.recovery_manager.initialize()
            
            self.status = PoolStatus.ACTIVE
            self.logger.info("Compute pool initialized successfully")
            
        except Exception as e:
            self.status = PoolStatus.DEGRADED
            self.logger.error(f"Failed to initialize compute pool: {e}")
            raise
    
    async def start(self) -> None:
        """Start the compute pool and all its services"""
        if self.status != PoolStatus.ACTIVE:
            raise RuntimeError("Pool must be initialized before starting")
        
        self._running = True
        self.logger.info("Starting compute pool services")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._job_processing_loop()),
            asyncio.create_task(self._resource_monitoring_loop()),
            asyncio.create_task(self._checkpoint_loop()),
            asyncio.create_task(self._preemption_loop()) if self.preemption_manager else None,
            asyncio.create_task(self._fair_share_loop()) if self.fair_share_manager else None
        ]
        
        # Filter out None tasks
        tasks = [t for t in tasks if t is not None]
        
        await asyncio.gather(*tasks)
    
    async def submit_job(self, job_spec: Dict[str, Any]) -> str:
        """Submit a new job to the compute pool"""
        job = Job.from_spec(job_spec)
        self._stats["jobs_submitted"] += 1
        
        self.logger.info(f"Submitting job {job.job_id} with resources: {job.resource_requirements}")
        
        # Check fair share quotas if enabled
        if self.fair_share_manager:
            if not await self.fair_share_manager.check_quota(job.user_id, job.resource_requirements):
                job.status = JobStatus.REJECTED
                job.error_message = "Fair share quota exceeded"
                return job.job_id
        
        # Add to pending queue
        self._pending_jobs.add(job.job_id)
        self._active_jobs[job.job_id] = job
        
        # Try immediate scheduling
        await self._try_schedule_job(job)
        
        return job.job_id
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or pending job"""
        if job_id not in self._active_jobs:
            return False
        
        job = self._active_jobs[job_id]
        
        if job.status == JobStatus.RUNNING:
            # Stop the job and free resources
            await self._stop_job(job)
            job.status = JobStatus.CANCELLED
        elif job.status == JobStatus.PENDING:
            # Remove from pending queue
            self._pending_jobs.discard(job_id)
            job.status = JobStatus.CANCELLED
        
        self.logger.info(f"Cancelled job {job_id}")
        return True
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a job"""
        if job_id not in self._active_jobs:
            return None
        
        job = self._active_jobs[job_id]
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "submitted_at": job.submitted_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "resource_requirements": job.resource_requirements,
            "allocated_resources": job.allocated_resources,
            "progress": job.progress,
            "error_message": job.error_message
        }
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get comprehensive pool status"""
        resource_utilization = await self._get_resource_utilization()
        
        return {
            "pool_id": self.pool_id,
            "name": self.config.name,
            "status": self.status.value,
            "active_jobs": len([j for j in self._active_jobs.values() if j.status == JobStatus.RUNNING]),
            "pending_jobs": len(self._pending_jobs),
            "total_jobs": len(self._active_jobs),
            "resource_utilization": resource_utilization,
            "statistics": self._stats.copy(),
            "providers": self.config.providers
        }
    
    async def _job_processing_loop(self) -> None:
        """Main job processing loop"""
        while self._running and not self._shutdown_event.is_set():
            try:
                # Process pending jobs
                pending_jobs = list(self._pending_jobs)
                for job_id in pending_jobs:
                    if job_id in self._active_jobs:
                        job = self._active_jobs[job_id]
                        if job.status == JobStatus.PENDING:
                            await self._try_schedule_job(job)
                
                # Check for completed jobs
                completed_jobs = []
                for job_id, job in self._active_jobs.items():
                    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                        completed_jobs.append(job_id)
                
                # Clean up completed jobs
                for job_id in completed_jobs:
                    await self._cleanup_job(job_id)
                
                await asyncio.sleep(1.0)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Error in job processing loop: {e}")
                await asyncio.sleep(5.0)
    
    async def _try_schedule_job(self, job: Job) -> bool:
        """Try to schedule a pending job"""
        try:
            # Check resource availability
            allocation = await self.resource_allocator.allocate_resources(job.resource_requirements)
            
            if allocation:
                # Update job with allocated resources
                job.allocated_resources = allocation.resources
                job.status = JobStatus.RUNNING
                job.started_at = time.time()
                
                # Remove from pending
                self._pending_jobs.discard(job.job_id)
                
                # Start job execution
                await self._start_job(job)
                
                self.logger.info(f"Scheduled job {job.job_id} with allocation: {allocation}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to schedule job {job.job_id}: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            self._stats["jobs_failed"] += 1
        
        return False
    
    async def _start_job(self, job: Job) -> None:
        """Start executing a job"""
        # This would typically involve:
        # 1. Setting up the execution environment
        # 2. Starting the actual workload
        # 3. Monitoring job progress
        
        # For now, simulate job execution
        self._executor.submit(self._simulate_job_execution, job)
    
    def _simulate_job_execution(self, job: Job) -> None:
        """Simulate job execution (replace with real execution logic)"""
        try:
            # Simulate execution time based on resource requirements
            execution_time = job.resource_requirements.get("estimated_duration", 60.0)
            
            # Simulate progress updates
            for i in range(10):
                if job.status != JobStatus.RUNNING:
                    break
                
                time.sleep(execution_time / 10)
                job.progress = (i + 1) * 10
            
            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
                self._stats["jobs_completed"] += 1
                self._stats["total_compute_time"] += execution_time
                
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            self._stats["jobs_failed"] += 1
    
    async def _stop_job(self, job: Job) -> None:
        """Stop a running job and free its resources"""
        if job.allocated_resources:
            await self.resource_allocator.deallocate_resources(job.allocated_resources)
        
        # Additional cleanup logic here
        self.logger.info(f"Stopped job {job.job_id}")
    
    async def _cleanup_job(self, job_id: str) -> None:
        """Clean up a completed job"""
        if job_id in self._active_jobs:
            job = self._active_jobs[job_id]
            
            # Free allocated resources
            if job.allocated_resources:
                await self.resource_allocator.deallocate_resources(job.allocated_resources)
            
            # Update fair share usage
            if self.fair_share_manager and job.status == JobStatus.COMPLETED:
                duration = (job.completed_at - job.started_at) if job.completed_at and job.started_at else 0
                await self.fair_share_manager.update_usage(job.user_id, job.resource_requirements, duration)
            
            # Remove from active jobs after some time (for status queries)
            await asyncio.sleep(300)  # Keep for 5 minutes
            if job_id in self._active_jobs:
                del self._active_jobs[job_id]
    
    async def _resource_monitoring_loop(self) -> None:
        """Monitor resource utilization"""
        while self._running and not self._shutdown_event.is_set():
            try:
                utilization = await self._get_resource_utilization()
                await self.metrics_collector.record_utilization(utilization)
                
                # Check for resource pressure and trigger scaling if needed
                if self.config.auto_scaling_enabled:
                    await self._check_auto_scaling(utilization)
                
                await asyncio.sleep(self.config.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in resource monitoring loop: {e}")
                await asyncio.sleep(30.0)
    
    async def _checkpoint_loop(self) -> None:
        """Periodic checkpointing for fault tolerance"""
        while self._running and not self._shutdown_event.is_set():
            try:
                checkpoint_data = {
                    "active_jobs": {job_id: job.to_dict() for job_id, job in self._active_jobs.items()},
                    "resource_usage": self._resource_usage.copy(),
                    "statistics": self._stats.copy(),
                    "timestamp": time.time()
                }
                
                await self.checkpoint_manager.save_checkpoint(self.pool_id, checkpoint_data)
                await asyncio.sleep(self.config.checkpoint_interval)
                
            except Exception as e:
                self.logger.error(f"Error in checkpoint loop: {e}")
                await asyncio.sleep(60.0)
    
    async def _preemption_loop(self) -> None:
        """Handle job preemption for higher priority jobs"""
        if not self.preemption_manager:
            return
        
        while self._running and not self._shutdown_event.is_set():
            try:
                preemption_candidates = await self.preemption_manager.find_preemption_candidates(
                    list(self._active_jobs.values()),
                    list(self._pending_jobs)
                )
                
                for candidate in preemption_candidates:
                    await self._preempt_job(candidate)
                
                await asyncio.sleep(10.0)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in preemption loop: {e}")
                await asyncio.sleep(30.0)
    
    async def _fair_share_loop(self) -> None:
        """Manage fair share scheduling"""
        if not self.fair_share_manager:
            return
        
        while self._running and not self._shutdown_event.is_set():
            try:
                await self.fair_share_manager.update_allocations()
                await asyncio.sleep(60.0)  # Update every minute
                
            except Exception as e:
                self.logger.error(f"Error in fair share loop: {e}")
                await asyncio.sleep(60.0)
    
    async def _preempt_job(self, job: Job) -> None:
        """Preempt a running job"""
        self.logger.info(f"Preempting job {job.job_id}")
        
        # Save job state for potential resumption
        await self.checkpoint_manager.save_job_checkpoint(job.job_id, job.to_dict())
        
        # Stop the job
        await self._stop_job(job)
        
        # Mark as preempted
        job.status = JobStatus.PENDING
        job.preempted = True
        job.preemption_count += 1
        
        # Add back to pending queue
        self._pending_jobs.add(job.job_id)
        
        self._stats["jobs_preempted"] += 1
    
    async def _get_resource_utilization(self) -> Dict[str, float]:
        """Get current resource utilization across all managers"""
        utilization = {}
        
        utilization.update(await self.gpu_manager.get_utilization())
        utilization.update(await self.cpu_manager.get_utilization())
        utilization.update(await self.memory_manager.get_utilization())
        utilization.update(await self.storage_manager.get_utilization())
        utilization.update(await self.network_manager.get_utilization())
        
        return utilization
    
    async def _check_auto_scaling(self, utilization: Dict[str, float]) -> None:
        """Check if auto-scaling is needed based on resource utilization"""
        # Simple auto-scaling logic - can be made more sophisticated
        avg_utilization = sum(utilization.values()) / len(utilization) if utilization else 0
        
        if avg_utilization > 0.8:  # Scale up if > 80% utilized
            self.logger.info("High resource utilization detected, considering scale up")
            # Trigger scale up logic
            
        elif avg_utilization < 0.2:  # Scale down if < 20% utilized
            self.logger.info("Low resource utilization detected, considering scale down")
            # Trigger scale down logic
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the compute pool"""
        self.logger.info("Shutting down compute pool")
        self.status = PoolStatus.SHUTDOWN
        
        self._running = False
        self._shutdown_event.set()
        
        # Cancel all pending jobs
        for job_id in list(self._pending_jobs):
            await self.cancel_job(job_id)
        
        # Stop all running jobs
        running_jobs = [job for job in self._active_jobs.values() if job.status == JobStatus.RUNNING]
        for job in running_jobs:
            await self._stop_job(job)
        
        # Shutdown components
        await self.metrics_collector.shutdown()
        await self.checkpoint_manager.shutdown()
        await self.recovery_manager.shutdown()
        
        # Shutdown resource managers
        await self.gpu_manager.shutdown()
        await self.cpu_manager.shutdown()
        await self.memory_manager.shutdown()
        await self.storage_manager.shutdown()
        await self.network_manager.shutdown()
        
        self._executor.shutdown(wait=True)
        self.logger.info("Compute pool shutdown complete")