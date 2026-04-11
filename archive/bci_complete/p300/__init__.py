"""
P300 Speller BCI Module

P300-based brain-computer interface for text input and communication.
Includes stimulus presentation, signal processing, and classification.
"""

from .speller import P300Speller
from .stimulus_controller import StimulusController
from .p300_classifier import P300Classifier
from .feature_extractor import P300FeatureExtractor

__all__ = [
    'P300Speller',
    'StimulusController',
    'P300Classifier',
    'P300FeatureExtractor'
]