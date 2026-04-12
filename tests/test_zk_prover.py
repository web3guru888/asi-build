"""
Tests for Groth16 ZK Proof System
===================================

Comprehensive tests for the real BN254 pairing-based Groth16 proof
system used in the Rings ↔ Ethereum bridge.

Each test that involves pairing verification is inherently slow (~10-15s)
because of the py_ecc BN128 pairing computation.  Tests are organised
so that the fast (non-pairing) tests run first, and expensive pairing
tests are clearly marked.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time

import pytest

from py_ecc.bn128 import (
    G1,
    G2,
    Z1,
    Z2,
    FQ,
    FQ2,
    FQ12,
    add,
    curve_order,
    field_modulus,
    is_on_curve,
    multiply,
    neg,
)
from py_ecc.bn128.bn128_curve import b as B_COEFF, b2 as B2_COEFF

from asi_build.rings.bridge.zk_prover import (
    BridgeWithdrawalCircuit,
    Groth16Proof,
    Groth16Prover,
    Groth16Verifier,
    ProvingKey,
    SyncCommitteeCircuit,
    TrustedSetup,
    VerificationKey,
    _is_valid_g1,
    _is_valid_g2,
    g1_to_uint256,
    g2_to_uint256,
    hash_to_scalar,
    random_scalar,
    vk_to_solidity_args,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def setup():
    """Create a single deterministic setup for the entire test module.

    This is expensive (~2-3s) so we share it across tests.
    """
    return TrustedSetup(num_public_inputs=3, num_witness=4, seed=42)


@pytest.fixture(scope="module")
def prover(setup):
    """Prover instance from the shared setup."""
    return Groth16Prover(setup.pk)


@pytest.fixture(scope="module")
def verifier(setup):
    """Verifier instance from the shared setup."""
    return Groth16Verifier(setup.vk)


@pytest.fixture(scope="module")
def valid_proof(prover):
    """A pre-generated valid proof for reuse in multiple tests."""
    return prover.prove([100, 200, 300], witness=[1, 2, 3, 4])


@pytest.fixture(scope="module")
def valid_proof_bytes(valid_proof):
    """Serialised version of the valid proof."""
    return Groth16Prover.serialize_proof(valid_proof)


# ---------------------------------------------------------------------------
# 1. TrustedSetup Tests
# ---------------------------------------------------------------------------

class TestTrustedSetup:
    """Tests for key generation and setup consistency."""

    def test_setup_creates_vk_and_pk(self, setup):
        assert isinstance(setup.vk, VerificationKey)
        assert isinstance(setup.pk, ProvingKey)

    def test_vk_num_public_inputs(self, setup):
        assert setup.vk.num_public_inputs == 3

    def test_vk_ic_length(self, setup):
        # IC has n_pub + 1 elements (constant + one per public input)
        assert len(setup.vk.ic) == 4

    def test_vk_points_on_curve(self, setup):
        vk = setup.vk
        assert _is_valid_g1(vk.alpha1)
        assert _is_valid_g2(vk.beta2)
        assert _is_valid_g2(vk.gamma2)
        assert _is_valid_g2(vk.delta2)
        for pt in vk.ic:
            assert _is_valid_g1(pt)

    def test_pk_points_on_curve(self, setup):
        pk = setup.pk
        assert _is_valid_g1(pk.alpha1)
        assert _is_valid_g1(pk.beta1)
        assert _is_valid_g2(pk.beta2)
        assert _is_valid_g1(pk.delta1)
        assert _is_valid_g2(pk.delta2)
        for pt in pk.u_g1:
            assert _is_valid_g1(pt)
        for pt in pk.v_g1:
            assert _is_valid_g1(pt)
        for pt in pk.v_g2:
            assert _is_valid_g2(pt)
        for pt in pk.w_g1:
            assert _is_valid_g1(pt)

    def test_pk_qap_vectors_correct_length(self, setup):
        pk = setup.pk
        assert len(pk.u) == pk.n_total
        assert len(pk.v) == pk.n_total
        assert len(pk.w) == pk.n_total
        assert pk.n_total == 1 + 3 + 4  # const + 3 pub + 4 wit

    def test_pk_witness_combined_length(self, setup):
        # One combined point per witness element
        assert len(setup.pk.wit_combined_g1) == 4  # n_witness = 4

    def test_deterministic_seed_produces_same_keys(self):
        s1 = TrustedSetup(num_public_inputs=2, num_witness=2, seed=123)
        s2 = TrustedSetup(num_public_inputs=2, num_witness=2, seed=123)
        # VK alpha1 should be identical
        assert g1_to_uint256(s1.vk.alpha1) == g1_to_uint256(s2.vk.alpha1)
        # IC should be identical
        for a, b in zip(s1.vk.ic, s2.vk.ic):
            assert g1_to_uint256(a) == g1_to_uint256(b)

    def test_different_seeds_produce_different_keys(self):
        s1 = TrustedSetup(num_public_inputs=2, num_witness=2, seed=111)
        s2 = TrustedSetup(num_public_inputs=2, num_witness=2, seed=222)
        assert g1_to_uint256(s1.vk.alpha1) != g1_to_uint256(s2.vk.alpha1)

    def test_setup_without_seed_is_random(self):
        s1 = TrustedSetup(num_public_inputs=1, num_witness=1)
        s2 = TrustedSetup(num_public_inputs=1, num_witness=1)
        # Extremely unlikely to be the same
        assert g1_to_uint256(s1.vk.alpha1) != g1_to_uint256(s2.vk.alpha1)

    def test_pk_scalars_are_valid(self, setup):
        pk = setup.pk
        assert 0 < pk.alpha < curve_order
        assert 0 < pk.beta < curve_order
        assert 0 < pk.delta < curve_order
        for u_i in pk.u:
            assert 0 < u_i < curve_order
        for v_i in pk.v:
            assert 0 < v_i < curve_order
        for w_i in pk.w:
            assert 0 < w_i < curve_order

    def test_delta_inv_is_correct(self, setup):
        pk = setup.pk
        assert (pk.delta * pk.delta_inv) % curve_order == 1


# ---------------------------------------------------------------------------
# 2. Scalar Utility Tests
# ---------------------------------------------------------------------------

class TestScalarUtils:
    """Tests for random_scalar and hash_to_scalar."""

    def test_random_scalar_in_range(self):
        for _ in range(20):
            s = random_scalar()
            assert 1 <= s < curve_order

    def test_random_scalar_uniqueness(self):
        scalars = {random_scalar() for _ in range(50)}
        assert len(scalars) == 50

    def test_hash_to_scalar_deterministic(self):
        s1 = hash_to_scalar(b"test", b"data")
        s2 = hash_to_scalar(b"test", b"data")
        assert s1 == s2

    def test_hash_to_scalar_different_inputs(self):
        s1 = hash_to_scalar(b"test1")
        s2 = hash_to_scalar(b"test2")
        assert s1 != s2

    def test_hash_to_scalar_range(self):
        for i in range(20):
            s = hash_to_scalar(i.to_bytes(4, "big"))
            assert 1 <= s < curve_order

    def test_hash_to_scalar_nonzero(self):
        # The function guarantees non-zero output
        for i in range(100):
            s = hash_to_scalar(b"nz", i.to_bytes(8, "big"))
            assert s > 0


# ---------------------------------------------------------------------------
# 3. Proof Generation Tests
# ---------------------------------------------------------------------------

class TestProofGeneration:
    """Tests for Groth16Prover.prove()."""

    def test_proof_has_correct_types(self, valid_proof):
        assert isinstance(valid_proof, Groth16Proof)
        assert valid_proof.A is not None
        assert valid_proof.B is not None
        assert valid_proof.C is not None

    def test_proof_points_on_curve(self, valid_proof):
        assert _is_valid_g1(valid_proof.A)
        assert _is_valid_g2(valid_proof.B)
        assert _is_valid_g1(valid_proof.C)

    def test_proof_points_not_at_infinity(self, valid_proof):
        assert valid_proof.A != Z1
        assert valid_proof.B != Z2
        assert valid_proof.C != Z1

    def test_wrong_public_input_count_raises(self, prover):
        with pytest.raises(ValueError, match="Expected 3 public inputs"):
            prover.prove([1, 2], witness=[1, 2, 3, 4])

    def test_short_witness_padded(self, prover):
        # Should not raise — witness is padded with random values
        proof = prover.prove([1, 2, 3], witness=[1])
        assert _is_valid_g1(proof.A)

    def test_zero_public_inputs(self, prover):
        proof = prover.prove([0, 0, 0], witness=[0, 0, 0, 0])
        assert _is_valid_g1(proof.A)

    def test_large_public_inputs_reduced_mod_order(self, prover):
        # Inputs larger than curve_order should be reduced
        big = curve_order + 42
        proof = prover.prove([big, 0, 0], witness=[1, 2, 3, 4])
        assert _is_valid_g1(proof.A)

    def test_different_inputs_different_proofs(self, prover):
        p1 = prover.prove([1, 2, 3], witness=[4, 5, 6, 7])
        p2 = prover.prove([10, 20, 30], witness=[4, 5, 6, 7])
        # Different inputs → different A points (with overwhelming probability)
        assert g1_to_uint256(p1.A) != g1_to_uint256(p2.A)

    def test_same_inputs_different_proofs_due_to_blinding(self, prover):
        # Same inputs but different random blinding → different proofs
        p1 = prover.prove([1, 2, 3], witness=[4, 5, 6, 7])
        p2 = prover.prove([1, 2, 3], witness=[4, 5, 6, 7])
        # A and C differ due to random r, s
        assert g1_to_uint256(p1.A) != g1_to_uint256(p2.A)


# ---------------------------------------------------------------------------
# 4. Proof Verification Tests (slow — involve pairings)
# ---------------------------------------------------------------------------

class TestProofVerification:
    """Tests for Groth16Verifier.verify()."""

    def test_valid_proof_verifies(self, verifier, valid_proof):
        assert verifier.verify(valid_proof, [100, 200, 300]) is True

    def test_wrong_public_inputs_rejected(self, verifier, valid_proof):
        assert verifier.verify(valid_proof, [101, 200, 300]) is False

    def test_wrong_input_count_rejected(self, verifier, valid_proof):
        assert verifier.verify(valid_proof, [100, 200]) is False

    def test_zero_inputs_proof_verifies(self, setup):
        prover = Groth16Prover(setup.pk)
        verifier = Groth16Verifier(setup.vk)
        proof = prover.prove([0, 0, 0], witness=[0, 0, 0, 0])
        assert verifier.verify(proof, [0, 0, 0]) is True

    def test_max_value_inputs_proof_verifies(self, setup):
        prover = Groth16Prover(setup.pk)
        verifier = Groth16Verifier(setup.vk)
        # curve_order - 1 is the largest valid scalar
        big = curve_order - 1
        proof = prover.prove([big, big, big], witness=[big, big, big, big])
        assert verifier.verify(proof, [big, big, big]) is True

    def test_different_setup_vk_rejects(self, valid_proof):
        # Proof from one setup should not verify with another setup's VK
        other_setup = TrustedSetup(num_public_inputs=3, num_witness=4, seed=999)
        other_verifier = Groth16Verifier(other_setup.vk)
        assert other_verifier.verify(valid_proof, [100, 200, 300]) is False


# ---------------------------------------------------------------------------
# 5. Serialisation Tests
# ---------------------------------------------------------------------------

class TestSerialisation:
    """Tests for proof serialisation/deserialisation."""

    def test_serialize_proof_length(self, valid_proof_bytes):
        assert len(valid_proof_bytes) == 256

    def test_serialize_deserialize_roundtrip(self, valid_proof, valid_proof_bytes):
        recovered = Groth16Prover.deserialize_proof(valid_proof_bytes)
        # Compare coordinate values
        assert g1_to_uint256(recovered.A) == g1_to_uint256(valid_proof.A)
        assert g1_to_uint256(recovered.C) == g1_to_uint256(valid_proof.C)
        # G2 comparison
        (bxi, bxr), (byi, byr) = g2_to_uint256(recovered.B)
        (bxi2, bxr2), (byi2, byr2) = g2_to_uint256(valid_proof.B)
        assert (bxi, bxr, byi, byr) == (bxi2, bxr2, byi2, byr2)

    def test_deserialized_proof_verifies(self, verifier, valid_proof_bytes):
        assert verifier.verify_from_bytes(valid_proof_bytes, [100, 200, 300]) is True

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="256 bytes"):
            Groth16Prover.deserialize_proof(b"\x00" * 128)

    def test_empty_bytes_raises(self):
        with pytest.raises(ValueError, match="256 bytes"):
            Groth16Prover.deserialize_proof(b"")

    def test_random_256_bytes_rejected(self, verifier):
        # Random bytes extremely unlikely to form valid curve points
        random_bytes = os.urandom(256)
        result = verifier.verify_from_bytes(random_bytes, [100, 200, 300])
        assert result is False

    def test_tampered_proof_rejected(self, verifier, valid_proof_bytes):
        tampered = bytearray(valid_proof_bytes)
        tampered[16] ^= 0x01  # flip one bit in A.x
        result = verifier.verify_from_bytes(bytes(tampered), [100, 200, 300])
        assert result is False

    def test_serialize_g1_point(self):
        p = multiply(G1, 42)
        x, y = g1_to_uint256(p)
        assert 0 < x < field_modulus
        assert 0 < y < field_modulus

    def test_serialize_g2_point(self):
        p = multiply(G2, 42)
        (xi, xr), (yi, yr) = g2_to_uint256(p)
        assert all(0 <= v < field_modulus for v in (xi, xr, yi, yr))

    def test_g1_point_at_infinity_raises(self):
        with pytest.raises(ValueError, match="point at infinity"):
            g1_to_uint256(Z1)

    def test_g2_point_at_infinity_raises(self):
        with pytest.raises(ValueError, match="point at infinity"):
            g2_to_uint256(Z2)

    def test_g1_none_raises(self):
        with pytest.raises(ValueError, match="point at infinity"):
            g1_to_uint256(None)


# ---------------------------------------------------------------------------
# 6. VK-to-Solidity Export Tests
# ---------------------------------------------------------------------------

class TestVKToSolidity:
    """Tests for the Solidity constructor argument export."""

    def test_vk_export_has_all_keys(self, setup):
        args = vk_to_solidity_args(setup.vk)
        assert set(args.keys()) == {"alpha", "beta", "gamma", "delta", "ic"}

    def test_alpha_is_g1_pair(self, setup):
        args = vk_to_solidity_args(setup.vk)
        assert len(args["alpha"]) == 2
        assert all(isinstance(v, int) for v in args["alpha"])

    def test_beta_is_g2_pair_of_pairs(self, setup):
        args = vk_to_solidity_args(setup.vk)
        beta = args["beta"]
        assert len(beta) == 2
        assert all(len(pair) == 2 for pair in beta)

    def test_ic_count_matches_inputs_plus_one(self, setup):
        args = vk_to_solidity_args(setup.vk)
        assert len(args["ic"]) == setup.vk.num_public_inputs + 1

    def test_all_values_are_positive_integers(self, setup):
        args = vk_to_solidity_args(setup.vk)
        for x in args["alpha"]:
            assert isinstance(x, int) and x >= 0
        for pair in args["ic"]:
            for x in pair:
                assert isinstance(x, int) and x >= 0


# ---------------------------------------------------------------------------
# 7. Bridge Withdrawal Circuit Tests
# ---------------------------------------------------------------------------

class TestBridgeWithdrawalCircuit:
    """Tests for the withdrawal-specific circuit wrapper."""

    @pytest.fixture(scope="class")
    def circuit(self, setup):
        return BridgeWithdrawalCircuit(setup)

    def test_circuit_requires_3_public_inputs(self):
        small_setup = TrustedSetup(num_public_inputs=2, num_witness=2, seed=1)
        with pytest.raises(ValueError, match="requires >= 3"):
            BridgeWithdrawalCircuit(small_setup)

    def test_derive_public_inputs_deterministic(self):
        pub1 = BridgeWithdrawalCircuit.derive_public_inputs(
            10**18, 1, "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
        )
        pub2 = BridgeWithdrawalCircuit.derive_public_inputs(
            10**18, 1, "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
        )
        assert pub1 == pub2

    def test_derive_public_inputs_format(self):
        pub = BridgeWithdrawalCircuit.derive_public_inputs(
            10**18, 1, "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
        )
        assert len(pub) == 3
        assert all(isinstance(x, int) for x in pub)
        assert all(0 <= x < curve_order for x in pub)

    def test_derive_public_inputs_amount(self):
        pub = BridgeWithdrawalCircuit.derive_public_inputs(42, 7, "0x" + "ab" * 20)
        assert pub[0] == 42  # amount
        assert pub[1] == 7   # nonce

    def test_prove_withdrawal_returns_bytes_and_inputs(self, circuit):
        proof_bytes, pub = circuit.prove_withdrawal(
            amount=10**18,
            nonce=1,
            recipient="0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
            signatures=[b"sig1", b"sig2"],
            state_root=b"\x00" * 32,
        )
        assert isinstance(proof_bytes, bytes)
        assert len(proof_bytes) == 256
        assert isinstance(pub, list)
        assert len(pub) == 3

    def test_prove_and_verify_withdrawal(self, circuit):
        proof_bytes, pub = circuit.prove_withdrawal(
            amount=10**18,
            nonce=1,
            recipient="0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
            signatures=[b"sig1"],
            state_root=b"\xff" * 32,
        )
        assert circuit.verify_withdrawal(proof_bytes, pub) is True

    def test_withdrawal_wrong_amount_rejected(self, circuit):
        proof_bytes, pub = circuit.prove_withdrawal(
            amount=10**18,
            nonce=1,
            recipient="0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
            signatures=[b"sig1"],
            state_root=b"\xff" * 32,
        )
        # Tamper with the amount in public inputs
        tampered_pub = [pub[0] + 1, pub[1], pub[2]]
        assert circuit.verify_withdrawal(proof_bytes, tampered_pub) is False

    def test_different_recipients_different_proofs(self, circuit):
        pb1, _ = circuit.prove_withdrawal(
            10**18, 1, "0x" + "11" * 20, [b"s"], b"\x00" * 32,
        )
        pb2, _ = circuit.prove_withdrawal(
            10**18, 1, "0x" + "22" * 20, [b"s"], b"\x00" * 32,
        )
        assert pb1 != pb2


# ---------------------------------------------------------------------------
# 8. Sync Committee Circuit Tests
# ---------------------------------------------------------------------------

class TestSyncCommitteeCircuit:
    """Tests for the sync committee rotation circuit."""

    @pytest.fixture(scope="class")
    def sync_circuit(self, setup):
        return SyncCommitteeCircuit(setup)

    def test_circuit_requires_2_public_inputs(self):
        small_setup = TrustedSetup(num_public_inputs=1, num_witness=2, seed=1)
        with pytest.raises(ValueError, match="requires >= 2"):
            SyncCommitteeCircuit(small_setup)

    def test_derive_public_inputs(self):
        pub = SyncCommitteeCircuit.derive_public_inputs(
            committee_root=b"\xab" * 32,
            slot=8192000,
        )
        assert len(pub) == 2
        assert pub[1] == 8192000

    def test_prove_and_verify_rotation(self, sync_circuit):
        proof_bytes, pub = sync_circuit.prove_rotation(
            committee_root=b"\xab" * 32,
            slot=8192000,
            old_pubkeys=[b"pk1", b"pk2"],
            new_pubkeys=[b"pk3", b"pk4"],
            aggregate_sig=b"agg_sig",
        )
        assert len(proof_bytes) == 256
        assert sync_circuit.verify_rotation(proof_bytes, pub) is True

    def test_rotation_wrong_slot_rejected(self, sync_circuit):
        proof_bytes, pub = sync_circuit.prove_rotation(
            committee_root=b"\xab" * 32,
            slot=8192000,
            old_pubkeys=[b"pk1"],
            new_pubkeys=[b"pk2"],
            aggregate_sig=b"sig",
        )
        tampered_pub = list(pub)
        tampered_pub[1] = 9999999  # wrong slot
        assert sync_circuit.verify_rotation(proof_bytes, tampered_pub) is False


# ---------------------------------------------------------------------------
# 9. Point Validation Tests
# ---------------------------------------------------------------------------

class TestPointValidation:
    """Tests for _is_valid_g1 and _is_valid_g2."""

    def test_generator_is_valid_g1(self):
        assert _is_valid_g1(G1) is True

    def test_generator_is_valid_g2(self):
        assert _is_valid_g2(G2) is True

    def test_z1_is_invalid_g1(self):
        assert _is_valid_g1(Z1) is False

    def test_z2_is_invalid_g2(self):
        assert _is_valid_g2(Z2) is False

    def test_none_is_invalid(self):
        assert _is_valid_g1(None) is False
        assert _is_valid_g2(None) is False

    def test_scaled_g1_is_valid(self):
        p = multiply(G1, 12345)
        assert _is_valid_g1(p) is True

    def test_scaled_g2_is_valid(self):
        p = multiply(G2, 12345)
        assert _is_valid_g2(p) is True

    def test_random_fq_pair_likely_invalid(self):
        # Random (x, y) almost certainly not on the curve
        p = (FQ(42), FQ(99))
        assert _is_valid_g1(p) is False


# ---------------------------------------------------------------------------
# 10. Curve Order Boundary Tests
# ---------------------------------------------------------------------------

class TestCurveOrderBoundary:
    """Edge cases around the curve order."""

    def test_scalar_at_curve_order_minus_one(self, prover):
        # curve_order - 1 is the max valid scalar
        proof = prover.prove(
            [curve_order - 1, 0, 0],
            witness=[curve_order - 1, 0, 0, 0],
        )
        assert _is_valid_g1(proof.A)

    def test_scalar_at_curve_order_wraps_to_zero(self, prover):
        # curve_order mod curve_order = 0
        proof = prover.prove(
            [curve_order, 0, 0],
            witness=[0, 0, 0, 0],
        )
        # This is equivalent to [0, 0, 0]
        assert _is_valid_g1(proof.A)

    def test_negative_wrap(self, prover):
        # In modular arithmetic, -1 == curve_order - 1
        proof = prover.prove(
            [curve_order - 1, 0, 0],
            witness=[1, 2, 3, 4],
        )
        assert _is_valid_g1(proof.A)

    def test_one_is_valid_input(self, prover, verifier):
        proof = prover.prove([1, 1, 1], witness=[1, 1, 1, 1])
        assert verifier.verify(proof, [1, 1, 1]) is True


# ---------------------------------------------------------------------------
# 11. Security Tests
# ---------------------------------------------------------------------------

class TestSecurity:
    """Tests that invalid/forged proofs are rejected."""

    def test_random_g1_g2_proof_rejected(self, verifier):
        """A proof with random (but valid) curve points should not verify."""
        # Create random curve points
        A = multiply(G1, random_scalar())
        B = multiply(G2, random_scalar())
        C = multiply(G1, random_scalar())
        fake_proof = Groth16Proof(A=A, B=B, C=C)
        assert verifier.verify(fake_proof, [100, 200, 300]) is False

    def test_swapped_A_C_rejected(self, verifier, valid_proof):
        """Swapping A and C should invalidate the proof."""
        swapped = Groth16Proof(A=valid_proof.C, B=valid_proof.B, C=valid_proof.A)
        assert verifier.verify(swapped, [100, 200, 300]) is False

    def test_negated_A_rejected(self, verifier, valid_proof):
        """Negating A should invalidate the proof."""
        negated = Groth16Proof(A=neg(valid_proof.A), B=valid_proof.B, C=valid_proof.C)
        assert verifier.verify(negated, [100, 200, 300]) is False

    def test_proof_from_different_witness_valid(self, prover, verifier):
        """Different witnesses (same public inputs) produce different but valid proofs."""
        p1 = prover.prove([42, 0, 0], witness=[1, 2, 3, 4])
        p2 = prover.prove([42, 0, 0], witness=[5, 6, 7, 8])
        assert verifier.verify(p1, [42, 0, 0]) is True
        assert verifier.verify(p2, [42, 0, 0]) is True
        # But the proofs should differ
        assert g1_to_uint256(p1.A) != g1_to_uint256(p2.A)


# ---------------------------------------------------------------------------
# 12. E2E Integration Tests
# ---------------------------------------------------------------------------

class TestE2EIntegration:
    """End-to-end tests combining setup, prove, verify, and serialise."""

    def test_full_flow_small_setup(self):
        """Minimal setup (1 pub, 1 wit) full flow."""
        setup = TrustedSetup(num_public_inputs=1, num_witness=1, seed=7)
        prover = Groth16Prover(setup.pk)
        verifier = Groth16Verifier(setup.vk)

        proof = prover.prove([42], witness=[99])
        assert verifier.verify(proof, [42]) is True
        assert verifier.verify(proof, [43]) is False

    def test_full_flow_large_setup(self):
        """Larger setup (5 pub, 8 wit) full flow."""
        setup = TrustedSetup(num_public_inputs=5, num_witness=8, seed=77)
        prover = Groth16Prover(setup.pk)
        verifier = Groth16Verifier(setup.vk)

        pub = [111, 222, 333, 444, 555]
        wit = [1, 2, 3, 4, 5, 6, 7, 8]
        proof = prover.prove(pub, witness=wit)
        assert verifier.verify(proof, pub) is True

        # Serialize roundtrip
        proof_bytes = Groth16Prover.serialize_proof(proof)
        assert len(proof_bytes) == 256
        assert verifier.verify_from_bytes(proof_bytes, pub) is True

    def test_vk_export_for_solidity_deployment(self, setup):
        """VK can be exported and used for mock contract deployment."""
        args = vk_to_solidity_args(setup.vk)
        # Verify the exported values match the VK
        alpha_x, alpha_y = g1_to_uint256(setup.vk.alpha1)
        assert args["alpha"] == [alpha_x, alpha_y]
        assert len(args["ic"]) == 4  # 3 pub + 1 constant
