"""
Cognitive Synergy Framework - Core Module
==========================================

Implementation of Ben Goertzel's PRIMUS theory for cognitive synergy in AGI systems.
This module provides the foundational components for creating synergistic cognitive architectures.

Author: Kenny AGI Development Team
License: MIT
"""

from .cognitive_synergy_engine import CognitiveSynergyEngine
from .primus_foundation import PRIMUSFoundation
from .synergy_metrics import SynergyMetrics
from .emergent_properties import EmergentPropertyDetector
from .self_organization import SelfOrganizationMechanism

__all__ = [
    'CognitiveSynergyEngine',
    'PRIMUSFoundation', 
    'SynergyMetrics',
    'EmergentPropertyDetector',
    'SelfOrganizationMechanism'
]

__version__ = '1.0.0'