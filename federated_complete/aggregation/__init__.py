"""
Aggregation algorithms for federated learning

Implementations of various aggregation methods including FedAvg, secure aggregation,
and Byzantine-robust approaches.
"""

from .base_aggregator import BaseAggregator
from .fedavg import FedAvgAggregator
from .fedprox import FedProxAggregator
from .secure_aggregation import SecureAggregator
from .byzantine_robust import ByzantineRobustAggregator
from .scaffold import SCAFFOLDAggregator
from .fednova import FedNovaAggregator

__all__ = [
    "BaseAggregator",
    "FedAvgAggregator",
    "FedProxAggregator", 
    "SecureAggregator",
    "ByzantineRobustAggregator",
    "SCAFFOLDAggregator",
    "FedNovaAggregator"
]