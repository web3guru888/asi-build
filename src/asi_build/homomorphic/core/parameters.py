"""
Parameter generation and validation for homomorphic encryption schemes.
"""

import logging
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from .base import ParameterException, SchemeType, SecurityLevel

logger = logging.getLogger(__name__)


@dataclass
class FHEParameters:
    """Container for FHE scheme parameters."""

    polynomial_modulus_degree: int
    coefficient_modulus: List[int]
    plaintext_modulus: Optional[int]
    scale: Optional[float]
    security_level: SecurityLevel
    scheme_type: SchemeType
    noise_standard_deviation: float

    def __post_init__(self):
        """Validate parameters after initialization."""
        self._validate()

    def _validate(self):
        """Validate parameter consistency and security."""
        if self.polynomial_modulus_degree <= 0:
            raise ParameterException("Polynomial modulus degree must be positive")

        if not self._is_power_of_2(self.polynomial_modulus_degree):
            raise ParameterException("Polynomial modulus degree must be a power of 2")

        if not self.coefficient_modulus:
            raise ParameterException("Coefficient modulus cannot be empty")

        # Check security level constraints
        log_q = sum(math.log2(q) for q in self.coefficient_modulus)
        if not self._check_security_constraint(log_q):
            raise ParameterException(f"Parameters do not meet {self.security_level.value} security")

    def _is_power_of_2(self, n: int) -> bool:
        """Check if n is a power of 2."""
        return n > 0 and (n & (n - 1)) == 0

    def _check_security_constraint(self, log_q: float) -> bool:
        """Check if parameters meet security constraints."""
        # Simplified security check based on LWE hardness
        log_n = math.log2(self.polynomial_modulus_degree)

        # Security estimates based on lattice attacks
        security_bits = {
            SecurityLevel.LOW: 128,
            SecurityLevel.MEDIUM: 192,
            SecurityLevel.HIGH: 256,
            SecurityLevel.ULTRA: 384,
        }

        required_bits = security_bits[self.security_level]
        estimated_security = log_n * 8 - log_q  # Simplified estimate

        return estimated_security >= required_bits


class ParameterGenerator:
    """Generate secure parameters for different FHE schemes."""

    # Predefined secure parameter sets
    SECURE_PARAMETERS = {
        (SchemeType.CKKS, SecurityLevel.LOW): {
            "poly_modulus_degree": 8192,
            "coeff_modulus_bits": [60, 40, 40, 60],
            "scale_bits": 40,
            "noise_std": 3.2,
        },
        (SchemeType.CKKS, SecurityLevel.MEDIUM): {
            "poly_modulus_degree": 16384,
            "coeff_modulus_bits": [60, 40, 40, 40, 40, 60],
            "scale_bits": 40,
            "noise_std": 3.2,
        },
        (SchemeType.CKKS, SecurityLevel.HIGH): {
            "poly_modulus_degree": 32768,
            "coeff_modulus_bits": [60, 40, 40, 40, 40, 40, 40, 60],
            "scale_bits": 40,
            "noise_std": 3.2,
        },
        (SchemeType.BFV, SecurityLevel.LOW): {
            "poly_modulus_degree": 4096,
            "coeff_modulus_bits": [36, 36, 37],
            "plaintext_modulus": 1024,
            "noise_std": 3.2,
        },
        (SchemeType.BFV, SecurityLevel.MEDIUM): {
            "poly_modulus_degree": 8192,
            "coeff_modulus_bits": [43, 43, 44],
            "plaintext_modulus": 1024,
            "noise_std": 3.2,
        },
        (SchemeType.BFV, SecurityLevel.HIGH): {
            "poly_modulus_degree": 16384,
            "coeff_modulus_bits": [48, 48, 48, 49],
            "plaintext_modulus": 1024,
            "noise_std": 3.2,
        },
        (SchemeType.BGV, SecurityLevel.LOW): {
            "poly_modulus_degree": 4096,
            "coeff_modulus_bits": [36, 36, 37],
            "plaintext_modulus": 1024,
            "noise_std": 3.2,
        },
        (SchemeType.BGV, SecurityLevel.MEDIUM): {
            "poly_modulus_degree": 8192,
            "coeff_modulus_bits": [43, 43, 44],
            "plaintext_modulus": 1024,
            "noise_std": 3.2,
        },
        (SchemeType.BGV, SecurityLevel.HIGH): {
            "poly_modulus_degree": 16384,
            "coeff_modulus_bits": [48, 48, 48, 49],
            "plaintext_modulus": 1024,
            "noise_std": 3.2,
        },
    }

    def __init__(self):
        """Initialize the parameter generator."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_parameters(
        self,
        scheme_type: SchemeType,
        security_level: SecurityLevel,
        custom_params: Optional[Dict] = None,
    ) -> FHEParameters:
        """
        Generate secure parameters for the specified scheme and security level.

        Args:
            scheme_type: The FHE scheme type
            security_level: Desired security level
            custom_params: Optional custom parameter overrides

        Returns:
            FHEParameters object with generated parameters
        """
        key = (scheme_type, security_level)

        if key not in self.SECURE_PARAMETERS:
            raise ParameterException(
                f"No predefined parameters for {scheme_type.value} "
                f"at {security_level.value} security level"
            )

        base_params = self.SECURE_PARAMETERS[key].copy()

        # Apply custom parameter overrides
        if custom_params:
            base_params.update(custom_params)

        # Generate coefficient modulus from bit sizes
        coeff_modulus = self._generate_coefficient_modulus(base_params["coeff_modulus_bits"])

        # Set scale for CKKS
        scale = None
        if scheme_type == SchemeType.CKKS:
            scale = 2.0 ** base_params.get("scale_bits", 40)

        # Set plaintext modulus for BFV/BGV
        plaintext_modulus = None
        if scheme_type in [SchemeType.BFV, SchemeType.BGV]:
            plaintext_modulus = base_params.get("plaintext_modulus")

        parameters = FHEParameters(
            polynomial_modulus_degree=base_params["poly_modulus_degree"],
            coefficient_modulus=coeff_modulus,
            plaintext_modulus=plaintext_modulus,
            scale=scale,
            security_level=security_level,
            scheme_type=scheme_type,
            noise_standard_deviation=base_params["noise_std"],
        )

        self.logger.info(
            f"Generated {scheme_type.value} parameters for "
            f"{security_level.value} security: "
            f"N={parameters.polynomial_modulus_degree}, "
            f"log(q)={sum(math.log2(q) for q in coeff_modulus):.1f}"
        )

        return parameters

    def _generate_coefficient_modulus(self, bit_sizes: List[int]) -> List[int]:
        """
        Generate coefficient modulus primes from bit sizes.

        Args:
            bit_sizes: List of bit sizes for each prime

        Returns:
            List of prime numbers for coefficient modulus
        """
        primes = []
        for bits in bit_sizes:
            prime = self._generate_prime(bits)
            primes.append(prime)

        return primes

    def _generate_prime(self, bits: int) -> int:
        """
        Generate a prime number with the specified bit length.

        Args:
            bits: Number of bits for the prime

        Returns:
            A prime number with the specified bit length
        """
        # For polynomial modulus degree N, we need primes ≡ 1 (mod 2N)
        # This ensures NTT can be performed

        min_val = 2 ** (bits - 1)
        max_val = 2**bits - 1

        # Start with a random odd number in the range
        candidate = random.randrange(min_val | 1, max_val, 2)

        while not self._is_prime(candidate):
            candidate += 2
            if candidate > max_val:
                candidate = min_val | 1

        return candidate

    def _is_prime(self, n: int) -> bool:
        """
        Check if a number is prime using Miller-Rabin test.

        Args:
            n: Number to test for primality

        Returns:
            True if n is probably prime, False otherwise
        """
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False

        # Miller-Rabin primality test
        r = 0
        d = n - 1
        while d % 2 == 0:
            r += 1
            d //= 2

        # Perform test with multiple witnesses
        for _ in range(10):  # 10 rounds for high confidence
            a = random.randrange(2, n - 1)
            x = pow(a, d, n)

            if x == 1 or x == n - 1:
                continue

            for _ in range(r - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False

        return True

    def estimate_noise_growth(
        self, parameters: FHEParameters, operation_sequence: List[str]
    ) -> float:
        """
        Estimate noise growth for a sequence of operations.

        Args:
            parameters: FHE parameters
            operation_sequence: List of operations ('add', 'mult', 'relin', etc.)

        Returns:
            Estimated final noise variance
        """
        # Initial noise variance
        noise_var = parameters.noise_standard_deviation**2

        for op in operation_sequence:
            if op == "add":
                # Addition doubles noise variance
                noise_var *= 2
            elif op in ["mult", "multiply"]:
                # Multiplication significantly increases noise
                noise_var *= parameters.polynomial_modulus_degree
            elif op == "relin":
                # Relinearization adds some noise
                noise_var += parameters.noise_standard_deviation**2

        return math.sqrt(noise_var)

    def suggest_parameters(
        self, scheme_type: SchemeType, required_depth: int, batch_size: Optional[int] = None
    ) -> Tuple[SecurityLevel, FHEParameters]:
        """
        Suggest optimal parameters for a given computation depth.

        Args:
            scheme_type: The FHE scheme type
            required_depth: Required multiplicative depth
            batch_size: Required batch size for CKKS

        Returns:
            Tuple of (recommended security level, parameters)
        """
        # Start with lowest security level and increase if needed
        for security_level in [SecurityLevel.LOW, SecurityLevel.MEDIUM, SecurityLevel.HIGH]:
            try:
                params = self.generate_parameters(scheme_type, security_level)

                # Check if parameters support required depth
                max_depth = self._estimate_max_depth(params)

                if max_depth >= required_depth:
                    # Check batch size for CKKS
                    if scheme_type == SchemeType.CKKS and batch_size:
                        max_batch = params.polynomial_modulus_degree // 2
                        if max_batch < batch_size:
                            continue

                    self.logger.info(
                        f"Recommended {security_level.value} security "
                        f"for depth {required_depth}"
                    )
                    return security_level, params

            except ParameterException:
                continue

        # If no suitable parameters found, recommend ultra security
        return SecurityLevel.ULTRA, self.generate_parameters(scheme_type, SecurityLevel.ULTRA)

    def _estimate_max_depth(self, parameters: FHEParameters) -> int:
        """
        Estimate maximum multiplicative depth for given parameters.

        Args:
            parameters: FHE parameters

        Returns:
            Estimated maximum multiplicative depth
        """
        # Simplified depth estimation based on coefficient modulus
        total_bits = sum(math.log2(q) for q in parameters.coefficient_modulus)

        if parameters.scheme_type == SchemeType.CKKS:
            # CKKS needs bits for scaling
            scale_bits = math.log2(parameters.scale) if parameters.scale else 40
            return int((total_bits - 60) / scale_bits)  # Reserve 60 bits for security
        else:
            # BFV/BGV depth estimation
            return int(total_bits / 30)  # Rough estimate
