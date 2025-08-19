"""
Multiverse Event System
======================

Event bus and messaging system for coordinating activities across
multiverse components and enabling reactive multiverse operations.
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict, deque
import json


class EventPriority(Enum):
    """Event priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class EventStatus(Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MultiverseEvent:
    """Represents an event in the multiverse system."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    source_component: str = ""
    target_component: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Processing tracking
    status: EventStatus = EventStatus.PENDING
    processing_started: Optional[float] = None
    processing_completed: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Correlation and causality
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    child_event_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'source_component': self.source_component,
            'target_component': self.target_component,
            'priority': self.priority.value,
            'timestamp': self.timestamp,
            'data': self.data,
            'metadata': self.metadata,
            'status': self.status.value,
            'processing_started': self.processing_started,
            'processing_completed': self.processing_completed,
            'retry_count': self.retry_count,
            'correlation_id': self.correlation_id,
            'parent_event_id': self.parent_event_id,
            'child_event_ids': self.child_event_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MultiverseEvent':
        """Create event from dictionary."""
        event = cls()
        for key, value in data.items():
            if key == 'priority' and isinstance(value, (int, str)):
                event.priority = EventPriority(value) if isinstance(value, int) else EventPriority[value]
            elif key == 'status' and isinstance(value, str):
                event.status = EventStatus(value)
            elif hasattr(event, key):
                setattr(event, key, value)
        return event
    
    def create_child_event(self, event_type: str, data: Any = None) -> 'MultiverseEvent':
        """Create a child event."""
        child_event = MultiverseEvent(
            event_type=event_type,
            source_component=self.source_component,
            priority=self.priority,
            data=data,
            parent_event_id=self.event_id,
            correlation_id=self.correlation_id or self.event_id
        )
        
        self.child_event_ids.append(child_event.event_id)
        return child_event
    
    def mark_processing_started(self):
        """Mark event as processing started."""
        self.status = EventStatus.PROCESSING
        self.processing_started = time.time()
    
    def mark_completed(self):
        """Mark event as completed."""
        self.status = EventStatus.COMPLETED
        self.processing_completed = time.time()
    
    def mark_failed(self):
        """Mark event as failed."""
        self.status = EventStatus.FAILED
        self.processing_completed = time.time()
    
    def get_processing_duration(self) -> Optional[float]:
        """Get event processing duration."""
        if self.processing_started and self.processing_completed:
            return self.processing_completed - self.processing_started
        return None
    
    def should_retry(self) -> bool:
        """Check if event should be retried."""
        return (self.status == EventStatus.FAILED and 
                self.retry_count < self.max_retries)


class EventHandler:
    """Base class for event handlers."""
    
    def __init__(self, handler_id: str, handler_func: Callable[[MultiverseEvent], Any]):
        """Initialize event handler."""
        self.handler_id = handler_id
        self.handler_func = handler_func
        self.registration_time = time.time()
        self.events_processed = 0
        self.processing_errors = 0
        self.total_processing_time = 0.0
        self.is_active = True
    
    async def handle_event(self, event: MultiverseEvent) -> Any:
        """Handle an event."""
        if not self.is_active:
            return None
        
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(self.handler_func):
                result = await self.handler_func(event)
            else:
                result = self.handler_func(event)
            
            self.events_processed += 1
            return result
            
        except Exception as e:
            self.processing_errors += 1
            raise e
        finally:
            processing_time = time.time() - start_time
            self.total_processing_time += processing_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            'handler_id': self.handler_id,
            'registration_time': self.registration_time,
            'events_processed': self.events_processed,
            'processing_errors': self.processing_errors,
            'total_processing_time': self.total_processing_time,
            'average_processing_time': (
                self.total_processing_time / max(1, self.events_processed)
            ),
            'error_rate': self.processing_errors / max(1, self.events_processed),
            'is_active': self.is_active
        }


class MultiverseEventBus:
    """
    Central event bus for multiverse component coordination.
    
    Provides publish-subscribe messaging, event routing, priority handling,
    and correlation tracking for multiverse operations.
    """
    
    def __init__(self, max_queue_size: int = 10000):
        """Initialize the multiverse event bus."""
        self.bus_id = str(uuid.uuid4())
        self.logger = logging.getLogger("multiverse.event_bus")
        
        # Event storage and queuing
        self.event_queue: deque = deque(maxlen=max_queue_size)
        self.event_history: Dict[str, MultiverseEvent] = {}
        self.priority_queues: Dict[EventPriority, deque] = {
            priority: deque() for priority in EventPriority
        }
        
        # Handler management
        self.handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self.global_handlers: List[EventHandler] = []
        self.handler_registry: Dict[str, EventHandler] = {}
        
        # Processing control
        self.is_running = False
        self.processing_thread: Optional[threading.Thread] = None
        self.event_lock = threading.RLock()
        
        # Statistics and monitoring
        self.total_events_processed = 0
        self.total_events_failed = 0
        self.events_by_type: Dict[str, int] = defaultdict(int)
        self.processing_latencies: deque = deque(maxlen=1000)
        
        # Correlation tracking
        self.event_correlations: Dict[str, List[str]] = defaultdict(list)
        self.event_chains: Dict[str, List[str]] = defaultdict(list)
        
        self.logger.info("MultiverseEventBus initialized: %s", self.bus_id)
    
    def start(self):
        """Start the event bus processing."""
        if self.is_running:
            self.logger.warning("Event bus already running")
            return
        
        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True,
            name="EventBusProcessor"
        )
        self.processing_thread.start()
        
        self.logger.info("Event bus started")
    
    def stop(self):
        """Stop the event bus processing."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        self.logger.info("Event bus stopped")
    
    def emit(self, event: MultiverseEvent):
        """
        Emit an event to the bus.
        
        Args:
            event: Event to emit
        """
        try:
            with self.event_lock:
                # Add to appropriate priority queue
                self.priority_queues[event.priority].append(event)
                
                # Add to main queue for history
                self.event_queue.append(event)
                
                # Store in history
                self.event_history[event.event_id] = event
                
                # Update correlation tracking
                if event.correlation_id:
                    self.event_correlations[event.correlation_id].append(event.event_id)
                
                if event.parent_event_id:
                    self.event_chains[event.parent_event_id].append(event.event_id)
                
                # Update statistics
                self.events_by_type[event.event_type] += 1
            
            self.logger.debug("Event emitted: %s (%s)", event.event_id, event.event_type)
            
        except Exception as e:
            self.logger.error("Error emitting event: %s", e)
    
    def subscribe(self, event_type: str, handler_func: Callable[[MultiverseEvent], Any],
                 handler_id: Optional[str] = None) -> str:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of events to subscribe to
            handler_func: Function to handle events
            handler_id: Optional handler ID
            
        Returns:
            Handler ID
        """
        if handler_id is None:
            handler_id = f"handler_{uuid.uuid4()}"
        
        handler = EventHandler(handler_id, handler_func)
        
        with self.event_lock:
            self.handlers[event_type].append(handler)
            self.handler_registry[handler_id] = handler
        
        self.logger.debug("Subscribed handler %s to event type %s", handler_id, event_type)
        
        return handler_id
    
    def subscribe_global(self, handler_func: Callable[[MultiverseEvent], Any],
                        handler_id: Optional[str] = None) -> str:
        """
        Subscribe to all events (global handler).
        
        Args:
            handler_func: Function to handle events
            handler_id: Optional handler ID
            
        Returns:
            Handler ID
        """
        if handler_id is None:
            handler_id = f"global_handler_{uuid.uuid4()}"
        
        handler = EventHandler(handler_id, handler_func)
        
        with self.event_lock:
            self.global_handlers.append(handler)
            self.handler_registry[handler_id] = handler
        
        self.logger.debug("Subscribed global handler: %s", handler_id)
        
        return handler_id
    
    def unsubscribe(self, handler_id: str) -> bool:
        """
        Unsubscribe a handler.
        
        Args:
            handler_id: Handler to unsubscribe
            
        Returns:
            True if successful, False otherwise
        """
        with self.event_lock:
            handler = self.handler_registry.get(handler_id)
            if not handler:
                return False
            
            # Remove from specific event type handlers
            for event_type, handlers in self.handlers.items():
                self.handlers[event_type] = [h for h in handlers if h.handler_id != handler_id]
            
            # Remove from global handlers
            self.global_handlers = [h for h in self.global_handlers if h.handler_id != handler_id]
            
            # Remove from registry
            del self.handler_registry[handler_id]
        
        self.logger.debug("Unsubscribed handler: %s", handler_id)
        
        return True
    
    def _processing_loop(self):
        """Main event processing loop."""
        while self.is_running:
            try:
                event = self._get_next_event()
                if event:
                    self._process_event(event)
                else:
                    # No events, brief sleep
                    time.sleep(0.01)
            except Exception as e:
                self.logger.error("Error in event processing loop: %s", e)
                time.sleep(0.1)
    
    def _get_next_event(self) -> Optional[MultiverseEvent]:
        """Get the next event to process based on priority."""
        with self.event_lock:
            # Process events by priority
            for priority in EventPriority:
                queue = self.priority_queues[priority]
                if queue:
                    return queue.popleft()
            
            return None
    
    def _process_event(self, event: MultiverseEvent):
        """Process a single event."""
        start_time = time.time()
        
        try:
            event.mark_processing_started()
            
            # Get handlers for this event type
            handlers = []
            
            with self.event_lock:
                # Add specific handlers
                handlers.extend(self.handlers.get(event.event_type, []))
                
                # Add global handlers
                handlers.extend(self.global_handlers)
                
                # Add target-specific handlers if specified
                if event.target_component:
                    target_handlers = self.handlers.get(f"{event.target_component}.*", [])
                    handlers.extend(target_handlers)
            
            # Process with all handlers
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler.handler_func):
                        # Run async handler in thread pool
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(handler.handle_event(event))
                        finally:
                            loop.close()
                    else:
                        handler.handle_event(event)
                        
                except Exception as e:
                    self.logger.error("Error in event handler %s: %s", handler.handler_id, e)
                    handler.processing_errors += 1
            
            event.mark_completed()
            self.total_events_processed += 1
            
        except Exception as e:
            self.logger.error("Error processing event %s: %s", event.event_id, e)
            event.mark_failed()
            self.total_events_failed += 1
            
            # Check for retry
            if event.should_retry():
                event.retry_count += 1
                event.status = EventStatus.PENDING
                with self.event_lock:
                    self.priority_queues[event.priority].append(event)
        
        finally:
            # Record processing latency
            latency = time.time() - start_time
            self.processing_latencies.append(latency)
    
    def publish_async(self, event_type: str, data: Any = None, 
                     source_component: str = "", 
                     priority: EventPriority = EventPriority.NORMAL,
                     target_component: Optional[str] = None) -> str:
        """
        Publish an event asynchronously.
        
        Args:
            event_type: Type of event
            data: Event data
            source_component: Source component name
            priority: Event priority
            target_component: Target component (optional)
            
        Returns:
            Event ID
        """
        event = MultiverseEvent(
            event_type=event_type,
            source_component=source_component,
            target_component=target_component,
            priority=priority,
            data=data
        )
        
        self.emit(event)
        return event.event_id
    
    def publish_sync(self, event_type: str, data: Any = None,
                    source_component: str = "",
                    timeout: float = 30.0) -> MultiverseEvent:
        """
        Publish an event synchronously and wait for completion.
        
        Args:
            event_type: Type of event
            data: Event data
            source_component: Source component name
            timeout: Timeout in seconds
            
        Returns:
            Completed event
        """
        event = MultiverseEvent(
            event_type=event_type,
            source_component=source_component,
            data=data
        )
        
        self.emit(event)
        
        # Wait for completion
        start_time = time.time()
        while time.time() - start_time < timeout:
            if event.status in [EventStatus.COMPLETED, EventStatus.FAILED, EventStatus.CANCELLED]:
                break
            time.sleep(0.01)
        
        return event
    
    def get_event(self, event_id: str) -> Optional[MultiverseEvent]:
        """Get an event by ID."""
        return self.event_history.get(event_id)
    
    def get_correlated_events(self, correlation_id: str) -> List[MultiverseEvent]:
        """Get all events with a specific correlation ID."""
        event_ids = self.event_correlations.get(correlation_id, [])
        return [self.event_history[eid] for eid in event_ids if eid in self.event_history]
    
    def get_event_chain(self, parent_event_id: str) -> List[MultiverseEvent]:
        """Get the chain of child events for a parent event."""
        event_ids = self.event_chains.get(parent_event_id, [])
        events = [self.event_history[eid] for eid in event_ids if eid in self.event_history]
        
        # Recursively get child chains
        all_events = events.copy()
        for event in events:
            child_chain = self.get_event_chain(event.event_id)
            all_events.extend(child_chain)
        
        return all_events
    
    def get_events_by_type(self, event_type: str, limit: Optional[int] = None) -> List[MultiverseEvent]:
        """Get events by type."""
        events = [
            event for event in self.event_history.values()
            if event.event_type == event_type
        ]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        if limit:
            events = events[:limit]
        
        return events
    
    def get_recent_events(self, limit: int = 100) -> List[MultiverseEvent]:
        """Get recent events."""
        events = list(self.event_history.values())
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def get_handler_statistics(self) -> Dict[str, Any]:
        """Get statistics for all handlers."""
        with self.event_lock:
            handler_stats = {}
            for handler_id, handler in self.handler_registry.items():
                handler_stats[handler_id] = handler.get_statistics()
            
            return handler_stats
    
    def get_bus_statistics(self) -> Dict[str, Any]:
        """Get comprehensive event bus statistics."""
        with self.event_lock:
            queue_sizes = {
                priority.name: len(queue) 
                for priority, queue in self.priority_queues.items()
            }
            
            avg_latency = (
                sum(self.processing_latencies) / len(self.processing_latencies)
                if self.processing_latencies else 0.0
            )
            
            return {
                'bus_id': self.bus_id,
                'is_running': self.is_running,
                'total_events_processed': self.total_events_processed,
                'total_events_failed': self.total_events_failed,
                'events_in_history': len(self.event_history),
                'queue_sizes': queue_sizes,
                'events_by_type': dict(self.events_by_type),
                'registered_handlers': len(self.handler_registry),
                'global_handlers': len(self.global_handlers),
                'average_processing_latency': avg_latency,
                'event_correlations': len(self.event_correlations),
                'event_chains': len(self.event_chains)
            }
    
    def clear_history(self, keep_recent: int = 1000):
        """Clear event history, keeping only recent events."""
        with self.event_lock:
            if len(self.event_history) <= keep_recent:
                return
            
            # Sort events by timestamp
            events = list(self.event_history.values())
            events.sort(key=lambda e: e.timestamp, reverse=True)
            
            # Keep only recent events
            recent_events = events[:keep_recent]
            recent_event_ids = {e.event_id for e in recent_events}
            
            # Clear old events
            self.event_history = {
                eid: event for eid, event in self.event_history.items()
                if eid in recent_event_ids
            }
            
            # Clean up correlations and chains
            self.event_correlations = {
                cid: [eid for eid in event_ids if eid in recent_event_ids]
                for cid, event_ids in self.event_correlations.items()
            }
            self.event_correlations = {
                cid: event_ids for cid, event_ids in self.event_correlations.items()
                if event_ids
            }
            
            self.event_chains = {
                pid: [eid for eid in event_ids if eid in recent_event_ids]
                for pid, event_ids in self.event_chains.items()
            }
            self.event_chains = {
                pid: event_ids for pid, event_ids in self.event_chains.items()
                if event_ids
            }
            
            self.logger.info("Event history cleared, kept %d recent events", keep_recent)
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Global event bus instance
_global_event_bus: Optional[MultiverseEventBus] = None


def get_global_event_bus() -> MultiverseEventBus:
    """Get the global multiverse event bus."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = MultiverseEventBus()
        _global_event_bus.start()
    return _global_event_bus


def set_global_event_bus(event_bus: MultiverseEventBus):
    """Set the global multiverse event bus."""
    global _global_event_bus
    if _global_event_bus and _global_event_bus.is_running:
        _global_event_bus.stop()
    _global_event_bus = event_bus