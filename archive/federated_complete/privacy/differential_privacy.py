"""
Differential Privacy for Federated Learning

Implementation of differential privacy mechanisms including Gaussian noise,
Laplace noise, and advanced privacy accounting.
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import tensorflow as tf
from scipy import stats
from abc import ABC, abstractmethod

from ..core.exceptions import PrivacyError


class PrivacyMechanism(ABC):
    """Abstract base class for privacy mechanisms."""
    
    def __init__(self, epsilon: float, delta: float = 0.0):
        self.epsilon = epsilon
        self.delta = delta
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def add_noise(self, data: np.ndarray, sensitivity: float) -> np.ndarray:
        """Add privacy-preserving noise to data."""
        pass
    
    @abstractmethod
    def get_privacy_cost(self, num_queries: int) -> Tuple[float, float]:
        """Get privacy cost for given number of queries."""
        pass


class LaplaceMechanism(PrivacyMechanism):
    """Laplace mechanism for differential privacy."""
    
    def __init__(self, epsilon: float):
        super().__init__(epsilon, delta=0.0)
    
    def add_noise(self, data: np.ndarray, sensitivity: float) -> np.ndarray:
        """Add Laplace noise for epsilon-differential privacy."""
        if self.epsilon <= 0:
            raise PrivacyError(
                "Epsilon must be positive for Laplace mechanism",
                privacy_mechanism="laplace",
                privacy_budget=self.epsilon
            )
        
        scale = sensitivity / self.epsilon
        noise = np.random.laplace(0, scale, data.shape)
        return data + noise
    
    def get_privacy_cost(self, num_queries: int) -> Tuple[float, float]:
        """Privacy cost accumulates linearly for Laplace mechanism."""
        return self.epsilon * num_queries, 0.0


class GaussianMechanism(PrivacyMechanism):
    """Gaussian mechanism for (epsilon, delta)-differential privacy."""
    
    def __init__(self, epsilon: float, delta: float):
        super().__init__(epsilon, delta)
        
        if delta <= 0 or delta >= 1:
            raise PrivacyError(
                "Delta must be in (0, 1) for Gaussian mechanism",
                privacy_mechanism="gaussian",
                privacy_budget=delta
            )
    
    def compute_noise_scale(self, sensitivity: float) -> float:
        """Compute noise scale for Gaussian mechanism."""
        if self.epsilon <= 0:
            raise PrivacyError(
                "Epsilon must be positive",
                privacy_mechanism="gaussian",
                privacy_budget=self.epsilon
            )
        
        # Compute sigma using the formula for (epsilon, delta)-DP
        c = math.sqrt(2 * math.log(1.25 / self.delta))
        sigma = c * sensitivity / self.epsilon
        return sigma
    
    def add_noise(self, data: np.ndarray, sensitivity: float) -> np.ndarray:
        """Add Gaussian noise for (epsilon, delta)-differential privacy."""
        sigma = self.compute_noise_scale(sensitivity)
        noise = np.random.normal(0, sigma, data.shape)
        return data + noise
    
    def get_privacy_cost(self, num_queries: int) -> Tuple[float, float]:
        """Privacy cost for Gaussian mechanism (simplified composition)."""
        # Advanced composition for Gaussian mechanism
        total_epsilon = num_queries * self.epsilon
        total_delta = num_queries * self.delta
        return total_epsilon, min(total_delta, 1.0)


class AdaptiveGaussianMechanism(GaussianMechanism):
    """Adaptive Gaussian mechanism with noise scaling."""
    
    def __init__(self, epsilon: float, delta: float, adaptive_factor: float = 1.0):
        super().__init__(epsilon, delta)
        self.adaptive_factor = adaptive_factor
        self.noise_history = []
    
    def add_noise(self, data: np.ndarray, sensitivity: float, 
                 gradient_norm: Optional[float] = None) -> np.ndarray:
        """Add adaptive Gaussian noise based on gradient norms."""
        base_sigma = self.compute_noise_scale(sensitivity)
        
        # Adapt noise based on gradient norm
        if gradient_norm is not None:
            # Reduce noise when gradients are small
            adaptive_sigma = base_sigma * (1 + self.adaptive_factor * gradient_norm)
        else:
            adaptive_sigma = base_sigma
        
        noise = np.random.normal(0, adaptive_sigma, data.shape)
        self.noise_history.append(adaptive_sigma)
        
        return data + noise


class DifferentialPrivacyManager:
    """Manager for differential privacy in federated learning."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.epsilon = config.get("epsilon", 1.0)
        self.delta = config.get("delta", 1e-5)
        self.noise_multiplier = config.get("noise_multiplier", 1.0)
        self.max_grad_norm = config.get("max_grad_norm", 1.0)
        self.adaptive_noise = config.get("adaptive_noise", False)
        self.mechanism_type = config.get("mechanism", "gaussian")
        
        # Initialize privacy mechanism
        self.mechanism = self._create_mechanism()
        
        # Privacy accounting
        self.total_epsilon_spent = 0.0
        self.total_delta_spent = 0.0
        self.query_count = 0
        self.privacy_history = []
        
        self.logger = logging.getLogger("DifferentialPrivacyManager")
        self.logger.info(f"DP Manager initialized: ε={self.epsilon}, δ={self.delta}")
    
    def _create_mechanism(self) -> PrivacyMechanism:
        """Create the appropriate privacy mechanism."""
        if self.mechanism_type.lower() == "laplace":
            return LaplaceMechanism(self.epsilon)
        elif self.mechanism_type.lower() == "gaussian":
            return GaussianMechanism(self.epsilon, self.delta)
        elif self.mechanism_type.lower() == "adaptive_gaussian":
            adaptive_factor = self.config.get("adaptive_factor", 1.0)
            return AdaptiveGaussianMechanism(self.epsilon, self.delta, adaptive_factor)
        else:
            raise PrivacyError(
                f"Unknown mechanism type: {self.mechanism_type}",
                privacy_mechanism=self.mechanism_type
            )
    
    def clip_gradients(self, gradients: List[np.ndarray]) -> Tuple[List[np.ndarray], float]:
        """Clip gradients to bound sensitivity."""
        clipped_gradients = []
        total_norm = 0.0
        
        # Compute total gradient norm
        for grad in gradients:
            total_norm += np.sum(grad ** 2)
        total_norm = math.sqrt(total_norm)
        
        # Clip gradients if necessary
        if total_norm > self.max_grad_norm:
            clip_factor = self.max_grad_norm / total_norm
            for grad in gradients:
                clipped_gradients.append(grad * clip_factor)
        else:
            clipped_gradients = gradients.copy()
        
        clipped_norm = min(total_norm, self.max_grad_norm)
        return clipped_gradients, clipped_norm
    
    def add_noise_to_gradients(self, gradients: List[np.ndarray], 
                             gradient_norm: Optional[float] = None) -> List[np.ndarray]:
        """Add differential privacy noise to gradients."""
        # Clip gradients first
        clipped_gradients, clipped_norm = self.clip_gradients(gradients)
        
        # Add noise to each gradient
        noisy_gradients = []
        sensitivity = 2 * self.max_grad_norm  # L2 sensitivity for clipped gradients
        
        for grad in clipped_gradients:
            if isinstance(self.mechanism, AdaptiveGaussianMechanism):
                noisy_grad = self.mechanism.add_noise(grad, sensitivity, gradient_norm)
            else:
                noisy_grad = self.mechanism.add_noise(grad, sensitivity)
            noisy_gradients.append(noisy_grad)
        
        # Update privacy accounting
        self._update_privacy_accounting()
        
        return noisy_gradients
    
    def add_noise_to_weights(self, weights: List[np.ndarray], 
                           weight_sensitivity: Optional[float] = None) -> List[np.ndarray]:
        """Add differential privacy noise to model weights."""
        if weight_sensitivity is None:
            weight_sensitivity = self.max_grad_norm
        
        noisy_weights = []
        for weight in weights:
            noisy_weight = self.mechanism.add_noise(weight, weight_sensitivity)
            noisy_weights.append(noisy_weight)
        
        # Update privacy accounting
        self._update_privacy_accounting()
        
        return noisy_weights
    
    def _update_privacy_accounting(self):
        """Update privacy budget accounting."""
        self.query_count += 1
        epsilon_cost, delta_cost = self.mechanism.get_privacy_cost(1)
        
        self.total_epsilon_spent += epsilon_cost
        self.total_delta_spent += delta_cost
        
        # Record privacy history
        self.privacy_history.append({
            "query_count": self.query_count,
            "epsilon_spent": self.total_epsilon_spent,
            "delta_spent": self.total_delta_spent,
            "epsilon_remaining": max(0, self.epsilon - self.total_epsilon_spent),
            "delta_remaining": max(0, self.delta - self.total_delta_spent)
        })
        
        # Check privacy budget exhaustion
        if self.total_epsilon_spent > self.epsilon:
            self.logger.warning(f"Privacy budget exceeded! ε spent: {self.total_epsilon_spent:.6f}")
        if self.total_delta_spent > self.delta:
            self.logger.warning(f"Delta budget exceeded! δ spent: {self.total_delta_spent:.6f}")
    
    def get_privacy_status(self) -> Dict[str, Any]:
        """Get current privacy status."""
        return {
            "mechanism": self.mechanism_type,
            "epsilon_budget": self.epsilon,
            "delta_budget": self.delta,
            "epsilon_spent": self.total_epsilon_spent,
            "delta_spent": self.total_delta_spent,
            "epsilon_remaining": max(0, self.epsilon - self.total_epsilon_spent),
            "delta_remaining": max(0, self.delta - self.total_delta_spent),
            "query_count": self.query_count,
            "max_grad_norm": self.max_grad_norm,
            "noise_multiplier": self.noise_multiplier,
            "budget_exhausted": (
                self.total_epsilon_spent > self.epsilon or 
                self.total_delta_spent > self.delta
            )
        }
    
    def check_privacy_budget(self) -> bool:
        """Check if privacy budget is still available."""
        return (self.total_epsilon_spent <= self.epsilon and 
                self.total_delta_spent <= self.delta)
    
    def reset_privacy_accounting(self):
        """Reset privacy accounting (use with caution)."""
        self.total_epsilon_spent = 0.0
        self.total_delta_spent = 0.0
        self.query_count = 0
        self.privacy_history.clear()
        self.logger.info("Privacy accounting reset")
    
    def estimate_remaining_queries(self) -> int:
        """Estimate number of remaining queries within budget."""
        if not self.check_privacy_budget():
            return 0
        
        epsilon_per_query, delta_per_query = self.mechanism.get_privacy_cost(1)
        
        epsilon_remaining = self.epsilon - self.total_epsilon_spent
        delta_remaining = self.delta - self.total_delta_spent
        
        if epsilon_per_query <= 0 and delta_per_query <= 0:
            return float('inf')
        
        queries_by_epsilon = (
            epsilon_remaining / epsilon_per_query if epsilon_per_query > 0 
            else float('inf')
        )
        queries_by_delta = (
            delta_remaining / delta_per_query if delta_per_query > 0 
            else float('inf')
        )
        
        return int(min(queries_by_epsilon, queries_by_delta))
    
    def get_noise_statistics(self) -> Dict[str, Any]:
        """Get noise addition statistics."""
        if hasattr(self.mechanism, 'noise_history') and self.mechanism.noise_history:
            noise_history = self.mechanism.noise_history
            return {
                "total_noise_additions": len(noise_history),
                "avg_noise_scale": np.mean(noise_history),
                "std_noise_scale": np.std(noise_history),
                "min_noise_scale": np.min(noise_history),
                "max_noise_scale": np.max(noise_history)
            }
        else:
            base_sigma = self.mechanism.compute_noise_scale(self.max_grad_norm)
            return {
                "total_noise_additions": self.query_count,
                "base_noise_scale": base_sigma,
                "mechanism_type": self.mechanism_type
            }


class RenyiDifferentialPrivacy:
    """Renyi Differential Privacy for tighter privacy analysis."""
    
    def __init__(self, alpha: float = 10.0):
        self.alpha = alpha
        self.rdp_orders = [1 + x / 10.0 for x in range(1, 100)] + list(range(12, 64))
        self.logger = logging.getLogger("RenyiDP")
    
    def compute_rdp(self, noise_multiplier: float, num_steps: int, 
                   sampling_probability: float = 1.0) -> List[float]:
        """Compute RDP guarantees for Gaussian mechanism."""
        rdp = []
        for alpha in self.rdp_orders:
            if alpha == 1:
                rdp.append(0.0)  # RDP at alpha=1 is always 0
            else:
                # RDP for Gaussian mechanism with subsampling
                rdp_alpha = (
                    alpha * sampling_probability**2 * num_steps / 
                    (2 * noise_multiplier**2)
                )
                rdp.append(rdp_alpha)
        return rdp
    
    def convert_rdp_to_dp(self, rdp: List[float], delta: float) -> float:
        """Convert RDP to (epsilon, delta)-DP."""
        eps_values = []
        for i, rdp_alpha in enumerate(rdp):
            alpha = self.rdp_orders[i]
            if alpha > 1:
                eps = rdp_alpha + math.log(delta) / (alpha - 1)
                eps_values.append(eps)
        
        return min(eps_values) if eps_values else float('inf')
    
    def compute_dp_from_gaussian(self, noise_multiplier: float, num_steps: int,
                               delta: float, sampling_probability: float = 1.0) -> float:
        """Compute DP guarantee from Gaussian mechanism parameters."""
        rdp = self.compute_rdp(noise_multiplier, num_steps, sampling_probability)
        return self.convert_rdp_to_dp(rdp, delta)