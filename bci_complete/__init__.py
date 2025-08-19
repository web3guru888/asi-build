"""
Brain-Computer Interface (BCI) Framework for Kenny

This package provides comprehensive BCI functionality including:
- EEG signal processing and analysis
- Motor imagery classification
- P300 speller systems
- SSVEP detection
- Neurofeedback training
- Brain state decoding
- Neural prosthetic control
- Thought-to-text conversion
"""

from .core.bci_manager import BCIManager
from .core.signal_processor import SignalProcessor
from .core.neural_decoder import NeuralDecoder
from .eeg.eeg_processor import EEGProcessor
from .motor_imagery.classifier import MotorImageryClassifier
from .p300.speller import P300Speller
from .ssvep.detector import SSVEPDetector
from .neurofeedback.trainer import NeurofeedbackTrainer
from .brain_state.decoder import BrainStateDecoder
from .neural_control.controller import NeuralController
from .thought_text.converter import ThoughtToTextConverter
from .prosthetic.controller import ProstheticController

__version__ = "1.0.0"
__author__ = "Kenny BCI Team"

# Export main classes
__all__ = [
    'BCIManager',
    'SignalProcessor', 
    'NeuralDecoder',
    'EEGProcessor',
    'MotorImageryClassifier',
    'P300Speller',
    'SSVEPDetector',
    'NeurofeedbackTrainer',
    'BrainStateDecoder',
    'NeuralController',
    'ThoughtToTextConverter',
    'ProstheticController'
]