"""
Personalized Federated Learning

Implementation of personalized federated learning algorithms that adapt
global models to individual client data distributions.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import tensorflow as tf
from abc import ABC, abstractmethod

from ..core.base import FederatedClient, FederatedServer, FederatedModel
from ..core.exceptions import FederatedLearningError, ModelError
from ..aggregation.base_aggregator import BaseAggregator


class PersonalizationStrategy(ABC):
    """Abstract base class for personalization strategies."""
    
    @abstractmethod
    def personalize_model(self, global_weights: List[np.ndarray],
                         local_weights: List[np.ndarray],
                         client_data: tf.data.Dataset) -> List[np.ndarray]:
        """Personalize global model for a specific client."""
        pass


class LocalFinetuning(PersonalizationStrategy):
    """Personalization through local fine-tuning."""
    
    def __init__(self, finetune_epochs: int = 5, learning_rate: float = 0.001):
        self.finetune_epochs = finetune_epochs
        self.learning_rate = learning_rate
        self.logger = logging.getLogger("LocalFinetuning")
    
    def personalize_model(self, global_weights: List[np.ndarray],
                         local_weights: List[np.ndarray],
                         client_data: tf.data.Dataset) -> List[np.ndarray]:
        """Fine-tune global model on local data."""
        # Start with global weights
        personalized_weights = [w.copy() for w in global_weights]
        
        # This is a simplified version - in practice, you'd need the actual model
        # to perform gradient-based fine-tuning
        self.logger.info(f"Fine-tuning with {self.finetune_epochs} epochs")
        
        return personalized_weights


class LayerWisePersonalization(PersonalizationStrategy):
    """Personalization by mixing global and local layers."""
    
    def __init__(self, personal_layers: List[int], mixing_ratio: float = 0.5):
        self.personal_layers = personal_layers
        self.mixing_ratio = mixing_ratio
        self.logger = logging.getLogger("LayerWisePersonalization")
    
    def personalize_model(self, global_weights: List[np.ndarray],
                         local_weights: List[np.ndarray],
                         client_data: tf.data.Dataset) -> List[np.ndarray]:
        """Personalize specific layers while keeping others global."""
        if len(global_weights) != len(local_weights):
            raise ModelError("Global and local weights dimension mismatch")
        
        personalized_weights = []
        for i, (global_w, local_w) in enumerate(zip(global_weights, local_weights)):
            if i in self.personal_layers:
                # Mix global and local weights for personal layers
                mixed_weight = (
                    self.mixing_ratio * local_w + 
                    (1 - self.mixing_ratio) * global_w
                )
                personalized_weights.append(mixed_weight)
            else:
                # Use global weights for shared layers
                personalized_weights.append(global_w.copy())
        
        return personalized_weights


class AttentionBasedPersonalization(PersonalizationStrategy):
    """Attention-based personalization strategy."""
    
    def __init__(self, attention_dim: int = 64, temperature: float = 1.0):
        self.attention_dim = attention_dim
        self.temperature = temperature
        self.logger = logging.getLogger("AttentionPersonalization")
    
    def personalize_model(self, global_weights: List[np.ndarray],
                         local_weights: List[np.ndarray],
                         client_data: tf.data.Dataset) -> List[np.ndarray]:
        """Use attention mechanism to blend global and local knowledge."""
        personalized_weights = []
        
        for global_w, local_w in zip(global_weights, local_weights):
            # Compute attention weights (simplified)
            global_norm = np.linalg.norm(global_w)
            local_norm = np.linalg.norm(local_w)
            
            # Attention scores based on weight magnitudes
            attention_global = np.exp(global_norm / self.temperature)
            attention_local = np.exp(local_norm / self.temperature)
            
            # Normalize attention
            total_attention = attention_global + attention_local
            alpha_global = attention_global / total_attention
            alpha_local = attention_local / total_attention
            
            # Weighted combination
            personalized_w = alpha_global * global_w + alpha_local * local_w
            personalized_weights.append(personalized_w)
        
        return personalized_weights


class FedPerAvg(BaseAggregator):
    """
    FedPerAvg: Federated Personalized Averaging
    
    Combines global model training with personalization through
    local fine-tuning or parameter mixing.
    """
    
    def __init__(self, aggregator_id: str = "fedperavg", config: Dict[str, Any] = None):
        super().__init__(aggregator_id, config)
        
        # Personalization parameters
        self.personalization_strategy = self.config.get("personalization_strategy", "local_finetuning")
        self.alpha = self.config.get("alpha", 0.5)  # Mixing parameter
        self.personal_layers = self.config.get("personal_layers", [])
        self.global_rounds = self.config.get("global_rounds", 1)
        self.personal_rounds = self.config.get("personal_rounds", 5)
        
        # Initialize personalization strategy
        self.strategy = self._create_personalization_strategy()
        
        # Client personalization states
        self.client_personal_weights = {}
        self.client_personalization_history = {}
        
        self.logger.info(f"FedPerAvg initialized with strategy: {self.personalization_strategy}")
    
    def _create_personalization_strategy(self) -> PersonalizationStrategy:
        """Create the personalization strategy."""
        if self.personalization_strategy == "local_finetuning":
            return LocalFinetuning(
                finetune_epochs=self.personal_rounds,
                learning_rate=self.config.get("personal_lr", 0.001)
            )
        elif self.personalization_strategy == "layer_wise":
            return LayerWisePersonalization(
                personal_layers=self.personal_layers,
                mixing_ratio=self.alpha
            )
        elif self.personalization_strategy == "attention":
            return AttentionBasedPersonalization(
                attention_dim=self.config.get("attention_dim", 64),
                temperature=self.config.get("temperature", 1.0)
            )
        else:
            raise ValueError(f"Unknown personalization strategy: {self.personalization_strategy}")
    
    def aggregate(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate client updates with personalization."""
        start_time = time.time()
        
        # Validate updates
        self.validate_updates(client_updates)
        
        # Extract client information
        client_weights_list = [update["weights"] for update in client_updates]
        data_sizes = [update["data_size"] for update in client_updates]
        client_ids = [update["client_id"] for update in client_updates]
        
        # Store client personal weights
        for client_id, weights in zip(client_ids, client_weights_list):
            self.client_personal_weights[client_id] = [w.copy() for w in weights]
        
        # Compute global aggregation (standard FedAvg)
        aggregation_weights = self.compute_client_weights(client_updates)
        global_weights = self.weighted_average(client_weights_list, aggregation_weights)
        
        # Apply gradient clipping and noise
        global_weights = self.clip_weights(global_weights)
        global_weights = self.add_noise(global_weights)
        
        aggregation_time = time.time() - start_time
        
        # Compute personalization metrics
        personalization_metrics = self._compute_personalization_metrics(
            client_ids, client_weights_list, global_weights
        )
        
        result = {
            "aggregated_weights": global_weights,
            "num_clients": len(client_updates),
            "aggregation_time": aggregation_time,
            "aggregation_method": "fedperavg",
            "personalization_strategy": self.personalization_strategy,
            "metadata": {
                "global_rounds": self.global_rounds,
                "personal_rounds": self.personal_rounds,
                "alpha": self.alpha,
                "personalization_metrics": personalization_metrics,
                "total_samples": sum(data_sizes)
            }
        }
        
        self.record_aggregation(result)
        self.logger.info(f"FedPerAvg aggregation completed in {aggregation_time:.3f}s")
        
        return result
    
    def personalize_for_client(self, client_id: str, global_weights: List[np.ndarray],
                             client_data: tf.data.Dataset) -> List[np.ndarray]:
        """Generate personalized model for a specific client."""
        if client_id not in self.client_personal_weights:
            # First time - use global weights as local weights
            local_weights = [w.copy() for w in global_weights]
        else:
            local_weights = self.client_personal_weights[client_id]
        
        # Apply personalization strategy
        personalized_weights = self.strategy.personalize_model(
            global_weights, local_weights, client_data
        )
        
        # Update client history
        if client_id not in self.client_personalization_history:
            self.client_personalization_history[client_id] = []
        
        self.client_personalization_history[client_id].append({
            "timestamp": time.time(),
            "strategy": self.personalization_strategy,
            "global_model_version": getattr(self, 'round_number', 0)
        })
        
        return personalized_weights
    
    def _compute_personalization_metrics(self, client_ids: List[str],
                                       client_weights_list: List[List[np.ndarray]],
                                       global_weights: List[np.ndarray]) -> Dict[str, Any]:
        """Compute metrics about personalization."""
        metrics = {
            "num_personalized_clients": len(client_ids),
            "personalization_strategy": self.personalization_strategy
        }
        
        # Compute diversity metrics
        client_similarities = []
        global_similarities = []
        
        for weights in client_weights_list:
            # Similarity between clients
            for other_weights in client_weights_list:
                if weights is not other_weights:
                    similarity = self._compute_weight_similarity(weights, other_weights)
                    client_similarities.append(similarity)
            
            # Similarity to global model
            global_sim = self._compute_weight_similarity(weights, global_weights)
            global_similarities.append(global_sim)
        
        if client_similarities:
            metrics["avg_client_similarity"] = np.mean(client_similarities)
            metrics["std_client_similarity"] = np.std(client_similarities)
        
        if global_similarities:
            metrics["avg_global_similarity"] = np.mean(global_similarities)
            metrics["std_global_similarity"] = np.std(global_similarities)
        
        return metrics
    
    def _compute_weight_similarity(self, weights1: List[np.ndarray],
                                 weights2: List[np.ndarray]) -> float:
        """Compute cosine similarity between two weight vectors."""
        # Flatten and concatenate all weights
        flat1 = np.concatenate([w.flatten() for w in weights1])
        flat2 = np.concatenate([w.flatten() for w in weights2])
        
        # Compute cosine similarity
        dot_product = np.dot(flat1, flat2)
        norm1 = np.linalg.norm(flat1)
        norm2 = np.linalg.norm(flat2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_client_personalization_status(self, client_id: str) -> Dict[str, Any]:
        """Get personalization status for a specific client."""
        return {
            "client_id": client_id,
            "has_personal_weights": client_id in self.client_personal_weights,
            "personalization_history": self.client_personalization_history.get(client_id, []),
            "strategy": self.personalization_strategy,
            "num_personalizations": len(self.client_personalization_history.get(client_id, []))
        }


class PersonalizedFederatedLearning:
    """
    Main manager for personalized federated learning.
    
    Coordinates global model training with client-specific personalization.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.aggregator = FedPerAvg("personalized_aggregator", config.get("aggregator", {}))
        
        # Personalization parameters
        self.enable_global_training = config.get("enable_global_training", True)
        self.enable_personalization = config.get("enable_personalization", True)
        self.personalization_frequency = config.get("personalization_frequency", 1)
        
        # State management
        self.current_round = 0
        self.global_model_weights = None
        self.client_personalized_models = {}
        
        self.logger = logging.getLogger("PersonalizedFL")
        self.logger.info("Personalized federated learning manager initialized")
    
    def training_round(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute one round of personalized federated learning."""
        round_start_time = time.time()
        
        results = {
            "round": self.current_round,
            "global_training": None,
            "personalization": None
        }
        
        # Global model training
        if self.enable_global_training:
            global_result = self.aggregator.aggregate(client_updates)
            self.global_model_weights = global_result["aggregated_weights"]
            results["global_training"] = global_result
            
            self.logger.info(f"Global training completed for round {self.current_round}")
        
        # Client personalization
        if (self.enable_personalization and 
            self.current_round % self.personalization_frequency == 0):
            
            personalization_results = []
            for update in client_updates:
                client_id = update["client_id"]
                
                # Get client data (this would need to be provided in practice)
                client_data = update.get("client_data")
                if client_data and self.global_model_weights:
                    personalized_weights = self.aggregator.personalize_for_client(
                        client_id, self.global_model_weights, client_data
                    )
                    
                    self.client_personalized_models[client_id] = personalized_weights
                    
                    personalization_results.append({
                        "client_id": client_id,
                        "personalized": True,
                        "timestamp": time.time()
                    })
            
            results["personalization"] = {
                "num_clients_personalized": len(personalization_results),
                "personalization_results": personalization_results
            }
            
            self.logger.info(f"Personalization completed for {len(personalization_results)} clients")
        
        self.current_round += 1
        round_time = time.time() - round_start_time
        results["round_time"] = round_time
        
        return results
    
    def get_model_for_client(self, client_id: str) -> Optional[List[np.ndarray]]:
        """Get the best model (personalized or global) for a client."""
        if client_id in self.client_personalized_models:
            return self.client_personalized_models[client_id]
        elif self.global_model_weights:
            return self.global_model_weights
        else:
            return None
    
    def get_personalization_summary(self) -> Dict[str, Any]:
        """Get summary of personalization across all clients."""
        return {
            "total_rounds": self.current_round,
            "num_personalized_clients": len(self.client_personalized_models),
            "personalization_strategy": self.aggregator.personalization_strategy,
            "global_training_enabled": self.enable_global_training,
            "personalization_enabled": self.enable_personalization,
            "personalization_frequency": self.personalization_frequency,
            "aggregator_stats": self.aggregator.get_aggregation_stats()
        }