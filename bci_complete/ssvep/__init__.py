"""
SSVEP BCI Module

Steady-State Visual Evoked Potential (SSVEP) based brain-computer interface.
Includes frequency detection, stimulus generation, and multi-target classification.
"""

from .detector import SSVEPDetector
from .frequency_analyzer import SSVEPFrequencyAnalyzer
from .stimulus_generator import SSVEPStimulusGenerator
from .classifier import SSVEPClassifier

__all__ = [
    'SSVEPDetector',
    'SSVEPFrequencyAnalyzer',
    'SSVEPStimulusGenerator', 
    'SSVEPClassifier'
]