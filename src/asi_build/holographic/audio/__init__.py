"""
Spatial audio system for holographic experiences
"""

try:
    from .spatial_audio_manager import SpatialAudioManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    SpatialAudioManager = None

__all__ = [
    'SpatialAudioManager',
    'HolographicAudio',
    'SpatialAudioProcessor',
    'Audio3DRenderer'
]