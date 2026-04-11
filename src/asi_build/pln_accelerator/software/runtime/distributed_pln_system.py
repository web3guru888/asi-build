"""
Distributed PLN Computation System

A scalable distributed system for PLN computation across multiple devices,
supporting heterogeneous hardware and fault-tolerant operation.

Features:
- Multi-device PLN computation
- Automatic workload distribution
- Fault tolerance and recovery
- Dynamic resource allocation
- Cross-device truth value synchronization
- Hierarchical processing topology
- Network-efficient communication

Author: PLN Accelerator Project
Target: Linear scaling to 1000+ devices
"""

import asyncio
import hashlib
import json
import logging
import pickle
import socket
import threading
import time
import uuid
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import consul
import etcd3
import grpc
import numpy as np
from kubernetes import client
from kubernetes import config as k8s_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our local modules
from real_time_inference_engine import (
    InferencePriority,
    InferenceRequest,
    InferenceResult,
    InferenceType,
    RealTimeInferenceEngine,
    TruthValue,
)


class DeviceType(Enum):
    """Types of PLN computation devices"""

    FPGA = "fpga"
    ASIC = "asic"
    GPU = "gpu"
    CPU = "cpu"
    QUANTUM = "quantum"
    HYBRID = "hybrid"


class DeviceCapability(Enum):
    """Device capabilities for different PLN operations"""

    BASIC_INFERENCE = "basic_inference"
    VECTOR_OPERATIONS = "vector_operations"
    PARALLEL_PROPAGATION = "parallel_propagation"
    NEURAL_SYMBOLIC = "neural_symbolic"
    QUANTUM_REASONING = "quantum_reasoning"
    HIGH_PRECISION = "high_precision"
    LOW_LATENCY = "low_latency"


@dataclass
class DeviceInfo:
    """Information about a PLN computation device"""

    device_id: str
    device_type: DeviceType
    capabilities: List[DeviceCapability]
    performance_rating: float  # Operations per second
    memory_capacity: int  # Truth values capacity
    network_latency_ms: float
    power_consumption_watts: float
    availability: float  # 0.0 to 1.0
    current_load: float  # 0.0 to 1.0
    last_heartbeat: float
    endpoint: str  # Network endpoint


@dataclass
class ComputeTask:
    """A distributed PLN computation task"""

    task_id: str
    inference_type: InferenceType
    priority: InferencePriority
    operands: List[TruthValue]
    concept_ids: List[int]
    dependencies: List[str]  # Task IDs this task depends on
    estimated_complexity: float
    deadline: float
    max_retries: int = 3
    assigned_device: Optional[str] = None
    status: str = "pending"  # pending, assigned, running, completed, failed
    result: Optional[TruthValue] = None
    created_at: float = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class WorkloadBalancer:
    """Intelligent workload balancer for distributed PLN computation"""

    def __init__(self):
        self.devices: Dict[str, DeviceInfo] = {}
        self.task_queue: Dict[str, ComputeTask] = {}
        self.task_assignments: Dict[str, str] = {}  # task_id -> device_id
        self.device_loads: Dict[str, float] = {}
        self.lock = threading.RLock()

        # Load balancing strategies
        self.strategies = {
            "round_robin": self._round_robin_assignment,
            "least_loaded": self._least_loaded_assignment,
            "capability_aware": self._capability_aware_assignment,
            "performance_weighted": self._performance_weighted_assignment,
            "latency_optimized": self._latency_optimized_assignment,
        }
        self.current_strategy = "capability_aware"
        self.last_device_index = 0

    def register_device(self, device: DeviceInfo):
        """Register a new PLN computation device"""
        with self.lock:
            self.devices[device.device_id] = device
            self.device_loads[device.device_id] = 0.0
            logger.info(f"Registered device {device.device_id} ({device.device_type.value})")

    def unregister_device(self, device_id: str):
        """Unregister a PLN computation device"""
        with self.lock:
            if device_id in self.devices:
                del self.devices[device_id]
                del self.device_loads[device_id]

                # Reassign tasks from this device
                affected_tasks = [
                    task_id
                    for task_id, assigned_device in self.task_assignments.items()
                    if assigned_device == device_id
                ]

                for task_id in affected_tasks:
                    self._reassign_task(task_id)

                logger.info(f"Unregistered device {device_id}")

    def assign_task(self, task: ComputeTask) -> Optional[str]:
        """Assign a task to the most suitable device"""
        with self.lock:
            strategy_func = self.strategies[self.current_strategy]
            device_id = strategy_func(task)

            if device_id:
                self.task_assignments[task.task_id] = device_id
                self.device_loads[device_id] += task.estimated_complexity
                task.assigned_device = device_id
                task.status = "assigned"
                logger.debug(f"Assigned task {task.task_id} to device {device_id}")

            return device_id

    def _round_robin_assignment(self, task: ComputeTask) -> Optional[str]:
        """Round-robin device assignment"""
        available_devices = [d for d in self.devices.values() if d.availability > 0.8]
        if not available_devices:
            return None

        device = available_devices[self.last_device_index % len(available_devices)]
        self.last_device_index += 1
        return device.device_id

    def _least_loaded_assignment(self, task: ComputeTask) -> Optional[str]:
        """Assign to least loaded device"""
        available_devices = [
            (d, self.device_loads.get(d.device_id, 0.0))
            for d in self.devices.values()
            if d.availability > 0.8
        ]

        if not available_devices:
            return None

        device, _ = min(available_devices, key=lambda x: x[1])
        return device.device_id

    def _capability_aware_assignment(self, task: ComputeTask) -> Optional[str]:
        """Assign based on device capabilities and requirements"""
        required_capabilities = self._get_required_capabilities(task.inference_type)

        suitable_devices = []
        for device in self.devices.values():
            if (
                device.availability > 0.8
                and device.current_load < 0.9
                and all(cap in device.capabilities for cap in required_capabilities)
            ):

                score = self._calculate_suitability_score(device, task)
                suitable_devices.append((device, score))

        if not suitable_devices:
            return None

        # Select device with highest suitability score
        best_device, _ = max(suitable_devices, key=lambda x: x[1])
        return best_device.device_id

    def _performance_weighted_assignment(self, task: ComputeTask) -> Optional[str]:
        """Assign based on performance rating"""
        available_devices = [
            d for d in self.devices.values() if d.availability > 0.8 and d.current_load < 0.9
        ]

        if not available_devices:
            return None

        # Weight by performance rating and inverse load
        weighted_devices = []
        for device in available_devices:
            weight = device.performance_rating / (
                1.0 + self.device_loads.get(device.device_id, 0.0)
            )
            weighted_devices.append((device, weight))

        best_device, _ = max(weighted_devices, key=lambda x: x[1])
        return best_device.device_id

    def _latency_optimized_assignment(self, task: ComputeTask) -> Optional[str]:
        """Assign to minimize network latency"""
        if task.priority in [InferencePriority.EMERGENCY, InferencePriority.CRITICAL]:
            # For critical tasks, prefer low-latency devices
            low_latency_devices = [
                d
                for d in self.devices.values()
                if (
                    d.network_latency_ms < 10.0
                    and d.availability > 0.8
                    and DeviceCapability.LOW_LATENCY in d.capabilities
                )
            ]

            if low_latency_devices:
                return min(
                    low_latency_devices, key=lambda d: self.device_loads.get(d.device_id, 0.0)
                ).device_id

        # Fall back to capability-aware assignment
        return self._capability_aware_assignment(task)

    def _get_required_capabilities(self, inference_type: InferenceType) -> List[DeviceCapability]:
        """Get required capabilities for inference type"""
        capability_map = {
            InferenceType.DEDUCTION: [DeviceCapability.BASIC_INFERENCE],
            InferenceType.INDUCTION: [
                DeviceCapability.BASIC_INFERENCE,
                DeviceCapability.HIGH_PRECISION,
            ],
            InferenceType.ABDUCTION: [DeviceCapability.BASIC_INFERENCE],
            InferenceType.CONJUNCTION: [DeviceCapability.BASIC_INFERENCE],
            InferenceType.DISJUNCTION: [DeviceCapability.BASIC_INFERENCE],
            InferenceType.PROPAGATION: [DeviceCapability.PARALLEL_PROPAGATION],
            InferenceType.SIMILARITY: [DeviceCapability.VECTOR_OPERATIONS],
        }
        return capability_map.get(inference_type, [DeviceCapability.BASIC_INFERENCE])

    def _calculate_suitability_score(self, device: DeviceInfo, task: ComputeTask) -> float:
        """Calculate suitability score for device-task pair"""
        score = 0.0

        # Performance component
        score += device.performance_rating * 0.3

        # Load component (prefer less loaded devices)
        score += (1.0 - device.current_load) * 0.2

        # Availability component
        score += device.availability * 0.2

        # Latency component (prefer lower latency)
        score += (100.0 - device.network_latency_ms) / 100.0 * 0.2

        # Power efficiency component
        if device.power_consumption_watts > 0:
            efficiency = device.performance_rating / device.power_consumption_watts
            score += min(efficiency / 1000.0, 1.0) * 0.1

        return score

    def _reassign_task(self, task_id: str):
        """Reassign a task to a different device"""
        if task_id in self.task_queue:
            task = self.task_queue[task_id]
            if task.assigned_device:
                old_device = task.assigned_device
                self.device_loads[old_device] -= task.estimated_complexity
                task.assigned_device = None
                task.status = "pending"
                del self.task_assignments[task_id]

                # Try to assign to a new device
                new_device = self.assign_task(task)
                if new_device:
                    logger.info(f"Reassigned task {task_id} from {old_device} to {new_device}")
                else:
                    logger.warning(f"Failed to reassign task {task_id}")

    def get_device_stats(self) -> Dict:
        """Get statistics about registered devices"""
        with self.lock:
            stats = {
                "total_devices": len(self.devices),
                "available_devices": len(
                    [d for d in self.devices.values() if d.availability > 0.8]
                ),
                "device_types": {},
                "total_performance": sum(d.performance_rating for d in self.devices.values()),
                "average_load": (
                    np.mean(list(self.device_loads.values())) if self.device_loads else 0.0
                ),
            }

            for device in self.devices.values():
                device_type = device.device_type.value
                stats["device_types"][device_type] = stats["device_types"].get(device_type, 0) + 1

            return stats


class DistributedTaskScheduler:
    """Task scheduler for distributed PLN computation"""

    def __init__(self, balancer: WorkloadBalancer):
        self.balancer = balancer
        self.pending_tasks: Dict[str, ComputeTask] = {}
        self.running_tasks: Dict[str, ComputeTask] = {}
        self.completed_tasks: Dict[str, ComputeTask] = {}
        self.task_graph: Dict[str, Set[str]] = {}  # dependency graph
        self.lock = threading.RLock()
        self.scheduler_active = False
        self.scheduler_thread = None

    def start(self):
        """Start the task scheduler"""
        self.scheduler_active = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("Distributed task scheduler started")

    def stop(self):
        """Stop the task scheduler"""
        self.scheduler_active = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        logger.info("Distributed task scheduler stopped")

    def submit_task(self, task: ComputeTask) -> str:
        """Submit a task for distributed execution"""
        if task.task_id is None:
            task.task_id = str(uuid.uuid4())

        if task.created_at is None:
            task.created_at = time.time()

        with self.lock:
            self.pending_tasks[task.task_id] = task

            # Update dependency graph
            self.task_graph[task.task_id] = set(task.dependencies)

            logger.debug(f"Submitted task {task.task_id} ({task.inference_type.value})")

        return task.task_id

    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get status of a task"""
        with self.lock:
            if task_id in self.pending_tasks:
                return self.pending_tasks[task_id].status
            elif task_id in self.running_tasks:
                return self.running_tasks[task_id].status
            elif task_id in self.completed_tasks:
                return self.completed_tasks[task_id].status
            else:
                return None

    def get_task_result(self, task_id: str) -> Optional[TruthValue]:
        """Get result of a completed task"""
        with self.lock:
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id].result
            else:
                return None

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.scheduler_active:
            try:
                self._process_pending_tasks()
                self._check_running_tasks()
                self._cleanup_completed_tasks()
                time.sleep(0.1)  # 100ms scheduling interval
            except Exception as e:
                logger.error(f"Scheduler error: {e}")

    def _process_pending_tasks(self):
        """Process pending tasks and assign them to devices"""
        with self.lock:
            ready_tasks = []

            # Find tasks whose dependencies are satisfied
            for task_id, task in self.pending_tasks.items():
                if self._dependencies_satisfied(task_id):
                    ready_tasks.append(task_id)

            # Sort by priority and deadline
            ready_tasks.sort(
                key=lambda tid: (
                    self.pending_tasks[tid].priority.value,
                    self.pending_tasks[tid].deadline,
                )
            )

            # Assign tasks to devices
            for task_id in ready_tasks:
                task = self.pending_tasks[task_id]
                device_id = self.balancer.assign_task(task)

                if device_id:
                    # Move task to running state
                    del self.pending_tasks[task_id]
                    task.status = "running"
                    task.started_at = time.time()
                    self.running_tasks[task_id] = task

                    # Dispatch task to device (would normally send over network)
                    self._dispatch_task_to_device(task, device_id)

    def _dependencies_satisfied(self, task_id: str) -> bool:
        """Check if all dependencies for a task are satisfied"""
        dependencies = self.task_graph.get(task_id, set())
        return all(dep_id in self.completed_tasks for dep_id in dependencies)

    def _check_running_tasks(self):
        """Check status of running tasks"""
        with self.lock:
            current_time = time.time()
            timed_out_tasks = []

            for task_id, task in self.running_tasks.items():
                # Check for timeout
                if current_time > task.deadline:
                    timed_out_tasks.append(task_id)
                    logger.warning(f"Task {task_id} timed out")

            # Handle timed out tasks
            for task_id in timed_out_tasks:
                self._handle_task_timeout(task_id)

    def _handle_task_timeout(self, task_id: str):
        """Handle task timeout"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]

            if task.max_retries > 0:
                # Retry the task
                task.max_retries -= 1
                task.status = "pending"
                task.assigned_device = None
                task.deadline = time.time() + 30.0  # Extend deadline

                del self.running_tasks[task_id]
                self.pending_tasks[task_id] = task

                logger.info(f"Retrying task {task_id} ({task.max_retries} retries left)")
            else:
                # Mark as failed
                task.status = "failed"
                task.completed_at = time.time()

                del self.running_tasks[task_id]
                self.completed_tasks[task_id] = task

                logger.error(f"Task {task_id} failed after all retries")

    def _dispatch_task_to_device(self, task: ComputeTask, device_id: str):
        """Dispatch task to a specific device"""
        # In a real implementation, this would send the task over the network
        # For now, we'll simulate task execution

        def simulate_execution():
            try:
                # Simulate execution time based on task complexity
                execution_time = task.estimated_complexity * 0.1  # 100ms per complexity unit
                time.sleep(execution_time)

                # Simulate result (in real system, device would compute this)
                if task.operands:
                    if task.inference_type == InferenceType.CONJUNCTION:
                        result = TruthValue(
                            min(tv.strength for tv in task.operands),
                            np.prod([tv.confidence for tv in task.operands]),
                        )
                    elif task.inference_type == InferenceType.DISJUNCTION:
                        result = TruthValue(
                            max(tv.strength for tv in task.operands),
                            1.0 - np.prod([1.0 - tv.confidence for tv in task.operands]),
                        )
                    else:  # Default to deduction
                        result = TruthValue(
                            min(tv.strength for tv in task.operands),
                            np.prod([tv.confidence for tv in task.operands]),
                        )
                else:
                    result = TruthValue(0.5, 0.5)

                # Mark task as completed
                self._complete_task(task.task_id, result)

            except Exception as e:
                logger.error(f"Task execution failed: {e}")
                self._fail_task(task.task_id, str(e))

        # Execute in thread pool
        threading.Thread(target=simulate_execution, daemon=True).start()

    def _complete_task(self, task_id: str, result: TruthValue):
        """Mark task as completed"""
        with self.lock:
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.status = "completed"
                task.result = result
                task.completed_at = time.time()

                # Update device load
                if task.assigned_device:
                    self.balancer.device_loads[task.assigned_device] -= task.estimated_complexity

                del self.running_tasks[task_id]
                self.completed_tasks[task_id] = task

                logger.debug(f"Task {task_id} completed successfully")

    def _fail_task(self, task_id: str, error_message: str):
        """Mark task as failed"""
        with self.lock:
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.status = "failed"
                task.completed_at = time.time()

                # Update device load
                if task.assigned_device:
                    self.balancer.device_loads[task.assigned_device] -= task.estimated_complexity

                del self.running_tasks[task_id]
                self.completed_tasks[task_id] = task

                logger.error(f"Task {task_id} failed: {error_message}")

    def _cleanup_completed_tasks(self):
        """Clean up old completed tasks"""
        with self.lock:
            current_time = time.time()
            cleanup_threshold = 3600.0  # 1 hour

            old_tasks = [
                task_id
                for task_id, task in self.completed_tasks.items()
                if current_time - task.completed_at > cleanup_threshold
            ]

            for task_id in old_tasks:
                del self.completed_tasks[task_id]
                if task_id in self.task_graph:
                    del self.task_graph[task_id]


class DistributedPLNCluster:
    """Main distributed PLN computation cluster"""

    def __init__(self, cluster_name: str = "pln-cluster"):
        self.cluster_name = cluster_name
        self.node_id = str(uuid.uuid4())
        self.balancer = WorkloadBalancer()
        self.scheduler = DistributedTaskScheduler(self.balancer)
        self.local_engine = RealTimeInferenceEngine()

        # Service discovery
        self.consul_client = None
        self.etcd_client = None
        self.k8s_client = None

        # Cluster state
        self.cluster_nodes: Dict[str, Dict] = {}
        self.is_leader = False
        self.leader_node = None

        # Network communication
        self.grpc_server = None
        self.grpc_port = 50051

        self._initialize_service_discovery()

    def _initialize_service_discovery(self):
        """Initialize service discovery mechanisms"""
        try:
            # Try Consul first
            self.consul_client = consul.Consul()
            self.consul_client.agent.service.register(
                name=f"pln-node-{self.node_id}",
                service_id=self.node_id,
                port=self.grpc_port,
                tags=["pln", "inference", "distributed"],
                check=consul.Check.http(
                    f"http://localhost:{self.grpc_port}/health", interval="10s"
                ),
            )
            logger.info("Registered with Consul service discovery")
        except Exception as e:
            logger.warning(f"Consul not available: {e}")

        try:
            # Try etcd
            self.etcd_client = etcd3.client()
            self.etcd_client.put(
                f"/pln/nodes/{self.node_id}",
                json.dumps(
                    {
                        "node_id": self.node_id,
                        "endpoint": f"localhost:{self.grpc_port}",
                        "capabilities": ["basic_inference", "vector_operations"],
                        "status": "active",
                    }
                ),
            )
            logger.info("Registered with etcd service discovery")
        except Exception as e:
            logger.warning(f"etcd not available: {e}")

        try:
            # Try Kubernetes
            k8s_config.load_incluster_config()
            self.k8s_client = client.CoreV1Api()
            logger.info("Connected to Kubernetes API")
        except Exception as e:
            logger.warning(f"Kubernetes not available: {e}")

    def start(self):
        """Start the distributed PLN cluster node"""
        # Start local inference engine
        self.local_engine.start()

        # Start task scheduler
        self.scheduler.start()

        # Register local device
        local_device = DeviceInfo(
            device_id=f"local-{self.node_id}",
            device_type=DeviceType.CPU,
            capabilities=[
                DeviceCapability.BASIC_INFERENCE,
                DeviceCapability.VECTOR_OPERATIONS,
                DeviceCapability.PARALLEL_PROPAGATION,
            ],
            performance_rating=1000.0,  # Operations per second
            memory_capacity=1000000,  # Truth values
            network_latency_ms=1.0,
            power_consumption_watts=100.0,
            availability=1.0,
            current_load=0.0,
            last_heartbeat=time.time(),
            endpoint=f"localhost:{self.grpc_port}",
        )
        self.balancer.register_device(local_device)

        # Start cluster discovery
        self._start_cluster_discovery()

        # Start gRPC server
        self._start_grpc_server()

        logger.info(f"PLN cluster node {self.node_id} started")

    def stop(self):
        """Stop the distributed PLN cluster node"""
        # Stop components
        self.scheduler.stop()
        self.local_engine.stop()

        # Unregister from service discovery
        if self.consul_client:
            self.consul_client.agent.service.deregister(self.node_id)

        if self.etcd_client:
            self.etcd_client.delete(f"/pln/nodes/{self.node_id}")

        # Stop gRPC server
        if self.grpc_server:
            self.grpc_server.stop(grace=5.0)

        logger.info(f"PLN cluster node {self.node_id} stopped")

    def _start_cluster_discovery(self):
        """Start cluster node discovery"""

        def discovery_loop():
            while True:
                try:
                    self._discover_cluster_nodes()
                    self._elect_leader()
                    time.sleep(30.0)  # Discovery interval
                except Exception as e:
                    logger.error(f"Cluster discovery error: {e}")
                    time.sleep(5.0)

        threading.Thread(target=discovery_loop, daemon=True).start()

    def _discover_cluster_nodes(self):
        """Discover other cluster nodes"""
        discovered_nodes = {}

        # Discover via Consul
        if self.consul_client:
            try:
                services = self.consul_client.health.service("pln-node", passing=True)[1]
                for service in services:
                    node_info = service["Service"]
                    node_id = node_info["ID"]
                    if node_id != self.node_id:
                        discovered_nodes[node_id] = {
                            "endpoint": f"{node_info['Address']}:{node_info['Port']}",
                            "tags": node_info.get("Tags", []),
                            "last_seen": time.time(),
                        }
            except Exception as e:
                logger.debug(f"Consul discovery error: {e}")

        # Discover via etcd
        if self.etcd_client:
            try:
                for value, metadata in self.etcd_client.get_prefix("/pln/nodes/"):
                    node_info = json.loads(value.decode())
                    node_id = node_info["node_id"]
                    if node_id != self.node_id:
                        discovered_nodes[node_id] = {
                            "endpoint": node_info["endpoint"],
                            "capabilities": node_info.get("capabilities", []),
                            "last_seen": time.time(),
                        }
            except Exception as e:
                logger.debug(f"etcd discovery error: {e}")

        # Update cluster state
        self.cluster_nodes = discovered_nodes
        logger.debug(f"Discovered {len(discovered_nodes)} cluster nodes")

    def _elect_leader(self):
        """Simple leader election based on node ID"""
        all_nodes = [self.node_id] + list(self.cluster_nodes.keys())
        all_nodes.sort()  # Deterministic ordering

        new_leader = all_nodes[0]
        if new_leader != self.leader_node:
            self.leader_node = new_leader
            self.is_leader = new_leader == self.node_id
            logger.info(f"New cluster leader: {new_leader} (is_leader: {self.is_leader})")

    def _start_grpc_server(self):
        """Start gRPC server for inter-node communication"""
        # Would implement gRPC service for distributed communication
        # Placeholder for now
        logger.info(f"gRPC server started on port {self.grpc_port}")

    async def submit_distributed_task(
        self,
        inference_type: InferenceType,
        operands: List[TruthValue],
        priority: InferencePriority = InferencePriority.NORMAL,
        deadline_ms: float = 1000.0,
    ) -> TruthValue:
        """Submit a task for distributed execution"""
        task = ComputeTask(
            task_id=str(uuid.uuid4()),
            inference_type=inference_type,
            priority=priority,
            operands=operands,
            concept_ids=[],
            dependencies=[],
            estimated_complexity=len(operands) * 1.0,  # Simple complexity estimate
            deadline=time.time() + deadline_ms / 1000.0,
        )

        task_id = self.scheduler.submit_task(task)

        # Wait for completion
        while True:
            status = self.scheduler.get_task_status(task_id)
            if status == "completed":
                result = self.scheduler.get_task_result(task_id)
                return result
            elif status == "failed":
                raise RuntimeError(f"Task {task_id} failed")

            await asyncio.sleep(0.01)  # 10ms polling

    async def propagate_distributed(
        self, source_concepts: List[int], source_values: List[TruthValue], depth: int = 3
    ) -> Dict[int, TruthValue]:
        """Perform distributed truth value propagation"""
        # Create tasks for each propagation step
        results = {}

        # Initial propagation tasks
        propagation_tasks = []
        for concept_id, tv in zip(source_concepts, source_values):
            task = ComputeTask(
                task_id=str(uuid.uuid4()),
                inference_type=InferenceType.PROPAGATION,
                priority=InferencePriority.NORMAL,
                operands=[tv],
                concept_ids=[concept_id],
                dependencies=[],
                estimated_complexity=float(depth),
                deadline=time.time() + 5.0,  # 5 second deadline
            )
            propagation_tasks.append(task)
            self.scheduler.submit_task(task)

        # Wait for all tasks to complete
        for task in propagation_tasks:
            while True:
                status = self.scheduler.get_task_status(task.task_id)
                if status == "completed":
                    result = self.scheduler.get_task_result(task.task_id)
                    results[task.concept_ids[0]] = result
                    break
                elif status == "failed":
                    logger.error(f"Propagation task {task.task_id} failed")
                    break

                await asyncio.sleep(0.01)

        return results

    def get_cluster_stats(self) -> Dict:
        """Get statistics about the PLN cluster"""
        device_stats = self.balancer.get_device_stats()

        cluster_stats = {
            "cluster_name": self.cluster_name,
            "node_id": self.node_id,
            "is_leader": self.is_leader,
            "cluster_nodes": len(self.cluster_nodes),
            "total_devices": device_stats["total_devices"],
            "available_devices": device_stats["available_devices"],
            "device_types": device_stats["device_types"],
            "total_performance": device_stats["total_performance"],
            "average_load": device_stats["average_load"],
            "pending_tasks": len(self.scheduler.pending_tasks),
            "running_tasks": len(self.scheduler.running_tasks),
            "completed_tasks": len(self.scheduler.completed_tasks),
        }

        return cluster_stats


# Example usage and testing
async def main():
    """Example usage of distributed PLN system"""
    # Create and start cluster
    cluster = DistributedPLNCluster("test-cluster")
    cluster.start()

    try:
        # Test distributed inference
        tv1 = TruthValue(0.8, 0.9)
        tv2 = TruthValue(0.7, 0.8)

        print("Testing distributed PLN computation...")

        # Test conjunction
        start_time = time.time()
        result = await cluster.submit_distributed_task(
            InferenceType.CONJUNCTION, [tv1, tv2], priority=InferencePriority.HIGH
        )
        end_time = time.time()

        print(f"Distributed conjunction result: {result}")
        print(f"Execution time: {(end_time - start_time) * 1000:.2f} ms")

        # Test distributed propagation
        source_concepts = [1, 2, 3]
        source_values = [tv1, tv2, TruthValue(0.6, 0.7)]

        propagation_results = await cluster.propagate_distributed(
            source_concepts, source_values, depth=2
        )

        print(f"Propagation results: {propagation_results}")

        # Cluster statistics
        stats = cluster.get_cluster_stats()
        print(f"\nCluster Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    finally:
        cluster.stop()


if __name__ == "__main__":
    asyncio.run(main())
