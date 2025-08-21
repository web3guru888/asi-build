/**
 * Performance and Load Testing Suite for ASI-Code
 */

import { describe, it, expect, beforeAll, afterAll, bench } from 'vitest';
import { ToolRegistry } from '../../src/tool/tool-registry.js';
import { DefaultSessionManager } from '../../src/session/session-manager.js';
import { ReadTool } from '../../src/tool/built-in-tools/read.js';
import { MessageBus } from '../../src/kenny/message-bus.js';
import { StateManager } from '../../src/kenny/state-manager.js';
import { PermissionManager } from '../../src/permission/permission-manager.js';
import { vol } from 'memfs';
import { createMockToolExecutionContext } from '../test-utils.js';

// Mock fs for performance tests
vi.mock('fs/promises', () => {
  const memfs = require('memfs');
  return memfs.fs.promises;
});

vi.mock('fs', () => {
  const memfs = require('memfs');
  return memfs.fs;
});

// Mock storage for performance tests
class PerformanceTestStorage {
  private storage = new Map();

  async save(data: any): Promise<void> {
    this.storage.set(data.id, JSON.parse(JSON.stringify(data)));
  }

  async load(id: string): Promise<any> {
    return this.storage.get(id) || null;
  }

  async delete(id: string): Promise<void> {
    this.storage.delete(id);
  }

  async list(): Promise<string[]> {
    return Array.from(this.storage.keys());
  }

  async cleanup(): Promise<void> {
    this.storage.clear();
  }

  size(): number {
    return this.storage.size;
  }
}

describe('ASI-Code Performance Tests', () => {
  let toolRegistry: ToolRegistry;
  let sessionManager: DefaultSessionManager;
  let messageBus: MessageBus;
  let stateManager: StateManager;
  let permissionManager: PermissionManager;
  let testStorage: PerformanceTestStorage;

  beforeAll(async () => {
    // Setup components for performance testing
    testStorage = new PerformanceTestStorage();
    sessionManager = new DefaultSessionManager(testStorage as any);
    toolRegistry = new ToolRegistry({ maxConcurrentExecutions: 50 });
    messageBus = new MessageBus();
    stateManager = new StateManager();
    permissionManager = new PermissionManager({
      enableCaching: true,
      enableAuditing: false // Disable for performance
    });

    // Initialize components
    await toolRegistry.initialize();
    await stateManager.initialize();
    await permissionManager.initialize();

    // Setup test files
    vol.fromJSON({
      '/perf/small.txt': 'Small test file',
      '/perf/medium.txt': 'M'.repeat(1000),
      '/perf/large.txt': 'L'.repeat(10000),
      '/perf/data.json': JSON.stringify({ test: 'data', number: 123 })
    });

    // Register test tools
    const readTool = new ReadTool();
    await toolRegistry.register(readTool);
  });

  afterAll(async () => {
    await toolRegistry?.shutdown();
    await sessionManager?.cleanup();
    await permissionManager?.shutdown();
    vol.reset();
  });

  describe('Session Management Performance', () => {
    bench('Create 100 sessions', async () => {
      const promises = Array.from({ length: 100 }, (_, i) =>
        sessionManager.createSession(`user-${i}`, { persistHistory: false })
      );
      
      const sessions = await Promise.all(promises);
      expect(sessions).toHaveLength(100);
      
      // Cleanup
      await Promise.all(sessions.map(s => sessionManager.deleteSession(s.data.id)));
    });

    bench('Concurrent session access', async () => {
      // Create a session first
      const session = await sessionManager.createSession('concurrent-user');
      
      // Perform concurrent access
      const promises = Array.from({ length: 50 }, () =>
        sessionManager.getSession(session.data.id)
      );
      
      const results = await Promise.all(promises);
      expect(results.every(r => r !== null)).toBe(true);
      
      await sessionManager.deleteSession(session.data.id);
    });

    bench('Session creation with persistence', async () => {
      const persistentStorage = new PerformanceTestStorage();
      const persistentManager = new DefaultSessionManager(persistentStorage as any);
      
      const promises = Array.from({ length: 50 }, (_, i) =>
        persistentManager.createSession(`persistent-user-${i}`, { persistHistory: true })
      );
      
      const sessions = await Promise.all(promises);
      expect(sessions).toHaveLength(50);
      expect(persistentStorage.size()).toBe(50);
      
      await persistentManager.cleanup();
    });
  });

  describe('Tool Execution Performance', () => {
    let testContext: any;

    beforeAll(() => {
      testContext = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/perf'
      });
    });

    bench('Single tool execution', async () => {
      const result = await toolRegistry.execute('read', {
        path: '/perf/small.txt'
      }, testContext);
      
      expect(result.success).toBe(true);
    });

    bench('Concurrent tool executions', async () => {
      const promises = Array.from({ length: 20 }, () =>
        toolRegistry.execute('read', {
          path: '/perf/medium.txt'
        }, testContext)
      );
      
      const results = await Promise.all(promises);
      expect(results.every(r => r.success)).toBe(true);
    });

    bench('Tool execution with different file sizes', async () => {
      const files = [
        '/perf/small.txt',
        '/perf/medium.txt',
        '/perf/large.txt'
      ];
      
      const promises = files.map(path =>
        toolRegistry.execute('read', { path }, testContext)
      );
      
      const results = await Promise.all(promises);
      expect(results.every(r => r.success)).toBe(true);
    });

    bench('Tool registry operations', async () => {
      // Measure registry operations
      const definitions = toolRegistry.list();
      expect(definitions.length).toBeGreaterThan(0);
      
      const tool = toolRegistry.get('read');
      expect(tool).toBeDefined();
      
      const metrics = toolRegistry.getMetrics();
      expect(Array.isArray(metrics)).toBe(true);
    });
  });

  describe('Kenny Integration Pattern Performance', () => {
    bench('Message bus event publishing', async () => {
      const eventPromises = Array.from({ length: 100 }, (_, i) =>
        messageBus.publish({
          type: 'test.event',
          source: 'performance-test',
          data: { index: i, timestamp: Date.now() }
        })
      );
      
      await Promise.all(eventPromises);
    });

    bench('Message bus subscription and filtering', async () => {
      let eventCount = 0;
      
      // Setup subscriptions
      messageBus.subscribe({ type: 'perf.test' }, () => eventCount++);
      messageBus.subscribe({ type: /^perf\./ }, () => eventCount++);
      messageBus.subscribe({ source: 'perf-source' }, () => eventCount++);
      
      // Publish events
      const publishPromises = Array.from({ length: 50 }, (_, i) =>
        messageBus.publish({
          type: 'perf.test',
          source: 'perf-source',
          data: { index: i }
        })
      );
      
      await Promise.all(publishPromises);
      expect(eventCount).toBe(150); // 3 subscriptions × 50 events
    });

    bench('State manager operations', async () => {
      // Measure state operations
      const promises: Promise<void>[] = [];
      
      // Set operations
      for (let i = 0; i < 50; i++) {
        promises.push(stateManager.set(`test.item.${i}`, {
          id: i,
          value: `item-${i}`,
          timestamp: new Date()
        }));
      }
      
      await Promise.all(promises);
      
      // Get operations
      const getPromises = Array.from({ length: 50 }, (_, i) =>
        stateManager.get(`test.item.${i}`)
      );
      
      const results = await Promise.all(getPromises);
      expect(results.every(r => r !== undefined)).toBe(true);
    });
  });

  describe('Permission System Performance', () => {
    let testUser: any;
    let testSession: any;

    beforeAll(async () => {
      // Setup test permission and role
      await permissionManager.addPermission({
        id: 'perf_permission',
        name: 'Performance Test Permission',
        description: 'For performance testing',
        category: 'test',
        safetyLevel: 'safe',
        resourceTypes: ['test_resource']
      });

      await permissionManager.addRole({
        id: 'perf_role',
        name: 'Performance Test Role',
        description: 'Role for performance testing',
        permissions: ['perf_permission'],
        level: 'user'
      });

      testUser = await permissionManager.createUser({
        id: 'perf_user',
        username: 'perfuser',
        email: 'perf@test.com',
        roles: ['perf_role'],
        status: 'active'
      });

      testSession = await permissionManager.createSession(testUser.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Performance Test',
        status: 'active'
      });
    });

    bench('Permission checking with caching', async () => {
      const request = {
        permissionId: 'perf_permission',
        context: {
          userId: testUser.id,
          sessionId: testSession.id,
          resource: 'test_resource',
          operation: 'read'
        }
      };

      // First call - should miss cache
      let result = await permissionManager.checkPermission(request);
      expect(result.granted).toBe(true);

      // Subsequent calls - should hit cache
      const promises = Array.from({ length: 100 }, () =>
        permissionManager.checkPermission(request)
      );

      const results = await Promise.all(promises);
      expect(results.every(r => r.granted)).toBe(true);

      const stats = permissionManager.getStats();
      expect(stats.cacheHits).toBeGreaterThan(90);
    });

    bench('Concurrent permission checks', async () => {
      const requests = Array.from({ length: 50 }, (_, i) => ({
        permissionId: 'perf_permission',
        context: {
          userId: testUser.id,
          sessionId: testSession.id,
          resource: `test_resource_${i}`,
          operation: 'read'
        }
      }));

      const promises = requests.map(req =>
        permissionManager.checkPermission(req)
      );

      const results = await Promise.all(promises);
      expect(results.every(r => r.granted)).toBe(true);
    });

    bench('User permission lookup', async () => {
      const promises = Array.from({ length: 100 }, () =>
        permissionManager.getUserPermissions(testUser.id)
      );

      const results = await Promise.all(promises);
      expect(results.every(perms => perms.length > 0)).toBe(true);
    });
  });

  describe('Memory Usage and Leak Detection', () => {
    it('should not leak memory during intensive operations', async () => {
      const initialMemory = process.memoryUsage();
      
      // Perform intensive operations
      const operations = [];
      
      for (let i = 0; i < 1000; i++) {
        operations.push(
          sessionManager.createSession(`mem-test-${i}`, { persistHistory: false })
            .then(session => sessionManager.deleteSession(session.data.id))
        );
      }
      
      await Promise.all(operations);
      
      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }
      
      const finalMemory = process.memoryUsage();
      const memoryGrowth = finalMemory.heapUsed - initialMemory.heapUsed;
      
      // Memory growth should be reasonable (less than 50MB)
      expect(memoryGrowth).toBeLessThan(50 * 1024 * 1024);
    });

    it('should cleanup resources properly', async () => {
      const registry = new ToolRegistry();
      await registry.initialize();
      
      // Register multiple tools
      for (let i = 0; i < 10; i++) {
        const tool = new ReadTool();
        tool.definition.name = `read-tool-${i}`;
        await registry.register(tool);
      }
      
      expect(registry.list()).toHaveLength(10);
      
      // Shutdown should cleanup all resources
      await registry.shutdown();
      
      expect(registry.list()).toHaveLength(0);
    });
  });

  describe('Stress Testing', () => {
    it('should handle high-load scenarios', async () => {
      const startTime = Date.now();
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/perf'
      });

      // Create a large number of concurrent operations
      const promises = Array.from({ length: 200 }, (_, i) => {
        const operation = i % 3;
        
        switch (operation) {
          case 0:
            return toolRegistry.execute('read', {
              path: '/perf/small.txt'
            }, context);
          
          case 1:
            return sessionManager.createSession(`stress-user-${i}`)
              .then(s => sessionManager.deleteSession(s.data.id));
          
          case 2:
            return messageBus.publish({
              type: 'stress.test',
              source: 'stress-test',
              data: { index: i }
            });
        }
      });

      const results = await Promise.all(promises);
      const endTime = Date.now();
      
      // All operations should complete
      expect(results).toHaveLength(200);
      
      // Should complete within reasonable time (10 seconds)
      expect(endTime - startTime).toBeLessThan(10000);
      
      // Check system health after stress test
      const health = await toolRegistry.healthCheck();
      expect(health.status).toBe('healthy');
    });
  });

  describe('Benchmarking Core Operations', () => {
    bench('JSON serialization/deserialization', () => {
      const data = {
        id: 'test-123',
        name: 'Test Object',
        timestamp: new Date(),
        metadata: { key: 'value', number: 123 },
        array: Array.from({ length: 100 }, (_, i) => ({ index: i, value: `item-${i}` }))
      };
      
      const serialized = JSON.stringify(data);
      const deserialized = JSON.parse(serialized);
      
      expect(deserialized.id).toBe(data.id);
    });

    bench('ID generation', () => {
      const { nanoid } = require('nanoid');
      
      const ids = Array.from({ length: 1000 }, () => nanoid());
      const uniqueIds = new Set(ids);
      
      expect(uniqueIds.size).toBe(ids.length);
    });

    bench('Array operations', () => {
      const array = Array.from({ length: 10000 }, (_, i) => ({ id: i, value: `item-${i}` }));
      
      // Filter operations
      const filtered = array.filter(item => item.id % 2 === 0);
      expect(filtered.length).toBe(5000);
      
      // Map operations
      const mapped = array.map(item => ({ ...item, processed: true }));
      expect(mapped.length).toBe(10000);
      
      // Find operations
      const found = array.find(item => item.id === 5000);
      expect(found?.id).toBe(5000);
    });
  });
});