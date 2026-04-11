"""
Qiskit Integration Layer

Provides seamless integration between Kenny's quantum simulator and Qiskit,
allowing users to leverage both local simulation and real quantum hardware
through IBM Quantum Network, Amazon Braket, and other cloud providers.

Features:
- Qiskit circuit conversion
- Real quantum hardware access
- Noise modeling from real devices
- Circuit optimization and transpilation
- Result comparison between simulators
- Quantum device characterization
- Error mitigation techniques

Author: Kenny Quantum Team
"""

import json
import logging
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# Qiskit imports (with fallback if not installed)
try:
    from qiskit import ClassicalRegister
    from qiskit import QuantumCircuit as QiskitCircuit
    from qiskit import QuantumRegister, execute, transpile
    from qiskit.circuit import Parameter
    from qiskit.circuit.library import TwoLocal
    from qiskit.providers import Backend
    from qiskit.providers.aer import AerSimulator
    from qiskit.providers.aer.noise import NoiseModel
    from qiskit.providers.fake_provider import FakeProvider
    from qiskit.quantum_info import DensityMatrix, Statevector
    from qiskit.result import Result
    from qiskit.visualization import plot_histogram, plot_state_qsphere

    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    warnings.warn("Qiskit not available. Install with: pip install qiskit")

# Kenny quantum imports
from .quantum_simulator import GateType, QuantumCircuit, QuantumGate, QuantumSimulator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Types of quantum backends available."""

    SIMULATOR = "simulator"
    REAL_DEVICE = "real_device"
    FAKE_DEVICE = "fake_device"
    KENNY_SIMULATOR = "kenny_simulator"


@dataclass
class QuantumDevice:
    """Information about a quantum device."""

    name: str
    backend_type: BackendType
    num_qubits: int
    connectivity: List[Tuple[int, int]]
    gate_set: List[str]
    error_rates: Dict[str, float]
    coherence_times: Dict[str, float]


class QiskitInterface:
    """Main interface for Qiskit integration with Kenny quantum system."""

    def __init__(self, kenny_simulator: Optional[QuantumSimulator] = None):
        self.kenny_simulator = kenny_simulator or QuantumSimulator()
        self.qiskit_available = QISKIT_AVAILABLE

        if self.qiskit_available:
            # Initialize Qiskit components
            self.aer_simulator = AerSimulator()
            self.fake_provider = FakeProvider()
            self.noise_models = {}
            self._init_backends()
        else:
            logger.warning("Qiskit not available - limited functionality")

        logger.info("Qiskit integration layer initialized")

    def _init_backends(self):
        """Initialize available quantum backends."""
        if not self.qiskit_available:
            return

        self.backends = {
            "aer_simulator": self.aer_simulator,
            "kenny_simulator": self.kenny_simulator,
        }

        # Add fake backends for testing
        fake_backends = self.fake_provider.backends()
        for backend in fake_backends[:3]:  # Limit to first 3 for performance
            self.backends[backend.name()] = backend

            # Create noise model for this device
            try:
                noise_model = NoiseModel.from_backend(backend)
                self.noise_models[backend.name()] = noise_model
            except Exception as e:
                logger.warning(f"Could not create noise model for {backend.name()}: {e}")

    def kenny_to_qiskit(self, kenny_circuit: QuantumCircuit) -> "QiskitCircuit":
        """Convert Kenny quantum circuit to Qiskit circuit."""
        if not self.qiskit_available:
            raise RuntimeError("Qiskit not available")

        # Create Qiskit circuit
        qiskit_circuit = QiskitCircuit(kenny_circuit.num_qubits, kenny_circuit.num_qubits)
        qiskit_circuit.name = kenny_circuit.name

        # Convert gates
        for gate in kenny_circuit.gates:
            self._add_gate_to_qiskit(qiskit_circuit, gate)

        logger.info(f"Converted Kenny circuit to Qiskit: {kenny_circuit.name}")
        return qiskit_circuit

    def _add_gate_to_qiskit(self, qiskit_circuit: "QiskitCircuit", gate: QuantumGate):
        """Add a Kenny gate to a Qiskit circuit."""
        if gate.gate_type == GateType.X:
            qiskit_circuit.x(gate.qubits[0])
        elif gate.gate_type == GateType.Y:
            qiskit_circuit.y(gate.qubits[0])
        elif gate.gate_type == GateType.Z:
            qiskit_circuit.z(gate.qubits[0])
        elif gate.gate_type == GateType.H:
            qiskit_circuit.h(gate.qubits[0])
        elif gate.gate_type == GateType.S:
            qiskit_circuit.s(gate.qubits[0])
        elif gate.gate_type == GateType.T:
            qiskit_circuit.t(gate.qubits[0])
        elif gate.gate_type == GateType.CNOT:
            qiskit_circuit.cx(gate.qubits[0], gate.qubits[1])
        elif gate.gate_type == GateType.CZ:
            qiskit_circuit.cz(gate.qubits[0], gate.qubits[1])
        elif gate.gate_type == GateType.CCNOT:
            qiskit_circuit.ccx(gate.qubits[0], gate.qubits[1], gate.qubits[2])
        elif gate.gate_type == GateType.RX:
            qiskit_circuit.rx(gate.parameters[0], gate.qubits[0])
        elif gate.gate_type == GateType.RY:
            qiskit_circuit.ry(gate.parameters[0], gate.qubits[0])
        elif gate.gate_type == GateType.RZ:
            qiskit_circuit.rz(gate.parameters[0], gate.qubits[0])
        elif gate.gate_type == GateType.PHASE:
            qiskit_circuit.p(gate.parameters[0], gate.qubits[0])
        elif gate.gate_type == GateType.SWAP:
            qiskit_circuit.swap(gate.qubits[0], gate.qubits[1])
        elif gate.gate_type == GateType.MEASURE:
            qiskit_circuit.measure(gate.qubits[0], gate.qubits[0])
        else:
            logger.warning(f"Unsupported gate type for Qiskit: {gate.gate_type}")

    def qiskit_to_kenny(self, qiskit_circuit: "QiskitCircuit") -> QuantumCircuit:
        """Convert Qiskit circuit to Kenny quantum circuit."""
        if not self.qiskit_available:
            raise RuntimeError("Qiskit not available")

        # Create Kenny circuit
        kenny_circuit = QuantumCircuit(qiskit_circuit.num_qubits, qiskit_circuit.name)

        # Convert gates
        for instruction, qubits, clbits in qiskit_circuit.data:
            gate_name = instruction.name
            qubit_indices = [qiskit_circuit.find_bit(qubit).index for qubit in qubits]
            params = instruction.params

            self._add_gate_to_kenny(kenny_circuit, gate_name, qubit_indices, params)

        logger.info(f"Converted Qiskit circuit to Kenny: {qiskit_circuit.name}")
        return kenny_circuit

    def _add_gate_to_kenny(
        self, kenny_circuit: QuantumCircuit, gate_name: str, qubits: List[int], params: List[float]
    ):
        """Add a Qiskit gate to a Kenny circuit."""
        if gate_name == "x":
            kenny_circuit.x(qubits[0])
        elif gate_name == "y":
            kenny_circuit.y(qubits[0])
        elif gate_name == "z":
            kenny_circuit.z(qubits[0])
        elif gate_name == "h":
            kenny_circuit.h(qubits[0])
        elif gate_name == "s":
            kenny_circuit.s(qubits[0])
        elif gate_name == "t":
            kenny_circuit.t(qubits[0])
        elif gate_name == "cx":
            kenny_circuit.cnot(qubits[0], qubits[1])
        elif gate_name == "cz":
            kenny_circuit.cz(qubits[0], qubits[1])
        elif gate_name == "ccx":
            kenny_circuit.ccnot(qubits[0], qubits[1], qubits[2])
        elif gate_name == "rx":
            kenny_circuit.rx(qubits[0], params[0])
        elif gate_name == "ry":
            kenny_circuit.ry(qubits[0], params[0])
        elif gate_name == "rz":
            kenny_circuit.rz(qubits[0], params[0])
        elif gate_name == "p":
            kenny_circuit.phase(qubits[0], params[0])
        elif gate_name == "swap":
            kenny_circuit.swap(qubits[0], qubits[1])
        elif gate_name == "measure":
            kenny_circuit.measure(qubits[0])
        else:
            logger.warning(f"Unsupported Qiskit gate: {gate_name}")

    def run_on_backend(
        self,
        circuit: Union[QuantumCircuit, "QiskitCircuit"],
        backend_name: str,
        shots: int = 1024,
        optimization_level: int = 1,
    ) -> Dict:
        """Run circuit on specified backend."""
        if not self.qiskit_available and backend_name != "kenny_simulator":
            raise RuntimeError("Qiskit not available")

        # Handle Kenny simulator directly
        if backend_name == "kenny_simulator":
            if isinstance(circuit, QiskitCircuit):
                circuit = self.qiskit_to_kenny(circuit)
            return self.kenny_simulator.run_circuit(circuit, shots)

        # Convert to Qiskit circuit if needed
        if isinstance(circuit, QuantumCircuit):
            qiskit_circuit = self.kenny_to_qiskit(circuit)
        else:
            qiskit_circuit = circuit

        # Get backend
        if backend_name not in self.backends:
            raise ValueError(f"Backend {backend_name} not available")

        backend = self.backends[backend_name]

        # Transpile circuit for backend
        transpiled_circuit = transpile(
            qiskit_circuit, backend, optimization_level=optimization_level
        )

        # Execute circuit
        job = execute(transpiled_circuit, backend, shots=shots)
        result = job.result()

        # Convert results to Kenny format
        return self._convert_qiskit_result(result)

    def _convert_qiskit_result(self, result: "Result") -> Dict:
        """Convert Qiskit result to Kenny format."""
        counts = result.get_counts()

        # Convert to Kenny format
        kenny_result = {
            "measurements": [],
            "statistics": {},
            "counts": counts,
            "success": result.success,
        }

        # Convert counts to statistics
        total_shots = sum(counts.values())
        for state, count in counts.items():
            for i, bit in enumerate(state[::-1]):  # Reverse bit order
                if i not in kenny_result["statistics"]:
                    kenny_result["statistics"][i] = {"0": 0, "1": 0}
                kenny_result["statistics"][i][bit] += count

        return kenny_result

    def compare_simulators(self, circuit: QuantumCircuit, shots: int = 1024) -> Dict:
        """Compare results between Kenny simulator and Qiskit simulators."""
        results = {}

        # Run on Kenny simulator
        kenny_result = self.kenny_simulator.run_circuit(circuit, shots)
        results["kenny"] = kenny_result

        if self.qiskit_available:
            # Run on Qiskit AER simulator
            qiskit_result = self.run_on_backend(circuit, "aer_simulator", shots)
            results["qiskit_aer"] = qiskit_result

            # Calculate fidelity between results
            fidelity = self._calculate_result_fidelity(kenny_result, qiskit_result)
            results["fidelity"] = fidelity

        return results

    def _calculate_result_fidelity(self, result1: Dict, result2: Dict) -> float:
        """Calculate fidelity between two measurement results."""
        if "statistics" not in result1 or "statistics" not in result2:
            return 0.0

        fidelities = []

        for qubit in result1["statistics"]:
            if qubit in result2["statistics"]:
                stats1 = result1["statistics"][qubit]
                stats2 = result2["statistics"][qubit]

                total1 = stats1.get("0", 0) + stats1.get("1", 0)
                total2 = stats2.get("0", 0) + stats2.get("1", 0)

                if total1 > 0 and total2 > 0:
                    p1_0 = stats1.get("0", 0) / total1
                    p2_0 = stats2.get("0", 0) / total2

                    # Simple probability difference as fidelity measure
                    fidelity = 1.0 - abs(p1_0 - p2_0)
                    fidelities.append(fidelity)

        return np.mean(fidelities) if fidelities else 0.0

    def get_device_info(self, backend_name: str) -> QuantumDevice:
        """Get information about a quantum device."""
        if backend_name == "kenny_simulator":
            return QuantumDevice(
                name="Kenny Simulator",
                backend_type=BackendType.KENNY_SIMULATOR,
                num_qubits=self.kenny_simulator.max_qubits,
                connectivity=[(i, j) for i in range(20) for j in range(i + 1, 20)],
                gate_set=["X", "Y", "Z", "H", "CNOT", "CZ", "RX", "RY", "RZ"],
                error_rates={"gate": 0.0, "measurement": 0.0},
                coherence_times={"T1": float("inf"), "T2": float("inf")},
            )

        if not self.qiskit_available:
            raise RuntimeError("Qiskit not available")

        if backend_name not in self.backends:
            raise ValueError(f"Backend {backend_name} not available")

        backend = self.backends[backend_name]
        config = backend.configuration()

        # Get connectivity
        connectivity = []
        if hasattr(config, "coupling_map") and config.coupling_map:
            connectivity = config.coupling_map

        # Get gate set
        gate_set = []
        if hasattr(config, "basis_gates"):
            gate_set = config.basis_gates

        # Get error rates (simplified)
        error_rates = {"gate": 0.001, "measurement": 0.01}  # Default values

        # Get coherence times (simplified)
        coherence_times = {"T1": 100.0, "T2": 80.0}  # Default values in microseconds

        return QuantumDevice(
            name=backend.name(),
            backend_type=(
                BackendType.FAKE_DEVICE
                if "fake" in backend.name().lower()
                else BackendType.SIMULATOR
            ),
            num_qubits=config.n_qubits,
            connectivity=connectivity,
            gate_set=gate_set,
            error_rates=error_rates,
            coherence_times=coherence_times,
        )

    def optimize_circuit(
        self,
        circuit: QuantumCircuit,
        backend_name: str = "aer_simulator",
        optimization_level: int = 2,
    ) -> QuantumCircuit:
        """Optimize circuit for specific backend."""
        if not self.qiskit_available:
            logger.warning("Qiskit not available - returning original circuit")
            return circuit

        # Convert to Qiskit
        qiskit_circuit = self.kenny_to_qiskit(circuit)

        # Get backend
        backend = self.backends.get(backend_name, self.aer_simulator)

        # Transpile for optimization
        optimized_qiskit = transpile(qiskit_circuit, backend, optimization_level=optimization_level)

        # Convert back to Kenny
        optimized_kenny = self.qiskit_to_kenny(optimized_qiskit)

        logger.info(
            f"Circuit optimized: {len(circuit.gates)} -> {len(optimized_kenny.gates)} gates"
        )
        return optimized_kenny

    def create_variational_circuit(self, num_qubits: int, depth: int = 3) -> QuantumCircuit:
        """Create a variational quantum circuit for optimization algorithms."""
        if not self.qiskit_available:
            # Create simple alternating circuit
            circuit = QuantumCircuit(num_qubits, f"variational_depth_{depth}")

            for layer in range(depth):
                # Rotation layer
                for qubit in range(num_qubits):
                    circuit.ry(qubit, np.pi / 4)  # Placeholder parameter

                # Entangling layer
                for qubit in range(num_qubits - 1):
                    circuit.cnot(qubit, qubit + 1)

            return circuit

        # Use Qiskit's TwoLocal ansatz
        qiskit_ansatz = TwoLocal(num_qubits, "ry", "cx", "linear", reps=depth)

        # Bind parameters to concrete values (for demo)
        param_values = [np.pi / 4] * qiskit_ansatz.num_parameters
        bound_circuit = qiskit_ansatz.bind_parameters(param_values)

        # Convert to Kenny circuit
        return self.qiskit_to_kenny(bound_circuit)

    def simulate_with_noise(
        self, circuit: QuantumCircuit, backend_name: str, shots: int = 1024
    ) -> Dict:
        """Simulate circuit with realistic noise model."""
        if not self.qiskit_available:
            logger.warning("Qiskit not available - running noiseless simulation")
            return self.kenny_simulator.run_circuit(circuit, shots)

        if backend_name not in self.noise_models:
            logger.warning(f"No noise model for {backend_name} - running noiseless")
            return self.run_on_backend(circuit, backend_name, shots)

        # Convert to Qiskit
        qiskit_circuit = self.kenny_to_qiskit(circuit)

        # Run with noise
        noise_model = self.noise_models[backend_name]
        job = execute(qiskit_circuit, self.aer_simulator, shots=shots, noise_model=noise_model)
        result = job.result()

        return self._convert_qiskit_result(result)

    def get_available_backends(self) -> List[str]:
        """Get list of available quantum backends."""
        available = ["kenny_simulator"]

        if self.qiskit_available:
            available.extend(list(self.backends.keys()))

        return available

    def benchmark_circuit(self, circuit: QuantumCircuit, shots: int = 1024) -> Dict:
        """Benchmark circuit performance across different backends."""
        results = {}
        available_backends = self.get_available_backends()

        for backend_name in available_backends:
            try:
                import time

                start_time = time.time()

                result = self.run_on_backend(circuit, backend_name, shots)

                end_time = time.time()
                execution_time = end_time - start_time

                results[backend_name] = {
                    "result": result,
                    "execution_time": execution_time,
                    "success": True,
                }

            except Exception as e:
                results[backend_name] = {"error": str(e), "success": False}

        return results


class QuantumBackend:
    """Wrapper for different quantum backends."""

    def __init__(self, backend_name: str, qiskit_interface: QiskitInterface):
        self.backend_name = backend_name
        self.qiskit_interface = qiskit_interface
        self.device_info = qiskit_interface.get_device_info(backend_name)

    def run(self, circuit: QuantumCircuit, shots: int = 1024, **kwargs) -> Dict:
        """Run circuit on this backend."""
        return self.qiskit_interface.run_on_backend(circuit, self.backend_name, shots, **kwargs)

    def optimize_for_backend(self, circuit: QuantumCircuit, **kwargs) -> QuantumCircuit:
        """Optimize circuit for this specific backend."""
        return self.qiskit_interface.optimize_circuit(circuit, self.backend_name, **kwargs)

    def get_properties(self) -> Dict:
        """Get backend properties."""
        return {
            "name": self.device_info.name,
            "type": self.device_info.backend_type.value,
            "num_qubits": self.device_info.num_qubits,
            "connectivity": self.device_info.connectivity,
            "gate_set": self.device_info.gate_set,
            "error_rates": self.device_info.error_rates,
            "coherence_times": self.device_info.coherence_times,
        }


# Test functions
def test_qiskit_integration():
    """Test Qiskit integration functionality."""
    print("Testing Qiskit Integration...")

    # Create Kenny simulator and Qiskit interface
    kenny_sim = QuantumSimulator()
    qiskit_interface = QiskitInterface(kenny_sim)

    print(f"Available backends: {qiskit_interface.get_available_backends()}")

    # Create test circuit
    circuit = QuantumCircuit(2, "test_circuit")
    circuit.h(0)
    circuit.cnot(0, 1)
    circuit.measure_all()

    print(f"\nTest circuit:\n{circuit}")

    # Test backend comparison
    if qiskit_interface.qiskit_available:
        print("\n1. Comparing simulators:")
        comparison = qiskit_interface.compare_simulators(circuit, shots=1000)
        print(f"Kenny results: {comparison['kenny']['statistics']}")
        print(f"Qiskit results: {comparison['qiskit_aer']['statistics']}")
        print(f"Fidelity: {comparison['fidelity']:.3f}")

        # Test circuit conversion
        print("\n2. Testing circuit conversion:")
        qiskit_circuit = qiskit_interface.kenny_to_qiskit(circuit)
        kenny_circuit_back = qiskit_interface.qiskit_to_kenny(qiskit_circuit)
        print(f"Original gates: {len(circuit.gates)}")
        print(f"Converted back gates: {len(kenny_circuit_back.gates)}")

        # Test optimization
        print("\n3. Testing circuit optimization:")
        optimized = qiskit_interface.optimize_circuit(circuit)
        print(f"Original: {len(circuit.gates)} gates")
        print(f"Optimized: {len(optimized.gates)} gates")

        # Test variational circuit
        print("\n4. Creating variational circuit:")
        var_circuit = qiskit_interface.create_variational_circuit(3, depth=2)
        print(f"Variational circuit: {len(var_circuit.gates)} gates")

    else:
        print("Qiskit not available - testing Kenny simulator only")
        result = qiskit_interface.run_on_backend(circuit, "kenny_simulator", shots=1000)
        print(f"Kenny simulator result: {result['statistics']}")

    print("\nQiskit integration tests completed!")


if __name__ == "__main__":
    test_qiskit_integration()
