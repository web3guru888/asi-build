"""
Neuromorphic Computing Configuration System

Provides centralized configuration management for all neuromorphic components
including timing parameters, neural dynamics, learning rates, and hardware specifications.
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np

@dataclass
class NeuronConfig:
    """Configuration for individual neuron models."""
    # Leaky Integrate-and-Fire parameters
    tau_membrane: float = 20.0e-3  # Membrane time constant (s)
    tau_synapse: float = 5.0e-3    # Synaptic time constant (s)
    v_threshold: float = -50.0e-3   # Spike threshold (V)
    v_reset: float = -70.0e-3       # Reset potential (V)
    v_rest: float = -65.0e-3        # Resting potential (V)
    refractory_period: float = 2.0e-3  # Refractory period (s)
    
    # Adaptive parameters
    adaptation_strength: float = 0.02
    adaptation_tau: float = 100.0e-3
    
    # Noise parameters
    noise_amplitude: float = 1.0e-3
    noise_correlation: float = 0.1

@dataclass
class SynapseConfig:
    """Configuration for synaptic connections."""
    # Basic synaptic parameters
    weight_init_range: tuple = (0.0, 1.0)
    delay_range: tuple = (1.0e-3, 10.0e-3)
    
    # STDP parameters
    stdp_enabled: bool = True
    tau_plus: float = 20.0e-3      # Pre-synaptic time constant
    tau_minus: float = 20.0e-3     # Post-synaptic time constant
    a_plus: float = 0.01           # LTP amplitude
    a_minus: float = 0.012         # LTD amplitude
    
    # Homeostatic parameters
    homeostasis_enabled: bool = True
    target_rate: float = 5.0       # Target firing rate (Hz)
    homeostasis_tau: float = 1000.0e-3  # Homeostasis time constant
    
    # Metaplasticity
    metaplasticity_enabled: bool = False
    metaplasticity_tau: float = 300.0e-3

@dataclass
class NetworkConfig:
    """Configuration for neural network topology."""
    # Network structure
    num_input_neurons: int = 100
    num_hidden_neurons: int = 500
    num_output_neurons: int = 10
    num_layers: int = 3
    
    # Connectivity
    connection_probability: float = 0.1
    inhibitory_fraction: float = 0.2
    small_world_rewiring: float = 0.1
    
    # Population dynamics
    population_synchrony: float = 0.05
    oscillation_frequency: float = 40.0  # Gamma oscillations (Hz)

@dataclass
class LearningConfig:
    """Configuration for learning algorithms."""
    # STDP parameters
    stdp_learning_rate: float = 0.01
    stdp_window_size: float = 50.0e-3
    
    # Homeostatic plasticity
    homeostatic_scaling: bool = True
    intrinsic_plasticity: bool = True
    
    # Metaplasticity
    bcm_threshold: float = 1e-3
    sliding_threshold: bool = True
    
    # Reinforcement learning
    dopamine_modulation: bool = True
    reward_prediction_error: bool = True

@dataclass
class HardwareConfig:
    """Configuration for neuromorphic hardware simulation."""
    # Chip specifications
    chip_type: str = "loihi"  # loihi, truenorth, spinnaker, dynap-se
    num_cores: int = 128
    neurons_per_core: int = 1024
    
    # Timing constraints
    time_step: float = 1.0e-3  # Simulation time step
    max_delay: float = 63.0e-3  # Maximum synaptic delay
    
    # Quantization
    weight_bits: int = 8
    membrane_bits: int = 16
    
    # Power constraints
    power_budget: float = 1.0  # Watts
    energy_per_spike: float = 1.0e-12  # Joules

@dataclass
class ReservoirConfig:
    """Configuration for reservoir computing systems."""
    # Reservoir structure
    reservoir_size: int = 1000
    input_scaling: float = 0.5
    spectral_radius: float = 0.9
    sparsity: float = 0.1
    
    # Liquid State Machine
    membrane_tau: float = 30.0e-3
    synaptic_tau: float = 3.0e-3
    
    # Echo State Network
    leak_rate: float = 0.1
    feedback_scaling: float = 0.1

@dataclass
class VisionConfig:
    """Configuration for neuromorphic vision processing."""
    # DVS parameters
    temporal_contrast_threshold: float = 0.1
    spatial_filter_size: int = 3
    temporal_filter_length: int = 10
    
    # Event processing
    event_buffer_size: int = 10000
    time_window: float = 10.0e-3
    
    # Feature extraction
    orientation_filters: int = 8
    spatial_frequencies: int = 4

@dataclass
class BCIConfig:
    """Configuration for brain-computer interfaces."""
    # Signal processing
    sampling_rate: float = 1000.0  # Hz
    filter_band: tuple = (1.0, 100.0)  # Hz
    
    # Spike detection
    threshold_factor: float = 4.0
    min_spike_interval: float = 1.0e-3
    
    # Decoding
    decoder_type: str = "kalman"  # kalman, population_vector, machine_learning
    adaptation_rate: float = 0.01

class NeuromorphicConfig:
    """
    Centralized configuration manager for neuromorphic computing system.
    
    Provides hierarchical configuration management with support for:
    - YAML/JSON configuration files
    - Environment variable overrides
    - Runtime parameter updates
    - Configuration validation
    """
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """Initialize configuration system."""
        self.config_file = config_file
        
        # Initialize component configurations
        self.neuron = NeuronConfig()
        self.synapse = SynapseConfig()
        self.network = NetworkConfig()
        self.learning = LearningConfig()
        self.hardware = HardwareConfig()
        self.reservoir = ReservoirConfig()
        self.vision = VisionConfig()
        self.bci = BCIConfig()
        
        # Load configuration if file provided
        if config_file:
            self.load_config(config_file)
            
        # Apply environment variable overrides
        self._apply_env_overrides()
    
    def load_config(self, config_file: Union[str, Path]) -> None:
        """Load configuration from file."""
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config format: {config_path.suffix}")
            
            self._update_from_dict(config_data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def save_config(self, config_file: Union[str, Path]) -> None:
        """Save current configuration to file."""
        config_path = Path(config_file)
        config_data = self.to_dict()
        
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                elif config_path.suffix.lower() == '.json':
                    json.dump(config_data, f, indent=2)
                else:
                    raise ValueError(f"Unsupported config format: {config_path.suffix}")
                    
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'neuron': self.neuron.__dict__,
            'synapse': self.synapse.__dict__,
            'network': self.network.__dict__,
            'learning': self.learning.__dict__,
            'hardware': self.hardware.__dict__,
            'reservoir': self.reservoir.__dict__,
            'vision': self.vision.__dict__,
            'bci': self.bci.__dict__
        }
    
    def _update_from_dict(self, config_data: Dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        for section_name, section_data in config_data.items():
            if hasattr(self, section_name):
                section_config = getattr(self, section_name)
                for key, value in section_data.items():
                    if hasattr(section_config, key):
                        setattr(section_config, key, value)
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        # Neural parameters
        if 'NEUROMORPHIC_TAU_MEMBRANE' in os.environ:
            self.neuron.tau_membrane = float(os.environ['NEUROMORPHIC_TAU_MEMBRANE'])
        
        # Network parameters
        if 'NEUROMORPHIC_HIDDEN_NEURONS' in os.environ:
            self.network.num_hidden_neurons = int(os.environ['NEUROMORPHIC_HIDDEN_NEURONS'])
        
        # Hardware parameters
        if 'NEUROMORPHIC_CHIP_TYPE' in os.environ:
            self.hardware.chip_type = os.environ['NEUROMORPHIC_CHIP_TYPE']
    
    def validate(self) -> bool:
        """Validate configuration parameters."""
        try:
            # Validate neuron parameters
            assert self.neuron.tau_membrane > 0, "Membrane time constant must be positive"
            assert self.neuron.v_threshold > self.neuron.v_reset, "Threshold must be above reset"
            
            # Validate network parameters
            assert self.network.num_input_neurons > 0, "Must have input neurons"
            assert 0 <= self.network.connection_probability <= 1, "Connection probability must be [0,1]"
            
            # Validate hardware parameters
            assert self.hardware.time_step > 0, "Time step must be positive"
            assert self.hardware.weight_bits > 0, "Weight bits must be positive"
            
            return True
            
        except AssertionError as e:
            print(f"Configuration validation failed: {e}")
            return False
    
    def get_timing_parameters(self) -> Dict[str, float]:
        """Get all timing-related parameters."""
        return {
            'time_step': self.hardware.time_step,
            'tau_membrane': self.neuron.tau_membrane,
            'tau_synapse': self.neuron.tau_synapse,
            'refractory_period': self.neuron.refractory_period,
            'stdp_tau_plus': self.synapse.tau_plus,
            'stdp_tau_minus': self.synapse.tau_minus,
            'max_delay': self.hardware.max_delay
        }
    
    def get_plasticity_parameters(self) -> Dict[str, Any]:
        """Get all plasticity-related parameters."""
        return {
            'stdp_enabled': self.synapse.stdp_enabled,
            'stdp_learning_rate': self.learning.stdp_learning_rate,
            'homeostasis_enabled': self.synapse.homeostasis_enabled,
            'target_rate': self.synapse.target_rate,
            'metaplasticity_enabled': self.synapse.metaplasticity_enabled,
            'dopamine_modulation': self.learning.dopamine_modulation
        }
    
    def clone(self) -> 'NeuromorphicConfig':
        """Create a deep copy of the configuration."""
        new_config = NeuromorphicConfig()
        new_config._update_from_dict(self.to_dict())
        return new_config
    
    def __str__(self) -> str:
        """String representation of configuration."""
        lines = ["Neuromorphic Computing Configuration:"]
        
        for section_name in ['neuron', 'synapse', 'network', 'learning', 
                           'hardware', 'reservoir', 'vision', 'bci']:
            section = getattr(self, section_name)
            lines.append(f"\n{section_name.title()}:")
            
            for key, value in section.__dict__.items():
                lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)