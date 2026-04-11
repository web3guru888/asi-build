#!/usr/bin/env python3
"""
Complete Decentralized AGI Training Example
Demonstrates full end-to-end training workflow with all components
"""

import asyncio
import logging
import time
from typing import Any, Dict, List

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from systems.decentralized_training.blockchain.agix_rewards import RewardDistributionManager
from systems.decentralized_training.blockchain.checkpoint_manager import BlockchainCheckpointManager
from systems.decentralized_training.core.byzantine_tolerance import AdaptiveByzantineDefense
from systems.decentralized_training.core.dataset_sharding import DistributedDatasetManager
from systems.decentralized_training.core.error_handling import (
    ErrorHandler,
    get_global_error_handler,
)

# Import system components
from systems.decentralized_training.core.federated_orchestrator import FederatedOrchestrator
from systems.decentralized_training.core.gradient_compression import AdaptiveCompressor
from systems.decentralized_training.monitoring.dashboard import DashboardApp, MetricsCollector
from systems.decentralized_training.p2p.node_discovery import P2PNetworkManager
from systems.decentralized_training.privacy.secure_aggregation import SecureAggregationProtocol
from torch.utils.data import DataLoader, TensorDataset

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleNN(nn.Module):
    """Simple neural network for demonstration"""

    def __init__(self, input_size=784, hidden_size=128, output_size=10):
        super(SimpleNN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, output_size)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x):
        x = x.view(x.size(0), -1)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return self.softmax(x)


class TrainingNode:
    """Represents a training node in the decentralized network"""

    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config

        # Initialize model
        self.model = SimpleNN()
        self.optimizer = optim.SGD(self.model.parameters(), lr=0.01)
        self.criterion = nn.CrossEntropyLoss()

        # Training data (will be assigned by dataset sharding)
        self.train_loader = None
        self.current_round = 0

        # Metrics
        self.training_history = []

        logger.info(f"Training node {node_id} initialized")

    def set_training_data(self, data_loader: DataLoader):
        """Set training data for this node"""
        self.train_loader = data_loader
        logger.info(f"Node {self.node_id} received {len(data_loader)} training batches")

    def train_local_model(self, epochs: int = 1) -> Dict[str, Any]:
        """Train local model and return gradients"""
        if not self.train_loader:
            raise ValueError("No training data assigned to node")

        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for epoch in range(epochs):
            for batch_idx, (data, target) in enumerate(self.train_loader):
                self.optimizer.zero_grad()

                output = self.model(data)
                loss = self.criterion(output, target)
                loss.backward()

                total_loss += loss.item()

                # Calculate accuracy
                _, predicted = torch.max(output.data, 1)
                total += target.size(0)
                correct += (predicted == target).sum().item()

                self.optimizer.step()

        # Calculate metrics
        avg_loss = total_loss / len(self.train_loader)
        accuracy = correct / total

        # Extract gradients
        gradients = {}
        for name, param in self.model.named_parameters():
            if param.grad is not None:
                gradients[name] = param.grad.clone()

        # Record training metrics
        metrics = {
            "round": self.current_round,
            "loss": avg_loss,
            "accuracy": accuracy,
            "data_size": len(self.train_loader.dataset),
            "training_time": time.time(),
        }

        self.training_history.append(metrics)

        logger.info(
            f"Node {self.node_id} completed local training - Loss: {avg_loss:.4f}, Accuracy: {accuracy:.3f}"
        )

        return gradients, metrics

    def update_model(self, global_gradients: Dict[str, torch.Tensor]):
        """Update local model with aggregated gradients"""
        with torch.no_grad():
            for name, param in self.model.named_parameters():
                if name in global_gradients:
                    param.data -= self.config.get("learning_rate", 0.01) * global_gradients[name]

        self.current_round += 1
        logger.info(f"Node {self.node_id} updated model for round {self.current_round}")


class DecentralizedTrainingCoordinator:
    """Main coordinator for decentralized training"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Initialize all system components
        self.orchestrator = FederatedOrchestrator(config.get("orchestrator", {}))
        self.checkpoint_manager = None  # Will be initialized if blockchain config provided
        self.reward_manager = None
        self.privacy_protocol = SecureAggregationProtocol(config.get("privacy", {}))
        self.p2p_manager = P2PNetworkManager(config.get("p2p", {}))
        self.compressor = AdaptiveCompressor(config.get("compression", {}))
        self.byzantine_defense = AdaptiveByzantineDefense(config.get("byzantine", {}))
        self.dataset_manager = DistributedDatasetManager(config.get("dataset", {}))
        self.metrics_collector = MetricsCollector(config.get("monitoring", {}))
        self.error_handler = ErrorHandler(config.get("error_handling", {}))

        # Training state
        self.training_nodes: Dict[str, TrainingNode] = {}
        self.global_model = SimpleNN()
        self.training_rounds = 0
        self.is_running = False

        # Optional blockchain integration
        if "blockchain" in config:
            self.checkpoint_manager = BlockchainCheckpointManager(config["blockchain"])
            self.reward_manager = RewardDistributionManager(config["blockchain"])

        logger.info("Decentralized training coordinator initialized")

    async def setup_system(self):
        """Setup and initialize all system components"""
        try:
            logger.info("Setting up decentralized training system...")

            # Start error handling
            from systems.decentralized_training.core.error_handling import set_global_error_handler

            set_global_error_handler(self.error_handler)

            # Start orchestrator
            orchestrator_task = asyncio.create_task(self.orchestrator.start())

            # Start P2P network
            bootstrap_nodes = self.config.get("bootstrap_nodes", [])
            p2p_task = asyncio.create_task(self.p2p_manager.start(bootstrap_nodes))

            # Wait for core components to initialize
            await asyncio.sleep(2)

            logger.info("Core components started successfully")

        except Exception as e:
            self.error_handler.handle_error(
                e, "system_setup", ErrorSeverity.CRITICAL, ErrorCategory.PROTOCOL
            )
            raise

    async def create_training_nodes(self, num_nodes: int) -> List[str]:
        """Create and register training nodes"""
        node_ids = []

        for i in range(num_nodes):
            node_id = f"training_node_{i}"

            # Create training node
            node = TrainingNode(node_id, self.config)
            self.training_nodes[node_id] = node

            # Register with orchestrator
            node_info = {
                "ip_address": f"192.168.1.{100+i}",
                "port": 8000 + i,
                "capabilities": {
                    "gpu": i % 2 == 0,  # Half nodes have GPU
                    "memory_gb": 8 + (i % 4) * 4,  # 8-20 GB memory
                    "cpu_cores": 4 + (i % 3) * 2,  # 4-8 CPU cores
                },
                "compute_power": 1.0 + (i % 5) * 0.5,  # 1.0-3.0 compute power
                "stake_amount": 1000.0 + (i % 10) * 100,  # 1000-1900 AGIX stake
            }

            result = await self.orchestrator.register_node(node_info)
            node_ids.append(result["node_id"])

            # Register with P2P network (mock)
            self.p2p_manager.register_node(node_id, node_info["capabilities"])

            logger.info(f"Created and registered training node: {node_id}")

        return node_ids

    def create_synthetic_dataset(self, num_samples: int = 10000) -> TensorDataset:
        """Create synthetic dataset for demonstration"""
        # Generate random data (28x28 images, 10 classes)
        X = torch.randn(num_samples, 1, 28, 28)
        y = torch.randint(0, 10, (num_samples,))

        dataset = TensorDataset(X, y)
        logger.info(f"Created synthetic dataset with {num_samples} samples")

        return dataset

    async def distribute_dataset(
        self, dataset: TensorDataset, node_ids: List[str], strategy: str = "noniid"
    ):
        """Distribute dataset across training nodes"""

        # Register dataset with dataset manager
        await self.dataset_manager.register_dataset(dataset, "synthetic_mnist")

        # Shard dataset
        shards = await self.dataset_manager.shard_dataset("synthetic_mnist", strategy, node_ids)

        # Assign shards to nodes
        for shard in shards:
            if shard.node_id in self.training_nodes:
                # Create data loader for this shard
                shard_indices = shard.data_indices
                shard_dataset = torch.utils.data.Subset(dataset, shard_indices)
                data_loader = DataLoader(shard_dataset, batch_size=32, shuffle=True)

                # Assign to training node
                self.training_nodes[shard.node_id].set_training_data(data_loader)

                logger.info(f"Assigned {len(shard_indices)} samples to node {shard.node_id}")

    async def run_training_round(self) -> bool:
        """Execute a single training round"""
        try:
            self.training_rounds += 1
            round_start = time.time()

            logger.info(f"Starting training round {self.training_rounds}")

            # Step 1: Local training
            node_gradients = {}
            node_metrics = {}

            for node_id, node in self.training_nodes.items():
                try:
                    gradients, metrics = node.train_local_model(epochs=1)
                    node_gradients[node_id] = gradients
                    node_metrics[node_id] = metrics

                    # Record metrics
                    from systems.decentralized_training.monitoring.dashboard import TrainingMetrics

                    training_metrics = TrainingMetrics(
                        node_id=node_id,
                        round_id=str(self.training_rounds),
                        epoch=1,
                        loss=metrics["loss"],
                        accuracy=metrics["accuracy"],
                        learning_rate=0.01,
                        batch_time=1.0,
                        communication_time=0.0,
                        memory_usage=50.0,  # Mock
                        gpu_utilization=80.0,  # Mock
                        timestamp=time.time(),
                    )

                    self.metrics_collector.record_training_metrics(training_metrics)

                except Exception as e:
                    self.error_handler.handle_error(
                        e,
                        f"local_training_{node_id}",
                        ErrorSeverity.MEDIUM,
                        ErrorCategory.COMPUTATION,
                    )
                    continue

            if not node_gradients:
                logger.error("No nodes completed local training")
                return False

            # Step 2: Gradient compression
            compressed_gradients = {}
            for node_id, gradients in node_gradients.items():
                try:
                    compressed_data, metadata = await self.compressor.compress(gradients)
                    compressed_gradients[node_id] = (compressed_data, metadata)
                except Exception as e:
                    self.error_handler.handle_error(
                        e, f"compression_{node_id}", ErrorSeverity.LOW, ErrorCategory.COMPUTATION
                    )
                    compressed_gradients[node_id] = (None, None)

            # Step 3: Decompress gradients
            decompressed_gradients = {}
            for node_id, (compressed_data, metadata) in compressed_gradients.items():
                if compressed_data is not None:
                    try:
                        gradients = await self.compressor.decompress(compressed_data, metadata)
                        decompressed_gradients[node_id] = gradients
                    except Exception as e:
                        self.error_handler.handle_error(
                            e,
                            f"decompression_{node_id}",
                            ErrorSeverity.LOW,
                            ErrorCategory.COMPUTATION,
                        )
                        # Fallback to original gradients
                        decompressed_gradients[node_id] = node_gradients[node_id]
                else:
                    decompressed_gradients[node_id] = node_gradients[node_id]

            # Step 4: Byzantine-tolerant aggregation
            aggregation_result = await self.byzantine_defense.adaptive_aggregate(
                decompressed_gradients
            )

            if not aggregation_result.aggregated_gradients:
                logger.error("Aggregation failed")
                return False

            logger.info(
                f"Aggregation completed - Method: {aggregation_result.aggregation_method}, "
                f"Honest: {len(aggregation_result.honest_participants)}, "
                f"Byzantine: {len(aggregation_result.suspected_byzantine)}"
            )

            # Step 5: Update local models
            for node_id, node in self.training_nodes.items():
                if node_id in aggregation_result.honest_participants:
                    try:
                        node.update_model(aggregation_result.aggregated_gradients)
                    except Exception as e:
                        self.error_handler.handle_error(
                            e,
                            f"model_update_{node_id}",
                            ErrorSeverity.MEDIUM,
                            ErrorCategory.COMPUTATION,
                        )

            # Step 6: Optional checkpoint saving
            if self.checkpoint_manager and self.training_rounds % 10 == 0:
                try:
                    checkpoint_metadata = {
                        "round_number": self.training_rounds,
                        "accuracy_metrics": {
                            "avg_accuracy": np.mean([m["accuracy"] for m in node_metrics.values()])
                        },
                    }

                    checkpoint_id = await self.checkpoint_manager.save_checkpoint(
                        self.global_model, checkpoint_metadata
                    )

                    logger.info(f"Saved checkpoint: {checkpoint_id}")

                except Exception as e:
                    self.error_handler.handle_error(
                        e, "checkpoint_save", ErrorSeverity.LOW, ErrorCategory.STORAGE
                    )

            # Step 7: Reward distribution
            if self.reward_manager:
                try:
                    # Create contribution records
                    contributions = []
                    for node_id, metrics in node_metrics.items():
                        from systems.decentralized_training.blockchain.agix_rewards import (
                            ComputeContribution,
                        )

                        contribution = ComputeContribution(
                            node_id=node_id,
                            round_id=str(self.training_rounds),
                            data_processed=metrics["data_size"],
                            compute_time=10.0,  # Mock
                            gpu_hours=0.1,  # Mock
                            model_accuracy=metrics["accuracy"],
                            bandwidth_used=1024,  # Mock
                            timestamp=time.time(),
                        )
                        contributions.append(contribution)

                    # Distribute rewards
                    reward_result = await self.reward_manager.process_round_rewards(
                        contributions, time.time() + 300, {}, {}
                    )

                    logger.info(
                        f"Distributed {reward_result['total_agix_distributed']} AGIX to {reward_result['successful_distributions']} nodes"
                    )

                except Exception as e:
                    self.error_handler.handle_error(
                        e, "reward_distribution", ErrorSeverity.MEDIUM, ErrorCategory.PROTOCOL
                    )

            # Step 8: Record network metrics
            round_time = time.time() - round_start
            avg_loss = np.mean([m["loss"] for m in node_metrics.values()])
            avg_accuracy = np.mean([m["accuracy"] for m in node_metrics.values()])

            from systems.decentralized_training.monitoring.dashboard import NetworkMetrics

            network_metrics = NetworkMetrics(
                round_id=str(self.training_rounds),
                total_nodes=len(self.training_nodes),
                active_nodes=len(node_gradients),
                avg_loss=avg_loss,
                avg_accuracy=avg_accuracy,
                consensus_time=round_time,
                data_transmitted_mb=10.0,  # Mock
                byzantine_nodes_detected=len(aggregation_result.suspected_byzantine),
                timestamp=time.time(),
            )

            self.metrics_collector.record_network_metrics(network_metrics)

            logger.info(
                f"Round {self.training_rounds} completed in {round_time:.2f}s - "
                f"Avg Loss: {avg_loss:.4f}, Avg Accuracy: {avg_accuracy:.3f}"
            )

            return True

        except Exception as e:
            self.error_handler.handle_error(
                e, "training_round", ErrorSeverity.HIGH, ErrorCategory.PROTOCOL
            )
            return False

    async def run_training(self, num_rounds: int = 100):
        """Run complete decentralized training"""

        self.is_running = True
        successful_rounds = 0

        logger.info(f"Starting decentralized training for {num_rounds} rounds")

        for round_num in range(num_rounds):
            if not self.is_running:
                break

            success = await self.run_training_round()

            if success:
                successful_rounds += 1

            # Brief pause between rounds
            await asyncio.sleep(1)

            # Early stopping if too many failures
            if round_num > 10 and successful_rounds / (round_num + 1) < 0.5:
                logger.warning("Too many failed rounds, stopping training")
                break

        logger.info(f"Training completed: {successful_rounds}/{num_rounds} successful rounds")

        return successful_rounds

    def stop_training(self):
        """Stop training"""
        self.is_running = False
        logger.info("Training stopped")

    async def shutdown(self):
        """Shutdown all system components"""
        logger.info("Shutting down decentralized training system")

        self.stop_training()
        await self.orchestrator.stop()
        await self.p2p_manager.stop()

        logger.info("System shutdown complete")


async def main():
    """Main example execution"""

    # Configuration for the complete system
    config = {
        "orchestrator": {
            "max_nodes": 1000,
            "min_nodes_per_round": 3,
            "max_nodes_per_round": 20,
            "round_duration": 300,
            "heartbeat_interval": 30,
        },
        "privacy": {
            "threshold": 10,
            "total_participants": 20,
            "epsilon": 1.0,
            "delta": 1e-5,
            "clipping_norm": 1.0,
        },
        "p2p": {"listen_port": 8080, "max_gossip_peers": 3, "k_bucket_size": 20},
        "compression": {"topk_ratio": 0.1, "quantization_bits": 8, "error_feedback": True},
        "byzantine": {"aggregation_method": "krum", "byzantine_ratio": 0.3, "adaptation_rate": 0.1},
        "dataset": {"noniid_alpha": 0.5, "min_samples_per_class": 10},
        "monitoring": {"enable_dashboard": True, "dashboard_port": 8050},
        "error_handling": {
            "circuit_breaker_threshold": 5,
            "max_retries": 3,
            "retry_base_delay": 1.0,
        },
        "bootstrap_nodes": [],
        "learning_rate": 0.01,
    }

    # Optional blockchain configuration
    # Uncomment and configure for blockchain integration
    """
    config['blockchain'] = {
        'ethereum_rpc_url': 'https://mainnet.infura.io/v3/YOUR_PROJECT_ID',
        'private_key': 'YOUR_PRIVATE_KEY',
        'agix_token_address': '0x5b7533812759b45c2b44c19e320ba2cd2681b542',
        'contract_address': 'YOUR_CONTRACT_ADDRESS',
        'contract_abi': [],  # Contract ABI
        'ipfs_api_url': '/dns/localhost/tcp/5001/http'
    }
    """

    try:
        # Create coordinator
        coordinator = DecentralizedTrainingCoordinator(config)

        # Setup system components
        await coordinator.setup_system()

        # Create training nodes
        logger.info("Creating training nodes...")
        node_ids = await coordinator.create_training_nodes(num_nodes=10)

        # Create and distribute dataset
        logger.info("Creating and distributing dataset...")
        dataset = coordinator.create_synthetic_dataset(num_samples=5000)
        await coordinator.distribute_dataset(dataset, node_ids, strategy="noniid")

        # Optional: Start monitoring dashboard in background
        if config["monitoring"]["enable_dashboard"]:
            dashboard = DashboardApp(
                coordinator.metrics_collector, port=config["monitoring"]["dashboard_port"]
            )

            # Start dashboard in background thread
            import threading

            dashboard_thread = threading.Thread(
                target=lambda: dashboard.run(debug=False, host="0.0.0.0")
            )
            dashboard_thread.daemon = True
            dashboard_thread.start()

            logger.info(
                f"Dashboard available at http://localhost:{config['monitoring']['dashboard_port']}"
            )

        # Run training
        logger.info("Starting decentralized training...")
        successful_rounds = await coordinator.run_training(num_rounds=50)

        # Print final results
        logger.info(f"Training completed with {successful_rounds} successful rounds")

        # Print system statistics
        error_summary = coordinator.error_handler.get_error_summary()
        logger.info(f"Error summary: {error_summary}")

        orchestrator_status = coordinator.orchestrator.get_status()
        logger.info(f"Orchestrator status: {orchestrator_status}")

        if coordinator.reward_manager:
            treasury_status = coordinator.reward_manager.get_treasury_status()
            logger.info(f"Treasury status: {treasury_status}")

        # Shutdown
        await coordinator.shutdown()

        logger.info("Example completed successfully!")

    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
        await coordinator.shutdown()

    except Exception as e:
        logger.error(f"Example failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
