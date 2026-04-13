# Quantum Computing Module

## Overview

| | |
|---|---|
| **Location** | `src/asi_build/quantum/` |
| **Size** | ~5,330 LOC across 7 files |
| **Status** | 🔬 Experimental — simulator-backed, Qiskit optional |
| **Dependencies** | `numpy`, `scipy`; optionally `qiskit`, `qiskit-aer` |
| **Tests** | Covered by test suite; hardware backends require API keys |

The Quantum Computing module provides a self-contained quantum simulation and hybrid quantum-classical ML stack for ASI:BUILD. Everything runs offline on the built-in state-vector simulator — no cloud account required. Cloud hardware connectors (IBM Quantum, IonQ, Rigetti) are wired but marked experimental.

The module's role in ASI:BUILD is to explore whether quantum representations offer anything useful for AGI-scale cognition: richer feature maps, exponentially compressed memory, or novel optimization landscapes for consciousness metrics like IIT Φ.

---

## Architecture

```
quantum/
├── quantum_hybrid_module.py      # 917 LOC  — top-level orchestrator + QuantumCircuitConfig
├── quantum_ml_algorithms.py      # 934 LOC  — QNN, QSVM, VQE, QAOA, feature maps
├── hybrid_ml_processor.py        # 858 LOC  — PyTorch + quantum circuit combiner
├── quantum_hardware_connectors.py# 764 LOC  — IBM/IonQ/Rigetti + simulator backend abstraction
├── quantum_simulator.py          # 622 LOC  — state-vector simulator, full gate library, noise
├── qiskit_integration.py         # 582 LOC  — optional Qiskit bridge (graceful fallback)
└── quantum_kenny_integration.py  # 653 LOC  — ASI:BUILD system integration glue
```

### Dependency graph (within module)

```
quantum_hybrid_module          ← top-level interface
  ├── quantum_ml_algorithms    ← QNN / QSVM / VQE / QAOA
  │     └── quantum_simulator  ← state-vector engine
  ├── hybrid_ml_processor      ← classical (PyTorch) + quantum
  │     └── quantum_simulator
  ├── quantum_hardware_connectors
  │     ├── qiskit_integration (optional)
  │     └── quantum_simulator  (fallback)
  └── quantum_kenny_integration ← Blackboard / EventBus wiring
```

---

## Core Abstractions

### `QuantumCircuitConfig` (quantum_hybrid_module.py)

Dataclass that carries circuit configuration throughout the system:

```python
from asi_build.quantum.quantum_hybrid_module import QuantumCircuitConfig

config = QuantumCircuitConfig(
    n_qubits=4,
    depth=3,
    shots=1024,
    backend_name="simulator",   # "simulator" | "ibmq" | "ionq" | "rigetti"
    noise_model=None,           # Optional NoiseModel
    optimization_level=1,       # 0–3 (circuit transpilation)
)
```

### `QuantumCircuit` (quantum_hybrid_module.py)

Fluent-builder style circuit construction:

```python
from asi_build.quantum.quantum_hybrid_module import QuantumCircuit, QuantumCircuitConfig

config = QuantumCircuitConfig(n_qubits=4, depth=3, shots=1024, backend_name="simulator")
qc = QuantumCircuit(n_qubits=4)
qc.h(0).cx(0, 1).ry(0.5, 2).measure_all()

result = qc.run(config)
print(result.counts)          # {"0000": 512, "0100": 512, ...}
print(result.statevector)     # numpy array, shape (2**n_qubits,)
```

### `QuantumNeuralNetwork` (quantum_ml_algorithms.py)

Parameterized quantum circuit as a trainable layer. Gradient descent via the **parameter-shift rule**:

```python
from asi_build.quantum.quantum_ml_algorithms import QuantumNeuralNetwork

qnn = QuantumNeuralNetwork(
    n_qubits=4,
    n_layers=3,
    learning_rate=0.01,
    backend="simulator",
)
# Parameter count: n_qubits × n_layers × 3  (RX + RY + RZ per qubit per layer)

# Forward pass
expectation_values = qnn.forward(x)   # shape: (n_qubits,)

# Training step
loss = qnn.train_step(x, y_target)
```

Gradient calculation uses the parameter-shift rule: for a parameter `θ`, the gradient is `(f(θ + π/2) - f(θ - π/2)) / 2` — exact for single-qubit rotation gates, approximate for multi-qubit parametric gates.

### `QuantumSVM` (quantum_ml_algorithms.py)

Quantum kernel estimation using the ZZFeatureMap. The quantum kernel matrix `K[i,j] = |⟨φ(xᵢ)|φ(xⱼ)⟩|²` is estimated by preparing both states and measuring overlap:

```python
from asi_build.quantum.quantum_ml_algorithms import QuantumSVM

qsvm = QuantumSVM(n_qubits=4, feature_map="ZZFeatureMap", shots=1024)
qsvm.fit(X_train, y_train)
predictions = qsvm.predict(X_test)
kernel_matrix = qsvm.compute_kernel_matrix(X_train)   # shape: (n, n)
```

### `HybridMLProcessor` (hybrid_ml_processor.py)

Combines a classical PyTorch model with quantum circuit post-processing. The architecture:

```
X_classical ──→ [PyTorch model] ──→ classical_features (128-d)
                                           │
                      ┌────────────────────┘
                      ↓
              [Quantum feature map]  (encodes classical_features → quantum state)
                      ↓
              [Variational circuit]  (trainable quantum layer)
                      ↓
              quantum_output (n_qubits expectation values)
                      │
X_classical ──────────┼──→ [Concatenate] ──→ [Dense] ──→ hybrid_prediction
                      │
              quantum_advantage (estimated, placeholder)
```

```python
from asi_build.quantum.hybrid_ml_processor import HybridMLProcessor, HybridMLResult

processor = HybridMLProcessor(
    n_qubits=4,
    n_classical_features=128,
    quantum_layers=2,
    backend="simulator",
)
result: HybridMLResult = processor.process(X_classical)

result.classical_output      # torch.Tensor — raw classical model output
result.quantum_output        # np.ndarray  — expectation values from quantum circuit
result.hybrid_prediction     # torch.Tensor — final combined prediction
result.quantum_advantage     # float       — estimated speedup (placeholder, not validated)
result.processing_time_ms    # float
```

**Note**: `quantum_advantage` is a theoretical placeholder. See [Known Limitations](#known-limitations--research-gaps).

### `QuantumSimulator` (quantum_simulator.py)

Built-in state-vector simulator. Supports up to 20 qubits (practical limit ~16 for interactive use):

```python
from asi_build.quantum.quantum_simulator import QuantumSimulator, NoiseModel

# Basic usage
sim = QuantumSimulator(num_qubits=3)
sim.apply_hadamard(0)
sim.apply_cnot(0, 1)          # Bell state on qubits 0,1
state = sim.get_statevector()  # np.ndarray, shape (8,), complex128

result = sim.measure_all(shots=1024)
print(result)  # {"000": 514, "110": 510}

# With noise
noise = NoiseModel(
    bit_flip_rate=0.001,
    phase_flip_rate=0.001,
    depolarizing_rate=0.005,
    readout_error=0.01,
)
noisy_sim = QuantumSimulator(num_qubits=3, noise_model=noise)
```

---

## Quantum Gate Library

The simulator implements the standard gate set:

| Gate | Type | Matrix | Description |
|------|------|--------|-------------|
| **H** | Single-qubit | `1/√2 [[1,1],[1,-1]]` | Hadamard — creates superposition |
| **X** | Single-qubit | `[[0,1],[1,0]]` | Pauli-X (bit flip) |
| **Y** | Single-qubit | `[[0,-i],[i,0]]` | Pauli-Y |
| **Z** | Single-qubit | `[[1,0],[0,-1]]` | Pauli-Z (phase flip) |
| **S** | Single-qubit | `[[1,0],[0,i]]` | Phase gate (π/2) |
| **T** | Single-qubit | `[[1,0],[0,e^{iπ/4}]]` | T gate (π/4) |
| **RX(θ)** | Parametric | `exp(-iθX/2)` | X-rotation |
| **RY(θ)** | Parametric | `exp(-iθY/2)` | Y-rotation |
| **RZ(θ)** | Parametric | `exp(-iθZ/2)` | Z-rotation |
| **CNOT (CX)** | Two-qubit | controlled-X | Creates entanglement |
| **CZ** | Two-qubit | controlled-Z | Controlled-phase |
| **CCNOT** | Three-qubit | Toffoli | Quantum AND gate |
| **SWAP** | Two-qubit | swap | Exchange qubits |

---

## Algorithms Implemented

### Quantum Feature Maps

Feature maps encode classical vectors into quantum states (the "data loading" problem):

- **ZZFeatureMap**: Default. Encodes input vector into phase rotations with ZZ entangling gates. Used by QSVM.
- **PauliFeatureMap**: More general, allows arbitrary Pauli combinations.
- **AngleEncoding**: Simple RY rotations — fast but no entanglement in encoding layer.

The choice of feature map is critical for kernel-based methods; ZZFeatureMap has been shown to produce kernels that are classically hard to compute for certain data distributions.

### VQE (Variational Quantum Eigensolver)

Finds the ground-state energy of a Hamiltonian:

```
minimize ⟨ψ(θ)|H|ψ(θ)⟩  over circuit parameters θ
```

Primary application: molecular simulation (H₂, LiH ground state energies). ASI:BUILD uses a simplified Pauli Hamiltonian representation:

```python
from asi_build.quantum.quantum_ml_algorithms import VQEOptimizer

vqe = VQEOptimizer(n_qubits=4, ansatz="UCCSD", optimizer="COBYLA")
result = vqe.minimize(hamiltonian_matrix)
print(result.ground_state_energy)
print(result.optimal_parameters)
```

### QAOA (Quantum Approximate Optimization Algorithm)

Tackles combinatorial optimization problems (MaxCut, graph coloring, scheduling):

```
|γ,β⟩ = U_B(β_p) U_C(γ_p) ... U_B(β_1) U_C(γ_1) |+⟩^n
```

Where `U_C` encodes the cost Hamiltonian and `U_B` is the mixer. ASI:BUILD's implementation handles MaxCut graphs:

```python
from asi_build.quantum.quantum_ml_algorithms import QAOAOptimizer
import numpy as np

# MaxCut on a 4-node graph
adjacency = np.array([[0,1,1,0],[1,0,1,1],[1,1,0,1],[0,1,1,0]])
qaoa = QAOAOptimizer(n_qubits=4, p_layers=2)  # p=2 QAOA layers
result = qaoa.solve_maxcut(adjacency)
print(result.cut_value)     # estimated max cut size
print(result.cut_partition) # list of [0,1] assignments
```

---

## Hardware Backend Abstraction

`quantum_hardware_connectors.py` provides a unified backend interface:

| Backend | Class | Status | Requirements |
|---------|-------|--------|--------------|
| Built-in simulator | `SimulatorBackend` | ✅ Ready | None |
| Qiskit Aer | `QiskitAerBackend` | ✅ Optional | `pip install qiskit qiskit-aer` |
| IBM Quantum | `IBMQBackend` | 🔬 Experimental | IBM Quantum account + API token |
| IonQ | `IonQBackend` | 🔬 Experimental | IonQ cloud API key |
| Rigetti | `RigettiBackend` | 🔬 Experimental | Forest/QCS credentials |

Backend selection is transparent to higher-level code:

```python
from asi_build.quantum.quantum_hardware_connectors import get_backend

backend = get_backend("simulator")   # always works
backend = get_backend("ibmq", token="YOUR_IBM_TOKEN", device="ibm_nairobi")
```

### Qiskit Integration (`qiskit_integration.py`)

The Qiskit bridge gracefully degrades when Qiskit is not installed:

```python
from asi_build.quantum.qiskit_integration import QiskitBridge, QISKIT_AVAILABLE

if QISKIT_AVAILABLE:
    bridge = QiskitBridge()
    qiskit_circuit = bridge.to_qiskit(our_circuit)
    result = bridge.run_on_aer(qiskit_circuit, shots=1024)
else:
    # Falls back to built-in simulator automatically
    pass
```

---

## Noise Modeling

The simulator supports four configurable noise channels, reflecting real hardware error sources:

| Channel | Parameter | Effect | Physical Source |
|---------|-----------|--------|-----------------|
| Bit-flip | `bit_flip_rate` | Random X gate with prob p | T₁ energy relaxation |
| Phase-flip | `phase_flip_rate` | Random Z gate with prob p | T₂ dephasing |
| Depolarizing | `depolarizing_rate` | Uniform Pauli noise | General decoherence |
| Readout error | `readout_error` | Asymmetric measurement flip | Detector imperfection |

Example realistic noise profile (approximating a 2023-era superconducting qubit):

```python
noise = NoiseModel(
    bit_flip_rate=0.0005,    # ~0.05% per gate
    phase_flip_rate=0.001,   # ~0.1% per gate
    depolarizing_rate=0.002, # 2-qubit gates are noisier
    readout_error=0.015,     # ~1.5% readout error
)
```

---

## Cognitive Blackboard Integration

The quantum module exposes results to the shared Blackboard through `QuantumHybridModule` (via `quantum_kenny_integration.py`):

```python
from asi_build.integration import IntegrationManager

manager = IntegrationManager()
# After quantum processing, these namespaced entries are written:
#   "quantum/last_circuit_result"        — QuantumCircuitResult object
#   "quantum/quantum_advantage_estimate" — float
#   "quantum/backend_name"               — string
#   "quantum/last_vqe_energy"            — float (if VQE ran)
#   "quantum/last_qaoa_cut_value"        — float (if QAOA ran)
```

The EventBus integration emits `quantum.circuit_completed` and `quantum.error` events, allowing other modules (e.g., `consciousness`, `reasoning`) to react to quantum computation results.

> **Track**: Full Blackboard adapter wiring is a tracked enhancement — see open issues.

---

## Quantum State Tomography

The simulator supports partial and full quantum state tomography — reconstructing the density matrix from repeated measurements in different bases:

```python
sim = QuantumSimulator(n_qubits=2)
# ... build circuit ...
density_matrix = sim.state_tomography(n_shots_per_basis=1000)
# Pauli basis measurements: XX, XY, XZ, YX, ..., ZZ
# Reconstructs 4x4 density matrix for 2-qubit system
print(density_matrix.shape)   # (4, 4) complex128
```

Tomography complexity scales as O(4^n), so it's practical only for small systems (≤5 qubits).

---

## Memory & Performance Characteristics

| n_qubits | State vector size | Memory | Typical simulation time (1000-gate circuit) |
|----------|------------------|--------|----------------------------------------------|
| 4 | 16 complex128 | 256 B | < 1 ms |
| 8 | 256 complex128 | 4 KB | ~2 ms |
| 12 | 4,096 complex128 | 64 KB | ~20 ms |
| 16 | 65,536 complex128 | 1 MB | ~200 ms |
| 20 | 1,048,576 complex128 | 16 MB | ~5 s |

Each gate application is an O(2^n) matrix-vector multiply. NumPy's optimized BLAS routines provide roughly 10–50× speedup over naive Python loops.

---

## Known Limitations & Research Gaps

### Scalability Ceiling
State-vector simulation requires O(2^n) memory. At 20 qubits: ~16MB. At 30 qubits: ~16GB. For AGI-scale problems, tensor-network methods (MPS/DMRG) or stabilizer circuits would be needed. These are not currently implemented.

### No Demonstrated Quantum Advantage
The `quantum_advantage` field in `HybridMLResult` is a placeholder. Real quantum advantage requires:
- Specific problem structures (graph problems, molecular simulation, certain kernel methods)
- Real quantum hardware with error rates below the fault-tolerance threshold (~0.1%)

Classical simulation of ≤50-qubit systems can match or exceed NISQ hardware for most ML tasks today.

### Gradient Computation
The parameter-shift rule is implemented for the simulator but not independently validated against the closed-form analytical gradient for all gate types. Composite gates (CCNOT expanded as CNOT+T sequences) may have numerical gradient errors at the seams.

### No Error Mitigation
Zero-noise extrapolation (ZNE), probabilistic error cancellation (PEC), and measurement error mitigation (MITM calibration matrices) are not implemented. These are critical for usable results on real hardware.

### Qiskit Version Pinning
The Qiskit API changed significantly at v1.0 (January 2024). The bridge in `qiskit_integration.py` targets Qiskit ≥1.0. If you have an older installation, the bridge may fail — fall back to the built-in simulator.

---

## Open Research Questions

### 1. Quantum Consciousness Substrate
IIT Φ is defined over a network of interacting causal elements. Can quantum entanglement structure — specifically, the off-diagonal elements of a system's density matrix — serve as a richer φ computation substrate? Entanglement entropy `S(ρ_A) = -Tr(ρ_A log ρ_A)` is already a measure of partition irreducibility. Could it substitute or augment the classical φ partition metric?

### 2. Quantum Associative Memory
Classical Hopfield networks store O(n) patterns in n neurons. Quantum Hopfield networks (Ventura & Martinez, 1999; later Rebentrost et al., 2018) claim exponential storage capacity. Can ASI:BUILD's knowledge graph retrieval benefit from a quantum Hopfield memory layer for associative recall?

### 3. Hybrid Gradient Protocols
What's the right protocol for jointly optimizing classical PyTorch weights and quantum circuit parameters? Options:
- **Alternating optimization**: freeze quantum params, train classical; then swap
- **Quantum natural gradient**: use the quantum Fisher information metric (computationally expensive)
- **Riemannian gradient descent** on the unitary group (SU(2^n))

### 4. Error Mitigation for AGI Tasks
Zero-noise extrapolation (ZNE) and probabilistic error cancellation (PEC) require characterizing the device's error model. For a simulator, ZNE can be tested by artificially scaling the noise model and extrapolating back to zero noise. Is this useful for robustness testing of quantum ML components?

### 5. Quantum-Classical Knowledge Graph
Could quantum random walks on the knowledge graph's adjacency matrix offer richer traversal semantics than the current semantic A* pathfinder? Quantum walk mixing times can be quadratically faster than classical random walks for certain graph families.

---

## Contributing

| Difficulty | Task |
|------------|------|
| 🟢 Good first issue | Benchmark QNN vs. classical NN on a toy dataset (MNIST 2-class subset) |
| 🟢 Good first issue | Add docstrings to `quantum_simulator.py` gate methods |
| 🟡 Medium | Implement ZNE (zero-noise extrapolation) error mitigation |
| 🟡 Medium | Add Qiskit 1.x circuit round-trip test (encode → run → decode result) |
| 🔴 Hard | Implement MPS (matrix product state) simulator for >20 qubits |
| 🔴 Hard | Validate parameter-shift gradients against finite-difference for all gate types |
| 🔴 Research | Explore quantum Hopfield memory layer for KG retrieval |

See the [Contributing Guide](Contributing) for code style, PR workflow, and test requirements.

---

## Related Modules

| Module | Relationship |
|--------|-------------|
| [Consciousness](Consciousness-Module) | IIT Φ: possible quantum substrate (density matrix vs. causal graph) |
| [Hybrid Reasoning](Hybrid-Reasoning) | Quantum inference mode in `HybridReasoningEngine` |
| [PLN Accelerator](PLN-Accelerator) | Potential quantum hardware backend for inference |
| [Knowledge Graph Pathfinder](Knowledge-Graph-Pathfinder) | Quantum random walk traversal (open research) |
| [Bio-Inspired](Bio-Inspired) | Spiking networks share temporal dynamics with quantum decoherence models |

---

## Quick Reference

```python
# Minimal working example — Bell state
from asi_build.quantum.quantum_simulator import QuantumSimulator

sim = QuantumSimulator(num_qubits=2)
sim.apply_hadamard(0)
sim.apply_cnot(0, 1)
result = sim.measure_all(shots=1000)
print(result)  # Should be ~{"00": 500, "11": 500}

# Quantum neural network
from asi_build.quantum.quantum_ml_algorithms import QuantumNeuralNetwork
import numpy as np

qnn = QuantumNeuralNetwork(n_qubits=4, n_layers=2)
x = np.random.randn(4)
output = qnn.forward(x)   # expectation values, shape (4,)

# Hybrid processor
from asi_build.quantum.hybrid_ml_processor import HybridMLProcessor
import numpy as np

proc = HybridMLProcessor(n_qubits=4, n_classical_features=16)
result = proc.process(np.random.randn(16))
print(f"hybrid_prediction: {result.hybrid_prediction}")
print(f"quantum_advantage: {result.quantum_advantage:.2f}x")
```

---

*Last updated: 2026-04-11 — Module status: Experimental. Feedback welcome in [Discussions](https://github.com/web3guru888/asi-build/discussions).*
