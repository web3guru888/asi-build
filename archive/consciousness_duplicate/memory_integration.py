"""
Memory Integration System

This module integrates various memory systems with consciousness, managing
episodic, semantic, procedural, and working memory in conscious experience.

Key components:
- Memory consolidation
- Conscious memory access
- Memory-consciousness binding
- Autobiographical memory
- Memory reconsolidation
- Consciousness-dependent memory formation
"""

import time
import threading
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import numpy as np

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState

class MemoryType(Enum):
    """Types of memory systems"""
    WORKING = "working"
    EPISODIC = "episodic" 
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    AUTOBIOGRAPHICAL = "autobiographical"
    EMOTIONAL = "emotional"
    SENSORY = "sensory"

class ConsolidationState(Enum):
    """States of memory consolidation"""
    INITIAL = "initial"
    CONSOLIDATING = "consolidating"
    CONSOLIDATED = "consolidated"
    RECONSOLIDATING = "reconsolidating"

@dataclass
class MemoryTrace:
    """Represents a memory trace in the system"""
    memory_id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    strength: float
    consciousness_level: float
    consolidation_state: ConsolidationState
    formation_time: float
    last_accessed: float
    access_count: int = 0
    associated_consciousness_events: List[str] = field(default_factory=list)
    
    def decay_strength(self, decay_rate: float = 0.99) -> None:
        """Apply decay to memory strength"""
        self.strength *= decay_rate

@dataclass
class MemoryCluster:
    """Cluster of related memories"""
    cluster_id: str
    memory_ids: Set[str]
    cluster_theme: str
    coherence_score: float
    last_updated: float
    
class MemoryIntegration(BaseConsciousness):
    """
    Memory Integration with Consciousness
    
    Manages the integration of various memory systems with conscious processes,
    including consolidation, retrieval, and consciousness-dependent encoding.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("MemoryIntegration", config)
        
        # Memory stores
        self.memory_traces: Dict[str, MemoryTrace] = {}
        self.memory_clusters: Dict[str, MemoryCluster] = {}
        self.working_memory: Dict[str, Any] = {}
        
        # Memory by type
        self.memory_by_type: Dict[MemoryType, Set[str]] = defaultdict(set)
        
        # Consolidation system
        self.consolidation_queue: deque = deque()
        self.consolidation_threshold = self.config.get('consolidation_threshold', 0.7)
        
        # Conscious memory access
        self.conscious_memory_buffer: Dict[str, MemoryTrace] = {}
        self.consciousness_memory_links: Dict[str, List[str]] = defaultdict(list)
        
        # Parameters
        self.working_memory_capacity = self.config.get('working_memory_capacity', 7)
        self.consolidation_rate = self.config.get('consolidation_rate', 0.1)
        self.decay_rate = self.config.get('decay_rate', 0.995)
        
        # Statistics
        self.total_memories_formed = 0
        self.consolidations_performed = 0
        self.memory_retrievals = 0
        
        # Threading
        self.memory_lock = threading.Lock()
    
    def form_memory(self, content: Dict[str, Any], memory_type: MemoryType,
                   consciousness_level: float = 0.5) -> MemoryTrace:
        """Form a new memory trace"""
        memory_id = f"memory_{self.total_memories_formed:06d}"
        self.total_memories_formed += 1
        
        memory_trace = MemoryTrace(
            memory_id=memory_id,
            memory_type=memory_type,
            content=content,
            strength=consciousness_level,  # Initial strength based on consciousness
            consciousness_level=consciousness_level,
            consolidation_state=ConsolidationState.INITIAL,
            formation_time=time.time(),
            last_accessed=time.time()
        )
        
        with self.memory_lock:
            self.memory_traces[memory_id] = memory_trace
            self.memory_by_type[memory_type].add(memory_id)
            
            # Add to consolidation queue if strong enough
            if consciousness_level > self.consolidation_threshold:
                self.consolidation_queue.append(memory_id)
        
        self.logger.debug(f"Formed {memory_type.value} memory: {memory_id}")
        return memory_trace
    
    def retrieve_memory(self, query: Dict[str, Any], 
                       memory_types: Optional[List[MemoryType]] = None) -> List[MemoryTrace]:
        """Retrieve memories based on query"""
        if memory_types is None:
            memory_types = list(MemoryType)
        
        self.memory_retrievals += 1
        retrieved_memories = []
        
        # Search through relevant memory types
        for memory_type in memory_types:
            memory_ids = self.memory_by_type[memory_type]
            
            for memory_id in memory_ids:
                if memory_id in self.memory_traces:
                    memory = self.memory_traces[memory_id]
                    
                    # Calculate relevance score
                    relevance = self._calculate_memory_relevance(memory, query)
                    
                    if relevance > 0.3:  # Relevance threshold
                        # Update access information
                        memory.last_accessed = time.time()
                        memory.access_count += 1
                        
                        # Strengthen memory based on retrieval
                        memory.strength = min(1.0, memory.strength + 0.05)
                        
                        retrieved_memories.append((memory, relevance))
        
        # Sort by relevance and return top matches
        retrieved_memories.sort(key=lambda x: x[1], reverse=True)
        
        results = [memory for memory, relevance in retrieved_memories[:10]]
        
        # Add to conscious memory buffer if highly relevant
        for memory in results[:3]:
            self.conscious_memory_buffer[memory.memory_id] = memory
        
        return results
    
    def _calculate_memory_relevance(self, memory: MemoryTrace, query: Dict[str, Any]) -> float:
        """Calculate how relevant a memory is to a query"""
        relevance = 0.0
        
        # Content similarity
        content_match = 0.0
        query_keywords = set()
        memory_keywords = set()
        
        # Extract keywords from query
        for key, value in query.items():
            if isinstance(value, str):
                query_keywords.update(value.lower().split())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        query_keywords.update(item.lower().split())
        
        # Extract keywords from memory content
        for key, value in memory.content.items():
            if isinstance(value, str):
                memory_keywords.update(value.lower().split())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        memory_keywords.update(item.lower().split())
        
        # Calculate keyword overlap
        if query_keywords and memory_keywords:
            overlap = len(query_keywords.intersection(memory_keywords))
            total_keywords = len(query_keywords.union(memory_keywords))
            content_match = overlap / total_keywords if total_keywords > 0 else 0.0
        
        relevance += content_match * 0.6
        
        # Recency bonus
        time_diff = time.time() - memory.formation_time
        recency_factor = max(0.0, 1.0 - time_diff / 86400)  # Decay over 24 hours
        relevance += recency_factor * 0.2
        
        # Strength bonus
        relevance += memory.strength * 0.2
        
        return min(1.0, relevance)
    
    def consolidate_memories(self) -> List[str]:
        """Perform memory consolidation"""
        consolidated_memories = []
        
        while self.consolidation_queue and len(consolidated_memories) < 5:
            memory_id = self.consolidation_queue.popleft()
            
            if memory_id in self.memory_traces:
                memory = self.memory_traces[memory_id]
                
                if memory.consolidation_state == ConsolidationState.INITIAL:
                    # Perform consolidation
                    success = self._perform_consolidation(memory)
                    
                    if success:
                        memory.consolidation_state = ConsolidationState.CONSOLIDATED
                        memory.strength = min(1.0, memory.strength + 0.1)
                        consolidated_memories.append(memory_id)
                        self.consolidations_performed += 1
                        
                        # Look for clustering opportunities
                        self._attempt_memory_clustering(memory)
        
        return consolidated_memories
    
    def _perform_consolidation(self, memory: MemoryTrace) -> bool:
        """Perform the actual consolidation process"""
        # Simulate consolidation by strengthening related patterns
        
        # Find related memories
        related_memories = self._find_related_memories(memory)
        
        # Strengthen associations
        for related_id in related_memories:
            if related_id in self.memory_traces:
                related_memory = self.memory_traces[related_id]
                related_memory.strength = min(1.0, related_memory.strength + 0.02)
        
        # Mark as consolidating
        memory.consolidation_state = ConsolidationState.CONSOLIDATING
        
        return True
    
    def _find_related_memories(self, target_memory: MemoryTrace) -> List[str]:
        """Find memories related to the target memory"""
        related_memories = []
        
        # Look for memories of same type formed around same time
        time_window = 3600  # 1 hour
        
        for memory_id, memory in self.memory_traces.items():
            if (memory_id != target_memory.memory_id and
                memory.memory_type == target_memory.memory_type and
                abs(memory.formation_time - target_memory.formation_time) < time_window):
                
                # Check content similarity
                similarity = self._calculate_content_similarity(target_memory.content, memory.content)
                if similarity > 0.3:
                    related_memories.append(memory_id)
        
        return related_memories[:5]  # Limit to 5 related memories
    
    def _calculate_content_similarity(self, content1: Dict[str, Any], content2: Dict[str, Any]) -> float:
        """Calculate similarity between two memory contents"""
        similarity = 0.0
        
        # Simple keyword-based similarity
        keywords1 = set()
        keywords2 = set()
        
        for value in content1.values():
            if isinstance(value, str):
                keywords1.update(value.lower().split())
        
        for value in content2.values():
            if isinstance(value, str):
                keywords2.update(value.lower().split())
        
        if keywords1 and keywords2:
            overlap = len(keywords1.intersection(keywords2))
            total = len(keywords1.union(keywords2))
            similarity = overlap / total if total > 0 else 0.0
        
        return similarity
    
    def _attempt_memory_clustering(self, memory: MemoryTrace) -> None:
        """Attempt to cluster memory with related memories"""
        related_memories = self._find_related_memories(memory)
        
        if len(related_memories) >= 2:
            # Create or update cluster
            cluster_theme = self._extract_cluster_theme(memory, related_memories)
            
            # Check if memory belongs to existing cluster
            existing_cluster = None
            for cluster in self.memory_clusters.values():
                if memory.memory_id in cluster.memory_ids:
                    existing_cluster = cluster
                    break
            
            if existing_cluster:
                # Update existing cluster
                existing_cluster.memory_ids.update(related_memories)
                existing_cluster.last_updated = time.time()
            else:
                # Create new cluster
                cluster_id = f"cluster_{len(self.memory_clusters):06d}"
                cluster = MemoryCluster(
                    cluster_id=cluster_id,
                    memory_ids={memory.memory_id}.union(related_memories),
                    cluster_theme=cluster_theme,
                    coherence_score=0.7,
                    last_updated=time.time()
                )
                self.memory_clusters[cluster_id] = cluster
    
    def _extract_cluster_theme(self, central_memory: MemoryTrace, related_memory_ids: List[str]) -> str:
        """Extract a theme for a memory cluster"""
        all_keywords = set()
        
        # Extract keywords from central memory
        for value in central_memory.content.values():
            if isinstance(value, str):
                all_keywords.update(value.lower().split())
        
        # Extract keywords from related memories
        for memory_id in related_memory_ids:
            if memory_id in self.memory_traces:
                memory = self.memory_traces[memory_id]
                for value in memory.content.values():
                    if isinstance(value, str):
                        all_keywords.update(value.lower().split())
        
        # Simple theme extraction (most common keywords)
        if all_keywords:
            return f"Theme: {', '.join(list(all_keywords)[:3])}"
        else:
            return "Mixed theme"
    
    def bind_consciousness_to_memory(self, consciousness_event_id: str, memory_id: str) -> None:
        """Create binding between consciousness event and memory"""
        if memory_id in self.memory_traces:
            memory = self.memory_traces[memory_id]
            memory.associated_consciousness_events.append(consciousness_event_id)
            
            # Strengthen memory based on consciousness binding
            memory.consciousness_level = min(1.0, memory.consciousness_level + 0.1)
            memory.strength = min(1.0, memory.strength + 0.05)
            
            # Add to consciousness-memory links
            self.consciousness_memory_links[consciousness_event_id].append(memory_id)
    
    def update_working_memory(self, item_id: str, content: Any) -> None:
        """Update working memory with new content"""
        self.working_memory[item_id] = {
            'content': content,
            'timestamp': time.time(),
            'access_count': 1
        }
        
        # Enforce capacity limit
        if len(self.working_memory) > self.working_memory_capacity:
            # Remove oldest item
            oldest_item = min(self.working_memory.items(), 
                            key=lambda x: x[1]['timestamp'])
            del self.working_memory[oldest_item[0]]
    
    def reconsolidate_memory(self, memory_id: str, new_context: Dict[str, Any]) -> bool:
        """Reconsolidate a memory with new context"""
        if memory_id not in self.memory_traces:
            return False
        
        memory = self.memory_traces[memory_id]
        
        # Mark as reconsolidating
        memory.consolidation_state = ConsolidationState.RECONSOLIDATING
        
        # Update content with new context
        memory.content.update(new_context)
        memory.last_accessed = time.time()
        
        # Reset consolidation to allow re-consolidation
        memory.consolidation_state = ConsolidationState.INITIAL
        self.consolidation_queue.append(memory_id)
        
        return True
    
    def get_autobiographical_timeline(self) -> List[Dict[str, Any]]:
        """Get chronological timeline of autobiographical memories"""
        autobiographical_memories = [
            self.memory_traces[mid] for mid in self.memory_by_type[MemoryType.AUTOBIOGRAPHICAL]
            if mid in self.memory_traces
        ]
        
        # Sort by formation time
        autobiographical_memories.sort(key=lambda m: m.formation_time)
        
        timeline = []
        for memory in autobiographical_memories:
            timeline.append({
                'memory_id': memory.memory_id,
                'timestamp': memory.formation_time,
                'content_summary': str(memory.content)[:100] + "..." if len(str(memory.content)) > 100 else str(memory.content),
                'strength': memory.strength,
                'consciousness_level': memory.consciousness_level
            })
        
        return timeline
    
    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "memory_formation_request":
            content = event.data.get('content', {})
            memory_type_str = event.data.get('memory_type', 'episodic')
            consciousness_level = event.data.get('consciousness_level', 0.5)
            
            try:
                memory_type = MemoryType(memory_type_str)
                memory = self.form_memory(content, memory_type, consciousness_level)
                
                # Bind to consciousness event
                self.bind_consciousness_to_memory(event.event_id, memory.memory_id)
                
                return ConsciousnessEvent(
                    event_id=f"memory_formed_{memory.memory_id}",
                    timestamp=time.time(),
                    event_type="memory_formed",
                    data={
                        'memory_id': memory.memory_id,
                        'memory_type': memory_type.value,
                        'consciousness_level': consciousness_level
                    },
                    source_module="memory_integration"
                )
            except ValueError:
                self.logger.error(f"Invalid memory type: {memory_type_str}")
        
        elif event.event_type == "memory_retrieval_request":
            query = event.data.get('query', {})
            memory_types_str = event.data.get('memory_types', [])
            
            memory_types = []
            for mt_str in memory_types_str:
                try:
                    memory_types.append(MemoryType(mt_str))
                except ValueError:
                    continue
            
            retrieved_memories = self.retrieve_memory(query, memory_types if memory_types else None)
            
            return ConsciousnessEvent(
                event_id=f"memories_retrieved_{len(retrieved_memories)}",
                timestamp=time.time(),
                event_type="memories_retrieved",
                data={
                    'retrieved_count': len(retrieved_memories),
                    'memory_summaries': [
                        {
                            'memory_id': mem.memory_id,
                            'memory_type': mem.memory_type.value,
                            'strength': mem.strength,
                            'content_preview': str(mem.content)[:50] + "..."
                        }
                        for mem in retrieved_memories[:5]  # Top 5
                    ]
                },
                source_module="memory_integration"
            )
        
        return None
    
    def update(self) -> None:
        """Update the Memory Integration system"""
        # Apply memory decay
        for memory in self.memory_traces.values():
            memory.decay_strength(self.decay_rate)
        
        # Perform consolidation
        if self.consolidation_queue:
            self.consolidate_memories()
        
        # Clean up very weak memories
        weak_memories = [
            mid for mid, memory in self.memory_traces.items()
            if memory.strength < 0.01
        ]
        
        for mid in weak_memories:
            memory = self.memory_traces.pop(mid)
            self.memory_by_type[memory.memory_type].discard(mid)
        
        # Update consciousness metrics
        total_memories = len(self.memory_traces)
        conscious_memories = len([m for m in self.memory_traces.values() if m.consciousness_level > 0.5])
        
        if total_memories > 0:
            self.metrics.awareness_level = conscious_memories / total_memories
        
        # Clear old items from conscious memory buffer
        current_time = time.time()
        old_items = [
            mid for mid, memory in self.conscious_memory_buffer.items()
            if current_time - memory.last_accessed > 300  # 5 minutes
        ]
        for mid in old_items:
            del self.conscious_memory_buffer[mid]
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Memory Integration system"""
        memory_stats_by_type = {}
        for memory_type in MemoryType:
            count = len(self.memory_by_type[memory_type])
            avg_strength = 0.0
            if count > 0:
                memories = [self.memory_traces[mid] for mid in self.memory_by_type[memory_type] 
                          if mid in self.memory_traces]
                avg_strength = sum(m.strength for m in memories) / len(memories)
            
            memory_stats_by_type[memory_type.value] = {
                'count': count,
                'average_strength': avg_strength
            }
        
        return {
            'total_memories': len(self.memory_traces),
            'memory_by_type': memory_stats_by_type,
            'memory_clusters': len(self.memory_clusters),
            'working_memory_items': len(self.working_memory),
            'conscious_memory_buffer_size': len(self.conscious_memory_buffer),
            'consolidation_queue_size': len(self.consolidation_queue),
            'total_memories_formed': self.total_memories_formed,
            'consolidations_performed': self.consolidations_performed,
            'memory_retrievals': self.memory_retrievals,
            'consciousness_memory_links': len(self.consciousness_memory_links)
        }