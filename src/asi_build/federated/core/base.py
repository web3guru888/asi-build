"""
Base classes for federated learning

Core abstractions for federated learning components.
"""

import abc
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union
import tensorflow as tf
import numpy as np

from .config import FederatedConfig, ClientConfig, ServerConfig
from .exceptions import FederatedLearningError, ModelError, ClientError, ServerError


class FederatedModel(abc.ABC):
    """Abstract base class for federated learning models."""
    
    def __init__(self, model_config: Dict[str, Any]):
        self.model_config = model_config
        self.model: Optional[tf.keras.Model] = None
        self._compiled = False
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abc.abstractmethod
    def build_model(self) -> tf.keras.Model:
        """Build and return the TensorFlow model."""
        pass
    
    @abc.abstractmethod
    def compile_model(self, optimizer: str = "adam", 
                     loss: str = "categorical_crossentropy",
                     metrics: List[str] = None) -> None:
        """Compile the model with specified parameters."""
        pass
    
    def get_weights(self) -> List[np.ndarray]:
        """Get model weights."""
        if self.model is None:
            raise ModelError("Model not built", model_type=self.__class__.__name__)
        return self.model.get_weights()
    
    def set_weights(self, weights: List[np.ndarray]) -> None:
        """Set model weights."""
        if self.model is None:
            raise ModelError("Model not built", model_type=self.__class__.__name__)
        self.model.set_weights(weights)
    
    def get_model_size(self) -> Dict[str, int]:
        """Get model size information."""
        if self.model is None:
            raise ModelError("Model not built", model_type=self.__class__.__name__)
        
        total_params = self.model.count_params()
        trainable_params = sum([tf.reduce_prod(var.shape) for var in self.model.trainable_variables])
        
        return {
            "total_parameters": total_params,
            "trainable_parameters": int(trainable_params),
            "non_trainable_parameters": total_params - int(trainable_params)
        }
    
    def save_model(self, path: str) -> None:
        """Save model to disk."""
        if self.model is None:
            raise ModelError("Model not built", model_type=self.__class__.__name__)
        self.model.save(path)
        self.logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str) -> None:
        """Load model from disk."""
        self.model = tf.keras.models.load_model(path)
        self._compiled = True
        self.logger.info(f"Model loaded from {path}")


class FederatedClient(abc.ABC):
    """Abstract base class for federated learning clients."""
    
    def __init__(self, client_id: str, config: ClientConfig, model: FederatedModel):
        self.client_id = client_id
        self.config = config
        self.model = model
        self.round_number = 0
        self.training_history = []
        self.local_data_size = 0
        self.logger = logging.getLogger(f"Client-{client_id}")
        
        # Training state
        self._is_training = False
        self._last_update_time = None
        
        # Performance metrics
        self.metrics = {
            "training_time": [],
            "loss_history": [],
            "accuracy_history": [],
            "communication_overhead": 0
        }
    
    @abc.abstractmethod
    def load_data(self) -> Tuple[tf.data.Dataset, tf.data.Dataset]:
        """Load training and validation datasets."""
        pass
    
    @abc.abstractmethod
    def local_training(self, global_weights: List[np.ndarray]) -> Dict[str, Any]:
        """Perform local training and return updated weights and metrics."""
        pass
    
    def update_model(self, global_weights: List[np.ndarray]) -> None:
        """Update local model with global weights."""
        self.model.set_weights(global_weights)
        self._last_update_time = time.time()
        self.logger.debug(f"Model updated for round {self.round_number}")
    
    def get_model_update(self) -> Dict[str, Any]:
        """Get model update for aggregation."""
        weights = self.model.get_weights()
        return {
            "client_id": self.client_id,
            "weights": weights,
            "data_size": self.local_data_size,
            "round_number": self.round_number,
            "timestamp": time.time(),
            "metrics": self.get_latest_metrics()
        }
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """Get latest training metrics."""
        if not self.training_history:
            return {}
        
        latest = self.training_history[-1]
        return {
            "loss": latest.get("loss", 0.0),
            "accuracy": latest.get("accuracy", 0.0),
            "epochs_completed": len(self.training_history),
            "training_time": sum(self.metrics["training_time"])
        }
    
    def evaluate_model(self, test_data: tf.data.Dataset) -> Dict[str, float]:
        """Evaluate model on test data."""
        if self.model.model is None:
            raise ClientError("Model not initialized", self.client_id)
        
        start_time = time.time()
        results = self.model.model.evaluate(test_data, verbose=0)
        evaluation_time = time.time() - start_time
        
        # Handle both single metric and multiple metrics
        if isinstance(results, (list, tuple)):
            metrics = dict(zip(self.model.model.metrics_names, results))
        else:
            metrics = {"loss": results}
        
        metrics["evaluation_time"] = evaluation_time
        return metrics
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get client information."""
        return {
            "client_id": self.client_id,
            "round_number": self.round_number,
            "data_size": self.local_data_size,
            "is_training": self._is_training,
            "last_update_time": self._last_update_time,
            "config": self.config.to_dict() if hasattr(self.config, 'to_dict') else str(self.config)
        }


class FederatedServer(abc.ABC):
    """Abstract base class for federated learning servers."""
    
    def __init__(self, server_id: str, config: ServerConfig, model: FederatedModel):
        self.server_id = server_id
        self.config = config
        self.model = model
        self.round_number = 0
        self.clients: Dict[str, FederatedClient] = {}
        self.client_updates: Dict[str, Dict[str, Any]] = {}
        self.global_metrics_history = []
        self.logger = logging.getLogger(f"Server-{server_id}")
        
        # Server state
        self._is_running = False
        self._current_round_start_time = None
        
        # Performance tracking
        self.server_metrics = {
            "round_times": [],
            "aggregation_times": [],
            "communication_overhead": 0,
            "total_clients_served": 0,
            "convergence_rounds": None
        }
    
    @abc.abstractmethod
    def aggregate_updates(self, client_updates: List[Dict[str, Any]]) -> List[np.ndarray]:
        """Aggregate client updates into global model."""
        pass
    
    @abc.abstractmethod
    def select_clients(self) -> List[str]:
        """Select clients for the current round."""
        pass
    
    def register_client(self, client: FederatedClient) -> bool:
        """Register a new client."""
        if len(self.clients) >= self.config.max_clients:
            self.logger.warning(f"Maximum clients ({self.config.max_clients}) reached")
            return False
        
        self.clients[client.client_id] = client
        self.server_metrics["total_clients_served"] += 1
        self.logger.info(f"Client {client.client_id} registered. Total clients: {len(self.clients)}")
        return True
    
    def unregister_client(self, client_id: str) -> bool:
        """Unregister a client."""
        if client_id in self.clients:
            del self.clients[client_id]
            if client_id in self.client_updates:
                del self.client_updates[client_id]
            self.logger.info(f"Client {client_id} unregistered")
            return True
        return False
    
    def start_round(self) -> bool:
        """Start a new federated learning round."""
        if len(self.clients) < self.config.min_clients:
            self.logger.warning(f"Insufficient clients. Need {self.config.min_clients}, have {len(self.clients)}")
            return False
        
        self.round_number += 1
        self._current_round_start_time = time.time()
        self.client_updates.clear()
        
        self.logger.info(f"Starting round {self.round_number}")
        return True
    
    def collect_updates(self, client_id: str, update: Dict[str, Any]) -> bool:
        """Collect update from a client."""
        if client_id not in self.clients:
            self.logger.warning(f"Update from unregistered client {client_id}")
            return False
        
        self.client_updates[client_id] = update
        self.logger.debug(f"Collected update from client {client_id}")
        return True
    
    def finish_round(self) -> Dict[str, Any]:
        """Finish the current round and return metrics."""
        if self._current_round_start_time is None:
            raise ServerError("Round not started", round_number=self.round_number)
        
        round_time = time.time() - self._current_round_start_time
        self.server_metrics["round_times"].append(round_time)
        
        # Calculate round metrics
        round_metrics = {
            "round_number": self.round_number,
            "round_time": round_time,
            "participating_clients": len(self.client_updates),
            "total_registered_clients": len(self.clients),
            "timestamp": time.time()
        }
        
        # Add client metrics if available
        if self.client_updates:
            client_losses = [update.get("metrics", {}).get("loss", 0) 
                           for update in self.client_updates.values()]
            client_accuracies = [update.get("metrics", {}).get("accuracy", 0) 
                               for update in self.client_updates.values()]
            
            if client_losses:
                round_metrics["avg_client_loss"] = np.mean(client_losses)
                round_metrics["std_client_loss"] = np.std(client_losses)
            
            if client_accuracies:
                round_metrics["avg_client_accuracy"] = np.mean(client_accuracies)
                round_metrics["std_client_accuracy"] = np.std(client_accuracies)
        
        self.global_metrics_history.append(round_metrics)
        self.logger.info(f"Round {self.round_number} completed in {round_time:.2f}s with {len(self.client_updates)} clients")
        
        return round_metrics
    
    def get_global_model(self) -> List[np.ndarray]:
        """Get current global model weights."""
        return self.model.get_weights()
    
    def update_global_model(self, new_weights: List[np.ndarray]) -> None:
        """Update global model with new weights."""
        self.model.set_weights(new_weights)
        self.logger.debug(f"Global model updated for round {self.round_number}")
    
    def check_convergence(self, threshold: float = 0.001) -> bool:
        """Check if the model has converged."""
        if len(self.global_metrics_history) < 2:
            return False
        
        # Check loss convergence
        recent_losses = [m.get("avg_client_loss", float('inf')) 
                        for m in self.global_metrics_history[-5:]]
        
        if len(recent_losses) >= 2:
            loss_change = abs(recent_losses[-1] - recent_losses[-2])
            if loss_change < threshold:
                if self.server_metrics["convergence_rounds"] is None:
                    self.server_metrics["convergence_rounds"] = self.round_number
                    self.logger.info(f"Model converged at round {self.round_number}")
                return True
        
        return False
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get comprehensive server status."""
        return {
            "server_id": self.server_id,
            "round_number": self.round_number,
            "is_running": self._is_running,
            "registered_clients": len(self.clients),
            "max_clients": self.config.max_clients,
            "min_clients": self.config.min_clients,
            "client_updates_received": len(self.client_updates),
            "total_rounds_completed": len(self.global_metrics_history),
            "convergence_rounds": self.server_metrics["convergence_rounds"],
            "avg_round_time": np.mean(self.server_metrics["round_times"]) if self.server_metrics["round_times"] else 0,
            "config": self.config.to_dict() if hasattr(self.config, 'to_dict') else str(self.config)
        }