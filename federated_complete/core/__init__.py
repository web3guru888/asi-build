"""
Core federated learning components

Base classes and fundamental abstractions for federated learning.
"""

from .base import FederatedClient, FederatedServer, FederatedModel
from .config import FederatedConfig, ClientConfig, ServerConfig
from .manager import FederatedManager
from .exceptions import FederatedLearningError, CommunicationError, AggregationError

__all__ = [
    "FederatedClient",
    "FederatedServer", 
    "FederatedModel",
    "FederatedConfig",
    "ClientConfig",
    "ServerConfig",
    "FederatedManager",
    "FederatedLearningError",
    "CommunicationError",
    "AggregationError"
]