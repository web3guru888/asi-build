"""
Spike-Timing Dependent Plasticity (STDP) Implementation

Implements various STDP learning rules that modify synaptic strengths
based on the precise timing of pre- and post-synaptic spikes.
"""

import numpy as np
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from collections import deque
import logging

@dataclass
class STDPParameters:
    """Parameters for STDP learning rules."""
    # Basic STDP parameters
    tau_plus: float = 20.0e-3      # Pre-synaptic time constant (s)
    tau_minus: float = 20.0e-3     # Post-synaptic time constant (s)
    a_plus: float = 0.01           # LTP amplitude
    a_minus: float = 0.012         # LTD amplitude (typically slightly larger)
    
    # Weight bounds
    w_min: float = 0.0             # Minimum weight
    w_max: float = 1.0             # Maximum weight
    
    # Multiplicative factors
    mu_plus: float = 0.0           # LTP multiplicative factor
    mu_minus: float = 0.0          # LTD multiplicative factor
    
    # Learning rate modulation
    learning_rate: float = 1.0     # Global learning rate multiplier
    
    # Eligibility trace parameters
    trace_decay: float = 0.95      # Eligibility trace decay factor
    
    # Homeostatic parameters
    target_rate: float = 5.0       # Target firing rate (Hz)
    homeostatic_scaling: bool = False
    
    # Metaplasticity parameters
    meta_plasticity: bool = False
    meta_tau: float = 1000.0e-3    # Metaplasticity time constant

class STDPLearning(ABC):
    """
    Abstract base class for STDP learning implementations.
    
    Provides common functionality for spike-timing dependent plasticity
    including eligibility traces, weight bounds, and homeostatic regulation.
    """
    
    def __init__(self, params: STDPParameters):
        """Initialize STDP learning."""
        self.params = params
        
        # Eligibility traces
        self.pre_traces = {}   # Pre-synaptic traces
        self.post_traces = {}  # Post-synaptic traces
        
        # Spike history for STDP calculations
        self.pre_spike_history = {}
        self.post_spike_history = {}
        
        # Weight change tracking
        self.weight_changes = {}
        self.total_weight_change = 0.0
        
        # Homeostatic tracking
        self.firing_rates = {}
        self.rate_estimates = {}
        
        # Metaplasticity state
        self.meta_variables = {}
        
        # Performance tracking
        self.ltp_events = 0
        self.ltd_events = 0
        self.update_count = 0
        
        # Logging
        self.logger = logging.getLogger(f"stdp.{self.__class__.__name__}")
    
    @abstractmethod
    def update_weight(self, synapse_id: int, pre_spike_time: float, 
                     post_spike_time: float, current_weight: float) -> float:
        """Update synaptic weight based on spike timing."""
        pass
    
    def process_pre_spike(self, synapse_id: int, spike_time: float, 
                         post_neuron_id: int, current_weight: float) -> float:
        """Process pre-synaptic spike for STDP."""
        # Update pre-synaptic trace
        self._update_pre_trace(synapse_id, spike_time)
        
        # Add to spike history
        if synapse_id not in self.pre_spike_history:
            self.pre_spike_history[synapse_id] = deque(maxlen=100)
        self.pre_spike_history[synapse_id].append(spike_time)
        
        # Look for recent post-synaptic spikes for LTD
        weight_change = 0.0
        
        if post_neuron_id in self.post_spike_history:
            for post_time in self.post_spike_history[post_neuron_id]:
                dt = spike_time - post_time
                
                if dt > 0 and dt <= 5 * self.params.tau_minus:
                    # LTD (pre after post)\n                    weight_change -= self._calculate_ltd(dt, current_weight)\n        \n        # Apply weight change\n        new_weight = self._apply_weight_change(current_weight, weight_change)\n        \n        # Track statistics\n        if weight_change < 0:\n            self.ltd_events += 1\n        \n        return new_weight\n    \n    def process_post_spike(self, post_neuron_id: int, spike_time: float, \n                          connected_synapses: List[Tuple[int, float]]) -> List[Tuple[int, float]]:\n        \"\"\"Process post-synaptic spike for STDP.\"\"\"\n        # Update post-synaptic trace\n        self._update_post_trace(post_neuron_id, spike_time)\n        \n        # Add to spike history\n        if post_neuron_id not in self.post_spike_history:\n            self.post_spike_history[post_neuron_id] = deque(maxlen=100)\n        self.post_spike_history[post_neuron_id].append(spike_time)\n        \n        # Update firing rate estimate\n        self._update_firing_rate(post_neuron_id, spike_time)\n        \n        # Process all connected synapses\n        updated_weights = []\n        \n        for synapse_id, current_weight in connected_synapses:\n            weight_change = 0.0\n            \n            # Look for recent pre-synaptic spikes for LTP\n            if synapse_id in self.pre_spike_history:\n                for pre_time in self.pre_spike_history[synapse_id]:\n                    dt = spike_time - pre_time\n                    \n                    if dt > 0 and dt <= 5 * self.params.tau_plus:\n                        # LTP (pre before post)\n                        weight_change += self._calculate_ltp(dt, current_weight)\n            \n            # Apply weight change\n            new_weight = self._apply_weight_change(current_weight, weight_change)\n            updated_weights.append((synapse_id, new_weight))\n            \n            # Track statistics\n            if weight_change > 0:\n                self.ltp_events += 1\n        \n        return updated_weights\n    \n    def _calculate_ltp(self, dt: float, current_weight: float) -> float:\n        \"\"\"Calculate LTP weight change.\"\"\"\n        # Exponential STDP window\n        ltp_amplitude = self.params.a_plus * np.exp(-dt / self.params.tau_plus)\n        \n        # Apply multiplicative scaling if enabled\n        if self.params.mu_plus > 0:\n            ltp_amplitude *= (self.params.w_max - current_weight) ** self.params.mu_plus\n        \n        return ltp_amplitude * self.params.learning_rate\n    \n    def _calculate_ltd(self, dt: float, current_weight: float) -> float:\n        \"\"\"Calculate LTD weight change.\"\"\"\n        # Exponential STDP window\n        ltd_amplitude = self.params.a_minus * np.exp(-dt / self.params.tau_minus)\n        \n        # Apply multiplicative scaling if enabled\n        if self.params.mu_minus > 0:\n            ltd_amplitude *= (current_weight - self.params.w_min) ** self.params.mu_minus\n        \n        return ltd_amplitude * self.params.learning_rate\n    \n    def _apply_weight_change(self, current_weight: float, weight_change: float) -> float:\n        \"\"\"Apply weight change with bounds checking.\"\"\"\n        new_weight = current_weight + weight_change\n        \n        # Apply bounds\n        new_weight = np.clip(new_weight, self.params.w_min, self.params.w_max)\n        \n        # Apply homeostatic scaling if enabled\n        if self.params.homeostatic_scaling:\n            new_weight = self._apply_homeostatic_scaling(new_weight)\n        \n        # Track total weight change\n        actual_change = new_weight - current_weight\n        self.total_weight_change += abs(actual_change)\n        \n        return new_weight\n    \n    def _update_pre_trace(self, synapse_id: int, spike_time: float) -> None:\n        \"\"\"Update pre-synaptic eligibility trace.\"\"\"\n        if synapse_id not in self.pre_traces:\n            self.pre_traces[synapse_id] = {'value': 0.0, 'last_update': 0.0}\n        \n        trace = self.pre_traces[synapse_id]\n        \n        # Decay trace\n        dt = spike_time - trace['last_update']\n        trace['value'] *= np.exp(-dt / self.params.tau_plus)\n        \n        # Add spike contribution\n        trace['value'] += 1.0\n        trace['last_update'] = spike_time\n    \n    def _update_post_trace(self, neuron_id: int, spike_time: float) -> None:\n        \"\"\"Update post-synaptic eligibility trace.\"\"\"\n        if neuron_id not in self.post_traces:\n            self.post_traces[neuron_id] = {'value': 0.0, 'last_update': 0.0}\n        \n        trace = self.post_traces[neuron_id]\n        \n        # Decay trace\n        dt = spike_time - trace['last_update']\n        trace['value'] *= np.exp(-dt / self.params.tau_minus)\n        \n        # Add spike contribution\n        trace['value'] += 1.0\n        trace['last_update'] = spike_time\n    \n    def _update_firing_rate(self, neuron_id: int, spike_time: float) -> None:\n        \"\"\"Update firing rate estimate for homeostatic plasticity.\"\"\"\n        if neuron_id not in self.rate_estimates:\n            self.rate_estimates[neuron_id] = {\n                'rate': 0.0,\n                'last_spike': 0.0,\n                'spike_count': 0\n            }\n        \n        estimate = self.rate_estimates[neuron_id]\n        \n        # Simple exponential moving average\n        time_window = 1.0  # 1 second window\n        alpha = 0.1  # Update rate\n        \n        if estimate['last_spike'] > 0:\n            isi = spike_time - estimate['last_spike']\n            instant_rate = 1.0 / isi if isi > 0 else 0.0\n            \n            estimate['rate'] = (1 - alpha) * estimate['rate'] + alpha * instant_rate\n        \n        estimate['last_spike'] = spike_time\n        estimate['spike_count'] += 1\n    \n    def _apply_homeostatic_scaling(self, weight: float) -> float:\n        \"\"\"Apply homeostatic scaling to maintain target firing rates.\"\"\"\n        # This is a simplified implementation\n        # Real homeostatic scaling would consider network-wide activity\n        return weight\n    \n    def get_trace_value(self, synapse_id: int, current_time: float, \n                       trace_type: str = 'pre') -> float:\n        \"\"\"Get current eligibility trace value.\"\"\"\n        traces = self.pre_traces if trace_type == 'pre' else self.post_traces\n        \n        if synapse_id not in traces:\n            return 0.0\n        \n        trace = traces[synapse_id]\n        dt = current_time - trace['last_update']\n        \n        # Decay trace to current time\n        tau = self.params.tau_plus if trace_type == 'pre' else self.params.tau_minus\n        current_value = trace['value'] * np.exp(-dt / tau)\n        \n        return current_value\n    \n    def get_statistics(self) -> Dict[str, Any]:\n        \"\"\"Get STDP learning statistics.\"\"\"\n        total_events = self.ltp_events + self.ltd_events\n        \n        return {\n            'ltp_events': self.ltp_events,\n            'ltd_events': self.ltd_events,\n            'total_events': total_events,\n            'ltp_ratio': self.ltp_events / max(total_events, 1),\n            'total_weight_change': self.total_weight_change,\n            'avg_weight_change': self.total_weight_change / max(total_events, 1),\n            'active_traces': len(self.pre_traces) + len(self.post_traces),\n            'tracked_neurons': len(self.rate_estimates)\n        }\n    \n    def reset(self) -> None:\n        \"\"\"Reset STDP learning state.\"\"\"\n        self.pre_traces.clear()\n        self.post_traces.clear()\n        self.pre_spike_history.clear()\n        self.post_spike_history.clear()\n        self.weight_changes.clear()\n        self.firing_rates.clear()\n        self.rate_estimates.clear()\n        self.meta_variables.clear()\n        \n        self.total_weight_change = 0.0\n        self.ltp_events = 0\n        self.ltd_events = 0\n        self.update_count = 0\n\nclass PairSTDP(STDPLearning):\n    \"\"\"Standard pairwise STDP implementation.\"\"\"\n    \n    def update_weight(self, synapse_id: int, pre_spike_time: float,\n                     post_spike_time: float, current_weight: float) -> float:\n        \"\"\"Update weight using pairwise STDP rule.\"\"\"\n        dt = post_spike_time - pre_spike_time\n        \n        if dt > 0:\n            # LTP: pre before post\n            if dt <= 5 * self.params.tau_plus:\n                weight_change = self._calculate_ltp(dt, current_weight)\n            else:\n                weight_change = 0.0\n        else:\n            # LTD: post before pre\n            if abs(dt) <= 5 * self.params.tau_minus:\n                weight_change = -self._calculate_ltd(abs(dt), current_weight)\n            else:\n                weight_change = 0.0\n        \n        return self._apply_weight_change(current_weight, weight_change)\n\nclass TripletSTDP(STDPLearning):\n    \"\"\"Triplet STDP implementation with three-spike interactions.\"\"\"\n    \n    def __init__(self, params: STDPParameters):\n        super().__init__(params)\n        \n        # Additional parameters for triplet STDP\n        self.tau_x = 15.0e-3   # Triplet time constant\n        self.tau_y = 30.0e-3   # Triplet time constant\n        self.a2_plus = 7.5e-5  # Triplet LTP amplitude\n        self.a2_minus = 7e-3   # Triplet LTD amplitude\n        \n        # Triplet traces\n        self.r1_traces = {}  # First-order pre traces\n        self.r2_traces = {}  # Second-order pre traces\n        self.o1_traces = {}  # First-order post traces\n        self.o2_traces = {}  # Second-order post traces\n    \n    def update_weight(self, synapse_id: int, pre_spike_time: float,\n                     post_spike_time: float, current_weight: float) -> float:\n        \"\"\"Update weight using triplet STDP rule.\"\"\"\n        dt = post_spike_time - pre_spike_time\n        \n        # Standard pairwise term\n        if dt > 0:\n            pair_change = self._calculate_ltp(dt, current_weight)\n        else:\n            pair_change = -self._calculate_ltd(abs(dt), current_weight)\n        \n        # Triplet terms (simplified)\n        triplet_change = self._calculate_triplet_change(synapse_id, pre_spike_time, \n                                                       post_spike_time, current_weight)\n        \n        total_change = pair_change + triplet_change\n        \n        return self._apply_weight_change(current_weight, total_change)\n    \n    def _calculate_triplet_change(self, synapse_id: int, pre_spike_time: float,\n                                 post_spike_time: float, current_weight: float) -> float:\n        \"\"\"Calculate triplet STDP contribution.\"\"\"\n        # This is a simplified triplet calculation\n        # Full implementation would track all three-spike combinations\n        \n        # Get trace values\n        r1 = self.get_trace_value(synapse_id, pre_spike_time, 'pre')\n        o1 = self.get_trace_value(synapse_id, post_spike_time, 'post')\n        \n        dt = post_spike_time - pre_spike_time\n        \n        if dt > 0:\n            # Triplet LTP\n            triplet_ltp = self.a2_plus * r1 * np.exp(-dt / self.tau_y)\n            return triplet_ltp\n        else:\n            # Triplet LTD\n            triplet_ltd = self.a2_minus * o1 * np.exp(dt / self.tau_x)\n            return -triplet_ltd\n\nclass VoltageSTDP(STDPLearning):\n    \"\"\"Voltage-based STDP that depends on postsynaptic membrane potential.\"\"\"\n    \n    def __init__(self, params: STDPParameters):\n        super().__init__(params)\n        \n        # Voltage thresholds\n        self.v_thresh = -50.0e-3  # LTP threshold\n        self.v_ltd = -70.0e-3     # LTD threshold\n        \n        # Voltage scaling factors\n        self.voltage_scaling = True\n        self.v_scale_factor = 10.0\n    \n    def update_weight_with_voltage(self, synapse_id: int, pre_spike_time: float,\n                                  post_voltage: float, current_weight: float) -> float:\n        \"\"\"Update weight based on pre-spike time and post-synaptic voltage.\"\"\"\n        # Voltage-dependent plasticity\n        if post_voltage > self.v_thresh:\n            # LTP regime\n            voltage_factor = (post_voltage - self.v_thresh) * self.v_scale_factor\n            weight_change = self.params.a_plus * voltage_factor\n        elif post_voltage < self.v_ltd:\n            # LTD regime\n            voltage_factor = (self.v_ltd - post_voltage) * self.v_scale_factor\n            weight_change = -self.params.a_minus * voltage_factor\n        else:\n            # No plasticity\n            weight_change = 0.0\n        \n        return self._apply_weight_change(current_weight, weight_change)\n    \n    def update_weight(self, synapse_id: int, pre_spike_time: float,\n                     post_spike_time: float, current_weight: float) -> float:\n        \"\"\"Standard spike-based update (fallback).\"\"\"\n        # Use standard pairwise STDP if voltage not available\n        dt = post_spike_time - pre_spike_time\n        \n        if dt > 0:\n            weight_change = self._calculate_ltp(dt, current_weight)\n        else:\n            weight_change = -self._calculate_ltd(abs(dt), current_weight)\n        \n        return self._apply_weight_change(current_weight, weight_change)"