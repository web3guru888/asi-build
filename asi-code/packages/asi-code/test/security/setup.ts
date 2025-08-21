/**
 * Security test setup
 */

import { beforeAll, afterAll, beforeEach } from 'vitest';

// Security test configuration
const SECURITY_CONFIG = {
  enableAuditing: true,
  strictValidation: true,
  logSecurityEvents: true,
  simulateAttacks: true
};

beforeAll(() => {
  // Configure security testing environment
  process.env.NODE_ENV = 'security-test';
  process.env.SECURITY_MODE = 'strict';
  process.env.ENABLE_SECURITY_LOGGING = 'true';
  
  console.log('[Security Setup] Initialized security testing environment');
});

beforeEach(() => {
  // Reset security state between tests
  if (global.gc) {
    global.gc();
  }
});

afterAll(() => {
  console.log('[Security Teardown] Security tests completed');
});

// Security test utilities
export const SecurityTestUtils = {
  // Generate malicious payloads for testing
  generateXSSPayload: () => '<script>alert("xss")</script>',
  
  generateSQLInjectionPayload: () => "'; DROP TABLE users; --",
  
  generatePathTraversalPayload: () => '../../../etc/passwd',
  
  generateCommandInjectionPayload: () => '; rm -rf /',
  
  generateLargePayload: (size: number = 1024 * 1024) => 'A'.repeat(size),
  
  generateUnicodePayload: () => '\u0000\u0001\u0002\uFFFF',
  
  // Validation helpers
  isSecureError: (error: string) => {
    const securePatterns = [
      /access denied/i,
      /permission denied/i,
      /not allowed/i,
      /blocked/i,
      /forbidden/i
    ];
    return securePatterns.some(pattern => pattern.test(error));
  },
  
  hasInformationLeakage: (message: string) => {
    const leakagePatterns = [
      /\/etc\/passwd/,
      /\/root\//,
      /node_modules/,
      /src\//,
      /internal error/i,
      /stack trace/i,
      /database/i
    ];
    return leakagePatterns.some(pattern => pattern.test(message));
  }
};

export { SECURITY_CONFIG };