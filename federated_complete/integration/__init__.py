"""
Integration with Kenny's Existing Systems

Connects the federated learning framework with Kenny's existing
infrastructure and capabilities.
"""

from .kenny_integration import KennyFederatedIntegration
from .data_integration import KennyDataAdapter
from .model_integration import KennyModelAdapter

__all__ = [
    "KennyFederatedIntegration",
    "KennyDataAdapter", 
    "KennyModelAdapter"
]