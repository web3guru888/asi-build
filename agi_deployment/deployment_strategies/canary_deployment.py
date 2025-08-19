#!/usr/bin/env python3
"""
Canary Deployment Strategy for AGI Models
Implements gradual rollout with traffic splitting and automatic rollback
"""

import asyncio
import logging
import json
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import yaml
from datetime import datetime, timedelta
import numpy as np

class CanaryStatus(Enum):
    """Canary deployment status"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    DEPLOYING = "deploying"
    VALIDATING = "validating"
    RAMPING = "ramping"
    MONITORING = "monitoring"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"

@dataclass
class CanaryStage:
    """Canary deployment stage configuration"""
    stage_name: str
    traffic_percentage: float
    duration_minutes: int
    success_criteria: Dict[str, float]
    auto_advance: bool = True
    max_error_rate: float = 0.01
    max_latency_p95: float = 200
    min_success_rate: float = 0.99

@dataclass
class CanaryMetrics:
    """Canary deployment metrics"""
    timestamp: datetime
    traffic_percentage: float
    request_count: int
    error_count: int
    error_rate: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    success_rate: float
    throughput_rps: float
    cpu_usage: float
    memory_usage: float
    custom_metrics: Dict[str, float] = field(default_factory=dict)

@dataclass
class CanaryTarget:
    """Canary deployment target"""
    endpoint: str
    instances: List[str]
    capacity: int
    region: str = "us-east-1"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CanaryConfig:
    """Canary deployment configuration"""
    model_id: str
    model_version: str
    canary_target: CanaryTarget
    stable_target: CanaryTarget
    stages: List[CanaryStage]
    load_balancer_endpoint: str
    monitoring_config: Dict[str, Any] = field(default_factory=dict)
    rollback_config: Dict[str, Any] = field(default_factory=dict)
    notification_config: Dict[str, Any] = field(default_factory=dict)

class CanaryDeployment:
    """
    Canary deployment strategy implementation with gradual traffic ramping
    """
    
    def __init__(self, config: CanaryConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.current_status = CanaryStatus.PENDING
        self.current_stage_index = 0
        self.deployment_start_time: Optional[datetime] = None
        self.stage_start_time: Optional[datetime] = None
        self.metrics_history: List[CanaryMetrics] = []
        self.deployment_id: Optional[str] = None
        self.is_paused = False
        
    async def deploy(self) -> Dict[str, Any]:
        """
        Execute canary deployment with gradual rollout
        """
        self.deployment_start_time = datetime.now()
        self.deployment_id = f"canary-{self.config.model_id}-{int(time.time())}"
        
        self.logger.info(f"Starting canary deployment: {self.deployment_id}")
        
        try:
            # Initialize canary environment
            await self._initialize_canary()
            
            # Execute canary stages
            for stage_index, stage in enumerate(self.config.stages):
                self.current_stage_index = stage_index
                success = await self._execute_stage(stage)
                
                if not success:
                    self.logger.error(f"Stage '{stage.stage_name}' failed")
                    await self._rollback()
                    return self._create_deployment_result("failed", f"Stage '{stage.stage_name}' failed")
                
                if self.is_paused:
                    self.logger.info("Deployment paused by user")
                    return self._create_deployment_result("paused", "Deployment paused")
            
            # Complete deployment
            await self._complete_deployment()
            
            self.current_status = CanaryStatus.COMPLETED
            result = self._create_deployment_result("success", "Canary deployment completed successfully")
            
            self.logger.info(f"Canary deployment completed: {self.deployment_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Canary deployment failed: {e}")
            self.current_status = CanaryStatus.FAILED
            
            # Attempt rollback
            rollback_result = await self._rollback()
            return self._create_deployment_result("failed", str(e), rollback_result)
    
    async def _initialize_canary(self):
        """Initialize canary environment"""
        self.current_status = CanaryStatus.INITIALIZING
        
        self.logger.info("Initializing canary environment...")
        
        # Deploy new version to canary instances
        await self._deploy_to_canary_instances()
        
        # Wait for canary instances to be ready
        await self._wait_for_canary_ready()
        
        # Run initial validation
        await self._validate_canary_deployment()
        
        self.logger.info("Canary environment initialized successfully")
    
    async def _deploy_to_canary_instances(self):
        """Deploy model to canary instances"""
        self.current_status = CanaryStatus.DEPLOYING
        
        deployment_tasks = []
        for instance in self.config.canary_target.instances:
            task = self._deploy_to_instance(instance, self.config.model_version)
            deployment_tasks.append(task)
        
        # Deploy in parallel
        results = await asyncio.gather(*deployment_tasks, return_exceptions=True)
        
        # Check for failures
        failed_deployments = [r for r in results if isinstance(r, Exception)]
        if failed_deployments:
            raise Exception(f"Canary deployment failed on {len(failed_deployments)} instances")
    
    async def _deploy_to_instance(self, instance: str, model_version: str):
        """Deploy model to specific instance"""
        try:
            async with aiohttp.ClientSession() as session:
                deployment_payload = {
                    "model_id": self.config.model_id,
                    "model_version": model_version,
                    "deployment_type": "canary",
                    "deployment_id": self.deployment_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                async with session.post(f"http://{instance}/deploy", json=deployment_payload, timeout=300) as response:
                    if response.status == 200:
                        self.logger.info(f"Successfully deployed to canary instance {instance}")
                        return True
                    else:
                        raise Exception(f"Deployment failed with status {response.status}")
        
        except Exception as e:
            self.logger.error(f"Failed to deploy to instance {instance}: {e}")
            raise
    
    async def _wait_for_canary_ready(self):
        """Wait for canary instances to be ready"""
        self.logger.info("Waiting for canary instances to be ready...")
        
        max_wait_time = 600  # 10 minutes
        check_interval = 15  # 15 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            ready_count = 0
            
            for instance in self.config.canary_target.instances:
                if await self._is_instance_ready(instance):
                    ready_count += 1
            
            if ready_count == len(self.config.canary_target.instances):
                self.logger.info("All canary instances are ready")
                return
            
            self.logger.info(f"{ready_count}/{len(self.config.canary_target.instances)} canary instances ready")
            await asyncio.sleep(check_interval)
        
        raise Exception("Timeout waiting for canary instances to be ready")
    
    async def _is_instance_ready(self, instance: str) -> bool:
        """Check if instance is ready"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{instance}/health", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("status") == "healthy"
        except Exception:
            return False
        return False
    
    async def _validate_canary_deployment(self):
        """Validate canary deployment before starting traffic"""
        self.current_status = CanaryStatus.VALIDATING
        
        self.logger.info("Validating canary deployment...")
        
        # Run smoke tests
        validation_tasks = [
            self._test_canary_inference(),
            self._test_canary_performance(),
            self._test_canary_error_handling()
        ]
        
        results = await asyncio.gather(*validation_tasks)
        
        # Check if all validations passed
        failed_validations = [r for r in results if not r.get("passed", False)]
        if failed_validations:
            raise Exception(f"Canary validation failed: {failed_validations}")
        
        self.logger.info("Canary deployment validation successful")
    
    async def _test_canary_inference(self) -> Dict[str, Any]:
        """Test canary inference functionality"""
        try:
            async with aiohttp.ClientSession() as session:
                test_payload = {
                    "input": "Canary deployment test",
                    "max_length": 50,
                    "deployment_test": True
                }
                
                async with session.post(f"{self.config.canary_target.endpoint}/generate", 
                                      json=test_payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "output" in data and len(data["output"]) > 0:
                            return {"test": "canary_inference", "passed": True}
            
            return {"test": "canary_inference", "passed": False}
        
        except Exception as e:
            return {"test": "canary_inference", "passed": False, "error": str(e)}
    
    async def _test_canary_performance(self) -> Dict[str, Any]:
        """Test canary performance"""
        try:
            # Run multiple requests to test performance
            request_count = 10
            latencies = []
            
            async with aiohttp.ClientSession() as session:
                for i in range(request_count):
                    start_time = time.time()
                    
                    test_payload = {"input": f"Performance test {i}"}
                    async with session.post(f"{self.config.canary_target.endpoint}/generate", 
                                          json=test_payload) as response:
                        if response.status == 200:
                            latency = (time.time() - start_time) * 1000
                            latencies.append(latency)
            
            if latencies:
                avg_latency = np.mean(latencies)
                p95_latency = np.percentile(latencies, 95)
                
                if avg_latency < 1000 and p95_latency < 2000:  # Thresholds
                    return {
                        "test": "canary_performance", 
                        "passed": True,
                        "avg_latency": avg_latency,
                        "p95_latency": p95_latency
                    }
            
            return {"test": "canary_performance", "passed": False}
        
        except Exception as e:
            return {"test": "canary_performance", "passed": False, "error": str(e)}
    
    async def _test_canary_error_handling(self) -> Dict[str, Any]:
        """Test canary error handling"""
        try:
            async with aiohttp.ClientSession() as session:
                # Send invalid request
                invalid_payload = {"invalid_field": "test"}
                
                async with session.post(f"{self.config.canary_target.endpoint}/generate", 
                                      json=invalid_payload) as response:
                    if response.status == 400:  # Expected error response
                        return {"test": "canary_error_handling", "passed": True}
            
            return {"test": "canary_error_handling", "passed": False}
        
        except Exception as e:
            return {"test": "canary_error_handling", "passed": False, "error": str(e)}
    
    async def _execute_stage(self, stage: CanaryStage) -> bool:
        """Execute a canary deployment stage"""
        self.current_status = CanaryStatus.RAMPING
        self.stage_start_time = datetime.now()
        
        self.logger.info(f"Executing canary stage: {stage.stage_name} ({stage.traffic_percentage}% traffic)")
        
        try:
            # Update traffic routing
            await self._update_traffic_routing(stage.traffic_percentage)
            
            # Monitor stage for specified duration
            stage_success = await self._monitor_stage(stage)
            
            if stage_success:
                self.logger.info(f"Stage '{stage.stage_name}' completed successfully")
                return True
            else:
                self.logger.error(f"Stage '{stage.stage_name}' failed success criteria")
                return False
        
        except Exception as e:
            self.logger.error(f"Stage '{stage.stage_name}' failed with exception: {e}")
            return False
    
    async def _update_traffic_routing(self, canary_percentage: float):
        """Update traffic routing to canary"""
        try:
            # In a real implementation, this would update load balancer configuration
            routing_config = {
                "canary": canary_percentage,
                "stable": 100 - canary_percentage,
                "timestamp": datetime.now().isoformat(),
                "deployment_id": self.deployment_id
            }
            
            self.logger.info(f"Updating traffic routing: {canary_percentage}% to canary")
            
            # Simulate load balancer update
            await asyncio.sleep(2)
            
            # Verify routing update
            await self._verify_traffic_routing(canary_percentage)
            
        except Exception as e:
            self.logger.error(f"Failed to update traffic routing: {e}")
            raise
    
    async def _verify_traffic_routing(self, expected_percentage: float):
        """Verify traffic routing is working correctly"""
        # Simulate traffic routing verification
        # In practice, this would check load balancer configuration
        
        verification_requests = 100
        canary_requests = 0
        
        async with aiohttp.ClientSession() as session:
            for _ in range(verification_requests):
                try:
                    # Make request through load balancer
                    test_payload = {"input": "routing test", "verify": True}
                    async with session.post(f"{self.config.load_balancer_endpoint}/generate", 
                                          json=test_payload, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Check if request went to canary (would be marked in response)
                            if data.get("served_by") == "canary":
                                canary_requests += 1
                except Exception:
                    continue
        
        actual_percentage = (canary_requests / verification_requests) * 100
        tolerance = 5.0  # 5% tolerance
        
        if abs(actual_percentage - expected_percentage) <= tolerance:
            self.logger.info(f"Traffic routing verified: {actual_percentage:.1f}% (expected {expected_percentage}%)")
        else:
            raise Exception(f"Traffic routing verification failed: {actual_percentage:.1f}% vs expected {expected_percentage}%")
    
    async def _monitor_stage(self, stage: CanaryStage) -> bool:
        """Monitor canary stage for success criteria"""
        self.current_status = CanaryStatus.MONITORING
        
        monitor_duration = stage.duration_minutes * 60  # Convert to seconds
        check_interval = 30  # Check every 30 seconds
        start_time = time.time()
        
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        self.logger.info(f"Monitoring stage for {stage.duration_minutes} minutes...")
        
        while time.time() - start_time < monitor_duration and not self.is_paused:
            try:
                # Collect metrics
                metrics = await self._collect_canary_metrics(stage.traffic_percentage)
                self.metrics_history.append(metrics)
                
                # Evaluate success criteria
                criteria_met = self._evaluate_success_criteria(metrics, stage)
                
                if criteria_met:
                    consecutive_failures = 0
                    self.logger.debug(f"Success criteria met: {metrics.success_rate:.3f} success rate, {metrics.error_rate:.3f} error rate")
                else:
                    consecutive_failures += 1
                    self.logger.warning(f"Success criteria not met (attempt {consecutive_failures}/{max_consecutive_failures})")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        self.logger.error("Too many consecutive failures, stage failed")
                        return False
                
                # Check for critical failures (immediate rollback triggers)
                if self._check_critical_failure(metrics, stage):
                    self.logger.error("Critical failure detected, triggering immediate rollback")
                    return False
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"Error during stage monitoring: {e}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_consecutive_failures:
                    return False
        
        if self.is_paused:
            return True  # Stage can be resumed later
        
        # Final evaluation
        recent_metrics = self.metrics_history[-5:] if len(self.metrics_history) >= 5 else self.metrics_history
        overall_success = all(self._evaluate_success_criteria(m, stage) for m in recent_metrics)
        
        self.logger.info(f"Stage monitoring completed. Overall success: {overall_success}")
        return overall_success
    
    async def _collect_canary_metrics(self, traffic_percentage: float) -> CanaryMetrics:
        """Collect canary deployment metrics"""
        # In a real implementation, this would collect metrics from monitoring systems
        # For now, we'll simulate metric collection with some realistic values
        
        base_error_rate = 0.001  # 0.1% base error rate
        base_latency = 50        # 50ms base latency
        
        # Add some realistic variation and potential issues
        error_rate = base_error_rate + random.uniform(0, 0.005)
        latency_p50 = base_latency + random.uniform(0, 20)
        latency_p95 = latency_p50 + random.uniform(30, 80)
        latency_p99 = latency_p95 + random.uniform(20, 100)
        
        # Simulate higher load/errors at higher traffic percentages
        load_factor = traffic_percentage / 100
        error_rate *= (1 + load_factor * 0.5)
        latency_p95 *= (1 + load_factor * 0.3)
        
        request_count = int(100 * load_factor + random.uniform(10, 50))
        error_count = int(request_count * error_rate)
        success_rate = 1 - error_rate
        throughput_rps = request_count / 30  # Assuming 30-second collection period
        
        return CanaryMetrics(
            timestamp=datetime.now(),
            traffic_percentage=traffic_percentage,
            request_count=request_count,
            error_count=error_count,
            error_rate=error_rate,
            latency_p50=latency_p50,
            latency_p95=latency_p95,
            latency_p99=latency_p99,
            success_rate=success_rate,
            throughput_rps=throughput_rps,
            cpu_usage=random.uniform(40, 70),
            memory_usage=random.uniform(50, 80),
            custom_metrics={
                "model_accuracy": random.uniform(0.85, 0.95),
                "cache_hit_rate": random.uniform(0.8, 0.95)
            }
        )
    
    def _evaluate_success_criteria(self, metrics: CanaryMetrics, stage: CanaryStage) -> bool:
        """Evaluate if metrics meet stage success criteria"""
        # Check error rate
        if metrics.error_rate > stage.max_error_rate:
            return False
        
        # Check latency
        if metrics.latency_p95 > stage.max_latency_p95:
            return False
        
        # Check success rate
        if metrics.success_rate < stage.min_success_rate:
            return False
        
        # Check custom success criteria
        for metric_name, threshold in stage.success_criteria.items():
            if metric_name in metrics.custom_metrics:
                if metrics.custom_metrics[metric_name] < threshold:
                    return False
        
        return True
    
    def _check_critical_failure(self, metrics: CanaryMetrics, stage: CanaryStage) -> bool:
        """Check for critical failures that require immediate rollback"""
        critical_thresholds = {
            "max_error_rate": 0.05,      # 5% error rate
            "max_latency_p95": 5000,     # 5 second latency
            "min_success_rate": 0.9      # 90% success rate
        }
        
        if metrics.error_rate > critical_thresholds["max_error_rate"]:
            self.logger.critical(f"Critical error rate: {metrics.error_rate:.3f}")
            return True
        
        if metrics.latency_p95 > critical_thresholds["max_latency_p95"]:
            self.logger.critical(f"Critical latency: {metrics.latency_p95:.1f}ms")
            return True
        
        if metrics.success_rate < critical_thresholds["min_success_rate"]:
            self.logger.critical(f"Critical success rate: {metrics.success_rate:.3f}")
            return True
        
        return False
    
    async def _complete_deployment(self):
        """Complete canary deployment by routing 100% traffic to canary"""
        self.current_status = CanaryStatus.COMPLETING
        
        self.logger.info("Completing canary deployment...")
        
        # Route 100% traffic to canary
        await self._update_traffic_routing(100.0)
        
        # Final monitoring period
        await self._final_monitoring()
        
        # Update stable environment with canary version
        await self._promote_canary_to_stable()
        
        self.logger.info("Canary deployment completed successfully")
    
    async def _final_monitoring(self):
        """Final monitoring after 100% traffic routing"""
        self.logger.info("Final monitoring period...")
        
        monitor_duration = 300  # 5 minutes
        check_interval = 30
        start_time = time.time()
        
        while time.time() - start_time < monitor_duration:
            metrics = await self._collect_canary_metrics(100.0)
            self.metrics_history.append(metrics)
            
            # Check for any issues at 100% traffic
            if metrics.error_rate > 0.01 or metrics.latency_p95 > 500:
                self.logger.warning("Issues detected during final monitoring")
                # Could trigger rollback here if issues are severe
            
            await asyncio.sleep(check_interval)
    
    async def _promote_canary_to_stable(self):
        """Promote canary version to stable environment"""
        self.logger.info("Promoting canary to stable environment...")
        
        # In a real implementation, this would:
        # 1. Update stable environment with new model version
        # 2. Scale down canary environment
        # 3. Update routing to use stable environment
        
        # Simulate the promotion process
        await asyncio.sleep(5)
        
        self.logger.info("Canary promoted to stable successfully")
    
    async def _rollback(self) -> Dict[str, Any]:
        """Perform rollback to stable version"""
        self.current_status = CanaryStatus.ROLLING_BACK
        
        self.logger.info("Initiating canary rollback...")
        
        try:
            # Route all traffic back to stable
            await self._update_traffic_routing(0.0)
            
            # Verify stable environment health
            await self._verify_stable_health()
            
            # Scale down canary environment
            await self._scale_down_canary()
            
            self.current_status = CanaryStatus.ROLLED_BACK
            
            rollback_result = {
                "status": "success",
                "rollback_time": datetime.now().isoformat(),
                "final_canary_stage": self.current_stage_index,
                "rollback_reason": "failure_or_manual_trigger"
            }
            
            self.logger.info("Canary rollback completed successfully")
            return rollback_result
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "rollback_time": datetime.now().isoformat()
            }
    
    async def _verify_stable_health(self):
        """Verify stable environment health after rollback"""
        for instance in self.config.stable_target.instances:
            if not await self._is_instance_ready(instance):
                raise Exception(f"Stable instance {instance} is not healthy after rollback")
    
    async def _scale_down_canary(self):
        """Scale down canary environment after rollback"""
        self.logger.info("Scaling down canary environment...")
        # Simulate scaling down
        await asyncio.sleep(2)
    
    def pause_deployment(self):
        """Pause the current deployment"""
        self.is_paused = True
        self.logger.info("Deployment paused")
    
    def resume_deployment(self):
        """Resume the paused deployment"""
        self.is_paused = False
        self.logger.info("Deployment resumed")
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status and metrics"""
        recent_metrics = self.metrics_history[-10:] if self.metrics_history else []
        
        return {
            "deployment_id": self.deployment_id,
            "status": self.current_status.value,
            "current_stage": self.current_stage_index,
            "total_stages": len(self.config.stages),
            "is_paused": self.is_paused,
            "deployment_start_time": self.deployment_start_time.isoformat() if self.deployment_start_time else None,
            "stage_start_time": self.stage_start_time.isoformat() if self.stage_start_time else None,
            "current_traffic_percentage": recent_metrics[-1].traffic_percentage if recent_metrics else 0,
            "recent_metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "traffic_percentage": m.traffic_percentage,
                    "error_rate": m.error_rate,
                    "latency_p95": m.latency_p95,
                    "success_rate": m.success_rate,
                    "throughput_rps": m.throughput_rps
                }
                for m in recent_metrics
            ],
            "model_version": self.config.model_version
        }
    
    def _create_deployment_result(self, status: str, message: str, rollback_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create deployment result dictionary"""
        result = {
            "deployment_id": self.deployment_id,
            "status": status,
            "message": message,
            "model_version": self.config.model_version,
            "deployment_duration": (datetime.now() - self.deployment_start_time).total_seconds() if self.deployment_start_time else 0,
            "stages_completed": self.current_stage_index,
            "total_stages": len(self.config.stages),
            "timestamp": datetime.now().isoformat(),
            "metrics_collected": len(self.metrics_history)
        }
        
        if rollback_result:
            result["rollback_result"] = rollback_result
        
        return result

# Example usage and configuration
if __name__ == "__main__":
    async def main():
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Define canary stages
        stages = [
            CanaryStage(
                stage_name="Initial Validation",
                traffic_percentage=5.0,
                duration_minutes=10,
                success_criteria={"model_accuracy": 0.85},
                max_error_rate=0.005
            ),
            CanaryStage(
                stage_name="Low Traffic",
                traffic_percentage=20.0,
                duration_minutes=15,
                success_criteria={"model_accuracy": 0.87},
                max_error_rate=0.003
            ),
            CanaryStage(
                stage_name="Medium Traffic",
                traffic_percentage=50.0,
                duration_minutes=20,
                success_criteria={"model_accuracy": 0.88},
                max_error_rate=0.002
            ),
            CanaryStage(
                stage_name="High Traffic",
                traffic_percentage=80.0,
                duration_minutes=15,
                success_criteria={"model_accuracy": 0.89},
                max_error_rate=0.001
            )
        ]
        
        # Define deployment targets
        canary_target = CanaryTarget(
            endpoint="http://canary-lb.example.com",
            instances=["canary-1.example.com", "canary-2.example.com"],
            capacity=2,
            region="us-east-1"
        )
        
        stable_target = CanaryTarget(
            endpoint="http://stable-lb.example.com",
            instances=["stable-1.example.com", "stable-2.example.com", "stable-3.example.com"],
            capacity=3,
            region="us-east-1"
        )
        
        # Create canary configuration
        config = CanaryConfig(
            model_id="kenny-agi-model",
            model_version="v2.1.0",
            canary_target=canary_target,
            stable_target=stable_target,
            stages=stages,
            load_balancer_endpoint="http://lb.example.com",
            rollback_config={
                "auto_rollback": True,
                "rollback_on_critical_failure": True
            },
            notification_config={
                "slack_webhook": "https://hooks.slack.com/...",
                "email_alerts": ["ops@example.com"]
            }
        )
        
        # Create canary deployment
        canary = CanaryDeployment(config)
        
        # Execute deployment
        result = await canary.deploy()
        
        print(json.dumps(result, indent=2))
        
        # Check final status
        status = canary.get_deployment_status()
        print("Final Status:", json.dumps(status, indent=2))
    
    asyncio.run(main())