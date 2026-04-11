"""
Core holographic system components
"""

try:
    from .engine import HolographicEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    HolographicEngine = None
try:
    from .light_field import LightFieldProcessor
except (ImportError, ModuleNotFoundError, SyntaxError):
    LightFieldProcessor = None
try:
    from .config import HolographicConfig
except (ImportError, ModuleNotFoundError, SyntaxError):
    HolographicConfig = None
try:
    from .base import HolographicBase
except (ImportError, ModuleNotFoundError, SyntaxError):
    HolographicBase = None
try:
    from .math_utils import SpatialMath
except (ImportError, ModuleNotFoundError, SyntaxError):
    SpatialMath = None
try:
    from .event_system import HolographicEventSystem
except (ImportError, ModuleNotFoundError, SyntaxError):
    HolographicEventSystem = None

__all__ = [
    "HolographicEngine",
    "SpatialRenderer",
    "LightFieldProcessor",
    "HolographicConfig",
    "HolographicBase",
    "SpatialMath",
    "HolographicEventSystem",
]
