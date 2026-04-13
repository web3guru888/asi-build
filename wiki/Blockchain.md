# Blockchain Module

> **Module path**: `src/asi_build/blockchain/`  
> **Size**: 15 files · 5,963 LOC  
> **Status**: ✅ Functional — Web3 integration, IPFS storage, cryptographic audit trail, REST API all operational  
> **Purpose**: Tamper-proof audit trail for AGI decisions + decentralized data persistence via IPFS + smart contract governance

The `blockchain` module provides ASI:BUILD's integrity layer: a cryptographically verifiable record of every significant AGI action, decision, and state transition. When the safety module approves a plan, when the knowledge graph writes a new fact, when two agents reach a GOAL_AGREEMENT — those events can be recorded to an immutable blockchain ledger and stored to IPFS.

The module was originally designed as a "Kenny AGI Blockchain Audit Trail" — a system to make AI decision-making auditable and accountable.

---

## Architecture

```
blockchain/
├── api/
│   ├── auth.py          # JWT/API-key auth + RBAC (5 roles: admin, auditor, verifier, read_only, system)
│   ├── middleware.py     # Rate limiting, request validation, logging middleware
│   └── rest_api.py       # FastAPI REST endpoints for audit trail queries
├── contracts/
│   └── contracts/        # Solidity smart contract ABI definitions
├── crypto/
│   ├── hash_manager.py   # Merkle trees, hash chains, SHA256/SHA3/BLAKE2/Keccak
│   └── signature_manager.py  # ECDSA signing, Ed25519, batch verification
├── ipfs/
│   ├── ipfs_client.py    # IPFS HTTP client (local node or Infura)
│   ├── data_manager.py   # AuditRecord serialization, encryption, IPFS storage
│   └── pinning_service.py  # Pinning management (Pinata, web3.storage, self-hosted)
└── web3_integration/
    ├── web3_client.py    # Web3.py wrapper (Ethereum mainnet/testnet/local)
    ├── contract_manager.py  # ContractInterface deploy/interact/verify
    └── network_config.py  # Multi-network config (Ethereum, Polygon, Arbitrum, local)
```

---

## Core Concepts

### Audit Record

The fundamental unit is an `AuditRecord` — a structured event with cryptographic proof:

```python
@dataclass
class AuditRecord:
    id: str              # UUID
    event_type: str      # "decision", "state_transition", "goal_agreement", ...
    timestamp: datetime
    user_id: str         # agent or human actor
    action: str          # what happened
    resource: str        # what was affected
    details: Dict[str, Any]   # arbitrary event data
    hash: Optional[str]  # SHA256 of record content (set on write)
    signature: Optional[str]  # ECDSA signature (set on write)
```

The hash and signature are computed by `HashManager` and `SignatureManager` at write time, creating a tamper-evident record.

### Hash Chain

Each record's hash includes the previous record's hash — forming a **hash chain** (same principle as a blockchain):

```
record[N].hash = SHA256(record[N].content + record[N-1].hash)
```

Tampering with any record invalidates all subsequent hashes, making fraud detectable without requiring the entire chain to be downloaded.

### Merkle Tree

For batch integrity checking, `HashManager` builds Merkle trees over sets of records:

```python
from asi_build.blockchain.crypto.hash_manager import HashManager

hm = HashManager()
records = [record1, record2, record3, record4]
tree = hm.build_merkle_tree([r.hash for r in records])
root = tree.root   # single hash representing all 4 records
proof = tree.get_proof(record2.hash)   # membership proof (log N hashes)
```

The Merkle root can be published to a smart contract — a cheap, permanent commitment to the full record set.

---

## Cryptography

### Hash Algorithms

`HashAlgorithm` enum supports: SHA256, SHA512, SHA3-256, SHA3-512, BLAKE2b, BLAKE2s, Keccak (Ethereum-compatible).

```python
from asi_build.blockchain.crypto.hash_manager import HashManager, HashAlgorithm

hm = HashManager()
result = hm.hash(data, algorithm=HashAlgorithm.KECCAK)
# HashResult:
#   algorithm: HashAlgorithm.KECCAK
#   hash_value: "0x..."
#   input_size: 1024  (bytes)
```

### Digital Signatures

`SignatureManager` supports ECDSA (secp256k1 — Ethereum-compatible) and Ed25519:

```python
from asi_build.blockchain.crypto.signature_manager import SignatureManager

sm = SignatureManager()
private_key, public_key = sm.generate_keypair(algorithm="ecdsa_secp256k1")
signature = sm.sign(record.hash, private_key)
valid = sm.verify(record.hash, signature, public_key)
```

**Batch verification**: `sm.batch_verify([(hash, sig, pubkey), ...])` — useful for auditing large record sets without per-record overhead.

---

## IPFS Integration

### IPFSClient

Wraps the IPFS HTTP API (compatible with local nodes, Infura, and Web3.storage):

```python
from asi_build.blockchain.ipfs.ipfs_client import IPFSClient

client = IPFSClient(api_url="http://localhost:5001")
cid = await client.add(data_bytes)         # returns IPFS CID
content = await client.cat(cid)            # retrieve by CID
await client.pin(cid)                      # pin to prevent GC
```

### DataManager

`DataManager` handles `AuditRecord` persistence with encryption:

```python
from asi_build.blockchain.ipfs.data_manager import DataManager, AuditRecord

dm = DataManager(ipfs_client, encryption_key=fernet_key)
cid = await dm.store_record(record)      # encrypt + compress + IPFS add
record = await dm.retrieve_record(cid)   # IPFS cat + decompress + decrypt
```

Encryption uses **Fernet** (symmetric) with optional RSA key wrapping for multi-party access. Compression uses gzip (typically 4–8× for JSON audit records).

### Pinning Service

`PinningService` ensures records persist even if the local IPFS node goes offline:

- **Pinata**: commercial pinning service
- **web3.storage**: Filecoin-backed free tier
- **Self-hosted**: pinning via local IPFS cluster

---

## Web3 Integration

### Web3Client

Wraps `web3.py` for Ethereum interaction:

```python
from asi_build.blockchain.web3_integration.web3_client import Web3Client

client = Web3Client(rpc_url="https://mainnet.infura.io/v3/YOUR_KEY")
block = await client.get_block("latest")
tx = await client.send_transaction(...)
receipt = await client.wait_for_receipt(tx_hash)
```

Supported networks (via `network_config.py`): Ethereum mainnet, Goerli/Sepolia testnets, Polygon, Arbitrum, local Hardhat/Anvil.

### ContractManager

`ContractManager` deploys and interacts with Solidity smart contracts:

```python
from asi_build.blockchain.web3_integration.contract_manager import ContractManager

cm = ContractManager(web3_client)
contract = await cm.deploy(
    name="AGI_AuditTrail",
    abi=audit_abi,
    bytecode=audit_bytecode,
    constructor_args=[owner_address],
)
# ContractInterface: address, ABI, deployment timestamp, verifier address

tx = await cm.call_function(contract, "recordMerkleRoot", [merkle_root, block_number])
```

### Smart Contract Role

The Solidity contract serves as a **public commitment store**: it records Merkle roots on-chain, allowing anyone to verify that a specific audit record was included in a batch at a given time. The actual record data lives in IPFS (cheaper, larger); the on-chain hash ties IPFS content to an immutable timeline.

---

## REST API

`rest_api.py` exposes audit trail queries via FastAPI:

| Endpoint | Auth | Description |
|---|---|---|
| `POST /records` | `ADMIN`, `SYSTEM` | Create audit record |
| `GET /records/{id}` | `READ_ONLY`+ | Retrieve single record |
| `GET /records?event_type=...` | `AUDITOR`+ | Query records by type/time |
| `GET /records/{id}/verify` | `VERIFIER`+ | Verify hash + signature |
| `GET /status` | public | System health |

### Authentication

`auth.py` supports two credential types:

1. **API Keys**: hashed with bcrypt, stored in key registry
2. **JWT Tokens**: RS256-signed, 24h expiry, role-embedded in claims

```python
# RBAC: role → permissions
ROLE_PERMISSIONS = {
    UserRole.ADMIN:     ALL_PERMISSIONS,
    UserRole.AUDITOR:   [READ, VERIFY, QUERY],
    UserRole.VERIFIER:  [READ, VERIFY],
    UserRole.READ_ONLY: [READ, QUERY],
    UserRole.SYSTEM:    [CREATE, READ],
}
```

---

## Integration with ASI:BUILD

### Safety Gate → Blockchain

The safety module should emit a blockchain audit record on every formal verification result:

```python
# In safety/formal_verification.py (proposed integration)
async def verify_plan(plan: Plan) -> VerificationResult:
    result = theorem_prover.verify(plan)
    
    await audit.record(AuditRecord(
        event_type="safety_verification",
        action="formal_verify",
        resource=plan.id,
        details={"result": result.verdict, "proof_steps": result.n_steps},
    ))
    return result
```

This creates an immutable log of every safety decision — critical for post-hoc accountability.

### Cognitive Blackboard → Blockchain

High-confidence Blackboard writes (e.g. goal agreements, world model updates) can be mirrored to IPFS with Merkle root commitments on-chain. This provides:
- **Auditability**: anyone can verify the AGI's world model history
- **Tamper evidence**: retroactive edits break the hash chain
- **Federation**: multiple ASI:BUILD instances can share verified world model snapshots

See [Issue #63](https://github.com/web3guru888/asi-build/issues/63): Wire agi_economics reputation system into Cognitive Blackboard — the reputation system could also log scoring events here.

### AGI Economics → Blockchain

The `agi_economics` reputation and token systems are a natural fit for on-chain settlement:
- **Reputation scores**: finalized scores published as Merkle roots
- **Token transfers**: AGIX/AGI token accounting via ERC-20 smart contracts
- **Service contracts**: `AGIServiceContract` (in `contracts/`) maps to actual Solidity contracts

---

## Open Research Questions

1. **Cost vs. auditability tradeoff**: Writing every AGI decision to Ethereum mainnet costs real gas. L2 rollups (Arbitrum, Optimism) reduce this by ~100×. What's the right publication frequency — every decision, every N decisions, or only high-stakes ones?

2. **Privacy**: IPFS content is public by default. The current AuditRecord uses Fernet encryption, but key distribution for multi-party audit access is unsolved. ZKPs (see [Homomorphic Computing](Homomorphic-Computing)) could enable selective disclosure.

3. **Governance**: Who controls the Solidity contract owner address? In a decentralized AGI network (see [Rings Network](Rings-Network)), this should be a multi-sig or DAO — but the current design uses a single deployer.

4. **Cross-chain**: The architecture supports Ethereum + Polygon + Arbitrum, but chain selection logic is manual. Should the system auto-select based on gas prices, finality requirements, and network congestion?

5. **AGI decision provenance**: As ASI:BUILD makes more autonomous decisions, how do we trace any given output back to its causal chain? Blockchain timestamping + IPFS content addressing + knowledge graph edge metadata together could form a complete provenance system — but the pieces need to be wired.

---

## Related Modules

- [Safety Module](Safety-Module) — formal verification results → audit records
- [AGI Economics](AGI-Economics) — token transfers, reputation scoring → on-chain settlement
- [Homomorphic Computing](Homomorphic-Computing) — ZKPs for selective audit disclosure
- [Rings Network](Rings-Network) — P2P DID identity + distributed ledger alternative
- [Cognitive Blackboard](Cognitive-Blackboard) — high-stakes writes → IPFS persistence

---

## Relevant Issues

- [Issue #63](https://github.com/web3guru888/asi-build/issues/63): Wire agi_economics reputation into Cognitive Blackboard (Economics + Blockchain overlap)
- [Issue #37](https://github.com/web3guru888/asi-build/issues/37): Wire EthicalVerificationEngine into Blackboard write/read pipeline (safety logging via Blockchain)
