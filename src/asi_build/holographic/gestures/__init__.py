"""
3D gesture recognition and spatial interaction system
"""

try:
    from .hand_tracker import HandLandmarks, HandTracker
except (ImportError, ModuleNotFoundError, SyntaxError):
    HandTracker = None
    HandLandmarks = None

__all__ = [
    "GestureRecognizer3D",
    "HandTracker",
    "HandLandmarks",
    "SpatialInteractionHandler",
    "GestureManager",
    "NeuralGestureProcessor",
]
