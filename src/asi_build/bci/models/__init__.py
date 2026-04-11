"""
BCI Models Module

Machine learning models and neural networks for BCI applications.
Includes deep learning, traditional ML, and ensemble methods.
"""

try:
    from .deep_learning import DeepLearningModels
except (ImportError, ModuleNotFoundError, SyntaxError):
    DeepLearningModels = None
try:
    from .traditional_ml import TraditionalMLModels
except (ImportError, ModuleNotFoundError, SyntaxError):
    TraditionalMLModels = None
try:
    from .ensemble import EnsembleModels
except (ImportError, ModuleNotFoundError, SyntaxError):
    EnsembleModels = None
try:
    from .model_selector import ModelSelector
except (ImportError, ModuleNotFoundError, SyntaxError):
    ModelSelector = None

__all__ = [
    'DeepLearningModels',
    'TraditionalMLModels',
    'EnsembleModels',
    'ModelSelector'
]