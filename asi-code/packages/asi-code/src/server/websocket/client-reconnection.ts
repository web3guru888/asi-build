/**
 * WebSocket Client Reconnection Strategy
 *
 * Client-side reconnection logic with exponential backoff,
 * connection state management, and automatic recovery.
 */

import { EventEmitter } from 'eventemitter3';
import type { WSConnectionState, WSMessage } from './types.js';

export interface ReconnectionConfig {
  enabled: boolean;
  maxRetries: number;
  initialDelay: number; // milliseconds
  maxDelay: number; // milliseconds
  backoffMultiplier: number;
  jitter: boolean; // Add random variation to delays
  autoReconnect: boolean;
  reconnectOnVisibilityChange: boolean;
  heartbeatInterval: number;
  heartbeatTimeout: number;
}

export interface ConnectionState {
  status:
    | 'disconnected'
    | 'connecting'
    | 'connected'
    | 'reconnecting'
    | 'failed';
  attempts: number;
  lastConnected?: number;
  lastDisconnected?: number;
  nextAttempt?: number;
  error?: string;
}

export interface ReconnectionEvents {
  'connection:attempting': (attempt: number, delay: number) => void;
  'connection:established': (duration: number) => void;
  'connection:lost': (code?: number, reason?: string) => void;
  'connection:failed': (error: Error, attempts: number) => void;
  'connection:gave_up': (totalAttempts: number) => void;
  'heartbeat:sent': () => void;
  'heartbeat:received': (latency: number) => void;
  'heartbeat:timeout': () => void;
  'message:queued': (message: WSMessage) => void;
  'message:sent': (message: WSMessage) => void;
  'state:changed': (
    oldState: ConnectionState,
    newState: ConnectionState
  ) => void;
}

export class WSClientReconnection extends EventEmitter<ReconnectionEvents> {
  private readonly config: ReconnectionConfig;
  private state: ConnectionState;
  private ws: WebSocket | null = null;
  private reconnectTimeout?: NodeJS.Timeout;
  private heartbeatInterval?: NodeJS.Timeout;
  private heartbeatTimeout?: NodeJS.Timeout;
  private messageQueue: WSMessage[] = [];
  private readonly url: string;
  private readonly protocols?: string | string[];
  private readonly pendingMessages = new Map<
    string,
    { resolve: Function; reject: Function; timeout: NodeJS.Timeout }
  >();
  private lastHeartbeat?: number;

  constructor(
    url: string,
    config: Partial<ReconnectionConfig> = {},
    protocols?: string | string[]
  ) {
    super();

    this.url = url;
    this.protocols = protocols;
    this.config = {
      enabled: true,
      maxRetries: 5,
      initialDelay: 1000,
      maxDelay: 30000,
      backoffMultiplier: 1.5,
      jitter: true,
      autoReconnect: true,
      reconnectOnVisibilityChange: true,
      heartbeatInterval: 30000,
      heartbeatTimeout: 10000,
      ...config,
    };

    this.state = {
      status: 'disconnected',
      attempts: 0,
    };

    this.setupVisibilityChangeHandler();
    this.setupPageUnloadHandler();
  }

  /**
   * Connect to WebSocket server
   */
  async connect(): Promise<void> {
    if (
      this.state.status === 'connecting' ||
      this.state.status === 'connected'
    ) {
      return;
    }

    this.updateState({
      status: 'connecting',
      attempts: this.state.attempts + 1,
    });

    try {
      await this.establishConnection();
    } catch (error) {
      this.handleConnectionError(error as Error);
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(code?: number, reason?: string): void {
    this.config.autoReconnect = false;
    this.clearTimeouts();

    if (this.ws) {
      this.ws.close(code || 1000, reason || 'Client disconnect');
    }

    this.updateState({ status: 'disconnected' });
  }

  /**
   * Send a message
   */
  async send(message: WSMessage, timeout: number = 30000): Promise<void> {
    if (this.state.status !== 'connected' || !this.ws) {
      // Queue message if not connected
      this.messageQueue.push(message);
      this.emit('message:queued', message);

      if (this.config.autoReconnect && this.state.status !== 'connecting') {
        this.scheduleReconnect();
      }
      return;
    }

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        this.pendingMessages.delete(message.id);
        reject(new Error('Message send timeout'));
      }, timeout);

      this.pendingMessages.set(message.id, {
        resolve,
        reject,
        timeout: timeoutId,
      });

      try {
        this.ws!.send(JSON.stringify(message));
        this.emit('message:sent', message);

        // For messages that don't expect a response, resolve immediately
        if (!this.expectsResponse(message.type)) {
          const pending = this.pendingMessages.get(message.id);
          if (pending) {
            clearTimeout(pending.timeout);
            this.pendingMessages.delete(message.id);
            pending.resolve();
          }
        }
      } catch (error) {
        const pending = this.pendingMessages.get(message.id);
        if (pending) {
          clearTimeout(pending.timeout);
          this.pendingMessages.delete(message.id);
          pending.reject(error);
        }
      }
    });
  }

  /**
   * Get current connection state
   */
  getState(): ConnectionState {
    return { ...this.state };
  }

  /**
   * Get connection statistics
   */
  getStats(): {
    state: ConnectionState;
    queuedMessages: number;
    pendingMessages: number;
    uptime?: number;
    latency?: number;
  } {
    return {
      state: this.getState(),
      queuedMessages: this.messageQueue.length,
      pendingMessages: this.pendingMessages.size,
      uptime: this.state.lastConnected
        ? Date.now() - this.state.lastConnected
        : undefined,
      latency: this.lastHeartbeat ? Date.now() - this.lastHeartbeat : undefined,
    };
  }

  /**
   * Force reconnection
   */
  async reconnect(): Promise<void> {
    this.disconnect(1000, 'Manual reconnect');
    await new Promise(resolve => setTimeout(resolve, 100)); // Brief delay
    await this.connect();
  }

  /**
   * Clear message queue
   */
  clearQueue(): number {
    const count = this.messageQueue.length;
    this.messageQueue = [];
    return count;
  }

  /**
   * Enable auto-reconnect
   */
  enableAutoReconnect(): void {
    this.config.autoReconnect = true;
    if (this.state.status === 'disconnected') {
      this.scheduleReconnect();
    }
  }

  /**
   * Disable auto-reconnect
   */
  disableAutoReconnect(): void {
    this.config.autoReconnect = false;
    this.clearTimeouts();
  }

  /**
   * Establish WebSocket connection
   */
  private async establishConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url, this.protocols);

        const connectionTimeout = setTimeout(() => {
          this.ws?.close();
          reject(new Error('Connection timeout'));
        }, 10000);

        this.ws.onopen = () => {
          clearTimeout(connectionTimeout);
          this.handleConnectionOpen();
          resolve();
        };

        this.ws.onmessage = event => {
          this.handleMessage(event);
        };

        this.ws.onclose = event => {
          clearTimeout(connectionTimeout);
          this.handleConnectionClose(event.code, event.reason);
          if (this.state.status === 'connecting') {
            reject(
              new Error(`Connection failed: ${event.code} ${event.reason}`)
            );
          }
        };

        this.ws.onerror = error => {
          clearTimeout(connectionTimeout);
          console.error('WebSocket error:', error);
          if (this.state.status === 'connecting') {
            reject(new Error('Connection error'));
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Handle connection open
   */
  private handleConnectionOpen(): void {
    const now = Date.now();
    const duration = this.state.lastDisconnected
      ? now - this.state.lastDisconnected
      : 0;

    this.updateState({
      status: 'connected',
      attempts: 0,
      lastConnected: now,
      error: undefined,
      nextAttempt: undefined,
    });

    this.startHeartbeat();
    this.processQueuedMessages();
    this.emit('connection:established', duration);
  }

  /**
   * Handle connection close
   */
  private handleConnectionClose(code: number, reason: string): void {
    this.clearTimeouts();
    this.ws = null;

    this.updateState({
      status: 'disconnected',
      lastDisconnected: Date.now(),
    });

    this.emit('connection:lost', code, reason);

    // Schedule reconnect if auto-reconnect is enabled
    if (this.config.autoReconnect && this.config.enabled) {
      this.scheduleReconnect();
    }
  }

  /**
   * Handle connection error
   */
  private handleConnectionError(error: Error): void {
    this.updateState({
      status: 'failed',
      error: error.message,
    });

    this.emit('connection:failed', error, this.state.attempts);

    if (this.state.attempts >= this.config.maxRetries) {
      this.updateState({ status: 'disconnected' });
      this.emit('connection:gave_up', this.state.attempts);
      return;
    }

    if (this.config.autoReconnect && this.config.enabled) {
      this.scheduleReconnect();
    }
  }

  /**
   * Handle incoming message
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: WSMessage = JSON.parse(event.data);

      // Handle heartbeat responses
      if (message.type === 'connection:pong') {
        this.handleHeartbeatResponse(message);
        return;
      }

      // Resolve pending promises
      const pending = this.pendingMessages.get(message.id);
      if (pending) {
        clearTimeout(pending.timeout);
        this.pendingMessages.delete(message.id);
        pending.resolve(message);
      }

      // Emit message event for application handling
      this.emit('message', message);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (
      this.state.status === 'connecting' ||
      this.state.status === 'connected'
    ) {
      return;
    }

    if (this.state.attempts >= this.config.maxRetries) {
      this.updateState({ status: 'disconnected' });
      this.emit('connection:gave_up', this.state.attempts);
      return;
    }

    this.clearTimeouts();

    const delay = this.calculateDelay();
    const nextAttempt = Date.now() + delay;

    this.updateState({
      status: 'reconnecting',
      nextAttempt,
    });

    this.emit('connection:attempting', this.state.attempts + 1, delay);

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Calculate reconnection delay with exponential backoff
   */
  private calculateDelay(): number {
    const baseDelay =
      this.config.initialDelay *
      Math.pow(this.config.backoffMultiplier, this.state.attempts);

    let delay = Math.min(baseDelay, this.config.maxDelay);

    if (this.config.jitter) {
      // Add random jitter (±25%)
      const jitter = delay * 0.25;
      delay += (Math.random() - 0.5) * 2 * jitter;
    }

    return Math.max(delay, 0);
  }

  /**
   * Start heartbeat mechanism
   */
  private startHeartbeat(): void {
    if (!this.config.heartbeatInterval) return;

    this.clearHeartbeatTimeouts();

    this.heartbeatInterval = setInterval(() => {
      this.sendHeartbeat();
    }, this.config.heartbeatInterval);
  }

  /**
   * Send heartbeat ping
   */
  private sendHeartbeat(): void {
    if (this.state.status !== 'connected' || !this.ws) {
      return;
    }

    const pingMessage: WSMessage = {
      id: `ping_${Date.now()}`,
      type: 'connection:ping',
      timestamp: Date.now(),
      data: { timestamp: Date.now() },
    };

    this.lastHeartbeat = Date.now();

    try {
      this.ws.send(JSON.stringify(pingMessage));
      this.emit('heartbeat:sent');

      // Set timeout for heartbeat response
      this.heartbeatTimeout = setTimeout(() => {
        this.emit('heartbeat:timeout');
        if (this.config.autoReconnect) {
          this.ws?.close(1001, 'Heartbeat timeout');
        }
      }, this.config.heartbeatTimeout);
    } catch (error) {
      console.error('Error sending heartbeat:', error);
    }
  }

  /**
   * Handle heartbeat response
   */
  private handleHeartbeatResponse(message: WSMessage): void {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = undefined;
    }

    const latency = message.data?.latency || 0;
    this.emit('heartbeat:received', latency);
  }

  /**
   * Process queued messages
   */
  private processQueuedMessages(): void {
    const messages = [...this.messageQueue];
    this.messageQueue = [];

    for (const message of messages) {
      this.send(message).catch(error => {
        console.error('Error sending queued message:', error);
        // Re-queue the message
        this.messageQueue.push(message);
      });
    }
  }

  /**
   * Check if message type expects a response
   */
  private expectsResponse(messageType: string): boolean {
    const responseExpected = [
      'connection:auth',
      'channel:join',
      'subscription:subscribe',
      'ai:stream:start',
      'tool:execute:start',
    ];

    return responseExpected.includes(messageType);
  }

  /**
   * Update connection state
   */
  private updateState(updates: Partial<ConnectionState>): void {
    const oldState = { ...this.state };
    this.state = { ...this.state, ...updates };
    this.emit('state:changed', oldState, this.state);
  }

  /**
   * Clear all timeouts
   */
  private clearTimeouts(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = undefined;
    }
    this.clearHeartbeatTimeouts();
  }

  /**
   * Clear heartbeat timeouts
   */
  private clearHeartbeatTimeouts(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = undefined;
    }
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = undefined;
    }
  }

  /**
   * Setup visibility change handler for reconnection
   */
  private setupVisibilityChangeHandler(): void {
    if (!this.config.reconnectOnVisibilityChange) return;
    if (typeof document === 'undefined') return; // Node.js environment

    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        // Page became visible, check connection
        if (this.state.status === 'disconnected' && this.config.autoReconnect) {
          this.connect();
        }
      }
    });
  }

  /**
   * Setup page unload handler
   */
  private setupPageUnloadHandler(): void {
    if (typeof window === 'undefined') return; // Node.js environment

    window.addEventListener('beforeunload', () => {
      this.disconnect(1000, 'Page unload');
    });
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.config.autoReconnect = false;
    this.clearTimeouts();
    this.disconnect();
    this.removeAllListeners();

    // Clear pending promises
    for (const [id, pending] of this.pendingMessages) {
      clearTimeout(pending.timeout);
      pending.reject(new Error('Connection cleanup'));
    }
    this.pendingMessages.clear();
  }
}

/**
 * Factory function for creating reconnection-enabled WebSocket client
 */
export function createReconnectingWebSocket(
  url: string,
  config?: Partial<ReconnectionConfig>,
  protocols?: string | string[]
): WSClientReconnection {
  return new WSClientReconnection(url, config, protocols);
}

/**
 * Utility function to create a promise that resolves when connection is established
 */
export function waitForConnection(
  client: WSClientReconnection,
  timeout: number = 30000
): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error('Connection timeout'));
    }, timeout);

    const checkState = () => {
      const state = client.getState();
      if (state.status === 'connected') {
        clearTimeout(timeoutId);
        resolve();
      } else if (state.status === 'failed' && state.attempts >= 5) {
        clearTimeout(timeoutId);
        reject(new Error('Connection failed after maximum retries'));
      }
    };

    client.on('state:changed', checkState);
    checkState(); // Check current state
  });
}
