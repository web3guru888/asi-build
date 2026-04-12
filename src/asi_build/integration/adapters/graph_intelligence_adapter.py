"""
Graph Intelligence ↔ Blackboard Adapter
=========================================

Bridges the graph_intelligence module (``CommunityDetectionEngine``,
``FastToGReasoningEngine``, ``SchemaManager``) with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``graph_intelligence.communities``  — Community detection results
- ``graph_intelligence.reasoning``    — FastToG reasoning outputs
- ``graph_intelligence.graph_stats``  — Graph statistics (node/edge/community counts)

Topics consumed
~~~~~~~~~~~~~~~
- ``knowledge_graph``   — KG updates → trigger community re-detection
- ``reasoning``         — Reasoning queries → feed into FastToG pipeline
- ``consciousness``     — Consciousness broadcasts → prioritise relevant communities

Events emitted
~~~~~~~~~~~~~~
- ``graph_intelligence.communities.detected``   — New communities found
- ``graph_intelligence.reasoning.completed``    — FastToG reasoning finished
- ``graph_intelligence.graph.updated``          — Graph structure changed

Events listened
~~~~~~~~~~~~~~~
- ``knowledge_graph.triple.added``      → Trigger re-analysis
- ``reasoning.inference.completed``     → Feed into graph reasoning
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Sequence

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

# Lazy imports — the graph_intelligence module may not be available
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


class GraphIntelligenceAdapter:
    """Adapter connecting the graph_intelligence module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``CommunityDetectionEngine`` — Louvain / Girvan-Newman / hybrid community detection
    - ``FastToGReasoningEngine``   — Community-based graph reasoning
    - ``SchemaManager``            — Graph schema operations

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    community_engine : optional
        A ``CommunityDetectionEngine`` instance.
    reasoning_engine : optional
        A ``FastToGReasoningEngine`` instance.
    schema_manager : optional
        A ``SchemaManager`` instance.  If engines are passed without an explicit
        *schema_manager*, the adapter extracts it from ``community_engine.sm``
        or ``reasoning_engine.sm``.
    communities_ttl : float
        TTL in seconds for community entries (default 600).
    reasoning_ttl : float
        TTL for reasoning result entries (default 300).
    stats_ttl : float
        TTL for graph statistics entries (default 120).
    """

    MODULE_NAME = "graph_intelligence"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        community_engine: Any = None,
        reasoning_engine: Any = None,
        schema_manager: Any = None,
        *,
        communities_ttl: float = 600.0,
        reasoning_ttl: float = 300.0,
        stats_ttl: float = 120.0,
    ) -> None:
        self._community_engine = community_engine
        self._reasoning_engine = reasoning_engine

        # Resolve schema_manager: explicit > extracted from engines
        if schema_manager is not None:
            self._schema_manager = schema_manager
        elif community_engine is not None and hasattr(community_engine, "sm"):
            self._schema_manager = community_engine.sm
        elif reasoning_engine is not None and hasattr(reasoning_engine, "sm"):
            self._schema_manager = reasoning_engine.sm
        else:
            self._schema_manager = None

        self._communities_ttl = communities_ttl
        self._reasoning_ttl = reasoning_ttl
        self._stats_ttl = stats_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change-detection state
        self._last_community_count: Optional[int] = None
        self._last_node_count: Optional[int] = None
        self._last_edge_count: Optional[int] = None

        # Queues populated by consume() / handle_event()
        self._needs_redetection: bool = False
        self._pending_reasoning_requests: List[Dict[str, Any]] = []

    # ── BlackboardParticipant protocol ────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER | ModuleCapability.CONSUMER
            ),
            description=(
                "Graph intelligence: community detection (Louvain / Girvan-Newman), "
                "FastToG community-based reasoning, and graph statistics."
            ),
            topics_produced=frozenset(
                {
                    "graph_intelligence.communities",
                    "graph_intelligence.reasoning",
                    "graph_intelligence.graph_stats",
                }
            ),
            topics_consumed=frozenset(
                {
                    "knowledge_graph",
                    "reasoning",
                    "consciousness",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "GraphIntelligenceAdapter registered (community=%s, reasoning=%s, schema=%s)",
            self._community_engine is not None,
            self._reasoning_engine is not None,
            self._schema_manager is not None,
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
        """Handle incoming events from other modules.

        - ``knowledge_graph.triple.added`` → flag community re-detection
        - ``reasoning.inference.completed`` → queue for graph reasoning
        """
        try:
            if event.event_type.startswith("knowledge_graph."):
                with self._lock:
                    self._needs_redetection = True
                self._emit(
                    "graph_intelligence.graph.updated",
                    {"trigger": event.event_type, "event_id": event.event_id},
                )
            elif event.event_type.startswith("reasoning."):
                with self._lock:
                    self._pending_reasoning_requests.append(event.payload)
        except Exception:
            logger.debug(
                "GraphIntelligenceAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from graph intelligence state.

        Called during a production sweep.  Collects:
        1. Community detection results (if count changed)
        2. Graph statistics (if node/edge count changed)
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            comm_entry = self._produce_communities()
            if comm_entry is not None:
                entries.append(comm_entry)

            stats_entry = self._produce_graph_stats()
            if stats_entry is not None:
                entries.append(stats_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        - ``knowledge_graph.*`` → flag re-detection needed
        - ``reasoning.*``       → queue reasoning request
        - ``consciousness.*``   → note for community prioritisation
        """
        for entry in entries:
            try:
                if entry.topic.startswith("knowledge_graph."):
                    with self._lock:
                        self._needs_redetection = True
                elif entry.topic.startswith("reasoning."):
                    data = entry.data if isinstance(entry.data, dict) else {}
                    with self._lock:
                        self._pending_reasoning_requests.append(data)
                elif entry.topic.startswith("consciousness."):
                    # Note: consciousness broadcasts can be used to prioritise
                    # communities in future iterations.  Currently a no-op.
                    pass
            except Exception:
                logger.debug(
                    "GraphIntelligenceAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_communities(self) -> Optional[BlackboardEntry]:
        """Run community detection and return an entry if the count changed."""
        if self._community_engine is None:
            return None

        try:
            communities = self._community_engine.detect_communities()
        except Exception:
            logger.debug("Community detection failed", exc_info=True)
            return None

        count = len(communities) if communities else 0

        # Change detection: skip if community count unchanged
        if self._last_community_count is not None and count == self._last_community_count:
            return None
        self._last_community_count = count

        # Calculate modularity if available
        modularity = 0.0
        try:
            result = self._community_engine.detect_all_communities()
            modularity = getattr(result, "modularity", 0.0)
        except Exception:
            pass

        entry_data: Dict[str, Any] = {
            "communities": communities,
            "community_count": count,
            "modularity": modularity,
        }

        entry = BlackboardEntry(
            topic="graph_intelligence.communities",
            data=entry_data,
            source_module=self.MODULE_NAME,
            confidence=min(1.0, modularity + 0.3) if modularity > 0 else 0.5,
            priority=EntryPriority.HIGH if count > 0 else EntryPriority.LOW,
            ttl_seconds=self._communities_ttl,
            tags=frozenset({"community_detection", "louvain", "graph"}),
            metadata={"community_count": count, "modularity": modularity},
        )

        self._emit(
            "graph_intelligence.communities.detected",
            {"entry_id": entry.entry_id, "community_count": count, "modularity": modularity},
        )
        return entry

    def _produce_graph_stats(self) -> Optional[BlackboardEntry]:
        """Produce a graph statistics entry if node/edge counts changed."""
        if self._schema_manager is None:
            return None

        try:
            # Attempt common SchemaManager stat-gathering methods
            stats: Dict[str, Any] = {}
            if hasattr(self._schema_manager, "get_statistics"):
                stats = self._schema_manager.get_statistics()
            elif hasattr(self._schema_manager, "get_stats"):
                stats = self._schema_manager.get_stats()
            else:
                # Fall back to counting nodes/edges via find_nodes if available
                node_count = 0
                edge_count = 0
                if hasattr(self._schema_manager, "find_nodes"):
                    nodes = self._schema_manager.find_nodes(limit=0)
                    node_count = len(nodes) if nodes else 0
                stats = {"node_count": node_count, "edge_count": edge_count}
        except Exception:
            logger.debug("Graph stats collection failed", exc_info=True)
            return None

        node_count = stats.get("node_count", stats.get("nodes", 0))
        edge_count = stats.get("edge_count", stats.get("edges", 0))

        # Change detection
        if (
            self._last_node_count is not None
            and self._last_node_count == node_count
            and self._last_edge_count == edge_count
        ):
            return None

        self._last_node_count = node_count
        self._last_edge_count = edge_count

        stats["community_count"] = self._last_community_count or 0

        return BlackboardEntry(
            topic="graph_intelligence.graph_stats",
            data=stats,
            source_module=self.MODULE_NAME,
            confidence=1.0,
            priority=EntryPriority.LOW,
            ttl_seconds=self._stats_ttl,
            tags=frozenset({"statistics", "graph", "snapshot"}),
            metadata={"node_count": node_count, "edge_count": edge_count},
        )

    # ── Convenience ───────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of adapter state for debugging / dashboards."""
        return {
            "module": self.MODULE_NAME,
            "has_community_engine": self._community_engine is not None,
            "has_reasoning_engine": self._reasoning_engine is not None,
            "has_schema_manager": self._schema_manager is not None,
            "last_community_count": self._last_community_count,
            "last_node_count": self._last_node_count,
            "last_edge_count": self._last_edge_count,
            "needs_redetection": self._needs_redetection,
            "pending_reasoning_requests": len(self._pending_reasoning_requests),
            "registered": self._blackboard is not None,
        }
