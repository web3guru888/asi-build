"""
Rings Network Python SDK
=========================

Async client library for the `Rings Network <https://ringsnetwork.io>`_ —
a Chord-based, DID-authenticated peer-to-peer overlay network with
cryptoeconomic reputation.

Modules
~~~~~~~

- :mod:`~.client`     — ``RingsClient``: DHT, Chord ring, Sub-Rings, sessions
- :mod:`~.did`        — ``RingsDID``: DID creation, resolution, proof, VIDs
- :mod:`~.reputation` — ``ReputationClient``: local/global scoring, trust checks

Quick Start
~~~~~~~~~~~

::

    from asi_build.rings import RingsClient, RingsDID, ReputationClient

    async def main():
        async with RingsClient("ws://localhost:50000") as client:
            # Store/retrieve from Chord DHT
            await client.dht_put("my-key", {"data": 42})
            value = await client.dht_get("my-key")

            # DID identity
            did_mgr = RingsDID(client)
            did, doc = did_mgr.create_did()

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
    # Reputation
    "ReputationClient",
    "BehaviourType",
    "TrustTier",
    "LocalObservation",
    "LocalRankRecord",
    "GlobalRankRecord",
    "SlashReport",
]

__version__ = "0.1.0"
__maturity__ = "beta"
