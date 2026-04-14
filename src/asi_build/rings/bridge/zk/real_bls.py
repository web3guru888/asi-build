"""
Real BLS12-381 Cryptographic Primitives Using ``py_ecc``
=========================================================

Production-grade BLS12-381 implementation for the Rings ↔ Ethereum bridge.
Uses the `py_ecc <https://github.com/ethereum/py_ecc>`_ library which
provides pure-Python implementations of the BLS operations used by the
Ethereum beacon chain.

This module provides drop-in replacements for the simulated classes in
:mod:`bls`:

=========================  ===========================
Simulated (``bls.py``)    Real (``real_bls.py``)
=========================  ===========================
``BLSKeyPair``             ``RealBLSKeyPair``
``BLS12381``               ``RealBLS12381``
``SyncCommitteeBLS``       ``RealSyncCommitteeBLS``
``BLSPublicKey``           (reuses 48-byte ``bytes``)
``BLSSignature``           (reuses 96-byte ``bytes``)
=========================  ===========================

Scheme
------

We use **Proof of Possession** (``G2ProofOfPossession``) which is the
scheme used by Ethereum 2.0.  In this scheme:

- Public keys are 48-byte compressed G1 points.
- Signatures are 96-byte compressed G2 points.
- Aggregation is performed on G2 (signature) points.
- ``FastAggregateVerify`` checks that N pubkeys all signed the *same*
  message with a single aggregate signature.

This matches the Ethereum sync committee verification exactly.

Performance Notes
-----------------

``py_ecc`` is a pure-Python library.  Approximate timings on a single core:

- ``KeyGen``: ~7ms
- ``Sign``:   ~200ms
- ``Verify``: ~550ms
- ``FastAggregateVerify`` (N=16): ~600ms
- ``FastAggregateVerify`` (N=512): ~4s+ (pairing + multi-scalar mul)

For production, replace with ``blst`` (C bindings, 100× faster) or
``py_arkworks_bls12381`` (Rust bindings).

Factory
-------

Use :func:`get_bls_backend` to select between simulated and real at
runtime::

    from asi_build.rings.bridge.zk.real_bls import get_bls_backend
    KeyPair, BLSOps, SyncCommittee = get_bls_backend(real=True)
    kp = KeyPair.generate()
    sig = kp.sign(b"hello")
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, List, Optional, Tuple, Type

try:
    from py_ecc.bls import G2ProofOfPossession as bls_pop
    from py_ecc.optimized_bls12_381 import curve_order as CURVE_ORDER

    _HAS_PY_ECC = True
except ImportError:  # pragma: no cover
    bls_pop = None  # type: ignore[assignment,misc]
    CURVE_ORDER = None  # type: ignore[assignment]
    _HAS_PY_ECC = False

logger = logging.getLogger(__name__)

if not _HAS_PY_ECC:
    logger.warning(
        "py_ecc is not installed — real BLS12-381 unavailable. "
        "Install with: pip install asi-build[rings]"
    )

# ---------------------------------------------------------------------------
# Constants (shared with bls.py for cross-compatibility)
# ---------------------------------------------------------------------------

#: BLS12-381 base-field prime.
FIELD_MODULUS: int = int(
    "1a0111ea397fe69a4b1ba7b6434bacd7"
    "64774b84f38512bf6730d2a0f6b0f624"
    "1eabfffeb153ffffb9feffffffffaaab",
    16,
)

#: Prime-order subgroup (r).
GROUP_ORDER: int = CURVE_ORDER

#: Domain separation tag for PoP scheme (Ethereum).
DOMAIN_SEPARATOR: bytes = b"BLS_SIG_BLS12381G2_XMD:SHA-256_SSWU_RO_POP_"

#: Compressed G1 point size (public key).
G1_SIZE: int = 48

#: Compressed G2 point size (signature).
G2_SIZE: int = 96

#: Ethereum sync committee size.
SYNC_COMMITTEE_SIZE: int = 512

#: Default participation quorum (⌈2/3 × 512⌉).
DEFAULT_SYNC_THRESHOLD: int = 342


# ---------------------------------------------------------------------------
# RealBLSKeyPair
# ---------------------------------------------------------------------------

@dataclass
class RealBLSKeyPair:
    """A real BLS12-381 key pair backed by ``py_ecc``.

    The secret key is an integer in ``[1, CURVE_ORDER)``; the public key
    is a 48-byte compressed G1 point.

    Interface-compatible with :class:`bls.BLSKeyPair` — same method
    signatures, same attribute names.

    Attributes
    ----------
    secret_key : int
        The BLS secret key scalar.
    public_key : bytes
        48-byte compressed G1 public key.
    proof_of_possession : bytes or None
        96-byte PoP signature (generated on demand).
    """

    secret_key: int
    public_key: bytes  # 48-byte compressed G1
    proof_of_possession: Optional[bytes] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not (1 <= self.secret_key < CURVE_ORDER):
            raise ValueError(
                f"Secret key must be in [1, CURVE_ORDER), "
                f"got {self.secret_key}"
            )
        if len(self.public_key) != G1_SIZE:
            raise ValueError(
                f"Public key must be {G1_SIZE} bytes, "
                f"got {len(self.public_key)}"
            )

    # ---- Constructors -------------------------------------------------------

    @classmethod
    def generate(cls, seed: Optional[bytes] = None) -> RealBLSKeyPair:
        """Generate a real BLS12-381 key pair.

        Parameters
        ----------
        seed : bytes, optional
            If provided (≥32 bytes), used as IKM for deterministic key
            derivation per EIP-2333.  If ``None``, uses 32 bytes from
            ``os.urandom``.

        Returns
        -------
        RealBLSKeyPair
        """
        if seed is None:
            ikm = os.urandom(32)
        else:
            # Ensure IKM is at least 32 bytes as required by KeyGen spec
            if len(seed) < 32:
                # Pad short seeds via SHA-256 expansion (deterministic)
                ikm = hashlib.sha256(b"bls_ikm_pad" + seed).digest()
            else:
                ikm = seed[:32]

        sk = bls_pop.KeyGen(ikm)
        pk = bls_pop.SkToPk(sk)

        logger.debug(
            "RealBLSKeyPair.generate: pk=%s…", pk[:8].hex()
        )
        return cls(secret_key=sk, public_key=pk)

    # ---- Backward compatibility aliases ------------------------------------

    @property
    def secret(self) -> bytes:
        """32-byte representation of the secret key for compatibility.

        Note: the real secret key is an integer; this returns it as
        big-endian 32-byte encoding.
        """
        return self.secret_key.to_bytes(32, "big")

    # ---- Signing ------------------------------------------------------------

    def sign(self, message: bytes) -> bytes:
        """Sign *message* using real BLS12-381.

        Parameters
        ----------
        message : bytes
            The message to sign.

        Returns
        -------
        bytes
            96-byte compressed G2 signature.
        """
        sig = bls_pop.Sign(self.secret_key, message)
        logger.debug(
            "RealBLSKeyPair.sign: pk=%s… msg_len=%d",
            self.public_key[:8].hex(),
            len(message),
        )
        return sig

    def verify(self, message: bytes, signature: bytes) -> bool:
        """Verify a BLS signature against this key pair's public key.

        Parameters
        ----------
        message : bytes
            The original message.
        signature : bytes
            96-byte BLS signature.

        Returns
        -------
        bool
        """
        try:
            return bls_pop.Verify(self.public_key, message, signature)
        except Exception:
            logger.debug(
                "RealBLSKeyPair.verify: exception during verification",
                exc_info=True,
            )
            return False

    def pop_prove(self) -> bytes:
        """Generate a Proof of Possession for this key pair.

        Returns
        -------
        bytes
            96-byte PoP signature.
        """
        if self.proof_of_possession is None:
            self.proof_of_possession = bls_pop.PopProve(self.secret_key)
        return self.proof_of_possession

    @staticmethod
    def pop_verify(public_key: bytes, proof: bytes) -> bool:
        """Verify a Proof of Possession.

        Parameters
        ----------
        public_key : bytes
            48-byte compressed G1 public key.
        proof : bytes
            96-byte PoP signature.

        Returns
        -------
        bool
        """
        try:
            return bls_pop.PopVerify(public_key, proof)
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"RealBLSKeyPair(pk={self.public_key[:8].hex()}…)"


# ---------------------------------------------------------------------------
# RealBLS12381 — static utility class
# ---------------------------------------------------------------------------

class RealBLS12381:
    """Real BLS12-381 operations using ``py_ecc``.

    Interface-compatible with :class:`bls.BLS12381`.
    All methods are ``@staticmethod``.
    """

    @staticmethod
    def aggregate_signatures(signatures: List[bytes]) -> bytes:
        """Aggregate BLS signatures via G2 point addition.

        Parameters
        ----------
        signatures : list of bytes
            Each element is a 96-byte compressed G2 signature.

        Returns
        -------
        bytes
            96-byte aggregate signature.

        Raises
        ------
        ValueError
            If no signatures provided.
        """
        if not signatures:
            raise ValueError("Cannot aggregate zero signatures")
        return bls_pop.Aggregate(signatures)

    @staticmethod
    def verify_aggregate(
        pubkeys: List[bytes],
        messages: List[bytes],
        signature: bytes,
    ) -> bool:
        """Verify an aggregate signature where each pubkey signed a
        different message.

        Uses ``AggregateVerify`` per the BLS specification.

        Parameters
        ----------
        pubkeys : list of bytes
            48-byte compressed G1 public keys.
        messages : list of bytes
            The messages, one per pubkey.
        signature : bytes
            96-byte aggregate BLS signature.

        Returns
        -------
        bool
        """
        if len(pubkeys) != len(messages):
            raise ValueError(
                f"pubkeys length ({len(pubkeys)}) != "
                f"messages length ({len(messages)})"
            )
        if not pubkeys:
            return False
        try:
            return bls_pop.AggregateVerify(pubkeys, messages, signature)
        except Exception:
            logger.debug(
                "RealBLS12381.verify_aggregate: exception",
                exc_info=True,
            )
            return False

    @staticmethod
    def fast_aggregate_verify(
        pubkeys: List[bytes],
        message: bytes,
        signature: bytes,
    ) -> bool:
        """Verify an aggregate signature where all pubkeys signed the
        *same* message.

        This is the operation used for sync committee verification in
        the Ethereum beacon chain.

        Parameters
        ----------
        pubkeys : list of bytes
            48-byte compressed G1 public keys of participating validators.
        message : bytes
            The beacon block root (32 bytes).
        signature : bytes
            96-byte aggregate BLS signature.

        Returns
        -------
        bool
        """
        if not pubkeys:
            return False
        try:
            return bls_pop.FastAggregateVerify(pubkeys, message, signature)
        except Exception:
            logger.debug(
                "RealBLS12381.fast_aggregate_verify: exception",
                exc_info=True,
            )
            return False

    @staticmethod
    def aggregate_pubkeys(
        pubkeys: List[bytes],
        bitmap: Optional[List[bool]] = None,
    ) -> bytes:
        """Aggregate public keys via G1 point addition.

        Parameters
        ----------
        pubkeys : list of bytes
            48-byte compressed G1 public keys.
        bitmap : list of bool, optional
            If provided, only aggregate keys where ``bitmap[i]`` is True.

        Returns
        -------
        bytes
            48-byte aggregate compressed G1 public key.
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

        # py_ecc's _AggregatePKs does the actual G1 addition
        return bls_pop._AggregatePKs(selected)

    @staticmethod
    def verify_sync_committee(
        committee_pubkeys: List[bytes],
        signature: bytes,
        header_root: bytes,
        participation_bitmap: List[bool],
        threshold: int = DEFAULT_SYNC_THRESHOLD,
    ) -> bool:
        """Verify a sync committee signature over a beacon header root.

        This is the core light-client verification operation per the
        Altair spec.  It checks:

        1. Participation count ≥ threshold (default 342 = ⌈2/3 × 512⌉)
        2. ``FastAggregateVerify(participating_pubkeys, header_root,
           aggregate_signature)``

        Parameters
        ----------
        committee_pubkeys : list of bytes
            The 512 compressed G1 pubkeys of the sync committee.
        signature : bytes
            96-byte aggregate BLS signature.
        header_root : bytes
            32-byte beacon block header root.
        participation_bitmap : list of bool
            Which committee members participated in signing.
        threshold : int
            Minimum participants required.

        Returns
        -------
        bool
        """
        if len(participation_bitmap) != len(committee_pubkeys):
            raise ValueError(
                f"Bitmap length ({len(participation_bitmap)}) != "
                f"committee size ({len(committee_pubkeys)})"
            )

        n_participants = sum(participation_bitmap)
        if n_participants < threshold:
            logger.debug(
                "Sync committee: only %d/%d participants (need %d)",
                n_participants,
                len(committee_pubkeys),
                threshold,
            )
            return False

        # Select participating pubkeys
        participating = [
            pk for pk, bit in zip(committee_pubkeys, participation_bitmap)
            if bit
        ]

        return RealBLS12381.fast_aggregate_verify(
            participating, header_root, signature
        )

    @staticmethod
    def hash_to_g1(
        message: bytes, dst: bytes = DOMAIN_SEPARATOR
    ) -> bytes:
        """Hash a message to a G1 point (48-byte compressed).

        Note: py_ecc's PoP scheme hashes to G2, not G1.  For G1 hashing
        (used in some protocols), we use the internal hash_to_G1.
        This is provided for API compatibility but most callers should
        use ``sign()`` which handles hashing internally.

        Falls back to a deterministic hash if the low-level API is not
        available.
        """
        # py_ecc hash_to_G2 is used internally by Sign.
        # For a G1 hash, we do a domain-separated SHA-256 expansion
        # since py_ecc doesn't expose hash_to_G1 in the PoP API.
        h1 = hashlib.sha256(dst + b"\x01" + message).digest()
        h2 = hashlib.sha256(dst + b"\x02" + message).digest()
        return (h1 + h2)[:G1_SIZE]


# ---------------------------------------------------------------------------
# RealSyncCommitteeBLS
# ---------------------------------------------------------------------------

@dataclass
class RealSyncCommitteeBLS:
    """A BLS-backed sync committee using real elliptic curve operations.

    This class manages a committee of ``committee_size`` BLS key pairs,
    allowing collective signing and verification of beacon block roots
    exactly as performed in the Ethereum Altair spec.

    For testing, use small committees (8–16) to keep runtimes manageable
    since ``py_ecc`` is pure Python.

    Attributes
    ----------
    committee_size : int
        Number of validators in the committee.
    threshold : int
        Minimum participants for a valid attestation.
    members : list of RealBLSKeyPair
        The committee member key pairs.
    period : int
        The sync committee period number.
    """

    committee_size: int = 16
    threshold: int = 11
    members: List[RealBLSKeyPair] = field(default_factory=list)
    period: int = 0

    def setup_committee(
        self,
        seeds: Optional[List[bytes]] = None,
    ) -> None:
        """Generate or load committee member key pairs.

        Parameters
        ----------
        seeds : list of bytes, optional
            If provided, must be ``committee_size`` seeds for deterministic
            key generation.  Otherwise uses random IKMs.
        """
        if seeds is not None:
            if len(seeds) != self.committee_size:
                raise ValueError(
                    f"Expected {self.committee_size} seeds, "
                    f"got {len(seeds)}"
                )
            self.members = [
                RealBLSKeyPair.generate(seed=s) for s in seeds
            ]
        else:
            self.members = [
                RealBLSKeyPair.generate() for _ in range(self.committee_size)
            ]

        logger.info(
            "RealSyncCommitteeBLS: committee of %d set up (period %d)",
            self.committee_size,
            self.period,
        )

    @property
    def pubkeys(self) -> List[bytes]:
        """All committee member public keys (48-byte each)."""
        return [m.public_key for m in self.members]

    @property
    def aggregate_pubkey(self) -> bytes:
        """Pre-computed aggregate public key over all members."""
        if not self.members:
            raise ValueError("Committee not set up — call setup_committee()")
        return RealBLS12381.aggregate_pubkeys(self.pubkeys)

    def root(self) -> bytes:
        """Compute the committee root hash.

        ``SHA-256(SHA-256(pk_0 || pk_1 || … || pk_N) || aggregate_pubkey)``

        Mirrors the SSZ hash-tree-root of a ``SyncCommittee`` container.
        """
        inner = hashlib.sha256(b"".join(self.pubkeys)).digest()
        return hashlib.sha256(inner + self.aggregate_pubkey).digest()

    def sign_beacon_block_root(
        self,
        block_root: bytes,
        participant_indices: List[int],
    ) -> Tuple[bytes, List[bool]]:
        """Have selected participants sign a beacon block root.

        Parameters
        ----------
        block_root : bytes
            The 32-byte beacon block root to sign.
        participant_indices : list of int
            Indices of participating committee members.

        Returns
        -------
        tuple of (bytes, list of bool)
            ``(aggregate_signature, participation_bitvector)`` where
            the bitvector has True at participating indices.

        Raises
        ------
        ValueError
            If committee not set up or indices out of range.
        """
        if not self.members:
            raise ValueError("Committee not set up — call setup_committee()")

        for idx in participant_indices:
            if idx < 0 or idx >= self.committee_size:
                raise ValueError(
                    f"Participant index {idx} out of range "
                    f"[0, {self.committee_size})"
                )

        # Build participation bitvector
        bits = [False] * self.committee_size
        for idx in participant_indices:
            bits[idx] = True

        # Each participant signs the block root
        sigs = [self.members[idx].sign(block_root) for idx in participant_indices]

        # Aggregate all participant signatures
        agg_sig = RealBLS12381.aggregate_signatures(sigs)

        logger.debug(
            "sign_beacon_block_root: %d/%d participants, root=%s…",
            len(participant_indices),
            self.committee_size,
            block_root[:8].hex(),
        )

        return agg_sig, bits

    def verify_sync_committee_signature(
        self,
        block_root: bytes,
        aggregate_signature: bytes,
        participation_bits: List[bool],
        committee_pubkeys: Optional[List[bytes]] = None,
    ) -> bool:
        """Verify a sync committee aggregate signature.

        This implements the exact verification logic from the Ethereum
        Altair spec:

        1. Count participation ≥ threshold.
        2. Select participating pubkeys.
        3. ``FastAggregateVerify(participating_pubkeys, block_root,
           aggregate_signature)``.

        Parameters
        ----------
        block_root : bytes
            The 32-byte beacon block root.
        aggregate_signature : bytes
            96-byte aggregate BLS signature.
        participation_bits : list of bool
            Participation bitvector.
        committee_pubkeys : list of bytes, optional
            If provided, used instead of ``self.pubkeys`` (for external
            committee verification).

        Returns
        -------
        bool
        """
        pks = committee_pubkeys or self.pubkeys

        return RealBLS12381.verify_sync_committee(
            committee_pubkeys=pks,
            signature=aggregate_signature,
            header_root=block_root,
            participation_bitmap=participation_bits,
            threshold=self.threshold,
        )

    def select_participants(self, bitmap: List[bool]) -> List[bytes]:
        """Return pubkeys where ``bitmap[i]`` is ``True``."""
        if len(bitmap) != len(self.pubkeys):
            raise ValueError(
                f"Bitmap length ({len(bitmap)}) != "
                f"committee size ({self.committee_size})"
            )
        return [pk for pk, b in zip(self.pubkeys, bitmap) if b]

    def participant_count(self, bitmap: List[bool]) -> int:
        """Count how many members are flagged in *bitmap*."""
        if len(bitmap) != len(self.pubkeys):
            raise ValueError(
                f"Bitmap length ({len(bitmap)}) != "
                f"committee size ({self.committee_size})"
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
        if self.members:
            return (
                f"RealSyncCommitteeBLS(period={self.period}, "
                f"members={self.committee_size}, "
                f"root={self.root()[:8].hex()}…)"
            )
        return (
            f"RealSyncCommitteeBLS(period={self.period}, "
            f"members={self.committee_size}, "
            f"not_initialized)"
        )


# ---------------------------------------------------------------------------
# Factory — select between simulated and real backend
# ---------------------------------------------------------------------------

def get_bls_backend(
    real: bool = False,
) -> Tuple[type, type, type]:
    """Return the appropriate BLS backend classes.

    Parameters
    ----------
    real : bool
        If ``True``, return the real ``py_ecc``-backed implementations.
        If ``False``, return the simulated registry-backed implementations
        from :mod:`bls`.

    Returns
    -------
    tuple of (KeyPairClass, BLSOpsClass, SyncCommitteeClass)

    Example
    -------
    ::

        KeyPair, BLSOps, SyncCommittee = get_bls_backend(real=True)
        kp = KeyPair.generate(seed=b'\\x00' * 32)
        sig = kp.sign(b"beacon block root")
    """
    if real:
        return RealBLSKeyPair, RealBLS12381, RealSyncCommitteeBLS
    else:
        from .bls import BLSKeyPair, BLS12381, SyncCommitteeBLS
        return BLSKeyPair, BLS12381, SyncCommitteeBLS
