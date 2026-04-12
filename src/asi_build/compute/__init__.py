"""
Kenny AGI Compute Resource Pooling System

A comprehensive system for dynamic resource allocation across multiple providers
with advanced scheduling, monitoring, and fault tolerance capabilities.
"""

try:
    from .core.pool_manager import ComputePoolManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    ComputePoolManager = None
try:
    from .core.resource_allocator import ResourceAllocator
except (ImportError, ModuleNotFoundError, SyntaxError):
    ResourceAllocator = None
try:
    from .core.job_scheduler import JobScheduler
except (ImportError, ModuleNotFoundError, SyntaxError):
    JobScheduler = None
try:
    from .monitoring.metrics_collector import MetricsCollector
except (ImportError, ModuleNotFoundError, SyntaxError):
    MetricsCollector = None

try:
    from .analytics.predictor import ResourcePredictor
except ImportError:
    ResourcePredictor = None

__version__ = "1.0.0"
__author__ = "Kenny AGI Team"
__maturity__ = "alpha"

__all__ = [
    "ComputePoolManager",
    "ResourceAllocator",
    "JobScheduler",
    "MetricsCollector",
    "ResourcePredictor",
]
