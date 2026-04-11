"""
Holographic physics engine for realistic hologram interactions
"""

try:
    from .physics_manager import HolographicPhysicsManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    HolographicPhysicsManager = None

__all__ = [
    "HolographicPhysicsManager",
    "HologramPhysics",
    "CollisionDetector",
    "ForceSimulator",
    "ParticleSystem",
]
