"""
Holographic ↔ Blackboard Adapter
==================================

Bridges the holographic module (``HolographicEngine``, ``LightFieldProcessor``,
``VolumetricDisplay``) with the Cognitive Blackboard.

The holographic subsystem renders 3-D visualisations of cognitive state — Bloch
spheres for quantum data, knowledge-graph force layouts, and consciousness
attention maps.  This adapter exposes engine telemetry as blackboard entries
and consumes data from other modules to drive the rendering pipeline.

Topics produced
~~~~~~~~~~~~~~~
- ``holographic.engine.status``       — Engine state, FPS, frame count, uptime
- ``holographic.engine.performance``  — Detailed performance metrics (fps, frame
                                        time, memory, GPU utilisation)
- ``holographic.lightfield.capture``  — Light-field capture events (count, stats)
- ``holographic.display.render``      — Volumetric display render statistics

Topics consumed
~~~~~~~~~~~~~~~
- ``consciousness.*``     — Consciousness state → visualisation updates
- ``knowledge_graph.*``   — KG triples / pathfinding → graph rendering
- ``quantum.*``           — Quantum state → Bloch-sphere / state visualisation

Events emitted
~~~~~~~~~~~~~~
- ``holographic.engine.state_changed``    — Engine state transition
- ``holographic.engine.fps_changed``      — Significant FPS change (>5 %)
- ``holographic.lightfield.captured``     — New light-field capture completed
- ``holographic.display.rendered``        — New volumetric render frame

Events listened
~~~~~~~~~~~~~~~
- ``consciousness.*``     — Trigger consciousness visualisation refresh
- ``knowledge_graph.*``   — Trigger graph render update
- ``quantum.*``           — Trigger quantum-state visualisation
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

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

# ---------------------------------------------------------------------------
# Lazy module import — holographic may not be installed
# ---------------------------------------------------------------------------

_holographic_module = None


def _get_holographic():
    """Lazy import of holographic module to allow graceful degradation."""
    global _holographic_module
    if _holographic_module is None:
        try:
            from asi_build import holographic as _hm

            _holographic_module = _hm
        except (ImportError, ModuleNotFoundError):
            _holographic_module = False
    return _holographic_module if _holographic_module is not False else None


class HolographicBlackboardAdapter:
    """Adapter connecting the holographic module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``HolographicEngine``   — core rendering engine with start/stop lifecycle,
      FPS tracking, and callback registration.
    - ``LightFieldProcessor`` — light-field capture, view synthesis, depth-map
      estimation, and refocusing.
    - ``VolumetricDisplay``   — layered voxel display with per-layer depth and
      resolution, plus a ``render()`` pipeline.

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    engine : optional
        A ``HolographicEngine`` instance.
    light_field : optional
        A ``LightFieldProcessor`` instance.
    display : optional
        A ``VolumetricDisplay`` instance.
    status_ttl : float
        TTL in seconds for engine-status entries (default 120 = 2 min).
    performance_ttl : float
        TTL for engine-performance entries (default 60 = 1 min).
    capture_ttl : float
        TTL for light-field capture entries (default 300 = 5 min).
    render_ttl : float
        TTL for volumetric-render entries (default 60 = 1 min).
    """

    # ── Protocol-required class attributes ────────────────────────────
    MODULE_NAME = "holographic"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        engine: Any = None,
        light_field: Any = None,
        display: Any = None,
        *,
        status_ttl: float = 120.0,
        performance_ttl: float = 60.0,
        capture_ttl: float = 300.0,
        render_ttl: float = 60.0,
    ) -> None:
        self._engine = engine
        self._light_field = light_field
        self._display = display

        self._status_ttl = status_ttl
        self._performance_ttl = performance_ttl
        self._capture_ttl = capture_ttl
        self._render_ttl = render_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # ── Change-detection state ────────────────────────────────────
        self._last_engine_state: Optional[str] = None
        self._last_frame_count: int = 0
        self._last_fps: Optional[float] = None
        self._capture_count: int = 0
        self._render_count: int = 0

        # ── Visualisation queues (populated by consumers) ─────────────
        self._pending_consciousness_updates: List[Dict[str, Any]] = []
        self._pending_kg_updates: List[Dict[str, Any]] = []
        self._pending_quantum_updates: List[Dict[str, Any]] = []

    # ── BlackboardParticipant protocol ────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        """Return metadata about the holographic module."""
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER | ModuleCapability.CONSUMER
            ),
            description=(
                "Holographic subsystem: 3-D engine telemetry, light-field "
                "capture, and volumetric display rendering.  Consumes "
                "consciousness, knowledge-graph, and quantum data for "
                "interactive visualisation."
            ),
            topics_produced=frozenset(
                {
                    "holographic.engine.status",
                    "holographic.engine.performance",
                    "holographic.lightfield.capture",
                    "holographic.display.render",
                }
            ),
            topics_consumed=frozenset(
                {
                    "consciousness",
                    "knowledge_graph",
                    "quantum",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "HolographicAdapter registered with blackboard "
            "(engine=%s, light_field=%s, display=%s)",
            self._engine is not None,
            self._light_field is not None,
            self._display is not None,
        )

    # ── EventEmitter protocol ─────────────────────────────────────────

    def set_event_handler(self, handler: EventHandler) -> None:
        """Inject the event-emission callback (typically ``EventBus.emit``)."""
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

        Routes events by prefix to the appropriate visualisation-update
        handler so the holographic engine can render them on the next frame.
        """
        try:
            if event.event_type.startswith("consciousness."):
                self._handle_consciousness_event(event)
            elif event.event_type.startswith("knowledge_graph."):
                self._handle_kg_event(event)
            elif event.event_type.startswith("quantum."):
                self._handle_quantum_event(event)
        except Exception:
            logger.debug(
                "HolographicAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current holographic state.

        Called during a production sweep.  Collects:

        1. Engine status (state, FPS, frame count, uptime)
        2. Engine performance metrics (fps, frame time, memory, GPU)
        3. Light-field capture count and statistics
        4. Volumetric display render statistics
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            status = self._produce_engine_status()
            if status is not None:
                entries.append(status)

            perf = self._produce_engine_performance()
            if perf is not None:
                entries.append(perf)

            capture = self._produce_lightfield_capture()
            if capture is not None:
                entries.append(capture)

            render = self._produce_display_render()
            if render is not None:
                entries.append(render)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        - ``consciousness.*`` → consciousness-state visualisation updates
        - ``knowledge_graph.*`` → graph-layout render commands
        - ``quantum.*`` → Bloch-sphere / state-vector visualisation
        """
        for entry in entries:
            try:
                if entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
                elif entry.topic.startswith("knowledge_graph."):
                    self._consume_kg(entry)
                elif entry.topic.startswith("quantum."):
                    self._consume_quantum(entry)
            except Exception:
                logger.debug(
                    "HolographicAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_engine_status(self) -> Optional[BlackboardEntry]:
        """Read engine status and return an entry if state or frame_count changed."""
        if self._engine is None:
            return None

        try:
            status = self._engine.get_status()
        except Exception:
            logger.debug("HolographicEngine get_status() failed", exc_info=True)
            return None

        if not isinstance(status, dict):
            return None

        current_state = str(status.get("state", ""))
        current_frame_count = int(status.get("frame_count", 0))

        # Change detection: state transition OR new frames rendered
        if (
            current_state == self._last_engine_state
            and current_frame_count == self._last_frame_count
        ):
            return None

        state_changed = current_state != self._last_engine_state
        self._last_engine_state = current_state
        self._last_frame_count = current_frame_count

        entry = BlackboardEntry(
            topic="holographic.engine.status",
            data={
                "state": current_state,
                "fps": status.get("fps", 0.0),
                "frame_count": current_frame_count,
                "uptime": status.get("uptime", 0.0),
                "components": status.get("components", {}),
            },
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=(
                EntryPriority.HIGH if state_changed else EntryPriority.NORMAL
            ),
            ttl_seconds=self._status_ttl,
            tags=frozenset({"engine", "status", "holographic"}),
            metadata={
                "engine_state": current_state,
                "state_changed": state_changed,
            },
        )

        if state_changed:
            self._emit(
                "holographic.engine.state_changed",
                {
                    "new_state": current_state,
                    "frame_count": current_frame_count,
                    "entry_id": entry.entry_id,
                },
            )

        return entry

    def _produce_engine_performance(self) -> Optional[BlackboardEntry]:
        """Read engine performance metrics; post if FPS changed >5 %."""
        if self._engine is None:
            return None

        try:
            metrics = self._engine.get_performance_metrics()
        except Exception:
            logger.debug(
                "HolographicEngine get_performance_metrics() failed",
                exc_info=True,
            )
            return None

        if not isinstance(metrics, dict):
            return None

        current_fps = float(metrics.get("fps", 0.0))

        # Change detection: >5 % relative FPS change (or first reading)
        if self._last_fps is not None and self._last_fps > 0:
            delta_ratio = abs(current_fps - self._last_fps) / self._last_fps
            if delta_ratio < 0.05:
                return None
        elif self._last_fps is not None and current_fps == 0:
            # Both zero → no change
            return None

        self._last_fps = current_fps

        entry = BlackboardEntry(
            topic="holographic.engine.performance",
            data={
                "fps": current_fps,
                "frame_time": metrics.get("frame_time", 0.0),
                "memory": metrics.get("memory", 0.0),
                "gpu": metrics.get("gpu", 0.0),
            },
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=(
                EntryPriority.HIGH
                if current_fps < 10.0
                else EntryPriority.NORMAL
            ),
            ttl_seconds=self._performance_ttl,
            tags=frozenset({"engine", "performance", "holographic", "metrics"}),
            metadata={"fps": current_fps},
        )

        self._emit(
            "holographic.engine.fps_changed",
            {
                "fps": current_fps,
                "frame_time": metrics.get("frame_time", 0.0),
                "entry_id": entry.entry_id,
            },
        )

        return entry

    def _produce_lightfield_capture(self) -> Optional[BlackboardEntry]:
        """Report new light-field captures since last sweep."""
        if self._light_field is None:
            return None

        try:
            stats = self._light_field.get_performance_stats()
        except Exception:
            logger.debug(
                "LightFieldProcessor get_performance_stats() failed",
                exc_info=True,
            )
            return None

        if not isinstance(stats, dict):
            return None

        # Track captures via stats dict — look for a counter key
        current_count = int(
            stats.get("capture_count", stats.get("total_captures", 0))
        )
        if current_count <= self._capture_count:
            return None  # No new captures

        new_captures = current_count - self._capture_count
        self._capture_count = current_count

        entry = BlackboardEntry(
            topic="holographic.lightfield.capture",
            data={
                "capture_count": current_count,
                "new_captures": new_captures,
                "stats": stats,
            },
            source_module=self.MODULE_NAME,
            confidence=0.85,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._capture_ttl,
            tags=frozenset({"lightfield", "capture", "holographic"}),
            metadata={"capture_count": current_count},
        )

        self._emit(
            "holographic.lightfield.captured",
            {
                "capture_count": current_count,
                "new_captures": new_captures,
                "entry_id": entry.entry_id,
            },
        )

        return entry

    def _produce_display_render(self) -> Optional[BlackboardEntry]:
        """Report volumetric display render statistics if changed."""
        if self._display is None:
            return None

        try:
            stats = self._display.get_performance_stats()
        except Exception:
            logger.debug(
                "VolumetricDisplay get_performance_stats() failed",
                exc_info=True,
            )
            return None

        if not isinstance(stats, dict):
            return None

        current_count = int(
            stats.get("render_count", stats.get("total_renders", 0))
        )
        if current_count <= self._render_count:
            return None  # No new renders

        new_renders = current_count - self._render_count
        self._render_count = current_count

        entry = BlackboardEntry(
            topic="holographic.display.render",
            data={
                "render_count": current_count,
                "new_renders": new_renders,
                "stats": stats,
            },
            source_module=self.MODULE_NAME,
            confidence=0.85,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._render_ttl,
            tags=frozenset({"display", "render", "holographic", "volumetric"}),
            metadata={"render_count": current_count},
        )

        self._emit(
            "holographic.display.rendered",
            {
                "render_count": current_count,
                "new_renders": new_renders,
                "entry_id": entry.entry_id,
            },
        )

        return entry

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Translate consciousness state into holographic visualisation commands.

        Consciousness data is converted into a colour-mapped attention overlay
        on the volumetric display.  If the engine exposes an update callback,
        it is invoked directly; otherwise the update is queued for the next
        render sweep.
        """
        data = entry.data if isinstance(entry.data, dict) else {}

        viz_update: Dict[str, Any] = {
            "type": "consciousness",
            "topic": entry.topic,
            "timestamp": entry.timestamp,
        }

        # Extract the most useful fields for visualisation
        if "phi" in data:
            viz_update["phi"] = float(data["phi"])
            viz_update["viz_mode"] = "phi_heatmap"
        elif entry.topic.endswith(".broadcast"):
            viz_update["broadcast_strength"] = data.get("broadcast_strength", 0.0)
            viz_update["viz_mode"] = "broadcast_pulse"
        elif entry.topic.endswith(".state"):
            viz_update["state_name"] = data.get("state", data.get("consciousness_state", ""))
            viz_update["viz_mode"] = "state_overlay"
        elif entry.topic.endswith(".attention"):
            viz_update["attention"] = data
            viz_update["viz_mode"] = "attention_spotlight"
        else:
            viz_update["raw"] = data
            viz_update["viz_mode"] = "generic"

        self._pending_consciousness_updates.append(viz_update)
        self._push_visualization_update(viz_update)

    def _consume_kg(self, entry: BlackboardEntry) -> None:
        """Translate knowledge-graph data into 3-D graph-layout commands.

        KG triples become nodes and edges in a force-directed layout rendered
        by the volumetric display.  Pathfinding results are highlighted as
        luminous paths through the graph.
        """
        data = entry.data if isinstance(entry.data, dict) else {}

        viz_update: Dict[str, Any] = {
            "type": "knowledge_graph",
            "topic": entry.topic,
            "timestamp": entry.timestamp,
        }

        if entry.topic.endswith(".triple"):
            viz_update["viz_mode"] = "graph_edge"
            viz_update["subject"] = data.get("subject")
            viz_update["predicate"] = data.get("predicate")
            viz_update["object"] = data.get("object")
        elif entry.topic.endswith(".pathfinding"):
            viz_update["viz_mode"] = "path_highlight"
            viz_update["path"] = data.get("path", [])
        elif entry.topic.endswith(".contradiction"):
            viz_update["viz_mode"] = "conflict_marker"
            viz_update["entities"] = data.get("entities", [])
        else:
            viz_update["viz_mode"] = "graph_generic"
            viz_update["raw"] = data

        self._pending_kg_updates.append(viz_update)
        self._push_visualization_update(viz_update)

    def _consume_quantum(self, entry: BlackboardEntry) -> None:
        """Translate quantum state data into Bloch-sphere visualisation commands.

        Qubit states are rendered as points on the Bloch sphere; multi-qubit
        states use a density-matrix colour-map.  Entanglement links are shown
        as glowing connections between qubit representations.
        """
        data = entry.data if isinstance(entry.data, dict) else {}

        viz_update: Dict[str, Any] = {
            "type": "quantum",
            "topic": entry.topic,
            "timestamp": entry.timestamp,
        }

        # Detect the kind of quantum data
        if "state_vector" in data or "amplitudes" in data:
            viz_update["viz_mode"] = "bloch_sphere"
            viz_update["state_vector"] = data.get(
                "state_vector", data.get("amplitudes")
            )
        elif "density_matrix" in data:
            viz_update["viz_mode"] = "density_matrix"
            viz_update["density_matrix"] = data["density_matrix"]
        elif "entanglement" in data or "concurrence" in data:
            viz_update["viz_mode"] = "entanglement_links"
            viz_update["entanglement"] = data.get(
                "entanglement", data.get("concurrence")
            )
        elif "gate" in data or "circuit" in data:
            viz_update["viz_mode"] = "circuit_diagram"
            viz_update["circuit"] = data.get("circuit", data.get("gate"))
        else:
            viz_update["viz_mode"] = "quantum_generic"
            viz_update["raw"] = data

        self._pending_quantum_updates.append(viz_update)
        self._push_visualization_update(viz_update)

    # ── Event → visualisation routing ─────────────────────────────────

    def _handle_consciousness_event(self, event: CognitiveEvent) -> None:
        """Route consciousness events to the visualisation pipeline."""
        self._push_visualization_update(
            {
                "type": "consciousness_event",
                "event_type": event.event_type,
                "payload": event.payload,
                "viz_mode": "consciousness_refresh",
            }
        )

    def _handle_kg_event(self, event: CognitiveEvent) -> None:
        """Route knowledge-graph events to the graph renderer."""
        self._push_visualization_update(
            {
                "type": "kg_event",
                "event_type": event.event_type,
                "payload": event.payload,
                "viz_mode": "graph_refresh",
            }
        )

    def _handle_quantum_event(self, event: CognitiveEvent) -> None:
        """Route quantum events to the Bloch-sphere / state renderer."""
        self._push_visualization_update(
            {
                "type": "quantum_event",
                "event_type": event.event_type,
                "payload": event.payload,
                "viz_mode": "quantum_refresh",
            }
        )

    # ── Internal helpers ──────────────────────────────────────────────

    def _push_visualization_update(self, update: Dict[str, Any]) -> None:
        """Push a visualisation update to the engine via its update callback.

        If the engine is unavailable or lacks the callback, the update is
        silently ignored (it remains in the pending queues for later retrieval
        via :meth:`snapshot`).
        """
        if self._engine is None:
            return

        try:
            # Try the registered update callback first
            if hasattr(self._engine, "add_update_callback"):
                # Engines that accept a single data dict
                callbacks = getattr(self._engine, "_update_callbacks", None)
                if callbacks:
                    for cb in callbacks:
                        try:
                            cb(update)
                        except Exception:
                            logger.debug(
                                "Holographic update callback failed",
                                exc_info=True,
                            )
        except Exception:
            logger.debug(
                "HolographicAdapter: failed to push viz update", exc_info=True
            )

    # ── Convenience: diagnostic snapshot ──────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all holographic components.

        Useful for debugging, dashboard display, and health checks.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_engine": self._engine is not None,
            "has_light_field": self._light_field is not None,
            "has_display": self._display is not None,
            "registered": self._blackboard is not None,
            "last_engine_state": self._last_engine_state,
            "last_frame_count": self._last_frame_count,
            "last_fps": self._last_fps,
            "capture_count": self._capture_count,
            "render_count": self._render_count,
            "pending_consciousness_updates": len(self._pending_consciousness_updates),
            "pending_kg_updates": len(self._pending_kg_updates),
            "pending_quantum_updates": len(self._pending_quantum_updates),
        }

        if self._engine is not None:
            try:
                snap["engine_status"] = self._engine.get_status()
            except Exception:
                snap["engine_status"] = None

            try:
                snap["engine_performance"] = self._engine.get_performance_metrics()
            except Exception:
                snap["engine_performance"] = None

        if self._light_field is not None:
            try:
                snap["lightfield_stats"] = self._light_field.get_performance_stats()
            except Exception:
                snap["lightfield_stats"] = None

        if self._display is not None:
            try:
                snap["display_stats"] = self._display.get_performance_stats()
            except Exception:
                snap["display_stats"] = None

        return snap
