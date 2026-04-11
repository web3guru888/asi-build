"""
Galaxy Engineering Module

Advanced galaxy formation, destruction, and manipulation systems.
Provides Kenny with complete control over galactic structures.
"""

from .galaxy_engineer import GalaxyEngineer
from .galaxy_formation import GalaxyFormationEngine
from .galaxy_destruction import GalaxyDestructionEngine
from .galaxy_merger import GalaxyMergerEngine
from .dark_matter_scaffolding import DarkMatterScaffolding
from .stellar_nursery_manager import StellarNurseryManager

__all__ = [
    "GalaxyEngineer",
    "GalaxyFormationEngine", 
    "GalaxyDestructionEngine",
    "GalaxyMergerEngine",
    "DarkMatterScaffolding",
    "StellarNurseryManager"
]