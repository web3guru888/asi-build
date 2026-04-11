"""
Spike-Timing Dependent Plasticity (STDP) Implementation

Implements various STDP learning rules that modify synaptic strengths
based on the precise timing of pre- and post-synaptic spikes.
"""

import logging
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class STDPParameters:
    """Parameters for STDP learning rules."""

    # Basic STDP parameters
    tau_plus: float = 20.0e-3  # Pre-synaptic time constant (s)
    tau_minus: float = 20.0e-3  # Post-synaptic time constant (s)
    a_plus: float = 0.01  # LTP amplitude
    a_minus: float = 0.012  # LTD amplitude (typically slightly larger)

    # Weight bounds
    w_min: float = 0.0  # Minimum weight
    w_max: float = 1.0  # Maximum weight

    # Multiplicative factors
    mu_plus: float = 0.0  # LTP multiplicative factor
    mu_minus: float = 0.0  # LTD multiplicative factor

    # Learning rate modulation
    learning_rate: float = 1.0  # Global learning rate multiplier

    # Eligibility trace parameters
    trace_decay: float = 0.95  # Eligibility trace decay factor

    # Homeostatic parameters
    target_rate: float = 5.0  # Target firing rate (Hz)
    homeostatic_scaling: bool = False

    # Metaplasticity parameters
    meta_plasticity: bool = False
    meta_tau: float = 1000.0e-3  # Metaplasticity time constant


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
        self.pre_traces = {}  # Pre-synaptic traces
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
    def update_weight(
        self, synapse_id: int, pre_spike_time: float, post_spike_time: float, current_weight: float
    ) -> float:
        """Update synaptic weight based on spike timing."""
        pass

    def process_pre_spike(
        self, synapse_id: int, spike_time: float, post_neuron_id: int, current_weight: float
    ) -> float:
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
                    # LTD (pre after post)
                    weight_change -= self._calculate_ltd(dt, current_weight)

        # Apply weight change
        new_weight = self._apply_weight_change(current_weight, weight_change)

        # Track statistics
        if weight_change < 0:
            self.ltd_events += 1

        return new_weight

    def process_post_spike(
        self, post_neuron_id: int, spike_time: float, connected_synapses: List[Tuple[int, float]]
    ) -> List[Tuple[int, float]]:
        """Process post-synaptic spike for STDP."""
        # Update post-synaptic trace
        self._update_post_trace(post_neuron_id, spike_time)

        # Add to spike history
        if post_neuron_id not in self.post_spike_history:
            self.post_spike_history[post_neuron_id] = deque(maxlen=100)
        self.post_spike_history[post_neuron_id].append(spike_time)

        # Update firing rate estimate
        self._update_firing_rate(post_neuron_id, spike_time)

        # Process all connected synapses
        updated_weights = []

        for synapse_id, current_weight in connected_synapses:
            weight_change = 0.0

            # Look for recent pre-synaptic spikes for LTP
            if synapse_id in self.pre_spike_history:
                for pre_time in self.pre_spike_history[synapse_id]:
                    dt = spike_time - pre_time

                    if dt > 0 and dt <= 5 * self.params.tau_plus:
                        # LTP (pre before post)
                        weight_change += self._calculate_ltp(dt, current_weight)

            # Apply weight change
            new_weight = self._apply_weight_change(current_weight, weight_change)
            updated_weights.append((synapse_id, new_weight))

            # Track statistics
            if weight_change > 0:
                self.ltp_events += 1

        return updated_weights

    def _calculate_ltp(self, dt: float, current_weight: float) -> float:
        """Calculate LTP weight change."""
        # Exponential STDP window
        ltp_amplitude = self.params.a_plus * np.exp(-dt / self.params.tau_plus)

        # Apply multiplicative scaling if enabled
        if self.params.mu_plus > 0:
            ltp_amplitude *= (self.params.w_max - current_weight) ** self.params.mu_plus

        return ltp_amplitude * self.params.learning_rate

    def _calculate_ltd(self, dt: float, current_weight: float) -> float:
        """Calculate LTD weight change."""
        # Exponential STDP window
        ltd_amplitude = self.params.a_minus * np.exp(-dt / self.params.tau_minus)

        # Apply multiplicative scaling if enabled
        if self.params.mu_minus > 0:
            ltd_amplitude *= (current_weight - self.params.w_min) ** self.params.mu_minus

        return ltd_amplitude * self.params.learning_rate

    def _apply_weight_change(self, current_weight: float, weight_change: float) -> float:
        """Apply weight change with bounds checking."""
        new_weight = current_weight + weight_change

        # Apply bounds
        new_weight = np.clip(new_weight, self.params.w_min, self.params.w_max)

        # Apply homeostatic scaling if enabled
        if self.params.homeostatic_scaling:
            new_weight = self._apply_homeostatic_scaling(new_weight)

        # Track total weight change
        actual_change = new_weight - current_weight
        self.total_weight_change += abs(actual_change)

        return new_weight

    def _update_pre_trace(self, synapse_id: int, spike_time: float) -> None:
        """Update pre-synaptic eligibility trace."""
        if synapse_id not in self.pre_traces:
            self.pre_traces[synapse_id] = {"value": 0.0, "last_update": 0.0}

        trace = self.pre_traces[synapse_id]

        # Decay trace
        dt = spike_time - trace["last_update"]
        trace["value"] *= np.exp(-dt / self.params.tau_plus)

        # Add spike contribution
        trace["value"] += 1.0
        trace["last_update"] = spike_time

    def _update_post_trace(self, neuron_id: int, spike_time: float) -> None:
        """Update post-synaptic eligibility trace."""
        if neuron_id not in self.post_traces:
            self.post_traces[neuron_id] = {"value": 0.0, "last_update": 0.0}

        trace = self.post_traces[neuron_id]

        # Decay trace
        dt = spike_time - trace["last_update"]
        trace["value"] *= np.exp(-dt / self.params.tau_minus)

        # Add spike contribution
        trace["value"] += 1.0
        trace["last_update"] = spike_time

    def _update_firing_rate(self, neuron_id: int, spike_time: float) -> None:
        """Update firing rate estimate for homeostatic plasticity."""
        if neuron_id not in self.rate_estimates:
            self.rate_estimates[neuron_id] = {"rate": 0.0, "last_spike": 0.0, "spike_count": 0}

        estimate = self.rate_estimates[neuron_id]

        # Simple exponential moving average
        time_window = 1.0  # 1 second window
        alpha = 0.1  # Update rate

        if estimate["last_spike"] > 0:
            isi = spike_time - estimate["last_spike"]
            instant_rate = 1.0 / isi if isi > 0 else 0.0

            estimate["rate"] = (1 - alpha) * estimate["rate"] + alpha * instant_rate

        estimate["last_spike"] = spike_time
        estimate["spike_count"] += 1

    def _apply_homeostatic_scaling(self, weight: float) -> float:
        """Apply homeostatic scaling to maintain target firing rates."""
        # This is a simplified implementation
        # Real homeostatic scaling would consider network-wide activity
        return weight

    def get_trace_value(
        self, synapse_id: int, current_time: float, trace_type: str = "pre"
    ) -> float:
        """Get current eligibility trace value."""
        traces = self.pre_traces if trace_type == "pre" else self.post_traces

        if synapse_id not in traces:
            return 0.0

        trace = traces[synapse_id]
        dt = current_time - trace["last_update"]

        # Decay trace to current time
        tau = self.params.tau_plus if trace_type == "pre" else self.params.tau_minus
        current_value = trace["value"] * np.exp(-dt / tau)

        return current_value

    def get_statistics(self) -> Dict[str, Any]:
        """Get STDP learning statistics."""
        total_events = self.ltp_events + self.ltd_events

        return {
            "ltp_events": self.ltp_events,
            "ltd_events": self.ltd_events,
            "total_events": total_events,
            "ltp_ratio": self.ltp_events / max(total_events, 1),
            "total_weight_change": self.total_weight_change,
            "avg_weight_change": self.total_weight_change / max(total_events, 1),
            "active_traces": len(self.pre_traces) + len(self.post_traces),
            "tracked_neurons": len(self.rate_estimates),
        }

    def reset(self) -> None:
        """Reset STDP learning state."""
        self.pre_traces.clear()
        self.post_traces.clear()
        self.pre_spike_history.clear()
        self.post_spike_history.clear()
        self.weight_changes.clear()
        self.firing_rates.clear()
        self.rate_estimates.clear()
        self.meta_variables.clear()

        self.total_weight_change = 0.0
        self.ltp_events = 0
        self.ltd_events = 0
        self.update_count = 0


class PairSTDP(STDPLearning):
    """Standard pairwise STDP implementation."""

    def update_weight(
        self, synapse_id: int, pre_spike_time: float, post_spike_time: float, current_weight: float
    ) -> float:
        """Update weight using pairwise STDP rule."""
        dt = post_spike_time - pre_spike_time

        if dt > 0:
            # LTP: pre before post
            if dt <= 5 * self.params.tau_plus:
                weight_change = self._calculate_ltp(dt, current_weight)
            else:
                weight_change = 0.0
        else:
            # LTD: post before pre
            if abs(dt) <= 5 * self.params.tau_minus:
                weight_change = -self._calculate_ltd(abs(dt), current_weight)
            else:
                weight_change = 0.0

        return self._apply_weight_change(current_weight, weight_change)


class TripletSTDP(STDPLearning):
    """Triplet STDP implementation with three-spike interactions."""

    def __init__(self, params: STDPParameters):
        super().__init__(params)

        # Additional parameters for triplet STDP
        self.tau_x = 15.0e-3  # Triplet time constant
        self.tau_y = 30.0e-3  # Triplet time constant
        self.a2_plus = 7.5e-5  # Triplet LTP amplitude
        self.a2_minus = 7e-3  # Triplet LTD amplitude

        # Triplet traces
        self.r1_traces = {}  # First-order pre traces
        self.r2_traces = {}  # Second-order pre traces
        self.o1_traces = {}  # First-order post traces
        self.o2_traces = {}  # Second-order post traces

    def update_weight(
        self, synapse_id: int, pre_spike_time: float, post_spike_time: float, current_weight: float
    ) -> float:
        """Update weight using triplet STDP rule."""
        dt = post_spike_time - pre_spike_time

        # Standard pairwise term
        if dt > 0:
            pair_change = self._calculate_ltp(dt, current_weight)
        else:
            pair_change = -self._calculate_ltd(abs(dt), current_weight)

        # Triplet terms (simplified)
        triplet_change = self._calculate_triplet_change(
            synapse_id, pre_spike_time, post_spike_time, current_weight
        )

        total_change = pair_change + triplet_change

        return self._apply_weight_change(current_weight, total_change)

    def _calculate_triplet_change(
        self, synapse_id: int, pre_spike_time: float, post_spike_time: float, current_weight: float
    ) -> float:
        """Calculate triplet STDP contribution."""
        # This is a simplified triplet calculation
        # Full implementation would track all three-spike combinations

        # Get trace values
        r1 = self.get_trace_value(synapse_id, pre_spike_time, "pre")
        o1 = self.get_trace_value(synapse_id, post_spike_time, "post")

        dt = post_spike_time - pre_spike_time

        if dt > 0:
            # Triplet LTP
            triplet_ltp = self.a2_plus * r1 * np.exp(-dt / self.tau_y)
            return triplet_ltp
        else:
            # Triplet LTD
            triplet_ltd = self.a2_minus * o1 * np.exp(dt / self.tau_x)
            return -triplet_ltd


class VoltageSTDP(STDPLearning):
    """Voltage-based STDP that depends on postsynaptic membrane potential."""

    def __init__(self, params: STDPParameters):
        super().__init__(params)

        # Voltage thresholds
        self.v_thresh = -50.0e-3  # LTP threshold
        self.v_ltd = -70.0e-3  # LTD threshold

        # Voltage scaling factors
        self.voltage_scaling = True
        self.v_scale_factor = 10.0

    def update_weight_with_voltage(
        self, synapse_id: int, pre_spike_time: float, post_voltage: float, current_weight: float
    ) -> float:
        """Update weight based on pre-spike time and post-synaptic voltage."""
        # Voltage-dependent plasticity
        if post_voltage > self.v_thresh:
            # LTP regime
            voltage_factor = (post_voltage - self.v_thresh) * self.v_scale_factor
            weight_change = self.params.a_plus * voltage_factor
        elif post_voltage < self.v_ltd:
            # LTD regime
            voltage_factor = (self.v_ltd - post_voltage) * self.v_scale_factor
            weight_change = -self.params.a_minus * voltage_factor
        else:
            # No plasticity
            weight_change = 0.0

        return self._apply_weight_change(current_weight, weight_change)

    def update_weight(
        self, synapse_id: int, pre_spike_time: float, post_spike_time: float, current_weight: float
    ) -> float:
        """Standard spike-based update (fallback)."""
        # Use standard pairwise STDP if voltage not available
        dt = post_spike_time - pre_spike_time

        if dt > 0:
            weight_change = self._calculate_ltp(dt, current_weight)
        else:
            weight_change = -self._calculate_ltd(abs(dt), current_weight)

        return self._apply_weight_change(current_weight, weight_change)
