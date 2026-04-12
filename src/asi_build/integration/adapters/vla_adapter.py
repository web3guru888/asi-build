"""
VLA++ ↔ Blackboard Adapter
==============================

Bridges the VLA++ optimization module (``VLAPlusPlus``, ``VLATrainer``,
``VLAOptimizationPipeline``) with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``vla.training_progress``      — Training epoch/step metrics (loss, accuracy)
- ``vla.model_metrics``          — Model size, parameter count, latency
- ``vla.optimization_status``    — Optimization pipeline status (quantization, pruning, distillation)

Topics consumed
~~~~~~~~~~~~~~~
- ``compute``                    — Compute resource availability → adjust batch size
- ``distributed_training``       — Federated updates → incorporate into VLA model
- ``consciousness``              — Consciousness state → attention weighting for VLA

Events emitted
~~~~~~~~~~~~~~
- ``vla.training.epoch_complete``   — An epoch of VLA training completed
- ``vla.optimization.improved``     — Optimization pipeline achieved an improvement

Events listened
~~~~~~~~~~~~~~~
- ``compute.resource.exhausted``    — Reduce batch size / pause training
- ``distributed_training.round.completed`` — Merge federated updates

.. note::

    This is a PyTorch module.  The lazy import handles torch being absent
    gracefully — all operations degrade to no-ops if torch/the VLA module
    is not installed.
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

_optimization_module = None


def _get_optimization():
    """Lazy import of optimization module to allow graceful degradation.

    This module depends on PyTorch, which may not be installed.
    """
    global _optimization_module
    if _optimization_module is None:
        try:
            from asi_build import optimization as _om

            _optimization_module = _om
        except (ImportError, ModuleNotFoundError):
            _optimization_module = False
    return _optimization_module if _optimization_module is not False else None


class VLABlackboardAdapter:
    """Adapter connecting the VLA++ optimization module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``VLAPlusPlus`` — the VLA++ multi-modal model (Vision-Language-Action)
    - ``VLATrainer`` — training loop with LoRA fine-tuning support
    - ``VLAOptimizationPipeline`` — model optimization (quantization, pruning, distillation)

    If a component is ``None`` (or if PyTorch is unavailable), the adapter
    gracefully skips operations involving that component.

    Parameters
    ----------
    model : optional
        A ``VLAPlusPlus`` model instance.
    trainer : optional
        A ``VLATrainer`` instance.
    optimization_pipeline : optional
        A ``VLAOptimizationPipeline`` instance.
    training_progress_ttl : float
        TTL in seconds for training progress entries (default 60).
    model_metrics_ttl : float
        TTL for model metrics entries (default 300).
    optimization_status_ttl : float
        TTL for optimization status entries (default 300).
    """

    MODULE_NAME = "vla"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        model: Any = None,
        trainer: Any = None,
        optimization_pipeline: Any = None,
        *,
        training_progress_ttl: float = 60.0,
        model_metrics_ttl: float = 300.0,
        optimization_status_ttl: float = 300.0,
    ) -> None:
        self._model = model
        self._trainer = trainer
        self._optimization_pipeline = optimization_pipeline
        self._training_progress_ttl = training_progress_ttl
        self._model_metrics_ttl = model_metrics_ttl
        self._optimization_status_ttl = optimization_status_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change detection
        self._last_epoch: int = -1
        self._last_step: int = -1
        self._last_train_loss: Optional[float] = None
        self._last_val_loss: Optional[float] = None
        self._last_param_count: Optional[int] = None
        self._last_model_size: Optional[float] = None
        self._last_optimization_result: Optional[str] = None
        self._best_val_loss: float = float("inf")

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
                "VLA++ multi-modal model: training progress, model metrics, "
                "and optimization pipeline (quantization, pruning, distillation)."
            ),
            topics_produced=frozenset(
                {
                    "vla.training_progress",
                    "vla.model_metrics",
                    "vla.optimization_status",
                }
            ),
            topics_consumed=frozenset(
                {
                    "compute",
                    "distributed_training",
                    "consciousness",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "VLABlackboardAdapter registered with blackboard "
            "(model=%s, trainer=%s, pipeline=%s)",
            self._model is not None,
            self._trainer is not None,
            self._optimization_pipeline is not None,
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
            elif event.event_type.startswith("consciousness."):
                self._handle_consciousness_event(event)
        except Exception:
            logger.debug(
                "VLABlackboardAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current VLA++ state."""
        entries: List[BlackboardEntry] = []

        with self._lock:
            training_entry = self._produce_training_progress()
            if training_entry is not None:
                entries.append(training_entry)

            metrics_entry = self._produce_model_metrics()
            if metrics_entry is not None:
                entries.append(metrics_entry)

            opt_entry = self._produce_optimization_status()
            if opt_entry is not None:
                entries.append(opt_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        Compute resource updates → adjust batch size.
        Training round updates → incorporate federated updates.
        Consciousness state → attention weighting.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("compute."):
                    self._consume_compute(entry)
                elif entry.topic.startswith("distributed_training."):
                    self._consume_training(entry)
                elif entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
            except Exception:
                logger.debug(
                    "VLABlackboardAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_training_progress(self) -> Optional[BlackboardEntry]:
        """Read training progress from VLATrainer and return entry if epoch changed."""
        if self._trainer is None:
            return None

        progress: Dict[str, Any] = {}
        try:
            progress["current_epoch"] = getattr(self._trainer, "current_epoch",
                                                 getattr(self._trainer, "epoch", -1))
            progress["current_step"] = getattr(self._trainer, "global_step",
                                                getattr(self._trainer, "step", -1))
            progress["train_loss"] = getattr(self._trainer, "train_loss",
                                             getattr(self._trainer, "current_loss", None))
            progress["val_loss"] = getattr(self._trainer, "val_loss",
                                           getattr(self._trainer, "best_val_loss", None))
            progress["learning_rate"] = getattr(self._trainer, "learning_rate",
                                                getattr(self._trainer, "lr", None))
            progress["is_training"] = getattr(self._trainer, "is_training", False)
        except Exception:
            logger.debug("VLATrainer progress read failed", exc_info=True)
            return None

        epoch = progress.get("current_epoch", -1)
        step = progress.get("current_step", -1)
        train_loss = progress.get("train_loss")

        # Change detection: only post if epoch or step changed
        if epoch == self._last_epoch and step == self._last_step:
            return None

        epoch_changed = epoch != self._last_epoch
        self._last_epoch = epoch
        self._last_step = step
        self._last_train_loss = train_loss

        # Track best val loss
        val_loss = progress.get("val_loss")
        val_improved = False
        if val_loss is not None and isinstance(val_loss, (int, float)):
            if val_loss < self._best_val_loss:
                self._best_val_loss = val_loss
                val_improved = True
            progress["best_val_loss"] = self._best_val_loss

        priority = EntryPriority.NORMAL
        if epoch_changed:
            priority = EntryPriority.HIGH

        entry = BlackboardEntry(
            topic="vla.training_progress",
            data=progress,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=priority,
            ttl_seconds=self._training_progress_ttl,
            tags=frozenset({"vla", "training", "progress", "epoch"}),
            metadata={
                "epoch": epoch,
                "step": step,
                "train_loss": train_loss,
            },
        )

        if epoch_changed and epoch >= 0:
            self._emit(
                "vla.training.epoch_complete",
                {
                    "epoch": epoch,
                    "train_loss": train_loss,
                    "val_loss": val_loss,
                    "val_improved": val_improved,
                    "entry_id": entry.entry_id,
                },
            )

        return entry

    def _produce_model_metrics(self) -> Optional[BlackboardEntry]:
        """Capture model metrics (parameter count, size, etc.)."""
        if self._model is None:
            return None

        metrics: Dict[str, Any] = {}

        # Parameter count
        try:
            count_fn = getattr(self._model, "count_parameters", None)
            if count_fn is not None:
                param_count = count_fn()
            else:
                # Fallback: try PyTorch parameters()
                params = getattr(self._model, "parameters", None)
                if params is not None and callable(params):
                    param_count = sum(p.numel() for p in params() if getattr(p, "requires_grad", True))
                else:
                    param_count = None
            metrics["parameter_count"] = param_count
        except Exception:
            param_count = None

        # Model size (via optimization pipeline or estimation)
        model_size = None
        if self._optimization_pipeline is not None:
            try:
                size_fn = getattr(self._optimization_pipeline, "get_model_size", None)
                if size_fn is not None:
                    model_size = size_fn(self._model)
                    metrics["model_size_mb"] = model_size
            except Exception:
                pass

        # Training mode
        try:
            metrics["training"] = getattr(self._model, "training", None)
        except Exception:
            pass

        # Gradient checkpointing
        try:
            metrics["gradient_checkpointing"] = getattr(
                self._model, "_gradient_checkpointing", False
            )
        except Exception:
            pass

        if not metrics:
            return None

        # Change detection: only post if param count or size changed
        if param_count == self._last_param_count and model_size == self._last_model_size:
            return None
        self._last_param_count = param_count
        self._last_model_size = model_size

        return BlackboardEntry(
            topic="vla.model_metrics",
            data=metrics,
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._model_metrics_ttl,
            tags=frozenset({"vla", "model", "metrics", "parameters"}),
            metadata={
                "parameter_count": param_count,
                "model_size_mb": model_size,
            },
        )

    def _produce_optimization_status(self) -> Optional[BlackboardEntry]:
        """Capture optimization pipeline status."""
        if self._optimization_pipeline is None:
            return None

        status: Dict[str, Any] = {}

        try:
            # Check quantizer state
            quantizer = getattr(self._optimization_pipeline, "quantizer", None)
            if quantizer is not None:
                status["quantizer_enabled"] = True
                status["quantization_type"] = getattr(quantizer, "config", {})
                if hasattr(status["quantization_type"], "quantization_bits"):
                    status["quantization_bits"] = status["quantization_type"].quantization_bits
            else:
                status["quantizer_enabled"] = False
        except Exception:
            pass

        try:
            # Check pruner state
            pruner = getattr(self._optimization_pipeline, "pruner", None)
            if pruner is not None:
                status["pruner_enabled"] = True
                pruner_config = getattr(pruner, "config", None)
                if pruner_config is not None:
                    status["pruning_ratio"] = getattr(pruner_config, "pruning_ratio", None)
            else:
                status["pruner_enabled"] = False
        except Exception:
            pass

        try:
            # Check distiller state
            distiller = getattr(self._optimization_pipeline, "distiller", None)
            status["distiller_enabled"] = distiller is not None
        except Exception:
            pass

        if not status:
            return None

        # Simple string-based change detection
        status_key = str(sorted(status.items()))
        if status_key == self._last_optimization_result:
            return None
        self._last_optimization_result = status_key

        return BlackboardEntry(
            topic="vla.optimization_status",
            data=status,
            source_module=self.MODULE_NAME,
            confidence=0.85,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._optimization_status_ttl,
            tags=frozenset({"vla", "optimization", "quantization", "pruning"}),
        )

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_compute(self, entry: BlackboardEntry) -> None:
        """Adjust training based on compute resource availability."""
        if self._trainer is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        max_util = data.get("max_utilization", None)

        # If GPU utilization is high, try to reduce batch size
        if max_util is not None and isinstance(max_util, (int, float)) and max_util > 0.9:
            config = getattr(self._trainer, "config", None)
            if config is not None:
                current_batch = getattr(config, "batch_size", None)
                if current_batch is not None and isinstance(current_batch, int) and current_batch > 1:
                    try:
                        config.batch_size = max(1, current_batch // 2)
                        logger.info(
                            "VLA: reduced batch_size from %d to %d due to resource pressure",
                            current_batch, config.batch_size,
                        )
                    except (AttributeError, Exception):
                        pass

    def _consume_training(self, entry: BlackboardEntry) -> None:
        """Incorporate federated training updates into VLA model."""
        if self._model is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        # If there are aggregated gradients, they could be applied
        aggregated = data.get("aggregated_model", data.get("aggregated_weights", None))
        if aggregated is not None and hasattr(self._model, "load_state_dict"):
            # In practice, this requires careful handling — log intent
            logger.debug(
                "VLA: received federated update (entry=%s), integration pending",
                entry.entry_id,
            )

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Modulate VLA attention weights based on consciousness state."""
        if self._model is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        phi = data.get("phi", data.get("phi_value", None))
        if phi is not None:
            # Store as model metadata for potential use in forward pass
            try:
                if not hasattr(self._model, "_blackboard_metadata"):
                    self._model._blackboard_metadata = {}
                self._model._blackboard_metadata["consciousness_phi"] = float(phi)
            except (AttributeError, Exception):
                pass

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_compute_event(self, event: CognitiveEvent) -> None:
        """React to compute resource exhaustion — reduce training load."""
        if self._trainer is None:
            return
        if event.event_type == "compute.resource.exhausted":
            # Signal trainer to pause or reduce intensity
            if hasattr(self._trainer, "config"):
                config = self._trainer.config
                if hasattr(config, "gradient_accumulation_steps"):
                    try:
                        config.gradient_accumulation_steps = max(
                            1,
                            getattr(config, "gradient_accumulation_steps", 1) * 2,
                        )
                    except (AttributeError, Exception):
                        pass

    def _handle_training_event(self, event: CognitiveEvent) -> None:
        """React to distributed training round completion."""
        payload = event.payload or {}
        round_id = payload.get("round_id")
        if round_id:
            logger.debug("VLA: distributed training round %s completed", round_id)

    def _handle_consciousness_event(self, event: CognitiveEvent) -> None:
        """Modulate training based on consciousness state changes."""
        if self._trainer is None:
            return
        payload = event.payload or {}
        new_state = payload.get("new_state", "")
        # Could modulate learning rate based on consciousness state
        if new_state and hasattr(self._trainer, "config"):
            try:
                if not hasattr(self._trainer.config, "_consciousness_state"):
                    pass
                self._trainer.config._consciousness_state = str(new_state)
            except (AttributeError, Exception):
                pass

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all VLA++ components."""
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_model": self._model is not None,
            "has_trainer": self._trainer is not None,
            "has_optimization_pipeline": self._optimization_pipeline is not None,
            "last_epoch": self._last_epoch,
            "last_step": self._last_step,
            "last_train_loss": self._last_train_loss,
            "best_val_loss": self._best_val_loss if self._best_val_loss < float("inf") else None,
            "last_param_count": self._last_param_count,
            "last_model_size": self._last_model_size,
            "registered": self._blackboard is not None,
        }

        if self._model is not None:
            try:
                count_fn = getattr(self._model, "count_parameters", None)
                if count_fn is not None:
                    snap["current_param_count"] = count_fn()
                snap["model_training"] = getattr(self._model, "training", None)
            except Exception:
                pass

        if self._trainer is not None:
            try:
                snap["trainer_active"] = getattr(self._trainer, "is_training", False)
                snap["current_lr"] = getattr(self._trainer, "learning_rate",
                                             getattr(self._trainer, "lr", None))
            except Exception:
                pass

        return snap
