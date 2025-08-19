"""
Global Workspace Theory (GWT) Implementation

Based on Bernard Baars' Global Workspace Theory, this module implements a
consciousness model where information becomes conscious when it's broadcast
globally to all cognitive subsystems through a shared workspace.

Key components:
- Global workspace buffer
- Competitive selection mechanism
- Broadcasting system
- Specialized processors
- Coalition formation
"""

import time
import threading
import math
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import numpy as np

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState

@dataclass
class WorkspaceContent:
    """Content that can be broadcast in the global workspace"""
    content_id: str
    data: Dict[str, Any]
    source: str
    activation_level: float = 0.0
    support_coalition: Set[str] = field(default_factory=set)
    competition_strength: float = 0.0
    broadcast_count: int = 0
    timestamp: float = field(default_factory=time.time)
    
    def calculate_strength(self) -> float:
        """Calculate overall strength for competition"""
        coalition_strength = len(self.support_coalition) * 0.1
        time_decay = math.exp(-(time.time() - self.timestamp) * 0.01)
        return (self.activation_level + coalition_strength) * time_decay

@dataclass
class CognitiveProcessor:
    """Represents a specialized cognitive processor"""
    processor_id: str
    specialization: str
    activation_threshold: float = 0.5
    processing_capacity: float = 1.0
    current_load: float = 0.0
    interests: Set[str] = field(default_factory=set)
    active: bool = True
    
    def can_process(self, content: WorkspaceContent) -> bool:
        """Check if processor can handle this content"""
        if not self.active or self.current_load >= self.processing_capacity:
            return False
        
        # Check if content matches interests
        content_tags = set(content.data.get('tags', []))
        return bool(self.interests.intersection(content_tags)) or not self.interests

@dataclass
class BroadcastEvent:
    """Represents a global broadcast event"""
    broadcast_id: str
    content: WorkspaceContent
    timestamp: float
    recipient_processors: Set[str]
    responses: Dict[str, Any] = field(default_factory=dict)

class GlobalWorkspaceTheory(BaseConsciousness):
    """
    Implementation of Global Workspace Theory
    
    Manages the competition between different content for global broadcasting
    and facilitates communication between specialized cognitive processors.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("GlobalWorkspace", config)
        
        # Core GWT components
        self.workspace_buffer: List[WorkspaceContent] = []
        self.cognitive_processors: Dict[str, CognitiveProcessor] = {}
        self.broadcast_history: deque = deque(maxlen=100)
        
        # Competition parameters
        self.max_workspace_size = self.config.get('max_workspace_size', 5)
        self.competition_threshold = self.config.get('competition_threshold', 0.3)
        self.broadcast_interval = self.config.get('broadcast_interval', 0.5)
        
        # State tracking
        self.current_broadcast: Optional[BroadcastEvent] = None
        self.conscious_content: Optional[WorkspaceContent] = None
        self.attention_focus: Dict[str, float] = defaultdict(float)
        
        # Threading
        self.workspace_lock = threading.Lock()
        self.last_broadcast_time = 0
        
        # Statistics
        self.total_broadcasts = 0
        self.competition_events = 0
        self.processor_activations = defaultdict(int)
    
    def _initialize(self):
        """Initialize the Global Workspace Theory system"""
        # Create default cognitive processors
        default_processors = [
            CognitiveProcessor("visual", "visual_processing", 
                             interests={"visual", "image", "screen", "ui"}),
            CognitiveProcessor("linguistic", "language_processing",
                             interests={"text", "language", "speech", "nlp"}),
            CognitiveProcessor("motor", "motor_control",
                             interests={"action", "movement", "control", "automation"}),
            CognitiveProcessor("executive", "executive_control",
                             interests={"planning", "decision", "control", "strategy"}),
            CognitiveProcessor("memory", "memory_systems",
                             interests={"memory", "recall", "learning", "experience"}),
            CognitiveProcessor("emotional", "emotional_processing",
                             interests={"emotion", "mood", "feeling", "affect"}),
            CognitiveProcessor("attention", "attention_control",
                             interests={"focus", "attention", "selection", "priority"}),
            CognitiveProcessor("temporal", "temporal_processing",
                             interests={"time", "sequence", "temporal", "timing"}),
        ]
        
        for processor in default_processors:
            self.cognitive_processors[processor.processor_id] = processor
        
        self.logger.info(f"Initialized Global Workspace with {len(self.cognitive_processors)} processors")
    
    def add_processor(self, processor: CognitiveProcessor) -> None:
        """Add a new cognitive processor to the system"""
        with self.workspace_lock:
            self.cognitive_processors[processor.processor_id] = processor
        self.logger.info(f"Added processor: {processor.processor_id}")
    
    def remove_processor(self, processor_id: str) -> None:
        """Remove a cognitive processor"""
        with self.workspace_lock:
            if processor_id in self.cognitive_processors:
                del self.cognitive_processors[processor_id]
                self.logger.info(f"Removed processor: {processor_id}")
    
    def submit_content(self, content: WorkspaceContent) -> None:
        """Submit content for potential global broadcasting"""
        with self.workspace_lock:
            self.workspace_buffer.append(content)
            
            # Enforce workspace size limit
            if len(self.workspace_buffer) > self.max_workspace_size:
                # Remove weakest content
                self.workspace_buffer.sort(key=lambda c: c.calculate_strength())
                removed = self.workspace_buffer.pop(0)
                self.logger.debug(f"Removed weak content: {removed.content_id}")
        
        # Trigger competition if enough content
        if len(self.workspace_buffer) >= 2:
            self._trigger_competition()
    
    def _trigger_competition(self) -> None:
        """Trigger competition between workspace contents"""
        with self.workspace_lock:
            if not self.workspace_buffer:
                return
            
            self.competition_events += 1
            
            # Calculate competition strengths
            for content in self.workspace_buffer:
                content.competition_strength = content.calculate_strength()
                
                # Form coalitions based on similarity and support
                self._form_coalitions(content)
            
            # Find winner
            winner = max(self.workspace_buffer, key=lambda c: c.competition_strength)
            
            # Check if winner meets broadcast threshold
            if winner.competition_strength >= self.competition_threshold:
                self._initiate_broadcast(winner)
                self.workspace_buffer.remove(winner)
    
    def _form_coalitions(self, content: WorkspaceContent) -> None:
        """Form supporting coalitions for content"""
        content.support_coalition.clear()
        
        # Check which processors support this content
        for proc_id, processor in self.cognitive_processors.items():
            if processor.can_process(content):
                # Calculate support based on match and current load
                support_strength = 1.0 - processor.current_load
                if support_strength > 0.3:  # Threshold for support
                    content.support_coalition.add(proc_id)
    
    def _initiate_broadcast(self, content: WorkspaceContent) -> None:
        """Initiate global broadcast of winning content"""
        if time.time() - self.last_broadcast_time < self.broadcast_interval:
            return  # Rate limiting
        
        broadcast_id = f"broadcast_{self.total_broadcasts:06d}"
        self.total_broadcasts += 1
        self.last_broadcast_time = time.time()
        
        # Determine recipient processors
        recipients = set()
        for proc_id, processor in self.cognitive_processors.items():
            if processor.can_process(content):
                recipients.add(proc_id)
                processor.current_load = min(1.0, processor.current_load + 0.1)
                self.processor_activations[proc_id] += 1
        
        # Create broadcast event
        broadcast = BroadcastEvent(
            broadcast_id=broadcast_id,
            content=content,
            timestamp=time.time(),
            recipient_processors=recipients
        )
        
        self.current_broadcast = broadcast
        self.conscious_content = content
        self.broadcast_history.append(broadcast)
        
        # Update attention focus
        self._update_attention_focus(content)
        
        # Emit consciousness event
        consciousness_event = ConsciousnessEvent(
            event_id=f"gwt_broadcast_{broadcast_id}",
            timestamp=time.time(),
            event_type="global_broadcast",
            data={
                'content': content.data,
                'source': content.source,
                'recipients': list(recipients),
                'strength': content.competition_strength,
                'coalition': list(content.support_coalition)
            },
            priority=8,
            source_module="global_workspace",
            confidence=content.competition_strength
        )
        
        self.emit_event(consciousness_event)
        
        self.logger.info(f"Global broadcast: {content.content_id} -> {len(recipients)} processors")
    
    def _update_attention_focus(self, content: WorkspaceContent) -> None:
        """Update attention focus based on broadcasted content"""
        # Decay existing attention
        decay_factor = 0.9
        for key in self.attention_focus:
            self.attention_focus[key] *= decay_factor
        
        # Increase attention for current content tags
        content_tags = content.data.get('tags', [])
        attention_boost = content.competition_strength * 0.2
        
        for tag in content_tags:
            self.attention_focus[tag] += attention_boost
    
    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process incoming consciousness events"""
        if event.event_type == "submit_content":
            # Convert event to workspace content
            content = WorkspaceContent(
                content_id=event.event_id,
                data=event.data,
                source=event.source_module,
                activation_level=event.confidence
            )
            self.submit_content(content)
            
        elif event.event_type == "processor_response":
            # Handle processor response to broadcast
            if self.current_broadcast:
                processor_id = event.data.get('processor_id')
                response = event.data.get('response')
                if processor_id and response:
                    self.current_broadcast.responses[processor_id] = response
        
        elif event.event_type == "attention_shift":
            # Handle external attention shifts
            target = event.data.get('target')
            strength = event.data.get('strength', 0.5)
            if target:
                self.attention_focus[target] = strength
        
        return None
    
    def update(self) -> None:
        """Update the Global Workspace state"""
        current_time = time.time()
        
        # Decay processor loads
        for processor in self.cognitive_processors.values():
            processor.current_load = max(0.0, processor.current_load - 0.05)
        
        # Update metrics
        if self.conscious_content:
            self.metrics.awareness_level = self.conscious_content.competition_strength
        
        total_attention = sum(self.attention_focus.values())
        self.metrics.attention_focus = min(1.0, total_attention)
        
        # Calculate integration level based on processor involvement
        active_processors = sum(1 for p in self.cognitive_processors.values() if p.current_load > 0.1)
        self.metrics.integration_level = active_processors / len(self.cognitive_processors)
        
        # Trigger periodic competition if content is waiting
        if (len(self.workspace_buffer) > 0 and 
            current_time - self.last_broadcast_time > self.broadcast_interval * 2):
            self._trigger_competition()
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Global Workspace"""
        with self.workspace_lock:
            return {
                'workspace_buffer_size': len(self.workspace_buffer),
                'active_processors': len([p for p in self.cognitive_processors.values() if p.active]),
                'current_broadcast': self.current_broadcast.broadcast_id if self.current_broadcast else None,
                'conscious_content': self.conscious_content.content_id if self.conscious_content else None,
                'attention_focus': dict(self.attention_focus),
                'total_broadcasts': self.total_broadcasts,
                'competition_events': self.competition_events,
                'processor_activations': dict(self.processor_activations),
                'processor_loads': {pid: p.current_load for pid, p in self.cognitive_processors.items()}
            }
    
    def get_workspace_contents(self) -> List[Dict[str, Any]]:
        """Get all current workspace contents"""
        with self.workspace_lock:
            return [
                {
                    'content_id': content.content_id,
                    'source': content.source,
                    'activation_level': content.activation_level,
                    'competition_strength': content.competition_strength,
                    'coalition_size': len(content.support_coalition),
                    'age': time.time() - content.timestamp
                }
                for content in self.workspace_buffer
            ]
    
    def get_broadcast_history(self) -> List[Dict[str, Any]]:
        """Get recent broadcast history"""
        return [
            {
                'broadcast_id': broadcast.broadcast_id,
                'content_id': broadcast.content.content_id,
                'timestamp': broadcast.timestamp,
                'recipients': list(broadcast.recipient_processors),
                'responses_count': len(broadcast.responses)
            }
            for broadcast in self.broadcast_history
        ]
    
    def force_broadcast(self, content_id: str) -> bool:
        """Force broadcast of specific content (for testing/debugging)"""
        with self.workspace_lock:
            for content in self.workspace_buffer:
                if content.content_id == content_id:
                    self._initiate_broadcast(content)
                    self.workspace_buffer.remove(content)
                    return True
        return False
    
    def get_processor_status(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed status of all processors"""
        return {
            proc_id: {
                'specialization': processor.specialization,
                'activation_threshold': processor.activation_threshold,
                'processing_capacity': processor.processing_capacity,
                'current_load': processor.current_load,
                'interests': list(processor.interests),
                'active': processor.active,
                'total_activations': self.processor_activations[proc_id]
            }
            for proc_id, processor in self.cognitive_processors.items()
        }