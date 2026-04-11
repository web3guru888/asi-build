#!/usr/bin/env python3
"""
Slurm Integration Example - Demonstrates Slurm Workload Manager integration
"""

import asyncio
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

# Add the compute pool to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pool_manager import ComputePoolManager, PoolConfig
from integrations.slurm_integration import SlurmIntegration, SlurmJobSpec

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def slurm_integration_demo():
    """Demonstrate Slurm integration"""
    logger.info("=== Kenny AGI Compute Pool - Slurm Integration Demo ===")

    try:
        # 1. Initialize Slurm integration
        slurm_integration = SlurmIntegration(slurm_bin_path="/usr/bin")  # Adjust path as needed

        await slurm_integration.initialize()
        logger.info("Slurm integration initialized")

        # 2. Get cluster information
        cluster_resources = await slurm_integration.get_cluster_resources()
        logger.info(f"Cluster resources: {cluster_resources}")

        partition_info = await slurm_integration.get_partition_info()
        logger.info(f"Available partitions: {list(partition_info.keys())}")

        queue_status = await slurm_integration.get_queue_status()
        logger.info(f"Current queue status: {queue_status}")

        # 3. Create temporary script files for jobs
        with tempfile.TemporaryDirectory() as temp_dir:
            # CPU-intensive job
            cpu_script_path = os.path.join(temp_dir, "cpu_job.py")
            with open(cpu_script_path, "w") as f:
                f.write("""
import time
import multiprocessing as mp

def cpu_intensive_task(n):
    result = sum(i**2 for i in range(n))
    return result

if __name__ == "__main__":
    print("Starting CPU-intensive computation...")
    
    # Use multiple processes to utilize multiple cores
    with mp.Pool(processes=2) as pool:
        results = pool.map(cpu_intensive_task, [1000000] * 4)
    
    print(f"Computation completed. Results: {sum(results)}")
    time.sleep(10)  # Simulate additional work
    print("CPU job finished successfully")
""")

            cpu_job_spec = SlurmJobSpec(
                name="cpu_intensive_job",
                script_path=cpu_script_path,
                partition="compute",  # Adjust partition name as needed
                nodes=1,
                ntasks=1,
                cpus_per_task=2,
                memory="4G",
                time_limit="00:10:00",  # 10 minutes
                output_file=os.path.join(temp_dir, "cpu_job.out"),
                error_file=os.path.join(temp_dir, "cpu_job.err"),
                environment_variables={
                    "KENNY_JOB_TYPE": "cpu_intensive",
                    "KENNY_POOL": "slurm_demo",
                },
            )

            cpu_job_id = "cpu-job-" + str(int(time.time()))
            cpu_requirements = {
                "cpu_cores": 2,
                "memory": 4,  # GB
                "estimated_duration": 300.0,  # 5 minutes
                "priority": 2,
            }

            slurm_job_id = await slurm_integration.submit_job(
                cpu_job_id, cpu_job_spec, cpu_requirements
            )

            if slurm_job_id:
                logger.info(f"Submitted CPU job: {cpu_job_id} -> Slurm job {slurm_job_id}")
            else:
                logger.error("Failed to submit CPU job")

            # Memory-intensive job
            memory_script_path = os.path.join(temp_dir, "memory_job.py")
            with open(memory_script_path, "w") as f:
                f.write("""
import time
import gc

def memory_intensive_task():
    print("Starting memory-intensive task...")
    
    # Allocate large amounts of memory
    big_list = []
    for i in range(10):
        chunk = [j for j in range(1000000)]  # 1M integers per chunk
        big_list.append(chunk)
        print(f"Allocated chunk {i+1}/10")
        time.sleep(2)
    
    print(f"Total memory allocated: {len(big_list)} chunks")
    
    # Process the data
    total = sum(sum(chunk) for chunk in big_list)
    print(f"Processing complete. Total sum: {total}")
    
    # Clean up
    del big_list
    gc.collect()
    print("Memory job finished successfully")

if __name__ == "__main__":
    memory_intensive_task()
""")

            memory_job_spec = SlurmJobSpec(
                name="memory_intensive_job",
                script_path=memory_script_path,
                partition="compute",
                nodes=1,
                ntasks=1,
                cpus_per_task=1,
                memory="8G",
                time_limit="00:08:00",  # 8 minutes
                output_file=os.path.join(temp_dir, "memory_job.out"),
                error_file=os.path.join(temp_dir, "memory_job.err"),
                environment_variables={
                    "KENNY_JOB_TYPE": "memory_intensive",
                    "KENNY_POOL": "slurm_demo",
                },
            )

            memory_job_id = "memory-job-" + str(int(time.time()))
            memory_requirements = {
                "cpu_cores": 1,
                "memory": 8,  # GB
                "estimated_duration": 240.0,  # 4 minutes
                "priority": 3,
            }

            slurm_job_id_2 = await slurm_integration.submit_job(
                memory_job_id, memory_job_spec, memory_requirements
            )

            if slurm_job_id_2:
                logger.info(f"Submitted memory job: {memory_job_id} -> Slurm job {slurm_job_id_2}")
            else:
                logger.error("Failed to submit memory job")

            # GPU job (if GPUs available)
            gpu_script_path = os.path.join(temp_dir, "gpu_job.py")
            with open(gpu_script_path, "w") as f:
                f.write("""
import time
import os

def gpu_computation():
    print("Starting GPU computation simulation...")
    
    # Check for GPU environment variables
    gpu_devices = os.environ.get('CUDA_VISIBLE_DEVICES', 'none')
    print(f"Available GPU devices: {gpu_devices}")
    
    try:
        # Try to import and use a GPU library
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"GPU info: {result.stdout}")
        else:
            print("GPU info not available")
    except Exception as e:
        print(f"Could not get GPU info: {e}")
    
    # Simulate GPU computation
    print("Performing GPU computation...")
    for i in range(10):
        time.sleep(2)
        print(f"GPU computation step {i+1}/10")
    
    print("GPU job finished successfully")

if __name__ == "__main__":
    gpu_computation()
""")

            gpu_job_spec = SlurmJobSpec(
                name="gpu_computation",
                script_path=gpu_script_path,
                partition="gpu",  # GPU partition (adjust as needed)
                nodes=1,
                ntasks=1,
                cpus_per_task=1,
                memory="4G",
                time_limit="00:05:00",  # 5 minutes
                gres="gpu:1",  # Request 1 GPU
                output_file=os.path.join(temp_dir, "gpu_job.out"),
                error_file=os.path.join(temp_dir, "gpu_job.err"),
                environment_variables={
                    "KENNY_JOB_TYPE": "gpu_computation",
                    "KENNY_POOL": "slurm_demo",
                },
            )

            gpu_job_id = "gpu-job-" + str(int(time.time()))
            gpu_requirements = {
                "cpu_cores": 1,
                "memory": 4,  # GB
                "gpu_count": 1,
                "estimated_duration": 180.0,  # 3 minutes
                "priority": 1,  # Highest priority
            }

            slurm_job_id_3 = await slurm_integration.submit_job(
                gpu_job_id, gpu_job_spec, gpu_requirements
            )

            if slurm_job_id_3:
                logger.info(f"Submitted GPU job: {gpu_job_id} -> Slurm job {slurm_job_id_3}")
            else:
                logger.warning("Failed to submit GPU job (GPU partition may not be available)")

            # 4. Monitor job statuses
            job_ids = [cpu_job_id, memory_job_id, gpu_job_id]

            logger.info("Monitoring job statuses...")
            for _ in range(30):  # Monitor for ~5 minutes
                integration_status = await slurm_integration.get_integration_status()
                logger.info(f"Slurm Integration: {integration_status['active_jobs']} active jobs")

                current_queue = await slurm_integration.get_queue_status()
                if current_queue.get("total_jobs", 0) > 0:
                    logger.info(f"Queue status: {current_queue}")

                for job_id in job_ids:
                    job_status = await slurm_integration.get_job_status(job_id)
                    if job_status:
                        logger.info(
                            f"Job {job_id}: {job_status['state']} on {job_status.get('nodes', 'unassigned')}"
                        )

                await asyncio.sleep(10.0)

            # 5. Clean up - cancel any remaining jobs
            logger.info("Cleaning up jobs...")
            for job_id in job_ids:
                job_status = await slurm_integration.get_job_status(job_id)
                if job_status and job_status["state"] in ["PENDING", "RUNNING"]:
                    cancelled = await slurm_integration.cancel_job(job_id)
                    if cancelled:
                        logger.info(f"Cancelled job {job_id}")

            # 6. Display job output files
            logger.info("=== Job Output Files ===")
            for job_type, filename in [
                ("CPU", "cpu_job.out"),
                ("Memory", "memory_job.out"),
                ("GPU", "gpu_job.out"),
            ]:
                output_path = os.path.join(temp_dir, filename)
                if os.path.exists(output_path):
                    with open(output_path, "r") as f:
                        content = f.read()
                        if content.strip():
                            logger.info(f"{job_type} job output:\n{content}")
                        else:
                            logger.info(f"{job_type} job output file is empty")
                else:
                    logger.info(f"{job_type} job output file not found")

        # 7. Final status
        final_status = await slurm_integration.get_integration_status()
        logger.info(f"Final integration status: {final_status}")

    except Exception as e:
        logger.error(f"Error in Slurm demo: {e}")
        if "slurm command" in str(e).lower() and "not available" in str(e).lower():
            logger.warning(
                "Slurm commands not available. Make sure Slurm is installed and in PATH."
            )
            logger.warning("This demo requires a working Slurm cluster.")
        raise

    finally:
        await slurm_integration.shutdown()
        logger.info("Slurm integration demo completed!")


async def slurm_batch_job_demo():
    """Demonstrate batch job submission with Slurm"""
    logger.info("=== Slurm Batch Job Demo ===")

    try:
        slurm_integration = SlurmIntegration()
        await slurm_integration.initialize()

        # Create multiple related jobs (job array simulation)
        job_ids = []

        with tempfile.TemporaryDirectory() as temp_dir:
            for i in range(3):
                script_path = os.path.join(temp_dir, f"batch_job_{i}.py")
                with open(script_path, "w") as f:
                    f.write(f"""
import time
import os

job_index = {i}
print(f"Batch job {{job_index}} starting...")

# Simulate different workloads
if job_index == 0:
    # CPU-heavy task
    result = sum(i**2 for i in range(500000))
    print(f"CPU task result: {{result}}")
elif job_index == 1:
    # I/O-heavy task
    data = []
    for j in range(100000):
        data.append(f"data_{{j}}")
    print(f"I/O task processed {{len(data)}} items")
else:
    # Mixed workload
    time.sleep(15)
    print("Mixed workload completed")

print(f"Batch job {{job_index}} finished successfully")
""")

                job_spec = SlurmJobSpec(
                    name=f"batch_job_{i}",
                    script_path=script_path,
                    partition="compute",
                    nodes=1,
                    ntasks=1,
                    cpus_per_task=1,
                    memory="2G",
                    time_limit="00:03:00",
                    output_file=os.path.join(temp_dir, f"batch_{i}.out"),
                    error_file=os.path.join(temp_dir, f"batch_{i}.err"),
                    environment_variables={"BATCH_INDEX": str(i), "BATCH_SIZE": "3"},
                )

                compute_job_id = f"batch-job-{i}-{int(time.time())}"
                requirements = {
                    "cpu_cores": 1,
                    "memory": 2,
                    "estimated_duration": 120.0,
                    "priority": 3,
                }

                slurm_job_id = await slurm_integration.submit_job(
                    compute_job_id, job_spec, requirements
                )

                if slurm_job_id:
                    job_ids.append(compute_job_id)
                    logger.info(f"Submitted batch job {i}: {compute_job_id}")

            # Monitor batch jobs
            logger.info("Monitoring batch jobs...")
            all_completed = False

            for _ in range(20):  # Monitor for up to 200 seconds
                completed_count = 0

                for job_id in job_ids:
                    job_status = await slurm_integration.get_job_status(job_id)
                    if job_status:
                        logger.info(f"Batch job {job_id}: {job_status['state']}")
                        if job_status["state"] in ["COMPLETED", "FAILED", "CANCELLED"]:
                            completed_count += 1

                if completed_count == len(job_ids):
                    all_completed = True
                    break

                await asyncio.sleep(10.0)

            if all_completed:
                logger.info("All batch jobs completed")
            else:
                logger.info("Some batch jobs still running")

            # Show outputs
            logger.info("=== Batch Job Outputs ===")
            for i in range(3):
                output_file = os.path.join(temp_dir, f"batch_{i}.out")
                if os.path.exists(output_file):
                    with open(output_file, "r") as f:
                        content = f.read()
                        logger.info(f"Batch job {i} output:\n{content}")

    except Exception as e:
        logger.error(f"Error in batch job demo: {e}")

    finally:
        await slurm_integration.shutdown()


async def main():
    """Run Slurm integration demonstrations"""
    try:
        # Run basic Slurm integration demo
        await slurm_integration_demo()

        await asyncio.sleep(2.0)

        # Run batch job demo
        await slurm_batch_job_demo()

        logger.info("All Slurm demos completed successfully!")

    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        if "slurm command" not in str(e).lower():
            raise


if __name__ == "__main__":
    asyncio.run(main())
