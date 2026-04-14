"""
Real Groth16 ZK proof engine using circom/snarkjs.

Provides :class:`SnarkJSProver`, a concrete :class:`ZKProofEngine`
implementation that generates and verifies Groth16 proofs by calling
the ``snarkjs`` CLI and using Poseidon-hashed Merkle tree witnesses
generated via Node.js helpers.

The circuit (:file:`circuits/withdrawal.circom`) enforces:

1. **Balance sufficiency** — ``amount ≤ balance`` via 64-bit range check
2. **Account leaf** — ``Poseidon(secret, balance, nonce)``
3. **Merkle proof** — path from leaf to ``stateRoot`` using Poseidon
4. **Root match** — computed root equals public ``stateRoot``
5. **Recipient binding** — ``recipientHash`` is bound to the proof

Usage
-----
::

    prover = SnarkJSProver(circuits_dir="/shared/asi-build/circuits")
    if prover.is_available:
        proof = await prover.generate_proof(circuit, witness, public_inputs)
        valid = await prover.verify_proof(circuit, proof, public_inputs)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .circuits import Circuit
from .prover import (
    ProofGenerationError,
    ProofVerificationError,
    ZKProof,
    ZKProofEngine,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default path to the circuits directory relative to project root
DEFAULT_CIRCUITS_DIR = Path(__file__).resolve().parents[5] / "circuits"

#: BN254 scalar field order
BN254_FIELD_ORDER = (
    21888242871839275222246405745257275088548364400416034343698204186575808495617
)

#: Estimated gas for Groth16 on-chain verification (~230K for BN254 pairing)
GROTH16_VERIFY_GAS = 230_000


# ---------------------------------------------------------------------------
# SnarkJSProver
# ---------------------------------------------------------------------------


class SnarkJSProver(ZKProofEngine):
    """Groth16 proof engine using circom circuits and snarkjs CLI.

    Parameters
    ----------
    circuits_dir : str or Path
        Root directory containing the circuit source, ``build/`` artifacts,
        and ``node_modules/``.
    snarkjs_bin : str
        Path or name of the ``snarkjs`` executable.
    node_bin : str
        Path or name of the ``node`` executable.
    circuit_name : str
        Name of the compiled circuit (default ``"withdrawal"``).
    """

    def __init__(
        self,
        circuits_dir: str | Path | None = None,
        snarkjs_bin: str = "snarkjs",
        node_bin: str = "node",
        circuit_name: str = "withdrawal",
    ):
        self._circuits_dir = Path(circuits_dir or DEFAULT_CIRCUITS_DIR)
        self._snarkjs = snarkjs_bin
        self._node = node_bin
        self._circuit_name = circuit_name
        self._build_dir = self._circuits_dir / "build"

        # Key paths
        self._wasm_path = (
            self._build_dir
            / f"{circuit_name}_js"
            / f"{circuit_name}.wasm"
        )
        self._zkey_path = self._build_dir / f"{circuit_name}_final.zkey"
        self._vkey_path = self._build_dir / "verification_key.json"
        self._witness_gen = (
            self._build_dir / f"{circuit_name}_js" / "generate_witness.js"
        )

        # Statistics
        self._proofs_generated = 0
        self._proofs_verified = 0
        self._total_gen_time_ms = 0
        self._total_verify_time_ms = 0

    # -- ZKProofEngine interface ---------------------------------------------

    @property
    def prover_type(self) -> str:
        """Return ``"groth16_snarkjs"``."""
        return "groth16_snarkjs"

    @property
    def is_available(self) -> bool:
        """Check if snarkjs is installed and circuit artifacts exist."""
        if not self._wasm_path.exists():
            return False
        if not self._zkey_path.exists():
            return False
        if not self._vkey_path.exists():
            return False
        # Check snarkjs binary
        try:
            subprocess.run(
                [self._snarkjs, "--version"],
                capture_output=True,
                timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    async def generate_proof(
        self,
        circuit: Circuit,
        witness: dict,
        public_inputs: dict,
    ) -> ZKProof:
        """Generate a Groth16 proof via snarkjs.

        Parameters
        ----------
        circuit : Circuit
            The circuit description (used for ``circuit_id``).
        witness : dict
            Private witness values (``secret``, ``balance``,
            ``pathElements``, ``pathIndices``).
        public_inputs : dict
            Public input values (``amount``, ``nonce``,
            ``recipientHash``, ``stateRoot``).

        Returns
        -------
        ZKProof
            The generated proof with formatted bytes for on-chain
            submission.
        """
        if not self.is_available:
            raise ProofGenerationError(
                "snarkjs prover not available: check circuit artifacts"
            )

        start_ms = time.monotonic_ns() // 1_000_000

        # Merge all inputs into a single input.json
        all_inputs = {**public_inputs, **witness}
        # Ensure all values are strings (snarkjs expects string numbers)
        input_json = _stringify_inputs(all_inputs)

        try:
            with tempfile.TemporaryDirectory(
                prefix="snarkjs_"
            ) as tmpdir:
                tmpdir = Path(tmpdir)
                input_path = tmpdir / "input.json"
                witness_path = tmpdir / "witness.wtns"
                proof_path = tmpdir / "proof.json"
                public_path = tmpdir / "public.json"

                # Write input
                input_path.write_text(json.dumps(input_json))

                # Generate witness
                await self._run_cmd(
                    [
                        self._node,
                        str(self._witness_gen),
                        str(self._wasm_path),
                        str(input_path),
                        str(witness_path),
                    ],
                    "witness generation",
                )

                # Generate proof
                await self._run_cmd(
                    [
                        self._snarkjs,
                        "groth16",
                        "prove",
                        str(self._zkey_path),
                        str(witness_path),
                        str(proof_path),
                        str(public_path),
                    ],
                    "proof generation",
                )

                # Read outputs
                proof_data = json.loads(proof_path.read_text())
                public_data = json.loads(public_path.read_text())

        except ProofGenerationError:
            raise
        except Exception as exc:
            raise ProofGenerationError(
                f"snarkjs proof generation failed: {exc}"
            ) from exc

        elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

        # Format proof bytes (256 bytes = 8 x 32-byte field elements)
        proof_bytes = self._encode_proof(proof_data)

        # Format public inputs as bytes32
        public_bytes = [
            int(s).to_bytes(32, "big") for s in public_data
        ]

        self._proofs_generated += 1
        self._total_gen_time_ms += elapsed_ms

        circuit_id = getattr(circuit, "name", "withdrawal")

        return ZKProof(
            proof_bytes=proof_bytes,
            public_inputs=public_bytes,
            proof_type="groth16",
            circuit_id=circuit_id,
            generation_time_ms=elapsed_ms,
            proof_size_bytes=len(proof_bytes),
            estimated_verify_gas=GROTH16_VERIFY_GAS,
            metadata={
                "prover": "snarkjs",
                "curve": proof_data.get("curve", "bn128"),
                "protocol": proof_data.get("protocol", "groth16"),
                "raw_proof": proof_data,
                "raw_public": public_data,
            },
        )

    async def verify_proof(
        self,
        circuit: Circuit,
        proof: ZKProof,
        public_inputs: dict,
    ) -> bool:
        """Verify a Groth16 proof locally via snarkjs.

        Parameters
        ----------
        circuit : Circuit
            The circuit description.
        proof : ZKProof
            The proof to verify (must have ``raw_proof`` and
            ``raw_public`` in metadata, OR will be decoded from bytes).
        public_inputs : dict
            Public input values (used only for logging; the proof's
            embedded public signals are authoritative).

        Returns
        -------
        bool
            True if the proof is valid.
        """
        if not self.is_available:
            raise ProofVerificationError(
                "snarkjs prover not available"
            )

        start_ms = time.monotonic_ns() // 1_000_000

        try:
            # Extract raw proof/public from metadata if available
            raw_proof = proof.metadata.get("raw_proof")
            raw_public = proof.metadata.get("raw_public")

            if raw_proof is None or raw_public is None:
                # Decode from proof_bytes
                raw_proof = self._decode_proof(proof.proof_bytes)
                raw_public = [
                    str(int.from_bytes(pi, "big"))
                    for pi in proof.public_inputs
                ]

            with tempfile.TemporaryDirectory(
                prefix="snarkjs_verify_"
            ) as tmpdir:
                tmpdir = Path(tmpdir)
                proof_path = tmpdir / "proof.json"
                public_path = tmpdir / "public.json"

                proof_path.write_text(json.dumps(raw_proof))
                public_path.write_text(json.dumps(raw_public))

                result = await self._run_cmd(
                    [
                        self._snarkjs,
                        "groth16",
                        "verify",
                        str(self._vkey_path),
                        str(public_path),
                        str(proof_path),
                    ],
                    "proof verification",
                    check=False,
                )

                is_valid = "OK" in result.stdout

        except ProofVerificationError:
            raise
        except Exception as exc:
            raise ProofVerificationError(
                f"snarkjs verification failed: {exc}"
            ) from exc

        elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
        self._proofs_verified += 1
        self._total_verify_time_ms += elapsed_ms

        return is_valid

    # -- Proof encoding/decoding ---------------------------------------------

    @staticmethod
    def _encode_proof(proof_data: dict) -> bytes:
        """Encode snarkjs proof.json into 256-byte on-chain format.

        Layout (8 × 32 bytes):
            [0]  a[0]
            [1]  a[1]
            [2]  b[0][0]
            [3]  b[0][1]
            [4]  b[1][0]
            [5]  b[1][1]
            [6]  c[0]
            [7]  c[1]
        """
        pi_a = proof_data["pi_a"]
        pi_b = proof_data["pi_b"]
        pi_c = proof_data["pi_c"]

        elements = [
            int(pi_a[0]),
            int(pi_a[1]),
            int(pi_b[0][0]),
            int(pi_b[0][1]),
            int(pi_b[1][0]),
            int(pi_b[1][1]),
            int(pi_c[0]),
            int(pi_c[1]),
        ]

        proof_bytes = b""
        for e in elements:
            proof_bytes += e.to_bytes(32, "big")

        assert len(proof_bytes) == 256
        return proof_bytes

    @staticmethod
    def _decode_proof(proof_bytes: bytes) -> dict:
        """Decode 256-byte proof back to snarkjs proof.json format."""
        assert len(proof_bytes) == 256

        def _read(offset: int) -> str:
            return str(int.from_bytes(proof_bytes[offset : offset + 32], "big"))

        return {
            "pi_a": [_read(0), _read(32), "1"],
            "pi_b": [
                [_read(64), _read(96)],
                [_read(128), _read(160)],
                ["1", "0"],
            ],
            "pi_c": [_read(192), _read(224), "1"],
            "protocol": "groth16",
            "curve": "bn128",
        }

    # -- Solidity calldata formatting ----------------------------------------

    @staticmethod
    def format_calldata(proof: ZKProof) -> Tuple[bytes, List[bytes]]:
        """Format proof for the WithdrawalVerifierBridge contract.

        Returns ``(proof_bytes, public_inputs)`` ready for ABI encoding
        and on-chain submission.
        """
        return proof.proof_bytes, proof.public_inputs

    @staticmethod
    def format_calldata_snarkjs(proof: ZKProof) -> dict:
        """Format proof for direct snarkjs-style Solidity verifier.

        Returns a dict with keys ``a``, ``b``, ``c``, ``input`` as
        hex strings ready for ``cast`` or ethers.js.
        """
        raw = proof.metadata.get("raw_proof")
        raw_pub = proof.metadata.get("raw_public")

        if raw is None:
            raw = SnarkJSProver._decode_proof(proof.proof_bytes)
        if raw_pub is None:
            raw_pub = [
                str(int.from_bytes(pi, "big"))
                for pi in proof.public_inputs
            ]

        def _hex(val: str) -> str:
            return hex(int(val))

        return {
            "a": [_hex(raw["pi_a"][0]), _hex(raw["pi_a"][1])],
            "b": [
                [_hex(raw["pi_b"][0][0]), _hex(raw["pi_b"][0][1])],
                [_hex(raw["pi_b"][1][0]), _hex(raw["pi_b"][1][1])],
            ],
            "c": [_hex(raw["pi_c"][0]), _hex(raw["pi_c"][1])],
            "input": [_hex(s) for s in raw_pub],
        }

    # -- Statistics -----------------------------------------------------------

    @property
    def stats(self) -> dict:
        """Return prover statistics."""
        return {
            "prover_type": self.prover_type,
            "proofs_generated": self._proofs_generated,
            "proofs_verified": self._proofs_verified,
            "avg_gen_time_ms": (
                self._total_gen_time_ms / self._proofs_generated
                if self._proofs_generated > 0
                else 0
            ),
            "avg_verify_time_ms": (
                self._total_verify_time_ms / self._proofs_verified
                if self._proofs_verified > 0
                else 0
            ),
            "circuits_dir": str(self._circuits_dir),
            "circuit_name": self._circuit_name,
            "is_available": self.is_available,
        }

    # -- Internal helpers ----------------------------------------------------

    async def _run_cmd(
        self,
        cmd: List[str],
        description: str,
        check: bool = True,
        timeout: int = 60,
    ) -> subprocess.CompletedProcess:
        """Run a subprocess asynchronously.

        Parameters
        ----------
        cmd : list of str
            Command and arguments.
        description : str
            Human-readable description for error messages.
        check : bool
            If True, raise on non-zero exit code.
        timeout : int
            Timeout in seconds.
        """
        logger.debug("Running %s: %s", description, " ".join(cmd))

        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    ),
                ),
                timeout=timeout + 5,
            )
        except asyncio.TimeoutError:
            raise ProofGenerationError(
                f"{description} timed out after {timeout}s"
            )
        except subprocess.TimeoutExpired:
            raise ProofGenerationError(
                f"{description} timed out after {timeout}s"
            )

        if check and result.returncode != 0:
            raise ProofGenerationError(
                f"{description} failed (exit {result.returncode}): "
                f"{result.stderr[:500]}"
            )

        return result

    def __repr__(self) -> str:
        return (
            f"SnarkJSProver(circuit={self._circuit_name!r}, "
            f"available={self.is_available}, "
            f"proofs={self._proofs_generated})"
        )


# ---------------------------------------------------------------------------
# Witness generation helpers
# ---------------------------------------------------------------------------


@dataclass
class WithdrawalWitness:
    """Structured witness for the withdrawal circuit.

    All numeric fields are Python ints; they are stringified when
    passed to the circuit.

    The ``chain_id`` field is required to prevent cross-chain replay attacks
    (#1242).  It must match the EVM ``block.chainid`` of the destination
    bridge contract.  Known chain IDs:
        - Sepolia:       11155111
        - Base Sepolia:  84532
        - ARC Testnet:   5042002
    """

    # Public inputs
    amount: int
    nonce: int
    recipient_hash: int
    state_root: int
    chain_id: int  # EVM chain ID — binds proof to a specific chain (#1242)

    # Private inputs
    secret: int
    balance: int
    path_elements: List[int] = field(default_factory=list)
    path_indices: List[int] = field(default_factory=list)

    def to_circuit_inputs(self) -> Tuple[dict, dict]:
        """Split into ``(witness, public_inputs)`` dicts for the prover.

        The ``public`` dict contains 5 signals matching the circuit's
        ``component main {public [...]}`` declaration in the same order.
        ``publicInputs[4]`` in the on-chain call must equal ``block.chainid``.

        Returns
        -------
        tuple of (dict, dict)
            ``(witness_dict, public_inputs_dict)``
        """
        witness = {
            "secret": self.secret,
            "balance": self.balance,
            "pathElements": self.path_elements,
            "pathIndices": self.path_indices,
        }
        public = {
            "amount": self.amount,
            "nonce": self.nonce,
            "recipientHash": self.recipient_hash,
            "stateRoot": self.state_root,
            "chainId": self.chain_id,  # Must equal block.chainid on destination (#1242)
        }
        return witness, public

    def validate(self) -> List[str]:
        """Basic validation of witness consistency.

        Returns a list of error strings (empty = valid).
        """
        errors: List[str] = []
        if self.amount > self.balance:
            errors.append(
                f"amount ({self.amount}) exceeds balance ({self.balance})"
            )
        if self.amount < 0:
            errors.append(f"negative amount: {self.amount}")
        if self.balance < 0:
            errors.append(f"negative balance: {self.balance}")
        if len(self.path_elements) != len(self.path_indices):
            errors.append(
                f"path length mismatch: {len(self.path_elements)} "
                f"elements vs {len(self.path_indices)} indices"
            )
        if not all(idx in (0, 1) for idx in self.path_indices):
            errors.append("path indices must be 0 or 1")
        if self.balance - self.amount >= 2**64:
            errors.append("balance - amount exceeds 64-bit range")
        return errors


# ---------------------------------------------------------------------------
# Poseidon hash helpers (pure Python, field arithmetic)
# ---------------------------------------------------------------------------

# We need Poseidon for computing witnesses in Python.
# For production, use the Node.js poseidon-lite. Here we provide a
# subprocess-based helper that calls Node.js for hash computation.


async def poseidon_hash(
    inputs: List[int],
    node_bin: str = "node",
    circuits_dir: str | Path | None = None,
) -> int:
    """Compute Poseidon hash via Node.js poseidon-lite.

    Parameters
    ----------
    inputs : list of int
        1-16 field elements to hash.
    node_bin : str
        Path to Node.js.
    circuits_dir : str or Path or None
        Directory containing ``node_modules/poseidon-lite``.

    Returns
    -------
    int
        Poseidon hash output.
    """
    cdir = Path(circuits_dir or DEFAULT_CIRCUITS_DIR)
    js_code = f"""
    const {{ poseidon{len(inputs)} }} = require("poseidon-lite");
    const result = poseidon{len(inputs)}([{','.join(f'BigInt("{x}")' for x in inputs)}]);
    console.log(result.toString());
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: subprocess.run(
            [node_bin, "-e", js_code],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(cdir),
        ),
    )
    if result.returncode != 0:
        raise RuntimeError(f"poseidon hash failed: {result.stderr}")
    return int(result.stdout.strip())


async def compute_withdrawal_witness(
    secret: int,
    balance: int,
    amount: int,
    nonce: int,
    recipient_address: int,
    merkle_siblings: List[int] | None = None,
    merkle_indices: List[int] | None = None,
    tree_depth: int = 10,
    node_bin: str = "node",
    circuits_dir: str | Path | None = None,
) -> WithdrawalWitness:
    """Compute a full withdrawal witness with Poseidon hashes.

    If ``merkle_siblings`` is None, generates a test Merkle tree.

    Parameters
    ----------
    secret : int
        User's secret key.
    balance : int
        Current balance.
    amount : int
        Withdrawal amount.
    nonce : int
        Replay protection nonce.
    recipient_address : int
        Ethereum recipient address as int.
    merkle_siblings : list of int or None
        Sibling hashes for the Merkle proof.
    merkle_indices : list of int or None
        Left/right direction flags.
    tree_depth : int
        Depth of the Merkle tree (must match circuit parameter).
    node_bin : str
        Path to Node.js binary.
    circuits_dir : str or Path or None
        Path to circuits directory.

    Returns
    -------
    WithdrawalWitness
    """
    cdir = circuits_dir or DEFAULT_CIRCUITS_DIR

    # Compute account leaf: Poseidon(secret, balance, nonce)
    leaf = await poseidon_hash(
        [secret, balance, nonce], node_bin, cdir
    )

    # Compute recipient hash: Poseidon(address, 0)
    recipient_hash = await poseidon_hash(
        [recipient_address, 0], node_bin, cdir
    )

    if merkle_siblings is None:
        # Generate test Merkle tree
        merkle_siblings = list(range(100, 100 + tree_depth))
        merkle_indices = [0] * tree_depth

    if merkle_indices is None:
        merkle_indices = [0] * tree_depth

    # Compute state root by walking the Merkle path
    current = leaf
    for i in range(tree_depth):
        if merkle_indices[i] == 0:
            # Current on left, sibling on right
            current = await poseidon_hash(
                [current, merkle_siblings[i]], node_bin, cdir
            )
        else:
            # Current on right, sibling on left
            current = await poseidon_hash(
                [merkle_siblings[i], current], node_bin, cdir
            )

    return WithdrawalWitness(
        amount=amount,
        nonce=nonce,
        recipient_hash=recipient_hash,
        state_root=current,
        secret=secret,
        balance=balance,
        path_elements=merkle_siblings,
        path_indices=merkle_indices,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stringify_inputs(inputs: dict) -> dict:
    """Recursively convert all numeric values to strings for snarkjs."""
    result = {}
    for k, v in inputs.items():
        if isinstance(v, list):
            result[k] = [
                str(x) if isinstance(x, int) else x for x in v
            ]
        elif isinstance(v, int):
            result[k] = str(v)
        else:
            result[k] = v
    return result
