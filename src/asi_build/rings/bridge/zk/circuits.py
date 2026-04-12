"""
ZK Circuit Definitions for Bridge Verification
================================================

Python representations of the arithmetic circuits used for bridge
ZK proofs.  These define the constraint systems and witness generation
that would be compiled to R1CS/AIR for a real prover (SP1/Nova/Groth16).

Each circuit defines:

- **Public inputs**: values known to the verifier (on-chain contract)
- **Private witness**: values known only to the prover
- **Constraints**: conditions that must hold for a valid proof
- **Witness generation**: compute the full witness from raw data
- **Constraint verification**: check all constraints (Python simulation)

.. important::

    All hash operations use SHA-256 (``hashlib.sha256``).  This is a
    deliberate simplification — real in-circuit hashing would use
    Poseidon (for SNARK-friendly hashing) or keccak256-in-circuit
    (for EVM compatibility).  SHA-256 keeps the simulation portable
    and avoids importing heavy field-arithmetic libraries.

These circuits are *higher-level* than the Groth16 prover in
``zk_prover.py``.  They define the **logical** constraint systems;
the prover turns them into actual polynomial commitments.
"""

from __future__ import annotations

import hashlib
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Metadata & Base
# ---------------------------------------------------------------------------


@dataclass
class CircuitMetadata:
    """Describes a circuit's static properties.

    Attributes
    ----------
    name : str
        Human-readable circuit name.
    version : str
        Semantic version string (e.g. ``"0.1.0"``).
    estimated_constraints : int
        Approximate R1CS constraint count for the circuit.
    num_public_inputs : int
        Number of field elements exposed as public inputs.
    num_witness_fields : int
        Number of private witness entries.
    description : str
        Free-form description of the circuit's purpose.
    """

    name: str
    version: str
    estimated_constraints: int
    num_public_inputs: int
    num_witness_fields: int
    description: str


class Circuit(ABC):
    """Abstract base for all ZK circuits.

    Subclasses define the constraint system for a specific proof type.
    The Python-level ``verify_constraints`` method acts as a **simulation**
    of the constraints that a real R1CS/AIR circuit would enforce.
    """

    @abstractmethod
    def metadata(self) -> CircuitMetadata:
        """Return static metadata about this circuit."""

    @abstractmethod
    def generate_witness(self, **kwargs: Any) -> dict:
        """Generate the full witness (public + private) from raw inputs.

        Returns
        -------
        dict
            Keys prefixed ``pub_`` are public inputs; everything else is
            private witness.
        """

    @abstractmethod
    def verify_constraints(
        self, witness: dict, public_inputs: dict,
    ) -> Tuple[bool, List[str]]:
        """Check all constraints.

        Returns
        -------
        tuple of (bool, list of str)
            ``(all_passed, list_of_violated_constraint_names)``.
            An empty list means every constraint holds.
        """

    @abstractmethod
    def public_inputs_from_witness(self, witness: dict) -> dict:
        """Extract only the public inputs from a full witness."""

    def estimate_constraints(self) -> int:
        """Estimated total R1CS constraint count."""
        return self.metadata().estimated_constraints


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(data: bytes) -> bytes:
    """Compute SHA-256 digest.

    .. note::
        Stands in for Poseidon / keccak256-in-circuit in real implementations.
    """
    return hashlib.sha256(data).digest()


def _concat_bytes_list(items: List[bytes]) -> bytes:
    """Concatenate a list of byte strings with length-prefix framing.

    Each element is preceded by its 4-byte big-endian length so that the
    hash is collision-resistant across different list partitions.
    """
    parts: list[bytes] = []
    for item in items:
        parts.append(struct.pack(">I", len(item)))
        parts.append(item)
    return b"".join(parts)


def _hash_header_fields(
    slot: int,
    proposer_index: int,
    parent_root: bytes,
    state_root: bytes,
    body_root: bytes,
) -> bytes:
    """Deterministic SHA-256 of header fields (mock SSZ hash-tree-root)."""
    payload = b"".join([
        struct.pack(">Q", slot),
        struct.pack(">Q", proposer_index),
        parent_root[:32].ljust(32, b"\x00"),
        state_root[:32].ljust(32, b"\x00"),
        body_root[:32].ljust(32, b"\x00"),
    ])
    return _sha256(payload)


def _to_bytes32(val: bytes | str) -> bytes:
    """Normalise a value to exactly 32 bytes."""
    if isinstance(val, str):
        val = bytes.fromhex(val.replace("0x", ""))
    return val[:32].ljust(32, b"\x00")


def _to_bytes20(val: bytes | str) -> bytes:
    """Normalise an Ethereum address to exactly 20 bytes."""
    if isinstance(val, str):
        val = bytes.fromhex(val.replace("0x", "").ljust(40, "0")[:40])
    return val[:20].ljust(20, b"\x00")


# ---------------------------------------------------------------------------
# BLS Verification Circuit
# ---------------------------------------------------------------------------


class BLSVerificationCircuit(Circuit):
    """Proves that a sync committee attested a beacon block header.

    The circuit verifies (in simulation) that:

    1. The committee's public keys hash to the expected root.
    2. A super-majority (≥ *threshold*) of committee members participated.
    3. The header fields hash to the expected block header hash.
    4. The aggregate signature has the correct length (96 bytes for BLS).

    Parameters
    ----------
    committee_size : int
        Expected number of sync committee members (default 512).
    threshold : int
        Minimum participation count for a valid attestation (default 342,
        i.e. ⅔ + 1 of 512).
    """

    def __init__(
        self,
        committee_size: int = 512,
        threshold: int = 342,
    ) -> None:
        self.committee_size = committee_size
        self.threshold = threshold

    # -- metadata ----------------------------------------------------------

    def metadata(self) -> CircuitMetadata:
        return CircuitMetadata(
            name="BLSVerificationCircuit",
            version="0.1.0",
            estimated_constraints=500_000,
            num_public_inputs=3,
            num_witness_fields=5,
            description=(
                "Verifies a BLS sync committee attestation over a beacon "
                "block header.  ~350K constraints for the BLS pairing check "
                "and ~150K for Poseidon hashing of the committee."
            ),
        )

    # -- witness generation ------------------------------------------------

    def generate_witness(self, **kwargs: Any) -> dict:
        """Generate a full witness.

        Parameters (via kwargs)
        -----------------------
        committee_pubkeys : list of bytes
            48-byte BLS public keys of all committee members.
        signature : bytes
            96-byte BLS aggregate signature.
        header_fields : dict
            Must contain ``slot``, ``proposer_index``, ``parent_root``,
            ``state_root``, ``body_root`` (bytes or hex str).
        bitmap : list of bool
            Participation bitmap (one entry per committee member).
        """
        committee_pubkeys: List[bytes] = kwargs["committee_pubkeys"]
        signature: bytes = kwargs["signature"]
        header_fields: dict = kwargs["header_fields"]
        bitmap: List[bool] = kwargs["bitmap"]

        # Derive public inputs
        committee_root = _sha256(
            _concat_bytes_list(committee_pubkeys),
        )
        participation_count = sum(bitmap)

        header_hash = _hash_header_fields(
            slot=header_fields["slot"],
            proposer_index=header_fields["proposer_index"],
            parent_root=_to_bytes32(header_fields["parent_root"]),
            state_root=_to_bytes32(header_fields["state_root"]),
            body_root=_to_bytes32(header_fields["body_root"]),
        )

        return {
            # Public inputs
            "pub_sync_committee_root": committee_root,
            "pub_block_header_hash": header_hash,
            "pub_participation_count": participation_count,
            # Private witness
            "committee_pubkeys": committee_pubkeys,
            "aggregate_signature": signature,
            "participation_bitmap": bitmap,
            "header_fields": header_fields,
        }

    # -- public inputs -----------------------------------------------------

    def public_inputs_from_witness(self, witness: dict) -> dict:
        return {
            "sync_committee_root": witness["pub_sync_committee_root"],
            "block_header_hash": witness["pub_block_header_hash"],
            "participation_count": witness["pub_participation_count"],
        }

    # -- constraint verification -------------------------------------------

    def verify_constraints(
        self, witness: dict, public_inputs: dict,
    ) -> Tuple[bool, List[str]]:
        """Check all BLS verification constraints.

        Constraints
        -----------
        1. SHA-256(committee_pubkeys) == sync_committee_root
        2. sum(bitmap) == participation_count
        3. participation_count >= threshold
        4. len(committee_pubkeys) == committee_size
        5. hash(header_fields) == block_header_hash
        6. len(aggregate_signature) == 96
        """
        violations: List[str] = []

        # 1. Committee root
        computed_root = _sha256(
            _concat_bytes_list(witness["committee_pubkeys"]),
        )
        if computed_root != _to_bytes32(public_inputs["sync_committee_root"]):
            violations.append(
                "committee_root_mismatch: "
                "SHA256(committee_pubkeys) != sync_committee_root"
            )

        # 2. Participation count matches bitmap
        bitmap_sum = sum(witness["participation_bitmap"])
        if bitmap_sum != public_inputs["participation_count"]:
            violations.append(
                f"participation_count_mismatch: "
                f"sum(bitmap)={bitmap_sum} != "
                f"participation_count={public_inputs['participation_count']}"
            )

        # 3. Threshold
        if public_inputs["participation_count"] < self.threshold:
            violations.append(
                f"below_threshold: "
                f"participation_count={public_inputs['participation_count']} "
                f"< threshold={self.threshold}"
            )

        # 4. Committee size
        if len(witness["committee_pubkeys"]) != self.committee_size:
            violations.append(
                f"committee_size_mismatch: "
                f"len(pubkeys)={len(witness['committee_pubkeys'])} "
                f"!= expected={self.committee_size}"
            )

        # 5. Header hash
        hf = witness["header_fields"]
        computed_header_hash = _hash_header_fields(
            slot=hf["slot"],
            proposer_index=hf["proposer_index"],
            parent_root=_to_bytes32(hf["parent_root"]),
            state_root=_to_bytes32(hf["state_root"]),
            body_root=_to_bytes32(hf["body_root"]),
        )
        if computed_header_hash != _to_bytes32(
            public_inputs["block_header_hash"],
        ):
            violations.append(
                "header_hash_mismatch: "
                "hash(header_fields) != block_header_hash"
            )

        # 6. Signature length
        if len(witness["aggregate_signature"]) != 96:
            violations.append(
                f"signature_length: "
                f"len(aggregate_signature)={len(witness['aggregate_signature'])} "
                f"!= 96"
            )

        return (len(violations) == 0, violations)


# ---------------------------------------------------------------------------
# Merkle Patricia Circuit
# ---------------------------------------------------------------------------


class MerklePatriciaCircuit(Circuit):
    """Proves inclusion of an account state in the Ethereum state trie.

    The circuit verifies that a chain of MPT proof nodes links the
    ``state_root`` to a leaf containing the expected account state.

    .. note::
        Real EVM MPT proofs use keccak256.  We simulate with SHA-256
        for circuit-portability reasons.
    """

    # -- metadata ----------------------------------------------------------

    def metadata(self) -> CircuitMetadata:
        return CircuitMetadata(
            name="MerklePatriciaCircuit",
            version="0.1.0",
            estimated_constraints=100_000,
            num_public_inputs=3,
            num_witness_fields=3,
            description=(
                "Verifies Merkle-Patricia proof of account inclusion.  "
                "~30K constraints per keccak256-in-circuit round, "
                "typically 6-8 rounds for a full MPT path."
            ),
        )

    # -- witness generation ------------------------------------------------

    def generate_witness(self, **kwargs: Any) -> dict:
        """Generate a full witness.

        Parameters (via kwargs)
        -----------------------
        state_root : bytes
            32-byte state root.
        address : bytes | str
            20-byte Ethereum address (or hex string).
        proof_nodes : list of bytes
            MPT proof nodes from RPC ``eth_getProof``.
        account_state : dict
            Keys: ``nonce`` (int), ``balance`` (int),
            ``storage_root`` (bytes32), ``code_hash`` (bytes32).
        """
        state_root: bytes = _to_bytes32(kwargs["state_root"])
        address_raw = kwargs["address"]
        address: bytes = _to_bytes20(address_raw)
        proof_nodes: List[bytes] = kwargs["proof_nodes"]
        account_state: dict = kwargs["account_state"]

        address_hash = _sha256(address)

        # Derive expected value hash from account state
        account_bytes = self._encode_account_state(account_state)
        expected_value_hash = _sha256(account_bytes)

        # Build key path as nibbles
        key_path = [b >> 4 for b in address_hash] + [b & 0x0F for b in address_hash]

        return {
            # Public inputs
            "pub_state_root": state_root,
            "pub_address_hash": address_hash,
            "pub_expected_value_hash": expected_value_hash,
            # Private witness
            "proof_nodes": proof_nodes,
            "account_state": account_state,
            "key_path": key_path,
            "address": address,
        }

    # -- public inputs -----------------------------------------------------

    def public_inputs_from_witness(self, witness: dict) -> dict:
        return {
            "state_root": witness["pub_state_root"],
            "address_hash": witness["pub_address_hash"],
            "expected_value_hash": witness["pub_expected_value_hash"],
        }

    # -- constraint verification -------------------------------------------

    def verify_constraints(
        self, witness: dict, public_inputs: dict,
    ) -> Tuple[bool, List[str]]:
        """Check all Merkle Patricia proof constraints.

        Constraints
        -----------
        1. Proof path root == state_root
        2. SHA-256(address) == address_hash
        3. SHA-256(account_state_encoded) == expected_value_hash
        4. Each proof node chains to its parent via hash
        5. proof_nodes is non-empty
        6. Leaf node contains the account state
        """
        violations: List[str] = []

        proof_nodes: List[bytes] = witness["proof_nodes"]

        # 5. Non-empty proof
        if not proof_nodes:
            violations.append("empty_proof: proof_nodes list is empty")
            # Cannot check further constraints without proof nodes
            return (False, violations)

        # 1. Proof path root check
        computed_root = _sha256(proof_nodes[0])
        if computed_root != _to_bytes32(public_inputs["state_root"]):
            violations.append(
                "root_mismatch: SHA256(proof_nodes[0]) != state_root"
            )

        # 2. Address hash
        computed_addr_hash = _sha256(witness["address"])
        if computed_addr_hash != _to_bytes32(public_inputs["address_hash"]):
            violations.append(
                "address_hash_mismatch: SHA256(address) != address_hash"
            )

        # 3. Account state value hash
        account_bytes = self._encode_account_state(witness["account_state"])
        computed_value_hash = _sha256(account_bytes)
        if computed_value_hash != _to_bytes32(
            public_inputs["expected_value_hash"],
        ):
            violations.append(
                "value_hash_mismatch: "
                "SHA256(account_state) != expected_value_hash"
            )

        # 4. Proof node chaining — each node's hash appears in its parent
        for i in range(len(proof_nodes) - 1):
            child_hash = _sha256(proof_nodes[i + 1])
            if child_hash not in self._extract_hashes(proof_nodes[i]):
                violations.append(
                    f"chain_break_at_{i}: "
                    f"hash(proof_nodes[{i + 1}]) not embedded in "
                    f"proof_nodes[{i}]"
                )

        # 6. Leaf node contains account state
        leaf_node = proof_nodes[-1]
        if computed_value_hash not in self._extract_hashes(leaf_node):
            violations.append(
                "leaf_value_mismatch: "
                "account_state hash not found in leaf proof node"
            )

        return (len(violations) == 0, violations)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _encode_account_state(account_state: dict) -> bytes:
        """Deterministic encoding of account state fields.

        Encodes nonce (8B) + balance (32B) + storage_root (32B) +
        code_hash (32B) = 104 bytes total.
        """
        nonce = account_state.get("nonce", 0)
        balance = account_state.get("balance", 0)
        storage_root = _to_bytes32(account_state.get("storage_root", b"\x00" * 32))
        code_hash = _to_bytes32(account_state.get("code_hash", b"\x00" * 32))

        return b"".join([
            struct.pack(">Q", nonce),
            balance.to_bytes(32, "big"),
            storage_root,
            code_hash,
        ])

    @staticmethod
    def _extract_hashes(node: bytes) -> set:
        """Extract all possible 32-byte aligned sub-sequences from a node.

        In a real MPT, we would parse RLP and extract child references.
        For simulation, we check every 32-byte window.
        """
        hashes = set()
        for offset in range(0, max(1, len(node) - 31)):
            hashes.add(node[offset : offset + 32])
        return hashes


# ---------------------------------------------------------------------------
# Bridge Withdrawal Circuit (Main / Composite)
# ---------------------------------------------------------------------------


class BridgeWithdrawalCircuit(Circuit):
    """Composite circuit proving a valid cross-chain withdrawal.

    Combines three sub-proofs:

    1. **BLS verification** — the beacon header is attested by the sync
       committee (via :class:`BLSVerificationCircuit`).
    2. **MPT verification** — the deposit event exists in the attested
       block's state (via :class:`MerklePatriciaCircuit`).
    3. **Withdrawal authorisation** — validator signatures meet threshold
       and deposit data matches public inputs.

    This is the circuit that the on-chain bridge contract verifies.

    Parameters
    ----------
    committee_size : int
        Sync committee size (default 512).
    committee_threshold : int
        BLS attestation threshold (default 342).
    """

    def __init__(
        self,
        committee_size: int = 512,
        committee_threshold: int = 342,
    ) -> None:
        self.bls_circuit = BLSVerificationCircuit(
            committee_size=committee_size,
            threshold=committee_threshold,
        )
        self.mpt_circuit = MerklePatriciaCircuit()

    # -- metadata ----------------------------------------------------------

    def metadata(self) -> CircuitMetadata:
        return CircuitMetadata(
            name="BridgeWithdrawalCircuit",
            version="0.1.0",
            estimated_constraints=700_000,
            num_public_inputs=6,
            num_witness_fields=8,
            description=(
                "Composite circuit: BLS header verification (~500K) + "
                "MPT state inclusion (~100K) + withdrawal authorisation "
                "(~100K).  Proves a Rings→Ethereum withdrawal is backed "
                "by an on-chain deposit in an attested block."
            ),
        )

    # -- witness generation ------------------------------------------------

    def generate_witness(self, **kwargs: Any) -> dict:
        """Generate the composite witness.

        Parameters (via kwargs)
        -----------------------
        recipient : bytes | str
            20-byte Ethereum address.
        amount : int
            Withdrawal amount in wei.
        nonce : int
            Withdrawal nonce.
        rings_did : str | bytes
            Rings DID identifier (hashed to bytes32).
        header_proof : dict
            Must contain ``committee_pubkeys``, ``signature``,
            ``header_fields``, ``bitmap`` — forwarded to
            :class:`BLSVerificationCircuit`.
        receipt_proof : dict
            Must contain ``state_root``, ``address``, ``proof_nodes``,
            ``account_state`` — forwarded to
            :class:`MerklePatriciaCircuit`.
        validator_sigs : list of bytes
            Bridge validator signatures authorising the withdrawal.
        threshold : int
            Minimum number of validator signatures (default 4).
        """
        recipient_raw = kwargs["recipient"]
        amount: int = kwargs["amount"]
        nonce: int = kwargs["nonce"]
        rings_did = kwargs["rings_did"]
        header_proof: dict = kwargs["header_proof"]
        receipt_proof: dict = kwargs["receipt_proof"]
        validator_sigs: List[bytes] = kwargs["validator_sigs"]
        threshold: int = kwargs.get("threshold", 4)

        # Sub-witnesses
        bls_witness = self.bls_circuit.generate_witness(**header_proof)
        mpt_witness = self.mpt_circuit.generate_witness(**receipt_proof)

        # Public input derivations
        recipient = _to_bytes20(recipient_raw)
        if isinstance(rings_did, str):
            rings_did_hash = _sha256(rings_did.encode("utf-8"))
        else:
            rings_did_hash = _sha256(rings_did)

        # Deposit log data: deterministic encoding of (recipient, amount)
        deposit_log_data = recipient + amount.to_bytes(32, "big")

        return {
            # Public inputs
            "pub_recipient": recipient,
            "pub_amount": amount,
            "pub_nonce": nonce,
            "pub_rings_did_hash": rings_did_hash,
            "pub_block_header_hash": bls_witness["pub_block_header_hash"],
            "pub_state_root": mpt_witness["pub_state_root"],
            # Private witness — sub-circuits
            "bls_witness": bls_witness,
            "mpt_witness": mpt_witness,
            # Private witness — withdrawal specific
            "validator_signatures": validator_sigs,
            "validator_threshold": threshold,
            "deposit_log_data": deposit_log_data,
        }

    # -- public inputs -----------------------------------------------------

    def public_inputs_from_witness(self, witness: dict) -> dict:
        return {
            "recipient": witness["pub_recipient"],
            "amount": witness["pub_amount"],
            "nonce": witness["pub_nonce"],
            "rings_did_hash": witness["pub_rings_did_hash"],
            "block_header_hash": witness["pub_block_header_hash"],
            "state_root": witness["pub_state_root"],
        }

    # -- constraint verification -------------------------------------------

    def verify_constraints(
        self, witness: dict, public_inputs: dict,
    ) -> Tuple[bool, List[str]]:
        """Check all bridge withdrawal constraints.

        Constraints
        -----------
        1. BLS sub-circuit constraints pass (header attested).
        2. MPT sub-circuit constraints pass (deposit in state).
        3. len(validator_signatures) >= validator_threshold.
        4. Every validator signature is non-empty.
        5. amount > 0.
        6. nonce >= 0.
        7. deposit_log_data encodes (recipient, amount).
        """
        violations: List[str] = []

        # 1. BLS sub-constraints
        bls_pub = self.bls_circuit.public_inputs_from_witness(
            witness["bls_witness"],
        )
        bls_ok, bls_violations = self.bls_circuit.verify_constraints(
            witness["bls_witness"], bls_pub,
        )
        for v in bls_violations:
            violations.append(f"bls:{v}")

        # 2. MPT sub-constraints
        mpt_pub = self.mpt_circuit.public_inputs_from_witness(
            witness["mpt_witness"],
        )
        mpt_ok, mpt_violations = self.mpt_circuit.verify_constraints(
            witness["mpt_witness"], mpt_pub,
        )
        for v in mpt_violations:
            violations.append(f"mpt:{v}")

        # 3. Validator threshold
        sigs = witness["validator_signatures"]
        threshold = witness["validator_threshold"]
        if len(sigs) < threshold:
            violations.append(
                f"validator_threshold: "
                f"len(signatures)={len(sigs)} < threshold={threshold}"
            )

        # 4. Non-empty signatures
        for idx, sig in enumerate(sigs):
            if not sig or len(sig) == 0:
                violations.append(f"empty_signature_at_{idx}")

        # 5. Positive amount
        if public_inputs["amount"] <= 0:
            violations.append(
                f"non_positive_amount: amount={public_inputs['amount']}"
            )

        # 6. Non-negative nonce
        if public_inputs["nonce"] < 0:
            violations.append(
                f"negative_nonce: nonce={public_inputs['nonce']}"
            )

        # 7. Deposit log data encodes (recipient, amount)
        expected_log_data = (
            _to_bytes20(public_inputs["recipient"])
            + public_inputs["amount"].to_bytes(32, "big")
        )
        if witness["deposit_log_data"] != expected_log_data:
            violations.append(
                "deposit_log_mismatch: "
                "deposit_log_data != encode(recipient, amount)"
            )

        return (len(violations) == 0, violations)

    # -- convenience -------------------------------------------------------

    def public_inputs_hash(
        self,
        recipient: bytes | str,
        amount: int,
        nonce: int,
        rings_did: bytes | str,
    ) -> bytes:
        """SHA-256 of all public inputs packed into a single digest.

        This is the value the on-chain contract would compare against
        to bind the proof to a specific withdrawal request.

        Returns
        -------
        bytes
            32-byte SHA-256 digest.
        """
        recipient_b = _to_bytes20(recipient)
        if isinstance(rings_did, str):
            did_hash = _sha256(rings_did.encode("utf-8"))
        else:
            did_hash = _sha256(rings_did)

        payload = b"".join([
            recipient_b,
            amount.to_bytes(32, "big"),
            nonce.to_bytes(32, "big"),
            did_hash,
        ])
        return _sha256(payload)


# ---------------------------------------------------------------------------
# Sync Committee Rotation Circuit
# ---------------------------------------------------------------------------


class SyncCommitteeRotationCircuit(Circuit):
    """Proves a valid sync committee rotation on the beacon chain.

    The current sync committee (attested by a super-majority of its own
    members) endorses the next sync committee.  This circuit proves that
    transition without revealing individual public keys.

    Parameters
    ----------
    committee_size : int
        Expected committee size (default 512).
    supermajority_threshold : int
        Minimum attestation count from the current committee (default 342).
    """

    def __init__(
        self,
        committee_size: int = 512,
        supermajority_threshold: int = 342,
    ) -> None:
        self.committee_size = committee_size
        self.supermajority_threshold = supermajority_threshold

    # -- metadata ----------------------------------------------------------

    def metadata(self) -> CircuitMetadata:
        return CircuitMetadata(
            name="SyncCommitteeRotationCircuit",
            version="0.1.0",
            estimated_constraints=600_000,
            num_public_inputs=3,
            num_witness_fields=5,
            description=(
                "Proves a valid sync committee rotation.  Two SHA-256 "
                "committee hashes (~150K each) + BLS attestation check "
                "(~350K) = ~600K constraints."
            ),
        )

    # -- witness generation ------------------------------------------------

    def generate_witness(self, **kwargs: Any) -> dict:
        """Generate the rotation witness.

        Parameters (via kwargs)
        -----------------------
        current_pubkeys : list of bytes
            48-byte BLS public keys of the current committee.
        new_pubkeys : list of bytes
            48-byte BLS public keys of the incoming committee.
        attestation_sig : bytes
            96-byte aggregate BLS signature from current committee members
            attesting the new committee.
        attestation_bitmap : list of bool
            Participation bitmap for the attestation.
        slot : int
            Beacon chain slot at which the rotation is attested.
        """
        current_pubkeys: List[bytes] = kwargs["current_pubkeys"]
        new_pubkeys: List[bytes] = kwargs["new_pubkeys"]
        attestation_sig: bytes = kwargs["attestation_sig"]
        attestation_bitmap: List[bool] = kwargs["attestation_bitmap"]
        slot: int = kwargs["slot"]

        current_root = _sha256(_concat_bytes_list(current_pubkeys))
        new_root = _sha256(_concat_bytes_list(new_pubkeys))

        return {
            # Public inputs
            "pub_current_committee_root": current_root,
            "pub_new_committee_root": new_root,
            "pub_attested_slot": slot,
            # Private witness
            "current_pubkeys": current_pubkeys,
            "new_pubkeys": new_pubkeys,
            "attestation_signature": attestation_sig,
            "attestation_bitmap": attestation_bitmap,
            "slot_data": slot,
        }

    # -- public inputs -----------------------------------------------------

    def public_inputs_from_witness(self, witness: dict) -> dict:
        return {
            "current_committee_root": witness["pub_current_committee_root"],
            "new_committee_root": witness["pub_new_committee_root"],
            "attested_slot": witness["pub_attested_slot"],
        }

    # -- constraint verification -------------------------------------------

    def verify_constraints(
        self, witness: dict, public_inputs: dict,
    ) -> Tuple[bool, List[str]]:
        """Check all sync committee rotation constraints.

        Constraints
        -----------
        1. SHA-256(current_pubkeys) == current_committee_root
        2. SHA-256(new_pubkeys) == new_committee_root
        3. sum(attestation_bitmap) >= supermajority_threshold (342)
        4. len(current_pubkeys) == committee_size (512)
        5. len(new_pubkeys) == committee_size (512)
        6. slot_data == attested_slot
        """
        violations: List[str] = []

        # 1. Current committee root
        computed_current = _sha256(
            _concat_bytes_list(witness["current_pubkeys"]),
        )
        if computed_current != _to_bytes32(
            public_inputs["current_committee_root"],
        ):
            violations.append(
                "current_root_mismatch: "
                "SHA256(current_pubkeys) != current_committee_root"
            )

        # 2. New committee root
        computed_new = _sha256(
            _concat_bytes_list(witness["new_pubkeys"]),
        )
        if computed_new != _to_bytes32(public_inputs["new_committee_root"]):
            violations.append(
                "new_root_mismatch: "
                "SHA256(new_pubkeys) != new_committee_root"
            )

        # 3. Supermajority attestation
        attestation_count = sum(witness["attestation_bitmap"])
        if attestation_count < self.supermajority_threshold:
            violations.append(
                f"below_supermajority: "
                f"sum(bitmap)={attestation_count} < "
                f"threshold={self.supermajority_threshold}"
            )

        # 4. Current committee size
        if len(witness["current_pubkeys"]) != self.committee_size:
            violations.append(
                f"current_size_mismatch: "
                f"len(current_pubkeys)={len(witness['current_pubkeys'])} "
                f"!= {self.committee_size}"
            )

        # 5. New committee size
        if len(witness["new_pubkeys"]) != self.committee_size:
            violations.append(
                f"new_size_mismatch: "
                f"len(new_pubkeys)={len(witness['new_pubkeys'])} "
                f"!= {self.committee_size}"
            )

        # 6. Slot consistency
        if witness["slot_data"] != public_inputs["attested_slot"]:
            violations.append(
                f"slot_mismatch: "
                f"slot_data={witness['slot_data']} != "
                f"attested_slot={public_inputs['attested_slot']}"
            )

        return (len(violations) == 0, violations)


# ---------------------------------------------------------------------------
# Convenience: all circuit classes
# ---------------------------------------------------------------------------

ALL_CIRCUITS: List[type] = [
    BLSVerificationCircuit,
    MerklePatriciaCircuit,
    BridgeWithdrawalCircuit,
    SyncCommitteeRotationCircuit,
]

__all__ = [
    "Circuit",
    "CircuitMetadata",
    "BLSVerificationCircuit",
    "MerklePatriciaCircuit",
    "BridgeWithdrawalCircuit",
    "SyncCommitteeRotationCircuit",
    "ALL_CIRCUITS",
]
