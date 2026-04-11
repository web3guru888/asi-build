"""
AR holographic overlay system for mixed reality experiences
"""

try:
    from .mixed_reality_engine import MixedRealityEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    MixedRealityEngine = None

__all__ = [
    "AROverlayManager",
    "MixedRealityEngine",
    "SpatialAnchorSystem",
    "ObjectTracker",
    "OcclusionManager",
]
