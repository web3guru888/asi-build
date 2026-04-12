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
- :mod:`~.merkle_patricia`  — ``MerklePatriciaVerifier``: EIP-1186 proof
  verification for Ethereum state, storage, and receipt tries.
- :mod:`~.contract_client`  — ``BridgeContractClient``, ``BridgeDeployer``:
  Python bindings for on-chain bridge contracts.
- :mod:`~.e2e`              — ``BridgeOrchestrator``: end-to-end deposit →
  attest → withdraw relay loop.
"""

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

__all__ = [
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
]
