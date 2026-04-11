"""
Spiking Neural Networks Implementation

Biologically-inspired spiking neural networks with Leaky Integrate-and-Fire neurons,
STDP learning, and temporal dynamics that mirror biological neural networks.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
from collections import deque
import asyncio
import time

from ..core import BioCognitiveModule, BiologicalMetrics

logger = logging.getLogger(__name__)

@dataclass
class SpikeEvent:
    """Represents a spike event in the network"""
    neuron_id: int
    timestamp: float
    amplitude: float = 1.0
    duration: float = 1.0
    
class NeuronModel(ABC):
    """Abstract base class for neuron models"""
    
    @abstractmethod
    def update(self, dt: float, current: float) -> bool:
        """Update neuron state and return True if spike occurred"""
        pass
    
    @abstractmethod
    def reset(self):
        """Reset neuron to resting state"""
        pass

class LeakyIntegrateFireNeuron(NeuronModel):
    """
    Leaky Integrate-and-Fire neuron model
    
    Implements the classic LIF neuron with biologically plausible parameters
    """
    
    def __init__(self, 
                 v_rest: float = -70.0,      # Resting potential (mV)
                 v_threshold: float = -55.0,  # Spike threshold (mV)
                 v_reset: float = -80.0,      # Reset potential (mV)
                 tau_m: float = 20.0,         # Membrane time constant (ms)
                 r_m: float = 10.0,           # Membrane resistance (MΩ)
                 refractory_period: float = 2.0,  # Refractory period (ms)
                 noise_std: float = 0.1):    # Noise standard deviation
        
        self.v_rest = v_rest
        self.v_threshold = v_threshold
        self.v_reset = v_reset
        self.tau_m = tau_m
        self.r_m = r_m
        self.refractory_period = refractory_period
        self.noise_std = noise_std
        
        # State variables
        self.v_membrane = v_rest
        self.last_spike_time = -np.inf
        self.spike_count = 0
        
    def update(self, dt: float, current: float) -> bool:
        """Update neuron membrane potential"""
        current_time = time.time() * 1000  # Convert to ms
        
        # Check if in refractory period
        if current_time - self.last_spike_time < self.refractory_period:
            return False
        
        # Add noise
        noise = np.random.normal(0, self.noise_std)
        
        # Leaky integrate dynamics
        dv_dt = (-(self.v_membrane - self.v_rest) + self.r_m * (current + noise)) / self.tau_m
        self.v_membrane += dv_dt * dt
        
        # Check for spike
        if self.v_membrane >= self.v_threshold:
            self.v_membrane = self.v_reset
            self.last_spike_time = current_time
            self.spike_count += 1
            return True
        
        return False
    
    def reset(self):
        """Reset neuron to resting state"""
        self.v_membrane = self.v_rest
        self.last_spike_time = -np.inf
        self.spike_count = 0

class AdaptiveExponentialNeuron(NeuronModel):
    """
    Adaptive Exponential Integrate-and-Fire neuron
    
    More sophisticated neuron model with adaptation and exponential spike initiation
    """
    
    def __init__(self,
                 v_rest: float = -70.0,
                 v_threshold: float = -50.0,
                 v_reset: float = -80.0,
                 delta_t: float = 2.0,        # Spike slope factor
                 tau_m: float = 9.3,          # Membrane time constant
                 tau_w: float = 144.0,        # Adaptation time constant
                 a: float = 4.0,              # Sub-threshold adaptation
                 b: float = 0.0805,           # Spike-triggered adaptation
                 v_peak: float = 20.0):       # Spike cutoff
        
        self.v_rest = v_rest
        self.v_threshold = v_threshold
        self.v_reset = v_reset
        self.delta_t = delta_t
        self.tau_m = tau_m
        self.tau_w = tau_w
        self.a = a
        self.b = b
        self.v_peak = v_peak
        
        # State variables
        self.v_membrane = v_rest
        self.w_adaptation = 0.0
        self.spike_count = 0
        
    def update(self, dt: float, current: float) -> bool:
        """Update adaptive exponential neuron"""
        # Membrane potential dynamics
        exp_term = self.delta_t * np.exp((self.v_membrane - self.v_threshold) / self.delta_t)
        dv_dt = (-(self.v_membrane - self.v_rest) + exp_term - self.w_adaptation + current) / self.tau_m
        
        # Adaptation dynamics
        dw_dt = (self.a * (self.v_membrane - self.v_rest) - self.w_adaptation) / self.tau_w
        
        # Update state
        self.v_membrane += dv_dt * dt
        self.w_adaptation += dw_dt * dt
        
        # Check for spike
        if self.v_membrane >= self.v_peak:
            self.v_membrane = self.v_reset
            self.w_adaptation += self.b
            self.spike_count += 1
            return True
        
        return False
    
    def reset(self):
        """Reset neuron to resting state"""
        self.v_membrane = self.v_rest
        self.w_adaptation = 0.0
        self.spike_count = 0

@dataclass
class SynapticConnection:
    """Represents a synaptic connection between neurons"""
    pre_neuron_id: int
    post_neuron_id: int
    weight: float
    delay: float = 1.0              # Synaptic delay (ms)
    type: str = "excitatory"        # "excitatory" or "inhibitory"
    
    # STDP parameters
    a_plus: float = 0.01            # LTP learning rate
    a_minus: float = 0.012          # LTD learning rate
    tau_plus: float = 20.0          # LTP time constant
    tau_minus: float = 20.0         # LTD time constant
    
    # Synaptic dynamics
    tau_syn: float = 5.0            # Synaptic time constant
    last_update: float = 0.0
    
    def update_weight(self, pre_spike_time: float, post_spike_time: float, dt: float):
        """Update synaptic weight using STDP"""
        delta_t = post_spike_time - pre_spike_time
        
        if delta_t > 0:  # Post-synaptic spike after pre-synaptic (LTP)
            dw = self.a_plus * np.exp(-delta_t / self.tau_plus)
        else:  # Pre-synaptic spike after post-synaptic (LTD)
            dw = -self.a_minus * np.exp(delta_t / self.tau_minus)
        
        self.weight += dw
        
        # Enforce weight bounds
        if self.type == "excitatory":
            self.weight = np.clip(self.weight, 0.0, 10.0)
        else:
            self.weight = np.clip(self.weight, -10.0, 0.0)

class SpikingNeuron:
    """Individual spiking neuron with comprehensive biological modeling"""
    
    def __init__(self, 
                 neuron_id: int,
                 neuron_model: NeuronModel,
                 neuron_type: str = "excitatory",
                 location: Optional[Tuple[float, float, float]] = None):
        
        self.neuron_id = neuron_id
        self.model = neuron_model
        self.neuron_type = neuron_type
        self.location = location or (0.0, 0.0, 0.0)
        
        # Connection tracking
        self.incoming_connections: List[SynapticConnection] = []
        self.outgoing_connections: List[SynapticConnection] = []
        
        # Spike history for STDP
        self.spike_times: deque = deque(maxlen=100)
        
        # Current input and state
        self.current_input = 0.0
        self.output_current = 0.0
        
        # Biological metrics
        self.energy_consumption = 0.0
        self.firing_rate = 0.0
        self.last_firing_rate_update = time.time()
        
    def add_incoming_connection(self, connection: SynapticConnection):
        """Add incoming synaptic connection"""
        self.incoming_connections.append(connection)
    
    def add_outgoing_connection(self, connection: SynapticConnection):
        """Add outgoing synaptic connection"""
        self.outgoing_connections.append(connection)
    
    def update(self, dt: float) -> Optional[SpikeEvent]:
        """Update neuron and return spike event if spike occurred"""
        # Update neuron model
        spiked = self.model.update(dt, self.current_input)
        
        # Update energy consumption
        base_energy = 0.001  # Base metabolic cost
        spike_energy = 0.1 if spiked else 0.0
        self.energy_consumption += base_energy + spike_energy
        
        # Update firing rate
        current_time = time.time()
        if current_time - self.last_firing_rate_update > 1.0:  # Update every second
            self.firing_rate = len(self.spike_times) / 1.0  # Spikes per second
            self.last_firing_rate_update = current_time
        
        if spiked:
            spike_time = current_time * 1000  # Convert to ms
            self.spike_times.append(spike_time)
            
            return SpikeEvent(
                neuron_id=self.neuron_id,
                timestamp=spike_time,
                amplitude=1.0
            )
        
        return None
    
    def receive_spike(self, spike: SpikeEvent, weight: float, delay: float):
        """Process incoming spike"""
        # Simple exponential decay for post-synaptic current
        self.current_input += weight * np.exp(-delay / 5.0)  # tau_syn = 5ms
    
    def reset_input(self):
        """Reset current input (called after each update)"""
        self.current_input *= 0.95  # Exponential decay

class SpikingNeuralNetwork(BioCognitiveModule):
    """
    Comprehensive Spiking Neural Network implementation
    
    Features:
    - Multiple neuron models (LIF, AdEx)
    - STDP learning
    - Temporal dynamics
    - Network topology management
    - Biological metrics tracking
    """
    
    def __init__(self, 
                 name: str = "SNN",
                 num_neurons: int = 1000,
                 connection_probability: float = 0.1,
                 excitatory_ratio: float = 0.8,
                 config: Optional[Dict[str, Any]] = None):
        
        super().__init__(name)
        
        self.config = config or self._get_default_config()
        self.num_neurons = num_neurons
        self.connection_probability = connection_probability
        self.excitatory_ratio = excitatory_ratio
        
        # Network components
        self.neurons: Dict[int, SpikingNeuron] = {}
        self.connections: List[SynapticConnection] = []
        
        # Network state
        self.current_time = 0.0
        self.dt = 0.1  # Time step (ms)
        
        # Metrics tracking
        self.total_spikes = 0
        self.network_activity = deque(maxlen=1000)
        self.energy_consumption = 0.0
        
        # Event queue for delayed spikes
        self.spike_queue: List[Tuple[float, SpikeEvent, SynapticConnection]] = []
        
        # Initialize network
        self._initialize_network()
        
        logger.info(f"Initialized SNN with {num_neurons} neurons and {len(self.connections)} connections")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'neuron_model': 'LIF',
            'dt': 0.1,
            'stdp_enabled': True,
            'homeostatic_scaling': True,
            'noise_level': 0.1,
            'max_weight': 10.0,
            'min_weight': 0.0,
            'target_firing_rate': 5.0,  # Hz
            'scaling_factor': 0.001
        }
    
    def _initialize_network(self):
        """Initialize network topology and connections"""
        # Create neurons
        for i in range(self.num_neurons):
            neuron_type = "excitatory" if i < int(self.num_neurons * self.excitatory_ratio) else "inhibitory"
            
            # Choose neuron model
            if self.config['neuron_model'] == 'LIF':
                model = LeakyIntegrateFireNeuron()
            else:
                model = AdaptiveExponentialNeuron()
            
            # Random 3D location
            location = (
                np.random.uniform(-1, 1),
                np.random.uniform(-1, 1),
                np.random.uniform(-1, 1)
            )
            
            neuron = SpikingNeuron(i, model, neuron_type, location)
            self.neurons[i] = neuron
        
        # Create connections
        self._create_connections()
    
    def _create_connections(self):
        """Create synaptic connections between neurons"""
        for pre_id in range(self.num_neurons):
            for post_id in range(self.num_neurons):
                if pre_id != post_id and np.random.random() < self.connection_probability:
                    
                    pre_neuron = self.neurons[pre_id]
                    post_neuron = self.neurons[post_id]
                    
                    # Calculate distance-based delay
                    distance = np.linalg.norm(
                        np.array(pre_neuron.location) - np.array(post_neuron.location)
                    )
                    delay = 1.0 + distance * 5.0  # 1-6 ms delay range
                    
                    # Set weight based on neuron types
                    if pre_neuron.neuron_type == "excitatory":
                        weight = np.random.uniform(0.1, 2.0)
                        conn_type = "excitatory"
                    else:
                        weight = np.random.uniform(-2.0, -0.1)
                        conn_type = "inhibitory"
                    
                    connection = SynapticConnection(
                        pre_neuron_id=pre_id,
                        post_neuron_id=post_id,
                        weight=weight,
                        delay=delay,
                        type=conn_type
                    )
                    
                    self.connections.append(connection)
                    pre_neuron.add_outgoing_connection(connection)
                    post_neuron.add_incoming_connection(connection)
    
    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process inputs through the spiking neural network"""
        
        # Extract input currents
        input_currents = inputs.get('input_currents', {})
        external_stimuli = inputs.get('external_stimuli', np.array([]))
        
        # Apply external stimuli to random neurons
        if len(external_stimuli) > 0:
            stimulated_neurons = np.random.choice(
                list(self.neurons.keys()), 
                size=min(len(external_stimuli), self.num_neurons),
                replace=False
            )
            
            for i, neuron_id in enumerate(stimulated_neurons):
                if i < len(external_stimuli):
                    self.neurons[neuron_id].current_input += external_stimuli[i]
        
        # Apply specific input currents
        for neuron_id, current in input_currents.items():
            if neuron_id in self.neurons:
                self.neurons[neuron_id].current_input += current
        
        # Simulate network for one time step
        spike_events = await self._simulate_timestep()
        
        # Process spike propagation
        await self._propagate_spikes(spike_events)
        
        # Update network metrics
        self._update_network_metrics(spike_events)
        
        # Apply learning if enabled
        if self.config['stdp_enabled']:
            self._apply_stdp_learning()
        
        # Apply homeostatic scaling if enabled
        if self.config['homeostatic_scaling']:
            self._apply_homeostatic_scaling()
        
        # Prepare outputs
        output = {
            'spike_events': [
                {
                    'neuron_id': spike.neuron_id,
                    'timestamp': spike.timestamp,
                    'amplitude': spike.amplitude
                }
                for spike in spike_events
            ],
            'network_activity': len(spike_events),
            'firing_rates': {
                neuron_id: neuron.firing_rate 
                for neuron_id, neuron in self.neurons.items()
            },
            'total_energy': self.energy_consumption,
            'mean_firing_rate': np.mean([n.firing_rate for n in self.neurons.values()]),
            'network_synchrony': self._calculate_synchrony(),
            'connection_strengths': [conn.weight for conn in self.connections]
        }
        
        return output
    
    async def _simulate_timestep(self) -> List[SpikeEvent]:
        """Simulate one timestep of the network"""
        spike_events = []
        
        # Update all neurons
        for neuron in self.neurons.values():
            spike = neuron.update(self.dt)
            if spike:
                spike_events.append(spike)
            
            # Reset input for next timestep
            neuron.reset_input()
        
        # Update time
        self.current_time += self.dt
        
        return spike_events
    
    async def _propagate_spikes(self, spike_events: List[SpikeEvent]):
        """Propagate spikes through synaptic connections"""
        
        for spike in spike_events:
            # Find all outgoing connections from this neuron
            spiking_neuron = self.neurons[spike.neuron_id]
            
            for connection in spiking_neuron.outgoing_connections:
                # Schedule spike delivery with delay
                delivery_time = self.current_time + connection.delay
                self.spike_queue.append((delivery_time, spike, connection))
        
        # Process delayed spikes
        delivered_spikes = []
        remaining_spikes = []
        
        for delivery_time, spike, connection in self.spike_queue:
            if delivery_time <= self.current_time:
                # Deliver spike
                post_neuron = self.neurons[connection.post_neuron_id]
                post_neuron.receive_spike(spike, connection.weight, connection.delay)
                delivered_spikes.append((spike, connection))
            else:
                remaining_spikes.append((delivery_time, spike, connection))
        
        self.spike_queue = remaining_spikes
    
    def _apply_stdp_learning(self):
        """Apply Spike-Timing Dependent Plasticity learning"""
        current_time = self.current_time
        
        for connection in self.connections:
            pre_neuron = self.neurons[connection.pre_neuron_id]
            post_neuron = self.neurons[connection.post_neuron_id]
            
            # Check for recent spike pairs
            for pre_spike_time in list(pre_neuron.spike_times)[-10:]:  # Last 10 spikes
                for post_spike_time in list(post_neuron.spike_times)[-10:]:
                    # Only consider recent spike pairs
                    if abs(pre_spike_time - post_spike_time) < 100:  # Within 100ms
                        connection.update_weight(pre_spike_time, post_spike_time, self.dt)
    
    def _apply_homeostatic_scaling(self):
        """Apply homeostatic scaling to maintain target firing rates"""
        target_rate = self.config['target_firing_rate']
        scaling_factor = self.config['scaling_factor']
        
        for neuron in self.neurons.values():
            if neuron.firing_rate > 0:
                # Scale all incoming connections
                scale = target_rate / neuron.firing_rate
                scale = 1.0 + scaling_factor * (scale - 1.0)  # Gradual scaling
                
                for connection in neuron.incoming_connections:
                    connection.weight *= scale
                    
                    # Enforce bounds
                    if connection.type == "excitatory":
                        connection.weight = np.clip(connection.weight, 0.0, self.config['max_weight'])
                    else:
                        connection.weight = np.clip(connection.weight, -self.config['max_weight'], 0.0)
    
    def _update_network_metrics(self, spike_events: List[SpikeEvent]):
        """Update network-level metrics"""
        num_spikes = len(spike_events)
        self.total_spikes += num_spikes
        self.network_activity.append(num_spikes)
        
        # Update energy consumption
        for neuron in self.neurons.values():
            self.energy_consumption += neuron.energy_consumption
            neuron.energy_consumption = 0  # Reset for next timestep
    
    def _calculate_synchrony(self) -> float:
        """Calculate network synchrony measure"""
        if len(self.network_activity) < 2:
            return 0.0
        
        # Simple measure: coefficient of variation of activity
        activity_array = np.array(list(self.network_activity))
        if np.mean(activity_array) == 0:
            return 0.0
        
        cv = np.std(activity_array) / np.mean(activity_array)
        synchrony = 1.0 / (1.0 + cv)  # Higher synchrony = lower CV
        
        return synchrony
    
    def get_biological_metrics(self) -> BiologicalMetrics:
        """Get current biological metrics"""
        if not self.neurons:
            return BiologicalMetrics()
        
        firing_rates = [neuron.firing_rate for neuron in self.neurons.values()]
        mean_firing_rate = np.mean(firing_rates)
        
        # Calculate energy efficiency
        total_neurons = len(self.neurons)
        energy_per_neuron = self.energy_consumption / (total_neurons + 1e-6)
        efficiency = 1.0 / (1.0 + energy_per_neuron)
        
        # Calculate synaptic strength
        weights = [abs(conn.weight) for conn in self.connections]
        mean_synaptic_strength = np.mean(weights) if weights else 0.0
        
        # Calculate plasticity index (weight change rate)
        weight_variance = np.var(weights) if weights else 0.0
        plasticity_index = min(1.0, weight_variance / 10.0)
        
        self.metrics = BiologicalMetrics(
            energy_efficiency=efficiency,
            spike_rate=mean_firing_rate,
            synaptic_strength=mean_synaptic_strength,
            plasticity_index=plasticity_index,
            neurotransmitter_levels={
                'glutamate': 0.6,  # Excitatory activity proxy
                'gaba': 0.4        # Inhibitory activity proxy
            }
        )
        
        return self.metrics
    
    def update_parameters(self, learning_signal: float):
        """Update network parameters based on learning signal"""
        # Adjust STDP parameters based on learning signal
        if learning_signal > 0.7:  # Strong positive signal - increase plasticity
            for connection in self.connections:
                connection.a_plus *= 1.01
                connection.a_minus *= 1.01
        elif learning_signal < 0.3:  # Weak signal - decrease plasticity
            for connection in self.connections:
                connection.a_plus *= 0.99
                connection.a_minus *= 0.99
    
    def add_neurons(self, num_new_neurons: int):
        """Add new neurons to the network (developmental growth)"""
        start_id = len(self.neurons)
        
        for i in range(num_new_neurons):
            neuron_id = start_id + i
            neuron_type = "excitatory" if np.random.random() < self.excitatory_ratio else "inhibitory"
            
            if self.config['neuron_model'] == 'LIF':
                model = LeakyIntegrateFireNeuron()
            else:
                model = AdaptiveExponentialNeuron()
            
            location = (
                np.random.uniform(-1, 1),
                np.random.uniform(-1, 1),
                np.random.uniform(-1, 1)
            )
            
            neuron = SpikingNeuron(neuron_id, model, neuron_type, location)
            self.neurons[neuron_id] = neuron
            
            # Connect to existing network
            self._connect_new_neuron(neuron)
        
        self.num_neurons += num_new_neurons
        logger.info(f"Added {num_new_neurons} neurons. Total: {self.num_neurons}")
    
    def _connect_new_neuron(self, new_neuron: SpikingNeuron):
        """Connect a new neuron to the existing network"""
        for existing_id, existing_neuron in self.neurons.items():
            if existing_id == new_neuron.neuron_id:
                continue
            
            # Incoming connections
            if np.random.random() < self.connection_probability:
                distance = np.linalg.norm(
                    np.array(existing_neuron.location) - np.array(new_neuron.location)
                )
                delay = 1.0 + distance * 5.0
                
                if existing_neuron.neuron_type == "excitatory":
                    weight = np.random.uniform(0.1, 2.0)
                    conn_type = "excitatory"
                else:
                    weight = np.random.uniform(-2.0, -0.1)
                    conn_type = "inhibitory"
                
                connection = SynapticConnection(
                    pre_neuron_id=existing_id,
                    post_neuron_id=new_neuron.neuron_id,
                    weight=weight,
                    delay=delay,
                    type=conn_type
                )
                
                self.connections.append(connection)
                existing_neuron.add_outgoing_connection(connection)
                new_neuron.add_incoming_connection(connection)
            
            # Outgoing connections
            if np.random.random() < self.connection_probability:
                distance = np.linalg.norm(
                    np.array(new_neuron.location) - np.array(existing_neuron.location)
                )
                delay = 1.0 + distance * 5.0
                
                if new_neuron.neuron_type == "excitatory":
                    weight = np.random.uniform(0.1, 2.0)
                    conn_type = "excitatory"
                else:
                    weight = np.random.uniform(-2.0, -0.1)
                    conn_type = "inhibitory"
                
                connection = SynapticConnection(
                    pre_neuron_id=new_neuron.neuron_id,
                    post_neuron_id=existing_id,
                    weight=weight,
                    delay=delay,
                    type=conn_type
                )
                
                self.connections.append(connection)
                new_neuron.add_outgoing_connection(connection)
                existing_neuron.add_incoming_connection(connection)
    
    def prune_connections(self, threshold: float = 0.1):
        """Prune weak synaptic connections"""
        connections_to_remove = []
        
        for i, connection in enumerate(self.connections):
            if abs(connection.weight) < threshold:
                connections_to_remove.append(i)
        
        # Remove connections (in reverse order to maintain indices)
        for i in reversed(connections_to_remove):
            connection = self.connections[i]
            
            # Remove from neuron connection lists
            pre_neuron = self.neurons[connection.pre_neuron_id]
            post_neuron = self.neurons[connection.post_neuron_id]
            
            if connection in pre_neuron.outgoing_connections:
                pre_neuron.outgoing_connections.remove(connection)
            if connection in post_neuron.incoming_connections:
                post_neuron.incoming_connections.remove(connection)
            
            # Remove from main list
            del self.connections[i]
        
        logger.info(f"Pruned {len(connections_to_remove)} weak connections")
    
    def get_network_statistics(self) -> Dict[str, Any]:
        """Get comprehensive network statistics"""
        if not self.neurons:
            return {}
        
        firing_rates = [neuron.firing_rate for neuron in self.neurons.values()]
        weights = [conn.weight for conn in self.connections]
        delays = [conn.delay for conn in self.connections]
        
        excitatory_weights = [w for w in weights if w > 0]
        inhibitory_weights = [w for w in weights if w < 0]
        
        return {
            'num_neurons': len(self.neurons),
            'num_connections': len(self.connections),
            'mean_firing_rate': np.mean(firing_rates),
            'std_firing_rate': np.std(firing_rates),
            'mean_weight': np.mean(np.abs(weights)) if weights else 0.0,
            'std_weight': np.std(weights) if weights else 0.0,
            'mean_delay': np.mean(delays) if delays else 0.0,
            'excitatory_ratio': len(excitatory_weights) / len(weights) if weights else 0.0,
            'mean_excitatory_weight': np.mean(excitatory_weights) if excitatory_weights else 0.0,
            'mean_inhibitory_weight': np.mean(np.abs(inhibitory_weights)) if inhibitory_weights else 0.0,
            'network_synchrony': self._calculate_synchrony(),
            'total_spikes': self.total_spikes,
            'energy_consumption': self.energy_consumption,
            'current_time': self.current_time
        }
    
    def save_network_state(self, filepath: str):
        """Save network state to file"""
        import pickle
        
        state = {
            'config': self.config,
            'num_neurons': self.num_neurons,
            'connection_probability': self.connection_probability,
            'excitatory_ratio': self.excitatory_ratio,
            'current_time': self.current_time,
            'total_spikes': self.total_spikes,
            'energy_consumption': self.energy_consumption,
            'neurons': {
                nid: {
                    'neuron_type': n.neuron_type,
                    'location': n.location,
                    'firing_rate': n.firing_rate,
                    'spike_times': list(n.spike_times)
                }
                for nid, n in self.neurons.items()
            },
            'connections': [
                {
                    'pre_neuron_id': c.pre_neuron_id,
                    'post_neuron_id': c.post_neuron_id,
                    'weight': c.weight,
                    'delay': c.delay,
                    'type': c.type
                }
                for c in self.connections
            ]
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)
        
        logger.info(f"Network state saved to {filepath}")
    
    def load_network_state(self, filepath: str):
        """Load network state from file"""
        import pickle
        
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        
        # Restore basic parameters
        self.config = state['config']
        self.num_neurons = state['num_neurons']
        self.connection_probability = state['connection_probability']
        self.excitatory_ratio = state['excitatory_ratio']
        self.current_time = state['current_time']
        self.total_spikes = state['total_spikes']
        self.energy_consumption = state['energy_consumption']
        
        # Rebuild neurons
        self.neurons = {}
        for nid, neuron_data in state['neurons'].items():
            if self.config['neuron_model'] == 'LIF':
                model = LeakyIntegrateFireNeuron()
            else:
                model = AdaptiveExponentialNeuron()
            
            neuron = SpikingNeuron(
                int(nid), 
                model, 
                neuron_data['neuron_type'], 
                neuron_data['location']
            )
            neuron.firing_rate = neuron_data['firing_rate']
            neuron.spike_times = deque(neuron_data['spike_times'], maxlen=100)
            
            self.neurons[int(nid)] = neuron
        
        # Rebuild connections
        self.connections = []
        for conn_data in state['connections']:
            connection = SynapticConnection(
                pre_neuron_id=conn_data['pre_neuron_id'],
                post_neuron_id=conn_data['post_neuron_id'],
                weight=conn_data['weight'],
                delay=conn_data['delay'],
                type=conn_data['type']
            )
            
            self.connections.append(connection)
            
            # Update neuron connection lists
            pre_neuron = self.neurons[conn_data['pre_neuron_id']]
            post_neuron = self.neurons[conn_data['post_neuron_id']]
            pre_neuron.add_outgoing_connection(connection)
            post_neuron.add_incoming_connection(connection)
        
        logger.info(f"Network state loaded from {filepath}")
    
    def reset_network(self):
        """Reset network to initial state"""
        # Reset all neurons
        for neuron in self.neurons.values():
            neuron.model.reset()
            neuron.spike_times.clear()
            neuron.current_input = 0.0
            neuron.energy_consumption = 0.0
            neuron.firing_rate = 0.0
        
        # Reset network state
        self.current_time = 0.0
        self.total_spikes = 0
        self.energy_consumption = 0.0
        self.network_activity.clear()
        self.spike_queue.clear()
        
        logger.info("Network reset to initial state")