"""
Reproducibility ↔ Blackboard Adapter
========================================

Bridges the AGI reproducibility module (``ExperimentTracker``,
``VersionManager``, ``PlatformConfig``) with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``reproducibility.experiment_status``  — Experiment state and progress
- ``reproducibility.version_info``       — Version history and branching
- ``reproducibility.verification``       — Experiment verification and reproduction results

Topics consumed
~~~~~~~~~~~~~~~
- ``compute``                            — Compute job completions → experiment status updates
- ``distributed_training``               — Training rounds → experiment metrics capture
- ``reasoning``                          — Reasoning inferences → experiment result logging

Events emitted
~~~~~~~~~~~~~~
- ``reproducibility.experiment.completed``  — An experiment has finished
- ``reproducibility.version.created``       — A new version snapshot was created

Events listened
~~~~~~~~~~~~~~~
- ``compute.job.completed``                 — Trigger experiment result capture
- ``distributed_training.round.completed``  — Log training metrics to experiment
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

_reproducibility_module = None


def _get_reproducibility():
    """Lazy import of agi_reproducibility module to allow graceful degradation."""
    global _reproducibility_module
    if _reproducibility_module is None:
        try:
            from asi_build import agi_reproducibility as _rm

            _reproducibility_module = _rm
        except (ImportError, ModuleNotFoundError):
            _reproducibility_module = False
    return _reproducibility_module if _reproducibility_module is not False else None


class ReproducibilityBlackboardAdapter:
    """Adapter connecting the AGI reproducibility module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``ExperimentTracker`` — experiment creation, status tracking, result logging
    - ``VersionManager`` — experiment versioning, branching, tagging
    - ``PlatformConfig`` — reproducibility platform configuration

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    tracker : optional
        An ``ExperimentTracker`` instance.
    version_manager : optional
        A ``VersionManager`` instance.
    config : optional
        A ``PlatformConfig`` instance.
    experiment_status_ttl : float
        TTL in seconds for experiment status entries (default 300).
    version_info_ttl : float
        TTL for version info entries (default 600).
    verification_ttl : float
        TTL for verification entries (default 600).
    """

    MODULE_NAME = "reproducibility"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        tracker: Any = None,
        version_manager: Any = None,
        config: Any = None,
        *,
        experiment_status_ttl: float = 300.0,
        version_info_ttl: float = 600.0,
        verification_ttl: float = 600.0,
    ) -> None:
        self._tracker = tracker
        self._version_manager = version_manager
        self._config = config
        self._experiment_status_ttl = experiment_status_ttl
        self._version_info_ttl = version_info_ttl
        self._verification_ttl = verification_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change detection
        self._last_experiment_statuses: Dict[str, str] = {}
        self._last_version_counts: Dict[str, int] = {}
        self._pending_verifications: List[Dict[str, Any]] = []
        self._tracked_experiments: List[str] = []

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
                "AGI reproducibility: experiment tracking, versioning, "
                "and verification for reproducible research."
            ),
            topics_produced=frozenset(
                {
                    "reproducibility.experiment_status",
                    "reproducibility.version_info",
                    "reproducibility.verification",
                }
            ),
            topics_consumed=frozenset(
                {
                    "compute",
                    "distributed_training",
                    "reasoning",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "ReproducibilityBlackboardAdapter registered with blackboard "
            "(tracker=%s, version_manager=%s, config=%s)",
            self._tracker is not None,
            self._version_manager is not None,
            self._config is not None,
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
            elif event.event_type.startswith("distributed_training."):
                self._handle_training_event(event)
        except Exception:
            logger.debug(
                "ReproducibilityBlackboardAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── Public API: register experiments for tracking ─────────────────

    def track_experiment(self, experiment_id: str) -> None:
        """Register an experiment ID for status tracking in produce()."""
        with self._lock:
            if experiment_id not in self._tracked_experiments:
                self._tracked_experiments.append(experiment_id)

    def add_verification_result(self, result: Dict[str, Any]) -> None:
        """Queue a verification result for the next production sweep."""
        with self._lock:
            self._pending_verifications.append({
                **result,
                "timestamp": time.time(),
            })

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current reproducibility state."""
        entries: List[BlackboardEntry] = []

        with self._lock:
            exp_entries = self._produce_experiment_statuses()
            entries.extend(exp_entries)

            version_entries = self._produce_version_info()
            entries.extend(version_entries)

            verification_entries = self._produce_verifications()
            entries.extend(verification_entries)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        Compute completions → experiment status updates.
        Training round updates → experiment metrics capture.
        Reasoning inferences → experiment result logging.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("compute."):
                    self._consume_compute(entry)
                elif entry.topic.startswith("distributed_training."):
                    self._consume_training(entry)
                elif entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
            except Exception:
                logger.debug(
                    "ReproducibilityBlackboardAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_experiment_statuses(self) -> List[BlackboardEntry]:
        """Check status of all tracked experiments and return entries for changed ones."""
        if self._tracker is None:
            return []

        entries: List[BlackboardEntry] = []
        experiments_to_check = list(self._tracked_experiments)

        for exp_id in experiments_to_check:
            try:
                # Try sync get_experiment first
                get_fn = getattr(self._tracker, "get_experiment", None)
                if get_fn is None:
                    continue

                experiment = get_fn(exp_id)
                if experiment is None:
                    continue

                # Normalize to dict
                if hasattr(experiment, "to_dict"):
                    exp_data = experiment.to_dict()
                elif hasattr(experiment, "__dict__"):
                    try:
                        from dataclasses import asdict
                        exp_data = asdict(experiment)
                    except (TypeError, Exception):
                        exp_data = vars(experiment)
                elif isinstance(experiment, dict):
                    exp_data = experiment
                else:
                    exp_data = {"raw": str(experiment)}

                status = str(exp_data.get("status", exp_data.get("state", "")))

                # Change detection: only post if status changed
                prev_status = self._last_experiment_statuses.get(exp_id)
                if status == prev_status:
                    continue
                self._last_experiment_statuses[exp_id] = status

                is_completed = status.lower() in (
                    "completed", "finished", "success", "failed", "error"
                )
                priority = EntryPriority.HIGH if is_completed else EntryPriority.NORMAL

                entry = BlackboardEntry(
                    topic="reproducibility.experiment_status",
                    data=exp_data,
                    source_module=self.MODULE_NAME,
                    confidence=0.95,
                    priority=priority,
                    ttl_seconds=self._experiment_status_ttl,
                    tags=frozenset({"reproducibility", "experiment", status.lower(), exp_id[:8]}),
                    metadata={
                        "experiment_id": exp_id,
                        "status": status,
                    },
                )
                entries.append(entry)

                if is_completed:
                    self._emit(
                        "reproducibility.experiment.completed",
                        {
                            "experiment_id": exp_id,
                            "status": status,
                            "entry_id": entry.entry_id,
                        },
                    )

            except Exception:
                logger.debug(
                    "Failed to check experiment %s", exp_id, exc_info=True
                )

        return entries

    def _produce_version_info(self) -> List[BlackboardEntry]:
        """Produce version info entries for tracked experiments with new versions."""
        if self._version_manager is None:
            return []

        entries: List[BlackboardEntry] = []
        experiments_to_check = list(self._tracked_experiments)

        for exp_id in experiments_to_check:
            try:
                history_fn = getattr(self._version_manager, "get_version_history", None)
                if history_fn is None:
                    continue

                history = history_fn(exp_id)
                if not history:
                    continue

                version_count = len(history) if hasattr(history, '__len__') else 0
                prev_count = self._last_version_counts.get(exp_id, 0)

                # Change detection: only post if new versions appeared
                if version_count <= prev_count:
                    continue
                self._last_version_counts[exp_id] = version_count

                # Get latest version info
                latest = history[-1] if isinstance(history, list) else history
                if hasattr(latest, "to_dict"):
                    version_data = latest.to_dict()
                elif hasattr(latest, "__dict__"):
                    try:
                        from dataclasses import asdict
                        version_data = asdict(latest)
                    except (TypeError, Exception):
                        version_data = vars(latest)
                elif isinstance(latest, dict):
                    version_data = latest
                else:
                    version_data = {"raw": str(latest)}

                version_data["experiment_id"] = exp_id
                version_data["total_versions"] = version_count

                entry = BlackboardEntry(
                    topic="reproducibility.version_info",
                    data=version_data,
                    source_module=self.MODULE_NAME,
                    confidence=0.9,
                    priority=EntryPriority.NORMAL,
                    ttl_seconds=self._version_info_ttl,
                    tags=frozenset({"reproducibility", "version", "history"}),
                    metadata={
                        "experiment_id": exp_id,
                        "version_count": version_count,
                    },
                )
                entries.append(entry)

                self._emit(
                    "reproducibility.version.created",
                    {
                        "experiment_id": exp_id,
                        "version_count": version_count,
                        "entry_id": entry.entry_id,
                    },
                )

            except Exception:
                logger.debug(
                    "Failed to get version info for %s", exp_id, exc_info=True
                )

        return entries

    def _produce_verifications(self) -> List[BlackboardEntry]:
        """Flush pending verification results as blackboard entries."""
        if not self._pending_verifications:
            return []

        entries: List[BlackboardEntry] = []
        verifications_to_post = list(self._pending_verifications)
        self._pending_verifications.clear()

        for verification in verifications_to_post:
            passed = verification.get("passed", verification.get("success", None))
            priority = EntryPriority.NORMAL
            if passed is True:
                priority = EntryPriority.HIGH
            elif passed is False:
                priority = EntryPriority.CRITICAL

            entries.append(
                BlackboardEntry(
                    topic="reproducibility.verification",
                    data=verification,
                    source_module=self.MODULE_NAME,
                    confidence=0.95 if passed is True else 0.7,
                    priority=priority,
                    ttl_seconds=self._verification_ttl,
                    tags=frozenset({
                        "reproducibility", "verification",
                        "passed" if passed else "failed" if passed is False else "pending",
                    }),
                    metadata={
                        "experiment_id": verification.get("experiment_id", ""),
                        "passed": passed,
                    },
                )
            )

        return entries

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_compute(self, entry: BlackboardEntry) -> None:
        """React to compute completions — update experiment status."""
        if self._tracker is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        job_name = data.get("name", data.get("job_name", ""))

        # If the job relates to an experiment, auto-track it
        exp_id = data.get("experiment_id")
        if exp_id:
            self.track_experiment(exp_id)

        # Log compute result as experiment metric
        if exp_id and hasattr(self._tracker, "update_experiment_results"):
            try:
                self._tracker.update_experiment_results(
                    exp_id,
                    results={
                        "compute_entry": entry.entry_id,
                        "job_name": job_name,
                        "timestamp": time.time(),
                    },
                )
            except Exception:
                pass

    def _consume_training(self, entry: BlackboardEntry) -> None:
        """Capture training metrics into experiment records."""
        if self._tracker is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        exp_id = data.get("experiment_id")
        if exp_id:
            self.track_experiment(exp_id)

        # Log training round metrics
        round_id = data.get("round_id", "")
        loss = data.get("avg_loss", data.get("loss"))
        if exp_id and hasattr(self._tracker, "update_experiment_benchmarks"):
            try:
                self._tracker.update_experiment_benchmarks(
                    exp_id,
                    benchmarks={
                        "training_round": round_id,
                        "loss": loss,
                        "entry_id": entry.entry_id,
                        "timestamp": time.time(),
                    },
                )
            except Exception:
                pass

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Log reasoning outputs as experiment artifacts."""
        if self._tracker is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        exp_id = data.get("experiment_id")
        if exp_id:
            self.track_experiment(exp_id)
            if hasattr(self._tracker, "update_experiment_results"):
                try:
                    self._tracker.update_experiment_results(
                        exp_id,
                        results={
                            "reasoning_entry": entry.entry_id,
                            "confidence": entry.confidence,
                            "timestamp": time.time(),
                        },
                    )
                except Exception:
                    pass

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_compute_event(self, event: CognitiveEvent) -> None:
        """React to compute job completions — trigger experiment result capture."""
        if self._tracker is None:
            return
        payload = event.payload or {}
        exp_id = payload.get("experiment_id")
        if exp_id:
            self.track_experiment(exp_id)

    def _handle_training_event(self, event: CognitiveEvent) -> None:
        """React to training round completions — log metrics to experiment."""
        if self._tracker is None:
            return
        payload = event.payload or {}
        exp_id = payload.get("experiment_id")
        if exp_id:
            self.track_experiment(exp_id)

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all reproducibility components."""
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_tracker": self._tracker is not None,
            "has_version_manager": self._version_manager is not None,
            "has_config": self._config is not None,
            "tracked_experiments": list(self._tracked_experiments),
            "experiment_count": len(self._tracked_experiments),
            "pending_verifications": len(self._pending_verifications),
            "experiment_statuses": dict(self._last_experiment_statuses),
            "version_counts": dict(self._last_version_counts),
            "registered": self._blackboard is not None,
        }

        if self._config is not None:
            try:
                snap["platform_name"] = getattr(self._config, "platform_name", "unknown")
                snap["base_dir"] = getattr(self._config, "base_dir", "unknown")
            except Exception:
                pass

        if self._tracker is not None:
            try:
                health_fn = getattr(self._tracker, "health_check", None)
                if health_fn is not None:
                    snap["tracker_health"] = health_fn()
            except Exception:
                snap["tracker_health"] = None

        return snap
