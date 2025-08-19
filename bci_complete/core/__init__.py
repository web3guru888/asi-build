"""
Core BCI Framework Components

Provides base classes and utilities for all BCI modules.
"""

from .bci_manager import BCIManager
from .signal_processor import SignalProcessor
from .neural_decoder import NeuralDecoder
from .config import BCIConfig
from .device_interface import DeviceInterface

__all__ = [
    'BCIManager',
    'SignalProcessor',
    'NeuralDecoder', 
    'BCIConfig',
    'DeviceInterface'
]