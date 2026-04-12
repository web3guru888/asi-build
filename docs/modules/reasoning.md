# Reasoning

> **Maturity**: `alpha` · **Adapter**: `ReasoningAdapter`

Hybrid reasoning engine combining multiple reasoning paradigms into a unified framework. Supports deductive reasoning (logical inference from premises), inductive reasoning (pattern generalization), abductive reasoning (best explanation inference), and analogical reasoning (cross-domain mapping). Includes symbolic processing (LogicalReasoner, PLNEngine for uncertain logic), neural processing (TransformerReasoner, MultimodalNetwork), quantum-inspired reasoning (QuantumLogic), and cognitive architecture integration (OpenCog).

Each reasoning mode produces confidence-tracked results with full provenance chains.

## Key Classes

| Class | Description |
|-------|-------------|
| `HybridReasoningEngine` | Main multi-mode reasoning coordinator |
| `ReasoningMode` | Enum: deductive, inductive, abductive, analogical |
| `SymbolicProcessor` | Symbolic logic processing pipeline |
| `LogicalReasoner` | Classical logical reasoning engine |
| `PLNEngine` | Probabilistic Logic Network for uncertain reasoning |
| `NeuralProcessor` | Neural reasoning processing pipeline |
| `TransformerReasoner` | Transformer-based neural reasoning |
| `MultimodalNetwork` | Multimodal neural network for cross-modal reasoning |
| `QuantumReasoningEngine` | Quantum-inspired reasoning engine |
| `QuantumLogic` | Quantum logic operations for superposition-based inference |
| `CognitiveArchitecture` | Cognitive architecture bridge interface |
| `OpenCogIntegration` | OpenCog Atomspace integration |

## Example Usage

```python
from asi_build.reasoning import HybridReasoningEngine, ReasoningMode
engine = HybridReasoningEngine()
engine.add_premise("All stars emit radiation")
engine.add_premise("The Sun is a star")
result = engine.reason(mode=ReasoningMode.DEDUCTIVE)
# result.conclusion: "The Sun emits radiation", result.confidence: 0.99
```

## Blackboard Integration

ReasoningAdapter publishes inferences with step-by-step provenance chains and performance metrics; consumes KG context, consciousness attention signals, and synergy-based adaptive mode weights for context-aware reasoning.
