"""
Swarm Communication Protocols

This module implements communication protocols for swarm
intelligence systems, enabling information exchange and
coordination between agents.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass
from enum import Enum
import time
import json


class MessageType(Enum):
    """Types of messages in swarm communication"""
    POSITION_UPDATE = "position_update"
    FITNESS_REPORT = "fitness_report"
    DISCOVERY = "discovery"
    COORDINATION = "coordination"
    WARNING = "warning"
    RECRUITMENT = "recruitment"
    STATUS = "status"


class CommunicationTopology(Enum):
    """Communication network topologies"""
    GLOBAL = "global"           # All-to-all communication
    RING = "ring"              # Ring topology
    STAR = "star"              # Star topology
    MESH = "mesh"              # Mesh topology
    HIERARCHICAL = "hierarchical"  # Hierarchical topology
    SMALL_WORLD = "small_world"    # Small world network


@dataclass
class SwarmMessage:
    """Message structure for swarm communication"""
    sender_id: str
    receiver_id: str
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: float
    priority: int = 1
    ttl: int = 10  # Time to live


class SwarmCommunicationProtocol:
    """Protocol for swarm communication and coordination"""
    
    def __init__(self, topology: CommunicationTopology = CommunicationTopology.GLOBAL):
        self.topology = topology
        self.message_queue = []
        self.agent_registry = {}
        self.communication_graph = {}
        self.message_history = []
        
        # Communication parameters
        self.max_message_queue_size = 1000
        self.message_timeout = 60.0  # seconds
        self.broadcast_range = 5.0
        
        # Performance metrics
        self.messages_sent = 0
        self.messages_received = 0
        self.messages_dropped = 0
    
    def register_agent(self, agent_id: str, position: np.ndarray,
                      communication_range: float = 5.0) -> None:
        """Register an agent in the communication system"""
        self.agent_registry[agent_id] = {
            'position': position.copy(),
            'communication_range': communication_range,
            'last_seen': time.time(),
            'neighbors': set(),
            'message_queue': []
        }
        
        # Update communication graph
        self._update_communication_graph()
    
    def send_message(self, sender_id: str, receiver_id: str,
                    message_type: MessageType, content: Dict[str, Any],
                    priority: int = 1) -> bool:
        """Send a message from one agent to another"""
        
        # Check if sender is registered
        if sender_id not in self.agent_registry:
            return False
        
        # Create message
        message = SwarmMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            timestamp=time.time(),
            priority=priority
        )
        
        # Route message based on topology
        if self._route_message(message):\n            self.messages_sent += 1\n            return True\n        else:\n            self.messages_dropped += 1\n            return False\n    \n    def broadcast_message(self, sender_id: str, message_type: MessageType,\n                         content: Dict[str, Any], priority: int = 1) -> int:\n        \"\"\"Broadcast message to all reachable agents\"\"\"\n        \n        if sender_id not in self.agent_registry:\n            return 0\n        \n        messages_sent = 0\n        sender_info = self.agent_registry[sender_id]\n        \n        # Determine recipients based on topology\n        if self.topology == CommunicationTopology.GLOBAL:\n            recipients = list(self.agent_registry.keys())\n        else:\n            recipients = list(sender_info['neighbors'])\n        \n        # Send to each recipient\n        for receiver_id in recipients:\n            if receiver_id != sender_id:\n                if self.send_message(sender_id, receiver_id, message_type, content, priority):\n                    messages_sent += 1\n        \n        return messages_sent\n    \n    def receive_messages(self, agent_id: str) -> List[SwarmMessage]:\n        \"\"\"Receive messages for a specific agent\"\"\"\n        \n        if agent_id not in self.agent_registry:\n            return []\n        \n        agent_messages = self.agent_registry[agent_id]['message_queue']\n        self.agent_registry[agent_id]['message_queue'] = []\n        \n        self.messages_received += len(agent_messages)\n        return agent_messages\n    \n    def update_agent_position(self, agent_id: str, new_position: np.ndarray) -> None:\n        \"\"\"Update agent position and recalculate communication graph\"\"\"\n        \n        if agent_id in self.agent_registry:\n            self.agent_registry[agent_id]['position'] = new_position.copy()\n            self.agent_registry[agent_id]['last_seen'] = time.time()\n            self._update_communication_graph()\n    \n    def _route_message(self, message: SwarmMessage) -> bool:\n        \"\"\"Route message based on topology and constraints\"\"\"\n        \n        # Check if receiver exists\n        if message.receiver_id not in self.agent_registry:\n            return False\n        \n        # Check communication constraints\n        if not self._can_communicate(message.sender_id, message.receiver_id):\n            return False\n        \n        # Add to receiver's queue\n        receiver_queue = self.agent_registry[message.receiver_id]['message_queue']\n        \n        # Check queue size\n        if len(receiver_queue) >= self.max_message_queue_size:\n            # Remove oldest low-priority message\n            receiver_queue.sort(key=lambda m: (m.priority, m.timestamp))\n            receiver_queue.pop(0)\n        \n        receiver_queue.append(message)\n        self.message_history.append(message)\n        \n        return True\n    \n    def _can_communicate(self, sender_id: str, receiver_id: str) -> bool:\n        \"\"\"Check if two agents can communicate\"\"\"\n        \n        if self.topology == CommunicationTopology.GLOBAL:\n            return True\n        \n        # Distance-based communication\n        sender_info = self.agent_registry[sender_id]\n        receiver_info = self.agent_registry[receiver_id]\n        \n        distance = np.linalg.norm(sender_info['position'] - receiver_info['position'])\n        return distance <= sender_info['communication_range']\n    \n    def _update_communication_graph(self) -> None:\n        \"\"\"Update communication graph based on current topology\"\"\"\n        \n        # Clear existing connections\n        for agent_id in self.agent_registry:\n            self.agent_registry[agent_id]['neighbors'] = set()\n        \n        if self.topology == CommunicationTopology.GLOBAL:\n            # All agents can communicate with all others\n            agent_ids = list(self.agent_registry.keys())\n            for agent_id in agent_ids:\n                self.agent_registry[agent_id]['neighbors'] = set(agent_ids) - {agent_id}\n        \n        elif self.topology == CommunicationTopology.RING:\n            self._create_ring_topology()\n        \n        elif self.topology == CommunicationTopology.MESH:\n            self._create_mesh_topology()\n        \n        elif self.topology == CommunicationTopology.HIERARCHICAL:\n            self._create_hierarchical_topology()\n    \n    def _create_ring_topology(self) -> None:\n        \"\"\"Create ring communication topology\"\"\"\n        agent_ids = list(self.agent_registry.keys())\n        \n        for i, agent_id in enumerate(agent_ids):\n            # Connect to previous and next agent in ring\n            prev_id = agent_ids[(i - 1) % len(agent_ids)]\n            next_id = agent_ids[(i + 1) % len(agent_ids)]\n            \n            self.agent_registry[agent_id]['neighbors'].add(prev_id)\n            self.agent_registry[agent_id]['neighbors'].add(next_id)\n    \n    def _create_mesh_topology(self) -> None:\n        \"\"\"Create mesh topology based on spatial proximity\"\"\"\n        agent_ids = list(self.agent_registry.keys())\n        \n        for agent_id in agent_ids:\n            agent_pos = self.agent_registry[agent_id]['position']\n            comm_range = self.agent_registry[agent_id]['communication_range']\n            \n            for other_id in agent_ids:\n                if other_id != agent_id:\n                    other_pos = self.agent_registry[other_id]['position']\n                    distance = np.linalg.norm(agent_pos - other_pos)\n                    \n                    if distance <= comm_range:\n                        self.agent_registry[agent_id]['neighbors'].add(other_id)\n    \n    def _create_hierarchical_topology(self) -> None:\n        \"\"\"Create hierarchical communication topology\"\"\"\n        agent_ids = list(self.agent_registry.keys())\n        \n        # Simple hierarchical structure\n        if len(agent_ids) > 0:\n            # First agent is root\n            root_id = agent_ids[0]\n            \n            # Others connect to root\n            for agent_id in agent_ids[1:]:\n                self.agent_registry[agent_id]['neighbors'].add(root_id)\n                self.agent_registry[root_id]['neighbors'].add(agent_id)\n    \n    def cleanup_expired_messages(self) -> int:\n        \"\"\"Remove expired messages from queues\"\"\"\n        current_time = time.time()\n        removed_count = 0\n        \n        for agent_id in self.agent_registry:\n            queue = self.agent_registry[agent_id]['message_queue']\n            original_length = len(queue)\n            \n            # Filter out expired messages\n            self.agent_registry[agent_id]['message_queue'] = [\n                msg for msg in queue\n                if (current_time - msg.timestamp) < self.message_timeout\n            ]\n            \n            removed_count += original_length - len(self.agent_registry[agent_id]['message_queue'])\n        \n        return removed_count\n    \n    def get_communication_statistics(self) -> Dict[str, Any]:\n        \"\"\"Get communication system statistics\"\"\"\n        return {\n            'topology': self.topology.value,\n            'registered_agents': len(self.agent_registry),\n            'messages_sent': self.messages_sent,\n            'messages_received': self.messages_received,\n            'messages_dropped': self.messages_dropped,\n            'total_messages_in_queues': sum(\n                len(info['message_queue']) for info in self.agent_registry.values()\n            ),\n            'message_history_size': len(self.message_history),\n            'average_neighbors': np.mean([\n                len(info['neighbors']) for info in self.agent_registry.values()\n            ]) if self.agent_registry else 0\n        }\n    \n    def visualize_communication_graph(self) -> Dict[str, Any]:\n        \"\"\"Get visualization data for communication graph\"\"\"\n        nodes = []\n        edges = []\n        \n        for agent_id, info in self.agent_registry.items():\n            nodes.append({\n                'id': agent_id,\n                'position': info['position'].tolist(),\n                'neighbors_count': len(info['neighbors'])\n            })\n            \n            for neighbor_id in info['neighbors']:\n                if neighbor_id in self.agent_registry:\n                    edges.append({\n                        'source': agent_id,\n                        'target': neighbor_id\n                    })\n        \n        return {\n            'nodes': nodes,\n            'edges': edges,\n            'topology': self.topology.value\n        }\n\n\nclass BroadcastProtocol:\n    \"\"\"Specialized protocol for broadcast communication\"\"\"\n    \n    def __init__(self, communication_protocol: SwarmCommunicationProtocol):\n        self.comm_protocol = communication_protocol\n        self.broadcast_history = []\n    \n    def emergency_broadcast(self, sender_id: str, alert_type: str,\n                          alert_data: Dict[str, Any]) -> int:\n        \"\"\"Send emergency broadcast with high priority\"\"\"\n        \n        content = {\n            'alert_type': alert_type,\n            'alert_data': alert_data,\n            'emergency': True\n        }\n        \n        count = self.comm_protocol.broadcast_message(\n            sender_id, MessageType.WARNING, content, priority=10\n        )\n        \n        self.broadcast_history.append({\n            'timestamp': time.time(),\n            'sender': sender_id,\n            'type': alert_type,\n            'recipients': count\n        })\n        \n        return count\n    \n    def coordinate_swarm_action(self, coordinator_id: str,\n                              action_type: str, action_params: Dict[str, Any]) -> int:\n        \"\"\"Coordinate collective swarm action\"\"\"\n        \n        content = {\n            'action_type': action_type,\n            'parameters': action_params,\n            'coordination_id': f\"coord_{time.time()}\"\n        }\n        \n        return self.comm_protocol.broadcast_message(\n            coordinator_id, MessageType.COORDINATION, content, priority=5\n        )\n\n\n# Factory functions\ndef create_swarm_communication_protocol(topology: CommunicationTopology = CommunicationTopology.GLOBAL) -> SwarmCommunicationProtocol:\n    \"\"\"Create swarm communication protocol\"\"\"\n    return SwarmCommunicationProtocol(topology)\n\n\ndef create_broadcast_protocol(communication_protocol: SwarmCommunicationProtocol) -> BroadcastProtocol:\n    \"\"\"Create broadcast protocol\"\"\"\n    return BroadcastProtocol(communication_protocol)