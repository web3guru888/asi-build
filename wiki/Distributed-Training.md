# Distributed Training Module

**Path**: `src/asi_build/distributed_training/`  
**Size**: 14 files · 8,595 LOC  
**Status**: ✅ Implemented (infrastructure layer complete; Blackboard integration pending — Issue #75)

---

## Overview

The `distributed_training` module provides infrastructure for training large models across a decentralized network of up to **10,000 nodes**. It handles:

- **Federated orchestration**: round management, node selection, model distribution
- **Byzantine fault tolerance**: adversarial node detection and robust aggregation
- **Gradient compression**: bandwidth optimization via sparsification and quantization
- **AGIX token incentives**: stake-weighted compute rewards via Web3.py + Solidity
- **P2P node discovery**: Kademlia DHT + gossip protocol
- **Secure aggregation**: encrypted gradient summation (coordinator never sees raw gradients)

This module differs from `federated/` in scope: `federated/` focuses on privacy-preserving model averaging algorithms (FedAvg, FedMAML, Byzantine robustness at the ML level). `distributed_training/` is the full infrastructure layer — node registry, round lifecycle, token economics, smart contracts, and P2P transport.

---

## Architecture

```
distributed_training/
├── core/
│   ├── federated_orchestrator.py   # Main coordinator (up to 10,000 nodes)
│   ├── byzantine_tolerance.py      # Adversarial node detection + aggregation
│   ├── gradient_compression.py     # TopK sparsification, quantization, zlib/brotli/lz4
│   ├── dataset_sharding.py         # Data distribution across nodes
│   └── error_handling.py           # Failure recovery and retry logic
├── p2p/
│   └── node_discovery.py           # DHT + gossip node discovery
├── blockchain/
│   ├── agix_rewards.py             # AGIX token reward calculation (Web3.py)
│   └── checkpoint_manager.py       # On-chain model checkpoint management
├── smart_contracts/
│   └── TrainingCoordinator.sol     # Solidity coordinator contract
├── monitoring/
│   └── dashboard.py                # Live training metrics dashboard
└── privacy/
    └── secure_aggregation.py       # Secure multi-party gradient aggregation
```

---

## Core: FederatedOrchestrator

The main entry point. Manages node registry, round lifecycle, model distribution, and result collection.

### Key Data Classes

```python
@dataclass
class NodeInfo:
    node_id: str
    ip_address: str
    port: int
    capabilities: Dict[str, Any]
    compute_power: float       # Relative GPU/CPU score
    reputation_score: float    # 0.0–1.0 (updated each round)
    stake_amount: float        # AGIX tokens staked
    status: str                # active | inactive | malicious | quarantined

@dataclass
class TrainingRound:
    round_id: str
    global_model_hash: str     # SHA-256 of current global model
    participants: List[str]    # Selected node IDs for this round
    start_time: float
    deadline: float
    min_participants: int      # Default: 10
    max_participants: int      # Default: 100
    status: str                # preparing | active | aggregating | completed

@dataclass
class ModelUpdate:
    node_id: str
    round_id: str
    model_diff: bytes          # Compressed gradient delta
    data_size: int             # Number of samples processed
    compute_proof: str         # Cryptographic proof of work
    signature: str             # RSA-2048 signature
    timestamp: float
```

### Configuration

```python
orchestrator = FederatedOrchestrator({
    "max_nodes": 10000,
    "min_nodes_per_round": 10,
    "max_nodes_per_round": 100,
    "round_duration": 300,       # 5 minutes
    "heartbeat_interval": 30,    # seconds
})
```

Node selection prioritizes high-reputation, high-compute-power nodes with sufficient stake, subject to the configured `max_nodes_per_round` cap. The orchestrator uses a **ThreadPoolExecutor** (50 workers) for concurrent node communication.

---

## Byzantine Fault Tolerance

`byzantine_tolerance.py` implements detection and robust aggregation for adversarial nodes.

### Attack Taxonomy

```python
class AttackType(Enum):
    HONEST = "honest"
    RANDOM = "random"         # Inject random gradient noise
    SIGN_FLIP = "sign_flip"   # Flip gradient signs to reverse learning
    GAUSSIAN = "gaussian"     # Add Gaussian noise to gradients
    LABEL_FLIP = "label_flip" # Poison training data labels
    BACKDOOR = "backdoor"     # Insert trigger-activated backdoor
    SYBIL = "sybil"           # Multiple fake node identities
```

### Per-Node Behavioral Tracking

```python
@dataclass
class NodeBehavior:
    node_id: str
    gradient_norms: List[float]          # Historical gradient magnitudes
    submission_times: List[float]        # Timing patterns
    accuracy_contributions: List[float]  # Per-round accuracy delta
    similarity_scores: List[float]       # Cosine similarity to aggregate
    reputation_score: float              # 0.0–1.0
    trust_score: float                   # 0.0–1.0 (decays on anomaly)
    detected_attacks: List[AttackType]   # Attack history
    last_evaluation: float
```

### Detection Methods

1. **Z-score on gradient norms**: nodes with norms > 3σ above historical baseline are flagged
2. **DBSCAN clustering**: identifies groups of colluding nodes submitting similar malicious gradients
3. **Trust score decay**: each anomaly reduces trust; nodes below threshold are quarantined
4. **Timing analysis**: suspiciously fast submissions (before honest nodes can compute) are flagged

### Aggregation Result

```python
@dataclass
class AggregationResult:
    aggregated_gradients: Dict[str, torch.Tensor]
    honest_participants: List[str]
    suspected_byzantine: List[str]
    confidence_score: float          # 0.0–1.0
    aggregation_method: str          # "trimmed_mean" | "krum" | "median"
    detection_stats: Dict[str, Any]  # Per-node suspicion scores
```

---

## Gradient Compression

Bandwidth is often the bottleneck in large-scale decentralized training. `gradient_compression.py` implements multiple strategies under a `GradientCompressor` abstract base class.

### TopK Sparsification

Transmit only the top-K% of gradient components by magnitude, with error feedback to prevent drift:

```python
class TopKSparsification(GradientCompressor):
    def __init__(self, k_ratio: float = 0.1, error_feedback: bool = True):
        self.k_ratio = k_ratio          # Transmit top 10% by default
        self.error_feedback = error_feedback
        self.error_memory: Dict[str, torch.Tensor] = {}

    async def compress(self, gradients: Dict[str, torch.Tensor]) -> Tuple[bytes, Dict]:
        # 1. Add accumulated error (error feedback)
        # 2. Select top-K indices by magnitude
        # 3. Store residual in error_memory for next round
        # 4. Serialize as sparse matrix (scipy.sparse.csr_matrix)
        # 5. Compress with zlib/brotli/lz4
```

### Compression Statistics

```python
@dataclass
class CompressionStats:
    original_size: int
    compressed_size: int
    compression_ratio: float    # original / compressed
    compression_time: float     # seconds
    decompression_time: float
    algorithm: str              # "topk" | "random" | "quantized" | "brotli"
```

Additional compressors: Random sparsification, FP32→INT8 quantization, and lossless byte compression.

---

## AGIX Token Incentives

`blockchain/agix_rewards.py` integrates with Web3.py to calculate SingularityNET AGIX token rewards for compute contributions.

### Contribution Tracking

```python
@dataclass
class ComputeContribution:
    node_id: str
    round_id: str
    data_processed: int      # Training samples processed
    compute_time: float      # Wall-clock seconds
    gpu_hours: float         # Billed GPU-hours
    model_accuracy: float    # This node's contribution to round accuracy delta
    bandwidth_used: int      # Bytes transmitted (compressed gradient)
    timestamp: float
```

### Reward Calculation

```python
@dataclass
class RewardCalculation:
    node_id: str
    base_reward: Decimal              # base_reward_per_sample × data_processed
    quality_bonus: Decimal            # accuracy above threshold × quality_multiplier
    consistency_bonus: Decimal        # multi-round reliability × consistency_multiplier
    early_submission_bonus: Decimal   # submitted before deadline × 1.2
    total_reward: Decimal
    agix_amount: Decimal              # Converted at current AGIX/USD rate
```

The reward formula is deterministic. The Solidity `TrainingCoordinator.sol` smart contract mirrors the same logic — nodes can verify their reward independently before accepting a round.

---

## P2P Node Discovery

`p2p/node_discovery.py` implements a **Kademlia-style DHT** for peer lookup plus a **gossip overlay** for low-latency announcements.

```python
@dataclass
class PeerInfo:
    peer_id: str           # Kademlia node ID (SHA-256 of public key)
    ip_address: str
    port: int
    public_key: str        # Ed25519 public key (base64)
    capabilities: Dict     # {"gpu": True, "tpu": False, "ram_gb": 64, ...}
    last_seen: float
    reputation: float      # 0.0–1.0, propagated via gossip
    is_bootstrap: bool
    network_id: str        # Prevents cross-network contamination
```

Bootstrap nodes seed the initial DHT ring. New nodes announce themselves, collect peer lists, and gradually populate their routing table. Uses `aiodns` for async DNS resolution and `aiohttp` for HTTP transport.

---

## Secure Aggregation

`privacy/secure_aggregation.py` ensures the orchestrator never sees raw gradient values — only their encrypted sum. This uses **secret sharing** (each node's gradient is split into N shares, sent to N other nodes before aggregation) so that no single coordinator has access to individual gradients.

This pairs with Byzantine detection in a non-trivial way: detection must operate on statistical metadata (gradient norms, timing, similarity scores) derived from public proofs, not raw gradient values. Privacy and security are complementary here — the detection statistics are computed before encryption, not from the encrypted aggregate.

---

## On-Chain Checkpoint Management

`blockchain/checkpoint_manager.py` publishes model checkpoint hashes to the blockchain:

- Each completed training round writes `(round_id, model_hash, accuracy, participant_list)` on-chain
- Provides tamper-evident audit trail of model evolution
- Any node can verify that the current global model descends from a valid checkpoint sequence
- Integrates with `blockchain/` module's IPFS persistence for actual model storage

---

## Cognitive Blackboard Integration (Planned)

> **Issue #75** — Waiting for contributors

A `DistributedTrainingAdapter` would publish round state to the Blackboard:

```python
# On round start:
blackboard.write("distributed_training", "training.state", {
    "status": "active",
    "round_id": ...,
    "participants": [...],
    "deadline": ...
})

# On round complete:
blackboard.write("distributed_training", f"round.{round_id}.result", {
    "honest_participants": [...],
    "suspected_byzantine": [...],
    "confidence_score": 0.97,
    "aggregation_method": "trimmed_mean"
})
```

Downstream modules could subscribe:
- **bio_inspired**: switch to consolidation mode during high-loss rounds
- **consciousness**: update meta-cognitive state based on learning progress  
- **safety**: audit high-stakes model updates via blockchain ledger
- **agi_economics**: adjust node reputation scores from Byzantine detection

---

## Rings Network Synergy (Future)

The P2P transport currently uses raw aiohttp. The Rings Network SDK could replace it, providing:

- **DID-authenticated node identities** — each training node gets a DID, no more IP-based identification
- **Reputation inheritance** — Rings reputation protocol could seed initial trust scores
- **Encrypted channels** — Rings provides E2E encryption out of the box, potentially simplifying `secure_aggregation.py`

---

## Open Questions

1. **What model does this train?** With 29 specialized modules, is there a meta-learning layer training the module router/weighting function? Or do individual modules self-train independently?

2. **Shard reassignment**: What happens when a node drops mid-round? Does the round absorb the loss, or is there a reassignment protocol?

3. **AGIX economics at scale**: Is token-incentivized compute viable for an open-source AGI framework? What prevents a race to the bottom on model quality?

4. **Cross-silo vs. cross-device**: The module seems designed for cross-silo (organization-level nodes). How would it need to change for cross-device (millions of edge devices)?

---

## See Also

- [`federated/`](Federated-Learning) — Privacy-preserving model averaging algorithms
- [`blockchain/`](Blockchain) — IPFS persistence and audit ledger
- [`agi_economics/`](AGI-Economics) — Reputation scoring and token incentives
- [Issue #75](https://github.com/web3guru888/asi-build/issues/75) — Blackboard adapter
- [Discussion #74](https://github.com/web3guru888/asi-build/discussions/74) — Deep-dive Show & Tell
