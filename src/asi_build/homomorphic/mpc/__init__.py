"""
Secure Multi-Party Computation (MPC) framework.
"""

try:
    from .protocols import BGWProtocol, GMWProtocol, SecretSharingProtocol
except (ImportError, ModuleNotFoundError, SyntaxError):
    SecretSharingProtocol = None
    BGWProtocol = None
    GMWProtocol = None
try:
    from .shamir import ShamirSecretSharing
except (ImportError, ModuleNotFoundError, SyntaxError):
    ShamirSecretSharing = None
try:
    from .beaver import BeaverTriples
except (ImportError, ModuleNotFoundError, SyntaxError):
    BeaverTriples = None
try:
    from .garbled_circuits import GarbledCircuits
except (ImportError, ModuleNotFoundError, SyntaxError):
    GarbledCircuits = None
try:
    from .oblivious_transfer import ObliviousTransfer
except (ImportError, ModuleNotFoundError, SyntaxError):
    ObliviousTransfer = None
try:
    from .zero_knowledge import ZKProofs
except (ImportError, ModuleNotFoundError, SyntaxError):
    ZKProofs = None
try:
    from .mpc_engine import MPCEngine, MPCParty
except (ImportError, ModuleNotFoundError, SyntaxError):
    MPCEngine = None
    MPCParty = None

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
    "MPCParty",
]
