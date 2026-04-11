"""
Utility modules for federated learning

Helper functions, model compression, metrics, and other utilities.
"""

try:
    from .model_compression import ModelCompressor, QuantizationCompressor, PruningCompressor
except (ImportError, ModuleNotFoundError, SyntaxError):
    ModelCompressor = None
    QuantizationCompressor = None
    PruningCompressor = None
try:
    from .metrics import FederatedMetrics, PerformanceTracker
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedMetrics = None
    PerformanceTracker = None
try:
    from .data_utils import DataPartitioner, IIDPartitioner, NonIIDPartitioner
except (ImportError, ModuleNotFoundError, SyntaxError):
    DataPartitioner = None
    IIDPartitioner = None
    NonIIDPartitioner = None
try:
    from .visualization import FederatedVisualizer
except (ImportError, ModuleNotFoundError, SyntaxError):
    FederatedVisualizer = None

__all__ = [
    "ModelCompressor",
    "QuantizationCompressor", 
    "PruningCompressor",
    "FederatedMetrics",
    "PerformanceTracker",
    "DataPartitioner",
    "IIDPartitioner",
    "NonIIDPartitioner",
    "FederatedVisualizer"
]