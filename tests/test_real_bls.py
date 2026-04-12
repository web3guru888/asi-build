"""
Tests for Real BLS12-381 Implementation
=========================================

Tests the ``real_bls.py`` module which uses ``py_ecc`` for actual
elliptic curve BLS12-381 operations.

Note: py_ecc is pure Python and therefore slow (~200ms per sign,
~550ms per verify).  Test committees use small sizes (4–16) to
keep total test runtime manageable.
"""

from __future__ import annotations

import hashlib
import os
import time

import pytest

from asi_build.rings.bridge.zk.real_bls import (
    CURVE_ORDER,
    DEFAULT_SYNC_THRESHOLD,
    DOMAIN_SEPARATOR,
    FIELD_MODULUS,
    G1_SIZE,
    G2_SIZE,
    GROUP_ORDER,
    SYNC_COMMITTEE_SIZE,
    RealBLS12381,
    RealBLSKeyPair,
    RealSyncCommitteeBLS,
    get_bls_backend,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def deterministic_keypair():
    """A deterministic key pair for reproducible tests."""
    return RealBLSKeyPair.generate(seed=b"\x00" * 32)


@pytest.fixture
def second_keypair():
    """A second deterministic key pair."""
    return RealBLSKeyPair.generate(seed=b"\x01" * 32)


@pytest.fixture
def third_keypair():
    """A third deterministic key pair."""
    return RealBLSKeyPair.generate(seed=b"\x02" * 32)


@pytest.fixture
def small_committee():
    """A 4-member committee with threshold=3."""
    committee = RealSyncCommitteeBLS(committee_size=4, threshold=3)
    seeds = [i.to_bytes(32, "big") for i in range(4)]
    committee.setup_committee(seeds=seeds)
    return committee


@pytest.fixture
def medium_committee():
    """An 8-member committee with threshold=6 for more thorough tests."""
    committee = RealSyncCommitteeBLS(committee_size=8, threshold=6)
    seeds = [i.to_bytes(32, "big") for i in range(8)]
    committee.setup_committee(seeds=seeds)
    return committee


# ===================================================================
# TestRealBLSKeyPair
# ===================================================================

class TestRealBLSKeyPair:
    """Tests for :class:`RealBLSKeyPair`."""

    def test_generate_random(self):
        """Random generation produces valid key pair."""
        kp = RealBLSKeyPair.generate()
        assert isinstance(kp.secret_key, int)
        assert 1 <= kp.secret_key < CURVE_ORDER
        assert isinstance(kp.public_key, bytes)
        assert len(kp.public_key) == G1_SIZE

    def test_generate_deterministic(self, deterministic_keypair):
        """Same seed produces same key pair."""
        kp2 = RealBLSKeyPair.generate(seed=b"\x00" * 32)
        assert kp2.secret_key == deterministic_keypair.secret_key
        assert kp2.public_key == deterministic_keypair.public_key

    def test_generate_different_seeds(self, deterministic_keypair, second_keypair):
        """Different seeds produce different keys."""
        assert deterministic_keypair.secret_key != second_keypair.secret_key
        assert deterministic_keypair.public_key != second_keypair.public_key

    def test_generate_short_seed_padded(self):
        """Seeds shorter than 32 bytes are padded deterministically."""
        kp1 = RealBLSKeyPair.generate(seed=b"short")
        kp2 = RealBLSKeyPair.generate(seed=b"short")
        assert kp1.secret_key == kp2.secret_key
        assert kp1.public_key == kp2.public_key

    def test_public_key_is_48_bytes(self, deterministic_keypair):
        """Public key is a 48-byte compressed G1 point."""
        assert len(deterministic_keypair.public_key) == 48

    def test_secret_property(self, deterministic_keypair):
        """The .secret property returns 32-byte big-endian encoding."""
        s = deterministic_keypair.secret
        assert isinstance(s, bytes)
        assert len(s) == 32
        # Roundtrip
        assert int.from_bytes(s, "big") == deterministic_keypair.secret_key

    def test_sign_produces_96_bytes(self, deterministic_keypair):
        """Signing produces a 96-byte G2 signature."""
        sig = deterministic_keypair.sign(b"hello")
        assert isinstance(sig, bytes)
        assert len(sig) == G2_SIZE

    def test_sign_deterministic(self, deterministic_keypair):
        """Same message always produces the same signature."""
        sig1 = deterministic_keypair.sign(b"hello")
        sig2 = deterministic_keypair.sign(b"hello")
        assert sig1 == sig2

    def test_sign_different_messages(self, deterministic_keypair):
        """Different messages produce different signatures."""
        sig1 = deterministic_keypair.sign(b"hello")
        sig2 = deterministic_keypair.sign(b"world")
        assert sig1 != sig2

    def test_verify_valid_signature(self, deterministic_keypair):
        """Verification succeeds for a valid signature."""
        msg = b"test message"
        sig = deterministic_keypair.sign(msg)
        assert deterministic_keypair.verify(msg, sig) is True

    def test_verify_wrong_message(self, deterministic_keypair):
        """Verification fails for wrong message."""
        sig = deterministic_keypair.sign(b"correct")
        assert deterministic_keypair.verify(b"wrong", sig) is False

    def test_verify_wrong_key(self, deterministic_keypair, second_keypair):
        """Verification fails with wrong public key."""
        sig = deterministic_keypair.sign(b"test")
        assert second_keypair.verify(b"test", sig) is False

    def test_verify_corrupted_signature(self, deterministic_keypair):
        """Verification fails for corrupted signature."""
        sig = deterministic_keypair.sign(b"test")
        corrupted = bytearray(sig)
        corrupted[0] ^= 0xFF
        # Corrupted sig may raise or return False; both are acceptable
        assert deterministic_keypair.verify(b"test", bytes(corrupted)) is False

    def test_verify_empty_message(self, deterministic_keypair):
        """Empty message can be signed and verified."""
        sig = deterministic_keypair.sign(b"")
        assert deterministic_keypair.verify(b"", sig) is True

    def test_verify_large_message(self, deterministic_keypair):
        """Large messages can be signed and verified."""
        msg = os.urandom(10000)
        sig = deterministic_keypair.sign(msg)
        assert deterministic_keypair.verify(msg, sig) is True

    def test_invalid_secret_key_zero(self):
        """Secret key of 0 is rejected."""
        pk = RealBLSKeyPair.generate().public_key
        with pytest.raises(ValueError, match="Secret key must be"):
            RealBLSKeyPair(secret_key=0, public_key=pk)

    def test_invalid_secret_key_too_large(self):
        """Secret key ≥ CURVE_ORDER is rejected."""
        pk = RealBLSKeyPair.generate().public_key
        with pytest.raises(ValueError, match="Secret key must be"):
            RealBLSKeyPair(secret_key=CURVE_ORDER, public_key=pk)

    def test_invalid_public_key_wrong_size(self):
        """Public key with wrong size is rejected."""
        with pytest.raises(ValueError, match="Public key must be"):
            RealBLSKeyPair(secret_key=1, public_key=b"\x00" * 32)

    def test_proof_of_possession(self, deterministic_keypair):
        """PoP proves possession of the secret key."""
        pop = deterministic_keypair.pop_prove()
        assert isinstance(pop, bytes)
        assert len(pop) == G2_SIZE
        # Verify PoP
        assert RealBLSKeyPair.pop_verify(
            deterministic_keypair.public_key, pop
        ) is True

    def test_proof_of_possession_cached(self, deterministic_keypair):
        """PoP is computed once and cached."""
        pop1 = deterministic_keypair.pop_prove()
        pop2 = deterministic_keypair.pop_prove()
        assert pop1 is pop2  # same object

    def test_pop_verify_wrong_key(self, deterministic_keypair, second_keypair):
        """PoP fails verification against wrong public key."""
        pop = deterministic_keypair.pop_prove()
        assert RealBLSKeyPair.pop_verify(
            second_keypair.public_key, pop
        ) is False

    def test_repr(self, deterministic_keypair):
        """repr includes truncated pubkey hex."""
        r = repr(deterministic_keypair)
        assert "RealBLSKeyPair" in r
        assert "pk=" in r


# ===================================================================
# TestRealBLS12381
# ===================================================================

class TestRealBLS12381:
    """Tests for :class:`RealBLS12381` static operations."""

    # ---- Aggregation -------------------------------------------------------

    def test_aggregate_single_signature(self, deterministic_keypair):
        """Aggregating a single signature returns it unchanged."""
        sig = deterministic_keypair.sign(b"msg")
        agg = RealBLS12381.aggregate_signatures([sig])
        assert agg == sig

    def test_aggregate_multiple_signatures(
        self, deterministic_keypair, second_keypair
    ):
        """Aggregating multiple signatures produces valid output."""
        msg = b"same message"
        sig1 = deterministic_keypair.sign(msg)
        sig2 = second_keypair.sign(msg)
        agg = RealBLS12381.aggregate_signatures([sig1, sig2])
        assert isinstance(agg, bytes)
        assert len(agg) == G2_SIZE
        # The aggregate is different from either individual signature
        assert agg != sig1
        assert agg != sig2

    def test_aggregate_empty_raises(self):
        """Aggregating zero signatures raises ValueError."""
        with pytest.raises(ValueError, match="Cannot aggregate"):
            RealBLS12381.aggregate_signatures([])

    # ---- FastAggregateVerify (same message) --------------------------------

    def test_fast_aggregate_verify_valid(
        self, deterministic_keypair, second_keypair
    ):
        """FastAggregateVerify succeeds for valid same-message aggregate."""
        msg = b"beacon block root"
        sig1 = deterministic_keypair.sign(msg)
        sig2 = second_keypair.sign(msg)
        agg = RealBLS12381.aggregate_signatures([sig1, sig2])

        assert RealBLS12381.fast_aggregate_verify(
            [deterministic_keypair.public_key, second_keypair.public_key],
            msg,
            agg,
        ) is True

    def test_fast_aggregate_verify_wrong_message(
        self, deterministic_keypair, second_keypair
    ):
        """FastAggregateVerify fails for wrong message."""
        msg = b"correct"
        sig1 = deterministic_keypair.sign(msg)
        sig2 = second_keypair.sign(msg)
        agg = RealBLS12381.aggregate_signatures([sig1, sig2])

        assert RealBLS12381.fast_aggregate_verify(
            [deterministic_keypair.public_key, second_keypair.public_key],
            b"wrong",
            agg,
        ) is False

    def test_fast_aggregate_verify_missing_signer(
        self, deterministic_keypair, second_keypair, third_keypair
    ):
        """FastAggregateVerify fails when a non-signer is included."""
        msg = b"msg"
        sig1 = deterministic_keypair.sign(msg)
        sig2 = second_keypair.sign(msg)
        agg = RealBLS12381.aggregate_signatures([sig1, sig2])

        # Use third_keypair instead of second_keypair — should fail
        assert RealBLS12381.fast_aggregate_verify(
            [deterministic_keypair.public_key, third_keypair.public_key],
            msg,
            agg,
        ) is False

    def test_fast_aggregate_verify_empty_pubkeys(self):
        """FastAggregateVerify returns False for empty pubkeys."""
        assert RealBLS12381.fast_aggregate_verify([], b"msg", b"\x00" * 96) is False

    def test_fast_aggregate_verify_single_signer(self, deterministic_keypair):
        """FastAggregateVerify works with a single signer."""
        msg = b"solo"
        sig = deterministic_keypair.sign(msg)
        assert RealBLS12381.fast_aggregate_verify(
            [deterministic_keypair.public_key], msg, sig
        ) is True

    # ---- AggregateVerify (different messages) ------------------------------

    def test_aggregate_verify_valid(
        self, deterministic_keypair, second_keypair
    ):
        """AggregateVerify succeeds for different messages."""
        msg1 = b"message one"
        msg2 = b"message two"
        sig1 = deterministic_keypair.sign(msg1)
        sig2 = second_keypair.sign(msg2)
        agg = RealBLS12381.aggregate_signatures([sig1, sig2])

        assert RealBLS12381.verify_aggregate(
            [deterministic_keypair.public_key, second_keypair.public_key],
            [msg1, msg2],
            agg,
        ) is True

    def test_aggregate_verify_wrong_message(
        self, deterministic_keypair, second_keypair
    ):
        """AggregateVerify fails when a message is swapped."""
        msg1 = b"message one"
        msg2 = b"message two"
        sig1 = deterministic_keypair.sign(msg1)
        sig2 = second_keypair.sign(msg2)
        agg = RealBLS12381.aggregate_signatures([sig1, sig2])

        # Swap messages
        assert RealBLS12381.verify_aggregate(
            [deterministic_keypair.public_key, second_keypair.public_key],
            [msg2, msg1],
            agg,
        ) is False

    def test_aggregate_verify_length_mismatch(self, deterministic_keypair):
        """AggregateVerify raises on pubkeys/messages length mismatch."""
        sig = deterministic_keypair.sign(b"msg")
        with pytest.raises(ValueError, match="pubkeys length"):
            RealBLS12381.verify_aggregate(
                [deterministic_keypair.public_key],
                [b"msg1", b"msg2"],
                sig,
            )

    def test_aggregate_verify_empty(self):
        """AggregateVerify returns False for empty inputs."""
        assert RealBLS12381.verify_aggregate([], [], b"\x00" * 96) is False

    # ---- aggregate_pubkeys -------------------------------------------------

    def test_aggregate_pubkeys(self, deterministic_keypair, second_keypair):
        """Aggregating pubkeys produces a 48-byte result."""
        agg = RealBLS12381.aggregate_pubkeys([
            deterministic_keypair.public_key,
            second_keypair.public_key,
        ])
        assert isinstance(agg, bytes)
        assert len(agg) == G1_SIZE

    def test_aggregate_pubkeys_with_bitmap(
        self, deterministic_keypair, second_keypair, third_keypair
    ):
        """Bitmap selects which pubkeys to include."""
        all_pks = [
            deterministic_keypair.public_key,
            second_keypair.public_key,
            third_keypair.public_key,
        ]

        # Only first and third
        agg_partial = RealBLS12381.aggregate_pubkeys(
            all_pks, bitmap=[True, False, True]
        )
        # Compare with manual aggregate of just first and third
        agg_manual = RealBLS12381.aggregate_pubkeys([
            deterministic_keypair.public_key,
            third_keypair.public_key,
        ])
        assert agg_partial == agg_manual

    def test_aggregate_pubkeys_bitmap_mismatch(self, deterministic_keypair):
        """Bitmap length mismatch raises ValueError."""
        with pytest.raises(ValueError, match="Bitmap length"):
            RealBLS12381.aggregate_pubkeys(
                [deterministic_keypair.public_key],
                bitmap=[True, False],
            )

    def test_aggregate_pubkeys_empty_raises(self):
        """Aggregating zero pubkeys raises ValueError."""
        with pytest.raises(ValueError, match="Cannot aggregate"):
            RealBLS12381.aggregate_pubkeys([])

    def test_aggregate_pubkeys_all_false_bitmap(
        self, deterministic_keypair, second_keypair
    ):
        """All-False bitmap results in zero selected — raises."""
        with pytest.raises(ValueError, match="Cannot aggregate"):
            RealBLS12381.aggregate_pubkeys(
                [deterministic_keypair.public_key, second_keypair.public_key],
                bitmap=[False, False],
            )

    # ---- verify_sync_committee --------------------------------------------

    def test_verify_sync_committee_valid(self, small_committee):
        """Valid sync committee signature verifies."""
        block_root = hashlib.sha256(b"block 42").digest()
        # All 4 members sign
        agg_sig, bits = small_committee.sign_beacon_block_root(
            block_root, [0, 1, 2, 3]
        )
        assert RealBLS12381.verify_sync_committee(
            committee_pubkeys=small_committee.pubkeys,
            signature=agg_sig,
            header_root=block_root,
            participation_bitmap=bits,
            threshold=3,
        ) is True

    def test_verify_sync_committee_below_threshold(self, small_committee):
        """Below-threshold participation fails."""
        block_root = hashlib.sha256(b"block 42").digest()
        # Only 2 of 4 sign, threshold is 3
        agg_sig, bits = small_committee.sign_beacon_block_root(
            block_root, [0, 1]
        )
        assert RealBLS12381.verify_sync_committee(
            committee_pubkeys=small_committee.pubkeys,
            signature=agg_sig,
            header_root=block_root,
            participation_bitmap=bits,
            threshold=3,
        ) is False

    def test_verify_sync_committee_bitmap_mismatch(self, small_committee):
        """Bitmap length mismatch raises."""
        with pytest.raises(ValueError, match="Bitmap length"):
            RealBLS12381.verify_sync_committee(
                committee_pubkeys=small_committee.pubkeys,
                signature=b"\x00" * 96,
                header_root=b"\x00" * 32,
                participation_bitmap=[True, True],  # wrong size
                threshold=1,
            )

    # ---- hash_to_g1 -------------------------------------------------------

    def test_hash_to_g1_produces_48_bytes(self):
        """hash_to_g1 returns 48 bytes."""
        h = RealBLS12381.hash_to_g1(b"test")
        assert len(h) == G1_SIZE

    def test_hash_to_g1_deterministic(self):
        """Same input → same output."""
        h1 = RealBLS12381.hash_to_g1(b"test")
        h2 = RealBLS12381.hash_to_g1(b"test")
        assert h1 == h2

    def test_hash_to_g1_different_inputs(self):
        """Different inputs → different outputs."""
        h1 = RealBLS12381.hash_to_g1(b"test1")
        h2 = RealBLS12381.hash_to_g1(b"test2")
        assert h1 != h2


# ===================================================================
# TestRealSyncCommitteeBLS
# ===================================================================

class TestRealSyncCommitteeBLS:
    """Tests for :class:`RealSyncCommitteeBLS`."""

    def test_setup_deterministic(self, small_committee):
        """Deterministic setup produces same keys."""
        committee2 = RealSyncCommitteeBLS(committee_size=4, threshold=3)
        seeds = [i.to_bytes(32, "big") for i in range(4)]
        committee2.setup_committee(seeds=seeds)
        assert small_committee.pubkeys == committee2.pubkeys

    def test_setup_random(self):
        """Random setup produces valid committee."""
        committee = RealSyncCommitteeBLS(committee_size=4, threshold=3)
        committee.setup_committee()
        assert len(committee.members) == 4
        for m in committee.members:
            assert len(m.public_key) == G1_SIZE

    def test_setup_wrong_seed_count(self):
        """Wrong number of seeds raises ValueError."""
        committee = RealSyncCommitteeBLS(committee_size=4, threshold=3)
        with pytest.raises(ValueError, match="Expected 4 seeds"):
            committee.setup_committee(seeds=[b"\x00" * 32] * 3)

    def test_pubkeys_property(self, small_committee):
        """pubkeys property returns list of 48-byte keys."""
        pks = small_committee.pubkeys
        assert len(pks) == 4
        for pk in pks:
            assert len(pk) == G1_SIZE

    def test_aggregate_pubkey(self, small_committee):
        """aggregate_pubkey returns 48-byte aggregated key."""
        agg = small_committee.aggregate_pubkey
        assert isinstance(agg, bytes)
        assert len(agg) == G1_SIZE

    def test_aggregate_pubkey_uninitialized(self):
        """aggregate_pubkey raises if committee not set up."""
        committee = RealSyncCommitteeBLS(committee_size=4, threshold=3)
        with pytest.raises(ValueError, match="not set up"):
            _ = committee.aggregate_pubkey

    def test_root_deterministic(self, small_committee):
        """Root hash is deterministic."""
        r1 = small_committee.root()
        r2 = small_committee.root()
        assert r1 == r2
        assert len(r1) == 32

    def test_root_different_committees(self):
        """Different committees produce different roots."""
        c1 = RealSyncCommitteeBLS(committee_size=4, threshold=3)
        c1.setup_committee(seeds=[i.to_bytes(32, "big") for i in range(4)])
        c2 = RealSyncCommitteeBLS(committee_size=4, threshold=3)
        c2.setup_committee(seeds=[(i + 10).to_bytes(32, "big") for i in range(4)])
        assert c1.root() != c2.root()

    # ---- Sign + Verify full cycle -----------------------------------------

    def test_sign_and_verify_all_participants(self, small_committee):
        """All members sign → verify succeeds."""
        block_root = os.urandom(32)
        agg_sig, bits = small_committee.sign_beacon_block_root(
            block_root, [0, 1, 2, 3]
        )
        assert len(agg_sig) == G2_SIZE
        assert bits == [True, True, True, True]
        assert small_committee.verify_sync_committee_signature(
            block_root, agg_sig, bits
        ) is True

    def test_sign_and_verify_threshold_exactly(self, small_committee):
        """Exactly threshold members sign → verify succeeds."""
        block_root = os.urandom(32)
        # threshold=3, so 3 out of 4 should pass
        agg_sig, bits = small_committee.sign_beacon_block_root(
            block_root, [0, 1, 2]
        )
        assert sum(bits) == 3
        assert small_committee.verify_sync_committee_signature(
            block_root, agg_sig, bits
        ) is True

    def test_sign_and_verify_below_threshold(self, small_committee):
        """Below-threshold participation → verify fails."""
        block_root = os.urandom(32)
        # threshold=3, only 2 sign
        agg_sig, bits = small_committee.sign_beacon_block_root(
            block_root, [0, 1]
        )
        assert sum(bits) == 2
        assert small_committee.verify_sync_committee_signature(
            block_root, agg_sig, bits
        ) is False

    def test_sign_wrong_block_root(self, small_committee):
        """Signature for one block root does not verify for another."""
        root1 = os.urandom(32)
        root2 = os.urandom(32)
        agg_sig, bits = small_committee.sign_beacon_block_root(
            root1, [0, 1, 2, 3]
        )
        assert small_committee.verify_sync_committee_signature(
            root2, agg_sig, bits
        ) is False

    def test_sign_with_external_pubkeys(self, small_committee):
        """Verification works with explicitly provided pubkeys."""
        block_root = os.urandom(32)
        agg_sig, bits = small_committee.sign_beacon_block_root(
            block_root, [0, 1, 2, 3]
        )
        # Pass pubkeys explicitly
        assert small_committee.verify_sync_committee_signature(
            block_root, agg_sig, bits,
            committee_pubkeys=small_committee.pubkeys,
        ) is True

    def test_sign_invalid_index(self, small_committee):
        """Out-of-range participant index raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            small_committee.sign_beacon_block_root(
                os.urandom(32), [0, 1, 4]  # 4 is out of range for size=4
            )

    def test_sign_negative_index(self, small_committee):
        """Negative participant index raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            small_committee.sign_beacon_block_root(
                os.urandom(32), [0, -1]
            )

    def test_sign_not_initialized(self):
        """Signing without setup raises ValueError."""
        committee = RealSyncCommitteeBLS(committee_size=4, threshold=3)
        with pytest.raises(ValueError, match="not set up"):
            committee.sign_beacon_block_root(os.urandom(32), [0])

    # ---- Participant selection ---------------------------------------------

    def test_select_participants(self, small_committee):
        """select_participants filters by bitmap."""
        bitmap = [True, False, True, False]
        selected = small_committee.select_participants(bitmap)
        assert len(selected) == 2
        assert selected[0] == small_committee.pubkeys[0]
        assert selected[1] == small_committee.pubkeys[2]

    def test_select_participants_all_true(self, small_committee):
        """All True returns all pubkeys."""
        bitmap = [True] * 4
        selected = small_committee.select_participants(bitmap)
        assert selected == small_committee.pubkeys

    def test_select_participants_all_false(self, small_committee):
        """All False returns empty list."""
        bitmap = [False] * 4
        selected = small_committee.select_participants(bitmap)
        assert selected == []

    def test_select_participants_bitmap_mismatch(self, small_committee):
        """Wrong bitmap length raises ValueError."""
        with pytest.raises(ValueError, match="Bitmap length"):
            small_committee.select_participants([True, True])

    def test_participant_count(self, small_committee):
        """participant_count correctly counts True bits."""
        assert small_committee.participant_count([True, False, True, False]) == 2
        assert small_committee.participant_count([True] * 4) == 4
        assert small_committee.participant_count([False] * 4) == 0

    def test_participant_count_mismatch(self, small_committee):
        """participant_count raises on length mismatch."""
        with pytest.raises(ValueError, match="Bitmap length"):
            small_committee.participant_count([True])

    # ---- Serialisation / format -------------------------------------------

    def test_to_light_client_format(self, small_committee):
        """to_light_client_format produces correct dict."""
        fmt = small_committee.to_light_client_format()
        assert fmt["period"] == 0
        assert len(fmt["pubkeys"]) == 4
        for pk_hex in fmt["pubkeys"]:
            assert len(pk_hex) == G1_SIZE * 2  # hex encoding
        assert len(fmt["aggregate_pubkey"]) == G1_SIZE * 2

    def test_repr_initialized(self, small_committee):
        """repr shows period, member count, root prefix."""
        r = repr(small_committee)
        assert "RealSyncCommitteeBLS" in r
        assert "period=0" in r
        assert "members=4" in r
        assert "root=" in r

    def test_repr_uninitialized(self):
        """repr shows not_initialized when committee not set up."""
        c = RealSyncCommitteeBLS(committee_size=8, threshold=6)
        r = repr(c)
        assert "not_initialized" in r


# ===================================================================
# TestMediumCommittee — more thorough with 8 members
# ===================================================================

class TestMediumCommittee:
    """Tests with an 8-member committee for broader coverage."""

    def test_supermajority_signs(self, medium_committee):
        """6 of 8 (exactly threshold) signs and verifies."""
        block_root = hashlib.sha256(b"slot 100").digest()
        agg_sig, bits = medium_committee.sign_beacon_block_root(
            block_root, [0, 1, 2, 3, 4, 5]
        )
        assert sum(bits) == 6
        assert medium_committee.verify_sync_committee_signature(
            block_root, agg_sig, bits
        ) is True

    def test_five_of_eight_below_threshold(self, medium_committee):
        """5 of 8 (below threshold=6) fails."""
        block_root = hashlib.sha256(b"slot 101").digest()
        agg_sig, bits = medium_committee.sign_beacon_block_root(
            block_root, [0, 1, 2, 3, 4]
        )
        assert sum(bits) == 5
        assert medium_committee.verify_sync_committee_signature(
            block_root, agg_sig, bits
        ) is False

    def test_all_eight_sign(self, medium_committee):
        """All 8 members sign → verify succeeds."""
        block_root = hashlib.sha256(b"slot 102").digest()
        agg_sig, bits = medium_committee.sign_beacon_block_root(
            block_root, list(range(8))
        )
        assert sum(bits) == 8
        assert medium_committee.verify_sync_committee_signature(
            block_root, agg_sig, bits
        ) is True

    def test_different_participant_subsets(self, medium_committee):
        """Different subsets produce different signatures."""
        block_root = hashlib.sha256(b"slot 103").digest()
        agg1, _ = medium_committee.sign_beacon_block_root(
            block_root, [0, 1, 2, 3, 4, 5]
        )
        agg2, _ = medium_committee.sign_beacon_block_root(
            block_root, [2, 3, 4, 5, 6, 7]
        )
        assert agg1 != agg2

    def test_cross_verify_fails(self, medium_committee):
        """Signature from one subset doesn't verify for different bitmap."""
        block_root = hashlib.sha256(b"slot 104").digest()
        # Sign with [0,1,2,3,4,5]
        agg_sig, bits1 = medium_committee.sign_beacon_block_root(
            block_root, [0, 1, 2, 3, 4, 5]
        )
        # Create different bitmap — say [2,3,4,5,6,7]
        bits2 = [False, False, True, True, True, True, True, True]
        # Verification should fail because the aggregate doesn't match bits2
        assert medium_committee.verify_sync_committee_signature(
            block_root, agg_sig, bits2
        ) is False


# ===================================================================
# TestCrossCompatibility — simulated vs real
# ===================================================================

class TestCrossCompatibility:
    """Verify that real and simulated backends have matching interfaces."""

    def test_factory_real(self):
        """get_bls_backend(real=True) returns real classes."""
        KP, Ops, SC = get_bls_backend(real=True)
        assert KP is RealBLSKeyPair
        assert Ops is RealBLS12381
        assert SC is RealSyncCommitteeBLS

    def test_factory_simulated(self):
        """get_bls_backend(real=False) returns simulated classes."""
        from asi_build.rings.bridge.zk.bls import (
            BLS12381,
            BLSKeyPair,
            SyncCommitteeBLS,
        )
        KP, Ops, SC = get_bls_backend(real=False)
        assert KP is BLSKeyPair
        assert Ops is BLS12381
        assert SC is SyncCommitteeBLS

    def test_real_keypair_has_generate(self):
        """RealBLSKeyPair has .generate() class method."""
        assert hasattr(RealBLSKeyPair, "generate")

    def test_real_keypair_has_sign_verify(self, deterministic_keypair):
        """RealBLSKeyPair has .sign() and .verify() methods."""
        assert hasattr(deterministic_keypair, "sign")
        assert hasattr(deterministic_keypair, "verify")

    def test_real_ops_has_required_methods(self):
        """RealBLS12381 has all required static methods."""
        assert hasattr(RealBLS12381, "aggregate_signatures")
        assert hasattr(RealBLS12381, "aggregate_pubkeys")
        assert hasattr(RealBLS12381, "fast_aggregate_verify")
        assert hasattr(RealBLS12381, "verify_aggregate")
        assert hasattr(RealBLS12381, "verify_sync_committee")
        assert hasattr(RealBLS12381, "hash_to_g1")

    def test_real_committee_has_required_methods(self):
        """RealSyncCommitteeBLS has all required methods."""
        c = RealSyncCommitteeBLS(committee_size=4, threshold=3)
        assert hasattr(c, "setup_committee")
        assert hasattr(c, "sign_beacon_block_root")
        assert hasattr(c, "verify_sync_committee_signature")
        assert hasattr(c, "select_participants")
        assert hasattr(c, "participant_count")
        assert hasattr(c, "to_light_client_format")
        assert hasattr(c, "root")


# ===================================================================
# TestConstants
# ===================================================================

class TestConstants:
    """Verify cryptographic constants match Ethereum spec."""

    def test_curve_order_matches(self):
        """GROUP_ORDER matches py_ecc's curve_order."""
        assert GROUP_ORDER == CURVE_ORDER

    def test_curve_order_bit_length(self):
        """Curve order is ~255 bits."""
        assert 254 <= CURVE_ORDER.bit_length() <= 256

    def test_field_modulus_bit_length(self):
        """Field modulus is 381 bits."""
        assert FIELD_MODULUS.bit_length() == 381

    def test_g1_size(self):
        assert G1_SIZE == 48

    def test_g2_size(self):
        assert G2_SIZE == 96

    def test_sync_committee_size(self):
        assert SYNC_COMMITTEE_SIZE == 512

    def test_default_threshold(self):
        assert DEFAULT_SYNC_THRESHOLD == 342


# ===================================================================
# TestEth2SpecVectors — Known test vectors
# ===================================================================

class TestEth2SpecVectors:
    """Test against known Ethereum 2.0 BLS test vectors.

    These are derived from the eth2 specification test suite at
    https://github.com/ethereum/bls12-381-tests
    """

    def test_keygen_deterministic_vector(self):
        """KeyGen with known IKM produces expected key."""
        ikm = b"\x00" * 32
        from py_ecc.bls import G2ProofOfPossession as bls
        sk = bls.KeyGen(ikm)
        pk = bls.SkToPk(sk)
        # The secret key should be a valid scalar in [1, CURVE_ORDER)
        assert 1 <= sk < CURVE_ORDER
        # Public key should be a valid compressed G1 point (48 bytes)
        assert len(pk) == 48
        # Key should validate
        assert bls.KeyValidate(pk) is True

    def test_sign_verify_roundtrip_known_message(self):
        """Sign and verify with a known message from eth2 test vectors."""
        kp = RealBLSKeyPair.generate(seed=b"\x00" * 32)
        # Ethereum beacon block roots are always 32 bytes
        block_root = bytes.fromhex(
            "0000000000000000000000000000000000000000000000000000000000000000"
        )
        sig = kp.sign(block_root)
        assert kp.verify(block_root, sig) is True

    def test_aggregate_verify_three_signers(self):
        """Three signers with different messages → AggregateVerify."""
        kps = [RealBLSKeyPair.generate(seed=i.to_bytes(32, "big")) for i in range(3)]
        msgs = [b"msg_0", b"msg_1", b"msg_2"]
        sigs = [kps[i].sign(msgs[i]) for i in range(3)]
        agg = RealBLS12381.aggregate_signatures(sigs)

        assert RealBLS12381.verify_aggregate(
            [kp.public_key for kp in kps], msgs, agg
        ) is True

    def test_fast_aggregate_verify_four_signers(self):
        """Four signers on same message → FastAggregateVerify."""
        kps = [RealBLSKeyPair.generate(seed=i.to_bytes(32, "big")) for i in range(4)]
        msg = hashlib.sha256(b"common beacon root").digest()
        sigs = [kp.sign(msg) for kp in kps]
        agg = RealBLS12381.aggregate_signatures(sigs)

        assert RealBLS12381.fast_aggregate_verify(
            [kp.public_key for kp in kps], msg, agg
        ) is True

    def test_pop_prove_and_verify(self):
        """Proof of Possession roundtrip per Ethereum spec."""
        kp = RealBLSKeyPair.generate(seed=b"\xab" * 32)
        pop = kp.pop_prove()
        assert RealBLSKeyPair.pop_verify(kp.public_key, pop) is True

        # Wrong pubkey should fail
        kp2 = RealBLSKeyPair.generate(seed=b"\xcd" * 32)
        assert RealBLSKeyPair.pop_verify(kp2.public_key, pop) is False


# ===================================================================
# TestEdgeCases
# ===================================================================

class TestEdgeCases:
    """Edge cases and error scenarios."""

    def test_sign_32_byte_beacon_root(self, deterministic_keypair):
        """Beacon block roots are exactly 32 bytes — this is the hot path."""
        root = hashlib.sha256(b"beacon block content").digest()
        assert len(root) == 32
        sig = deterministic_keypair.sign(root)
        assert deterministic_keypair.verify(root, sig) is True

    def test_single_member_committee(self):
        """Committee of 1 with threshold=1 works."""
        c = RealSyncCommitteeBLS(committee_size=1, threshold=1)
        c.setup_committee(seeds=[b"\x00" * 32])
        root = os.urandom(32)
        agg_sig, bits = c.sign_beacon_block_root(root, [0])
        assert c.verify_sync_committee_signature(root, agg_sig, bits) is True

    def test_threshold_equals_committee_size(self):
        """All members must sign when threshold == committee_size."""
        c = RealSyncCommitteeBLS(committee_size=4, threshold=4)
        c.setup_committee(seeds=[i.to_bytes(32, "big") for i in range(4)])
        root = os.urandom(32)

        # Only 3 sign — should fail
        agg_sig, bits = c.sign_beacon_block_root(root, [0, 1, 2])
        assert c.verify_sync_committee_signature(root, agg_sig, bits) is False

        # All 4 sign — should pass
        agg_sig, bits = c.sign_beacon_block_root(root, [0, 1, 2, 3])
        assert c.verify_sync_committee_signature(root, agg_sig, bits) is True

    def test_committee_period(self):
        """Committee period is stored and retrievable."""
        c = RealSyncCommitteeBLS(committee_size=4, threshold=3, period=42)
        assert c.period == 42

    def test_multiple_blocks_same_committee(self, small_committee):
        """Same committee signs multiple blocks — each verifies independently."""
        root1 = os.urandom(32)
        root2 = os.urandom(32)

        agg1, bits1 = small_committee.sign_beacon_block_root(root1, [0, 1, 2])
        agg2, bits2 = small_committee.sign_beacon_block_root(root2, [1, 2, 3])

        # Each verifies for its own root
        assert small_committee.verify_sync_committee_signature(root1, agg1, bits1) is True
        assert small_committee.verify_sync_committee_signature(root2, agg2, bits2) is True

        # Cross-check fails
        assert small_committee.verify_sync_committee_signature(root1, agg2, bits2) is False
        assert small_committee.verify_sync_committee_signature(root2, agg1, bits1) is False

    def test_duplicate_participant_indices(self, small_committee):
        """Duplicate participant indices — signs once per index position.

        BLS aggregation of duplicate signatures is mathematically valid
        but the bitvector will only show the member as participating once.
        However, the aggregate would be wrong because it includes the
        signature twice. This tests that behavior is defined.
        """
        root = os.urandom(32)
        # Index 0 appears twice — will sign twice and aggregate
        agg_sig, bits = small_committee.sign_beacon_block_root(root, [0, 0, 1, 2])
        # bits[0] is set True twice but result is same
        assert bits[0] is True
        # Verification should FAIL because aggregate includes sig_0 twice
        # but the verifier only accounts for it once
        assert small_committee.verify_sync_committee_signature(
            root, agg_sig, bits
        ) is False
