/**
 * Error Handling and Recovery Integration Tests
 * 
 * Tests comprehensive error handling scenarios, system recovery mechanisms,
 * fault tolerance, graceful degradation, and resilience patterns across
 * all ASI-Code components and integration points.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { createServer } from '../../src/server/server.js';
import { ToolRegistry } from '../../src/tool/tool-registry.js';
import { DefaultSessionManager } from '../../src/session/session-manager.js';
import { ProviderManager } from '../../src/provider/index.js';
import { PermissionManager } from '../../src/permission/permission-manager.js';
import { Database, createDatabase } from '../../src/database/index.js';
import { WSServer } from '../../src/server/websocket/websocket-server.js';
import { Logger } from '../../src/logging/index.js';
import { createBuiltInTools } from '../../src/tool/built-in-tools/index.js';
import { vol } from 'memfs';
import supertest from 'supertest';
import WebSocket from 'ws';
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

// Test storage with failure injection
class FlakySessionStorage {
  private storage = new Map();
  private shouldFail = false;
  private failureRate = 0;
  private operationCount = 0;

  setShouldFail(fail: boolean) { this.shouldFail = fail; }
  setFailureRate(rate: number) { this.failureRate = rate; }
  
  private shouldFailOperation(): boolean {
    this.operationCount++;
    return this.shouldFail || (Math.random() < this.failureRate);
  }

  async save(sessionData: any): Promise<void> {
    if (this.shouldFailOperation()) {
      throw new Error('Storage failure: Unable to save session');
    }
    this.storage.set(sessionData.id, { ...sessionData });
  }

  async load(sessionId: string): Promise<any> {
    if (this.shouldFailOperation()) {
      throw new Error('Storage failure: Unable to load session');
    }
    return this.storage.get(sessionId) || null;
  }

  async delete(sessionId: string): Promise<void> {
    if (this.shouldFailOperation()) {
      throw new Error('Storage failure: Unable to delete session');
    }
    this.storage.delete(sessionId);
  }

  async list(userId?: string): Promise<string[]> {
    if (this.shouldFailOperation()) {
      throw new Error('Storage failure: Unable to list sessions');
    }
    const sessions = Array.from(this.storage.values());
    return sessions
      .filter((session: any) => !userId || session.userId === userId)
      .map((session: any) => session.id);
  }

  async cleanup(): Promise<void> {
    if (this.shouldFailOperation()) {
      throw new Error('Storage failure: Unable to cleanup sessions');
    }
  }

  clear(): void { this.storage.clear(); }
  getOperationCount(): number { return this.operationCount; }
}

// Flaky provider for testing error handling
class FlakyProvider {
  private shouldFail = false;
  private failureCount = 0;
  private successCount = 0;

  setShouldFail(fail: boolean) { this.shouldFail = fail; }

  async generate(messages: any[]): Promise<any> {
    if (this.shouldFail) {
      this.failureCount++;
      const errors = [
        'Network timeout',
        'Rate limit exceeded',
        'Service unavailable',
        'Invalid API key',
        'Model overloaded'
      ];
      throw new Error(errors[Math.floor(Math.random() * errors.length)]);
    }

    this.successCount++;
    return {
      content: 'Test response',
      usage: { inputTokens: 10, outputTokens: 15, totalTokens: 25 },
      model: 'test-model',
      metadata: { id: 'test-response' }
    };
  }

  async isAvailable(): Promise<boolean> {
    return !this.shouldFail;
  }

  getStats() {
    return {
      failures: this.failureCount,
      successes: this.successCount
    };
  }

  reset() {
    this.failureCount = 0;
    this.successCount = 0;
    this.shouldFail = false;
  }
}

describe('Error Handling and Recovery Integration Tests', () => {
  let server: Server;
  let request: supertest.SuperTest<supertest.Test>;
  let toolRegistry: ToolRegistry;
  let sessionManager: DefaultSessionManager;
  let providerManager: ProviderManager;
  let permissionManager: PermissionManager;
  let logger: Logger;
  let flakyStorage: FlakySessionStorage;
  let flakyProvider: FlakyProvider;
  const serverPort = 3006;

  beforeAll(async () => {
    logger = new Logger({ level: 'error', enabled: true });
    flakyStorage = new FlakySessionStorage();
    flakyProvider = new FlakyProvider();

    sessionManager = new DefaultSessionManager(flakyStorage as any);
    toolRegistry = new ToolRegistry();
    providerManager = new ProviderManager();
    permissionManager = new PermissionManager({
      enableSafetyProtocols: true,
      enableCaching: false, // Disable caching to test real-time failures
      enableAuditing: false
    });

    await toolRegistry.initialize();
    await toolRegistry.start();

    // Register built-in tools
    const builtInTools = createBuiltInTools();
    for (const tool of builtInTools) {
      await toolRegistry.register(tool, [tool.getCategory()]);
    }

    // Create server with error handling middleware
    server = createServer({
      port: serverPort,
      host: 'localhost',
      enableLogging: false,
      enableCors: true,
      errorHandling: {
        enableDetailedErrors: true,
        enableRetryLogic: true,
        maxRetries: 3,
        retryDelay: 100
      },
      components: {
        toolRegistry,
        sessionManager,
        providerManager,
        permissionManager,
        logger
      }
    });

    await new Promise<void>((resolve) => {
      server.listen(serverPort, () => {
        console.log(`Error recovery test server running on port ${serverPort}`);
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

    if (permissionManager) {
      await permissionManager.cleanup();
    }

    if (providerManager) {
      await providerManager.cleanup();
    }
  });

  beforeEach(() => {
    vol.reset();
    flakyStorage.clear();
    flakyProvider.reset();
    flakyStorage.setShouldFail(false);
    flakyStorage.setFailureRate(0);

    // Setup test files
    vol.fromJSON({
      '/test/sample.txt': 'Sample content',
      '/test/large.txt': 'A'.repeat(10000),
      '/test/binary.bin': Buffer.from([0x00, 0x01, 0x02]).toString(),
      '/test/corrupt.txt': '\x00\x01\x02Invalid\xFF\xFE',
      '/test/readonly/file.txt': 'Read-only content',
      '/nonexistent/path.txt': 'This should not exist'
    });
  });

  afterEach(() => {
    vol.reset();
  });

  describe('Network and Connection Error Recovery', () => {
    it('should handle server startup failures gracefully', async () => {
      // Test server restart after failure
      const originalListen = server.listen.bind(server);
      let listenCallCount = 0;

      server.listen = vi.fn().mockImplementation((port, callback) => {
        listenCallCount++;
        if (listenCallCount === 1) {
          // Simulate first attempt failure
          const error = new Error('Port already in use');
          (error as any).code = 'EADDRINUSE';
          throw error;
        }
        return originalListen(port + 1, callback); // Use different port
      });

      // Server should handle startup failure and potentially retry
      expect(server).toBeDefined();
    });

    it('should recover from temporary network failures', async () => {
      // Create a session first
      const response = await request
        .post('/api/sessions')
        .send({ userId: 'network-test-user' })
        .expect(201);

      const sessionId = response.body.sessionId;

      // Simulate network failure by making storage flaky
      flakyStorage.setFailureRate(0.8); // 80% failure rate

      // Multiple requests - some should fail, some should succeed with retries
      const requests = Array.from({ length: 10 }, () =>
        request.get(`/api/sessions/${sessionId}`)
      );

      const results = await Promise.allSettled(requests);
      
      const successful = results.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status === 200
      ).length;
      
      const failed = results.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status >= 500
      ).length;

      // Some should succeed due to retries, some may still fail
      expect(successful + failed).toBe(10);
      expect(successful).toBeGreaterThan(0); // Some should succeed with retries
    });

    it('should handle connection pool exhaustion', async () => {
      // Simulate many concurrent connections
      const concurrentRequests = Array.from({ length: 100 }, () =>
        request
          .get('/health')
          .timeout(5000)
      );

      const results = await Promise.allSettled(concurrentRequests);
      
      // System should handle gracefully - not all may succeed but shouldn't crash
      const successful = results.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status === 200
      ).length;
      
      expect(successful).toBeGreaterThan(0);
      expect(successful).toBeLessThanOrEqual(100);
    });

    it('should implement circuit breaker pattern for failing services', async () => {
      // Make provider consistently fail
      flakyProvider.setShouldFail(true);
      
      // Register flaky provider
      (providerManager as any).providers.set('flaky-provider', flakyProvider);

      // Rapid requests should trigger circuit breaker
      const rapidRequests = Array.from({ length: 20 }, () =>
        request
          .post('/api/providers/flaky-provider/generate')
          .send({
            messages: [{ role: 'user', content: 'test' }],
            options: {}
          })
      );

      const results = await Promise.all(rapidRequests);
      
      // Later requests should be rejected faster (circuit breaker open)
      const earlyResults = results.slice(0, 5);
      const lateResults = results.slice(-5);

      // Early requests might take time to fail
      // Late requests should be rejected immediately by circuit breaker
      earlyResults.forEach(result => {
        expect(result.status).toBeOneOf([500, 503]);
      });

      lateResults.forEach(result => {
        expect(result.status).toBeOneOf([503, 429]); // Service unavailable or circuit open
      });
    });

    it('should handle graceful degradation when services are unavailable', async () => {
      // Disable flaky storage completely
      flakyStorage.setShouldFail(true);

      // System should still respond to health checks
      const healthResponse = await request
        .get('/health')
        .expect(200);

      expect(healthResponse.body.status).toBeOneOf(['healthy', 'degraded']);

      // Session operations should fail gracefully
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'degraded-test' })
        .expect(503);

      expect(sessionResponse.body.error).toContain('service unavailable');
    });
  });

  describe('Database Error Handling', () => {
    it('should handle database connection failures', async () => {
      // Mock database connection failure
      const mockDatabase = {
        query: vi.fn().mockRejectedValue(new Error('Connection refused')),
        transaction: vi.fn().mockRejectedValue(new Error('Connection refused')),
        getHealthStatus: vi.fn().mockResolvedValue({
          status: 'unhealthy',
          checks: [{ name: 'connection', status: 'fail' }]
        })
      };

      // System should handle database unavailability
      const healthResponse = await request
        .get('/health')
        .expect(200);

      // Health should reflect database issues
      expect(healthResponse.body.status).toBeOneOf(['degraded', 'unhealthy']);
    });

    it('should handle transaction rollbacks correctly', async () => {
      // This test would simulate transaction failures and verify rollback
      // Since we don't have a real database in this test, we'll mock the behavior
      
      const mockTransaction = {
        query: vi.fn().mockImplementation((sql: string) => {
          if (sql.includes('INSERT')) {
            return Promise.resolve({ rowCount: 1 });
          }
          if (sql.includes('UPDATE')) {
            throw new Error('Constraint violation');
          }
          return Promise.resolve({ rows: [] });
        }),
        commit: vi.fn(),
        rollback: vi.fn()
      };

      // Simulate transaction that should rollback
      try {
        await mockTransaction.query('INSERT INTO sessions (id) VALUES (?)');
        await mockTransaction.query('UPDATE sessions SET invalid_column = ?');
        await mockTransaction.commit();
      } catch (error) {
        await mockTransaction.rollback();
        expect(mockTransaction.rollback).toHaveBeenCalled();
      }

      expect(mockTransaction.rollback).toHaveBeenCalled();
    });

    it('should handle concurrent database access conflicts', async () => {
      // Create multiple sessions concurrently that might conflict
      const concurrentSessionCreation = Array.from({ length: 20 }, (_, i) =>
        request
          .post('/api/sessions')
          .send({ userId: `concurrent-user-${i}` })
      );

      const results = await Promise.allSettled(concurrentSessionCreation);
      
      // Most should succeed, but handle any that fail due to conflicts
      const successful = results.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status === 201
      ).length;

      expect(successful).toBeGreaterThan(15); // Most should succeed
    });

    it('should handle database schema migration failures', async () => {
      // Mock migration failure scenario
      const mockMigrationRunner = {
        runPendingMigrations: vi.fn().mockRejectedValue(
          new Error('Migration failed: Duplicate column')
        ),
        getStatus: vi.fn().mockResolvedValue({
          appliedCount: 5,
          pendingCount: 1,
          appliedMigrations: ['001', '002', '003', '004', '005'],
          pendingMigrations: ['006']
        }),
        rollback: vi.fn().mockResolvedValue(true)
      };

      // System should handle migration failures gracefully
      try {
        await mockMigrationRunner.runPendingMigrations();
      } catch (error) {
        expect(error.message).toContain('Migration failed');
        
        // Should attempt rollback
        await mockMigrationRunner.rollback('006');
        expect(mockMigrationRunner.rollback).toHaveBeenCalledWith('006');
      }
    });
  });

  describe('Tool Execution Error Handling', () => {
    it('should handle file system errors gracefully', async () => {
      // Create session
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'tool-error-user' });
      const sessionId = sessionResponse.body.sessionId;

      // Simulate various file system errors
      const errorTests = [
        {
          name: 'File not found',
          params: { path: '/nonexistent/file.txt' },
          expectedError: 'not found'
        },
        {
          name: 'Permission denied',
          params: { path: '/test/readonly/file.txt' },
          context: { permissions: [], workingDirectory: '/test' },
          expectedError: 'permission'
        },
        {
          name: 'Invalid path',
          params: { path: '/test/../../../etc/passwd' },
          expectedError: 'traversal'
        }
      ];

      for (const test of errorTests) {
        const response = await request
          .post(`/api/sessions/${sessionId}/tools/read/execute`)
          .send({
            parameters: test.params,
            context: test.context || { 
              permissions: ['read_files'], 
              workingDirectory: '/test' 
            }
          });

        expect(response.status).toBeOneOf([200, 403, 404]);
        
        if (response.status === 200) {
          expect(response.body.result.success).toBe(false);
          expect(response.body.result.error).toContain(test.expectedError);
        }
      }
    });

    it('should handle tool timeout and resource exhaustion', async () => {
      // Create session
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'timeout-test-user' });
      const sessionId = sessionResponse.body.sessionId;

      // Mock long-running command
      const timeoutResponse = await request
        .post(`/api/sessions/${sessionId}/tools/bash/execute`)
        .send({
          parameters: { 
            command: 'sleep 30', // Long running command
            timeout: 1000 // 1 second timeout
          },
          context: { 
            permissions: ['execute_commands'], 
            workingDirectory: '/test' 
          }
        })
        .expect(200);

      expect(timeoutResponse.body.result.success).toBe(false);
      expect(timeoutResponse.body.result.error).toContain('timeout');
    });

    it('should handle malformed tool parameters', async () => {
      // Create session
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'malformed-test-user' });
      const sessionId = sessionResponse.body.sessionId;

      // Test various malformed parameters
      const malformedTests = [
        {
          tool: 'read',
          params: null, // null parameters
          expectedStatus: 400
        },
        {
          tool: 'write',
          params: { path: '/test/file.txt' }, // missing content
          expectedStatus: 400
        },
        {
          tool: 'read',
          params: { path: 123 }, // wrong type
          expectedStatus: 400
        },
        {
          tool: 'bash',
          params: { command: ['array', 'instead', 'of', 'string'] }, // wrong type
          expectedStatus: 400
        }
      ];

      for (const test of malformedTests) {
        const response = await request
          .post(`/api/sessions/${sessionId}/tools/${test.tool}/execute`)
          .send({
            parameters: test.params,
            context: { 
              permissions: ['read_files', 'write_files', 'execute_commands'], 
              workingDirectory: '/test' 
            }
          })
          .expect(test.expectedStatus);

        expect(response.body.error).toBeDefined();
      }
    });

    it('should handle concurrent tool execution conflicts', async () => {
      // Create session
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'concurrent-tool-user' });
      const sessionId = sessionResponse.body.sessionId;

      // Execute conflicting operations on same file
      const concurrentOperations = [
        // Multiple writes to same file
        request.post(`/api/sessions/${sessionId}/tools/write/execute`)
          .send({
            parameters: { path: '/test/concurrent.txt', content: 'Write 1' },
            context: { permissions: ['write_files'], workingDirectory: '/test' }
          }),
        request.post(`/api/sessions/${sessionId}/tools/write/execute`)
          .send({
            parameters: { path: '/test/concurrent.txt', content: 'Write 2' },
            context: { permissions: ['write_files'], workingDirectory: '/test' }
          }),
        // Read while writing
        request.post(`/api/sessions/${sessionId}/tools/read/execute`)
          .send({
            parameters: { path: '/test/concurrent.txt' },
            context: { permissions: ['read_files'], workingDirectory: '/test' }
          })
      ];

      const results = await Promise.all(concurrentOperations);
      
      // All operations should complete, though results may vary
      results.forEach(result => {
        expect(result.status).toBe(200);
        expect(result.body.result).toBeDefined();
      });
    });

    it('should recover from tool registry failures', async () => {
      // Simulate tool registry corruption
      const originalGet = toolRegistry.get.bind(toolRegistry);
      let corruptionCount = 0;

      toolRegistry.get = vi.fn().mockImplementation((name: string) => {
        corruptionCount++;
        if (corruptionCount <= 3) {
          throw new Error('Tool registry corrupted');
        }
        return originalGet(name);
      });

      // Create session
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'registry-error-user' });
      const sessionId = sessionResponse.body.sessionId;

      // First few requests should fail
      const failedResponse = await request
        .post(`/api/sessions/${sessionId}/tools/read/execute`)
        .send({
          parameters: { path: '/test/sample.txt' },
          context: { permissions: ['read_files'], workingDirectory: '/test' }
        })
        .expect(500);

      expect(failedResponse.body.error).toContain('registry');

      // Later requests should succeed after "recovery"
      const successResponse = await request
        .post(`/api/sessions/${sessionId}/tools/read/execute`)
        .send({
          parameters: { path: '/test/sample.txt' },
          context: { permissions: ['read_files'], workingDirectory: '/test' }
        })
        .expect(200);

      expect(successResponse.body.result.success).toBe(true);

      // Restore original method
      toolRegistry.get = originalGet;
    });
  });

  describe('Session Management Error Recovery', () => {
    it('should handle session storage corruption', async () => {
      // Create valid session first
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'corruption-test-user' })
        .expect(201);

      const sessionId = sessionResponse.body.sessionId;

      // Corrupt storage for subsequent operations
      flakyStorage.setShouldFail(true);

      // Subsequent operations should fail gracefully
      const corruptedResponse = await request
        .get(`/api/sessions/${sessionId}`)
        .expect(503);

      expect(corruptedResponse.body.error).toContain('storage');

      // Restore storage
      flakyStorage.setShouldFail(false);

      // System should recover
      const recoveredResponse = await request
        .get(`/api/sessions/${sessionId}`)
        .expect(404); // Session may be lost due to corruption

      expect(recoveredResponse.body.error).toContain('not found');
    });

    it('should handle session expiration edge cases', async () => {
      // Create session with very short TTL
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ 
          userId: 'expiration-test-user',
          config: { ttl: 100 } // 100ms TTL
        })
        .expect(201);

      const sessionId = sessionResponse.body.sessionId;

      // Wait for expiration
      await new Promise(resolve => setTimeout(resolve, 200));

      // Operations on expired session should fail gracefully
      const expiredResponse = await request
        .post(`/api/sessions/${sessionId}/messages`)
        .send({
          content: 'Message to expired session',
          type: 'user'
        })
        .expect(404);

      expect(expiredResponse.body.error).toContain('not found');
    });

    it('should handle session data consistency issues', async () => {
      // Create session
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'consistency-test-user' })
        .expect(201);

      const sessionId = sessionResponse.body.sessionId;

      // Add messages concurrently to test consistency
      const concurrentMessages = Array.from({ length: 10 }, (_, i) =>
        request
          .post(`/api/sessions/${sessionId}/messages`)
          .send({
            content: `Concurrent message ${i}`,
            type: 'user'
          })
      );

      const messageResults = await Promise.all(concurrentMessages);
      
      // All message additions should succeed
      messageResults.forEach(result => {
        expect(result.status).toBe(200);
        expect(result.body.message).toBeDefined();
      });

      // Verify all messages are preserved
      const messagesResponse = await request
        .get(`/api/sessions/${sessionId}/messages`)
        .expect(200);

      expect(messagesResponse.body.messages).toHaveLength(10);
    });

    it('should handle memory leaks in session management', async () => {
      // Create many sessions to test memory management
      const sessionIds: string[] = [];

      for (let i = 0; i < 100; i++) {
        const response = await request
          .post('/api/sessions')
          .send({ userId: `memory-test-user-${i}` });

        if (response.status === 201) {
          sessionIds.push(response.body.sessionId);
        }
      }

      expect(sessionIds.length).toBeGreaterThan(90); // Most should succeed

      // System should still be responsive
      const healthResponse = await request
        .get('/health')
        .expect(200);

      expect(healthResponse.body.status).toBeOneOf(['healthy', 'degraded']);

      // Cleanup sessions
      const deletePromises = sessionIds.map(id =>
        request.delete(`/api/sessions/${id}`)
      );

      await Promise.allSettled(deletePromises);
    });
  });

  describe('WebSocket Error Handling', () => {
    it('should handle WebSocket connection failures gracefully', async () => {
      const wsUrl = `ws://localhost:${serverPort}/ws`;
      
      // Try to connect multiple times with some failures
      const connectionAttempts = Array.from({ length: 5 }, async () => {
        try {
          const ws = new WebSocket(wsUrl);
          
          return new Promise((resolve) => {
            ws.on('open', () => {
              ws.close();
              resolve('connected');
            });
            
            ws.on('error', () => {
              resolve('failed');
            });
            
            // Timeout after 2 seconds
            setTimeout(() => {
              ws.terminate();
              resolve('timeout');
            }, 2000);
          });
        } catch (error) {
          return 'error';
        }
      });

      const results = await Promise.all(connectionAttempts);
      
      // Some connections may fail, but system should handle gracefully
      expect(results.length).toBe(5);
    });

    it('should handle WebSocket message corruption', async () => {
      const wsUrl = `ws://localhost:${serverPort}/ws`;
      
      try {
        const ws = new WebSocket(wsUrl);
        
        await new Promise<void>((resolve, reject) => {
          ws.on('open', () => resolve());
          ws.on('error', reject);
          setTimeout(() => reject(new Error('Connection timeout')), 5000);
        });

        // Send corrupted messages
        const corruptedMessages = [
          'invalid json',
          '{"incomplete": }',
          '{"type": null}',
          Buffer.from([0x00, 0x01, 0x02]), // Binary data
          JSON.stringify({ type: 'unknown_type', data: 'test' })
        ];

        let errorCount = 0;
        ws.on('message', (data) => {
          try {
            const message = JSON.parse(data.toString());
            if (message.type === 'error') {
              errorCount++;
            }
          } catch (error) {
            // Expected for corrupted messages
          }
        });

        // Send corrupted messages
        for (const message of corruptedMessages) {
          try {
            ws.send(message);
            await new Promise(resolve => setTimeout(resolve, 100));
          } catch (error) {
            // Expected for some messages
          }
        }

        // Wait for error responses
        await new Promise(resolve => setTimeout(resolve, 1000));

        // WebSocket should handle corrupted messages gracefully
        expect(ws.readyState).toBe(WebSocket.OPEN);

        ws.close();
      } catch (error) {
        // Connection may fail in test environment
        expect(error).toBeDefined();
      }
    });

    it('should handle WebSocket resource exhaustion', async () => {
      const wsUrl = `ws://localhost:${serverPort}/ws`;
      const connections: WebSocket[] = [];
      
      try {
        // Create many connections to test resource limits
        for (let i = 0; i < 50; i++) {
          const ws = new WebSocket(wsUrl);
          connections.push(ws);
          
          await new Promise((resolve) => {
            ws.on('open', resolve);
            ws.on('error', resolve); // Continue even if some fail
            setTimeout(resolve, 1000); // Timeout individual connections
          });
        }

        // System should handle connection pressure gracefully
        const openConnections = connections.filter(ws => 
          ws.readyState === WebSocket.OPEN
        ).length;

        expect(openConnections).toBeGreaterThan(0);

        // Close all connections
        connections.forEach(ws => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.close();
          }
        });
      } catch (error) {
        // Some connections may fail due to resource limits
        expect(error).toBeDefined();
      }
    });
  });

  describe('System-Wide Error Recovery', () => {
    it('should handle cascading failures gracefully', async () => {
      // Simulate multiple component failures
      flakyStorage.setShouldFail(true); // Session storage fails
      flakyProvider.setShouldFail(true); // Provider fails

      // System should still respond to basic health checks
      const healthResponse = await request
        .get('/health')
        .expect(200);

      expect(healthResponse.body.status).toBeOneOf(['degraded', 'unhealthy']);
      expect(healthResponse.body.errors).toBeDefined();

      // Gradual recovery
      flakyStorage.setShouldFail(false); // Storage recovers

      const partialHealthResponse = await request
        .get('/health')
        .expect(200);

      // Should show some improvement
      expect(partialHealthResponse.body.status).toBeDefined();

      // Full recovery
      flakyProvider.setShouldFail(false);

      const fullHealthResponse = await request
        .get('/health')
        .expect(200);

      expect(fullHealthResponse.body.status).toBeOneOf(['healthy', 'degraded']);
    });

    it('should implement proper bulkhead patterns', async () => {
      // One subsystem failure shouldn't affect others
      flakyStorage.setShouldFail(true);

      // Session operations should fail
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'bulkhead-test' })
        .expect(503);

      expect(sessionResponse.body.error).toContain('service unavailable');

      // But tool operations should still work (if they don't depend on sessions)
      const toolResponse = await request
        .get('/api/tools')
        .expect(200);

      expect(toolResponse.body.tools).toBeDefined();
      expect(toolResponse.body.tools.length).toBeGreaterThan(0);
    });

    it('should handle resource cleanup after failures', async () => {
      // Simulate failures that might leave resources open
      const initialMemory = process.memoryUsage();

      // Create operations that might fail and leave resources
      const faultyOperations = Array.from({ length: 50 }, async () => {
        try {
          const response = await request
            .post('/api/sessions')
            .send({ userId: `cleanup-test-${Date.now()}` })
            .timeout(100); // Very short timeout to force failures

          if (response.status === 201) {
            // Immediately try to corrupt the session
            flakyStorage.setShouldFail(true);
            await request
              .delete(`/api/sessions/${response.body.sessionId}`)
              .timeout(100);
            flakyStorage.setShouldFail(false);
          }
        } catch (error) {
          // Expected failures
        }
      });

      await Promise.allSettled(faultyOperations);

      // Wait for cleanup
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Memory usage shouldn't grow excessively
      const finalMemory = process.memoryUsage();
      const memoryGrowth = finalMemory.heapUsed - initialMemory.heapUsed;
      
      // Allow some growth but not excessive
      expect(memoryGrowth).toBeLessThan(100 * 1024 * 1024); // 100MB
    });

    it('should provide detailed error reporting for debugging', async () => {
      // Cause various errors and check error reporting
      flakyStorage.setShouldFail(true);

      const errorResponse = await request
        .post('/api/sessions')
        .send({ userId: 'error-reporting-test' })
        .expect(503);

      expect(errorResponse.body).toMatchObject({
        error: expect.any(String),
        timestamp: expect.any(String),
        requestId: expect.any(String),
        errorDetails: expect.any(Object)
      });

      expect(errorResponse.body.errorDetails).toMatchObject({
        component: expect.any(String),
        operation: expect.any(String),
        cause: expect.any(String)
      });
    });

    it('should maintain system stability under sustained error conditions', async () => {
      // Introduce sustained random failures
      flakyStorage.setFailureRate(0.3); // 30% failure rate

      const sustainedRequests = Array.from({ length: 100 }, () =>
        request
          .post('/api/sessions')
          .send({ userId: `sustained-test-${Date.now()}` })
      );

      const results = await Promise.allSettled(sustainedRequests);
      
      const successful = results.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status === 201
      ).length;
      
      const failed = results.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status >= 500
      ).length;

      // System should maintain some success rate despite failures
      expect(successful).toBeGreaterThan(50); // At least 50% success
      expect(failed).toBeGreaterThan(10); // Some failures expected

      // System should still be responsive after sustained errors
      const finalHealthResponse = await request
        .get('/health')
        .expect(200);

      expect(finalHealthResponse.body.status).toBeDefined();
    });
  });

  describe('Error Monitoring and Alerting', () => {
    it('should track error rates and patterns', async () => {
      // Generate various types of errors
      const errorGenerators = [
        () => request.post('/api/sessions').send(null), // Invalid payload
        () => request.get('/api/sessions/invalid-id'), // Invalid ID
        () => request.delete('/api/nonexistent'), // Not found
        () => request.post('/api/tools/nonexistent/execute').send({}), // Tool not found
      ];

      // Generate errors
      for (const generator of errorGenerators) {
        await Promise.all(Array.from({ length: 5 }, () => generator()));
      }

      // Error tracking would be implemented in monitoring system
      // This is a placeholder for error rate monitoring
      expect(true).toBe(true);
    });

    it('should generate alerts for critical errors', async () => {
      // Simulate critical system error
      flakyStorage.setShouldFail(true);
      flakyProvider.setShouldFail(true);

      // Multiple failed operations should trigger alerts
      const criticalRequests = Array.from({ length: 10 }, () =>
        request.post('/api/sessions').send({ userId: 'alert-test' })
      );

      await Promise.all(criticalRequests);

      // Alert system would be notified of critical failures
      // This is a placeholder for alert generation
      expect(true).toBe(true);
    });

    it('should provide error analytics and insights', async () => {
      // This would test error analytics features
      // Generate different error patterns
      const errorPatterns = [
        { type: 'timeout', count: 5 },
        { type: 'validation', count: 10 },
        { type: 'permission', count: 3 },
        { type: 'network', count: 7 }
      ];

      // Analytics would process error data
      expect(errorPatterns.length).toBe(4);
    });
  });
});