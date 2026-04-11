"""
Holographic UI Framework for Kenny

A comprehensive holographic user interface system that provides:
- Volumetric display rendering
- Light field generation
- Holographic projection mapping
- 3D gesture recognition
- Interactive holograms
- AR overlays
- Telepresence capabilities
- Spatial audio integration

Author: Agent H1 - Holographic Specialist
"""

__version__ = "1.0.0"
__author__ = "Agent H1"

from .core import (
    HolographicEngine,
    HologramManager,
    SpatialRenderer,
    LightFieldProcessor
)

from .display import (
    VolumetricDisplay,
    HolographicProjector,
    DisplayCalibrator
)

from .gestures import (
    GestureRecognizer3D,
    SpatialInteractionHandler,
    HandTracker
)

from .visualization import (
    HolographicDataViz,
    VolumetricRenderer,
    InteractiveHologram
)

from .telepresence import (
    HolographicTelepresence,
    RemotePresenceManager,
    SpatialStreamer
)

from .ar_overlay import (
    ARHologramOverlay,
    MixedRealityEngine,
    SpatialAnchorSystem
)

__all__ = [
    'HolographicEngine',
    'HologramManager', 
    'SpatialRenderer',
    'LightFieldProcessor',
    'VolumetricDisplay',
    'HolographicProjector',
    'DisplayCalibrator',
    'GestureRecognizer3D',
    'SpatialInteractionHandler',
    'HandTracker',
    'HolographicDataViz',
    'VolumetricRenderer', 
    'InteractiveHologram',
    'HolographicTelepresence',
    'RemotePresenceManager',
    'SpatialStreamer',
    'ARHologramOverlay',
    'MixedRealityEngine',
    'SpatialAnchorSystem'
]