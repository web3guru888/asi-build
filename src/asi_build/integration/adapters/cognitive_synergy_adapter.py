"""
Cognitive Synergy ↔ Blackboard Adapter
========================================

Bridges ``CognitiveSynergyEngine`` and ``SynergyMetrics`` with the
Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``cognitive_synergy.pair``        — Per-pair synergy measurements
- ``cognitive_synergy.emergence``   — Detected emergence events
- ``cognitive_synergy.coherence``   — Global coherence snapshots
- ``cognitive_synergy.profile``     — Synergy profiles per pair

Topics consumed
~~~~~~~~~~~~~~~
- ``consciousness.*``       — Feed consciousness data into synergy pairs
- ``reasoning.*``           — Feed reasoning data into synergy pairs
- ``knowledge_graph.*``     — Feed KG data into synergy pairs

Events emitted
~~~~~~~~~~~~~~
- ``cognitive_synergy.emergence.detected``    — Emergence above threshold
- ``cognitive_synergy.coherence.updated``     — Global coherence changed
- ``cognitive_synergy.pair.updated``          — Pair synergy updated

Events listened
~~~~~~~~~~~~~~~
- ``consciousness.*``   — Update conscious/unconscious synergy pair
- ``reasoning.*``        — Update pattern_reasoning synergy pair
- ``knowledge_graph.*``  — Update memory_learning synergy pair
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


class CognitiveSynergyAdapter:
    """Adapter connecting the cognitive_synergy module to the Cognitive Blackboard.

    Wraps:

    - ``CognitiveSynergyEngine`` — main synergy engine with 10 pairs
    - ``SynergyMetrics`` — info-theoretic metrics (MI, TE, PLV, coherence, etc.)

    The adapter acts as a **Transformer**: it consumes outputs from all other
    modules, measures cross-module synergy, and posts the results back.

    Parameters
    ----------
    engine : CognitiveSynergyEngine, optional
        The synergy engine instance.  May be ``None`` for metrics-only mode.
    metrics : SynergyMetrics, optional
        The metrics instance.  If ``None``, a fresh one is created.
    pair_ttl : float
        TTL for pair-level entries (default 300s).
    emergence_ttl : float
        TTL for emergence entries (default 600s — they're important).
    coherence_ttl : float
        TTL for coherence snapshots (default 120s).
    """

    MODULE_NAME = "cognitive_synergy"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        engine: Any = None,
        metrics: Any = None,
        *,
        pair_ttl: float = 300.0,
        emergence_ttl: float = 600.0,
        coherence_ttl: float = 120.0,
    ) -> None:
        self._engine = engine
        self._metrics = metrics
        self._pair_ttl = pair_ttl
        self._emergence_ttl = emergence_ttl
        self._coherence_ttl = coherence_ttl

        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Tracking
        self._last_coherence: Optional[float] = None
        self._last_pair_values: Dict[str, float] = {}
        self._emergence_count: int = 0

        # Time-series data buffers for cross-module synergy measurement.
        # Keys are "<sourceA>_<sourceB>"; values are lists of (ts, val_a, val_b).
        self._ts_buffers: Dict[str, List] = {}

    # ── BlackboardParticipant ─────────────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.CONSUMER
                | ModuleCapability.PRODUCER
                | ModuleCapability.TRANSFORMER
                | ModuleCapability.VALIDATOR
            ),
            description=(
                "Cognitive synergy measurement — info-theoretic cross-module "
                "metrics (MI, TE, PLV), emergence detection, and global "
                "coherence tracking."
            ),
            topics_produced=frozenset(
                {
                    "cognitive_synergy.pair",
                    "cognitive_synergy.emergence",
                    "cognitive_synergy.coherence",
                    "cognitive_synergy.profile",
                }
            ),
            topics_consumed=frozenset(
                {
                    "consciousness",
                    "reasoning",
                    "knowledge_graph",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        self._blackboard = blackboard
        logger.info(
            "CognitiveSynergyAdapter registered (engine=%s, metrics=%s)",
            self._engine is not None,
            self._metrics is not None,
        )

    # ── EventEmitter ──────────────────────────────────────────────────

    def set_event_handler(self, handler: EventHandler) -> None:
        self._event_handler = handler

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self._event_handler is not None:
            self._event_handler(
                CognitiveEvent(
                    event_type=event_type,
                    payload=payload,
                    source=self.MODULE_NAME,
                )
            )

    # ── EventListener ─────────────────────────────────────────────────

    def handle_event(self, event: CognitiveEvent) -> None:
        """Handle events — feed cross-module data into synergy measurement."""
        try:
            self._record_event_data(event)
        except Exception:
            logger.debug(
                "SynergyAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer ────────────────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Produce synergy measurements and emergence events."""
        entries: List[BlackboardEntry] = []

        with self._lock:
            # 1. Per-pair synergy values from the engine
            pair_entries = self._produce_pair_entries()
            entries.extend(pair_entries)

            # 2. Global coherence
            coherence_entry = self._produce_coherence()
            if coherence_entry is not None:
                entries.append(coherence_entry)

            # 3. Emergence events
            emergence_entries = self._produce_emergence()
            entries.extend(emergence_entries)

            # 4. Metrics profiles
            profile_entries = self._produce_profiles()
            entries.extend(profile_entries)

        return entries

    # ── BlackboardConsumer ────────────────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules — feed into synergy measurement.

        Maps module outputs to synergy pair data:
        - consciousness → conscious half of conscious_unconscious pair
        - reasoning → reasoning half of pattern_reasoning pair
        - knowledge_graph → memory half of memory_learning pair
        """
        for entry in entries:
            try:
                self._feed_into_metrics(entry)
            except Exception:
                logger.debug(
                    "SynergyAdapter: failed to consume %s",
                    entry.topic,
                    exc_info=True,
                )

    # ── BlackboardTransformer ─────────────────────────────────────────

    def transform(self, entries: Sequence[BlackboardEntry]) -> Sequence[BlackboardEntry]:
        """Transform entries — annotate with synergy scores.

        Adds a ``synergy_context`` metadata field showing which synergy
        pairs are relevant to each entry.
        """
        results: List[BlackboardEntry] = []

        for entry in entries:
            relevant_pairs = self._get_relevant_pairs(entry)
            if not relevant_pairs:
                continue

            results.append(
                BlackboardEntry(
                    topic="cognitive_synergy.annotation",
                    data={
                        "original_entry_id": entry.entry_id,
                        "original_topic": entry.topic,
                        "relevant_pairs": relevant_pairs,
                    },
                    source_module=self.MODULE_NAME,
                    confidence=0.7,
                    priority=EntryPriority.LOW,
                    ttl_seconds=self._pair_ttl,
                    parent_id=entry.entry_id,
                    tags=frozenset({"annotation", "synergy"}),
                )
            )

        return results

    # ── Public API ────────────────────────────────────────────────────

    def measure_pair(self, pair_name: str) -> Optional[Dict[str, Any]]:
        """Explicitly measure a synergy pair and post to blackboard.

        Returns the synergy profile dict or ``None``.
        """
        if self._metrics is None:
            return None

        try:
            profile = self._metrics.compute_synergy_profile(pair_name)
        except Exception:
            return None

        if profile is None:
            return None

        data = {
            "pair_name": pair_name,
            "mutual_information": getattr(profile, "mutual_information", 0.0),
            "transfer_entropy": getattr(profile, "transfer_entropy", 0.0),
            "phase_coupling": getattr(profile, "phase_coupling", 0.0),
            "coherence": getattr(profile, "coherence", 0.0),
            "emergence_index": getattr(profile, "emergence_index", 0.0),
            "integration_index": getattr(profile, "integration_index", 0.0),
            "complexity_resonance": getattr(profile, "complexity_resonance", 0.0),
        }

        if self._blackboard is not None:
            entry = BlackboardEntry(
                topic="cognitive_synergy.profile",
                data=data,
                source_module=self.MODULE_NAME,
                confidence=0.9,
                priority=EntryPriority.NORMAL,
                ttl_seconds=self._pair_ttl,
                tags=frozenset({"profile", pair_name}),
                metadata={"pair_name": pair_name},
            )
            self._blackboard.post(entry)

        return data

    # ── Internal: produce helpers ─────────────────────────────────────

    def _produce_pair_entries(self) -> List[BlackboardEntry]:
        """Produce entries for each synergy pair whose value changed."""
        if self._engine is None:
            return []

        entries: List[BlackboardEntry] = []
        pairs = getattr(self._engine, "synergy_pairs", {})

        for pair_name, pair_obj in pairs.items():
            current = getattr(pair_obj, "synergy_strength", 0.0)
            last = self._last_pair_values.get(pair_name)

            # Only post if changed significantly
            if last is not None and abs(current - last) < 0.01:
                continue
            self._last_pair_values[pair_name] = current

            entries.append(
                BlackboardEntry(
                    topic="cognitive_synergy.pair",
                    data={
                        "pair_name": pair_name,
                        "synergy": current,
                        "module_a": getattr(pair_obj, "module_a", ""),
                        "module_b": getattr(pair_obj, "module_b", ""),
                    },
                    source_module=self.MODULE_NAME,
                    confidence=0.85,
                    priority=(EntryPriority.HIGH if current > 0.8 else EntryPriority.NORMAL),
                    ttl_seconds=self._pair_ttl,
                    tags=frozenset({"pair", pair_name}),
                    metadata={"pair_name": pair_name, "synergy": current},
                )
            )

            self._emit(
                "cognitive_synergy.pair.updated",
                {
                    "pair_name": pair_name,
                    "synergy": current,
                },
            )

        return entries

    def _produce_coherence(self) -> Optional[BlackboardEntry]:
        """Produce a global coherence entry if changed."""
        if self._engine is None:
            return None

        try:
            coherence = getattr(self._engine, "global_coherence", None)
            if coherence is None:
                return None
        except Exception:
            return None

        if self._last_coherence is not None and abs(coherence - self._last_coherence) < 0.01:
            return None

        self._last_coherence = coherence

        self._emit(
            "cognitive_synergy.coherence.updated",
            {
                "coherence": coherence,
            },
        )

        return BlackboardEntry(
            topic="cognitive_synergy.coherence",
            data={
                "global_coherence": coherence,
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._coherence_ttl,
            tags=frozenset({"coherence", "global"}),
        )

    def _produce_emergence(self) -> List[BlackboardEntry]:
        """Produce entries for emergence events."""
        if self._engine is None:
            return []

        try:
            indicators = self._engine.get_emergence_indicators()
        except Exception:
            return []

        if not indicators:
            return []

        # Only post new emergence events
        new_count = len(indicators)
        if new_count <= self._emergence_count:
            return []

        new_indicators = indicators[self._emergence_count :]
        self._emergence_count = new_count

        entries: List[BlackboardEntry] = []
        for indicator in new_indicators:
            entries.append(
                BlackboardEntry(
                    topic="cognitive_synergy.emergence",
                    data=indicator,
                    source_module=self.MODULE_NAME,
                    confidence=0.8,
                    priority=EntryPriority.HIGH,
                    ttl_seconds=self._emergence_ttl,
                    tags=frozenset({"emergence", "detected"}),
                )
            )

            self._emit(
                "cognitive_synergy.emergence.detected",
                {
                    "indicator": indicator,
                },
            )

        return entries

    def _produce_profiles(self) -> List[BlackboardEntry]:
        """Produce synergy profiles from the metrics engine."""
        if self._metrics is None:
            return []

        entries: List[BlackboardEntry] = []
        try:
            all_profiles = self._metrics.get_all_profiles()
        except Exception:
            return []

        for pair_name, profile in all_profiles.items():
            entries.append(
                BlackboardEntry(
                    topic="cognitive_synergy.profile",
                    data={
                        "pair_name": pair_name,
                        "mutual_information": getattr(profile, "mutual_information", 0.0),
                        "transfer_entropy": getattr(profile, "transfer_entropy", 0.0),
                        "phase_coupling": getattr(profile, "phase_coupling", 0.0),
                        "coherence": getattr(profile, "coherence", 0.0),
                        "emergence_index": getattr(profile, "emergence_index", 0.0),
                        "integration_index": getattr(profile, "integration_index", 0.0),
                        "complexity_resonance": getattr(profile, "complexity_resonance", 0.0),
                    },
                    source_module=self.MODULE_NAME,
                    confidence=0.85,
                    priority=EntryPriority.LOW,
                    ttl_seconds=self._pair_ttl,
                    tags=frozenset({"profile", pair_name}),
                    metadata={"pair_name": pair_name},
                )
            )

        return entries

    # ── Internal: consume/event helpers ───────────────────────────────

    def _feed_into_metrics(self, entry: BlackboardEntry) -> None:
        """Feed a consumed entry's data into the metrics engine as time-series."""
        if self._metrics is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        value = self._extract_numeric_value(data)
        if value is None:
            return

        # Map topic → pair name (which synergy pair this module contributes to)
        pair_map = {
            "consciousness": ("conscious_unconscious", "a"),
            "reasoning": ("pattern_reasoning", "b"),
            "knowledge_graph": ("memory_learning", "a"),
        }
        topic_root = entry.topic.split(".")[0]
        mapping = pair_map.get(topic_root)
        if mapping is None:
            return

        pair_name, side = mapping
        ts = entry.timestamp

        # Buffer the value
        buf = self._ts_buffers.setdefault(pair_name, [])
        buf.append((ts, side, value))

        # Try to form a matched pair for the metrics engine
        a_vals = [v for (t, s, v) in buf if s == "a"]
        b_vals = [v for (t, s, v) in buf if s == "b"]

        if a_vals and b_vals:
            a_val = a_vals[-1]
            b_val = b_vals[-1]
            try:
                self._metrics.add_time_series_data(pair_name, a_val, b_val, ts)
            except Exception:
                pass
            # Trim buffer
            if len(buf) > 200:
                self._ts_buffers[pair_name] = buf[-100:]

    def _record_event_data(self, event: CognitiveEvent) -> None:
        """Record event data for synergy measurement (same logic as consume)."""
        data = event.payload
        value = self._extract_numeric_value(data)
        if value is None:
            return

        pair_map = {
            "consciousness": ("conscious_unconscious", "a"),
            "reasoning": ("pattern_reasoning", "b"),
            "knowledge_graph": ("memory_learning", "a"),
        }
        root = event.event_type.split(".")[0]
        mapping = pair_map.get(root)
        if mapping is None:
            return

        pair_name, side = mapping
        buf = self._ts_buffers.setdefault(pair_name, [])
        buf.append((event.timestamp, side, value))

    def _extract_numeric_value(self, data: Dict[str, Any]) -> Optional[float]:
        """Extract a representative numeric value from a data dict."""
        # Try well-known keys
        for key in ("phi", "confidence", "synergy", "coherence", "strength", "score"):
            if key in data:
                try:
                    return float(data[key])
                except (TypeError, ValueError):
                    continue
        # Fallback: first numeric value
        for v in data.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
        return None

    def _get_relevant_pairs(self, entry: BlackboardEntry) -> List[Dict[str, Any]]:
        """Find synergy pairs relevant to an entry's topic."""
        if self._engine is None:
            return []

        topic_root = entry.topic.split(".")[0]

        relevance_map = {
            "consciousness": ["conscious_unconscious", "attention_intention"],
            "reasoning": ["pattern_reasoning", "symbolic_subsymbolic"],
            "knowledge_graph": ["memory_learning", "local_global"],
        }

        pair_names = relevance_map.get(topic_root, [])
        result: List[Dict[str, Any]] = []

        pairs = getattr(self._engine, "synergy_pairs", {})
        for name in pair_names:
            pair = pairs.get(name)
            if pair is not None:
                result.append(
                    {
                        "pair_name": name,
                        "synergy": getattr(pair, "synergy_strength", 0.0),
                        "module_a": getattr(pair, "module_a", ""),
                        "module_b": getattr(pair, "module_b", ""),
                    }
                )

        return result

    # ── Convenience ───────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of adapter state."""
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_engine": self._engine is not None,
            "has_metrics": self._metrics is not None,
            "last_coherence": self._last_coherence,
            "pair_values": dict(self._last_pair_values),
            "emergence_count": self._emergence_count,
            "registered": self._blackboard is not None,
        }

        if self._engine is not None:
            try:
                snap["system_state"] = self._engine.get_system_state()
            except Exception:
                pass

        return snap
