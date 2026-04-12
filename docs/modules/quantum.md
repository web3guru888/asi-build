# Quantum

> **Maturity**: `experimental` · **Adapter**: `QuantumBlackboardAdapter`

Quantum computing simulation and hybrid quantum-classical ML processing. Provides gate-level quantum circuit simulation, QAOA (Quantum Approximate Optimization Algorithm) for combinatorial optimization, VQE (Variational Quantum Eigensolver) for finding ground state energies, and hybrid ML processors that combine quantum feature maps with classical neural networks. Designed for exploring quantum advantage in ASI reasoning tasks without requiring physical quantum hardware.

## Key Classes

| Class | Description |
|-------|-------------|
| `QuantumSimulator` | Gate-level quantum circuit simulation |
| `HybridMLProcessor` | Quantum-classical ML pipeline combining quantum feature maps with classical networks |
| `QAOA` | Quantum Approximate Optimization Algorithm for combinatorial problems |
| `VQE` | Variational Quantum Eigensolver for ground state energy computation |

## Example Usage

```python
from asi_build.quantum import QuantumSimulator, QAOA
sim = QuantumSimulator(num_qubits=4)
sim.h(0)  # Hadamard gate
sim.cx(0, 1)  # CNOT gate
result = sim.measure()
qaoa = QAOA(num_qubits=4, depth=3)
optimal = qaoa.optimize(cost_function=problem_hamiltonian)
```

## Blackboard Integration

QuantumBlackboardAdapter publishes quantum measurement results, circuit execution metrics, and optimization progress; consumes problem specifications from reasoning and optimization modules for quantum processing.
