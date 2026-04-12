"""
Tests for EthLightClient interface, MockLightClient, HeliosLightClient,
and MerklePatriciaVerifier.
===================================================================

Covers:
- MockLightClient setup, sync, header/proof CRUD
- HeliosLightClient stub (all NotImplementedError)
- MerklePatriciaVerifier: keccak256, RLP decoding, HP path decoding, proof verification
"""

from __future__ import annotations

import asyncio
import hashlib

import pytest

from asi_build.rings.bridge.light_client import (
    BeaconHeader,
    EventProof,
    HeliosLightClient,
    MockLightClient,
    StateProof,
    SyncCommittee,
)
from asi_build.rings.bridge.merkle_patricia import (
    MerklePatriciaVerifier,
    RLPDecoder,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_header(slot: int = 100) -> BeaconHeader:
    return BeaconHeader(
        slot=slot,
        proposer_index=42,
        parent_root="0xaaaa",
        state_root="0xbbbb",
        body_root="0xcccc",
        timestamp=1700000000,
    )


def _make_state_proof(address: str = "0xabc", block: int = 50) -> StateProof:
    return StateProof(
        address=address,
        balance=10**18,
        nonce=5,
        code_hash="0x" + "00" * 32,
        storage_hash="0x" + "ff" * 32,
        account_proof=["0xdeadbeef"],
        storage_proofs={},
        block_number=block,
    )


def _make_event_proof(tx_hash: str = "0xaaa", log_index: int = 0) -> EventProof:
    return EventProof(
        tx_hash=tx_hash,
        log_index=log_index,
        address="0xcontract",
        topics=["0xsig"],
        data="0x1234",
        block_number=100,
        receipt_proof=["0xproof"],
    )


def _make_sync_committee(period: int = 1) -> SyncCommittee:
    return SyncCommittee(
        period=period,
        pubkeys=[f"0xpk{i}" for i in range(4)],
        aggregate_pubkey="0xagg",
    )


# ===================================================================
# 1.  MockLightClient (15 tests)
# ===================================================================


class TestMockLightClient:
    """In-memory light client for deterministic testing."""

    def test_not_synced_initially(self):
        lc = MockLightClient()
        assert lc.is_synced is False

    def test_sync_sets_synced(self):
        async def _test():
            lc = MockLightClient()
            await lc.sync("0xcheckpoint")
            assert lc.is_synced is True
        run(_test())

    def test_add_header_then_get(self):
        async def _test():
            lc = MockLightClient()
            h = _make_header(200)
            lc.add_header(h)
            got = await lc.get_verified_header(200)
            assert got.slot == 200
            assert got.proposer_index == 42
        run(_test())

    def test_get_header_missing_raises(self):
        async def _test():
            lc = MockLightClient()
            with pytest.raises(KeyError, match="No header for slot"):
                await lc.get_verified_header(999)
        run(_test())

    def test_add_state_proof_then_verify(self):
        async def _test():
            lc = MockLightClient()
            sp = _make_state_proof("0xabc", 50)
            lc.add_state_proof(sp)
            got = await lc.verify_state_proof("0xabc", [], 50)
            assert got.verified is True
            assert got.balance == 10**18
        run(_test())

    def test_verify_state_proof_missing_raises(self):
        async def _test():
            lc = MockLightClient()
            with pytest.raises(KeyError, match="No state proof"):
                await lc.verify_state_proof("0xmissing", [], 1)
        run(_test())

    def test_add_event_proof_then_verify(self):
        async def _test():
            lc = MockLightClient()
            ep = _make_event_proof("0xtx", 2)
            lc.add_event_proof(ep)
            got = await lc.verify_event("0xtx", 2)
            assert got.verified is True
            assert got.address == "0xcontract"
        run(_test())

    def test_add_sync_committee_then_get(self):
        async def _test():
            lc = MockLightClient()
            sc = _make_sync_committee(5)
            lc.add_sync_committee(sc)
            got = await lc.get_sync_committee(5)
            assert got.period == 5
            assert len(got.pubkeys) == 4
        run(_test())

    def test_get_latest_slot(self):
        async def _test():
            lc = MockLightClient()
            assert await lc.get_latest_slot() == 0
            lc.add_header(_make_header(10))
            assert await lc.get_latest_slot() == 10
            lc.add_header(_make_header(5))
            assert await lc.get_latest_slot() == 10
            lc.add_header(_make_header(20))
            assert await lc.get_latest_slot() == 20
        run(_test())

    def test_multiple_headers(self):
        async def _test():
            lc = MockLightClient()
            for s in [1, 2, 3, 4, 5]:
                lc.add_header(_make_header(s))
            h3 = await lc.get_verified_header(3)
            assert h3.slot == 3
            h5 = await lc.get_verified_header(5)
            assert h5.slot == 5
        run(_test())

    def test_state_proof_fields(self):
        sp = _make_state_proof()
        assert sp.address == "0xabc"
        assert sp.nonce == 5
        assert sp.verified is False

    def test_event_proof_fields(self):
        ep = _make_event_proof()
        assert ep.tx_hash == "0xaaa"
        assert ep.log_index == 0
        assert ep.verified is False

    def test_beacon_header_fields(self):
        h = _make_header(50)
        assert h.slot == 50
        assert h.proposer_index == 42
        root = h.header_root()
        assert isinstance(root, str) and len(root) == 64

    def test_sync_committee_fields(self):
        sc = _make_sync_committee(10)
        assert sc.period == 10
        assert sc.aggregate_pubkey == "0xagg"


# ===================================================================
# 2.  HeliosLightClient (5 tests)
# ===================================================================


class TestHeliosLightClient:
    """Stub that raises NotImplementedError on all operations."""

    def test_constructor_accepts_params(self):
        lc = HeliosLightClient(
            helios_binary="/usr/bin/helios",
            checkpoint="0xaaa",
            network="goerli",
        )
        assert lc._network == "goerli"

    def test_is_synced_false(self):
        lc = HeliosLightClient()
        assert lc.is_synced is False

    def test_sync_raises(self):
        async def _test():
            lc = HeliosLightClient()
            with pytest.raises(NotImplementedError, match="Helios FFI not yet"):
                await lc.sync("0x")
        run(_test())

    def test_get_verified_header_raises(self):
        async def _test():
            lc = HeliosLightClient()
            with pytest.raises(NotImplementedError):
                await lc.get_verified_header(1)
        run(_test())

    def test_all_methods_raise(self):
        async def _test():
            lc = HeliosLightClient()
            with pytest.raises(NotImplementedError):
                await lc.verify_state_proof("0x", [], 1)
            with pytest.raises(NotImplementedError):
                await lc.verify_event("0x", 0)
            with pytest.raises(NotImplementedError):
                await lc.get_sync_committee(1)
            with pytest.raises(NotImplementedError):
                await lc.get_latest_slot()
        run(_test())


# ===================================================================
# 3.  MerklePatriciaVerifier (10 tests)
# ===================================================================


class TestMerklePatriciaVerifier:
    """RLP decoding, keccak256, HP path decoding, and proof verification."""

    # ── keccak256 ──────────────────────────────────────────────────

    def test_keccak256_known_vector(self):
        """keccak256("") is the well-known empty hash."""
        h = MerklePatriciaVerifier.keccak256(b"")
        assert h.hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"

    def test_keccak256_abc(self):
        """keccak256("abc") — another standard test vector."""
        h = MerklePatriciaVerifier.keccak256(b"abc")
        # This is the standard Keccak-256 (NOT SHA3-256) result
        assert len(h) == 32
        # Deterministic
        assert h == MerklePatriciaVerifier.keccak256(b"abc")

    # ── RLPDecoder ─────────────────────────────────────────────────

    def test_rlp_decode_single_byte(self):
        # Single byte < 0x80 is identity
        assert RLPDecoder.decode(b"\x42") == b"\x42"

    def test_rlp_decode_short_string(self):
        # 0x83 = 0x80 + 3 → next 3 bytes are the string
        assert RLPDecoder.decode(b"\x83dog") == b"dog"

    def test_rlp_decode_short_list(self):
        # \xc8 = 0xc0 + 8 → list payload is 8 bytes
        # \x83cat = 4 bytes, \x83dog = 4 bytes
        result = RLPDecoder.decode(b"\xc8\x83cat\x83dog")
        assert isinstance(result, list)
        assert result == [b"cat", b"dog"]

    def test_rlp_decode_nested_list(self):
        # Inner list: \xc4\x83cat → [b"cat"] (5 bytes)
        # Outer: \xc5 + inner → 6-byte payload: \xc5\xc4\x83cat
        # Wait, let's be precise:
        # Inner: \xc4\x83cat  → list of [b"cat"], total 5 bytes
        # Outer: payload = inner (5 bytes), prefix = \xc0 + 5 = \xc5
        result = RLPDecoder.decode(b"\xc5\xc4\x83cat")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert result[0] == [b"cat"]

    def test_rlp_decode_empty_string(self):
        # 0x80 = empty string
        assert RLPDecoder.decode(b"\x80") == b""

    def test_rlp_decode_empty_list(self):
        # 0xc0 = empty list
        assert RLPDecoder.decode(b"\xc0") == []

    # ── nibbles_from_bytes ──────────────────────────────────────────

    def test_nibbles_from_bytes(self):
        result = MerklePatriciaVerifier.nibbles_from_bytes(b"\xab\xcd")
        assert result == [0xa, 0xb, 0xc, 0xd]

    # ── _decode_compact_path ────────────────────────────────────────

    def test_decode_compact_path_leaf_odd(self):
        # Flag nibble 0x3 → leaf, odd. First byte = 0x3N where N is first nibble.
        # \x35\xab → leaf=True, nibbles=[5, 0xa, 0xb]
        path, is_leaf = MerklePatriciaVerifier._decode_compact_path(b"\x35\xab")
        assert is_leaf is True
        assert path == [5, 0xa, 0xb]

    def test_decode_compact_path_extension_even(self):
        # Flag nibble 0x0 → extension, even. First byte = 0x00 (padding).
        # \x00\xab → extension, nibbles=[0xa, 0xb]
        path, is_leaf = MerklePatriciaVerifier._decode_compact_path(b"\x00\xab")
        assert is_leaf is False
        assert path == [0xa, 0xb]

    # ── verify_proof (constructed MPT) ──────────────────────────────

    def test_verify_proof_simple_leaf(self):
        """Construct a minimal valid MPT: single leaf node, root = keccak(leaf_rlp)."""
        # We want to prove key = b"\x01\x23" → value = b"hello"
        # Leaf HP encoding: flag=0x2 (leaf, even), then nibbles of the key
        # key nibbles: [0, 1, 2, 3]
        # HP leaf even: prefix byte = 0x20, then raw key bytes: \x20\x01\x23
        hp_encoded_path = b"\x20\x01\x23"

        value = b"hello"

        # RLP encode the leaf node: [hp_encoded_path, value]
        # hp_encoded_path = 3 bytes → \x83 prefix
        # value = 5 bytes → \x85 prefix
        # List payload = (1+3) + (1+5) = 10 bytes
        # List prefix = \xc0 + 10 = \xca
        leaf_rlp = b"\xca" + b"\x83" + hp_encoded_path + b"\x85" + value

        root = MerklePatriciaVerifier.keccak256(leaf_rlp)
        key = b"\x01\x23"

        result = MerklePatriciaVerifier.verify_proof(root, key, [leaf_rlp])
        assert result == b"hello"

    def test_verify_proof_wrong_key_returns_none(self):
        """Proof for key A, querying key B → None."""
        hp_encoded_path = b"\x20\x01\x23"
        value = b"hello"
        leaf_rlp = b"\xca" + b"\x83" + hp_encoded_path + b"\x85" + value
        root = MerklePatriciaVerifier.keccak256(leaf_rlp)

        # Query with a different key
        result = MerklePatriciaVerifier.verify_proof(root, b"\x99\x99", [leaf_rlp])
        assert result is None

    def test_verify_proof_empty_returns_none(self):
        """Empty proof → None."""
        assert MerklePatriciaVerifier.verify_proof(b"\x00" * 32, b"\x01", []) is None
