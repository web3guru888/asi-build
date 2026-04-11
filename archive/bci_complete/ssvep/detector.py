"""
SSVEP Detector

Advanced SSVEP detection using multiple frequency analysis methods
including CCA, FBCCA, and machine learning approaches.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from scipy.signal import welch, hilbert, coherence
from scipy.stats import pearsonr
from sklearn.cross_decomposition import CCA
from sklearn.preprocessing import StandardScaler

from ..core.config import BCIConfig


@dataclass
class SSVEPDetection:
    """SSVEP detection result"""
    detected_frequency: float
    confidence: float
    snr: float
    power_spectrum: Dict[str, float]
    method_scores: Dict[str, float]
    harmonics_detected: List[float]
    processing_time: float


class SSVEPDetector:
    """
    Steady-State Visual Evoked Potential (SSVEP) detector
    
    Methods:
    - Power Spectral Density (PSD) analysis
    - Canonical Correlation Analysis (CCA)
    - Filter Bank CCA (FBCCA)
    - Multivariate Synchronization Index (MSI)
    - Machine learning classification
    """
    
    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.sampling_rate = config.device.sampling_rate
        self.channels = config.device.channels
        
        # SSVEP configuration
        self.ssvep_config = config.ssvep
        self.target_frequencies = self.ssvep_config['frequencies']
        self.harmonics = self.ssvep_config['harmonics']
        self.window_length = self.ssvep_config['window_length']
        self.target_channels = self._get_target_channels()
        
        # Reference signals for CCA
        self.reference_signals = self._generate_reference_signals()
        
        # CCA models
        self.cca_models = {}
        self.fbcca_models = {}
        
        # Filter bank
        self.filter_bank = self._design_filter_bank()
        
        # Detection parameters
        self.min_snr_threshold = 3.0  # Minimum SNR for detection
        self.confidence_threshold = 0.7
        
        self.logger.info(f"SSVEP Detector initialized for frequencies: {self.target_frequencies} Hz")
    
    def _get_target_channels(self) -> List[str]:
        """Get occipital channels for SSVEP"""
        # Prioritize occipital channels
        target_chs = self.ssvep_config.get('target_channels', ['O1', 'O2', 'Oz'])
        
        # Filter channels that exist in montage
        available_channels = [ch for ch in target_chs if ch in self.channels]
        
        # Add additional occipital channels if available
        additional_channels = ['PO3', 'PO4', 'POz', 'P7', 'P8']
        for ch in additional_channels:
            if ch in self.channels and ch not in available_channels:
                available_channels.append(ch)
        
        if not available_channels:
            self.logger.warning("No occipital channels found, using all channels")
            available_channels = self.channels
        
        return available_channels
    
    def _generate_reference_signals(self) -> Dict[float, np.ndarray]:
        """Generate reference signals for CCA"""
        reference_signals = {}
        
        n_samples = int(self.window_length * self.sampling_rate)
        t = np.arange(n_samples) / self.sampling_rate
        
        for freq in self.target_frequencies:
            # Generate sine and cosine at fundamental and harmonics
            n_harmonics = len(self.harmonics) + 1  # Include fundamental
            n_signals = n_harmonics * 2  # Sine and cosine for each harmonic
            
            ref_signal = np.zeros((n_signals, n_samples))
            
            signal_idx = 0
            
            # Fundamental frequency
            ref_signal[signal_idx, :] = np.sin(2 * np.pi * freq * t)
            ref_signal[signal_idx + 1, :] = np.cos(2 * np.pi * freq * t)
            signal_idx += 2
            
            # Harmonics
            for harmonic in self.harmonics:
                harmonic_freq = freq * harmonic
                if harmonic_freq < self.sampling_rate / 2:  # Nyquist limit
                    ref_signal[signal_idx, :] = np.sin(2 * np.pi * harmonic_freq * t)
                    ref_signal[signal_idx + 1, :] = np.cos(2 * np.pi * harmonic_freq * t)
                signal_idx += 2
            
            reference_signals[freq] = ref_signal
        
        return reference_signals
    
    def _design_filter_bank(self) -> List[Tuple[float, float]]:
        """Design filter bank for FBCCA"""
        filter_bank = []
        
        for freq in self.target_frequencies:
            # Narrow band around each target frequency
            bandwidth = 2.0  # Hz
            low_freq = max(1.0, freq - bandwidth/2)
            high_freq = min(self.sampling_rate/2 - 1, freq + bandwidth/2)
            
            filter_bank.append((low_freq, high_freq))
            
            # Add harmonic bands
            for harmonic in self.harmonics:
                harmonic_freq = freq * harmonic
                if harmonic_freq < self.sampling_rate / 2 - bandwidth:
                    h_low = harmonic_freq - bandwidth/2
                    h_high = harmonic_freq + bandwidth/2
                    filter_bank.append((h_low, h_high))
        
        return filter_bank
    
    def detect(self, eeg_data: np.ndarray) -> SSVEPDetection:
        """
        Detect SSVEP response in EEG data
        
        Parameters:
        eeg_data: EEG data (n_channels, n_samples)
        
        Returns:
        SSVEP detection result
        """
        start_time = time.time()
        
        try:
            # Extract target channels
            target_data = self._extract_target_data(eeg_data)
            
            if target_data is None:
                raise ValueError("No target channels available")
            
            # Apply different detection methods
            method_scores = {}
            
            # Method 1: Power spectral density
            psd_scores = self._psd_detection(target_data)
            method_scores['psd'] = psd_scores
            
            # Method 2: Canonical correlation analysis
            cca_scores = self._cca_detection(target_data)
            method_scores['cca'] = cca_scores
            
            # Method 3: Filter bank CCA
            fbcca_scores = self._fbcca_detection(target_data)
            method_scores['fbcca'] = fbcca_scores
            
            # Method 4: Multivariate synchronization index
            msi_scores = self._msi_detection(target_data)
            method_scores['msi'] = msi_scores
            
            # Combine scores and make decision
            final_scores = self._combine_method_scores(method_scores)
            
            # Find best frequency
            best_freq, confidence = self._select_best_frequency(final_scores)
            
            # Calculate additional metrics
            snr = self._calculate_snr(target_data, best_freq)
            power_spectrum = self._calculate_power_spectrum(target_data)
            harmonics = self._detect_harmonics(target_data, best_freq)
            
            processing_time = time.time() - start_time
            
            detection_result = SSVEPDetection(
                detected_frequency=best_freq,
                confidence=confidence,
                snr=snr,
                power_spectrum=power_spectrum,
                method_scores=method_scores,
                harmonics_detected=harmonics,
                processing_time=processing_time
            )
            
            return detection_result
            
        except Exception as e:
            self.logger.error(f"SSVEP detection failed: {e}")
            # Return default result
            return SSVEPDetection(
                detected_frequency=0.0,
                confidence=0.0,
                snr=0.0,
                power_spectrum={},
                method_scores={},
                harmonics_detected=[],
                processing_time=time.time() - start_time
            )
    
    def _extract_target_data(self, eeg_data: np.ndarray) -> Optional[np.ndarray]:
        """Extract data from target channels"""
        target_indices = []
        
        for ch in self.target_channels:
            if ch in self.channels:
                target_indices.append(self.channels.index(ch))
        
        if not target_indices:
            return None
        
        return eeg_data[target_indices, :]
    
    def _psd_detection(self, data: np.ndarray) -> Dict[float, float]:
        """Power spectral density based detection"""
        scores = {}
        
        for ch_idx in range(data.shape[0]):
            ch_data = data[ch_idx, :]
            
            # Compute PSD
            f, psd = welch(ch_data, fs=self.sampling_rate, nperseg=256)
            
            # Score each target frequency
            for freq in self.target_frequencies:
                # Find closest frequency bin
                freq_idx = np.argmin(np.abs(f - freq))
                
                # Extract power at target frequency and neighbors
                freq_range = 3  # bins
                start_idx = max(0, freq_idx - freq_range // 2)
                end_idx = min(len(psd), freq_idx + freq_range // 2 + 1)
                
                target_power = np.mean(psd[start_idx:end_idx])
                
                # Calculate signal-to-noise ratio
                # Noise estimation from neighboring frequencies
                noise_bands = []
                
                # Lower noise band
                noise_start = max(0, start_idx - freq_range * 2)
                noise_end = start_idx
                if noise_end > noise_start:
                    noise_bands.append(psd[noise_start:noise_end])
                
                # Upper noise band
                noise_start = end_idx
                noise_end = min(len(psd), end_idx + freq_range * 2)
                if noise_end > noise_start:
                    noise_bands.append(psd[noise_start:noise_end])
                
                if noise_bands:
                    noise_power = np.mean(np.concatenate(noise_bands))
                    snr = target_power / (noise_power + 1e-10)
                else:
                    snr = 1.0
                
                # Store score (average across channels)
                if freq not in scores:
                    scores[freq] = []
                scores[freq].append(snr)
        
        # Average across channels
        for freq in scores:
            scores[freq] = np.mean(scores[freq])
        
        return scores
    
    def _cca_detection(self, data: np.ndarray) -> Dict[float, float]:
        """Canonical correlation analysis detection"""
        scores = {}
        
        for freq in self.target_frequencies:
            # Get reference signal for this frequency
            ref_signal = self.reference_signals[freq]
            
            # Ensure data length matches reference
            n_samples = min(data.shape[1], ref_signal.shape[1])
            data_segment = data[:, :n_samples]
            ref_segment = ref_signal[:, :n_samples]
            
            try:
                # Apply CCA
                cca = CCA(n_components=1)
                
                # Fit CCA
                data_cca, ref_cca = cca.fit_transform(data_segment.T, ref_segment.T)
                
                # Calculate correlation coefficient
                correlation, _ = pearsonr(data_cca.flatten(), ref_cca.flatten())
                
                # Store squared correlation as score
                scores[freq] = correlation ** 2
                
            except Exception as e:
                self.logger.warning(f"CCA failed for {freq} Hz: {e}")
                scores[freq] = 0.0
        
        return scores
    
    def _fbcca_detection(self, data: np.ndarray) -> Dict[float, float]:
        """Filter bank CCA detection"""
        scores = {}
        
        for freq in self.target_frequencies:
            freq_scores = []
            
            # Apply each filter in the bank
            for low_freq, high_freq in self.filter_bank:
                # Check if this filter is relevant for current frequency
                if (low_freq <= freq <= high_freq or 
                    any(low_freq <= freq * h <= high_freq for h in self.harmonics)):
                    
                    # Filter data
                    filtered_data = self._apply_bandpass_filter(data, low_freq, high_freq)
                    
                    # Apply CCA with filtered data
                    ref_signal = self.reference_signals[freq]
                    
                    n_samples = min(filtered_data.shape[1], ref_signal.shape[1])
                    data_segment = filtered_data[:, :n_samples]
                    ref_segment = ref_signal[:, :n_samples]
                    
                    try:
                        cca = CCA(n_components=1)
                        data_cca, ref_cca = cca.fit_transform(data_segment.T, ref_segment.T)
                        
                        correlation, _ = pearsonr(data_cca.flatten(), ref_cca.flatten())
                        freq_scores.append(correlation ** 2)
                        
                    except Exception:
                        freq_scores.append(0.0)
            
            # Combine scores from different filters
            if freq_scores:
                scores[freq] = np.max(freq_scores)  # Take best filter
            else:
                scores[freq] = 0.0
        
        return scores
    
    def _msi_detection(self, data: np.ndarray) -> Dict[float, float]:
        """Multivariate synchronization index detection"""
        scores = {}
        
        for freq in self.target_frequencies:
            try:
                # Generate template signal
                n_samples = data.shape[1]
                t = np.arange(n_samples) / self.sampling_rate
                template = np.sin(2 * np.pi * freq * t)
                
                # Calculate phase synchronization
                sync_indices = []
                
                for ch_idx in range(data.shape[0]):
                    ch_data = data[ch_idx, :]
                    
                    # Get analytic signals
                    analytic_data = hilbert(ch_data)
                    analytic_template = hilbert(template)
                    
                    # Extract phases
                    phase_data = np.angle(analytic_data)
                    phase_template = np.angle(analytic_template)
                    
                    # Phase difference
                    phase_diff = phase_data - phase_template
                    
                    # Synchronization index
                    sync_index = np.abs(np.mean(np.exp(1j * phase_diff)))
                    sync_indices.append(sync_index)
                
                # Average across channels
                scores[freq] = np.mean(sync_indices)
                
            except Exception as e:
                self.logger.warning(f"MSI calculation failed for {freq} Hz: {e}")
                scores[freq] = 0.0
        
        return scores
    
    def _apply_bandpass_filter(self, data: np.ndarray, low_freq: float, high_freq: float) -> np.ndarray:
        """Apply bandpass filter to data"""
        from scipy.signal import butter, filtfilt
        
        nyquist = self.sampling_rate / 2
        low = low_freq / nyquist
        high = high_freq / nyquist
        
        # Ensure valid frequency range
        low = max(0.01, min(0.99, low))
        high = max(low + 0.01, min(0.99, high))
        
        try:
            b, a = butter(4, [low, high], btype='band')
            
            filtered_data = np.zeros_like(data)
            for ch in range(data.shape[0]):
                filtered_data[ch, :] = filtfilt(b, a, data[ch, :])
            
            return filtered_data
            
        except Exception as e:
            self.logger.warning(f"Filtering failed: {e}")
            return data
    
    def _combine_method_scores(self, method_scores: Dict[str, Dict[float, float]]) -> Dict[float, float]:
        """Combine scores from different methods"""
        combined_scores = {}
        
        # Weight for each method
        method_weights = {
            'psd': 0.2,
            'cca': 0.3,
            'fbcca': 0.4,
            'msi': 0.1
        }
        
        for freq in self.target_frequencies:
            combined_score = 0.0
            total_weight = 0.0
            
            for method, weight in method_weights.items():
                if method in method_scores and freq in method_scores[method]:
                    combined_score += weight * method_scores[method][freq]
                    total_weight += weight
            
            if total_weight > 0:
                combined_scores[freq] = combined_score / total_weight
            else:
                combined_scores[freq] = 0.0
        
        return combined_scores
    
    def _select_best_frequency(self, scores: Dict[float, float]) -> Tuple[float, float]:
        """Select best frequency and confidence"""
        if not scores:
            return 0.0, 0.0
        
        # Find frequency with highest score
        best_freq = max(scores.keys(), key=lambda f: scores[f])
        best_score = scores[best_freq]
        
        # Calculate confidence based on score separation
        sorted_scores = sorted(scores.values(), reverse=True)
        
        if len(sorted_scores) > 1:
            # Confidence based on difference between best and second best
            confidence = (sorted_scores[0] - sorted_scores[1]) / (sorted_scores[0] + 1e-10)
        else:
            confidence = best_score
        
        # Normalize confidence to [0, 1]
        confidence = min(1.0, max(0.0, confidence))
        
        return best_freq, confidence
    
    def _calculate_snr(self, data: np.ndarray, target_freq: float) -> float:
        """Calculate signal-to-noise ratio at target frequency"""
        if target_freq == 0.0:
            return 0.0
        
        try:
            # Average across channels
            avg_data = np.mean(data, axis=0)
            
            # Compute PSD
            f, psd = welch(avg_data, fs=self.sampling_rate, nperseg=256)
            
            # Find target frequency bin
            freq_idx = np.argmin(np.abs(f - target_freq))
            
            # Signal power (target frequency ± 1 Hz)
            freq_range = max(1, int(2 * len(f) / (f[-1] - f[0])))  # ±1 Hz
            start_idx = max(0, freq_idx - freq_range // 2)
            end_idx = min(len(psd), freq_idx + freq_range // 2 + 1)
            
            signal_power = np.mean(psd[start_idx:end_idx])
            
            # Noise power (exclude signal band)
            noise_mask = np.ones(len(psd), dtype=bool)
            noise_mask[start_idx:end_idx] = False
            
            if np.any(noise_mask):
                noise_power = np.mean(psd[noise_mask])
                snr = signal_power / (noise_power + 1e-10)
            else:
                snr = 1.0
            
            return float(snr)
            
        except Exception as e:
            self.logger.error(f"SNR calculation failed: {e}")
            return 0.0
    
    def _calculate_power_spectrum(self, data: np.ndarray) -> Dict[str, float]:
        """Calculate power spectrum for target frequencies"""
        power_spectrum = {}
        
        try:
            # Average across channels
            avg_data = np.mean(data, axis=0)
            
            # Compute PSD
            f, psd = welch(avg_data, fs=self.sampling_rate, nperseg=256)
            
            # Extract power at each target frequency
            for freq in self.target_frequencies:
                freq_idx = np.argmin(np.abs(f - freq))
                power_spectrum[f'{freq}Hz'] = float(psd[freq_idx])
            
        except Exception as e:
            self.logger.error(f"Power spectrum calculation failed: {e}")
        
        return power_spectrum
    
    def _detect_harmonics(self, data: np.ndarray, fundamental_freq: float) -> List[float]:
        """Detect harmonics of fundamental frequency"""
        if fundamental_freq == 0.0:
            return []
        
        detected_harmonics = []
        
        try:
            # Average across channels
            avg_data = np.mean(data, axis=0)
            
            # Compute PSD
            f, psd = welch(avg_data, fs=self.sampling_rate, nperseg=256)
            
            # Check each harmonic
            for harmonic in self.harmonics:
                harmonic_freq = fundamental_freq * harmonic
                
                if harmonic_freq < self.sampling_rate / 2:
                    # Find harmonic frequency bin
                    freq_idx = np.argmin(np.abs(f - harmonic_freq))
                    
                    # Check if harmonic is prominent
                    harmonic_power = psd[freq_idx]
                    
                    # Compare with neighboring frequencies
                    neighbor_range = 3
                    start_idx = max(0, freq_idx - neighbor_range)
                    end_idx = min(len(psd), freq_idx + neighbor_range + 1)
                    
                    # Exclude the harmonic bin itself
                    neighbor_powers = np.concatenate([
                        psd[start_idx:freq_idx],
                        psd[freq_idx+1:end_idx]
                    ])
                    
                    if len(neighbor_powers) > 0:
                        avg_neighbor_power = np.mean(neighbor_powers)
                        
                        # If harmonic power is significantly higher
                        if harmonic_power > 2 * avg_neighbor_power:
                            detected_harmonics.append(harmonic_freq)
            
        except Exception as e:
            self.logger.error(f"Harmonic detection failed: {e}")
        
        return detected_harmonics
    
    def calibrate(self, 
                 calibration_data: List[Tuple[np.ndarray, float]],
                 method: str = 'cca') -> Dict[str, Any]:
        """
        Calibrate SSVEP detector with training data
        
        Parameters:
        calibration_data: List of (eeg_data, target_frequency) tuples
        method: Calibration method ('cca', 'fbcca', or 'ml')
        """
        try:
            self.logger.info(f"Calibrating SSVEP detector with {len(calibration_data)} trials")
            
            if method == 'cca':
                return self._calibrate_cca(calibration_data)
            elif method == 'fbcca':
                return self._calibrate_fbcca(calibration_data)
            elif method == 'ml':
                return self._calibrate_ml(calibration_data)
            else:
                raise ValueError(f"Unknown calibration method: {method}")
                
        except Exception as e:
            self.logger.error(f"SSVEP calibration failed: {e}")
            raise
    
    def _calibrate_cca(self, calibration_data: List[Tuple[np.ndarray, float]]) -> Dict[str, Any]:
        """Calibrate CCA models"""
        # For now, CCA uses pre-generated reference signals
        # Could optimize reference signals based on calibration data
        
        accuracy_scores = []
        
        for eeg_data, true_freq in calibration_data:
            detection = self.detect(eeg_data)
            predicted_freq = detection.detected_frequency
            
            # Check if prediction is correct (within tolerance)
            tolerance = 0.5  # Hz
            is_correct = abs(predicted_freq - true_freq) <= tolerance
            accuracy_scores.append(is_correct)
        
        accuracy = np.mean(accuracy_scores)
        
        return {
            'method': 'cca',
            'accuracy': float(accuracy),
            'calibration_trials': len(calibration_data),
            'target_frequencies': self.target_frequencies
        }
    
    def _calibrate_fbcca(self, calibration_data: List[Tuple[np.ndarray, float]]) -> Dict[str, Any]:
        """Calibrate Filter Bank CCA"""
        # Similar to CCA but could optimize filter bank parameters
        return self._calibrate_cca(calibration_data)
    
    def _calibrate_ml(self, calibration_data: List[Tuple[np.ndarray, float]]) -> Dict[str, Any]:
        """Calibrate machine learning classifier"""
        # This would train a supervised classifier
        # For now, return basic calibration
        return self._calibrate_cca(calibration_data)