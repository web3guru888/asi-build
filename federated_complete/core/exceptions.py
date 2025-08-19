"""
Federated Learning Exceptions

Custom exception classes for the federated learning framework.
"""

from typing import Optional, Any, Dict


class FederatedLearningError(Exception):
    """Base exception for federated learning framework."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}. Details: {self.details}"
        return self.message


class CommunicationError(FederatedLearningError):
    """Exception raised for communication-related errors."""
    
    def __init__(self, message: str, client_id: Optional[str] = None, 
                 error_code: Optional[str] = None):
        super().__init__(message, {
            "client_id": client_id,
            "error_code": error_code
        })
        self.client_id = client_id
        self.error_code = error_code


class AggregationError(FederatedLearningError):
    """Exception raised for aggregation-related errors."""
    
    def __init__(self, message: str, aggregator_type: Optional[str] = None,
                 client_count: Optional[int] = None):
        super().__init__(message, {
            "aggregator_type": aggregator_type,
            "client_count": client_count
        })
        self.aggregator_type = aggregator_type
        self.client_count = client_count


class PrivacyError(FederatedLearningError):
    """Exception raised for privacy-related errors."""
    
    def __init__(self, message: str, privacy_mechanism: Optional[str] = None,
                 privacy_budget: Optional[float] = None):
        super().__init__(message, {
            "privacy_mechanism": privacy_mechanism,
            "privacy_budget": privacy_budget
        })
        self.privacy_mechanism = privacy_mechanism
        self.privacy_budget = privacy_budget


class SecurityError(FederatedLearningError):
    """Exception raised for security-related errors."""
    
    def __init__(self, message: str, security_level: Optional[str] = None,
                 threat_type: Optional[str] = None):
        super().__init__(message, {
            "security_level": security_level,
            "threat_type": threat_type
        })
        self.security_level = security_level
        self.threat_type = threat_type


class ModelError(FederatedLearningError):
    """Exception raised for model-related errors."""
    
    def __init__(self, message: str, model_type: Optional[str] = None,
                 operation: Optional[str] = None):
        super().__init__(message, {
            "model_type": model_type,
            "operation": operation
        })
        self.model_type = model_type
        self.operation = operation


class ClientError(FederatedLearningError):
    """Exception raised for client-related errors."""
    
    def __init__(self, message: str, client_id: str,
                 client_state: Optional[str] = None):
        super().__init__(message, {
            "client_id": client_id,
            "client_state": client_state
        })
        self.client_id = client_id
        self.client_state = client_state


class ServerError(FederatedLearningError):
    """Exception raised for server-related errors."""
    
    def __init__(self, message: str, server_state: Optional[str] = None,
                 round_number: Optional[int] = None):
        super().__init__(message, {
            "server_state": server_state,
            "round_number": round_number
        })
        self.server_state = server_state
        self.round_number = round_number


class ConfigurationError(FederatedLearningError):
    """Exception raised for configuration-related errors."""
    
    def __init__(self, message: str, config_section: Optional[str] = None,
                 invalid_parameter: Optional[str] = None):
        super().__init__(message, {
            "config_section": config_section,
            "invalid_parameter": invalid_parameter
        })
        self.config_section = config_section
        self.invalid_parameter = invalid_parameter


class ValidationError(FederatedLearningError):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, validation_type: str,
                 expected_value: Optional[Any] = None,
                 actual_value: Optional[Any] = None):
        super().__init__(message, {
            "validation_type": validation_type,
            "expected_value": expected_value,
            "actual_value": actual_value
        })
        self.validation_type = validation_type
        self.expected_value = expected_value
        self.actual_value = actual_value