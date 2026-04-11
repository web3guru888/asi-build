"""
API Module - Knowledge Network API Interface
===========================================

REST and WebSocket API for accessing omniscience network capabilities.
"""

try:
    from .knowledge_api import KnowledgeAPI, KnowledgeAPIClient, create_api_server, run_api_server
except (ImportError, ModuleNotFoundError, SyntaxError):
    KnowledgeAPI = None
    KnowledgeAPIClient = None
    create_api_server = None
    run_api_server = None

__all__ = ["KnowledgeAPI", "KnowledgeAPIClient", "create_api_server", "run_api_server"]
