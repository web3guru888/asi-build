"""
Chaos Amplifier

System for amplifying small probability changes into large-scale effects
using chaos theory principles, strange attractors, and nonlinear dynamics.
"""

import numpy as np
import logging
import math
import time
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import threading


class ChaosSystem(Enum):
    """Types of chaotic systems for amplification."""
    LORENZ = "lorenz"
    ROSSLER = "rossler"
    HENON = "henon"
    LOGISTIC = "logistic"
    DOUBLE_PENDULUM = "double_pendulum"
    BUTTERFLY = "butterfly"


@dataclass
class ChaosState:
    """State of a chaotic system."""
    system_id: str
    system_type: ChaosSystem
    state_vector: np.ndarray
    parameters: Dict[str, float]
    sensitivity: float
    time_step: float
    iteration_count: int
    last_update: float


class ChaosAmplifier:
    """
    Chaos theory probability amplification system.
    
    Uses chaotic systems to amplify tiny probability changes into
    large-scale effects through sensitive dependence on initial conditions.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Core state
        self.chaos_systems: Dict[str, ChaosState] = {}
        self.amplification_history: List[Dict[str, Any]] = []
        
        # Threading
        self.chaos_lock = threading.RLock()
        
        # System parameters
        self.max_amplification_factor = 1000000.0
        self.chaos_evolution_timestep = 0.01
        self.sensitivity_threshold = 1e-15
        
        self.logger.info("ChaosAmplifier initialized")
    
    def create_chaos_system(
        self,
        system_type: ChaosSystem,
        initial_conditions: Optional[np.ndarray] = None,
        parameters: Optional[Dict[str, float]] = None
    ) -> str:
        """Create a new chaotic system for amplification."""
        system_id = f"chaos_{system_type.value}_{int(time.time() * 1000000)}"
        
        # Set default initial conditions and parameters
        if system_type == ChaosSystem.LORENZ:
            if initial_conditions is None:
                initial_conditions = np.array([1.0, 1.0, 1.0])
            if parameters is None:
                parameters = {'sigma': 10.0, 'rho': 28.0, 'beta': 8.0/3.0}
                
        elif system_type == ChaosSystem.ROSSLER:
            if initial_conditions is None:
                initial_conditions = np.array([1.0, 1.0, 1.0])
            if parameters is None:
                parameters = {'a': 0.2, 'b': 0.2, 'c': 5.7}
                
        elif system_type == ChaosSystem.HENON:
            if initial_conditions is None:
                initial_conditions = np.array([0.1, 0.1])
            if parameters is None:
                parameters = {'a': 1.4, 'b': 0.3}
                
        elif system_type == ChaosSystem.LOGISTIC:
            if initial_conditions is None:
                initial_conditions = np.array([0.5])
            if parameters is None:
                parameters = {'r': 3.9}
                
        # Calculate sensitivity
        sensitivity = self._calculate_system_sensitivity(system_type, parameters)
        
        chaos_state = ChaosState(
            system_id=system_id,
            system_type=system_type,
            state_vector=initial_conditions.copy(),
            parameters=parameters,
            sensitivity=sensitivity,
            time_step=self.chaos_evolution_timestep,
            iteration_count=0,
            last_update=time.time()
        )
        
        self.chaos_systems[system_id] = chaos_state
        
        self.logger.info(f"Created {system_type.value} chaos system {system_id}")
        return system_id
    
    def amplify_probability_change(
        self,
        system_id: str,
        initial_perturbation: float,
        target_amplification: float,
        evolution_time: float = 10.0
    ) -> Dict[str, Any]:
        """Amplify a small probability change using chaotic dynamics."""
        if system_id not in self.chaos_systems:
            raise ValueError(f"Chaos system {system_id} not found")
        
        chaos_state = self.chaos_systems[system_id]
        amplification_id = f"amp_{system_id}_{int(time.time() * 1000000)}"
        
        # Apply initial perturbation
        perturbed_state = chaos_state.state_vector.copy()
        perturbation_vector = self._generate_perturbation_vector(
            chaos_state, initial_perturbation
        )
        perturbed_state += perturbation_vector
        
        # Evolve both original and perturbed systems
        original_trajectory = self._evolve_system(chaos_state, evolution_time)
        perturbed_trajectory = self._evolve_perturbed_system(
            chaos_state, perturbed_state, evolution_time
        )
        
        # Calculate amplification achieved
        final_divergence = np.linalg.norm(
            original_trajectory[-1] - perturbed_trajectory[-1]
        )
        
        amplification_factor = final_divergence / initial_perturbation
        amplification_factor = min(amplification_factor, self.max_amplification_factor)
        
        # Calculate butterfly effect strength
        butterfly_strength = self._calculate_butterfly_strength(
            original_trajectory, perturbed_trajectory
        )
        
        result = {
            'amplification_id': amplification_id,
            'system_id': system_id,
            'system_type': chaos_state.system_type.value,
            'initial_perturbation': initial_perturbation,
            'target_amplification': target_amplification,
            'achieved_amplification': amplification_factor,
            'butterfly_strength': butterfly_strength,
            'evolution_time': evolution_time,
            'final_divergence': final_divergence,
            'lyapunov_exponent': self._calculate_lyapunov_exponent(original_trajectory),
            'sensitivity_measure': chaos_state.sensitivity,
            'success': amplification_factor >= target_amplification * 0.8,
            'timestamp': time.time()
        }
        
        self.amplification_history.append(result)
        
        # Update chaos system state
        chaos_state.state_vector = original_trajectory[-1]
        chaos_state.iteration_count += len(original_trajectory)
        chaos_state.last_update = time.time()
        
        self.logger.info(
            f"Amplified perturbation by factor {amplification_factor:.2e} "
            f"using {chaos_state.system_type.value} system"
        )
        
        return result
    
    def create_butterfly_effect(
        self,
        source_location: Tuple[float, float, float],
        target_location: Tuple[float, float, float],
        effect_magnitude: float,
        propagation_time: float = 86400.0
    ) -> str:
        """Create a butterfly effect from source to target location."""
        effect_id = f"butterfly_{int(time.time() * 1000000)}"
        
        # Calculate distance and required amplification
        distance = math.sqrt(sum((t - s)**2 for s, t in zip(source_location, target_location)))
        required_amplification = distance * effect_magnitude * 1000
        
        # Create optimal chaos system for this effect
        system_id = self.create_chaos_system(ChaosSystem.BUTTERFLY)
        
        # Calculate initial perturbation needed
        initial_perturbation = effect_magnitude / required_amplification
        initial_perturbation = max(self.sensitivity_threshold, initial_perturbation)
        
        # Execute amplification
        amplification_result = self.amplify_probability_change(
            system_id=system_id,
            initial_perturbation=initial_perturbation,
            target_amplification=required_amplification,
            evolution_time=propagation_time / 86400 * 10  # Scale time
        )
        
        butterfly_effect = {
            'effect_id': effect_id,
            'source_location': source_location,
            'target_location': target_location,
            'distance': distance,
            'effect_magnitude': effect_magnitude,
            'propagation_time': propagation_time,
            'chaos_system_id': system_id,
            'amplification_result': amplification_result,
            'creation_time': time.time()
        }
        
        self.logger.info(f"Created butterfly effect {effect_id}")
        return effect_id
    
    def _generate_perturbation_vector(
        self,
        chaos_state: ChaosState,
        magnitude: float
    ) -> np.ndarray:
        """Generate a perturbation vector for the chaos system."""
        # Generate random direction
        direction = np.random.randn(len(chaos_state.state_vector))
        direction = direction / np.linalg.norm(direction)
        
        # Scale by magnitude
        return direction * magnitude
    
    def _evolve_system(self, chaos_state: ChaosState, evolution_time: float) -> np.ndarray:
        """Evolve the chaotic system forward in time."""
        num_steps = int(evolution_time / chaos_state.time_step)
        trajectory = np.zeros((num_steps, len(chaos_state.state_vector)))
        
        current_state = chaos_state.state_vector.copy()
        
        for i in range(num_steps):
            current_state = self._step_system(chaos_state, current_state)
            trajectory[i] = current_state
        
        return trajectory
    
    def _evolve_perturbed_system(
        self,
        chaos_state: ChaosState,
        initial_state: np.ndarray,
        evolution_time: float
    ) -> np.ndarray:
        """Evolve a perturbed version of the chaotic system."""
        num_steps = int(evolution_time / chaos_state.time_step)
        trajectory = np.zeros((num_steps, len(initial_state)))
        
        current_state = initial_state.copy()
        
        for i in range(num_steps):
            current_state = self._step_system(chaos_state, current_state)
            trajectory[i] = current_state
        
        return trajectory
    
    def _step_system(self, chaos_state: ChaosState, state: np.ndarray) -> np.ndarray:
        """Perform one integration step of the chaotic system."""
        if chaos_state.system_type == ChaosSystem.LORENZ:
            return self._step_lorenz(state, chaos_state.parameters, chaos_state.time_step)
        elif chaos_state.system_type == ChaosSystem.ROSSLER:
            return self._step_rossler(state, chaos_state.parameters, chaos_state.time_step)
        elif chaos_state.system_type == ChaosSystem.HENON:
            return self._step_henon(state, chaos_state.parameters)
        elif chaos_state.system_type == ChaosSystem.LOGISTIC:
            return self._step_logistic(state, chaos_state.parameters)
        else:
            # Default: simple chaotic map
            return state * 2.0 % 1.0
    
    def _step_lorenz(self, state: np.ndarray, params: Dict[str, float], dt: float) -> np.ndarray:
        """Step the Lorenz system."""
        x, y, z = state
        sigma, rho, beta = params['sigma'], params['rho'], params['beta']
        
        dx = sigma * (y - x)
        dy = x * (rho - z) - y
        dz = x * y - beta * z
        
        return state + dt * np.array([dx, dy, dz])
    
    def _step_rossler(self, state: np.ndarray, params: Dict[str, float], dt: float) -> np.ndarray:
        """Step the Rössler system."""
        x, y, z = state
        a, b, c = params['a'], params['b'], params['c']
        
        dx = -y - z
        dy = x + a * y
        dz = b + z * (x - c)
        
        return state + dt * np.array([dx, dy, dz])
    
    def _step_henon(self, state: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """Step the Hénon map."""
        x, y = state
        a, b = params['a'], params['b']
        
        x_new = 1 - a * x**2 + y
        y_new = b * x
        
        return np.array([x_new, y_new])
    
    def _step_logistic(self, state: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """Step the logistic map."""
        x = state[0]
        r = params['r']
        
        x_new = r * x * (1 - x)
        return np.array([x_new])
    
    def _calculate_system_sensitivity(
        self,
        system_type: ChaosSystem,
        parameters: Dict[str, float]
    ) -> float:
        """Calculate the sensitivity of the chaotic system."""
        # Estimates based on known Lyapunov exponents
        sensitivity_estimates = {
            ChaosSystem.LORENZ: 0.9,
            ChaosSystem.ROSSLER: 0.1,
            ChaosSystem.HENON: 0.4,
            ChaosSystem.LOGISTIC: 0.7,
            ChaosSystem.DOUBLE_PENDULUM: 1.5,
            ChaosSystem.BUTTERFLY: 2.0
        }
        
        return sensitivity_estimates.get(system_type, 1.0)
    
    def _calculate_butterfly_strength(
        self,
        original_trajectory: np.ndarray,
        perturbed_trajectory: np.ndarray
    ) -> float:
        """Calculate the strength of the butterfly effect."""
        if len(original_trajectory) != len(perturbed_trajectory):
            return 0.0
        
        # Calculate divergence over time
        divergences = [
            np.linalg.norm(orig - pert)
            for orig, pert in zip(original_trajectory, perturbed_trajectory)
        ]
        
        # Look for exponential growth
        if len(divergences) > 10:
            # Fit exponential to last part of trajectory
            time_indices = np.arange(len(divergences)//2, len(divergences))
            log_divergences = np.log(np.array(divergences[len(divergences)//2:]) + 1e-10)
            
            # Linear fit to log data gives exponential growth rate
            coeffs = np.polyfit(time_indices, log_divergences, 1)
            exponential_growth_rate = coeffs[0]
            
            return max(0.0, exponential_growth_rate)
        
        return 0.0
    
    def _calculate_lyapunov_exponent(self, trajectory: np.ndarray) -> float:
        """Calculate the largest Lyapunov exponent."""
        if len(trajectory) < 100:
            return 0.0
        
        # Simple estimate using trajectory divergence
        # This is a simplified calculation
        divergences = []
        
        for i in range(1, len(trajectory)):
            diff = np.linalg.norm(trajectory[i] - trajectory[i-1])
            if diff > 0:
                divergences.append(diff)
        
        if divergences:
            mean_divergence = np.mean(divergences)
            return math.log(mean_divergence + 1e-10)
        
        return 0.0
    
    def get_chaos_system_status(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a chaos system."""
        if system_id not in self.chaos_systems:
            return None
        
        chaos_state = self.chaos_systems[system_id]
        
        return {
            'system_id': system_id,
            'system_type': chaos_state.system_type.value,
            'current_state': chaos_state.state_vector.tolist(),
            'parameters': chaos_state.parameters,
            'sensitivity': chaos_state.sensitivity,
            'iteration_count': chaos_state.iteration_count,
            'age': time.time() - chaos_state.last_update,
            'lyapunov_estimate': self._calculate_lyapunov_exponent(
                chaos_state.state_vector.reshape(1, -1)
            )
        }