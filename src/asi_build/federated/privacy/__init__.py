"""
Privacy mechanisms for federated learning

Implementation of differential privacy, secure multi-party computation,
and other privacy-preserving techniques.
"""

try:
    from .differential_privacy import DifferentialPrivacyManager, GaussianMechanism, LaplaceMechanism
except (ImportError, ModuleNotFoundError, SyntaxError):
    DifferentialPrivacyManager = None
    GaussianMechanism = None
    LaplaceMechanism = None
try:
    from .privacy_accountant import PrivacyAccountant, RDPAccountant
except (ImportError, ModuleNotFoundError, SyntaxError):
    PrivacyAccountant = None
    RDPAccountant = None
try:
    from .noise_mechanisms import AdaptiveNoiseManager, PrivacyBudgetTracker
except (ImportError, ModuleNotFoundError, SyntaxError):
    AdaptiveNoiseManager = None
    PrivacyBudgetTracker = None
try:
    from .secure_computation import SecureComputationManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    SecureComputationManager = None
try:
    from .anonymization import DataAnonymizer, KAnonymity
except (ImportError, ModuleNotFoundError, SyntaxError):
    DataAnonymizer = None
    KAnonymity = None

__all__ = [
    "DifferentialPrivacyManager",
    "GaussianMechanism", 
    "LaplaceMechanism",
    "PrivacyAccountant",
    "RDPAccountant",
    "AdaptiveNoiseManager",
    "PrivacyBudgetTracker",
    "SecureComputationManager",
    "DataAnonymizer",
    "KAnonymity"
]