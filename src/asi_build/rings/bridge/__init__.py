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
"""

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
    "BridgeProtocol",
    "BridgeMessage",
    "BridgeValidator",
    "BridgeState",
    "DepositRecord",
    "WithdrawalRecord",
    "EthLightClient",
    "HeliosLightClient",
    "MockLightClient",
    "BeaconHeader",
    "SyncCommittee",
    "StateProof",
    "EventProof",
    "MerklePatriciaVerifier",
    "AccountState",
    "TransactionReceipt",
    "RLPDecoder",
]
