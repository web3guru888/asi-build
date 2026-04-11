"""
SSVEP BCI Module

Steady-State Visual Evoked Potential (SSVEP) based brain-computer interface.
Includes frequency detection, stimulus generation, and multi-target classification.
"""

try:
    from .detector import SSVEPDetector
except (ImportError, ModuleNotFoundError, SyntaxError):
    SSVEPDetector = None
try:
    from .frequency_analyzer import SSVEPFrequencyAnalyzer
except (ImportError, ModuleNotFoundError, SyntaxError):
    SSVEPFrequencyAnalyzer = None
try:
    from .stimulus_generator import SSVEPStimulusGenerator
except (ImportError, ModuleNotFoundError, SyntaxError):
    SSVEPStimulusGenerator = None
try:
    from .classifier import SSVEPClassifier
except (ImportError, ModuleNotFoundError, SyntaxError):
    SSVEPClassifier = None

__all__ = ["SSVEPDetector", "SSVEPFrequencyAnalyzer", "SSVEPStimulusGenerator", "SSVEPClassifier"]
