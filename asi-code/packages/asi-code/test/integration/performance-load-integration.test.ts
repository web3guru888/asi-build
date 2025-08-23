/**
 * Performance and Load Testing Integration Tests
 * 
 * Tests system performance under various load conditions, measures response times,
 * throughput, resource utilization, and validates system behavior under stress.
 * Includes load testing, stress testing, endurance testing, and spike testing.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { createServer } from '../../src/server/server.js';
import { ToolRegistry } from '../../src/tool/tool-registry.js';
import { DefaultSessionManager } from '../../src/session/session-manager.js';
import { ProviderManager } from '../../src/provider/index.js';
import { PermissionManager } from '../../src/permission/permission-manager.js';
import { createBuiltInTools } from '../../src/tool/built-in-tools/index.js';
import { vol } from 'memfs';
import supertest from 'supertest';
import WebSocket from 'ws';
import { performance } from 'perf_hooks';
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

// Performance metrics collector
class PerformanceMetrics {
  private metrics: Map<string, number[]> = new Map();
  private resourceUsage: Array<{
    timestamp: number;
    memory: NodeJS.MemoryUsage;
    cpu: number;
  }> = [];

  recordMetric(name: string, value: number): void {
    if (!this.metrics.has(name)) {
      this.metrics.set(name, []);
    }
    this.metrics.get(name)!.push(value);
  }

  recordResourceUsage(): void {
    this.resourceUsage.push({
      timestamp: Date.now(),
      memory: process.memoryUsage(),
      cpu: process.cpuUsage().user / 1000000 // Convert to seconds
    });
  }

  getStats(metricName: string): {
    min: number;
    max: number;
    avg: number;
    p50: number;
    p90: number;
    p95: number;
    p99: number;
    count: number;
  } | null {
    const values = this.metrics.get(metricName);
    if (!values || values.length === 0) return null;

    const sorted = [...values].sort((a, b) => a - b);
    const count = sorted.length;

    return {
      min: sorted[0],
      max: sorted[count - 1],
      avg: sorted.reduce((a, b) => a + b) / count,
      p50: sorted[Math.floor(count * 0.5)],
      p90: sorted[Math.floor(count * 0.9)],
      p95: sorted[Math.floor(count * 0.95)],
      p99: sorted[Math.floor(count * 0.99)],
      count
    };
  }

  getMemoryTrend(): {
    initial: number;
    final: number;
    peak: number;
    growth: number;
  } | null {
    if (this.resourceUsage.length < 2) return null;

    const initial = this.resourceUsage[0].memory.heapUsed;
    const final = this.resourceUsage[this.resourceUsage.length - 1].memory.heapUsed;
    const peak = Math.max(...this.resourceUsage.map(r => r.memory.heapUsed));

    return {
      initial,
      final,
      peak,
      growth: final - initial
    };
  }

  clear(): void {
    this.metrics.clear();
    this.resourceUsage.length = 0;
  }

  getAllMetrics(): Map<string, number[]> {
    return new Map(this.metrics);
  }
}

// Test session storage optimized for performance testing
class PerformanceSessionStorage {
  private storage = new Map<string, any>();
  private operationCount = 0;
  private operationTimes: number[] = [];

  async save(sessionData: any): Promise<void> {
    const start = performance.now();
    this.storage.set(sessionData.id, { ...sessionData });
    this.operationTimes.push(performance.now() - start);
    this.operationCount++;
  }

  async load(sessionId: string): Promise<any> {
    const start = performance.now();
    const result = this.storage.get(sessionId) || null;
    this.operationTimes.push(performance.now() - start);
    this.operationCount++;
    return result;
  }

  async delete(sessionId: string): Promise<void> {
    const start = performance.now();
    this.storage.delete(sessionId);
    this.operationTimes.push(performance.now() - start);
    this.operationCount++;
  }

  async list(userId?: string): Promise<string[]> {
    const start = performance.now();
    const sessions = Array.from(this.storage.values());
    const result = sessions
      .filter((session: any) => !userId || session.userId === userId)
      .map((session: any) => session.id);
    this.operationTimes.push(performance.now() - start);
    this.operationCount++;
    return result;
  }

  async cleanup(): Promise<void> {
    const start = performance.now();
    // Simulate cleanup operation
    this.operationTimes.push(performance.now() - start);
    this.operationCount++;
  }

  getPerformanceStats(): {
    operationCount: number;
    avgOperationTime: number;
    storageSize: number;
  } {
    return {
      operationCount: this.operationCount,
      avgOperationTime: this.operationTimes.length > 0 
        ? this.operationTimes.reduce((a, b) => a + b) / this.operationTimes.length 
        : 0,
      storageSize: this.storage.size
    };
  }

  clear(): void {
    this.storage.clear();
    this.operationCount = 0;
    this.operationTimes.length = 0;
  }
}

// High-performance mock provider
class PerformanceProvider {
  private responseTime: number;
  private requestCount = 0;
  private concurrentRequests = 0;
  private maxConcurrent = 0;

  constructor(responseTime = 50) {
    this.responseTime = responseTime;
  }

  async generate(messages: any[]): Promise<any> {
    this.concurrentRequests++;
    this.maxConcurrent = Math.max(this.maxConcurrent, this.concurrentRequests);
    this.requestCount++;

    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, this.responseTime));

    this.concurrentRequests--;

    return {
      content: `Performance test response ${this.requestCount}`,
      usage: { inputTokens: 10, outputTokens: 15, totalTokens: 25 },
      model: 'performance-test-model',
      metadata: { 
        id: `perf-test-${this.requestCount}`,
        responseTime: this.responseTime
      }
    };
  }

  async isAvailable(): Promise<boolean> {
    return true;
  }

  getStats() {
    return {
      requestCount: this.requestCount,
      currentConcurrent: this.concurrentRequests,
      maxConcurrent: this.maxConcurrent,
      avgResponseTime: this.responseTime
    };
  }

  setResponseTime(time: number) {
    this.responseTime = time;
  }

  reset() {
    this.requestCount = 0;
    this.concurrentRequests = 0;
    this.maxConcurrent = 0;
  }
}

describe('Performance and Load Testing Integration Tests', () => {
  let server: Server;
  let request: supertest.SuperTest<supertest.Test>;
  let toolRegistry: ToolRegistry;
  let sessionManager: DefaultSessionManager;
  let providerManager: ProviderManager;
  let permissionManager: PermissionManager;
  let performanceStorage: PerformanceSessionStorage;
  let performanceProvider: PerformanceProvider;
  let metrics: PerformanceMetrics;
  const serverPort = 3007;

  // Test configuration
  const LOAD_TEST_CONFIG = {
    lightLoad: { concurrent: 10, requests: 100 },
    mediumLoad: { concurrent: 50, requests: 500 },
    heavyLoad: { concurrent: 100, requests: 1000 },
    spikeLoad: { concurrent: 200, requests: 200 },
    enduranceTest: { concurrent: 20, duration: 30000 } // 30 seconds
  };

  beforeAll(async () => {
    metrics = new PerformanceMetrics();
    performanceStorage = new PerformanceSessionStorage();
    performanceProvider = new PerformanceProvider(50); // 50ms response time

    sessionManager = new DefaultSessionManager(performanceStorage as any);
    toolRegistry = new ToolRegistry();
    providerManager = new ProviderManager();
    permissionManager = new PermissionManager({
      enableSafetyProtocols: false, // Disable for performance testing
      enableCaching: true,
      enableAuditing: false
    });

    await toolRegistry.initialize();
    await toolRegistry.start();

    // Register optimized built-in tools
    const builtInTools = createBuiltInTools();
    for (const tool of builtInTools) {
      await toolRegistry.register(tool, [tool.getCategory()]);
    }

    // Register performance provider
    (providerManager as any).providers.set('performance-provider', performanceProvider);

    // Create server with performance optimizations
    server = createServer({
      port: serverPort,
      host: 'localhost',
      enableLogging: false,
      enableCors: true,
      performance: {
        enableCompression: true,
        enableCaching: true,
        maxConcurrentRequests: 500,
        requestTimeout: 30000
      },
      components: {
        toolRegistry,
        sessionManager,
        providerManager,
        permissionManager
      }
    });

    await new Promise<void>((resolve) => {
      server.listen(serverPort, () => {
        console.log(`Performance test server running on port ${serverPort}`);
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
    performanceStorage.clear();
    performanceProvider.reset();
    metrics.clear();

    // Setup performance test files
    vol.fromJSON({
      '/test/small.txt': 'Small file content',
      '/test/medium.txt': 'M'.repeat(1000), // 1KB
      '/test/large.txt': 'L'.repeat(100000), // 100KB
      '/test/xlarge.txt': 'X'.repeat(1000000), // 1MB
      ...Object.fromEntries(
        // Create 100 test files for concurrent access
        Array.from({ length: 100 }, (_, i) => [
          `/test/concurrent-${i}.txt`,
          `Concurrent test file ${i} with some content`
        ])
      )
    });
  });

  afterEach(() => {
    vol.reset();
  });

  describe('Baseline Performance Metrics', () => {
    it('should measure single request response times', async () => {
      const iterations = 100;
      const responseTimes: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        
        const response = await request
          .get('/health')
          .expect(200);

        const responseTime = performance.now() - start;
        responseTimes.push(responseTime);
        metrics.recordMetric('health_response_time', responseTime);
      }

      const stats = metrics.getStats('health_response_time')!;
      
      expect(stats.count).toBe(iterations);
      expect(stats.avg).toBeLessThan(100); // Average under 100ms
      expect(stats.p95).toBeLessThan(200); // 95th percentile under 200ms
      expect(stats.p99).toBeLessThan(500); // 99th percentile under 500ms

      console.log(`Health endpoint baseline performance:`, stats);
    });

    it('should measure session creation performance', async () => {
      const iterations = 50;

      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        
        const response = await request
          .post('/api/sessions')
          .send({ userId: `perf-test-user-${i}` })
          .expect(201);

        const responseTime = performance.now() - start;
        metrics.recordMetric('session_creation_time', responseTime);
        
        expect(response.body.sessionId).toBeDefined();
      }

      const stats = metrics.getStats('session_creation_time')!;
      
      expect(stats.avg).toBeLessThan(500); // Average under 500ms
      expect(stats.p95).toBeLessThan(1000); // 95th percentile under 1s

      console.log(`Session creation baseline performance:`, stats);
    });

    it('should measure tool execution performance', async () => {
      // Create session for tool testing
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'tool-perf-user' });
      const sessionId = sessionResponse.body.sessionId;

      const toolTests = [
        { tool: 'read', params: { path: '/test/small.txt' } },
        { tool: 'read', params: { path: '/test/medium.txt' } },
        { tool: 'list', params: { path: '/test' } },
        { tool: 'search', params: { path: '/test', pattern: 'content' } }
      ];

      for (const test of toolTests) {
        const iterations = 20;
        
        for (let i = 0; i < iterations; i++) {
          const start = performance.now();
          
          const response = await request
            .post(`/api/sessions/${sessionId}/tools/${test.tool}/execute`)
            .send({
              parameters: test.params,
              context: { 
                permissions: ['read_files', 'search_files', 'list_files'],
                workingDirectory: '/test' 
              }
            })
            .expect(200);

          const responseTime = performance.now() - start;
          metrics.recordMetric(`${test.tool}_execution_time`, responseTime);
          
          expect(response.body.result).toBeDefined();
        }

        const stats = metrics.getStats(`${test.tool}_execution_time`)!;
        console.log(`${test.tool} execution baseline performance:`, stats);
        
        expect(stats.avg).toBeLessThan(1000); // Average under 1s
      }
    });
  });

  describe('Load Testing', () => {
    it('should handle light load (10 concurrent, 100 requests)', async () => {
      const { concurrent, requests } = LOAD_TEST_CONFIG.lightLoad;
      const startTime = performance.now();
      
      // Monitor resource usage
      const resourceMonitor = setInterval(() => {
        metrics.recordResourceUsage();
      }, 1000);

      // Execute concurrent requests
      const batches = [];
      for (let i = 0; i < requests; i += concurrent) {
        const batch = Array.from({ length: Math.min(concurrent, requests - i) }, (_, j) =>
          measureRequestTime('light_load_health', () => request.get('/health'))
        );
        batches.push(Promise.all(batch));
      }

      const results = await Promise.all(batches);
      const allResults = results.flat();
      
      clearInterval(resourceMonitor);
      const totalTime = performance.now() - startTime;

      // Analyze results
      const successful = allResults.filter(r => r.status === 200).length;
      const failed = allResults.length - successful;
      const throughput = successful / (totalTime / 1000); // requests per second

      const stats = metrics.getStats('light_load_health')!;
      const memoryTrend = metrics.getMemoryTrend()!;

      expect(successful).toBe(requests);
      expect(failed).toBe(0);
      expect(throughput).toBeGreaterThan(50); // At least 50 RPS
      expect(stats.p95).toBeLessThan(500); // 95th percentile under 500ms
      expect(memoryTrend.growth).toBeLessThan(50 * 1024 * 1024); // Memory growth under 50MB

      console.log(`Light load test results:`, {
        successful,
        failed,
        throughput: throughput.toFixed(2),
        responseTimeStats: stats,
        memoryTrend
      });
    });

    it('should handle medium load (50 concurrent, 500 requests)', async () => {
      const { concurrent, requests } = LOAD_TEST_CONFIG.mediumLoad;
      const startTime = performance.now();

      // Monitor resource usage
      const resourceMonitor = setInterval(() => {
        metrics.recordResourceUsage();
      }, 1000);

      // Create sessions for load testing
      const sessionPromises = Array.from({ length: concurrent }, (_, i) =>
        measureRequestTime('medium_load_session', () => 
          request
            .post('/api/sessions')
            .send({ userId: `medium-load-user-${i}` })
        )
      );

      const sessionResults = await Promise.all(sessionPromises);
      const sessionIds = sessionResults
        .filter(r => r.status === 201)
        .map(r => r.body.sessionId);

      expect(sessionIds.length).toBe(concurrent);

      // Execute tool operations concurrently
      const toolPromises = Array.from({ length: requests }, (_, i) => {
        const sessionId = sessionIds[i % sessionIds.length];
        return measureRequestTime('medium_load_tool', () =>
          request
            .post(`/api/sessions/${sessionId}/tools/read/execute`)
            .send({
              parameters: { path: '/test/small.txt' },
              context: { 
                permissions: ['read_files'],
                workingDirectory: '/test' 
              }
            })
        );
      });

      const toolResults = await Promise.all(toolPromises);
      
      clearInterval(resourceMonitor);
      const totalTime = performance.now() - startTime;

      // Analyze results
      const successful = toolResults.filter(r => r.status === 200).length;
      const throughput = successful / (totalTime / 1000);

      const sessionStats = metrics.getStats('medium_load_session')!;
      const toolStats = metrics.getStats('medium_load_tool')!;
      const memoryTrend = metrics.getMemoryTrend()!;

      expect(successful).toBeGreaterThan(requests * 0.95); // At least 95% success rate
      expect(throughput).toBeGreaterThan(20); // At least 20 RPS
      expect(toolStats.p90).toBeLessThan(1000); // 90th percentile under 1s

      console.log(`Medium load test results:`, {
        successful,
        total: requests,
        successRate: (successful / requests * 100).toFixed(2) + '%',
        throughput: throughput.toFixed(2),
        sessionStats,
        toolStats,
        memoryTrend
      });
    });

    it('should handle heavy load (100 concurrent, 1000 requests)', async () => {
      const { concurrent, requests } = LOAD_TEST_CONFIG.heavyLoad;
      const startTime = performance.now();

      // Monitor resource usage more frequently
      const resourceMonitor = setInterval(() => {
        metrics.recordResourceUsage();
      }, 500);

      // Test mix of operations for realistic heavy load
      const operationTypes = [
        { type: 'health', weight: 0.3 },
        { type: 'session', weight: 0.2 },
        { type: 'tool', weight: 0.4 },
        { type: 'list', weight: 0.1 }
      ];

      // Create some sessions upfront
      const initialSessions = await Promise.all(
        Array.from({ length: 20 }, (_, i) =>
          request
            .post('/api/sessions')
            .send({ userId: `heavy-load-user-${i}` })
        )
      );
      
      const sessionIds = initialSessions
        .filter(r => r.status === 201)
        .map(r => r.body.sessionId);

      // Generate mixed workload
      const operations = Array.from({ length: requests }, (_, i) => {
        const rand = Math.random();
        let cumulative = 0;
        
        for (const op of operationTypes) {
          cumulative += op.weight;
          if (rand < cumulative) {
            switch (op.type) {
              case 'health':
                return measureRequestTime('heavy_load_health', () => request.get('/health'));
              
              case 'session':
                return measureRequestTime('heavy_load_session', () =>
                  request
                    .post('/api/sessions')
                    .send({ userId: `heavy-session-${i}` })
                );
              
              case 'tool':
                const sessionId = sessionIds[i % sessionIds.length];
                return measureRequestTime('heavy_load_tool', () =>
                  request
                    .post(`/api/sessions/${sessionId}/tools/read/execute`)
                    .send({
                      parameters: { path: `/test/concurrent-${i % 100}.txt` },
                      context: { 
                        permissions: ['read_files'],
                        workingDirectory: '/test' 
                      }
                    })
                );
              
              case 'list':
                return measureRequestTime('heavy_load_list', () => request.get('/api/tools'));
              
              default:
                return measureRequestTime('heavy_load_health', () => request.get('/health'));
            }
          }
        }
        
        return measureRequestTime('heavy_load_health', () => request.get('/health'));
      });

      // Execute operations in batches to control concurrency
      const batchSize = concurrent;
      const batches = [];
      
      for (let i = 0; i < operations.length; i += batchSize) {
        const batch = operations.slice(i, i + batchSize);
        batches.push(Promise.all(batch));
      }

      const results = await Promise.all(batches);
      const allResults = results.flat();
      
      clearInterval(resourceMonitor);
      const totalTime = performance.now() - startTime;

      // Analyze results by operation type
      const resultsByType: { [key: string]: any[] } = {};
      allResults.forEach(result => {
        const type = result.operationType || 'unknown';
        if (!resultsByType[type]) resultsByType[type] = [];
        resultsByType[type].push(result);
      });

      const successful = allResults.filter(r => r.status >= 200 && r.status < 400).length;
      const throughput = successful / (totalTime / 1000);
      const memoryTrend = metrics.getMemoryTrend()!;

      expect(successful).toBeGreaterThan(requests * 0.9); // At least 90% success rate
      expect(throughput).toBeGreaterThan(10); // At least 10 RPS under heavy load

      console.log(`Heavy load test results:`, {
        successful,
        total: requests,
        successRate: (successful / requests * 100).toFixed(2) + '%',
        throughput: throughput.toFixed(2),
        operationBreakdown: Object.keys(resultsByType).map(type => ({
          type,
          count: resultsByType[type].length,
          successful: resultsByType[type].filter(r => r.status >= 200 && r.status < 400).length
        })),
        memoryTrend
      });
    });

    it('should handle spike load (200 concurrent, short burst)', async () => {
      const { concurrent, requests } = LOAD_TEST_CONFIG.spikeLoad;
      const startTime = performance.now();

      // Monitor resource usage during spike
      const resourceMonitor = setInterval(() => {
        metrics.recordResourceUsage();
      }, 100); // More frequent monitoring

      // Create sudden spike of concurrent requests
      const spikeRequests = Array.from({ length: requests }, (_, i) =>
        measureRequestTime('spike_load', () =>
          request
            .get('/health')
            .timeout(5000) // Allow more time during spike
        )
      );

      const results = await Promise.allSettled(spikeRequests);
      
      clearInterval(resourceMonitor);
      const totalTime = performance.now() - startTime;

      // Analyze spike handling
      const successful = results.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status === 200
      ).length;
      
      const failed = results.filter(r => 
        r.status === 'rejected' || (r.status === 'fulfilled' && (r.value as any).status >= 400)
      ).length;

      const stats = metrics.getStats('spike_load');
      const memoryTrend = metrics.getMemoryTrend()!;

      // During spike, some failures are acceptable
      expect(successful).toBeGreaterThan(requests * 0.8); // At least 80% success
      expect(stats?.p99).toBeLessThan(5000); // 99th percentile under 5s

      console.log(`Spike load test results:`, {
        successful,
        failed,
        total: requests,
        successRate: (successful / requests * 100).toFixed(2) + '%',
        avgResponseTime: stats?.avg,
        p99ResponseTime: stats?.p99,
        memoryTrend,
        duration: totalTime
      });
    });
  });

  describe('Endurance Testing', () => {
    it('should maintain performance over extended duration', async () => {
      const { concurrent, duration } = LOAD_TEST_CONFIG.enduranceTest;
      const startTime = performance.now();
      let requestCount = 0;

      // Monitor resources throughout test
      const resourceMonitor = setInterval(() => {
        metrics.recordResourceUsage();
      }, 2000);

      // Run continuous load for specified duration
      const endTime = startTime + duration;
      const workers: Promise<void>[] = [];

      // Create concurrent workers
      for (let i = 0; i < concurrent; i++) {
        const worker = async () => {
          const sessionResponse = await request
            .post('/api/sessions')
            .send({ userId: `endurance-user-${i}` });
          
          const sessionId = sessionResponse.body.sessionId;

          while (performance.now() < endTime) {
            try {
              const operation = requestCount % 4;
              let requestPromise;

              switch (operation) {
                case 0:
                  requestPromise = request.get('/health');
                  break;
                case 1:
                  requestPromise = request.get(`/api/sessions/${sessionId}`);
                  break;
                case 2:
                  requestPromise = request
                    .post(`/api/sessions/${sessionId}/tools/read/execute`)
                    .send({
                      parameters: { path: '/test/small.txt' },
                      context: { permissions: ['read_files'], workingDirectory: '/test' }
                    });
                  break;
                case 3:
                  requestPromise = request.get('/api/tools');
                  break;
                default:
                  requestPromise = request.get('/health');
              }

              const reqStart = performance.now();
              const response = await requestPromise;
              const responseTime = performance.now() - reqStart;
              
              metrics.recordMetric('endurance_response_time', responseTime);
              requestCount++;

              // Small delay between requests for each worker
              await new Promise(resolve => setTimeout(resolve, 100));
            } catch (error) {
              // Continue on individual request failures
              metrics.recordMetric('endurance_errors', 1);
            }
          }
        };

        workers.push(worker());
      }

      await Promise.all(workers);
      
      clearInterval(resourceMonitor);
      const actualDuration = performance.now() - startTime;

      // Analyze endurance performance
      const responseStats = metrics.getStats('endurance_response_time')!;
      const memoryTrend = metrics.getMemoryTrend()!;
      const throughput = requestCount / (actualDuration / 1000);

      expect(requestCount).toBeGreaterThan(100); // Minimum requests completed
      expect(throughput).toBeGreaterThan(5); // Minimum throughput
      expect(memoryTrend.growth).toBeLessThan(100 * 1024 * 1024); // Memory growth under 100MB

      console.log(`Endurance test results:`, {
        duration: actualDuration,
        requestCount,
        throughput: throughput.toFixed(2),
        responseStats,
        memoryTrend,
        memoryGrowthMB: (memoryTrend.growth / (1024 * 1024)).toFixed(2)
      });
    }, 40000); // Increase timeout for endurance test
  });

  describe('Resource Utilization Testing', () => {
    it('should efficiently handle memory usage under load', async () => {
      const initialMemory = process.memoryUsage();
      
      // Create many sessions to test memory efficiency
      const sessionCount = 100;
      const sessionPromises = Array.from({ length: sessionCount }, (_, i) =>
        request
          .post('/api/sessions')
          .send({ userId: `memory-test-user-${i}` })
      );

      const sessionResults = await Promise.all(sessionPromises);
      const sessionIds = sessionResults
        .filter(r => r.status === 201)
        .map(r => r.body.sessionId);

      expect(sessionIds.length).toBe(sessionCount);

      // Add messages to sessions
      const messagePromises = sessionIds.flatMap(sessionId =>
        Array.from({ length: 10 }, (_, i) =>
          request
            .post(`/api/sessions/${sessionId}/messages`)
            .send({
              content: `Memory test message ${i}`,
              type: 'user'
            })
        )
      );

      await Promise.all(messagePromises);

      const peakMemory = process.memoryUsage();
      const memoryGrowth = peakMemory.heapUsed - initialMemory.heapUsed;

      // Cleanup sessions
      const deletePromises = sessionIds.map(id =>
        request.delete(`/api/sessions/${id}`)
      );
      
      await Promise.all(deletePromises);

      // Allow garbage collection
      if (global.gc) {
        global.gc();
      }
      await new Promise(resolve => setTimeout(resolve, 1000));

      const finalMemory = process.memoryUsage();
      const memoryRecovered = peakMemory.heapUsed - finalMemory.heapUsed;

      console.log(`Memory usage test:`, {
        initialMB: (initialMemory.heapUsed / 1024 / 1024).toFixed(2),
        peakMB: (peakMemory.heapUsed / 1024 / 1024).toFixed(2),
        finalMB: (finalMemory.heapUsed / 1024 / 1024).toFixed(2),
        growthMB: (memoryGrowth / 1024 / 1024).toFixed(2),
        recoveredMB: (memoryRecovered / 1024 / 1024).toFixed(2),
        recoveryRate: ((memoryRecovered / memoryGrowth) * 100).toFixed(2) + '%'
      });

      // Memory should be reasonable
      expect(memoryGrowth).toBeLessThan(200 * 1024 * 1024); // Under 200MB growth
      expect(memoryRecovered).toBeGreaterThan(memoryGrowth * 0.5); // At least 50% recovered
    });

    it('should handle file operations efficiently', async () => {
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'file-perf-user' });
      const sessionId = sessionResponse.body.sessionId;

      // Test different file sizes
      const fileSizeTests = [
        { name: 'small', size: 'small.txt' },
        { name: 'medium', size: 'medium.txt' },
        { name: 'large', size: 'large.txt' }
      ];

      for (const test of fileSizeTests) {
        const iterations = 20;
        
        for (let i = 0; i < iterations; i++) {
          const start = performance.now();
          
          const response = await request
            .post(`/api/sessions/${sessionId}/tools/read/execute`)
            .send({
              parameters: { path: `/test/${test.size}` },
              context: { permissions: ['read_files'], workingDirectory: '/test' }
            });

          const responseTime = performance.now() - start;
          metrics.recordMetric(`file_${test.name}_read_time`, responseTime);
          
          expect(response.status).toBe(200);
          expect(response.body.result.success).toBe(true);
        }

        const stats = metrics.getStats(`file_${test.name}_read_time`)!;
        console.log(`File ${test.name} read performance:`, stats);
      }

      // Large files should be handled efficiently
      const largeFileStats = metrics.getStats('file_large_read_time')!;
      expect(largeFileStats.avg).toBeLessThan(2000); // Average under 2s for 100KB file
    });

    it('should handle concurrent file access efficiently', async () => {
      const sessionResponse = await request
        .post('/api/sessions')
        .send({ userId: 'concurrent-file-user' });
      const sessionId = sessionResponse.body.sessionId;

      // Access different files concurrently
      const concurrentReads = Array.from({ length: 50 }, (_, i) => {
        const start = performance.now();
        return request
          .post(`/api/sessions/${sessionId}/tools/read/execute`)
          .send({
            parameters: { path: `/test/concurrent-${i % 20}.txt` },
            context: { permissions: ['read_files'], workingDirectory: '/test' }
          })
          .then(response => ({
            responseTime: performance.now() - start,
            status: response.status,
            success: response.body.result?.success
          }));
      });

      const results = await Promise.all(concurrentReads);
      
      const successful = results.filter(r => r.status === 200 && r.success).length;
      const avgResponseTime = results.reduce((sum, r) => sum + r.responseTime, 0) / results.length;

      expect(successful).toBe(50); // All should succeed
      expect(avgResponseTime).toBeLessThan(1000); // Average under 1s

      console.log(`Concurrent file access results:`, {
        successful,
        total: results.length,
        avgResponseTime: avgResponseTime.toFixed(2),
        maxResponseTime: Math.max(...results.map(r => r.responseTime)).toFixed(2)
      });
    });
  });

  describe('Provider Performance Testing', () => {
    it('should handle provider requests efficiently', async () => {
      const requestCount = 100;
      const concurrency = 20;
      
      performanceProvider.setResponseTime(100); // 100ms response time

      // Test concurrent provider requests
      const batches = [];
      for (let i = 0; i < requestCount; i += concurrency) {
        const batch = Array.from({ length: Math.min(concurrency, requestCount - i) }, () =>
          measureRequestTime('provider_generate', () =>
            request
              .post('/api/providers/performance-provider/generate')
              .send({
                messages: [{ role: 'user', content: 'Performance test request' }],
                options: { maxTokens: 100 }
              })
          )
        );
        batches.push(Promise.all(batch));
      }

      const results = await Promise.all(batches);
      const allResults = results.flat();

      const successful = allResults.filter(r => r.status === 200).length;
      const stats = metrics.getStats('provider_generate')!;
      const providerStats = performanceProvider.getStats();

      expect(successful).toBe(requestCount);
      expect(stats.avg).toBeGreaterThan(100); // Should include network overhead
      expect(stats.avg).toBeLessThan(500); // But not too much overhead
      expect(providerStats.maxConcurrent).toBeGreaterThan(1);

      console.log(`Provider performance results:`, {
        successful,
        responseStats: stats,
        providerStats
      });
    });

    it('should handle provider failures gracefully', async () => {
      // Test with slower provider response
      performanceProvider.setResponseTime(1000); // 1s response time

      const slowRequests = Array.from({ length: 10 }, () =>
        measureRequestTime('slow_provider', () =>
          request
            .post('/api/providers/performance-provider/generate')
            .send({
              messages: [{ role: 'user', content: 'Slow request' }],
              options: { maxTokens: 50 }
            })
        )
      );

      const results = await Promise.all(slowRequests);
      const successful = results.filter(r => r.status === 200).length;
      const stats = metrics.getStats('slow_provider')!;

      expect(successful).toBe(10);
      expect(stats.avg).toBeGreaterThan(1000); // Should reflect slow response

      console.log(`Slow provider handling:`, {
        successful,
        avgResponseTime: stats.avg,
        maxResponseTime: stats.max
      });

      // Reset provider speed
      performanceProvider.setResponseTime(50);
    });
  });

  describe('WebSocket Performance Testing', () => {
    it('should handle multiple WebSocket connections efficiently', async () => {
      const connectionCount = 20;
      const messagesPerConnection = 10;
      const wsUrl = `ws://localhost:${serverPort}/ws`;

      const connectionResults = await Promise.allSettled(
        Array.from({ length: connectionCount }, async (_, i) => {
          const ws = new WebSocket(wsUrl);
          const connectionId = `perf-ws-${i}`;
          
          // Wait for connection
          await new Promise((resolve, reject) => {
            ws.on('open', resolve);
            ws.on('error', reject);
            setTimeout(() => reject(new Error('Connection timeout')), 5000);
          });

          // Send test messages
          const messagePromises = Array.from({ length: messagesPerConnection }, (_, j) => {
            return new Promise<number>((resolve) => {
              const start = performance.now();
              const message = {
                id: `${connectionId}-msg-${j}`,
                type: 'test_message',
                timestamp: Date.now(),
                data: { content: `Test message ${j}` }
              };

              ws.send(JSON.stringify(message));

              // Wait for response or timeout
              const timeout = setTimeout(() => resolve(5000), 5000);
              ws.once('message', () => {
                clearTimeout(timeout);
                resolve(performance.now() - start);
              });
            });
          });

          const messageTimes = await Promise.all(messagePromises);
          ws.close();

          return {
            connectionId,
            messageCount: messagesPerConnection,
            avgMessageTime: messageTimes.reduce((a, b) => a + b) / messageTimes.length,
            maxMessageTime: Math.max(...messageTimes)
          };
        })
      );

      const successful = connectionResults.filter(r => r.status === 'fulfilled').length;
      const results = connectionResults
        .filter(r => r.status === 'fulfilled')
        .map(r => (r as any).value);

      const avgMessageTime = results.length > 0 
        ? results.reduce((sum, r) => sum + r.avgMessageTime, 0) / results.length 
        : 0;

      expect(successful).toBeGreaterThan(connectionCount * 0.8); // At least 80% success
      expect(avgMessageTime).toBeLessThan(1000); // Average message time under 1s

      console.log(`WebSocket performance results:`, {
        successfulConnections: successful,
        totalConnections: connectionCount,
        avgMessageTime: avgMessageTime.toFixed(2),
        totalMessages: successful * messagesPerConnection
      });
    });
  });

  // Helper function to measure request time and store metrics
  async function measureRequestTime(
    metricName: string, 
    requestFn: () => supertest.Test
  ): Promise<any> {
    const start = performance.now();
    
    try {
      const response = await requestFn();
      const responseTime = performance.now() - start;
      
      metrics.recordMetric(metricName, responseTime);
      
      return {
        ...response,
        responseTime,
        operationType: metricName
      };
    } catch (error) {
      const responseTime = performance.now() - start;
      metrics.recordMetric(`${metricName}_error`, responseTime);
      
      throw {
        ...error,
        responseTime,
        operationType: `${metricName}_error`
      };
    }
  }
});