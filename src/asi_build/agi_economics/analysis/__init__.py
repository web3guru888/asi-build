"""
Game Theory and Economic Analysis
================================

Advanced game theory analysis and Nash equilibrium calculations
for AGI economic systems.
"""

try:
    from .game_theory import GameTheoryAnalyzer
except (ImportError, ModuleNotFoundError, SyntaxError):
    GameTheoryAnalyzer = None
try:
    from .nash_equilibrium import NashEquilibriumCalculator
except (ImportError, ModuleNotFoundError, SyntaxError):
    NashEquilibriumCalculator = None
try:
    from .mechanism_design import MechanismDesignEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    MechanismDesignEngine = None

__all__ = [
    'GameTheoryAnalyzer',
    'NashEquilibriumCalculator',
    'MechanismDesignEngine'
]