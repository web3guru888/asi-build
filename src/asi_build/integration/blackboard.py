"""
Cognitive Blackboard — Shared workspace for cross-module data exchange.

The blackboard is the central coordination point of the ASI:BUILD integration
layer.  Modules post findings and read others' findings through a type-safe,
thread-safe, async-compatible API.

Architecture
~~~~~~~~~~~~

::

    ┌────────────────────────────────────────────────────────────────┐
    │                   CognitiveBlackboard                          │
    │                                                                │
    │  ┌──────────┐   ┌──────────┐   ┌──────────┐                  │
    │  │ Topic A  │   │ Topic B  │   │ Topic C  │   ...             │
    │  │ entries  │   │ entries  │   │ entries  │                    │
    │  └──────────┘   └──────────┘   └──────────┘                  │
    │                                                                │
    │  ┌─────────────────────────────────────────┐                  │
    │  │            EventBus                      │                  │
    │  │  blackboard.entry.added                  │                  │
    │  │  blackboard.entry.updated                │                  │
    │  │  blackboard.entry.expired                │                  │
    │  │  blackboard.module.registered            │                  │
    │  └─────────────────────────────────────────┘                  │
    │                                                                │
    │  ┌─────────────────────────────────────────┐                  │
    │  │         Module Registry                  │                  │
    │  │  consciousness  [P,C,T]                  │                  │
    │  │  reasoning       [P,R]                   │                  │
    │  │  bio_inspired    [P,C]                   │                  │
    │  └─────────────────────────────────────────┘                  │
    └────────────────────────────────────────────────────────────────┘

Lifecycle events emitted on the embedded ``EventBus``:

- ``blackboard.entry.added``    — payload: ``{"entry_id", "topic", "source_module"}``
- ``blackboard.entry.updated``  — payload: ``{"entry_id", "topic", "field", "old", "new"}``
- ``blackboard.entry.removed``  — payload: ``{"entry_id", "topic", "reason"}``
- ``blackboard.entry.expired``  — payload: ``{"entry_id", "topic"}``
- ``blackboard.module.registered``   — payload: ``{"module_name", "capabilities"}``
- ``blackboard.module.unregistered`` — payload: ``{"module_name"}``
- ``blackboard.sweep.complete``      — payload: ``{"expired_count", "active_count"}``
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
)

from .events import EventBus
from .protocols import (
    BlackboardEntry,
    BlackboardParticipant,
    BlackboardQuery,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    ModuleCapability,
    ModuleInfo,
)

logger = logging.getLogger(__name__)

_UNSET = object()  # sentinel for "field not provided"


class CognitiveBlackboard:
    """Thread-safe, async-compatible cognitive blackboard.

    Parameters
    ----------
    event_bus : EventBus, optional
        External event bus.  If ``None``, an internal bus is created.
    max_entries : int
        Hard cap on total entries.  Oldest low-priority entries are evicted
        when the cap is reached.
    auto_expire : bool
        If ``True``, queries and sweeps automatically mark expired entries.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        max_entries: int = 10_000,
        auto_expire: bool = True,
    ) -> None:
        self._lock = threading.RLock()
        self.event_bus: EventBus = event_bus or EventBus()
        self._max_entries = max_entries
        self._auto_expire = auto_expire

        # Primary storage: entry_id → BlackboardEntry
        self._entries: Dict[str, BlackboardEntry] = {}
        # Index: topic → set of entry_ids
        self._topic_index: Dict[str, Set[str]] = defaultdict(set)
        # Index: source_module → set of entry_ids
        self._source_index: Dict[str, Set[str]] = defaultdict(set)
        # Registered modules: name → ModuleInfo
        self._modules: Dict[str, ModuleInfo] = {}
        # Module instances: name → participant object
        self._module_instances: Dict[str, BlackboardParticipant] = {}
        # Stats
        self._total_posted = 0
        self._total_removed = 0

    # ── Module registration ───────────────────────────────────────────

    def register_module(
        self,
        participant: BlackboardParticipant,
    ) -> None:
        """Register a module with the blackboard.

        The module's ``on_registered()`` callback is invoked after
        registration.

        Raises
        ------
        ValueError
            If a module with the same name is already registered.
        """
        info = participant.module_info
        with self._lock:
            if info.name in self._modules:
                raise ValueError(
                    f"Module '{info.name}' is already registered"
                )
            self._modules[info.name] = info
            self._module_instances[info.name] = participant

        participant.on_registered(self)

        self.event_bus.emit(CognitiveEvent(
            event_type="blackboard.module.registered",
            payload={
                "module_name": info.name,
                "capabilities": str(info.capabilities),
                "version": info.version,
            },
            source="blackboard",
        ))
        logger.info("Module registered: %s (v%s)", info.name, info.version)

    def unregister_module(self, module_name: str) -> bool:
        """Unregister a module.  Returns ``True`` if it existed."""
        with self._lock:
            existed = module_name in self._modules
            self._modules.pop(module_name, None)
            self._module_instances.pop(module_name, None)

        if existed:
            self.event_bus.emit(CognitiveEvent(
                event_type="blackboard.module.unregistered",
                payload={"module_name": module_name},
                source="blackboard",
            ))
        return existed

    def get_module(self, module_name: str) -> Optional[ModuleInfo]:
        """Get info about a registered module."""
        with self._lock:
            return self._modules.get(module_name)

    def get_module_instance(self, module_name: str) -> Optional[BlackboardParticipant]:
        """Get the actual participant object for a registered module."""
        with self._lock:
            return self._module_instances.get(module_name)

    def list_modules(self) -> List[ModuleInfo]:
        """List all registered modules."""
        with self._lock:
            return list(self._modules.values())

    # ── Entry CRUD ────────────────────────────────────────────────────

    def post(self, entry: BlackboardEntry) -> str:
        """Post an entry to the blackboard.

        Returns the entry's ID.  If the blackboard is at capacity, the
        oldest low-priority entry is evicted first.

        Emits ``blackboard.entry.added``.
        """
        with self._lock:
            # Capacity enforcement
            if len(self._entries) >= self._max_entries:
                self._evict_one()
            self._entries[entry.entry_id] = entry
            self._topic_index[entry.topic].add(entry.entry_id)
            self._source_index[entry.source_module].add(entry.entry_id)
            self._total_posted += 1

        self.event_bus.emit(CognitiveEvent(
            event_type="blackboard.entry.added",
            payload={
                "entry_id": entry.entry_id,
                "topic": entry.topic,
                "source_module": entry.source_module,
                "priority": entry.priority.name,
            },
            source="blackboard",
        ))
        return entry.entry_id

    def post_many(self, entries: Sequence[BlackboardEntry]) -> List[str]:
        """Post multiple entries atomically.  Returns their IDs."""
        ids = []
        with self._lock:
            for entry in entries:
                if len(self._entries) >= self._max_entries:
                    self._evict_one()
                self._entries[entry.entry_id] = entry
                self._topic_index[entry.topic].add(entry.entry_id)
                self._source_index[entry.source_module].add(entry.entry_id)
                self._total_posted += 1
                ids.append(entry.entry_id)

        # Events outside lock
        for entry in entries:
            self.event_bus.emit(CognitiveEvent(
                event_type="blackboard.entry.added",
                payload={
                    "entry_id": entry.entry_id,
                    "topic": entry.topic,
                    "source_module": entry.source_module,
                },
                source="blackboard",
            ))
        return ids

    def get(self, entry_id: str) -> Optional[BlackboardEntry]:
        """Get an entry by ID.  Returns ``None`` if not found or expired."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return None
            if self._auto_expire and entry.is_expired:
                self._expire_entry(entry)
                return None
            return entry

    def query(self, q: BlackboardQuery) -> List[BlackboardEntry]:
        """Query entries matching *q*.

        Returns entries sorted by (priority desc, timestamp desc).
        """
        with self._lock:
            if self._auto_expire:
                self._sweep_expired()

            # Fast path: topic filter uses index
            if q.topics:
                candidate_ids: Set[str] = set()
                for topic in q.topics:
                    # Exact match
                    candidate_ids |= self._topic_index.get(topic, set())
                    # Prefix match (subtopics)
                    for indexed_topic, ids in self._topic_index.items():
                        if indexed_topic.startswith(topic + "."):
                            candidate_ids |= ids
                candidates = [
                    self._entries[eid] for eid in candidate_ids
                    if eid in self._entries
                ]
            else:
                candidates = list(self._entries.values())

            results = [e for e in candidates if q.matches(e)]

        # Sort: priority desc, then timestamp desc
        results.sort(key=lambda e: (e.priority.value, e.timestamp), reverse=True)
        if q.limit is not None:
            results = results[:q.limit]
        return results

    def get_by_topic(self, topic: str, include_subtopics: bool = True) -> List[BlackboardEntry]:
        """Convenience: get all active entries for a topic."""
        with self._lock:
            if self._auto_expire:
                self._sweep_expired()

            ids = set(self._topic_index.get(topic, set()))
            if include_subtopics:
                for t, eids in self._topic_index.items():
                    if t.startswith(topic + "."):
                        ids |= eids
            results = [
                self._entries[eid]
                for eid in ids
                if eid in self._entries
                and self._entries[eid].status == EntryStatus.ACTIVE
                and not self._entries[eid].is_expired
            ]
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results

    def get_by_source(self, source_module: str) -> List[BlackboardEntry]:
        """Get all active entries from a specific module."""
        with self._lock:
            ids = self._source_index.get(source_module, set())
            results = [
                self._entries[eid]
                for eid in ids
                if eid in self._entries
                and self._entries[eid].status == EntryStatus.ACTIVE
                and not self._entries[eid].is_expired
            ]
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results

    def update_entry(
        self,
        entry_id: str,
        *,
        data: Any = _UNSET,
        confidence: Any = _UNSET,
        status: Any = _UNSET,
        priority: Any = _UNSET,
        tags: Any = _UNSET,
        metadata: Any = _UNSET,
    ) -> bool:
        """Update fields of an existing entry.

        Returns ``True`` if the entry was found and updated.
        Emits ``blackboard.entry.updated`` for each changed field.
        """
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return False

            changes: List[Dict[str, Any]] = []

            if data is not _UNSET:
                changes.append({"field": "data", "old": entry.data, "new": data})
                entry.data = data
            if confidence is not _UNSET:
                changes.append({"field": "confidence", "old": entry.confidence, "new": confidence})
                entry.confidence = confidence
            if status is not _UNSET:
                changes.append({"field": "status", "old": entry.status.value, "new": status.value})
                entry.status = status
            if priority is not _UNSET:
                changes.append({"field": "priority", "old": entry.priority.name, "new": priority.name})
                entry.priority = priority
            if tags is not _UNSET:
                changes.append({"field": "tags", "old": set(entry.tags), "new": set(tags)})
                entry.tags = frozenset(tags)
            if metadata is not _UNSET:
                changes.append({"field": "metadata", "old": entry.metadata, "new": metadata})
                entry.metadata = metadata

        for change in changes:
            self.event_bus.emit(CognitiveEvent(
                event_type="blackboard.entry.updated",
                payload={"entry_id": entry_id, "topic": entry.topic, **change},
                source="blackboard",
            ))
        return bool(changes)

    def remove(self, entry_id: str, reason: str = "explicit") -> bool:
        """Remove an entry from the blackboard.

        Returns ``True`` if found and removed.
        Emits ``blackboard.entry.removed``.
        """
        with self._lock:
            entry = self._entries.pop(entry_id, None)
            if entry is None:
                return False
            self._topic_index[entry.topic].discard(entry_id)
            self._source_index[entry.source_module].discard(entry_id)
            self._total_removed += 1

        self.event_bus.emit(CognitiveEvent(
            event_type="blackboard.entry.removed",
            payload={
                "entry_id": entry_id,
                "topic": entry.topic,
                "reason": reason,
            },
            source="blackboard",
        ))
        return True

    def retract(self, entry_id: str) -> bool:
        """Mark an entry as retracted (soft-delete — kept for provenance)."""
        return self.update_entry(entry_id, status=EntryStatus.RETRACTED)

    def supersede(self, old_entry_id: str, new_entry: BlackboardEntry) -> str:
        """Replace an entry with a new one.

        The old entry is marked ``SUPERSEDED``; the new entry's
        ``parent_id`` is set to the old entry's ID.

        Returns the new entry's ID.
        """
        self.update_entry(old_entry_id, status=EntryStatus.SUPERSEDED)
        new_entry.parent_id = old_entry_id
        return self.post(new_entry)

    # ── Maintenance ───────────────────────────────────────────────────

    def sweep_expired(self) -> int:
        """Manually expire all entries that have exceeded their TTL.

        Returns the count of newly expired entries.
        Emits ``blackboard.sweep.complete``.
        """
        with self._lock:
            count = self._sweep_expired()
            active = sum(
                1 for e in self._entries.values()
                if e.status == EntryStatus.ACTIVE
            )

        self.event_bus.emit(CognitiveEvent(
            event_type="blackboard.sweep.complete",
            payload={"expired_count": count, "active_count": active},
            source="blackboard",
        ))
        return count

    def clear(self) -> int:
        """Remove all entries.  Returns count removed."""
        with self._lock:
            n = len(self._entries)
            self._entries.clear()
            self._topic_index.clear()
            self._source_index.clear()
            self._total_removed += n
        return n

    # ── Introspection ─────────────────────────────────────────────────

    @property
    def entry_count(self) -> int:
        """Total entries currently stored (including expired/retracted)."""
        with self._lock:
            return len(self._entries)

    @property
    def active_entry_count(self) -> int:
        """Count of ACTIVE, non-expired entries."""
        with self._lock:
            return sum(
                1 for e in self._entries.values()
                if e.status == EntryStatus.ACTIVE and not e.is_expired
            )

    @property
    def module_count(self) -> int:
        with self._lock:
            return len(self._modules)

    def get_topics(self) -> List[str]:
        """List all topics that have at least one entry."""
        with self._lock:
            return [t for t, ids in self._topic_index.items() if ids]

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive blackboard statistics."""
        with self._lock:
            status_counts: Dict[str, int] = defaultdict(int)
            topic_counts: Dict[str, int] = defaultdict(int)
            source_counts: Dict[str, int] = defaultdict(int)

            for entry in self._entries.values():
                status_counts[entry.status.value] += 1
                topic_counts[entry.topic] += 1
                source_counts[entry.source_module] += 1

            return {
                "total_entries": len(self._entries),
                "max_entries": self._max_entries,
                "total_posted": self._total_posted,
                "total_removed": self._total_removed,
                "registered_modules": len(self._modules),
                "status_distribution": dict(status_counts),
                "entries_by_topic": dict(topic_counts),
                "entries_by_source": dict(source_counts),
                "event_bus": self.event_bus.get_stats(),
            }

    # ── Internal helpers ──────────────────────────────────────────────

    def _sweep_expired(self) -> int:
        """Expire entries past TTL.  Caller must hold ``self._lock``."""
        expired_ids = [
            eid for eid, entry in self._entries.items()
            if entry.status == EntryStatus.ACTIVE and entry.is_expired
        ]
        for eid in expired_ids:
            self._expire_entry(self._entries[eid])
        return len(expired_ids)

    def _expire_entry(self, entry: BlackboardEntry) -> None:
        """Mark a single entry as expired.  Caller must hold ``self._lock``."""
        entry.status = EntryStatus.EXPIRED
        # Don't remove from storage — keep for provenance queries
        self.event_bus.emit(CognitiveEvent(
            event_type="blackboard.entry.expired",
            payload={"entry_id": entry.entry_id, "topic": entry.topic},
            source="blackboard",
        ))

    def _evict_one(self) -> None:
        """Evict the oldest LOW-priority entry to make room.

        If no LOW entries exist, evict the oldest NORMAL, then HIGH.
        CRITICAL entries are never evicted (capacity is violated).

        Caller must hold ``self._lock``.
        """
        for priority_level in (EntryPriority.LOW, EntryPriority.NORMAL, EntryPriority.HIGH):
            candidates = [
                (eid, e) for eid, e in self._entries.items()
                if e.priority == priority_level
            ]
            if candidates:
                # Oldest first
                candidates.sort(key=lambda x: x[1].timestamp)
                eid, entry = candidates[0]
                self._entries.pop(eid)
                self._topic_index[entry.topic].discard(eid)
                self._source_index[entry.source_module].discard(eid)
                self._total_removed += 1
                return
        # If only CRITICAL entries remain, allow over-capacity rather than evict
        logger.warning(
            "Blackboard at capacity (%d) with only CRITICAL entries — no eviction possible",
            self._max_entries,
        )
