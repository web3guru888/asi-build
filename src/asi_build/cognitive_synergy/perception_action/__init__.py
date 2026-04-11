"""
Perception ↔ Action Coupling Module
===================================

Implements sensorimotor loops and bidirectional coupling between perception
and action systems for embodied cognitive synergy.
"""

try:
    from .perception_engine import PerceptionEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    PerceptionEngine = None
try:
    from .action_engine import ActionEngine  
except (ImportError, ModuleNotFoundError, SyntaxError):
    ActionEngine = None
try:
    from .sensorimotor_synergy import SensorimotorSynergy
except (ImportError, ModuleNotFoundError, SyntaxError):
    SensorimotorSynergy = None

__all__ = ['PerceptionEngine', 'ActionEngine', 'SensorimotorSynergy']