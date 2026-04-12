"""
Kenny Graph SSE ↔ Blackboard Adapter
========================================

Server-Sent-Events (SSE) streaming adapter that wraps graph intelligence
results into an SSE-compatible stream format.

Takes community detection and reasoning results from the graph intelligence
module and formats them as SSE events that can be streamed to web clients
via an ``/events`` endpoint.

Topics produced
~~~~~~~~~~~~~~~
- ``kenny_graph.sse_event``     — Formatted SSE events for client streaming
- ``kenny_graph.stream_status`` — Stream connection state and statistics

Topics consumed
~~~~~~~~~~~~~~~
- ``graph_intelligence``        — Community detection, graph stats → format as SSE
- ``knowledge_graph``           — KG triples, pathfinding → format as SSE

Events emitted
~~~~~~~~~~~~~~
- ``kenny_graph.stream.connected`` — A new SSE stream was started
- ``kenny_graph.stream.data``      — Data event pushed to SSE stream

Events listened
~~~~~~~~~~~~~~~
- ``graph_intelligence.community.detected``  — Wrap as SSE event
- ``knowledge_graph.triple.added``           — Wrap as SSE event
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Any, Dict, Iterator, List, Optional, Sequence

from ..protocols import (
    BlackboardEntry,
    BlackboardQuery,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    EventHandler,
    ModuleCapability,
    ModuleInfo,
)

logger = logging.getLogger(__name__)

_graph_intelligence_module = None


def _get_graph_intelligence():
    """Lazy import of graph_intelligence module to allow graceful degradation."""
    global _graph_intelligence_module
    if _graph_intelligence_module is None:
        try:
            from asi_build import graph_intelligence as _gm

            _graph_intelligence_module = _gm
        except (ImportError, ModuleNotFoundError):
            _graph_intelligence_module = False
    return _graph_intelligence_module if _graph_intelligence_module is not False else None


class SSEEvent:
    """A single Server-Sent Event."""

    __slots__ = ("event_type", "data", "event_id", "retry")

    def __init__(
        self,
        data: str,
        event_type: str = "message",
        event_id: Optional[str] = None,
        retry: Optional[int] = None,
    ) -> None:
        self.event_type = event_type
        self.data = data
        self.event_id = event_id
        self.retry = retry

    def format(self) -> str:
        """Format as SSE wire protocol text."""
        lines: List[str] = []
        if self.event_type and self.event_type != "message":
            lines.append(f"event: {self.event_type}")
        if self.event_id is not None:
            lines.append(f"id: {self.event_id}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        for line in self.data.split("\n"):
            lines.append(f"data: {line}")
        lines.append("")
        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "event_id": self.event_id,
            "retry": self.retry,
        }


class KennyGraphBlackboardAdapter:
    """SSE streaming adapter for graph intelligence results.

    Wraps graph intelligence community detection and reasoning results
    into Server-Sent Events that can be streamed to web clients.  Uses
    an internal queue to buffer events for SSE consumption.

    Parameters
    ----------
    graph_adapter : optional
        A ``GraphIntelligenceAdapter`` instance (from the blackboard adapter layer).
    max_queue_size : int
        Maximum SSE events to buffer before dropping oldest (default 1000).
    sse_event_ttl : float
        TTL in seconds for SSE event entries (default 60).
    stream_status_ttl : float
        TTL for stream status entries (default 120).
    heartbeat_interval : float
        Seconds between heartbeat SSE comments (default 30).
    """

    MODULE_NAME = "kenny_graph"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        graph_adapter: Any = None,
        *,
        max_queue_size: int = 1000,
        sse_event_ttl: float = 60.0,
        stream_status_ttl: float = 120.0,
        heartbeat_interval: float = 30.0,
    ) -> None:
        self._graph_adapter = graph_adapter
        self._max_queue_size = max_queue_size
        self._sse_event_ttl = sse_event_ttl
        self._stream_status_ttl = stream_status_ttl
        self._heartbeat_interval = heartbeat_interval

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # SSE queue and state
        self._event_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._event_counter: int = 0
        self._total_events_produced: int = 0
        self._total_events_dropped: int = 0
        self._connected_streams: int = 0
        self._last_stream_count: int = 0
        self._last_event_id: Optional[str] = None
        self._pending_sse_entries: List[Dict[str, Any]] = []

    # ── BlackboardParticipant protocol ────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER
                | ModuleCapability.CONSUMER
                | ModuleCapability.TRANSFORMER
            ),
            description=(
                "Kenny Graph SSE adapter: formats graph intelligence and "
                "knowledge graph results as Server-Sent Events for web streaming."
            ),
            topics_produced=frozenset(
                {
                    "kenny_graph.sse_event",
                    "kenny_graph.stream_status",
                }
            ),
            topics_consumed=frozenset(
                {
                    "graph_intelligence",
                    "knowledge_graph",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "KennyGraphBlackboardAdapter registered with blackboard "
            "(graph_adapter=%s)",
            self._graph_adapter is not None,
        )

    # ── EventEmitter protocol ─────────────────────────────────────────

    def set_event_handler(self, handler: EventHandler) -> None:
        self._event_handler = handler

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Emit an event via the injected handler."""
        if self._event_handler is not None:
            self._event_handler(
                CognitiveEvent(
                    event_type=event_type,
                    payload=payload,
                    source=self.MODULE_NAME,
                )
            )

    # ── EventListener protocol ────────────────────────────────────────

    def handle_event(self, event: CognitiveEvent) -> None:
        """Handle incoming events from other modules and convert to SSE."""
        try:
            if event.event_type.startswith("graph_intelligence."):
                self._handle_graph_event(event)
            elif event.event_type.startswith("knowledge_graph."):
                self._handle_kg_event(event)
        except Exception:
            logger.debug(
                "KennyGraphBlackboardAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── Public API: SSE stream interface ──────────────────────────────

    def connect_stream(self) -> str:
        """Register a new SSE stream connection.

        Returns a stream ID.  Call ``disconnect_stream(stream_id)``
        when the client disconnects.
        """
        with self._lock:
            self._connected_streams += 1
            stream_id = f"sse_{self._connected_streams}_{time.time_ns()}"

        self._emit(
            "kenny_graph.stream.connected",
            {"stream_id": stream_id, "total_streams": self._connected_streams},
        )
        return stream_id

    def disconnect_stream(self, stream_id: str) -> None:
        """Unregister an SSE stream connection."""
        with self._lock:
            self._connected_streams = max(0, self._connected_streams - 1)

    def iter_events(self, timeout: float = 30.0) -> Iterator[str]:
        """Iterate over SSE events as formatted strings.

        Yields SSE-formatted text suitable for writing to an HTTP response.
        Blocks up to ``timeout`` seconds waiting for the next event.
        Yields a heartbeat comment (``:``) if no events arrive within
        ``heartbeat_interval`` seconds.
        """
        while True:
            try:
                sse_event = self._event_queue.get(timeout=min(timeout, self._heartbeat_interval))
                yield sse_event.format()
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f": heartbeat {time.time()}\n\n"

    def get_queued_events(self, max_count: int = 100) -> List[SSEEvent]:
        """Drain up to ``max_count`` events from the queue (non-blocking).

        Returns a list of ``SSEEvent`` objects.
        """
        events: List[SSEEvent] = []
        while len(events) < max_count:
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def push_event(
        self,
        data: Any,
        event_type: str = "message",
        event_id: Optional[str] = None,
    ) -> bool:
        """Manually push an SSE event into the queue.

        Returns True if the event was queued, False if dropped.
        """
        if isinstance(data, dict):
            data_str = json.dumps(data, default=str)
        else:
            data_str = str(data)

        with self._lock:
            self._event_counter += 1
            eid = event_id or f"evt_{self._event_counter}"

        sse = SSEEvent(
            data=data_str,
            event_type=event_type,
            event_id=eid,
        )

        try:
            self._event_queue.put_nowait(sse)
            with self._lock:
                self._total_events_produced += 1
                self._last_event_id = eid
            return True
        except queue.Full:
            # Drop oldest event and retry
            try:
                self._event_queue.get_nowait()
                self._event_queue.put_nowait(sse)
                with self._lock:
                    self._total_events_produced += 1
                    self._total_events_dropped += 1
                    self._last_event_id = eid
                return True
            except (queue.Empty, queue.Full):
                with self._lock:
                    self._total_events_dropped += 1
                return False

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from pending SSE events and stream status."""
        entries: List[BlackboardEntry] = []

        with self._lock:
            sse_entries = self._produce_sse_entries()
            entries.extend(sse_entries)

            status_entry = self._produce_stream_status()
            if status_entry is not None:
                entries.append(status_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume graph intelligence and KG entries → format as SSE events."""
        for entry in entries:
            try:
                if entry.topic.startswith("graph_intelligence."):
                    self._consume_graph_intelligence(entry)
                elif entry.topic.startswith("knowledge_graph."):
                    self._consume_knowledge_graph(entry)
            except Exception:
                logger.debug(
                    "KennyGraphBlackboardAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_sse_entries(self) -> List[BlackboardEntry]:
        """Flush pending SSE entries to blackboard."""
        if not self._pending_sse_entries:
            return []

        entries: List[BlackboardEntry] = []
        to_post = list(self._pending_sse_entries)
        self._pending_sse_entries.clear()

        for sse_data in to_post:
            entries.append(
                BlackboardEntry(
                    topic="kenny_graph.sse_event",
                    data=sse_data,
                    source_module=self.MODULE_NAME,
                    confidence=0.9,
                    priority=EntryPriority.NORMAL,
                    ttl_seconds=self._sse_event_ttl,
                    tags=frozenset({"sse", "stream", "graph", sse_data.get("event_type", "message")}),
                    metadata={
                        "event_type": sse_data.get("event_type", "message"),
                        "event_id": sse_data.get("event_id"),
                    },
                )
            )

        return entries

    def _produce_stream_status(self) -> Optional[BlackboardEntry]:
        """Report SSE stream connection status."""
        # Change detection: only post if stream count changed or significant event activity
        if self._connected_streams == self._last_stream_count:
            return None

        self._last_stream_count = self._connected_streams

        status_data = {
            "connected_streams": self._connected_streams,
            "queue_size": self._event_queue.qsize(),
            "total_events_produced": self._total_events_produced,
            "total_events_dropped": self._total_events_dropped,
            "last_event_id": self._last_event_id,
            "max_queue_size": self._max_queue_size,
            "timestamp": time.time(),
        }

        return BlackboardEntry(
            topic="kenny_graph.stream_status",
            data=status_data,
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=EntryPriority.LOW,
            ttl_seconds=self._stream_status_ttl,
            tags=frozenset({"sse", "stream", "status", "connection"}),
            metadata={
                "connected_streams": self._connected_streams,
                "queue_size": self._event_queue.qsize(),
            },
        )

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_graph_intelligence(self, entry: BlackboardEntry) -> None:
        """Convert graph intelligence entries into SSE events."""
        data = entry.data if isinstance(entry.data, dict) else {"raw": str(entry.data)}
        sse_data = {
            "source": "graph_intelligence",
            "topic": entry.topic,
            "entry_id": entry.entry_id,
            "confidence": entry.confidence,
            **data,
        }

        # Determine SSE event type from topic
        if "community" in entry.topic:
            event_type = "community_update"
        elif "stats" in entry.topic or "statistics" in entry.topic:
            event_type = "graph_stats"
        elif "reasoning" in entry.topic:
            event_type = "graph_reasoning"
        else:
            event_type = "graph_update"

        pushed = self.push_event(sse_data, event_type=event_type)
        if pushed:
            self._pending_sse_entries.append({
                "event_type": event_type,
                "event_id": self._last_event_id,
                "source_topic": entry.topic,
                "source_entry_id": entry.entry_id,
            })

            self._emit(
                "kenny_graph.stream.data",
                {
                    "event_type": event_type,
                    "source_topic": entry.topic,
                    "event_id": self._last_event_id,
                },
            )

    def _consume_knowledge_graph(self, entry: BlackboardEntry) -> None:
        """Convert knowledge graph entries into SSE events."""
        data = entry.data if isinstance(entry.data, dict) else {"raw": str(entry.data)}
        sse_data = {
            "source": "knowledge_graph",
            "topic": entry.topic,
            "entry_id": entry.entry_id,
            "confidence": entry.confidence,
            **data,
        }

        # Determine SSE event type from topic
        if "triple" in entry.topic:
            event_type = "kg_triple"
        elif "contradiction" in entry.topic:
            event_type = "kg_contradiction"
        elif "pathfinding" in entry.topic:
            event_type = "kg_path"
        else:
            event_type = "kg_update"

        pushed = self.push_event(sse_data, event_type=event_type)
        if pushed:
            self._pending_sse_entries.append({
                "event_type": event_type,
                "event_id": self._last_event_id,
                "source_topic": entry.topic,
                "source_entry_id": entry.entry_id,
            })

            self._emit(
                "kenny_graph.stream.data",
                {
                    "event_type": event_type,
                    "source_topic": entry.topic,
                    "event_id": self._last_event_id,
                },
            )

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_graph_event(self, event: CognitiveEvent) -> None:
        """Convert graph intelligence events into SSE events."""
        payload = event.payload or {}
        sse_data = {
            "source": "graph_intelligence_event",
            "event_type": event.event_type,
            "event_id": event.event_id,
            **payload,
        }
        event_type = "graph_event"
        if "community" in event.event_type:
            event_type = "community_event"
        self.push_event(sse_data, event_type=event_type)

    def _handle_kg_event(self, event: CognitiveEvent) -> None:
        """Convert knowledge graph events into SSE events."""
        payload = event.payload or {}
        sse_data = {
            "source": "knowledge_graph_event",
            "event_type": event.event_type,
            "event_id": event.event_id,
            **payload,
        }
        event_type = "kg_event"
        if "triple" in event.event_type:
            event_type = "kg_triple_event"
        self.push_event(sse_data, event_type=event_type)

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of the SSE streaming state."""
        return {
            "module": self.MODULE_NAME,
            "has_graph_adapter": self._graph_adapter is not None,
            "connected_streams": self._connected_streams,
            "queue_size": self._event_queue.qsize(),
            "max_queue_size": self._max_queue_size,
            "total_events_produced": self._total_events_produced,
            "total_events_dropped": self._total_events_dropped,
            "last_event_id": self._last_event_id,
            "pending_sse_entries": len(self._pending_sse_entries),
            "heartbeat_interval": self._heartbeat_interval,
            "registered": self._blackboard is not None,
        }
