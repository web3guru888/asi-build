"""
Federated Learning Metrics and Performance Tracking

Comprehensive metrics collection and analysis for federated learning systems.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from collections import defaultdict, deque
import json


class FederatedMetrics:
    """Comprehensive metrics collection for federated learning."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.metrics_history = defaultdict(list)
        self.round_metrics = []
        self.client_metrics = defaultdict(lambda: defaultdict(list))
        
        # Performance tracking
        self.communication_overhead = 0
        self.computation_time = defaultdict(list)
        self.start_time = time.time()
        
        self.logger = logging.getLogger("FederatedMetrics")
    
    def record_round_metric(self, round_num: int, metric_name: str, value: float):
        """Record a metric for a specific round."""
        self.metrics_history[metric_name].append((round_num, value, time.time()))
    
    def record_client_metric(self, client_id: str, metric_name: str, value: float):
        """Record a metric for a specific client."""
        self.client_metrics[client_id][metric_name].append((time.time(), value))
    
    def record_communication_overhead(self, bytes_sent: int, bytes_received: int):
        """Record communication overhead."""
        self.communication_overhead += bytes_sent + bytes_received
    
    def record_computation_time(self, operation: str, duration: float):
        """Record computation time for different operations."""
        self.computation_time[operation].append(duration)
    
    def get_metric_summary(self, metric_name: str) -> Dict[str, Any]:
        """Get summary statistics for a metric."""
        if metric_name not in self.metrics_history:
            return {"error": "Metric not found"}
        
        values = [v for _, v, _ in self.metrics_history[metric_name]]
        
        if not values:
            return {"error": "No data available"}
        
        return {
            "count": len(values),
            "mean": np.mean(values),
            "std": np.std(values),
            "min": np.min(values),
            "max": np.max(values),
            "latest": values[-1] if values else None,
            "trend": self._calculate_trend(values)
        }
    
    def get_client_summary(self, client_id: str) -> Dict[str, Any]:
        """Get summary for a specific client."""
        if client_id not in self.client_metrics:
            return {"error": "Client not found"}
        
        summary = {}
        for metric_name, metric_data in self.client_metrics[client_id].items():
            values = [v for _, v in metric_data]
            if values:
                summary[metric_name] = {
                    "count": len(values),
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "latest": values[-1]
                }
        
        return summary
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        total_time = time.time() - self.start_time
        
        summary = {
            "total_runtime": total_time,
            "communication_overhead_bytes": self.communication_overhead,
            "computation_times": {}
        }
        
        for operation, times in self.computation_time.items():
            if times:
                summary["computation_times"][operation] = {
                    "total": sum(times),
                    "mean": np.mean(times),
                    "count": len(times)
                }
        
        return summary
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for a list of values."""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.01:
            return "increasing"
        elif slope < -0.01:
            return "decreasing"
        else:
            return "stable"
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file."""
        export_data = {
            "metrics_history": dict(self.metrics_history),
            "client_metrics": dict(self.client_metrics),
            "performance_summary": self.get_performance_summary(),
            "export_timestamp": time.time()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.info(f"Metrics exported to {filepath}")


class PerformanceTracker:
    """Real-time performance tracking for federated learning."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        
        # Rolling windows for metrics
        self.round_times = deque(maxlen=window_size)
        self.aggregation_times = deque(maxlen=window_size)
        self.communication_times = deque(maxlen=window_size)
        self.accuracy_scores = deque(maxlen=window_size)
        self.loss_values = deque(maxlen=window_size)
        
        # Throughput tracking
        self.rounds_completed = 0
        self.start_time = time.time()
        
        # Resource utilization
        self.memory_usage = deque(maxlen=window_size)
        self.cpu_usage = deque(maxlen=window_size)
        
        self.logger = logging.getLogger("PerformanceTracker")
    
    def record_round_completion(self, round_time: float, num_clients: int):
        """Record completion of a training round."""
        self.round_times.append(round_time)
        self.rounds_completed += 1
        
        # Calculate throughput
        total_time = time.time() - self.start_time
        throughput = self.rounds_completed / total_time if total_time > 0 else 0
        
        self.logger.debug(f"Round completed in {round_time:.2f}s, throughput: {throughput:.2f} rounds/s")
    
    def record_aggregation_time(self, duration: float):
        """Record aggregation operation time."""
        self.aggregation_times.append(duration)
    
    def record_communication_time(self, duration: float):
        """Record communication operation time."""
        self.communication_times.append(duration)
    
    def record_model_performance(self, accuracy: float, loss: float):
        """Record model performance metrics."""
        self.accuracy_scores.append(accuracy)
        self.loss_values.append(loss)
    
    def record_resource_usage(self, memory_mb: float, cpu_percent: float):
        """Record resource usage."""
        self.memory_usage.append(memory_mb)
        self.cpu_usage.append(cpu_percent)
    
    def get_current_performance(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        total_time = time.time() - self.start_time
        throughput = self.rounds_completed / total_time if total_time > 0 else 0
        
        performance = {
            "throughput_rounds_per_second": throughput,
            "rounds_completed": self.rounds_completed,
            "total_runtime": total_time
        }
        
        # Add rolling averages
        if self.round_times:
            performance["avg_round_time"] = np.mean(self.round_times)
            performance["round_time_std"] = np.std(self.round_times)
        
        if self.aggregation_times:
            performance["avg_aggregation_time"] = np.mean(self.aggregation_times)
        
        if self.communication_times:
            performance["avg_communication_time"] = np.mean(self.communication_times)
        
        if self.accuracy_scores:
            performance["latest_accuracy"] = self.accuracy_scores[-1]
            performance["avg_accuracy"] = np.mean(self.accuracy_scores)
        
        if self.loss_values:
            performance["latest_loss"] = self.loss_values[-1]
            performance["avg_loss"] = np.mean(self.loss_values)
        
        if self.memory_usage:
            performance["avg_memory_usage_mb"] = np.mean(self.memory_usage)
            performance["peak_memory_usage_mb"] = np.max(self.memory_usage)
        
        if self.cpu_usage:
            performance["avg_cpu_usage_percent"] = np.mean(self.cpu_usage)
            performance["peak_cpu_usage_percent"] = np.max(self.cpu_usage)
        
        return performance
    
    def get_efficiency_metrics(self) -> Dict[str, Any]:
        """Calculate efficiency metrics."""
        metrics = {}
        
        if self.round_times and self.aggregation_times:
            # Aggregation efficiency
            total_round_time = sum(self.round_times)
            total_aggregation_time = sum(self.aggregation_times)
            aggregation_efficiency = total_aggregation_time / total_round_time if total_round_time > 0 else 0
            metrics["aggregation_efficiency"] = aggregation_efficiency
        
        if self.round_times and self.communication_times:
            # Communication efficiency
            total_round_time = sum(self.round_times)
            total_communication_time = sum(self.communication_times)
            communication_efficiency = total_communication_time / total_round_time if total_round_time > 0 else 0
            metrics["communication_efficiency"] = communication_efficiency
        
        # Convergence rate
        if len(self.loss_values) >= 2:
            initial_loss = self.loss_values[0]
            latest_loss = self.loss_values[-1]
            improvement = (initial_loss - latest_loss) / initial_loss if initial_loss != 0 else 0
            metrics["loss_improvement_rate"] = improvement
        
        return metrics
    
    def detect_performance_issues(self) -> List[Dict[str, Any]]:
        """Detect potential performance issues."""
        issues = []
        
        # Check for increasing round times
        if len(self.round_times) >= 10:
            recent_times = list(self.round_times)[-5:]
            early_times = list(self.round_times)[:5]
            
            if np.mean(recent_times) > np.mean(early_times) * 1.5:
                issues.append({
                    "type": "increasing_round_times",
                    "severity": "warning",
                    "description": "Round times are increasing significantly"
                })
        
        # Check for stagnant accuracy
        if len(self.accuracy_scores) >= 10:
            recent_accuracy = list(self.accuracy_scores)[-5:]
            if np.std(recent_accuracy) < 0.001:  # Very low variance
                issues.append({
                    "type": "stagnant_accuracy",
                    "severity": "info",
                    "description": "Model accuracy has plateaued"
                })
        
        # Check for high resource usage
        if self.memory_usage and np.mean(self.memory_usage) > 8000:  # 8GB
            issues.append({
                "type": "high_memory_usage",
                "severity": "warning",
                "description": "High memory usage detected"
            })
        
        if self.cpu_usage and np.mean(self.cpu_usage) > 90:
            issues.append({
                "type": "high_cpu_usage",
                "severity": "warning",
                "description": "High CPU usage detected"
            })
        
        return issues


class ConvergenceTracker:
    """Track convergence metrics for federated learning."""
    
    def __init__(self, patience: int = 10, threshold: float = 0.001):
        self.patience = patience
        self.threshold = threshold
        
        self.loss_history = []
        self.accuracy_history = []
        self.best_loss = float('inf')
        self.best_accuracy = 0.0
        self.rounds_without_improvement = 0
        
        self.logger = logging.getLogger("ConvergenceTracker")
    
    def update(self, loss: float, accuracy: float) -> Dict[str, Any]:
        """Update convergence tracking."""
        self.loss_history.append(loss)
        self.accuracy_history.append(accuracy)
        
        improved = False
        
        # Check for improvement
        if loss < self.best_loss - self.threshold:
            self.best_loss = loss
            self.rounds_without_improvement = 0
            improved = True
        elif accuracy > self.best_accuracy + self.threshold:
            self.best_accuracy = accuracy
            self.rounds_without_improvement = 0
            improved = True
        else:
            self.rounds_without_improvement += 1
        
        # Check convergence
        converged = self.rounds_without_improvement >= self.patience
        
        return {
            "converged": converged,
            "improved": improved,
            "rounds_without_improvement": self.rounds_without_improvement,
            "best_loss": self.best_loss,
            "best_accuracy": self.best_accuracy,
            "current_loss": loss,
            "current_accuracy": accuracy
        }
    
    def get_convergence_analysis(self) -> Dict[str, Any]:
        """Get detailed convergence analysis."""
        if not self.loss_history:
            return {"error": "No data available"}
        
        analysis = {
            "total_rounds": len(self.loss_history),
            "converged": self.rounds_without_improvement >= self.patience,
            "patience": self.patience,
            "threshold": self.threshold
        }
        
        # Loss analysis
        if self.loss_history:
            analysis["loss_analysis"] = {
                "initial": self.loss_history[0],
                "final": self.loss_history[-1],
                "best": self.best_loss,
                "improvement": (self.loss_history[0] - self.loss_history[-1]) / self.loss_history[0]
            }
        
        # Accuracy analysis
        if self.accuracy_history:
            analysis["accuracy_analysis"] = {
                "initial": self.accuracy_history[0],
                "final": self.accuracy_history[-1],
                "best": self.best_accuracy,
                "improvement": self.accuracy_history[-1] - self.accuracy_history[0]
            }
        
        return analysis