"""
Brain State Decoding Module

Decoding cognitive and emotional brain states from EEG signals.
Includes attention, workload, stress, and arousal detection.
"""

try:
    from .decoder import BrainStateDecoder
except (ImportError, ModuleNotFoundError, SyntaxError):
    BrainStateDecoder = None
try:
    from .attention_monitor import AttentionMonitor
except (ImportError, ModuleNotFoundError, SyntaxError):
    AttentionMonitor = None
try:
    from .workload_estimator import WorkloadEstimator
except (ImportError, ModuleNotFoundError, SyntaxError):
    WorkloadEstimator = None
try:
    from .emotion_classifier import EmotionClassifier
except (ImportError, ModuleNotFoundError, SyntaxError):
    EmotionClassifier = None

__all__ = [
    'BrainStateDecoder',
    'AttentionMonitor',
    'WorkloadEstimator', 
    'EmotionClassifier'
]