"""
Temporal Dynamics Manager for Neuromorphic Computing

Manages time-dependent processes in neuromorphic systems including:
- Spike timing dynamics
- Temporal pattern learning
- Neural oscillations
- Synchronization mechanisms
- Time-based memory formation
"""

import time
import numpy as np
import threading
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
from scipy import signal
from scipy.fft import fft, fftfreq

@dataclass
class TemporalPattern:
    """Represents a temporal pattern in neural activity."""
    pattern_id: str
    spike_times: List[float]
    neuron_ids: List[int]
    duration: float
    frequency: Optional[float] = None
    phase: Optional[float] = None
    strength: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OscillationState:
    """State of neural oscillations."""
    frequency: float
    amplitude: float
    phase: float
    coherence: float
    participants: List[int]  # Neuron IDs participating in oscillation
    last_update: float

class TemporalDynamics:
    """
    Manages temporal aspects of neuromorphic computation.
    
    Features:
    - Spike timing precision
    - Temporal pattern detection
    - Neural oscillation generation
    - Synchronization dynamics
    - Time-based plasticity modulation
    - Temporal memory formation
    """
    
    def __init__(self, config):
        """Initialize temporal dynamics manager."""
        self.config = config
        
        # Time management
        self.current_time = 0.0
        self.time_step = config.hardware.time_step
        self.time_precision = 1e-6  # Microsecond precision
        
        # Oscillation management
        self.oscillations = {}
        self.global_oscillation_state = OscillationState(
            frequency=40.0,  # Gamma frequency
            amplitude=1.0,
            phase=0.0,
            coherence=0.5,
            participants=[],
            last_update=0.0
        )
        
        # Temporal pattern tracking
        self.detected_patterns = {}
        self.pattern_templates = {}
        self.pattern_detection_window = 100.0e-3  # 100ms
        
        # Spike timing tracking
        self.spike_history = defaultdict(deque)
        self.spike_intervals = defaultdict(deque)
        self.burst_detection = {}
        
        # Synchronization tracking
        self.synchrony_measures = {}
        self.coherence_history = deque(maxlen=1000)
        
        # Plasticity modulation
        self.plasticity_modulation = {}
        self.temporal_learning_windows = {}
        
        # Performance monitoring
        self.processing_times = deque(maxlen=1000)
        self.pattern_counts = defaultdict(int)
        
        # Threading
        self._lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger("neuromorphic.temporal_dynamics")
        
        # Callbacks
        self.pattern_callbacks = defaultdict(list)
        self.oscillation_callbacks = []
        self.synchrony_callbacks = []
    
    def initialize(self) -> None:
        """Initialize temporal dynamics system."""
        self.logger.info("Initializing temporal dynamics")
        
        # Reset time
        self.current_time = 0.0
        
        # Initialize oscillation generators
        self._initialize_oscillations()
        
        # Setup pattern templates
        self._setup_pattern_templates()
        
        self.logger.info("Temporal dynamics initialized")
    
    def shutdown(self) -> None:
        """Shutdown temporal dynamics system."""
        self.logger.info("Shutting down temporal dynamics")
        
        # Clear data structures
        self.oscillations.clear()
        self.detected_patterns.clear()
        self.spike_history.clear()
        self.spike_intervals.clear()
        
        self.logger.info("Temporal dynamics shutdown complete")
    
    def update(self, dt: float) -> None:
        """Update temporal dynamics for one time step."""
        start_time = time.perf_counter()
        
        with self._lock:
            # Update current time
            self.current_time += dt
            
            # Update oscillations
            self._update_oscillations(dt)
            
            # Detect temporal patterns
            self._detect_temporal_patterns()
            
            # Update synchronization measures
            self._update_synchronization()
            
            # Update plasticity modulation
            self._update_plasticity_modulation(dt)
            
            # Clean old data
            self._cleanup_old_data()
        
        # Record processing time
        processing_time = time.perf_counter() - start_time
        self.processing_times.append(processing_time)
    
    def register_spike(self, neuron_id: int, spike_time: float) -> None:
        """Register a spike event for temporal analysis."""
        with self._lock:
            # Add to spike history
            self.spike_history[neuron_id].append(spike_time)
            
            # Limit history length
            max_history = int(1.0 / self.time_step)  # 1 second of history
            if len(self.spike_history[neuron_id]) > max_history:
                self.spike_history[neuron_id].popleft()
            
            # Calculate inter-spike interval
            if len(self.spike_history[neuron_id]) >= 2:
                isi = spike_time - self.spike_history[neuron_id][-2]
                self.spike_intervals[neuron_id].append(isi)
                
                # Limit ISI history
                if len(self.spike_intervals[neuron_id]) > 100:
                    self.spike_intervals[neuron_id].popleft()
            
            # Check for burst detection
            self._detect_burst(neuron_id, spike_time)
    
    def add_pattern_template(self, pattern: TemporalPattern) -> None:
        """Add a temporal pattern template for detection."""
        self.pattern_templates[pattern.pattern_id] = pattern
        self.logger.debug(f"Added pattern template: {pattern.pattern_id}")
    
    def get_oscillation_phase(self, frequency: float = None) -> float:
        """Get current phase of oscillation."""
        if frequency is None:
            frequency = self.global_oscillation_state.frequency
        
        # Calculate phase based on current time
        angular_freq = 2 * np.pi * frequency
        phase = (angular_freq * self.current_time) % (2 * np.pi)
        
        return phase
    
    def get_synchrony_measure(self, neuron_ids: List[int], 
                             time_window: float = 50.0e-3) -> float:
        """Calculate synchrony measure for a group of neurons."""
        if len(neuron_ids) < 2:
            return 0.0
        
        # Get recent spike times for each neuron
        recent_spikes = {}
        for neuron_id in neuron_ids:
            if neuron_id in self.spike_history:
                cutoff_time = self.current_time - time_window
                recent_spikes[neuron_id] = [
                    t for t in self.spike_history[neuron_id] 
                    if t >= cutoff_time
                ]
        
        # Calculate pairwise synchrony
        synchrony_values = []
        
        for i, neuron_a in enumerate(neuron_ids):
            for neuron_b in neuron_ids[i+1:]:
                if neuron_a in recent_spikes and neuron_b in recent_spikes:
                    sync = self._calculate_pairwise_synchrony(
                        recent_spikes[neuron_a],
                        recent_spikes[neuron_b]
                    )
                    synchrony_values.append(sync)
        
        return np.mean(synchrony_values) if synchrony_values else 0.0
    
    def modulate_plasticity(self, neuron_id: int, modulation_factor: float) -> None:
        """Modulate plasticity based on temporal dynamics."""
        self.plasticity_modulation[neuron_id] = modulation_factor
    
    def get_plasticity_modulation(self, neuron_id: int) -> float:
        """Get current plasticity modulation for a neuron."""
        return self.plasticity_modulation.get(neuron_id, 1.0)
    
    def detect_burst(self, neuron_id: int) -> bool:
        """Check if neuron is currently in a burst state."""
        return self.burst_detection.get(neuron_id, False)
    
    def get_firing_rate(self, neuron_id: int, time_window: float = 1.0) -> float:
        """Calculate instantaneous firing rate."""
        if neuron_id not in self.spike_history:
            return 0.0
        
        cutoff_time = self.current_time - time_window
        recent_spikes = [
            t for t in self.spike_history[neuron_id] 
            if t >= cutoff_time
        ]
        
        return len(recent_spikes) / time_window
    
    def get_isi_statistics(self, neuron_id: int) -> Dict[str, float]:
        """Get inter-spike interval statistics."""
        if neuron_id not in self.spike_intervals or not self.spike_intervals[neuron_id]:
            return {'mean': 0.0, 'std': 0.0, 'cv': 0.0}
        
        intervals = list(self.spike_intervals[neuron_id])
        
        mean_isi = np.mean(intervals)
        std_isi = np.std(intervals)
        cv_isi = std_isi / mean_isi if mean_isi > 0 else 0.0
        
        return {
            'mean': mean_isi,
            'std': std_isi,
            'cv': cv_isi
        }
    
    def analyze_spike_train(self, neuron_id: int) -> Dict[str, Any]:
        """Comprehensive spike train analysis."""
        if neuron_id not in self.spike_history:
            return {}
        
        spike_times = list(self.spike_history[neuron_id])
        
        if len(spike_times) < 2:
            return {}
        
        # Basic statistics
        analysis = {
            'num_spikes': len(spike_times),
            'duration': spike_times[-1] - spike_times[0] if len(spike_times) > 1 else 0.0,
            'firing_rate': self.get_firing_rate(neuron_id),
            'isi_stats': self.get_isi_statistics(neuron_id)
        }
        
        # Regularity measures
        if len(spike_times) >= 3:
            intervals = np.diff(spike_times)
            analysis['regularity'] = {
                'cv': np.std(intervals) / np.mean(intervals),
                'fano_factor': np.var(intervals) / np.mean(intervals)
            }
        
        # Burst analysis
        analysis['burst_detected'] = self.detect_burst(neuron_id)
        
        return analysis
    
    def get_network_synchrony(self, neuron_ids: List[int] = None) -> Dict[str, float]:
        """Calculate network-wide synchrony measures."""
        if neuron_ids is None:
            neuron_ids = list(self.spike_history.keys())
        
        if len(neuron_ids) < 2:
            return {'synchrony': 0.0, 'coherence': 0.0}
        
        # Calculate synchrony
        synchrony = self.get_synchrony_measure(neuron_ids)
        
        # Calculate coherence from oscillation state
        coherence = self.global_oscillation_state.coherence
        
        return {
            'synchrony': synchrony,
            'coherence': coherence,
            'participating_neurons': len(neuron_ids)
        }
    
    def add_pattern_callback(self, pattern_id: str, callback: Callable) -> None:
        """Add callback for pattern detection."""
        self.pattern_callbacks[pattern_id].append(callback)
    
    def add_oscillation_callback(self, callback: Callable) -> None:
        """Add callback for oscillation updates."""
        self.oscillation_callbacks.append(callback)
    
    def add_synchrony_callback(self, callback: Callable) -> None:
        """Add callback for synchrony changes."""
        self.synchrony_callbacks.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get temporal dynamics statistics."""
        avg_processing_time = (
            np.mean(self.processing_times) if self.processing_times else 0.0
        )
        
        return {
            'current_time': self.current_time,
            'active_neurons': len(self.spike_history),
            'detected_patterns': len(self.detected_patterns),
            'pattern_templates': len(self.pattern_templates),
            'oscillation_frequency': self.global_oscillation_state.frequency,
            'oscillation_coherence': self.global_oscillation_state.coherence,
            'avg_processing_time': avg_processing_time,
            'pattern_counts': dict(self.pattern_counts)
        }
    
    def _initialize_oscillations(self) -> None:
        """Initialize oscillation generators."""
        # Common neural oscillation frequencies
        oscillation_bands = {
            'delta': (1, 4),     # Deep sleep
            'theta': (4, 8),     # Memory formation
            'alpha': (8, 13),    # Relaxed awareness
            'beta': (13, 30),    # Active concentration
            'gamma': (30, 100)   # Binding, consciousness
        }
        
        for band_name, (min_freq, max_freq) in oscillation_bands.items():
            center_freq = (min_freq + max_freq) / 2
            self.oscillations[band_name] = OscillationState(
                frequency=center_freq,
                amplitude=1.0,
                phase=np.random.uniform(0, 2*np.pi),
                coherence=0.5,
                participants=[],
                last_update=0.0
            )
    
    def _setup_pattern_templates(self) -> None:
        """Setup common temporal pattern templates."""
        # Burst pattern
        burst_pattern = TemporalPattern(
            pattern_id="burst",
            spike_times=[0, 0.002, 0.004, 0.006],  # 4 spikes in 6ms
            neuron_ids=[0],
            duration=0.006,
            metadata={'type': 'burst', 'min_spikes': 3}
        )
        self.add_pattern_template(burst_pattern)
        
        # Gamma oscillation pattern
        gamma_pattern = TemporalPattern(
            pattern_id="gamma_oscillation",
            spike_times=np.arange(0, 0.1, 1/40).tolist(),  # 40Hz for 100ms
            neuron_ids=list(range(10)),
            duration=0.1,
            frequency=40.0,
            metadata={'type': 'oscillation', 'band': 'gamma'}
        )
        self.add_pattern_template(gamma_pattern)
    
    def _update_oscillations(self, dt: float) -> None:
        """Update neural oscillation states."""
        for band_name, osc_state in self.oscillations.items():
            # Update phase
            angular_freq = 2 * np.pi * osc_state.frequency
            osc_state.phase += angular_freq * dt
            osc_state.phase = osc_state.phase % (2 * np.pi)
            
            # Update coherence based on participation
            if osc_state.participants:
                participation_factor = len(osc_state.participants) / 100.0
                target_coherence = min(participation_factor, 1.0)
                
                # Smooth coherence update
                alpha = 0.1
                osc_state.coherence = (1 - alpha) * osc_state.coherence + alpha * target_coherence
            
            osc_state.last_update = self.current_time
        
        # Update global oscillation state
        self.global_oscillation_state.phase += 2 * np.pi * self.global_oscillation_state.frequency * dt
        self.global_oscillation_state.phase = self.global_oscillation_state.phase % (2 * np.pi)
        self.global_oscillation_state.last_update = self.current_time
    
    def _detect_temporal_patterns(self) -> None:
        """Detect temporal patterns in spike activity."""
        for pattern_id, template in self.pattern_templates.items():
            detected = self._match_pattern(template)
            
            if detected:
                if pattern_id not in self.detected_patterns:
                    self.detected_patterns[pattern_id] = []
                
                self.detected_patterns[pattern_id].append({
                    'time': self.current_time,
                    'neurons': detected['neurons'],
                    'confidence': detected['confidence']
                })
                
                self.pattern_counts[pattern_id] += 1
                
                # Call pattern callbacks
                for callback in self.pattern_callbacks[pattern_id]:
                    try:
                        callback(pattern_id, detected)
                    except Exception as e:
                        self.logger.warning(f"Pattern callback failed: {e}")
    
    def _match_pattern(self, template: TemporalPattern) -> Optional[Dict[str, Any]]:
        """Match a pattern template against current spike activity."""
        # This is a simplified pattern matching algorithm
        # In practice, you would use more sophisticated methods
        
        # Look for burst patterns
        if template.metadata.get('type') == 'burst':
            return self._detect_burst_pattern(template)
        
        # Look for oscillation patterns
        elif template.metadata.get('type') == 'oscillation':
            return self._detect_oscillation_pattern(template)
        
        return None
    
    def _detect_burst_pattern(self, template: TemporalPattern) -> Optional[Dict[str, Any]]:
        """Detect burst patterns."""
        min_spikes = template.metadata.get('min_spikes', 3)
        burst_window = template.duration
        
        for neuron_id, spike_times in self.spike_history.items():
            if len(spike_times) < min_spikes:
                continue
            
            # Check recent spikes for burst
            recent_spikes = [
                t for t in spike_times 
                if t >= self.current_time - burst_window
            ]
            
            if len(recent_spikes) >= min_spikes:
                # Calculate burst strength
                intervals = np.diff(sorted(recent_spikes))
                avg_interval = np.mean(intervals)
                
                # Burst if intervals are short and consistent
                if avg_interval < 0.01 and np.std(intervals) < 0.005:
                    return {
                        'neurons': [neuron_id],
                        'confidence': 0.8,
                        'properties': {
                            'num_spikes': len(recent_spikes),
                            'avg_interval': avg_interval
                        }
                    }
        
        return None
    
    def _detect_oscillation_pattern(self, template: TemporalPattern) -> Optional[Dict[str, Any]]:
        """Detect oscillation patterns."""
        target_freq = template.frequency
        if not target_freq:
            return None
        
        # Check if current oscillation matches template
        current_phase = self.get_oscillation_phase(target_freq)
        template_phase = template.metadata.get('phase', 0.0)
        
        phase_diff = abs(current_phase - template_phase)
        phase_diff = min(phase_diff, 2*np.pi - phase_diff)  # Circular distance
        
        if phase_diff < np.pi/4:  # Within 45 degrees
            return {
                'neurons': [],  # Global pattern
                'confidence': 0.7,
                'properties': {
                    'frequency': target_freq,
                    'phase_match': 1 - phase_diff/(np.pi/4)
                }
            }
        
        return None
    
    def _update_synchronization(self) -> None:
        """Update synchronization measures."""
        # Calculate global synchrony
        all_neurons = list(self.spike_history.keys())
        if len(all_neurons) >= 2:
            synchrony = self.get_synchrony_measure(all_neurons)
            self.coherence_history.append(synchrony)
            
            # Update global oscillation coherence
            self.global_oscillation_state.coherence = synchrony
    
    def _update_plasticity_modulation(self, dt: float) -> None:
        """Update plasticity modulation based on temporal dynamics."""
        for neuron_id in list(self.plasticity_modulation.keys()):
            # Decay modulation over time
            decay_factor = np.exp(-dt / 0.1)  # 100ms time constant
            self.plasticity_modulation[neuron_id] *= decay_factor
            
            # Remove if too small
            if self.plasticity_modulation[neuron_id] < 0.01:
                del self.plasticity_modulation[neuron_id]
    
    def _detect_burst(self, neuron_id: int, spike_time: float) -> None:
        """Detect if neuron is in burst state."""
        if len(self.spike_history[neuron_id]) < 3:
            return
        
        # Check last 3 spikes
        recent_spikes = list(self.spike_history[neuron_id])[-3:]
        intervals = np.diff(recent_spikes)
        
        # Burst if all intervals are short (< 10ms)
        if all(isi < 0.01 for isi in intervals):
            self.burst_detection[neuron_id] = True
        else:
            self.burst_detection[neuron_id] = False
    
    def _calculate_pairwise_synchrony(self, spikes_a: List[float], 
                                    spikes_b: List[float]) -> float:
        """Calculate synchrony between two spike trains."""
        if not spikes_a or not spikes_b:
            return 0.0
        
        # Simple coincidence-based synchrony measure
        coincidence_window = 0.005  # 5ms
        coincidences = 0
        
        for spike_a in spikes_a:
            for spike_b in spikes_b:
                if abs(spike_a - spike_b) <= coincidence_window:
                    coincidences += 1
                    break
        
        max_coincidences = min(len(spikes_a), len(spikes_b))
        
        return coincidences / max_coincidences if max_coincidences > 0 else 0.0
    
    def _cleanup_old_data(self) -> None:
        """Clean up old temporal data."""
        # Remove old detected patterns
        pattern_lifetime = 1.0  # 1 second
        
        for pattern_id in list(self.detected_patterns.keys()):
            old_detections = [
                d for d in self.detected_patterns[pattern_id]
                if self.current_time - d['time'] > pattern_lifetime
            ]
            
            for old_detection in old_detections:
                self.detected_patterns[pattern_id].remove(old_detection)
            
            # Remove empty pattern lists
            if not self.detected_patterns[pattern_id]:
                del self.detected_patterns[pattern_id]