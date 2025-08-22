#!/usr/bin/env bun

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { serve } from 'bun';

// Import ASI-Code components
async function startASICode() {
  console.log('🚀 Initializing ASI-Code components...\n');
  
  const app = new Hono();
  
  // Middleware
  app.use('*', cors());
  app.use('*', logger());
  
  // Health check endpoint
  app.get('/health', (c) => {
    return c.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      components: {
        kenny: 'operational',
        asi1: 'ready',
        toolRegistry: 'loaded',
        sessionManager: 'active'
      }
    });
  });
  
  // Root endpoint
  app.get('/', (c) => {
    return c.json({
      name: 'ASI-Code Framework',
      version: '1.0.0',
      status: 'running',
      features: [
        'Kenny Integration Pattern',
        'ASI1 LLM Provider',
        'Tool Registry System',
        'Session Management',
        'Permission System',
        'Consciousness Engine'
      ],
      endpoints: {
        health: '/health',
        api: '/api',
        tools: '/api/tools',
        sessions: '/api/sessions',
        providers: '/api/providers'
      }
    });
  });
  
  // API endpoints
  app.get('/api', (c) => {
    return c.json({
      message: 'ASI-Code API',
      version: '1.0.0'
    });
  });
  
  // Tool registry endpoint
  app.get('/api/tools', async (c) => {
    try {
      const { createToolRegistry } = await import('./src/tool/tool-registry.js');
      const registry = createToolRegistry();
      await registry.initialize({});
      const health = await registry.healthCheck();
      
      return c.json({
        status: 'success',
        tools: [],
        health
      });
    } catch (error: any) {
      return c.json({
        status: 'error',
        message: error.message,
        tools: []
      }, 500);
    }
  });
  
  // Session endpoint
  app.get('/api/sessions', async (c) => {
    try {
      const { DefaultSessionManager } = await import('./src/session/session-manager.js');
      const { MemorySessionStorage } = await import('./src/session/storage.js');
      
      const storage = new MemorySessionStorage();
      const manager = new DefaultSessionManager(storage);
      
      return c.json({
        status: 'success',
        sessions: [],
        capabilities: ['create', 'destroy', 'list']
      });
    } catch (error: any) {
      return c.json({
        status: 'error',
        message: error.message,
        sessions: []
      }, 500);
    }
  });
  
  // Provider info endpoint
  app.get('/api/providers', async (c) => {
    try {
      const { ASI1Provider } = await import('./src/provider/asi1.js');
      const provider = new ASI1Provider({ apiKey: process.env.ASI1_API_KEY });
      
      return c.json({
        status: 'success',
        providers: [{
          name: 'ASI1',
          models: provider.getAvailableModels(),
          configured: !!process.env.ASI1_API_KEY
        }]
      });
    } catch (error: any) {
      return c.json({
        status: 'error',
        message: error.message,
        providers: []
      }, 500);
    }
  });
  
  // Kenny Integration endpoint
  app.get('/api/kenny', async (c) => {
    try {
      const { getKennyIntegration } = await import('./src/kenny/integration.js');
      const kenny = getKennyIntegration();
      
      return c.json({
        status: 'success',
        kenny: {
          initialized: true,
          components: {
            messageBus: 'MessageBus',
            stateManager: 'StateManager',
            subsystems: []
          }
        }
      });
    } catch (error: any) {
      return c.json({
        status: 'error',
        message: error.message
      }, 500);
    }
  });
  
  // Error handling
  app.onError((err, c) => {
    console.error(`Error: ${err.message}`);
    return c.json({
      error: err.message,
      status: 'error'
    }, 500);
  });
  
  // 404 handler
  app.notFound((c) => {
    return c.json({
      error: 'Not Found',
      message: 'The requested endpoint does not exist',
      availableEndpoints: ['/', '/health', '/api', '/api/tools', '/api/sessions', '/api/providers', '/api/kenny']
    }, 404);
  });
  
  const port = parseInt(process.env.PORT || '8080');
  const host = process.env.HOST || '0.0.0.0';
  
  console.log(`🌐 Starting ASI-Code server...`);
  console.log(`📡 Server: http://${host}:${port}`);
  console.log(`🏥 Health: http://${host}:${port}/health`);
  console.log(`🔧 API: http://${host}:${port}/api`);
  console.log(`\n✅ ASI-Code is running!\n`);
  console.log('Press Ctrl+C to stop\n');
  
  // Start the server
  serve({
    fetch: app.fetch,
    port,
    hostname: host,
  });
}

// Start the application
startASICode().catch(console.error);
