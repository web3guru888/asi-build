/**
 * WebSocket Server Integration
 *
 * Integrates WebSocket functionality with the existing Hono server,
 * providing real-time communication capabilities for ASI-Code.
 */

import { Hono } from 'hono';
import { upgradeWebSocket } from '@hono/node-ws';
import WebSocket from 'ws';
import { nanoid } from 'nanoid';
import { EventEmitter } from 'eventemitter3';

import { WSConnectionManager } from './connection-manager.js';
import { WSMessageQueue } from './message-queue.js';
import { WSBinaryManager, WSCompressionManager } from './compression.js';
import { createDefaultMiddlewareStack } from './middleware.js';
import type { WSConnectionState, WSMessage, WSServerEvents } from './types.js';
import type { ServerConfig } from '../../config/config-types.js';
import type { ASIServer } from '../server.js';

export interface WebSocketServerEvents extends WSServerEvents {
  'ai:stream:request': (connectionId: string, request: any) => void;
  'tool:execute:request': (connectionId: string, request: any) => void;
  'session:update:request': (connectionId: string, request: any) => void;
}

export class WSServer extends EventEmitter<WebSocketServerEvents> {
  private readonly connectionManager: WSConnectionManager;
  private readonly messageQueue: WSMessageQueue;
  private readonly compressionManager: WSCompressionManager;
  private readonly binaryManager: WSBinaryManager;
  private readonly config: ServerConfig['websocket'];
  private readonly asiServer: ASIServer;
  private readonly wsServer?: WebSocket.Server;

  constructor(asiServer: ASIServer) {
    super();
    this.asiServer = asiServer;
    this.config = asiServer.config.websocket || { enabled: false };

    if (!this.config.enabled) {
      throw new Error('WebSocket is not enabled in server configuration');
    }

    // Initialize managers
    this.connectionManager = new WSConnectionManager(this.config);
    this.messageQueue = new WSMessageQueue(this.config.messageQueue);
    this.compressionManager = new WSCompressionManager(
      this.config.compression || { enabled: false, threshold: 1024, level: 6 }
    );
    this.binaryManager = new WSBinaryManager({
      maxSize: this.config.binary?.maxSize,
      allowedTypes: this.config.binary?.allowedTypes,
    });

    this.setupConnectionManagerEvents();
    this.setupMiddleware();
    this.setupEventHandlers();
  }

  /**
   * Setup WebSocket routes in Hono app
   */
  setupRoutes(app: Hono): void {
    const wsPath = this.config.path || '/ws';

    app.get(
      wsPath,
      upgradeWebSocket(c => {
        return {
          onOpen: (event, ws) => {
            this.handleWebSocketConnection(ws);
          },
          onMessage: (event, ws) => {
            // Handled by connection manager
          },
          onClose: (event, ws) => {
            // Handled by connection manager
          },
          onError: (event, ws) => {
            console.error('WebSocket error:', event);
          },
        };
      })
    );

    // WebSocket status endpoint
    app.get('/api/websocket/status', c => {
      const stats = this.getStats();
      return c.json({
        enabled: this.config.enabled,
        stats,
        capabilities: this.getCapabilities(),
      });
    });

    // WebSocket connection info endpoint
    app.get('/api/websocket/connections', c => {
      const connections = this.connectionManager.getStats();
      return c.json(connections);
    });

    // Broadcast endpoint for server-side messages
    app.post('/api/websocket/broadcast', async c => {
      const { message, filter } = await c.req.json();
      await this.broadcast(message, filter);
      return c.json({ success: true });
    });
  }

  /**
   * Handle new WebSocket connection
   */
  private handleWebSocketConnection(ws: WebSocket): void {
    const connectionId = this.connectionManager.addConnection(ws);

    // Start processing queued messages for this connection
    const processQueue = async () => {
      if (ws.readyState === WebSocket.OPEN) {
        await this.messageQueue.processConnectionQueue(
          connectionId,
          async message => {
            try {
              await this.sendToConnection(connectionId, message);
              return true;
            } catch (error) {
              console.error('Error sending queued message:', error);
              return false;
            }
          }
        );
      }
    };

    // Process queue every 5 seconds
    const queueInterval = setInterval(processQueue, 5000);

    // Clean up when connection closes
    ws.on('close', () => {
      clearInterval(queueInterval);
    });
  }

  /**
   * Send message to a specific connection
   */
  async sendToConnection(
    connectionId: string,
    message: WSMessage
  ): Promise<void> {
    // Apply compression if enabled and message is large enough
    let messageData: string | Buffer = JSON.stringify(message);
    let headers: Record<string, any> = {};

    if (this.config.compression?.enabled) {
      const compressionResult =
        await this.compressionManager.compressMessage(messageData);
      if (compressionResult.compressed) {
        messageData = compressionResult.data;
        headers = {
          'x-compressed': true,
          'x-original-size': compressionResult.originalSize,
          'x-compressed-size': compressionResult.compressedSize,
        };
      }
    }

    await this.connectionManager.sendMessage(connectionId, {
      ...message,
      metadata: {
        ...message.metadata,
        ...headers,
      },
    });
  }

  /**
   * Broadcast message to all connections
   */
  async broadcast(
    message: WSMessage,
    filter?: (connection: WSConnectionState) => boolean
  ): Promise<void> {
    await this.connectionManager.broadcast(message, filter);
  }

  /**
   * Broadcast to channel
   */
  async broadcastToChannel(
    channel: string,
    message: WSMessage,
    exclude?: string[]
  ): Promise<void> {
    await this.connectionManager.broadcastToChannel(channel, message, exclude);
  }

  /**
   * Publish event to subscribers
   */
  async publishEvent(
    event: string,
    payload: any,
    source?: string
  ): Promise<void> {
    await this.connectionManager.publishEvent(event, payload, source);
  }

  /**
   * Queue message for reliable delivery
   */
  async queueMessage(
    connectionId: string,
    message: WSMessage,
    options?: {
      priority?: number;
      maxAttempts?: number;
      persistent?: boolean;
      delay?: number;
    }
  ): Promise<void> {
    await this.messageQueue.queueMessage(connectionId, message, options);
  }

  /**
   * Get server statistics
   */
  getStats(): {
    connections: number;
    channels: number;
    subscriptions: number;
    queuedMessages: number;
    compression: any;
    uptime: number;
  } {
    return {
      ...this.connectionManager.getStats(),
      compression: this.compressionManager.getStats(),
      uptime: process.uptime() * 1000,
    };
  }

  /**
   * Get server capabilities
   */
  private getCapabilities(): string[] {
    const capabilities: string[] = ['messaging'];

    if (this.config.channels?.enabled) capabilities.push('channels');
    if (this.config.binary?.enabled) capabilities.push('binary');
    if (this.config.compression?.enabled) capabilities.push('compression');
    if (this.config.heartbeat?.enabled) capabilities.push('heartbeat');
    if (this.config.messageQueue?.enabled) capabilities.push('queuing');

    return capabilities;
  }

  /**
   * Setup connection manager event forwarding
   */
  private setupConnectionManagerEvents(): void {
    // Forward all connection manager events
    this.connectionManager.on('connection:open', (connectionId, connection) => {
      this.emit('connection:open', connectionId, connection);
    });

    this.connectionManager.on(
      'connection:close',
      (connectionId, code, reason) => {
        this.emit('connection:close', connectionId, code, reason);
      }
    );

    this.connectionManager.on('connection:error', (connectionId, error) => {
      this.emit('connection:error', connectionId, error);
    });

    this.connectionManager.on(
      'connection:authenticated',
      (connectionId, userId) => {
        this.emit('connection:authenticated', connectionId, userId);
      }
    );

    this.connectionManager.on('message:received', (connectionId, message) => {
      this.emit('message:received', connectionId, message);
      this.handleIncomingMessage(connectionId, message);
    });

    this.connectionManager.on('message:sent', (connectionId, message) => {
      this.emit('message:sent', connectionId, message);
    });

    this.connectionManager.on('channel:joined', (connectionId, channel) => {
      this.emit('channel:joined', connectionId, channel);
    });

    this.connectionManager.on('channel:left', (connectionId, channel) => {
      this.emit('channel:left', connectionId, channel);
    });

    this.connectionManager.on('subscription:added', (connectionId, event) => {
      this.emit('subscription:added', connectionId, event);
    });

    this.connectionManager.on('subscription:removed', (connectionId, event) => {
      this.emit('subscription:removed', connectionId, event);
    });

    this.connectionManager.on('rate:limited', (connectionId, type) => {
      this.emit('rate:limited', connectionId, type);
    });

    this.connectionManager.on('queue:full', connectionId => {
      this.emit('queue:full', connectionId);
    });
  }

  /**
   * Setup middleware stack
   */
  private setupMiddleware(): void {
    const middlewareStack = createDefaultMiddlewareStack(this.config);

    for (const middleware of middlewareStack) {
      this.connectionManager.use(middleware);
    }
  }

  /**
   * Setup custom event handlers
   */
  private setupEventHandlers(): void {
    // Handle AI streaming requests
    this.connectionManager.on('message:received', (connectionId, message) => {
      if (message.type === 'ai:stream:start') {
        this.emit('ai:stream:request', connectionId, message.data);
      }
    });

    // Handle tool execution requests
    this.connectionManager.on('message:received', (connectionId, message) => {
      if (message.type === 'tool:execute:start') {
        this.emit('tool:execute:request', connectionId, message.data);
      }
    });

    // Handle session update requests
    this.connectionManager.on('message:received', (connectionId, message) => {
      if (message.type === 'session:update') {
        this.emit('session:update:request', connectionId, message.data);
      }
    });
  }

  /**
   * Handle incoming WebSocket messages
   */
  private async handleIncomingMessage(
    connectionId: string,
    message: WSMessage
  ): Promise<void> {
    try {
      // Handle special message types that require server integration
      switch (message.type) {
        case 'ai:stream:start':
          await this.handleAIStreamRequest(connectionId, message);
          break;

        case 'tool:execute:start':
          await this.handleToolExecutionRequest(connectionId, message);
          break;

        case 'session:update':
          await this.handleSessionUpdateRequest(connectionId, message);
          break;

        case 'system:status':
          await this.handleSystemStatusRequest(connectionId, message);
          break;

        default:
          // Message handled by connection manager
          break;
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: 'Message handling error',
          code: 'MESSAGE_HANDLER_ERROR',
          originalMessageId: message.id,
          timestamp: Date.now(),
        },
      });
    }
  }

  /**
   * Handle AI stream request
   */
  private async handleAIStreamRequest(
    connectionId: string,
    message: WSMessage
  ): Promise<void> {
    const { requestId, provider, model, prompt, options } = message.data || {};

    if (!requestId || !provider || !prompt) {
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'ai:stream:error',
        timestamp: Date.now(),
        data: {
          requestId: requestId || 'unknown',
          error: 'Missing required fields: requestId, provider, prompt',
          code: 'MISSING_FIELDS',
        },
      });
      return;
    }

    try {
      // Get provider manager from ASI server
      const providerManager = this.asiServer.getProviderManager();
      const selectedProvider = await providerManager.getProvider(provider);

      if (!selectedProvider) {
        await this.sendToConnection(connectionId, {
          id: nanoid(),
          type: 'ai:stream:error',
          timestamp: Date.now(),
          data: {
            requestId,
            error: `Provider not found: ${provider}`,
            code: 'PROVIDER_NOT_FOUND',
          },
        });
        return;
      }

      // Start streaming response
      const streamOptions = {
        model: model || selectedProvider.getDefaultModel(),
        stream: true,
        ...options,
      };

      let chunkIndex = 0;
      let totalTokens = 0;
      const startTime = Date.now();

      // Create stream handler
      const handleStream = async (chunk: any) => {
        await this.sendToConnection(connectionId, {
          id: nanoid(),
          type: 'ai:stream:chunk',
          timestamp: Date.now(),
          data: {
            requestId,
            chunk: chunk.content || chunk.text || '',
            index: chunkIndex++,
            finished: false,
            usage: chunk.usage,
          },
        });

        if (chunk.usage?.tokens) {
          totalTokens += chunk.usage.tokens;
        }
      };

      const handleComplete = async () => {
        await this.sendToConnection(connectionId, {
          id: nanoid(),
          type: 'ai:stream:end',
          timestamp: Date.now(),
          data: {
            requestId,
            totalChunks: chunkIndex,
            totalTokens,
            duration: Date.now() - startTime,
          },
        });
      };

      const handleError = async (error: Error) => {
        await this.sendToConnection(connectionId, {
          id: nanoid(),
          type: 'ai:stream:error',
          timestamp: Date.now(),
          data: {
            requestId,
            error: error.message,
            code: 'STREAM_ERROR',
          },
        });
      };

      // Start the stream
      await selectedProvider.streamCompletion(prompt, streamOptions, {
        onChunk: handleStream,
        onComplete: handleComplete,
        onError: handleError,
      });
    } catch (error) {
      console.error('AI stream error:', error);
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'ai:stream:error',
        timestamp: Date.now(),
        data: {
          requestId,
          error: error instanceof Error ? error.message : 'Unknown error',
          code: 'STREAM_SETUP_ERROR',
        },
      });
    }
  }

  /**
   * Handle tool execution request
   */
  private async handleToolExecutionRequest(
    connectionId: string,
    message: WSMessage
  ): Promise<void> {
    const { executionId, toolName, parameters, sessionId } = message.data || {};

    if (!executionId || !toolName) {
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'tool:execute:error',
        timestamp: Date.now(),
        data: {
          executionId: executionId || 'unknown',
          error: 'Missing required fields: executionId, toolName',
          code: 'MISSING_FIELDS',
        },
      });
      return;
    }

    try {
      // Get tool manager from ASI server
      const toolManager = this.asiServer.getToolManager();
      const tool = toolManager.getTool(toolName);

      if (!tool) {
        await this.sendToConnection(connectionId, {
          id: nanoid(),
          type: 'tool:execute:error',
          timestamp: Date.now(),
          data: {
            executionId,
            error: `Tool not found: ${toolName}`,
            code: 'TOOL_NOT_FOUND',
          },
        });
        return;
      }

      // Send start notification
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'tool:execute:start',
        timestamp: Date.now(),
        data: {
          executionId,
          toolName,
          parameters,
          sessionId,
        },
      });

      const startTime = Date.now();

      // Execute tool with progress updates
      const result = await tool.execute(parameters, {
        onProgress: async (progress, status, output) => {
          await this.sendToConnection(connectionId, {
            id: nanoid(),
            type: 'tool:execute:progress',
            timestamp: Date.now(),
            data: {
              executionId,
              progress,
              status,
              output,
            },
          });
        },
      });

      // Send result
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'tool:execute:result',
        timestamp: Date.now(),
        data: {
          executionId,
          result,
          success: true,
          duration: Date.now() - startTime,
        },
      });
    } catch (error) {
      console.error('Tool execution error:', error);
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'tool:execute:error',
        timestamp: Date.now(),
        data: {
          executionId,
          error: error instanceof Error ? error.message : 'Unknown error',
          code: 'TOOL_EXECUTION_ERROR',
        },
      });
    }
  }

  /**
   * Handle session update request
   */
  private async handleSessionUpdateRequest(
    connectionId: string,
    message: WSMessage
  ): Promise<void> {
    const { sessionId, update } = message.data || {};

    if (!sessionId) {
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: 'Missing sessionId',
          code: 'MISSING_SESSION_ID',
          timestamp: Date.now(),
        },
      });
      return;
    }

    try {
      // Get session manager from ASI server
      const sessionManager = this.asiServer.getSessionManager();
      const session = await sessionManager.getSession(sessionId);

      if (!session) {
        await this.sendToConnection(connectionId, {
          id: nanoid(),
          type: 'connection:error',
          timestamp: Date.now(),
          data: {
            error: `Session not found: ${sessionId}`,
            code: 'SESSION_NOT_FOUND',
            timestamp: Date.now(),
          },
        });
        return;
      }

      // Apply updates
      if (update) {
        await session.update(update);
      }

      // Send updated session data
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'session:update',
        timestamp: Date.now(),
        data: {
          sessionId,
          update: {
            messages: session.getMessages(),
            context: session.getContext(),
            status: session.getStatus(),
          },
        },
      });
    } catch (error) {
      console.error('Session update error:', error);
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error:
            error instanceof Error ? error.message : 'Session update error',
          code: 'SESSION_UPDATE_ERROR',
          timestamp: Date.now(),
        },
      });
    }
  }

  /**
   * Handle system status request
   */
  private async handleSystemStatusRequest(
    connectionId: string,
    message: WSMessage
  ): Promise<void> {
    try {
      const stats = this.getStats();

      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'system:status',
        timestamp: Date.now(),
        data: {
          status: 'healthy',
          components: {
            websocket: {
              status: 'healthy',
              message: `${stats.connections} active connections`,
            },
            server: {
              status: 'healthy',
              message: `Uptime: ${stats.uptime}ms`,
            },
          },
          timestamp: Date.now(),
        },
      });
    } catch (error) {
      console.error('System status error:', error);
      await this.sendToConnection(connectionId, {
        id: nanoid(),
        type: 'system:status',
        timestamp: Date.now(),
        data: {
          status: 'error',
          components: {
            websocket: {
              status: 'error',
              message: error instanceof Error ? error.message : 'Unknown error',
            },
          },
          timestamp: Date.now(),
        },
      });
    }
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.connectionManager.cleanup();
    this.messageQueue.cleanup();
    this.removeAllListeners();

    if (this.wsServer) {
      this.wsServer.close();
    }
  }
}
