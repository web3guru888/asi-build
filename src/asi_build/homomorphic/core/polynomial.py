"""
Polynomial arithmetic for homomorphic encryption operations.
"""

import numpy as np
from typing import List, Optional, Union
import random
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class Polynomial:
    """
    Polynomial representation for homomorphic encryption.
    
    Represents polynomials in Z[X]/(X^n + 1) with coefficients modulo q.
    """
    
    def __init__(self, coefficients: List[int], ring: 'PolynomialRing'):
        """
        Initialize a polynomial.
        
        Args:
            coefficients: List of polynomial coefficients
            ring: The polynomial ring this polynomial belongs to
        """
        self.ring = ring
        self.degree = ring.degree
        
        # Ensure we have the right number of coefficients
        if len(coefficients) > self.degree:
            # Reduce modulo X^n + 1
            self.coefficients = self._reduce_degree(coefficients)
        elif len(coefficients) < self.degree:
            # Pad with zeros
            self.coefficients = coefficients + [0] * (self.degree - len(coefficients))
        else:
            self.coefficients = coefficients.copy()
        
        # Reduce coefficients modulo the coefficient modulus
        self._reduce_coefficients()
    
    def _reduce_degree(self, coeffs: List[int]) -> List[int]:
        """
        Reduce polynomial degree modulo X^n + 1.
        
        Args:
            coeffs: Input coefficients
        
        Returns:
            Reduced coefficients
        """
        result = [0] * self.degree
        
        for i, coeff in enumerate(coeffs):
            pos = i % self.degree
            
            if i >= self.degree and (i // self.degree) % 2 == 1:
                # X^(n+k) = -X^k in the cyclotomic ring
                result[pos] -= coeff
            else:
                result[pos] += coeff
        
        return result
    
    def _reduce_coefficients(self):
        """Reduce coefficients modulo the coefficient modulus."""
        for i, q in enumerate(self.ring.coefficient_modulus):
            if i < len(self.coefficients):
                self.coefficients[i] = self.coefficients[i] % q
    
    def __add__(self, other: 'Polynomial') -> 'Polynomial':
        """Add two polynomials."""
        if not isinstance(other, Polynomial):
            raise TypeError("Can only add polynomials")
        
        if self.ring != other.ring:
            raise ValueError("Polynomials must be in the same ring")
        
        result_coeffs = [
            (a + b) for a, b in zip(self.coefficients, other.coefficients)
        ]
        
        return Polynomial(result_coeffs, self.ring)
    
    def __sub__(self, other: 'Polynomial') -> 'Polynomial':
        """Subtract two polynomials."""
        if not isinstance(other, Polynomial):
            raise TypeError("Can only subtract polynomials")
        
        if self.ring != other.ring:
            raise ValueError("Polynomials must be in the same ring")
        
        result_coeffs = [
            (a - b) for a, b in zip(self.coefficients, other.coefficients)
        ]
        
        return Polynomial(result_coeffs, self.ring)
    
    def __mul__(self, other: Union['Polynomial', int]) -> 'Polynomial':
        """Multiply polynomial by another polynomial or scalar."""
        if isinstance(other, int):
            # Scalar multiplication
            result_coeffs = [coeff * other for coeff in self.coefficients]
            return Polynomial(result_coeffs, self.ring)
        
        elif isinstance(other, Polynomial):
            if self.ring != other.ring:
                raise ValueError("Polynomials must be in the same ring")
            
            # Polynomial multiplication using NTT
            return self._multiply_ntt(other)
        
        else:
            raise TypeError("Can only multiply by polynomial or integer")
    
    def __rmul__(self, other: int) -> 'Polynomial':
        """Right multiplication by scalar."""
        return self.__mul__(other)
    
    def __neg__(self) -> 'Polynomial':
        """Negate polynomial."""
        result_coeffs = [-coeff for coeff in self.coefficients]
        return Polynomial(result_coeffs, self.ring)
    
    def __eq__(self, other: 'Polynomial') -> bool:
        """Check equality of polynomials."""
        if not isinstance(other, Polynomial):
            return False
        
        return (self.ring == other.ring and 
                self.coefficients == other.coefficients)
    
    def __str__(self) -> str:
        """String representation of polynomial."""
        terms = []
        for i, coeff in enumerate(self.coefficients):
            if coeff != 0:
                if i == 0:
                    terms.append(str(coeff))
                elif i == 1:
                    terms.append(f"{coeff}*X" if coeff != 1 else "X")
                else:
                    terms.append(f"{coeff}*X^{i}" if coeff != 1 else f"X^{i}")
        
        if not terms:
            return "0"
        
        return " + ".join(terms).replace("+ -", "- ")
    
    def __repr__(self) -> str:
        return f"Polynomial({self.coefficients[:5]}..., degree={self.degree})"
    
    def _multiply_ntt(self, other: 'Polynomial') -> 'Polynomial':
        """
        Multiply polynomials using Number Theoretic Transform (NTT).
        
        Args:
            other: Polynomial to multiply with
        
        Returns:
            Product polynomial
        """
        # Convert to NTT form
        self_ntt = self.ring.to_ntt_form(self.coefficients)
        other_ntt = self.ring.to_ntt_form(other.coefficients)
        
        # Component-wise multiplication in NTT domain
        result_ntt = [
            (a * b) % q for a, b, q in zip(
                self_ntt, other_ntt, self.ring.coefficient_modulus
            )
        ]
        
        # Convert back from NTT form
        result_coeffs = self.ring.from_ntt_form(result_ntt)
        
        return Polynomial(result_coeffs, self.ring)
    
    def _multiply_schoolbook(self, other: 'Polynomial') -> 'Polynomial':
        """
        Multiply polynomials using schoolbook method (for small degrees).
        
        Args:
            other: Polynomial to multiply with
        
        Returns:
            Product polynomial
        """
        result_coeffs = [0] * (2 * self.degree - 1)
        
        for i, a in enumerate(self.coefficients):
            for j, b in enumerate(other.coefficients):
                result_coeffs[i + j] += a * b
        
        # Reduce modulo X^n + 1
        return Polynomial(result_coeffs, self.ring)
    
    def evaluate_at(self, point: int) -> int:
        """
        Evaluate polynomial at a given point.
        
        Args:
            point: Point to evaluate at
        
        Returns:
            Polynomial value
        """
        result = 0
        power = 1
        
        for coeff in self.coefficients:
            result += coeff * power
            power *= point
        
        return result
    
    def derivative(self) -> 'Polynomial':
        """
        Compute the derivative of the polynomial.
        
        Returns:
            Derivative polynomial
        """
        if self.degree <= 1:
            return Polynomial([0], self.ring)
        
        deriv_coeffs = [
            i * self.coefficients[i] for i in range(1, self.degree)
        ] + [0]
        
        return Polynomial(deriv_coeffs, self.ring)
    
    def is_zero(self) -> bool:
        """Check if polynomial is zero."""
        return all(coeff == 0 for coeff in self.coefficients)
    
    def norm_squared(self) -> int:
        """Compute the squared norm of the polynomial."""
        return sum(coeff * coeff for coeff in self.coefficients)
    
    def max_coefficient(self) -> int:
        """Get the maximum absolute coefficient."""
        return max(abs(coeff) for coeff in self.coefficients)


class PolynomialRing:
    """
    Polynomial ring Z[X]/(X^n + 1) with coefficient modulus.
    
    Provides operations for polynomials in the cyclotomic ring used
    in homomorphic encryption schemes.
    """
    
    def __init__(self, degree: int, coefficient_modulus: List[int]):
        """
        Initialize the polynomial ring.
        
        Args:
            degree: Polynomial degree (must be power of 2)
            coefficient_modulus: List of moduli for CRT representation
        """
        self.degree = degree
        self.coefficient_modulus = coefficient_modulus
        self.num_moduli = len(coefficient_modulus)
        
        # Validate degree is power of 2
        if degree <= 0 or (degree & (degree - 1)) != 0:
            raise ValueError("Degree must be a power of 2")
        
        # Precompute NTT parameters
        self._init_ntt_parameters()
        
        logger.debug(f"Initialized polynomial ring: degree={degree}, "
                    f"moduli={len(coefficient_modulus)}")
    
    def _init_ntt_parameters(self):
        """Initialize parameters for Number Theoretic Transform."""
        self.ntt_roots = []
        self.inv_ntt_roots = []
        self.inv_degree = []
        
        for q in self.coefficient_modulus:
            # Find primitive 2n-th root of unity modulo q
            root = self._find_primitive_root(q, 2 * self.degree)
            inv_root = pow(root, q - 2, q)  # Modular inverse
            inv_deg = pow(self.degree, q - 2, q)  # Inverse of degree
            
            self.ntt_roots.append(root)
            self.inv_ntt_roots.append(inv_root)
            self.inv_degree.append(inv_deg)
    
    def _find_primitive_root(self, modulus: int, order: int) -> int:
        """
        Find a primitive root of the specified order modulo the given modulus.
        
        Args:
            modulus: The modulus
            order: The required order
        
        Returns:
            Primitive root of the specified order
        """
        # For NTT, we need a primitive 2n-th root of unity
        # Start with a generator and raise to appropriate power
        
        # Simple search for small moduli (should be precomputed for efficiency)
        for candidate in range(2, min(modulus, 1000)):
            if pow(candidate, order, modulus) == 1:
                # Check if it's primitive
                is_primitive = True
                for divisor in self._get_proper_divisors(order):
                    if pow(candidate, divisor, modulus) == 1:
                        is_primitive = False
                        break
                
                if is_primitive:
                    return candidate
        
        # Fallback: use a known primitive root formula
        # For primes p ≡ 1 (mod 2n), there exist primitive 2n-th roots
        return 3  # Simple fallback
    
    def _get_proper_divisors(self, n: int) -> List[int]:
        """Get proper divisors of n."""
        divisors = []
        for i in range(1, int(n**0.5) + 1):
            if n % i == 0:
                divisors.append(i)
                if i != n // i and i != 1:
                    divisors.append(n // i)
        return divisors
    
    def to_ntt_form(self, coefficients: List[int]) -> List[int]:
        """
        Convert polynomial coefficients to NTT form.
        
        Args:
            coefficients: Polynomial coefficients
        
        Returns:
            NTT-transformed coefficients
        """
        result = []
        
        for i, q in enumerate(self.coefficient_modulus):
            # Apply NTT for this modulus
            ntt_coeffs = self._ntt_forward(
                [c % q for c in coefficients], 
                q, 
                self.ntt_roots[i]
            )
            result.extend(ntt_coeffs)
        
        return result
    
    def from_ntt_form(self, ntt_coefficients: List[int]) -> List[int]:
        """
        Convert from NTT form back to polynomial coefficients.
        
        Args:
            ntt_coefficients: NTT-transformed coefficients
        
        Returns:
            Polynomial coefficients
        """
        # Split coefficients by modulus
        mod_coeffs = []
        chunk_size = self.degree
        
        for i in range(self.num_moduli):
            start = i * chunk_size
            end = start + chunk_size
            mod_coeffs.append(ntt_coefficients[start:end])
        
        # Apply inverse NTT for each modulus
        poly_coeffs = []
        for i, coeffs in enumerate(mod_coeffs):
            q = self.coefficient_modulus[i]
            inv_ntt_coeffs = self._ntt_inverse(
                coeffs, q, self.inv_ntt_roots[i], self.inv_degree[i]
            )
            poly_coeffs.append(inv_ntt_coeffs)
        
        # Use Chinese Remainder Theorem to combine
        return self._crt_combine(poly_coeffs)
    
    def _ntt_forward(self, coeffs: List[int], modulus: int, root: int) -> List[int]:
        """
        Forward Number Theoretic Transform.
        
        Args:
            coeffs: Input coefficients
            modulus: Modulus for arithmetic
            root: Primitive root
        
        Returns:
            NTT-transformed coefficients
        """
        n = len(coeffs)
        if n == 1:
            return coeffs.copy()
        
        # Bit-reverse permutation
        result = [0] * n
        for i in range(n):
            j = self._bit_reverse(i, n)
            result[j] = coeffs[i]
        
        # Cooley-Tukey NTT
        length = 2
        while length <= n:
            w = pow(root, (modulus - 1) // length, modulus)
            for i in range(0, n, length):
                wn = 1
                for j in range(length // 2):
                    u = result[i + j]
                    v = (result[i + j + length // 2] * wn) % modulus
                    result[i + j] = (u + v) % modulus
                    result[i + j + length // 2] = (u - v) % modulus
                    wn = (wn * w) % modulus
            length *= 2
        
        return result
    
    def _ntt_inverse(self, coeffs: List[int], modulus: int, inv_root: int, inv_n: int) -> List[int]:
        """
        Inverse Number Theoretic Transform.
        
        Args:
            coeffs: NTT coefficients
            modulus: Modulus for arithmetic
            inv_root: Inverse of primitive root
            inv_n: Inverse of n modulo modulus
        
        Returns:
            Original coefficients
        """
        result = self._ntt_forward(coeffs, modulus, inv_root)
        
        # Multiply by inverse of n
        for i in range(len(result)):
            result[i] = (result[i] * inv_n) % modulus
        
        return result
    
    def _bit_reverse(self, num: int, length: int) -> int:
        """Bit-reverse a number for the given length."""
        result = 0
        for _ in range(length.bit_length() - 1):
            result = (result << 1) | (num & 1)
            num >>= 1
        return result
    
    def _crt_combine(self, mod_coeffs: List[List[int]]) -> List[int]:
        """
        Combine coefficients using Chinese Remainder Theorem.
        
        Args:
            mod_coeffs: Coefficients for each modulus
        
        Returns:
            Combined coefficients
        """
        if len(mod_coeffs) == 1:
            return mod_coeffs[0]
        
        result = mod_coeffs[0].copy()
        current_modulus = self.coefficient_modulus[0]
        
        for i in range(1, len(mod_coeffs)):
            next_modulus = self.coefficient_modulus[i]
            next_coeffs = mod_coeffs[i]
            
            # Extended Euclidean algorithm for CRT
            inv_current = pow(current_modulus, next_modulus - 2, next_modulus)
            inv_next = pow(next_modulus, current_modulus - 2, current_modulus)
            
            new_result = []
            new_modulus = current_modulus * next_modulus
            
            for j in range(self.degree):
                # CRT formula
                x1 = result[j]
                x2 = next_coeffs[j]
                
                combined = (
                    x1 * next_modulus * inv_next +
                    x2 * current_modulus * inv_current
                ) % new_modulus
                
                new_result.append(combined)
            
            result = new_result
            current_modulus = new_modulus
        
        return result
    
    def zero_polynomial(self) -> Polynomial:
        """Create the zero polynomial."""
        return Polynomial([0] * self.degree, self)
    
    def one_polynomial(self) -> Polynomial:
        """Create the polynomial representing 1."""
        coeffs = [1] + [0] * (self.degree - 1)
        return Polynomial(coeffs, self)
    
    def random_polynomial(self, max_coeff: Optional[int] = None) -> Polynomial:
        """
        Generate a random polynomial.
        
        Args:
            max_coeff: Maximum coefficient value (uses modulus if None)
        
        Returns:
            Random polynomial
        """
        if max_coeff is None:
            max_coeff = min(self.coefficient_modulus)
        
        coeffs = [random.randint(0, max_coeff - 1) for _ in range(self.degree)]
        return Polynomial(coeffs, self)
    
    def add(self, poly1: Polynomial, poly2: Polynomial) -> Polynomial:
        """Add two polynomials."""
        return poly1 + poly2
    
    def subtract(self, poly1: Polynomial, poly2: Polynomial) -> Polynomial:
        """Subtract two polynomials."""
        return poly1 - poly2
    
    def multiply(self, poly1: Polynomial, poly2: Polynomial) -> Polynomial:
        """Multiply two polynomials."""
        return poly1 * poly2
    
    def scalar_multiply(self, poly: Polynomial, scalar: int) -> Polynomial:
        """Multiply polynomial by scalar."""
        return poly * scalar
    
    def negate(self, poly: Polynomial) -> Polynomial:
        """Negate a polynomial."""
        return -poly
    
    def __eq__(self, other: 'PolynomialRing') -> bool:
        """Check equality of polynomial rings."""
        return (self.degree == other.degree and 
                self.coefficient_modulus == other.coefficient_modulus)
    
    def __str__(self) -> str:
        return f"PolynomialRing(degree={self.degree}, moduli={len(self.coefficient_modulus)})"