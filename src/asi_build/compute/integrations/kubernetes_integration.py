"""
Kubernetes Integration - Integrates compute pool with Kubernetes scheduler
"""

import asyncio
import logging
import json
import yaml
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
import time
import uuid


try:
    from kubernetes import client, config, watch
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    
    # Mock classes for when kubernetes is not available
    class client:
        class V1Pod: pass
        class V1Node: pass
        class V1ConfigMap: pass
        class CoreV1Api: pass
        class CustomObjectsApi: pass
    
    class config:
        @staticmethod
        def load_incluster_config(): pass
        @staticmethod
        def load_kube_config(): pass
    
    class watch:
        class Watch: pass
    
    class ApiException(Exception): pass


@dataclass
class KubernetesPodSpec:
    """Kubernetes pod specification for compute pool jobs"""
    name: str
    image: str
    command: List[str] = field(default_factory=list)
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)
    node_selector: Dict[str, str] = field(default_factory=dict)
    tolerations: List[Dict[str, Any]] = field(default_factory=list)
    annotations: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_k8s_pod(self, namespace: str = "default") -> Dict[str, Any]:
        """Convert to Kubernetes pod manifest"""
        return {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": self.name,
                "namespace": namespace,
                "labels": {
                    "app": "compute-pool-job",
                    "managed-by": "kenny-compute-pool",
                    **self.labels
                },
                "annotations": self.annotations
            },
            "spec": {
                "containers": [{
                    "name": "main",
                    "image": self.image,
                    "command": self.command,
                    "args": self.args,
                    "env": [{"name": k, "value": v} for k, v in self.env.items()],
                    "resources": self.resources
                }],
                "nodeSelector": self.node_selector,
                "tolerations": self.tolerations,
                "restartPolicy": "Never"
            }
        }


@dataclass
class KubernetesJobStatus:
    """Kubernetes job status tracking"""
    pod_name: str
    phase: str  # Pending, Running, Succeeded, Failed, Unknown
    node_name: Optional[str] = None
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pod_name": self.pod_name,
            "phase": self.phase,
            "node_name": self.node_name,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "resource_usage": self.resource_usage,
            "events": self.events
        }


class KubernetesIntegration:
    """
    Advanced Kubernetes integration for the compute pool system
    """
    
    def __init__(self, namespace: str = "default", config_path: Optional[str] = None):
        self.namespace = namespace
        self.config_path = config_path
        self.logger = logging.getLogger("kubernetes_integration")
        
        # Kubernetes clients
        self.core_v1_api: Optional[client.CoreV1Api] = None
        self.custom_objects_api: Optional[client.CustomObjectsApi] = None
        
        # Job tracking
        self.active_pods: Dict[str, KubernetesJobStatus] = {}
        self.job_id_to_pod: Dict[str, str] = {}  # job_id -> pod_name
        self.pod_to_job_id: Dict[str, str] = {}  # pod_name -> job_id
        
        # Resource monitoring
        self.node_resources: Dict[str, Dict[str, Any]] = {}
        self.resource_quotas: Dict[str, Dict[str, Any]] = {}
        
        # Event watching
        self.pod_watcher: Optional[watch.Watch] = None
        self.node_watcher: Optional[watch.Watch] = None
        self.watch_tasks: List[asyncio.Task] = []
        
        # Statistics
        self._stats = {
            "total_pods_created": 0,
            "active_pods": 0,
            "completed_pods": 0,
            "failed_pods": 0,
            "nodes_available": 0,
            "total_cpu_capacity": 0,
            "total_memory_capacity": 0,
            "total_gpu_capacity": 0
        }
        
    async def initialize(self) -> None:
        """Initialize Kubernetes integration"""
        if not KUBERNETES_AVAILABLE:
            raise RuntimeError("Kubernetes client library not available")
        
        self.logger.info("Initializing Kubernetes integration")
        
        try:
            # Load Kubernetes configuration
            if self.config_path:
                config.load_kube_config(config_file=self.config_path)
            else:
                try:
                    config.load_incluster_config()
                    self.logger.info("Loaded in-cluster Kubernetes configuration")
                except:
                    config.load_kube_config()
                    self.logger.info("Loaded local Kubernetes configuration")
            
            # Initialize API clients
            self.core_v1_api = client.CoreV1Api()
            self.custom_objects_api = client.CustomObjectsApi()
            
            # Verify connection
            await self._verify_connection()
            
            # Load cluster information
            await self._load_cluster_info()
            
            # Start event watchers
            await self._start_event_watchers()
            
            self.logger.info("Kubernetes integration initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing Kubernetes integration: {e}")
            raise
            
    async def _verify_connection(self) -> None:
        """Verify connection to Kubernetes cluster"""
        try:
            nodes = self.core_v1_api.list_node()
            self.logger.info(f"Connected to Kubernetes cluster with {len(nodes.items)} nodes")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Kubernetes cluster: {e}")
            raise
            
    async def _load_cluster_info(self) -> None:
        """Load cluster node and resource information"""
        try:
            # Get node information
            nodes = self.core_v1_api.list_node()
            
            total_cpu = 0
            total_memory = 0
            total_gpu = 0
            
            for node in nodes.items:
                node_name = node.metadata.name
                
                # Get node capacity
                capacity = node.status.capacity or {}
                allocatable = node.status.allocatable or {}
                
                cpu_capacity = self._parse_cpu_quantity(capacity.get("cpu", "0"))
                memory_capacity = self._parse_memory_quantity(capacity.get("memory", "0"))
                gpu_capacity = int(capacity.get("nvidia.com/gpu", "0"))
                
                self.node_resources[node_name] = {
                    "capacity": {
                        "cpu": cpu_capacity,
                        "memory": memory_capacity,
                        "gpu": gpu_capacity
                    },
                    "allocatable": {
                        "cpu": self._parse_cpu_quantity(allocatable.get("cpu", "0")),
                        "memory": self._parse_memory_quantity(allocatable.get("memory", "0")),
                        "gpu": int(allocatable.get("nvidia.com/gpu", "0"))
                    },
                    "labels": node.metadata.labels or {},
                    "conditions": [
                        {
                            "type": condition.type,
                            "status": condition.status,
                            "reason": condition.reason
                        }
                        for condition in (node.status.conditions or [])
                    ]
                }
                
                total_cpu += cpu_capacity
                total_memory += memory_capacity
                total_gpu += gpu_capacity
            
            # Update statistics
            self._stats["nodes_available"] = len(nodes.items)
            self._stats["total_cpu_capacity"] = total_cpu
            self._stats["total_memory_capacity"] = total_memory
            self._stats["total_gpu_capacity"] = total_gpu
            
            self.logger.info(
                f"Loaded cluster info: {len(nodes.items)} nodes, "
                f"{total_cpu} CPU cores, {total_memory/1024/1024/1024:.1f} GB memory, "
                f"{total_gpu} GPUs"
            )
            
        except Exception as e:
            self.logger.error(f"Error loading cluster info: {e}")
            
    def _parse_cpu_quantity(self, cpu_str: str) -> float:
        """Parse Kubernetes CPU quantity string"""
        if not cpu_str:
            return 0.0
        
        cpu_str = str(cpu_str).lower()
        
        if cpu_str.endswith("m"):
            return float(cpu_str[:-1]) / 1000.0
        elif cpu_str.endswith("n"):
            return float(cpu_str[:-1]) / 1000000000.0
        else:
            return float(cpu_str)
            
    def _parse_memory_quantity(self, memory_str: str) -> int:
        """Parse Kubernetes memory quantity string to bytes"""
        if not memory_str:
            return 0
        
        memory_str = str(memory_str).upper()
        
        multipliers = {
            "K": 1024,
            "M": 1024**2,
            "G": 1024**3,
            "T": 1024**4,
            "KI": 1024,
            "MI": 1024**2,
            "GI": 1024**3,
            "TI": 1024**4
        }
        
        for suffix, multiplier in multipliers.items():
            if memory_str.endswith(suffix):
                return int(float(memory_str[:-len(suffix)]) * multiplier)
        
        return int(memory_str)
        
    async def _start_event_watchers(self) -> None:
        """Start Kubernetes event watchers"""
        try:
            self.pod_watcher = watch.Watch()
            self.node_watcher = watch.Watch()
            
            # Start pod watcher
            pod_watch_task = asyncio.create_task(self._watch_pods())
            self.watch_tasks.append(pod_watch_task)
            
            # Start node watcher
            node_watch_task = asyncio.create_task(self._watch_nodes())
            self.watch_tasks.append(node_watch_task)
            
            self.logger.info("Started Kubernetes event watchers")
            
        except Exception as e:
            self.logger.error(f"Error starting event watchers: {e}")
            
    async def _watch_pods(self) -> None:
        """Watch pod events"""
        try:
            while True:
                try:
                    for event in self.pod_watcher.stream(
                        self.core_v1_api.list_namespaced_pod,
                        namespace=self.namespace,
                        label_selector="managed-by=kenny-compute-pool",
                        timeout_seconds=30
                    ):
                        await self._handle_pod_event(event)
                        
                except Exception as e:
                    self.logger.error(f"Error in pod watcher: {e}")
                    await asyncio.sleep(5.0)
                    
        except asyncio.CancelledError:
            self.logger.info("Pod watcher cancelled")
            
    async def _watch_nodes(self) -> None:
        """Watch node events"""
        try:
            while True:
                try:
                    for event in self.node_watcher.stream(
                        self.core_v1_api.list_node,
                        timeout_seconds=30
                    ):
                        await self._handle_node_event(event)
                        
                except Exception as e:
                    self.logger.error(f"Error in node watcher: {e}")
                    await asyncio.sleep(5.0)
                    
        except asyncio.CancelledError:
            self.logger.info("Node watcher cancelled")
            
    async def _handle_pod_event(self, event: Dict[str, Any]) -> None:
        """Handle pod events from Kubernetes"""
        try:
            event_type = event["type"]  # ADDED, MODIFIED, DELETED
            pod = event["object"]
            
            pod_name = pod.metadata.name
            phase = pod.status.phase if pod.status else "Unknown"
            
            # Update pod status
            if pod_name in self.active_pods:
                self.active_pods[pod_name].phase = phase
                self.active_pods[pod_name].node_name = pod.spec.node_name if pod.spec else None
                
                if pod.status:
                    self.active_pods[pod_name].start_time = pod.status.start_time
                    
                    if hasattr(pod.status, 'container_statuses') and pod.status.container_statuses:
                        container_status = pod.status.container_statuses[0]
                        if hasattr(container_status.state, 'terminated') and container_status.state.terminated:
                            self.active_pods[pod_name].completion_time = container_status.state.terminated.finished_at
            
            # Log significant events
            if event_type in ["ADDED", "DELETED"] or phase in ["Running", "Succeeded", "Failed"]:
                self.logger.info(f"Pod {pod_name}: {event_type} - {phase}")
                
            # Update statistics
            if phase == "Running":
                self._stats["active_pods"] = len([
                    p for p in self.active_pods.values() if p.phase == "Running"
                ])
            elif phase == "Succeeded":
                self._stats["completed_pods"] += 1
            elif phase == "Failed":
                self._stats["failed_pods"] += 1
                
        except Exception as e:
            self.logger.error(f"Error handling pod event: {e}")
            
    async def _handle_node_event(self, event: Dict[str, Any]) -> None:
        """Handle node events from Kubernetes"""
        try:
            event_type = event["type"]
            node = event["object"]
            
            node_name = node.metadata.name
            
            if event_type == "MODIFIED":
                # Update node resource information
                capacity = node.status.capacity or {}
                
                if node_name in self.node_resources:
                    self.node_resources[node_name]["capacity"] = {
                        "cpu": self._parse_cpu_quantity(capacity.get("cpu", "0")),
                        "memory": self._parse_memory_quantity(capacity.get("memory", "0")),
                        "gpu": int(capacity.get("nvidia.com/gpu", "0"))
                    }
                    
                    self.node_resources[node_name]["conditions"] = [
                        {
                            "type": condition.type,
                            "status": condition.status,
                            "reason": condition.reason
                        }
                        for condition in (node.status.conditions or [])
                    ]
                    
        except Exception as e:
            self.logger.error(f"Error handling node event: {e}")
            
    async def submit_job(
        self,
        job_id: str,
        pod_spec: KubernetesPodSpec,
        resource_requirements: Dict[str, Any]
    ) -> bool:
        """Submit a job to Kubernetes"""
        try:
            # Update pod spec with resource requirements
            pod_spec.resources = self._convert_resource_requirements(resource_requirements)
            
            # Generate unique pod name
            pod_name = f"{pod_spec.name}-{job_id[:8]}-{int(time.time())}"
            pod_spec.name = pod_name
            
            # Add job tracking labels
            pod_spec.labels.update({
                "job-id": job_id,
                "submitted-at": str(int(time.time()))
            })
            
            # Create pod manifest
            pod_manifest = pod_spec.to_k8s_pod(self.namespace)
            
            # Submit to Kubernetes
            created_pod = self.core_v1_api.create_namespaced_pod(
                namespace=self.namespace,
                body=pod_manifest
            )
            
            # Track job
            job_status = KubernetesJobStatus(
                pod_name=pod_name,
                phase="Pending"
            )
            
            self.active_pods[pod_name] = job_status
            self.job_id_to_pod[job_id] = pod_name
            self.pod_to_job_id[pod_name] = job_id
            
            self._stats["total_pods_created"] += 1
            
            self.logger.info(f"Submitted job {job_id} as pod {pod_name}")
            return True
            
        except ApiException as e:
            self.logger.error(f"Kubernetes API error submitting job {job_id}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error submitting job {job_id}: {e}")
            return False
            
    def _convert_resource_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Convert compute pool resource requirements to Kubernetes format"""
        k8s_resources = {
            "requests": {},
            "limits": {}
        }
        
        # CPU
        if "cpu_cores" in requirements:
            cpu_cores = requirements["cpu_cores"]
            k8s_resources["requests"]["cpu"] = f"{cpu_cores}"
            k8s_resources["limits"]["cpu"] = f"{cpu_cores * 1.2}"  # Allow 20% burst
        
        # Memory
        if "memory" in requirements:
            memory_gb = requirements["memory"]
            k8s_resources["requests"]["memory"] = f"{memory_gb}Gi"
            k8s_resources["limits"]["memory"] = f"{memory_gb}Gi"
        
        # GPU
        if "gpu_count" in requirements and requirements["gpu_count"] > 0:
            gpu_count = requirements["gpu_count"]
            k8s_resources["requests"]["nvidia.com/gpu"] = str(gpu_count)
            k8s_resources["limits"]["nvidia.com/gpu"] = str(gpu_count)
        
        # Storage (ephemeral)
        if "storage" in requirements:
            storage_gb = requirements["storage"]
            k8s_resources["requests"]["ephemeral-storage"] = f"{storage_gb}Gi"
            k8s_resources["limits"]["ephemeral-storage"] = f"{storage_gb}Gi"
        
        return k8s_resources
        
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a Kubernetes job"""
        if job_id not in self.job_id_to_pod:
            return False
        
        pod_name = self.job_id_to_pod[job_id]
        
        try:
            # Delete the pod
            self.core_v1_api.delete_namespaced_pod(
                name=pod_name,
                namespace=self.namespace
            )
            
            # Clean up tracking
            if pod_name in self.active_pods:
                del self.active_pods[pod_name]
            del self.job_id_to_pod[job_id]
            del self.pod_to_job_id[pod_name]
            
            self.logger.info(f"Cancelled job {job_id} (pod {pod_name})")
            return True
            
        except ApiException as e:
            self.logger.error(f"Kubernetes API error cancelling job {job_id}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error cancelling job {job_id}: {e}")
            return False
            
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status from Kubernetes"""
        if job_id not in self.job_id_to_pod:
            return None
        
        pod_name = self.job_id_to_pod[job_id]
        
        if pod_name not in self.active_pods:
            return None
        
        return self.active_pods[pod_name].to_dict()
        
    async def get_cluster_resources(self) -> Dict[str, Any]:
        """Get current cluster resource availability"""
        try:
            # Get pod resource usage
            pods = self.core_v1_api.list_namespaced_pod(namespace=self.namespace)
            
            used_resources = {
                "cpu": 0.0,
                "memory": 0,
                "gpu": 0
            }
            
            for pod in pods.items:
                if pod.spec and pod.spec.containers:
                    for container in pod.spec.containers:
                        if container.resources and container.resources.requests:
                            requests = container.resources.requests
                            
                            if "cpu" in requests:
                                used_resources["cpu"] += self._parse_cpu_quantity(requests["cpu"])
                            
                            if "memory" in requests:
                                used_resources["memory"] += self._parse_memory_quantity(requests["memory"])
                            
                            if "nvidia.com/gpu" in requests:
                                used_resources["gpu"] += int(requests["nvidia.com/gpu"])
            
            # Calculate available resources
            available_resources = {
                "cpu": self._stats["total_cpu_capacity"] - used_resources["cpu"],
                "memory": self._stats["total_memory_capacity"] - used_resources["memory"],
                "gpu": self._stats["total_gpu_capacity"] - used_resources["gpu"]
            }
            
            return {
                "total": {
                    "cpu": self._stats["total_cpu_capacity"],
                    "memory": self._stats["total_memory_capacity"],
                    "gpu": self._stats["total_gpu_capacity"]
                },
                "used": used_resources,
                "available": available_resources,
                "nodes": len(self.node_resources)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cluster resources: {e}")
            return {}
            
    async def create_resource_quota(
        self,
        name: str,
        cpu_limit: Optional[float] = None,
        memory_limit: Optional[int] = None,
        gpu_limit: Optional[int] = None
    ) -> bool:
        """Create a Kubernetes ResourceQuota"""
        try:
            resource_quota = {
                "apiVersion": "v1",
                "kind": "ResourceQuota",
                "metadata": {
                    "name": name,
                    "namespace": self.namespace
                },
                "spec": {
                    "hard": {}
                }
            }
            
            if cpu_limit is not None:
                resource_quota["spec"]["hard"]["requests.cpu"] = f"{cpu_limit}"
                resource_quota["spec"]["hard"]["limits.cpu"] = f"{cpu_limit * 1.2}"
            
            if memory_limit is not None:
                memory_gi = memory_limit // (1024**3)
                resource_quota["spec"]["hard"]["requests.memory"] = f"{memory_gi}Gi"
                resource_quota["spec"]["hard"]["limits.memory"] = f"{memory_gi}Gi"
            
            if gpu_limit is not None:
                resource_quota["spec"]["hard"]["requests.nvidia.com/gpu"] = str(gpu_limit)
                resource_quota["spec"]["hard"]["limits.nvidia.com/gpu"] = str(gpu_limit)
            
            created_quota = self.core_v1_api.create_namespaced_resource_quota(
                namespace=self.namespace,
                body=resource_quota
            )
            
            self.resource_quotas[name] = created_quota.to_dict()
            
            self.logger.info(f"Created ResourceQuota: {name}")
            return True
            
        except ApiException as e:
            self.logger.error(f"Kubernetes API error creating ResourceQuota {name}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error creating ResourceQuota {name}: {e}")
            return False
            
    async def get_integration_status(self) -> Dict[str, Any]:
        """Get Kubernetes integration status"""
        return {
            "namespace": self.namespace,
            "statistics": self._stats.copy(),
            "active_pods": len(self.active_pods),
            "tracked_jobs": len(self.job_id_to_pod),
            "node_count": len(self.node_resources),
            "resource_quotas": len(self.resource_quotas),
            "watchers_running": len(self.watch_tasks)
        }
        
    async def apply_manifest(self, manifest: Dict[str, Any]) -> bool:
        """Apply a Kubernetes manifest"""
        try:
            api_version = manifest.get("apiVersion", "")
            kind = manifest.get("kind", "")
            
            if api_version == "v1" and kind == "Pod":
                created_object = self.core_v1_api.create_namespaced_pod(
                    namespace=self.namespace,
                    body=manifest
                )
            elif api_version == "v1" and kind == "ConfigMap":
                created_object = self.core_v1_api.create_namespaced_config_map(
                    namespace=self.namespace,
                    body=manifest
                )
            else:
                # Use custom objects API for other resources
                group, version = api_version.split("/") if "/" in api_version else ("", api_version)
                created_object = self.custom_objects_api.create_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=self.namespace,
                    plural=f"{kind.lower()}s",  # Simple pluralization
                    body=manifest
                )
            
            self.logger.info(f"Applied {kind}: {manifest.get('metadata', {}).get('name', 'unknown')}")
            return True
            
        except ApiException as e:
            self.logger.error(f"Kubernetes API error applying manifest: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error applying manifest: {e}")
            return False
            
    async def shutdown(self) -> None:
        """Shutdown Kubernetes integration"""
        self.logger.info("Shutting down Kubernetes integration")
        
        # Cancel watch tasks
        for task in self.watch_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Stop watchers
        if self.pod_watcher:
            self.pod_watcher.stop()
        if self.node_watcher:
            self.node_watcher.stop()
        
        self.logger.info("Kubernetes integration shutdown complete")