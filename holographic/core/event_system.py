"""
Event system for holographic components communication
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import weakref
from concurrent.futures import ThreadPoolExecutor
import json

logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """Event priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

@dataclass
class HolographicEvent:
    """Holographic system event"""
    name: str
    data: Dict[str, Any]
    timestamp: float
    priority: EventPriority = EventPriority.NORMAL
    source: Optional[str] = None
    target: Optional[str] = None
    event_id: Optional[str] = None
    
    def __post_init__(self):
        if self.event_id is None:
            self.event_id = f"{self.name}_{int(time.time() * 1000000)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "name": self.name,
            "data": self.data,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "source": self.source,
            "target": self.target,
            "event_id": self.event_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HolographicEvent':
        """Create event from dictionary"""
        return cls(
            name=data["name"],
            data=data["data"],
            timestamp=data["timestamp"],
            priority=EventPriority(data["priority"]),
            source=data.get("source"),
            target=data.get("target"),
            event_id=data.get("event_id")
        )

class EventSubscriber:
    """Event subscriber wrapper"""
    
    def __init__(self, callback: Callable, event_name: str, 
                 priority: EventPriority = EventPriority.NORMAL,
                 weak_ref: bool = False):
        self.event_name = event_name
        self.priority = priority
        self.weak_ref = weak_ref
        self.subscription_time = time.time()
        
        if weak_ref:
            # Use weak reference for automatic cleanup
            self._callback_ref = weakref.ref(callback)
        else:
            self._callback_ref = callback
    
    @property
    def callback(self):
        """Get the callback function"""
        if self.weak_ref:
            callback = self._callback_ref()
            if callback is None:
                raise ReferenceError("Weak reference callback was garbage collected")
            return callback
        return self._callback_ref
    
    def is_valid(self) -> bool:
        """Check if subscriber is still valid"""
        if self.weak_ref:
            return self._callback_ref() is not None
        return True

class HolographicEventSystem:
    """
    Comprehensive event system for holographic components
    Supports async/sync events, priorities, filtering, and network distribution
    """
    
    def __init__(self, max_workers: int = 4):
        self.subscribers: Dict[str, List[EventSubscriber]] = {}
        self.event_history: List[HolographicEvent] = []
        self.max_history_size = 1000
        self.running = False
        self.initialized = False
        
        # Threading
        self._lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Event queue for async processing
        self.event_queue = asyncio.Queue()
        self.processing_task = None
        
        # Event filters
        self.global_filters: List[Callable[[HolographicEvent], bool]] = []
        
        # Statistics
        self.stats = {
            "events_emitted": 0,
            "events_processed": 0,
            "events_filtered": 0,
            "subscribers_count": 0
        }
        
        # Network distribution (optional)
        self.network_enabled = False
        self.network_subscribers: Set[str] = set()
        
        logger.info("HolographicEventSystem initialized")
    
    async def initialize(self) -> bool:
        """Initialize the event system"""
        try:
            if self.initialized:
                return True
            
            self.running = True
            self.processing_task = asyncio.create_task(self._process_events())
            
            # Register default system events
            await self._register_system_events()
            
            self.initialized = True
            logger.info("HolographicEventSystem initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize event system: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the event system"""
        logger.info("Shutting down HolographicEventSystem...")
        
        self.running = False
        
        # Cancel processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Clear subscribers
        with self._lock:
            self.subscribers.clear()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        self.initialized = False
        logger.info("HolographicEventSystem shutdown complete")
    
    def subscribe(self, event_name: str, callback: Callable,
                 priority: EventPriority = EventPriority.NORMAL,
                 weak_ref: bool = False) -> str:
        """
        Subscribe to an event
        
        Args:
            event_name: Name of the event to subscribe to (supports wildcards)
            callback: Callback function (async or sync)
            priority: Event priority
            weak_ref: Use weak reference for automatic cleanup
            
        Returns:
            Subscription ID
        """
        with self._lock:
            if event_name not in self.subscribers:
                self.subscribers[event_name] = []
            
            subscriber = EventSubscriber(callback, event_name, priority, weak_ref)
            self.subscribers[event_name].append(subscriber)
            
            # Sort by priority (highest first)
            self.subscribers[event_name].sort(key=lambda x: x.priority.value, reverse=True)
            
            self.stats["subscribers_count"] += 1
            
            subscription_id = f"{event_name}_{len(self.subscribers[event_name])}"
            logger.debug(f"Subscribed to event '{event_name}' with priority {priority}")
            
            return subscription_id
    
    def unsubscribe(self, event_name: str, callback: Callable) -> bool:
        """Unsubscribe from an event"""
        with self._lock:
            if event_name not in self.subscribers:
                return False
            
            # Find and remove subscriber
            for i, subscriber in enumerate(self.subscribers[event_name]):
                try:
                    if subscriber.callback == callback:
                        del self.subscribers[event_name][i]
                        self.stats["subscribers_count"] -= 1
                        logger.debug(f"Unsubscribed from event '{event_name}'")
                        return True
                except ReferenceError:
                    # Weak reference was garbage collected, remove it
                    del self.subscribers[event_name][i]
                    self.stats["subscribers_count"] -= 1
            
            return False
    
    def unsubscribe_all(self, event_name: str) -> int:
        """Unsubscribe all callbacks from an event"""
        with self._lock:
            if event_name not in self.subscribers:
                return 0
            
            count = len(self.subscribers[event_name])
            del self.subscribers[event_name]
            self.stats["subscribers_count"] -= count
            
            logger.debug(f"Unsubscribed all {count} callbacks from event '{event_name}'")
            return count
    
    async def emit(self, event_name: str, data: Optional[Dict[str, Any]] = None,
                  priority: EventPriority = EventPriority.NORMAL,
                  source: Optional[str] = None, target: Optional[str] = None,
                  immediate: bool = False) -> str:
        """
        Emit an event
        
        Args:
            event_name: Name of the event
            data: Event data
            priority: Event priority
            source: Event source identifier
            target: Event target identifier
            immediate: Process immediately (bypass queue)
            
        Returns:
            Event ID
        """
        event = HolographicEvent(
            name=event_name,
            data=data or {},
            timestamp=time.time(),
            priority=priority,
            source=source,
            target=target
        )
        
        self.stats["events_emitted"] += 1
        
        # Add to history
        self._add_to_history(event)
        
        if immediate:
            await self._process_event(event)
        else:
            await self.event_queue.put(event)
        
        logger.debug(f"Emitted event '{event_name}' with ID {event.event_id}")
        return event.event_id
    
    def emit_sync(self, event_name: str, data: Optional[Dict[str, Any]] = None,
                 priority: EventPriority = EventPriority.NORMAL,
                 source: Optional[str] = None, target: Optional[str] = None) -> str:
        """Synchronous event emission"""
        event = HolographicEvent(
            name=event_name,
            data=data or {},
            timestamp=time.time(),
            priority=priority,
            source=source,
            target=target
        )
        
        self.stats["events_emitted"] += 1
        self._add_to_history(event)
        
        # Process synchronously
        self._process_event_sync(event)
        
        logger.debug(f"Emitted sync event '{event_name}' with ID {event.event_id}")
        return event.event_id
    
    async def _process_events(self):
        """Main event processing loop"""
        logger.info("Event processing loop started")
        
        try:
            while self.running:
                try:
                    # Get event from queue with timeout
                    event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                    await self._process_event(event)
                    self.event_queue.task_done()
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    
        except asyncio.CancelledError:
            logger.info("Event processing loop cancelled")
        except Exception as e:
            logger.error(f"Event processing loop error: {e}")
        finally:
            logger.info("Event processing loop ended")
    
    async def _process_event(self, event: HolographicEvent):
        """Process a single event"""
        try:
            # Apply global filters
            if not self._apply_filters(event):
                self.stats["events_filtered"] += 1
                return
            
            # Find matching subscribers
            matching_subscribers = self._find_matching_subscribers(event.name, event.target)
            
            if not matching_subscribers:
                return
            
            # Process subscribers by priority
            tasks = []
            for subscriber in matching_subscribers:
                if not subscriber.is_valid():
                    continue
                
                try:
                    callback = subscriber.callback
                    
                    # Check if callback is async
                    if asyncio.iscoroutinefunction(callback):
                        tasks.append(callback(event.data))
                    else:
                        # Run sync callback in executor
                        tasks.append(asyncio.get_event_loop().run_in_executor(
                            self.executor, callback, event.data
                        ))
                        
                except ReferenceError:
                    # Weak reference was garbage collected, remove subscriber
                    self._cleanup_invalid_subscriber(subscriber)
                except Exception as e:
                    logger.error(f"Error getting callback for event {event.name}: {e}")
            
            # Execute all callbacks
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            self.stats["events_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error processing event {event.name}: {e}")
    
    def _process_event_sync(self, event: HolographicEvent):
        """Process event synchronously"""
        try:
            # Apply global filters
            if not self._apply_filters(event):
                self.stats["events_filtered"] += 1
                return
            
            # Find matching subscribers
            matching_subscribers = self._find_matching_subscribers(event.name, event.target)
            
            for subscriber in matching_subscribers:
                if not subscriber.is_valid():
                    continue
                
                try:
                    callback = subscriber.callback
                    
                    # Only call sync callbacks
                    if not asyncio.iscoroutinefunction(callback):
                        callback(event.data)
                    else:
                        logger.warning(f"Skipping async callback for sync event {event.name}")
                        
                except ReferenceError:
                    # Weak reference was garbage collected
                    self._cleanup_invalid_subscriber(subscriber)
                except Exception as e:
                    logger.error(f"Error calling sync callback for event {event.name}: {e}")
            
            self.stats["events_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error processing sync event {event.name}: {e}")
    
    def _find_matching_subscribers(self, event_name: str, target: Optional[str]) -> List[EventSubscriber]:
        """Find subscribers matching the event name and target"""
        matching = []
        
        with self._lock:
            # Exact match
            if event_name in self.subscribers:
                matching.extend(self.subscribers[event_name])
            
            # Wildcard matching
            for pattern, subscribers in self.subscribers.items():
                if self._matches_pattern(event_name, pattern):
                    matching.extend(subscribers)
        
        # Filter by target if specified
        if target:
            matching = [s for s in matching if hasattr(s, 'target') and s.target == target]
        
        # Remove duplicates and sort by priority
        unique_matching = list(set(matching))
        unique_matching.sort(key=lambda x: x.priority.value, reverse=True)
        
        return unique_matching
    
    def _matches_pattern(self, event_name: str, pattern: str) -> bool:
        """Check if event name matches pattern (supports wildcards)"""
        if pattern == event_name:
            return True
        
        # Simple wildcard matching
        if '*' in pattern:
            import fnmatch
            return fnmatch.fnmatch(event_name, pattern)
        
        return False
    
    def _apply_filters(self, event: HolographicEvent) -> bool:
        """Apply global filters to event"""
        for filter_func in self.global_filters:
            try:
                if not filter_func(event):
                    return False
            except Exception as e:
                logger.error(f"Error applying filter: {e}")
        
        return True
    
    def add_global_filter(self, filter_func: Callable[[HolographicEvent], bool]):
        """Add a global event filter"""
        if filter_func not in self.global_filters:
            self.global_filters.append(filter_func)
    
    def remove_global_filter(self, filter_func: Callable[[HolographicEvent], bool]):
        """Remove a global event filter"""
        if filter_func in self.global_filters:
            self.global_filters.remove(filter_func)
    
    def _add_to_history(self, event: HolographicEvent):
        """Add event to history"""
        self.event_history.append(event)
        
        # Trim history if too large
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]
    
    def _cleanup_invalid_subscriber(self, subscriber: EventSubscriber):
        """Cleanup invalid subscriber"""
        with self._lock:
            for event_name, subscribers in self.subscribers.items():
                if subscriber in subscribers:
                    subscribers.remove(subscriber)
                    self.stats["subscribers_count"] -= 1
                    break
    
    def get_event_history(self, event_name: Optional[str] = None,
                         limit: Optional[int] = None) -> List[HolographicEvent]:
        """Get event history"""
        history = self.event_history
        
        if event_name:
            history = [e for e in history if e.name == event_name]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event system statistics"""
        with self._lock:
            active_subscribers = sum(len(subs) for subs in self.subscribers.values())
            
            return {
                **self.stats,
                "active_subscribers": active_subscribers,
                "event_types": len(self.subscribers),
                "history_size": len(self.event_history),
                "queue_size": self.event_queue.qsize() if hasattr(self.event_queue, 'qsize') else 0,
                "running": self.running,
                "initialized": self.initialized
            }
    
    def clear_history(self):
        """Clear event history"""
        self.event_history.clear()
    
    def clear_statistics(self):
        """Clear statistics"""
        self.stats = {
            "events_emitted": 0,
            "events_processed": 0,
            "events_filtered": 0,
            "subscribers_count": len([s for subs in self.subscribers.values() for s in subs])
        }
    
    async def _register_system_events(self):
        """Register default system events"""
        system_events = [
            "system.startup",
            "system.shutdown", 
            "system.pause",
            "system.resume",
            "system.error",
            "engine.initialized",
            "engine.started",
            "engine.stopped",
            "engine.paused",
            "engine.resumed",
            "engine.error",
            "engine.frame_batch",
            "config.updated",
            "display.calibrated",
            "gesture.detected",
            "hologram.created",
            "hologram.updated",
            "hologram.destroyed"
        ]
        
        logger.info(f"Registered {len(system_events)} system events")
    
    # Network distribution methods (for distributed holographic systems)
    def enable_network_distribution(self, network_config: Dict[str, Any]):
        """Enable network event distribution"""
        self.network_enabled = True
        # Implementation would depend on specific networking requirements
        logger.info("Network event distribution enabled")
    
    def disable_network_distribution(self):
        """Disable network event distribution"""
        self.network_enabled = False
        self.network_subscribers.clear()
        logger.info("Network event distribution disabled")
    
    async def distribute_network_event(self, event: HolographicEvent):
        """Distribute event to network subscribers"""
        if not self.network_enabled:
            return
        
        # Implementation would serialize event and send to network subscribers
        # This is a placeholder for the network distribution logic
        logger.debug(f"Distributing event {event.name} to network subscribers")
    
    def export_events(self, filename: str, format: str = "json") -> bool:
        """Export event history to file"""
        try:
            if format.lower() == "json":
                events_data = [event.to_dict() for event in self.event_history]
                with open(filename, 'w') as f:
                    json.dump(events_data, f, indent=2)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
            
            logger.info(f"Exported {len(self.event_history)} events to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting events: {e}")
            return False