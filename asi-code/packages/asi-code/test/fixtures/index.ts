/**
 * Test Fixtures - Centralized test data and mock objects
 */

import { nanoid } from 'nanoid';
import type { KennyContext, KennyMessage } from '@/kenny/index.js';
import type { Provider, ProviderConfig, ProviderMessage, ProviderResponse } from '@/provider/index.js';
import type { Tool, ToolDefinition, ToolExecutionContext, ToolResult } from '@/tool/index.js';
import type { SessionConfig, SessionData } from '@/session/index.js';

// =============================================================================
// KENNY FIXTURES
// =============================================================================

export const KennyFixtures = {
  defaultContext: (): KennyContext => ({
    id: `ctx_${nanoid(12)}`,
    sessionId: `session_${nanoid(8)}`,
    userId: `user_${nanoid(8)}`,
    consciousness: {
      level: 75,
      state: 'active',
      awarenessLevel: 80,
      adaptationRate: 0.15
    },
    permissions: {
      tools: ['read', 'write', 'bash', 'search'],
      resources: ['file-system', 'network', 'database'],
      restrictions: []
    },
    metadata: {
      createdAt: new Date().toISOString(),
      lastActive: new Date().toISOString(),
      fixture: true
    }
  }),

  highPermissionContext: (): KennyContext => ({
    ...KennyFixtures.defaultContext(),
    permissions: {
      tools: ['read', 'write', 'bash', 'search', 'edit', 'delete', 'move', 'admin'],
      resources: ['file-system', 'network', 'database', 'system', 'cloud'],
      restrictions: []
    }
  }),

  restrictedContext: (): KennyContext => ({
    ...KennyFixtures.defaultContext(),
    permissions: {
      tools: ['read'],
      resources: ['file-system'],
      restrictions: ['no-network', 'read-only', 'sandbox']
    }
  }),

  userMessage: (content: string = 'Test message', context?: KennyContext): KennyMessage => ({
    id: `msg_${nanoid(12)}`,
    type: 'user',
    content,
    timestamp: new Date(),
    context: context || KennyFixtures.defaultContext(),
    metadata: { fixture: true }
  }),

  assistantMessage: (content: string = 'Assistant response', context?: KennyContext): KennyMessage => ({
    id: `msg_${nanoid(12)}`,
    type: 'assistant',
    content,
    timestamp: new Date(),
    context: context || KennyFixtures.defaultContext(),
    metadata: { fixture: true, model: 'test-model' }
  }),

  conversation: (length: number = 3): KennyMessage[] => {
    const context = KennyFixtures.defaultContext();
    const messages: KennyMessage[] = [];
    
    for (let i = 0; i < length; i++) {
      const isUser = i % 2 === 0;
      messages.push(
        isUser 
          ? KennyFixtures.userMessage(`User message ${i + 1}`, context)
          : KennyFixtures.assistantMessage(`Assistant response ${i}`, context)
      );
    }
    
    return messages;
  }
};

// =============================================================================
// PROVIDER FIXTURES
// =============================================================================

export const ProviderFixtures = {
  anthropicConfig: (): ProviderConfig => ({
    name: 'anthropic-test',
    type: 'anthropic',
    apiKey: 'sk-ant-test123',
    model: 'claude-3-sonnet-20240229',
    maxTokens: 4096,
    temperature: 0.7,
    topP: 0.9
  }),

  openaiConfig: (): ProviderConfig => ({
    name: 'openai-test',
    type: 'openai',
    apiKey: 'sk-test123',
    model: 'gpt-4',
    maxTokens: 4096,
    temperature: 0.7,
    topP: 0.9
  }),

  localConfig: (): ProviderConfig => ({
    name: 'local-test',
    type: 'local',
    model: 'llama-2-7b',
    endpoint: 'http://localhost:8080',
    maxTokens: 2048
  }),

  userMessage: (content: string = 'Hello'): ProviderMessage => ({
    role: 'user',
    content
  }),

  assistantMessage: (content: string = 'Hi there!'): ProviderMessage => ({
    role: 'assistant',
    content
  }),

  systemMessage: (content: string = 'You are a helpful assistant'): ProviderMessage => ({
    role: 'system',
    content
  }),

  conversation: (userPrompt: string = 'Hello'): ProviderMessage[] => [
    ProviderFixtures.systemMessage(),
    ProviderFixtures.userMessage(userPrompt),
    ProviderFixtures.assistantMessage('Hello! How can I help you today?')
  ],

  response: (content: string = 'Test response'): ProviderResponse => ({
    content,
    model: 'test-model',
    usage: {
      inputTokens: Math.floor(content.length / 4),
      outputTokens: Math.floor(content.length / 4),
      totalTokens: Math.floor(content.length / 2)
    },
    metadata: {
      fixture: true,
      timestamp: new Date().toISOString()
    }
  }),

  streamingResponse: function* (content: string = 'Streaming test response') {
    const words = content.split(' ');
    for (const word of words) {
      yield word + ' ';
    }
    return ProviderFixtures.response(content);
  }
};

// =============================================================================
// TOOL FIXTURES
// =============================================================================

export const ToolFixtures = {
  readTool: (): ToolDefinition => ({
    name: 'read',
    description: 'Read file contents',
    parameters: [
      {
        name: 'path',
        type: 'string',
        description: 'File path to read',
        required: true
      },
      {
        name: 'encoding',
        type: 'string',
        description: 'File encoding',
        required: false,
        default: 'utf8'
      }
    ],
    category: 'file-system',
    version: '1.0.0',
    author: 'asi-code'
  }),

  writeTool: (): ToolDefinition => ({
    name: 'write',
    description: 'Write content to file',
    parameters: [
      {
        name: 'path',
        type: 'string',
        description: 'File path to write',
        required: true
      },
      {
        name: 'content',
        type: 'string',
        description: 'Content to write',
        required: true
      },
      {
        name: 'encoding',
        type: 'string',
        description: 'File encoding',
        required: false,
        default: 'utf8'
      }
    ],
    category: 'file-system',
    version: '1.0.0',
    author: 'asi-code'
  }),

  bashTool: (): ToolDefinition => ({
    name: 'bash',
    description: 'Execute bash commands',
    parameters: [
      {
        name: 'command',
        type: 'string',
        description: 'Command to execute',
        required: true
      },
      {
        name: 'timeout',
        type: 'number',
        description: 'Timeout in milliseconds',
        required: false,
        default: 30000
      }
    ],
    category: 'system',
    version: '1.0.0',
    author: 'asi-code'
  }),

  customTool: (name: string = 'custom-tool'): ToolDefinition => ({
    name,
    description: `Custom tool: ${name}`,
    parameters: [
      {
        name: 'input',
        type: 'string',
        description: 'Input parameter',
        required: true
      }
    ],
    category: 'custom',
    version: '1.0.0',
    author: 'test'
  }),

  executionContext: (): ToolExecutionContext => ({
    sessionId: `session_${nanoid(8)}`,
    userId: `user_${nanoid(8)}`,
    permissions: ['read', 'write', 'execute'],
    workingDirectory: '/tmp/asi-code-test',
    environment: {
      NODE_ENV: 'test',
      PATH: '/usr/bin:/bin',
      HOME: '/tmp'
    }
  }),

  successResult: (data: any = { message: 'Success' }): ToolResult => ({
    success: true,
    data,
    metadata: {
      fixture: true,
      executedAt: new Date().toISOString(),
      duration: Math.floor(Math.random() * 1000)
    }
  }),

  errorResult: (error: string = 'Test error'): ToolResult => ({
    success: false,
    error,
    metadata: {
      fixture: true,
      executedAt: new Date().toISOString(),
      duration: Math.floor(Math.random() * 1000)
    }
  })
};

// =============================================================================
// SESSION FIXTURES
// =============================================================================

export const SessionFixtures = {
  defaultConfig: (): SessionConfig => ({
    sessionId: `session_${nanoid(8)}`,
    userId: `user_${nanoid(8)}`,
    maxDuration: 3600000, // 1 hour
    idleTimeout: 900000,  // 15 minutes
    persistSession: true,
    enableLogging: true
  }),

  guestConfig: (): SessionConfig => ({
    ...SessionFixtures.defaultConfig(),
    userId: 'guest',
    maxDuration: 1800000, // 30 minutes
    idleTimeout: 300000,  // 5 minutes
    persistSession: false
  }),

  sessionData: (): SessionData => ({
    id: `session_${nanoid(8)}`,
    userId: `user_${nanoid(8)}`,
    createdAt: new Date(),
    lastActiveAt: new Date(),
    data: {
      kennyContext: KennyFixtures.defaultContext(),
      messageHistory: KennyFixtures.conversation(5),
      activeTools: ['read', 'write', 'bash'],
      preferences: {
        theme: 'dark',
        language: 'en',
        notifications: true
      }
    },
    metadata: {
      fixture: true,
      userAgent: 'ASI-Code-Test/1.0.0',
      ipAddress: '127.0.0.1'
    }
  })
};

// =============================================================================
// ERROR FIXTURES
// =============================================================================

export const ErrorFixtures = {
  validationError: (field: string = 'unknown') => ({
    name: 'ValidationError',
    message: `Validation failed for field: ${field}`,
    code: 'VALIDATION_ERROR',
    statusCode: 400,
    details: { field, reason: 'Invalid format' }
  }),

  authenticationError: () => ({
    name: 'AuthenticationError',
    message: 'Authentication required',
    code: 'AUTH_REQUIRED',
    statusCode: 401
  }),

  authorizationError: (permission: string = 'unknown') => ({
    name: 'AuthorizationError',
    message: `Permission denied: ${permission}`,
    code: 'PERMISSION_DENIED',
    statusCode: 403,
    details: { permission }
  }),

  notFoundError: (resource: string = 'resource') => ({
    name: 'NotFoundError',
    message: `${resource} not found`,
    code: 'NOT_FOUND',
    statusCode: 404,
    details: { resource }
  }),

  internalError: () => ({
    name: 'InternalError',
    message: 'An internal error occurred',
    code: 'INTERNAL_ERROR',
    statusCode: 500
  }),

  networkError: () => ({
    name: 'NetworkError',
    message: 'Network connection failed',
    code: 'NETWORK_ERROR',
    cause: new Error('ECONNREFUSED')
  }),

  timeoutError: (timeout: number = 30000) => ({
    name: 'TimeoutError',
    message: `Operation timed out after ${timeout}ms`,
    code: 'TIMEOUT',
    timeout
  })
};

// =============================================================================
// PERFORMANCE FIXTURES
// =============================================================================

export const PerformanceFixtures = {
  smallDataset: () => Array.from({ length: 100 }, (_, i) => ({
    id: i,
    name: `Item ${i}`,
    value: Math.random() * 100
  })),

  mediumDataset: () => Array.from({ length: 10000 }, (_, i) => ({
    id: i,
    name: `Item ${i}`,
    value: Math.random() * 100,
    metadata: {
      category: `Category ${i % 10}`,
      tags: [`tag${i % 5}`, `tag${i % 7}`],
      timestamp: new Date(Date.now() - Math.random() * 86400000).toISOString()
    }
  })),

  largeDataset: () => Array.from({ length: 100000 }, (_, i) => ({
    id: i,
    name: `Item ${i}`,
    value: Math.random() * 100,
    description: `This is a longer description for item ${i} with some random content: ${Math.random().toString(36)}`,
    metadata: {
      category: `Category ${i % 10}`,
      subcategory: `Subcategory ${i % 50}`,
      tags: Array.from({ length: Math.floor(Math.random() * 5) + 1 }, (_, j) => `tag${j}_${i % 20}`),
      timestamp: new Date(Date.now() - Math.random() * 86400000).toISOString(),
      properties: Object.fromEntries(
        Array.from({ length: Math.floor(Math.random() * 10) + 1 }, (_, j) => [
          `prop${j}`,
          Math.random() > 0.5 ? Math.random() * 1000 : `value${j}_${Math.random().toString(36)}`
        ])
      )
    }
  })),

  memoryIntensiveData: (sizeMB: number = 10) => {
    const targetSize = sizeMB * 1024 * 1024;
    const itemSize = 1024; // Approximate size per item
    const itemCount = Math.floor(targetSize / itemSize);
    
    return Array.from({ length: itemCount }, (_, i) => ({
      id: i,
      data: 'x'.repeat(Math.floor(itemSize * 0.8)), // Leave some room for other properties
      metadata: {
        index: i,
        timestamp: new Date().toISOString()
      }
    }));
  }
};

// =============================================================================
// DATABASE FIXTURES
// =============================================================================

export const DatabaseFixtures = {
  users: () => [
    {
      id: 'user_001',
      username: 'testuser1',
      email: 'test1@example.com',
      firstName: 'Test',
      lastName: 'User1',
      createdAt: new Date('2024-01-01'),
      updatedAt: new Date('2024-01-01'),
      isActive: true
    },
    {
      id: 'user_002',
      username: 'testuser2',
      email: 'test2@example.com',
      firstName: 'Test',
      lastName: 'User2',
      createdAt: new Date('2024-01-02'),
      updatedAt: new Date('2024-01-02'),
      isActive: true
    },
    {
      id: 'user_003',
      username: 'inactiveuser',
      email: 'inactive@example.com',
      firstName: 'Inactive',
      lastName: 'User',
      createdAt: new Date('2023-12-01'),
      updatedAt: new Date('2023-12-01'),
      isActive: false
    }
  ],

  sessions: () => [
    {
      id: 'session_001',
      userId: 'user_001',
      data: JSON.stringify(SessionFixtures.sessionData().data),
      createdAt: new Date(),
      lastActiveAt: new Date(),
      expiresAt: new Date(Date.now() + 3600000)
    },
    {
      id: 'session_002',
      userId: 'user_002',
      data: JSON.stringify(SessionFixtures.sessionData().data),
      createdAt: new Date(Date.now() - 1800000),
      lastActiveAt: new Date(Date.now() - 900000),
      expiresAt: new Date(Date.now() + 1800000)
    }
  ],

  messages: () => [
    {
      id: 'msg_001',
      sessionId: 'session_001',
      type: 'user',
      content: 'Hello, how are you?',
      timestamp: new Date(Date.now() - 300000),
      metadata: JSON.stringify({ fixture: true })
    },
    {
      id: 'msg_002',
      sessionId: 'session_001',
      type: 'assistant',
      content: 'Hello! I\'m doing well, thank you for asking. How can I help you today?',
      timestamp: new Date(Date.now() - 299000),
      metadata: JSON.stringify({ fixture: true, model: 'claude-3-sonnet' })
    },
    {
      id: 'msg_003',
      sessionId: 'session_001',
      type: 'user',
      content: 'Can you help me write some code?',
      timestamp: new Date(Date.now() - 120000),
      metadata: JSON.stringify({ fixture: true })
    }
  ]
};

// =============================================================================
// EXPORTS
// =============================================================================

export default {
  Kenny: KennyFixtures,
  Provider: ProviderFixtures,
  Tool: ToolFixtures,
  Session: SessionFixtures,
  Error: ErrorFixtures,
  Performance: PerformanceFixtures,
  Database: DatabaseFixtures
};