# Blockchain Module

> **Module path**: `src/asi_build/blockchain/`  
> **Size**: 17 files · 5,963 LOC  
> **Status**: ✅ Functional — audit trails, IPFS storage, Web3 integration, cryptographic verification  
> **Issue**: [#96 — Wire Blockchain to Cognitive Blackboard](https://github.com/web3guru888/asi-build/issues) (coming soon)

---

## Overview

The Blockchain module gives ASI:BUILD a **verifiable audit trail** for agent actions. Every cognitive event — goal updates, safety decisions, negotiation outcomes — can be cryptographically signed, hashed into a Merkle chain, stored on IPFS, and anchored to an EVM-compatible blockchain.

It is organized into four sub-packages:

| Sub-package | Purpose |
|-------------|---------|
| `api/` | FastAPI REST endpoints + JWT/API-key auth |
| `crypto/` | Hash management (Merkle trees, hash chains), digital signatures |
| `ipfs/` | IPFS client, pinning service, encrypted data manager |
| `web3_integration/` | Web3 client (multi-RPC failover), contract manager, network config |

---

## Sub-packages

### `api/` — Audit Trail REST API

**Files:** `rest_api.py`, `auth.py`, `middleware.py`

The `AuditTrailAPI` class exposes a FastAPI application with:

- `POST /audit/records` — Create a new audit record (optionally encrypted)
- `GET /audit/records/{id}` — Retrieve and verify a record
- `POST /audit/query` — Batch query by user, event type, time range
- `POST /audit/verify` — Verify record integrity against chain
- `GET /audit/status` — System health + chain connectivity

**Authentication** (`auth.py`):
- JWT bearer tokens via `JWTAuth`
- API key header via `APIKey`
- `AuthManager` consolidates both strategies

**Middleware** (`middleware.py`):
- `LoggingMiddleware` — structured request/response logging
- `RateLimitMiddleware` — per-IP and per-key rate limiting

**Request model example:**
```python
class AuditRecordRequest(BaseModel):
    event_type: str      # create|read|update|delete|access|authentication|authorization|system
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    encrypt: bool = False
```

---

### `crypto/` — Cryptographic Primitives

**Files:** `hash_manager.py`, `signature_manager.py`

#### `HashManager` + `MerkleTree` + `HashChain`

Supports 7 hash algorithms via `HashAlgorithm` enum:

| Algorithm | Use case |
|-----------|---------|
| `SHA256` | General-purpose hashing |
| `SHA512` | High-security hashing |
| `SHA3_256` / `SHA3_512` | Keccak-based (EVM-compatible) |
| `BLAKE2B` / `BLAKE2S` | High-speed hashing |
| `KECCAK` | Ethereum-native |

`HashResult` dataclass carries: algorithm, hash value, input size, timestamp, metadata.

**Merkle tree** (`MerkleTree`):
- Binary tree of hashes over a list of records
- `get_proof(index)` → `MerkleProof` with sibling hashes for O(log n) verification
- Recomputes root on `add_leaf()` — append-efficient

**Hash chain** (`HashChain`):
- Linked list of chained hashes: `H_n = Hash(H_{n-1} || data_n)`
- Tamper-evident: any modification breaks the chain from that point forward
- `verify_chain()` recomputes and compares all links

#### `SignatureManager` + `SignatureVerifier`

Supports `SignatureAlgorithm` enum: `ECDSA_SECP256K1`, `ECDSA_P256`, `RSA_PSS`, `ED25519`.

`DigitalSignature` dataclass: algorithm, signature bytes, public key, timestamp, metadata.

`SignatureManager`:
- `sign(data, private_key)` → `DigitalSignature`
- `verify(data, signature)` → bool
- Key generation (`generate_key_pair()`) for all algorithms

`SignatureVerifier` provides batch verification and Ethereum-compatible `recover_signer()`.

---

### `ipfs/` — Decentralized Storage

**Files:** `ipfs_client.py`, `data_manager.py`, `pinning_service.py`

#### `IPFSClient`

High-level IPFS client over [`ipfshttpclient`](https://ipfshttpclient.readthedocs.io/):

- `add_file(path)` / `add_json(data)` / `add_bytes(data)` → CID
- `get_file(cid)` / `get_json(cid)` → content
- Automatic retry with exponential backoff
- Chunked upload for large files (default 1 MB chunks)
- Health check via `is_connected()`

#### `DataManager`

Wraps `IPFSClient` with metadata tracking:
- Stores `IPFSFile` records (hash, name, size, timestamp, metadata)
- `store_audit_record(record)` → CID
- `retrieve_audit_record(cid)` → dict
- Local index of CID → metadata for fast lookups

#### `EncryptedDataManager`

Extends `DataManager` with AES-GCM envelope encryption before IPFS upload:
- Encryption key derived from agent identity (or provided externally)
- Decryption requires matching key — unauthorized nodes get ciphertext

#### `PinningService`

Manages pin lifecycle across multiple IPFS pinning services (Pinata, Infura, local node):
- `pin(cid)` / `unpin(cid)` / `list_pins()`
- Replication factor tracking (min 2 nodes by default)
- Periodic re-pin check via background task

---

### `web3_integration/` — EVM Blockchain

**Files:** `web3_client.py`, `contract_manager.py`, `network_config.py`

#### `Web3Client`

Multi-RPC endpoint client with automatic failover:

```python
client = Web3Client(
    network="ethereum",      # or chain ID, or NetworkConfig
    private_key="0x...",
    max_retries=3,
    retry_delay=1.0,
)
```

Features:
- **RPC failover**: cycles through endpoints on failure
- **Connection pooling**: persistent sessions via `aiohttp`
- **PoA middleware**: `geth_poa_middleware` for private/consortium chains
- `send_transaction(tx)` / `call_contract(address, abi, method, *args)`
- `wait_for_receipt(tx_hash, timeout=120)`
- `BlockInfo` and `TransactionInfo` dataclasses for structured results

#### `NetworkConfig` + `network_config.py`

Pre-configured networks: Ethereum mainnet/testnet, Polygon, BSC, local Hardhat/Ganache.

```python
network = get_network_by_name("polygon")   # or get_network_by_chain_id(137)
```

Each `NetworkConfig` carries: chain ID, RPC URLs (list for failover), explorer URL, native currency, block time estimate.

#### `ContractManager`

Deploys and interacts with Solidity contracts:

```python
cm = ContractManager(web3_client)
interface = await cm.deploy_contract("AuditTrail", abi, bytecode, constructor_args)
result = await cm.call_function(interface, "recordEvent", event_hash, timestamp)
```

`ContractInterface` dataclass: name, address, ABI, bytecode, deployed_at, deployer, network, verified flag.

---

## Audit Trail Design

The full audit trail pipeline:

```
Agent action
    │
    ▼
AuditRecordRequest (event_type, user_id, action, resource, details)
    │
    ├─► HashManager.sha256(record) ──► HashChain.append()
    │
    ├─► SignatureManager.sign(record, agent_key) ──► DigitalSignature
    │
    ├─► IPFSClient.add_json(signed_record) ──► CID
    │
    └─► ContractManager.call("recordAudit", cid, hash, signature) ──► tx_hash
```

Every record is:
1. **Hashed** into the running chain (tamper-evident)
2. **Signed** by the agent's key (non-repudiable)
3. **Stored on IPFS** (content-addressed, decentralized)
4. **Anchored on-chain** (immutable timestamp + CID)

---

## Cognitive Blackboard Integration

The blockchain module is **not yet wired** to the Cognitive Blackboard. When connected, a `BlockchainBlackboardAdapter` would:

| Direction | Topic / Event |
|-----------|--------------|
| **Consumes** | `safety.violation`, `goal_update`, `agent_directive`, `negotiation.outcome` |
| **Produces** | `audit.record.cid`, `audit.chain.root` |
| **Emits** | `audit.anchored` (on successful chain write) |
| **Listens** | `*.committed` (any committed Blackboard write above threshold) |

This would give every cross-module interaction a cryptographic audit trail — useful for formal reproducibility, AGSSL verification, and multi-agent accountability.

See [Issue #96](https://github.com/web3guru888/asi-build/issues) for the implementation plan.

---

## Dependencies

```
web3>=6.0.0
eth-account>=0.9.0
ipfshttpclient>=0.8.0
aiohttp>=3.8.0
fastapi>=0.100.0
python-jose[cryptography]   # JWT
pydantic>=2.0.0
```

---

## Related Wiki Pages

- [Cognitive Blackboard](Cognitive-Blackboard) — event bus + thread-safe entry store
- [Blackboard Integration Status](Blackboard-Integration-Status) — which modules are wired
- [Safety Module](Safety-Module) — formal verification + AGSSL
- [AGI Reproducibility](AGI-Reproducibility) — experiment tracking + certified proofs
- [Rings Network](Rings-Network) — DID-authenticated P2P transport
