"""
Memristive Device Simulation

Implements realistic memristor models for neuromorphic computing including:
- Voltage-controlled memristors
- Current-controlled memristors
- Synaptic plasticity emulation
- Crossbar array architectures
- Device variability and aging
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class MemristorType(Enum):
    """Types of memristor models."""

    LINEAR_DRIFT = "linear_drift"
    NONLINEAR_DRIFT = "nonlinear_drift"
    VOLTAGE_THRESHOLD = "voltage_threshold"
    BIOLEK = "biolek"
    TEAM = "team"
    VTEAM = "vteam"


@dataclass
class MemristorParams:
    """Parameters for memristor device models."""

    # Physical parameters
    ron: float = 100.0  # Low resistance state (Ohms)
    roff: float = 16000.0  # High resistance state (Ohms)
    d: float = 10.0e-9  # Device thickness (m)
    mu_v: float = 1.0e-14  # Mobility (m^2/V/s)

    # Nonlinear parameters
    p: float = 1.0  # Nonlinearity parameter
    j: float = 1  # Window function parameter

    # Threshold parameters
    v_on: float = 1.0  # Turn-on voltage (V)
    v_off: float = -1.0  # Turn-off voltage (V)
    k_on: float = 1.0e-4  # On switching rate
    k_off: float = 1.0e-4  # Off switching rate

    # Noise and variability
    resistance_variance: float = 0.1  # Resistance variation
    switching_variance: float = 0.1  # Switching variation
    rtc_variance: float = 0.05  # Retention/aging variation

    # Temperature effects
    temp_coefficient: float = 0.002  # Resistance temperature coefficient
    activation_energy: float = 0.8  # eV


class MemristiveDevice:
    """
    Single memristive device simulation with realistic physics.

    Features:
    - Multiple memristor models
    - Device-to-device variations
    - Temperature effects
    - Aging and retention
    - Noise modeling
    """

    def __init__(
        self,
        device_id: int,
        memristor_type: MemristorType,
        params: MemristorParams,
        initial_state: float = 0.5,
    ):
        """Initialize memristive device."""
        self.device_id = device_id
        self.memristor_type = memristor_type
        self.params = params

        # Device state
        self.state = np.clip(initial_state, 0.0, 1.0)  # Normalized state [0,1]
        self.resistance = self._calculate_resistance()

        # History tracking
        self.state_history = [self.state]
        self.voltage_history = []
        self.current_history = []

        # Device variations
        self._apply_device_variations()

        # Environmental conditions
        self.temperature = 298.15  # Kelvin (25°C)
        self.age = 0.0  # Device age in seconds

        # Statistics
        self.write_cycles = 0
        self.total_energy = 0.0

        # Logging
        self.logger = logging.getLogger(f"memristor_{device_id}")

    def apply_voltage(self, voltage: float, duration: float) -> Tuple[float, float]:
        """Apply voltage and return current and resistance change."""
        start_resistance = self.resistance

        # Calculate current
        current = voltage / self.resistance

        # Update device state based on model
        if self.memristor_type == MemristorType.LINEAR_DRIFT:
            self._update_linear_drift(voltage, duration)
        elif self.memristor_type == MemristorType.NONLINEAR_DRIFT:
            self._update_nonlinear_drift(voltage, duration)
        elif self.memristor_type == MemristorType.VOLTAGE_THRESHOLD:
            self._update_voltage_threshold(voltage, duration)
        elif self.memristor_type == MemristorType.BIOLEK:
            self._update_biolek(voltage, current, duration)
        elif self.memristor_type == MemristorType.TEAM:
            self._update_team(voltage, duration)
        elif self.memristor_type == MemristorType.VTEAM:
            self._update_vteam(voltage, duration)

        # Apply environmental effects
        self._apply_temperature_effects()
        self._apply_aging_effects(duration)
        self._apply_noise()

        # Update resistance
        self.resistance = self._calculate_resistance()

        # Record history
        self.state_history.append(self.state)
        self.voltage_history.append(voltage)
        self.current_history.append(current)

        # Limit history length
        if len(self.state_history) > 1000:
            self.state_history = self.state_history[-500:]
            self.voltage_history = self.voltage_history[-500:]
            self.current_history = self.current_history[-500:]

        # Update statistics
        if abs(start_resistance - self.resistance) > 0.01 * start_resistance:
            self.write_cycles += 1

        energy = abs(voltage * current * duration)
        self.total_energy += energy

        self.age += duration

        return current, self.resistance - start_resistance

    def set_state(self, new_state: float) -> None:
        """Directly set device state (for initialization/testing)."""
        self.state = np.clip(new_state, 0.0, 1.0)
        self.resistance = self._calculate_resistance()

    def get_conductance(self) -> float:
        """Get device conductance."""
        return 1.0 / self.resistance

    def get_device_info(self) -> Dict[str, Any]:
        """Get comprehensive device information."""
        return {
            "device_id": self.device_id,
            "type": self.memristor_type.value,
            "state": self.state,
            "resistance": self.resistance,
            "conductance": self.get_conductance(),
            "temperature": self.temperature,
            "age": self.age,
            "write_cycles": self.write_cycles,
            "total_energy": self.total_energy,
            "retention_factor": self._calculate_retention_factor(),
        }

    def _calculate_resistance(self) -> float:
        """Calculate resistance from device state."""
        # Clip state to valid range
        state = np.clip(self.state, 1e-6, 1.0 - 1e-6)

        # Linear interpolation between ron and roff
        resistance = self.params.ron + (self.params.roff - self.params.ron) * (1.0 - state)

        return max(resistance, self.params.ron)

    def _update_linear_drift(self, voltage: float, dt: float) -> None:
        """Update state using linear drift model."""
        # Hewlett model: dx/dt = (mu_v * Ron / D^2) * i(t)
        current = voltage / self.resistance

        dx_dt = (self.params.mu_v * self.params.ron / (self.params.d**2)) * current

        # Apply window function
        window = self._window_function(self.state)

        self.state += dx_dt * dt * window
        self.state = np.clip(self.state, 0.0, 1.0)

    def _update_nonlinear_drift(self, voltage: float, dt: float) -> None:
        """Update state using nonlinear drift model."""
        current = voltage / self.resistance

        # Nonlinear drift with power law
        dx_dt = (self.params.mu_v * self.params.ron / (self.params.d**2)) * current

        if current > 0:
            dx_dt *= self.state**self.params.p
        else:
            dx_dt *= (1 - self.state) ** self.params.p

        window = self._window_function(self.state)

        self.state += dx_dt * dt * window
        self.state = np.clip(self.state, 0.0, 1.0)

    def _update_voltage_threshold(self, voltage: float, dt: float) -> None:
        """Update state using voltage threshold model."""
        if voltage > self.params.v_on:
            # Set operation
            dx_dt = self.params.k_on * np.sinh(voltage / self.params.v_on)
        elif voltage < self.params.v_off:
            # Reset operation
            dx_dt = -self.params.k_off * np.sinh(abs(voltage) / abs(self.params.v_off))
        else:
            # No switching
            dx_dt = 0.0

        window = self._window_function(self.state)

        self.state += dx_dt * dt * window
        self.state = np.clip(self.state, 0.0, 1.0)

    def _update_biolek(self, voltage: float, current: float, dt: float) -> None:
        """Update state using Biolek model."""
        # Biolek window function includes current direction
        if current >= 0:
            window = self.state * (1 - self.state)
        else:
            window = (1 - self.state) * self.state

        dx_dt = (self.params.mu_v * self.params.ron / (self.params.d**2)) * current

        self.state += dx_dt * dt * window
        self.state = np.clip(self.state, 0.0, 1.0)

    def _update_team(self, voltage: float, dt: float) -> None:
        """Update state using TEAM model."""
        if voltage > 0:
            # Set process
            if self.state < 1.0:
                k = self.params.k_on * np.exp(
                    -self.params.activation_energy / (8.617e-5 * self.temperature)
                )
                dx_dt = k * np.sinh(voltage / self.params.v_on)
            else:
                dx_dt = 0.0
        else:
            # Reset process
            if self.state > 0.0:
                k = self.params.k_off * np.exp(
                    -self.params.activation_energy / (8.617e-5 * self.temperature)
                )
                dx_dt = -k * np.sinh(abs(voltage) / abs(self.params.v_off))
            else:
                dx_dt = 0.0

        self.state += dx_dt * dt
        self.state = np.clip(self.state, 0.0, 1.0)

    def _update_vteam(self, voltage: float, dt: float) -> None:
        """Update state using VTEAM model (voltage threshold adaptive memristor)."""
        # Adaptive threshold based on state
        v_on_eff = self.params.v_on * (1 + 0.1 * self.state)
        v_off_eff = self.params.v_off * (1 + 0.1 * (1 - self.state))

        if voltage > v_on_eff:
            dx_dt = self.params.k_on * np.exp(-(v_on_eff / voltage))
        elif voltage < v_off_eff:
            dx_dt = -self.params.k_off * np.exp(-(abs(v_off_eff) / abs(voltage)))
        else:
            dx_dt = 0.0

        self.state += dx_dt * dt
        self.state = np.clip(self.state, 0.0, 1.0)

    def _window_function(self, x: float) -> float:
        """Window function to model boundary effects."""
        # Joglekar window function
        return 1 - (2 * x - 1) ** (2 * self.params.j)

    def _apply_device_variations(self) -> None:
        """Apply device-to-device variations."""
        # Resistance variations
        ron_var = np.random.normal(1.0, self.params.resistance_variance)
        roff_var = np.random.normal(1.0, self.params.resistance_variance)

        self.params.ron *= max(0.1, ron_var)
        self.params.roff *= max(0.1, roff_var)

        # Switching parameter variations
        k_on_var = np.random.normal(1.0, self.params.switching_variance)
        k_off_var = np.random.normal(1.0, self.params.switching_variance)

        self.params.k_on *= max(0.1, k_on_var)
        self.params.k_off *= max(0.1, k_off_var)

    def _apply_temperature_effects(self) -> None:
        """Apply temperature effects on resistance."""
        # Simple temperature coefficient model
        temp_factor = 1 + self.params.temp_coefficient * (self.temperature - 298.15)

        # Apply to both ron and roff
        self.params.ron *= temp_factor
        self.params.roff *= temp_factor

    def _apply_aging_effects(self, dt: float) -> None:
        """Apply aging effects on device parameters."""
        # Simple aging model - resistance drift over time
        aging_rate = 1e-8  # Fractional change per second

        ron_drift = 1 + aging_rate * self.age * np.random.normal(1.0, self.params.rtc_variance)
        roff_drift = 1 + aging_rate * self.age * np.random.normal(1.0, self.params.rtc_variance)

        self.params.ron *= ron_drift
        self.params.roff *= roff_drift

    def _apply_noise(self) -> None:
        """Apply random noise to device state."""
        # Random telegraph noise and thermal noise
        noise_amplitude = 0.001  # Small noise amplitude

        state_noise = np.random.normal(0, noise_amplitude)
        self.state += state_noise
        self.state = np.clip(self.state, 0.0, 1.0)

    def _calculate_retention_factor(self) -> float:
        """Calculate retention factor based on age and temperature."""
        # Arrhenius model for retention
        boltzmann = 8.617e-5  # eV/K
        retention_time = np.exp(self.params.activation_energy / (boltzmann * self.temperature))

        return np.exp(-self.age / retention_time)


class MemristorArray:
    """
    2D array of memristive devices for crossbar architectures.

    Features:
    - Crossbar array simulation
    - Sneak path modeling
    - Selector device integration
    - Parallel read/write operations
    - Wire resistance effects
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        memristor_type: MemristorType,
        params: MemristorParams,
        wire_resistance: float = 1.0,
    ):
        """Initialize memristor crossbar array."""
        self.rows = rows
        self.cols = cols
        self.wire_resistance = wire_resistance  # Ohms per unit length

        # Create device array
        self.devices = {}
        for i in range(rows):
            for j in range(cols):
                device_id = i * cols + j
                initial_state = np.random.uniform(0.3, 0.7)  # Random initial states

                self.devices[(i, j)] = MemristiveDevice(
                    device_id=device_id,
                    memristor_type=memristor_type,
                    params=params,
                    initial_state=initial_state,
                )

        # Array-level statistics
        self.total_operations = 0
        self.total_energy = 0.0

        # Wire resistance matrix
        self.row_resistances = np.ones(rows) * wire_resistance
        self.col_resistances = np.ones(cols) * wire_resistance

        # Selector devices (optional)
        self.use_selectors = False
        self.selector_resistance = 1000.0  # Ohms

        self.logger = logging.getLogger(f"memristor_array_{rows}x{cols}")

    def write_device(
        self,
        row: int,
        col: int,
        target_state: float,
        write_voltage: float = 2.0,
        write_time: float = 100e-6,
    ) -> bool:
        """Write to a specific device in the array."""
        if not self._validate_address(row, col):
            return False

        device = self.devices[(row, col)]

        # Calculate required voltage considering wire resistance
        effective_voltage = self._calculate_effective_voltage(row, col, write_voltage)

        # Apply voltage to device
        current, resistance_change = device.apply_voltage(effective_voltage, write_time)

        # Model sneak paths
        sneak_current = self._calculate_sneak_paths(row, col, write_voltage)

        # Update statistics
        self.total_operations += 1
        energy = abs(effective_voltage * (current + sneak_current) * write_time)
        self.total_energy += energy

        return True

    def read_device(self, row: int, col: int, read_voltage: float = 0.1) -> Optional[float]:
        """Read resistance of a specific device."""
        if not self._validate_address(row, col):
            return None

        device = self.devices[(row, col)]

        # Calculate effective voltage
        effective_voltage = self._calculate_effective_voltage(row, col, read_voltage)

        # Calculate current (without changing device state)
        current = effective_voltage / device.resistance

        # Add sneak path effects
        sneak_current = self._calculate_sneak_paths(row, col, read_voltage)
        total_current = current + sneak_current

        # Calculate apparent resistance
        apparent_resistance = read_voltage / total_current if total_current > 0 else float("inf")

        return apparent_resistance

    def write_row(self, row: int, target_states: List[float], write_voltage: float = 2.0) -> bool:
        """Write to entire row simultaneously."""
        if row >= self.rows or len(target_states) != self.cols:
            return False

        success = True
        for col, target_state in enumerate(target_states):
            if not self.write_device(row, col, target_state, write_voltage):
                success = False

        return success

    def read_row(self, row: int, read_voltage: float = 0.1) -> List[float]:
        """Read entire row simultaneously."""
        if row >= self.rows:
            return []

        resistances = []
        for col in range(self.cols):
            resistance = self.read_device(row, col, read_voltage)
            resistances.append(resistance or float("inf"))

        return resistances

    def vector_matrix_multiply(
        self, input_vector: np.ndarray, read_voltage: float = 0.1
    ) -> np.ndarray:
        """Perform analog vector-matrix multiplication."""
        if len(input_vector) != self.rows:
            raise ValueError(f"Input vector length {len(input_vector)} != array rows {self.rows}")

        output_currents = np.zeros(self.cols)

        for row in range(self.rows):
            row_voltage = input_vector[row] * read_voltage

            for col in range(self.cols):
                device = self.devices[(row, col)]

                # Calculate current through device
                effective_voltage = self._calculate_effective_voltage(row, col, row_voltage)
                current = effective_voltage / device.resistance

                output_currents[col] += current

        return output_currents

    def get_conductance_matrix(self) -> np.ndarray:
        """Get conductance matrix of all devices."""
        conductances = np.zeros((self.rows, self.cols))

        for row in range(self.rows):
            for col in range(self.cols):
                device = self.devices[(row, col)]
                conductances[row, col] = device.get_conductance()

        return conductances

    def get_resistance_matrix(self) -> np.ndarray:
        """Get resistance matrix of all devices."""
        resistances = np.zeros((self.rows, self.cols))

        for row in range(self.rows):
            for col in range(self.cols):
                device = self.devices[(row, col)]
                resistances[row, col] = device.resistance

        return resistances

    def get_array_statistics(self) -> Dict[str, Any]:
        """Get comprehensive array statistics."""
        resistances = self.get_resistance_matrix().flatten()
        conductances = self.get_conductance_matrix().flatten()

        total_write_cycles = sum(device.write_cycles for device in self.devices.values())
        total_device_energy = sum(device.total_energy for device in self.devices.values())

        return {
            "dimensions": (self.rows, self.cols),
            "total_devices": len(self.devices),
            "resistance_stats": {
                "mean": np.mean(resistances),
                "std": np.std(resistances),
                "min": np.min(resistances),
                "max": np.max(resistances),
            },
            "conductance_stats": {
                "mean": np.mean(conductances),
                "std": np.std(conductances),
                "min": np.min(conductances),
                "max": np.max(conductances),
            },
            "operations": {
                "total_operations": self.total_operations,
                "total_write_cycles": total_write_cycles,
                "avg_write_cycles_per_device": total_write_cycles / len(self.devices),
            },
            "energy": {
                "total_array_energy": self.total_energy,
                "total_device_energy": total_device_energy,
                "avg_energy_per_operation": self.total_energy / max(self.total_operations, 1),
            },
        }

    def _validate_address(self, row: int, col: int) -> bool:
        """Validate array address."""
        return 0 <= row < self.rows and 0 <= col < self.cols

    def _calculate_effective_voltage(self, row: int, col: int, applied_voltage: float) -> float:
        """Calculate effective voltage at device considering wire resistance."""
        # Simple wire resistance model
        row_drop = self.row_resistances[row] * 1e-3  # Assume 1mA current
        col_drop = self.col_resistances[col] * 1e-3

        effective_voltage = applied_voltage - row_drop - col_drop

        return max(effective_voltage, 0.0)

    def _calculate_sneak_paths(
        self, target_row: int, target_col: int, applied_voltage: float
    ) -> float:
        """Calculate sneak path currents in crossbar array."""
        # Simplified sneak path model
        # In reality, this requires solving the full resistive network

        total_sneak_current = 0.0

        # Consider immediate neighbors
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue

                neighbor_row = target_row + dr
                neighbor_col = target_col + dc

                if self._validate_address(neighbor_row, neighbor_col):
                    neighbor_device = self.devices[(neighbor_row, neighbor_col)]

                    # Estimate sneak current through this path
                    path_resistance = neighbor_device.resistance + 2 * self.wire_resistance
                    sneak_current = applied_voltage / path_resistance

                    total_sneak_current += abs(sneak_current) * 0.1  # Reduced contribution

        return total_sneak_current
