"""
Multiverse Metrics Collector
============================

Comprehensive metrics collection and analysis system for monitoring
multiverse performance, stability, and operational characteristics.
"""

import numpy as np
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics
import json
import uuid


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"
    DISTRIBUTION = "distribution"


class MetricAggregation(Enum):
    """Metric aggregation methods."""
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    STANDARD_DEVIATION = "std"


@dataclass
class MetricValue:
    """Represents a single metric value."""
    value: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'value': self.value,
            'timestamp': self.timestamp,
            'tags': self.tags,
            'metadata': self.metadata
        }


@dataclass
class Metric:
    """Represents a metric with its values and properties."""
    name: str
    metric_type: MetricType
    description: str = ""
    unit: str = ""
    values: deque = field(default_factory=lambda: deque(maxlen=10000))
    creation_time: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def add_value(self, value: Union[int, float], 
                 tags: Optional[Dict[str, str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """Add a value to the metric."""
        metric_value = MetricValue(
            value=value,
            tags=tags or {},
            metadata=metadata or {}
        )
        
        self.values.append(metric_value)
        self.last_updated = time.time()
    
    def get_latest_value(self) -> Optional[MetricValue]:
        """Get the latest metric value."""
        return self.values[-1] if self.values else None
    
    def get_values_in_range(self, start_time: float, end_time: float) -> List[MetricValue]:
        """Get values within a time range."""
        return [
            value for value in self.values
            if start_time <= value.timestamp <= end_time
        ]
    
    def calculate_statistics(self, time_window: Optional[float] = None) -> Dict[str, float]:
        """Calculate statistics for metric values."""
        if not self.values:
            return {}
        
        # Filter by time window if specified
        if time_window:
            cutoff_time = time.time() - time_window
            values = [v.value for v in self.values if v.timestamp >= cutoff_time]
        else:
            values = [v.value for v in self.values]
        
        if not values:
            return {}
        
        stats = {
            'count': len(values),
            'sum': sum(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'latest': values[-1]
        }
        
        if len(values) > 1:
            stats['std'] = statistics.stdev(values)
            stats['median'] = statistics.median(values)
            
            # Percentiles
            if len(values) >= 4:
                stats['p50'] = statistics.median(values)
                stats['p95'] = np.percentile(values, 95)
                stats['p99'] = np.percentile(values, 99)
        
        return stats
    
    def calculate_rate(self, time_window: float = 60.0) -> float:
        """Calculate rate of change over time window."""
        cutoff_time = time.time() - time_window
        recent_values = [v for v in self.values if v.timestamp >= cutoff_time]
        
        if len(recent_values) < 2:
            return 0.0
        
        # Calculate rate based on first and last values in window
        first_value = recent_values[0]
        last_value = recent_values[-1]
        
        time_diff = last_value.timestamp - first_value.timestamp
        if time_diff == 0:
            return 0.0
        
        if self.metric_type == MetricType.COUNTER:
            # For counters, rate is change per second
            value_diff = last_value.value - first_value.value
            return value_diff / time_diff
        else:
            # For other types, use average
            total_change = sum(v.value for v in recent_values)
            return total_change / time_diff


class MultiverseMetrics:
    """
    Comprehensive metrics collection system for multiverse operations.
    
    Collects, stores, and analyzes performance metrics, operational statistics,
    and system health indicators across all multiverse components.
    """
    
    def __init__(self, retention_period: float = 3600.0):
        """
        Initialize metrics collector.
        
        Args:
            retention_period: How long to retain metrics (seconds)
        """
        self.collector_id = str(uuid.uuid4())
        self.logger = logging.getLogger("multiverse.metrics")
        
        # Metric storage
        self.metrics: Dict[str, Metric] = {}
        self.metric_lock = threading.RLock()
        
        # Configuration
        self.retention_period = retention_period
        self.collection_interval = 10.0  # seconds
        self.cleanup_interval = 300.0  # 5 minutes
        
        # Background tasks
        self.is_running = False
        self.collection_thread: Optional[threading.Thread] = None
        self.cleanup_thread: Optional[threading.Thread] = None
        
        # Built-in metrics
        self._initialize_system_metrics()
        
        self.logger.info("MultiverseMetrics initialized: %s", self.collector_id)
    
    def _initialize_system_metrics(self):
        """Initialize built-in system metrics."""
        system_metrics = [
            ("multiverse.active_universes", MetricType.GAUGE, "Number of active universes"),
            ("multiverse.total_universes", MetricType.COUNTER, "Total universes created"),
            ("multiverse.quantum_energy", MetricType.GAUGE, "Total quantum energy"),
            ("multiverse.portal_count", MetricType.GAUGE, "Active portal count"),
            ("multiverse.timeline_branches", MetricType.COUNTER, "Timeline branches created"),
            ("multiverse.reality_anchor_count", MetricType.GAUGE, "Active reality anchors"),
            ("multiverse.stability_index", MetricType.GAUGE, "Overall stability index"),
            ("multiverse.processing_latency", MetricType.HISTOGRAM, "Processing latency"),
            ("multiverse.event_count", MetricType.COUNTER, "Events processed"),
            ("multiverse.error_count", MetricType.COUNTER, "Errors encountered"),
            ("system.cpu_usage", MetricType.GAUGE, "CPU usage percentage"),
            ("system.memory_usage", MetricType.GAUGE, "Memory usage percentage"),
            ("system.uptime", MetricType.GAUGE, "System uptime")
        ]
        
        for name, metric_type, description in system_metrics:
            self.create_metric(name, metric_type, description)
    
    def start(self):
        """Start metrics collection."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start collection thread
        self.collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True,
            name="MetricsCollector"
        )
        self.collection_thread.start()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="MetricsCleanup"
        )
        self.cleanup_thread.start()
        
        self.logger.info("Metrics collection started")
    
    def stop(self):
        """Stop metrics collection."""
        self.is_running = False
        
        if self.collection_thread and self.collection_thread.is_alive():
            self.collection_thread.join(timeout=5.0)
        
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5.0)
        
        self.logger.info("Metrics collection stopped")
    
    def create_metric(self, name: str, metric_type: MetricType, 
                     description: str = "", unit: str = "",
                     tags: Optional[Dict[str, str]] = None) -> Metric:
        """
        Create a new metric.
        
        Args:
            name: Metric name
            metric_type: Type of metric
            description: Metric description
            unit: Unit of measurement
            tags: Metric tags
            
        Returns:
            Created metric
        """
        with self.metric_lock:
            if name in self.metrics:
                return self.metrics[name]
            
            metric = Metric(
                name=name,
                metric_type=metric_type,
                description=description,
                unit=unit,
                tags=tags or {}
            )
            
            self.metrics[name] = metric
            
            self.logger.debug("Created metric: %s (%s)", name, metric_type.value)
            
            return metric
    
    def record_value(self, name: str, value: Union[int, float],
                    tags: Optional[Dict[str, str]] = None,
                    metadata: Optional[Dict[str, Any]] = None):
        """
        Record a metric value.
        
        Args:
            name: Metric name
            value: Value to record
            tags: Additional tags
            metadata: Additional metadata
        """
        with self.metric_lock:
            metric = self.metrics.get(name)
            if not metric:
                self.logger.warning("Metric not found: %s", name)
                return
            
            metric.add_value(value, tags, metadata)
    
    def increment_counter(self, name: str, value: Union[int, float] = 1,
                         tags: Optional[Dict[str, str]] = None):
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            value: Value to add
            tags: Additional tags
        """
        with self.metric_lock:
            metric = self.metrics.get(name)
            if not metric:
                # Auto-create counter metric
                metric = self.create_metric(name, MetricType.COUNTER)
            
            # Get current value
            current = metric.get_latest_value()
            current_value = current.value if current else 0
            
            # Add increment
            new_value = current_value + value
            metric.add_value(new_value, tags)
    
    def set_gauge(self, name: str, value: Union[int, float],
                 tags: Optional[Dict[str, str]] = None):
        """
        Set a gauge metric value.
        
        Args:
            name: Gauge name
            value: Value to set
            tags: Additional tags
        """
        with self.metric_lock:
            metric = self.metrics.get(name)
            if not metric:
                # Auto-create gauge metric
                metric = self.create_metric(name, MetricType.GAUGE)
            
            metric.add_value(value, tags)
    
    def record_timer(self, name: str, duration: float,
                    tags: Optional[Dict[str, str]] = None):
        """
        Record a timer metric.
        
        Args:
            name: Timer name
            duration: Duration in seconds
            tags: Additional tags
        """
        with self.metric_lock:
            metric = self.metrics.get(name)
            if not metric:
                # Auto-create timer metric
                metric = self.create_metric(name, MetricType.TIMER, unit="seconds")
            
            metric.add_value(duration, tags)
    
    def record_histogram(self, name: str, value: Union[int, float],
                        tags: Optional[Dict[str, str]] = None):
        """
        Record a histogram metric.
        
        Args:
            name: Histogram name
            value: Value to record
            tags: Additional tags
        """
        with self.metric_lock:
            metric = self.metrics.get(name)
            if not metric:
                # Auto-create histogram metric
                metric = self.create_metric(name, MetricType.HISTOGRAM)
            
            metric.add_value(value, tags)
    
    def timer_context(self, name: str, tags: Optional[Dict[str, str]] = None):
        """
        Context manager for timing operations.
        
        Args:
            name: Timer name
            tags: Additional tags
        """
        return TimerContext(self, name, tags)
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        with self.metric_lock:
            return self.metrics.get(name)
    
    def get_metric_statistics(self, name: str, 
                             time_window: Optional[float] = None) -> Dict[str, float]:
        """
        Get statistics for a metric.
        
        Args:
            name: Metric name
            time_window: Time window in seconds (None for all data)
            
        Returns:
            Statistics dictionary
        """
        with self.metric_lock:
            metric = self.metrics.get(name)
            if not metric:
                return {}
            
            return metric.calculate_statistics(time_window)
    
    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all metrics."""
        with self.metric_lock:
            return self.metrics.copy()
    
    def get_metrics_by_prefix(self, prefix: str) -> Dict[str, Metric]:
        """Get metrics with names starting with prefix."""
        with self.metric_lock:
            return {
                name: metric for name, metric in self.metrics.items()
                if name.startswith(prefix)
            }
    
    def aggregate_metrics(self, names: List[str], 
                         aggregation: MetricAggregation,
                         time_window: Optional[float] = None) -> float:
        """
        Aggregate multiple metrics.
        
        Args:
            names: List of metric names
            aggregation: Aggregation method
            time_window: Time window in seconds
            
        Returns:
            Aggregated value
        """
        values = []
        
        with self.metric_lock:
            for name in names:
                metric = self.metrics.get(name)
                if metric:
                    stats = metric.calculate_statistics(time_window)
                    if 'mean' in stats:
                        values.append(stats['mean'])
        
        if not values:
            return 0.0
        
        if aggregation == MetricAggregation.SUM:
            return sum(values)
        elif aggregation == MetricAggregation.AVERAGE:
            return statistics.mean(values)
        elif aggregation == MetricAggregation.MIN:
            return min(values)
        elif aggregation == MetricAggregation.MAX:
            return max(values)
        elif aggregation == MetricAggregation.COUNT:
            return len(values)
        elif aggregation == MetricAggregation.MEDIAN:
            return statistics.median(values)
        elif aggregation == MetricAggregation.STANDARD_DEVIATION:
            return statistics.stdev(values) if len(values) > 1 else 0.0
        else:
            return statistics.mean(values)
    
    def _collection_loop(self):
        """Background metrics collection loop."""
        while self.is_running:
            try:
                self._collect_system_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                self.logger.error("Error in metrics collection: %s", e)
                time.sleep(1.0)
    
    def _cleanup_loop(self):
        """Background metrics cleanup loop."""
        while self.is_running:
            try:
                self._cleanup_old_metrics()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                self.logger.error("Error in metrics cleanup: %s", e)
                time.sleep(10.0)
    
    def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.set_gauge("system.cpu_usage", cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.set_gauge("system.memory_usage", memory.percent)
            
            # Uptime
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
            self.set_gauge("system.uptime", uptime)
            
        except ImportError:
            # psutil not available, use basic metrics
            self.set_gauge("system.uptime", time.time())
    
    def _cleanup_old_metrics(self):
        """Clean up old metric values."""
        cutoff_time = time.time() - self.retention_period
        
        with self.metric_lock:
            for metric in self.metrics.values():
                # Remove old values
                while metric.values and metric.values[0].timestamp < cutoff_time:
                    metric.values.popleft()
    
    def export_metrics(self, format: str = "json") -> str:
        """
        Export metrics in specified format.
        
        Args:
            format: Export format ("json", "prometheus", "csv")
            
        Returns:
            Exported metrics string
        """
        with self.metric_lock:
            if format == "json":
                return self._export_json()
            elif format == "prometheus":
                return self._export_prometheus()
            elif format == "csv":
                return self._export_csv()
            else:
                raise ValueError(f"Unsupported export format: {format}")
    
    def _export_json(self) -> str:
        """Export metrics as JSON."""
        export_data = {
            'collector_id': self.collector_id,
            'timestamp': time.time(),
            'metrics': {}
        }
        
        for name, metric in self.metrics.items():
            export_data['metrics'][name] = {
                'type': metric.metric_type.value,
                'description': metric.description,
                'unit': metric.unit,
                'statistics': metric.calculate_statistics(),
                'value_count': len(metric.values),
                'last_updated': metric.last_updated
            }
        
        return json.dumps(export_data, indent=2)
    
    def _export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        for name, metric in self.metrics.items():
            # Convert name to Prometheus format
            prom_name = name.replace('.', '_').replace('-', '_')
            
            # Add help and type
            lines.append(f"# HELP {prom_name} {metric.description}")
            lines.append(f"# TYPE {prom_name} {metric.metric_type.value}")
            
            # Add current value
            latest = metric.get_latest_value()
            if latest:
                tags_str = ""
                if latest.tags:
                    tag_pairs = [f'{k}="{v}"' for k, v in latest.tags.items()]
                    tags_str = "{" + ",".join(tag_pairs) + "}"
                
                lines.append(f"{prom_name}{tags_str} {latest.value} {int(latest.timestamp * 1000)}")
        
        return "\n".join(lines)
    
    def _export_csv(self) -> str:
        """Export metrics as CSV."""
        lines = ["metric_name,timestamp,value,type,tags"]
        
        for name, metric in self.metrics.items():
            for value in list(metric.values)[-100:]:  # Last 100 values
                tags_str = ";".join([f"{k}={v}" for k, v in value.tags.items()])
                line = f"{name},{value.timestamp},{value.value},{metric.metric_type.value},{tags_str}"
                lines.append(line)
        
        return "\n".join(lines)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics collection summary."""
        with self.metric_lock:
            total_values = sum(len(metric.values) for metric in self.metrics.values())
            
            return {
                'collector_id': self.collector_id,
                'is_running': self.is_running,
                'total_metrics': len(self.metrics),
                'total_values': total_values,
                'retention_period': self.retention_period,
                'collection_interval': self.collection_interval,
                'metric_types': {
                    metric_type.value: sum(
                        1 for m in self.metrics.values() 
                        if m.metric_type == metric_type
                    )
                    for metric_type in MetricType
                }
            }
    
    # Convenience methods for common multiverse metrics
    def record_universe_count(self, count: int):
        """Record number of active universes."""
        self.set_gauge("multiverse.active_universes", count)
    
    def record_active_universe(self, universe_id: Optional[str]):
        """Record active universe change."""
        if universe_id:
            self.increment_counter("multiverse.universe_switches")
    
    def record_total_quantum_energy(self, energy: float):
        """Record total quantum energy."""
        self.set_gauge("multiverse.quantum_energy", energy)
    
    def record_portal_activity(self, portal_count: int):
        """Record portal activity."""
        self.set_gauge("multiverse.portal_count", portal_count)
    
    def record_timeline_branch(self):
        """Record timeline branching event."""
        self.increment_counter("multiverse.timeline_branches")
    
    def record_processing_latency(self, latency: float):
        """Record processing latency."""
        self.record_histogram("multiverse.processing_latency", latency)
    
    def record_error(self, error_type: str = "general"):
        """Record an error."""
        self.increment_counter("multiverse.error_count", tags={'type': error_type})


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(self, metrics: MultiverseMetrics, name: str, 
                 tags: Optional[Dict[str, str]] = None):
        """Initialize timer context."""
        self.metrics = metrics
        self.name = name
        self.tags = tags or {}
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and record duration."""
        if self.start_time:
            duration = time.time() - self.start_time
            self.metrics.record_timer(self.name, duration, self.tags)


class PerformanceTracker:
    """
    Performance tracking utility for multiverse operations.
    
    Provides easy-to-use decorators and context managers for tracking
    performance of multiverse functions and operations.
    """
    
    def __init__(self, metrics: MultiverseMetrics):
        """Initialize performance tracker."""
        self.metrics = metrics
    
    def track_function(self, metric_name: Optional[str] = None,
                      tags: Optional[Dict[str, str]] = None):
        """
        Decorator to track function execution time.
        
        Args:
            metric_name: Name for the metric (defaults to function name)
            tags: Additional tags
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                name = metric_name or f"function.{func.__name__}"
                with self.metrics.timer_context(name, tags):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def track_operation(self, operation_name: str,
                       tags: Optional[Dict[str, str]] = None):
        """
        Context manager to track operation performance.
        
        Args:
            operation_name: Name of the operation
            tags: Additional tags
        """
        return self.metrics.timer_context(f"operation.{operation_name}", tags)
    
    def track_multiverse_operation(self, operation_type: str,
                                  universe_id: Optional[str] = None):
        """
        Track multiverse-specific operations.
        
        Args:
            operation_type: Type of operation
            universe_id: Associated universe ID
        """
        tags = {'operation_type': operation_type}
        if universe_id:
            tags['universe_id'] = universe_id
        
        return self.metrics.timer_context("multiverse.operation", tags)