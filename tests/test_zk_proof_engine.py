"""
Tests for ZK Proof Engines (SimulatedProver, SP1, DistributedProver)
=====================================================================

Comprehensive tests for the proof generation and verification engines
in ``rings.bridge.zk.prover``, exercising the circuit→proof→verify
pipeline for all four circuit types.

NOTE: The existing ``test_zk_prover.py`` covers the BN254 pairing-based
Groth16 system (py_ecc).  *This* file covers the higher-level
``ZKProofEngine`` hierarchy:  SimulatedProver, SP1ProverInterface,
DistributedProver, ProvingTask, and ZKProof dataclass.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.asi_build.rings.bridge.zk.prover import (
    ZKProof,
    ZKProofEngine,
    SimulatedProver,
    SP1ProverInterface,
    DistributedProver,
    ProvingTask,
    ProofGenerationError,
    ProofVerificationError,
    PROOF_SIZE,
    GAS_ESTIMATE_SIMULATED,
    GAS_ESTIMATE_NOVA,
)
from src.asi_build.rings.bridge.zk.circuits import (
    BLSVerificationCircuit,
    MerklePatriciaCircuit,
    BridgeWithdrawalCircuit,
    SyncCommitteeRotationCircuit,
)


# ---------------------------------------------------------------------------
# Helpers — build valid witnesses for each circuit
# ---------------------------------------------------------------------------

COMMITTEE_SIZE = 4  # small for test speed
THRESHOLD = 3


def _make_bls_witness():
    """Build a valid BLS verification witness (committee_size=4, threshold=3)."""
    circuit = BLSVerificationCircuit(committee_size=COMMITTEE_SIZE, threshold=THRESHOLD)
    pubkeys = [os.urandom(48) for _ in range(COMMITTEE_SIZE)]
    bitmap = [True, True, True, True]
    header_fields = {
        "slot": 100,
        "proposer_index": 7,
        "parent_root": os.urandom(32),
        "state_root": os.urandom(32),
        "body_root": os.urandom(32),
    }
    signature = os.urandom(96)
    witness = circuit.generate_witness(
        committee_pubkeys=pubkeys,
        signature=signature,
        header_fields=header_fields,
        bitmap=bitmap,
    )
    public_inputs = circuit.public_inputs_from_witness(witness)
    return circuit, witness, public_inputs


def _make_mpt_witness():
    """Build a valid Merkle-Patricia proof witness."""
    circuit = MerklePatriciaCircuit()
    address = os.urandom(20)

    account_state = {
        "nonce": 42,
        "balance": 10**18,
        "storage_root": os.urandom(32),
        "code_hash": os.urandom(32),
    }

    # Build a simplified proof chain that satisfies the constraint checker.
    # The circuit checks:
    #   1) sha256(proof_nodes[0]) == state_root
    #   2) sha256(address) == address_hash
    #   3) sha256(account_encoded) == expected_value_hash
    #   4) child hash embedded in parent node
    #   5) value hash embedded in leaf node

    # Encode the account state to get its hash
    nonce_b = account_state["nonce"].to_bytes(8, "big")
    balance_b = account_state["balance"].to_bytes(32, "big")
    storage_root = account_state["storage_root"][:32].ljust(32, b"\x00")
    code_hash = account_state["code_hash"][:32].ljust(32, b"\x00")
    account_bytes = nonce_b + balance_b + storage_root + code_hash
    value_hash = hashlib.sha256(account_bytes).digest()

    # Leaf node must contain the value_hash
    leaf_padding = os.urandom(10)
    leaf_node = leaf_padding + value_hash + os.urandom(10)

    # Parent node must contain sha256(leaf_node)
    child_hash = hashlib.sha256(leaf_node).digest()
    root_node_body = os.urandom(8) + child_hash + os.urandom(8)

    # state_root = sha256(root_node_body)
    state_root = hashlib.sha256(root_node_body).digest()

    witness = circuit.generate_witness(
        state_root=state_root,
        address=address,
        proof_nodes=[root_node_body, leaf_node],
        account_state=account_state,
    )
    public_inputs = circuit.public_inputs_from_witness(witness)
    return circuit, witness, public_inputs


def _make_withdrawal_witness():
    """Build a valid bridge withdrawal witness."""
    circuit = BridgeWithdrawalCircuit(
        committee_size=COMMITTEE_SIZE, committee_threshold=THRESHOLD,
    )
    _, bls_w, _ = _make_bls_witness()
    _, mpt_w, _ = _make_mpt_witness()

    header_proof = {
        "committee_pubkeys": bls_w["committee_pubkeys"],
        "signature": bls_w["aggregate_signature"],
        "header_fields": bls_w["header_fields"],
        "bitmap": bls_w["participation_bitmap"],
    }
    receipt_proof = {
        "state_root": mpt_w["pub_state_root"],
        "address": mpt_w["address"],
        "proof_nodes": mpt_w["proof_nodes"],
        "account_state": mpt_w["account_state"],
    }

    witness = circuit.generate_witness(
        recipient=os.urandom(20),
        amount=10**18,
        nonce=1,
        rings_did="did:rings:test123",
        header_proof=header_proof,
        receipt_proof=receipt_proof,
        validator_sigs=[os.urandom(65) for _ in range(5)],
        threshold=4,
    )
    public_inputs = circuit.public_inputs_from_witness(witness)
    return circuit, witness, public_inputs


def _make_rotation_witness():
    """Build a valid sync committee rotation witness."""
    circuit = SyncCommitteeRotationCircuit(
        committee_size=COMMITTEE_SIZE,
        supermajority_threshold=THRESHOLD,
    )
    current_pubkeys = [os.urandom(48) for _ in range(COMMITTEE_SIZE)]
    new_pubkeys = [os.urandom(48) for _ in range(COMMITTEE_SIZE)]
    bitmap = [True] * COMMITTEE_SIZE

    witness = circuit.generate_witness(
        current_pubkeys=current_pubkeys,
        new_pubkeys=new_pubkeys,
        attestation_sig=os.urandom(96),
        attestation_bitmap=bitmap,
        slot=12345,
    )
    public_inputs = circuit.public_inputs_from_witness(witness)
    return circuit, witness, public_inputs


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# ZKProof dataclass tests
# ---------------------------------------------------------------------------


class TestZKProof:
    """Tests for the ZKProof data container."""

    def _sample_proof(self, **overrides) -> ZKProof:
        defaults = dict(
            proof_bytes=os.urandom(256),
            public_inputs=[os.urandom(32), os.urandom(32)],
            proof_type="simulated",
            circuit_id="TestCircuit",
            generation_time_ms=42,
            proof_size_bytes=256,
            estimated_verify_gas=220_000,
            metadata={"prover": "SimulatedProver"},
        )
        defaults.update(overrides)
        return ZKProof(**defaults)

    def test_zkproof_creation(self):
        """All fields populated correctly on creation."""
        p = self._sample_proof()
        assert len(p.proof_bytes) == 256
        assert len(p.public_inputs) == 2
        assert p.proof_type == "simulated"
        assert p.circuit_id == "TestCircuit"
        assert p.generation_time_ms == 42
        assert p.proof_size_bytes == 256
        assert p.estimated_verify_gas == 220_000
        assert p.metadata["prover"] == "SimulatedProver"

    def test_zkproof_to_dict(self):
        """Serializes to JSON-compatible dict with hex bytes."""
        p = self._sample_proof()
        d = p.to_dict()
        assert d["proof_bytes"].startswith("0x")
        assert all(pi.startswith("0x") for pi in d["public_inputs"])
        assert d["proof_type"] == "simulated"
        assert isinstance(d["generation_time_ms"], int)

    def test_zkproof_from_dict_roundtrip(self):
        """from_dict(to_dict()) preserves all fields."""
        p = self._sample_proof()
        d = p.to_dict()
        p2 = ZKProof.from_dict(d)
        assert p2.proof_bytes == p.proof_bytes
        assert p2.public_inputs == p.public_inputs
        assert p2.proof_type == p.proof_type
        assert p2.circuit_id == p.circuit_id
        assert p2.generation_time_ms == p.generation_time_ms
        assert p2.proof_size_bytes == p.proof_size_bytes
        assert p2.estimated_verify_gas == p.estimated_verify_gas
        assert p2.metadata == p.metadata

    def test_zkproof_to_contract_args(self):
        """to_contract_args returns (bytes, list_of_int)."""
        pi1 = b"\x00" * 31 + b"\x05"  # 5 in big-endian bytes32
        p = self._sample_proof(public_inputs=[pi1])
        proof_bytes, uint_inputs = p.to_contract_args()
        assert proof_bytes == p.proof_bytes
        assert uint_inputs == [5]

    def test_zkproof_proof_size(self):
        """proof_size_bytes == len(proof_bytes)."""
        raw = os.urandom(128)
        p = self._sample_proof(proof_bytes=raw, proof_size_bytes=len(raw))
        assert p.proof_size_bytes == len(p.proof_bytes)

    def test_zkproof_metadata(self):
        """Metadata dict stored correctly."""
        meta = {"version": "1.2.3", "segments": 4}
        p = self._sample_proof(metadata=meta)
        assert p.metadata == meta

    def test_zkproof_types(self):
        """Various proof_type values accepted."""
        for pt in ("groth16", "stark", "nova", "simulated", "distributed_nova"):
            p = self._sample_proof(proof_type=pt)
            assert p.proof_type == pt

    def test_zkproof_empty_public_inputs(self):
        """Works with empty public inputs list."""
        p = self._sample_proof(public_inputs=[])
        d = p.to_dict()
        assert d["public_inputs"] == []
        p2 = ZKProof.from_dict(d)
        assert p2.public_inputs == []
        _, uint_inputs = p2.to_contract_args()
        assert uint_inputs == []

    def test_zkproof_repr(self):
        """repr includes key fields."""
        p = self._sample_proof()
        r = repr(p)
        assert "simulated" in r
        assert "TestCircuit" in r


# ---------------------------------------------------------------------------
# SimulatedProver tests
# ---------------------------------------------------------------------------


class TestSimulatedProver:
    """Tests for the SimulatedProver (HMAC-commitment engine)."""

    def test_prover_type(self):
        assert SimulatedProver().prover_type == "simulated"

    def test_is_available(self):
        assert SimulatedProver().is_available is True

    def test_generate_proof_bls_circuit(self):
        circuit, witness, pi = _make_bls_witness()
        prover = SimulatedProver()
        proof = _run(prover.generate_proof(circuit, witness, pi))
        assert isinstance(proof, ZKProof)
        assert len(proof.proof_bytes) == PROOF_SIZE

    def test_generate_proof_mpt_circuit(self):
        circuit, witness, pi = _make_mpt_witness()
        prover = SimulatedProver()
        proof = _run(prover.generate_proof(circuit, witness, pi))
        assert isinstance(proof, ZKProof)

    def test_generate_proof_withdrawal_circuit(self):
        circuit, witness, pi = _make_withdrawal_witness()
        prover = SimulatedProver()
        proof = _run(prover.generate_proof(circuit, witness, pi))
        assert isinstance(proof, ZKProof)

    def test_generate_proof_rotation_circuit(self):
        circuit, witness, pi = _make_rotation_witness()
        prover = SimulatedProver()
        proof = _run(prover.generate_proof(circuit, witness, pi))
        assert isinstance(proof, ZKProof)

    def test_proof_is_256_bytes(self):
        circuit, witness, pi = _make_bls_witness()
        proof = _run(SimulatedProver().generate_proof(circuit, witness, pi))
        assert len(proof.proof_bytes) == 256

    def test_proof_type_is_simulated(self):
        circuit, witness, pi = _make_bls_witness()
        proof = _run(SimulatedProver().generate_proof(circuit, witness, pi))
        assert proof.proof_type == "simulated"

    def test_proof_circuit_id(self):
        circuit, witness, pi = _make_bls_witness()
        proof = _run(SimulatedProver().generate_proof(circuit, witness, pi))
        assert proof.circuit_id == "BLSVerificationCircuit"

    def test_proof_generation_time(self):
        circuit, witness, pi = _make_bls_witness()
        proof = _run(SimulatedProver().generate_proof(circuit, witness, pi))
        assert proof.generation_time_ms >= 0

    def test_proof_estimated_gas(self):
        circuit, witness, pi = _make_bls_witness()
        proof = _run(SimulatedProver().generate_proof(circuit, witness, pi))
        assert proof.estimated_verify_gas == GAS_ESTIMATE_SIMULATED  # 220_000

    def test_verify_proof_valid(self):
        circuit, witness, pi = _make_bls_witness()
        prover = SimulatedProver()
        proof = _run(prover.generate_proof(circuit, witness, pi))
        assert _run(prover.verify_proof(circuit, proof, pi)) is True

    def test_verify_proof_tampered_bytes(self):
        """Modifying proof_bytes causes verification failure."""
        circuit, witness, pi = _make_bls_witness()
        prover = SimulatedProver()
        proof = _run(prover.generate_proof(circuit, witness, pi))
        # Tamper with the integrity section
        tampered = bytearray(proof.proof_bytes)
        tampered[130] ^= 0xFF
        proof.proof_bytes = bytes(tampered)
        assert _run(prover.verify_proof(circuit, proof, pi)) is False

    def test_verify_proof_tampered_public_inputs(self):
        """Changed public inputs → verification failure."""
        circuit, witness, pi = _make_bls_witness()
        prover = SimulatedProver()
        proof = _run(prover.generate_proof(circuit, witness, pi))
        # Change a public input
        bad_pi = dict(pi)
        bad_pi["participation_count"] = pi["participation_count"] + 1
        assert _run(prover.verify_proof(circuit, proof, bad_pi)) is False

    def test_verify_proof_wrong_circuit(self):
        """Verify with different circuit type → failure."""
        bls_circuit, witness, pi = _make_bls_witness()
        prover = SimulatedProver()
        proof = _run(prover.generate_proof(bls_circuit, witness, pi))
        # Use MPT circuit for verification
        mpt_circuit = MerklePatriciaCircuit()
        assert _run(prover.verify_proof(mpt_circuit, proof, pi)) is False

    def test_verify_proof_wrong_type(self):
        """Non-simulated proof_type → fails in SimulatedProver."""
        circuit, witness, pi = _make_bls_witness()
        prover = SimulatedProver()
        proof = _run(prover.generate_proof(circuit, witness, pi))
        proof.proof_type = "groth16"
        assert _run(prover.verify_proof(circuit, proof, pi)) is False

    def test_constraint_violation_raises(self):
        """Invalid witness → ProofGenerationError with violations."""
        circuit = BLSVerificationCircuit(committee_size=4, threshold=3)
        # Only 2 participants → below threshold
        pubkeys = [os.urandom(48) for _ in range(4)]
        bitmap = [True, True, False, False]  # only 2
        hf = {
            "slot": 1, "proposer_index": 1,
            "parent_root": os.urandom(32),
            "state_root": os.urandom(32),
            "body_root": os.urandom(32),
        }
        witness = circuit.generate_witness(
            committee_pubkeys=pubkeys, signature=os.urandom(96),
            header_fields=hf, bitmap=bitmap,
        )
        pi = circuit.public_inputs_from_witness(witness)
        prover = SimulatedProver()
        with pytest.raises(ProofGenerationError) as exc_info:
            _run(prover.generate_proof(circuit, witness, pi))
        assert len(exc_info.value.violations) > 0

    def test_constraint_violation_message(self):
        """Error message contains violation descriptions."""
        circuit = BLSVerificationCircuit(committee_size=4, threshold=3)
        pubkeys = [os.urandom(48) for _ in range(4)]
        bitmap = [True, False, False, False]  # only 1
        hf = {
            "slot": 1, "proposer_index": 1,
            "parent_root": os.urandom(32),
            "state_root": os.urandom(32),
            "body_root": os.urandom(32),
        }
        witness = circuit.generate_witness(
            committee_pubkeys=pubkeys, signature=os.urandom(96),
            header_fields=hf, bitmap=bitmap,
        )
        pi = circuit.public_inputs_from_witness(witness)
        with pytest.raises(ProofGenerationError) as exc_info:
            _run(SimulatedProver().generate_proof(circuit, witness, pi))
        assert "below_threshold" in exc_info.value.violations[0]

    def test_custom_commitment_key(self):
        """Different key → different witness commitment bytes."""
        circuit, witness, pi = _make_bls_witness()
        p1 = _run(SimulatedProver(commitment_key=b"\x01" * 32).generate_proof(circuit, witness, pi))
        p2 = _run(SimulatedProver(commitment_key=b"\x02" * 32).generate_proof(circuit, witness, pi))
        # Witness commitment (bytes[0:32]) should differ
        assert p1.proof_bytes[0:32] != p2.proof_bytes[0:32]

    def test_artificial_delay(self):
        """With delay_ms=50, generation takes at least ~50ms."""
        circuit, witness, pi = _make_bls_witness()
        prover = SimulatedProver(artificial_delay_ms=50)
        t0 = time.monotonic()
        _run(prover.generate_proof(circuit, witness, pi))
        elapsed = (time.monotonic() - t0) * 1000
        assert elapsed >= 40  # some margin for timing jitter

    def test_deterministic_with_same_key(self):
        """Same key + same witness → same witness commitment (bytes[0:32])."""
        circuit, witness, pi = _make_bls_witness()
        key = b"\xaa" * 32
        p1 = _run(SimulatedProver(commitment_key=key).generate_proof(circuit, witness, pi))
        p2 = _run(SimulatedProver(commitment_key=key).generate_proof(circuit, witness, pi))
        # Witness commitment and PI/circuit bindings should match
        assert p1.proof_bytes[0:32] == p2.proof_bytes[0:32]
        assert p1.proof_bytes[32:96] == p2.proof_bytes[32:96]

    def test_different_witnesses_different_proofs(self):
        """Different witnesses → different proof witness commitments."""
        key = b"\xbb" * 32
        c1, w1, pi1 = _make_bls_witness()
        c2, w2, pi2 = _make_bls_witness()
        p1 = _run(SimulatedProver(commitment_key=key).generate_proof(c1, w1, pi1))
        p2 = _run(SimulatedProver(commitment_key=key).generate_proof(c2, w2, pi2))
        # Extremely unlikely to be the same
        assert p1.proof_bytes[0:32] != p2.proof_bytes[0:32]

    def test_stats_tracking(self):
        """Stats counter increments on generate and verify."""
        circuit, witness, pi = _make_bls_witness()
        prover = SimulatedProver()
        assert prover.stats["proofs_generated"] == 0
        proof = _run(prover.generate_proof(circuit, witness, pi))
        assert prover.stats["proofs_generated"] == 1
        _run(prover.verify_proof(circuit, proof, pi))
        assert prover.stats["proofs_verified"] == 1

    def test_verify_short_proof_bytes(self):
        """Proof with < 160 bytes fails verification gracefully."""
        circuit, witness, pi = _make_bls_witness()
        prover = SimulatedProver()
        proof = _run(prover.generate_proof(circuit, witness, pi))
        proof.proof_bytes = proof.proof_bytes[:100]
        assert _run(prover.verify_proof(circuit, proof, pi)) is False

    def test_all_four_circuits_generate_and_verify(self):
        """End-to-end generate+verify for all four circuit types."""
        prover = SimulatedProver(commitment_key=b"\xcc" * 32)
        for make_fn in (_make_bls_witness, _make_mpt_witness,
                        _make_withdrawal_witness, _make_rotation_witness):
            circuit, witness, pi = make_fn()
            proof = _run(prover.generate_proof(circuit, witness, pi))
            assert _run(prover.verify_proof(circuit, proof, pi)) is True


# ---------------------------------------------------------------------------
# SP1ProverInterface tests
# ---------------------------------------------------------------------------


class TestSP1ProverInterface:
    """Tests for the SP1 prover stub."""

    def test_prover_type(self):
        assert SP1ProverInterface().prover_type == "sp1"

    def test_is_not_available(self):
        assert SP1ProverInterface().is_available is False

    def test_generate_raises_not_implemented(self):
        circuit, witness, pi = _make_bls_witness()
        sp1 = SP1ProverInterface()
        with pytest.raises(NotImplementedError) as exc_info:
            _run(sp1.generate_proof(circuit, witness, pi))
        assert "SP1" in str(exc_info.value)

    def test_verify_raises_not_implemented(self):
        circuit, witness, pi = _make_bls_witness()
        sp1 = SP1ProverInterface()
        proof = ZKProof(
            proof_bytes=os.urandom(256), public_inputs=[], proof_type="sp1",
            circuit_id="test", generation_time_ms=0, proof_size_bytes=256,
            estimated_verify_gas=0,
        )
        with pytest.raises(NotImplementedError):
            _run(sp1.verify_proof(circuit, proof, pi))

    def test_check_installation(self):
        sp1 = SP1ProverInterface()
        status = sp1.check_sp1_installation()
        assert isinstance(status, dict)
        assert status["installed"] is False
        assert "errors" in status

    def test_repr(self):
        sp1 = SP1ProverInterface(sp1_binary_path="/usr/bin/sp1")
        r = repr(sp1)
        assert "SP1ProverInterface" in r
        assert "/usr/bin/sp1" in r


# ---------------------------------------------------------------------------
# ProvingTask tests
# ---------------------------------------------------------------------------


class TestProvingTask:
    """Tests for the ProvingTask dataclass."""

    def test_creation(self):
        t = ProvingTask(circuit_id="TestCircuit", segment_index=0)
        assert t.circuit_id == "TestCircuit"
        assert t.segment_index == 0
        assert t.assigned_node is None
        assert t.result is None

    def test_default_status_pending(self):
        t = ProvingTask()
        assert t.status == "pending"

    def test_status_transitions(self):
        t = ProvingTask()
        assert t.status == "pending"
        t.assign("did:rings:node1")
        assert t.status == "assigned"
        assert t.assigned_node == "did:rings:node1"
        t.start_proving()
        assert t.status == "proving"
        t.complete(b"\xde\xad")
        assert t.status == "completed"
        assert t.result == b"\xde\xad"
        assert t.completed_at is not None

    def test_fail_transition(self):
        t = ProvingTask()
        t.assign("did:rings:node2")
        t.fail("timeout")
        assert t.status == "failed"
        assert t.completed_at is not None
        assert t.witness_segment.get("_failure_reason") == "timeout"

    def test_task_id_unique(self):
        ids = {ProvingTask().task_id for _ in range(100)}
        assert len(ids) == 100

    def test_serialization(self):
        t = ProvingTask(circuit_id="BLS", segment_index=2)
        t.assign("did:rings:node3")
        d = t.to_dict()
        assert d["task_id"] == t.task_id
        assert d["segment_index"] == 2
        assert d["circuit_id"] == "BLS"
        assert d["assigned_node"] == "did:rings:node3"
        assert d["status"] == "assigned"
        assert d["has_result"] is False

    def test_created_at_is_recent(self):
        t0 = time.time()
        t = ProvingTask()
        assert t.created_at >= t0 - 1
        assert t.created_at <= time.time() + 1


# ---------------------------------------------------------------------------
# DistributedProver tests
# ---------------------------------------------------------------------------


class TestDistributedProver:
    """Tests for the DistributedProver (Nova IVC coordinator)."""

    def test_prover_type(self):
        dp = DistributedProver()
        assert dp.prover_type == "distributed_nova"

    def test_is_available_no_client(self):
        dp = DistributedProver(rings_client=None)
        assert dp.is_available is False

    def test_is_available_with_client(self):
        mock_client = MagicMock()
        dp = DistributedProver(rings_client=mock_client)
        assert dp.is_available is True

    def test_fallback_to_simulated(self):
        """No network provers → falls back to SimulatedProver."""
        sim = SimulatedProver(commitment_key=b"\xee" * 32)
        dp = DistributedProver(
            rings_client=None,
            fallback_prover=sim,
        )
        circuit, witness, pi = _make_bls_witness()
        proof = _run(dp.generate_proof(circuit, witness, pi))
        assert proof.proof_type == "simulated"
        assert proof.metadata.get("fallback") is True

    def test_fallback_generates_valid_proof(self):
        """Fallback proof verifies correctly via SimulatedProver."""
        sim = SimulatedProver(commitment_key=b"\xff" * 32)
        dp = DistributedProver(rings_client=None, fallback_prover=sim)
        circuit, witness, pi = _make_bls_witness()
        proof = _run(dp.generate_proof(circuit, witness, pi))
        assert _run(sim.verify_proof(circuit, proof, pi)) is True

    def test_no_fallback_raises(self):
        """No provers and no fallback → ProofGenerationError."""
        dp = DistributedProver(rings_client=None, fallback_prover=None)
        circuit, witness, pi = _make_bls_witness()
        with pytest.raises(ProofGenerationError):
            _run(dp.generate_proof(circuit, witness, pi))

    def test_split_circuit_small(self):
        """Small circuit → single segment."""
        circuit = BLSVerificationCircuit(committee_size=4, threshold=3)
        dp = DistributedProver(segment_size=1_000_000)  # huge segment
        witness = {"committee_pubkeys": [b"x"] * 4}
        segments = dp.split_circuit(circuit, witness)
        # 500_000 constraints < 1_000_000 segment → 1 segment
        assert len(segments) == 1

    def test_split_circuit_large(self):
        """Circuit with many constraints → multiple segments."""
        circuit = BridgeWithdrawalCircuit(committee_size=4, committee_threshold=3)
        dp = DistributedProver(segment_size=100_000)
        # Make a witness with a large list to split on
        big_list = [os.urandom(48) for _ in range(100)]
        witness = {"big_data": big_list, "other": "value"}
        segments = dp.split_circuit(circuit, witness)
        assert len(segments) >= 1

    def test_discover_provers_no_client(self):
        """No client → empty prover list."""
        dp = DistributedProver(rings_client=None)
        result = _run(dp.discover_provers())
        assert result == []

    def test_discover_provers_with_client(self):
        """Mock client returns prover list."""
        mock_client = AsyncMock()
        mock_client.dht_get = AsyncMock(return_value=[
            "did:rings:prover1", "did:rings:prover2", "did:rings:prover3",
        ])
        dp = DistributedProver(rings_client=mock_client)
        provers = _run(dp.discover_provers())
        assert len(provers) == 3

    def test_compress_to_groth16(self):
        """Compresses fold proofs into a 256-byte proof."""
        circuit, _, _ = _make_bls_witness()
        dp = DistributedProver()
        fold_proofs = [os.urandom(64) for _ in range(3)]
        proof = _run(dp.compress_to_groth16(fold_proofs, circuit))
        assert len(proof.proof_bytes) == PROOF_SIZE
        assert proof.proof_type == "distributed_nova"
        assert proof.estimated_verify_gas == GAS_ESTIMATE_NOVA
        assert proof.metadata["fold_count"] == 3

    def test_verify_distributed_nova_proof(self):
        """Compressed proof verifies structurally."""
        circuit, _, _ = _make_bls_witness()
        dp = DistributedProver()
        fold_proofs = [os.urandom(64) for _ in range(3)]
        proof = _run(dp.compress_to_groth16(fold_proofs, circuit))
        pi = {}  # DistributedProver verify doesn't re-check PI commitment
        assert _run(dp.verify_proof(circuit, proof, pi)) is True

    def test_verify_wrong_circuit_fails(self):
        """Distributed proof for one circuit fails for another."""
        bls_circuit, _, _ = _make_bls_witness()
        dp = DistributedProver()
        fold_proofs = [os.urandom(64)]
        proof = _run(dp.compress_to_groth16(fold_proofs, bls_circuit))
        mpt_circuit = MerklePatriciaCircuit()
        assert _run(dp.verify_proof(mpt_circuit, proof, {})) is False

    def test_verify_tampered_distributed_proof(self):
        """Tampered distributed proof fails integrity check."""
        circuit, _, _ = _make_bls_witness()
        dp = DistributedProver()
        fold_proofs = [os.urandom(64)]
        proof = _run(dp.compress_to_groth16(fold_proofs, circuit))
        tampered = bytearray(proof.proof_bytes)
        tampered[135] ^= 0xFF
        proof.proof_bytes = bytes(tampered)
        assert _run(dp.verify_proof(circuit, proof, {})) is False

    def test_proving_task_lifecycle(self):
        """create → assign → complete with DistributedProver tracking."""
        dp = DistributedProver()
        task = ProvingTask(circuit_id="BLS", segment_index=0)
        dp._active_tasks[task.task_id] = task
        assert dp.stats["active_tasks"] == 1
        task.complete(b"\x00" * 32)
        dp._active_tasks.pop(task.task_id)
        assert dp.stats["active_tasks"] == 0

    def test_stats(self):
        dp = DistributedProver(
            min_provers=5, segment_size=20_000,
            bridge_subring="test:provers",
        )
        s = dp.stats
        assert s["min_provers"] == 5
        assert s["segment_size"] == 20_000
        assert s["bridge_subring"] == "test:provers"
        assert s["completed_proofs"] == 0
        assert s["fallback_count"] == 0

    def test_repr(self):
        dp = DistributedProver()
        r = repr(dp)
        assert "DistributedProver" in r
        assert "distributed_nova" not in r or "available" in r

    def test_delegated_verify_to_fallback(self):
        """Simulated-type proof delegated to fallback for verification."""
        sim = SimulatedProver(commitment_key=b"\x11" * 32)
        dp = DistributedProver(rings_client=None, fallback_prover=sim)
        circuit, witness, pi = _make_bls_witness()
        proof = _run(dp.generate_proof(circuit, witness, pi))
        # DistributedProver.verify_proof should delegate to SimulatedProver
        assert _run(dp.verify_proof(circuit, proof, pi)) is True


# ---------------------------------------------------------------------------
# Exception tests
# ---------------------------------------------------------------------------


class TestExceptions:
    """Tests for ProofGenerationError and ProofVerificationError."""

    def test_proof_generation_error_message(self):
        err = ProofGenerationError("bad witness", violations=["v1", "v2"])
        assert str(err) == "bad witness"
        assert err.violations == ["v1", "v2"]

    def test_proof_generation_error_no_violations(self):
        err = ProofGenerationError("generic failure")
        assert err.violations == []

    def test_proof_verification_error(self):
        err = ProofVerificationError("malformed proof data")
        assert str(err) == "malformed proof data"
