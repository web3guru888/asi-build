"""
Motor Imagery BCI Module

Motor imagery classification for brain-computer interfaces.
Includes CSP, filter bank methods, and deep learning approaches.
"""

from .classifier import MotorImageryClassifier
from .csp_processor import CSPProcessor
from .feature_extractor import MotorImageryFeatureExtractor
from .training_protocol import MotorImageryTrainer

__all__ = [
    'MotorImageryClassifier',
    'CSPProcessor',
    'MotorImageryFeatureExtractor', 
    'MotorImageryTrainer'
]