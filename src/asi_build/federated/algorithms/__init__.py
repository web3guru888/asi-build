"""
Advanced federated learning algorithms

Implementation of personalized federated learning, transfer learning,
meta-learning, and other advanced algorithms.
"""

try:
    from .personalized_fl import FedPerAvg, LocalFinetuning, PersonalizedFederatedLearning
except (ImportError, ModuleNotFoundError, SyntaxError):
    PersonalizedFederatedLearning = None
    FedPerAvg = None
    LocalFinetuning = None
try:
    from .federated_transfer import FederatedTransferLearning, FedTransferManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedTransferLearning = None
    FedTransferManager = None
try:
    from .async_fl import AsyncFedAvg, AsynchronousFederatedLearning
except (ImportError, ModuleNotFoundError, SyntaxError):
    AsynchronousFederatedLearning = None
    AsyncFedAvg = None
try:
    from .meta_learning import FederatedMetaLearning, FedMAML, FedReptile
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedMetaLearning = None
    FedMAML = None
    FedReptile = None
try:
    from .cross_silo import CrossSiloFederation, SiloCoordinator
except (ImportError, ModuleNotFoundError, SyntaxError):
    CrossSiloFederation = None
    SiloCoordinator = None

__all__ = [
    "PersonalizedFederatedLearning",
    "FedPerAvg",
    "LocalFinetuning",
    "FederatedTransferLearning",
    "FedTransferManager",
    "AsynchronousFederatedLearning",
    "AsyncFedAvg",
    "FederatedMetaLearning",
    "FedMAML",
    "FedReptile",
    "CrossSiloFederation",
    "SiloCoordinator",
]
