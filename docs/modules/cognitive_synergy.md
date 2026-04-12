# Cognitive Synergy

> **Maturity**: `beta` · **Adapter**: `CognitiveSynergyAdapter`

Cross-module cognitive synergy measurement and emergence detection. Quantifies how ASI modules interact and amplify each other's capabilities using information-theoretic metrics (mutual information, transfer entropy, phase locking, Lempel-Ziv complexity). Detects emergent properties that arise from module interactions, tracks coherence across the system, and profiles inter-module dynamics. Includes the PRIMUS foundation for cognitive primitives and self-organization mechanisms.

## Key Classes

| Class | Description |
|-------|-------------|
| `CognitiveSynergyEngine` | Core synergy measurement engine |
| `SynergyMetrics` / `SynergyMeasurement` / `SynergyProfile` | Metric computation and profiling |
| `EmergentPropertyDetector` / `EmergentProperty` / `EmergenceSignature` | Emergence detection |
| `PRIMUSFoundation` / `PRIMUSState` / `CognitivePrimitive` | Cognitive primitive framework |
| `SelfOrganizationMechanism` / `HomeostaticController` / `AdaptiveRestructurer` | Self-organization |
| `ReasoningEngine` / `ReasoningType` | Synergy-aware reasoning |
| `PatternMiningEngine` / `Pattern` | Pattern discovery |

## Example Usage

```python
from asi_build.cognitive_synergy import CognitiveSynergyEngine, SynergyMetrics
engine = CognitiveSynergyEngine()
engine.register_module("reasoning", time_series=[0.8, 0.85, 0.9])
engine.register_module("knowledge_graph", time_series=[0.7, 0.75, 0.82])
synergy = engine.compute_pairwise("reasoning", "knowledge_graph")
```

## Blackboard Integration

CognitiveSynergyAdapter publishes pair synergy values, coherence scores, emergence detections, and module profiles; consumes time-series data from all registered modules for continuous synergy measurement.
