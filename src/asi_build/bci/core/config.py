"""
BCI Configuration Management

Centralized configuration for all BCI components.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DeviceConfig:
    """Configuration for BCI devices"""

    device_type: str = "eeg"
    sampling_rate: float = 250.0
    channels: List[str] = field(
        default_factory=lambda: ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2"]
    )
    impedance_threshold: float = 5.0  # kOhms
    buffer_size: int = 1000
    connection_timeout: float = 10.0


@dataclass
class SignalProcessingConfig:
    """Configuration for signal processing"""

    # Filtering
    bandpass_low: float = 0.5  # Hz
    bandpass_high: float = 50.0  # Hz
    notch_freq: float = 50.0  # Hz (power line)

    # Artifact removal
    enable_ica: bool = True
    ica_components: int = 10
    enable_eog_removal: bool = True
    enable_emg_removal: bool = True

    # Epoching
    epoch_length: float = 2.0  # seconds
    baseline_correction: bool = True
    baseline_window: tuple = (-0.2, 0.0)  # seconds

    # Feature extraction
    enable_spectral_features: bool = True
    enable_temporal_features: bool = True
    enable_spatial_features: bool = True


@dataclass
class ClassificationConfig:
    """Configuration for neural classification"""

    # Models
    default_classifier: str = "csp_lda"
    ensemble_voting: bool = True
    cross_validation_folds: int = 5

    # Training
    training_epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    validation_split: float = 0.2

    # Performance
    confidence_threshold: float = 0.7
    calibration_trials: int = 20
    adaptation_rate: float = 0.1


@dataclass
class BCIConfig:
    """Main BCI configuration class"""

    # Component configurations
    device: DeviceConfig = field(default_factory=DeviceConfig)
    signal_processing: SignalProcessingConfig = field(default_factory=SignalProcessingConfig)
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)

    # General settings
    debug_mode: bool = False
    log_level: str = "INFO"
    data_directory: str = "./bci_data"
    model_directory: str = "./bci_models"

    # Real-time processing
    realtime_buffer_ms: int = 100
    processing_threads: int = 2
    enable_gpu: bool = True

    # Safety and limits
    max_session_duration: float = 3600.0  # seconds
    auto_save_interval: float = 300.0  # seconds
    emergency_stop_threshold: float = 100.0  # μV

    # Task-specific settings
    motor_imagery: Dict[str, Any] = field(
        default_factory=lambda: {
            "classes": ["left_hand", "right_hand", "feet", "tongue"],
            "trial_duration": 4.0,  # seconds
            "cue_duration": 1.0,
            "rest_duration": 2.0,
            "frequency_bands": {"mu": (8, 12), "beta": (13, 30), "gamma": (30, 50)},
        }
    )

    p300: Dict[str, Any] = field(
        default_factory=lambda: {
            "flash_duration": 0.1,  # seconds
            "isi": 0.175,  # inter-stimulus interval
            "repetitions": 6,
            "target_channels": ["Cz", "Pz"],
            "epoch_window": (0.0, 0.8),  # seconds
        }
    )

    ssvep: Dict[str, Any] = field(
        default_factory=lambda: {
            "frequencies": [8.0, 10.0, 12.0, 14.0],  # Hz
            "harmonics": [2, 3],
            "window_length": 4.0,  # seconds
            "overlap": 0.5,
            "target_channels": ["O1", "O2", "Oz"],
        }
    )

    neurofeedback: Dict[str, Any] = field(
        default_factory=lambda: {
            "target_bands": {"theta": (4, 8), "alpha": (8, 12), "beta": (12, 30)},
            "feedback_delay": 0.1,  # seconds
            "update_rate": 10,  # Hz
            "threshold_adaptation": True,
        }
    )

    @classmethod
    def load_from_file(cls, config_path: str) -> "BCIConfig":
        """Load configuration from JSON file"""
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)

            # Create config object with defaults
            config = cls()

            # Update with loaded data
            config._update_from_dict(config_data)

            return config

        except Exception as e:
            raise ValueError(f"Failed to load config from {config_path}: {e}")

    def save_to_file(self, config_path: str):
        """Save configuration to JSON file"""
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            config_dict = self._to_dict()

            with open(config_path, "w") as f:
                json.dump(config_dict, f, indent=2)

        except Exception as e:
            raise ValueError(f"Failed to save config to {config_path}: {e}")

    def _to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""

        def convert_value(value):
            if hasattr(value, "__dict__"):
                return {k: convert_value(v) for k, v in value.__dict__.items()}
            elif isinstance(value, (list, tuple)):
                return [convert_value(v) for v in value]
            elif isinstance(value, dict):
                return {k: convert_value(v) for k, v in value.items()}
            else:
                return value

        return convert_value(self)

    def _update_from_dict(self, config_dict: Dict[str, Any]):
        """Update configuration from dictionary"""

        def update_object(obj, data):
            for key, value in data.items():
                if hasattr(obj, key):
                    current_value = getattr(obj, key)
                    if hasattr(current_value, "__dict__") and isinstance(value, dict):
                        update_object(current_value, value)
                    else:
                        setattr(obj, key, value)

        update_object(self, config_dict)

    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []

        # Validate device config
        if self.device.sampling_rate <= 0:
            issues.append("Invalid sampling rate: must be > 0")

        if not self.device.channels:
            issues.append("No channels specified")

        # Validate signal processing
        if self.signal_processing.bandpass_low >= self.signal_processing.bandpass_high:
            issues.append("Invalid bandpass filter: low freq >= high freq")

        if self.signal_processing.epoch_length <= 0:
            issues.append("Invalid epoch length: must be > 0")

        # Validate classification
        if (
            self.classification.confidence_threshold < 0
            or self.classification.confidence_threshold > 1
        ):
            issues.append("Invalid confidence threshold: must be between 0 and 1")

        if self.classification.calibration_trials < 1:
            issues.append("Invalid calibration trials: must be >= 1")

        # Validate directories
        try:
            os.makedirs(self.data_directory, exist_ok=True)
            os.makedirs(self.model_directory, exist_ok=True)
        except Exception as e:
            issues.append(f"Cannot create directories: {e}")

        return issues

    def get_task_config(self, task: str) -> Optional[Dict[str, Any]]:
        """Get configuration for specific BCI task"""
        task_configs = {
            "motor_imagery": self.motor_imagery,
            "p300": self.p300,
            "ssvep": self.ssvep,
            "neurofeedback": self.neurofeedback,
        }

        return task_configs.get(task)

    def update_task_config(self, task: str, config_update: Dict[str, Any]):
        """Update configuration for specific task"""
        if task == "motor_imagery":
            self.motor_imagery.update(config_update)
        elif task == "p300":
            self.p300.update(config_update)
        elif task == "ssvep":
            self.ssvep.update(config_update)
        elif task == "neurofeedback":
            self.neurofeedback.update(config_update)
        else:
            raise ValueError(f"Unknown task: {task}")

    def __repr__(self) -> str:
        return (
            f"BCIConfig(device={self.device.device_type}, "
            f"channels={len(self.device.channels)}, "
            f"sampling_rate={self.device.sampling_rate}Hz)"
        )
