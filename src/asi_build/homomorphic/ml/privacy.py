"""
Privacy-preserving techniques for encrypted machine learning.
"""

import numpy as np
from typing import List, Dict, Any, Optional
import logging

from ..schemes.ckks import CKKSScheme, CKKSCiphertext

logger = logging.getLogger(__name__)


class DifferentialPrivacy:
    """Differential privacy mechanisms for encrypted ML."""
    
    def __init__(self, scheme: CKKSScheme, epsilon: float = 1.0):
        self.scheme = scheme
        self.epsilon = epsilon  # Privacy budget
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_laplace_noise(self, data: CKKSCiphertext, sensitivity: float) -> CKKSCiphertext:
        """Add Laplace noise for differential privacy."""
        # Laplace noise scale
        scale = sensitivity / self.epsilon
        
        # Generate Laplace noise (simplified - would use proper distribution)
        noise_values = np.random.laplace(0, scale, self.scheme.encoder.slots)
        noise_plaintext = self.scheme.encode(noise_values.astype(complex))
        noise_encrypted = self.scheme.encrypt(noise_plaintext)
        
        # Add noise to data
        noisy_data = self.scheme.add(data, noise_encrypted)
        
        self.logger.debug(f"Added Laplace noise with scale {scale:.6f}")
        return noisy_data
    
    def add_gaussian_noise(self, data: CKKSCiphertext, sensitivity: float, delta: float = 1e-5) -> CKKSCiphertext:
        """Add Gaussian noise for (ε,δ)-differential privacy."""
        # Gaussian noise standard deviation
        sigma = (sensitivity * np.sqrt(2 * np.log(1.25 / delta))) / self.epsilon
        
        # Generate Gaussian noise
        noise_values = np.random.normal(0, sigma, self.scheme.encoder.slots)
        noise_plaintext = self.scheme.encode(noise_values.astype(complex))
        noise_encrypted = self.scheme.encrypt(noise_plaintext)
        
        # Add noise to data
        noisy_data = self.scheme.add(data, noise_encrypted)
        
        self.logger.debug(f"Added Gaussian noise with σ={sigma:.6f}")
        return noisy_data


class SecureAggregation:
    """Secure aggregation protocols for federated learning."""
    
    def __init__(self, scheme: CKKSScheme):
        self.scheme = scheme
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def secure_sum(self, client_data: List[CKKSCiphertext]) -> CKKSCiphertext:
        """Securely sum data from multiple clients."""
        if not client_data:
            raise ValueError("No client data provided")
        
        # Sum all client contributions
        total = client_data[0]
        for data in client_data[1:]:
            total = self.scheme.add(total, data)
        
        self.logger.info(f"Securely aggregated data from {len(client_data)} clients")
        return total
    
    def secure_average(self, client_data: List[CKKSCiphertext]) -> CKKSCiphertext:
        """Securely compute average of client data."""
        total = self.secure_sum(client_data)
        n_clients = len(client_data)
        
        # Compute average
        average = self.scheme.multiply_plain(total, 1.0 / n_clients)
        
        return average
    
    def weighted_secure_aggregation(self, client_data: List[CKKSCiphertext], 
                                  weights: List[float]) -> CKKSCiphertext:
        """Securely aggregate with client weights."""
        if len(client_data) != len(weights):
            raise ValueError("Number of clients must match number of weights")
        
        # Weighted sum
        weighted_sum = self.scheme.multiply_plain(client_data[0], weights[0])
        
        for data, weight in zip(client_data[1:], weights[1:]):
            weighted_data = self.scheme.multiply_plain(data, weight)
            weighted_sum = self.scheme.add(weighted_sum, weighted_data)
        
        # Normalize by sum of weights
        total_weight = sum(weights)
        result = self.scheme.multiply_plain(weighted_sum, 1.0 / total_weight)
        
        self.logger.info(f"Weighted secure aggregation with {len(client_data)} clients")
        return result