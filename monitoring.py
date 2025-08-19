#!/usr/bin/env python3
"""
ASI:BUILD Monitoring and Observability System
=============================================

Comprehensive monitoring system with metrics collection, health checks,
performance monitoring, alert definitions, and dashboard configurations.

Features:
- Prometheus metrics collection
- Custom health checks
- Performance monitoring
- Resource usage tracking
- Safety violation monitoring
- Alert definitions and routing
- Dashboard configurations
- Log aggregation
- Real-time notifications
"""

import asyncio
import logging
import time
import json
import os
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

# Monitoring and metrics
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, Summary, Info, Enum, CollectorRegistry, push_to_gateway
import aiofiles
import aiohttp
import redis

# Add the ASI_BUILD path
import sys
ASI_BUILD_ROOT = Path(__file__).parent
sys.path.insert(0, str(ASI_BUILD_ROOT))

# Configure logging
logger = logging.getLogger(__name__)

# Prometheus metrics registry
registry = CollectorRegistry()

# Core system metrics
SYSTEM_INFO = Info('asi_build_system_info', 'System information', registry=registry)
SYSTEM_UPTIME = Gauge('asi_build_uptime_seconds', 'System uptime in seconds', registry=registry)
SYSTEM_STATE = Enum('asi_build_system_state', 'Current system state', 
                   states=['offline', 'initializing', 'active', 'god_mode', 'emergency', 'shutdown'], 
                   registry=registry)

# Resource metrics
CPU_USAGE = Gauge('asi_build_cpu_usage_percent', 'CPU usage percentage', registry=registry)
MEMORY_USAGE = Gauge('asi_build_memory_usage_bytes', 'Memory usage in bytes', registry=registry)
MEMORY_USAGE_PERCENT = Gauge('asi_build_memory_usage_percent', 'Memory usage percentage', registry=registry)
DISK_USAGE = Gauge('asi_build_disk_usage_percent', 'Disk usage percentage', registry=registry)
GPU_USAGE = Gauge('asi_build_gpu_usage_percent', 'GPU usage percentage', ['gpu_id'], registry=registry)
GPU_MEMORY = Gauge('asi_build_gpu_memory_bytes', 'GPU memory usage in bytes', ['gpu_id'], registry=registry)

# Subsystem metrics
SUBSYSTEM_STATUS = Gauge('asi_build_subsystem_status', 'Subsystem status (1=active, 0=inactive)', 
                        ['subsystem'], registry=registry)
SUBSYSTEM_ERRORS = Counter('asi_build_subsystem_errors_total', 'Total subsystem errors', 
                          ['subsystem'], registry=registry)
SUBSYSTEM_PROCESSING_TIME = Histogram('asi_build_subsystem_processing_seconds', 
                                     'Subsystem processing time', ['subsystem'], registry=registry)

# Safety metrics
SAFETY_VIOLATIONS = Counter('asi_build_safety_violations_total', 'Total safety violations', 
                           ['type', 'threat_level'], registry=registry)
REALITY_LOCK_ATTEMPTS = Counter('asi_build_reality_lock_attempts_total', 'Reality lock bypass attempts', 
                               ['lock_type'], registry=registry)
GOD_MODE_SESSIONS = Gauge('asi_build_god_mode_sessions_active', 'Active god mode sessions', registry=registry)
CONSCIOUSNESS_VIOLATIONS = Counter('asi_build_consciousness_violations_total', 'Consciousness access violations', 
                                  ['violation_type'], registry=registry)

# API metrics
API_REQUESTS = Counter('asi_build_api_requests_total', 'Total API requests', 
                      ['method', 'endpoint', 'status'], registry=registry)
API_DURATION = Histogram('asi_build_api_duration_seconds', 'API request duration', 
                        ['method', 'endpoint'], registry=registry)
API_ACTIVE_CONNECTIONS = Gauge('asi_build_api_active_connections', 'Active API connections', registry=registry)

# Performance metrics
REASONING_ACCURACY = Gauge('asi_build_reasoning_accuracy', 'Reasoning accuracy score', registry=registry)
ETHICAL_COMPLIANCE = Gauge('asi_build_ethical_compliance', 'Ethical compliance score', registry=registry)
LEARNING_RATE = Gauge('asi_build_learning_rate', 'Learning rate metric', registry=registry)
COLLABORATION_EFFICIENCY = Gauge('asi_build_collaboration_efficiency', 'Collaboration efficiency', registry=registry)

# Alert metrics
ALERTS_ACTIVE = Gauge('asi_build_alerts_active', 'Currently active alerts', ['severity'], registry=registry)
ALERTS_TOTAL = Counter('asi_build_alerts_total', 'Total alerts generated', ['severity', 'type'], registry=registry)

@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    description: str
    check_function: Callable
    interval: int = 30  # seconds
    timeout: int = 10   # seconds
    critical: bool = False
    enabled: bool = True
    last_run: Optional[float] = None
    last_result: Optional[bool] = None
    last_error: Optional[str] = None

@dataclass
class Alert:
    """Alert definition"""
    id: str
    name: str
    description: str
    severity: str  # critical, warning, info
    condition: str
    threshold: float
    duration: int = 60  # seconds
    enabled: bool = True
    last_triggered: Optional[float] = None
    active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MetricSnapshot:
    """Point-in-time metric snapshot"""
    timestamp: float
    metrics: Dict[str, Any]
    system_state: str
    alerts: List[Dict[str, Any]]

class MonitoringSystem:
    """
    Comprehensive monitoring and observability system for ASI:BUILD
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.start_time = time.time()
        
        # Health checks
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_check_results: Dict[str, Any] = {}
        
        # Alerts
        self.alerts: Dict[str, Alert] = {}
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Dict[str, Any]] = []
        
        # Monitoring state
        self.monitoring_active = False
        self.metric_snapshots: List[MetricSnapshot] = []
        self.max_snapshots = 1000  # Keep last 1000 snapshots
        
        # External connections
        self.redis_client = None
        self.prometheus_gateway = None
        
        # Initialize system info
        SYSTEM_INFO.info({
            'version': '1.0.0',
            'build_date': datetime.now().isoformat(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'platform': os.uname().sysname,
            'hostname': os.uname().nodename
        })
        
        logger.info("Monitoring system initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default monitoring configuration"""
        return {
            "metrics": {
                "collection_interval": 10,  # seconds
                "retention_days": 30,
                "prometheus_gateway": "http://localhost:9091",
                "job_name": "asi_build"
            },
            "health_checks": {
                "enabled": True,
                "default_interval": 30,
                "default_timeout": 10
            },
            "alerts": {
                "enabled": True,
                "webhook_urls": [],
                "email_recipients": [],
                "slack_webhook": None
            },
            "dashboards": {
                "grafana_url": "http://localhost:3000",
                "auto_provision": True
            },
            "logging": {
                "level": "INFO",
                "file_path": "/var/log/asi_build/monitoring.log",
                "max_size_mb": 100,
                "backup_count": 5
            }
        }
    
    async def initialize(self):
        """Initialize the monitoring system"""
        logger.info("Initializing monitoring system...")
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.Redis(
                host='localhost', 
                port=6379, 
                db=1,  # Use different DB for monitoring
                decode_responses=True
            )
            await self._test_redis_connection()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
        
        # Initialize health checks
        await self._initialize_health_checks()
        
        # Initialize alerts
        await self._initialize_alerts()
        
        # Start monitoring tasks
        self.monitoring_active = True
        asyncio.create_task(self._metrics_collection_loop())
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._alert_evaluation_loop())
        
        logger.info("Monitoring system initialized and active")
    
    async def _test_redis_connection(self):
        """Test Redis connection"""
        if self.redis_client:
            await asyncio.get_event_loop().run_in_executor(None, self.redis_client.ping)
            logger.info("Redis connection established")
    
    async def _initialize_health_checks(self):
        """Initialize health check definitions"""
        health_checks = [
            HealthCheck(
                name="system_memory",
                description="System memory usage",
                check_function=self._check_memory_health,
                critical=True
            ),
            HealthCheck(
                name="system_cpu",
                description="System CPU usage",
                check_function=self._check_cpu_health
            ),
            HealthCheck(
                name="disk_space",
                description="Disk space availability",
                check_function=self._check_disk_health,
                critical=True
            ),
            HealthCheck(
                name="asi_core_health",
                description="ASI:BUILD core system health",
                check_function=self._check_asi_core_health,
                critical=True
            ),
            HealthCheck(
                name="safety_protocols",
                description="Safety protocols status",
                check_function=self._check_safety_protocols,
                critical=True
            ),
            HealthCheck(
                name="subsystem_health",
                description="Subsystem health status",
                check_function=self._check_subsystem_health
            ),
            HealthCheck(
                name="api_health",
                description="API server health",
                check_function=self._check_api_health
            ),
            HealthCheck(
                name="database_health",
                description="Database connectivity",
                check_function=self._check_database_health
            )
        ]
        
        for hc in health_checks:
            self.health_checks[hc.name] = hc
        
        logger.info(f"Initialized {len(health_checks)} health checks")
    
    async def _initialize_alerts(self):
        """Initialize alert definitions"""
        alerts = [
            Alert(
                id="high_memory_usage",
                name="High Memory Usage",
                description="System memory usage above threshold",
                severity="warning",
                condition="memory_usage_percent > 80",
                threshold=80.0,
                duration=300  # 5 minutes
            ),
            Alert(
                id="critical_memory_usage",
                name="Critical Memory Usage",
                description="System memory usage critically high",
                severity="critical",
                condition="memory_usage_percent > 95",
                threshold=95.0,
                duration=60  # 1 minute
            ),
            Alert(
                id="high_cpu_usage",
                name="High CPU Usage",
                description="System CPU usage above threshold",
                severity="warning",
                condition="cpu_usage_percent > 90",
                threshold=90.0,
                duration=300
            ),
            Alert(
                id="disk_space_low",
                name="Low Disk Space",
                description="Disk space running low",
                severity="warning",
                condition="disk_usage_percent > 85",
                threshold=85.0,
                duration=600  # 10 minutes
            ),
            Alert(
                id="safety_violation",
                name="Safety Violation",
                description="Safety protocol violation detected",
                severity="critical",
                condition="safety_violations > 0",
                threshold=0.0,
                duration=0  # Immediate
            ),
            Alert(
                id="god_mode_active",
                name="God Mode Active",
                description="God mode is currently active",
                severity="warning",
                condition="god_mode_sessions > 0",
                threshold=0.0,
                duration=0
            ),
            Alert(
                id="subsystem_failures",
                name="Multiple Subsystem Failures",
                description="Multiple subsystems have failed",
                severity="critical",
                condition="failed_subsystems > 5",
                threshold=5.0,
                duration=180  # 3 minutes
            ),
            Alert(
                id="api_high_error_rate",
                name="High API Error Rate",
                description="API error rate above threshold",
                severity="warning",
                condition="api_error_rate > 0.1",
                threshold=0.1,
                duration=300
            )
        ]
        
        for alert in alerts:
            self.alerts[alert.id] = alert
        
        logger.info(f"Initialized {len(alerts)} alert definitions")
    
    async def _metrics_collection_loop(self):
        """Main metrics collection loop"""
        while self.monitoring_active:
            try:
                await self._collect_system_metrics()
                await self._collect_asi_metrics()
                await self._take_metric_snapshot()
                
                await asyncio.sleep(self.config["metrics"]["collection_interval"])
                
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(30)
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # Update uptime
            SYSTEM_UPTIME.set(time.time() - self.start_time)
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            CPU_USAGE.set(cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            MEMORY_USAGE.set(memory.used)
            MEMORY_USAGE_PERCENT.set(memory.percent)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            DISK_USAGE.set(disk.percent)
            
            # GPU metrics (if available)
            try:
                import pynvml
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    
                    # GPU utilization
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    GPU_USAGE.labels(gpu_id=str(i)).set(util.gpu)
                    
                    # GPU memory
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    GPU_MEMORY.labels(gpu_id=str(i)).set(mem_info.used)
                    
            except ImportError:
                pass  # NVIDIA ML library not available
            except Exception as e:
                logger.debug(f"GPU monitoring error: {e}")
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _collect_asi_metrics(self):
        """Collect ASI:BUILD specific metrics"""
        try:
            # This would integrate with the actual ASI:BUILD system
            # For now, we'll use placeholder values
            
            # Safety metrics (would come from safety_protocols.py)
            SAFETY_VIOLATIONS.labels(type="example", threat_level="low")._value._value = 0
            GOD_MODE_SESSIONS.set(0)
            
            # Performance metrics (would come from actual system)
            REASONING_ACCURACY.set(0.85)
            ETHICAL_COMPLIANCE.set(0.92)
            LEARNING_RATE.set(0.7)
            COLLABORATION_EFFICIENCY.set(0.8)
            
        except Exception as e:
            logger.error(f"Error collecting ASI metrics: {e}")
    
    async def _take_metric_snapshot(self):
        """Take a snapshot of current metrics"""
        try:
            # Collect current metric values
            metrics = {
                "timestamp": time.time(),
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "uptime": time.time() - self.start_time
            }
            
            # Add ASI-specific metrics
            metrics.update({
                "reasoning_accuracy": 0.85,  # Would come from actual system
                "ethical_compliance": 0.92,
                "safety_violations": 0,
                "active_subsystems": 25,  # Would come from actual system
                "god_mode_active": False
            })
            
            # Create snapshot
            snapshot = MetricSnapshot(
                timestamp=time.time(),
                metrics=metrics,
                system_state="active",  # Would come from actual system
                alerts=[alert.__dict__ for alert in self.active_alerts]
            )
            
            # Store snapshot
            self.metric_snapshots.append(snapshot)
            
            # Trim old snapshots
            if len(self.metric_snapshots) > self.max_snapshots:
                self.metric_snapshots = self.metric_snapshots[-self.max_snapshots:]
            
            # Store in Redis if available
            if self.redis_client:
                await self._store_metrics_in_redis(metrics)
            
        except Exception as e:
            logger.error(f"Error taking metric snapshot: {e}")
    
    async def _store_metrics_in_redis(self, metrics: Dict[str, Any]):
        """Store metrics in Redis for external access"""
        try:
            # Store latest metrics
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self.redis_client.hset,
                "asi_build:metrics:latest",
                mapping=metrics
            )
            
            # Store time series data
            ts_key = f"asi_build:metrics:timeseries:{int(time.time())}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.hset,
                ts_key,
                mapping=metrics
            )
            
            # Set expiration for time series data (30 days)
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.expire,
                ts_key,
                86400 * 30
            )
            
        except Exception as e:
            logger.error(f"Error storing metrics in Redis: {e}")
    
    async def _health_check_loop(self):
        """Health check evaluation loop"""
        while self.monitoring_active:
            try:
                for name, health_check in self.health_checks.items():
                    if not health_check.enabled:
                        continue
                    
                    # Check if it's time to run
                    if (health_check.last_run is None or 
                        time.time() - health_check.last_run >= health_check.interval):
                        
                        await self._run_health_check(health_check)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)
    
    async def _run_health_check(self, health_check: HealthCheck):
        """Run an individual health check"""
        try:
            health_check.last_run = time.time()
            
            # Run the check function with timeout
            result = await asyncio.wait_for(
                health_check.check_function(),
                timeout=health_check.timeout
            )
            
            health_check.last_result = result
            health_check.last_error = None
            
            # Store result
            self.health_check_results[health_check.name] = {
                "status": "healthy" if result else "unhealthy",
                "last_check": health_check.last_run,
                "critical": health_check.critical
            }
            
            if not result and health_check.critical:
                logger.error(f"CRITICAL health check failed: {health_check.name}")
                await self._trigger_alert(f"health_check_{health_check.name}", {
                    "severity": "critical",
                    "description": f"Critical health check failed: {health_check.description}"
                })
            
        except asyncio.TimeoutError:
            health_check.last_result = False
            health_check.last_error = "Timeout"
            logger.warning(f"Health check timeout: {health_check.name}")
            
        except Exception as e:
            health_check.last_result = False
            health_check.last_error = str(e)
            logger.error(f"Health check error: {health_check.name} - {e}")
    
    # Health check functions
    async def _check_memory_health(self) -> bool:
        """Check system memory health"""
        memory = psutil.virtual_memory()
        return memory.percent < 95  # Fail if > 95%
    
    async def _check_cpu_health(self) -> bool:
        """Check system CPU health"""
        cpu_percent = psutil.cpu_percent(interval=1)
        return cpu_percent < 98  # Fail if > 98%
    
    async def _check_disk_health(self) -> bool:
        """Check disk space health"""
        disk = psutil.disk_usage('/')
        return disk.percent < 95  # Fail if > 95%
    
    async def _check_asi_core_health(self) -> bool:
        """Check ASI:BUILD core system health"""
        # This would check the actual ASI system
        # For now, return True as placeholder
        return True
    
    async def _check_safety_protocols(self) -> bool:
        """Check safety protocols status"""
        # This would check the actual safety system
        # For now, return True as placeholder
        return True
    
    async def _check_subsystem_health(self) -> bool:
        """Check subsystem health"""
        # This would check actual subsystems
        # For now, return True as placeholder
        return True
    
    async def _check_api_health(self) -> bool:
        """Check API server health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8080/health', timeout=5) as response:
                    return response.status == 200
        except:
            return False
    
    async def _check_database_health(self) -> bool:
        """Check database connectivity"""
        # This would check actual database
        # For now, return True as placeholder
        return True
    
    async def _alert_evaluation_loop(self):
        """Alert evaluation loop"""
        while self.monitoring_active:
            try:
                for alert_id, alert in self.alerts.items():
                    if not alert.enabled:
                        continue
                    
                    # Evaluate alert condition
                    triggered = await self._evaluate_alert_condition(alert)
                    
                    if triggered and not alert.active:
                        # Alert triggered
                        await self._activate_alert(alert)
                    elif not triggered and alert.active:
                        # Alert resolved
                        await self._resolve_alert(alert)
                
                await asyncio.sleep(30)  # Evaluate every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in alert evaluation: {e}")
                await asyncio.sleep(60)
    
    async def _evaluate_alert_condition(self, alert: Alert) -> bool:
        """Evaluate if an alert condition is met"""
        try:
            # Get current metrics
            if not self.metric_snapshots:
                return False
            
            latest_metrics = self.metric_snapshots[-1].metrics
            
            # Simple condition evaluation (in production, use proper expression parser)
            if "memory_usage_percent" in alert.condition:
                value = latest_metrics.get("memory_usage_percent", 0)
                return value > alert.threshold
            elif "cpu_usage_percent" in alert.condition:
                value = latest_metrics.get("cpu_usage_percent", 0)
                return value > alert.threshold
            elif "disk_usage_percent" in alert.condition:
                value = latest_metrics.get("disk_usage_percent", 0)
                return value > alert.threshold
            elif "safety_violations" in alert.condition:
                value = latest_metrics.get("safety_violations", 0)
                return value > alert.threshold
            elif "god_mode_sessions" in alert.condition:
                value = latest_metrics.get("god_mode_active", False)
                return value
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating alert condition: {e}")
            return False
    
    async def _activate_alert(self, alert: Alert):
        """Activate an alert"""
        alert.active = True
        alert.last_triggered = time.time()
        self.active_alerts.append(alert)
        
        # Update metrics
        ALERTS_ACTIVE.labels(severity=alert.severity).inc()
        ALERTS_TOTAL.labels(severity=alert.severity, type=alert.name).inc()
        
        # Log alert
        logger.warning(f"ALERT ACTIVATED: {alert.name} - {alert.description}")
        
        # Store in history
        self.alert_history.append({
            "id": alert.id,
            "name": alert.name,
            "severity": alert.severity,
            "description": alert.description,
            "activated_at": alert.last_triggered,
            "status": "active"
        })
        
        # Send notifications
        await self._send_alert_notification(alert, "activated")
    
    async def _resolve_alert(self, alert: Alert):
        """Resolve an alert"""
        alert.active = False
        if alert in self.active_alerts:
            self.active_alerts.remove(alert)
        
        # Update metrics
        ALERTS_ACTIVE.labels(severity=alert.severity).dec()
        
        # Log resolution
        logger.info(f"ALERT RESOLVED: {alert.name}")
        
        # Update history
        for entry in reversed(self.alert_history):
            if entry["id"] == alert.id and entry["status"] == "active":
                entry["status"] = "resolved"
                entry["resolved_at"] = time.time()
                break
        
        # Send notifications
        await self._send_alert_notification(alert, "resolved")
    
    async def _trigger_alert(self, alert_id: str, alert_data: Dict[str, Any]):
        """Manually trigger an alert"""
        alert = Alert(
            id=alert_id,
            name=alert_data.get("name", alert_id),
            description=alert_data["description"],
            severity=alert_data["severity"],
            condition="manual",
            threshold=0.0,
            enabled=True
        )
        
        await self._activate_alert(alert)
    
    async def _send_alert_notification(self, alert: Alert, action: str):
        """Send alert notifications"""
        try:
            # Webhook notifications
            for webhook_url in self.config["alerts"]["webhook_urls"]:
                await self._send_webhook_notification(webhook_url, alert, action)
            
            # Slack notifications
            if self.config["alerts"]["slack_webhook"]:
                await self._send_slack_notification(alert, action)
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")
    
    async def _send_webhook_notification(self, webhook_url: str, alert: Alert, action: str):
        """Send webhook notification"""
        try:
            payload = {
                "alert_id": alert.id,
                "name": alert.name,
                "description": alert.description,
                "severity": alert.severity,
                "action": action,
                "timestamp": time.time()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        logger.info(f"Webhook notification sent: {alert.name}")
                    else:
                        logger.warning(f"Webhook notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
    
    async def _send_slack_notification(self, alert: Alert, action: str):
        """Send Slack notification"""
        try:
            color = {"critical": "danger", "warning": "warning", "info": "good"}.get(alert.severity, "good")
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": f"ASI:BUILD Alert {action.title()}",
                    "fields": [
                        {"title": "Alert", "value": alert.name, "short": True},
                        {"title": "Severity", "value": alert.severity.upper(), "short": True},
                        {"title": "Description", "value": alert.description, "short": False}
                    ],
                    "timestamp": int(time.time())
                }]
            }
            
            webhook_url = self.config["alerts"]["slack_webhook"]
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent: {alert.name}")
                    else:
                        logger.warning(f"Slack notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
    
    async def health_check(self) -> bool:
        """Overall system health check"""
        if not self.monitoring_active:
            return False
        
        # Check if any critical health checks are failing
        for name, result in self.health_check_results.items():
            health_check = self.health_checks.get(name)
            if health_check and health_check.critical and result["status"] != "healthy":
                return False
        
        return True
    
    async def record_health_metrics(self, metrics: Dict[str, Any]):
        """Record health metrics from external systems"""
        try:
            # Update relevant metrics
            if "active_subsystems" in metrics:
                for i in range(metrics["active_subsystems"]):
                    SUBSYSTEM_STATUS.labels(subsystem=f"subsystem_{i}").set(1)
            
            if "error_subsystems" in metrics:
                for i in range(metrics["error_subsystems"]):
                    SUBSYSTEM_ERRORS.labels(subsystem=f"subsystem_{i}").inc()
            
            # Store in snapshots
            snapshot = MetricSnapshot(
                timestamp=time.time(),
                metrics=metrics,
                system_state=metrics.get("state", "unknown"),
                alerts=[]
            )
            self.metric_snapshots.append(snapshot)
            
        except Exception as e:
            logger.error(f"Error recording health metrics: {e}")
    
    async def record_god_mode_activity(self, activity_data: Dict[str, Any]):
        """Record god mode activity"""
        try:
            # Update god mode metrics
            GOD_MODE_SESSIONS.set(activity_data.get("active_sessions", 0))
            
            # Log activity
            logger.warning(f"God mode activity: {activity_data}")
            
            # Store in Redis if available
            if self.redis_client:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.redis_client.lpush,
                    "asi_build:god_mode:activity",
                    json.dumps(activity_data)
                )
                
                # Keep only last 1000 entries
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.redis_client.ltrim,
                    "asi_build:god_mode:activity",
                    0, 999
                )
            
        except Exception as e:
            logger.error(f"Error recording god mode activity: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        if not self.metric_snapshots:
            return {"error": "No metrics available"}
        
        latest = self.metric_snapshots[-1]
        
        return {
            "timestamp": latest.timestamp,
            "system_state": latest.system_state,
            "metrics": latest.metrics,
            "health_checks": {
                name: {
                    "status": result["status"],
                    "last_check": result["last_check"],
                    "critical": result["critical"]
                }
                for name, result in self.health_check_results.items()
            },
            "active_alerts": len(self.active_alerts),
            "alert_summary": {
                alert.severity: len([a for a in self.active_alerts if a.severity == alert.severity])
                for alert in self.active_alerts
            } if self.active_alerts else {}
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        return {
            "overall_health": "healthy" if len([a for a in self.active_alerts if a.severity == "critical"]) == 0 else "unhealthy",
            "monitoring_active": self.monitoring_active,
            "uptime": time.time() - self.start_time,
            "health_checks": {
                name: {
                    "status": hc.last_result,
                    "last_run": hc.last_run,
                    "last_error": hc.last_error,
                    "critical": hc.critical
                }
                for name, hc in self.health_checks.items()
            },
            "active_alerts": [
                {
                    "id": alert.id,
                    "name": alert.name,
                    "severity": alert.severity,
                    "description": alert.description,
                    "duration": time.time() - alert.last_triggered if alert.last_triggered else 0
                }
                for alert in self.active_alerts
            ],
            "metrics_collected": len(self.metric_snapshots),
            "last_metric_collection": self.metric_snapshots[-1].timestamp if self.metric_snapshots else None
        }

# Utility functions
def create_grafana_dashboard_config() -> Dict[str, Any]:
    """Create Grafana dashboard configuration"""
    return {
        "dashboard": {
            "id": None,
            "title": "ASI:BUILD Monitoring Dashboard",
            "tags": ["asi-build", "monitoring"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "System Overview",
                    "type": "stat",
                    "targets": [
                        {"expr": "asi_build_uptime_seconds", "legendFormat": "Uptime"},
                        {"expr": "asi_build_system_state", "legendFormat": "State"}
                    ]
                },
                {
                    "id": 2,
                    "title": "Resource Usage",
                    "type": "graph",
                    "targets": [
                        {"expr": "asi_build_cpu_usage_percent", "legendFormat": "CPU %"},
                        {"expr": "asi_build_memory_usage_percent", "legendFormat": "Memory %"},
                        {"expr": "asi_build_disk_usage_percent", "legendFormat": "Disk %"}
                    ]
                },
                {
                    "id": 3,
                    "title": "Safety Metrics",
                    "type": "graph",
                    "targets": [
                        {"expr": "rate(asi_build_safety_violations_total[5m])", "legendFormat": "Safety Violations/min"},
                        {"expr": "asi_build_god_mode_sessions_active", "legendFormat": "God Mode Sessions"}
                    ]
                },
                {
                    "id": 4,
                    "title": "API Performance",
                    "type": "graph",
                    "targets": [
                        {"expr": "rate(asi_build_api_requests_total[5m])", "legendFormat": "Requests/min"},
                        {"expr": "histogram_quantile(0.95, asi_build_api_duration_seconds)", "legendFormat": "95th percentile latency"}
                    ]
                }
            ],
            "time": {"from": "now-1h", "to": "now"},
            "refresh": "30s"
        }
    }

if __name__ == "__main__":
    # Example usage
    async def test_monitoring():
        monitoring = MonitoringSystem()
        await monitoring.initialize()
        
        # Let it run for a while
        await asyncio.sleep(60)
        
        # Get status
        health = monitoring.get_system_health()
        print(f"System health: {health}")
        
        summary = monitoring.get_metrics_summary()
        print(f"Metrics summary: {summary}")
    
    # Run test
    asyncio.run(test_monitoring())