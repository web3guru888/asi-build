"""
SSZ (Simple Serialize) — Ethereum Beacon Chain Serialization
=============================================================

Implements encoding, decoding, and Merkleization of beacon chain
types per the Ethereum consensus specification.

SSZ is the canonical serialization for all beacon chain data structures.
It supports:
- Fixed-size types: uint8..uint256, bool, bytes1..bytes32
- Variable-size types: List, Bitlist, ByteList
- Containers (structs with named, typed fields)
- Merkleization: computing hash_tree_root for all types
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ZERO_HASH = b"\x00" * 32
BYTES_PER_CHUNK = 32
SYNC_COMMITTEE_SIZE = 512
SUPERMAJORITY_THRESHOLD = (SYNC_COMMITTEE_SIZE * 2) // 3  # 341.33 → 342

_VALID_UINT_BITS = frozenset({8, 16, 32, 64, 128, 256})


# ---------------------------------------------------------------------------
# SSZSchema — lightweight type descriptors
# ---------------------------------------------------------------------------


class SSZType(Enum):
    """Primitive SSZ type descriptors."""

    UINT8 = auto()
    UINT16 = auto()
    UINT32 = auto()
    UINT64 = auto()
    UINT128 = auto()
    UINT256 = auto()
    BOOL = auto()
    BYTES4 = auto()
    BYTES32 = auto()
    BYTES48 = auto()
    BYTES96 = auto()


# Map SSZType → (is_fixed, fixed_size_bytes)
_TYPE_SIZE = {
    SSZType.UINT8: 1,
    SSZType.UINT16: 2,
    SSZType.UINT32: 4,
    SSZType.UINT64: 8,
    SSZType.UINT128: 16,
    SSZType.UINT256: 32,
    SSZType.BOOL: 1,
    SSZType.BYTES4: 4,
    SSZType.BYTES32: 32,
    SSZType.BYTES48: 48,
    SSZType.BYTES96: 96,
}


def _sha256(*parts: bytes) -> bytes:
    """SHA-256 over concatenated *parts*."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.digest()


def _next_power_of_two(n: int) -> int:
    """Return smallest 2**k >= n (minimum 1)."""
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


# ---------------------------------------------------------------------------
# SSZ — core static methods
# ---------------------------------------------------------------------------


class SSZ:
    """Static helpers for SSZ encode / decode / Merkleize."""

    # -- encoding -----------------------------------------------------------

    @staticmethod
    def encode_uint(value: int, bits: int) -> bytes:
        """Encode *value* as a little-endian unsigned int of *bits* width."""
        if bits not in _VALID_UINT_BITS:
            raise ValueError(f"Unsupported uint width: {bits}")
        byte_len = bits // 8
        if value < 0 or value >= (1 << bits):
            raise ValueError(
                f"Value {value} out of range for uint{bits}"
            )
        return value.to_bytes(byte_len, "little")

    @staticmethod
    def decode_uint(data: bytes, bits: int) -> int:
        """Decode a little-endian uint of *bits* width from *data*."""
        if bits not in _VALID_UINT_BITS:
            raise ValueError(f"Unsupported uint width: {bits}")
        byte_len = bits // 8
        if len(data) < byte_len:
            raise ValueError(
                f"Need {byte_len} bytes for uint{bits}, got {len(data)}"
            )
        return int.from_bytes(data[:byte_len], "little")

    @staticmethod
    def encode_bool(value: bool) -> bytes:
        """Encode a boolean as a single byte (0x01 / 0x00)."""
        return b"\x01" if value else b"\x00"

    @staticmethod
    def decode_bool(data: bytes) -> bool:
        """Decode a single-byte boolean."""
        if len(data) < 1:
            raise ValueError("Empty data for bool decode")
        if data[0] not in (0, 1):
            raise ValueError(f"Invalid bool byte: 0x{data[0]:02x}")
        return data[0] == 1

    @staticmethod
    def encode_bytes(value: bytes, fixed_length: int | None = None) -> bytes:
        """Encode fixed- or variable-length bytes.

        For fixed-length, pads or validates length.  For variable-length
        (``fixed_length=None``), returns the raw bytes (length is tracked
        externally in the container offset table).
        """
        if fixed_length is not None:
            if len(value) > fixed_length:
                raise ValueError(
                    f"Value length {len(value)} exceeds fixed_length "
                    f"{fixed_length}"
                )
            return value.ljust(fixed_length, b"\x00")
        return value  # variable-length

    @staticmethod
    def encode_container(
        fields: list[tuple[str, bytes, bool]],
    ) -> bytes:
        """Encode an SSZ container from pre-serialized fields.

        Parameters
        ----------
        fields : list of (name, serialized_bytes, is_fixed)
            Each field is already serialized.  *is_fixed* indicates
            whether the field is fixed-size (True) or variable-size
            (False).  Variable fields are placed after all fixed data
            with 4-byte little-endian offsets in the fixed part.

        Returns
        -------
        bytes
            The SSZ-encoded container.
        """
        fixed_parts: list[bytes | None] = []
        variable_parts: list[bytes] = []

        # First pass: separate fixed vs variable
        for _name, data, is_fixed in fields:
            if is_fixed:
                fixed_parts.append(data)
            else:
                fixed_parts.append(None)  # placeholder for offset
                variable_parts.append(data)

        # Calculate total fixed section size (4 bytes per offset slot)
        fixed_size = sum(
            len(p) if p is not None else 4 for p in fixed_parts
        )

        # Second pass: fill in offset values
        result = bytearray()
        var_idx = 0
        var_offset = fixed_size
        for part in fixed_parts:
            if part is not None:
                result.extend(part)
            else:
                result.extend(var_offset.to_bytes(4, "little"))
                var_offset += len(variable_parts[var_idx])
                var_idx += 1

        # Append variable parts
        for vp in variable_parts:
            result.extend(vp)

        return bytes(result)

    # -- Merkleization ------------------------------------------------------

    @staticmethod
    def merkleize(
        chunks: list[bytes], limit: int | None = None
    ) -> bytes:
        """Compute the Merkle root of *chunks*.

        Pads the list to the next power-of-two length with ``ZERO_HASH``
        chunks, then hashes pairs bottom-up.  If *limit* is given, the
        effective leaf count is ``next_power_of_two(limit)`` (used for
        lists with a declared maximum length).
        """
        # Determine target leaf count
        if limit is not None:
            leaf_count = _next_power_of_two(limit)
        else:
            leaf_count = _next_power_of_two(len(chunks)) if chunks else 1

        # Pad to leaf_count
        layer = list(chunks)
        while len(layer) < leaf_count:
            layer.append(ZERO_HASH)

        # Hash pairs bottom-up
        while len(layer) > 1:
            next_layer: list[bytes] = []
            for i in range(0, len(layer), 2):
                left = layer[i]
                right = layer[i + 1] if i + 1 < len(layer) else ZERO_HASH
                next_layer.append(_sha256(left, right))
            layer = next_layer

        return layer[0] if layer else ZERO_HASH

    @staticmethod
    def hash_tree_root_basic(value: int, bits: int) -> bytes:
        """Hash-tree-root for a basic uint type (pack into 32-byte chunk)."""
        encoded = SSZ.encode_uint(value, bits)
        chunk = encoded.ljust(BYTES_PER_CHUNK, b"\x00")
        return SSZ.merkleize([chunk])

    @staticmethod
    def hash_tree_root_bytes(value: bytes) -> bytes:
        """Hash-tree-root for variable-length bytes (``ByteList``).

        Packs into 32-byte chunks, merkleizes, then mixes in the length.
        """
        chunks = SSZ.pack([value], 1)
        root = SSZ.merkleize(chunks)
        return SSZ.mix_in_length(root, len(value))

    @staticmethod
    def hash_tree_root_container(field_roots: list[bytes]) -> bytes:
        """Hash-tree-root for a container — merkleize the field roots."""
        return SSZ.merkleize(field_roots)

    @staticmethod
    def mix_in_length(root: bytes, length: int) -> bytes:
        """``SHA-256(root || length_bytes)`` per SSZ spec."""
        length_bytes = length.to_bytes(32, "little")
        return _sha256(root, length_bytes)

    @staticmethod
    def pack(
        values: list[bytes], element_size: int
    ) -> list[bytes]:
        """Pack fixed-size serialized elements into 32-byte chunks.

        Concatenates all *values*, then splits into ``BYTES_PER_CHUNK``
        sized pieces (zero-padding the last chunk if needed).
        """
        concat = b"".join(values)
        if not concat:
            return [ZERO_HASH]
        n_chunks = math.ceil(len(concat) / BYTES_PER_CHUNK)
        chunks: list[bytes] = []
        for i in range(n_chunks):
            start = i * BYTES_PER_CHUNK
            end = start + BYTES_PER_CHUNK
            chunk = concat[start:end]
            if len(chunk) < BYTES_PER_CHUNK:
                chunk = chunk.ljust(BYTES_PER_CHUNK, b"\x00")
            chunks.append(chunk)
        return chunks


# ---------------------------------------------------------------------------
# BeaconBlockHeader — proper SSZ container
# ---------------------------------------------------------------------------


@dataclass
class BeaconBlockHeader:
    """Beacon chain block header with correct SSZ serialization.

    Fields (per consensus spec):
      - slot: uint64
      - proposer_index: uint64
      - parent_root: Bytes32
      - state_root: Bytes32
      - body_root: Bytes32

    Total fixed size: 8 + 8 + 32 + 32 + 32 = 112 bytes.
    """

    slot: int = 0
    proposer_index: int = 0
    parent_root: bytes = field(default_factory=lambda: ZERO_HASH)
    state_root: bytes = field(default_factory=lambda: ZERO_HASH)
    body_root: bytes = field(default_factory=lambda: ZERO_HASH)

    # SSZ field schema (name, type, bits_or_len)
    _SCHEMA: list[tuple[str, SSZType]] = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        self._SCHEMA = [
            ("slot", SSZType.UINT64),
            ("proposer_index", SSZType.UINT64),
            ("parent_root", SSZType.BYTES32),
            ("state_root", SSZType.BYTES32),
            ("body_root", SSZType.BYTES32),
        ]
        # Accept hex strings for convenience and normalise to bytes
        for attr in ("parent_root", "state_root", "body_root"):
            v = getattr(self, attr)
            if isinstance(v, str):
                object.__setattr__(self, attr, bytes.fromhex(v.removeprefix("0x")))

    FIXED_SIZE = 112  # 8+8+32+32+32

    def serialize(self) -> bytes:
        """SSZ-encode this header (all fields are fixed-size)."""
        parts = [
            SSZ.encode_uint(self.slot, 64),
            SSZ.encode_uint(self.proposer_index, 64),
            SSZ.encode_bytes(self.parent_root, 32),
            SSZ.encode_bytes(self.state_root, 32),
            SSZ.encode_bytes(self.body_root, 32),
        ]
        return b"".join(parts)

    @classmethod
    def deserialize(cls, data: bytes) -> "BeaconBlockHeader":
        """Decode a 112-byte SSZ-encoded header."""
        if len(data) < cls.FIXED_SIZE:
            raise ValueError(
                f"BeaconBlockHeader needs {cls.FIXED_SIZE} bytes, "
                f"got {len(data)}"
            )
        slot = SSZ.decode_uint(data[0:8], 64)
        proposer_index = SSZ.decode_uint(data[8:16], 64)
        parent_root = data[16:48]
        state_root = data[48:80]
        body_root = data[80:112]
        return cls(
            slot=slot,
            proposer_index=proposer_index,
            parent_root=parent_root,
            state_root=state_root,
            body_root=body_root,
        )

    def hash_tree_root(self) -> bytes:
        """Compute the SSZ hash-tree-root for this header.

        Each field becomes a 32-byte leaf:
          - uint64 → little-endian padded to 32 bytes
          - bytes32 → used directly
        Then merkleize the 5 leaves (padded to 8).
        """
        field_roots = [
            SSZ.encode_uint(self.slot, 64).ljust(32, b"\x00"),
            SSZ.encode_uint(self.proposer_index, 64).ljust(32, b"\x00"),
            self.parent_root,
            self.state_root,
            self.body_root,
        ]
        return SSZ.hash_tree_root_container(field_roots)

    def signing_root(self) -> bytes:
        """Signing root for the header (same as hash_tree_root)."""
        return self.hash_tree_root()


# ---------------------------------------------------------------------------
# SyncCommitteeSSZ
# ---------------------------------------------------------------------------


@dataclass
class SyncCommitteeSSZ:
    """SSZ-typed sync committee (512 BLS pubkeys + aggregate key).

    Each pubkey is 48 bytes (BLS12-381 compressed G1 point).
    ``aggregate_pubkey`` is also 48 bytes.
    """

    pubkeys: list[bytes] = field(default_factory=list)
    aggregate_pubkey: bytes = field(
        default_factory=lambda: b"\x00" * 48
    )

    def hash_tree_root(self) -> bytes:
        """Hash-tree-root per the SyncCommittee container spec.

        Fields:
          1. pubkeys — Vector[BLSPubkey, 512].  Each pubkey is a
             48-byte basic object, hash_tree_root'd individually,
             then the 512 roots are merkleized.
          2. aggregate_pubkey — BLSPubkey (48 bytes → 2 chunks).

        Container root = merkleize([pubkeys_root, agg_root]).
        """
        # Each pubkey → pack into 2×32-byte chunks → merkleize
        pk_roots: list[bytes] = []
        for pk in self.pubkeys:
            chunks = SSZ.pack([pk], 48)
            pk_roots.append(SSZ.merkleize(chunks))

        # Pad to 512 if fewer provided (for partial committees)
        while len(pk_roots) < SYNC_COMMITTEE_SIZE:
            pk_roots.append(SSZ.merkleize([ZERO_HASH, ZERO_HASH]))

        pubkeys_root = SSZ.merkleize(pk_roots)

        # aggregate_pubkey: 48 bytes → 2 chunks
        agg_chunks = SSZ.pack([self.aggregate_pubkey], 48)
        agg_root = SSZ.merkleize(agg_chunks)

        return SSZ.hash_tree_root_container([pubkeys_root, agg_root])


# ---------------------------------------------------------------------------
# LightClientUpdate
# ---------------------------------------------------------------------------


@dataclass
class LightClientUpdate:
    """A light-client update message per the Altair spec.

    Contains everything a light client needs to advance its view of
    the beacon chain: attested + finalized headers, sync committee
    signature/participation bits, and optional next sync committee
    for period transitions.
    """

    attested_header: BeaconBlockHeader = field(
        default_factory=BeaconBlockHeader
    )
    sync_committee_bits: list[bool] = field(
        default_factory=lambda: [False] * SYNC_COMMITTEE_SIZE
    )
    sync_committee_signature: bytes = field(
        default_factory=lambda: b"\x00" * 96
    )
    finalized_header: BeaconBlockHeader = field(
        default_factory=BeaconBlockHeader
    )
    finality_branch: list[bytes] = field(default_factory=list)
    next_sync_committee: Optional[SyncCommitteeSSZ] = None
    next_sync_committee_branch: list[bytes] = field(
        default_factory=list
    )

    # -- helpers ------------------------------------------------------------

    def participant_count(self) -> int:
        """Number of sync committee members that participated."""
        return sum(self.sync_committee_bits)

    def has_supermajority(self) -> bool:
        """Whether ≥ 2/3 of the committee participated (≥ 342)."""
        return self.participant_count() >= 342

    # -- serialization ------------------------------------------------------

    def _encode_bitvector(self) -> bytes:
        """Encode sync_committee_bits as a packed bitvector (64 bytes)."""
        result = bytearray(64)  # 512 bits = 64 bytes
        for i, bit in enumerate(self.sync_committee_bits[:512]):
            if bit:
                result[i // 8] |= 1 << (i % 8)
        return bytes(result)

    @staticmethod
    def _decode_bitvector(data: bytes) -> list[bool]:
        """Decode a 64-byte bitvector into 512 bools."""
        bits: list[bool] = []
        for i in range(SYNC_COMMITTEE_SIZE):
            byte_idx = i // 8
            bit_idx = i % 8
            bits.append(bool(data[byte_idx] & (1 << bit_idx)))
        return bits

    def serialize(self) -> bytes:
        """SSZ-encode the light client update.

        Layout (all fixed-size fields first, then variable parts):
          - attested_header: 112 bytes (fixed)
          - sync_committee_bits: 64 bytes (fixed — Bitvector[512])
          - sync_committee_signature: 96 bytes (fixed)
          - finalized_header: 112 bytes (fixed)
          - offsets for: finality_branch, next_sync_committee,
            next_sync_committee_branch (variable)
        """
        fixed = bytearray()
        fixed.extend(self.attested_header.serialize())         # 112
        fixed.extend(self._encode_bitvector())                 # 64
        fixed.extend(
            SSZ.encode_bytes(self.sync_committee_signature, 96)  # 96
        )
        fixed.extend(self.finalized_header.serialize())        # 112

        # Variable parts: finality_branch, next_sync_committee,
        # next_sync_committee_branch
        var_parts: list[bytes] = []

        # finality_branch: list of bytes32
        fb = b"".join(self.finality_branch)
        var_parts.append(fb)

        # next_sync_committee (optional — encode empty if None)
        if self.next_sync_committee is not None:
            # Serialize as concatenated pubkeys + agg key
            sc_data = b"".join(self.next_sync_committee.pubkeys)
            sc_data += SSZ.encode_bytes(
                self.next_sync_committee.aggregate_pubkey, 48
            )
        else:
            sc_data = b""
        var_parts.append(sc_data)

        # next_sync_committee_branch
        nscb = b"".join(self.next_sync_committee_branch)
        var_parts.append(nscb)

        # 3 offset slots (4 bytes each) at end of fixed section
        num_offsets = 3
        offset_start = len(fixed) + num_offsets * 4
        offsets = bytearray()
        cur_offset = offset_start
        for vp in var_parts:
            offsets.extend(cur_offset.to_bytes(4, "little"))
            cur_offset += len(vp)

        return bytes(fixed) + bytes(offsets) + b"".join(var_parts)
