"""
Homeostatic Regulation Module

Implements biological homeostasis and allostasis mechanisms for maintaining
system stability while enabling adaptive responses to environmental changes.
"""

try:
    from .homeostatic_regulator import HomeostaticRegulator, HomeostaticVariable
except (ImportError, ModuleNotFoundError, SyntaxError):
    HomeostaticRegulator = None
    HomeostaticVariable = None
try:
    from .allostasis_controller import AllostasisController, AllostaticState
except (ImportError, ModuleNotFoundError, SyntaxError):
    AllostasisController = None
    AllostaticState = None
try:
    from .stress_response import StressLevel, StressResponseSystem
except (ImportError, ModuleNotFoundError, SyntaxError):
    StressResponseSystem = None
    StressLevel = None
try:
    from .energy_balance import EnergyBalanceManager, MetabolicState
except (ImportError, ModuleNotFoundError, SyntaxError):
    EnergyBalanceManager = None
    MetabolicState = None

__all__ = [
    "HomeostaticRegulator",
    "HomeostaticVariable",
    "AllostasisController",
    "AllostaticState",
    "StressResponseSystem",
    "StressLevel",
    "EnergyBalanceManager",
    "MetabolicState",
]
