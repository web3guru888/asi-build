"""
Holographic telepresence system for remote collaboration
"""

try:
    from .telepresence_manager import TelepresenceManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    TelepresenceManager = None

__all__ = [
    'TelepresenceManager',
    'RemotePresenceManager',
    'SpatialStreamer',
    'HologramEncoder',
    'PresenceRenderer'
]