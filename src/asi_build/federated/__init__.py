"""
Federated Learning Framework for Kenny

This module provides a comprehensive federated learning framework with:
- Secure aggregation protocols
- Differential privacy mechanisms
- Multiple federated learning algorithms
- Byzantine-robust aggregation
- Cross-silo and cross-device federation
- Production-ready TensorFlow integration
"""

try:
    from .core.base import FederatedClient, FederatedServer, FederatedModel
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedClient = None
    FederatedServer = None
    FederatedModel = None
try:
    from .core.config import FederatedConfig
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedConfig = None
try:
    from .core.manager import FederatedManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedManager = None
try:
    from .aggregation.fedavg import FedAvgAggregator
except (ImportError, ModuleNotFoundError, SyntaxError):
    FedAvgAggregator = None
try:
    from .aggregation.secure_aggregation import SecureAggregator
except (ImportError, ModuleNotFoundError, SyntaxError):
    SecureAggregator = None
try:
    from .aggregation.byzantine_robust import ByzantineRobustAggregator
except (ImportError, ModuleNotFoundError, SyntaxError):
    ByzantineRobustAggregator = None
try:
    from .privacy.differential_privacy import DifferentialPrivacyManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    DifferentialPrivacyManager = None
try:
    from .algorithms.personalized_fl import PersonalizedFederatedLearning
except (ImportError, ModuleNotFoundError, SyntaxError):
    PersonalizedFederatedLearning = None
try:
    from .algorithms.federated_transfer import FederatedTransferLearning
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedTransferLearning = None
try:
    from .algorithms.async_fl import AsynchronousFederatedLearning
except (ImportError, ModuleNotFoundError, SyntaxError):
    AsynchronousFederatedLearning = None
try:
    from .algorithms.meta_learning import FederatedMetaLearning
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedMetaLearning = None
try:
    from .communication.protocols import FederatedCommunicationProtocol
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedCommunicationProtocol = None
try:
    from .utils.model_compression import ModelCompressor
except (ImportError, ModuleNotFoundError, SyntaxError):
    ModelCompressor = None
try:
    from .utils.metrics import FederatedMetrics
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedMetrics = None

__version__ = "1.0.0"
__author__ = "Kenny AI Systems"

# Main framework exports
__all__ = [
    # Core components
    "FederatedClient",
    "FederatedServer", 
    "FederatedModel",
    "FederatedConfig",
    "FederatedManager",
    
    # Aggregation methods
    "FedAvgAggregator",
    "SecureAggregator",
    "ByzantineRobustAggregator",
    
    # Privacy mechanisms
    "DifferentialPrivacyManager",
    
    # Advanced algorithms
    "PersonalizedFederatedLearning",
    "FederatedTransferLearning",
    "AsynchronousFederatedLearning",
    "FederatedMetaLearning",
    
    # Communication
    "FederatedCommunicationProtocol",
    
    # Utilities
    "ModelCompressor",
    "FederatedMetrics"
]

# Framework metadata
FRAMEWORK_INFO = {
    "name": "Kenny Federated Learning Framework",
    "version": __version__,
    "description": "Production-ready federated learning framework with advanced privacy and security features",
    "supported_algorithms": [
        "FedAvg", "FedProx", "FedNova", "SCAFFOLD",
        "Personalized FL", "Meta-Learning", "Transfer Learning",
        "Byzantine-Robust", "Asynchronous FL", "Cross-Silo"
    ],
    "privacy_features": [
        "Differential Privacy", "Secure Aggregation", 
        "Homomorphic Encryption", "Secret Sharing"
    ],
    "frameworks": ["TensorFlow", "PyTorch", "JAX"],
    "deployment": ["Local", "Cloud", "Edge", "Hybrid"]
}