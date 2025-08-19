"""
Homomorphic evaluation operations for ciphertexts.
"""

import numpy as np
from typing import List, Optional, Union
import logging

from .base import EvaluationException, NoiseException
from .parameters import FHEParameters
from .keys import RelinearizationKeys, GaloisKeys
from .encryption import Ciphertext
from .polynomial import Polynomial, PolynomialRing
from .modular import ModularArithmetic

logger = logging.getLogger(__name__)


class Evaluator:
    """
    Homomorphic evaluator for performing operations on encrypted data.
    
    Provides arithmetic operations (addition, multiplication), rotation,
    and other advanced operations on ciphertexts.
    """
    
    def __init__(self, parameters: FHEParameters, 
                 relin_keys: Optional[RelinearizationKeys] = None,
                 galois_keys: Optional[GaloisKeys] = None):
        """
        Initialize the evaluator.
        
        Args:
            parameters: FHE parameters
            relin_keys: Relinearization keys (optional)
            galois_keys: Galois keys for rotations (optional)
        """
        self.parameters = parameters
        self.relin_keys = relin_keys
        self.galois_keys = galois_keys
        
        self.poly_ring = PolynomialRing(
            parameters.polynomial_modulus_degree,
            parameters.coefficient_modulus
        )
        self.modular = ModularArithmetic(parameters.coefficient_modulus)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Noise growth tracking
        self.operation_count = 0
        self.multiplication_depth = 0
    
    def add(self, ciphertext1: Ciphertext, ciphertext2: Ciphertext) -> Ciphertext:
        """
        Homomorphic addition of two ciphertexts.
        
        Args:
            ciphertext1: First ciphertext
            ciphertext2: Second ciphertext
        
        Returns:
            Sum of the two ciphertexts
        """
        self._validate_ciphertexts_compatible(ciphertext1, ciphertext2)
        
        try:
            # Ensure same size by padding with zeros if necessary
            max_size = max(ciphertext1.size, ciphertext2.size)
            
            result_polys = []
            for i in range(max_size):
                if i < ciphertext1.size and i < ciphertext2.size:
                    # Add corresponding polynomials
                    sum_poly = self.poly_ring.add(
                        ciphertext1.polynomials[i],
                        ciphertext2.polynomials[i]
                    )
                elif i < ciphertext1.size:
                    # Copy from first ciphertext
                    sum_poly = ciphertext1.polynomials[i]
                else:
                    # Copy from second ciphertext
                    sum_poly = ciphertext2.polynomials[i]
                
                result_polys.append(sum_poly)
            
            # Result scale (for CKKS)
            result_scale = ciphertext1.scale
            if ciphertext2.scale and ciphertext1.scale:
                if abs(ciphertext1.scale - ciphertext2.scale) > 1e-6:
                    self.logger.warning("Adding ciphertexts with different scales")
                result_scale = (ciphertext1.scale + ciphertext2.scale) / 2
            
            result = Ciphertext(
                result_polys, 
                result_scale,
                max(ciphertext1.level, ciphertext2.level),
                ciphertext1.is_ntt_form and ciphertext2.is_ntt_form
            )
            
            self.operation_count += 1
            self.logger.debug(f"Added two ciphertexts (size {result.size})")
            
            return result
            
        except Exception as e:
            raise EvaluationException(f"Addition failed: {e}")
    
    def subtract(self, ciphertext1: Ciphertext, ciphertext2: Ciphertext) -> Ciphertext:
        """
        Homomorphic subtraction of two ciphertexts.
        
        Args:
            ciphertext1: First ciphertext (minuend)
            ciphertext2: Second ciphertext (subtrahend)
        
        Returns:
            Difference of the two ciphertexts
        """
        self._validate_ciphertexts_compatible(ciphertext1, ciphertext2)
        
        try:
            # Negate second ciphertext and add
            negated_ct2 = self.negate(ciphertext2)
            return self.add(ciphertext1, negated_ct2)
            
        except Exception as e:
            raise EvaluationException(f"Subtraction failed: {e}")
    
    def multiply(self, ciphertext1: Ciphertext, ciphertext2: Ciphertext) -> Ciphertext:
        """
        Homomorphic multiplication of two ciphertexts.
        
        Args:
            ciphertext1: First ciphertext
            ciphertext2: Second ciphertext
        
        Returns:
            Product of the two ciphertexts
        """
        self._validate_ciphertexts_compatible(ciphertext1, ciphertext2)
        
        try:
            # Ciphertext multiplication produces size-1 result
            result_size = ciphertext1.size + ciphertext2.size - 1
            result_polys = [self.poly_ring.zero_polynomial()] * result_size
            
            # Polynomial multiplication
            for i in range(ciphertext1.size):
                for j in range(ciphertext2.size):
                    product = self.poly_ring.multiply(
                        ciphertext1.polynomials[i],
                        ciphertext2.polynomials[j]
                    )
                    result_polys[i + j] = self.poly_ring.add(
                        result_polys[i + j], 
                        product
                    )
            
            # Result scale (for CKKS)
            result_scale = None
            if ciphertext1.scale and ciphertext2.scale:
                result_scale = ciphertext1.scale * ciphertext2.scale
            
            result = Ciphertext(
                result_polys,
                result_scale,
                max(ciphertext1.level, ciphertext2.level),
                ciphertext1.is_ntt_form and ciphertext2.is_ntt_form
            )
            
            self.operation_count += 1
            self.multiplication_depth += 1
            self.logger.debug(f"Multiplied two ciphertexts (result size {result.size})")
            
            return result
            
        except Exception as e:
            raise EvaluationException(f"Multiplication failed: {e}")
    
    def add_plain(self, ciphertext: Ciphertext, plaintext_poly: Polynomial) -> Ciphertext:
        """
        Add a plaintext polynomial to a ciphertext.
        
        Args:
            ciphertext: Input ciphertext
            plaintext_poly: Plaintext polynomial to add
        
        Returns:
            Sum of ciphertext and plaintext
        """
        try:
            result_polys = ciphertext.polynomials.copy()
            
            # Add plaintext to the first polynomial (constant term)
            result_polys[0] = self.poly_ring.add(result_polys[0], plaintext_poly)
            
            result = Ciphertext(
                result_polys,
                ciphertext.scale,
                ciphertext.level,
                ciphertext.is_ntt_form
            )
            
            self.operation_count += 1
            self.logger.debug("Added plaintext to ciphertext")
            
            return result
            
        except Exception as e:
            raise EvaluationException(f"Plaintext addition failed: {e}")
    
    def multiply_plain(self, ciphertext: Ciphertext, plaintext_poly: Polynomial) -> Ciphertext:
        """
        Multiply a ciphertext by a plaintext polynomial.
        
        Args:
            ciphertext: Input ciphertext
            plaintext_poly: Plaintext polynomial to multiply by
        
        Returns:
            Product of ciphertext and plaintext
        """
        try:
            result_polys = []
            
            # Multiply each polynomial in the ciphertext
            for poly in ciphertext.polynomials:
                product = self.poly_ring.multiply(poly, plaintext_poly)
                result_polys.append(product)
            
            result = Ciphertext(
                result_polys,
                ciphertext.scale,
                ciphertext.level,
                ciphertext.is_ntt_form
            )
            
            self.operation_count += 1
            self.logger.debug("Multiplied ciphertext by plaintext")
            
            return result
            
        except Exception as e:
            raise EvaluationException(f"Plaintext multiplication failed: {e}")
    
    def negate(self, ciphertext: Ciphertext) -> Ciphertext:
        """
        Negate a ciphertext.
        
        Args:
            ciphertext: Input ciphertext
        
        Returns:
            Negated ciphertext
        """
        try:
            result_polys = []
            
            for poly in ciphertext.polynomials:
                negated_poly = self.poly_ring.negate(poly)
                result_polys.append(negated_poly)
            
            result = Ciphertext(
                result_polys,
                ciphertext.scale,
                ciphertext.level,
                ciphertext.is_ntt_form
            )
            
            self.logger.debug("Negated ciphertext")
            return result
            
        except Exception as e:
            raise EvaluationException(f"Negation failed: {e}")
    
    def relinearize(self, ciphertext: Ciphertext) -> Ciphertext:
        """
        Relinearize a ciphertext to reduce its size.
        
        Args:
            ciphertext: Input ciphertext (typically size > 2)
        
        Returns:
            Relinearized ciphertext (size 2)
        """
        if not self.relin_keys:
            raise EvaluationException("Relinearization keys not provided")
        
        if ciphertext.size <= 2:
            return ciphertext  # Already linearized
        
        try:
            # Relinearize from size 3 to size 2 (most common case)
            if ciphertext.size == 3:
                c0, c1, c2 = ciphertext.polynomials
                
                # Decompose c2 for key switching
                decomposed = self._decompose_polynomial(c2)
                
                # Apply relinearization keys
                relin_result = self._apply_key_switching(decomposed, self.relin_keys.key_matrices[0])
                
                # Combine results
                new_c0 = self.poly_ring.add(c0, relin_result[0])
                new_c1 = self.poly_ring.add(c1, relin_result[1])
                
                result = Ciphertext(
                    [new_c0, new_c1],
                    ciphertext.scale,
                    ciphertext.level,
                    ciphertext.is_ntt_form
                )
                
                self.logger.debug("Relinearized ciphertext from size 3 to 2")
                return result
            
            else:
                # For higher sizes, apply iteratively
                current = ciphertext
                while current.size > 2:
                    # Extract last polynomial and relinearize
                    c_high = current.polynomials[-1]
                    c_rest = current.polynomials[:-1]
                    
                    # Apply relinearization
                    decomposed = self._decompose_polynomial(c_high)
                    level = min(current.size - 3, len(self.relin_keys.key_matrices) - 1)
                    relin_result = self._apply_key_switching(
                        decomposed, 
                        self.relin_keys.key_matrices[level]
                    )
                    
                    # Update ciphertext
                    c_rest[0] = self.poly_ring.add(c_rest[0], relin_result[0])
                    c_rest[1] = self.poly_ring.add(c_rest[1], relin_result[1])
                    
                    current = Ciphertext(
                        c_rest,
                        current.scale,
                        current.level,
                        current.is_ntt_form
                    )
                
                self.logger.debug(f"Relinearized ciphertext from size {ciphertext.size} to 2")
                return current
            
        except Exception as e:
            raise EvaluationException(f"Relinearization failed: {e}")
    
    def rescale(self, ciphertext: Ciphertext) -> Ciphertext:
        """
        Rescale a ciphertext (primarily for CKKS).
        
        Args:
            ciphertext: Input ciphertext
        
        Returns:
            Rescaled ciphertext
        """
        if not ciphertext.scale:
            raise EvaluationException("Cannot rescale ciphertext without scale")
        
        try:
            # Drop the last modulus and rescale
            if ciphertext.level >= len(self.parameters.coefficient_modulus) - 1:
                raise EvaluationException("Cannot rescale further - no moduli remaining")
            
            new_level = ciphertext.level + 1
            dropped_modulus = self.parameters.coefficient_modulus[new_level]
            new_scale = ciphertext.scale / dropped_modulus
            
            # Rescale each polynomial
            result_polys = []
            for poly in ciphertext.polynomials:
                # Divide coefficients by dropped modulus and round
                new_coeffs = []
                for coeff in poly.coefficients:
                    new_coeff = round(coeff / dropped_modulus)
                    new_coeffs.append(new_coeff)
                
                # Create new polynomial with reduced modulus chain
                new_poly = Polynomial(new_coeffs, self.poly_ring)
                result_polys.append(new_poly)
            
            result = Ciphertext(
                result_polys,
                new_scale,
                new_level,
                ciphertext.is_ntt_form
            )
            
            self.logger.debug(f"Rescaled ciphertext (level {ciphertext.level} -> {new_level})")
            return result
            
        except Exception as e:
            raise EvaluationException(f"Rescaling failed: {e}")
    
    def rotate_vector(self, ciphertext: Ciphertext, steps: int) -> Ciphertext:
        """
        Rotate the encrypted vector by the specified number of steps.
        
        Args:
            ciphertext: Input ciphertext
            steps: Number of rotation steps
        
        Returns:
            Rotated ciphertext
        """
        if not self.galois_keys:
            raise EvaluationException("Galois keys not provided for rotation")
        
        try:
            # Compute Galois element for this rotation
            galois_element = self._compute_galois_element(steps)
            
            if galois_element not in self.galois_keys.key_map:
                raise EvaluationException(f"Galois key for {steps} steps not available")
            
            # Apply Galois automorphism to each polynomial
            rotated_polys = []
            for poly in ciphertext.polynomials:
                rotated_poly = self._apply_galois_automorphism(poly, galois_element)
                rotated_polys.append(rotated_poly)
            
            # Apply key switching for the second polynomial
            if len(rotated_polys) > 1:
                # Key switching for c1
                decomposed = self._decompose_polynomial(rotated_polys[1])
                switched_result = self._apply_key_switching(
                    decomposed,
                    [self.galois_keys.key_map[galois_element]]
                )
                
                # Update result
                rotated_polys[0] = self.poly_ring.add(rotated_polys[0], switched_result[0])
                rotated_polys[1] = switched_result[1]
            
            result = Ciphertext(
                rotated_polys,
                ciphertext.scale,
                ciphertext.level,
                ciphertext.is_ntt_form
            )
            
            self.logger.debug(f"Rotated ciphertext by {steps} steps")
            return result
            
        except Exception as e:
            raise EvaluationException(f"Rotation failed: {e}")
    
    def _validate_ciphertexts_compatible(self, ct1: Ciphertext, ct2: Ciphertext) -> None:
        """Validate that two ciphertexts are compatible for operations."""
        if ct1.level != ct2.level:
            raise EvaluationException("Ciphertexts have different levels")
        
        if ct1.is_ntt_form != ct2.is_ntt_form:
            raise EvaluationException("Ciphertexts have different NTT forms")
    
    def _decompose_polynomial(self, polynomial: Polynomial, base: int = 2**60) -> List[Polynomial]:
        """
        Decompose a polynomial for key switching.
        
        Args:
            polynomial: Polynomial to decompose
            base: Decomposition base
        
        Returns:
            List of decomposed polynomials
        """
        decomposed = []
        num_levels = len(self.parameters.coefficient_modulus)
        
        for level in range(num_levels):
            level_coeffs = []
            
            for coeff in polynomial.coefficients:
                # Extract level-th "digit" in base representation
                level_coeff = (coeff // (base ** level)) % base
                level_coeffs.append(level_coeff)
            
            decomposed.append(Polynomial(level_coeffs, self.poly_ring))
        
        return decomposed
    
    def _apply_key_switching(self, decomposed_polys: List[Polynomial], 
                           key_switching_keys: List[List[Polynomial]]) -> List[Polynomial]:
        """
        Apply key switching using decomposed polynomials.
        
        Args:
            decomposed_polys: List of decomposed polynomials
            key_switching_keys: Key switching keys
        
        Returns:
            Result of key switching
        """
        result = [self.poly_ring.zero_polynomial(), self.poly_ring.zero_polynomial()]
        
        for i, decomposed_poly in enumerate(decomposed_polys):
            if i < len(key_switching_keys):
                key_pair = key_switching_keys[i]
                
                # Multiply by key switching keys
                term0 = self.poly_ring.multiply(decomposed_poly, key_pair[0])
                term1 = self.poly_ring.multiply(decomposed_poly, key_pair[1])
                
                # Add to result
                result[0] = self.poly_ring.add(result[0], term0)
                result[1] = self.poly_ring.add(result[1], term1)
        
        return result
    
    def _compute_galois_element(self, steps: int) -> int:
        """Compute Galois element for rotation by steps."""
        n = self.parameters.polynomial_modulus_degree
        m = 2 * n
        
        # For rotation by k steps: primitive_root^k mod m
        primitive_root = 5  # Common choice
        return pow(primitive_root, steps, m)
    
    def _apply_galois_automorphism(self, polynomial: Polynomial, galois_element: int) -> Polynomial:
        """Apply Galois automorphism to a polynomial."""
        n = self.parameters.polynomial_modulus_degree
        m = 2 * n
        
        new_coeffs = [0] * n
        
        for i, coeff in enumerate(polynomial.coefficients):
            if coeff != 0:
                new_power = (galois_element * i) % m
                
                if new_power < n:
                    new_coeffs[new_power] += coeff
                else:
                    # Handle wrap-around in cyclotomic ring
                    new_coeffs[new_power - n] -= coeff
        
        return Polynomial(new_coeffs, self.poly_ring)
    
    def get_operation_stats(self) -> dict:
        """Get statistics about performed operations."""
        return {
            "total_operations": self.operation_count,
            "multiplication_depth": self.multiplication_depth,
            "estimated_noise_growth": self._estimate_noise_growth()
        }
    
    def _estimate_noise_growth(self) -> float:
        """Estimate cumulative noise growth."""
        # Simplified noise growth estimation
        additive_noise = self.operation_count * 1.1  # Small growth for additions
        multiplicative_noise = (2 ** self.multiplication_depth) * self.parameters.polynomial_modulus_degree
        return additive_noise + multiplicative_noise
    
    def reset_stats(self) -> None:
        """Reset operation statistics."""
        self.operation_count = 0
        self.multiplication_depth = 0