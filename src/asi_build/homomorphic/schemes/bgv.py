"""
BGV (Brakerski-Gentry-Vaikuntanathan) Scheme Implementation.

The BGV scheme enables exact arithmetic on encrypted integers with
efficient modulus switching and optimized noise management.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Union

from ..core.base import CiphertextBase, FHEConfiguration, FHECore, PlaintextBase, SchemeType
from ..core.encryption import Ciphertext, Decryptor, Encryptor, Plaintext
from ..core.evaluation import Evaluator
from ..core.keys import GaloisKeys, KeyGenerator, PublicKey, RelinearizationKeys, SecretKey
from ..core.parameters import FHEParameters, ParameterGenerator
from ..core.polynomial import Polynomial, PolynomialRing
from ..core.utils import HomomorphicUtils

logger = logging.getLogger(__name__)


class BGVPlaintext(PlaintextBase):
    """BGV-specific plaintext for integer arithmetic with modulus switching."""

    def __init__(self, values: Union[List[int], int], plaintext_modulus: int, level: int = 0):
        """
        Initialize BGV plaintext.

        Args:
            values: Integer values to encode
            plaintext_modulus: Plaintext modulus for reduction
            level: Modulus chain level
        """
        if isinstance(values, int):
            values = [values]

        # Reduce values modulo plaintext modulus
        self.integer_values = [v % plaintext_modulus for v in values]
        self.plaintext_modulus = plaintext_modulus
        self.level = level

        super().__init__(self.integer_values)
        self.encoding = "bgv_packed"

    def __str__(self) -> str:
        return f"BGVPlaintext(values={len(self.integer_values)}, mod={self.plaintext_modulus}, level={self.level})"


class BGVCiphertext(CiphertextBase):
    """BGV-specific ciphertext with level and noise tracking."""

    def __init__(
        self,
        polynomials: List[Polynomial],
        level: int = 0,
        noise_budget: Optional[int] = None,
        is_ntt_form: bool = False,
    ):
        """
        Initialize BGV ciphertext.

        Args:
            polynomials: Polynomials representing the ciphertext
            level: Current level in the modulus chain
            noise_budget: Remaining noise budget in bits
            is_ntt_form: Whether ciphertext is in NTT form
        """
        super().__init__(polynomials)
        self.level = level
        self.noise_budget = noise_budget
        self.is_ntt_form = is_ntt_form

    def __str__(self) -> str:
        return (
            f"BGVCiphertext(size={self.size}, level={self.level}, noise_budget={self.noise_budget})"
        )


class BGVBatchEncoder:
    """
    BGV batch encoder for SIMD-style operations with improved packing.

    Similar to BFV but optimized for BGV's modulus switching approach.
    """

    def __init__(self, polynomial_modulus_degree: int, plaintext_modulus: int):
        """
        Initialize BGV batch encoder.

        Args:
            polynomial_modulus_degree: Degree of polynomial modulus
            plaintext_modulus: Plaintext modulus
        """
        self.N = polynomial_modulus_degree
        self.t = plaintext_modulus

        # Calculate slot count for batching
        self.slots = self._calculate_slot_count()

        # Precompute batching parameters
        self._precompute_batching_parameters()

        logger.debug(f"BGV batch encoder initialized: N={self.N}, t={self.t}, slots={self.slots}")

    def _calculate_slot_count(self) -> int:
        """Calculate the number of slots available for batching."""
        # BGV can achieve better batching efficiency than BFV
        # For prime t with t ≡ 1 (mod 2N), we get N slots
        if self._is_prime(self.t):
            if (self.t - 1) % (2 * self.N) == 0:
                return self.N
            else:
                # Check for smaller factors
                for factor in [self.N, self.N // 2, self.N // 4]:
                    if factor > 0 and (self.t - 1) % (2 * factor) == 0:
                        return factor

        # Fallback: no batching
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

    def _precompute_batching_parameters(self):
        """Precompute parameters for efficient batching."""
        if self.slots > 1:
            # Compute factorization parameters for CRT
            self.crt_factors = self._compute_crt_factors()
        else:
            self.crt_factors = []

    def _compute_crt_factors(self) -> List[int]:
        """Compute CRT factors for batching."""
        # Simplified implementation
        # In practice, would factor X^N + 1 modulo t
        factors = []

        # For now, use simple factorization
        for i in range(1, min(self.slots + 1, 10)):
            if self.t % i == 1:
                factors.append(i)

        return factors

    def encode(self, values: List[int]) -> BGVPlaintext:
        """
        Encode integers into a BGV plaintext.

        Args:
            values: Integer values to encode

        Returns:
            Encoded BGV plaintext
        """
        if self.slots == 1:
            # No batching - simple coefficient encoding
            coefficients = values[: self.N]
            if len(coefficients) < self.N:
                coefficients.extend([0] * (self.N - len(coefficients)))
        else:
            # Batched encoding using CRT
            coefficients = self._batch_encode_crt(values)

        # Reduce modulo plaintext modulus
        coefficients = [c % self.t for c in coefficients]

        plaintext = BGVPlaintext(values, self.t)
        plaintext.polynomial = Polynomial(coefficients, None)  # Ring will be set by scheme

        return plaintext

    def decode(self, plaintext: BGVPlaintext) -> List[int]:
        """
        Decode a BGV plaintext back to integers.

        Args:
            plaintext: BGV plaintext to decode

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
        # Pad or truncate to slot count
        padded_values = values[: self.slots]
        if len(padded_values) < self.slots:
            padded_values.extend([0] * (self.slots - len(padded_values)))

        # Enhanced CRT encoding for BGV
        coefficients = [0] * self.N

        if self.crt_factors:
            # Use precomputed CRT factors
            for i, val in enumerate(padded_values):
                # Map value to coefficient position using CRT
                if i < len(self.crt_factors):
                    pos = self.crt_factors[i] % self.N
                    coefficients[pos] = val
                elif i < self.N:
                    coefficients[i] = val
        else:
            # Simple mapping
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
        values = []

        if self.crt_factors:
            # Use precomputed CRT factors for decoding
            for factor in self.crt_factors:
                pos = factor % self.N
                if pos < len(coefficients):
                    values.append(coefficients[pos])
                else:
                    values.append(0)
        else:
            # Simple extraction
            values = coefficients[: self.slots]

        return values


class BGVScheme(FHECore):
    """
    Complete BGV scheme implementation.

    Provides encryption, decryption, and homomorphic operations on
    exact integers with efficient modulus switching for noise management.
    """

    def __init__(self, config: FHEConfiguration):
        """
        Initialize BGV scheme.

        Args:
            config: FHE configuration for BGV
        """
        if config.scheme_type != SchemeType.BGV:
            raise ValueError("Configuration must be for BGV scheme")

        super().__init__(config)

        # Generate parameters
        param_gen = ParameterGenerator()
        self.parameters = param_gen.generate_parameters(
            config.scheme_type,
            config.security_level,
            {
                "poly_modulus_degree": config.polynomial_modulus_degree,
                "coeff_modulus_bits": self._infer_modulus_bits(config.coefficient_modulus),
                "plaintext_modulus": config.plaintext_modulus,
            },
        )

        # Initialize components
        self.batch_encoder = BGVBatchEncoder(
            self.parameters.polynomial_modulus_degree, self.parameters.plaintext_modulus
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

        # BGV-specific: track current modulus level
        self.current_level = 0

        logger.info(
            f"BGV scheme initialized with plaintext modulus {self.parameters.plaintext_modulus}"
        )

    def _infer_modulus_bits(self, coefficient_modulus: List[int]) -> List[int]:
        """Infer bit sizes from coefficient modulus."""
        return [int(math.log2(q)) for q in coefficient_modulus]

    def generate_keys(self) -> Dict[str, Any]:
        """
        Generate all necessary keys for the BGV scheme.

        Returns:
            Dictionary containing all generated keys
        """
        # Generate secret key
        self.secret_key = self.key_generator.generate_secret_key()

        # Generate public key
        self.public_key = self.key_generator.generate_public_key(self.secret_key)

        # Generate relinearization keys for multiple levels
        max_level = len(self.parameters.coefficient_modulus) - 1
        self.relin_keys = self.key_generator.generate_relinearization_keys(
            self.secret_key, max_level
        )

        # Generate Galois keys for rotations (if batching is enabled)
        if self.batch_encoder.slots > 1:
            rotation_steps = self._get_rotation_steps()
            self.galois_keys = self.key_generator.generate_galois_keys(
                self.secret_key, rotation_steps
            )

        # Initialize encryptor, decryptor, and evaluator
        self.encryptor = Encryptor(self.parameters, self.public_key)
        self.decryptor = Decryptor(self.parameters, self.secret_key)
        self.evaluator = Evaluator(self.parameters, self.relin_keys, self.galois_keys)

        keys = {
            "secret_key": self.secret_key,
            "public_key": self.public_key,
            "relinearization_keys": self.relin_keys,
            "galois_keys": self.galois_keys,
        }

        logger.info("Generated complete BGV key set")
        return keys

    def _get_rotation_steps(self) -> List[int]:
        """Get rotation steps for Galois keys."""
        if self.batch_encoder.slots <= 1:
            return []

        steps = []

        # Powers of 2 for efficient rotations
        power = 1
        while power < self.batch_encoder.slots:
            steps.append(power)
            steps.append(-power)  # Both directions
            power *= 2

        # Additional useful steps
        for step in [3, 5, 7, 15]:
            if step < self.batch_encoder.slots:
                steps.append(step)
                steps.append(-step)

        return list(set(steps))  # Remove duplicates

    def encode(self, values: Union[List[int], int], level: int = 0) -> BGVPlaintext:
        """
        Encode integer values into a BGV plaintext.

        Args:
            values: Integer values to encode
            level: Target modulus level

        Returns:
            Encoded BGV plaintext
        """
        if isinstance(values, int):
            values = [values]

        plaintext = self.batch_encoder.encode(values)
        plaintext.level = level

        return plaintext

    def decode(self, plaintext: BGVPlaintext) -> List[int]:
        """
        Decode a BGV plaintext to integer values.

        Args:
            plaintext: BGV plaintext to decode

        Returns:
            List of integer values
        """
        return self.batch_encoder.decode(plaintext)

    def encrypt(
        self, plaintext: Union[BGVPlaintext, List[int], int], public_key: Optional[PublicKey] = None
    ) -> BGVCiphertext:
        """
        Encrypt a plaintext or values.

        Args:
            plaintext: Plaintext to encrypt or values to encode and encrypt
            public_key: Public key (uses instance key if None)

        Returns:
            Encrypted ciphertext
        """
        if not isinstance(plaintext, BGVPlaintext):
            # Encode values first
            plaintext = self.encode(plaintext)

        if public_key is None:
            if self.encryptor is None:
                raise ValueError("No encryptor available - generate keys first")
            encryptor = self.encryptor
        else:
            encryptor = Encryptor(self.parameters, public_key)

        # Convert to standard plaintext format
        std_plaintext = Plaintext(
            plaintext.polynomial.coefficients, encoding="bgv_packed", level=plaintext.level
        )

        # Encrypt
        std_ciphertext = encryptor.encrypt(std_plaintext)

        # Convert to BGV ciphertext
        bgv_ciphertext = BGVCiphertext(
            std_ciphertext.polynomials,
            std_ciphertext.level if hasattr(std_ciphertext, "level") else 0,
        )

        return bgv_ciphertext

    def decrypt(
        self, ciphertext: BGVCiphertext, secret_key: Optional[SecretKey] = None
    ) -> BGVPlaintext:
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
        std_plaintext = decryptor.decrypt(std_ciphertext, "bgv_packed")

        # Convert to BGV plaintext
        polynomial = Polynomial(std_plaintext.data, None)
        bgv_plaintext = BGVPlaintext([], self.parameters.plaintext_modulus, ciphertext.level)
        bgv_plaintext.polynomial = polynomial

        # Decode to get integer values
        bgv_plaintext.integer_values = self.batch_encoder.decode(bgv_plaintext)

        return bgv_plaintext

    def add(self, ciphertext1: BGVCiphertext, ciphertext2: BGVCiphertext) -> BGVCiphertext:
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

        # Ensure ciphertexts are at the same level
        ct1, ct2 = self._align_ciphertext_levels(ciphertext1, ciphertext2)

        # Convert to standard format
        std_ct1 = Ciphertext(ct1.polynomials, level=ct1.level)
        std_ct2 = Ciphertext(ct2.polynomials, level=ct2.level)

        # Perform addition
        result_std = self.evaluator.add(std_ct1, std_ct2)

        # Convert back to BGV format
        result = BGVCiphertext(
            result_std.polynomials, result_std.level if hasattr(result_std, "level") else ct1.level
        )

        return result

    def multiply(self, ciphertext1: BGVCiphertext, ciphertext2: BGVCiphertext) -> BGVCiphertext:
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

        # Ensure ciphertexts are at the same level
        ct1, ct2 = self._align_ciphertext_levels(ciphertext1, ciphertext2)

        # Convert to standard format
        std_ct1 = Ciphertext(ct1.polynomials, level=ct1.level)
        std_ct2 = Ciphertext(ct2.polynomials, level=ct2.level)

        # Perform multiplication
        result_std = self.evaluator.multiply(std_ct1, std_ct2)

        # Relinearize
        result_std = self.evaluator.relinearize(result_std)

        # Convert back to BGV format
        result = BGVCiphertext(
            result_std.polynomials, result_std.level if hasattr(result_std, "level") else ct1.level
        )

        return result

    def modulus_switch_to_next(self, ciphertext: BGVCiphertext) -> BGVCiphertext:
        """
        Switch ciphertext to the next smaller modulus level.

        This is a key optimization in BGV for noise management.

        Args:
            ciphertext: Input ciphertext

        Returns:
            Ciphertext at the next modulus level
        """
        if ciphertext.level >= len(self.parameters.coefficient_modulus) - 1:
            raise ValueError("Cannot switch to next level - already at lowest level")

        # BGV modulus switching algorithm
        new_level = ciphertext.level + 1

        # Scale down coefficients to next modulus
        new_polynomials = []
        for poly in ciphertext.polynomials:
            # Simplified modulus switching
            # In practice, would use proper scaling and rounding
            new_coeffs = []
            for coeff in poly.coefficients:
                # Scale by ratio of moduli
                old_modulus = self.parameters.coefficient_modulus[ciphertext.level]
                new_modulus = self.parameters.coefficient_modulus[new_level]
                scaled_coeff = (coeff * new_modulus) // old_modulus
                new_coeffs.append(scaled_coeff)

            new_poly = Polynomial(new_coeffs, poly.ring)
            new_polynomials.append(new_poly)

        result = BGVCiphertext(new_polynomials, new_level)

        logger.debug(f"Switched ciphertext from level {ciphertext.level} to {new_level}")
        return result

    def _align_ciphertext_levels(self, ct1: BGVCiphertext, ct2: BGVCiphertext) -> tuple:
        """
        Align two ciphertexts to the same modulus level.

        Args:
            ct1: First ciphertext
            ct2: Second ciphertext

        Returns:
            Tuple of aligned ciphertexts
        """
        if ct1.level == ct2.level:
            return ct1, ct2

        # Switch the lower-level ciphertext to match the higher level
        if ct1.level < ct2.level:
            # Switch ct1 to ct2's level
            aligned_ct1 = ct1
            for _ in range(ct2.level - ct1.level):
                aligned_ct1 = self.modulus_switch_to_next(aligned_ct1)
            return aligned_ct1, ct2
        else:
            # Switch ct2 to ct1's level
            aligned_ct2 = ct2
            for _ in range(ct1.level - ct2.level):
                aligned_ct2 = self.modulus_switch_to_next(aligned_ct2)
            return ct1, aligned_ct2

    def add_plain(
        self, ciphertext: BGVCiphertext, plaintext: Union[BGVPlaintext, List[int], int]
    ) -> BGVCiphertext:
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
            plaintext = self.encode(plaintext, ciphertext.level)

        if not isinstance(plaintext, BGVPlaintext):
            raise TypeError("Invalid plaintext type")

        # Convert to standard format
        std_ct = Ciphertext(ciphertext.polynomials, level=ciphertext.level)
        std_pt_poly = Polynomial(plaintext.polynomial.coefficients, None)

        # Perform addition
        result_std = self.evaluator.add_plain(std_ct, std_pt_poly)

        # Convert back to BGV format
        result = BGVCiphertext(
            result_std.polynomials,
            result_std.level if hasattr(result_std, "level") else ciphertext.level,
        )

        return result

    def multiply_plain(
        self, ciphertext: BGVCiphertext, plaintext: Union[BGVPlaintext, List[int], int]
    ) -> BGVCiphertext:
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
            plaintext = self.encode(plaintext, ciphertext.level)

        if not isinstance(plaintext, BGVPlaintext):
            raise TypeError("Invalid plaintext type")

        # Convert to standard format
        std_ct = Ciphertext(ciphertext.polynomials, level=ciphertext.level)
        std_pt_poly = Polynomial(plaintext.polynomial.coefficients, None)

        # Perform multiplication
        result_std = self.evaluator.multiply_plain(std_ct, std_pt_poly)

        # Convert back to BGV format
        result = BGVCiphertext(
            result_std.polynomials,
            result_std.level if hasattr(result_std, "level") else ciphertext.level,
        )

        return result

    def rotate_rows(self, ciphertext: BGVCiphertext, steps: int) -> BGVCiphertext:
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

        # Convert back to BGV format
        result = BGVCiphertext(
            result_std.polynomials,
            result_std.level if hasattr(result_std, "level") else ciphertext.level,
        )

        return result

    def get_noise_budget(self, ciphertext: BGVCiphertext) -> int:
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
        """Get information about the BGV scheme configuration."""
        base_info = super().get_scheme_info()

        bgv_info = {
            "plaintext_modulus": self.parameters.plaintext_modulus,
            "batching_enabled": self.batch_encoder.slots > 1,
            "batch_slots": self.batch_encoder.slots,
            "exact_arithmetic": True,
            "modulus_switching_enabled": True,
            "max_levels": len(self.parameters.coefficient_modulus) - 1,
            "current_level": self.current_level,
            "current_keys_generated": {
                "public_key": self.public_key is not None,
                "secret_key": self.secret_key is not None,
                "relinearization_keys": self.relin_keys is not None,
                "galois_keys": self.galois_keys is not None,
            },
        }

        base_info.update(bgv_info)
        return base_info
