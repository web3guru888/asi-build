"""
Async Adapter Base Class
========================

Abstract base class for async-native Cognitive Blackboard adapters.

Implements all sync and async protocols from ``..protocols`` so that
concrete adapters only need to override the ``async`` methods.  Sync
wrappers (``produce()``, ``consume()``, ``handle_event()``) are provided
for backward compatibility with the synchronous blackboard sweep, and
they delegate to the async variants via ``asyncio.run()`` or the
running event loop.

Thread safety is achieved through ``asyncio.Lock`` (for async code paths)
and a ``threading.Lock`` fallback (for sync callers on threads without an
event loop).

Usage
~~~~~
::

    class MyAdapter(AsyncAdapterBase):
        MODULE_NAME = "my_module"
        MODULE_VERSION = "1.0.0"

        @property
        def module_info(self) -> ModuleInfo:
            return ModuleInfo(
                name=self.MODULE_NAME,
                version=self.MODULE_VERSION,
                capabilities=ModuleCapability.PRODUCER | ModuleCapability.CONSUMER,
                description="My async adapter",
            )

        async def produce_async(self) -> Sequence[BlackboardEntry]:
            ...

        async def consume_async(self, entries: Sequence[BlackboardEntry]) -> None:
            ...

        async def handle_event_async(self, event: CognitiveEvent) -> None:
            ...

        def snapshot(self) -> Dict[str, Any]:
            return {"status": "ok"}
"""

from __future__ import annotations

import abc
import asyncio
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Sequence

from ..protocols import (
    BlackboardEntry,
    CognitiveEvent,
    EventHandler,
    ModuleCapability,
    ModuleInfo,
)

logger = logging.getLogger(__name__)

__all__ = ["AsyncAdapterBase"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_coroutine_sync(coro):
    """Run a coroutine from a synchronous context.

    If there is already a running event loop (e.g. inside a Jupyter
    notebook or an async framework), we schedule the coroutine on that
    loop from a new thread.  Otherwise we spin up a fresh loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We are inside an already-running loop — cannot call loop.run_until_complete.
        # Schedule on a background thread's loop instead.
        result = [None]
        exc = [None]

        def _target():
            try:
                result[0] = asyncio.run(coro)
            except Exception as e:
                exc[0] = e

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        t.join()
        if exc[0] is not None:
            raise exc[0]
        return result[0]

    # No running loop — safe to create one.
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class AsyncAdapterBase(abc.ABC):
    """Abstract base class for async-native Cognitive Blackboard adapters.

    Concrete subclasses **must** implement:

    * :pyattr:`MODULE_NAME` (class attribute)
    * :pyattr:`MODULE_VERSION` (class attribute)
    * :py:attr:`module_info` (property → ``ModuleInfo``)
    * :py:meth:`produce_async` → ``Sequence[BlackboardEntry]``
    * :py:meth:`consume_async`
    * :py:meth:`handle_event_async`
    * :py:meth:`snapshot` → ``Dict[str, Any]``

    Optionally override :py:meth:`transform_async` if the adapter also
    acts as a transformer.

    Thread safety
    ~~~~~~~~~~~~~
    All mutation goes through ``self._async_lock`` (an ``asyncio.Lock``)
    when called from async code, and ``self._sync_lock`` (a
    ``threading.Lock``) when called from synchronous callers.

    The locks are **not** held simultaneously — the sync wrappers acquire
    ``_sync_lock``, then delegate to the async method which acquires
    ``_async_lock``.  This avoids deadlocks while still preventing
    concurrent modification from mixed sync/async callers.
    """

    # Override in subclasses -------------------------------------------------
    MODULE_NAME: str = "async_adapter"
    MODULE_VERSION: str = "0.0.0"

    # -----------------------------------------------------------------------
    # Initialisation
    # -----------------------------------------------------------------------

    def __init__(self) -> None:
        self._blackboard: Optional[Any] = None
        self._event_handler: Optional[EventHandler] = None
        self._async_lock = asyncio.Lock()
        self._sync_lock = threading.Lock()
        self._created_at: float = time.time()

    # -----------------------------------------------------------------------
    # BlackboardParticipant protocol
    # -----------------------------------------------------------------------

    @property
    @abc.abstractmethod
    def module_info(self) -> ModuleInfo:
        """Return metadata about this adapter module."""
        ...

    def on_registered(self, blackboard: Any) -> None:
        """Called when the adapter is registered with a blackboard.

        Stores a reference to the blackboard for later use (e.g. to
        post entries outside of the production sweep).
        """
        self._blackboard = blackboard
        logger.debug("%s: registered with blackboard", self.MODULE_NAME)

    # -----------------------------------------------------------------------
    # EventEmitter protocol
    # -----------------------------------------------------------------------

    def set_event_handler(self, handler: EventHandler) -> None:
        """Inject the event-bus callback used by :meth:`_emit`."""
        self._event_handler = handler
        logger.debug("%s: event handler set", self.MODULE_NAME)

    def _emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Emit a ``CognitiveEvent`` via the registered handler.

        No-op if no handler has been injected yet — adapters should
        degrade gracefully during startup.
        """
        if self._event_handler is None:
            return
        event = CognitiveEvent(
            event_type=event_type,
            payload=payload or {},
            source=self.MODULE_NAME,
        )
        try:
            self._event_handler(event)
        except Exception:
            logger.warning(
                "%s: event handler raised for %s", self.MODULE_NAME, event_type, exc_info=True
            )

    # -----------------------------------------------------------------------
    # Async abstract methods (override these)
    # -----------------------------------------------------------------------

    @abc.abstractmethod
    async def produce_async(self) -> Sequence[BlackboardEntry]:
        """Generate entries to post to the blackboard (async).

        Called during a production sweep.  Return an empty sequence if
        there is nothing new to report.
        """
        ...

    @abc.abstractmethod
    async def consume_async(self, entries: Sequence[BlackboardEntry]) -> None:
        """Process entries read from the blackboard (async).

        The blackboard delivers entries matching this adapter's subscribed
        topics.
        """
        ...

    async def transform_async(
        self, entries: Sequence[BlackboardEntry]
    ) -> Sequence[BlackboardEntry]:
        """Transform entries and return derived entries (async).

        The default implementation is a pass-through — override in
        adapters that act as transformers.
        """
        return list(entries)

    @abc.abstractmethod
    async def handle_event_async(self, event: CognitiveEvent) -> None:
        """Handle an incoming event (async)."""
        ...

    # -----------------------------------------------------------------------
    # Sync wrappers (BlackboardProducer / Consumer / Transformer / EventListener)
    # -----------------------------------------------------------------------

    def produce(self) -> Sequence[BlackboardEntry]:
        """Synchronous wrapper around :meth:`produce_async`."""
        with self._sync_lock:
            return _run_coroutine_sync(self.produce_async())

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Synchronous wrapper around :meth:`consume_async`."""
        with self._sync_lock:
            _run_coroutine_sync(self.consume_async(entries))

    def transform(self, entries: Sequence[BlackboardEntry]) -> Sequence[BlackboardEntry]:
        """Synchronous wrapper around :meth:`transform_async`."""
        with self._sync_lock:
            return _run_coroutine_sync(self.transform_async(entries))

    def handle_event(self, event: CognitiveEvent) -> None:
        """Synchronous wrapper around :meth:`handle_event_async`."""
        with self._sync_lock:
            _run_coroutine_sync(self.handle_event_async(event))

    # -----------------------------------------------------------------------
    # Snapshot / introspection
    # -----------------------------------------------------------------------

    @abc.abstractmethod
    def snapshot(self) -> Dict[str, Any]:
        """Return a serialisable snapshot of the adapter's current state.

        Used by the blackboard's monitoring/dashboard layer.
        """
        ...

    def __repr__(self) -> str:
        return f"<{type(self).__name__} module={self.MODULE_NAME!r} v{self.MODULE_VERSION}>"
