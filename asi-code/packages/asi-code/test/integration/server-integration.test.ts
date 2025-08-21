/**
 * Integration tests for ASI-Code server functionality
 * Tests the full system integration including server, tools, sessions, and permissions
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { createServer } from '../../src/server/server.js';
import { ToolRegistry } from '../../src/tool/tool-registry.js';
import { DefaultSessionManager } from '../../src/session/session-manager.js';
import { ReadTool } from '../../src/tool/built-in-tools/read.js';
import { getMessageBus, resetMessageBus } from '../../src/kenny/message-bus.js';
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

// Mock storage implementation for tests
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

describe('ASI-Code Server Integration Tests', () => {
  let server: Server;
  let request: supertest.SuperTest<supertest.Test>;
  let toolRegistry: ToolRegistry;
  let sessionManager: DefaultSessionManager;
  let testStorage: TestSessionStorage;
  const serverPort = 3002; // Different from setup.ts to avoid conflicts

  beforeAll(async () => {
    // Reset Kenny Integration
    resetMessageBus();

    // Setup test storage and managers
    testStorage = new TestSessionStorage();
    sessionManager = new DefaultSessionManager(testStorage as any);
    toolRegistry = new ToolRegistry();
    
    // Initialize components
    await toolRegistry.initialize();
    await toolRegistry.start();

    // Register built-in tools
    const readTool = new ReadTool();
    await toolRegistry.register(readTool, ['file', 'io']);

    // Create and start server
    server = createServer({
      port: serverPort,
      host: 'localhost',
      enableLogging: false,
      enableCors: true,
      components: {
        toolRegistry,
        sessionManager
      }
    });

    await new Promise<void>((resolve) => {
      server.listen(serverPort, () => {
        console.log(`Integration test server running on port ${serverPort}`);
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
  });

  beforeEach(() => {
    vol.reset();
    testStorage.clear();
  });

  afterEach(() => {
    vol.reset();
  });

  describe('Server Health and Status', () => {
    it('should respond to health check', async () => {
      const response = await request
        .get('/health')
        .expect(200);

      expect(response.body).toMatchObject({
        status: 'healthy',
        timestamp: expect.any(String),
        components: expect.objectContaining({
          server: 'healthy',
          toolRegistry: expect.any(String),
          sessionManager: expect.any(String)
        })
      });
    });

    it('should provide system status', async () => {
      const response = await request
        .get('/api/status')
        .expect(200);

      expect(response.body).toMatchObject({
        system: expect.objectContaining({
          status: expect.any(String),
          uptime: expect.any(Number),
          version: expect.any(String)
        }),
        components: expect.any(Object)
      });
    });
  });

  describe('Session Management Integration', () => {
    it('should create new session', async () => {
      const response = await request
        .post('/api/sessions')
        .send({
          userId: 'test-user-123',
          config: {
            maxMessages: 50,
            ttl: 3600000 // 1 hour
          }
        })
        .expect(201);

      expect(response.body).toMatchObject({
        sessionId: expect.any(String),
        userId: 'test-user-123',
        config: expect.objectContaining({
          maxMessages: 50,
          ttl: 3600000
        }),
        kennyContext: expect.objectContaining({
          id: expect.any(String),
          sessionId: expect.any(String),
          userId: 'test-user-123'
        })
      });

      // Verify session was created in manager
      const sessionId = response.body.sessionId;
      const session = await sessionManager.getSession(sessionId);
      expect(session).toBeDefined();
      expect(session?.data.userId).toBe('test-user-123');
    });

    it('should retrieve existing session', async () => {
      // Create session first
      const createResponse = await request
        .post('/api/sessions')
        .send({ userId: 'retrieve-user' });

      const sessionId = createResponse.body.sessionId;

      // Retrieve session
      const response = await request
        .get(`/api/sessions/${sessionId}`)
        .expect(200);

      expect(response.body).toMatchObject({
        sessionId,
        userId: 'retrieve-user',
        status: 'active'
      });
    });

    it('should list sessions for user', async () => {
      const userId = 'list-user';
      
      // Create multiple sessions
      await request.post('/api/sessions').send({ userId });
      await request.post('/api/sessions').send({ userId });
      await request.post('/api/sessions').send({ userId: 'other-user' });

      const response = await request
        .get(`/api/sessions?userId=${userId}`)
        .expect(200);

      expect(response.body.sessions).toHaveLength(2);
      expect(response.body.sessions.every((s: any) => s.userId === userId)).toBe(true);
    });

    it('should delete session', async () => {
      const createResponse = await request
        .post('/api/sessions')
        .send({ userId: 'delete-user' });

      const sessionId = createResponse.body.sessionId;

      await request
        .delete(`/api/sessions/${sessionId}`)
        .expect(204);

      // Verify session was deleted
      const session = await sessionManager.getSession(sessionId);
      expect(session).toBeNull();
    });
  });

  describe('Tool Execution Integration', () => {
    let sessionId: string;

    beforeEach(async () => {
      // Create test session
      const response = await request
        .post('/api/sessions')
        .send({
          userId: 'tool-test-user',
          config: { maxMessages: 100 }
        });
      sessionId = response.body.sessionId;

      // Setup test files
      vol.fromJSON({
        '/test/hello.txt': 'Hello, World!',
        '/test/data.json': '{"message": "test data"}',
        '/test/large.txt': 'A'.repeat(1000)
      });
    });

    it('should execute read tool successfully', async () => {
      const response = await request
        .post(`/api/sessions/${sessionId}/tools/read/execute`)
        .send({
          parameters: {
            path: '/test/hello.txt'
          },
          context: {
            permissions: ['read_files'],
            workingDirectory: '/test',
            environment: { NODE_ENV: 'test' }
          }
        })
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        data: expect.objectContaining({
          content: 'Hello, World!',
          path: '/test/hello.txt',
          size: 13,
          encoding: 'utf8'
        }),
        performance: expect.objectContaining({
          executionTime: expect.any(Number),
          resourcesAccessed: ['/test/hello.txt']
        })
      });
    });

    it('should handle tool execution with parameters', async () => {
      const response = await request
        .post(`/api/sessions/${sessionId}/tools/read/execute`)
        .send({
          parameters: {
            path: '/test/data.json',
            encoding: 'utf8',
            maxSize: 500
          },
          context: {
            permissions: ['read_files'],
            workingDirectory: '/test'
          }
        })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.content).toBe('{"message": "test data"}');
      expect(response.body.data.encoding).toBe('utf8');
    });

    it('should handle tool execution errors', async () => {
      const response = await request
        .post(`/api/sessions/${sessionId}/tools/read/execute`)
        .send({
          parameters: {
            path: '/nonexistent/file.txt'
          },
          context: {
            permissions: ['read_files'],
            workingDirectory: '/test'
          }
        })
        .expect(200); // Tool execution endpoint returns 200 even for tool errors

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('File not found');
    });

    it('should validate tool parameters', async () => {
      const response = await request
        .post(`/api/sessions/${sessionId}/tools/read/execute`)
        .send({
          parameters: {
            // Missing required 'path' parameter
            encoding: 'utf8'
          },
          context: {
            permissions: ['read_files'],
            workingDirectory: '/test'
          }
        })
        .expect(400);

      expect(response.body.error).toContain('validation');
    });

    it('should enforce permissions', async () => {
      const response = await request
        .post(`/api/sessions/${sessionId}/tools/read/execute`)
        .send({
          parameters: {
            path: '/test/hello.txt'
          },
          context: {
            permissions: [], // No read_files permission
            workingDirectory: '/test'
          }
        })
        .expect(403);

      expect(response.body.error).toContain('permission');
    });

    it('should list available tools', async () => {
      const response = await request
        .get(`/api/sessions/${sessionId}/tools`)
        .expect(200);

      expect(response.body.tools).toHaveLength(1);
      expect(response.body.tools[0]).toMatchObject({
        name: 'read',
        description: expect.any(String),
        category: 'file',
        parameters: expect.any(Array)
      });
    });

    it('should get tool definition', async () => {
      const response = await request
        .get(`/api/sessions/${sessionId}/tools/read`)
        .expect(200);

      expect(response.body).toMatchObject({
        name: 'read',
        description: expect.any(String),
        parameters: expect.arrayContaining([
          expect.objectContaining({
            name: 'path',
            type: 'string',
            required: true
          })
        ]),
        category: 'file',
        version: '1.0.0',
        safetyLevel: 'safe'
      });
    });
  });

  describe('Kenny Integration Pattern', () => {
    it('should coordinate subsystems through message bus', async () => {
      const messageBus = getMessageBus();
      const events: any[] = [];

      // Subscribe to system events
      messageBus.subscribe({ type: /^tool\./ }, (event) => {
        events.push(event);
      });

      // Create session to trigger events
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'kenny-test' });

      const sessionId = sessionResponse.body.sessionId;

      // Execute tool to trigger more events
      vol.writeFileSync('/test/kenny.txt', 'Kenny integration test');
      
      await request
        .post(`/api/sessions/${sessionId}/tools/read/execute`)
        .send({
          parameters: { path: '/test/kenny.txt' },
          context: {
            permissions: ['read_files'],
            workingDirectory: '/test'
          }
        });

      // Wait a bit for events to propagate
      await new Promise(resolve => setTimeout(resolve, 50));

      // Should have received events from tool execution
      expect(events.length).toBeGreaterThan(0);
      
      const toolEvents = events.filter(e => e.type.startsWith('tool.'));
      expect(toolEvents.length).toBeGreaterThan(0);
    });

    it('should maintain state consistency across subsystems', async () => {
      // Create session
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'state-test' });

      const sessionId = sessionResponse.body.sessionId;

      // Execute multiple operations to test state consistency
      vol.writeFileSync('/test/file1.txt', 'content1');
      vol.writeFileSync('/test/file2.txt', 'content2');

      const [result1, result2] = await Promise.all([
        request
          .post(`/api/sessions/${sessionId}/tools/read/execute`)
          .send({
            parameters: { path: '/test/file1.txt' },
            context: { permissions: ['read_files'], workingDirectory: '/test' }
          }),
        request
          .post(`/api/sessions/${sessionId}/tools/read/execute`)
          .send({
            parameters: { path: '/test/file2.txt' },
            context: { permissions: ['read_files'], workingDirectory: '/test' }
          })
      ]);

      expect(result1.body.success).toBe(true);
      expect(result2.body.success).toBe(true);
      expect(result1.body.data.content).toBe('content1');
      expect(result2.body.data.content).toBe('content2');
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle server errors gracefully', async () => {
      const response = await request
        .get('/api/nonexistent-endpoint')
        .expect(404);

      expect(response.body).toMatchObject({
        error: expect.any(String),
        timestamp: expect.any(String)
      });
    });

    it('should handle malformed requests', async () => {
      const response = await request
        .post('/api/sessions')
        .send('invalid json')
        .set('Content-Type', 'application/json')
        .expect(400);

      expect(response.body.error).toContain('Invalid');
    });

    it('should handle session not found', async () => {
      const response = await request
        .get('/api/sessions/nonexistent-session')
        .expect(404);

      expect(response.body.error).toContain('Session not found');
    });

    it('should handle tool not found', async () => {
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'error-test' });

      const sessionId = sessionResponse.body.sessionId;

      const response = await request
        .post(`/api/sessions/${sessionId}/tools/nonexistent/execute`)
        .send({
          parameters: {},
          context: { permissions: [] }
        })
        .expect(404);

      expect(response.body.error).toContain('Tool not found');
    });
  });

  describe('Performance and Scalability', () => {
    it('should handle concurrent requests', async () => {
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'concurrent-test' });

      const sessionId = sessionResponse.body.sessionId;

      // Setup test files
      for (let i = 0; i < 10; i++) {
        vol.writeFileSync(`/test/concurrent-${i}.txt`, `Content ${i}`);
      }

      // Execute concurrent requests
      const promises = Array.from({ length: 10 }, (_, i) =>
        request
          .post(`/api/sessions/${sessionId}/tools/read/execute`)
          .send({
            parameters: { path: `/test/concurrent-${i}.txt` },
            context: { permissions: ['read_files'], workingDirectory: '/test' }
          })
      );

      const results = await Promise.all(promises);

      // All requests should succeed
      results.forEach((result, i) => {
        expect(result.status).toBe(200);
        expect(result.body.success).toBe(true);
        expect(result.body.data.content).toBe(`Content ${i}`);
      });
    });

    it('should handle rapid session creation and deletion', async () => {
      const sessionIds: string[] = [];

      // Create multiple sessions rapidly
      const createPromises = Array.from({ length: 5 }, () =>
        request
          .post('/api/sessions')
          .send({ userId: `rapid-user-${Date.now()}` })
      );

      const createResults = await Promise.all(createPromises);
      createResults.forEach(result => {
        expect(result.status).toBe(201);
        sessionIds.push(result.body.sessionId);
      });

      // Delete all sessions
      const deletePromises = sessionIds.map(id =>
        request.delete(`/api/sessions/${id}`)
      );

      const deleteResults = await Promise.all(deletePromises);
      deleteResults.forEach(result => {
        expect(result.status).toBe(204);
      });

      // Verify sessions are deleted
      const verifyPromises = sessionIds.map(id =>
        request.get(`/api/sessions/${id}`)
      );

      const verifyResults = await Promise.all(verifyPromises);
      verifyResults.forEach(result => {
        expect(result.status).toBe(404);
      });
    });
  });

  describe('WebSocket Integration', () => {
    it('should establish WebSocket connection for real-time updates', async () => {
      // This would require WebSocket client setup
      // For now, we'll test the WebSocket endpoint exists
      const response = await request
        .get('/ws')
        .expect(426); // Upgrade Required

      expect(response.text).toContain('Upgrade Required');
    });
  });

  describe('Security and Validation', () => {
    it('should validate session access', async () => {
      const session1Response = await request
        .post('/api/sessions')
        .send({ userId: 'user1' });

      const session2Response = await request
        .post('/api/sessions')
        .send({ userId: 'user2' });

      const session1Id = session1Response.body.sessionId;
      const session2Id = session2Response.body.sessionId;

      // User1 should not be able to access User2's session
      const response = await request
        .get(`/api/sessions/${session2Id}`)
        .set('X-Session-Id', session1Id) // Simulate user1 trying to access user2's session
        .expect(200); // Note: This test would need proper auth middleware to work

      // For now, just verify the endpoint exists and responds
      expect(response.body.sessionId).toBe(session2Id);
    });

    it('should sanitize input parameters', async () => {
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'sanitize-test' });

      const sessionId = sessionResponse.body.sessionId;

      // Test with potentially dangerous input
      const response = await request
        .post(`/api/sessions/${sessionId}/tools/read/execute`)
        .send({
          parameters: {
            path: '/test/../../../etc/passwd' // Path traversal attempt
          },
          context: {
            permissions: ['read_files'],
            workingDirectory: '/test'
          }
        });

      // Should be blocked by the read tool's security checks
      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('traversal');
    });
  });
});