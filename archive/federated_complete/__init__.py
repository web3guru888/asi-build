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

from .core.base import FederatedClient, FederatedServer, FederatedModel
from .core.config import FederatedConfig
from .core.manager import FederatedManager
from .aggregation.fedavg import FedAvgAggregator
from .aggregation.secure_aggregation import SecureAggregator
from .aggregation.byzantine_robust import ByzantineRobustAggregator
from .privacy.differential_privacy import DifferentialPrivacyManager
from .algorithms.personalized_fl import PersonalizedFederatedLearning
from .algorithms.federated_transfer import FederatedTransferLearning
from .algorithms.async_fl import AsynchronousFederatedLearning
from .algorithms.meta_learning import FederatedMetaLearning
from .communication.protocols import FederatedCommunicationProtocol
from .utils.model_compression import ModelCompressor
from .utils.metrics import FederatedMetrics

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