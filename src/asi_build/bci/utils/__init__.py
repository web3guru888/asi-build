"""
BCI Utilities Module

Utility functions and helpers for BCI applications.
Includes signal processing utilities, visualization, and metrics.
"""

try:
    from .signal_utils import SignalUtilities
except (ImportError, ModuleNotFoundError, SyntaxError):
    SignalUtilities = None
try:
    from .visualization import BCIVisualizer
except (ImportError, ModuleNotFoundError, SyntaxError):
    BCIVisualizer = None
try:
    from .metrics import BCIMetrics
except (ImportError, ModuleNotFoundError, SyntaxError):
    BCIMetrics = None
try:
    from .validation import ValidationUtils
except (ImportError, ModuleNotFoundError, SyntaxError):
    ValidationUtils = None

__all__ = [
    'SignalUtilities',
    'BCIVisualizer',
    'BCIMetrics',
    'ValidationUtils'
]