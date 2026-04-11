"""
AGI Economic Systems
===================

Comprehensive systems for reputation, governance, and value alignment.
"""

try:
    from .value_alignment import ValueAlignmentEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    ValueAlignmentEngine = None
try:
    from .reputation_system import ReputationSystem
except (ImportError, ModuleNotFoundError, SyntaxError):
    ReputationSystem = None
try:
    from .governance import GovernanceSystem
except (ImportError, ModuleNotFoundError, SyntaxError):
    GovernanceSystem = None

__all__ = ["ValueAlignmentEngine", "ReputationSystem", "GovernanceSystem"]
