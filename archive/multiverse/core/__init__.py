"""
Multiverse Core Framework
========================

Core components for multiverse management, quantum state handling,
and fundamental dimensional operations.
"""

from .multiverse_manager import MultiverseManager
from .quantum_state import QuantumState, QuantumStateVector
from .reality_anchor import RealityAnchor, RealityStabilizer
from .dimensional_coordinate import DimensionalCoordinate, DimensionalSpace
from .base_multiverse import BaseMultiverseComponent
from .config_manager import MultiverseConfig, UniverseConfig
from .event_system import MultiverseEventBus, MultiverseEvent
from .metrics_collector import MultiverseMetrics, PerformanceTracker

__all__ = [
    'MultiverseManager',
    'QuantumState', 'QuantumStateVector',
    'RealityAnchor', 'RealityStabilizer',
    'DimensionalCoordinate', 'DimensionalSpace',
    'BaseMultiverseComponent',
    'MultiverseConfig', 'UniverseConfig',
    'MultiverseEventBus', 'MultiverseEvent',
    'MultiverseMetrics', 'PerformanceTracker'
]