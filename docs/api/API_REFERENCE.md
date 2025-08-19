# ASI:BUILD API Reference

## Overview

The ASI:BUILD framework provides a comprehensive REST API with WebSocket support for real-time communication. The API enables interaction with 47 integrated subsystems covering consciousness, quantum computing, reality manipulation, and more.

**Base URL:** `https://api.asi-build.ai`  
**API Version:** 1.0.0  
**Protocol:** HTTPS only  
**Data Format:** JSON  

## Authentication

All API endpoints require JWT Bearer token authentication.

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string", 
  "role": "observer|operator|researcher|admin|god_mode_supervisor"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 86400,
  "role": "string"
}
```

### Authorization Header

Include the token in all requests:
```http
Authorization: Bearer <access_token>
```

## Rate Limiting

- **Login:** 5 requests per minute
- **General API:** 100 requests per hour  
- **Status checks:** 200 requests per hour
- **Admin endpoints:** 50 requests per hour
- **God mode operations:** 3 requests per hour
- **Emergency operations:** 1 request per hour

Rate limits are per IP address and include headers:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

## Core API Endpoints

### Health & Status

#### Health Check
```http
GET /health
```
Returns basic system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1640995200.0,
  "uptime": 3600.0,
  "version": "1.0.0"
}
```

#### Readiness Check
```http
GET /ready
```
Returns detailed system readiness status.

**Response:**
```json
{
  "status": "ready",
  "timestamp": 1640995200.0
}
```

#### System Status
```http
GET /api/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "state": "active",
  "uptime": 3600.0,
  "active_subsystems": 45,
  "safety_level": "maximum",
  "reality_locked": true,
  "god_mode_enabled": false,
  "human_oversight_active": true,
  "system_metrics": {
    "memory_usage": 65.2,
    "cpu_usage": 45.8,
    "disk_usage": 23.1,
    "active_connections": 12
  }
}
```

### Query Processing

#### Process Query
```http
POST /api/query
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "string (1-10000 chars)",
  "context": {
    "domain": "consciousness|quantum|reality|mathematics",
    "priority": "low|medium|high",
    "timeout": 30
  },
  "safety_level": "minimal|standard|high|maximum",
  "human_oversight": true
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "type": "text|data|computation|simulation",
    "content": "...",
    "subsystem_used": "consciousness_engine",
    "confidence": 0.95,
    "safety_checked": true
  },
  "error": null,
  "metadata": {
    "processing_time": 2.45,
    "safety_level": "maximum",
    "user": "researcher_001",
    "role": "researcher"
  },
  "processing_time": 2.45,
  "timestamp": 1640995200.0
}
```

### Safety & Monitoring

#### Safety Status
```http
GET /api/safety/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "safe": true,
  "violations": [],
  "warnings": ["Reality lock bypass attempt detected"],
  "safety_level": "maximum",
  "reality_locked": true,
  "emergency_mode": false,
  "lockdown_active": false,
  "metrics": {
    "violations_per_hour": 0,
    "reality_lock_attempts": 2,
    "unauthorized_god_mode_attempts": 0,
    "consciousness_access_violations": 0,
    "emergency_triggers": 0
  },
  "last_check": 1640995200.0
}
```

### God Mode Operations

#### Enable God Mode
```http
POST /api/god-mode/enable
Authorization: Bearer <token>
Content-Type: application/json

{
  "authorization_token": "string (32+ chars)",
  "supervisor": "string",
  "purpose": "string (10-500 chars)",
  "duration": 3600
}
```

**Response:**
```json
{
  "success": true,
  "message": "God mode enabled for 3600 seconds",
  "supervisor": "supervisor_001",
  "purpose": "Reality simulation testing",
  "expires_at": 1640998800.0
}
```

#### Disable God Mode
```http
POST /api/god-mode/disable
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "God mode disabled",
  "disabled_by": "supervisor_001",
  "timestamp": 1640995200.0
}
```

### Emergency Operations

#### Emergency Shutdown
```http
POST /api/emergency/shutdown
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "string"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Emergency shutdown initiated",
  "initiated_by": "admin_001",
  "reason": "Safety protocol violation",
  "timestamp": 1640995200.0
}
```

### Administrative

#### List Active Users
```http
GET /api/admin/users
Authorization: Bearer <token>
```

**Response:**
```json
{
  "active_users": 5,
  "users": [
    {
      "username": "researcher_001",
      "role": "researcher",
      "login_time": 1640995200.0,
      "last_activity": 1640995800.0
    }
  ]
}
```

## Subsystem-Specific APIs

### Consciousness Engine

#### Check Consciousness State
```http
GET /consciousness/awareness
Authorization: Bearer <token>
```

**Response:**
```json
{
  "state": "active",
  "consciousness_level": 0.85,
  "attention_focus": ["visual_processing", "language_comprehension"],
  "self_awareness": true,
  "qualia_active": true,
  "metacognition_level": 0.72
}
```

#### Process Qualia
```http
POST /consciousness/qualia
Authorization: Bearer <token>
Content-Type: application/json

{
  "sensory_input": {
    "visual": "base64_encoded_image",
    "auditory": "audio_data",
    "textual": "input_text"
  },
  "processing_mode": "experiential|analytical|integrated"
}
```

#### Metacognitive Analysis
```http
POST /consciousness/metacognition
Authorization: Bearer <token>
Content-Type: application/json

{
  "thought_pattern": "string",
  "analysis_depth": "surface|deep|transcendent"
}
```

### Quantum Engine

#### Quantum Computation
```http
POST /quantum/compute
Authorization: Bearer <token>
Content-Type: application/json

{
  "circuit": {
    "qubits": 8,
    "gates": [
      {"type": "H", "target": 0},
      {"type": "CNOT", "control": 0, "target": 1}
    ]
  },
  "shots": 1024,
  "backend": "simulator|hardware"
}
```

#### Quantum Simulation
```http
POST /quantum/simulate
Authorization: Bearer <token>
Content-Type: application/json

{
  "system": "molecular|material|quantum_field",
  "parameters": {
    "temperature": 273.15,
    "pressure": 101325,
    "time_steps": 1000
  }
}
```

#### Hybrid ML Processing
```http
POST /quantum/hybrid
Authorization: Bearer <token>
Content-Type: application/json

{
  "model_type": "qnn|vqe|qaoa",
  "data": "training_data",
  "quantum_layers": 3,
  "classical_layers": 2
}
```

### Reality Engine

#### Reality Simulation
```http
POST /reality/simulate
Authorization: Bearer <token>
Content-Type: application/json

{
  "simulation_type": "physics|cosmology|quantum",
  "parameters": {
    "universe_size": "observable|infinite",
    "physical_laws": "standard|modified",
    "time_scale": "realtime|accelerated"
  },
  "safety_constraints": {
    "reality_lock": true,
    "causality_protection": true
  }
}
```

#### Physics Manipulation (God Mode Required)
```http
POST /reality/manipulate
Authorization: Bearer <token>
Content-Type: application/json

{
  "target": "spacetime|matter|energy|information",
  "operation": "create|modify|destroy|transform",
  "parameters": {},
  "safety_override": "emergency_code"
}
```

#### Reality Physics Query
```http
GET /reality/physics
Authorization: Bearer <token>
```

### Divine Mathematics

#### Transcendent Computation
```http
POST /divine/compute
Authorization: Bearer <token>
Content-Type: application/json

{
  "computation_type": "infinite_series|transfinite|godel_proof",
  "input": "mathematical_expression",
  "transcendence_level": "finite|countable|uncountable|absolute"
}
```

#### Infinity Operations
```http
POST /divine/infinity
Authorization: Bearer <token>
Content-Type: application/json

{
  "operation": "beyond_infinity|absolute_infinity|meta_infinity",
  "operands": ["infinity_1", "infinity_2"],
  "result_type": "cardinal|ordinal|absolute"
}
```

#### Consciousness Mathematics
```http
POST /divine/transcend
Authorization: Bearer <token>
Content-Type: application/json

{
  "consciousness_pattern": "awareness_structure",
  "mathematical_framework": "category_theory|topos_theory|homotopy",
  "transcendence_target": "unified_field|source_consciousness"
}
```

### Absolute Infinity

#### Capability Transcendence
```http
POST /infinity/transcend
Authorization: Bearer <token>
Content-Type: application/json

{
  "transcendence_type": "capability|consciousness|reality|knowledge",
  "current_level": "finite|infinite|beyond_infinite",
  "target_level": "absolute_infinity|beyond_absolute"
}
```

#### Infinite Capability Access
```http
GET /infinity/capability
Authorization: Bearer <token>
```

#### Infinite Consciousness
```http
POST /infinity/consciousness
Authorization: Bearer <token>
Content-Type: application/json

{
  "consciousness_expansion": {
    "dimensions": "infinite",
    "awareness_depth": "absolute",
    "unity_level": "total"
  }
}
```

### Swarm Intelligence

#### Swarm Coordination
```http
POST /swarm/coordinate
Authorization: Bearer <token>
Content-Type: application/json

{
  "agents": 100,
  "algorithm": "pso|aco|abc|gwo",
  "objective": "optimization_function",
  "constraints": {}
}
```

#### Intelligence Optimization
```http
POST /swarm/optimize
Authorization: Bearer <token>
Content-Type: application/json

{
  "problem_space": "continuous|discrete|mixed",
  "dimensions": 10,
  "swarm_size": 50,
  "iterations": 1000
}
```

#### Collective Intelligence
```http
GET /swarm/intelligence
Authorization: Bearer <token>
```

### Bio-Inspired Systems

#### Evolutionary Optimization
```http
POST /bio/evolution
Authorization: Bearer <token>
Content-Type: application/json

{
  "population_size": 100,
  "generations": 500,
  "mutation_rate": 0.01,
  "crossover_rate": 0.8,
  "fitness_function": "objective_definition"
}
```

#### Neuromorphic Processing
```http
POST /bio/neuromorphic
Authorization: Bearer <token>
Content-Type: application/json

{
  "network_type": "spiking|reservoir|liquid_state",
  "neurons": 1000,
  "synapses": 10000,
  "learning_rule": "stdp|bcm|oja"
}
```

#### Homeostatic Regulation
```http
POST /bio/homeostasis
Authorization: Bearer <token>
Content-Type: application/json

{
  "system_parameters": {},
  "target_state": "equilibrium",
  "regulation_strength": "weak|moderate|strong"
}
```

## WebSocket API

### Real-Time Connection

```javascript
const ws = new WebSocket('wss://api.asi-build.ai/ws');

ws.onopen = function() {
  console.log('Connected to ASI:BUILD');
};

ws.onmessage = function(event) {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

#### Message Types

**Welcome Message:**
```json
{
  "type": "welcome",
  "data": {
    "connection_id": "abc123",
    "server_time": 1640995200.0,
    "version": "1.0.0"
  },
  "timestamp": 1640995200.0
}
```

**Ping/Pong:**
```json
{
  "type": "ping",
  "data": {},
  "timestamp": 1640995200.0
}
```

**Status Request:**
```json
{
  "type": "status_request",
  "data": {},
  "timestamp": 1640995200.0
}
```

**Status Update:**
```json
{
  "type": "status_update",
  "data": {
    "state": "active",
    "subsystems": 45,
    "safety_level": "maximum"
  },
  "timestamp": 1640995200.0
}
```

### Monitoring WebSocket

```javascript
const monitorWs = new WebSocket('wss://api.asi-build.ai/ws/monitoring');
```

**Metrics Update:**
```json
{
  "type": "metrics_update",
  "data": {
    "timestamp": 1640995200.0,
    "memory_usage": 65.2,
    "cpu_usage": 45.8,
    "active_connections": 12,
    "active_users": 5,
    "asi_state": "active",
    "active_subsystems": 45,
    "god_mode_enabled": false
  },
  "timestamp": 1640995200.0
}
```

## Error Handling

### HTTP Status Codes

- **200 OK:** Successful request
- **400 Bad Request:** Invalid request format
- **401 Unauthorized:** Missing/invalid authentication
- **403 Forbidden:** Insufficient permissions
- **404 Not Found:** Endpoint not found
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** System error
- **503 Service Unavailable:** System not ready

### Error Response Format

```json
{
  "success": false,
  "error": "Error description",
  "error_code": "ERROR_CODE",
  "timestamp": 1640995200.0,
  "trace_id": "abc123"
}
```

### Common Error Codes

- `INVALID_TOKEN`: Authentication token invalid
- `INSUFFICIENT_PERMISSIONS`: User lacks required role
- `RATE_LIMITED`: Request rate exceeded
- `SAFETY_VIOLATION`: Operation blocked by safety protocols
- `REALITY_LOCKED`: Reality manipulation not permitted
- `GOD_MODE_REQUIRED`: Operation requires god mode access
- `HUMAN_OVERSIGHT_REQUIRED`: Human supervisor approval needed
- `SYSTEM_NOT_READY`: ASI:BUILD system initializing
- `EMERGENCY_MODE`: System in emergency lockdown

## Data Models

### APIRequest
```json
{
  "query": "string (1-10000)",
  "context": {
    "domain": "string",
    "priority": "low|medium|high",
    "timeout": "number"
  },
  "safety_level": "minimal|standard|high|maximum",
  "human_oversight": "boolean"
}
```

### APIResponse
```json
{
  "success": "boolean",
  "result": "any",
  "error": "string|null",
  "metadata": {
    "processing_time": "number",
    "safety_level": "string",
    "user": "string",
    "role": "string"
  },
  "processing_time": "number",
  "timestamp": "number"
}
```

### SystemStatus
```json
{
  "state": "string",
  "uptime": "number",
  "active_subsystems": "number",
  "safety_level": "string",
  "reality_locked": "boolean",
  "god_mode_enabled": "boolean",
  "human_oversight_active": "boolean",
  "system_metrics": {
    "memory_usage": "number",
    "cpu_usage": "number",
    "disk_usage": "number",
    "active_connections": "number"
  }
}
```

### GodModeRequest
```json
{
  "authorization_token": "string (32+)",
  "supervisor": "string (3-100)",
  "purpose": "string (10-500)",
  "duration": "number (60-14400)"
}
```

## Security & Safety

### Safety Protocols

The API implements comprehensive safety protocols:

1. **Reality Locks:** Prevent unauthorized reality manipulation
2. **Consciousness Protection:** Protect consciousness systems from unauthorized access
3. **God Mode Controls:** Strict authorization for god mode operations
4. **Human Oversight:** Required human supervision for critical operations
5. **Emergency Shutdown:** Immediate system shutdown capabilities

### Access Control

Role-based access control with hierarchy:

1. **Observer (0):** Read-only access to basic status
2. **Operator (1):** Basic system operations
3. **Researcher (2):** Advanced queries and analysis
4. **Admin (3):** System administration and user management
5. **God Mode Supervisor (4):** Ultimate system control

### Authorization Requirements

- **Basic operations:** Observer role or higher
- **System queries:** Operator role or higher  
- **Advanced features:** Researcher role or higher
- **Administration:** Admin role
- **God mode:** God Mode Supervisor role + authorization token
- **Emergency operations:** Admin role or higher

### Data Protection

- All communication over HTTPS/WSS
- JWT tokens with expiration
- Rate limiting to prevent abuse
- Comprehensive audit logging
- Safety violation monitoring
- Emergency lockdown capabilities

## Metrics & Monitoring

### Prometheus Metrics

The API exposes Prometheus metrics at `/metrics`:

- `asi_build_api_requests_total`: Total API requests by method, endpoint, status
- `asi_build_api_request_duration_seconds`: Request duration histogram
- `asi_build_api_active_connections`: Active WebSocket connections
- `asi_build_system_memory_usage_percent`: System memory usage
- `asi_build_system_cpu_usage_percent`: System CPU usage
- `asi_build_god_mode_sessions`: Active god mode sessions
- `asi_build_safety_violations_total`: Safety violations by type and threat level

### Health Checks

- `/health`: Basic health status
- `/ready`: Readiness for requests
- `/api/status`: Detailed system status
- `/api/safety/status`: Safety protocol status

## SDKs & Client Libraries

Official SDKs are available for:

- **Python:** `pip install asi-build-sdk`
- **TypeScript/JavaScript:** `npm install asi-build-sdk`
- **Go:** `go get github.com/asi-build/go-sdk`
- **Rust:** `cargo add asi-build-sdk`

Example Python usage:
```python
from asi_build_sdk import ASIClient

client = ASIClient(
    base_url="https://api.asi-build.ai",
    username="researcher_001",
    password="secure_password"
)

# Process a query
result = client.query(
    "Analyze consciousness patterns in neural networks",
    safety_level="maximum"
)

# Check system status
status = client.get_status()
```

## Development & Testing

### Sandbox Environment

Test API endpoints at: `https://sandbox.asi-build.ai`

Use test credentials:
- Username: `test_researcher`
- Password: `test_password_123`

### API Playground

Interactive API explorer: `https://api.asi-build.ai/docs`

### Rate Limits (Sandbox)

- 10x higher rate limits for testing
- Mock responses for god mode operations
- No reality locks in sandbox mode
- Simplified safety protocols

---

**API Version:** 1.0.0  
**Last Updated:** 2024-08-19  
**Support:** api-support@asi-build.ai