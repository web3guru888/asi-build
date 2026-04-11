"""
Aggregation algorithms for federated learning

Implementations of various aggregation methods including FedAvg, secure aggregation,
and Byzantine-robust approaches.
"""

try:
    from .base_aggregator import BaseAggregator
except (ImportError, ModuleNotFoundError, SyntaxError):
    BaseAggregator = None
try:
    from .fedavg import FedAvgAggregator
except (ImportError, ModuleNotFoundError, SyntaxError):
    FedAvgAggregator = None
try:
    from .fedprox import FedProxAggregator
except (ImportError, ModuleNotFoundError, SyntaxError):
    FedProxAggregator = None
try:
    from .secure_aggregation import SecureAggregator
except (ImportError, ModuleNotFoundError, SyntaxError):
    SecureAggregator = None
try:
    from .byzantine_robust import ByzantineRobustAggregator
except (ImportError, ModuleNotFoundError, SyntaxError):
    ByzantineRobustAggregator = None
try:
    from .scaffold import SCAFFOLDAggregator
except (ImportError, ModuleNotFoundError, SyntaxError):
    SCAFFOLDAggregator = None
try:
    from .fednova import FedNovaAggregator
except (ImportError, ModuleNotFoundError, SyntaxError):
    FedNovaAggregator = None

__all__ = [
    "BaseAggregator",
    "FedAvgAggregator",
    "FedProxAggregator", 
    "SecureAggregator",
    "ByzantineRobustAggregator",
    "SCAFFOLDAggregator",
    "FedNovaAggregator"
]