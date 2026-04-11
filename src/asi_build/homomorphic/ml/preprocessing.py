"""
Encrypted preprocessing utilities for machine learning.
"""

import numpy as np
from typing import List, Dict, Any, Optional
import logging

from ..schemes.ckks import CKKSScheme, CKKSCiphertext

logger = logging.getLogger(__name__)


class EncryptedScaler:
    """Encrypted data scaler for standardization and normalization."""
    
    def __init__(self, scheme: CKKSScheme, scaler_type: str = "standard"):
        self.scheme = scheme
        self.scaler_type = scaler_type  # "standard", "minmax", "robust"
        self.statistics = {}
        self.is_fitted = False
    
    def fit(self, X_encrypted: List[CKKSCiphertext]):
        """Fit scaler to encrypted data."""
        # Compute statistics on encrypted data
        if self.scaler_type == "standard":
            # Compute mean and std
            self._compute_mean_std(X_encrypted)
        elif self.scaler_type == "minmax":
            # Compute min and max
            self._compute_min_max(X_encrypted)
        
        self.is_fitted = True
        logger.info(f"Fitted {self.scaler_type} scaler")
    
    def transform(self, X_encrypted: List[CKKSCiphertext]) -> List[CKKSCiphertext]:
        """Transform encrypted data using fitted scaler."""
        if not self.is_fitted:
            raise ValueError("Scaler not fitted")
        
        if self.scaler_type == "standard":
            return self._standard_transform(X_encrypted)
        elif self.scaler_type == "minmax":
            return self._minmax_transform(X_encrypted)
        
        return X_encrypted
    
    def _compute_mean_std(self, X_encrypted: List[CKKSCiphertext]):
        """Compute encrypted mean and standard deviation."""
        # Mean computation
        sum_data = X_encrypted[0]
        for x in X_encrypted[1:]:
            sum_data = self.scheme.add(sum_data, x)
        
        n = len(X_encrypted)
        mean = self.scheme.multiply_plain(sum_data, 1.0 / n)
        
        # Variance computation
        var_sum = self.scheme.encrypt(self.scheme.encode([0.0]))
        for x in X_encrypted:
            diff = self.scheme.subtract(x, mean)
            sq_diff = self.scheme.multiply(diff, diff)
            var_sum = self.scheme.add(var_sum, sq_diff)
        
        variance = self.scheme.multiply_plain(var_sum, 1.0 / (n - 1))
        
        self.statistics["mean"] = mean
        self.statistics["variance"] = variance
    
    def _compute_min_max(self, X_encrypted: List[CKKSCiphertext]):
        """Compute encrypted min and max (approximation)."""
        # Simplified - would need max/min approximation functions
        self.statistics["min"] = X_encrypted[0]
        self.statistics["max"] = X_encrypted[0]
    
    def _standard_transform(self, X_encrypted: List[CKKSCiphertext]) -> List[CKKSCiphertext]:
        """Apply standard scaling: (x - mean) / std."""
        mean = self.statistics["mean"]
        # std = sqrt(variance) - would need sqrt approximation
        
        scaled = []
        for x in X_encrypted:
            centered = self.scheme.subtract(x, mean)
            # Would divide by std here
            scaled.append(centered)
        
        return scaled
    
    def _minmax_transform(self, X_encrypted: List[CKKSCiphertext]) -> List[CKKSCiphertext]:
        """Apply min-max scaling: (x - min) / (max - min)."""
        min_val = self.statistics["min"]
        max_val = self.statistics["max"]
        
        scaled = []
        for x in X_encrypted:
            shifted = self.scheme.subtract(x, min_val)
            # Would divide by (max - min) here
            scaled.append(shifted)
        
        return scaled


class EncryptedPreprocessor:
    """Comprehensive encrypted preprocessing pipeline."""
    
    def __init__(self, scheme: CKKSScheme):
        self.scheme = scheme
        self.steps = []
        self.is_fitted = False
    
    def add_scaler(self, scaler_type: str = "standard"):
        """Add scaling step to pipeline."""
        scaler = EncryptedScaler(self.scheme, scaler_type)
        self.steps.append(("scaler", scaler))
        return self
    
    def fit(self, X_encrypted: List[CKKSCiphertext]):
        """Fit all preprocessing steps."""
        current_data = X_encrypted
        
        for name, step in self.steps:
            step.fit(current_data)
            current_data = step.transform(current_data)
        
        self.is_fitted = True
        logger.info(f"Fitted preprocessing pipeline with {len(self.steps)} steps")
    
    def transform(self, X_encrypted: List[CKKSCiphertext]) -> List[CKKSCiphertext]:
        """Apply all preprocessing steps."""
        if not self.is_fitted:
            raise ValueError("Preprocessor not fitted")
        
        current_data = X_encrypted
        for name, step in self.steps:
            current_data = step.transform(current_data)
        
        return current_data
    
    def fit_transform(self, X_encrypted: List[CKKSCiphertext]) -> List[CKKSCiphertext]:
        """Fit and transform in one step."""
        self.fit(X_encrypted)
        return self.transform(X_encrypted)