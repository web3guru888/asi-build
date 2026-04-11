"""
Neural Prosthetic Control Module

BCI systems for controlling prosthetic devices and assistive technology.
Includes limb control, wheelchair navigation, and environmental control.
"""

try:
    from .controller import ProstheticController
except (ImportError, ModuleNotFoundError, SyntaxError):
    ProstheticController = None
try:
    from .limb_control import LimbController
except (ImportError, ModuleNotFoundError, SyntaxError):
    LimbController = None
try:
    from .wheelchair_controller import WheelchairController
except (ImportError, ModuleNotFoundError, SyntaxError):
    WheelchairController = None
try:
    from .environmental_control import EnvironmentalController
except (ImportError, ModuleNotFoundError, SyntaxError):
    EnvironmentalController = None

__all__ = [
    "ProstheticController",
    "LimbController",
    "WheelchairController",
    "EnvironmentalController",
]
