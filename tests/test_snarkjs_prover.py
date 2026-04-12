"""Tests for the real Groth16 ZK proof engine (snarkjs + circom).

Tests range from unit tests for encoding/decoding to integration tests
that generate and verify real Groth16 proofs on the BN254 curve.

Requirements:
    - Node.js with snarkjs installed globally
    - Compiled circuit artifacts in /shared/asi-build/circuits/build/
    - circomlib and poseidon-lite in circuits/node_modules/
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the package is importable
sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "src")
)

from asi_build.rings.bridge.zk.snarkjs_prover import (
    BN254_FIELD_ORDER,
    DEFAULT_CIRCUITS_DIR,
    GROTH16_VERIFY_GAS,
    SnarkJSProver,
    WithdrawalWitness,
    _stringify_inputs,
    compute_withdrawal_witness,
    poseidon_hash,
)
from asi_build.rings.bridge.zk.prover import (
    ProofGenerationError,
    ProofVerificationError,
    ZKProof,
    ZKProofEngine,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CIRCUITS_DIR = Path("/shared/asi-build/circuits")
BUILD_DIR = CIRCUITS_DIR / "build"


def _snarkjs_available() -> bool:
    """Check if snarkjs + circuit artifacts are available."""
    try:
        r = subprocess.run(
            ["snarkjs", "--version"],
            capture_output=True,
            timeout=5,
        )
        # snarkjs --version returns exit code 99 but prints version info
        has_snarkjs = b"snarkjs" in r.stdout or b"snarkjs" in r.stderr
        return (
            has_snarkjs
            and (BUILD_DIR / "withdrawal_final.zkey").exists()
            and (BUILD_DIR / "withdrawal_js" / "withdrawal.wasm").exists()
        )
    except Exception:
        return False


def _node_available() -> bool:
    """Check if node + poseidon-lite are available."""
    try:
        r = subprocess.run(
            [
                "node",
                "-e",
                'require("poseidon-lite"); console.log("ok")',
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(CIRCUITS_DIR),
        )
        return r.returncode == 0 and "ok" in r.stdout
    except Exception:
        return False


SNARKJS_AVAILABLE = _snarkjs_available()
NODE_AVAILABLE = _node_available()

skip_no_snarkjs = pytest.mark.skipif(
    not SNARKJS_AVAILABLE,
    reason="snarkjs or circuit artifacts not available",
)
skip_no_node = pytest.mark.skipif(
    not NODE_AVAILABLE,
    reason="node or poseidon-lite not available",
)


@pytest.fixture
def prover():
    """Create a SnarkJSProver instance."""
    return SnarkJSProver(circuits_dir=CIRCUITS_DIR)


@pytest.fixture
def mock_circuit():
    """Create a mock Circuit object."""
    c = MagicMock()
    c.name = "withdrawal"
    return c


@pytest.fixture
def sample_proof_data():
    """Sample snarkjs proof.json data."""
    return {
        "pi_a": [
            "21431209929377312836974376715976240814510128295884212848526094472617294023841",
            "4095412068241057880971148561190453110104364175971120918791781384902276508016",
            "1",
        ],
        "pi_b": [
            [
                "10379200183431987672439439067124041903711582283556133942518649052640214235753",
                "1861540490904301119093404931798261457337422439709562375028597454303320457650",
            ],
            [
                "16369688626715233434909861955111604534627217688415669372672354355575614134851",
                "12549895292165083796776300221772018109166850271674929833542485543373558398660",
            ],
            ["1", "0"],
        ],
        "pi_c": [
            "15935612244044686812898502155084132997689487080932549758116009972260220811155",
            "8330120734171576484346486359142462420359813621931845282591686015239494912782",
            "1",
        ],
        "protocol": "groth16",
        "curve": "bn128",
    }


# ---------------------------------------------------------------------------
# Unit tests: SnarkJSProver basics
# ---------------------------------------------------------------------------


class TestSnarkJSProverBasics:
    """Basic unit tests for SnarkJSProver."""

    def test_prover_type(self, prover):
        assert prover.prover_type == "groth16_snarkjs"

    def test_is_subclass_of_engine(self, prover):
        assert isinstance(prover, ZKProofEngine)

    @skip_no_snarkjs
    def test_is_available(self, prover):
        assert prover.is_available is True

    def test_not_available_bad_dir(self):
        p = SnarkJSProver(circuits_dir="/nonexistent/path")
        assert p.is_available is False

    def test_repr(self, prover):
        r = repr(prover)
        assert "SnarkJSProver" in r
        assert "withdrawal" in r

    def test_default_circuits_dir(self):
        # DEFAULT_CIRCUITS_DIR should resolve to something sensible
        assert isinstance(DEFAULT_CIRCUITS_DIR, Path)

    def test_stats_initial(self, prover):
        stats = prover.stats
        assert stats["prover_type"] == "groth16_snarkjs"
        assert stats["proofs_generated"] == 0
        assert stats["proofs_verified"] == 0
        assert stats["avg_gen_time_ms"] == 0
        assert stats["circuit_name"] == "withdrawal"

    def test_bn254_field_order(self):
        # Well-known BN254 scalar field prime
        assert BN254_FIELD_ORDER == (
            21888242871839275222246405745257275088548364400416034343698204186575808495617
        )

    def test_groth16_gas_estimate(self):
        assert GROTH16_VERIFY_GAS == 230_000


# ---------------------------------------------------------------------------
# Unit tests: proof encoding/decoding
# ---------------------------------------------------------------------------


class TestProofEncoding:
    """Tests for proof bytes encoding and decoding."""

    def test_encode_proof(self, sample_proof_data):
        proof_bytes = SnarkJSProver._encode_proof(sample_proof_data)
        assert len(proof_bytes) == 256
        assert isinstance(proof_bytes, bytes)

    def test_decode_proof(self, sample_proof_data):
        proof_bytes = SnarkJSProver._encode_proof(sample_proof_data)
        decoded = SnarkJSProver._decode_proof(proof_bytes)

        assert decoded["protocol"] == "groth16"
        assert decoded["curve"] == "bn128"
        assert decoded["pi_a"][0] == sample_proof_data["pi_a"][0]
        assert decoded["pi_a"][1] == sample_proof_data["pi_a"][1]
        assert decoded["pi_a"][2] == "1"
        assert decoded["pi_b"][0][0] == sample_proof_data["pi_b"][0][0]
        assert decoded["pi_b"][0][1] == sample_proof_data["pi_b"][0][1]
        assert decoded["pi_b"][1][0] == sample_proof_data["pi_b"][1][0]
        assert decoded["pi_b"][1][1] == sample_proof_data["pi_b"][1][1]
        assert decoded["pi_c"][0] == sample_proof_data["pi_c"][0]
        assert decoded["pi_c"][1] == sample_proof_data["pi_c"][1]

    def test_encode_decode_roundtrip(self, sample_proof_data):
        """Encode → decode must preserve all field elements."""
        proof_bytes = SnarkJSProver._encode_proof(sample_proof_data)
        decoded = SnarkJSProver._decode_proof(proof_bytes)
        re_encoded = SnarkJSProver._encode_proof(decoded)
        assert proof_bytes == re_encoded

    def test_encode_zero_proof(self):
        """All-zero proof should encode to 256 zero bytes."""
        zero_proof = {
            "pi_a": ["0", "0", "1"],
            "pi_b": [["0", "0"], ["0", "0"], ["1", "0"]],
            "pi_c": ["0", "0", "1"],
            "protocol": "groth16",
            "curve": "bn128",
        }
        proof_bytes = SnarkJSProver._encode_proof(zero_proof)
        assert proof_bytes == b"\x00" * 256

    def test_encode_max_field_elements(self):
        """Max BN254 field elements should fit in 32 bytes."""
        max_val = str(BN254_FIELD_ORDER - 1)
        proof = {
            "pi_a": [max_val, max_val, "1"],
            "pi_b": [
                [max_val, max_val],
                [max_val, max_val],
                ["1", "0"],
            ],
            "pi_c": [max_val, max_val, "1"],
            "protocol": "groth16",
            "curve": "bn128",
        }
        proof_bytes = SnarkJSProver._encode_proof(proof)
        assert len(proof_bytes) == 256

    def test_decode_invalid_length(self):
        """Decode with wrong length should raise."""
        with pytest.raises(AssertionError):
            SnarkJSProver._decode_proof(b"\x00" * 128)


# ---------------------------------------------------------------------------
# Unit tests: calldata formatting
# ---------------------------------------------------------------------------


class TestCalldataFormatting:
    """Tests for Solidity calldata formatting."""

    def test_format_calldata(self, sample_proof_data):
        proof_bytes = SnarkJSProver._encode_proof(sample_proof_data)
        public_data = [
            "100",
            "1",
            "8115236278915580287033870785443340863078946943991125563411906784305589881962",
            "3305197735301507071566117782537473216135263344381086466045543627147954894876",
        ]
        public_bytes = [int(s).to_bytes(32, "big") for s in public_data]

        zk_proof = ZKProof(
            proof_bytes=proof_bytes,
            public_inputs=public_bytes,
            proof_type="groth16",
            circuit_id="withdrawal",
            generation_time_ms=100,
            proof_size_bytes=256,
            estimated_verify_gas=230_000,
            metadata={
                "raw_proof": sample_proof_data,
                "raw_public": public_data,
            },
        )

        pb, pi = SnarkJSProver.format_calldata(zk_proof)
        assert pb == proof_bytes
        assert len(pi) == 4

    def test_format_calldata_snarkjs(self, sample_proof_data):
        public_data = ["100", "1", "123456", "789012"]
        proof_bytes = SnarkJSProver._encode_proof(sample_proof_data)
        public_bytes = [int(s).to_bytes(32, "big") for s in public_data]

        zk_proof = ZKProof(
            proof_bytes=proof_bytes,
            public_inputs=public_bytes,
            proof_type="groth16",
            circuit_id="withdrawal",
            generation_time_ms=100,
            proof_size_bytes=256,
            estimated_verify_gas=230_000,
            metadata={
                "raw_proof": sample_proof_data,
                "raw_public": public_data,
            },
        )

        cd = SnarkJSProver.format_calldata_snarkjs(zk_proof)
        assert "a" in cd
        assert "b" in cd
        assert "c" in cd
        assert "input" in cd
        assert len(cd["a"]) == 2
        assert len(cd["b"]) == 2
        assert len(cd["b"][0]) == 2
        assert len(cd["c"]) == 2
        assert len(cd["input"]) == 4

        # Verify hex format
        assert all(s.startswith("0x") for s in cd["a"])
        assert all(s.startswith("0x") for s in cd["input"])


# ---------------------------------------------------------------------------
# Unit tests: WithdrawalWitness
# ---------------------------------------------------------------------------


class TestWithdrawalWitness:
    """Tests for the WithdrawalWitness dataclass."""

    def test_basic_creation(self):
        w = WithdrawalWitness(
            amount=100,
            nonce=1,
            recipient_hash=12345,
            state_root=67890,
            secret=42,
            balance=1000,
            path_elements=[100, 101, 102],
            path_indices=[0, 1, 0],
        )
        assert w.amount == 100
        assert w.balance == 1000

    def test_to_circuit_inputs(self):
        w = WithdrawalWitness(
            amount=100,
            nonce=1,
            recipient_hash=12345,
            state_root=67890,
            secret=42,
            balance=1000,
            path_elements=[100, 101],
            path_indices=[0, 1],
        )
        witness, public = w.to_circuit_inputs()

        assert public["amount"] == 100
        assert public["nonce"] == 1
        assert public["recipientHash"] == 12345
        assert public["stateRoot"] == 67890
        assert witness["secret"] == 42
        assert witness["balance"] == 1000
        assert witness["pathElements"] == [100, 101]
        assert witness["pathIndices"] == [0, 1]

    def test_validate_valid(self):
        w = WithdrawalWitness(
            amount=100,
            nonce=1,
            recipient_hash=12345,
            state_root=67890,
            secret=42,
            balance=1000,
            path_elements=[100, 101],
            path_indices=[0, 1],
        )
        errors = w.validate()
        assert errors == []

    def test_validate_insufficient_balance(self):
        w = WithdrawalWitness(
            amount=2000,
            nonce=1,
            recipient_hash=12345,
            state_root=67890,
            secret=42,
            balance=1000,
            path_elements=[100],
            path_indices=[0],
        )
        errors = w.validate()
        assert any("exceeds balance" in e for e in errors)

    def test_validate_negative_amount(self):
        w = WithdrawalWitness(
            amount=-1,
            nonce=1,
            recipient_hash=12345,
            state_root=67890,
            secret=42,
            balance=1000,
            path_elements=[100],
            path_indices=[0],
        )
        errors = w.validate()
        assert any("negative amount" in e for e in errors)

    def test_validate_path_length_mismatch(self):
        w = WithdrawalWitness(
            amount=100,
            nonce=1,
            recipient_hash=12345,
            state_root=67890,
            secret=42,
            balance=1000,
            path_elements=[100, 101, 102],
            path_indices=[0, 1],
        )
        errors = w.validate()
        assert any("mismatch" in e for e in errors)

    def test_validate_bad_path_indices(self):
        w = WithdrawalWitness(
            amount=100,
            nonce=1,
            recipient_hash=12345,
            state_root=67890,
            secret=42,
            balance=1000,
            path_elements=[100],
            path_indices=[2],  # Invalid: must be 0 or 1
        )
        errors = w.validate()
        assert any("0 or 1" in e for e in errors)

    def test_validate_overflow_balance_diff(self):
        w = WithdrawalWitness(
            amount=0,
            nonce=1,
            recipient_hash=12345,
            state_root=67890,
            secret=42,
            balance=2**65,  # Exceeds 64-bit range
            path_elements=[100],
            path_indices=[0],
        )
        errors = w.validate()
        assert any("64-bit" in e for e in errors)


# ---------------------------------------------------------------------------
# Unit tests: helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    """Tests for utility functions."""

    def test_stringify_inputs_ints(self):
        result = _stringify_inputs({"a": 42, "b": 100})
        assert result == {"a": "42", "b": "100"}

    def test_stringify_inputs_lists(self):
        result = _stringify_inputs({"a": [1, 2, 3]})
        assert result == {"a": ["1", "2", "3"]}

    def test_stringify_inputs_strings(self):
        result = _stringify_inputs({"a": "hello"})
        assert result == {"a": "hello"}

    def test_stringify_inputs_mixed(self):
        result = _stringify_inputs(
            {"amount": 100, "path": [1, 2], "name": "test"}
        )
        assert result == {
            "amount": "100",
            "path": ["1", "2"],
            "name": "test",
        }


# ---------------------------------------------------------------------------
# Integration tests: Poseidon hash
# ---------------------------------------------------------------------------


class TestPoseidonHash:
    """Tests for Poseidon hash computation via Node.js."""

    @skip_no_node
    @pytest.mark.asyncio
    async def test_poseidon2(self):
        """Poseidon(1, 2) should return a deterministic result."""
        result = await poseidon_hash(
            [1, 2], circuits_dir=CIRCUITS_DIR
        )
        assert isinstance(result, int)
        assert result > 0
        assert result < BN254_FIELD_ORDER

    @skip_no_node
    @pytest.mark.asyncio
    async def test_poseidon3(self):
        """Poseidon(42, 1000, 1) — the leaf hash for test inputs."""
        result = await poseidon_hash(
            [42, 1000, 1], circuits_dir=CIRCUITS_DIR
        )
        assert isinstance(result, int)
        assert result > 0

    @skip_no_node
    @pytest.mark.asyncio
    async def test_poseidon_deterministic(self):
        """Same inputs → same output."""
        h1 = await poseidon_hash([42, 1000, 1], circuits_dir=CIRCUITS_DIR)
        h2 = await poseidon_hash([42, 1000, 1], circuits_dir=CIRCUITS_DIR)
        assert h1 == h2

    @skip_no_node
    @pytest.mark.asyncio
    async def test_poseidon_different_inputs(self):
        """Different inputs → different output."""
        h1 = await poseidon_hash([1, 2], circuits_dir=CIRCUITS_DIR)
        h2 = await poseidon_hash([2, 1], circuits_dir=CIRCUITS_DIR)
        assert h1 != h2

    @skip_no_node
    @pytest.mark.asyncio
    async def test_poseidon_known_value(self):
        """Verify against the known leaf from our test input generation."""
        leaf = await poseidon_hash(
            [42, 1000, 1], circuits_dir=CIRCUITS_DIR
        )
        # This is the leaf hash computed by our generate_test_input.js
        expected = 7138946408509900141572757971884330120447472310724103259417700574110708038504
        assert leaf == expected


# ---------------------------------------------------------------------------
# Integration tests: witness computation
# ---------------------------------------------------------------------------


class TestComputeWitness:
    """Tests for compute_withdrawal_witness."""

    @skip_no_node
    @pytest.mark.asyncio
    async def test_compute_default_witness(self):
        """Generate a witness with default test Merkle tree."""
        w = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=100,
            nonce=1,
            recipient_address=0x35C3770470F57560BEBD1C6C74366B0297110BC2,
            circuits_dir=CIRCUITS_DIR,
        )
        assert isinstance(w, WithdrawalWitness)
        assert w.amount == 100
        assert w.balance == 1000
        assert w.secret == 42
        assert w.nonce == 1
        assert len(w.path_elements) == 10
        assert len(w.path_indices) == 10
        assert w.state_root > 0
        assert w.recipient_hash > 0
        assert w.validate() == []

    @skip_no_node
    @pytest.mark.asyncio
    async def test_witness_matches_test_input(self):
        """The computed witness should match our generate_test_input.js."""
        w = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=100,
            nonce=1,
            recipient_address=0x35C3770470F57560BEBD1C6C74366B0297110BC2,
            circuits_dir=CIRCUITS_DIR,
        )
        # Expected values from generate_test_input.js
        expected_root = 3305197735301507071566117782537473216135263344381086466045543627147954894876
        expected_recipient = 8115236278915580287033870785443340863078946943991125563411906784305589881962
        assert w.state_root == expected_root
        assert w.recipient_hash == expected_recipient


# ---------------------------------------------------------------------------
# Integration tests: real proof generation & verification
# ---------------------------------------------------------------------------


class TestRealProofGeneration:
    """Full integration tests: generate and verify real Groth16 proofs."""

    @skip_no_snarkjs
    @skip_no_node
    @pytest.mark.asyncio
    async def test_generate_proof(self, prover, mock_circuit):
        """Generate a real Groth16 proof."""
        witness = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=100,
            nonce=1,
            recipient_address=0x35C3770470F57560BEBD1C6C74366B0297110BC2,
            circuits_dir=CIRCUITS_DIR,
        )
        w, pub = witness.to_circuit_inputs()

        proof = await prover.generate_proof(mock_circuit, w, pub)

        assert isinstance(proof, ZKProof)
        assert proof.proof_type == "groth16"
        assert proof.circuit_id == "withdrawal"
        assert proof.proof_size_bytes == 256
        assert len(proof.proof_bytes) == 256
        assert len(proof.public_inputs) == 4
        assert proof.generation_time_ms > 0
        assert proof.estimated_verify_gas == GROTH16_VERIFY_GAS
        assert "raw_proof" in proof.metadata
        assert "raw_public" in proof.metadata

    @skip_no_snarkjs
    @skip_no_node
    @pytest.mark.asyncio
    async def test_verify_proof(self, prover, mock_circuit):
        """Generate and verify a real proof."""
        witness = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=100,
            nonce=1,
            recipient_address=0x35C3770470F57560BEBD1C6C74366B0297110BC2,
            circuits_dir=CIRCUITS_DIR,
        )
        w, pub = witness.to_circuit_inputs()

        proof = await prover.generate_proof(mock_circuit, w, pub)
        is_valid = await prover.verify_proof(mock_circuit, proof, pub)

        assert is_valid is True

    @skip_no_snarkjs
    @skip_no_node
    @pytest.mark.asyncio
    async def test_verify_tampered_proof(self, prover, mock_circuit):
        """A tampered proof should not verify."""
        witness = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=100,
            nonce=1,
            recipient_address=0x35C3770470F57560BEBD1C6C74366B0297110BC2,
            circuits_dir=CIRCUITS_DIR,
        )
        w, pub = witness.to_circuit_inputs()

        proof = await prover.generate_proof(mock_circuit, w, pub)

        # Tamper with proof bytes (flip a byte)
        tampered = bytearray(proof.proof_bytes)
        tampered[10] ^= 0xFF
        proof.proof_bytes = bytes(tampered)
        proof.metadata.pop("raw_proof", None)  # Force re-decode

        is_valid = await prover.verify_proof(mock_circuit, proof, pub)
        assert is_valid is False

    @skip_no_snarkjs
    @skip_no_node
    @pytest.mark.asyncio
    async def test_different_amounts(self, prover, mock_circuit):
        """Different amounts produce different proofs and both verify."""
        w1 = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=100,
            nonce=1,
            recipient_address=0x1234,
            circuits_dir=CIRCUITS_DIR,
        )
        w2 = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=500,
            nonce=1,
            recipient_address=0x1234,
            circuits_dir=CIRCUITS_DIR,
        )

        w1_w, w1_pub = w1.to_circuit_inputs()
        w2_w, w2_pub = w2.to_circuit_inputs()

        p1 = await prover.generate_proof(mock_circuit, w1_w, w1_pub)
        p2 = await prover.generate_proof(mock_circuit, w2_w, w2_pub)

        assert p1.proof_bytes != p2.proof_bytes
        assert p1.public_inputs != p2.public_inputs

        assert await prover.verify_proof(mock_circuit, p1, w1_pub)
        assert await prover.verify_proof(mock_circuit, p2, w2_pub)

    @skip_no_snarkjs
    @skip_no_node
    @pytest.mark.asyncio
    async def test_stats_after_proofs(self, prover, mock_circuit):
        """Stats should update after generating and verifying."""
        witness = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=100,
            nonce=1,
            recipient_address=0x1234,
            circuits_dir=CIRCUITS_DIR,
        )
        w, pub = witness.to_circuit_inputs()

        proof = await prover.generate_proof(mock_circuit, w, pub)
        await prover.verify_proof(mock_circuit, proof, pub)

        stats = prover.stats
        assert stats["proofs_generated"] >= 1
        assert stats["proofs_verified"] >= 1
        assert stats["avg_gen_time_ms"] > 0
        assert stats["avg_verify_time_ms"] > 0

    @skip_no_snarkjs
    @skip_no_node
    @pytest.mark.asyncio
    async def test_proof_to_dict_and_back(self, prover, mock_circuit):
        """ZKProof serialization roundtrip."""
        witness = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=100,
            nonce=1,
            recipient_address=0x1234,
            circuits_dir=CIRCUITS_DIR,
        )
        w, pub = witness.to_circuit_inputs()

        proof = await prover.generate_proof(mock_circuit, w, pub)

        # Serialize and deserialize (without metadata since it has non-basic types)
        d = proof.to_dict()
        proof2 = ZKProof.from_dict(d)

        assert proof2.proof_type == "groth16"
        assert proof2.circuit_id == "withdrawal"
        assert proof2.proof_bytes == proof.proof_bytes
        assert proof2.public_inputs == proof.public_inputs

    @skip_no_snarkjs
    @skip_no_node
    @pytest.mark.asyncio
    async def test_proof_to_contract_args(self, prover, mock_circuit):
        """Test formatting for on-chain submission."""
        witness = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=100,
            nonce=1,
            recipient_address=0x1234,
            circuits_dir=CIRCUITS_DIR,
        )
        w, pub = witness.to_circuit_inputs()

        proof = await prover.generate_proof(mock_circuit, w, pub)
        pb, pi_ints = proof.to_contract_args()

        assert len(pb) == 256
        assert len(pi_ints) == 4
        assert pi_ints[0] == 100  # amount
        assert pi_ints[1] == 1  # nonce
        assert all(isinstance(x, int) for x in pi_ints)

    @skip_no_snarkjs
    @skip_no_node
    @pytest.mark.asyncio
    async def test_format_snarkjs_calldata(self, prover, mock_circuit):
        """Test snarkjs-style calldata formatting."""
        witness = await compute_withdrawal_witness(
            secret=42,
            balance=1000,
            amount=100,
            nonce=1,
            recipient_address=0x1234,
            circuits_dir=CIRCUITS_DIR,
        )
        w, pub = witness.to_circuit_inputs()

        proof = await prover.generate_proof(mock_circuit, w, pub)
        cd = SnarkJSProver.format_calldata_snarkjs(proof)

        assert len(cd["a"]) == 2
        assert len(cd["b"]) == 2
        assert len(cd["b"][0]) == 2
        assert len(cd["c"]) == 2
        assert len(cd["input"]) == 4

        # amount = 100 → hex 0x64
        assert cd["input"][0] == "0x64"


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for error handling in the prover."""

    @skip_no_snarkjs
    @pytest.mark.asyncio
    async def test_generate_with_bad_witness(self, prover, mock_circuit):
        """Invalid witness should raise ProofGenerationError."""
        # amount > balance
        bad_inputs = {
            "amount": "2000",
            "nonce": "1",
            "recipientHash": "12345",
            "stateRoot": "67890",
            "secret": "42",
            "balance": "100",
            "pathElements": ["0"] * 10,
            "pathIndices": ["0"] * 10,
        }
        with pytest.raises(ProofGenerationError):
            await prover.generate_proof(
                mock_circuit,
                {
                    k: v
                    for k, v in bad_inputs.items()
                    if k in ("secret", "balance", "pathElements", "pathIndices")
                },
                {
                    k: v
                    for k, v in bad_inputs.items()
                    if k in ("amount", "nonce", "recipientHash", "stateRoot")
                },
            )

    @pytest.mark.asyncio
    async def test_generate_unavailable(self, mock_circuit):
        """Prover at bad path should raise ProofGenerationError."""
        p = SnarkJSProver(circuits_dir="/nonexistent")
        with pytest.raises(ProofGenerationError, match="not available"):
            await p.generate_proof(mock_circuit, {}, {})

    @pytest.mark.asyncio
    async def test_verify_unavailable(self, mock_circuit):
        """Prover at bad path should raise ProofVerificationError."""
        p = SnarkJSProver(circuits_dir="/nonexistent")
        dummy_proof = ZKProof(
            proof_bytes=b"\x00" * 256,
            public_inputs=[b"\x00" * 32] * 4,
            proof_type="groth16",
            circuit_id="withdrawal",
            generation_time_ms=0,
            proof_size_bytes=256,
            estimated_verify_gas=230_000,
        )
        with pytest.raises(ProofVerificationError, match="not available"):
            await p.verify_proof(mock_circuit, dummy_proof, {})


# ---------------------------------------------------------------------------
# Circuit compilation test (slow, marks as such)
# ---------------------------------------------------------------------------


class TestCircuitCompilation:
    """Tests that verify the circom circuit compiles correctly."""

    @pytest.mark.skipif(
        not os.path.exists("/usr/local/bin/circom"),
        reason="circom not installed",
    )
    def test_circuit_file_exists(self):
        assert (CIRCUITS_DIR / "withdrawal.circom").exists()

    @pytest.mark.skipif(
        not os.path.exists("/usr/local/bin/circom"),
        reason="circom not installed",
    )
    def test_r1cs_exists(self):
        assert (BUILD_DIR / "withdrawal.r1cs").exists()

    @pytest.mark.skipif(
        not os.path.exists("/usr/local/bin/circom"),
        reason="circom not installed",
    )
    def test_wasm_exists(self):
        assert (
            BUILD_DIR / "withdrawal_js" / "withdrawal.wasm"
        ).exists()

    @skip_no_snarkjs
    def test_verification_key_valid(self):
        vk = json.loads((BUILD_DIR / "verification_key.json").read_text())
        assert vk["protocol"] == "groth16"
        assert vk["curve"] == "bn128"
        assert vk["nPublic"] == 4
        assert len(vk["IC"]) == 5  # IC[0] + 4 public inputs

    @skip_no_snarkjs
    def test_solidity_verifier_exists(self):
        sol_path = BUILD_DIR / "WithdrawalVerifier.sol"
        assert sol_path.exists()
        content = sol_path.read_text()
        assert "Groth16Verifier" in content
        assert "verifyProof" in content

    @skip_no_snarkjs
    def test_circuit_info(self):
        """Verify circuit constraint count."""
        result = subprocess.run(
            ["snarkjs", "r1cs", "info", str(BUILD_DIR / "withdrawal.r1cs")],
            capture_output=True,
            text=True,
        )
        assert "6388" in result.stdout or "Constraints" in result.stdout


# ---------------------------------------------------------------------------
# ZKProof dataclass integration
# ---------------------------------------------------------------------------


class TestZKProofIntegration:
    """Verify ZKProof dataclass works correctly with snarkjs proofs."""

    def test_from_encoded_proof(self, sample_proof_data):
        proof_bytes = SnarkJSProver._encode_proof(sample_proof_data)
        public_data = ["100", "1", "12345", "67890"]
        public_bytes = [int(s).to_bytes(32, "big") for s in public_data]

        proof = ZKProof(
            proof_bytes=proof_bytes,
            public_inputs=public_bytes,
            proof_type="groth16",
            circuit_id="withdrawal",
            generation_time_ms=50,
            proof_size_bytes=256,
            estimated_verify_gas=230_000,
        )

        # to_contract_args
        pb, pi = proof.to_contract_args()
        assert pb == proof_bytes
        assert pi[0] == 100
        assert pi[1] == 1

        # to_dict
        d = proof.to_dict()
        assert d["proof_type"] == "groth16"
        assert d["proof_bytes"].startswith("0x")
        assert len(d["public_inputs"]) == 4

        # from_dict roundtrip
        proof2 = ZKProof.from_dict(d)
        assert proof2.proof_bytes == proof.proof_bytes

    def test_repr(self, sample_proof_data):
        proof_bytes = SnarkJSProver._encode_proof(sample_proof_data)
        proof = ZKProof(
            proof_bytes=proof_bytes,
            public_inputs=[b"\x00" * 32],
            proof_type="groth16",
            circuit_id="withdrawal",
            generation_time_ms=50,
            proof_size_bytes=256,
            estimated_verify_gas=230_000,
        )
        r = repr(proof)
        assert "groth16" in r
        assert "withdrawal" in r
        assert "256B" in r
