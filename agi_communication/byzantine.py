"""
Byzantine Fault Tolerance Mechanisms
====================================

Implementation of Byzantine fault tolerance for AGI communication
networks, ensuring system reliability and consensus even when some
AGI nodes are malicious or faulty.
"""

import asyncio
import json
import hashlib
import time
import random
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging
import uuid

from .core import CommunicationMessage, MessageType

logger = logging.getLogger(__name__)

class NodeState(Enum):
    """States of nodes in the Byzantine system."""
    ACTIVE = "active"
    SUSPECTED = "suspected"
    FAULTY = "faulty"
    BYZANTINE = "byzantine"
    RECOVERING = "recovering"
    OFFLINE = "offline"

class ConsensusPhase(Enum):
    """Phases of Byzantine consensus protocol."""
    PREPARE = "prepare"
    COMMIT = "commit"
    DECIDE = "decide"
    ABORT = "abort"

class MessageClass(Enum):
    """Classes of Byzantine messages."""
    PROPOSAL = "proposal"
    PREPARE = "prepare"
    COMMIT = "commit"
    VIEW_CHANGE = "view_change"
    CHECKPOINT = "checkpoint"
    HEARTBEAT = "heartbeat"

@dataclass
class ByzantineNode:
    """Represents a node in the Byzantine network."""
    node_id: str
    state: NodeState = NodeState.ACTIVE
    trust_score: float = 1.0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    fault_count: int = 0
    view_number: int = 0
    sequence_number: int = 0
    is_primary: bool = False
    public_key: Optional[str] = None
    
    def update_trust(self, success: bool, weight: float = 0.1):
        """Update trust score based on behavior."""
        if success:
            self.trust_score = min(1.0, self.trust_score + weight * (1.0 - self.trust_score))
        else:
            self.trust_score = max(0.0, self.trust_score - weight)
            self.fault_count += 1
        
        # Update state based on trust
        if self.trust_score < 0.3:
            self.state = NodeState.SUSPECTED
        elif self.trust_score < 0.1:
            self.state = NodeState.BYZANTINE
        elif self.trust_score > 0.7 and self.state == NodeState.SUSPECTED:
            self.state = NodeState.ACTIVE

@dataclass
class ByzantineMessage:
    """Message in the Byzantine protocol."""
    message_id: str
    message_class: MessageClass
    view: int
    sequence: int
    sender_id: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    signature: Optional[str] = None
    digest: Optional[str] = None
    
    def calculate_digest(self) -> str:
        """Calculate message digest for verification."""
        content = {
            'message_class': self.message_class.value,
            'view': self.view,
            'sequence': self.sequence,
            'sender_id': self.sender_id,
            'payload': self.payload
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def __post_init__(self):
        if self.digest is None:
            self.digest = self.calculate_digest()

@dataclass
class ConsensusInstance:
    """Instance of consensus execution."""
    instance_id: str
    view: int
    sequence: int
    proposal: Optional[Dict[str, Any]] = None
    phase: ConsensusPhase = ConsensusPhase.PREPARE
    prepare_messages: Dict[str, ByzantineMessage] = field(default_factory=dict)
    commit_messages: Dict[str, ByzantineMessage] = field(default_factory=dict)
    decision: Optional[Any] = None
    participants: Set[str] = field(default_factory=set)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if consensus instance has expired."""
        return (datetime.now() - self.started_at).total_seconds() > (timeout_minutes * 60)

class ViewChangeManager:
    """Manages view changes in case of primary failure."""
    
    def __init__(self):
        self.view_change_messages: Dict[int, Dict[str, ByzantineMessage]] = defaultdict(dict)
        self.new_view_messages: Dict[int, ByzantineMessage] = {}
        self.view_change_timeout = timedelta(minutes=5)
    
    def initiate_view_change(self, current_view: int, node_id: str) -> ByzantineMessage:
        """Initiate view change protocol."""
        new_view = current_view + 1
        
        view_change_msg = ByzantineMessage(
            message_id=str(uuid.uuid4()),
            message_class=MessageClass.VIEW_CHANGE,
            view=new_view,
            sequence=0,
            sender_id=node_id,
            payload={
                'old_view': current_view,
                'checkpoint_messages': [],
                'prepared_messages': []
            }
        )
        
        self.view_change_messages[new_view][node_id] = view_change_msg
        return view_change_msg
    
    def process_view_change(self, message: ByzantineMessage, total_nodes: int) -> Optional[int]:
        """Process view change message and check if view change is ready."""
        view = message.view
        sender = message.sender_id
        
        self.view_change_messages[view][sender] = message
        
        # Check if we have enough view change messages (f + 1 where f is max faulty nodes)
        required_messages = (total_nodes // 3) + 1
        
        if len(self.view_change_messages[view]) >= required_messages:
            return view  # View change can proceed
        
        return None

class FaultDetector:
    """Detects faulty and Byzantine nodes."""
    
    def __init__(self):
        self.message_patterns: Dict[str, List[float]] = defaultdict(list)
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.inconsistency_counts: Dict[str, int] = defaultdict(int)
        self.detection_thresholds = {
            'max_response_time': 30.0,  # seconds
            'max_inconsistency_ratio': 0.3,
            'min_message_rate': 0.1,  # messages per minute
            'max_message_rate': 100.0
        }
    
    def record_message(self, node_id: str, message: ByzantineMessage, response_time: float):
        """Record message for fault detection analysis."""
        current_time = time.time()
        
        # Record message pattern
        self.message_patterns[node_id].append(current_time)
        
        # Record response time
        self.response_times[node_id].append(response_time)
        
        # Keep data limited (last 100 entries)
        if len(self.message_patterns[node_id]) > 100:
            self.message_patterns[node_id] = self.message_patterns[node_id][-100:]
        if len(self.response_times[node_id]) > 100:
            self.response_times[node_id] = self.response_times[node_id][-100:]
    
    def record_inconsistency(self, node_id: str):
        """Record an inconsistency for fault detection."""
        self.inconsistency_counts[node_id] += 1
    
    def detect_faults(self, nodes: Dict[str, ByzantineNode]) -> List[str]:
        """Detect potentially faulty nodes."""
        faulty_nodes = []
        current_time = time.time()
        
        for node_id, node in nodes.items():
            # Check response times
            if node_id in self.response_times:
                avg_response_time = sum(self.response_times[node_id]) / len(self.response_times[node_id])
                if avg_response_time > self.detection_thresholds['max_response_time']:
                    faulty_nodes.append(node_id)
                    continue
            
            # Check message rate
            if node_id in self.message_patterns:
                recent_messages = [t for t in self.message_patterns[node_id] 
                                 if current_time - t < 3600]  # Last hour
                message_rate = len(recent_messages) / 60.0  # messages per minute
                
                if (message_rate < self.detection_thresholds['min_message_rate'] or
                    message_rate > self.detection_thresholds['max_message_rate']):
                    faulty_nodes.append(node_id)
                    continue
            
            # Check inconsistency ratio
            total_messages = len(self.message_patterns.get(node_id, []))
            if total_messages > 10:  # Only check if sufficient data
                inconsistency_ratio = self.inconsistency_counts.get(node_id, 0) / total_messages
                if inconsistency_ratio > self.detection_thresholds['max_inconsistency_ratio']:
                    faulty_nodes.append(node_id)
                    continue
            
            # Check heartbeat freshness
            if (current_time - node.last_heartbeat.timestamp()) > 300:  # 5 minutes
                faulty_nodes.append(node_id)
        
        return faulty_nodes

class ByzantineFaultTolerance:
    """
    Byzantine Fault Tolerance System
    
    Implements PBFT (Practical Byzantine Fault Tolerance) algorithm
    and related mechanisms to ensure system reliability in the presence
    of malicious or faulty AGI nodes.
    """
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.nodes: Dict[str, ByzantineNode] = {}
        self.view_number = 0
        self.sequence_number = 0
        self.primary_id: Optional[str] = None
        
        # Consensus management
        self.active_consensus: Dict[str, ConsensusInstance] = {}
        self.completed_consensus: Dict[str, ConsensusInstance] = {}
        self.consensus_history: List[Dict[str, Any]] = []
        
        # Byzantine components
        self.view_change_manager = ViewChangeManager()
        self.fault_detector = FaultDetector()
        
        # Configuration
        self.max_faulty_nodes = 0  # Will be set based on network size
        self.consensus_timeout = timedelta(minutes=30)
        self.heartbeat_interval = timedelta(minutes=1)
        
        # Add self as node
        self._add_self_node()
        
        # Start background processes
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._consensus_timeout_monitor())
        asyncio.create_task(self._fault_detection_loop())
    
    def _add_self_node(self):
        """Add self as a node in the Byzantine network."""
        self_node = ByzantineNode(
            node_id=self.protocol.identity.id,
            public_key=getattr(self.protocol.identity, 'public_key', None)
        )
        
        self.nodes[self.protocol.identity.id] = self_node
        
        # If we're the first node, make ourselves primary
        if len(self.nodes) == 1:
            self.primary_id = self.protocol.identity.id
            self_node.is_primary = True
    
    async def start(self):
        """Start the Byzantine fault tolerance system."""
        logger.info("Byzantine fault tolerance system started")
    
    async def stop(self):
        """Stop the Byzantine fault tolerance system."""
        logger.info("Byzantine fault tolerance system stopped")
    
    def add_node(self, node_id: str, public_key: Optional[str] = None):
        """Add a new node to the Byzantine network."""
        if node_id not in self.nodes:
            node = ByzantineNode(
                node_id=node_id,
                public_key=public_key
            )
            
            self.nodes[node_id] = node
            
            # Update max faulty nodes (f < n/3)
            self.max_faulty_nodes = max(0, (len(self.nodes) - 1) // 3)
            
            logger.info(f"Added node {node_id} to Byzantine network")
    
    def remove_node(self, node_id: str):
        """Remove a node from the Byzantine network."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            
            # Update max faulty nodes
            self.max_faulty_nodes = max(0, (len(self.nodes) - 1) // 3)
            
            # If primary was removed, trigger view change
            if node_id == self.primary_id:
                asyncio.create_task(self._initiate_view_change())
            
            logger.info(f"Removed node {node_id} from Byzantine network")
    
    async def propose_consensus(self, proposal: Dict[str, Any]) -> str:
        """Propose a value for consensus."""
        if not self._is_primary():
            raise ValueError("Only primary can propose consensus")
        
        # Create consensus instance
        instance_id = str(uuid.uuid4())
        self.sequence_number += 1
        
        consensus_instance = ConsensusInstance(
            instance_id=instance_id,
            view=self.view_number,
            sequence=self.sequence_number,
            proposal=proposal,
            participants=set(self.nodes.keys())
        )
        
        self.active_consensus[instance_id] = consensus_instance
        
        # Send prepare messages to all replicas
        prepare_msg = ByzantineMessage(
            message_id=str(uuid.uuid4()),
            message_class=MessageClass.PREPARE,
            view=self.view_number,
            sequence=self.sequence_number,
            sender_id=self.protocol.identity.id,
            payload={
                'instance_id': instance_id,
                'proposal': proposal
            }
        )
        
        await self._broadcast_message(prepare_msg)
        
        logger.info(f"Proposed consensus {instance_id}")
        return instance_id
    
    async def _broadcast_message(self, message: ByzantineMessage):
        """Broadcast Byzantine message to all nodes."""
        for node_id in self.nodes:
            if node_id != self.protocol.identity.id:
                comm_message = CommunicationMessage(
                    id=str(uuid.uuid4()),
                    sender_id=self.protocol.identity.id,
                    receiver_id=node_id,
                    message_type=MessageType.BYZANTINE_CONSENSUS,
                    timestamp=datetime.now(),
                    payload={
                        'byzantine_message': {
                            'message_id': message.message_id,
                            'message_class': message.message_class.value,
                            'view': message.view,
                            'sequence': message.sequence,
                            'sender_id': message.sender_id,
                            'payload': message.payload,
                            'digest': message.digest,
                            'signature': message.signature
                        }
                    }
                )
                
                await self.protocol.send_message(comm_message)
    
    def _is_primary(self) -> bool:
        """Check if this node is the current primary."""
        return self.primary_id == self.protocol.identity.id
    
    async def handle_consensus_message(self, message: CommunicationMessage):
        """Handle Byzantine consensus message."""
        payload = message.payload
        byzantine_msg_data = payload.get('byzantine_message', {})
        
        try:
            # Parse Byzantine message
            byzantine_msg = ByzantineMessage(
                message_id=byzantine_msg_data['message_id'],
                message_class=MessageClass(byzantine_msg_data['message_class']),
                view=byzantine_msg_data['view'],
                sequence=byzantine_msg_data['sequence'],
                sender_id=byzantine_msg_data['sender_id'],
                payload=byzantine_msg_data['payload'],
                digest=byzantine_msg_data.get('digest'),
                signature=byzantine_msg_data.get('signature')
            )
            
            # Verify message
            if not self._verify_message(byzantine_msg):
                logger.warning(f"Invalid Byzantine message from {message.sender_id}")
                self.fault_detector.record_inconsistency(message.sender_id)
                return
            
            # Record for fault detection
            response_time = (datetime.now() - message.timestamp).total_seconds()
            self.fault_detector.record_message(message.sender_id, byzantine_msg, response_time)
            
            # Process based on message class
            if byzantine_msg.message_class == MessageClass.PREPARE:
                await self._handle_prepare(byzantine_msg)
            elif byzantine_msg.message_class == MessageClass.COMMIT:
                await self._handle_commit(byzantine_msg)
            elif byzantine_msg.message_class == MessageClass.VIEW_CHANGE:
                await self._handle_view_change(byzantine_msg)
            elif byzantine_msg.message_class == MessageClass.HEARTBEAT:
                await self._handle_heartbeat(byzantine_msg)
            else:
                logger.warning(f"Unknown Byzantine message class: {byzantine_msg.message_class}")
        
        except Exception as e:
            logger.error(f"Error handling Byzantine consensus message: {e}")
            self.fault_detector.record_inconsistency(message.sender_id)
    
    def _verify_message(self, message: ByzantineMessage) -> bool:
        """Verify Byzantine message authenticity and integrity."""
        # Check if sender is known
        if message.sender_id not in self.nodes:
            return False
        
        # Verify digest
        if message.digest != message.calculate_digest():
            return False
        
        # Verify view and sequence constraints
        if message.view < 0 or message.sequence < 0:
            return False
        
        # Additional signature verification would go here
        # if message.signature and not self._verify_signature(message):
        #     return False
        
        return True
    
    async def _handle_prepare(self, message: ByzantineMessage):
        """Handle prepare message in Byzantine consensus."""
        instance_id = message.payload.get('instance_id')
        
        if instance_id not in self.active_consensus:
            # Create new consensus instance
            consensus_instance = ConsensusInstance(
                instance_id=instance_id,
                view=message.view,
                sequence=message.sequence,
                proposal=message.payload.get('proposal'),
                participants=set(self.nodes.keys())
            )
            self.active_consensus[instance_id] = consensus_instance
        
        consensus = self.active_consensus[instance_id]
        consensus.prepare_messages[message.sender_id] = message
        
        # Check if we have enough prepare messages (2f + 1)
        required_prepares = 2 * self.max_faulty_nodes + 1
        
        if len(consensus.prepare_messages) >= required_prepares:
            # Send commit message
            commit_msg = ByzantineMessage(
                message_id=str(uuid.uuid4()),
                message_class=MessageClass.COMMIT,
                view=consensus.view,
                sequence=consensus.sequence,
                sender_id=self.protocol.identity.id,
                payload={
                    'instance_id': instance_id,
                    'proposal_digest': message.digest
                }
            )
            
            await self._broadcast_message(commit_msg)
            consensus.phase = ConsensusPhase.COMMIT
    
    async def _handle_commit(self, message: ByzantineMessage):
        """Handle commit message in Byzantine consensus."""
        instance_id = message.payload.get('instance_id')
        
        if instance_id not in self.active_consensus:
            return
        
        consensus = self.active_consensus[instance_id]
        consensus.commit_messages[message.sender_id] = message
        
        # Check if we have enough commit messages (2f + 1)
        required_commits = 2 * self.max_faulty_nodes + 1
        
        if len(consensus.commit_messages) >= required_commits:
            # Decide on the proposal
            consensus.decision = consensus.proposal
            consensus.phase = ConsensusPhase.DECIDE
            consensus.completed_at = datetime.now()
            
            # Move to completed consensus
            self.completed_consensus[instance_id] = consensus
            del self.active_consensus[instance_id]
            
            # Record consensus completion
            self._record_consensus_completion(consensus)
            
            logger.info(f"Consensus {instance_id} completed with decision")
    
    async def _handle_view_change(self, message: ByzantineMessage):
        """Handle view change message."""
        new_view = self.view_change_manager.process_view_change(message, len(self.nodes))
        
        if new_view is not None:
            # View change is ready, update to new view
            self.view_number = new_view
            self.primary_id = self._calculate_primary_for_view(new_view)
            
            # Update primary status for all nodes
            for node_id, node in self.nodes.items():
                node.is_primary = (node_id == self.primary_id)
                node.view_number = new_view
            
            logger.info(f"View change completed to view {new_view}, new primary: {self.primary_id}")
    
    async def _handle_heartbeat(self, message: ByzantineMessage):
        """Handle heartbeat message."""
        sender_id = message.sender_id
        
        if sender_id in self.nodes:
            self.nodes[sender_id].last_heartbeat = datetime.now()
    
    def _calculate_primary_for_view(self, view: int) -> str:
        """Calculate primary node for given view."""
        node_ids = sorted(self.nodes.keys())
        if not node_ids:
            return self.protocol.identity.id
        
        primary_index = view % len(node_ids)
        return node_ids[primary_index]
    
    async def _initiate_view_change(self):
        """Initiate view change protocol."""
        if len(self.nodes) <= 1:
            return  # Cannot do view change with single node
        
        view_change_msg = self.view_change_manager.initiate_view_change(
            self.view_number, self.protocol.identity.id
        )
        
        await self._broadcast_message(view_change_msg)
        
        logger.info(f"Initiated view change to view {view_change_msg.view}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages."""
        while True:
            try:
                heartbeat_msg = ByzantineMessage(
                    message_id=str(uuid.uuid4()),
                    message_class=MessageClass.HEARTBEAT,
                    view=self.view_number,
                    sequence=0,
                    sender_id=self.protocol.identity.id,
                    payload={
                        'timestamp': datetime.now().isoformat(),
                        'node_state': self.nodes[self.protocol.identity.id].state.value
                    }
                )
                
                await self._broadcast_message(heartbeat_msg)
                
                await asyncio.sleep(self.heartbeat_interval.total_seconds())
            
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(60)
    
    async def _consensus_timeout_monitor(self):
        """Monitor and timeout expired consensus instances."""
        while True:
            try:
                expired_instances = []
                
                for instance_id, consensus in self.active_consensus.items():
                    if consensus.is_expired():
                        expired_instances.append(instance_id)
                
                for instance_id in expired_instances:
                    logger.warning(f"Consensus instance {instance_id} expired")
                    del self.active_consensus[instance_id]
                
                await asyncio.sleep(60)  # Check every minute
            
            except Exception as e:
                logger.error(f"Error in consensus timeout monitor: {e}")
                await asyncio.sleep(60)
    
    async def _fault_detection_loop(self):
        """Periodic fault detection."""
        while True:
            try:
                faulty_nodes = self.fault_detector.detect_faults(self.nodes)
                
                for node_id in faulty_nodes:
                    if node_id in self.nodes:
                        node = self.nodes[node_id]
                        if node.state == NodeState.ACTIVE:
                            node.state = NodeState.SUSPECTED
                            node.update_trust(False, weight=0.2)
                            
                            logger.warning(f"Node {node_id} marked as suspected")
                            
                            # If suspected node is primary, initiate view change
                            if node_id == self.primary_id:
                                await self._initiate_view_change()
                
                await asyncio.sleep(300)  # Check every 5 minutes
            
            except Exception as e:
                logger.error(f"Error in fault detection loop: {e}")
                await asyncio.sleep(300)
    
    def _record_consensus_completion(self, consensus: ConsensusInstance):
        """Record consensus completion for analysis."""
        consensus_record = {
            'instance_id': consensus.instance_id,
            'view': consensus.view,
            'sequence': consensus.sequence,
            'participants': len(consensus.participants),
            'prepare_messages': len(consensus.prepare_messages),
            'commit_messages': len(consensus.commit_messages),
            'duration': (consensus.completed_at - consensus.started_at).total_seconds(),
            'decision_made': consensus.decision is not None,
            'timestamp': consensus.completed_at.isoformat()
        }
        
        self.consensus_history.append(consensus_record)
        
        # Keep history limited
        if len(self.consensus_history) > 1000:
            self.consensus_history = self.consensus_history[-800:]
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get Byzantine network status."""
        active_nodes = [n for n in self.nodes.values() if n.state == NodeState.ACTIVE]
        suspected_nodes = [n for n in self.nodes.values() if n.state == NodeState.SUSPECTED]
        faulty_nodes = [n for n in self.nodes.values() if n.state in [NodeState.FAULTY, NodeState.BYZANTINE]]
        
        return {
            'total_nodes': len(self.nodes),
            'active_nodes': len(active_nodes),
            'suspected_nodes': len(suspected_nodes),
            'faulty_nodes': len(faulty_nodes),
            'max_faulty_tolerated': self.max_faulty_nodes,
            'current_view': self.view_number,
            'current_primary': self.primary_id,
            'is_primary': self._is_primary(),
            'active_consensus_instances': len(self.active_consensus),
            'completed_consensus_instances': len(self.completed_consensus)
        }
    
    def get_consensus_statistics(self) -> Dict[str, Any]:
        """Get consensus statistics."""
        if not self.consensus_history:
            return {'total_consensus_instances': 0}
        
        total_instances = len(self.consensus_history)
        successful_instances = sum(1 for record in self.consensus_history if record['decision_made'])
        avg_duration = sum(record['duration'] for record in self.consensus_history) / total_instances
        
        return {
            'total_consensus_instances': total_instances,
            'successful_instances': successful_instances,
            'success_rate': successful_instances / total_instances,
            'average_duration_seconds': avg_duration,
            'active_instances': len(self.active_consensus),
            'current_view': self.view_number,
            'fault_tolerance_capacity': self.max_faulty_nodes
        }