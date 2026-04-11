"""
Federated Learning Manager

Central coordinator for federated learning workflows, managing clients,
servers, and the overall training process.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from ..aggregation.byzantine_robust import ByzantineRobustAggregator
from ..aggregation.fedavg import FedAvgAggregator
from ..aggregation.secure_aggregation import SecureAggregator
from .base import FederatedClient, FederatedModel, FederatedServer
from .config import FederatedConfig
from .exceptions import ClientError, FederatedLearningError, ServerError


class FederatedManager:
    """
    Central manager for federated learning workflows.

    Coordinates the entire federated learning process including client management,
    server coordination, and training orchestration.
    """

    def __init__(self, config: FederatedConfig):
        self.config = config
        self.server: Optional[FederatedServer] = None
        self.clients: Dict[str, FederatedClient] = {}

        # Training state
        self.is_training = False
        self.current_round = 0
        self.training_start_time = None
        self.training_history = []

        # Performance tracking
        self.round_times = []
        self.client_participation = []
        self.convergence_metrics = []

        self.logger = logging.getLogger("FederatedManager")
        self.logger.info("Federated learning manager initialized")

    def set_server(self, server: FederatedServer):
        """Set the federated server."""
        self.server = server
        self.logger.info(f"Server set: {server.server_id}")

    def register_client(self, client: FederatedClient) -> bool:
        """Register a client."""
        if self.server and not self.server.register_client(client):
            return False

        self.clients[client.client_id] = client
        self.logger.info(f"Client registered: {client.client_id}")
        return True

    def unregister_client(self, client_id: str) -> bool:
        """Unregister a client."""
        if client_id in self.clients:
            del self.clients[client_id]
            if self.server:
                self.server.unregister_client(client_id)
            self.logger.info(f"Client unregistered: {client_id}")
            return True
        return False

    def start_training(self) -> Dict[str, Any]:
        """Start federated training process."""
        if self.is_training:
            raise FederatedLearningError("Training already in progress")

        if not self.server:
            raise FederatedLearningError("No server configured")

        if len(self.clients) < self.config.server.min_clients:
            raise FederatedLearningError(
                f"Insufficient clients. Need {self.config.server.min_clients}, have {len(self.clients)}"
            )

        self.is_training = True
        self.training_start_time = time.time()
        self.current_round = 0

        training_result = {
            "status": "started",
            "start_time": self.training_start_time,
            "num_clients": len(self.clients),
            "config": self.config.to_dict(),
        }

        self.logger.info(f"Training started with {len(self.clients)} clients")
        return training_result

    def stop_training(self) -> Dict[str, Any]:
        """Stop federated training process."""
        if not self.is_training:
            return {"status": "not_running"}

        self.is_training = False
        training_duration = (
            time.time() - self.training_start_time if self.training_start_time else 0
        )

        result = {
            "status": "stopped",
            "total_rounds": self.current_round,
            "training_duration": training_duration,
            "avg_round_time": (
                sum(self.round_times) / len(self.round_times) if self.round_times else 0
            ),
        }

        self.logger.info(f"Training stopped after {self.current_round} rounds")
        return result

    def execute_round(self) -> Dict[str, Any]:
        """Execute one round of federated learning."""
        if not self.is_training:
            raise FederatedLearningError("Training not started")

        if not self.server:
            raise ServerError("No server available")

        round_start_time = time.time()

        # Start round
        if not self.server.start_round():
            raise ServerError("Failed to start round")

        # Select clients for this round
        selected_client_ids = self.server.select_clients()
        selected_clients = [self.clients[cid] for cid in selected_client_ids if cid in self.clients]

        self.logger.info(
            f"Round {self.current_round + 1}: Selected {len(selected_clients)} clients"
        )

        # Get current global model
        global_weights = self.server.get_global_model()

        # Collect client updates
        client_updates = []
        for client in selected_clients:
            try:
                # Update client model
                client.update_model(global_weights)

                # Perform local training
                local_result = client.local_training(global_weights)

                # Collect update
                update = client.get_model_update()
                update.update(local_result)

                client_updates.append(update)
                self.server.collect_updates(client.client_id, update)

            except Exception as e:
                self.logger.error(f"Error with client {client.client_id}: {str(e)}")

        # Aggregate updates
        if client_updates:
            aggregated_weights = self.server.aggregate_updates(client_updates)
            self.server.update_global_model(aggregated_weights)

        # Finish round
        round_metrics = self.server.finish_round()

        round_time = time.time() - round_start_time
        self.round_times.append(round_time)
        self.client_participation.append(len(client_updates))

        self.current_round += 1

        # Check convergence
        converged = self.server.check_convergence()
        if converged:
            self.logger.info("Convergence detected")

        round_result = {
            "round": self.current_round,
            "round_time": round_time,
            "participating_clients": len(client_updates),
            "round_metrics": round_metrics,
            "converged": converged,
            "global_model_updated": len(client_updates) > 0,
        }

        self.training_history.append(round_result)
        return round_result

    def run_training(self, max_rounds: Optional[int] = None) -> Dict[str, Any]:
        """Run complete federated training process."""
        if max_rounds is None:
            max_rounds = self.config.server.rounds

        # Start training
        start_result = self.start_training()

        try:
            # Execute rounds
            for round_num in range(max_rounds):
                round_result = self.execute_round()

                self.logger.info(f"Round {round_num + 1}/{max_rounds} completed")

                # Check for early stopping
                if round_result.get("converged", False):
                    self.logger.info("Early stopping due to convergence")
                    break

                # Check if we should continue
                if not self.is_training:
                    break

        except Exception as e:
            self.logger.error(f"Training error: {str(e)}")
            raise

        finally:
            # Stop training
            stop_result = self.stop_training()

        return {
            "start_result": start_result,
            "stop_result": stop_result,
            "total_rounds": self.current_round,
            "training_history": self.training_history,
        }

    async def run_training_async(self, max_rounds: Optional[int] = None) -> Dict[str, Any]:
        """Run federated training asynchronously."""
        # This would implement async training with concurrent client updates
        return await asyncio.to_thread(self.run_training, max_rounds)

    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status."""
        status = {
            "is_training": self.is_training,
            "current_round": self.current_round,
            "num_clients": len(self.clients),
            "training_duration": (
                time.time() - self.training_start_time if self.training_start_time else 0
            ),
        }

        if self.server:
            status["server_status"] = self.server.get_server_status()

        if self.round_times:
            status["avg_round_time"] = sum(self.round_times) / len(self.round_times)
            status["total_training_time"] = sum(self.round_times)

        return status

    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """Get status of a specific client."""
        if client_id not in self.clients:
            return {"error": "Client not found"}

        client = self.clients[client_id]
        return client.get_client_info()

    def get_comprehensive_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of federated learning session."""
        summary = {
            "config": self.config.to_dict(),
            "training_status": self.get_training_status(),
            "performance_metrics": {
                "total_rounds": self.current_round,
                "avg_round_time": (
                    sum(self.round_times) / len(self.round_times) if self.round_times else 0
                ),
                "avg_client_participation": (
                    sum(self.client_participation) / len(self.client_participation)
                    if self.client_participation
                    else 0
                ),
                "round_time_std": np.std(self.round_times) if self.round_times else 0,
            },
        }

        # Add convergence information
        if self.server and hasattr(self.server, "server_metrics"):
            convergence_rounds = self.server.server_metrics.get("convergence_rounds")
            if convergence_rounds:
                summary["convergence"] = {
                    "achieved": True,
                    "convergence_round": convergence_rounds,
                    "rounds_to_convergence": convergence_rounds,
                }
            else:
                summary["convergence"] = {"achieved": False}

        return summary
