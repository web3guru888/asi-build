"""
Cognitive Integration Protocols — Type-safe interfaces for cross-module communication.

Defines the contracts that ASI:BUILD modules implement to participate in the
Cognitive Blackboard architecture.  Pure stdlib; no external dependencies.

Architecture
~~~~~~~~~~~~
Modules communicate through a shared **CognitiveBlackboard** (see blackboard.py).
Each participating module:

1. Implements ``BlackboardParticipant`` (read/write the blackboard).
2. Optionally implements ``EventEmitter`` / ``EventListener`` for pub/sub.
3. Declares its capabilities via ``ModuleCapability`` flags.

Data on the blackboard is wrapped in ``BlackboardEntry`` containers that carry
provenance metadata (source module, timestamp, confidence, TTL).
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Protocol,
    Sequence,
    Set,
    TypeVar,
    runtime_checkable,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ModuleCapability(enum.Flag):
    """Capability flags that modules declare on registration.

    Flags are combinable:  ``PRODUCER | CONSUMER | TRANSFORMER``
    """

    PRODUCER = enum.auto()       # Can write new entries to the blackboard
    CONSUMER = enum.auto()       # Reads entries from the blackboard
    TRANSFORMER = enum.auto()    # Reads, transforms, and writes back
    REASONER = enum.auto()       # Can perform reasoning over entries
    VALIDATOR = enum.auto()      # Can validate / score entries
    LEARNER = enum.auto()        # Adapts based on blackboard history


class EntryPriority(enum.IntEnum):
    """Priority levels for blackboard entries — higher = more urgent."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class EntryStatus(enum.Enum):
    """Lifecycle status of a blackboard entry."""

    ACTIVE = "active"
    CONSUMED = "consumed"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    RETRACTED = "retracted"


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class BlackboardEntry:
    """An item posted to the Cognitive Blackboard.

    Attributes
    ----------
    entry_id : str
        Unique identifier (auto-generated UUID4 if not supplied).
    topic : str
        Hierarchical topic string (e.g. ``"consciousness.phi"``,
        ``"reasoning.hypothesis"``).  Used for subscription routing.
    data : Any
        Arbitrary payload — dict, dataclass, primitive, etc.
    source_module : str
        Name of the module that produced this entry.
    timestamp : float
        UNIX epoch when the entry was created.
    confidence : float
        Producer's confidence in this data (0.0–1.0).
    priority : EntryPriority
        Urgency level.
    status : EntryStatus
        Lifecycle status.
    ttl_seconds : Optional[float]
        Time-to-live in seconds.  ``None`` = never expires.
    tags : FrozenSet[str]
        Freeform tags for filtering.
    parent_id : Optional[str]
        ID of the entry this one was derived from (provenance chain).
    metadata : Dict[str, Any]
        Arbitrary key-value metadata.
    """

    topic: str
    data: Any
    source_module: str
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    priority: EntryPriority = EntryPriority.NORMAL
    status: EntryStatus = EntryStatus.ACTIVE
    ttl_seconds: Optional[float] = None
    tags: FrozenSet[str] = field(default_factory=frozenset)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check whether this entry has exceeded its TTL."""
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.timestamp) > self.ttl_seconds


@dataclass
class ModuleInfo:
    """Metadata about a registered module.

    Attributes
    ----------
    name : str
        Unique module name (e.g. ``"consciousness"``).
    version : str
        Semver string.
    capabilities : ModuleCapability
        Declared capability flags.
    description : str
        Human-readable description.
    topics_produced : FrozenSet[str]
        Topics this module writes to.
    topics_consumed : FrozenSet[str]
        Topics this module subscribes to.
    """

    name: str
    version: str = "0.0.0"
    capabilities: ModuleCapability = ModuleCapability.PRODUCER
    description: str = ""
    topics_produced: FrozenSet[str] = field(default_factory=frozenset)
    topics_consumed: FrozenSet[str] = field(default_factory=frozenset)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

@dataclass
class CognitiveEvent:
    """An event published on the EventBus.

    Unlike blackboard entries (persistent data), events are transient
    notifications.  They carry a small payload and are delivered to all
    matching listeners in real time.

    Attributes
    ----------
    event_type : str
        Dot-separated type hierarchy (e.g. ``"blackboard.entry.added"``).
    payload : Dict[str, Any]
        Event-specific data.
    source : str
        Name of the emitting module (or ``"system"``).
    timestamp : float
        When the event was emitted.
    event_id : str
        Unique ID.
    """

    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)


# Callback signatures
EventHandler = Callable[[CognitiveEvent], None]
AsyncEventHandler = Callable  # Actually Callable[[CognitiveEvent], Awaitable[None]]

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Protocols — structural subtyping
# ---------------------------------------------------------------------------

@runtime_checkable
class BlackboardParticipant(Protocol):
    """Protocol for any module that can interact with the blackboard."""

    @property
    def module_info(self) -> ModuleInfo:
        """Return metadata about this module."""
        ...

    def on_registered(self, blackboard: Any) -> None:
        """Called when the module is registered with a blackboard.

        The module can store a reference to the blackboard for later posting.
        """
        ...


@runtime_checkable
class BlackboardProducer(Protocol):
    """Protocol for modules that produce entries."""

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate entries to post to the blackboard.

        Returns a (possibly empty) sequence of entries.  The blackboard
        calls this during a *production sweep*.
        """
        ...


@runtime_checkable
class BlackboardConsumer(Protocol):
    """Protocol for modules that consume entries."""

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Process entries read from the blackboard.

        The blackboard calls this with entries matching the module's
        subscribed topics.
        """
        ...


@runtime_checkable
class BlackboardTransformer(Protocol):
    """Protocol for modules that transform entries.

    A transformer reads entries, processes them, and produces new entries
    (with ``parent_id`` set for provenance).
    """

    def transform(self, entries: Sequence[BlackboardEntry]) -> Sequence[BlackboardEntry]:
        """Transform a batch of entries, returning new derived entries."""
        ...


@runtime_checkable
class EventEmitter(Protocol):
    """Protocol for modules that emit events."""

    def set_event_handler(self, handler: EventHandler) -> None:
        """Set the callback the module uses to emit events.

        The blackboard/event-bus injects this after registration so the
        module does not need a direct reference to the bus.
        """
        ...


@runtime_checkable
class EventListener(Protocol):
    """Protocol for modules that listen to events."""

    def handle_event(self, event: CognitiveEvent) -> None:
        """Handle an incoming event."""
        ...


@runtime_checkable
class AsyncBlackboardProducer(Protocol):
    """Async variant of BlackboardProducer."""

    async def produce_async(self) -> Sequence[BlackboardEntry]:
        ...


@runtime_checkable
class AsyncBlackboardConsumer(Protocol):
    """Async variant of BlackboardConsumer."""

    async def consume_async(self, entries: Sequence[BlackboardEntry]) -> None:
        ...


@runtime_checkable
class AsyncBlackboardTransformer(Protocol):
    """Async variant of BlackboardTransformer."""

    async def transform_async(
        self, entries: Sequence[BlackboardEntry]
    ) -> Sequence[BlackboardEntry]:
        ...


@runtime_checkable
class AsyncEventListener(Protocol):
    """Async variant of EventListener."""

    async def handle_event_async(self, event: CognitiveEvent) -> None:
        ...


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

@dataclass
class BlackboardQuery:
    """Structured query against the blackboard.

    All fields are optional — ``None`` means "no constraint".
    Multiple constraints are AND-ed.
    """

    topics: Optional[List[str]] = None
    source_modules: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    min_priority: Optional[EntryPriority] = None
    tags_any: Optional[Set[str]] = None     # match if entry has ANY of these
    tags_all: Optional[Set[str]] = None     # match if entry has ALL of these
    statuses: Optional[Set[EntryStatus]] = None
    since_timestamp: Optional[float] = None
    limit: Optional[int] = None
    include_expired: bool = False

    def matches(self, entry: BlackboardEntry) -> bool:
        """Test whether *entry* satisfies all constraints."""
        if not self.include_expired and entry.is_expired:
            return False
        if self.statuses and entry.status not in self.statuses:
            return False
        if self.topics:
            if not any(
                entry.topic == t or entry.topic.startswith(t + ".")
                for t in self.topics
            ):
                return False
        if self.source_modules and entry.source_module not in self.source_modules:
            return False
        if self.min_confidence is not None and entry.confidence < self.min_confidence:
            return False
        if self.min_priority is not None and entry.priority < self.min_priority:
            return False
        if self.tags_any and not (set(entry.tags) & self.tags_any):
            return False
        if self.tags_all and not (self.tags_all <= set(entry.tags)):
            return False
        if self.since_timestamp is not None and entry.timestamp < self.since_timestamp:
            return False
        return True
