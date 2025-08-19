"""
Neural Prosthetic Control Module

BCI systems for controlling prosthetic devices and assistive technology.
Includes limb control, wheelchair navigation, and environmental control.
"""

from .controller import ProstheticController
from .limb_control import LimbController
from .wheelchair_controller import WheelchairController
from .environmental_control import EnvironmentalController

__all__ = [
    'ProstheticController',
    'LimbController',
    'WheelchairController',
    'EnvironmentalController'
]