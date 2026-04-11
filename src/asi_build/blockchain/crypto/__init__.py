"""
Cryptographic Module for Kenny AGI Blockchain Audit Trail

This module provides comprehensive cryptographic functionality including
digital signatures, encryption, hashing, and key management for secure
audit trail operations.
"""

try:
    from .signature_manager import KeyPair, SignatureManager, SignatureVerifier
except (ImportError, ModuleNotFoundError, SyntaxError):
    SignatureManager = None
    SignatureVerifier = None
    KeyPair = None
try:
    from .encryption_manager import AsymmetricKeyPair, EncryptionManager, SymmetricKey
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptionManager = None
    SymmetricKey = None
    AsymmetricKeyPair = None
try:
    from .hash_manager import HashChain, HashManager, MerkleTree
except (ImportError, ModuleNotFoundError, SyntaxError):
    HashManager = None
    MerkleTree = None
    HashChain = None
try:
    from .key_manager import KeyManager, KeyStore
except (ImportError, ModuleNotFoundError, SyntaxError):
    KeyManager = None
    KeyStore = None
try:
    from .zero_knowledge import ZKProof, ZKProofSystem
except (ImportError, ModuleNotFoundError, SyntaxError):
    ZKProofSystem = None
    ZKProof = None

__all__ = [
    "SignatureManager",
    "SignatureVerifier",
    "KeyPair",
    "EncryptionManager",
    "SymmetricKey",
    "AsymmetricKeyPair",
    "HashManager",
    "MerkleTree",
    "HashChain",
    "KeyManager",
    "KeyStore",
    "ZKProofSystem",
    "ZKProof",
]
