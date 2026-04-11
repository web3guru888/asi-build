"""
BCI Manager - Central coordination for all BCI operations

Manages BCI devices, signal processing, and neural decoding pipelines.
"""

import asyncio
import json
import logging
import queue
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from .config import BCIConfig
from .device_interface import DeviceInterface
from .neural_decoder import NeuralDecoder
from .signal_processor import SignalProcessor


@dataclass
class BCISession:
    """Represents an active BCI session"""

    session_id: str
    start_time: datetime
    device_type: str
    sampling_rate: float
    channels: List[str]
    tasks: List[str]
    status: str = "active"


class BCIManager:
    """
    Central BCI coordination and management system

    Features:
    - Multi-device support (EEG, EMG, fNIRS)
    - Real-time signal processing
    - Neural decoding coordination
    - Session management
    - Data recording and playback
    """

    def __init__(self, config: Optional[BCIConfig] = None):
        self.config = config or BCIConfig()
        self.logger = logging.getLogger(__name__)

        # Core components
        self.device_interface = DeviceInterface(self.config)
        self.signal_processor = SignalProcessor(self.config)
        self.neural_decoder = NeuralDecoder(self.config)

        # Session management
        self.active_sessions: Dict[str, BCISession] = {}
        self.session_counter = 0

        # Real-time processing
        self.processing_queue = queue.Queue()
        self.result_callbacks: List[Callable] = []
        self.is_running = False
        self.processing_thread = None

        # Data storage
        self.recorded_data: List[Dict] = []
        self.calibration_data: Dict = {}

        self.logger.info("BCI Manager initialized")

    async def start_session(
        self, device_type: str, tasks: List[str], channels: Optional[List[str]] = None
    ) -> str:
        """Start a new BCI session"""
        try:
            session_id = f"bci_session_{self.session_counter}"
            self.session_counter += 1

            # Initialize device
            await self.device_interface.connect(device_type)
            device_info = await self.device_interface.get_device_info()

            # Create session
            session = BCISession(
                session_id=session_id,
                start_time=datetime.now(),
                device_type=device_type,
                sampling_rate=device_info.get("sampling_rate", 250.0),
                channels=channels or device_info.get("channels", []),
                tasks=tasks,
            )

            self.active_sessions[session_id] = session

            # Start real-time processing
            if not self.is_running:
                await self.start_processing()

            self.logger.info(f"Started BCI session: {session_id}")
            return session_id

        except Exception as e:
            self.logger.error(f"Failed to start BCI session: {e}")
            raise

    async def stop_session(self, session_id: str) -> bool:
        """Stop an active BCI session"""
        try:
            if session_id not in self.active_sessions:
                return False

            session = self.active_sessions[session_id]
            session.status = "stopped"

            # Stop device if no other sessions
            active_count = sum(1 for s in self.active_sessions.values() if s.status == "active")

            if active_count <= 1:
                await self.device_interface.disconnect()
                await self.stop_processing()

            self.logger.info(f"Stopped BCI session: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop session {session_id}: {e}")
            return False

    async def start_processing(self):
        """Start real-time signal processing"""
        if self.is_running:
            return

        self.is_running = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()

        self.logger.info("Started real-time processing")

    async def stop_processing(self):
        """Stop real-time signal processing"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)

        self.logger.info("Stopped real-time processing")

    def _processing_loop(self):
        """Main processing loop for real-time data"""
        while self.is_running:
            try:
                # Get data from device
                if self.device_interface.is_connected():
                    raw_data = self.device_interface.read_data()

                    if raw_data is not None:
                        # Process signal
                        processed_data = self.signal_processor.process_realtime(raw_data)

                        # Decode neural signals
                        decoded_results = self.neural_decoder.decode(processed_data)

                        # Store data
                        self.recorded_data.append(
                            {
                                "timestamp": datetime.now().isoformat(),
                                "raw_data": (
                                    raw_data.tolist()
                                    if isinstance(raw_data, np.ndarray)
                                    else raw_data
                                ),
                                "processed_data": processed_data,
                                "decoded_results": decoded_results,
                            }
                        )

                        # Notify callbacks
                        for callback in self.result_callbacks:
                            try:
                                callback(decoded_results)
                            except Exception as e:
                                self.logger.error(f"Callback error: {e}")

                # Small delay to prevent CPU overload
                asyncio.sleep(0.01)

            except Exception as e:
                self.logger.error(f"Processing loop error: {e}")
                asyncio.sleep(0.1)

    def add_result_callback(self, callback: Callable):
        """Add callback for real-time results"""
        self.result_callbacks.append(callback)

    def remove_result_callback(self, callback: Callable):
        """Remove result callback"""
        if callback in self.result_callbacks:
            self.result_callbacks.remove(callback)

    async def calibrate(self, task_type: str, duration: float = 60.0, trials: int = 20) -> Dict:
        """Perform BCI calibration for specific task"""
        try:
            self.logger.info(f"Starting calibration for {task_type}")

            calibration_data = []

            for trial in range(trials):
                # Collect calibration trial data
                trial_data = await self._collect_calibration_trial(task_type, duration / trials)
                calibration_data.append(trial_data)

                self.logger.info(f"Completed calibration trial {trial + 1}/{trials}")

            # Train classifier with calibration data
            model_params = await self.neural_decoder.train_classifier(task_type, calibration_data)

            # Store calibration results
            self.calibration_data[task_type] = {
                "timestamp": datetime.now().isoformat(),
                "trials": trials,
                "duration": duration,
                "model_params": model_params,
                "accuracy": model_params.get("accuracy", 0.0),
            }

            self.logger.info(
                f"Calibration completed for {task_type}, "
                f"accuracy: {model_params.get('accuracy', 0.0):.2f}"
            )

            return self.calibration_data[task_type]

        except Exception as e:
            self.logger.error(f"Calibration failed for {task_type}: {e}")
            raise

    async def _collect_calibration_trial(self, task_type: str, duration: float) -> Dict:
        """Collect data for a single calibration trial"""
        start_time = datetime.now()
        trial_data = {
            "task_type": task_type,
            "start_time": start_time.isoformat(),
            "duration": duration,
            "raw_data": [],
            "processed_data": [],
        }

        # Collect data for specified duration
        while (datetime.now() - start_time).total_seconds() < duration:
            if self.device_interface.is_connected():
                raw_data = self.device_interface.read_data()
                if raw_data is not None:
                    processed_data = self.signal_processor.process_realtime(raw_data)

                    trial_data["raw_data"].append(raw_data.tolist())
                    trial_data["processed_data"].append(processed_data)

            await asyncio.sleep(0.01)

        return trial_data

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a BCI session"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        return {
            "session_id": session.session_id,
            "start_time": session.start_time.isoformat(),
            "device_type": session.device_type,
            "sampling_rate": session.sampling_rate,
            "channels": session.channels,
            "tasks": session.tasks,
            "status": session.status,
            "duration": (datetime.now() - session.start_time).total_seconds(),
        }

    def get_system_status(self) -> Dict:
        """Get overall BCI system status"""
        return {
            "active_sessions": len(
                [s for s in self.active_sessions.values() if s.status == "active"]
            ),
            "total_sessions": len(self.active_sessions),
            "is_processing": self.is_running,
            "device_connected": self.device_interface.is_connected(),
            "recorded_samples": len(self.recorded_data),
            "calibrated_tasks": list(self.calibration_data.keys()),
            "uptime": datetime.now().isoformat(),
        }

    def export_session_data(self, session_id: str, format: str = "json") -> Optional[str]:
        """Export session data in specified format"""
        try:
            if session_id not in self.active_sessions:
                return None

            session_data = {
                "session_info": self.get_session_info(session_id),
                "recorded_data": [
                    d for d in self.recorded_data if d.get("session_id") == session_id
                ],
                "calibration_data": self.calibration_data,
            }

            if format.lower() == "json":
                return json.dumps(session_data, indent=2)
            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            self.logger.error(f"Failed to export session data: {e}")
            return None

    async def shutdown(self):
        """Shutdown BCI manager and cleanup resources"""
        try:
            # Stop all active sessions
            for session_id in list(self.active_sessions.keys()):
                await self.stop_session(session_id)

            # Cleanup components
            await self.device_interface.cleanup()
            await self.signal_processor.cleanup()
            await self.neural_decoder.cleanup()

            self.logger.info("BCI Manager shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
