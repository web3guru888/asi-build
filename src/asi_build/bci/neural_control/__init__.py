"""
Neural Control Interface

Direct neural control of external devices and systems.
Includes cursor control, robotic control, and device switching.
"""

try:
    from .controller import NeuralController
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeuralController = None
try:
    from .cursor_control import CursorController
except (ImportError, ModuleNotFoundError, SyntaxError):
    CursorController = None
try:
    from .device_interface import DeviceControlInterface
except (ImportError, ModuleNotFoundError, SyntaxError):
    DeviceControlInterface = None
try:
    from .command_translator import CommandTranslator
except (ImportError, ModuleNotFoundError, SyntaxError):
    CommandTranslator = None

__all__ = [
    'NeuralController',
    'CursorController',
    'DeviceControlInterface',
    'CommandTranslator'
]