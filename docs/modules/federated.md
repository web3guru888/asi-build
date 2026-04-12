# Federated Learning

> **Maturity**: `alpha` · **Adapter**: `FederatedLearningBlackboardAdapter`

Federated learning framework supporting privacy-preserving distributed machine learning. Implements FedAvg aggregation, secure aggregation protocols, Byzantine-robust aggregation, differential privacy (DP) noise injection, secret sharing for secure computation, model compression for efficient communication, and personalized/transfer/meta/asynchronous federated learning variants.

One of the most complete federated learning implementations with 16 exported classes.

## Key Classes

| Class | Description |
|-------|-------------|
| `FederatedManager` | Core lifecycle manager |
| `FederatedClient` | Client-side federated training participant |
| `FederatedServer` | Server-side federated training coordinator |
| `FedAvgAggregator` | Standard FedAvg aggregation |
| `SecureAggregator` | Cryptographic secure aggregation |
| `ByzantineRobustAggregator` | Byzantine fault tolerance for federated rounds |
| `DifferentialPrivacyManager` | DP noise calibration and privacy budget tracking |
| `PersonalizedFederatedLearning` | Per-client model personalization |
| `FederatedTransferLearning` | Cross-domain federated transfer |
| `AsynchronousFederatedLearning` | Asynchronous client updates |
| `FederatedMetaLearning` | Meta-learning across federated clients |
| `ModelCompressor` | Gradient and model compression |
| `FederatedMetrics` | Training analytics and convergence tracking |

## Example Usage

```python
from asi_build.federated import FederatedManager, FedAvgAggregator, DifferentialPrivacyManager
manager = FederatedManager(num_clients=10, rounds=50)
aggregator = FedAvgAggregator()
dp = DifferentialPrivacyManager(epsilon=1.0, delta=1e-5)
manager.run_training(aggregator=aggregator, privacy=dp)
```

## Blackboard Integration

FederatedLearningBlackboardAdapter publishes training round metrics, privacy budget usage, and model convergence status; consumes distributed training configuration and resource allocations.
