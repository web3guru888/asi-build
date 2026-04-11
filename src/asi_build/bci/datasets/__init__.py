"""
BCI Datasets Module

Data handling, loading, and preprocessing for BCI datasets.
Includes support for standard BCI datasets and custom data formats.
"""

try:
    from .loader import DatasetLoader
except (ImportError, ModuleNotFoundError, SyntaxError):
    DatasetLoader = None
try:
    from .preprocessor import DatasetPreprocessor
except (ImportError, ModuleNotFoundError, SyntaxError):
    DatasetPreprocessor = None
try:
    from .generator import SyntheticDataGenerator
except (ImportError, ModuleNotFoundError, SyntaxError):
    SyntheticDataGenerator = None
try:
    from .validator import DatasetValidator
except (ImportError, ModuleNotFoundError, SyntaxError):
    DatasetValidator = None

__all__ = ["DatasetLoader", "DatasetPreprocessor", "SyntheticDataGenerator", "DatasetValidator"]
