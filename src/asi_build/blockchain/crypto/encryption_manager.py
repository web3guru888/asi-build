"""
Encryption Management for Kenny AGI Blockchain Audit Trail

Provides symmetric (AES-GCM, ChaCha20-Poly1305) and asymmetric (RSA-OAEP)
encryption functionality for securing audit trail data at rest and in
transit.
"""

import base64
import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305

logger = logging.getLogger(__name__)


class SymmetricAlgorithm(Enum):
    """Supported symmetric encryption algorithms"""

    AES_128_GCM = "aes_128_gcm"
    AES_256_GCM = "aes_256_gcm"
    CHACHA20_POLY1305 = "chacha20_poly1305"


# Key sizes in bytes for each algorithm
_KEY_SIZES = {
    SymmetricAlgorithm.AES_128_GCM: 16,
    SymmetricAlgorithm.AES_256_GCM: 32,
    SymmetricAlgorithm.CHACHA20_POLY1305: 32,
}

# Nonce sizes in bytes
_NONCE_SIZES = {
    SymmetricAlgorithm.AES_128_GCM: 12,
    SymmetricAlgorithm.AES_256_GCM: 12,
    SymmetricAlgorithm.CHACHA20_POLY1305: 12,
}


@dataclass
class SymmetricKey:
    """Represents a symmetric encryption key"""

    algorithm: SymmetricAlgorithm
    key_bytes: bytes
    key_id: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_hex(self) -> str:
        """Export key material as hex string"""
        return self.key_bytes.hex()

    @classmethod
    def from_hex(
        cls,
        hex_str: str,
        algorithm: SymmetricAlgorithm,
        key_id: str,
    ) -> "SymmetricKey":
        """Import key from hex string"""
        key_bytes = bytes.fromhex(hex_str)
        expected = _KEY_SIZES[algorithm]
        if len(key_bytes) != expected:
            raise ValueError(
                f"Key length {len(key_bytes)} does not match "
                f"expected {expected} for {algorithm.value}"
            )
        return cls(
            algorithm=algorithm,
            key_bytes=key_bytes,
            key_id=key_id,
            created_at=datetime.now(),
        )


@dataclass
class AsymmetricKeyPair:
    """Represents an asymmetric (RSA) key pair for encryption"""

    private_key: Any
    public_key: Any
    key_id: str
    algorithm: str  # "rsa"
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_public_key_pem(self) -> str:
        """Get public key in PEM format"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    def get_private_key_pem(self) -> str:
        """Get private key in PEM format (use with caution!)"""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()


class EncryptionManager:
    """
    Comprehensive encryption manager

    Supports symmetric AEAD encryption (AES-GCM, ChaCha20-Poly1305) and
    asymmetric encryption (RSA-OAEP) with key lifecycle management.
    """

    def __init__(self):
        """Initialize encryption manager"""
        self._keys: Dict[str, SymmetricKey] = {}
        self._asymmetric_keys: Dict[str, AsymmetricKeyPair] = {}

    # ------------------------------------------------------------------
    # Symmetric key management
    # ------------------------------------------------------------------

    def generate_symmetric_key(
        self,
        algorithm: SymmetricAlgorithm = SymmetricAlgorithm.AES_256_GCM,
        key_id: Optional[str] = None,
    ) -> SymmetricKey:
        """
        Generate a new symmetric encryption key

        Args:
            algorithm: Symmetric algorithm to use
            key_id: Optional key identifier (auto-generated if None)

        Returns:
            Generated symmetric key
        """
        if not key_id:
            key_id = f"{algorithm.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

        key_size = _KEY_SIZES[algorithm]
        key_bytes = os.urandom(key_size)

        sym_key = SymmetricKey(
            algorithm=algorithm,
            key_bytes=key_bytes,
            key_id=key_id,
            created_at=datetime.now(),
        )
        self._keys[key_id] = sym_key

        logger.info(f"Generated {algorithm.value} key with ID: {key_id}")
        return sym_key

    def import_symmetric_key(self, key: SymmetricKey) -> None:
        """Import an existing symmetric key into the manager"""
        self._keys[key.key_id] = key
        logger.info(f"Imported symmetric key: {key.key_id}")

    def get_symmetric_key(self, key_id: str) -> Optional[SymmetricKey]:
        """Retrieve a symmetric key by ID"""
        return self._keys.get(key_id)

    # ------------------------------------------------------------------
    # Symmetric encryption / decryption
    # ------------------------------------------------------------------

    def encrypt(
        self,
        plaintext: bytes,
        key_id: str,
        aad: Optional[bytes] = None,
    ) -> Tuple[bytes, bytes]:
        """
        Encrypt data using AEAD symmetric encryption

        Args:
            plaintext: Data to encrypt
            key_id: Symmetric key identifier
            aad: Optional additional authenticated data

        Returns:
            Tuple of (nonce, ciphertext)
        """
        if key_id not in self._keys:
            raise KeyError(f"Symmetric key not found: {key_id}")

        sym_key = self._keys[key_id]
        nonce_size = _NONCE_SIZES[sym_key.algorithm]
        nonce = os.urandom(nonce_size)

        try:
            if sym_key.algorithm in (
                SymmetricAlgorithm.AES_128_GCM,
                SymmetricAlgorithm.AES_256_GCM,
            ):
                cipher = AESGCM(sym_key.key_bytes)
            elif sym_key.algorithm == SymmetricAlgorithm.CHACHA20_POLY1305:
                cipher = ChaCha20Poly1305(sym_key.key_bytes)
            else:
                raise ValueError(f"Unsupported algorithm: {sym_key.algorithm}")

            ciphertext = cipher.encrypt(nonce, plaintext, aad)

            logger.debug(
                f"Encrypted {len(plaintext)} bytes with key {key_id} "
                f"({sym_key.algorithm.value})"
            )
            return nonce, ciphertext

        except Exception as e:
            raise RuntimeError(f"Encryption failed: {str(e)}")

    def decrypt(
        self,
        nonce: bytes,
        ciphertext: bytes,
        key_id: str,
        aad: Optional[bytes] = None,
    ) -> bytes:
        """
        Decrypt data using AEAD symmetric decryption

        Args:
            nonce: Nonce used during encryption
            ciphertext: Encrypted data (includes authentication tag)
            key_id: Symmetric key identifier
            aad: Optional additional authenticated data (must match encryption)

        Returns:
            Decrypted plaintext
        """
        if key_id not in self._keys:
            raise KeyError(f"Symmetric key not found: {key_id}")

        sym_key = self._keys[key_id]

        try:
            if sym_key.algorithm in (
                SymmetricAlgorithm.AES_128_GCM,
                SymmetricAlgorithm.AES_256_GCM,
            ):
                cipher = AESGCM(sym_key.key_bytes)
            elif sym_key.algorithm == SymmetricAlgorithm.CHACHA20_POLY1305:
                cipher = ChaCha20Poly1305(sym_key.key_bytes)
            else:
                raise ValueError(f"Unsupported algorithm: {sym_key.algorithm}")

            plaintext = cipher.decrypt(nonce, ciphertext, aad)

            logger.debug(
                f"Decrypted {len(ciphertext)} bytes with key {key_id} "
                f"({sym_key.algorithm.value})"
            )
            return plaintext

        except Exception as e:
            raise RuntimeError(f"Decryption failed: {str(e)}")

    # ------------------------------------------------------------------
    # Asymmetric key management
    # ------------------------------------------------------------------

    def generate_asymmetric_key(
        self,
        key_id: Optional[str] = None,
        key_size: int = 2048,
    ) -> AsymmetricKeyPair:
        """
        Generate an RSA key pair for asymmetric encryption

        Args:
            key_id: Optional key identifier (auto-generated if None)
            key_size: RSA key size in bits (2048, 3072, or 4096)

        Returns:
            Generated asymmetric key pair
        """
        if not key_id:
            key_id = f"rsa_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

        try:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
            )
            public_key = private_key.public_key()

            key_pair = AsymmetricKeyPair(
                private_key=private_key,
                public_key=public_key,
                key_id=key_id,
                algorithm="rsa",
                created_at=datetime.now(),
            )
            self._asymmetric_keys[key_id] = key_pair

            logger.info(f"Generated RSA-{key_size} key pair with ID: {key_id}")
            return key_pair

        except Exception as e:
            raise RuntimeError(f"Failed to generate asymmetric key: {str(e)}")

    def import_asymmetric_key(self, key_pair: AsymmetricKeyPair) -> None:
        """Import an existing asymmetric key pair into the manager"""
        self._asymmetric_keys[key_pair.key_id] = key_pair
        logger.info(f"Imported asymmetric key: {key_pair.key_id}")

    def get_asymmetric_key(self, key_id: str) -> Optional[AsymmetricKeyPair]:
        """Retrieve an asymmetric key pair by ID"""
        return self._asymmetric_keys.get(key_id)

    # ------------------------------------------------------------------
    # Asymmetric encryption / decryption (RSA-OAEP)
    # ------------------------------------------------------------------

    def asymmetric_encrypt(self, plaintext: bytes, key_id: str) -> bytes:
        """
        Encrypt data using RSA-OAEP

        Note: RSA encryption is limited by key size. For large data, use
        hybrid encryption (encrypt data with a symmetric key, then encrypt
        the symmetric key with RSA).

        Args:
            plaintext: Data to encrypt
            key_id: Asymmetric key identifier

        Returns:
            Encrypted ciphertext
        """
        if key_id not in self._asymmetric_keys:
            raise KeyError(f"Asymmetric key not found: {key_id}")

        key_pair = self._asymmetric_keys[key_id]

        try:
            ciphertext = key_pair.public_key.encrypt(
                plaintext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            logger.debug(f"RSA-OAEP encrypted {len(plaintext)} bytes with key {key_id}")
            return ciphertext

        except Exception as e:
            raise RuntimeError(f"Asymmetric encryption failed: {str(e)}")

    def asymmetric_decrypt(self, ciphertext: bytes, key_id: str) -> bytes:
        """
        Decrypt data using RSA-OAEP

        Args:
            ciphertext: Encrypted data
            key_id: Asymmetric key identifier

        Returns:
            Decrypted plaintext
        """
        if key_id not in self._asymmetric_keys:
            raise KeyError(f"Asymmetric key not found: {key_id}")

        key_pair = self._asymmetric_keys[key_id]

        try:
            plaintext = key_pair.private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            logger.debug(f"RSA-OAEP decrypted {len(ciphertext)} bytes with key {key_id}")
            return plaintext

        except Exception as e:
            raise RuntimeError(f"Asymmetric decryption failed: {str(e)}")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def list_symmetric_keys(self) -> list:
        """List all symmetric key IDs"""
        return list(self._keys.keys())

    def list_asymmetric_keys(self) -> list:
        """List all asymmetric key IDs"""
        return list(self._asymmetric_keys.keys())

    def remove_key(self, key_id: str) -> bool:
        """Remove a key (symmetric or asymmetric) by ID"""
        removed = False
        if key_id in self._keys:
            del self._keys[key_id]
            removed = True
        if key_id in self._asymmetric_keys:
            del self._asymmetric_keys[key_id]
            removed = True
        if removed:
            logger.info(f"Removed key: {key_id}")
        return removed
