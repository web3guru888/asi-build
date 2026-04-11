"""
Core architecture and bridge system for NL-Logic translation.
"""

from .bridge import NLLogicBridge
from .architecture import BridgeArchitecture
from .logic_systems import LogicSystems
from .context_manager import ContextManager

__all__ = ["NLLogicBridge", "BridgeArchitecture", "LogicSystems", "ContextManager"]