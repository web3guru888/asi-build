"""
Middleware Components for Kenny AGI Blockchain Audit Trail API

Provides middleware for rate limiting, logging, CORS handling,
and other cross-cutting concerns.
"""

import asyncio
import time
import json
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.middleware.cors import CORSMiddleware as StarletteCorsMidleware
from starlette.types import ASGIApp
import aioredis

logger = logging.getLogger(__name__)


@dataclass
class RequestLog:
    """Request log entry"""
    
    request_id: str
    timestamp: datetime
    method: str
    path: str
    client_ip: str
    user_agent: Optional[str] = None
    user_id: Optional[str] = None
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'request_id': self.request_id,
            'timestamp': self.timestamp.isoformat(),
            'method': self.method,
            'path': self.path,
            'client_ip': self.client_ip,
            'user_agent': self.user_agent,
            'user_id': self.user_id,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'request_size': self.request_size,
            'response_size': self.response_size,
            'error': self.error,
            'metadata': self.metadata
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware
    
    Implements sliding window rate limiting with support for
    different limits based on authentication and endpoints.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        calls: int = 100,
        period: int = 60,
        redis_url: Optional[str] = None,
        exempt_paths: Optional[List[str]] = None
    ):
        """
        Initialize rate limiting middleware
        
        Args:
            app: ASGI application
            calls: Number of calls allowed
            period: Time period in seconds
            redis_url: Redis URL for distributed rate limiting
            exempt_paths: Paths exempt from rate limiting
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.redis_url = redis_url
        self.exempt_paths = exempt_paths or ['/health', '/docs', '/redoc']
        
        # Local storage for rate limiting (in-memory)
        self.request_counts = {}
        
        # Redis connection for distributed rate limiting
        self.redis = None
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        
        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
            
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not await self._check_rate_limit(client_id):
            return JSONResponse(
                status_code=429,
                content={
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {self.calls} requests per {self.period} seconds allowed',
                    'retry_after': self.period
                },
                headers={'Retry-After': str(self.period)}
            )
            
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = await self._get_remaining_calls(client_id)
        response.headers['X-RateLimit-Limit'] = str(self.calls)
        response.headers['X-RateLimit-Remaining'] = str(remaining)
        response.headers['X-RateLimit-Reset'] = str(int(time.time()) + self.period)
        
        return response
        
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from authorization
        auth_header = request.headers.get('Authorization')
        if auth_header:
            # In a real implementation, decode the token to get user ID
            return f"user_{hash(auth_header) % 10000}"
            
        # Fall back to IP address
        client_ip = request.client.host if request.client else 'unknown'
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()
            
        return f"ip_{client_ip}"
        
    async def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limit"""
        if self.redis:
            return await self._check_rate_limit_redis(client_id)
        else:
            return self._check_rate_limit_memory(client_id)
            
    def _check_rate_limit_memory(self, client_id: str) -> bool:
        """Check rate limit using in-memory storage"""
        now = time.time()
        
        if client_id not in self.request_counts:
            self.request_counts[client_id] = []
            
        # Clean old entries
        cutoff = now - self.period
        self.request_counts[client_id] = [
            timestamp for timestamp in self.request_counts[client_id]
            if timestamp > cutoff
        ]
        
        # Check current count
        if len(self.request_counts[client_id]) >= self.calls:
            return False
            
        # Add current request
        self.request_counts[client_id].append(now)
        return True
        
    async def _check_rate_limit_redis(self, client_id: str) -> bool:
        """Check rate limit using Redis"""
        try:
            if not self.redis:
                self.redis = await aioredis.from_url(self.redis_url)
                
            key = f"rate_limit:{client_id}"
            now = int(time.time())
            
            # Use Redis sorted set for sliding window
            pipe = self.redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, now - self.period)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(uuid.uuid4()): now})
            
            # Set expiry
            pipe.expire(key, self.period)
            
            results = await pipe.execute()
            current_count = results[1]
            
            return current_count < self.calls
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {str(e)}")
            # Fall back to memory-based rate limiting
            return self._check_rate_limit_memory(client_id)
            
    async def _get_remaining_calls(self, client_id: str) -> int:
        """Get remaining calls for client"""
        if self.redis:
            try:
                key = f"rate_limit:{client_id}"
                current_count = await self.redis.zcard(key)
                return max(0, self.calls - current_count)
            except Exception:
                pass
                
        # Memory-based fallback
        current_count = len(self.request_counts.get(client_id, []))
        return max(0, self.calls - current_count)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive logging middleware
    
    Logs all requests with detailed information including
    timing, user information, and error details.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enable_request_body_logging: bool = False,
        enable_response_body_logging: bool = False,
        max_body_size: int = 10000,
        skip_paths: Optional[List[str]] = None
    ):
        """
        Initialize logging middleware
        
        Args:
            app: ASGI application
            enable_request_body_logging: Whether to log request bodies
            enable_response_body_logging: Whether to log response bodies
            max_body_size: Maximum body size to log
            skip_paths: Paths to skip logging
        """
        super().__init__(app)
        self.enable_request_body_logging = enable_request_body_logging
        self.enable_response_body_logging = enable_response_body_logging
        self.max_body_size = max_body_size
        self.skip_paths = skip_paths or ['/health']
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging"""
        
        # Skip logging for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
            
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Create request log
        request_log = RequestLog(
            request_id=request_id,
            timestamp=datetime.now(),
            method=request.method,
            path=str(request.url.path),
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get('User-Agent')
        )
        
        # Add request ID to headers for response
        request.state.request_id = request_id
        
        # Log request body if enabled
        if self.enable_request_body_logging:
            try:
                body = await request.body()
                if len(body) <= self.max_body_size:
                    request_log.metadata['request_body'] = body.decode('utf-8')
                    request_log.request_size = len(body)
            except Exception as e:
                logger.warning(f"Failed to log request body: {str(e)}")
                
        # Record start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            request_log.response_time_ms = response_time
            request_log.status_code = response.status_code
            
            # Log response body if enabled and not too large
            if self.enable_response_body_logging and hasattr(response, 'body'):
                try:
                    if hasattr(response.body, '__len__') and len(response.body) <= self.max_body_size:
                        request_log.response_size = len(response.body)
                        if isinstance(response.body, bytes):
                            request_log.metadata['response_body'] = response.body.decode('utf-8')
                except Exception as e:
                    logger.warning(f"Failed to log response body: {str(e)}")
                    
            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id
            
            # Log successful request
            logger.info(f"Request completed: {request_log.to_dict()}")
            
            return response
            
        except Exception as e:
            # Log error
            response_time = (time.time() - start_time) * 1000
            request_log.response_time_ms = response_time
            request_log.status_code = 500
            request_log.error = str(e)
            
            logger.error(f"Request failed: {request_log.to_dict()}")
            
            # Re-raise exception
            raise
            
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
            
        forwarded = request.headers.get('X-Forwarded')
        if forwarded:
            return forwarded.split(',')[0].strip()
            
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
            
        # Fall back to client IP
        return request.client.host if request.client else 'unknown'


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for common security headers and protections
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enable_csp: bool = True,
        enable_hsts: bool = True,
        enable_xss_protection: bool = True,
        enable_content_type_nosniff: bool = True
    ):
        """Initialize security middleware"""
        super().__init__(app)
        self.enable_csp = enable_csp
        self.enable_hsts = enable_hsts
        self.enable_xss_protection = enable_xss_protection
        self.enable_content_type_nosniff = enable_content_type_nosniff
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        response = await call_next(request)
        
        # Content Security Policy
        if self.enable_csp:
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https: wss:"
            )
            
        # HTTP Strict Transport Security
        if self.enable_hsts:
            response.headers['Strict-Transport-Security'] = "max-age=31536000; includeSubDomains"
            
        # XSS Protection
        if self.enable_xss_protection:
            response.headers['X-XSS-Protection'] = "1; mode=block"
            
        # Content Type Options
        if self.enable_content_type_nosniff:
            response.headers['X-Content-Type-Options'] = "nosniff"
            
        # Frame Options
        response.headers['X-Frame-Options'] = "DENY"
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers['Permissions-Policy'] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=(), "
            "accelerometer=(), ambient-light-sensor=(), autoplay=()"
        )
        
        return response


class CORSMiddleware(StarletteCorsMidleware):
    """
    Enhanced CORS middleware with additional configuration options
    """
    
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        expose_headers: List[str] = None,
        max_age: int = 600,
        allow_origin_regex: Optional[str] = None
    ):
        """Initialize enhanced CORS middleware"""
        
        # Default secure configuration
        if allow_origins is None:
            allow_origins = []  # Require explicit configuration
            
        if allow_methods is None:
            allow_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD']
            
        if allow_headers is None:
            allow_headers = [
                'Accept',
                'Accept-Language',
                'Content-Language',
                'Content-Type',
                'Authorization',
                'X-Requested-With',
                'X-Request-ID'
            ]
            
        if expose_headers is None:
            expose_headers = [
                'X-Request-ID',
                'X-RateLimit-Limit',
                'X-RateLimit-Remaining',
                'X-RateLimit-Reset'
            ]
            
        super().__init__(
            app,
            allow_origins=allow_origins,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            allow_credentials=allow_credentials,
            expose_headers=expose_headers,
            max_age=max_age,
            allow_origin_regex=allow_origin_regex
        )


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Metrics collection middleware
    
    Collects performance and usage metrics for monitoring.
    """
    
    def __init__(self, app: ASGIApp):
        """Initialize metrics middleware"""
        super().__init__(app)
        self.metrics = {
            'requests_total': 0,
            'requests_by_method': {},
            'requests_by_status': {},
            'response_times': [],
            'active_requests': 0,
            'errors_total': 0
        }
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect metrics for request"""
        start_time = time.time()
        
        # Increment active requests
        self.metrics['active_requests'] += 1
        self.metrics['requests_total'] += 1
        
        # Track requests by method
        method = request.method
        self.metrics['requests_by_method'][method] = self.metrics['requests_by_method'].get(method, 0) + 1
        
        try:
            response = await call_next(request)
            
            # Track response time
            response_time = (time.time() - start_time) * 1000
            self.metrics['response_times'].append(response_time)
            
            # Keep only last 1000 response times
            if len(self.metrics['response_times']) > 1000:
                self.metrics['response_times'] = self.metrics['response_times'][-1000:]
                
            # Track responses by status code
            status_code = response.status_code
            self.metrics['requests_by_status'][status_code] = self.metrics['requests_by_status'].get(status_code, 0) + 1
            
            # Track errors
            if status_code >= 400:
                self.metrics['errors_total'] += 1
                
            return response
            
        except Exception as e:
            self.metrics['errors_total'] += 1
            raise
        finally:
            self.metrics['active_requests'] -= 1
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        response_times = self.metrics['response_times']
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
        else:
            avg_response_time = 0
            p95_response_time = 0
            
        return {
            'requests_total': self.metrics['requests_total'],
            'requests_by_method': self.metrics['requests_by_method'].copy(),
            'requests_by_status': self.metrics['requests_by_status'].copy(),
            'active_requests': self.metrics['active_requests'],
            'errors_total': self.metrics['errors_total'],
            'avg_response_time_ms': avg_response_time,
            'p95_response_time_ms': p95_response_time,
            'timestamp': datetime.now().isoformat()
        }
        
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {
            'requests_total': 0,
            'requests_by_method': {},
            'requests_by_status': {},
            'response_times': [],
            'active_requests': 0,
            'errors_total': 0
        }