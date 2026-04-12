"""
Key Management for Kenny AGI Blockchain Audit Trail

Provides key storage, retrieval, and derivation (HKDF, PBKDF2) for
managing cryptographic keys across the system.
"""

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


@dataclass
class KeyMetadata:
    """Metadata associated with a stored key"""

    key_id: str
    key_type: str  # "symmetric", "asymmetric", "derived"
    algorithm: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    parent_key_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check whether the key has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "key_id": self.key_id,
            "key_type": self.key_type,
            "algorithm": self.algorithm,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "parent_key_id": self.parent_key_id,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyMetadata":
        """Create from dictionary"""
        return cls(
            key_id=data["key_id"],
            key_type=data["key_type"],
            algorithm=data["algorithm"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
            parent_key_id=data.get("parent_key_id"),
            tags=data.get("tags", {}),
        )


class KeyStore:
    """
    Secure in-memory key storage with metadata

    Stores raw key material alongside descriptive metadata.  Keys are
    indexed by ``key_id`` and can be enumerated, retrieved, or deleted.
    """

    def __init__(self):
        """Initialize empty key store"""
        self._keys: Dict[str, bytes] = {}
        self._metadata: Dict[str, KeyMetadata] = {}

    def store(self, key_id: str, key_data: bytes, metadata: KeyMetadata) -> None:
        """
        Store a key with associated metadata

        Args:
            key_id: Unique key identifier
            key_data: Raw key material
            metadata: Key metadata
        """
        self._keys[key_id] = key_data
        self._metadata[key_id] = metadata
        logger.info(f"Stored key: {key_id} (type={metadata.key_type})")

    def retrieve(self, key_id: str) -> Optional[bytes]:
        """
        Retrieve raw key material by ID

        Args:
            key_id: Key identifier

        Returns:
            Raw key bytes or None if not found
        """
        return self._keys.get(key_id)

    def get_metadata(self, key_id: str) -> Optional[KeyMetadata]:
        """Retrieve metadata for a key"""
        return self._metadata.get(key_id)

    def delete(self, key_id: str) -> bool:
        """
        Delete a key and its metadata

        Args:
            key_id: Key identifier

        Returns:
            True if the key was found and deleted
        """
        if key_id in self._keys:
            del self._keys[key_id]
            del self._metadata[key_id]
            logger.info(f"Deleted key: {key_id}")
            return True
        return False

    def list_keys(self) -> List[KeyMetadata]:
        """List metadata for all stored keys"""
        return list(self._metadata.values())

    def has_key(self, key_id: str) -> bool:
        """Check whether a key exists in the store"""
        return key_id in self._keys


class KeyManager:
    """
    Key lifecycle management with derivation capabilities

    Provides high-level operations for generating, deriving, rotating,
    and managing cryptographic keys through an underlying :class:`KeyStore`.
    """

    def __init__(self, store: Optional[KeyStore] = None):
        """
        Initialize key manager

        Args:
            store: Optional key store instance (creates a new one if None)
        """
        self.store = store or KeyStore()

    # ------------------------------------------------------------------
    # Key generation
    # ------------------------------------------------------------------

    def generate_random_key(
        self,
        length: int = 32,
        key_id: Optional[str] = None,
        algorithm: str = "random",
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate a cryptographically secure random key

        Args:
            length: Key length in bytes
            key_id: Optional key identifier (auto-generated if None)
            algorithm: Algorithm label for metadata
            tags: Optional metadata tags

        Returns:
            The key identifier
        """
        if not key_id:
            key_id = f"key_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

        key_data = os.urandom(length)
        metadata = KeyMetadata(
            key_id=key_id,
            key_type="symmetric",
            algorithm=algorithm,
            created_at=datetime.now(),
            tags=tags or {},
        )
        self.store.store(key_id, key_data, metadata)

        logger.info(f"Generated random key ({length} bytes): {key_id}")
        return key_id

    # ------------------------------------------------------------------
    # Key derivation
    # ------------------------------------------------------------------

    def derive_key(
        self,
        master_key: bytes,
        info: bytes,
        length: int = 32,
        salt: Optional[bytes] = None,
    ) -> bytes:
        """
        Derive a key using HKDF (HMAC-based Key Derivation Function)

        Args:
            master_key: Input key material
            info: Context/application-specific info
            length: Desired output key length in bytes
            salt: Optional salt (random value recommended)

        Returns:
            Derived key bytes
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            info=info,
        )
        derived = hkdf.derive(master_key)

        logger.debug(f"Derived {length}-byte key via HKDF")
        return derived

    def derive_from_password(
        self,
        password: str,
        salt: Optional[bytes] = None,
        iterations: int = 600_000,
        length: int = 32,
    ) -> Tuple[bytes, bytes]:
        """
        Derive a key from a password using PBKDF2-HMAC-SHA256

        Args:
            password: Password string
            salt: Optional salt (auto-generated 16 bytes if None)
            iterations: PBKDF2 iteration count
            length: Desired key length in bytes

        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            iterations=iterations,
        )
        derived = kdf.derive(password.encode("utf-8"))

        logger.debug(f"Derived key from password via PBKDF2 ({iterations} iterations)")
        return derived, salt

    def derive_and_store(
        self,
        master_key_id: str,
        info: bytes,
        length: int = 32,
        child_key_id: Optional[str] = None,
    ) -> str:
        """
        Derive a child key from a stored master key and store the result

        Args:
            master_key_id: Identifier of the master key in the store
            info: Context info for derivation
            length: Desired child key length
            child_key_id: Optional identifier for the child key

        Returns:
            The child key identifier
        """
        master_data = self.store.retrieve(master_key_id)
        if master_data is None:
            raise KeyError(f"Master key not found: {master_key_id}")

        child_bytes = self.derive_key(master_data, info, length)

        if not child_key_id:
            child_key_id = (
                f"derived_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                f"_{os.urandom(4).hex()}"
            )

        metadata = KeyMetadata(
            key_id=child_key_id,
            key_type="derived",
            algorithm="hkdf_sha256",
            created_at=datetime.now(),
            parent_key_id=master_key_id,
        )
        self.store.store(child_key_id, child_bytes, metadata)

        logger.info(f"Derived child key {child_key_id} from {master_key_id}")
        return child_key_id

    # ------------------------------------------------------------------
    # Key rotation
    # ------------------------------------------------------------------

    def rotate_key(self, old_key_id: str) -> str:
        """
        Rotate a key: generate a replacement and mark the old key as expired

        The old key is *not* deleted — it remains in the store with an
        ``expires_at`` timestamp so that data encrypted under it can still
        be decrypted during a migration window.

        Args:
            old_key_id: Identifier of the key to rotate

        Returns:
            The new key identifier
        """
        old_data = self.store.retrieve(old_key_id)
        if old_data is None:
            raise KeyError(f"Key not found: {old_key_id}")

        old_meta = self.store.get_metadata(old_key_id)

        # Mark old key as expired
        if old_meta is not None:
            old_meta.expires_at = datetime.now()
            old_meta.tags["rotated"] = "true"

        # Generate replacement with same length
        new_key_id = f"rotated_{old_key_id}_{os.urandom(4).hex()}"
        new_data = os.urandom(len(old_data))

        new_meta = KeyMetadata(
            key_id=new_key_id,
            key_type=old_meta.key_type if old_meta else "symmetric",
            algorithm=old_meta.algorithm if old_meta else "unknown",
            created_at=datetime.now(),
            parent_key_id=old_key_id,
            tags={"rotated_from": old_key_id},
        )
        self.store.store(new_key_id, new_data, new_meta)

        logger.info(f"Rotated key {old_key_id} → {new_key_id}")
        return new_key_id

    # ------------------------------------------------------------------
    # Convenience pass-through
    # ------------------------------------------------------------------

    def get_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve raw key material by ID"""
        return self.store.retrieve(key_id)

    def delete_key(self, key_id: str) -> bool:
        """Delete a key from the store"""
        return self.store.delete(key_id)

    def list_keys(self) -> List[KeyMetadata]:
        """List metadata for all managed keys"""
        return self.store.list_keys()
