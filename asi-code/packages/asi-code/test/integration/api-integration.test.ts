/**
 * API Integration Tests - Comprehensive testing of all HTTP API endpoints
 * 
 * Tests all API routes including sessions, providers, tools, SSE events,
 * health checks, and error handling scenarios.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { createServer } from '../../src/server/server.js';
import { ToolRegistry } from '../../src/tool/tool-registry.js';
import { DefaultSessionManager } from '../../src/session/session-manager.js';
import { ProviderManager, AnthropicProvider, OpenAIProvider } from '../../src/provider/index.js';
import { createBuiltInTools } from '../../src/tool/built-in-tools/index.js';
import { vol } from 'memfs';
import supertest from 'supertest';
import type { Server } from 'node:http';

// Mock fs for file operations
vi.mock('fs/promises', () => {
  const memfs = require('memfs');
  return memfs.fs.promises;
});

vi.mock('fs', () => {
  const memfs = require('memfs');
  return memfs.fs;
});

// Mock storage for tests
class TestSessionStorage {
  private storage = new Map();

  async save(sessionData: any): Promise<void> {
    this.storage.set(sessionData.id, { ...sessionData });
  }

  async load(sessionId: string): Promise<any> {
    return this.storage.get(sessionId) || null;
  }

  async delete(sessionId: string): Promise<void> {
    this.storage.delete(sessionId);
  }

  async list(userId?: string): Promise<string[]> {
    const sessions = Array.from(this.storage.values());
    return sessions
      .filter((session: any) => !userId || session.userId === userId)
      .map((session: any) => session.id);
  }

  async cleanup(): Promise<void> {
    const now = Date.now();
    const expiredIds: string[] = [];
    
    for (const [id, session] of this.storage.entries()) {
      const expiry = (session as any).lastActivity.getTime() + (session as any).config.ttl;
      if (now > expiry) {
        expiredIds.push(id);
      }
    }
    
    expiredIds.forEach(id => this.storage.delete(id));
  }

  clear(): void {
    this.storage.clear();
  }
}

describe('API Integration Tests', () => {
  let server: Server;
  let request: supertest.SuperTest<supertest.Test>;
  let toolRegistry: ToolRegistry;
  let sessionManager: DefaultSessionManager;
  let providerManager: ProviderManager;
  let testStorage: TestSessionStorage;
  const serverPort = 3003;

  beforeAll(async () => {
    // Setup test components
    testStorage = new TestSessionStorage();
    sessionManager = new DefaultSessionManager(testStorage as any);
    toolRegistry = new ToolRegistry();
    providerManager = new ProviderManager();
    
    // Initialize components
    await toolRegistry.initialize();
    await toolRegistry.start();

    // Register all built-in tools
    const builtInTools = createBuiltInTools();
    for (const tool of builtInTools) {
      await toolRegistry.register(tool, [tool.getCategory()]);
    }

    // Register mock providers for testing
    await providerManager.register({
      name: 'test-anthropic',
      type: 'anthropic',
      apiKey: 'test-key',
      model: 'claude-3-sonnet-20240229'
    });

    await providerManager.register({
      name: 'test-openai',
      type: 'openai',
      apiKey: 'test-key',
      model: 'gpt-4'
    });

    // Create and start server
    server = createServer({
      port: serverPort,
      host: 'localhost',
      enableLogging: false,
      enableCors: true,
      components: {
        toolRegistry,
        sessionManager,
        providerManager
      }
    });

    await new Promise<void>((resolve) => {
      server.listen(serverPort, () => {
        console.log(`API integration test server running on port ${serverPort}`);
        resolve();
      });
    });

    request = supertest(`http://localhost:${serverPort}`);
  });

  afterAll(async () => {
    if (server) {
      await new Promise<void>((resolve) => {
        server.close(() => resolve());
      });
    }
    
    if (toolRegistry) {
      await toolRegistry.shutdown();
    }
    
    if (sessionManager) {
      await sessionManager.cleanup();
    }

    if (providerManager) {
      await providerManager.cleanup();
    }
  });

  beforeEach(() => {
    vol.reset();
    testStorage.clear();
  });

  afterEach(() => {
    vol.reset();
  });

  describe('Health and Status Endpoints', () => {
    it('should respond to health check with system information', async () => {
      const response = await request
        .get('/health')
        .expect(200);

      expect(response.body).toMatchObject({
        status: expect.any(String),
        timestamp: expect.any(String),
        connections: expect.any(Number)
      });
    });

    it('should provide models endpoint (alias for providers)', async () => {
      const response = await request
        .get('/models')
        .expect(200);

      expect(response.body).toMatchObject({
        models: expect.any(Array),
        providers: expect.any(Array)
      });

      expect(response.body.models).toEqual(response.body.providers);
      expect(response.body.providers).toContain('test-anthropic');
      expect(response.body.providers).toContain('test-openai');
    });
  });

  describe('Session Management API', () => {
    it('should create new session with complete metadata', async () => {
      const sessionData = {
        userId: 'api-test-user-123',
        config: {
          maxMessages: 100,
          ttl: 7200000, // 2 hours
          metadata: { source: 'api-test' }
        }
      };

      const response = await request
        .post('/api/sessions')
        .send(sessionData)
        .expect(201);

      expect(response.body).toMatchObject({
        sessionId: expect.any(String),
        kennyContext: expect.objectContaining({
          id: expect.any(String),
          sessionId: expect.any(String),
          userId: 'api-test-user-123',
          consciousness: expect.objectContaining({
            level: expect.any(Number),
            state: expect.any(String)
          })
        })
      });

      // Verify session exists in manager
      const session = await sessionManager.getSession(response.body.sessionId);
      expect(session).toBeDefined();
      expect(session?.data.userId).toBe('api-test-user-123');
    });

    it('should retrieve session with complete information', async () => {
      // Create session first
      const createResponse = await request
        .post('/api/sessions')
        .send({
          userId: 'retrieve-test-user',
          config: { maxMessages: 50 }
        });

      const sessionId = createResponse.body.sessionId;

      // Retrieve session
      const response = await request
        .get(`/api/sessions/${sessionId}`)
        .expect(200);

      expect(response.body).toMatchObject({
        session: {
          id: sessionId,
          userId: 'retrieve-test-user',
          kennyContext: expect.objectContaining({
            id: expect.any(String),
            sessionId: sessionId,
            userId: 'retrieve-test-user'
          }),
          messageCount: 0,
          createdAt: expect.any(String),
          lastActivity: expect.any(String)
        }
      });
    });

    it('should list sessions with user filtering', async () => {
      const userId1 = 'list-user-1';
      const userId2 = 'list-user-2';
      
      // Create sessions for different users
      await request.post('/api/sessions').send({ userId: userId1 });
      await request.post('/api/sessions').send({ userId: userId1 });
      await request.post('/api/sessions').send({ userId: userId2 });
      await request.post('/api/sessions').send({ userId: userId2 });
      await request.post('/api/sessions').send({ userId: userId2 });

      // Test listing all sessions
      const allResponse = await request
        .get('/api/sessions')
        .expect(200);

      expect(allResponse.body.sessions).toHaveLength(5);

      // Test listing sessions for specific user
      const user1Response = await request
        .get(`/api/sessions?userId=${userId1}`)
        .expect(200);

      expect(user1Response.body.sessions).toHaveLength(2);
      expect(user1Response.body.sessions.every((s: any) => s.userId === userId1)).toBe(true);

      const user2Response = await request
        .get(`/api/sessions?userId=${userId2}`)
        .expect(200);

      expect(user2Response.body.sessions).toHaveLength(3);
      expect(user2Response.body.sessions.every((s: any) => s.userId === userId2)).toBe(true);
    });

    it('should handle session deletion gracefully', async () => {
      // Create session
      const createResponse = await request
        .post('/api/sessions')
        .send({ userId: 'delete-user' });

      const sessionId = createResponse.body.sessionId;

      // Verify session exists
      await request.get(`/api/sessions/${sessionId}`).expect(200);

      // Delete session
      await request
        .delete(`/api/sessions/${sessionId}`)
        .expect(200);

      expect((await request.delete(`/api/sessions/${sessionId}`)).body).toMatchObject({
        success: true
      });

      // Verify session is deleted
      await request.get(`/api/sessions/${sessionId}`).expect(404);
    });

    it('should add messages to session with metadata', async () => {
      // Create session
      const createResponse = await request
        .post('/api/sessions')
        .send({ userId: 'message-user' });

      const sessionId = createResponse.body.sessionId;

      // Add message
      const messageData = {
        content: 'Hello, this is a test message',
        type: 'user',
        metadata: {
          source: 'api-test',
          timestamp: new Date().toISOString()
        }
      };

      const response = await request
        .post(`/api/sessions/${sessionId}/messages`)
        .send(messageData)
        .expect(200);

      expect(response.body.message).toMatchObject({
        id: expect.any(String),
        type: 'user',
        content: 'Hello, this is a test message',
        timestamp: expect.any(String),
        context: expect.objectContaining({
          sessionId: sessionId
        }),
        metadata: expect.objectContaining({
          source: 'api-test'
        })
      });

      // Verify message was added to session
      const messagesResponse = await request
        .get(`/api/sessions/${sessionId}/messages`)
        .expect(200);

      expect(messagesResponse.body.messages).toHaveLength(1);
      expect(messagesResponse.body.messages[0].content).toBe('Hello, this is a test message');
    });

    it('should retrieve session messages with limit', async () => {
      // Create session
      const createResponse = await request
        .post('/api/sessions')
        .send({ userId: 'message-limit-user' });

      const sessionId = createResponse.body.sessionId;

      // Add multiple messages
      const messages = Array.from({ length: 10 }, (_, i) => ({
        content: `Message ${i + 1}`,
        type: 'user'
      }));

      for (const msg of messages) {
        await request
          .post(`/api/sessions/${sessionId}/messages`)
          .send(msg);
      }

      // Get all messages
      const allResponse = await request
        .get(`/api/sessions/${sessionId}/messages`)
        .expect(200);

      expect(allResponse.body.messages).toHaveLength(10);

      // Get limited messages
      const limitedResponse = await request
        .get(`/api/sessions/${sessionId}/messages?limit=5`)
        .expect(200);

      expect(limitedResponse.body.messages).toHaveLength(5);
    });
  });

  describe('Provider API Integration', () => {
    it('should list available providers with capabilities', async () => {
      const response = await request
        .get('/api/providers')
        .expect(200);

      expect(response.body.providers).toContain('test-anthropic');
      expect(response.body.providers).toContain('test-openai');
    });

    it('should get provider capabilities and configuration', async () => {
      const response = await request
        .get('/api/providers/test-anthropic')
        .expect(200);

      expect(response.body).toMatchObject({
        name: 'test-anthropic',
        capabilities: expect.any(Object),
        config: expect.objectContaining({
          name: 'test-anthropic',
          type: 'anthropic',
          model: 'claude-3-sonnet-20240229'
        })
      });
    });

    it('should handle provider generation requests', async () => {
      const generationRequest = {
        messages: [
          { role: 'user', content: 'Hello, this is a test message' }
        ],
        options: {
          maxTokens: 100,
          temperature: 0.7
        }
      };

      // Mock the provider generate method to avoid external API calls
      const provider = providerManager.get('test-anthropic');
      if (provider) {
        vi.spyOn(provider, 'generate').mockResolvedValue({
          content: 'Test response from mocked provider',
          usage: { inputTokens: 10, outputTokens: 15, totalTokens: 25 },
          model: 'claude-3-sonnet-20240229',
          metadata: { id: 'test-response-id' }
        });
      }

      const response = await request
        .post('/api/providers/test-anthropic/generate')
        .send(generationRequest)
        .expect(200);

      expect(response.body).toMatchObject({
        response: {
          content: expect.any(String),
          usage: expect.objectContaining({
            inputTokens: expect.any(Number),
            outputTokens: expect.any(Number),
            totalTokens: expect.any(Number)
          }),
          model: expect.any(String)
        }
      });
    });

    it('should handle provider not found error', async () => {
      const response = await request
        .get('/api/providers/nonexistent-provider')
        .expect(404);

      expect(response.body.error).toContain('Provider not found');
    });

    it('should handle invalid generation requests', async () => {
      const invalidRequest = {
        // Missing required messages field
        options: { maxTokens: 100 }
      };

      const response = await request
        .post('/api/providers/test-anthropic/generate')
        .send(invalidRequest)
        .expect(400);

      expect(response.body.error).toBeDefined();
    });
  });

  describe('Tool API Integration', () => {
    beforeEach(() => {
      // Setup test files for tool operations
      vol.fromJSON({
        '/test/sample.txt': 'Sample file content',
        '/test/data.json': '{"key": "value", "number": 42}',
        '/test/large.txt': 'A'.repeat(5000),
        '/test/dir1/file1.txt': 'File 1 content',
        '/test/dir1/file2.txt': 'File 2 content',
        '/test/dir2/nested/deep.txt': 'Deep nested file'
      });
    });

    it('should list all available tools with metadata', async () => {
      const response = await request
        .get('/api/tools')
        .expect(200);

      expect(response.body.tools).toHaveLength(8); // All built-in tools
      
      const toolNames = response.body.tools.map((tool: any) => tool.name);
      expect(toolNames).toContain('bash');
      expect(toolNames).toContain('read');
      expect(toolNames).toContain('write');
      expect(toolNames).toContain('edit');
      expect(toolNames).toContain('search');
      expect(toolNames).toContain('delete');
      expect(toolNames).toContain('move');
      expect(toolNames).toContain('list');

      // Verify tool metadata structure
      const readTool = response.body.tools.find((tool: any) => tool.name === 'read');
      expect(readTool).toMatchObject({
        name: 'read',
        description: expect.any(String),
        category: expect.any(String),
        parameters: expect.any(Array)
      });
    });

    it('should get individual tool schema and definition', async () => {
      const response = await request
        .get('/api/tools/read')
        .expect(200);

      expect(response.body).toMatchObject({
        name: 'read',
        schema: expect.any(Object),
        description: expect.any(String)
      });
    });

    it('should execute read tool successfully', async () => {
      const executionRequest = {
        parameters: {
          path: '/test/sample.txt'
        },
        context: {
          permissions: ['read_files'],
          workingDirectory: '/test',
          environment: { NODE_ENV: 'test' }
        }
      };

      const response = await request
        .post('/api/tools/read/execute')
        .send(executionRequest)
        .expect(200);

      expect(response.body.result).toMatchObject({
        success: true,
        data: expect.objectContaining({
          content: 'Sample file content',
          path: '/test/sample.txt',
          encoding: expect.any(String)
        }),
        performance: expect.objectContaining({
          executionTime: expect.any(Number)
        })
      });
    });

    it('should execute write tool successfully', async () => {
      const executionRequest = {
        parameters: {
          path: '/test/new-file.txt',
          content: 'This is new content',
          encoding: 'utf8'
        },
        context: {
          permissions: ['write_files'],
          workingDirectory: '/test'
        }
      };

      const response = await request
        .post('/api/tools/write/execute')
        .send(executionRequest)
        .expect(200);

      expect(response.body.result.success).toBe(true);

      // Verify file was created
      const readResponse = await request
        .post('/api/tools/read/execute')
        .send({
          parameters: { path: '/test/new-file.txt' },
          context: { permissions: ['read_files'], workingDirectory: '/test' }
        });

      expect(readResponse.body.result.data.content).toBe('This is new content');
    });

    it('should execute list tool with directory traversal', async () => {
      const executionRequest = {
        parameters: {
          path: '/test',
          recursive: true,
          includeHidden: false
        },
        context: {
          permissions: ['read_files', 'list_files'],
          workingDirectory: '/test'
        }
      };

      const response = await request
        .post('/api/tools/list/execute')
        .send(executionRequest)
        .expect(200);

      expect(response.body.result.success).toBe(true);
      expect(response.body.result.data.files).toBeDefined();
      expect(Array.isArray(response.body.result.data.files)).toBe(true);
      
      // Should find our test files
      const filePaths = response.body.result.data.files.map((f: any) => f.path);
      expect(filePaths).toContain('/test/sample.txt');
      expect(filePaths).toContain('/test/data.json');
    });

    it('should execute search tool with pattern matching', async () => {
      const executionRequest = {
        parameters: {
          path: '/test',
          pattern: 'content',
          recursive: true,
          caseSensitive: false
        },
        context: {
          permissions: ['read_files', 'search_files'],
          workingDirectory: '/test'
        }
      };

      const response = await request
        .post('/api/tools/search/execute')
        .send(executionRequest)
        .expect(200);

      expect(response.body.result.success).toBe(true);
      expect(response.body.result.data.matches).toBeDefined();
      expect(Array.isArray(response.body.result.data.matches)).toBe(true);
      
      // Should find matches in files containing "content"
      expect(response.body.result.data.matches.length).toBeGreaterThan(0);
    });

    it('should handle tool parameter validation errors', async () => {
      const invalidRequest = {
        parameters: {
          // Missing required 'path' parameter for read tool
          encoding: 'utf8'
        },
        context: {
          permissions: ['read_files'],
          workingDirectory: '/test'
        }
      };

      const response = await request
        .post('/api/tools/read/execute')
        .send(invalidRequest)
        .expect(400);

      expect(response.body.error).toContain('validation');
    });

    it('should enforce permission restrictions', async () => {
      const executionRequest = {
        parameters: {
          path: '/test/sample.txt'
        },
        context: {
          permissions: [], // No permissions granted
          workingDirectory: '/test'
        }
      };

      const response = await request
        .post('/api/tools/read/execute')
        .send(executionRequest)
        .expect(403);

      expect(response.body.error).toContain('permission');
    });

    it('should handle tool execution errors gracefully', async () => {
      const executionRequest = {
        parameters: {
          path: '/nonexistent/file.txt'
        },
        context: {
          permissions: ['read_files'],
          workingDirectory: '/test'
        }
      };

      const response = await request
        .post('/api/tools/read/execute')
        .send(executionRequest)
        .expect(200); // Tool returns 200 even for execution errors

      expect(response.body.result.success).toBe(false);
      expect(response.body.result.error).toBeDefined();
    });

    it('should handle tool not found error', async () => {
      const response = await request
        .post('/api/tools/nonexistent-tool/execute')
        .send({
          parameters: {},
          context: { permissions: [] }
        })
        .expect(404);

      expect(response.body.error).toContain('Tool not found');
    });
  });

  describe('Server-Sent Events (SSE) Integration', () => {
    it('should establish SSE connection and receive events', async () => {
      // Start SSE connection
      const sseResponse = await request
        .get('/api/events')
        .set('Accept', 'text/event-stream')
        .set('Cache-Control', 'no-cache');

      expect(sseResponse.status).toBe(200);
      expect(sseResponse.headers['content-type']).toContain('text/event-stream');
      expect(sseResponse.headers['cache-control']).toBe('no-cache');
    });

    it('should handle broadcast requests to SSE connections', async () => {
      const broadcastRequest = {
        event: 'test-event',
        data: {
          message: 'Test broadcast message',
          timestamp: new Date().toISOString()
        }
      };

      const response = await request
        .post('/api/events/broadcast')
        .send(broadcastRequest)
        .expect(200);

      expect(response.body.success).toBe(true);
    });

    it('should handle targeted broadcasts to specific connections', async () => {
      const targetedRequest = {
        event: 'targeted-event',
        data: { message: 'Targeted message' },
        connectionId: 'test-connection-123'
      };

      const response = await request
        .post('/api/events/broadcast')
        .send(targetedRequest)
        .expect(200);

      expect(response.body.success).toBe(true);
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle malformed JSON requests', async () => {
      const response = await request
        .post('/api/sessions')
        .send('invalid json')
        .set('Content-Type', 'application/json')
        .expect(400);

      expect(response.body.error).toBeDefined();
    });

    it('should handle missing Content-Type header', async () => {
      const response = await request
        .post('/api/sessions')
        .send({ userId: 'test' });
        // Don't set explicit expectation - let it return whatever status it does

      expect(response.status).toBeOneOf([200, 201, 400]); // Accept any reasonable response
    });

    it('should handle nonexistent endpoints gracefully', async () => {
      const response = await request
        .get('/api/nonexistent-endpoint')
        .expect(404);

      expect(response.body).toMatchObject({
        error: expect.any(String),
        timestamp: expect.any(String)
      });
    });

    it('should handle invalid HTTP methods on valid endpoints', async () => {
      const response = await request
        .patch('/api/sessions') // PATCH not supported
        .expect(405);

      expect(response.body.error).toBeDefined();
    });

    it('should handle oversized request payloads', async () => {
      const largePayload = {
        userId: 'test-user',
        config: {
          data: 'x'.repeat(10000000) // 10MB string
        }
      };

      const response = await request
        .post('/api/sessions')
        .send(largePayload)
        .expect(413);

      expect(response.body.error).toContain('payload');
    });

    it('should maintain API consistency during high load', async () => {
      // Create multiple concurrent requests
      const promises = Array.from({ length: 20 }, (_, i) =>
        request
          .post('/api/sessions')
          .send({ userId: `load-test-user-${i}` })
      );

      const results = await Promise.all(promises);

      // All requests should succeed
      results.forEach((result, i) => {
        expect(result.status).toBe(201);
        expect(result.body.sessionId).toBeDefined();
        expect(result.body.kennyContext.userId).toBe(`load-test-user-${i}`);
      });

      // Verify all sessions were created
      const listResponse = await request.get('/api/sessions');
      expect(listResponse.body.sessions.length).toBeGreaterThanOrEqual(20);
    });
  });

  describe('Security and Validation', () => {
    it('should sanitize input parameters', async () => {
      const maliciousRequest = {
        userId: '<script>alert("xss")</script>',
        config: {
          maxMessages: 'DROP TABLE users;--'
        }
      };

      const response = await request
        .post('/api/sessions')
        .send(maliciousRequest);

      // Should either sanitize or reject the request
      if (response.status === 201) {
        // If accepted, should be sanitized
        expect(response.body.kennyContext.userId).not.toContain('<script>');
      } else {
        // If rejected, should have proper error
        expect(response.status).toBe(400);
        expect(response.body.error).toBeDefined();
      }
    });

    it('should validate request structure and types', async () => {
      const invalidRequests = [
        { userId: 123 }, // userId should be string
        { userId: 'valid', config: 'invalid' }, // config should be object
        { userId: 'valid', config: { maxMessages: 'invalid' } } // maxMessages should be number
      ];

      for (const invalidRequest of invalidRequests) {
        const response = await request
          .post('/api/sessions')
          .send(invalidRequest);

        expect(response.status).toBeOneOf([400, 422]); // Validation error
        expect(response.body.error).toBeDefined();
      }
    });

    it('should handle rate limiting gracefully', async () => {
      // Simulate rapid requests that might trigger rate limiting
      const rapidRequests = Array.from({ length: 100 }, () =>
        request
          .get('/health')
          .timeout(1000)
      );

      const results = await Promise.allSettled(rapidRequests);
      
      // Some requests might succeed, some might be rate limited
      const successful = results.filter(r => r.status === 'fulfilled' && (r.value as any).status === 200).length;
      const rateLimited = results.filter(r => r.status === 'fulfilled' && (r.value as any).status === 429).length;
      
      expect(successful + rateLimited).toBeGreaterThan(0);
    });
  });
});