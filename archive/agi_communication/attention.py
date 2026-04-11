"""
Shared Attention Mechanisms for Joint Tasks
===========================================

Advanced attention coordination system that enables multiple AGIs
to synchronize their attention and work collaboratively on shared tasks.
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import uuid
import heapq
from collections import defaultdict, deque

from .core import CommunicationMessage, MessageType

logger = logging.getLogger(__name__)

class AttentionType(Enum):
    """Types of attention mechanisms."""
    FOCUSED = "focused"  # Concentrated attention on specific item
    DISTRIBUTED = "distributed"  # Distributed across multiple items
    SELECTIVE = "selective"  # Selective attention with filtering
    SUSTAINED = "sustained"  # Sustained attention over time
    DIVIDED = "divided"  # Divided attention between multiple tasks
    EXECUTIVE = "executive"  # Executive attention for control

class AttentionScope(Enum):
    """Scope of attention."""
    LOCAL = "local"  # Single AGI
    SHARED = "shared"  # Multiple AGIs
    GLOBAL = "global"  # Entire network
    HIERARCHICAL = "hierarchical"  # Hierarchical attention structure

class PriorityLevel(Enum):
    """Priority levels for attention targets."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"

@dataclass
class AttentionTarget:
    """Represents a target of attention."""
    id: str
    description: str
    content: Any
    priority: PriorityLevel
    attention_weight: float  # 0-1 scale
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    associated_tasks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    decay_rate: float = 0.95  # How quickly attention weight decays
    
    def update_access(self):
        """Update access information."""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def decay_attention(self, time_delta: timedelta):
        """Apply temporal decay to attention weight."""
        decay_factor = self.decay_rate ** (time_delta.total_seconds() / 3600)  # Hourly decay
        self.attention_weight *= decay_factor

@dataclass
class AttentionState:
    """Current attention state of an AGI."""
    agi_id: str
    current_targets: Dict[str, AttentionTarget] = field(default_factory=dict)
    focus_target: Optional[str] = None  # Currently focused target ID
    attention_capacity: float = 1.0  # Total attention capacity
    used_capacity: float = 0.0  # Currently used capacity
    attention_history: List[Dict[str, Any]] = field(default_factory=list)
    shared_contexts: Set[str] = field(default_factory=set)  # Shared attention contexts
    
    def add_target(self, target: AttentionTarget):
        """Add attention target."""
        self.current_targets[target.id] = target
        self._update_used_capacity()
    
    def remove_target(self, target_id: str):
        """Remove attention target."""
        if target_id in self.current_targets:
            del self.current_targets[target_id]
            self._update_used_capacity()
    
    def set_focus(self, target_id: Optional[str]):
        """Set focus to specific target."""
        if target_id and target_id in self.current_targets:
            self.focus_target = target_id
            self.current_targets[target_id].update_access()
        else:
            self.focus_target = None
    
    def _update_used_capacity(self):
        """Update used attention capacity."""
        self.used_capacity = sum(target.attention_weight for target in self.current_targets.values())
    
    def get_available_capacity(self) -> float:
        """Get available attention capacity."""
        return max(0.0, self.attention_capacity - self.used_capacity)
    
    def get_top_targets(self, n: int = 5) -> List[AttentionTarget]:
        """Get top N attention targets by weight."""
        return sorted(self.current_targets.values(), 
                     key=lambda t: t.attention_weight, reverse=True)[:n]

@dataclass
class SharedAttentionContext:
    """Shared attention context between multiple AGIs."""
    id: str
    name: str
    description: str
    participants: Set[str]  # AGI IDs
    shared_targets: Dict[str, AttentionTarget] = field(default_factory=dict)
    attention_map: Dict[str, Dict[str, float]] = field(default_factory=dict)  # agi_id -> target_id -> weight
    coordination_strategy: str = "consensus"  # consensus, weighted, hierarchical
    created_at: datetime = field(default_factory=datetime.now)
    last_synchronized: datetime = field(default_factory=datetime.now)
    synchronization_frequency: timedelta = field(default=timedelta(seconds=30))
    
    def add_participant(self, agi_id: str):
        """Add participant to shared context."""
        self.participants.add(agi_id)
        if agi_id not in self.attention_map:
            self.attention_map[agi_id] = {}
    
    def remove_participant(self, agi_id: str):
        """Remove participant from shared context."""
        self.participants.discard(agi_id)
        if agi_id in self.attention_map:
            del self.attention_map[agi_id]
    
    def update_attention(self, agi_id: str, target_id: str, weight: float):
        """Update attention weight for AGI on specific target."""
        if agi_id not in self.attention_map:
            self.attention_map[agi_id] = {}
        self.attention_map[agi_id][target_id] = weight
    
    def get_consensus_attention(self) -> Dict[str, float]:
        """Calculate consensus attention weights across all participants."""
        consensus = {}
        
        # Get all targets being attended to
        all_targets = set()
        for agi_attention in self.attention_map.values():
            all_targets.update(agi_attention.keys())
        
        # Calculate consensus weights
        for target_id in all_targets:
            weights = []
            for agi_id in self.participants:
                weight = self.attention_map.get(agi_id, {}).get(target_id, 0.0)
                weights.append(weight)
            
            if weights:
                consensus[target_id] = sum(weights) / len(weights)
        
        return consensus
    
    def needs_synchronization(self) -> bool:
        """Check if synchronization is needed."""
        return (datetime.now() - self.last_synchronized) > self.synchronization_frequency

class AttentionCoordinator:
    """Coordinates attention across multiple AGIs."""
    
    def __init__(self):
        self.attention_policies: Dict[str, Callable] = {}
        self.conflict_resolvers: Dict[str, Callable] = {}
        
        # Register default policies
        self._register_default_policies()
    
    def _register_default_policies(self):
        """Register default attention coordination policies."""
        self.attention_policies.update({
            'round_robin': self._round_robin_policy,
            'priority_based': self._priority_based_policy,
            'capacity_aware': self._capacity_aware_policy,
            'consensus_driven': self._consensus_driven_policy
        })
        
        self.conflict_resolvers.update({
            'priority': self._resolve_by_priority,
            'consensus': self._resolve_by_consensus,
            'capacity': self._resolve_by_capacity
        })
    
    def coordinate_attention(self, context: SharedAttentionContext, 
                           attention_states: Dict[str, AttentionState]) -> Dict[str, List[str]]:
        """Coordinate attention allocation among participants."""
        # Use consensus-driven policy by default
        return self.attention_policies['consensus_driven'](context, attention_states)
    
    def _round_robin_policy(self, context: SharedAttentionContext, 
                          attention_states: Dict[str, AttentionState]) -> Dict[str, List[str]]:
        """Round-robin attention allocation."""
        allocations = {agi_id: [] for agi_id in context.participants}
        
        targets = list(context.shared_targets.keys())
        participants = list(context.participants)
        
        for i, target_id in enumerate(targets):
            assigned_agi = participants[i % len(participants)]
            allocations[assigned_agi].append(target_id)
        
        return allocations
    
    def _priority_based_policy(self, context: SharedAttentionContext, 
                             attention_states: Dict[str, AttentionState]) -> Dict[str, List[str]]:
        """Priority-based attention allocation."""
        allocations = {agi_id: [] for agi_id in context.participants}
        
        # Sort targets by priority
        sorted_targets = sorted(
            context.shared_targets.values(),
            key=lambda t: (t.priority.value, -t.attention_weight),
            reverse=True
        )
        
        # Allocate to AGIs with available capacity
        for target in sorted_targets:
            best_agi = None
            best_capacity = -1
            
            for agi_id in context.participants:
                if agi_id in attention_states:
                    available_capacity = attention_states[agi_id].get_available_capacity()
                    if available_capacity > best_capacity and available_capacity >= target.attention_weight:
                        best_capacity = available_capacity
                        best_agi = agi_id
            
            if best_agi:
                allocations[best_agi].append(target.id)
        
        return allocations
    
    def _capacity_aware_policy(self, context: SharedAttentionContext, 
                             attention_states: Dict[str, AttentionState]) -> Dict[str, List[str]]:
        """Capacity-aware attention allocation."""
        allocations = {agi_id: [] for agi_id in context.participants}
        
        # Create priority queue of (capacity, agi_id)
        capacity_queue = []
        for agi_id in context.participants:
            if agi_id in attention_states:
                capacity = attention_states[agi_id].get_available_capacity()
                heapq.heappush(capacity_queue, (-capacity, agi_id))  # Negative for max-heap
        
        # Allocate targets to AGIs with most capacity
        for target in context.shared_targets.values():
            if capacity_queue:
                neg_capacity, agi_id = heapq.heappop(capacity_queue)
                capacity = -neg_capacity
                
                if capacity >= target.attention_weight:
                    allocations[agi_id].append(target.id)
                    # Update capacity and re-add to queue
                    new_capacity = capacity - target.attention_weight
                    heapq.heappush(capacity_queue, (-new_capacity, agi_id))
        
        return allocations
    
    def _consensus_driven_policy(self, context: SharedAttentionContext, 
                               attention_states: Dict[str, AttentionState]) -> Dict[str, List[str]]:
        """Consensus-driven attention allocation."""
        allocations = {agi_id: [] for agi_id in context.participants}
        
        # Get consensus attention weights
        consensus = context.get_consensus_attention()
        
        # Sort targets by consensus weight
        sorted_targets = sorted(consensus.items(), key=lambda x: x[1], reverse=True)
        
        # Allocate based on individual preferences weighted by consensus
        for target_id, consensus_weight in sorted_targets:
            if target_id in context.shared_targets:
                target = context.shared_targets[target_id]
                
                # Find AGI with highest individual attention to this target
                best_agi = None
                best_weight = 0
                
                for agi_id in context.participants:
                    individual_weight = context.attention_map.get(agi_id, {}).get(target_id, 0)
                    if individual_weight > best_weight:
                        if agi_id in attention_states:
                            available_capacity = attention_states[agi_id].get_available_capacity()
                            if available_capacity >= target.attention_weight:
                                best_weight = individual_weight
                                best_agi = agi_id
                
                if best_agi:
                    allocations[best_agi].append(target_id)
        
        return allocations
    
    def _resolve_by_priority(self, conflicts: List[Tuple[str, str, float]]) -> str:
        """Resolve attention conflicts by priority."""
        # conflicts is list of (agi_id, target_id, priority_score)
        return max(conflicts, key=lambda x: x[2])[0]  # Return agi_id with highest priority
    
    def _resolve_by_consensus(self, conflicts: List[Tuple[str, str, float]]) -> str:
        """Resolve attention conflicts by consensus."""
        # Simple majority rule
        agi_votes = defaultdict(int)
        for agi_id, _, _ in conflicts:
            agi_votes[agi_id] += 1
        return max(agi_votes.keys(), key=lambda k: agi_votes[k])
    
    def _resolve_by_capacity(self, conflicts: List[Tuple[str, str, float]]) -> str:
        """Resolve attention conflicts by available capacity."""
        return max(conflicts, key=lambda x: x[2])[0]  # Assuming third element is capacity

class SharedAttentionMechanism:
    """
    Shared Attention Mechanisms for Joint Tasks
    
    Coordinates attention across multiple AGIs to enable effective
    collaboration and task synchronization.
    """
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.attention_state = AttentionState(agi_id=protocol.identity.id)
        self.shared_contexts: Dict[str, SharedAttentionContext] = {}
        self.coordinator = AttentionCoordinator()
        self.attention_history: List[Dict[str, Any]] = []
        
        # Attention parameters
        self.max_targets = 20
        self.decay_interval = timedelta(hours=1)
        self.sync_interval = timedelta(seconds=30)
        
        # Start background processes
        asyncio.create_task(self._attention_decay_process())
        asyncio.create_task(self._synchronization_process())
    
    async def focus_on(self, target: AttentionTarget, context_id: Optional[str] = None) -> bool:
        """Focus attention on a specific target."""
        # Check if we have capacity
        if self.attention_state.get_available_capacity() < target.attention_weight:
            # Try to free up capacity by removing low-priority targets
            await self._manage_capacity(target.attention_weight)
        
        if self.attention_state.get_available_capacity() >= target.attention_weight:
            self.attention_state.add_target(target)
            self.attention_state.set_focus(target.id)
            
            # If part of shared context, update shared attention
            if context_id and context_id in self.shared_contexts:
                await self._update_shared_attention(context_id, target.id, target.attention_weight)
            
            self._record_attention_event("focus", target.id, context_id)
            return True
        
        return False
    
    async def distribute_attention(self, targets: List[AttentionTarget], 
                                 context_id: Optional[str] = None) -> List[str]:
        """Distribute attention across multiple targets."""
        successfully_added = []
        
        # Sort targets by priority
        sorted_targets = sorted(targets, key=lambda t: t.priority.value, reverse=True)
        
        for target in sorted_targets:
            if await self.focus_on(target, context_id):
                successfully_added.append(target.id)
        
        self._record_attention_event("distribute", successfully_added, context_id)
        return successfully_added
    
    async def create_shared_context(self, name: str, description: str, 
                                  participants: List[str]) -> str:
        """Create a shared attention context."""
        context_id = str(uuid.uuid4())
        
        context = SharedAttentionContext(
            id=context_id,
            name=name,
            description=description,
            participants=set(participants + [self.protocol.identity.id])
        )
        
        self.shared_contexts[context_id] = context
        self.attention_state.shared_contexts.add(context_id)
        
        # Notify participants
        for participant_id in participants:
            invite_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=participant_id,
                message_type=MessageType.ATTENTION_SYNC,
                timestamp=datetime.now(),
                payload={
                    'action': 'context_invitation',
                    'context_id': context_id,
                    'context_name': name,
                    'context_description': description,
                    'participants': list(context.participants)
                }
            )
            
            await self.protocol.send_message(invite_message)
        
        logger.info(f"Created shared attention context {context_id}: {name}")
        return context_id
    
    async def join_shared_context(self, context_id: str) -> bool:
        """Join an existing shared attention context."""
        if context_id in self.shared_contexts:
            context = self.shared_contexts[context_id]
            context.add_participant(self.protocol.identity.id)
            self.attention_state.shared_contexts.add(context_id)
            return True
        
        return False
    
    async def synchronize_attention(self, context_id: str):
        """Synchronize attention with other participants in shared context."""
        if context_id not in self.shared_contexts:
            return
        
        context = self.shared_contexts[context_id]
        
        # Update our attention in the shared context
        for target_id, target in self.attention_state.current_targets.items():
            context.update_attention(self.protocol.identity.id, target_id, target.attention_weight)
        
        # Request attention updates from other participants
        for participant_id in context.participants:
            if participant_id != self.protocol.identity.id:
                sync_message = CommunicationMessage(
                    id=str(uuid.uuid4()),
                    sender_id=self.protocol.identity.id,
                    receiver_id=participant_id,
                    message_type=MessageType.ATTENTION_SYNC,
                    timestamp=datetime.now(),
                    payload={
                        'action': 'sync_request',
                        'context_id': context_id,
                        'my_attention': {
                            target_id: target.attention_weight 
                            for target_id, target in self.attention_state.current_targets.items()
                        }
                    }
                )
                
                await self.protocol.send_message(sync_message)
        
        context.last_synchronized = datetime.now()
    
    async def coordinate_shared_attention(self, context_id: str) -> Dict[str, List[str]]:
        """Coordinate attention allocation in shared context."""
        if context_id not in self.shared_contexts:
            return {}
        
        context = self.shared_contexts[context_id]
        
        # Get attention states of all participants (simplified)
        attention_states = {self.protocol.identity.id: self.attention_state}
        
        # Use coordinator to determine allocations
        allocations = self.coordinator.coordinate_attention(context, attention_states)
        
        # Send allocation recommendations to participants
        for participant_id in context.participants:
            if participant_id != self.protocol.identity.id and participant_id in allocations:
                allocation_message = CommunicationMessage(
                    id=str(uuid.uuid4()),
                    sender_id=self.protocol.identity.id,
                    receiver_id=participant_id,
                    message_type=MessageType.ATTENTION_SYNC,
                    timestamp=datetime.now(),
                    payload={
                        'action': 'attention_allocation',
                        'context_id': context_id,
                        'allocated_targets': allocations[participant_id],
                        'coordination_timestamp': datetime.now().isoformat()
                    }
                )
                
                await self.protocol.send_message(allocation_message)
        
        return allocations
    
    async def _manage_capacity(self, required_capacity: float):
        """Manage attention capacity by removing low-priority targets."""
        # Sort targets by priority and access time
        targets = list(self.attention_state.current_targets.values())
        targets.sort(key=lambda t: (t.priority.value, t.last_accessed))
        
        freed_capacity = 0.0
        targets_to_remove = []
        
        for target in targets:
            if freed_capacity >= required_capacity:
                break
            
            targets_to_remove.append(target.id)
            freed_capacity += target.attention_weight
        
        # Remove targets
        for target_id in targets_to_remove:
            self.attention_state.remove_target(target_id)
            self._record_attention_event("removed_for_capacity", target_id)
    
    async def _update_shared_attention(self, context_id: str, target_id: str, weight: float):
        """Update attention in shared context."""
        if context_id in self.shared_contexts:
            context = self.shared_contexts[context_id]
            context.update_attention(self.protocol.identity.id, target_id, weight)
    
    def _record_attention_event(self, event_type: str, target_info: Any, context_id: Optional[str] = None):
        """Record attention event for analysis."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'target_info': target_info,
            'context_id': context_id,
            'attention_capacity_used': self.attention_state.used_capacity,
            'focus_target': self.attention_state.focus_target
        }
        
        self.attention_history.append(event)
        
        # Keep history limited
        if len(self.attention_history) > 1000:
            self.attention_history = self.attention_history[-800:]
    
    async def _attention_decay_process(self):
        """Background process to decay attention weights over time."""
        while True:
            try:
                current_time = datetime.now()
                
                for target in self.attention_state.current_targets.values():
                    time_since_access = current_time - target.last_accessed
                    if time_since_access > self.decay_interval:
                        target.decay_attention(time_since_access)
                
                # Remove targets with very low attention
                to_remove = [
                    target_id for target_id, target in self.attention_state.current_targets.items()
                    if target.attention_weight < 0.01
                ]
                
                for target_id in to_remove:
                    self.attention_state.remove_target(target_id)
                    self._record_attention_event("decayed", target_id)
                
                await asyncio.sleep(60)  # Check every minute
            
            except Exception as e:
                logger.error(f"Error in attention decay process: {e}")
                await asyncio.sleep(60)
    
    async def _synchronization_process(self):
        """Background process to synchronize shared attention contexts."""
        while True:
            try:
                for context_id, context in self.shared_contexts.items():
                    if context.needs_synchronization():
                        await self.synchronize_attention(context_id)
                
                await asyncio.sleep(30)  # Check every 30 seconds
            
            except Exception as e:
                logger.error(f"Error in synchronization process: {e}")
                await asyncio.sleep(30)
    
    async def handle_attention_sync(self, message: CommunicationMessage):
        """Handle attention synchronization message from another AGI."""
        payload = message.payload
        action = payload.get('action')
        
        try:
            if action == 'context_invitation':
                await self._handle_context_invitation(message)
            elif action == 'sync_request':
                await self._handle_sync_request(message)
            elif action == 'sync_response':
                await self._handle_sync_response(message)
            elif action == 'attention_allocation':
                await self._handle_attention_allocation(message)
            else:
                logger.warning(f"Unknown attention sync action: {action}")
        
        except Exception as e:
            logger.error(f"Error handling attention sync: {e}")
    
    async def _handle_context_invitation(self, message: CommunicationMessage):
        """Handle shared context invitation."""
        payload = message.payload
        context_id = payload['context_id']
        context_name = payload['context_name']
        context_description = payload['context_description']
        participants = set(payload['participants'])
        
        # Accept invitation (could add logic for selective acceptance)
        context = SharedAttentionContext(
            id=context_id,
            name=context_name,
            description=context_description,
            participants=participants
        )
        
        self.shared_contexts[context_id] = context
        self.attention_state.shared_contexts.add(context_id)
        
        # Send acceptance response
        response_message = CommunicationMessage(
            id=str(uuid.uuid4()),
            sender_id=self.protocol.identity.id,
            receiver_id=message.sender_id,
            message_type=MessageType.ATTENTION_SYNC,
            timestamp=datetime.now(),
            payload={
                'action': 'context_acceptance',
                'context_id': context_id,
                'accepted': True
            }
        )
        
        await self.protocol.send_message(response_message)
    
    async def _handle_sync_request(self, message: CommunicationMessage):
        """Handle synchronization request."""
        payload = message.payload
        context_id = payload['context_id']
        their_attention = payload['my_attention']
        
        if context_id in self.shared_contexts:
            context = self.shared_contexts[context_id]
            
            # Update their attention in context
            for target_id, weight in their_attention.items():
                context.update_attention(message.sender_id, target_id, weight)
            
            # Send our attention back
            response_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.ATTENTION_SYNC,
                timestamp=datetime.now(),
                payload={
                    'action': 'sync_response',
                    'context_id': context_id,
                    'my_attention': {
                        target_id: target.attention_weight 
                        for target_id, target in self.attention_state.current_targets.items()
                    }
                }
            )
            
            await self.protocol.send_message(response_message)
    
    async def _handle_sync_response(self, message: CommunicationMessage):
        """Handle synchronization response."""
        payload = message.payload
        context_id = payload['context_id']
        their_attention = payload['my_attention']
        
        if context_id in self.shared_contexts:
            context = self.shared_contexts[context_id]
            
            # Update their attention in context
            for target_id, weight in their_attention.items():
                context.update_attention(message.sender_id, target_id, weight)
    
    async def _handle_attention_allocation(self, message: CommunicationMessage):
        """Handle attention allocation recommendation."""
        payload = message.payload
        context_id = payload['context_id']
        allocated_targets = payload['allocated_targets']
        
        # Apply allocation recommendations (simplified implementation)
        for target_id in allocated_targets:
            if context_id in self.shared_contexts:
                context = self.shared_contexts[context_id]
                if target_id in context.shared_targets:
                    target = context.shared_targets[target_id]
                    await self.focus_on(target, context_id)
    
    def get_attention_statistics(self) -> Dict[str, Any]:
        """Get attention mechanism statistics."""
        return {
            'current_targets': len(self.attention_state.current_targets),
            'attention_capacity_used': self.attention_state.used_capacity,
            'attention_capacity_available': self.attention_state.get_available_capacity(),
            'focus_target': self.attention_state.focus_target,
            'shared_contexts': len(self.shared_contexts),
            'attention_events': len(self.attention_history),
            'top_targets': [
                {'id': t.id, 'weight': t.attention_weight, 'priority': t.priority.value}
                for t in self.attention_state.get_top_targets()
            ]
        }