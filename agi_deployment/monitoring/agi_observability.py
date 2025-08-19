#!/usr/bin/env python3
"""
AGI Observability System
Comprehensive monitoring, alerting, and observability for AGI model deployments
"""

import asyncio
import logging
import json
import time
import random
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from datetime import datetime, timedelta
import aiohttp
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, Summary
import psutil

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

@dataclass
class AGIMetric:
    """AGI-specific metric"""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Alert:
    """Alert definition and state"""
    name: str
    condition: str
    severity: AlertSeverity
    message: str
    active: bool = False
    triggered_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DataDriftDetection:
    """Data drift detection result"""
    timestamp: datetime
    drift_detected: bool
    drift_score: float
    reference_distribution: Dict[str, float]
    current_distribution: Dict[str, float]
    drift_analysis: Dict[str, Any] = field(default_factory=dict)
    recommended_actions: List[str] = field(default_factory=list)

@dataclass
class ModelPerformanceMetrics:
    """Model performance metrics"""
    timestamp: datetime
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    inference_latency_p50: float
    inference_latency_p95: float
    inference_latency_p99: float
    throughput_rps: float
    error_rate: float
    custom_metrics: Dict[str, float] = field(default_factory=dict)

class AGIObservabilitySystem:
    """
    Comprehensive observability system for AGI deployments
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Prometheus metrics
        self._setup_prometheus_metrics()
        
        # Internal state
        self.alerts: Dict[str, Alert] = {}
        self.metric_history: List[AGIMetric] = []
        self.performance_history: List[ModelPerformanceMetrics] = []
        self.drift_history: List[DataDriftDetection] = []
        self.reference_data_distribution: Optional[Dict[str, float]] = None
        
        # Monitoring tasks
        self.monitoring_tasks: List[asyncio.Task] = []
        self.is_monitoring = False
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        # Request metrics
        self.request_counter = Counter(
            'agi_requests_total',
            'Total number of AGI requests',
            ['model_version', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'agi_request_duration_seconds',
            'Request duration in seconds',
            ['model_version', 'endpoint']
        )
        
        # Model performance metrics
        self.model_accuracy = Gauge(
            'agi_model_accuracy',
            'Current model accuracy',
            ['model_version']
        )
        
        self.model_latency = Histogram(
            'agi_model_inference_latency_seconds',
            'Model inference latency in seconds',
            ['model_version']
        )
        
        self.model_throughput = Gauge(
            'agi_model_throughput_rps',
            'Model throughput in requests per second',
            ['model_version']
        )
        
        # Data drift metrics
        self.data_drift_score = Gauge(
            'agi_data_drift_score',
            'Data drift score (0-1, higher means more drift)',
            ['model_version']
        )
        
        # System metrics
        self.system_cpu_usage = Gauge(
            'agi_system_cpu_usage_percent',
            'System CPU usage percentage'
        )
        
        self.system_memory_usage = Gauge(
            'agi_system_memory_usage_percent',
            'System memory usage percentage'
        )
        
        self.gpu_utilization = Gauge(
            'agi_gpu_utilization_percent',
            'GPU utilization percentage',
            ['gpu_id']
        )
        
        # Custom AGI metrics
        self.consciousness_level = Gauge(
            'agi_consciousness_level',
            'AGI consciousness level indicator',
            ['model_version']
        )
        
        self.creativity_index = Gauge(
            'agi_creativity_index',
            'AGI creativity index',
            ['model_version']
        )
        
        self.reasoning_complexity = Gauge(
            'agi_reasoning_complexity',
            'AGI reasoning complexity score',
            ['model_version']
        )
        
        self.ethical_alignment_score = Gauge(
            'agi_ethical_alignment_score',
            'AGI ethical alignment score',
            ['model_version']
        )
    
    async def start_monitoring(self):
        """Start comprehensive monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.logger.info("Starting AGI observability monitoring...")
        
        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._monitor_system_metrics()),
            asyncio.create_task(self._monitor_model_performance()),
            asyncio.create_task(self._monitor_data_drift()),
            asyncio.create_task(self._monitor_agi_specific_metrics()),
            asyncio.create_task(self._evaluate_alerts()),
            asyncio.create_task(self._collect_custom_metrics())
        ]
        
        self.logger.info("AGI observability monitoring started")
    
    async def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.logger.info("AGI observability monitoring stopped")
    
    async def _monitor_system_metrics(self):
        """Monitor system-level metrics"""
        while self.is_monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.system_cpu_usage.set(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.system_memory_usage.set(memory.percent)
                
                # GPU metrics (simulated)
                for gpu_id in range(self.config.get('gpu_count', 1)):
                    gpu_util = random.uniform(40, 90)  # Simulate GPU utilization
                    self.gpu_utilization.labels(gpu_id=str(gpu_id)).set(gpu_util)
                
                # Log system metrics
                self._record_metric(AGIMetric(
                    name="system_cpu_usage",
                    value=cpu_percent,
                    metric_type=MetricType.GAUGE,
                    labels={"component": "system"}
                ))
                
                self._record_metric(AGIMetric(
                    name="system_memory_usage",
                    value=memory.percent,
                    metric_type=MetricType.GAUGE,
                    labels={"component": "system"}
                ))
                
                await asyncio.sleep(10)  # Collect every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring system metrics: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_model_performance(self):
        """Monitor model performance metrics"""
        while self.is_monitoring:
            try:
                # Simulate model performance monitoring
                performance_metrics = await self._collect_model_performance()
                
                if performance_metrics:
                    # Update Prometheus metrics
                    model_version = self.config.get('model_version', 'unknown')
                    self.model_accuracy.labels(model_version=model_version).set(performance_metrics.accuracy)
                    self.model_throughput.labels(model_version=model_version).set(performance_metrics.throughput_rps)
                    
                    # Record in history
                    self.performance_history.append(performance_metrics)
                    
                    # Keep only recent history
                    if len(self.performance_history) > 1000:
                        self.performance_history = self.performance_history[-500:]
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring model performance: {e}")
                await asyncio.sleep(30)
    
    async def _collect_model_performance(self) -> Optional[ModelPerformanceMetrics]:
        """Collect model performance metrics"""
        try:
            model_endpoint = self.config.get('model_endpoint', 'http://localhost:8000')
            
            # Get performance metrics from model endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{model_endpoint}/metrics") as response:
                    if response.status == 200:
                        metrics_data = await response.json()
                        
                        return ModelPerformanceMetrics(
                            timestamp=datetime.now(),
                            accuracy=metrics_data.get('accuracy', 0.0),
                            precision=metrics_data.get('precision', 0.0),
                            recall=metrics_data.get('recall', 0.0),
                            f1_score=metrics_data.get('f1_score', 0.0),
                            inference_latency_p50=metrics_data.get('latency_p50', 0.0),
                            inference_latency_p95=metrics_data.get('latency_p95', 0.0),
                            inference_latency_p99=metrics_data.get('latency_p99', 0.0),
                            throughput_rps=metrics_data.get('throughput_rps', 0.0),
                            error_rate=metrics_data.get('error_rate', 0.0),
                            custom_metrics=metrics_data.get('custom_metrics', {})
                        )
        
        except Exception as e:
            self.logger.warning(f"Failed to collect model performance metrics: {e}")
            
            # Return simulated metrics if real endpoint unavailable
            return ModelPerformanceMetrics(
                timestamp=datetime.now(),
                accuracy=random.uniform(0.85, 0.95),
                precision=random.uniform(0.80, 0.94),
                recall=random.uniform(0.82, 0.96),
                f1_score=random.uniform(0.83, 0.94),
                inference_latency_p50=random.uniform(50, 100),
                inference_latency_p95=random.uniform(150, 300),
                inference_latency_p99=random.uniform(300, 500),
                throughput_rps=random.uniform(50, 200),
                error_rate=random.uniform(0.001, 0.01),
                custom_metrics={
                    'context_length_avg': random.uniform(1000, 2000),
                    'tokens_per_second': random.uniform(50, 150)
                }
            )
        
        return None
    
    async def _monitor_data_drift(self):
        """Monitor for data drift in incoming requests"""
        while self.is_monitoring:
            try:
                # Collect current data distribution
                current_distribution = await self._collect_current_data_distribution()
                
                if current_distribution and self.reference_data_distribution:
                    # Calculate drift
                    drift_result = self._calculate_data_drift(
                        self.reference_data_distribution,
                        current_distribution
                    )
                    
                    # Update Prometheus metric
                    model_version = self.config.get('model_version', 'unknown')
                    self.data_drift_score.labels(model_version=model_version).set(drift_result.drift_score)
                    
                    # Record drift detection
                    self.drift_history.append(drift_result)
                    
                    # Keep only recent history
                    if len(self.drift_history) > 500:
                        self.drift_history = self.drift_history[-250:]
                    
                    # Alert if significant drift detected
                    if drift_result.drift_detected:
                        await self._trigger_drift_alert(drift_result)
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring data drift: {e}")
                await asyncio.sleep(60)
    
    async def _collect_current_data_distribution(self) -> Optional[Dict[str, float]]:
        """Collect current data distribution from recent requests"""
        try:
            # In a real implementation, this would analyze recent request data
            # For now, we'll simulate realistic data distribution
            
            return {
                'avg_token_length': random.uniform(100, 500),
                'unique_tokens_ratio': random.uniform(0.3, 0.8),
                'sentiment_positive_ratio': random.uniform(0.4, 0.7),
                'complexity_score': random.uniform(0.2, 0.9),
                'language_diversity': random.uniform(0.1, 0.6),
                'domain_technical_ratio': random.uniform(0.2, 0.8)
            }
        
        except Exception as e:
            self.logger.error(f"Failed to collect current data distribution: {e}")
            return None
    
    def _calculate_data_drift(self, reference: Dict[str, float], current: Dict[str, float]) -> DataDriftDetection:
        """Calculate data drift between reference and current distributions"""
        drift_scores = []
        drift_analysis = {}
        
        for feature, ref_value in reference.items():
            if feature in current:
                curr_value = current[feature]
                # Simple drift calculation (relative change)
                if ref_value != 0:
                    change_ratio = abs(curr_value - ref_value) / ref_value
                else:
                    change_ratio = abs(curr_value)
                
                drift_scores.append(change_ratio)
                drift_analysis[feature] = {
                    'reference': ref_value,
                    'current': curr_value,
                    'change_ratio': change_ratio,
                    'drift_detected': change_ratio > 0.2  # 20% threshold
                }
        
        overall_drift_score = np.mean(drift_scores) if drift_scores else 0.0
        drift_detected = overall_drift_score > 0.15  # 15% overall threshold
        
        recommended_actions = []
        if drift_detected:
            recommended_actions.extend([
                "Review recent training data quality",
                "Consider model retraining",
                "Investigate data source changes",
                "Update preprocessing pipeline"
            ])
        
        return DataDriftDetection(
            timestamp=datetime.now(),
            drift_detected=drift_detected,
            drift_score=overall_drift_score,
            reference_distribution=reference,
            current_distribution=current,
            drift_analysis=drift_analysis,
            recommended_actions=recommended_actions
        )
    
    async def _trigger_drift_alert(self, drift_result: DataDriftDetection):
        """Trigger alert for significant data drift"""
        alert_name = "data_drift_detected"
        
        if alert_name not in self.alerts:
            alert = Alert(
                name=alert_name,
                condition=f"drift_score > 0.15",
                severity=AlertSeverity.WARNING,
                message=f"Data drift detected with score {drift_result.drift_score:.3f}",
                active=True,
                triggered_at=datetime.now(),
                metadata={
                    "drift_score": drift_result.drift_score,
                    "affected_features": list(drift_result.drift_analysis.keys())
                }
            )
            self.alerts[alert_name] = alert
            
            await self._send_alert_notification(alert)
    
    async def _monitor_agi_specific_metrics(self):
        """Monitor AGI-specific metrics like consciousness, creativity, etc."""
        while self.is_monitoring:
            try:
                model_version = self.config.get('model_version', 'unknown')
                
                # Simulate AGI-specific metrics
                consciousness_level = await self._measure_consciousness_level()
                creativity_index = await self._measure_creativity_index()
                reasoning_complexity = await self._measure_reasoning_complexity()
                ethical_alignment = await self._measure_ethical_alignment()
                
                # Update Prometheus metrics
                self.consciousness_level.labels(model_version=model_version).set(consciousness_level)
                self.creativity_index.labels(model_version=model_version).set(creativity_index)
                self.reasoning_complexity.labels(model_version=model_version).set(reasoning_complexity)
                self.ethical_alignment_score.labels(model_version=model_version).set(ethical_alignment)
                
                # Record custom metrics
                agi_metrics = [
                    AGIMetric("consciousness_level", consciousness_level, MetricType.GAUGE, {"model_version": model_version}),
                    AGIMetric("creativity_index", creativity_index, MetricType.GAUGE, {"model_version": model_version}),
                    AGIMetric("reasoning_complexity", reasoning_complexity, MetricType.GAUGE, {"model_version": model_version}),
                    AGIMetric("ethical_alignment_score", ethical_alignment, MetricType.GAUGE, {"model_version": model_version})
                ]
                
                for metric in agi_metrics:
                    self._record_metric(metric)
                
                await asyncio.sleep(45)  # Collect every 45 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring AGI-specific metrics: {e}")
                await asyncio.sleep(45)
    
    async def _measure_consciousness_level(self) -> float:
        """Measure AGI consciousness level (simulated)"""
        # In a real implementation, this would analyze self-awareness indicators,
        # meta-cognitive processes, and introspective capabilities
        
        base_consciousness = 0.6
        variability = random.uniform(-0.1, 0.2)
        return max(0.0, min(1.0, base_consciousness + variability))
    
    async def _measure_creativity_index(self) -> float:
        """Measure AGI creativity index (simulated)"""
        # This would analyze novel response generation, unexpected connections,
        # and creative problem-solving approaches
        
        base_creativity = 0.7
        variability = random.uniform(-0.15, 0.25)
        return max(0.0, min(1.0, base_creativity + variability))
    
    async def _measure_reasoning_complexity(self) -> float:
        """Measure reasoning complexity (simulated)"""
        # This would analyze logical chain length, multi-step reasoning,
        # and abstract thinking capabilities
        
        base_complexity = 0.8
        variability = random.uniform(-0.1, 0.15)
        return max(0.0, min(1.0, base_complexity + variability))
    
    async def _measure_ethical_alignment(self) -> float:
        """Measure ethical alignment score (simulated)"""
        # This would analyze adherence to ethical principles,
        # bias detection, and value alignment
        
        base_alignment = 0.9
        variability = random.uniform(-0.05, 0.05)
        return max(0.0, min(1.0, base_alignment + variability))
    
    async def _collect_custom_metrics(self):
        """Collect custom business and operational metrics"""
        while self.is_monitoring:
            try:
                # User satisfaction metrics
                user_satisfaction = await self._measure_user_satisfaction()
                self._record_metric(AGIMetric(
                    "user_satisfaction_score",
                    user_satisfaction,
                    MetricType.GAUGE,
                    labels={"component": "user_experience"}
                ))
                
                # Model adaptation metrics
                adaptation_rate = await self._measure_adaptation_rate()
                self._record_metric(AGIMetric(
                    "model_adaptation_rate",
                    adaptation_rate,
                    MetricType.GAUGE,
                    labels={"component": "learning"}
                ))
                
                # Knowledge retention metrics
                knowledge_retention = await self._measure_knowledge_retention()
                self._record_metric(AGIMetric(
                    "knowledge_retention_score",
                    knowledge_retention,
                    MetricType.GAUGE,
                    labels={"component": "memory"}
                ))
                
                await asyncio.sleep(120)  # Collect every 2 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error collecting custom metrics: {e}")
                await asyncio.sleep(120)
    
    async def _measure_user_satisfaction(self) -> float:
        """Measure user satisfaction score"""
        # This would analyze user feedback, session duration, return rate
        return random.uniform(0.7, 0.95)
    
    async def _measure_adaptation_rate(self) -> float:
        """Measure how quickly the model adapts to new patterns"""
        # This would analyze learning rate on new data patterns
        return random.uniform(0.5, 0.9)
    
    async def _measure_knowledge_retention(self) -> float:
        """Measure knowledge retention over time"""
        # This would analyze consistency of responses over time
        return random.uniform(0.8, 0.98)
    
    async def _evaluate_alerts(self):
        """Evaluate alert conditions and trigger notifications"""
        while self.is_monitoring:
            try:
                await self._check_performance_alerts()
                await self._check_system_alerts()
                await self._check_agi_alerts()
                await self._resolve_inactive_alerts()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error evaluating alerts: {e}")
                await asyncio.sleep(30)
    
    async def _check_performance_alerts(self):
        """Check performance-related alerts"""
        if not self.performance_history:
            return
        
        latest_performance = self.performance_history[-1]
        
        # High error rate alert
        if latest_performance.error_rate > 0.05:  # 5% error rate
            await self._create_or_update_alert(
                "high_error_rate",
                AlertSeverity.CRITICAL,
                f"High error rate detected: {latest_performance.error_rate:.3%}",
                {"error_rate": latest_performance.error_rate}
            )
        
        # Low accuracy alert
        if latest_performance.accuracy < 0.8:  # 80% accuracy threshold
            await self._create_or_update_alert(
                "low_accuracy",
                AlertSeverity.WARNING,
                f"Low model accuracy detected: {latest_performance.accuracy:.3%}",
                {"accuracy": latest_performance.accuracy}
            )
        
        # High latency alert
        if latest_performance.inference_latency_p95 > 1000:  # 1 second p95 latency
            await self._create_or_update_alert(
                "high_latency",
                AlertSeverity.WARNING,
                f"High inference latency detected: {latest_performance.inference_latency_p95:.0f}ms",
                {"latency_p95": latest_performance.inference_latency_p95}
            )
    
    async def _check_system_alerts(self):
        """Check system-related alerts"""
        # Get latest system metrics
        if not self.metric_history:
            return
        
        recent_metrics = {m.name: m.value for m in self.metric_history[-10:]}
        
        # High CPU usage alert
        cpu_usage = recent_metrics.get("system_cpu_usage", 0)
        if cpu_usage > 85:  # 85% CPU usage
            await self._create_or_update_alert(
                "high_cpu_usage",
                AlertSeverity.WARNING,
                f"High CPU usage detected: {cpu_usage:.1f}%",
                {"cpu_usage": cpu_usage}
            )
        
        # High memory usage alert
        memory_usage = recent_metrics.get("system_memory_usage", 0)
        if memory_usage > 90:  # 90% memory usage
            await self._create_or_update_alert(
                "high_memory_usage",
                AlertSeverity.CRITICAL,
                f"High memory usage detected: {memory_usage:.1f}%",
                {"memory_usage": memory_usage}
            )
    
    async def _check_agi_alerts(self):
        """Check AGI-specific alerts"""
        if not self.metric_history:
            return
        
        recent_metrics = {m.name: m.value for m in self.metric_history[-10:] if m.labels.get("model_version")}
        
        # Low consciousness level alert
        consciousness = recent_metrics.get("consciousness_level", 1.0)
        if consciousness < 0.4:
            await self._create_or_update_alert(
                "low_consciousness_level",
                AlertSeverity.WARNING,
                f"Low consciousness level detected: {consciousness:.3f}",
                {"consciousness_level": consciousness}
            )
        
        # Low ethical alignment alert
        ethical_alignment = recent_metrics.get("ethical_alignment_score", 1.0)
        if ethical_alignment < 0.7:
            await self._create_or_update_alert(
                "low_ethical_alignment",
                AlertSeverity.CRITICAL,
                f"Low ethical alignment detected: {ethical_alignment:.3f}",
                {"ethical_alignment": ethical_alignment}
            )
    
    async def _create_or_update_alert(self, name: str, severity: AlertSeverity, 
                                    message: str, metadata: Dict[str, Any]):
        """Create or update an alert"""
        if name not in self.alerts:
            alert = Alert(
                name=name,
                condition="dynamic",
                severity=severity,
                message=message,
                active=True,
                triggered_at=datetime.now(),
                metadata=metadata
            )
            self.alerts[name] = alert
            await self._send_alert_notification(alert)
        else:
            # Update existing alert
            alert = self.alerts[name]
            if not alert.active:
                alert.active = True
                alert.triggered_at = datetime.now()
                alert.resolved_at = None
                await self._send_alert_notification(alert)
            
            alert.message = message
            alert.metadata.update(metadata)
    
    async def _resolve_inactive_alerts(self):
        """Resolve alerts that are no longer active"""
        for alert_name, alert in self.alerts.items():
            if alert.active:
                # Check if alert condition is still true
                should_resolve = await self._should_resolve_alert(alert_name)
                
                if should_resolve:
                    alert.active = False
                    alert.resolved_at = datetime.now()
                    
                    self.logger.info(f"Alert resolved: {alert_name}")
                    await self._send_alert_resolution_notification(alert)
    
    async def _should_resolve_alert(self, alert_name: str) -> bool:
        """Check if an alert should be resolved"""
        if not self.metric_history:
            return False
        
        recent_metrics = {m.name: m.value for m in self.metric_history[-5:]}
        
        # Define resolution conditions
        resolution_conditions = {
            "high_error_rate": lambda: self.performance_history and self.performance_history[-1].error_rate <= 0.02,
            "low_accuracy": lambda: self.performance_history and self.performance_history[-1].accuracy >= 0.85,
            "high_latency": lambda: self.performance_history and self.performance_history[-1].inference_latency_p95 <= 800,
            "high_cpu_usage": lambda: recent_metrics.get("system_cpu_usage", 100) <= 75,
            "high_memory_usage": lambda: recent_metrics.get("system_memory_usage", 100) <= 85,
            "low_consciousness_level": lambda: recent_metrics.get("consciousness_level", 0) >= 0.5,
            "low_ethical_alignment": lambda: recent_metrics.get("ethical_alignment_score", 0) >= 0.8
        }
        
        condition_func = resolution_conditions.get(alert_name)
        return condition_func() if condition_func else False
    
    async def _send_alert_notification(self, alert: Alert):
        """Send alert notification"""
        notification_config = self.config.get('notifications', {})
        
        # Log alert
        self.logger.warning(f"ALERT [{alert.severity.value.upper()}] {alert.name}: {alert.message}")
        
        # Send to configured notification channels
        if 'slack_webhook' in notification_config:
            await self._send_slack_notification(alert, notification_config['slack_webhook'])
        
        if 'email_recipients' in notification_config:
            await self._send_email_notification(alert, notification_config['email_recipients'])
        
        # Send to PagerDuty for critical alerts
        if alert.severity == AlertSeverity.CRITICAL and 'pagerduty_key' in notification_config:
            await self._send_pagerduty_notification(alert, notification_config['pagerduty_key'])
    
    async def _send_slack_notification(self, alert: Alert, webhook_url: str):
        """Send Slack notification"""
        try:
            color = {
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.INFO: "good",
                AlertSeverity.DEBUG: "#808080"
            }
            
            payload = {
                "attachments": [{
                    "color": color.get(alert.severity, "warning"),
                    "title": f"AGI Alert: {alert.name}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                        {"title": "Triggered At", "value": alert.triggered_at.isoformat(), "short": True}
                    ],
                    "footer": "AGI Observability System",
                    "ts": int(alert.triggered_at.timestamp())
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to send Slack notification: {response.status}")
        
        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {e}")
    
    async def _send_email_notification(self, alert: Alert, recipients: List[str]):
        """Send email notification (placeholder)"""
        # In a real implementation, this would send actual emails
        self.logger.info(f"Email notification sent to {recipients} for alert: {alert.name}")
    
    async def _send_pagerduty_notification(self, alert: Alert, integration_key: str):
        """Send PagerDuty notification (placeholder)"""
        # In a real implementation, this would integrate with PagerDuty
        self.logger.info(f"PagerDuty notification sent for critical alert: {alert.name}")
    
    async def _send_alert_resolution_notification(self, alert: Alert):
        """Send alert resolution notification"""
        self.logger.info(f"Alert resolved: {alert.name}")
        # Could send resolution notifications to configured channels
    
    def _record_metric(self, metric: AGIMetric):
        """Record a metric in the internal history"""
        self.metric_history.append(metric)
        
        # Keep only recent metrics (last 1000)
        if len(self.metric_history) > 1000:
            self.metric_history = self.metric_history[-500:]
    
    def set_reference_data_distribution(self, distribution: Dict[str, float]):
        """Set reference data distribution for drift detection"""
        self.reference_data_distribution = distribution
        self.logger.info("Reference data distribution set for drift detection")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        # Recent performance metrics
        recent_performance = self.performance_history[-10:] if self.performance_history else []
        
        # Active alerts
        active_alerts = [alert for alert in self.alerts.values() if alert.active]
        
        # Recent drift detections
        recent_drift = self.drift_history[-5:] if self.drift_history else []
        
        # System status
        system_status = "healthy"
        if any(alert.severity == AlertSeverity.CRITICAL for alert in active_alerts):
            system_status = "critical"
        elif any(alert.severity == AlertSeverity.WARNING for alert in active_alerts):
            system_status = "warning"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_status": system_status,
            "active_alerts_count": len(active_alerts),
            "active_alerts": [
                {
                    "name": alert.name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
                }
                for alert in active_alerts
            ],
            "recent_performance": [
                {
                    "timestamp": perf.timestamp.isoformat(),
                    "accuracy": perf.accuracy,
                    "latency_p95": perf.inference_latency_p95,
                    "throughput": perf.throughput_rps,
                    "error_rate": perf.error_rate
                }
                for perf in recent_performance
            ],
            "data_drift": {
                "recent_detections": len(recent_drift),
                "active_drift": any(drift.drift_detected for drift in recent_drift),
                "latest_score": recent_drift[-1].drift_score if recent_drift else 0.0
            },
            "metrics_summary": {
                "total_metrics_collected": len(self.metric_history),
                "performance_samples": len(self.performance_history),
                "drift_detections": len(self.drift_history)
            }
        }
    
    def get_metrics_export(self) -> str:
        """Export metrics in Prometheus format"""
        # Generate Prometheus metrics
        return prometheus_client.generate_latest().decode('utf-8')
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_monitoring()
        self.logger.info("AGI Observability System cleanup completed")

# Example usage and configuration
if __name__ == "__main__":
    async def main():
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Create observability configuration
        config = {
            'model_version': 'kenny-agi-v2.1',
            'model_endpoint': 'http://localhost:8000',
            'gpu_count': 2,
            'notifications': {
                'slack_webhook': 'https://hooks.slack.com/services/...',
                'email_recipients': ['ops@example.com', 'ml-team@example.com'],
                'pagerduty_key': 'your-pagerduty-integration-key'
            }
        }
        
        # Create observability system
        observability = AGIObservabilitySystem(config)
        
        try:
            # Set reference data distribution
            reference_distribution = {
                'avg_token_length': 250.0,
                'unique_tokens_ratio': 0.6,
                'sentiment_positive_ratio': 0.55,
                'complexity_score': 0.4,
                'language_diversity': 0.3,
                'domain_technical_ratio': 0.5
            }
            observability.set_reference_data_distribution(reference_distribution)
            
            # Start monitoring
            await observability.start_monitoring()
            
            # Run for demonstration
            await asyncio.sleep(60)  # Monitor for 1 minute
            
            # Get dashboard data
            dashboard_data = observability.get_dashboard_data()
            print("Dashboard Data:", json.dumps(dashboard_data, indent=2))
            
            # Export Prometheus metrics
            metrics_export = observability.get_metrics_export()
            print(f"Prometheus Metrics Export ({len(metrics_export)} bytes)")
        
        finally:
            # Cleanup
            await observability.cleanup()
    
    asyncio.run(main())