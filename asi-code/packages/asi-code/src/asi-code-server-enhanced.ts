#!/usr/bin/env bun

/**
 * Enhanced ASI-Code Server - Integration with New Tool System
 *
 * Demonstrates how to integrate the new Tool Registry system with the existing server architecture.
 * Provides enhanced tool capabilities while maintaining backward compatibility.
 */

import { createASIServer, defaultServerConfig } from './server/server.js';
import { setupEnhancedToolRoutes } from './server/enhanced-tool-routes.js';
import { createCompatibleToolManager } from './tool/tool-manager-bridge.js';
import { initializeToolSystem } from './tool/tool-initializer.js';
import { createSessionManager, createSessionStorage } from './session/index.js';
import { createProviderManager } from './provider/index.js';
import type { Hono } from 'hono';

async function main() {
  console.log(
    '🚀 Starting Enhanced ASI-Code Server with Tool Registry System...'
  );

  try {
    // Initialize the tool system first
    console.log('📦 Initializing Tool System...');
    const toolInitResult = await initializeToolSystem({
      enableMetrics: true,
      enableCaching: true,
      maxConcurrentExecutions: 10,
      defaultTimeout: 300000, // 5 minutes
      autoRegisterBuiltIns: true,
      enableToolValidation: true,
      enableVersioning: true,
    });

    console.log(`✅ Tool System initialized successfully:`);
    console.log(`   - Tools registered: ${toolInitResult.toolsRegistered}`);
    console.log(
      `   - Categories: ${Object.keys(toolInitResult.categoryCounts).join(', ')}`
    );
    console.log(
      `   - Initialization time: ${toolInitResult.initializationTime}ms`
    );

    if (toolInitResult.errors.length > 0) {
      console.warn(`⚠️  Tool registration errors:`);
      toolInitResult.errors.forEach(error => {
        console.warn(`   - ${error.toolName}: ${error.error}`);
      });
    }

    // Create managers using the new system
    console.log('🔧 Creating system managers...');

    // Create enhanced tool manager (backward compatible)
    const toolManager = await createCompatibleToolManager({
      enableMetrics: true,
      enableCaching: true,
      maxConcurrentExecutions: 10,
      defaultTimeout: 300000,
      autoRegisterBuiltIns: true,
      enableToolValidation: true,
      enableVersioning: true,
    });

    // Create other managers (existing system)
    const sessionStorage = createSessionStorage('memory');
    const sessionManager = createSessionManager(sessionStorage);

    const providerManager = createProviderManager();

    // Create server with enhanced configuration
    console.log('🌐 Setting up server...');
    const serverConfig = {
      ...defaultServerConfig,
      port: process.env.PORT ? parseInt(process.env.PORT) : 3001,
      host: process.env.HOST || 'localhost',
      cors: {
        origin: ['http://localhost:3000', 'http://localhost:3001'],
        credentials: true,
        methods: ['GET', 'POST', 'PUT', 'DELETE'],
        allowedHeaders: ['Content-Type', 'Authorization'],
      },
    };

    const server = createASIServer(
      serverConfig,
      sessionManager,
      providerManager,
      toolManager
    );

    // Add enhanced tool routes
    setupEnhancedToolRoutes(server.app, server as any);

    // Add health check endpoint with tool system info
    server.app.get('/health/detailed', async c => {
      try {
        const systemInfo = toolManager.getSystemInfo?.() || {};
        const toolHealth = (await toolManager.healthCheck?.()) || {
          status: 'unknown',
        };

        return c.json({
          server: {
            status: 'ok',
            timestamp: new Date().toISOString(),
            uptime: process.uptime(),
            memory: process.memoryUsage(),
            pid: process.pid,
          },
          tools: {
            health: toolHealth,
            system: systemInfo,
            registry: toolInitResult,
          },
          sessions: {
            total: (await sessionManager.listSessions()).length,
          },
          providers: {
            total: providerManager.list().length,
          },
        });
      } catch (error) {
        return c.json(
          {
            error: (error as Error).message,
            timestamp: new Date().toISOString(),
          },
          500
        );
      }
    });

    // Setup graceful shutdown
    const gracefulShutdown = async () => {
      console.log('🔄 Graceful shutdown initiated...');

      try {
        // Stop server
        await server.stop();
        console.log('✅ Server stopped');

        // Cleanup tool system
        await toolManager.cleanup();
        console.log('✅ Tool system cleaned up');

        // Cleanup other managers
        await sessionManager.cleanup?.();
        await providerManager.cleanup?.();
        console.log('✅ System managers cleaned up');

        console.log('👋 Server shutdown complete');
        process.exit(0);
      } catch (error) {
        console.error('❌ Error during shutdown:', error);
        process.exit(1);
      }
    };

    // Handle shutdown signals
    process.on('SIGINT', gracefulShutdown);
    process.on('SIGTERM', gracefulShutdown);

    // Start server
    await server.start();

    console.log('🎉 Enhanced ASI-Code Server started successfully!');
    console.log(
      `📍 Server running on http://${serverConfig.host}:${serverConfig.port}`
    );
    console.log('🔧 Available endpoints:');
    console.log('   - GET  /health - Basic health check');
    console.log('   - GET  /health/detailed - Detailed system status');
    console.log('   - GET  /api/tools - List all tools');
    console.log('   - GET  /api/tools/discover - Tool discovery info');
    console.log('   - GET  /api/tools/documentation - Tool documentation');
    console.log('   - POST /api/tools/:name/execute - Execute a tool');
    console.log('   - POST /api/tools/execute-batch - Batch tool execution');
    console.log('   - POST /api/tools/:name/validate - Validate parameters');
    console.log('   - GET  /api/tools/health - Tool system health');
    console.log('   - GET  /api/tools/executions - Running executions');
    console.log('   - GET  /api/events - SSE event stream');

    // Log initial tool system status
    setTimeout(async () => {
      try {
        const systemInfo = toolManager.getSystemInfo?.() || {};
        const health = (await toolManager.healthCheck?.()) || {
          status: 'unknown',
        };

        console.log('📊 Tool System Status:');
        console.log(`   - Total tools: ${systemInfo.totalTools || 'unknown'}`);
        console.log(
          `   - Built-in tools: ${systemInfo.builtInTools?.length || 'unknown'}`
        );
        console.log(`   - Health: ${health.status}`);
        console.log(
          `   - Running executions: ${health.details?.runningExecutions || 0}`
        );

        if (systemInfo.categoryCounts) {
          console.log('   - Categories:');
          Object.entries(systemInfo.categoryCounts).forEach(
            ([category, count]) => {
              console.log(`     * ${category}: ${count} tools`);
            }
          );
        }
      } catch (error) {
        console.warn(
          '⚠️  Could not retrieve tool system status:',
          (error as Error).message
        );
      }
    }, 1000);
  } catch (error) {
    console.error('❌ Failed to start server:', error);

    if (error instanceof Error) {
      console.error('Error details:', error.message);
      if (error.stack) {
        console.error('Stack trace:', error.stack);
      }
    }

    process.exit(1);
  }
}

// Handle unhandled errors
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

process.on('uncaughtException', error => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

// Start the server
main().catch(error => {
  console.error('Fatal error in main:', error);
  process.exit(1);
});
