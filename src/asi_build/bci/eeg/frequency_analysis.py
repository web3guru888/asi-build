"""
EEG Frequency Domain Analysis

Advanced frequency domain analysis for EEG signals including
spectral features, connectivity metrics, and frequency tracking.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.signal import coherence, hilbert, periodogram, welch
from scipy.stats import entropy

from ..core.config import BCIConfig


class FrequencyAnalyzer:
    """
    Comprehensive frequency domain analysis for EEG

    Features:
    - Power spectral density analysis
    - Spectral coherence and connectivity
    - Time-frequency analysis
    - Frequency band analysis
    - Cross-frequency coupling
    """

    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        self.sampling_rate = config.device.sampling_rate
        self.channels = config.device.channels

        # Standard EEG frequency bands
        self.frequency_bands = {
            "delta": (0.5, 4),
            "theta": (4, 8),
            "alpha": (8, 12),
            "beta": (12, 30),
            "gamma": (30, 100),
        }

        self.logger.info("Frequency Analyzer initialized")

    def analyze(self, data: np.ndarray, sampling_rate: float) -> Dict[str, Any]:
        """
        Perform comprehensive frequency analysis

        Parameters:
        data: EEG data (n_channels, n_samples)
        sampling_rate: Sampling rate in Hz

        Returns:
        Dictionary of frequency features
        """
        features = {}

        # Basic spectral features
        features.update(self._compute_spectral_features(data, sampling_rate))

        # Band power features
        features.update(self._compute_band_powers(data, sampling_rate))

        # Spectral ratios
        features.update(self._compute_spectral_ratios(features))

        # Coherence features
        features.update(self._compute_coherence_features(data, sampling_rate))

        # Cross-frequency coupling
        features.update(self._compute_cross_frequency_coupling(data, sampling_rate))

        return features

    def _compute_spectral_features(self, data: np.ndarray, sampling_rate: float) -> Dict[str, Any]:
        """Compute basic spectral features"""
        features = {}

        for ch_idx, channel in enumerate(self.channels):
            if ch_idx >= data.shape[0]:
                break

            ch_data = data[ch_idx, :]

            # Power spectral density
            f, psd = welch(ch_data, fs=sampling_rate, nperseg=256)

            # Spectral centroid
            spectral_centroid = np.sum(f * psd) / np.sum(psd)
            features[f"{channel}_spectral_centroid"] = float(spectral_centroid)

            # Spectral spread
            spectral_spread = np.sqrt(np.sum(((f - spectral_centroid) ** 2) * psd) / np.sum(psd))
            features[f"{channel}_spectral_spread"] = float(spectral_spread)

            # Spectral skewness
            spectral_skewness = np.sum(((f - spectral_centroid) ** 3) * psd) / (
                np.sum(psd) * spectral_spread**3
            )
            features[f"{channel}_spectral_skewness"] = float(spectral_skewness)

            # Spectral kurtosis
            spectral_kurtosis = np.sum(((f - spectral_centroid) ** 4) * psd) / (
                np.sum(psd) * spectral_spread**4
            )
            features[f"{channel}_spectral_kurtosis"] = float(spectral_kurtosis)

            # Spectral entropy
            norm_psd = psd / np.sum(psd)
            spectral_entropy = entropy(norm_psd)
            features[f"{channel}_spectral_entropy"] = float(spectral_entropy)

            # Peak frequency
            peak_freq = f[np.argmax(psd)]
            features[f"{channel}_peak_frequency"] = float(peak_freq)

            # Spectral edge frequency (95% power)
            cumsum_psd = np.cumsum(psd)
            total_power = cumsum_psd[-1]
            edge_95_idx = np.where(cumsum_psd >= 0.95 * total_power)[0]

            if len(edge_95_idx) > 0:
                edge_freq = f[edge_95_idx[0]]
                features[f"{channel}_spectral_edge_95"] = float(edge_freq)

        return features

    def _compute_band_powers(self, data: np.ndarray, sampling_rate: float) -> Dict[str, float]:
        """Compute power in standard frequency bands"""
        features = {}

        for ch_idx, channel in enumerate(self.channels):
            if ch_idx >= data.shape[0]:
                break

            ch_data = data[ch_idx, :]

            # Compute PSD
            f, psd = welch(ch_data, fs=sampling_rate, nperseg=256)

            # Extract band powers
            total_power = np.trapz(psd, f)

            for band_name, (low_freq, high_freq) in self.frequency_bands.items():
                # Find frequency indices
                band_mask = (f >= low_freq) & (f <= high_freq)

                if np.any(band_mask):
                    band_power = np.trapz(psd[band_mask], f[band_mask])

                    # Absolute power
                    features[f"{channel}_{band_name}_power"] = float(band_power)

                    # Relative power
                    if total_power > 0:
                        rel_power = band_power / total_power
                        features[f"{channel}_{band_name}_rel_power"] = float(rel_power)

        return features

    def _compute_spectral_ratios(self, band_features: Dict[str, float]) -> Dict[str, float]:
        """Compute important spectral ratios"""
        features = {}

        # Common EEG ratios
        ratios = [
            ("theta", "alpha"),  # Theta/Alpha ratio (attention)
            ("theta", "beta"),  # Theta/Beta ratio (ADHD marker)
            ("alpha", "beta"),  # Alpha/Beta ratio
            ("beta", "gamma"),  # Beta/Gamma ratio
            ("delta", "alpha"),  # Delta/Alpha ratio (sleep)
        ]

        for channel in self.channels:
            for band1, band2 in ratios:
                power1_key = f"{channel}_{band1}_power"
                power2_key = f"{channel}_{band2}_power"

                if power1_key in band_features and power2_key in band_features:
                    power1 = band_features[power1_key]
                    power2 = band_features[power2_key]

                    if power2 > 0:
                        ratio = power1 / power2
                        features[f"{channel}_{band1}_{band2}_ratio"] = float(ratio)

        return features

    def _compute_coherence_features(
        self, data: np.ndarray, sampling_rate: float
    ) -> Dict[str, float]:
        """Compute spectral coherence between channels"""
        features = {}

        n_channels = min(data.shape[0], len(self.channels))

        # Compute coherence for each frequency band
        for band_name, (low_freq, high_freq) in self.frequency_bands.items():
            coherence_values = []

            for i in range(n_channels):
                for j in range(i + 1, n_channels):
                    ch1_data = data[i, :]
                    ch2_data = data[j, :]

                    # Compute coherence
                    f, coh = coherence(ch1_data, ch2_data, fs=sampling_rate, nperseg=256)

                    # Extract coherence in frequency band
                    band_mask = (f >= low_freq) & (f <= high_freq)

                    if np.any(band_mask):
                        avg_coherence = np.mean(coh[band_mask])
                        coherence_values.append(avg_coherence)

                        # Store individual channel pair coherence
                        ch1_name = self.channels[i]
                        ch2_name = self.channels[j]
                        features[f"{ch1_name}_{ch2_name}_{band_name}_coherence"] = float(
                            avg_coherence
                        )

            # Store average coherence for this band
            if coherence_values:
                features[f"avg_{band_name}_coherence"] = float(np.mean(coherence_values))
                features[f"max_{band_name}_coherence"] = float(np.max(coherence_values))

        return features

    def _compute_cross_frequency_coupling(
        self, data: np.ndarray, sampling_rate: float
    ) -> Dict[str, float]:
        """Compute cross-frequency coupling measures"""
        features = {}

        # Phase-amplitude coupling between frequency bands
        coupling_pairs = [
            ("theta", "gamma"),  # Theta-gamma coupling
            ("alpha", "gamma"),  # Alpha-gamma coupling
            ("beta", "gamma"),  # Beta-gamma coupling
        ]

        for ch_idx, channel in enumerate(self.channels):
            if ch_idx >= data.shape[0]:
                break

            ch_data = data[ch_idx, :]

            for low_band, high_band in coupling_pairs:
                # Get frequency ranges
                low_freq_range = self.frequency_bands[low_band]
                high_freq_range = self.frequency_bands[high_band]

                # Extract phase from low frequency band
                low_filtered = self._bandpass_filter(
                    ch_data, low_freq_range[0], low_freq_range[1], sampling_rate
                )
                low_analytic = hilbert(low_filtered)
                low_phase = np.angle(low_analytic)

                # Extract amplitude from high frequency band
                high_filtered = self._bandpass_filter(
                    ch_data, high_freq_range[0], high_freq_range[1], sampling_rate
                )
                high_analytic = hilbert(high_filtered)
                high_amplitude = np.abs(high_analytic)

                # Compute phase-amplitude coupling
                pac = self._compute_phase_amplitude_coupling(low_phase, high_amplitude)
                features[f"{channel}_{low_band}_{high_band}_pac"] = float(pac)

        return features

    def _bandpass_filter(
        self, data: np.ndarray, low_freq: float, high_freq: float, sampling_rate: float
    ) -> np.ndarray:
        """Apply bandpass filter"""
        from scipy.signal import butter, filtfilt

        nyquist = sampling_rate / 2
        low = low_freq / nyquist
        high = high_freq / nyquist

        # Ensure valid frequency range
        low = max(0.01, min(0.99, low))
        high = max(low + 0.01, min(0.99, high))

        try:
            b, a = butter(4, [low, high], btype="band")
            filtered_data = filtfilt(b, a, data)
            return filtered_data
        except Exception:
            return data

    def _compute_phase_amplitude_coupling(self, phase: np.ndarray, amplitude: np.ndarray) -> float:
        """Compute phase-amplitude coupling strength"""
        try:
            # Method: Mean Vector Length
            complex_valued = amplitude * np.exp(1j * phase)
            mvc = np.abs(np.mean(complex_valued)) / np.mean(amplitude)
            return mvc
        except Exception:
            return 0.0

    def compute_time_frequency_analysis(
        self, data: np.ndarray, sampling_rate: float
    ) -> Dict[str, Any]:
        """Compute time-frequency decomposition"""
        try:
            from scipy import signal as sp_signal

            features = {}

            for ch_idx, channel in enumerate(self.channels):
                if ch_idx >= data.shape[0]:
                    break

                ch_data = data[ch_idx, :]

                # Short-time Fourier transform
                f, t, Zxx = sp_signal.stft(ch_data, fs=sampling_rate, nperseg=256)

                # Power spectrogram
                power_spectrogram = np.abs(Zxx) ** 2

                # Time-averaged power in each band
                for band_name, (low_freq, high_freq) in self.frequency_bands.items():
                    band_mask = (f >= low_freq) & (f <= high_freq)

                    if np.any(band_mask):
                        band_power_time = np.mean(power_spectrogram[band_mask, :], axis=0)

                        # Statistics of power over time
                        features[f"{channel}_{band_name}_power_mean"] = float(
                            np.mean(band_power_time)
                        )
                        features[f"{channel}_{band_name}_power_std"] = float(
                            np.std(band_power_time)
                        )
                        features[f"{channel}_{band_name}_power_max"] = float(
                            np.max(band_power_time)
                        )
                        features[f"{channel}_{band_name}_power_min"] = float(
                            np.min(band_power_time)
                        )

            return features

        except Exception as e:
            self.logger.error(f"Time-frequency analysis failed: {e}")
            return {}

    def compute_frequency_stability(
        self, data: np.ndarray, sampling_rate: float, window_length: float = 2.0
    ) -> Dict[str, float]:
        """Compute frequency stability over time"""
        features = {}

        window_samples = int(window_length * sampling_rate)
        n_windows = data.shape[1] // window_samples

        if n_windows < 2:
            return features

        for ch_idx, channel in enumerate(self.channels):
            if ch_idx >= data.shape[0]:
                break

            ch_data = data[ch_idx, :]

            # Compute peak frequency in each window
            peak_frequencies = []

            for win_idx in range(n_windows):
                start_idx = win_idx * window_samples
                end_idx = start_idx + window_samples

                window_data = ch_data[start_idx:end_idx]

                # Compute PSD for this window
                f, psd = welch(window_data, fs=sampling_rate, nperseg=min(256, len(window_data)))

                # Find peak frequency
                peak_freq = f[np.argmax(psd)]
                peak_frequencies.append(peak_freq)

            # Compute stability metrics
            if len(peak_frequencies) > 1:
                features[f"{channel}_peak_freq_std"] = float(np.std(peak_frequencies))
                features[f"{channel}_peak_freq_range"] = float(np.ptp(peak_frequencies))
                features[f"{channel}_peak_freq_stability"] = float(
                    1.0 / (1.0 + np.std(peak_frequencies))
                )

        return features
