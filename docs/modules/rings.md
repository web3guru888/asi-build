# Rings

> **Maturity**: `beta` · **Adapter**: `RingsNetworkAdapter`

Python SDK for the Rings P2P decentralized network. Provides a full async client for DHT (Distributed Hash Table) operations using Chord protocol, W3C-compliant DID (Decentralized Identifier) creation and verification with secp256k1/ed25519 key support, and a local reputation scoring system with 3-factor trust assessment (success rate, validity rate, average score) and exponential decay. Supports Sub-Ring creation for topic-partitioned overlay networks and end-to-end encrypted sessions between peers.

## Key Classes

| Class | Description |
|-------|-------------|
| `RingsClient` | Async DHT put/get/delete, Chord ring join/find_successor, Sub-Ring create/join/broadcast, E2E sessions |
| `RingsDID` | W3C DID creation with secp256k1/ed25519 key support |
| `DIDDocument` | W3C-compliant DID Document with serialization |
| `DIDKeyPair` | Cryptographic key pair for DID operations |
| `DIDProof` | Proof generation and verification for DID authentication |
| `KeyCurve` | Enum for supported cryptographic curves |
| `VerificationType` | Enum for verification method types |
| `ReputationClient` | 3-factor reputation scoring with trust tiers and exponential decay |
| `TrustTier` | Enum: 5-level trust classification |
| `BehaviourType` | Enum for peer behavior categorization |
| `LocalObservation` | Local observation record for reputation tracking |
| `LocalRankRecord` | Local ranking record for a peer |
| `GlobalRankRecord` | Global ranking record aggregated across observers |
| `SlashReport` | Slashing report for Byzantine behavior (auto-penalizes 3x) |
| `RingsTransport` | Pluggable transport layer protocol |
| `InMemoryTransport` | In-memory transport for testing |
| `ConnectionState` | Enum for connection lifecycle states |
| `DHTOperator` | Enum for DHT operations (PUT, GET, DELETE, EXTEND) |
| `PeerInfo` | Peer information data model |
| `SubRingInfo` | Sub-Ring metadata |
| `SessionInfo` | E2E session metadata |
| `FingerEntry` | Chord finger table entry |

## Example Usage

```python
from asi_build.rings import RingsClient, InMemoryTransport, RingsDID
transport = InMemoryTransport()
client = RingsClient(transport=transport)
await client.join(bootstrap="ring://node1:9090")
did = RingsDID.create(curve="ed25519")
await client.dht_put("research/hypothesis_1", data={"status": "confirmed"})
```

## Blackboard Integration

RingsNetworkAdapter publishes peer discovery events, DID operations, reputation threshold crossings, and Sub-Ring broadcasts; consumes reasoning/KG/consciousness entries for P2P replication across the network.
