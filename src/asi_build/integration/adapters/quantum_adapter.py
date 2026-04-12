"""
Quantum ↔ Blackboard Adapter
==============================

Bridges the quantum computing module (``QuantumSimulator``,
``HybridMLProcessor``, ``QAOA``, ``VQE``, ``KennyQuantumIntegration``)
with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``quantum.circuit.result``         — Circuit execution results (state vector, stats)
- ``quantum.optimization.result``    — QAOA / VQE optimization outcomes
- ``quantum.ml.prediction``          — Hybrid quantum-classical ML predictions
- ``quantum.metrics``                — Quantum processing metrics snapshot

Topics consumed
~~~~~~~~~~~~~~~
- ``reasoning.*``                    — Optimization problems from the reasoning engine
- ``knowledge_graph.*``              — Graph structures for quantum graph optimization
- ``cognitive_synergy.*``            — Multi-module coordination tasks

Events emitted
~~~~~~~~~~~~~~
- ``quantum.circuit.executed``       — A circuit finished execution
- ``quantum.optimization.completed`` — QAOA/VQE converged on a solution
- ``quantum.ml.predicted``           — Hybrid ML produced a new prediction
- ``quantum.metrics.updated``        — Fresh metrics available

Events listened
~~~~~~~~~~~~~~~
- ``reasoning.inference.completed``        — Queue inferred optimization problem
- ``knowledge_graph.triple.added``         — Graph structure for quantum optimization
- ``cognitive_synergy.emergence.detected`` — Coordination optimization trigger
"""

from __future__ import annotations

import hashlib
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
# Lazy imports — the quantum module may not be available
# ---------------------------------------------------------------------------
_quantum_module = None


def _get_quantum():
    """Lazy import of the quantum module to allow graceful degradation."""
    global _quantum_module
    if _quantum_module is None:
        try:
            from asi_build import quantum as _qm

            _quantum_module = _qm
        except (ImportError, ModuleNotFoundError):
            _quantum_module = False
    return _quantum_module if _quantum_module is not False else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_array(arr: Any) -> str:
    """Produce a stable hex digest for a numpy-like array or dict.

    Falls back to ``str(arr)`` when numpy is unavailable.
    """
    try:
        import numpy as np

        if isinstance(arr, np.ndarray):
            return hashlib.sha256(arr.tobytes()).hexdigest()[:16]
    except ImportError:
        pass
    return hashlib.sha256(str(arr).encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class QuantumBlackboardAdapter:
    """Adapter connecting the quantum computing module to the Cognitive Blackboard.

    Wraps up to five components:

    - ``QuantumSimulator``          — state-vector circuit simulation
    - ``HybridMLProcessor``         — quantum-classical hybrid ML pipeline
    - ``QAOA``                      — Quantum Approximate Optimization Algorithm
    - ``VQE``                       — Variational Quantum Eigensolver
    - ``KennyQuantumIntegration``   — high-level decision / pattern / coordination

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    simulator : optional
        A ``QuantumSimulator`` instance.
    hybrid_ml : optional
        A ``HybridMLProcessor`` instance.
    qaoa : optional
        A ``QAOA`` instance.
    vqe : optional
        A ``VQE`` instance.
    kenny_integration : optional
        A ``KennyQuantumIntegration`` instance.
    circuit_ttl : float
        TTL in seconds for circuit result entries (default 300 = 5 min).
    optimization_ttl : float
        TTL for optimization result entries (default 600 = 10 min).
    ml_ttl : float
        TTL for ML prediction entries (default 120 = 2 min).
    metrics_ttl : float
        TTL for metrics snapshot entries (default 60 = 1 min).
    """

    # ── Protocol-required class attributes ────────────────────────────
    MODULE_NAME = "quantum"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        simulator: Any = None,
        hybrid_ml: Any = None,
        qaoa: Any = None,
        vqe: Any = None,
        kenny_integration: Any = None,
        *,
        circuit_ttl: float = 300.0,
        optimization_ttl: float = 600.0,
        ml_ttl: float = 120.0,
        metrics_ttl: float = 60.0,
    ) -> None:
        self._simulator = simulator
        self._hybrid_ml = hybrid_ml
        self._qaoa = qaoa
        self._vqe = vqe
        self._kenny = kenny_integration

        self._circuit_ttl = circuit_ttl
        self._optimization_ttl = optimization_ttl
        self._ml_ttl = ml_ttl
        self._metrics_ttl = metrics_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change-detection state
        self._last_state_vector_hash: Optional[str] = None
        self._last_optimization_energy: Optional[float] = None
        self._last_ml_prediction_hash: Optional[str] = None
        self._last_fidelity: Optional[float] = None
        self._last_error_rate: Optional[float] = None

        # Queued work from consumed entries / events
        self._optimization_queue: List[Dict[str, Any]] = []
        self._graph_optimization_queue: List[Dict[str, Any]] = []
        self._coordination_queue: List[Dict[str, Any]] = []

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
            ),
            description=(
                "Quantum computing module: circuit simulation (QuantumSimulator), "
                "hybrid quantum-classical ML (HybridMLProcessor), "
                "QAOA / VQE optimization, and multi-agent coordination "
                "(KennyQuantumIntegration)."
            ),
            topics_produced=frozenset(
                {
                    "quantum.circuit.result",
                    "quantum.optimization.result",
                    "quantum.ml.prediction",
                    "quantum.metrics",
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
            "QuantumBlackboardAdapter registered with blackboard "
            "(simulator=%s, hybrid_ml=%s, qaoa=%s, vqe=%s, kenny=%s)",
            self._simulator is not None,
            self._hybrid_ml is not None,
            self._qaoa is not None,
            self._vqe is not None,
            self._kenny is not None,
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

        Routes events into internal work queues that are drained during
        the next ``consume()`` or ``produce()`` cycle.
        """
        try:
            if event.event_type.startswith("reasoning."):
                self._queue_optimization_from_event(event)
            elif event.event_type.startswith("knowledge_graph."):
                self._queue_graph_optimization_from_event(event)
            elif event.event_type.startswith("cognitive_synergy."):
                self._queue_coordination_from_event(event)
        except Exception:
            logger.debug(
                "QuantumBlackboardAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current quantum state.

        Called during a production sweep.  Collects:
        1. Latest circuit execution result from QuantumSimulator
        2. Latest QAOA/VQE optimization result
        3. Latest hybrid-ML prediction
        4. Quantum processing metrics snapshot
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            circuit_entry = self._produce_circuit_result()
            if circuit_entry is not None:
                entries.append(circuit_entry)

            opt_entry = self._produce_optimization_result()
            if opt_entry is not None:
                entries.append(opt_entry)

            ml_entry = self._produce_ml_prediction()
            if ml_entry is not None:
                entries.append(ml_entry)

            metrics_entry = self._produce_metrics()
            if metrics_entry is not None:
                entries.append(metrics_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        Reasoning results → queue as optimization problems for QAOA / VQE.
        Knowledge-graph triples → queue as graph structures for quantum optimization.
        Cognitive-synergy data → queue for multi-agent coordination optimization.
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
                    "QuantumBlackboardAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── BlackboardTransformer protocol ────────────────────────────────

    def transform(self, entries: Sequence[BlackboardEntry]) -> Sequence[BlackboardEntry]:
        """Enrich entries with quantum metrics.

        Annotates each entry's *metadata* with:
        - ``quantum_fidelity``         — current simulator fidelity estimate
        - ``quantum_advantage_score``  — latest advantage score from HybridML
        - ``quantum_enriched``         — True flag

        Returns new entries (with ``parent_id`` provenance) for any entry
        that could be enriched.
        """
        enriched: List[BlackboardEntry] = []

        # Gather quantum context once
        fidelity = self._current_fidelity()
        advantage = self._current_advantage_score()

        if fidelity is None and advantage is None:
            return enriched  # nothing to contribute

        for entry in entries:
            try:
                new_meta = dict(entry.metadata)
                if fidelity is not None:
                    new_meta["quantum_fidelity"] = fidelity
                if advantage is not None:
                    new_meta["quantum_advantage_score"] = advantage
                new_meta["quantum_enriched"] = True

                enriched.append(
                    BlackboardEntry(
                        topic=entry.topic,
                        data=entry.data,
                        source_module=self.MODULE_NAME,
                        confidence=entry.confidence,
                        priority=entry.priority,
                        ttl_seconds=entry.ttl_seconds,
                        tags=entry.tags | frozenset({"quantum_enriched"}),
                        parent_id=entry.entry_id,
                        metadata=new_meta,
                    )
                )
            except Exception:
                logger.debug(
                    "QuantumBlackboardAdapter: failed to transform entry %s",
                    entry.entry_id,
                    exc_info=True,
                )

        return enriched

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_circuit_result(self) -> Optional[BlackboardEntry]:
        """Get latest circuit result from the simulator, with change detection on
        the state-vector hash."""
        if self._simulator is None:
            return None

        try:
            state_vector = self._simulator.get_state_vector()
        except Exception:
            logger.debug("QuantumSimulator.get_state_vector() failed", exc_info=True)
            return None

        if state_vector is None:
            return None

        sv_hash = _hash_array(state_vector)
        if sv_hash == self._last_state_vector_hash:
            return None  # no change
        self._last_state_vector_hash = sv_hash

        # Gather probabilities
        try:
            probabilities = self._simulator.get_probabilities()
        except Exception:
            probabilities = None

        data: Dict[str, Any] = {
            "state_vector_hash": sv_hash,
            "num_qubits": len(state_vector).bit_length() - 1,
        }
        if probabilities is not None:
            try:
                import numpy as np

                probs = np.asarray(probabilities, dtype=float)
                data["max_probability"] = float(np.max(probs))
                nonzero = probs[probs > 0]
                data["entropy"] = float(-np.sum(nonzero * np.log2(nonzero)))
            except Exception:
                pass

        # Include measurement stats if available
        measurement_results = getattr(self._simulator, "measurement_results", None)
        if measurement_results:
            data["measurement_count"] = len(measurement_results)

        entry = BlackboardEntry(
            topic="quantum.circuit.result",
            data=data,
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._circuit_ttl,
            tags=frozenset({"circuit", "state_vector", "simulation"}),
            metadata={"state_vector_hash": sv_hash},
        )

        self._emit(
            "quantum.circuit.executed",
            {"entry_id": entry.entry_id, "state_vector_hash": sv_hash},
        )
        return entry

    def _produce_optimization_result(self) -> Optional[BlackboardEntry]:
        """Get latest QAOA/VQE optimisation result, with change detection on
        the best energy value."""
        # Try QAOA first, then VQE
        source_name: Optional[str] = None
        energy: Optional[float] = None
        params: Optional[list] = None
        history: Optional[list] = None

        if self._qaoa is not None:
            opt_params = getattr(self._qaoa, "optimal_params", None)
            if opt_params is not None:
                try:
                    energy = float(
                        getattr(self._qaoa, "optimization_history", [{}])[-1].get(
                            "cost", None
                        )
                    ) if getattr(self._qaoa, "optimization_history", []) else None
                except (IndexError, TypeError, ValueError):
                    energy = None
                try:
                    import numpy as np
                    params = opt_params.tolist() if hasattr(opt_params, "tolist") else list(opt_params)
                except Exception:
                    params = list(opt_params)
                history = getattr(self._qaoa, "optimization_history", None)
                source_name = "qaoa"

        if energy is None and self._vqe is not None:
            opt_params = getattr(self._vqe, "optimal_params", None)
            if opt_params is not None:
                try:
                    import numpy as np
                    params = opt_params.tolist() if hasattr(opt_params, "tolist") else list(opt_params)
                except Exception:
                    params = list(opt_params)
                source_name = "vqe"
                # VQE doesn't keep optimization_history; signal that we have params
                energy = 0.0  # placeholder — will be overwritten below if available

        if energy is None:
            return None

        # Change detection on energy value
        if (
            self._last_optimization_energy is not None
            and energy is not None
            and abs(energy - self._last_optimization_energy) < 1e-8
        ):
            return None
        self._last_optimization_energy = energy

        data: Dict[str, Any] = {
            "algorithm": source_name,
            "best_energy": energy,
            "optimal_params": params,
        }
        if history:
            data["iterations"] = len(history)
            data["convergence_trace"] = [
                h.get("cost") for h in history[-10:]  # last 10 steps
            ]

        entry = BlackboardEntry(
            topic="quantum.optimization.result",
            data=data,
            source_module=self.MODULE_NAME,
            confidence=min(1.0, 0.5 + 0.5 / (1.0 + abs(energy))),
            priority=EntryPriority.HIGH,
            ttl_seconds=self._optimization_ttl,
            tags=frozenset({"optimization", source_name or "unknown"}),
            metadata={"algorithm": source_name, "energy": energy},
        )

        self._emit(
            "quantum.optimization.completed",
            {
                "entry_id": entry.entry_id,
                "algorithm": source_name,
                "energy": energy,
            },
        )
        return entry

    def _produce_ml_prediction(self) -> Optional[BlackboardEntry]:
        """Get latest HybridML result, with change detection on prediction hash."""
        if self._hybrid_ml is None:
            return None

        # HybridMLProcessor stores metrics incrementally; check if new data exists
        metrics = getattr(self._hybrid_ml, "metrics", {})
        adv_scores = metrics.get("quantum_advantage_scores", [])
        if not adv_scores:
            return None  # no predictions have been made yet

        # Build a hash from the latest metrics state
        try:
            import numpy as np

            pred_hash = hashlib.sha256(
                f"{len(adv_scores)}:{adv_scores[-1]:.8f}".encode()
            ).hexdigest()[:16]
        except Exception:
            pred_hash = str(len(adv_scores))

        if pred_hash == self._last_ml_prediction_hash:
            return None
        self._last_ml_prediction_hash = pred_hash

        latest_advantage = adv_scores[-1] if adv_scores else 0.0
        avg_advantage = sum(adv_scores) / len(adv_scores) if adv_scores else 0.0

        data: Dict[str, Any] = {
            "total_predictions": len(adv_scores),
            "latest_quantum_advantage": latest_advantage,
            "avg_quantum_advantage": avg_advantage,
            "quantum_processing_times": len(metrics.get("quantum_processing_time", [])),
        }

        entry = BlackboardEntry(
            topic="quantum.ml.prediction",
            data=data,
            source_module=self.MODULE_NAME,
            confidence=min(1.0, latest_advantage / 2.0),
            priority=(
                EntryPriority.HIGH if latest_advantage > 1.5 else EntryPriority.NORMAL
            ),
            ttl_seconds=self._ml_ttl,
            tags=frozenset({"hybrid_ml", "prediction", "quantum_advantage"}),
            metadata={"prediction_hash": pred_hash},
        )

        self._emit(
            "quantum.ml.predicted",
            {
                "entry_id": entry.entry_id,
                "advantage": latest_advantage,
            },
        )
        return entry

    def _produce_metrics(self) -> Optional[BlackboardEntry]:
        """Get quantum processing metrics from HybridMLProcessor, with change
        detection on fidelity and error-correction rate."""
        if self._hybrid_ml is None:
            return None

        try:
            qm = self._hybrid_ml.get_quantum_metrics()
        except Exception:
            logger.debug("HybridMLProcessor.get_quantum_metrics() failed", exc_info=True)
            return None

        if not qm or qm.get("status") == "no_data":
            return None

        fidelity = qm.get("error_correction_rate")
        error_rate = 1.0 - fidelity if fidelity is not None else None

        # Change detection — only post if fidelity or error_rate shifted
        if (
            self._last_fidelity is not None
            and fidelity is not None
            and abs(fidelity - self._last_fidelity) < 0.005
        ):
            if (
                self._last_error_rate is not None
                and error_rate is not None
                and abs(error_rate - self._last_error_rate) < 0.005
            ):
                return None  # neither changed enough
        self._last_fidelity = fidelity
        self._last_error_rate = error_rate

        data: Dict[str, Any] = dict(qm)
        if error_rate is not None:
            data["error_rate"] = error_rate

        entry = BlackboardEntry(
            topic="quantum.metrics",
            data=data,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._metrics_ttl,
            tags=frozenset({"metrics", "quantum", "performance"}),
            metadata={
                "fidelity": fidelity,
                "error_rate": error_rate,
            },
        )

        self._emit(
            "quantum.metrics.updated",
            {
                "entry_id": entry.entry_id,
                "fidelity": fidelity,
                "error_rate": error_rate,
            },
        )
        return entry

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Extract optimisation problems from reasoning results and queue
        them for QAOA / VQE processing."""
        if self._qaoa is None and self._vqe is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        # Look for structures that can be expressed as optimization problems
        problem: Optional[Dict[str, Any]] = None

        if "optimization_problem" in data:
            problem = data["optimization_problem"]
        elif "hypothesis" in data:
            # Treat hypothesis testing as an optimisation task
            problem = {
                "type": "hypothesis_test",
                "source_entry": entry.entry_id,
                "payload": data,
            }
        elif "inference" in data:
            problem = {
                "type": "inference_optimization",
                "source_entry": entry.entry_id,
                "payload": data.get("inference"),
            }

        if problem is not None:
            self._optimization_queue.append(problem)
            logger.debug(
                "Queued optimization problem from reasoning entry %s",
                entry.entry_id,
            )

    def _consume_kg(self, entry: BlackboardEntry) -> None:
        """Extract graph structures from knowledge-graph entries for quantum
        graph optimisation (e.g. MaxCut, graph partitioning)."""
        if self._kenny is None and self._qaoa is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        graph_item: Optional[Dict[str, Any]] = None

        if "adjacency_matrix" in data:
            graph_item = {
                "type": "graph_optimization",
                "source_entry": entry.entry_id,
                "adjacency_matrix": data["adjacency_matrix"],
            }
        elif "subject" in data and "predicate" in data and "object" in data:
            # Single triple — accumulate for batch graph building
            graph_item = {
                "type": "triple_accumulate",
                "source_entry": entry.entry_id,
                "triple": (data["subject"], data["predicate"], data["object"]),
            }
        elif "triples" in data:
            graph_item = {
                "type": "triple_batch",
                "source_entry": entry.entry_id,
                "triples": data["triples"],
            }

        if graph_item is not None:
            self._graph_optimization_queue.append(graph_item)
            logger.debug(
                "Queued graph optimization from KG entry %s",
                entry.entry_id,
            )

    def _consume_synergy(self, entry: BlackboardEntry) -> None:
        """Use KennyQuantumIntegration to optimise multi-module coordination
        tasks surfaced by the cognitive-synergy engine."""
        if self._kenny is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        coord_item: Optional[Dict[str, Any]] = None

        if "agents" in data and "tasks" in data:
            coord_item = {
                "type": "multi_agent_coordination",
                "source_entry": entry.entry_id,
                "agents": data["agents"],
                "tasks": data["tasks"],
            }
        elif "coherence" in data or "global_coherence" in data:
            coherence = data.get("global_coherence", data.get("coherence", 0.0))
            coord_item = {
                "type": "coherence_optimization",
                "source_entry": entry.entry_id,
                "coherence": coherence,
            }
        elif "emergence" in data:
            coord_item = {
                "type": "emergence_optimization",
                "source_entry": entry.entry_id,
                "emergence_data": data["emergence"],
            }

        if coord_item is not None:
            self._coordination_queue.append(coord_item)
            logger.debug(
                "Queued coordination task from synergy entry %s",
                entry.entry_id,
            )

    # ── Event → queue injection ───────────────────────────────────────

    def _queue_optimization_from_event(self, event: CognitiveEvent) -> None:
        """Convert a reasoning event into a queued optimization problem."""
        self._optimization_queue.append(
            {
                "type": "event_optimization",
                "source_event": event.event_id,
                "payload": event.payload,
            }
        )

    def _queue_graph_optimization_from_event(self, event: CognitiveEvent) -> None:
        """Convert a KG event into a queued graph optimization."""
        self._graph_optimization_queue.append(
            {
                "type": "event_graph_optimization",
                "source_event": event.event_id,
                "payload": event.payload,
            }
        )

    def _queue_coordination_from_event(self, event: CognitiveEvent) -> None:
        """Convert a synergy event into a queued coordination task."""
        self._coordination_queue.append(
            {
                "type": "event_coordination",
                "source_event": event.event_id,
                "payload": event.payload,
            }
        )

    # ── Internal metric helpers ───────────────────────────────────────

    def _current_fidelity(self) -> Optional[float]:
        """Return the most recent fidelity estimate, or ``None``."""
        if self._hybrid_ml is None:
            return None
        try:
            qm = self._hybrid_ml.get_quantum_metrics()
            return qm.get("error_correction_rate")
        except Exception:
            return None

    def _current_advantage_score(self) -> Optional[float]:
        """Return the latest quantum-advantage score, or ``None``."""
        if self._hybrid_ml is None:
            return None
        try:
            qm = self._hybrid_ml.get_quantum_metrics()
            return qm.get("avg_quantum_advantage")
        except Exception:
            return None

    # ── Convenience: diagnostic snapshot ──────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all quantum components.

        Useful for debugging and dashboard display.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_simulator": self._simulator is not None,
            "has_hybrid_ml": self._hybrid_ml is not None,
            "has_qaoa": self._qaoa is not None,
            "has_vqe": self._vqe is not None,
            "has_kenny_integration": self._kenny is not None,
            "last_state_vector_hash": self._last_state_vector_hash,
            "last_optimization_energy": self._last_optimization_energy,
            "last_ml_prediction_hash": self._last_ml_prediction_hash,
            "last_fidelity": self._last_fidelity,
            "last_error_rate": self._last_error_rate,
            "optimization_queue_depth": len(self._optimization_queue),
            "graph_optimization_queue_depth": len(self._graph_optimization_queue),
            "coordination_queue_depth": len(self._coordination_queue),
            "registered": self._blackboard is not None,
        }

        if self._simulator is not None:
            try:
                sv = self._simulator.get_state_vector()
                snap["simulator_active"] = sv is not None
                if sv is not None:
                    snap["simulator_num_qubits"] = len(sv).bit_length() - 1
            except Exception:
                snap["simulator_active"] = False

        if self._hybrid_ml is not None:
            try:
                qm = self._hybrid_ml.get_quantum_metrics()
                if qm and qm.get("status") != "no_data":
                    snap["quantum_metrics"] = qm
            except Exception:
                pass

        if self._qaoa is not None:
            snap["qaoa_has_solution"] = getattr(self._qaoa, "optimal_params", None) is not None
            snap["qaoa_history_len"] = len(
                getattr(self._qaoa, "optimization_history", [])
            )

        if self._vqe is not None:
            snap["vqe_has_solution"] = getattr(self._vqe, "optimal_params", None) is not None

        return snap
