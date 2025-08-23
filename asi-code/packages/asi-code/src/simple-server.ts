#!/usr/bin/env bun

/**
 * Simple ASI-Code Server
 *
 * A minimal server implementation to test basic functionality
 */

// Basic imports for testing
import { createLogger } from './logging/logger.js';
import { DEFAULT_ASI_CONFIG } from './config/default-config.js';

console.log('🚀 Starting Simple ASI-Code Server...');
console.log('✅ Basic imports successful');

try {
  // Create a simple logger
  const logger = createLogger({
    level: 'info',
    format: 'pretty',
    enabled: true,
    outputs: [
      {
        type: 'console',
        enabled: true,
        options: {},
      },
    ],
    includeTimestamp: true,
    colorize: true,
  });

  logger.info('Logger created successfully');
  logger.info('Default config loaded', { configId: DEFAULT_ASI_CONFIG.id });

  // Simple HTTP server
  const server = Bun.serve({
    port: 3005,
    hostname: '0.0.0.0',
    fetch(req) {
      const url = new URL(req.url);

      if (url.pathname === '/') {
        return new Response(
          JSON.stringify({
            status: 'running',
            message: 'ASI-Code Simple Server',
            version: '1.0.0',
            timestamp: new Date().toISOString(),
          }),
          {
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }

      if (url.pathname === '/health') {
        return new Response(
          JSON.stringify({
            status: 'healthy',
            uptime: process.uptime(),
            timestamp: new Date().toISOString(),
          }),
          {
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }

      return new Response('Not Found', { status: 404 });
    },
  });

  logger.info(`🎯 Server running on http://localhost:${server.port}`);
  logger.info('✅ ASI-Code Simple Server started successfully');
} catch (error) {
  console.error('❌ Failed to start server:', error);
  process.exit(1);
}
