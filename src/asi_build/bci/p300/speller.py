"""
P300 Speller System

Complete P300-based communication system for text input using ERP responses.
"""

import asyncio
import logging
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ..core.config import BCIConfig
from ..core.signal_processor import ProcessedSignal
from .p300_classifier import P300Classifier
from .stimulus_controller import StimulusController


@dataclass
class P300Trial:
    """Single P300 trial data"""

    stimulus_id: str
    stimulus_type: str  # 'target' or 'non_target'
    epoch_data: np.ndarray
    timestamp: float
    response_detected: bool = False
    confidence: float = 0.0


@dataclass
class SpellerResult:
    """Result from P300 speller classification"""

    predicted_character: str
    confidence: float
    trial_count: int
    processing_time: float
    detailed_scores: Dict[str, float]


class P300Speller:
    """
    Complete P300 speller system

    Features:
    - Configurable character matrix (6x6, 8x8, etc.)
    - Adaptive stimulus timing and repetitions
    - Real-time P300 detection and classification
    - Multiple selection modes (row-column, single character)
    - Text prediction and autocomplete
    - Training and calibration protocols
    """

    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Core components
        self.stimulus_controller = StimulusController(config)
        self.classifier = P300Classifier(config)

        # Speller configuration
        self.matrix_size = (6, 6)  # Default 6x6 matrix
        self.character_matrix = self._create_character_matrix()

        # P300 parameters
        self.p300_config = config.p300
        self.flash_duration = self.p300_config["flash_duration"]
        self.isi = self.p300_config["isi"]  # inter-stimulus interval
        self.repetitions = self.p300_config["repetitions"]

        # State management
        self.is_active = False
        self.current_mode = "row_column"  # 'row_column' or 'single_char'
        self.current_text = ""
        self.selection_history: List[SpellerResult] = []

        # Real-time processing
        self.trial_queue = queue.Queue()
        self.processing_thread: Optional[threading.Thread] = None

        # Callbacks
        self.character_callbacks: List[Callable] = []
        self.prediction_callbacks: List[Callable] = []

        # Training data
        self.training_trials: List[P300Trial] = []
        self.calibration_completed = False

        self.logger.info("P300 Speller initialized")

    def _create_character_matrix(self) -> np.ndarray:
        """Create character matrix for speller"""
        if self.matrix_size == (6, 6):
            chars = [
                ["A", "B", "C", "D", "E", "F"],
                ["G", "H", "I", "J", "K", "L"],
                ["M", "N", "O", "P", "Q", "R"],
                ["S", "T", "U", "V", "W", "X"],
                ["Y", "Z", "1", "2", "3", "4"],
                ["5", "6", "7", "8", "9", "0"],
            ]
        elif self.matrix_size == (8, 8):
            chars = [
                ["A", "B", "C", "D", "E", "F", "G", "H"],
                ["I", "J", "K", "L", "M", "N", "O", "P"],
                ["Q", "R", "S", "T", "U", "V", "W", "X"],
                ["Y", "Z", "1", "2", "3", "4", "5", "6"],
                ["7", "8", "9", "0", ".", ",", "?", "!"],
                [" ", "DEL", "CLR", "SPC", "ENT", "-", "+", "="],
                ["(", ")", "[", "]", "{", "}", "<", ">"],
                ["@", "#", "$", "%", "&", "*", "/", "\\"],
            ]
        else:
            # Default minimal matrix
            chars = [["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]]

        return np.array(chars)

    async def start_spelling_session(self) -> bool:
        """Start a new spelling session"""
        try:
            if not self.calibration_completed:
                self.logger.warning("P300 classifier not calibrated. Run calibration first.")
                return False

            self.is_active = True
            self.current_text = ""
            self.selection_history.clear()

            # Start stimulus controller
            await self.stimulus_controller.start()

            # Start processing thread
            self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.processing_thread.start()

            self.logger.info("P300 spelling session started")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start spelling session: {e}")
            return False

    async def stop_spelling_session(self) -> bool:
        """Stop the current spelling session"""
        try:
            self.is_active = False

            # Stop stimulus controller
            await self.stimulus_controller.stop()

            # Wait for processing thread to finish
            if self.processing_thread:
                self.processing_thread.join(timeout=5.0)

            self.logger.info("P300 spelling session stopped")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop spelling session: {e}")
            return False

    def _processing_loop(self):
        """Main processing loop for P300 trials"""
        while self.is_active:
            try:
                # Get trial from queue
                try:
                    trial = self.trial_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Process trial
                result = self._process_trial(trial)

                if result:
                    # Handle character selection
                    self._handle_character_selection(result)

            except Exception as e:
                self.logger.error(f"Processing loop error: {e}")
                time.sleep(0.1)

    def _process_trial(self, trial: P300Trial) -> Optional[SpellerResult]:
        """Process single P300 trial"""
        try:
            # Classify epoch
            prediction = self.classifier.predict(trial.epoch_data)

            if prediction is None:
                return None

            # Convert prediction to character
            character = self._prediction_to_character(prediction, trial.stimulus_id)

            if character is None:
                return None

            # Create result
            result = SpellerResult(
                predicted_character=character,
                confidence=prediction.confidence,
                trial_count=1,  # Single trial for now
                processing_time=prediction.processing_time,
                detailed_scores=prediction.class_probabilities,
            )

            return result

        except Exception as e:
            self.logger.error(f"Trial processing failed: {e}")
            return None

    def _prediction_to_character(self, prediction: Any, stimulus_id: str) -> Optional[str]:
        """Convert classifier prediction to character"""
        try:
            # For row-column paradigm
            if self.current_mode == "row_column":
                return self._row_column_to_character(prediction, stimulus_id)

            # For single character paradigm
            elif self.current_mode == "single_char":
                return self._single_char_to_character(prediction, stimulus_id)

            return None

        except Exception as e:
            self.logger.error(f"Character conversion failed: {e}")
            return None

    def _row_column_to_character(self, prediction: Any, stimulus_id: str) -> Optional[str]:
        """Convert row-column prediction to character"""
        # This is a simplified implementation
        # In practice, you'd accumulate scores across multiple repetitions

        if prediction.predicted_class == "target":
            # Parse stimulus_id to get row/column
            if "row" in stimulus_id:
                row_idx = int(stimulus_id.split("_")[1])
                # Need column information from another flash
                # For now, return first character in row
                if 0 <= row_idx < self.matrix_size[0]:
                    return self.character_matrix[row_idx, 0]

            elif "col" in stimulus_id:
                col_idx = int(stimulus_id.split("_")[1])
                # Need row information from another flash
                # For now, return first character in column
                if 0 <= col_idx < self.matrix_size[1]:
                    return self.character_matrix[0, col_idx]

        return None

    def _single_char_to_character(self, prediction: Any, stimulus_id: str) -> Optional[str]:
        """Convert single character prediction to character"""
        if prediction.predicted_class == "target":
            # Parse stimulus_id to get character position
            if "char" in stimulus_id:
                parts = stimulus_id.split("_")
                if len(parts) >= 3:
                    row_idx = int(parts[1])
                    col_idx = int(parts[2])

                    if 0 <= row_idx < self.matrix_size[0] and 0 <= col_idx < self.matrix_size[1]:
                        return self.character_matrix[row_idx, col_idx]

        return None

    def _handle_character_selection(self, result: SpellerResult):
        """Handle character selection result"""
        try:
            character = result.predicted_character

            # Special characters
            if character == "DEL":
                if self.current_text:
                    self.current_text = self.current_text[:-1]
            elif character == "CLR":
                self.current_text = ""
            elif character == "SPC":
                self.current_text += " "
            elif character == "ENT":
                # End of sentence/line
                self.current_text += "\n"
            else:
                # Regular character
                self.current_text += character

            # Store result
            self.selection_history.append(result)

            # Notify callbacks
            for callback in self.character_callbacks:
                try:
                    callback(character, self.current_text, result)
                except Exception as e:
                    self.logger.error(f"Character callback error: {e}")

            self.logger.info(f"Selected character: '{character}', Text: '{self.current_text}'")

        except Exception as e:
            self.logger.error(f"Character selection handling failed: {e}")

    async def calibrate(
        self, target_characters: List[str], trials_per_character: int = 10
    ) -> Dict[str, Any]:
        """Calibrate P300 classifier"""
        try:
            self.logger.info(f"Starting P300 calibration with {len(target_characters)} characters")

            calibration_trials = []

            for char_idx, target_char in enumerate(target_characters):
                self.logger.info(
                    f"Calibrating character {char_idx + 1}/{len(target_characters)}: '{target_char}'"
                )

                # Find character position in matrix
                char_position = self._find_character_position(target_char)
                if char_position is None:
                    self.logger.warning(f"Character '{target_char}' not found in matrix")
                    continue

                # Run calibration trials for this character
                char_trials = await self._run_calibration_trials(
                    target_char, char_position, trials_per_character
                )

                calibration_trials.extend(char_trials)

            # Train classifier
            training_result = await self._train_classifier(calibration_trials)

            # Mark calibration as completed
            self.calibration_completed = True

            calibration_result = {
                "characters_calibrated": len(target_characters),
                "total_trials": len(calibration_trials),
                "training_result": training_result,
                "timestamp": datetime.now().isoformat(),
            }

            self.logger.info(
                f"P300 calibration completed: {training_result.get('accuracy', 0.0):.3f} accuracy"
            )

            return calibration_result

        except Exception as e:
            self.logger.error(f"P300 calibration failed: {e}")
            raise

    def _find_character_position(self, character: str) -> Optional[Tuple[int, int]]:
        """Find character position in matrix"""
        for i in range(self.matrix_size[0]):
            for j in range(self.matrix_size[1]):
                if self.character_matrix[i, j] == character:
                    return (i, j)
        return None

    async def _run_calibration_trials(
        self, target_char: str, target_position: Tuple[int, int], n_trials: int
    ) -> List[P300Trial]:
        """Run calibration trials for a specific character"""
        trials = []

        for trial_idx in range(n_trials):
            # Present stimuli and collect responses
            if self.current_mode == "row_column":
                trial_data = await self._run_row_column_trial(target_position)
            else:
                trial_data = await self._run_single_char_trial(target_position)

            trials.extend(trial_data)

        return trials

    async def _run_row_column_trial(self, target_position: Tuple[int, int]) -> List[P300Trial]:
        """Run single row-column trial"""
        target_row, target_col = target_position
        trials = []

        # Flash all rows and columns multiple times
        for rep in range(self.repetitions):
            # Flash rows
            for row_idx in range(self.matrix_size[0]):
                stimulus_id = f"row_{row_idx}"
                is_target = row_idx == target_row

                # Present stimulus
                await self.stimulus_controller.flash_row(row_idx, self.flash_duration)

                # Wait for ISI
                await asyncio.sleep(self.isi)

                # Collect epoch data (simulated for now)
                epoch_data = self._collect_epoch_data()

                trial = P300Trial(
                    stimulus_id=stimulus_id,
                    stimulus_type="target" if is_target else "non_target",
                    epoch_data=epoch_data,
                    timestamp=time.time(),
                )

                trials.append(trial)

            # Flash columns
            for col_idx in range(self.matrix_size[1]):
                stimulus_id = f"col_{col_idx}"
                is_target = col_idx == target_col

                # Present stimulus
                await self.stimulus_controller.flash_column(col_idx, self.flash_duration)

                # Wait for ISI
                await asyncio.sleep(self.isi)

                # Collect epoch data (simulated for now)
                epoch_data = self._collect_epoch_data()

                trial = P300Trial(
                    stimulus_id=stimulus_id,
                    stimulus_type="target" if is_target else "non_target",
                    epoch_data=epoch_data,
                    timestamp=time.time(),
                )

                trials.append(trial)

        return trials

    async def _run_single_char_trial(self, target_position: Tuple[int, int]) -> List[P300Trial]:
        """Run single character trial"""
        target_row, target_col = target_position
        trials = []

        # Flash all characters multiple times
        for rep in range(self.repetitions):
            for row_idx in range(self.matrix_size[0]):
                for col_idx in range(self.matrix_size[1]):
                    stimulus_id = f"char_{row_idx}_{col_idx}"
                    is_target = row_idx == target_row and col_idx == target_col

                    # Present stimulus
                    await self.stimulus_controller.flash_character(
                        row_idx, col_idx, self.flash_duration
                    )

                    # Wait for ISI
                    await asyncio.sleep(self.isi)

                    # Collect epoch data (simulated for now)
                    epoch_data = self._collect_epoch_data()

                    trial = P300Trial(
                        stimulus_id=stimulus_id,
                        stimulus_type="target" if is_target else "non_target",
                        epoch_data=epoch_data,
                        timestamp=time.time(),
                    )

                    trials.append(trial)

        return trials

    def _collect_epoch_data(self) -> np.ndarray:
        """Collect epoch data from EEG (simulated for now)"""
        # This would interface with the actual EEG system
        # For now, return simulated data

        n_channels = len(self.config.device.channels)
        epoch_samples = int(
            (self.p300_config["epoch_window"][1] - self.p300_config["epoch_window"][0])
            * self.config.device.sampling_rate
        )

        # Generate simulated P300 response
        epoch_data = np.random.randn(n_channels, epoch_samples) * 10  # μV

        # Add simulated P300 component (simplified)
        p300_latency = 0.3  # seconds
        p300_sample = int(p300_latency * self.config.device.sampling_rate)

        if p300_sample < epoch_samples:
            # Add P300-like deflection to target channels
            target_channels = ["Cz", "Pz"]
            for ch_name in target_channels:
                if ch_name in self.config.device.channels:
                    ch_idx = self.config.device.channels.index(ch_name)
                    # Add positive deflection
                    epoch_data[ch_idx, p300_sample : p300_sample + 20] += 15  # μV

        return epoch_data

    async def _train_classifier(self, training_trials: List[P300Trial]) -> Dict[str, Any]:
        """Train P300 classifier with calibration data"""
        try:
            # Prepare training data
            epochs = []
            labels = []

            for trial in training_trials:
                epochs.append(trial.epoch_data)
                labels.append(trial.stimulus_type)

            # Train classifier
            training_result = await self.classifier.train(epochs, labels)

            return training_result

        except Exception as e:
            self.logger.error(f"Classifier training failed: {e}")
            raise

    def add_trial_data(self, epoch_data: np.ndarray, stimulus_id: str, stimulus_type: str):
        """Add trial data to processing queue"""
        trial = P300Trial(
            stimulus_id=stimulus_id,
            stimulus_type=stimulus_type,
            epoch_data=epoch_data,
            timestamp=time.time(),
        )

        try:
            self.trial_queue.put_nowait(trial)
        except queue.Full:
            self.logger.warning("Trial queue full, dropping trial")

    def add_character_callback(self, callback: Callable):
        """Add callback for character selection events"""
        self.character_callbacks.append(callback)

    def remove_character_callback(self, callback: Callable):
        """Remove character selection callback"""
        if callback in self.character_callbacks:
            self.character_callbacks.remove(callback)

    def get_current_text(self) -> str:
        """Get current spelled text"""
        return self.current_text

    def clear_text(self):
        """Clear current text"""
        self.current_text = ""
        self.selection_history.clear()

    def get_selection_history(self) -> List[SpellerResult]:
        """Get history of character selections"""
        return self.selection_history.copy()

    def get_character_matrix(self) -> np.ndarray:
        """Get character matrix"""
        return self.character_matrix.copy()

    def set_matrix_size(self, rows: int, cols: int):
        """Set character matrix size"""
        self.matrix_size = (rows, cols)
        self.character_matrix = self._create_character_matrix()
        self.logger.info(f"Character matrix set to {rows}x{cols}")

    def set_mode(self, mode: str):
        """Set spelling mode ('row_column' or 'single_char')"""
        if mode in ["row_column", "single_char"]:
            self.current_mode = mode
            self.logger.info(f"Spelling mode set to: {mode}")
        else:
            self.logger.error(f"Invalid mode: {mode}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        if not self.selection_history:
            return {}

        # Calculate metrics
        avg_confidence = np.mean([r.confidence for r in self.selection_history])
        avg_processing_time = np.mean([r.processing_time for r in self.selection_history])

        return {
            "total_selections": len(self.selection_history),
            "average_confidence": float(avg_confidence),
            "average_processing_time": float(avg_processing_time),
            "current_text_length": len(self.current_text),
            "calibration_completed": self.calibration_completed,
            "current_mode": self.current_mode,
        }

    async def shutdown(self):
        """Shutdown P300 speller"""
        try:
            if self.is_active:
                await self.stop_spelling_session()

            await self.stimulus_controller.cleanup()
            await self.classifier.cleanup()

            self.character_callbacks.clear()
            self.prediction_callbacks.clear()

            # Clear queues
            while not self.trial_queue.empty():
                try:
                    self.trial_queue.get_nowait()
                except queue.Empty:
                    break

            self.logger.info("P300 Speller shutdown complete")

        except Exception as e:
            self.logger.error(f"P300 speller shutdown failed: {e}")
