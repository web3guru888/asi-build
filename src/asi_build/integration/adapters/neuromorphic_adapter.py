"""
Neuromorphic ↔ Blackboard Adapter
===================================

Bridges the neuromorphic computing module (``NeuromorphicManager``,
``EventProcessor``, ``SpikeMonitor``, ``STDPLearning``) with the Cognitive
Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``neuromorphic.simulation.status``       — Simulation running state and step count
- ``neuromorphic.simulation.performance``  — Step timing, spike rate, memory usage
- ``neuromorphic.spike.monitor``           — Spike statistics (firing rates, synchrony)
- ``neuromorphic.event.statistics``        — Event processing throughput and queue stats
- ``neuromorphic.learning.update``         — STDP weight change statistics (LTP/LTD)

Topics consumed
~~~~~~~~~~~~~~~
- ``bci.*``            — Neural signal data → external events for simulation
- ``consciousness.*``  — Consciousness state → modulate simulation parameters
- ``quantum.*``        — Quantum optimization → network topology updates

Events emitted
~~~~~~~~~~~~~~
- ``neuromorphic.simulation.started``       — Simulation entered running state
- ``neuromorphic.simulation.stopped``       — Simulation stopped
- ``neuromorphic.performance.degraded``     — Step rate dropped >5%
- ``neuromorphic.spikes.burst``             — Spike count jump detected
- ``neuromorphic.learning.weight_shift``    — Significant STDP weight change

Events listened
~~~~~~~~~~~~~~~
- ``bci.signal.received``                   — Inject neural signals as events
- ``consciousness.state.changed``           — Modulate simulation from consciousness
- ``quantum.optimization.completed``        — Apply topology optimizations
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

# Lazy imports — the neuromorphic module may not be available
_neuromorphic_module = None


def _get_neuromorphic():
    """Lazy import of neuromorphic module to allow graceful degradation."""
    global _neuromorphic_module
    if _neuromorphic_module is None:
        try:
            from asi_build import neuromorphic as _nm

            _neuromorphic_module = _nm
        except (ImportError, ModuleNotFoundError):
            _neuromorphic_module = False
    return _neuromorphic_module if _neuromorphic_module is not False else None


class NeuromorphicBlackboardAdapter:
    """Adapter connecting the neuromorphic computing module to the Cognitive Blackboard.

    Wraps up to four components:

    - ``NeuromorphicManager`` — simulation lifecycle, network registration, stepping
    - ``EventProcessor``      — event queuing, dispatch, and statistics
    - ``SpikeMonitor``        — spike recording, firing rates, synchrony analysis
    - ``STDPLearning``        — spike-timing-dependent plasticity weight updates

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    manager : optional
        A ``NeuromorphicManager`` instance (core.manager).
    event_processor : optional
        An ``EventProcessor`` instance (core.event_processor).
    spike_monitor : optional
        A ``SpikeMonitor`` instance (core.spike_monitor).
    stdp : optional
        An ``STDPLearning`` instance (learning.stdp).
    status_ttl : float
        TTL in seconds for simulation status entries (default 120 = 2 minutes).
    performance_ttl : float
        TTL for performance metric entries (default 60 = 1 minute).
    spike_ttl : float
        TTL for spike monitoring entries (default 90 = 1.5 minutes).
    event_ttl : float
        TTL for event statistics entries (default 60 = 1 minute).
    learning_ttl : float
        TTL for learning update entries (default 180 = 3 minutes).
    """

    # ── Protocol-required property ────────────────────────────────────
    MODULE_NAME = "neuromorphic"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        manager: Any = None,
        event_processor: Any = None,
        spike_monitor: Any = None,
        stdp: Any = None,
        *,
        status_ttl: float = 120.0,
        performance_ttl: float = 60.0,
        spike_ttl: float = 90.0,
        event_ttl: float = 60.0,
        learning_ttl: float = 180.0,
    ) -> None:
        self._manager = manager
        self._event_processor = event_processor
        self._spike_monitor = spike_monitor
        self._stdp = stdp

        self._status_ttl = status_ttl
        self._performance_ttl = performance_ttl
        self._spike_ttl = spike_ttl
        self._event_ttl = event_ttl
        self._learning_ttl = learning_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Track last values for change detection
        self._last_is_running: Optional[bool] = None
        self._last_total_steps: Optional[int] = None
        self._last_steps_per_second: Optional[float] = None
        self._last_total_spikes: Optional[int] = None
        self._last_events_processed: Optional[int] = None
        self._last_total_updates: Optional[int] = None

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
                "Neuromorphic computing module: spiking neural network simulation, "
                "event-driven processing, spike monitoring, and STDP learning."
            ),
            topics_produced=frozenset(
                {
                    "neuromorphic.simulation.status",
                    "neuromorphic.simulation.performance",
                    "neuromorphic.spike.monitor",
                    "neuromorphic.event.statistics",
                    "neuromorphic.learning.update",
                }
            ),
            topics_consumed=frozenset(
                {
                    "bci",
                    "consciousness",
                    "quantum",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "NeuromorphicBlackboardAdapter registered with blackboard "
            "(manager=%s, event_processor=%s, spike_monitor=%s, stdp=%s)",
            self._manager is not None,
            self._event_processor is not None,
            self._spike_monitor is not None,
            self._stdp is not None,
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

        Routes BCI neural signals, consciousness state changes, and quantum
        optimization results into the neuromorphic simulation.
        """
        try:
            if event.event_type.startswith("bci."):
                self._handle_bci_event(event)
            elif event.event_type.startswith("consciousness."):
                self._handle_consciousness_event(event)
            elif event.event_type.startswith("quantum."):
                self._handle_quantum_event(event)
        except Exception:
            logger.debug(
                "NeuromorphicBlackboardAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current neuromorphic state.

        Called during a production sweep.  Collects:
        1. Simulation status (running state, step count)
        2. Simulation performance metrics (step rate, spike rate)
        3. Spike monitoring statistics (firing rates, synchrony)
        4. Event processing statistics (throughput, queue sizes)
        5. STDP learning updates (weight changes, LTP/LTD counts)
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            status_entry = self._produce_simulation_status()
            if status_entry is not None:
                entries.append(status_entry)

            perf_entry = self._produce_simulation_performance()
            if perf_entry is not None:
                entries.append(perf_entry)

            spike_entry = self._produce_spike_monitor()
            if spike_entry is not None:
                entries.append(spike_entry)

            event_entry = self._produce_event_statistics()
            if event_entry is not None:
                entries.append(event_entry)

            learning_entry = self._produce_learning_update()
            if learning_entry is not None:
                entries.append(learning_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        BCI data → submit as external events to the event processor.
        Consciousness state → modulate simulation parameters.
        Quantum optimization → apply network topology updates.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("bci."):
                    self._consume_bci(entry)
                elif entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
                elif entry.topic.startswith("quantum."):
                    self._consume_quantum(entry)
            except Exception:
                logger.debug(
                    "NeuromorphicBlackboardAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_simulation_status(self) -> Optional[BlackboardEntry]:
        """Query NeuromorphicManager for system status and return an entry if changed.

        Change detection triggers on ``is_running`` or ``total_steps`` changing.
        """
        if self._manager is None:
            return None

        try:
            status = self._manager.get_system_status()
        except Exception:
            logger.debug("NeuromorphicManager.get_system_status() failed", exc_info=True)
            return None

        is_running = getattr(status, "is_running", False)
        total_steps = getattr(status, "total_steps", 0)

        # Change detection: running state or step count must differ
        if (
            self._last_is_running is not None
            and is_running == self._last_is_running
            and total_steps == self._last_total_steps
        ):
            return None

        # Detect start/stop transitions for event emission
        was_running = self._last_is_running
        self._last_is_running = is_running
        self._last_total_steps = total_steps

        status_data: Dict[str, Any] = {
            "is_initialized": getattr(status, "is_initialized", False),
            "is_running": is_running,
            "total_steps": total_steps,
            "current_time": getattr(status, "current_time", 0.0),
            "registered_networks": getattr(status, "registered_networks", 0),
            "registered_processors": getattr(status, "registered_processors", 0),
            "registered_interfaces": getattr(status, "registered_interfaces", 0),
            "memory_usage": getattr(status, "memory_usage", 0),
        }

        entry = BlackboardEntry(
            topic="neuromorphic.simulation.status",
            data=status_data,
            source_module=self.MODULE_NAME,
            confidence=0.99,
            priority=EntryPriority.HIGH if is_running else EntryPriority.NORMAL,
            ttl_seconds=self._status_ttl,
            tags=frozenset({"simulation", "status", "neuromorphic"}),
            metadata={"is_running": is_running, "total_steps": total_steps},
        )

        # Emit state transition events
        if was_running is not None and is_running and not was_running:
            self._emit(
                "neuromorphic.simulation.started",
                {"total_steps": total_steps, "entry_id": entry.entry_id},
            )
        elif was_running is not None and not is_running and was_running:
            self._emit(
                "neuromorphic.simulation.stopped",
                {"total_steps": total_steps, "entry_id": entry.entry_id},
            )

        return entry

    def _produce_simulation_performance(self) -> Optional[BlackboardEntry]:
        """Query NeuromorphicManager for performance metrics.

        Change detection triggers when ``steps_per_second`` changes by >5%.
        """
        if self._manager is None:
            return None

        try:
            perf = self._manager.get_performance_metrics()
        except Exception:
            logger.debug(
                "NeuromorphicManager.get_performance_metrics() failed", exc_info=True
            )
            return None

        steps_per_second = getattr(perf, "steps_per_second", 0.0)

        # Change detection: >5% relative change in step rate
        if self._last_steps_per_second is not None:
            if self._last_steps_per_second == 0 and steps_per_second == 0:
                return None
            denom = max(abs(self._last_steps_per_second), 1e-9)
            rel_change = abs(steps_per_second - self._last_steps_per_second) / denom
            if rel_change < 0.05:
                return None

        prev_sps = self._last_steps_per_second
        self._last_steps_per_second = steps_per_second

        perf_data: Dict[str, Any] = {
            "avg_step_time": getattr(perf, "avg_step_time", 0.0),
            "steps_per_second": steps_per_second,
            "total_spikes": getattr(perf, "total_spikes", 0),
            "spike_rate": getattr(perf, "spike_rate", 0.0),
            "memory_usage": getattr(perf, "memory_usage", 0),
        }

        # Determine priority based on performance
        priority = EntryPriority.NORMAL
        if steps_per_second > 0 and getattr(perf, "avg_step_time", 0) > 0.1:
            priority = EntryPriority.HIGH  # Slow simulation step

        entry = BlackboardEntry(
            topic="neuromorphic.simulation.performance",
            data=perf_data,
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=priority,
            ttl_seconds=self._performance_ttl,
            tags=frozenset({"simulation", "performance", "metrics"}),
            metadata={"steps_per_second": steps_per_second},
        )

        # Emit degradation event if rate dropped significantly
        if (
            prev_sps is not None
            and prev_sps > 0
            and steps_per_second < prev_sps * 0.95
        ):
            self._emit(
                "neuromorphic.performance.degraded",
                {
                    "previous_sps": prev_sps,
                    "current_sps": steps_per_second,
                    "drop_pct": round((1 - steps_per_second / prev_sps) * 100, 2),
                    "entry_id": entry.entry_id,
                },
            )

        return entry

    def _produce_spike_monitor(self) -> Optional[BlackboardEntry]:
        """Query SpikeMonitor for statistics and return an entry if spike count changed."""
        if self._spike_monitor is None:
            return None

        try:
            stats = self._spike_monitor.get_statistics()
        except Exception:
            logger.debug("SpikeMonitor.get_statistics() failed", exc_info=True)
            return None

        total_spikes = getattr(stats, "total_spikes", 0)

        # Change detection: total spike count must have increased
        if self._last_total_spikes is not None and total_spikes == self._last_total_spikes:
            return None

        prev_spikes = self._last_total_spikes
        self._last_total_spikes = total_spikes

        spike_data: Dict[str, Any] = {
            "total_spikes": total_spikes,
            "active_neurons": getattr(stats, "active_neurons", 0),
            "avg_firing_rate": getattr(stats, "avg_firing_rate", 0.0),
            "max_firing_rate": getattr(stats, "max_firing_rate", 0.0),
            "synchrony_index": getattr(stats, "synchrony_index", 0.0),
            "recording_duration": getattr(stats, "recording_duration", 0.0),
        }

        # Higher confidence when more spikes are recorded (richer data)
        confidence = min(1.0, 0.5 + total_spikes / 10000.0)

        entry = BlackboardEntry(
            topic="neuromorphic.spike.monitor",
            data=spike_data,
            source_module=self.MODULE_NAME,
            confidence=confidence,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._spike_ttl,
            tags=frozenset({"spikes", "monitor", "firing_rate", "synchrony"}),
            metadata={
                "total_spikes": total_spikes,
                "synchrony_index": getattr(stats, "synchrony_index", 0.0),
            },
        )

        # Emit burst event if spike count jumped significantly
        if prev_spikes is not None and prev_spikes > 0:
            spike_jump = total_spikes - prev_spikes
            if spike_jump > prev_spikes * 0.5:  # >50% increase in one sweep
                self._emit(
                    "neuromorphic.spikes.burst",
                    {
                        "previous_total": prev_spikes,
                        "current_total": total_spikes,
                        "spike_jump": spike_jump,
                        "entry_id": entry.entry_id,
                    },
                )

        return entry

    def _produce_event_statistics(self) -> Optional[BlackboardEntry]:
        """Query EventProcessor for throughput stats and return if changed.

        Change detection triggers on ``total_processed`` (exact int comparison).
        """
        if self._event_processor is None:
            return None

        try:
            stats = self._event_processor.get_statistics()
        except Exception:
            logger.debug("EventProcessor.get_statistics() failed", exc_info=True)
            return None

        # get_statistics() returns a Dict
        if isinstance(stats, dict):
            total_processed = stats.get("total_processed", stats.get("total processed", 0))
        else:
            total_processed = getattr(stats, "total_processed", 0)

        # Change detection: total processed must differ
        if (
            self._last_events_processed is not None
            and total_processed == self._last_events_processed
        ):
            return None

        self._last_events_processed = total_processed

        # Normalize the stats dict
        if isinstance(stats, dict):
            event_data = {
                "total_processed": total_processed,
                "queue_sizes": stats.get("queue_sizes", stats.get("queue sizes", {})),
                "processing_rate": stats.get(
                    "processing_rate", stats.get("processing rate", 0.0)
                ),
                "events_by_type": stats.get(
                    "events_by_type", stats.get("events by type", {})
                ),
            }
        else:
            event_data = {
                "total_processed": total_processed,
                "queue_sizes": getattr(stats, "queue_sizes", {}),
                "processing_rate": getattr(stats, "processing_rate", 0.0),
                "events_by_type": getattr(stats, "events_by_type", {}),
            }

        entry = BlackboardEntry(
            topic="neuromorphic.event.statistics",
            data=event_data,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._event_ttl,
            tags=frozenset({"events", "statistics", "throughput"}),
            metadata={"total_processed": total_processed},
        )

        return entry

    def _produce_learning_update(self) -> Optional[BlackboardEntry]:
        """Query STDPLearning for weight change statistics.

        Change detection triggers on ``total_updates`` (exact int comparison).
        """
        if self._stdp is None:
            return None

        try:
            stats = self._stdp.get_statistics()
        except Exception:
            logger.debug("STDPLearning.get_statistics() failed", exc_info=True)
            return None

        # get_statistics() returns a Dict
        if isinstance(stats, dict):
            total_updates = stats.get("total_updates", 0)
        else:
            total_updates = getattr(stats, "total_updates", 0)

        # Change detection: total updates must differ
        if (
            self._last_total_updates is not None
            and total_updates == self._last_total_updates
        ):
            return None

        prev_updates = self._last_total_updates
        self._last_total_updates = total_updates

        if isinstance(stats, dict):
            learning_data = {
                "total_updates": total_updates,
                "avg_weight_change": stats.get("avg_weight_change", 0.0),
                "ltp_count": stats.get("ltp_count", stats.get("ltp", 0)),
                "ltd_count": stats.get("ltd_count", stats.get("ltd", 0)),
            }
        else:
            learning_data = {
                "total_updates": total_updates,
                "avg_weight_change": getattr(stats, "avg_weight_change", 0.0),
                "ltp_count": getattr(stats, "ltp_count", 0),
                "ltd_count": getattr(stats, "ltd_count", 0),
            }

        # Higher priority when learning is active (many recent updates)
        update_burst = (
            total_updates - prev_updates if prev_updates is not None else total_updates
        )
        priority = EntryPriority.HIGH if update_burst > 100 else EntryPriority.NORMAL

        entry = BlackboardEntry(
            topic="neuromorphic.learning.update",
            data=learning_data,
            source_module=self.MODULE_NAME,
            confidence=0.85,
            priority=priority,
            ttl_seconds=self._learning_ttl,
            tags=frozenset({"stdp", "learning", "plasticity", "weights"}),
            metadata={
                "total_updates": total_updates,
                "avg_weight_change": learning_data["avg_weight_change"],
            },
        )

        # Emit weight shift event if avg_weight_change is significant
        avg_change = learning_data["avg_weight_change"]
        if abs(avg_change) > 0.01:
            self._emit(
                "neuromorphic.learning.weight_shift",
                {
                    "avg_weight_change": avg_change,
                    "total_updates": total_updates,
                    "ltp_count": learning_data["ltp_count"],
                    "ltd_count": learning_data["ltd_count"],
                    "entry_id": entry.entry_id,
                },
            )

        return entry

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_bci(self, entry: BlackboardEntry) -> None:
        """Feed BCI neural signal data into the event processor as external events.

        BCI entries carry raw or decoded neural signals.  We submit them
        to the ``EventProcessor`` as high-priority external input events so
        the spiking simulation can react to real neural data.
        """
        if self._event_processor is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        nm = _get_neuromorphic()

        # Try to create a proper event object if the module is available
        event_obj = None
        if nm is not None:
            EventClass = getattr(nm, "NeuromorphicEvent", None)
            if EventClass is None:
                try:
                    from asi_build.neuromorphic.core.event_processor import (
                        NeuromorphicEvent,
                    )
                    EventClass = NeuromorphicEvent
                except (ImportError, AttributeError):
                    EventClass = None

            if EventClass is not None:
                try:
                    event_obj = EventClass(
                        event_type="external_input",
                        data=data,
                        source=f"bci:{entry.entry_id}",
                        timestamp=entry.timestamp,
                    )
                except Exception:
                    pass

        if event_obj is not None:
            try:
                self._event_processor.submit_event(event_obj, high_priority=True)
            except Exception:
                logger.debug("Failed to submit BCI event to EventProcessor", exc_info=True)
        else:
            # Fallback: submit raw data dict if event class unavailable
            try:
                self._event_processor.submit_event(
                    {
                        "type": "external_input",
                        "source": f"bci:{entry.entry_id}",
                        "data": data,
                        "timestamp": entry.timestamp,
                    },
                    high_priority=True,
                )
            except Exception:
                logger.debug(
                    "Failed to submit BCI dict event to EventProcessor", exc_info=True
                )

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Modulate simulation parameters based on consciousness state.

        Consciousness broadcasts and Φ values can influence the neuromorphic
        simulation — e.g. higher Φ → tighter synchronization constraints,
        attention focus → bias input weights for specific network regions.
        """
        if self._manager is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        # Extract relevant consciousness metrics
        phi = data.get("phi", data.get("phi_value"))
        state_name = data.get("state", data.get("state_name", data.get("consciousness_state")))
        broadcast_strength = data.get("broadcast_strength")

        # Modulate simulation parameters if the manager supports it
        if phi is not None and hasattr(self._manager, "set_parameter"):
            try:
                # Scale global inhibition with Φ — higher integration → more
                # correlated activity through tighter inhibitory control
                inhibition_factor = min(1.0, float(phi) / 5.0)
                self._manager.set_parameter("global_inhibition", inhibition_factor)
            except Exception:
                logger.debug("Failed to set global_inhibition from phi", exc_info=True)

        if broadcast_strength is not None and hasattr(self._manager, "set_parameter"):
            try:
                # Broadcast strength modulates simulation gain
                self._manager.set_parameter(
                    "input_gain", 0.5 + float(broadcast_strength) * 0.5
                )
            except Exception:
                logger.debug(
                    "Failed to set input_gain from broadcast_strength", exc_info=True
                )

        if state_name is not None and hasattr(self._manager, "set_parameter"):
            try:
                # Map consciousness states to simulation modes
                mode_map = {
                    "focused": "synchronous",
                    "diffuse": "asynchronous",
                    "dreaming": "spontaneous",
                    "idle": "resting",
                }
                mode = mode_map.get(str(state_name).lower())
                if mode is not None:
                    self._manager.set_parameter("simulation_mode", mode)
            except Exception:
                logger.debug(
                    "Failed to set simulation_mode from consciousness state", exc_info=True
                )

    def _consume_quantum(self, entry: BlackboardEntry) -> None:
        """Apply quantum optimization results to network topology.

        Quantum modules may optimize network connectivity patterns,
        weight distributions, or routing tables.  We apply these as
        topology updates to registered networks in the manager.
        """
        if self._manager is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        # Topology optimization: new network connections or weight matrix
        optimized_weights = data.get("optimized_weights", data.get("weights"))
        target_network = data.get("network", data.get("target_network", "default"))

        if optimized_weights is not None and hasattr(self._manager, "update_network_weights"):
            try:
                self._manager.update_network_weights(target_network, optimized_weights)
            except Exception:
                logger.debug(
                    "Failed to apply quantum-optimized weights to network '%s'",
                    target_network,
                    exc_info=True,
                )

        # Topology restructuring: new connections
        new_connections = data.get("connections", data.get("topology"))
        if new_connections is not None and hasattr(self._manager, "update_network_topology"):
            try:
                self._manager.update_network_topology(target_network, new_connections)
            except Exception:
                logger.debug(
                    "Failed to apply quantum topology update to network '%s'",
                    target_network,
                    exc_info=True,
                )

    # ── Event→Simulation injection ────────────────────────────────────

    def _handle_bci_event(self, event: CognitiveEvent) -> None:
        """Convert a BCI event into an external input for the event processor."""
        if self._event_processor is None:
            return

        try:
            self._event_processor.submit_event(
                {
                    "type": "external_input",
                    "source": f"bci_event:{event.event_id}",
                    "data": event.payload,
                    "timestamp": event.timestamp,
                },
                high_priority=True,
            )
        except Exception:
            logger.debug("Failed to inject BCI event into EventProcessor", exc_info=True)

    def _handle_consciousness_event(self, event: CognitiveEvent) -> None:
        """Modulate simulation from a consciousness state-change event."""
        if self._manager is None:
            return

        payload = event.payload or {}
        new_state = payload.get("new_state", payload.get("state"))

        if new_state is not None and hasattr(self._manager, "set_parameter"):
            try:
                mode_map = {
                    "focused": "synchronous",
                    "diffuse": "asynchronous",
                    "dreaming": "spontaneous",
                    "idle": "resting",
                }
                mode = mode_map.get(str(new_state).lower())
                if mode is not None:
                    self._manager.set_parameter("simulation_mode", mode)
            except Exception:
                logger.debug(
                    "Failed to modulate simulation from consciousness event", exc_info=True
                )

    def _handle_quantum_event(self, event: CognitiveEvent) -> None:
        """Apply quantum optimization results from an event."""
        if self._manager is None:
            return

        payload = event.payload or {}
        optimized_weights = payload.get("optimized_weights", payload.get("weights"))
        target_network = payload.get("network", "default")

        if optimized_weights is not None and hasattr(self._manager, "update_network_weights"):
            try:
                self._manager.update_network_weights(target_network, optimized_weights)
            except Exception:
                logger.debug(
                    "Failed to apply quantum event weights to network '%s'",
                    target_network,
                    exc_info=True,
                )

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all neuromorphic components.

        Useful for debugging and dashboard display.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_manager": self._manager is not None,
            "has_event_processor": self._event_processor is not None,
            "has_spike_monitor": self._spike_monitor is not None,
            "has_stdp": self._stdp is not None,
            "last_is_running": self._last_is_running,
            "last_total_steps": self._last_total_steps,
            "last_steps_per_second": self._last_steps_per_second,
            "last_total_spikes": self._last_total_spikes,
            "last_events_processed": self._last_events_processed,
            "last_total_updates": self._last_total_updates,
            "registered": self._blackboard is not None,
        }

        if self._manager is not None:
            try:
                status = self._manager.get_system_status()
                snap["current_is_running"] = getattr(status, "is_running", None)
                snap["current_total_steps"] = getattr(status, "total_steps", None)
            except Exception:
                snap["current_is_running"] = None

        if self._spike_monitor is not None:
            try:
                stats = self._spike_monitor.get_statistics()
                snap["current_total_spikes"] = getattr(stats, "total_spikes", None)
                snap["current_avg_firing_rate"] = getattr(stats, "avg_firing_rate", None)
            except Exception:
                pass

        if self._event_processor is not None:
            try:
                stats = self._event_processor.get_statistics()
                if isinstance(stats, dict):
                    snap["current_events_processed"] = stats.get(
                        "total_processed", stats.get("total processed")
                    )
                else:
                    snap["current_events_processed"] = getattr(
                        stats, "total_processed", None
                    )
            except Exception:
                pass

        if self._stdp is not None:
            try:
                stats = self._stdp.get_statistics()
                if isinstance(stats, dict):
                    snap["current_total_updates"] = stats.get("total_updates")
                    snap["current_avg_weight_change"] = stats.get("avg_weight_change")
                else:
                    snap["current_total_updates"] = getattr(stats, "total_updates", None)
            except Exception:
                pass

        return snap
