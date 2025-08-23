/**
 * Route Definitions and Handlers
 *
 * HTTP API endpoints for ASI-Code server including health checks,
 * session management, provider interactions, and SSE events.
 */

import type { Hono } from 'hono';
import { createReadStream, readFileSync, existsSync } from 'fs';
import { join } from 'path';
import type { DefaultASIServer } from './server.js';
import type { KennyMessage } from '../kenny/index.js';

export function setupRoutes(app: Hono, server: DefaultASIServer): void {
  // Serve the Web UI at root
  app.get('/', c => {
    const uiPath = join(process.cwd(), 'public', 'index.html');
    if (existsSync(uiPath)) {
      const html = readFileSync(uiPath, 'utf-8');
      return c.html(html);
    }
    // Fallback message if UI not found
    return c.json({
      message: 'ASI-Code Server Running',
      version: '0.2.0',
      api: '/api',
      health: '/health',
      ui: 'Web UI not found. Please ensure public/index.html exists.'
    });
  });

  // Health check endpoint
  app.get('/health', c => {
    return c.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      connections: server.sseManager.getConnectionCount(),
    });
  });

  // Models endpoint (alias for providers)
  app.get('/models', c => {
    const providers = server.getProviderManager().list();
    return c.json({ models: providers, providers });
  });

  // Session Management Routes
  setupSessionRoutes(app, server);

  // Provider Routes
  setupProviderRoutes(app, server);

  // Tool Routes
  setupToolRoutes(app, server);

  // SSE Event Stream
  setupSSERoutes(app, server);

  // Static file serving
  setupStaticRoutes(app);
}

function setupSessionRoutes(app: Hono, server: DefaultASIServer): void {
  const sessionManager = server.getSessionManager();

  // Create new session
  app.post('/api/sessions', async c => {
    try {
      const body = await c.req.json();
      const { userId, config } = body;

      const session = await sessionManager.createSession(userId, config);
      server.emit('session:created', { sessionId: session.data.id, userId });

      return c.json({
        sessionId: session.data.id,
        kennyContext: session.data.kennyContext,
      });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Get session by ID
  app.get('/api/sessions/:id', async c => {
    try {
      const sessionId = c.req.param('id');
      const session = await sessionManager.getSession(sessionId);

      if (!session) {
        return c.json({ error: 'Session not found' }, 404);
      }

      return c.json({
        session: {
          id: session.data.id,
          userId: session.data.userId,
          kennyContext: session.data.kennyContext,
          messageCount: session.data.messages.length,
          createdAt: session.data.createdAt,
          lastActivity: session.data.lastActivity,
        },
      });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Delete session
  app.delete('/api/sessions/:id', async c => {
    try {
      const sessionId = c.req.param('id');
      await sessionManager.deleteSession(sessionId);
      server.emit('session:deleted', { sessionId });
      return c.json({ success: true });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Add message to session
  app.post('/api/sessions/:id/messages', async c => {
    try {
      const sessionId = c.req.param('id');
      const body = await c.req.json();
      const { content, type = 'user', metadata } = body;

      const session = await sessionManager.getSession(sessionId);
      if (!session) {
        return c.json({ error: 'Session not found' }, 404);
      }

      const message: KennyMessage = {
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type,
        content,
        timestamp: new Date(),
        context: session.data.kennyContext,
        metadata,
      };

      session.addMessage(message);
      await sessionManager.saveSession(sessionId);

      // Broadcast to SSE connections
      server.sseManager.broadcast('message', { sessionId, message });
      server.emit('message:added', { sessionId, message });

      return c.json({ message });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Get session messages
  app.get('/api/sessions/:id/messages', async c => {
    try {
      const sessionId = c.req.param('id');
      const limit = c.req.query('limit')
        ? parseInt(c.req.query('limit')!)
        : undefined;

      const session = await sessionManager.getSession(sessionId);
      if (!session) {
        return c.json({ error: 'Session not found' }, 404);
      }

      const messages = session.getMessages(limit);
      return c.json({ messages });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // List sessions for a user
  app.get('/api/sessions', async c => {
    try {
      const userId = c.req.query('userId');
      const sessions = await sessionManager.listSessions(userId);
      return c.json({ sessions });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });
}

function setupProviderRoutes(app: Hono, server: DefaultASIServer): void {
  const providerManager = server.getProviderManager();

  // List available providers
  app.get('/api/providers', c => {
    const providers = providerManager.list();
    return c.json({ providers });
  });

  // Generate using a specific provider
  app.post('/api/providers/:name/generate', async c => {
    try {
      const providerName = c.req.param('name');
      const body = await c.req.json();
      const { messages, options } = body;

      const provider = providerManager.get(providerName);
      if (!provider) {
        return c.json({ error: 'Provider not found' }, 404);
      }

      const response = await provider.generate(messages, options);
      server.emit('generation:completed', { provider: providerName, response });

      return c.json({ response });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Get provider capabilities
  app.get('/api/providers/:name', c => {
    try {
      const providerName = c.req.param('name');
      const provider = providerManager.get(providerName);

      if (!provider) {
        return c.json({ error: 'Provider not found' }, 404);
      }

      return c.json({
        name: providerName,
        capabilities: (provider as any).getCapabilities?.() || {},
        config: (provider as any).config || {},
      });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });
}

function setupToolRoutes(app: Hono, server: DefaultASIServer): void {
  const toolManager = server.getToolManager();

  // List available tools
  app.get('/api/tools', c => {
    const tools = toolManager.list();
    return c.json({ tools });
  });

  // Execute a tool
  app.post('/api/tools/:name/execute', async c => {
    try {
      const toolName = c.req.param('name');
      const body = await c.req.json();
      const { parameters, context } = body;

      const result = await toolManager.execute(toolName, parameters, context);
      server.emit('tool:executed', { tool: toolName, result });

      return c.json({ result });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Get tool schema
  app.get('/api/tools/:name', c => {
    try {
      const toolName = c.req.param('name');
      const tool = toolManager.get(toolName);

      if (!tool) {
        return c.json({ error: 'Tool not found' }, 404);
      }

      return c.json({
        name: toolName,
        schema: (tool as any).getSchema?.() || {},
        description:
          (tool as any).getDescription?.() || 'No description available',
      });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });
}

function setupSSERoutes(app: Hono, server: DefaultASIServer): void {
  // Server-Sent Events endpoint
  app.get('/api/events', async c => {
    const connectionId = `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    return new Response(
      new ReadableStream({
        start: controller => {
          // Setup SSE headers
          const encoder = new TextEncoder();
          const writer = controller;

          // Add connection to manager
          server.sseManager.addConnection(connectionId, writer as any);

          // Send initial connection event
          const initMessage = `event: connected\ndata: ${JSON.stringify({ connectionId })}\n\n`;
          controller.enqueue(encoder.encode(initMessage));

          // Setup cleanup on close
          c.req.raw.signal.addEventListener('abort', () => {
            server.sseManager.removeConnection(connectionId);
            controller.close();
          });
        },
      }),
      {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Headers': 'Cache-Control',
        },
      }
    );
  });

  // Endpoint to send custom events
  app.post('/api/events/broadcast', async c => {
    try {
      const body = await c.req.json();
      const { event, data, connectionId } = body;

      if (connectionId) {
        server.sseManager.sendToConnection(connectionId, event, data);
      } else {
        server.sseManager.broadcast(event, data);
      }

      return c.json({ success: true });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });
}

function setupStaticRoutes(app: Hono): void {
  // Static file serving
  app.get('/static/*', async c => {
    const filePath = c.req.param('*');
    if (!filePath) {
      return c.notFound();
    }
    try {
      const stream = createReadStream(filePath);
      return new Response(stream as any);
    } catch {
      return c.notFound();
    }
  });
}
