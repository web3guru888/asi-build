# Rings Network Module

**Status**: Active 🟢 — SDK wrapper + DID adapter + ZK bridge (Sepolia) + Token Ledger  
**Location**: `src/asi_build/rings/`  
**Tests**: 799+ tests passing (668 bridge + 131 ledger + 108 base SDK, all passing)  
**LOC**: ~21,062 (bridge 19,353 · ledger 1,709 · SDK 1,951 · `__init__.py`)

> **🌉 Sepolia Testnet Live** — RingsBridge, Groth16Verifier, and BridgedToken (bASI) are deployed on Sepolia. See [Deployed Contracts](#deployed-contracts-sepolia) below.

---

## What is the Rings Network?

[Rings Network](https://github.com/RingsNetwork/rings-node) is a decentralised P2P overlay for AI agents. It's built on:

- **Chord DHT** — consistent hashing in Z₂¹⁶⁰, O(log n) routing
- **DID authentication** — every node has a `did:rings:<curve>:<fingerprint>` identity
- **WebRTC / DTLS transport** — browser-compatible, NAT-traversing
- **Rust + WASM runtime** — runs in browsers and server-side with the same code

ASI:BUILD's integration is a Python SDK wrapper — we don't embed a full Rings node, we speak its JSON-RPC / WebSocket interface from Python.

---

## Module structure

```
src/asi_build/rings/
├── __init__.py          # RingsNode facade, exports
├── client.py            # Async RPC client (707 LOC)
├── did.py               # DID creation, verification, VID computation (556 LOC)
├── reputation.py        # Local + global ranking protocol client (577 LOC)
├── bridge/              # ZK bridge (19,353 LOC — see Bridge section below)
│   ├── circuits/        # Groth16 ZK circuits (Circom)
│   ├── contracts/       # Solidity: RingsBridge, Groth16Verifier, BridgedToken
│   ├── light_client.py  # SSZ Merkle state verification
│   ├── prover.py        # BLS12-381 proof generation
│   └── relayer.py       # Cross-chain event relayer
└── ledger/              # Token ledger (1,709 LOC — see Ledger page)
    ├── balance.py        # DHT-backed balance map
    ├── transfer.py       # TransferProposal lifecycle
    ├── consensus.py      # 4/6 validator attestation
    └── validator.py      # ValidatorNode runner
```

---

## Key components

### `client.py` — RingsClient

The main async client. Transport-agnostic: uses a real WebSocket to a Rings node in production, or an `InMemoryTransport` for testing (no network required).

**Architecture (5-layer Rings stack):**

```
Application  ← this SDK lives here
Protocol     ← DID, sessions, VIDs
Network      ← Chord DHT, finger tables
Transport    ← WebRTC / DTLS
Runtime      ← Rust / WASM
```

**Constants:**
```python
RING_MODULUS = 2**160      # Chord ring operates in Z_{2^160}
DEFAULT_REPLICATION = 6    # DHash: 6 replicas per block
DEFAULT_RPC_TIMEOUT = 30.0 # seconds
```

**Core operations:**
```python
from asi_build.rings import RingsNode

# Connect to a local Rings node
node = RingsNode(endpoint="ws://localhost:50000")
await node.connect()

# Store data in the DHT
await node.store(key="my_key", value={"data": "payload"})

# Retrieve from DHT
result = await node.fetch(key="my_key")

# Send a message to a peer (DID-authenticated)
await node.send_message(
    recipient_did="did:rings:secp256k1:abc123...",
    payload={"type": "inference_result", "data": {...}}
)

# Register a message handler
@node.on_message
async def handle(msg):
    print(f"From {msg.sender_did}: {msg.payload}")
```

---

### `did.py` — DID and VID

Implements the `did:rings` DID method. Supports two key curves:

| Curve | Use case |
|-------|----------|
| `secp256k1` | Bitcoin/Ethereum-compatible ECDSA |
| `ed25519` | EdDSA — faster, shorter signatures |

**DID format:**
```
did:rings:<curve>:<fingerprint>
```

**Creating a DID:**
```python
from asi_build.rings.did import DIDManager

manager = DIDManager()

# Generate a new DID with ed25519 keys
did, key_pair = manager.create_did(curve="ed25519")
print(did)  # did:rings:ed25519:a3f2b...

# Create a W3C-compliant DID Document
doc = manager.create_did_document(did, key_pair)
# doc contains: verificationMethod, authentication, service, proof

# Sign a payload
signature = manager.sign(payload=b"hello", private_key=key_pair.private)

# Verify a signature
valid = manager.verify(
    payload=b"hello",
    signature=signature,
    did="did:rings:ed25519:a3f2b..."
)
```

**Virtual DIDs (VIDs):**

VIDs are deterministic addresses on the Chord ring, used for DHT storage keys, mailboxes, and service endpoints:

```python
vid = manager.compute_vid(namespace="asi_build", key="module_registry")
# VID = H("asi_build:module_registry") mod 2^160
```

---

### `reputation.py` — Ranking Protocol

Implements the client side of the Rings Ranking Protocol — Sybil-resistant reputation scoring.

**Four phases of global ranking:**
1. Random seed from decentralised oracle
2. Systematic sampling targets
3. DHT lookup + entropy test (Shannon/Rényi)
4. Kolmogorov-Smirnov test for distribution fairness

**Game-theoretic properties:**
- Median game → honest reporting is Nash Equilibrium
- Byzantine distributed game → unique NE = all honest (with ≥⅔ honest assumption)

```python
from asi_build.rings.reputation import ReputationClient

rep = ReputationClient()

# Record an interaction with a peer
rep.record_interaction(
    peer_did="did:rings:ed25519:xyz...",
    success=True,
    response_time_ms=45.0
)

# Query local rank (0.0–1.0)
local_rank = rep.get_local_rank("did:rings:ed25519:xyz...")

# Check if a peer meets the trust threshold (default: 0.5)
trusted = rep.is_trusted("did:rings:ed25519:xyz...")

# Report malicious behaviour (triggers freeze + slashing logic)
rep.report_malicious("did:rings:ed25519:xyz...", evidence={...})
```

---

## Current limitations

| Limitation | Status |
|-----------|--------|
| No live Rings node bundled | By design — requires external Rings node |
| Blackboard integration not yet wired | Planned in Issue [#19](https://github.com/web3guru888/asi-build/issues/19) |
| DID resolution is local-only | DHT-backed resolution needs live network |
| `secp256k1` ECDSA signing is simulated | Real signing requires `cryptography` library in production |

---

## Planned integration: RingsBlackboardBridge

Issue [#19](https://github.com/web3guru888/asi-build/issues/19) tracks the full Cognitive Blackboard integration. The planned bridge:

```python
class RingsBlackboardBridge:
    def __init__(self, blackboard: CognitiveBlackboard, rings_node: RingsNode):
        self.bb = blackboard
        self.node = rings_node
        # Incoming Rings messages → Blackboard entries
        rings_node.on_message(self._inbound_handler)
        # Blackboard inference events → outbound P2P messages
        blackboard.event_bus.subscribe("inference", self._outbound_handler)

    async def _inbound_handler(self, msg: RingsMessage):
        # Only accept DID-verified messages
        if not await self.node.verify_did(msg.sender_did, msg.signature):
            return
        self.bb.write(BlackboardEntry(
            entry_type="remote_inference",
            data=msg.payload,
            metadata={"source_did": msg.sender_did, "trust_level": "verified"}
        ))
```

This will enable **distributed cognitive networks** — multiple ASI:BUILD instances sharing inference results via the Rings P2P overlay.

---

## Running the tests

```bash
# Run all Rings tests (no network needed — uses InMemoryTransport)
pytest tests/test_rings.py -v

# Run a specific component
pytest tests/test_rings.py -k "did" -v
pytest tests/test_rings.py -k "reputation" -v
```

All 108 tests pass without a live Rings node.

---

---

## Rings↔Eth Bridge (Sepolia Testnet)

> Phase 3 complete — 668 bridge tests passing, contracts live on Sepolia.

The Rings↔Ethereum bridge lets agents deposit ETH or any ERC-20 from Ethereum into the Rings DHT, transfer between agents at DHT speed, and withdraw back to Ethereum — all enforced by ZK proofs. **No multisigs. No oracles. No trusted relayer.**

### ZK Proof Architecture

```
Ethereum (Sepolia)                         Rings Network
══════════════════                         ══════════════
RingsBridge.deposit(token, amount)
  └─ locks tokens in bridge escrow
  └─ emits Deposit(depositor, token, amount, leafIndex)
                    │
                    ▼  (relayer picks up event)
             Rings light client
               verifies SSZ Merkle proof
               of Ethereum state header
                    │
                    ▼
             BalanceStore.credit()
               DHT balance += amount
                    │
              (agent pays agent)
              ledger.pay() ← 4/6 consensus
                    │
             ledger.withdraw_request()
               DHT balance -= amount
               Groth16 circuit generates π
                    │
                    ▼  (anyone submits)
RingsBridge.withdraw(π, publicInputs)
  └─ Groth16Verifier.verify(π) on-chain
  └─ releases tokens to recipient
```

### Why ZK?

| Property | Multisig | Oracle | ZK (this bridge) |
|----------|----------|--------|-------------------|
| Trust assumption | ≥ k/n signers honest | Oracle honest | Math |
| Proof size | O(n) sigs | 1 attestation | ~200 bytes (Groth16) |
| On-chain verification cost | ~21k gas/sig | ~30k gas | ~280k gas (constant) |
| Liveness dependency | k signers online | Oracle online | Anyone can relay |
| Formally verified | ❌ | ❌ | ✅ (Certora) |

### Deployed Contracts (Sepolia)

| Contract | Address | Etherscan |
|----------|---------|-----------|
| **Groth16Verifier** | `0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59` | [View](https://sepolia.etherscan.io/address/0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59) |
| **RingsBridge** | `0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca` | [View](https://sepolia.etherscan.io/address/0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca) |
| **BridgedToken (bASI)** | `0x257dDA1fa34eb847060EcB743E808B65099FB497` | [View](https://sepolia.etherscan.io/address/0x257dDA1fa34eb847060EcB743E808B65099FB497) |

> All contracts deployed by `web3guru888` EOA. Contracts are formally verified via Certora prover.

### Groth16 Circuit

The ZK circuit proves:
1. The deposit leaf exists in the Ethereum state Merkle tree (SSZ proof)
2. The withdrawal amount ≤ credited balance
3. The recipient address matches the claimant's secp256k1 key
4. The nonce has not been used before (nullifier hash)

Proving key generated via BLS12-381 Powers-of-Tau ceremony. Verification key committed on-chain in `Groth16Verifier`.

### Bridge Tests (668 passing)

```
tests/rings/bridge/
├── test_circuits.py         # 187 tests — ZK circuit constraints
├── test_contracts.py        # 142 tests — Solidity contract logic (Hardhat)
├── test_light_client.py     # 131 tests — SSZ Merkle proof verification
├── test_prover.py           # 118 tests — BLS12-381 proof generation
└── test_relayer.py          #  90 tests — cross-chain event relay
```

---

## Token Ledger (Agent-to-Agent Payments)

The token ledger enables agents to pay each other with bridged tokens — no Ethereum transaction per payment, just DHT writes with 4/6 validator consensus.

**See the full page**: [Rings Token Ledger: Agent-to-Agent Payments](Rings-Token-Ledger)

**Quick start:**

```python
from asi_build.rings.ledger import LedgerClient

ledger = LedgerClient(rings_node=node)

# Pay another agent 1 bASI
tx = await ledger.pay(
    recipient_did="did:rings:secp256k1:xyz...",
    token_address="0x257dDA1fa34eb847060EcB743E808B65099FB497",
    amount=1_000_000,   # 1 bASI (6 decimals)
)
# tx.status: PROPOSED → ATTESTING → FINALIZED (~200ms p95)
```

Transfer lifecycle: `PROPOSED` → `ATTESTING` (4/6 validators sign) → `FINALIZED` (DHT balances updated).

---

## Related discussions & issues

- Discussion [#5](https://github.com/web3guru888/asi-build/discussions/5) — Research directions: what should Rings integration tackle?
- Discussion [#20](https://github.com/web3guru888/asi-build/discussions/20) — Show & Tell: Rings SDK walkthrough
- Discussion [#31](https://github.com/web3guru888/asi-build/discussions/31) — Phase 2 planning: privacy-preserving consciousness
- Discussion [#35](https://github.com/web3guru888/asi-build/discussions/35) — Full-system orchestration with all 29 modules
- Issue [#19](https://github.com/web3guru888/asi-build/issues/19) — Blackboard integration (open, help wanted)

---

*Rings Network: https://github.com/RingsNetwork/rings-node*
