"""
Encryption and decryption operations for homomorphic encryption.
"""

import logging
import random
from typing import Any, List, Optional, Union

import numpy as np

from .base import CiphertextBase, EncryptionException, PlaintextBase, SchemeType
from .keys import PublicKey, SecretKey
from .modular import ModularArithmetic
from .parameters import FHEParameters
from .polynomial import Polynomial, PolynomialRing

logger = logging.getLogger(__name__)


class Ciphertext(CiphertextBase):
    """Enhanced ciphertext class with additional metadata."""

    def __init__(
        self,
        polynomials: List[Polynomial],
        scale: Optional[float] = None,
        level: int = 0,
        is_ntt_form: bool = False,
    ):
        """
        Initialize a ciphertext.

        Args:
            polynomials: List of polynomials representing the ciphertext
            scale: Scale factor (for CKKS)
            level: Current level in the modulus chain
            is_ntt_form: Whether ciphertext is in NTT form
        """
        super().__init__(polynomials, scale)
        self.level = level
        self.is_ntt_form = is_ntt_form
        self.noise_budget = None  # Will be estimated during operations

    def copy(self) -> "Ciphertext":
        """Create a deep copy of the ciphertext."""
        poly_copies = [Polynomial(p.coefficients.copy(), p.ring) for p in self.polynomials]
        return Ciphertext(poly_copies, self.scale, self.level, self.is_ntt_form)


class Plaintext(PlaintextBase):
    """Enhanced plaintext class with encoding information."""

    def __init__(
        self,
        data: Union[list, np.ndarray],
        scale: Optional[float] = None,
        encoding: str = "coefficients",
        level: int = 0,
    ):
        """
        Initialize a plaintext.

        Args:
            data: The plaintext data
            scale: Scale factor (for CKKS)
            encoding: Encoding type ("coefficients", "packed", "single")
            level: Target level for encryption
        """
        super().__init__(data, scale)
        self.encoding = encoding
        self.level = level

    def copy(self) -> "Plaintext":
        """Create a deep copy of the plaintext."""
        return Plaintext(self.data.copy(), self.scale, self.encoding, self.level)


class Encryptor:
    """
    Encryptor for homomorphic encryption schemes.

    Provides encryption functionality with support for different
    encoding schemes and optimization techniques.
    """

    def __init__(self, parameters: FHEParameters, public_key: PublicKey):
        """
        Initialize the encryptor.

        Args:
            parameters: FHE parameters
            public_key: Public key for encryption
        """
        self.parameters = parameters
        self.public_key = public_key
        self.poly_ring = PolynomialRing(
            parameters.polynomial_modulus_degree, parameters.coefficient_modulus
        )
        self.modular = ModularArithmetic(parameters.coefficient_modulus)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Validate key compatibility
        if public_key.metadata.parameters_hash != self._hash_parameters():
            raise EncryptionException("Public key parameters don't match encryptor parameters")

    def _hash_parameters(self) -> str:
        """Generate a hash of the parameters for validation."""
        import hashlib

        param_str = (
            f"{self.parameters.polynomial_modulus_degree}"
            f"{self.parameters.coefficient_modulus}"
            f"{self.parameters.plaintext_modulus}"
            f"{self.parameters.scale}"
            f"{self.parameters.security_level.value}"
            f"{self.parameters.scheme_type.value}"
        )
        return hashlib.sha256(param_str.encode()).hexdigest()

    def encrypt(self, plaintext: Plaintext) -> Ciphertext:
        """
        Encrypt a plaintext.

        Args:
            plaintext: Plaintext to encrypt

        Returns:
            Encrypted ciphertext
        """
        try:
            if self.parameters.scheme_type == SchemeType.CKKS:
                return self._encrypt_ckks(plaintext)
            elif self.parameters.scheme_type in [SchemeType.BFV, SchemeType.BGV]:
                return self._encrypt_bfv_bgv(plaintext)
            else:
                raise EncryptionException(f"Unsupported scheme: {self.parameters.scheme_type}")

        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            raise EncryptionException(f"Encryption failed: {e}")

    def _encrypt_ckks(self, plaintext: Plaintext) -> Ciphertext:
        """
        Encrypt using CKKS scheme.

        Args:
            plaintext: CKKS plaintext

        Returns:
            CKKS ciphertext
        """
        # Encode plaintext to polynomial
        plain_poly = self._encode_ckks(plaintext)

        # Sample randomness
        u = self._sample_ternary()
        e0 = self._sample_gaussian_noise()
        e1 = self._sample_gaussian_noise()

        # Encrypt: c0 = b*u + e0 + m, c1 = a*u + e1
        pk_b, pk_a = self.public_key.polynomials[0], self.public_key.polynomials[1]

        bu = self.poly_ring.multiply(pk_b, u)
        au = self.poly_ring.multiply(pk_a, u)

        c0 = self.poly_ring.add(self.poly_ring.add(bu, e0), plain_poly)
        c1 = self.poly_ring.add(au, e1)

        ciphertext = Ciphertext([c0, c1], plaintext.scale, plaintext.level)

        self.logger.debug(f"CKKS encrypted plaintext with scale {plaintext.scale}")
        return ciphertext

    def _encrypt_bfv_bgv(self, plaintext: Plaintext) -> Ciphertext:
        """
        Encrypt using BFV/BGV scheme.

        Args:
            plaintext: BFV/BGV plaintext

        Returns:
            BFV/BGV ciphertext
        """
        # Encode plaintext to polynomial
        plain_poly = self._encode_bfv_bgv(plaintext)

        # Sample randomness
        u = self._sample_ternary()
        e0 = self._sample_gaussian_noise()
        e1 = self._sample_gaussian_noise()

        # Scale plaintext by delta = q/t
        delta = self.parameters.coefficient_modulus[0] // self.parameters.plaintext_modulus
        scaled_plain = self.poly_ring.scalar_multiply(plain_poly, delta)

        # Encrypt: c0 = b*u + e0 + delta*m, c1 = a*u + e1
        pk_b, pk_a = self.public_key.polynomials[0], self.public_key.polynomials[1]

        bu = self.poly_ring.multiply(pk_b, u)
        au = self.poly_ring.multiply(pk_a, u)

        c0 = self.poly_ring.add(self.poly_ring.add(bu, e0), scaled_plain)
        c1 = self.poly_ring.add(au, e1)

        ciphertext = Ciphertext([c0, c1], level=plaintext.level)

        self.logger.debug(f"BFV/BGV encrypted plaintext")
        return ciphertext

    def _encode_ckks(self, plaintext: Plaintext) -> Polynomial:
        """
        Encode CKKS plaintext to polynomial.

        Args:
            plaintext: CKKS plaintext

        Returns:
            Encoded polynomial
        """
        if plaintext.encoding == "single":
            # Single value encoding
            coeffs = [int(plaintext.data[0] * plaintext.scale)] + [0] * (
                self.parameters.polynomial_modulus_degree - 1
            )
        elif plaintext.encoding == "packed":
            # Packed encoding using complex conjugate pairs
            n = self.parameters.polynomial_modulus_degree
            slots = n // 2

            # Pad or truncate to slots
            values = np.array(plaintext.data, dtype=complex)
            if len(values) > slots:
                values = values[:slots]
            elif len(values) < slots:
                values = np.pad(values, (0, slots - len(values)), mode="constant")

            # Use canonical embedding (simplified)
            coeffs = self._canonical_embedding_inverse(values, plaintext.scale)
        else:
            # Direct coefficient encoding
            coeffs = [
                int(x * plaintext.scale) if plaintext.scale else int(x) for x in plaintext.data
            ]

            # Pad to polynomial degree
            if len(coeffs) < self.parameters.polynomial_modulus_degree:
                coeffs.extend([0] * (self.parameters.polynomial_modulus_degree - len(coeffs)))
            elif len(coeffs) > self.parameters.polynomial_modulus_degree:
                coeffs = coeffs[: self.parameters.polynomial_modulus_degree]

        return Polynomial(coeffs, self.poly_ring)

    def _encode_bfv_bgv(self, plaintext: Plaintext) -> Polynomial:
        """
        Encode BFV/BGV plaintext to polynomial.

        Args:
            plaintext: BFV/BGV plaintext

        Returns:
            Encoded polynomial
        """
        if plaintext.encoding == "packed":
            # Batched encoding using CRT
            coeffs = self._batch_encode(plaintext.data)
        else:
            # Direct coefficient encoding
            coeffs = [int(x) % self.parameters.plaintext_modulus for x in plaintext.data]

            # Pad to polynomial degree
            if len(coeffs) < self.parameters.polynomial_modulus_degree:
                coeffs.extend([0] * (self.parameters.polynomial_modulus_degree - len(coeffs)))
            elif len(coeffs) > self.parameters.polynomial_modulus_degree:
                coeffs = coeffs[: self.parameters.polynomial_modulus_degree]

        return Polynomial(coeffs, self.poly_ring)

    def _canonical_embedding_inverse(self, values: np.ndarray, scale: float) -> List[int]:
        """
        Inverse canonical embedding for CKKS encoding.

        Args:
            values: Complex values to encode
            scale: Scaling factor

        Returns:
            Polynomial coefficients
        """
        # Simplified implementation - in practice would use FFT
        n = self.parameters.polynomial_modulus_degree
        coeffs = [0] * n

        # Map complex values to polynomial coefficients
        for i, val in enumerate(values):
            # Real part
            coeffs[i] = int(val.real * scale)
            # Imaginary part (if space allows)
            if i + len(values) < n:
                coeffs[i + len(values)] = int(val.imag * scale)

        return coeffs

    def _batch_encode(self, values: List[int]) -> List[int]:
        """
        Batch encoding for BFV/BGV using CRT.

        Args:
            values: Values to encode

        Returns:
            Encoded coefficients
        """
        # Simplified batching - would use proper CRT in practice
        n = self.parameters.polynomial_modulus_degree
        coeffs = [0] * n

        for i, val in enumerate(values):
            if i < n:
                coeffs[i] = val % self.parameters.plaintext_modulus

        return coeffs

    def _sample_ternary(self) -> Polynomial:
        """
        Sample a ternary polynomial with coefficients in {-1, 0, 1}.

        Returns:
            Ternary polynomial
        """
        n = self.parameters.polynomial_modulus_degree
        hamming_weight = n // 3  # Typical choice

        coeffs = [0] * n
        positions = random.sample(range(n), hamming_weight * 2)

        for i, pos in enumerate(positions):
            coeffs[pos] = 1 if i < hamming_weight else -1

        return Polynomial(coeffs, self.poly_ring)

    def _sample_gaussian_noise(self) -> Polynomial:
        """
        Sample Gaussian noise polynomial.

        Returns:
            Noise polynomial
        """
        n = self.parameters.polynomial_modulus_degree
        std_dev = self.parameters.noise_standard_deviation

        noise = np.random.normal(0, std_dev, n)
        coeffs = [int(round(x)) for x in noise]

        return Polynomial(coeffs, self.poly_ring)

    def encrypt_zero(self) -> Ciphertext:
        """
        Encrypt a zero plaintext (useful for testing).

        Returns:
            Ciphertext encrypting zero
        """
        zero_data = [0] * self.parameters.polynomial_modulus_degree
        zero_plaintext = Plaintext(zero_data, scale=self.parameters.scale)
        return self.encrypt(zero_plaintext)


class Decryptor:
    """
    Decryptor for homomorphic encryption schemes.

    Provides decryption functionality with support for different
    encoding schemes and noise estimation.
    """

    def __init__(self, parameters: FHEParameters, secret_key: SecretKey):
        """
        Initialize the decryptor.

        Args:
            parameters: FHE parameters
            secret_key: Secret key for decryption
        """
        self.parameters = parameters
        self.secret_key = secret_key
        self.poly_ring = PolynomialRing(
            parameters.polynomial_modulus_degree, parameters.coefficient_modulus
        )
        self.modular = ModularArithmetic(parameters.coefficient_modulus)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Validate key compatibility
        if secret_key.metadata.parameters_hash != self._hash_parameters():
            raise EncryptionException("Secret key parameters don't match decryptor parameters")

    def _hash_parameters(self) -> str:
        """Generate a hash of the parameters for validation."""
        import hashlib

        param_str = (
            f"{self.parameters.polynomial_modulus_degree}"
            f"{self.parameters.coefficient_modulus}"
            f"{self.parameters.plaintext_modulus}"
            f"{self.parameters.scale}"
            f"{self.parameters.security_level.value}"
            f"{self.parameters.scheme_type.value}"
        )
        return hashlib.sha256(param_str.encode()).hexdigest()

    def decrypt(self, ciphertext: Ciphertext, target_encoding: str = "coefficients") -> Plaintext:
        """
        Decrypt a ciphertext.

        Args:
            ciphertext: Ciphertext to decrypt
            target_encoding: Target encoding for the plaintext

        Returns:
            Decrypted plaintext
        """
        try:
            if self.parameters.scheme_type == SchemeType.CKKS:
                return self._decrypt_ckks(ciphertext, target_encoding)
            elif self.parameters.scheme_type in [SchemeType.BFV, SchemeType.BGV]:
                return self._decrypt_bfv_bgv(ciphertext, target_encoding)
            else:
                raise EncryptionException(f"Unsupported scheme: {self.parameters.scheme_type}")

        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            raise EncryptionException(f"Decryption failed: {e}")

    def _decrypt_ckks(self, ciphertext: Ciphertext, target_encoding: str) -> Plaintext:
        """
        Decrypt using CKKS scheme.

        Args:
            ciphertext: CKKS ciphertext
            target_encoding: Target encoding

        Returns:
            CKKS plaintext
        """
        # Decrypt: m = c0 + c1*s (mod q)
        c0, c1 = ciphertext.polynomials[0], ciphertext.polynomials[1]

        c1s = self.poly_ring.multiply(c1, self.secret_key.polynomial)
        decrypted_poly = self.poly_ring.add(c0, c1s)

        # Decode polynomial to values
        if target_encoding == "single":
            # Single value decoding
            value = decrypted_poly.coefficients[0] / ciphertext.scale
            data = [value]
        elif target_encoding == "packed":
            # Packed decoding using canonical embedding
            data = self._canonical_embedding(decrypted_poly, ciphertext.scale)
        else:
            # Coefficient decoding
            data = [
                coeff / ciphertext.scale if ciphertext.scale else coeff
                for coeff in decrypted_poly.coefficients
            ]

        plaintext = Plaintext(data, ciphertext.scale, target_encoding, ciphertext.level)

        self.logger.debug(f"CKKS decrypted ciphertext with scale {ciphertext.scale}")
        return plaintext

    def _decrypt_bfv_bgv(self, ciphertext: Ciphertext, target_encoding: str) -> Plaintext:
        """
        Decrypt using BFV/BGV scheme.

        Args:
            ciphertext: BFV/BGV ciphertext
            target_encoding: Target encoding

        Returns:
            BFV/BGV plaintext
        """
        # Decrypt: m = (c0 + c1*s) / delta (mod t)
        c0, c1 = ciphertext.polynomials[0], ciphertext.polynomials[1]

        c1s = self.poly_ring.multiply(c1, self.secret_key.polynomial)
        decrypted_poly = self.poly_ring.add(c0, c1s)

        # Scale down by delta = q/t
        delta = self.parameters.coefficient_modulus[0] // self.parameters.plaintext_modulus

        # Decode polynomial to values
        if target_encoding == "packed":
            # Batch decoding using CRT
            data = self._batch_decode(decrypted_poly, delta)
        else:
            # Coefficient decoding
            data = []
            for coeff in decrypted_poly.coefficients:
                # Round and reduce modulo t
                val = round(coeff / delta) % self.parameters.plaintext_modulus
                data.append(val)

        plaintext = Plaintext(data, encoding=target_encoding, level=ciphertext.level)

        self.logger.debug(f"BFV/BGV decrypted ciphertext")
        return plaintext

    def _canonical_embedding(self, polynomial: Polynomial, scale: float) -> List[complex]:
        """
        Canonical embedding for CKKS decoding.

        Args:
            polynomial: Polynomial to decode
            scale: Scaling factor

        Returns:
            Complex values
        """
        # Simplified implementation - in practice would use FFT
        n = self.parameters.polynomial_modulus_degree
        slots = n // 2

        values = []
        for i in range(slots):
            real_part = polynomial.coefficients[i] / scale
            imag_part = polynomial.coefficients[i + slots] / scale if i + slots < n else 0
            values.append(complex(real_part, imag_part))

        return values

    def _batch_decode(self, polynomial: Polynomial, delta: int) -> List[int]:
        """
        Batch decoding for BFV/BGV using CRT.

        Args:
            polynomial: Polynomial to decode
            delta: Scaling factor

        Returns:
            Decoded values
        """
        # Simplified implementation
        values = []
        for coeff in polynomial.coefficients:
            val = round(coeff / delta) % self.parameters.plaintext_modulus
            values.append(val)

        return values

    def estimate_noise_budget(self, ciphertext: Ciphertext) -> int:
        """
        Estimate the remaining noise budget in a ciphertext.

        Args:
            ciphertext: Ciphertext to analyze

        Returns:
            Estimated noise budget in bits
        """
        # Decrypt and compute noise
        decrypted = self.decrypt(ciphertext)

        # Re-encrypt and compare
        from .keys import KeyGenerator

        keygen = KeyGenerator(self.parameters)
        pub_key = keygen.generate_public_key(self.secret_key)
        encryptor = Encryptor(self.parameters, pub_key)

        re_encrypted = encryptor.encrypt(decrypted)

        # Compute noise as difference
        c0_diff = self.poly_ring.subtract(ciphertext.polynomials[0], re_encrypted.polynomials[0])
        noise_norm = c0_diff.norm_squared()

        # Estimate remaining budget
        max_noise = self.parameters.coefficient_modulus[0] // 2
        remaining_bits = max(0, int(np.log2(max_noise / max(1, noise_norm))))

        self.logger.debug(f"Estimated noise budget: {remaining_bits} bits")
        return remaining_bits
