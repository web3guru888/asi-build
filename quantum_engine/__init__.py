"""
Kenny Quantum Computing Framework

A comprehensive quantum computing module for Kenny AI system that provides:
- Quantum circuit simulation
- Quantum algorithms implementation
- Quantum machine learning
- Quantum cryptography
- Quantum error correction
- Quantum-classical hybrid algorithms

This module integrates quantum computing capabilities into Kenny's AI-powered
GUI automation system, enabling quantum-enhanced decision making and optimization.

Author: Kenny Quantum Team
Version: 1.0.0
License: MIT
"""

from .quantum_simulator import QuantumSimulator, QuantumCircuit, QuantumGate
from .qiskit_integration import QiskitInterface, QuantumBackend
from .quantum_ml import QuantumMachineLearning, QuantumNeuralNetwork
from .quantum_crypto import QuantumCryptography, QuantumKeyDistribution
from .shors_algorithm import ShorsAlgorithm, QuantumFactorization
from .grovers_algorithm import GroversAlgorithm, QuantumSearch
from .quantum_annealing import QuantumAnnealer, AnnealingOptimizer
from .vqe_algorithm import VariationalQuantumEigensolver, VQEOptimizer
from .quantum_error_correction import QuantumErrorCorrection, StabilizerCode
from .hybrid_algorithms import QuantumClassicalHybrid, QAOA
from .quantum_fourier_transform import QuantumFourierTransform, QFTCircuit
from .quantum_phase_estimation import QuantumPhaseEstimation, PhaseEstimator
from .quantum_teleportation import QuantumTeleportation, TeleportationProtocol
from .quantum_supremacy import QuantumSupremacy, SupremacyBenchmark
from .quantum_optimization import QuantumOptimization, QuantumApproximateOptimization
from .quantum_utils import QuantumUtils, QuantumMath, QuantumVisualization

__version__ = "1.0.0"
__author__ = "Kenny Quantum Team"

# Module exports
__all__ = [
    # Core simulation
    'QuantumSimulator',
    'QuantumCircuit', 
    'QuantumGate',
    
    # Qiskit integration
    'QiskitInterface',
    'QuantumBackend',
    
    # Machine learning
    'QuantumMachineLearning',
    'QuantumNeuralNetwork',
    
    # Cryptography
    'QuantumCryptography',
    'QuantumKeyDistribution',
    
    # Algorithms
    'ShorsAlgorithm',
    'QuantumFactorization',
    'GroversAlgorithm',
    'QuantumSearch',
    'QuantumAnnealer',
    'AnnealingOptimizer',
    'VariationalQuantumEigensolver',
    'VQEOptimizer',
    
    # Error correction
    'QuantumErrorCorrection',
    'StabilizerCode',
    
    # Hybrid algorithms
    'QuantumClassicalHybrid',
    'QAOA',
    
    # Quantum transforms
    'QuantumFourierTransform',
    'QFTCircuit',
    'QuantumPhaseEstimation',
    'PhaseEstimator',
    
    # Protocols
    'QuantumTeleportation',
    'TeleportationProtocol',
    
    # Benchmarks and optimization
    'QuantumSupremacy',
    'SupremacyBenchmark',
    'QuantumOptimization',
    'QuantumApproximateOptimization',
    
    # Utilities
    'QuantumUtils',
    'QuantumMath',
    'QuantumVisualization'
]

# Version info
version_info = (1, 0, 0)

def get_version():
    """Get the version string for the quantum module."""
    return __version__

def get_quantum_capabilities():
    """Return a dictionary of quantum computing capabilities."""
    return {
        'simulation': True,
        'qiskit_integration': True,
        'machine_learning': True,
        'cryptography': True,
        'error_correction': True,
        'hybrid_algorithms': True,
        'optimization': True,
        'benchmarking': True,
        'max_qubits': 20,  # For classical simulation
        'supported_gates': ['X', 'Y', 'Z', 'H', 'CNOT', 'CZ', 'T', 'S', 'RX', 'RY', 'RZ'],
        'algorithms': ['Shor', 'Grover', 'VQE', 'QAOA', 'QFT', 'QPE']
    }

def initialize_quantum_system():
    """Initialize the Kenny quantum computing system."""
    print("Initializing Kenny Quantum Computing Framework v1.0.0")
    print("Quantum capabilities loaded successfully.")
    return get_quantum_capabilities()