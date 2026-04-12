# Blockchain

> **Maturity**: `alpha` · **Adapter**: `BlockchainBlackboardAdapter`

Cryptographic integrity and audit trail infrastructure using blockchain primitives. Provides hash management (SHA-256, BLAKE2), Merkle tree construction and verification, append-only hash chains for tamper-evident logging, and digital signature management. Designed for ensuring data integrity across the ASI system rather than cryptocurrency applications.

## Key Classes

| Class | Description |
|-------|-------------|
| `HashManager` | Multi-algorithm hash computation and verification |
| `MerkleTree` | Merkle tree construction, proof generation, verification |
| `HashChain` | Append-only tamper-evident log chain |
| `SignatureManager` | Digital signature creation and verification |
| `NetworkConfig` | Blockchain network configuration |

## Example Usage

```python
from asi_build.blockchain import HashManager, MerkleTree
hasher = HashManager(algorithm="sha256")
tree = MerkleTree()
tree.add_leaves(["discovery_1", "discovery_2", "discovery_3"])
root = tree.build()
proof = tree.get_proof("discovery_2")
```

## Blackboard Integration

BlockchainBlackboardAdapter publishes integrity proofs, Merkle roots, and audit events; consumes entries from other modules to create verifiable audit trails.
