# ASI-Code API Reference

Comprehensive API documentation for the ASI-Code framework, including REST endpoints, WebSocket events, provider interfaces, and tool definitions.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [REST API](#rest-api)
- [WebSocket API](#websocket-api)
- [Provider API](#provider-api)
- [Tool API](#tool-api)
- [Configuration API](#configuration-api)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## Overview

ASI-Code provides multiple API interfaces:

- **REST API**: HTTP endpoints for session management, tool execution, and system administration
- **WebSocket API**: Real-time communication for live updates and streaming responses
- **Provider API**: Interface for AI provider integrations (Anthropic, OpenAI, etc.)
- **Tool API**: Framework for custom tool development and execution
- **Configuration API**: Dynamic configuration management

### Base URL

```
Production: https://api.asi-code.dev
Development: http://localhost:3000
```

### API Versioning

```
Current Version: v1
Base Path: /api/v1
```

## Authentication

### API Key Authentication

```http
Authorization: Bearer asi_key_your-api-key-here
```

### Session Token Authentication

```http
Authorization: Bearer session_token_here
X-Session-ID: session-uuid-here
```

### Example

```bash
curl -H "Authorization: Bearer asi_key_abc123" \
     -H "Content-Type: application/json" \
     https://api.asi-code.dev/api/v1/sessions
```

## REST API

### Health and Status

#### GET /health

Check system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "version": "1.0.0",
  "uptime": 3600,
  "components": {
    "kenny": "healthy",
    "consciousness": "healthy",
    "providers": "healthy",
    "tools": "healthy"
  }
}
```

#### GET /api/v1/status

Get detailed system status.

**Response:**
```json
{
  "system": {
    "status": "operational",
    "version": "1.0.0",
    "buildDate": "2024-01-15T09:00:00.000Z",
    "uptime": 3600000
  },
  "components": {
    "kenny": {
      "status": "healthy",
      "activeContexts": 42,
      "messagesProcessed": 1234
    },
    "consciousness": {
      "status": "healthy",
      "activeStates": 15,
      "memoryUsage": "24MB"
    },
    "providers": {
      "status": "healthy",
      "available": ["anthropic", "openai"],
      "defaultProvider": "anthropic"
    },
    "tools": {
      "status": "healthy",
      "registered": 12,
      "executionsToday": 567
    }
  },
  "performance": {
    "avgResponseTime": 120,
    "requestsPerSecond": 45,
    "errorRate": 0.01
  }
}
```

### Session Management

#### POST /api/v1/sessions

Create a new session.

**Request:**
```json
{
  "userId": "user123",
  "metadata": {
    "name": "My AI Session",
    "description": "Code generation session"
  },
  "config": {
    "provider": "anthropic",
    "model": "claude-3-sonnet-20240229",
    "consciousness": {
      "enabled": true,
      "personalityTraits": {
        "creativity": 80,
        "helpfulness": 90
      }
    }
  }
}
```

**Response:**
```json
{
  "id": "session_abc123",
  "userId": "user123",
  "status": "active",
  "createdAt": "2024-01-15T10:30:00.000Z",
  "lastActivity": "2024-01-15T10:30:00.000Z",
  "context": {
    "id": "context_xyz789",
    "consciousness": {
      "level": 1,
      "state": "active",
      "lastActivity": "2024-01-15T10:30:00.000Z"
    }
  },
  "config": {
    "provider": "anthropic",
    "model": "claude-3-sonnet-20240229"
  },
  "metadata": {
    "name": "My AI Session",
    "description": "Code generation session"
  }
}
```

#### GET /api/v1/sessions

List user sessions.

**Query Parameters:**
- `limit` (optional): Number of sessions to return (default: 20, max: 100)
- `offset` (optional): Number of sessions to skip (default: 0)
- `status` (optional): Filter by status (active, paused, completed)
- `sort` (optional): Sort order (createdAt, lastActivity, name)

**Response:**
```json
{
  "sessions": [
    {
      "id": "session_abc123",
      "userId": "user123",
      "status": "active",
      "createdAt": "2024-01-15T10:30:00.000Z",
      "lastActivity": "2024-01-15T10:35:00.000Z",
      "messageCount": 12,
      "metadata": {
        "name": "My AI Session"
      }
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "hasMore": false
  }
}
```

#### GET /api/v1/sessions/:sessionId

Get session details.

**Response:**
```json
{
  "id": "session_abc123",
  "userId": "user123",
  "status": "active",
  "createdAt": "2024-01-15T10:30:00.000Z",
  "lastActivity": "2024-01-15T10:35:00.000Z",
  "context": {
    "id": "context_xyz789",
    "consciousness": {
      "level": 45,
      "state": "active",
      "awareness": 78,
      "engagement": 82
    }
  },
  "statistics": {
    "messageCount": 12,
    "toolExecutions": 3,
    "averageResponseTime": 1200,
    "consciousnessEvolution": [
      { "timestamp": "2024-01-15T10:30:00.000Z", "level": 1 },
      { "timestamp": "2024-01-15T10:35:00.000Z", "level": 45 }
    ]
  },
  "config": {
    "provider": "anthropic",
    "model": "claude-3-sonnet-20240229"
  }
}
```

#### PUT /api/v1/sessions/:sessionId

Update session configuration.

**Request:**
```json
{
  "metadata": {
    "name": "Updated Session Name"
  },
  "config": {
    "consciousness": {
      "personalityTraits": {
        "creativity": 90
      }
    }
  }
}
```

**Response:**
```json
{
  "id": "session_abc123",
  "updatedAt": "2024-01-15T10:40:00.000Z",
  "changes": [
    "metadata.name",
    "config.consciousness.personalityTraits.creativity"
  ]
}
```

#### DELETE /api/v1/sessions/:sessionId

Delete a session.

**Response:**
```json
{
  "id": "session_abc123",
  "deletedAt": "2024-01-15T10:45:00.000Z",
  "status": "deleted"
}
```

### Message Processing

#### POST /api/v1/sessions/:sessionId/messages

Send a message to a session.

**Request:**
```json
{
  "content": "Help me write a React component for user authentication",
  "type": "user",
  "metadata": {
    "language": "typescript",
    "framework": "react"
  },
  "tools": {
    "enabled": true,
    "allowed": ["write", "read", "analyze"]
  }
}
```

**Response:**
```json
{
  "id": "message_def456",
  "sessionId": "session_abc123",
  "type": "user",
  "content": "Help me write a React component for user authentication",
  "timestamp": "2024-01-15T10:50:00.000Z",
  "status": "processing",
  "queuePosition": 1,
  "estimatedResponseTime": 3000
}
```

#### GET /api/v1/sessions/:sessionId/messages

Get message history.

**Query Parameters:**
- `limit` (optional): Number of messages (default: 50, max: 200)
- `before` (optional): Get messages before this timestamp
- `after` (optional): Get messages after this timestamp
- `type` (optional): Filter by message type (user, assistant, system, tool)

**Response:**
```json
{
  "messages": [
    {
      "id": "message_def456",
      "type": "user",
      "content": "Help me write a React component for user authentication",
      "timestamp": "2024-01-15T10:50:00.000Z",
      "metadata": {
        "language": "typescript",
        "framework": "react"
      }
    },
    {
      "id": "message_ghi789",
      "type": "assistant",
      "content": "I'll help you create a React authentication component...",
      "timestamp": "2024-01-15T10:50:03.000Z",
      "metadata": {
        "consciousness": {
          "level": 47,
          "awareness": 80,
          "engagement": 85
        },
        "provider": {
          "name": "anthropic",
          "model": "claude-3-sonnet-20240229",
          "usage": {
            "inputTokens": 45,
            "outputTokens": 234
          }
        },
        "processingTime": 2800
      },
      "toolExecutions": [
        {
          "toolName": "write",
          "status": "completed",
          "result": {
            "filesCreated": ["AuthComponent.tsx"]
          }
        }
      ]
    }
  ],
  "pagination": {
    "total": 2,
    "hasMore": false
  }
}
```

#### GET /api/v1/messages/:messageId

Get specific message details.

**Response:**
```json
{
  "id": "message_ghi789",
  "sessionId": "session_abc123",
  "type": "assistant",
  "content": "I'll help you create a React authentication component...",
  "timestamp": "2024-01-15T10:50:03.000Z",
  "status": "completed",
  "metadata": {
    "consciousness": {
      "level": 47,
      "awareness": 80,
      "engagement": 85,
      "memoriesUsed": 3,
      "adaptationRate": 0.15
    },
    "provider": {
      "name": "anthropic",
      "model": "claude-3-sonnet-20240229",
      "usage": {
        "inputTokens": 45,
        "outputTokens": 234,
        "cost": 0.0012
      }
    },
    "processingTime": 2800,
    "qualityMetrics": {
      "relevance": 0.95,
      "helpfulness": 0.92,
      "accuracy": 0.98
    }
  },
  "toolExecutions": [
    {
      "id": "execution_123",
      "toolName": "write",
      "params": {
        "filePath": "./src/components/AuthComponent.tsx",
        "content": "import React from 'react'..."
      },
      "status": "completed",
      "startTime": "2024-01-15T10:50:02.000Z",
      "endTime": "2024-01-15T10:50:02.500Z",
      "result": {
        "success": true,
        "filesCreated": ["./src/components/AuthComponent.tsx"],
        "bytesWritten": 1024
      }
    }
  ]
}
```

### Tool Management

#### GET /api/v1/tools

List available tools.

**Query Parameters:**
- `category` (optional): Filter by category (file, shell, analysis, etc.)
- `enabled` (optional): Filter by enabled status (true/false)

**Response:**
```json
{
  "tools": [
    {
      "name": "write",
      "description": "Write content to files",
      "category": "file",
      "version": "1.0.0",
      "enabled": true,
      "permissions": ["filesystem:write"],
      "parameters": {
        "filePath": {
          "type": "string",
          "required": true,
          "description": "Path to write the file"
        },
        "content": {
          "type": "string",
          "required": true,
          "description": "Content to write"
        }
      }
    },
    {
      "name": "bash",
      "description": "Execute bash commands",
      "category": "shell",
      "version": "1.0.0",
      "enabled": true,
      "permissions": ["shell:execute"],
      "parameters": {
        "command": {
          "type": "string",
          "required": true,
          "description": "Command to execute"
        },
        "timeout": {
          "type": "number",
          "required": false,
          "default": 30000,
          "description": "Execution timeout in milliseconds"
        }
      }
    }
  ]
}
```

#### POST /api/v1/tools/:toolName/execute

Execute a tool directly (outside of a session context).

**Request:**
```json
{
  "parameters": {
    "filePath": "./example.txt",
    "content": "Hello, World!"
  },
  "context": {
    "sessionId": "session_abc123",
    "permissions": {
      "filesystem": ["./"],
      "network": false
    }
  }
}
```

**Response:**
```json
{
  "executionId": "execution_456",
  "toolName": "write",
  "status": "completed",
  "startTime": "2024-01-15T11:00:00.000Z",
  "endTime": "2024-01-15T11:00:00.200Z",
  "result": {
    "success": true,
    "filesCreated": ["./example.txt"],
    "bytesWritten": 13
  },
  "permissions": {
    "granted": ["filesystem:write"],
    "denied": []
  }
}
```

### Provider Management

#### GET /api/v1/providers

List configured providers.

**Response:**
```json
{
  "providers": [
    {
      "name": "default",
      "type": "anthropic",
      "model": "claude-3-sonnet-20240229",
      "status": "available",
      "capabilities": [
        "text-generation",
        "function-calling",
        "code-generation"
      ],
      "limits": {
        "maxTokens": 200000,
        "requestsPerMinute": 60,
        "requestsPerDay": 1000
      }
    },
    {
      "name": "openai",
      "type": "openai",
      "model": "gpt-4",
      "status": "available",
      "capabilities": [
        "text-generation",
        "function-calling",
        "code-generation"
      ]
    }
  ]
}
```

#### POST /api/v1/providers/:providerName/test

Test provider connectivity and capabilities.

**Response:**
```json
{
  "providerName": "anthropic",
  "status": "healthy",
  "responseTime": 245,
  "capabilities": {
    "textGeneration": true,
    "functionCalling": true,
    "codeGeneration": true
  },
  "limits": {
    "available": true,
    "remaining": {
      "requestsPerMinute": 58,
      "requestsPerDay": 987
    }
  },
  "testMessage": {
    "sent": "Hello, this is a test message",
    "received": "Hello! I received your test message successfully.",
    "responseTime": 1200
  }
}
```

## WebSocket API

### Connection

Connect to the WebSocket endpoint for real-time communication:

```javascript
const ws = new WebSocket('wss://api.asi-code.dev/ws');

// With authentication
const ws = new WebSocket('wss://api.asi-code.dev/ws', {
  headers: {
    'Authorization': 'Bearer your-api-key'
  }
});
```

### Event Types

#### Client to Server Events

**session:join**
```json
{
  "type": "session:join",
  "sessionId": "session_abc123",
  "userId": "user123"
}
```

**message:send**
```json
{
  "type": "message:send",
  "sessionId": "session_abc123",
  "message": {
    "content": "Generate a Python function",
    "type": "user",
    "metadata": {
      "language": "python"
    }
  }
}
```

**tool:execute**
```json
{
  "type": "tool:execute",
  "sessionId": "session_abc123",
  "tool": {
    "name": "bash",
    "parameters": {
      "command": "ls -la"
    }
  }
}
```

**consciousness:query**
```json
{
  "type": "consciousness:query",
  "sessionId": "session_abc123",
  "query": "current_state"
}
```

#### Server to Client Events

**session:joined**
```json
{
  "type": "session:joined",
  "sessionId": "session_abc123",
  "context": {
    "id": "context_xyz789",
    "consciousness": {
      "level": 45,
      "state": "active"
    }
  },
  "timestamp": "2024-01-15T11:00:00.000Z"
}
```

**message:processing**
```json
{
  "type": "message:processing",
  "sessionId": "session_abc123",
  "messageId": "message_def456",
  "status": "processing",
  "estimatedTime": 3000,
  "queuePosition": 1
}
```

**message:stream**
```json
{
  "type": "message:stream",
  "sessionId": "session_abc123",
  "messageId": "message_def456",
  "chunk": "I'll help you create a Python function...",
  "isComplete": false,
  "metadata": {
    "chunkIndex": 0,
    "totalChunks": null
  }
}
```

**message:complete**
```json
{
  "type": "message:complete",
  "sessionId": "session_abc123",
  "messageId": "message_def456",
  "message": {
    "id": "message_def456",
    "type": "assistant",
    "content": "I'll help you create a Python function...",
    "timestamp": "2024-01-15T11:00:03.000Z",
    "metadata": {
      "consciousness": {
        "level": 47,
        "awareness": 82
      },
      "processingTime": 2800
    }
  }
}
```

**tool:result**
```json
{
  "type": "tool:result",
  "sessionId": "session_abc123",
  "executionId": "execution_789",
  "toolName": "bash",
  "status": "completed",
  "result": {
    "exitCode": 0,
    "stdout": "total 8\ndrwxr-xr-x 3 user user 4096 Jan 15 11:00 .\ndrwxr-xr-x 5 user user 4096 Jan 15 10:55 ..",
    "stderr": "",
    "executionTime": 120
  }
}
```

**consciousness:update**
```json
{
  "type": "consciousness:update",
  "sessionId": "session_abc123",
  "contextId": "context_xyz789",
  "state": {
    "level": 48,
    "awareness": 83,
    "engagement": 87,
    "adaptability": 74,
    "coherence": 91,
    "timestamp": "2024-01-15T11:00:05.000Z"
  },
  "changes": [
    {
      "property": "awareness",
      "oldValue": 82,
      "newValue": 83,
      "reason": "user_feedback"
    }
  ]
}
```

**error**
```json
{
  "type": "error",
  "code": "TOOL_EXECUTION_FAILED",
  "message": "Tool execution failed: Permission denied",
  "sessionId": "session_abc123",
  "details": {
    "toolName": "bash",
    "command": "sudo rm -rf /",
    "reason": "Dangerous command blocked by security policy"
  },
  "timestamp": "2024-01-15T11:00:00.000Z"
}
```

### JavaScript Client Example

```javascript
class ASICodeClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.ws = null;
    this.eventHandlers = new Map();
  }
  
  connect() {
    this.ws = new WebSocket('wss://api.asi-code.dev/ws', {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleEvent(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }
  
  on(eventType, handler) {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, []);
    }
    this.eventHandlers.get(eventType).push(handler);
  }
  
  handleEvent(event) {
    const handlers = this.eventHandlers.get(event.type) || [];
    handlers.forEach(handler => handler(event));
  }
  
  sendMessage(sessionId, content, type = 'user') {
    this.ws.send(JSON.stringify({
      type: 'message:send',
      sessionId,
      message: { content, type }
    }));
  }
  
  joinSession(sessionId, userId) {
    this.ws.send(JSON.stringify({
      type: 'session:join',
      sessionId,
      userId
    }));
  }
}

// Usage
const client = new ASICodeClient('your-api-key');

client.on('message:complete', (event) => {
  console.log('Received response:', event.message.content);
});

client.on('consciousness:update', (event) => {
  console.log('Consciousness level:', event.state.level);
});

client.connect();
client.joinSession('session_abc123', 'user123');
client.sendMessage('session_abc123', 'Hello, ASI-Code!');
```

## Provider API

### Provider Interface

All AI providers must implement the `Provider` interface:

```typescript
interface Provider {
  name: string;
  type: string;
  model: string;
  
  initialize(config: ProviderConfig): Promise<void>;
  generate(messages: ProviderMessage[]): Promise<ProviderResponse>;
  validate(): Promise<boolean>;
  cleanup(): Promise<void>;
}

interface ProviderMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: Record<string, any>;
}

interface ProviderResponse {
  content: string;
  model: string;
  usage: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
  };
  metadata?: Record<string, any>;
}
```

### Custom Provider Example

```typescript
import { Provider, ProviderConfig, ProviderMessage, ProviderResponse } from 'asi-code/provider';

export class CustomProvider implements Provider {
  name = 'custom';
  type = 'custom';
  model: string;
  
  private apiKey: string;
  private baseUrl: string;
  
  async initialize(config: ProviderConfig): Promise<void> {
    this.model = config.model;
    this.apiKey = config.apiKey;
    this.baseUrl = config.baseUrl || 'https://api.custom-ai.com';
    
    // Test connection
    if (!await this.validate()) {
      throw new Error('Failed to initialize custom provider');
    }
  }
  
  async generate(messages: ProviderMessage[]): Promise<ProviderResponse> {
    const response = await fetch(`${this.baseUrl}/generate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: this.model,
        messages,
        max_tokens: 4000
      })
    });
    
    if (!response.ok) {
      throw new Error(`Provider request failed: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    return {
      content: data.message.content,
      model: this.model,
      usage: {
        inputTokens: data.usage.input_tokens,
        outputTokens: data.usage.output_tokens,
        totalTokens: data.usage.total_tokens
      },
      metadata: {
        requestId: data.id,
        finishReason: data.finish_reason
      }
    };
  }
  
  async validate(): Promise<boolean> {
    try {
      const testMessage: ProviderMessage = {
        role: 'user',
        content: 'Hello'
      };
      
      await this.generate([testMessage]);
      return true;
    } catch (error) {
      console.error('Provider validation failed:', error);
      return false;
    }
  }
  
  async cleanup(): Promise<void> {
    // Clean up resources
  }
}
```

### Provider Registration

```typescript
import { createProviderManager } from 'asi-code/provider';
import { CustomProvider } from './custom-provider';

const providerManager = createProviderManager();

// Register custom provider
await providerManager.register({
  name: 'custom',
  type: 'custom',
  apiKey: process.env.CUSTOM_API_KEY,
  model: 'custom-model-v1',
  implementation: CustomProvider
});

// Use the provider
const provider = providerManager.get('custom');
const response = await provider.generate([
  { role: 'user', content: 'Hello, world!' }
]);
```

## Tool API

### Tool Interface

Custom tools must extend the `BaseTool` class:

```typescript
import { BaseTool, ToolResult, SecurityContext } from 'asi-code/tool';

export class CustomTool extends BaseTool {
  name = 'custom-tool';
  description = 'Custom tool for specific operations';
  category = 'utility';
  version = '1.0.0';
  
  // Define required parameters
  parameters = {
    input: {
      type: 'string',
      required: true,
      description: 'Input data for processing'
    },
    options: {
      type: 'object',
      required: false,
      description: 'Optional configuration'
    }
  };
  
  // Define required permissions
  permissions = ['custom:execute'];
  
  async execute(params: any, context: SecurityContext): Promise<ToolResult> {
    // Validate parameters
    if (!this.validateParams(params)) {
      throw new Error('Invalid parameters');
    }
    
    // Check permissions
    if (!context.hasPermission('custom:execute')) {
      throw new Error('Permission denied');
    }
    
    try {
      // Perform tool operation
      const result = await this.performOperation(params.input, params.options);
      
      return {
        success: true,
        result,
        metadata: {
          processingTime: Date.now() - context.startTime,
          version: this.version
        }
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        metadata: {
          errorCode: 'EXECUTION_FAILED'
        }
      };
    }
  }
  
  validateParams(params: any): boolean {
    return typeof params.input === 'string' && params.input.length > 0;
  }
  
  private async performOperation(input: string, options?: any): Promise<any> {
    // Custom tool logic here
    return { processed: input.toUpperCase() };
  }
}
```

### Tool Registration

```typescript
import { createToolManager } from 'asi-code/tool';
import { CustomTool } from './custom-tool';

const toolManager = createToolManager();

// Register custom tool
toolManager.register(new CustomTool());

// Execute tool
const result = await toolManager.execute('custom-tool', {
  input: 'hello world',
  options: { uppercase: true }
}, securityContext);
```

## Configuration API

### Dynamic Configuration

Configuration can be updated at runtime through the API:

#### GET /api/v1/config

Get current configuration.

**Response:**
```json
{
  "providers": {
    "default": {
      "name": "default",
      "type": "anthropic",
      "model": "claude-3-sonnet-20240229"
    }
  },
  "consciousness": {
    "enabled": true,
    "awarenessThreshold": 70,
    "personalityTraits": {
      "curiosity": 80,
      "helpfulness": 90
    }
  },
  "security": {
    "permissionLevel": "safe",
    "allowedCommands": ["read", "write", "analyze"]
  },
  "server": {
    "port": 3000,
    "cors": true
  }
}
```

#### PUT /api/v1/config

Update configuration.

**Request:**
```json
{
  "consciousness": {
    "personalityTraits": {
      "creativity": 85
    }
  },
  "security": {
    "allowedCommands": ["read", "write", "analyze", "bash"]
  }
}
```

**Response:**
```json
{
  "updated": true,
  "changes": [
    "consciousness.personalityTraits.creativity",
    "security.allowedCommands"
  ],
  "timestamp": "2024-01-15T11:30:00.000Z"
}
```

## Error Handling

### Error Response Format

All API errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "additional error details",
      "suggestion": "possible solution"
    },
    "timestamp": "2024-01-15T11:00:00.000Z",
    "requestId": "req_123456"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_API_KEY` | 401 | Invalid or missing API key |
| `INSUFFICIENT_PERMISSIONS` | 403 | Lack required permissions |
| `SESSION_NOT_FOUND` | 404 | Session doesn't exist |
| `TOOL_NOT_FOUND` | 404 | Tool doesn't exist |
| `PROVIDER_UNAVAILABLE` | 502 | AI provider is unavailable |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `TOOL_EXECUTION_FAILED` | 500 | Tool execution error |
| `CONSCIOUSNESS_ERROR` | 500 | Consciousness engine error |
| `INTERNAL_SERVER_ERROR` | 500 | Generic server error |

### Error Examples

**Authentication Error:**
```json
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "The provided API key is invalid or expired",
    "details": {
      "suggestion": "Please check your API key and ensure it's active"
    },
    "timestamp": "2024-01-15T11:00:00.000Z",
    "requestId": "req_123456"
  }
}
```

**Validation Error:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "field": "content",
      "issue": "Content is required and cannot be empty",
      "received": ""
    },
    "timestamp": "2024-01-15T11:00:00.000Z",
    "requestId": "req_123456"
  }
}
```

**Tool Execution Error:**
```json
{
  "error": {
    "code": "TOOL_EXECUTION_FAILED",
    "message": "Tool execution failed due to permission restrictions",
    "details": {
      "toolName": "bash",
      "command": "rm -rf /",
      "reason": "Dangerous command blocked by security policy",
      "suggestion": "Use safer alternatives or adjust security settings"
    },
    "timestamp": "2024-01-15T11:00:00.000Z",
    "requestId": "req_123456"
  }
}
```

## Rate Limiting

### Limits

Default rate limits per API key:

| Endpoint | Limit |
|----------|-------|
| `/api/v1/sessions` | 100 requests/hour |
| `/api/v1/messages` | 1000 requests/hour |
| `/api/v1/tools/*/execute` | 500 requests/hour |
| WebSocket connections | 10 concurrent |
| Message streaming | 50 messages/minute |

### Headers

Rate limit information is included in response headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1642248000
X-RateLimit-Window: 3600
```

### Rate Limit Exceeded Response

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 1000,
      "window": 3600,
      "resetTime": "2024-01-15T12:00:00.000Z",
      "suggestion": "Please wait before making more requests"
    }
  }
}
```

## Examples

### Complete Session Workflow

```javascript
const API_BASE = 'https://api.asi-code.dev/api/v1';
const API_KEY = 'your-api-key';

async function createAndUseSession() {
  // 1. Create session
  const sessionResponse = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      userId: 'user123',
      metadata: {
        name: 'Code Generation Session'
      },
      config: {
        provider: 'anthropic',
        model: 'claude-3-sonnet-20240229'
      }
    })
  });
  
  const session = await sessionResponse.json();
  console.log('Created session:', session.id);
  
  // 2. Send message
  const messageResponse = await fetch(`${API_BASE}/sessions/${session.id}/messages`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      content: 'Create a Python function to calculate fibonacci numbers',
      type: 'user',
      tools: {
        enabled: true,
        allowed: ['write']
      }
    })
  });
  
  const message = await messageResponse.json();
  console.log('Sent message:', message.id);
  
  // 3. Poll for response (or use WebSocket for real-time)
  let response = null;
  while (!response) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const historyResponse = await fetch(`${API_BASE}/sessions/${session.id}/messages`, {
      headers: {
        'Authorization': `Bearer ${API_KEY}`
      }
    });
    
    const history = await historyResponse.json();
    response = history.messages.find(m => 
      m.type === 'assistant' && 
      m.timestamp > message.timestamp
    );
  }
  
  console.log('Received response:', response.content);
  console.log('Consciousness level:', response.metadata.consciousness.level);
  
  // 4. Check tool executions
  if (response.toolExecutions && response.toolExecutions.length > 0) {
    console.log('Tool executions:');
    response.toolExecutions.forEach(execution => {
      console.log(`- ${execution.toolName}: ${execution.status}`);
      if (execution.result) {
        console.log(`  Result:`, execution.result);
      }
    });
  }
}

createAndUseSession().catch(console.error);
```

### WebSocket Streaming Example

```javascript
class StreamingChat {
  constructor(apiKey, sessionId) {
    this.apiKey = apiKey;
    this.sessionId = sessionId;
    this.ws = null;
    this.messageBuffer = '';
  }
  
  connect() {
    this.ws = new WebSocket('wss://api.asi-code.dev/ws', {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });
    
    this.ws.onopen = () => {
      console.log('Connected to ASI-Code');
      this.joinSession();
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleEvent(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }
  
  joinSession() {
    this.ws.send(JSON.stringify({
      type: 'session:join',
      sessionId: this.sessionId,
      userId: 'user123'
    }));
  }
  
  sendMessage(content) {
    this.ws.send(JSON.stringify({
      type: 'message:send',
      sessionId: this.sessionId,
      message: {
        content,
        type: 'user'
      }
    }));
    
    this.messageBuffer = '';
    console.log('\n--- Streaming Response ---');
  }
  
  handleEvent(event) {
    switch (event.type) {
      case 'session:joined':
        console.log('Joined session successfully');
        break;
        
      case 'message:stream':
        process.stdout.write(event.chunk);
        this.messageBuffer += event.chunk;
        break;
        
      case 'message:complete':
        console.log('\n--- Response Complete ---');
        console.log('Final message:', this.messageBuffer);
        console.log('Consciousness level:', event.message.metadata.consciousness.level);
        break;
        
      case 'consciousness:update':
        console.log('Consciousness update:', {
          level: event.state.level,
          awareness: event.state.awareness,
          engagement: event.state.engagement
        });
        break;
        
      case 'tool:result':
        console.log('Tool execution result:', {
          tool: event.toolName,
          status: event.status,
          result: event.result
        });
        break;
        
      case 'error':
        console.error('Error:', event.message);
        break;
    }
  }
}

// Usage
const chat = new StreamingChat('your-api-key', 'session_abc123');
chat.connect();

// Send messages after connection
setTimeout(() => {
  chat.sendMessage('Generate a React component for user authentication');
}, 2000);
```

### Custom Tool Integration

```javascript
// Server-side tool registration
import { createToolManager, BaseTool } from 'asi-code/tool';

class DatabaseQueryTool extends BaseTool {
  name = 'database-query';
  description = 'Execute database queries safely';
  category = 'database';
  version = '1.0.0';
  
  parameters = {
    query: {
      type: 'string',
      required: true,
      description: 'SQL query to execute'
    },
    database: {
      type: 'string',
      required: false,
      default: 'default',
      description: 'Database connection name'
    }
  };
  
  permissions = ['database:read', 'database:write'];
  
  async execute(params, context) {
    // Validate SQL query for safety
    if (this.isDangerousQuery(params.query)) {
      throw new Error('Dangerous query blocked');
    }
    
    // Execute query (implementation depends on your database)
    const result = await this.executeQuery(params.query, params.database);
    
    return {
      success: true,
      result: {
        rows: result.rows,
        rowCount: result.rowCount,
        executionTime: result.executionTime
      }
    };
  }
  
  isDangerousQuery(query) {
    const dangerous = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER'];
    return dangerous.some(keyword => 
      query.toUpperCase().includes(keyword)
    );
  }
  
  async executeQuery(query, database) {
    // Database execution logic
    return {
      rows: [{ id: 1, name: 'John' }],
      rowCount: 1,
      executionTime: 45
    };
  }
}

// Register the tool
const toolManager = createToolManager();
toolManager.register(new DatabaseQueryTool());

// Client-side usage
const response = await fetch('/api/v1/tools/database-query/execute', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    parameters: {
      query: 'SELECT * FROM users WHERE active = true',
      database: 'production'
    },
    context: {
      sessionId: 'session_abc123'
    }
  })
});

const result = await response.json();
console.log('Query result:', result.result);
```

---

For more examples and detailed documentation, visit the [docs/](docs/) directory or check out our [GitHub repository](https://github.com/asi-team/asi-code).