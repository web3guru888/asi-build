"""
EEG Artifact Removal

Advanced artifact removal techniques for EEG signals including
ICA, template matching, and machine learning approaches.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from scipy import signal, stats
from scipy.signal import butter, filtfilt
from sklearn.decomposition import FastICA, PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from ..core.config import BCIConfig


class ArtifactRemover:
    """
    Comprehensive artifact removal for EEG signals
    
    Artifacts handled:
    - Eye movement artifacts (EOG)
    - Muscle artifacts (EMG)
    - Cardiac artifacts (ECG)
    - Line noise and electrical interference
    - Movement artifacts
    """
    
    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.sampling_rate = config.device.sampling_rate
        self.channels = config.device.channels
        self.n_channels = len(self.channels)
        
        # ICA model for artifact removal
        self.ica_model = None
        self.artifact_components: List[int] = []
        
        # Artifact templates
        self.eog_templates = {}
        self.emg_templates = {}
        self.ecg_templates = {}
        
        # Adaptive filters
        self.adaptive_filters = {}
        
        self.logger.info("Artifact Remover initialized")
    
    def remove_artifacts(self, data: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Remove artifacts from EEG data
        
        Parameters:
        data: EEG data (n_channels, n_samples)
        
        Returns:
        Tuple of (clean_data, artifacts_removed)
        """
        try:
            clean_data = data.copy()
            artifacts_removed = False
            
            # Step 1: Remove line noise
            clean_data = self._remove_line_noise(clean_data)
            artifacts_removed = True
            
            # Step 2: ICA-based artifact removal
            if self.ica_model is not None:
                clean_data = self._ica_artifact_removal(clean_data)
                artifacts_removed = True
            
            # Step 3: Template-based artifact removal
            clean_data, template_removed = self._template_based_removal(clean_data)
            if template_removed:
                artifacts_removed = True
            
            # Step 4: Adaptive filtering
            clean_data = self._adaptive_filtering(clean_data)
            
            # Step 5: Statistical outlier removal
            clean_data = self._remove_statistical_outliers(clean_data)
            
            return clean_data, artifacts_removed
            
        except Exception as e:
            self.logger.error(f"Artifact removal failed: {e}")
            return data, False
    
    def _remove_line_noise(self, data: np.ndarray) -> np.ndarray:
        """Remove power line noise"""
        clean_data = data.copy()
        
        # Remove 50Hz (and harmonics) or 60Hz depending on region
        line_freqs = [50, 100, 150] if self.config.signal_processing.notch_freq == 50 else [60, 120, 180]
        
        for freq in line_freqs:
            if freq < self.sampling_rate / 2:
                # Design notch filter
                b, a = signal.iirnotch(freq, 30, self.sampling_rate)
                
                # Apply to all channels
                for ch in range(self.n_channels):
                    clean_data[ch, :] = filtfilt(b, a, clean_data[ch, :])
        
        return clean_data
    
    def _ica_artifact_removal(self, data: np.ndarray) -> np.ndarray:
        """Remove artifacts using ICA"""
        if self.ica_model is None:
            return data
        
        try:
            # Transform to ICA space
            ica_data = self.ica_model.transform(data.T).T
            
            # Remove artifact components
            clean_ica_data = ica_data.copy()
            clean_ica_data[self.artifact_components, :] = 0
            
            # Transform back to sensor space
            clean_data = self.ica_model.inverse_transform(clean_ica_data.T).T
            
            return clean_data
            
        except Exception as e:
            self.logger.error(f"ICA artifact removal failed: {e}")
            return data
    
    def _template_based_removal(self, data: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Remove artifacts using template matching"""
        clean_data = data.copy()
        artifacts_removed = False
        
        try:
            # EOG artifact removal
            if self.eog_templates:
                clean_data, eog_removed = self._remove_eog_artifacts(clean_data)
                if eog_removed:
                    artifacts_removed = True
            
            # EMG artifact removal
            if self.emg_templates:
                clean_data, emg_removed = self._remove_emg_artifacts(clean_data)
                if emg_removed:
                    artifacts_removed = True
            
            # ECG artifact removal
            if self.ecg_templates:
                clean_data, ecg_removed = self._remove_ecg_artifacts(clean_data)
                if ecg_removed:
                    artifacts_removed = True
            
            return clean_data, artifacts_removed
            
        except Exception as e:
            self.logger.error(f"Template-based removal failed: {e}")
            return data, False
    
    def _remove_eog_artifacts(self, data: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Remove eye movement artifacts"""
        # Simple approach: high-pass filter for frontal channels
        frontal_channels = ['Fp1', 'Fp2', 'F7', 'F8']
        
        clean_data = data.copy()
        artifacts_removed = False
        
        for ch_name in frontal_channels:
            if ch_name in self.channels:
                ch_idx = self.channels.index(ch_name)
                
                # Detect eye blinks (high amplitude spikes)
                ch_data = data[ch_idx, :]
                
                # Threshold-based detection
                threshold = 3 * np.std(ch_data)
                artifact_indices = np.where(np.abs(ch_data) > threshold)[0]
                
                if len(artifact_indices) > 0:
                    # Simple interpolation to remove artifacts
                    for idx in artifact_indices:
                        start_idx = max(0, idx - 10)
                        end_idx = min(len(ch_data), idx + 10)
                        
                        if start_idx > 0 and end_idx < len(ch_data):
                            # Linear interpolation
                            clean_data[ch_idx, start_idx:end_idx] = np.interp(
                                np.arange(start_idx, end_idx),
                                [start_idx - 1, end_idx],
                                [ch_data[start_idx - 1], ch_data[end_idx]]
                            )
                            artifacts_removed = True
        
        return clean_data, artifacts_removed
    
    def _remove_emg_artifacts(self, data: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Remove muscle artifacts"""
        # EMG typically has high frequency content
        clean_data = data.copy()
        artifacts_removed = False
        
        # Low-pass filter to remove high-frequency EMG
        cutoff_freq = 45  # Hz
        nyquist = self.sampling_rate / 2
        
        if cutoff_freq < nyquist:
            b, a = butter(4, cutoff_freq / nyquist, 'low')
            
            for ch in range(self.n_channels):
                # Detect high-frequency content
                f, psd = signal.welch(data[ch, :], fs=self.sampling_rate, nperseg=256)
                high_freq_power = np.sum(psd[f > 30])
                total_power = np.sum(psd)
                
                # If high-frequency power is significant, apply filter
                if high_freq_power / total_power > 0.3:
                    clean_data[ch, :] = filtfilt(b, a, clean_data[ch, :])
                    artifacts_removed = True
        
        return clean_data, artifacts_removed
    
    def _remove_ecg_artifacts(self, data: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Remove cardiac artifacts"""
        # ECG artifacts typically occur at ~1Hz
        clean_data = data.copy()
        artifacts_removed = False
        
        # Simple approach: detect periodic artifacts
        for ch in range(self.n_channels):
            ch_data = data[ch, :]
            
            # Autocorrelation to detect periodic patterns
            autocorr = np.correlate(ch_data, ch_data, mode='full')
            autocorr = autocorr[autocorr.size // 2:]
            
            # Look for peaks at cardiac frequencies (0.8-1.5 Hz)
            cardiac_samples = int(self.sampling_rate * 0.7)  # ~1.4 Hz
            cardiac_range = slice(int(cardiac_samples * 0.5), int(cardiac_samples * 1.5))
            
            if len(autocorr) > cardiac_samples * 1.5:
                cardiac_autocorr = autocorr[cardiac_range]
                max_autocorr = np.max(cardiac_autocorr)
                
                # If strong periodicity detected, apply filter
                if max_autocorr > 0.5 * autocorr[0]:
                    # Notch filter at detected frequency
                    peak_idx = np.argmax(cardiac_autocorr) + cardiac_range.start
                    cardiac_freq = self.sampling_rate / peak_idx
                    
                    if 0.8 <= cardiac_freq <= 1.5:  # Valid cardiac frequency
                        b, a = signal.iirnotch(cardiac_freq, 10, self.sampling_rate)
                        clean_data[ch, :] = filtfilt(b, a, clean_data[ch, :])
                        artifacts_removed = True
        
        return clean_data, artifacts_removed
    
    def _adaptive_filtering(self, data: np.ndarray) -> np.ndarray:
        """Apply adaptive filtering"""
        # Simple adaptive mean filter
        window_size = int(0.1 * self.sampling_rate)  # 100ms window
        
        clean_data = data.copy()
        
        for ch in range(self.n_channels):
            # Moving average filter with adaptive window
            clean_data[ch, :] = self._adaptive_moving_average(
                data[ch, :], window_size
            )
        
        return clean_data
    
    def _adaptive_moving_average(self, signal_data: np.ndarray, base_window: int) -> np.ndarray:
        """Adaptive moving average filter"""
        filtered_signal = signal_data.copy()
        
        for i in range(len(signal_data)):
            # Adapt window size based on local variance
            start_idx = max(0, i - base_window // 2)
            end_idx = min(len(signal_data), i + base_window // 2)
            
            local_data = signal_data[start_idx:end_idx]
            local_std = np.std(local_data)
            
            # Larger window for stable regions, smaller for variable regions
            if local_std < np.std(signal_data) * 0.5:
                window_size = base_window
            else:
                window_size = base_window // 2
            
            # Apply moving average
            avg_start = max(0, i - window_size // 2)
            avg_end = min(len(signal_data), i + window_size // 2)
            
            if avg_end > avg_start:
                filtered_signal[i] = np.mean(signal_data[avg_start:avg_end])
        
        return filtered_signal
    
    def _remove_statistical_outliers(self, data: np.ndarray) -> np.ndarray:
        """Remove statistical outliers"""
        clean_data = data.copy()
        
        for ch in range(self.n_channels):
            ch_data = data[ch, :]
            
            # Z-score based outlier detection
            z_scores = np.abs(stats.zscore(ch_data))
            outlier_threshold = 4  # 4 standard deviations
            
            outlier_indices = np.where(z_scores > outlier_threshold)[0]
            
            # Interpolate outliers
            for idx in outlier_indices:
                # Find nearest non-outlier values
                left_idx = idx - 1
                right_idx = idx + 1
                
                while left_idx >= 0 and z_scores[left_idx] > outlier_threshold:
                    left_idx -= 1
                
                while right_idx < len(ch_data) and z_scores[right_idx] > outlier_threshold:
                    right_idx += 1
                
                # Interpolate
                if left_idx >= 0 and right_idx < len(ch_data):
                    clean_data[ch, idx] = np.interp(
                        idx, [left_idx, right_idx],
                        [ch_data[left_idx], ch_data[right_idx]]
                    )
                elif left_idx >= 0:
                    clean_data[ch, idx] = ch_data[left_idx]
                elif right_idx < len(ch_data):
                    clean_data[ch, idx] = ch_data[right_idx]
        
        return clean_data
    
    def train_ica_model(self, training_data: np.ndarray) -> bool:
        """Train ICA model for artifact removal"""
        try:
            if training_data.shape[0] < self.n_channels:
                self.logger.error("Insufficient data for ICA training")
                return False
            
            # Initialize ICA
            n_components = min(self.config.signal_processing.ica_components, self.n_channels)
            
            self.ica_model = FastICA(
                n_components=n_components,
                whiten='unit-variance',
                random_state=42,
                max_iter=1000
            )
            
            # Fit ICA
            self.ica_model.fit(training_data.T)
            
            # Automatically identify artifact components
            self.artifact_components = self._identify_artifact_components(training_data)
            
            self.logger.info(f"ICA model trained with {n_components} components")
            self.logger.info(f"Identified {len(self.artifact_components)} artifact components")
            
            return True
            
        except Exception as e:
            self.logger.error(f"ICA training failed: {e}")
            return False
    
    def _identify_artifact_components(self, data: np.ndarray) -> List[int]:
        """Automatically identify artifact components"""
        if self.ica_model is None:
            return []
        
        artifact_components = []
        
        try:
            # Transform data to ICA space
            ica_data = self.ica_model.transform(data.T).T
            
            for comp_idx, component in enumerate(ica_data):
                # Check for artifact characteristics
                
                # 1. High amplitude variance (likely artifacts)
                comp_std = np.std(component)
                if comp_std > 3 * np.mean([np.std(comp) for comp in ica_data]):
                    artifact_components.append(comp_idx)
                    continue
                
                # 2. High frequency content (EMG artifacts)
                f, psd = signal.welch(component, fs=self.sampling_rate, nperseg=256)
                high_freq_power = np.sum(psd[f > 30])
                total_power = np.sum(psd)
                
                if high_freq_power / total_power > 0.6:
                    artifact_components.append(comp_idx)
                    continue
                
                # 3. Low frequency trend (eye movements)
                low_freq_power = np.sum(psd[f < 2])
                if low_freq_power / total_power > 0.7:
                    artifact_components.append(comp_idx)
                    continue
                
                # 4. Periodic patterns (cardiac artifacts)
                autocorr = np.correlate(component, component, mode='full')
                autocorr = autocorr[autocorr.size // 2:]
                
                # Check for periodicity in cardiac range
                cardiac_samples = int(self.sampling_rate)  # 1 second
                if len(autocorr) > cardiac_samples:
                    periodic_strength = np.max(autocorr[cardiac_samples//2:cardiac_samples]) / autocorr[0]
                    if periodic_strength > 0.3:
                        artifact_components.append(comp_idx)
            
            return artifact_components
            
        except Exception as e:
            self.logger.error(f"Artifact component identification failed: {e}")
            return []
    
    def set_artifact_components(self, component_indices: List[int]):
        """Manually set artifact components"""
        self.artifact_components = component_indices
        self.logger.info(f"Set {len(component_indices)} artifact components: {component_indices}")
    
    def get_ica_components(self) -> Optional[np.ndarray]:
        """Get ICA components for inspection"""
        if self.ica_model is None:
            return None
        
        return self.ica_model.components_
    
    def get_ica_mixing_matrix(self) -> Optional[np.ndarray]:
        """Get ICA mixing matrix"""
        if self.ica_model is None:
            return None
        
        return self.ica_model.mixing_
    
    def visualize_ica_components(self, data_sample: Optional[np.ndarray] = None):
        """Visualize ICA components"""
        if self.ica_model is None:
            self.logger.error("ICA model not trained")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            components = self.get_ica_components()
            n_components = components.shape[0]
            
            # Plot component topographies
            fig, axes = plt.subplots(2, (n_components + 1) // 2, figsize=(15, 8))
            axes = axes.flatten()
            
            for i in range(n_components):
                ax = axes[i]
                
                # Simple bar plot of component weights
                ax.bar(range(self.n_channels), components[i, :])
                ax.set_title(f'IC {i+1}' + (' (Artifact)' if i in self.artifact_components else ''))
                ax.set_xlabel('Channels')
                ax.set_ylabel('Weight')
                
                if len(self.channels) <= 20:  # Only show channel names for small montages
                    ax.set_xticks(range(self.n_channels))
                    ax.set_xticklabels(self.channels, rotation=45)
            
            plt.tight_layout()
            plt.suptitle('ICA Components')
            plt.show()
            
            # Plot component time series if data provided
            if data_sample is not None:
                ica_data = self.ica_model.transform(data_sample.T).T
                
                fig, axes = plt.subplots(n_components, 1, figsize=(12, 2*n_components))
                if n_components == 1:
                    axes = [axes]
                
                time_axis = np.arange(ica_data.shape[1]) / self.sampling_rate
                
                for i in range(n_components):
                    axes[i].plot(time_axis, ica_data[i, :])
                    axes[i].set_title(f'IC {i+1}' + (' (Artifact)' if i in self.artifact_components else ''))
                    axes[i].set_ylabel('Amplitude')
                    
                    if i == n_components - 1:
                        axes[i].set_xlabel('Time (s)')
                
                plt.tight_layout()
                plt.suptitle('ICA Component Time Series')
                plt.show()
            
        except ImportError:
            self.logger.warning("Matplotlib not available for visualization")
        except Exception as e:
            self.logger.error(f"Visualization failed: {e}")
    
    def save_model(self, filepath: str) -> bool:
        """Save ICA model"""
        try:
            import joblib
            
            model_data = {
                'ica_model': self.ica_model,
                'artifact_components': self.artifact_components,
                'channels': self.channels,
                'sampling_rate': self.sampling_rate
            }
            
            joblib.dump(model_data, filepath)
            self.logger.info(f"Artifact removal model saved to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
            return False
    
    def load_model(self, filepath: str) -> bool:
        """Load ICA model"""
        try:
            import joblib
            
            model_data = joblib.load(filepath)
            
            self.ica_model = model_data['ica_model']
            self.artifact_components = model_data['artifact_components']
            
            # Verify compatibility
            if (model_data['channels'] == self.channels and 
                model_data['sampling_rate'] == self.sampling_rate):
                
                self.logger.info(f"Artifact removal model loaded from {filepath}")
                return True
            else:
                self.logger.warning("Model parameters don't match current configuration")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            return False