"""
Cognitive Cycle — Real-time perception→cognition→action tick loop.
==================================================================

The ``CognitiveCycle`` is the beating heart of the ASI:BUILD integration
layer.  It orchestrates all registered :class:`BlackboardParticipant`
adapters through a deterministic three-phase loop:

1. **Perceive** — collect fresh data from all *producers*
2. **Cognize**  — distribute entries to *consumers* and *transformers*
3. **Act**      — apply safety checks, emit aggregate events, update metrics

Each iteration is called a **tick**.  The cycle supports configurable tick
rates, graceful start/stop, pause/resume, and per-tick metrics for
monitoring and dashboards.

Architecture
~~~~~~~~~~~~

::

    ┌───────────────────────────────────────────────────────┐
    │                   CognitiveCycle                       │
    │                                                       │
    │   ┌───────────┐   ┌──────────┐   ┌─────────┐        │
    │   │  PERCEIVE │──►│ COGNIZE  │──►│   ACT   │        │
    │   │ (produce) │   │(consume/ │   │ (safety │        │
    │   │           │   │transform)│   │  sweep) │        │
    │   └───────────┘   └──────────┘   └─────────┘        │
    │          ▲                              │             │
    │          └──────────────────────────────┘             │
    │                    tick loop                          │
    │                                                       │
    │   CognitiveBlackboard                                │
    │   EventBus                                           │
    │   24 Adapters                                        │
    └───────────────────────────────────────────────────────┘

Usage
~~~~~

::

    from asi_build.integration import CognitiveBlackboard
    from asi_build.integration.cognitive_cycle import CognitiveCycle
    from asi_build.integration.adapters import (
        ConsciousnessAdapter,
        ReasoningAdapter,
        SafetyBlackboardAdapter,
        wire_all,
    )

    bb = CognitiveBlackboard()
    cycle = CognitiveCycle(blackboard=bb, tick_rate_hz=10.0)

    # Register adapters
    consciousness = ConsciousnessAdapter(gwt=my_gwt, iit=my_iit)
    reasoning = ReasoningAdapter(engine=my_engine)
    safety = SafetyBlackboardAdapter(verifier=my_verifier)

    cycle.register_adapter(consciousness)
    cycle.register_adapter(reasoning)
    cycle.register_adapter(safety, role="safety")  # safety gate

    # Run
    cycle.start()          # background thread
    cycle.wait(timeout=60) # block until stopped or timeout
    cycle.stop()           # graceful shutdown
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

from .blackboard import CognitiveBlackboard
from .events import EventBus
from .protocols import (
    BlackboardEntry,
    BlackboardQuery,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    ModuleCapability,
    ModuleInfo,
)

logger = logging.getLogger(__name__)

__all__ = [
    "CognitiveCycle",
    "CyclePhase",
    "CycleState",
    "CycleMetrics",
    "TickResult",
    "AdapterRole",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CyclePhase(enum.Enum):
    """Phase of the cognitive cycle."""

    IDLE = "idle"
    PERCEIVE = "perceive"
    COGNIZE = "cognize"
    ACT = "act"


class CycleState(enum.Enum):
    """Overall lifecycle state of the cycle."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AdapterRole(enum.Enum):
    """Special roles an adapter can fulfil in the cycle.

    Most adapters are ``GENERAL`` — they participate in all phases
    normally.  Special roles change *when* the adapter is invoked:

    - ``SAFETY``: Invoked in the Act phase as a gate.  If the safety
      adapter vetoes, downstream actions are suppressed.
    - ``PERCEPTION``: Only invoked during the Perceive phase.
    - ``ACTION``: Only invoked during the Act phase (post-safety).
    """

    GENERAL = "general"
    SAFETY = "safety"
    PERCEPTION = "perception"
    ACTION = "action"


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class TickResult:
    """Summary of a single tick's execution."""

    tick_number: int
    phase_times: Dict[str, float] = field(default_factory=dict)
    entries_produced: int = 0
    entries_consumed: int = 0
    entries_transformed: int = 0
    safety_checks: int = 0
    safety_vetoes: int = 0
    errors: List[str] = field(default_factory=list)
    total_time_ms: float = 0.0


@dataclass
class CycleMetrics:
    """Aggregate metrics across all ticks."""

    total_ticks: int = 0
    total_entries_produced: int = 0
    total_entries_consumed: int = 0
    total_entries_transformed: int = 0
    total_safety_checks: int = 0
    total_safety_vetoes: int = 0
    total_errors: int = 0
    avg_tick_time_ms: float = 0.0
    max_tick_time_ms: float = 0.0
    min_tick_time_ms: float = float("inf")
    uptime_seconds: float = 0.0
    ticks_per_second: float = 0.0

    # Per-adapter metrics
    adapter_produce_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    adapter_consume_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    adapter_error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict for dashboards / JSON."""
        return {
            "total_ticks": self.total_ticks,
            "total_entries_produced": self.total_entries_produced,
            "total_entries_consumed": self.total_entries_consumed,
            "total_entries_transformed": self.total_entries_transformed,
            "total_safety_checks": self.total_safety_checks,
            "total_safety_vetoes": self.total_safety_vetoes,
            "total_errors": self.total_errors,
            "avg_tick_time_ms": round(self.avg_tick_time_ms, 3),
            "max_tick_time_ms": round(self.max_tick_time_ms, 3),
            "min_tick_time_ms": round(self.min_tick_time_ms, 3)
            if self.min_tick_time_ms != float("inf")
            else 0.0,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "ticks_per_second": round(self.ticks_per_second, 3),
            "adapter_produce_counts": dict(self.adapter_produce_counts),
            "adapter_consume_counts": dict(self.adapter_consume_counts),
            "adapter_error_counts": dict(self.adapter_error_counts),
        }


# ---------------------------------------------------------------------------
# CognitiveCycle
# ---------------------------------------------------------------------------


class CognitiveCycle:
    """Orchestrates a perception→cognition→action loop over the Blackboard.

    Parameters
    ----------
    blackboard : CognitiveBlackboard
        The shared workspace all adapters communicate through.
    tick_rate_hz : float
        Target ticks per second.  Set to 0 for no rate limiting (run
        as fast as possible).  Default 10 Hz.
    max_ticks : int or None
        Stop automatically after this many ticks.  ``None`` = unlimited.
    safety_required : bool
        If ``True``, at least one adapter with ``role="safety"`` must be
        registered before the cycle can start.  Default ``True``.
    auto_wire : bool
        If ``True``, adapters are automatically wired to the blackboard
        and event bus on registration.  Default ``True``.
    on_tick : callable or None
        Optional callback invoked after each tick with ``(tick_number, TickResult)``.
    on_error : callable or None
        Optional callback invoked on per-adapter errors with ``(adapter_name, exception)``.
    """

    def __init__(
        self,
        blackboard: CognitiveBlackboard,
        *,
        tick_rate_hz: float = 10.0,
        max_ticks: Optional[int] = None,
        safety_required: bool = True,
        auto_wire: bool = True,
        on_tick: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> None:
        self._blackboard = blackboard
        self._tick_rate_hz = tick_rate_hz
        self._tick_interval = 1.0 / tick_rate_hz if tick_rate_hz > 0 else 0.0
        self._max_ticks = max_ticks
        self._safety_required = safety_required
        self._auto_wire = auto_wire
        self._on_tick = on_tick
        self._on_error = on_error

        # Adapter registry: name → (adapter, role)
        self._adapters: Dict[str, tuple] = {}  # name → (adapter_instance, AdapterRole)
        self._adapter_order: List[str] = []  # insertion order

        # State
        self._state = CycleState.CREATED
        self._phase = CyclePhase.IDLE
        self._tick_number = 0
        self._started_at: Optional[float] = None
        self._stopped_at: Optional[float] = None
        self._metrics = CycleMetrics()

        # Threading
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._thread: Optional[threading.Thread] = None

        # Tick history (ring buffer of last N results)
        self._tick_history: List[TickResult] = []
        self._history_maxlen = 100

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> CycleState:
        """Current lifecycle state."""
        return self._state

    @property
    def phase(self) -> CyclePhase:
        """Current phase within a tick."""
        return self._phase

    @property
    def tick_number(self) -> int:
        """Number of ticks completed."""
        return self._tick_number

    @property
    def tick_rate_hz(self) -> float:
        return self._tick_rate_hz

    @tick_rate_hz.setter
    def tick_rate_hz(self, hz: float) -> None:
        self._tick_rate_hz = hz
        self._tick_interval = 1.0 / hz if hz > 0 else 0.0

    @property
    def blackboard(self) -> CognitiveBlackboard:
        return self._blackboard

    @property
    def metrics(self) -> CycleMetrics:
        """Current aggregate metrics (read-only snapshot)."""
        with self._lock:
            return self._metrics

    @property
    def adapter_count(self) -> int:
        return len(self._adapters)

    @property
    def is_running(self) -> bool:
        return self._state == CycleState.RUNNING

    @property
    def is_paused(self) -> bool:
        return self._state == CycleState.PAUSED

    # ------------------------------------------------------------------
    # Adapter management
    # ------------------------------------------------------------------

    def register_adapter(
        self,
        adapter: Any,
        role: str = "general",
    ) -> str:
        """Register an adapter with the cycle.

        Parameters
        ----------
        adapter : BlackboardParticipant
            Must have ``module_info``, ``produce``, ``consume``, etc.
        role : str
            One of "general", "safety", "perception", "action".

        Returns
        -------
        str
            The adapter's MODULE_NAME.

        Raises
        ------
        ValueError
            If the adapter is already registered or *role* is invalid.
        RuntimeError
            If the cycle is already running (adapters must be registered
            before ``start()``).
        """
        name = getattr(adapter, "MODULE_NAME", None) or adapter.module_info.name
        adapter_role = AdapterRole(role)

        with self._lock:
            if name in self._adapters:
                raise ValueError(f"Adapter '{name}' is already registered")
            if self._state == CycleState.RUNNING:
                raise RuntimeError("Cannot register adapters while cycle is running")

            self._adapters[name] = (adapter, adapter_role)
            self._adapter_order.append(name)

        # Auto-wire to blackboard
        if self._auto_wire:
            try:
                self._blackboard.register_module(adapter)
            except ValueError:
                pass  # Already registered (e.g. user did it manually)

            if hasattr(adapter, "set_event_handler"):
                adapter.set_event_handler(self._blackboard.event_bus.emit)

            if hasattr(adapter, "handle_event"):
                info = adapter.module_info
                for topic in info.topics_consumed:
                    self._blackboard.event_bus.subscribe(
                        pattern=f"{topic}.*",
                        handler=adapter.handle_event,
                        source_filter=None,
                    )

        logger.info("CognitiveCycle: registered adapter %s (role=%s)", name, role)
        return name

    def unregister_adapter(self, name: str) -> bool:
        """Remove an adapter.  Returns True if it was registered."""
        with self._lock:
            if name not in self._adapters:
                return False
            del self._adapters[name]
            self._adapter_order = [n for n in self._adapter_order if n != name]
        return True

    def get_adapter(self, name: str) -> Optional[Any]:
        """Retrieve a registered adapter by name."""
        with self._lock:
            pair = self._adapters.get(name)
            return pair[0] if pair else None

    def list_adapters(self) -> List[Dict[str, Any]]:
        """Return info about all registered adapters."""
        with self._lock:
            result = []
            for name in self._adapter_order:
                adapter, role = self._adapters[name]
                info = adapter.module_info
                result.append(
                    {
                        "name": name,
                        "role": role.value,
                        "version": info.version,
                        "capabilities": str(info.capabilities),
                        "topics_produced": list(info.topics_produced),
                        "topics_consumed": list(info.topics_consumed),
                    }
                )
            return result

    # ------------------------------------------------------------------
    # Lifecycle control
    # ------------------------------------------------------------------

    def start(self, daemon: bool = True) -> None:
        """Start the cognitive cycle in a background thread.

        Parameters
        ----------
        daemon : bool
            Whether the thread is a daemon (default True).

        Raises
        ------
        RuntimeError
            If the cycle is already running, or if safety is required
            but no safety adapter is registered.
        """
        with self._lock:
            if self._state in (CycleState.RUNNING, CycleState.STARTING):
                raise RuntimeError(f"Cycle is already {self._state.value}")

            # Safety gate check
            if self._safety_required:
                has_safety = any(
                    role == AdapterRole.SAFETY for _, role in self._adapters.values()
                )
                if not has_safety:
                    raise RuntimeError(
                        "safety_required=True but no adapter registered with role='safety'. "
                        "Either register a SafetyBlackboardAdapter(role='safety') or "
                        "set safety_required=False."
                    )

            self._state = CycleState.STARTING
            self._stop_event.clear()
            self._pause_event.set()
            self._started_at = time.time()

        self._thread = threading.Thread(
            target=self._run_loop,
            name="CognitiveCycle",
            daemon=daemon,
        )
        self._thread.start()
        self._state = CycleState.RUNNING

        self._blackboard.event_bus.emit(
            CognitiveEvent(
                event_type="cycle.started",
                payload={
                    "tick_rate_hz": self._tick_rate_hz,
                    "adapter_count": len(self._adapters),
                    "max_ticks": self._max_ticks,
                },
                source="cognitive_cycle",
            )
        )
        logger.info(
            "CognitiveCycle started (%.1f Hz, %d adapters)",
            self._tick_rate_hz,
            len(self._adapters),
        )

    def stop(self, timeout: float = 10.0) -> None:
        """Signal the cycle to stop and wait for the thread to finish.

        Parameters
        ----------
        timeout : float
            Maximum seconds to wait for the thread to join.
        """
        self._state = CycleState.STOPPING
        self._stop_event.set()
        self._pause_event.set()  # Unpause so the loop can exit

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        self._stopped_at = time.time()
        self._state = CycleState.STOPPED

        if self._started_at:
            self._metrics.uptime_seconds = (self._stopped_at or time.time()) - self._started_at

        self._blackboard.event_bus.emit(
            CognitiveEvent(
                event_type="cycle.stopped",
                payload={
                    "total_ticks": self._tick_number,
                    "uptime_seconds": self._metrics.uptime_seconds,
                },
                source="cognitive_cycle",
            )
        )
        logger.info("CognitiveCycle stopped after %d ticks", self._tick_number)

    def pause(self) -> None:
        """Pause the cycle.  The current tick will complete first."""
        self._pause_event.clear()
        self._state = CycleState.PAUSED
        self._blackboard.event_bus.emit(
            CognitiveEvent(
                event_type="cycle.paused",
                payload={"tick_number": self._tick_number},
                source="cognitive_cycle",
            )
        )
        logger.info("CognitiveCycle paused at tick %d", self._tick_number)

    def resume(self) -> None:
        """Resume a paused cycle."""
        self._pause_event.set()
        self._state = CycleState.RUNNING
        self._blackboard.event_bus.emit(
            CognitiveEvent(
                event_type="cycle.resumed",
                payload={"tick_number": self._tick_number},
                source="cognitive_cycle",
            )
        )
        logger.info("CognitiveCycle resumed at tick %d", self._tick_number)

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until the cycle stops (or *timeout* elapses).

        Returns ``True`` if the cycle stopped, ``False`` on timeout.
        """
        if self._thread is None:
            return True
        self._thread.join(timeout=timeout)
        return not self._thread.is_alive()

    # ------------------------------------------------------------------
    # Single tick (can also be called manually for testing)
    # ------------------------------------------------------------------

    def tick(self) -> TickResult:
        """Execute a single perception→cognition→action tick.

        This is the core method.  ``start()`` calls it in a loop, but
        it can also be called directly for unit testing or step-by-step
        execution.

        Returns
        -------
        TickResult
            Summary of what happened during this tick.
        """
        self._tick_number += 1
        result = TickResult(tick_number=self._tick_number)
        tick_start = time.monotonic()

        # ── Phase 1: PERCEIVE ────────────────────────────────────────
        self._phase = CyclePhase.PERCEIVE
        phase_start = time.monotonic()

        produced_entries: List[BlackboardEntry] = []
        for name in self._adapter_order:
            pair = self._adapters.get(name)
            if pair is None:
                continue
            adapter, role = pair

            # Skip action-only adapters during perception
            if role == AdapterRole.ACTION:
                continue

            if not hasattr(adapter, "produce"):
                continue

            try:
                entries = adapter.produce()
                if entries:
                    produced_entries.extend(entries)
                    result.entries_produced += len(entries)
                    self._metrics.adapter_produce_counts[name] += len(entries)
            except Exception as exc:
                self._record_adapter_error(name, exc, result)

        # Post all produced entries to the blackboard
        if produced_entries:
            try:
                self._blackboard.post_many(produced_entries)
            except Exception as exc:
                result.errors.append(f"blackboard.post_many: {exc}")

        result.phase_times["perceive"] = (time.monotonic() - phase_start) * 1000

        # ── Phase 2: COGNIZE ─────────────────────────────────────────
        self._phase = CyclePhase.COGNIZE
        phase_start = time.monotonic()

        # Distribute entries to consumers
        for name in self._adapter_order:
            pair = self._adapters.get(name)
            if pair is None:
                continue
            adapter, role = pair

            # Skip perception-only and action-only adapters
            if role in (AdapterRole.PERCEPTION, AdapterRole.ACTION):
                continue

            if not hasattr(adapter, "consume"):
                continue

            info = adapter.module_info
            # Find entries matching this adapter's consumed topics
            relevant_entries: List[BlackboardEntry] = []
            for topic in info.topics_consumed:
                try:
                    entries = self._blackboard.get_by_topic(topic, include_subtopics=True)
                    relevant_entries.extend(entries)
                except Exception:
                    pass

            if not relevant_entries:
                continue

            # Deduplicate by entry_id
            seen: Set[str] = set()
            unique_entries: List[BlackboardEntry] = []
            for e in relevant_entries:
                if e.entry_id not in seen:
                    seen.add(e.entry_id)
                    unique_entries.append(e)

            try:
                adapter.consume(unique_entries)
                result.entries_consumed += len(unique_entries)
                self._metrics.adapter_consume_counts[name] += len(unique_entries)
            except Exception as exc:
                self._record_adapter_error(name, exc, result)

        # Run transformers
        for name in self._adapter_order:
            pair = self._adapters.get(name)
            if pair is None:
                continue
            adapter, role = pair

            if not hasattr(adapter, "transform"):
                continue

            info = adapter.module_info
            if ModuleCapability.TRANSFORMER not in info.capabilities:
                continue

            # Get entries this transformer wants
            transform_input: List[BlackboardEntry] = []
            for topic in info.topics_consumed:
                try:
                    entries = self._blackboard.get_by_topic(topic, include_subtopics=True)
                    transform_input.extend(entries)
                except Exception:
                    pass

            if not transform_input:
                continue

            try:
                transformed = adapter.transform(transform_input)
                if transformed:
                    result.entries_transformed += len(transformed)
                    self._blackboard.post_many(list(transformed))
            except Exception as exc:
                self._record_adapter_error(name, exc, result)

        result.phase_times["cognize"] = (time.monotonic() - phase_start) * 1000

        # ── Phase 3: ACT ─────────────────────────────────────────────
        self._phase = CyclePhase.ACT
        phase_start = time.monotonic()

        # Safety checks
        for name in self._adapter_order:
            pair = self._adapters.get(name)
            if pair is None:
                continue
            adapter, role = pair

            if role != AdapterRole.SAFETY:
                continue

            # Safety adapter produces verification results
            if hasattr(adapter, "produce"):
                try:
                    safety_entries = adapter.produce()
                    if safety_entries:
                        result.safety_checks += len(safety_entries)
                        self._metrics.total_safety_checks += len(safety_entries)

                        for se in safety_entries:
                            data = se.data if isinstance(se.data, dict) else {}
                            if data.get("is_ethical") is False or se.priority == EntryPriority.CRITICAL:
                                result.safety_vetoes += 1
                                self._metrics.total_safety_vetoes += 1

                        self._blackboard.post_many(list(safety_entries))
                except Exception as exc:
                    self._record_adapter_error(name, exc, result)

        # Run action-role adapters
        for name in self._adapter_order:
            pair = self._adapters.get(name)
            if pair is None:
                continue
            adapter, role = pair

            if role != AdapterRole.ACTION:
                continue

            if hasattr(adapter, "produce"):
                try:
                    action_entries = adapter.produce()
                    if action_entries:
                        self._blackboard.post_many(list(action_entries))
                        result.entries_produced += len(action_entries)
                except Exception as exc:
                    self._record_adapter_error(name, exc, result)

        # Sweep expired entries
        try:
            self._blackboard.sweep_expired()
        except Exception:
            pass

        result.phase_times["act"] = (time.monotonic() - phase_start) * 1000

        # ── Tick bookkeeping ─────────────────────────────────────────
        self._phase = CyclePhase.IDLE
        result.total_time_ms = (time.monotonic() - tick_start) * 1000

        self._update_metrics(result)

        # Emit tick event
        self._blackboard.event_bus.emit(
            CognitiveEvent(
                event_type="cycle.tick.completed",
                payload={
                    "tick_number": result.tick_number,
                    "total_time_ms": round(result.total_time_ms, 3),
                    "entries_produced": result.entries_produced,
                    "entries_consumed": result.entries_consumed,
                    "safety_checks": result.safety_checks,
                    "safety_vetoes": result.safety_vetoes,
                    "errors": len(result.errors),
                },
                source="cognitive_cycle",
            )
        )

        # User callback
        if self._on_tick is not None:
            try:
                self._on_tick(result.tick_number, result)
            except Exception:
                logger.debug("on_tick callback raised", exc_info=True)

        # History ring buffer
        self._tick_history.append(result)
        if len(self._tick_history) > self._history_maxlen:
            self._tick_history.pop(0)

        return result

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status snapshot."""
        with self._lock:
            uptime = 0.0
            if self._started_at:
                end = self._stopped_at or time.time()
                uptime = end - self._started_at

            return {
                "state": self._state.value,
                "phase": self._phase.value,
                "tick_number": self._tick_number,
                "tick_rate_hz": self._tick_rate_hz,
                "max_ticks": self._max_ticks,
                "adapter_count": len(self._adapters),
                "safety_required": self._safety_required,
                "uptime_seconds": round(uptime, 2),
                "blackboard_entries": self._blackboard.entry_count,
                "blackboard_modules": self._blackboard.module_count,
                "metrics": self._metrics.to_dict(),
            }

    def get_tick_history(self, last_n: int = 10) -> List[Dict[str, Any]]:
        """Return the last *n* tick results as dicts."""
        history = self._tick_history[-last_n:]
        return [
            {
                "tick_number": r.tick_number,
                "total_time_ms": round(r.total_time_ms, 3),
                "entries_produced": r.entries_produced,
                "entries_consumed": r.entries_consumed,
                "entries_transformed": r.entries_transformed,
                "safety_checks": r.safety_checks,
                "safety_vetoes": r.safety_vetoes,
                "errors": r.errors,
                "phase_times": {k: round(v, 3) for k, v in r.phase_times.items()},
            }
            for r in history
        ]

    # ------------------------------------------------------------------
    # Internal: main loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Background thread target — runs tick() in a loop."""
        try:
            while not self._stop_event.is_set():
                # Pause support
                self._pause_event.wait()
                if self._stop_event.is_set():
                    break

                tick_start = time.monotonic()

                try:
                    self.tick()
                except Exception:
                    logger.error("CognitiveCycle tick %d failed", self._tick_number, exc_info=True)
                    self._metrics.total_errors += 1

                # Max ticks check
                if self._max_ticks is not None and self._tick_number >= self._max_ticks:
                    logger.info("CognitiveCycle reached max_ticks=%d", self._max_ticks)
                    break

                # Rate limiting
                if self._tick_interval > 0:
                    elapsed = time.monotonic() - tick_start
                    sleep_time = self._tick_interval - elapsed
                    if sleep_time > 0:
                        self._stop_event.wait(timeout=sleep_time)

        except Exception:
            logger.error("CognitiveCycle loop crashed", exc_info=True)
            self._state = CycleState.ERROR

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    def _record_adapter_error(
        self,
        adapter_name: str,
        exc: Exception,
        result: TickResult,
    ) -> None:
        """Record an adapter error."""
        msg = f"{adapter_name}: {type(exc).__name__}: {exc}"
        result.errors.append(msg)
        self._metrics.total_errors += 1
        self._metrics.adapter_error_counts[adapter_name] += 1
        logger.debug("CognitiveCycle adapter error: %s", msg, exc_info=True)

        if self._on_error is not None:
            try:
                self._on_error(adapter_name, exc)
            except Exception:
                pass

    def _update_metrics(self, result: TickResult) -> None:
        """Update aggregate metrics from a tick result."""
        m = self._metrics
        m.total_ticks += 1
        m.total_entries_produced += result.entries_produced
        m.total_entries_consumed += result.entries_consumed
        m.total_entries_transformed += result.entries_transformed
        m.total_errors += len(result.errors)

        t = result.total_time_ms
        m.max_tick_time_ms = max(m.max_tick_time_ms, t)
        m.min_tick_time_ms = min(m.min_tick_time_ms, t)

        # Running average
        if m.total_ticks > 0:
            m.avg_tick_time_ms = (
                m.avg_tick_time_ms * (m.total_ticks - 1) + t
            ) / m.total_ticks

        if self._started_at:
            elapsed = time.time() - self._started_at
            if elapsed > 0:
                m.uptime_seconds = elapsed
                m.ticks_per_second = m.total_ticks / elapsed

    def __repr__(self) -> str:
        return (
            f"<CognitiveCycle state={self._state.value} "
            f"tick={self._tick_number} "
            f"adapters={len(self._adapters)} "
            f"rate={self._tick_rate_hz}Hz>"
        )
