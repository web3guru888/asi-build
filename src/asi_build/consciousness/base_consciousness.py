"""
Base Consciousness Framework

This module provides the foundational architecture for all consciousness models
in the Kenny system. It defines the core interfaces and common functionality
shared across different theories of consciousness.
"""

import time
import threading
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

class ConsciousnessState(Enum):
    """States of consciousness system"""
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PROCESSING = "processing"
    REFLECTING = "reflecting"
    LEARNING = "learning"
    ERROR = "error"

@dataclass
class ConsciousnessEvent:
    """Represents an event in the consciousness system"""
    event_id: str
    timestamp: float
    event_type: str
    data: Dict[str, Any]
    priority: int = 5  # 1-10, 10 being highest
    source_module: str = ""
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'data': self.data,
            'priority': self.priority,
            'source_module': self.source_module,
            'confidence': self.confidence
        }

@dataclass
class ConsciousnessMetrics:
    """Metrics for consciousness system performance"""
    awareness_level: float = 0.0
    attention_focus: float = 0.0
    self_model_accuracy: float = 0.0
    prediction_accuracy: float = 0.0
    integration_level: float = 0.0
    metacognitive_accuracy: float = 0.0
    emotional_coherence: float = 0.0
    learning_rate: float = 0.0
    total_events_processed: int = 0
    average_processing_time: float = 0.0
    last_updated: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'awareness_level': self.awareness_level,
            'attention_focus': self.attention_focus,
            'self_model_accuracy': self.self_model_accuracy,
            'prediction_accuracy': self.prediction_accuracy,
            'integration_level': self.integration_level,
            'metacognitive_accuracy': self.metacognitive_accuracy,
            'emotional_coherence': self.emotional_coherence,
            'learning_rate': self.learning_rate,
            'total_events_processed': self.total_events_processed,
            'average_processing_time': self.average_processing_time,
            'last_updated': self.last_updated
        }

class BaseConsciousness(ABC):
    """
    Abstract base class for all consciousness models.
    
    Provides common infrastructure including:
    - Event processing
    - State management
    - Metrics collection
    - Threading support
    - Logging
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.state = ConsciousnessState.INACTIVE
        self.metrics = ConsciousnessMetrics()
        
        # Event system
        self.event_queue: List[ConsciousnessEvent] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.event_lock = threading.Lock()
        
        # Processing
        self.processing_thread: Optional[threading.Thread] = None
        self.should_stop = threading.Event()
        self.update_interval = self.config.get('update_interval', 0.1)
        
        # Logging
        self.logger = logging.getLogger(f"consciousness.{name}")
        
        # Callbacks
        self.state_change_callbacks: List[Callable] = []
        
        # Initialize subclass
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """Initialize the specific consciousness model"""
        pass
    
    @abstractmethod
    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process a consciousness event and optionally return a response event"""
        pass
    
    @abstractmethod
    def update(self) -> None:
        """Update the consciousness model state"""
        pass
    
    @abstractmethod
    def get_current_state(self) -> Dict[str, Any]:
        """Get current internal state of the consciousness model"""
        pass
    
    def start(self) -> None:
        """Start the consciousness processing thread"""
        if self.processing_thread and self.processing_thread.is_alive():
            self.logger.warning(f"{self.name} is already running")
            return
            
        self.should_stop.clear()
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        self._set_state(ConsciousnessState.ACTIVE)
        self.logger.info(f"{self.name} consciousness started")
    
    def stop(self) -> None:
        """Stop the consciousness processing"""
        self.should_stop.set()
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        self._set_state(ConsciousnessState.INACTIVE)
        self.logger.info(f"{self.name} consciousness stopped")
    
    def add_event(self, event: ConsciousnessEvent) -> None:
        """Add an event to the processing queue"""
        with self.event_lock:
            self.event_queue.append(event)
            # Sort by priority (highest first)
            self.event_queue.sort(key=lambda e: e.priority, reverse=True)
    
    def subscribe_to_event(self, event_type: str, handler: Callable) -> None:
        """Subscribe to specific event types"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def emit_event(self, event: ConsciousnessEvent) -> None:
        """Emit an event to all subscribers"""
        if event.event_type in self.event_handlers:
            for handler in self.event_handlers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {e}")
    
    def add_state_change_callback(self, callback: Callable) -> None:
        """Add callback for state changes"""
        self.state_change_callbacks.append(callback)
    
    def _set_state(self, new_state: ConsciousnessState) -> None:
        """Change consciousness state and notify callbacks"""
        old_state = self.state
        self.state = new_state
        
        for callback in self.state_change_callbacks:
            try:
                callback(self.name, old_state, new_state)
            except Exception as e:
                self.logger.error(f"Error in state change callback: {e}")
    
    def _processing_loop(self) -> None:
        """Main processing loop for consciousness"""
        while not self.should_stop.is_set():
            try:
                start_time = time.time()
                
                # Process events
                events_processed = self._process_events()
                
                # Update consciousness model
                self.update()
                
                # Update metrics
                processing_time = time.time() - start_time
                self._update_metrics(events_processed, processing_time)
                
                # Sleep until next update
                time.sleep(max(0, self.update_interval - processing_time))
                
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
                self._set_state(ConsciousnessState.ERROR)
                time.sleep(1.0)  # Prevent tight error loop
    
    def _process_events(self) -> int:
        """Process all queued events"""
        events_processed = 0
        
        while True:
            event = None
            with self.event_lock:
                if self.event_queue:
                    event = self.event_queue.pop(0)
            
            if not event:
                break
            
            try:
                start_time = time.time()
                response_event = self.process_event(event)
                processing_time = time.time() - start_time
                
                # Emit response event if generated
                if response_event:
                    self.emit_event(response_event)
                
                events_processed += 1
                
                # Log slow processing
                if processing_time > 0.1:
                    self.logger.warning(f"Slow event processing: {processing_time:.3f}s for {event.event_type}")
                    
            except Exception as e:
                self.logger.error(f"Error processing event {event.event_id}: {e}")
        
        return events_processed
    
    def _update_metrics(self, events_processed: int, processing_time: float) -> None:
        """Update consciousness metrics"""
        self.metrics.total_events_processed += events_processed
        
        # Update average processing time (exponential moving average)
        alpha = 0.1
        self.metrics.average_processing_time = (
            alpha * processing_time + 
            (1 - alpha) * self.metrics.average_processing_time
        )
        
        self.metrics.last_updated = time.time()
    
    def get_metrics(self) -> ConsciousnessMetrics:
        """Get current metrics"""
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information"""
        return {
            'name': self.name,
            'state': self.state.value,
            'metrics': self.metrics.to_dict(),
            'event_queue_size': len(self.event_queue),
            'event_handlers': {k: len(v) for k, v in self.event_handlers.items()},
            'is_running': self.processing_thread and self.processing_thread.is_alive(),
            'internal_state': self.get_current_state()
        }
    
    def save_state(self, filepath: str) -> None:
        """Save consciousness state to file"""
        state_data = {
            'name': self.name,
            'config': self.config,
            'metrics': self.metrics.to_dict(),
            'internal_state': self.get_current_state(),
            'timestamp': time.time()
        }
        
        with open(filepath, 'w') as f:
            json.dump(state_data, f, indent=2)
    
    def load_state(self, filepath: str) -> None:
        """Load consciousness state from file"""
        with open(filepath, 'r') as f:
            state_data = json.load(f)
        
        # Restore metrics
        metrics_data = state_data.get('metrics', {})
        for key, value in metrics_data.items():
            if hasattr(self.metrics, key):
                setattr(self.metrics, key, value)
        
        self.logger.info(f"Loaded state from {filepath}")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', state={self.state.value})"