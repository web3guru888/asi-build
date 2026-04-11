"""
Probability Wave Calculator
==========================

Calculates and manages probability waves for multiverse navigation,
quantum state propagation, and inter-dimensional probability mapping.
"""

import numpy as np
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import cmath
from scipy.fft import fft, ifft, fftfreq
from scipy.interpolate import interp1d
import math

from ..core.base_multiverse import MultiverseComponent
from ..core.quantum_state import QuantumState
from ..core.config_manager import get_global_config


class WaveType(Enum):
    """Types of probability waves."""
    PLANAR = "planar"
    SPHERICAL = "spherical"
    CYLINDRICAL = "cylindrical"
    GAUSSIAN = "gaussian"
    SOLITON = "soliton"
    SUPERPOSITION = "superposition"
    ENTANGLED = "entangled"
    TRAVELLING = "travelling"


@dataclass
class ProbabilityWave:
    """Represents a probability wave in the multiverse."""
    wave_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    wave_type: WaveType = WaveType.GAUSSIAN
    amplitude: complex = 1.0 + 0j
    frequency: float = 1.0
    wavelength: float = 1.0
    phase: float = 0.0
    position: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    velocity: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    width: float = 1.0
    decay_rate: float = 0.0
    creation_time: float = field(default_factory=time.time)
    universe_id: Optional[str] = None
    quantum_state: Optional[QuantumState] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize wave parameters."""
        if isinstance(self.position, list):
            self.position = np.array(self.position)
        if isinstance(self.velocity, list):
            self.velocity = np.array(self.velocity)
        
        # Ensure position and velocity are 3D
        if self.position.size == 0:
            self.position = np.array([0.0, 0.0, 0.0])
        elif self.position.size < 3:
            self.position = np.pad(self.position, (0, 3 - self.position.size))
        
        if self.velocity.size == 0:
            self.velocity = np.array([0.0, 0.0, 0.0])
        elif self.velocity.size < 3:
            self.velocity = np.pad(self.velocity, (0, 3 - self.velocity.size))
    
    def evaluate_at_point(self, point: np.ndarray, current_time: float) -> complex:
        """Evaluate the probability wave at a specific point and time."""
        point = np.array(point)
        if point.size < 3:
            point = np.pad(point, (0, 3 - point.size))
        
        # Time evolution
        time_elapsed = current_time - self.creation_time
        current_position = self.position + self.velocity * time_elapsed
        
        # Distance from wave center
        distance = np.linalg.norm(point - current_position)
        
        # Calculate wave value based on type
        if self.wave_type == WaveType.GAUSSIAN:
            return self._gaussian_wave(distance, time_elapsed)
        elif self.wave_type == WaveType.PLANAR:
            return self._planar_wave(point, current_position, time_elapsed)
        elif self.wave_type == WaveType.SPHERICAL:
            return self._spherical_wave(distance, time_elapsed)
        elif self.wave_type == WaveType.SOLITON:
            return self._soliton_wave(distance, time_elapsed)
        else:
            return self._default_wave(distance, time_elapsed)
    
    def _gaussian_wave(self, distance: float, time_elapsed: float) -> complex:
        """Calculate Gaussian wave packet."""
        # Gaussian envelope
        envelope = math.exp(-0.5 * (distance / self.width)**2)
        
        # Oscillatory part
        phase_total = self.phase + 2 * math.pi * self.frequency * time_elapsed
        oscillation = cmath.exp(1j * phase_total)
        
        # Decay
        decay = math.exp(-self.decay_rate * time_elapsed)
        
        return self.amplitude * envelope * oscillation * decay
    
    def _planar_wave(self, point: np.ndarray, center: np.ndarray, time_elapsed: float) -> complex:
        """Calculate planar wave."""
        # Wave propagation direction (normalized velocity)
        if np.linalg.norm(self.velocity) > 0:
            direction = self.velocity / np.linalg.norm(self.velocity)
        else:
            direction = np.array([1.0, 0.0, 0.0])
        
        # Dot product for planar wave
        k_dot_r = 2 * math.pi / self.wavelength * np.dot(direction, point - center)
        phase_total = self.phase + k_dot_r + 2 * math.pi * self.frequency * time_elapsed
        
        decay = math.exp(-self.decay_rate * time_elapsed)
        
        return self.amplitude * cmath.exp(1j * phase_total) * decay
    
    def _spherical_wave(self, distance: float, time_elapsed: float) -> complex:
        """Calculate spherical wave."""
        if distance < 1e-10:
            distance = 1e-10  # Avoid division by zero
        
        # Spherical wave amplitude (1/r dependence)
        amplitude_factor = 1.0 / distance
        
        # Phase
        k = 2 * math.pi / self.wavelength
        phase_total = self.phase + k * distance + 2 * math.pi * self.frequency * time_elapsed
        
        # Decay
        decay = math.exp(-self.decay_rate * time_elapsed)
        
        return self.amplitude * amplitude_factor * cmath.exp(1j * phase_total) * decay
    
    def _soliton_wave(self, distance: float, time_elapsed: float) -> complex:
        """Calculate soliton wave (non-dispersive)."""
        # Soliton profile: sech function
        shifted_distance = distance - np.linalg.norm(self.velocity) * time_elapsed
        soliton_profile = 1.0 / math.cosh(shifted_distance / self.width)
        
        # Phase
        phase_total = self.phase + 2 * math.pi * self.frequency * time_elapsed
        
        # Decay
        decay = math.exp(-self.decay_rate * time_elapsed)
        
        return self.amplitude * soliton_profile * cmath.exp(1j * phase_total) * decay
    
    def _default_wave(self, distance: float, time_elapsed: float) -> complex:
        """Default wave calculation (exponentially decaying oscillation)."""
        spatial_decay = math.exp(-distance / self.width)
        temporal_decay = math.exp(-self.decay_rate * time_elapsed)
        phase_total = self.phase + 2 * math.pi * self.frequency * time_elapsed
        
        return self.amplitude * spatial_decay * temporal_decay * cmath.exp(1j * phase_total)
    
    def get_probability_density(self, point: np.ndarray, current_time: float) -> float:
        """Get probability density at a point."""
        wave_value = self.evaluate_at_point(point, current_time)
        return abs(wave_value)**2
    
    def integrate_over_region(self, bounds: List[Tuple[float, float]], 
                            current_time: float, resolution: int = 50) -> float:
        """Integrate probability density over a region."""
        if len(bounds) != 3:
            raise ValueError("Bounds must be 3D: [(x_min, x_max), (y_min, y_max), (z_min, z_max)]")
        
        total_probability = 0.0
        volume_element = 1.0
        
        # Calculate volume element
        for x_min, x_max in bounds:
            volume_element *= (x_max - x_min) / resolution
        
        # Integrate using Monte Carlo sampling
        for _ in range(resolution**3):
            point = np.array([
                np.random.uniform(bounds[0][0], bounds[0][1]),
                np.random.uniform(bounds[1][0], bounds[1][1]),
                np.random.uniform(bounds[2][0], bounds[2][1])
            ])
            
            probability_density = self.get_probability_density(point, current_time)
            total_probability += probability_density
        
        return total_probability * volume_element


class ProbabilityWaveCalculator(MultiverseComponent):
    """
    Calculator for probability waves in the multiverse framework.
    
    Manages wave propagation, interference, superposition, and provides
    navigation assistance through probability landscape analysis.
    """
    
    def __init__(self, multiverse_manager=None):
        """Initialize the probability wave calculator."""
        super().__init__("ProbabilityWaveCalculator")
        
        self.multiverse_manager = multiverse_manager
        self.config = get_global_config()
        
        # Wave management
        self.active_waves: Dict[str, ProbabilityWave] = {}
        self.wave_history: List[ProbabilityWave] = []
        self.wave_lock = threading.RLock()
        
        # Calculation parameters
        self.calculation_precision = 1e-6
        self.max_wave_age = 3600.0  # 1 hour
        self.interference_threshold = 0.1
        self.superposition_limit = 100  # Max waves in superposition
        
        # Grid for wave field calculations
        self.grid_resolution = 64
        self.grid_bounds = [(-10.0, 10.0), (-10.0, 10.0), (-10.0, 10.0)]
        self.wave_field_cache: Dict[str, np.ndarray] = {}
        self.cache_timeout = 60.0  # 1 minute
        
        # Statistics
        self.total_waves_created = 0
        self.total_calculations_performed = 0
        self.interference_events = 0
        
        self.logger.info("ProbabilityWaveCalculator initialized")
    
    def on_start(self):
        """Start the probability wave calculator."""
        self.logger.info("Probability wave calculator started")
        self.update_property("status", "calculating")
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def on_stop(self):
        """Stop the probability wave calculator."""
        self.logger.info("Probability wave calculator stopped")
        self.update_property("status", "stopped")
    
    def _start_cleanup_thread(self):
        """Start wave cleanup thread."""
        def cleanup_waves():
            while self.is_running:
                try:
                    self._cleanup_old_waves()
                    self._cleanup_cache()
                    time.sleep(60.0)  # Clean up every minute
                except Exception as e:
                    self.logger.error("Error in wave cleanup: %s", e)
                    time.sleep(10.0)
        
        cleanup_thread = threading.Thread(
            target=cleanup_waves,
            daemon=True,
            name="WaveCleanup"
        )
        cleanup_thread.start()
    
    def create_probability_wave(self, 
                              wave_type: WaveType = WaveType.GAUSSIAN,
                              amplitude: complex = 1.0 + 0j,
                              frequency: float = 1.0,
                              position: List[float] = None,
                              velocity: List[float] = None,
                              universe_id: Optional[str] = None,
                              **kwargs) -> str:
        """
        Create a new probability wave.
        
        Args:
            wave_type: Type of wave to create
            amplitude: Wave amplitude
            frequency: Wave frequency
            position: Initial position [x, y, z]
            velocity: Wave velocity [vx, vy, vz]
            universe_id: Associated universe ID
            **kwargs: Additional wave parameters
            
        Returns:
            Wave ID
        """
        with self.wave_lock:
            wave = ProbabilityWave(
                wave_type=wave_type,
                amplitude=amplitude,
                frequency=frequency,
                position=np.array(position or [0.0, 0.0, 0.0]),
                velocity=np.array(velocity or [0.0, 0.0, 0.0]),
                universe_id=universe_id
            )
            
            # Apply additional parameters
            for key, value in kwargs.items():
                if hasattr(wave, key):
                    setattr(wave, key, value)
            
            # Store wave
            self.active_waves[wave.wave_id] = wave
            self.wave_history.append(wave)
            self.total_waves_created += 1
            
            self.emit_event("probability_wave_created", {
                'wave_id': wave.wave_id,
                'wave_type': wave_type.value,
                'universe_id': universe_id
            })
            
            self.logger.info("Probability wave created: %s (%s)", 
                           wave.wave_id, wave_type.value)
            
            return wave.wave_id
    
    def create_wave_from_quantum_state(self, quantum_state: QuantumState,
                                     position: List[float] = None,
                                     universe_id: Optional[str] = None) -> str:
        """
        Create a probability wave from a quantum state.
        
        Args:
            quantum_state: Quantum state to convert
            position: Wave position
            universe_id: Associated universe ID
            
        Returns:
            Wave ID
        """
        # Extract parameters from quantum state
        state_vector = quantum_state.state_vector
        if state_vector is not None:
            # Use first component for amplitude
            amplitude = complex(state_vector[0])
            
            # Use state entropy for frequency
            entropy = quantum_state.calculate_von_neumann_entropy()
            frequency = max(0.1, entropy)  # Minimum frequency
            
            # Use purity for wave width
            purity = quantum_state.calculate_purity()
            width = 1.0 / max(0.1, purity)  # Inverse relationship
        else:
            amplitude = 1.0 + 0j
            frequency = 1.0
            width = 1.0
        
        return self.create_probability_wave(
            wave_type=WaveType.GAUSSIAN,
            amplitude=amplitude,
            frequency=frequency,
            position=position,
            width=width,
            universe_id=universe_id,
            quantum_state=quantum_state
        )
    
    def calculate_wave_superposition(self, wave_ids: List[str], 
                                   evaluation_point: List[float],
                                   current_time: Optional[float] = None) -> complex:
        """
        Calculate superposition of multiple waves at a point.
        
        Args:
            wave_ids: List of wave IDs to superpose
            evaluation_point: Point to evaluate [x, y, z]
            current_time: Time for evaluation (defaults to current time)
            
        Returns:
            Complex amplitude of superposition
        """
        if current_time is None:
            current_time = time.time()
        
        point = np.array(evaluation_point)
        total_amplitude = 0j
        
        with self.wave_lock:
            for wave_id in wave_ids:
                wave = self.active_waves.get(wave_id)
                if wave:
                    amplitude = wave.evaluate_at_point(point, current_time)
                    total_amplitude += amplitude
        
        self.total_calculations_performed += 1
        return total_amplitude
    
    def calculate_interference_pattern(self, wave_id1: str, wave_id2: str,
                                     grid_bounds: Optional[List[Tuple[float, float]]] = None,
                                     resolution: int = 64) -> np.ndarray:
        """
        Calculate interference pattern between two waves.
        
        Args:
            wave_id1: First wave ID
            wave_id2: Second wave ID
            grid_bounds: Bounds for calculation grid
            resolution: Grid resolution
            
        Returns:
            3D array of interference pattern
        """
        bounds = grid_bounds or self.grid_bounds
        current_time = time.time()
        
        with self.wave_lock:
            wave1 = self.active_waves.get(wave_id1)
            wave2 = self.active_waves.get(wave_id2)
            
            if not wave1 or not wave2:
                raise ValueError("One or both waves not found")
            
            # Create calculation grid
            x_range = np.linspace(bounds[0][0], bounds[0][1], resolution)
            y_range = np.linspace(bounds[1][0], bounds[1][1], resolution)
            z_range = np.linspace(bounds[2][0], bounds[2][1], resolution)
            
            interference = np.zeros((resolution, resolution, resolution), dtype=complex)
            
            for i, x in enumerate(x_range):
                for j, y in enumerate(y_range):
                    for k, z in enumerate(z_range):
                        point = np.array([x, y, z])
                        
                        amp1 = wave1.evaluate_at_point(point, current_time)
                        amp2 = wave2.evaluate_at_point(point, current_time)
                        
                        interference[i, j, k] = amp1 + amp2
            
            self.interference_events += 1
            self.total_calculations_performed += resolution**3
            
            return interference
    
    def find_probability_maxima(self, wave_ids: List[str],
                              search_bounds: List[Tuple[float, float]],
                              current_time: Optional[float] = None,
                              threshold: float = 0.5) -> List[Tuple[np.ndarray, float]]:
        """
        Find local maxima in probability density for navigation.
        
        Args:
            wave_ids: Wave IDs to analyze
            search_bounds: Bounds for search
            current_time: Time for evaluation
            threshold: Minimum probability threshold
            
        Returns:
            List of (position, probability) tuples for maxima
        """
        if current_time is None:
            current_time = time.time()
        
        maxima = []
        resolution = 32  # Coarse search
        
        # Create search grid
        x_range = np.linspace(search_bounds[0][0], search_bounds[0][1], resolution)
        y_range = np.linspace(search_bounds[1][0], search_bounds[1][1], resolution)
        z_range = np.linspace(search_bounds[2][0], search_bounds[2][1], resolution)
        
        # Sample probability field
        for x in x_range:
            for y in y_range:
                for z in z_range:
                    point = np.array([x, y, z])
                    
                    # Calculate superposition amplitude
                    total_amplitude = self.calculate_wave_superposition(
                        wave_ids, point.tolist(), current_time
                    )
                    probability = abs(total_amplitude)**2
                    
                    if probability > threshold:
                        # Check if this is a local maximum
                        is_maximum = True
                        for dx in [-0.5, 0.5]:
                            for dy in [-0.5, 0.5]:
                                for dz in [-0.5, 0.5]:
                                    if dx == 0 and dy == 0 and dz == 0:
                                        continue
                                    
                                    neighbor_point = point + np.array([dx, dy, dz])
                                    neighbor_amplitude = self.calculate_wave_superposition(
                                        wave_ids, neighbor_point.tolist(), current_time
                                    )
                                    neighbor_probability = abs(neighbor_amplitude)**2
                                    
                                    if neighbor_probability > probability:
                                        is_maximum = False
                                        break
                                
                                if not is_maximum:
                                    break
                            if not is_maximum:
                                break
                        
                        if is_maximum:
                            maxima.append((point.copy(), probability))
        
        # Sort by probability (highest first)
        maxima.sort(key=lambda x: x[1], reverse=True)
        
        return maxima
    
    def calculate_probability_gradient(self, wave_ids: List[str],
                                     position: List[float],
                                     current_time: Optional[float] = None,
                                     step_size: float = 0.01) -> np.ndarray:
        """
        Calculate probability gradient for navigation direction.
        
        Args:
            wave_ids: Wave IDs to analyze
            position: Current position
            current_time: Time for evaluation
            step_size: Step size for gradient calculation
            
        Returns:
            Gradient vector [dx, dy, dz]
        """
        if current_time is None:
            current_time = time.time()
        
        point = np.array(position)
        gradient = np.zeros(3)
        
        # Calculate central probability
        center_amplitude = self.calculate_wave_superposition(
            wave_ids, point.tolist(), current_time
        )
        center_probability = abs(center_amplitude)**2
        
        # Calculate gradient components
        for i in range(3):
            # Forward step
            forward_point = point.copy()
            forward_point[i] += step_size
            forward_amplitude = self.calculate_wave_superposition(
                wave_ids, forward_point.tolist(), current_time
            )
            forward_probability = abs(forward_amplitude)**2
            
            # Backward step
            backward_point = point.copy()
            backward_point[i] -= step_size
            backward_amplitude = self.calculate_wave_superposition(
                wave_ids, backward_point.tolist(), current_time
            )
            backward_probability = abs(backward_amplitude)**2
            
            # Central difference
            gradient[i] = (forward_probability - backward_probability) / (2 * step_size)
        
        return gradient
    
    def create_wave_packet(self, center_position: List[float],
                          target_position: List[float],
                          universe_id: Optional[str] = None,
                          packet_width: float = 1.0) -> str:
        """
        Create a wave packet for directed navigation.
        
        Args:
            center_position: Starting position
            target_position: Target position
            universe_id: Associated universe ID
            packet_width: Width of wave packet
            
        Returns:
            Wave ID
        """
        center = np.array(center_position)
        target = np.array(target_position)
        
        # Calculate velocity towards target
        direction = target - center
        distance = np.linalg.norm(direction)
        
        if distance > 0:
            velocity = direction / distance * 1.0  # Unit velocity
        else:
            velocity = np.array([0.0, 0.0, 0.0])
        
        # Create wave packet
        return self.create_probability_wave(
            wave_type=WaveType.GAUSSIAN,
            amplitude=1.0 + 0j,
            frequency=1.0,
            position=center_position,
            velocity=velocity.tolist(),
            width=packet_width,
            universe_id=universe_id,
            metadata={
                'navigation_type': 'directed_packet',
                'target_position': target_position,
                'travel_distance': distance
            }
        )
    
    def propagate_waves(self, time_step: float):
        """
        Propagate all active waves forward in time.
        
        Args:
            time_step: Time step for propagation
        """
        with self.wave_lock:
            for wave in self.active_waves.values():
                # Update position
                wave.position += wave.velocity * time_step
                
                # Apply decay
                if wave.decay_rate > 0:
                    wave.amplitude *= math.exp(-wave.decay_rate * time_step)
                
                # Update phase
                wave.phase += 2 * math.pi * wave.frequency * time_step
        
        # Clear cache since waves have moved
        self.wave_field_cache.clear()
    
    def _cleanup_old_waves(self):
        """Clean up old and weak waves."""
        current_time = time.time()
        
        with self.wave_lock:
            waves_to_remove = []
            
            for wave_id, wave in self.active_waves.items():
                # Remove old waves
                if current_time - wave.creation_time > self.max_wave_age:
                    waves_to_remove.append(wave_id)
                # Remove very weak waves
                elif abs(wave.amplitude) < 1e-6:
                    waves_to_remove.append(wave_id)
            
            for wave_id in waves_to_remove:
                del self.active_waves[wave_id]
            
            if waves_to_remove:
                self.logger.debug("Cleaned up %d old waves", len(waves_to_remove))
    
    def _cleanup_cache(self):
        """Clean up cached calculations."""
        # Simple time-based cache cleanup
        self.wave_field_cache.clear()
    
    def get_wave_statistics(self) -> Dict[str, Any]:
        """Get probability wave statistics."""
        with self.wave_lock:
            wave_types = {}
            total_amplitude = 0.0
            
            for wave in self.active_waves.values():
                wave_type = wave.wave_type.value
                wave_types[wave_type] = wave_types.get(wave_type, 0) + 1
                total_amplitude += abs(wave.amplitude)
            
            return {
                'active_waves': len(self.active_waves),
                'total_waves_created': self.total_waves_created,
                'wave_types': wave_types,
                'total_amplitude': total_amplitude,
                'calculations_performed': self.total_calculations_performed,
                'interference_events': self.interference_events,
                'cache_entries': len(self.wave_field_cache)
            }
    
    def on_health_check(self) -> Optional[Dict[str, Any]]:
        """Health check for probability wave calculator."""
        return {
            'active_waves': len(self.active_waves),
            'calculations_performed': self.total_calculations_performed,
            'cache_size': len(self.wave_field_cache),
            'calculator_active': self.is_running
        }