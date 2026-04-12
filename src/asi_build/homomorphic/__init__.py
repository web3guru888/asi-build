"""
Homomorphic Encryption Module for Kenny

A comprehensive implementation of fully homomorphic encryption (FHE) schemes
including CKKS, BFV, BGV, and advanced cryptographic protocols.

This module provides:
- Core FHE operations and utilities
- CKKS scheme for approximate arithmetic
- BFV/BGV schemes for exact arithmetic
- Encrypted machine learning
- Secure multi-party computation
- Private set intersection
- Encrypted databases
- Zero-knowledge proofs
- Threshold cryptography
"""

try:
    from .core import *
except (ImportError, ModuleNotFoundError, SyntaxError):
    pass
try:
    from .schemes import *
except (ImportError, ModuleNotFoundError, SyntaxError):
    pass
try:
    from .ml import *
except (ImportError, ModuleNotFoundError, SyntaxError):
    pass
try:
    from .mpc import *
except (ImportError, ModuleNotFoundError, SyntaxError):
    pass
try:
    from .psi import *
except (ImportError, ModuleNotFoundError, SyntaxError):
    pass
try:
    from .database import *
except (ImportError, ModuleNotFoundError, SyntaxError):
    pass
try:
    from .zkp import *
except (ImportError, ModuleNotFoundError, SyntaxError):
    pass
try:
    from .threshold import *
except (ImportError, ModuleNotFoundError, SyntaxError):
    pass

__version__ = "1.0.0"
__author__ = "Kenny HE1 - Homomorphic Encryption Specialist"
__maturity__ = "alpha"

__all__ = [
    # Core modules
    "FHECore",
    "ParameterGenerator",
    "KeyGenerator",
    "Encryptor",
    "Decryptor",
    "Evaluator",
    # Schemes
    "CKKSScheme",
    "BFVScheme",
    "BGVScheme",
    # Machine Learning
    "EncryptedNeuralNetwork",
    "EncryptedLinearRegression",
    "EncryptedLogisticRegression",
    # Multi-party Computation
    "SecureMultiPartyComputation",
    "ThresholdScheme",
    # Private Set Intersection
    "PrivateSetIntersection",
    # Database
    "EncryptedDatabase",
    # Zero-Knowledge Proofs
    "ZKProofSystem",
    # Utilities
    "HomomorphicUtils",
    "SecurityLevel",
    "PerformanceBenchmark",
]
