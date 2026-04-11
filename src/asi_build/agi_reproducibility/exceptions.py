"""
Custom Exception Classes for AGI Reproducibility Platform

Comprehensive exception hierarchy for handling all error scenarios
in the AGI reproducibility platform.
"""

from typing import Any, Dict, List, Optional


class AGIReproducibilityError(Exception):
    """Base exception class for AGI Reproducibility Platform."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
        }


# Configuration Exceptions
class ConfigurationError(AGIReproducibilityError):
    """Exception raised for configuration-related errors."""

    pass


class ValidationError(AGIReproducibilityError):
    """Exception raised for validation failures."""

    pass


# Experiment Tracking Exceptions
class ExperimentError(AGIReproducibilityError):
    """Base class for experiment-related errors."""

    pass


class ExperimentNotFoundError(ExperimentError):
    """Exception raised when experiment is not found."""

    pass


class ExperimentAlreadyExistsError(ExperimentError):
    """Exception raised when experiment already exists."""

    pass


class ExperimentStateError(ExperimentError):
    """Exception raised for invalid experiment state transitions."""

    pass


class VersioningError(ExperimentError):
    """Exception raised for versioning-related errors."""

    pass


# Environment Capture Exceptions
class EnvironmentCaptureError(AGIReproducibilityError):
    """Base class for environment capture errors."""

    pass


class DependencyResolutionError(EnvironmentCaptureError):
    """Exception raised when dependencies cannot be resolved."""

    pass


class ContainerBuildError(EnvironmentCaptureError):
    """Exception raised when container build fails."""

    pass


class EnvironmentMismatchError(EnvironmentCaptureError):
    """Exception raised when environments don't match."""

    pass


# Replay System Exceptions
class ReplayError(AGIReproducibilityError):
    """Base class for replay system errors."""

    pass


class NonDeterministicBehaviorError(ReplayError):
    """Exception raised when non-deterministic behavior is detected."""

    pass


class ReplayTimeoutError(ReplayError):
    """Exception raised when replay times out."""

    pass


class ReplayResourceError(ReplayError):
    """Exception raised when replay exceeds resource limits."""

    pass


# Validation Exceptions
class ResultValidationError(AGIReproducibilityError):
    """Base class for result validation errors."""

    pass


class MetricComputationError(ResultValidationError):
    """Exception raised when metrics cannot be computed."""

    pass


class StatisticalSignificanceError(ResultValidationError):
    """Exception raised when results are not statistically significant."""

    pass


class ComparisonError(ResultValidationError):
    """Exception raised when result comparison fails."""

    pass


# Benchmark Exceptions
class BenchmarkError(AGIReproducibilityError):
    """Base class for benchmark-related errors."""

    pass


class BenchmarkTimeoutError(BenchmarkError):
    """Exception raised when benchmark times out."""

    pass


class BenchmarkFailureError(BenchmarkError):
    """Exception raised when benchmark fails."""

    pass


class ScalabilityError(BenchmarkError):
    """Exception raised for scalability issues."""

    pass


# Sharing Platform Exceptions
class SharingError(AGIReproducibilityError):
    """Base class for sharing platform errors."""

    pass


class PackageError(SharingError):
    """Exception raised for package-related errors."""

    pass


class PeerReviewError(SharingError):
    """Exception raised for peer review errors."""

    pass


class PermissionError(SharingError):
    """Exception raised for permission-related errors."""

    pass


# Formal Verification Exceptions
class FormalVerificationError(AGIReproducibilityError):
    """Base class for formal verification errors."""

    pass


class TheoremProvingError(FormalVerificationError):
    """Exception raised when theorem proving fails."""

    pass


class SafetyVerificationError(FormalVerificationError):
    """Exception raised when safety verification fails."""

    pass


class ProofValidationError(FormalVerificationError):
    """Exception raised when proof validation fails."""

    pass


# Hyperon/PRIMUS Specific Exceptions
class HyperonError(AGIReproducibilityError):
    """Base class for Hyperon-related errors."""

    pass


class PLNValidationError(HyperonError):
    """Exception raised for PLN validation errors."""

    pass


class MeTTaError(HyperonError):
    """Exception raised for MeTTa-related errors."""

    pass


class AtomSpaceError(HyperonError):
    """Exception raised for AtomSpace errors."""

    pass


class MORKError(HyperonError):
    """Exception raised for MORK data structure errors."""

    pass


# Integration Exceptions
class IntegrationError(AGIReproducibilityError):
    """Base class for integration errors."""

    pass


class GitHubIntegrationError(IntegrationError):
    """Exception raised for GitHub integration errors."""

    pass


class GitLabIntegrationError(IntegrationError):
    """Exception raised for GitLab integration errors."""

    pass


class ArXivIntegrationError(IntegrationError):
    """Exception raised for arXiv integration errors."""

    pass


class SingularityNetError(IntegrationError):
    """Exception raised for SingularityNET integration errors."""

    pass


# Storage Exceptions
class StorageError(AGIReproducibilityError):
    """Base class for storage errors."""

    pass


class S3StorageError(StorageError):
    """Exception raised for S3 storage errors."""

    pass


class IPFSStorageError(StorageError):
    """Exception raised for IPFS storage errors."""

    pass


class ArweaveStorageError(StorageError):
    """Exception raised for Arweave storage errors."""

    pass


# Security Exceptions
class SecurityError(AGIReproducibilityError):
    """Base class for security-related errors."""

    pass


class SandboxViolationError(SecurityError):
    """Exception raised when sandbox is violated."""

    pass


class CodeSigningError(SecurityError):
    """Exception raised for code signing errors."""

    pass


class AuthenticationError(SecurityError):
    """Exception raised for authentication errors."""

    pass


class AuthorizationError(SecurityError):
    """Exception raised for authorization errors."""

    pass


# Hardware/Resource Exceptions
class ResourceError(AGIReproducibilityError):
    """Base class for resource-related errors."""

    pass


class HardwareNotAvailableError(ResourceError):
    """Exception raised when required hardware is not available."""

    pass


class InsufficientResourcesError(ResourceError):
    """Exception raised when insufficient resources are available."""

    pass


class HardwareMismatchError(ResourceError):
    """Exception raised when hardware doesn't match requirements."""

    pass


class ExceptionHandler:
    """Centralized exception handling utility."""

    def __init__(self, logger=None):
        self.logger = logger

    def handle_exception(
        self, exception: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle and format exception for logging/reporting."""
        if isinstance(exception, AGIReproducibilityError):
            error_info = exception.to_dict()
        else:
            error_info = {
                "error_type": exception.__class__.__name__,
                "message": str(exception),
                "error_code": None,
                "context": context or {},
            }

        if self.logger:
            self.logger.error(f"Exception occurred: {error_info}")

        return error_info

    def wrap_exception(self, func):
        """Decorator to wrap functions with exception handling."""

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AGIReproducibilityError:
                raise  # Re-raise our custom exceptions
            except Exception as e:
                # Convert generic exceptions to our custom ones
                raise AGIReproducibilityError(
                    message=f"Unexpected error in {func.__name__}: {str(e)}",
                    error_code="UNEXPECTED_ERROR",
                    context={"function": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                ) from e

        return wrapper


def validate_experiment_id(experiment_id: str) -> None:
    """Validate experiment ID format."""
    if not experiment_id:
        raise ValidationError("Experiment ID cannot be empty")

    if len(experiment_id) > 100:
        raise ValidationError("Experiment ID cannot exceed 100 characters")

    # Check for valid characters (alphanumeric, hyphens, underscores)
    import re

    if not re.match(r"^[a-zA-Z0-9_-]+$", experiment_id):
        raise ValidationError("Experiment ID contains invalid characters")


def validate_version(version: str) -> None:
    """Validate version format (semantic versioning)."""
    if not version:
        raise ValidationError("Version cannot be empty")

    import re

    # Semantic versioning pattern
    pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*))?(?:\+([a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*))?$"
    if not re.match(pattern, version):
        raise ValidationError("Version must follow semantic versioning format (e.g., 1.0.0)")


def require_authentication(func):
    """Decorator to require authentication for sensitive operations."""

    def wrapper(*args, **kwargs):
        # TODO: Implement authentication check
        # For now, just pass through
        return func(*args, **kwargs)

    return wrapper


def require_authorization(permissions: List[str]):
    """Decorator to require specific permissions."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # TODO: Implement authorization check
            # For now, just pass through
            return func(*args, **kwargs)

        return wrapper

    return decorator
