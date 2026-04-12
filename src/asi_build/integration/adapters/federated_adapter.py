"""
Federated Learning ↔ Blackboard Adapter
=========================================

Bridges the Federated Learning module (``FederatedManager``,
``FederatedServer``, ``FedAvgAggregator``, ``FederatedMetrics``) with the
Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``federated.round.result``          — Round completion with aggregation stats
- ``federated.training.status``       — Training lifecycle (start/stop/convergence)
- ``federated.client.update``         — Client training metrics
- ``federated.aggregation.stats``     — Aggregation statistics per round
- ``federated.convergence.analysis``  — Convergence tracking and detection
- ``federated.performance.metrics``   — Round times, communication overhead

Topics consumed
~~~~~~~~~~~~~~~
- ``consciousness.*``   — Attention-weighted client selection
- ``reasoning.*``       — Strategic reasoning for hyperparameter tuning
- ``quantum.*``         — Quantum-enhanced aggregation potential

Events emitted
~~~~~~~~~~~~~~
- ``federated.training.started``       — Training loop initiated
- ``federated.training.stopped``       — Training loop terminated
- ``federated.round.completed``        — Round finished (includes round number)
- ``federated.convergence.detected``   — Training converged
- ``federated.client.joined``          — New client registered

Events listened
~~~~~~~~~~~~~~~
- ``consciousness.state.changed``      — Adjust client selection attention
- ``reasoning.inference.completed``    — Feed into HP tuning strategy
- ``quantum.optimization.result``      — Quantum aggregation hints
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
# Lazy import — the federated module may not be available
# ---------------------------------------------------------------------------
_federated_module = None


def _get_federated():
    """Lazy import of federated module for graceful degradation."""
    global _federated_module
    if _federated_module is None:
        try:
            from asi_build import federated as _fm

            _federated_module = _fm
        except (ImportError, ModuleNotFoundError):
            _federated_module = False
    return _federated_module if _federated_module is not False else None


class FederatedLearningBlackboardAdapter:
    """Adapter connecting the Federated Learning module to the Cognitive Blackboard.

    Wraps up to four components:

    - ``FederatedManager`` — orchestrates federated learning rounds
    - ``FederatedServer`` — central server for model aggregation
    - ``FedAvgAggregator`` — Federated Averaging aggregation strategy
    - ``FederatedMetrics`` — training metrics tracking and analysis

    All components are optional; the adapter gracefully skips operations for
    any component that is ``None``.

    Parameters
    ----------
    manager : optional
        A ``FederatedManager`` instance.
    server : optional
        A ``FederatedServer`` instance.
    aggregator : optional
        A ``FedAvgAggregator`` instance.
    metrics : optional
        A ``FederatedMetrics`` instance.
    round_ttl : float
        TTL in seconds for round result entries (default 300).
    status_ttl : float
        TTL for training status entries (default 120).
    client_ttl : float
        TTL for client update entries (default 180).
    convergence_ttl : float
        TTL for convergence analysis entries (default 600).
    performance_ttl : float
        TTL for performance metric entries (default 120).
    """

    MODULE_NAME = "federated_learning"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        manager: Any = None,
        server: Any = None,
        aggregator: Any = None,
        metrics: Any = None,
        *,
        round_ttl: float = 300.0,
        status_ttl: float = 120.0,
        client_ttl: float = 180.0,
        convergence_ttl: float = 600.0,
        performance_ttl: float = 120.0,
    ) -> None:
        self._manager = manager
        self._server = server
        self._aggregator = aggregator
        self._metrics = metrics

        self._round_ttl = round_ttl
        self._status_ttl = status_ttl
        self._client_ttl = client_ttl
        self._convergence_ttl = convergence_ttl
        self._performance_ttl = performance_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change-detection state
        self._last_round: int = -1
        self._last_is_training: Optional[bool] = None
        self._last_num_clients: int = 0
        self._last_convergence_status: Optional[bool] = None
        self._last_performance_snapshot: Optional[Dict[str, Any]] = None

    # ── BlackboardParticipant protocol ────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER
                | ModuleCapability.CONSUMER
                | ModuleCapability.LEARNER
            ),
            description=(
                "Federated Learning module: round orchestration, server "
                "aggregation, FedAvg strategy, convergence tracking, and "
                "performance metrics."
            ),
            topics_produced=frozenset(
                {
                    "federated.round.result",
                    "federated.training.status",
                    "federated.client.update",
                    "federated.aggregation.stats",
                    "federated.convergence.analysis",
                    "federated.performance.metrics",
                }
            ),
            topics_consumed=frozenset(
                {
                    "consciousness",
                    "reasoning",
                    "quantum",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "FederatedLearningBlackboardAdapter registered with blackboard "
            "(manager=%s, server=%s, aggregator=%s, metrics=%s)",
            self._manager is not None,
            self._server is not None,
            self._aggregator is not None,
            self._metrics is not None,
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

        Routes consciousness state changes for attention-weighted client
        selection, reasoning results for HP tuning, and quantum optimization
        hints for aggregation.
        """
        try:
            if event.event_type.startswith("consciousness."):
                self._handle_consciousness_event(event)
            elif event.event_type.startswith("reasoning."):
                self._handle_reasoning_event(event)
            elif event.event_type.startswith("quantum."):
                self._handle_quantum_event(event)
        except Exception:
            logger.debug(
                "FederatedAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current federated state.

        Called during a production sweep.  Collects:
        1. Training status (is_training, current_round, client count)
        2. Latest round results (aggregation stats)
        3. Client updates
        4. Convergence analysis
        5. Performance metrics
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            status_entry = self._produce_training_status()
            if status_entry is not None:
                entries.append(status_entry)

            round_entry = self._produce_round_result()
            if round_entry is not None:
                entries.append(round_entry)

            agg_entry = self._produce_aggregation_stats()
            if agg_entry is not None:
                entries.append(agg_entry)

            convergence_entry = self._produce_convergence()
            if convergence_entry is not None:
                entries.append(convergence_entry)

            performance_entry = self._produce_performance()
            if performance_entry is not None:
                entries.append(performance_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        - ``consciousness.*``  — Attention scores for weighted client selection
        - ``reasoning.*``      — Strategic reasoning for hyperparameter tuning
        - ``quantum.*``        — Quantum optimization results for aggregation
        """
        for entry in entries:
            try:
                if entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
                elif entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
                elif entry.topic.startswith("quantum."):
                    self._consume_quantum(entry)
            except Exception:
                logger.debug(
                    "FederatedAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_training_status(self) -> Optional[BlackboardEntry]:
        """Produce training status entry with change detection."""
        if self._manager is None:
            return None

        try:
            status = self._manager.get_training_status()
        except Exception:
            logger.debug("Failed to get training status", exc_info=True)
            return None

        is_training = status.get("is_training", False)
        current_round = status.get("current_round", 0)
        num_clients = status.get("num_clients", 0)

        # Change detection — status or client count changed
        if (
            is_training == self._last_is_training
            and num_clients == self._last_num_clients
            and current_round == self._last_round
        ):
            return None

        # Detect state transitions
        was_training = self._last_is_training
        self._last_is_training = is_training
        self._last_num_clients = num_clients

        entry = BlackboardEntry(
            topic="federated.training.status",
            data={
                "is_training": is_training,
                "current_round": current_round,
                "total_rounds": status.get("total_rounds", 0),
                "num_clients": num_clients,
                "convergence_metrics": status.get("convergence_metrics", {}),
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=(
                EntryPriority.HIGH if is_training else EntryPriority.NORMAL
            ),
            ttl_seconds=self._status_ttl,
            tags=frozenset({"training", "status", "lifecycle"}),
            metadata={
                "is_training": is_training,
                "round": current_round,
            },
        )

        # Emit lifecycle events
        if is_training and was_training is False:
            self._emit(
                "federated.training.started",
                {"round": current_round, "clients": num_clients},
            )
        elif not is_training and was_training is True:
            self._emit(
                "federated.training.stopped",
                {"final_round": current_round, "clients": num_clients},
            )

        # Emit client join/leave events
        if num_clients > self._last_num_clients:
            self._emit(
                "federated.client.joined",
                {
                    "new_count": num_clients,
                    "previous_count": self._last_num_clients,
                },
            )

        return entry

    def _produce_round_result(self) -> Optional[BlackboardEntry]:
        """Produce round result entry when a new round completes."""
        if self._manager is None:
            return None

        try:
            status = self._manager.get_training_status()
            current_round = status.get("current_round", 0)
        except Exception:
            return None

        if current_round <= self._last_round:
            return None
        self._last_round = current_round

        try:
            # Get comprehensive summary for the completed round
            summary = self._manager.get_comprehensive_summary()
        except Exception:
            summary = {"round": current_round}

        entry = BlackboardEntry(
            topic="federated.round.result",
            data={
                "round": current_round,
                "selected_clients": summary.get("selected_clients", []),
                "aggregation_stats": summary.get("aggregation_stats", {}),
                "model_metrics": summary.get("model_metrics", {}),
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.HIGH,
            ttl_seconds=self._round_ttl,
            tags=frozenset({"round", "result", "aggregation"}),
            metadata={"round": current_round},
        )

        self._emit(
            "federated.round.completed",
            {"round": current_round, "entry_id": entry.entry_id},
        )
        return entry

    def _produce_aggregation_stats(self) -> Optional[BlackboardEntry]:
        """Produce aggregation-specific statistics."""
        if self._aggregator is None:
            return None

        try:
            stats = self._aggregator.get_fedavg_specific_stats()
        except Exception:
            try:
                # Fallback to general stats
                stats = getattr(self._aggregator, "get_stats", lambda: {})()
            except Exception:
                return None

        if not stats:
            return None

        entry = BlackboardEntry(
            topic="federated.aggregation.stats",
            data={
                "strategy": "fedavg",
                "total_aggregations": stats.get("total_aggregations", 0),
                "avg_weight_divergence": stats.get("avg_weight_divergence", 0.0),
                "client_contribution_weights": stats.get(
                    "client_contribution_weights", {}
                ),
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._round_ttl,
            tags=frozenset({"aggregation", "fedavg", "stats"}),
        )
        return entry

    def _produce_convergence(self) -> Optional[BlackboardEntry]:
        """Produce convergence analysis entry."""
        if self._server is None and self._metrics is None:
            return None

        converged = False
        convergence_data: Dict[str, Any] = {}

        # Check via server
        if self._server is not None:
            try:
                converged = self._server.check_convergence(threshold=0.001)
                convergence_data["converged"] = converged
            except Exception:
                pass

        # Enrich with metrics
        if self._metrics is not None:
            try:
                perf = self._metrics.get_performance_summary()
                convergence_data.update(
                    {
                        "loss_trend": perf.get("loss_trend", []),
                        "accuracy_trend": perf.get("accuracy_trend", []),
                        "best_loss": perf.get("best_loss"),
                        "best_accuracy": perf.get("best_accuracy"),
                    }
                )
            except Exception:
                pass

        if not convergence_data:
            return None

        # Change detection
        if converged == self._last_convergence_status:
            return None
        self._last_convergence_status = converged

        convergence_data["timestamp"] = time.time()

        entry = BlackboardEntry(
            topic="federated.convergence.analysis",
            data=convergence_data,
            source_module=self.MODULE_NAME,
            confidence=0.85 if converged else 0.7,
            priority=(
                EntryPriority.HIGH if converged else EntryPriority.NORMAL
            ),
            ttl_seconds=self._convergence_ttl,
            tags=frozenset({"convergence", "analysis"}),
            metadata={"converged": converged},
        )

        if converged:
            self._emit(
                "federated.convergence.detected",
                {"entry_id": entry.entry_id, "converged": True},
            )

        return entry

    def _produce_performance(self) -> Optional[BlackboardEntry]:
        """Produce performance metrics entry."""
        if self._metrics is None:
            return None

        try:
            perf = self._metrics.get_performance_summary()
        except Exception:
            return None

        if not perf:
            return None

        # Change detection — compare key metrics
        perf_key = {
            "total_rounds": perf.get("total_rounds"),
            "avg_round_time": perf.get("avg_round_time"),
        }
        if perf_key == self._last_performance_snapshot:
            return None
        self._last_performance_snapshot = perf_key

        entry = BlackboardEntry(
            topic="federated.performance.metrics",
            data={
                "total_rounds": perf.get("total_rounds", 0),
                "avg_round_time": perf.get("avg_round_time", 0.0),
                "avg_aggregation_time": perf.get("avg_aggregation_time", 0.0),
                "communication_overhead": perf.get("communication_overhead", 0.0),
                "efficiency": perf.get("efficiency", 0.0),
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._performance_ttl,
            tags=frozenset({"performance", "metrics", "timing"}),
        )
        return entry

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Use consciousness state for attention-weighted client selection.

        Higher Φ values or focused states may weight certain clients more
        heavily during the selection phase.
        """
        if self._server is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        phi = data.get("phi", data.get("phi_value"))

        if phi is not None and hasattr(self._server, "attention_weights"):
            try:
                # Scale attention weighting with consciousness level
                self._server.attention_weights = {
                    "consciousness_factor": min(1.0, float(phi) / 5.0)
                }
            except (TypeError, ValueError, AttributeError):
                pass

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Feed reasoning results into hyperparameter tuning.

        Strategic reasoning about learning rate scheduling, batch sizes,
        or client selection strategies.
        """
        if self._manager is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        hp_suggestion = data.get("hyperparameter_suggestion", data.get("optimization"))

        if hp_suggestion is not None and isinstance(hp_suggestion, dict):
            logger.debug(
                "Received HP suggestion from reasoning: %s",
                str(hp_suggestion)[:100],
            )
            # HP suggestions influence next round configuration
            if hasattr(self._manager, "config") and self._manager.config is not None:
                for key in ("learning_rate", "batch_size", "num_epochs"):
                    if key in hp_suggestion:
                        try:
                            setattr(self._manager.config, key, hp_suggestion[key])
                        except (AttributeError, TypeError):
                            pass

    def _consume_quantum(self, entry: BlackboardEntry) -> None:
        """Use quantum optimization results for enhanced aggregation.

        Quantum kernel or QAOA results can guide the aggregation weighting
        across heterogeneous client updates.
        """
        if self._aggregator is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        optimal_weights = data.get("optimal_weights", data.get("weights"))

        if optimal_weights is not None and hasattr(
            self._aggregator, "quantum_weights"
        ):
            try:
                self._aggregator.quantum_weights = optimal_weights
                logger.debug(
                    "Applied quantum-optimized aggregation weights: %s",
                    str(optimal_weights)[:100],
                )
            except (TypeError, AttributeError):
                pass

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_consciousness_event(self, event: CognitiveEvent) -> None:
        """Handle consciousness state changes for client selection."""
        payload = event.payload or {}
        new_state = payload.get("new_state", "")

        if self._server is not None and hasattr(self._server, "selection_strategy"):
            try:
                # High-consciousness states → more selective (pick best clients)
                if new_state in ("focused", "broadcasting"):
                    self._server.selection_strategy = "quality_weighted"
                else:
                    self._server.selection_strategy = "random"
            except AttributeError:
                pass

    def _handle_reasoning_event(self, event: CognitiveEvent) -> None:
        """Handle reasoning events for training strategy adaptation."""
        payload = event.payload or {}
        if "convergence_prediction" in payload:
            logger.debug(
                "Reasoning predicts convergence at round %s",
                payload.get("convergence_prediction"),
            )

    def _handle_quantum_event(self, event: CognitiveEvent) -> None:
        """Handle quantum optimization events for aggregation."""
        payload = event.payload or {}
        if "optimization_result" in payload or "energy" in payload:
            logger.debug(
                "Quantum optimization event received for aggregation tuning"
            )

    # ── Snapshot ──────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all federated learning components.

        Useful for debugging and dashboard display.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_manager": self._manager is not None,
            "has_server": self._server is not None,
            "has_aggregator": self._aggregator is not None,
            "has_metrics": self._metrics is not None,
            "last_round": self._last_round,
            "is_training": self._last_is_training,
            "num_clients": self._last_num_clients,
            "converged": self._last_convergence_status,
            "registered": self._blackboard is not None,
        }

        if self._manager is not None:
            try:
                snap["training_status"] = self._manager.get_training_status()
            except Exception:
                snap["training_status"] = None

        if self._server is not None:
            try:
                snap["server_status"] = self._server.get_server_status()
            except Exception:
                snap["server_status"] = None

        if self._aggregator is not None:
            try:
                snap["aggregation_stats"] = self._aggregator.get_fedavg_specific_stats()
            except Exception:
                snap["aggregation_stats"] = None

        if self._metrics is not None:
            try:
                snap["performance_summary"] = self._metrics.get_performance_summary()
            except Exception:
                snap["performance_summary"] = None

        return snap
