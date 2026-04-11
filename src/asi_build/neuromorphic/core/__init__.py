"""
Core neuromorphic computing components and configurations.
"""

try:
    from .config import NeuromorphicConfig
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeuromorphicConfig = None
try:
    from .manager import NeuromorphicManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeuromorphicManager = None
try:
    from .event_processor import EventProcessor
except (ImportError, ModuleNotFoundError, SyntaxError):
    EventProcessor = None
try:
    from .temporal_dynamics import TemporalDynamics
except (ImportError, ModuleNotFoundError, SyntaxError):
    TemporalDynamics = None
try:
    from .neural_base import NeuralBase
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeuralBase = None
try:
    from .spike_monitor import SpikeMonitor
except (ImportError, ModuleNotFoundError, SyntaxError):
    SpikeMonitor = None

__all__ = [
    "NeuromorphicConfig",
    "NeuromorphicManager",
    "EventProcessor",
    "TemporalDynamics",
    "NeuralBase",
    "SpikeMonitor",
]
