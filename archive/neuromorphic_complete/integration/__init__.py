"""
Integration Module for Kenny AI System

Provides seamless integration between neuromorphic computing components
and Kenny's existing AI architecture.
"""

from .kenny_integration import KennyNeuromorphicIntegration
from .data_bridge import DataBridge, KennyDataAdapter
from .event_bridge import EventBridge, KennyEventHandler  
from .memory_bridge import MemoryBridge, KennyMemoryAdapter
from .performance_bridge import PerformanceBridge, KennyPerformanceMonitor

__all__ = [
    'KennyNeuromorphicIntegration',
    'DataBridge',
    'KennyDataAdapter', 
    'EventBridge',
    'KennyEventHandler',
    'MemoryBridge',
    'KennyMemoryAdapter',
    'PerformanceBridge',
    'KennyPerformanceMonitor'
]