"""
API Module for Kenny AGI Blockchain Audit Trail

This module provides REST and GraphQL APIs for interacting with the
blockchain-based audit trail system, including query, verification,
and management endpoints.
"""

try:
    from .rest_api import AuditTrailAPI, create_app
except (ImportError, ModuleNotFoundError, SyntaxError):
    AuditTrailAPI = None
    create_app = None
try:
    from .graphql_api import GraphQLAPI, create_graphql_app
except (ImportError, ModuleNotFoundError, SyntaxError):
    GraphQLAPI = None
    create_graphql_app = None
try:
    from .websocket_api import AuditEventSubscription, WebSocketAPI
except (ImportError, ModuleNotFoundError, SyntaxError):
    WebSocketAPI = None
    AuditEventSubscription = None
try:
    from .auth import APIKey, AuthManager, JWTAuth
except (ImportError, ModuleNotFoundError, SyntaxError):
    AuthManager = None
    APIKey = None
    JWTAuth = None
try:
    from .validators import RequestValidator, ResponseValidator
except (ImportError, ModuleNotFoundError, SyntaxError):
    RequestValidator = None
    ResponseValidator = None
try:
    from .middleware import CORSMiddleware, LoggingMiddleware, RateLimitMiddleware
except (ImportError, ModuleNotFoundError, SyntaxError):
    CORSMiddleware = None
    RateLimitMiddleware = None
    LoggingMiddleware = None

__all__ = [
    "AuditTrailAPI",
    "create_app",
    "GraphQLAPI",
    "create_graphql_app",
    "WebSocketAPI",
    "AuditEventSubscription",
    "AuthManager",
    "APIKey",
    "JWTAuth",
    "RequestValidator",
    "ResponseValidator",
    "CORSMiddleware",
    "RateLimitMiddleware",
    "LoggingMiddleware",
]
