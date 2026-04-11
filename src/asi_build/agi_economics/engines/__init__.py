"""
Economic Engines
===============

Core economic engines for the AGI Economics platform.
"""

try:
    from .token_economics import TokenEconomicsEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    TokenEconomicsEngine = None
try:
    from .bonding_curves import BondingCurveEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    BondingCurveEngine = None
try:
    from .liquidity_pools import LiquidityPoolEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    LiquidityPoolEngine = None

__all__ = ["TokenEconomicsEngine", "BondingCurveEngine", "LiquidityPoolEngine"]
