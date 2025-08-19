# Kenny Graph SSE Server API Documentation

## Base URL
```
http://localhost:8090
```

## Endpoints

### 1. Server-Sent Events Stream
**GET** `/sse`

Establishes a persistent SSE connection for real-time updates from Kenny Graph.

#### Response Format
```javascript
event: kenny_update
data: {
  "timestamp": "2025-08-18T02:30:00Z",
  "stats": {
    "total_nodes": 89574,
    "total_relationships": 96871,
    "active_agents": 256,
    "memory_usage": "4.2GB"
  },
  "recent_activity": [...]
}
```

#### Example Usage
```javascript
const eventSource = new EventSource('http://localhost:8090/sse');

eventSource.addEventListener('kenny_update', (event) => {
  const data = JSON.parse(event.data);
  console.log('Kenny Graph Update:', data);
});

eventSource.addEventListener('agent_status', (event) => {
  const status = JSON.parse(event.data);
  console.log('Agent Status:', status);
});
```

### 2. Send Message to Kenny
**POST** `/message`

Sends a message/query to Kenny Graph for processing.

#### Request Body
```json
{
  "query": "Your Cypher query or natural language question",
  "type": "cypher|natural",
  "params": {}
}
```

#### Response
```json
{
  "success": true,
  "result": {
    "data": [...],
    "metadata": {
      "execution_time": "23ms",
      "nodes_accessed": 42
    }
  }
}
```

#### Example
```bash
curl -X POST http://localhost:8090/message \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (n:Module) RETURN n.name LIMIT 5",
    "type": "cypher"
  }'
```

### 3. Health Check
**GET** `/health`

Returns server health status.

#### Response
```json
{
  "status": "healthy",
  "uptime": "3h 42m",
  "memgraph_connected": true,
  "active_connections": 12
}
```

### 4. Graph Statistics
**GET** `/stats`

Returns current Kenny Graph statistics.

#### Response
```json
{
  "nodes": {
    "total": 89574,
    "by_label": {
      "Kenny": 1,
      "Module": 48,
      "Agent": 1405,
      "Memory": 12847,
      "Knowledge": 75273
    }
  },
  "relationships": {
    "total": 96871,
    "by_type": {
      "HAS_MODULE": 48,
      "CONNECTS_TO": 5892,
      "KNOWS": 42156,
      "REMEMBERS": 48775
    }
  }
}
```

### 5. Query Kenny Graph
**POST** `/query`

Execute a Cypher query against Kenny Graph.

#### Request Body
```json
{
  "cypher": "MATCH (n:Agent) WHERE n.status = 'active' RETURN n",
  "params": {},
  "limit": 100
}
```

#### Response
```json
{
  "success": true,
  "records": [...],
  "summary": {
    "nodes_created": 0,
    "nodes_deleted": 0,
    "relationships_created": 0,
    "relationships_deleted": 0,
    "properties_set": 0,
    "execution_time_ms": 15
  }
}
```

### 6. Agent Army Status
**GET** `/agents`

Returns status of Kenny's agent army.

#### Response
```json
{
  "total_agents": 1405,
  "active_agents": 256,
  "pools": [
    {
      "name": "vision",
      "size": 32,
      "active": 12,
      "utilization": 37.5
    },
    {
      "name": "language",
      "size": 64,
      "active": 48,
      "utilization": 75.0
    },
    {
      "name": "action",
      "size": 16,
      "active": 8,
      "utilization": 50.0
    },
    {
      "name": "quantum",
      "size": 8,
      "active": 2,
      "utilization": 25.0
    }
  ]
}
```

### 7. WebSocket Upgrade (Alternative to SSE)
**GET** `/ws`

Establishes WebSocket connection for bidirectional communication.

#### Message Format
```json
{
  "type": "query|command|subscribe",
  "payload": {
    ...
  }
}
```

## Error Responses

All endpoints return errors in the following format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Common Error Codes
- `DB_CONNECTION_ERROR`: Cannot connect to Memgraph
- `INVALID_QUERY`: Malformed Cypher query
- `TIMEOUT`: Query execution timeout
- `RATE_LIMIT`: Too many requests
- `UNAUTHORIZED`: Missing or invalid authentication

## Rate Limiting

- Default: 100 requests per minute per IP
- SSE connections: Max 10 concurrent per IP
- WebSocket connections: Max 5 concurrent per IP

## Authentication (Optional)

If authentication is enabled, include API key in headers:

```
Authorization: Bearer YOUR_API_KEY
```

## CORS Configuration

The server allows cross-origin requests from all origins by default. For production, configure allowed origins in the server settings.

## Example Client Implementation

### JavaScript/TypeScript
```javascript
class KennyGraphClient {
  constructor(baseUrl = 'http://localhost:8090') {
    this.baseUrl = baseUrl;
    this.eventSource = null;
  }

  connect() {
    this.eventSource = new EventSource(`${this.baseUrl}/sse`);
    
    this.eventSource.addEventListener('kenny_update', (event) => {
      this.handleUpdate(JSON.parse(event.data));
    });
    
    this.eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      this.reconnect();
    };
  }

  async query(cypher, params = {}) {
    const response = await fetch(`${this.baseUrl}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cypher, params })
    });
    
    return response.json();
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
    }
  }
}
```

### Python
```python
import requests
import sseclient

class KennyGraphClient:
    def __init__(self, base_url='http://localhost:8090'):
        self.base_url = base_url
        
    def stream_updates(self):
        response = requests.get(f'{self.base_url}/sse', stream=True)
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            if event.event == 'kenny_update':
                yield json.loads(event.data)
    
    def query(self, cypher, params=None):
        response = requests.post(
            f'{self.base_url}/query',
            json={'cypher': cypher, 'params': params or {}}
        )
        return response.json()
```

## Performance Tips

1. **Use query parameters** to filter SSE events and reduce bandwidth
2. **Batch queries** when possible to reduce round trips
3. **Cache frequently accessed data** on the client side
4. **Use WebSocket** for bidirectional communication needs
5. **Implement exponential backoff** for reconnection logic

## Monitoring

Monitor the following metrics for optimal performance:
- SSE connection count
- Query response times (p50, p95, p99)
- Memory usage
- Active agent utilization
- Graph query complexity

---

*API Version: 1.0.0*  
*Last Updated: August 18, 2025*