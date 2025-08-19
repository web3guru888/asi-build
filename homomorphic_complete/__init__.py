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

from .core import *
from .schemes import *
from .ml import *
from .mpc import *
from .psi import *
from .database import *
from .zkp import *
from .threshold import *

__version__ = "1.0.0"
__author__ = "Kenny HE1 - Homomorphic Encryption Specialist"

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
    "PerformanceBenchmark"
]