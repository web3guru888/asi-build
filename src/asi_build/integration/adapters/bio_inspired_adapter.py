"""
Bio-Inspired ↔ Blackboard Adapter
====================================

Bridges the bio-inspired module (``BioCognitiveArchitecture``,
``EvolutionaryOptimizer``, ``HomeostaticRegulator``) with the Cognitive
Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``bio_inspired.fitness``        — Best fitness scores from evolutionary optimization
- ``bio_inspired.population``     — Population statistics (diversity, mean fitness, generation)
- ``bio_inspired.homeostasis``    — Homeostatic regulation state (variable states, stability)
- ``bio_inspired.system_status``  — Overall BioCognitiveArchitecture status

Topics consumed
~~~~~~~~~~~~~~~
- ``reasoning``                   — Reasoning results → optimization targets / evaluation data
- ``consciousness``               — Consciousness state → homeostatic disturbances
- ``cognitive_synergy``           — Synergy metrics → fitness evaluation criteria

Events emitted
~~~~~~~~~~~~~~
- ``bio_inspired.fitness.improved``       — New best fitness found
- ``bio_inspired.homeostasis.alert``      — Emergency homeostatic condition
- ``bio_inspired.system_status.changed``  — Architecture state transition

Events listened
~~~~~~~~~~~~~~~
- ``reasoning.inference.completed``       — Feed into optimizer evaluation
- ``consciousness.state.changed``         — Modulate homeostatic targets
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

# Lazy imports — the bio_inspired module may not be available
_bio_inspired_module = None


def _get_bio_inspired():
    """Lazy import of bio_inspired module to allow graceful degradation."""
    global _bio_inspired_module
    if _bio_inspired_module is None:
        try:
            from asi_build import bio_inspired as _bm

            _bio_inspired_module = _bm
        except (ImportError, ModuleNotFoundError):
            _bio_inspired_module = False
    return _bio_inspired_module if _bio_inspired_module is not False else None


class BioInspiredAdapter:
    """Adapter connecting the bio-inspired module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``BioCognitiveArchitecture`` — overall bio-cognitive system status
    - ``EvolutionaryOptimizer`` — evolutionary optimization and fitness tracking
    - ``HomeostaticRegulator`` — homeostatic regulation and stability

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    architecture : optional
        A ``BioCognitiveArchitecture`` instance.
    optimizer : optional
        An ``EvolutionaryOptimizer`` instance.
    regulator : optional
        A ``HomeostaticRegulator`` instance.
    fitness_ttl : float
        TTL in seconds for fitness entries (default 300 = 5 minutes).
    population_ttl : float
        TTL for population statistics entries (default 120 = 2 minutes).
    homeostasis_ttl : float
        TTL for homeostasis entries (default 60 = 1 minute).
    status_ttl : float
        TTL for system status entries (default 120 = 2 minutes).
    """

    # ── Protocol-required property ────────────────────────────────────
    MODULE_NAME = "bio_inspired"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        architecture: Any = None,
        optimizer: Any = None,
        regulator: Any = None,
        *,
        fitness_ttl: float = 300.0,
        population_ttl: float = 120.0,
        homeostasis_ttl: float = 60.0,
        status_ttl: float = 120.0,
    ) -> None:
        self._architecture = architecture
        self._optimizer = optimizer
        self._regulator = regulator
        self._fitness_ttl = fitness_ttl
        self._population_ttl = population_ttl
        self._homeostasis_ttl = homeostasis_ttl
        self._status_ttl = status_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Track last values for change detection
        self._last_best_fitness: Optional[float] = None
        self._last_stability: Optional[float] = None
        self._last_status: Optional[str] = None

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
                "Bio-inspired module: evolutionary optimization, homeostatic "
                "regulation, and bio-cognitive architecture status."
            ),
            topics_produced=frozenset(
                {
                    "bio_inspired.fitness",
                    "bio_inspired.population",
                    "bio_inspired.homeostasis",
                    "bio_inspired.system_status",
                }
            ),
            topics_consumed=frozenset(
                {
                    "reasoning",
                    "consciousness",
                    "cognitive_synergy",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "BioInspiredAdapter registered with blackboard "
            "(architecture=%s, optimizer=%s, regulator=%s)",
            self._architecture is not None,
            self._optimizer is not None,
            self._regulator is not None,
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

        Routes reasoning inferences into the optimizer as evaluation data,
        and consciousness state changes into homeostatic target modulation.
        """
        try:
            if event.event_type.startswith("reasoning."):
                self._handle_reasoning_event(event)
            elif event.event_type.startswith("consciousness."):
                self._handle_consciousness_event(event)
        except Exception:
            logger.debug(
                "BioInspiredAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current bio-inspired state.

        Called during a production sweep.  Collects:
        1. Best fitness from EvolutionaryOptimizer
        2. Population statistics from EvolutionaryOptimizer
        3. Homeostatic regulation state from HomeostaticRegulator
        4. Overall system status from BioCognitiveArchitecture
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            fitness_entry = self._produce_fitness()
            if fitness_entry is not None:
                entries.append(fitness_entry)

            pop_entry = self._produce_population()
            if pop_entry is not None:
                entries.append(pop_entry)

            homeo_entry = self._produce_homeostasis()
            if homeo_entry is not None:
                entries.append(homeo_entry)

            status_entry = self._produce_system_status()
            if status_entry is not None:
                entries.append(status_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        Reasoning results → feed into optimizer as evaluation data.
        Consciousness state → homeostatic disturbances (e.g. arousal).
        Synergy metrics → fitness evaluation criteria.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
                elif entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
                elif entry.topic.startswith("cognitive_synergy."):
                    self._consume_synergy(entry)
            except Exception:
                logger.debug(
                    "BioInspiredAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_fitness(self) -> Optional[BlackboardEntry]:
        """Read best fitness from optimizer and return an entry if improved >1%."""
        if self._optimizer is None:
            return None

        try:
            best_fitness = self._optimizer.best_fitness
        except (AttributeError, Exception):
            logger.debug("Optimizer best_fitness unavailable", exc_info=True)
            return None

        if best_fitness is None:
            return None

        # Only post if fitness improved by >1%
        if self._last_best_fitness is not None:
            if self._last_best_fitness == 0:
                if best_fitness == 0:
                    return None
            else:
                improvement = (best_fitness - self._last_best_fitness) / max(
                    abs(self._last_best_fitness), 1e-9
                )
                if improvement <= 0.01:
                    return None

        self._last_best_fitness = best_fitness

        metadata: Dict[str, Any] = {"best_fitness": best_fitness}
        try:
            metadata["generation"] = getattr(self._optimizer, "generation", None)
        except Exception:
            pass

        entry = BlackboardEntry(
            topic="bio_inspired.fitness",
            data=metadata,
            source_module=self.MODULE_NAME,
            confidence=min(1.0, best_fitness),
            priority=EntryPriority.HIGH if best_fitness > 0.9 else EntryPriority.NORMAL,
            ttl_seconds=self._fitness_ttl,
            tags=frozenset({"evolutionary", "fitness", "optimization"}),
            metadata={"best_fitness": best_fitness},
        )

        self._emit(
            "bio_inspired.fitness.improved",
            {"best_fitness": best_fitness, "entry_id": entry.entry_id},
        )
        return entry

    def _produce_population(self) -> Optional[BlackboardEntry]:
        """Capture population statistics from the optimizer."""
        if self._optimizer is None:
            return None

        try:
            stats: Dict[str, Any] = {}
            stats["generation"] = getattr(self._optimizer, "generation", 0)
            stats["population_size"] = getattr(self._optimizer, "population_size", 0)
            stats["diversity"] = getattr(self._optimizer, "diversity", None)
            stats["mean_fitness"] = getattr(self._optimizer, "mean_fitness", None)
        except Exception:
            return None

        # Always post population stats (no change detection — these are informational)
        return BlackboardEntry(
            topic="bio_inspired.population",
            data=stats,
            source_module=self.MODULE_NAME,
            confidence=0.8,
            priority=EntryPriority.LOW,
            ttl_seconds=self._population_ttl,
            tags=frozenset({"evolutionary", "population", "statistics"}),
        )

    def _produce_homeostasis(self) -> Optional[BlackboardEntry]:
        """Snapshot homeostatic regulation state."""
        if self._regulator is None:
            return None

        try:
            state = self._regulator.get_state()
        except Exception:
            logger.debug("HomeostaticRegulator get_state() failed", exc_info=True)
            return None

        if state is None:
            return None

        state_data = state if isinstance(state, dict) else {"raw": state}
        stability = state_data.get("stability", state_data.get("balance", None))

        # Only post if stability changed by >5%
        if stability is not None and self._last_stability is not None:
            delta = abs(stability - self._last_stability)
            if self._last_stability == 0:
                if delta < 0.05:
                    return None
            elif delta / max(abs(self._last_stability), 1e-9) <= 0.05:
                return None

        if stability is not None:
            self._last_stability = stability

        is_emergency = state_data.get("emergency", False) or (
            stability is not None and stability < 0.2
        )

        entry = BlackboardEntry(
            topic="bio_inspired.homeostasis",
            data=state_data,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.CRITICAL if is_emergency else EntryPriority.NORMAL,
            ttl_seconds=self._homeostasis_ttl,
            tags=frozenset({"homeostasis", "regulation", "stability"}),
            metadata={"stability": stability},
        )

        if is_emergency:
            self._emit(
                "bio_inspired.homeostasis.alert",
                {"stability": stability, "state": state_data, "entry_id": entry.entry_id},
            )

        return entry

    def _produce_system_status(self) -> Optional[BlackboardEntry]:
        """Snapshot overall BioCognitiveArchitecture status."""
        if self._architecture is None:
            return None

        try:
            status_data = self._architecture.get_status()
        except Exception:
            return None

        if status_data is None:
            return None

        status_data = status_data if isinstance(status_data, dict) else {"raw": status_data}
        status_name = str(
            status_data.get("state", status_data.get("status", ""))
        )

        # Only post if state changed
        if status_name == self._last_status:
            return None
        self._last_status = status_name

        entry = BlackboardEntry(
            topic="bio_inspired.system_status",
            data=status_data,
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._status_ttl,
            tags=frozenset({"system", "status", "bio_cognitive"}),
            metadata={"status_name": status_name},
        )

        self._emit(
            "bio_inspired.system_status.changed",
            {"new_status": status_name, "entry_id": entry.entry_id},
        )
        return entry

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Feed reasoning results into optimizer as evaluation data."""
        if self._optimizer is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        eval_data = {
            "source": f"reasoning:{entry.entry_id}",
            "confidence": entry.confidence,
            "result": data,
            "timestamp": time.time(),
        }
        if hasattr(self._optimizer, "add_evaluation_data"):
            self._optimizer.add_evaluation_data(eval_data)

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Route consciousness state into homeostatic disturbances."""
        if self._regulator is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        # Extract arousal/attention level as a homeostatic disturbance
        arousal = data.get("phi", data.get("arousal", data.get("activation", None)))
        if arousal is not None and hasattr(self._regulator, "apply_disturbance"):
            self._regulator.apply_disturbance("arousal", float(arousal))

    def _consume_synergy(self, entry: BlackboardEntry) -> None:
        """Use synergy metrics as fitness evaluation criteria."""
        if self._optimizer is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        coherence = data.get("global_coherence", data.get("coherence", None))
        if coherence is not None and hasattr(self._optimizer, "set_fitness_criterion"):
            self._optimizer.set_fitness_criterion("synergy_coherence", float(coherence))

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_reasoning_event(self, event: CognitiveEvent) -> None:
        """Convert a reasoning event into optimizer evaluation data."""
        if self._optimizer is None:
            return
        if hasattr(self._optimizer, "add_evaluation_data"):
            self._optimizer.add_evaluation_data(
                {
                    "source": f"event:{event.event_id}",
                    "payload": event.payload,
                    "timestamp": time.time(),
                }
            )

    def _handle_consciousness_event(self, event: CognitiveEvent) -> None:
        """Convert a consciousness event into homeostatic target modulation."""
        if self._regulator is None:
            return
        payload = event.payload or {}
        new_state = payload.get("new_state", payload.get("state", None))
        if new_state is not None and hasattr(self._regulator, "modulate_target"):
            self._regulator.modulate_target("consciousness_state", str(new_state))

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all bio-inspired components.

        Useful for debugging and dashboard display.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_architecture": self._architecture is not None,
            "has_optimizer": self._optimizer is not None,
            "has_regulator": self._regulator is not None,
            "last_best_fitness": self._last_best_fitness,
            "last_stability": self._last_stability,
            "last_status": self._last_status,
            "registered": self._blackboard is not None,
        }

        if self._optimizer is not None:
            try:
                snap["current_fitness"] = self._optimizer.best_fitness
                snap["generation"] = getattr(self._optimizer, "generation", None)
            except Exception:
                snap["current_fitness"] = None

        if self._regulator is not None:
            try:
                snap["homeostasis_state"] = self._regulator.get_state()
            except Exception:
                snap["homeostasis_state"] = None

        if self._architecture is not None:
            try:
                snap["system_status"] = self._architecture.get_status()
            except Exception:
                snap["system_status"] = None

        return snap
