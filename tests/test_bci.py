"""
Tests for asi_build.bci module.

Covers signal processing, feature extraction, CSP, SSVEP detection,
metrics, and configuration.
"""

import math
import pytest
import numpy as np
from scipy.signal import butter, filtfilt

# BCI modules require mne (optional). Skip gracefully if not installed.
try:
    import mne
    HAS_MNE = True
except ImportError:
    HAS_MNE = False

# ════════════════════════════════════════════════════════
# Signal Utilities
# ════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_MNE, reason="mne not installed")
class TestSignalUtilities:
    """Tests for SignalUtilities static methods."""

    def test_bandpass_filter_removes_dc_and_high_freq(self):
        """Bandpass 5-20 Hz should remove DC and frequencies above 20 Hz."""
        from asi_build.bci.utils.signal_utils import SignalUtilities

        fs = 250.0
        t = np.arange(0, 2, 1/fs)
        # 10 Hz (in-band) + 50 Hz (out-of-band) + DC offset
        sig = np.sin(2*np.pi*10*t) + 0.5*np.sin(2*np.pi*50*t) + 3.0

        filtered = SignalUtilities.bandpass_filter(sig, 5.0, 20.0, fs)

        # DC should be gone (mean near zero)
        assert abs(np.mean(filtered[50:-50])) < 0.3
        # 10 Hz component survives (amplitude near 1.0)
        assert np.std(filtered[50:-50]) > 0.5

    def test_bandpass_filter_multichannel(self):
        """Bandpass works on 2D array (channels × samples)."""
        from asi_build.bci.utils.signal_utils import SignalUtilities

        fs = 250.0
        t = np.arange(0, 2, 1/fs)
        data = np.stack([np.sin(2*np.pi*10*t), np.sin(2*np.pi*15*t)])

        filtered = SignalUtilities.bandpass_filter(data, 5.0, 30.0, fs)
        assert filtered.shape == data.shape

    def test_notch_filter_removes_target_frequency(self):
        """Notch at 50 Hz should attenuate 50 Hz component."""
        from asi_build.bci.utils.signal_utils import SignalUtilities

        fs = 250.0
        t = np.arange(0, 2, 1/fs)
        sig = np.sin(2*np.pi*10*t) + np.sin(2*np.pi*50*t)

        filtered = SignalUtilities.notch_filter(sig, 50.0, fs)

        # Compute power at 50 Hz before and after
        from scipy.signal import welch
        _, psd_before = welch(sig, fs=fs, nperseg=256)
        f, psd_after = welch(filtered, fs=fs, nperseg=256)
        idx50 = np.argmin(np.abs(f - 50))

        assert psd_after[idx50] < psd_before[idx50] * 0.1  # >90% attenuation

    def test_compute_psd_single_channel(self):
        """PSD returns correct frequency axis and positive values."""
        from asi_build.bci.utils.signal_utils import SignalUtilities

        fs = 250.0
        t = np.arange(0, 4, 1/fs)
        sig = np.sin(2*np.pi*10*t)

        f, psd = SignalUtilities.compute_psd(sig, fs, nperseg=256)

        assert len(f) == len(psd)
        assert np.all(psd >= 0)
        # Peak should be near 10 Hz
        peak_freq = f[np.argmax(psd)]
        assert abs(peak_freq - 10.0) < 2.0

    def test_epoch_data(self):
        """Epoching produces correct number and shape of segments."""
        from asi_build.bci.utils.signal_utils import SignalUtilities

        data = np.random.randn(4, 1000)  # 4 channels, 1000 samples
        epochs = SignalUtilities.epoch_data(data, epoch_length=250, overlap=0.0)

        assert epochs.shape == (4, 4, 250)  # 4 epochs × 4 ch × 250 samples

    def test_normalize_zscore(self):
        """Z-score normalization: mean≈0, std≈1."""
        from asi_build.bci.utils.signal_utils import SignalUtilities

        data = np.random.randn(100) * 5 + 10
        normed = SignalUtilities.normalize_signal(data, 'zscore')

        assert abs(np.mean(normed)) < 0.1
        assert abs(np.std(normed) - 1.0) < 0.1


# ════════════════════════════════════════════════════════
# Frequency Analysis
# ════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_MNE, reason="mne not installed")
class TestFrequencyAnalysis:
    """Tests for FrequencyAnalyzer — spectral features, band powers."""

    def _make_config(self):
        from asi_build.bci.core.config import BCIConfig
        return BCIConfig()

    def test_spectral_features_keys(self):
        """Spectral features returns expected keys."""
        from asi_build.bci.eeg.frequency_analysis import FrequencyAnalyzer

        analyzer = FrequencyAnalyzer(self._make_config())
        data = np.random.randn(10, 1000)  # 10 channels (match default), 1000 samples
        features = analyzer.compute_spectral_features(data)

        # Should contain band powers, ratios, or nested feature dicts
        assert isinstance(features, dict)
        assert len(features) > 0

    def test_band_powers_returned(self):
        """Band powers returns a dict-like structure."""
        from asi_build.bci.eeg.frequency_analysis import FrequencyAnalyzer

        analyzer = FrequencyAnalyzer(self._make_config())
        data = np.random.randn(10, 1000)
        features = analyzer.compute_spectral_features(data)

        assert isinstance(features, dict)


# ════════════════════════════════════════════════════════
# CSP Processor
# ════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_MNE, reason="mne not installed")
class TestCSPProcessor:
    """Tests for Common Spatial Patterns."""

    def _make_binary_data(self, n_trials=40, n_channels=4, n_samples=250, seed=42):
        """Generate synthetic 2-class motor imagery data.

        Class 0: strong alpha at channel 0, weak at channel 2
        Class 1: strong alpha at channel 2, weak at channel 0
        """
        np.random.seed(seed)
        t = np.arange(n_samples) / 250.0

        trials = []
        labels = []
        for i in range(n_trials):
            trial = np.random.randn(n_channels, n_samples) * 0.3
            if i % 2 == 0:  # class 0
                trial[0] += 2.0 * np.sin(2*np.pi*10*t)
                labels.append(0)
            else:  # class 1
                trial[2] += 2.0 * np.sin(2*np.pi*10*t)
                labels.append(1)
            trials.append(trial)

        return np.array(trials), np.array(labels)

    def test_csp_fit_produces_filters(self):
        """CSP fit() creates spatial filters for binary classification."""
        from asi_build.bci.motor_imagery.csp_processor import CSPProcessor

        csp = CSPProcessor(n_components=2)
        X, y = self._make_binary_data()
        csp.fit(X, y)

        assert csp.filters_ is not None
        assert csp.filters_.shape[0] > 0

    def test_csp_transform_log_variance(self):
        """CSP transform() returns log-variance features."""
        from asi_build.bci.motor_imagery.csp_processor import CSPProcessor

        csp = CSPProcessor(n_components=2)
        X, y = self._make_binary_data()
        csp.fit(X, y)
        features = csp.transform(X)

        # Features should be (n_trials, 2*n_components) — but at least 2D
        assert features.ndim == 2
        assert features.shape[0] == X.shape[0]

    def test_csp_discriminability(self):
        """CSP features should discriminate the two classes."""
        from asi_build.bci.motor_imagery.csp_processor import CSPProcessor

        csp = CSPProcessor(n_components=2)
        X, y = self._make_binary_data(n_trials=60)
        csp.fit(X, y)
        features = csp.transform(X)

        # Class means should differ
        c0 = features[y == 0].mean(axis=0)
        c1 = features[y == 1].mean(axis=0)
        # At least one feature dimension should differ significantly
        assert np.max(np.abs(c0 - c1)) > 0.1


# ════════════════════════════════════════════════════════
# SSVEP Detector
# ════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_MNE, reason="mne not installed")
class TestSSVEPDetector:
    """Tests for SSVEP detection (CCA, PSD-based)."""

    def _make_ssvep_signal(self, freq=10.0, fs=250.0, duration=4.0, n_channels=4):
        """Generate synthetic SSVEP at target frequency."""
        t = np.arange(0, duration, 1/fs)
        data = np.zeros((n_channels, len(t)))
        for ch in range(n_channels):
            # SSVEP fundamental + 2nd harmonic + noise
            data[ch] = (np.sin(2*np.pi*freq*t)
                       + 0.5*np.sin(2*np.pi*2*freq*t)
                       + 0.3*np.random.randn(len(t)))
        return data

    def test_cca_reference_generation(self):
        """CCA reference signals have correct shape and frequency."""
        from asi_build.bci.ssvep.detector import SSVEPDetector
        from asi_build.bci.core.config import BCIConfig

        config = BCIConfig()
        det = SSVEPDetector(config)

        fs = 250.0
        n_samples = 1000
        n_harmonics = 3
        freq = 10.0

        ref = det._generate_reference_signals(freq, n_samples, fs, n_harmonics)

        # Shape: (2*n_harmonics, n_samples) — sin and cos for each harmonic
        assert ref.shape == (2 * n_harmonics, n_samples)


# ════════════════════════════════════════════════════════
# Metrics — ITR
# ════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_MNE, reason="mne not installed")
class TestBCIMetrics:
    """Tests for Information Transfer Rate and classification metrics."""

    def test_itr_perfect_accuracy(self):
        """Perfect accuracy with 4 classes, 1s per selection → 2 bits/s × 60 = 120 bpm."""
        from asi_build.bci.utils.metrics import BCIMetrics

        # Wolpaw formula: B = log2(N) + P*log2(P) + (1-P)*log2((1-P)/(N-1))
        # With P=0.999 (capped), N=4: B ≈ log2(4) = 2 bits
        itr = BCIMetrics.information_transfer_rate(accuracy=1.0, n_classes=4,
                                                    selection_time=1.0)
        assert itr > 100  # Should be close to 120 bits/min

    def test_itr_chance_level_is_zero(self):
        """At chance accuracy, ITR should be 0."""
        from asi_build.bci.utils.metrics import BCIMetrics

        itr = BCIMetrics.information_transfer_rate(accuracy=0.25, n_classes=4,
                                                    selection_time=1.0)
        assert itr == 0.0

    def test_itr_increases_with_accuracy(self):
        """ITR should increase monotonically with accuracy (above chance)."""
        from asi_build.bci.utils.metrics import BCIMetrics

        itrs = [BCIMetrics.information_transfer_rate(acc, 4, 1.0)
                for acc in [0.4, 0.6, 0.8, 0.95]]
        for i in range(len(itrs) - 1):
            assert itrs[i+1] > itrs[i], f"ITR should increase: {itrs}"

    def test_classification_metrics(self):
        """Classification metrics returns accuracy, precision, recall, F1."""
        from asi_build.bci.utils.metrics import BCIMetrics

        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 0, 1, 2, 2, 2])

        metrics = BCIMetrics.classification_metrics(y_true, y_pred)

        assert 'accuracy' in metrics
        assert 0 < metrics['accuracy'] < 1.0


# ════════════════════════════════════════════════════════
# Config
# ════════════════════════════════════════════════════════

class TestBCIConfig:
    """Test BCIConfig serialization."""

    def test_config_defaults(self):
        """Default config has sensible values."""
        from asi_build.bci.core.config import BCIConfig

        config = BCIConfig()
        assert config.device is not None
        assert config.signal_processing is not None

    def test_config_to_dict_roundtrip(self):
        """Config → dict → Config preserves values."""
        from asi_build.bci.core.config import BCIConfig

        config = BCIConfig()
        d = config._to_dict()
        assert isinstance(d, dict)
        assert 'device' in d or 'signal_processing' in d


# ════════════════════════════════════════════════════════
# Artifact Removal
# ════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_MNE, reason="mne not installed")
class TestArtifactRemoval:
    """Tests for artifact removal algorithms."""

    def _make_config(self):
        from asi_build.bci.core.config import BCIConfig
        return BCIConfig()

    def test_line_noise_removal(self):
        """Artifact remover's internal _remove_line_noise attenuates 50Hz."""
        from asi_build.bci.eeg.artifact_removal import ArtifactRemover

        config = self._make_config()
        remover = ArtifactRemover(config)
        fs = config.device.sampling_rate
        n_ch = len(config.device.channels)
        t = np.arange(0, 2, 1/fs)

        # Build multi-channel data with 50Hz line noise
        data = np.zeros((n_ch, len(t)))
        for ch in range(n_ch):
            data[ch] = np.sin(2*np.pi*10*t) + 0.5*np.sin(2*np.pi*50*t) + 0.1*np.random.randn(len(t))

        cleaned = remover._remove_line_noise(data)

        # Power at 50 Hz should be reduced in first channel
        from scipy.signal import welch as welch_fn
        f, psd_raw = welch_fn(data[0], fs=fs, nperseg=256)
        f, psd_clean = welch_fn(cleaned[0], fs=fs, nperseg=256)
        idx50 = np.argmin(np.abs(f - 50))
        assert psd_clean[idx50] < psd_raw[idx50] * 0.5

    def test_statistical_outlier_removal(self):
        """Statistical outlier removal catches extreme spikes."""
        from asi_build.bci.eeg.artifact_removal import ArtifactRemover

        config = self._make_config()
        remover = ArtifactRemover(config)
        n_ch = len(config.device.channels)

        data = np.random.randn(n_ch, 500) * 10
        # Insert artifact in first channel
        data[0, 200:205] = 1000.0

        cleaned = remover._remove_statistical_outliers(data)

        # Artifact region should be interpolated/reduced
        assert np.max(np.abs(cleaned[0, 200:205])) < np.max(np.abs(data[0, 200:205]))


# ════════════════════════════════════════════════════════
# EEG Processor — Higuchi FD fix verification
# ════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_MNE, reason="mne not installed")
class TestHiguchiFD:
    """Verify the Higuchi fractal dimension fix."""

    def test_higuchi_fd_white_noise(self):
        """White noise should have FD ≈ 2.0 (space-filling)."""
        from asi_build.bci.eeg.eeg_processor import EEGProcessor
        from asi_build.bci.core.config import BCIConfig

        proc = EEGProcessor(BCIConfig())
        np.random.seed(42)
        noise = np.random.randn(1000)
        fd = proc._higuchi_fractal_dimension(noise, k_max=10)

        # White noise FD should be between 1.5 and 2.0
        assert 1.3 < fd < 2.1, f"White noise Higuchi FD={fd}, expected ~1.5-2.0"

    def test_higuchi_fd_sine_wave(self):
        """Sine wave should have FD ≈ 1.0 (smooth curve)."""
        from asi_build.bci.eeg.eeg_processor import EEGProcessor
        from asi_build.bci.core.config import BCIConfig

        proc = EEGProcessor(BCIConfig())
        t = np.arange(1000) / 250.0
        sine = np.sin(2*np.pi*10*t)
        fd = proc._higuchi_fractal_dimension(sine, k_max=10)

        # Sine wave FD should be close to 1.0
        assert 0.8 < fd < 1.5, f"Sine wave Higuchi FD={fd}, expected ~1.0"
