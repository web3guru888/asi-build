"""
Core federated learning components

Base classes and fundamental abstractions for federated learning.
"""

try:
    from .base import FederatedClient, FederatedServer, FederatedModel
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedClient = None
    FederatedServer = None
    FederatedModel = None
try:
    from .config import FederatedConfig, ClientConfig, ServerConfig
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedConfig = None
    ClientConfig = None
    ServerConfig = None
try:
    from .manager import FederatedManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedManager = None
try:
    from .exceptions import FederatedLearningError, CommunicationError, AggregationError
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
    "AggregationError"
]