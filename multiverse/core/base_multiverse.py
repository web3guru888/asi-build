"""
Base Multiverse Component
========================

Base class for all multiverse framework components providing common functionality,
logging, event handling, and lifecycle management.
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import uuid


@dataclass
class ComponentMetadata:
    """Metadata for multiverse components."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"
    created_at: float = field(default_factory=time.time)
    status: str = "inactive"
    properties: Dict[str, Any] = field(default_factory=dict)


class BaseMultiverseComponent(ABC):
    """
    Base class for all multiverse framework components.
    
    Provides common functionality including:
    - Logging with component-specific prefixes
    - Event handling and lifecycle management
    - Performance tracking and metrics
    - Thread-safe operations
    - Configuration management
    """
    
    def __init__(self, name: Optional[str] = None):
        """Initialize base multiverse component."""
        self.metadata = ComponentMetadata(
            name=name or self.__class__.__name__
        )
        
        # Setup logging
        self.logger = logging.getLogger(f"multiverse.{self.metadata.name}")
        self._setup_logging()
        
        # Thread safety
        self._lock = threading.RLock()
        self._state_lock = threading.Lock()
        
        # Component state
        self._is_initialized = False
        self._is_running = False
        self._is_shutting_down = False
        
        # Performance tracking
        self._start_time = time.time()
        self._operation_count = 0
        self._error_count = 0
        self._last_operation_time = None
        
        # Event handlers
        self._event_handlers: Dict[str, List[callable]] = {}
        
        # Initialize component
        self._initialize()
        
        self.logger.info("Component initialized: %s [%s]", 
                        self.metadata.name, self.metadata.id)
    
    def _setup_logging(self):
        """Setup component-specific logging."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _initialize(self):
        """Initialize the component. Override in subclasses."""
        with self._state_lock:
            if not self._is_initialized:
                self.on_initialize()
                self._is_initialized = True
                self.metadata.status = "initialized"
    
    def on_initialize(self):
        """Hook for component-specific initialization. Override in subclasses."""
        pass
    
    def start(self):
        """Start the component."""
        with self._state_lock:
            if not self._is_initialized:
                raise RuntimeError(f"Component {self.metadata.name} not initialized")
            
            if self._is_running:
                self.logger.warning("Component already running")
                return
            
            self.on_start()
            self._is_running = True
            self.metadata.status = "running"
            
            self.logger.info("Component started: %s", self.metadata.name)
    
    def stop(self):
        """Stop the component."""
        with self._state_lock:
            if not self._is_running:
                self.logger.warning("Component not running")
                return
            
            self._is_shutting_down = True
            self.on_stop()
            self._is_running = False
            self.metadata.status = "stopped"
            
            self.logger.info("Component stopped: %s", self.metadata.name)
    
    def on_start(self):
        """Hook for component-specific start logic. Override in subclasses."""
        pass
    
    def on_stop(self):
        """Hook for component-specific stop logic. Override in subclasses."""
        pass
    
    def restart(self):
        """Restart the component."""
        self.stop()
        time.sleep(0.1)  # Brief pause
        self.start()
    
    @property
    def is_running(self) -> bool:
        """Check if component is running."""
        with self._state_lock:
            return self._is_running
    
    @property
    def is_shutting_down(self) -> bool:
        """Check if component is shutting down."""
        with self._state_lock:
            return self._is_shutting_down
    
    def track_operation(self, operation_name: str = "generic"):
        """Track an operation for performance metrics."""
        with self._lock:
            self._operation_count += 1
            self._last_operation_time = time.time()
            
            self.logger.debug("Operation tracked: %s (#%d)", 
                            operation_name, self._operation_count)
    
    def track_error(self, error: Exception, context: str = ""):
        """Track an error for metrics."""
        with self._lock:
            self._error_count += 1
            
            self.logger.error("Error tracked in %s: %s - %s", 
                            context or "unknown context", 
                            type(error).__name__, str(error))
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this component."""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                'component_id': self.metadata.id,
                'component_name': self.metadata.name,
                'uptime_seconds': uptime,
                'operation_count': self._operation_count,
                'error_count': self._error_count,
                'operations_per_second': self._operation_count / max(uptime, 1),
                'error_rate': self._error_count / max(self._operation_count, 1),
                'last_operation_time': self._last_operation_time,
                'status': self.metadata.status
            }
    
    def add_event_handler(self, event_type: str, handler: callable):
        """Add an event handler for a specific event type."""
        with self._lock:
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            self._event_handlers[event_type].append(handler)
            
            self.logger.debug("Event handler added: %s -> %s", 
                            event_type, handler.__name__)
    
    def remove_event_handler(self, event_type: str, handler: callable):
        """Remove an event handler."""
        with self._lock:
            if event_type in self._event_handlers:
                try:
                    self._event_handlers[event_type].remove(handler)
                    self.logger.debug("Event handler removed: %s -> %s", 
                                    event_type, handler.__name__)
                except ValueError:
                    self.logger.warning("Event handler not found: %s -> %s", 
                                      event_type, handler.__name__)
    
    def emit_event(self, event_type: str, data: Any = None):
        """Emit an event to all registered handlers."""
        with self._lock:
            handlers = self._event_handlers.get(event_type, [])
            
            for handler in handlers:
                try:
                    handler(event_type, data)
                except Exception as e:
                    self.logger.error("Error in event handler %s: %s", 
                                    handler.__name__, e)
                    self.track_error(e, f"event_handler_{event_type}")
    
    def get_metadata(self) -> ComponentMetadata:
        """Get component metadata."""
        return self.metadata
    
    def update_property(self, key: str, value: Any):
        """Update a component property."""
        with self._lock:
            self.metadata.properties[key] = value
            self.logger.debug("Property updated: %s = %s", key, value)
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a component property."""
        with self._lock:
            return self.metadata.properties.get(key, default)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the component."""
        try:
            # Basic health indicators
            health = {
                'component_id': self.metadata.id,
                'component_name': self.metadata.name,
                'status': self.metadata.status,
                'is_running': self.is_running,
                'is_healthy': True,
                'uptime_seconds': time.time() - self._start_time,
                'operation_count': self._operation_count,
                'error_count': self._error_count,
                'last_check': time.time()
            }
            
            # Component-specific health check
            custom_health = self.on_health_check()
            if custom_health:
                health.update(custom_health)
            
            # Determine overall health
            error_rate = self._error_count / max(self._operation_count, 1)
            if error_rate > 0.1:  # More than 10% error rate
                health['is_healthy'] = False
                health['health_issues'] = ['high_error_rate']
            
            return health
            
        except Exception as e:
            self.logger.error("Health check failed: %s", e)
            return {
                'component_id': self.metadata.id,
                'component_name': self.metadata.name,
                'status': 'error',
                'is_healthy': False,
                'error': str(e),
                'last_check': time.time()
            }
    
    def on_health_check(self) -> Optional[Dict[str, Any]]:
        """Hook for component-specific health checks. Override in subclasses."""
        return None
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of component status."""
        return {
            'id': self.metadata.id,
            'name': self.metadata.name,
            'version': self.metadata.version,
            'status': self.metadata.status,
            'is_running': self.is_running,
            'created_at': self.metadata.created_at,
            'uptime': time.time() - self._start_time,
            'operation_count': self._operation_count,
            'error_count': self._error_count,
            'properties': self.metadata.properties.copy()
        }
    
    def __repr__(self) -> str:
        """String representation of the component."""
        return (f"{self.__class__.__name__}("
                f"name='{self.metadata.name}', "
                f"id='{self.metadata.id[:8]}...', "
                f"status='{self.metadata.status}')")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


class MultiverseComponent(BaseMultiverseComponent):
    """
    Enhanced base component with multiverse-specific functionality.
    """
    
    def __init__(self, name: Optional[str] = None, universe_aware: bool = True):
        """Initialize multiverse component."""
        super().__init__(name)
        
        self.universe_aware = universe_aware
        self.current_universe_id: Optional[str] = None
        self.universe_contexts: Dict[str, Dict[str, Any]] = {}
        
        if universe_aware:
            self.logger.info("Component is universe-aware")
    
    def set_universe_context(self, universe_id: str, context: Dict[str, Any]):
        """Set context for a specific universe."""
        if not self.universe_aware:
            self.logger.warning("Component is not universe-aware")
            return
        
        with self._lock:
            self.universe_contexts[universe_id] = context.copy()
            self.logger.debug("Universe context set: %s", universe_id)
    
    def get_universe_context(self, universe_id: str) -> Optional[Dict[str, Any]]:
        """Get context for a specific universe."""
        if not self.universe_aware:
            return None
        
        with self._lock:
            return self.universe_contexts.get(universe_id)
    
    def switch_universe_context(self, universe_id: str) -> bool:
        """Switch to a different universe context."""
        if not self.universe_aware:
            self.logger.warning("Component is not universe-aware")
            return False
        
        with self._lock:
            if universe_id not in self.universe_contexts:
                self.logger.error("Universe context not found: %s", universe_id)
                return False
            
            old_universe = self.current_universe_id
            self.current_universe_id = universe_id
            
            # Trigger context switch hook
            self.on_universe_context_switch(old_universe, universe_id)
            
            self.logger.info("Switched universe context: %s -> %s", 
                           old_universe, universe_id)
            return True
    
    def on_universe_context_switch(self, from_universe: Optional[str], 
                                  to_universe: str):
        """Hook for universe context switches. Override in subclasses."""
        pass
    
    def get_current_universe_context(self) -> Optional[Dict[str, Any]]:
        """Get current universe context."""
        if not self.universe_aware or not self.current_universe_id:
            return None
        
        return self.get_universe_context(self.current_universe_id)
    
    def on_health_check(self) -> Optional[Dict[str, Any]]:
        """Enhanced health check with universe context information."""
        health = super().on_health_check() or {}
        
        if self.universe_aware:
            health.update({
                'universe_aware': True,
                'current_universe': self.current_universe_id,
                'universe_contexts_count': len(self.universe_contexts)
            })
        
        return health