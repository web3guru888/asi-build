/**
 * ASI-Code Performance Benchmarks
 * 
 * This file contains performance benchmarks for critical ASI-Code operations.
 * These benchmarks help us track performance regressions and optimization improvements.
 */

import { bench, describe } from 'vitest';
import { ToolRegistry } from '../../src/tool/tool-registry.js';
import { DefaultSessionManager } from '../../src/session/session-manager.js';
import { ReadTool } from '../../src/tool/built-in-tools/read.js';
import { MessageBus } from '../../src/kenny/message-bus.js';
import { StateManager } from '../../src/kenny/state-manager.js';
import { PermissionManager } from '../../src/permission/permission-manager.js';
import { vol } from 'memfs';

// Mock storage for benchmarks
class BenchmarkStorage {
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
}

// Mock file system for benchmarks
vi.mock('fs/promises', () => {
  const memfs = require('memfs');
  return memfs.fs.promises;
});

vi.mock('fs', () => {
  const memfs = require('memfs');
  return memfs.fs;
});

describe('ASI-Code Performance Benchmarks', () => {
  let toolRegistry: ToolRegistry;
  let sessionManager: DefaultSessionManager;
  let messageBus: MessageBus;
  let stateManager: StateManager;
  let permissionManager: PermissionManager;
  let benchmarkStorage: BenchmarkStorage;

  beforeAll(async () => {
    // Setup components
    benchmarkStorage = new BenchmarkStorage();
    sessionManager = new DefaultSessionManager(benchmarkStorage as any);
    toolRegistry = new ToolRegistry({ maxConcurrentExecutions: 100 });
    messageBus = new MessageBus();
    stateManager = new StateManager();
    permissionManager = new PermissionManager({
      enableCaching: true,
      enableAuditing: false
    });

    // Initialize all components
    await toolRegistry.initialize();
    await stateManager.initialize();
    await permissionManager.initialize();

    // Setup test files
    vol.fromJSON({
      '/benchmark/small.txt': 'S'.repeat(100),
      '/benchmark/medium.txt': 'M'.repeat(1000),
      '/benchmark/large.txt': 'L'.repeat(10000),
      '/benchmark/xlarge.txt': 'X'.repeat(100000),
      '/benchmark/data.json': JSON.stringify({ 
        data: Array.from({ length: 1000 }, (_, i) => ({ id: i, value: `item-${i}` }))
      })
    });

    // Register tools
    const readTool = new ReadTool();
    await toolRegistry.register(readTool);
  });

  afterAll(async () => {
    await toolRegistry?.shutdown();
    await sessionManager?.cleanup();
    await permissionManager?.shutdown();
    vol.reset();
  });

  describe('Session Management Benchmarks', () => {
    bench('Create single session', async () => {
      const session = await sessionManager.createSession(`user-${Date.now()}`);
      await sessionManager.deleteSession(session.data.id);
    });

    bench('Create 10 sessions sequentially', async () => {
      const sessionIds: string[] = [];
      
      for (let i = 0; i < 10; i++) {
        const session = await sessionManager.createSession(`user-seq-${i}`);
        sessionIds.push(session.data.id);
      }
      
      // Cleanup
      for (const id of sessionIds) {
        await sessionManager.deleteSession(id);
      }
    });

    bench('Create 10 sessions concurrently', async () => {
      const promises = Array.from({ length: 10 }, (_, i) =>
        sessionManager.createSession(`user-conc-${i}`)
      );
      
      const sessions = await Promise.all(promises);
      
      // Cleanup
      await Promise.all(sessions.map(s => sessionManager.deleteSession(s.data.id)));
    });

    bench('Session lookup (hit)', async () => {
      const session = await sessionManager.createSession('lookup-test');
      
      // Perform lookup
      await sessionManager.getSession(session.data.id);
      
      await sessionManager.deleteSession(session.data.id);
    });

    bench('Session lookup (miss)', async () => {
      await sessionManager.getSession('non-existent-session');
    });
  });

  describe('Tool Execution Benchmarks', () => {
    bench('Execute read tool (small file)', async () => {
      await toolRegistry.execute('read', {
        path: '/benchmark/small.txt'
      }, {
        sessionId: 'bench-session',
        userId: 'bench-user',
        permissions: ['read_files'],
        workingDirectory: '/benchmark'
      });
    });

    bench('Execute read tool (medium file)', async () => {
      await toolRegistry.execute('read', {
        path: '/benchmark/medium.txt'
      }, {
        sessionId: 'bench-session',
        userId: 'bench-user',
        permissions: ['read_files'],
        workingDirectory: '/benchmark'
      });
    });

    bench('Execute read tool (large file)', async () => {
      await toolRegistry.execute('read', {
        path: '/benchmark/large.txt'
      }, {
        sessionId: 'bench-session',
        userId: 'bench-user',
        permissions: ['read_files'],
        workingDirectory: '/benchmark'
      });
    });

    bench('Concurrent tool executions (5x)', async () => {
      const promises = Array.from({ length: 5 }, () =>
        toolRegistry.execute('read', {
          path: '/benchmark/medium.txt'
        }, {
          sessionId: 'bench-session',
          userId: 'bench-user',
          permissions: ['read_files'],
          workingDirectory: '/benchmark'
        })
      );
      
      await Promise.all(promises);
    });

    bench('Tool registry operations', async () => {
      // Multiple registry operations
      const definitions = toolRegistry.list();
      const tool = toolRegistry.get('read');
      const metrics = toolRegistry.getMetrics();
    });
  });

  describe('Kenny Integration Pattern Benchmarks', () => {
    bench('Message bus publish (single)', async () => {
      await messageBus.publish({
        type: 'benchmark.test',
        source: 'benchmark',
        data: { timestamp: Date.now() }
      });
    });

    bench('Message bus publish (batch of 10)', async () => {
      const promises = Array.from({ length: 10 }, (_, i) =>
        messageBus.publish({
          type: 'benchmark.batch',
          source: 'benchmark',
          data: { index: i, timestamp: Date.now() }
        })
      );
      
      await Promise.all(promises);
    });

    bench('State manager set operation', async () => {
      await stateManager.set('benchmark.key', {
        id: Date.now(),
        data: 'benchmark data',
        timestamp: new Date()
      });
    });

    bench('State manager get operation', async () => {
      await stateManager.set('benchmark.get.key', { value: 'test' });
      await stateManager.get('benchmark.get.key');
    });

    bench('State manager batch operations', async () => {
      const setPromises = Array.from({ length: 5 }, (_, i) =>
        stateManager.set(`benchmark.batch.${i}`, { index: i })
      );
      
      await Promise.all(setPromises);
      
      const getPromises = Array.from({ length: 5 }, (_, i) =>
        stateManager.get(`benchmark.batch.${i}`)
      );
      
      await Promise.all(getPromises);
    });
  });

  describe('Permission System Benchmarks', () => {
    bench('Permission check (cached)', async () => {
      const request = {
        permissionId: 'read_files',
        context: {
          userId: 'bench-user',
          sessionId: 'bench-session',
          resource: 'file',
          operation: 'read'
        }
      };

      // First call to populate cache
      await permissionManager.checkPermission(request);
      
      // Benchmark the cached call
      await permissionManager.checkPermission(request);
    });

    bench('User permission lookup', async () => {
      await permissionManager.getUserPermissions('bench-user');
    });

    bench('Concurrent permission checks', async () => {
      const requests = Array.from({ length: 5 }, (_, i) => ({
        permissionId: 'read_files',
        context: {
          userId: 'bench-user',
          sessionId: 'bench-session',
          resource: `file-${i}`,
          operation: 'read'
        }
      }));

      const promises = requests.map(req => permissionManager.checkPermission(req));
      await Promise.all(promises);
    });
  });

  describe('Memory and Resource Benchmarks', () => {
    bench('JSON serialization (small object)', async () => {
      const data = { id: 1, name: 'test', timestamp: Date.now() };
      const serialized = JSON.stringify(data);
      const deserialized = JSON.parse(serialized);
    });

    bench('JSON serialization (large object)', async () => {
      const data = {
        id: 1,
        items: Array.from({ length: 1000 }, (_, i) => ({
          id: i,
          name: `item-${i}`,
          data: 'x'.repeat(100)
        }))
      };
      const serialized = JSON.stringify(data);
      const deserialized = JSON.parse(serialized);
    });

    bench('Array operations (filter + map)', async () => {
      const array = Array.from({ length: 10000 }, (_, i) => ({
        id: i,
        value: Math.random(),
        active: i % 2 === 0
      }));
      
      const filtered = array.filter(item => item.active);
      const mapped = filtered.map(item => ({ ...item, processed: true }));
    });

    bench('ID generation (nanoid)', async () => {
      const { nanoid } = await import('nanoid');
      const ids = Array.from({ length: 100 }, () => nanoid());
    });
  });
});