"""
Reasoning ↔ Blackboard Adapter
================================

Bridges the ``HybridReasoningEngine`` with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``reasoning.inference``       — Completed reasoning results
- ``reasoning.step``            — Individual reasoning steps (for provenance)
- ``reasoning.performance``     — Reasoning engine performance metrics

Topics consumed
~~~~~~~~~~~~~~~
- ``knowledge_graph.*``     — KG triples/paths → reasoning context
- ``consciousness.*``       — Consciousness state → attention guidance
- ``cognitive_synergy.*``   — Synergy metrics → mode weight adjustment

Events emitted
~~~~~~~~~~~~~~
- ``reasoning.inference.completed``     — Reasoning cycle complete
- ``reasoning.mode.selected``           — Reasoning mode chosen
- ``reasoning.safety.flagged``          — Safety check flagged an issue

Events listened
~~~~~~~~~~~~~~~
- ``knowledge_graph.triple.added``      — New triples for reasoning context
- ``consciousness.state.changed``       — State changes affect reasoning
- ``cognitive_synergy.coherence.updated``— Coherence affects mode weights
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


class ReasoningAdapter:
    """Adapter connecting HybridReasoningEngine to the Cognitive Blackboard.

    Provides:
    - **Context-enriched reasoning**: queries KG and consciousness entries
      on the blackboard before invoking ``reason()``.
    - **Result posting**: posts reasoning results and individual steps.
    - **Mode adaptation**: adjusts reasoning mode weights based on synergy.

    Parameters
    ----------
    engine : HybridReasoningEngine
        The reasoning engine instance.
    inference_ttl : float
        TTL for inference result entries (default 600s).
    step_ttl : float
        TTL for individual step entries (default 300s).
    auto_context : bool
        If ``True``, automatically pull KG/consciousness context from the
        blackboard before reasoning (default ``True``).
    max_context_entries : int
        Max blackboard entries to pull for context (default 20).
    """

    MODULE_NAME = "reasoning"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        engine: Any,
        *,
        inference_ttl: float = 600.0,
        step_ttl: float = 300.0,
        auto_context: bool = True,
        max_context_entries: int = 20,
    ) -> None:
        if engine is None:
            raise ValueError("ReasoningAdapter requires a non-None engine instance")
        self._engine = engine
        self._inference_ttl = inference_ttl
        self._step_ttl = step_ttl
        self._auto_context = auto_context
        self._max_context_entries = max_context_entries

        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Track recent inferences to avoid double-posting
        self._inference_count: int = 0
        self._pending_results: List[Dict[str, Any]] = []
        self._last_performance: Optional[Dict[str, Any]] = None

        # Context accumulator from events
        self._kg_context: List[Dict[str, Any]] = []
        self._consciousness_context: Dict[str, Any] = {}

    # ── BlackboardParticipant ─────────────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER
                | ModuleCapability.CONSUMER
                | ModuleCapability.REASONER
            ),
            description=(
                "Hybrid reasoning engine combining logical, probabilistic, "
                "analogical, causal, creative, and quantum reasoning modes."
            ),
            topics_produced=frozenset({
                "reasoning.inference",
                "reasoning.step",
                "reasoning.performance",
            }),
            topics_consumed=frozenset({
                "knowledge_graph",
                "consciousness",
                "cognitive_synergy",
            }),
        )

    def on_registered(self, blackboard: Any) -> None:
        self._blackboard = blackboard
        logger.info("ReasoningAdapter registered (engine=%s)", type(self._engine).__name__)

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
        """Handle events — accumulate context for future reasoning."""
        try:
            if event.event_type.startswith("knowledge_graph."):
                self._accumulate_kg_context(event)
            elif event.event_type.startswith("consciousness."):
                self._update_consciousness_context(event)
            elif event.event_type.startswith("cognitive_synergy.coherence"):
                self._adapt_mode_weights(event)
        except Exception:
            logger.debug(
                "ReasoningAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer ────────────────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Produce entries from pending reasoning results."""
        entries: List[BlackboardEntry] = []

        with self._lock:
            for result_data in self._pending_results:
                entries.extend(self._result_to_entries(result_data))
            self._pending_results.clear()

            perf_entry = self._produce_performance()
            if perf_entry is not None:
                entries.append(perf_entry)

        return entries

    # ── BlackboardConsumer ────────────────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries — build context for future reasoning.

        KG triples → reasoning context.
        Consciousness state → attention guidance.
        Synergy metrics → mode weight adjustment.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("knowledge_graph."):
                    self._consume_kg(entry)
                elif entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
                elif entry.topic.startswith("cognitive_synergy."):
                    self._consume_synergy(entry)
            except Exception:
                logger.debug(
                    "ReasoningAdapter: failed to consume %s",
                    entry.topic,
                    exc_info=True,
                )

    # ── Public API: reason with blackboard context ────────────────────

    def reason(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        reasoning_mode: Any = None,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """Execute reasoning with blackboard-enriched context.

        1. If ``auto_context`` is enabled, queries the blackboard for
           relevant KG triples and consciousness state.
        2. Merges with accumulated event context and user-provided context.
        3. Invokes the underlying reasoning engine.
        4. Posts the result to the blackboard.

        Parameters
        ----------
        query : str
            The reasoning query.
        context : dict, optional
            Additional context (merged with blackboard context).
        reasoning_mode : ReasoningMode, optional
            Explicit reasoning mode.  If ``None``, engine chooses automatically.

        Returns
        -------
        dict or None
            The reasoning result dict, or ``None`` on failure.
        """
        # Build enriched context
        enriched_context = self._build_context(context)

        # Invoke engine
        try:
            reason_kwargs: Dict[str, Any] = {
                "query": query,
                "context": enriched_context,
            }
            if reasoning_mode is not None:
                reason_kwargs["reasoning_mode"] = reasoning_mode
            reason_kwargs.update(kwargs)

            result = self._engine.reason(**reason_kwargs)
        except Exception:
            logger.debug("Reasoning engine failed", exc_info=True)
            return None

        # Convert result to dict
        result_data = self._result_to_dict(result)

        # Queue for blackboard posting
        with self._lock:
            self._pending_results.append(result_data)
            self._inference_count += 1

        # Emit events
        self._emit("reasoning.inference.completed", {
            "query": query,
            "conclusion": result_data.get("conclusion", ""),
            "confidence": result_data.get("confidence", 0.0),
            "mode": result_data.get("reasoning_mode", ""),
        })

        # Safety check
        safety = result_data.get("safety", {})
        if safety.get("flagged", False):
            self._emit("reasoning.safety.flagged", {
                "query": query,
                "concerns": safety.get("concerns", []),
            })

        return result_data

    # ── Internal: context building ────────────────────────────────────

    def _build_context(self, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build enriched context by merging sources."""
        ctx: Dict[str, Any] = {}

        # 1. Accumulated event context
        with self._lock:
            if self._kg_context:
                ctx["kg_triples"] = list(self._kg_context[-self._max_context_entries:])
            if self._consciousness_context:
                ctx["consciousness_state"] = dict(self._consciousness_context)

        # 2. Blackboard query (if auto_context and blackboard available)
        if self._auto_context and self._blackboard is not None:
            bb_ctx = self._query_blackboard_context()
            ctx.update(bb_ctx)

        # 3. User context (highest precedence)
        if user_context:
            ctx.update(user_context)

        return ctx

    def _query_blackboard_context(self) -> Dict[str, Any]:
        """Query the blackboard for relevant context."""
        ctx: Dict[str, Any] = {}

        try:
            # Get recent KG triples
            kg_entries = self._blackboard.get_by_topic("knowledge_graph")
            if kg_entries:
                ctx["blackboard_kg"] = [
                    e.data for e in kg_entries[:self._max_context_entries]
                    if isinstance(e.data, dict)
                ]

            # Get consciousness state
            state_entries = self._blackboard.get_by_topic("consciousness.state")
            if state_entries:
                ctx["blackboard_consciousness"] = state_entries[0].data

            # Get latest Φ
            phi_entries = self._blackboard.get_by_topic("consciousness.phi")
            if phi_entries:
                ctx["blackboard_phi"] = phi_entries[0].data
        except Exception:
            logger.debug("Failed to query blackboard for context", exc_info=True)

        return ctx

    # ── Internal: result conversion ───────────────────────────────────

    def _result_to_dict(self, result: Any) -> Dict[str, Any]:
        """Convert a ReasoningResult to a plain dict."""
        if isinstance(result, dict):
            return result
        if hasattr(result, "to_dict"):
            return result.to_dict()
        # Manual conversion
        return {
            "conclusion": getattr(result, "conclusion", str(result)),
            "confidence": getattr(result, "confidence", 0.5),
            "confidence_level": str(getattr(result, "confidence_level", "")),
            "reasoning_mode": str(getattr(result, "reasoning_mode", "")),
            "total_processing_time": getattr(result, "total_processing_time", 0.0),
            "explanation": getattr(result, "explanation", ""),
            "reasoning_steps": [
                self._step_to_dict(s)
                for s in getattr(result, "reasoning_steps", [])
            ],
            "sources": list(getattr(result, "sources", [])),
            "uncertainty_areas": list(getattr(result, "uncertainty_areas", [])),
            "alternative_conclusions": list(getattr(result, "alternative_conclusions", [])),
        }

    def _step_to_dict(self, step: Any) -> Dict[str, Any]:
        """Convert a ReasoningStep to a dict."""
        if isinstance(step, dict):
            return step
        return {
            "mode": str(getattr(step, "mode", "")),
            "input_data": getattr(step, "input_data", ""),
            "output_data": getattr(step, "output_data", ""),
            "confidence": getattr(step, "confidence", 0.0),
            "processing_time": getattr(step, "processing_time", 0.0),
            "reasoning_chain": getattr(step, "reasoning_chain", ""),
        }

    def _result_to_entries(self, result_data: Dict[str, Any]) -> List[BlackboardEntry]:
        """Convert a reasoning result dict to blackboard entries."""
        entries: List[BlackboardEntry] = []

        # Main inference entry
        confidence = result_data.get("confidence", 0.5)
        entries.append(BlackboardEntry(
            topic="reasoning.inference",
            data=result_data,
            source_module=self.MODULE_NAME,
            confidence=confidence,
            priority=(
                EntryPriority.HIGH if confidence > 0.8
                else EntryPriority.NORMAL
            ),
            ttl_seconds=self._inference_ttl,
            tags=frozenset({
                "inference",
                result_data.get("reasoning_mode", "hybrid"),
            }),
            metadata={
                "conclusion": str(result_data.get("conclusion", ""))[:200],
                "mode": result_data.get("reasoning_mode", ""),
            },
        ))

        # Individual step entries (for fine-grained provenance)
        for i, step in enumerate(result_data.get("reasoning_steps", [])):
            entries.append(BlackboardEntry(
                topic="reasoning.step",
                data=step,
                source_module=self.MODULE_NAME,
                confidence=step.get("confidence", 0.5),
                priority=EntryPriority.LOW,
                ttl_seconds=self._step_ttl,
                tags=frozenset({"step", f"step_{i}"}),
                parent_id=entries[0].entry_id,  # Link to main inference
                metadata={"step_index": i},
            ))

        return entries

    def _produce_performance(self) -> Optional[BlackboardEntry]:
        """Produce a performance metrics entry if changed."""
        try:
            perf = self._engine.get_performance_metrics()
        except Exception:
            return None

        if perf == self._last_performance:
            return None
        self._last_performance = perf

        return BlackboardEntry(
            topic="reasoning.performance",
            data=perf,
            source_module=self.MODULE_NAME,
            confidence=1.0,
            priority=EntryPriority.LOW,
            ttl_seconds=120.0,
            tags=frozenset({"performance", "metrics"}),
        )

    # ── Internal: consume helpers ─────────────────────────────────────

    def _consume_kg(self, entry: BlackboardEntry) -> None:
        """Accumulate KG data for reasoning context."""
        data = entry.data if isinstance(entry.data, dict) else {"raw": entry.data}
        with self._lock:
            self._kg_context.append(data)
            # Keep bounded
            if len(self._kg_context) > self._max_context_entries * 2:
                self._kg_context = self._kg_context[-self._max_context_entries:]

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Update consciousness context for reasoning."""
        if isinstance(entry.data, dict):
            with self._lock:
                self._consciousness_context.update(entry.data)

    def _consume_synergy(self, entry: BlackboardEntry) -> None:
        """Adapt reasoning weights based on synergy data."""
        data = entry.data if isinstance(entry.data, dict) else {}
        coherence = data.get("global_coherence", data.get("coherence"))
        if coherence is not None:
            self._adapt_weights_from_coherence(float(coherence))

    # ── Internal: event helpers ───────────────────────────────────────

    def _accumulate_kg_context(self, event: CognitiveEvent) -> None:
        """Accumulate KG event data."""
        with self._lock:
            self._kg_context.append(event.payload)
            if len(self._kg_context) > self._max_context_entries * 2:
                self._kg_context = self._kg_context[-self._max_context_entries:]

    def _update_consciousness_context(self, event: CognitiveEvent) -> None:
        """Update consciousness state from events."""
        with self._lock:
            self._consciousness_context.update(event.payload)

    def _adapt_mode_weights(self, event: CognitiveEvent) -> None:
        """Adjust mode weights based on coherence events."""
        coherence = event.payload.get("coherence", event.payload.get("global_coherence"))
        if coherence is not None:
            self._adapt_weights_from_coherence(float(coherence))

    def _adapt_weights_from_coherence(self, coherence: float) -> None:
        """Adapt reasoning mode weights based on system coherence.

        High coherence (>0.7): boost logical/causal (structured) reasoning.
        Low coherence (<0.3): boost creative/analogical (exploratory) reasoning.
        """
        if not hasattr(self._engine, "mode_weights"):
            return

        try:
            weights = self._engine.mode_weights
            if coherence > 0.7:
                # System is coherent → structured reasoning
                _nudge_weight(weights, "LOGICAL", +0.02)
                _nudge_weight(weights, "CAUSAL", +0.01)
                _nudge_weight(weights, "CREATIVE", -0.01)
            elif coherence < 0.3:
                # System is fragmented → exploratory reasoning
                _nudge_weight(weights, "CREATIVE", +0.02)
                _nudge_weight(weights, "ANALOGICAL", +0.01)
                _nudge_weight(weights, "LOGICAL", -0.01)
        except Exception:
            logger.debug("Failed to adapt mode weights", exc_info=True)

    # ── Convenience ───────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of adapter state."""
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "inference_count": self._inference_count,
            "pending_results": len(self._pending_results),
            "kg_context_size": len(self._kg_context),
            "auto_context": self._auto_context,
            "registered": self._blackboard is not None,
        }
        try:
            snap["performance"] = self._engine.get_performance_metrics()
        except Exception:
            pass
        return snap


# ── Utility ───────────────────────────────────────────────────────────

def _nudge_weight(weights: Dict, key_suffix: str, delta: float) -> None:
    """Nudge a weight by *delta*, keeping it in [0.01, 0.95].

    Works with both string keys and enum keys whose ``.name`` matches.
    """
    for k in weights:
        name = k.name if hasattr(k, "name") else str(k)
        if name == key_suffix or name.upper() == key_suffix:
            old = weights[k]
            weights[k] = max(0.01, min(0.95, old + delta))
            return
