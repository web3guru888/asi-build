"""
Tests for SSZ (Simple Serialize) Implementation
=================================================

Comprehensive tests for the SSZ encoding, decoding, Merkleization, and
beacon chain types defined in ``rings.bridge.zk.ssz``.
"""

from __future__ import annotations

import hashlib
import os
import struct

import pytest

from src.asi_build.rings.bridge.zk.ssz import (
    SSZ,
    SSZType,
    BeaconBlockHeader,
    LightClientUpdate,
    SyncCommitteeSSZ,
    ZERO_HASH,
    BYTES_PER_CHUNK,
    SYNC_COMMITTEE_SIZE,
    _next_power_of_two,
    _sha256,
)


# ---------------------------------------------------------------------------
# SSZ encode / decode tests
# ---------------------------------------------------------------------------


class TestSSZEncodeDecode:
    """Tests for SSZ encoding and decoding primitives."""

    def test_encode_uint8(self):
        assert SSZ.encode_uint(255, 8) == b"\xff"
        assert SSZ.encode_uint(0, 8) == b"\x00"

    def test_encode_uint16(self):
        # 0x0102 → little-endian → 0x02, 0x01
        assert SSZ.encode_uint(0x0102, 16) == b"\x02\x01"

    def test_encode_uint32_roundtrip(self):
        val = 0xDEADBEEF
        encoded = SSZ.encode_uint(val, 32)
        assert len(encoded) == 4
        decoded = SSZ.decode_uint(encoded, 32)
        assert decoded == val

    def test_encode_uint64_roundtrip(self):
        val = 2**63 - 1
        encoded = SSZ.encode_uint(val, 64)
        assert len(encoded) == 8
        decoded = SSZ.decode_uint(encoded, 64)
        assert decoded == val

    def test_encode_uint128_roundtrip(self):
        val = 2**100 + 42
        encoded = SSZ.encode_uint(val, 128)
        assert len(encoded) == 16
        decoded = SSZ.decode_uint(encoded, 128)
        assert decoded == val

    def test_encode_uint256_roundtrip(self):
        val = 2**255 - 1
        encoded = SSZ.encode_uint(val, 256)
        assert len(encoded) == 32
        decoded = SSZ.decode_uint(encoded, 256)
        assert decoded == val

    def test_encode_uint_overflow(self):
        with pytest.raises(ValueError, match="out of range"):
            SSZ.encode_uint(256, 8)  # 256 doesn't fit in uint8

    def test_encode_uint_max_boundary(self):
        # Exact max value should work
        SSZ.encode_uint(255, 8)
        SSZ.encode_uint(65535, 16)
        # One above max should fail
        with pytest.raises(ValueError):
            SSZ.encode_uint(65536, 16)

    def test_encode_uint_negative(self):
        with pytest.raises(ValueError, match="out of range"):
            SSZ.encode_uint(-1, 8)

    def test_encode_uint_invalid_bits(self):
        with pytest.raises(ValueError, match="Unsupported uint width"):
            SSZ.encode_uint(42, 12)

    def test_decode_uint_roundtrip_all_sizes(self):
        for bits in (8, 16, 32, 64, 128, 256):
            val = (1 << bits) - 1  # max value
            encoded = SSZ.encode_uint(val, bits)
            decoded = SSZ.decode_uint(encoded, bits)
            assert decoded == val, f"Failed for uint{bits}"

    def test_decode_uint_short_data(self):
        with pytest.raises(ValueError, match="Need"):
            SSZ.decode_uint(b"\x00", 32)  # need 4 bytes, got 1

    def test_encode_bool_true(self):
        assert SSZ.encode_bool(True) == b"\x01"

    def test_encode_bool_false(self):
        assert SSZ.encode_bool(False) == b"\x00"

    def test_decode_bool_roundtrip(self):
        assert SSZ.decode_bool(SSZ.encode_bool(True)) is True
        assert SSZ.decode_bool(SSZ.encode_bool(False)) is False

    def test_decode_bool_invalid(self):
        with pytest.raises(ValueError, match="Invalid bool byte"):
            SSZ.decode_bool(b"\x02")

    def test_decode_bool_empty(self):
        with pytest.raises(ValueError, match="Empty data"):
            SSZ.decode_bool(b"")

    def test_encode_bytes_fixed(self):
        data = b"\xaa\xbb"
        encoded = SSZ.encode_bytes(data, fixed_length=4)
        assert len(encoded) == 4
        assert encoded[:2] == data
        assert encoded[2:] == b"\x00\x00"

    def test_encode_bytes_fixed_too_long(self):
        with pytest.raises(ValueError, match="exceeds fixed_length"):
            SSZ.encode_bytes(b"\x00" * 5, fixed_length=4)

    def test_encode_bytes_variable(self):
        data = b"\xaa\xbb\xcc"
        encoded = SSZ.encode_bytes(data)  # no fixed_length
        assert encoded == data

    def test_encode_container_simple(self):
        """Container with 2 fixed-size fields."""
        fields = [
            ("slot", SSZ.encode_uint(100, 64), True),
            ("index", SSZ.encode_uint(7, 64), True),
        ]
        encoded = SSZ.encode_container(fields)
        assert len(encoded) == 16
        assert SSZ.decode_uint(encoded[:8], 64) == 100
        assert SSZ.decode_uint(encoded[8:16], 64) == 7

    def test_encode_container_with_variable(self):
        """Container with fixed + variable fields."""
        var_data = b"\xde\xad\xbe\xef"
        fields = [
            ("slot", SSZ.encode_uint(42, 64), True),
            ("data", var_data, False),
        ]
        encoded = SSZ.encode_container(fields)
        # Fixed part: 8 (uint64) + 4 (offset) = 12 bytes
        # Variable part: 4 bytes
        assert len(encoded) == 16
        # The offset at position 8-12 should point to byte 12
        offset = int.from_bytes(encoded[8:12], "little")
        assert offset == 12
        assert encoded[12:] == var_data

    def test_encode_uint_zero(self):
        for bits in (8, 16, 32, 64, 128, 256):
            encoded = SSZ.encode_uint(0, bits)
            assert all(b == 0 for b in encoded)
            assert SSZ.decode_uint(encoded, bits) == 0


# ---------------------------------------------------------------------------
# Merkleization tests
# ---------------------------------------------------------------------------


class TestMerkleization:
    """Tests for SSZ Merkleization (hash-tree-root computation)."""

    def test_merkleize_single_chunk(self):
        chunk = os.urandom(32)
        root = SSZ.merkleize([chunk])
        assert root == chunk

    def test_merkleize_two_chunks(self):
        c1 = os.urandom(32)
        c2 = os.urandom(32)
        root = SSZ.merkleize([c1, c2])
        expected = _sha256(c1, c2)
        assert root == expected

    def test_merkleize_four_chunks(self):
        c = [os.urandom(32) for _ in range(4)]
        root = SSZ.merkleize(c)
        h01 = _sha256(c[0], c[1])
        h23 = _sha256(c[2], c[3])
        expected = _sha256(h01, h23)
        assert root == expected

    def test_merkleize_non_power_of_2(self):
        """3 chunks → padded to 4 with ZERO_HASH."""
        c = [os.urandom(32) for _ in range(3)]
        root = SSZ.merkleize(c)
        # Manual: pad to 4
        h01 = _sha256(c[0], c[1])
        h2z = _sha256(c[2], ZERO_HASH)
        expected = _sha256(h01, h2z)
        assert root == expected

    def test_merkleize_empty(self):
        """Empty list → ZERO_HASH (single zero leaf)."""
        root = SSZ.merkleize([])
        assert root == ZERO_HASH

    def test_merkleize_with_limit(self):
        """limit > len → pads to next_power_of_two(limit)."""
        chunk = os.urandom(32)
        # limit=4 → 4 leaves (1 real + 3 zero)
        root = SSZ.merkleize([chunk], limit=4)
        # Manual: 4 leaves
        h0z = _sha256(chunk, ZERO_HASH)
        hzz = _sha256(ZERO_HASH, ZERO_HASH)
        expected = _sha256(h0z, hzz)
        assert root == expected

    def test_hash_tree_root_basic_uint64(self):
        val = 42
        root = SSZ.hash_tree_root_basic(val, 64)
        encoded = SSZ.encode_uint(val, 64).ljust(32, b"\x00")
        expected = SSZ.merkleize([encoded])
        assert root == expected

    def test_hash_tree_root_bytes_variable(self):
        data = b"hello world"
        root = SSZ.hash_tree_root_bytes(data)
        # Should be mix_in_length(merkleize(pack(data)), len(data))
        chunks = SSZ.pack([data], 1)
        inner = SSZ.merkleize(chunks)
        expected = SSZ.mix_in_length(inner, len(data))
        assert root == expected

    def test_hash_tree_root_container(self):
        r1 = os.urandom(32)
        r2 = os.urandom(32)
        root = SSZ.hash_tree_root_container([r1, r2])
        expected = SSZ.merkleize([r1, r2])
        assert root == expected

    def test_mix_in_length(self):
        root = os.urandom(32)
        length = 42
        result = SSZ.mix_in_length(root, length)
        length_bytes = length.to_bytes(32, "little")
        expected = _sha256(root, length_bytes)
        assert result == expected

    def test_pack_elements(self):
        """Pack small elements into 32-byte chunks."""
        # 4 uint64 values → 32 bytes total → 1 chunk
        values = [SSZ.encode_uint(i, 64) for i in range(4)]
        chunks = SSZ.pack(values, 8)
        assert len(chunks) == 1
        assert len(chunks[0]) == 32

    def test_pack_larger_than_one_chunk(self):
        """Pack enough elements to need multiple chunks."""
        values = [SSZ.encode_uint(i, 64) for i in range(8)]  # 64 bytes → 2 chunks
        chunks = SSZ.pack(values, 8)
        assert len(chunks) == 2

    def test_pack_empty(self):
        chunks = SSZ.pack([], 1)
        assert chunks == [ZERO_HASH]

    def test_merkleize_deterministic(self):
        """Same input → same root."""
        c = [b"\xaa" * 32, b"\xbb" * 32]
        r1 = SSZ.merkleize(c)
        r2 = SSZ.merkleize(c)
        assert r1 == r2

    def test_next_power_of_two(self):
        assert _next_power_of_two(0) == 1
        assert _next_power_of_two(1) == 1
        assert _next_power_of_two(2) == 2
        assert _next_power_of_two(3) == 4
        assert _next_power_of_two(5) == 8
        assert _next_power_of_two(8) == 8
        assert _next_power_of_two(9) == 16


# ---------------------------------------------------------------------------
# BeaconBlockHeader tests
# ---------------------------------------------------------------------------


class TestBeaconBlockHeader:
    """Tests for BeaconBlockHeader SSZ container."""

    def test_creation(self):
        h = BeaconBlockHeader(
            slot=100, proposer_index=7,
            parent_root=b"\xaa" * 32,
            state_root=b"\xbb" * 32,
            body_root=b"\xcc" * 32,
        )
        assert h.slot == 100
        assert h.proposer_index == 7
        assert h.parent_root == b"\xaa" * 32

    def test_creation_from_hex_strings(self):
        hex_root = "aa" * 32
        h = BeaconBlockHeader(parent_root=hex_root)
        assert h.parent_root == b"\xaa" * 32

    def test_creation_from_0x_hex_strings(self):
        hex_root = "0x" + "bb" * 32
        h = BeaconBlockHeader(state_root=hex_root)
        assert h.state_root == b"\xbb" * 32

    def test_serialize(self):
        h = BeaconBlockHeader(
            slot=1, proposer_index=2,
            parent_root=b"\x01" * 32,
            state_root=b"\x02" * 32,
            body_root=b"\x03" * 32,
        )
        serialized = h.serialize()
        assert len(serialized) == 112

    def test_deserialize_roundtrip(self):
        h = BeaconBlockHeader(
            slot=9999, proposer_index=42,
            parent_root=os.urandom(32),
            state_root=os.urandom(32),
            body_root=os.urandom(32),
        )
        data = h.serialize()
        h2 = BeaconBlockHeader.deserialize(data)
        assert h2.slot == h.slot
        assert h2.proposer_index == h.proposer_index
        assert h2.parent_root == h.parent_root
        assert h2.state_root == h.state_root
        assert h2.body_root == h.body_root

    def test_hash_tree_root_deterministic(self):
        h = BeaconBlockHeader(
            slot=100, proposer_index=7,
            parent_root=b"\xaa" * 32,
            state_root=b"\xbb" * 32,
            body_root=b"\xcc" * 32,
        )
        r1 = h.hash_tree_root()
        r2 = h.hash_tree_root()
        assert r1 == r2
        assert len(r1) == 32

    def test_hash_tree_root_changes_with_slot(self):
        h1 = BeaconBlockHeader(slot=1)
        h2 = BeaconBlockHeader(slot=2)
        assert h1.hash_tree_root() != h2.hash_tree_root()

    def test_hash_tree_root_changes_with_state_root(self):
        h1 = BeaconBlockHeader(state_root=b"\x01" * 32)
        h2 = BeaconBlockHeader(state_root=b"\x02" * 32)
        assert h1.hash_tree_root() != h2.hash_tree_root()

    def test_signing_root_equals_hash_tree_root(self):
        h = BeaconBlockHeader(slot=42, proposer_index=7)
        assert h.signing_root() == h.hash_tree_root()

    def test_serialize_fixed_size(self):
        """Every header serializes to exactly 112 bytes."""
        for _ in range(5):
            h = BeaconBlockHeader(
                slot=os.urandom(1)[0],
                proposer_index=os.urandom(1)[0],
                parent_root=os.urandom(32),
                state_root=os.urandom(32),
                body_root=os.urandom(32),
            )
            assert len(h.serialize()) == BeaconBlockHeader.FIXED_SIZE == 112

    def test_known_zero_header(self):
        """All-zero header has a deterministic root."""
        h = BeaconBlockHeader()
        root = h.hash_tree_root()
        assert root == h.hash_tree_root()
        assert len(root) == 32
        # Root should NOT be all zeros (it's a hash of 5 zero leaves)
        assert root != ZERO_HASH

    def test_deserialize_short_data_raises(self):
        with pytest.raises(ValueError, match="needs 112 bytes"):
            BeaconBlockHeader.deserialize(b"\x00" * 100)

    def test_hash_tree_root_manual(self):
        """Manually compute expected hash-tree-root and compare."""
        h = BeaconBlockHeader(
            slot=100, proposer_index=7,
            parent_root=b"\xaa" * 32,
            state_root=b"\xbb" * 32,
            body_root=b"\xcc" * 32,
        )
        # 5 field roots, padded to 8 leaves
        leaves = [
            SSZ.encode_uint(100, 64).ljust(32, b"\x00"),
            SSZ.encode_uint(7, 64).ljust(32, b"\x00"),
            b"\xaa" * 32,
            b"\xbb" * 32,
            b"\xcc" * 32,
        ]
        expected = SSZ.merkleize(leaves)
        assert h.hash_tree_root() == expected


# ---------------------------------------------------------------------------
# LightClientUpdate tests
# ---------------------------------------------------------------------------


class TestLightClientUpdate:
    """Tests for LightClientUpdate."""

    def test_creation_defaults(self):
        lcu = LightClientUpdate()
        assert lcu.participant_count() == 0
        assert lcu.has_supermajority() is False

    def test_participant_count(self):
        bits = [True] * 400 + [False] * 112
        lcu = LightClientUpdate(sync_committee_bits=bits)
        assert lcu.participant_count() == 400

    def test_has_supermajority_true(self):
        bits = [True] * 400 + [False] * 112
        lcu = LightClientUpdate(sync_committee_bits=bits)
        assert lcu.has_supermajority() is True

    def test_has_supermajority_false(self):
        bits = [True] * 300 + [False] * 212
        lcu = LightClientUpdate(sync_committee_bits=bits)
        assert lcu.has_supermajority() is False

    def test_has_supermajority_exact_boundary(self):
        """342 participants → exactly at threshold → True."""
        bits = [True] * 342 + [False] * 170
        lcu = LightClientUpdate(sync_committee_bits=bits)
        assert lcu.participant_count() == 342
        assert lcu.has_supermajority() is True

    def test_has_supermajority_one_below(self):
        """341 participants → below threshold → False."""
        bits = [True] * 341 + [False] * 171
        lcu = LightClientUpdate(sync_committee_bits=bits)
        assert lcu.has_supermajority() is False

    def test_serialize_produces_bytes(self):
        lcu = LightClientUpdate()
        data = lcu.serialize()
        assert isinstance(data, bytes)
        # Minimum size: 112 + 64 + 96 + 112 + 3*4 = 396 bytes
        assert len(data) >= 396

    def test_serialize_with_next_committee(self):
        pubkeys = [os.urandom(48) for _ in range(10)]
        sc = SyncCommitteeSSZ(
            pubkeys=pubkeys, aggregate_pubkey=os.urandom(48),
        )
        lcu = LightClientUpdate(next_sync_committee=sc)
        data = lcu.serialize()
        # Should be longer than without committee
        base_lcu = LightClientUpdate()
        base_data = base_lcu.serialize()
        assert len(data) > len(base_data)

    def test_serialize_without_next_committee(self):
        lcu = LightClientUpdate(next_sync_committee=None)
        data = lcu.serialize()
        assert isinstance(data, bytes)

    def test_bitvector_encoding_roundtrip(self):
        """Encode then decode bitvector preserves bits."""
        bits = [i % 3 == 0 for i in range(512)]
        lcu = LightClientUpdate(sync_committee_bits=bits)
        encoded = lcu._encode_bitvector()
        assert len(encoded) == 64  # 512 / 8
        decoded = LightClientUpdate._decode_bitvector(encoded)
        assert decoded == bits

    def test_serialize_with_finality_branch(self):
        branch = [os.urandom(32) for _ in range(6)]
        lcu = LightClientUpdate(finality_branch=branch)
        data = lcu.serialize()
        assert len(data) > 396 + 6 * 32 - 10  # approximate check

    def test_attested_header_included(self):
        h = BeaconBlockHeader(slot=999, proposer_index=42)
        lcu = LightClientUpdate(attested_header=h)
        data = lcu.serialize()
        # First 8 bytes should be slot=999 in little-endian
        assert SSZ.decode_uint(data[:8], 64) == 999


# ---------------------------------------------------------------------------
# SyncCommitteeSSZ tests
# ---------------------------------------------------------------------------


class TestSyncCommitteeSSZ:
    """Tests for SyncCommitteeSSZ."""

    def test_creation(self):
        pubkeys = [os.urandom(48) for _ in range(512)]
        agg = os.urandom(48)
        sc = SyncCommitteeSSZ(pubkeys=pubkeys, aggregate_pubkey=agg)
        assert len(sc.pubkeys) == 512
        assert sc.aggregate_pubkey == agg

    def test_hash_tree_root_deterministic(self):
        pubkeys = [b"\x01" * 48 for _ in range(512)]
        agg = b"\x02" * 48
        sc = SyncCommitteeSSZ(pubkeys=pubkeys, aggregate_pubkey=agg)
        r1 = sc.hash_tree_root()
        r2 = sc.hash_tree_root()
        assert r1 == r2
        assert len(r1) == 32

    def test_hash_tree_root_different_committees(self):
        sc1 = SyncCommitteeSSZ(
            pubkeys=[b"\x01" * 48] * 512,
            aggregate_pubkey=b"\x01" * 48,
        )
        sc2 = SyncCommitteeSSZ(
            pubkeys=[b"\x02" * 48] * 512,
            aggregate_pubkey=b"\x02" * 48,
        )
        assert sc1.hash_tree_root() != sc2.hash_tree_root()

    def test_pubkey_count_stored(self):
        pubkeys = [os.urandom(48) for _ in range(512)]
        sc = SyncCommitteeSSZ(pubkeys=pubkeys)
        assert len(sc.pubkeys) == 512

    def test_aggregate_stored(self):
        agg = os.urandom(48)
        sc = SyncCommitteeSSZ(aggregate_pubkey=agg)
        assert sc.aggregate_pubkey == agg

    def test_partial_committee_padded(self):
        """Fewer than 512 pubkeys → padded with zero roots in hash_tree_root."""
        pubkeys = [os.urandom(48) for _ in range(10)]
        sc = SyncCommitteeSSZ(pubkeys=pubkeys, aggregate_pubkey=os.urandom(48))
        root = sc.hash_tree_root()
        assert len(root) == 32  # should not crash

    def test_empty_committee(self):
        sc = SyncCommitteeSSZ()
        root = sc.hash_tree_root()
        assert len(root) == 32

    def test_default_aggregate_is_zeros(self):
        sc = SyncCommitteeSSZ()
        assert sc.aggregate_pubkey == b"\x00" * 48


# ---------------------------------------------------------------------------
# SSZType enum tests
# ---------------------------------------------------------------------------


class TestSSZType:
    """Tests for SSZType enum."""

    def test_all_types_exist(self):
        expected = [
            "UINT8", "UINT16", "UINT32", "UINT64", "UINT128", "UINT256",
            "BOOL", "BYTES4", "BYTES32", "BYTES48", "BYTES96",
        ]
        for name in expected:
            assert hasattr(SSZType, name)

    def test_type_values_unique(self):
        values = [t.value for t in SSZType]
        assert len(values) == len(set(values))
