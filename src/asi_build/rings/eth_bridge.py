"""
Rings ↔ Ethereum Identity Bridge
=================================

Unified identity: one secp256k1 private key produces both a Rings DID
and an Ethereum address.  This is the foundation for trustless cross-chain
operations — the same key proves identity on both networks.

Ethereum Address Derivation
~~~~~~~~~~~~~~~~~~~~~~~~~~~
From secp256k1 public key:

1. Get uncompressed public key bytes (65 bytes, starting with ``0x04``)
2. Take bytes ``[1:]`` (64 bytes — x and y coordinates)
3. ``keccak256(64_bytes)`` → 32 bytes
4. Take last 20 bytes → Ethereum address
5. EIP-55 checksum encoding → ``"0x..."`` string

EIP-191 Personal Sign
~~~~~~~~~~~~~~~~~~~~~
::

    "\\x19Ethereum Signed Message:\\n" + len(message) + message

Then ECDSA sign the keccak256 hash of the prefixed message.

EIP-712 Typed Data
~~~~~~~~~~~~~~~~~~
Structured data signing following EIP-712 spec::

    keccak256("\\x19\\x01" + domainSeparator + hashStruct(message))

The domain separator encodes chain-specific context (name, version,
chain ID, verifying contract) and ``hashStruct`` recursively encodes
typed data into a canonical hash.

Usage
~~~~~
::

    from asi_build.rings.eth_bridge import RingsEthIdentity

    # Generate fresh identity
    identity = RingsEthIdentity.generate()

    # Same key, two worlds
    print(identity.ethereum_address)  # 0x71C7656E...
    print(identity.rings_did)         # did:rings:secp256k1:a3f8...

    # Sign for Ethereum (EIP-191 personal_sign)
    sig = identity.sign_ethereum(b"Hello DeFi")
    assert identity.verify_ethereum(b"Hello DeFi", sig)

    # Sign for Rings (ECDSA-SHA256, DER)
    sig = identity.sign_rings(b"Hello P2P")
    assert identity.verify_rings(b"Hello P2P", sig)

    # Recover address from signature
    addr = RingsEthIdentity.recover_ethereum_address(b"Hello DeFi", sig_eth)
    assert addr == identity.ethereum_address
"""

from __future__ import annotations

import hashlib
import logging
import struct
from typing import Any, Dict, List, Optional, Tuple, Union

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from Crypto.Hash import keccak as _pycryptodome_keccak
from eth_keys import keys as eth_keys_mod

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: secp256k1 curve order (n)
SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

#: HKDF salt and info for deterministic seed derivation
_HKDF_SALT = b"rings-eth-identity"
_HKDF_INFO = b"secp256k1-private-key"

#: EIP-191 personal sign prefix
_EIP191_PREFIX = b"\x19Ethereum Signed Message:\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _keccak256(data: bytes) -> bytes:
    """Compute keccak-256 hash using pycryptodome."""
    h = _pycryptodome_keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


def _eip55_checksum(address_hex: str) -> str:
    """Apply EIP-55 mixed-case checksum to a hex address.

    Parameters
    ----------
    address_hex : str
        40-char lowercase hex string (no ``0x`` prefix).

    Returns
    -------
    str
        ``"0x"``-prefixed checksummed address.
    """
    address_lower = address_hex.lower()
    hash_hex = _keccak256(address_lower.encode("ascii")).hex()

    checksummed = []
    for i, char in enumerate(address_lower):
        if char in "0123456789":
            checksummed.append(char)
        else:
            # If the corresponding nibble in the hash is >= 8, uppercase
            checksummed.append(char.upper() if int(hash_hex[i], 16) >= 8 else char)

    return "0x" + "".join(checksummed)


def _encode_eip712_type(type_name: str, types: Dict[str, List[Dict[str, str]]]) -> str:
    """Encode type string for EIP-712 ``encodeType``.

    Produces ``TypeName(type1 name1,type2 name2,...)`` with referenced
    types appended in sorted order.

    Parameters
    ----------
    type_name : str
        The primary type being encoded.
    types : dict
        Mapping of type name → list of ``{"name": ..., "type": ...}`` fields.

    Returns
    -------
    str
        The canonical type encoding string.
    """
    # Collect all referenced types (excluding primary built-in Solidity types)
    BUILTIN_TYPES = {
        "address", "bool", "string", "bytes",
        *(f"uint{i}" for i in range(8, 257, 8)),
        *(f"int{i}" for i in range(8, 257, 8)),
        *(f"bytes{i}" for i in range(1, 33)),
    }

    def _collect_deps(tn: str, seen: set) -> set:
        if tn in seen or tn not in types:
            return seen
        seen.add(tn)
        for field in types[tn]:
            ft = field["type"].rstrip("[]")  # strip array suffix
            if ft not in BUILTIN_TYPES and ft in types:
                _collect_deps(ft, seen)
        return seen

    deps = _collect_deps(type_name, set())
    deps.discard(type_name)

    def _format_type(tn: str) -> str:
        fields = ",".join(f"{f['type']} {f['name']}" for f in types[tn])
        return f"{tn}({fields})"

    result = _format_type(type_name)
    for dep in sorted(deps):
        result += _format_type(dep)
    return result


def _hash_eip712_struct(
    type_name: str,
    data: Dict[str, Any],
    types: Dict[str, List[Dict[str, str]]],
) -> bytes:
    """Compute ``hashStruct`` for EIP-712 typed data.

    Parameters
    ----------
    type_name : str
        The struct type name (e.g. ``"Mail"``).
    data : dict
        The struct data values.
    types : dict
        Type definitions.

    Returns
    -------
    bytes
        32-byte keccak256 hash of the encoded struct.
    """
    BUILTIN_TYPES = {
        "address", "bool", "string", "bytes",
        *(f"uint{i}" for i in range(8, 257, 8)),
        *(f"int{i}" for i in range(8, 257, 8)),
        *(f"bytes{i}" for i in range(1, 33)),
    }

    # typeHash = keccak256(encodeType)
    type_str = _encode_eip712_type(type_name, types)
    type_hash = _keccak256(type_str.encode("utf-8"))

    encoded_values = [type_hash]

    for field in types[type_name]:
        field_name = field["name"]
        field_type = field["type"]
        value = data.get(field_name)

        base_type = field_type.rstrip("[]")
        is_array = field_type.endswith("[]")

        if is_array:
            # Array: keccak256(concat(encode(element) for element in value))
            elements = b""
            for item in (value or []):
                if base_type in types:
                    elements += _hash_eip712_struct(base_type, item, types)
                elif base_type == "string":
                    elements += _keccak256(item.encode("utf-8") if isinstance(item, str) else item)
                elif base_type == "bytes":
                    elements += _keccak256(item if isinstance(item, bytes) else bytes.fromhex(item))
                else:
                    elements += _encode_atomic(base_type, item)
            encoded_values.append(_keccak256(elements))
        elif field_type in types:
            # Nested struct
            encoded_values.append(
                _hash_eip712_struct(field_type, value or {}, types)
            )
        elif field_type == "string":
            encoded_values.append(
                _keccak256(value.encode("utf-8") if isinstance(value, str) else (value or b""))
            )
        elif field_type == "bytes":
            raw = value if isinstance(value, bytes) else bytes.fromhex(value or "")
            encoded_values.append(_keccak256(raw))
        else:
            encoded_values.append(_encode_atomic(field_type, value))

    return _keccak256(b"".join(encoded_values))


def _encode_atomic(solidity_type: str, value: Any) -> bytes:
    """ABI-encode an atomic Solidity type to 32 bytes.

    Parameters
    ----------
    solidity_type : str
        e.g. ``"uint256"``, ``"address"``, ``"bool"``, ``"bytes32"``
    value :
        The value to encode.

    Returns
    -------
    bytes
        32-byte ABI-encoded value.
    """
    if solidity_type == "address":
        # Address → 20 bytes, left-padded to 32
        addr = value.lower().replace("0x", "")
        return bytes(12) + bytes.fromhex(addr)
    elif solidity_type == "bool":
        return (1 if value else 0).to_bytes(32, "big")
    elif solidity_type.startswith("uint"):
        bits = int(solidity_type[4:]) if len(solidity_type) > 4 else 256
        v = int(value) if not isinstance(value, int) else value
        return v.to_bytes(32, "big")
    elif solidity_type.startswith("int"):
        bits = int(solidity_type[3:]) if len(solidity_type) > 3 else 256
        v = int(value) if not isinstance(value, int) else value
        # Two's complement for negative values
        if v < 0:
            v = (1 << 256) + v
        return v.to_bytes(32, "big")
    elif solidity_type.startswith("bytes"):
        # bytesN — right-padded to 32 bytes
        n = int(solidity_type[5:])
        raw = value if isinstance(value, bytes) else bytes.fromhex(value)
        return raw[:n].ljust(32, b"\x00")
    else:
        # Fallback: try to encode as uint256
        return int(value).to_bytes(32, "big")


# ---------------------------------------------------------------------------
# RingsEthIdentity
# ---------------------------------------------------------------------------


class RingsEthIdentity:
    """Unified identity bridge between Rings DID and Ethereum.

    A single secp256k1 private key produces both a Rings DID
    (``did:rings:secp256k1:<fingerprint>``) and an EIP-55 checksummed
    Ethereum address.  Supports signing and verification for both
    protocols.

    Parameters
    ----------
    private_key : ec.EllipticCurvePrivateKey
        A secp256k1 private key from the ``cryptography`` library.

    Raises
    ------
    ValueError
        If the key is not on the secp256k1 curve.
    """

    def __init__(self, private_key: ec.EllipticCurvePrivateKey) -> None:
        if not isinstance(private_key.curve, ec.SECP256K1):
            raise ValueError(
                f"Expected secp256k1 key, got {type(private_key.curve).__name__}"
            )
        self._private_key = private_key
        self._public_key = private_key.public_key()

        # Cache raw bytes
        self._private_bytes = (
            private_key.private_numbers().private_value.to_bytes(32, "big")
        )
        self._public_uncompressed = self._public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        self._public_compressed = self._public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.CompressedPoint,
        )

        # eth_keys private key (for Ethereum signature operations)
        self._eth_key = eth_keys_mod.PrivateKey(self._private_bytes)

        # Derive Ethereum address
        self._eth_address = self._derive_ethereum_address()

        # Derive Rings DID
        self._rings_did = self._derive_rings_did()

    # ── Constructors ─────────────────────────────────────────────────────

    @classmethod
    def generate(cls) -> RingsEthIdentity:
        """Generate a new identity with a random secp256k1 key.

        Returns
        -------
        RingsEthIdentity
            A fresh identity with a cryptographically random key.
        """
        private_key = ec.generate_private_key(ec.SECP256K1())
        return cls(private_key)

    @classmethod
    def from_private_key_hex(cls, hex_key: str) -> RingsEthIdentity:
        """Create an identity from a hex-encoded private key.

        Parameters
        ----------
        hex_key : str
            64-character hex string (optionally ``0x``-prefixed).

        Returns
        -------
        RingsEthIdentity

        Raises
        ------
        ValueError
            If the hex string is malformed or the value is out of range.
        """
        hex_key = hex_key.removeprefix("0x").removeprefix("0X")
        if len(hex_key) != 64:
            raise ValueError(
                f"Private key must be 64 hex chars, got {len(hex_key)}"
            )

        key_int = int(hex_key, 16)
        if key_int < 1 or key_int >= SECP256K1_ORDER:
            raise ValueError("Private key out of valid secp256k1 range")

        private_key = ec.derive_private_key(key_int, ec.SECP256K1())
        return cls(private_key)

    @classmethod
    def from_seed(cls, seed: str) -> RingsEthIdentity:
        """Create a deterministic identity from a seed string.

        Uses HKDF-SHA256 to derive a valid secp256k1 private key from
        the seed.  Identical seeds always produce identical identities.

        Parameters
        ----------
        seed : str
            Arbitrary seed string (e.g. ``"test-alice"``).

        Returns
        -------
        RingsEthIdentity
            A deterministic identity.
        """
        derived = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=_HKDF_SALT,
            info=_HKDF_INFO,
        ).derive(seed.encode("utf-8"))

        # Ensure the derived value is a valid secp256k1 private key
        key_int = int.from_bytes(derived, "big")
        if key_int < 1 or key_int >= SECP256K1_ORDER:
            # Extremely unlikely with HKDF output, but handle gracefully
            key_int = (key_int % (SECP256K1_ORDER - 1)) + 1

        private_key = ec.derive_private_key(key_int, ec.SECP256K1())
        return cls(private_key)

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def private_key(self) -> ec.EllipticCurvePrivateKey:
        """The underlying ``cryptography`` private key object."""
        return self._private_key

    @property
    def private_key_hex(self) -> str:
        """Private key as 64 hex characters (no ``0x`` prefix)."""
        return self._private_bytes.hex()

    @property
    def public_key_hex(self) -> str:
        """Uncompressed public key — 130 hex chars (``04`` + x + y)."""
        return self._public_uncompressed.hex()

    @property
    def public_key_compressed_hex(self) -> str:
        """Compressed public key — 66 hex chars (``02``/``03`` + x)."""
        return self._public_compressed.hex()

    @property
    def ethereum_address(self) -> str:
        """EIP-55 checksummed Ethereum address (``0x...``, 42 chars)."""
        return self._eth_address

    @property
    def rings_did(self) -> str:
        """Rings DID string (``did:rings:secp256k1:<fingerprint>``)."""
        return self._rings_did

    # ── Ethereum Signing (EIP-191) ───────────────────────────────────────

    def sign_ethereum(self, message: bytes) -> bytes:
        r"""Sign a message using EIP-191 personal_sign.

        Constructs the standard Ethereum personal sign hash::

            keccak256("\\x19Ethereum Signed Message:\\n" + len(message) + message)

        Then signs with ECDSA and returns the 65-byte ``(r, s, v)`` signature.

        Parameters
        ----------
        message : bytes
            The message to sign.

        Returns
        -------
        bytes
            65-byte signature: ``r`` (32 bytes) + ``s`` (32 bytes) + ``v`` (1 byte).
        """
        msg_hash = _eip191_hash(message)
        sig = self._eth_key.sign_msg_hash(msg_hash)
        return sig.to_bytes()  # 65 bytes: r (32) + s (32) + v (1)

    def verify_ethereum(self, message: bytes, signature: bytes) -> bool:
        r"""Verify an EIP-191 personal_sign signature.

        Parameters
        ----------
        message : bytes
            The original signed message.
        signature : bytes
            65-byte ``(r, s, v)`` signature.

        Returns
        -------
        bool
            ``True`` if the signature is valid and was produced by this key.
        """
        try:
            msg_hash = _eip191_hash(message)
            sig = eth_keys_mod.Signature(signature)
            recovered = sig.recover_public_key_from_msg_hash(msg_hash)
            return recovered == self._eth_key.public_key
        except Exception:
            return False

    # ── EIP-712 Typed Data Signing ───────────────────────────────────────

    def sign_eip712(
        self,
        domain: Dict[str, Any],
        types: Dict[str, List[Dict[str, str]]],
        message: Dict[str, Any],
        primary_type: str = "",
    ) -> bytes:
        r"""Sign EIP-712 typed structured data.

        Constructs::

            keccak256("\\x19\\x01" + domainSeparator + hashStruct(message))

        and signs with ECDSA.

        Parameters
        ----------
        domain : dict
            EIP-712 domain with keys like ``name``, ``version``,
            ``chainId``, ``verifyingContract``, ``salt``.
        types : dict
            Type definitions.  Must include the primary message type.
            ``EIP712Domain`` is constructed automatically.
        message : dict
            The message data to sign.
        primary_type : str, optional
            The primary type name.  If not specified, inferred as the
            first key in ``types`` that is not ``"EIP712Domain"``.

        Returns
        -------
        bytes
            65-byte ``(r, s, v)`` signature.
        """
        # Infer primary type
        if not primary_type:
            for key in types:
                if key != "EIP712Domain":
                    primary_type = key
                    break

        # Build EIP712Domain type definition from provided domain fields
        domain_fields: List[Dict[str, str]] = []
        if "name" in domain:
            domain_fields.append({"name": "name", "type": "string"})
        if "version" in domain:
            domain_fields.append({"name": "version", "type": "string"})
        if "chainId" in domain:
            domain_fields.append({"name": "chainId", "type": "uint256"})
        if "verifyingContract" in domain:
            domain_fields.append({"name": "verifyingContract", "type": "address"})
        if "salt" in domain:
            domain_fields.append({"name": "salt", "type": "bytes32"})

        full_types = {**types, "EIP712Domain": domain_fields}

        # domainSeparator = hashStruct("EIP712Domain", domain)
        domain_separator = _hash_eip712_struct("EIP712Domain", domain, full_types)

        # hashStruct(primary_type, message)
        struct_hash = _hash_eip712_struct(primary_type, message, full_types)

        # Final hash: keccak256("\x19\x01" + domainSeparator + structHash)
        final_hash = _keccak256(b"\x19\x01" + domain_separator + struct_hash)

        sig = self._eth_key.sign_msg_hash(final_hash)
        return sig.to_bytes()

    # ── Rings Protocol Signing ───────────────────────────────────────────

    def sign_rings(self, data: bytes) -> bytes:
        """Sign data for the Rings protocol (ECDSA-SHA256, DER-encoded).

        Parameters
        ----------
        data : bytes
            The data to sign.

        Returns
        -------
        bytes
            DER-encoded ECDSA signature.
        """
        return self._private_key.sign(data, ec.ECDSA(hashes.SHA256()))

    def verify_rings(self, data: bytes, signature: bytes) -> bool:
        """Verify a Rings protocol signature.

        Parameters
        ----------
        data : bytes
            The original signed data.
        signature : bytes
            DER-encoded ECDSA signature.

        Returns
        -------
        bool
            ``True`` if the signature is valid.
        """
        try:
            self._public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False

    # ── Static Recovery ──────────────────────────────────────────────────

    @staticmethod
    def recover_ethereum_address(message: bytes, signature: bytes) -> str:
        """Recover the Ethereum address that signed an EIP-191 message.

        Parameters
        ----------
        message : bytes
            The original message (before EIP-191 prefix).
        signature : bytes
            65-byte ``(r, s, v)`` signature.

        Returns
        -------
        str
            EIP-55 checksummed Ethereum address.

        Raises
        ------
        ValueError
            If recovery fails (invalid signature).
        """
        msg_hash = _eip191_hash(message)
        try:
            sig = eth_keys_mod.Signature(signature)
            recovered_pub = sig.recover_public_key_from_msg_hash(msg_hash)
            return recovered_pub.to_checksum_address()
        except Exception as e:
            raise ValueError(f"Signature recovery failed: {e}") from e

    @staticmethod
    def recover_eip712_address(
        domain: Dict[str, Any],
        types: Dict[str, List[Dict[str, str]]],
        message: Dict[str, Any],
        signature: bytes,
        primary_type: str = "",
    ) -> str:
        """Recover the Ethereum address that signed EIP-712 typed data.

        Parameters
        ----------
        domain, types, message, primary_type :
            Same as :meth:`sign_eip712`.
        signature : bytes
            65-byte ``(r, s, v)`` signature.

        Returns
        -------
        str
            EIP-55 checksummed Ethereum address.

        Raises
        ------
        ValueError
            If recovery fails.
        """
        # Build the same hash as sign_eip712
        if not primary_type:
            for key in types:
                if key != "EIP712Domain":
                    primary_type = key
                    break

        domain_fields: List[Dict[str, str]] = []
        if "name" in domain:
            domain_fields.append({"name": "name", "type": "string"})
        if "version" in domain:
            domain_fields.append({"name": "version", "type": "string"})
        if "chainId" in domain:
            domain_fields.append({"name": "chainId", "type": "uint256"})
        if "verifyingContract" in domain:
            domain_fields.append({"name": "verifyingContract", "type": "address"})
        if "salt" in domain:
            domain_fields.append({"name": "salt", "type": "bytes32"})

        full_types = {**types, "EIP712Domain": domain_fields}
        domain_separator = _hash_eip712_struct("EIP712Domain", domain, full_types)
        struct_hash = _hash_eip712_struct(primary_type, message, full_types)
        final_hash = _keccak256(b"\x19\x01" + domain_separator + struct_hash)

        try:
            sig = eth_keys_mod.Signature(signature)
            recovered_pub = sig.recover_public_key_from_msg_hash(final_hash)
            return recovered_pub.to_checksum_address()
        except Exception as e:
            raise ValueError(f"EIP-712 signature recovery failed: {e}") from e

    # ── Utilities ────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, str]:
        """Serialize identity to a dict (excludes private key).

        Returns
        -------
        dict
            Public identity information.
        """
        return {
            "ethereum_address": self._eth_address,
            "rings_did": self._rings_did,
            "public_key": self.public_key_hex,
            "public_key_compressed": self.public_key_compressed_hex,
        }

    def __repr__(self) -> str:
        return (
            f"RingsEthIdentity("
            f"eth={self._eth_address[:10]}…, "
            f"did={self._rings_did})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RingsEthIdentity):
            return NotImplemented
        return self._private_bytes == other._private_bytes

    def __hash__(self) -> int:
        return hash(self._private_bytes)

    # ── Private Derivation ───────────────────────────────────────────────

    def _derive_ethereum_address(self) -> str:
        """Derive EIP-55 checksummed Ethereum address from the public key.

        Steps:
        1. Take 64 bytes of the uncompressed public key (skip ``0x04`` prefix)
        2. ``keccak256(64_bytes)``
        3. Take last 20 bytes
        4. Apply EIP-55 checksum
        """
        # public_uncompressed[0] == 0x04 (uncompressed point marker)
        pub_xy = self._public_uncompressed[1:]  # 64 bytes
        address_bytes = _keccak256(pub_xy)[-20:]
        return _eip55_checksum(address_bytes.hex())

    def _derive_rings_did(self) -> str:
        """Derive a Rings DID from the compressed public key.

        Format: ``did:rings:secp256k1:<fingerprint>``

        The fingerprint is the first 20 hex chars of SHA-1 of the
        compressed public key bytes (matching the existing DID module's
        convention).
        """
        fingerprint = hashlib.sha1(self._public_compressed).hexdigest()[:20]
        return f"did:rings:secp256k1:{fingerprint}"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _eip191_hash(message: bytes) -> bytes:
    """Compute the EIP-191 personal sign hash.

    ::

        keccak256("\\x19Ethereum Signed Message:\\n" + str(len(message)) + message)

    Parameters
    ----------
    message : bytes
        The raw message.

    Returns
    -------
    bytes
        32-byte keccak256 hash.
    """
    prefix = _EIP191_PREFIX + str(len(message)).encode("ascii")
    return _keccak256(prefix + message)
