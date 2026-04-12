# AGI Reproducibility

> **Maturity**: `alpha` · **Adapter**: `ReproducibilityBlackboardAdapter`

Experiment tracking and reproducibility auditing for AI research workflows. Provides SQLite-backed experiment logging with git-aware version tracking, platform configuration management, and validation pipelines. Ensures that every experiment can be faithfully reproduced with identical results.

## Key Classes

| Class | Description |
|-------|-------------|
| `ExperimentTracker` | SQLite-backed experiment logging |
| `VersionManager` | Git-aware version tracking |
| `PlatformConfig` | Platform configuration management |
| `ValidationPipeline` | Result validation and comparison |

## Example Usage

```python
from asi_build.agi_reproducibility import ExperimentTracker
tracker = ExperimentTracker(db_path="experiments.db")
exp_id = tracker.start_experiment("hypothesis_test", params={"lr": 0.01})
tracker.log_result(exp_id, metric="accuracy", value=0.95)
```

## Blackboard Integration

ReproducibilityBlackboardAdapter publishes experiment metadata and version snapshots to the blackboard; consumes results from other modules for automatic audit trail creation.
