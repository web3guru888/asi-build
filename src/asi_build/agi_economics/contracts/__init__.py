"""
Smart Contract Templates
=======================

Smart contract templates for AGI services, staking, and governance.
"""

from .agi_service_contract import AGIServiceContract
from .token_contract import AGIXTokenContract
from .staking_contract import StakingContract
from .governance_contract import GovernanceContract

__all__ = [
    'AGIServiceContract',
    'AGIXTokenContract',
    'StakingContract',
    'GovernanceContract'
]