/**
 * WebSocket Connection Manager
 * 
 * Manages WebSocket connections, channels, and real-time communication
 * for the ASI-Code system. Includes room/channel support, message queuing,
 * and connection lifecycle management.
 */

import { EventEmitter } from 'eventemitter3';
import WebSocket from 'ws';
import { nanoid } from 'nanoid';
import type {
  WSMessage,
  WSConnectionState,
  WSChannelState,
  WSSubscriptionState,
  WSQueuedMessage,
  WSRateLimitState,
  WSServerEvents,
  WSMiddleware,
  WSMiddlewareContext,
  WSEventHandlers
} from './types.js';
import type { ServerConfig } from '../../config/config-types.js';

export class WSConnectionManager extends EventEmitter<WSServerEvents> {
  private connections = new Map<string, WSConnectionState>();
  private channels = new Map<string, WSChannelState>();
  private subscriptions = new Map<string, WSSubscriptionState>();
  private messageQueue = new Map<string, WSQueuedMessage[]>();
  private rateLimits = new Map<string, WSRateLimitState>();
  private websockets = new Map<string, WebSocket>();
  private middleware: WSMiddleware[] = [];
  private eventHandlers: WSEventHandlers = {};
  private config: ServerConfig['websocket'];
  
  // Heartbeat management
  private heartbeatInterval?: NodeJS.Timeout;
  private cleanupInterval?: NodeJS.Timeout;

  constructor(config: ServerConfig['websocket']) {
    super();
    this.config = {
      enabled: true,
      path: '/ws',
      maxConnections: 1000,
      heartbeat: {
        enabled: true,
        interval: 30000, // 30s
        timeout: 60000, // 60s
      },
      compression: {
        enabled: true,
        threshold: 1024, // 1KB
        level: 6,
      },
      auth: {
        enabled: false,
        type: 'jwt',
        timeout: 300, // 5min
      },
      rateLimiting: {
        enabled: true,
        messagesPerSecond: 10,
        messagesPerMinute: 100,
        bytesPerSecond: 10240, // 10KB
      },
      messageQueue: {
        enabled: true,
        maxSize: 1000,
        persistence: false,
        ttl: 3600, // 1 hour
      },
      channels: {
        enabled: true,
        maxChannelsPerConnection: 50,
        channelNamePattern: '^[a-zA-Z0-9_-]{1,64}$',
      },
      binary: {
        enabled: true,
        maxSize: 10485760, // 10MB
        allowedTypes: ['application/octet-stream', 'application/json', 'text/plain'],
      },
      reconnection: {
        enabled: true,
        maxRetries: 5,
        backoffMultiplier: 1.5,
        maxBackoffTime: 30000, // 30s
      },
      ...config,
    };

    this.startHeartbeat();
    this.startCleanup();
  }

  /**
   * Add a new WebSocket connection
   */
  addConnection(ws: WebSocket, connectionId?: string): string {
    const id = connectionId || nanoid();
    
    // Check connection limit
    if (this.connections.size >= this.config.maxConnections!) {
      ws.close(1013, 'Server capacity exceeded');
      throw new Error('Maximum connections exceeded');
    }

    const connection: WSConnectionState = {
      id,
      authenticated: !this.config.auth?.enabled,
      channels: new Set(),
      subscriptions: new Set(),
      messageQueue: [],
      metadata: {},
      createdAt: Date.now(),
      lastActivity: Date.now(),
    };

    this.connections.set(id, connection);
    this.websockets.set(id, ws);
    this.messageQueue.set(id, []);
    
    if (this.config.rateLimiting?.enabled) {
      this.rateLimits.set(id, {
        connectionId: id,
        messagesPerSecond: 0,
        messagesPerMinute: 0,
        bytesPerSecond: 0,
        windowStart: Date.now(),
        messageCount: 0,
        byteCount: 0,
        violations: 0,
      });
    }

    // Set up WebSocket event handlers
    this.setupWebSocketHandlers(ws, id);

    // Send ready message
    this.sendMessage(id, {
      id: nanoid(),
      type: 'connection:ready',
      timestamp: Date.now(),
      data: {
        connectionId: id,
        capabilities: this.getCapabilities(),
        maxMessageSize: this.config.binary?.maxSize || 0,
        heartbeatInterval: this.config.heartbeat?.interval || 0,
      },
    });

    this.emit('connection:open', id, connection);
    return id;
  }

  /**
   * Remove a connection
   */
  removeConnection(connectionId: string, code?: number, reason?: string): void {
    const connection = this.connections.get(connectionId);
    if (!connection) return;

    // Leave all channels
    for (const channelName of connection.channels) {
      this.leaveChannel(connectionId, channelName);
    }

    // Remove all subscriptions
    for (const event of connection.subscriptions) {
      this.unsubscribe(connectionId, event);
    }

    // Clean up
    const ws = this.websockets.get(connectionId);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close(code, reason);
    }

    this.connections.delete(connectionId);
    this.websockets.delete(connectionId);
    this.messageQueue.delete(connectionId);
    this.rateLimits.delete(connectionId);

    this.emit('connection:close', connectionId, code, reason);
  }

  /**
   * Send a message to a specific connection
   */
  async sendMessage(connectionId: string, message: WSMessage): Promise<void> {
    const ws = this.websockets.get(connectionId);
    const connection = this.connections.get(connectionId);
    
    if (!ws || !connection || ws.readyState !== WebSocket.OPEN) {
      if (this.config.messageQueue?.enabled) {
        this.queueMessage(connectionId, message);
      }
      return;
    }

    try {
      const messageStr = JSON.stringify(message);
      const messageSize = Buffer.byteLength(messageStr, 'utf8');

      // Check if compression should be applied
      if (this.config.compression?.enabled && 
          messageSize > (this.config.compression.threshold || 1024)) {
        // TODO: Implement compression
      }

      ws.send(messageStr);
      connection.lastActivity = Date.now();
      
      this.emit('message:sent', connectionId, message);
    } catch (error) {
      console.error(`Failed to send message to ${connectionId}:`, error);
      this.emit('connection:error', connectionId, error as Error);
    }
  }

  /**
   * Broadcast a message to multiple connections
   */
  async broadcast(
    message: WSMessage,
    filter?: (connection: WSConnectionState) => boolean
  ): Promise<void> {
    const promises: Promise<void>[] = [];
    
    for (const [connectionId, connection] of this.connections) {
      if (!filter || filter(connection)) {
        promises.push(this.sendMessage(connectionId, message));
      }
    }

    await Promise.all(promises);
  }

  /**
   * Join a channel
   */
  joinChannel(connectionId: string, channelName: string, password?: string): boolean {
    const connection = this.connections.get(connectionId);
    if (!connection) return false;

    // Validate channel name
    const pattern = this.config.channels?.channelNamePattern;
    if (pattern && !new RegExp(pattern).test(channelName)) {
      return false;
    }

    // Check channel limit
    const maxChannels = this.config.channels?.maxChannelsPerConnection || 50;
    if (connection.channels.size >= maxChannels) {
      return false;
    }

    // Get or create channel
    let channel = this.channels.get(channelName);
    if (!channel) {
      channel = {
        name: channelName,
        connections: new Set(),
        metadata: {},
        history: [],
        maxHistory: 100,
        createdAt: Date.now(),
        lastActivity: Date.now(),
      };
      this.channels.set(channelName, channel);
    }

    // Add connection to channel
    connection.channels.add(channelName);
    channel.connections.add(connectionId);
    channel.lastActivity = Date.now();

    this.emit('channel:joined', connectionId, channelName);
    
    // Notify other channel members
    this.broadcastToChannel(channelName, {
      id: nanoid(),
      type: 'channel:message',
      timestamp: Date.now(),
      data: {
        channel: channelName,
        message: {
          type: 'member_joined',
          connectionId,
        },
        sender: 'system',
      },
    }, [connectionId]);

    return true;
  }

  /**
   * Leave a channel
   */
  leaveChannel(connectionId: string, channelName: string): boolean {
    const connection = this.connections.get(connectionId);
    const channel = this.channels.get(channelName);
    
    if (!connection || !channel) return false;

    connection.channels.delete(channelName);
    channel.connections.delete(connectionId);

    // Clean up empty channels
    if (channel.connections.size === 0) {
      this.channels.delete(channelName);
    } else {
      // Notify remaining channel members
      this.broadcastToChannel(channelName, {
        id: nanoid(),
        type: 'channel:message',
        timestamp: Date.now(),
        data: {
          channel: channelName,
          message: {
            type: 'member_left',
            connectionId,
          },
          sender: 'system',
        },
      });
    }

    this.emit('channel:left', connectionId, channelName);
    return true;
  }

  /**
   * Broadcast to all connections in a channel
   */
  async broadcastToChannel(
    channelName: string,
    message: WSMessage,
    exclude?: string[]
  ): Promise<void> {
    const channel = this.channels.get(channelName);
    if (!channel) return;

    const promises: Promise<void>[] = [];
    const excludeSet = new Set(exclude || []);

    for (const connectionId of channel.connections) {
      if (!excludeSet.has(connectionId)) {
        promises.push(this.sendMessage(connectionId, message));
      }
    }

    // Add to channel history
    channel.history.push(message);
    if (channel.history.length > channel.maxHistory) {
      channel.history = channel.history.slice(-channel.maxHistory);
    }

    channel.lastActivity = Date.now();
    await Promise.all(promises);
  }

  /**
   * Subscribe to events
   */
  subscribe(
    connectionId: string,
    event: string,
    filter?: Record<string, any>,
    options?: { includeHistory?: boolean; maxHistory?: number }
  ): boolean {
    const connection = this.connections.get(connectionId);
    if (!connection) return false;

    connection.subscriptions.add(event);

    let subscription = this.subscriptions.get(event);
    if (!subscription) {
      subscription = {
        event,
        connections: new Set(),
        filter,
        options,
        history: [],
        createdAt: Date.now(),
      };
      this.subscriptions.set(event, subscription);
    }

    subscription.connections.add(connectionId);

    // Send history if requested
    if (options?.includeHistory && subscription.history.length > 0) {
      const historyCount = Math.min(
        subscription.history.length,
        options.maxHistory || 10
      );
      const history = subscription.history.slice(-historyCount);

      for (const historyItem of history) {
        this.sendMessage(connectionId, {
          id: nanoid(),
          type: 'subscription:event',
          timestamp: Date.now(),
          data: {
            event,
            payload: historyItem,
            source: 'history',
          },
        });
      }
    }

    this.emit('subscription:added', connectionId, event);
    return true;
  }

  /**
   * Unsubscribe from events
   */
  unsubscribe(connectionId: string, event: string): boolean {
    const connection = this.connections.get(connectionId);
    const subscription = this.subscriptions.get(event);
    
    if (!connection || !subscription) return false;

    connection.subscriptions.delete(event);
    subscription.connections.delete(connectionId);

    // Clean up empty subscriptions
    if (subscription.connections.size === 0) {
      this.subscriptions.delete(event);
    }

    this.emit('subscription:removed', connectionId, event);
    return true;
  }

  /**
   * Publish event to subscribers
   */
  async publishEvent(event: string, payload: any, source?: string): Promise<void> {
    const subscription = this.subscriptions.get(event);
    if (!subscription) return;

    const message: WSMessage = {
      id: nanoid(),
      type: 'subscription:event',
      timestamp: Date.now(),
      data: {
        event,
        payload,
        source,
      },
    };

    // Add to subscription history
    subscription.history.push(payload);
    if (subscription.history.length > 100) { // Default max history
      subscription.history = subscription.history.slice(-100);
    }

    // Send to all subscribers
    const promises: Promise<void>[] = [];
    for (const connectionId of subscription.connections) {
      promises.push(this.sendMessage(connectionId, message));
    }

    await Promise.all(promises);
  }

  /**
   * Add middleware
   */
  use(middleware: WSMiddleware): void {
    this.middleware.push(middleware);
  }

  /**
   * Add event handler
   */
  on<T extends keyof WSServerEvents>(event: T, handler: WSServerEvents[T]): this {
    return super.on(event, handler);
  }

  /**
   * Handle incoming message
   */
  private async handleMessage(connectionId: string, rawMessage: string | Buffer): Promise<void> {
    try {
      const connection = this.connections.get(connectionId);
      if (!connection) return;

      // Rate limiting
      if (!this.checkRateLimit(connectionId, rawMessage)) {
        this.emit('rate:limited', connectionId, 'message');
        return;
      }

      // Parse message
      let message: WSMessage;
      try {
        message = JSON.parse(rawMessage.toString());
      } catch (error) {
        this.sendError(connectionId, 'Invalid JSON message', 'INVALID_JSON');
        return;
      }

      connection.lastActivity = Date.now();

      // Create middleware context
      const context: WSMiddlewareContext = {
        connectionId,
        connection,
        message,
        rawMessage,
        server: this,
        next: async () => {
          await this.processMessage(connectionId, message);
        },
        error: (error: Error) => {
          this.emit('connection:error', connectionId, error);
        },
        respond: (responseMessage: WSMessage) => {
          return this.sendMessage(connectionId, responseMessage);
        },
        broadcast: (broadcastMessage: WSMessage, filter?) => {
          return this.broadcast(broadcastMessage, filter);
        },
      };

      // Execute middleware chain
      await this.executeMiddleware(context, 0);

      this.emit('message:received', connectionId, message);
    } catch (error) {
      console.error(`Error handling message from ${connectionId}:`, error);
      this.emit('connection:error', connectionId, error as Error);
    }
  }

  /**
   * Execute middleware chain
   */
  private async executeMiddleware(context: WSMiddlewareContext, index: number): Promise<void> {
    if (index >= this.middleware.length) {
      await context.next();
      return;
    }

    const middleware = this.middleware[index];
    const originalNext = context.next;
    
    context.next = async () => {
      await this.executeMiddleware(context, index + 1);
    };

    await middleware(context);
  }

  /**
   * Process a message after middleware
   */
  private async processMessage(connectionId: string, message: WSMessage): Promise<void> {
    const handler = this.eventHandlers[message.type];
    if (handler) {
      const connection = this.connections.get(connectionId);
      if (connection) {
        await handler(connectionId, message, { connection, server: this });
      }
    } else {
      // Handle built-in message types
      await this.handleBuiltinMessage(connectionId, message);
    }
  }

  /**
   * Handle built-in message types
   */
  private async handleBuiltinMessage(connectionId: string, message: WSMessage): Promise<void> {
    switch (message.type) {
      case 'connection:ping':
        await this.sendMessage(connectionId, {
          id: nanoid(),
          type: 'connection:pong',
          timestamp: Date.now(),
          data: {
            timestamp: Date.now(),
            latency: message.data?.timestamp ? Date.now() - message.data.timestamp : 0,
          },
        });
        break;

      case 'channel:join':
        if (message.data?.channel) {
          const joined = this.joinChannel(connectionId, message.data.channel, message.data.password);
          if (!joined) {
            await this.sendError(connectionId, 'Failed to join channel', 'CHANNEL_JOIN_FAILED');
          }
        }
        break;

      case 'channel:leave':
        if (message.data?.channel) {
          this.leaveChannel(connectionId, message.data.channel);
        }
        break;

      case 'channel:message':
        if (message.data?.channel && message.data?.message) {
          await this.broadcastToChannel(message.data.channel, {
            ...message,
            data: {
              ...message.data,
              sender: connectionId,
            },
          }, [connectionId]);
        }
        break;

      case 'subscription:subscribe':
        if (message.data?.event) {
          this.subscribe(
            connectionId,
            message.data.event,
            message.data.filter,
            message.data.options
          );
        }
        break;

      case 'subscription:unsubscribe':
        if (message.data?.event) {
          this.unsubscribe(connectionId, message.data.event);
        }
        break;

      default:
        // Unknown message type
        await this.sendError(connectionId, `Unknown message type: ${message.type}`, 'UNKNOWN_MESSAGE_TYPE');
    }
  }

  /**
   * Set up WebSocket event handlers
   */
  private setupWebSocketHandlers(ws: WebSocket, connectionId: string): void {
    ws.on('message', (data) => {
      this.handleMessage(connectionId, data);
    });

    ws.on('close', (code, reason) => {
      this.removeConnection(connectionId, code, reason.toString());
    });

    ws.on('error', (error) => {
      this.emit('connection:error', connectionId, error);
      this.removeConnection(connectionId, 1011, 'Internal error');
    });

    ws.on('pong', () => {
      const connection = this.connections.get(connectionId);
      if (connection) {
        connection.lastPong = Date.now();
      }
    });
  }

  /**
   * Check rate limits
   */
  private checkRateLimit(connectionId: string, message: string | Buffer): boolean {
    if (!this.config.rateLimiting?.enabled) return true;

    const rateLimit = this.rateLimits.get(connectionId);
    if (!rateLimit) return true;

    const now = Date.now();
    const messageSize = Buffer.byteLength(message);

    // Reset window if needed
    if (now - rateLimit.windowStart > 60000) { // 1 minute window
      rateLimit.windowStart = now;
      rateLimit.messageCount = 0;
      rateLimit.byteCount = 0;
    }

    // Check limits
    const messagesPerSecond = this.config.rateLimiting.messagesPerSecond || 10;
    const messagesPerMinute = this.config.rateLimiting.messagesPerMinute || 100;
    const bytesPerSecond = this.config.rateLimiting.bytesPerSecond || 10240;

    rateLimit.messageCount++;
    rateLimit.byteCount += messageSize;

    // Check per-second limits (simple approximation)
    const secondsInWindow = Math.max(1, (now - rateLimit.windowStart) / 1000);
    const currentMps = rateLimit.messageCount / secondsInWindow;
    const currentBps = rateLimit.byteCount / secondsInWindow;

    if (currentMps > messagesPerSecond ||
        rateLimit.messageCount > messagesPerMinute ||
        currentBps > bytesPerSecond) {
      rateLimit.violations++;
      return false;
    }

    return true;
  }

  /**
   * Queue message for later delivery
   */
  private queueMessage(connectionId: string, message: WSMessage): void {
    if (!this.config.messageQueue?.enabled) return;

    const queue = this.messageQueue.get(connectionId);
    if (!queue) return;

    const queuedMessage: WSQueuedMessage = {
      connectionId,
      message,
      attempts: 0,
      maxAttempts: 3,
      nextAttempt: Date.now() + 1000, // Retry in 1 second
      priority: 1,
      persistent: false,
    };

    queue.push(queuedMessage);

    // Limit queue size
    const maxSize = this.config.messageQueue.maxSize || 1000;
    if (queue.length > maxSize) {
      queue.shift(); // Remove oldest message
      this.emit('queue:full', connectionId);
    }
  }

  /**
   * Send error message
   */
  private async sendError(connectionId: string, error: string, code?: string): Promise<void> {
    await this.sendMessage(connectionId, {
      id: nanoid(),
      type: 'connection:error',
      timestamp: Date.now(),
      data: {
        error,
        code,
        timestamp: Date.now(),
      },
    });
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

    return capabilities;
  }

  /**
   * Start heartbeat mechanism
   */
  private startHeartbeat(): void {
    if (!this.config.heartbeat?.enabled) return;

    const interval = this.config.heartbeat.interval || 30000;
    const timeout = this.config.heartbeat.timeout || 60000;

    this.heartbeatInterval = setInterval(() => {
      const now = Date.now();

      for (const [connectionId, connection] of this.connections) {
        const ws = this.websockets.get(connectionId);
        if (!ws) continue;

        // Check if connection is stale
        if (connection.lastPong && (now - connection.lastPong) > timeout) {
          this.removeConnection(connectionId, 1001, 'Heartbeat timeout');
          continue;
        }

        // Send ping
        if (ws.readyState === WebSocket.OPEN) {
          connection.lastPing = now;
          ws.ping();
        }
      }
    }, interval);
  }

  /**
   * Start cleanup routine
   */
  private startCleanup(): void {
    this.cleanupInterval = setInterval(() => {
      const now = Date.now();
      const ttl = (this.config.messageQueue?.ttl || 3600) * 1000;

      // Clean up old queued messages
      for (const [connectionId, queue] of this.messageQueue) {
        for (let i = queue.length - 1; i >= 0; i--) {
          if ((now - queue[i].nextAttempt) > ttl) {
            queue.splice(i, 1);
          }
        }
      }

      // Clean up old channels
      for (const [channelName, channel] of this.channels) {
        if (channel.connections.size === 0 && (now - channel.lastActivity) > ttl) {
          this.channels.delete(channelName);
        }
      }
    }, 60000); // Run every minute
  }

  /**
   * Get connection statistics
   */
  getStats(): {
    connections: number;
    channels: number;
    subscriptions: number;
    queuedMessages: number;
  } {
    let totalQueuedMessages = 0;
    for (const queue of this.messageQueue.values()) {
      totalQueuedMessages += queue.length;
    }

    return {
      connections: this.connections.size,
      channels: this.channels.size,
      subscriptions: this.subscriptions.size,
      queuedMessages: totalQueuedMessages,
    };
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }

    // Close all connections
    for (const [connectionId] of this.connections) {
      this.removeConnection(connectionId, 1001, 'Server shutdown');
    }

    // Clear all data structures
    this.connections.clear();
    this.channels.clear();
    this.subscriptions.clear();
    this.messageQueue.clear();
    this.rateLimits.clear();
    this.websockets.clear();
  }
}