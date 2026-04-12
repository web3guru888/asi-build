# Consciousness

> **Maturity**: `beta` · **Adapter**: `ConsciousnessAdapter`

Consciousness modeling inspired by leading theories of consciousness. Implements Integrated Information Theory (IIT) with correct TPM-based Φ computation, Global Workspace Theory (GWT) for information broadcasting, Attention Schema Theory (AST) for attention modeling, predictive processing, metacognition, self-awareness, theory of mind, qualia processing, emotional consciousness, sensory integration, temporal consciousness, and memory integration. The ConsciousnessOrchestrator coordinates all subsystems into a unified consciousness model. One of the most feature-rich modules with 18 exported classes.

## Key Classes

| Class | Description |
|-------|-------------|
| `BaseConsciousness` / `ConsciousnessState` / `ConsciousnessMetrics` | Base infrastructure |
| `GlobalWorkspaceTheory` | GWT workspace broadcasting |
| `IntegratedInformationTheory` | IIT Φ computation via TPM |
| `AttentionSchemaTheory` | Attention schema modeling |
| `PredictiveProcessing` | Predictive coding |
| `MetacognitionSystem` | Self-monitoring |
| `SelfAwarenessEngine` | Self-model |
| `TheoryOfMind` | Agent mental model |
| `QualiaProcessor` | Subjective experience |
| `EmotionalConsciousness` | Emotional integration |
| `RecursiveSelfImprovement` | Self-improvement cycles |
| `ConsciousnessOrchestrator` | Unified coordinator |

## Example Usage

```python
from asi_build.consciousness import GlobalWorkspaceTheory, IntegratedInformationTheory
gwt = GlobalWorkspaceTheory()
gwt.add_to_workspace("visual", data={"object": "anomaly", "confidence": 0.92})
broadcast = gwt.broadcast()
iit = IntegratedInformationTheory()
phi = iit.compute_phi(network_state=[1, 0, 1, 1])
```

## Blackboard Integration

ConsciousnessAdapter publishes Φ values, GWT broadcasts, and consciousness state; consumes reasoning outputs to GWT workspace and synergy signals for attention modulation.
