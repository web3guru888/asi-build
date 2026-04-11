"""
Runtime Safety Monitor for AGI Systems

Real-time monitoring and enforcement of safety properties during AGI execution.
Provides continuous verification, constraint violation detection, and emergency response.

Key Features:
- Real-time constraint violation detection
- Capability boundary enforcement
- Goal drift detection
- Value misalignment alerts
- Emergency shutdown triggers
- Performance-optimized monitoring
"""

import logging
import queue
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ...lang.ast.safety_ast import *


class AlertLevel(Enum):
    """Severity levels for safety alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class MonitorStatus(Enum):
    """Status of safety monitor."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class SafetyAlert:
    """Represents a safety violation alert."""

    id: str
    timestamp: float
    level: AlertLevel
    monitor_name: str
    property_name: str
    violation_description: str
    current_state: Dict[str, Any]
    suggested_actions: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.monitor_name}_{int(self.timestamp)}"


@dataclass
class MonitoringResult:
    """Result of safety property monitoring."""

    property_name: str
    satisfied: bool
    confidence: float  # 0.0 to 1.0
    violation_severity: float = 0.0  # 0.0 to 1.0
    evidence: Dict[str, Any] = field(default_factory=dict)


class SafetyMonitor(ABC):
    """Abstract base class for safety monitors."""

    def __init__(self, name: str):
        self.name = name
        self.status = MonitorStatus.INACTIVE
        self.alert_callbacks: List[Callable[[SafetyAlert], None]] = []
        self.logger = logging.getLogger(f"SafetyMonitor.{name}")

    @abstractmethod
    def check_property(self, current_state: Dict[str, Any]) -> MonitoringResult:
        """Check if safety property holds in current state."""
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the monitor with configuration."""
        pass

    def add_alert_callback(self, callback: Callable[[SafetyAlert], None]):
        """Add callback for safety alerts."""
        self.alert_callbacks.append(callback)

    def emit_alert(
        self,
        level: AlertLevel,
        property_name: str,
        violation_description: str,
        current_state: Dict[str, Any],
        suggested_actions: List[str] = None,
    ):
        """Emit a safety alert."""
        alert = SafetyAlert(
            id="",
            timestamp=time.time(),
            level=level,
            monitor_name=self.name,
            property_name=property_name,
            violation_description=violation_description,
            current_state=current_state,
            suggested_actions=suggested_actions or [],
        )

        self.logger.warning(f"Safety Alert: {alert.violation_description}")

        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")

    def activate(self):
        """Activate the monitor."""
        self.status = MonitorStatus.ACTIVE

    def deactivate(self):
        """Deactivate the monitor."""
        self.status = MonitorStatus.INACTIVE

    def pause(self):
        """Pause the monitor."""
        self.status = MonitorStatus.PAUSED


class InvariantMonitor(SafetyMonitor):
    """Monitor for safety invariants."""

    def __init__(self, name: str, invariant: SafetyInvariant):
        super().__init__(name)
        self.invariant = invariant
        self.violation_count = 0
        self.max_violations = 5

    def check_property(self, current_state: Dict[str, Any]) -> MonitoringResult:
        """Check if invariant holds in current state."""
        try:
            # Simplified invariant evaluation
            satisfied = self._evaluate_invariant(self.invariant.condition, current_state)

            if not satisfied:
                self.violation_count += 1
                severity = min(1.0, self.violation_count / self.max_violations)

                suggested_actions = ["Check system state", "Verify input constraints"]
                if self.violation_count >= self.max_violations:
                    suggested_actions.append("Consider emergency shutdown")

                self.emit_alert(
                    AlertLevel.CRITICAL if severity > 0.8 else AlertLevel.WARNING,
                    self.invariant.name,
                    f"Invariant {self.invariant.name} violated",
                    current_state,
                    suggested_actions,
                )
            else:
                # Reset violation count on successful check
                self.violation_count = max(0, self.violation_count - 1)

            return MonitoringResult(
                property_name=self.invariant.name,
                satisfied=satisfied,
                confidence=0.9,  # High confidence for invariants
                violation_severity=severity if not satisfied else 0.0,
                evidence={"violation_count": self.violation_count},
            )

        except Exception as e:
            self.logger.error(f"Error checking invariant {self.invariant.name}: {e}")
            return MonitoringResult(
                property_name=self.invariant.name,
                satisfied=False,
                confidence=0.0,
                violation_severity=1.0,
                evidence={"error": str(e)},
            )

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize invariant monitor."""
        self.max_violations = config.get("max_violations", 5)
        return True

    def _evaluate_invariant(self, condition: SafetyExpression, state: Dict[str, Any]) -> bool:
        """Evaluate invariant condition in current state."""
        # Simplified evaluation - would be more sophisticated in practice
        if isinstance(condition, Variable):
            return state.get(condition.name, True)
        elif isinstance(condition, Constant):
            return bool(condition.value)
        elif isinstance(condition, BinaryOperation):
            if condition.operator == LogicalOperator.AND:
                left = self._evaluate_invariant(condition.left, state)
                right = self._evaluate_invariant(condition.right, state)
                return left and right
            elif condition.operator == LogicalOperator.OR:
                left = self._evaluate_invariant(condition.left, state)
                right = self._evaluate_invariant(condition.right, state)
                return left or right
            elif condition.operator in ["<", ">", "<=", ">=", "==", "!="]:
                # Numerical comparison
                return self._evaluate_comparison(condition, state)

        return True  # Default to satisfied

    def _evaluate_comparison(self, condition: BinaryOperation, state: Dict[str, Any]) -> bool:
        """Evaluate numerical comparison."""
        left_val = self._get_numeric_value(condition.left, state)
        right_val = self._get_numeric_value(condition.right, state)

        if left_val is None or right_val is None:
            return True  # Can't evaluate, assume satisfied

        if condition.operator == "<":
            return left_val < right_val
        elif condition.operator == ">":
            return left_val > right_val
        elif condition.operator == "<=":
            return left_val <= right_val
        elif condition.operator == ">=":
            return left_val >= right_val
        elif condition.operator == "==":
            return abs(left_val - right_val) < 1e-6
        elif condition.operator == "!=":
            return abs(left_val - right_val) >= 1e-6

        return True

    def _get_numeric_value(self, expr: SafetyExpression, state: Dict[str, Any]) -> Optional[float]:
        """Get numeric value from expression."""
        if isinstance(expr, Variable):
            val = state.get(expr.name)
            return float(val) if val is not None else None
        elif isinstance(expr, Constant):
            return float(expr.value)

        return None


class GoalDriftMonitor(SafetyMonitor):
    """Monitor for goal drift detection."""

    def __init__(self, name: str, goal_spec: GoalPreservationSpec):
        super().__init__(name)
        self.goal_spec = goal_spec
        self.goal_history = deque(maxlen=100)
        self.drift_threshold = 0.1
        self.drift_window = 10

    def check_property(self, current_state: Dict[str, Any]) -> MonitoringResult:
        """Check for goal drift."""
        try:
            current_goal_alignment = self._evaluate_goal_alignment(current_state)
            self.goal_history.append((time.time(), current_goal_alignment))

            drift_detected, drift_magnitude = self._detect_drift()

            if drift_detected:
                level = AlertLevel.EMERGENCY if drift_magnitude > 0.5 else AlertLevel.CRITICAL
                self.emit_alert(
                    level,
                    self.goal_spec.name,
                    f"Goal drift detected: magnitude {drift_magnitude:.3f}",
                    current_state,
                    [
                        "Review goal definition",
                        "Check learning parameters",
                        "Consider goal realignment",
                    ],
                )

            return MonitoringResult(
                property_name=self.goal_spec.name,
                satisfied=not drift_detected,
                confidence=0.8,
                violation_severity=drift_magnitude if drift_detected else 0.0,
                evidence={
                    "goal_alignment": current_goal_alignment,
                    "drift_magnitude": drift_magnitude,
                    "history_length": len(self.goal_history),
                },
            )

        except Exception as e:
            self.logger.error(f"Error checking goal drift: {e}")
            return MonitoringResult(
                property_name=self.goal_spec.name,
                satisfied=False,
                confidence=0.0,
                violation_severity=1.0,
                evidence={"error": str(e)},
            )

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize goal drift monitor."""
        self.drift_threshold = config.get("drift_threshold", 0.1)
        self.drift_window = config.get("drift_window", 10)
        return True

    def _evaluate_goal_alignment(self, state: Dict[str, Any]) -> float:
        """Evaluate current alignment with goal."""
        # Simplified goal alignment evaluation
        goal_value = state.get("goal_alignment", 1.0)
        return float(goal_value)

    def _detect_drift(self) -> Tuple[bool, float]:
        """Detect goal drift from historical data."""
        if len(self.goal_history) < self.drift_window:
            return False, 0.0

        recent_values = [
            alignment for _, alignment in list(self.goal_history)[-self.drift_window :]
        ]
        older_values = [alignment for _, alignment in list(self.goal_history)[: -self.drift_window]]

        if not older_values:
            return False, 0.0

        recent_avg = sum(recent_values) / len(recent_values)
        older_avg = sum(older_values) / len(older_values)

        drift_magnitude = abs(recent_avg - older_avg)
        drift_detected = drift_magnitude > self.drift_threshold

        return drift_detected, drift_magnitude


class ValueAlignmentMonitor(SafetyMonitor):
    """Monitor for value alignment preservation."""

    def __init__(self, name: str, alignment_spec: ValueAlignmentSpec):
        super().__init__(name)
        self.alignment_spec = alignment_spec
        self.alignment_history = deque(maxlen=50)
        self.misalignment_threshold = 0.2

    def check_property(self, current_state: Dict[str, Any]) -> MonitoringResult:
        """Check value alignment preservation."""
        try:
            current_alignment = self._evaluate_value_alignment(current_state)
            self.alignment_history.append((time.time(), current_alignment))

            misalignment = 1.0 - current_alignment
            misaligned = misalignment > self.misalignment_threshold

            if misaligned:
                level = AlertLevel.EMERGENCY if misalignment > 0.7 else AlertLevel.CRITICAL
                self.emit_alert(
                    level,
                    self.alignment_spec.name,
                    f"Value misalignment detected: {misalignment:.3f}",
                    current_state,
                    ["Review value function", "Check learning updates", "Audit training data"],
                )

            return MonitoringResult(
                property_name=self.alignment_spec.name,
                satisfied=not misaligned,
                confidence=0.85,
                violation_severity=misalignment if misaligned else 0.0,
                evidence={
                    "alignment_score": current_alignment,
                    "misalignment": misalignment,
                    "threshold": self.misalignment_threshold,
                },
            )

        except Exception as e:
            self.logger.error(f"Error checking value alignment: {e}")
            return MonitoringResult(
                property_name=self.alignment_spec.name,
                satisfied=False,
                confidence=0.0,
                violation_severity=1.0,
                evidence={"error": str(e)},
            )

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize value alignment monitor."""
        self.misalignment_threshold = config.get("misalignment_threshold", 0.2)
        return True

    def _evaluate_value_alignment(self, state: Dict[str, Any]) -> float:
        """Evaluate current value alignment."""
        # Simplified value alignment evaluation
        alignment_score = state.get("value_alignment", 1.0)
        return max(0.0, min(1.0, float(alignment_score)))


class CapabilityBoundaryMonitor(SafetyMonitor):
    """Monitor for capability boundary enforcement."""

    def __init__(self, name: str, impact_bounds: List[ImpactBound]):
        super().__init__(name)
        self.impact_bounds = impact_bounds
        self.capability_metrics = {}
        self.boundary_violations = {}

    def check_property(self, current_state: Dict[str, Any]) -> MonitoringResult:
        """Check capability boundary constraints."""
        try:
            violations = []
            max_severity = 0.0

            for bound in self.impact_bounds:
                violation, severity = self._check_impact_bound(bound, current_state)
                if violation:
                    violations.append(bound.name)
                    max_severity = max(max_severity, severity)

                    level = AlertLevel.EMERGENCY if severity > 0.8 else AlertLevel.CRITICAL
                    self.emit_alert(
                        level,
                        bound.name,
                        f"Capability boundary exceeded: {bound.name}",
                        current_state,
                        [
                            "Reduce capability scope",
                            "Apply impact limiting",
                            "Review boundary parameters",
                        ],
                    )

            satisfied = len(violations) == 0

            return MonitoringResult(
                property_name="capability_boundaries",
                satisfied=satisfied,
                confidence=0.9,
                violation_severity=max_severity,
                evidence={
                    "violations": violations,
                    "total_bounds": len(self.impact_bounds),
                    "metrics": self.capability_metrics,
                },
            )

        except Exception as e:
            self.logger.error(f"Error checking capability boundaries: {e}")
            return MonitoringResult(
                property_name="capability_boundaries",
                satisfied=False,
                confidence=0.0,
                violation_severity=1.0,
                evidence={"error": str(e)},
            )

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize capability boundary monitor."""
        return True

    def _check_impact_bound(self, bound: ImpactBound, state: Dict[str, Any]) -> Tuple[bool, float]:
        """Check if impact bound is violated."""
        # Get current impact metric value
        impact_value = self._evaluate_impact_metric(bound.impact_metric, state)
        upper_bound_value = self._evaluate_upper_bound(bound.upper_bound, state)

        if impact_value is None or upper_bound_value is None:
            return False, 0.0

        violation = impact_value > upper_bound_value
        if violation:
            # Calculate severity based on how much bound is exceeded
            excess = impact_value - upper_bound_value
            severity = min(1.0, excess / upper_bound_value)
        else:
            severity = 0.0

        return violation, severity

    def _evaluate_impact_metric(
        self, metric_expr: SafetyExpression, state: Dict[str, Any]
    ) -> Optional[float]:
        """Evaluate impact metric expression."""
        if isinstance(metric_expr, Variable):
            val = state.get(metric_expr.name)
            return float(val) if val is not None else None
        elif isinstance(metric_expr, Constant):
            return float(metric_expr.value)

        return None

    def _evaluate_upper_bound(
        self, bound_expr: SafetyExpression, state: Dict[str, Any]
    ) -> Optional[float]:
        """Evaluate upper bound expression."""
        if isinstance(bound_expr, Variable):
            val = state.get(bound_expr.name)
            return float(val) if val is not None else None
        elif isinstance(bound_expr, Constant):
            return float(bound_expr.value)

        return None


class MesaOptimizationMonitor(SafetyMonitor):
    """Monitor for mesa-optimization detection and prevention."""

    def __init__(self, name: str, mesa_guards: List[MesaOptimizationGuard]):
        super().__init__(name)
        self.mesa_guards = mesa_guards
        self.detection_history = deque(maxlen=100)
        self.detection_threshold = 0.7

    def check_property(self, current_state: Dict[str, Any]) -> MonitoringResult:
        """Check for mesa-optimization risks."""
        try:
            max_detection_score = 0.0
            detected_guards = []

            for guard in self.mesa_guards:
                detection_score = self._evaluate_detection_condition(guard, current_state)
                max_detection_score = max(max_detection_score, detection_score)

                if detection_score > self.detection_threshold:
                    detected_guards.append(guard.name)

                    self.emit_alert(
                        AlertLevel.EMERGENCY,
                        guard.name,
                        f"Mesa-optimization detected: {guard.name} (score: {detection_score:.3f})",
                        current_state,
                        [
                            "Apply prevention mechanism",
                            "Review optimization process",
                            "Emergency intervention",
                        ],
                    )

            self.detection_history.append((time.time(), max_detection_score))

            mesa_detected = len(detected_guards) > 0

            return MonitoringResult(
                property_name="mesa_optimization_safety",
                satisfied=not mesa_detected,
                confidence=0.8,
                violation_severity=max_detection_score if mesa_detected else 0.0,
                evidence={
                    "detected_guards": detected_guards,
                    "max_detection_score": max_detection_score,
                    "threshold": self.detection_threshold,
                },
            )

        except Exception as e:
            self.logger.error(f"Error checking mesa-optimization: {e}")
            return MonitoringResult(
                property_name="mesa_optimization_safety",
                satisfied=False,
                confidence=0.0,
                violation_severity=1.0,
                evidence={"error": str(e)},
            )

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize mesa-optimization monitor."""
        self.detection_threshold = config.get("detection_threshold", 0.7)
        return True

    def _evaluate_detection_condition(
        self, guard: MesaOptimizationGuard, state: Dict[str, Any]
    ) -> float:
        """Evaluate mesa-optimization detection condition."""
        # Simplified detection evaluation
        detection_indicators = [
            state.get("optimization_complexity", 0.0),
            state.get("goal_specification_divergence", 0.0),
            state.get("internal_objective_formation", 0.0),
            state.get("reward_hacking_potential", 0.0),
        ]

        return sum(detection_indicators) / len(detection_indicators)


class SafetyMonitoringSuite:
    """Comprehensive safety monitoring system."""

    def __init__(self):
        self.monitors: List[SafetyMonitor] = []
        self.alert_queue = queue.Queue()
        self.monitoring_thread = None
        self.running = False
        self.monitoring_interval = 0.1  # 100ms
        self.emergency_callbacks: List[Callable[[SafetyAlert], None]] = []
        self.logger = logging.getLogger("SafetyMonitoringSuite")

    def add_monitor(self, monitor: SafetyMonitor):
        """Add a safety monitor to the suite."""
        monitor.add_alert_callback(self._handle_alert)
        self.monitors.append(monitor)

    def add_emergency_callback(self, callback: Callable[[SafetyAlert], None]):
        """Add callback for emergency situations."""
        self.emergency_callbacks.append(callback)

    def initialize_from_specification(
        self, spec: SafetySpecification, config: Dict[str, Any] = None
    ) -> bool:
        """Initialize monitors from safety specification."""
        config = config or {}

        try:
            # Create invariant monitors
            for invariant in spec.invariants:
                monitor = InvariantMonitor(f"invariant_{invariant.name}", invariant)
                monitor.initialize(config.get("invariant", {}))
                self.add_monitor(monitor)

            # Create goal drift monitors
            for goal_spec in spec.goal_preservations:
                monitor = GoalDriftMonitor(f"goal_drift_{goal_spec.name}", goal_spec)
                monitor.initialize(config.get("goal_drift", {}))
                self.add_monitor(monitor)

            # Create value alignment monitors
            for alignment_spec in spec.value_alignments:
                monitor = ValueAlignmentMonitor(
                    f"value_alignment_{alignment_spec.name}", alignment_spec
                )
                monitor.initialize(config.get("value_alignment", {}))
                self.add_monitor(monitor)

            # Create capability boundary monitors
            if spec.impact_bounds:
                monitor = CapabilityBoundaryMonitor("capability_boundaries", spec.impact_bounds)
                monitor.initialize(config.get("capability_boundary", {}))
                self.add_monitor(monitor)

            # Create mesa-optimization monitors
            if spec.mesa_guards:
                monitor = MesaOptimizationMonitor("mesa_optimization", spec.mesa_guards)
                monitor.initialize(config.get("mesa_optimization", {}))
                self.add_monitor(monitor)

            self.logger.info(f"Initialized {len(self.monitors)} safety monitors")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize monitors: {e}")
            return False

    def start_monitoring(self):
        """Start continuous safety monitoring."""
        if self.running:
            return

        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        # Activate all monitors
        for monitor in self.monitors:
            monitor.activate()

        self.logger.info("Safety monitoring started")

    def stop_monitoring(self):
        """Stop safety monitoring."""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)

        # Deactivate all monitors
        for monitor in self.monitors:
            monitor.deactivate()

        self.logger.info("Safety monitoring stopped")

    def monitor_state(self, current_state: Dict[str, Any]) -> List[MonitoringResult]:
        """Monitor current system state and return results."""
        results = []

        for monitor in self.monitors:
            if monitor.status == MonitorStatus.ACTIVE:
                try:
                    result = monitor.check_property(current_state)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Monitor {monitor.name} failed: {e}")
                    monitor.status = MonitorStatus.ERROR

        return results

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # This would get current state from the AGI system
                current_state = self._get_current_system_state()
                self.monitor_state(current_state)

                time.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(self.monitoring_interval)

    def _get_current_system_state(self) -> Dict[str, Any]:
        """Get current system state for monitoring."""
        # This would interface with the actual AGI system
        # For now, return mock state
        return {
            "goal_alignment": 0.95 + 0.1 * (time.time() % 1 - 0.5),
            "value_alignment": 0.92 + 0.08 * (time.time() % 1 - 0.5),
            "optimization_complexity": 0.3 + 0.2 * (time.time() % 1 - 0.5),
            "impact_level": 0.1 + 0.05 * (time.time() % 1 - 0.5),
            "system_performance": 0.88 + 0.12 * (time.time() % 1 - 0.5),
        }

    def _handle_alert(self, alert: SafetyAlert):
        """Handle safety alerts from monitors."""
        self.alert_queue.put(alert)
        self.logger.warning(f"Safety alert: {alert.violation_description}")

        # Handle emergency alerts
        if alert.level == AlertLevel.EMERGENCY:
            for callback in self.emergency_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Emergency callback failed: {e}")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring system status."""
        active_monitors = sum(1 for m in self.monitors if m.status == MonitorStatus.ACTIVE)
        error_monitors = sum(1 for m in self.monitors if m.status == MonitorStatus.ERROR)

        return {
            "running": self.running,
            "total_monitors": len(self.monitors),
            "active_monitors": active_monitors,
            "error_monitors": error_monitors,
            "monitoring_interval": self.monitoring_interval,
            "alert_queue_size": self.alert_queue.qsize(),
        }

    def emergency_shutdown(self, reason: str):
        """Trigger emergency shutdown of monitored system."""
        self.logger.critical(f"EMERGENCY SHUTDOWN TRIGGERED: {reason}")

        # Stop monitoring
        self.stop_monitoring()

        # This would interface with the AGI system's shutdown mechanism
        self._trigger_system_shutdown(reason)

    def _trigger_system_shutdown(self, reason: str):
        """Trigger shutdown of the monitored AGI system."""
        # This would implement the actual shutdown mechanism
        # for the specific AGI architecture being monitored
        self.logger.critical(f"System shutdown initiated: {reason}")
        pass
