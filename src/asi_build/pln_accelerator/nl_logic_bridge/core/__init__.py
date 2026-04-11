"""
Core architecture and bridge system for NL-Logic translation.
"""

try:
    from .bridge import NLLogicBridge
except (ImportError, ModuleNotFoundError, SyntaxError):
    NLLogicBridge = None
try:
    from .architecture import BridgeArchitecture
except (ImportError, ModuleNotFoundError, SyntaxError):
    BridgeArchitecture = None
try:
    from .logic_systems import LogicSystems
except (ImportError, ModuleNotFoundError, SyntaxError):
    LogicSystems = None
try:
    from .context_manager import ContextManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    ContextManager = None

__all__ = ["NLLogicBridge", "BridgeArchitecture", "LogicSystems", "ContextManager"]
