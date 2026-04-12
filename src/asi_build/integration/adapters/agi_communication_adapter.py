"""
AGI Communication ↔ Blackboard Adapter
========================================

Bridges the AGI Communication module (``AGICommunicationProtocol``,
``GoalNegotiationProtocol``, ``CollaborativeProblemSolver``,
``SemanticInteroperabilityLayer``, ``KnowledgeGraphMerger``) with the
Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``agi_comm.session.status``         — Communication session lifecycle events
- ``agi_comm.message.received``       — Incoming message events
- ``agi_comm.negotiation.status``     — Negotiation session state & proposals
- ``agi_comm.negotiation.analysis``   — Nash equilibria, Pareto fronts, Shapley values
- ``agi_comm.collaboration.status``   — Collaboration session state & task assignments
- ``agi_comm.collaboration.solution`` — Solutions submitted and validated
- ``agi_comm.translation.result``     — Semantic translation results
- ``agi_comm.knowledge.merge``        — KG merge results, conflicts, confidence

Topics consumed
~~~~~~~~~~~~~~~
- ``reasoning.*``           — Reasoning results for collaborative problem solving
- ``knowledge_graph.*``     — KG data for cross-AGI merging
- ``consciousness.*``       — Consciousness state for communication priority
- ``cognitive_synergy.*``   — Synergy metrics for collaboration efficiency

Events emitted
~~~~~~~~~~~~~~
- ``agi_comm.session.opened``                — New session established
- ``agi_comm.session.closed``                — Session terminated
- ``agi_comm.negotiation.completed``         — Negotiation reached agreement
- ``agi_comm.collaboration.solution.found``  — Collaboration produced a solution
- ``agi_comm.knowledge.merge.completed``     — KG merge finished

Events listened
~~~~~~~~~~~~~~~
- ``reasoning.inference.completed``          — Feed into collaborative solving
- ``knowledge_graph.triple.added``           — Trigger KG merge evaluation
- ``consciousness.state.changed``            — Adjust communication priority
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
# Lazy import — the agi_communication module may not be available
# ---------------------------------------------------------------------------
_agi_comm_module = None


def _get_agi_comm():
    """Lazy import of agi_communication module for graceful degradation."""
    global _agi_comm_module
    if _agi_comm_module is None:
        try:
            from asi_build import agi_communication as _acm

            _agi_comm_module = _acm
        except (ImportError, ModuleNotFoundError):
            _agi_comm_module = False
    return _agi_comm_module if _agi_comm_module is not False else None


class AGICommunicationBlackboardAdapter:
    """Adapter connecting the AGI Communication module to the Cognitive Blackboard.

    Wraps up to five components:

    - ``AGICommunicationProtocol`` — inter-AGI session management and messaging
    - ``GoalNegotiationProtocol`` — multi-agent goal negotiation with game theory
    - ``CollaborativeProblemSolver`` — collaborative problem decomposition & solving
    - ``SemanticInteroperabilityLayer`` — knowledge representation translation
    - ``KnowledgeGraphMerger`` — cross-AGI knowledge graph merging

    All components are optional; the adapter gracefully skips operations for
    any component that is ``None``.

    Parameters
    ----------
    protocol : optional
        An ``AGICommunicationProtocol`` instance.
    negotiation : optional
        A ``GoalNegotiationProtocol`` instance.
    collaboration : optional
        A ``CollaborativeProblemSolver`` instance.
    semantic : optional
        A ``SemanticInteroperabilityLayer`` instance.
    kg_merger : optional
        A ``KnowledgeGraphMerger`` instance.
    session_ttl : float
        TTL in seconds for session entries (default 120).
    message_ttl : float
        TTL for message entries (default 60).
    negotiation_ttl : float
        TTL for negotiation entries (default 300).
    collaboration_ttl : float
        TTL for collaboration entries (default 300).
    translation_ttl : float
        TTL for translation entries (default 180).
    merge_ttl : float
        TTL for merge entries (default 600).
    """

    MODULE_NAME = "agi_communication"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        protocol: Any = None,
        negotiation: Any = None,
        collaboration: Any = None,
        semantic: Any = None,
        kg_merger: Any = None,
        *,
        session_ttl: float = 120.0,
        message_ttl: float = 60.0,
        negotiation_ttl: float = 300.0,
        collaboration_ttl: float = 300.0,
        translation_ttl: float = 180.0,
        merge_ttl: float = 600.0,
    ) -> None:
        self._protocol = protocol
        self._negotiation = negotiation
        self._collaboration = collaboration
        self._semantic = semantic
        self._kg_merger = kg_merger

        self._session_ttl = session_ttl
        self._message_ttl = message_ttl
        self._negotiation_ttl = negotiation_ttl
        self._collaboration_ttl = collaboration_ttl
        self._translation_ttl = translation_ttl
        self._merge_ttl = merge_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change-detection state
        self._last_session_count: int = 0
        self._last_message_count: int = 0
        self._last_negotiation_stats: Optional[Dict[str, Any]] = None
        self._last_collaboration_stats: Optional[Dict[str, Any]] = None
        self._last_translation_count: int = 0
        self._last_merge_count: int = 0

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
                | ModuleCapability.REASONER
            ),
            description=(
                "AGI Communication module: inter-AGI messaging, goal negotiation "
                "with game theory, collaborative problem solving, semantic "
                "interoperability, and knowledge graph merging."
            ),
            topics_produced=frozenset(
                {
                    "agi_comm.session.status",
                    "agi_comm.message.received",
                    "agi_comm.negotiation.status",
                    "agi_comm.negotiation.analysis",
                    "agi_comm.collaboration.status",
                    "agi_comm.collaboration.solution",
                    "agi_comm.translation.result",
                    "agi_comm.knowledge.merge",
                }
            ),
            topics_consumed=frozenset(
                {
                    "reasoning",
                    "knowledge_graph",
                    "consciousness",
                    "cognitive_synergy",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "AGICommunicationBlackboardAdapter registered with blackboard "
            "(protocol=%s, negotiation=%s, collaboration=%s, semantic=%s, kg_merger=%s)",
            self._protocol is not None,
            self._negotiation is not None,
            self._collaboration is not None,
            self._semantic is not None,
            self._kg_merger is not None,
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

        Routes reasoning completions into collaborative solving contexts,
        KG additions into merge pipelines, and consciousness state changes
        into communication priority adjustments.
        """
        try:
            if event.event_type.startswith("reasoning."):
                self._handle_reasoning_event(event)
            elif event.event_type.startswith("knowledge_graph."):
                self._handle_kg_event(event)
            elif event.event_type.startswith("consciousness."):
                self._handle_consciousness_event(event)
        except Exception:
            logger.debug(
                "AGICommunicationAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current communication state.

        Called during a production sweep.  Collects:
        1. Session lifecycle status from protocol
        2. Negotiation status and game-theory analysis
        3. Collaboration status and solutions
        4. Translation statistics
        5. KG merge results
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            session_entries = self._produce_sessions()
            entries.extend(session_entries)

            negotiation_entries = self._produce_negotiations()
            entries.extend(negotiation_entries)

            collaboration_entries = self._produce_collaborations()
            entries.extend(collaboration_entries)

            merge_entry = self._produce_merge()
            if merge_entry is not None:
                entries.append(merge_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        - ``reasoning.*``         — Feed into collaborative problem solving
        - ``knowledge_graph.*``   — Trigger KG merge evaluation
        - ``consciousness.*``     — Adjust communication priority
        - ``cognitive_synergy.*`` — Update collaboration efficiency params
        """
        for entry in entries:
            try:
                if entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
                elif entry.topic.startswith("knowledge_graph."):
                    self._consume_kg(entry)
                elif entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
                elif entry.topic.startswith("cognitive_synergy."):
                    self._consume_synergy(entry)
            except Exception:
                logger.debug(
                    "AGICommunicationAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── BlackboardTransformer protocol ────────────────────────────────

    def transform(self, entries: Sequence[BlackboardEntry]) -> Sequence[BlackboardEntry]:
        """Enrich entries with AGI communication context.

        Adds active session count, negotiation state, and semantic
        translation metadata to entries passing through this adapter.
        """
        if self._protocol is None and self._semantic is None:
            return entries

        enriched: List[BlackboardEntry] = []
        for entry in entries:
            try:
                metadata = dict(entry.metadata) if entry.metadata else {}

                # Add communication context
                if self._protocol is not None:
                    try:
                        sessions = self._protocol.get_active_sessions()
                        metadata["agi_comm_active_sessions"] = len(sessions)
                    except Exception:
                        pass

                # Add negotiation context if relevant
                if self._negotiation is not None and entry.topic.startswith("reasoning."):
                    try:
                        neg_stats = self._negotiation.get_negotiation_statistics()
                        metadata["agi_comm_active_negotiations"] = neg_stats.get(
                            "active_negotiations", 0
                        )
                    except Exception:
                        pass

                enriched.append(
                    BlackboardEntry(
                        topic=entry.topic,
                        data=entry.data,
                        source_module=entry.source_module,
                        confidence=entry.confidence,
                        priority=entry.priority,
                        ttl_seconds=entry.ttl_seconds,
                        tags=entry.tags,
                        metadata=metadata,
                    )
                )
            except Exception:
                enriched.append(entry)

        return enriched

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_sessions(self) -> List[BlackboardEntry]:
        """Produce session status and message entries from the protocol."""
        if self._protocol is None:
            return []

        entries: List[BlackboardEntry] = []

        # Session status
        try:
            stats = self._protocol.get_communication_stats()
            active = stats.get("active_sessions", 0)
            total = stats.get("total_sessions", 0)

            if total != self._last_session_count:
                self._last_session_count = total

                entry = BlackboardEntry(
                    topic="agi_comm.session.status",
                    data={
                        "active_sessions": active,
                        "total_sessions": total,
                        "messages_sent": stats.get("messages_sent", 0),
                        "messages_received": stats.get("messages_received", 0),
                        "avg_latency": stats.get("avg_latency", 0.0),
                    },
                    source_module=self.MODULE_NAME,
                    confidence=0.95,
                    priority=EntryPriority.NORMAL,
                    ttl_seconds=self._session_ttl,
                    tags=frozenset({"session", "status", "communication"}),
                    metadata={"active_sessions": active},
                )
                entries.append(entry)

                if active > 0:
                    self._emit(
                        "agi_comm.session.opened",
                        {"active_sessions": active, "entry_id": entry.entry_id},
                    )
        except Exception:
            logger.debug("Failed to produce session status", exc_info=True)

        # Message received events
        try:
            msg_count = stats.get("messages_received", 0)
            if msg_count > self._last_message_count and msg_count > 0:
                new_messages = msg_count - self._last_message_count
                self._last_message_count = msg_count

                entry = BlackboardEntry(
                    topic="agi_comm.message.received",
                    data={
                        "new_messages": new_messages,
                        "total_received": msg_count,
                        "timestamp": time.time(),
                    },
                    source_module=self.MODULE_NAME,
                    confidence=0.9,
                    priority=EntryPriority.NORMAL,
                    ttl_seconds=self._message_ttl,
                    tags=frozenset({"message", "received"}),
                )
                entries.append(entry)
        except Exception:
            logger.debug("Failed to produce message entries", exc_info=True)

        return entries

    def _produce_negotiations(self) -> List[BlackboardEntry]:
        """Produce negotiation status and game-theory analysis entries."""
        if self._negotiation is None:
            return []

        entries: List[BlackboardEntry] = []

        try:
            neg_stats = self._negotiation.get_negotiation_statistics()

            # Change detection: compare active negotiation count + completed count
            stats_key = {
                "active": neg_stats.get("active_negotiations", 0),
                "completed": neg_stats.get("completed_negotiations", 0),
            }
            if stats_key == self._last_negotiation_stats:
                return []
            self._last_negotiation_stats = stats_key

            # Negotiation status
            entry = BlackboardEntry(
                topic="agi_comm.negotiation.status",
                data={
                    "active_negotiations": neg_stats.get("active_negotiations", 0),
                    "completed_negotiations": neg_stats.get("completed_negotiations", 0),
                    "total_proposals": neg_stats.get("total_proposals", 0),
                    "agreement_rate": neg_stats.get("agreement_rate", 0.0),
                    "avg_rounds": neg_stats.get("avg_rounds", 0.0),
                },
                source_module=self.MODULE_NAME,
                confidence=0.9,
                priority=EntryPriority.NORMAL,
                ttl_seconds=self._negotiation_ttl,
                tags=frozenset({"negotiation", "status", "game_theory"}),
                metadata={"active": neg_stats.get("active_negotiations", 0)},
            )
            entries.append(entry)

            # Game-theory analysis (if any active negotiations with evaluated proposals)
            if neg_stats.get("active_negotiations", 0) > 0:
                analysis_data = {
                    "total_proposals": neg_stats.get("total_proposals", 0),
                    "agreement_rate": neg_stats.get("agreement_rate", 0.0),
                    "has_nash_equilibria": neg_stats.get("has_nash_equilibria", False),
                    "pareto_optimal_count": neg_stats.get("pareto_optimal_count", 0),
                    "timestamp": time.time(),
                }

                analysis_entry = BlackboardEntry(
                    topic="agi_comm.negotiation.analysis",
                    data=analysis_data,
                    source_module=self.MODULE_NAME,
                    confidence=0.85,
                    priority=EntryPriority.HIGH,
                    ttl_seconds=self._negotiation_ttl,
                    tags=frozenset({"negotiation", "analysis", "game_theory", "nash", "pareto"}),
                )
                entries.append(analysis_entry)

            # Emit completion event when a negotiation just finished
            completed = neg_stats.get("completed_negotiations", 0)
            prev_completed = (
                self._last_negotiation_stats.get("completed", 0)
                if self._last_negotiation_stats
                else 0
            )
            if completed > prev_completed:
                self._emit(
                    "agi_comm.negotiation.completed",
                    {
                        "completed_count": completed,
                        "agreement_rate": neg_stats.get("agreement_rate", 0.0),
                    },
                )

        except Exception:
            logger.debug("Failed to produce negotiation entries", exc_info=True)

        return entries

    def _produce_collaborations(self) -> List[BlackboardEntry]:
        """Produce collaboration status and solution entries."""
        if self._collaboration is None:
            return []

        entries: List[BlackboardEntry] = []

        try:
            collab_stats = self._collaboration.get_collaboration_statistics()

            # Change detection
            stats_key = {
                "active": collab_stats.get("active_collaborations", 0),
                "completed": collab_stats.get("completed_collaborations", 0),
            }
            if stats_key == self._last_collaboration_stats:
                return []
            self._last_collaboration_stats = stats_key

            # Collaboration status
            entry = BlackboardEntry(
                topic="agi_comm.collaboration.status",
                data={
                    "active_collaborations": collab_stats.get("active_collaborations", 0),
                    "completed_collaborations": collab_stats.get(
                        "completed_collaborations", 0
                    ),
                    "total_tasks_assigned": collab_stats.get("total_tasks_assigned", 0),
                    "total_solutions": collab_stats.get("total_solutions", 0),
                    "avg_completion_time": collab_stats.get("avg_completion_time", 0.0),
                },
                source_module=self.MODULE_NAME,
                confidence=0.9,
                priority=EntryPriority.NORMAL,
                ttl_seconds=self._collaboration_ttl,
                tags=frozenset({"collaboration", "status", "problem_solving"}),
                metadata={"active": collab_stats.get("active_collaborations", 0)},
            )
            entries.append(entry)

            # Solution entries (when new solutions are found)
            total_solutions = collab_stats.get("total_solutions", 0)
            if total_solutions > 0:
                solution_entry = BlackboardEntry(
                    topic="agi_comm.collaboration.solution",
                    data={
                        "total_solutions": total_solutions,
                        "success_rate": collab_stats.get("success_rate", 0.0),
                        "avg_quality": collab_stats.get("avg_quality", 0.0),
                        "timestamp": time.time(),
                    },
                    source_module=self.MODULE_NAME,
                    confidence=collab_stats.get("avg_quality", 0.7),
                    priority=EntryPriority.HIGH,
                    ttl_seconds=self._collaboration_ttl,
                    tags=frozenset({"collaboration", "solution"}),
                )
                entries.append(solution_entry)

                self._emit(
                    "agi_comm.collaboration.solution.found",
                    {
                        "solutions_count": total_solutions,
                        "entry_id": solution_entry.entry_id,
                    },
                )

        except Exception:
            logger.debug("Failed to produce collaboration entries", exc_info=True)

        return entries

    def _produce_merge(self) -> Optional[BlackboardEntry]:
        """Produce KG merge result entries."""
        if self._kg_merger is None:
            return None

        try:
            merge_stats = self._kg_merger.get_merge_statistics()
            total_merges = merge_stats.get("total_merges", 0)

            if total_merges == self._last_merge_count:
                return None
            self._last_merge_count = total_merges

            entry = BlackboardEntry(
                topic="agi_comm.knowledge.merge",
                data={
                    "total_merges": total_merges,
                    "total_conflicts": merge_stats.get("total_conflicts", 0),
                    "avg_confidence": merge_stats.get("avg_confidence", 0.0),
                    "resolution_strategies_used": merge_stats.get(
                        "resolution_strategies_used", []
                    ),
                    "timestamp": time.time(),
                },
                source_module=self.MODULE_NAME,
                confidence=merge_stats.get("avg_confidence", 0.7),
                priority=EntryPriority.HIGH,
                ttl_seconds=self._merge_ttl,
                tags=frozenset({"knowledge", "merge", "graph"}),
                metadata={"total_merges": total_merges},
            )

            self._emit(
                "agi_comm.knowledge.merge.completed",
                {
                    "total_merges": total_merges,
                    "entry_id": entry.entry_id,
                },
            )
            return entry
        except Exception:
            logger.debug("Failed to produce merge entries", exc_info=True)
            return None

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Feed reasoning results into collaborative problem solving.

        When a reasoning inference arrives, if there's an active collaboration
        session, submit it as a partial solution or context.
        """
        if self._collaboration is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        inference = data.get("inference", data.get("result", data.get("conclusion")))
        if inference is None:
            return

        try:
            collab_stats = self._collaboration.get_collaboration_statistics()
            if collab_stats.get("active_collaborations", 0) > 0:
                # Submit reasoning result as a solution contribution
                solution = {
                    "type": "reasoning_inference",
                    "content": inference,
                    "confidence": entry.confidence,
                    "source_entry": entry.entry_id,
                    "timestamp": time.time(),
                }
                self._collaboration.submit_solution(
                    session_id=None,  # active session
                    solution=solution,
                )
        except Exception:
            logger.debug("Failed to feed reasoning into collaboration", exc_info=True)

    def _consume_kg(self, entry: BlackboardEntry) -> None:
        """Feed knowledge graph data into the KG merger.

        When new triples arrive, queue them for merge evaluation across
        AGI knowledge bases.
        """
        if self._kg_merger is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        triples = data.get("triples", [])
        if not triples and "subject" in data:
            triples = [data]

        if not triples:
            return

        try:
            # Build a mini-graph from the incoming triples for merge
            graph = {"triples": triples, "source": entry.source_module}
            self._kg_merger.merge_graphs(
                graphs=[graph],
                resolution_strategy="evidence_based",
            )
        except Exception:
            logger.debug("Failed to feed KG data into merger", exc_info=True)

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Adjust communication priority based on consciousness state.

        Higher consciousness states (higher Φ) may increase communication
        urgency and session capacity.
        """
        if self._protocol is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        phi = data.get("phi", data.get("phi_value"))
        state = data.get("state", data.get("consciousness_state"))

        if phi is not None and hasattr(self._protocol, "priority_level"):
            try:
                # Scale priority with consciousness level
                self._protocol.priority_level = min(1.0, float(phi) / 5.0)
            except (TypeError, ValueError, AttributeError):
                pass

    def _consume_synergy(self, entry: BlackboardEntry) -> None:
        """Update collaboration efficiency based on synergy metrics.

        Coherence scores influence how the problem solver distributes tasks.
        """
        if self._collaboration is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        coherence = data.get("global_coherence", data.get("coherence"))

        if coherence is not None and hasattr(self._collaboration, "efficiency_factor"):
            try:
                self._collaboration.efficiency_factor = float(coherence)
            except (TypeError, ValueError, AttributeError):
                pass

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_reasoning_event(self, event: CognitiveEvent) -> None:
        """Route reasoning events to collaboration context."""
        if self._collaboration is None:
            return

        try:
            collab_stats = self._collaboration.get_collaboration_statistics()
            if collab_stats.get("active_collaborations", 0) > 0:
                payload = event.payload or {}
                solution = {
                    "type": "reasoning_event",
                    "content": payload,
                    "source_event": event.event_id,
                    "timestamp": time.time(),
                }
                self._collaboration.submit_solution(
                    session_id=None,
                    solution=solution,
                )
        except Exception:
            logger.debug(
                "Failed to handle reasoning event for collaboration", exc_info=True
            )

    def _handle_kg_event(self, event: CognitiveEvent) -> None:
        """Route KG events to merge evaluation."""
        if self._kg_merger is None:
            return

        payload = event.payload or {}
        if "triples" in payload or "subject" in payload:
            triples = payload.get("triples", [payload] if "subject" in payload else [])
            if triples:
                try:
                    graph = {"triples": triples, "source": event.source}
                    self._kg_merger.merge_graphs(
                        graphs=[graph],
                        resolution_strategy="temporal",
                    )
                except Exception:
                    logger.debug("Failed to merge KG from event", exc_info=True)

    def _handle_consciousness_event(self, event: CognitiveEvent) -> None:
        """Handle consciousness state changes for priority adjustment."""
        if self._protocol is None:
            return

        payload = event.payload or {}
        new_state = payload.get("new_state", "")
        if new_state and hasattr(self._protocol, "priority_level"):
            try:
                # Higher consciousness states → higher communication priority
                state_priorities = {
                    "focused": 0.8,
                    "aware": 0.6,
                    "broadcasting": 0.9,
                    "dormant": 0.2,
                }
                priority = state_priorities.get(new_state, 0.5)
                self._protocol.priority_level = priority
            except (TypeError, AttributeError):
                pass

    # ── Snapshot ──────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all communication components.

        Useful for debugging and dashboard display.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_protocol": self._protocol is not None,
            "has_negotiation": self._negotiation is not None,
            "has_collaboration": self._collaboration is not None,
            "has_semantic": self._semantic is not None,
            "has_kg_merger": self._kg_merger is not None,
            "last_session_count": self._last_session_count,
            "last_message_count": self._last_message_count,
            "last_merge_count": self._last_merge_count,
            "registered": self._blackboard is not None,
        }

        if self._protocol is not None:
            try:
                snap["comm_stats"] = self._protocol.get_communication_stats()
            except Exception:
                snap["comm_stats"] = None

        if self._negotiation is not None:
            try:
                snap["negotiation_stats"] = self._negotiation.get_negotiation_statistics()
            except Exception:
                snap["negotiation_stats"] = None

        if self._collaboration is not None:
            try:
                snap["collaboration_stats"] = (
                    self._collaboration.get_collaboration_statistics()
                )
            except Exception:
                snap["collaboration_stats"] = None

        if self._kg_merger is not None:
            try:
                snap["merge_stats"] = self._kg_merger.get_merge_statistics()
            except Exception:
                snap["merge_stats"] = None

        return snap
