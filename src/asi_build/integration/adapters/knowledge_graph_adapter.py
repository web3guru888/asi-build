"""
Knowledge Graph ↔ Blackboard Adapter
======================================

Bridges the knowledge_graph module (``TemporalKnowledgeGraph``, ``KGPathfinder``)
with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``knowledge_graph.triple``            — New triples added to the KG
- ``knowledge_graph.contradiction``     — Detected contradictions
- ``knowledge_graph.pathfinding``       — Pathfinding results
- ``knowledge_graph.statistics``        — KG statistics snapshots

Topics consumed
~~~~~~~~~~~~~~~
- ``reasoning.*``           — Reasoning inferences → new triples
- ``consciousness.*``       — Consciousness state → entity relevance
- ``cognitive_synergy.*``   — Synergy findings → new triples

Events emitted
~~~~~~~~~~~~~~
- ``knowledge_graph.triple.added``          — Triple added
- ``knowledge_graph.contradiction.found``   — Contradiction detected
- ``knowledge_graph.pathfinding.completed`` — Pathfinding result

Events listened
~~~~~~~~~~~~~~~
- ``reasoning.inference.completed``     — Convert inferences to triples
- ``consciousness.broadcast.completed`` — Tag relevant entities
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

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


class KnowledgeGraphAdapter:
    """Adapter connecting the knowledge_graph module to the Cognitive Blackboard.

    Wraps:

    - ``TemporalKnowledgeGraph`` — triple store with provenance and temporality
    - ``KGPathfinder`` — semantic A* pathfinding

    Parameters
    ----------
    kg : TemporalKnowledgeGraph
        The temporal knowledge graph instance.
    pathfinder : KGPathfinder, optional
        If ``None``, pathfinding operations are skipped.
    auto_ingest_inferences : bool
        If ``True``, automatically convert consumed reasoning entries into
        KG triples (default ``True``).
    triple_ttl : float
        TTL for triple notification entries on the blackboard (default 600s).
    stats_ttl : float
        TTL for statistics snapshot entries (default 120s).
    """

    MODULE_NAME = "knowledge_graph"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        kg: Any,
        pathfinder: Any = None,
        *,
        auto_ingest_inferences: bool = True,
        triple_ttl: float = 600.0,
        stats_ttl: float = 120.0,
    ) -> None:
        if kg is None:
            raise ValueError("KnowledgeGraphAdapter requires a non-None kg instance")
        self._kg = kg
        self._pathfinder = pathfinder
        self._auto_ingest = auto_ingest_inferences
        self._triple_ttl = triple_ttl
        self._stats_ttl = stats_ttl

        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Track recently posted triples to avoid re-posting
        self._posted_triple_ids: Set[str] = set()
        self._last_stats_snapshot: Optional[Dict[str, Any]] = None
        self._pending_triples: List[Dict[str, Any]] = []

    # ── BlackboardParticipant ─────────────────────────────────────────

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
                "Temporal knowledge graph with provenance tracking, contradiction "
                "detection, and semantic A* pathfinding."
            ),
            topics_produced=frozenset({
                "knowledge_graph.triple",
                "knowledge_graph.contradiction",
                "knowledge_graph.pathfinding",
                "knowledge_graph.statistics",
            }),
            topics_consumed=frozenset({
                "reasoning",
                "consciousness",
                "cognitive_synergy",
            }),
        )

    def on_registered(self, blackboard: Any) -> None:
        self._blackboard = blackboard
        logger.info(
            "KnowledgeGraphAdapter registered (kg=%s, pathfinder=%s)",
            type(self._kg).__name__,
            self._pathfinder is not None,
        )

    # ── EventEmitter ──────────────────────────────────────────────────

    def set_event_handler(self, handler: EventHandler) -> None:
        self._event_handler = handler

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self._event_handler is not None:
            self._event_handler(CognitiveEvent(
                event_type=event_type,
                payload=payload,
                source=self.MODULE_NAME,
            ))

    # ── EventListener ─────────────────────────────────────────────────

    def handle_event(self, event: CognitiveEvent) -> None:
        """Handle events from other modules.

        - Reasoning inferences → potential new triples
        - Consciousness broadcasts → entity relevance updates
        """
        try:
            if event.event_type.startswith("reasoning.") and self._auto_ingest:
                self._ingest_inference_event(event)
            elif event.event_type.startswith("consciousness.broadcast"):
                self._handle_broadcast_event(event)
        except Exception:
            logger.debug(
                "KGAdapter: failed to handle event %s", event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer ────────────────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Produce entries from pending triples and periodic stats."""
        entries: List[BlackboardEntry] = []

        with self._lock:
            # Flush pending triples
            for triple_data in self._pending_triples:
                entries.append(self._triple_to_entry(triple_data))
            self._pending_triples.clear()

            # Periodic stats snapshot
            stats_entry = self._produce_stats()
            if stats_entry is not None:
                entries.append(stats_entry)

        return entries

    # ── BlackboardConsumer ────────────────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        Reasoning entries → ingest as KG triples.
        Synergy entries → record synergy relationships.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("reasoning.") and self._auto_ingest:
                    self._ingest_reasoning_entry(entry)
                elif entry.topic.startswith("cognitive_synergy."):
                    self._ingest_synergy_entry(entry)
            except Exception:
                logger.debug(
                    "KGAdapter: failed to consume %s", entry.topic, exc_info=True,
                )

    # ── BlackboardTransformer ─────────────────────────────────────────

    def transform(self, entries: Sequence[BlackboardEntry]) -> Sequence[BlackboardEntry]:
        """Transform entries — enrich with KG context.

        For reasoning entries, look up related triples and attach them
        as metadata for downstream consumers.
        """
        results: List[BlackboardEntry] = []

        for entry in entries:
            if not entry.topic.startswith("reasoning."):
                continue
            enriched = self._enrich_with_kg(entry)
            if enriched is not None:
                results.append(enriched)

        return results

    # ── Public API: explicit triple posting ───────────────────────────

    def add_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        *,
        source: str = "blackboard",
        confidence: float = 1.0,
        agent: str = "",
        statement_type: str = "fact",
    ) -> Optional[str]:
        """Add a triple to the KG and queue it for blackboard posting.

        Returns the triple ID, or ``None`` on failure.
        """
        try:
            triple_id = self._kg.add_triple(
                subject=subject,
                predicate=predicate,
                object=obj,
                source=source,
                confidence=confidence,
                agent=agent,
                statement_type=statement_type,
            )
        except Exception:
            logger.debug("Failed to add triple to KG", exc_info=True)
            return None

        # Check for contradictions
        contradictions = self._check_contradictions(subject, predicate, obj, confidence)

        triple_data = {
            "triple_id": triple_id,
            "subject": subject,
            "predicate": predicate,
            "object": obj,
            "confidence": confidence,
            "source": source,
            "statement_type": statement_type,
            "contradictions": contradictions,
        }

        with self._lock:
            self._pending_triples.append(triple_data)
            self._posted_triple_ids.add(triple_id)

        self._emit("knowledge_graph.triple.added", {
            "triple_id": triple_id,
            "subject": subject,
            "predicate": predicate,
            "object": obj,
        })

        if contradictions:
            self._emit("knowledge_graph.contradiction.found", {
                "triple_id": triple_id,
                "contradictions": contradictions,
            })

        return triple_id

    def find_path(self, start: str, goal: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """Find a path between two entities and post the result.

        Returns the pathfinding result dict or ``None``.
        """
        if self._pathfinder is None:
            return None

        try:
            result = self._pathfinder.find_path(start, goal, **kwargs)
        except Exception:
            logger.debug("Pathfinding failed", exc_info=True)
            return None

        if result.get("found", False) and self._blackboard is not None:
            entry = BlackboardEntry(
                topic="knowledge_graph.pathfinding",
                data=result,
                source_module=self.MODULE_NAME,
                confidence=result.get("confidence", 0.8),
                priority=EntryPriority.NORMAL,
                ttl_seconds=self._triple_ttl,
                tags=frozenset({"pathfinding", "a_star"}),
                metadata={"start": start, "goal": goal},
            )
            self._blackboard.post(entry)
            self._emit("knowledge_graph.pathfinding.completed", {
                "start": start,
                "goal": goal,
                "entry_id": entry.entry_id,
                "path_length": len(result.get("path", [])),
            })

        return result

    # ── Internal helpers ──────────────────────────────────────────────

    def _triple_to_entry(self, triple_data: Dict[str, Any]) -> BlackboardEntry:
        """Convert a triple dict to a BlackboardEntry."""
        has_contradictions = bool(triple_data.get("contradictions"))
        topic = (
            "knowledge_graph.contradiction"
            if has_contradictions
            else "knowledge_graph.triple"
        )
        priority = EntryPriority.HIGH if has_contradictions else EntryPriority.NORMAL

        return BlackboardEntry(
            topic=topic,
            data=triple_data,
            source_module=self.MODULE_NAME,
            confidence=triple_data.get("confidence", 1.0),
            priority=priority,
            ttl_seconds=self._triple_ttl,
            tags=frozenset({
                "triple",
                triple_data.get("statement_type", "fact"),
                *(["contradiction"] if has_contradictions else []),
            }),
            metadata={
                "triple_id": triple_data.get("triple_id", ""),
                "subject": triple_data.get("subject", ""),
                "predicate": triple_data.get("predicate", ""),
                "object": triple_data.get("object", ""),
            },
        )

    def _produce_stats(self) -> Optional[BlackboardEntry]:
        """Produce a KG statistics entry if stats have changed."""
        try:
            stats = self._kg.get_statistics()
        except Exception:
            return None

        # Simple change detection on total_triples count
        total = stats.get("total_triples", stats.get("total", 0))
        if (
            self._last_stats_snapshot is not None
            and self._last_stats_snapshot.get("total_triples") == total
        ):
            return None

        self._last_stats_snapshot = stats

        return BlackboardEntry(
            topic="knowledge_graph.statistics",
            data=stats,
            source_module=self.MODULE_NAME,
            confidence=1.0,
            priority=EntryPriority.LOW,
            ttl_seconds=self._stats_ttl,
            tags=frozenset({"statistics", "snapshot"}),
        )

    def _check_contradictions(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float,
    ) -> List[Dict[str, Any]]:
        """Check for contradictions with existing triples."""
        try:
            return self._kg.detect_contradictions(
                subject=subject,
                predicate=predicate,
                new_object=obj,
                new_confidence=confidence,
            )
        except Exception:
            return []

    def _ingest_reasoning_entry(self, entry: BlackboardEntry) -> None:
        """Convert a reasoning BlackboardEntry into a KG triple."""
        data = entry.data if isinstance(entry.data, dict) else {}
        conclusion = data.get("conclusion", data.get("result", ""))
        if not conclusion:
            return

        subject = data.get("subject", "reasoning_system")
        predicate = data.get("predicate", "concluded")
        obj = str(conclusion)

        self.add_triple(
            subject=subject,
            predicate=predicate,
            obj=obj,
            source=f"reasoning:{entry.entry_id}",
            confidence=entry.confidence,
            agent="blackboard_adapter",
            statement_type="inference",
        )

    def _ingest_synergy_entry(self, entry: BlackboardEntry) -> None:
        """Record synergy relationships as KG triples."""
        data = entry.data if isinstance(entry.data, dict) else {}

        pair_name = data.get("pair_name", "")
        synergy_value = data.get("synergy", data.get("strength", None))

        if pair_name and synergy_value is not None:
            parts = pair_name.split("_", 1)
            if len(parts) == 2:
                self.add_triple(
                    subject=parts[0],
                    predicate="synergizes_with",
                    obj=parts[1],
                    source="cognitive_synergy",
                    confidence=min(1.0, float(synergy_value)),
                    agent="blackboard_adapter",
                    statement_type="observation",
                )

    def _ingest_inference_event(self, event: CognitiveEvent) -> None:
        """Convert a reasoning event into a KG triple."""
        payload = event.payload
        conclusion = payload.get("conclusion", payload.get("result", ""))
        if conclusion:
            self.add_triple(
                subject=payload.get("subject", "reasoning"),
                predicate=payload.get("predicate", "inferred"),
                obj=str(conclusion),
                source=f"event:{event.event_id}",
                confidence=payload.get("confidence", 0.7),
                agent="blackboard_adapter",
                statement_type="inference",
            )

    def _handle_broadcast_event(self, event: CognitiveEvent) -> None:
        """Handle GWT broadcast — mark relevant entities as attended."""
        # This is a lightweight signal: we just note the broadcast happened.
        # Could enrich entities with "attention_level" metadata in the future.
        pass

    def _enrich_with_kg(self, entry: BlackboardEntry) -> Optional[BlackboardEntry]:
        """Enrich a reasoning entry with related KG context."""
        data = entry.data if isinstance(entry.data, dict) else {}
        subject = data.get("subject", "")
        if not subject:
            return None

        try:
            relations = self._kg.get_entity_relations(subject)
        except Exception:
            return None

        if not relations:
            return None

        return BlackboardEntry(
            topic="knowledge_graph.enrichment",
            data={
                "original_entry_id": entry.entry_id,
                "original_topic": entry.topic,
                "entity": subject,
                "related_triples": relations[:10],  # Cap to 10
            },
            source_module=self.MODULE_NAME,
            confidence=0.8,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._triple_ttl,
            parent_id=entry.entry_id,
            tags=frozenset({"enrichment", "kg_context"}),
        )

    # ── Convenience ───────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of adapter state."""
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_pathfinder": self._pathfinder is not None,
            "auto_ingest": self._auto_ingest,
            "posted_triples": len(self._posted_triple_ids),
            "pending_triples": len(self._pending_triples),
            "registered": self._blackboard is not None,
        }
        try:
            snap["kg_stats"] = self._kg.get_statistics()
        except Exception:
            snap["kg_stats"] = None
        return snap
