"""
Secure Multi-Party Computation (MPC) framework.
"""

from .protocols import SecretSharingProtocol, BGWProtocol, GMWProtocol
from .shamir import ShamirSecretSharing
from .beaver import BeaverTriples  
from .garbled_circuits import GarbledCircuits
from .oblivious_transfer import ObliviousTransfer
from .zero_knowledge import ZKProofs
from .mpc_engine import MPCEngine, MPCParty

__all__ = [
    # Core protocols
    "SecretSharingProtocol",
    "BGWProtocol", 
    "GMWProtocol",
    
    # Secret sharing
    "ShamirSecretSharing",
    
    # Preprocessing
    "BeaverTriples",
    
    # Garbled circuits
    "GarbledCircuits",
    
    # Oblivious transfer
    "ObliviousTransfer",
    
    # Zero knowledge
    "ZKProofs",
    
    # MPC engine
    "MPCEngine",
    "MPCParty"
]