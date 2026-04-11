"""
Motor Imagery BCI Module

Motor imagery classification for brain-computer interfaces.
Includes CSP, filter bank methods, and deep learning approaches.
"""

try:
    from .classifier import MotorImageryClassifier
except (ImportError, ModuleNotFoundError, SyntaxError):
    MotorImageryClassifier = None
try:
    from .csp_processor import CSPProcessor
except (ImportError, ModuleNotFoundError, SyntaxError):
    CSPProcessor = None
try:
    from .feature_extractor import MotorImageryFeatureExtractor
except (ImportError, ModuleNotFoundError, SyntaxError):
    MotorImageryFeatureExtractor = None
try:
    from .training_protocol import MotorImageryTrainer
except (ImportError, ModuleNotFoundError, SyntaxError):
    MotorImageryTrainer = None

__all__ = [
    'MotorImageryClassifier',
    'CSPProcessor',
    'MotorImageryFeatureExtractor', 
    'MotorImageryTrainer'
]