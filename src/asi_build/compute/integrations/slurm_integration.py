"""
Slurm Integration - Integrates compute pool with Slurm Workload Manager
"""

import asyncio
import json
import logging
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class SlurmJobSpec:
    """Slurm job specification"""

    name: str
    script_path: Optional[str] = None
    command: Optional[str] = None
    partition: str = "compute"
    nodes: int = 1
    ntasks: int = 1
    cpus_per_task: int = 1
    memory: Optional[str] = None  # e.g., "4G", "1000M"
    time_limit: Optional[str] = None  # e.g., "01:00:00"
    gres: Optional[str] = None  # e.g., "gpu:1"
    account: Optional[str] = None
    qos: Optional[str] = None
    mail_type: Optional[str] = None
    mail_user: Optional[str] = None
    output_file: Optional[str] = None
    error_file: Optional[str] = None
    working_directory: Optional[str] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    sbatch_options: Dict[str, str] = field(default_factory=dict)

    def to_sbatch_script(self) -> str:
        """Convert to Slurm sbatch script"""
        lines = ["#!/bin/bash"]

        # Add SBATCH directives
        lines.append(f"#SBATCH --job-name={self.name}")
        lines.append(f"#SBATCH --partition={self.partition}")
        lines.append(f"#SBATCH --nodes={self.nodes}")
        lines.append(f"#SBATCH --ntasks={self.ntasks}")
        lines.append(f"#SBATCH --cpus-per-task={self.cpus_per_task}")

        if self.memory:
            lines.append(f"#SBATCH --mem={self.memory}")

        if self.time_limit:
            lines.append(f"#SBATCH --time={self.time_limit}")

        if self.gres:
            lines.append(f"#SBATCH --gres={self.gres}")

        if self.account:
            lines.append(f"#SBATCH --account={self.account}")

        if self.qos:
            lines.append(f"#SBATCH --qos={self.qos}")

        if self.mail_type:
            lines.append(f"#SBATCH --mail-type={self.mail_type}")

        if self.mail_user:
            lines.append(f"#SBATCH --mail-user={self.mail_user}")

        if self.output_file:
            lines.append(f"#SBATCH --output={self.output_file}")

        if self.error_file:
            lines.append(f"#SBATCH --error={self.error_file}")

        if self.working_directory:
            lines.append(f"#SBATCH --chdir={self.working_directory}")

        # Add custom sbatch options
        for key, value in self.sbatch_options.items():
            lines.append(f"#SBATCH --{key}={value}")

        lines.append("")  # Empty line

        # Add environment variables
        for key, value in self.environment_variables.items():
            lines.append(f"export {key}={value}")

        if self.environment_variables:
            lines.append("")  # Empty line

        # Add the command or script
        if self.command:
            lines.append(self.command)
        elif self.script_path:
            lines.append(f"bash {self.script_path}")
        else:
            lines.append("echo 'No command or script specified'")

        return "\n".join(lines)


@dataclass
class SlurmJobStatus:
    """Slurm job status information"""

    job_id: str
    name: str
    state: str  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, etc.
    partition: str
    nodes: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    elapsed_time: Optional[str] = None
    exit_code: Optional[str] = None
    working_directory: Optional[str] = None
    submit_time: Optional[str] = None
    user: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "state": self.state,
            "partition": self.partition,
            "nodes": self.nodes,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_time": self.elapsed_time,
            "exit_code": self.exit_code,
            "working_directory": self.working_directory,
            "submit_time": self.submit_time,
            "user": self.user,
        }


class SlurmIntegration:
    """
    Advanced Slurm integration for the compute pool system
    """

    def __init__(self, slurm_bin_path: str = "/usr/bin"):
        self.slurm_bin_path = slurm_bin_path
        self.logger = logging.getLogger("slurm_integration")

        # Command paths
        self.sbatch_cmd = f"{slurm_bin_path}/sbatch"
        self.squeue_cmd = f"{slurm_bin_path}/squeue"
        self.scancel_cmd = f"{slurm_bin_path}/scancel"
        self.sinfo_cmd = f"{slurm_bin_path}/sinfo"
        self.scontrol_cmd = f"{slurm_bin_path}/scontrol"
        self.sacct_cmd = f"{slurm_bin_path}/sacct"

        # Job tracking
        self.active_jobs: Dict[str, SlurmJobStatus] = {}
        self.compute_pool_job_to_slurm: Dict[str, str] = {}  # compute_pool_job_id -> slurm_job_id
        self.slurm_to_compute_pool_job: Dict[str, str] = {}  # slurm_job_id -> compute_pool_job_id

        # Cluster information
        self.partitions: Dict[str, Dict[str, Any]] = {}
        self.nodes: Dict[str, Dict[str, Any]] = {}

        # Monitoring
        self.monitoring_interval = 30.0  # 30 seconds
        self.monitoring_task: Optional[asyncio.Task] = None

        # Statistics
        self._stats = {
            "total_jobs_submitted": 0,
            "active_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "cancelled_jobs": 0,
            "total_nodes": 0,
            "idle_nodes": 0,
            "allocated_nodes": 0,
            "down_nodes": 0,
            "total_cpus": 0,
            "idle_cpus": 0,
            "allocated_cpus": 0,
        }

    async def initialize(self) -> None:
        """Initialize Slurm integration"""
        self.logger.info("Initializing Slurm integration")

        try:
            # Check if Slurm commands are available
            await self._check_slurm_availability()

            # Load cluster information
            await self._load_cluster_info()

            # Start job monitoring
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())

            self.logger.info("Slurm integration initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing Slurm integration: {e}")
            raise

    async def _check_slurm_availability(self) -> None:
        """Check if Slurm commands are available"""
        commands_to_check = [
            self.sbatch_cmd,
            self.squeue_cmd,
            self.scancel_cmd,
            self.sinfo_cmd,
            self.scontrol_cmd,
            self.sacct_cmd,
        ]

        for cmd in commands_to_check:
            try:
                result = await self._run_command([cmd, "--help"], timeout=5.0)
                if result["returncode"] != 0:
                    raise RuntimeError(f"Slurm command {cmd} not working")
            except Exception as e:
                raise RuntimeError(f"Slurm command {cmd} not available: {e}")

        self.logger.info("All Slurm commands are available")

    async def _load_cluster_info(self) -> None:
        """Load Slurm cluster information"""
        try:
            # Get partition information
            await self._load_partition_info()

            # Get node information
            await self._load_node_info()

            self.logger.info(
                f"Loaded cluster info: {len(self.partitions)} partitions, "
                f"{len(self.nodes)} nodes"
            )

        except Exception as e:
            self.logger.error(f"Error loading cluster info: {e}")

    async def _load_partition_info(self) -> None:
        """Load partition information using sinfo"""
        try:
            result = await self._run_command(
                [self.sinfo_cmd, "--format=%P,%a,%l,%D,%T,%N", "--noheader", "--parsable2"]
            )

            if result["returncode"] != 0:
                raise RuntimeError(f"sinfo command failed: {result['stderr']}")

            for line in result["stdout"].strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split("|")
                if len(parts) >= 6:
                    partition_name = parts[0].rstrip("*")  # Remove default partition marker

                    self.partitions[partition_name] = {
                        "name": partition_name,
                        "availability": parts[1],
                        "time_limit": parts[2],
                        "nodes": int(parts[3]),
                        "state": parts[4],
                        "node_list": parts[5],
                    }

        except Exception as e:
            self.logger.error(f"Error loading partition info: {e}")

    async def _load_node_info(self) -> None:
        """Load node information using sinfo"""
        try:
            result = await self._run_command(
                [
                    self.sinfo_cmd,
                    "--Node",
                    "--format=%N,%T,%C,%m,%G,%P",
                    "--noheader",
                    "--parsable2",
                ]
            )

            if result["returncode"] != 0:
                raise RuntimeError(f"sinfo command failed: {result['stderr']}")

            total_cpus = 0
            idle_cpus = 0
            allocated_cpus = 0
            idle_nodes = 0
            allocated_nodes = 0
            down_nodes = 0

            for line in result["stdout"].strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split("|")
                if len(parts) >= 6:
                    node_name = parts[0]
                    state = parts[1]
                    cpu_info = parts[2]  # Format: allocated/idle/other/total
                    memory = parts[3]
                    gres = parts[4]  # Generic resources (GPUs, etc.)
                    partitions = parts[5]

                    # Parse CPU information
                    cpu_parts = cpu_info.split("/")
                    if len(cpu_parts) >= 4:
                        allocated = int(cpu_parts[0])
                        idle = int(cpu_parts[1])
                        total = int(cpu_parts[3])
                    else:
                        allocated = idle = total = 0

                    self.nodes[node_name] = {
                        "name": node_name,
                        "state": state,
                        "cpus_allocated": allocated,
                        "cpus_idle": idle,
                        "cpus_total": total,
                        "memory": memory,
                        "gres": gres,
                        "partitions": partitions,
                    }

                    total_cpus += total
                    idle_cpus += idle
                    allocated_cpus += allocated

                    # Count node states
                    if "idle" in state.lower():
                        idle_nodes += 1
                    elif "alloc" in state.lower() or "mixed" in state.lower():
                        allocated_nodes += 1
                    elif "down" in state.lower() or "drain" in state.lower():
                        down_nodes += 1

            # Update statistics
            self._stats["total_nodes"] = len(self.nodes)
            self._stats["idle_nodes"] = idle_nodes
            self._stats["allocated_nodes"] = allocated_nodes
            self._stats["down_nodes"] = down_nodes
            self._stats["total_cpus"] = total_cpus
            self._stats["idle_cpus"] = idle_cpus
            self._stats["allocated_cpus"] = allocated_cpus

        except Exception as e:
            self.logger.error(f"Error loading node info: {e}")

    async def submit_job(
        self,
        compute_pool_job_id: str,
        job_spec: SlurmJobSpec,
        resource_requirements: Dict[str, Any],
    ) -> Optional[str]:
        """Submit a job to Slurm"""
        try:
            # Update job spec with resource requirements
            self._apply_resource_requirements(job_spec, resource_requirements)

            # Generate sbatch script
            script_content = job_spec.to_sbatch_script()

            # Submit job using sbatch
            result = await self._run_command(
                [self.sbatch_cmd], input_text=script_content, timeout=30.0
            )

            if result["returncode"] != 0:
                self.logger.error(f"sbatch failed: {result['stderr']}")
                return None

            # Parse job ID from sbatch output
            output = result["stdout"].strip()
            match = re.search(r"Submitted batch job (\d+)", output)

            if not match:
                self.logger.error(f"Could not parse job ID from sbatch output: {output}")
                return None

            slurm_job_id = match.group(1)

            # Track the job
            job_status = SlurmJobStatus(
                job_id=slurm_job_id,
                name=job_spec.name,
                state="PENDING",
                partition=job_spec.partition,
            )

            self.active_jobs[slurm_job_id] = job_status
            self.compute_pool_job_to_slurm[compute_pool_job_id] = slurm_job_id
            self.slurm_to_compute_pool_job[slurm_job_id] = compute_pool_job_id

            self._stats["total_jobs_submitted"] += 1

            self.logger.info(f"Submitted job {compute_pool_job_id} as Slurm job {slurm_job_id}")
            return slurm_job_id

        except Exception as e:
            self.logger.error(f"Error submitting job {compute_pool_job_id}: {e}")
            return None

    def _apply_resource_requirements(
        self, job_spec: SlurmJobSpec, requirements: Dict[str, Any]
    ) -> None:
        """Apply compute pool resource requirements to Slurm job spec"""
        # CPU cores
        if "cpu_cores" in requirements:
            job_spec.cpus_per_task = requirements["cpu_cores"]

        # Memory
        if "memory" in requirements:
            memory_gb = requirements["memory"]
            job_spec.memory = f"{int(memory_gb * 1024)}M"  # Convert to MB

        # GPU
        if "gpu_count" in requirements and requirements["gpu_count"] > 0:
            gpu_count = requirements["gpu_count"]
            job_spec.gres = f"gpu:{gpu_count}"

        # Time limit (if provided)
        if "estimated_duration" in requirements:
            duration_seconds = requirements["estimated_duration"]
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600) // 60)
            seconds = int(duration_seconds % 60)
            job_spec.time_limit = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Partition selection based on requirements
        if "priority" in requirements:
            priority = requirements["priority"]
            if priority <= 2:  # High priority
                if "gpu" in job_spec.gres if job_spec.gres else "":
                    job_spec.partition = "gpu-priority"
                else:
                    job_spec.partition = "priority"
            elif priority >= 4:  # Low priority
                job_spec.partition = "batch"
            # else: keep default partition

    async def cancel_job(self, compute_pool_job_id: str) -> bool:
        """Cancel a Slurm job"""
        if compute_pool_job_id not in self.compute_pool_job_to_slurm:
            return False

        slurm_job_id = self.compute_pool_job_to_slurm[compute_pool_job_id]

        try:
            result = await self._run_command([self.scancel_cmd, slurm_job_id], timeout=10.0)

            if result["returncode"] != 0:
                self.logger.error(f"scancel failed: {result['stderr']}")
                return False

            # Update job status
            if slurm_job_id in self.active_jobs:
                self.active_jobs[slurm_job_id].state = "CANCELLED"
                self._stats["cancelled_jobs"] += 1

            self.logger.info(f"Cancelled job {compute_pool_job_id} (Slurm job {slurm_job_id})")
            return True

        except Exception as e:
            self.logger.error(f"Error cancelling job {compute_pool_job_id}: {e}")
            return False

    async def get_job_status(self, compute_pool_job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status from Slurm"""
        if compute_pool_job_id not in self.compute_pool_job_to_slurm:
            return None

        slurm_job_id = self.compute_pool_job_to_slurm[compute_pool_job_id]

        # Update job status from Slurm
        await self._update_job_status(slurm_job_id)

        if slurm_job_id not in self.active_jobs:
            return None

        return self.active_jobs[slurm_job_id].to_dict()

    async def _update_job_status(self, slurm_job_id: str) -> None:
        """Update job status from Slurm"""
        try:
            # Use squeue for active jobs
            result = await self._run_command(
                [
                    self.squeue_cmd,
                    "--job",
                    slurm_job_id,
                    "--format=%i,%j,%T,%P,%N,%S,%V,%L",
                    "--noheader",
                    "--parsable2",
                ],
                timeout=10.0,
            )

            if result["returncode"] == 0 and result["stdout"].strip():
                # Job found in queue
                line = result["stdout"].strip()
                parts = line.split("|")

                if len(parts) >= 8:
                    job_status = SlurmJobStatus(
                        job_id=parts[0],
                        name=parts[1],
                        state=parts[2],
                        partition=parts[3],
                        nodes=parts[4] if parts[4] else None,
                        start_time=parts[5] if parts[5] else None,
                        submit_time=parts[6] if parts[6] else None,
                        elapsed_time=parts[7] if parts[7] else None,
                    )

                    self.active_jobs[slurm_job_id] = job_status
                    return

            # Job not in queue, try sacct for completed jobs
            result = await self._run_command(
                [
                    self.sacct_cmd,
                    "--job",
                    slurm_job_id,
                    "--format=JobID,JobName,State,Partition,NodeList,Start,End,Elapsed,ExitCode,WorkDir",
                    "--noheader",
                    "--parsable2",
                ],
                timeout=10.0,
            )

            if result["returncode"] == 0 and result["stdout"].strip():
                lines = result["stdout"].strip().split("\n")

                for line in lines:
                    if not line.strip() or ".batch" in line or ".extern" in line:
                        continue  # Skip batch and extern steps

                    parts = line.split("|")
                    if len(parts) >= 10:
                        job_status = SlurmJobStatus(
                            job_id=parts[0],
                            name=parts[1],
                            state=parts[2],
                            partition=parts[3],
                            nodes=parts[4] if parts[4] else None,
                            start_time=parts[5] if parts[5] else None,
                            end_time=parts[6] if parts[6] else None,
                            elapsed_time=parts[7] if parts[7] else None,
                            exit_code=parts[8] if parts[8] else None,
                            working_directory=parts[9] if parts[9] else None,
                        )

                        self.active_jobs[slurm_job_id] = job_status

                        # Update statistics for completed jobs
                        if job_status.state in ["COMPLETED", "FAILED", "CANCELLED"]:
                            if job_status.state == "COMPLETED":
                                self._stats["completed_jobs"] += 1
                            elif job_status.state == "FAILED":
                                self._stats["failed_jobs"] += 1
                            elif job_status.state == "CANCELLED":
                                self._stats["cancelled_jobs"] += 1

                        break

        except Exception as e:
            self.logger.error(f"Error updating job status for {slurm_job_id}: {e}")

    async def _monitoring_loop(self) -> None:
        """Monitor Slurm jobs and cluster status"""
        while True:
            try:
                # Update all active job statuses
                slurm_job_ids = list(self.active_jobs.keys())

                for slurm_job_id in slurm_job_ids:
                    await self._update_job_status(slurm_job_id)

                # Update cluster information periodically
                await self._load_node_info()

                # Update active jobs count
                active_count = len(
                    [
                        job
                        for job in self.active_jobs.values()
                        if job.state in ["PENDING", "RUNNING"]
                    ]
                )
                self._stats["active_jobs"] = active_count

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60.0)

    async def get_cluster_resources(self) -> Dict[str, Any]:
        """Get current cluster resource availability"""
        await self._load_node_info()  # Refresh node information

        total_cpus = sum(node["cpus_total"] for node in self.nodes.values())
        idle_cpus = sum(node["cpus_idle"] for node in self.nodes.values())
        allocated_cpus = sum(node["cpus_allocated"] for node in self.nodes.values())

        # Count GPUs (simplified - assumes GPU info is in GRES)
        total_gpus = 0
        idle_gpus = 0

        for node in self.nodes.values():
            gres = node.get("gres", "")
            if "gpu:" in gres:
                # Simple parsing of GPU count from GRES
                import re

                match = re.search(r"gpu:(\d+)", gres)
                if match:
                    node_gpus = int(match.group(1))
                    total_gpus += node_gpus

                    # Assume GPUs are idle if node is idle
                    if "idle" in node["state"].lower():
                        idle_gpus += node_gpus

        return {
            "nodes": {
                "total": len(self.nodes),
                "idle": self._stats["idle_nodes"],
                "allocated": self._stats["allocated_nodes"],
                "down": self._stats["down_nodes"],
            },
            "cpus": {
                "total": total_cpus,
                "idle": idle_cpus,
                "allocated": allocated_cpus,
                "utilization": (allocated_cpus / total_cpus * 100) if total_cpus > 0 else 0,
            },
            "gpus": {
                "total": total_gpus,
                "idle": idle_gpus,
                "allocated": total_gpus - idle_gpus,
                "utilization": (
                    ((total_gpus - idle_gpus) / total_gpus * 100) if total_gpus > 0 else 0
                ),
            },
            "partitions": list(self.partitions.keys()),
        }

    async def get_partition_info(self, partition_name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about Slurm partitions"""
        if partition_name:
            return self.partitions.get(partition_name, {})
        else:
            return self.partitions.copy()

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current job queue status"""
        try:
            result = await self._run_command(
                [self.squeue_cmd, "--format=%T,%r", "--noheader", "--parsable2"], timeout=10.0
            )

            if result["returncode"] != 0:
                return {}

            state_counts = {}
            reason_counts = {}

            for line in result["stdout"].strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split("|")
                if len(parts) >= 2:
                    state = parts[0]
                    reason = parts[1]

                    state_counts[state] = state_counts.get(state, 0) + 1
                    if reason and reason != "(null)":
                        reason_counts[reason] = reason_counts.get(reason, 0) + 1

            return {
                "job_states": state_counts,
                "pending_reasons": reason_counts,
                "total_jobs": sum(state_counts.values()),
            }

        except Exception as e:
            self.logger.error(f"Error getting queue status: {e}")
            return {}

    async def _run_command(
        self, cmd: List[str], input_text: Optional[str] = None, timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Run a Slurm command and return the result"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if input_text else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_text.encode() if input_text else None),
                timeout=timeout,
            )

            return {
                "returncode": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
            }

        except asyncio.TimeoutError:
            self.logger.error(f"Command timeout: {' '.join(cmd)}")
            return {"returncode": -1, "stdout": "", "stderr": "Command timeout"}
        except Exception as e:
            self.logger.error(f"Error running command {' '.join(cmd)}: {e}")
            return {"returncode": -1, "stdout": "", "stderr": str(e)}

    async def get_integration_status(self) -> Dict[str, Any]:
        """Get Slurm integration status"""
        return {
            "slurm_bin_path": self.slurm_bin_path,
            "statistics": self._stats.copy(),
            "active_jobs": len(
                [job for job in self.active_jobs.values() if job.state in ["PENDING", "RUNNING"]]
            ),
            "tracked_jobs": len(self.active_jobs),
            "partitions": len(self.partitions),
            "nodes": len(self.nodes),
            "monitoring_interval": self.monitoring_interval,
        }

    async def shutdown(self) -> None:
        """Shutdown Slurm integration"""
        self.logger.info("Shutting down Slurm integration")

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Slurm integration shutdown complete")
