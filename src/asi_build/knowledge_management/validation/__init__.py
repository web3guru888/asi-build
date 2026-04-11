"""
Validation Module - Knowledge Quality Control
===========================================

Comprehensive validation and quality assurance for knowledge processing.
"""

try:
    from .quality_controller import QualityController, ValidationRule, ValidationResult
except (ImportError, ModuleNotFoundError, SyntaxError):
    QualityController = None
    ValidationRule = None
    ValidationResult = None

__all__ = ['QualityController', 'ValidationRule', 'ValidationResult']