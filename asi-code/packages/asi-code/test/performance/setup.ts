/**
 * Performance test setup
 */

import { beforeAll, afterAll } from 'vitest';

// Global performance test configuration
const PERFORMANCE_CONFIG = {
  warmupIterations: 3,
  measurementIterations: 10,
  gcBetweenTests: true,
  memoryThreshold: 100 * 1024 * 1024, // 100MB
  timeoutThreshold: 30000 // 30 seconds
};

beforeAll(() => {
  // Configure performance testing environment
  process.env.NODE_ENV = 'performance';
  process.env.PERFORMANCE_MODE = 'true';
  
  // Disable logging for performance tests
  console.log = () => {};
  console.warn = () => {};
  console.info = () => {};
  
  // Enable garbage collection if available
  if (global.gc) {
    global.gc();
  }
  
  console.error(`[Performance Setup] Initialized with config:`, PERFORMANCE_CONFIG);
});

afterAll(() => {
  // Final garbage collection
  if (global.gc) {
    global.gc();
  }
  
  // Report final memory usage
  const memoryUsage = process.memoryUsage();
  console.error(`[Performance Teardown] Final memory usage:`, {
    heapUsed: `${Math.round(memoryUsage.heapUsed / 1024 / 1024)}MB`,
    heapTotal: `${Math.round(memoryUsage.heapTotal / 1024 / 1024)}MB`,
    external: `${Math.round(memoryUsage.external / 1024 / 1024)}MB`,
    rss: `${Math.round(memoryUsage.rss / 1024 / 1024)}MB`
  });
});

export { PERFORMANCE_CONFIG };