"""
Noise estimation and management for homomorphic encryption.
"""

import math
import numpy as np
from typing import Any, List, Dict, Optional, Tuple
import logging

from .parameters import FHEParameters
from .base import NoiseException
from .encryption import Ciphertext
from .polynomial import Polynomial

logger = logging.getLogger(__name__)


class NoiseEstimator:
    """
    Noise estimation and tracking for homomorphic encryption schemes.
    
    Provides methods to estimate noise growth, track noise budgets,
    and predict when ciphertexts will become unusable.
    """
    
    def __init__(self, parameters: FHEParameters):
        """
        Initialize the noise estimator.
        
        Args:
            parameters: FHE parameters
        """
        self.parameters = parameters
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Precompute noise bounds
        self.initial_noise_bound = self._compute_initial_noise_bound()
        self.max_noise_bound = self._compute_max_noise_bound()
        
        # Operation tracking
        self.operation_history = []
    
    def _compute_initial_noise_bound(self) -> float:
        """
        Compute the initial noise bound for fresh ciphertexts.
        
        Returns:
            Initial noise bound
        """
        # Based on Gaussian noise with standard deviation σ
        # B_fresh ≈ 6σ * sqrt(n) with high probability
        sigma = self.parameters.noise_standard_deviation
        n = self.parameters.polynomial_modulus_degree
        
        return 6 * sigma * math.sqrt(n)
    
    def _compute_max_noise_bound(self) -> float:
        """
        Compute the maximum allowable noise bound.
        
        Returns:
            Maximum noise bound before decryption fails
        """
        # For correct decryption, noise must be less than q/2t (BFV/BGV)
        # or approximately q/4 (CKKS)
        
        if self.parameters.scheme_type.value in ["BFV", "BGV"]:
            if self.parameters.plaintext_modulus:
                q = self.parameters.coefficient_modulus[0]
                t = self.parameters.plaintext_modulus
                return q / (2 * t)
        
        # For CKKS or when no plaintext modulus
        q = self.parameters.coefficient_modulus[0]
        return q / 4
    
    def estimate_fresh_noise(self, ciphertext: Ciphertext) -> float:
        """
        Estimate noise in a fresh ciphertext.
        
        Args:
            ciphertext: Fresh ciphertext
        
        Returns:
            Estimated noise magnitude
        """
        # For fresh ciphertexts, use theoretical bound
        return self.initial_noise_bound
    
    def estimate_addition_noise(self, noise1: float, noise2: float) -> float:
        """
        Estimate noise after homomorphic addition.
        
        Args:
            noise1: Noise in first operand
            noise2: Noise in second operand
        
        Returns:
            Estimated noise after addition
        """
        # Addition: noise grows additively with small constant factor
        return noise1 + noise2 + 1  # +1 for rounding errors
    
    def estimate_multiplication_noise(self, noise1: float, noise2: float,
                                    ciphertext1: Ciphertext, ciphertext2: Ciphertext) -> float:
        """
        Estimate noise after homomorphic multiplication.
        
        Args:
            noise1: Noise in first operand
            noise2: Noise in second operand
            ciphertext1: First ciphertext operand
            ciphertext2: Second ciphertext operand
        
        Returns:
            Estimated noise after multiplication
        """
        # Multiplication noise grows significantly
        n = self.parameters.polynomial_modulus_degree
        
        # Estimate plaintext norms
        pt1_norm = self._estimate_plaintext_norm(ciphertext1)
        pt2_norm = self._estimate_plaintext_norm(ciphertext2)
        
        # Noise growth formula (simplified)
        # B_mult ≈ (B1 * ||pt2|| + B2 * ||pt1|| + B1 * B2) * growth_factor
        growth_factor = math.sqrt(n)  # Simplified growth factor
        
        mult_noise = (noise1 * pt2_norm + noise2 * pt1_norm + noise1 * noise2) * growth_factor
        
        return mult_noise
    
    def estimate_relinearization_noise(self, noise: float) -> float:
        """
        Estimate noise after relinearization.
        
        Args:
            noise: Input noise
        
        Returns:
            Estimated noise after relinearization
        """
        # Relinearization adds some noise but is typically manageable
        additional_noise = self.initial_noise_bound * 0.1  # 10% of fresh noise
        return noise + additional_noise
    
    def estimate_rotation_noise(self, noise: float) -> float:
        """
        Estimate noise after rotation.
        
        Args:
            noise: Input noise
        
        Returns:
            Estimated noise after rotation
        """
        # Rotation typically adds noise similar to relinearization
        additional_noise = self.initial_noise_bound * 0.15  # 15% of fresh noise
        return noise + additional_noise
    
    def estimate_rescaling_noise(self, noise: float, scale_factor: float) -> float:
        """
        Estimate noise after rescaling (CKKS).
        
        Args:
            noise: Input noise
            scale_factor: Scale factor for rescaling
        
        Returns:
            Estimated noise after rescaling
        """
        # Rescaling reduces noise proportionally but adds rounding errors
        rescaled_noise = noise / scale_factor
        rounding_error = math.sqrt(self.parameters.polynomial_modulus_degree)
        
        return rescaled_noise + rounding_error
    
    def _estimate_plaintext_norm(self, ciphertext: Ciphertext) -> float:
        """
        Estimate the norm of the underlying plaintext.
        
        Args:
            ciphertext: Ciphertext to analyze
        
        Returns:
            Estimated plaintext norm
        """
        # Simplified estimation based on ciphertext statistics
        # In practice, this would require more sophisticated analysis
        
        if ciphertext.scale:
            # For CKKS, estimate based on scale
            return math.sqrt(self.parameters.polynomial_modulus_degree) * ciphertext.scale
        else:
            # For BFV/BGV, use plaintext modulus as rough estimate
            if self.parameters.plaintext_modulus:
                return math.sqrt(self.parameters.polynomial_modulus_degree) * self.parameters.plaintext_modulus / 2
            else:
                return math.sqrt(self.parameters.polynomial_modulus_degree)
    
    def track_operation(self, operation: str, input_noises: List[float], 
                       output_noise: float, **kwargs) -> None:
        """
        Track a homomorphic operation for noise analysis.
        
        Args:
            operation: Type of operation
            input_noises: List of input noise levels
            output_noise: Resulting noise level
            **kwargs: Additional operation metadata
        """
        operation_record = {
            "operation": operation,
            "input_noises": input_noises.copy(),
            "output_noise": output_noise,
            "noise_growth": output_noise - max(input_noises) if input_noises else output_noise,
            "metadata": kwargs.copy()
        }
        
        self.operation_history.append(operation_record)
        
        # Log warning if noise is getting high
        noise_ratio = output_noise / self.max_noise_bound
        if noise_ratio > 0.8:
            self.logger.warning(f"High noise level after {operation}: {noise_ratio:.2%} of maximum")
        elif noise_ratio > 0.5:
            self.logger.info(f"Moderate noise level after {operation}: {noise_ratio:.2%} of maximum")
    
    def predict_remaining_operations(self, current_noise: float, 
                                   operation_pattern: List[str]) -> int:
        """
        Predict how many more operations can be performed.
        
        Args:
            current_noise: Current noise level
            operation_pattern: Pattern of operations to simulate
        
        Returns:
            Estimated number of remaining operations
        """
        simulated_noise = current_noise
        operation_count = 0
        max_iterations = 1000  # Safety limit
        
        while (simulated_noise < self.max_noise_bound and 
               operation_count < max_iterations):
            
            for op in operation_pattern:
                if op == "add":
                    # Simulate addition with similar noise
                    simulated_noise = self.estimate_addition_noise(
                        simulated_noise, simulated_noise
                    )
                elif op == "multiply":
                    # Simulate multiplication
                    simulated_noise = self.estimate_multiplication_noise(
                        simulated_noise, simulated_noise, None, None
                    )
                    # Add relinearization noise
                    simulated_noise = self.estimate_relinearization_noise(simulated_noise)
                elif op == "rotate":
                    simulated_noise = self.estimate_rotation_noise(simulated_noise)
                
                operation_count += 1
                
                if simulated_noise >= self.max_noise_bound:
                    break
        
        return operation_count
    
    def analyze_circuit_depth(self, circuit: List[Dict]) -> Dict[str, float]:
        """
        Analyze the noise growth for a given circuit.
        
        Args:
            circuit: List of operation descriptions
        
        Returns:
            Analysis results including final noise and feasibility
        """
        noise_levels = {}  # Track noise for each variable
        current_noise = self.initial_noise_bound
        
        # Initialize input variables
        for i, op in enumerate(circuit):
            if op.get("type") == "input":
                var_name = op.get("output", f"var_{i}")
                noise_levels[var_name] = self.initial_noise_bound
        
        # Process operations
        max_noise = current_noise
        
        for op in circuit:
            op_type = op.get("type")
            inputs = op.get("inputs", [])
            output = op.get("output", f"temp_{len(noise_levels)}")
            
            if op_type == "add":
                if len(inputs) >= 2:
                    noise1 = noise_levels.get(inputs[0], current_noise)
                    noise2 = noise_levels.get(inputs[1], current_noise)
                    result_noise = self.estimate_addition_noise(noise1, noise2)
                    noise_levels[output] = result_noise
                    max_noise = max(max_noise, result_noise)
            
            elif op_type == "multiply":
                if len(inputs) >= 2:
                    noise1 = noise_levels.get(inputs[0], current_noise)
                    noise2 = noise_levels.get(inputs[1], current_noise)
                    result_noise = self.estimate_multiplication_noise(
                        noise1, noise2, None, None
                    )
                    # Add relinearization
                    result_noise = self.estimate_relinearization_noise(result_noise)
                    noise_levels[output] = result_noise
                    max_noise = max(max_noise, result_noise)
            
            elif op_type == "rotate":
                if len(inputs) >= 1:
                    noise1 = noise_levels.get(inputs[0], current_noise)
                    result_noise = self.estimate_rotation_noise(noise1)
                    noise_levels[output] = result_noise
                    max_noise = max(max_noise, result_noise)
        
        return {
            "final_noise": max_noise,
            "noise_ratio": max_noise / self.max_noise_bound,
            "is_feasible": max_noise < self.max_noise_bound,
            "noise_budget_remaining": max(0, self.max_noise_bound - max_noise),
            "variable_noises": noise_levels.copy()
        }
    
    def suggest_parameter_changes(self, target_depth: int, 
                                target_operations: List[str]) -> Dict[str, Any]:
        """
        Suggest parameter changes to support a target computation depth.
        
        Args:
            target_depth: Target multiplicative depth
            target_operations: List of operations to support
        
        Returns:
            Suggested parameter changes
        """
        # Simulate noise growth for target operations
        simulated_noise = self.initial_noise_bound
        
        for _ in range(target_depth):
            for op in target_operations:
                if op == "multiply":
                    simulated_noise = self.estimate_multiplication_noise(
                        simulated_noise, simulated_noise, None, None
                    )
                    simulated_noise = self.estimate_relinearization_noise(simulated_noise)
                elif op == "add":
                    simulated_noise = self.estimate_addition_noise(
                        simulated_noise, simulated_noise
                    )
        
        suggestions = {}
        
        if simulated_noise >= self.max_noise_bound:
            # Need larger parameters
            current_bits = sum(math.log2(q) for q in self.parameters.coefficient_modulus)
            required_bits = current_bits * (simulated_noise / self.max_noise_bound) * 1.5
            
            suggestions["increase_modulus_bits"] = required_bits - current_bits
            suggestions["reason"] = "Insufficient noise budget for target depth"
        
        else:
            # Current parameters are sufficient
            noise_ratio = simulated_noise / self.max_noise_bound
            suggestions["current_usage"] = f"{noise_ratio:.1%}"
            suggestions["status"] = "Sufficient for target operations"
        
        return suggestions
    
    def get_noise_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about noise growth from operation history.
        
        Returns:
            Noise statistics
        """
        if not self.operation_history:
            return {"message": "No operations tracked"}
        
        operation_types = [op["operation"] for op in self.operation_history]
        noise_growths = [op["noise_growth"] for op in self.operation_history]
        final_noises = [op["output_noise"] for op in self.operation_history]
        
        return {
            "total_operations": len(self.operation_history),
            "operation_types": {op_type: operation_types.count(op_type) 
                             for op_type in set(operation_types)},
            "average_noise_growth": float(np.mean(noise_growths)),
            "max_noise_growth": float(np.max(noise_growths)),
            "final_noise": float(final_noises[-1]),
            "noise_budget_used": float(final_noises[-1] / self.max_noise_bound),
            "noise_budget_remaining": float(max(0, self.max_noise_bound - final_noises[-1]))
        }
    
    def reset_tracking(self) -> None:
        """Reset operation tracking history."""
        self.operation_history.clear()
        self.logger.info("Reset noise tracking history")


class NoiseManager:
    """
    Advanced noise management with automatic parameter adjustment.
    """
    
    def __init__(self, parameters: FHEParameters):
        """
        Initialize the noise manager.
        
        Args:
            parameters: FHE parameters
        """
        self.parameters = parameters
        self.estimator = NoiseEstimator(parameters)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Adaptive thresholds
        self.warning_threshold = 0.7  # 70% of max noise
        self.critical_threshold = 0.9  # 90% of max noise
    
    def check_noise_level(self, ciphertext: Ciphertext, estimated_noise: float) -> Dict[str, Any]:
        """
        Check noise level and provide recommendations.
        
        Args:
            ciphertext: Ciphertext to check
            estimated_noise: Estimated noise level
        
        Returns:
            Noise level assessment and recommendations
        """
        noise_ratio = estimated_noise / self.estimator.max_noise_bound
        
        assessment = {
            "noise_level": estimated_noise,
            "noise_ratio": noise_ratio,
            "max_noise": self.estimator.max_noise_bound,
            "status": "safe"
        }
        
        if noise_ratio >= self.critical_threshold:
            assessment["status"] = "critical"
            assessment["recommendations"] = [
                "Consider rescaling (CKKS)",
                "Use bootstrap if available", 
                "Reduce operation complexity",
                "Use fresh ciphertexts"
            ]
            self.logger.error(f"Critical noise level: {noise_ratio:.1%}")
        
        elif noise_ratio >= self.warning_threshold:
            assessment["status"] = "warning"
            assessment["recommendations"] = [
                "Monitor noise carefully",
                "Consider rescaling soon",
                "Limit additional multiplications"
            ]
            self.logger.warning(f"High noise level: {noise_ratio:.1%}")
        
        else:
            assessment["recommendations"] = [
                f"Safe to continue - {(1-noise_ratio)*100:.1f}% budget remaining"
            ]
        
        return assessment
    
    def auto_rescale_recommendation(self, ciphertext: Ciphertext, 
                                  estimated_noise: float) -> bool:
        """
        Determine if automatic rescaling is recommended.
        
        Args:
            ciphertext: Ciphertext to evaluate
            estimated_noise: Current estimated noise
        
        Returns:
            True if rescaling is recommended
        """
        if not ciphertext.scale:
            return False  # Not applicable for non-CKKS schemes
        
        noise_ratio = estimated_noise / self.estimator.max_noise_bound
        
        # Recommend rescaling if noise is high and scale allows it
        return (noise_ratio > self.warning_threshold and 
                ciphertext.level < len(self.parameters.coefficient_modulus) - 1)
    
    def optimize_parameter_chain(self, target_operations: List[str]) -> List[int]:
        """
        Optimize the modulus chain for a sequence of operations.
        
        Args:
            target_operations: Sequence of operations to optimize for
        
        Returns:
            Optimized coefficient modulus chain
        """
        # Count multiplicative depth
        mult_depth = sum(1 for op in target_operations if op in ["multiply", "square"])
        
        # Estimate required modulus bits per level
        base_bits = 50  # Base security
        scale_bits = 40 if self.parameters.scale else 0
        
        # Calculate bits needed per level
        bits_per_level = scale_bits + 10  # Extra for noise
        total_bits = base_bits + (mult_depth + 1) * bits_per_level
        
        # Generate modulus chain
        modulus_chain = []
        remaining_bits = total_bits
        
        while remaining_bits > base_bits:
            level_bits = min(60, remaining_bits - base_bits)  # Max 60 bits per prime
            level_bits = max(30, level_bits)  # Min 30 bits per prime
            
            # Generate prime with approximately level_bits bits
            prime = self._generate_modulus_prime(level_bits)
            modulus_chain.append(prime)
            
            remaining_bits -= level_bits
        
        return modulus_chain
    
    def _generate_modulus_prime(self, bits: int) -> int:
        """Generate a prime for the modulus chain."""
        # Simplified implementation - in practice would ensure NTT-friendly primes
        import random
        
        min_val = 2 ** (bits - 1)
        max_val = 2 ** bits - 1
        
        # Start with a random candidate
        candidate = random.randrange(min_val | 1, max_val, 2)
        
        # Find next prime (simplified)
        while not self._is_prime_simple(candidate):
            candidate += 2
            if candidate > max_val:
                candidate = min_val | 1
        
        return candidate
    
    def _is_prime_simple(self, n: int) -> bool:
        """Simple primality test."""
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        
        for i in range(3, int(n**0.5) + 1, 2):
            if n % i == 0:
                return False
        
        return True