"""
Neural Control Interface

Direct neural control of external devices and systems.
Includes cursor control, robotic control, and device switching.
"""

from .controller import NeuralController
from .cursor_control import CursorController
from .device_interface import DeviceControlInterface
from .command_translator import CommandTranslator

__all__ = [
    'NeuralController',
    'CursorController',
    'DeviceControlInterface',
    'CommandTranslator'
]