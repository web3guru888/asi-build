"""
API Module - Knowledge Network API Interface
===========================================

REST and WebSocket API for accessing omniscience network capabilities.
"""

from .knowledge_api import KnowledgeAPI, KnowledgeAPIClient, create_api_server, run_api_server

__all__ = ['KnowledgeAPI', 'KnowledgeAPIClient', 'create_api_server', 'run_api_server']