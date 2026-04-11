"""
BFV (Brakerski-Fan-Vercauteren) Scheme Implementation.

The BFV scheme enables exact arithmetic on encrypted integers,
making it suitable for applications requiring precise computations
without approximation errors.
"""

import math
from typing import List, Dict, Any, Optional, Union
import logging

from ..core.base import FHECore, FHEConfiguration, SchemeType, CiphertextBase, PlaintextBase
from ..core.parameters import ParameterGenerator, FHEParameters
from ..core.keys import KeyGenerator, PublicKey, SecretKey, RelinearizationKeys, GaloisKeys
from ..core.encryption import Encryptor, Decryptor, Ciphertext, Plaintext
from ..core.evaluation import Evaluator
from ..core.polynomial import Polynomial, PolynomialRing
from ..core.utils import HomomorphicUtils

logger = logging.getLogger(__name__)


class BFVPlaintext(PlaintextBase):
    """BFV-specific plaintext for integer arithmetic."""
    
    def __init__(self, values: Union[List[int], int], plaintext_modulus: int):
        """
        Initialize BFV plaintext.
        
        Args:
            values: Integer values to encode
            plaintext_modulus: Plaintext modulus for reduction
        """
        if isinstance(values, int):
            values = [values]
        
        # Reduce values modulo plaintext modulus
        self.integer_values = [v % plaintext_modulus for v in values]
        self.plaintext_modulus = plaintext_modulus
        
        super().__init__(self.integer_values)
        self.encoding = "bfv_packed"
    
    def __str__(self) -> str:
        return f"BFVPlaintext(values={len(self.integer_values)}, mod={self.plaintext_modulus})"


class BFVCiphertext(CiphertextBase):
    """BFV-specific ciphertext with noise tracking."""
    
    def __init__(self, polynomials: List[Polynomial], level: int = 0, noise_budget: Optional[int] = None):
        """
        Initialize BFV ciphertext.
        
        Args:
            polynomials: Polynomials representing the ciphertext
            level: Current level in the modulus chain
            noise_budget: Remaining noise budget in bits
        """
        super().__init__(polynomials)
        self.level = level
        self.noise_budget = noise_budget
    
    def __str__(self) -> str:
        return f"BFVCiphertext(size={self.size}, level={self.level}, noise_budget={self.noise_budget})"


class BFVBatchEncoder:
    """
    BFV batch encoder for SIMD-style operations.
    
    Uses Chinese Remainder Theorem to pack multiple integers
    into a single polynomial, enabling vectorized operations.
    """
    
    def __init__(self, polynomial_modulus_degree: int, plaintext_modulus: int):
        """
        Initialize BFV batch encoder.
        
        Args:
            polynomial_modulus_degree: Degree of polynomial modulus
            plaintext_modulus: Plaintext modulus
        """
        self.N = polynomial_modulus_degree
        self.t = plaintext_modulus
        
        # Calculate slot count for batching
        self.slots = self._calculate_slot_count()
        
        logger.debug(f"BFV batch encoder initialized: N={self.N}, t={self.t}, slots={self.slots}")
    
    def _calculate_slot_count(self) -> int:
        """Calculate the number of slots available for batching."""
        # For BFV batching, we need t to be prime and t ≡ 1 (mod 2N)
        # This is a simplified calculation
        if self._is_prime(self.t) and (self.t - 1) % (2 * self.N) == 0:
            return self.N
        else:
            # Fallback: no batching available
            return 1
    
    def _is_prime(self, n: int) -> bool:
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
    
    def encode(self, values: List[int]) -> BFVPlaintext:
        """
        Encode integers into a BFV plaintext.
        
        Args:
            values: Integer values to encode
        
        Returns:
            Encoded BFV plaintext
        """
        if self.slots == 1:
            # No batching - simple coefficient encoding
            coefficients = values[:self.N]
            if len(coefficients) < self.N:
                coefficients.extend([0] * (self.N - len(coefficients)))
        else:
            # Batched encoding using CRT
            coefficients = self._batch_encode_crt(values)
        
        # Reduce modulo plaintext modulus
        coefficients = [c % self.t for c in coefficients]
        
        plaintext = BFVPlaintext(values, self.t)
        plaintext.polynomial = Polynomial(coefficients, None)  # Ring will be set by scheme
        
        return plaintext
    
    def decode(self, plaintext: BFVPlaintext) -> List[int]:
        """
        Decode a BFV plaintext back to integers.
        
        Args:
            plaintext: BFV plaintext to decode
        
        Returns:
            List of integer values
        """
        coefficients = plaintext.polynomial.coefficients
        
        if self.slots == 1:
            # Simple coefficient decoding
            return [c for c in coefficients if c != 0]
        else:
            # Batched decoding using CRT
            return self._batch_decode_crt(coefficients)
    
    def _batch_encode_crt(self, values: List[int]) -> List[int]:
        """
        Encode values using Chinese Remainder Theorem for batching.
        
        Args:
            values: Values to encode
        
        Returns:
            Polynomial coefficients
        """
        # Simplified CRT encoding
        # In practice, this would use proper CRT with factor base
        
        # Pad or truncate to slot count
        padded_values = values[:self.slots]
        if len(padded_values) < self.slots:
            padded_values.extend([0] * (self.slots - len(padded_values)))
        
        # Simple coefficient mapping (placeholder for real CRT)
        coefficients = [0] * self.N
        for i, val in enumerate(padded_values):
            if i < self.N:
                coefficients[i] = val
        
        return coefficients
    
    def _batch_decode_crt(self, coefficients: List[int]) -> List[int]:
        """
        Decode coefficients using Chinese Remainder Theorem.
        
        Args:
            coefficients: Polynomial coefficients
        
        Returns:
            Decoded values
        """
        # Simplified CRT decoding (placeholder)
        return coefficients[:self.slots]


class BFVScheme(FHECore):
    """
    Complete BFV scheme implementation.
    
    Provides encryption, decryption, and homomorphic operations on
    exact integers with optional SIMD-style batching.
    """
    
    def __init__(self, config: FHEConfiguration):
        """
        Initialize BFV scheme.
        
        Args:
            config: FHE configuration for BFV
        """
        if config.scheme_type != SchemeType.BFV:
            raise ValueError("Configuration must be for BFV scheme")
        
        super().__init__(config)
        
        # Generate parameters
        param_gen = ParameterGenerator()
        self.parameters = param_gen.generate_parameters(
            config.scheme_type,
            config.security_level,
            {
                "poly_modulus_degree": config.polynomial_modulus_degree,
                "coeff_modulus_bits": self._infer_modulus_bits(config.coefficient_modulus),
                "plaintext_modulus": config.plaintext_modulus
            }
        )
        
        # Initialize components
        self.batch_encoder = BFVBatchEncoder(
            self.parameters.polynomial_modulus_degree,
            self.parameters.plaintext_modulus
        )
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
        
        logger.info(f"BFV scheme initialized with plaintext modulus {self.parameters.plaintext_modulus}")
    
    def _infer_modulus_bits(self, coefficient_modulus: List[int]) -> List[int]:
        """Infer bit sizes from coefficient modulus."""
        return [int(math.log2(q)) for q in coefficient_modulus]
    
    def generate_keys(self) -> Dict[str, Any]:
        """
        Generate all necessary keys for the BFV scheme.
        
        Returns:
            Dictionary containing all generated keys
        """
        # Generate secret key
        self.secret_key = self.key_generator.generate_secret_key()
        
        # Generate public key
        self.public_key = self.key_generator.generate_public_key(self.secret_key)
        
        # Generate relinearization keys
        self.relin_keys = self.key_generator.generate_relinearization_keys(self.secret_key)
        
        # Generate Galois keys for rotations (if batching is enabled)
        if self.batch_encoder.slots > 1:
            rotation_steps = self._get_rotation_steps()
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
        
        logger.info("Generated complete BFV key set")
        return keys
    
    def _get_rotation_steps(self) -> List[int]:
        """Get rotation steps for Galois keys."""
        if self.batch_encoder.slots <= 1:
            return []
        
        steps = []
        
        # Powers of 2
        power = 1
        while power < self.batch_encoder.slots:
            steps.append(power)
            power *= 2
        
        return steps
    
    def encode(self, values: Union[List[int], int]) -> BFVPlaintext:
        """
        Encode integer values into a BFV plaintext.
        
        Args:
            values: Integer values to encode
        
        Returns:
            Encoded BFV plaintext
        """
        if isinstance(values, int):
            values = [values]
        
        return self.batch_encoder.encode(values)
    
    def decode(self, plaintext: BFVPlaintext) -> List[int]:
        """
        Decode a BFV plaintext to integer values.
        
        Args:
            plaintext: BFV plaintext to decode
        
        Returns:
            List of integer values
        """
        return self.batch_encoder.decode(plaintext)
    
    def encrypt(self, plaintext: Union[BFVPlaintext, List[int], int], 
                public_key: Optional[PublicKey] = None) -> BFVCiphertext:
        """
        Encrypt a plaintext or values.
        
        Args:
            plaintext: Plaintext to encrypt or values to encode and encrypt
            public_key: Public key (uses instance key if None)
        
        Returns:
            Encrypted ciphertext
        """
        if not isinstance(plaintext, BFVPlaintext):
            # Encode values first
            plaintext = self.encode(plaintext)
        
        if public_key is None:
            if self.encryptor is None:
                raise ValueError("No encryptor available - generate keys first")
            encryptor = self.encryptor
        else:
            encryptor = Encryptor(self.parameters, public_key)
        
        # Convert to standard plaintext format
        std_plaintext = Plaintext(plaintext.polynomial.coefficients, encoding="bfv_packed")
        
        # Encrypt
        std_ciphertext = encryptor.encrypt(std_plaintext)
        
        # Convert to BFV ciphertext
        bfv_ciphertext = BFVCiphertext(
            std_ciphertext.polynomials,
            std_ciphertext.level if hasattr(std_ciphertext, 'level') else 0
        )
        
        return bfv_ciphertext
    
    def decrypt(self, ciphertext: BFVCiphertext, 
                secret_key: Optional[SecretKey] = None) -> BFVPlaintext:
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
        std_ciphertext = Ciphertext(ciphertext.polynomials, level=ciphertext.level)
        
        # Decrypt
        std_plaintext = decryptor.decrypt(std_ciphertext, "bfv_packed")
        
        # Convert to BFV plaintext
        polynomial = Polynomial(std_plaintext.data, None)
        bfv_plaintext = BFVPlaintext([], self.parameters.plaintext_modulus)
        bfv_plaintext.polynomial = polynomial
        
        # Decode to get integer values
        bfv_plaintext.integer_values = self.batch_encoder.decode(bfv_plaintext)
        
        return bfv_plaintext
    
    def add(self, ciphertext1: BFVCiphertext, ciphertext2: BFVCiphertext) -> BFVCiphertext:
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
        
        # Convert to standard format
        std_ct1 = Ciphertext(ciphertext1.polynomials, level=ciphertext1.level)
        std_ct2 = Ciphertext(ciphertext2.polynomials, level=ciphertext2.level)
        
        # Perform addition
        result_std = self.evaluator.add(std_ct1, std_ct2)
        
        # Convert back to BFV format
        result = BFVCiphertext(
            result_std.polynomials,
            result_std.level if hasattr(result_std, 'level') else 0
        )
        
        return result
    
    def subtract(self, ciphertext1: BFVCiphertext, ciphertext2: BFVCiphertext) -> BFVCiphertext:
        """
        Homomorphic subtraction of two ciphertexts.
        
        Args:
            ciphertext1: First ciphertext (minuend)
            ciphertext2: Second ciphertext (subtrahend)
        
        Returns:
            Difference of the ciphertexts
        """
        if self.evaluator is None:
            raise ValueError("No evaluator available - generate keys first")
        
        # Convert to standard format
        std_ct1 = Ciphertext(ciphertext1.polynomials, level=ciphertext1.level)
        std_ct2 = Ciphertext(ciphertext2.polynomials, level=ciphertext2.level)
        
        # Perform subtraction
        result_std = self.evaluator.subtract(std_ct1, std_ct2)
        
        # Convert back to BFV format
        result = BFVCiphertext(
            result_std.polynomials,
            result_std.level if hasattr(result_std, 'level') else 0
        )
        
        return result
    
    def multiply(self, ciphertext1: BFVCiphertext, ciphertext2: BFVCiphertext) -> BFVCiphertext:
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
        std_ct1 = Ciphertext(ciphertext1.polynomials, level=ciphertext1.level)
        std_ct2 = Ciphertext(ciphertext2.polynomials, level=ciphertext2.level)
        
        # Perform multiplication
        result_std = self.evaluator.multiply(std_ct1, std_ct2)
        
        # Relinearize to reduce size
        result_std = self.evaluator.relinearize(result_std)
        
        # Convert back to BFV format
        result = BFVCiphertext(
            result_std.polynomials,
            result_std.level if hasattr(result_std, 'level') else 0
        )
        
        return result
    
    def add_plain(self, ciphertext: BFVCiphertext, 
                  plaintext: Union[BFVPlaintext, List[int], int]) -> BFVCiphertext:
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
        if isinstance(plaintext, (list, int)):
            plaintext = self.encode(plaintext)
        
        if not isinstance(plaintext, BFVPlaintext):
            raise TypeError("Invalid plaintext type")
        
        # Convert to standard format
        std_ct = Ciphertext(ciphertext.polynomials, level=ciphertext.level)
        std_pt_poly = Polynomial(plaintext.polynomial.coefficients, None)
        
        # Perform addition
        result_std = self.evaluator.add_plain(std_ct, std_pt_poly)
        
        # Convert back to BFV format
        result = BFVCiphertext(
            result_std.polynomials,
            result_std.level if hasattr(result_std, 'level') else 0
        )
        
        return result
    
    def multiply_plain(self, ciphertext: BFVCiphertext, 
                      plaintext: Union[BFVPlaintext, List[int], int]) -> BFVCiphertext:
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
        if isinstance(plaintext, (list, int)):
            plaintext = self.encode(plaintext)
        
        if not isinstance(plaintext, BFVPlaintext):
            raise TypeError("Invalid plaintext type")
        
        # Convert to standard format
        std_ct = Ciphertext(ciphertext.polynomials, level=ciphertext.level)
        std_pt_poly = Polynomial(plaintext.polynomial.coefficients, None)
        
        # Perform multiplication
        result_std = self.evaluator.multiply_plain(std_ct, std_pt_poly)
        
        # Convert back to BFV format
        result = BFVCiphertext(
            result_std.polynomials,
            result_std.level if hasattr(result_std, 'level') else 0
        )
        
        return result
    
    def rotate_rows(self, ciphertext: BFVCiphertext, steps: int) -> BFVCiphertext:
        """
        Rotate rows in batched ciphertext.
        
        Args:
            ciphertext: Input ciphertext
            steps: Number of rotation steps
        
        Returns:
            Rotated ciphertext
        """
        if self.evaluator is None or self.batch_encoder.slots <= 1:
            raise ValueError("Rotation not available without batching")
        
        # Convert to standard format
        std_ct = Ciphertext(ciphertext.polynomials, level=ciphertext.level)
        
        # Perform rotation
        result_std = self.evaluator.rotate_vector(std_ct, steps)
        
        # Convert back to BFV format
        result = BFVCiphertext(
            result_std.polynomials,
            result_std.level if hasattr(result_std, 'level') else ciphertext.level
        )
        
        return result
    
    def negate(self, ciphertext: BFVCiphertext) -> BFVCiphertext:
        """
        Negate a ciphertext.
        
        Args:
            ciphertext: Input ciphertext
        
        Returns:
            Negated ciphertext
        """
        if self.evaluator is None:
            raise ValueError("No evaluator available - generate keys first")
        
        # Convert to standard format
        std_ct = Ciphertext(ciphertext.polynomials, level=ciphertext.level)
        
        # Perform negation
        result_std = self.evaluator.negate(std_ct)
        
        # Convert back to BFV format
        result = BFVCiphertext(
            result_std.polynomials,
            result_std.level if hasattr(result_std, 'level') else 0
        )
        
        return result
    
    def square(self, ciphertext: BFVCiphertext) -> BFVCiphertext:
        """
        Square a ciphertext.
        
        Args:
            ciphertext: Input ciphertext
        
        Returns:
            Squared ciphertext
        """
        return self.multiply(ciphertext, ciphertext)
    
    def modulus_switch_to_next(self, ciphertext: BFVCiphertext) -> BFVCiphertext:
        """
        Switch ciphertext to next smaller modulus level.
        
        Args:
            ciphertext: Input ciphertext
        
        Returns:
            Ciphertext at next modulus level
        """
        # BFV modulus switching implementation would go here
        # For now, return a copy with incremented level
        result = BFVCiphertext(
            [Polynomial(poly.coefficients.copy(), poly.ring) for poly in ciphertext.polynomials],
            ciphertext.level + 1,
            ciphertext.noise_budget
        )
        
        return result
    
    def get_noise_budget(self, ciphertext: BFVCiphertext) -> int:
        """
        Estimate remaining noise budget in bits.
        
        Args:
            ciphertext: Ciphertext to analyze
        
        Returns:
            Estimated noise budget in bits
        """
        if self.decryptor is None:
            return 0
        
        # Use decryptor's noise estimation
        std_ciphertext = Ciphertext(ciphertext.polynomials, level=ciphertext.level)
        return self.decryptor.estimate_noise_budget(std_ciphertext)
    
    def get_scheme_info(self) -> Dict[str, Any]:
        """Get information about the BFV scheme configuration."""
        base_info = super().get_scheme_info()
        
        bfv_info = {
            "plaintext_modulus": self.parameters.plaintext_modulus,
            "batching_enabled": self.batch_encoder.slots > 1,
            "batch_slots": self.batch_encoder.slots,
            "exact_arithmetic": True,
            "current_keys_generated": {
                "public_key": self.public_key is not None,
                "secret_key": self.secret_key is not None,
                "relinearization_keys": self.relin_keys is not None,
                "galois_keys": self.galois_keys is not None
            }
        }
        
        base_info.update(bfv_info)
        return base_info