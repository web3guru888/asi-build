"""
API Module for Kenny AGI Blockchain Audit Trail

This module provides REST and GraphQL APIs for interacting with the
blockchain-based audit trail system, including query, verification,
and management endpoints.
"""

from .rest_api import AuditTrailAPI, create_app
from .graphql_api import GraphQLAPI, create_graphql_app
from .websocket_api import WebSocketAPI, AuditEventSubscription
from .auth import AuthManager, APIKey, JWTAuth
from .validators import RequestValidator, ResponseValidator
from .middleware import CORSMiddleware, RateLimitMiddleware, LoggingMiddleware

__all__ = [
    'AuditTrailAPI',
    'create_app',
    'GraphQLAPI',
    'create_graphql_app',
    'WebSocketAPI',
    'AuditEventSubscription',
    'AuthManager',
    'APIKey',
    'JWTAuth',
    'RequestValidator',
    'ResponseValidator',
    'CORSMiddleware',
    'RateLimitMiddleware',
    'LoggingMiddleware'
]