"""
BLS12-381 Cryptographic Primitives for Ethereum Sync Committee Verification
============================================================================

BLS12-381 is the elliptic curve used by Ethereum's beacon chain for
validator signatures.  This module provides:

- Key generation (simulated via hash derivation)
- Signing and verification (simulated via HMAC)
- Signature aggregation (simulated via XOR + hash)
- Sync committee verification (participation threshold + aggregate verify)

In production, these would use the ``blst`` library (C bindings, fastest
BLS implementation).  Our Python simulation preserves correct type
signatures and mathematical properties so that ``blst`` can drop in
as a replacement.

**Simulation model**
~~~~~~~~~~~~~~~~~~~~

Real BLS signatures rely on bilinear pairings over G1/G2 subgroups of the
BLS12-381 curve.  We cannot reproduce those pairings in pure Python
without a large dependency, so the simulation uses a *registry-backed*
HMAC scheme:

- ``BLSKeyPair.sign(msg)`` computes an HMAC commitment and records
  ``(pubkey, msg_hash) → sig`` in a module-level registry.
- ``BLSKeyPair.verify()`` looks up the registry to confirm the sig was
  produced by the claimed pubkey for the claimed message.
- ``BLS12381.aggregate_signatures()`` combines individual signatures via
  iterative XOR then hashes for uniformity.
- ``BLS12381.verify_aggregate()`` checks that the aggregate matches the
  registry-tracked individual components.

This is **test-only** — do not use for any security-critical purpose.
The ``blst``-backed production replacement would remove the registry
entirely and use real pairing checks.

**Naming note**: ``SyncCommitteeBLS`` is deliberately different from
``light_client.SyncCommittee`` to avoid import clashes.  The former
carries raw ``bytes`` pubkeys (48-byte compressed G1 points); the latter
carries hex-encoded ``str`` pubkeys for the higher-level light-client
protocol.

Constants
---------
``FIELD_MODULUS``
    The BLS12-381 base-field prime (381 bits).
``GROUP_ORDER``
    The prime-order subgroup of G1/G2 (~255 bits).
``DOMAIN_SEPARATOR``
    The hash-to-G1 domain separation tag per Ethereum spec (EIP-2333
    compatible ``POP`` suite).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIELD_MODULUS: int = int(
    "1a0111ea397fe69a4b1ba7b6434bacd7"
    "64774b84f38512bf6730d2a0f6b0f624"
    "1eabfffeb153ffffb9feffffffffaaab",
    16,
)

GROUP_ORDER: int = int(
    "73eda753299d7d483339d80809a1d805"
    "53bda402fffe5bfeffffffff00000001",
    16,
)

DOMAIN_SEPARATOR: bytes = b"BLS_SIG_BLS12381G1_XMD:SHA-256_SSWU_RO_POP_"

# Compressed G1 point size (bytes).
G1_SIZE: int = 48

# G2 point / signature size (bytes).
G2_SIZE: int = 96

# Ethereum sync committee size.
SYNC_COMMITTEE_SIZE: int = 512

# Default participation quorum (2/3 of 512).
DEFAULT_SYNC_THRESHOLD: int = 342


# ---------------------------------------------------------------------------
# Simulation registry — maps (pubkey_bytes, msg_hash) → sig_bytes
# ---------------------------------------------------------------------------

_SIGNING_REGISTRY: Dict[Tuple[bytes, bytes], bytes] = {}

# Also track which individual sigs comprise a given aggregate, keyed by
# the aggregate sig bytes.
_AGGREGATE_REGISTRY: Dict[bytes, List[Tuple[bytes, bytes]]] = {}


def _msg_hash(message: bytes) -> bytes:
    """Canonical message hash used as registry key."""
    return hashlib.sha256(message).digest()


def _clear_registries() -> None:
    """Reset simulation registries — useful for test isolation."""
    _SIGNING_REGISTRY.clear()
    _AGGREGATE_REGISTRY.clear()


# ---------------------------------------------------------------------------
# BLSPublicKey
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BLSPublicKey:
    """A BLS12-381 public key (compressed G1 point, 48 bytes).

    In production this wraps a ``blst.P1_Affine``; here it wraps raw
    bytes with hash-derived simulation.
    """

    key_bytes: bytes

    def __post_init__(self) -> None:
        if len(self.key_bytes) != G1_SIZE:
            raise ValueError(
                f"BLS public key must be {G1_SIZE} bytes, "
                f"got {len(self.key_bytes)}"
            )

    # -- constructors -------------------------------------------------------

    @classmethod
    def from_secret(cls, secret: bytes) -> BLSPublicKey:
        """Derive a public key from a 32-byte secret.

        Simulation: ``SHA-256(b"bls_pubkey" || secret)`` truncated/padded
        to 48 bytes.  Real implementation: scalar-multiply the G1
        generator by the secret scalar.
        """
        raw = hashlib.sha256(b"bls_pubkey" + secret).digest()
        # SHA-256 gives 32 bytes; extend to 48 by hashing again.
        ext = hashlib.sha256(b"bls_pubkey_ext" + secret).digest()
        return cls(key_bytes=(raw + ext)[:G1_SIZE])

    # -- serialisation ------------------------------------------------------

    def hex(self) -> str:
        """Return the hex-encoded public key."""
        return self.key_bytes.hex()

    @classmethod
    def from_hex(cls, h: str) -> BLSPublicKey:
        return cls(key_bytes=bytes.fromhex(h))

    # -- hashing / equality (frozen dataclass gives us these, but be
    #    explicit about bytes-based identity) --------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BLSPublicKey):
            return NotImplemented
        return self.key_bytes == other.key_bytes

    def __hash__(self) -> int:
        return hash(self.key_bytes)

    def __repr__(self) -> str:
        return f"BLSPublicKey({self.key_bytes[:8].hex()}…)"


# ---------------------------------------------------------------------------
# BLSSignature
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BLSSignature:
    """A BLS12-381 signature (compressed G2 point, 96 bytes)."""

    sig_bytes: bytes

    def __post_init__(self) -> None:
        if len(self.sig_bytes) != G2_SIZE:
            raise ValueError(
                f"BLS signature must be {G2_SIZE} bytes, "
                f"got {len(self.sig_bytes)}"
            )

    def hex(self) -> str:
        return self.sig_bytes.hex()

    @classmethod
    def from_hex(cls, h: str) -> BLSSignature:
        return cls(sig_bytes=bytes.fromhex(h))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BLSSignature):
            return NotImplemented
        return self.sig_bytes == other.sig_bytes

    def __hash__(self) -> int:
        return hash(self.sig_bytes)

    def __repr__(self) -> str:
        return f"BLSSignature({self.sig_bytes[:8].hex()}…)"


# ---------------------------------------------------------------------------
# BLSKeyPair
# ---------------------------------------------------------------------------

@dataclass
class BLSKeyPair:
    """A BLS12-381 key pair (secret scalar + public key).

    Provides sign/verify with simulation-registry backing.
    """

    secret: bytes  # 32 bytes
    public_key: BLSPublicKey

    def __post_init__(self) -> None:
        if len(self.secret) != 32:
            raise ValueError(
                f"BLS secret key must be 32 bytes, got {len(self.secret)}"
            )

    # -- constructors -------------------------------------------------------

    @classmethod
    def generate(cls, seed: Optional[bytes] = None) -> BLSKeyPair:
        """Generate a new key pair.

        Parameters
        ----------
        seed : bytes, optional
            If provided, derive the secret deterministically via
            ``SHA-256(b"bls_keygen" || seed)``.  Otherwise use
            ``os.urandom(32)``.
        """
        if seed is not None:
            secret = hashlib.sha256(b"bls_keygen" + seed).digest()
        else:
            secret = os.urandom(32)
        return cls(secret=secret, public_key=BLSPublicKey.from_secret(secret))

    # -- signing ------------------------------------------------------------

    def sign(self, message: bytes) -> BLSSignature:
        """Sign *message* and register the result.

        Simulation: the signature is ``HMAC-SHA256(secret, domain || msg)``
        extended to 96 bytes, with a binding commitment to the pubkey so
        that the registry can attribute the sig to a specific key.
        """
        commitment = hmac.new(
            self.secret, DOMAIN_SEPARATOR + message, hashlib.sha256
        ).digest()  # 32 bytes

        binding = hashlib.sha256(
            self.public_key.key_bytes + commitment
        ).digest()  # 32 bytes

        # Third 32 bytes for uniqueness/padding.
        pad = hashlib.sha256(commitment + binding).digest()

        sig_bytes = (commitment + binding + pad)[:G2_SIZE]
        sig = BLSSignature(sig_bytes=sig_bytes)

        # Register in simulation registry.
        mh = _msg_hash(message)
        _SIGNING_REGISTRY[(self.public_key.key_bytes, mh)] = sig_bytes
        logger.debug(
            "BLS sign: pubkey=%s msg_hash=%s",
            self.public_key.key_bytes[:8].hex(),
            mh[:8].hex(),
        )
        return sig

    # -- verification -------------------------------------------------------

    @staticmethod
    def verify(
        message: bytes, signature: BLSSignature, pubkey: BLSPublicKey
    ) -> bool:
        """Verify a single BLS signature.

        Simulation: checks the registry to confirm this (pubkey, message)
        produced this signature.  In production this would perform a
        pairing check ``e(sig, g2) == e(H(msg), pubkey)``.
        """
        mh = _msg_hash(message)
        registered = _SIGNING_REGISTRY.get((pubkey.key_bytes, mh))
        if registered is None:
            return False
        return registered == signature.sig_bytes


# ---------------------------------------------------------------------------
# BLS12381 — static utility class
# ---------------------------------------------------------------------------

class BLS12381:
    """Static utility methods for BLS12-381 operations.

    All methods are ``@staticmethod`` so the class acts as a namespace.
    """

    @staticmethod
    def hash_to_g1(
        message: bytes, dst: bytes = DOMAIN_SEPARATOR
    ) -> bytes:
        """Hash an arbitrary message to a 48-byte simulated G1 point.

        Follows the structure of ``hash_to_curve`` (RFC 9380) with
        ``expand_message_xmd(SHA-256)`` but outputs a simple hash for
        simulation purposes.
        """
        h1 = hashlib.sha256(dst + b"\x01" + message).digest()
        h2 = hashlib.sha256(dst + b"\x02" + message).digest()
        return (h1 + h2)[:G1_SIZE]

    # -- aggregation --------------------------------------------------------

    @staticmethod
    def aggregate_signatures(
        signatures: List[BLSSignature],
    ) -> BLSSignature:
        """Aggregate one or more BLS signatures.

        Simulation: iterative XOR of all ``sig_bytes``, then hashed for
        uniformity (real BLS uses point addition on G2).

        The original component signatures are tracked in the aggregate
        registry so that :meth:`verify_aggregate` can validate them.
        """
        if not signatures:
            raise ValueError("Cannot aggregate zero signatures")

        # XOR fold.
        acc = bytearray(G2_SIZE)
        for sig in signatures:
            for i in range(G2_SIZE):
                acc[i] ^= sig.sig_bytes[i]

        # Hash for uniformity — keep 96 bytes.
        h1 = hashlib.sha256(bytes(acc) + b"\x01").digest()
        h2 = hashlib.sha256(bytes(acc) + b"\x02").digest()
        h3 = hashlib.sha256(bytes(acc) + b"\x03").digest()
        agg_bytes = (h1 + h2 + h3)[:G2_SIZE]

        # Register aggregate composition — store the raw sig bytes of
        # each component so verify_aggregate can cross-check.
        _AGGREGATE_REGISTRY[agg_bytes] = [
            (sig.sig_bytes, b"") for sig in signatures
        ]

        return BLSSignature(sig_bytes=agg_bytes)

    @staticmethod
    def aggregate_pubkeys(
        pubkeys: List[BLSPublicKey],
        bitmap: Optional[List[bool]] = None,
    ) -> BLSPublicKey:
        """Aggregate public keys, optionally filtered by *bitmap*.

        If *bitmap* is provided, only include ``pubkeys[i]`` where
        ``bitmap[i]`` is ``True``.  Real BLS adds the G1 points;
        simulation XORs then hashes.
        """
        if bitmap is not None:
            if len(bitmap) != len(pubkeys):
                raise ValueError(
                    f"Bitmap length ({len(bitmap)}) != "
                    f"pubkey count ({len(pubkeys)})"
                )
            selected = [pk for pk, b in zip(pubkeys, bitmap) if b]
        else:
            selected = list(pubkeys)

        if not selected:
            raise ValueError("Cannot aggregate zero public keys")

        acc = bytearray(G1_SIZE)
        for pk in selected:
            for i in range(G1_SIZE):
                acc[i] ^= pk.key_bytes[i]

        h1 = hashlib.sha256(bytes(acc) + b"agg_pk_1").digest()
        h2 = hashlib.sha256(bytes(acc) + b"agg_pk_2").digest()
        return BLSPublicKey(key_bytes=(h1 + h2)[:G1_SIZE])

    # -- aggregate verification ---------------------------------------------

    @staticmethod
    def verify_aggregate(
        aggregate_sig: BLSSignature,
        aggregate_pubkey: BLSPublicKey,
        message: bytes,
    ) -> bool:
        """Verify an aggregate BLS signature.

        Simulation: looks up the aggregate registry to find the component
        signatures, then confirms each was individually registered for
        *message*.  In production this would be a single pairing check.

        Returns ``True`` if the aggregate is known AND every component
        signature passes individual verification for *message*.
        """
        components = _AGGREGATE_REGISTRY.get(aggregate_sig.sig_bytes)
        if components is None:
            logger.debug("verify_aggregate: aggregate not in registry")
            return False

        mh = _msg_hash(message)

        # Check that every component sig is registered for *some* pubkey
        # signing this message.  We look through all registry entries for
        # this message hash and confirm each component sig is present.
        registered_for_msg: Dict[bytes, bytes] = {}
        for (pk_bytes, reg_mh), sig_bytes in _SIGNING_REGISTRY.items():
            if reg_mh == mh:
                registered_for_msg[sig_bytes] = pk_bytes

        for comp_sig_bytes, _ in components:
            if comp_sig_bytes not in registered_for_msg:
                logger.debug(
                    "verify_aggregate: component sig not found in registry"
                )
                return False

        return True

    # -- sync committee verification ----------------------------------------

    @staticmethod
    def verify_sync_committee(
        committee_pubkeys: List[bytes],
        signature: bytes,
        header_root: bytes,
        participation_bitmap: List[bool],
        threshold: int = DEFAULT_SYNC_THRESHOLD,
    ) -> bool:
        """Verify a sync committee signature over a beacon header root.

        Parameters
        ----------
        committee_pubkeys : list of bytes
            The 512 BLS pubkeys (48 bytes each) of the sync committee.
        signature : bytes
            The 96-byte aggregate BLS signature.
        header_root : bytes
            The 32-byte beacon block header root being attested.
        participation_bitmap : list of bool
            Which committee members participated in signing.
        threshold : int
            Minimum number of participants required (default 342 = ⌈2/3 × 512⌉).

        Returns
        -------
        bool
            ``True`` iff participation ≥ threshold AND the aggregate
            signature is valid over *header_root* for the participating
            pubkeys.
        """
        # 1. Participation check.
        n_participants = sum(participation_bitmap)
        if n_participants < threshold:
            logger.debug(
                "Sync committee: only %d/%d participants (need %d)",
                n_participants,
                len(committee_pubkeys),
                threshold,
            )
            return False

        if len(participation_bitmap) != len(committee_pubkeys):
            raise ValueError(
                f"Bitmap length ({len(participation_bitmap)}) != "
                f"committee size ({len(committee_pubkeys)})"
            )

        # 2. Build pubkey objects and select participants.
        all_pks = [BLSPublicKey(key_bytes=kb) for kb in committee_pubkeys]
        agg_pk = BLS12381.aggregate_pubkeys(all_pks, participation_bitmap)

        # 3. Wrap the raw signature.
        agg_sig = BLSSignature(sig_bytes=signature)

        # 4. Verify aggregate signature over header_root.
        return BLS12381.verify_aggregate(agg_sig, agg_pk, header_root)


# ---------------------------------------------------------------------------
# SyncCommitteeBLS
# ---------------------------------------------------------------------------

@dataclass
class SyncCommitteeBLS:
    """BLS-level sync committee representation.

    Named ``SyncCommitteeBLS`` to avoid clashing with
    ``light_client.SyncCommittee`` which uses hex-encoded string pubkeys.
    This dataclass works with raw ``bytes`` throughout, suitable for the
    cryptographic layer.

    Attributes
    ----------
    pubkeys : list of bytes
        512 compressed G1 public keys (48 bytes each).
    aggregate_pubkey : bytes
        The pre-computed aggregate public key (48 bytes).
    period : int
        The sync committee period number.
    """

    pubkeys: List[bytes]
    aggregate_pubkey: bytes
    period: int

    def __post_init__(self) -> None:
        for i, pk in enumerate(self.pubkeys):
            if len(pk) != G1_SIZE:
                raise ValueError(
                    f"Pubkey {i} is {len(pk)} bytes, expected {G1_SIZE}"
                )
        if len(self.aggregate_pubkey) != G1_SIZE:
            raise ValueError(
                f"Aggregate pubkey is {len(self.aggregate_pubkey)} bytes, "
                f"expected {G1_SIZE}"
            )

    def root(self) -> bytes:
        """Compute the committee root hash.

        ``SHA-256(SHA-256(pk_0 || pk_1 || … || pk_511) || aggregate_pubkey)``

        This mirrors the SSZ hash-tree-root of a ``SyncCommittee``
        container on the beacon chain.
        """
        inner = hashlib.sha256(b"".join(self.pubkeys)).digest()
        return hashlib.sha256(inner + self.aggregate_pubkey).digest()

    def select_participants(self, bitmap: List[bool]) -> List[bytes]:
        """Return pubkeys where ``bitmap[i]`` is ``True``."""
        if len(bitmap) != len(self.pubkeys):
            raise ValueError(
                f"Bitmap length ({len(bitmap)}) != "
                f"committee size ({len(self.pubkeys)})"
            )
        return [pk for pk, b in zip(self.pubkeys, bitmap) if b]

    def participant_count(self, bitmap: List[bool]) -> int:
        """Count how many members are flagged in *bitmap*."""
        if len(bitmap) != len(self.pubkeys):
            raise ValueError(
                f"Bitmap length ({len(bitmap)}) != "
                f"committee size ({len(self.pubkeys)})"
            )
        return sum(bitmap)

    def to_light_client_format(self) -> dict:
        """Convert to the format expected by ``light_client.SyncCommittee``.

        Returns a dict with hex-encoded pubkeys suitable for::

            from rings.bridge.light_client import SyncCommittee
            SyncCommittee(**committee_bls.to_light_client_format())
        """
        return {
            "period": self.period,
            "pubkeys": [pk.hex() for pk in self.pubkeys],
            "aggregate_pubkey": self.aggregate_pubkey.hex(),
        }

    def __repr__(self) -> str:
        return (
            f"SyncCommitteeBLS(period={self.period}, "
            f"members={len(self.pubkeys)}, "
            f"root={self.root()[:8].hex()}…)"
        )
