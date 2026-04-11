"""
P300 Speller BCI Module

P300-based brain-computer interface for text input and communication.
Includes stimulus presentation, signal processing, and classification.
"""

try:
    from .speller import P300Speller
except (ImportError, ModuleNotFoundError, SyntaxError):
    P300Speller = None
try:
    from .stimulus_controller import StimulusController
except (ImportError, ModuleNotFoundError, SyntaxError):
    StimulusController = None
try:
    from .p300_classifier import P300Classifier
except (ImportError, ModuleNotFoundError, SyntaxError):
    P300Classifier = None
try:
    from .feature_extractor import P300FeatureExtractor
except (ImportError, ModuleNotFoundError, SyntaxError):
    P300FeatureExtractor = None

__all__ = ["P300Speller", "StimulusController", "P300Classifier", "P300FeatureExtractor"]
