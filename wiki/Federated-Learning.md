# Federated Learning Module

The `federated` module brings privacy-preserving distributed machine learning to ASI:BUILD — enabling model training across multiple agents, organizations, or edge nodes without centralizing raw data.

**Location**: `src/asi_build/federated/`  
**LOC**: ~6,811 across 16 Python files  
**Status**: Implemented, not yet wired to Cognitive Blackboard  

---

## Architecture

```
federated/
├── core/
│   ├── base.py          # FederatedClient, FederatedServer, FederatedModel ABCs
│   ├── config.py        # FederatedConfig dataclass
│   ├── manager.py       # FederatedManager (central coordinator)
│   └── exceptions.py    # FL-specific error types
├── aggregation/
│   ├── base_aggregator.py
│   ├── fedavg.py        # Weighted FedAvg baseline
│   ├── byzantine_robust.py  # Krum, multi-Krum, trimmed mean, median
│   └── secure_aggregation.py  # Secret-sharing-based secure aggregation
├── algorithms/
│   ├── async_fl.py      # Asynchronous FL with staleness discounting
│   ├── cross_silo.py    # Cross-organization FL with trust negotiation
│   ├── personalized_fl.py  # Per-client personalization layer
│   ├── federated_transfer.py  # Transfer learning across silos
│   └── meta_learning.py  # FedMAML, FedReptile
├── privacy/
│   └── differential_privacy.py  # Laplace + Gaussian mechanisms, privacy accountant
└── utils/
    ├── metrics.py       # FederatedMetrics tracker
    └── model_compression.py  # Quantization, pruning, sparse updates
```

---

## Core Abstractions

### `FederatedClient`

Abstract base class for participating nodes:
```python
class FederatedClient(ABC):
    client_id: str
    local_data: Optional[tf.data.Dataset]
    
    @abstractmethod
    def train_local(self, global_weights, config) -> Dict[str, Any]:
        """Train on local data, return update dict."""
    
    @abstractmethod
    def evaluate_local(self, weights) -> Dict[str, float]:
        """Evaluate model on local data."""
```

### `FederatedServer`

Coordinates rounds, manages registered clients, applies aggregation:
```python
server = FederatedServer("server-0", aggregator=ByzantineRobustAggregator())
server.register_client(client)
results = server.run_round(client_ids=selected_clients)
```

### `FederatedManager`

Top-level coordinator — wraps server+clients, drives training loop, tracks convergence:
```python
manager = FederatedManager(config)
manager.set_server(server)
manager.register_client(client1)
manager.register_client(client2)
history = manager.train(num_rounds=50, target_accuracy=0.95)
```

---

## Aggregation Methods

### FedAvg (Baseline)

Weighted average by local dataset size — the McMahan et al. (2017) baseline:

```
W_global = Σᵢ (nᵢ / N) * W_i
```

Where `nᵢ` is client `i`'s local data size and `N = Σ nᵢ`.

### Byzantine-Robust Aggregation

Defends against malicious clients that send arbitrary gradient updates.

**Krum**: Selects the update that minimizes distance to its nearest `n - f - 2` neighbors, where `f` is the expected Byzantine count:
```python
aggregator = ByzantineRobustAggregator(config={"defense_method": "krum", "num_byzantine": 1})
```

| Method | Robustness Guarantee | Cost |
|--------|---------------------|------|
| `krum` | Selects a single honest update | O(n²) distance computation |
| `multi_krum` | Selects `m` updates, then averages | O(n²) |
| `trimmed_mean` | Removes top/bottom α fraction per coordinate | O(n log n) |
| `coordinate_median` | Coordinate-wise median | O(n) |
| DBSCAN anomaly detection | Pre-filters outlier clusters | O(n²) |

### Secure Aggregation

Uses **additive secret sharing** so the server learns only `Σ W_i` — never any individual `W_i`:
```python
aggregator = SecureAggregator(min_clients=5, threshold=3)
```

Clients exchange masked updates using pairwise random masks that cancel in the sum. Requires a minimum quorum of clients to reconstruct the aggregate.

---

## Differential Privacy

Two mechanisms in `privacy/differential_privacy.py`:

### Laplace Mechanism — Pure ε-DP

Adds `Lap(sensitivity/ε)` noise to each parameter:

```python
dp = LaplaceMechanism(epsilon=1.0)
noisy_weights = dp.add_noise(weights, sensitivity=1.0)
```

Privacy cost accumulates **linearly** over rounds: after `T` rounds, total ε = `T * ε_round`.

### Gaussian Mechanism — (ε, δ)-DP

Adds `N(0, σ²)` noise where `σ = sqrt(2 ln(1.25/δ)) * sensitivity / ε`:

```python
dp = GaussianMechanism(epsilon=1.0, delta=1e-5)
noisy_weights = dp.add_noise(weights, sensitivity=1.0)
cost_eps, cost_delta = dp.get_privacy_cost(num_rounds=50)
```

Supports **Rényi DP composition** via moments accountant — achieves tighter privacy bounds than linear composition for long training runs.

### `DifferentialPrivacyManager`

Wraps both mechanisms, tracks cumulative privacy budget, enforces budget limits:
```python
manager = DifferentialPrivacyManager(total_epsilon=10.0, total_delta=1e-4)
manager.apply_privacy(weights, sensitivity=1.0, mechanism="gaussian")
print(manager.remaining_budget())  # {'epsilon': 8.3, 'delta': 8.7e-5}
```

---

## Training Algorithms

### Asynchronous FL

Eliminates the synchronization barrier — clients submit updates as they complete training. The server applies updates immediately with **staleness discounting**:

```python
# Staleness discount: older updates count less
discount = 1.0 / (1 + alpha * staleness)
effective_weight = client_weight * discount
```

`AsyncUpdateBuffer` enforces a `staleness_threshold`: updates more than `k` global rounds stale are rejected.

### Cross-Silo FL

Designed for organization-to-organization collaboration with legal/trust constraints:

```python
silo = SiloIdentity(silo_id="hospital-a", organization="General Hospital", domain="radiology")
agreement = SiloAgreement(silos=["hospital-a", "hospital-b"], terms={...})
```

`CrossSiloManager` handles trust negotiation, capability exchange, and mandatory secure aggregation between silos.

### Personalized Federated Learning

Each client maintains a local **personalization layer** on top of the shared global model:

```
Global base model ──→ Client A's personalization head
                 └──→ Client B's personalization head
```

The global layers converge toward general representations; personalization layers adapt to local distributions without polluting the shared model.

### Meta-Learning: FedMAML and FedReptile

For fast adaptation to new tasks from limited local data.

**FedMAML**: Inner loop adapts for `K` steps on local data; outer loop meta-updates global weights using second-order gradients:
```python
meta_learner = FederatedMetaLearner(strategy="maml", inner_lr=0.01, meta_lr=0.001, inner_steps=5)
```

**FedReptile** (first-order, cheaper):
```python
# Reptile meta-update: move toward locally-adapted weights
global_weights = global_weights + meta_lr * mean(adapted_i - global for adapted_i in clients)
```

---

## Model Compression

Reduces communication overhead — the primary bottleneck in large-scale FL.

| Technique | Typical Compression | Quality Impact |
|-----------|--------------------|-|
| 8-bit quantization | 4× | Minimal (<0.5% accuracy drop) |
| Top-k sparsification | 10–100× | Moderate (depends on k) |
| Magnitude pruning | 2–10× | Depends on sparsity level |

```python
compressor = QuantizationCompressor(config={"quantization_bits": 8})
compressed, metadata = compressor.compress(weights)
# ... transmit compressed ...
recovered = compressor.decompress(compressed, metadata)
```

`FederatedMetrics` tracks compression ratios, round times, per-client accuracy, and convergence curves.

---

## Integration with ASI:BUILD

The federated module is **not yet wired** to the Cognitive Blackboard. A natural integration would look like:

```python
class FederatedBlackboardAdapter:
    """Publishes FL training events to the Cognitive Blackboard."""
    
    def on_round_complete(self, round_id: int, metrics: Dict[str, float]):
        self.blackboard.write(BlackboardEntry(
            key=f"federated:round:{round_id}",
            value=metrics,
            source="federated_manager",
            tags=["federated", "training_metrics"]
        ))
        self.event_bus.publish(Event(
            type="FEDERATED_ROUND_COMPLETE",
            data={"round": round_id, "accuracy": metrics["accuracy"]}
        ))
```

This would enable other modules (e.g., consciousness, safety) to observe federation progress in real-time and gate training continuation on ethical/safety checks.

**Related Issue**: [#37 — Wire EthicalVerificationEngine into Blackboard write/read pipeline](https://github.com/web3guru888/asi-build/issues/37)

---

## Rings Network Synergy

The `rings` module provides a DID-authenticated P2P transport. An intriguing integration: replace the FedAvg star topology (all clients contact a central server) with **gossip-based decentralized aggregation** over Rings:

```
Traditional FL: Client → Server → Client (hub-and-spoke)
Rings-FL: Client ↔ Client ↔ Client (gossip graph, no central server)
```

Gossip-based FL (e.g., [Gossip Learning](https://arxiv.org/abs/1905.13720)) can achieve similar convergence to FedAvg with no single point of failure and full DID-based authentication.

---

## Open Research Questions

1. **Privacy-utility for Φ** — How much Laplace/Gaussian noise can we add to activations before IIT Φ becomes meaningless? Is there a threshold ε where consciousness measurement survives DP?

2. **Non-IID convergence** — Cognitive specialization implies heterogeneous local distributions. Standard FedAvg convergence assumes bounded data heterogeneity (bounded gradient divergence). What do the bounds look like for deliberately specialized cognitive agents?

3. **Byzantine robustness vs. cognitive diversity** — Krum filters "outlier" updates. But a minority cognitive node with novel activations might be the most valuable contributor. Should Byzantine robustness be *disabled* for trusted cognitive sub-networks?

4. **Gossip over Rings** — Is Rings's peer discovery protocol compatible with gossip-based FL? Can DID-signed gradient updates provide the same security guarantees as secure aggregation?

5. **Federated consciousness** — What does federated learning *mean* for a consciousness-measuring system? If Φ is computed on the global federated model, what is the "experiential unit"?

---

## See Also
- [Rings Network](Rings-Network) — P2P transport layer  
- [Architecture](Architecture) — Cognitive Blackboard integration  
- [Cognitive Blackboard](Cognitive-Blackboard) — Event-driven module communication  
- [Safety Module](Safety-Module) — Ethical verification engine  

---

*Module status: Implemented · Not yet Blackboard-integrated · See [Issue #37](https://github.com/web3guru888/asi-build/issues/37) for integration roadmap*
