"""
Quantum Probability Controller

Advanced quantum-level probability manipulation using wave function control,
quantum superposition, entanglement, and measurement collapse dynamics.
"""

import numpy as np
import cmath
import logging
from typing import Dict, List, Tuple, Optional, Any, Complex
from dataclasses import dataclass
from enum import Enum
import threading
import time
import random
import math
from concurrent.futures import ThreadPoolExecutor
from ..core.field_mathematics import FieldMathematics, WaveFunction


class QuantumState(Enum):
    """Quantum states for probability control."""
    SUPERPOSITION = "superposition"
    COLLAPSED = "collapsed"
    ENTANGLED = "entangled"
    DECOHERENT = "decoherent"
    COHERENT = "coherent"
    MIXED = "mixed"


class MeasurementBasis(Enum):
    """Measurement basis for quantum observations."""
    COMPUTATIONAL = "computational"  # |0⟩, |1⟩
    DIAGONAL = "diagonal"           # |+⟩, |-⟩
    CIRCULAR = "circular"           # |R⟩, |L⟩
    PROBABILITY = "probability"     # Custom probability basis


@dataclass
class QuantumProbabilityState:
    """Represents a quantum probability state."""
    state_id: str
    amplitudes: List[Complex]
    basis_states: List[str]
    entanglement_partners: List[str]
    coherence_time: float
    measurement_count: int
    creation_time: float
    last_measurement: float
    decoherence_rate: float
    fidelity: float


@dataclass
class QuantumMeasurement:
    """Result of a quantum measurement."""
    measurement_id: str
    state_id: str
    measured_value: Any
    probability: float
    basis: MeasurementBasis
    measurement_time: float
    post_measurement_state: List[Complex]
    von_neumann_entropy: float
    measurement_strength: float


class QuantumProbabilityController:
    """
    Advanced quantum probability manipulation system.
    
    This controller provides precise control over quantum probability
    distributions using wave function manipulation, superposition control,
    and quantum measurement dynamics.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.field_math = FieldMathematics()
        
        # Quantum system state
        self.quantum_states: Dict[str, QuantumProbabilityState] = {}
        self.entanglement_network: Dict[str, List[str]] = {}
        self.measurement_history: List[QuantumMeasurement] = []
        self.quantum_lock = threading.RLock()
        
        # Quantum constants
        self.PLANCK_CONSTANT = 6.62607015e-34
        self.REDUCED_PLANCK = self.PLANCK_CONSTANT / (2 * math.pi)
        self.QUANTUM_COHERENCE_TIME = 1e-6  # Microseconds
        self.DECOHERENCE_RATE = 1e-3
        self.MEASUREMENT_PRECISION = 1e-12
        
        # Quantum control parameters
        self.max_superposition_states = 256
        self.entanglement_strength_threshold = 0.5
        self.fidelity_threshold = 0.95
        self.coherence_threshold = 0.1
        
        # Initialize quantum random number generator
        self._quantum_rng = random.SystemRandom()
        
        self.logger.info("QuantumProbabilityController initialized")
    
    def create_quantum_superposition(
        self,
        probabilities: List[float],
        basis_labels: Optional[List[str]] = None,
        coherence_time: float = None
    ) -> str:
        """
        Create a quantum superposition state with specified probabilities.
        
        Args:
            probabilities: List of probability amplitudes
            basis_labels: Labels for basis states
            coherence_time: How long superposition remains coherent
            
        Returns:
            Quantum state ID
        """
        with self.quantum_lock:
            state_id = f"qs_{int(time.time() * 1000000)}"
            
            # Normalize probabilities
            total_prob = sum(probabilities)
            if total_prob == 0:
                raise ValueError("Total probability cannot be zero")
            
            normalized_probs = [p / total_prob for p in probabilities]
            
            # Convert probabilities to quantum amplitudes
            amplitudes = []
            for prob in normalized_probs:
                if prob < 0:
                    raise ValueError("Probability cannot be negative")
                
                # Amplitude = sqrt(probability) * phase
                magnitude = math.sqrt(prob)
                phase = self._quantum_rng.uniform(0, 2 * math.pi)
                amplitude = magnitude * cmath.exp(1j * phase)
                amplitudes.append(amplitude)
            
            # Generate basis labels if not provided
            if basis_labels is None:
                basis_labels = [f"|{i}⟩" for i in range(len(probabilities))]
            
            # Set coherence time
            if coherence_time is None:
                coherence_time = self.QUANTUM_COHERENCE_TIME
            
            # Create quantum state
            quantum_state = QuantumProbabilityState(
                state_id=state_id,
                amplitudes=amplitudes,
                basis_states=basis_labels,
                entanglement_partners=[],
                coherence_time=coherence_time,
                measurement_count=0,
                creation_time=time.time(),
                last_measurement=0,
                decoherence_rate=self.DECOHERENCE_RATE,
                fidelity=1.0
            )
            
            self.quantum_states[state_id] = quantum_state
            self.logger.info(f"Created quantum superposition {state_id} with {len(amplitudes)} states")
            
            return state_id
    
    def manipulate_wave_function(
        self,
        state_id: str,
        rotation_angles: Tuple[float, float, float],
        evolution_time: float = 0.0
    ) -> bool:
        """
        Apply unitary transformations to manipulate quantum wave function.
        
        Args:
            state_id: Quantum state to manipulate
            rotation_angles: (θ, φ, λ) Euler angles for rotation
            evolution_time: Time evolution parameter
            
        Returns:
            True if manipulation successful
        """
        with self.quantum_lock:
            if state_id not in self.quantum_states:
                return False
            
            state = self.quantum_states[state_id]
            
            # Check if state is still coherent
            if not self._is_state_coherent(state):
                self.logger.warning(f"State {state_id} has decoherent, manipulation may fail")
            
            # Apply rotation transformation
            transformed_amplitudes = self._apply_rotation_matrix(
                state.amplitudes, rotation_angles
            )
            
            # Apply time evolution
            if evolution_time > 0:
                transformed_amplitudes = self._apply_time_evolution(
                    transformed_amplitudes, evolution_time
                )
            
            # Update state
            state.amplitudes = transformed_amplitudes
            state.fidelity *= 0.99  # Slight fidelity loss from manipulation
            
            self.logger.info(f"Manipulated wave function for state {state_id}")
            return True
    
    def entangle_quantum_states(
        self,
        state_id1: str,
        state_id2: str,
        entanglement_strength: float = 1.0
    ) -> bool:
        """
        Create quantum entanglement between two probability states.
        
        Args:
            state_id1: First quantum state
            state_id2: Second quantum state
            entanglement_strength: Strength of entanglement (0-1)
            
        Returns:
            True if entanglement successful
        """
        with self.quantum_lock:
            if state_id1 not in self.quantum_states or state_id2 not in self.quantum_states:
                return False
            
            state1 = self.quantum_states[state_id1]
            state2 = self.quantum_states[state_id2]
            
            # Check entanglement compatibility
            if len(state1.amplitudes) != len(state2.amplitudes):
                self.logger.warning("States have different dimensionality, creating partial entanglement")
            
            # Create entanglement links
            if state_id2 not in state1.entanglement_partners:
                state1.entanglement_partners.append(state_id2)
            if state_id1 not in state2.entanglement_partners:
                state2.entanglement_partners.append(state_id1)
            
            # Update entanglement network
            if state_id1 not in self.entanglement_network:
                self.entanglement_network[state_id1] = []
            if state_id2 not in self.entanglement_network:
                self.entanglement_network[state_id2] = []
            
            self.entanglement_network[state_id1].append(state_id2)
            self.entanglement_network[state_id2].append(state_id1)
            
            # Apply entanglement transformation
            self._apply_entanglement_transformation(state1, state2, entanglement_strength)
            
            self.logger.info(f"Entangled states {state_id1} and {state_id2}")
            return True
    
    def measure_quantum_state(
        self,
        state_id: str,
        basis: MeasurementBasis = MeasurementBasis.COMPUTATIONAL,
        measurement_strength: float = 1.0
    ) -> QuantumMeasurement:
        """
        Perform quantum measurement and collapse wave function.
        
        Args:
            state_id: Quantum state to measure
            basis: Measurement basis
            measurement_strength: Strength of measurement (0-1)
            
        Returns:
            QuantumMeasurement result
        """
        with self.quantum_lock:
            if state_id not in self.quantum_states:
                raise ValueError(f"State {state_id} not found")
            
            state = self.quantum_states[state_id]
            measurement_id = f"qm_{int(time.time() * 1000000)}"
            
            # Calculate measurement probabilities
            probabilities = [abs(amp) ** 2 for amp in state.amplitudes]
            total_prob = sum(probabilities)
            
            if total_prob == 0:
                raise ValueError("State has zero probability")
            
            # Normalize probabilities
            probabilities = [p / total_prob for p in probabilities]
            
            # Perform measurement based on basis
            measured_index, measured_prob = self._perform_measurement(
                probabilities, basis, measurement_strength
            )
            
            # Calculate post-measurement state
            post_measurement_amplitudes = self._calculate_post_measurement_state(
                state.amplitudes, measured_index, measurement_strength
            )
            
            # Calculate von Neumann entropy
            entropy = self._calculate_von_neumann_entropy(probabilities)
            
            # Update state after measurement
            if measurement_strength == 1.0:
                # Full collapse
                state.amplitudes = post_measurement_amplitudes
            else:
                # Partial collapse - mix original and collapsed states
                mix_factor = measurement_strength
                for i in range(len(state.amplitudes)):
                    state.amplitudes[i] = (
                        (1 - mix_factor) * state.amplitudes[i] + 
                        mix_factor * post_measurement_amplitudes[i]
                    )
            
            state.measurement_count += 1
            state.last_measurement = time.time()
            state.fidelity *= (1.0 - measurement_strength * 0.1)
            
            # Create measurement result
            measurement = QuantumMeasurement(
                measurement_id=measurement_id,
                state_id=state_id,
                measured_value=measured_index,
                probability=measured_prob,
                basis=basis,
                measurement_time=time.time(),
                post_measurement_state=post_measurement_amplitudes.copy(),
                von_neumann_entropy=entropy,
                measurement_strength=measurement_strength
            )
            
            self.measurement_history.append(measurement)
            
            # Propagate measurement to entangled states
            self._propagate_measurement_to_entangled_states(state, measurement)
            
            self.logger.info(f"Measured state {state_id}: result = {measured_index}, P = {measured_prob:.4f}")
            
            return measurement
    
    def create_bell_state(self, bell_type: str = "phi_plus") -> Tuple[str, str]:
        """
        Create maximally entangled Bell states.
        
        Args:
            bell_type: Type of Bell state ("phi_plus", "phi_minus", "psi_plus", "psi_minus")
            
        Returns:
            Tuple of (state_id1, state_id2)
        """
        # Define Bell state amplitudes
        bell_states = {
            "phi_plus": [1/math.sqrt(2), 0, 0, 1/math.sqrt(2)],    # |Φ+⟩ = (|00⟩ + |11⟩)/√2
            "phi_minus": [1/math.sqrt(2), 0, 0, -1/math.sqrt(2)],  # |Φ-⟩ = (|00⟩ - |11⟩)/√2
            "psi_plus": [0, 1/math.sqrt(2), 1/math.sqrt(2), 0],    # |Ψ+⟩ = (|01⟩ + |10⟩)/√2
            "psi_minus": [0, 1/math.sqrt(2), -1/math.sqrt(2), 0]   # |Ψ-⟩ = (|01⟩ - |10⟩)/√2
        }
        
        if bell_type not in bell_states:
            raise ValueError(f"Unknown Bell state type: {bell_type}")
        
        amplitudes = bell_states[bell_type]
        
        # Create first qubit state
        state_id1 = self.create_quantum_superposition(
            probabilities=[abs(amplitudes[0])**2 + abs(amplitudes[1])**2,
                          abs(amplitudes[2])**2 + abs(amplitudes[3])**2],
            basis_labels=["|0⟩", "|1⟩"]
        )
        
        # Create second qubit state
        state_id2 = self.create_quantum_superposition(
            probabilities=[abs(amplitudes[0])**2 + abs(amplitudes[2])**2,
                          abs(amplitudes[1])**2 + abs(amplitudes[3])**2],
            basis_labels=["|0⟩", "|1⟩"]
        )
        
        # Entangle the states
        self.entangle_quantum_states(state_id1, state_id2, entanglement_strength=1.0)
        
        self.logger.info(f"Created Bell state {bell_type}: {state_id1}, {state_id2}")
        
        return state_id1, state_id2
    
    def apply_quantum_gate(
        self,
        state_id: str,
        gate_name: str,
        parameters: Optional[List[float]] = None
    ) -> bool:
        """
        Apply quantum gate operations to modify probability distributions.
        
        Args:
            state_id: Quantum state to operate on
            gate_name: Name of quantum gate
            parameters: Gate parameters if needed
            
        Returns:
            True if gate application successful
        """
        with self.quantum_lock:
            if state_id not in self.quantum_states:
                return False
            
            state = self.quantum_states[state_id]
            
            # Define quantum gates
            gates = {
                "X": self._pauli_x_gate,
                "Y": self._pauli_y_gate,
                "Z": self._pauli_z_gate,
                "H": self._hadamard_gate,
                "S": self._phase_gate,
                "T": self._t_gate,
                "RX": self._rotation_x_gate,
                "RY": self._rotation_y_gate,
                "RZ": self._rotation_z_gate
            }
            
            if gate_name not in gates:
                self.logger.error(f"Unknown gate: {gate_name}")
                return False
            
            # Apply gate
            try:
                gate_function = gates[gate_name]
                if parameters:
                    new_amplitudes = gate_function(state.amplitudes, parameters)
                else:
                    new_amplitudes = gate_function(state.amplitudes)
                
                state.amplitudes = new_amplitudes
                state.fidelity *= 0.995  # Slight fidelity loss
                
                self.logger.info(f"Applied {gate_name} gate to state {state_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error applying gate {gate_name}: {e}")
                return False
    
    def calculate_quantum_fidelity(self, state_id1: str, state_id2: str) -> float:
        """
        Calculate fidelity between two quantum states.
        
        Args:
            state_id1: First quantum state
            state_id2: Second quantum state
            
        Returns:
            Fidelity value (0-1)
        """
        if state_id1 not in self.quantum_states or state_id2 not in self.quantum_states:
            return 0.0
        
        state1 = self.quantum_states[state_id1]
        state2 = self.quantum_states[state_id2]
        
        # Calculate overlap
        overlap = 0j
        min_len = min(len(state1.amplitudes), len(state2.amplitudes))
        
        for i in range(min_len):
            overlap += np.conj(state1.amplitudes[i]) * state2.amplitudes[i]
        
        # Fidelity = |⟨ψ1|ψ2⟩|²
        fidelity = abs(overlap) ** 2
        
        return fidelity
    
    def get_quantum_state_info(self, state_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a quantum state."""
        if state_id not in self.quantum_states:
            return None
        
        state = self.quantum_states[state_id]
        
        # Calculate probabilities
        probabilities = [abs(amp) ** 2 for amp in state.amplitudes]
        
        # Calculate purity
        purity = sum(p ** 2 for p in probabilities)
        
        # Calculate entropy
        entropy = self._calculate_von_neumann_entropy(probabilities)
        
        return {
            'state_id': state.state_id,
            'dimension': len(state.amplitudes),
            'probabilities': probabilities,
            'basis_states': state.basis_states,
            'entanglement_partners': state.entanglement_partners,
            'coherence_time': state.coherence_time,
            'measurement_count': state.measurement_count,
            'fidelity': state.fidelity,
            'purity': purity,
            'entropy': entropy,
            'is_coherent': self._is_state_coherent(state),
            'age': time.time() - state.creation_time
        }
    
    def get_quantum_system_status(self) -> Dict[str, Any]:
        """Get comprehensive quantum system status."""
        total_entanglements = sum(len(partners) for partners in self.entanglement_network.values()) // 2
        
        coherent_states = sum(1 for state in self.quantum_states.values() 
                             if self._is_state_coherent(state))
        
        average_fidelity = (sum(state.fidelity for state in self.quantum_states.values()) / 
                           len(self.quantum_states) if self.quantum_states else 0)
        
        return {
            'total_quantum_states': len(self.quantum_states),
            'coherent_states': coherent_states,
            'total_entanglements': total_entanglements,
            'total_measurements': len(self.measurement_history),
            'average_fidelity': average_fidelity,
            'entanglement_networks': len(self.entanglement_network),
            'quantum_coherence_time': self.QUANTUM_COHERENCE_TIME,
            'decoherence_rate': self.DECOHERENCE_RATE
        }
    
    # Private helper methods
    
    def _is_state_coherent(self, state: QuantumProbabilityState) -> bool:
        """Check if quantum state is still coherent."""
        current_time = time.time()
        elapsed_time = current_time - state.creation_time
        
        # Exponential decoherence
        coherence_factor = math.exp(-elapsed_time * state.decoherence_rate)
        
        return coherence_factor > self.coherence_threshold
    
    def _apply_rotation_matrix(
        self,
        amplitudes: List[Complex],
        angles: Tuple[float, float, float]
    ) -> List[Complex]:
        """Apply rotation transformation to quantum amplitudes."""
        theta, phi, lambda_angle = angles
        
        # For 2D case (most common)
        if len(amplitudes) == 2:
            # Single qubit rotation
            cos_half_theta = math.cos(theta / 2)
            sin_half_theta = math.sin(theta / 2)
            
            # Rotation matrix
            u00 = cos_half_theta
            u01 = -cmath.exp(1j * lambda_angle) * sin_half_theta
            u10 = cmath.exp(1j * phi) * sin_half_theta
            u11 = cmath.exp(1j * (phi + lambda_angle)) * cos_half_theta
            
            a0, a1 = amplitudes[0], amplitudes[1]
            
            new_a0 = u00 * a0 + u01 * a1
            new_a1 = u10 * a0 + u11 * a1
            
            return [new_a0, new_a1]
        
        else:
            # For higher dimensions, apply rotation to first two components
            result = amplitudes.copy()
            if len(result) >= 2:
                rotated = self._apply_rotation_matrix(result[:2], angles)
                result[0] = rotated[0]
                result[1] = rotated[1]
            
            return result
    
    def _apply_time_evolution(self, amplitudes: List[Complex], time_param: float) -> List[Complex]:
        """Apply time evolution to quantum amplitudes."""
        result = []
        for i, amplitude in enumerate(amplitudes):
            # Apply energy-dependent phase evolution
            energy = i * self.REDUCED_PLANCK  # Simple energy levels
            phase_evolution = cmath.exp(-1j * energy * time_param / self.REDUCED_PLANCK)
            result.append(amplitude * phase_evolution)
        
        return result
    
    def _apply_entanglement_transformation(
        self,
        state1: QuantumProbabilityState,
        state2: QuantumProbabilityState,
        strength: float
    ) -> None:
        """Apply entanglement transformation between two states."""
        # Simple entanglement model - correlate amplitudes
        min_len = min(len(state1.amplitudes), len(state2.amplitudes))
        
        for i in range(min_len):
            # Create correlation between states
            correlation_factor = strength * cmath.exp(1j * self._quantum_rng.uniform(0, 2 * math.pi))
            
            original1 = state1.amplitudes[i]
            original2 = state2.amplitudes[i]
            
            # Apply entanglement mixing
            state1.amplitudes[i] = math.sqrt(1 - strength**2) * original1 + strength * correlation_factor * original2
            state2.amplitudes[i] = math.sqrt(1 - strength**2) * original2 + strength * np.conj(correlation_factor) * original1
    
    def _perform_measurement(
        self,
        probabilities: List[float],
        basis: MeasurementBasis,
        strength: float
    ) -> Tuple[int, float]:
        """Perform quantum measurement in specified basis."""
        # Transform probabilities based on measurement basis
        if basis == MeasurementBasis.DIAGONAL:
            # Transform to diagonal basis
            transformed_probs = self._transform_to_diagonal_basis(probabilities)
        elif basis == MeasurementBasis.CIRCULAR:
            # Transform to circular basis
            transformed_probs = self._transform_to_circular_basis(probabilities)
        else:
            # Computational basis (default)
            transformed_probs = probabilities
        
        # Perform probabilistic measurement
        rand_value = self._quantum_rng.random()
        cumulative_prob = 0.0
        
        for i, prob in enumerate(transformed_probs):
            cumulative_prob += prob
            if rand_value <= cumulative_prob:
                return i, prob
        
        # Fallback to last state
        return len(transformed_probs) - 1, transformed_probs[-1]
    
    def _calculate_post_measurement_state(
        self,
        amplitudes: List[Complex],
        measured_index: int,
        strength: float
    ) -> List[Complex]:
        """Calculate quantum state after measurement."""
        result = [0j] * len(amplitudes)
        
        if strength == 1.0:
            # Full collapse to measured state
            result[measured_index] = 1.0
        else:
            # Partial collapse
            original_prob = abs(amplitudes[measured_index]) ** 2
            
            for i in range(len(amplitudes)):
                if i == measured_index:
                    # Enhance measured state
                    result[i] = amplitudes[i] * math.sqrt((1 + strength) / (2 * original_prob))
                else:
                    # Suppress other states
                    result[i] = amplitudes[i] * math.sqrt((1 - strength) / 2)
        
        return result
    
    def _calculate_von_neumann_entropy(self, probabilities: List[float]) -> float:
        """Calculate von Neumann entropy of quantum state."""
        entropy = 0.0
        for prob in probabilities:
            if prob > 0:
                entropy -= prob * math.log2(prob)
        
        return entropy
    
    def _propagate_measurement_to_entangled_states(
        self,
        measured_state: QuantumProbabilityState,
        measurement: QuantumMeasurement
    ) -> None:
        """Propagate measurement effects to entangled states."""
        for partner_id in measured_state.entanglement_partners:
            if partner_id in self.quantum_states:
                partner_state = self.quantum_states[partner_id]
                
                # Apply correlated collapse to entangled partner
                measured_index = measurement.measured_value
                if measured_index < len(partner_state.amplitudes):
                    # Enhance corresponding amplitude in partner
                    enhancement_factor = math.sqrt(measurement.probability * 2)
                    partner_state.amplitudes[measured_index] *= enhancement_factor
                    
                    # Renormalize
                    total_prob = sum(abs(amp)**2 for amp in partner_state.amplitudes)
                    if total_prob > 0:
                        norm_factor = 1.0 / math.sqrt(total_prob)
                        partner_state.amplitudes = [amp * norm_factor for amp in partner_state.amplitudes]
    
    def _transform_to_diagonal_basis(self, probabilities: List[float]) -> List[float]:
        """Transform probabilities to diagonal measurement basis."""
        # Simple transformation for demonstration
        if len(probabilities) >= 2:
            p0, p1 = probabilities[0], probabilities[1]
            diag_p0 = (p0 + p1) / 2  # |+⟩ state
            diag_p1 = abs(p0 - p1) / 2  # |-⟩ state
            result = [diag_p0, diag_p1] + probabilities[2:]
            return result
        
        return probabilities
    
    def _transform_to_circular_basis(self, probabilities: List[float]) -> List[float]:
        """Transform probabilities to circular measurement basis."""
        # Simple transformation for demonstration
        return probabilities  # Placeholder
    
    # Quantum gate implementations
    
    def _pauli_x_gate(self, amplitudes: List[Complex]) -> List[Complex]:
        """Apply Pauli-X (NOT) gate."""
        if len(amplitudes) >= 2:
            return [amplitudes[1], amplitudes[0]] + amplitudes[2:]
        return amplitudes
    
    def _pauli_y_gate(self, amplitudes: List[Complex]) -> List[Complex]:
        """Apply Pauli-Y gate."""
        if len(amplitudes) >= 2:
            return [-1j * amplitudes[1], 1j * amplitudes[0]] + amplitudes[2:]
        return amplitudes
    
    def _pauli_z_gate(self, amplitudes: List[Complex]) -> List[Complex]:
        """Apply Pauli-Z gate."""
        if len(amplitudes) >= 2:
            return [amplitudes[0], -amplitudes[1]] + amplitudes[2:]
        return amplitudes
    
    def _hadamard_gate(self, amplitudes: List[Complex]) -> List[Complex]:
        """Apply Hadamard gate."""
        if len(amplitudes) >= 2:
            sqrt2 = math.sqrt(2)
            a0, a1 = amplitudes[0], amplitudes[1]
            new_a0 = (a0 + a1) / sqrt2
            new_a1 = (a0 - a1) / sqrt2
            return [new_a0, new_a1] + amplitudes[2:]
        return amplitudes
    
    def _phase_gate(self, amplitudes: List[Complex]) -> List[Complex]:
        """Apply S (phase) gate."""
        if len(amplitudes) >= 2:
            return [amplitudes[0], 1j * amplitudes[1]] + amplitudes[2:]
        return amplitudes
    
    def _t_gate(self, amplitudes: List[Complex]) -> List[Complex]:
        """Apply T gate."""
        if len(amplitudes) >= 2:
            return [amplitudes[0], cmath.exp(1j * math.pi / 4) * amplitudes[1]] + amplitudes[2:]
        return amplitudes
    
    def _rotation_x_gate(self, amplitudes: List[Complex], parameters: List[float]) -> List[Complex]:
        """Apply rotation around X axis."""
        if len(amplitudes) >= 2 and parameters:
            theta = parameters[0]
            cos_half = math.cos(theta / 2)
            sin_half = math.sin(theta / 2)
            
            a0, a1 = amplitudes[0], amplitudes[1]
            new_a0 = cos_half * a0 - 1j * sin_half * a1
            new_a1 = -1j * sin_half * a0 + cos_half * a1
            
            return [new_a0, new_a1] + amplitudes[2:]
        return amplitudes
    
    def _rotation_y_gate(self, amplitudes: List[Complex], parameters: List[float]) -> List[Complex]:
        """Apply rotation around Y axis."""
        if len(amplitudes) >= 2 and parameters:
            theta = parameters[0]
            cos_half = math.cos(theta / 2)
            sin_half = math.sin(theta / 2)
            
            a0, a1 = amplitudes[0], amplitudes[1]
            new_a0 = cos_half * a0 - sin_half * a1
            new_a1 = sin_half * a0 + cos_half * a1
            
            return [new_a0, new_a1] + amplitudes[2:]
        return amplitudes
    
    def _rotation_z_gate(self, amplitudes: List[Complex], parameters: List[float]) -> List[Complex]:
        """Apply rotation around Z axis."""
        if len(amplitudes) >= 2 and parameters:
            theta = parameters[0]
            
            a0, a1 = amplitudes[0], amplitudes[1]
            new_a0 = cmath.exp(-1j * theta / 2) * a0
            new_a1 = cmath.exp(1j * theta / 2) * a1
            
            return [new_a0, new_a1] + amplitudes[2:]
        return amplitudes