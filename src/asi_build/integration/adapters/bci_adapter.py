"""
BCI ↔ Blackboard Adapter
=========================

Bridges the Brain-Computer Interface module (``BCIManager``, ``SignalProcessor``,
``NeuralDecoder``) with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``bci.signal.processed``       — Latest processed neural signal with features
- ``bci.signal.quality``         — Signal quality score (change-detected >5%)
- ``bci.decode.result``          — Neural decoder output (class + confidence)
- ``bci.decode.performance``     — Decoder accuracy / precision / recall / F1
- ``bci.session.status``         — Active sessions and device/processing state
- ``bci.calibration.result``     — Calibration results (accuracy, timing)

Topics consumed
~~~~~~~~~~~~~~~
- ``consciousness.*``            — Consciousness state → neurofeedback parameters
- ``neuromorphic.*``             — Spike data → cross-modal neural analysis
- ``holographic.*``              — Holographic display → BCI-controlled rendering

Events emitted
~~~~~~~~~~~~~~
- ``bci.signal.quality.changed``    — Quality score crossed a threshold
- ``bci.decode.completed``          — New decoding result available
- ``bci.session.state.changed``     — Session started / stopped / error
- ``bci.calibration.completed``     — Calibration finished with results

Events listened
~~~~~~~~~~~~~~~
- ``consciousness.phi.updated``           — Modulate neurofeedback based on Φ
- ``consciousness.state.changed``         — Adapt BCI processing mode
- ``neuromorphic.spike.detected``         — Cross-modal spike-BCI correlation
- ``holographic.render.completed``        — Update BCI-driven display parameters
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

# Lazy imports — the BCI module may not be available
_bci_module = None


def _get_bci():
    """Lazy import of BCI module to allow graceful degradation."""
    global _bci_module
    if _bci_module is None:
        try:
            from asi_build import bci as _bm

            _bci_module = _bm
        except (ImportError, ModuleNotFoundError):
            _bci_module = False
    return _bci_module if _bci_module is not False else None


class BCIBlackboardAdapter:
    """Adapter connecting the BCI module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``BCIManager`` — session lifecycle, device management, calibration
    - ``SignalProcessor`` — real-time filtering, ICA, feature extraction
    - ``NeuralDecoder`` — classification of processed signals into intents

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    bci_manager : optional
        A ``BCIManager`` instance for session and device management.
    signal_processor : optional
        A ``SignalProcessor`` instance for real-time neural signal processing.
    neural_decoder : optional
        A ``NeuralDecoder`` instance for decoding processed signals.
    signal_ttl : float
        TTL in seconds for processed signal entries (default 30 = 30 seconds).
    quality_ttl : float
        TTL for signal quality entries (default 60 = 1 minute).
    decode_ttl : float
        TTL for decoding result entries (default 60 = 1 minute).
    performance_ttl : float
        TTL for performance summary entries (default 300 = 5 minutes).
    session_ttl : float
        TTL for session status entries (default 120 = 2 minutes).
    calibration_ttl : float
        TTL for calibration result entries (default 600 = 10 minutes).
    """

    # ── Protocol-required property ────────────────────────────────────
    MODULE_NAME = "bci"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        bci_manager: Any = None,
        signal_processor: Any = None,
        neural_decoder: Any = None,
        *,
        signal_ttl: float = 30.0,
        quality_ttl: float = 60.0,
        decode_ttl: float = 60.0,
        performance_ttl: float = 300.0,
        session_ttl: float = 120.0,
        calibration_ttl: float = 600.0,
    ) -> None:
        self._bci_manager = bci_manager
        self._signal_processor = signal_processor
        self._neural_decoder = neural_decoder
        self._signal_ttl = signal_ttl
        self._quality_ttl = quality_ttl
        self._decode_ttl = decode_ttl
        self._performance_ttl = performance_ttl
        self._session_ttl = session_ttl
        self._calibration_ttl = calibration_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Track last values for change detection
        self._last_signal_timestamp: Optional[float] = None
        self._last_quality_score: Optional[float] = None
        self._last_decoded_class: Optional[str] = None
        self._last_decode_confidence: Optional[float] = None
        self._last_accuracy: Optional[float] = None
        self._last_active_sessions: Optional[int] = None
        self._last_calibration_timestamp: Optional[float] = None

        # Neurofeedback state driven by consumed consciousness data
        self._neurofeedback_params: Dict[str, Any] = {
            "phi_target": 3.0,
            "feedback_gain": 1.0,
            "mode": "default",
        }

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
                "Brain-Computer Interface module: real-time signal processing, "
                "neural decoding, session management, and calibration."
            ),
            topics_produced=frozenset(
                {
                    "bci.signal.processed",
                    "bci.signal.quality",
                    "bci.decode.result",
                    "bci.decode.performance",
                    "bci.session.status",
                    "bci.calibration.result",
                }
            ),
            topics_consumed=frozenset(
                {
                    "consciousness",
                    "neuromorphic",
                    "holographic",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "BCIBlackboardAdapter registered with blackboard "
            "(manager=%s, processor=%s, decoder=%s)",
            self._bci_manager is not None,
            self._signal_processor is not None,
            self._neural_decoder is not None,
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

        Routes consciousness, neuromorphic, and holographic events to
        the appropriate BCI subsystems for cross-modal integration.
        """
        try:
            if event.event_type.startswith("consciousness."):
                self._handle_consciousness_event(event)
            elif event.event_type.startswith("neuromorphic."):
                self._handle_neuromorphic_event(event)
            elif event.event_type.startswith("holographic."):
                self._handle_holographic_event(event)
        except Exception:
            logger.debug(
                "BCIBlackboardAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current BCI state.

        Called during a production sweep.  Collects:
        1. Latest processed signal (timestamp change-detected)
        2. Signal quality score (>5% change threshold)
        3. Latest decoding result (class or confidence change)
        4. Decoder performance summary (accuracy change)
        5. Session status (active sessions count change)
        6. Calibration results (new calibration detected)
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            for producer_fn in (
                self._produce_signal_processed,
                self._produce_signal_quality,
                self._produce_decode_result,
                self._produce_decode_performance,
                self._produce_session_status,
                self._produce_calibration,
            ):
                entry = producer_fn()
                if entry is not None:
                    entries.append(entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        Consciousness state → neurofeedback parameter updates.
        Neuromorphic spike data → cross-modal neural analysis.
        Holographic display state → BCI-controlled rendering feedback.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
                elif entry.topic.startswith("neuromorphic."):
                    self._consume_neuromorphic(entry)
                elif entry.topic.startswith("holographic."):
                    self._consume_holographic(entry)
            except Exception:
                logger.debug(
                    "BCIBlackboardAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── BlackboardTransformer protocol ────────────────────────────────

    def transform(self, entries: Sequence[BlackboardEntry]) -> Sequence[BlackboardEntry]:
        """Enrich entries with BCI signal quality and decoded intent.

        For each incoming entry, appends BCI metadata:
        - ``bci_signal_quality``: current signal quality (0.0–1.0)
        - ``bci_decoded_intent``: latest decoded class, if available
        - ``bci_decode_confidence``: decoder confidence for the intent
        - ``bci_artifacts_detected``: whether artifacts were detected
        """
        enriched: List[BlackboardEntry] = []

        # Gather current BCI context once for the batch
        quality_score = self._get_current_quality()
        decoded_class = self._last_decoded_class
        decode_confidence = self._last_decode_confidence
        artifacts = self._get_current_artifacts()

        for entry in entries:
            bci_meta: Dict[str, Any] = {}

            if quality_score is not None:
                bci_meta["bci_signal_quality"] = quality_score

            if decoded_class is not None:
                bci_meta["bci_decoded_intent"] = decoded_class
                bci_meta["bci_decode_confidence"] = decode_confidence

            if artifacts is not None:
                bci_meta["bci_artifacts_detected"] = artifacts

            if not bci_meta:
                continue  # Nothing to enrich with

            # Build enriched metadata
            new_metadata = dict(entry.metadata) if entry.metadata else {}
            new_metadata.update(bci_meta)

            enriched.append(
                BlackboardEntry(
                    topic=entry.topic,
                    data=entry.data,
                    source_module=self.MODULE_NAME,
                    confidence=entry.confidence,
                    priority=entry.priority,
                    ttl_seconds=entry.ttl_seconds,
                    tags=entry.tags | frozenset({"bci_enriched"}),
                    parent_id=entry.entry_id,
                    metadata=new_metadata,
                )
            )

        return enriched

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_signal_processed(self) -> Optional[BlackboardEntry]:
        """Get latest ProcessedSignal and return an entry if timestamp changed."""
        if self._signal_processor is None:
            return None

        try:
            processed = self._signal_processor.process_realtime(None)
        except Exception:
            logger.debug("SignalProcessor.process_realtime() failed", exc_info=True)
            return None

        if processed is None:
            return None

        # Change detection: only post if the signal timestamp advanced
        ts = getattr(processed, "timestamp", None)
        if ts is not None and ts == self._last_signal_timestamp:
            return None
        self._last_signal_timestamp = ts

        signal_data: Dict[str, Any] = {
            "timestamp": ts,
            "quality_score": getattr(processed, "quality_score", None),
            "artifacts_detected": getattr(processed, "artifacts_detected", False),
        }

        # Include features if available (may be numpy, so convert)
        features = getattr(processed, "features", None)
        if features is not None:
            try:
                signal_data["features"] = (
                    features.tolist() if hasattr(features, "tolist") else features
                )
            except Exception:
                signal_data["features"] = str(features)

        # Include filtered_data shape info (not the raw data itself — too large)
        filtered = getattr(processed, "filtered_data", None)
        if filtered is not None:
            try:
                signal_data["filtered_shape"] = (
                    list(filtered.shape) if hasattr(filtered, "shape") else len(filtered)
                )
            except Exception:
                pass

        quality = signal_data.get("quality_score", 0.5) or 0.5
        entry = BlackboardEntry(
            topic="bci.signal.processed",
            data=signal_data,
            source_module=self.MODULE_NAME,
            confidence=min(1.0, quality),
            priority=EntryPriority.HIGH if quality > 0.8 else EntryPriority.NORMAL,
            ttl_seconds=self._signal_ttl,
            tags=frozenset({"signal", "processed", "realtime"}),
            metadata={"signal_timestamp": ts},
        )

        return entry

    def _produce_signal_quality(self) -> Optional[BlackboardEntry]:
        """Extract signal quality score and return entry on >5% change."""
        if self._signal_processor is None:
            return None

        try:
            processed = self._signal_processor.process_realtime(None)
        except Exception:
            return None

        if processed is None:
            return None

        quality = getattr(processed, "quality_score", None)
        if quality is None:
            return None

        # Change detection: >5% relative change
        if self._last_quality_score is not None:
            delta = abs(quality - self._last_quality_score)
            if delta < 0.05 and (
                self._last_quality_score == 0
                or delta / max(abs(self._last_quality_score), 1e-9) < 0.05
            ):
                return None

        old_quality = self._last_quality_score
        self._last_quality_score = quality

        quality_data: Dict[str, Any] = {
            "quality_score": quality,
            "previous_score": old_quality,
            "artifacts_detected": getattr(processed, "artifacts_detected", False),
            "timestamp": getattr(processed, "timestamp", time.time()),
        }

        # Determine priority: poor signal quality is CRITICAL
        if quality < 0.3:
            priority = EntryPriority.CRITICAL
        elif quality < 0.6:
            priority = EntryPriority.HIGH
        else:
            priority = EntryPriority.NORMAL

        entry = BlackboardEntry(
            topic="bci.signal.quality",
            data=quality_data,
            source_module=self.MODULE_NAME,
            confidence=0.95,  # We trust quality metrics
            priority=priority,
            ttl_seconds=self._quality_ttl,
            tags=frozenset({"signal", "quality", "metric"}),
            metadata={"quality_score": quality},
        )

        # Emit event for significant quality changes
        direction = "improved" if (old_quality or 0) < quality else "degraded"
        self._emit(
            "bci.signal.quality.changed",
            {
                "quality_score": quality,
                "previous_score": old_quality,
                "direction": direction,
                "entry_id": entry.entry_id,
            },
        )

        return entry

    def _produce_decode_result(self) -> Optional[BlackboardEntry]:
        """Get latest DecodingResult and return entry on class/confidence change."""
        if self._neural_decoder is None or self._signal_processor is None:
            return None

        # Get a processed signal to decode
        try:
            processed = self._signal_processor.process_realtime(None)
        except Exception:
            return None

        if processed is None:
            return None

        try:
            result = self._neural_decoder.decode(processed)
        except Exception:
            logger.debug("NeuralDecoder.decode() failed", exc_info=True)
            return None

        if result is None:
            return None

        decoded_class = getattr(result, "decoded_class", None)
        confidence = getattr(result, "confidence", 0.0)

        # Change detection: new class or >10% confidence shift
        class_changed = decoded_class != self._last_decoded_class
        confidence_changed = (
            self._last_decode_confidence is not None
            and abs(confidence - self._last_decode_confidence) > 0.10
        )
        if not class_changed and not confidence_changed:
            return None

        self._last_decoded_class = decoded_class
        self._last_decode_confidence = confidence

        decode_data: Dict[str, Any] = {
            "decoded_class": decoded_class,
            "confidence": confidence,
            "task": getattr(result, "task", None),
            "latency": getattr(result, "latency", None),
        }

        # Include features_used if available
        features_used = getattr(result, "features_used", None)
        if features_used is not None:
            try:
                decode_data["features_used"] = (
                    features_used.tolist()
                    if hasattr(features_used, "tolist")
                    else features_used
                )
            except Exception:
                decode_data["features_used"] = str(features_used)

        entry = BlackboardEntry(
            topic="bci.decode.result",
            data=decode_data,
            source_module=self.MODULE_NAME,
            confidence=min(1.0, confidence),
            priority=EntryPriority.HIGH if confidence > 0.8 else EntryPriority.NORMAL,
            ttl_seconds=self._decode_ttl,
            tags=frozenset({"decode", "classification", "intent"}),
            metadata={
                "decoded_class": decoded_class,
                "decode_confidence": confidence,
            },
        )

        self._emit(
            "bci.decode.completed",
            {
                "decoded_class": decoded_class,
                "confidence": confidence,
                "entry_id": entry.entry_id,
            },
        )

        return entry

    def _produce_decode_performance(self) -> Optional[BlackboardEntry]:
        """Get performance summary from decoder and return entry on accuracy change."""
        if self._neural_decoder is None:
            return None

        try:
            summary = self._neural_decoder.get_performance_summary(task=None)
        except Exception:
            logger.debug("NeuralDecoder.get_performance_summary() failed", exc_info=True)
            return None

        if summary is None or not isinstance(summary, dict):
            return None

        accuracy = summary.get("accuracy")
        if accuracy is None:
            return None

        # Change detection: >2% accuracy change
        if self._last_accuracy is not None:
            delta = abs(accuracy - self._last_accuracy)
            if delta < 0.02:
                return None

        self._last_accuracy = accuracy

        perf_data: Dict[str, Any] = {
            "accuracy": accuracy,
            "precision": summary.get("precision"),
            "recall": summary.get("recall"),
            "f1": summary.get("f1"),
        }

        entry = BlackboardEntry(
            topic="bci.decode.performance",
            data=perf_data,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._performance_ttl,
            tags=frozenset({"decode", "performance", "metric"}),
            metadata={"accuracy": accuracy},
        )

        return entry

    def _produce_session_status(self) -> Optional[BlackboardEntry]:
        """Get system status from BCIManager and return entry on change."""
        if self._bci_manager is None:
            return None

        try:
            status = self._bci_manager.get_system_status()
        except Exception:
            logger.debug("BCIManager.get_system_status() failed", exc_info=True)
            return None

        if status is None or not isinstance(status, dict):
            return None

        # Change detection: active sessions count changed
        active_sessions = status.get("active_sessions")
        if isinstance(active_sessions, (list, set)):
            active_count = len(active_sessions)
        elif isinstance(active_sessions, (int, float)):
            active_count = int(active_sessions)
        else:
            active_count = 0

        if active_count == self._last_active_sessions:
            return None

        old_count = self._last_active_sessions
        self._last_active_sessions = active_count

        session_data: Dict[str, Any] = {
            "active_sessions": active_count,
            "device_status": status.get("device_status"),
            "processing_state": status.get("processing_state"),
        }

        # Include any additional status fields
        for key in ("uptime", "error_count", "total_sessions"):
            if key in status:
                session_data[key] = status[key]

        # Session changes are noteworthy
        entry = BlackboardEntry(
            topic="bci.session.status",
            data=session_data,
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=(
                EntryPriority.HIGH
                if active_count == 0 and (old_count or 0) > 0
                else EntryPriority.NORMAL
            ),
            ttl_seconds=self._session_ttl,
            tags=frozenset({"session", "status", "device"}),
            metadata={"active_sessions": active_count},
        )

        self._emit(
            "bci.session.state.changed",
            {
                "active_sessions": active_count,
                "previous_count": old_count,
                "entry_id": entry.entry_id,
            },
        )

        return entry

    def _produce_calibration(self) -> Optional[BlackboardEntry]:
        """Track calibration events and return entry on new calibration."""
        if self._bci_manager is None:
            return None

        try:
            status = self._bci_manager.get_system_status()
        except Exception:
            return None

        if status is None or not isinstance(status, dict):
            return None

        # Look for a calibration timestamp in the status
        cal_ts = status.get("last_calibration_timestamp")
        if cal_ts is None:
            # Try alternative keys
            cal_ts = status.get("calibration_timestamp")
            if cal_ts is None:
                return None

        # Change detection: new calibration timestamp
        if cal_ts == self._last_calibration_timestamp:
            return None

        self._last_calibration_timestamp = cal_ts

        cal_data: Dict[str, Any] = {
            "calibration_timestamp": cal_ts,
            "calibration_accuracy": status.get("calibration_accuracy"),
            "calibration_task": status.get("calibration_task"),
        }

        # Try to get more detailed calibration results
        try:
            cal_result = self._bci_manager.calibrate(
                task_type=None, duration=0, trials=0
            )
            if isinstance(cal_result, dict):
                cal_data.update(cal_result)
        except Exception:
            pass  # Calibration info is best-effort

        entry = BlackboardEntry(
            topic="bci.calibration.result",
            data=cal_data,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.HIGH,
            ttl_seconds=self._calibration_ttl,
            tags=frozenset({"calibration", "session", "performance"}),
            metadata={"calibration_timestamp": cal_ts},
        )

        self._emit(
            "bci.calibration.completed",
            {
                "calibration_timestamp": cal_ts,
                "entry_id": entry.entry_id,
            },
        )

        return entry

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Map consciousness state to BCI neurofeedback parameters.

        Phi values modulate feedback gain.  State changes adjust processing mode.
        Broadcast events can trigger BCI session reconfiguration.
        """
        data = entry.data if isinstance(entry.data, dict) else {}

        # Phi-driven neurofeedback
        phi = data.get("phi")
        if phi is not None:
            try:
                phi_val = float(phi)
                # Scale feedback gain: higher Φ → stronger feedback signal
                self._neurofeedback_params["phi_target"] = phi_val
                self._neurofeedback_params["feedback_gain"] = min(2.0, phi_val / 3.0)
            except (TypeError, ValueError):
                pass

        # State-driven mode adjustment
        state_name = data.get("state", data.get("consciousness_state"))
        if state_name is not None:
            self._neurofeedback_params["mode"] = str(state_name)

        # If we have a signal processor, push neurofeedback parameters to it
        if self._signal_processor is not None and hasattr(
            self._signal_processor, "set_neurofeedback_params"
        ):
            try:
                self._signal_processor.set_neurofeedback_params(
                    self._neurofeedback_params
                )
            except Exception:
                logger.debug(
                    "Failed to set neurofeedback params on signal processor",
                    exc_info=True,
                )

    def _consume_neuromorphic(self, entry: BlackboardEntry) -> None:
        """Cross-modal analysis: correlate spike data with BCI signals.

        Neuromorphic spike trains provide an alternative neural encoding
        that can improve decoding accuracy when fused with traditional
        BCI features.
        """
        if self._neural_decoder is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        # Extract spike features for cross-modal fusion
        spike_data = data.get("spike_train", data.get("spikes"))
        if spike_data is None:
            return

        # If the decoder supports cross-modal input, inject spike data
        if hasattr(self._neural_decoder, "inject_auxiliary_features"):
            try:
                self._neural_decoder.inject_auxiliary_features(
                    source="neuromorphic",
                    features=spike_data,
                    timestamp=entry.timestamp,
                )
            except Exception:
                logger.debug(
                    "Failed to inject neuromorphic features into decoder",
                    exc_info=True,
                )

    def _consume_holographic(self, entry: BlackboardEntry) -> None:
        """Process holographic display state for BCI-controlled rendering.

        The holographic module provides display state that the BCI system
        uses to close the loop: decoded intent → display update → visual
        evoked potential → better decoding.
        """
        if self._bci_manager is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        # Extract render state for feedback loop
        render_state = data.get("render_state", data.get("display_state"))
        if render_state is None:
            return

        # If the manager supports display feedback, update it
        if hasattr(self._bci_manager, "update_display_feedback"):
            try:
                self._bci_manager.update_display_feedback(
                    render_state=render_state,
                    timestamp=entry.timestamp,
                )
            except Exception:
                logger.debug(
                    "Failed to update display feedback on BCI manager",
                    exc_info=True,
                )

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_consciousness_event(self, event: CognitiveEvent) -> None:
        """Update neurofeedback parameters based on consciousness events."""
        payload = event.payload or {}

        if "phi" in payload:
            try:
                phi_val = float(payload["phi"])
                self._neurofeedback_params["phi_target"] = phi_val
                self._neurofeedback_params["feedback_gain"] = min(2.0, phi_val / 3.0)
            except (TypeError, ValueError):
                pass

        if "new_state" in payload:
            self._neurofeedback_params["mode"] = str(payload["new_state"])

    def _handle_neuromorphic_event(self, event: CognitiveEvent) -> None:
        """Correlate neuromorphic spike events with BCI processing.

        Real-time spike events can trigger immediate BCI processing
        adjustments for latency-critical applications.
        """
        if self._signal_processor is None:
            return

        payload = event.payload or {}
        spike_rate = payload.get("spike_rate", payload.get("firing_rate"))

        if spike_rate is not None and hasattr(
            self._signal_processor, "adjust_sensitivity"
        ):
            try:
                # High spike rates suggest more neural activity →
                # increase processing sensitivity
                self._signal_processor.adjust_sensitivity(
                    factor=min(2.0, 1.0 + float(spike_rate) / 100.0)
                )
            except Exception:
                logger.debug(
                    "Failed to adjust signal processor sensitivity",
                    exc_info=True,
                )

    def _handle_holographic_event(self, event: CognitiveEvent) -> None:
        """Update BCI display control parameters from holographic events.

        Holographic render completion events allow the BCI to synchronize
        stimulus presentation with signal acquisition windows.
        """
        if self._bci_manager is None:
            return

        payload = event.payload or {}
        render_complete = payload.get("render_complete", False)

        if render_complete and hasattr(self._bci_manager, "sync_stimulus_window"):
            try:
                self._bci_manager.sync_stimulus_window(
                    timestamp=event.timestamp,
                )
            except Exception:
                logger.debug(
                    "Failed to sync BCI stimulus window",
                    exc_info=True,
                )

    # ── Internal helpers ──────────────────────────────────────────────

    def _get_current_quality(self) -> Optional[float]:
        """Return the latest signal quality score, or None."""
        if self._signal_processor is None:
            return self._last_quality_score

        try:
            processed = self._signal_processor.process_realtime(None)
            if processed is not None:
                return getattr(processed, "quality_score", None)
        except Exception:
            pass

        return self._last_quality_score

    def _get_current_artifacts(self) -> Optional[bool]:
        """Return whether artifacts are currently detected, or None."""
        if self._signal_processor is None:
            return None

        try:
            processed = self._signal_processor.process_realtime(None)
            if processed is not None:
                return getattr(processed, "artifacts_detected", None)
        except Exception:
            pass

        return None

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all BCI components.

        Useful for debugging and dashboard display.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_bci_manager": self._bci_manager is not None,
            "has_signal_processor": self._signal_processor is not None,
            "has_neural_decoder": self._neural_decoder is not None,
            "last_signal_timestamp": self._last_signal_timestamp,
            "last_quality_score": self._last_quality_score,
            "last_decoded_class": self._last_decoded_class,
            "last_decode_confidence": self._last_decode_confidence,
            "last_accuracy": self._last_accuracy,
            "last_active_sessions": self._last_active_sessions,
            "last_calibration_timestamp": self._last_calibration_timestamp,
            "neurofeedback_params": dict(self._neurofeedback_params),
            "registered": self._blackboard is not None,
        }

        # Live status from BCIManager
        if self._bci_manager is not None:
            try:
                status = self._bci_manager.get_system_status()
                if isinstance(status, dict):
                    snap["system_status"] = status
            except Exception:
                snap["system_status"] = None

        # Live quality from SignalProcessor
        if self._signal_processor is not None:
            try:
                processed = self._signal_processor.process_realtime(None)
                if processed is not None:
                    snap["current_quality"] = getattr(
                        processed, "quality_score", None
                    )
                    snap["artifacts_detected"] = getattr(
                        processed, "artifacts_detected", None
                    )
            except Exception:
                snap["current_quality"] = None

        # Performance from NeuralDecoder
        if self._neural_decoder is not None:
            try:
                perf = self._neural_decoder.get_performance_summary(task=None)
                if isinstance(perf, dict):
                    snap["decoder_performance"] = perf
            except Exception:
                snap["decoder_performance"] = None

        return snap
