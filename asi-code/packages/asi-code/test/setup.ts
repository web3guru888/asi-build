/**
 * Global test setup for Vitest
 */

import { vi, beforeEach, afterEach } from 'vitest';
import { createMockConfig } from './test-utils.js';

// Mock environment variables
process.env.NODE_ENV = 'test';
process.env.ASI1_API_KEY = 'test-key';
process.env.OPENAI_API_KEY = 'test-openai-key';

// Global test configuration
const globalConfig = createMockConfig();

// Setup global mocks
vi.mock('fs-extra', () => ({
  default: {
    ensureDir: vi.fn(),
    readFile: vi.fn(),
    writeFile: vi.fn(),
    remove: vi.fn(),
    pathExists: vi.fn(() => Promise.resolve(true)),
    copy: vi.fn(),
    move: vi.fn()
  },
  ensureDir: vi.fn(),
  readFile: vi.fn(),
  writeFile: vi.fn(),
  remove: vi.fn(),
  pathExists: vi.fn(() => Promise.resolve(true)),
  copy: vi.fn(),
  move: vi.fn()
}));

// Mock external API calls
vi.mock('node:fetch', () => ({
  fetch: vi.fn()
}));

// Global setup before each test
beforeEach(() => {
  // Clear all mocks
  vi.clearAllMocks();
  
  // Reset modules
  vi.resetModules();
  
  // Reset timers
  vi.useFakeTimers();
});

// Global cleanup after each test
afterEach(() => {
  // Restore real timers
  vi.useRealTimers();
  
  // Clear all timers
  vi.clearAllTimers();
  
  // Clean up any remaining promises
  return new Promise(resolve => setImmediate(resolve));
});

// Extend expect with custom matchers
expect.extend({
  toBeValidEventEmission(received, eventName, expectedData) {
    const pass = received && 
                 received.eventName === eventName && 
                 (expectedData ? JSON.stringify(received.data) === JSON.stringify(expectedData) : true);
    
    if (pass) {
      return {
        message: () => `expected event not to be ${eventName}`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected event to be ${eventName} with data ${JSON.stringify(expectedData)}`,
        pass: false,
      };
    }
  },
  
  toBeWithinRange(received, floor, ceiling) {
    const pass = received >= floor && received <= ceiling;
    if (pass) {
      return {
        message: () => `expected ${received} not to be within range ${floor} - ${ceiling}`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be within range ${floor} - ${ceiling}`,
        pass: false,
      };
    }
  }
});

// Global error handler for unhandled rejections in tests
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Increase default timeout for async operations
vi.setConfig({
  testTimeout: 10000,
  hookTimeout: 10000,
});

export { globalConfig };