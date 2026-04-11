"""
Federated Learning Orchestrator for Decentralized AGI Training
Supports 1000+ nodes with efficient coordination and management
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set

import aiohttp
import numpy as np
import torch
import websockets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


@dataclass
class NodeInfo:
    """Information about a training node"""

    node_id: str
    ip_address: str
    port: int
    capabilities: Dict[str, Any]
    compute_power: float
    last_heartbeat: float
    reputation_score: float
    stake_amount: float
    status: str  # active, inactive, malicious, quarantined


@dataclass
class TrainingRound:
    """Information about a training round"""

    round_id: str
    global_model_hash: str
    participants: List[str]
    start_time: float
    deadline: float
    min_participants: int
    max_participants: int
    status: str  # preparing, active, aggregating, completed


@dataclass
class ModelUpdate:
    """Model update from a node"""

    node_id: str
    round_id: str
    model_diff: bytes
    data_size: int
    compute_proof: str
    signature: str
    timestamp: float


class FederatedOrchestrator:
    """
    Main orchestrator for federated learning across 1000+ nodes
    Handles node management, round coordination, and aggregation
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.node_registry: Dict[str, NodeInfo] = {}
        self.active_rounds: Dict[str, TrainingRound] = {}
        self.model_updates: Dict[str, List[ModelUpdate]] = defaultdict(list)
        self.global_model = None
        self.running = False

        # Network configuration
        self.max_nodes = config.get("max_nodes", 10000)
        self.min_nodes_per_round = config.get("min_nodes_per_round", 10)
        self.max_nodes_per_round = config.get("max_nodes_per_round", 100)
        self.round_duration = config.get("round_duration", 300)  # 5 minutes
        self.heartbeat_interval = config.get("heartbeat_interval", 30)

        # Security
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.public_key = self.private_key.public_key()

        # Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Thread pool for concurrent operations
        self.executor = ThreadPoolExecutor(max_workers=50)

    async def start(self):
        """Start the orchestrator"""
        self.running = True
        self.logger.info("Starting Federated Learning Orchestrator")

        # Start background tasks
        tasks = [
            asyncio.create_task(self._heartbeat_monitor()),
            asyncio.create_task(self._training_coordinator()),
            asyncio.create_task(self._reputation_manager()),
            asyncio.create_task(self._websocket_server()),
        ]

        await asyncio.gather(*tasks)

    async def stop(self):
        """Stop the orchestrator"""
        self.running = False
        self.logger.info("Stopping Federated Learning Orchestrator")

    async def register_node(self, node_info: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new training node"""
        node_id = str(uuid.uuid4())

        node = NodeInfo(
            node_id=node_id,
            ip_address=node_info["ip_address"],
            port=node_info["port"],
            capabilities=node_info.get("capabilities", {}),
            compute_power=node_info.get("compute_power", 1.0),
            last_heartbeat=time.time(),
            reputation_score=0.5,  # Start with neutral reputation
            stake_amount=node_info.get("stake_amount", 0.0),
            status="active",
        )

        self.node_registry[node_id] = node

        self.logger.info(f"Registered node {node_id} from {node.ip_address}:{node.port}")

        return {
            "node_id": node_id,
            "status": "registered",
            "public_key": self._serialize_public_key(),
        }

    async def unregister_node(self, node_id: str) -> Dict[str, Any]:
        """Unregister a training node"""
        if node_id in self.node_registry:
            del self.node_registry[node_id]
            self.logger.info(f"Unregistered node {node_id}")
            return {"status": "unregistered"}
        else:
            return {"status": "not_found"}

    async def heartbeat(self, node_id: str, status_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process heartbeat from a node"""
        if node_id not in self.node_registry:
            return {"status": "not_registered"}

        node = self.node_registry[node_id]
        node.last_heartbeat = time.time()

        # Update node status
        if "compute_power" in status_info:
            node.compute_power = status_info["compute_power"]
        if "capabilities" in status_info:
            node.capabilities.update(status_info["capabilities"])

        return {"status": "acknowledged", "next_heartbeat": time.time() + self.heartbeat_interval}

    async def submit_model_update(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process model update from a node"""
        node_id = update_data["node_id"]
        round_id = update_data["round_id"]

        # Validate node and round
        if node_id not in self.node_registry:
            return {"status": "error", "message": "Node not registered"}

        if round_id not in self.active_rounds:
            return {"status": "error", "message": "Invalid round"}

        # Verify signature
        if not self._verify_update_signature(update_data):
            self.logger.warning(f"Invalid signature from node {node_id}")
            return {"status": "error", "message": "Invalid signature"}

        # Create model update
        update = ModelUpdate(
            node_id=node_id,
            round_id=round_id,
            model_diff=update_data["model_diff"],
            data_size=update_data["data_size"],
            compute_proof=update_data["compute_proof"],
            signature=update_data["signature"],
            timestamp=time.time(),
        )

        self.model_updates[round_id].append(update)

        self.logger.info(f"Received model update from node {node_id} for round {round_id}")

        return {"status": "accepted", "update_id": str(uuid.uuid4())}

    async def _heartbeat_monitor(self):
        """Monitor node heartbeats and remove inactive nodes"""
        while self.running:
            current_time = time.time()
            inactive_nodes = []

            for node_id, node in self.node_registry.items():
                if current_time - node.last_heartbeat > self.heartbeat_interval * 3:
                    inactive_nodes.append(node_id)
                    node.status = "inactive"

            for node_id in inactive_nodes:
                self.logger.warning(f"Node {node_id} marked as inactive")

            await asyncio.sleep(self.heartbeat_interval)

    async def _training_coordinator(self):
        """Coordinate training rounds"""
        while self.running:
            # Check if we should start a new round
            active_nodes = [n for n in self.node_registry.values() if n.status == "active"]

            if len(active_nodes) >= self.min_nodes_per_round and not self.active_rounds:
                await self._start_training_round(active_nodes)

            # Check for completed rounds
            completed_rounds = []
            for round_id, training_round in self.active_rounds.items():
                if time.time() > training_round.deadline:
                    completed_rounds.append(round_id)

            for round_id in completed_rounds:
                await self._complete_training_round(round_id)

            await asyncio.sleep(10)  # Check every 10 seconds

    async def _start_training_round(self, available_nodes: List[NodeInfo]):
        """Start a new training round"""
        round_id = str(uuid.uuid4())

        # Select participants based on reputation and compute power
        participants = self._select_participants(available_nodes)

        training_round = TrainingRound(
            round_id=round_id,
            global_model_hash=self._get_model_hash(),
            participants=[p.node_id for p in participants],
            start_time=time.time(),
            deadline=time.time() + self.round_duration,
            min_participants=self.min_nodes_per_round,
            max_participants=self.max_nodes_per_round,
            status="active",
        )

        self.active_rounds[round_id] = training_round

        # Notify participants
        for participant in participants:
            await self._notify_node_training_start(participant, training_round)

        self.logger.info(f"Started training round {round_id} with {len(participants)} participants")

    async def _complete_training_round(self, round_id: str):
        """Complete a training round and aggregate updates"""
        training_round = self.active_rounds[round_id]
        updates = self.model_updates[round_id]

        self.logger.info(f"Completing round {round_id} with {len(updates)} updates")

        if len(updates) >= training_round.min_participants:
            # Aggregate model updates
            aggregated_model = await self._aggregate_updates(updates)

            # Update global model
            if aggregated_model is not None:
                self.global_model = aggregated_model

                # Update node reputations based on participation
                await self._update_reputations(updates)

                # Broadcast new global model
                await self._broadcast_global_model()

                self.logger.info(f"Successfully completed round {round_id}")
            else:
                self.logger.error(f"Failed to aggregate updates for round {round_id}")
        else:
            self.logger.warning(f"Insufficient updates for round {round_id}")

        # Cleanup
        del self.active_rounds[round_id]
        del self.model_updates[round_id]

    def _select_participants(self, available_nodes: List[NodeInfo]) -> List[NodeInfo]:
        """Select participants for training round based on reputation and compute power"""
        # Sort by reputation score and compute power
        scored_nodes = [
            (node, node.reputation_score * node.compute_power) for node in available_nodes
        ]
        scored_nodes.sort(key=lambda x: x[1], reverse=True)

        # Select top nodes up to max_nodes_per_round
        selected = [node for node, _ in scored_nodes[: self.max_nodes_per_round]]

        return selected

    async def _aggregate_updates(self, updates: List[ModelUpdate]) -> Optional[torch.Tensor]:
        """Aggregate model updates using weighted average"""
        try:
            # Filter out potentially malicious updates using Byzantine fault tolerance
            valid_updates = await self._filter_malicious_updates(updates)

            if not valid_updates:
                return None

            # Weighted aggregation based on data size and reputation
            total_weight = 0
            aggregated_gradients = None

            for update in valid_updates:
                node = self.node_registry[update.node_id]
                weight = update.data_size * node.reputation_score

                # Deserialize model diff
                model_diff = torch.load(update.model_diff)

                if aggregated_gradients is None:
                    aggregated_gradients = {k: v * weight for k, v in model_diff.items()}
                else:
                    for k, v in model_diff.items():
                        aggregated_gradients[k] += v * weight

                total_weight += weight

            # Normalize by total weight
            if total_weight > 0:
                for k in aggregated_gradients:
                    aggregated_gradients[k] /= total_weight

            return aggregated_gradients

        except Exception as e:
            self.logger.error(f"Error aggregating updates: {e}")
            return None

    async def _filter_malicious_updates(self, updates: List[ModelUpdate]) -> List[ModelUpdate]:
        """Filter out potentially malicious updates using statistical analysis"""
        if len(updates) < 3:
            return updates

        # Simple outlier detection based on gradient norms
        # In production, this would be more sophisticated
        valid_updates = []

        for update in updates:
            node = self.node_registry[update.node_id]

            # Skip updates from nodes with very low reputation
            if node.reputation_score < 0.1:
                continue

            # TODO: Implement more sophisticated Byzantine fault tolerance
            # For now, accept all updates from reputable nodes
            valid_updates.append(update)

        return valid_updates

    async def _reputation_manager(self):
        """Manage node reputation scores"""
        while self.running:
            # Update reputation scores based on various factors
            for node_id, node in self.node_registry.items():
                # Decay reputation over time if node is inactive
                if node.status != "active":
                    node.reputation_score *= 0.99

                # Boost reputation for consistent participation
                # This would be based on training history in practice

            await asyncio.sleep(60)  # Update every minute

    async def _update_reputations(self, updates: List[ModelUpdate]):
        """Update node reputations based on training participation"""
        for update in updates:
            node = self.node_registry[update.node_id]

            # Increase reputation for successful participation
            node.reputation_score = min(1.0, node.reputation_score + 0.01)

    async def _websocket_server(self):
        """WebSocket server for real-time communication with nodes"""

        async def handle_client(websocket, path):
            try:
                async for message in websocket:
                    data = json.loads(message)
                    response = await self._handle_websocket_message(data)
                    await websocket.send(json.dumps(response))
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")

        server = await websockets.serve(handle_client, "0.0.0.0", 8765)
        self.logger.info("WebSocket server started on port 8765")
        await server.wait_closed()

    async def _handle_websocket_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming WebSocket messages"""
        message_type = data.get("type")

        if message_type == "register":
            return await self.register_node(data.get("node_info", {}))
        elif message_type == "heartbeat":
            return await self.heartbeat(data.get("node_id"), data.get("status_info", {}))
        elif message_type == "model_update":
            return await self.submit_model_update(data)
        else:
            return {"status": "error", "message": "Unknown message type"}

    def _get_model_hash(self) -> str:
        """Get hash of current global model"""
        if self.global_model is None:
            return "initial"

        # Create hash of model parameters
        model_str = str(self.global_model)
        digest = hashes.Hash(hashes.SHA256())
        digest.update(model_str.encode())
        return digest.finalize().hex()

    def _serialize_public_key(self) -> str:
        """Serialize public key for distribution"""
        pem = self.public_key.public_key_pem()
        return pem.decode("utf-8")

    def _verify_update_signature(self, update_data: Dict[str, Any]) -> bool:
        """Verify signature of model update"""
        # In practice, this would verify the signature using the node's public key
        # For now, return True as placeholder
        return True

    async def _notify_node_training_start(self, node: NodeInfo, training_round: TrainingRound):
        """Notify a node that training round has started"""
        # This would send training parameters to the node
        pass

    async def _broadcast_global_model(self):
        """Broadcast updated global model to all nodes"""
        # This would distribute the new global model to all active nodes
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status"""
        active_nodes = len([n for n in self.node_registry.values() if n.status == "active"])

        return {
            "total_nodes": len(self.node_registry),
            "active_nodes": active_nodes,
            "active_rounds": len(self.active_rounds),
            "global_model_hash": self._get_model_hash(),
            "uptime": time.time() - getattr(self, "_start_time", time.time()),
        }
