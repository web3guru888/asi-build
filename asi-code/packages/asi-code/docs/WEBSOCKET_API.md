# ASI-Code WebSocket API Documentation

## Overview

ASI-Code provides comprehensive WebSocket support for real-time communication, enabling features like:

- **AI Response Streaming**: Real-time streaming of AI model responses
- **Tool Execution Updates**: Live progress updates for tool executions
- **Channel/Room Support**: Multi-user communication channels
- **Event Subscriptions**: Subscribe to system and custom events
- **Message Queuing**: Reliable message delivery with retry mechanisms
- **Binary Message Support**: Efficient transfer of binary data
- **Compression**: Automatic compression for large messages
- **Authentication**: Secure WebSocket connections
- **Rate Limiting**: Protection against message flooding
- **Auto-Reconnection**: Client-side reconnection with exponential backoff

## Connection

### Endpoint
```
ws://localhost:3000/ws
wss://your-domain.com/ws  (for SSL)
```

### Connection Flow
1. Client initiates WebSocket connection
2. Server sends `connection:ready` message with capabilities
3. Client can optionally authenticate with `connection:auth`
4. Normal message exchange begins

## Message Format

All WebSocket messages follow this JSON schema:

```typescript
interface WSMessage {
  id: string;           // Unique message identifier
  type: string;         // Message type (see Message Types below)
  timestamp: number;    // Unix timestamp in milliseconds
  data?: any;          // Message-specific payload
  metadata?: Record<string, any>; // Optional metadata
}
```

### Example Message
```json
{
  "id": "msg_12345",
  "type": "connection:ping",
  "timestamp": 1642425600000,
  "data": {
    "timestamp": 1642425600000
  }
}
```

## Message Types

### Connection Management

#### `connection:ready`
**Direction**: Server → Client  
**Description**: Sent when connection is established  
```json
{
  "id": "ready_001",
  "type": "connection:ready",
  "timestamp": 1642425600000,
  "data": {
    "connectionId": "conn_abc123",
    "capabilities": ["messaging", "channels", "heartbeat", "compression"],
    "maxMessageSize": 1048576,
    "heartbeatInterval": 30000
  }
}
```

#### `connection:auth`
**Direction**: Client → Server  
**Description**: Authenticate the connection  
```json
{
  "id": "auth_001",
  "type": "connection:auth",
  "timestamp": 1642425600000,
  "data": {
    "token": "jwt_token_here",
    "sessionId": "session_123",
    "userId": "user_456"
  }
}
```

#### `connection:ping` / `connection:pong`
**Description**: Heartbeat mechanism  
```json
// Ping (Client → Server)
{
  "id": "ping_001",
  "type": "connection:ping",
  "timestamp": 1642425600000,
  "data": {
    "timestamp": 1642425600000
  }
}

// Pong (Server → Client)
{
  "id": "pong_001",
  "type": "connection:pong",
  "timestamp": 1642425600100,
  "data": {
    "timestamp": 1642425600100,
    "latency": 100
  }
}
```

### Channel/Room Management

#### `channel:join`
**Direction**: Client → Server  
**Description**: Join a communication channel  
```json
{
  "id": "join_001",
  "type": "channel:join",
  "timestamp": 1642425600000,
  "data": {
    "channel": "general",
    "password": "optional_password"
  }
}
```

#### `channel:leave`
**Direction**: Client → Server  
**Description**: Leave a channel  
```json
{
  "id": "leave_001",
  "type": "channel:leave",
  "timestamp": 1642425600000,
  "data": {
    "channel": "general"
  }
}
```

#### `channel:message`
**Description**: Send or receive channel messages  
```json
// Send (Client → Server)
{
  "id": "msg_001",
  "type": "channel:message",
  "timestamp": 1642425600000,
  "data": {
    "channel": "general",
    "message": "Hello everyone!"
  }
}

// Receive (Server → Client)
{
  "id": "msg_002",
  "type": "channel:message",
  "timestamp": 1642425600000,
  "data": {
    "channel": "general",
    "message": "Hello everyone!",
    "sender": "user_123"
  }
}
```

### Event Subscriptions

#### `subscription:subscribe`
**Direction**: Client → Server  
**Description**: Subscribe to events  
```json
{
  "id": "sub_001",
  "type": "subscription:subscribe",
  "timestamp": 1642425600000,
  "data": {
    "event": "user-activity",
    "filter": {
      "userId": "user_123"
    },
    "options": {
      "includeHistory": true,
      "maxHistory": 10
    }
  }
}
```

#### `subscription:unsubscribe`
**Direction**: Client → Server  
**Description**: Unsubscribe from events  
```json
{
  "id": "unsub_001",
  "type": "subscription:unsubscribe",
  "timestamp": 1642425600000,
  "data": {
    "event": "user-activity"
  }
}
```

#### `subscription:event`
**Direction**: Server → Client  
**Description**: Event notification  
```json
{
  "id": "event_001",
  "type": "subscription:event",
  "timestamp": 1642425600000,
  "data": {
    "event": "user-activity",
    "payload": {
      "userId": "user_123",
      "action": "login",
      "timestamp": 1642425600000
    },
    "source": "auth-service"
  }
}
```

### AI Streaming

#### `ai:stream:start`
**Direction**: Client → Server  
**Description**: Start AI response streaming  
```json
{
  "id": "ai_start_001",
  "type": "ai:stream:start",
  "timestamp": 1642425600000,
  "data": {
    "requestId": "req_123",
    "provider": "anthropic",
    "model": "claude-3-sonnet",
    "prompt": "Explain quantum computing",
    "options": {
      "temperature": 0.7,
      "maxTokens": 1000
    }
  }
}
```

#### `ai:stream:chunk`
**Direction**: Server → Client  
**Description**: Streaming chunk of AI response  
```json
{
  "id": "ai_chunk_001",
  "type": "ai:stream:chunk",
  "timestamp": 1642425600000,
  "data": {
    "requestId": "req_123",
    "chunk": "Quantum computing is a revolutionary approach",
    "index": 0,
    "finished": false,
    "usage": {
      "tokens": 8
    }
  }
}
```

#### `ai:stream:end`
**Direction**: Server → Client  
**Description**: AI streaming completed  
```json
{
  "id": "ai_end_001",
  "type": "ai:stream:end",
  "timestamp": 1642425600000,
  "data": {
    "requestId": "req_123",
    "totalChunks": 25,
    "totalTokens": 150,
    "duration": 2500,
    "cost": 0.002
  }
}
```

#### `ai:stream:error`
**Direction**: Server → Client  
**Description**: AI streaming error  
```json
{
  "id": "ai_error_001",
  "type": "ai:stream:error",
  "timestamp": 1642425600000,
  "data": {
    "requestId": "req_123",
    "error": "Model timeout",
    "code": "MODEL_TIMEOUT",
    "retryable": true
  }
}
```

### Tool Execution

#### `tool:execute:start`
**Direction**: Client → Server  
**Description**: Start tool execution  
```json
{
  "id": "tool_start_001",
  "type": "tool:execute:start",
  "timestamp": 1642425600000,
  "data": {
    "executionId": "exec_123",
    "toolName": "bash",
    "parameters": {
      "command": "ls -la /home"
    },
    "sessionId": "session_456"
  }
}
```

#### `tool:execute:progress`
**Direction**: Server → Client  
**Description**: Tool execution progress update  
```json
{
  "id": "tool_progress_001",
  "type": "tool:execute:progress",
  "timestamp": 1642425600000,
  "data": {
    "executionId": "exec_123",
    "progress": 50,
    "status": "running",
    "output": "Processing files...",
    "stage": "execution"
  }
}
```

#### `tool:execute:result`
**Direction**: Server → Client  
**Description**: Tool execution result  
```json
{
  "id": "tool_result_001",
  "type": "tool:execute:result",
  "timestamp": 1642425600000,
  "data": {
    "executionId": "exec_123",
    "result": {
      "stdout": "total 24\ndrwxr-xr-x 3 user user 4096 Jan 17 10:00 .\n",
      "stderr": "",
      "exitCode": 0
    },
    "success": true,
    "duration": 1500
  }
}
```

### System Messages

#### `system:status`
**Direction**: Server → Client  
**Description**: System status update  
```json
{
  "id": "status_001",
  "type": "system:status",
  "timestamp": 1642425600000,
  "data": {
    "status": "healthy",
    "components": {
      "websocket": {
        "status": "healthy",
        "connections": 42
      },
      "database": {
        "status": "healthy",
        "responseTime": 15
      }
    }
  }
}
```

#### `system:notification`
**Direction**: Server → Client  
**Description**: System notification  
```json
{
  "id": "notif_001",
  "type": "system:notification",
  "timestamp": 1642425600000,
  "data": {
    "level": "warning",
    "title": "Maintenance Scheduled",
    "message": "System maintenance in 1 hour",
    "actions": [
      {
        "label": "Dismiss",
        "action": "dismiss"
      },
      {
        "label": "More Info",
        "action": "open_url",
        "url": "/maintenance"
      }
    ]
  }
}
```

## Error Handling

All errors follow this format:
```json
{
  "id": "error_001",
  "type": "connection:error",
  "timestamp": 1642425600000,
  "data": {
    "error": "Invalid message format",
    "code": "INVALID_MESSAGE",
    "details": "Missing required 'type' field",
    "retryable": false
  }
}
```

### Common Error Codes
- `INVALID_JSON`: Malformed JSON message
- `INVALID_MESSAGE`: Missing required message fields
- `AUTH_REQUIRED`: Authentication needed
- `AUTH_FAILED`: Authentication failed
- `AUTH_EXPIRED`: Authentication token expired
- `RATE_LIMIT_EXCEEDED`: Too many messages sent
- `MESSAGE_TOO_LARGE`: Message exceeds size limit
- `CHANNEL_NOT_FOUND`: Channel doesn't exist
- `TOOL_NOT_FOUND`: Tool not available
- `INTERNAL_ERROR`: Server-side error

## Client Implementation

### JavaScript/TypeScript Client

```typescript
import { WSClientReconnection } from './client-reconnection';

// Create reconnecting WebSocket client
const client = new WSClientReconnection('ws://localhost:3000/ws', {
  enabled: true,
  maxRetries: 5,
  initialDelay: 1000,
  maxDelay: 30000,
  backoffMultiplier: 1.5,
  autoReconnect: true,
  heartbeatInterval: 30000
});

// Handle connection events
client.on('connection:established', (duration) => {
  console.log(`Connected after ${duration}ms`);
});

client.on('connection:lost', (code, reason) => {
  console.log(`Disconnected: ${code} ${reason}`);
});

// Handle messages
client.on('message', (message) => {
  console.log('Received:', message);
});

// Send messages
await client.send({
  id: 'ping-1',
  type: 'connection:ping',
  timestamp: Date.now(),
  data: { timestamp: Date.now() }
});

// Connect
await client.connect();
```

### Configuration

Server-side WebSocket configuration:

```typescript
const config = {
  websocket: {
    enabled: true,
    path: '/ws',
    maxConnections: 1000,
    heartbeat: {
      enabled: true,
      interval: 30000,    // 30 seconds
      timeout: 60000      // 60 seconds
    },
    compression: {
      enabled: true,
      threshold: 1024,    // 1KB
      level: 6            // Compression level 1-9
    },
    auth: {
      enabled: false,
      type: 'jwt',
      timeout: 300        // 5 minutes
    },
    rateLimiting: {
      enabled: true,
      messagesPerSecond: 10,
      messagesPerMinute: 100,
      bytesPerSecond: 10240  // 10KB/s
    },
    messageQueue: {
      enabled: true,
      maxSize: 1000,
      persistence: false,
      ttl: 3600           // 1 hour
    },
    channels: {
      enabled: true,
      maxChannelsPerConnection: 50,
      channelNamePattern: '^[a-zA-Z0-9_-]{1,64}$'
    },
    binary: {
      enabled: true,
      maxSize: 10485760,  // 10MB
      allowedTypes: ['application/octet-stream']
    },
    reconnection: {
      enabled: true,
      maxRetries: 5,
      backoffMultiplier: 1.5,
      maxBackoffTime: 30000
    }
  }
}
```

## Testing with wscat

Install wscat globally:
```bash
npm install -g wscat
```

### Basic Connection Test
```bash
wscat -c ws://localhost:3000/ws
```

### Send Test Messages

1. **Ping Test**:
```json
{"id":"ping-1","type":"connection:ping","timestamp":1642425600000,"data":{"timestamp":1642425600000}}
```

2. **AI Streaming Test**:
```json
{"id":"ai-1","type":"ai:stream:start","timestamp":1642425600000,"data":{"requestId":"req-1","provider":"anthropic","prompt":"Hello"}}
```

3. **Tool Execution Test**:
```json
{"id":"tool-1","type":"tool:execute:start","timestamp":1642425600000,"data":{"executionId":"exec-1","toolName":"bash","parameters":{"command":"echo test"}}}
```

4. **Channel Join Test**:
```json
{"id":"channel-1","type":"channel:join","timestamp":1642425600000,"data":{"channel":"test-room"}}
```

## Security Considerations

1. **Authentication**: Enable JWT authentication for production
2. **Rate Limiting**: Configure appropriate rate limits
3. **Message Size**: Set reasonable message size limits  
4. **CORS**: Configure CORS properly for web clients
5. **SSL/TLS**: Use WSS (WebSocket Secure) in production
6. **Input Validation**: All message data is validated
7. **Error Handling**: Errors don't expose sensitive information

## Performance Tips

1. **Compression**: Enable compression for large messages
2. **Message Batching**: Batch multiple small messages when possible
3. **Binary Data**: Use binary messages for non-text data
4. **Connection Pooling**: Limit concurrent connections per user
5. **Memory Management**: Monitor memory usage with large message queues
6. **Health Checks**: Implement proper health checking
7. **Monitoring**: Monitor connection metrics and performance

## Monitoring and Metrics

WebSocket server exposes metrics at:
- `/api/websocket/status` - Current server status
- `/api/websocket/connections` - Connection statistics

Available metrics:
- Active connections count
- Messages sent/received per second
- Average message size
- Compression ratio
- Error rates by type
- Queue sizes and processing time

## Support

For issues, feature requests, or questions:
- Check the test server at `/simple-websocket-test.ts`
- Review the comprehensive tests in `/test/websocket/`
- Examine the example client implementation
- Refer to the TypeScript type definitions

The WebSocket implementation is production-ready and includes all necessary features for real-time communication in ASI-Code applications.