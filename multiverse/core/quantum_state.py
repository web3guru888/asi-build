"""
Quantum State Management
=======================

Manages quantum states, superposition, entanglement, and quantum operations
within the multiverse framework.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import cmath
import uuid
from scipy.linalg import expm
from scipy.sparse import csr_matrix


class QuantumStateType(Enum):
    """Types of quantum states."""
    PURE = "pure"
    MIXED = "mixed"
    ENTANGLED = "entangled"
    SUPERPOSITION = "superposition"
    COHERENT = "coherent"
    SQUEEZED = "squeezed"


@dataclass
class QuantumMeasurement:
    """Result of a quantum measurement."""
    measurement_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    observable: str = ""
    eigenvalue: complex = 0+0j
    probability: float = 0.0
    state_after_measurement: Optional['QuantumState'] = None
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    collapsed: bool = False


class QuantumState:
    """
    Represents a quantum state in the multiverse framework.
    
    Supports pure states, mixed states, superposition, entanglement,
    and various quantum operations.
    """
    
    def __init__(self, 
                 state_vector: Optional[np.ndarray] = None,
                 density_matrix: Optional[np.ndarray] = None,
                 state_type: QuantumStateType = QuantumStateType.PURE,
                 dimension: int = 2,
                 name: str = ""):
        """
        Initialize quantum state.
        
        Args:
            state_vector: State vector for pure states
            density_matrix: Density matrix for mixed states
            state_type: Type of quantum state
            dimension: Hilbert space dimension
            name: Optional name for the state
        """
        self.state_id = str(uuid.uuid4())
        self.name = name or f"quantum_state_{self.state_id[:8]}"
        self.state_type = state_type
        self.dimension = dimension
        self.logger = logging.getLogger(f"multiverse.quantum.{self.name}")
        
        # State representation
        self._state_vector: Optional[np.ndarray] = None
        self._density_matrix: Optional[np.ndarray] = None
        
        # Quantum properties
        self.is_normalized = True
        self.entanglement_partners: List[str] = []
        self.coherence_time = float('inf')
        self.decoherence_rate = 0.0
        
        # Measurement history
        self.measurement_history: List[QuantumMeasurement] = []
        
        # Initialize state
        if state_vector is not None:
            self.set_state_vector(state_vector)
        elif density_matrix is not None:
            self.set_density_matrix(density_matrix)
        else:
            self._initialize_default_state()
    
    def _initialize_default_state(self):
        """Initialize default quantum state."""
        if self.state_type == QuantumStateType.PURE:
            # Initialize to |0⟩ state
            self._state_vector = np.zeros(self.dimension, dtype=complex)
            self._state_vector[0] = 1.0
        else:
            # Initialize to completely mixed state
            self._density_matrix = np.eye(self.dimension) / self.dimension
    
    def set_state_vector(self, state_vector: np.ndarray):
        """Set the state vector for pure states."""
        if len(state_vector) != self.dimension:
            raise ValueError(f"State vector dimension {len(state_vector)} "
                           f"doesn't match expected {self.dimension}")
        
        self._state_vector = np.array(state_vector, dtype=complex)
        self._normalize_state_vector()
        self.state_type = QuantumStateType.PURE
        self._density_matrix = None  # Clear density matrix
    
    def set_density_matrix(self, density_matrix: np.ndarray):
        """Set the density matrix for mixed states."""
        if density_matrix.shape != (self.dimension, self.dimension):
            raise ValueError(f"Density matrix shape {density_matrix.shape} "
                           f"doesn't match expected ({self.dimension}, {self.dimension})")
        
        self._density_matrix = np.array(density_matrix, dtype=complex)
        self._normalize_density_matrix()
        self.state_type = QuantumStateType.MIXED
        self._state_vector = None  # Clear state vector
    
    def _normalize_state_vector(self):
        """Normalize the state vector."""
        if self._state_vector is not None:
            norm = np.linalg.norm(self._state_vector)
            if norm > 1e-10:
                self._state_vector /= norm
                self.is_normalized = True
            else:
                self.logger.warning("State vector has zero norm")
                self.is_normalized = False
    
    def _normalize_density_matrix(self):
        """Normalize the density matrix to have trace 1."""
        if self._density_matrix is not None:
            trace = np.trace(self._density_matrix)
            if abs(trace) > 1e-10:
                self._density_matrix /= trace
                self.is_normalized = True
            else:
                self.logger.warning("Density matrix has zero trace")
                self.is_normalized = False
    
    @property
    def state_vector(self) -> Optional[np.ndarray]:
        """Get the state vector."""
        return self._state_vector.copy() if self._state_vector is not None else None
    
    @property
    def density_matrix(self) -> np.ndarray:
        """Get the density matrix."""
        if self._density_matrix is not None:
            return self._density_matrix.copy()
        elif self._state_vector is not None:
            # Convert pure state to density matrix
            psi = self._state_vector.reshape(-1, 1)
            return np.outer(psi, psi.conj())
        else:
            raise ValueError("No state representation available")
    
    def create_superposition(self, coefficients: Optional[List[complex]] = None) -> 'QuantumState':
        """
        Create a superposition state.
        
        Args:
            coefficients: Coefficients for superposition basis states
            
        Returns:
            New QuantumState in superposition
        """
        if coefficients is None:
            # Create equal superposition
            coefficients = [1.0 / np.sqrt(self.dimension)] * self.dimension
        
        if len(coefficients) != self.dimension:
            raise ValueError(f"Number of coefficients {len(coefficients)} "
                           f"doesn't match dimension {self.dimension}")
        
        superposition_vector = np.array(coefficients, dtype=complex)
        
        new_state = QuantumState(
            state_vector=superposition_vector,
            state_type=QuantumStateType.SUPERPOSITION,
            dimension=self.dimension,
            name=f"{self.name}_superposition"
        )
        
        self.logger.info("Created superposition state: %s", new_state.name)
        return new_state
    
    def apply_unitary(self, unitary: np.ndarray) -> 'QuantumState':
        """
        Apply a unitary operation to the quantum state.
        
        Args:
            unitary: Unitary matrix to apply
            
        Returns:
            New quantum state after applying unitary
        """
        if unitary.shape != (self.dimension, self.dimension):
            raise ValueError(f"Unitary shape {unitary.shape} "
                           f"doesn't match dimension {self.dimension}")
        
        # Check if matrix is unitary
        if not self._is_unitary(unitary):
            self.logger.warning("Matrix may not be unitary")
        
        if self._state_vector is not None:
            # Apply to state vector
            new_vector = unitary @ self._state_vector
            return QuantumState(
                state_vector=new_vector,
                state_type=self.state_type,
                dimension=self.dimension,
                name=f"{self.name}_evolved"
            )
        else:
            # Apply to density matrix
            rho = self.density_matrix
            new_rho = unitary @ rho @ unitary.conj().T
            return QuantumState(
                density_matrix=new_rho,
                state_type=self.state_type,
                dimension=self.dimension,
                name=f"{self.name}_evolved"
            )
    
    def _is_unitary(self, matrix: np.ndarray, tolerance: float = 1e-10) -> bool:
        """Check if a matrix is unitary."""
        product = matrix @ matrix.conj().T
        identity = np.eye(matrix.shape[0])
        return np.allclose(product, identity, atol=tolerance)
    
    def measure(self, observable: np.ndarray, 
                collapse: bool = True) -> QuantumMeasurement:
        """
        Perform a quantum measurement.
        
        Args:
            observable: Observable operator (Hermitian matrix)
            collapse: Whether to collapse the state after measurement
            
        Returns:
            Measurement result
        """
        if observable.shape != (self.dimension, self.dimension):
            raise ValueError(f"Observable shape {observable.shape} "
                           f"doesn't match dimension {self.dimension}")
        
        # Get eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eigh(observable)
        
        # Calculate measurement probabilities
        rho = self.density_matrix
        probabilities = []
        for i, eigenval in enumerate(eigenvalues):
            projector = np.outer(eigenvectors[:, i], eigenvectors[:, i].conj())
            prob = np.real(np.trace(rho @ projector))
            probabilities.append(prob)
        
        # Randomly select outcome based on probabilities
        outcome_index = np.random.choice(len(eigenvalues), p=probabilities)
        measured_eigenvalue = eigenvalues[outcome_index]
        measured_probability = probabilities[outcome_index]
        
        # Create measurement result
        measurement = QuantumMeasurement(
            observable="custom_observable",
            eigenvalue=complex(measured_eigenvalue),
            probability=measured_probability,
            collapsed=collapse
        )
        
        # Collapse state if requested
        if collapse:
            projector = np.outer(eigenvectors[:, outcome_index], 
                               eigenvectors[:, outcome_index].conj())
            if self._state_vector is not None:
                # Collapse state vector
                collapsed_vector = projector @ self._state_vector
                collapsed_vector /= np.linalg.norm(collapsed_vector)
                measurement.state_after_measurement = QuantumState(
                    state_vector=collapsed_vector,
                    dimension=self.dimension,
                    name=f"{self.name}_collapsed"
                )
            else:
                # Collapse density matrix
                collapsed_rho = projector @ rho @ projector / measured_probability
                measurement.state_after_measurement = QuantumState(
                    density_matrix=collapsed_rho,
                    dimension=self.dimension,
                    name=f"{self.name}_collapsed"
                )
        
        self.measurement_history.append(measurement)
        self.logger.info("Quantum measurement performed: eigenvalue=%.4f, prob=%.4f",
                        measured_eigenvalue, measured_probability)
        
        return measurement
    
    def entangle_with(self, other_state: 'QuantumState') -> 'QuantumState':
        """
        Create an entangled state with another quantum state.
        
        Args:
            other_state: Other quantum state to entangle with
            
        Returns:
            Entangled composite state
        """
        # Create tensor product of the two states
        if self._state_vector is not None and other_state._state_vector is not None:
            entangled_vector = np.kron(self._state_vector, other_state._state_vector)
            composite_dimension = self.dimension * other_state.dimension
            
            entangled_state = QuantumState(
                state_vector=entangled_vector,
                state_type=QuantumStateType.ENTANGLED,
                dimension=composite_dimension,
                name=f"{self.name}_entangled_{other_state.name}"
            )
        else:
            # Use density matrices
            rho1 = self.density_matrix
            rho2 = other_state.density_matrix
            entangled_rho = np.kron(rho1, rho2)
            composite_dimension = self.dimension * other_state.dimension
            
            entangled_state = QuantumState(
                density_matrix=entangled_rho,
                state_type=QuantumStateType.ENTANGLED,
                dimension=composite_dimension,
                name=f"{self.name}_entangled_{other_state.name}"
            )
        
        # Update entanglement information
        self.entanglement_partners.append(other_state.state_id)
        other_state.entanglement_partners.append(self.state_id)
        
        self.logger.info("Created entangled state: %s", entangled_state.name)
        return entangled_state
    
    def calculate_fidelity(self, other_state: 'QuantumState') -> float:
        """
        Calculate fidelity between this state and another.
        
        Args:
            other_state: Other quantum state
            
        Returns:
            Fidelity value between 0 and 1
        """
        if self.dimension != other_state.dimension:
            raise ValueError("States must have same dimension for fidelity calculation")
        
        rho1 = self.density_matrix
        rho2 = other_state.density_matrix
        
        # Calculate fidelity F = Tr(√(√ρ₁ ρ₂ √ρ₁))²
        sqrt_rho1 = self._matrix_sqrt(rho1)
        middle = sqrt_rho1 @ rho2 @ sqrt_rho1
        sqrt_middle = self._matrix_sqrt(middle)
        fidelity = np.real(np.trace(sqrt_middle))**2
        
        return min(1.0, max(0.0, fidelity))  # Clamp to [0, 1]
    
    def _matrix_sqrt(self, matrix: np.ndarray) -> np.ndarray:
        """Calculate matrix square root."""
        eigenvals, eigenvecs = np.linalg.eigh(matrix)
        eigenvals = np.maximum(eigenvals, 0)  # Ensure non-negative
        sqrt_eigenvals = np.sqrt(eigenvals)
        return eigenvecs @ np.diag(sqrt_eigenvals) @ eigenvecs.conj().T
    
    def calculate_von_neumann_entropy(self) -> float:
        """Calculate von Neumann entropy of the state."""
        rho = self.density_matrix
        eigenvals = np.linalg.eigvals(rho)
        eigenvals = eigenvals[eigenvals > 1e-12]  # Remove zero eigenvalues
        
        entropy = -np.sum(eigenvals * np.log2(eigenvals))
        return np.real(entropy)
    
    def calculate_purity(self) -> float:
        """Calculate purity of the quantum state."""
        rho = self.density_matrix
        purity = np.real(np.trace(rho @ rho))
        return purity
    
    def is_pure_state(self) -> bool:
        """Check if the state is pure."""
        purity = self.calculate_purity()
        return abs(purity - 1.0) < 1e-10
    
    def is_entangled(self) -> bool:
        """Check if the state is entangled (for composite systems)."""
        return len(self.entanglement_partners) > 0
    
    def apply_decoherence(self, decoherence_strength: float = 0.01):
        """Apply decoherence to the quantum state."""
        if self._state_vector is not None:
            # Convert to density matrix and apply decoherence
            rho = self.density_matrix
        else:
            rho = self._density_matrix.copy()
        
        # Simple decoherence model: mix with maximally mixed state
        mixed_state = np.eye(self.dimension) / self.dimension
        rho_decohered = (1 - decoherence_strength) * rho + decoherence_strength * mixed_state
        
        self.set_density_matrix(rho_decohered)
        self.decoherence_rate += decoherence_strength
        
        self.logger.debug("Applied decoherence: strength=%.4f", decoherence_strength)
    
    def time_evolve(self, hamiltonian: np.ndarray, time: float) -> 'QuantumState':
        """
        Evolve the quantum state under a Hamiltonian.
        
        Args:
            hamiltonian: Hamiltonian operator
            time: Evolution time
            
        Returns:
            Time-evolved quantum state
        """
        # Calculate time evolution operator U = exp(-iHt/ℏ)
        # Setting ℏ = 1 for simplicity
        evolution_operator = expm(-1j * hamiltonian * time)
        
        return self.apply_unitary(evolution_operator)
    
    def calculate_total_energy(self) -> float:
        """Calculate total quantum energy of the state."""
        if self._state_vector is not None:
            # For pure states, use expectation value of simple Hamiltonian
            h = self._create_simple_hamiltonian()
            energy = np.real(np.conj(self._state_vector) @ h @ self._state_vector)
        else:
            # For mixed states
            h = self._create_simple_hamiltonian()
            rho = self.density_matrix
            energy = np.real(np.trace(rho @ h))
        
        return energy
    
    def _create_simple_hamiltonian(self) -> np.ndarray:
        """Create a simple Hamiltonian for energy calculations."""
        # Simple harmonic oscillator-like Hamiltonian
        h = np.zeros((self.dimension, self.dimension), dtype=complex)
        for i in range(self.dimension):
            h[i, i] = i + 0.5  # Energy levels: 0.5, 1.5, 2.5, ...
        return h
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the quantum state."""
        return {
            'state_id': self.state_id,
            'name': self.name,
            'state_type': self.state_type.value,
            'dimension': self.dimension,
            'is_normalized': self.is_normalized,
            'is_pure': self.is_pure_state(),
            'is_entangled': self.is_entangled(),
            'purity': self.calculate_purity(),
            'von_neumann_entropy': self.calculate_von_neumann_entropy(),
            'total_energy': self.calculate_total_energy(),
            'entanglement_partners': self.entanglement_partners.copy(),
            'measurement_count': len(self.measurement_history),
            'decoherence_rate': self.decoherence_rate,
            'coherence_time': self.coherence_time
        }
    
    def __repr__(self) -> str:
        """String representation of the quantum state."""
        return (f"QuantumState(name='{self.name}', "
                f"type={self.state_type.value}, "
                f"dim={self.dimension}, "
                f"purity={self.calculate_purity():.3f})")


class QuantumStateVector:
    """
    Collection of quantum states with vector operations.
    """
    
    def __init__(self, states: Optional[List[QuantumState]] = None):
        """Initialize quantum state vector."""
        self.states = states or []
        self.vector_id = str(uuid.uuid4())
        self.logger = logging.getLogger("multiverse.quantum.state_vector")
    
    def add_state(self, state: QuantumState):
        """Add a quantum state to the vector."""
        self.states.append(state)
        self.logger.debug("Added state %s to vector", state.name)
    
    def remove_state(self, state_id: str) -> bool:
        """Remove a quantum state from the vector."""
        for i, state in enumerate(self.states):
            if state.state_id == state_id:
                del self.states[i]
                self.logger.debug("Removed state %s from vector", state_id)
                return True
        return False
    
    def get_state(self, state_id: str) -> Optional[QuantumState]:
        """Get a specific quantum state by ID."""
        for state in self.states:
            if state.state_id == state_id:
                return state
        return None
    
    def calculate_collective_entropy(self) -> float:
        """Calculate collective von Neumann entropy."""
        total_entropy = 0.0
        for state in self.states:
            total_entropy += state.calculate_von_neumann_entropy()
        return total_entropy
    
    def calculate_average_fidelity(self, other_vector: 'QuantumStateVector') -> float:
        """Calculate average fidelity with another state vector."""
        if len(self.states) != len(other_vector.states):
            raise ValueError("State vectors must have same length")
        
        total_fidelity = 0.0
        for state1, state2 in zip(self.states, other_vector.states):
            total_fidelity += state1.calculate_fidelity(state2)
        
        return total_fidelity / len(self.states)
    
    def create_collective_superposition(self) -> QuantumState:
        """Create a collective superposition of all states."""
        if not self.states:
            raise ValueError("No states in vector")
        
        # Assume all states have same dimension
        dimension = self.states[0].dimension
        total_dimension = dimension ** len(self.states)
        
        # Create tensor product of all state vectors
        collective_vector = np.array([1.0], dtype=complex)
        for state in self.states:
            if state.state_vector is not None:
                collective_vector = np.kron(collective_vector, state.state_vector)
            else:
                # Convert mixed state to pure state (approximate)
                eigenvals, eigenvecs = np.linalg.eigh(state.density_matrix)
                max_eigen_idx = np.argmax(eigenvals)
                pure_vector = eigenvecs[:, max_eigen_idx]
                collective_vector = np.kron(collective_vector, pure_vector)
        
        return QuantumState(
            state_vector=collective_vector,
            state_type=QuantumStateType.SUPERPOSITION,
            dimension=total_dimension,
            name=f"collective_superposition_{self.vector_id[:8]}"
        )
    
    def __len__(self) -> int:
        """Get number of states in vector."""
        return len(self.states)
    
    def __iter__(self):
        """Iterate over quantum states."""
        return iter(self.states)
    
    def __getitem__(self, index: int) -> QuantumState:
        """Get state by index."""
        return self.states[index]