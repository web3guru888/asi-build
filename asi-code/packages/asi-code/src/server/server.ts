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
}

// SSE Connection Manager
export class SSEConnectionManager {
  private connections = new Map<string, WritableStreamDefaultWriter>();

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
  
  private server: any = null;
  private sessionManager: SessionManager;
  private providerManager: ProviderManager;
  private toolManager: ToolManager;

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
    
    this.setupServer();
  }

  private setupServer(): void {
    setupMiddleware(this.app, this.config);
    setupRoutes(this.app, this);
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
      hostname: this.config.host
    });

    this.emit('server:started', { 
      host: this.config.host, 
      port: this.config.port 
    });
  }

  async stop(): Promise<void> {
    if (this.server) {
      this.server.close();
      this.server = null;
      this.sseManager.cleanup();
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
  return new DefaultASIServer(config, sessionManager, providerManager, toolManager);
}

// Default server configuration
export const defaultServerConfig: ServerConfig = {
  port: 3000,
  host: 'localhost',
  ssl: {
    enabled: false
  },
  cors: {
    origin: ['http://localhost:3000'],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization']
  },
  auth: {
    enabled: false,
    type: 'jwt'
  },
  middleware: {
    compression: true,
    helmet: true,
    rateLimiting: {
      enabled: true,
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 100
    },
    requestLogging: true
  },
  static: {
    enabled: false,
    path: './public'
  }
};