# Distributed Training

> **Maturity**: `alpha` · **Adapter**: `DistributedTrainingAdapter`

Distributed model training orchestration across multiple compute nodes. Provides federated orchestration for coordinating training across heterogeneous nodes, Byzantine-tolerant aggregation that detects and excludes malicious gradient updates, and communication-efficient gradient compression.

Uses a dynamic auto-import pattern that loads all callables from the package.

## Key Classes

| Class | Description |
|-------|-------------|
| `FederatedOrchestrator` | Multi-node training coordination |
| `ByzantineTolerantAggregator` | Robust gradient aggregation with Byzantine fault detection |
| `GradientCompressor` | Communication-efficient training via gradient compression |
| `TrainingCoordinator` | Distributed training lifecycle management |

## Example Usage

```python
from asi_build.distributed_training import FederatedOrchestrator
orchestrator = FederatedOrchestrator(num_workers=4, aggregation="byzantine_tolerant")
orchestrator.distribute_model(model_weights)
aggregated = orchestrator.aggregate_round(worker_updates)
```

## Blackboard Integration

DistributedTrainingAdapter publishes training progress, aggregation metrics, and Byzantine detection alerts; consumes compute resource allocations from the compute module.
