"""
Integration Module - System Integration Layer
===========================================

Integration layer for connecting omniscience with external systems.
"""

from .kenny_integration import KennyIntegration, create_kenny_integration, query_with_kenny_integration

__all__ = ['KennyIntegration', 'create_kenny_integration', 'query_with_kenny_integration']