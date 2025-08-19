#!/usr/bin/env python3
"""
Kubernetes Integration Example - Demonstrates Kubernetes scheduler integration
"""

import asyncio
import logging
import time
import yaml
from pathlib import Path
import sys

# Add the compute pool to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pool_manager import ComputePoolManager, PoolConfig
from integrations.kubernetes_integration import (
    KubernetesIntegration, 
    KubernetesPodSpec
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def kubernetes_integration_demo():
    """Demonstrate Kubernetes integration"""
    logger.info("=== Kenny AGI Compute Pool - Kubernetes Integration Demo ===")
    
    try:
        # 1. Initialize Kubernetes integration
        k8s_integration = KubernetesIntegration(
            namespace="kenny-compute-pool"
        )
        
        await k8s_integration.initialize()
        logger.info("Kubernetes integration initialized")
        
        # 2. Get cluster resources
        cluster_resources = await k8s_integration.get_cluster_resources()
        logger.info(f"Cluster resources: {cluster_resources}")
        
        # 3. Submit jobs to Kubernetes
        
        # CPU-intensive job
        cpu_pod_spec = KubernetesPodSpec(
            name="cpu-intensive-job",
            image="python:3.9-slim",
            command=["python", "-c"],
            args=["import time; [x**2 for x in range(1000000)]; time.sleep(30); print('CPU job completed')"],
            labels={
                "job-type": "cpu-intensive",
                "demo": "kenny-compute-pool"
            }
        )
        
        cpu_job_id = "cpu-job-" + str(int(time.time()))
        resource_requirements = {
            "cpu_cores": 2,
            "memory": 4  # GB
        }
        
        success = await k8s_integration.submit_job(
            cpu_job_id,
            cpu_pod_spec,
            resource_requirements
        )
        
        if success:
            logger.info(f"Submitted CPU job: {cpu_job_id}")
        else:
            logger.error("Failed to submit CPU job")
        
        # Memory-intensive job
        memory_pod_spec = KubernetesPodSpec(
            name="memory-intensive-job",
            image="python:3.9-slim",
            command=["python", "-c"],
            args=["data = [i for i in range(5000000)]; import time; time.sleep(20); print(f'Memory job completed with {len(data)} items')"],
            labels={
                "job-type": "memory-intensive",
                "demo": "kenny-compute-pool"
            }
        )
        
        memory_job_id = "memory-job-" + str(int(time.time()))
        memory_requirements = {
            "cpu_cores": 1,
            "memory": 6  # GB
        }
        
        success = await k8s_integration.submit_job(
            memory_job_id,
            memory_pod_spec,
            memory_requirements
        )
        
        if success:
            logger.info(f"Submitted memory job: {memory_job_id}")
        else:
            logger.error("Failed to submit memory job")
        
        # GPU job (if GPUs available)
        gpu_pod_spec = KubernetesPodSpec(
            name="gpu-job",
            image="tensorflow/tensorflow:2.8.0-gpu",
            command=["python", "-c"],
            args=["import tensorflow as tf; print('GPU devices:', tf.config.list_physical_devices('GPU')); import time; time.sleep(25)"],
            labels={
                "job-type": "gpu-computation",
                "demo": "kenny-compute-pool"
            }
        )
        
        gpu_job_id = "gpu-job-" + str(int(time.time()))
        gpu_requirements = {
            "cpu_cores": 1,
            "memory": 4,
            "gpu_count": 1
        }
        
        success = await k8s_integration.submit_job(
            gpu_job_id,
            gpu_pod_spec,
            gpu_requirements
        )
        
        if success:
            logger.info(f"Submitted GPU job: {gpu_job_id}")
        else:
            logger.warning("Failed to submit GPU job (GPUs may not be available)")
        
        # 4. Monitor job statuses
        job_ids = [cpu_job_id, memory_job_id, gpu_job_id]
        
        logger.info("Monitoring job statuses...")
        for _ in range(20):  # Monitor for ~2 minutes
            integration_status = await k8s_integration.get_integration_status()
            logger.info(f"K8s Integration: {integration_status['active_pods']} active pods")
            
            for job_id in job_ids:
                job_status = await k8s_integration.get_job_status(job_id)
                if job_status:
                    logger.info(f"Job {job_id}: {job_status['phase']} on node {job_status.get('node_name', 'unassigned')}")
                
            await asyncio.sleep(6.0)
        
        # 5. Create resource quota
        logger.info("Creating resource quota...")
        quota_created = await k8s_integration.create_resource_quota(
            name="kenny-compute-pool-quota",
            cpu_limit=10.0,  # 10 CPU cores
            memory_limit=20 * 1024**3,  # 20 GB
            gpu_limit=2  # 2 GPUs
        )
        
        if quota_created:
            logger.info("Resource quota created successfully")
        
        # 6. Clean up - cancel remaining jobs
        logger.info("Cleaning up jobs...")
        for job_id in job_ids:
            job_status = await k8s_integration.get_job_status(job_id)
            if job_status and job_status['phase'] in ['Pending', 'Running']:
                await k8s_integration.cancel_job(job_id)
                logger.info(f"Cancelled job {job_id}")
        
        # 7. Final status
        final_status = await k8s_integration.get_integration_status()
        logger.info(f"Final integration status: {final_status}")
        
    except Exception as e:
        logger.error(f"Error in Kubernetes demo: {e}")
        if "kubernetes client library not available" in str(e).lower():
            logger.warning("Kubernetes client not installed. Install with: pip install kubernetes")
        raise
    
    finally:
        await k8s_integration.shutdown()
        logger.info("Kubernetes integration demo completed!")


async def kubernetes_manifest_demo():
    """Demonstrate applying Kubernetes manifests"""
    logger.info("=== Kubernetes Manifest Demo ===")
    
    try:
        k8s_integration = KubernetesIntegration(namespace="kenny-compute-pool")
        await k8s_integration.initialize()
        
        # Create a ConfigMap manifest
        configmap_manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "kenny-compute-pool-config",
                "namespace": "kenny-compute-pool"
            },
            "data": {
                "pool_config.yaml": yaml.dump({
                    "pool_name": "kubernetes_pool",
                    "max_concurrent_jobs": 50,
                    "resource_timeout": 600,
                    "scheduling_algorithm": "fair_share",
                    "monitoring_interval": 15
                }),
                "scheduler_config.yaml": yaml.dump({
                    "algorithms": ["fifo", "priority", "fair_share"],
                    "default_algorithm": "fair_share",
                    "preemption_enabled": True,
                    "backfill_enabled": True
                })
            }
        }
        
        success = await k8s_integration.apply_manifest(configmap_manifest)
        if success:
            logger.info("ConfigMap applied successfully")
        
        # Create a custom job pod with specific configuration
        custom_job_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "custom-compute-job",
                "namespace": "kenny-compute-pool",
                "labels": {
                    "app": "kenny-compute-pool",
                    "job-type": "custom",
                    "priority": "high"
                },
                "annotations": {
                    "kenny.compute-pool/job-id": f"custom-job-{int(time.time())}",
                    "kenny.compute-pool/user": "advanced-user",
                    "kenny.compute-pool/deadline": str(int(time.time() + 300))  # 5 minutes from now
                }
            },
            "spec": {
                "containers": [{
                    "name": "compute-task",
                    "image": "python:3.9-slim",
                    "command": ["python", "-c"],
                    "args": [
                        "import time; import os; "
                        "print(f'Job ID: {os.environ.get(\"KENNY_JOB_ID\", \"unknown\")}'); "
                        "print('Performing custom computation...'); "
                        "time.sleep(20); "
                        "print('Custom job completed successfully')"
                    ],
                    "env": [
                        {"name": "KENNY_JOB_ID", "value": f"custom-job-{int(time.time())}"},
                        {"name": "KENNY_USER", "value": "advanced-user"},
                        {"name": "KENNY_POOL", "value": "kubernetes_pool"}
                    ],
                    "resources": {
                        "requests": {
                            "cpu": "1",
                            "memory": "2Gi"
                        },
                        "limits": {
                            "cpu": "1.5",
                            "memory": "2Gi"
                        }
                    }
                }],
                "restartPolicy": "Never",
                "tolerations": [
                    {
                        "key": "node-role.kubernetes.io/compute",
                        "operator": "Equal",
                        "value": "true",
                        "effect": "NoSchedule"
                    }
                ]
            }
        }
        
        success = await k8s_integration.apply_manifest(custom_job_manifest)
        if success:
            logger.info("Custom job pod applied successfully")
        
        # Monitor the custom job
        logger.info("Monitoring custom job...")
        for _ in range(15):
            # In a real implementation, you'd track this job
            await asyncio.sleep(2.0)
        
    except Exception as e:
        logger.error(f"Error in manifest demo: {e}")
    
    finally:
        await k8s_integration.shutdown()


async def main():
    """Run Kubernetes integration demonstrations"""
    try:
        # Run basic Kubernetes integration demo
        await kubernetes_integration_demo()
        
        await asyncio.sleep(2.0)
        
        # Run manifest demo
        await kubernetes_manifest_demo()
        
        logger.info("All Kubernetes demos completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        if "kubernetes client library not available" not in str(e).lower():
            raise


if __name__ == "__main__":
    asyncio.run(main())