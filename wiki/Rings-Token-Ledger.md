# Rings Token Ledger: Agent-to-Agent Payments

**Status**: ✅ Shipped — 1,709 LOC · 131 tests passing  
**Location**: `src/asi_build/rings/ledger/`  
**Introduced**: Phase 3 bridge milestone (2026-04-12)  
**Depends on**: [Rings↔Ethereum Bridge](Rings-Network#ringseth-bridge-sepolia-testnet), [BridgedToken bASI](Rings-Network#deployed-contracts-sepolia)

---

## Overview

The **Rings Token Ledger** is a DHT-backed payment layer that enables ASI:BUILD agents to pay each other using bridged ERC-20 tokens (USDC, ETH, bASI, or any token bridged via the [RingsBridge contract](Rings-Network#deployed-contracts-sepolia)).

No Ethereum transaction is needed for agent-to-agent transfers — balances live in the Rings DHT, moves are attested by a 4-of-6 validator quorum, and settlement to Ethereum happens only when an agent calls `withdraw()`.

```
Agent A ──pay(amount, recipient_did)──► Ledger
                                          │
                          ┌───────────────▼──────────────────┐
                          │   TransferProposal (PROPOSED)     │
                          └───────────────┬──────────────────┘
                                          │ 4/6 validators attest
                          ┌───────────────▼──────────────────┐
                          │   Transfer (ATTESTING → FINALIZED)│
                          └───────────────┬──────────────────┘
                                          │ balances updated in DHT
                                         Agent B can spend or withdraw
```

---

## Architecture

```
src/asi_build/rings/ledger/
├── __init__.py          # LedgerClient facade, exports
├── balance.py           # BalanceStore — DHT-backed balance map
├── transfer.py          # TransferProposal, TransferStatus lifecycle
├── consensus.py         # ValidatorSet — 4/6 attestation protocol
├── validator.py         # ValidatorNode — local validator runner
└── types.py             # Dataclasses: AgentBalance, Transfer, Attestation
```

---

## Transfer Lifecycle

Every agent-to-agent payment passes through three states:

### 1. `PROPOSED`

`LedgerClient.pay()` creates a `TransferProposal` and stores it in the DHT under a deterministic key:

```
ledger/transfers/{transfer_id}
```

The proposal includes:
- `sender_did` — payer's Rings DID
- `recipient_did` — payee's Rings DID
- `token_address` — ERC-20 contract address (on Ethereum / Sepolia)
- `amount` — uint256 in token's smallest unit (wei for ETH, μUSDC for USDC)
- `nonce` — sender's monotonically-increasing counter (prevents replay)
- `signature` — ECDSA signature of proposal hash, signed by sender's secp256k1 key

### 2. `ATTESTING`

The `ValidatorSet` monitors new proposals via DHT subscription. Each of the 6 validators independently:

1. Verifies the sender's DID signature
2. Checks sender's DHT balance ≥ `amount`
3. Verifies `nonce` is strictly greater than the last accepted nonce for this sender
4. Signs an `Attestation` and writes it back to the DHT

Once **4 of 6** attestations are collected, the proposal advances to `FINALIZED`.

```python
# Attestation threshold
VALIDATOR_THRESHOLD = 4
VALIDATOR_COUNT     = 6
```

### 3. `FINALIZED`

The `BalanceStore` atomically:
- Debits `sender_did` balance by `amount`
- Credits `recipient_did` balance by `amount`
- Writes the final `Transfer` record to the DHT with all 6 attestation signatures

Finalized transfers are **immutable** — they cannot be reversed. The quorum signatures serve as a cryptographic proof of the transfer for future withdrawal from Ethereum.

---

## Balance Store

Balances are stored in the Rings DHT under per-agent, per-token keys:

```
ledger/balances/{agent_did}/{token_address}
```

`BalanceStore` wraps `RingsClient.store()` / `RingsClient.fetch()` with:
- **Optimistic locking** — a version counter on each balance record; concurrent writes fail-fast and retry
- **Replication** — `DEFAULT_REPLICATION = 6` DHT replicas per balance entry
- **Read-your-writes** — `fetch()` always contacts the same primary replica first

```python
from asi_build.rings.ledger import LedgerClient

ledger = LedgerClient(rings_node=node)

# Check balance
balance = await ledger.get_balance(
    agent_did="did:rings:secp256k1:abc...",
    token_address="0x257dDA1fa34eb847060EcB743E808B65099FB497",  # bASI
)
print(f"Balance: {balance.amount} bASI")

# Transfer
tx = await ledger.pay(
    recipient_did="did:rings:secp256k1:xyz...",
    token_address="0x257dDA1fa34eb847060EcB743E808B65099FB497",
    amount=1_000_000,   # 1 bASI (6 decimals)
)
print(f"Transfer {tx.transfer_id}: {tx.status}")  # PROPOSED → FINALIZED
```

---

## Validator Consensus

The 6 validators form a **ValidatorSet** — a fixed quorum of well-known Rings nodes that watch the ledger namespace and attest transfers.

### Validator Selection

Validators are identified by their Rings DIDs, published in the DHT under:

```
ledger/validators
```

The ValidatorSet is currently **static** (fixed 6 nodes, configured at deploy time). Rotating validators is a Phase 4 objective — tracked in the roadmap under "Ledger Governance".

### Byzantine Fault Tolerance

| Scenario | Outcome |
|----------|---------|
| 0–2 validators offline / malicious | Transfer finalizes normally (4/4 or 5/4 honest) |
| 3 validators offline | Transfer stalls at ATTESTING until a validator comes back |
| 3 validators collude | Cannot finalize (need 4 of 6; 3 < threshold) |
| All 6 validators honest | Transfer finalizes in one DHT gossip round (~200ms p95) |

The 4/6 threshold follows the **BFT assumption**: tolerate up to `f = floor((n−1)/3) = 1` Byzantine fault under honest-majority assumption, or up to `n − threshold = 2` offline/faulty validators.

### Attestation Protocol

```
Validator:
  1. watch DHT for ledger/transfers/{id} (status == PROPOSED)
  2. verify sender_did signature over proposal hash
  3. verify sender balance >= amount (read from DHT)
  4. verify nonce is fresh (monotonic, not replayed)
  5. sign Attestation = Sign(validator_private_key, proposal_hash)
  6. store Attestation at ledger/attestations/{id}/{validator_did}
  7. (any validator, once count >= 4): finalize transfer, update balances
```

---

## Bridge Integration

The ledger is the **on-Rings side** of the full Rings↔Ethereum bridge:

```
Ethereum (Sepolia)                     Rings Network
══════════════════                     ═════════════
RingsBridge.deposit()      ───────►    BalanceStore.credit()
  (lock ETH/ERC-20)                    (mint DHT balance)
                                              │
                                       ledger.pay()   ← agent pays agent
                                              │
BalanceStore.debit()       ◄───────    ledger.withdraw_request()
RingsBridge.withdraw()                 (burn DHT balance + generate ZK proof)
  (release ETH/ERC-20)
```

**Deposit flow:**
1. User calls `RingsBridge.deposit(token, amount)` on Sepolia — tokens are locked in the bridge contract
2. The bridge emits a `Deposit` event, picked up by the Rings light client
3. `BalanceStore.credit(agent_did, token_address, amount)` mints the equivalent DHT balance

**Withdrawal flow:**
1. Agent calls `ledger.withdraw_request(amount, eth_recipient)` on Rings
2. Validators attest the debit (same 4/6 consensus)
3. A ZK proof is generated via the Groth16 circuit (see [ZK Bridge Architecture](Rings-Network#zk-proof-architecture))
4. Anyone submits the proof to `RingsBridge.withdraw(proof, publicInputs)` on Sepolia — tokens are released

---

## Supported Tokens

Any ERC-20 token can be bridged and used in the ledger. Tokens deployed on Sepolia testnet:

| Token | Sepolia Address | Decimals |
|-------|----------------|----------|
| **bASI** (Bridged ASI) | [`0x257dDA1fa34eb847060EcB743E808B65099FB497`](https://sepolia.etherscan.io/address/0x257dDA1fa34eb847060EcB743E808B65099FB497) | 6 |
| ETH (wrapped) | Native deposit via `RingsBridge` | 18 |
| USDC | Bridge any Sepolia USDC | 6 |

---

## Test Coverage

```
tests/rings/test_ledger.py      131 tests — all passing
```

| Test group | Count | Notes |
|-----------|-------|-------|
| `BalanceStore` unit | 28 | Optimistic lock, replication, DHT serialization |
| `TransferProposal` lifecycle | 31 | PROPOSED→ATTESTING→FINALIZED happy path + failures |
| `ValidatorSet` consensus | 42 | 4/6 threshold, Byzantine scenarios, timeout/retry |
| `LedgerClient` integration | 30 | Full pay() + withdraw_request() flows with mock DHT |

All tests use the `InMemoryTransport` — no live Rings node or Sepolia connection required.

---

## Running the Tests

```bash
# All ledger tests
pytest tests/rings/test_ledger.py -v

# Consensus scenarios only
pytest tests/rings/test_ledger.py -k "validator" -v

# Full bridge + ledger integration
pytest tests/rings/ -v
```

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Pay() end-to-end latency | ~200ms p95 (1 DHT gossip round) |
| Validator attestation latency | ~50ms p95 per validator |
| DHT balance reads | ~20ms p95 |
| Max concurrent transfers | Bounded by DHT write throughput (~500/s) |
| Nonce replay window | 0 (strict monotonic per sender) |

---

## Phase 4 Roadmap

| Item | Status |
|------|--------|
| Dynamic validator rotation | Planned — validators join/leave via governance |
| Token whitelisting governance | Planned — DAO vote to add new bridgeable tokens |
| Ledger state snapshots | Planned — periodic Merkle root commitment to Ethereum |
| Mainnet deployment | After Phase 4 production hardening |

---

## Related Pages

- [Rings Network](Rings-Network) — P2P layer, DID auth, reputation
- [Rings↔Ethereum Bridge](Rings-Network#ringseth-bridge-sepolia-testnet) — ZK bridge architecture, contract addresses
- [AGI Economics](AGI-Economics) — Token economics and AGIX incentives
- [Blockchain Module](Blockchain-Module) — Ethereum audit trail and Web3 integration

---

## Related Issues & Discussions

- Issue [#19](https://github.com/web3guru888/asi-build/issues/19) — Blackboard integration for Rings (open)
- Discussion [#20](https://github.com/web3guru888/asi-build/discussions/20) — Rings SDK walkthrough
