"""
Compute ↔ Blackboard Adapter
================================

Bridges the compute module (``JobScheduler``, ``ResourceAllocator``,
``MetricsCollector``) with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``compute.job_status``             — Job queue status and scheduling metrics
- ``compute.resource_utilization``   — Resource allocation and utilization levels
- ``compute.metrics``                — Collected compute metrics (counters, timers, histograms)

Topics consumed
~~~~~~~~~~~~~~~
- ``reasoning``                      — Reasoning workloads → submit as compute jobs
- ``distributed_training``           — Training rounds → resource allocation requests

Events emitted
~~~~~~~~~~~~~~
- ``compute.job.completed``          — A scheduled job has completed
- ``compute.resource.exhausted``     — Resource utilization exceeds critical threshold

Events listened
~~~~~~~~~~~~~~~
- ``reasoning.inference.completed``  — May trigger follow-up compute jobs
- ``distributed_training.round.completed`` — Release resources from completed rounds
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

# Lazy imports — the compute module may not be available
_compute_module = None


def _get_compute():
    """Lazy import of compute module to allow graceful degradation."""
    global _compute_module
    if _compute_module is None:
        try:
            from asi_build import compute as _cm

            _compute_module = _cm
        except (ImportError, ModuleNotFoundError):
            _compute_module = False
    return _compute_module if _compute_module is not False else None


class ComputeBlackboardAdapter:
    """Adapter connecting the compute module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``JobScheduler`` — job queue management and scheduling
    - ``ResourceAllocator`` — dynamic resource allocation across providers
    - ``MetricsCollector`` — compute metrics collection and alerting

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    scheduler : optional
        A ``JobScheduler`` instance.
    allocator : optional
        A ``ResourceAllocator`` instance.
    metrics_collector : optional
        A ``MetricsCollector`` instance.
    job_status_ttl : float
        TTL in seconds for job status entries (default 120 = 2 minutes).
    resource_ttl : float
        TTL for resource utilization entries (default 60 = 1 minute).
    metrics_ttl : float
        TTL for metrics entries (default 180 = 3 minutes).
    resource_exhaustion_threshold : float
        Utilization level (0–1) above which a resource.exhausted event fires
        (default 0.95).
    """

    MODULE_NAME = "compute"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        scheduler: Any = None,
        allocator: Any = None,
        metrics_collector: Any = None,
        *,
        job_status_ttl: float = 120.0,
        resource_ttl: float = 60.0,
        metrics_ttl: float = 180.0,
        resource_exhaustion_threshold: float = 0.95,
    ) -> None:
        self._scheduler = scheduler
        self._allocator = allocator
        self._metrics_collector = metrics_collector
        self._job_status_ttl = job_status_ttl
        self._resource_ttl = resource_ttl
        self._metrics_ttl = metrics_ttl
        self._resource_exhaustion_threshold = resource_exhaustion_threshold

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change detection state
        self._last_queue_status: Optional[Dict[str, Any]] = None
        self._last_utilization: Optional[Dict[str, float]] = None
        self._last_completed_jobs: int = 0
        self._resource_exhausted_fired: bool = False

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
                "Compute resource pooling: job scheduling, resource allocation, "
                "and compute metrics collection."
            ),
            topics_produced=frozenset(
                {
                    "compute.job_status",
                    "compute.resource_utilization",
                    "compute.metrics",
                }
            ),
            topics_consumed=frozenset(
                {
                    "reasoning",
                    "distributed_training",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "ComputeBlackboardAdapter registered with blackboard "
            "(scheduler=%s, allocator=%s, metrics=%s)",
            self._scheduler is not None,
            self._allocator is not None,
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
        """Handle incoming events from other modules.

        Routes reasoning completion events to job scheduling feedback,
        and distributed training completion to resource release.
        """
        try:
            if event.event_type.startswith("reasoning."):
                self._handle_reasoning_event(event)
            elif event.event_type.startswith("distributed_training."):
                self._handle_training_event(event)
        except Exception:
            logger.debug(
                "ComputeBlackboardAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current compute state.

        Called during a production sweep.  Collects:
        1. Job queue status from JobScheduler
        2. Resource utilization from ResourceAllocator
        3. Collected metrics from MetricsCollector
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            job_entry = self._produce_job_status()
            if job_entry is not None:
                entries.append(job_entry)

            resource_entry = self._produce_resource_utilization()
            if resource_entry is not None:
                entries.append(resource_entry)

            metrics_entry = self._produce_metrics()
            if metrics_entry is not None:
                entries.append(metrics_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        Reasoning workloads → submit as compute jobs.
        Training round updates → adjust resource allocation.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
                elif entry.topic.startswith("distributed_training."):
                    self._consume_training(entry)
            except Exception:
                logger.debug(
                    "ComputeBlackboardAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_job_status(self) -> Optional[BlackboardEntry]:
        """Read queue status from scheduler and return entry if changed."""
        if self._scheduler is None:
            return None

        try:
            queue_status = getattr(self._scheduler, "get_queue_status", None)
            if queue_status is None:
                return None
            status_data = queue_status()
        except Exception:
            logger.debug("JobScheduler get_queue_status() failed", exc_info=True)
            return None

        if status_data is None:
            return None

        status_data = status_data if isinstance(status_data, dict) else {"raw": status_data}

        # Track completed jobs for event emission
        completed = status_data.get("completed_jobs", status_data.get("completed", 0))
        new_completions = False
        if isinstance(completed, (int, float)) and completed > self._last_completed_jobs:
            new_completions = True
            delta_completed = int(completed - self._last_completed_jobs)
            self._last_completed_jobs = int(completed)

        # Change detection: compare key queue metrics
        queue_key = (
            status_data.get("pending_jobs", status_data.get("pending", None)),
            status_data.get("running_jobs", status_data.get("running", None)),
            completed,
        )
        last_key = None
        if self._last_queue_status is not None:
            last_key = (
                self._last_queue_status.get("pending_jobs",
                                            self._last_queue_status.get("pending", None)),
                self._last_queue_status.get("running_jobs",
                                            self._last_queue_status.get("running", None)),
                self._last_queue_status.get("completed_jobs",
                                            self._last_queue_status.get("completed", None)),
            )
        if queue_key == last_key:
            return None

        self._last_queue_status = status_data

        pending = status_data.get("pending_jobs", status_data.get("pending", 0))
        running = status_data.get("running_jobs", status_data.get("running", 0))

        priority = EntryPriority.NORMAL
        if isinstance(pending, (int, float)) and pending > 100:
            priority = EntryPriority.HIGH

        entry = BlackboardEntry(
            topic="compute.job_status",
            data=status_data,
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=priority,
            ttl_seconds=self._job_status_ttl,
            tags=frozenset({"compute", "job", "scheduler", "queue"}),
            metadata={
                "pending": pending,
                "running": running,
                "completed": completed,
            },
        )

        if new_completions:
            self._emit(
                "compute.job.completed",
                {
                    "completed_count": delta_completed,
                    "total_completed": self._last_completed_jobs,
                    "entry_id": entry.entry_id,
                },
            )

        return entry

    def _produce_resource_utilization(self) -> Optional[BlackboardEntry]:
        """Snapshot resource utilization from allocator."""
        if self._allocator is None:
            return None

        # Try sync get_utilization first, then async-stored cache
        utilization: Optional[Dict[str, float]] = None
        try:
            get_util = getattr(self._allocator, "get_utilization", None)
            if get_util is not None:
                result = get_util()
                if isinstance(result, dict):
                    utilization = result
        except Exception:
            pass

        # Fallback: try reading cached utilization attribute
        if utilization is None:
            utilization = getattr(self._allocator, "current_utilization", None)
            if utilization is not None and not isinstance(utilization, dict):
                utilization = None

        if utilization is None:
            # Attempt to build from resource counts
            try:
                total = getattr(self._allocator, "total_resources", None)
                allocated = getattr(self._allocator, "allocated_resources", None)
                if total and allocated and isinstance(total, dict) and isinstance(allocated, dict):
                    utilization = {}
                    for key in total:
                        t = total.get(key, 0)
                        a = allocated.get(key, 0)
                        utilization[key] = a / max(t, 1)
            except Exception:
                pass

        if utilization is None:
            return None

        # Change detection: only post if any resource changed by >5%
        if self._last_utilization is not None:
            max_delta = 0.0
            all_keys = set(utilization.keys()) | set(self._last_utilization.keys())
            for key in all_keys:
                cur = utilization.get(key, 0.0)
                prev = self._last_utilization.get(key, 0.0)
                max_delta = max(max_delta, abs(cur - prev))
            if max_delta < 0.05:
                return None

        self._last_utilization = dict(utilization)

        # Check for resource exhaustion
        max_util = max(utilization.values()) if utilization else 0.0
        is_exhausted = max_util >= self._resource_exhaustion_threshold

        priority = EntryPriority.NORMAL
        if is_exhausted:
            priority = EntryPriority.CRITICAL
        elif max_util > 0.8:
            priority = EntryPriority.HIGH

        entry = BlackboardEntry(
            topic="compute.resource_utilization",
            data=utilization,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=priority,
            ttl_seconds=self._resource_ttl,
            tags=frozenset({"compute", "resource", "utilization"}),
            metadata={"max_utilization": max_util},
        )

        if is_exhausted and not self._resource_exhausted_fired:
            self._resource_exhausted_fired = True
            self._emit(
                "compute.resource.exhausted",
                {
                    "utilization": utilization,
                    "max_utilization": max_util,
                    "threshold": self._resource_exhaustion_threshold,
                    "entry_id": entry.entry_id,
                },
            )
        elif not is_exhausted:
            self._resource_exhausted_fired = False

        return entry

    def _produce_metrics(self) -> Optional[BlackboardEntry]:
        """Collect metrics summary from MetricsCollector."""
        if self._metrics_collector is None:
            return None

        try:
            # Try get_metrics_list + get_metric_value for a summary
            metrics_list_fn = getattr(self._metrics_collector, "get_metrics_list", None)
            if metrics_list_fn is not None:
                names = metrics_list_fn()
                if not names:
                    return None
                summary: Dict[str, Any] = {"metric_count": len(names)}
                get_val = getattr(self._metrics_collector, "get_metric_value", None)
                if get_val is not None:
                    for name in names[:20]:  # Cap to avoid huge entries
                        try:
                            summary[name] = get_val(name)
                        except Exception:
                            pass
            else:
                # Fallback: try query_metrics
                query_fn = getattr(self._metrics_collector, "query_metrics", None)
                if query_fn is None:
                    return None
                summary = query_fn()
                if not summary:
                    return None
                if not isinstance(summary, dict):
                    summary = {"raw": summary}
        except Exception:
            logger.debug("MetricsCollector query failed", exc_info=True)
            return None

        # Always post metrics (informational, no change detection)
        return BlackboardEntry(
            topic="compute.metrics",
            data=summary,
            source_module=self.MODULE_NAME,
            confidence=0.85,
            priority=EntryPriority.LOW,
            ttl_seconds=self._metrics_ttl,
            tags=frozenset({"compute", "metrics", "monitoring"}),
        )

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Submit reasoning workloads as compute jobs."""
        if self._scheduler is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        job_spec = {
            "name": f"reasoning_{entry.entry_id[:8]}",
            "source": f"reasoning:{entry.entry_id}",
            "priority": entry.priority.value if hasattr(entry.priority, "value") else 0,
            "payload": data,
            "submitted_at": time.time(),
        }
        submit_fn = getattr(self._scheduler, "submit_job", None)
        if submit_fn is not None:
            try:
                submit_fn(job_spec)
            except TypeError:
                # submit_job may expect a Job object, not a dict
                pass
            except Exception:
                logger.debug("Failed to submit reasoning job", exc_info=True)

    def _consume_training(self, entry: BlackboardEntry) -> None:
        """Adjust resource allocation based on training round status."""
        if self._allocator is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        round_status = data.get("status", data.get("round_status", ""))
        # If training round completed, signal potential resource release
        if round_status in ("completed", "finished", "done"):
            release_fn = getattr(self._allocator, "deallocate_resources", None)
            if release_fn is not None:
                try:
                    release_fn({"source": f"training:{entry.entry_id}"})
                except Exception:
                    logger.debug("Failed to release training resources", exc_info=True)

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_reasoning_event(self, event: CognitiveEvent) -> None:
        """React to reasoning completion — potentially queue follow-up jobs."""
        if self._scheduler is None:
            return
        payload = event.payload or {}
        if payload.get("needs_compute", False):
            submit_fn = getattr(self._scheduler, "submit_job", None)
            if submit_fn is not None:
                try:
                    submit_fn({
                        "name": f"followup_{event.event_id[:8]}",
                        "source": f"event:{event.event_id}",
                        "payload": payload,
                    })
                except (TypeError, Exception):
                    pass

    def _handle_training_event(self, event: CognitiveEvent) -> None:
        """React to training round completion — release allocated resources."""
        if self._allocator is None:
            return
        payload = event.payload or {}
        if payload.get("round_id"):
            release_fn = getattr(self._allocator, "deallocate_resources", None)
            if release_fn is not None:
                try:
                    release_fn({
                        "round_id": payload["round_id"],
                        "source": f"event:{event.event_id}",
                    })
                except Exception:
                    pass

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all compute components.

        Useful for debugging and dashboard display.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_scheduler": self._scheduler is not None,
            "has_allocator": self._allocator is not None,
            "has_metrics_collector": self._metrics_collector is not None,
            "last_completed_jobs": self._last_completed_jobs,
            "resource_exhausted": self._resource_exhausted_fired,
            "registered": self._blackboard is not None,
        }

        if self._scheduler is not None:
            try:
                queue_fn = getattr(self._scheduler, "get_queue_status", None)
                if queue_fn is not None:
                    snap["queue_status"] = queue_fn()
            except Exception:
                snap["queue_status"] = None

        if self._last_utilization is not None:
            snap["last_utilization"] = self._last_utilization

        if self._metrics_collector is not None:
            try:
                names_fn = getattr(self._metrics_collector, "get_metrics_list", None)
                if names_fn is not None:
                    snap["tracked_metrics_count"] = len(names_fn())
            except Exception:
                snap["tracked_metrics_count"] = None

        return snap
