"""Tests for BLS12-381 simulation primitives.

Covers BLSKeyPair, BLSPublicKey, BLSSignature, BLS12381 static methods,
SyncCommitteeBLS, and module constants.
"""

import hashlib
import os

import pytest

from src.asi_build.rings.bridge.zk.bls import (
    BLS12381,
    BLSKeyPair,
    BLSPublicKey,
    BLSSignature,
    DOMAIN_SEPARATOR,
    FIELD_MODULUS,
    G1_SIZE,
    G2_SIZE,
    GROUP_ORDER,
    SYNC_COMMITTEE_SIZE,
    SyncCommitteeBLS,
    _clear_registries,
)


# ---------------------------------------------------------------------------
# Fixture — clear registries between every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_bls_registries():
    _clear_registries()
    yield
    _clear_registries()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gen_committee(n: int = 512) -> list[BLSKeyPair]:
    """Generate *n* deterministic key pairs."""
    return [BLSKeyPair.generate(seed=i.to_bytes(4, "big")) for i in range(n)]


# ===================================================================
# BLSKeyPair
# ===================================================================

class TestBLSKeyPair:

    def test_generate_random(self):
        kp1 = BLSKeyPair.generate()
        kp2 = BLSKeyPair.generate()
        assert kp1.secret != kp2.secret
        assert kp1.public_key != kp2.public_key

    def test_generate_from_seed(self):
        kp = BLSKeyPair.generate(seed=b"test_seed")
        assert len(kp.secret) == 32
        assert isinstance(kp.public_key, BLSPublicKey)

    def test_generate_from_same_seed(self):
        kp1 = BLSKeyPair.generate(seed=b"same")
        kp2 = BLSKeyPair.generate(seed=b"same")
        assert kp1.secret == kp2.secret
        assert kp1.public_key == kp2.public_key

    def test_generate_different_seeds(self):
        kp1 = BLSKeyPair.generate(seed=b"alpha")
        kp2 = BLSKeyPair.generate(seed=b"beta")
        assert kp1.secret != kp2.secret
        assert kp1.public_key != kp2.public_key

    def test_pubkey_is_48_bytes(self):
        kp = BLSKeyPair.generate(seed=b"x")
        assert len(kp.public_key.key_bytes) == 48

    def test_sign_produces_96_bytes(self):
        kp = BLSKeyPair.generate(seed=b"signer")
        sig = kp.sign(b"hello world")
        assert len(sig.sig_bytes) == 96

    def test_sign_deterministic(self):
        kp = BLSKeyPair.generate(seed=b"det")
        sig1 = kp.sign(b"msg")
        _clear_registries()
        sig2 = kp.sign(b"msg")
        assert sig1 == sig2

    def test_sign_different_messages(self):
        kp = BLSKeyPair.generate(seed=b"d")
        s1 = kp.sign(b"message_a")
        s2 = kp.sign(b"message_b")
        assert s1 != s2

    def test_verify_valid_signature(self):
        kp = BLSKeyPair.generate(seed=b"v")
        msg = b"verify me"
        sig = kp.sign(msg)
        assert BLSKeyPair.verify(msg, sig, kp.public_key) is True

    def test_verify_wrong_message(self):
        kp = BLSKeyPair.generate(seed=b"w")
        sig = kp.sign(b"correct")
        assert BLSKeyPair.verify(b"wrong", sig, kp.public_key) is False

    def test_verify_wrong_pubkey(self):
        kp1 = BLSKeyPair.generate(seed=b"k1")
        kp2 = BLSKeyPair.generate(seed=b"k2")
        sig = kp1.sign(b"test")
        assert BLSKeyPair.verify(b"test", sig, kp2.public_key) is False

    def test_secret_must_be_32_bytes(self):
        with pytest.raises(ValueError, match="32 bytes"):
            BLSKeyPair(secret=b"\x00" * 16, public_key=BLSPublicKey(key_bytes=b"\x00" * 48))


# ===================================================================
# BLSPublicKey
# ===================================================================

class TestBLSPublicKey:

    def test_from_secret(self):
        pk = BLSPublicKey.from_secret(os.urandom(32))
        assert len(pk.key_bytes) == 48

    def test_hex_roundtrip(self):
        pk = BLSPublicKey.from_secret(b"\xaa" * 32)
        hex_str = pk.hex()
        recovered = BLSPublicKey.from_hex(hex_str)
        assert recovered == pk

    def test_equality(self):
        data = b"\xbb" * 48
        pk1 = BLSPublicKey(key_bytes=data)
        pk2 = BLSPublicKey(key_bytes=data)
        assert pk1 == pk2

    def test_inequality(self):
        pk1 = BLSPublicKey(key_bytes=b"\x01" * 48)
        pk2 = BLSPublicKey(key_bytes=b"\x02" * 48)
        assert pk1 != pk2

    def test_hashable(self):
        pk1 = BLSPublicKey(key_bytes=b"\x01" * 48)
        pk2 = BLSPublicKey(key_bytes=b"\x02" * 48)
        pk3 = BLSPublicKey(key_bytes=b"\x01" * 48)
        s = {pk1, pk2, pk3}
        assert len(s) == 2

    def test_wrong_size_raises(self):
        with pytest.raises(ValueError, match="48 bytes"):
            BLSPublicKey(key_bytes=b"\x00" * 32)

    def test_repr(self):
        pk = BLSPublicKey(key_bytes=b"\xab" * 48)
        assert "BLSPublicKey(" in repr(pk)


# ===================================================================
# BLSSignature
# ===================================================================

class TestBLSSignature:

    def test_sig_bytes_96(self):
        sig = BLSSignature(sig_bytes=os.urandom(96))
        assert len(sig.sig_bytes) == 96

    def test_hex_roundtrip(self):
        data = os.urandom(96)
        sig = BLSSignature(sig_bytes=data)
        recovered = BLSSignature.from_hex(sig.hex())
        assert recovered == sig

    def test_equality(self):
        data = b"\xcc" * 96
        assert BLSSignature(sig_bytes=data) == BLSSignature(sig_bytes=data)

    def test_inequality(self):
        assert BLSSignature(sig_bytes=b"\x01" * 96) != BLSSignature(sig_bytes=b"\x02" * 96)

    def test_hashable(self):
        s1 = BLSSignature(sig_bytes=b"\x01" * 96)
        s2 = BLSSignature(sig_bytes=b"\x01" * 96)
        assert len({s1, s2}) == 1

    def test_wrong_size_raises(self):
        with pytest.raises(ValueError, match="96 bytes"):
            BLSSignature(sig_bytes=b"\x00" * 48)

    def test_repr(self):
        sig = BLSSignature(sig_bytes=b"\xde" * 96)
        assert "BLSSignature(" in repr(sig)


# ===================================================================
# BLS12381 static methods
# ===================================================================

class TestBLS12381:

    def test_hash_to_g1(self):
        result = BLS12381.hash_to_g1(b"test message")
        assert len(result) == 48

    def test_hash_to_g1_deterministic(self):
        h1 = BLS12381.hash_to_g1(b"same input")
        h2 = BLS12381.hash_to_g1(b"same input")
        assert h1 == h2

    def test_hash_to_g1_different_inputs(self):
        h1 = BLS12381.hash_to_g1(b"input_a")
        h2 = BLS12381.hash_to_g1(b"input_b")
        assert h1 != h2

    def test_hash_to_g1_custom_dst(self):
        default = BLS12381.hash_to_g1(b"msg")
        custom = BLS12381.hash_to_g1(b"msg", dst=b"CUSTOM_DST_")
        assert default != custom

    def test_aggregate_signatures_single(self):
        kp = BLSKeyPair.generate(seed=b"solo")
        sig = kp.sign(b"msg")
        agg = BLS12381.aggregate_signatures([sig])
        assert isinstance(agg, BLSSignature)
        assert len(agg.sig_bytes) == 96

    def test_aggregate_signatures_multiple(self):
        kps = [BLSKeyPair.generate(seed=i.to_bytes(4, "big")) for i in range(5)]
        msg = b"common message"
        sigs = [kp.sign(msg) for kp in kps]
        agg = BLS12381.aggregate_signatures(sigs)
        assert isinstance(agg, BLSSignature)
        assert len(agg.sig_bytes) == 96

    def test_aggregate_signatures_empty_raises(self):
        with pytest.raises(ValueError, match="zero signatures"):
            BLS12381.aggregate_signatures([])

    def test_aggregate_pubkeys(self):
        pks = [BLSKeyPair.generate(seed=i.to_bytes(4, "big")).public_key for i in range(10)]
        agg = BLS12381.aggregate_pubkeys(pks)
        assert isinstance(agg, BLSPublicKey)
        assert len(agg.key_bytes) == 48

    def test_aggregate_pubkeys_with_bitmap(self):
        pks = [BLSKeyPair.generate(seed=i.to_bytes(4, "big")).public_key for i in range(5)]
        bitmap = [True, False, True, False, True]
        agg = BLS12381.aggregate_pubkeys(pks, bitmap=bitmap)
        assert isinstance(agg, BLSPublicKey)
        # Should only use keys 0, 2, 4
        agg_manual = BLS12381.aggregate_pubkeys([pks[0], pks[2], pks[4]])
        assert agg == agg_manual

    def test_aggregate_pubkeys_bitmap_length_mismatch(self):
        pks = [BLSKeyPair.generate(seed=i.to_bytes(4, "big")).public_key for i in range(5)]
        with pytest.raises(ValueError, match="Bitmap length"):
            BLS12381.aggregate_pubkeys(pks, bitmap=[True, False])

    def test_aggregate_pubkeys_empty_raises(self):
        with pytest.raises(ValueError, match="zero public keys"):
            BLS12381.aggregate_pubkeys([], bitmap=[])

    def test_verify_aggregate_valid(self):
        kps = [BLSKeyPair.generate(seed=i.to_bytes(4, "big")) for i in range(5)]
        msg = b"aggregate test"
        sigs = [kp.sign(msg) for kp in kps]
        agg_sig = BLS12381.aggregate_signatures(sigs)
        agg_pk = BLS12381.aggregate_pubkeys([kp.public_key for kp in kps])
        assert BLS12381.verify_aggregate(agg_sig, agg_pk, msg) is True

    def test_verify_aggregate_wrong_message(self):
        kps = [BLSKeyPair.generate(seed=i.to_bytes(4, "big")) for i in range(3)]
        sigs = [kp.sign(b"correct") for kp in kps]
        agg_sig = BLS12381.aggregate_signatures(sigs)
        agg_pk = BLS12381.aggregate_pubkeys([kp.public_key for kp in kps])
        assert BLS12381.verify_aggregate(agg_sig, agg_pk, b"wrong") is False

    def test_verify_aggregate_unknown_sig(self):
        """An aggregate not in the registry should fail."""
        fake_sig = BLSSignature(sig_bytes=os.urandom(96))
        fake_pk = BLSPublicKey(key_bytes=os.urandom(48))
        assert BLS12381.verify_aggregate(fake_sig, fake_pk, b"msg") is False

    def test_verify_sync_committee_valid(self):
        kps = _gen_committee(512)
        msg = b"header_root_data"

        # Sign with 400 participants
        bitmap = [True] * 400 + [False] * 112
        sigs = [kps[i].sign(msg) for i in range(400)]
        agg_sig = BLS12381.aggregate_signatures(sigs)

        pubkey_bytes = [kp.public_key.key_bytes for kp in kps]
        result = BLS12381.verify_sync_committee(
            committee_pubkeys=pubkey_bytes,
            signature=agg_sig.sig_bytes,
            header_root=msg,
            participation_bitmap=bitmap,
            threshold=342,
        )
        assert result is True

    def test_verify_sync_committee_below_threshold(self):
        kps = _gen_committee(512)
        msg = b"header"

        bitmap = [True] * 300 + [False] * 212
        sigs = [kps[i].sign(msg) for i in range(300)]
        agg_sig = BLS12381.aggregate_signatures(sigs)

        pubkey_bytes = [kp.public_key.key_bytes for kp in kps]
        result = BLS12381.verify_sync_committee(
            committee_pubkeys=pubkey_bytes,
            signature=agg_sig.sig_bytes,
            header_root=msg,
            participation_bitmap=bitmap,
            threshold=342,
        )
        assert result is False

    def test_verify_sync_committee_exact_threshold(self):
        kps = _gen_committee(512)
        msg = b"exactly_342"

        bitmap = [True] * 342 + [False] * 170
        sigs = [kps[i].sign(msg) for i in range(342)]
        agg_sig = BLS12381.aggregate_signatures(sigs)

        pubkey_bytes = [kp.public_key.key_bytes for kp in kps]
        result = BLS12381.verify_sync_committee(
            committee_pubkeys=pubkey_bytes,
            signature=agg_sig.sig_bytes,
            header_root=msg,
            participation_bitmap=bitmap,
            threshold=342,
        )
        assert result is True

    def test_verify_sync_committee_bitmap_mismatch(self):
        """Bitmap length != committee size should raise ValueError.

        Note: verify_sync_committee checks participation count *before*
        bitmap length, so we must ensure sum(bitmap) >= threshold to
        actually reach the length check.
        """
        kps = _gen_committee(10)
        pubkey_bytes = [kp.public_key.key_bytes for kp in kps]
        # 8 True values in a bitmap of length 8 (not 10) -> passes threshold
        # but mismatches committee size 10 -> ValueError
        with pytest.raises(ValueError, match="Bitmap length"):
            BLS12381.verify_sync_committee(
                committee_pubkeys=pubkey_bytes,
                signature=os.urandom(96),
                header_root=b"x",
                participation_bitmap=[True] * 8,  # len=8 != 10 pubkeys
                threshold=7,
            )


# ===================================================================
# SyncCommitteeBLS
# ===================================================================

class TestSyncCommitteeBLS:

    def _make_committee(self, n: int = 512, period: int = 1) -> SyncCommitteeBLS:
        kps = _gen_committee(n)
        pubkeys = [kp.public_key.key_bytes for kp in kps]
        agg = BLS12381.aggregate_pubkeys([kp.public_key for kp in kps])
        return SyncCommitteeBLS(
            pubkeys=pubkeys,
            aggregate_pubkey=agg.key_bytes,
            period=period,
        )

    def test_creation(self):
        sc = self._make_committee()
        assert len(sc.pubkeys) == 512
        assert len(sc.aggregate_pubkey) == 48
        assert sc.period == 1

    def test_root_deterministic(self):
        sc = self._make_committee()
        r1 = sc.root()
        r2 = sc.root()
        assert r1 == r2
        assert len(r1) == 32

    def test_root_different_committees(self):
        sc1 = self._make_committee(period=1)
        # Generate a different committee (different seeds via offset)
        kps = [BLSKeyPair.generate(seed=(i + 1000).to_bytes(4, "big")) for i in range(512)]
        pubkeys = [kp.public_key.key_bytes for kp in kps]
        agg = BLS12381.aggregate_pubkeys([kp.public_key for kp in kps])
        sc2 = SyncCommitteeBLS(pubkeys=pubkeys, aggregate_pubkey=agg.key_bytes, period=2)
        assert sc1.root() != sc2.root()

    def test_select_participants(self):
        sc = self._make_committee()
        bitmap = [False] * 512
        bitmap[0] = True
        bitmap[5] = True
        bitmap[511] = True
        selected = sc.select_participants(bitmap)
        assert len(selected) == 3
        assert selected[0] == sc.pubkeys[0]
        assert selected[1] == sc.pubkeys[5]
        assert selected[2] == sc.pubkeys[511]

    def test_select_participants_all_true(self):
        sc = self._make_committee()
        bitmap = [True] * 512
        selected = sc.select_participants(bitmap)
        assert len(selected) == 512
        assert selected == sc.pubkeys

    def test_select_participants_all_false(self):
        sc = self._make_committee()
        bitmap = [False] * 512
        selected = sc.select_participants(bitmap)
        assert selected == []

    def test_select_participants_bitmap_mismatch(self):
        sc = self._make_committee()
        with pytest.raises(ValueError, match="Bitmap length"):
            sc.select_participants([True] * 10)

    def test_participant_count(self):
        sc = self._make_committee()
        bitmap = [True] * 400 + [False] * 112
        assert sc.participant_count(bitmap) == 400

    def test_participant_count_empty_bitmap(self):
        sc = self._make_committee()
        bitmap = [False] * 512
        assert sc.participant_count(bitmap) == 0

    def test_participant_count_bitmap_mismatch(self):
        sc = self._make_committee()
        with pytest.raises(ValueError, match="Bitmap length"):
            sc.participant_count([True] * 10)

    def test_to_light_client_format(self):
        sc = self._make_committee(period=7)
        lc = sc.to_light_client_format()
        assert lc["period"] == 7
        assert len(lc["pubkeys"]) == 512
        assert all(isinstance(pk, str) for pk in lc["pubkeys"])
        assert isinstance(lc["aggregate_pubkey"], str)
        # hex roundtrip
        assert bytes.fromhex(lc["pubkeys"][0]) == sc.pubkeys[0]

    def test_wrong_pubkey_size_raises(self):
        with pytest.raises(ValueError, match="expected 48"):
            SyncCommitteeBLS(
                pubkeys=[b"\x00" * 32],  # too short
                aggregate_pubkey=b"\x00" * 48,
                period=0,
            )

    def test_wrong_aggregate_size_raises(self):
        kp = BLSKeyPair.generate(seed=b"x")
        with pytest.raises(ValueError, match="expected 48"):
            SyncCommitteeBLS(
                pubkeys=[kp.public_key.key_bytes],
                aggregate_pubkey=b"\x00" * 32,  # too short
                period=0,
            )

    def test_repr(self):
        sc = self._make_committee()
        r = repr(sc)
        assert "SyncCommitteeBLS" in r
        assert "period=" in r
        assert "members=512" in r


# ===================================================================
# Constants
# ===================================================================

class TestConstants:

    def test_field_modulus_bit_length(self):
        """BLS12-381 field modulus p is ~381 bits."""
        assert FIELD_MODULUS.bit_length() == 381

    def test_group_order_bit_length(self):
        """BLS12-381 group order r is ~255 bits."""
        assert GROUP_ORDER.bit_length() == 255

    def test_g1_size(self):
        assert G1_SIZE == 48

    def test_g2_size(self):
        assert G2_SIZE == 96

    def test_sync_committee_size(self):
        assert SYNC_COMMITTEE_SIZE == 512

    def test_domain_separator_is_bytes(self):
        assert isinstance(DOMAIN_SEPARATOR, bytes)
        assert b"BLS12381" in DOMAIN_SEPARATOR
