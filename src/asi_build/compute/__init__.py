"""
Kenny AGI Compute Resource Pooling System

A comprehensive system for dynamic resource allocation across multiple providers
with advanced scheduling, monitoring, and fault tolerance capabilities.
"""

from .core.pool_manager import ComputePoolManager
from .core.resource_allocator import ResourceAllocator
from .core.job_scheduler import JobScheduler
from .monitoring.metrics_collector import MetricsCollector

try:
    from .analytics.predictor import ResourcePredictor
except ImportError:
    ResourcePredictor = None

__version__ = "1.0.0"
__author__ = "Kenny AGI Team"

__all__ = [
    "ComputePoolManager",
    "ResourceAllocator", 
    "JobScheduler",
    "MetricsCollector",
    "ResourcePredictor"
]