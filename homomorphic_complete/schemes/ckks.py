"""
CKKS (Cheon-Kim-Kim-Song) Scheme Implementation.

The CKKS scheme enables approximate arithmetic on encrypted real/complex numbers,
making it ideal for privacy-preserving machine learning and signal processing.
"""

import numpy as np
import math
import cmath
from typing import List, Dict, Any, Optional, Union, Tuple
import logging

from ..core.base import FHECore, FHEConfiguration, SchemeType, CiphertextBase, PlaintextBase
from ..core.parameters import ParameterGenerator, FHEParameters
from ..core.keys import KeyGenerator, PublicKey, SecretKey, RelinearizationKeys, GaloisKeys
from ..core.encryption import Encryptor, Decryptor, Ciphertext, Plaintext
from ..core.evaluation import Evaluator
from ..core.polynomial import Polynomial, PolynomialRing
from ..core.utils import HomomorphicUtils

logger = logging.getLogger(__name__)


class CKKSPlaintext(PlaintextBase):
    """CKKS-specific plaintext with complex number support."""
    
    def __init__(self, values: Union[List[complex], np.ndarray], scale: float):
        """
        Initialize CKKS plaintext.
        
        Args:
            values: Complex values to encode
            scale: Scaling factor for fixed-point representation
        """
        self.complex_values = np.array(values, dtype=complex)
        self.scale = scale
        super().__init__(self.complex_values, scale)
        self.encoding = "ckks_packed"
    
    def __str__(self) -> str:
        return f"CKKSPlaintext(slots={len(self.complex_values)}, scale={self.scale:.0f})"


class CKKSCiphertext(CiphertextBase):
    """CKKS-specific ciphertext with scale and level tracking."""
    
    def __init__(self, polynomials: List[Polynomial], scale: float, level: int = 0):
        """
        Initialize CKKS ciphertext.
        
        Args:
            polynomials: Polynomials representing the ciphertext
            scale: Current scale factor
            level: Current level in the modulus chain
        """
        super().__init__(polynomials, scale)
        self.level = level
        self.slots = len(polynomials[0].coefficients) // 2  # Number of complex slots
    
    def __str__(self) -> str:
        return f"CKKSCiphertext(size={self.size}, slots={self.slots}, scale={self.scale:.0f}, level={self.level})"


class CKKSEncoder:
    """
    CKKS encoder for converting between complex values and polynomials.
    
    Uses the canonical embedding to map complex vectors to polynomial
    coefficients, enabling packed SIMD operations.
    """
    
    def __init__(self, polynomial_modulus_degree: int):
        """
        Initialize CKKS encoder.
        
        Args:
            polynomial_modulus_degree: Degree of polynomial modulus
        """
        self.N = polynomial_modulus_degree
        self.M = 2 * self.N  # Cyclotomic polynomial degree
        self.slots = self.N // 2  # Number of complex slots
        
        # Precompute roots of unity for FFT/iFFT
        self._precompute_fft_roots()
        
        logger.debug(f"CKKS encoder initialized: N={self.N}, slots={self.slots}")
    
    def _precompute_fft_roots(self):
        """Precompute roots of unity for encoding/decoding."""
        # Primitive M-th root of unity
        zeta_M = cmath.exp(2j * cmath.pi / self.M)
        
        # Roots for canonical embedding
        self.sigma_roots = []
        for j in range(self.slots):
            exponent = (2 * j + 1)
            root = zeta_M ** exponent
            self.sigma_roots.append(root)
        
        self.sigma_roots = np.array(self.sigma_roots)
    
    def encode(self, values: Union[List[complex], np.ndarray], scale: float) -> CKKSPlaintext:
        """
        Encode complex values into a CKKS plaintext.
        
        Args:
            values: Complex values to encode (max self.slots values)
            scale: Scaling factor
        
        Returns:
            Encoded CKKS plaintext
        """
        values = np.array(values, dtype=complex)
        
        # Pad or truncate to slot count
        if len(values) > self.slots:
            values = values[:self.slots]
        elif len(values) < self.slots:
            values = np.pad(values, (0, self.slots - len(values)), mode='constant')
        
        # Apply scaling
        scaled_values = values * scale
        
        # Inverse canonical embedding (complex domain -> coefficient domain)
        coefficients = self._inverse_canonical_embedding(scaled_values)
        
        # Convert to integers with rounding
        int_coefficients = [int(round(coeff.real)) for coeff in coefficients]
        
        # Create polynomial
        polynomial = Polynomial(int_coefficients, None)  # Ring will be set by scheme
        
        plaintext = CKKSPlaintext(values, scale)
        plaintext.polynomial = polynomial
        
        return plaintext
    
    def decode(self, plaintext: CKKSPlaintext) -> np.ndarray:
        """
        Decode a CKKS plaintext back to complex values.
        
        Args:
            plaintext: CKKS plaintext to decode
        
        Returns:
            Array of complex values
        """
        # Get polynomial coefficients
        coefficients = plaintext.polynomial.coefficients
        
        # Convert to complex representation
        complex_coeffs = np.array(coefficients, dtype=complex)
        
        # Apply canonical embedding (coefficient domain -> complex domain)
        values = self._canonical_embedding(complex_coeffs)
        
        # Descale
        descaled_values = values / plaintext.scale
        
        return descaled_values[:self.slots]
    
    def _canonical_embedding(self, coefficients: np.ndarray) -> np.ndarray:
        """
        Apply canonical embedding to map polynomial to complex values.
        
        Args:
            coefficients: Polynomial coefficients
        
        Returns:
            Complex values
        """
        # Evaluate polynomial at roots of unity
        values = np.zeros(self.slots, dtype=complex)
        
        for i, root in enumerate(self.sigma_roots):
            # Evaluate polynomial at this root
            value = 0
            power = 1
            for coeff in coefficients:
                value += coeff * power
                power *= root
            values[i] = value
        
        return values
    
    def _inverse_canonical_embedding(self, values: np.ndarray) -> np.ndarray:
        """
        Apply inverse canonical embedding to map complex values to polynomial.
        
        Args:
            values: Complex values
        
        Returns:
            Polynomial coefficients
        """
        # Use FFT-based approach for efficiency
        # This is a simplified implementation - production would use optimized FFT
        
        # Extend to full cyclotomic ring
        extended_values = np.zeros(self.N, dtype=complex)
        extended_values[:self.slots] = values
        extended_values[self.slots:] = np.conj(values[::-1])  # Complex conjugate symmetry
        
        # Apply inverse DFT
        coefficients = np.fft.ifft(extended_values) * self.N
        
        # Take real part (should be real due to conjugate symmetry)
        real_coefficients = coefficients.real
        
        return real_coefficients


class CKKSScheme(FHECore):
    """
    Complete CKKS scheme implementation.
    
    Provides encryption, decryption, and homomorphic operations on
    approximate real/complex numbers with SIMD-style batching.
    """
    
    def __init__(self, config: FHEConfiguration):
        """
        Initialize CKKS scheme.
        
        Args:
            config: FHE configuration for CKKS
        """
        if config.scheme_type != SchemeType.CKKS:
            raise ValueError("Configuration must be for CKKS scheme")
        
        super().__init__(config)
        
        # Generate parameters
        param_gen = ParameterGenerator()
        self.parameters = param_gen.generate_parameters(
            config.scheme_type,
            config.security_level,
            {
                "poly_modulus_degree": config.polynomial_modulus_degree,
                "coeff_modulus_bits": self._infer_modulus_bits(config.coefficient_modulus),
                "scale_bits": int(math.log2(config.scale)) if config.scale else 40
            }
        )
        
        # Initialize components
        self.encoder = CKKSEncoder(self.parameters.polynomial_modulus_degree)
        self.key_generator = KeyGenerator(self.parameters)
        
        # Keys (will be generated when needed)
        self.public_key = None
        self.secret_key = None
        self.relin_keys = None
        self.galois_keys = None
        
        # Components (will be initialized after key generation)
        self.encryptor = None
        self.decryptor = None
        self.evaluator = None
        
        logger.info(f"CKKS scheme initialized with {self.encoder.slots} slots")
    
    def _infer_modulus_bits(self, coefficient_modulus: List[int]) -> List[int]:
        """Infer bit sizes from coefficient modulus."""
        return [int(math.log2(q)) for q in coefficient_modulus]
    
    def generate_keys(self) -> Dict[str, Any]:
        """
        Generate all necessary keys for the CKKS scheme.
        
        Returns:
            Dictionary containing all generated keys
        """
        # Generate secret key
        self.secret_key = self.key_generator.generate_secret_key()
        
        # Generate public key
        self.public_key = self.key_generator.generate_public_key(self.secret_key)
        
        # Generate relinearization keys
        self.relin_keys = self.key_generator.generate_relinearization_keys(self.secret_key)
        
        # Generate Galois keys for common rotations
        rotation_steps = self._get_standard_rotation_steps()
        self.galois_keys = self.key_generator.generate_galois_keys(self.secret_key, rotation_steps)
        
        # Initialize encryptor, decryptor, and evaluator
        self.encryptor = Encryptor(self.parameters, self.public_key)
        self.decryptor = Decryptor(self.parameters, self.secret_key)
        self.evaluator = Evaluator(self.parameters, self.relin_keys, self.galois_keys)
        
        keys = {
            "secret_key": self.secret_key,
            "public_key": self.public_key,
            "relinearization_keys": self.relin_keys,
            "galois_keys": self.galois_keys
        }
        
        logger.info("Generated complete CKKS key set")
        return keys
    
    def _get_standard_rotation_steps(self) -> List[int]:
        """Get standard rotation steps for Galois keys."""
        steps = []
        
        # Powers of 2 up to slots/2
        power = 1
        while power <= self.encoder.slots // 2:
            steps.append(power)
            steps.append(-power)  # Both directions
            power *= 2
        
        # Some additional useful rotations
        for step in [3, 5, 7, 15, 31]:
            if step < self.encoder.slots:
                steps.append(step)
                steps.append(-step)
        
        return list(set(steps))  # Remove duplicates
    
    def encode(self, values: Union[List[complex], np.ndarray], scale: Optional[float] = None) -> CKKSPlaintext:
        """
        Encode complex values into a CKKS plaintext.
        
        Args:
            values: Complex values to encode
            scale: Scaling factor (uses default if None)
        
        Returns:
            Encoded CKKS plaintext
        """
        if scale is None:
            scale = self.parameters.scale
        
        return self.encoder.encode(values, scale)
    
    def decode(self, plaintext: CKKSPlaintext) -> np.ndarray:
        """
        Decode a CKKS plaintext to complex values.
        
        Args:
            plaintext: CKKS plaintext to decode
        
        Returns:
            Array of complex values
        """
        return self.encoder.decode(plaintext)
    
    def encrypt(self, plaintext: Union[CKKSPlaintext, List, np.ndarray], 
                public_key: Optional[PublicKey] = None) -> CKKSCiphertext:
        """
        Encrypt a plaintext or values.
        
        Args:
            plaintext: Plaintext to encrypt or values to encode and encrypt
            public_key: Public key (uses instance key if None)
        
        Returns:
            Encrypted ciphertext
        """
        if not isinstance(plaintext, CKKSPlaintext):
            # Encode values first
            plaintext = self.encode(plaintext)
        
        if public_key is None:
            if self.encryptor is None:
                raise ValueError("No encryptor available - generate keys first")
            encryptor = self.encryptor
        else:
            encryptor = Encryptor(self.parameters, public_key)
        
        # Convert to standard plaintext format
        std_plaintext = Plaintext(plaintext.polynomial.coefficients, plaintext.scale, "ckks_packed")
        
        # Encrypt
        std_ciphertext = encryptor.encrypt(std_plaintext)
        
        # Convert to CKKS ciphertext
        ckks_ciphertext = CKKSCiphertext(
            std_ciphertext.polynomials,
            std_ciphertext.scale,
            std_ciphertext.level if hasattr(std_ciphertext, 'level') else 0
        )
        
        return ckks_ciphertext
    
    def decrypt(self, ciphertext: CKKSCiphertext, 
                secret_key: Optional[SecretKey] = None) -> CKKSPlaintext:
        """
        Decrypt a ciphertext.
        
        Args:
            ciphertext: Ciphertext to decrypt
            secret_key: Secret key (uses instance key if None)
        
        Returns:
            Decrypted plaintext
        """
        if secret_key is None:
            if self.decryptor is None:
                raise ValueError("No decryptor available - generate keys first")
            decryptor = self.decryptor
        else:
            decryptor = Decryptor(self.parameters, secret_key)
        
        # Convert to standard ciphertext format
        std_ciphertext = Ciphertext(ciphertext.polynomials, ciphertext.scale, ciphertext.level)
        
        # Decrypt
        std_plaintext = decryptor.decrypt(std_ciphertext, "ckks_packed")
        
        # Convert to CKKS plaintext
        polynomial = Polynomial(std_plaintext.data, None)
        ckks_plaintext = CKKSPlaintext([], std_plaintext.scale)
        ckks_plaintext.polynomial = polynomial
        
        # Decode to get complex values
        ckks_plaintext.complex_values = self.encoder.decode(ckks_plaintext)
        
        return ckks_plaintext
    
    def add(self, ciphertext1: CKKSCiphertext, ciphertext2: CKKSCiphertext) -> CKKSCiphertext:
        """
        Homomorphic addition of two ciphertexts.
        
        Args:
            ciphertext1: First ciphertext
            ciphertext2: Second ciphertext
        
        Returns:
            Sum of the ciphertexts
        """
        if self.evaluator is None:
            raise ValueError("No evaluator available - generate keys first")
        
        # Check scale compatibility
        if abs(ciphertext1.scale - ciphertext2.scale) > 1e-6:
            raise ValueError("Ciphertexts must have the same scale for addition")
        
        # Convert to standard format
        std_ct1 = Ciphertext(ciphertext1.polynomials, ciphertext1.scale, ciphertext1.level)
        std_ct2 = Ciphertext(ciphertext2.polynomials, ciphertext2.scale, ciphertext2.level)
        
        # Perform addition
        result_std = self.evaluator.add(std_ct1, std_ct2)
        
        # Convert back to CKKS format
        result = CKKSCiphertext(
            result_std.polynomials,
            result_std.scale,
            result_std.level if hasattr(result_std, 'level') else 0
        )
        
        return result
    
    def multiply(self, ciphertext1: CKKSCiphertext, ciphertext2: CKKSCiphertext) -> CKKSCiphertext:
        """
        Homomorphic multiplication of two ciphertexts.
        
        Args:
            ciphertext1: First ciphertext
            ciphertext2: Second ciphertext
        
        Returns:
            Product of the ciphertexts
        """
        if self.evaluator is None:
            raise ValueError("No evaluator available - generate keys first")
        
        # Convert to standard format
        std_ct1 = Ciphertext(ciphertext1.polynomials, ciphertext1.scale, ciphertext1.level)
        std_ct2 = Ciphertext(ciphertext2.polynomials, ciphertext2.scale, ciphertext2.level)
        
        # Perform multiplication
        result_std = self.evaluator.multiply(std_ct1, std_ct2)
        
        # Relinearize
        result_std = self.evaluator.relinearize(result_std)
        
        # Convert back to CKKS format
        result = CKKSCiphertext(
            result_std.polynomials,
            result_std.scale,
            result_std.level if hasattr(result_std, 'level') else 0
        )
        
        return result
    
    def add_plain(self, ciphertext: CKKSCiphertext, 
                  plaintext: Union[CKKSPlaintext, List, np.ndarray, complex]) -> CKKSCiphertext:
        """
        Add a plaintext to a ciphertext.
        
        Args:
            ciphertext: Input ciphertext
            plaintext: Plaintext to add
        
        Returns:
            Sum of ciphertext and plaintext
        """
        if self.evaluator is None:
            raise ValueError("No evaluator available - generate keys first")
        
        # Handle different plaintext types
        if isinstance(plaintext, (list, np.ndarray)):
            plaintext = self.encode(plaintext, ciphertext.scale)
        elif isinstance(plaintext, complex):
            plaintext = self.encode([plaintext], ciphertext.scale)
        
        if not isinstance(plaintext, CKKSPlaintext):
            raise TypeError("Invalid plaintext type")
        
        # Convert to standard format
        std_ct = Ciphertext(ciphertext.polynomials, ciphertext.scale, ciphertext.level)
        std_pt_poly = Polynomial(plaintext.polynomial.coefficients, None)
        
        # Perform addition
        result_std = self.evaluator.add_plain(std_ct, std_pt_poly)
        
        # Convert back to CKKS format
        result = CKKSCiphertext(
            result_std.polynomials,
            result_std.scale,
            result_std.level if hasattr(result_std, 'level') else 0
        )
        
        return result
    
    def multiply_plain(self, ciphertext: CKKSCiphertext, 
                      plaintext: Union[CKKSPlaintext, List, np.ndarray, complex]) -> CKKSCiphertext:
        """
        Multiply a ciphertext by a plaintext.
        
        Args:
            ciphertext: Input ciphertext
            plaintext: Plaintext to multiply by
        
        Returns:
            Product of ciphertext and plaintext
        """
        if self.evaluator is None:
            raise ValueError("No evaluator available - generate keys first")
        
        # Handle different plaintext types
        if isinstance(plaintext, (list, np.ndarray)):
            plaintext = self.encode(plaintext, ciphertext.scale)
        elif isinstance(plaintext, complex):
            plaintext = self.encode([plaintext], ciphertext.scale)
        
        if not isinstance(plaintext, CKKSPlaintext):
            raise TypeError("Invalid plaintext type")
        
        # Convert to standard format
        std_ct = Ciphertext(ciphertext.polynomials, ciphertext.scale, ciphertext.level)
        std_pt_poly = Polynomial(plaintext.polynomial.coefficients, None)
        
        # Perform multiplication
        result_std = self.evaluator.multiply_plain(std_ct, std_pt_poly)
        
        # Convert back to CKKS format
        result = CKKSCiphertext(
            result_std.polynomials,
            result_std.scale,
            result_std.level if hasattr(result_std, 'level') else 0
        )
        
        return result
    
    def rescale(self, ciphertext: CKKSCiphertext) -> CKKSCiphertext:
        """
        Rescale a ciphertext to manage noise and scale growth.
        
        Args:
            ciphertext: Ciphertext to rescale
        
        Returns:
            Rescaled ciphertext
        """
        if self.evaluator is None:
            raise ValueError("No evaluator available - generate keys first")
        
        # Convert to standard format
        std_ct = Ciphertext(ciphertext.polynomials, ciphertext.scale, ciphertext.level)
        
        # Perform rescaling
        result_std = self.evaluator.rescale(std_ct)
        
        # Convert back to CKKS format
        result = CKKSCiphertext(
            result_std.polynomials,
            result_std.scale,
            result_std.level if hasattr(result_std, 'level') else ciphertext.level + 1
        )
        
        return result
    
    def rotate_vector(self, ciphertext: CKKSCiphertext, steps: int) -> CKKSCiphertext:
        """
        Rotate the encrypted vector by the specified number of steps.
        
        Args:
            ciphertext: Input ciphertext
            steps: Number of rotation steps
        
        Returns:
            Rotated ciphertext
        """
        if self.evaluator is None:
            raise ValueError("No evaluator available - generate keys first")
        
        # Convert to standard format
        std_ct = Ciphertext(ciphertext.polynomials, ciphertext.scale, ciphertext.level)
        
        # Perform rotation
        result_std = self.evaluator.rotate_vector(std_ct, steps)
        
        # Convert back to CKKS format
        result = CKKSCiphertext(
            result_std.polynomials,
            result_std.scale,
            result_std.level if hasattr(result_std, 'level') else ciphertext.level
        )
        
        return result
    
    def conjugate(self, ciphertext: CKKSCiphertext) -> CKKSCiphertext:
        """
        Compute complex conjugate of encrypted values.
        
        Args:
            ciphertext: Input ciphertext
        
        Returns:
            Conjugated ciphertext
        """
        # Complex conjugation is equivalent to rotation by N/2
        return self.rotate_vector(ciphertext, self.encoder.slots)
    
    def sum_elements(self, ciphertext: CKKSCiphertext) -> CKKSCiphertext:
        """
        Sum all elements in the encrypted vector.
        
        Args:
            ciphertext: Input ciphertext
        
        Returns:
            Ciphertext with the sum in all slots
        """
        result = ciphertext
        
        # Use tree reduction with rotations
        step = 1
        while step < self.encoder.slots:
            rotated = self.rotate_vector(result, step)
            result = self.add(result, rotated)
            step *= 2
        
        return result
    
    def dot_product(self, ciphertext1: CKKSCiphertext, ciphertext2: CKKSCiphertext) -> CKKSCiphertext:
        """
        Compute dot product of two encrypted vectors.
        
        Args:
            ciphertext1: First encrypted vector
            ciphertext2: Second encrypted vector
        
        Returns:
            Ciphertext containing the dot product
        """
        # Element-wise multiplication
        product = self.multiply(ciphertext1, ciphertext2)
        
        # Sum all elements
        return self.sum_elements(product)
    
    def polynomial_evaluation(self, ciphertext: CKKSCiphertext, 
                            coefficients: List[complex]) -> CKKSCiphertext:
        """
        Evaluate a polynomial on encrypted values using Horner's method.
        
        Args:
            ciphertext: Input ciphertext
            coefficients: Polynomial coefficients (constant term first)
        
        Returns:
            Result of polynomial evaluation
        """
        if not coefficients:
            raise ValueError("Polynomial coefficients cannot be empty")
        
        # Start with the highest degree term
        result = self.multiply_plain(ciphertext, coefficients[-1])
        
        # Horner's method: work backwards through coefficients
        for coeff in reversed(coefficients[:-1]):
            result = self.multiply(result, ciphertext)
            if coeff != 0:
                coeff_plaintext = self.encode([coeff] * self.encoder.slots, result.scale)
                result = self.add_plain(result, coeff_plaintext)
        
        return result
    
    def matrix_vector_multiply(self, matrix_rows: List[CKKSCiphertext], 
                             vector: CKKSCiphertext) -> List[CKKSCiphertext]:
        """
        Multiply an encrypted matrix by an encrypted vector.
        
        Args:
            matrix_rows: List of ciphertexts representing matrix rows
            vector: Encrypted vector
        
        Returns:
            List of ciphertexts representing the result vector
        """
        result = []
        
        for row in matrix_rows:
            # Compute dot product of row with vector
            dot_product = self.dot_product(row, vector)
            result.append(dot_product)
        
        return result
    
    def get_scheme_info(self) -> Dict[str, Any]:
        """Get information about the CKKS scheme configuration."""
        base_info = super().get_scheme_info()
        
        ckks_info = {
            "slots": self.encoder.slots,
            "complex_precision": f"~{int(math.log2(self.parameters.scale))} bits",
            "max_levels": len(self.parameters.coefficient_modulus) - 1,
            "current_keys_generated": {
                "public_key": self.public_key is not None,
                "secret_key": self.secret_key is not None,
                "relinearization_keys": self.relin_keys is not None,
                "galois_keys": self.galois_keys is not None
            }
        }
        
        base_info.update(ckks_info)
        return base_info