"""
Holographic display systems
"""

try:
    from .volumetric_display import VolumetricDisplay, VolumetricDisplayManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    VolumetricDisplay = None
    VolumetricDisplayManager = None

__all__ = [
    'VolumetricDisplay',
    'VolumetricDisplayManager', 
    'HolographicProjector',
    'DisplayCalibrator',
    'LightFieldDisplay',
    'DisplayRenderer'
]