"""
Core AGI Economics Platform Components
=====================================

Core infrastructure and base classes for the AGI Economics platform.
"""

try:
    from .base_engine import BaseEconomicEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    BaseEconomicEngine = None
try:
    from .config import EconomicConfig
except (ImportError, ModuleNotFoundError, SyntaxError):
    EconomicConfig = None
try:
    from .exceptions import AGIEconomicsError
except (ImportError, ModuleNotFoundError, SyntaxError):
    AGIEconomicsError = None
try:
    from .types import *
except (ImportError, ModuleNotFoundError, SyntaxError):
    pass

__all__ = [
    "BaseEconomicEngine",
    "EconomicConfig",
    "AGIEconomicsError",
    "TokenType",
    "ResourceType",
    "AgentType",
]
