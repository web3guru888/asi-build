"""
Holographic telepresence system for remote collaboration
"""

from .telepresence_manager import TelepresenceManager
from .remote_presence import RemotePresenceManager
from .spatial_streamer import SpatialStreamer
from .hologram_encoder import HologramEncoder
from .presence_renderer import PresenceRenderer

__all__ = [
    'TelepresenceManager',
    'RemotePresenceManager',
    'SpatialStreamer',
    'HologramEncoder',
    'PresenceRenderer'
]