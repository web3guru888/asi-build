"""
Core BCI Framework Components

Provides base classes and utilities for all BCI modules.
"""

try:
    from .bci_manager import BCIManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    BCIManager = None
try:
    from .signal_processor import SignalProcessor
except (ImportError, ModuleNotFoundError, SyntaxError):
    SignalProcessor = None
try:
    from .neural_decoder import NeuralDecoder
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeuralDecoder = None
try:
    from .config import BCIConfig
except (ImportError, ModuleNotFoundError, SyntaxError):
    BCIConfig = None
try:
    from .device_interface import DeviceInterface
except (ImportError, ModuleNotFoundError, SyntaxError):
    DeviceInterface = None

__all__ = ["BCIManager", "SignalProcessor", "NeuralDecoder", "BCIConfig", "DeviceInterface"]
