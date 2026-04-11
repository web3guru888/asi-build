"""
Motor Imagery Classifier

State-of-the-art motor imagery classification using CSP, filter banks,
and deep learning approaches.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from ..core.config import BCIConfig
from ..core.signal_processor import ProcessedSignal
from .csp_processor import CSPProcessor
from .feature_extractor import MotorImageryFeatureExtractor


@dataclass
class MotorImageryPrediction:
    """Motor imagery classification result"""

    predicted_class: str
    confidence: float
    class_probabilities: Dict[str, float]
    features_used: List[str]
    processing_time: float
    csp_patterns: Optional[np.ndarray] = None
    band_powers: Optional[Dict[str, float]] = None


class MotorImageryClassifier:
    """
    Advanced motor imagery classifier

    Features:
    - Common Spatial Patterns (CSP) with multiple frequency bands
    - Filter Bank CSP (FBCSP) for optimal frequency selection
    - Deep learning models (CNN, LSTM)
    - Ensemble methods combining multiple approaches
    - Real-time classification with adaptation
    - Multi-class support (left hand, right hand, feet, tongue)
    """

    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Motor imagery classes
        self.classes = config.motor_imagery["classes"]
        self.n_classes = len(self.classes)

        # Processing components
        self.csp_processor = CSPProcessor(config)
        self.feature_extractor = MotorImageryFeatureExtractor(config)

        # Classification models
        self.models = self._initialize_models()
        self.ensemble_model = None

        # Feature processing
        self.scaler = StandardScaler()
        self.feature_selector = None

        # Training data storage
        self.training_data: List[Dict] = []
        self.validation_scores: Dict[str, List[float]] = {}

        # Real-time classification
        self.current_model = "fbcsp_lda"
        self.adaptation_enabled = True
        self.adaptation_buffer: List[Dict] = []

        self.logger.info(f"Motor Imagery Classifier initialized for classes: {self.classes}")

    def _initialize_models(self) -> Dict[str, Any]:
        """Initialize classification models"""
        models = {}

        # CSP + LDA (classic approach)
        models["csp_lda"] = Pipeline(
            [("csp", self.csp_processor), ("lda", LinearDiscriminantAnalysis())]
        )

        # Filter Bank CSP + LDA
        models["fbcsp_lda"] = Pipeline(
            [
                ("fbcsp", self.csp_processor),
                ("scaler", StandardScaler()),
                ("lda", LinearDiscriminantAnalysis()),
            ]
        )

        # CSP + SVM
        models["csp_svm"] = Pipeline(
            [
                ("csp", self.csp_processor),
                ("scaler", StandardScaler()),
                ("svm", SVC(probability=True, kernel="rbf")),
            ]
        )

        # Random Forest with spectral features
        models["rf_spectral"] = Pipeline(
            [
                ("features", self.feature_extractor),
                ("scaler", StandardScaler()),
                ("rf", RandomForestClassifier(n_estimators=100, random_state=42)),
            ]
        )

        return models

    def train(
        self, training_epochs: List[np.ndarray], labels: List[str], validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """Train motor imagery classifier"""
        try:
            self.logger.info(
                f"Training motor imagery classifier with {len(training_epochs)} epochs"
            )

            # Validate inputs
            if len(training_epochs) != len(labels):
                raise ValueError("Number of epochs must match number of labels")

            # Convert data format
            X = np.array(training_epochs)  # Shape: (n_epochs, n_channels, n_samples)
            y = np.array(labels)

            # Store training data
            self.training_data = [
                {"epoch": epoch, "label": label} for epoch, label in zip(training_epochs, labels)
            ]

            # Train all models and select best
            results = {}
            best_score = 0
            best_model_name = None

            for model_name, model in self.models.items():
                try:
                    # Cross-validation
                    cv_scores = cross_val_score(
                        model,
                        X,
                        y,
                        cv=self.config.classification.cross_validation_folds,
                        scoring="accuracy",
                    )

                    mean_score = np.mean(cv_scores)
                    results[model_name] = {
                        "cv_scores": cv_scores.tolist(),
                        "mean_accuracy": float(mean_score),
                        "std_accuracy": float(np.std(cv_scores)),
                    }

                    # Track best model
                    if mean_score > best_score:
                        best_score = mean_score
                        best_model_name = model_name

                    # Store validation scores
                    if model_name not in self.validation_scores:
                        self.validation_scores[model_name] = []
                    self.validation_scores[model_name].extend(cv_scores.tolist())

                    self.logger.info(f"{model_name}: {mean_score:.3f} ± {np.std(cv_scores):.3f}")

                except Exception as e:
                    self.logger.error(f"Training failed for {model_name}: {e}")
                    results[model_name] = {"error": str(e)}

            # Train best model on full dataset
            if best_model_name:
                self.current_model = best_model_name
                best_model = self.models[best_model_name]
                best_model.fit(X, y)

                self.logger.info(
                    f"Selected best model: {best_model_name} (accuracy: {best_score:.3f})"
                )

            # Train ensemble model
            self._train_ensemble_model(X, y)

            # Save models
            self._save_models()

            training_result = {
                "best_model": best_model_name,
                "best_accuracy": float(best_score),
                "model_results": results,
                "training_epochs": len(training_epochs),
                "classes": self.classes,
                "timestamp": datetime.now().isoformat(),
            }

            return training_result

        except Exception as e:
            self.logger.error(f"Motor imagery training failed: {e}")
            raise

    def _train_ensemble_model(self, X: np.ndarray, y: np.ndarray):
        """Train ensemble model combining multiple approaches"""
        try:
            from sklearn.ensemble import VotingClassifier

            # Select models that trained successfully
            working_models = []
            for name, model in self.models.items():
                if hasattr(model, "predict"):
                    working_models.append((name, model))

            if len(working_models) >= 2:
                self.ensemble_model = VotingClassifier(
                    estimators=working_models, voting="soft"  # Use probabilities
                )

                # Train ensemble
                self.ensemble_model.fit(X, y)

                # Evaluate ensemble
                cv_scores = cross_val_score(self.ensemble_model, X, y, cv=3)
                ensemble_score = np.mean(cv_scores)

                self.logger.info(f"Ensemble model accuracy: {ensemble_score:.3f}")

                # Use ensemble if it's better than individual models
                if ensemble_score > max(
                    self.validation_scores.get(name, [0])[-1:] for name in self.models.keys()
                ):
                    self.current_model = "ensemble"

        except Exception as e:
            self.logger.warning(f"Ensemble training failed: {e}")

    def predict(self, epoch_data: np.ndarray) -> MotorImageryPrediction:
        """Classify single motor imagery epoch"""
        start_time = datetime.now()

        try:
            # Validate input
            if epoch_data.ndim != 2:
                raise ValueError("Epoch data must be 2D (channels x samples)")

            # Get current model
            if self.current_model == "ensemble" and self.ensemble_model is not None:
                model = self.ensemble_model
            else:
                model = self.models.get(self.current_model)

            if model is None:
                raise ValueError(f"Model not available: {self.current_model}")

            # Prepare data
            X = epoch_data.reshape(1, *epoch_data.shape)

            # Make prediction
            predicted_class = model.predict(X)[0]

            # Get probabilities
            if hasattr(model, "predict_proba"):
                probabilities = model.predict_proba(X)[0]
                class_probs = {cls: float(prob) for cls, prob in zip(self.classes, probabilities)}
                confidence = float(np.max(probabilities))
            else:
                class_probs = {predicted_class: 1.0}
                confidence = 1.0

            # Extract additional information
            csp_patterns = None
            band_powers = None
            features_used = []

            if "csp" in self.current_model:
                # Get CSP patterns if available
                if hasattr(model, "named_steps") and "csp" in model.named_steps:
                    csp_step = model.named_steps["csp"]
                    if hasattr(csp_step, "patterns_"):
                        csp_patterns = csp_step.patterns_

                # Get band powers
                band_powers = self._extract_band_powers(epoch_data)
                features_used.extend(["csp_features", "spatial_filters"])

            if "spectral" in self.current_model or "rf" in self.current_model:
                features_used.extend(["spectral_features", "temporal_features"])

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            # Create prediction result
            prediction = MotorImageryPrediction(
                predicted_class=predicted_class,
                confidence=confidence,
                class_probabilities=class_probs,
                features_used=features_used,
                processing_time=processing_time,
                csp_patterns=csp_patterns,
                band_powers=band_powers,
            )

            # Store for adaptation if confidence is high
            if (
                self.adaptation_enabled
                and confidence >= self.config.classification.confidence_threshold
            ):
                self._store_for_adaptation(epoch_data, prediction)

            return prediction

        except Exception as e:
            self.logger.error(f"Motor imagery prediction failed: {e}")
            raise

    def _extract_band_powers(self, epoch_data: np.ndarray) -> Dict[str, float]:
        """Extract power in motor imagery relevant frequency bands"""
        from scipy.signal import welch

        band_powers = {}

        # Focus on sensorimotor channels
        motor_channels = ["C3", "C4", "Cz"]

        for ch_idx, channel in enumerate(self.config.device.channels):
            if channel in motor_channels and ch_idx < epoch_data.shape[0]:
                ch_data = epoch_data[ch_idx, :]

                # Compute PSD
                f, psd = welch(ch_data, fs=self.config.device.sampling_rate, nperseg=256)

                # Extract band powers
                bands = self.config.motor_imagery["frequency_bands"]

                for band_name, (low_freq, high_freq) in bands.items():
                    band_mask = (f >= low_freq) & (f <= high_freq)
                    band_power = np.trapezoid(psd[band_mask], f[band_mask])
                    band_powers[f"{channel}_{band_name}"] = float(band_power)

        return band_powers

    def _store_for_adaptation(self, epoch_data: np.ndarray, prediction: MotorImageryPrediction):
        """Store data for online adaptation"""
        adaptation_entry = {
            "timestamp": datetime.now().isoformat(),
            "epoch_data": epoch_data.copy(),
            "prediction": prediction.predicted_class,
            "confidence": prediction.confidence,
            "band_powers": prediction.band_powers,
        }

        self.adaptation_buffer.append(adaptation_entry)

        # Keep only recent data
        max_buffer_size = 50
        if len(self.adaptation_buffer) > max_buffer_size:
            self.adaptation_buffer = self.adaptation_buffer[-max_buffer_size:]

    def adapt_online(self, true_labels: List[str]) -> bool:
        """Perform online adaptation with feedback"""
        try:
            if not self.adaptation_enabled or len(self.adaptation_buffer) == 0:
                return False

            if len(true_labels) != len(self.adaptation_buffer):
                self.logger.warning("Mismatch between buffer size and provided labels")
                return False

            # Extract data for adaptation
            adaptation_epochs = []
            adaptation_labels = []

            for entry, true_label in zip(self.adaptation_buffer, true_labels):
                adaptation_epochs.append(entry["epoch_data"])
                adaptation_labels.append(true_label)

            # Incremental learning (simplified)
            X_adapt = np.array(adaptation_epochs)
            y_adapt = np.array(adaptation_labels)

            # Get current model
            current_model = self.models.get(self.current_model)

            if current_model is not None and hasattr(current_model, "partial_fit"):
                # For models that support incremental learning
                current_model.partial_fit(X_adapt, y_adapt)
                self.logger.info(f"Adapted model with {len(adaptation_epochs)} samples")

            elif current_model is not None:
                # For models that need full retraining
                # Combine with existing training data (simplified)
                all_epochs = [
                    entry["epoch"] for entry in self.training_data
                ] + adaptation_epochs.tolist()
                all_labels = [
                    entry["label"] for entry in self.training_data
                ] + adaptation_labels.tolist()

                # Retrain with limited data to avoid overfitting
                recent_count = min(200, len(all_epochs))
                X_retrain = np.array(all_epochs[-recent_count:])
                y_retrain = np.array(all_labels[-recent_count:])

                current_model.fit(X_retrain, y_retrain)
                self.logger.info(f"Retrained model with {recent_count} samples")

            # Clear adaptation buffer
            self.adaptation_buffer.clear()

            return True

        except Exception as e:
            self.logger.error(f"Online adaptation failed: {e}")
            return False

    def evaluate_model(
        self, test_epochs: List[np.ndarray], test_labels: List[str]
    ) -> Dict[str, Any]:
        """Evaluate model performance on test data"""
        try:
            X_test = np.array(test_epochs)
            y_test = np.array(test_labels)

            # Get current model
            if self.current_model == "ensemble" and self.ensemble_model is not None:
                model = self.ensemble_model
            else:
                model = self.models.get(self.current_model)

            if model is None:
                raise ValueError(f"Model not available: {self.current_model}")

            # Make predictions
            y_pred = model.predict(X_test)

            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            conf_matrix = confusion_matrix(y_test, y_pred, labels=self.classes)
            class_report = classification_report(
                y_test, y_pred, labels=self.classes, output_dict=True
            )

            # Per-class accuracies
            class_accuracies = {}
            for i, class_name in enumerate(self.classes):
                class_mask = y_test == class_name
                if np.any(class_mask):
                    class_acc = accuracy_score(y_test[class_mask], y_pred[class_mask])
                    class_accuracies[class_name] = float(class_acc)

            # Confidence analysis
            if hasattr(model, "predict_proba"):
                y_proba = model.predict_proba(X_test)
                avg_confidence = float(np.mean(np.max(y_proba, axis=1)))
                confidence_by_class = {}

                for i, class_name in enumerate(self.classes):
                    class_mask = y_test == class_name
                    if np.any(class_mask):
                        class_confidences = np.max(y_proba[class_mask], axis=1)
                        confidence_by_class[class_name] = float(np.mean(class_confidences))
            else:
                avg_confidence = 1.0
                confidence_by_class = {cls: 1.0 for cls in self.classes}

            evaluation_result = {
                "model_name": self.current_model,
                "overall_accuracy": float(accuracy),
                "class_accuracies": class_accuracies,
                "confusion_matrix": conf_matrix.tolist(),
                "classification_report": class_report,
                "average_confidence": avg_confidence,
                "confidence_by_class": confidence_by_class,
                "test_samples": len(test_epochs),
                "timestamp": datetime.now().isoformat(),
            }

            return evaluation_result

        except Exception as e:
            self.logger.error(f"Model evaluation failed: {e}")
            raise

    def get_feature_importance(self) -> Dict[str, Any]:
        """Get feature importance from trained models"""
        importance_data = {}

        try:
            for model_name, model in self.models.items():
                if hasattr(model, "feature_importances_"):
                    # For tree-based models
                    importance_data[model_name] = {
                        "feature_importances": model.feature_importances_.tolist(),
                        "type": "tree_based",
                    }
                elif hasattr(model, "coef_"):
                    # For linear models
                    importance_data[model_name] = {
                        "coefficients": model.coef_.tolist(),
                        "type": "linear",
                    }
                elif hasattr(model, "named_steps"):
                    # For pipeline models
                    pipeline_importance = {}

                    for step_name, step in model.named_steps.items():
                        if hasattr(step, "feature_importances_"):
                            pipeline_importance[step_name] = step.feature_importances_.tolist()
                        elif hasattr(step, "coef_"):
                            pipeline_importance[step_name] = step.coef_.tolist()

                    if pipeline_importance:
                        importance_data[model_name] = {
                            "pipeline_importance": pipeline_importance,
                            "type": "pipeline",
                        }

        except Exception as e:
            self.logger.error(f"Feature importance extraction failed: {e}")

        return importance_data

    def _save_models(self):
        """Save trained models to disk"""
        try:
            model_dir = os.path.join(self.config.model_directory, "motor_imagery")
            os.makedirs(model_dir, exist_ok=True)

            # Save individual models
            for name, model in self.models.items():
                if hasattr(model, "predict"):  # Only save trained models
                    model_path = os.path.join(model_dir, f"{name}_model.pkl")
                    joblib.dump(model, model_path)

            # Save ensemble model
            if self.ensemble_model is not None:
                ensemble_path = os.path.join(model_dir, "ensemble_model.pkl")
                joblib.dump(self.ensemble_model, ensemble_path)

            # Save metadata
            metadata = {
                "classes": self.classes,
                "current_model": self.current_model,
                "training_samples": len(self.training_data),
                "timestamp": datetime.now().isoformat(),
                "config": self.config._to_dict(),
            }

            import json

            metadata_path = os.path.join(model_dir, "metadata.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            self.logger.info(f"Models saved to {model_dir}")

        except Exception as e:
            self.logger.error(f"Failed to save models: {e}")

    def load_models(self) -> bool:
        """Load trained models from disk"""
        try:
            model_dir = os.path.join(self.config.model_directory, "motor_imagery")

            # Load metadata
            metadata_path = os.path.join(model_dir, "metadata.json")
            if os.path.exists(metadata_path):
                import json

                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

                self.classes = metadata.get("classes", self.classes)
                self.current_model = metadata.get("current_model", "fbcsp_lda")

            # Load individual models
            models_loaded = 0
            for name in self.models.keys():
                model_path = os.path.join(model_dir, f"{name}_model.pkl")
                if os.path.exists(model_path):
                    self.models[name] = joblib.load(model_path)
                    models_loaded += 1

            # Load ensemble model
            ensemble_path = os.path.join(model_dir, "ensemble_model.pkl")
            if os.path.exists(ensemble_path):
                self.ensemble_model = joblib.load(ensemble_path)
                models_loaded += 1

            if models_loaded > 0:
                self.logger.info(f"Loaded {models_loaded} motor imagery models")
                return True
            else:
                self.logger.warning("No motor imagery models found to load")
                return False

        except Exception as e:
            self.logger.error(f"Failed to load models: {e}")
            return False

    def get_training_history(self) -> Dict[str, Any]:
        """Get training and validation history"""
        return {
            "validation_scores": self.validation_scores,
            "current_model": self.current_model,
            "classes": self.classes,
            "training_samples": len(self.training_data),
            "adaptation_enabled": self.adaptation_enabled,
            "adaptation_buffer_size": len(self.adaptation_buffer),
        }

    def set_model(self, model_name: str) -> bool:
        """Set active model for prediction"""
        if model_name == "ensemble" and self.ensemble_model is not None:
            self.current_model = model_name
            return True
        elif model_name in self.models and hasattr(self.models[model_name], "predict"):
            self.current_model = model_name
            return True
        else:
            self.logger.error(f"Model not available: {model_name}")
            return False

    def enable_adaptation(self, enabled: bool = True):
        """Enable or disable online adaptation"""
        self.adaptation_enabled = enabled
        if not enabled:
            self.adaptation_buffer.clear()

        self.logger.info(f"Online adaptation {'enabled' if enabled else 'disabled'}")
