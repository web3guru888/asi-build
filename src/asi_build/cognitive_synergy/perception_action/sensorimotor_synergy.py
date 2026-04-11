"""
Sensorimotor Synergy - Perception ↔ Action Coupling
===================================================

Implements the fundamental sensorimotor loops that couple perception and action
in cognitive systems, enabling embodied cognition and adaptive behavior.
"""

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class SensorimotorLoop:
    """Represents a sensorimotor loop"""

    name: str
    perception_modality: str
    action_modality: str
    coupling_strength: float = 0.0
    feedback_delay: float = 0.1  # seconds
    adaptation_rate: float = 0.01
    prediction_accuracy: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class PerceptionState:
    """Current perception state"""

    modality: str
    features: np.ndarray
    confidence: float
    timestamp: float
    prediction: Optional[np.ndarray] = None


@dataclass
class ActionState:
    """Current action state"""

    modality: str
    commands: np.ndarray
    execution_confidence: float
    timestamp: float
    predicted_outcome: Optional[np.ndarray] = None


class SensorimotorSynergy:
    """
    Core sensorimotor synergy implementation.

    Manages perception-action coupling through:
    1. Forward models - Predict sensory consequences of actions
    2. Inverse models - Generate actions from desired outcomes
    3. Sensorimotor adaptation - Learn coupling relationships
    4. Predictive coding - Use predictions to guide perception
    5. Active perception - Use actions to improve perception
    """

    def __init__(
        self,
        coupling_threshold: float = 0.6,
        adaptation_rate: float = 0.01,
        prediction_window: float = 0.5,
    ):
        """
        Initialize sensorimotor synergy.

        Args:
            coupling_threshold: Minimum coupling strength to maintain
            adaptation_rate: Rate of sensorimotor adaptation
            prediction_window: Time window for predictions (seconds)
        """
        self.coupling_threshold = coupling_threshold
        self.adaptation_rate = adaptation_rate
        self.prediction_window = prediction_window

        # Sensorimotor loops
        self.sensorimotor_loops: Dict[str, SensorimotorLoop] = {}

        # State buffers
        self.perception_history = deque(maxlen=1000)
        self.action_history = deque(maxlen=1000)

        # Forward and inverse models
        self.forward_models = {}  # Predict perception from action
        self.inverse_models = {}  # Predict action from desired perception

        # Prediction tracking
        self.predictions = deque(maxlen=500)
        self.prediction_errors = defaultdict(list)

        # Synergy metrics
        self.coupling_strengths = {}
        self.adaptation_rates = {}
        self.prediction_accuracies = {}

        # Control
        self._running = False
        self._update_thread = None

    def add_sensorimotor_loop(
        self, name: str, perception_modality: str, action_modality: str
    ) -> SensorimotorLoop:
        """Add a sensorimotor loop"""
        loop = SensorimotorLoop(
            name=name, perception_modality=perception_modality, action_modality=action_modality
        )

        self.sensorimotor_loops[name] = loop
        self.forward_models[name] = ForwardModel(perception_modality, action_modality)
        self.inverse_models[name] = InverseModel(action_modality, perception_modality)

        return loop

    def process_perception(
        self, modality: str, features: np.ndarray, confidence: float = 1.0
    ) -> Dict[str, Any]:
        """Process perceptual input and update sensorimotor loops"""
        timestamp = time.time()

        # Create perception state
        perception_state = PerceptionState(
            modality=modality, features=features, confidence=confidence, timestamp=timestamp
        )

        # Add to history
        self.perception_history.append(perception_state)

        # Update relevant sensorimotor loops
        responses = {}

        for loop_name, loop in self.sensorimotor_loops.items():
            if loop.perception_modality == modality:
                response = self._process_perception_in_loop(loop, perception_state)
                responses[loop_name] = response

        # Generate predictions for active perception
        predictions = self._generate_perceptual_predictions(modality, features)

        return {
            "processed_perception": perception_state,
            "loop_responses": responses,
            "predictions": predictions,
            "timestamp": timestamp,
        }

    def process_action(
        self, modality: str, commands: np.ndarray, execution_confidence: float = 1.0
    ) -> Dict[str, Any]:
        """Process action commands and update sensorimotor loops"""
        timestamp = time.time()

        # Create action state
        action_state = ActionState(
            modality=modality,
            commands=commands,
            execution_confidence=execution_confidence,
            timestamp=timestamp,
        )

        # Add to history
        self.action_history.append(action_state)

        # Update relevant sensorimotor loops
        responses = {}

        for loop_name, loop in self.sensorimotor_loops.items():
            if loop.action_modality == modality:
                response = self._process_action_in_loop(loop, action_state)
                responses[loop_name] = response

        # Generate sensory predictions from forward models
        sensory_predictions = self._generate_sensory_predictions(modality, commands)

        return {
            "processed_action": action_state,
            "loop_responses": responses,
            "sensory_predictions": sensory_predictions,
            "timestamp": timestamp,
        }

    def _process_perception_in_loop(
        self, loop: SensorimotorLoop, perception: PerceptionState
    ) -> Dict[str, Any]:
        """Process perception within a sensorimotor loop"""

        # Update inverse model with perception
        if loop.name in self.inverse_models:
            suggested_action = self.inverse_models[loop.name].predict(perception.features)

            # Compute coupling strength based on prediction accuracy
            if hasattr(loop, "_last_action_prediction"):
                prediction_error = (
                    np.linalg.norm(perception.features - loop._last_action_prediction)
                    if loop._last_action_prediction is not None
                    else 1.0
                )

                accuracy = 1.0 / (1.0 + prediction_error)
                loop.prediction_accuracy = 0.9 * loop.prediction_accuracy + 0.1 * accuracy
                loop.coupling_strength = loop.prediction_accuracy

        # Active perception - suggest actions to improve perception
        active_perception_actions = self._generate_active_perception_actions(loop, perception)

        return {
            "suggested_action": suggested_action if "suggested_action" in locals() else None,
            "active_perception_actions": active_perception_actions,
            "coupling_strength": loop.coupling_strength,
            "prediction_accuracy": loop.prediction_accuracy,
        }

    def _process_action_in_loop(
        self, loop: SensorimotorLoop, action: ActionState
    ) -> Dict[str, Any]:
        """Process action within a sensorimotor loop"""

        # Generate forward prediction
        if loop.name in self.forward_models:
            predicted_perception = self.forward_models[loop.name].predict(action.commands)
            action.predicted_outcome = predicted_perception

            # Store prediction for later validation
            loop._last_action_prediction = predicted_perception

            self.predictions.append(
                {
                    "loop_name": loop.name,
                    "prediction": predicted_perception,
                    "action": action.commands,
                    "timestamp": action.timestamp,
                }
            )

        # Adaptation based on recent prediction errors
        self._adapt_sensorimotor_loop(loop)

        return {
            "predicted_perception": (
                predicted_perception if "predicted_perception" in locals() else None
            ),
            "adaptation_update": True,
            "coupling_strength": loop.coupling_strength,
        }

    def _generate_perceptual_predictions(
        self, modality: str, features: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Generate predictions about future perceptual states"""
        predictions = []

        # Use recent action history to predict perceptual changes
        recent_actions = [
            a for a in self.action_history if time.time() - a.timestamp < self.prediction_window
        ]

        for action in recent_actions:
            # Find relevant sensorimotor loop
            for loop_name, loop in self.sensorimotor_loops.items():
                if loop.perception_modality == modality and loop.action_modality == action.modality:

                    if loop_name in self.forward_models:
                        predicted_change = self.forward_models[loop_name].predict_change(
                            features, action.commands
                        )

                        predictions.append(
                            {
                                "loop_name": loop_name,
                                "predicted_features": features + predicted_change,
                                "confidence": loop.prediction_accuracy,
                                "time_horizon": self.prediction_window,
                            }
                        )

        return predictions

    def _generate_sensory_predictions(
        self, modality: str, commands: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Generate predictions about sensory outcomes of actions"""
        predictions = []

        for loop_name, loop in self.sensorimotor_loops.items():
            if loop.action_modality == modality:
                if loop_name in self.forward_models:
                    predicted_perception = self.forward_models[loop_name].predict(commands)

                    predictions.append(
                        {
                            "loop_name": loop_name,
                            "modality": loop.perception_modality,
                            "predicted_perception": predicted_perception,
                            "confidence": loop.prediction_accuracy,
                            "delay": loop.feedback_delay,
                        }
                    )

        return predictions

    def _generate_active_perception_actions(
        self, loop: SensorimotorLoop, perception: PerceptionState
    ) -> List[Dict[str, Any]]:
        """Generate actions to improve perception quality"""
        actions = []

        # If perception confidence is low, suggest exploratory actions
        if perception.confidence < 0.7:
            if loop.name in self.inverse_models:
                # Generate actions to reduce uncertainty
                exploratory_actions = self.inverse_models[loop.name].generate_exploratory_actions(
                    perception.features, uncertainty=1.0 - perception.confidence
                )

                for action in exploratory_actions:
                    actions.append(
                        {
                            "type": "exploratory",
                            "action_commands": action,
                            "purpose": "reduce_perceptual_uncertainty",
                            "expected_improvement": 0.2,
                        }
                    )

        # Suggest attention-directing actions
        if hasattr(perception, "attention_focus"):
            attention_actions = self._generate_attention_actions(loop, perception)
            actions.extend(attention_actions)

        return actions

    def _generate_attention_actions(
        self, loop: SensorimotorLoop, perception: PerceptionState
    ) -> List[Dict[str, Any]]:
        """Generate actions to direct attention"""
        actions = []

        # Simple attention-directing actions
        if loop.action_modality in ["motor", "head_movement", "eye_movement"]:
            # Generate small movements to scan environment
            base_action = np.zeros(3)  # Assume 3D action space

            for direction in [np.array([0.1, 0, 0]), np.array([0, 0.1, 0])]:
                actions.append(
                    {
                        "type": "attention_directing",
                        "action_commands": base_action + direction,
                        "purpose": "improve_perception",
                        "expected_improvement": 0.1,
                    }
                )

        return actions

    def _adapt_sensorimotor_loop(self, loop: SensorimotorLoop):
        """Adapt sensorimotor loop based on prediction errors"""
        loop_name = loop.name

        # Get recent prediction errors for this loop
        current_time = time.time()
        recent_errors = [
            error
            for error_time, error in self.prediction_errors[loop_name]
            if current_time - error_time < 60.0  # Last minute
        ]

        if recent_errors:
            # Compute average error
            avg_error = np.mean(recent_errors)

            # Adapt forward model
            if loop_name in self.forward_models:
                self.forward_models[loop_name].adapt(avg_error, loop.adaptation_rate)

            # Adapt inverse model
            if loop_name in self.inverse_models:
                self.inverse_models[loop_name].adapt(avg_error, loop.adaptation_rate)

            # Update loop adaptation rate
            loop.adaptation_rate = min(0.1, loop.adaptation_rate + 0.001 * avg_error)

        loop.last_updated = current_time

    def validate_predictions(self):
        """Validate recent predictions against actual outcomes"""
        current_time = time.time()

        # Check predictions that should have manifested by now
        for prediction in list(self.predictions):
            prediction_age = current_time - prediction["timestamp"]

            if prediction_age > self.prediction_window:
                # Find actual perception outcome
                actual_perception = self._find_matching_perception(prediction, prediction_age)

                if actual_perception is not None:
                    # Compute prediction error
                    predicted = prediction["prediction"]
                    actual = actual_perception.features

                    if predicted.shape == actual.shape:
                        error = np.linalg.norm(predicted - actual)

                        # Store error for adaptation
                        loop_name = prediction["loop_name"]
                        self.prediction_errors[loop_name].append((current_time, error))

                        # Update loop prediction accuracy
                        if loop_name in self.sensorimotor_loops:
                            loop = self.sensorimotor_loops[loop_name]
                            accuracy = 1.0 / (1.0 + error)
                            loop.prediction_accuracy = (
                                0.9 * loop.prediction_accuracy + 0.1 * accuracy
                            )

                # Remove processed prediction
                self.predictions.remove(prediction)

    def _find_matching_perception(
        self, prediction: Dict[str, Any], age: float
    ) -> Optional[PerceptionState]:
        """Find perception that matches a prediction"""
        loop_name = prediction["loop_name"]

        if loop_name not in self.sensorimotor_loops:
            return None

        loop = self.sensorimotor_loops[loop_name]
        target_modality = loop.perception_modality

        # Look for perceptions in the expected time window
        prediction_time = prediction["timestamp"]
        expected_time = prediction_time + loop.feedback_delay

        for perception in reversed(list(self.perception_history)):
            if perception.modality == target_modality:
                time_diff = abs(perception.timestamp - expected_time)

                if time_diff < 0.1:  # Within 100ms tolerance
                    return perception

        return None

    def get_synergy_state(self) -> Dict[str, Any]:
        """Get current sensorimotor synergy state"""
        current_time = time.time()

        loop_states = {}
        for name, loop in self.sensorimotor_loops.items():
            loop_states[name] = {
                "coupling_strength": loop.coupling_strength,
                "prediction_accuracy": loop.prediction_accuracy,
                "adaptation_rate": loop.adaptation_rate,
                "last_updated": loop.last_updated,
                "active": current_time - loop.last_updated < 10.0,
            }

        return {
            "sensorimotor_loops": loop_states,
            "recent_perceptions": len(
                [p for p in self.perception_history if current_time - p.timestamp < 10.0]
            ),
            "recent_actions": len(
                [a for a in self.action_history if current_time - a.timestamp < 10.0]
            ),
            "pending_predictions": len(self.predictions),
            "average_coupling_strength": np.mean(
                [l.coupling_strength for l in self.sensorimotor_loops.values()]
            ),
            "average_prediction_accuracy": np.mean(
                [l.prediction_accuracy for l in self.sensorimotor_loops.values()]
            ),
        }


class ForwardModel:
    """Forward model predicting sensory outcomes from actions"""

    def __init__(self, perception_modality: str, action_modality: str):
        self.perception_modality = perception_modality
        self.action_modality = action_modality

        # Simple linear model parameters (in practice would use neural networks)
        self.weights = np.random.normal(0, 0.1, (10, 10))  # 10D perception from 10D action
        self.bias = np.zeros(10)

        # Learning parameters
        self.learning_rate = 0.01

    def predict(self, action_commands: np.ndarray) -> np.ndarray:
        """Predict sensory outcome from action"""
        # Ensure proper dimensionality
        if len(action_commands) < 10:
            action_input = np.zeros(10)
            action_input[: len(action_commands)] = action_commands
        else:
            action_input = action_commands[:10]

        prediction = np.dot(self.weights, action_input) + self.bias
        return prediction

    def predict_change(
        self, current_perception: np.ndarray, action_commands: np.ndarray
    ) -> np.ndarray:
        """Predict change in perception from action"""
        predicted_perception = self.predict(action_commands)

        if len(current_perception) < 10:
            current_input = np.zeros(10)
            current_input[: len(current_perception)] = current_perception
        else:
            current_input = current_perception[:10]

        change = predicted_perception - current_input
        return change[: len(current_perception)]

    def adapt(self, error: float, learning_rate: float):
        """Adapt model based on prediction error"""
        # Simple adaptation - scale weights slightly
        adaptation_factor = 1.0 - learning_rate * error * 0.1
        self.weights *= adaptation_factor


class InverseModel:
    """Inverse model predicting actions from desired perceptions"""

    def __init__(self, action_modality: str, perception_modality: str):
        self.action_modality = action_modality
        self.perception_modality = perception_modality

        # Simple inverse model parameters
        self.weights = np.random.normal(0, 0.1, (10, 10))  # 10D action from 10D perception
        self.bias = np.zeros(10)

    def predict(self, desired_perception: np.ndarray) -> np.ndarray:
        """Predict action from desired perception"""
        # Ensure proper dimensionality
        if len(desired_perception) < 10:
            perception_input = np.zeros(10)
            perception_input[: len(desired_perception)] = desired_perception
        else:
            perception_input = desired_perception[:10]

        action = np.dot(self.weights, perception_input) + self.bias
        return action

    def generate_exploratory_actions(
        self, current_perception: np.ndarray, uncertainty: float
    ) -> List[np.ndarray]:
        """Generate exploratory actions to reduce uncertainty"""
        base_action = self.predict(current_perception)

        exploratory_actions = []

        # Add noise proportional to uncertainty
        noise_scale = uncertainty * 0.5

        for _ in range(3):  # Generate 3 exploratory actions
            noise = np.random.normal(0, noise_scale, len(base_action))
            exploratory_action = base_action + noise
            exploratory_actions.append(exploratory_action)

        return exploratory_actions

    def adapt(self, error: float, learning_rate: float):
        """Adapt inverse model based on error"""
        adaptation_factor = 1.0 - learning_rate * error * 0.1
        self.weights *= adaptation_factor
