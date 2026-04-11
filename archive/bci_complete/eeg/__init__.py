"""
EEG Processing Module

Advanced EEG signal processing and analysis for BCI applications.
"""

from .eeg_processor import EEGProcessor
from .artifact_removal import ArtifactRemover
from .frequency_analysis import FrequencyAnalyzer
from .spatial_filters import SpatialFilterBank

__all__ = [
    'EEGProcessor',
    'ArtifactRemover', 
    'FrequencyAnalyzer',
    'SpatialFilterBank'
]