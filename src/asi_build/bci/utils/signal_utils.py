"""
Signal Processing Utilities

Collection of utility functions for BCI signal processing.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import signal
from scipy.signal import butter, filtfilt, hilbert, welch


class SignalUtilities:
    """Utility functions for signal processing"""

    @staticmethod
    def bandpass_filter(
        data: np.ndarray, low_freq: float, high_freq: float, sampling_rate: float, order: int = 4
    ) -> np.ndarray:
        """Apply bandpass filter to signal"""
        nyquist = sampling_rate / 2
        low = low_freq / nyquist
        high = high_freq / nyquist

        low = max(0.01, min(0.99, low))
        high = max(low + 0.01, min(0.99, high))

        b, a = butter(order, [low, high], btype="band")

        if data.ndim == 1:
            return filtfilt(b, a, data)
        else:
            filtered_data = np.zeros_like(data)
            for ch in range(data.shape[0]):
                filtered_data[ch, :] = filtfilt(b, a, data[ch, :])
            return filtered_data

    @staticmethod
    def notch_filter(
        data: np.ndarray, notch_freq: float, sampling_rate: float, quality_factor: float = 30
    ) -> np.ndarray:
        """Apply notch filter to remove line noise"""
        b, a = signal.iirnotch(notch_freq, quality_factor, sampling_rate)

        if data.ndim == 1:
            return filtfilt(b, a, data)
        else:
            filtered_data = np.zeros_like(data)
            for ch in range(data.shape[0]):
                filtered_data[ch, :] = filtfilt(b, a, data[ch, :])
            return filtered_data

    @staticmethod
    def compute_psd(
        data: np.ndarray, sampling_rate: float, nperseg: int = 256
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute power spectral density"""
        if data.ndim == 1:
            return welch(data, fs=sampling_rate, nperseg=nperseg)
        else:
            # Multi-channel data
            f = None
            psd_matrix = []

            for ch in range(data.shape[0]):
                f_ch, psd_ch = welch(data[ch, :], fs=sampling_rate, nperseg=nperseg)
                if f is None:
                    f = f_ch
                psd_matrix.append(psd_ch)

            return f, np.array(psd_matrix)

    @staticmethod
    def epoch_data(data: np.ndarray, epoch_length: int, overlap: float = 0.0) -> np.ndarray:
        """Split continuous data into epochs"""
        if data.ndim == 1:
            data = data.reshape(1, -1)

        n_channels, n_samples = data.shape
        step_size = int(epoch_length * (1 - overlap))

        epochs = []
        start = 0

        while start + epoch_length <= n_samples:
            epoch = data[:, start : start + epoch_length]
            epochs.append(epoch)
            start += step_size

        return np.array(epochs)

    @staticmethod
    def normalize_signal(data: np.ndarray, method: str = "zscore") -> np.ndarray:
        """Normalize signal using various methods"""
        if method == "zscore":
            return (data - np.mean(data, axis=-1, keepdims=True)) / np.std(
                data, axis=-1, keepdims=True
            )
        elif method == "minmax":
            min_val = np.min(data, axis=-1, keepdims=True)
            max_val = np.max(data, axis=-1, keepdims=True)
            return (data - min_val) / (max_val - min_val)
        elif method == "robust":
            median = np.median(data, axis=-1, keepdims=True)
            mad = np.median(np.abs(data - median), axis=-1, keepdims=True)
            return (data - median) / mad
        else:
            raise ValueError(f"Unknown normalization method: {method}")

    @staticmethod
    def detect_bad_samples(data: np.ndarray, threshold: float = 4.0) -> np.ndarray:
        """Detect bad samples using z-score"""
        z_scores = np.abs((data - np.mean(data)) / np.std(data))
        return z_scores > threshold

    @staticmethod
    def interpolate_bad_samples(data: np.ndarray, bad_mask: np.ndarray) -> np.ndarray:
        """Interpolate bad samples"""
        clean_data = data.copy()
        bad_indices = np.where(bad_mask)[0]

        for idx in bad_indices:
            # Find nearest good samples
            left_idx = idx - 1
            right_idx = idx + 1

            while left_idx >= 0 and bad_mask[left_idx]:
                left_idx -= 1

            while right_idx < len(data) and bad_mask[right_idx]:
                right_idx += 1

            # Interpolate
            if left_idx >= 0 and right_idx < len(data):
                clean_data[idx] = np.interp(
                    idx, [left_idx, right_idx], [data[left_idx], data[right_idx]]
                )
            elif left_idx >= 0:
                clean_data[idx] = data[left_idx]
            elif right_idx < len(data):
                clean_data[idx] = data[right_idx]

        return clean_data
