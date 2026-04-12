"""
Bio-Inspired Cognitive State → Knowledge Graph Bridge

Connects CognitiveState transitions from the BioCognitiveArchitecture
to the TemporalKnowledgeGraph, recording each state change as a set of
temporal triples.  The bridge is non-invasive: it wraps
``_update_cognitive_state`` via a thin decorator so ``core.py`` is never
modified.

Usage
-----
::

    from asi_build.bio_inspired.core import BioCognitiveArchitecture
    from asi_build.knowledge_graph.temporal_kg import TemporalKnowledgeGraph
    from asi_build.bio_inspired.kg_bridge import enable_kg_logging

    arch = BioCognitiveArchitecture()
    kg = TemporalKnowledgeGraph(db_path=":memory:")
    bridge = enable_kg_logging(arch, kg)

From that point on, every call to ``arch._update_cognitive_state()`` that
actually changes ``arch.state`` writes three triples (transition-from,
transition-to, current-state) plus optional biological-metric triples.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from asi_build.bio_inspired.core import BioCognitiveArchitecture, CognitiveState
from asi_build.knowledge_graph.temporal_kg import TemporalKnowledgeGraph

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────

SUBJECT = "bio_cognitive_system"
SOURCE = "bio_inspired"
AGENT = "kg_bridge"

# Metrics to record as triples (field_name → predicate)
_METRIC_PREDICATES: Dict[str, str] = {
    "energy_efficiency": "energy_efficiency",
    "spike_rate": "spike_rate",
    "synaptic_strength": "synaptic_strength",
    "plasticity_index": "plasticity_index",
    "homeostatic_balance": "homeostatic_balance",
    "memory_consolidation": "memory_consolidation",
    "attention_focus": "attention_focus",
    "emotional_valence": "emotional_valence",
}


# ── Data class for transition records ──────────────────────────────────

@dataclass
class TransitionRecord:
    """Immutable snapshot of a single state transition and its KG artefacts."""

    old_state: CognitiveState
    new_state: CognitiveState
    timestamp: float
    triple_ids: List[str] = field(default_factory=list)
    metric_triple_ids: List[str] = field(default_factory=list)


# ── Bridge class ───────────────────────────────────────────────────────

class CognitiveStateKGBridge:
    """Records BioCognitiveArchitecture state transitions in a KG.

    Parameters
    ----------
    arch : BioCognitiveArchitecture
        The architecture whose state changes are observed.
    kg : TemporalKnowledgeGraph
        Target knowledge graph for storing triples.
    record_metrics : bool
        If *True* (default), also record ``global_metrics`` fields as
        triples when a state change happens.
    """

    def __init__(
        self,
        arch: BioCognitiveArchitecture,
        kg: TemporalKnowledgeGraph,
        record_metrics: bool = True,
    ) -> None:
        self.arch = arch
        self.kg = kg
        self.record_metrics = record_metrics
        self.history: List[TransitionRecord] = []
        self._current_state_triple_id: Optional[str] = None

    # ── Core recording method ──────────────────────────────────────────

    def record_state_change(
        self,
        old_state: CognitiveState,
        new_state: CognitiveState,
    ) -> TransitionRecord:
        """Write a state transition to the KG.

        Creates three triples:

        1. ``(SUBJECT, "transitioned_from", old_state.value)``
        2. ``(SUBJECT, "transitioned_to", new_state.value)``
        3. ``(SUBJECT, "current_state", new_state.value)``  — replaces
           the previous ``current_state`` triple via
           ``resolve_contradictions``.

        If ``record_metrics`` is enabled, additional triples are written
        for each biological metric.

        Returns
        -------
        TransitionRecord
            A snapshot of the transition and all created triple IDs.
        """
        record = TransitionRecord(
            old_state=old_state,
            new_state=new_state,
            timestamp=time.time(),
        )

        # 1. transitioned_from
        tid_from = self.kg.add_triple(
            subject=SUBJECT,
            predicate="transitioned_from",
            object=old_state.value,
            source=SOURCE,
            confidence=1.0,
            agent=AGENT,
            statement_type="observation",
            temporal_type="dynamic",
        )
        record.triple_ids.append(tid_from)

        # 2. transitioned_to
        tid_to = self.kg.add_triple(
            subject=SUBJECT,
            predicate="transitioned_to",
            object=new_state.value,
            source=SOURCE,
            confidence=1.0,
            agent=AGENT,
            statement_type="observation",
            temporal_type="dynamic",
        )
        record.triple_ids.append(tid_to)

        # 3. current_state — manually invalidate the old one then add new.
        #    We don't use resolve_contradictions because it uses strict `>`
        #    for confidence comparison, and both old and new have confidence
        #    1.0, so the old triple would be "kept" rather than invalidated.
        if self._current_state_triple_id is not None:
            self.kg.invalidate_triple(
                triple_id=self._current_state_triple_id,
                reason=(
                    f"State changed: {old_state.value} → {new_state.value}"
                ),
                agent=AGENT,
            )

        new_current_id = self.kg.add_triple(
            subject=SUBJECT,
            predicate="current_state",
            object=new_state.value,
            source=SOURCE,
            confidence=1.0,
            agent=AGENT,
            statement_type="observation",
            temporal_type="dynamic",
        )
        record.triple_ids.append(new_current_id)
        self._current_state_triple_id = new_current_id

        # 4. Optional biological metrics
        if self.record_metrics:
            record.metric_triple_ids = self._record_metrics()

        self.history.append(record)

        logger.info(
            "KG bridge: %s → %s  (%d triples, %d metric triples)",
            old_state.value,
            new_state.value,
            len(record.triple_ids),
            len(record.metric_triple_ids),
        )

        return record

    # ── Metrics recording ──────────────────────────────────────────────

    def _record_metrics(self) -> List[str]:
        """Snapshot ``arch.global_metrics`` into KG triples."""
        ids: List[str] = []
        metrics_dict = self.arch.global_metrics.to_dict()

        for field_name, predicate in _METRIC_PREDICATES.items():
            value = metrics_dict.get(field_name)
            if value is None:
                continue
            tid = self.kg.add_triple(
                subject=SUBJECT,
                predicate=predicate,
                object=str(round(value, 6)),
                source=SOURCE,
                confidence=0.9,
                agent=AGENT,
                statement_type="observation",
                temporal_type="dynamic",
            )
            ids.append(tid)

        return ids

    # ── Query helpers ──────────────────────────────────────────────────

    def get_current_state_triple(self) -> Optional[Dict[str, Any]]:
        """Return the active ``current_state`` triple, if any."""
        triples = self.kg.get_triples(
            subject=SUBJECT,
            predicate="current_state",
            current_only=True,
        )
        return triples[0] if triples else None

    def get_transition_history(self) -> List[Dict[str, Any]]:
        """Return full temporal history of ``current_state`` predicate."""
        return self.kg.get_temporal_history(
            subject=SUBJECT,
            predicate="current_state",
        )


# ── Wrapper installer ─────────────────────────────────────────────────

def enable_kg_logging(
    arch: BioCognitiveArchitecture,
    kg: TemporalKnowledgeGraph,
    record_metrics: bool = True,
) -> CognitiveStateKGBridge:
    """Wrap ``arch._update_cognitive_state`` so state changes are logged.

    This is non-invasive: the original method is captured and called
    inside the wrapper.  Only actual state changes trigger KG writes.

    Parameters
    ----------
    arch : BioCognitiveArchitecture
        Architecture instance to instrument.
    kg : TemporalKnowledgeGraph
        Target knowledge graph.
    record_metrics : bool
        Forward to :class:`CognitiveStateKGBridge`.

    Returns
    -------
    CognitiveStateKGBridge
        The bridge instance (also stored as ``arch._kg_bridge``).
    """
    bridge = CognitiveStateKGBridge(arch, kg, record_metrics=record_metrics)

    original_update = arch._update_cognitive_state

    def _wrapped_update():
        old_state = arch.state
        original_update()
        if arch.state != old_state:
            bridge.record_state_change(old_state, arch.state)

    arch._update_cognitive_state = _wrapped_update
    arch._kg_bridge = bridge  # type: ignore[attr-defined]

    logger.info("KG logging enabled for BioCognitiveArchitecture")
    return bridge
