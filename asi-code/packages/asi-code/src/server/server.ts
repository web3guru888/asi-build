/**
 * Main Hono Server Implementation
 *
 * Core server class with HTTP/SSE capabilities for ASI-Code system.
 * Provides real-time communication and REST API endpoints.
 */

import { Hono } from 'hono';
import { serve } from '@hono/node-server';
import { EventEmitter } from 'eventemitter3';
import { setupMiddleware } from './middleware.js';
import { setupRoutes } from './routes.js';
import type { SessionManager } from '../session/index.js';
import type { ProviderManager } from '../provider/index.js';
import type { ToolManager } from '../tool/index.js';
import type { ServerConfig } from '../config/config-types.js';

// ServerConfig imported from config-types.js

export interface ASIServer extends EventEmitter {
  config: ServerConfig;
  app: Hono;
  start(): Promise<void>;
  stop(): Promise<void>;
  isRunning(): boolean;
  sseManager: SSEConnectionManager;
  getSessionManager(): SessionManager;
  getProviderManager(): ProviderManager;
  getToolManager(): ToolManager;
}

// SSE Connection Manager
export class SSEConnectionManager {
  private readonly connections = new Map<string, WritableStreamDefaultWriter>();

  addConnection(id: string, writer: WritableStreamDefaultWriter): void {
    this.connections.set(id, writer);
  }

  removeConnection(id: string): void {
    const writer = this.connections.get(id);
    if (writer) {
      writer.close();
      this.connections.delete(id);
    }
  }

  broadcast(event: string, data: any): void {
    const message = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
    for (const writer of this.connections.values()) {
      writer.write(new TextEncoder().encode(message));
    }
  }

  sendToConnection(id: string, event: string, data: any): void {
    const writer = this.connections.get(id);
    if (writer) {
      const message = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
      writer.write(new TextEncoder().encode(message));
    }
  }

  getConnectionCount(): number {
    return this.connections.size;
  }

  cleanup(): void {
    for (const writer of this.connections.values()) {
      writer.close();
    }
    this.connections.clear();
  }
}

export class DefaultASIServer extends EventEmitter implements ASIServer {
  public config: ServerConfig;
  public app: Hono;
  public sseManager = new SSEConnectionManager();
  public wsServer?: import('./websocket/websocket-server.js').WSServer;

  private server: any = null;
  private readonly sessionManager: SessionManager;
  private readonly providerManager: ProviderManager;
  private readonly toolManager: ToolManager;

  constructor(
    config: ServerConfig,
    sessionManager: SessionManager,
    providerManager: ProviderManager,
    toolManager: ToolManager
  ) {
    super();
    this.config = config;
    this.sessionManager = sessionManager;
    this.providerManager = providerManager;
    this.toolManager = toolManager;
    this.app = new Hono();

    // Setup server asynchronously
    this.setupServer().catch(error => {
      console.error('Failed to setup server:', error);
      this.emit('error', error);
    });
  }

  private async setupServer(): Promise<void> {
    setupMiddleware(this.app, this.config);
    setupRoutes(this.app, this);

    // Setup WebSocket server if enabled
    if (this.config.websocket?.enabled) {
      try {
        const { WSServer } = await import('./websocket/websocket-server.js');
        this.wsServer = new WSServer(this);
        this.wsServer.setupRoutes(this.app);
        console.log('WebSocket server initialized');
      } catch (error) {
        console.error('Failed to initialize WebSocket server:', error);
      }
    }
  }

  // Getters for route handlers to access dependencies
  getSessionManager(): SessionManager {
    return this.sessionManager;
  }

  getProviderManager(): ProviderManager {
    return this.providerManager;
  }

  getToolManager(): ToolManager {
    return this.toolManager;
  }

  async start(): Promise<void> {
    if (this.server) {
      throw new Error('Server is already running');
    }

    this.server = serve({
      fetch: this.app.fetch,
      port: this.config.port,
      hostname: this.config.host,
    });

    this.emit('server:started', {
      host: this.config.host,
      port: this.config.port,
    });
  }

  async stop(): Promise<void> {
    if (this.server) {
      this.server.close();
      this.server = null;
      this.sseManager.cleanup();

      // Cleanup WebSocket server
      if (this.wsServer) {
        this.wsServer.cleanup();
        this.wsServer = undefined;
      }

      this.emit('server:stopped');
    }
  }

  isRunning(): boolean {
    return this.server !== null;
  }
}

// Factory function
export function createASIServer(
  config: ServerConfig,
  sessionManager: SessionManager,
  providerManager: ProviderManager,
  toolManager: ToolManager
): ASIServer {
  return new DefaultASIServer(
    config,
    sessionManager,
    providerManager,
    toolManager
  );
}

// Simplified server creation function for testing
export function createServer(config: any): any {
  // For integration tests, return a simplified server interface
  const app = new Hono();

  // Minimal setup for testing
  setupMiddleware(app, config);

  const server = {
    app,
    listen: (port: number, callback?: () => void) => {
      const nodeServer = serve({
        fetch: app.fetch,
        port: port,
        hostname: config.host || 'localhost',
      });

      if (callback) {
        process.nextTick(callback);
      }

      return nodeServer;
    },
    close: (callback?: () => void) => {
      if (callback) {
        process.nextTick(callback);
      }
    },
  };

  return server;
}

// Default server configuration
export const defaultServerConfig: ServerConfig = {
  port: 3000,
  host: 'localhost',
  ssl: {
    enabled: false,
  },
  cors: {
    origin: ['http://localhost:3000'],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  },
  auth: {
    enabled: false,
    type: 'jwt',
  },
  middleware: {
    compression: true,
    helmet: true,
    rateLimiting: {
      enabled: true,
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 100,
    },
    requestLogging: true,
  },
  static: {
    enabled: false,
    path: './public',
  },
  websocket: {
    enabled: true,
    path: '/ws',
    maxConnections: 1000,
    heartbeat: {
      enabled: true,
      interval: 30000,
      timeout: 60000,
    },
    compression: {
      enabled: true,
      threshold: 1024,
      level: 6,
    },
    auth: {
      enabled: false,
      type: 'jwt',
      timeout: 300,
    },
    rateLimiting: {
      enabled: true,
      messagesPerSecond: 10,
      messagesPerMinute: 100,
      bytesPerSecond: 10240,
    },
    messageQueue: {
      enabled: true,
      maxSize: 1000,
      persistence: false,
      ttl: 3600,
    },
    channels: {
      enabled: true,
      maxChannelsPerConnection: 50,
      channelNamePattern: '^[a-zA-Z0-9_-]{1,64}$',
    },
    binary: {
      enabled: true,
      maxSize: 10485760,
      allowedTypes: [
        'application/octet-stream',
        'application/json',
        'text/plain',
      ],
    },
    reconnection: {
      enabled: true,
      maxRetries: 5,
      backoffMultiplier: 1.5,
      maxBackoffTime: 30000,
    },
  },
};
