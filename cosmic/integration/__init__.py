"""
Kenny Integration Module

Integrates cosmic engineering with Kenny's existing systems.
"""

from .kenny_cosmic_interface import KennyCosmicInterface
from .automation_bridge import CosmicAutomationBridge
from .ai_coordinator import CosmicAICoordinator

__all__ = [
    "KennyCosmicInterface",
    "CosmicAutomationBridge",
    "CosmicAICoordinator"
]