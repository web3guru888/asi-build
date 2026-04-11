"""
Base classes for neuromorphic computing components.

Provides fundamental abstractions for neurons, synapses, and networks
with consistent interfaces and shared functionality.
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


@dataclass
class SpikeEvent:
    """Represents a single spike event."""

    neuron_id: int
    timestamp: float
    amplitude: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SynapticEvent:
    """Represents a synaptic transmission event."""

    pre_neuron_id: int
    post_neuron_id: int
    timestamp: float
    weight: float
    delay: float
    event_type: str = "excitatory"  # excitatory, inhibitory, modulatory


class NeuralBase(ABC):
    """
    Abstract base class for all neural components.

    Provides common functionality for:
    - Event handling
    - State management
    - Parameter updates
    - Monitoring and logging
    """

    def __init__(self, component_id: int, name: str = ""):
        """Initialize neural component."""
        self.component_id = component_id
        self.name = name or f"{self.__class__.__name__}_{component_id}"

        # Timing
        self.current_time = 0.0
        self.last_update_time = 0.0

        # State management
        self.state = {}
        self.parameters = {}
        self.is_active = True

        # Event handling
        self.event_queue = deque()
        self.spike_history = deque(maxlen=1000)

        # Monitoring
        self.monitor_enabled = False
        self.recorded_variables = set()
        self.recorded_data = {}

        # Thread safety
        self._lock = threading.Lock()

        # Logging
        self.logger = logging.getLogger(f"neuromorphic.{self.name}")

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update component state for one time step."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset component to initial state."""
        pass

    def set_parameter(self, name: str, value: Any) -> None:
        """Set a parameter value."""
        with self._lock:
            self.parameters[name] = value
            self._on_parameter_changed(name, value)

    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get a parameter value."""
        return self.parameters.get(name, default)

    def get_state(self, variable: str = None) -> Union[Any, Dict[str, Any]]:
        """Get current state or specific state variable."""
        if variable is None:
            return self.state.copy()
        return self.state.get(variable)

    def add_event(self, event: Union[SpikeEvent, SynapticEvent]) -> None:
        """Add event to processing queue."""
        with self._lock:
            self.event_queue.append(event)

    def process_events(self, current_time: float) -> List[Union[SpikeEvent, SynapticEvent]]:
        """Process all queued events up to current time."""
        processed_events = []

        with self._lock:
            while self.event_queue and self.event_queue[0].timestamp <= current_time:
                event = self.event_queue.popleft()
                self._process_event(event)
                processed_events.append(event)

        return processed_events

    def enable_monitoring(self, variables: List[str] = None) -> None:
        """Enable monitoring of specified variables."""
        self.monitor_enabled = True

        if variables:
            self.recorded_variables.update(variables)
        else:
            # Monitor all state variables by default
            self.recorded_variables.update(self.state.keys())

        # Initialize recording buffers
        for var in self.recorded_variables:
            if var not in self.recorded_data:
                self.recorded_data[var] = []

    def disable_monitoring(self) -> None:
        """Disable monitoring and clear recorded data."""
        self.monitor_enabled = False
        self.recorded_variables.clear()
        self.recorded_data.clear()

    def get_recorded_data(self, variable: str = None) -> Union[List, Dict[str, List]]:
        """Get recorded monitoring data."""
        if variable:
            return self.recorded_data.get(variable, [])
        return self.recorded_data.copy()

    def _process_event(self, event: Union[SpikeEvent, SynapticEvent]) -> None:
        """Process a single event (to be overridden by subclasses)."""
        pass

    def _on_parameter_changed(self, name: str, value: Any) -> None:
        """Called when a parameter is changed (to be overridden by subclasses)."""
        pass

    def _record_variables(self) -> None:
        """Record monitored variables."""
        if not self.monitor_enabled:
            return

        for var in self.recorded_variables:
            if var in self.state:
                self.recorded_data[var].append(
                    {"time": self.current_time, "value": self.state[var]}
                )

    def get_info(self) -> Dict[str, Any]:
        """Get component information."""
        return {
            "id": self.component_id,
            "name": self.name,
            "type": self.__class__.__name__,
            "current_time": self.current_time,
            "is_active": self.is_active,
            "num_events_queued": len(self.event_queue),
            "monitor_enabled": self.monitor_enabled,
            "recorded_variables": list(self.recorded_variables),
            "parameters": self.parameters.copy(),
            "state_keys": list(self.state.keys()),
        }


class NeuronBase(NeuralBase):
    """
    Base class for neuron models.

    Provides common neuron functionality:
    - Membrane potential dynamics
    - Spike generation
    - Refractory period handling
    - Input current integration
    """

    def __init__(self, neuron_id: int, neuron_type: str = "excitatory", **kwargs):
        """Initialize neuron."""
        super().__init__(neuron_id, **kwargs)

        self.neuron_type = neuron_type

        # Initialize neuron state
        self.state.update(
            {
                "membrane_potential": -65.0e-3,  # V
                "input_current": 0.0,  # A
                "spike_times": [],
                "last_spike_time": -np.inf,
                "refractory_until": 0.0,
                "adaptation_current": 0.0,
            }
        )

        # Default parameters
        self.parameters.update(
            {
                "v_threshold": -50.0e-3,  # V
                "v_reset": -70.0e-3,  # V
                "v_rest": -65.0e-3,  # V
                "tau_membrane": 20.0e-3,  # s
                "refractory_period": 2.0e-3,  # s
                "capacitance": 1.0e-9,  # F
                "adaptation_strength": 0.02,
                "adaptation_tau": 100.0e-3,  # s
            }
        )

        # Synaptic connections
        self.input_synapses = []
        self.output_synapses = []

        # Spike detection
        self.spike_threshold_crossed = False

    @abstractmethod
    def compute_membrane_dynamics(self, dt: float) -> float:
        """Compute membrane potential change for one time step."""
        pass

    def update(self, dt: float) -> None:
        """Update neuron state for one time step."""
        self.current_time += dt

        # Process incoming events
        self.process_events(self.current_time)

        # Skip dynamics during refractory period
        if self.current_time < self.state["refractory_until"]:
            self._record_variables()
            return

        # Compute membrane dynamics
        dv_dt = self.compute_membrane_dynamics(dt)
        self.state["membrane_potential"] += dv_dt * dt

        # Check for spike
        if self._check_spike_condition():
            self._generate_spike()

        # Update adaptation current
        self._update_adaptation(dt)

        # Reset input current
        self.state["input_current"] = 0.0

        # Record monitoring data
        self._record_variables()

    def add_input_current(self, current: float) -> None:
        """Add input current to the neuron."""
        self.state["input_current"] += current

    def add_input_synapse(self, synapse: "SynapseBase") -> None:
        """Add input synaptic connection."""
        self.input_synapses.append(synapse)

    def add_output_synapse(self, synapse: "SynapseBase") -> None:
        """Add output synaptic connection."""
        self.output_synapses.append(synapse)

    def get_firing_rate(self, time_window: float = 1.0) -> float:
        """Calculate recent firing rate."""
        recent_spikes = [
            t for t in self.state["spike_times"] if t > self.current_time - time_window
        ]
        return len(recent_spikes) / time_window

    def is_refractory(self) -> bool:
        """Check if neuron is in refractory period."""
        return self.current_time < self.state["refractory_until"]

    def _check_spike_condition(self) -> bool:
        """Check if neuron should spike."""
        v_mem = self.state["membrane_potential"]
        v_thresh = self.parameters["v_threshold"]

        # Detect threshold crossing
        if v_mem >= v_thresh and not self.spike_threshold_crossed:
            self.spike_threshold_crossed = True
            return True
        elif v_mem < v_thresh:
            self.spike_threshold_crossed = False

        return False

    def _generate_spike(self) -> None:
        """Generate a spike event."""
        spike_time = self.current_time

        # Update neuron state
        self.state["last_spike_time"] = spike_time
        self.state["spike_times"].append(spike_time)
        self.state["membrane_potential"] = self.parameters["v_reset"]
        self.state["refractory_until"] = spike_time + self.parameters["refractory_period"]

        # Create spike event
        spike_event = SpikeEvent(neuron_id=self.component_id, timestamp=spike_time, amplitude=1.0)

        # Add to spike history
        self.spike_history.append(spike_event)

        # Propagate spike to output synapses
        for synapse in self.output_synapses:
            synapse.receive_spike(spike_event)

        self.logger.debug(f"Neuron {self.component_id} spiked at time {spike_time:.6f}s")

    def _update_adaptation(self, dt: float) -> None:
        """Update adaptation current."""
        tau_adapt = self.parameters["adaptation_tau"]
        adaptation_decay = np.exp(-dt / tau_adapt)

        # Decay adaptation current
        self.state["adaptation_current"] *= adaptation_decay

        # Add adaptation from recent spike
        if (self.current_time - self.state["last_spike_time"]) < dt:
            adaptation_strength = self.parameters["adaptation_strength"]
            self.state["adaptation_current"] += adaptation_strength

    def reset(self) -> None:
        """Reset neuron to initial state."""
        self.state["membrane_potential"] = self.parameters["v_rest"]
        self.state["input_current"] = 0.0
        self.state["spike_times"] = []
        self.state["last_spike_time"] = -np.inf
        self.state["refractory_until"] = 0.0
        self.state["adaptation_current"] = 0.0
        self.spike_threshold_crossed = False
        self.current_time = 0.0


class SynapseBase(NeuralBase):
    """
    Base class for synaptic connections.

    Provides common synapse functionality:
    - Weight dynamics
    - Delay handling
    - Plasticity mechanisms
    """

    def __init__(self, synapse_id: int, pre_neuron: NeuronBase, post_neuron: NeuronBase, **kwargs):
        """Initialize synapse."""
        super().__init__(synapse_id, **kwargs)

        self.pre_neuron = pre_neuron
        self.post_neuron = post_neuron

        # Initialize synapse state
        self.state.update(
            {
                "weight": 1.0,
                "last_pre_spike": -np.inf,
                "last_post_spike": -np.inf,
                "eligibility_trace": 0.0,
                "delayed_spikes": deque(),
            }
        )

        # Default parameters
        self.parameters.update(
            {
                "initial_weight": 1.0,
                "max_weight": 5.0,
                "min_weight": 0.0,
                "delay": 1.0e-3,  # s
                "plasticity_enabled": True,
                "synapse_type": "excitatory",  # excitatory, inhibitory, modulatory
            }
        )

        # Set initial weight
        self.state["weight"] = self.parameters["initial_weight"]

    @abstractmethod
    def compute_psc(self, spike_event: SpikeEvent) -> float:
        """Compute post-synaptic current from spike event."""
        pass

    def update(self, dt: float) -> None:
        """Update synapse state for one time step."""
        self.current_time += dt

        # Process delayed spikes
        self._process_delayed_spikes()

        # Update plasticity
        if self.parameters["plasticity_enabled"]:
            self._update_plasticity(dt)

        # Record monitoring data
        self._record_variables()

    def receive_spike(self, spike_event: SpikeEvent) -> None:
        """Receive spike from pre-synaptic neuron."""
        # Add delay to spike delivery
        delayed_time = spike_event.timestamp + self.parameters["delay"]
        delayed_spike = SpikeEvent(
            neuron_id=spike_event.neuron_id, timestamp=delayed_time, amplitude=spike_event.amplitude
        )

        self.state["delayed_spikes"].append(delayed_spike)
        self.state["last_pre_spike"] = spike_event.timestamp

    def _process_delayed_spikes(self) -> None:
        """Process spikes that have completed their delay."""
        while (
            self.state["delayed_spikes"]
            and self.state["delayed_spikes"][0].timestamp <= self.current_time
        ):

            spike_event = self.state["delayed_spikes"].popleft()

            # Compute post-synaptic current
            psc = self.compute_psc(spike_event)

            # Apply current to post-synaptic neuron
            self.post_neuron.add_input_current(psc)

    @abstractmethod
    def _update_plasticity(self, dt: float) -> None:
        """Update synaptic plasticity."""
        pass

    def set_weight(self, weight: float) -> None:
        """Set synaptic weight with bounds checking."""
        min_weight = self.parameters["min_weight"]
        max_weight = self.parameters["max_weight"]
        self.state["weight"] = np.clip(weight, min_weight, max_weight)

    def get_weight(self) -> float:
        """Get current synaptic weight."""
        return self.state["weight"]

    def reset(self) -> None:
        """Reset synapse to initial state."""
        self.state["weight"] = self.parameters["initial_weight"]
        self.state["last_pre_spike"] = -np.inf
        self.state["last_post_spike"] = -np.inf
        self.state["eligibility_trace"] = 0.0
        self.state["delayed_spikes"].clear()
        self.current_time = 0.0


class NetworkBase(ABC):
    """
    Base class for neural networks.

    Provides common network functionality:
    - Neuron and synapse management
    - Simulation control
    - Event propagation
    """

    def __init__(self, network_id: int, **kwargs):
        """Initialize network."""
        self.network_id = network_id
        self.name = kwargs.get("name", f"Network_{network_id}")

        # Network components
        self.neurons = {}
        self.synapses = {}

        # Simulation state
        self.current_time = 0.0
        self.time_step = kwargs.get("time_step", 1.0e-3)
        self.is_running = False

        # Event system
        self.global_event_queue = []

        # Monitoring
        self.monitor_enabled = False
        self.recorded_data = {}

        # Thread safety
        self._lock = threading.Lock()

        # Logging
        self.logger = logging.getLogger(f"neuromorphic.{self.name}")

    @abstractmethod
    def build_network(self) -> None:
        """Build network topology."""
        pass

    def add_neuron(self, neuron: NeuronBase) -> None:
        """Add neuron to network."""
        with self._lock:
            self.neurons[neuron.component_id] = neuron

    def add_synapse(self, synapse: SynapseBase) -> None:
        """Add synapse to network."""
        with self._lock:
            self.synapses[synapse.component_id] = synapse

    def remove_neuron(self, neuron_id: int) -> None:
        """Remove neuron from network."""
        with self._lock:
            if neuron_id in self.neurons:
                del self.neurons[neuron_id]

    def remove_synapse(self, synapse_id: int) -> None:
        """Remove synapse from network."""
        with self._lock:
            if synapse_id in self.synapses:
                del self.synapses[synapse_id]

    def step(self) -> None:
        """Execute one simulation time step."""
        # Update all neurons
        for neuron in self.neurons.values():
            if neuron.is_active:
                neuron.update(self.time_step)

        # Update all synapses
        for synapse in self.synapses.values():
            if synapse.is_active:
                synapse.update(self.time_step)

        # Update network time
        self.current_time += self.time_step

    def run(self, duration: float, real_time: bool = False) -> None:
        """Run simulation for specified duration."""
        start_time = time.time()
        target_steps = int(duration / self.time_step)

        self.is_running = True

        try:
            for step_idx in range(target_steps):
                self.step()

                # Real-time simulation
                if real_time:
                    elapsed = time.time() - start_time
                    target_elapsed = step_idx * self.time_step
                    if elapsed < target_elapsed:
                        time.sleep(target_elapsed - elapsed)

                if not self.is_running:
                    break

        except KeyboardInterrupt:
            self.logger.info("Simulation interrupted by user")
        finally:
            self.is_running = False

    def stop(self) -> None:
        """Stop simulation."""
        self.is_running = False

    def reset(self) -> None:
        """Reset network to initial state."""
        with self._lock:
            # Reset all neurons
            for neuron in self.neurons.values():
                neuron.reset()

            # Reset all synapses
            for synapse in self.synapses.values():
                synapse.reset()

            # Reset network state
            self.current_time = 0.0
            self.is_running = False
            self.global_event_queue.clear()

    def get_network_state(self) -> Dict[str, Any]:
        """Get current network state."""
        return {
            "current_time": self.current_time,
            "num_neurons": len(self.neurons),
            "num_synapses": len(self.synapses),
            "is_running": self.is_running,
            "active_neurons": sum(1 for n in self.neurons.values() if n.is_active),
            "active_synapses": sum(1 for s in self.synapses.values() if s.is_active),
        }

    def get_neuron(self, neuron_id: int) -> Optional[NeuronBase]:
        """Get neuron by ID."""
        return self.neurons.get(neuron_id)

    def get_synapse(self, synapse_id: int) -> Optional[SynapseBase]:
        """Get synapse by ID."""
        return self.synapses.get(synapse_id)

    def get_spike_activity(self, time_window: float = None) -> Dict[int, List[float]]:
        """Get spike times for all neurons."""
        spike_activity = {}

        for neuron_id, neuron in self.neurons.items():
            spike_times = neuron.state["spike_times"]

            if time_window:
                # Filter spikes within time window
                recent_spikes = [t for t in spike_times if t > self.current_time - time_window]
                spike_activity[neuron_id] = recent_spikes
            else:
                spike_activity[neuron_id] = spike_times.copy()

        return spike_activity
