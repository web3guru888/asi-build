"""
Recovery Manager - Handles automatic failure detection and recovery
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class FailureType(Enum):
    NODE_FAILURE = "node_failure"
    SERVICE_CRASH = "service_crash"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    HARDWARE_FAILURE = "hardware_failure"
    SOFTWARE_ERROR = "software_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    RESTART = "restart"
    MIGRATE = "migrate"
    RESCHEDULE = "reschedule"
    ROLLBACK = "rollback"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    MANUAL_INTERVENTION = "manual_intervention"
    IGNORE = "ignore"


class RecoveryStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FailureEvent:
    """Failure event information"""

    event_id: str
    failure_type: FailureType
    affected_component: str  # job_id, node_id, service_name, etc.
    detected_at: float
    description: str
    severity: str = "medium"  # low, medium, high, critical
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "failure_type": self.failure_type.value,
            "affected_component": self.affected_component,
            "detected_at": self.detected_at,
            "description": self.description,
            "severity": self.severity,
            "metadata": self.metadata,
        }


@dataclass
class RecoveryPlan:
    """Recovery plan for handling failures"""

    plan_id: str
    failure_event_id: str
    recovery_actions: List[RecoveryAction]
    estimated_duration: float  # seconds
    success_probability: float  # 0.0 to 1.0
    dependencies: List[str] = field(default_factory=list)  # other plan IDs
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "failure_event_id": self.failure_event_id,
            "recovery_actions": [action.value for action in self.recovery_actions],
            "estimated_duration": self.estimated_duration,
            "success_probability": self.success_probability,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }


@dataclass
class RecoveryExecution:
    """Recovery execution tracking"""

    execution_id: str
    plan_id: str
    status: RecoveryStatus
    started_at: float
    completed_at: Optional[float] = None
    current_action_index: int = 0
    success: bool = False
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "current_action_index": self.current_action_index,
            "success": self.success,
            "error_message": self.error_message,
            "logs": self.logs,
        }


class HealthChecker:
    """Health checker for system components"""

    def __init__(self, component_name: str, check_interval: float = 30.0):
        self.component_name = component_name
        self.check_interval = check_interval
        self.logger = logging.getLogger(f"health_checker.{component_name}")
        self.last_check_time = 0.0
        self.healthy = True
        self.check_history: List[Tuple[float, bool]] = []
        self.failure_callbacks: List[Callable[[str, str], None]] = []

    async def add_failure_callback(self, callback: Callable[[str, str], None]) -> None:
        """Add callback to be called when failure is detected"""
        self.failure_callbacks.append(callback)

    async def perform_health_check(self) -> bool:
        """Perform health check - to be implemented by subclasses"""
        return True

    async def start_monitoring(self) -> None:
        """Start health monitoring"""
        while True:
            try:
                current_time = time.time()
                is_healthy = await self.perform_health_check()

                self.check_history.append((current_time, is_healthy))

                # Keep only recent history (last hour)
                cutoff_time = current_time - 3600
                self.check_history = [
                    (timestamp, healthy)
                    for timestamp, healthy in self.check_history
                    if timestamp > cutoff_time
                ]

                # Detect state change
                if self.healthy and not is_healthy:
                    # Component became unhealthy
                    self.healthy = False
                    failure_reason = f"{self.component_name} health check failed"

                    # Notify failure callbacks
                    for callback in self.failure_callbacks:
                        try:
                            await callback(self.component_name, failure_reason)
                        except Exception as e:
                            self.logger.error(f"Error in failure callback: {e}")

                elif not self.healthy and is_healthy:
                    # Component recovered
                    self.healthy = True
                    self.logger.info(f"{self.component_name} has recovered")

                self.last_check_time = current_time
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(self.check_interval)


class RecoveryManager:
    """
    Advanced recovery manager with automatic failure detection and recovery
    """

    def __init__(self):
        self.logger = logging.getLogger("recovery_manager")

        # Failure tracking
        self.failure_events: Dict[str, FailureEvent] = {}
        self.recovery_plans: Dict[str, RecoveryPlan] = {}
        self.recovery_executions: Dict[str, RecoveryExecution] = {}

        # Health checkers
        self.health_checkers: Dict[str, HealthChecker] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}

        # Recovery strategies
        self.recovery_strategies: Dict[FailureType, List[RecoveryAction]] = {
            FailureType.NODE_FAILURE: [RecoveryAction.MIGRATE, RecoveryAction.RESCHEDULE],
            FailureType.SERVICE_CRASH: [RecoveryAction.RESTART, RecoveryAction.MIGRATE],
            FailureType.RESOURCE_EXHAUSTION: [RecoveryAction.SCALE_UP, RecoveryAction.MIGRATE],
            FailureType.NETWORK_PARTITION: [RecoveryAction.MIGRATE, RecoveryAction.RESCHEDULE],
            FailureType.HARDWARE_FAILURE: [RecoveryAction.MIGRATE, RecoveryAction.RESCHEDULE],
            FailureType.SOFTWARE_ERROR: [RecoveryAction.RESTART, RecoveryAction.ROLLBACK],
            FailureType.TIMEOUT: [RecoveryAction.RESTART, RecoveryAction.RESCHEDULE],
            FailureType.UNKNOWN: [RecoveryAction.MANUAL_INTERVENTION],
        }

        # Recovery execution pool
        self.max_concurrent_recoveries = 5
        self.active_recoveries: Set[str] = set()

        # Statistics
        self._stats = {
            "total_failures": 0,
            "recovered_failures": 0,
            "failed_recoveries": 0,
            "average_recovery_time": 0.0,
            "current_failures": 0,
            "active_recoveries": 0,
        }

    async def initialize(self) -> None:
        """Initialize the recovery manager"""
        self.logger.info("Initializing recovery manager")

        # Initialize default health checkers
        await self._initialize_default_health_checkers()

        self.logger.info("Recovery manager initialized")

    async def _initialize_default_health_checkers(self) -> None:
        """Initialize default health checkers for system components"""
        # Add health checkers for key system components
        system_checker = SystemHealthChecker("system")
        await self.add_health_checker(system_checker)

        memory_checker = MemoryHealthChecker("memory")
        await self.add_health_checker(memory_checker)

        disk_checker = DiskHealthChecker("disk")
        await self.add_health_checker(disk_checker)

    async def add_health_checker(self, health_checker: HealthChecker) -> None:
        """Add a health checker for a component"""
        component_name = health_checker.component_name
        self.health_checkers[component_name] = health_checker

        # Add failure callback
        await health_checker.add_failure_callback(self._on_component_failure)

        # Start monitoring task
        self.monitoring_tasks[component_name] = asyncio.create_task(
            health_checker.start_monitoring()
        )

        self.logger.info(f"Added health checker for {component_name}")

    async def _on_component_failure(self, component_name: str, failure_reason: str) -> None:
        """Handle component failure detection"""
        await self.report_failure(
            failure_type=FailureType.SERVICE_CRASH,
            affected_component=component_name,
            description=failure_reason,
            severity="high",
        )

    async def report_failure(
        self,
        failure_type: FailureType,
        affected_component: str,
        description: str,
        severity: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Report a failure event"""
        event_id = str(uuid.uuid4())

        failure_event = FailureEvent(
            event_id=event_id,
            failure_type=failure_type,
            affected_component=affected_component,
            detected_at=time.time(),
            description=description,
            severity=severity,
            metadata=metadata or {},
        )

        self.failure_events[event_id] = failure_event
        self._stats["total_failures"] += 1
        self._stats["current_failures"] += 1

        self.logger.warning(
            f"Failure reported: {failure_type.value} on {affected_component} - {description}"
        )

        # Automatically create and execute recovery plan
        plan_id = await self._create_recovery_plan(failure_event)
        if plan_id:
            await self._execute_recovery_plan(plan_id)

        return event_id

    async def _create_recovery_plan(self, failure_event: FailureEvent) -> Optional[str]:
        """Create a recovery plan for a failure event"""
        try:
            plan_id = str(uuid.uuid4())

            # Get recovery actions for this failure type
            recovery_actions = self.recovery_strategies.get(
                failure_event.failure_type, [RecoveryAction.MANUAL_INTERVENTION]
            )

            # Estimate duration based on actions
            estimated_duration = self._estimate_recovery_duration(recovery_actions)

            # Calculate success probability
            success_probability = self._calculate_success_probability(
                failure_event.failure_type, recovery_actions
            )

            recovery_plan = RecoveryPlan(
                plan_id=plan_id,
                failure_event_id=failure_event.event_id,
                recovery_actions=recovery_actions,
                estimated_duration=estimated_duration,
                success_probability=success_probability,
            )

            self.recovery_plans[plan_id] = recovery_plan

            self.logger.info(
                f"Created recovery plan {plan_id} for failure {failure_event.event_id} "
                f"with {len(recovery_actions)} actions"
            )

            return plan_id

        except Exception as e:
            self.logger.error(f"Error creating recovery plan: {e}")
            return None

    def _estimate_recovery_duration(self, recovery_actions: List[RecoveryAction]) -> float:
        """Estimate recovery duration based on actions"""
        action_durations = {
            RecoveryAction.RESTART: 60.0,
            RecoveryAction.MIGRATE: 300.0,
            RecoveryAction.RESCHEDULE: 120.0,
            RecoveryAction.ROLLBACK: 180.0,
            RecoveryAction.SCALE_UP: 240.0,
            RecoveryAction.SCALE_DOWN: 120.0,
            RecoveryAction.MANUAL_INTERVENTION: 3600.0,
            RecoveryAction.IGNORE: 0.0,
        }

        total_duration = 0.0
        for action in recovery_actions:
            total_duration += action_durations.get(action, 300.0)

        return total_duration

    def _calculate_success_probability(
        self, failure_type: FailureType, recovery_actions: List[RecoveryAction]
    ) -> float:
        """Calculate success probability for recovery actions"""
        # Base success rates for different failure types
        base_success_rates = {
            FailureType.NODE_FAILURE: 0.8,
            FailureType.SERVICE_CRASH: 0.9,
            FailureType.RESOURCE_EXHAUSTION: 0.85,
            FailureType.NETWORK_PARTITION: 0.7,
            FailureType.HARDWARE_FAILURE: 0.6,
            FailureType.SOFTWARE_ERROR: 0.8,
            FailureType.TIMEOUT: 0.85,
            FailureType.UNKNOWN: 0.5,
        }

        base_rate = base_success_rates.get(failure_type, 0.7)

        # Adjust based on recovery actions
        action_multipliers = {
            RecoveryAction.RESTART: 1.1,
            RecoveryAction.MIGRATE: 1.0,
            RecoveryAction.RESCHEDULE: 1.05,
            RecoveryAction.ROLLBACK: 0.9,
            RecoveryAction.SCALE_UP: 1.15,
            RecoveryAction.SCALE_DOWN: 1.1,
            RecoveryAction.MANUAL_INTERVENTION: 0.8,
            RecoveryAction.IGNORE: 0.0,
        }

        multiplier = 1.0
        for action in recovery_actions:
            multiplier *= action_multipliers.get(action, 1.0)

        return min(1.0, base_rate * multiplier)

    async def _execute_recovery_plan(self, plan_id: str) -> str:
        """Execute a recovery plan"""
        if plan_id not in self.recovery_plans:
            raise ValueError(f"Recovery plan {plan_id} not found")

        if len(self.active_recoveries) >= self.max_concurrent_recoveries:
            self.logger.warning("Maximum concurrent recoveries reached, queuing plan")
            # In a full implementation, you'd queue this for later execution
            return ""

        recovery_plan = self.recovery_plans[plan_id]
        execution_id = str(uuid.uuid4())

        recovery_execution = RecoveryExecution(
            execution_id=execution_id,
            plan_id=plan_id,
            status=RecoveryStatus.IN_PROGRESS,
            started_at=time.time(),
        )

        self.recovery_executions[execution_id] = recovery_execution
        self.active_recoveries.add(execution_id)
        self._stats["active_recoveries"] += 1

        self.logger.info(f"Starting execution of recovery plan {plan_id}")

        # Execute recovery plan in background
        asyncio.create_task(self._execute_recovery_actions(execution_id))

        return execution_id

    async def _execute_recovery_actions(self, execution_id: str) -> None:
        """Execute recovery actions for a plan"""
        execution = self.recovery_executions[execution_id]
        recovery_plan = self.recovery_plans[execution.plan_id]
        failure_event = self.failure_events[recovery_plan.failure_event_id]

        try:
            execution.logs.append(f"Starting recovery execution at {time.time()}")

            for i, action in enumerate(recovery_plan.recovery_actions):
                execution.current_action_index = i
                execution.logs.append(
                    f"Executing action {i + 1}/{len(recovery_plan.recovery_actions)}: {action.value}"
                )

                success = await self._execute_recovery_action(
                    action, failure_event.affected_component, execution
                )

                if not success:
                    execution.logs.append(f"Action {action.value} failed")
                    break

                execution.logs.append(f"Action {action.value} completed successfully")

            # Check if all actions completed successfully
            all_completed = (
                execution.current_action_index >= len(recovery_plan.recovery_actions) - 1
            )

            if all_completed:
                execution.status = RecoveryStatus.COMPLETED
                execution.success = True
                execution.logs.append("Recovery completed successfully")

                # Mark failure as recovered
                self._stats["recovered_failures"] += 1
                self._stats["current_failures"] -= 1

            else:
                execution.status = RecoveryStatus.FAILED
                execution.error_message = "One or more recovery actions failed"
                execution.logs.append("Recovery failed")
                self._stats["failed_recoveries"] += 1

        except Exception as e:
            execution.status = RecoveryStatus.FAILED
            execution.error_message = str(e)
            execution.logs.append(f"Recovery execution error: {e}")
            self._stats["failed_recoveries"] += 1

        finally:
            execution.completed_at = time.time()

            # Update statistics
            if execution.success:
                recovery_time = execution.completed_at - execution.started_at
                self._stats["average_recovery_time"] = (
                    (
                        (
                            self._stats["average_recovery_time"]
                            * (self._stats["recovered_failures"] - 1)
                            + recovery_time
                        )
                        / self._stats["recovered_failures"]
                    )
                    if self._stats["recovered_failures"] > 0
                    else recovery_time
                )

            # Clean up
            self.active_recoveries.discard(execution_id)
            self._stats["active_recoveries"] -= 1

            self.logger.info(
                f"Recovery execution {execution_id} completed with status: {execution.status.value}"
            )

    async def _execute_recovery_action(
        self, action: RecoveryAction, affected_component: str, execution: RecoveryExecution
    ) -> bool:
        """Execute a specific recovery action"""
        try:
            if action == RecoveryAction.RESTART:
                return await self._restart_component(affected_component)
            elif action == RecoveryAction.MIGRATE:
                return await self._migrate_component(affected_component)
            elif action == RecoveryAction.RESCHEDULE:
                return await self._reschedule_component(affected_component)
            elif action == RecoveryAction.ROLLBACK:
                return await self._rollback_component(affected_component)
            elif action == RecoveryAction.SCALE_UP:
                return await self._scale_up_component(affected_component)
            elif action == RecoveryAction.SCALE_DOWN:
                return await self._scale_down_component(affected_component)
            elif action == RecoveryAction.MANUAL_INTERVENTION:
                return await self._request_manual_intervention(affected_component)
            elif action == RecoveryAction.IGNORE:
                return True  # Always succeeds
            else:
                execution.logs.append(f"Unknown recovery action: {action}")
                return False

        except Exception as e:
            execution.logs.append(f"Error executing {action.value}: {e}")
            return False

    # Recovery action implementations (simplified)
    async def _restart_component(self, component: str) -> bool:
        """Restart a component"""
        self.logger.info(f"Restarting component: {component}")
        await asyncio.sleep(2.0)  # Simulate restart time
        return True

    async def _migrate_component(self, component: str) -> bool:
        """Migrate a component to another node"""
        self.logger.info(f"Migrating component: {component}")
        await asyncio.sleep(5.0)  # Simulate migration time
        return True

    async def _reschedule_component(self, component: str) -> bool:
        """Reschedule a component"""
        self.logger.info(f"Rescheduling component: {component}")
        await asyncio.sleep(3.0)  # Simulate reschedule time
        return True

    async def _rollback_component(self, component: str) -> bool:
        """Rollback a component to previous state"""
        self.logger.info(f"Rolling back component: {component}")
        await asyncio.sleep(4.0)  # Simulate rollback time
        return True

    async def _scale_up_component(self, component: str) -> bool:
        """Scale up resources for a component"""
        self.logger.info(f"Scaling up component: {component}")
        await asyncio.sleep(6.0)  # Simulate scale up time
        return True

    async def _scale_down_component(self, component: str) -> bool:
        """Scale down resources for a component"""
        self.logger.info(f"Scaling down component: {component}")
        await asyncio.sleep(3.0)  # Simulate scale down time
        return True

    async def _request_manual_intervention(self, component: str) -> bool:
        """Request manual intervention"""
        self.logger.warning(f"Manual intervention required for component: {component}")
        # In a real system, this would create a ticket or alert
        return False  # Requires manual action

    async def get_recovery_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get recovery execution status"""
        if execution_id not in self.recovery_executions:
            return None

        execution = self.recovery_executions[execution_id]
        return execution.to_dict()

    async def get_failure_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent failure events"""
        events = sorted(self.failure_events.values(), key=lambda e: e.detected_at, reverse=True)

        return [event.to_dict() for event in events[:limit]]

    async def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery system statistics"""
        return {
            **self._stats,
            "health_checkers": len(self.health_checkers),
            "recovery_plans": len(self.recovery_plans),
            "recovery_executions": len(self.recovery_executions),
            "failure_types_distribution": self._get_failure_type_distribution(),
        }

    def _get_failure_type_distribution(self) -> Dict[str, int]:
        """Get distribution of failure types"""
        distribution = {}
        for failure_type in FailureType:
            count = len([f for f in self.failure_events.values() if f.failure_type == failure_type])
            distribution[failure_type.value] = count
        return distribution

    async def shutdown(self) -> None:
        """Shutdown the recovery manager"""
        self.logger.info("Shutting down recovery manager")

        # Cancel all monitoring tasks
        for task_name, task in self.monitoring_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.logger.info("Recovery manager shutdown complete")


# Specific health checker implementations


class SystemHealthChecker(HealthChecker):
    """System-level health checker"""

    async def perform_health_check(self) -> bool:
        try:
            import psutil

            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1.0)
            if cpu_percent > 95:
                return False

            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 95:
                return False

            # Check disk usage
            disk = psutil.disk_usage("/")
            if (disk.used / disk.total) > 0.95:
                return False

            return True

        except Exception as e:
            self.logger.error(f"System health check failed: {e}")
            return False


class MemoryHealthChecker(HealthChecker):
    """Memory-specific health checker"""

    async def perform_health_check(self) -> bool:
        try:
            import psutil

            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Check if memory usage is critical
            if memory.percent > 90:
                return False

            # Check if swap usage is too high
            if swap.percent > 80:
                return False

            return True

        except Exception as e:
            self.logger.error(f"Memory health check failed: {e}")
            return False


class DiskHealthChecker(HealthChecker):
    """Disk-specific health checker"""

    async def perform_health_check(self) -> bool:
        try:
            import psutil

            # Check all disk partitions
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    if (usage.used / usage.total) > 0.9:
                        self.logger.warning(
                            f"Disk {partition.mountpoint} is {(usage.used / usage.total) * 100:.1f}% full"
                        )
                        return False
                except (PermissionError, OSError):
                    continue

            return True

        except Exception as e:
            self.logger.error(f"Disk health check failed: {e}")
            return False
