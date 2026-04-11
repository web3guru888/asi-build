#!/usr/bin/env python3
"""
Basic Usage Example - Demonstrates fundamental compute pool operations
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add the compute pool to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.job_scheduler import SchedulingAlgorithm, SchedulingPolicy
from core.pool_manager import ComputePoolManager, PoolConfig
from fault_tolerance.checkpoint_manager import CheckpointPolicy
from monitoring.metrics_collector import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def basic_compute_pool_demo():
    """Demonstrate basic compute pool functionality"""
    logger.info("=== Kenny AGI Compute Pool - Basic Usage Demo ===")

    # 1. Create pool configuration
    pool_config = PoolConfig(
        name="demo_pool",
        max_concurrent_jobs=10,
        resource_timeout=300.0,
        preemption_enabled=True,
        fair_share_enabled=True,
        checkpoint_interval=60.0,
        monitoring_interval=10.0,
        auto_scaling_enabled=True,
        providers=["local"],
        priority_levels=5,
    )

    # 2. Initialize compute pool manager
    pool_manager = ComputePoolManager(pool_config)

    try:
        # Initialize all components
        await pool_manager.initialize()

        # 3. Submit some example jobs
        logger.info("Submitting example jobs...")

        # CPU-intensive job
        cpu_job_spec = {
            "name": "cpu_intensive_job",
            "command": "python -c 'import time; [x**2 for x in range(1000000)]; time.sleep(30)'",
            "resource_requirements": {
                "cpu_cores": 2,
                "memory": 4,  # GB
                "estimated_duration": 45.0,
            },
            "user_id": "demo_user",
            "priority": 2,  # High priority
            "queue": "default",
        }

        cpu_job_id = await pool_manager.submit_job(cpu_job_spec)
        logger.info(f"Submitted CPU job: {cpu_job_id}")

        # Memory-intensive job
        memory_job_spec = {
            "name": "memory_intensive_job",
            "command": "python -c 'data = [i for i in range(10000000)]; import time; time.sleep(20)'",
            "resource_requirements": {
                "cpu_cores": 1,
                "memory": 8,  # GB
                "estimated_duration": 30.0,
            },
            "user_id": "demo_user",
            "priority": 3,  # Normal priority
            "queue": "default",
        }

        memory_job_id = await pool_manager.submit_job(memory_job_spec)
        logger.info(f"Submitted memory job: {memory_job_id}")

        # GPU job (if available)
        gpu_job_spec = {
            "name": "gpu_computation",
            "command": "python -c 'print(\"GPU computation simulation\"); import time; time.sleep(25)'",
            "resource_requirements": {
                "cpu_cores": 1,
                "memory": 2,  # GB
                "gpu_count": 1,
                "estimated_duration": 35.0,
            },
            "user_id": "demo_user",
            "priority": 1,  # Highest priority
            "queue": "default",
        }

        gpu_job_id = await pool_manager.submit_job(gpu_job_spec)
        logger.info(f"Submitted GPU job: {gpu_job_id}")

        # 4. Monitor job progress
        job_ids = [cpu_job_id, memory_job_id, gpu_job_id]

        logger.info("Monitoring job progress...")
        for _ in range(12):  # Monitor for ~1 minute
            pool_status = await pool_manager.get_pool_status()
            logger.info(
                f"Pool status: {pool_status['active_jobs']} active, "
                f"{pool_status['pending_jobs']} pending"
            )

            # Check individual job statuses
            for job_id in job_ids:
                job_status = await pool_manager.get_job_status(job_id)
                if job_status:
                    logger.info(
                        f"Job {job_id}: {job_status['status']} - Progress: {job_status['progress']}%"
                    )

            await asyncio.sleep(5.0)

        # 5. Demonstrate resource utilization monitoring
        logger.info("=== Resource Utilization ===")

        utilization = await pool_manager.get_pool_status()
        logger.info(f"Resource utilization: {utilization['resource_utilization']}")

        # 6. Wait for jobs to complete or demonstrate cancellation
        logger.info("Waiting for jobs to complete...")
        await asyncio.sleep(30.0)

        # Cancel any remaining jobs for cleanup
        for job_id in job_ids:
            job_status = await pool_manager.get_job_status(job_id)
            if job_status and job_status["status"] in ["pending", "running"]:
                logger.info(f"Cancelling job {job_id}")
                await pool_manager.cancel_job(job_id)

        # 7. Display final statistics
        logger.info("=== Final Statistics ===")
        final_status = await pool_manager.get_pool_status()
        logger.info(
            f"Total jobs processed: {final_status['statistics']['jobs_completed'] + final_status['statistics']['jobs_failed']}"
        )
        logger.info(f"Successful jobs: {final_status['statistics']['jobs_completed']}")
        logger.info(f"Failed jobs: {final_status['statistics']['jobs_failed']}")

    except Exception as e:
        logger.error(f"Error in demo: {e}")
        raise

    finally:
        # Cleanup
        await pool_manager.shutdown()
        logger.info("Demo completed successfully!")


async def advanced_scheduling_demo():
    """Demonstrate advanced scheduling features"""
    logger.info("=== Advanced Scheduling Demo ===")

    # Create a pool with different scheduling algorithm
    pool_config = PoolConfig(
        name="advanced_pool",
        max_concurrent_jobs=5,
        fair_share_enabled=True,
        preemption_enabled=True,
    )

    pool_manager = ComputePoolManager(pool_config)

    try:
        await pool_manager.initialize()

        # Create multiple users with different priorities
        users = ["user_a", "user_b", "user_c"]

        # Submit jobs from different users
        job_ids = []

        for i, user in enumerate(users):
            for j in range(3):  # 3 jobs per user
                job_spec = {
                    "name": f"{user}_job_{j}",
                    "command": f"python -c 'print(\"Job from {user}\"); import time; time.sleep({20 + j * 5})'",
                    "resource_requirements": {
                        "cpu_cores": 1,
                        "memory": 2,
                        "estimated_duration": float(25 + j * 5),
                    },
                    "user_id": user,
                    "priority": i + 1,  # Different priorities per user
                    "queue": "default",
                }

                job_id = await pool_manager.submit_job(job_spec)
                job_ids.append(job_id)
                logger.info(f"Submitted job {job_id} for {user} with priority {i + 1}")

        # Monitor fair share behavior
        logger.info("Monitoring fair share scheduling...")
        for _ in range(15):
            pool_status = await pool_manager.get_pool_status()
            logger.info(
                f"Active: {pool_status['active_jobs']}, Pending: {pool_status['pending_jobs']}"
            )

            # Show which jobs are running
            running_jobs = []
            for job_id in job_ids:
                job_status = await pool_manager.get_job_status(job_id)
                if job_status and job_status["status"] == "running":
                    running_jobs.append(f"{job_id} ({job_status.get('user_id', 'unknown')})")

            if running_jobs:
                logger.info(f"Running jobs: {', '.join(running_jobs)}")

            await asyncio.sleep(3.0)

    finally:
        await pool_manager.shutdown()


async def fault_tolerance_demo():
    """Demonstrate fault tolerance and checkpointing"""
    logger.info("=== Fault Tolerance Demo ===")

    # Configure checkpointing
    checkpoint_policy = CheckpointPolicy(
        interval_seconds=30.0,  # Checkpoint every 30 seconds
        max_checkpoints_per_job=3,
        compression_enabled=True,
        retention_days=1,
    )

    pool_config = PoolConfig(name="fault_tolerant_pool", checkpoint_interval=30.0)

    pool_manager = ComputePoolManager(pool_config)

    try:
        await pool_manager.initialize()

        # Submit a long-running job that can be checkpointed
        long_job_spec = {
            "name": "long_running_job",
            "command": "python -c 'import time; [print(f\"Step {i}\") or time.sleep(10) for i in range(20)]'",
            "resource_requirements": {"cpu_cores": 1, "memory": 1, "estimated_duration": 200.0},
            "user_id": "fault_test_user",
            "priority": 3,
        }

        job_id = await pool_manager.submit_job(long_job_spec)
        logger.info(f"Submitted long-running job: {job_id}")

        # Let it run for a while
        await asyncio.sleep(45.0)

        # Simulate a failure by cancelling and restarting
        logger.info("Simulating failure - cancelling job")
        await pool_manager.cancel_job(job_id)

        # Wait a moment
        await asyncio.sleep(5.0)

        # In a real scenario, you would restore from checkpoint
        logger.info("In a real scenario, job would be restored from checkpoint")

        # Submit recovery job
        recovery_job_spec = {
            "name": "recovered_job",
            "command": "python -c 'print(\"Recovered from checkpoint\"); import time; time.sleep(20)'",
            "resource_requirements": {"cpu_cores": 1, "memory": 1, "estimated_duration": 30.0},
            "user_id": "fault_test_user",
            "priority": 1,  # High priority for recovery
        }

        recovery_job_id = await pool_manager.submit_job(recovery_job_spec)
        logger.info(f"Submitted recovery job: {recovery_job_id}")

        # Monitor recovery
        for _ in range(10):
            job_status = await pool_manager.get_job_status(recovery_job_id)
            if job_status:
                logger.info(f"Recovery job status: {job_status['status']}")
            await asyncio.sleep(3.0)

    finally:
        await pool_manager.shutdown()


async def main():
    """Run all demonstrations"""
    try:
        # Run basic demo
        await basic_compute_pool_demo()

        await asyncio.sleep(2.0)

        # Run advanced scheduling demo
        await advanced_scheduling_demo()

        await asyncio.sleep(2.0)

        # Run fault tolerance demo
        await fault_tolerance_demo()

        logger.info("All demos completed successfully!")

    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
