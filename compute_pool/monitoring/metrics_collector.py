"""
Metrics Collector - Collects and stores system metrics for monitoring and analytics
"""

import asyncio
import logging
import time
import json
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import deque, defaultdict
import statistics


class MetricType(Enum):
    COUNTER = "counter"  # Monotonically increasing value
    GAUGE = "gauge"      # Point-in-time value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"      # Duration measurements


@dataclass
class MetricPoint:
    """Individual metric data point"""
    metric_id: str
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
            "type": self.metric_type.value
        }


@dataclass
class MetricSeries:
    """Time series of metric data points"""
    name: str
    metric_type: MetricType
    points: deque = field(default_factory=lambda: deque(maxlen=1000))  # Keep last 1000 points
    labels: Dict[str, str] = field(default_factory=dict)
    
    def add_point(self, value: float, timestamp: Optional[float] = None) -> None:
        if timestamp is None:
            timestamp = time.time()
        
        point = MetricPoint(
            metric_id=str(uuid.uuid4()),
            name=self.name,
            value=value,
            timestamp=timestamp,
            labels=self.labels,
            metric_type=self.metric_type
        )
        
        self.points.append(point)
    
    def get_latest(self) -> Optional[MetricPoint]:
        return self.points[-1] if self.points else None
    
    def get_range(self, start_time: float, end_time: float) -> List[MetricPoint]:
        return [
            point for point in self.points 
            if start_time <= point.timestamp <= end_time
        ]
    
    def get_statistics(self, window_seconds: float = 300) -> Dict[str, float]:
        """Get statistical summary of recent values"""
        cutoff_time = time.time() - window_seconds
        recent_values = [
            point.value for point in self.points 
            if point.timestamp >= cutoff_time
        ]
        
        if not recent_values:
            return {}
        
        return {
            "count": len(recent_values),
            "min": min(recent_values),
            "max": max(recent_values),
            "mean": statistics.mean(recent_values),
            "median": statistics.median(recent_values),
            "stddev": statistics.stdev(recent_values) if len(recent_values) > 1 else 0.0
        }


class MetricsCollector:
    """
    Comprehensive metrics collection system with storage and aggregation
    """
    
    def __init__(self, collection_interval: float = 10.0):
        self.collection_interval = collection_interval
        self.logger = logging.getLogger("metrics_collector")
        
        # Metric storage
        self.metrics: Dict[str, MetricSeries] = {}
        self.db_path: Optional[str] = None
        self.db_connection: Optional[sqlite3.Connection] = None
        
        # Collection tasks
        self.collection_task: Optional[asyncio.Task] = None
        self.persistence_task: Optional[asyncio.Task] = None
        
        # Aggregation windows
        self.aggregation_windows = [60, 300, 3600, 86400]  # 1min, 5min, 1hour, 1day
        self.aggregated_metrics: Dict[str, Dict[int, Dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
        
        # Alert thresholds
        self.alert_thresholds: Dict[str, Dict[str, float]] = {}
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self._stats = {
            "total_metrics": 0,
            "total_points": 0,
            "collection_runs": 0,
            "last_collection_time": 0.0,
            "active_alerts": 0,
            "storage_size_bytes": 0
        }
        
    async def initialize(self, db_path: Optional[str] = None) -> None:
        """Initialize the metrics collector"""
        self.logger.info("Initializing metrics collector")
        
        # Set up database for persistence
        if db_path:
            self.db_path = db_path
            await self._initialize_database()
        
        # Start collection and persistence tasks
        self.collection_task = asyncio.create_task(self._collection_loop())
        
        if self.db_path:
            self.persistence_task = asyncio.create_task(self._persistence_loop())
        
        self.logger.info("Metrics collector initialized")
        
    async def _initialize_database(self) -> None:
        """Initialize SQLite database for metrics storage"""
        try:
            self.db_connection = sqlite3.connect(self.db_path, check_same_thread=False)
            
            # Create tables
            self.db_connection.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_id TEXT UNIQUE,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    labels TEXT,
                    type TEXT NOT NULL,
                    INDEX(name, timestamp)
                )
            """)
            
            self.db_connection.execute("""
                CREATE TABLE IF NOT EXISTS aggregated_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    window_seconds INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    count INTEGER,
                    min_value REAL,
                    max_value REAL,
                    avg_value REAL,
                    sum_value REAL,
                    UNIQUE(name, window_seconds, timestamp)
                )
            """)
            
            self.db_connection.commit()
            self.logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        timestamp: Optional[float] = None
    ) -> None:
        """Record a metric value"""
        if labels is None:
            labels = {}
            
        # Create metric key from name and labels
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        metric_key = f"{name}:{label_str}" if label_str else name
        
        # Create or get metric series
        if metric_key not in self.metrics:
            self.metrics[metric_key] = MetricSeries(
                name=name,
                metric_type=metric_type,
                labels=labels
            )
            self._stats["total_metrics"] += 1
        
        # Add data point
        self.metrics[metric_key].add_point(value, timestamp)
        self._stats["total_points"] += 1
        
        # Check for alerts
        self._check_alert_thresholds(name, value, labels)
        
    async def record_utilization(self, utilization_data: Dict[str, float]) -> None:
        """Record resource utilization metrics"""
        timestamp = time.time()
        
        for resource, utilization in utilization_data.items():
            self.record_metric(
                name=f"resource_utilization",
                value=utilization,
                labels={"resource": resource},
                timestamp=timestamp
            )
    
    def record_counter(self, name: str, increment: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a counter metric (always incrementing)"""
        self.record_metric(name, increment, MetricType.COUNTER, labels)
        
    def record_timer(self, name: str, duration_seconds: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a timer metric"""
        self.record_metric(name, duration_seconds, MetricType.TIMER, labels)
        
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric"""
        self.record_metric(name, value, MetricType.HISTOGRAM, labels)
        
    def get_metric(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[MetricSeries]:
        """Get a metric series by name and labels"""
        if labels is None:
            labels = {}
            
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        metric_key = f"{name}:{label_str}" if label_str else name
        
        return self.metrics.get(metric_key)
        
    def get_metric_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get the latest value of a metric"""
        metric = self.get_metric(name, labels)
        if metric:
            latest = metric.get_latest()
            return latest.value if latest else None
        return None
        
    def query_metrics(
        self,
        name: str,
        start_time: float,
        end_time: float,
        labels: Optional[Dict[str, str]] = None
    ) -> List[MetricPoint]:
        """Query metrics within a time range"""
        metric = self.get_metric(name, labels)
        if metric:
            return metric.get_range(start_time, end_time)
        return []
        
    def get_metrics_list(self) -> List[str]:
        """Get list of all metric names"""
        metric_names = set()
        for metric_key in self.metrics.keys():
            name = metric_key.split(':')[0]
            metric_names.add(name)
        return sorted(list(metric_names))
        
    def set_alert_threshold(
        self,
        metric_name: str,
        threshold_type: str,  # 'min', 'max', 'rate'
        threshold_value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set alert threshold for a metric"""
        if labels is None:
            labels = {}
            
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        alert_key = f"{metric_name}:{label_str}" if label_str else metric_name
        
        if alert_key not in self.alert_thresholds:
            self.alert_thresholds[alert_key] = {}
            
        self.alert_thresholds[alert_key][threshold_type] = threshold_value
        
        self.logger.info(f"Set {threshold_type} threshold for {alert_key}: {threshold_value}")
        
    def _check_alert_thresholds(self, name: str, value: float, labels: Dict[str, str]) -> None:
        """Check if metric value violates any thresholds"""
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        alert_key = f"{name}:{label_str}" if label_str else name
        
        if alert_key not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[alert_key]
        current_time = time.time()
        
        # Check min threshold
        if "min" in thresholds and value < thresholds["min"]:
            self._trigger_alert(alert_key, "min", value, thresholds["min"], current_time)
        
        # Check max threshold
        if "max" in thresholds and value > thresholds["max"]:
            self._trigger_alert(alert_key, "max", value, thresholds["max"], current_time)
        
        # Check rate threshold (change per second)
        if "rate" in thresholds:
            metric = self.get_metric(name, labels)
            if metric and len(metric.points) >= 2:
                prev_point = metric.points[-2]
                time_delta = current_time - prev_point.timestamp
                if time_delta > 0:
                    rate = abs(value - prev_point.value) / time_delta
                    if rate > thresholds["rate"]:
                        self._trigger_alert(alert_key, "rate", rate, thresholds["rate"], current_time)
    
    def _trigger_alert(
        self,
        alert_key: str,
        threshold_type: str,
        current_value: float,
        threshold_value: float,
        timestamp: float
    ) -> None:
        """Trigger an alert"""
        alert_id = f"{alert_key}:{threshold_type}"
        
        # Avoid duplicate alerts within 5 minutes
        if alert_id in self.active_alerts:
            if timestamp - self.active_alerts[alert_id]["timestamp"] < 300:
                return
        
        alert = {
            "alert_id": alert_id,
            "metric_name": alert_key.split(':')[0],
            "threshold_type": threshold_type,
            "current_value": current_value,
            "threshold_value": threshold_value,
            "timestamp": timestamp,
            "severity": self._calculate_severity(threshold_type, current_value, threshold_value)
        }
        
        self.active_alerts[alert_id] = alert
        self._stats["active_alerts"] = len(self.active_alerts)
        
        self.logger.warning(
            f"ALERT: {alert_key} {threshold_type} threshold violated - "
            f"current: {current_value}, threshold: {threshold_value}"
        )
    
    def _calculate_severity(self, threshold_type: str, current_value: float, threshold_value: float) -> str:
        """Calculate alert severity based on how much the threshold is exceeded"""
        if threshold_type == "max":
            ratio = current_value / threshold_value if threshold_value > 0 else 0
        elif threshold_type == "min":
            ratio = threshold_value / current_value if current_value > 0 else 0
        else:  # rate
            ratio = current_value / threshold_value if threshold_value > 0 else 0
        
        if ratio >= 2.0:
            return "critical"
        elif ratio >= 1.5:
            return "high"
        elif ratio >= 1.2:
            return "medium"
        else:
            return "low"
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts"""
        return list(self.active_alerts.values())
    
    def clear_alert(self, alert_id: str) -> bool:
        """Clear an active alert"""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            self._stats["active_alerts"] = len(self.active_alerts)
            self.logger.info(f"Cleared alert: {alert_id}")
            return True
        return False
    
    async def _collection_loop(self) -> None:
        """Main metrics collection loop"""
        while True:
            try:
                await self._collect_system_metrics()
                await self._aggregate_metrics()
                
                self._stats["collection_runs"] += 1
                self._stats["last_collection_time"] = time.time()
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(30.0)
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics"""
        try:
            import psutil
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            self.record_metric("system_cpu_usage_percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.record_metric("system_memory_usage_percent", memory.percent)
            self.record_metric("system_memory_available_bytes", memory.available)
            self.record_metric("system_memory_used_bytes", memory.used)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self.record_metric("system_disk_usage_percent", (disk.used / disk.total) * 100)
            self.record_metric("system_disk_free_bytes", disk.free)
            
            # Network metrics
            net_io = psutil.net_io_counters()
            if net_io:
                self.record_counter("system_network_bytes_sent", net_io.bytes_sent)
                self.record_counter("system_network_bytes_recv", net_io.bytes_recv)
                self.record_counter("system_network_packets_sent", net_io.packets_sent)
                self.record_counter("system_network_packets_recv", net_io.packets_recv)
            
            # Load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()
                self.record_metric("system_load_1min", load_avg[0])
                self.record_metric("system_load_5min", load_avg[1])
                self.record_metric("system_load_15min", load_avg[2])
            except (AttributeError, OSError):
                pass  # Not available on all systems
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    async def _aggregate_metrics(self) -> None:
        """Aggregate metrics over different time windows"""
        current_time = time.time()
        
        for metric_key, metric_series in self.metrics.items():
            metric_name = metric_series.name
            
            for window_seconds in self.aggregation_windows:
                # Calculate window start time
                window_start = current_time - window_seconds
                
                # Get points in this window
                points_in_window = [
                    point.value for point in metric_series.points
                    if point.timestamp >= window_start
                ]
                
                if not points_in_window:
                    continue
                
                # Calculate aggregations
                aggregation = {
                    "count": len(points_in_window),
                    "min": min(points_in_window),
                    "max": max(points_in_window),
                    "avg": sum(points_in_window) / len(points_in_window),
                    "sum": sum(points_in_window)
                }
                
                # Store aggregation
                self.aggregated_metrics[metric_name][window_seconds] = aggregation
    
    def get_aggregated_metrics(
        self,
        metric_name: str,
        window_seconds: int
    ) -> Optional[Dict[str, float]]:
        """Get aggregated metrics for a time window"""
        return self.aggregated_metrics.get(metric_name, {}).get(window_seconds)
    
    async def _persistence_loop(self) -> None:
        """Persist metrics to database"""
        while True:
            try:
                await self._persist_metrics_to_db()
                await asyncio.sleep(60.0)  # Persist every minute
                
            except Exception as e:
                self.logger.error(f"Error in persistence loop: {e}")
                await asyncio.sleep(120.0)
    
    async def _persist_metrics_to_db(self) -> None:
        """Persist recent metrics to database"""
        if not self.db_connection:
            return
        
        try:
            current_time = time.time()
            cutoff_time = current_time - 120  # Persist last 2 minutes
            
            metrics_to_persist = []
            
            for metric_series in self.metrics.values():
                for point in metric_series.points:
                    if point.timestamp >= cutoff_time:
                        metrics_to_persist.append((
                            point.metric_id,
                            point.name,
                            point.value,
                            point.timestamp,
                            json.dumps(point.labels),
                            point.metric_type.value
                        ))
            
            if metrics_to_persist:
                self.db_connection.executemany("""
                    INSERT OR IGNORE INTO metrics 
                    (metric_id, name, value, timestamp, labels, type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, metrics_to_persist)
                
                self.db_connection.commit()
                
                self.logger.debug(f"Persisted {len(metrics_to_persist)} metrics to database")
                
                # Update storage size estimate
                self._stats["storage_size_bytes"] = self._estimate_db_size()
        
        except Exception as e:
            self.logger.error(f"Error persisting metrics: {e}")
    
    def _estimate_db_size(self) -> int:
        """Estimate database size"""
        try:
            if self.db_connection:
                cursor = self.db_connection.execute("SELECT COUNT(*) FROM metrics")
                count = cursor.fetchone()[0]
                # Rough estimate: 200 bytes per metric point
                return count * 200
        except:
            pass
        return 0
    
    async def export_metrics(
        self,
        start_time: float,
        end_time: float,
        format: str = "json"
    ) -> str:
        """Export metrics in specified format"""
        exported_metrics = []
        
        for metric_series in self.metrics.values():
            points = metric_series.get_range(start_time, end_time)
            if points:
                exported_metrics.append({
                    "name": metric_series.name,
                    "type": metric_series.metric_type.value,
                    "labels": metric_series.labels,
                    "points": [point.to_dict() for point in points]
                })
        
        if format == "json":
            return json.dumps({
                "start_time": start_time,
                "end_time": end_time,
                "metrics": exported_metrics
            }, indent=2)
        elif format == "prometheus":
            return self._export_prometheus_format(exported_metrics)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_prometheus_format(self, metrics: List[Dict[str, Any]]) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        for metric in metrics:
            name = metric["name"].replace("-", "_")
            metric_type = metric["type"]
            
            # Add TYPE and HELP comments
            lines.append(f"# TYPE {name} {metric_type}")
            lines.append(f"# HELP {name} {metric['name']} metric")
            
            # Add data points
            for point in metric["points"]:
                labels_str = ""
                if point["labels"]:
                    label_pairs = [f'{k}="{v}"' for k, v in point["labels"].items()]
                    labels_str = "{" + ",".join(label_pairs) + "}"
                
                lines.append(f"{name}{labels_str} {point['value']} {int(point['timestamp'] * 1000)}")
        
        return "\n".join(lines)
    
    def get_collector_status(self) -> Dict[str, Any]:
        """Get metrics collector status"""
        return {
            "statistics": self._stats.copy(),
            "metrics_count": len(self.metrics),
            "alert_thresholds_count": len(self.alert_thresholds),
            "collection_interval": self.collection_interval,
            "database_enabled": self.db_path is not None,
            "aggregation_windows": self.aggregation_windows
        }
    
    async def cleanup_old_metrics(self, retention_days: int = 7) -> int:
        """Clean up old metrics from database"""
        if not self.db_connection:
            return 0
        
        try:
            cutoff_time = time.time() - (retention_days * 86400)
            
            cursor = self.db_connection.execute(
                "SELECT COUNT(*) FROM metrics WHERE timestamp < ?",
                (cutoff_time,)
            )
            count_to_delete = cursor.fetchone()[0]
            
            self.db_connection.execute(
                "DELETE FROM metrics WHERE timestamp < ?",
                (cutoff_time,)
            )
            
            self.db_connection.execute(
                "DELETE FROM aggregated_metrics WHERE timestamp < ?",
                (cutoff_time,)
            )
            
            self.db_connection.commit()
            
            self.logger.info(f"Cleaned up {count_to_delete} old metric points")
            return count_to_delete
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old metrics: {e}")
            return 0
    
    async def shutdown(self) -> None:
        """Shutdown the metrics collector"""
        self.logger.info("Shutting down metrics collector")
        
        # Cancel collection tasks
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        if self.persistence_task:
            self.persistence_task.cancel()
            try:
                await self.persistence_task
            except asyncio.CancelledError:
                pass
        
        # Final persistence
        if self.db_connection:
            await self._persist_metrics_to_db()
            self.db_connection.close()
        
        self.logger.info("Metrics collector shutdown complete")