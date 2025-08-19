"""
Basic FedAvg Example

Demonstrates a simple federated learning setup using FedAvg aggregation.
"""

import numpy as np
import tensorflow as tf
from typing import Dict, Any, List, Tuple

from ..core.base import FederatedModel, FederatedClient, FederatedServer
from ..core.config import FederatedConfig, ClientConfig, ServerConfig
from ..core.manager import FederatedManager
from ..aggregation.fedavg import FedAvgAggregator


class SimpleNeuralNetwork(FederatedModel):
    """Simple neural network for demonstration."""
    
    def __init__(self, input_shape: List[int], num_classes: int):
        super().__init__({"input_shape": input_shape, "num_classes": num_classes})
        self.input_shape = input_shape
        self.num_classes = num_classes
    
    def build_model(self) -> tf.keras.Model:
        """Build a simple dense neural network."""
        model = tf.keras.Sequential([
            tf.keras.layers.Flatten(input_shape=self.input_shape),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(self.num_classes, activation='softmax')
        ])
        
        self.model = model
        return model
    
    def compile_model(self, optimizer: str = "adam", 
                     loss: str = "categorical_crossentropy",
                     metrics: List[str] = None) -> None:
        """Compile the model."""
        if metrics is None:
            metrics = ["accuracy"]
        
        if self.model is None:
            self.build_model()
        
        self.model.compile(
            optimizer=optimizer,
            loss=loss,
            metrics=metrics
        )
        self._compiled = True


class SimpleClient(FederatedClient):
    """Simple federated client implementation."""
    
    def __init__(self, client_id: str, config: ClientConfig, model: FederatedModel):
        super().__init__(client_id, config, model)
        self.train_data = None
        self.val_data = None
    
    def load_data(self) -> Tuple[tf.data.Dataset, tf.data.Dataset]:
        """Load training and validation data."""
        # Generate synthetic data for demonstration
        num_samples = np.random.randint(100, 500)
        
        # Generate random data matching model input shape
        x_data = np.random.random((num_samples,) + tuple(self.model.input_shape))
        y_data = tf.keras.utils.to_categorical(
            np.random.randint(0, self.model.num_classes, num_samples),
            num_classes=self.model.num_classes
        )
        
        # Split into train and validation
        split_idx = int(0.8 * num_samples)
        
        train_dataset = tf.data.Dataset.from_tensor_slices((
            x_data[:split_idx], y_data[:split_idx]
        )).batch(self.config.batch_size)
        
        val_dataset = tf.data.Dataset.from_tensor_slices((
            x_data[split_idx:], y_data[split_idx:]
        )).batch(self.config.batch_size)
        
        self.local_data_size = split_idx
        self.train_data = train_dataset
        self.val_data = val_dataset
        
        return train_dataset, val_dataset
    
    def local_training(self, global_weights: List[np.ndarray]) -> Dict[str, Any]:
        """Perform local training."""
        if self.train_data is None:
            self.load_data()
        
        # Update model with global weights
        self.update_model(global_weights)
        
        # Ensure model is compiled
        if not self.model._compiled:
            self.model.compile_model()
        
        # Perform local training
        history = self.model.model.fit(
            self.train_data,
            epochs=self.config.local_epochs,
            verbose=0,
            validation_data=self.val_data
        )
        
        # Record training history
        self.training_history.append({
            "round": self.round_number,
            "loss": history.history["loss"][-1],
            "accuracy": history.history["accuracy"][-1],
            "val_loss": history.history["val_loss"][-1] if "val_loss" in history.history else None,
            "val_accuracy": history.history["val_accuracy"][-1] if "val_accuracy" in history.history else None
        })
        
        self.round_number += 1
        
        return {
            "training_loss": history.history["loss"][-1],
            "training_accuracy": history.history["accuracy"][-1],
            "validation_loss": history.history["val_loss"][-1] if "val_loss" in history.history else None,
            "validation_accuracy": history.history["val_accuracy"][-1] if "val_accuracy" in history.history else None,
            "epochs_completed": self.config.local_epochs
        }


class SimpleServer(FederatedServer):
    """Simple federated server implementation."""
    
    def __init__(self, server_id: str, config: ServerConfig, model: FederatedModel):
        super().__init__(server_id, config, model)
        self.aggregator = FedAvgAggregator("server_aggregator")
        
        # Initialize global model
        if not model._compiled:
            model.compile_model()
    
    def aggregate_updates(self, client_updates: List[Dict[str, Any]]) -> List[np.ndarray]:
        """Aggregate client updates."""
        aggregation_result = self.aggregator.aggregate(client_updates)
        return aggregation_result["aggregated_weights"]
    
    def select_clients(self) -> List[str]:
        """Select clients for the current round."""
        # Select all available clients or a fraction based on config
        available_clients = list(self.clients.keys())
        num_to_select = max(
            self.config.min_clients,
            int(len(available_clients) * self.config.client_fraction)
        )
        
        # For simplicity, select first N clients
        # In practice, you might use random selection or other strategies
        selected = available_clients[:num_to_select]
        return selected


class BasicFedAvgExample:
    """Complete example of basic FedAvg federated learning."""
    
    def __init__(self, num_clients: int = 5, input_shape: List[int] = None, num_classes: int = 10):
        if input_shape is None:
            input_shape = [28, 28, 1]  # MNIST-like
        
        self.num_clients = num_clients
        self.input_shape = input_shape
        self.num_classes = num_classes
        
        # Create configuration
        self.config = FederatedConfig(
            experiment_name="basic_fedavg_example",
            client=ClientConfig(
                client_id="default",
                local_epochs=3,
                batch_size=32,
                learning_rate=0.01
            ),
            server=ServerConfig(
                rounds=10,
                min_clients=2,
                client_fraction=1.0
            ),
            input_shape=input_shape,
            num_classes=num_classes
        )
        
        # Initialize manager
        self.manager = FederatedManager(self.config)
        
        # Create model
        self.model = SimpleNeuralNetwork(input_shape, num_classes)
        
        print(f"BasicFedAvgExample initialized with {num_clients} clients")
    
    def setup_federation(self):
        """Set up the federated learning components."""
        # Create server
        server = SimpleServer("main_server", self.config.server, self.model)
        self.manager.set_server(server)
        
        # Create clients
        for i in range(self.num_clients):
            client_config = ClientConfig(
                client_id=f"client_{i}",
                local_epochs=self.config.client.local_epochs,
                batch_size=self.config.client.batch_size,
                learning_rate=self.config.client.learning_rate
            )
            
            # Each client gets its own model instance
            client_model = SimpleNeuralNetwork(self.input_shape, self.num_classes)
            client = SimpleClient(f"client_{i}", client_config, client_model)
            
            self.manager.register_client(client)
        
        print(f"Federation setup complete: 1 server, {self.num_clients} clients")
    
    def run_experiment(self, num_rounds: int = None) -> Dict[str, Any]:
        """Run the federated learning experiment."""
        if num_rounds is None:
            num_rounds = self.config.server.rounds
        
        print(f"Starting federated learning experiment for {num_rounds} rounds...")
        
        # Setup federation
        self.setup_federation()
        
        # Run training
        results = self.manager.run_training(num_rounds)
        
        print(f"Experiment completed!")
        print(f"Total rounds: {results['total_rounds']}")
        print(f"Training time: {results['stop_result']['training_duration']:.2f} seconds")
        
        return results
    
    def get_experiment_summary(self) -> Dict[str, Any]:
        """Get comprehensive experiment summary."""
        return self.manager.get_comprehensive_summary()


def run_basic_example():
    """Run a basic FedAvg example."""
    print("=" * 50)
    print("Basic FedAvg Federated Learning Example")
    print("=" * 50)
    
    # Create and run example
    example = BasicFedAvgExample(num_clients=3, num_classes=5)
    results = example.run_experiment(num_rounds=5)
    
    # Print summary
    summary = example.get_experiment_summary()
    print("\nExperiment Summary:")
    print(f"- Configuration: {summary['config']['experiment_name']}")
    print(f"- Total rounds: {summary['training_status']['current_round']}")
    print(f"- Average round time: {summary['performance_metrics']['avg_round_time']:.2f}s")
    print(f"- Convergence achieved: {summary.get('convergence', {}).get('achieved', False)}")
    
    return results, summary


if __name__ == "__main__":
    run_basic_example()