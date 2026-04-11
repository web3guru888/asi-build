"""
Neuromorphic Chip Simulator

Base classes and implementations for simulating various neuromorphic 
computing architectures with realistic hardware constraints and behavior.
"""

import numpy as np
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import logging

class ChipType(Enum):
    """Types of neuromorphic chips."""
    LOIHI = "loihi"
    TRUENORTH = "truenorth"
    SPINNAKER = "spinnaker"
    DYNAP_SE = "dynap_se"
    CUSTOM = "custom"

@dataclass
class ChipConfig:
    """Configuration for neuromorphic chip simulation."""
    chip_type: ChipType = ChipType.LOIHI
    num_cores: int = 128
    neurons_per_core: int = 1024
    synapses_per_core: int = 1048576
    
    # Timing constraints
    time_step: float = 1.0e-3  # 1ms
    max_delay: int = 63
    refractory_period: int = 2
    
    # Quantization
    weight_bits: int = 8
    membrane_bits: int = 16
    threshold_bits: int = 8
    
    # Power model
    static_power: float = 1.0  # Watts
    dynamic_power_per_spike: float = 1.0e-12  # Joules per spike
    dynamic_power_per_synapse: float = 1.0e-15  # Joules per synaptic operation
    
    # Memory constraints
    neuron_memory_per_core: int = 1024 * 8  # Bytes
    synapse_memory_per_core: int = 1024 * 1024  # Bytes
    
    # Communication
    packet_header_bits: int = 40
    routing_table_size: int = 1024
    
    # Noise and variability
    process_variation: float = 0.05
    thermal_noise: float = 0.01
    voltage_noise: float = 0.02

@dataclass
class CoreState:
    """State of a single neuromorphic core."""
    core_id: int
    num_neurons: int = 0
    num_synapses: int = 0
    active_neurons: int = 0
    membrane_potentials: np.ndarray = field(default_factory=lambda: np.array([]))
    spike_counts: np.ndarray = field(default_factory=lambda: np.array([]))
    power_consumption: float = 0.0
    utilization: float = 0.0
    temperature: float = 25.0  # Celsius

class NeuromorphicChip(ABC):
    """
    Abstract base class for neuromorphic chip simulation.
    
    Provides common functionality for:
    - Multi-core architecture simulation
    - Hardware constraints modeling
    - Power consumption tracking
    - Timing and quantization effects
    - Inter-core communication
    """
    
    def __init__(self, config: ChipConfig):
        """Initialize neuromorphic chip."""
        self.config = config
        self.chip_id = id(self)
        
        # Core management
        self.cores = {}
        self.num_cores = config.num_cores
        
        # Initialize cores
        for core_id in range(self.num_cores):
            self.cores[core_id] = CoreState(
                core_id=core_id,
                membrane_potentials=np.zeros(config.neurons_per_core),
                spike_counts=np.zeros(config.neurons_per_core)
            )
        
        # Global state
        self.current_time = 0.0
        self.total_spikes = 0
        self.total_power = 0.0
        
        # Communication infrastructure
        self.spike_packets = []
        self.routing_table = {}
        
        # Performance tracking
        self.utilization_history = []
        self.power_history = []
        self.spike_rate_history = []
        
        # Hardware effects
        self.process_variations = self._generate_process_variations()
        self.thermal_state = self._initialize_thermal_model()
        
        # Threading
        self._lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger(f"neuromorphic.{config.chip_type.value}_chip")
        
        self.logger.info(f"Initialized {config.chip_type.value} chip with {self.num_cores} cores")
    
    @abstractmethod
    def update_neuron_dynamics(self, core_id: int, dt: float) -> None:
        """Update neuron dynamics for a specific core."""
        pass
    
    @abstractmethod
    def process_spikes(self, core_id: int, input_spikes: List[Tuple[int, float]]) -> None:
        """Process incoming spikes for a core."""
        pass
    
    @abstractmethod
    def generate_output_spikes(self, core_id: int) -> List[Tuple[int, float]]:
        """Generate output spikes from a core."""
        pass
    
    def step(self, dt: float) -> None:
        """Execute one simulation time step."""
        start_time = time.perf_counter()
        
        with self._lock:
            # Update global time
            self.current_time += dt
            
            # Process each core
            for core_id in range(self.num_cores):
                self._step_core(core_id, dt)
            
            # Handle inter-core communication
            self._process_communication()
            
            # Update thermal state
            self._update_thermal_model(dt)
            
            # Update power consumption
            self._update_power_model(dt)
            
            # Record performance metrics
            self._record_metrics()
        
        # Track step time
        step_time = time.perf_counter() - start_time
        self._update_performance_metrics(step_time)
    
    def add_neuron(self, core_id: int, neuron_params: Dict[str, Any]) -> int:
        """Add a neuron to a specific core."""
        if core_id >= self.num_cores:
            raise ValueError(f"Core {core_id} does not exist")
        
        core = self.cores[core_id]
        
        if core.num_neurons >= self.config.neurons_per_core:
            raise RuntimeError(f"Core {core_id} is at maximum neuron capacity")
        
        neuron_id = core.num_neurons
        core.num_neurons += 1
        
        # Initialize neuron state with hardware constraints
        self._initialize_neuron_hardware(core_id, neuron_id, neuron_params)
        
        return neuron_id
    
    def add_synapse(self, src_core: int, src_neuron: int, 
                   dst_core: int, dst_neuron: int, 
                   weight: float, delay: int = 1) -> bool:
        """Add a synaptic connection between neurons."""
        # Check hardware constraints
        if not self._validate_synapse_constraints(src_core, dst_core, delay):
            return False
        
        # Quantize weight
        quantized_weight = self._quantize_weight(weight)
        
        # Add to routing table if inter-core
        if src_core != dst_core:
            self._add_to_routing_table(src_core, src_neuron, dst_core, dst_neuron)
        
        # Update core synapse count
        if dst_core < self.num_cores:
            self.cores[dst_core].num_synapses += 1
        
        return True
    
    def get_core_state(self, core_id: int) -> CoreState:
        """Get current state of a core."""
        if core_id >= self.num_cores:
            raise ValueError(f"Core {core_id} does not exist")
        
        return self.cores[core_id]
    
    def get_chip_statistics(self) -> Dict[str, Any]:
        """Get comprehensive chip statistics."""
        total_neurons = sum(core.num_neurons for core in self.cores.values())
        total_synapses = sum(core.num_synapses for core in self.cores.values())
        avg_utilization = np.mean([core.utilization for core in self.cores.values()])
        
        return {
            'chip_type': self.config.chip_type.value,
            'num_cores': self.num_cores,
            'total_neurons': total_neurons,
            'total_synapses': total_synapses,
            'current_time': self.current_time,
            'total_spikes': self.total_spikes,
            'total_power': self.total_power,
            'avg_utilization': avg_utilization,
            'max_neurons': self.num_cores * self.config.neurons_per_core,
            'max_synapses': self.num_cores * self.config.synapses_per_core
        }
    
    def get_power_consumption(self) -> Dict[str, float]:
        """Get detailed power consumption breakdown."""
        static_power = self.config.static_power
        
        # Calculate dynamic power per core
        dynamic_power = 0.0
        for core in self.cores.values():
            dynamic_power += core.power_consumption
        
        return {
            'static_power': static_power,
            'dynamic_power': dynamic_power,
            'total_power': static_power + dynamic_power,
            'power_per_core': (static_power + dynamic_power) / self.num_cores,
            'power_efficiency': self.total_spikes / (static_power + dynamic_power) if dynamic_power > 0 else 0.0
        }
    
    def get_thermal_state(self) -> Dict[str, float]:
        """Get thermal state of the chip."""
        return {
            'avg_temperature': np.mean([core.temperature for core in self.cores.values()]),
            'max_temperature': max(core.temperature for core in self.cores.values()),
            'thermal_gradient': max(core.temperature for core in self.cores.values()) - 
                              min(core.temperature for core in self.cores.values())
        }
    
    def reset(self) -> None:
        """Reset chip to initial state."""
        with self._lock:
            self.current_time = 0.0
            self.total_spikes = 0
            self.total_power = 0.0
            
            # Reset all cores
            for core in self.cores.values():
                core.membrane_potentials.fill(0.0)
                core.spike_counts.fill(0)
                core.power_consumption = 0.0
                core.temperature = 25.0
            
            # Clear communication
            self.spike_packets.clear()
            
            # Clear history
            self.utilization_history.clear()
            self.power_history.clear()
            self.spike_rate_history.clear()
    
    def _step_core(self, core_id: int, dt: float) -> None:
        """Execute one time step for a specific core."""
        # Update neuron dynamics
        self.update_neuron_dynamics(core_id, dt)
        
        # Process incoming spikes
        input_spikes = self._get_input_spikes(core_id)
        self.process_spikes(core_id, input_spikes)
        
        # Generate output spikes
        output_spikes = self.generate_output_spikes(core_id)
        
        # Route output spikes
        self._route_spikes(core_id, output_spikes)
        
        # Update core utilization
        core = self.cores[core_id]
        core.utilization = core.active_neurons / max(core.num_neurons, 1)
    
    def _get_input_spikes(self, core_id: int) -> List[Tuple[int, float]]:
        """Get input spikes for a core from communication packets."""
        input_spikes = []
        
        # Process packets destined for this core
        remaining_packets = []
        
        for packet in self.spike_packets:
            if packet['dst_core'] == core_id and packet['delivery_time'] <= self.current_time:
                input_spikes.append((packet['dst_neuron'], packet['weight']))
            else:
                remaining_packets.append(packet)
        
        self.spike_packets = remaining_packets
        
        return input_spikes
    
    def _route_spikes(self, src_core: int, spikes: List[Tuple[int, float]]) -> None:
        """Route spikes to destination cores."""
        for src_neuron, amplitude in spikes:
            # Look up routing destinations
            route_key = (src_core, src_neuron)
            
            if route_key in self.routing_table:
                for dst_core, dst_neuron, weight, delay in self.routing_table[route_key]:
                    # Create spike packet
                    packet = {
                        'src_core': src_core,
                        'src_neuron': src_neuron,
                        'dst_core': dst_core,
                        'dst_neuron': dst_neuron,
                        'weight': weight * amplitude,
                        'delivery_time': self.current_time + delay * self.config.time_step,
                        'packet_size': self.config.packet_header_bits
                    }
                    
                    self.spike_packets.append(packet)
        
        # Update spike count
        self.total_spikes += len(spikes)
    
    def _process_communication(self) -> None:
        """Process inter-core communication."""
        # Apply communication delays and bandwidth constraints
        # This is a simplified model - real chips have complex NoC architectures
        pass
    
    def _quantize_weight(self, weight: float) -> float:
        """Apply weight quantization based on hardware bits."""
        max_weight = 2**(self.config.weight_bits - 1) - 1
        min_weight = -2**(self.config.weight_bits - 1)
        
        # Scale and quantize
        scaled_weight = weight * max_weight
        quantized = np.clip(np.round(scaled_weight), min_weight, max_weight)
        
        return quantized / max_weight
    
    def _quantize_membrane_potential(self, voltage: float) -> float:
        """Apply membrane potential quantization."""
        max_voltage = 2**(self.config.membrane_bits - 1) - 1
        min_voltage = -2**(self.config.membrane_bits - 1)
        
        # Assume voltage range of -100mV to +50mV
        voltage_range = 0.15  # 150mV
        scaled_voltage = (voltage + 0.1) / voltage_range * max_voltage
        quantized = np.clip(np.round(scaled_voltage), min_voltage, max_voltage)
        
        return (quantized / max_voltage * voltage_range) - 0.1
    
    def _validate_synapse_constraints(self, src_core: int, dst_core: int, delay: int) -> bool:
        """Validate synapse against hardware constraints."""
        # Check delay constraints
        if delay > self.config.max_delay:
            return False
        
        # Check core capacity
        if dst_core >= self.num_cores:
            return False
        
        dst_core_state = self.cores[dst_core]
        if dst_core_state.num_synapses >= self.config.synapses_per_core:
            return False
        
        return True
    
    def _add_to_routing_table(self, src_core: int, src_neuron: int, 
                             dst_core: int, dst_neuron: int) -> None:
        """Add entry to routing table."""
        route_key = (src_core, src_neuron)
        
        if route_key not in self.routing_table:
            self.routing_table[route_key] = []
        
        # Add destination (dst_core, dst_neuron, weight, delay)
        self.routing_table[route_key].append((dst_core, dst_neuron, 1.0, 1))
    
    def _generate_process_variations(self) -> Dict[int, float]:
        """Generate process variations for each core."""
        variations = {}
        
        for core_id in range(self.num_cores):
            # Generate Gaussian variation
            variation = np.random.normal(1.0, self.config.process_variation)
            variations[core_id] = max(0.1, variation)  # Prevent negative variations
        
        return variations
    
    def _initialize_thermal_model(self) -> Dict[str, Any]:
        """Initialize thermal model."""
        return {
            'ambient_temperature': 25.0,
            'thermal_resistance': 1.0,
            'thermal_capacitance': 100.0
        }
    
    def _update_thermal_model(self, dt: float) -> None:
        """Update thermal state based on power consumption."""
        ambient_temp = self.thermal_state['ambient_temperature']
        thermal_resistance = self.thermal_state['thermal_resistance']
        
        for core in self.cores.values():
            # Simple thermal model: T = T_ambient + P * R_thermal
            power_density = core.power_consumption / 1000.0  # W/mm^2 approximation
            temperature_rise = power_density * thermal_resistance
            
            # Add thermal noise
            noise = np.random.normal(0, self.config.thermal_noise)
            
            core.temperature = ambient_temp + temperature_rise + noise
    
    def _update_power_model(self, dt: float) -> None:
        """Update power consumption model."""
        total_dynamic_power = 0.0
        
        for core in self.cores.values():
            # Dynamic power from spikes
            spike_power = (core.active_neurons * 
                          self.config.dynamic_power_per_spike / dt)
            
            # Dynamic power from synaptic operations
            synapse_power = (core.num_synapses * 
                           self.config.dynamic_power_per_synapse / dt)
            
            core.power_consumption = spike_power + synapse_power
            total_dynamic_power += core.power_consumption
        
        self.total_power = self.config.static_power + total_dynamic_power
    
    def _initialize_neuron_hardware(self, core_id: int, neuron_id: int, 
                                  neuron_params: Dict[str, Any]) -> None:
        """Initialize neuron with hardware-specific constraints."""
        core = self.cores[core_id]
        
        # Apply process variations
        variation_factor = self.process_variations[core_id]
        
        # Initialize membrane potential with variation
        rest_potential = neuron_params.get('v_rest', -65.0e-3)
        core.membrane_potentials[neuron_id] = rest_potential * variation_factor
    
    def _record_metrics(self) -> None:
        """Record performance and utilization metrics."""
        avg_utilization = np.mean([core.utilization for core in self.cores.values()])
        self.utilization_history.append(avg_utilization)
        
        self.power_history.append(self.total_power)
        
        spike_rate = self.total_spikes / max(self.current_time, 1e-6)
        self.spike_rate_history.append(spike_rate)
        
        # Limit history length
        max_history = 1000
        if len(self.utilization_history) > max_history:
            self.utilization_history = self.utilization_history[-max_history//2:]
            self.power_history = self.power_history[-max_history//2:]
            self.spike_rate_history = self.spike_rate_history[-max_history//2:]
    
    def _update_performance_metrics(self, step_time: float) -> None:
        """Update performance timing metrics."""
        # Track real-time performance
        real_time_factor = self.config.time_step / step_time
        
        # Log performance warnings
        if real_time_factor < 1.0:
            self.logger.warning(f"Simulation running slower than real-time: {real_time_factor:.2f}x")
