"""
Comprehensive Error Handling and Recovery System
Provides robust error handling and recovery mechanisms for decentralized training
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories"""

    NETWORK = "network"
    COMPUTATION = "computation"
    STORAGE = "storage"
    PROTOCOL = "protocol"
    SECURITY = "security"
    RESOURCE = "resource"
    DATA = "data"
    CONSENSUS = "consensus"


@dataclass
class ErrorInfo:
    """Detailed error information"""

    error_id: str
    timestamp: float
    severity: ErrorSeverity
    category: ErrorCategory
    component: str
    message: str
    stack_trace: str
    context: Dict[str, Any]
    recovery_action: Optional[str] = None
    resolved: bool = False
    resolution_time: Optional[float] = None


class CircuitBreakerState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker pattern implementation"""

    def __init__(
        self, failure_threshold: int = 5, recovery_timeout: float = 60.0, success_threshold: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state = CircuitBreakerState.CLOSED

        self.logger = logging.getLogger(__name__)

    def call(self, func: Callable, *args, **kwargs):
        """Call function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    async def call_async(self, func: Callable, *args, **kwargs):
        """Async version of circuit breaker call"""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.logger.info("Circuit breaker transitioning to CLOSED")

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(
                f"Circuit breaker transitioning to OPEN after {self.failure_count} failures"
            )

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }


class RetryManager:
    """Advanced retry logic with exponential backoff"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

        self.logger = logging.getLogger(__name__)

    async def retry_async(self, func: Callable, *args, **kwargs):
        """Retry async function with exponential backoff"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    self.logger.info(f"Function succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)

                    if self.jitter:
                        import random

                        delay = delay * (0.5 + random.random() * 0.5)

                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"All {self.max_retries + 1} attempts failed")

        raise last_exception

    def retry(self, func: Callable, *args, **kwargs):
        """Retry sync function with exponential backoff"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    self.logger.info(f"Function succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)

                    if self.jitter:
                        import random

                        delay = delay * (0.5 + random.random() * 0.5)

                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {self.max_retries + 1} attempts failed")

        raise last_exception


class ErrorHandler:
    """Central error handling and recovery system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Error storage
        self.error_history: List[ErrorInfo] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_managers: Dict[str, RetryManager] = {}

        # Recovery strategies
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {
            ErrorCategory.NETWORK: self._handle_network_error,
            ErrorCategory.COMPUTATION: self._handle_computation_error,
            ErrorCategory.STORAGE: self._handle_storage_error,
            ErrorCategory.PROTOCOL: self._handle_protocol_error,
            ErrorCategory.SECURITY: self._handle_security_error,
            ErrorCategory.RESOURCE: self._handle_resource_error,
            ErrorCategory.DATA: self._handle_data_error,
            ErrorCategory.CONSENSUS: self._handle_consensus_error,
        }

        # Error thresholds
        self.severity_thresholds = {
            ErrorSeverity.CRITICAL: 1,  # Immediate action
            ErrorSeverity.HIGH: 3,  # Action within minutes
            ErrorSeverity.MEDIUM: 10,  # Action within hours
            ErrorSeverity.LOW: 50,  # Monitor and track
        }

        self.logger = logging.getLogger(__name__)

        # Setup structured logging
        self._setup_structured_logging()

    def _setup_structured_logging(self):
        """Setup structured logging with error context"""
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(component)s - %(message)s"
        )

        # File handler for errors
        error_handler = logging.FileHandler("/tmp/decentralized_training_errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        # Add custom filter for component context
        class ComponentFilter(logging.Filter):
            def filter(self, record):
                if not hasattr(record, "component"):
                    record.component = "unknown"
                return True

        error_handler.addFilter(ComponentFilter())

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(error_handler)

    def get_circuit_breaker(self, component: str) -> CircuitBreaker:
        """Get or create circuit breaker for component"""
        if component not in self.circuit_breakers:
            self.circuit_breakers[component] = CircuitBreaker(
                failure_threshold=self.config.get("circuit_breaker_threshold", 5),
                recovery_timeout=self.config.get("circuit_breaker_timeout", 60.0),
            )
        return self.circuit_breakers[component]

    def get_retry_manager(self, component: str) -> RetryManager:
        """Get or create retry manager for component"""
        if component not in self.retry_managers:
            self.retry_managers[component] = RetryManager(
                max_retries=self.config.get("max_retries", 3),
                base_delay=self.config.get("retry_base_delay", 1.0),
                max_delay=self.config.get("retry_max_delay", 60.0),
            )
        return self.retry_managers[component]

    def handle_error(
        self,
        error: Exception,
        component: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        context: Dict[str, Any] = None,
    ) -> ErrorInfo:
        """Handle and log error with recovery action"""

        error_id = f"{component}_{int(time.time())}_{id(error)}"

        error_info = ErrorInfo(
            error_id=error_id,
            timestamp=time.time(),
            severity=severity,
            category=category,
            component=component,
            message=str(error),
            stack_trace=traceback.format_exc(),
            context=context or {},
        )

        # Log error with structured context
        extra = {
            "component": component,
            "error_id": error_id,
            "severity": severity.value,
            "category": category.value,
        }

        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error in {component}: {error}", extra=extra)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(f"High severity error in {component}: {error}", extra=extra)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Medium severity error in {component}: {error}", extra=extra)
        else:
            self.logger.info(f"Low severity error in {component}: {error}", extra=extra)

        # Store error
        self.error_history.append(error_info)

        # Attempt recovery
        recovery_action = self._attempt_recovery(error_info)
        error_info.recovery_action = recovery_action

        # Check if immediate escalation is needed
        self._check_escalation(error_info)

        return error_info

    def _attempt_recovery(self, error_info: ErrorInfo) -> Optional[str]:
        """Attempt automatic recovery based on error category"""

        if error_info.category in self.recovery_strategies:
            try:
                recovery_strategy = self.recovery_strategies[error_info.category]
                return recovery_strategy(error_info)

            except Exception as recovery_error:
                self.logger.error(f"Recovery strategy failed: {recovery_error}")
                return f"recovery_failed: {recovery_error}"

        return "no_recovery_strategy"

    def _handle_network_error(self, error_info: ErrorInfo) -> str:
        """Handle network-related errors"""

        # Network-specific recovery logic
        if "connection" in error_info.message.lower():
            return "connection_retry_scheduled"
        elif "timeout" in error_info.message.lower():
            return "timeout_increase_scheduled"
        elif "dns" in error_info.message.lower():
            return "dns_refresh_scheduled"

        return "generic_network_recovery"

    def _handle_computation_error(self, error_info: ErrorInfo) -> str:
        """Handle computation-related errors"""

        if "cuda" in error_info.message.lower() or "gpu" in error_info.message.lower():
            return "gpu_reset_scheduled"
        elif "memory" in error_info.message.lower() or "oom" in error_info.message.lower():
            return "memory_cleanup_scheduled"
        elif "nan" in error_info.message.lower() or "inf" in error_info.message.lower():
            return "gradient_clipping_enabled"

        return "computation_restart_scheduled"

    def _handle_storage_error(self, error_info: ErrorInfo) -> str:
        """Handle storage-related errors"""

        if "disk" in error_info.message.lower() and "full" in error_info.message.lower():
            return "disk_cleanup_scheduled"
        elif "permission" in error_info.message.lower():
            return "permission_fix_scheduled"
        elif "corruption" in error_info.message.lower():
            return "data_recovery_scheduled"

        return "storage_check_scheduled"

    def _handle_protocol_error(self, error_info: ErrorInfo) -> str:
        """Handle protocol-related errors"""

        if "handshake" in error_info.message.lower():
            return "protocol_handshake_retry"
        elif "version" in error_info.message.lower():
            return "protocol_version_check"

        return "protocol_reset_scheduled"

    def _handle_security_error(self, error_info: ErrorInfo) -> str:
        """Handle security-related errors"""

        if "signature" in error_info.message.lower():
            return "signature_verification_retry"
        elif "authentication" in error_info.message.lower():
            return "reauthentication_scheduled"
        elif "byzantine" in error_info.message.lower():
            return "node_quarantine_scheduled"

        return "security_audit_scheduled"

    def _handle_resource_error(self, error_info: ErrorInfo) -> str:
        """Handle resource-related errors"""

        if "cpu" in error_info.message.lower():
            return "cpu_optimization_scheduled"
        elif "memory" in error_info.message.lower():
            return "memory_optimization_scheduled"
        elif "bandwidth" in error_info.message.lower():
            return "bandwidth_throttling_enabled"

        return "resource_rebalancing_scheduled"

    def _handle_data_error(self, error_info: ErrorInfo) -> str:
        """Handle data-related errors"""

        if "corrupt" in error_info.message.lower():
            return "data_integrity_check_scheduled"
        elif "missing" in error_info.message.lower():
            return "data_recovery_scheduled"
        elif "format" in error_info.message.lower():
            return "data_format_conversion_scheduled"

        return "data_validation_scheduled"

    def _handle_consensus_error(self, error_info: ErrorInfo) -> str:
        """Handle consensus-related errors"""

        if "timeout" in error_info.message.lower():
            return "consensus_timeout_increased"
        elif "disagreement" in error_info.message.lower():
            return "consensus_restart_scheduled"

        return "consensus_algorithm_fallback"

    def _check_escalation(self, error_info: ErrorInfo):
        """Check if error requires escalation"""

        # Count recent errors of same category
        recent_errors = [
            e
            for e in self.error_history[-100:]  # Last 100 errors
            if (e.category == error_info.category and time.time() - e.timestamp < 3600)  # Last hour
        ]

        threshold = self.severity_thresholds.get(error_info.severity, 10)

        if len(recent_errors) >= threshold:
            self._escalate_error(error_info, len(recent_errors))

    def _escalate_error(self, error_info: ErrorInfo, error_count: int):
        """Escalate error to higher level handling"""

        escalation_message = (
            f"ERROR ESCALATION: {error_count} {error_info.category.value} errors "
            f"in the last hour. Latest: {error_info.message}"
        )

        self.logger.critical(
            escalation_message,
            extra={
                "component": "error_handler",
                "error_id": error_info.error_id,
                "escalation": True,
            },
        )

        # Here you could integrate with external alerting systems
        # e.g., send to Slack, email, PagerDuty, etc.

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for specified time period"""

        cutoff_time = time.time() - (hours * 3600)
        recent_errors = [e for e in self.error_history if e.timestamp >= cutoff_time]

        if not recent_errors:
            return {"total_errors": 0, "period_hours": hours}

        # Categorize errors
        by_category = defaultdict(int)
        by_severity = defaultdict(int)
        by_component = defaultdict(int)

        for error in recent_errors:
            by_category[error.category.value] += 1
            by_severity[error.severity.value] += 1
            by_component[error.component] += 1

        # Calculate resolution rate
        resolved_errors = sum(1 for e in recent_errors if e.resolved)
        resolution_rate = resolved_errors / len(recent_errors) if recent_errors else 0

        return {
            "total_errors": len(recent_errors),
            "period_hours": hours,
            "resolution_rate": resolution_rate,
            "by_category": dict(by_category),
            "by_severity": dict(by_severity),
            "by_component": dict(by_component),
            "critical_errors": by_severity.get("critical", 0),
            "most_problematic_component": (
                max(by_component, key=by_component.get) if by_component else None
            ),
        }

    def mark_error_resolved(self, error_id: str, resolution_notes: str = ""):
        """Mark error as resolved"""

        for error in self.error_history:
            if error.error_id == error_id:
                error.resolved = True
                error.resolution_time = time.time()
                error.recovery_action = f"{error.recovery_action}; resolved: {resolution_notes}"

                self.logger.info(f"Error {error_id} marked as resolved: {resolution_notes}")
                return True

        return False


def error_handler_decorator(
    component: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.COMPUTATION,
    reraise: bool = True,
):
    """Decorator for automatic error handling"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Get error handler from global context or create one
                error_handler = getattr(async_wrapper, "_error_handler", None)
                if error_handler is None:
                    error_handler = ErrorHandler({})

                error_handler.handle_error(e, component, severity, category)

                if reraise:
                    raise
                return None

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get error handler from global context or create one
                error_handler = getattr(sync_wrapper, "_error_handler", None)
                if error_handler is None:
                    error_handler = ErrorHandler({})

                error_handler.handle_error(e, component, severity, category)

                if reraise:
                    raise
                return None

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class HealthChecker:
    """System health monitoring and checks"""

    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.health_checks: Dict[str, Callable] = {}
        self.health_status: Dict[str, Dict[str, Any]] = {}

        self.logger = logging.getLogger(__name__)

    def register_health_check(
        self, name: str, check_func: Callable, interval: float = 60.0, critical: bool = False
    ):
        """Register a health check"""

        self.health_checks[name] = {
            "func": check_func,
            "interval": interval,
            "critical": critical,
            "last_run": 0,
            "last_result": None,
        }

    async def run_health_checks(self):
        """Run all registered health checks"""

        current_time = time.time()

        for name, check_info in self.health_checks.items():
            if current_time - check_info["last_run"] >= check_info["interval"]:
                try:
                    if asyncio.iscoroutinefunction(check_info["func"]):
                        result = await check_info["func"]()
                    else:
                        result = check_info["func"]()

                    self.health_status[name] = {
                        "status": "healthy",
                        "result": result,
                        "timestamp": current_time,
                        "critical": check_info["critical"],
                    }

                    check_info["last_result"] = result
                    check_info["last_run"] = current_time

                except Exception as e:
                    self.health_status[name] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "timestamp": current_time,
                        "critical": check_info["critical"],
                    }

                    severity = (
                        ErrorSeverity.CRITICAL if check_info["critical"] else ErrorSeverity.HIGH
                    )

                    self.error_handler.handle_error(
                        e, f"health_check_{name}", severity, ErrorCategory.RESOURCE
                    )

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""

        if not self.health_status:
            return {"status": "unknown", "checks": 0}

        healthy_checks = sum(
            1 for status in self.health_status.values() if status["status"] == "healthy"
        )
        total_checks = len(self.health_status)

        critical_unhealthy = sum(
            1
            for status in self.health_status.values()
            if status["status"] == "unhealthy" and status["critical"]
        )

        if critical_unhealthy > 0:
            overall_status = "critical"
        elif healthy_checks == total_checks:
            overall_status = "healthy"
        elif healthy_checks / total_checks >= 0.8:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "checks": total_checks,
            "healthy": healthy_checks,
            "unhealthy": total_checks - healthy_checks,
            "critical_failures": critical_unhealthy,
            "health_score": healthy_checks / total_checks if total_checks > 0 else 0,
        }


# Global error handler instance
_global_error_handler = None


def get_global_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler({})
    return _global_error_handler


def set_global_error_handler(error_handler: ErrorHandler):
    """Set global error handler instance"""
    global _global_error_handler
    _global_error_handler = error_handler
