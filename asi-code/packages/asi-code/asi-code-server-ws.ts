#!/usr/bin/env bun

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { serve } from 'bun';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

// Import ASI-Code components
async function startASICode() {
  console.log('🚀 Initializing ASI-Code with WebSocket support...\n');
  
  const app = new Hono();
  
  // Middleware - Allow CORS from anywhere for development
  app.use('*', cors({
    origin: '*',
    credentials: true,
    allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowHeaders: ['Content-Type', 'Authorization', 'Accept']
  }));
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
        sessionManager: 'active',
        websocket: 'enabled'
      }
    });
  });
  
  // Root endpoint - Serve Web UI
  app.get('/', (c) => {
    try {
      const uiPath = join(process.cwd(), 'public', 'index.html');
      console.log('Looking for UI at:', uiPath);
      console.log('File exists:', existsSync(uiPath));
      
      if (existsSync(uiPath)) {
        const html = readFileSync(uiPath, 'utf-8');
        console.log('Serving HTML UI');
        return c.html(html);
      }
    } catch (error) {
      console.error('Error loading UI:', error);
    }
    
    // Fallback to JSON if UI not found
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
        'Consciousness Engine',
        'Chat Completions API',
        'WebSocket Support'
      ],
      endpoints: {
        health: '/health',
        api: '/api',
        chat: '/api/chat',
        tools: '/api/tools',
        sessions: '/api/sessions',
        providers: '/api/providers',
        websocket: '/ws'
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
      });
    }
  });
  
  // Providers endpoint
  app.get('/api/providers', async (c) => {
    try {
      return c.json({
        providers: [
          {
            name: 'asi1',
            status: 'ready',
            models: ['asi1-mini', 'asi1-extended', 'asi1-thinking']
          }
        ]
      });
    } catch (error: any) {
      return c.json({
        status: 'error',
        message: error.message,
        providers: []
      });
    }
  });
  
  // Sessions endpoints
  app.get('/api/sessions', (c) => {
    return c.json({ sessions: [] });
  });
  
  app.post('/api/sessions', async (c) => {
    const body = await c.req.json();
    return c.json({
      sessionId: `session_${Date.now()}`,
      ...body
    });
  });

  const port = process.env.PORT || 3000;
  const host = process.env.HOST || '0.0.0.0';
  
  console.log('🌐 Starting ASI-Code server with WebSocket...');
  console.log(`📡 Server: http://${host}:${port}`);
  console.log(`🏥 Health: http://${host}:${port}/health`);
  console.log(`🔧 API: http://${host}:${port}/api`);
  console.log(`🔌 WebSocket: ws://${host}:${port}/ws`);
  console.log(`\n✅ ASI-Code is running with WebSocket support!\n`);
  console.log('Press Ctrl+C to stop\n');

  // WebSocket connections storage
  const wsClients = new Set();

  // Start the server with WebSocket support
  serve({
    port,
    hostname: host,
    
    fetch(req, server) {
      const url = new URL(req.url);
      
      // Handle WebSocket upgrade
      if (url.pathname === '/ws') {
        const success = server.upgrade(req);
        if (success) {
          return undefined;
        }
        return new Response('WebSocket upgrade failed', { status: 400 });
      }
      
      // Handle regular HTTP requests
      return app.fetch(req);
    },
    
    websocket: {
      open(ws) {
        wsClients.add(ws);
        console.log('✅ WebSocket client connected. Total clients:', wsClients.size);
        
        // Send welcome message
        ws.send(JSON.stringify({
          type: 'welcome',
          message: 'Connected to ASI-Code WebSocket',
          timestamp: new Date().toISOString(),
          features: ['chat', 'commands', 'real-time updates']
        }));
      },
      
      message(ws, message) {
        console.log('📨 Received:', message);
        
        try {
          const data = typeof message === 'string' ? JSON.parse(message) : message;
          
          // Handle different message types
          switch (data.type) {
            case 'ping':
              ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
              break;
              
            case 'command':
              ws.send(JSON.stringify({
                type: 'response',
                command: data.data,
                result: `Executed: ${data.data}`,
                timestamp: new Date().toISOString()
              }));
              break;
              
            case 'chat':
              ws.send(JSON.stringify({
                type: 'chat',
                message: `Echo: ${data.message}`,
                timestamp: new Date().toISOString()
              }));
              break;
              
            default:
              ws.send(JSON.stringify({
                type: 'message',
                echo: data,
                timestamp: new Date().toISOString()
              }));
          }
          
          // Broadcast to all clients
          for (const client of wsClients) {
            if (client !== ws && client.readyState === 1) {
              client.send(JSON.stringify({
                type: 'broadcast',
                from: 'other-client',
                data: data,
                timestamp: new Date().toISOString()
              }));
            }
          }
        } catch (error) {
          console.error('❌ WebSocket message error:', error);
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Invalid message format',
            timestamp: new Date().toISOString()
          }));
        }
      },
      
      close(ws) {
        wsClients.delete(ws);
        console.log('👋 WebSocket client disconnected. Total clients:', wsClients.size);
      },
      
      error(ws, error) {
        console.error('❌ WebSocket error:', error);
      }
    }
  });
}

// Start the server
startASICode().catch(console.error);