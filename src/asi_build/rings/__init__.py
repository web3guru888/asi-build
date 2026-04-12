"""
Rings Network Python SDK
=========================

Async client library for the `Rings Network <https://ringsnetwork.io>`_ —
a Chord-based, DID-authenticated peer-to-peer overlay network with
cryptoeconomic reputation and Ethereum bridge support.

Modules
~~~~~~~

- :mod:`~.client`     — ``RingsClient``: DHT, Chord ring, Sub-Rings, sessions
- :mod:`~.did`        — ``RingsDID``: DID creation (real secp256k1/Ed25519), resolution, proof, VIDs
- :mod:`~.eth_bridge` — ``RingsEthIdentity``: Unified Rings DID + Ethereum address from one key
- :mod:`~.reputation` — ``ReputationClient``: local/global scoring, trust checks
- :mod:`~.bridge`     — Bridge Sub-Ring protocol, Ethereum light client, Merkle-Patricia verification

Quick Start
~~~~~~~~~~~

::

    from asi_build.rings import RingsClient, RingsDID, ReputationClient, RingsEthIdentity

    async def main():
        async with RingsClient("ws://localhost:50000") as client:
            # Store/retrieve from Chord DHT
            await client.dht_put("my-key", {"data": 42})
            value = await client.dht_get("my-key")

            # DID identity (real secp256k1)
            did_mgr = RingsDID(client)
            did, doc = did_mgr.create_did()

            # Unified Rings + Ethereum identity
            identity = RingsEthIdentity.generate()
            print(identity.ethereum_address)  # 0x...
            print(identity.rings_did)         # did:rings:secp256k1:...

            # Reputation
            rep = ReputationClient(client, local_did=did)
            rep.report_behaviour(
                "did:rings:ed25519:abc", BehaviourType.REQUEST_SUCCESS, 0.95
            )

Transport
~~~~~~~~~

The SDK communicates with a Rings node (Rust/WASM) via JSON-RPC over
WebSocket.  For testing, an :class:`~.client.InMemoryTransport` is used
by default — no live node required.

To connect to a real node::

    from asi_build.rings.client import WebSocketTransport  # future
    client = RingsClient("ws://node:50000", transport=WebSocketTransport())
"""

from __future__ import annotations

from .client import (
    ConnectionState,
    DHTOperator,
    FingerEntry,
    InMemoryTransport,
    PeerInfo,
    RingsClient,
    RingsTransport,
    SessionInfo,
    SubRingInfo,
)
from .did import (
    DIDDocument,
    DIDKeyPair,
    DIDProof,
    KeyCurve,
    RingsDID,
    VerificationType,
)
from .eth_bridge import RingsEthIdentity
from .transport import (
    HTTPTransport,
    MultiNodeTransport,
    WebSocketTransport,
    create_transport,
)
from .reputation import (
    BehaviourType,
    GlobalRankRecord,
    LocalObservation,
    LocalRankRecord,
    ReputationClient,
    SlashReport,
    TrustTier,
)

__all__ = [
    # Client
    "RingsClient",
    "RingsTransport",
    "InMemoryTransport",
    "ConnectionState",
    "DHTOperator",
    "PeerInfo",
    "SubRingInfo",
    "SessionInfo",
    "FingerEntry",
    # DID
    "RingsDID",
    "DIDDocument",
    "DIDKeyPair",
    "DIDProof",
    "KeyCurve",
    "VerificationType",
    # Ethereum Bridge Identity
    "RingsEthIdentity",
    # Transport
    "WebSocketTransport",
    "HTTPTransport",
    "MultiNodeTransport",
    "create_transport",
    # Reputation
    "ReputationClient",
    "BehaviourType",
    "TrustTier",
    "LocalObservation",
    "LocalRankRecord",
    "GlobalRankRecord",
    "SlashReport",
]

__version__ = "0.2.0"
__maturity__ = "beta"
