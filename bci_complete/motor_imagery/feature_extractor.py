"""
Motor Imagery Feature Extractor

Comprehensive feature extraction for motor imagery BCI including
spectral, temporal, and spatial features.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from scipy.signal import welch, coherence, hilbert
from scipy import stats
from sklearn.base import BaseEstimator, TransformerMixin

from ..core.config import BCIConfig


class MotorImageryFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Advanced feature extractor for motor imagery BCI
    
    Features extracted:
    - Band power features (mu, beta, gamma rhythms)
    - Spectral edge frequency and peak frequency
    - Relative band powers and ratios
    - Hemispheric asymmetry indices
    - Phase locking value (PLV)
    - Coherence features
    - Temporal complexity measures
    - Hjorth parameters
    """
    
    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.sampling_rate = config.device.sampling_rate
        self.channels = config.device.channels
        self.n_channels = len(self.channels)
        
        # Motor imagery specific frequency bands
        self.mi_bands = config.motor_imagery['frequency_bands']
        
        # Channel groups for motor imagery
        self.sensorimotor_channels = self._define_sensorimotor_channels()
        self.hemisphere_pairs = self._define_hemisphere_pairs()
        
        # Feature categories
        self.feature_categories = [
            'band_powers',
            'spectral_features', 
            'asymmetry_features',
            'connectivity_features',
            'temporal_features',
            'hjorth_parameters'
        ]
        
        self.logger.info("Motor Imagery Feature Extractor initialized")
    
    def _define_sensorimotor_channels(self) -> Dict[str, List[str]]:
        """Define sensorimotor channel groups"""
        sensorimotor = {
            'central': ['C3', 'Cz', 'C4'],
            'left_motor': ['C3', 'FC3', 'CP3'],
            'right_motor': ['C4', 'FC4', 'CP4'],
            'supplementary': ['FCz', 'Cz', 'CPz'],
            'all_motor': ['FC3', 'FC1', 'FCz', 'FC2', 'FC4',
                         'C3', 'C1', 'Cz', 'C2', 'C4',
                         'CP3', 'CP1', 'CPz', 'CP2', 'CP4']
        }
        
        # Filter channels that exist in our montage
        filtered_sensorimotor = {}
        for region, channels in sensorimotor.items():
            existing_channels = [ch for ch in channels if ch in self.channels]
            if existing_channels:
                filtered_sensorimotor[region] = existing_channels
        
        return filtered_sensorimotor
    
    def _define_hemisphere_pairs(self) -> List[Tuple[str, str]]:
        """Define left-right hemisphere channel pairs"""
        pairs = [
            ('C3', 'C4'),    # Primary motor cortex
            ('FC3', 'FC4'),  # Premotor cortex
            ('CP3', 'CP4'),  # Posterior parietal
            ('F3', 'F4'),    # Frontal
            ('P3', 'P4'),    # Parietal
        ]
        
        # Filter pairs where both channels exist
        existing_pairs = []
        for left, right in pairs:
            if left in self.channels and right in self.channels:
                existing_pairs.append((left, right))
        
        return existing_pairs
    
    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> 'MotorImageryFeatureExtractor':
        """Fit feature extractor (no parameters to learn)"""
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Extract motor imagery features from EEG data
        
        Parameters:
        X: EEG data (n_trials, n_channels, n_samples)
        
        Returns:
        Feature matrix (n_trials, n_features)
        """
        try:
            n_trials = X.shape[0]
            all_features = []
            
            for trial in range(n_trials):
                trial_data = X[trial, :, :]  # (n_channels, n_samples)
                trial_features = self.extract_trial_features(trial_data)
                all_features.append(trial_features)
            
            # Convert to feature matrix
            feature_matrix = self._features_to_matrix(all_features)
            
            self.logger.debug(f"Extracted {feature_matrix.shape[1]} features from {n_trials} trials")
            
            return feature_matrix
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {e}")
            raise
    
    def extract_trial_features(self, trial_data: np.ndarray) -> Dict[str, Any]:
        """Extract all features from single trial"""
        features = {}
        
        # Band power features
        features.update(self._extract_band_power_features(trial_data))
        
        # Spectral features
        features.update(self._extract_spectral_features(trial_data))
        
        # Asymmetry features
        features.update(self._extract_asymmetry_features(trial_data))
        
        # Connectivity features
        features.update(self._extract_connectivity_features(trial_data))
        
        # Temporal features
        features.update(self._extract_temporal_features(trial_data))
        
        # Hjorth parameters
        features.update(self._extract_hjorth_parameters(trial_data))
        
        return features
    
    def _extract_band_power_features(self, data: np.ndarray) -> Dict[str, float]:
        """Extract band power features"""
        features = {}
        
        # Extract for sensorimotor channels
        for region, channels in self.sensorimotor_channels.items():
            region_powers = {}
            
            for channel in channels:
                if channel in self.channels:
                    ch_idx = self.channels.index(channel)
                    ch_data = data[ch_idx, :]
                    
                    # Compute PSD
                    f, psd = welch(ch_data, fs=self.sampling_rate, nperseg=256)
                    
                    # Extract band powers
                    for band_name, (low_freq, high_freq) in self.mi_bands.items():
                        band_mask = (f >= low_freq) & (f <= high_freq)
                        band_power = np.trapz(psd[band_mask], f[band_mask])
                        
                        feature_name = f'{region}_{channel}_{band_name}_power'
                        features[feature_name] = float(band_power)
                        
                        # Store for region averaging
                        if band_name not in region_powers:
                            region_powers[band_name] = []
                        region_powers[band_name].append(band_power)
            
            # Average band powers across region
            for band_name, powers in region_powers.items():
                if powers:
                    features[f'{region}_avg_{band_name}_power'] = float(np.mean(powers))
                    features[f'{region}_std_{band_name}_power'] = float(np.std(powers))
        
        # Compute relative band powers
        features.update(self._compute_relative_band_powers(features))
        
        # Compute band power ratios
        features.update(self._compute_band_power_ratios(features))
        
        return features
    
    def _compute_relative_band_powers(self, band_features: Dict[str, float]) -> Dict[str, float]:
        """Compute relative band powers (normalized by total power)"""
        relative_features = {}
        
        # Group features by channel and region
        power_groups = {}
        
        for feature_name, value in band_features.items():
            if '_power' in feature_name and 'avg' not in feature_name:
                # Parse feature name: region_channel_band_power
                parts = feature_name.split('_')
                if len(parts) >= 4:
                    region_channel = '_'.join(parts[:-2])
                    band = parts[-2]
                    
                    if region_channel not in power_groups:
                        power_groups[region_channel] = {}
                    power_groups[region_channel][band] = value
        
        # Compute relative powers
        for region_channel, band_powers in power_groups.items():
            total_power = sum(band_powers.values())
            
            if total_power > 0:
                for band, power in band_powers.items():
                    rel_feature_name = f'{region_channel}_{band}_rel_power'
                    relative_features[rel_feature_name] = float(power / total_power)
        
        return relative_features
    
    def _compute_band_power_ratios(self, band_features: Dict[str, float]) -> Dict[str, float]:
        """Compute important band power ratios for motor imagery"""
        ratio_features = {}
        
        # Common motor imagery ratios
        ratio_pairs = [
            ('mu', 'beta'),     # Mu/Beta ratio
            ('beta', 'gamma'),  # Beta/Gamma ratio
            ('mu', 'gamma'),    # Mu/Gamma ratio
        ]
        
        # Extract ratios for each sensorimotor region
        for region in self.sensorimotor_channels.keys():
            for band1, band2 in ratio_pairs:
                feature1 = f'{region}_avg_{band1}_power'
                feature2 = f'{region}_avg_{band2}_power'
                
                if feature1 in band_features and feature2 in band_features:
                    power1 = band_features[feature1]
                    power2 = band_features[feature2]
                    
                    if power2 > 0:
                        ratio = power1 / power2
                        ratio_features[f'{region}_{band1}_{band2}_ratio'] = float(ratio)
        
        return ratio_features
    
    def _extract_spectral_features(self, data: np.ndarray) -> Dict[str, float]:
        """Extract spectral features"""
        features = {}
        
        for region, channels in self.sensorimotor_channels.items():
            spectral_metrics = []
            
            for channel in channels:
                if channel in self.channels:
                    ch_idx = self.channels.index(channel)
                    ch_data = data[ch_idx, :]
                    
                    # Compute PSD
                    f, psd = welch(ch_data, fs=self.sampling_rate, nperseg=256)
                    
                    # Peak frequency in motor imagery bands
                    mi_mask = (f >= 8) & (f <= 30)  # Mu + Beta bands
                    if np.any(mi_mask):
                        peak_freq_idx = np.argmax(psd[mi_mask])
                        peak_freq = f[mi_mask][peak_freq_idx]
                        features[f'{channel}_peak_freq'] = float(peak_freq)
                        spectral_metrics.append(peak_freq)
                    
                    # Spectral edge frequency (95% power)
                    cumsum_psd = np.cumsum(psd)
                    total_power = cumsum_psd[-1]
                    edge_95_idx = np.where(cumsum_psd >= 0.95 * total_power)[0]
                    
                    if len(edge_95_idx) > 0:
                        edge_freq = f[edge_95_idx[0]]
                        features[f'{channel}_spectral_edge_95'] = float(edge_freq)
                    
                    # Spectral centroid
                    spectral_centroid = np.sum(f * psd) / np.sum(psd)
                    features[f'{channel}_spectral_centroid'] = float(spectral_centroid)
                    
                    # Spectral entropy
                    norm_psd = psd / np.sum(psd)
                    spectral_entropy = -np.sum(norm_psd * np.log2(norm_psd + 1e-10))
                    features[f'{channel}_spectral_entropy'] = float(spectral_entropy)
            
            # Region averages
            if spectral_metrics:
                features[f'{region}_avg_peak_freq'] = float(np.mean(spectral_metrics))
                features[f'{region}_std_peak_freq'] = float(np.std(spectral_metrics))
        
        return features
    
    def _extract_asymmetry_features(self, data: np.ndarray) -> Dict[str, float]:
        """Extract hemispheric asymmetry features"""
        features = {}
        
        for left_ch, right_ch in self.hemisphere_pairs:
            left_idx = self.channels.index(left_ch)
            right_idx = self.channels.index(right_ch)
            
            left_data = data[left_idx, :]
            right_data = data[right_idx, :]
            
            # Band power asymmetries
            for band_name, (low_freq, high_freq) in self.mi_bands.items():
                # Compute band powers
                f_left, psd_left = welch(left_data, fs=self.sampling_rate, nperseg=256)
                f_right, psd_right = welch(right_data, fs=self.sampling_rate, nperseg=256)
                
                band_mask = (f_left >= low_freq) & (f_left <= high_freq)
                
                left_power = np.trapz(psd_left[band_mask], f_left[band_mask])
                right_power = np.trapz(psd_right[band_mask], f_right[band_mask])
                
                # Asymmetry index: (Right - Left) / (Right + Left)
                if left_power + right_power > 0:
                    asymmetry = (right_power - left_power) / (right_power + left_power)
                    features[f'{left_ch}_{right_ch}_{band_name}_asymmetry'] = float(asymmetry)
                
                # Log ratio: log(Right/Left)
                if left_power > 0 and right_power > 0:
                    log_ratio = np.log(right_power / left_power)
                    features[f'{left_ch}_{right_ch}_{band_name}_log_ratio'] = float(log_ratio)
        
        return features
    
    def _extract_connectivity_features(self, data: np.ndarray) -> Dict[str, float]:
        """Extract connectivity features"""
        features = {}
        
        # Coherence between hemisphere pairs
        for left_ch, right_ch in self.hemisphere_pairs:
            left_idx = self.channels.index(left_ch)
            right_idx = self.channels.index(right_ch)
            
            left_data = data[left_idx, :]
            right_data = data[right_idx, :]
            
            # Compute coherence
            f, coh = coherence(left_data, right_data, fs=self.sampling_rate, nperseg=256)
            
            # Average coherence in motor imagery bands
            for band_name, (low_freq, high_freq) in self.mi_bands.items():
                band_mask = (f >= low_freq) & (f <= high_freq)
                
                if np.any(band_mask):
                    avg_coherence = np.mean(coh[band_mask])
                    features[f'{left_ch}_{right_ch}_{band_name}_coherence'] = float(avg_coherence)
        
        # Phase locking value (PLV) for central channels
        central_channels = [ch for ch in ['C3', 'Cz', 'C4'] if ch in self.channels]
        
        if len(central_channels) >= 2:
            for i, ch1 in enumerate(central_channels):
                for ch2 in central_channels[i+1:]:
                    ch1_idx = self.channels.index(ch1)
                    ch2_idx = self.channels.index(ch2)
                    
                    # Compute PLV
                    plv = self._compute_plv(data[ch1_idx, :], data[ch2_idx, :])
                    features[f'{ch1}_{ch2}_plv'] = float(plv)
        
        return features
    
    def _compute_plv(self, signal1: np.ndarray, signal2: np.ndarray) -> float:
        """Compute Phase Locking Value between two signals"""
        try:
            # Get analytic signals
            analytic1 = hilbert(signal1)
            analytic2 = hilbert(signal2)
            
            # Extract phases
            phase1 = np.angle(analytic1)
            phase2 = np.angle(analytic2)
            
            # Phase difference
            phase_diff = phase1 - phase2
            
            # PLV calculation
            plv = np.abs(np.mean(np.exp(1j * phase_diff)))
            
            return plv
            
        except Exception:
            return 0.0
    
    def _extract_temporal_features(self, data: np.ndarray) -> Dict[str, float]:
        """Extract temporal complexity features"""
        features = {}
        
        for region, channels in self.sensorimotor_channels.items():
            complexity_metrics = []
            
            for channel in channels:
                if channel in self.channels:
                    ch_idx = self.channels.index(channel)
                    ch_data = data[ch_idx, :]
                    
                    # Zero crossings
                    zero_crossings = len(np.where(np.diff(np.sign(ch_data)))[0])
                    features[f'{channel}_zero_crossings'] = float(zero_crossings)
                    
                    # Line length (total variation)
                    line_length = np.sum(np.abs(np.diff(ch_data)))
                    features[f'{channel}_line_length'] = float(line_length)
                    
                    # Petrosian fractal dimension
                    petrosian_fd = self._petrosian_fractal_dimension(ch_data)
                    features[f'{channel}_petrosian_fd'] = float(petrosian_fd)
                    complexity_metrics.append(petrosian_fd)
                    
                    # Katz fractal dimension
                    katz_fd = self._katz_fractal_dimension(ch_data)
                    features[f'{channel}_katz_fd'] = float(katz_fd)
            
            # Region averages
            if complexity_metrics:
                features[f'{region}_avg_complexity'] = float(np.mean(complexity_metrics))
        
        return features
    
    def _petrosian_fractal_dimension(self, signal: np.ndarray) -> float:
        """Compute Petrosian fractal dimension"""
        try:
            N = len(signal)
            
            # Count sign changes in first derivative
            diff_signal = np.diff(signal)
            sign_changes = len(np.where(np.diff(np.sign(diff_signal)))[0])
            
            # Petrosian FD formula
            if sign_changes > 0:
                petrosian_fd = np.log10(N) / (np.log10(N) + np.log10(N / (N + 0.4 * sign_changes)))
            else:
                petrosian_fd = 1.0
            
            return petrosian_fd
            
        except Exception:
            return 1.0
    
    def _katz_fractal_dimension(self, signal: np.ndarray) -> float:
        """Compute Katz fractal dimension"""
        try:
            N = len(signal)
            
            # Compute distances
            dists = np.abs(np.diff(signal))
            L = np.sum(dists)  # Total length
            
            if L == 0:
                return 1.0
            
            # Maximum distance
            d = np.max(np.abs(signal - signal[0]))
            
            if d == 0:
                return 1.0
            
            # Katz FD formula
            katz_fd = np.log10(N - 1) / (np.log10(N - 1) + np.log10(d / L))
            
            return katz_fd
            
        except Exception:
            return 1.0
    
    def _extract_hjorth_parameters(self, data: np.ndarray) -> Dict[str, float]:
        """Extract Hjorth parameters (Activity, Mobility, Complexity)"""
        features = {}
        
        for region, channels in self.sensorimotor_channels.items():
            hjorth_metrics = {'activity': [], 'mobility': [], 'complexity': []}
            
            for channel in channels:
                if channel in self.channels:
                    ch_idx = self.channels.index(channel)
                    ch_data = data[ch_idx, :]
                    
                    # Compute Hjorth parameters
                    activity, mobility, complexity = self._compute_hjorth_parameters(ch_data)
                    
                    features[f'{channel}_hjorth_activity'] = float(activity)
                    features[f'{channel}_hjorth_mobility'] = float(mobility)
                    features[f'{channel}_hjorth_complexity'] = float(complexity)
                    
                    hjorth_metrics['activity'].append(activity)
                    hjorth_metrics['mobility'].append(mobility)
                    hjorth_metrics['complexity'].append(complexity)
            
            # Region averages
            for param_name, values in hjorth_metrics.items():
                if values:
                    features[f'{region}_avg_hjorth_{param_name}'] = float(np.mean(values))
        
        return features
    
    def _compute_hjorth_parameters(self, signal: np.ndarray) -> Tuple[float, float, float]:
        """Compute Hjorth parameters for a signal"""
        try:
            # First and second derivatives
            first_deriv = np.diff(signal)
            second_deriv = np.diff(first_deriv)
            
            # Variances
            var_signal = np.var(signal)
            var_first_deriv = np.var(first_deriv)
            var_second_deriv = np.var(second_deriv)
            
            # Activity (variance of signal)
            activity = var_signal
            
            # Mobility (square root of variance ratio)
            if var_signal > 0:
                mobility = np.sqrt(var_first_deriv / var_signal)
            else:
                mobility = 0.0
            
            # Complexity
            if var_first_deriv > 0 and mobility > 0:
                complexity = np.sqrt(var_second_deriv / var_first_deriv) / mobility
            else:
                complexity = 0.0
            
            return activity, mobility, complexity
            
        except Exception:
            return 0.0, 0.0, 0.0
    
    def _features_to_matrix(self, feature_list: List[Dict[str, Any]]) -> np.ndarray:
        """Convert list of feature dictionaries to matrix"""
        if not feature_list:
            return np.array([])
        
        # Get all feature names (use first trial as reference)
        feature_names = list(feature_list[0].keys())
        
        # Create feature matrix
        n_trials = len(feature_list)
        n_features = len(feature_names)
        
        feature_matrix = np.zeros((n_trials, n_features))
        
        for trial_idx, features in enumerate(feature_list):
            for feat_idx, feat_name in enumerate(feature_names):
                value = features.get(feat_name, 0.0)
                
                # Handle non-numeric values
                if isinstance(value, (int, float)) and not np.isnan(value):
                    feature_matrix[trial_idx, feat_idx] = value
                else:
                    feature_matrix[trial_idx, feat_idx] = 0.0
        
        # Store feature names for reference
        self.feature_names_ = feature_names
        
        return feature_matrix
    
    def get_feature_names(self) -> List[str]:
        """Get names of extracted features"""
        return getattr(self, 'feature_names_', [])
    
    def get_feature_categories(self) -> Dict[str, List[str]]:
        """Get features grouped by category"""
        if not hasattr(self, 'feature_names_'):
            return {}
        
        categories = {}
        
        for category in self.feature_categories:
            category_features = []
            
            for feat_name in self.feature_names_:
                if any(keyword in feat_name.lower() for keyword in self._get_category_keywords(category)):
                    category_features.append(feat_name)
            
            if category_features:
                categories[category] = category_features
        
        return categories
    
    def _get_category_keywords(self, category: str) -> List[str]:
        """Get keywords for feature categories"""
        keywords_map = {
            'band_powers': ['power', 'rel_power', 'ratio'],
            'spectral_features': ['peak_freq', 'spectral_edge', 'spectral_centroid', 'spectral_entropy'],
            'asymmetry_features': ['asymmetry', 'log_ratio'],
            'connectivity_features': ['coherence', 'plv'],
            'temporal_features': ['zero_crossings', 'line_length', 'petrosian_fd', 'katz_fd'],
            'hjorth_parameters': ['hjorth']
        }
        
        return keywords_map.get(category, [])