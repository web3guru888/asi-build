"""
Smart Contract Templates
=======================

Smart contract templates for AGI services, staking, and governance.
"""

try:
    from .agi_service_contract import AGIServiceContract
except (ImportError, ModuleNotFoundError, SyntaxError):
    AGIServiceContract = None
try:
    from .token_contract import AGIXTokenContract
except (ImportError, ModuleNotFoundError, SyntaxError):
    AGIXTokenContract = None
try:
    from .staking_contract import StakingContract
except (ImportError, ModuleNotFoundError, SyntaxError):
    StakingContract = None
try:
    from .governance_contract import GovernanceContract
except (ImportError, ModuleNotFoundError, SyntaxError):
    GovernanceContract = None

__all__ = ["AGIServiceContract", "AGIXTokenContract", "StakingContract", "GovernanceContract"]
