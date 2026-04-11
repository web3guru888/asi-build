"""
Event-Driven Processing System for Neuromorphic Computing

Provides efficient event-based computation that mimics the asynchronous,
event-driven nature of biological neural systems. Events are processed
only when they occur, leading to significant computational savings.
"""

import time
import heapq
import threading
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import numpy as np
from enum import Enum
import logging

class EventType(Enum):
    """Types of neuromorphic events."""
    SPIKE = "spike"
    SYNAPTIC = "synaptic"
    PLASTICITY = "plasticity"
    ADAPTATION = "adaptation"
    HOMEOSTASIS = "homeostasis"
    REWARD = "reward"
    ATTENTION = "attention"
    OSCILLATION = "oscillation"
    EXTERNAL = "external"

@dataclass
class Event:
    """Base event class for neuromorphic systems."""
    event_id: str
    event_type: EventType
    timestamp: float
    source_id: int
    target_id: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher values = higher priority
    
    def __lt__(self, other):
        """For heap ordering by timestamp and priority."""
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        return self.priority > other.priority  # Higher priority first

@dataclass
class SpikeEvent(Event):
    """Spike event with neuronal firing information."""
    def __init__(self, neuron_id: int, timestamp: float, amplitude: float = 1.0, **kwargs):
        super().__init__(
            event_id=f"spike_{neuron_id}_{timestamp:.6f}",
            event_type=EventType.SPIKE,
            timestamp=timestamp,
            source_id=neuron_id,
            data={'amplitude': amplitude, **kwargs}
        )

@dataclass
class SynapticEvent(Event):
    """Synaptic transmission event."""
    def __init__(self, pre_neuron: int, post_neuron: int, timestamp: float, 
                 weight: float, delay: float, **kwargs):
        super().__init__(
            event_id=f"synapse_{pre_neuron}_{post_neuron}_{timestamp:.6f}",
            event_type=EventType.SYNAPTIC,
            timestamp=timestamp + delay,
            source_id=pre_neuron,
            target_id=post_neuron,
            data={'weight': weight, 'delay': delay, **kwargs}
        )

@dataclass
class PlasticityEvent(Event):
    """Synaptic plasticity update event."""
    def __init__(self, synapse_id: int, timestamp: float, weight_change: float, **kwargs):
        super().__init__(
            event_id=f"plasticity_{synapse_id}_{timestamp:.6f}",
            event_type=EventType.PLASTICITY,
            timestamp=timestamp,
            source_id=synapse_id,
            data={'weight_change': weight_change, **kwargs}
        )

class EventHandler(ABC):
    """Abstract base class for event handlers."""
    
    @abstractmethod
    def handle_event(self, event: Event) -> List[Event]:
        """Handle an event and return any generated events."""
        pass
    
    @abstractmethod
    def get_supported_events(self) -> List[EventType]:
        """Return list of supported event types."""
        pass

class EventQueue:
    """Thread-safe priority queue for neuromorphic events."""
    
    def __init__(self, max_size: int = 100000):
        """Initialize event queue."""
        self._heap = []
        self._max_size = max_size
        self._lock = threading.Lock()
        self._event_count = 0
        self._dropped_events = 0
        
    def push(self, event: Event) -> bool:
        """Add event to queue."""
        with self._lock:
            if len(self._heap) >= self._max_size:
                # Drop oldest event if queue is full
                if self._heap:
                    heapq.heappop(self._heap)
                    self._dropped_events += 1
            
            heapq.heappush(self._heap, event)
            self._event_count += 1
            return True
    
    def pop(self) -> Optional[Event]:
        """Remove and return next event."""
        with self._lock:
            if self._heap:
                return heapq.heappop(self._heap)
            return None
    
    def peek(self) -> Optional[Event]:
        """Peek at next event without removing it."""
        with self._lock:
            if self._heap:
                return self._heap[0]
            return None
    
    def size(self) -> int:
        """Get current queue size."""
        with self._lock:
            return len(self._heap)
    
    def clear(self) -> None:
        """Clear all events from queue."""
        with self._lock:
            self._heap.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        with self._lock:
            return {
                'current_size': len(self._heap),
                'max_size': self._max_size,
                'total_events': self._event_count,
                'dropped_events': self._dropped_events
            }

class EventProcessor:
    """
    Central event processing engine for neuromorphic computing.
    
    Features:
    - Asynchronous event processing
    - Priority-based event scheduling
    - Event filtering and routing
    - Performance monitoring
    - Temporal synchronization
    - Event compression and batching
    """
    
    def __init__(self, config):
        """Initialize event processor."""
        self.config = config
        
        # Event queues
        self.event_queue = EventQueue(max_size=100000)
        self.priority_queue = EventQueue(max_size=10000)
        
        # Event handlers
        self.handlers = defaultdict(list)
        self.global_handlers = []
        
        # Event filtering
        self.event_filters = []
        self.blocked_events = set()
        
        # Performance monitoring
        self.events_processed = 0
        self.events_generated = 0
        self.processing_times = deque(maxlen=1000)
        self.event_latencies = deque(maxlen=1000)
        
        # Temporal management
        self.current_time = 0.0
        self.time_window = 1.0e-3  # 1ms processing window
        self.lookahead_time = 10.0e-3  # 10ms lookahead
        
        # Event compression
        self.compression_enabled = True
        self.compression_window = 1.0e-4  # 0.1ms
        self.compressed_events = {}
        
        # Threading
        self.processing_thread = None
        self.stop_event = threading.Event()
        self.paused = False
        
        # Callbacks
        self.event_callbacks = defaultdict(list)
        self.performance_callbacks = []
        
        # Logging
        self.logger = logging.getLogger("neuromorphic.event_processor")
        
        # Statistics
        self.event_type_counts = defaultdict(int)
        self.handler_execution_times = defaultdict(list)
    
    def initialize(self) -> None:
        """Initialize the event processor."""
        self.logger.info("Initializing event processor")
        
        # Reset state
        self.current_time = 0.0
        self.events_processed = 0
        self.events_generated = 0
        
        # Clear queues
        self.event_queue.clear()
        self.priority_queue.clear()
        
        # Start processing thread
        self.start_processing()
        
        self.logger.info("Event processor initialized")
    
    def shutdown(self) -> None:
        """Shutdown the event processor."""
        self.logger.info("Shutting down event processor")
        
        # Stop processing
        self.stop_processing()
        
        # Clear data structures
        self.handlers.clear()
        self.global_handlers.clear()
        self.event_filters.clear()
        
        self.logger.info("Event processor shutdown complete")
    
    def register_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """Register an event handler for specific event type."""
        self.handlers[event_type].append(handler)
        self.logger.debug(f"Registered handler for {event_type}")
    
    def register_global_handler(self, handler: EventHandler) -> None:
        """Register a global event handler for all events."""
        self.global_handlers.append(handler)
        self.logger.debug("Registered global handler")
    
    def submit_event(self, event: Event, high_priority: bool = False) -> bool:
        """Submit event for processing."""
        # Apply filters
        if not self._should_process_event(event):
            return False
        
        # Apply compression if enabled
        if self.compression_enabled and self._can_compress_event(event):
            self._compress_event(event)
            return True
        
        # Add to appropriate queue
        queue = self.priority_queue if high_priority else self.event_queue
        success = queue.push(event)
        
        if success:
            self.events_generated += 1
            self.event_type_counts[event.event_type] += 1
        
        return success
    
    def process_events(self, time_step: float) -> int:
        """Process events for one time step."""
        start_time = time.perf_counter()
        events_processed = 0
        
        # Update current time
        self.current_time += time_step
        target_time = self.current_time
        
        # Process high priority events first
        events_processed += self._process_queue(self.priority_queue, target_time)
        
        # Process regular events
        events_processed += self._process_queue(self.event_queue, target_time)
        
        # Process compressed events
        events_processed += self._process_compressed_events(target_time)
        
        # Update statistics
        processing_time = time.perf_counter() - start_time
        self.processing_times.append(processing_time)
        self.events_processed += events_processed
        
        return events_processed
    
    def start_processing(self) -> None:
        """Start asynchronous event processing."""
        if self.processing_thread and self.processing_thread.is_alive():
            return
        
        self.stop_event.clear()
        self.processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True
        )
        self.processing_thread.start()
        self.logger.debug("Started event processing thread")
    
    def stop_processing(self) -> None:
        """Stop asynchronous event processing."""
        if self.processing_thread and self.processing_thread.is_alive():
            self.stop_event.set()
            self.processing_thread.join(timeout=5.0)
            
            if self.processing_thread.is_alive():
                self.logger.warning("Processing thread did not stop gracefully")
        
        self.logger.debug("Stopped event processing thread")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processor statistics."""
        avg_processing_time = (
            np.mean(self.processing_times) if self.processing_times else 0.0
        )
        
        avg_latency = (
            np.mean(self.event_latencies) if self.event_latencies else 0.0
        )
        
        return {
            'events_processed': self.events_processed,
            'events_generated': self.events_generated,
            'current_time': self.current_time,
            'queue_size': self.event_queue.size(),
            'priority_queue_size': self.priority_queue.size(),
            'avg_processing_time': avg_processing_time,
            'avg_event_latency': avg_latency,
            'event_type_counts': dict(self.event_type_counts),
            'compression_enabled': self.compression_enabled,
            'compressed_events': len(self.compressed_events)
        }
    
    def _should_process_event(self, event: Event) -> bool:
        """Check if event should be processed."""
        # Check if event type is blocked
        if event.event_type in self.blocked_events:
            return False
        
        # Apply custom filters
        for filter_func in self.event_filters:
            try:
                if not filter_func(event):
                    return False
            except Exception as e:
                self.logger.warning(f"Event filter failed: {e}")
        
        return True
    
    def _can_compress_event(self, event: Event) -> bool:
        """Check if event can be compressed."""
        # Only compress certain event types
        compressible_types = {EventType.SPIKE, EventType.SYNAPTIC}
        return event.event_type in compressible_types
    
    def _compress_event(self, event: Event) -> None:
        """Compress event with similar events in time window."""
        # Create compression key based on event type and source
        key = (event.event_type, event.source_id, event.target_id)
        
        if key not in self.compressed_events:
            self.compressed_events[key] = []
        
        # Add event to compression buffer
        self.compressed_events[key].append(event)
    
    def _process_compressed_events(self, target_time: float) -> int:
        """Process compressed events that are ready."""
        events_processed = 0
        keys_to_remove = []
        
        for key, events in self.compressed_events.items():
            if not events:
                keys_to_remove.append(key)
                continue
            
            # Check if any events are ready for processing
            ready_events = [e for e in events if e.timestamp <= target_time]
            
            if ready_events:
                # Create compressed event
                compressed_event = self._create_compressed_event(ready_events)
                
                # Process compressed event
                if compressed_event:
                    self._process_single_event(compressed_event)
                    events_processed += 1
                
                # Remove processed events
                for event in ready_events:
                    events.remove(event)
        
        # Clean up empty entries
        for key in keys_to_remove:
            del self.compressed_events[key]
        
        return events_processed
    
    def _create_compressed_event(self, events: List[Event]) -> Optional[Event]:
        """Create a single compressed event from multiple events."""
        if not events:
            return None
        
        # Use first event as template
        template = events[0]
        
        # Aggregate event data
        if template.event_type == EventType.SPIKE:
            # For spikes, sum amplitudes
            total_amplitude = sum(e.data.get('amplitude', 1.0) for e in events)
            compressed_data = {'amplitude': total_amplitude, 'count': len(events)}
        else:
            # For other events, average relevant values
            compressed_data = template.data.copy()
            compressed_data['count'] = len(events)
        
        # Create compressed event
        compressed_event = Event(
            event_id=f"compressed_{template.event_type}_{template.source_id}_{template.timestamp:.6f}",
            event_type=template.event_type,
            timestamp=template.timestamp,
            source_id=template.source_id,
            target_id=template.target_id,
            data=compressed_data,
            priority=template.priority
        )
        
        return compressed_event
    
    def _process_queue(self, queue: EventQueue, target_time: float) -> int:
        """Process events from a queue up to target time."""
        events_processed = 0
        
        while True:
            event = queue.peek()
            
            if not event or event.timestamp > target_time:
                break
            
            # Remove event from queue
            queue.pop()
            
            # Process event
            self._process_single_event(event)
            events_processed += 1
        
        return events_processed
    
    def _process_single_event(self, event: Event) -> None:
        """Process a single event."""
        start_time = time.perf_counter()
        
        try:
            # Calculate event latency
            latency = self.current_time - event.timestamp
            self.event_latencies.append(latency)
            
            # Call event callbacks
            for callback in self.event_callbacks[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.warning(f"Event callback failed: {e}")
            
            # Process with registered handlers
            generated_events = []
            
            # Global handlers
            for handler in self.global_handlers:
                try:
                    new_events = handler.handle_event(event)
                    if new_events:
                        generated_events.extend(new_events)
                except Exception as e:
                    self.logger.warning(f"Global handler failed: {e}")
            
            # Type-specific handlers
            for handler in self.handlers[event.event_type]:
                try:
                    new_events = handler.handle_event(event)
                    if new_events:
                        generated_events.extend(new_events)
                except Exception as e:
                    self.logger.warning(f"Event handler failed: {e}")
            
            # Submit generated events
            for new_event in generated_events:
                self.submit_event(new_event)
            
        except Exception as e:
            self.logger.error(f"Failed to process event {event.event_id}: {e}")
    
    def _processing_loop(self) -> None:
        """Asynchronous processing loop."""
        while not self.stop_event.is_set():
            try:
                if not self.paused:
                    # Process events for current time window
                    self.process_events(self.time_window)
                
                # Short sleep to prevent busy waiting
                time.sleep(0.001)  # 1ms
                
            except Exception as e:
                self.logger.error(f"Processing loop error: {e}")