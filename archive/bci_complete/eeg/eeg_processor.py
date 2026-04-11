"""
EEG Processor - Specialized EEG signal processing

Advanced EEG-specific processing including artifact removal, 
frequency analysis, and spatial filtering.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from scipy import signal, stats
from scipy.signal import butter, filtfilt, welch, coherence
from sklearn.decomposition import FastICA, PCA
import mne
from dataclasses import dataclass

from ..core.config import BCIConfig
from ..core.signal_processor import ProcessedSignal
from .artifact_removal import ArtifactRemover
from .frequency_analysis import FrequencyAnalyzer
from .spatial_filters import SpatialFilterBank


@dataclass
class EEGEpoch:
    """Single EEG epoch with metadata"""
    data: np.ndarray  # Shape: (n_channels, n_samples)
    start_time: float
    duration: float
    label: Optional[str] = None
    event_type: Optional[str] = None
    artifacts: Dict[str, bool] = None
    quality_score: float = 1.0


class EEGProcessor:
    """
    Advanced EEG signal processor
    
    Features:
    - Comprehensive artifact removal (EOG, EMG, line noise)
    - Frequency domain analysis (PSD, coherence, connectivity)
    - Spatial filtering (CAR, Laplacian, ICA, CSP)
    - Epoching and event-related processing
    - Quality assessment and bad channel detection
    """
    
    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Sampling parameters
        self.sampling_rate = config.device.sampling_rate
        self.channels = config.device.channels
        self.n_channels = len(self.channels)
        
        # Processing components
        self.artifact_remover = ArtifactRemover(config)
        self.frequency_analyzer = FrequencyAnalyzer(config)
        self.spatial_filters = SpatialFilterBank(config)
        
        # Electrode montage for MNE
        self.montage = self._create_montage()
        
        # Bad channels tracking
        self.bad_channels: List[str] = []
        self.channel_quality: Dict[str, float] = {}
        
        # Preprocessing pipeline
        self.preprocessing_steps = [
            'line_noise_removal',
            'bandpass_filter',
            'artifact_removal',
            'bad_channel_interpolation',
            'rereferencing'
        ]
        
        self.logger.info("EEG Processor initialized")
    
    def _create_montage(self) -> Optional[Any]:
        """Create electrode montage for spatial analysis"""
        try:
            # Standard 10-20 electrode positions
            standard_1020 = mne.channels.make_standard_montage('standard_1020')
            
            # Extract channels that are in our montage
            available_channels = []
            for ch in self.channels:
                if ch in standard_1020.ch_names:
                    available_channels.append(ch)
            
            if available_channels:
                montage = standard_1020.copy()
                montage.ch_names = available_channels
                return montage
            else:
                self.logger.warning("No standard electrode positions found")
                return None
                
        except Exception as e:
            self.logger.warning(f"Could not create montage: {e}")
            return None
    
    def process_continuous(self, raw_data: np.ndarray) -> ProcessedSignal:
        """Process continuous EEG data"""
        try:
            # Input validation
            if raw_data.shape[0] != self.n_channels:
                raise ValueError(f"Expected {self.n_channels} channels, got {raw_data.shape[0]}")
            
            processed_data = raw_data.copy()
            
            # Step 1: Remove line noise
            processed_data = self._remove_line_noise(processed_data)
            
            # Step 2: Bandpass filtering
            processed_data = self._apply_bandpass_filter(processed_data)
            
            # Step 3: Detect and interpolate bad channels
            bad_channels = self._detect_bad_channels(processed_data)
            if bad_channels:
                processed_data = self._interpolate_bad_channels(processed_data, bad_channels)
            
            # Step 4: Artifact removal
            processed_data, artifacts_removed = self.artifact_remover.remove_artifacts(processed_data)
            
            # Step 5: Re-referencing
            processed_data = self._apply_reference(processed_data)
            
            # Step 6: Spatial filtering (if enabled)
            if hasattr(self.config, 'spatial_filtering_enabled') and self.config.spatial_filtering_enabled:
                processed_data = self.spatial_filters.apply_car(processed_data)
            
            # Extract features
            features = self._extract_eeg_features(processed_data)
            
            # Quality assessment
            quality_score = self._assess_eeg_quality(processed_data)
            
            # Create processed signal
            result = ProcessedSignal(
                data=processed_data,
                sampling_rate=self.sampling_rate,
                channels=self.channels,
                timestamp=np.datetime64('now').astype(float),
                features=features,
                artifacts_removed=artifacts_removed,
                quality_score=quality_score
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"EEG processing error: {e}")
            raise
    
    def create_epochs(self, 
                     data: np.ndarray,
                     events: List[Dict],
                     epoch_length: float,
                     baseline: Optional[Tuple[float, float]] = None) -> List[EEGEpoch]:
        """Create epochs from continuous data"""
        epochs = []
        
        try:
            epoch_samples = int(epoch_length * self.sampling_rate)
            
            for event in events:
                start_sample = int(event['sample'])
                end_sample = start_sample + epoch_samples
                
                # Check bounds
                if end_sample <= data.shape[1]:
                    epoch_data = data[:, start_sample:end_sample]
                    
                    # Apply baseline correction if specified
                    if baseline is not None:
                        epoch_data = self._apply_baseline_correction(
                            epoch_data, baseline, epoch_length
                        )
                    
                    # Create epoch object
                    epoch = EEGEpoch(
                        data=epoch_data,
                        start_time=start_sample / self.sampling_rate,
                        duration=epoch_length,
                        label=event.get('label'),
                        event_type=event.get('type'),
                        quality_score=self._assess_epoch_quality(epoch_data)
                    )
                    
                    epochs.append(epoch)
            
            self.logger.info(f"Created {len(epochs)} epochs")
            return epochs
            
        except Exception as e:
            self.logger.error(f"Epoch creation error: {e}")
            return []
    
    def _remove_line_noise(self, data: np.ndarray) -> np.ndarray:
        """Remove power line interference"""
        # Notch filter at 50Hz and harmonics
        clean_data = data.copy()
        
        notch_freqs = [50, 100, 150]  # Hz
        
        for freq in notch_freqs:
            if freq < self.sampling_rate / 2:
                # Design notch filter
                b, a = signal.iirnotch(freq, 30, self.sampling_rate)
                
                # Apply to all channels
                for ch in range(self.n_channels):
                    clean_data[ch, :] = filtfilt(b, a, clean_data[ch, :])
        
        return clean_data
    
    def _apply_bandpass_filter(self, data: np.ndarray) -> np.ndarray:
        """Apply bandpass filter to EEG frequency range"""
        nyquist = self.sampling_rate / 2
        low = self.config.signal_processing.bandpass_low / nyquist
        high = self.config.signal_processing.bandpass_high / nyquist
        
        # Design bandpass filter
        b, a = butter(4, [low, high], btype='band')
        
        # Apply to all channels
        filtered_data = data.copy()
        for ch in range(self.n_channels):
            filtered_data[ch, :] = filtfilt(b, a, filtered_data[ch, :])
        
        return filtered_data
    
    def _detect_bad_channels(self, data: np.ndarray) -> List[str]:
        """Detect bad channels based on various criteria"""
        bad_channels = []
        
        for ch_idx, channel in enumerate(self.channels):
            ch_data = data[ch_idx, :]
            
            # Criterion 1: Flat line detection
            if np.std(ch_data) < 0.1:  # μV
                bad_channels.append(channel)
                continue
            
            # Criterion 2: High amplitude artifacts
            if np.max(np.abs(ch_data)) > 200:  # μV
                bad_channels.append(channel)
                continue
            
            # Criterion 3: High frequency noise
            f, psd = welch(ch_data, fs=self.sampling_rate, nperseg=256)
            high_freq_power = np.sum(psd[f > 40])
            total_power = np.sum(psd)
            
            if high_freq_power / total_power > 0.5:
                bad_channels.append(channel)
                continue
            
            # Criterion 4: Low correlation with neighbors
            correlations = []
            for other_ch_idx, other_channel in enumerate(self.channels):
                if other_ch_idx != ch_idx:
                    corr = np.corrcoef(ch_data, data[other_ch_idx, :])[0, 1]
                    if not np.isnan(corr):
                        correlations.append(corr)
            
            if correlations and np.mean(correlations) < 0.1:
                bad_channels.append(channel)
        
        if bad_channels:
            self.logger.warning(f"Detected bad channels: {bad_channels}")
            self.bad_channels.extend(bad_channels)
        
        return bad_channels
    
    def _interpolate_bad_channels(self, data: np.ndarray, bad_channels: List[str]) -> np.ndarray:
        """Interpolate bad channels using spherical splines"""
        if not bad_channels or self.montage is None:
            return data
        
        try:
            # Create MNE info object
            info = mne.create_info(
                ch_names=self.channels,
                sfreq=self.sampling_rate,
                ch_types='eeg'
            )
            info.set_montage(self.montage)
            
            # Create raw object
            raw = mne.io.RawArray(data, info)
            raw.info['bads'] = bad_channels
            
            # Interpolate
            raw.interpolate_bads(reset_bads=True)
            
            return raw.get_data()
            
        except Exception as e:
            self.logger.warning(f"Channel interpolation failed: {e}")
            return data
    
    def _apply_reference(self, data: np.ndarray, reference_type: str = 'average') -> np.ndarray:
        """Apply re-referencing to the data"""
        if reference_type == 'average':
            # Common Average Reference (CAR)
            ref_signal = np.mean(data, axis=0)
            referenced_data = data - ref_signal
        elif reference_type == 'median':
            # Common Median Reference
            ref_signal = np.median(data, axis=0)
            referenced_data = data - ref_signal
        else:
            # No re-referencing
            referenced_data = data
        
        return referenced_data
    
    def _apply_baseline_correction(self, 
                                 epoch_data: np.ndarray,
                                 baseline: Tuple[float, float],
                                 epoch_length: float) -> np.ndarray:
        """Apply baseline correction to epoch"""
        baseline_start = int((baseline[0] + epoch_length/2) * self.sampling_rate)
        baseline_end = int((baseline[1] + epoch_length/2) * self.sampling_rate)
        
        baseline_start = max(0, baseline_start)
        baseline_end = min(epoch_data.shape[1], baseline_end)
        
        if baseline_end > baseline_start:
            baseline_mean = np.mean(epoch_data[:, baseline_start:baseline_end], axis=1, keepdims=True)
            corrected_data = epoch_data - baseline_mean
        else:
            corrected_data = epoch_data
        
        return corrected_data
    
    def _extract_eeg_features(self, data: np.ndarray) -> Dict[str, Any]:
        """Extract EEG-specific features"""
        features = {}
        
        # Frequency domain features
        freq_features = self.frequency_analyzer.analyze(data, self.sampling_rate)
        features.update(freq_features)
        
        # Connectivity features
        connectivity_features = self._compute_connectivity(data)
        features['connectivity'] = connectivity_features
        
        # Complexity features
        complexity_features = self._compute_complexity_metrics(data)
        features['complexity'] = complexity_features
        
        # Asymmetry features
        asymmetry_features = self._compute_asymmetry_features(data)
        features['asymmetry'] = asymmetry_features
        
        return features
    
    def _compute_connectivity(self, data: np.ndarray) -> Dict[str, Any]:
        """Compute connectivity metrics between channels"""
        connectivity = {}
        
        try:
            # Coherence matrix
            n_channels = data.shape[0]
            coherence_matrix = np.zeros((n_channels, n_channels))
            
            for i in range(n_channels):
                for j in range(i + 1, n_channels):
                    f, coh = coherence(
                        data[i, :], data[j, :],
                        fs=self.sampling_rate,
                        nperseg=256
                    )
                    
                    # Average coherence in specific bands
                    alpha_mask = (f >= 8) & (f <= 12)
                    beta_mask = (f >= 13) & (f <= 30)
                    
                    alpha_coh = np.mean(coh[alpha_mask])
                    beta_coh = np.mean(coh[beta_mask])
                    
                    coherence_matrix[i, j] = alpha_coh
                    coherence_matrix[j, i] = alpha_coh
            
            connectivity['alpha_coherence_matrix'] = coherence_matrix.tolist()
            connectivity['mean_alpha_coherence'] = np.mean(coherence_matrix[np.triu_indices(n_channels, k=1)])
            
            # Phase locking value (simplified)
            plv_matrix = self._compute_plv_matrix(data)
            connectivity['plv_matrix'] = plv_matrix.tolist()
            connectivity['mean_plv'] = np.mean(plv_matrix[np.triu_indices(n_channels, k=1)])
            
        except Exception as e:
            self.logger.error(f"Connectivity computation error: {e}")
            connectivity = {'error': str(e)}
        
        return connectivity
    
    def _compute_plv_matrix(self, data: np.ndarray) -> np.ndarray:
        """Compute Phase Locking Value matrix"""
        from scipy.signal import hilbert
        
        n_channels = data.shape[0]
        plv_matrix = np.zeros((n_channels, n_channels))
        
        # Get instantaneous phases
        phases = np.angle(hilbert(data, axis=1))
        
        for i in range(n_channels):
            for j in range(i + 1, n_channels):
                # Phase difference
                phase_diff = phases[i, :] - phases[j, :]
                
                # PLV calculation
                plv = np.abs(np.mean(np.exp(1j * phase_diff)))
                
                plv_matrix[i, j] = plv
                plv_matrix[j, i] = plv
        
        return plv_matrix
    
    def _compute_complexity_metrics(self, data: np.ndarray) -> Dict[str, Any]:
        """Compute complexity metrics for EEG"""
        complexity = {}
        
        for ch_idx, channel in enumerate(self.channels):
            ch_data = data[ch_idx, :]
            
            # Sample entropy
            sample_entropy = self._sample_entropy(ch_data)
            complexity[f'{channel}_sample_entropy'] = sample_entropy
            
            # Spectral entropy
            f, psd = welch(ch_data, fs=self.sampling_rate, nperseg=256)
            norm_psd = psd / np.sum(psd)
            spectral_entropy = -np.sum(norm_psd * np.log2(norm_psd + 1e-10))
            complexity[f'{channel}_spectral_entropy'] = spectral_entropy
            
            # Higuchi fractal dimension
            fractal_dim = self._higuchi_fractal_dimension(ch_data)
            complexity[f'{channel}_fractal_dimension'] = fractal_dim
        
        return complexity
    
    def _sample_entropy(self, data: np.ndarray, m: int = 2, r: float = 0.2) -> float:
        """Calculate sample entropy"""
        try:
            N = len(data)
            
            # Normalize data
            data_norm = (data - np.mean(data)) / np.std(data)
            
            def _maxdist(data, i, j, m):
                return max([abs(data[i + k] - data[j + k]) for k in range(m)])
            
            def _phi(m):
                patterns = []
                for i in range(N - m + 1):
                    template = data_norm[i:i + m]
                    matches = 0
                    for j in range(N - m + 1):
                        if i != j and _maxdist(data_norm, i, j, m) <= r:
                            matches += 1
                    if matches > 0:
                        patterns.append(matches)
                
                if patterns:
                    return np.mean(patterns) / (N - m + 1)
                else:
                    return 0
            
            phi_m = _phi(m)
            phi_m1 = _phi(m + 1)
            
            if phi_m == 0 or phi_m1 == 0:
                return 0
            
            return -np.log(phi_m1 / phi_m)
            
        except Exception:
            return 0.0
    
    def _higuchi_fractal_dimension(self, data: np.ndarray, k_max: int = 10) -> float:
        """Calculate Higuchi fractal dimension"""
        try:
            N = len(data)
            L = []
            x = []
            
            for k in range(1, k_max + 1):
                Lk = []
                for m in range(k):
                    Lmk = 0
                    for i in range(1, int((N - m) / k)):
                        Lmk += abs(data[m + i * k] - data[m + (i - 1) * k])
                    Lmk = Lmk * (N - 1) / (((N - m) / k) * k) / k
                    Lmk = Lmk / k
                    Lk.append(Lmk)
                L.append(np.log(np.mean(Lmk)))
                x.append(np.log(1.0 / k))
            
            # Linear regression
            coeffs = np.polyfit(x, L, 1)
            return coeffs[0]
            
        except Exception:
            return 1.0
    
    def _compute_asymmetry_features(self, data: np.ndarray) -> Dict[str, Any]:
        """Compute hemispheric asymmetry features"""
        asymmetry = {}
        
        # Define hemisphere channel pairs
        hemisphere_pairs = {
            'frontal': [('Fp1', 'Fp2'), ('F3', 'F4'), ('F7', 'F8')],
            'central': [('C3', 'C4')],
            'parietal': [('P3', 'P4'), ('P7', 'P8')],
            'occipital': [('O1', 'O2')]
        }
        
        for region, pairs in hemisphere_pairs.items():
            region_asymmetries = []
            
            for left_ch, right_ch in pairs:
                if left_ch in self.channels and right_ch in self.channels:
                    left_idx = self.channels.index(left_ch)
                    right_idx = self.channels.index(right_ch)
                    
                    # Power asymmetry in alpha band
                    left_power = self._compute_band_power(data[left_idx, :], 8, 12)
                    right_power = self._compute_band_power(data[right_idx, :], 8, 12)
                    
                    if left_power + right_power > 0:
                        asymmetry_index = (right_power - left_power) / (right_power + left_power)
                        region_asymmetries.append(asymmetry_index)
            
            if region_asymmetries:
                asymmetry[f'{region}_asymmetry'] = np.mean(region_asymmetries)
        
        return asymmetry
    
    def _compute_band_power(self, data: np.ndarray, low_freq: float, high_freq: float) -> float:
        """Compute power in specific frequency band"""
        f, psd = welch(data, fs=self.sampling_rate, nperseg=256)
        band_mask = (f >= low_freq) & (f <= high_freq)
        return np.trapz(psd[band_mask], f[band_mask])
    
    def _assess_eeg_quality(self, data: np.ndarray) -> float:
        """Assess EEG signal quality"""
        quality_scores = []
        
        for ch_idx, channel in enumerate(self.channels):
            ch_data = data[ch_idx, :]
            
            # Check for saturation
            saturation_ratio = np.mean(np.abs(ch_data) > 100)  # μV
            
            # Check signal-to-noise ratio
            signal_power = np.var(ch_data)
            
            # Frequency content check
            f, psd = welch(ch_data, fs=self.sampling_rate, nperseg=256)
            
            # EEG should have most power in low frequencies
            low_freq_power = np.sum(psd[f <= 30])
            high_freq_power = np.sum(psd[f > 30])
            
            freq_ratio = low_freq_power / (high_freq_power + 1e-10)
            
            # Combined quality score
            ch_quality = (1 - saturation_ratio) * min(1.0, freq_ratio / 10.0) * min(1.0, signal_power / 100.0)
            quality_scores.append(max(0.0, ch_quality))
            
            self.channel_quality[channel] = ch_quality
        
        return np.mean(quality_scores)
    
    def _assess_epoch_quality(self, epoch_data: np.ndarray) -> float:
        """Assess quality of single epoch"""
        # Check for artifacts
        max_amplitude = np.max(np.abs(epoch_data))
        
        if max_amplitude > 150:  # μV - likely artifact
            return 0.2
        elif max_amplitude > 100:
            return 0.5
        else:
            return 1.0
    
    def get_channel_quality(self) -> Dict[str, float]:
        """Get quality scores for all channels"""
        return self.channel_quality.copy()
    
    def get_bad_channels(self) -> List[str]:
        """Get list of detected bad channels"""
        return self.bad_channels.copy()
    
    def reset_bad_channels(self):
        """Reset bad channel list"""
        self.bad_channels.clear()
        self.channel_quality.clear()