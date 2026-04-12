# PLN Accelerator

> **Maturity**: `alpha` · **Adapter**: None

Probabilistic Logic Network (PLN) accelerator for high-performance uncertain reasoning. Designed to accelerate PLN inference through FPGA-based hardware (Verilog), quantum circuit implementations (Qiskit), a natural language-to-logic bridge, and distributed PLN execution across multiple nodes. Currently a placeholder module with no public API exports — the acceleration backends are under development.

## Key Classes

| Class | Description |
|-------|-------------|
| *(No public API classes exported)* | Acceleration backends under development |

## Example Usage

```python
# PLN acceleration is currently accessed through the reasoning module
from asi_build.reasoning import PLNEngine
pln = PLNEngine()
pln.add_belief("rain", truth_value=(0.8, 0.9))  # (strength, confidence)
pln.add_rule("rain", "wet_ground", rule_type="deduction")
result = pln.infer("wet_ground")
```

## Blackboard Integration

No blackboard adapter. PLN inference is accessed through the reasoning module's ReasoningAdapter.
