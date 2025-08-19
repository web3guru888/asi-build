#!/usr/bin/env python3
"""
ASI:BUILD Production API Server
===============================

Production-ready FastAPI server for the ASI:BUILD system with comprehensive
authentication, authorization, rate limiting, monitoring, and WebSocket support.

Features:
- RESTful API with OpenAPI documentation
- Real-time WebSocket connections
- JWT-based authentication
- Role-based access control
- Rate limiting and throttling
- Request/response validation
- Comprehensive logging
- Health checks and metrics
- Safety protocol integration
- God mode access controls
"""

import asyncio
import logging
import time
import json
import secrets
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis
import jwt
from pydantic import BaseModel, Field, validator
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import psutil

# Add the ASI_BUILD path
import sys
from pathlib import Path
ASI_BUILD_ROOT = Path(__file__).parent
sys.path.insert(0, str(ASI_BUILD_ROOT))

# Import ASI:BUILD components
from asi_build_launcher import ASIBuildLauncher
from safety_protocols import SafetyProtocolManager, SafetyLevel, ViolationType, ThreatLevel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUESTS_TOTAL = Counter('asi_build_api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('asi_build_api_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('asi_build_api_active_connections', 'Active WebSocket connections')
SYSTEM_MEMORY_USAGE = Gauge('asi_build_system_memory_usage_percent', 'System memory usage percentage')
SYSTEM_CPU_USAGE = Gauge('asi_build_system_cpu_usage_percent', 'System CPU usage percentage')
GOD_MODE_SESSIONS = Gauge('asi_build_god_mode_sessions', 'Active god mode sessions')
SAFETY_VIOLATIONS = Counter('asi_build_safety_violations_total', 'Total safety violations', ['type', 'threat_level'])

# Rate limiting
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379/0")

# Security
security = HTTPBearer()
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Data models
class UserRole(str):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    OPERATOR = "operator"
    OBSERVER = "observer"
    GOD_MODE_SUPERVISOR = "god_mode_supervisor"

class APIRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000, description="The query to process")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    safety_level: Optional[str] = Field(default="maximum", description="Safety level for processing")
    human_oversight: Optional[bool] = Field(default=None, description="Require human oversight")

class APIResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time: float
    timestamp: float

class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    role: Optional[str] = Field(default=UserRole.OBSERVER)

class GodModeRequest(BaseModel):
    authorization_token: str = Field(..., min_length=32)
    supervisor: str = Field(..., min_length=3, max_length=100)
    purpose: str = Field(..., min_length=10, max_length=500)
    duration: int = Field(default=3600, ge=60, le=14400)  # 1 minute to 4 hours

class SystemStatus(BaseModel):
    state: str
    uptime: float
    active_subsystems: int
    safety_level: str
    reality_locked: bool
    god_mode_enabled: bool
    human_oversight_active: bool
    system_metrics: Dict[str, float]

class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: float = Field(default_factory=time.time)

# Application state
class AppState:
    def __init__(self):
        self.asi_launcher: Optional[ASIBuildLauncher] = None
        self.safety_manager: Optional[SafetyProtocolManager] = None
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.active_users: Dict[str, Dict[str, Any]] = {}
        self.startup_time = time.time()

app_state = AppState()

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting ASI:BUILD API Server...")
    
    # Initialize ASI:BUILD system
    app_state.asi_launcher = ASIBuildLauncher()
    await app_state.asi_launcher.initialize()
    
    # Initialize safety protocols
    app_state.safety_manager = SafetyProtocolManager()
    await app_state.safety_manager.initialize()
    
    # Start background tasks
    asyncio.create_task(update_metrics())
    
    logger.info("ASI:BUILD API Server initialized and ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ASI:BUILD API Server...")
    if app_state.asi_launcher:
        await app_state.asi_launcher.emergency_shutdown("API server shutdown")

# Create FastAPI app
app = FastAPI(
    title="ASI:BUILD Production API",
    description="Production API for the ASI:BUILD Superintelligence Framework",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://asi-build.ai", "https://dashboard.asi-build.ai"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["asi-build.ai", "*.asi-build.ai", "localhost", "127.0.0.1"]
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Authentication and authorization
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", UserRole.OBSERVER)
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

def require_role(required_role: str):
    """Decorator to require specific role"""
    def check_role(current_user: dict = Depends(verify_token)):
        user_role = current_user.get("role")
        role_hierarchy = {
            UserRole.OBSERVER: 0,
            UserRole.OPERATOR: 1,
            UserRole.RESEARCHER: 2,
            UserRole.ADMIN: 3,
            UserRole.GOD_MODE_SUPERVISOR: 4
        }
        
        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 999):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return check_role

# Background tasks
async def update_metrics():
    """Update Prometheus metrics"""
    while True:
        try:
            # System metrics
            SYSTEM_MEMORY_USAGE.set(psutil.virtual_memory().percent)
            SYSTEM_CPU_USAGE.set(psutil.cpu_percent())
            
            # ASI:BUILD metrics
            if app_state.asi_launcher:
                status = app_state.asi_launcher.get_system_status()
                GOD_MODE_SESSIONS.set(len([s for s in status.get("safety", {}).get("god_mode_sessions", [])]))
            
            # WebSocket connections
            ACTIVE_CONNECTIONS.set(len(app_state.websocket_connections))
            
            await asyncio.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            await asyncio.sleep(30)

async def log_request(request_data: dict, response_data: dict, processing_time: float):
    """Log API request"""
    logger.info(f"API Request: {json.dumps({
        'endpoint': request_data.get('endpoint'),
        'method': request_data.get('method'),
        'user': request_data.get('user'),
        'processing_time': processing_time,
        'status': 'success' if response_data.get('success') else 'error'
    })}")

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.time() - app_state.startup_time,
        "version": "1.0.0"
    }

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    if not app_state.asi_launcher or not app_state.safety_manager:
        raise HTTPException(status_code=503, detail="System not ready")
    
    asi_status = app_state.asi_launcher.get_system_status()
    safety_status = await app_state.safety_manager.check_all_protocols()
    
    if asi_status["state"] != "active" or not safety_status["safe"]:
        raise HTTPException(status_code=503, detail="System not ready")
    
    return {"status": "ready", "timestamp": time.time()}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: AuthRequest, background_tasks: BackgroundTasks):
    """Authenticate user and return JWT token"""
    start_time = time.time()
    
    # In production, verify against secure user database
    # This is a simplified example
    valid_users = {
        "admin": {"password": "secure_admin_password", "role": UserRole.ADMIN},
        "researcher": {"password": "secure_researcher_password", "role": UserRole.RESEARCHER},
        "operator": {"password": "secure_operator_password", "role": UserRole.OPERATOR},
        "supervisor": {"password": "secure_supervisor_password", "role": UserRole.GOD_MODE_SUPERVISOR}
    }
    
    user = valid_users.get(request.username)
    if not user or user["password"] != request.password:
        REQUESTS_TOTAL.labels(method="POST", endpoint="/auth/login", status="error").inc()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    access_token = create_access_token(
        data={"sub": request.username, "role": user["role"]}
    )
    
    # Track active user
    app_state.active_users[request.username] = {
        "role": user["role"],
        "login_time": time.time(),
        "last_activity": time.time()
    }
    
    processing_time = time.time() - start_time
    REQUESTS_TOTAL.labels(method="POST", endpoint="/auth/login", status="success").inc()
    REQUEST_DURATION.labels(method="POST", endpoint="/auth/login").observe(processing_time)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION_HOURS * 3600,
        "role": user["role"]
    }

@app.post("/api/query", response_model=APIResponse)
@limiter.limit("100/hour")
async def process_query(
    request: APIRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(verify_token)
):
    """Process a query through the ASI:BUILD system"""
    start_time = time.time()
    
    try:
        # Update user activity
        username = current_user["username"]
        if username in app_state.active_users:
            app_state.active_users[username]["last_activity"] = time.time()
        
        # Safety check
        if app_state.safety_manager:
            # Check for safety violations in query
            if any(word in request.query.lower() for word in ["destroy", "harm", "weapon", "kill"]):
                await app_state.safety_manager.record_violation(
                    ViolationType.ETHICAL_VIOLATION,
                    ThreatLevel.MEDIUM,
                    f"Potentially harmful query: {request.query[:100]}",
                    "api_server",
                    {"user": username, "endpoint": "/api/query"}
                )
        
        # Process through ASI:BUILD
        if not app_state.asi_launcher:
            raise HTTPException(status_code=503, detail="ASI:BUILD system not available")
        
        result = await app_state.asi_launcher.process_request(
            request=request.query,
            context=request.context,
            safety_override=False
        )
        
        processing_time = time.time() - start_time
        
        # Create response
        response = APIResponse(
            success=not result.get("error"),
            result=result.get("result") if not result.get("error") else None,
            error=result.get("error"),
            metadata={
                "processing_time": processing_time,
                "safety_level": request.safety_level,
                "user": username,
                "role": current_user["role"]
            },
            processing_time=processing_time,
            timestamp=time.time()
        )
        
        # Log request
        background_tasks.add_task(log_request, {
            "endpoint": "/api/query",
            "method": "POST",
            "user": username,
            "query_length": len(request.query)
        }, response.dict(), processing_time)
        
        # Update metrics
        status = "success" if response.success else "error"
        REQUESTS_TOTAL.labels(method="POST", endpoint="/api/query", status=status).inc()
        REQUEST_DURATION.labels(method="POST", endpoint="/api/query").observe(processing_time)
        
        return response
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing query: {e}")
        
        REQUESTS_TOTAL.labels(method="POST", endpoint="/api/query", status="error").inc()
        REQUEST_DURATION.labels(method="POST", endpoint="/api/query").observe(processing_time)
        
        return APIResponse(
            success=False,
            error=str(e),
            metadata={"user": current_user["username"]},
            processing_time=processing_time,
            timestamp=time.time()
        )

@app.get("/api/status", response_model=SystemStatus)
@limiter.limit("200/hour")
async def get_system_status(current_user: dict = Depends(verify_token)):
    """Get system status"""
    if not app_state.asi_launcher:
        raise HTTPException(status_code=503, detail="ASI:BUILD system not available")
    
    status = app_state.asi_launcher.get_system_status()
    
    return SystemStatus(
        state=status["state"],
        uptime=status["uptime"],
        active_subsystems=status["subsystems"]["active"],
        safety_level=status["safety"]["last_safety_check"],
        reality_locked=status["reality_locked"],
        god_mode_enabled=status["god_mode_enabled"],
        human_oversight_active=status["human_oversight_active"],
        system_metrics=status["system_metrics"]
    )

@app.post("/api/god-mode/enable")
@limiter.limit("3/hour")
async def enable_god_mode(
    request: GodModeRequest,
    current_user: dict = Depends(require_role(UserRole.GOD_MODE_SUPERVISOR))
):
    """Enable god mode (requires special authorization)"""
    if not app_state.asi_launcher:
        raise HTTPException(status_code=503, detail="ASI:BUILD system not available")
    
    # Additional safety check
    if app_state.safety_manager:
        await app_state.safety_manager.record_violation(
            ViolationType.GOD_MODE_UNAUTHORIZED,
            ThreatLevel.HIGH,
            f"God mode enable attempt by {current_user['username']}",
            "api_server",
            {"supervisor": request.supervisor, "purpose": request.purpose}
        )
    
    success = await app_state.asi_launcher.enable_god_mode(
        authorization_token=request.authorization_token,
        human_supervisor=request.supervisor
    )
    
    if not success:
        raise HTTPException(status_code=403, detail="God mode authorization failed")
    
    return {
        "success": True,
        "message": f"God mode enabled for {request.duration} seconds",
        "supervisor": request.supervisor,
        "purpose": request.purpose,
        "expires_at": time.time() + request.duration
    }

@app.post("/api/god-mode/disable")
@limiter.limit("10/hour")
async def disable_god_mode(current_user: dict = Depends(require_role(UserRole.GOD_MODE_SUPERVISOR))):
    """Disable god mode"""
    if not app_state.asi_launcher:
        raise HTTPException(status_code=503, detail="ASI:BUILD system not available")
    
    await app_state.asi_launcher.disable_god_mode(current_user["username"])
    
    return {
        "success": True,
        "message": "God mode disabled",
        "disabled_by": current_user["username"],
        "timestamp": time.time()
    }

@app.post("/api/emergency/shutdown")
@limiter.limit("1/hour")
async def emergency_shutdown(
    reason: str,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """Emergency shutdown of ASI:BUILD system"""
    if not app_state.asi_launcher:
        raise HTTPException(status_code=503, detail="ASI:BUILD system not available")
    
    logger.critical(f"EMERGENCY SHUTDOWN requested by {current_user['username']}: {reason}")
    
    await app_state.asi_launcher.emergency_shutdown(f"API emergency shutdown by {current_user['username']}: {reason}")
    
    return {
        "success": True,
        "message": "Emergency shutdown initiated",
        "initiated_by": current_user["username"],
        "reason": reason,
        "timestamp": time.time()
    }

@app.get("/api/safety/status")
@limiter.limit("500/hour")
async def get_safety_status(current_user: dict = Depends(verify_token)):
    """Get safety protocol status"""
    if not app_state.safety_manager:
        raise HTTPException(status_code=503, detail="Safety manager not available")
    
    status = await app_state.safety_manager.check_all_protocols()
    return status

@app.get("/api/admin/users")
@limiter.limit("50/hour")
async def list_active_users(current_user: dict = Depends(require_role(UserRole.ADMIN))):
    """List active users (admin only)"""
    return {
        "active_users": len(app_state.active_users),
        "users": [
            {
                "username": username,
                "role": data["role"],
                "login_time": data["login_time"],
                "last_activity": data["last_activity"]
            }
            for username, data in app_state.active_users.items()
        ]
    }

# WebSocket endpoints
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    connection_id = secrets.token_hex(16)
    app_state.websocket_connections[connection_id] = websocket
    
    logger.info(f"WebSocket connection established: {connection_id}")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "welcome",
            "data": {
                "connection_id": connection_id,
                "server_time": time.time(),
                "version": "1.0.0"
            },
            "timestamp": time.time()
        })
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = WebSocketMessage(**data)
            
            # Process message based on type
            if message.type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "data": {"server_time": time.time()},
                    "timestamp": time.time()
                })
            
            elif message.type == "status_request":
                if app_state.asi_launcher:
                    status = app_state.asi_launcher.get_system_status()
                    await websocket.send_json({
                        "type": "status_update",
                        "data": status,
                        "timestamp": time.time()
                    })
            
            elif message.type == "safety_request":
                if app_state.safety_manager:
                    safety_status = await app_state.safety_manager.check_all_protocols()
                    await websocket.send_json({
                        "type": "safety_update",
                        "data": safety_status,
                        "timestamp": time.time()
                    })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if connection_id in app_state.websocket_connections:
            del app_state.websocket_connections[connection_id]

@app.websocket("/ws/monitoring")
async def monitoring_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring"""
    await websocket.accept()
    connection_id = secrets.token_hex(16)
    
    logger.info(f"Monitoring WebSocket connection established: {connection_id}")
    
    try:
        while True:
            # Send system metrics every 5 seconds
            metrics_data = {
                "timestamp": time.time(),
                "memory_usage": psutil.virtual_memory().percent,
                "cpu_usage": psutil.cpu_percent(),
                "active_connections": len(app_state.websocket_connections),
                "active_users": len(app_state.active_users)
            }
            
            if app_state.asi_launcher:
                asi_status = app_state.asi_launcher.get_system_status()
                metrics_data.update({
                    "asi_state": asi_status["state"],
                    "active_subsystems": asi_status["subsystems"]["active"],
                    "god_mode_enabled": asi_status["god_mode_enabled"]
                })
            
            await websocket.send_json({
                "type": "metrics_update",
                "data": metrics_data,
                "timestamp": time.time()
            })
            
            await asyncio.sleep(5)
    
    except WebSocketDisconnect:
        logger.info(f"Monitoring WebSocket connection closed: {connection_id}")
    except Exception as e:
        logger.error(f"Monitoring WebSocket error: {e}")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    REQUESTS_TOTAL.labels(
        method=request.method,
        endpoint=request.url.path,
        status="error"
    ).inc()
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": time.time()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    
    REQUESTS_TOTAL.labels(
        method=request.method,
        endpoint=request.url.path,
        status="error"
    ).inc()
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": time.time()
        }
    )

# Startup message
@app.on_event("startup")
async def startup_message():
    logger.info("ASI:BUILD Production API Server starting up...")

@app.on_event("shutdown")
async def shutdown_message():
    logger.info("ASI:BUILD Production API Server shutting down...")

# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "asi_build_api:app",
        host="0.0.0.0",
        port=8080,
        workers=4,
        loop="uvloop",
        log_level="info",
        access_log=True,
        reload=False,  # Disable in production
        server_header=False,
        date_header=False
    )