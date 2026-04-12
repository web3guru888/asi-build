"""
Knowledge Management ↔ Blackboard Adapter
===========================================

Bridges the knowledge_management module (``KnowledgeEngine``,
``PredictiveSynthesizer``, ``ContextualLearner``) with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``knowledge_management.synthesis``    — Knowledge synthesis results
- ``knowledge_management.patterns``     — Pattern recognition findings
- ``knowledge_management.performance``  — Engine performance metrics
- ``knowledge_management.learning``     — Learning insights and adaptations

Topics consumed
~~~~~~~~~~~~~~~
- ``knowledge_graph.*``    — KG triples/pathfinding → graph insights for engine
- ``reasoning.*``          — Reasoning inferences → synthesizer input
- ``consciousness.*``      — Consciousness broadcasts → contextual enrichment

Events emitted
~~~~~~~~~~~~~~
- ``knowledge_management.synthesis.completed``   — Synthesis finished
- ``knowledge_management.pattern.detected``      — New pattern found
- ``knowledge_management.performance.degraded``  — Performance below threshold

Events listened
~~~~~~~~~~~~~~~
- ``knowledge_graph.triple.added``         — Feed new triples into knowledge base
- ``reasoning.inference.completed``        — Trigger learning from new inferences
"""

from __future__ import annotations

import logging
import threading
import time
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

# Lazy imports — the knowledge_management module may not be available
_km_module = None


def _get_km():
    """Lazy import of knowledge_management module to allow graceful degradation."""
    global _km_module
    if _km_module is None:
        try:
            from asi_build import knowledge_management as _km

            _km_module = _km
        except (ImportError, ModuleNotFoundError):
            _km_module = False
    return _km_module if _km_module is not False else None


class KnowledgeManagementAdapter:
    """Adapter connecting the knowledge_management module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``KnowledgeEngine`` — core knowledge querying and aggregation
    - ``PredictiveSynthesizer`` — synthesis and prediction from accumulated knowledge
    - ``ContextualLearner`` — pattern recognition and adaptive learning

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    engine : optional
        A ``KnowledgeEngine`` instance.
    synthesizer : optional
        A ``PredictiveSynthesizer`` instance.
    learner : optional
        A ``ContextualLearner`` instance.
    synthesis_ttl : float
        TTL in seconds for synthesis entries (default 300 = 5 minutes).
    patterns_ttl : float
        TTL for pattern entries (default 600 = 10 minutes).
    performance_ttl : float
        TTL for performance metric entries (default 120 = 2 minutes).
    learning_ttl : float
        TTL for learning insight entries (default 300 = 5 minutes).
    """

    MODULE_NAME = "knowledge_management"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        engine: Any = None,
        synthesizer: Any = None,
        learner: Any = None,
        *,
        synthesis_ttl: float = 300.0,
        patterns_ttl: float = 600.0,
        performance_ttl: float = 120.0,
        learning_ttl: float = 300.0,
    ) -> None:
        self._engine = engine
        self._synthesizer = synthesizer
        self._learner = learner
        self._synthesis_ttl = synthesis_ttl
        self._patterns_ttl = patterns_ttl
        self._performance_ttl = performance_ttl
        self._learning_ttl = learning_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Track last values for change detection
        self._last_query_count: int = 0
        self._last_pattern_count: int = 0

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
                "Knowledge management: engine-driven querying, predictive "
                "synthesis, and contextual pattern learning."
            ),
            topics_produced=frozenset(
                {
                    "knowledge_management.synthesis",
                    "knowledge_management.patterns",
                    "knowledge_management.performance",
                    "knowledge_management.learning",
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
            "KnowledgeManagementAdapter registered (engine=%s, synthesizer=%s, learner=%s)",
            self._engine is not None,
            self._synthesizer is not None,
            self._learner is not None,
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

        Routes KG triple additions into the knowledge base and reasoning
        inferences into the learner.
        """
        try:
            if event.event_type.startswith("knowledge_graph.triple"):
                self._ingest_triple_event(event)
            elif event.event_type.startswith("reasoning.inference"):
                self._ingest_inference_event(event)
        except Exception:
            logger.debug(
                "KnowledgeManagementAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current knowledge management state.

        Called during a production sweep.  Collects:
        1. Synthesis results from the synthesizer
        2. Pattern findings from the learner
        3. Engine performance metrics
        4. Learning insights from the learner
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            synthesis_entry = self._produce_synthesis()
            if synthesis_entry is not None:
                entries.append(synthesis_entry)

            patterns_entry = self._produce_patterns()
            if patterns_entry is not None:
                entries.append(patterns_entry)

            perf_entry = self._produce_performance()
            if perf_entry is not None:
                entries.append(perf_entry)

            learning_entry = self._produce_learning()
            if learning_entry is not None:
                entries.append(learning_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        KG entries → feed into engine as graph insights.
        Reasoning entries → feed into synthesizer as aggregated info.
        Consciousness entries → contextual enrichment for queries.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("knowledge_graph."):
                    self._consume_kg(entry)
                elif entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
                elif entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
            except Exception:
                logger.debug(
                    "KnowledgeManagementAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_synthesis(self) -> Optional[BlackboardEntry]:
        """Produce a synthesis result entry from the synthesizer."""
        if self._synthesizer is None:
            return None

        try:
            result = self._synthesizer.get_latest_synthesis()
        except Exception:
            logger.debug("PredictiveSynthesizer.get_latest_synthesis() failed", exc_info=True)
            return None

        if result is None:
            return None

        findings = result.get("findings", [])
        confidence = result.get("confidence", 0.5)
        predictions = result.get("predictions", [])

        entry = BlackboardEntry(
            topic="knowledge_management.synthesis",
            data=result,
            source_module=self.MODULE_NAME,
            confidence=confidence,
            priority=EntryPriority.HIGH if confidence > 0.8 else EntryPriority.NORMAL,
            ttl_seconds=self._synthesis_ttl,
            tags=frozenset({"synthesis", "prediction", "knowledge"}),
            metadata={
                "findings_count": len(findings),
                "predictions_count": len(predictions),
            },
        )

        self._emit(
            "knowledge_management.synthesis.completed",
            {"entry_id": entry.entry_id, "confidence": confidence},
        )
        return entry

    def _produce_patterns(self) -> Optional[BlackboardEntry]:
        """Produce a pattern recognition entry from the learner."""
        if self._learner is None:
            return None

        try:
            patterns = self._learner.get_patterns()
        except Exception:
            logger.debug("ContextualLearner.get_patterns() failed", exc_info=True)
            return None

        if patterns is None:
            return None

        # Change detection — only post if pattern count changed
        pattern_count = len(patterns) if isinstance(patterns, (list, dict)) else 0
        if pattern_count == self._last_pattern_count:
            return None
        self._last_pattern_count = pattern_count

        entry = BlackboardEntry(
            topic="knowledge_management.patterns",
            data={"patterns": patterns, "count": pattern_count},
            source_module=self.MODULE_NAME,
            confidence=0.7,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._patterns_ttl,
            tags=frozenset({"patterns", "learning", "recognition"}),
            metadata={"pattern_count": pattern_count},
        )

        self._emit(
            "knowledge_management.pattern.detected",
            {"entry_id": entry.entry_id, "pattern_count": pattern_count},
        )
        return entry

    def _produce_performance(self) -> Optional[BlackboardEntry]:
        """Produce engine performance metrics if they changed."""
        if self._engine is None:
            return None

        try:
            metrics = self._engine.get_performance_metrics()
        except Exception:
            logger.debug("KnowledgeEngine.get_performance_metrics() failed", exc_info=True)
            return None

        if metrics is None:
            return None

        # Change detection — only post if query_count increased
        query_count = metrics.get("query_count", 0)
        if query_count <= self._last_query_count:
            return None
        self._last_query_count = query_count

        avg_time = metrics.get("avg_query_time", 0.0)
        confidence = metrics.get("avg_confidence", 0.0)

        # Detect degraded performance
        is_degraded = avg_time > 2.0 or confidence < 0.3
        priority = EntryPriority.HIGH if is_degraded else EntryPriority.LOW

        entry = BlackboardEntry(
            topic="knowledge_management.performance",
            data=metrics,
            source_module=self.MODULE_NAME,
            confidence=1.0,
            priority=priority,
            ttl_seconds=self._performance_ttl,
            tags=frozenset({"performance", "metrics", *(["degraded"] if is_degraded else [])}),
            metadata={
                "query_count": query_count,
                "avg_query_time": avg_time,
                "avg_confidence": confidence,
            },
        )

        if is_degraded:
            self._emit(
                "knowledge_management.performance.degraded",
                {
                    "entry_id": entry.entry_id,
                    "avg_query_time": avg_time,
                    "avg_confidence": confidence,
                },
            )

        return entry

    def _produce_learning(self) -> Optional[BlackboardEntry]:
        """Produce learning insights from the contextual learner."""
        if self._learner is None:
            return None

        try:
            insights = self._learner.get_learning_insights()
        except Exception:
            logger.debug("ContextualLearner.get_learning_insights() failed", exc_info=True)
            return None

        if not insights:
            return None

        entry = BlackboardEntry(
            topic="knowledge_management.learning",
            data=insights,
            source_module=self.MODULE_NAME,
            confidence=0.6,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._learning_ttl,
            tags=frozenset({"learning", "adaptation", "insights"}),
        )

        return entry

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_kg(self, entry: BlackboardEntry) -> None:
        """Feed KG triples/pathfinding results into the knowledge engine."""
        if self._engine is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        try:
            self._engine.ingest_graph_insight(data, source=f"kg:{entry.entry_id}")
        except (AttributeError, TypeError):
            # Engine may not support this method yet — degrade gracefully
            logger.debug("KnowledgeEngine.ingest_graph_insight() not available")

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Feed reasoning inferences into the synthesizer."""
        if self._synthesizer is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        try:
            self._synthesizer.add_input(data, source=f"reasoning:{entry.entry_id}")
        except (AttributeError, TypeError):
            logger.debug("PredictiveSynthesizer.add_input() not available")

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Feed consciousness state into the engine for contextual enrichment."""
        if self._engine is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        try:
            self._engine.set_context(data, source=f"consciousness:{entry.entry_id}")
        except (AttributeError, TypeError):
            logger.debug("KnowledgeEngine.set_context() not available")

    # ── Event→Component injection ────────────────────────────────────

    def _ingest_triple_event(self, event: CognitiveEvent) -> None:
        """Feed a new KG triple into the knowledge engine."""
        if self._engine is None:
            return
        try:
            self._engine.ingest_graph_insight(
                event.payload, source=f"event:{event.event_id}"
            )
        except (AttributeError, TypeError):
            pass

    def _ingest_inference_event(self, event: CognitiveEvent) -> None:
        """Trigger learning from a new reasoning inference."""
        if self._learner is None:
            return
        try:
            self._learner.learn_from_inference(event.payload)
        except (AttributeError, TypeError):
            pass

    # ── Convenience ───────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of adapter state for debugging/dashboard."""
        return {
            "module": self.MODULE_NAME,
            "has_engine": self._engine is not None,
            "has_synthesizer": self._synthesizer is not None,
            "has_learner": self._learner is not None,
            "last_query_count": self._last_query_count,
            "last_pattern_count": self._last_pattern_count,
            "registered": self._blackboard is not None,
        }
