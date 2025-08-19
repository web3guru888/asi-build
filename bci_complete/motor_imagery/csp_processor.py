"""
Common Spatial Patterns (CSP) Processor

Advanced CSP implementation for motor imagery classification including
filter bank CSP and regularized CSP variants.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from scipy import linalg
from scipy.signal import butter, filtfilt
from sklearn.base import BaseEstimator, TransformerMixin

from ..core.config import BCIConfig


class CSPProcessor(BaseEstimator, TransformerMixin):
    """
    Common Spatial Patterns processor for motor imagery BCI
    
    Features:
    - Multi-class CSP (One-vs-Rest and One-vs-One)
    - Filter Bank CSP (FBCSP) for automatic frequency selection
    - Regularized CSP for improved generalization
    - Subject-specific and subject-independent modes
    """
    
    def __init__(self, config: BCIConfig, n_components: int = 4, 
                 reg_param: float = 0.1, filter_bank: bool = True):
        self.config = config
        self.n_components = n_components
        self.reg_param = reg_param
        self.filter_bank = filter_bank
        self.logger = logging.getLogger(__name__)
        
        # CSP parameters
        self.filters_ = None
        self.patterns_ = None
        self.eigenvalues_ = None
        self.classes_ = None
        
        # Filter bank parameters
        if filter_bank:
            self.frequency_bands = [
                (8, 12),   # Alpha/Mu
                (12, 16),  # Lower Beta
                (16, 20),  # Mid Beta
                (20, 24),  # Higher Beta
                (24, 30),  # High Beta
                (8, 30)    # Broad band
            ]
        else:
            # Single band from config
            mu_band = config.motor_imagery['frequency_bands']['mu']
            beta_band = config.motor_imagery['frequency_bands']['beta']
            self.frequency_bands = [
                mu_band,
                beta_band,
                (mu_band[0], beta_band[1])  # Combined
            ]
        
        self.band_filters = {}
        self.band_csp = {}
        
        self.sampling_rate = config.device.sampling_rate
        
        self.logger.info(f"CSP Processor initialized with {len(self.frequency_bands)} frequency bands")
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'CSPProcessor':
        """
        Fit CSP filters
        
        Parameters:
        X: EEG data (n_trials, n_channels, n_samples)
        y: Labels (n_trials,)
        """
        try:
            self.classes_ = np.unique(y)
            n_classes = len(self.classes_)
            
            if n_classes < 2:
                raise ValueError("Need at least 2 classes for CSP")
            
            # Design frequency filters
            self._design_frequency_filters()
            
            if n_classes == 2:
                # Binary CSP
                self._fit_binary_csp(X, y)
            else:
                # Multi-class CSP (One-vs-Rest)
                self._fit_multiclass_csp(X, y)
            
            self.logger.info(f"CSP fitted for {n_classes} classes")
            return self
            
        except Exception as e:
            self.logger.error(f"CSP fitting failed: {e}")
            raise
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Transform data using fitted CSP filters
        
        Parameters:
        X: EEG data (n_trials, n_channels, n_samples)
        
        Returns:
        Transformed features (n_trials, n_features)
        """
        try:
            if self.filters_ is None:
                raise ValueError("CSP not fitted yet")
            
            # Apply frequency filtering and CSP for each band
            all_features = []
            
            for band_idx, (low_freq, high_freq) in enumerate(self.frequency_bands):
                # Filter data to frequency band
                X_filtered = self._apply_frequency_filter(X, low_freq, high_freq)
                
                # Apply CSP transformation
                if len(self.classes_) == 2:
                    features = self._transform_binary(X_filtered, band_idx)
                else:
                    features = self._transform_multiclass(X_filtered, band_idx)
                
                all_features.append(features)
            
            # Concatenate features from all bands
            combined_features = np.concatenate(all_features, axis=1)
            
            return combined_features
            
        except Exception as e:
            self.logger.error(f"CSP transformation failed: {e}")
            raise
    
    def _design_frequency_filters(self):
        """Design bandpass filters for frequency bands"""
        nyquist = self.sampling_rate / 2
        
        for band_idx, (low_freq, high_freq) in enumerate(self.frequency_bands):
            if high_freq >= nyquist:
                high_freq = nyquist - 1
            
            # Design Butterworth bandpass filter
            b, a = butter(4, [low_freq / nyquist, high_freq / nyquist], btype='band')
            self.band_filters[band_idx] = (b, a)
    
    def _apply_frequency_filter(self, X: np.ndarray, low_freq: float, high_freq: float) -> np.ndarray:
        """Apply frequency filtering to data"""
        n_trials, n_channels, n_samples = X.shape
        X_filtered = np.zeros_like(X)
        
        # Find corresponding filter
        band_idx = None
        for idx, (low, high) in enumerate(self.frequency_bands):
            if low == low_freq and high == high_freq:
                band_idx = idx
                break
        
        if band_idx is not None and band_idx in self.band_filters:
            b, a = self.band_filters[band_idx]
            
            for trial in range(n_trials):
                for ch in range(n_channels):
                    X_filtered[trial, ch, :] = filtfilt(b, a, X[trial, ch, :])
        else:
            # Fall back to manual filtering
            nyquist = self.sampling_rate / 2
            b, a = butter(4, [low_freq / nyquist, high_freq / nyquist], btype='band')
            
            for trial in range(n_trials):
                for ch in range(n_channels):
                    X_filtered[trial, ch, :] = filtfilt(b, a, X[trial, ch, :])
        
        return X_filtered
    
    def _fit_binary_csp(self, X: np.ndarray, y: np.ndarray):
        """Fit CSP for binary classification"""
        self.filters_ = {}
        self.patterns_ = {}
        self.eigenvalues_ = {}
        
        for band_idx, (low_freq, high_freq) in enumerate(self.frequency_bands):
            # Filter data to frequency band
            X_filtered = self._apply_frequency_filter(X, low_freq, high_freq)
            
            # Separate classes
            class1_mask = (y == self.classes_[0])
            class2_mask = (y == self.classes_[1])
            
            X1 = X_filtered[class1_mask]
            X2 = X_filtered[class2_mask]
            
            # Compute covariance matrices
            C1 = self._compute_covariance_matrix(X1)
            C2 = self._compute_covariance_matrix(X2)
            
            # Regularization
            n_channels = C1.shape[0]
            reg_matrix = self.reg_param * np.eye(n_channels)
            C1_reg = C1 + reg_matrix
            C2_reg = C2 + reg_matrix
            
            # Solve generalized eigenvalue problem
            eigenvals, eigenvecs = linalg.eigh(C1_reg, C1_reg + C2_reg)
            
            # Sort by eigenvalues
            sort_indices = np.argsort(eigenvals)
            eigenvals = eigenvals[sort_indices]
            eigenvecs = eigenvecs[:, sort_indices]
            
            # Select most discriminative patterns
            n_select = min(self.n_components, n_channels // 2)
            
            # Take n_select smallest and n_select largest eigenvalues
            selected_indices = np.concatenate([
                sort_indices[:n_select],           # Smallest (class 1)
                sort_indices[-n_select:]          # Largest (class 2)
            ])
            
            W = eigenvecs[:, selected_indices]
            
            # Store filters and patterns
            self.filters_[band_idx] = W.T  # Transpose for easy application
            self.patterns_[band_idx] = linalg.pinv(W.T)
            self.eigenvalues_[band_idx] = eigenvals[selected_indices]
    
    def _fit_multiclass_csp(self, X: np.ndarray, y: np.ndarray):
        """Fit CSP for multi-class classification using One-vs-Rest"""
        self.filters_ = {}
        self.patterns_ = {}
        self.eigenvalues_ = {}
        
        for band_idx, (low_freq, high_freq) in enumerate(self.frequency_bands):
            # Filter data to frequency band
            X_filtered = self._apply_frequency_filter(X, low_freq, high_freq)
            
            band_filters = []
            band_patterns = []
            band_eigenvals = []
            
            # One-vs-Rest CSP for each class
            for class_idx, target_class in enumerate(self.classes_):
                # Create binary problem: target class vs all others
                binary_y = (y == target_class).astype(int)
                
                # Skip if class has too few samples
                if np.sum(binary_y) < 2 or np.sum(1 - binary_y) < 2:
                    continue
                
                # Separate target class from others
                target_mask = (binary_y == 1)
                other_mask = (binary_y == 0)
                
                X_target = X_filtered[target_mask]
                X_other = X_filtered[other_mask]
                
                # Compute covariance matrices
                C_target = self._compute_covariance_matrix(X_target)
                C_other = self._compute_covariance_matrix(X_other)
                
                # Regularization
                n_channels = C_target.shape[0]
                reg_matrix = self.reg_param * np.eye(n_channels)
                C_target_reg = C_target + reg_matrix
                C_other_reg = C_other + reg_matrix
                
                # Solve generalized eigenvalue problem
                eigenvals, eigenvecs = linalg.eigh(C_target_reg, C_target_reg + C_other_reg)
                
                # Sort by eigenvalues
                sort_indices = np.argsort(eigenvals)
                eigenvals = eigenvals[sort_indices]
                eigenvecs = eigenvecs[:, sort_indices]
                
                # Select most discriminative patterns for this class
                n_select = min(self.n_components // len(self.classes_), n_channels // 4)
                n_select = max(1, n_select)  # At least 1 component per class
                
                # Take patterns most specific to target class
                selected_indices = sort_indices[-n_select:]  # Largest eigenvalues
                
                W_class = eigenvecs[:, selected_indices]
                
                band_filters.append(W_class.T)
                band_patterns.append(linalg.pinv(W_class.T))
                band_eigenvals.append(eigenvals[selected_indices])
            
            # Combine filters from all classes
            if band_filters:
                self.filters_[band_idx] = np.vstack(band_filters)
                self.patterns_[band_idx] = np.vstack(band_patterns)
                self.eigenvalues_[band_idx] = np.concatenate(band_eigenvals)
    
    def _compute_covariance_matrix(self, X: np.ndarray) -> np.ndarray:
        """Compute average covariance matrix from trials"""
        n_trials, n_channels, n_samples = X.shape
        
        # Method 1: Average covariance across trials
        cov_matrices = []
        
        for trial in range(n_trials):
            trial_data = X[trial, :, :]  # (n_channels, n_samples)
            
            # Compute covariance for this trial
            cov_trial = np.cov(trial_data)
            cov_matrices.append(cov_trial)
        
        # Average covariance
        avg_cov = np.mean(cov_matrices, axis=0)
        
        return avg_cov
    
    def _transform_binary(self, X_filtered: np.ndarray, band_idx: int) -> np.ndarray:
        """Transform data using binary CSP filters"""
        n_trials, n_channels, n_samples = X_filtered.shape
        W = self.filters_[band_idx]
        n_filters = W.shape[0]
        
        features = np.zeros((n_trials, n_filters))
        
        for trial in range(n_trials):
            # Apply spatial filters
            filtered_data = W @ X_filtered[trial, :, :]  # (n_filters, n_samples)
            
            # Compute log variance features
            for filt in range(n_filters):
                variance = np.var(filtered_data[filt, :])
                features[trial, filt] = np.log(variance + 1e-10)
        
        return features
    
    def _transform_multiclass(self, X_filtered: np.ndarray, band_idx: int) -> np.ndarray:
        """Transform data using multi-class CSP filters"""
        n_trials, n_channels, n_samples = X_filtered.shape
        W = self.filters_[band_idx]
        n_filters = W.shape[0]
        
        features = np.zeros((n_trials, n_filters))
        
        for trial in range(n_trials):
            # Apply spatial filters
            filtered_data = W @ X_filtered[trial, :, :]  # (n_filters, n_samples)
            
            # Compute log variance features
            for filt in range(n_filters):
                variance = np.var(filtered_data[filt, :])
                features[trial, filt] = np.log(variance + 1e-10)
        
        return features
    
    def get_patterns(self, band_idx: int = 0) -> Optional[np.ndarray]:
        """Get CSP patterns for visualization"""
        if self.patterns_ is None or band_idx not in self.patterns_:
            return None
        
        return self.patterns_[band_idx]
    
    def get_filters(self, band_idx: int = 0) -> Optional[np.ndarray]:
        """Get CSP filters"""
        if self.filters_ is None or band_idx not in self.filters_:
            return None
        
        return self.filters_[band_idx]
    
    def get_eigenvalues(self, band_idx: int = 0) -> Optional[np.ndarray]:
        """Get eigenvalues for discriminability analysis"""
        if self.eigenvalues_ is None or band_idx not in self.eigenvalues_:
            return None
        
        return self.eigenvalues_[band_idx]
    
    def get_frequency_bands(self) -> List[Tuple[float, float]]:
        """Get frequency bands used in filter bank"""
        return self.frequency_bands.copy()
    
    def compute_discriminability_index(self, band_idx: int = 0) -> float:
        """Compute discriminability index for frequency band"""
        eigenvals = self.get_eigenvalues(band_idx)
        
        if eigenvals is None or len(eigenvals) == 0:
            return 0.0
        
        # Discriminability index based on eigenvalue spread
        max_eigenval = np.max(eigenvals)
        min_eigenval = np.min(eigenvals)
        
        if min_eigenval <= 0:
            return 0.0
        
        # Log ratio gives measure of class separability
        discriminability = np.log(max_eigenval / min_eigenval)
        
        return float(discriminability)
    
    def select_best_frequency_bands(self, n_bands: int = 3) -> List[int]:
        """Select most discriminative frequency bands"""
        if not self.filter_bank or self.eigenvalues_ is None:
            return list(range(len(self.frequency_bands)))
        
        # Compute discriminability for each band
        band_scores = []
        
        for band_idx in range(len(self.frequency_bands)):
            score = self.compute_discriminability_index(band_idx)
            band_scores.append((band_idx, score))
        
        # Sort by discriminability score
        band_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return indices of best bands
        best_bands = [band_idx for band_idx, _ in band_scores[:n_bands]]
        
        self.logger.info(f"Selected best frequency bands: {[self.frequency_bands[i] for i in best_bands]}")
        
        return best_bands
    
    def visualize_patterns(self, band_idx: int = 0, channel_names: Optional[List[str]] = None):
        """Visualize CSP patterns (requires matplotlib)"""
        try:
            import matplotlib.pyplot as plt
            
            patterns = self.get_patterns(band_idx)
            if patterns is None:
                self.logger.error("No patterns available for visualization")
                return
            
            n_patterns, n_channels = patterns.shape
            channel_names = channel_names or [f'Ch{i+1}' for i in range(n_channels)]
            
            fig, axes = plt.subplots(1, n_patterns, figsize=(4*n_patterns, 6))
            if n_patterns == 1:
                axes = [axes]
            
            for i in range(n_patterns):
                axes[i].bar(range(n_channels), patterns[i, :])
                axes[i].set_title(f'CSP Pattern {i+1}')
                axes[i].set_xlabel('Channels')
                axes[i].set_ylabel('Weight')
                axes[i].set_xticks(range(n_channels))
                axes[i].set_xticklabels(channel_names, rotation=45)
                axes[i].grid(True, alpha=0.3)
            
            freq_band = self.frequency_bands[band_idx]
            plt.suptitle(f'CSP Patterns for {freq_band[0]}-{freq_band[1]} Hz')
            plt.tight_layout()
            plt.show()
            
        except ImportError:
            self.logger.warning("Matplotlib not available for visualization")
        except Exception as e:
            self.logger.error(f"Visualization failed: {e}")
    
    def get_feature_info(self) -> Dict[str, Any]:
        """Get information about extracted features"""
        if self.filters_ is None:
            return {}
        
        info = {
            'n_frequency_bands': len(self.frequency_bands),
            'frequency_bands': self.frequency_bands,
            'n_classes': len(self.classes_) if self.classes_ is not None else 0,
            'classes': self.classes_.tolist() if self.classes_ is not None else [],
            'filter_bank_enabled': self.filter_bank,
            'regularization_parameter': self.reg_param
        }
        
        # Add per-band information
        band_info = {}
        for band_idx in self.filters_.keys():
            n_filters = self.filters_[band_idx].shape[0]
            discriminability = self.compute_discriminability_index(band_idx)
            
            band_info[band_idx] = {
                'frequency_range': self.frequency_bands[band_idx],
                'n_filters': n_filters,
                'discriminability_index': discriminability
            }
        
        info['band_details'] = band_info
        
        return info