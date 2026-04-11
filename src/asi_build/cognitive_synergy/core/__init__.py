"""
Cognitive Synergy Framework - Core Module
==========================================

Implementation of Ben Goertzel's PRIMUS theory for cognitive synergy in AGI systems.
This module provides the foundational components for creating synergistic cognitive architectures.

Author: Kenny AGI Development Team
License: MIT
"""

try:
    from .cognitive_synergy_engine import CognitiveSynergyEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    CognitiveSynergyEngine = None
try:
    from .primus_foundation import PRIMUSFoundation
except (ImportError, ModuleNotFoundError, SyntaxError):
    PRIMUSFoundation = None
try:
    from .synergy_metrics import SynergyMetrics
except (ImportError, ModuleNotFoundError, SyntaxError):
    SynergyMetrics = None
try:
    from .emergent_properties import EmergentPropertyDetector
except (ImportError, ModuleNotFoundError, SyntaxError):
    EmergentPropertyDetector = None
try:
    from .self_organization import SelfOrganizationMechanism
except (ImportError, ModuleNotFoundError, SyntaxError):
    SelfOrganizationMechanism = None

__all__ = [
    'CognitiveSynergyEngine',
    'PRIMUSFoundation', 
    'SynergyMetrics',
    'EmergentPropertyDetector',
    'SelfOrganizationMechanism'
]

__version__ = '1.0.0'