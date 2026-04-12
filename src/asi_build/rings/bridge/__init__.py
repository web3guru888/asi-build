"""
Rings ↔ Ethereum Bridge
========================

Bridge protocol for trustless cross-chain operations between
Rings Network and Ethereum, using light client verification.

Modules
~~~~~~~

- :mod:`~.protocol`         — ``BridgeProtocol``, ``BridgeValidator``: DHT key
  schema and validator node logic for the bridge Sub-Ring.
- :mod:`~.light_client`     — ``EthLightClient``: abstract Ethereum light client
  with Helios stub and in-memory mock.
- :mod:`~.beacon_client`    — ``BeaconAPILightClient``: production Beacon Chain
  light client connecting to real Beacon API + execution layer endpoints.
- :mod:`~.merkle_patricia`  — ``MerklePatriciaVerifier``: EIP-1186 proof
  verification for Ethereum state, storage, and receipt tries.
- :mod:`~.contract_client`  — ``BridgeContractClient``, ``BridgeDeployer``:
  Python bindings for on-chain bridge contracts.
- :mod:`~.e2e`              — ``BridgeOrchestrator``: end-to-end deposit →
  attest → withdraw relay loop.
- :mod:`~.zk_prover`        — ``Groth16Prover``, ``Groth16Verifier``:
  real BN254 pairing-based ZK proof system for bridge operations.
- :mod:`~.safety`           — ``BridgeSafetyManager``: circuit breakers,
  anomaly detection, rate-limit monitoring, validator health tracking.
- :mod:`~.zk`               — ZK proof sub-package: circuits, provers,
  coordinator, BLS12-381 primitives, SSZ encoding.
- :mod:`~.relayer`          — ``BridgeRelayer``: production daemon that
  monitors deposits, processes withdrawals, with health endpoints.
- :mod:`~.consensus`        — ``ValidatorConsensus``: 4/6 threshold
  multi-validator consensus for withdrawal approvals.
- :mod:`~.circuit_breaker`  — ``EnhancedSafetyManager``: proof-failure
  breakers, volume thresholds, per-address rate limits, cooldowns.
- :mod:`~.audit_log`        — ``AuditLogger``: structured JSON logging
  with rotation, trace IDs, and audit trail.
"""

from .beacon_client import (
    BeaconAPIError,
    BeaconAPILightClient,
    ExecutionRPCError,
)
from .contract_client import (
    BRIDGE_ABI,
    TOKEN_ABI,
    VERIFIER_ABI,
    BridgeContractClient,
    BridgeDeployer,
)
from .e2e import (
    BridgeOrchestrator,
    ProcessedDeposit,
)
from .light_client import (
    BeaconHeader,
    EthLightClient,
    EventProof,
    HeliosLightClient,
    MockLightClient,
    StateProof,
    SyncCommittee,
)
from .merkle_patricia import (
    AccountState,
    MerklePatriciaVerifier,
    RLPDecoder,
    TransactionReceipt,
)
from .protocol import (
    BridgeMessage,
    BridgeProtocol,
    BridgeState,
    BridgeValidator,
    DepositRecord,
    WithdrawalRecord,
)
from .safety import (
    AlertSeverity,
    AnomalyDetector,
    BridgeSafetyManager,
    CircuitBreaker,
    RateLimitMonitor,
    SafetyAlert,
    ValidatorHealthMonitor,
)
from .zk_prover import (
    BridgeWithdrawalCircuit,
    Groth16Proof,
    Groth16Prover,
    Groth16Verifier,
    ProvingKey,
    SyncCommitteeCircuit,
    TrustedSetup,
    VerificationKey,
    g1_to_uint256,
    g2_to_uint256,
    vk_to_solidity_args,
)

from .audit_log import AuditLogger
from .circuit_breaker import (
    AddressRateLimiter,
    CooldownGuard,
    EnhancedSafetyManager,
    ProofFailureBreaker,
    VolumeThresholdBreaker,
    WithdrawalAnomalyDetector,
)
from .consensus import (
    ProposalStatus,
    ValidatorConsensus,
    WithdrawalProposal,
)
from .ledger import (
    LedgerKeys,
    LedgerMessage,
    RingsTokenLedger,
    TransferRecord,
    TransferReceipt,
    TransferStatus,
    WithdrawalLock,
)
from .relayer import (
    BridgeRelayer,
    OperationStatus,
    RelayerConfig,
    RelayerDB,
)

__all__ = [
    # Beacon API client
    "BeaconAPILightClient",
    "BeaconAPIError",
    "ExecutionRPCError",
    # Protocol
    "BridgeProtocol",
    "BridgeMessage",
    "BridgeValidator",
    "BridgeState",
    "DepositRecord",
    "WithdrawalRecord",
    # Light client
    "EthLightClient",
    "HeliosLightClient",
    "MockLightClient",
    "BeaconHeader",
    "SyncCommittee",
    "StateProof",
    "EventProof",
    # Merkle Patricia
    "MerklePatriciaVerifier",
    "AccountState",
    "TransactionReceipt",
    "RLPDecoder",
    # Contract client
    "BridgeContractClient",
    "BridgeDeployer",
    "BRIDGE_ABI",
    "VERIFIER_ABI",
    "TOKEN_ABI",
    # Orchestrator
    "BridgeOrchestrator",
    "ProcessedDeposit",
    # Safety
    "AlertSeverity",
    "SafetyAlert",
    "CircuitBreaker",
    "AnomalyDetector",
    "RateLimitMonitor",
    "ValidatorHealthMonitor",
    "BridgeSafetyManager",
    # ZK Prover
    "TrustedSetup",
    "ProvingKey",
    "VerificationKey",
    "Groth16Proof",
    "Groth16Prover",
    "Groth16Verifier",
    "BridgeWithdrawalCircuit",
    "SyncCommitteeCircuit",
    "g1_to_uint256",
    "g2_to_uint256",
    "vk_to_solidity_args",
    # ZK sub-package (Phase 3)
    "zk",
    # Relayer (Phase E)
    "BridgeRelayer",
    "RelayerConfig",
    "RelayerDB",
    "OperationStatus",
    # Consensus (Phase E)
    "ValidatorConsensus",
    "WithdrawalProposal",
    "ProposalStatus",
    # Enhanced circuit breakers (Phase F)
    "EnhancedSafetyManager",
    "ProofFailureBreaker",
    "VolumeThresholdBreaker",
    "WithdrawalAnomalyDetector",
    "AddressRateLimiter",
    "CooldownGuard",
    # Audit logging (Phase F)
    "AuditLogger",
    # Token Ledger (Phase G)
    "RingsTokenLedger",
    "TransferRecord",
    "TransferReceipt",
    "TransferStatus",
    "WithdrawalLock",
    "LedgerKeys",
    "LedgerMessage",
]
