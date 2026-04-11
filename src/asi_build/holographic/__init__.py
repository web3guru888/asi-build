"""
Holographic UI Framework

Provides holographic user interface capabilities including:
- Spatial mathematics and 3D transformations
- Light field processing
- Volumetric display rendering
- Gesture recognition

Note: Some submodules require optional dependencies (cv2, torch).
"""

__version__ = "1.0.0"


def __getattr__(name):
    """Lazy imports — avoid cascading import errors from missing optional deps."""
    _lazy = {
        "HolographicEngine": ".core.engine",
        "LightFieldProcessor": ".core.light_field",
        "HolographicConfig": ".core.config",
        "HolographicBase": ".core.base",
        "SpatialMath": ".core.math_utils",
        "HolographicEventSystem": ".core.event_system",
        "VolumetricDisplay": ".display.volumetric_display",
    }
    if name in _lazy:
        import importlib

        mod = importlib.import_module(_lazy[name], package=__name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(
    {
        "HolographicEngine",
        "LightFieldProcessor",
        "HolographicConfig",
        "HolographicBase",
        "SpatialMath",
        "HolographicEventSystem",
        "VolumetricDisplay",
    }
)
