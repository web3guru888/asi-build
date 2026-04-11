"""
Homeostatic Regulation System

Implements biological homeostasis mechanisms for maintaining system stability
and optimal operating conditions in bio-inspired cognitive architectures.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..core import BioCognitiveModule, BiologicalMetrics

logger = logging.getLogger(__name__)


class RegulationMode(Enum):
    """Homeostatic regulation modes"""

    STRICT = "strict"
    ADAPTIVE = "adaptive"
    PREDICTIVE = "predictive"
    EMERGENCY = "emergency"


@dataclass
class HomeostaticVariable:
    """Represents a homeostatic variable to be regulated"""

    name: str
    current_value: float
    setpoint: float
    tolerance: float
    min_value: float = 0.0
    max_value: float = 1.0
    regulation_strength: float = 0.1
    adaptation_rate: float = 0.01

    def __post_init__(self):
        self.error_history = []
        self.integral_error = 0.0
        self.derivative_error = 0.0
        self.last_error = 0.0
        self.last_update_time = time.time()

    def calculate_error(self) -> float:
        """Calculate current error from setpoint"""
        return self.setpoint - self.current_value

    def update_pid_terms(self, error: float, dt: float):
        """Update PID control terms"""
        self.integral_error += error * dt
        self.derivative_error = (error - self.last_error) / dt if dt > 0 else 0.0
        self.last_error = error
        self.error_history.append(error)

        # Keep history bounded
        if len(self.error_history) > 100:
            self.error_history.pop(0)


class HomeostaticRegulator(BioCognitiveModule):
    """Main homeostatic regulation system"""

    def __init__(
        self,
        name: str = "HomeostaticRegulator",
        regulation_mode: RegulationMode = RegulationMode.ADAPTIVE,
    ):
        super().__init__(name)

        self.regulation_mode = regulation_mode
        self.variables: Dict[str, HomeostaticVariable] = {}

        # PID controller parameters
        self.kp = 1.0  # Proportional gain
        self.ki = 0.1  # Integral gain
        self.kd = 0.05  # Derivative gain

        # System state
        self.system_stability = 1.0
        self.total_regulation_effort = 0.0
        self.emergency_threshold = 0.8

        # Initialize default variables
        self._initialize_default_variables()

        logger.info(f"Initialized homeostatic regulator with {regulation_mode.value} mode")

    def _initialize_default_variables(self):
        """Initialize default homeostatic variables"""
        default_vars = {
            "energy_level": HomeostaticVariable(
                name="energy_level",
                current_value=0.7,
                setpoint=0.7,
                tolerance=0.1,
                min_value=0.0,
                max_value=1.0,
            ),
            "arousal_level": HomeostaticVariable(
                name="arousal_level",
                current_value=0.5,
                setpoint=0.5,
                tolerance=0.2,
                min_value=0.0,
                max_value=1.0,
            ),
            "attention_focus": HomeostaticVariable(
                name="attention_focus",
                current_value=0.6,
                setpoint=0.6,
                tolerance=0.15,
                min_value=0.0,
                max_value=1.0,
            ),
            "emotional_valence": HomeostaticVariable(
                name="emotional_valence",
                current_value=0.0,
                setpoint=0.0,
                tolerance=0.3,
                min_value=-1.0,
                max_value=1.0,
            ),
        }

        for name, var in default_vars.items():
            self.variables[name] = var

    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process homeostatic regulation"""
        current_values = inputs.get("current_values", {})
        disturbances = inputs.get("disturbances", {})
        setpoint_updates = inputs.get("setpoint_updates", {})

        # Update current values
        for var_name, value in current_values.items():
            if var_name in self.variables:
                self.variables[var_name].current_value = value

        # Update setpoints if provided
        for var_name, setpoint in setpoint_updates.items():
            if var_name in self.variables:
                self.variables[var_name].setpoint = setpoint

        # Apply disturbances
        await self._apply_disturbances(disturbances)

        # Perform regulation
        regulation_outputs = await self._regulate_variables()

        # Update system stability
        self._update_system_stability()

        # Check for emergency conditions
        emergency_actions = self._check_emergency_conditions()

        return {
            "regulation_outputs": regulation_outputs,
            "system_stability": self.system_stability,
            "regulation_effort": self.total_regulation_effort,
            "variable_states": self._get_variable_states(),
            "emergency_actions": emergency_actions,
            "homeostatic_balance": self._calculate_overall_balance(),
        }

    async def _apply_disturbances(self, disturbances: Dict[str, float]):
        """Apply environmental disturbances to variables"""
        for var_name, disturbance in disturbances.items():
            if var_name in self.variables:
                var = self.variables[var_name]
                var.current_value += disturbance
                var.current_value = np.clip(var.current_value, var.min_value, var.max_value)

    async def _regulate_variables(self) -> Dict[str, float]:
        """Regulate all homeostatic variables"""
        regulation_outputs = {}
        current_time = time.time()

        for var_name, var in self.variables.items():
            dt = current_time - var.last_update_time
            var.last_update_time = current_time

            # Calculate error
            error = var.calculate_error()

            # Update PID terms
            var.update_pid_terms(error, dt)

            # Calculate regulation output using PID control
            if self.regulation_mode == RegulationMode.STRICT:
                output = self._pid_control(var, error)
            elif self.regulation_mode == RegulationMode.ADAPTIVE:
                output = self._adaptive_control(var, error)
            elif self.regulation_mode == RegulationMode.PREDICTIVE:
                output = self._predictive_control(var, error)
            else:
                output = self._emergency_control(var, error)

            regulation_outputs[var_name] = output

            # Apply regulation to variable
            correction = output * var.regulation_strength
            var.current_value += correction
            var.current_value = np.clip(var.current_value, var.min_value, var.max_value)

        return regulation_outputs

    def _pid_control(self, var: HomeostaticVariable, error: float) -> float:
        """Standard PID control"""
        proportional = self.kp * error
        integral = self.ki * var.integral_error
        derivative = self.kd * var.derivative_error

        return proportional + integral + derivative

    def _adaptive_control(self, var: HomeostaticVariable, error: float) -> float:
        """Adaptive control with parameter adjustment"""
        # Base PID control
        output = self._pid_control(var, error)

        # Adapt parameters based on error history
        if len(var.error_history) > 10:
            recent_errors = var.error_history[-10:]
            error_variance = np.var(recent_errors)

            # Increase gains if error is persistent
            if error_variance < 0.01 and abs(error) > var.tolerance:
                var.regulation_strength = min(1.0, var.regulation_strength * 1.05)
            # Decrease gains if oscillating
            elif error_variance > 0.1:
                var.regulation_strength = max(0.01, var.regulation_strength * 0.95)

        return output

    def _predictive_control(self, var: HomeostaticVariable, error: float) -> float:
        """Predictive control with future error estimation"""
        # Base adaptive control
        output = self._adaptive_control(var, error)

        # Predict future error based on trend
        if len(var.error_history) > 5:
            recent_errors = var.error_history[-5:]
            error_trend = np.polyfit(range(len(recent_errors)), recent_errors, 1)[0]

            # Add predictive term
            prediction_horizon = 3  # time steps
            predicted_error = error + error_trend * prediction_horizon
            predictive_term = 0.2 * predicted_error

            output += predictive_term

        return output

    def _emergency_control(self, var: HomeostaticVariable, error: float) -> float:
        """Emergency control for critical situations"""
        # Aggressive control for large errors
        if abs(error) > var.tolerance * 2:
            emergency_gain = 5.0
            return emergency_gain * error
        else:
            return self._adaptive_control(var, error)

    def _update_system_stability(self):
        """Update overall system stability measure"""
        total_error = 0.0
        total_variables = len(self.variables)

        for var in self.variables.values():
            normalized_error = abs(var.calculate_error()) / (var.max_value - var.min_value)
            total_error += normalized_error

        if total_variables > 0:
            average_error = total_error / total_variables
            self.system_stability = max(0.0, 1.0 - average_error)

        # Update regulation effort
        self.total_regulation_effort = (
            sum(
                abs(var.integral_error) + abs(var.derivative_error)
                for var in self.variables.values()
            )
            / len(self.variables)
            if self.variables
            else 0.0
        )

    def _check_emergency_conditions(self) -> List[str]:
        """Check for emergency conditions requiring immediate action"""
        emergency_actions = []

        # Check individual variables
        for var_name, var in self.variables.items():
            error_magnitude = abs(var.calculate_error()) / (var.max_value - var.min_value)

            if error_magnitude > self.emergency_threshold:
                emergency_actions.append(f"emergency_regulation_{var_name}")

            # Check for extreme values
            if var.current_value <= var.min_value + 0.01:
                emergency_actions.append(f"critical_low_{var_name}")
            elif var.current_value >= var.max_value - 0.01:
                emergency_actions.append(f"critical_high_{var_name}")

        # Check system stability
        if self.system_stability < 0.3:
            emergency_actions.append("system_instability")

        if emergency_actions:
            self.regulation_mode = RegulationMode.EMERGENCY
        elif self.system_stability > 0.8:
            self.regulation_mode = RegulationMode.ADAPTIVE

        return emergency_actions

    def _calculate_overall_balance(self) -> float:
        """Calculate overall homeostatic balance"""
        if not self.variables:
            return 0.0

        balances = []
        for var in self.variables.values():
            error_magnitude = abs(var.calculate_error())
            normalized_error = error_magnitude / (var.tolerance + 1e-6)
            balance = max(0.0, 1.0 - normalized_error)
            balances.append(balance)

        return np.mean(balances)

    def _get_variable_states(self) -> Dict[str, Dict[str, float]]:
        """Get current state of all variables"""
        states = {}
        for var_name, var in self.variables.items():
            states[var_name] = {
                "current_value": var.current_value,
                "setpoint": var.setpoint,
                "error": var.calculate_error(),
                "tolerance": var.tolerance,
                "regulation_strength": var.regulation_strength,
            }
        return states

    def get_biological_metrics(self) -> BiologicalMetrics:
        """Get biological metrics for homeostatic regulator"""
        balance = self._calculate_overall_balance()

        self.metrics = BiologicalMetrics(
            homeostatic_balance=balance,
            energy_efficiency=self.system_stability,
            plasticity_index=self.total_regulation_effort / 10.0,  # Normalize
            neurotransmitter_levels={
                "cortisol": max(0.0, 1.0 - self.system_stability),  # Stress hormone
                "insulin": (
                    self.variables.get(
                        "energy_level", HomeostaticVariable("", 0, 0, 0)
                    ).current_value
                    if "energy_level" in self.variables
                    else 0.5
                ),
                "adrenaline": 1.0 - balance,  # Arousal from imbalance
            },
        )

        return self.metrics

    def update_parameters(self, learning_signal: float):
        """Update regulation parameters based on learning signal"""
        if learning_signal > 0.7:
            # Good performance - maintain current settings
            pass
        elif learning_signal < 0.3:
            # Poor performance - adjust regulation
            self.kp = min(2.0, self.kp * 1.1)
            self.ki = min(0.5, self.ki * 1.05)

        # Adapt tolerance based on performance
        for var in self.variables.values():
            if learning_signal > 0.8:
                var.tolerance = max(0.05, var.tolerance * 0.95)  # Tighten tolerance
            elif learning_signal < 0.2:
                var.tolerance = min(0.5, var.tolerance * 1.05)  # Loosen tolerance

    def add_variable(self, variable: HomeostaticVariable):
        """Add new homeostatic variable"""
        self.variables[variable.name] = variable
        logger.info(f"Added homeostatic variable: {variable.name}")

    def remove_variable(self, variable_name: str):
        """Remove homeostatic variable"""
        if variable_name in self.variables:
            del self.variables[variable_name]
            logger.info(f"Removed homeostatic variable: {variable_name}")

    def set_setpoint(self, variable_name: str, new_setpoint: float):
        """Update setpoint for a variable"""
        if variable_name in self.variables:
            var = self.variables[variable_name]
            var.setpoint = np.clip(new_setpoint, var.min_value, var.max_value)

    def get_regulation_history(self, variable_name: str) -> List[float]:
        """Get regulation history for a variable"""
        if variable_name in self.variables:
            return self.variables[variable_name].error_history.copy()
        return []

    def reset_regulation_state(self):
        """Reset regulation state for all variables"""
        for var in self.variables.values():
            var.error_history.clear()
            var.integral_error = 0.0
            var.derivative_error = 0.0
            var.last_error = 0.0
            var.last_update_time = time.time()

        self.system_stability = 1.0
        self.total_regulation_effort = 0.0

        logger.info("Reset homeostatic regulation state")
