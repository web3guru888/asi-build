"""
Asynchronous Federated Learning

Implementation of asynchronous federated learning algorithms that allow
clients to participate at different times without waiting for synchronization.
"""

import asyncio
import logging
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ..aggregation.base_aggregator import BaseAggregator
from ..core.base import FederatedClient, FederatedModel, FederatedServer
from ..core.exceptions import FederatedLearningError, ServerError


class AsyncUpdateBuffer:
    """Buffer for storing asynchronous client updates."""

    def __init__(self, max_size: int = 1000, staleness_threshold: int = 5):
        self.max_size = max_size
        self.staleness_threshold = staleness_threshold
        self.updates = deque(maxlen=max_size)
        self.global_version = 0
        self.lock = threading.Lock()
        self.logger = logging.getLogger("AsyncUpdateBuffer")

    def add_update(self, update: Dict[str, Any]) -> bool:
        """Add a client update to the buffer."""
        with self.lock:
            # Check staleness
            update_version = update.get("global_version", 0)
            staleness = self.global_version - update_version

            if staleness > self.staleness_threshold:
                self.logger.warning(
                    f"Rejecting stale update from client {update.get('client_id')} "
                    f"(staleness: {staleness})"
                )
                return False

            # Add timestamp and staleness info
            update["received_timestamp"] = time.time()
            update["staleness"] = staleness

            self.updates.append(update)
            self.logger.debug(
                f"Added update from client {update.get('client_id')} "
                f"(buffer size: {len(self.updates)})"
            )
            return True

    def get_updates(self, max_updates: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get updates from the buffer."""
        with self.lock:
            if max_updates is None:
                updates = list(self.updates)
                self.updates.clear()
            else:
                updates = []
                for _ in range(min(max_updates, len(self.updates))):
                    updates.append(self.updates.popleft())
            return updates

    def update_global_version(self, new_version: int):
        """Update the global model version."""
        with self.lock:
            self.global_version = new_version

    def get_buffer_status(self) -> Dict[str, Any]:
        """Get buffer status information."""
        with self.lock:
            return {
                "buffer_size": len(self.updates),
                "max_size": self.max_size,
                "global_version": self.global_version,
                "staleness_threshold": self.staleness_threshold,
            }


class AsyncFedAvg(BaseAggregator):
    """Asynchronous FedAvg aggregator."""

    def __init__(self, aggregator_id: str = "async_fedavg", config: Dict[str, Any] = None):
        super().__init__(aggregator_id, config)

        # Async-specific parameters
        self.min_updates_for_aggregation = self.config.get("min_updates_for_aggregation", 1)
        self.max_updates_per_round = self.config.get("max_updates_per_round", 10)
        self.staleness_weight_decay = self.config.get("staleness_weight_decay", 0.9)
        self.aggregation_frequency = self.config.get("aggregation_frequency", 5.0)  # seconds

        # Async state
        self.update_buffer = AsyncUpdateBuffer(
            max_size=self.config.get("buffer_size", 1000),
            staleness_threshold=self.config.get("staleness_threshold", 5),
        )
        self.global_version = 0
        self.is_running = False
        self.aggregation_thread = None

        self.logger.info(
            f"AsyncFedAvg aggregator initialized with min_updates={self.min_updates_for_aggregation}"
        )

    def start_async_aggregation(
        self, global_model_update_callback: Callable[[List[np.ndarray]], None]
    ):
        """Start asynchronous aggregation process."""
        if self.is_running:
            self.logger.warning("Async aggregation already running")
            return

        self.is_running = True
        self.aggregation_thread = threading.Thread(
            target=self._async_aggregation_loop, args=(global_model_update_callback,), daemon=True
        )
        self.aggregation_thread.start()
        self.logger.info("Started asynchronous aggregation")

    def stop_async_aggregation(self):
        """Stop asynchronous aggregation process."""
        self.is_running = False
        if self.aggregation_thread:
            self.aggregation_thread.join(timeout=10)
        self.logger.info("Stopped asynchronous aggregation")

    def add_client_update(self, client_update: Dict[str, Any]) -> bool:
        """Add a client update to the async buffer."""
        return self.update_buffer.add_update(client_update)

    def _async_aggregation_loop(
        self, global_model_update_callback: Callable[[List[np.ndarray]], None]
    ):
        """Main asynchronous aggregation loop."""
        while self.is_running:
            try:
                # Wait for aggregation interval
                time.sleep(self.aggregation_frequency)

                # Get available updates
                updates = self.update_buffer.get_updates(self.max_updates_per_round)

                if len(updates) >= self.min_updates_for_aggregation:
                    # Perform aggregation
                    result = self.aggregate(updates)

                    # Update global model
                    if result and "aggregated_weights" in result:
                        global_model_update_callback(result["aggregated_weights"])

                        # Update global version
                        self.global_version += 1
                        self.update_buffer.update_global_version(self.global_version)

                        self.logger.info(
                            f"Async aggregation completed (version {self.global_version}, "
                            f"{len(updates)} updates)"
                        )

            except Exception as e:
                self.logger.error(f"Error in async aggregation loop: {str(e)}")

    def aggregate(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate client updates asynchronously."""
        if not client_updates:
            return {}

        start_time = time.time()

        # Validate updates
        self.validate_updates(client_updates)

        # Extract client information
        client_weights_list = [update["weights"] for update in client_updates]
        data_sizes = [update["data_size"] for update in client_updates]
        client_ids = [update["client_id"] for update in client_updates]
        staleness_values = [update.get("staleness", 0) for update in client_updates]

        # Compute staleness-aware aggregation weights
        aggregation_weights = self._compute_staleness_aware_weights(
            client_updates, staleness_values
        )

        # Perform weighted averaging
        aggregated_weights = self.weighted_average(client_weights_list, aggregation_weights)

        # Apply gradient clipping and noise
        aggregated_weights = self.clip_weights(aggregated_weights)
        aggregated_weights = self.add_noise(aggregated_weights)

        aggregation_time = time.time() - start_time

        # Compute staleness statistics
        staleness_stats = {
            "avg_staleness": np.mean(staleness_values),
            "max_staleness": max(staleness_values),
            "min_staleness": min(staleness_values),
            "std_staleness": np.std(staleness_values),
        }

        result = {
            "aggregated_weights": aggregated_weights,
            "num_clients": len(client_updates),
            "aggregation_time": aggregation_time,
            "aggregation_method": "async_fedavg",
            "global_version": self.global_version,
            "staleness_stats": staleness_stats,
            "aggregation_weights": aggregation_weights,
            "metadata": {
                "staleness_weight_decay": self.staleness_weight_decay,
                "total_samples": sum(data_sizes),
            },
        }

        self.record_aggregation(result)
        return result

    def _compute_staleness_aware_weights(
        self, client_updates: List[Dict[str, Any]], staleness_values: List[int]
    ) -> List[float]:
        """Compute aggregation weights considering staleness."""
        # Base weights from data sizes
        base_weights = self.compute_client_weights(client_updates)

        # Apply staleness penalty
        staleness_weights = []
        for staleness in staleness_values:
            staleness_weight = self.staleness_weight_decay**staleness
            staleness_weights.append(staleness_weight)

        # Combine base weights with staleness weights
        combined_weights = [
            base_weight * staleness_weight
            for base_weight, staleness_weight in zip(base_weights, staleness_weights)
        ]

        # Normalize weights
        total_weight = sum(combined_weights)
        if total_weight > 0:
            combined_weights = [w / total_weight for w in combined_weights]
        else:
            combined_weights = [1.0 / len(combined_weights)] * len(combined_weights)

        return combined_weights

    def get_async_stats(self) -> Dict[str, Any]:
        """Get asynchronous aggregation statistics."""
        base_stats = self.get_aggregation_stats()

        async_stats = {
            "is_running": self.is_running,
            "global_version": self.global_version,
            "min_updates_for_aggregation": self.min_updates_for_aggregation,
            "max_updates_per_round": self.max_updates_per_round,
            "aggregation_frequency": self.aggregation_frequency,
            "staleness_weight_decay": self.staleness_weight_decay,
            "buffer_status": self.update_buffer.get_buffer_status(),
        }

        base_stats.update(async_stats)
        return base_stats


class AsyncFederatedServer(FederatedServer):
    """Asynchronous federated server implementation."""

    def __init__(self, server_id: str, config, model: FederatedModel):
        super().__init__(server_id, config, model)

        # Async-specific configuration
        self.async_config = config.async_config if hasattr(config, "async_config") else {}

        # Initialize async aggregator
        self.async_aggregator = AsyncFedAvg("async_server_aggregator", self.async_config)

        # Async state
        self.client_connections = {}
        self.active_training_sessions = {}

        # Threading for concurrent client handling
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_clients)

        self.logger.info("Asynchronous federated server initialized")

    def start_async_training(self):
        """Start asynchronous training process."""
        if self._is_running:
            self.logger.warning("Server already running")
            return

        self._is_running = True

        # Start async aggregation
        self.async_aggregator.start_async_aggregation(self._update_global_model)

        self.logger.info("Asynchronous training started")

    def stop_async_training(self):
        """Stop asynchronous training process."""
        self._is_running = False

        # Stop async aggregation
        self.async_aggregator.stop_async_aggregation()

        # Shutdown executor
        self.executor.shutdown(wait=True)

        self.logger.info("Asynchronous training stopped")

    def handle_client_update_async(
        self, client_id: str, client_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle client update asynchronously."""
        if not self._is_running:
            return {"status": "error", "message": "Server not running"}

        # Add global version to update
        client_update["global_version"] = self.async_aggregator.global_version
        client_update["client_id"] = client_id

        # Add update to buffer
        success = self.async_aggregator.add_client_update(client_update)

        if success:
            response = {
                "status": "accepted",
                "global_version": self.async_aggregator.global_version,
                "global_weights": self.get_global_model(),
                "server_time": time.time(),
            }
        else:
            response = {
                "status": "rejected",
                "reason": "stale_update",
                "global_version": self.async_aggregator.global_version,
                "global_weights": self.get_global_model(),
                "server_time": time.time(),
            }

        return response

    def _update_global_model(self, new_weights: List[np.ndarray]):
        """Update global model with new weights."""
        self.update_global_model(new_weights)
        self.logger.debug(f"Global model updated to version {self.async_aggregator.global_version}")

    def get_server_status_async(self) -> Dict[str, Any]:
        """Get comprehensive async server status."""
        base_status = self.get_server_status()

        async_status = {
            "async_aggregator_stats": self.async_aggregator.get_async_stats(),
            "active_training_sessions": len(self.active_training_sessions),
            "thread_pool_active": not self.executor._shutdown,
        }

        base_status.update(async_status)
        return base_status


class AsynchronousFederatedLearning:
    """
    Main coordinator for asynchronous federated learning.

    Manages the entire async FL workflow including client coordination,
    asynchronous aggregation, and global model updates.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Create async server (would need actual model in practice)
        self.server = None  # AsyncFederatedServer would be initialized here

        # Async FL configuration
        self.enable_async_evaluation = config.get("enable_async_evaluation", True)
        self.evaluation_frequency = config.get("evaluation_frequency", 30.0)  # seconds
        self.convergence_check_frequency = config.get("convergence_check_frequency", 60.0)

        # State tracking
        self.training_start_time = None
        self.evaluation_history = []
        self.convergence_history = []

        self.logger = logging.getLogger("AsynchronousFederatedLearning")
        self.logger.info("Asynchronous federated learning coordinator initialized")

    async def start_async_training(self, clients: List[FederatedClient]):
        """Start asynchronous federated training."""
        self.training_start_time = time.time()

        # Start server
        if self.server:
            self.server.start_async_training()

        # Start client training tasks
        client_tasks = []
        for client in clients:
            task = asyncio.create_task(self._async_client_training(client))
            client_tasks.append(task)

        # Start evaluation task if enabled
        if self.enable_async_evaluation:
            eval_task = asyncio.create_task(self._async_evaluation_loop())
            client_tasks.append(eval_task)

        # Start convergence checking task
        convergence_task = asyncio.create_task(self._async_convergence_check())
        client_tasks.append(convergence_task)

        self.logger.info(f"Started async training with {len(clients)} clients")

        # Wait for all tasks
        await asyncio.gather(*client_tasks, return_exceptions=True)

    async def _async_client_training(self, client: FederatedClient):
        """Asynchronous training loop for a single client."""
        while True:
            try:
                # Get current global model
                if self.server:
                    global_weights = self.server.get_global_model()

                    # Perform local training
                    local_result = client.local_training(global_weights)

                    # Send update to server
                    response = self.server.handle_client_update_async(
                        client.client_id, local_result
                    )

                    # Handle server response
                    if response["status"] == "accepted":
                        self.logger.debug(f"Update accepted from client {client.client_id}")
                    else:
                        self.logger.debug(
                            f"Update rejected from client {client.client_id}: {response.get('reason')}"
                        )

                # Sleep before next update (simulate realistic training intervals)
                await asyncio.sleep(np.random.exponential(10.0))  # Average 10 seconds

            except Exception as e:
                self.logger.error(f"Error in client {client.client_id} training: {str(e)}")
                await asyncio.sleep(5.0)  # Wait before retrying

    async def _async_evaluation_loop(self):
        """Asynchronous evaluation loop."""
        while True:
            try:
                await asyncio.sleep(self.evaluation_frequency)

                if self.server:
                    # Perform evaluation (simplified)
                    evaluation_result = {
                        "timestamp": time.time(),
                        "global_version": getattr(
                            self.server.async_aggregator, "global_version", 0
                        ),
                        "server_stats": self.server.get_server_status_async(),
                        "training_time": (
                            time.time() - self.training_start_time
                            if self.training_start_time
                            else 0
                        ),
                    }

                    self.evaluation_history.append(evaluation_result)

                    # Keep only recent evaluations
                    max_evaluations = self.config.get("max_evaluation_history", 1000)
                    if len(self.evaluation_history) > max_evaluations:
                        self.evaluation_history = self.evaluation_history[-max_evaluations:]

                    self.logger.info(
                        f"Async evaluation completed (version {evaluation_result.get('global_version')})"
                    )

            except Exception as e:
                self.logger.error(f"Error in async evaluation: {str(e)}")

    async def _async_convergence_check(self):
        """Asynchronous convergence checking."""
        while True:
            try:
                await asyncio.sleep(self.convergence_check_frequency)

                if self.server and len(self.evaluation_history) >= 2:
                    # Simple convergence check based on global version changes
                    recent_evaluations = self.evaluation_history[-5:]
                    version_changes = [
                        eval_result.get("global_version", 0) for eval_result in recent_evaluations
                    ]

                    if len(set(version_changes)) <= 1:
                        # No version changes - potential convergence or no activity
                        convergence_result = {
                            "timestamp": time.time(),
                            "converged": False,
                            "reason": "no_activity",
                            "recent_versions": version_changes,
                        }
                    else:
                        # Check rate of change
                        version_rate = (version_changes[-1] - version_changes[0]) / len(
                            version_changes
                        )
                        convergence_result = {
                            "timestamp": time.time(),
                            "converged": version_rate < 0.1,  # Arbitrary threshold
                            "version_rate": version_rate,
                            "recent_versions": version_changes,
                        }

                    self.convergence_history.append(convergence_result)

                    if convergence_result["converged"]:
                        self.logger.info("Potential convergence detected")

            except Exception as e:
                self.logger.error(f"Error in convergence check: {str(e)}")

    def get_async_training_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of async training."""
        summary = {
            "training_time": (
                time.time() - self.training_start_time if self.training_start_time else 0
            ),
            "num_evaluations": len(self.evaluation_history),
            "num_convergence_checks": len(self.convergence_history),
            "current_global_version": (
                getattr(self.server.async_aggregator, "global_version", 0) if self.server else 0
            ),
            "server_status": (self.server.get_server_status_async() if self.server else {}),
        }

        # Add latest evaluation
        if self.evaluation_history:
            summary["latest_evaluation"] = self.evaluation_history[-1]

        # Add convergence status
        if self.convergence_history:
            summary["latest_convergence_check"] = self.convergence_history[-1]

        return summary
