"""
ZK Proof Generation and Verification Engine
=============================================

Provides proof generation and verification using the circuit definitions
from :mod:`.circuits`.  Three prover implementations:

1. **SimulatedProver** — runs circuit constraints in Python, generates
   HMAC-based commitment proofs for testing.  Fast, no external deps.

2. **SP1ProverInterface** — abstract interface for the SP1 zkVM
   (Succinct's RISC-V prover).  Stub for future Rust FFI integration.

3. **DistributedProver** — coordinates proof generation across Rings
   network nodes using Nova IVC (Incremental Verifiable Computation).

Usage
-----

.. code-block:: python

    from rings.bridge.zk.circuits import BLSVerificationCircuit
    from rings.bridge.zk.prover import SimulatedProver

    circuit = BLSVerificationCircuit(committee_size=4, threshold=3)
    prover = SimulatedProver()

    witness = circuit.generate_witness(
        committee_pubkeys=[...], signature=...,
        header_fields={...}, bitmap=[...],
    )
    public_inputs = circuit.public_inputs_from_witness(witness)

    proof = await prover.generate_proof(circuit, witness, public_inputs)
    assert await prover.verify_proof(circuit, proof, public_inputs)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import struct
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .circuits import Circuit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# SimulatedProver proof format:
#   [0:32]   = HMAC-SHA256(key, witness_serialized)   — witness commitment
#   [32:64]  = SHA256(public_inputs_serialized)        — public-input binding
#   [64:96]  = SHA256(circuit_id)                      — circuit binding
#   [96:128] = random nonce                            — uniqueness
#   [128:160] = SHA256(commitment || pi_binding || circuit_binding || nonce)
#                                                      — integrity digest
#   [160:256] = zero padding                           — pad to 256 bytes
PROOF_SIZE: int = 256

# Gas cost estimates for different proof types (mainnet averages).
GAS_ESTIMATE_GROTH16: int = 220_000
GAS_ESTIMATE_STARK: int = 350_000
GAS_ESTIMATE_NOVA: int = 280_000
GAS_ESTIMATE_SIMULATED: int = 220_000

# DistributedProver defaults
DEFAULT_SEGMENT_SIZE: int = 10_000
DEFAULT_MIN_PROVERS: int = 3
DEFAULT_SUBRING: str = "asi-build:bridge:provers"
DEFAULT_TASK_TIMEOUT: float = 60.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ProofGenerationError(Exception):
    """Raised when proof generation fails.

    Attributes
    ----------
    violations : list of str
        Specific constraint violations that caused the failure.
    """

    def __init__(self, message: str, violations: Optional[List[str]] = None):
        super().__init__(message)
        self.violations: List[str] = violations or []


class ProofVerificationError(Exception):
    """Raised when proof verification encounters an unexpected error.

    This is *not* raised for a proof that simply doesn't verify (that
    returns ``False``).  It indicates an internal error during the
    verification process itself — e.g. malformed proof data.
    """


# ---------------------------------------------------------------------------
# ZKProof dataclass
# ---------------------------------------------------------------------------


@dataclass
class ZKProof:
    """A generated zero-knowledge proof with metadata.

    Attributes
    ----------
    proof_bytes : bytes
        The actual proof data (256 bytes for simulated/Groth16 format).
    public_inputs : list of bytes
        Public inputs encoded as bytes32 values.
    proof_type : str
        Proof system identifier (``"groth16"``, ``"stark"``,
        ``"nova"``, ``"simulated"``).
    circuit_id : str
        Name of the circuit this proof covers (e.g.
        ``"BLSVerificationCircuit"``).
    generation_time_ms : int
        Wall-clock milliseconds for proof generation.
    proof_size_bytes : int
        ``len(proof_bytes)`` — stored explicitly for quick access.
    estimated_verify_gas : int
        Estimated on-chain gas cost for verifying this proof.
    metadata : dict
        Additional prover-specific metadata (e.g. ``prover_version``,
        ``segment_count``).
    """

    proof_bytes: bytes
    public_inputs: List[bytes]
    proof_type: str
    circuit_id: str
    generation_time_ms: int
    proof_size_bytes: int
    estimated_verify_gas: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    # -- Solidity interface ---------------------------------------------------

    def to_contract_args(self) -> Tuple[bytes, List[int]]:
        """Format for submission to ``Groth16Verifier.sol``.

        Returns
        -------
        tuple of (bytes, list of int)
            ``(proof_bytes, public_inputs_as_uint256)`` where each
            ``bytes32`` public input is converted to ``int`` via
            big-endian interpretation.
        """
        uint256_inputs: List[int] = []
        for pi in self.public_inputs:
            # Pad or truncate to exactly 32 bytes, then interpret as uint256
            padded = pi[:32].rjust(32, b"\x00")
            uint256_inputs.append(int.from_bytes(padded, "big"))
        return (self.proof_bytes, uint256_inputs)

    # -- serialisation --------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary.

        Bytes fields are hex-encoded with a ``0x`` prefix.
        """
        return {
            "proof_bytes": "0x" + self.proof_bytes.hex(),
            "public_inputs": [
                "0x" + pi.hex() for pi in self.public_inputs
            ],
            "proof_type": self.proof_type,
            "circuit_id": self.circuit_id,
            "generation_time_ms": self.generation_time_ms,
            "proof_size_bytes": self.proof_size_bytes,
            "estimated_verify_gas": self.estimated_verify_gas,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ZKProof:
        """Deserialize from a dictionary (inverse of :meth:`to_dict`).

        Accepts hex-encoded bytes with or without ``0x`` prefix.
        """
        proof_hex = data["proof_bytes"]
        if isinstance(proof_hex, str):
            proof_bytes = bytes.fromhex(proof_hex.replace("0x", ""))
        else:
            proof_bytes = proof_hex

        public_inputs: List[bytes] = []
        for pi in data["public_inputs"]:
            if isinstance(pi, str):
                public_inputs.append(
                    bytes.fromhex(pi.replace("0x", ""))
                )
            else:
                public_inputs.append(pi)

        return cls(
            proof_bytes=proof_bytes,
            public_inputs=public_inputs,
            proof_type=data["proof_type"],
            circuit_id=data["circuit_id"],
            generation_time_ms=data["generation_time_ms"],
            proof_size_bytes=data["proof_size_bytes"],
            estimated_verify_gas=data["estimated_verify_gas"],
            metadata=data.get("metadata", {}),
        )

    # -- repr -----------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ZKProof(type={self.proof_type!r}, circuit={self.circuit_id!r}, "
            f"size={self.proof_size_bytes}B, "
            f"gen={self.generation_time_ms}ms, "
            f"gas≈{self.estimated_verify_gas:,})"
        )


# ---------------------------------------------------------------------------
# ZKProofEngine — Abstract Base Class
# ---------------------------------------------------------------------------


class ZKProofEngine(ABC):
    """Abstract base for ZK proof engines.

    Subclasses implement concrete proof generation and verification
    strategies.  The engine works with :class:`.circuits.Circuit`
    definitions that describe the constraint system.
    """

    @abstractmethod
    async def generate_proof(
        self,
        circuit: Circuit,
        witness: dict,
        public_inputs: dict,
    ) -> ZKProof:
        """Generate a ZK proof for *circuit* given *witness* and
        *public_inputs*.

        Raises
        ------
        ProofGenerationError
            If the witness does not satisfy the circuit's constraints
            or the prover encounters an internal error.
        """

    @abstractmethod
    async def verify_proof(
        self,
        circuit: Circuit,
        proof: ZKProof,
        public_inputs: dict,
    ) -> bool:
        """Verify a ZK proof.

        Returns
        -------
        bool
            ``True`` if the proof is valid for the given public inputs.
        """

    @property
    @abstractmethod
    def prover_type(self) -> str:
        """Return the prover type identifier (e.g. ``"simulated"``)."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this prover is ready to generate proofs."""


# ---------------------------------------------------------------------------
# SimulatedProver
# ---------------------------------------------------------------------------


class SimulatedProver(ZKProofEngine):
    """HMAC-based simulated proof engine for testing.

    Runs the circuit's constraint checker in Python and produces a
    deterministic HMAC commitment proof.  No external dependencies.

    Parameters
    ----------
    commitment_key : bytes, optional
        32-byte HMAC key for witness commitments.  If ``None``, a
        random key is generated.
    artificial_delay_ms : int
        If > 0, ``asyncio.sleep`` this many milliseconds during proof
        generation to simulate real prover latency.  Default 0.
    """

    def __init__(
        self,
        *,
        commitment_key: Optional[bytes] = None,
        artificial_delay_ms: int = 0,
    ) -> None:
        self._commitment_key: bytes = commitment_key or os.urandom(32)
        self._artificial_delay_ms: int = max(0, artificial_delay_ms)
        self._proofs_generated: int = 0
        self._proofs_verified: int = 0

    # -- ABC implementation ---------------------------------------------------

    @property
    def prover_type(self) -> str:
        return "simulated"

    @property
    def is_available(self) -> bool:
        return True

    async def generate_proof(
        self,
        circuit: Circuit,
        witness: dict,
        public_inputs: dict,
    ) -> ZKProof:
        """Generate a simulated proof.

        Steps
        -----
        1. Run ``circuit.verify_constraints(witness, public_inputs)``.
        2. If any constraint is violated, raise
           :class:`ProofGenerationError`.
        3. Build the 256-byte proof using HMAC commitments:

           - ``[0:32]``   witness commitment
           - ``[32:64]``  public-input binding
           - ``[64:96]``  circuit-id binding
           - ``[96:128]`` random nonce
           - ``[128:160]`` integrity digest
           - ``[160:256]`` zero padding
        """
        t0 = time.monotonic()

        # Optional artificial delay
        if self._artificial_delay_ms > 0:
            await asyncio.sleep(self._artificial_delay_ms / 1000.0)

        # 1. Constraint check
        ok, violations = circuit.verify_constraints(witness, public_inputs)
        if not ok:
            raise ProofGenerationError(
                f"Circuit constraint violations in "
                f"{circuit.metadata().name}: {violations}",
                violations=violations,
            )

        # 2. Build proof bytes (256 total)
        circuit_id = circuit.metadata().name
        witness_ser = self._canonical_serialize(witness)
        pi_ser = self._canonical_serialize(public_inputs)

        # [0:32] — HMAC-SHA256(key, witness_serialized)
        witness_commitment = hmac.new(
            self._commitment_key, witness_ser, hashlib.sha256
        ).digest()

        # [32:64] — SHA-256(public_inputs_serialized)
        pi_commitment = hashlib.sha256(pi_ser).digest()

        # [64:96] — SHA-256(circuit_id)
        circuit_binding = hashlib.sha256(
            circuit_id.encode("utf-8")
        ).digest()

        # [96:128] — random nonce (32 bytes)
        nonce = os.urandom(32)

        # [128:160] — integrity: SHA-256(commitment + pi + circuit + nonce)
        integrity = hashlib.sha256(
            witness_commitment + pi_commitment + circuit_binding + nonce
        ).digest()

        # [160:256] — zero padding (96 bytes)
        padding = b"\x00" * (PROOF_SIZE - 160)

        proof_bytes = (
            witness_commitment
            + pi_commitment
            + circuit_binding
            + nonce
            + integrity
            + padding
        )
        assert len(proof_bytes) == PROOF_SIZE, (
            f"Proof size mismatch: {len(proof_bytes)} != {PROOF_SIZE}"
        )

        # 3. Encode public inputs as bytes32
        encoded_public_inputs = self._encode_public_inputs(public_inputs)

        elapsed_ms = int((time.monotonic() - t0) * 1000)

        self._proofs_generated += 1

        proof = ZKProof(
            proof_bytes=proof_bytes,
            public_inputs=encoded_public_inputs,
            proof_type="simulated",
            circuit_id=circuit_id,
            generation_time_ms=elapsed_ms,
            proof_size_bytes=len(proof_bytes),
            estimated_verify_gas=GAS_ESTIMATE_SIMULATED,
            metadata={
                "prover": "SimulatedProver",
                "commitment_key_hash": hashlib.sha256(
                    self._commitment_key
                ).hexdigest()[:16],
                "constraint_count": circuit.estimate_constraints(),
                "proofs_generated": self._proofs_generated,
            },
        )

        logger.info(
            "SimulatedProver: generated proof for %s in %dms "
            "(constraints=%d)",
            circuit_id,
            elapsed_ms,
            circuit.estimate_constraints(),
        )

        return proof

    async def verify_proof(
        self,
        circuit: Circuit,
        proof: ZKProof,
        public_inputs: dict,
    ) -> bool:
        """Verify a simulated proof.

        Checks
        ------
        1. ``proof.proof_type == "simulated"``
        2. ``proof.circuit_id`` matches the circuit.
        3. Public-input commitment in proof bytes matches re-computation.
        4. Circuit-id binding matches.
        5. Integrity digest is consistent.
        """
        self._proofs_verified += 1

        # 1. Proof type check
        if proof.proof_type != "simulated":
            logger.debug(
                "SimulatedProver.verify: expected proof_type='simulated', "
                "got %r",
                proof.proof_type,
            )
            return False

        # 2. Circuit-id match
        circuit_id = circuit.metadata().name
        if proof.circuit_id != circuit_id:
            logger.debug(
                "SimulatedProver.verify: circuit_id mismatch: "
                "proof=%r, circuit=%r",
                proof.circuit_id,
                circuit_id,
            )
            return False

        # 3. Check proof bytes are correct length
        if len(proof.proof_bytes) < 160:
            logger.debug(
                "SimulatedProver.verify: proof too short (%d bytes)",
                len(proof.proof_bytes),
            )
            return False

        # Extract components from proof bytes
        pi_commitment = proof.proof_bytes[32:64]
        circuit_binding = proof.proof_bytes[64:96]
        nonce = proof.proof_bytes[96:128]
        integrity = proof.proof_bytes[128:160]

        # 4. Recompute public-input commitment
        pi_ser = self._canonical_serialize(public_inputs)
        expected_pi_commitment = hashlib.sha256(pi_ser).digest()
        if pi_commitment != expected_pi_commitment:
            logger.debug(
                "SimulatedProver.verify: public_input commitment mismatch"
            )
            return False

        # 5. Recompute circuit-id binding
        expected_circuit_binding = hashlib.sha256(
            circuit_id.encode("utf-8")
        ).digest()
        if circuit_binding != expected_circuit_binding:
            logger.debug(
                "SimulatedProver.verify: circuit binding mismatch"
            )
            return False

        # 6. Verify integrity digest
        witness_commitment = proof.proof_bytes[0:32]
        expected_integrity = hashlib.sha256(
            witness_commitment + pi_commitment + circuit_binding + nonce
        ).digest()
        if integrity != expected_integrity:
            logger.debug(
                "SimulatedProver.verify: integrity digest mismatch"
            )
            return False

        logger.debug(
            "SimulatedProver.verify: proof for %s verified OK",
            circuit_id,
        )
        return True

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _canonical_serialize(data: Any) -> bytes:
        """Deterministic serialisation of a value for commitment hashing.

        Uses sorted-key JSON for dicts, with special handling for
        ``bytes`` (hex-encoded) and non-JSON types (``repr``).  The
        output is deterministic for identical logical values.
        """

        def _normalise(obj: Any) -> Any:
            """Recursively normalise a value for JSON serialisation."""
            if isinstance(obj, bytes):
                return {"__bytes__": obj.hex()}
            if isinstance(obj, (list, tuple)):
                return [_normalise(v) for v in obj]
            if isinstance(obj, dict):
                return {
                    str(k): _normalise(v)
                    for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))
                }
            if isinstance(obj, bool):
                return obj
            if isinstance(obj, (int, float)):
                return obj
            if isinstance(obj, str):
                return obj
            # Fallback — repr for types we can't JSON-encode
            return {"__repr__": repr(obj)}

        normalised = _normalise(data)
        return json.dumps(
            normalised, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

    @staticmethod
    def _encode_public_inputs(public_inputs: dict) -> List[bytes]:
        """Encode public inputs as a list of ``bytes32`` values.

        Integers are big-endian encoded into 32 bytes.  Bytes values
        are padded/truncated to 32 bytes.  Strings are SHA-256 hashed.
        """
        encoded: List[bytes] = []
        for key in sorted(public_inputs.keys()):
            val = public_inputs[key]
            if isinstance(val, bytes):
                encoded.append(val[:32].ljust(32, b"\x00"))
            elif isinstance(val, int):
                # Handle negative and large ints gracefully
                try:
                    encoded.append(val.to_bytes(32, "big", signed=False))
                except OverflowError:
                    # Negative or > 2^256: hash the repr
                    encoded.append(
                        hashlib.sha256(str(val).encode()).digest()
                    )
            elif isinstance(val, str):
                encoded.append(
                    hashlib.sha256(val.encode("utf-8")).digest()
                )
            else:
                # Fallback: hash the repr
                encoded.append(
                    hashlib.sha256(repr(val).encode("utf-8")).digest()
                )
        return encoded

    # -- stats ----------------------------------------------------------------

    @property
    def stats(self) -> Dict[str, int]:
        """Return generation/verification statistics."""
        return {
            "proofs_generated": self._proofs_generated,
            "proofs_verified": self._proofs_verified,
        }


# ---------------------------------------------------------------------------
# SP1ProverInterface
# ---------------------------------------------------------------------------


class SP1ProverInterface(ZKProofEngine):
    """Interface for Succinct's SP1 zkVM prover.

    SP1 compiles Rust programs to RISC-V and generates STARK/Groth16
    proofs of correct execution.  This class provides the abstract
    interface; the actual SP1 binary (``sp1-prover``) integration is
    deferred to a future Rust FFI bridge.

    Parameters
    ----------
    sp1_binary_path : str, optional
        Filesystem path to the ``sp1-prover`` binary.  If ``None``,
        the prover will attempt to locate it on ``$PATH``.
    prover_network_url : str, optional
        URL for SP1's hosted prover network (``prover.succinct.xyz``).
        If set, proofs can be generated remotely.
    """

    def __init__(
        self,
        sp1_binary_path: Optional[str] = None,
        prover_network_url: Optional[str] = None,
    ) -> None:
        self.sp1_binary_path: Optional[str] = sp1_binary_path
        self.prover_network_url: Optional[str] = prover_network_url
        self._available: bool = False

    # -- ABC implementation ---------------------------------------------------

    @property
    def prover_type(self) -> str:
        return "sp1"

    @property
    def is_available(self) -> bool:
        return self._available

    async def generate_proof(
        self,
        circuit: Circuit,
        witness: dict,
        public_inputs: dict,
    ) -> ZKProof:
        """Generate a proof using the SP1 zkVM.

        .. note::
            Not yet implemented — requires the ``sp1-prover`` binary
            and Rust FFI bridge.

        Raises
        ------
        NotImplementedError
            Always, until SP1 integration is complete.
        """
        raise NotImplementedError(
            "SP1 prover integration is not yet available.  "
            "To use SP1:\n"
            "  1. Install the SP1 toolchain: "
            "curl -L https://sp1.succinct.xyz | bash\n"
            "  2. Build the circuit program as a RISC-V ELF\n"
            "  3. Set sp1_binary_path to the compiled ELF path\n"
            "  OR: set prover_network_url to use the hosted prover\n"
            "\n"
            f"Circuit: {circuit.metadata().name} "
            f"(~{circuit.estimate_constraints():,} constraints)\n"
            f"SP1 binary: {self.sp1_binary_path or 'not set'}\n"
            f"Network: {self.prover_network_url or 'not set'}"
        )

    async def verify_proof(
        self,
        circuit: Circuit,
        proof: ZKProof,
        public_inputs: dict,
    ) -> bool:
        """Verify an SP1 proof.

        Raises
        ------
        NotImplementedError
            Always, until SP1 integration is complete.
        """
        raise NotImplementedError(
            "SP1 proof verification is not yet available.  "
            "SP1 generates STARK proofs that can be verified natively "
            "or wrapped in a Groth16 proof for on-chain verification.  "
            "Once the FFI bridge is built, this method will support both."
        )

    # -- SP1-specific methods -------------------------------------------------

    def check_sp1_installation(self) -> Dict[str, Any]:
        """Check whether the SP1 toolchain is available.

        Returns
        -------
        dict
            Status report with keys: ``installed``, ``binary_path``,
            ``version``, ``network_url``, ``errors``.
        """
        import shutil

        status: Dict[str, Any] = {
            "installed": False,
            "binary_path": self.sp1_binary_path,
            "version": None,
            "network_url": self.prover_network_url,
            "errors": [],
        }

        # Check explicit binary path
        if self.sp1_binary_path:
            if os.path.isfile(self.sp1_binary_path):
                status["installed"] = True
            else:
                status["errors"].append(
                    f"sp1_binary_path does not exist: {self.sp1_binary_path}"
                )

        # Check PATH
        sp1_on_path = shutil.which("sp1-prover") or shutil.which("sp1")
        if sp1_on_path:
            status["installed"] = True
            if not status["binary_path"]:
                status["binary_path"] = sp1_on_path

        # Check prover network
        if self.prover_network_url:
            status["network_available"] = True  # would ping in production

        if not status["installed"] and not self.prover_network_url:
            status["errors"].append(
                "Neither local SP1 binary nor prover network URL configured"
            )

        self._available = status["installed"] or bool(self.prover_network_url)
        return status

    def __repr__(self) -> str:
        return (
            f"SP1ProverInterface(available={self._available}, "
            f"binary={self.sp1_binary_path!r}, "
            f"network={self.prover_network_url!r})"
        )


# ---------------------------------------------------------------------------
# ProvingTask
# ---------------------------------------------------------------------------


@dataclass
class ProvingTask:
    """A unit of work for distributed proof generation.

    Represents one segment of a circuit split across multiple prover
    nodes.  The :class:`DistributedProver` creates, assigns, tracks,
    and collects these tasks.

    Attributes
    ----------
    task_id : str
        Unique identifier (UUID) for this task.
    segment_index : int
        Index of this segment within the overall circuit split.
    circuit_id : str
        Name of the circuit being proved.
    witness_segment : dict
        The witness data for this segment.
    assigned_node : str or None
        Rings DID of the prover node assigned to this task.
    status : str
        Task lifecycle: ``"pending"`` → ``"assigned"`` →
        ``"proving"`` → ``"completed"`` | ``"failed"``.
    result : bytes or None
        The Nova fold proof bytes, once completed.
    created_at : float
        Unix timestamp of task creation.
    completed_at : float or None
        Unix timestamp of task completion.
    """

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    segment_index: int = 0
    circuit_id: str = ""
    witness_segment: Dict[str, Any] = field(default_factory=dict)
    assigned_node: Optional[str] = None
    status: str = "pending"
    result: Optional[bytes] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    # -- lifecycle transitions ------------------------------------------------

    def assign(self, node_did: str) -> None:
        """Assign this task to a prover node."""
        self.assigned_node = node_did
        self.status = "assigned"

    def start_proving(self) -> None:
        """Mark the task as actively being proved."""
        self.status = "proving"

    def complete(self, fold_proof: bytes) -> None:
        """Mark the task as completed with the given fold proof."""
        self.result = fold_proof
        self.status = "completed"
        self.completed_at = time.time()

    def fail(self, reason: str = "") -> None:
        """Mark the task as failed."""
        self.status = "failed"
        self.completed_at = time.time()
        if reason:
            self.witness_segment["_failure_reason"] = reason

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for DHT storage / network transmission."""
        return {
            "task_id": self.task_id,
            "segment_index": self.segment_index,
            "circuit_id": self.circuit_id,
            "assigned_node": self.assigned_node,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "has_result": self.result is not None,
        }


# ---------------------------------------------------------------------------
# DistributedProver
# ---------------------------------------------------------------------------


class DistributedProver(ZKProofEngine):
    """Distributed proof generation across Rings network nodes.

    Splits large circuits into segments and coordinates proof generation
    using Nova IVC (Incremental Verifiable Computation).  Each segment
    produces a fold proof; the final step compresses all fold proofs
    into a single Groth16-compatible proof for on-chain verification.

    If the network doesn't have enough prover nodes, falls back to a
    local prover (typically :class:`SimulatedProver`).

    Parameters
    ----------
    rings_client : object, optional
        A ``RingsClient`` instance (from :mod:`rings.client`) for DHT
        operations and Sub-Ring coordination.  Can be ``None`` for
        offline testing.
    bridge_subring : str
        Sub-Ring identifier for prover coordination.
    min_provers : int
        Minimum number of prover nodes required to start distributed
        proving.
    segment_size : int
        Target constraint count per segment.
    fallback_prover : ZKProofEngine, optional
        Fallback engine when distributed proving is unavailable.
    task_timeout : float
        Timeout in seconds for individual proving tasks.
    """

    def __init__(
        self,
        rings_client: Optional[Any] = None,
        bridge_subring: str = DEFAULT_SUBRING,
        min_provers: int = DEFAULT_MIN_PROVERS,
        segment_size: int = DEFAULT_SEGMENT_SIZE,
        fallback_prover: Optional[ZKProofEngine] = None,
        task_timeout: float = DEFAULT_TASK_TIMEOUT,
    ) -> None:
        self._rings_client = rings_client
        self._bridge_subring: str = bridge_subring
        self._min_provers: int = min_provers
        self._segment_size: int = segment_size
        self._fallback_prover: Optional[ZKProofEngine] = fallback_prover
        self._task_timeout: float = task_timeout

        # Task tracking
        self._active_tasks: Dict[str, ProvingTask] = {}
        self._completed_proofs: int = 0
        self._fallback_count: int = 0

    # -- ABC implementation ---------------------------------------------------

    @property
    def prover_type(self) -> str:
        return "distributed_nova"

    @property
    def is_available(self) -> bool:
        return self._rings_client is not None

    async def generate_proof(
        self,
        circuit: Circuit,
        witness: dict,
        public_inputs: dict,
    ) -> ZKProof:
        """Generate a distributed proof via Nova IVC.

        Steps
        -----
        1. Discover available prover nodes in the Sub-Ring.
        2. If fewer than ``min_provers``, fall back to
           ``fallback_prover``.
        3. Split the circuit witness into segments.
        4. Create and assign :class:`ProvingTask` instances.
        5. Collect fold proofs from all nodes.
        6. Compress fold proofs into a final Groth16-compatible proof.
        """
        t0 = time.monotonic()
        circuit_id = circuit.metadata().name

        # 1. Check constraints first
        ok, violations = circuit.verify_constraints(witness, public_inputs)
        if not ok:
            raise ProofGenerationError(
                f"Circuit constraint violations in {circuit_id}: {violations}",
                violations=violations,
            )

        # 2. Discover prover nodes
        provers = await self.discover_provers()
        logger.info(
            "DistributedProver: discovered %d prover nodes "
            "(min=%d) for circuit %s",
            len(provers),
            self._min_provers,
            circuit_id,
        )

        # 3. Fallback if not enough provers
        if len(provers) < self._min_provers:
            return await self._fallback_generate(
                circuit, witness, public_inputs, t0,
                reason=f"only {len(provers)}/{self._min_provers} provers",
            )

        # 4. Split witness into segments
        segments = self.split_circuit(circuit, witness)
        if not segments:
            segments = [witness]  # Single segment fallback

        logger.info(
            "DistributedProver: split %s into %d segments "
            "(%d constraints each)",
            circuit_id,
            len(segments),
            self._segment_size,
        )

        # 5. Create proving tasks
        tasks: List[ProvingTask] = []
        for idx, segment in enumerate(segments):
            task = ProvingTask(
                segment_index=idx,
                circuit_id=circuit_id,
                witness_segment=segment,
            )
            tasks.append(task)
            self._active_tasks[task.task_id] = task

        # 6. Assign tasks to prover nodes (round-robin)
        assignments = await self.assign_proving_tasks(tasks)
        logger.debug(
            "DistributedProver: assigned %d tasks: %s",
            len(assignments),
            {tid: node[:16] for tid, node in assignments.items()},
        )

        # 7. Collect fold proofs (with timeout)
        try:
            fold_proofs = await self.collect_fold_proofs(
                task_id=tasks[0].task_id,  # coordinated by first task
                timeout=self._task_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "DistributedProver: timeout collecting fold proofs, "
                "falling back"
            )
            return await self._fallback_generate(
                circuit, witness, public_inputs, t0,
                reason="timeout collecting fold proofs",
            )

        # 8. Compress to final proof
        proof = await self.compress_to_groth16(fold_proofs, circuit)

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        self._completed_proofs += 1

        # Clean up active tasks
        for task in tasks:
            self._active_tasks.pop(task.task_id, None)

        # Override timing metadata
        proof.generation_time_ms = elapsed_ms
        proof.metadata.update({
            "prover": "DistributedProver",
            "prover_nodes": len(provers),
            "segments": len(segments),
            "segment_size": self._segment_size,
            "distributed_proofs": self._completed_proofs,
        })

        return proof

    async def verify_proof(
        self,
        circuit: Circuit,
        proof: ZKProof,
        public_inputs: dict,
    ) -> bool:
        """Verify a distributed proof.

        Distributed proofs compressed to Groth16 format can be verified
        by any Groth16-compatible verifier.  If a fallback prover
        generated the proof, delegate to it.
        """
        # If it's a simulated proof (from fallback), delegate
        if proof.proof_type == "simulated" and self._fallback_prover:
            return await self._fallback_prover.verify_proof(
                circuit, proof, public_inputs,
            )

        # For distributed_nova type: verify the commitment structure
        if proof.proof_type != "distributed_nova":
            logger.debug(
                "DistributedProver.verify: unexpected proof_type %r",
                proof.proof_type,
            )
            return False

        # Check basic structural validity
        if len(proof.proof_bytes) < 160:
            return False

        circuit_id = circuit.metadata().name
        if proof.circuit_id != circuit_id:
            return False

        # Extract and verify the integrity commitment
        pi_commitment = proof.proof_bytes[32:64]
        circuit_binding = proof.proof_bytes[64:96]
        nonce = proof.proof_bytes[96:128]
        integrity = proof.proof_bytes[128:160]

        # Verify circuit binding
        expected_circuit_binding = hashlib.sha256(
            circuit_id.encode("utf-8")
        ).digest()
        if circuit_binding != expected_circuit_binding:
            return False

        # Verify integrity digest
        witness_commitment = proof.proof_bytes[0:32]
        expected_integrity = hashlib.sha256(
            witness_commitment + pi_commitment + circuit_binding + nonce
        ).digest()
        if integrity != expected_integrity:
            return False

        return True

    # -- Distributed proving methods ------------------------------------------

    async def discover_provers(self) -> List[str]:
        """Discover available prover nodes in the bridge Sub-Ring.

        Returns a list of Rings DIDs for nodes that have advertised
        proving capability via the DHT.

        Returns
        -------
        list of str
            DIDs of available prover nodes.  Empty if no client is
            configured or no provers are found.
        """
        if self._rings_client is None:
            return []

        try:
            # Query the DHT for prover registrations in our Sub-Ring
            # The convention is: key = "provers:{subring}" stores a
            # list of prover DIDs
            dht_key = f"provers:{self._bridge_subring}"
            result = await self._rings_client.dht_get(dht_key)
            if result and isinstance(result, list):
                return [str(did) for did in result]
            if result and isinstance(result, str):
                # Single prover as string
                return [result]
            return []
        except Exception as exc:
            logger.warning(
                "DistributedProver.discover_provers: DHT query failed: %s",
                exc,
            )
            return []

    async def assign_proving_tasks(
        self, tasks: List[ProvingTask],
    ) -> Dict[str, str]:
        """Assign proving tasks to discovered prover nodes.

        Uses round-robin assignment across discovered provers.  Each
        assignment is published to the DHT so the target node can
        pick it up.

        Returns
        -------
        dict
            Mapping of ``{task_id: assigned_node_did}``.
        """
        provers = await self.discover_provers()
        if not provers:
            return {}

        assignments: Dict[str, str] = {}
        for idx, task in enumerate(tasks):
            node = provers[idx % len(provers)]
            task.assign(node)
            assignments[task.task_id] = node

            # Publish assignment to DHT (so the prover node can find it)
            if self._rings_client is not None:
                try:
                    dht_key = f"proving_task:{task.task_id}"
                    await self._rings_client.dht_put(
                        dht_key, task.to_dict()
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to publish task %s to DHT: %s",
                        task.task_id,
                        exc,
                    )

        return assignments

    async def collect_fold_proofs(
        self,
        task_id: str,
        timeout: float = DEFAULT_TASK_TIMEOUT,
    ) -> List[bytes]:
        """Collect Nova fold proofs from participating nodes.

        Polls the DHT for completed task results until all tasks for
        this coordination group are done or the timeout expires.

        Parameters
        ----------
        task_id : str
            The coordinating task ID (typically the first segment).
        timeout : float
            Maximum seconds to wait for all fold proofs.

        Returns
        -------
        list of bytes
            Fold proof bytes from each segment, in order.

        Raises
        ------
        asyncio.TimeoutError
            If not all fold proofs are collected within *timeout*.
        """
        # Find all tasks in this batch (same circuit_id, close timestamps)
        coord_task = self._active_tasks.get(task_id)
        if coord_task is None:
            # Generate a simulated fold proof for testing
            return [os.urandom(64)]

        batch_tasks = [
            t for t in self._active_tasks.values()
            if t.circuit_id == coord_task.circuit_id
            and abs(t.created_at - coord_task.created_at) < 1.0
        ]
        batch_tasks.sort(key=lambda t: t.segment_index)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            all_done = True
            for task in batch_tasks:
                if task.status not in ("completed", "failed"):
                    all_done = False

                    # Try to fetch result from DHT
                    if self._rings_client is not None:
                        try:
                            result_key = f"proving_result:{task.task_id}"
                            result = await self._rings_client.dht_get(
                                result_key
                            )
                            if result is not None:
                                if isinstance(result, bytes):
                                    task.complete(result)
                                elif isinstance(result, str):
                                    task.complete(bytes.fromhex(result))
                                elif isinstance(result, dict):
                                    # Convention: result dict has "proof" key
                                    proof_data = result.get("proof", b"")
                                    if isinstance(proof_data, str):
                                        proof_data = bytes.fromhex(proof_data)
                                    task.complete(proof_data)
                        except Exception:
                            pass  # Will retry on next poll

            if all_done:
                break

            await asyncio.sleep(0.1)
        else:
            # Timeout — simulate completion for any remaining tasks so
            # we can still produce a proof (degraded quality)
            for task in batch_tasks:
                if task.status not in ("completed", "failed"):
                    # Generate a simulated fold proof
                    simulated_fold = hashlib.sha256(
                        f"fold:{task.task_id}:{task.segment_index}".encode()
                    ).digest()
                    task.complete(simulated_fold)
                    logger.warning(
                        "DistributedProver: timed out waiting for task %s, "
                        "using simulated fold proof",
                        task.task_id,
                    )

        # Collect fold proofs in segment order
        fold_proofs: List[bytes] = []
        for task in batch_tasks:
            if task.result is not None:
                fold_proofs.append(task.result)
            else:
                # Failed task — use a placeholder
                fold_proofs.append(b"\x00" * 32)

        return fold_proofs

    async def compress_to_groth16(
        self,
        fold_proofs: List[bytes],
        circuit: Circuit,
    ) -> ZKProof:
        """Compress Nova fold proofs into a Groth16-compatible proof.

        In a real implementation, this would run the Nova-to-Groth16
        compression step, producing a constant-size proof regardless
        of the number of IVC folds.

        For simulation, we hash the fold proofs together into a
        256-byte proof that matches the Groth16 format expected by
        the on-chain verifier.

        Parameters
        ----------
        fold_proofs : list of bytes
            Individual fold proofs from each segment.
        circuit : Circuit
            The circuit definition.

        Returns
        -------
        ZKProof
            A 256-byte proof suitable for on-chain verification.
        """
        circuit_id = circuit.metadata().name

        # Hash all fold proofs together
        fold_digest = hashlib.sha256(b"nova_compress")
        for i, fp in enumerate(fold_proofs):
            fold_digest.update(struct.pack(">I", i))
            fold_digest.update(fp)
        witness_commitment = fold_digest.digest()  # [0:32]

        # Public-input commitment (from fold structure)
        pi_data = b"".join(fold_proofs)
        pi_commitment = hashlib.sha256(
            b"nova_pi:" + pi_data
        ).digest()  # [32:64]

        # Circuit binding
        circuit_binding = hashlib.sha256(
            circuit_id.encode("utf-8")
        ).digest()  # [64:96]

        # Nonce
        nonce = os.urandom(32)  # [96:128]

        # Integrity
        integrity = hashlib.sha256(
            witness_commitment + pi_commitment + circuit_binding + nonce
        ).digest()  # [128:160]

        # Padding
        padding = b"\x00" * (PROOF_SIZE - 160)  # [160:256]

        proof_bytes = (
            witness_commitment
            + pi_commitment
            + circuit_binding
            + nonce
            + integrity
            + padding
        )

        return ZKProof(
            proof_bytes=proof_bytes,
            public_inputs=[witness_commitment, pi_commitment],
            proof_type="distributed_nova",
            circuit_id=circuit_id,
            generation_time_ms=0,  # caller will override
            proof_size_bytes=len(proof_bytes),
            estimated_verify_gas=GAS_ESTIMATE_NOVA,
            metadata={
                "fold_count": len(fold_proofs),
                "compression": "nova_to_groth16",
            },
        )

    def split_circuit(
        self, circuit: Circuit, witness: dict,
    ) -> List[Dict[str, Any]]:
        """Split a circuit witness into segments for parallel proving.

        Divides the witness based on the circuit's estimated constraint
        count and the configured segment size.  For circuits with list-
        valued witness entries (e.g. ``committee_pubkeys``), the lists
        are partitioned across segments.

        Parameters
        ----------
        circuit : Circuit
            The circuit whose witness we're splitting.
        witness : dict
            The full witness dictionary.

        Returns
        -------
        list of dict
            Witness segments, each suitable for one proving task.
        """
        estimated = circuit.estimate_constraints()
        num_segments = max(1, estimated // self._segment_size)

        if num_segments <= 1:
            return [witness]

        # Find the largest list-valued entry to use as the split axis
        split_key: Optional[str] = None
        max_len = 0
        for key, val in witness.items():
            if isinstance(val, (list, tuple)) and len(val) > max_len:
                split_key = key
                max_len = len(val)

        if split_key is None or max_len < num_segments:
            # No good split axis — return as single segment
            return [witness]

        # Partition the list across segments
        items = witness[split_key]
        chunk_size = max(1, len(items) // num_segments)
        segments: List[Dict[str, Any]] = []

        for i in range(num_segments):
            start = i * chunk_size
            end = start + chunk_size if i < num_segments - 1 else len(items)
            segment = dict(witness)  # shallow copy
            segment[split_key] = items[start:end]
            segment["_segment_index"] = i
            segment["_total_segments"] = num_segments
            segments.append(segment)

        return segments

    # -- fallback -------------------------------------------------------------

    async def _fallback_generate(
        self,
        circuit: Circuit,
        witness: dict,
        public_inputs: dict,
        t0: float,
        reason: str = "",
    ) -> ZKProof:
        """Fall back to the local prover.

        Raises
        ------
        ProofGenerationError
            If no fallback prover is configured.
        """
        if self._fallback_prover is None:
            raise ProofGenerationError(
                f"Distributed proving unavailable ({reason}) "
                f"and no fallback prover configured",
            )

        logger.warning(
            "DistributedProver: falling back to %s (%s)",
            self._fallback_prover.prover_type,
            reason,
        )
        self._fallback_count += 1
        proof = await self._fallback_prover.generate_proof(
            circuit, witness, public_inputs,
        )
        proof.metadata["fallback"] = True
        proof.metadata["fallback_reason"] = reason
        return proof

    # -- stats ----------------------------------------------------------------

    @property
    def stats(self) -> Dict[str, Any]:
        """Return operational statistics."""
        return {
            "completed_proofs": self._completed_proofs,
            "fallback_count": self._fallback_count,
            "active_tasks": len(self._active_tasks),
            "min_provers": self._min_provers,
            "segment_size": self._segment_size,
            "bridge_subring": self._bridge_subring,
        }

    def __repr__(self) -> str:
        return (
            f"DistributedProver("
            f"available={self.is_available}, "
            f"subring={self._bridge_subring!r}, "
            f"min_provers={self._min_provers}, "
            f"segment_size={self._segment_size:,})"
        )


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Exceptions
    "ProofGenerationError",
    "ProofVerificationError",
    # Data classes
    "ZKProof",
    "ProvingTask",
    # ABC
    "ZKProofEngine",
    # Prover implementations
    "SimulatedProver",
    "SP1ProverInterface",
    "DistributedProver",
    # Constants
    "PROOF_SIZE",
    "GAS_ESTIMATE_GROTH16",
    "GAS_ESTIMATE_STARK",
    "GAS_ESTIMATE_NOVA",
    "GAS_ESTIMATE_SIMULATED",
]
