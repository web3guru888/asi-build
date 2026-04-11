"""
Cognitive Event Bus — Pub/sub event system for cross-module communication.

Provides both synchronous and asynchronous event delivery with:

- **Topic-based routing**: subscribe to ``"consciousness.phi"`` or wildcard
  ``"consciousness.*"`` or catch-all ``"*"``.
- **Priority ordering**: higher-priority listeners fire first.
- **Thread safety**: all operations are guarded by a reentrant lock.
- **Async support**: ``emit_async()`` dispatches to both sync and async handlers.
- **Event history**: configurable ring buffer of recent events for replay.
- **Dead-letter tracking**: failed handler invocations are recorded.

Usage::

    bus = EventBus(history_size=500)
    bus.subscribe("reasoning.*", my_handler)
    bus.emit(CognitiveEvent(event_type="reasoning.conclusion", payload={...}))
"""

from __future__ import annotations

import asyncio
import collections
import fnmatch
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)

from .protocols import AsyncEventHandler, CognitiveEvent, EventHandler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subscription record
# ---------------------------------------------------------------------------


@dataclass
class Subscription:
    """A registered event subscription.

    Attributes
    ----------
    sub_id : str
        Unique subscription ID (for unsubscription).
    pattern : str
        Topic pattern (fnmatch-style, e.g. ``"consciousness.*"``).
    handler : EventHandler
        Synchronous callback.
    async_handler : Optional[AsyncEventHandler]
        Asynchronous callback (mutually exclusive with *handler* in practice,
        but both can be set).
    priority : int
        Higher values fire first.
    source_filter : Optional[str]
        If set, only events from this source module are delivered.
    """

    sub_id: str
    pattern: str
    handler: Optional[EventHandler] = None
    async_handler: Optional[AsyncEventHandler] = None
    priority: int = 0
    source_filter: Optional[str] = None


@dataclass
class DeadLetter:
    """Record of a failed handler invocation."""

    event: CognitiveEvent
    subscription_id: str
    error: str
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------


class EventBus:
    """Thread-safe, async-compatible event bus with topic-based routing.

    Parameters
    ----------
    history_size : int
        Maximum number of past events kept for replay.  0 = no history.
    """

    def __init__(self, history_size: int = 1000) -> None:
        self._lock = threading.RLock()
        self._subscriptions: Dict[str, Subscription] = {}  # sub_id → Subscription
        self._history: Deque[CognitiveEvent] = collections.deque(maxlen=history_size or None)
        self._history_size = history_size
        self._dead_letters: Deque[DeadLetter] = collections.deque(maxlen=200)
        self._paused = False
        self._emit_count = 0
        self._error_count = 0

    # -- Subscription management -------------------------------------------

    def subscribe(
        self,
        pattern: str,
        handler: Optional[EventHandler] = None,
        async_handler: Optional[AsyncEventHandler] = None,
        priority: int = 0,
        source_filter: Optional[str] = None,
    ) -> str:
        """Subscribe to events matching *pattern*.

        Returns the subscription ID (use with :meth:`unsubscribe`).

        Parameters
        ----------
        pattern : str
            ``fnmatch``-style topic pattern.  ``"*"`` matches everything.
        handler : EventHandler, optional
            Synchronous callback ``(CognitiveEvent) -> None``.
        async_handler : AsyncEventHandler, optional
            Async callback ``(CognitiveEvent) -> Awaitable[None]``.
        priority : int
            Higher values fire first within the same emit cycle.
        source_filter : str, optional
            Only deliver events whose ``source`` matches this string.
        """
        if handler is None and async_handler is None:
            raise ValueError("At least one of handler / async_handler must be provided")
        sub_id = uuid.uuid4().hex
        sub = Subscription(
            sub_id=sub_id,
            pattern=pattern,
            handler=handler,
            async_handler=async_handler,
            priority=priority,
            source_filter=source_filter,
        )
        with self._lock:
            self._subscriptions[sub_id] = sub
        return sub_id

    def unsubscribe(self, sub_id: str) -> bool:
        """Remove a subscription.  Returns ``True`` if it existed."""
        with self._lock:
            return self._subscriptions.pop(sub_id, None) is not None

    def unsubscribe_all(self, pattern: Optional[str] = None) -> int:
        """Remove all subscriptions, optionally filtered by *pattern*.

        Returns the count of removed subscriptions.
        """
        with self._lock:
            if pattern is None:
                n = len(self._subscriptions)
                self._subscriptions.clear()
                return n
            to_remove = [sid for sid, sub in self._subscriptions.items() if sub.pattern == pattern]
            for sid in to_remove:
                del self._subscriptions[sid]
            return len(to_remove)

    # -- Emission ----------------------------------------------------------

    def emit(self, event: CognitiveEvent) -> int:
        """Emit an event synchronously.

        Invokes all matching *sync* handlers in priority order.
        Returns the number of handlers invoked successfully.

        Async handlers are **skipped** — use :meth:`emit_async` for those.
        """
        if self._paused:
            return 0

        with self._lock:
            self._history.append(event)
            self._emit_count += 1
            matched = self._match_subscriptions(event)

        invoked = 0
        for sub in matched:
            if sub.handler is not None:
                try:
                    sub.handler(event)
                    invoked += 1
                except Exception as exc:
                    self._record_dead_letter(event, sub.sub_id, exc)
        return invoked

    async def emit_async(self, event: CognitiveEvent) -> int:
        """Emit an event asynchronously.

        Invokes both sync and async handlers.  Sync handlers are called
        directly (not offloaded to a thread) for simplicity — they should
        be fast.  Returns total successful invocations.
        """
        if self._paused:
            return 0

        with self._lock:
            self._history.append(event)
            self._emit_count += 1
            matched = self._match_subscriptions(event)

        invoked = 0
        for sub in matched:
            # Sync handler
            if sub.handler is not None:
                try:
                    sub.handler(event)
                    invoked += 1
                except Exception as exc:
                    self._record_dead_letter(event, sub.sub_id, exc)
            # Async handler
            if sub.async_handler is not None:
                try:
                    await sub.async_handler(event)
                    invoked += 1
                except Exception as exc:
                    self._record_dead_letter(event, sub.sub_id, exc)
        return invoked

    # -- Query / replay ----------------------------------------------------

    def get_history(
        self,
        pattern: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[float] = None,
    ) -> List[CognitiveEvent]:
        """Return recent events, optionally filtered.

        Parameters
        ----------
        pattern : str, optional
            fnmatch pattern to filter by event_type.
        limit : int, optional
            Max events to return (most recent first).
        since : float, optional
            Only events after this UNIX timestamp.
        """
        with self._lock:
            events = list(self._history)
        if since is not None:
            events = [e for e in events if e.timestamp >= since]
        if pattern is not None:
            events = [e for e in events if fnmatch.fnmatch(e.event_type, pattern)]
        events.reverse()  # most recent first
        if limit is not None:
            events = events[:limit]
        return events

    def replay(
        self,
        pattern: str = "*",
        handler: Optional[EventHandler] = None,
        async_handler: Optional[AsyncEventHandler] = None,
        since: Optional[float] = None,
    ) -> int:
        """Replay historical events through a handler.

        Useful for late-joining modules that need to catch up.
        Returns the count of events replayed.
        """
        events = self.get_history(pattern=pattern, since=since)
        events.reverse()  # chronological order for replay
        count = 0
        for event in events:
            if handler is not None:
                try:
                    handler(event)
                    count += 1
                except Exception:
                    pass  # replay is best-effort
        return count

    # -- Control -----------------------------------------------------------

    def pause(self) -> None:
        """Pause event delivery.  Events emitted while paused are dropped."""
        self._paused = True

    def resume(self) -> None:
        """Resume event delivery."""
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    def clear_history(self) -> None:
        """Drop all historical events."""
        with self._lock:
            self._history.clear()

    # -- Introspection -----------------------------------------------------

    @property
    def subscription_count(self) -> int:
        with self._lock:
            return len(self._subscriptions)

    @property
    def emit_count(self) -> int:
        return self._emit_count

    @property
    def error_count(self) -> int:
        return self._error_count

    def get_subscriptions(self, pattern: Optional[str] = None) -> List[Subscription]:
        """List subscriptions, optionally filtered by pattern."""
        with self._lock:
            subs = list(self._subscriptions.values())
        if pattern is not None:
            subs = [s for s in subs if s.pattern == pattern]
        return subs

    def get_dead_letters(self, limit: int = 50) -> List[DeadLetter]:
        """Return recent dead letters (failed handler invocations)."""
        with self._lock:
            letters = list(self._dead_letters)
        letters.reverse()
        return letters[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Return bus statistics."""
        with self._lock:
            return {
                "subscriptions": len(self._subscriptions),
                "history_size": len(self._history),
                "history_capacity": self._history_size,
                "total_emitted": self._emit_count,
                "total_errors": self._error_count,
                "dead_letters": len(self._dead_letters),
                "paused": self._paused,
            }

    # -- Internals ---------------------------------------------------------

    def _match_subscriptions(self, event: CognitiveEvent) -> List[Subscription]:
        """Return subscriptions matching *event*, sorted by descending priority.

        Caller must hold ``self._lock``.
        """
        matched: List[Subscription] = []
        for sub in self._subscriptions.values():
            if sub.source_filter and event.source != sub.source_filter:
                continue
            if fnmatch.fnmatch(event.event_type, sub.pattern):
                matched.append(sub)
        matched.sort(key=lambda s: s.priority, reverse=True)
        return matched

    def _record_dead_letter(self, event: CognitiveEvent, sub_id: str, exc: Exception) -> None:
        with self._lock:
            self._error_count += 1
            self._dead_letters.append(
                DeadLetter(
                    event=event,
                    subscription_id=sub_id,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
        logger.warning(
            "EventBus handler error [sub=%s, event=%s]: %s",
            sub_id,
            event.event_type,
            exc,
        )
