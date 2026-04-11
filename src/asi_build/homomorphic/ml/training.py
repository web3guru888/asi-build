"""
Encrypted training utilities for machine learning models.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from ..schemes.ckks import CKKSCiphertext, CKKSScheme

logger = logging.getLogger(__name__)


class EncryptedTrainer:
    """Encrypted trainer for ML models with various optimization algorithms."""

    def __init__(self, scheme: CKKSScheme):
        self.scheme = scheme
        self.logger = logging.getLogger(self.__class__.__name__)

    def sgd_step(
        self, weights: CKKSCiphertext, gradients: CKKSCiphertext, learning_rate: float
    ) -> CKKSCiphertext:
        """Perform SGD weight update step."""
        lr_gradients = self.scheme.multiply_plain(gradients, learning_rate)
        return self.scheme.subtract(weights, lr_gradients)

    def adam_step(
        self,
        weights: CKKSCiphertext,
        gradients: CKKSCiphertext,
        m: CKKSCiphertext,
        v: CKKSCiphertext,
        learning_rate: float,
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-8,
        t: int = 1,
    ) -> tuple:
        """Perform Adam optimizer step."""
        # Update biased first moment estimate
        beta1_complement = 1 - beta1
        m = self.scheme.add(
            self.scheme.multiply_plain(m, beta1),
            self.scheme.multiply_plain(gradients, beta1_complement),
        )

        # Update biased second moment estimate
        beta2_complement = 1 - beta2
        grad_squared = self.scheme.multiply(gradients, gradients)
        v = self.scheme.add(
            self.scheme.multiply_plain(v, beta2),
            self.scheme.multiply_plain(grad_squared, beta2_complement),
        )

        # Bias correction
        m_corrected = self.scheme.multiply_plain(m, 1 / (1 - beta1**t))
        v_corrected = self.scheme.multiply_plain(v, 1 / (1 - beta2**t))

        # Weight update (simplified - would need sqrt approximation)
        step = self.scheme.multiply_plain(m_corrected, learning_rate)
        new_weights = self.scheme.subtract(weights, step)

        return new_weights, m, v


class FederatedLearning:
    """Secure federated learning with homomorphic encryption."""

    def __init__(self, scheme: CKKSScheme):
        self.scheme = scheme
        self.logger = logging.getLogger(self.__class__.__name__)

    def aggregate_gradients(self, encrypted_gradients: List[CKKSCiphertext]) -> CKKSCiphertext:
        """Securely aggregate gradients from multiple clients."""
        if not encrypted_gradients:
            raise ValueError("No gradients to aggregate")

        # Sum all gradients
        aggregated = encrypted_gradients[0]
        for grad in encrypted_gradients[1:]:
            aggregated = self.scheme.add(aggregated, grad)

        # Average by number of clients
        n_clients = len(encrypted_gradients)
        return self.scheme.multiply_plain(aggregated, 1.0 / n_clients)

    def secure_aggregation(
        self, client_updates: List[CKKSCiphertext], weights: List[float]
    ) -> CKKSCiphertext:
        """Weighted secure aggregation of client updates."""
        if len(client_updates) != len(weights):
            raise ValueError("Number of updates must match number of weights")

        # Weighted sum
        weighted_sum = self.scheme.multiply_plain(client_updates[0], weights[0])
        for update, weight in zip(client_updates[1:], weights[1:]):
            weighted_update = self.scheme.multiply_plain(update, weight)
            weighted_sum = self.scheme.add(weighted_sum, weighted_update)

        return weighted_sum
