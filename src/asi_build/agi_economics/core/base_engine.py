"""
Base Economic Engine
===================

Abstract base class for all economic components in the AGI platform.
"""

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EconomicEvent:
    """Represents an economic event in the system"""

    id: str
    timestamp: float
    event_type: str
    agent_id: Optional[str] = None
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.data is None:
            self.data = {}


class BaseEconomicEngine(ABC):
    """
    Abstract base class for all economic engines in the AGI platform.

    Provides common functionality for event tracking, metrics collection,
    and state management.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.events: List[EconomicEvent] = []
        self.metrics: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}
        self.is_active = False
        self.engine_id = str(uuid.uuid4())

        logger.info(f"Initialized {self.__class__.__name__} with ID {self.engine_id}")

    @abstractmethod
    def start(self) -> bool:
        """Start the economic engine"""
        pass

    @abstractmethod
    def stop(self) -> bool:
        """Stop the economic engine"""
        pass

    @abstractmethod
    def process_event(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process an economic event"""
        pass

    def log_event(self, event_type: str, agent_id: str = None, data: Dict[str, Any] = None):
        """Log an economic event"""
        event = EconomicEvent(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            event_type=event_type,
            agent_id=agent_id,
            data=data or {},
        )
        self.events.append(event)
        logger.debug(f"Logged event: {event_type} for agent {agent_id}")
        return event

    def update_metrics(self, metrics: Dict[str, Any]):
        """Update engine metrics"""
        self.metrics.update(metrics)
        self.metrics["last_updated"] = time.time()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current engine metrics"""
        return {
            "engine_id": self.engine_id,
            "is_active": self.is_active,
            "total_events": len(self.events),
            "last_event_time": self.events[-1].timestamp if self.events else None,
            **self.metrics,
        }

    def get_events(
        self, event_type: str = None, agent_id: str = None, limit: int = None
    ) -> List[EconomicEvent]:
        """Get filtered events"""
        filtered_events = self.events

        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]

        if agent_id:
            filtered_events = [e for e in filtered_events if e.agent_id == agent_id]

        if limit:
            filtered_events = filtered_events[-limit:]

        return filtered_events

    def reset_state(self):
        """Reset engine state"""
        self.events.clear()
        self.metrics.clear()
        self.state.clear()
        self.is_active = False
        logger.info(f"Reset state for engine {self.engine_id}")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "engine_id": self.engine_id,
            "status": "healthy" if self.is_active else "inactive",
            "uptime": time.time() - (self.metrics.get("start_time", time.time())),
            "event_count": len(self.events),
            "error_count": len([e for e in self.events if e.event_type == "error"]),
        }
