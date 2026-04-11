"""
Consciousness ↔ Blackboard Adapter
====================================

Bridges the consciousness module (``BaseConsciousness``, ``GlobalWorkspaceTheory``,
``IntegratedInformationTheory``) with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``consciousness.phi``           — IIT Φ values (per-update snapshots)
- ``consciousness.broadcast``     — GWT broadcast events (winning content)
- ``consciousness.state``         — Overall consciousness state snapshot
- ``consciousness.attention``     — Attention focus shifts
- ``consciousness.competition``   — GWT competition results

Topics consumed
~~~~~~~~~~~~~~~
- ``reasoning.*``                 — Reasoning results to feed to workspace
- ``knowledge_graph.*``           — KG triples/pathfinding → sensory input
- ``cognitive_synergy.*``         — Synergy metrics → consciousness state

Events emitted
~~~~~~~~~~~~~~
- ``consciousness.phi.updated``         — New Φ computed
- ``consciousness.broadcast.completed`` — GWT broadcast cycle finished
- ``consciousness.state.changed``       — State transition

Events listened
~~~~~~~~~~~~~~~
- ``reasoning.inference.completed``     — Feed inference into GWT
- ``knowledge_graph.triple.added``      — Feed new triples as sensory input
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

# Lazy imports — the consciousness module may not be available
_consciousness_module = None


def _get_consciousness():
    """Lazy import of consciousness module to allow graceful degradation."""
    global _consciousness_module
    if _consciousness_module is None:
        try:
            from asi_build import consciousness as _cm

            _consciousness_module = _cm
        except (ImportError, ModuleNotFoundError):
            _consciousness_module = False
    return _consciousness_module if _consciousness_module is not False else None


class ConsciousnessAdapter:
    """Adapter connecting the consciousness module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``GlobalWorkspaceTheory`` (GWT) — workspace competition and broadcasting
    - ``IntegratedInformationTheory`` (IIT) — Φ calculation
    - Any ``BaseConsciousness`` subclass — generic consciousness events

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    gwt : optional
        A ``GlobalWorkspaceTheory`` instance.
    iit : optional
        An ``IntegratedInformationTheory`` instance.
    consciousness : optional
        Any ``BaseConsciousness`` subclass instance (may be the same as *gwt*
        or *iit*).
    phi_ttl : float
        TTL in seconds for Φ entries (default 300 = 5 minutes).
    broadcast_ttl : float
        TTL for broadcast entries (default 120 = 2 minutes).
    state_ttl : float
        TTL for state snapshots (default 60 = 1 minute).
    """

    # ── Protocol-required property ────────────────────────────────────
    MODULE_NAME = "consciousness"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        gwt: Any = None,
        iit: Any = None,
        consciousness: Any = None,
        *,
        phi_ttl: float = 300.0,
        broadcast_ttl: float = 120.0,
        state_ttl: float = 60.0,
    ) -> None:
        self._gwt = gwt
        self._iit = iit
        self._consciousness = consciousness
        self._phi_ttl = phi_ttl
        self._broadcast_ttl = broadcast_ttl
        self._state_ttl = state_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Track last values for change detection
        self._last_phi: Optional[float] = None
        self._last_state: Optional[str] = None
        self._broadcast_count: int = 0

    # ── BlackboardParticipant protocol ────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER | ModuleCapability.CONSUMER | ModuleCapability.LEARNER
            ),
            description=(
                "Consciousness module: GWT workspace competition, IIT Φ computation, "
                "attention schema, and state broadcasting."
            ),
            topics_produced=frozenset(
                {
                    "consciousness.phi",
                    "consciousness.broadcast",
                    "consciousness.state",
                    "consciousness.attention",
                    "consciousness.competition",
                }
            ),
            topics_consumed=frozenset(
                {
                    "reasoning",
                    "knowledge_graph",
                    "cognitive_synergy",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "ConsciousnessAdapter registered with blackboard (gwt=%s, iit=%s, base=%s)",
            self._gwt is not None,
            self._iit is not None,
            self._consciousness is not None,
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

        Routes reasoning inferences and KG findings into the GWT workspace
        as new content for competition.
        """
        if self._gwt is None:
            return

        try:
            if event.event_type.startswith("reasoning."):
                self._inject_reasoning_into_gwt(event)
            elif event.event_type.startswith("knowledge_graph."):
                self._inject_kg_into_gwt(event)
        except Exception:
            logger.debug(
                "ConsciousnessAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current consciousness state.

        Called during a production sweep.  Collects:
        1. Latest Φ value from IIT
        2. Latest GWT broadcast content
        3. Overall consciousness state snapshot
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            phi_entry = self._produce_phi()
            if phi_entry is not None:
                entries.append(phi_entry)

            broadcast_entry = self._produce_broadcast()
            if broadcast_entry is not None:
                entries.append(broadcast_entry)

            state_entry = self._produce_state()
            if state_entry is not None:
                entries.append(state_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        Reasoning results → feed into GWT workspace for competition.
        KG triples → used as sensory input for consciousness processing.
        Synergy metrics → modulate attention weights.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
                elif entry.topic.startswith("knowledge_graph."):
                    self._consume_kg(entry)
                elif entry.topic.startswith("cognitive_synergy."):
                    self._consume_synergy(entry)
            except Exception:
                logger.debug(
                    "ConsciousnessAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_phi(self) -> Optional[BlackboardEntry]:
        """Compute Φ and return an entry if the value changed."""
        if self._iit is None:
            return None

        try:
            phi = self._iit.calculate_phi()
        except Exception:
            logger.debug("IIT calculate_phi() failed", exc_info=True)
            return None

        # Only post if Φ changed significantly (>1% relative or absolute >0.01)
        if self._last_phi is not None:
            delta = abs(phi - self._last_phi)
            if delta < 0.01 and (
                self._last_phi == 0 or delta / max(abs(self._last_phi), 1e-9) < 0.01
            ):
                return None

        self._last_phi = phi

        # Gather extra IIT context
        metadata: Dict[str, Any] = {"phi": phi}
        try:
            complexes = self._iit.find_conscious_complexes()
            metadata["complexes_count"] = len(complexes)
            if complexes:
                metadata["max_complex_phi"] = max(c.phi_value for c in complexes)
        except Exception:
            pass

        entry = BlackboardEntry(
            topic="consciousness.phi",
            data=metadata,
            source_module=self.MODULE_NAME,
            confidence=min(1.0, phi / 5.0),  # Normalize: Φ=5 → confidence=1.0
            priority=EntryPriority.HIGH if phi > 3.0 else EntryPriority.NORMAL,
            ttl_seconds=self._phi_ttl,
            tags=frozenset({"iit", "phi", "integration"}),
            metadata={"phi_value": phi},
        )

        self._emit("consciousness.phi.updated", {"phi": phi, "entry_id": entry.entry_id})
        return entry

    def _produce_broadcast(self) -> Optional[BlackboardEntry]:
        """Capture latest GWT broadcast and return an entry."""
        if self._gwt is None:
            return None

        try:
            broadcast = self._gwt.current_broadcast
        except AttributeError:
            return None

        if broadcast is None:
            return None

        # Check if it's a new broadcast
        current_count = getattr(self._gwt, "total_broadcasts", 0)
        if current_count <= self._broadcast_count:
            return None
        self._broadcast_count = current_count

        try:
            broadcast_data = {
                "content_id": getattr(broadcast, "content_id", None)
                or getattr(broadcast.content, "content_id", "unknown"),
                "broadcast_strength": getattr(broadcast, "strength", 0.0),
                "processors_reached": getattr(broadcast, "processors_reached", 0),
                "timestamp": getattr(broadcast, "timestamp", time.time()),
            }
            # Include content data if available
            content = getattr(broadcast, "content", broadcast)
            if hasattr(content, "data"):
                broadcast_data["content_data"] = content.data
            if hasattr(content, "source"):
                broadcast_data["content_source"] = content.source
        except Exception:
            broadcast_data = {"broadcast_count": current_count}

        entry = BlackboardEntry(
            topic="consciousness.broadcast",
            data=broadcast_data,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.HIGH,
            ttl_seconds=self._broadcast_ttl,
            tags=frozenset({"gwt", "broadcast", "global_workspace"}),
        )

        self._emit(
            "consciousness.broadcast.completed",
            {
                "entry_id": entry.entry_id,
                "broadcast_count": current_count,
            },
        )
        return entry

    def _produce_state(self) -> Optional[BlackboardEntry]:
        """Snapshot overall consciousness state."""
        source = self._consciousness or self._gwt or self._iit
        if source is None:
            return None

        try:
            state_data = source.get_current_state()
        except Exception:
            return None

        # Detect state name change
        state_name = str(state_data.get("state", state_data.get("consciousness_state", "")))
        if state_name == self._last_state:
            return None  # No state transition
        self._last_state = state_name

        entry = BlackboardEntry(
            topic="consciousness.state",
            data=state_data,
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._state_ttl,
            tags=frozenset({"state", "snapshot"}),
            metadata={"state_name": state_name},
        )

        self._emit(
            "consciousness.state.changed",
            {
                "new_state": state_name,
                "entry_id": entry.entry_id,
            },
        )
        return entry

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Feed reasoning results into GWT workspace."""
        if self._gwt is None:
            return
        self._submit_to_gwt(
            content_type="reasoning",
            data=entry.data,
            activation=entry.confidence * 0.8,
            source=f"reasoning:{entry.entry_id}",
        )

    def _consume_kg(self, entry: BlackboardEntry) -> None:
        """Feed KG findings into GWT as sensory input."""
        if self._gwt is None:
            return
        self._submit_to_gwt(
            content_type="knowledge",
            data=entry.data,
            activation=entry.confidence * 0.6,
            source=f"kg:{entry.entry_id}",
        )

    def _consume_synergy(self, entry: BlackboardEntry) -> None:
        """Modulate attention weights based on synergy metrics."""
        if self._gwt is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        coherence = data.get("global_coherence", data.get("coherence", None))
        if coherence is not None and hasattr(self._gwt, "attention_focus"):
            try:
                self._gwt.attention_focus["synergy_coherence"] = float(coherence)
            except (TypeError, ValueError):
                pass

    # ── Event→GWT injection ───────────────────────────────────────────

    def _inject_reasoning_into_gwt(self, event: CognitiveEvent) -> None:
        """Convert a reasoning event into GWT workspace content."""
        self._submit_to_gwt(
            content_type="reasoning_event",
            data=event.payload,
            activation=0.7,
            source=f"event:{event.event_id}",
        )

    def _inject_kg_into_gwt(self, event: CognitiveEvent) -> None:
        """Convert a KG event into GWT workspace content."""
        self._submit_to_gwt(
            content_type="kg_event",
            data=event.payload,
            activation=0.5,
            source=f"event:{event.event_id}",
        )

    def _submit_to_gwt(
        self,
        content_type: str,
        data: Any,
        activation: float = 0.5,
        source: str = "",
    ) -> None:
        """Submit content to the GWT workspace buffer.

        Creates a ``WorkspaceContent`` if the class is available, otherwise
        uses the raw ``submit_content`` interface.
        """
        cm = _get_consciousness()
        if cm is None or self._gwt is None:
            return

        WorkspaceContent = getattr(cm, "WorkspaceContent", None)
        if WorkspaceContent is None:
            # Try direct import from submodule
            try:
                from asi_build.consciousness.global_workspace import WorkspaceContent as _WC

                WorkspaceContent = _WC
            except (ImportError, AttributeError):
                return

        try:
            content = WorkspaceContent(
                content_id=f"bb_{content_type}_{time.time_ns()}",
                content_type=content_type,
                data=data,
                source=source,
                activation_level=activation,
            )
            self._gwt.submit_content(content)
        except Exception:
            logger.debug("Failed to submit content to GWT", exc_info=True)

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all consciousness components.

        Useful for debugging and dashboard display.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_gwt": self._gwt is not None,
            "has_iit": self._iit is not None,
            "has_base": self._consciousness is not None,
            "last_phi": self._last_phi,
            "broadcast_count": self._broadcast_count,
            "last_state": self._last_state,
            "registered": self._blackboard is not None,
        }

        if self._iit is not None:
            try:
                snap["current_phi"] = self._iit.calculate_phi()
            except Exception:
                snap["current_phi"] = None

        if self._gwt is not None:
            try:
                snap["workspace_size"] = len(getattr(self._gwt, "workspace_buffer", []))
                snap["processors"] = len(getattr(self._gwt, "cognitive_processors", {}))
            except Exception:
                pass

        return snap
