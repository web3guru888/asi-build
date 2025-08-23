#!/usr/bin/env bun

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { serve } from 'bun';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

// Simple ASI1 client
class ASI1Client {
  private apiKey: string;
  private baseUrl: string;
  
  constructor() {
    this.apiKey = process.env.ASI1_API_KEY || '';
    this.baseUrl = process.env.ASI1_API_URL || 'https://api.asi1.ai';
    
    if (!this.apiKey) {
      console.warn('⚠️  ASI1_API_KEY not set - using mock responses');
    }
  }
  
  async chat(message: string): Promise<string> {
    if (!this.apiKey) {
      // Mock response for testing
      return `Mock ASI1 Response: I received your message "${message}". Please set ASI1_API_KEY to enable real AI responses.`;
    }
    
    try {
      const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: process.env.ASI1_MODEL || 'asi1-mini',
          messages: [
            { role: 'system', content: 'You are ASI-Code, an intelligent coding assistant.' },
            { role: 'user', content: message }
          ],
          temperature: 0.7,
          max_tokens: 500
        })
      });
      
      if (!response.ok) {
        throw new Error(`ASI1 API error: ${response.status}`);
      }
      
      const data = await response.json();
      return data.choices[0].message.content;
    } catch (error) {
      console.error('ASI1 API error:', error);
      return `Error connecting to ASI1: ${error.message}. Using fallback response.`;
    }
  }
}

// Import ASI-Code components
async function startASICode() {
  console.log('🚀 Initializing Enhanced ASI-Code with ASI1 integration...\n');
  
  const app = new Hono();
  const asi1 = new ASI1Client();
  
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
        asi1: process.env.ASI1_API_KEY ? 'connected' : 'mock-mode',
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
      if (existsSync(uiPath)) {
        const html = readFileSync(uiPath, 'utf-8');
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
      asi1: process.env.ASI1_API_KEY ? 'connected' : 'mock-mode',
      endpoints: {
        health: '/health',
        api: '/api',
        websocket: '/ws'
      }
    });
  });
  
  // API endpoints
  app.get('/api', (c) => {
    return c.json({
      message: 'ASI-Code API',
      version: '1.0.0',
      asi1: process.env.ASI1_API_KEY ? 'connected' : 'mock-mode'
    });
  });
  
  // Tool registry endpoint
  app.get('/api/tools', async (c) => {
    return c.json({
      status: 'success',
      tools: [
        { name: 'chat', description: 'Chat with ASI1' },
        { name: 'code', description: 'Generate code' },
        { name: 'analyze', description: 'Analyze code' }
      ]
    });
  });
  
  // Providers endpoint
  app.get('/api/providers', async (c) => {
    return c.json({
      providers: [
        {
          name: 'asi1',
          status: process.env.ASI1_API_KEY ? 'connected' : 'mock-mode',
          models: ['asi1-mini', 'asi1-extended', 'asi1-thinking']
        }
      ]
    });
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

  const port = process.env.PORT || 3333;
  const host = process.env.HOST || '0.0.0.0';
  
  console.log('🌐 Starting Enhanced ASI-Code server...');
  console.log(`📡 Server: http://${host}:${port}`);
  console.log(`🏥 Health: http://${host}:${port}/health`);
  console.log(`🔧 API: http://${host}:${port}/api`);
  console.log(`🔌 WebSocket: ws://${host}:${port}/ws`);
  console.log(`🤖 ASI1: ${process.env.ASI1_API_KEY ? 'Connected' : 'Mock Mode'}`);
  console.log(`\n✅ ASI-Code is running with enhanced ASI1 integration!\n`);
  console.log('Press Ctrl+C to stop\n');

  // WebSocket connections storage
  const wsClients = new Set();
  const sessions = new Map();

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
        const sessionId = `session_${Date.now()}`;
        ws.data = { sessionId, messages: [] };
        sessions.set(sessionId, ws);
        
        console.log('✅ WebSocket client connected. Total clients:', wsClients.size);
        
        // Send welcome message
        ws.send(JSON.stringify({
          type: 'welcome',
          message: 'Connected to ASI-Code WebSocket with ASI1 integration',
          sessionId,
          timestamp: new Date().toISOString(),
          features: ['chat', 'commands', 'real-time updates', 'asi1-powered'],
          asi1Status: process.env.ASI1_API_KEY ? 'connected' : 'mock-mode'
        }));
      },
      
      async message(ws, message) {
        console.log('📨 Received:', message);
        
        try {
          const data = typeof message === 'string' ? JSON.parse(message) : message;
          
          // Handle different message types
          switch (data.type) {
            case 'ping':
              ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
              break;
              
            case 'command':
            case 'chat':
              // Process through ASI1
              ws.send(JSON.stringify({
                type: 'processing',
                message: 'Processing your request...',
                timestamp: new Date().toISOString()
              }));
              
              const userMessage = data.data || data.message || data.content;
              const aiResponse = await asi1.chat(userMessage);
              
              // Store in session history
              if (ws.data) {
                ws.data.messages.push(
                  { role: 'user', content: userMessage, timestamp: new Date().toISOString() },
                  { role: 'assistant', content: aiResponse, timestamp: new Date().toISOString() }
                );
              }
              
              ws.send(JSON.stringify({
                type: 'response',
                message: aiResponse,
                sessionId: ws.data?.sessionId,
                timestamp: new Date().toISOString()
              }));
              break;
              
            case 'history':
              // Return session history
              ws.send(JSON.stringify({
                type: 'history',
                messages: ws.data?.messages || [],
                sessionId: ws.data?.sessionId,
                timestamp: new Date().toISOString()
              }));
              break;
              
            default:
              // For unknown types, try to process as chat
              const response = await asi1.chat(JSON.stringify(data));
              ws.send(JSON.stringify({
                type: 'response',
                message: response,
                timestamp: new Date().toISOString()
              }));
          }
          
          // Broadcast to all clients (for collaborative features)
          if (data.broadcast) {
            for (const client of wsClients) {
              if (client !== ws && client.readyState === 1) {
                client.send(JSON.stringify({
                  type: 'broadcast',
                  from: ws.data?.sessionId || 'anonymous',
                  data: data,
                  timestamp: new Date().toISOString()
                }));
              }
            }
          }
        } catch (error) {
          console.error('❌ WebSocket message error:', error);
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Error processing message: ' + error.message,
            timestamp: new Date().toISOString()
          }));
        }
      },
      
      close(ws) {
        wsClients.delete(ws);
        if (ws.data?.sessionId) {
          sessions.delete(ws.data.sessionId);
        }
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