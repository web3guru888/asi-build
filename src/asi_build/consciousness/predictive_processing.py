"""
Predictive Processing Framework

Based on the predictive processing theory of consciousness, this module implements
a hierarchical system where consciousness emerges from the brain's continuous
prediction and error correction processes.

Key components:
- Hierarchical predictive models
- Prediction error signals
- Bayesian inference
- Active inference
- Precision weighting
- Model updating
"""

import math
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import norm

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState


@dataclass
class Prediction:
    """Represents a prediction made by the system"""

    prediction_id: str
    level: int  # Hierarchical level
    prediction_type: str
    predicted_value: Any
    confidence: float
    uncertainty: float
    timestamp: float = field(default_factory=time.time)
    evidence_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "level": self.level,
            "prediction_type": self.prediction_type,
            "predicted_value": self.predicted_value,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "timestamp": self.timestamp,
            "evidence_count": self.evidence_count,
        }


@dataclass
class PredictionError:
    """Represents a prediction error signal"""

    error_id: str
    prediction_id: str
    expected: Any
    observed: Any
    error_magnitude: float
    precision: float  # Inverse variance
    level: int
    timestamp: float = field(default_factory=time.time)

    def calculate_surprise(self) -> float:
        """Calculate surprise (negative log probability)"""
        if self.precision > 0:
            return -math.log(
                max(1e-10, norm.pdf(self.error_magnitude, 0, 1 / math.sqrt(self.precision)))
            )
        return 0.0


@dataclass
class HierarchicalLevel:
    """Represents a level in the predictive hierarchy"""

    level_id: int
    name: str
    temporal_scale: float  # Time scale this level operates on
    spatial_scale: float  # Spatial scale this level covers
    active_predictions: Dict[str, Prediction] = field(default_factory=dict)
    prediction_errors: List[PredictionError] = field(default_factory=list)
    precision_weights: Dict[str, float] = field(default_factory=dict)
    learning_rate: float = 0.1

    def add_prediction(self, prediction: Prediction) -> None:
        """Add a prediction to this level"""
        self.active_predictions[prediction.prediction_id] = prediction

    def get_average_precision(self) -> float:
        """Get average precision at this level"""
        if not self.precision_weights:
            return 1.0
        return sum(self.precision_weights.values()) / len(self.precision_weights)


class PredictiveModel:
    """Base class for predictive models"""

    def __init__(self, model_id: str, model_type: str):
        self.model_id = model_id
        self.model_type = model_type
        self.parameters: Dict[str, float] = {}
        self.last_updated = time.time()

    def predict(self, input_data: Dict[str, Any]) -> Prediction:
        """Make a prediction based on input data"""
        raise NotImplementedError

    def update(self, error: PredictionError) -> None:
        """Update model based on prediction error"""
        raise NotImplementedError


class SimpleLinearModel(PredictiveModel):
    """Simple linear predictive model"""

    def __init__(self, model_id: str, input_dims: int):
        super().__init__(model_id, "linear")
        self.weights = np.random.normal(0, 0.1, input_dims)
        self.bias = 0.0
        self.input_dims = input_dims

    def predict(self, input_data: Dict[str, Any]) -> Prediction:
        """Make linear prediction"""
        inputs = input_data.get("inputs", np.zeros(self.input_dims))
        if len(inputs) != self.input_dims:
            inputs = np.pad(inputs, (0, max(0, self.input_dims - len(inputs))))[: self.input_dims]

        prediction_value = np.dot(self.weights, inputs) + self.bias

        # Calculate confidence based on weight stability
        confidence = 1.0 / (1.0 + np.std(self.weights))
        uncertainty = np.sum(np.abs(self.weights)) * 0.1

        return Prediction(
            prediction_id=f"{self.model_id}_{int(time.time() * 1000)}",
            level=input_data.get("level", 0),
            prediction_type="linear",
            predicted_value=float(prediction_value),
            confidence=confidence,
            uncertainty=uncertainty,
        )

    def update(self, error: PredictionError) -> None:
        """Update weights based on prediction error"""
        learning_rate = 0.01

        # Simple gradient descent update
        error_signal = error.error_magnitude * error.precision

        # Update bias
        self.bias -= learning_rate * error_signal

        # Update weights (simplified - would need input vector in real implementation)
        adjustment = learning_rate * error_signal * 0.1
        self.weights *= 1.0 - adjustment

        self.last_updated = time.time()


class PredictiveProcessing(BaseConsciousness):
    """
    Implementation of Predictive Processing Theory

    Implements a hierarchical system where consciousness emerges from
    continuous prediction and error correction processes.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("PredictiveProcessing", config)

        # Hierarchical structure
        self.hierarchy_levels: Dict[int, HierarchicalLevel] = {}
        self.num_levels = self.config.get("num_levels", 5)

        # Predictive models
        self.models: Dict[str, PredictiveModel] = {}

        # Processing parameters
        self.precision_learning_rate = self.config.get("precision_lr", 0.05)
        self.surprise_threshold = self.config.get("surprise_threshold", 5.0)
        self.max_prediction_history = self.config.get("max_history", 100)

        # Current state
        self.sensory_input: Dict[str, Any] = {}
        self.current_predictions: Dict[str, Prediction] = {}
        self.prediction_errors: deque = deque(maxlen=self.max_prediction_history)
        self.total_surprise = 0.0

        # Active inference
        self.active_inference_enabled = self.config.get("active_inference", True)
        self.action_predictions: Dict[str, Prediction] = {}

        # Attention and consciousness
        self.conscious_predictions: Set[str] = set()
        self.attention_weights: Dict[int, float] = defaultdict(lambda: 1.0)

        # Statistics
        self.total_predictions_made = 0
        self.average_prediction_accuracy = 0.0
        self.surprise_events = 0

        # Threading
        self.prediction_lock = threading.Lock()

    def _initialize(self):
        """Initialize the Predictive Processing system"""
        # Create hierarchical levels
        level_configs = [
            (0, "sensory", 0.1, 1.0),  # Fast, local
            (1, "perceptual", 0.3, 3.0),  # Medium, regional
            (2, "conceptual", 1.0, 10.0),  # Slow, global
            (3, "semantic", 3.0, 30.0),  # Very slow, abstract
            (4, "narrative", 10.0, 100.0),  # Extremely slow, story-level
        ]

        for level_id, name, temporal_scale, spatial_scale in level_configs:
            if level_id < self.num_levels:
                level = HierarchicalLevel(
                    level_id=level_id,
                    name=name,
                    temporal_scale=temporal_scale,
                    spatial_scale=spatial_scale,
                    learning_rate=0.1 / (level_id + 1),  # Slower learning at higher levels
                )
                self.hierarchy_levels[level_id] = level

        # Create predictive models for each level
        for level_id, level in self.hierarchy_levels.items():
            model_id = f"model_level_{level_id}"
            input_dims = max(1, 10 - level_id * 2)  # Decreasing complexity up the hierarchy
            model = SimpleLinearModel(model_id, input_dims)
            self.models[model_id] = model

        self.logger.info(
            f"Initialized Predictive Processing with {len(self.hierarchy_levels)} levels"
        )

    def add_sensory_input(self, input_type: str, input_data: Any) -> None:
        """Add sensory input to the system"""
        self.sensory_input[input_type] = {"data": input_data, "timestamp": time.time()}

        # Trigger prediction cascade
        self._process_sensory_input(input_type, input_data)

    def _process_sensory_input(self, input_type: str, input_data: Any) -> None:
        """Process sensory input through the predictive hierarchy"""
        # Start at lowest level (sensory)
        current_input = input_data

        for level_id in sorted(self.hierarchy_levels.keys()):
            level = self.hierarchy_levels[level_id]
            model_id = f"model_level_{level_id}"

            if model_id in self.models:
                model = self.models[model_id]

                # Make prediction at this level
                prediction_input = {
                    "inputs": self._prepare_input_for_level(current_input, level_id),
                    "level": level_id,
                    "input_type": input_type,
                }

                prediction = model.predict(prediction_input)

                with self.prediction_lock:
                    level.add_prediction(prediction)
                    self.current_predictions[prediction.prediction_id] = prediction
                    self.total_predictions_made += 1

                # Check for prediction errors if we have previous predictions
                self._check_prediction_errors(level_id, prediction, current_input)

                # Prepare input for next level (abstraction)
                current_input = prediction.predicted_value

    def _prepare_input_for_level(self, input_data: Any, level_id: int) -> np.ndarray:
        """Prepare input data for a specific hierarchical level"""
        # Convert input to numeric array
        if isinstance(input_data, (int, float)):
            base_array = np.array([input_data])
        elif isinstance(input_data, (list, tuple)):
            base_array = np.array(input_data[:10])  # Limit size
        elif isinstance(input_data, dict):
            # Extract numeric values
            values = []
            for key, value in input_data.items():
                if isinstance(value, (int, float)):
                    values.append(value)
            base_array = np.array(values[:10]) if values else np.array([0.0])
        else:
            # Default to zero array
            base_array = np.array([0.0])

        # Add level-specific processing
        if level_id > 0:
            # Higher levels see more abstract/averaged versions
            base_array = np.convolve(
                base_array, np.ones(min(3, len(base_array))) / min(3, len(base_array)), mode="same"
            )

        # Ensure minimum size
        if len(base_array) == 0:
            base_array = np.array([0.0])

        return base_array

    def _check_prediction_errors(
        self, level_id: int, new_prediction: Prediction, actual_input: Any
    ) -> None:
        """Check for prediction errors and update models"""
        level = self.hierarchy_levels[level_id]

        # Look for previous predictions to compare
        for pred_id, old_prediction in list(level.active_predictions.items()):
            if (
                old_prediction.prediction_id != new_prediction.prediction_id
                and old_prediction.prediction_type == new_prediction.prediction_type
            ):

                # Calculate prediction error
                if isinstance(old_prediction.predicted_value, (int, float)) and isinstance(
                    actual_input, (int, float)
                ):
                    error_magnitude = abs(old_prediction.predicted_value - actual_input)

                    # Calculate precision (inverse uncertainty)
                    precision = 1.0 / (old_prediction.uncertainty + 1e-6)

                    # Create error signal
                    error = PredictionError(
                        error_id=f"error_{old_prediction.prediction_id}",
                        prediction_id=old_prediction.prediction_id,
                        expected=old_prediction.predicted_value,
                        observed=actual_input,
                        error_magnitude=error_magnitude,
                        precision=precision,
                        level=level_id,
                    )

                    # Add to level and global error tracking
                    level.prediction_errors.append(error)
                    self.prediction_errors.append(error)

                    # Calculate surprise
                    surprise = error.calculate_surprise()
                    self.total_surprise += surprise

                    if surprise > self.surprise_threshold:
                        self.surprise_events += 1
                        self._handle_surprise_event(error, surprise)

                    # Update model based on error
                    model_id = f"model_level_{level_id}"
                    if model_id in self.models:
                        self.models[model_id].update(error)

                    # Update precision weights
                    self._update_precision_weights(level, error)

                    # Remove old prediction
                    del level.active_predictions[pred_id]

                    break

    def _update_precision_weights(self, level: HierarchicalLevel, error: PredictionError) -> None:
        """Update precision weights based on prediction errors"""
        error_type = error.prediction_id.split("_")[0] if "_" in error.prediction_id else "default"

        # Update precision based on error magnitude
        current_precision = level.precision_weights.get(error_type, 1.0)
        error_factor = 1.0 / (1.0 + error.error_magnitude)

        new_precision = (
            1.0 - self.precision_learning_rate
        ) * current_precision + self.precision_learning_rate * error_factor

        level.precision_weights[error_type] = new_precision

    def _handle_surprise_event(self, error: PredictionError, surprise: float) -> None:
        """Handle high-surprise events"""
        # High surprise indicates model needs significant updating
        level = self.hierarchy_levels[error.level]

        # Increase attention to this level
        self.attention_weights[error.level] *= 1.5

        # Mark associated predictions as conscious
        if error.prediction_id in self.current_predictions:
            self.conscious_predictions.add(error.prediction_id)

        # Emit consciousness event
        consciousness_event = ConsciousnessEvent(
            event_id=f"surprise_{error.error_id}",
            timestamp=time.time(),
            event_type="high_surprise",
            data={
                "error_magnitude": error.error_magnitude,
                "surprise": surprise,
                "level": error.level,
                "prediction_id": error.prediction_id,
                "expected": error.expected,
                "observed": error.observed,
            },
            priority=9,
            source_module="predictive_processing",
            confidence=min(1.0, surprise / 10.0),
        )

        self.emit_event(consciousness_event)

        self.logger.warning(f"High surprise event: {surprise:.2f} at level {error.level}")

    def make_action_prediction(
        self, action_type: str, action_parameters: Dict[str, Any]
    ) -> Prediction:
        """Make prediction about the consequences of an action"""
        if not self.active_inference_enabled:
            return None

        # Use highest level model for action prediction
        highest_level = max(self.hierarchy_levels.keys())
        model_id = f"model_level_{highest_level}"

        if model_id in self.models:
            model = self.models[model_id]

            prediction_input = {
                "inputs": self._prepare_action_input(action_type, action_parameters),
                "level": highest_level,
                "input_type": "action",
            }

            prediction = model.predict(prediction_input)
            prediction.prediction_type = f"action_{action_type}"

            self.action_predictions[prediction.prediction_id] = prediction
            return prediction

        return None

    def _prepare_action_input(self, action_type: str, parameters: Dict[str, Any]) -> np.ndarray:
        """Prepare action parameters as input for prediction"""
        # Convert action to numeric representation
        action_encoding = hash(action_type) % 1000 / 1000.0  # Normalize hash

        param_values = []
        for value in parameters.values():
            if isinstance(value, (int, float)):
                param_values.append(value)

        # Combine action encoding with parameters
        input_array = np.array([action_encoding] + param_values[:9])  # Limit to 10 total

        # Pad if needed
        if len(input_array) < 10:
            input_array = np.pad(input_array, (0, 10 - len(input_array)))

        return input_array

    def update_from_action_outcome(self, action_prediction_id: str, actual_outcome: Any) -> None:
        """Update models based on actual action outcomes"""
        if action_prediction_id in self.action_predictions:
            prediction = self.action_predictions[action_prediction_id]

            # Create prediction error for action
            if isinstance(prediction.predicted_value, (int, float)) and isinstance(
                actual_outcome, (int, float)
            ):
                error_magnitude = abs(prediction.predicted_value - actual_outcome)
                precision = 1.0 / (prediction.uncertainty + 1e-6)

                error = PredictionError(
                    error_id=f"action_error_{action_prediction_id}",
                    prediction_id=action_prediction_id,
                    expected=prediction.predicted_value,
                    observed=actual_outcome,
                    error_magnitude=error_magnitude,
                    precision=precision,
                    level=prediction.level,
                )

                # Update model
                model_id = f"model_level_{prediction.level}"
                if model_id in self.models:
                    self.models[model_id].update(error)

                # Clean up
                del self.action_predictions[action_prediction_id]

    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "sensory_input":
            input_type = event.data.get("input_type", "unknown")
            input_data = event.data.get("input_data")

            if input_data is not None:
                self.add_sensory_input(input_type, input_data)

        elif event.event_type == "action_prediction_request":
            action_type = event.data.get("action_type")
            parameters = event.data.get("parameters", {})

            if action_type:
                prediction = self.make_action_prediction(action_type, parameters)
                if prediction:
                    return ConsciousnessEvent(
                        event_id=f"action_prediction_{prediction.prediction_id}",
                        timestamp=time.time(),
                        event_type="action_prediction",
                        data=prediction.to_dict(),
                        source_module="predictive_processing",
                    )

        elif event.event_type == "action_outcome":
            prediction_id = event.data.get("prediction_id")
            outcome = event.data.get("outcome")

            if prediction_id and outcome is not None:
                self.update_from_action_outcome(prediction_id, outcome)

        return None

    def update(self) -> None:
        """Update the Predictive Processing system"""
        current_time = time.time()

        # Decay attention weights
        for level_id in self.attention_weights:
            self.attention_weights[level_id] *= 0.95
            if self.attention_weights[level_id] < 0.1:
                self.attention_weights[level_id] = 0.1

        # Clean up old predictions
        for level in self.hierarchy_levels.values():
            old_predictions = []
            for pred_id, prediction in level.active_predictions.items():
                if current_time - prediction.timestamp > level.temporal_scale * 5:
                    old_predictions.append(pred_id)

            for pred_id in old_predictions:
                del level.active_predictions[pred_id]
                if pred_id in self.current_predictions:
                    del self.current_predictions[pred_id]
                self.conscious_predictions.discard(pred_id)

        # Update metrics
        if self.prediction_errors:
            recent_errors = list(self.prediction_errors)[-20:]
            accuracies = [1.0 / (1.0 + error.error_magnitude) for error in recent_errors]
            self.average_prediction_accuracy = sum(accuracies) / len(accuracies)

        self.metrics.prediction_accuracy = self.average_prediction_accuracy
        self.metrics.awareness_level = len(self.conscious_predictions) / max(
            1, len(self.current_predictions)
        )

        # Calculate integration based on multi-level activity
        active_levels = sum(
            1 for level in self.hierarchy_levels.values() if level.active_predictions
        )
        self.metrics.integration_level = active_levels / len(self.hierarchy_levels)

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Predictive Processing system"""
        return {
            "num_levels": len(self.hierarchy_levels),
            "total_predictions": self.total_predictions_made,
            "active_predictions": len(self.current_predictions),
            "conscious_predictions": len(self.conscious_predictions),
            "total_surprise": self.total_surprise,
            "surprise_events": self.surprise_events,
            "average_accuracy": self.average_prediction_accuracy,
            "recent_errors": len(self.prediction_errors),
            "attention_weights": dict(self.attention_weights),
            "active_inference_enabled": self.active_inference_enabled,
            "level_activity": {
                level_id: len(level.active_predictions)
                for level_id, level in self.hierarchy_levels.items()
            },
        }

    def get_prediction_hierarchy_data(self) -> Dict[str, Any]:
        """Get data for visualizing the prediction hierarchy"""
        levels_data = []

        for level_id, level in self.hierarchy_levels.items():
            predictions_data = [pred.to_dict() for pred in level.active_predictions.values()]

            recent_errors = [
                {
                    "error_id": error.error_id,
                    "error_magnitude": error.error_magnitude,
                    "surprise": error.calculate_surprise(),
                    "timestamp": error.timestamp,
                }
                for error in level.prediction_errors[-10:]  # Last 10 errors
            ]

            levels_data.append(
                {
                    "level_id": level_id,
                    "name": level.name,
                    "temporal_scale": level.temporal_scale,
                    "spatial_scale": level.spatial_scale,
                    "active_predictions": predictions_data,
                    "recent_errors": recent_errors,
                    "average_precision": level.get_average_precision(),
                    "attention_weight": self.attention_weights[level_id],
                }
            )

        return {
            "levels": levels_data,
            "conscious_predictions": list(self.conscious_predictions),
            "total_surprise": self.total_surprise,
            "surprise_events": self.surprise_events,
        }
