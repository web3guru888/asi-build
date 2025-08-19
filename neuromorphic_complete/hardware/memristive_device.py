"""
Memristive Device Simulation

Implements realistic memristor models for neuromorphic computing including:
- Voltage-controlled memristors
- Current-controlled memristors  
- Synaptic plasticity emulation
- Crossbar array architectures
- Device variability and aging
"""

import numpy as np
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

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
    ron: float = 100.0          # Low resistance state (Ohms)
    roff: float = 16000.0       # High resistance state (Ohms)  
    d: float = 10.0e-9          # Device thickness (m)
    mu_v: float = 1.0e-14       # Mobility (m^2/V/s)
    
    # Nonlinear parameters
    p: float = 1.0              # Nonlinearity parameter
    j: float = 1                # Window function parameter
    
    # Threshold parameters
    v_on: float = 1.0           # Turn-on voltage (V)
    v_off: float = -1.0         # Turn-off voltage (V)
    k_on: float = 1.0e-4        # On switching rate
    k_off: float = 1.0e-4       # Off switching rate
    
    # Noise and variability
    resistance_variance: float = 0.1    # Resistance variation
    switching_variance: float = 0.1     # Switching variation
    rtc_variance: float = 0.05          # Retention/aging variation
    
    # Temperature effects
    temp_coefficient: float = 0.002     # Resistance temperature coefficient
    activation_energy: float = 0.8      # eV

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
    
    def __init__(self, device_id: int, memristor_type: MemristorType, 
                 params: MemristorParams, initial_state: float = 0.5):
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
        return {\n            'device_id': self.device_id,\n            'type': self.memristor_type.value,\n            'state': self.state,\n            'resistance': self.resistance,\n            'conductance': self.get_conductance(),\n            'temperature': self.temperature,\n            'age': self.age,\n            'write_cycles': self.write_cycles,\n            'total_energy': self.total_energy,\n            'retention_factor': self._calculate_retention_factor()\n        }\n    \n    def _calculate_resistance(self) -> float:\n        \"\"\"Calculate resistance from device state.\"\"\"\n        # Clip state to valid range\n        state = np.clip(self.state, 1e-6, 1.0 - 1e-6)\n        \n        # Linear interpolation between ron and roff\n        resistance = self.params.ron + (self.params.roff - self.params.ron) * (1.0 - state)\n        \n        return max(resistance, self.params.ron)\n    \n    def _update_linear_drift(self, voltage: float, dt: float) -> None:\n        \"\"\"Update state using linear drift model.\"\"\"\n        # Hewlett model: dx/dt = (mu_v * Ron / D^2) * i(t)\n        current = voltage / self.resistance\n        \n        dx_dt = (self.params.mu_v * self.params.ron / (self.params.d ** 2)) * current\n        \n        # Apply window function\n        window = self._window_function(self.state)\n        \n        self.state += dx_dt * dt * window\n        self.state = np.clip(self.state, 0.0, 1.0)\n    \n    def _update_nonlinear_drift(self, voltage: float, dt: float) -> None:\n        \"\"\"Update state using nonlinear drift model.\"\"\"\n        current = voltage / self.resistance\n        \n        # Nonlinear drift with power law\n        dx_dt = (self.params.mu_v * self.params.ron / (self.params.d ** 2)) * current\n        \n        if current > 0:\n            dx_dt *= (self.state ** self.params.p)\n        else:\n            dx_dt *= ((1 - self.state) ** self.params.p)\n        \n        window = self._window_function(self.state)\n        \n        self.state += dx_dt * dt * window\n        self.state = np.clip(self.state, 0.0, 1.0)\n    \n    def _update_voltage_threshold(self, voltage: float, dt: float) -> None:\n        \"\"\"Update state using voltage threshold model.\"\"\"\n        if voltage > self.params.v_on:\n            # Set operation\n            dx_dt = self.params.k_on * np.sinh(voltage / self.params.v_on)\n        elif voltage < self.params.v_off:\n            # Reset operation\n            dx_dt = -self.params.k_off * np.sinh(abs(voltage) / abs(self.params.v_off))\n        else:\n            # No switching\n            dx_dt = 0.0\n        \n        window = self._window_function(self.state)\n        \n        self.state += dx_dt * dt * window\n        self.state = np.clip(self.state, 0.0, 1.0)\n    \n    def _update_biolek(self, voltage: float, current: float, dt: float) -> None:\n        \"\"\"Update state using Biolek model.\"\"\"\n        # Biolek window function includes current direction\n        if current >= 0:\n            window = self.state * (1 - self.state)\n        else:\n            window = (1 - self.state) * self.state\n        \n        dx_dt = (self.params.mu_v * self.params.ron / (self.params.d ** 2)) * current\n        \n        self.state += dx_dt * dt * window\n        self.state = np.clip(self.state, 0.0, 1.0)\n    \n    def _update_team(self, voltage: float, dt: float) -> None:\n        \"\"\"Update state using TEAM model.\"\"\"\n        if voltage > 0:\n            # Set process\n            if self.state < 1.0:\n                k = self.params.k_on * np.exp(-self.params.activation_energy / (8.617e-5 * self.temperature))\n                dx_dt = k * np.sinh(voltage / self.params.v_on)\n            else:\n                dx_dt = 0.0\n        else:\n            # Reset process\n            if self.state > 0.0:\n                k = self.params.k_off * np.exp(-self.params.activation_energy / (8.617e-5 * self.temperature))\n                dx_dt = -k * np.sinh(abs(voltage) / abs(self.params.v_off))\n            else:\n                dx_dt = 0.0\n        \n        self.state += dx_dt * dt\n        self.state = np.clip(self.state, 0.0, 1.0)\n    \n    def _update_vteam(self, voltage: float, dt: float) -> None:\n        \"\"\"Update state using VTEAM model (voltage threshold adaptive memristor).\"\"\"\n        # Adaptive threshold based on state\n        v_on_eff = self.params.v_on * (1 + 0.1 * self.state)\n        v_off_eff = self.params.v_off * (1 + 0.1 * (1 - self.state))\n        \n        if voltage > v_on_eff:\n            dx_dt = self.params.k_on * np.exp(-(v_on_eff / voltage))\n        elif voltage < v_off_eff:\n            dx_dt = -self.params.k_off * np.exp(-(abs(v_off_eff) / abs(voltage)))\n        else:\n            dx_dt = 0.0\n        \n        self.state += dx_dt * dt\n        self.state = np.clip(self.state, 0.0, 1.0)\n    \n    def _window_function(self, x: float) -> float:\n        \"\"\"Window function to model boundary effects.\"\"\"\n        # Joglekar window function\n        return 1 - (2 * x - 1) ** (2 * self.params.j)\n    \n    def _apply_device_variations(self) -> None:\n        \"\"\"Apply device-to-device variations.\"\"\"\n        # Resistance variations\n        ron_var = np.random.normal(1.0, self.params.resistance_variance)\n        roff_var = np.random.normal(1.0, self.params.resistance_variance)\n        \n        self.params.ron *= max(0.1, ron_var)\n        self.params.roff *= max(0.1, roff_var)\n        \n        # Switching parameter variations\n        k_on_var = np.random.normal(1.0, self.params.switching_variance)\n        k_off_var = np.random.normal(1.0, self.params.switching_variance)\n        \n        self.params.k_on *= max(0.1, k_on_var)\n        self.params.k_off *= max(0.1, k_off_var)\n    \n    def _apply_temperature_effects(self) -> None:\n        \"\"\"Apply temperature effects on resistance.\"\"\"\n        # Simple temperature coefficient model\n        temp_factor = 1 + self.params.temp_coefficient * (self.temperature - 298.15)\n        \n        # Apply to both ron and roff\n        self.params.ron *= temp_factor\n        self.params.roff *= temp_factor\n    \n    def _apply_aging_effects(self, dt: float) -> None:\n        \"\"\"Apply aging effects on device parameters.\"\"\"\n        # Simple aging model - resistance drift over time\n        aging_rate = 1e-8  # Fractional change per second\n        \n        ron_drift = 1 + aging_rate * self.age * np.random.normal(1.0, self.params.rtc_variance)\n        roff_drift = 1 + aging_rate * self.age * np.random.normal(1.0, self.params.rtc_variance)\n        \n        self.params.ron *= ron_drift\n        self.params.roff *= roff_drift\n    \n    def _apply_noise(self) -> None:\n        \"\"\"Apply random noise to device state.\"\"\"\n        # Random telegraph noise and thermal noise\n        noise_amplitude = 0.001  # Small noise amplitude\n        \n        state_noise = np.random.normal(0, noise_amplitude)\n        self.state += state_noise\n        self.state = np.clip(self.state, 0.0, 1.0)\n    \n    def _calculate_retention_factor(self) -> float:\n        \"\"\"Calculate retention factor based on age and temperature.\"\"\"\n        # Arrhenius model for retention\n        boltzmann = 8.617e-5  # eV/K\n        retention_time = np.exp(self.params.activation_energy / (boltzmann * self.temperature))\n        \n        return np.exp(-self.age / retention_time)\n\nclass MemristorArray:\n    \"\"\"\n    2D array of memristive devices for crossbar architectures.\n    \n    Features:\n    - Crossbar array simulation\n    - Sneak path modeling\n    - Selector device integration\n    - Parallel read/write operations\n    - Wire resistance effects\n    \"\"\"\n    \n    def __init__(self, rows: int, cols: int, memristor_type: MemristorType,\n                 params: MemristorParams, wire_resistance: float = 1.0):\n        \"\"\"Initialize memristor crossbar array.\"\"\"\n        self.rows = rows\n        self.cols = cols\n        self.wire_resistance = wire_resistance  # Ohms per unit length\n        \n        # Create device array\n        self.devices = {}\n        for i in range(rows):\n            for j in range(cols):\n                device_id = i * cols + j\n                initial_state = np.random.uniform(0.3, 0.7)  # Random initial states\n                \n                self.devices[(i, j)] = MemristiveDevice(\n                    device_id=device_id,\n                    memristor_type=memristor_type,\n                    params=params,\n                    initial_state=initial_state\n                )\n        \n        # Array-level statistics\n        self.total_operations = 0\n        self.total_energy = 0.0\n        \n        # Wire resistance matrix\n        self.row_resistances = np.ones(rows) * wire_resistance\n        self.col_resistances = np.ones(cols) * wire_resistance\n        \n        # Selector devices (optional)\n        self.use_selectors = False\n        self.selector_resistance = 1000.0  # Ohms\n        \n        self.logger = logging.getLogger(f\"memristor_array_{rows}x{cols}\")\n    \n    def write_device(self, row: int, col: int, target_state: float, \n                    write_voltage: float = 2.0, write_time: float = 100e-6) -> bool:\n        \"\"\"Write to a specific device in the array.\"\"\"\n        if not self._validate_address(row, col):\n            return False\n        \n        device = self.devices[(row, col)]\n        \n        # Calculate required voltage considering wire resistance\n        effective_voltage = self._calculate_effective_voltage(row, col, write_voltage)\n        \n        # Apply voltage to device\n        current, resistance_change = device.apply_voltage(effective_voltage, write_time)\n        \n        # Model sneak paths\n        sneak_current = self._calculate_sneak_paths(row, col, write_voltage)\n        \n        # Update statistics\n        self.total_operations += 1\n        energy = abs(effective_voltage * (current + sneak_current) * write_time)\n        self.total_energy += energy\n        \n        return True\n    \n    def read_device(self, row: int, col: int, read_voltage: float = 0.1) -> Optional[float]:\n        \"\"\"Read resistance of a specific device.\"\"\"\n        if not self._validate_address(row, col):\n            return None\n        \n        device = self.devices[(row, col)]\n        \n        # Calculate effective voltage\n        effective_voltage = self._calculate_effective_voltage(row, col, read_voltage)\n        \n        # Calculate current (without changing device state)\n        current = effective_voltage / device.resistance\n        \n        # Add sneak path effects\n        sneak_current = self._calculate_sneak_paths(row, col, read_voltage)\n        total_current = current + sneak_current\n        \n        # Calculate apparent resistance\n        apparent_resistance = read_voltage / total_current if total_current > 0 else float('inf')\n        \n        return apparent_resistance\n    \n    def write_row(self, row: int, target_states: List[float], \n                 write_voltage: float = 2.0) -> bool:\n        \"\"\"Write to entire row simultaneously.\"\"\"\n        if row >= self.rows or len(target_states) != self.cols:\n            return False\n        \n        success = True\n        for col, target_state in enumerate(target_states):\n            if not self.write_device(row, col, target_state, write_voltage):\n                success = False\n        \n        return success\n    \n    def read_row(self, row: int, read_voltage: float = 0.1) -> List[float]:\n        \"\"\"Read entire row simultaneously.\"\"\"\n        if row >= self.rows:\n            return []\n        \n        resistances = []\n        for col in range(self.cols):\n            resistance = self.read_device(row, col, read_voltage)\n            resistances.append(resistance or float('inf'))\n        \n        return resistances\n    \n    def vector_matrix_multiply(self, input_vector: np.ndarray, \n                              read_voltage: float = 0.1) -> np.ndarray:\n        \"\"\"Perform analog vector-matrix multiplication.\"\"\"\n        if len(input_vector) != self.rows:\n            raise ValueError(f\"Input vector length {len(input_vector)} != array rows {self.rows}\")\n        \n        output_currents = np.zeros(self.cols)\n        \n        for row in range(self.rows):\n            row_voltage = input_vector[row] * read_voltage\n            \n            for col in range(self.cols):\n                device = self.devices[(row, col)]\n                \n                # Calculate current through device\n                effective_voltage = self._calculate_effective_voltage(row, col, row_voltage)\n                current = effective_voltage / device.resistance\n                \n                output_currents[col] += current\n        \n        return output_currents\n    \n    def get_conductance_matrix(self) -> np.ndarray:\n        \"\"\"Get conductance matrix of all devices.\"\"\"\n        conductances = np.zeros((self.rows, self.cols))\n        \n        for row in range(self.rows):\n            for col in range(self.cols):\n                device = self.devices[(row, col)]\n                conductances[row, col] = device.get_conductance()\n        \n        return conductances\n    \n    def get_resistance_matrix(self) -> np.ndarray:\n        \"\"\"Get resistance matrix of all devices.\"\"\"\n        resistances = np.zeros((self.rows, self.cols))\n        \n        for row in range(self.rows):\n            for col in range(self.cols):\n                device = self.devices[(row, col)]\n                resistances[row, col] = device.resistance\n        \n        return resistances\n    \n    def get_array_statistics(self) -> Dict[str, Any]:\n        \"\"\"Get comprehensive array statistics.\"\"\"\n        resistances = self.get_resistance_matrix().flatten()\n        conductances = self.get_conductance_matrix().flatten()\n        \n        total_write_cycles = sum(device.write_cycles for device in self.devices.values())\n        total_device_energy = sum(device.total_energy for device in self.devices.values())\n        \n        return {\n            'dimensions': (self.rows, self.cols),\n            'total_devices': len(self.devices),\n            'resistance_stats': {\n                'mean': np.mean(resistances),\n                'std': np.std(resistances),\n                'min': np.min(resistances),\n                'max': np.max(resistances)\n            },\n            'conductance_stats': {\n                'mean': np.mean(conductances),\n                'std': np.std(conductances),\n                'min': np.min(conductances),\n                'max': np.max(conductances)\n            },\n            'operations': {\n                'total_operations': self.total_operations,\n                'total_write_cycles': total_write_cycles,\n                'avg_write_cycles_per_device': total_write_cycles / len(self.devices)\n            },\n            'energy': {\n                'total_array_energy': self.total_energy,\n                'total_device_energy': total_device_energy,\n                'avg_energy_per_operation': self.total_energy / max(self.total_operations, 1)\n            }\n        }\n    \n    def _validate_address(self, row: int, col: int) -> bool:\n        \"\"\"Validate array address.\"\"\"\n        return 0 <= row < self.rows and 0 <= col < self.cols\n    \n    def _calculate_effective_voltage(self, row: int, col: int, applied_voltage: float) -> float:\n        \"\"\"Calculate effective voltage at device considering wire resistance.\"\"\"\n        # Simple wire resistance model\n        row_drop = self.row_resistances[row] * 1e-3  # Assume 1mA current\n        col_drop = self.col_resistances[col] * 1e-3\n        \n        effective_voltage = applied_voltage - row_drop - col_drop\n        \n        return max(effective_voltage, 0.0)\n    \n    def _calculate_sneak_paths(self, target_row: int, target_col: int, \n                              applied_voltage: float) -> float:\n        \"\"\"Calculate sneak path currents in crossbar array.\"\"\"\n        # Simplified sneak path model\n        # In reality, this requires solving the full resistive network\n        \n        total_sneak_current = 0.0\n        \n        # Consider immediate neighbors\n        for dr in [-1, 0, 1]:\n            for dc in [-1, 0, 1]:\n                if dr == 0 and dc == 0:\n                    continue\n                \n                neighbor_row = target_row + dr\n                neighbor_col = target_col + dc\n                \n                if self._validate_address(neighbor_row, neighbor_col):\n                    neighbor_device = self.devices[(neighbor_row, neighbor_col)]\n                    \n                    # Estimate sneak current through this path\n                    path_resistance = neighbor_device.resistance + 2 * self.wire_resistance\n                    sneak_current = applied_voltage / path_resistance\n                    \n                    total_sneak_current += abs(sneak_current) * 0.1  # Reduced contribution\n        \n        return total_sneak_current"