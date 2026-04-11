"""
BCI Signal Processor - Real-time neural signal processing

Handles filtering, artifact removal, and feature extraction for BCI signals.
"""

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import signal, stats
from scipy.signal import butter, filtfilt, iirnotch, welch
from sklearn.decomposition import FastICA

from .config import BCIConfig


@dataclass
class ProcessedSignal:
    """Container for processed signal data"""

    data: np.ndarray
    sampling_rate: float
    channels: List[str]
    timestamp: float
    features: Dict[str, Any]
    artifacts_removed: bool = False
    quality_score: float = 1.0


class SignalProcessor:
    """
    Real-time neural signal processing engine

    Features:
    - Multi-stage filtering (bandpass, notch, adaptive)
    - Artifact removal (ICA, EOG, EMG)
    - Feature extraction (spectral, temporal, spatial)
    - Real-time processing pipeline
    - Quality assessment
    """

    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Processing parameters
        self.sampling_rate = config.device.sampling_rate
        self.channels = config.device.channels
        self.num_channels = len(self.channels)

        # Filter design
        self._design_filters()

        # Artifact removal
        self.ica_model = None
        self.artifact_templates = {}

        # Real-time buffers
        self.signal_buffer = np.zeros(
            (self.num_channels, int(self.sampling_rate * 5))
        )  # 5 sec buffer
        self.buffer_index = 0
        self.buffer_lock = threading.Lock()

        # Feature extraction
        self.feature_extractors = self._initialize_feature_extractors()

        # Quality assessment
        self.quality_metrics = {}

        self.logger.info("Signal Processor initialized")

    def _design_filters(self):
        """Design signal processing filters"""
        # Bandpass filter
        nyquist = self.sampling_rate / 2
        low = self.config.signal_processing.bandpass_low / nyquist
        high = self.config.signal_processing.bandpass_high / nyquist

        self.bandpass_b, self.bandpass_a = butter(4, [low, high], btype="band")

        # Notch filter for power line interference
        notch_freq = self.config.signal_processing.notch_freq
        self.notch_b, self.notch_a = iirnotch(notch_freq, 30, self.sampling_rate)

        # Adaptive filter coefficients
        self.adaptive_filters = {}

        self.logger.info("Filters designed successfully")

    def _initialize_feature_extractors(self) -> Dict[str, Any]:
        """Initialize feature extraction methods"""
        extractors = {}

        if self.config.signal_processing.enable_spectral_features:
            extractors["spectral"] = SpectralFeatureExtractor(self.config)

        if self.config.signal_processing.enable_temporal_features:
            extractors["temporal"] = TemporalFeatureExtractor(self.config)

        if self.config.signal_processing.enable_spatial_features:
            extractors["spatial"] = SpatialFeatureExtractor(self.config)

        return extractors

    def process_realtime(self, raw_data: np.ndarray) -> ProcessedSignal:
        """Process incoming real-time data"""
        try:
            # Validate input
            if raw_data.shape[0] != self.num_channels:
                raise ValueError(f"Expected {self.num_channels} channels, got {raw_data.shape[0]}")

            # Update buffer
            self._update_buffer(raw_data)

            # Apply filtering
            filtered_data = self._apply_filters(raw_data)

            # Remove artifacts
            clean_data, artifacts_removed = self._remove_artifacts(filtered_data)

            # Extract features
            features = self._extract_features(clean_data)

            # Assess quality
            quality_score = self._assess_quality(clean_data)

            # Create processed signal object
            processed = ProcessedSignal(
                data=clean_data,
                sampling_rate=self.sampling_rate,
                channels=self.channels,
                timestamp=np.datetime64("now").astype(float),
                features=features,
                artifacts_removed=artifacts_removed,
                quality_score=quality_score,
            )

            return processed

        except Exception as e:
            self.logger.error(f"Real-time processing error: {e}")
            raise

    def _update_buffer(self, new_data: np.ndarray):
        """Update circular buffer with new data"""
        with self.buffer_lock:
            n_samples = new_data.shape[1]

            # Shift buffer if needed
            if self.buffer_index + n_samples > self.signal_buffer.shape[1]:
                shift = self.buffer_index + n_samples - self.signal_buffer.shape[1]
                self.signal_buffer[:, :-shift] = self.signal_buffer[:, shift:]
                self.buffer_index -= shift

            # Add new data
            self.signal_buffer[:, self.buffer_index : self.buffer_index + n_samples] = new_data
            self.buffer_index += n_samples

    def _apply_filters(self, data: np.ndarray) -> np.ndarray:
        """Apply multi-stage filtering"""
        filtered_data = data.copy()

        # Bandpass filter
        for ch in range(self.num_channels):
            filtered_data[ch, :] = filtfilt(self.bandpass_b, self.bandpass_a, filtered_data[ch, :])

        # Notch filter
        for ch in range(self.num_channels):
            filtered_data[ch, :] = filtfilt(self.notch_b, self.notch_a, filtered_data[ch, :])

        # Adaptive filtering (if enabled)
        if hasattr(self, "adaptive_enabled") and self.adaptive_enabled:
            filtered_data = self._apply_adaptive_filter(filtered_data)

        return filtered_data

    def _remove_artifacts(self, data: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Remove artifacts using ICA and template matching"""
        artifacts_removed = False
        clean_data = data.copy()

        try:
            # ICA-based artifact removal
            if self.config.signal_processing.enable_ica and self.ica_model is not None:
                clean_data = self._apply_ica_artifact_removal(clean_data)
                artifacts_removed = True

            # EOG artifact removal
            if self.config.signal_processing.enable_eog_removal:
                clean_data = self._remove_eog_artifacts(clean_data)
                artifacts_removed = True

            # EMG artifact removal
            if self.config.signal_processing.enable_emg_removal:
                clean_data = self._remove_emg_artifacts(clean_data)
                artifacts_removed = True

        except Exception as e:
            self.logger.warning(f"Artifact removal failed: {e}")

        return clean_data, artifacts_removed

    def _apply_ica_artifact_removal(self, data: np.ndarray) -> np.ndarray:
        """Apply ICA for artifact removal"""
        if self.ica_model is None:
            return data

        # Transform to ICA space
        ica_components = self.ica_model.transform(data.T).T

        # Identify artifact components (simplified)
        artifact_components = []
        for i, component in enumerate(ica_components):
            # Check for eye blink artifacts (high amplitude, frontal)
            if np.max(np.abs(component)) > 3 * np.std(component):
                artifact_components.append(i)

        # Remove artifact components
        clean_components = ica_components.copy()
        clean_components[artifact_components, :] = 0

        # Transform back to sensor space
        clean_data = self.ica_model.inverse_transform(clean_components.T).T

        return clean_data

    def _remove_eog_artifacts(self, data: np.ndarray) -> np.ndarray:
        """Remove eye movement artifacts"""
        # Simple high-pass filter for EOG removal
        sos = signal.butter(4, 1.0, "hp", fs=self.sampling_rate, output="sos")
        clean_data = signal.sosfiltfilt(sos, data, axis=1)
        return clean_data

    def _remove_emg_artifacts(self, data: np.ndarray) -> np.ndarray:
        """Remove muscle artifacts"""
        # Low-pass filter to remove high-frequency EMG
        sos = signal.butter(4, 45.0, "lp", fs=self.sampling_rate, output="sos")
        clean_data = signal.sosfiltfilt(sos, data, axis=1)
        return clean_data

    def _extract_features(self, data: np.ndarray) -> Dict[str, Any]:
        """Extract features from processed signal"""
        features = {}

        try:
            # Apply all configured feature extractors
            for name, extractor in self.feature_extractors.items():
                features[name] = extractor.extract(data, self.sampling_rate)

            # Add basic statistics
            features["statistics"] = {
                "mean": np.mean(data, axis=1).tolist(),
                "std": np.std(data, axis=1).tolist(),
                "variance": np.var(data, axis=1).tolist(),
                "skewness": stats.skew(data, axis=1).tolist(),
                "kurtosis": stats.kurtosis(data, axis=1).tolist(),
            }

        except Exception as e:
            self.logger.error(f"Feature extraction error: {e}")
            features = {"error": str(e)}

        return features

    def _assess_quality(self, data: np.ndarray) -> float:
        """Assess signal quality"""
        try:
            # Calculate quality metrics
            noise_level = np.mean(np.std(data, axis=1))
            signal_power = np.mean(np.var(data, axis=1))
            snr = signal_power / (noise_level + 1e-10)

            # Check for saturation
            saturation_ratio = np.mean(np.abs(data) > 0.9 * np.max(np.abs(data)))

            # Check for flat lines
            flat_ratio = np.mean(np.std(data, axis=1) < 0.1)

            # Combined quality score (0-1)
            quality_score = min(1.0, snr / 10.0) * (1 - saturation_ratio) * (1 - flat_ratio)

            return max(0.0, quality_score)

        except Exception as e:
            self.logger.error(f"Quality assessment error: {e}")
            return 0.5  # Default moderate quality

    def train_ica_model(self, training_data: np.ndarray):
        """Train ICA model for artifact removal"""
        try:
            if training_data.shape[0] < self.num_channels:
                raise ValueError("Insufficient data for ICA training")

            # Initialize and fit ICA
            n_components = min(self.config.signal_processing.ica_components, self.num_channels)

            self.ica_model = FastICA(
                n_components=n_components, whiten="unit-variance", random_state=42
            )

            # Fit on training data
            self.ica_model.fit(training_data.T)

            self.logger.info(f"ICA model trained with {n_components} components")

        except Exception as e:
            self.logger.error(f"ICA training failed: {e}")
            self.ica_model = None

    def get_buffer_data(self, duration: float) -> Optional[np.ndarray]:
        """Get data from buffer for specified duration"""
        with self.buffer_lock:
            n_samples = int(duration * self.sampling_rate)
            if self.buffer_index < n_samples:
                return None

            return self.signal_buffer[:, self.buffer_index - n_samples : self.buffer_index].copy()

    def reset_buffer(self):
        """Reset signal buffer"""
        with self.buffer_lock:
            self.signal_buffer.fill(0)
            self.buffer_index = 0

    async def cleanup(self):
        """Cleanup signal processor resources"""
        self.reset_buffer()
        self.ica_model = None
        self.artifact_templates.clear()
        self.logger.info("Signal Processor cleanup complete")


class SpectralFeatureExtractor:
    """Extract spectral features from EEG signals"""

    def __init__(self, config: BCIConfig):
        self.config = config

        # Frequency bands of interest
        self.frequency_bands = {
            "delta": (0.5, 4),
            "theta": (4, 8),
            "alpha": (8, 12),
            "beta": (12, 30),
            "gamma": (30, 50),
        }

    def extract(self, data: np.ndarray, sampling_rate: float) -> Dict[str, Any]:
        """Extract spectral features"""
        features = {}

        # Power spectral density
        for ch_idx, channel in enumerate(self.config.device.channels):
            f, psd = welch(data[ch_idx, :], fs=sampling_rate, nperseg=256)

            # Band power features
            band_powers = {}
            for band_name, (low, high) in self.frequency_bands.items():
                band_mask = (f >= low) & (f <= high)
                band_power = np.trapz(psd[band_mask], f[band_mask])
                band_powers[band_name] = float(band_power)

            features[f"ch_{channel}_band_powers"] = band_powers

            # Peak frequency
            peak_freq = f[np.argmax(psd)]
            features[f"ch_{channel}_peak_freq"] = float(peak_freq)

            # Spectral entropy
            norm_psd = psd / np.sum(psd)
            spectral_entropy = -np.sum(norm_psd * np.log2(norm_psd + 1e-10))
            features[f"ch_{channel}_spectral_entropy"] = float(spectral_entropy)

        return features


class TemporalFeatureExtractor:
    """Extract temporal features from EEG signals"""

    def __init__(self, config: BCIConfig):
        self.config = config

    def extract(self, data: np.ndarray, sampling_rate: float) -> Dict[str, Any]:
        """Extract temporal features"""
        features = {}

        for ch_idx, channel in enumerate(self.config.device.channels):
            ch_data = data[ch_idx, :]

            # Zero crossings
            zero_crossings = np.sum(np.diff(np.sign(ch_data)) != 0)
            features[f"ch_{channel}_zero_crossings"] = int(zero_crossings)

            # Activity (variance)
            activity = np.var(ch_data)
            features[f"ch_{channel}_activity"] = float(activity)

            # Mobility (mean frequency)
            diff1 = np.diff(ch_data)
            mobility = np.sqrt(np.var(diff1) / np.var(ch_data))
            features[f"ch_{channel}_mobility"] = float(mobility)

            # Complexity
            diff2 = np.diff(diff1)
            complexity = np.sqrt(np.var(diff2) / np.var(diff1)) / mobility
            features[f"ch_{channel}_complexity"] = float(complexity)

            # Peak-to-peak amplitude
            ptp_amplitude = np.ptp(ch_data)
            features[f"ch_{channel}_ptp_amplitude"] = float(ptp_amplitude)

        return features


class SpatialFeatureExtractor:
    """Extract spatial features from EEG signals"""

    def __init__(self, config: BCIConfig):
        self.config = config

    def extract(self, data: np.ndarray, sampling_rate: float) -> Dict[str, Any]:
        """Extract spatial features"""
        features = {}

        # Cross-correlation between channels
        n_channels = data.shape[0]
        correlations = np.corrcoef(data)

        # Average correlation
        mask = np.triu(np.ones_like(correlations, dtype=bool), k=1)
        avg_correlation = np.mean(correlations[mask])
        features["avg_cross_correlation"] = float(avg_correlation)

        # Maximum correlation
        max_correlation = np.max(correlations[mask])
        features["max_cross_correlation"] = float(max_correlation)

        # Coherence features
        coherence_matrix = self._compute_coherence_matrix(data, sampling_rate)
        features["avg_coherence"] = float(np.mean(coherence_matrix[mask]))
        features["max_coherence"] = float(np.max(coherence_matrix[mask]))

        # Spatial variance
        spatial_variance = np.var(np.mean(data, axis=1))
        features["spatial_variance"] = float(spatial_variance)

        return features

    def _compute_coherence_matrix(self, data: np.ndarray, sampling_rate: float) -> np.ndarray:
        """Compute coherence matrix between channels"""
        n_channels = data.shape[0]
        coherence_matrix = np.zeros((n_channels, n_channels))

        for i in range(n_channels):
            for j in range(i, n_channels):
                if i == j:
                    coherence_matrix[i, j] = 1.0
                else:
                    f, coh = signal.coherence(data[i, :], data[j, :], fs=sampling_rate, nperseg=256)
                    # Average coherence in alpha band
                    alpha_mask = (f >= 8) & (f <= 12)
                    avg_coh = np.mean(coh[alpha_mask])
                    coherence_matrix[i, j] = avg_coh
                    coherence_matrix[j, i] = avg_coh

        return coherence_matrix
