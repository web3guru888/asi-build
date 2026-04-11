"""
Stellar Engineering Module

Advanced stellar manipulation and megastructure construction.
Provides Kenny with stellar-scale engineering capabilities.
"""

from .stellar_engineer import StellarEngineer
from .dyson_sphere_constructor import DysonSphereConstructor
from .star_lifting_system import StarLiftingSystem
from .stellar_merger_controller import StellarMergerController
from .neutron_star_engineer import NeutronStarEngineer
from .supernova_trigger import SupernovaTrigger

__all__ = [
    "StellarEngineer",
    "DysonSphereConstructor",
    "StarLiftingSystem",
    "StellarMergerController", 
    "NeutronStarEngineer",
    "SupernovaTrigger"
]