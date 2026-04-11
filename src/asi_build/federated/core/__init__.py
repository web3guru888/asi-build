"""
Core federated learning components

Base classes and fundamental abstractions for federated learning.
"""

try:
    from .base import FederatedClient, FederatedModel, FederatedServer
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedClient = None
    FederatedServer = None
    FederatedModel = None
try:
    from .config import ClientConfig, FederatedConfig, ServerConfig
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedConfig = None
    ClientConfig = None
    ServerConfig = None
try:
    from .manager import FederatedManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedManager = None
try:
    from .exceptions import AggregationError, CommunicationError, FederatedLearningError
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedLearningError = None
    CommunicationError = None
    AggregationError = None

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
    "AggregationError",
]
