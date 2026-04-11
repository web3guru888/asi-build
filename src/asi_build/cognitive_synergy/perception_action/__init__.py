"""
Perception ↔ Action Coupling Module
===================================

Implements sensorimotor loops and bidirectional coupling between perception
and action systems for embodied cognitive synergy.
"""

from .perception_engine import PerceptionEngine
from .action_engine import ActionEngine  
from .sensorimotor_synergy import SensorimotorSynergy

__all__ = ['PerceptionEngine', 'ActionEngine', 'SensorimotorSynergy']