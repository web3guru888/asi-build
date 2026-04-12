# Optimization

> **Maturity**: `alpha` · **Adapter**: `VLABlackboardAdapter` (partial)

Optimization algorithms and hyperparameter tuning for AI model training. Includes VLA++ (Vision-Language-Action) model optimization pipelines, hyperparameter search strategies, and training loop utilities. Currently a minimal module with no public API exports in `__init__.py` — classes are accessed by importing from submodules directly.

## Key Classes

| Class | Description |
|-------|-------------|
| `VLAPlusPlus` | Vision-Language-Action model combining visual, language, and action modalities |
| `VLATrainer` | Training loop for VLA++ models with learning rate scheduling |
| `VLAOptimizationPipeline` | End-to-end VLA optimization pipeline |
| `FHEParameters` | Encryption parameter optimization (note: has known import issues) |

## Example Usage

```python
from asi_build.optimization.vla import VLAPlusPlus, VLATrainer
model = VLAPlusPlus(vision_dim=512, language_dim=768, action_dim=7)
trainer = VLATrainer(model, learning_rate=1e-4, batch_size=32)
trainer.train(dataset, epochs=10)
```

## Blackboard Integration

VLABlackboardAdapter (partial coverage) publishes VLA training metrics and optimization progress; the optimization module itself lacks a dedicated adapter for general hyperparameter tuning.
