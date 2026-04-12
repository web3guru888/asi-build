"""Tests for ZK circuit definitions.

Covers BLSVerificationCircuit, MerklePatriciaCircuit,
BridgeWithdrawalCircuit, SyncCommitteeRotationCircuit,
plus general Circuit ABC and ALL_CIRCUITS convenience list.
"""

import hashlib
import os
import struct
from abc import ABC

import pytest

from src.asi_build.rings.bridge.zk.circuits import (
    ALL_CIRCUITS,
    BLSVerificationCircuit,
    BridgeWithdrawalCircuit,
    Circuit,
    CircuitMetadata,
    MerklePatriciaCircuit,
    SyncCommitteeRotationCircuit,
    _concat_bytes_list,
    _hash_header_fields,
    _sha256,
    _to_bytes20,
    _to_bytes32,
)


# ---------------------------------------------------------------------------
# Helpers — reusable fixture builders
# ---------------------------------------------------------------------------

def _make_pubkeys(n: int = 512) -> list[bytes]:
    """Generate *n* deterministic 48-byte 'public keys'."""
    return [hashlib.sha256(i.to_bytes(4, "big")).digest() + b"\xaa" * 16 for i in range(n)]


def _make_header_fields(slot: int = 1000, proposer: int = 42) -> dict:
    return {
        "slot": slot,
        "proposer_index": proposer,
        "parent_root": os.urandom(32),
        "state_root": os.urandom(32),
        "body_root": os.urandom(32),
    }


def _make_bls_witness(
    committee_size: int = 512,
    participation: int = 400,
    sig_len: int = 96,
    header_fields: dict | None = None,
) -> dict:
    """Build kwargs suitable for BLSVerificationCircuit.generate_witness."""
    pubkeys = _make_pubkeys(committee_size)
    bitmap = [True] * participation + [False] * (committee_size - participation)
    if header_fields is None:
        header_fields = _make_header_fields()
    return {
        "committee_pubkeys": pubkeys,
        "signature": os.urandom(sig_len),
        "header_fields": header_fields,
        "bitmap": bitmap,
    }


def _make_mpt_witness_kwargs(chained: bool = True) -> dict:
    """Build kwargs suitable for MerklePatriciaCircuit.generate_witness.

    If *chained*, the proof nodes are constructed so that each parent node
    embeds the SHA-256 of its child node (constraint 4 passes).
    """
    address = os.urandom(20)
    account_state = {
        "nonce": 5,
        "balance": 10 ** 18,
        "storage_root": os.urandom(32),
        "code_hash": os.urandom(32),
    }
    # Build proof nodes bottom-up so that hashes chain.
    leaf_data = _sha256(MerklePatriciaCircuit._encode_account_state(account_state))
    leaf_node = os.urandom(10) + leaf_data + os.urandom(10)  # value hash embedded

    if chained:
        mid_node = os.urandom(5) + _sha256(leaf_node) + os.urandom(5)
        root_node_body = os.urandom(5) + _sha256(mid_node) + os.urandom(5)
        proof_nodes = [root_node_body, mid_node, leaf_node]
    else:
        proof_nodes = [leaf_node]

    state_root = _sha256(proof_nodes[0])

    return {
        "state_root": state_root,
        "address": address,
        "proof_nodes": proof_nodes,
        "account_state": account_state,
    }


def _make_bridge_withdrawal_kwargs(
    participation: int = 400,
    validator_count: int = 6,
    threshold: int = 4,
    amount: int = 10 ** 18,
    nonce: int = 1,
) -> dict:
    """Build kwargs suitable for BridgeWithdrawalCircuit.generate_witness."""
    header_fields = _make_header_fields()
    header_proof = _make_bls_witness(participation=participation, header_fields=header_fields)
    receipt_proof = _make_mpt_witness_kwargs(chained=True)

    return {
        "recipient": os.urandom(20),
        "amount": amount,
        "nonce": nonce,
        "rings_did": "did:rings:test123",
        "header_proof": header_proof,
        "receipt_proof": receipt_proof,
        "validator_sigs": [os.urandom(64) for _ in range(validator_count)],
        "threshold": threshold,
    }


def _make_rotation_kwargs(
    committee_size: int = 512,
    attestation_count: int = 400,
    slot: int = 256_000,
) -> dict:
    current = _make_pubkeys(committee_size)
    new = [hashlib.sha256(b"new" + i.to_bytes(4, "big")).digest() + b"\xbb" * 16 for i in range(committee_size)]
    bitmap = [True] * attestation_count + [False] * (committee_size - attestation_count)
    return {
        "current_pubkeys": current,
        "new_pubkeys": new,
        "attestation_sig": os.urandom(96),
        "attestation_bitmap": bitmap,
        "slot": slot,
    }


# ===================================================================
# BLSVerificationCircuit
# ===================================================================

class TestBLSVerificationCircuit:

    def test_metadata(self):
        c = BLSVerificationCircuit()
        m = c.metadata()
        assert m.name == "BLSVerificationCircuit"
        assert m.estimated_constraints == 500_000
        assert m.num_public_inputs == 3
        assert m.num_witness_fields == 5
        assert m.version == "0.1.0"

    def test_generate_witness_valid(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=400)
        w = c.generate_witness(**kw)
        assert "pub_sync_committee_root" in w
        assert "pub_block_header_hash" in w
        assert "pub_participation_count" in w
        assert w["pub_participation_count"] == 400
        assert "committee_pubkeys" in w
        assert "aggregate_signature" in w
        assert "participation_bitmap" in w
        assert "header_fields" in w

    def test_verify_constraints_valid(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=400)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is True
        assert violations == []

    def test_threshold_check_below_342(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=300)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("below_threshold" in v for v in violations)

    def test_under_threshold_341(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=341)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("below_threshold" in v for v in violations)

    def test_exact_threshold_342(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=342)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is True
        assert violations == []

    def test_wrong_committee_size(self):
        """100 pubkeys instead of 512 -> committee_size_mismatch violation."""
        c = BLSVerificationCircuit(committee_size=512)
        kw = _make_bls_witness(committee_size=100, participation=100)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("committee_size_mismatch" in v for v in violations)

    def test_wrong_committee_root(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=400)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        # Tamper with the committee root
        pub["sync_committee_root"] = os.urandom(32)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("committee_root_mismatch" in v for v in violations)

    def test_wrong_header_hash(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=400)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        pub["block_header_hash"] = os.urandom(32)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("header_hash_mismatch" in v for v in violations)

    def test_empty_signature(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=400, sig_len=96)
        w = c.generate_witness(**kw)
        # Replace the signature with empty bytes
        w["aggregate_signature"] = b""
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("signature_length" in v for v in violations)

    def test_short_signature(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=400)
        w = c.generate_witness(**kw)
        w["aggregate_signature"] = os.urandom(48)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("signature_length" in v for v in violations)

    def test_public_inputs_from_witness(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=400)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        assert set(pub.keys()) == {"sync_committee_root", "block_header_hash", "participation_count"}
        assert pub["sync_committee_root"] == w["pub_sync_committee_root"]
        assert pub["block_header_hash"] == w["pub_block_header_hash"]
        assert pub["participation_count"] == 400

    def test_estimate_constraints(self):
        c = BLSVerificationCircuit()
        assert c.estimate_constraints() == 500_000

    def test_custom_committee_size_and_threshold(self):
        c = BLSVerificationCircuit(committee_size=128, threshold=86)
        pubkeys = _make_pubkeys(128)
        bitmap = [True] * 86 + [False] * 42
        hf = _make_header_fields()
        w = c.generate_witness(
            committee_pubkeys=pubkeys, signature=os.urandom(96),
            header_fields=hf, bitmap=bitmap,
        )
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is True
        assert violations == []

    def test_participation_count_mismatch(self):
        c = BLSVerificationCircuit()
        kw = _make_bls_witness(participation=400)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        # Tamper with participation count
        pub["participation_count"] = 500
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("participation_count_mismatch" in v for v in violations)


# ===================================================================
# MerklePatriciaCircuit
# ===================================================================

class TestMerklePatriciaCircuit:

    def test_metadata(self):
        c = MerklePatriciaCircuit()
        m = c.metadata()
        assert m.name == "MerklePatriciaCircuit"
        assert m.estimated_constraints == 100_000
        assert m.num_public_inputs == 3

    def test_generate_witness_valid(self):
        c = MerklePatriciaCircuit()
        kw = _make_mpt_witness_kwargs(chained=True)
        w = c.generate_witness(**kw)
        assert "pub_state_root" in w
        assert "pub_address_hash" in w
        assert "pub_expected_value_hash" in w
        assert "proof_nodes" in w
        assert "account_state" in w
        assert "key_path" in w

    def test_verify_constraints_valid_chain(self):
        c = MerklePatriciaCircuit()
        kw = _make_mpt_witness_kwargs(chained=True)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is True, f"Expected valid, got violations: {violations}"
        assert violations == []

    def test_verify_constraints_root_mismatch(self):
        c = MerklePatriciaCircuit()
        kw = _make_mpt_witness_kwargs(chained=True)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        pub["state_root"] = os.urandom(32)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("root_mismatch" in v for v in violations)

    def test_address_hash_mismatch(self):
        c = MerklePatriciaCircuit()
        kw = _make_mpt_witness_kwargs(chained=True)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        pub["address_hash"] = os.urandom(32)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("address_hash_mismatch" in v for v in violations)

    def test_value_hash_mismatch(self):
        c = MerklePatriciaCircuit()
        kw = _make_mpt_witness_kwargs(chained=True)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        pub["expected_value_hash"] = os.urandom(32)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("value_hash_mismatch" in v for v in violations)

    def test_empty_proof_nodes(self):
        c = MerklePatriciaCircuit()
        kw = _make_mpt_witness_kwargs(chained=True)
        w = c.generate_witness(**kw)
        w["proof_nodes"] = []
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("empty_proof" in v for v in violations)

    def test_single_proof_node(self):
        """Single node proof (leaf only) should work if hashes match."""
        c = MerklePatriciaCircuit()
        kw = _make_mpt_witness_kwargs(chained=False)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is True, f"Single-node proof should pass, got: {violations}"

    def test_public_inputs_extraction(self):
        c = MerklePatriciaCircuit()
        kw = _make_mpt_witness_kwargs(chained=True)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        assert set(pub.keys()) == {"state_root", "address_hash", "expected_value_hash"}

    def test_estimate_constraints(self):
        c = MerklePatriciaCircuit()
        assert c.estimate_constraints() == 100_000

    def test_chain_break_detected(self):
        """Tamper with a middle proof node so the hash chain breaks."""
        c = MerklePatriciaCircuit()
        kw = _make_mpt_witness_kwargs(chained=True)
        w = c.generate_witness(**kw)
        # Replace mid node with random bytes (breaks chain from root to mid)
        w["proof_nodes"][1] = os.urandom(50)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("chain_break" in v for v in violations)

    def test_key_path_length(self):
        """Key path should be 64 nibbles (2 nibbles per byte of 32-byte hash)."""
        c = MerklePatriciaCircuit()
        kw = _make_mpt_witness_kwargs()
        w = c.generate_witness(**kw)
        assert len(w["key_path"]) == 64


# ===================================================================
# BridgeWithdrawalCircuit
# ===================================================================

class TestBridgeWithdrawalCircuit:

    def test_metadata(self):
        c = BridgeWithdrawalCircuit()
        m = c.metadata()
        assert m.name == "BridgeWithdrawalCircuit"
        assert m.estimated_constraints == 700_000
        assert m.num_public_inputs == 6
        assert m.num_witness_fields == 8

    def test_generate_witness_complete(self):
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs()
        w = c.generate_witness(**kw)
        expected_keys = {
            "pub_recipient", "pub_amount", "pub_nonce", "pub_rings_did_hash",
            "pub_block_header_hash", "pub_state_root",
            "bls_witness", "mpt_witness",
            "validator_signatures", "validator_threshold", "deposit_log_data",
        }
        assert expected_keys.issubset(set(w.keys()))

    def test_verify_constraints_valid(self):
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs()
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is True, f"Expected valid, got violations: {violations}"

    def test_zero_amount(self):
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs(amount=0)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("non_positive_amount" in v for v in violations)

    def test_negative_nonce(self):
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs(nonce=1)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        # Tamper the nonce to be negative in public inputs
        pub["nonce"] = -1
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("negative_nonce" in v for v in violations)

    def test_insufficient_validators(self):
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs(validator_count=2, threshold=4)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("validator_threshold" in v for v in violations)

    def test_empty_validator_sigs(self):
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs(validator_count=0, threshold=4)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("validator_threshold" in v for v in violations)

    def test_public_inputs_hash_deterministic(self):
        c = BridgeWithdrawalCircuit()
        recipient = b"\x11" * 20
        amount = 10 ** 18
        nonce = 42
        did = "did:rings:alice"
        h1 = c.public_inputs_hash(recipient, amount, nonce, did)
        h2 = c.public_inputs_hash(recipient, amount, nonce, did)
        assert h1 == h2
        assert len(h1) == 32

    def test_public_inputs_hash_different_recipients(self):
        c = BridgeWithdrawalCircuit()
        h1 = c.public_inputs_hash(b"\x11" * 20, 1000, 1, "did:rings:a")
        h2 = c.public_inputs_hash(b"\x22" * 20, 1000, 1, "did:rings:a")
        assert h1 != h2

    def test_public_inputs_hash_different_amounts(self):
        c = BridgeWithdrawalCircuit()
        h1 = c.public_inputs_hash(b"\x11" * 20, 1000, 1, "did:rings:a")
        h2 = c.public_inputs_hash(b"\x11" * 20, 2000, 1, "did:rings:a")
        assert h1 != h2

    def test_public_inputs_from_witness(self):
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs()
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        assert set(pub.keys()) == {
            "recipient", "amount", "nonce", "rings_did_hash",
            "block_header_hash", "state_root",
        }
        assert pub["amount"] == kw["amount"]

    def test_sub_circuit_bls_delegation(self):
        """BLS sub-constraints are delegated: wrong committee size -> bls: violation."""
        c = BridgeWithdrawalCircuit(committee_size=512)
        kw = _make_bridge_withdrawal_kwargs()
        # Shrink the committee in the header proof to trigger BLS mismatch
        kw["header_proof"]["committee_pubkeys"] = _make_pubkeys(100)
        kw["header_proof"]["bitmap"] = [True] * 100
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any(v.startswith("bls:") for v in violations)

    def test_sub_circuit_mpt_delegation(self):
        """MPT sub-constraints: empty proof nodes -> mpt: violation."""
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs()
        kw["receipt_proof"]["proof_nodes"] = []
        # Need to recalculate state_root to avoid other violations
        # But the point is the mpt sub-circuit catches empty proof
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any(v.startswith("mpt:") for v in violations)

    def test_estimate_constraints(self):
        c = BridgeWithdrawalCircuit()
        assert c.estimate_constraints() == 700_000

    def test_witness_contains_header_proof(self):
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs()
        w = c.generate_witness(**kw)
        bls_w = w["bls_witness"]
        assert "pub_sync_committee_root" in bls_w
        assert "pub_block_header_hash" in bls_w

    def test_witness_contains_receipt_proof(self):
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs()
        w = c.generate_witness(**kw)
        mpt_w = w["mpt_witness"]
        assert "pub_state_root" in mpt_w
        assert "pub_address_hash" in mpt_w

    def test_deposit_log_data_encoding(self):
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs(amount=5000)
        w = c.generate_witness(**kw)
        expected = _to_bytes20(kw["recipient"]) + (5000).to_bytes(32, "big")
        assert w["deposit_log_data"] == expected

    def test_validator_sig_with_empty_bytes(self):
        """One of the validator sigs is empty -> violation."""
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs(validator_count=5, threshold=4)
        w = c.generate_witness(**kw)
        # Replace one sig with empty bytes
        w["validator_signatures"][2] = b""
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("empty_signature" in v for v in violations)

    def test_rings_did_bytes_input(self):
        """rings_did as bytes (not str) should work."""
        c = BridgeWithdrawalCircuit()
        kw = _make_bridge_withdrawal_kwargs()
        kw["rings_did"] = b"\xde\xad\xbe\xef" * 8
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        assert len(pub["rings_did_hash"]) == 32


# ===================================================================
# SyncCommitteeRotationCircuit
# ===================================================================

class TestSyncCommitteeRotationCircuit:

    def test_metadata(self):
        c = SyncCommitteeRotationCircuit()
        m = c.metadata()
        assert m.name == "SyncCommitteeRotationCircuit"
        assert m.estimated_constraints == 600_000
        assert m.num_public_inputs == 3

    def test_generate_witness_valid(self):
        c = SyncCommitteeRotationCircuit()
        kw = _make_rotation_kwargs(attestation_count=400)
        w = c.generate_witness(**kw)
        assert "pub_current_committee_root" in w
        assert "pub_new_committee_root" in w
        assert "pub_attested_slot" in w
        assert "current_pubkeys" in w
        assert "new_pubkeys" in w
        assert "attestation_signature" in w
        assert "attestation_bitmap" in w

    def test_verify_constraints_valid(self):
        c = SyncCommitteeRotationCircuit()
        kw = _make_rotation_kwargs(attestation_count=400)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is True, f"Expected valid, got: {violations}"
        assert violations == []

    def test_wrong_current_root(self):
        c = SyncCommitteeRotationCircuit()
        kw = _make_rotation_kwargs()
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        pub["current_committee_root"] = os.urandom(32)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("current_root_mismatch" in v for v in violations)

    def test_wrong_new_root(self):
        c = SyncCommitteeRotationCircuit()
        kw = _make_rotation_kwargs()
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        pub["new_committee_root"] = os.urandom(32)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("new_root_mismatch" in v for v in violations)

    def test_insufficient_attestation(self):
        c = SyncCommitteeRotationCircuit()
        kw = _make_rotation_kwargs(attestation_count=300)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("below_supermajority" in v for v in violations)

    def test_exact_threshold_342(self):
        c = SyncCommitteeRotationCircuit()
        kw = _make_rotation_kwargs(attestation_count=342)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is True

    def test_below_threshold_341(self):
        c = SyncCommitteeRotationCircuit()
        kw = _make_rotation_kwargs(attestation_count=341)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("below_supermajority" in v for v in violations)

    def test_wrong_current_committee_size(self):
        c = SyncCommitteeRotationCircuit(committee_size=512)
        kw = _make_rotation_kwargs(committee_size=100, attestation_count=100)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("current_size_mismatch" in v for v in violations)

    def test_wrong_new_committee_size(self):
        c = SyncCommitteeRotationCircuit(committee_size=512)
        kw = _make_rotation_kwargs(committee_size=512, attestation_count=400)
        w = c.generate_witness(**kw)
        # Shrink new_pubkeys to trigger size mismatch
        w["new_pubkeys"] = w["new_pubkeys"][:100]
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("new_size_mismatch" in v for v in violations)

    def test_slot_mismatch(self):
        c = SyncCommitteeRotationCircuit()
        kw = _make_rotation_kwargs(slot=256_000)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        pub["attested_slot"] = 999_999
        ok, violations = c.verify_constraints(w, pub)
        assert ok is False
        assert any("slot_mismatch" in v for v in violations)

    def test_public_inputs_extraction(self):
        c = SyncCommitteeRotationCircuit()
        kw = _make_rotation_kwargs(slot=42)
        w = c.generate_witness(**kw)
        pub = c.public_inputs_from_witness(w)
        assert set(pub.keys()) == {"current_committee_root", "new_committee_root", "attested_slot"}
        assert pub["attested_slot"] == 42

    def test_estimate_constraints(self):
        c = SyncCommitteeRotationCircuit()
        assert c.estimate_constraints() == 600_000

    def test_custom_committee_size(self):
        c = SyncCommitteeRotationCircuit(committee_size=64, supermajority_threshold=43)
        current = [hashlib.sha256(i.to_bytes(4, "big")).digest() + b"\xcc" * 16 for i in range(64)]
        new = [hashlib.sha256(b"n" + i.to_bytes(4, "big")).digest() + b"\xdd" * 16 for i in range(64)]
        bitmap = [True] * 43 + [False] * 21
        w = c.generate_witness(
            current_pubkeys=current, new_pubkeys=new,
            attestation_sig=os.urandom(96), attestation_bitmap=bitmap, slot=100,
        )
        pub = c.public_inputs_from_witness(w)
        ok, violations = c.verify_constraints(w, pub)
        assert ok is True


# ===================================================================
# General / ABC / ALL_CIRCUITS
# ===================================================================

class TestGeneral:

    def test_all_circuits_list(self):
        assert len(ALL_CIRCUITS) == 4
        assert BLSVerificationCircuit in ALL_CIRCUITS
        assert MerklePatriciaCircuit in ALL_CIRCUITS
        assert BridgeWithdrawalCircuit in ALL_CIRCUITS
        assert SyncCommitteeRotationCircuit in ALL_CIRCUITS

    def test_circuit_abc_cannot_instantiate(self):
        with pytest.raises(TypeError):
            Circuit()  # type: ignore[abstract]

    def test_all_circuits_have_metadata(self):
        instances = [
            BLSVerificationCircuit(),
            MerklePatriciaCircuit(),
            BridgeWithdrawalCircuit(),
            SyncCommitteeRotationCircuit(),
        ]
        for inst in instances:
            m = inst.metadata()
            assert isinstance(m, CircuitMetadata)
            assert m.name
            assert m.estimated_constraints > 0
            assert m.num_public_inputs > 0

    def test_circuit_metadata_fields(self):
        m = CircuitMetadata(
            name="Test", version="1.0.0", estimated_constraints=100,
            num_public_inputs=2, num_witness_fields=3, description="A test circuit.",
        )
        assert m.name == "Test"
        assert m.version == "1.0.0"
        assert m.estimated_constraints == 100
        assert m.description == "A test circuit."

    def test_different_committee_sizes_bls(self):
        """BLSVerificationCircuit with custom committee size."""
        for size in [32, 64, 256]:
            threshold = (size * 2) // 3 + 1
            c = BLSVerificationCircuit(committee_size=size, threshold=threshold)
            assert c.committee_size == size
            assert c.threshold == threshold


# ===================================================================
# Helper function edge cases
# ===================================================================

class TestHelpers:

    def test_sha256(self):
        assert _sha256(b"hello") == hashlib.sha256(b"hello").digest()

    def test_to_bytes32_from_short(self):
        result = _to_bytes32(b"\x01")
        assert len(result) == 32
        assert result[0] == 1
        assert result[1:] == b"\x00" * 31

    def test_to_bytes32_from_hex_string(self):
        hex_str = "0x" + "ab" * 32
        result = _to_bytes32(hex_str)
        assert len(result) == 32
        assert result == b"\xab" * 32

    def test_to_bytes20_from_hex_string(self):
        hex_str = "0x" + "ff" * 20
        result = _to_bytes20(hex_str)
        assert len(result) == 20
        assert result == b"\xff" * 20

    def test_concat_bytes_list(self):
        items = [b"abc", b"de"]
        result = _concat_bytes_list(items)
        # Each item prefixed with 4-byte big-endian length
        expected = struct.pack(">I", 3) + b"abc" + struct.pack(">I", 2) + b"de"
        assert result == expected

    def test_hash_header_fields_deterministic(self):
        h1 = _hash_header_fields(100, 5, b"\x00" * 32, b"\x01" * 32, b"\x02" * 32)
        h2 = _hash_header_fields(100, 5, b"\x00" * 32, b"\x01" * 32, b"\x02" * 32)
        assert h1 == h2
        assert len(h1) == 32

    def test_hash_header_fields_different_slots(self):
        h1 = _hash_header_fields(100, 5, b"\x00" * 32, b"\x01" * 32, b"\x02" * 32)
        h2 = _hash_header_fields(101, 5, b"\x00" * 32, b"\x01" * 32, b"\x02" * 32)
        assert h1 != h2
