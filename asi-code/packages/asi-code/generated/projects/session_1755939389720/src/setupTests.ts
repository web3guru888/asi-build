import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './mocks/server';

// Extend Vitest's expect method with matchers from the @testing-library/jest-dom library
import * as matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect method with custom matchers
// eslint-disable-next-line @typescript-eslint/no-explicit-any
expect.extend(matchers);

// Establish API mocking before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'warn' });
});

// Reset any request handlers that we may add during the tests
afterEach(() => {
  server.resetHandlers();
  // Clean up the DOM after each test
  cleanup();
});

// Clean up after the tests are finished
afterAll(() => {
  server.close();
});

// Suppress warnings during tests (optional, useful for noisy libraries)
const originalConsoleError = console.error;
console.error = (...args) => {
  if (/Warning: /.test(args[0])) {
    return;
  }
  originalConsoleError(...args);
};

// Re-enable console.error in case something tries to restore it
afterAll(() => {
  console.error = originalConsoleError;
});