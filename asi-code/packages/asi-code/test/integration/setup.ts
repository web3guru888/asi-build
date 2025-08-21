/**
 * Integration test setup
 */

import { beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { createServer } from '../../src/server/server.js';
import type { Server } from 'node:http';

let testServer: Server;
let testPort = 3001;

beforeAll(async () => {
  // Find available port
  testPort = await findAvailablePort(3001);
  
  // Create test server
  testServer = createServer({
    port: testPort,
    host: 'localhost',
    enableLogging: false,
    enableCors: true
  });
  
  // Start server
  await new Promise<void>((resolve) => {
    testServer.listen(testPort, () => {
      console.log(`Test server running on port ${testPort}`);
      resolve();
    });
  });
});

afterAll(async () => {
  if (testServer) {
    await new Promise<void>((resolve) => {
      testServer.close(() => resolve());
    });
  }
});

beforeEach(async () => {
  // Reset any shared state between integration tests
  // This could include clearing databases, resetting caches, etc.
});

afterEach(async () => {
  // Cleanup after each integration test
});

async function findAvailablePort(startPort: number): Promise<number> {
  const net = await import('node:net');
  
  return new Promise((resolve) => {
    const server = net.createServer();
    server.listen(startPort, () => {
      const port = (server.address() as any)?.port || startPort;
      server.close(() => resolve(port));
    });
    
    server.on('error', () => {
      resolve(findAvailablePort(startPort + 1));
    });
  });
}

export { testServer, testPort };