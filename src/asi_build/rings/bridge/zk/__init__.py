# ruff: noqa: F401
"""
ZK Proof System for Rings ↔ Ethereum Bridge
=============================================

Provides zero-knowledge proof generation, verification, and coordination
for trustless bridge operations.  The package contains:

- :mod:`.circuits`    — Arithmetic circuit definitions (BLS, MPT, Withdrawal,
  Committee Rotation) with Python-simulated constraint verification.
- :mod:`.prover`      — Proof engines: ``SimulatedProver`` (testing),
  ``SP1ProverInterface`` (future zkVM), ``DistributedProver`` (Rings IVC).
- :mod:`.coordinator` — ``BridgeProofCoordinator``: full lifecycle
  orchestration with caching, batching, and statistics.
- :mod:`.bls`         — BLS12-381 primitives for sync committee verification.
- :mod:`.ssz`         — SSZ (Simple Serialize) encoding/decoding/Merkleization
  for beacon chain types.
- :mod:`.snarkjs_prover` — Real Groth16 proofs via circom/snarkjs:
  ``SnarkJSProver`` engine, ``WithdrawalWitness`` builder, and Poseidon
  hash helpers for withdrawal proof generation.
"""

from .bls import (
    BLS12381,
    BLSKeyPair,
    BLSPublicKey,
    BLSSignature,
    SyncCommitteeBLS,
)
from .real_bls import (
    RealBLS12381,
    RealBLSKeyPair,
    RealSyncCommitteeBLS,
    get_bls_backend,
)
from .circuits import (
    ALL_CIRCUITS,
    BLSVerificationCircuit,
    BridgeWithdrawalCircuit,
    Circuit,
    CircuitMetadata,
    MerklePatriciaCircuit,
    SyncCommitteeRotationCircuit,
)
from .coordinator import (
    BridgeProofCoordinator,
    ProofCache,
    ProofStats,
)
from .prover import (
    DistributedProver,
    ProofGenerationError,
    ProofVerificationError,
    ProvingTask,
    SimulatedProver,
    SP1ProverInterface,
    ZKProof,
    ZKProofEngine,
)
from .snarkjs_prover import (
    SnarkJSProver,
    WithdrawalWitness,
    compute_withdrawal_witness,
    poseidon_hash,
)
from .ssz import (
    SSZ,
    BeaconBlockHeader as SSZBeaconBlockHeader,
    LightClientUpdate,
    SyncCommitteeSSZ,
)

__all__ = [
    # Circuits
    "Circuit",
    "CircuitMetadata",
    "BLSVerificationCircuit",
    "MerklePatriciaCircuit",
    "BridgeWithdrawalCircuit",
    "SyncCommitteeRotationCircuit",
    "ALL_CIRCUITS",
    # Provers
    "ZKProofEngine",
    "ZKProof",
    "SimulatedProver",
    "SP1ProverInterface",
    "DistributedProver",
    "ProvingTask",
    "ProofGenerationError",
    "ProofVerificationError",
    # Coordinator
    "BridgeProofCoordinator",
    "ProofCache",
    "ProofStats",
    # BLS
    "BLS12381",
    "BLSKeyPair",
    "BLSPublicKey",
    "BLSSignature",
    "SyncCommitteeBLS",
    # Real BLS (py_ecc backed)
    "RealBLS12381",
    "RealBLSKeyPair",
    "RealSyncCommitteeBLS",
    "get_bls_backend",
    # SnarkJS (real Groth16)
    "SnarkJSProver",
    "WithdrawalWitness",
    "compute_withdrawal_witness",
    "poseidon_hash",
    # SSZ
    "SSZ",
    "SSZBeaconBlockHeader",
    "LightClientUpdate",
    "SyncCommitteeSSZ",
]
