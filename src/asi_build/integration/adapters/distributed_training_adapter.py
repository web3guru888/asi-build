"""
Distributed Training ↔ Blackboard Adapter
=============================================

Bridges the distributed training module (``FederatedOrchestrator``,
``ByzantineTolerantAggregator``, ``MetricsCollector``) with the Cognitive
Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``distributed_training.round_status``  — Current training round state and progress
- ``distributed_training.aggregation``   — Aggregation results (FedAvg, Krum, etc.)
- ``distributed_training.metrics``       — Training metrics (loss, accuracy, network health)

Topics consumed
~~~~~~~~~~~~~~~
- ``compute``                            — Compute resource updates → node capacity awareness
- ``reasoning``                          — Reasoning insights → training hyperparameter guidance
- ``consciousness``                      — Consciousness state → attention-weighted aggregation

Events emitted
~~~~~~~~~~~~~~
- ``distributed_training.round.completed``    — A training round has finished
- ``distributed_training.byzantine.detected`` — Byzantine node behavior detected

Events listened
~~~~~~~~~~~~~~~
- ``compute.resource.exhausted``              — Scale down training if resources exhausted
- ``consciousness.state.changed``             — Modulate training aggressiveness
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

_distributed_training_module = None


def _get_distributed_training():
    """Lazy import of distributed_training module to allow graceful degradation."""
    global _distributed_training_module
    if _distributed_training_module is None:
        try:
            from asi_build import distributed_training as _dtm

            _distributed_training_module = _dtm
        except (ImportError, ModuleNotFoundError):
            _distributed_training_module = False
    return _distributed_training_module if _distributed_training_module is not False else None


class DistributedTrainingAdapter:
    """Adapter connecting the distributed training module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``FederatedOrchestrator`` — federated learning orchestration and round management
    - ``ByzantineTolerantAggregator`` — gradient aggregation with Byzantine fault tolerance
    - ``MetricsCollector`` — training metrics collection and visualization

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    orchestrator : optional
        A ``FederatedOrchestrator`` instance.
    aggregator : optional
        A ``ByzantineTolerantAggregator`` instance.
    metrics_collector : optional
        A ``MetricsCollector`` (from distributed_training.monitoring.dashboard) instance.
    round_status_ttl : float
        TTL in seconds for round status entries (default 120).
    aggregation_ttl : float
        TTL for aggregation result entries (default 180).
    metrics_ttl : float
        TTL for training metrics entries (default 60).
    """

    MODULE_NAME = "distributed_training"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        orchestrator: Any = None,
        aggregator: Any = None,
        metrics_collector: Any = None,
        *,
        round_status_ttl: float = 120.0,
        aggregation_ttl: float = 180.0,
        metrics_ttl: float = 60.0,
    ) -> None:
        self._orchestrator = orchestrator
        self._aggregator = aggregator
        self._metrics_collector = metrics_collector
        self._round_status_ttl = round_status_ttl
        self._aggregation_ttl = aggregation_ttl
        self._metrics_ttl = metrics_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change detection
        self._last_round_id: Optional[str] = None
        self._last_round_status: Optional[str] = None
        self._last_aggregation_round: Optional[str] = None
        self._last_byzantine_count: int = 0
        self._last_loss: Optional[float] = None

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
                "Distributed training: federated learning orchestration, "
                "Byzantine-tolerant aggregation, and training metrics."
            ),
            topics_produced=frozenset(
                {
                    "distributed_training.round_status",
                    "distributed_training.aggregation",
                    "distributed_training.metrics",
                }
            ),
            topics_consumed=frozenset(
                {
                    "compute",
                    "reasoning",
                    "consciousness",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "DistributedTrainingAdapter registered with blackboard "
            "(orchestrator=%s, aggregator=%s, metrics=%s)",
            self._orchestrator is not None,
            self._aggregator is not None,
            self._metrics_collector is not None,
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
        """Handle incoming events from other modules."""
        try:
            if event.event_type.startswith("compute."):
                self._handle_compute_event(event)
            elif event.event_type.startswith("consciousness."):
                self._handle_consciousness_event(event)
        except Exception:
            logger.debug(
                "DistributedTrainingAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current distributed training state."""
        entries: List[BlackboardEntry] = []

        with self._lock:
            round_entry = self._produce_round_status()
            if round_entry is not None:
                entries.append(round_entry)

            agg_entry = self._produce_aggregation()
            if agg_entry is not None:
                entries.append(agg_entry)

            metrics_entry = self._produce_metrics()
            if metrics_entry is not None:
                entries.append(metrics_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        Compute resource updates → node capacity awareness.
        Reasoning insights → hyperparameter guidance.
        Consciousness state → attention-weighted aggregation.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("compute."):
                    self._consume_compute(entry)
                elif entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
                elif entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
            except Exception:
                logger.debug(
                    "DistributedTrainingAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_round_status(self) -> Optional[BlackboardEntry]:
        """Read current training round status from orchestrator."""
        if self._orchestrator is None:
            return None

        try:
            # Try to get current round info
            current_round = getattr(self._orchestrator, "current_round", None)
            if current_round is None:
                current_round = getattr(self._orchestrator, "current_training_round", None)
        except Exception:
            return None

        if current_round is None:
            return None

        if hasattr(current_round, "__dict__"):
            try:
                from dataclasses import asdict
                round_data = asdict(current_round)
            except (TypeError, Exception):
                round_data = vars(current_round) if hasattr(current_round, '__dict__') else {}
        elif isinstance(current_round, dict):
            round_data = current_round
        else:
            round_data = {"raw": str(current_round)}

        round_id = str(round_data.get("round_id", round_data.get("id", "")))
        status = str(round_data.get("status", round_data.get("state", "")))

        # Change detection: only post if round or status changed
        if round_id == self._last_round_id and status == self._last_round_status:
            return None

        was_different_round = round_id != self._last_round_id
        old_status = self._last_round_status
        self._last_round_id = round_id
        self._last_round_status = status

        # Enrich with node counts
        nodes = getattr(self._orchestrator, "nodes", None)
        active_nodes = getattr(self._orchestrator, "active_nodes", None)
        if nodes is not None:
            round_data["total_nodes"] = len(nodes) if hasattr(nodes, '__len__') else nodes
        if active_nodes is not None:
            round_data["active_nodes"] = (
                len(active_nodes) if hasattr(active_nodes, '__len__') else active_nodes
            )

        is_completed = status in ("completed", "finished", "aggregated", "done")
        priority = EntryPriority.HIGH if is_completed else EntryPriority.NORMAL

        entry = BlackboardEntry(
            topic="distributed_training.round_status",
            data=round_data,
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=priority,
            ttl_seconds=self._round_status_ttl,
            tags=frozenset({"federated", "training", "round", status}),
            metadata={"round_id": round_id, "status": status},
        )

        if is_completed and old_status != status:
            self._emit(
                "distributed_training.round.completed",
                {
                    "round_id": round_id,
                    "round_data": round_data,
                    "entry_id": entry.entry_id,
                },
            )

        return entry

    def _produce_aggregation(self) -> Optional[BlackboardEntry]:
        """Capture aggregation results and Byzantine detection stats."""
        if self._aggregator is None:
            return None

        # Get detection stats for Byzantine information
        agg_data: Dict[str, Any] = {}
        try:
            stats_fn = getattr(self._aggregator, "get_detection_stats", None)
            if stats_fn is not None:
                stats = stats_fn()
                if isinstance(stats, dict):
                    agg_data.update(stats)
        except Exception:
            pass

        # Get last aggregation result
        try:
            last_result = getattr(self._aggregator, "last_result", None)
            if last_result is not None:
                if hasattr(last_result, '__dict__'):
                    try:
                        from dataclasses import asdict
                        agg_data["last_aggregation"] = asdict(last_result)
                    except (TypeError, Exception):
                        agg_data["last_aggregation"] = str(last_result)
                elif isinstance(last_result, dict):
                    agg_data["last_aggregation"] = last_result
        except Exception:
            pass

        if not agg_data:
            return None

        # Detect Byzantine node changes
        suspected = agg_data.get("suspected_byzantine", agg_data.get("byzantine_nodes", []))
        byzantine_count = len(suspected) if isinstance(suspected, (list, set)) else 0

        # Change detection: only post if aggregation round changed or Byzantine count changed
        agg_round = agg_data.get("round_id", agg_data.get("aggregation_round", ""))
        if (str(agg_round) == str(self._last_aggregation_round)
                and byzantine_count == self._last_byzantine_count):
            return None

        new_byzantine = byzantine_count > self._last_byzantine_count
        self._last_aggregation_round = str(agg_round)
        self._last_byzantine_count = byzantine_count

        priority = EntryPriority.CRITICAL if byzantine_count > 0 else EntryPriority.NORMAL

        entry = BlackboardEntry(
            topic="distributed_training.aggregation",
            data=agg_data,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=priority,
            ttl_seconds=self._aggregation_ttl,
            tags=frozenset({"aggregation", "federated", "byzantine"}),
            metadata={
                "byzantine_count": byzantine_count,
                "aggregation_round": str(agg_round),
            },
        )

        if new_byzantine and byzantine_count > 0:
            self._emit(
                "distributed_training.byzantine.detected",
                {
                    "suspected_nodes": suspected if isinstance(suspected, list) else [],
                    "byzantine_count": byzantine_count,
                    "entry_id": entry.entry_id,
                },
            )

        return entry

    def _produce_metrics(self) -> Optional[BlackboardEntry]:
        """Collect training metrics from MetricsCollector."""
        if self._metrics_collector is None:
            return None

        try:
            summary_fn = getattr(self._metrics_collector, "get_current_round_summary", None)
            if summary_fn is not None:
                metrics_data = summary_fn()
            else:
                # Fallback to network health
                health_fn = getattr(self._metrics_collector, "get_network_health_status", None)
                if health_fn is not None:
                    metrics_data = health_fn()
                else:
                    return None
        except Exception:
            logger.debug("DT MetricsCollector query failed", exc_info=True)
            return None

        if not metrics_data or not isinstance(metrics_data, dict):
            return None

        # Change detection: only post if loss changed significantly
        current_loss = metrics_data.get("avg_loss", metrics_data.get("loss", None))
        if current_loss is not None and self._last_loss is not None:
            if isinstance(current_loss, (int, float)) and isinstance(self._last_loss, (int, float)):
                delta = abs(current_loss - self._last_loss)
                if self._last_loss != 0 and delta / max(abs(self._last_loss), 1e-9) < 0.02:
                    return None

        if current_loss is not None:
            self._last_loss = current_loss

        return BlackboardEntry(
            topic="distributed_training.metrics",
            data=metrics_data,
            source_module=self.MODULE_NAME,
            confidence=0.85,
            priority=EntryPriority.LOW,
            ttl_seconds=self._metrics_ttl,
            tags=frozenset({"training", "metrics", "loss", "accuracy"}),
            metadata={"loss": current_loss},
        )

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_compute(self, entry: BlackboardEntry) -> None:
        """React to compute resource updates — adjust node capacity awareness."""
        if self._orchestrator is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        max_util = data.get("max_utilization", None)
        if max_util is not None and hasattr(self._orchestrator, "config"):
            config = self._orchestrator.config
            if isinstance(config, dict):
                # Reduce participant count if resources are strained
                if isinstance(max_util, (int, float)) and max_util > 0.9:
                    current_min = config.get("min_participants", 2)
                    config["min_participants"] = max(2, current_min - 1)

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Use reasoning insights to guide training hyperparameters."""
        if self._orchestrator is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        # If reasoning suggests learning rate adjustment
        lr_suggestion = data.get("suggested_lr", data.get("learning_rate", None))
        if lr_suggestion is not None and hasattr(self._orchestrator, "config"):
            config = self._orchestrator.config
            if isinstance(config, dict):
                config["suggested_lr"] = float(lr_suggestion)

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Modulate training based on consciousness state."""
        if self._orchestrator is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        phi = data.get("phi", data.get("phi_value", None))
        if phi is not None and hasattr(self._orchestrator, "config"):
            config = self._orchestrator.config
            if isinstance(config, dict):
                # Higher consciousness → more aggressive aggregation
                config["consciousness_phi"] = float(phi)

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_compute_event(self, event: CognitiveEvent) -> None:
        """Handle compute resource events — scale down if resources exhausted."""
        if self._orchestrator is None:
            return
        if event.event_type == "compute.resource.exhausted":
            # Signal the orchestrator to reduce batch size or pause
            if hasattr(self._orchestrator, "config") and isinstance(
                self._orchestrator.config, dict
            ):
                self._orchestrator.config["resource_constrained"] = True

    def _handle_consciousness_event(self, event: CognitiveEvent) -> None:
        """Handle consciousness state changes — modulate training aggressiveness."""
        if self._orchestrator is None:
            return
        payload = event.payload or {}
        new_state = payload.get("new_state", "")
        if new_state and hasattr(self._orchestrator, "config") and isinstance(
            self._orchestrator.config, dict
        ):
            self._orchestrator.config["consciousness_state"] = str(new_state)

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all distributed training components."""
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_orchestrator": self._orchestrator is not None,
            "has_aggregator": self._aggregator is not None,
            "has_metrics_collector": self._metrics_collector is not None,
            "last_round_id": self._last_round_id,
            "last_round_status": self._last_round_status,
            "last_byzantine_count": self._last_byzantine_count,
            "last_loss": self._last_loss,
            "registered": self._blackboard is not None,
        }

        if self._orchestrator is not None:
            try:
                nodes = getattr(self._orchestrator, "nodes", {})
                snap["total_nodes"] = len(nodes) if hasattr(nodes, '__len__') else 0
                snap["is_running"] = getattr(self._orchestrator, "is_running", False)
            except Exception:
                pass

        if self._aggregator is not None:
            try:
                stats_fn = getattr(self._aggregator, "get_detection_stats", None)
                if stats_fn is not None:
                    snap["detection_stats"] = stats_fn()
            except Exception:
                snap["detection_stats"] = None

        if self._metrics_collector is not None:
            try:
                health_fn = getattr(self._metrics_collector, "get_network_health_status", None)
                if health_fn is not None:
                    snap["network_health"] = health_fn()
            except Exception:
                snap["network_health"] = None

        return snap
