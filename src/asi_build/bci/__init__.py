"""
Brain-Computer Interface (BCI) Framework

Provides comprehensive BCI functionality including:
- EEG signal processing and analysis
- Motor imagery classification (CSP + LDA)
- P300 speller systems
- SSVEP detection (CCA-based)
- Neurofeedback training
- Brain state decoding

Note: Most submodules require optional dependencies (mne, torch).
Install with: pip install asi-build[bci]

Core config is always available:
    from asi_build.bci.core.config import BCIConfig
"""

__version__ = "1.0.0"


def __getattr__(name):
    """Lazy imports — only load heavy modules when accessed."""
    _lazy_imports = {
        "BCIManager": ".core.bci_manager",
        "SignalProcessor": ".core.signal_processor",
        "NeuralDecoder": ".core.neural_decoder",
        "EEGProcessor": ".eeg.eeg_processor",
        "MotorImageryClassifier": ".motor_imagery.classifier",
        "P300Speller": ".p300.speller",
        "SSVEPDetector": ".ssvep.detector",
        "BCIConfig": ".core.config",
    }
    if name in _lazy_imports:
        import importlib

        module = importlib.import_module(_lazy_imports[name], package=__name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BCIManager",
    "SignalProcessor",
    "NeuralDecoder",
    "EEGProcessor",
    "MotorImageryClassifier",
    "P300Speller",
    "SSVEPDetector",
    "BCIConfig",
]
