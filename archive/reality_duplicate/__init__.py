"""
Reality Manipulation Simulation Engine

IMPORTANT DISCLAIMER:
===================
This module contains SIMULATION FRAMEWORKS ONLY. These are educational and 
theoretical implementations that model reality manipulation concepts in software.
They do NOT actually alter reality, physics, or spacetime. These are purely
computational simulations for research and educational purposes.

WARNING: These simulations are for educational, research, and entertainment 
purposes only. They cannot and do not affect actual reality.
"""

from .core import RealityEngine
from .physics import PhysicsSimulator
from .probability import ProbabilityManipulator
from .matter import MatterSimulator
from .spacetime import SpacetimeWarper
from .causal import CausalChainAnalyzer
from .simulation import SimulationHypothesisTester
from .matrix import MatrixEscapeProtocols
from .consciousness import ConsciousnessUploader
from .omnipotence import OmnipotenceFramework

__version__ = "1.0.0"
__author__ = "Kenny Reality Simulation Team"

# Safety validation
assert "SIMULATION" in __doc__, "Safety check: Must clarify these are simulations"

__all__ = [
    'RealityEngine',
    'PhysicsSimulator', 
    'ProbabilityManipulator',
    'MatterSimulator',
    'SpacetimeWarper',
    'CausalChainAnalyzer',
    'SimulationHypothesisTester',
    'MatrixEscapeProtocols',
    'ConsciousnessUploader',
    'OmnipotenceFramework'
]