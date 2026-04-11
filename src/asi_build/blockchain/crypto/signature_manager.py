"""
Digital Signature Management for Kenny AGI Blockchain Audit Trail

Provides comprehensive digital signature functionality including
RSA, ECDSA, and EdDSA signatures with key generation and verification.
"""

import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import nacl.encoding
import nacl.signing
from cryptography.exceptions import InvalidSignature

# Cryptographic imports
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from eth_account import Account
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)


class SignatureAlgorithm(Enum):
    """Supported signature algorithms"""

    RSA_PSS = "rsa_pss"
    RSA_PKCS1 = "rsa_pkcs1"
    ECDSA_P256 = "ecdsa_p256"
    ECDSA_P384 = "ecdsa_p384"
    ECDSA_SECP256K1 = "ecdsa_secp256k1"  # Ethereum standard
    ED25519 = "ed25519"
    ETHEREUM = "ethereum"  # Ethereum-specific signing


@dataclass
class KeyPair:
    """Represents a cryptographic key pair"""

    algorithm: SignatureAlgorithm
    private_key: Any
    public_key: Any
    key_id: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    def get_public_key_pem(self) -> str:
        """Get public key in PEM format"""
        if self.algorithm == SignatureAlgorithm.ETHEREUM:
            # Return Ethereum address
            return Account.from_key(self.private_key).address
        elif self.algorithm == SignatureAlgorithm.ED25519:
            # NaCl key
            if isinstance(self.public_key, nacl.signing.VerifyKey):
                return base64.b64encode(self.public_key.encode()).decode()
            else:
                return base64.b64encode(bytes(self.public_key)).decode()
        else:
            # Standard cryptography library keys
            return self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()

    def get_private_key_pem(self) -> str:
        """Get private key in PEM format (use with caution!)"""
        if self.algorithm == SignatureAlgorithm.ETHEREUM:
            return self.private_key
        elif self.algorithm == SignatureAlgorithm.ED25519:
            # NaCl key
            if isinstance(self.private_key, nacl.signing.SigningKey):
                return base64.b64encode(self.private_key.encode()).decode()
            else:
                return base64.b64encode(bytes(self.private_key)).decode()
        else:
            # Standard cryptography library keys
            return self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode()


@dataclass
class DigitalSignature:
    """Represents a digital signature"""

    signature: str  # Base64 encoded signature
    algorithm: SignatureAlgorithm
    key_id: str
    timestamp: datetime
    message_hash: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "signature": self.signature,
            "algorithm": self.algorithm.value,
            "key_id": self.key_id,
            "timestamp": self.timestamp.isoformat(),
            "message_hash": self.message_hash,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DigitalSignature":
        """Create from dictionary"""
        return cls(
            signature=data["signature"],
            algorithm=SignatureAlgorithm(data["algorithm"]),
            key_id=data["key_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_hash=data["message_hash"],
            metadata=data.get("metadata", {}),
        )


class SignatureManager:
    """
    Comprehensive digital signature manager

    Supports multiple signature algorithms and provides key generation,
    signing, and verification functionality.
    """

    def __init__(self):
        """Initialize signature manager"""
        self.key_pairs = {}

    def generate_key_pair(
        self,
        algorithm: SignatureAlgorithm,
        key_id: Optional[str] = None,
        key_size: int = 2048,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KeyPair:
        """
        Generate a new key pair

        Args:
            algorithm: Signature algorithm to use
            key_id: Optional key identifier (auto-generated if None)
            key_size: Key size for RSA (ignored for other algorithms)
            metadata: Optional metadata for the key pair

        Returns:
            Generated key pair
        """
        if not key_id:
            key_id = f"{algorithm.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            if algorithm == SignatureAlgorithm.RSA_PSS or algorithm == SignatureAlgorithm.RSA_PKCS1:
                private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
                public_key = private_key.public_key()

            elif algorithm == SignatureAlgorithm.ECDSA_P256:
                private_key = ec.generate_private_key(ec.SECP256R1())
                public_key = private_key.public_key()

            elif algorithm == SignatureAlgorithm.ECDSA_P384:
                private_key = ec.generate_private_key(ec.SECP384R1())
                public_key = private_key.public_key()

            elif algorithm == SignatureAlgorithm.ECDSA_SECP256K1:
                private_key = ec.generate_private_key(ec.SECP256K1())
                public_key = private_key.public_key()

            elif algorithm == SignatureAlgorithm.ED25519:
                signing_key = nacl.signing.SigningKey.generate()
                private_key = signing_key
                public_key = signing_key.verify_key

            elif algorithm == SignatureAlgorithm.ETHEREUM:
                # Generate Ethereum key pair
                private_key = Account.create().key.hex()
                public_key = Account.from_key(private_key).address

            else:
                raise ValueError(f"Unsupported signature algorithm: {algorithm}")

            key_pair = KeyPair(
                algorithm=algorithm,
                private_key=private_key,
                public_key=public_key,
                key_id=key_id,
                created_at=datetime.now(),
                metadata=metadata or {},
            )

            self.key_pairs[key_id] = key_pair

            logger.info(f"Generated {algorithm.value} key pair with ID: {key_id}")
            return key_pair

        except Exception as e:
            raise RuntimeError(f"Failed to generate key pair: {str(e)}")

    def import_key_pair(
        self,
        algorithm: SignatureAlgorithm,
        private_key_data: Union[str, bytes],
        key_id: str,
        password: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KeyPair:
        """
        Import an existing key pair

        Args:
            algorithm: Signature algorithm
            private_key_data: Private key data (PEM, bytes, or hex string)
            key_id: Key identifier
            password: Password for encrypted keys
            metadata: Optional metadata

        Returns:
            Imported key pair
        """
        try:
            if algorithm == SignatureAlgorithm.ETHEREUM:
                if isinstance(private_key_data, str) and not private_key_data.startswith("0x"):
                    private_key_data = "0x" + private_key_data

                account = Account.from_key(private_key_data)
                private_key = private_key_data
                public_key = account.address

            elif algorithm == SignatureAlgorithm.ED25519:
                if isinstance(private_key_data, str):
                    key_bytes = base64.b64decode(private_key_data)
                else:
                    key_bytes = private_key_data

                private_key = nacl.signing.SigningKey(key_bytes)
                public_key = private_key.verify_key

            else:
                # Standard cryptography library import
                if isinstance(private_key_data, str):
                    private_key_data = private_key_data.encode()

                if password:
                    password = password.encode()

                private_key = serialization.load_pem_private_key(
                    private_key_data, password=password
                )
                public_key = private_key.public_key()

            key_pair = KeyPair(
                algorithm=algorithm,
                private_key=private_key,
                public_key=public_key,
                key_id=key_id,
                created_at=datetime.now(),
                metadata=metadata or {},
            )

            self.key_pairs[key_id] = key_pair

            logger.info(f"Imported {algorithm.value} key pair with ID: {key_id}")
            return key_pair

        except Exception as e:
            raise RuntimeError(f"Failed to import key pair: {str(e)}")

    def sign_message(
        self, message: Union[str, bytes, Dict], key_id: str, hash_algorithm: str = "sha256"
    ) -> DigitalSignature:
        """
        Sign a message with the specified key

        Args:
            message: Message to sign (string, bytes, or dict)
            key_id: Key identifier to use for signing
            hash_algorithm: Hash algorithm to use

        Returns:
            Digital signature
        """
        if key_id not in self.key_pairs:
            raise KeyError(f"Key pair not found: {key_id}")

        key_pair = self.key_pairs[key_id]

        try:
            # Prepare message data
            if isinstance(message, dict):
                message_bytes = json.dumps(message, sort_keys=True, default=str).encode()
            elif isinstance(message, str):
                message_bytes = message.encode()
            else:
                message_bytes = message

            # Calculate message hash
            if hash_algorithm == "sha256":
                message_hash = hashlib.sha256(message_bytes).hexdigest()
            elif hash_algorithm == "sha512":
                message_hash = hashlib.sha512(message_bytes).hexdigest()
            else:
                raise ValueError(f"Unsupported hash algorithm: {hash_algorithm}")

            # Sign based on algorithm
            if key_pair.algorithm == SignatureAlgorithm.RSA_PSS:
                signature_bytes = key_pair.private_key.sign(
                    message_bytes,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256(),
                )

            elif key_pair.algorithm == SignatureAlgorithm.RSA_PKCS1:
                signature_bytes = key_pair.private_key.sign(
                    message_bytes, padding.PKCS1v15(), hashes.SHA256()
                )

            elif key_pair.algorithm in [
                SignatureAlgorithm.ECDSA_P256,
                SignatureAlgorithm.ECDSA_P384,
                SignatureAlgorithm.ECDSA_SECP256K1,
            ]:
                signature_bytes = key_pair.private_key.sign(
                    message_bytes, ec.ECDSA(hashes.SHA256())
                )

            elif key_pair.algorithm == SignatureAlgorithm.ED25519:
                signature_bytes = key_pair.private_key.sign(message_bytes).signature

            elif key_pair.algorithm == SignatureAlgorithm.ETHEREUM:
                # Ethereum-style message signing
                message_hash_bytes = encode_defunct(message_bytes)
                account = Account.from_key(key_pair.private_key)
                signed_message = account.sign_message(message_hash_bytes)
                signature_bytes = signed_message.signature

            else:
                raise ValueError(f"Unsupported signature algorithm: {key_pair.algorithm}")

            # Create signature object
            signature = DigitalSignature(
                signature=base64.b64encode(signature_bytes).decode(),
                algorithm=key_pair.algorithm,
                key_id=key_id,
                timestamp=datetime.now(),
                message_hash=message_hash,
            )

            logger.info(f"Signed message with key {key_id} using {key_pair.algorithm.value}")
            return signature

        except Exception as e:
            raise RuntimeError(f"Failed to sign message: {str(e)}")

    def sign_data_batch(
        self, data_list: List[Union[str, bytes, Dict]], key_id: str, hash_algorithm: str = "sha256"
    ) -> List[DigitalSignature]:
        """
        Sign multiple pieces of data in batch

        Args:
            data_list: List of data to sign
            key_id: Key identifier to use
            hash_algorithm: Hash algorithm to use

        Returns:
            List of digital signatures
        """
        signatures = []

        for data in data_list:
            try:
                signature = self.sign_message(data, key_id, hash_algorithm)
                signatures.append(signature)
            except Exception as e:
                logger.error(f"Failed to sign data item: {str(e)}")
                signatures.append(None)

        return signatures

    def get_key_pair(self, key_id: str) -> Optional[KeyPair]:
        """Get key pair by ID"""
        return self.key_pairs.get(key_id)

    def list_key_pairs(self) -> List[KeyPair]:
        """List all key pairs"""
        return list(self.key_pairs.values())

    def remove_key_pair(self, key_id: str) -> bool:
        """Remove key pair"""
        if key_id in self.key_pairs:
            del self.key_pairs[key_id]
            logger.info(f"Removed key pair: {key_id}")
            return True
        return False


class SignatureVerifier:
    """
    Digital signature verification system

    Provides verification functionality for all supported signature algorithms
    with public key management.
    """

    def __init__(self):
        """Initialize signature verifier"""
        self.public_keys = {}

    def add_public_key(
        self, key_id: str, public_key_data: Union[str, bytes, Any], algorithm: SignatureAlgorithm
    ):
        """
        Add a public key for verification

        Args:
            key_id: Key identifier
            public_key_data: Public key data
            algorithm: Signature algorithm
        """
        try:
            if algorithm == SignatureAlgorithm.ETHEREUM:
                # Ethereum address as public key
                if isinstance(public_key_data, str):
                    public_key = public_key_data
                else:
                    public_key = str(public_key_data)

            elif algorithm == SignatureAlgorithm.ED25519:
                if isinstance(public_key_data, str):
                    key_bytes = base64.b64decode(public_key_data)
                    public_key = nacl.signing.VerifyKey(key_bytes)
                else:
                    public_key = public_key_data

            else:
                # Standard cryptography library public key
                if isinstance(public_key_data, str):
                    public_key = serialization.load_pem_public_key(public_key_data.encode())
                elif isinstance(public_key_data, bytes):
                    public_key = serialization.load_pem_public_key(public_key_data)
                else:
                    public_key = public_key_data

            self.public_keys[key_id] = {"key": public_key, "algorithm": algorithm}

            logger.info(f"Added public key for verification: {key_id}")

        except Exception as e:
            raise RuntimeError(f"Failed to add public key: {str(e)}")

    def verify_signature(
        self,
        message: Union[str, bytes, Dict],
        signature: DigitalSignature,
        public_key_id: Optional[str] = None,
    ) -> bool:
        """
        Verify a digital signature

        Args:
            message: Original message that was signed
            signature: Digital signature to verify
            public_key_id: Optional public key ID (uses signature key_id if None)

        Returns:
            True if signature is valid
        """
        key_id = public_key_id or signature.key_id

        if key_id not in self.public_keys:
            raise KeyError(f"Public key not found: {key_id}")

        public_key_info = self.public_keys[key_id]
        public_key = public_key_info["key"]
        expected_algorithm = public_key_info["algorithm"]

        if signature.algorithm != expected_algorithm:
            raise ValueError("Signature algorithm mismatch")

        try:
            # Prepare message data (same as signing)
            if isinstance(message, dict):
                message_bytes = json.dumps(message, sort_keys=True, default=str).encode()
            elif isinstance(message, str):
                message_bytes = message.encode()
            else:
                message_bytes = message

            # Decode signature
            signature_bytes = base64.b64decode(signature.signature)

            # Verify based on algorithm
            if signature.algorithm == SignatureAlgorithm.RSA_PSS:
                public_key.verify(
                    signature_bytes,
                    message_bytes,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256(),
                )
                return True

            elif signature.algorithm == SignatureAlgorithm.RSA_PKCS1:
                public_key.verify(
                    signature_bytes, message_bytes, padding.PKCS1v15(), hashes.SHA256()
                )
                return True

            elif signature.algorithm in [
                SignatureAlgorithm.ECDSA_P256,
                SignatureAlgorithm.ECDSA_P384,
                SignatureAlgorithm.ECDSA_SECP256K1,
            ]:
                public_key.verify(signature_bytes, message_bytes, ec.ECDSA(hashes.SHA256()))
                return True

            elif signature.algorithm == SignatureAlgorithm.ED25519:
                public_key.verify(signature_bytes, message_bytes)
                return True

            elif signature.algorithm == SignatureAlgorithm.ETHEREUM:
                # Ethereum signature verification
                message_hash = encode_defunct(message_bytes)
                recovered_address = Account.recover_message(message_hash, signature=signature_bytes)
                return recovered_address.lower() == public_key.lower()

            else:
                raise ValueError(f"Unsupported signature algorithm: {signature.algorithm}")

        except (InvalidSignature, ValueError, Exception) as e:
            logger.warning(f"Signature verification failed: {str(e)}")
            return False

    def verify_signatures_batch(
        self,
        messages: List[Union[str, bytes, Dict]],
        signatures: List[DigitalSignature],
        public_key_id: Optional[str] = None,
    ) -> List[bool]:
        """
        Verify multiple signatures in batch

        Args:
            messages: List of original messages
            signatures: List of signatures to verify
            public_key_id: Optional public key ID

        Returns:
            List of verification results
        """
        if len(messages) != len(signatures):
            raise ValueError("Messages and signatures lists must have same length")

        results = []

        for message, signature in zip(messages, signatures):
            try:
                if signature is None:
                    results.append(False)
                else:
                    result = self.verify_signature(message, signature, public_key_id)
                    results.append(result)
            except Exception as e:
                logger.error(f"Batch verification error: {str(e)}")
                results.append(False)

        return results

    def list_public_keys(self) -> List[str]:
        """List all public key IDs"""
        return list(self.public_keys.keys())

    def remove_public_key(self, key_id: str) -> bool:
        """Remove public key"""
        if key_id in self.public_keys:
            del self.public_keys[key_id]
            logger.info(f"Removed public key: {key_id}")
            return True
        return False
