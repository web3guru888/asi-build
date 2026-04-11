"""
EEG Processing Module

Advanced EEG signal processing and analysis for BCI applications.
Requires: mne, scipy, numpy
"""

# Lazy imports — mne is heavy and optional
def __getattr__(name):
    _lazy = {
        'EEGProcessor': '.eeg_processor',
        'ArtifactRemover': '.artifact_removal',
        'FrequencyAnalyzer': '.frequency_analysis',
        'SpatialFilterBank': '.spatial_filters',
    }
    if name in _lazy:
        import importlib
        mod = importlib.import_module(_lazy[name], package=__name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['EEGProcessor', 'ArtifactRemover', 'FrequencyAnalyzer', 'SpatialFilterBank']
